#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import random
from typing import Sequence

from experiments.cms.attention import (
    ComplexState,
    attention_from_similarity,
    cms_attention_matrix,
    cosine_similarity,
    state_overlap,
)
from experiments.cms.metrics import (
    baseline_stability_proxy,
    coherence_proxy,
    similarity_distribution,
    trajectory_stability_proxy,
)


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


def _all_pair_scores(states: Sequence[ComplexState], fn) -> list[float]:
    values: list[float] = []
    for i, state_i in enumerate(states):
        for j, state_j in enumerate(states):
            if i == j:
                continue
            values.append(fn(state_i, state_j))
    return values


def run_benchmark(length: int, dimension: int, seed: int) -> dict:
    states = _build_dataset(length=length, dimension=dimension, seed=seed)
    cms_attention = cms_attention_matrix(states)
    cosine_attention = attention_from_similarity(states, cosine_similarity)

    cms_similarity_values = _all_pair_scores(states, state_overlap)
    cosine_similarity_values = _all_pair_scores(states, cosine_similarity)

    return {
        'dataset': {
            'length': length,
            'dimension': dimension,
            'seed': seed,
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
            'coherence_proxy': coherence_proxy(cms_attention) - coherence_proxy(cosine_attention),
            'trajectory_stability_proxy': trajectory_stability_proxy(states) - baseline_stability_proxy(states),
            'mean_similarity': similarity_distribution(cms_similarity_values)['mean']
            - similarity_distribution(cosine_similarity_values)['mean'],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Benchmark CMS overlap-attention vs cosine baseline.')
    parser.add_argument('--length', type=int, default=32, help='Number of states in synthetic trajectory.')
    parser.add_argument('--dimension', type=int, default=6, help='Complex dimensions per state.')
    parser.add_argument('--seed', type=int, default=42, help='Random seed.')
    parser.add_argument('--json', action='store_true', help='Print JSON only.')
    args = parser.parse_args()

    result = run_benchmark(length=args.length, dimension=args.dimension, seed=args.seed)
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
    print('CMS similarity distribution:')
    print(json.dumps(result['cms_overlap_attention']['similarity_distribution'], indent=2))
    print('Cosine similarity distribution:')
    print(json.dumps(result['cosine_baseline']['similarity_distribution'], indent=2))


if __name__ == '__main__':
    main()

