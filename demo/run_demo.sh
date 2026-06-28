#!/usr/bin/env bash
set -e

echo "=== IncidentLens demo ==="

echo "[1/3] Generating synthetic dataset…"
python demo/generate_dataset.py

echo "[2/3] Ingesting 500 incidents…"
curl -s -X POST http://localhost:8000/ingest \
     -F "file=@demo/incidents.csv" | python -m json.tool

echo "[3/3] Fetching top risk cluster…"
curl -s http://localhost:8000/clusters | python -m json.tool | head -60

echo "Done. Open http://localhost:8000 to view the dashboard."
