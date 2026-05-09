# SaltySeq Demo — Mekong Sentinel

> **CS313 · UIT · HK2 2025–2026** — Web demo dự báo căng thẳng cây trồng do xâm nhập mặn tại 5 trạm quan trắc tỉnh **Bến Tre, ĐBSCL**.
> Mô hình: XGBoost (Optuna-tuned) + PrefixSpan Sequential Pattern Mining.

---

## Hiện trạng hệ thống ✅

| Thành phần | Trạng thái | Ghi chú |
|------------|-----------|---------|
| Backend FastAPI | ✅ Hoạt động | Port 8000, real XGBoost |
| XGBoost model | ✅ Loaded | `backend/models/xgboost_model.json` |
| StandardScaler | ✅ Loaded | Fit trên train split ≤ 2022-12-31 |
| CSV data | ✅ 20,090 rows | 5 trạm × 2015–2025, 46 features |
| SPM patterns | ✅ Fallback | 41 danger + 152 warning patterns |
| Frontend — Trang Dự báo | ✅ | Gauge + form 46 features + history |
| Frontend — Trang Bản đồ | ✅ | Leaflet full-screen + popup stats |
| Frontend — Trang Về dự án | ✅ | Model metrics, tech stack, features |
| Auto-load data | ✅ | Tự tải khi chọn trạm/ngày |
| Đồng bộ map click → form | ✅ | Click trạm trên map → form cập nhật |
| Pipeline scheduler | ✅ | APScheduler 06:00 daily |

**Model performance:** PR-AUC = 0.974 · F2 = 0.925 · Recall = 0.939 · Precision = 0.874

---

## Cài đặt & Chạy demo

### 1. Yêu cầu

```bash
Python 3.10+
pip install -r requirements.txt
```

### 2. Export model (lần đầu hoặc sau khi re-train)

```bash
cd saltyseq-demo
python quick_export.py
```

Script này sẽ tự động:
- Load `ML/output/models/xgboost_best_model.pkl` → lưu `backend/models/xgboost_model.json`
- Fit `StandardScaler` trên train split (≤ 2022-12-31)
- Copy & rename `location_id → station_id` trong CSV
- Tính `station_stats.json` (stress rates thực)

> **Nếu chưa có `ML/output/models/`**: script tự train lại model từ CSV.

### 3. Chạy server

```bash
cd saltyseq-demo
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Sau đó mở **http://localhost:8000** trong browser.

> Shortcut: `./run.sh` (nếu đã cấp quyền execute: `chmod +x run.sh`)

### 4. Demo nhanh (ngày có kết quả rõ ràng)

Mở http://localhost:8000 → **Trang Dự báo**:

| Trạm | Ngày | Kết quả kỳ vọng |
|------|------|-----------------|
| Ba Tri | 2020-03-15 | **99.5% DANGER** — mặn 29.6 PSU |
| Bình Đại | 2020-03-15 | **99.9% DANGER** — mặn 26.3 PSU |
| Thạnh Phú | 2020-03-15 | **96.6% DANGER** — gần cửa biển nhất |
| Châu Thành | 2020-03-15 | **0.0% SAFE** — xa cửa biển 38km |
| Giồng Trôm | 2020-03-15 | **0.0% SAFE** — NDVI cao 0.6 |
| Ba Tri | 2015-06-09 | **99.9% DANGER** — stress event thật |
| Thạnh Phú | 2024-03-15 | **0.9% SAFE** — rainy recovery |

---

## Cấu trúc thư mục

```
saltyseq-demo/
├── quick_export.py          ← Export model artifacts (dùng cái này)
├── setup_model.py           ← Export + chạy PrefixSpan (cần prefixspan pkg)
├── requirements.txt
├── run.sh
├── README.md
├── backend/
│   ├── main.py              ← FastAPI app, 9 routes, StaticFiles sau routes
│   ├── inference.py         ← load_artifacts() @lru_cache, predict(), mock_predict()
│   ├── spm_explainer.py     ← match_patterns(), 14-day lookback, subsequence match
│   ├── database.py          ← SQLite CRUD prediction history
│   ├── scheduler.py         ← APScheduler 06:00 daily pipeline
│   ├── models/
│   │   ├── xgboost_model.json   ← XGBoost model (XGBClassifier.save_model)
│   │   ├── scaler.pkl           ← StandardScaler (fit on train ≤ 2022-12-31)
│   │   ├── feature_columns.json ← 46 feature names theo thứ tự
│   │   ├── spm_patterns.json    ← SPM patterns (danger + warning)
│   │   └── station_stats.json   ← stress_rate_30d và stress_rate_total
│   └── data/
│       ├── merged_final.csv     ← 20,090 rows, 70+ cols, station_id column
│       ├── predictions.db       ← SQLite history (tự tạo khi chạy)
│       └── pipeline_status.json ← APScheduler run status
└── frontend/
    ├── index.html           ← Entry point React SPA
    ├── assets/              ← Ảnh nông nghiệp (hero-rice, mekong-delta, ...)
    ├── css/
    │   ├── tokens.css       ← Design tokens, màu Sage & Harvest
    │   ├── layout.css       ← Header, 3-column grid, panels
    │   └── components.css   ← Cards, gauge, patterns, history, buttons
    └── js/
        ├── config.js        ← MS namespace, API wrappers, feature groups
        └── ui/
            ├── header.js    ← Header + Toast + nav routing
            ├── map-panel.js ← Leaflet + CartoDB Voyager + station list
            ├── prediction.js ← CircularGauge + PredictionPanel + ResultCard
            ├── analysis.js  ← SpmPatterns + FeatureBars + HistoryTable
            ├── pages.js     ← MapPage (full-screen) + AboutPage
            └── app.js       ← Root App, page state, data fetching
```

---

## API Reference

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/stations` | Danh sách 5 trạm + stress rates |
| GET | `/api/data/{station_id}/{date}` | Pre-fill 46 features từ CSV |
| POST | `/api/predict` | XGBoost inference + SPM matching |
| GET | `/api/history` | Lịch sử dự báo (SQLite, 50 records) |
| DELETE | `/api/history/{id}` | Xoá 1 record |
| DELETE | `/api/history/all` | Xoá tất cả |
| GET | `/api/pipeline/status` | Trạng thái APScheduler |
| POST | `/api/pipeline/run` | Trigger manual pipeline run |

### POST `/api/predict` — Request body

```json
{
  "station_id": "BT_BaTri",
  "date": "2020-03-15",
  "features": {
    "salinity_psu": 29.6,
    "ndvi": 0.247,
    "ndvi_tendency": -0.025,
    ...
  }
}
```

### POST `/api/predict` — Response

```json
{
  "probability": 0.9949,
  "label": "DANGER",
  "confidence": "HIGH",
  "threshold": 0.5,
  "matched_patterns": [...],
  "feature_top10": [...],
  "mock": false
}
```

**Label logic:** `≥ 0.6 → DANGER`, `≥ 0.35 → WARNING`, `< 0.35 → SAFE`

---

## Mock Mode

Nếu `backend/models/xgboost_model.json` không tồn tại:
- Backend tự động chuyển sang mock mode (`mock: true`)
- Probability tính từ công thức đơn giản: `f(salinity, ndvi, ndvi_tendency)`
- Frontend hiển thị banner vàng "Demo Mode"

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI · Python 3.10+ · Uvicorn |
| ML model | XGBoost (Optuna-tuned, `scale_pos_weight=8.946`) |
| Pattern mining | PrefixSpan (SPM) · 14-day lookback · min_support=3% |
| Scaler | StandardScaler (fit on train ≤ 2022-12-31) |
| Database | SQLite (stdlib `sqlite3`, no ORM) |
| Scheduler | APScheduler BackgroundScheduler |
| Frontend | React 18 (CDN) · Babel standalone (JSX) |
| Map | Leaflet · CartoDB Voyager tiles |
| Icons | Tabler Icons webfont |
| Fonts | IM Fell English SC · Crimson Pro · JetBrains Mono · Nunito |
| Data | 5 trạm Bến Tre · 2015–2025 · 70 cols · 20,090 rows |
