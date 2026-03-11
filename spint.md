# Sprint: Agent Reliability Layer (Step 1)

## Goal
Implement production-safety foundations for the local agent system:
- recursion/cost limits
- persistent memory store
- hybrid retrieval scoring
- tool policy guardrails with audit logging

## Scope
- Backend only (`backend/app/*`)
- Non-breaking API evolution (existing chat endpoints still work)
- Unit tests for new behavior

## Tasks
- [x] Add settings for agent governors, memory persistence, and policy controls
- [x] Implement persistent memory store (SQLite) with append + retrieval APIs
- [x] Add hybrid retrieval scorer (semantic/keyword, recency, importance, conversation affinity)
- [x] Wire retrieval into engine note/context selection
- [x] Add recursion / iteration / token / tool-call governors in engine execution path
- [x] Add tool policy guardrails (allow/deny by tool id + query pattern checks)
- [x] Add audit events for tool decisions and governor stops
- [x] Surface governance metadata in traces/output payload
- [x] Add unit tests for: governors, retrieval ranking, policy deny, persistence round-trip
- [x] Run test suite and fix regressions (targeted suites run: `test_agent_reliability.py`, `test_model_router.py`)
- [ ] Commit with clear message
- [ ] Push to origin

## Acceptance Criteria
- Requests cannot exceed configured depth/iterations/tool calls/tokens
- Memory survives process restart (SQLite file-based store)
- Retrieval returns ranked prior notes with weighted score components
- Denied tool requests are blocked and logged in traces
- Tests pass locally

## Notes
- Keep defaults conservative and configurable via env vars
- Preserve existing chat response fields (`answer`, `model_id`, `traces`, etc.)
