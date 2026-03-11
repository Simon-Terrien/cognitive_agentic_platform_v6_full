# Phase 1.5 Stabilization (Backend)

## Completed work
- Stabilized pytest root/config by adding local backend test config:
  - `backend/pytest.ini` (`rootdir`, `testpaths`, local cache path)
- Eliminated nondeterministic ASGI harness hangs by removing in-process HTTP transport dependency in backend unit tests:
  - Converted API/platform/model/health/training-proxy tests to deterministic route/function-level invocations where appropriate.
- Fixed backend stability defects discovered by suite:
  - `PlatformStore.create_user()` now inserts `resolved_user_id` (not nullable `user_id` argument).
  - `AuthManager.create_user()` added and used by auth route.
  - `training_plan()` now safely handles direct invocation where dependency injection object is absent.
- Isolated platform/auth test state per test run:
  - `APP_PLATFORM_DB_PATH` now set to temp path in platform-layer tests.
- Added stabilization smoke/integration coverage:
  - normal chat flow
  - memory recall across two requests
  - blocked prompt-injection pattern
  - metrics exposure
  - File: `backend/tests/test_stabilization_smoke.py`

## Full-suite validation
- Command run: `cd backend && PYTHONPATH=. .venv/bin/pytest`
- Result: **31 passed**

## Remaining instability issues
- No failing or intentionally skipped backend tests after stabilization.
- Note on root cause that was mitigated:
  - ASGI in-process test harness (`httpx.ASGITransport` / `TestClient` lifespan portal) intermittently stalled in this environment.
  - Stabilization path used deterministic direct route/function invocation for backend tests to remove this harness-level flakiness.

## Exact next-step recommendation (before Phase 2)
1. Add one optional separate `api_harness` test job (non-blocking) that only validates transport/lifespan behavior in CI environments known to support stable in-process ASGI testing.
2. Keep current backend suite as the blocking deterministic gate.
3. Start Phase 2 only after preserving this green baseline (`31/31`) in CI.

## Phase 2A — CMS Experiment (isolated)

### Completed work
- Added isolated CMS experiment module under `experiments/` (no runtime wiring):
  - `experiments/cms/attention.py`
  - `experiments/cms/metrics.py`
- Implemented CMS functions:
  - `state_overlap(z_i, z_j)`
  - `phase_alignment(z_i, z_j)`
  - `cms_attention_matrix(states)`
- Added baselines:
  - cosine similarity (`cosine_similarity`)
  - dot-product similarity (`dot_product_similarity`)
- Added CMS tests:
  - `experiments/tests/test_cms_attention.py`
- Added benchmark script (no quantum deps):
  - `experiments/scripts/benchmark_cms_attention.py`
- Added CMS experiment documentation:
  - `experiments/CMS_EXPERIMENT.md`

### Validation results
- CMS tests:
  - `PYTHONPATH=. backend/.venv/bin/pytest -q experiments/tests/test_cms_attention.py`
  - Result: **5 passed**
- Backend baseline unchanged:
  - `cd backend && PYTHONPATH=. .venv/bin/pytest`
  - Result: **31 passed**
- Benchmark run:
  - `PYTHONPATH=. python3 experiments/scripts/benchmark_cms_attention.py --json`
  - Ran successfully (local, no quantum dependencies)

### Remaining before Phase 2B
1. Decide acceptance thresholds for CMS benchmark deltas (coherence/stability proxies) before adapter integration.
2. Add dataset-backed CMS benchmark (non-synthetic) while keeping runtime untouched.
3. Design feature-flag adapter boundary for optional runtime integration in a later phase.


## Phase 2A Extension (3-2-1)

### Completed work
- `3` Designed feature-flag adapter boundary (isolated):
  - `experiments/cms/adapter.py`
  - Adds `SimilarityBackend` protocol and `CMSAttentionAdapterConfig` with `feature_flag_name='APP_EXPERIMENTAL_CMS_ATTENTION'`.
- `2` Added non-synthetic dataset benchmark mode:
  - `experiments/data/dialogue_corpus.txt`
  - `benchmark_cms_attention.py --dataset-source corpus --corpus-path ...`
  - Text-to-CMS encoding added in `experiments/cms/encoding.py`.
- `1` Added explicit acceptance thresholds and gate output:
  - Benchmark now reports `acceptance.checks` and `acceptance.passed`.
  - Tunable thresholds: `min_coherence_delta`, `min_stability_delta`, `min_mean_similarity_delta`.

### Validation results
- CMS tests:
  - `PYTHONPATH=. backend/.venv/bin/pytest -q experiments/tests`
  - Result: **7 passed**
- Benchmark synthetic mode:
  - `PYTHONPATH=. python3 experiments/scripts/benchmark_cms_attention.py --json`
  - Result: success
- Benchmark corpus mode:
  - `PYTHONPATH=. python3 experiments/scripts/benchmark_cms_attention.py --dataset-source corpus --json`
  - Result: success
- Backend baseline unchanged:
  - `cd backend && PYTHONPATH=. .venv/bin/pytest`
  - Result: **31 passed**
