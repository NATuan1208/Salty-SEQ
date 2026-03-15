#!/usr/bin/env python3
# ============================================================
# SaltySeq — Main Pipeline Orchestrator
# Capstone: Data Mining & Anomaly Detection — Mekong Delta
# ============================================================
#
# Chạy toàn bộ pipeline theo đúng thứ tự:
#
#   Script 1 → data/real_ndvi_lst.csv     (GEE: NDVI + LST)
#   Script 2 → data/real_weather.csv      (Open-Meteo: thời tiết + đất)
#   Script 3 → data/real_salinity.csv     (proxy độ mặn)
#   Script 4 → data/merged_final.csv      (merge + feature engineering)
#
# Cách chạy:
#   python run_pipeline.py                   # chạy cả 4 bước
#   python run_pipeline.py --skip-gee        # bỏ qua script1 (nếu GEE chưa auth)
#   python run_pipeline.py --from 2          # bắt đầu từ script2
#   python run_pipeline.py --only 4          # chỉ chạy script4
#
# Lưu ý GEE (Script 1):
#   Lần đầu chạy cần xác thực:  python -c "import ee; ee.Authenticate()"
#   Sau đó credentials được lưu tại ~/.config/earthengine/credentials
# ============================================================

import sys
import time
import argparse
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR  = BASE_DIR / "data"

# ── CÁC BƯỚC PIPELINE ──────────────────────────────────────
STEPS = [
    {
        "id": 1,
        "name": "Satellite Data (GEE — NDVI + LST)",
        "script": "src/satellite_gee.py",
        "output": DATA_DIR / "real_ndvi_lst.csv",
        "note": (
            "Yêu cầu xác thực GEE.\n"
            "  Nếu chưa auth, chạy:  python -c \"import ee; ee.Authenticate()\"\n"
            "  Project GEE:          cs313project-489508"
        ),
    },
    {
        "id": 2,
        "name": "Weather Data (Open-Meteo)",
        "script": "src/weather_openmeteo.py",
        "output": DATA_DIR / "real_weather.csv",
        "note": "Không cần API key — dùng ERA5-Land qua Open-Meteo Archive API.",
    },
    {
        "id": 3,
        "name": "Salinity Proxy",
        "script": "src/salinity.py",
        "output": DATA_DIR / "real_salinity.csv",
        "note": (
            "Method B (synthetic proxy) mặc định.\n"
            "  Để dùng Method A (Copernicus Marine), thêm cờ --salinity-cms\n"
            "  và cài:  python -m pip install copernicusmarine"
        ),
    },
    {
        "id": 4,
        "name": "Merge & Feature Engineering",
        "script": "src/merge_preprocess.py",
        "output": DATA_DIR / "merged_final.csv",
        "note": "Cần output của bước 1, 2, 3 tồn tại trước.",
    },
]


# ── HELPERS ────────────────────────────────────────────────
def _banner(text: str, char: str = "─", width: int = 62):
    print(f"\n{char * width}")
    print(f"  {text}")
    print(char * width)


def _check_preflight():
    """Kiểm tra môi trường trước khi chạy."""
    issues = []

    # earthengine-api
    try:
        import ee  # noqa: F401
    except ImportError:
        issues.append(
            "earthengine-api chưa cài —  python -m pip install earthengine-api"
        )

    # pandas, numpy, requests
    for pkg in ("pandas", "numpy", "requests"):
        try:
            __import__(pkg)
        except ImportError:
            issues.append(f"{pkg} chưa cài —  python -m pip install {pkg}")

    # output directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if issues:
        print("\n[Pre-flight] Phát hiện vấn đề môi trường:")
        for i in issues:
            print(f"  ✗ {i}")
        print()
        sys.exit(1)
    else:
        print("[Pre-flight] Môi trường OK  ✓")


def _run_step(step: dict, python_exe: str = sys.executable) -> bool:
    """Chạy một script, trả về True nếu thành công."""
    script_path = BASE_DIR / step["script"]
    if not script_path.exists():
        print(f"  [ERROR] Không tìm thấy: {step['script']}")
        return False

    start = time.time()
    result = subprocess.run(
        [python_exe, str(script_path)],
        capture_output=False,   # để output hiển thị trực tiếp
        cwd=str(BASE_DIR),
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"\n  [FAIL] {step['script']} thoát với mã lỗi {result.returncode}")
        print(f"  (Xem output phía trên để biết chi tiết)")
        return False

    out_file = step["output"]
    if not out_file.exists():
        print(f"\n  [WARN] Script chạy xong nhưng không thấy output: {out_file.name}")
        return False

    size_kb = out_file.stat().st_size / 1024
    print(f"\n  ✓ {out_file.name}  ({size_kb:.1f} KB)  [{elapsed:.1f}s]")
    return True


# ── MAIN ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="SaltySeq Pipeline Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--skip-gee", action="store_true",
        help="Bỏ qua Script 1 (GEE) — hữu ích khi real_ndvi_lst.csv đã có"
    )
    parser.add_argument(
        "--from", dest="from_step", type=int, default=1, metavar="N",
        help="Bắt đầu từ bước N (1–4)"
    )
    parser.add_argument(
        "--only", dest="only_step", type=int, default=None, metavar="N",
        help="Chỉ chạy bước N (1–4)"
    )
    args = parser.parse_args()

    _banner("SaltySeq Data Pipeline  —  Mekong Delta Anomaly Detection", "═")
    print(f"  Base dir   : {BASE_DIR}")
    print(f"  Data dir   : {DATA_DIR}")
    print(f"  Python     : {sys.executable}")

    _check_preflight()

    # Quyết định các bước cần chạy
    if args.only_step:
        steps_to_run = [s for s in STEPS if s["id"] == args.only_step]
    else:
        steps_to_run = [s for s in STEPS if s["id"] >= args.from_step]

    if args.skip_gee:
        steps_to_run = [s for s in steps_to_run if s["id"] != 1]
        if not (DATA_DIR / "real_ndvi_lst.csv").exists():
            print(
                "\n[WARN] --skip-gee được bật nhưng real_ndvi_lst.csv chưa tồn tại.\n"
                "       Script 4 sẽ báo lỗi thiếu file. Kiểm tra lại."
            )

    if not steps_to_run:
        print("\n[ERROR] Không có bước nào được chọn.")
        sys.exit(1)

    # Chạy từng bước
    failed_at = None
    for step in steps_to_run:
        _banner(f"Bước {step['id']} / 4 — {step['name']}")
        if step["note"]:
            for line in step["note"].splitlines():
                print(f"  ℹ  {line.strip()}")
        print()

        ok = _run_step(step)
        if not ok:
            failed_at = step["id"]
            print(
                f"\n[Pipeline] Dừng tại Bước {step['id']}.\n"
                f"  Sửa lỗi rồi chạy lại:  python run_pipeline.py --from {step['id']}"
            )
            sys.exit(1)

    # Tổng kết
    _banner("Pipeline hoàn thành  ✓", "═")
    print("\n  Các file output:")
    for f in sorted(OUTPUT_DIR.iterdir()):
        size_kb = f.stat().st_size / 1024
        print(f"    {f.name:<40}  {size_kb:>8.1f} KB")

    merged = OUTPUT_DIR / "merged_final.csv"
    if merged.exists():
        import pandas as pd  # lazy import — only needed for summary
        df = pd.read_csv(merged)
        print(f"\n  merged_final.csv:  {len(df)} rows × {len(df.columns)} features")
        print(f"  Columns: {', '.join(df.columns[:8])} ...")

    print("\n  Bước tiếp theo → Phase 2: Sequential Pattern Mining + XGBoost\n")


if __name__ == "__main__":
    main()
