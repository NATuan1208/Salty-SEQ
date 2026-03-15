# ============================================================
# SaltySeq — Script 4: Merging & Preprocessing Strategy
# ============================================================
# Mục đích: Ghép 3 nguồn dữ liệu thành 1 DataFrame sạch, sẵn sàng
#           cho PrefixSpan (Sequential Pattern Mining) và XGBoost
#           (Anomaly Detection).
#
# ┌────────────────────────────────────────────────────────┐
# │  SPATIO-TEMPORAL ALIGNMENT STRATEGY                    │
# │                                                        │
# │  Problem:                                              │
# │    • Satellite NDVI: ~5 ngày (irregular, cloud gaps)   │
# │    • Satellite LST:  ~8-16 ngày (Landsat 8+9 merged)  │
# │    • Weather:        daily (100% complete)             │
# │    • Salinity:       daily (proxy, 100% complete)      │
# │                                                        │
# │  Solution:                                             │
# │    1. Tạo daily date index (365 ngày)                  │
# │    2. Left-join satellite data (sparse) lên daily grid │
# │    3. Linear interpolation cho NDVI/LST gaps           │
# │       (limit=15 ngày — beyond that is unreliable)      │
# │    4. Inner-merge với weather + salinity (daily)        │
# │    5. Feature engineering: rolling stats, lag, anomaly  │
# │    6. Forward-fill cho remaining NaN edges              │
# └────────────────────────────────────────────────────────┘
#
# Output: data/merged_final.csv
# ============================================================

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ── CẤU HÌNH ───────────────────────────────────────────────
START_DATE = "2023-01-01"
END_DATE = "2023-12-31"

OUTPUT_DIR = Path(__file__).parent.parent / "data"
SATELLITE_FILE = OUTPUT_DIR / "real_ndvi_lst.csv"
WEATHER_FILE = OUTPUT_DIR / "real_weather.csv"
SALINITY_FILE = OUTPUT_DIR / "real_salinity.csv"
OUTPUT_FILE = OUTPUT_DIR / "merged_final.csv"


# ── STEP 1: LOAD ALL SOURCES ───────────────────────────────
def load_sources():
    """Đọc 3 file CSV từ Script 1, 2, 3."""
    print("[Step 1] Loading data sources...")

    # Pre-flight: kiểm tra file tồn tại trước khi đọc
    missing = []
    if not SATELLITE_FILE.exists():
        missing.append(f"  • {SATELLITE_FILE.name}  → chạy script1_satellite_gee.py trước")
    if not WEATHER_FILE.exists():
        missing.append(f"  • {WEATHER_FILE.name}  → chạy script2_weather_openmeteo.py trước")
    if not SALINITY_FILE.exists():
        missing.append(f"  • {SALINITY_FILE.name}  → chạy script3_salinity.py trước")
    if missing:
        raise FileNotFoundError(
            "\n[script4] Thiếu file đầu vào:\n" + "\n".join(missing) +
            "\n\nChạy lệnh:  python run_pipeline.py  để tự động xử lý đúng thứ tự."
        )

    # Satellite (NDVI + LST) — sparse, irregular timestamps
    df_sat = pd.read_csv(SATELLITE_FILE, parse_dates=['date'])
    print(f"  Satellite: {len(df_sat)} rows | "
          f"NDVI valid: {df_sat['ndvi'].notna().sum()} | "
          f"LST valid: {df_sat['lst'].notna().sum()}")

    # Weather — daily, complete
    df_weather = pd.read_csv(WEATHER_FILE, parse_dates=['date'])
    print(f"  Weather:   {len(df_weather)} rows | "
          f"Missing: {df_weather.isnull().sum().sum()}")

    # Salinity — daily
    df_salinity = pd.read_csv(SALINITY_FILE, parse_dates=['date'])
    print(f"  Salinity:  {len(df_salinity)} rows | "
          f"Mean: {df_salinity['salinity_psu'].mean():.2f} PSU")

    return df_sat, df_weather, df_salinity


# ── STEP 2: TEMPORAL ALIGNMENT ─────────────────────────────
def align_to_daily(df_sat):
    """
    ┌─────────────────────────────────────────────────────────┐
    │ SPATIO-TEMPORAL ALIGNMENT: Satellite → Daily Grid       │
    │                                                         │
    │ Tại sao cần alignment?                                  │
    │ • NDVI có ~37-50 data points trong 365 ngày             │
    │ • LST có ~15-25 data points (Landsat revisit dài hơn)   │
    │ • Weather/Salinity có 365 data points                   │
    │                                                         │
    │ Chiến lược:                                             │
    │ 1. Reindex satellite lên daily grid                     │
    │ 2. Linear interpolation (giới hạn 15 ngày liên tục)    │
    │    → Linear > Cubic vì ít artifacts ở biên, robust hơn  │
    │ 3. Đánh dấu cột is_observed để phân biệt real vs interp│
    │ 4. Forward + Backward fill cho edges                    │
    └─────────────────────────────────────────────────────────┘
    """
    print("\n[Step 2] Temporal alignment: Satellite → Daily grid...")

    # Tạo daily date index
    daily_dates = pd.date_range(start=START_DATE, end=END_DATE, freq='D')
    df_daily = pd.DataFrame({'date': daily_dates})

    # Merge satellite (sẽ có nhiều NaN)
    df_daily = df_daily.merge(df_sat, on='date', how='left')

    # Đánh dấu observed vs interpolated
    df_daily['ndvi_is_observed'] = df_daily['ndvi'].notna().astype(int)
    df_daily['lst_is_observed'] = df_daily['lst'].notna().astype(int)

    # Count before interpolation
    ndvi_obs = df_daily['ndvi_is_observed'].sum()
    lst_obs = df_daily['lst_is_observed'].sum()

    # Linear interpolation (limit 15 ngày — beyond that gap is too large)
    df_daily['ndvi'] = df_daily['ndvi'].interpolate(
        method='linear', limit=15, limit_direction='both'
    )
    df_daily['lst'] = df_daily['lst'].interpolate(
        method='linear', limit=15, limit_direction='both'
    )

    # Forward + backward fill cho remaining edge NaN
    df_daily['ndvi'] = df_daily['ndvi'].ffill().bfill()
    df_daily['lst'] = df_daily['lst'].ffill().bfill()

    ndvi_interp = 365 - ndvi_obs
    lst_interp = 365 - lst_obs
    print(f"  NDVI: {ndvi_obs} observed + {ndvi_interp} interpolated = 365 daily")
    print(f"  LST:  {lst_obs} observed + {lst_interp} interpolated = 365 daily")

    return df_daily


# ── STEP 3: MERGE ALL SOURCES ──────────────────────────────
def merge_all(df_daily_sat, df_weather, df_salinity):
    """
    Merge 3 nguồn dữ liệu trên cột Date.
    Inner join: chỉ giữ ngày mà CẢ 3 nguồn đều có dữ liệu.
    """
    print("\n[Step 3] Merging all sources on Date column...")

    # Merge satellite (daily aligned) với weather
    df = df_daily_sat.merge(df_weather, on='date', how='inner')

    # Merge với salinity (chỉ lấy salinity_psu)
    sal_cols = ['date', 'salinity_psu']
    if 'precip_7d_mm' in df_salinity.columns:
        sal_cols.append('precip_7d_mm')
    df = df.merge(df_salinity[sal_cols], on='date', how='inner')

    print(f"  Merged: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"  Date range: {df['date'].min().date()} → {df['date'].max().date()}")

    return df


# ── STEP 4: FEATURE ENGINEERING BASIC ─────────────────────────────
def engineer_features(df):
    """
    Tạo các features cơ bản cho Anomaly Detection & Pattern Mining.

    ┌─────────────────────────────────────────────────────────┐
    │ FEATURE GROUPS:                                         │
    │                                                         │
    │ A. Temporal: DOY, month, season, cyclical encoding      │
    │ B. Rolling: 7-day avg temp, 7-day avg NDVI, etc.        │
    │ C. Lag: NDVI(t-1), NDVI(t-7), salinity(t-1)            │
    │ D. Derived: Days_Without_Rain, moisture_deficit          │
    │ E. Anomaly baseline: Z-score NDVI, salinity threshold   │
    └─────────────────────────────────────────────────────────┘
    """
    print("\n[Step 4] Feature engineering...")
    df = df.copy()

    # ── A. TEMPORAL FEATURES ──
    df['day_of_year'] = df['date'].dt.dayofyear
    df['month'] = df['date'].dt.month
    df['week'] = df['date'].dt.isocalendar().week.astype(int)

    # Mùa vụ: Mùa khô (11-4) vs Mùa mưa (5-10)
    df['season'] = df['month'].apply(lambda m: 'dry' if m in [11,12,1,2,3,4] else 'wet')
    df['is_dry_season'] = (df['season'] == 'dry').astype(int)

    # Cyclical encoding (để model hiểu tháng 12 gần tháng 1)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    n_temporal = 7
    print(f"  A. Temporal features: +{n_temporal}")

    # ── B. ROLLING STATISTICS (7-day windows) ──
    df['temp_7d_avg'] = df['temp_mean'].rolling(7, min_periods=1).mean()
    df['ndvi_7d_avg'] = df['ndvi'].rolling(7, min_periods=1).mean()
    df['precip_7d_sum'] = df['precipitation'].rolling(7, min_periods=1).sum()
    df['salinity_7d_avg'] = df['salinity_psu'].rolling(7, min_periods=1).mean()
    df['lst_7d_avg'] = df['lst'].rolling(7, min_periods=1).mean()
    df['soil_moisture_7d_avg'] = df['soil_moisture_surface'].rolling(7, min_periods=1).mean()
    n_rolling = 6
    print(f"  B. Rolling statistics: +{n_rolling}")

    # ── C. LAG FEATURES (cho PrefixSpan sequential analysis) ──
    for lag in [1, 3, 7]:
        df[f'ndvi_lag_{lag}'] = df['ndvi'].shift(lag)
        df[f'salinity_lag_{lag}'] = df['salinity_psu'].shift(lag)
        df[f'precip_lag_{lag}'] = df['precipitation'].shift(lag)
    n_lag = 9
    print(f"  C. Lag features: +{n_lag}")

    # ── D. DERIVED FEATURES ──
    # Days_Without_Rain: bộ đếm số ngày liên tục không mưa (>= 1mm)
    rain_flag = (df['precipitation'] >= 1.0).astype(int)
    days_no_rain = []
    counter = 0
    for has_rain in rain_flag:
        if has_rain:
            counter = 0
        else:
            counter += 1
        days_no_rain.append(counter)
    df['days_without_rain'] = days_no_rain

    # Moisture deficit: ET0 - Precipitation (dương = thiếu nước)
    df['moisture_deficit'] = df['et0'] - df['precipitation']
    df['moisture_deficit_7d'] = df['moisture_deficit'].rolling(7, min_periods=1).sum()

    # NDVI rate of change
    df['ndvi_diff'] = df['ndvi'].diff()
    df['ndvi_pct_change'] = df['ndvi'].pct_change()

    # LST-NDVI interaction (nhiệt + cây trồng)
    df['lst_ndvi_ratio'] = df['lst'] / df['ndvi'].clip(lower=0.1)

    # Salinity-precipitation interaction
    df['salinity_precip_ratio'] = df['salinity_psu'] / df['precipitation'].clip(lower=0.1)

    n_derived = 7
    print(f"  D. Derived features: +{n_derived}")

    # ── E. ANOMALY BASELINE (Z-score) ──
    # NDVI anomaly: giá trị bất thường so với monthly mean
    monthly_stats = df.groupby('month')['ndvi'].agg(['mean', 'std'])
    df = df.merge(
        monthly_stats.rename(columns={'mean': 'ndvi_monthly_mean', 'std': 'ndvi_monthly_std'}),
        left_on='month', right_index=True
    )
    df['ndvi_zscore'] = (df['ndvi'] - df['ndvi_monthly_mean']) / df['ndvi_monthly_std'].clip(lower=0.01)
    df['is_ndvi_anomaly'] = (df['ndvi_zscore'].abs() > 2.0).astype(int)

    # Salinity anomaly (> 4 PSU trong mùa mưa = bất thường)
    df['is_salinity_spike'] = (
        (df['salinity_psu'] > 10) & (df['is_dry_season'] == 0)
    ).astype(int)

    # Crop stress composite: NDVI giảm + Salinity tăng + Soil khô
    df['crop_stress_score'] = (
        (1 - df['ndvi'] / df['ndvi'].max()) * 0.4 +
        (df['salinity_psu'] / df['salinity_psu'].max()) * 0.4 +
        (1 - df['soil_moisture_surface'] / df['soil_moisture_surface'].max()) * 0.2
    )

    # Cleanup temporary columns
    df = df.drop(columns=['ndvi_monthly_mean', 'ndvi_monthly_std'], errors='ignore')

    n_anomaly = 4
    print(f"  E. Anomaly features: +{n_anomaly}")

    return df


# ── STEP 5: FINAL CLEANUP ──────────────────────────────────
def final_cleanup(df):
    """
    Xử lý NaN còn sót (chủ yếu từ lag/rolling ở đầu chuỗi).
    Strategy: Forward fill → Backward fill.
    """
    print("\n[Step 5] Final cleanup (handle remaining NaN)...")

    missing_before = df.isnull().sum().sum()

    # Forward fill → backward fill cho numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].ffill().bfill()

    missing_after = df.isnull().sum().sum()
    print(f"  NaN before: {missing_before} → after: {missing_after}")

    return df


# ── STEP 6: DATA PROFILING ─────────────────────────────────
def profile_output(df):
    """In thống kê tổng quan cho team review."""
    print("\n" + "=" * 70)
    print("  FINAL DATASET PROFILING")
    print("=" * 70)

    print(f"\nShape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"Date: {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"Completeness: {(1 - df.isnull().sum().sum() / (df.shape[0] * df.shape[1])) * 100:.2f}%")

    print(f"\n── df.head(5) ──")
    # Chọn columns quan trọng để hiển thị gọn
    key_cols = ['date', 'ndvi', 'lst', 'temp_mean', 'precipitation',
                'soil_moisture_surface', 'salinity_psu',
                'days_without_rain', 'temp_7d_avg',
                'ndvi_zscore', 'is_ndvi_anomaly', 'crop_stress_score']
    display_cols = [c for c in key_cols if c in df.columns]
    print(df[display_cols].head(5).to_string())

    print(f"\n── df.info() ──")
    print(f"Dtypes: {df.dtypes.value_counts().to_dict()}")
    print(f"Memory: {df.memory_usage(deep=True).sum() / 1024:.1f} KB")

    print(f"\n── df.describe() (key features) ──")
    desc_cols = ['ndvi', 'lst', 'temp_mean', 'precipitation',
                 'soil_moisture_surface', 'salinity_psu',
                 'days_without_rain', 'crop_stress_score']
    desc_cols = [c for c in desc_cols if c in df.columns]
    print(df[desc_cols].describe().round(4).to_string())

    # Anomaly summary
    if 'is_ndvi_anomaly' in df.columns:
        n_anom = df['is_ndvi_anomaly'].sum()
        print(f"\n── Anomaly Summary ──")
        print(f"  NDVI anomalies (Z>2): {n_anom} / {len(df)} ({n_anom/len(df)*100:.1f}%)")
    if 'is_salinity_spike' in df.columns:
        n_spike = df['is_salinity_spike'].sum()
        print(f"  Salinity spikes:      {n_spike} / {len(df)} ({n_spike/len(df)*100:.1f}%)")

    # Correlation with crop stress
    print(f"\n── Top Correlations với crop_stress_score ──")
    if 'crop_stress_score' in df.columns:
        numeric = df.select_dtypes(include=[np.number])
        corr = numeric.corr()['crop_stress_score'].drop('crop_stress_score', errors='ignore')
        top = corr.abs().sort_values(ascending=False).head(10)
        for col in top.index:
            val = corr[col]
            bar = '█' * int(abs(val) * 20)
            sign = '+' if val > 0 else '-'
            print(f"    {col:30s} {sign}{abs(val):.4f} {bar}")


# ── MAIN ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Script 4: Merge & Preprocessing Pipeline")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # 1. Load
    df_sat, df_weather, df_salinity = load_sources()

    # 2. Temporal alignment (satellite → daily)
    df_daily_sat = align_to_daily(df_sat)

    # 3. Merge all
    df = merge_all(df_daily_sat, df_weather, df_salinity)

    # 4. Feature engineering
    df = engineer_features(df)

    # 5. Final cleanup
    df = final_cleanup(df)

    # 6. Save
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[✓] Đã lưu: {OUTPUT_FILE}")

    # 7. Profile
    profile_output(df)

    print(f"\n{'='*60}")
    print(f"  PIPELINE HOÀN TẤT — Ready for PrefixSpan + XGBoost")
    print(f"{'='*60}")

    return df


if __name__ == "__main__":
    main()
