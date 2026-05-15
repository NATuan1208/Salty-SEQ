import json
import pickle
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

MODELS_DIR = Path(__file__).parent / "models"
USE_GRU = True

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
        try:
            with open(scaler_path, "rb") as f:
                scaler = pickle.load(f)
        except Exception:
            scaler = None

    cols = FEATURE_COLUMNS
    if cols_path.exists():
        try:
            cols = json.loads(cols_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return model, scaler, cols


@lru_cache(maxsize=1)
def load_gru_artifacts() -> tuple:
    """Return (model, scaler, feature_columns, lookback). model=None when file absent."""
    model_path = MODELS_DIR / "gru_model.pt"
    scaler_path = MODELS_DIR / "gru_scaler.pkl"
    cols_path = MODELS_DIR / "gru_feature_columns.json"
    meta_path = MODELS_DIR / "gru_meta.json"

    if not model_path.exists():
        return None, None, FEATURE_COLUMNS, 1

    try:
        import torch
        import torch.nn as nn
    except Exception:
        return None, None, FEATURE_COLUMNS, 1

    scaler = None
    if scaler_path.exists():
        try:
            with open(scaler_path, "rb") as f:
                scaler = pickle.load(f)
        except Exception:
            scaler = None

    cols = FEATURE_COLUMNS
    if cols_path.exists():
        try:
            cols = json.loads(cols_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    lookback = 1
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            lookback = int(meta.get("lookback", 1))
        except Exception:
            lookback = 1

    def _build_model(input_size, hidden_size=64, dropout=0.1):
        class GRUClassifier(nn.Module):
            def __init__(self, input_size, hidden_size, dropout):
                super().__init__()
                self.gru = nn.GRU(input_size, hidden_size, batch_first=True)
                self.head = nn.Sequential(
                    nn.Dropout(dropout),
                    nn.Linear(hidden_size, 32),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(32, 16),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(16, 1)
                )

            def forward(self, x):
                out, _ = self.gru(x)
                out = out[:, -1, :]
                return self.head(out)

        return GRUClassifier(input_size, hidden_size, dropout)

    payload = torch.load(model_path, map_location="cpu")
    input_size = int(payload.get("input_size", len(cols)))
    hidden_size = int(payload.get("hidden_size", 64))
    dropout = float(payload.get("dropout", 0.1))

    model = _build_model(input_size, hidden_size, dropout)
    model.load_state_dict(payload["state_dict"])
    model.eval()

    return model, scaler, cols, lookback


def predict_gru(features: dict) -> float | None:
    model, scaler, cols, lookback = load_gru_artifacts()
    if model is None:
        return None

    try:
        import torch
    except Exception:
        return None

    row = np.array([[features.get(c, np.nan) for c in cols]], dtype=float)
    row = np.where(np.isnan(row), 0.0, row)

    if scaler is not None:
        row = scaler.transform(row)

    steps = max(int(lookback), 1)
    if steps == 1:
        seq = row.reshape(1, 1, -1)
    else:
        # Repeat the current row when the lookback window is larger than 1.
        seq = np.repeat(row, steps, axis=0).reshape(1, steps, -1)

    x = torch.tensor(seq, dtype=torch.float32)
    with torch.no_grad():
        logits = model(x)
        prob = torch.sigmoid(logits).item()
    return float(prob)


def predict(features: dict) -> dict:
    if USE_GRU:
        prob = predict_gru(features)
        if prob is not None:
            return {"probability": prob, "mock": False}

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
    if probability >= 0.50:
        label = "DANGER"
        confidence = "HIGH" if probability >= 0.70 else "MEDIUM"
    elif probability >= 0.30:
        label = "WARNING"
        confidence = "MEDIUM"
    else:
        label = "SAFE"
        confidence = "HIGH" if probability <= 0.20 else "MEDIUM"
    return label, confidence


def get_feature_top10(features: dict) -> list[dict]:
    return [
        {**item, "value": features.get(item["feature"])}
        for item in _FEATURE_TOP10_BASE
    ]


def _safe_float(value, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def generate_explanation(features: dict, probability: float, label: str) -> dict:
    """Build a short, user-facing reason block for a prediction."""
    sal = _safe_float(features.get("salinity_psu"), 0.0) or 0.0
    sal_7d = _safe_float(features.get("salinity_7d_avg"))
    ndvi = _safe_float(features.get("ndvi"))
    ndvi_t = _safe_float(features.get("ndvi_tendency"), 0.0) or 0.0
    ndvi_7d = _safe_float(features.get("ndvi_7d_avg"))
    dist = _safe_float(features.get("distance_to_estuary_km"))
    lst_ratio = _safe_float(features.get("lst_ndvi_ratio"))
    dry_days = _safe_float(features.get("days_without_rain"))
    precip_7d = _safe_float(features.get("precip_7d_sum"))

    drivers: list[dict] = []
    offsets: list[dict] = []

    if ndvi_t <= -0.01:
        drivers.append({
            "feature": "ndvi_tendency",
            "severity": "high",
            "text": f"NDVI đang giảm mạnh ({ndvi_t:.4f}/ngày), cây có dấu hiệu suy giảm sức khỏe.",
        })
    elif ndvi_t < 0:
        drivers.append({
            "feature": "ndvi_tendency",
            "severity": "medium",
            "text": f"NDVI có xu hướng giảm nhẹ ({ndvi_t:.4f}/ngày).",
        })
    elif ndvi_t > 0.005:
        offsets.append({
            "feature": "ndvi_tendency",
            "text": f"NDVI đang phục hồi ({ndvi_t:.4f}/ngày), giúp giảm rủi ro.",
        })

    if ndvi is not None and ndvi < 0.40:
        drivers.append({
            "feature": "ndvi",
            "severity": "high",
            "text": f"NDVI thấp ({ndvi:.3f}), thảm thực vật yếu hơn bình thường.",
        })
    elif ndvi is not None and ndvi < 0.55:
        drivers.append({
            "feature": "ndvi",
            "severity": "medium",
            "text": f"NDVI ở mức trung bình ({ndvi:.3f}), cần theo dõi thêm.",
        })
    elif ndvi is not None and ndvi >= 0.60:
        offsets.append({
            "feature": "ndvi",
            "text": f"NDVI khá tốt ({ndvi:.3f}), cây vẫn giữ độ xanh ổn định.",
        })

    if sal >= 8:
        drivers.append({
            "feature": "salinity_psu",
            "severity": "high",
            "text": f"Độ mặn cao ({sal:.2f} PSU), vượt xa ngưỡng nhạy cảm của cây trồng.",
        })
    elif sal >= 4:
        drivers.append({
            "feature": "salinity_psu",
            "severity": "medium",
            "text": f"Độ mặn đáng chú ý ({sal:.2f} PSU), có thể gây stress nếu kéo dài.",
        })
    elif sal < 2:
        offsets.append({
            "feature": "salinity_psu",
            "text": f"Độ mặn thấp ({sal:.2f} PSU), áp lực xâm nhập mặn hiện không lớn.",
        })

    if sal_7d is not None and sal_7d >= 4:
        drivers.append({
            "feature": "salinity_7d_avg",
            "severity": "medium",
            "text": f"Độ mặn trung bình 7 ngày vẫn cao ({sal_7d:.2f} PSU), rủi ro có tính kéo dài.",
        })

    if dist is not None and dist <= 10:
        drivers.append({
            "feature": "distance_to_estuary_km",
            "severity": "medium",
            "text": f"Trạm gần cửa biển ({dist:.1f} km), dễ chịu tác động khi mặn xâm nhập.",
        })
    elif dist is not None and dist >= 30:
        offsets.append({
            "feature": "distance_to_estuary_km",
            "text": f"Trạm cách cửa biển khá xa ({dist:.1f} km), giảm bớt rủi ro mặn trực tiếp.",
        })

    if lst_ratio is not None and lst_ratio >= 65:
        drivers.append({
            "feature": "lst_ndvi_ratio",
            "severity": "medium",
            "text": f"Tỷ lệ LST/NDVI cao ({lst_ratio:.1f}), gợi ý cây chịu áp lực nhiệt hoặc thiếu nước.",
        })

    if dry_days is not None and dry_days >= 10:
        drivers.append({
            "feature": "days_without_rain",
            "severity": "medium",
            "text": f"Nhiều ngày không mưa liên tiếp ({dry_days:.0f} ngày), nguy cơ khô hạn tăng.",
        })
    elif precip_7d is not None and precip_7d >= 40:
        offsets.append({
            "feature": "precip_7d_sum",
            "text": f"Lượng mưa 7 ngày khá tốt ({precip_7d:.1f} mm), có thể giảm áp lực hạn.",
        })

    if ndvi_7d is not None and ndvi is not None and ndvi < ndvi_7d - 0.02:
        drivers.append({
            "feature": "ndvi_7d_avg",
            "severity": "medium",
            "text": f"NDVI hiện tại thấp hơn trung bình 7 ngày ({ndvi:.3f} so với {ndvi_7d:.3f}).",
        })

    drivers = drivers[:4]
    offsets = offsets[:2]
    watchouts: list[dict] = []

    summary_phrases = []
    phrase_map = {
        "ndvi_tendency": "NDVI đang giảm",
        "ndvi": "NDVI thấp",
        "salinity_psu": "độ mặn cao",
        "salinity_7d_avg": "độ mặn cao kéo dài 7 ngày",
        "distance_to_estuary_km": "trạm gần cửa biển",
        "lst_ndvi_ratio": "áp lực nhiệt/thực vật cao",
        "days_without_rain": "nhiều ngày không mưa",
        "ndvi_7d_avg": "NDVI thấp hơn trung bình 7 ngày",
    }
    for item in drivers:
        phrase = phrase_map.get(item["feature"])
        if phrase and phrase not in summary_phrases:
            summary_phrases.append(phrase)

    if label == "SAFE":
        watchouts = drivers[:3]
        drivers = []
        offset_phrases = []
        offset_map = {
            "ndvi_tendency": "NDVI đang phục hồi",
            "ndvi": "NDVI còn tốt",
            "salinity_psu": "độ mặn thấp",
            "distance_to_estuary_km": "trạm cách xa cửa biển",
            "precip_7d_sum": "mưa 7 ngày hỗ trợ giảm hạn",
        }
        for item in offsets:
            phrase = offset_map.get(item["feature"])
            if phrase and phrase not in offset_phrases:
                offset_phrases.append(phrase)

        if offset_phrases:
            summary = (
                "Dự báo AN TOÀN vì các tín hiệu tổng hợp vẫn nằm trong vùng rủi ro thấp; "
                f"{', '.join(offset_phrases[:2])}."
            )
        elif watchouts:
            summary = (
                "Dự báo AN TOÀN vì hiện chưa đủ bằng chứng để chuyển sang cảnh báo. "
                "Tuy vậy vẫn cần theo dõi các tín hiệu bất lợi bên dưới."
            )
        else:
            summary = "Dự báo AN TOÀN vì các tín hiệu chính chưa cho thấy áp lực mặn, hạn hoặc suy giảm thực vật rõ rệt."
    elif summary_phrases:
        joined = ", ".join(summary_phrases[:3])
        summary = f"Nguy cơ tăng vì {joined}."
    else:
        summary = "Kết quả an toàn vì các tín hiệu chính chưa cho thấy áp lực mặn, hạn hoặc suy giảm thực vật rõ rệt."

    return {
        "summary": summary,
        "drivers": drivers,
        "watchouts": watchouts,
        "offsets": offsets,
        "score_percent": round(probability * 100, 2),
    }

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
