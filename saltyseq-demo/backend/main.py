import json
import logging
import math
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.database import init_db, save_prediction, get_history, delete_prediction, clear_history
from backend.inference import load_artifacts, predict, get_label_and_confidence, get_feature_top10, generate_recommendations, generate_explanation
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


def _coerce_float(value, fallback: float | None = None) -> float | None:
    try:
        if value is None:
            return fallback
        number = float(value)
        if math.isnan(number):
            return fallback
        return number
    except (TypeError, ValueError):
        return fallback


def _is_missing(value) -> bool:
    try:
        return value is None or math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def _trend_default_features(station_id: str, date: str) -> dict:
    """Deterministic demo fallback used when merged_final.csv is unavailable."""
    features = _default_features(station_id, date)
    dt = datetime.strptime(date, "%Y-%m-%d")
    info = STATIONS[station_id]
    seasonal = math.sin((dt.timetuple().tm_yday - 35) / 365 * 2 * math.pi)
    coastal = max(0.0, 1.0 - info["distance_to_estuary_km"] / 45.0)
    salinity = 6.0 + 15.0 * max(seasonal, 0) + 7.0 * coastal
    ndvi = 0.64 - 0.16 * max(seasonal, 0) - 0.06 * coastal
    features.update({
        "salinity_psu": round(salinity, 3),
        "salinity_7d_avg": round(salinity * 0.96, 3),
        "salinity_7d_median": round(salinity * 0.94, 3),
        "salinity_tendency": round(0.02 * seasonal, 4),
        "ndvi": round(ndvi, 4),
        "ndvi_7d_avg": round(ndvi + 0.01, 4),
        "ndvi_lag_1": round(ndvi + 0.004, 4),
        "ndvi_lag_7": round(ndvi + 0.018, 4),
        "ndvi_tendency": round(-0.006 * max(seasonal, 0), 5),
        "lst": round(31.0 + 5.0 * max(seasonal, 0), 2),
    })
    features["lst_ndvi_ratio"] = round(features["lst"] / max(features["ndvi"], 0.05), 3)
    return features


def _trend_point(station_id: str, station_name: str, date: str, features: dict) -> dict:
    pred = predict(features)
    probability = _coerce_float(pred.get("probability"), 0.0) or 0.0
    label, _confidence = get_label_and_confidence(probability)
    return {
        "station_id": station_id,
        "station_name": station_name,
        "date": date,
        "salinity_psu": _coerce_float(features.get("salinity_psu")),
        "ndvi": _coerce_float(features.get("ndvi")),
        "stress_probability": probability,
        "label": label,
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


@app.get("/api/trends")
def api_get_trends(date: str, days: int = 30, station_id: str | None = None) -> dict:
    if days not in (7, 30, 90):
        raise HTTPException(status_code=400, detail="days must be one of 7, 30, or 90")
    if station_id is not None and station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="Station not found")

    try:
        end_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="date must use YYYY-MM-DD")

    start_date = end_date - timedelta(days=days - 1)
    station_ids = [station_id] if station_id else list(STATIONS.keys())
    series_by_station = {
        sid: {
            "station_id": sid,
            "station_name": STATIONS[sid]["name"],
            "points": [],
        }
        for sid in station_ids
    }

    csv_path = DATA_DIR / "merged_final.csv"
    if csv_path.exists():
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
            df = df[
                (df["station_id"].isin(station_ids))
                & (df["date"] >= start_date)
                & (df["date"] <= end_date)
            ].sort_values(["station_id", "date"])

            for _idx, row in df.iterrows():
                sid = row["station_id"]
                features = {k: row.get(k) for k in FEATURE_COLUMNS}
                for key, value in _default_features(sid, row["date"].isoformat()).items():
                    if _is_missing(features.get(key)):
                        features[key] = value
                series_by_station[sid]["points"].append(
                    _trend_point(sid, STATIONS[sid]["name"], row["date"].isoformat(), features)
                )
        except Exception as e:
            logger.warning("Failed to read trend CSV for %s/%s: %s", station_id or "all", date, e)

    # Fill missing dates so the chart remains useful in demo mode or sparse CSV ranges.
    for sid in station_ids:
        existing = {p["date"] for p in series_by_station[sid]["points"]}
        for offset in range(days):
            dt = start_date + timedelta(days=offset)
            ds = dt.isoformat()
            if ds not in existing:
                features = _trend_default_features(sid, ds)
                series_by_station[sid]["points"].append(
                    _trend_point(sid, STATIONS[sid]["name"], ds, features)
                )
        series_by_station[sid]["points"].sort(key=lambda p: p["date"])

    return {
        "date": date,
        "days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "series": list(series_by_station.values()),
    }


@app.post("/api/predict")
def api_predict(req: PredictRequest) -> dict:
    if req.station_id not in STATIONS:
        raise HTTPException(status_code=404, detail="Station not found")

    result = predict(req.features)
    probability = result["probability"]
    mock = result["mock"]

    label, confidence = get_label_and_confidence(probability)
    feature_top10 = get_feature_top10(req.features)
    explanation = generate_explanation(req.features, probability, label)
    matched_patterns = match_patterns(req.station_id, req.date)
    recommendations = generate_recommendations(req.features, label)

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
        "threshold": 0.05,
        "risk_thresholds": {"warning": 0.05, "danger": 0.15},
        "matched_patterns": matched_patterns,
        "feature_top10": feature_top10,
        "explanation": explanation,
        "mock": mock,
        "recommendations": recommendations
    }


@app.get("/api/history")
def api_get_history() -> list[dict]:
    return get_history(5)


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
