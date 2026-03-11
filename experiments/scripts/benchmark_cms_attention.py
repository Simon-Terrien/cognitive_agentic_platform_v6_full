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

DEFAULT_CORPUS_PATH = Path(__file__).resolve().parents[1] / 'data' / 'dialogue_corpus.txt'


def _make_state(index: int, dimension: int, rng: random.Random) -> list[complex]:
    """
    Controlled trajectory: smooth amplitude drift + periodic phase shift + light noise.
    """
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


def _build_dataset(length: int, dimension: int, seed: int) -> list[ComplexState]:
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
        states = _build_dataset(length=length, dimension=dimension, seed=seed)
    elif dataset_source == 'corpus':
        resolved_corpus = corpus_path or DEFAULT_CORPUS_PATH
        states = _build_dataset_from_corpus(path=resolved_corpus, limit=length)
    else:
        raise ValueError(f'Unsupported dataset source: {dataset_source}')

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
        'dataset': {
            'source': dataset_source,
            'length': length,
            'dimension': dimension,
            'seed': seed,
            'corpus_path': str(corpus_path) if corpus_path else None,
        },
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


def main() -> None:
    parser = argparse.ArgumentParser(description='Benchmark CMS overlap-attention vs cosine baseline.')
    parser.add_argument('--length', type=int, default=32, help='Number of states in synthetic trajectory.')
    parser.add_argument('--dimension', type=int, default=6, help='Complex dimensions per state.')
    parser.add_argument('--seed', type=int, default=42, help='Random seed.')
    parser.add_argument('--dataset-source', choices=['synthetic', 'corpus'], default='synthetic', help='Input dataset mode.')
    parser.add_argument('--corpus-path', default=str(DEFAULT_CORPUS_PATH), help='Path to plain-text corpus (one line per sample).')
    parser.add_argument('--min-coherence-delta', type=float, default=-0.02, help='Acceptance threshold for coherence delta.')
    parser.add_argument('--min-stability-delta', type=float, default=0.0, help='Acceptance threshold for stability delta.')
    parser.add_argument('--min-mean-similarity-delta', type=float, default=0.0, help='Acceptance threshold for mean-similarity delta.')
    parser.add_argument('--json', action='store_true', help='Print JSON only.')
    args = parser.parse_args()

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

    print('CMS Attention Benchmark')
    print(f"Dataset: length={result['dataset']['length']} dimension={result['dataset']['dimension']} seed={result['dataset']['seed']}")
    print('')
    print(f"CMS coherence proxy:     {result['cms_overlap_attention']['coherence_proxy']:.6f}")
    print(f"Cosine coherence proxy:  {result['cosine_baseline']['coherence_proxy']:.6f}")
    print(f"Delta coherence proxy:   {result['delta']['coherence_proxy']:.6f}")
    print('')
    print(f"CMS stability proxy:     {result['cms_overlap_attention']['trajectory_stability_proxy']:.6f}")
    print(f"Cosine stability proxy:  {result['cosine_baseline']['trajectory_stability_proxy']:.6f}")
    print(f"Delta stability proxy:   {result['delta']['trajectory_stability_proxy']:.6f}")
    print('')
    print(f"Acceptance passed:      {result['acceptance']['passed']}")
    print(f"Acceptance checks:      {json.dumps(result['acceptance']['checks'])}")
    print('')
    print('CMS similarity distribution:')
    print(json.dumps(result['cms_overlap_attention']['similarity_distribution'], indent=2))
    print('Cosine similarity distribution:')
    print(json.dumps(result['cosine_baseline']['similarity_distribution'], indent=2))


if __name__ == '__main__':
    main()
