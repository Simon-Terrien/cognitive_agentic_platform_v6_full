#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-all}"
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=15001
TRAINING_PORT=15000
FRONTEND_PORT=15002

ensure_backend_env() {
  cd "$ROOT/backend"
  if [ ! -x ".venv/bin/uvicorn" ]; then
    echo "[backend] bootstrapping .venv"
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
  fi
}

free_port() {
  local port=$1
  local pid
  pid=$(lsof -ti tcp:"$port" 2>/dev/null || true)
  if [ -n "$pid" ]; then
    echo "[ports] freeing :$port (pid $pid)"
    kill "$pid" 2>/dev/null || true
    # wait until the port is actually released (max 3s)
    for _ in $(seq 1 6); do
      sleep 0.5
      lsof -ti tcp:"$port" &>/dev/null || return 0
    done
  fi
}

wait_for() {
  local label=$1 url=$2 retries=20
  echo "[health] waiting for $label..."
  for _ in $(seq 1 $retries); do
    curl -sf "$url" >/dev/null 2>&1 && echo "[health] $label is up" && return 0
    sleep 0.5
  done
  echo "[health] $label did not respond after ${retries} attempts"
  return 1
}

start_training() {
  free_port "$TRAINING_PORT"
  echo "[training] starting on :$TRAINING_PORT"
  cd "$ROOT/backend"
  ensure_backend_env
  .venv/bin/uvicorn training_service:app --reload --port "$TRAINING_PORT"
}

start_backend() {
  free_port "$BACKEND_PORT"
  echo "[backend] starting on :$BACKEND_PORT"
  cd "$ROOT/backend"
  ensure_backend_env
  APP_TRAINING_SERVICE_URL="http://localhost:$TRAINING_PORT" \
    .venv/bin/uvicorn app.main:app --reload --port "$BACKEND_PORT"
}

start_frontend() {
  free_port "$FRONTEND_PORT"
  echo "[frontend] starting on :$FRONTEND_PORT"
  cd "$ROOT/frontend"
  if [ ! -d "node_modules" ]; then
    echo "[frontend] installing dependencies..."
    npm install
  fi
  wait_for "training :$TRAINING_PORT" "http://localhost:$TRAINING_PORT/api/health"
  wait_for "backend  :$BACKEND_PORT" "http://localhost:$BACKEND_PORT/api/health"
  VITE_API_BASE="http://localhost:$BACKEND_PORT" npm run dev
}

case "$MODE" in
  training)
    start_training
    ;;
  backend)
    start_backend
    ;;
  frontend)
    start_frontend
    ;;
  docker)
    echo "[docker] running docker-compose up (training → backend → frontend)"
    cd "$ROOT"
    docker compose up --build
    ;;
  all)
    trap 'echo; echo "stopping..."; kill 0' INT TERM
    start_training &
    start_backend &
    start_frontend &
    wait
    ;;
  *)
    echo "Usage: $0 [backend|frontend|docker|all|training]"
    exit 1
    ;;
esac
