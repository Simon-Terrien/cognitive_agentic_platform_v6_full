# Planning

## Objective

Turn [cognitive_agentic_platform_v6_full](/home/lupise/dev/cognitive_agentic_platform_v6_full) into the single unified product:

- V6 remains the product core
- live starter-pack contributes platform maturity
- archive-only starter-pack files are used only as idea sources

## Current State

Already in place:
- V6 backend, frontend, provider matrix, training service, dataset planning
- upgraded command-surface frontend
- dataset selection and model retrieval improvements
- compatibility chat aliases
- backend metrics endpoint
- request ID middleware
- local operator auth scaffold
- Docker observability sidecars for Prometheus, Loki, Grafana

Known gaps:
- real provider connectivity is still fragile in Docker
- auth is not yet persistent in the starter-pack sense
- no database/redis-backed multi-user platform layer yet
- engine pooling and user isolation are missing
- frontend still lacks deeper test coverage
- backend HTTP test harness is unreliable in this shell and needs stabilization

## Architecture Direction

### Keep from V6

- current API shape
- provider abstraction
- model catalog and router
- training workflows
- R&D dashboard and demo story
- Docker launch model

### Port from live starter-pack

- auth backend design
- persistent user model
- usage tracking and run logs
- engine pool
- rate limiting
- admin endpoints and admin views
- richer docs and smoke coverage

### Mine from archive-only starter-pack ideas

- dynamic agent registry
- governance loop
- security-agent framing
- RLM decomposition concepts

Rule:
- adapt to V6 interfaces first
- never bulk-copy archive modules into production paths

## Workstreams

### Workstream A: Platform Reliability

Targets:
- provider fallback behavior
- Docker networking fixes
- startup validation
- observability sanity checks

Exit criteria:
- one reliable real-provider path
- one reliable offline fallback path

### Workstream B: Identity And Persistence

Targets:
- durable user storage
- proper login/session lifecycle
- persisted user preferences
- usage/run logging

Exit criteria:
- platform survives restart without losing operator state

### Workstream C: Multi-User Runtime

Targets:
- engine pool
- per-user isolation
- idle eviction
- session-scoped runtime configuration

Exit criteria:
- user activity no longer shares one implicit global runtime state

### Workstream D: Observability And Admin

Targets:
- dashboard refinement
- admin views
- operational summaries
- log/metric correlation

Exit criteria:
- operator can diagnose issues without shelling into containers

### Workstream E: Advanced Agent Layer

Targets:
- registry pattern
- governance loop
- optional security workflows

Exit criteria:
- advanced agent features are integrated as explicit modules, not experiments

## Risks

### Risk 1: Blind merge from starter-pack

Impact:
- duplicated routes
- mismatched models
- broken deployment

Response:
- keep V6 as canonical base
- port feature-by-feature only

### Risk 2: Overbuilding auth too early

Impact:
- destabilizes demo-ready V6

Response:
- keep current scaffold until persistent auth is ready
- preserve existing public health/model telemetry where useful

### Risk 3: Provider instability damages confidence

Impact:
- demo failure even when the app itself is sound

Response:
- keep mock/transformers fallback
- surface provider-state messaging clearly

### Risk 4: Test harness confusion

Impact:
- false negatives and wasted debugging time

Response:
- stabilize one canonical backend smoke path
- separate transport-test issues from application issues

## Delivery Strategy

### Phase A

- stabilize runtime
- validate observability stack
- lock down one repeatable demo flow

### Phase B

- port persistent auth and usage logging
- add user preferences

### Phase C

- add engine pool and user isolation
- add admin surface

### Phase D

- evaluate archive-only advanced-agent ideas

## Success Criteria

The unified project is successful when:

- the product still feels like the current V6 R&D platform
- it gains platform-grade auth, persistence, and observability
- it can support more than one operator cleanly
- it has a credible demo path and a credible engineering path

## Recommended Immediate Sequence

1. Rebuild and validate the new observability stack.
2. Fix containerized real-provider connectivity.
3. Port persistent auth and user storage.
4. Port usage logging and engine pool.
5. Add admin views.
6. Revisit governance and advanced-agent concepts after the platform layer is stable.
