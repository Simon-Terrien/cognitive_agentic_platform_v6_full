import httpx
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider as PydanticAIOpenAIProvider

from app.providers.pydantic_adapter import PydanticAIProvider


class OpenAICompatibleProvider(PydanticAIProvider):
    def __init__(self, base_url: str, provider_name: str, timeout: float = 60.0, api_key: str = 'local') -> None:
        self.base_url = base_url.rstrip('/')
        self.provider_name = provider_name
        self.timeout = timeout
        self.api_key = api_key
        super().__init__(
            provider_name=provider_name,
            agent_builder=lambda model: Agent(
                OpenAIChatModel(
                    model_name=model,
                    provider=PydanticAIOpenAIProvider(base_url=self.base_url, api_key=self.api_key),
                ),
                output_type=str,
            ),
            healthcheck=self._healthcheck,
            base_url=self.base_url,
        )

    def _healthcheck(self) -> tuple[bool, str]:
        url = f'{self.base_url}/models'
        try:
            response = httpx.get(url, timeout=0.5)
            response.raise_for_status()
            return True, 'reachable'
        except Exception as exc:
            return False, str(exc)
