# V6 Architecture

## High level

Frontend
→ FastAPI API
→ Agent Engine
→ Planner
→ Model Router
→ Provider Manager
→ Platform Store + Auth
→ Provider
→ Result + SSE trace

## Platform layer

In addition to the agent core, the backend now wires:

- **Platform Store:** SQLite-backed `users` + `user_preferences` with `APP_PLATFORM_DB_PATH`
- **Auth:** Local JWT issued by `app.core.auth`, bootstrap operator seeded from env
- **Request ID + metrics middleware** feeding `/metrics` and Prometheus/Loki
- **Observability stack:** Prometheus scrapes `/metrics`, Grafana (3001) and Loki (3100) expose dashboards/logs

The user preference data (model ID, dataset ID, blocked tools) flows into the model router so each operator can keep a private runtime.

## Provider abstraction

The backend hides inference differences behind a common interface:

- `OpenAICompatibleProvider`
  - used for **vLLM** and **llama.cpp**
- `OllamaProvider`
- `TransformersLocalProvider`

This keeps the agent logic stable while you swap serving stacks.

## Training side

Training path:

Dataset Registry
→ Dataset Loader
→ Normalizer
→ Trainer
→ Unsloth Adapter
→ Training Plan / Export Targets
