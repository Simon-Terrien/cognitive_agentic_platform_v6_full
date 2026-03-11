from dataclasses import dataclass, field


@dataclass
class CognitiveState:
    goal: str
    notes: list[str] = field(default_factory=list)
    answer: str | None = None
    confidence: float = 0.0

    def remember(self, note: str) -> None:
        self.notes.append(note)
