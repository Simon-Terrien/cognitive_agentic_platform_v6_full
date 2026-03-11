from __future__ import annotations

import math

from experiments.cms.attention import (
    cms_attention_matrix,
    cosine_similarity,
    phase_alignment,
    state_overlap,
)


def test_identical_states_have_maximum_overlap():
    state = [complex(1.0, 2.0), complex(-0.5, 0.25), complex(0.9, -0.1)]
    assert math.isclose(state_overlap(state, state), 1.0, rel_tol=1e-9, abs_tol=1e-9)


def test_orthogonal_or_dissimilar_states_have_lower_overlap():
    z_i = [complex(1.0, 0.0), complex(0.0, 0.0)]
    z_j = [complex(0.0, 0.0), complex(1.0, 0.0)]
    assert math.isclose(state_overlap(z_i, z_j), 0.0, rel_tol=1e-9, abs_tol=1e-9)
    assert state_overlap(z_i, z_j) < state_overlap(z_i, z_i)


def test_phase_shift_behavior_reduces_phase_alignment():
    reference = [complex(1.0, 0.0), complex(0.5, 0.0)]
    same_phase = [complex(2.0, 0.0), complex(1.0, 0.0)]
    shifted = [complex(-2.0, 0.0), complex(-1.0, 0.0)]

    aligned_same = phase_alignment(reference, same_phase)
    aligned_shifted = phase_alignment(reference, shifted)

    assert aligned_same > aligned_shifted
    assert aligned_same > 0.9
    assert aligned_shifted < 0.1


def test_attention_matrix_rows_are_normalized():
    states = [
        [complex(1.0, 0.0), complex(0.2, 0.2)],
        [complex(0.9, 0.1), complex(0.3, 0.2)],
        [complex(-0.8, 0.2), complex(-0.1, 0.9)],
    ]
    matrix = cms_attention_matrix(states)
    assert len(matrix) == 3
    for row in matrix:
        assert len(row) == 3
        assert all(value >= 0.0 for value in row)
        assert math.isclose(sum(row), 1.0, rel_tol=1e-9, abs_tol=1e-9)


def test_cosine_baseline_is_bounded():
    a = [complex(1.0, 0.0), complex(0.0, 1.0)]
    b = [complex(1.0, 0.0), complex(0.0, 1.0)]
    c = [complex(-1.0, 0.0), complex(0.0, -1.0)]
    assert 0.0 <= cosine_similarity(a, b) <= 1.0
    assert 0.0 <= cosine_similarity(a, c) <= 1.0
    assert cosine_similarity(a, b) > cosine_similarity(a, c)

