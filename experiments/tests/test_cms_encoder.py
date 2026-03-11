from __future__ import annotations

from experiments.cms.encoding import extract_cms_features, text_to_cms_state


def test_lexical_diversity_distinguishes_repetition():
    repetitive = extract_cms_features('error error error error error')
    diverse = extract_cms_features('error mitigation fallback latency token scheduler')
    assert diverse.lexical_diversity > repetitive.lexical_diversity


def test_certainty_uncertainty_signal_polarity():
    certain = extract_cms_features('This is definitely confirmed and certainly clear.')
    uncertain = extract_cms_features('Maybe this might be unclear and possibly uncertain.')
    assert certain.certainty > uncertain.certainty
    assert uncertain.uncertainty > certain.uncertainty


def test_emotional_signal_varies_with_language():
    positive = extract_cms_features('I feel calm, hopeful, and excited about this result.')
    negative = extract_cms_features('I feel worried, afraid, and frustrated by this incident.')
    assert positive.emotional_valence > negative.emotional_valence
    assert positive.emotional_intensity > 0.0
    assert negative.emotional_intensity > 0.0


def test_structural_complexity_reflects_sentence_form():
    simple = extract_cms_features('System stable.')
    complex_case = extract_cms_features('Although the model responded quickly, we delayed rollout because the downstream queue might overflow.')
    assert complex_case.structural_complexity > simple.structural_complexity
    assert complex_case.sentence_length >= simple.sentence_length


def test_text_to_cms_state_shape_and_type():
    state = text_to_cms_state('We should probably review the timeline before tomorrow.')
    assert len(state) == 6
    assert all(isinstance(value, complex) for value in state)

