# ============================================================
# SaltySeq — Script 1: REAL Satellite Data (Google Earth Engine)
# ============================================================
# Mục đích: Trích xuất NDVI và LST cho tọa độ Bến Tre, ĐBSCL.
#
# Chiến lược multi-source NDVI (giải quyết vấn đề mây mùa mưa):
#   ┌─────────────────┬────────┬───────────┬─────────────────────┐
#   │ Nguồn           │ Res.   │ Revisit   │ Đặc điểm            │
#   ├─────────────────┼────────┼───────────┼─────────────────────┤
#   │ Sentinel-2 SR   │ 10m    │ 5 ngày    │ Độ chính xác cao    │
#   │ Landsat 8/9 C2  │ 30m    │ ~8 ngày   │ Tăng mật độ thời gian│
#   │ MODIS MOD13Q1   │ 250m   │ 16-day    │ Max-value composite │
#   │       MYD13Q1   │        │ (offset)  │ → xuyên mây tốt nhất│
#   └─────────────────┴────────┴───────────┴─────────────────────┘
#   Ưu tiên khi cùng ngày: Sentinel-2 > Landsat > MODIS Terra > Aqua
#
# LST: Landsat 8/9 C2 L2 (thermal band ST_B10)
# Output: data/real_ndvi_lst.csv
# ============================================================

import ee
import pandas as pd
import numpy as np
from pathlib import Path

# ── CẤU HÌNH ───────────────────────────────────────────────
TARGET_LAT = 10.24
TARGET_LON = 106.37
BUFFER_M = 500          # Buffer 500m quanh điểm (trung bình spatial)
START_DATE = "2023-01-01"
END_DATE = "2025-12-31"

OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "real_ndvi_lst.csv"


# ── AUTHENTICATION ──────────────────────────────────────────
def init_gee():
    """Xác thực và khởi tạo Google Earth Engine."""
    ee.Authenticate()
    ee.Initialize(project='cs313project-489508')
    print("[✓] GEE đã khởi tạo thành công (project: cs313project-489508)")


# ── SENTINEL-2: NDVI ────────────────────────────────────────
def mask_s2_clouds(image):
    """
    Cloud masking cho Sentinel-2 SR Harmonized.
    Sử dụng QA60 band:
      - Bit 10: Opaque clouds
      - Bit 11: Cirrus clouds
    Cả 2 bit phải = 0 (không mây) để pixel được giữ lại.
    Thêm filter CLOUDY_PIXEL_PERCENTAGE < 50% ở collection level.
    """
    qa = image.select('QA60')
    cloud_mask = (
        qa.bitwiseAnd(1 << 10).eq(0)
        .And(qa.bitwiseAnd(1 << 11).eq(0))
    )
    return (image.updateMask(cloud_mask).divide(10000)
            .set('system:time_start', image.get('system:time_start')))


def compute_ndvi(image):
    """
    NDVI = (NIR - RED) / (NIR + RED)
    Sentinel-2: B8 (NIR, 842nm), B4 (RED, 665nm)
    Giá trị hợp lệ: [-1, 1], vùng nông nghiệp thường [0.2, 0.8]
    """
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return image.addBands(ndvi).copyProperties(image, ['system:time_start'])


def fetch_ndvi(roi):
    """Lấy chuỗi thời gian NDVI từ Sentinel-2 SR Harmonized."""
    print("\n[i] Đang truy vấn Sentinel-2 NDVI...")

    collection = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(roi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
        .filter(ee.Filter.gt('system:time_start', 0))
        .map(mask_s2_clouds)
        .map(compute_ndvi)
        .select(['NDVI'])
    )

    n_images = collection.size().getInfo()
    print(f"    Tìm thấy {n_images} ảnh Sentinel-2 sau cloud filter.")

    def extract_ndvi(image):
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=10,
            maxPixels=1e9
        )
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'ndvi': stats.get('NDVI')
        })

    features = collection.map(extract_ndvi).getInfo()['features']

    records = []
    for f in features:
        p = f['properties']
        if p.get('ndvi') is not None:
            records.append({'date': p['date'], 'ndvi': p['ndvi'], 'ndvi_source': 'sentinel2'})

    df = pd.DataFrame(records)
    if len(df) == 0:
        return df
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates(subset='date').reset_index(drop=True)

    print(f"[✓] Sentinel-2 NDVI: {len(df)} quan sát hợp lệ")
    print(f"    Range: {df['date'].min().date()} → {df['date'].max().date()}")
    print(f"    NDVI: {df['ndvi'].mean():.4f} ± {df['ndvi'].std():.4f}")
    return df


# ── LANDSAT 8/9: NDVI ──────────────────────────────────────
def fetch_ndvi_landsat(roi):
    """
    NDVI từ Landsat 8/9 Collection 2 Level 2.
    Landsat: SR_B4 = Red (0.64–0.67µm), SR_B5 = NIR (0.85–0.88µm)
    Scale factor C2: DN * 0.0000275 + (−0.2)
    Cloud mask: QA_PIXEL bit 3 (cloud) + bit 4 (shadow)
    """
    print("\n[i] Đang truy vấn Landsat 8/9 NDVI...")

    def compute_ndvi_ls(image):
        red = image.select('SR_B4').multiply(0.0000275).add(-0.2)
        nir = image.select('SR_B5').multiply(0.0000275).add(-0.2)
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        qa = image.select('QA_PIXEL')
        cloud_mask = (
            qa.bitwiseAnd(1 << 3).eq(0)
            .And(qa.bitwiseAnd(1 << 4).eq(0))
        )
        return (image.addBands(ndvi).updateMask(cloud_mask)
                .copyProperties(image, ['system:time_start']))

    l8 = (
        ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        .filterBounds(roi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt('CLOUD_COVER', 70))
        .filter(ee.Filter.gt('system:time_start', 0))
        .map(compute_ndvi_ls)
        .select(['NDVI'])
    )
    l9 = (
        ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        .filterBounds(roi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt('CLOUD_COVER', 70))
        .filter(ee.Filter.gt('system:time_start', 0))
        .map(compute_ndvi_ls)
        .select(['NDVI'])
    )
    collection = l8.merge(l9).sort('system:time_start')
    n = collection.size().getInfo()
    print(f"    Tìm thấy {n} ảnh Landsat 8/9")

    def extract_ls(image):
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=30,
            maxPixels=1e9
        )
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'ndvi': stats.get('NDVI')
        })

    features = collection.map(extract_ls).getInfo()['features']
    records = []
    for f in features:
        p = f['properties']
        val = p.get('ndvi')
        if val is not None and -0.2 <= val <= 1.0:
            records.append({'date': p['date'], 'ndvi': val, 'ndvi_source': 'landsat'})

    df = pd.DataFrame(records)
    if len(df) == 0:
        print("    Không có ảnh Landsat NDVI hợp lệ.")
        return df
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates(subset='date').reset_index(drop=True)
    print(f"[✓] Landsat 8/9 NDVI: {len(df)} quan sát hợp lệ")
    print(f"    NDVI: {df['ndvi'].mean():.4f} ± {df['ndvi'].std():.4f}")
    return df


# ── MODIS: NDVI (16-day max-value composite) ───────────────
def fetch_ndvi_modis(roi):
    """
    NDVI từ MODIS MOD13Q1 (Terra) + MYD13Q1 (Aqua) — 16-day composite.

    Tại sao MODIS hiệu quả ở vùng nhiệt đới nhiều mây?
    • Max-value composite: trong 16 ngày, GEE chọn pixel có NDVI cao nhất
      (≈ pixel ít mây nhất) thay vì chụp tại 1 thời điểm cố định.
    • Terra (đi qua ~10:30 sáng) + Aqua (đi qua ~13:30) offset nhau 8 ngày
      → effective temporal resolution = 8 ngày.
    NDVI band scale: × 0.0001, valid range [−2000, 10000] → [−0.2, 1.0]
    """
    print("\n[i] Đang truy vấn MODIS NDVI (MOD13Q1 Terra + MYD13Q1 Aqua)...")

    def extract_modis(image):
        stats = image.select('NDVI').reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=250,
            maxPixels=1e9
        )
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'ndvi': stats.get('NDVI')
        })

    records = []
    for product, src_label in [
        ('MODIS/061/MOD13Q1', 'modis_terra'),
        ('MODIS/061/MYD13Q1', 'modis_aqua'),
    ]:
        col = (
            ee.ImageCollection(product)
            .filterBounds(roi)
            .filterDate(START_DATE, END_DATE)
            .select(['NDVI'])
        )
        n = col.size().getInfo()
        print(f"    {src_label}: {n} composites")
        feats = col.map(extract_modis).getInfo()['features']
        for f in feats:
            p = f['properties']
            val = p.get('ndvi')
            if val is not None:
                val_scaled = val * 0.0001
                if -0.2 <= val_scaled <= 1.0:
                    records.append({
                        'date': p['date'],
                        'ndvi': round(val_scaled, 6),
                        'ndvi_source': src_label
                    })

    df = pd.DataFrame(records)
    if len(df) == 0:
        print("    Không có MODIS NDVI hợp lệ.")
        return df
    df['date'] = pd.to_datetime(df['date'])
    df = (df.sort_values('date')
            .drop_duplicates(subset='date', keep='first')
            .reset_index(drop=True))
    print(f"[✓] MODIS NDVI: {len(df)} composites hợp lệ")
    print(f"    NDVI: {df['ndvi'].mean():.4f} ± {df['ndvi'].std():.4f}")
    return df


# ── LANDSAT 8/9: LST (Land Surface Temperature) ────────────
def compute_lst_landsat(image):
    """
    Tính Land Surface Temperature (LST) từ Landsat 8/9 Collection 2 Level 2.

    Landsat C2 L2 đã có sẵn Surface Temperature (ST_B10) trong đơn vị
    scale factor = 0.00341802, offset = 149.0 (Kelvin).
    Công thức: LST_Kelvin = ST_B10 * 0.00341802 + 149.0
    Chuyển sang Celsius: LST_C = LST_Kelvin - 273.15

    Cloud masking dùng QA_PIXEL band (CFMask algorithm).
    """
    # Cloud mask: QA_PIXEL bit 3 (cloud) và bit 4 (cloud shadow) = 0
    qa = image.select('QA_PIXEL')
    cloud_mask = (
        qa.bitwiseAnd(1 << 3).eq(0)
        .And(qa.bitwiseAnd(1 << 4).eq(0))
    )

    # Tính LST (Celsius) từ ST_B10
    lst = (
        image.select('ST_B10')
        .multiply(0.00341802)
        .add(149.0)
        .subtract(273.15)
        .rename('LST')
    )

    return image.addBands(lst).updateMask(cloud_mask) \
                .copyProperties(image, ['system:time_start'])


def fetch_lst(roi):
    """
    Lấy chuỗi thời gian LST từ Landsat 8 + 9 Collection 2 Level 2.
    Kết hợp cả 2 satellite để tăng temporal density (16 ngày → ~8 ngày).
    """
    print("\n[i] Đang truy vấn Landsat 8/9 LST...")

    # Landsat 8 Collection 2 Level 2
    l8 = (
        ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
        .filterBounds(roi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt('CLOUD_COVER', 50))
        .filter(ee.Filter.gt('system:time_start', 0))
        .map(compute_lst_landsat)
        .select(['LST'])
    )

    # Landsat 9 Collection 2 Level 2
    l9 = (
        ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        .filterBounds(roi)
        .filterDate(START_DATE, END_DATE)
        .filter(ee.Filter.lt('CLOUD_COVER', 50))
        .filter(ee.Filter.gt('system:time_start', 0))
        .map(compute_lst_landsat)
        .select(['LST'])
    )

    # Merge 2 collections
    collection = l8.merge(l9).sort('system:time_start')
    n_images = collection.size().getInfo()
    print(f"    Tìm thấy {n_images} ảnh Landsat 8/9 sau cloud filter.")

    def extract_lst(image):
        stats = image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=roi,
            scale=30,
            maxPixels=1e9
        )
        return ee.Feature(None, {
            'date': image.date().format('YYYY-MM-dd'),
            'lst': stats.get('LST')
        })

    features = collection.map(extract_lst).getInfo()['features']

    records = []
    for f in features:
        p = f['properties']
        if p.get('lst') is not None:
            records.append({'date': p['date'], 'lst': p['lst']})

    df = pd.DataFrame(records)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').drop_duplicates(subset='date').reset_index(drop=True)

    print(f"[✓] LST: {len(df)} quan sát hợp lệ")
    if len(df) > 0:
        print(f"    Range: {df['date'].min().date()} → {df['date'].max().date()}")
        print(f"    LST: {df['lst'].mean():.2f}°C ± {df['lst'].std():.2f}°C")
    return df


# ── MAIN ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  Script 1: REAL Satellite Data (GEE) — Multi-source NDVI")
    print(f"  Tọa độ: ({TARGET_LAT}, {TARGET_LON}) — Bến Tre, VN")
    print(f"  Thời gian: {START_DATE} → {END_DATE}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)
    init_gee()

    # Tạo ROI
    point = ee.Geometry.Point([TARGET_LON, TARGET_LAT])
    roi = point.buffer(BUFFER_M)

    # ── NDVI: 3 nguồn ─────────────────────────────────────────
    df_s2   = fetch_ndvi(roi)           # Sentinel-2 (10m, ~5 ngày)
    df_ls   = fetch_ndvi_landsat(roi)   # Landsat 8/9 (30m, ~8 ngày)
    df_mod  = fetch_ndvi_modis(roi)     # MODIS composite (250m, 8-16 ngày)

    # Gộp theo thứ tự ưu tiên: S2 > Landsat > MODIS Terra > Aqua
    # Khi cùng ngày → giữ nguồn ưu tiên cao hơn
    priority_map = {'sentinel2': 0, 'landsat': 1, 'modis_terra': 2, 'modis_aqua': 3}
    parts = [df for df in [df_s2, df_ls, df_mod] if len(df) > 0]
    df_ndvi = pd.concat(parts, ignore_index=True)
    df_ndvi['date'] = pd.to_datetime(df_ndvi['date'])
    df_ndvi['_priority'] = df_ndvi['ndvi_source'].map(priority_map)
    df_ndvi = (
        df_ndvi.sort_values(['date', '_priority'])
               .drop_duplicates(subset='date', keep='first')
               .drop(columns='_priority')
               .sort_values('date')
               .reset_index(drop=True)
    )

    print(f"\n[i] NDVI tổng hợp 3 nguồn: {len(df_ndvi)} quan sát")
    for src, cnt in df_ndvi['ndvi_source'].value_counts().items():
        bar = '█' * int(cnt / len(df_ndvi) * 30)
        print(f"    {src:<15}: {cnt:>3}  {bar}")

    # ── LST: Landsat 8/9 ──────────────────────────────────────
    df_lst = fetch_lst(roi)

    # ── Merge NDVI + LST (outer join — giữ tất cả observ.) ───
    df_merged = (
        pd.merge(
            df_ndvi[['date', 'ndvi', 'ndvi_source']],
            df_lst,
            on='date', how='outer'
        )
        .sort_values('date')
        .reset_index(drop=True)
    )

    # Điền ndvi_source cho rows chỉ có LST
    df_merged['ndvi_source'] = df_merged['ndvi_source'].fillna('none')

    print(f"\n[i] Merged satellite dataset:")
    print(f"    Total rows:  {len(df_merged)}")
    print(f"    NDVI valid:  {df_merged['ndvi'].notna().sum()}")
    print(f"    LST valid:   {df_merged['lst'].notna().sum()}")
    print(f"    Both valid:  {df_merged.dropna(subset=['ndvi','lst']).shape[0]}")

    # Tháng nào có NDVI?
    df_merged['month'] = pd.to_datetime(df_merged['date']).dt.month
    ndvi_by_month = df_merged[df_merged['ndvi'].notna()].groupby('month').size()
    print("\n    NDVI coverage theo tháng:")
    for m in range(1, 13):
        cnt = ndvi_by_month.get(m, 0)
        bar = '▓' * cnt + '░' * max(0, 4 - cnt)
        print(f"    T{m:02d}: {bar} ({cnt})")
    df_merged = df_merged.drop(columns='month')

    # Lưu CSV
    df_merged.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[✓] Đã lưu: {OUTPUT_FILE}")
    print("\n--- Preview (15 dòng đầu) ---")
    print(df_merged.head(15).to_string())

    return df_merged


if __name__ == "__main__":
    main()
