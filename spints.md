# Spints

## Sprint 1: Runtime Hardening

Goal:
- make the current V6 stack reliable enough for demos and daily operator use

Scope:
- fix Ollama container-to-host reachability
- add provider fallback behavior when the selected runtime is offline
- make frontend degraded states clearer and actionable
- verify `/api/chat`, `/api/chat/stream`, `/api/training/status`, `/api/training/plan`, `/metrics`
- rebuild and validate Docker stack with Prometheus, Loki, and Grafana enabled

Definition of done:
- `docker compose up -d --build` works for backend, frontend, training, prometheus, loki, grafana
- Grafana dashboard loads and shows backend traffic
- chat works with at least one real provider and one fallback provider
- no demo-critical endpoint returns unexpected `500`

## Sprint 2: Real Auth And Persistence

Goal:
- replace the current local auth scaffold with starter-pack-grade persistence

Scope:
- port user model and preferences
- port token/session handling
- add rate limiting
- persist users, runs, tool usage, and token usage
- keep V6 route contracts stable while introducing authenticated operator flows

Definition of done:
- authenticated login flow works
- bearer auth protects selected routes when enabled
- user preferences persist across restarts
- run and usage records are stored durably

## Sprint 3: Engine Pool And User Isolation

Goal:
- move from single-operator runtime behavior to session-aware platform behavior

Scope:
- port engine pool pattern
- add per-user engine isolation
- add idle eviction
- add per-user selected model and runtime preferences
- preserve V6 model router as the source of truth

Definition of done:
- multiple users can run the platform without sharing one mutable engine instance
- stale engines are evicted cleanly
- preferences affect model routing without code edits

## Sprint 4: Admin And Usage Surface

Goal:
- make the platform operationally legible for internal admins and investors

Scope:
- add admin usage endpoints
- add basic admin UI views
- show runs, provider failures, auth failures, and training activity
- wire logs and metrics into the UI story where useful

Definition of done:
- admin can inspect usage and health from the app
- platform can explain who ran what and what failed

## Sprint 5: Test And Release Discipline

Goal:
- stop relying on ad hoc manual verification

Scope:
- stabilize backend test harness
- add endpoint smoke coverage for auth, chat, training, and metrics
- add frontend verification beyond typecheck/build
- add one pre-demo verification command

Definition of done:
- reproducible smoke suite passes locally and in Docker
- operator can run one command before demos and trust the output

## Sprint 6: Governance And Advanced Agents

Goal:
- selectively bring in the best higher-level ideas from the starter-pack archive

Scope:
- evaluate `agent_registry.py`
- evaluate `governance.py`
- evaluate `security_agent.py`
- evaluate `rlm.py`
- only integrate what fits the current V6 product narrative

Definition of done:
- each imported concept has a clear owner, interface, and test coverage
- no archive-only module is copied in blindly

## Priority Order

1. Sprint 1
2. Sprint 2
3. Sprint 3
4. Sprint 5
5. Sprint 4
6. Sprint 6

## Immediate Next Actions

1. Rebuild the full Docker stack with observability enabled.
2. Fix real-provider connectivity for Ollama from the backend container.
3. Replace the auth scaffold with persistent auth and user storage.
4. Port engine pool and preferences before broadening the UI surface.
