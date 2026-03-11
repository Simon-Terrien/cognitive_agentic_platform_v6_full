# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Backend (FastAPI + Uvicorn)
make backend                        # Run dev server on :8000 with --reload
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (React + Vite)
make frontend                       # Run dev server on :5173
cd frontend && npm install && npm run dev

# Tests
make test                           # Runs: cd backend && pytest -q
cd backend && pytest -q             # Single quiet run
cd backend && pytest tests/test_health.py  # Single test file

# Build
cd frontend && npm run build        # Production bundle

# Docker
docker-compose up                   # Backend :8000, Frontend :5173
```

## Architecture

**Flow**: `Frontend → FastAPI API → AgentEngine → Planner → ModelRouter → ProviderManager → Provider → SSE trace`

### Backend (`backend/app/`)

**Provider Layer** (`providers/`) — the core abstraction. All inference backends implement the same `Provider` base (`base.py`): `health()`, `generate()`, `stream()`. The three concrete providers are:
- `OllamaProvider` — native Ollama `/api/chat` etc.
- `OpenAICompatibleProvider` — for vLLM and llama.cpp
- `TransformersLocalProvider` — in-process HuggingFace pipeline

`ProviderManager` (`providers/manager.py`) is a singleton managing provider lifecycle and health status.

**Model System** (`models/`) — `ModelSpec` dataclass defines each model (id, label, provider, family, transport). Pre-configured models include ollama_qwen3, vllm_qwen3_8b, llamacpp_local_gguf, transformers_tiny_gpt2. `ModelRouter` selects based on config or per-request override.

**Agent Engine** (`agent/engine.py`) — orchestrates `Planner` (keyword-based intent → steps), `ToolRouter`, and `ModelRouter`. Emits structured SSE trace events: `plan`, `model`, `step`, `token`, `final`. Two modes: `run()` (sync) and `run_stream()` (async generator).

**Training Pipeline** (`training/`) — dataset normalization to JSONL, Unsloth plan generation (returns real plans, never fakes training without GPU), export targets: GGUF/Ollama/llama.cpp/vLLM.

**API Routes** (`api/routes/`):
- `GET /api/health`
- `GET /api/models`
- `GET /api/providers/status`
- `POST /api/chat` (sync)
- `POST /api/chat/stream` (SSE)
- `POST /api/training/` (start/stop/plan)

**Config** (`core/config.py`) — singleton `Settings` class backed by environment variables. CORS origins are configurable.

### Frontend (`frontend/src/`)

Single-page React + TypeScript app. `App.tsx` contains the full UI: model selector, chat interface, streaming SSE trace display, provider health badges, and training control panel. `api.ts` is the typed API client mapping to all backend endpoints. No UI framework — plain CSS.

## Key Design Decisions

- **Streaming-first**: SSE traces expose every reasoning step; use `EventSource` on the frontend, `StreamingResponse` on the backend.
- **Conservative training**: `UnslothAdapter` generates real plans and export hints but will not pretend to train without a GPU.
- **Provider swap**: Changing the inference backend requires only a config/env change — the agent logic is provider-agnostic.
- **ML deps are optional**: `requirements-ml.txt` is separate from `requirements.txt`; import-guarded in `transformers_local.py`.
