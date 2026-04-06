# BAO CAO EDA VA TIEN XU LY DU LIEU PANEL (2015-2025)

## CAP NHAT PHIEN BAN 2026-04-06 (Override + Audit Fix)

Cap nhat nay dong bo theo ban override moi trong `src/merge_preprocess.py` va ket qua rerun `python run_pipeline.py --from 4`.

### A. Ket qua du lieu sau rerun

- `merged_final.csv`: 20090 dong x 70 cot
- Date range: 2015-01-01 -> 2025-12-31
- So location: 5
- Key `location_id + date`: unique (0 duplicate)
- Completeness: 99.6329%
- NDVI observed ratio: 22.4988%
- LST observed ratio: 4.5495%

### B. Feature engineering duoc bo sung

- Median features:
   - `salinity_7d_median`
   - `ndvi_7d_median`
- Accumulation features:
   - `precip_15d_sum`
   - `precip_30d_sum`
- Event feature:
   - `heatwave_consecutive_days`
- Tendency features:
   - `salinity_tendency`
   - `ndvi_tendency`
   - `soil_moisture_tendency`

Tat ca feature tren da ton tai trong artifact moi nhat.

### C. Finding da sua theo audit (approved)

Da sua leakage fallback trong normalization cua `crop_stress_score`:

- Truoc day fallback co the dung `out[...].max()` (co chua holdout).
- Hien tai fallback chi dung train-only statistics:
   - `train_ref["ndvi"].max()`
   - `train_fallback_max["salinity_psu"]`
   - `train_fallback_max["soil_moisture_surface"]`

Muc tieu: dam bao khong co thong ke holdout lot vao buoc normalization khi tinh feature stress tong hop.

### D. Split metrics sau cap nhat

- Train 2015-2022 positive rate: 10.0548%
- Holdout 2023-2025 positive rate: 12.8102%

Ghi chu: Cac NaN o dau chuoi do lag/rolling duoc giu nguyen co chu dich de bao toan temporal safety.

## 1) Muc tieu bao cao
Bao cao nay tong hop day du ket qua EDA + preprocessing theo huong panel time-series cho 5 vi tri (location_id), voi 2 muc tieu:
- Tham dinh tinh dung dan cua du lieu dau vao cho phase mo hinh hoa.
- Giai thich ro cac bai toan kho (leakage, missing data, drift, stationarity, causality) va cach tiep can dang ap dung.

Pham vi:
- Tap train: 2015-01-01 den 2022-12-31.
- Tap holdout test cuoi: 2023-01-01 den 2025-12-31.
- Tan suat: theo ngay, panel 5 location.

## 2) Tong quan pipeline hien tai
Pipeline du lieu hien tai gom cac buoc chinh:
1. Lay du lieu ve tinh (NDVI, LST).
2. Lay du lieu khi tuong + dat.
3. Tao salinity proxy.
4. Merge + feature engineering + tao target stress event.
5. Tao artifact split thoi gian (train/holdout + expanding folds).

Thay doi quan trong trong dot refactor nay:
- Chuyen interpolation NDVI sang short-gap PCHIP co gioi han do dai gap (<= 14 ngay).
- Rolling feature doi sang min_periods=3 de giam over-trust o dau chuoi.
- Bo sung feature du bao an toan: salinity_7d_avg_lag1.
- Tinh ndvi_zscore bang thong ke train-only, sau do map ra full horizon (khong nhin tuong lai).
- Final cleanup chi ffill theo tung location (bo bfill de tranh future leakage).
- Chuan hoa naming holdout file thanh holdout_test_2023_2025.csv.

## 3) Tham dinh ket qua tu notebook panel EDA
Nguon tham dinh:
- Notebook panel EDA da duoc chay full.
- Kiem tra bo sung bang script doi chieu cung logic notebook.

### 3.1 Kiem tra tinh toan ven cua panel va split
Ket qua:
- Train: 14610 dong, 62 cot, 5 location, 2015-01-01 -> 2022-12-31.
- Holdout: 5480 dong, 62 cot, 5 location, 2023-01-01 -> 2025-12-31.
- Key (location_id, date) duy nhat o ca train va holdout.
- Do day du du lieu:
  - Train: 99.5329%
  - Holdout: 99.7610%

Nhan xet:
- Split time boundary dung theo thiet ke train/holdout.
- Khong phat hien trung key, tranh loi panel duplication.
- Do complete cao, du muc cho modeling; phan missing con lai tap trung o cac feature lag/rolling dau chuoi va 1 so cot co chu y nghiep vu.

### 3.2 Kiem tra target stress event
Ket qua ty le positive:
- Train: 10.0548%
- Holdout: 12.8102%

Nhan xet:
- Holdout co muc stress cao hon train (chenh ~2.76 diem phan tram).
- Day la tin hieu distribution shift can theo doi ky o phase model validation.
- Khong can can bang bang SMOTE/ADASYN trong bai toan chuoi thoi gian; uu tien thresholding, weighting, calibration theo thoi gian.

### 3.3 Kiem tra interpolation va gap
Ket qua NDVI interpolation tren train:
- pchip: 78.56%
- observed: 21.44%

Thong ke gap NDVI (train):
- p50 = 6 ngay
- p90 = 7 ngay
- p95 = 7 ngay
- p99 = 7 ngay

Nhan xet:
- Dac trung gap hien tai chu yeu la gap ngan (<= 7 ngay), phu hop voi chien luoc short-gap interpolation.
- Ty trong noi suy cao (78.56%) dat ra canh bao quan trong: mo hinh co nguy co hoc hanh vi interpolation hon la hoc tu quan sat thuc neu khong kiem soat.
- Vi vay can giu metadata interpolation (ndvi_interp_method, ndvi_is_observed, ndvi_gap_days) de phan tich bias va robust test.

### 3.4 Kiem tra rolling/lag feature
Ket qua so luong NaN tren train:
- ndvi_7d_avg: 10
- salinity_7d_avg: 10
- salinity_7d_avg_lag1: 15

Nhan xet:
- Muc NaN nay ky vong do min_periods=3 va shift(1) theo tung location.
- Day la hanh vi dung, khong phai loi; no xac nhan feature khong nhin tuong lai.

### 3.5 Granger causality theo tung location (salinity -> NDVI)
Ket qua tom tat:
- BT_BaTri: khong y nghia thong ke (min p ~ 0.4185)
- BT_BinhDai: khong y nghia thong ke (min p ~ 0.6710)
- BT_ChauThanh: khong y nghia thong ke (min p ~ 0.6804)
- BT_GiongTrom: co y nghia thong ke (best lag=7, min p ~ 0.0499)
- BT_ThanhPhu: khong y nghia thong ke (min p ~ 0.1333)

Tong quan: 1/5 location co dau hieu Granger y nghia.

Nhan xet:
- Quan he salinity -> NDVI khong dong nhat theo khong gian.
- Khong nen ap dung mot gia thuyet causal duy nhat cho tat ca location.
- Can tiep tuc model theo huong panel-aware/coefficient-by-location hoac cho phep heterogeneity.

### 3.6 Readiness check
Tat ca check dat:
- Train key unique: PASS
- Holdout key unique: PASS
- Train date range dung: PASS
- Holdout date range dung: PASS
- Location coverage match: PASS

Ket luan readiness: READY cho phase model baseline, voi dieu kien theo doi sat distribution shift va interpolation sensitivity.

## 4) Cac van de thuong gap trong bai toan nay va cach tiep can

### Van de A: Temporal leakage
Mo ta:
- De xay ra khi preprocess su dung thong tin tu tuong lai (vd bfill, chuan hoa toan bo horizon, rolling khong dung shift).

Tac dong:
- CV ao, holdout that bai, model overfit theo huong optimistic.

Tu duy xu ly:
- Moi bien doi phai dat cau hoi: tai ngay t, co the biet du lieu nay trong thuc te khong?
- Uu tien train-only statistics.

Giai phap dang ap dung:
- ndvi_zscore map tu thong ke train-only theo (location, month).
- final cleanup bo bfill, chi ffill theo location.
- rolling co min_periods=3 va feature lagged salinity_7d_avg_lag1.

### Van de B: Spatial leakage (tron location)
Mo ta:
- Trich xuat dac trung khong group theo location co the lam lo thong tin cheo diem.

Tac dong:
- Mat y nghia panel, mo hinh hoc sai co che dia phuong.

Tu duy xu ly:
- Moi transform phai groupby('location_id') neu lien quan chuoi thoi gian.

Giai phap dang ap dung:
- Rolling, lag, dry-spell, moisture deficit deu tinh theo tung location.

### Van de C: Missing data va interpolation bias
Mo ta:
- NDVI co tan suat quan sat thap hon weather/salinity; noi suy nhieu co the thay doi hinh dang chuoi.

Tac dong:
- Feature drift, mo hinh hoc pattern cua interpolation.

Tu duy xu ly:
- Phan biet ro observed va imputed.
- Gioi han interpolation theo do dai gap hop ly.

Giai phap dang ap dung:
- Short-gap PCHIP <= 14 ngay.
- Long gap giu missing.
- Luu metadata ndvi_interp_method, ndvi_gap_days.

### Van de D: Non-stationarity va heterogeneity theo location
Mo ta:
- Moi location co dong luc khac nhau; quan he salinity-NDVI khong co dinh toan vung.

Tac dong:
- Mot model/global signal duy nhat de bi fail local.

Tu duy xu ly:
- EDA/causality theo location truoc khi chot model architecture.

Giai phap dang ap dung:
- ACF/PACF va Granger chay rieng moi location.
- Tiep can panel-aware trong toan bo bao cao.

### Van de E: Label shift va event rarity
Mo ta:
- Ty le stress event dao dong theo giai doan (train vs holdout).

Tac dong:
- Threshold va calibration de bi sai lech khi deployment.

Tu duy xu ly:
- Tach holdout cuoi theo thoi gian, khong random split.
- Theo doi metric theo giai doan va theo location.

Giai phap dang ap dung:
- Holdout 2023-2025 doc lap.
- Expanding window folds trong train universe.

## 5) Danh gia uu diem, han che, rui ro con lai

### Uu diem hien tai
- Cau truc split dung nghiep vu forecasting (past -> future).
- Kiem soat leakage ro rang hon so voi ban truoc refactor.
- Notebook EDA panel da phu kin cac tru cot: integrity, interpolation, dependence, causality.
- Dataset sau preprocess co complete cao, phu hop baseline modeling.

### Han che/rui ro con lai
- Ty trong noi suy NDVI cao (78.56% train), can stress-test mo hinh theo observed-only subset.
- Granger chi y nghia 1/5 location => can tranh suy dien qua muc relation toan vung.
- Positive rate holdout cao hon train => can calibration/threshold tuning o stage model.
- Can theo doi tinh on dinh cua feature importance qua cac folds (risk concept drift).

## 6) De xuat hanh dong tiep theo (uu tien cao -> thap)
1. Baseline model theo expanding folds va bao cao metric theo tung location + overall.
2. Tao bo robust checks:
   - Train observed-only vs train full (de luong hoa interpolation sensitivity).
   - Backtest threshold stress event theo tung nam.
3. Calibration tai holdout:
   - Kiem tra precision-recall tradeoff.
   - Dieu chinh threshold theo objective nghiep vu (canh bao som vs false alarm).
4. Feature governance:
   - Danh dau ro cac feature co nguy co leakage cao.
   - Duy tri checklist no-future-information trong code review.
5. Cung co notebook audit:
   - Bo sung tong hop theo season (dry/wet) va theo location cho event rate.

## 7) Ket luan chot
Giai doan EDA + preprocessing hien tai dat muc "san sang cho modeling baseline" voi nen tang panel-safe va temporal-safe tot hon dang ke.

Diem can quan tam nhat cho phase tiep theo:
- Quan ly interpolation bias.
- Xu ly shift train/holdout.
- Ton trong tinh khong dong nhat theo location trong quan he salinity-NDVI.

Neu team giu dung ky luat split theo thoi gian + train-only statistics + panel isolation nhu hien tai, rui ro regression do leakage se duoc giam manh, va ket qua holdout se phan anh sat hon hieu nang thuc te khi trien khai.
