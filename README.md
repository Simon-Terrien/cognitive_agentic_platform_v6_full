# Cognitive Agentic Platform V6

A professional local-AI research platform with:

- **FastAPI backend**
- **React + TypeScript + Vite frontend**
- **Streaming SSE traces**
- **Request metrics + operator auth scaffold**
- **Unified provider layer**
  - `llama.cpp` (via OpenAI-compatible server)
  - `vLLM` (via OpenAI-compatible server)
  - `Ollama`
  - `Transformers` (local in-process)
- **Model catalog + router**
- **Idle training scheduler**
- **Hugging Face dataset normalization**
- **Unsloth training/export hooks**
- **Docker + tests**

## Why this version matters

This version is designed to be the first one you can **actually grow into a local AI lab**:

- run different inference backends without rewriting the agent
- switch models from the UI
- stream every reasoning step for debugging
- normalize TeichAI / HF datasets
- prepare a future LoRA / SFT / distillation workflow with **Unsloth**
- export or target deployment flows for **GGUF / Ollama / llama.cpp / vLLM**

## Quick start

### Recommended demo launch

```bash
cd /home/lupise/dev/cognitive_agentic_platform_v6_full
./start.sh all
```

That starts:

- training service on `http://localhost:15000`
- API backend on `http://localhost:15001`
- frontend on `http://localhost:15002`

### Manual split launch

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
APP_TRAINING_SERVICE_URL=http://localhost:15000 .venv/bin/uvicorn training_service:app --reload --port 15000
```

In another shell:

```bash
cd backend
source .venv/bin/activate
APP_TRAINING_SERVICE_URL=http://localhost:15000 .venv/bin/uvicorn app.main:app --reload --port 15001
```

In another shell:

```bash
cd frontend
npm install
VITE_API_BASE=http://localhost:15001 npm run dev
```

Open `http://localhost:15002`.

### Fast verification

```bash
./party_check.sh
make demo-check
make verify
```

## Platform Layer

V6 now includes the first unified platform layer taken from the starter-pack direction:

- request IDs on backend responses
- Prometheus-style metrics at `GET /metrics`
- local operator auth endpoints:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`
- optional auth enforcement for chat and training-control routes

Default local bootstrap operator:

- email: `operator@local`
- password: `operator-demo-pass`

Relevant environment variables:

- `APP_AUTH_REQUIRED=true`
- `APP_AUTH_SECRET=...`
- `APP_AUTH_BOOTSTRAP_EMAIL=...`
- `APP_AUTH_BOOTSTRAP_PASSWORD=...`
- `APP_AUTH_STORE_DIR=/tmp/cognitive_agentic_platform_v6_auth`

The auth store defaults to `/tmp` so the platform remains runnable in constrained local and containerized environments.

### User Preferences

Authenticated operators can call:

- `GET /api/users/me`
- `GET /api/users/me/preferences`
- `PATCH /api/users/me/preferences`

Preferences flow into the engine router and are stored in SQLite at `APP_PLATFORM_DB_PATH`. These endpoints are guarded by `APP_AUTH_REQUIRED`.

## Observability Stack

V6 now also carries a real sidecar observability stack:

- Prometheus on `http://localhost:9090`
- Loki on `http://localhost:3100`
- Grafana on `http://localhost:3001`

The backend ships logs to Loki when `APP_LOKI_ENABLED=true`, and Prometheus scrapes the backend `GET /metrics` endpoint.

Important compose environment variables:

- `APP_LOKI_ENABLED=true`
- `APP_LOKI_URL=http://loki:3100`
- `APP_ENVIRONMENT=development`
- `GRAFANA_ADMIN_PASSWORD=admin`

After rebuilding with Docker Compose, Grafana provisions:

- `Prometheus` datasource
- `Loki` datasource
- `Cognitive Agentic Platform Overview` dashboard

### Smoke check

Run `scripts/smoke_check.sh` after starting the stack to confirm backend, training proxy, metrics, and provider paths respond.

## Preset `.env` profiles

The backend now supports loading a preset env file before settings are built:

```bash
cd /home/lupise/dev/cognitive_agentic_platform_v6_full/backend
source .venv/bin/activate
APP_ENV_FILE=.env.mock .venv/bin/uvicorn app.main:app --reload --port 15001
```

Available tracked presets from the repo root:

- `.env.mock`
- `.env.mock.minimal`
- `.env.qwen.ollama`
- `.env.qwen.vllm`
- `.env.qwen.transformers`
- `.env.lfm2.700m`
- `.env.lfm2.1.2b`
- `.env.lfm2.vllm`
- `.env.bench.speed`
- `.env.bench.quality`
- `.env.bench.comparison`

Use `.env.example` as the editable starting point for a local custom setup.

## Benchmark runner

Run preset comparisons from the repo root:

```bash
backend/.venv/bin/python scripts/run_benchmark.py --env-file .env.mock --env-file .env.qwen.ollama --suite default
backend/.venv/bin/python scripts/run_benchmark.py --env-file .env.bench.speed --suite speed --iterations 3
backend/.venv/bin/python scripts/run_benchmark.py --env-file .env.qwen.vllm --env-file .env.lfm2.vllm --suite benchmark --json
```

## Supported local backends

### 1) Ollama
Default local URL: `http://localhost:11434`

### 2) llama.cpp
OpenAI-compatible server URL, for example: `http://localhost:8001/v1`

### 3) vLLM
OpenAI-compatible server URL, for example: `http://localhost:8002/v1`

### 4) Transformers
Runs in-process inside the backend for small/local experiments.

## Training / Unsloth

The project contains:

- dataset normalization
- a training registry
- a trainer service
- an `UnslothAdapter` that prepares:
  - training plan
  - normalized JSONL
  - deployment targets (GGUF / Ollama / llama.cpp / vLLM)

The adapter is intentionally conservative:
if Unsloth is not installed, it returns a **real training plan** instead of pretending to train.
