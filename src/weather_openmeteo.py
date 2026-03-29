"""SaltySeq Script 2: Open-Meteo weather panel data fetch."""

from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.pipeline_config import (
    END_DATE,
    HTTP_MAX_RETRIES,
    HTTP_RETRY_SLEEP_SEC,
    HTTP_TIMEOUT_DAILY_SEC,
    HTTP_TIMEOUT_HOURLY_SEC,
    LOCATIONS,
    OUTPUT_DIR,
    START_DATE,
    LocationConfig,
)

OUTPUT_FILE = OUTPUT_DIR / "real_weather.csv"
BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "precipitation_sum",
    "rain_sum",
    "et0_fao_evapotranspiration",
    "shortwave_radiation_sum",
    "windspeed_10m_max",
]

HOURLY_VARS = [
    "soil_moisture_0_to_7cm",
    "soil_moisture_7_to_28cm",
    "soil_temperature_0_to_7cm",
]

LOGGER = logging.getLogger("saltyseq.weather")


def configure_logging() -> None:
    """Configure logger for script execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def build_session() -> requests.Session:
    """Build a requests session with retry policy."""
    session = requests.Session()
    retry = Retry(
        total=HTTP_MAX_RETRIES,
        read=HTTP_MAX_RETRIES,
        connect=HTTP_MAX_RETRIES,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _request_json(
    session: requests.Session,
    params: dict[str, Any],
    timeout_sec: int,
    context: str,
) -> dict[str, Any]:
    """Execute GET request with lightweight manual retry for non-HTTP errors."""
    for attempt in range(1, HTTP_MAX_RETRIES + 1):
        try:
            resp = session.get(BASE_URL, params=params, timeout=timeout_sec)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(
                "Open-Meteo call failed (%s), attempt %s/%s: %s",
                context,
                attempt,
                HTTP_MAX_RETRIES,
                exc,
            )
            if attempt == HTTP_MAX_RETRIES:
                raise
            time.sleep(HTTP_RETRY_SLEEP_SEC * attempt)

    return {}


def fetch_daily_weather(
    session: requests.Session,
    location: LocationConfig,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch daily weather variables for one location."""
    params = {
        "latitude": location.lat,
        "longitude": location.lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": ",".join(DAILY_VARS),
        "timezone": "Asia/Ho_Chi_Minh",
    }

    data = _request_json(
        session=session,
        params=params,
        timeout_sec=HTTP_TIMEOUT_DAILY_SEC,
        context=f"daily:{location.location_id}",
    )

    daily = data["daily"]
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(daily["time"]),
            "temp_max": daily["temperature_2m_max"],
            "temp_min": daily["temperature_2m_min"],
            "temp_mean": daily["temperature_2m_mean"],
            "precipitation": daily["precipitation_sum"],
            "rain": daily["rain_sum"],
            "et0": daily["et0_fao_evapotranspiration"],
            "radiation": daily["shortwave_radiation_sum"],
            "wind_max": daily["windspeed_10m_max"],
        }
    )
    return df


def fetch_soil_data(
    session: requests.Session,
    location: LocationConfig,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch hourly soil data and aggregate to daily mean for one location."""
    params = {
        "latitude": location.lat,
        "longitude": location.lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "Asia/Ho_Chi_Minh",
    }

    data = _request_json(
        session=session,
        params=params,
        timeout_sec=HTTP_TIMEOUT_HOURLY_SEC,
        context=f"soil:{location.location_id}",
    )

    hourly = data["hourly"]
    df_hourly = pd.DataFrame(
        {
            "datetime": pd.to_datetime(hourly["time"]),
            "soil_moisture_surface": hourly["soil_moisture_0_to_7cm"],
            "soil_moisture_deep": hourly["soil_moisture_7_to_28cm"],
            "soil_temp": hourly["soil_temperature_0_to_7cm"],
        }
    )

    df_hourly["date"] = df_hourly["datetime"].dt.normalize()
    return df_hourly.drop(columns=["datetime"]).groupby("date").mean().reset_index()


def fetch_location_weather(
    session: requests.Session,
    location: LocationConfig,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch and merge weather + soil panel data for one location."""
    daily_df = fetch_daily_weather(session, location, start_date, end_date)
    soil_df = fetch_soil_data(session, location, start_date, end_date)

    merged = daily_df.merge(soil_df, on="date", how="left")
    merged["location_id"] = location.location_id
    merged["location_name"] = location.location_name
    merged["lat"] = location.lat
    merged["lon"] = location.lon
    merged["distance_to_estuary_km"] = location.distance_to_estuary_km

    cols = [
        "date",
        "location_id",
        "location_name",
        "lat",
        "lon",
        "distance_to_estuary_km",
        "temp_max",
        "temp_min",
        "temp_mean",
        "precipitation",
        "rain",
        "et0",
        "radiation",
        "wind_max",
        "soil_moisture_surface",
        "soil_moisture_deep",
        "soil_temp",
    ]
    return merged[cols].sort_values("date").reset_index(drop=True)


def main() -> pd.DataFrame:
    """Run weather collection for all configured locations."""
    configure_logging()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Starting Open-Meteo collection.")
    LOGGER.info("Date range: %s -> %s", START_DATE, END_DATE)
    LOGGER.info("Locations: %s", len(LOCATIONS))

    session = build_session()
    frames: list[pd.DataFrame] = []

    for location in LOCATIONS:
        LOGGER.info("Fetching weather for %s", location.location_id)
        try:
            df_loc = fetch_location_weather(session, location, START_DATE, END_DATE)
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Failed location %s: %s", location.location_id, exc)
            continue

        frames.append(df_loc)
        LOGGER.info(
            "Location %s complete: %s rows | missing=%s",
            location.location_id,
            len(df_loc),
            int(df_loc.isna().sum().sum()),
        )

        # Mild pacing to reduce burst traffic.
        time.sleep(0.5)

    if not frames:
        raise RuntimeError("No weather records were fetched for any location.")

    df_all = pd.concat(frames, ignore_index=True)
    df_all = (
        df_all.sort_values(["location_id", "date"])
        .drop_duplicates(subset=["location_id", "date"], keep="first")
        .reset_index(drop=True)
    )

    df_all.to_csv(OUTPUT_FILE, index=False)
    LOGGER.info("Saved weather panel: %s", OUTPUT_FILE)
    LOGGER.info(
        "Output rows=%s | locations=%s | missing=%s",
        len(df_all),
        df_all["location_id"].nunique(),
        int(df_all.isna().sum().sum()),
    )

    return df_all


if __name__ == "__main__":
    main()
