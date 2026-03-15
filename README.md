# SaltySeq — Du bao Stress Cay Trong do Xam Nhap Man

**Mon hoc:** CS313 - Data Mining  
**Vung nghien cuu:** Ben Tre, Dong bang song Cuu Long, Viet Nam  
**Giai doan du lieu:** 2023-01-01 -> 2025-12-31  
**Toa do:** 10.24N, 106.37E  

---

## Mo ta du an

SaltySeq la mot PoC (Proof of Concept) ung dung khai pha du lieu va phat hien bat thuong de theo doi tac dong cua xam nhap man len suc khoe cay trong tai vung DBSCL. Du an tich hop 3 nguon du lieu:

| Nguon | Bien | Tan suat |
|---|---|---|
| Google Earth Engine (Landsat 8/9) | NDVI, LST | ~5-16 ngay |
| Open-Meteo ERA5-Land | Nhiet do, Mua, Do am dat | Hang ngay |
| Proxy tong hop | Do man (PSU) | Hang ngay |

---

## Cau truc thu muc

```
poc_saltyseq/
|- run_pipeline.py
|- requirements.txt
|- src/
|  |- satellite_gee.py
|  |- weather_openmeteo.py
|  |- salinity.py
|  |- merge_preprocess.py
|- notebooks/
|  |- EDA_SaltySeq_Raw_Data.ipynb
|- reports/
|  |- generate_report.py
|  |- BAOCAT_TIENXULY.md
|  |- DATASOURCES_QUICKREF.md
|- data/
|  |- real_ndvi_lst.csv
|  |- real_weather.csv
|  |- real_salinity.csv
|  |- merged_final.csv
```

---

## Cach chay

```bash
pip install -r requirements.txt
python run_pipeline.py
```

Neu can xac thuc GEE lan dau:

```bash
python -c "import ee; ee.Authenticate()"
```

---

## Ket qua chinh

- **merged_final.csv**: 1096 ban ghi x 52 dac trung, san sang cho PrefixSpan va XGBoost.
- **EDA**: Phan tich missing pattern NDVI, tuong quan Spearman, ACF/PACF va seasonal decomposition.
