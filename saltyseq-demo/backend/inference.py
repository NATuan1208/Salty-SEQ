import json
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

MODELS_DIR = Path(__file__).parent / "models"

FEATURE_COLUMNS: list[str] = [
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

_FEATURE_TOP10_BASE: list[dict] = [
    {"feature": "ndvi_tendency",          "importance": 245.1},
    {"feature": "ndvi",                   "importance": 103.0},
    {"feature": "lat",                    "importance":  92.2},
    {"feature": "lon",                    "importance":  80.0},
    {"feature": "ndvi_lag_1",             "importance":  54.9},
    {"feature": "distance_to_estuary_km", "importance":  53.8},
    {"feature": "lst_ndvi_ratio",         "importance":  38.3},
    {"feature": "ndvi_lag_7",             "importance":  37.4},
    {"feature": "day_of_year",            "importance":  27.3},
    {"feature": "salinity_7d_median",     "importance":  26.8},
]


@lru_cache(maxsize=1)
def load_artifacts() -> tuple:
    """Return (model, scaler, feature_columns). model=None when file absent."""
    model_path = MODELS_DIR / "xgboost_model.json"
    scaler_path = MODELS_DIR / "scaler.pkl"
    cols_path = MODELS_DIR / "feature_columns.json"

    if not model_path.exists():
        return None, None, FEATURE_COLUMNS

    try:
        import xgboost as xgb
        model = xgb.XGBClassifier()
        model.load_model(str(model_path))
    except Exception:
        return None, None, FEATURE_COLUMNS

    scaler = None
    if scaler_path.exists():
        with open(scaler_path, "rb") as f:
            scaler = pickle.load(f)

    cols = FEATURE_COLUMNS
    if cols_path.exists():
        try:
            cols = json.loads(cols_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return model, scaler, cols


def predict(features: dict) -> dict:
    model, scaler, cols = load_artifacts()

    if model is None:
        return {"probability": mock_predict(features), "mock": True}

    X = np.array([[features.get(c, np.nan) for c in cols]], dtype=float)
    # fill NaN with 0 as median proxy (real median embedded in scaler mean)
    X = np.where(np.isnan(X), 0.0, X)

    if scaler is not None:
        X = scaler.transform(X)

    prob = float(model.predict_proba(X)[0, 1])
    return {"probability": prob, "mock": False}


def mock_predict(features: dict) -> float:
    sal = float(features.get("salinity_psu", 5.0))
    ndvi = float(features.get("ndvi", 0.4))
    ndvi_t = float(features.get("ndvi_tendency", 0.0))
    score = (sal / 32.0) * 0.5 + (1 - ndvi) * 0.3 + (-ndvi_t * 10) * 0.2
    return float(min(max(score, 0.0), 1.0))


def get_label_and_confidence(probability: float) -> tuple[str, str]:
    if probability >= 0.6:
        label = "DANGER"
        confidence = "HIGH" if probability >= 0.75 else "MEDIUM"
    elif probability >= 0.35:
        label = "WARNING"
        confidence = "MEDIUM"
    else:
        label = "SAFE"
        confidence = "HIGH" if probability < 0.2 else "MEDIUM"
    return label, confidence


def get_feature_top10(features: dict) -> list[dict]:
    return [
        {**item, "value": features.get(item["feature"])}
        for item in _FEATURE_TOP10_BASE
    ]

def generate_recommendations(features: dict, label: str) -> list[str]:
    recs = []
    sal = features.get("salinity_psu", 0)
    ndvi_t = features.get("ndvi_tendency", 0)
    
    try: sal = float(sal) if sal is not None else 0.0
    except: sal = 0.0
    
    try: ndvi_t = float(ndvi_t) if ndvi_t is not None else 0.0
    except: ndvi_t = 0.0

    if label == "DANGER":
        if sal > 4.0:
            recs.append("Độ mặn mương/sông ở mức rất cao (>4 PSU), tiến hành đóng cống ngăn mặn lập tức.")
        elif sal > 2.0:
            recs.append("Độ mặn vượt mức an toàn sinh lý của cây, ngừng bơm nước vào đồng.")
        if ndvi_t < -0.02:
            recs.append("Cây cối (NDVI) đang suy giảm thấy rõ, nên giảm stress cây bằng các loại vi lượng phun lá (không dùng qua rễ nếu khô hạn).")
        recs.append("Ưu tiên dồn nước ngọt dự trữ (ao, mương tù) phục vụ tưới tiêu cầm chừng tối thiểu trong 72h tới.")
    elif label == "WARNING":
        if sal > 2.0:
            recs.append("Phát hiện có xâm nhập mặn (>2 PSU) đi qua gần khu vực trạm, đặc biệt chú ý nếu có ý định sử dụng nguồn nước tưới.")
        else:
            recs.append("Sức chịu đựng của cây giảm do thời tiết (mặc dù độ mặn không quá cao), theo dõi sức khỏe cây để bổ sung nước/hạ nhiệt.")
        if ndvi_t < 0:
            recs.append("Xu suất tổng hợp diệp lục chững lại, cân nhắc giản cách ngày tưới tiêu.")
        recs.append("Kiểm tra nước thủy đạo, đo mặn cầm tay 2 lần/tuần nếu lấy nước mặt.")
    else:
        recs.append("Khu vực canh tác đang ở ngưỡng An Toàn ổn định.")
        recs.append("Duy trì lịch thời vụ canh tác và bổ sung dinh dưỡng theo kế hoạch định kỳ.")
        if sal < 1.0:
            recs.append("Tranh thủ mở cống lấy nước ngọt tự nhiên từ hệ thống khi mặn còn chưa vào sâu.")
            
    return recs
