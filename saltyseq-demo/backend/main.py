import json
import logging
import math
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.database import init_db, save_prediction, get_history, delete_prediction, clear_history
from backend.inference import load_artifacts, predict, get_label_and_confidence, get_feature_top10
from backend.scheduler import start_scheduler, get_pipeline_status, trigger_pipeline
from backend.spm_explainer import match_patterns

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
DATA_DIR = Path(__file__).parent / "data"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

STATIONS: dict[str, dict] = {
    "BT_BaTri":     {"name": "Ba Tri",      "lat": 10.0355, "lon": 106.6041, "distance_to_estuary_km": 22.5},
    "BT_BinhDai":   {"name": "Bình Đại",    "lat": 10.1499, "lon": 106.7905, "distance_to_estuary_km":  8.3},
    "BT_ChauThanh": {"name": "Châu Thành",  "lat": 10.2499, "lon": 106.4314, "distance_to_estuary_km": 38.1},
    "BT_GiongTrom": {"name": "Giồng Trôm",  "lat": 10.1009, "lon": 106.4736, "distance_to_estuary_km": 29.6},
    "BT_ThanhPhu":  {"name": "Thạnh Phú",   "lat":  9.9049, "lon": 106.5921, "distance_to_estuary_km":  5.2},
}

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    load_artifacts()
    start_scheduler()
    yield


app = FastAPI(title="SaltySeq Demo", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Pydantic Models ───────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    station_id: str
    date: str
    features: dict


# ─── Helper ────────────────────────────────────────────────────────────────────

def _default_features(station_id: str, date: str) -> dict:
    info = STATIONS[station_id]
    dt = datetime.strptime(date, "%Y-%m-%d")
    doy = dt.timetuple().tm_yday
    month = dt.month
    week = int(dt.strftime("%W"))
    return {
        "lat": info["lat"],
        "lon": info["lon"],
        "distance_to_estuary_km": info["distance_to_estuary_km"],
        "ndvi": 0.45,
        "lst": 32.0,
        "ndvi_gap_days": 0,
        "temp_max": 35.0,
        "temp_min": 24.0,
        "temp_mean": 29.5,
        "precipitation": 5.0,
        "et0": 4.5,
        "radiation": 18.0,
        "wind_max": 3.0,
        "soil_moisture_surface": 0.28,
        "soil_moisture_deep": 0.32,
        "soil_temp": 30.0,
        "salinity_psu": 5.0,
        "day_of_year": doy,
        "month": month,
        "week": week,
        "is_dry_season": 1 if month in [1, 2, 3, 4, 12] else 0,
        "month_sin": math.sin(2 * math.pi * month / 12),
        "month_cos": math.cos(2 * math.pi * month / 12),
        "temp_7d_avg": 29.5,
        "ndvi_7d_avg": 0.45,
        "precip_7d_sum": 35.0,
        "salinity_7d_avg": 5.0,
        "salinity_7d_avg_lag1": 4.8,
        "lst_7d_avg": 32.0,
        "soil_moisture_7d_avg": 0.28,
        "ndvi_lag_1": 0.44,
        "ndvi_lag_3": 0.42,
        "ndvi_lag_7": 0.40,
        "days_without_rain": 3,
        "moisture_deficit": 0.1,
        "moisture_deficit_7d": 0.15,
        "lst_ndvi_ratio": 71.1,
        "salinity_precip_ratio": 1.0,
        "salinity_7d_median": 5.0,
        "ndvi_7d_median": 0.45,
        "precip_15d_sum": 75.0,
        "precip_30d_sum": 150.0,
        "heatwave_consecutive_days": 0,
        "salinity_tendency": 0.0,
        "ndvi_tendency": 0.0,
        "soil_moisture_tendency": 0.0,
    }


# ─── API Routes ────────────────────────────────────────────────────────────────

@app.get("/api/stations")
def api_get_stations() -> list[dict]:
    stats_path = MODELS_DIR / "station_stats.json"
    stats: dict = {}
    if stats_path.exists():
        try:
            stats = json.loads(stats_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    result = []
    for sid, info in STATIONS.items():
        s = stats.get(sid, {})
        result.append({
            "station_id": sid,
            "name": info["name"],
            "lat": info["lat"],
            "lon": info["lon"],
            "distance_to_estuary_km": info["distance_to_estuary_km"],
            "stress_rate_30d": s.get("stress_rate_30d", 0.10),
            "stress_rate_total": s.get("stress_rate_total", 0.10),
        })
    return result


@app.get("/api/data/{station_id}/{date}")
def api_get_data(station_id: str, date: str) -> dict:
    if station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="Station not found")

    csv_path = DATA_DIR / "merged_final.csv"
    if not csv_path.exists():
        return _default_features(station_id, date)

    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        row = df[(df["station_id"] == station_id) & (df["date"] == date)]
        if row.empty:
            return _default_features(station_id, date)
        record = row.iloc[0].to_dict()
        return {k: record.get(k) for k in FEATURE_COLUMNS}
    except Exception as e:
        logger.warning("Failed to read CSV for %s/%s: %s", station_id, date, e)
        return _default_features(station_id, date)


@app.post("/api/predict")
def api_predict(req: PredictRequest) -> dict:
    if req.station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="Station not found")

    result = predict(req.features)
    probability = result["probability"]
    mock = result["mock"]

    label, confidence = get_label_and_confidence(probability)
    feature_top10 = get_feature_top10(req.features)
    matched_patterns = match_patterns(req.station_id, req.date)

    save_prediction({
        "station_id": req.station_id,
        "station_name": STATIONS[req.station_id]["name"],
        "date": req.date,
        "probability": probability,
        "label": label,
        "confidence": confidence,
        "features_json": json.dumps(req.features),
        "patterns_json": json.dumps(matched_patterns),
    })

    return {
        "probability": probability,
        "label": label,
        "confidence": confidence,
        "threshold": 0.5,
        "matched_patterns": matched_patterns,
        "feature_top10": feature_top10,
        "mock": mock,
    }


@app.get("/api/history")
def api_get_history() -> list[dict]:
    return get_history(50)


@app.delete("/api/history/all")
def api_clear_history() -> dict:
    clear_history()
    return {"ok": True}


@app.delete("/api/history/{id}")
def api_delete_history(id: int) -> dict:
    if not delete_prediction(id):
        raise HTTPException(status_code=404, detail="Record not found")
    return {"ok": True}


@app.get("/api/pipeline/status")
def api_pipeline_status() -> dict:
    return get_pipeline_status()


@app.post("/api/pipeline/run")
def api_pipeline_run() -> dict:
    trigger_pipeline()
    return {"ok": True, "message": "Pipeline triggered"}


# Mount static files AFTER all API routes (FastAPI priority: routes first)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
