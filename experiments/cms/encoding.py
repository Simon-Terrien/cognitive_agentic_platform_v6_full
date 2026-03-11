from __future__ import annotations

import math
import re
from typing import Iterable

from experiments.cms.attention import ComplexState

_CERTAINTY_WORDS = {
    'certain',
    'definitely',
    'always',
    'must',
    'clear',
    'confirmed',
}
_UNCERTAINTY_WORDS = {
    'maybe',
    'might',
    'unclear',
    'probably',
    'possibly',
    'unsure',
}
_TEMPORAL_WORDS = {
    'now',
    'today',
    'tomorrow',
    'yesterday',
    'before',
    'after',
    'later',
    'earlier',
}
_EMOTIONAL_WORDS = {
    'happy',
    'angry',
    'sad',
    'excited',
    'afraid',
    'frustrated',
    'calm',
    'worried',
}


def _tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-zA-Z']+", text.lower()) if token]


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def text_to_cms_state(text: str) -> ComplexState:
    """
    Convert text into a compact 3-complex CMS state.
    z1 = semantic_density + i*pragmatic_load
    z2 = epistemic_certainty + i*temporal_orientation
    z3 = topic_entropy + i*emotional_variance
    """
    tokens = _tokens(text)
    token_count = max(1, len(tokens))
    unique_ratio = len(set(tokens)) / token_count

    punctuation_hits = len(re.findall(r"[?!,:;]", text))
    pragmatic_load = _clamp(punctuation_hits / max(1, len(text) / 20.0))

    certainty_hits = sum((1 for token in tokens if token in _CERTAINTY_WORDS))
    uncertainty_hits = sum((1 for token in tokens if token in _UNCERTAINTY_WORDS))
    epistemic_raw = (certainty_hits - uncertainty_hits) / token_count
    epistemic_certainty = _clamp((epistemic_raw + 1.0) / 2.0)

    temporal_orientation = _clamp(sum((1 for token in tokens if token in _TEMPORAL_WORDS)) / token_count * 3.0)

    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    entropy = 0.0
    for count in counts.values():
        p = count / token_count
        entropy -= p * math.log(p + 1e-12)
    max_entropy = math.log(max(2, len(counts)))
    topic_entropy = _clamp(entropy / max_entropy if max_entropy > 0 else 0.0)

    emotional_variance = _clamp(sum((1 for token in tokens if token in _EMOTIONAL_WORDS)) / token_count * 4.0)

    return [
        complex(unique_ratio, pragmatic_load),
        complex(epistemic_certainty, temporal_orientation),
        complex(topic_entropy, emotional_variance),
    ]


def texts_to_states(texts: Iterable[str]) -> list[ComplexState]:
    return [text_to_cms_state(text) for text in texts]

