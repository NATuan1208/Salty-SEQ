"""Quick export: load pkl model → demo backend, xử lý location_id → station_id."""
import json, pickle, shutil, logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

ROOT      = Path(__file__).parent.parent          # poc_saltyseq/
ML_MODELS = ROOT / "ML" / "output" / "models"
DATA_SRC  = ROOT / "data" / "merged_final.csv"
DEMO_DIR  = Path(__file__).parent
MODELS_OUT = DEMO_DIR / "backend" / "models"
DATA_OUT   = DEMO_DIR / "backend" / "data"

FEATURE_COLUMNS = [
    "lat","lon","distance_to_estuary_km","ndvi","lst","ndvi_gap_days",
    "temp_max","temp_min","temp_mean","precipitation","et0","radiation",
    "wind_max","soil_moisture_surface","soil_moisture_deep","soil_temp",
    "salinity_psu","day_of_year","month","week","is_dry_season",
    "month_sin","month_cos","temp_7d_avg","ndvi_7d_avg","precip_7d_sum",
    "salinity_7d_avg","salinity_7d_avg_lag1","lst_7d_avg","soil_moisture_7d_avg",
    "ndvi_lag_1","ndvi_lag_3","ndvi_lag_7","days_without_rain",
    "moisture_deficit","moisture_deficit_7d","lst_ndvi_ratio",
    "salinity_precip_ratio","salinity_7d_median","ndvi_7d_median",
    "precip_15d_sum","precip_30d_sum","heatwave_consecutive_days",
    "salinity_tendency","ndvi_tendency","soil_moisture_tendency",
]
TARGET     = "is_stress_event"
TRAIN_END  = "2022-12-31"

STATIONS = {
    "BT_BaTri":     {"name":"Ba Tri",     "lat":10.0355,"lon":106.6041,"distance_to_estuary_km":22.5},
    "BT_BinhDai":   {"name":"Bình Đại",   "lat":10.1499,"lon":106.7905,"distance_to_estuary_km":8.3},
    "BT_ChauThanh": {"name":"Châu Thành", "lat":10.2499,"lon":106.4314,"distance_to_estuary_km":38.1},
    "BT_GiongTrom": {"name":"Giồng Trôm", "lat":10.1009,"lon":106.4736,"distance_to_estuary_km":29.6},
    "BT_ThanhPhu":  {"name":"Thạnh Phú",  "lat":9.9049, "lon":106.5921,"distance_to_estuary_km":5.2},
}

FALLBACK_PATTERNS = {
    "danger":[
        {"pattern":["Salt_High|Soil_Dry|Plant_Warning","Salt_High|Soil_Dry|Plant_DANGER"],"support":816,"support_pct":4.07,"type":"danger","label_vi":"Chuỗi mặn cao + khô hạn → NGUY HIỂM"},
        {"pattern":["Salt_Mod|Soil_Dry|Plant_Warning","Salt_High|Soil_Dry|Plant_DANGER"],"support":612,"support_pct":3.05,"type":"danger","label_vi":"Mặn vừa sang cao + đất khô → nguy hiểm"},
    ],
    "warning":[
        {"pattern":["Salt_High|Soil_Wet|Plant_Safe","Salt_High|Soil_Dry|Plant_Warning"],"support":4954,"support_pct":24.7,"type":"warning","label_vi":"Mặn cao từ ướt sang khô, cây cảnh báo"},
        {"pattern":["Salt_Low|Soil_Wet|Plant_Safe","Salt_Mod|Soil_Wet|Plant_Warning"],"support":2100,"support_pct":10.5,"type":"warning","label_vi":"Mặn tăng dần từ thấp → vừa, cây bị ảnh hưởng"},
    ],
    "lookback":14,"min_sup":0.03,
}

def main():
    MODELS_OUT.mkdir(parents=True, exist_ok=True)
    DATA_OUT.mkdir(parents=True, exist_ok=True)

    # ── 1. Load & preprocess CSV ─────────────────────────────────
    log.info("Loading %s", DATA_SRC)
    df = pd.read_csv(DATA_SRC, low_memory=False)
    df["date"] = pd.to_datetime(df["date"])

    # Rename location_id → station_id for demo compatibility
    if "location_id" in df.columns and "station_id" not in df.columns:
        df = df.rename(columns={"location_id": "station_id"})
        log.info("Renamed location_id → station_id")

    log.info("Rows: %d | Cols: %d", len(df), len(df.columns))

    # ── 2. Train split ───────────────────────────────────────────
    train = df[df["date"] <= TRAIN_END].copy()
    available = [c for c in FEATURE_COLUMNS if c in df.columns]
    missing   = [c for c in FEATURE_COLUMNS if c not in df.columns]
    if missing:
        log.warning("Missing features (will fill 0): %s", missing)

    X_train = train.reindex(columns=FEATURE_COLUMNS, fill_value=0.0).ffill().bfill().fillna(0.0)
    y_train = train[TARGET].astype(int) if TARGET in train.columns else None
    log.info("Train rows: %d | Test rows: %d", len(train), len(df) - len(train))

    # ── 3. Load XGBoost pkl, re-save as JSON ────────────────────
    xgb_pkl = ML_MODELS / "xgboost_best_model.pkl"
    if xgb_pkl.exists():
        log.info("Loading XGBoost from %s", xgb_pkl)
        import xgboost as xgb
        with open(xgb_pkl, "rb") as f:
            model = pickle.load(f)
        # Ensure it has the right features
        model_json_path = MODELS_OUT / "xgboost_model.json"
        model.save_model(str(model_json_path))
        log.info("Saved → %s", model_json_path)
    else:
        log.warning("xgboost_best_model.pkl not found — training fresh model")
        from xgboost import XGBClassifier
        model = XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.05,
            scale_pos_weight=8.946, eval_metric="logloss", random_state=42,
        )
        if y_train is not None:
            model.fit(X_train, y_train, verbose=False)
            model.save_model(str(MODELS_OUT / "xgboost_model.json"))
            log.info("Trained + saved fresh model")

    # ── 4. Scaler: use existing pkl if available ────────────────
    scaler_src = ML_MODELS / "feature_scaler.pkl"
    scaler_dst = MODELS_OUT / "scaler.pkl"
    if scaler_src.exists():
        shutil.copy2(scaler_src, scaler_dst)
        log.info("Copied scaler → %s", scaler_dst)
    else:
        log.info("Fitting new StandardScaler on train split")
        scaler = StandardScaler()
        scaler.fit(X_train)
        with open(scaler_dst, "wb") as f:
            pickle.dump(scaler, f)
        log.info("Saved scaler → %s", scaler_dst)

    # ── 5. Feature columns JSON ──────────────────────────────────
    cols_path = MODELS_OUT / "feature_columns.json"
    cols_path.write_text(json.dumps(FEATURE_COLUMNS), encoding="utf-8")
    log.info("Saved feature_columns.json")

    # ── 6. SPM patterns (fallback) ───────────────────────────────
    spm_path = MODELS_OUT / "spm_patterns.json"
    if not spm_path.exists():
        spm_path.write_text(json.dumps(FALLBACK_PATTERNS, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("Saved fallback spm_patterns.json")
    else:
        log.info("spm_patterns.json already exists — skipping")

    # ── 7. Copy merged_final.csv → backend/data/ ────────────────
    csv_dst = DATA_OUT / "merged_final.csv"
    df.to_csv(csv_dst, index=False)   # save the version with station_id
    log.info("Saved merged_final.csv → %s  (%d rows)", csv_dst, len(df))

    # ── 8. Station stats ─────────────────────────────────────────
    stats = {}
    cutoff = df["date"].max() - pd.Timedelta(days=30)
    for sid in STATIONS:
        sdf = df[df["station_id"] == sid]
        if sdf.empty:
            stats[sid] = {"stress_rate_30d": 0.10, "stress_rate_total": 0.10}
            continue
        total  = float(sdf[TARGET].mean()) if TARGET in sdf.columns else 0.1
        recent = sdf[sdf["date"] >= cutoff]
        r30 = float(recent[TARGET].mean()) if (TARGET in recent.columns and len(recent) > 0) else total
        stats[sid] = {"stress_rate_30d": round(r30,4), "stress_rate_total": round(total,4)}

    stats_path = MODELS_OUT / "station_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    log.info("Saved station_stats.json: %s", stats)

    log.info("=" * 50)
    log.info("Export complete! Run: cd saltyseq-demo && python -m uvicorn backend.main:app --port 8000 --reload")

if __name__ == "__main__":
    main()
