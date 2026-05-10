"""
Export XGBoost model + scaler + artifacts from Jupyter project to saltyseq-demo/.

Usage:
    python setup_model.py --data_path ./output/merged_final.csv
    python setup_model.py --data_path ./output/merged_final.csv --model_path ./output/xgboost_model.json
"""
import argparse
import json
import logging
import pickle
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEMO_DIR = Path(__file__).parent
MODELS_DIR = DEMO_DIR / "backend" / "models"
DATA_DIR = DEMO_DIR / "backend" / "data"

TRAIN_END = "2022-12-31"

FEATURE_COLUMNS = [
    "lat", "lon", "distance_to_estuary_km", "ndvi", "lst", "ndvi_gap_days",
    "temp_max", "temp_min", "temp_mean", "precipitation", "et0", "radiation",
    "wind_max", "soil_moisture_surface", "soil_moisture_deep", "soil_temp",
    "salinity_psu", "day_of_year", "month", "week", "is_dry_season",
    "month_sin", "month_cos", "temp_7d_avg", "ndvi_7d_avg", "precip_7d_sum",
    "salinity_7d_avg", "salinity_7d_avg_lag1", "lst_7d_avg", "soil_moisture_7d_avg",
    "ndvi_lag_1", "ndvi_lag_3", "ndvi_lag_7", "days_without_rain",
    "moisture_deficit", "moisture_deficit_7d", "lst_ndvi_ratio",
    "salinity_precip_ratio", "salinity_7d_median", "ndvi_7d_median",
    "precip_15d_sum", "precip_30d_sum", "heatwave_consecutive_days",
    "salinity_tendency", "ndvi_tendency", "soil_moisture_tendency",
]
TARGET_COL = "is_stress_event"

DEFAULT_PARAMS = {
    "n_estimators": 300,
    "max_depth": 6,
    "learning_rate": 0.05,
    "scale_pos_weight": 8.946,
    "use_label_encoder": False,
    "eval_metric": "logloss",
    "random_state": 42,
}

FALLBACK_PATTERNS = {
    "danger": [
        {
            "pattern": ["Salt_High|Soil_Dry|Plant_Warning", "Salt_High|Soil_Dry|Plant_DANGER"],
            "support": 816, "support_pct": 4.07, "type": "danger",
            "label_vi": "Chuỗi mặn cao + khô hạn dẫn đến NGUY HIỂM",
        },
        {
            "pattern": ["Salt_Mod|Soil_Dry|Plant_Warning", "Salt_High|Soil_Dry|Plant_DANGER"],
            "support": 612, "support_pct": 3.05, "type": "danger",
            "label_vi": "Mặn vừa sang cao + đất khô → nguy hiểm",
        },
    ],
    "warning": [
        {
            "pattern": ["Salt_High|Soil_Wet|Plant_Safe", "Salt_High|Soil_Dry|Plant_Warning"],
            "support": 4954, "support_pct": 24.7, "type": "warning",
            "label_vi": "Mặn cao chuyển từ ướt sang khô, cây bắt đầu cảnh báo",
        },
        {
            "pattern": ["Salt_Low|Soil_Wet|Plant_Safe", "Salt_Mod|Soil_Wet|Plant_Warning"],
            "support": 2100, "support_pct": 10.5, "type": "warning",
            "label_vi": "Mặn tăng dần từ thấp → vừa, cây bắt đầu bị ảnh hưởng",
        },
    ],
    "lookback": 14,
    "min_sup": 0.03,
}

STATIONS = {
    "BT_BaTri":     {"name": "Ba Tri",      "lat": 10.0355, "lon": 106.6041, "distance_to_estuary_km": 22.5},
    "BT_BinhDai":   {"name": "Bình Đại",    "lat": 10.1499, "lon": 106.7905, "distance_to_estuary_km":  8.3},
    "BT_ChauThanh": {"name": "Châu Thành",  "lat": 10.2499, "lon": 106.4314, "distance_to_estuary_km": 38.1},
    "BT_GiongTrom": {"name": "Giồng Trôm",  "lat": 10.1009, "lon": 106.4736, "distance_to_estuary_km": 29.6},
    "BT_ThanhPhu":  {"name": "Thạnh Phú",   "lat":  9.9049, "lon": 106.5921, "distance_to_estuary_km":  5.2},
}


def load_data(data_path: Path) -> pd.DataFrame:
    logger.info("Loading data from %s", data_path)
    df = pd.read_csv(data_path)
    df["date"] = pd.to_datetime(df["date"])
    logger.info("Loaded %d rows, %d columns", len(df), len(df.columns))
    return df


def split_train(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df["date"] <= TRAIN_END].copy()
    test = df[df["date"] > TRAIN_END].copy()
    logger.info("Train: %d rows | Test: %d rows", len(train), len(test))
    return train, test


def prepare_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    available = [c for c in FEATURE_COLUMNS if c in df.columns]
    missing = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        logger.warning("Missing columns (will fill 0): %s", missing)
    X = df.reindex(columns=FEATURE_COLUMNS, fill_value=0.0).ffill().bfill().fillna(0.0)
    y = df[TARGET_COL].astype(int)
    return X, y


def train_model(X_train: pd.DataFrame, y_train: pd.Series, params: dict):
    from xgboost import XGBClassifier
    logger.info("Training XGBoost with params: %s", params)
    model = XGBClassifier(**params)
    model.fit(X_train, y_train, verbose=False)
    logger.info("Training done")
    return model


def load_best_params(data_dir: Path) -> dict:
    trials_path = data_dir / "optuna_trials.csv"
    if not trials_path.exists():
        logger.info("No optuna_trials.csv found, using default params")
        return DEFAULT_PARAMS
    try:
        trials = pd.read_csv(trials_path)
        best = trials.sort_values("value", ascending=False).iloc[0]
        params = {
            "n_estimators": int(best.get("params_n_estimators", DEFAULT_PARAMS["n_estimators"])),
            "max_depth": int(best.get("params_max_depth", DEFAULT_PARAMS["max_depth"])),
            "learning_rate": float(best.get("params_learning_rate", DEFAULT_PARAMS["learning_rate"])),
            "scale_pos_weight": float(best.get("params_scale_pos_weight", DEFAULT_PARAMS["scale_pos_weight"])),
            "eval_metric": "logloss",
            "random_state": 42,
        }
        logger.info("Loaded best Optuna params: %s", params)
        return params
    except Exception as e:
        logger.warning("Failed to read optuna_trials.csv: %s — using defaults", e)
        return DEFAULT_PARAMS


def _label_salinity(psu: float) -> str:
    if psu < 2:
        return "Salt_Low"
    if psu < 4:
        return "Salt_Mod"
    return "Salt_High"


def _label_moisture(sm: float) -> str:
    return "Soil_Dry" if sm < 0.25 else "Soil_Wet"


def _label_stress(label: int) -> str:
    return "Plant_DANGER" if label else "Plant_Safe"


def run_spm(df: pd.DataFrame) -> dict:
    try:
        from prefixspan import PrefixSpan
    except ImportError:
        logger.warning("prefixspan not installed — saving fallback patterns")
        return FALLBACK_PATTERNS

    logger.info("Building SPM sequences...")
    sequences = []
    for (sid, _grp_date), group in df.groupby(["station_id", pd.Grouper(key="date", freq="14D")]):
        seq = []
        for _, row in group.iterrows():
            sal = _label_salinity(float(row.get("salinity_psu", 5.0) or 5.0))
            sm = _label_moisture(float(row.get("soil_moisture_surface", 0.3) or 0.3))
            stress = _label_stress(int(row.get(TARGET_COL, 0) or 0))
            seq.append(f"{sal}|{sm}|{stress}")
        if seq:
            sequences.append(seq)

    min_sup = max(1, int(len(sequences) * 0.03))
    logger.info("Running PrefixSpan on %d sequences, min_sup=%d", len(sequences), min_sup)
    ps = PrefixSpan(sequences)
    results = ps.frequent(min_sup)

    danger_patterns, warning_patterns = [], []
    for sup, pat in results:
        if not pat:
            continue
        entry = {
            "pattern": pat,
            "support": sup,
            "support_pct": round(sup / len(sequences) * 100, 2),
            "type": "danger" if "Plant_DANGER" in pat[-1] else "warning",
            "label_vi": None,
        }
        if "Plant_DANGER" in pat[-1]:
            danger_patterns.append(entry)
        elif "Plant_Warning" in pat[-1] or "Plant_Safe" in pat[-1]:
            warning_patterns.append(entry)

    logger.info("Found %d danger, %d warning patterns", len(danger_patterns), len(warning_patterns))
    return {
        "danger": sorted(danger_patterns, key=lambda x: x["support"], reverse=True)[:50],
        "warning": sorted(warning_patterns, key=lambda x: x["support"], reverse=True)[:150],
        "lookback": 14,
        "min_sup": 0.03,
    }


def compute_station_stats(df: pd.DataFrame) -> dict:
    stats = {}
    df["date"] = pd.to_datetime(df["date"])
    cutoff_30d = df["date"].max() - pd.Timedelta(days=30)
    for sid in STATIONS:
        sdf = df[df["station_id"] == sid]
        if sdf.empty:
            stats[sid] = {"stress_rate_30d": 0.1, "stress_rate_total": 0.1}
            continue
        total_rate = float(sdf[TARGET_COL].mean()) if TARGET_COL in sdf.columns else 0.1
        recent = sdf[sdf["date"] >= cutoff_30d]
        recent_rate = float(recent[TARGET_COL].mean()) if (TARGET_COL in recent.columns and len(recent) > 0) else total_rate
        stats[sid] = {
            "stress_rate_30d": round(recent_rate, 4),
            "stress_rate_total": round(total_rate, 4),
        }
    return stats


def main():
    parser = argparse.ArgumentParser(description="Export SaltySeq model artifacts to demo backend")
    parser.add_argument("--data_path", default="./output/merged_final.csv", help="Path to merged_final.csv")
    parser.add_argument("--model_path", default=None, help="Path to existing xgboost_model.json (optional)")
    args = parser.parse_args()

    data_path = Path(args.data_path)
    if not data_path.exists():
        logger.error("Data file not found: %s", data_path)
        raise SystemExit(1)

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data(data_path)
    train_df, _test_df = split_train(df)
    X_train, y_train = prepare_xy(train_df)

    # --- Fit scaler on train split ---
    logger.info("Fitting StandardScaler on train split...")
    scaler = StandardScaler()
    scaler.fit(X_train)
    scaler_out = MODELS_DIR / "scaler.pkl"
    with open(scaler_out, "wb") as f:
        pickle.dump(scaler, f)
    logger.info("Saved scaler → %s", scaler_out)

    # --- Model ---
    if args.model_path:
        from xgboost import XGBClassifier
        logger.info("Loading model from %s", args.model_path)
        model = XGBClassifier()
        model.load_model(args.model_path)
    else:
        params = load_best_params(data_path.parent)
        X_train_scaled = scaler.transform(X_train)
        model = train_model(pd.DataFrame(X_train_scaled, columns=FEATURE_COLUMNS), y_train, params)

    model_out = MODELS_DIR / "xgboost_model.json"
    model.save_model(str(model_out))
    logger.info("Saved model → %s", model_out)

    # --- Feature columns ---
    cols_out = MODELS_DIR / "feature_columns.json"
    cols_out.write_text(json.dumps(FEATURE_COLUMNS), encoding="utf-8")
    logger.info("Saved feature_columns.json → %s", cols_out)

    # --- SPM patterns ---
    patterns = run_spm(train_df)
    patterns_out = MODELS_DIR / "spm_patterns.json"
    patterns_out.write_text(json.dumps(patterns, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved spm_patterns.json → %s", patterns_out)

    # --- Copy data ---
    data_out = DATA_DIR / "merged_final.csv"
    shutil.copy2(data_path, data_out)
    logger.info("Copied merged_final.csv → %s", data_out)

    # --- Station stats ---
    stats = compute_station_stats(df)
    stats_out = MODELS_DIR / "station_stats.json"
    stats_out.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    logger.info("Saved station_stats.json → %s", stats_out)

    logger.info("✅ Setup complete. Run: ./run.sh")


if __name__ == "__main__":
    main()
