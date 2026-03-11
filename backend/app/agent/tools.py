from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class ToolDecision:
    allowed: bool
    tool_id: str
    reason: str


class ToolPolicy:
    def __init__(self) -> None:
        settings = get_settings()
        self.allowlist = {item.strip() for item in settings.agent_tool_allowlist if item.strip()}
        self.block_patterns = [item.lower() for item in settings.agent_block_patterns if item.strip()]

    def evaluate(self, query: str, step: str, tool_id: str) -> ToolDecision:
        normalized_tool = tool_id.split('::', 1)[0]
        if normalized_tool not in self.allowlist:
            return ToolDecision(allowed=False, tool_id=tool_id, reason='tool_not_allowed')
        lowered = f'{query} {step}'.lower()
        for pattern in self.block_patterns:
            if pattern and pattern in lowered:
                return ToolDecision(allowed=False, tool_id=tool_id, reason=f'blocked_pattern:{pattern}')
        return ToolDecision(allowed=True, tool_id=tool_id, reason='allowed')


class ToolRouter:
    def resolve(self, query: str, step: str) -> str:
        lowered = query.lower()
        if 'dataset' in lowered:
            return 'dataset_registry'
        if 'benchmark' in lowered or 'latency' in lowered:
            return 'benchmark_notes'
        if 'train' in lowered or 'lora' in lowered:
            return 'training_notes'
        return f'reasoning::{step}'

    def run(self, tool_id: str) -> str:
        normalized = tool_id.split('::', 1)[0]
        return f'tool={normalized}'

    def execute(self, query: str, step: str) -> str:
        return self.run(self.resolve(query, step))
