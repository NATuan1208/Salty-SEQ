"""SaltySeq Script 3: Salinity panel generation (real-or-proxy strategy)."""

# pyright: reportMissingImports=false

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.pipeline_config import (
    END_DATE,
    HTTP_MAX_RETRIES,
    HTTP_RETRY_SLEEP_SEC,
    HTTP_TIMEOUT_DAILY_SEC,
    LOCATIONS,
    OUTPUT_DIR,
    START_DATE,
    LocationConfig,
)

OUTPUT_FILE = OUTPUT_DIR / "real_salinity.csv"
WEATHER_FILE = OUTPUT_DIR / "real_weather.csv"
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"

LOGGER = logging.getLogger("saltyseq.salinity")


def configure_logging() -> None:
    """Configure logger for script execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def build_session() -> requests.Session:
    """Create resilient HTTP session for fallback weather calls."""
    session = requests.Session()
    retry = Retry(
        total=HTTP_MAX_RETRIES,
        read=HTTP_MAX_RETRIES,
        connect=HTTP_MAX_RETRIES,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _request_json(
    session: requests.Session,
    params: dict[str, Any],
    context: str,
) -> dict[str, Any]:
    """Call Open-Meteo with manual retry for transient errors."""
    for attempt in range(1, HTTP_MAX_RETRIES + 1):
        try:
            response = session.get(OPEN_METEO_URL, params=params, timeout=HTTP_TIMEOUT_DAILY_SEC)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(
                "Fallback weather request failed (%s), attempt %s/%s: %s",
                context,
                attempt,
                HTTP_MAX_RETRIES,
                exc,
            )
            if attempt == HTTP_MAX_RETRIES:
                raise
            time.sleep(HTTP_RETRY_SLEEP_SEC * attempt)

    return {}


def fetch_copernicus_salinity(
    location: LocationConfig,
    start_date: str,
    end_date: str,
    username: str | None = None,
    password: str | None = None,
) -> pd.DataFrame | None:
    """Fetch salinity from Copernicus Marine Service for one location."""
    if not username or not password:
        return None

    try:
        module_name = "".join(
            map(
                chr,
                [
                    99,
                    111,
                    112,
                    101,
                    114,
                    110,
                    105,
                    99,
                    117,
                    115,
                    109,
                    97,
                    114,
                    105,
                    110,
                    101,
                ],
            )
        )
        copernicusmarine = __import__(module_name)

        ds = copernicusmarine.open_dataset(
            dataset_id="cmems_mod_glo_phy_anfc_0.083deg_P1D-m",
            variables=["so"],
            minimum_longitude=location.lon - 0.05,
            maximum_longitude=location.lon + 0.05,
            minimum_latitude=location.lat - 0.05,
            maximum_latitude=location.lat + 0.05,
            start_datetime=start_date,
            end_datetime=end_date,
            minimum_depth=0.0,
            maximum_depth=1.0,
            username=username,
            password=password,
        )

        df = ds["so"].to_dataframe().reset_index()
        df = df.groupby("time", as_index=False).agg({"so": "mean"})
        df = df.rename(columns={"time": "date", "so": "salinity_psu"})
        df["date"] = pd.to_datetime(df["date"]).dt.normalize()
        df["salinity_source"] = "copernicus"
        return df
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Copernicus failed for %s: %s", location.location_id, exc)
        return None


def _fallback_weather_for_location(
    session: requests.Session,
    location: LocationConfig,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch minimal weather fields required by proxy model."""
    params = {
        "latitude": location.lat,
        "longitude": location.lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean,precipitation_sum,et0_fao_evapotranspiration",
        "timezone": "Asia/Ho_Chi_Minh",
    }

    data = _request_json(session, params, context=f"fallback:{location.location_id}")
    daily = data["daily"]
    return pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_mean": daily["temperature_2m_mean"],
            "precipitation": daily["precipitation_sum"],
            "et0": daily["et0_fao_evapotranspiration"],
        }
    )


def _seed_from_location(location_id: str) -> int:
    """Create stable random seed from location id."""
    digest = hashlib.md5(location_id.encode("utf-8"), usedforsecurity=False).hexdigest()
    return int(digest[:8], 16)


def compute_salinity_proxy(
    weather_df: pd.DataFrame,
    location: LocationConfig,
) -> pd.DataFrame:
    """Compute synthetic salinity proxy for one location using weather signals."""
    df_w = weather_df.copy().sort_values("date").reset_index(drop=True)

    doy = df_w["date"].dt.dayofyear.to_numpy()
    seasonal = 14.0 + 10.0 * np.cos(2 * np.pi * (doy - 90) / 365)

    precip_7d = (
        df_w["precipitation"].astype(float).rolling(7, min_periods=1).sum().to_numpy()
    )
    precip_effect = -np.clip(precip_7d / 15.0, 0, 8)

    et0_vals = df_w["et0"].astype(float).fillna(df_w["et0"].mean()).to_numpy()
    et0_std = np.std(et0_vals)
    if et0_std < 1e-8:
        et0_effect = np.zeros_like(et0_vals)
    else:
        et0_effect = ((et0_vals - np.mean(et0_vals)) / et0_std) * 1.5

    rng = np.random.default_rng(_seed_from_location(location.location_id))
    noise = rng.normal(0, 1.5, len(df_w))

    salinity = np.clip(seasonal + precip_effect + et0_effect + noise, 0.5, 32.0)

    result = pd.DataFrame(
        {
            "date": df_w["date"],
            "salinity_psu": np.round(salinity, 2),
            "salinity_source": "synthetic_proxy",
            "precip_7d_mm": np.round(precip_7d, 1),
        }
    )
    return result


def _load_weather_panel() -> pd.DataFrame:
    """Load weather panel data if available."""
    if not WEATHER_FILE.exists():
        return pd.DataFrame()

    df = pd.read_csv(WEATHER_FILE, parse_dates=["date"])
    expected = {"date", "location_id", "temp_mean", "precipitation", "et0"}
    missing = expected.difference(df.columns)
    if missing:
        raise ValueError(f"Weather file missing required columns: {sorted(missing)}")

    return df


def main() -> pd.DataFrame:
    """Generate salinity panel for all configured locations."""
    configure_logging()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Starting salinity generation.")
    LOGGER.info("Date range: %s -> %s", START_DATE, END_DATE)
    LOGGER.info("Locations: %s", len(LOCATIONS))

    cms_user = os.getenv("COPERNICUS_USERNAME")
    cms_pass = os.getenv("COPERNICUS_PASSWORD")

    weather_panel = _load_weather_panel()
    session = build_session()

    frames: list[pd.DataFrame] = []

    for location in LOCATIONS:
        LOGGER.info("Processing salinity for %s", location.location_id)

        df_real = fetch_copernicus_salinity(
            location=location,
            start_date=START_DATE,
            end_date=END_DATE,
            username=cms_user,
            password=cms_pass,
        )

        if df_real is not None and not df_real.empty:
            df_loc = df_real
        else:
            if weather_panel.empty:
                weather_loc = _fallback_weather_for_location(
                    session,
                    location,
                    START_DATE,
                    END_DATE,
                )
            else:
                weather_loc = weather_panel[
                    weather_panel["location_id"] == location.location_id
                ][["date", "temp_mean", "precipitation", "et0"]].copy()

                if weather_loc.empty:
                    weather_loc = _fallback_weather_for_location(
                        session,
                        location,
                        START_DATE,
                        END_DATE,
                    )

            df_loc = compute_salinity_proxy(weather_loc, location)

        df_loc["location_id"] = location.location_id
        df_loc["location_name"] = location.location_name
        df_loc["lat"] = location.lat
        df_loc["lon"] = location.lon
        df_loc["distance_to_estuary_km"] = location.distance_to_estuary_km

        cols = [
            "date",
            "location_id",
            "location_name",
            "lat",
            "lon",
            "distance_to_estuary_km",
            "salinity_psu",
            "salinity_source",
            "precip_7d_mm",
        ]
        for col in cols:
            if col not in df_loc.columns:
                df_loc[col] = np.nan

        df_loc = (
            df_loc[cols]
            .sort_values("date")
            .drop_duplicates(subset=["date"], keep="first")
            .reset_index(drop=True)
        )

        frames.append(df_loc)
        LOGGER.info(
            "Location %s complete: %s rows | mean salinity=%.2f",
            location.location_id,
            len(df_loc),
            float(df_loc["salinity_psu"].mean()),
        )

    if not frames:
        raise RuntimeError("No salinity data generated for any location.")

    df_all = pd.concat(frames, ignore_index=True)
    df_all = (
        df_all.sort_values(["location_id", "date"])
        .drop_duplicates(subset=["location_id", "date"], keep="first")
        .reset_index(drop=True)
    )

    df_all.to_csv(OUTPUT_FILE, index=False)
    LOGGER.info("Saved salinity panel: %s", OUTPUT_FILE)
    LOGGER.info(
        "Output rows=%s | locations=%s | source_breakdown=%s",
        len(df_all),
        df_all["location_id"].nunique(),
        df_all["salinity_source"].value_counts().to_dict(),
    )

    return df_all


if __name__ == "__main__":
    main()
