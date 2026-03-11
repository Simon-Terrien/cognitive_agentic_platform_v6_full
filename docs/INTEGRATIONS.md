# Integration notes

## llama.cpp
Expected mode: OpenAI-compatible server endpoint.

## vLLM
Expected mode: OpenAI-compatible server endpoint.

## Ollama
Expected mode: native `/api/chat`, `/api/tags`, `/api/version`.

## Transformers
Expected mode: small local models loaded in-process with `pipeline(...)`.

## Unsloth
This project includes:
- dataset normalization
- plan generation
- export target hints

It does not fake successful finetuning when the required GPU/runtime is unavailable.

## Auth + Platform Store

- Auth env controls: `APP_AUTH_REQUIRED`, `APP_AUTH_SECRET`, `APP_AUTH_BOOTSTRAP_EMAIL`, `APP_AUTH_BOOTSTRAP_PASSWORD`.
- Platform data stored in SQLite at `APP_PLATFORM_DB_PATH` (`/tmp/cognitive_agentic_platform_v6_platform/platform.db` by default).
- Bound endpoints: `/api/auth/*`, `/api/users/me`, `/api/users/me/preferences`.

## Observability

- Prometheus scrapes `GET /metrics`.
- Loki receives structured logs (`app.core.loki`).
- Grafana (provisioned dashboards) uses Prometheus + Loki datasources.
