# SaltySeq - Du bao Stress Cay Trong do Xam Nhap Man

Du an PoC cho bai toan khai pha du lieu va phat hien bat thuong trong nong nghiep vung ven bien Ben Tre.

## Thong tin nhanh

- Mon hoc: CS313 - Data Mining
- Vung nghien cuu: Ben Tre, Dong bang song Cuu Long, Viet Nam
- Pham vi thoi gian muc tieu: 2015-01-01 den 2025-12-31
- Chien luoc split: train/validation = 2015-2022, final holdout = 2023-2025
- Cau truc du lieu panel: 5 location x daily timeline
- Khoa chinh du lieu: location_id + date

## Trang thai du lieu sau lam giau (tom tat)

Cap nhat theo output pipeline trong thu muc data:

| Tep | So dong | So cot | So location | Khoa location_id+date |
|---|---:|---:|---:|---|
| real_ndvi_lst.csv | 4522 | 9 | 5 | unique |
| real_weather.csv | 20090 | 17 | 5 | unique |
| real_salinity.csv | 20090 | 9 | 5 | unique |
| merged_final.csv | 20090 | 61 | 5 | unique |

Chi so chat luong du lieu merged_final.csv:

- Do day du tong the: 99.65% (sau cleanup feature)
- Ti le NDVI quan sat truc tiep: 22.50% (con lai duoc noi suy co kiem soat)
- Ti le LST quan sat truc tiep: 4.55% (con lai duoc noi suy co kiem soat)
- Nguon salinity hien tai: synthetic_proxy (100%)

## Nguon du lieu

| Nguon | Bien chinh | Tan suat |
|---|---|---|
| Google Earth Engine | NDVI, LST | Khong deu theo ve tinh |
| Open-Meteo ERA5-Land | Nhiet do, mua, ET0, gio, buc xa, do am dat | Hang ngay |
| Proxy tong hop | Salinity PSU | Hang ngay |

## Pipeline

```
python run_pipeline.py
```

Thu tu xu ly:

1. src/satellite_gee.py -> Thu thap NDVI/LST theo location
2. src/weather_openmeteo.py -> Thu thap weather/soil daily theo location
3. src/salinity.py -> Tao salinity theo location (real optional, fallback proxy)
4. src/merge_preprocess.py -> Merge + feature engineering + xuat merged_final.csv
5. src/create_time_splits.py -> Tao train universe (2015-2022), CV folds, va holdout (2023-2025)

Neu chay GEE lan dau:

```
python -c "import ee; ee.Authenticate()"
```

## Dau ra phuc vu modeling

merged_final.csv da san sang cho cac buoc tiep theo:

- Sequential pattern mining (PrefixSpan) voi du lieu panel theo location
- Supervised learning (vd. XGBoost) voi bo feature da xu ly theo nhom thoi gian, lag, rolling va stress

## Temporal Split Policy

- Khong random split cho time-series.
- Validation noi bo: expanding-window folds tren 2015-2022.
- Final test set: 2023-2025, chi dung 1 lan sau khi khoa model.

Luu y:

- Chua su dung ky thuat sinh du lieu tong hop kieu SMOTE/ADASYN cho time-series de tranh leakage.
- Khuyen nghi danh gia model bang TimeSeriesSplit hoac backtesting theo moc thoi gian.
