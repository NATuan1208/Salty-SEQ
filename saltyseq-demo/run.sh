#!/bin/bash
set -e

# Check Python >= 3.10
PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    echo "❌ Python >= 3.10 required (found $PYTHON_VERSION)"
    exit 1
fi

# Check dependencies
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "❌ Dependencies not installed. Run: pip install -r requirements.txt"
    exit 1
fi

# Check model file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_FILE="$SCRIPT_DIR/backend/models/xgboost_model.json"

if [ ! -f "$MODEL_FILE" ]; then
    echo ""
    echo "⚠️  Model chưa được export. Chạy:"
    echo "   python setup_model.py --data_path <path_to_merged_final.csv>"
    echo "   Demo sẽ chạy ở MOCK MODE (predictions mô phỏng)"
    echo ""
fi

echo ""
echo "🌾 SaltySeq — Mekong Sentinel Demo"
echo "🌐 Đang chạy tại: http://localhost:8000"
echo "   Nhấn Ctrl+C để dừng."
echo ""

cd "$SCRIPT_DIR"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
