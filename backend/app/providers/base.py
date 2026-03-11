from dataclasses import dataclass
from typing import Generator


@dataclass
class ProviderResult:
    text: str
    provider: str
    model: str
    raw: dict | None = None


class ProviderError(Exception):
    def __init__(self, provider: str, detail: str, status_code: int = 503) -> None:
        super().__init__(detail)
        self.provider = provider
        self.detail = detail
        self.status_code = status_code


class Provider:
    def health(self) -> tuple[bool, str]:
        raise NotImplementedError

    def generate(self, model: str, prompt: str) -> ProviderResult:
        raise NotImplementedError

    def stream(self, model: str, prompt: str) -> Generator[str, None, None]:
        raise NotImplementedError
