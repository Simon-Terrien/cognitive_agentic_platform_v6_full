#!/usr/bin/env bash
set -euo pipefail

BASE=${BASE_URL:-http://localhost:15001}

echo "Checking backend health..."
curl -fsSL "${BASE}/api/health"

echo "Checking model catalog..."
curl -fsSL "${BASE}/api/models" | head -n 5

echo "Checking provider status..."
curl -fsSL "${BASE}/api/providers/status"

echo "Checking training status..."
curl -fsSL "${BASE}/api/training/status"

echo "Checking metrics..."
curl -fsSL "${BASE}/metrics" | head -n 5

echo "Smoke check completed."
