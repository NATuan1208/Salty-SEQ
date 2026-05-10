# BAO CAO TIEN XU LY VA FEATURE ENGINEERING (CAP NHAT)
## Du an SaltySeq - Panel time-series da vi tri

> Cap nhat sau rerun pipeline: 2026-04-06  
> Pham vi du lieu: 2015-01-01 den 2025-12-31  
> Khong gian: 5 location tai Ben Tre (panel daily)

---

## 1. Tom tat cap nhat dot nay

Ban cap nhat nay dong bo theo ban override moi cua `src/merge_preprocess.py` va ket qua rerun `python run_pipeline.py --from 4`.

Noi dung da cap nhat:

- Bo sung nhom feature nang cao (median, accumulation, tendency).
- Cap nhat thong ke output theo horizon day du 2015-2025.
- Ghi ro fix quan trong ve leakage trong `crop_stress_score` fallback.
- Dong bo so lieu split train/holdout theo artifact moi nhat.

---

## 2. Tong quan output du lieu (sau rerun)

| Tep | So dong | So cot | So location | Date range | Khoa location_id+date |
|---|---:|---:|---:|---|---|
| data/real_ndvi_lst.csv | 4522 | 9 | 5 | 2015-01-01 -> 2025-12-31 | unique |
| data/real_weather.csv | 20090 | 17 | 5 | 2015-01-01 -> 2025-12-31 | unique |
| data/real_salinity.csv | 20090 | 9 | 5 | 2015-01-01 -> 2025-12-31 | unique |
| data/merged_final.csv | 20090 | 70 | 5 | 2015-01-01 -> 2025-12-31 | unique |

Coverage theo location trong `merged_final.csv`:

- Moi location co du 4018 dong.
- Tong cong 5 location x 4018 ngay = 20090 dong.

---

## 3. Chat luong du lieu sau tien xu ly

Chi so tong quan tren `merged_final.csv`:

- Shape: 20090 x 70
- Completeness tong the: 99.6329%
- NDVI observed ratio: 22.4988%
- LST observed ratio: 4.5495%
- Nguon salinity: synthetic_proxy (100%)
- Duplicate key `location_id + date`: 0

Chi so label/anomaly:

- `is_stress_event = 1`: 2171 ban ghi (10.8064%)
- `is_salinity_spike = 1`: 3115 ban ghi
- `crop_stress_score` mean: 0.365938
- `crop_stress_score` p95: 0.695942

Ty le positive theo split artifact:

- Train 2015-2022: 10.0548%
- Holdout 2023-2025: 12.8102%

Phan bo `is_stress_event` theo nam (%):

- 2015: 0.88 ; 2016: 6.67 ; 2017: 1.75 ; 2018: 6.96
- 2019: 13.48 ; 2020: 21.09 ; 2021: 15.01 ; 2022: 14.58
- 2023: 13.26 ; 2024: 14.64 ; 2025: 10.52

Phan bo `is_stress_event` theo location (%):

- BT_ThanhPhu: 12.17
- BT_ChauThanh: 12.05
- BT_BaTri: 10.85
- BT_GiongTrom: 10.75
- BT_BinhDai: 8.21

---

## 4. Override improvements trong feature engineering

Cap nhat chinh da dua vao code:

- Nhom smoothing robust:
	- `salinity_7d_median`
	- `ndvi_7d_median`
- Nhom accumulation trend:
	- `precip_15d_sum`
	- `precip_30d_sum`
- Nhom event stress:
	- `heatwave_consecutive_days`
- Nhom tendency:
	- `salinity_tendency`
	- `ndvi_tendency`
	- `soil_moisture_tendency`

Tinh trang hien tai:

- Tat ca feature tren da co mat trong `merged_final.csv`.
- Tong so cot tang tu 61 len 70.

---

## 5. Finding da sua trong dot nay (approved fix)

### Fix leakage fallback trong `crop_stress_score`

Van de cu:

- Fallback max cua normalization co the dung thong ke tu `out` (co chua holdout), tao nguy co leakage.

Da sua:

- Chuyen fallback sang train-only statistics:
	- `ndvi_max`: fallback `train_ref["ndvi"].max()`
	- `salinity_max`: fallback `train_fallback_max["salinity_psu"]`
	- `soil_max`: fallback `train_fallback_max["soil_moisture_surface"]`
- Khong con fallback nao dung `out[...].max()`.

Ket qua:

- Logic normalization cua `crop_stress_score` da giu nguyen nguyen tac train-only, an toan hon cho holdout integrity.

---

## 6. Feature schema hien tai (70 cot)

Nhom cot trong `merged_final.csv`:

- Metadata panel.
- Satellite core + interpolation audit.
- Weather/soil/salinity goc.
- Time encoding.
- Rolling + lag + derived.
- Advanced features (median, accumulation, tendency, heatwave).
- Target/anomaly (`ndvi_zscore`, `is_stress_event`, `is_salinity_spike`, `crop_stress_score`).

---

## 7. Muc do san sang cho modeling

Trang thai hien tai:

- San sang cho XGBoost va PrefixSpan phase tiep theo.
- Split theo thoi gian da dong bo day du (train/holdout/folds).
- Key panel va date range dat dung policy khong random split.

Luu y van hanh:

- Giu nguyen ky luat temporal-safe: khong random split, khong dung thong ke full-horizon cho normalization train.
- Cac NaN o dau chuoi do lag/rolling la hanh vi mong doi va duoc chap nhan.

---

## 8. Ket luan

Sau dot override + rerun ngay 2026-04-06, bo du lieu da duoc nang cap day du ve feature engineering (70 cot), giu tinh toan ven panel key, va da xu ly diem leakage quan trong trong fallback normalization cua `crop_stress_score`. Dataset hien dat muc san sang de chuyen sang pha modeling va validation theo time-series protocol.