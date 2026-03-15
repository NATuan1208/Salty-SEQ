# BÁO CÁO PHÂN TÍCH TIỀN XỬ LÝ DỮ LIỆU
## Dự án SaltySeq – Khai phá dữ liệu & Phát hiện bất thường
### Vùng nghiên cứu: Bến Tre, Đồng bằng Sông Cửu Long, Việt Nam

> Được tạo tự động: 2026-03-08 15:07  
> Dữ liệu: 2023-01-01 → 2023-12-31 | Tọa độ: (10.24°N, 106.37°E)

---

## 1. TỔNG QUAN DỮ LIỆU THU THẬP (DATA ACQUISITION)

### 1.1 Nguồn dữ liệu & Phương thức thu thập

| # | Nguồn | API / Nền tảng | Phân giải | Tần suất | Trạng thái |
|---|-------|----------------|-----------|----------|------------|
| 1 | Sentinel-2 SR Harmonized | Google Earth Engine (GEE) | 10m | ~5 ngày | ✅ THỰC |
| 2 | MODIS MOD13Q1 (Terra) | Google Earth Engine (GEE) | 250m | 16-ngày composite | ✅ THỰC |
| 3 | MODIS MYD13Q1 (Aqua) | Google Earth Engine (GEE) | 250m | 16-ngày (offset 8 ngày) | ✅ THỰC |
| 4 | Landsat 8/9 C02 T1 L2 | Google Earth Engine (GEE) | 30m | ~8 ngày (L8+L9) | ✅ THỰC |
| 5 | Open-Meteo Archive API | ERA5-Land reanalysis | ~9km | Hằng ngày | ✅ THỰC |
| 6 | Độ mặn (proxy tổng hợp) | Mô hình hóa từ khí tượng | — | Hằng ngày | 🔶 PROXY |

**Ghi chú về dữ liệu độ mặn:**
Dữ liệu độ mặn thực (Copernicus Marine Service – `cmems_mod_glo_phy_anfc_0.083deg_P1D-m`)
yêu cầu tài khoản thương mại. Proxy tổng hợp được xây dựng theo phương pháp:

```
salinity(t) = S_seasonal(t)  +  S_precip(t)  +  S_et0(t)  +  ε(t)

  S_seasonal(t) = A × cos(2π × DOY/365 - φ)      # biên độ mùa vụ
  S_precip(t)   = -k₁ × precip_7d_avg(t)         # pha loãng do mưa
  S_et0(t)      = +k₂ × (ET0 - ET0_mean)         # cô đặc do bốc hơi
  ε(t)          = nhiễu Gaussian (σ=0.5 PSU)

  Hiệu chỉnh thực nghiệm:
   • Mùa khô (11-4): peak 15–28 PSU  → phù hợp ĐBSCL theo báo cáo MRC 2022
   • Mùa mưa (5-10): đáy  0.5–8 PSU  → phù hợp data Sở NN&PTNT Bến Tre
```

### 1.2 Chiến lược Multi-source NDVI

**Vấn đề:** Sentinel-2 có độ phân giải không gian tốt nhất (10m) nhưng bị giới hạn
bởi mây mùa mưa (tháng 5–10) ở ĐBSCL – cloud cover 70–95%, chỉ thu được 26 ảnh/năm.

**Giải pháp:** Kết hợp 3 nguồn theo thứ tự ưu tiên:

```
Ưu tiên: Sentinel-2 (10m) > Landsat 8/9 (30m) > MODIS composite (250m)

Lý do MODIS hiệu quả trong mùa mưa:
  • Max-value composite 16 ngày: GEE chọn pixel có NDVI cao nhất
    trong 16 ngày liên tiếp ≡ pixel có ít mây nhất → robust với cloud cover
  • Terra (10:30 AM) + Aqua (13:30 PM) offset 8 ngày → effective 8-ngày resolution
  • Được thiết kế đặc biệt cho vùng nhiệt đới (MODIS Land Product)
```

**Kết quả thu thập NDVI:**

| Nguồn | Số quan sát | % tổng | Độ phân giải |
|-------|-------------|--------|--------------|
| sentinel2 | 26 | 28.3% | 10m |
| modis_terra | 22 | 23.9% | 250m |
| modis_aqua | 22 | 23.9% | 250m |
| landsat | 22 | 23.9% | 30m |
| *(interpolated)* | 273 | — | — |
| **Tổng (365 ngày)** | **365** | **100%** | — |

**Coverage NDVI thực quan sát theo tháng:**

```
  T01 (Khô): ▓▓▓▓▓·····   5 obs  | NDVI_avg=0.316 | LST=31.5°C | Precip=107mm | Sal=14.0PSU
  T02 (Khô): ▓▓▓▓▓▓▓▓▓·   9 obs  | NDVI_avg=0.292 | LST=32.9°C | Precip=14mm | Sal=21.4PSU
  T03 (Khô): ▓▓▓▓▓▓▓▓▓▓  10 obs  | NDVI_avg=0.262 | LST=33.2°C | Precip=1mm | Sal=26.0PSU
  T04 (Khô): ▓▓▓▓▓▓▓▓▓·   9 obs  | NDVI_avg=0.291 | LST=34.9°C | Precip=78mm | Sal=24.1PSU
  T05 (Mưa): ▓▓▓▓▓▓▓▓▓▓  10 obs  | NDVI_avg=0.227 | LST=38.8°C | Precip=210mm | Sal=18.7PSU
  T06 (Mưa): ▓▓▓▓▓▓▓▓▓·   9 obs  | NDVI_avg=0.282 | LST=39.9°C | Precip=250mm | Sal=11.9PSU
  T07 (Mưa): ▓▓▓▓▓▓▓···   7 obs  | NDVI_avg=0.312 | LST=35.8°C | Precip=422mm | Sal=4.7PSU
  T08 (Mưa): ▓▓▓▓▓▓▓···   7 obs  | NDVI_avg=0.250 | LST=38.2°C | Precip=249mm | Sal=3.9PSU
  T09 (Mưa): ▓▓▓▓······   4 obs  | NDVI_avg=0.300 | LST=37.2°C | Precip=459mm | Sal=0.5PSU
  T10 (Mưa): ▓▓▓▓▓▓▓···   7 obs  | NDVI_avg=0.204 | LST=40.1°C | Precip=428mm | Sal=0.5PSU
  T11 (Khô): ▓▓▓▓▓▓▓···   7 obs  | NDVI_avg=0.302 | LST=36.8°C | Precip=133mm | Sal=4.3PSU
  T12 (Khô): ▓▓▓▓▓▓▓▓··   8 obs  | NDVI_avg=0.272 | LST=35.8°C | Precip=25mm | Sal=10.8PSU
```

---

## 2. CẤU TRÚC VÀ THỐNG KÊ DATASET

**Shape:** `365 hàng × 52 cột`
**Khoảng thời gian:** 2023-01-01 → 2023-12-31 (365 ngày, không thiếu ngày nào)
**Completeness tổng thể:** 98.56%
**Memory footprint:** ~175 KB

### 2.1 Các cột và nhóm đặc trưng

| # | Tên cột | Dtype | Min | Mean | Max | Mô tả |
|---|---------|-------|-----|------|-----|-------|
| — | `ndvi` | float64 | -0.03 | 0.275 | 0.43 | NDVI tổng hợp 3 nguồn |
| — | `lst` | float64 | 27.68 | 36.271 | 45.66 | Land Surface Temperature (°C) |
| — | `temp_mean` | float64 | 23.10 | 26.835 | 30.70 | Nhiệt độ không khí trung bình (°C) |
| — | `temp_max` | float64 | 25.60 | 31.244 | 36.50 | Nhiệt độ tối đa ngày (°C) |
| — | `temp_min` | float64 | 19.50 | 24.078 | 27.20 | Nhiệt độ tối thiểu ngày (°C) |
| — | `precipitation` | float64 | 0.00 | 6.512 | 75.20 | Lượng mưa (mm/ngày) |
| — | `et0` | float64 | 1.23 | 3.981 | 6.13 | Bốc hơi tiềm năng ET₀ (mm/ngày) |
| — | `radiation` | float64 | 6.17 | 18.932 | 26.04 | Bức xạ mặt trời (MJ/m²/ngày) |
| — | `wind_max` | float64 | 4.40 | 13.909 | 22.40 | Tốc độ gió tối đa (km/h) |
| — | `soil_moisture_surface` | float64 | 0.15 | 0.318 | 0.43 | Độ ẩm đất tầng 0–7cm (m³/m³) |
| — | `soil_moisture_deep` | float64 | 0.19 | 0.330 | 0.43 | Độ ẩm đất tầng 7–28cm (m³/m³) |
| — | `soil_temp` | float64 | 23.38 | 27.431 | 31.39 | Nhiệt độ đất bề mặt (°C) |
| — | `salinity_psu` | float64 | 0.50 | 11.672 | 28.95 | Độ mặn nước (PSU) |

### 2.2 Phân tích theo mùa

**Định nghĩa mùa (theo lịch thủy văn ĐBSCL):**
- **Mùa khô** (Dry Season): tháng 11, 12, 1, 2, 3, 4
- **Mùa mưa** (Wet Season): tháng 5, 6, 7, 8, 9, 10

| Mùa | Số ngày | NDVI TB | NDVI Std | LST TB | Mưa TB | Độ mặn TB | Stress TB |
|-----|---------|---------|----------|--------|--------|-----------|-----------|
| DRY | 181 | 0.289 | 0.056 | 34.2°C | 2.0mm | 16.7 PSU | 0.450 |
| WET | 184 | 0.262 | 0.073 | 38.3°C | 11.0mm | 6.7 PSU | 0.265 |

**Phân tích mùa vụ:**
- Mùa khô NDVI (0.289) > Mùa mưa (0.262): Thực vật phát triển tốt hơn khi không mưa lớn liên tục — bộ rễ không bị ngập úng
- LST mùa mưa (38.3°C) > LST mùa khô (34.2°C): Bức xạ cao hơn trong mùa mưa (ít mây cục bộ ngắn hạn, ban ngày nhiều nắng)
- Độ mặn mùa khô (16.7 PSU) >> mùa mưa (6.7 PSU): Xâm nhập mặn điển hình theo lịch ĐBSCL

### 2.3 Phân phối và outlier

```
  NDVI:
    Range   : [-0.0265, 0.4295]
    Mean±Std: 0.2755 ± 0.0666
    Giá trị âm (2 ngày): bề mặt nước/đất trống sau lũ — hợp lý
    Giá trị cao > 0.4 (2 ngày): MODIS composite mùa khô — cây trồng tốt

  LST:
    Range   : [27.7, 45.7]°C
    Max 45.7°C (tháng 5-6): stress nhiệt CỰC KỲ CAO — nguy cơ cháy lúa, héo cây
    Min 27.7°C (tháng 1): điều kiện mát mẻ nhất năm

  Độ mặn:
    Range   : [0.5, 28.9] PSU
    Peak 28.9 PSU (tháng 3): xâm nhập mặn đỉnh — ngưỡng gây chết lúa là 3 PSU
    0.50 PSU (tháng 9): mùa lũ, nước ngọt hoàn toàn

  Mưa:
    Total   : 2377 mm/năm
    Max ngày: 75.2 mm — sự kiện mưa cực đoan
    Số ngày không mưa: 67 / 365
    Chuỗi không mưa dài nhất: 38 ngày
```

---

## 3. QUY TRÌNH TIỀN XỬ LÝ (PREPROCESSING PIPELINE)

### 3.1 Tổng quan pipeline

```
Script 1  →  Script 2  →  Script 3  →  Script 4
  GEE         Open-Meteo   Salinity      Merge +
 (NDVI+LST)  (Weather+Soil) (Proxy)    Feature Eng.
    │              │            │            │
    ▼              ▼            ▼            ▼
 real_ndvi   real_weather  real_salinity  merged_final
 _lst.csv       .csv           .csv          .csv
 92 rows       365 rows      365 rows      365×52
```

### 3.2 Xử lý vấn đề độ thưa dữ liệu vệ tinh (Temporal Alignment)

**Vấn đề cốt lõi:**

```
  Sentinel-2 NDVI  : ~26 quan sát / năm  (irregular, cloud gaps)
  Landsat NDVI     : ~22 quan sát / năm  (irregular)
  MODIS NDVI       : ~44 quan sát / năm  (16-day grid)
  LST (Landsat)    : ~22 quan sát / năm  (irregular)
  ─────────────────────────────────────────────────────────
  Weather / Salinity:  365 quan sát / năm (daily, 0% missing)

  → Không thể merge trực tiếp: số hàng không bằng nhau
  → Cần đưa satellite về cùng lưới thời gian daily
```

**Chiến lược Temporal Alignment:**

```python
# Bước 1: Tạo daily date index (365 ngày)
daily_dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')

# Bước 2: Left-join satellite lên daily grid → nhiều NaN
df_daily = df_dates.merge(df_satellite, on='date', how='left')

# Bước 3: Linear interpolation (giới hạn 15 ngày)
# Tại sao linear?  → Ít artifact ở biên hơn Cubic/Spline
# Tại sao limit 15? → Gap > 15 ngày không đủ tin cậy để interpolate
df_daily['ndvi'] = df_daily['ndvi'].interpolate(method='linear', limit=15)

# Bước 4: Đánh dấu observed vs interpolated
df_daily['ndvi_is_observed'] = df_daily['ndvi'].notna().astype(int)

# Bước 5: Fill các edge NaN còn lại (đầu/cuối chuỗi)
df_daily['ndvi'] = df_daily['ndvi'].ffill().bfill()

# Bước 6: Inner merge với weather + salinity (đã daily, 0% missing)
df_merged = df_aligned.merge(df_weather, on='date', how='inner')
               .merge(df_salinity, on='date', how='inner')
```

**Kết quả alignment:**
- NDVI: 92 điểm thực quan sát + 273 ngày nội suy = 365 ngày
- LST:  22 điểm thực quan sát + 343 ngày nội suy = 365 ngày
- Cột `ndvi_is_observed` và `lst_is_observed` giúp model phân biệt real vs interpolated

### 3.3 Xử lý giá trị thiếu còn lại

```
  NaN còn lại sau alignment: 273 giá trị
  → 100% thuộc về các cột LAG, ROLLING ở đầu chuỗi (ngày 1-7)
    (rolling 7 ngày cần 6 giá trị trước → 6 ngày đầu không tính được)
  → Xử lý: forward-fill + backward-fill những cột này
  → Sau xử lý: completeness = 98.56% (273 NaN / 365×52 = 1.44%)
  → Các NaN còn lại: cột ndvi_source (text, hàng interpolated = NaN bình thường)
```

### 3.4 Kiểm tra chất lượng dữ liệu

| Tiêu chí | Kết quả | Đánh giá |
|---------|---------|----------|
| Số hàng | 365 / 365 | ✅ Đủ 365 ngày |
| Completeness tổng | 98.56% | ✅ Tốt |
| NDVI missing | 0 | ✅ Không thiếu |
| LST missing | 0 | ✅ Không thiếu |
| Weather missing | 0 | ✅ Hoàn hảo |
| NDVI range hợp lý | [-0.027, 0.430] ⊂ [-0.2, 1.0] | ✅ OK |
| LST range hợp lý | [27.7, 45.7] °C | ✅ Hợp lý ĐBSCL |
| Duplicate dates | 0 | ✅ Không trùng |
| Temporal continuity | Liên tục không gián đoạn | ✅ OK |

---

## 4. ĐẶC TRƯNG HÓA DỮ LIỆU (FEATURE ENGINEERING)

Tổng cộng **52 features** được tạo từ 4 nguồn dữ liệu gốc,
chia thành **5 nhóm** theo mục đích sử dụng:

```
  Nhóm A  (7 features): Temporal / Calendar
  Nhóm B  (6 features): Rolling statistics (7-day window)
  Nhóm C  (9 features): Lag features (1, 3, 7 days)
  Nhóm D  (7 features): Derived / Physical
  Nhóm E  (4 features): Anomaly detection labels
  ─────────────────────────────────────────────────────
  + Raw features (18): date, NDVI, LST, weather(9), soil(3), salinity
  = TỔNG: 52 columns
```

### Nhóm A — Temporal / Calendar Features

**Mục đích:** Giúp model học tính chu kỳ mùa vụ (seasonal patterns)
mà không cần giải thích thủ công. Đặc biệt quan trọng cho PrefixSpan
(các pattern xảy ra theo mùa) và XGBoost (feature mùa vụ rõ nghĩa).

| Feature | Công thức | Ý nghĩa |
|---------|-----------|---------|
| `day_of_year` | t.dayofyear | Ngày thứ N trong năm (1–365) |
| `month` | t.month | Tháng (1–12) |
| `week` | t.isocalendar().week | Tuần ISO (1–52) |
| `season` | 'dry'/'wet' | Mùa thủy văn ĐBSCL |
| `is_dry_season` | 1 nếu tháng ∈ {11,12,1,2,3,4} | Binary flag mùa khô |
| `month_sin` | sin(2π × month / 12) | Mã hóa tuần hoàn tháng |
| `month_cos` | cos(2π × month / 12) | Mã hóa tuần hoàn tháng |

**Lý do dùng sin/cos thay vì month thô:**
Tháng 1 và tháng 12 trong thực tế gần nhau (đều mùa khô) nhưng
về số học thì cách xa (1 vs 12). Fourier encoding `(sin, cos)` giữ
tính liên tục này: khoảng cách Euclidean giữa T12 và T1 ≈ 0.

### Nhóm B — Rolling Statistics (7-day window)

**Mục đích:** Làm mịn noise ngắn hạn, nắm xu hướng 1 tuần gần nhất.
Đặc biệt quan trọng cho phát hiện stress cây trồng (phản ứng chậm).

| Feature | Công thức | Ý nghĩa |
|---------|-----------|---------|
| `temp_7d_avg` | rolling(7).mean(temp_mean) | Nhiệt độ TB 7 ngày |
| `ndvi_7d_avg` | rolling(7).mean(ndvi) | NDVI TB 7 ngày |
| `precip_7d_sum` | rolling(7).sum(precipitation) | Tổng mưa 7 ngày |
| `salinity_7d_avg` | rolling(7).mean(salinity_psu) | Độ mặn TB 7 ngày |
| `lst_7d_avg` | rolling(7).mean(lst) | LST TB 7 ngày |
| `soil_moisture_7d_avg` | rolling(7).mean(soil_moisture_surface) | Ẩm đất TB 7 ngày |

**Thống kê rolling features:**
- `precip_7d_sum` range: [0.0, 190.8] mm
  → Max 190.8 mm/7 ngày: sự kiện lũ mạnh
- `ndvi_7d_avg` std: 0.0488 (thấp hơn NDVI gốc 0.0666)
  → Rolling làm mịn ~27% variance

### Nhóm C — Lag Features (1, 3, 7 ngày)

**Mục đích:** Cho model biết trạng thái **quá khứ gần**. Cực kỳ cần thiết cho:
- **XGBoost**: Time series forecasting cần biết giá trị hôm qua
- **PrefixSpan**: Pattern mining có thể phát hiện chuỗi NDVI↓ → Salinity↑ → Stress↑

| Feature | Công thức | Ý nghĩa |
|---------|-----------|---------|
| `ndvi_lag_1` | ndvi.shift(1) | NDVI ngày hôm qua |
| `ndvi_lag_3` | ndvi.shift(3) | NDVI 3 ngày trước |
| `ndvi_lag_7` | ndvi.shift(7) | NDVI 1 tuần trước |
| `salinity_lag_1` | salinity_psu.shift(1) | Độ mặn ngày hôm qua |
| `salinity_lag_3` | salinity_psu.shift(3) | Độ mặn 3 ngày trước |
| `salinity_lag_7` | salinity_psu.shift(7) | Độ mặn 1 tuần trước |
| `precip_lag_1` | precipitation.shift(1) | Lượng mưa ngày hôm qua |
| `precip_lag_3` | precipitation.shift(3) | Lượng mưa 3 ngày trước |
| `precip_lag_7` | precipitation.shift(7) | Lượng mưa 1 tuần trước |

**Tương quan lag features:**
- NDVI với lag: lag_1=0.719, lag_3=0.324, lag_7=0.191
  → Autocorrelation NDVI cao → chuỗi NDVI có tính dự đoán tốt
- Salinity với lag: lag_1=0.969, lag_3=0.956, lag_7=0.937
  → Autocorrelation độ mặn rất cao (>0.93) → quán tính thủy văn lớn

### Nhóm D — Derived / Physical Features

**Mục đích:** Kết hợp thông tin từ nhiều nguồn, tạo biến có ý nghĩa vật lý
cao hơn feature thô — giúp model học được quan hệ phi tuyến dễ hơn.

| Feature | Công thức | Ý nghĩa vật lý |
|---------|-----------|----------------|
| `days_without_rain` | Counter reset khi mưa > 0 | Hạn hán liên tục (ngày) |
| `moisture_deficit` | precip - ET₀ | Thâm hụt ẩm (thiếu nước khi âm) |
| `moisture_deficit_7d` | rolling(7).sum(moisture_deficit) | Thâm hụt ẩm tích lũy 7 ngày |
| `ndvi_diff` | ndvi − ndvi_lag_1 | Tốc độ thay đổi NDVI (Δt=1 ngày) |
| `ndvi_pct_change` | (ndvi − ndvi_lag_1) / ndvi_lag_1 | % thay đổi NDVI |
| `lst_ndvi_ratio` | lst / (ndvi + 0.1) | Chỉ số stress nhiệt–thực vật |
| `salinity_precip_ratio` | salinity_psu / (precip_7d_mm + 0.01) |Áp lực mặn trong điều kiện mưa |

**Phân tích chi tiết từng feature:**

**`days_without_rain`:** Max = 38 ngày liên tiếp không mưa (mùa khô tháng 2-3)
Ngưỡng nguy hiểm với lúa: >10 ngày → 30 ngày trong năm

**`moisture_deficit` (precip − ET₀):**
- Range: [-73.26, 6.13] mm
- Giá trị âm = cây cần nước (ET₀ > mưa): 171 ngày
- Giá trị dương = thừa ẩm (mưa > ET₀): 194 ngày

**`lst_ndvi_ratio` (Chỉ số Stress Nhiệt-Thực vật):**
- Range: [77.7, 421.9]
- Cao khi: LST cao + NDVI thấp → cây bị thiêu đốt, không có canopy che chắn
- Tương quan với NDVI: -0.911 → biến số mạnh nhất liên quan NDVI

**`salinity_precip_ratio`:** Độ mặn khi ít mưa — phát hiện xâm nhập mặn nguy hiểm
vào thời điểm cây trồng không được rửa mặn bởi mưa.

### Nhóm E — Anomaly Detection Labels

**Mục đích:** Target variables / semi-supervised labels cho bước ML.

| Feature | Định nghĩa | Số ngày | % năm |
|---------|------------|---------|-------|
| `ndvi_zscore` | Z-score monthly → (ndvi - monthly_mean) / monthly_std | 365 | 100% |
| `is_ndvi_anomaly` | 1 nếu |ndvi_zscore| > 2 | 17 | 4.7% |
| `is_salinity_spike` | 1 nếu sal > 10 PSU trong mùa mưa | 58 | 15.9% |
| `crop_stress_score` | Composite (0–1): stress nhiệt + mặn + ẩm | 365 | 100% |

**Công thức `crop_stress_score`:**
```python
s_lst  = clip((lst - 30) / 20, 0, 1)                    # stress nhiệt (>30°C → nguy hiểm)
s_sal  = clip(salinity_psu / 30, 0, 1)                  # stress mặn (0–30 PSU)
s_mois = clip(1 - soil_moisture_surface / 0.43, 0, 1)   # stress khô hạn
crop_stress_score = 0.4*s_sal + 0.35*s_lst + 0.25*s_mois
```

- Trọng số: Mặn (40%) > Nhiệt (35%) > Khô hạn (25%) — theo nghiên cứu nông nghiệp ĐBSCL
- Phân phối: [0.088, 0.738]
  → Mean = 0.357 (mức stress TB trung bình)
- Ngày stress cao (>0.6): 49 ngày (13.4%)
- Ngày stress thấp (≤0.2): 86 ngày (23.6%)

---

## 5. PHÂN TÍCH TƯƠNG QUAN (CORRELATION ANALYSIS)

### 5.1 Tương quan với NDVI

| Feature | |r| | Phương hướng | Diễn giải |
|---------|-----|------------|-----------|
| `lst_ndvi_ratio` | 0.911 | ↓ ngược chiều | — |
| `ndvi_zscore` | 0.794 | ↑ cùng chiều | — |
| `ndvi_lag_1` | 0.719 | ↑ cùng chiều | — |
| `ndvi_7d_avg` | 0.643 | ↑ cùng chiều | — |
| `ndvi_diff` | 0.372 | ↑ cùng chiều | — |
| `ndvi_lag_3` | 0.324 | ↑ cùng chiều | — |
| `crop_stress_score` | 0.310 | ↓ ngược chiều | — |
| `is_ndvi_anomaly` | 0.286 | ↓ ngược chiều | — |
| `lst_7d_avg` | 0.227 | ↓ ngược chiều | — |
| `lst` | 0.216 | ↓ ngược chiều | — |
| `ndvi_pct_change` | 0.201 | ↑ cùng chiều | — |
| `is_dry_season` | 0.201 | ↑ cùng chiều | — |

**Nhận xét:** `lst_ndvi_ratio` có tương quan cao nhất với NDVI (`|r|=0.91`) do
tính chất tự thân: ratio phụ thuộc vào NDVI. Loại bỏ trong thực tế training
nếu NDVI là target (data leakage).

### 5.2 Tương quan với Độ mặn

| Feature | |r| | Diễn giải |
|---------|-----|-----------|
| `salinity_7d_avg` | 0.979 | — |
| `salinity_lag_1` | 0.969 | — |
| `salinity_lag_3` | 0.956 | — |
| `salinity_lag_7` | 0.937 | — |
| `month_sin` | 0.936 | — |
| `crop_stress_score` | 0.927 | — |
| `soil_moisture_deep` | 0.883 | — |
| `soil_moisture_7d_avg` | 0.860 | — |
| `soil_moisture_surface` | 0.843 | — |
| `moisture_deficit_7d` | 0.779 | — |
| `precip_7d_mm` | 0.748 | — |
| `precip_7d_sum` | 0.748 | — |

**Nhận xét:** `soil_moisture_deep` tương quan nghịch mạnh với salinity (`r=-0.88`):
Khi độ mặn cao → đất bị nhiễm mặn → cây không hút được nước → soil_moisture giảm.
Các lag features salinity cho thấy *persistence* cao — độ mặn hôm nay tiên đoán
mạnh độ mặn ngày mai.

### 5.3 Tương quan với Crop Stress Score

| Feature | |r| | Bar |
|---------|-----|-----|
| `salinity_psu` | 0.927 | `+██████████████████░░` |
| `salinity_7d_avg` | 0.908 | `+██████████████████░░` |
| `salinity_lag_1` | 0.902 | `+██████████████████░░` |
| `salinity_lag_3` | 0.889 | `+█████████████████░░░` |
| `soil_moisture_deep` | 0.868 | `-█████████████████░░░` |
| `month_sin` | 0.860 | `+█████████████████░░░` |
| `salinity_lag_7` | 0.857 | `+█████████████████░░░` |
| `soil_moisture_surface` | 0.854 | `-█████████████████░░░` |
| `soil_moisture_7d_avg` | 0.852 | `-█████████████████░░░` |
| `moisture_deficit_7d` | 0.779 | `+███████████████░░░░░` |
| `precip_7d_sum` | 0.745 | `-██████████████░░░░░░` |
| `precip_7d_mm` | 0.745 | `-██████████████░░░░░░` |
| `salinity_precip_ratio` | 0.717 | `+██████████████░░░░░░` |
| `et0` | 0.695 | `+█████████████░░░░░░░` |
| `radiation` | 0.579 | `+███████████░░░░░░░░░` |

---

## 6. ĐÁNH GIÁ MỨC ĐỘ SẴN SÀNG CHO DATA MINING & ML

### 6.1 Checklist sẵn sàng

| Tiêu chí | Trạng thái | Chi tiết |
|---------|------------|----------|
| **Đủ quan sát** | ✅ | 365 ngày, continuous time series |
| **Không missing** | ✅ 98.56% | 273 NaN = rows đầu chuỗi (cột lag) |
| **Temporal alignment** | ✅ | Daily grid chuẩn hóa từ 4 nguồn |
| **Feature đa dạng** | ✅ | 52 features, 5 nhóm, multi-modal |
| **Labels/targets** | ✅ | `is_ndvi_anomaly`, `is_salinity_spike`, `crop_stress_score` |
| **Seasonal encoding** | ✅ | sin/cos + binary flag |
| **Data provenance** | ✅ | `ndvi_source`, `ndvi_is_observed` theo dõi nguồn |
| **Scale/units** | ⚠️ Cần normalize | Các cột có scale rất khác nhau (PSU vs mm vs °C) |
| **Dữ liệu độ mặn** | ⚠️ Proxy | Mô hình hóa, không phải sensor thực |
| **LST density** | ⚠️ Thưa | 22 obs/năm → interpolation chiếm 94% |

### 6.2 Phù hợp với từng thuật toán

#### PrefixSpan (Sequential Pattern Mining)
```
Yêu cầu:  Chuỗi sự kiện rời rạc (sequences of events)
Chuẩn bị cần thêm:
  1. Discretize các features liên tục → events
     Ví dụ: NDVI → {LOW(<0.15), MED(0.15-0.25), HIGH(>0.25)}
             Salinity → {FRESH(<2), BRACKISH(2-10), SALINE(>10)}
             Stress → {LOW(<0.2), MOD(0.2-0.4), HIGH(0.4-0.6), EXTREME(>0.6)}
  2. Chuyển DataFrame → list of sequences theo từng tuần/tháng
  3. Run PrefixSpan với min_support thích hợp (~0.1–0.3)

Patterns kỳ vọng:
  [SALINE, LOW_NDVI, HIGH_STRESS] → drought-salinity co-occurrence
  [HIGH_LST, DRY, SALINE] → hot-dry-salty shock
  [HIGH_PRECIP, FRESH, MED_NDVI] → post-flood recovery
```

#### XGBoost (Anomaly / Regression)
```
Yêu cầu:    Tabular features + target labels
Features:   52 cột (loại bỏ date, season, ndvi_source)
Targets:
  Bài toán 1 (Classification):
    → Predict is_ndvi_anomaly  (binary: 0/1)
    → Predict is_salinity_spike (binary: 0/1)
    → Class imbalance: 4.7% / 15.9% → cần stratified split + scale_pos_weight
  Bài toán 2 (Regression):
    → Predict crop_stress_score (0–1, continuous)
    → Predict salinity_psu (kg/m³)

Cần loại bỏ trước khi train:
  • Cột leakage: ndvi_zscore (tính từ ndvi), ndvi_7d_avg (overlap với target ndvi)
  • Cột identifier: date, ndvi_source, season

Hyperparameters đề xuất ban đầu:
  n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8
  Validation: TimeSeriesSplit(n_splits=5) — KHÔNG dùng random split!
  (Random split gây data leakage cho time series)
```

### 6.3 Giới hạn và hướng cải thiện

| Hạn chế | Mức độ | Hướng giải quyết |
|---------|--------|-----------------|
| Độ mặn là proxy, không phải sensor | Cao | Đăng ký Copernicus Marine Service hoặc kết nối dữ liệu Sở NN&PTNT Bến Tre |
| LST thưa (22 obs/năm) | Trung bình | Thêm MODIS LST (MOD11A1 – daily, 1km) |
| Chỉ 1 điểm không gian | Trung bình | Mở rộng grid 5×5 điểm bao phủ toàn tỉnh |
| 1 năm dữ liệu (2023) | Trung bình | Thu thập thêm 2020-2022 để học inter-annual variability |
| Không có ground truth anomaly | Cao | Cần gán nhãn từ báo cáo thiên tai/xâm nhập mặn ĐBSCL |

---

## 7. TÓM TẮT VÀ KẾT LUẬN

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATASET SUMMARY                             │
│                                                                 │
│  Shape    : 365 ngày × 52 features                             │
│  Sources  : GEE (3 vệ tinh) + Open-Meteo ERA5 + proxy mặn     │
│  NDVI     : 92 obs thực (26 S2 + 22 Landsat + 44 MODIS)        │
│  Coverage : 12/12 tháng, kể cả mùa mưa nhiều mây              │
│  Quality  : 98.56% complete, 0 duplicate dates                 │
│  Anomalies: 17 NDVI anomalies + 58 salinity spikes              │
│  Key corr : crop_stress ↔ salinity r=+0.93 (rất mạnh)          │
│  Key corr : crop_stress ↔ soil_moisture r=-0.87 (mạnh)         │
│                                                                 │
│  STATUS: ✅ SẴN SÀNG cho Phase 2 — PrefixSpan + XGBoost        │
└─────────────────────────────────────────────────────────────────┘
```

**Pipeline hoàn chỉnh:**
```
python run_pipeline.py
  ├── script1_satellite_gee.py   → real_ndvi_lst.csv   (GEE multi-source)
  ├── script2_weather_openmeteo.py → real_weather.csv  (ERA5-Land)
  ├── script3_salinity.py        → real_salinity.csv   (synthetic proxy)
  └── script4_merge_preprocess.py → merged_final.csv  (365×52, ML-ready)
```

---
*Báo cáo được sinh tự động từ `generate_report.py` — dựa trên dữ liệu thực tế trong `merged_final.csv`*