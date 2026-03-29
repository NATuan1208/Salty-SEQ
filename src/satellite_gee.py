"""SaltySeq Script 1: Satellite panel data fetch with temporal chunking."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Iterable

import ee
import pandas as pd

from src.pipeline_config import (
    END_DATE,
    GEE_CHUNK_MONTHS,
    GEE_MAX_RETRIES,
    GEE_PROJECT_ID,
    GEE_RETRY_SLEEP_SEC,
    LOCATIONS,
    OUTPUT_DIR,
    START_DATE,
    LocationConfig,
)

OUTPUT_FILE = OUTPUT_DIR / "real_ndvi_lst.csv"

LOGGER = logging.getLogger("saltyseq.satellite")


def configure_logging() -> None:
    """Configure logger for script execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def init_gee() -> None:
    """Authenticate and initialize Google Earth Engine."""
    try:
        ee.Initialize(project=GEE_PROJECT_ID)
        LOGGER.info("GEE initialized with cached credentials.")
    except Exception:
        LOGGER.info("GEE credentials not found in session. Starting authentication...")
        ee.Authenticate()
        ee.Initialize(project=GEE_PROJECT_ID)
        LOGGER.info("GEE initialized after interactive authentication.")


def iter_date_chunks(
    start_date: str,
    end_date: str,
    chunk_months: int,
) -> Iterable[tuple[str, str]]:
    """Yield inclusive date chunks in YYYY-MM-DD format."""
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    cursor = start_ts

    while cursor <= end_ts:
        chunk_end = min(
            cursor + pd.DateOffset(months=chunk_months) - pd.Timedelta(days=1),
            end_ts,
        )
        yield cursor.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")
        cursor = chunk_end + pd.Timedelta(days=1)


def mask_s2_clouds(image: ee.Image) -> ee.Image:
    """Cloud masking for Sentinel-2 SR Harmonized collection."""
    qa = image.select("QA60")
    cloud_mask = qa.bitwiseAnd(1 << 10).eq(0).And(qa.bitwiseAnd(1 << 11).eq(0))
    return image.updateMask(cloud_mask).divide(10000).set(
        "system:time_start", image.get("system:time_start")
    )


def compute_ndvi(image: ee.Image) -> ee.Image:
    """Compute NDVI for Sentinel-2 imagery."""
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return image.addBands(ndvi).copyProperties(image, ["system:time_start"])


def compute_lst_landsat(image: ee.Image) -> ee.Image:
    """Compute LST in Celsius from Landsat Collection 2 ST_B10."""
    qa = image.select("QA_PIXEL")
    cloud_mask = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))

    lst = (
        image.select("ST_B10")
        .multiply(0.00341802)
        .add(149.0)
        .subtract(273.15)
        .rename("LST")
    )
    return image.addBands(lst).updateMask(cloud_mask).copyProperties(
        image, ["system:time_start"]
    )


def _run_feature_export(
    collection: ee.ImageCollection,
    extract_fn,
    context: str,
) -> list[dict]:
    """Execute getInfo with retries for transient Earth Engine failures."""
    for attempt in range(1, GEE_MAX_RETRIES + 1):
        try:
            return collection.map(extract_fn).getInfo()["features"]
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning(
                "GEE export failed (%s), attempt %s/%s: %s",
                context,
                attempt,
                GEE_MAX_RETRIES,
                exc,
            )
            if attempt == GEE_MAX_RETRIES:
                raise
            time.sleep(GEE_RETRY_SLEEP_SEC * attempt)

    return []


def fetch_ndvi_sentinel(
    roi: ee.Geometry,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch Sentinel-2 NDVI for a date window."""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(roi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 50))
        .filter(ee.Filter.gt("system:time_start", 0))
        .map(mask_s2_clouds)
        .map(compute_ndvi)
        .select(["NDVI"])
    )

    def extract(image: ee.Image) -> ee.Feature:
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=10,
            maxPixels=1_000_000_000,
        )
        return ee.Feature(
            None,
            {
                "date": image.date().format("YYYY-MM-dd"),
                "ndvi": stats.get("NDVI"),
            },
        )

    features = _run_feature_export(collection, extract, "sentinel")
    rows: list[dict] = []
    for feature in features:
        props = feature.get("properties", {})
        val = props.get("ndvi")
        if val is None:
            continue
        rows.append({"date": props["date"], "ndvi": val, "ndvi_source": "sentinel2"})

    if not rows:
        return pd.DataFrame(columns=["date", "ndvi", "ndvi_source"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)


def fetch_ndvi_landsat(
    roi: ee.Geometry,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch Landsat 8/9 NDVI for a date window."""

    def compute_ndvi_ls(image: ee.Image) -> ee.Image:
        red = image.select("SR_B4").multiply(0.0000275).add(-0.2)
        nir = image.select("SR_B5").multiply(0.0000275).add(-0.2)
        ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
        qa = image.select("QA_PIXEL")
        cloud_mask = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))
        return image.addBands(ndvi).updateMask(cloud_mask).copyProperties(
            image, ["system:time_start"]
        )

    l8 = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterBounds(roi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUD_COVER", 70))
        .filter(ee.Filter.gt("system:time_start", 0))
        .map(compute_ndvi_ls)
        .select(["NDVI"])
    )

    l9 = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterBounds(roi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUD_COVER", 70))
        .filter(ee.Filter.gt("system:time_start", 0))
        .map(compute_ndvi_ls)
        .select(["NDVI"])
    )

    collection = l8.merge(l9).sort("system:time_start")

    def extract(image: ee.Image) -> ee.Feature:
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=30,
            maxPixels=1_000_000_000,
        )
        return ee.Feature(
            None,
            {
                "date": image.date().format("YYYY-MM-dd"),
                "ndvi": stats.get("NDVI"),
            },
        )

    features = _run_feature_export(collection, extract, "landsat_ndvi")

    rows: list[dict] = []
    for feature in features:
        props = feature.get("properties", {})
        val = props.get("ndvi")
        if val is None or not (-0.2 <= val <= 1.0):
            continue
        rows.append({"date": props["date"], "ndvi": val, "ndvi_source": "landsat"})

    if not rows:
        return pd.DataFrame(columns=["date", "ndvi", "ndvi_source"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)


def fetch_ndvi_modis(
    roi: ee.Geometry,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch MODIS Terra/Aqua NDVI for a date window."""

    def extract(image: ee.Image) -> ee.Feature:
        stats = image.select("NDVI").reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=250,
            maxPixels=1_000_000_000,
        )
        return ee.Feature(
            None,
            {
                "date": image.date().format("YYYY-MM-dd"),
                "ndvi": stats.get("NDVI"),
            },
        )

    rows: list[dict] = []
    products = [
        ("MODIS/061/MOD13Q1", "modis_terra"),
        ("MODIS/061/MYD13Q1", "modis_aqua"),
    ]

    for product, source in products:
        collection = (
            ee.ImageCollection(product)
            .filterBounds(roi)
            .filterDate(start_date, end_date)
            .select(["NDVI"])
        )

        features = _run_feature_export(collection, extract, f"{source}_ndvi")

        for feature in features:
            props = feature.get("properties", {})
            val = props.get("ndvi")
            if val is None:
                continue
            scaled = val * 0.0001
            if -0.2 <= scaled <= 1.0:
                rows.append(
                    {
                        "date": props["date"],
                        "ndvi": round(scaled, 6),
                        "ndvi_source": source,
                    }
                )

    if not rows:
        return pd.DataFrame(columns=["date", "ndvi", "ndvi_source"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return (
        df.sort_values(["date", "ndvi_source"])
        .drop_duplicates(subset=["date", "ndvi_source"])
        .reset_index(drop=True)
    )


def fetch_lst_landsat(
    roi: ee.Geometry,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch Landsat 8/9 LST for a date window."""
    l8 = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .filterBounds(roi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUD_COVER", 50))
        .filter(ee.Filter.gt("system:time_start", 0))
        .map(compute_lst_landsat)
        .select(["LST"])
    )

    l9 = (
        ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        .filterBounds(roi)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUD_COVER", 50))
        .filter(ee.Filter.gt("system:time_start", 0))
        .map(compute_lst_landsat)
        .select(["LST"])
    )

    collection = l8.merge(l9).sort("system:time_start")

    def extract(image: ee.Image) -> ee.Feature:
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=30,
            maxPixels=1_000_000_000,
        )
        return ee.Feature(
            None,
            {
                "date": image.date().format("YYYY-MM-dd"),
                "lst": stats.get("LST"),
            },
        )

    features = _run_feature_export(collection, extract, "landsat_lst")

    rows: list[dict] = []
    for feature in features:
        props = feature.get("properties", {})
        val = props.get("lst")
        if val is None:
            continue
        rows.append({"date": props["date"], "lst": val})

    if not rows:
        return pd.DataFrame(columns=["date", "lst"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)


def _combine_ndvi_sources(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Merge NDVI sources by date using source priority."""
    if not frames:
        return pd.DataFrame(columns=["date", "ndvi", "ndvi_source"])

    priority = {
        "sentinel2": 0,
        "landsat": 1,
        "modis_terra": 2,
        "modis_aqua": 3,
    }
    df = pd.concat(frames, ignore_index=True)
    df["priority"] = df["ndvi_source"].map(priority).fillna(99)
    df = (
        df.sort_values(["date", "priority"])
        .drop_duplicates(subset=["date"], keep="first")
        .drop(columns=["priority"])
        .sort_values("date")
        .reset_index(drop=True)
    )
    return df


def fetch_location_satellite(
    location: LocationConfig,
    start_date: str,
    end_date: str,
) -> pd.DataFrame:
    """Fetch and combine satellite data for one location with chunked queries."""
    point = ee.Geometry.Point([location.lon, location.lat])
    roi = point.buffer(location.buffer_m)

    chunk_frames: list[pd.DataFrame] = []

    for chunk_start, chunk_end in iter_date_chunks(start_date, end_date, GEE_CHUNK_MONTHS):
        LOGGER.info(
            "Location %s | chunk %s -> %s",
            location.location_id,
            chunk_start,
            chunk_end,
        )

        df_s2 = fetch_ndvi_sentinel(roi, chunk_start, chunk_end)
        df_ls = fetch_ndvi_landsat(roi, chunk_start, chunk_end)
        df_mod = fetch_ndvi_modis(roi, chunk_start, chunk_end)
        ndvi_parts = [df for df in [df_s2, df_ls, df_mod] if not df.empty]
        df_ndvi = _combine_ndvi_sources(ndvi_parts)

        df_lst = fetch_lst_landsat(roi, chunk_start, chunk_end)
        if df_ndvi.empty and df_lst.empty:
            continue

        merged = (
            pd.merge(df_ndvi, df_lst, on="date", how="outer")
            .sort_values("date")
            .reset_index(drop=True)
        )
        merged["ndvi_source"] = merged["ndvi_source"].fillna("none")
        chunk_frames.append(merged)

    if not chunk_frames:
        return pd.DataFrame(
            columns=[
                "date",
                "location_id",
                "location_name",
                "lat",
                "lon",
                "distance_to_estuary_km",
                "ndvi",
                "ndvi_source",
                "lst",
            ]
        )

    df_loc = pd.concat(chunk_frames, ignore_index=True)

    if not df_loc.empty:
        ndvi_rows = df_loc[df_loc["ndvi"].notna()][["date", "ndvi", "ndvi_source"]]
        ndvi_rows = _combine_ndvi_sources([ndvi_rows])
        lst_rows = (
            df_loc[df_loc["lst"].notna()][["date", "lst"]]
            .sort_values("date")
            .drop_duplicates(subset=["date"], keep="first")
        )
        df_loc = pd.merge(ndvi_rows, lst_rows, on="date", how="outer")

    df_loc["ndvi_source"] = df_loc["ndvi_source"].fillna("none")
    df_loc["location_id"] = location.location_id
    df_loc["location_name"] = location.location_name
    df_loc["lat"] = location.lat
    df_loc["lon"] = location.lon
    df_loc["distance_to_estuary_km"] = location.distance_to_estuary_km

    cols = [
        "date",
        "location_id",
        "location_name",
        "lat",
        "lon",
        "distance_to_estuary_km",
        "ndvi",
        "ndvi_source",
        "lst",
    ]
    return (
        df_loc[cols]
        .sort_values(["location_id", "date"])
        .drop_duplicates(subset=["location_id", "date"], keep="first")
        .reset_index(drop=True)
    )


def main() -> pd.DataFrame:
    """Run satellite collection for all configured locations."""
    configure_logging()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Starting satellite collection.")
    LOGGER.info("Date range: %s -> %s", START_DATE, END_DATE)
    LOGGER.info("Locations: %s", len(LOCATIONS))

    init_gee()

    location_frames: list[pd.DataFrame] = []
    for location in LOCATIONS:
        df_loc = fetch_location_satellite(location, START_DATE, END_DATE)
        if df_loc.empty:
            LOGGER.warning("No satellite data for location %s", location.location_id)
            continue
        location_frames.append(df_loc)
        LOGGER.info(
            "Location %s complete: %s rows",
            location.location_id,
            len(df_loc),
        )

    if not location_frames:
        raise RuntimeError("No satellite records were fetched for any location.")

    df_all = pd.concat(location_frames, ignore_index=True)
    df_all = df_all.sort_values(["location_id", "date"]).reset_index(drop=True)
    df_all.to_csv(OUTPUT_FILE, index=False)

    LOGGER.info("Saved satellite panel: %s", OUTPUT_FILE)
    LOGGER.info(
        "Output rows=%s | locations=%s | ndvi_valid=%s | lst_valid=%s",
        len(df_all),
        df_all["location_id"].nunique(),
        df_all["ndvi"].notna().sum(),
        df_all["lst"].notna().sum(),
    )

    return df_all


if __name__ == "__main__":
    main()
