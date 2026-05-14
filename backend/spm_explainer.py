import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
DATA_DIR = Path(__file__).parent / "data"
_TRAIN_END_DATE = "2022-12-31"

_FALLBACK_PATTERNS: list[dict] = [
    {
        "pattern": ["Salt_High|Soil_Dry|Plant_Warning", "Salt_High|Soil_Dry|Plant_DANGER"],
        "support": 816,
        "support_pct": 4.07,
        "type": "danger",
        "label_vi": "Chuỗi mặn cao + khô hạn dẫn đến NGUY HIỂM",
    },
    {
        "pattern": ["Salt_High|Soil_Wet|Plant_Safe", "Salt_High|Soil_Dry|Plant_Warning"],
        "support": 4954,
        "support_pct": 24.7,
        "type": "warning",
        "label_vi": "Mặn cao chuyển từ ướt sang khô, cây bắt đầu cảnh báo",
    },
    {
        "pattern": ["Salt_Mod|Soil_Dry|Plant_Warning", "Salt_High|Soil_Dry|Plant_DANGER"],
        "support": 612,
        "support_pct": 3.05,
        "type": "danger",
        "label_vi": "Mặn vừa sang cao + đất khô → nguy hiểm",
    },
    {
        "pattern": ["Salt_Low|Soil_Wet|Plant_Safe", "Salt_Mod|Soil_Wet|Plant_Warning"],
        "support": 2100,
        "support_pct": 10.5,
        "type": "warning",
        "label_vi": "Mặn tăng dần từ thấp → vừa, cây bắt đầu bị ảnh hưởng",
    },
    {
        "pattern": ["Salt_High|Soil_Dry|Plant_DANGER"],
        "support": 1203,
        "support_pct": 6.0,
        "type": "danger",
        "label_vi": "Mặn cao + đất khô: cây trong tình trạng nguy hiểm",
    },
]


def load_patterns() -> dict:
    path = MODELS_DIR / "spm_patterns.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to load spm_patterns.json: %s", e)
    return {
        "danger": [p for p in _FALLBACK_PATTERNS if p["type"] == "danger"],
        "warning": [p for p in _FALLBACK_PATTERNS if p["type"] == "warning"],
        "lookback": 14,
        "min_sup": 0.03,
    }


def _normalize_station_id(df):
    if "station_id" not in df.columns and "location_id" in df.columns:
        return df.rename(columns={"location_id": "station_id"})
    return df


def _safe_float(value, default: float | None = None) -> float | None:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=1)
def _load_dataframe():
    import pandas as pd

    csv_path = DATA_DIR / "merged_final.csv"
    df = _normalize_station_id(pd.read_csv(csv_path))
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


@lru_cache(maxsize=1)
def _compute_token_stats() -> dict:
    df = _load_dataframe()
    train_df = df
    if "date" in df.columns:
        train_df = df[df["date"] <= _TRAIN_END_DATE]
        if train_df.empty:
            train_df = df

    def _quantiles(series, q1=0.33, q2=0.66):
        s = series.replace([float("inf"), float("-inf")], float("nan")).dropna()
        if s.empty:
            return None, None
        return float(s.quantile(q1)), float(s.quantile(q2))

    def _quantile(series, q=0.5):
        s = series.replace([float("inf"), float("-inf")], float("nan")).dropna()
        if s.empty:
            return None
        return float(s.quantile(q))

    stats = {
        "sal_q1": None,
        "sal_q2": None,
        "soil_q50": None,
        "temp_q1": None,
        "temp_q2": None,
        "rain_p80": 0.0,
        "temp_col": "temp_mean" if "temp_mean" in train_df.columns else "lst",
    }

    if "salinity_psu" in train_df.columns:
        stats["sal_q1"], stats["sal_q2"] = _quantiles(train_df["salinity_psu"], 0.33, 0.66)
    if "soil_moisture_surface" in train_df.columns:
        stats["soil_q50"] = _quantile(train_df["soil_moisture_surface"], 0.50)
    if stats["temp_col"] in train_df.columns:
        stats["temp_q1"], stats["temp_q2"] = _quantiles(train_df[stats["temp_col"]], 0.33, 0.66)
    if "precipitation" in train_df.columns:
        non_zero = train_df.loc[train_df["precipitation"] > 0, "precipitation"]
        stats["rain_p80"] = float(non_zero.quantile(0.80)) if not non_zero.empty else 0.0

    return stats


def _label_salinity(psu: float, q1: float | None, q2: float | None) -> str:
    if q1 is None or q2 is None:
        return "Salt_Mid"
    if psu < q1:
        return "Salt_Low"
    if psu < q2:
        return "Salt_Mid"
    return "Salt_High"


def _label_moisture(sm: float, q50: float | None) -> str:
    threshold = q50 if q50 is not None else 0.25
    return "Soil_Dry" if sm < threshold else "Soil_Wet"


def _label_temp(temp: float, q1: float | None, q2: float | None) -> str:
    if q1 is None or q2 is None:
        return "Temp_Mild"
    if temp < q1:
        return "Temp_Cool"
    if temp < q2:
        return "Temp_Mild"
    return "Temp_Hot"


def _label_rain(precip: float, p80: float) -> str:
    if precip <= 0:
        return "Rain_None"
    return "Rain_Light" if precip < max(p80, 1e-6) else "Rain_Heavy"


def get_state(
    salinity_psu: float,
    soil_moisture_surface: float,
    temp_value: float,
    precipitation: float,
    stats: dict,
) -> str:
    s = _label_salinity(salinity_psu, stats.get("sal_q1"), stats.get("sal_q2"))
    m = _label_moisture(soil_moisture_surface, stats.get("soil_q50"))
    t = _label_temp(temp_value, stats.get("temp_q1"), stats.get("temp_q2"))
    r = _label_rain(precipitation, stats.get("rain_p80", 0.0))
    return f"{s}|{m}|{t}|{r}"


def contains_pattern(sequence: list[str], pattern: list[str]) -> bool:
    it = iter(sequence)
    return all(state in it for state in pattern)


def get_history_sequence(station_id: str, date_str: str, data_df, lookback: int = 14) -> list[str]:
    import pandas as pd

    station_df = data_df[data_df["station_id"] == station_id].copy()
    station_df["date"] = pd.to_datetime(station_df["date"])
    query_date = pd.to_datetime(date_str)
    window = station_df[station_df["date"] < query_date].sort_values("date").tail(lookback)

    stats = _compute_token_stats()
    temp_col = stats.get("temp_col", "temp_mean")

    states = []
    for _, row in window.iterrows():
        sal = _safe_float(row.get("salinity_psu"), 5.0) or 5.0
        sm = _safe_float(row.get("soil_moisture_surface"), 0.3) or 0.3
        temp_val = _safe_float(row.get(temp_col), None)
        if temp_val is None and temp_col != "lst":
            temp_val = _safe_float(row.get("lst"), 0.0)
        precip = _safe_float(row.get("precipitation"), 0.0) or 0.0
        states.append(get_state(sal, sm, temp_val or 0.0, precip, stats))
    return states


def _make_label_vi(pattern: list[str]) -> str:
    has_danger = any("Plant_DANGER" in s for s in pattern)
    has_salt_high = any("Salt_High" in s for s in pattern)
    has_dry = any("Soil_Dry" in s for s in pattern)
    parts = []
    if has_salt_high:
        parts.append("mặn cao")
    if has_dry:
        parts.append("khô hạn")
    suffix = "NGUY HIỂM" if has_danger else "cảnh báo"
    base = " + ".join(parts) if parts else "bất thường"
    return f"Chuỗi {base} → {suffix}"


def match_patterns(station_id: str, date_str: str, top_k: int = 5) -> list[dict]:
    csv_path = DATA_DIR / "merged_final.csv"
    if not csv_path.exists():
        return _FALLBACK_PATTERNS[:top_k]

    try:
        import pandas as pd
        df = _load_dataframe()
        sequence = get_history_sequence(station_id, date_str, df)
    except Exception as e:
        logger.warning("Could not build SPM sequence: %s", e)
        return _FALLBACK_PATTERNS[:top_k]

    if not sequence:
        return _FALLBACK_PATTERNS[:top_k]

    patterns = load_patterns()
    all_patterns = patterns.get("danger", []) + patterns.get("warning", [])

    all_matched = []
    for p in all_patterns:
        pat = p.get("pattern", [])
        if pat and contains_pattern(sequence, pat):
            all_matched.append({
                "pattern": pat,
                "support": p.get("support", 0),
                "support_pct": p.get("support_pct", 0.0),
                "type": p.get("type", "warning"),
                "label_vi": p.get("label_vi") or _make_label_vi(pat),
                "len": len(pat)
            })

    # Ưu tiên các chuỗi DÀI NHẤT trước (vì nó giải thích chính xác nhất lịch sử và tiến trình)
    all_matched.sort(key=lambda x: (x["len"], x["support"]), reverse=True)

    # Lọc bỏ các chuỗi con (subsequences) để tránh trùng lặp hiển thị
    # Ví dụ: nếu đã chọn [A -> A -> A], thì sẽ bỏ qua [A -> A] và [A]
    maximal_matched = []
    for m in all_matched:
        pat = m["pattern"]
        # Kiểm tra xem pat này có phải là chuỗi con của bất kỳ chuỗi nào đã được duyệt chưa?
        is_sub = any(contains_pattern(sel["pattern"], pat) for sel in maximal_matched)
        if not is_sub:
            # Gỡ bỏ "len" key để tránh gửi dữ liệu thừa xuống frontend
            clean_m = {k: v for k, v in m.items() if k != "len"}
            maximal_matched.append(clean_m)
            if len(maximal_matched) >= top_k:
                break

    # Sắp xếp lại lần cuối: Ưu tiên DANGER, sau đó đến mức độ phổ biến (support)
    maximal_matched.sort(key=lambda x: (x["type"] == "danger", x["support"]), reverse=True)

    return maximal_matched if maximal_matched else _FALLBACK_PATTERNS[:top_k]


def build_spm_sequence_string(station_id: str, date_str: str, lookback: int = 3) -> str:
    csv_path = DATA_DIR / "merged_final.csv"
    if not csv_path.exists():
        return ""

    try:
        import pandas as pd
        df = _load_dataframe()
        sequence = get_history_sequence(station_id, date_str, df, lookback=lookback)
    except Exception as e:
        logger.warning("Could not build SPM sequence: %s", e)
        return ""

    if len(sequence) < lookback:
        return ""
    return " -> ".join(sequence[-lookback:])
