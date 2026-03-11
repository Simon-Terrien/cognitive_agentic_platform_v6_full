import os
from collections.abc import Callable, Generator

from pydantic_ai import Agent

from app.providers.base import Provider, ProviderError, ProviderResult


def _message_from_exception(provider_name: str, base_url: str | None, exc: Exception) -> tuple[int, str]:
    detail = str(exc).strip()
    lowered = detail.lower()
    if any(token in lowered for token in ['connection refused', 'connection error', 'connect error', 'all connection attempts failed']):
        if base_url:
            return 503, f'{provider_name} is unavailable at {base_url}. Start the service or update the provider URL.'
        return 503, f'{provider_name} is unavailable.'
    if 'timed out' in lowered or 'timeout' in lowered:
        if base_url:
            return 504, f'{provider_name} timed out while answering from {base_url}.'
        return 504, f'{provider_name} timed out while answering.'
    if 'status code' in lowered or 'http' in lowered:
        if base_url:
            return 502, f'{provider_name} returned an upstream HTTP error from {base_url}.'
        return 502, f'{provider_name} returned an upstream HTTP error.'
    if base_url:
        return 502, f'{provider_name} request failed via PydanticAI at {base_url}: {detail}'
    return 502, f'{provider_name} request failed via PydanticAI: {detail}'


class PydanticAIProvider(Provider):
    def __init__(
        self,
        provider_name: str,
        agent_builder: Callable[[str], Agent],
        healthcheck: Callable[[], tuple[bool, str]],
        base_url: str | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.agent_builder = agent_builder
        self._healthcheck = healthcheck
        self.base_url = base_url.rstrip('/') if base_url else None

    def health(self) -> tuple[bool, str]:
        return self._healthcheck()

    def generate(self, model: str, prompt: str) -> ProviderResult:
        try:
            agent = self.agent_builder(model)
            result = agent.run_sync(prompt)
            text = result.output if isinstance(result.output, str) else str(result.output)
            return ProviderResult(text=text, provider=self.provider_name, model=model)
        except ProviderError:
            raise
        except Exception as exc:
            status_code, detail = _message_from_exception(self.provider_name, self.base_url, exc)
            raise ProviderError(self.provider_name, detail, status_code=status_code) from exc

    def stream(self, model: str, prompt: str) -> Generator[str, None, None]:
        text = self.generate(model, prompt).text
        for token in text.split():
            yield token + ' '


class NamedPydanticAIProvider(PydanticAIProvider):
    def __init__(self, provider_name: str, model_prefix: str, api_key: str | None, missing_key_hint: str) -> None:
        def _healthcheck() -> tuple[bool, str]:
            if api_key:
                return True, 'configured'
            return False, missing_key_hint

        super().__init__(
            provider_name=provider_name,
            agent_builder=lambda model: Agent(f'{model_prefix}:{model}', output_type=str),
            healthcheck=_healthcheck,
        )


def env_api_key(*names: str) -> str:
    for name in names:
        value = os.getenv(name, '').strip()
        if value:
            return value
    return ''
