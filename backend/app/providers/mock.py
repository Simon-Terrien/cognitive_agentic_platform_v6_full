import time
from typing import Generator

from app.providers.base import Provider, ProviderResult


class MockProvider(Provider):
    def __init__(self, delay_ms: int = 0) -> None:
        self.delay_ms = max(0, delay_ms)

    def health(self) -> tuple[bool, str]:
        return True, 'deterministic-in-process'

    def generate(self, model: str, prompt: str) -> ProviderResult:
        if self.delay_ms:
            time.sleep(self.delay_ms / 1000)
        text = _render_mock_text(model, prompt)
        return ProviderResult(text=text, provider='mock', model=model, raw={'mode': 'mock'})

    def stream(self, model: str, prompt: str) -> Generator[str, None, None]:
        result = self.generate(model, prompt)
        for token in result.text.split():
            yield token + ' '


def _extract(prompt: str, prefix: str) -> str:
    for line in prompt.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ''


def _render_mock_text(model: str, prompt: str) -> str:
    goal = _extract(prompt, 'Goal:')
    step = _extract(prompt, 'Step:')
    if prompt.startswith('Compose a final answer'):
        return f'[mock:{model}] Final answer synthesized from collected notes. Keep focus on the goal and state the conclusion directly.'
    if step:
        return f'[mock:{model}] Completed {step}. Goal context: {goal or "general analysis"}.'
    if goal:
        return f'[mock:{model}] Working on: {goal}.'
    return f'[mock:{model}] Deterministic mock response.'
