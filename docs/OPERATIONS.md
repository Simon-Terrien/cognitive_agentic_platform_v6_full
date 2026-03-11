# Operations

## Startup sequence

1. `./party_check.sh` (runs backend typecheck + readiness basics).
2. `docker compose up -d --build training backend prometheus loki grafana frontend`.
3. Wait for `backend` and `training` healthchecks, then hit:
   - `http://localhost:15001/api/health`
   - `http://localhost:15001/api/models`
   - `http://localhost:15001/api/providers/status`
   - `http://localhost:15001/api/training/status`
4. Visit Grafana `http://localhost:3001`, Prometheus `http://localhost:9090`, Loki `http://localhost:3100`.

## Demo checklist

- Real provider available (Ollama/vLLM/llama.cpp). Check `docker compose logs backend` for `[Errno 111] Connection refused`.
- If providers are offline, the UI will display `Mock / Deterministic` fallback. Confirm `/api/providers/status` shows `mock` healthy.
- When auth is enabled (`APP_AUTH_REQUIRED=true`), register/login via `POST /api/auth/login` and include `Authorization: Bearer ...`.
- Use `GET /api/users/me/preferences` to ensure preference persistence before demos.
- Validate `/metrics` via Grafana/Prometheus to ensure observability stack is scraping.
- Validate agent counters exist in `/metrics`:
  - `cap_agent_governor_events_total`
  - `cap_agent_tool_policy_total`
  - `cap_agent_memory_hits_total`

## Common failure modes

- **Ollama unreachable**: Backend logs `Connection refused`. Start Ollama with `OLLAMA_HOST=0.0.0.0:11434 ollama serve` or use the UI provider dropdown to switch to `Mock / Deterministic`.
- **auth scaffold missing user**: Check `/tmp/cognitive_agentic_platform_v6_auth` for `users.json` entries or `APP_PLATFORM_DB_PATH` for SQLite records.
- **Prometheus scrape error**: Confirm `APP_LOKI_ENABLED=true` and backend `GET /metrics` returns counters.
- **Training plan fails**: The dataset loader caches in `/tmp/cognitive_agentic_training`. Ensure Hugging Face downloads via cached dataset or `~/.cache/huggingface`.
- **Aggressive policy blocking**: If traces show `tool=blocked::...`, review `APP_AGENT_BLOCK_PATTERNS` and `APP_AGENT_TOOL_ALLOWLIST`.
- **Unexpected early stop**: Check traces for `kind=governor` and tune `APP_AGENT_MAX_*` budgets.

## Verification commands

1. `docker compose config` (ensures new observability services referenced correctly).
2. `curl -fsSX GET http://localhost:15001/api/auth/login -d '{"email":"operator@local","password":"operator-demo-pass"}'` to confirm auth works.
3. `curl -fs http://localhost:15001/metrics | head` to verify metrics exposures.
