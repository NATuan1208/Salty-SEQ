# ============================================================
# SaltySeq — Script 2: REAL Weather Data (Open-Meteo API)
# ============================================================
# Mục đích: Lấy dữ liệu khí tượng hàng ngày THẬT từ Open-Meteo
#           cho cùng tọa độ và timeframe với Script 1.
#
# Data source: Open-Meteo Historical Weather API
#   - Backend: ECMWF ERA5 + ERA5-Land reanalysis
#   - Resolution: 0.1° (~11km grid)
#   - Miễn phí, không cần API key
#
# Output: data/real_weather.csv
# ============================================================

import pandas as pd
import numpy as np
import requests
import time
from pathlib import Path

# ── CẤU HÌNH ───────────────────────────────────────────────
TARGET_LAT = 10.24
TARGET_LON = 106.37
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"

OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "real_weather.csv"

# Open-Meteo Archive API (Historical data)
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Biến daily cần lấy — đầy đủ cho agriculture analysis
DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "et0_fao_evapotranspiration",    # Chỉ số bốc thoát hơi nước (FAO Penman-Monteith)
    "shortwave_radiation_sum",        # Tổng bức xạ sóng ngắn (MJ/m²)
    "windspeed_10m_max",
]

# Biến hourly → aggregate thành daily (soil data)
HOURLY_VARS = [
    "soil_moisture_0_to_7cm",        # Độ ẩm đất lớp bề mặt (m³/m³)
    "soil_moisture_7_to_28cm",       # Độ ẩm đất lớp sâu hơn
    "soil_temperature_0_to_7cm",     # Nhiệt độ đất (°C)
]


# ── FETCH DAILY WEATHER ────────────────────────────────────
def fetch_daily_weather():
    """
    Gọi Open-Meteo Archive API lấy dữ liệu daily.
    API reference: https://open-meteo.com/en/docs/historical-weather-api
    """
    print("[i] Đang gọi Open-Meteo Daily API...")

    params = {
        "latitude": TARGET_LAT,
        "longitude": TARGET_LON,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(DAILY_VARS),
        "timezone": "Asia/Ho_Chi_Minh",
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    daily = data["daily"]
    df = pd.DataFrame({
        'date': pd.to_datetime(daily['time']),
        'temp_max': daily['temperature_2m_max'],
        'temp_min': daily['temperature_2m_min'],
        'temp_mean': daily['temperature_2m_mean'],
        'precipitation': daily['precipitation_sum'],
        'rain': daily['rain_sum'],
        'et0': daily['et0_fao_evapotranspiration'],
        'radiation': daily['shortwave_radiation_sum'],
        'wind_max': daily['windspeed_10m_max'],
    })

    print(f"[✓] Daily weather: {len(df)} ngày")
    print(f"    Temp: {df['temp_mean'].min():.1f}–{df['temp_mean'].max():.1f}°C")
    print(f"    Precip total: {df['precipitation'].sum():.1f} mm")
    return df


# ── FETCH HOURLY SOIL → DAILY ──────────────────────────────
def fetch_soil_data():
    """
    Lấy soil moisture/temperature (hourly) rồi aggregate thành daily mean.
    ERA5-Land soil moisture đơn vị: m³/m³ (volumetric).
    """
    print("\n[i] Đang gọi Open-Meteo Hourly Soil API...")

    params = {
        "latitude": TARGET_LAT,
        "longitude": TARGET_LON,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "Asia/Ho_Chi_Minh",
    }

    response = requests.get(BASE_URL, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    hourly = data["hourly"]
    df_h = pd.DataFrame({
        'datetime': pd.to_datetime(hourly['time']),
        'soil_moisture_surface': hourly['soil_moisture_0_to_7cm'],
        'soil_moisture_deep': hourly['soil_moisture_7_to_28cm'],
        'soil_temp': hourly['soil_temperature_0_to_7cm'],
    })

    # Aggregate hourly → daily mean
    df_h['date'] = df_h['datetime'].dt.normalize()
    df_daily = df_h.drop(columns='datetime').groupby('date').mean().reset_index()

    print(f"[✓] Soil data: {len(df_daily)} ngày (aggregated từ hourly)")
    print(f"    Soil moisture surface: {df_daily['soil_moisture_surface'].mean():.4f} m³/m³")
    return df_daily


# ── MAIN ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Script 2: REAL Weather Data (Open-Meteo)")
    print(f"  Tọa độ: ({TARGET_LAT}, {TARGET_LON}) — Bến Tre, VN")
    print(f"  Thời gian: {START_DATE} → {END_DATE}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Lấy daily weather
    df_weather = fetch_daily_weather()

    # Lấy soil data (hourly → daily)
    df_soil = fetch_soil_data()

    # Merge weather + soil
    df = df_weather.merge(df_soil, on='date', how='left')

    # Kiểm tra quality
    missing = df.isnull().sum()
    total_missing = missing.sum()
    print(f"\n[i] Final dataset: {df.shape[0]} rows × {df.shape[1]} columns")
    if total_missing > 0:
        print(f"    Missing values: {total_missing}")
        for col in df.columns:
            if missing[col] > 0:
                print(f"      {col}: {missing[col]} ({missing[col]/len(df)*100:.1f}%)")
    else:
        print(f"    Missing values: 0 — HOÀN HẢO")

    # Lưu CSV
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[✓] Đã lưu: {OUTPUT_FILE}")
    print("\n--- Preview ---")
    print(df.head(10).to_string())

    return df


if __name__ == "__main__":
    main()
