from collections.abc import Generator

from ollama import Client, ResponseError

from app.providers.base import Provider, ProviderError, ProviderResult


def _extract_text(payload: object) -> str:
    if isinstance(payload, dict):
        message = payload.get('message')
        if isinstance(message, dict):
            content = message.get('content')
            if isinstance(content, str):
                return content
        content = payload.get('response')
        if isinstance(content, str):
            return content
        return ''
    message = getattr(payload, 'message', None)
    content = getattr(message, 'content', None)
    if isinstance(content, str):
        return content
    raw_response = getattr(payload, 'response', None)
    if isinstance(raw_response, str):
        return raw_response
    return ''


def _map_exception(base_url: str, exc: Exception) -> ProviderError:
    detail = str(exc).strip()
    lowered = detail.lower()
    if isinstance(exc, ResponseError):
        return ProviderError('ollama', f'ollama returned HTTP {exc.status_code}: {detail}', status_code=502)
    if any(token in lowered for token in ['connection refused', 'connection error', 'all connection attempts failed']):
        return ProviderError(
            'ollama',
            f'ollama is unavailable at {base_url}. Start the service or update the provider URL.',
            status_code=503,
        )
    if 'timed out' in lowered or 'timeout' in lowered:
        return ProviderError('ollama', f'ollama timed out at {base_url}.', status_code=504)
    return ProviderError('ollama', f'ollama request failed at {base_url}: {detail}', status_code=502)


class OllamaProvider(Provider):
    def __init__(self, base_url: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = Client(host=self.base_url)

    def health(self) -> tuple[bool, str]:
        try:
            response = self.client.ps()
            models = response.get('models', []) if isinstance(response, dict) else getattr(response, 'models', [])
            return True, f'reachable ({len(models)} loaded)'
        except Exception as exc:
            return False, str(exc)

    def generate(self, model: str, prompt: str) -> ProviderResult:
        try:
            response = self._chat_or_generate(model=model, prompt=prompt, stream=False)
            text = _extract_text(response)
            return ProviderResult(
                text=text,
                provider='ollama',
                model=model,
                raw=response if isinstance(response, dict) else None,
            )
        except ProviderError:
            raise
        except Exception as exc:
            raise _map_exception(self.base_url, exc) from exc

    def stream(self, model: str, prompt: str) -> Generator[str, None, None]:
        try:
            stream = self._chat_or_generate(model=model, prompt=prompt, stream=True)
            for chunk in stream:
                token = _extract_text(chunk)
                if token:
                    yield token
        except ProviderError:
            raise
        except Exception as exc:
            raise _map_exception(self.base_url, exc) from exc

    def _chat_or_generate(self, model: str, prompt: str, stream: bool):
        try:
            return self.client.chat(
                model=model,
                messages=[{'role': 'user', 'content': prompt}],
                stream=stream,
            )
        except ResponseError as exc:
            # Older Ollama builds can miss /api/chat while still supporting /api/generate.
            if exc.status_code != 404:
                raise
            return self.client.generate(model=model, prompt=prompt, stream=stream)
