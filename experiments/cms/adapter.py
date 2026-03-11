from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from experiments.cms.attention import ComplexState, cms_attention_matrix
from experiments.cms.encoding import text_to_cms_state


class SimilarityBackend(Protocol):
    """
    Adapter boundary for future runtime integration.
    This is intentionally isolated to experiments in Phase 2A.
    """

    def encode(self, text: str) -> ComplexState: ...

    def attention(self, states: Sequence[ComplexState]) -> list[list[float]]: ...


@dataclass(frozen=True)
class CMSAttentionAdapterConfig:
    enabled: bool = False
    phase_weight: float = 0.35
    temperature: float = 1.0
    feature_flag_name: str = 'APP_EXPERIMENTAL_CMS_ATTENTION'


class CMSAttentionAdapter:
    def __init__(self, config: CMSAttentionAdapterConfig | None = None) -> None:
        self.config = config or CMSAttentionAdapterConfig()

    def encode(self, text: str) -> ComplexState:
        return text_to_cms_state(text)

    def attention(self, states: Sequence[ComplexState]) -> list[list[float]]:
        return cms_attention_matrix(
            states,
            phase_weight=self.config.phase_weight,
            temperature=self.config.temperature,
        )

