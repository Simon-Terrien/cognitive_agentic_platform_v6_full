from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable

from experiments.cms.attention import ComplexState

_CERTAINTY_WORDS = {
    'certain',
    'definitely',
    'always',
    'must',
    'clear',
    'confirmed',
    'proven',
    'exactly',
}
_UNCERTAINTY_WORDS = {
    'maybe',
    'might',
    'unclear',
    'probably',
    'possibly',
    'unsure',
    'perhaps',
    'unknown',
}
_TEMPORAL_PAST = {'yesterday', 'before', 'earlier', 'previously', 'last'}
_TEMPORAL_PRESENT = {'now', 'today', 'currently', 'presently'}
_TEMPORAL_FUTURE = {'tomorrow', 'later', 'soon', 'next', 'upcoming'}
_EMOTION_POSITIVE = {'happy', 'excited', 'calm', 'relieved', 'confident', 'hopeful'}
_EMOTION_NEGATIVE = {'angry', 'sad', 'afraid', 'frustrated', 'worried', 'anxious'}
_DISCOURSE_MARKERS = {
    'however',
    'therefore',
    'because',
    'although',
    'meanwhile',
    'moreover',
    'but',
    'so',
}
_CLAUSE_MARKERS = {'because', 'although', 'if', 'while', 'when', 'which', 'that'}
_STOPWORDS = {
    'the',
    'a',
    'an',
    'and',
    'or',
    'but',
    'if',
    'to',
    'of',
    'in',
    'on',
    'for',
    'with',
    'is',
    'are',
    'was',
    'were',
    'be',
    'it',
    'this',
    'that',
    'we',
    'you',
    'they',
    'i',
}


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _scale_01_to_signed(value: float) -> float:
    return max(-1.0, min(1.0, 2.0 * value - 1.0))


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z']+", text.lower()) if token]


def _sentences(text: str) -> list[str]:
    parts = [segment.strip() for segment in re.split(r'[.!?]+', text) if segment.strip()]
    return parts or [text.strip() or '']


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _bounded_entropy(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    total = len(tokens)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log(p + 1e-12)
    max_entropy = math.log(max(2, len(counts)))
    return _clamp(entropy / max_entropy if max_entropy > 0 else 0.0)


@dataclass(frozen=True)
class CMSFeatureVector:
    lexical_diversity: float
    discourse_load: float
    certainty: float
    uncertainty: float
    temporal_orientation: float
    emotional_valence: float
    emotional_intensity: float
    sentence_length: float
    structural_complexity: float
    topic_entropy: float
    content_density: float


def extract_cms_features(text: str) -> CMSFeatureVector:
    """
    Heuristic, dependency-light feature extraction for CMS experiments.
    This is not a production linguistic representation.
    """
    tokens = _tokens(text)
    token_count = max(1, len(tokens))
    sentence_chunks = _sentences(text)
    sentence_count = max(1, len(sentence_chunks))

    unique_ratio = _safe_ratio(len(set(tokens)), token_count)
    repetition_penalty = _safe_ratio(sum((1 for token in tokens if tokens.count(token) > 1)), token_count) * 0.25
    lexical_diversity = _clamp(unique_ratio - repetition_penalty)

    punctuation_hits = len(re.findall(r'[,:;?!()\-\"]', text))
    punctuation_density = _safe_ratio(punctuation_hits, max(1, len(text) / 12.0))
    discourse_marker_density = _safe_ratio(sum((1 for token in tokens if token in _DISCOURSE_MARKERS)), token_count) * 4.0
    discourse_load = _clamp((punctuation_density + discourse_marker_density) / 2.0)

    certainty_density = _safe_ratio(sum((1 for token in tokens if token in _CERTAINTY_WORDS)), token_count)
    uncertainty_density = _safe_ratio(sum((1 for token in tokens if token in _UNCERTAINTY_WORDS)), token_count)
    certainty = _clamp(0.5 + (certainty_density - uncertainty_density) * 4.0)
    uncertainty = _clamp(uncertainty_density * 6.0)

    past = sum((1 for token in tokens if token in _TEMPORAL_PAST))
    present = sum((1 for token in tokens if token in _TEMPORAL_PRESENT))
    future = sum((1 for token in tokens if token in _TEMPORAL_FUTURE))
    temporal_raw = future - past + 0.5 * present
    temporal_orientation = _clamp(0.5 + temporal_raw / max(1, token_count * 0.8))

    positive = sum((1 for token in tokens if token in _EMOTION_POSITIVE))
    negative = sum((1 for token in tokens if token in _EMOTION_NEGATIVE))
    emotional_valence = _clamp(0.5 + (positive - negative) / max(1, token_count * 0.4))
    emotional_intensity = _clamp(_safe_ratio(positive + negative, token_count) * 5.0)

    average_sentence_length = _safe_ratio(token_count, sentence_count)
    sentence_length = _clamp(average_sentence_length / 24.0)
    clause_density = _safe_ratio(sum((1 for token in tokens if token in _CLAUSE_MARKERS)), token_count) * 6.0
    structural_complexity = _clamp((sentence_length + clause_density) / 2.0)

    topic_entropy = _bounded_entropy(tokens)
    content_density = _clamp(_safe_ratio(sum((1 for token in tokens if token not in _STOPWORDS)), token_count))

    return CMSFeatureVector(
        lexical_diversity=lexical_diversity,
        discourse_load=discourse_load,
        certainty=certainty,
        uncertainty=uncertainty,
        temporal_orientation=temporal_orientation,
        emotional_valence=emotional_valence,
        emotional_intensity=emotional_intensity,
        sentence_length=sentence_length,
        structural_complexity=structural_complexity,
        topic_entropy=topic_entropy,
        content_density=content_density,
    )


def text_to_cms_state(text: str) -> ComplexState:
    """
    Experimental CMS projection to 6 complex dimensions.
    Axes are intentionally interpretable and heuristic.
    """
    f = extract_cms_features(text)

    return [
        complex(_scale_01_to_signed(f.lexical_diversity), _scale_01_to_signed(f.discourse_load)),
        complex(_scale_01_to_signed(f.certainty), _scale_01_to_signed(f.temporal_orientation)),
        complex(_scale_01_to_signed(f.topic_entropy), _scale_01_to_signed(f.emotional_valence)),
        complex(_scale_01_to_signed(f.sentence_length), _scale_01_to_signed(f.structural_complexity)),
        complex(_scale_01_to_signed(f.emotional_intensity), _scale_01_to_signed(f.uncertainty)),
        complex(_scale_01_to_signed(f.content_density), _scale_01_to_signed((f.lexical_diversity + f.topic_entropy) / 2.0)),
    ]


def texts_to_states(texts: Iterable[str]) -> list[ComplexState]:
    return [text_to_cms_state(text) for text in texts]

