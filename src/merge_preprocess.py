"""SaltySeq Script 4: Panel merge and preprocessing pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline

from src.pipeline_config import END_DATE, LOCATIONS, OUTPUT_DIR, START_DATE

SATELLITE_FILE = OUTPUT_DIR / "real_ndvi_lst.csv"
WEATHER_FILE = OUTPUT_DIR / "real_weather.csv"
SALINITY_FILE = OUTPUT_DIR / "real_salinity.csv"
OUTPUT_FILE = OUTPUT_DIR / "merged_final.csv"

LOGGER = logging.getLogger("saltyseq.merge")


def configure_logging() -> None:
    """Configure logger for script execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _ensure_location_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Backfill location_id for backward compatibility with legacy files."""
    out = df.copy()
    if "location_id" not in out.columns:
        out["location_id"] = LOCATIONS[0].location_id

    return out


def _validate_files_exist(paths: list[Path]) -> None:
    missing = [path for path in paths if not path.exists()]
    if missing:
        names = "\n".join(f"- {item.name}" for item in missing)
        raise FileNotFoundError(f"Missing required input files:\n{names}")


def load_sources() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load source CSV files from scripts 1, 2, and 3."""
    LOGGER.info("Loading source data files.")
    _validate_files_exist([SATELLITE_FILE, WEATHER_FILE, SALINITY_FILE])

    df_sat = pd.read_csv(SATELLITE_FILE, parse_dates=["date"])
    df_weather = pd.read_csv(WEATHER_FILE, parse_dates=["date"])
    df_salinity = pd.read_csv(SALINITY_FILE, parse_dates=["date"])

    df_sat = _ensure_location_columns(df_sat)
    df_weather = _ensure_location_columns(df_weather)
    df_salinity = _ensure_location_columns(df_salinity)

    for df in [df_sat, df_weather, df_salinity]:
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    LOGGER.info(
        "Loaded rows | satellite=%s weather=%s salinity=%s",
        len(df_sat),
        len(df_weather),
        len(df_salinity),
    )

    return df_sat, df_weather, df_salinity


def _missing_run_lengths(series: pd.Series) -> pd.Series:
    """Compute consecutive missing length indicator for each missing point."""
    is_missing = series.isna()
    group = (~is_missing).cumsum()
    lengths = is_missing.groupby(group).cumsum()
    return lengths.where(is_missing, 0).astype(int)


def _apply_edge_fill(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Fill only edge NaNs (before first valid or after last valid)."""
    out = series.copy()
    marker = pd.Series(False, index=out.index)

    valid_idx = np.flatnonzero(out.notna().to_numpy())
    if len(valid_idx) == 0:
        return out, marker

    first_valid = valid_idx[0]
    last_valid = valid_idx[-1]
    edge_mask = out.isna() & ((out.index <= first_valid) | (out.index >= last_valid))

    if edge_mask.any():
        edge_filled = out.ffill().bfill()
        out.loc[edge_mask] = edge_filled.loc[edge_mask]
        marker.loc[edge_mask] = True

    return out, marker


def _apply_spline_fill(
    dates: pd.Series,
    series: pd.Series,
    target_mask: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """Apply cubic spline interpolation on target points only."""
    out = series.copy()
    marker = pd.Series(False, index=series.index)

    obs_mask = out.notna()
    if obs_mask.sum() < 4 or target_mask.sum() == 0:
        return out, marker

    x_all = dates.map(pd.Timestamp.toordinal).to_numpy(dtype=float)
    x_obs = x_all[obs_mask.to_numpy()]
    y_obs = out.loc[obs_mask].to_numpy(dtype=float)

    try:
        spline = UnivariateSpline(x_obs, y_obs, k=3, s=0)
        x_target = x_all[target_mask.to_numpy()]
        y_pred = spline(x_target)
        out.loc[target_mask] = y_pred
        marker.loc[target_mask] = True
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Spline interpolation skipped due to error: %s", exc)

    return out, marker


def align_to_daily(df_sat: pd.DataFrame) -> pd.DataFrame:
    """Align satellite panel to daily grid per location with audited interpolation."""
    LOGGER.info("Aligning satellite data to daily panel grid.")

    daily_dates = pd.date_range(start=START_DATE, end=END_DATE, freq="D")
    cutoff_spline = pd.Timestamp("2017-12-31")

    frames: list[pd.DataFrame] = []

    for location in LOCATIONS:
        sat_loc = df_sat[df_sat["location_id"] == location.location_id].copy()
        sat_loc = sat_loc.sort_values("date").drop_duplicates(subset=["date"], keep="first")

        grid = pd.DataFrame({"date": daily_dates})
        merged = grid.merge(sat_loc, on="date", how="left")

        merged["location_id"] = location.location_id
        merged["location_name"] = location.location_name
        merged["lat"] = location.lat
        merged["lon"] = location.lon
        merged["distance_to_estuary_km"] = location.distance_to_estuary_km

        if "ndvi_source" not in merged.columns:
            merged["ndvi_source"] = "none"
        merged["ndvi_source"] = merged["ndvi_source"].fillna("none")

        ndvi_original = merged["ndvi"].astype(float)
        lst_original = merged["lst"].astype(float)

        merged["ndvi_is_observed"] = ndvi_original.notna().astype(int)
        merged["lst_is_observed"] = lst_original.notna().astype(int)
        merged["ndvi_gap_days"] = _missing_run_lengths(ndvi_original)

        ndvi_method = pd.Series("missing", index=merged.index, dtype="object")
        ndvi_method.loc[ndvi_original.notna()] = "observed"

        ndvi_linear = ndvi_original.interpolate(
            method="linear",
            limit=15,
            limit_direction="both",
        )
        linear_mask = ndvi_original.isna() & ndvi_linear.notna()
        ndvi_method.loc[linear_mask] = "linear"

        spline_target = ndvi_linear.isna() & (merged["date"] <= cutoff_spline)
        ndvi_spline, spline_mask = _apply_spline_fill(
            dates=merged["date"],
            series=ndvi_linear,
            target_mask=spline_target,
        )
        ndvi_method.loc[spline_mask] = "spline"

        ndvi_edge, edge_mask = _apply_edge_fill(ndvi_spline)
        ndvi_method.loc[edge_mask] = "edge_fill"

        merged["ndvi"] = ndvi_edge.clip(-0.2, 1.0)
        merged["ndvi_interp_method"] = ndvi_method

        lst_method = pd.Series("missing", index=merged.index, dtype="object")
        lst_method.loc[lst_original.notna()] = "observed"

        lst_linear = lst_original.interpolate(
            method="linear",
            limit=15,
            limit_direction="both",
        )
        lst_linear_mask = lst_original.isna() & lst_linear.notna()
        lst_method.loc[lst_linear_mask] = "linear"

        lst_edge, lst_edge_mask = _apply_edge_fill(lst_linear)
        lst_method.loc[lst_edge_mask] = "edge_fill"

        merged["lst"] = lst_edge
        merged["lst_interp_method"] = lst_method

        frames.append(merged)

        LOGGER.info(
            "Aligned %s | ndvi observed=%s, linear=%s, spline=%s, edge=%s",
            location.location_id,
            int((ndvi_method == "observed").sum()),
            int((ndvi_method == "linear").sum()),
            int((ndvi_method == "spline").sum()),
            int((ndvi_method == "edge_fill").sum()),
        )

    df_daily = pd.concat(frames, ignore_index=True)
    return df_daily.sort_values(["location_id", "date"]).reset_index(drop=True)


def merge_all(
    df_daily_sat: pd.DataFrame,
    df_weather: pd.DataFrame,
    df_salinity: pd.DataFrame,
) -> pd.DataFrame:
    """Merge panel datasets using composite key (location_id, date)."""
    LOGGER.info("Merging aligned satellite, weather, and salinity panel data.")

    weather_cols = [
        "location_id",
        "date",
        "temp_max",
        "temp_min",
        "temp_mean",
        "precipitation",
        "rain",
        "et0",
        "radiation",
        "wind_max",
        "soil_moisture_surface",
        "soil_moisture_deep",
        "soil_temp",
    ]
    weather_cols = [col for col in weather_cols if col in df_weather.columns]

    salinity_cols = ["location_id", "date", "salinity_psu", "precip_7d_mm", "salinity_source"]
    salinity_cols = [col for col in salinity_cols if col in df_salinity.columns]

    merged = df_daily_sat.merge(
        df_weather[weather_cols],
        on=["location_id", "date"],
        how="inner",
    )
    merged = merged.merge(
        df_salinity[salinity_cols],
        on=["location_id", "date"],
        how="inner",
    )

    if merged.duplicated(subset=["location_id", "date"]).any():
        raise ValueError("Duplicate keys detected after merge on location_id + date.")

    LOGGER.info(
        "Merged output rows=%s cols=%s locations=%s",
        len(merged),
        merged.shape[1],
        merged["location_id"].nunique(),
    )

    return merged


def _days_without_rain(series: pd.Series) -> pd.Series:
    """Count consecutive days with rainfall below 1 mm."""
    count = 0
    result: list[int] = []
    for rain in series.fillna(0.0):
        if rain >= 1.0:
            count = 0
        else:
            count += 1
        result.append(count)

    return pd.Series(result, index=series.index)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create panel-aware temporal, rolling, lag, and anomaly features."""
    LOGGER.info("Engineering panel features.")
    out = df.copy().sort_values(["location_id", "date"]).reset_index(drop=True)

    out["day_of_year"] = out["date"].dt.dayofyear
    out["month"] = out["date"].dt.month
    out["week"] = out["date"].dt.isocalendar().week.astype(int)
    out["season"] = out["month"].apply(lambda m: "dry" if m in [11, 12, 1, 2, 3, 4] else "wet")
    out["is_dry_season"] = (out["season"] == "dry").astype(int)
    out["month_sin"] = np.sin(2 * np.pi * out["month"] / 12)
    out["month_cos"] = np.cos(2 * np.pi * out["month"] / 12)

    grp = out.groupby("location_id", group_keys=False)

    out["temp_7d_avg"] = grp["temp_mean"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    out["ndvi_7d_avg"] = grp["ndvi"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    out["precip_7d_sum"] = grp["precipitation"].transform(lambda s: s.rolling(7, min_periods=1).sum())
    out["salinity_7d_avg"] = grp["salinity_psu"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    out["lst_7d_avg"] = grp["lst"].transform(lambda s: s.rolling(7, min_periods=1).mean())
    out["soil_moisture_7d_avg"] = grp["soil_moisture_surface"].transform(
        lambda s: s.rolling(7, min_periods=1).mean()
    )

    for lag in [1, 3, 7]:
        out[f"ndvi_lag_{lag}"] = grp["ndvi"].shift(lag)
        out[f"salinity_lag_{lag}"] = grp["salinity_psu"].shift(lag)
        out[f"precip_lag_{lag}"] = grp["precipitation"].shift(lag)

    out["days_without_rain"] = grp["precipitation"].transform(_days_without_rain)
    out["moisture_deficit"] = out["et0"] - out["precipitation"]
    out["moisture_deficit_7d"] = grp["moisture_deficit"].transform(
        lambda s: s.rolling(7, min_periods=1).sum()
    )

    out["ndvi_diff"] = grp["ndvi"].diff()
    out["ndvi_pct_change"] = grp["ndvi"].pct_change()

    out["lst_ndvi_ratio"] = out["lst"] / out["ndvi"].clip(lower=0.1)
    out["salinity_precip_ratio"] = out["salinity_psu"] / out["precipitation"].clip(lower=0.1)

    month_mean = out.groupby(["location_id", "month"])["ndvi"].transform("mean")
    month_std = out.groupby(["location_id", "month"])["ndvi"].transform("std")
    out["ndvi_zscore"] = (out["ndvi"] - month_mean) / month_std.clip(lower=0.01)
    out["is_ndvi_anomaly"] = (out["ndvi_zscore"].abs() > 2.0).astype(int)

    out["is_salinity_spike"] = (
        (out["salinity_psu"] > 10) & (out["is_dry_season"] == 0)
    ).astype(int)

    ndvi_max = grp["ndvi"].transform("max").clip(lower=0.01)
    salinity_max = grp["salinity_psu"].transform("max").clip(lower=0.01)
    soil_max = grp["soil_moisture_surface"].transform("max").clip(lower=0.01)

    out["crop_stress_score"] = (
        (1 - out["ndvi"] / ndvi_max) * 0.4
        + (out["salinity_psu"] / salinity_max) * 0.4
        + (1 - out["soil_moisture_surface"] / soil_max) * 0.2
    )

    return out


def final_cleanup(df: pd.DataFrame) -> pd.DataFrame:
    """Handle remaining NaNs without cross-location leakage."""
    LOGGER.info("Running final cleanup.")
    out = df.copy().sort_values(["location_id", "date"]).reset_index(drop=True)

    protected = {
        "ndvi",
        "lst",
        "ndvi_is_observed",
        "lst_is_observed",
        "ndvi_gap_days",
    }
    numeric_cols = [
        col
        for col in out.select_dtypes(include=[np.number]).columns
        if col not in protected
    ]

    for col in numeric_cols:
        out[col] = out.groupby("location_id")[col].transform(lambda s: s.ffill().bfill())

    missing_after = int(out.isna().sum().sum())
    LOGGER.info("Final missing values after cleanup: %s", missing_after)

    return out


def profile_output(df: pd.DataFrame) -> None:
    """Print concise profiling summary for review."""
    LOGGER.info("Profiling merged dataset.")

    total_cells = df.shape[0] * df.shape[1]
    missing = int(df.isna().sum().sum())
    completeness = 100.0 * (1.0 - (missing / total_cells))

    LOGGER.info(
        "Shape=%s x %s | locations=%s | range=%s -> %s | completeness=%.2f%%",
        df.shape[0],
        df.shape[1],
        df["location_id"].nunique(),
        df["date"].min().date(),
        df["date"].max().date(),
        completeness,
    )

    method_counts = (
        df["ndvi_interp_method"].value_counts(dropna=False).sort_index().to_dict()
        if "ndvi_interp_method" in df.columns
        else {}
    )
    LOGGER.info("NDVI interpolation methods: %s", method_counts)


def main() -> pd.DataFrame:
    """Execute merge and feature engineering pipeline."""
    configure_logging()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Starting merge preprocessing pipeline.")
    LOGGER.info("Date range target: %s -> %s", START_DATE, END_DATE)

    df_sat, df_weather, df_salinity = load_sources()
    df_daily_sat = align_to_daily(df_sat)
    df_merged = merge_all(df_daily_sat, df_weather, df_salinity)
    df_features = engineer_features(df_merged)
    df_final = final_cleanup(df_features)

    if df_final.duplicated(subset=["location_id", "date"]).any():
        raise ValueError("Duplicate keys in final dataset for location_id + date.")

    df_final.to_csv(OUTPUT_FILE, index=False)
    LOGGER.info("Saved merged panel dataset: %s", OUTPUT_FILE)

    profile_output(df_final)
    return df_final


if __name__ == "__main__":
    main()
