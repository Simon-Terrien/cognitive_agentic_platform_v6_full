#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import random
from typing import Sequence

from experiments.cms.attention import (
    ComplexState,
    attention_from_similarity,
    cms_attention_matrix,
    cosine_similarity,
    state_overlap,
)
from experiments.cms.encoding import texts_to_states
from experiments.cms.metrics import (
    baseline_stability_proxy,
    coherence_proxy,
    similarity_distribution,
    trajectory_stability_proxy,
)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
DEFAULT_CORPUS_PATH = DEFAULT_DATA_DIR / 'dialogue_corpus.txt'


def _make_state(index: int, dimension: int, rng: random.Random) -> list[complex]:
    state: list[complex] = []
    for dim in range(dimension):
        base_amp = 0.8 + 0.2 * math.sin((index + 1) * (dim + 1) * 0.07)
        base_phase = 0.22 * index + 0.11 * dim
        noise_amp = rng.uniform(-0.03, 0.03)
        noise_phase = rng.uniform(-0.05, 0.05)
        amp = max(0.01, base_amp + noise_amp)
        phase = base_phase + noise_phase
        state.append(complex(amp * math.cos(phase), amp * math.sin(phase)))
    return state


def _build_synthetic_dataset(length: int, dimension: int, seed: int) -> list[ComplexState]:
    rng = random.Random(seed)
    return [_make_state(index=i, dimension=dimension, rng=rng) for i in range(length)]


def _build_dataset_from_corpus(path: Path, limit: int | None = None) -> list[ComplexState]:
    lines = [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if limit is not None and limit > 0:
        lines = lines[:limit]
    return texts_to_states(lines)


def _all_pair_scores(states: Sequence[ComplexState], fn) -> list[float]:
    values: list[float] = []
    for i, state_i in enumerate(states):
        for j, state_j in enumerate(states):
            if i == j:
                continue
            values.append(fn(state_i, state_j))
    return values


def _evaluate_thresholds(
    coherence_delta: float,
    stability_delta: float,
    mean_similarity_delta: float,
    min_coherence_delta: float,
    min_stability_delta: float,
    min_mean_similarity_delta: float,
) -> dict:
    checks = {
        'coherence_proxy': coherence_delta >= min_coherence_delta,
        'trajectory_stability_proxy': stability_delta >= min_stability_delta,
        'mean_similarity': mean_similarity_delta >= min_mean_similarity_delta,
    }
    return {
        'thresholds': {
            'min_coherence_delta': min_coherence_delta,
            'min_stability_delta': min_stability_delta,
            'min_mean_similarity_delta': min_mean_similarity_delta,
        },
        'checks': checks,
        'passed': all(checks.values()),
    }


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = max(0.0, min(1.0, q)) * (len(ordered) - 1)
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    fraction = position - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def _compute_result_payload(
    states: Sequence[ComplexState],
    dataset_meta: dict,
    min_coherence_delta: float,
    min_stability_delta: float,
    min_mean_similarity_delta: float,
) -> dict:
    cms_attention = cms_attention_matrix(states)
    cosine_attention = attention_from_similarity(states, cosine_similarity)
    cms_similarity_values = _all_pair_scores(states, state_overlap)
    cosine_similarity_values = _all_pair_scores(states, cosine_similarity)

    coherence_delta = coherence_proxy(cms_attention) - coherence_proxy(cosine_attention)
    stability_delta = trajectory_stability_proxy(states) - baseline_stability_proxy(states)
    mean_similarity_delta = (
        similarity_distribution(cms_similarity_values)['mean']
        - similarity_distribution(cosine_similarity_values)['mean']
    )

    return {
        'dataset': dataset_meta,
        'cms_overlap_attention': {
            'coherence_proxy': coherence_proxy(cms_attention),
            'trajectory_stability_proxy': trajectory_stability_proxy(states),
            'similarity_distribution': similarity_distribution(cms_similarity_values),
        },
        'cosine_baseline': {
            'coherence_proxy': coherence_proxy(cosine_attention),
            'trajectory_stability_proxy': baseline_stability_proxy(states),
            'similarity_distribution': similarity_distribution(cosine_similarity_values),
        },
        'delta': {
            'coherence_proxy': coherence_delta,
            'trajectory_stability_proxy': stability_delta,
            'mean_similarity': mean_similarity_delta,
        },
        'acceptance': _evaluate_thresholds(
            coherence_delta=coherence_delta,
            stability_delta=stability_delta,
            mean_similarity_delta=mean_similarity_delta,
            min_coherence_delta=min_coherence_delta,
            min_stability_delta=min_stability_delta,
            min_mean_similarity_delta=min_mean_similarity_delta,
        ),
    }


def calibrate_thresholds_from_results(results: Sequence[dict], quantile: float = 0.25) -> dict[str, float]:
    coherence_deltas = [item['delta']['coherence_proxy'] for item in results]
    stability_deltas = [item['delta']['trajectory_stability_proxy'] for item in results]
    mean_deltas = [item['delta']['mean_similarity'] for item in results]
    return {
        'min_coherence_delta': _percentile(coherence_deltas, quantile),
        'min_stability_delta': _percentile(stability_deltas, quantile),
        'min_mean_similarity_delta': _percentile(mean_deltas, quantile),
    }


def run_benchmark(
    length: int,
    dimension: int,
    seed: int,
    dataset_source: str = 'synthetic',
    corpus_path: Path | None = None,
    min_coherence_delta: float = -0.02,
    min_stability_delta: float = 0.0,
    min_mean_similarity_delta: float = 0.0,
) -> dict:
    if dataset_source == 'synthetic':
        states = _build_synthetic_dataset(length=length, dimension=dimension, seed=seed)
        return _compute_result_payload(
            states=states,
            dataset_meta={
                'source': dataset_source,
                'name': 'synthetic',
                'length': len(states),
                'dimension': dimension,
                'seed': seed,
                'corpus_path': None,
            },
            min_coherence_delta=min_coherence_delta,
            min_stability_delta=min_stability_delta,
            min_mean_similarity_delta=min_mean_similarity_delta,
        )
    if dataset_source == 'corpus':
        resolved = corpus_path or DEFAULT_CORPUS_PATH
        states = _build_dataset_from_corpus(path=resolved, limit=length)
        return _compute_result_payload(
            states=states,
            dataset_meta={
                'source': dataset_source,
                'name': resolved.stem,
                'length': len(states),
                'dimension': len(states[0]) if states else 0,
                'seed': seed,
                'corpus_path': str(resolved),
            },
            min_coherence_delta=min_coherence_delta,
            min_stability_delta=min_stability_delta,
            min_mean_similarity_delta=min_mean_similarity_delta,
        )
    raise ValueError(f'Unsupported dataset source: {dataset_source}')


def run_multi_corpus_benchmark(
    data_dir: Path,
    length: int,
    seed: int,
    quantile: float = 0.25,
) -> dict:
    corpus_files = sorted(data_dir.glob('*_corpus.txt'))
    if not corpus_files:
        raise ValueError(f'No corpus files found in {data_dir}')

    provisional_results: list[dict] = []
    for corpus_path in corpus_files:
        provisional_results.append(
            run_benchmark(
                length=length,
                dimension=0,
                seed=seed,
                dataset_source='corpus',
                corpus_path=corpus_path,
                min_coherence_delta=-1.0,
                min_stability_delta=-1.0,
                min_mean_similarity_delta=-1.0,
            )
        )

    calibrated = calibrate_thresholds_from_results(provisional_results, quantile=quantile)
    per_corpus: dict[str, dict] = {}
    for result in provisional_results:
        name = result['dataset']['name']
        per_corpus[name] = _compute_result_payload(
            states=_build_dataset_from_corpus(Path(result['dataset']['corpus_path']), limit=length),
            dataset_meta=result['dataset'],
            min_coherence_delta=calibrated['min_coherence_delta'],
            min_stability_delta=calibrated['min_stability_delta'],
            min_mean_similarity_delta=calibrated['min_mean_similarity_delta'],
        )

    deltas = [item['delta'] for item in per_corpus.values()]
    passes = [item['acceptance']['passed'] for item in per_corpus.values()]
    aggregate = {
        'num_corpora': len(per_corpus),
        'pass_rate': sum((1 for passed in passes if passed)) / len(passes),
        'delta_distribution': {
            'coherence_proxy': similarity_distribution([item['coherence_proxy'] for item in deltas]),
            'trajectory_stability_proxy': similarity_distribution([item['trajectory_stability_proxy'] for item in deltas]),
            'mean_similarity': similarity_distribution([item['mean_similarity'] for item in deltas]),
        },
    }

    return {
        'mode': 'multi-corpus',
        'threshold_calibration': {
            'method': f'quantile_{quantile}',
            'thresholds': calibrated,
        },
        'per_corpus': per_corpus,
        'aggregate': aggregate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Benchmark CMS overlap-attention vs cosine baseline.')
    parser.add_argument('--length', type=int, default=32, help='Number of states for synthetic mode or row limit for corpus mode.')
    parser.add_argument('--dimension', type=int, default=6, help='Complex dimensions for synthetic mode.')
    parser.add_argument('--seed', type=int, default=42, help='Random seed.')
    parser.add_argument('--dataset-source', choices=['synthetic', 'corpus', 'multi-corpus'], default='synthetic')
    parser.add_argument('--corpus-path', default=str(DEFAULT_CORPUS_PATH), help='Path to plain-text corpus for corpus mode.')
    parser.add_argument('--data-dir', default=str(DEFAULT_DATA_DIR), help='Directory containing *_corpus.txt files for multi-corpus mode.')
    parser.add_argument('--calibration-quantile', type=float, default=0.25, help='Quantile used to derive provisional thresholds in multi-corpus mode.')
    parser.add_argument('--min-coherence-delta', type=float, default=-0.02, help='Acceptance threshold for single-run coherence delta.')
    parser.add_argument('--min-stability-delta', type=float, default=0.0, help='Acceptance threshold for single-run stability delta.')
    parser.add_argument('--min-mean-similarity-delta', type=float, default=0.0, help='Acceptance threshold for single-run mean-similarity delta.')
    parser.add_argument('--json', action='store_true', help='Print JSON only.')
    args = parser.parse_args()

    if args.dataset_source == 'multi-corpus':
        result = run_multi_corpus_benchmark(
            data_dir=Path(args.data_dir),
            length=args.length,
            seed=args.seed,
            quantile=args.calibration_quantile,
        )
    else:
        result = run_benchmark(
            length=args.length,
            dimension=args.dimension,
            seed=args.seed,
            dataset_source=args.dataset_source,
            corpus_path=Path(args.corpus_path),
            min_coherence_delta=args.min_coherence_delta,
            min_stability_delta=args.min_stability_delta,
            min_mean_similarity_delta=args.min_mean_similarity_delta,
        )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    if args.dataset_source == 'multi-corpus':
        print('CMS Multi-Corpus Benchmark')
        print(f"Calibrated thresholds: {json.dumps(result['threshold_calibration']['thresholds'])}")
        print(f"Pass rate: {result['aggregate']['pass_rate']:.3f} ({result['aggregate']['num_corpora']} corpora)")
        print('Per-corpus outcomes:')
        for name, corpus_result in result['per_corpus'].items():
            print(f"- {name}: passed={corpus_result['acceptance']['passed']} deltas={corpus_result['delta']}")
        return

    print('CMS Attention Benchmark')
    print(f"Dataset: source={result['dataset']['source']} name={result['dataset']['name']} length={result['dataset']['length']}")
    print(f"Delta coherence: {result['delta']['coherence_proxy']:.6f}")
    print(f"Delta stability: {result['delta']['trajectory_stability_proxy']:.6f}")
    print(f"Delta mean similarity: {result['delta']['mean_similarity']:.6f}")
    print(f"Acceptance passed: {result['acceptance']['passed']}")


if __name__ == '__main__':
    main()

