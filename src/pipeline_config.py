"""Shared configuration for SaltySeq data pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True)
class LocationConfig:
    """Spatial configuration for one monitoring location."""

    location_id: str
    location_name: str
    lat: float
    lon: float
    buffer_m: int
    distance_to_estuary_km: float


START_DATE: Final[str] = "2015-01-01"
END_DATE: Final[str] = "2022-12-31"

GEE_PROJECT_ID: Final[str] = "cs313project-489508"
GEE_CHUNK_MONTHS: Final[int] = 6
GEE_MAX_RETRIES: Final[int] = 3
GEE_RETRY_SLEEP_SEC: Final[int] = 8

HTTP_MAX_RETRIES: Final[int] = 3
HTTP_RETRY_SLEEP_SEC: Final[int] = 3
HTTP_TIMEOUT_DAILY_SEC: Final[int] = 45
HTTP_TIMEOUT_HOURLY_SEC: Final[int] = 75

OUTPUT_DIR: Final[Path] = Path(__file__).parent.parent / "data"

LOCATIONS: Final[list[LocationConfig]] = [
    LocationConfig(
        location_id="BT_BinhDai",
        location_name="Binh Dai",
        lat=10.11,
        lon=106.69,
        buffer_m=700,
        distance_to_estuary_km=4.0,
    ),
    LocationConfig(
        location_id="BT_BaTri",
        location_name="Ba Tri",
        lat=10.05,
        lon=106.59,
        buffer_m=700,
        distance_to_estuary_km=7.5,
    ),
    LocationConfig(
        location_id="BT_ThanhPhu",
        location_name="Thanh Phu",
        lat=9.95,
        lon=106.53,
        buffer_m=700,
        distance_to_estuary_km=11.0,
    ),
    LocationConfig(
        location_id="BT_GiongTrom",
        location_name="Giong Trom",
        lat=10.17,
        lon=106.47,
        buffer_m=700,
        distance_to_estuary_km=19.0,
    ),
    LocationConfig(
        location_id="BT_ChauThanh",
        location_name="Chau Thanh",
        lat=10.27,
        lon=106.33,
        buffer_m=700,
        distance_to_estuary_km=26.0,
    ),
]
