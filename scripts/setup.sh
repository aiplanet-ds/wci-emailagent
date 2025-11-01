#!/bin/bash
# Setup script for WCI Email Agent with PostgreSQL

set -e

echo "============================================================"
echo "WCI Email Agent - PostgreSQL Setup"
echo "============================================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running!"
    echo "Please start Docker and try again."
    exit 1
fi

echo "[1/5] Starting PostgreSQL container..."
docker-compose up -d postgres

echo ""
echo "[2/5] Waiting for PostgreSQL to be ready (30 seconds)..."
sleep 30

echo ""
echo "[3/5] Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "[4/5] Initializing database schema..."
python scripts/init_db.py

echo ""
echo "[5/5] Setup complete!"
echo ""
echo "============================================================"
echo "Next Steps:"
echo "============================================================"
echo ""
echo "1. Migrate existing data (if you have JSON files):"
echo "   python scripts/migrate_json_to_db.py --dry-run"
echo "   python scripts/migrate_json_to_db.py"
echo ""
echo "2. Start the application:"
echo "   python start.py"
echo ""
echo "3. Or run everything in Docker:"
echo "   docker-compose up -d"
echo ""
echo "4. Access the application at:"
echo "   http://localhost:8000"
echo ""
echo "============================================================"
echo ""
