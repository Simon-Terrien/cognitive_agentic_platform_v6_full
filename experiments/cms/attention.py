from __future__ import annotations

import cmath
import math
from typing import Callable, Sequence

ComplexState = Sequence[complex]
SimilarityFn = Callable[[ComplexState, ComplexState], float]


def _norm(state: ComplexState) -> float:
    return math.sqrt(sum((abs(value) ** 2 for value in state)))


def _softmax(row: Sequence[float], temperature: float = 1.0) -> list[float]:
    if not row:
        return []
    safe_temperature = max(1e-9, temperature)
    scaled = [value / safe_temperature for value in row]
    anchor = max(scaled)
    exps = [math.exp(value - anchor) for value in scaled]
    total = sum(exps)
    if total <= 0:
        uniform = 1.0 / len(row)
        return [uniform for _ in row]
    return [value / total for value in exps]


def state_overlap(z_i: ComplexState, z_j: ComplexState) -> float:
    """Amplitude overlap in [0, 1], analogous to |<zi, zj>| normalization."""
    norm_i = _norm(z_i)
    norm_j = _norm(z_j)
    if norm_i == 0.0 and norm_j == 0.0:
        return 1.0
    if norm_i == 0.0 or norm_j == 0.0:
        return 0.0
    inner = sum((a.conjugate() * b for a, b in zip(z_i, z_j)))
    return abs(inner) / (norm_i * norm_j)


def phase_alignment(z_i: ComplexState, z_j: ComplexState) -> float:
    """Phase agreement in [0, 1] weighted by component amplitudes."""
    weighted_score = 0.0
    weight_total = 0.0
    for a, b in zip(z_i, z_j):
        amp = abs(a) * abs(b)
        if amp == 0.0:
            continue
        phase_delta = cmath.phase(a) - cmath.phase(b)
        component = (math.cos(phase_delta) + 1.0) / 2.0
        weighted_score += component * amp
        weight_total += amp
    if weight_total == 0.0:
        return 1.0
    return weighted_score / weight_total


def cosine_similarity(z_i: ComplexState, z_j: ComplexState) -> float:
    """Cosine over flattened real/imag dimensions, mapped to [0, 1]."""
    components_i: list[float] = []
    components_j: list[float] = []
    for a, b in zip(z_i, z_j):
        components_i.extend([a.real, a.imag])
        components_j.extend([b.real, b.imag])
    dot = sum((x * y for x, y in zip(components_i, components_j)))
    norm_i = math.sqrt(sum((x * x for x in components_i)))
    norm_j = math.sqrt(sum((y * y for y in components_j)))
    if norm_i == 0.0 and norm_j == 0.0:
        return 1.0
    if norm_i == 0.0 or norm_j == 0.0:
        return 0.0
    raw = dot / (norm_i * norm_j)
    return (max(-1.0, min(1.0, raw)) + 1.0) / 2.0


def dot_product_similarity(z_i: ComplexState, z_j: ComplexState) -> float:
    """Magnitude-normalized inner product mapped to [0, 1]."""
    norm_i = _norm(z_i)
    norm_j = _norm(z_j)
    if norm_i == 0.0 and norm_j == 0.0:
        return 1.0
    if norm_i == 0.0 or norm_j == 0.0:
        return 0.0
    inner = sum((a.conjugate() * b for a, b in zip(z_i, z_j)))
    raw = inner.real / (norm_i * norm_j)
    return (max(-1.0, min(1.0, raw)) + 1.0) / 2.0


def attention_from_similarity(
    states: Sequence[ComplexState],
    similarity_fn: SimilarityFn,
    temperature: float = 1.0,
) -> list[list[float]]:
    matrix: list[list[float]] = []
    for row_state in states:
        similarities = [similarity_fn(row_state, col_state) for col_state in states]
        matrix.append(_softmax(similarities, temperature=temperature))
    return matrix


def cms_attention_matrix(
    states: Sequence[ComplexState],
    phase_weight: float = 0.35,
    temperature: float = 1.0,
) -> list[list[float]]:
    """
    Attention matrix using blended CMS similarity.
    blended_similarity = (1 - phase_weight) * state_overlap + phase_weight * phase_alignment
    """
    weight = max(0.0, min(1.0, phase_weight))

    def blended(a: ComplexState, b: ComplexState) -> float:
        overlap = state_overlap(a, b)
        phase = phase_alignment(a, b)
        return (1.0 - weight) * overlap + weight * phase

    return attention_from_similarity(states, blended, temperature=temperature)

