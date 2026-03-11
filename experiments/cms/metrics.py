from __future__ import annotations

import math
from typing import Sequence

from experiments.cms.attention import ComplexState, cosine_similarity, state_overlap


def coherence_proxy(attention: Sequence[Sequence[float]]) -> float:
    """
    Sequence coherence proxy:
    mean attention weight assigned to the next state i -> i+1.
    """
    if len(attention) < 2:
        return 1.0
    weights = []
    for index, row in enumerate(attention[:-1]):
        if index + 1 < len(row):
            weights.append(row[index + 1])
    if not weights:
        return 0.0
    return sum(weights) / len(weights)


def trajectory_stability_proxy(states: Sequence[ComplexState]) -> float:
    """
    Mean overlap between consecutive states.
    Higher values imply smoother trajectory evolution.
    """
    if len(states) < 2:
        return 1.0
    overlaps = [state_overlap(states[i], states[i + 1]) for i in range(len(states) - 1)]
    return sum(overlaps) / len(overlaps)


def baseline_stability_proxy(states: Sequence[ComplexState]) -> float:
    """Cosine-based trajectory stability baseline."""
    if len(states) < 2:
        return 1.0
    values = [cosine_similarity(states[i], states[i + 1]) for i in range(len(states) - 1)]
    return sum(values) / len(values)


def similarity_distribution(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {
            'count': 0.0,
            'min': 0.0,
            'max': 0.0,
            'mean': 0.0,
            'std': 0.0,
            'p10': 0.0,
            'p50': 0.0,
            'p90': 0.0,
        }

    ordered = sorted(values)
    count = len(ordered)
    mean = sum(ordered) / count
    variance = sum(((value - mean) ** 2 for value in ordered)) / count

    def percentile(p: float) -> float:
        if count == 1:
            return ordered[0]
        rank = max(0.0, min(1.0, p)) * (count - 1)
        low = math.floor(rank)
        high = math.ceil(rank)
        if low == high:
            return ordered[low]
        fraction = rank - low
        return ordered[low] + (ordered[high] - ordered[low]) * fraction

    return {
        'count': float(count),
        'min': ordered[0],
        'max': ordered[-1],
        'mean': mean,
        'std': math.sqrt(variance),
        'p10': percentile(0.10),
        'p50': percentile(0.50),
        'p90': percentile(0.90),
    }

