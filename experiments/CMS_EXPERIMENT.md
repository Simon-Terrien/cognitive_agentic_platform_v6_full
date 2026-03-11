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

Experimental encoder:
- `experiments/cms/encoding.py`
- pipeline: tokenize -> feature extraction -> CMS projection (`text_to_cms_state`)

## Why this is experimental
- It is not connected to `agent_engine.py`.
- It uses synthetic controlled trajectories and proxy metrics, not production user traffic.
- Similarity and attention choices (phase weighting, softmax temperature, metric definitions) are hypothesis-driven and can change.
- The text encoder is heuristic and lexicon-based; it is not a learned representation.

## Encoder limitations
- Language coverage is limited to the embedded lexicons and English-centric heuristics.
- No syntactic parser or semantic model is used; structural complexity is approximate.
- Feature interactions are hand-tuned and can overfit to small corpora.
- Scores should be treated as exploratory signals, not cognitive truth.

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

Multi-corpus calibration mode:

```bash
python3 experiments/scripts/benchmark_cms_attention.py \
  --dataset-source multi-corpus \
  --data-dir experiments/data \
  --json
```

Reported metrics:
- `coherence_proxy`: average attention weight from state `i` to `i+1`
- `trajectory_stability_proxy`: average consecutive-state similarity
- `similarity_distribution`: min/max/mean/std and percentiles

Acceptance gate output:
- `acceptance.checks`: boolean checks for each delta threshold
- `acceptance.passed`: overall gate decision

## Benchmark datasets used
- `experiments/data/technical_corpus.txt` (analytical/technical discourse)
- `experiments/data/conversational_corpus.txt` (dialogic/conversational discourse)
- `experiments/data/emotional_corpus.txt` (emotionally variable discourse)
- `experiments/data/dialogue_corpus.txt` (mixed operational dialogue)

Task-grounded dataset:
- `experiments/data/retrieval_rerank_dataset.json` (graded relevance labels for reranking)

## Threshold rationale (provisional)
For `multi-corpus` mode, thresholds are calibrated from observed corpus deltas:
- method: lower quantile across per-corpus deltas (default q=0.25)
- output: `threshold_calibration.thresholds`
- use: each corpus run is evaluated against these calibrated thresholds

This replaces arbitrary static thresholds with data-derived provisional bounds.

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

## Current recommendation status
- **Conditionally ready for Phase 2B design work** (adapter and evaluation policy), but **not ready for runtime integration**.
- Runtime integration should remain blocked until corpus-level pass rate and threshold stability are acceptable over larger datasets.

## Task-grounded validation (Phase 2A.2)
Primary task: **retrieval reranking**.

Run:

```bash
python3 experiments/scripts/benchmark_cms_task.py --json
```

Task metrics reported:
- `hit_at_1`
- `mrr`
- `ndcg_at_3`

Interpretation guide:
- `practical_signal=positive`: consistent downstream gain vs cosine baseline
- `practical_signal=weak_or_mixed`: no robust practical advantage yet
- `practical_signal=negative`: consistently worse than baseline

Current phase recommendation should be based on this task signal plus corpus calibration stability.
