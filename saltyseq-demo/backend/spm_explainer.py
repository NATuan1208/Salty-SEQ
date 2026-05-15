import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent / "models"
DATA_DIR = Path(__file__).parent / "data"

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


def _label_salinity(psu: float) -> str:
    if psu < 2:
        return "Salt_Low"
    if psu < 4:
        return "Salt_Mod"
    return "Salt_High"


def _label_moisture(sm: float) -> str:
    return "Soil_Dry" if sm < 0.25 else "Soil_Wet"


def _label_stress(css: float) -> str:
    if css < 0.4:
        return "Plant_Safe"
    if css < 0.7:
        return "Plant_Warning"
    return "Plant_DANGER"


def get_state(
    salinity_psu: float,
    soil_moisture_surface: float,
    crop_stress_score: Optional[float] = None,
) -> str:
    s = _label_salinity(salinity_psu)
    m = _label_moisture(soil_moisture_surface)
    if crop_stress_score is None:
        crop_stress_score = min((salinity_psu / 32.0) * 0.8, 1.0)
    p = _label_stress(crop_stress_score)
    return f"{s}|{m}|{p}"


def contains_pattern(sequence: list[str], pattern: list[str]) -> bool:
    it = iter(sequence)
    return all(state in it for state in pattern)


def get_history_sequence(station_id: str, date_str: str, data_df) -> list[str]:
    import pandas as pd

    station_df = data_df[data_df["station_id"] == station_id].copy()
    station_df["date"] = pd.to_datetime(station_df["date"])
    query_date = pd.to_datetime(date_str)
    window = station_df[station_df["date"] < query_date].sort_values("date").tail(14)

    states = []
    for _, row in window.iterrows():
        sal = float(row.get("salinity_psu", 5.0) or 5.0)
        sm = float(row.get("soil_moisture_surface", 0.3) or 0.3)
        is_stress = int(row.get("is_stress_event", 0) or 0)
        css = 0.8 if is_stress else None
        states.append(get_state(sal, sm, css))
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
        df = pd.read_csv(csv_path)
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
