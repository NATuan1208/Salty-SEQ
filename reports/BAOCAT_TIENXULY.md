# BAO CAO TIEN XU LY DU LIEU (CAP NHAT)
## Du an SaltySeq - Lam giau du lieu panel da vi tri

> Cap nhat thu cong: 2026-03-29 (dong bo sau commit threshold calibration)  
> Pham vi du lieu: 2015-01-01 den 2022-12-31  
> Khong gian: 5 location tai Ben Tre (panel time-series)

---

## 1. Muc tieu cap nhat

Ban bao cao nay thay the ban cu (single location 2023) de phan anh dung trang thai pipeline moi:

- Mo rong thoi gian 8 nam (2015-2022)
- Mo rong khong gian 5 location
- Chuan hoa merge key thanh location_id + date
- Bo sung audit interpolation cho NDVI/LST

---

## 2. Tong quan output du lieu

| Tep | So dong | So cot | So location | Date range | Khoa location_id+date |
|---|---:|---:|---:|---|---|
| data/real_ndvi_lst.csv | 3135 | 9 | 5 | 2015-01-01 -> 2022-12-31 | unique |
| data/real_weather.csv | 14610 | 17 | 5 | 2015-01-01 -> 2022-12-31 | unique |
| data/real_salinity.csv | 14610 | 9 | 5 | 2015-01-01 -> 2022-12-31 | unique |
| data/merged_final.csv | 14610 | 61 | 5 | 2015-01-01 -> 2022-12-31 | unique |

Coverage theo tung location trong merged_final.csv:

| location_id | So dong | Bat dau | Ket thuc |
|---|---:|---|---|
| BT_BaTri | 2922 | 2015-01-01 | 2022-12-31 |
| BT_BinhDai | 2922 | 2015-01-01 | 2022-12-31 |
| BT_ChauThanh | 2922 | 2015-01-01 | 2022-12-31 |
| BT_GiongTrom | 2922 | 2015-01-01 | 2022-12-31 |
| BT_ThanhPhu | 2922 | 2015-01-01 | 2022-12-31 |

---

## 3. Chat luong du lieu sau tien xu ly

Chi so tong quan tren merged_final.csv:

- Shape: 14610 x 61
- Completeness tong the: 99.5989% (missing trung binh 0.4011%)
- NDVI observed ratio: 21.44%
- LST observed ratio: 3.95%
- Nguon salinity: synthetic_proxy (100%)

Chi so label/anomaly:

- is_stress_event = 1: 1461 ban ghi (10.00%)
- Ty le lop 0/1: 13149 / 1461 (xap xi 9:1, dung policy ML)
- is_salinity_spike = 1: 2308 ban ghi
- crop_stress_score mean: 0.3655
- crop_stress_score p95: 0.6951

Phan bo is_stress_event theo nam (%):

- 2015: 0.77 | 2016: 6.34 | 2017: 1.37 | 2018: 7.07
- 2019: 13.04 | 2020: 21.15 | 2021: 14.96 | 2022: 15.29

Phan bo is_stress_event theo location (%):

- BT_ThanhPhu: 11.40
- BT_ChauThanh: 9.96
- BT_GiongTrom: 9.65
- BT_BaTri: 9.62
- BT_BinhDai: 9.38

Danh gia nhanh:

- Integrity key dat yeu cau (khong duplicate location_id + date)
- Temporal continuity dat yeu cau tren toan bo panel
- Missing chu yeu xuat hien o nhom feature phu thuoc lag/rolling va metadata nguon
- Target moi da dat dung dai can bang 10%-15% theo yeu cau huan luyen

---

## 4. Mo ta quy trinh tien xu ly

Pipeline gom 4 script theo thu tu:

1. src/satellite_gee.py
2. src/weather_openmeteo.py
3. src/salinity.py
4. src/merge_preprocess.py

Tom tat chuc nang:

- Script 1: thu NDVI/LST theo location, chunk theo moc thoi gian, gan metadata vi tri
- Script 2: thu weather/soil daily tu Open-Meteo theo location, co retry/backoff
- Script 3: tao salinity panel (uu tien du lieu that neu co, fallback proxy)
- Script 4: merge panel, tao feature lag/rolling/derived/anomaly, xuat merged_final.csv

---

## 5. Feature schema hien tai

merged_final.csv hien co 61 cot, gom cac nhom:

- Metadata panel: date, location_id, location_name, lat, lon, distance_to_estuary_km
- Satellite core: ndvi, ndvi_source, lst
- Interpolation audit: ndvi_is_observed, lst_is_observed, ndvi_gap_days, ndvi_interp_method, lst_interp_method
- Weather/soil/salinity goc: temp_max, temp_min, temp_mean, precipitation, rain, et0, radiation, wind_max, soil_moisture_surface, soil_moisture_deep, soil_temp, salinity_psu, precip_7d_mm, salinity_source
- Time encoding: day_of_year, month, week, season, is_dry_season, month_sin, month_cos
- Rolling features: temp_7d_avg, ndvi_7d_avg, precip_7d_sum, salinity_7d_avg, lst_7d_avg, soil_moisture_7d_avg
- Lag features: ndvi_lag_{1,3,7}, salinity_lag_{1,3,7}, precip_lag_{1,3,7}
- Derived features: days_without_rain, moisture_deficit, moisture_deficit_7d, ndvi_diff, ndvi_pct_change, lst_ndvi_ratio, salinity_precip_ratio
- Target-like features: ndvi_zscore, is_stress_event, is_salinity_spike, crop_stress_score

---

## 6. Muc do san sang cho modeling

Trang thai:

- San sang cho PrefixSpan: can discretize bien lien tuc thanh event theo tung location/time window
- San sang cho XGBoost: co the dung merged_final.csv sau khi loai bo cot leakage/identifier khong can thiet theo bai toan
- Target calibration da duoc khoa o nguong ndvi_zscore <= -1.315 (Moderate Stress)

Luu y ky thuat:

- Tuyet doi tranh random split cho time-series; uu tien TimeSeriesSplit/backtesting
- Danh gia leakage dac biet voi cac cot sinh tu target (vd. ndvi_zscore khi du doan ndvi)
- Salinity hien tai la proxy, can cap nhat nguon sensor that neu co de tang do tin cay

---

## 7. Ket luan

Dataset da chuyen thanh cong tu single-series sang panel time-series da vi tri, da mo rong du lieu 8 nam va dam bao tinh nhat quan khoa location_id + date. Voi target is_stress_event da hieu chinh ve muc 10.00%, bo du lieu hien tai dat muc san sang de chuyen sang pha modeling va validation theo time-series protocol.