import asyncio

import httpx

from app.main import app
from app.providers.base import ProviderResult
from app.providers.ollama import OllamaProvider
from app.api.routes import chat


class FakeProvider:
    def generate(self, model: str, prompt: str) -> ProviderResult:
        return ProviderResult(text=f'generated:{model}', provider='fake', model=model)

    def stream(self, model: str, prompt: str):
        yield 'chunk-1 '
        yield 'chunk-2'


class OfflineProvider:
    def generate(self, model: str, prompt: str) -> ProviderResult:
        raise chat.ProviderError('ollama', 'ollama is unavailable at http://localhost:11434. Start the service or update the provider URL.', status_code=503)

    def stream(self, model: str, prompt: str):
        raise chat.ProviderError('ollama', 'ollama is unavailable at http://localhost:11434. Start the service or update the provider URL.', status_code=503)
        yield


def test_chat_round_trip(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            response = await client.post('/api/chat', json={'message': 'Explain local model routing', 'model_id': 'ollama_qwen3'})
        assert response.status_code == 200
        payload = response.json()
        assert payload['answer']
        assert payload['model_id'] == 'ollama_qwen3'
        assert payload['traces']
        assert payload['confidence'] > 0

    asyncio.run(run())


def test_agent_query_alias_round_trip(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            response = await client.post('/api/agent/query', json={'query': 'Explain local model routing', 'model_id': 'ollama_qwen3'})
        assert response.status_code == 200
        payload = response.json()
        assert payload['answer']
        assert payload['model_id'] == 'ollama_qwen3'
        assert payload['traces']
        assert payload['confidence'] > 0

    asyncio.run(run())


def test_chat_stream_emits_final_event(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            response = await client.get('/api/chat/stream?message=Explain%20providers&model_id=ollama_qwen3')
        assert response.status_code == 200
        body = response.text
        assert 'data:' in body
        assert '"kind": "final"' in body or '"kind":"final"' in body

    asyncio.run(run())


def test_agent_stream_alias_emits_legacy_result_event(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            response = await client.get('/api/agent/stream?query=Explain%20providers&model_id=ollama_qwen3')
        assert response.status_code == 200
        body = response.text
        assert 'data:' in body
        assert '"kind": "result"' in body or '"kind":"result"' in body

    asyncio.run(run())


def test_chat_returns_503_when_provider_is_offline(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: OfflineProvider())
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            response = await client.post('/api/chat', json={'message': 'Explain local model routing', 'model_id': 'ollama_qwen3'})
        assert response.status_code == 503
        assert 'ollama is unavailable' in response.json()['detail']

    asyncio.run(run())


def test_chat_stream_emits_error_event_when_provider_is_offline(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: OfflineProvider())
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            response = await client.get('/api/chat/stream?message=Explain%20providers&model_id=ollama_qwen3')
        assert response.status_code == 200
        body = response.text
        assert '"kind": "error"' in body or '"kind":"error"' in body
        assert 'ollama is unavailable' in body

    asyncio.run(run())


def test_ollama_generate_maps_connect_errors_to_provider_error(monkeypatch):
    provider = OllamaProvider('http://localhost:11434')
    class BrokenClient:
        def chat(self, **kwargs):
            raise httpx.ConnectError('Connection refused')

    monkeypatch.setattr(provider, 'client', BrokenClient())

    try:
        provider.generate('qwen3', 'hello')
    except chat.ProviderError as exc:
        assert exc.status_code == 503
        assert exc.provider == 'ollama'
        assert 'http://localhost:11434' in exc.detail
    else:
        raise AssertionError('Expected ProviderError')
