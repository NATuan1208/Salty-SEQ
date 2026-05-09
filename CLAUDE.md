# SaltySeq Demo — Project Context for Claude Code

## 1. Dự án là gì?

**SaltySeq** là hệ thống dự báo crop stress (căng thẳng cây trồng do xâm nhập mặn) tại 5 trạm quan trắc tỉnh **Bến Tre, ĐBSCL**, giai đoạn 2015–2025. Hệ thống kết hợp Sequential Pattern Mining (PrefixSpan) + XGBoost. Đây là **web demo** phục vụ bảo vệ luận văn trước hội đồng giáo sư — ưu tiên **frontend đẹp, tương tác động**.

---

## 2. Tech Stack — KHÔNG được thay đổi

```
Backend  : FastAPI (Python) — chạy port 8000
Frontend : React 18 (CDN, single file index.html) — served bởi FastAPI
DB       : SQLite (file local, CRUD prediction history)
Scheduler: APScheduler (BackgroundScheduler, tích hợp vào FastAPI startup)
Model    : XGBoost (file JSON) + StandardScaler (pickle)
Deployment: Local only — localhost:8000
```

Phục vụ frontend bằng `StaticFiles` của FastAPI. **Không cần separate dev server.**

---

## 3. Cấu trúc thư mục — PHẢI tuân theo

```
saltyseq-demo/
├── CLAUDE.md                  ← file này
├── setup_model.py             ← user chạy để export model từ Jupyter
├── requirements.txt
├── run.sh
├── backend/
│   ├── __init__.py
│   ├── main.py                ← FastAPI app entry point
│   ├── inference.py           ← load model, predict
│   ├── spm_explainer.py       ← match SPM patterns từ history data
│   ├── database.py            ← SQLite CRUD (prediction history)
│   ├── scheduler.py           ← APScheduler daily pipeline
│   ├── models/                ← chứa xgboost_model.json, scaler.pkl, spm_patterns.json, station_stats.json
│   │   └── .gitkeep
│   └── data/
│       └── merged_final.csv   ← user copy vào đây (20,090 rows)
└── frontend/
    └── index.html             ← React SPA toàn bộ
```

---

## 4. Dữ liệu đầu vào Model — 46 features, ĐÚNG THỨ TỰ này

```python
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
TARGET_COL = "is_stress_event"      # binary: 0/1
TRAIN_END  = "2022-12-31"
SCALER     = StandardScaler()       # phải apply scaler TRƯỚC khi đưa vào XGBoost
```

**Model performance (Optuna-tuned XGBoost):**
- Test PR-AUC = **0.974**, F2-score = **0.925**, Recall = **0.939**, Precision = **0.874**
- `scale_pos_weight = 8.946` (class imbalance ~10% positive)
- Decision threshold = 0.5

---

## 5. Metadata 5 Trạm quan trắc

```python
STATIONS = {
    "BT_BaTri":     {"name": "Ba Tri",      "lat": 10.0355, "lon": 106.6041, "distance_to_estuary_km": 22.5},
    "BT_BinhDai":   {"name": "Bình Đại",    "lat": 10.1499, "lon": 106.7905, "distance_to_estuary_km":  8.3},
    "BT_ChauThanh": {"name": "Châu Thành",  "lat": 10.2499, "lon": 106.4314, "distance_to_estuary_km": 38.1},
    "BT_GiongTrom": {"name": "Giồng Trôm",  "lat": 10.1009, "lon": 106.4736, "distance_to_estuary_km": 29.6},
    "BT_ThanhPhu":  {"name": "Thạnh Phú",   "lat":  9.9049, "lon": 106.5921, "distance_to_estuary_km":  5.2},
}
# Thạnh Phú và Bình Đại gần cửa biển nhất → salinity cao nhất → stress rate cao nhất
```

---

## 6. SPM Pattern Architecture

**Discretization logic** (áp dụng lên từng ngày trong 14-day lookback window):
```python
def label_salinity(psu):   # "S_Lab"
    if psu < 2:  return "Salt_Low"
    if psu < 4:  return "Salt_Mod"
    return "Salt_High"

def label_moisture(sm):    # "M_Lab"
    return "Soil_Dry" if sm < 0.25 else "Soil_Wet"

def label_stress(css):     # "P_Lab"  (crop_stress_score)
    if css < 0.4: return "Plant_Safe"
    if css < 0.7: return "Plant_Warning"
    return "Plant_DANGER"

State = f"{S_Lab}|{M_Lab}|{P_Lab}"
# Ví dụ: "Salt_High|Soil_Dry|Plant_Warning"
```

**Kết quả từ PrefixSpan** (LOOKBACK=14, MIN_SUP=0.03):
- 939 frequent patterns tổng
- **41 danger-ending patterns** (kết thúc bằng `Plant_DANGER`)
- **152 warning-ending patterns** (kết thúc bằng `Plant_Warning`)

**File `backend/models/spm_patterns.json`** (generated bởi setup_model.py):
```json
{
  "danger": [{"support": 816, "pattern": ["Salt_High|Soil_Dry|Plant_Warning", "Salt_High|Soil_Dry|Plant_DANGER"], "type": "danger"}, ...],
  "warning": [{"support": 4954, "pattern": ["Salt_High|Soil_Wet|Plant_Safe", "Salt_High|Soil_Dry|Plant_Warning"], "type": "warning"}, ...],
  "lookback": 14,
  "min_sup": 0.03
}
```

**SPM matching tại inference time:**
- Lấy 14 ngày trước ngày query từ `merged_final.csv` cho station đó
- Tính State cho từng ngày
- Check `contains_pattern(sequence, pattern)` — subsequence matching (không cần contiguous)
- Trả về top-5 matched patterns (ưu tiên danger > warning, sort by support)

---

## 7. API Contract — FastAPI endpoints

```
GET  /api/stations                     → list 5 stations + current stress status
GET  /api/data/{station_id}/{date}     → pre-fill 46 features từ merged_final.csv
POST /api/predict                      → XGBoost inference
     Body: {station_id, date, features: {feature_name: value, ...}}
     Response: {probability, label, confidence, matched_patterns, feature_top10}

GET  /api/history                      → list prediction log (SQLite)
POST /api/history                      → save prediction result
DELETE /api/history/{id}               → delete record

GET  /api/pipeline/status              → {last_run, next_run, status, records_added}
POST /api/pipeline/run                 → trigger manual run

GET  /                                 → serve frontend/index.html
```

**POST /api/predict response schema:**
```json
{
  "probability": 0.87,
  "label": "DANGER",          // "DANGER" | "WARNING" | "SAFE"
  "confidence": "HIGH",       // "HIGH" | "MEDIUM" | "LOW"
  "threshold": 0.5,
  "matched_patterns": [
    {
      "pattern": ["Salt_High|Soil_Dry|Plant_Warning", "Salt_High|Soil_Dry|Plant_DANGER"],
      "support": 816,
      "support_pct": 4.07,
      "type": "danger",
      "label_vi": "Chuỗi mặn cao + khô hạn dẫn đến NGUY HIỂM"
    }
  ],
  "feature_top10": [
    {"feature": "ndvi_tendency", "importance": 245.1, "value": -0.032},
    ...
  ],
  "mock": false               // true nếu model file chưa có → demo mode
}
```

**Label logic:**
```python
if probability >= 0.6:    label = "DANGER",  confidence = "HIGH" if prob >= 0.75 else "MEDIUM"
elif probability >= 0.35: label = "WARNING", confidence = "MEDIUM"
else:                     label = "SAFE",    confidence = "HIGH" if prob < 0.2 else "MEDIUM"
```

---

## 8. Database Schema (SQLite)

```sql
CREATE TABLE predictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    station_id  TEXT NOT NULL,
    station_name TEXT NOT NULL,
    date        TEXT NOT NULL,
    probability REAL NOT NULL,
    label       TEXT NOT NULL,
    confidence  TEXT NOT NULL,
    features_json TEXT,
    patterns_json TEXT
);
```

---

## 9. Scheduler Spec

```python
# APScheduler — chạy mỗi ngày 06:00 sáng
# Job: fetch Open-Meteo ERA5-Land data → preprocess → append to merged_final.csv
# Log vào: backend/data/pipeline_runs.log
# Ghi status vào: backend/data/pipeline_status.json
{
  "last_run": "2026-05-09T06:00:00",
  "status": "success",           // "success" | "failed" | "running" | "never"
  "records_added": 5,
  "next_run": "2026-05-10T06:00:00",
  "error": null
}
```

**Scheduler job chỉ cần log + update status file.** Actual pipeline code (GEE + Open-Meteo) không cần implement đầy đủ — gọi placeholder function có try/except, log thành công/thất bại.

---

## 10. Mock Mode

Nếu `backend/models/xgboost_model.json` không tồn tại:
- Backend trả về **mock prediction** với `"mock": true`
- Probability được tính từ công thức đơn giản dựa trên salinity + ndvi
- Frontend hiển thị badge "⚠️ DEMO MODE — model chưa được load"
- Cho phép demo flow đầy đủ mà không cần model thật

```python
def mock_predict(features: dict) -> float:
    sal = features.get("salinity_psu", 5.0)
    ndvi = features.get("ndvi", 0.4)
    ndvi_t = features.get("ndvi_tendency", 0.0)
    score = (sal / 32.0) * 0.5 + (1 - ndvi) * 0.3 + (-ndvi_t * 10) * 0.2
    return min(max(score, 0.0), 1.0)
```

---

## 11. Feature Importance (top 10) — dùng cho display

Từ `feature_importance.csv`, top 10 theo XGBoost gain score:
```
1. ndvi_tendency          245.1  (vegetation trend)
2. ndvi                   103.0  (current health)
3. lat                     92.2  (geographic proxy)
4. lon                     80.0  (geographic proxy)
5. ndvi_lag_1              54.9  (recent change)
6. distance_to_estuary_km  53.8  (salinity exposure)
7. lst_ndvi_ratio          38.3  (heat-vegetation stress)
8. ndvi_lag_7              37.4  (weekly trend)
9. day_of_year             27.3  (seasonal cycle)
10. salinity_7d_median     26.8  (sustained salinity)
```

---

## 12. Known Constraints & Pitfalls

1. **Scaler bắt buộc**: Phải `scaler.transform(X)` TRƯỚC khi predict. Nếu thiếu scaler → dùng mock_predict.
2. **Feature order QUAN TRỌNG**: XGBoost JSON model giả định features đúng thứ tự như FEATURE_COLUMNS.
3. **NaN handling**: Dùng `ffill().bfill()` rồi `fillna(median)` cho missing features.
4. **SPM matching**: `contains_pattern` dùng subsequence matching (dùng `iter`, không cần contiguous).
5. **merged_final.csv không có trong repo**: User phải copy vào `backend/data/` sau khi chạy `setup_model.py`.
6. **CORS**: FastAPI cần allow all origins vì frontend gọi API từ cùng origin nhưng served as static file.

---

## 13. Design System Frontend — "Mekong Sentinel"

**Aesthetic**: Dark oceanic + warm agricultural. Mission control cho nông nghiệp ĐBSCL. KHÔNG dùng Inter/Roboto/Arial/Space Grotesk.

```css
/* Color palette */
--bg-0:          #060E1B;   /* deepest dark */
--bg-1:          #0B1929;   /* main background */
--bg-2:          #0F2236;   /* card background */
--bg-3:          #162F48;   /* elevated / hover */
--border:        #1E3F5C;   /* subtle border */
--accent-gold:   #D4A843;   /* primary accent — rice/amber */
--accent-teal:   #18BFB0;   /* water / safe state */
--danger:        #E53B3B;   /* DANGER */
--warning:       #F0823C;   /* WARNING */
--safe:          #27C98A;   /* SAFE */
--text-1:        #ECF4FA;   /* primary text */
--text-2:        #7BA8C9;   /* secondary text */
--text-3:        #4D7A9E;   /* muted text */
--glow-gold:     rgba(212,168,67,0.15);
--glow-danger:   rgba(229,59,59,0.20);
--glow-safe:     rgba(39,201,138,0.15);

/* Typography — Google Fonts */
font-display:    'IM Fell English SC', serif         /* logo / hero title */
font-heading:    'Crimson Pro', serif                /* section headers */
font-data:       'JetBrains Mono', monospace         /* numbers / values */
font-body:       'Nunito', sans-serif                /* UI labels, body */
```

**Layout** — 3-column grid (desktop):
```
┌─────────────────────────────────────────────────────────┐
│  HEADER: logo | "Mekong Sentinel" | pipeline status     │
├──────────────┬──────────────────────┬───────────────────┤
│   LEFT (25%) │    CENTER (45%)      │   RIGHT (30%)     │
│              │                      │                   │
│  Leaflet Map │  Station + Date sel  │  SPM Pattern Cards│
│  5 markers   │  Feature input form  │  (top 5 matched)  │
│              │  (grouped accordion) │                   │
│  Station     │  [ANALYZE] button    │  Feature bar chart│
│  status      │                      │                   │
│  cards       │  Result: gauge +     │  Prediction       │
│              │  label + confidence  │  History table    │
└──────────────┴──────────────────────┴───────────────────┘
```

**Key UI components:**

1. **Probability Gauge**: SVG circular arc, animated từ 0% → result. Color gradient: green→orange→red theo probability. Số ở giữa đếm lên như counter animation.

2. **SPM Pattern Cards**: Mỗi card hiển thị chuỗi states như `[A] → [B] → [C]` với màu theo loại state. Badge "DANGER" / "WARNING" ở góc. Support % dưới.

3. **Station Map (Leaflet)**: OpenStreetMap tiles. 5 marker tròn, màu theo stress_rate_30d (green/orange/red). Click marker → auto-fill station selector.

4. **Feature Groups (accordion)**:
   - 🌿 Thực vật (NDVI, LST, tendencies)
   - 🌊 Độ mặn (salinity PSU, 7d stats)
   - 🌦️ Khí hậu (nhiệt độ, mưa, ET0)
   - 🪱 Đất (soil moisture, soil temp)
   - 📅 Thời gian (auto-computed từ date)

5. **Background texture**: Subtle radial gradient + SVG wave pattern ở header.

6. **Mock mode banner**: Nếu mock=true, hiển thị dải vàng "⚠️ Demo Mode: model file chưa được load — kết quả mô phỏng"
