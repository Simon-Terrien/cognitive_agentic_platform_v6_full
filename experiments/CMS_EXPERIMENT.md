# CMS Overlap-Attention Experiment (Phase 2A)

## What this is
This experiment prototypes a **Complex Meaning Space (CMS)** similarity/attention mechanism in isolation from the runtime.

Implemented in `experiments/cms/attention.py`:
- `state_overlap(z_i, z_j)`
- `phase_alignment(z_i, z_j)`
- `cms_attention_matrix(states)`

Baselines included:
- cosine similarity (`cosine_similarity`)
- dot-product-like baseline (`dot_product_similarity`)

## Why this is experimental
- It is not connected to `agent_engine.py`.
- It uses synthetic controlled trajectories and proxy metrics, not production user traffic.
- Similarity and attention choices (phase weighting, softmax temperature, metric definitions) are hypothesis-driven and can change.

## Benchmark and metrics
Run:

```bash
python3 experiments/scripts/benchmark_cms_attention.py
```

JSON output:

```bash
python3 experiments/scripts/benchmark_cms_attention.py --json
```

Non-synthetic corpus mode:

```bash
python3 experiments/scripts/benchmark_cms_attention.py \
  --dataset-source corpus \
  --corpus-path experiments/data/dialogue_corpus.txt
```

Reported metrics:
- `coherence_proxy`: average attention weight from state `i` to `i+1`
- `trajectory_stability_proxy`: average consecutive-state similarity
- `similarity_distribution`: min/max/mean/std and percentiles

Acceptance gate output:
- `acceptance.checks`: boolean checks for each delta threshold
- `acceptance.passed`: overall gate decision

Default threshold profile (tunable):
- `min_coherence_delta=-0.02`
- `min_stability_delta=0.0`
- `min_mean_similarity_delta=0.0`

## Test coverage
`experiments/tests/test_cms_attention.py` validates:
- identical states produce maximum overlap
- orthogonal/dissimilar states produce lower overlap
- phase shift decreases phase alignment
- attention rows normalize to probability distributions

## Future integration path (not implemented in Phase 2A)
Potential runtime integration later can be done behind an adapter/flag:
1. Use the experimental adapter boundary in `experiments/cms/adapter.py`:
   - `SimilarityBackend` protocol
   - `CMSAttentionAdapterConfig` (includes `feature_flag_name`, default `APP_EXPERIMENTAL_CMS_ATTENTION`)
   - `CMSAttentionAdapter`
2. Keep default behavior unchanged (`cosine`) until benchmark gains are consistent.
3. Introduce opt-in runtime flag (e.g. `APP_EXPERIMENTAL_CMS_ATTENTION=true`).
4. Record production-safe telemetry before making CMS path default.
