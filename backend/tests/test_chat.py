import httpx
from fastapi import HTTPException

from app.api.routes import chat
from app.providers.base import ProviderResult
from app.providers.ollama import OllamaProvider
from app.schemas.chat import AgentQueryRequest, ChatRequest
from app.models.catalog import get_model_spec


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


def _pin_resolution(monkeypatch, model_id: str) -> None:
    spec = get_model_spec(model_id)
    monkeypatch.setattr(
        chat.engine.router,
        'resolve',
        lambda providers, requested_model_id=None, **kwargs: type(
            'Resolution',
            (),
            {
                'requested_model_id': requested_model_id or model_id,
                'resolved_model': spec,
                'fallback_reason': None,
                'fallback_candidates': [model_id],
                'health_snapshot': [],
                'routing_notes': [],
            },
        )(),
    )


def test_chat_round_trip(monkeypatch):
    _pin_resolution(monkeypatch, 'ollama_qwen3')
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    payload = chat._run_chat('Explain local model routing', 'ollama_qwen3', None)

    assert payload['answer']
    assert payload['model_id'] == 'ollama_qwen3'
    assert payload['traces']
    assert payload['confidence'] > 0


def test_chat_passes_session_key_to_engine(monkeypatch):
    captured: dict[str, str | None] = {}

    def fake_run(query: str, model_id: str | None = None, session_id: str | None = None):
        captured['query'] = query
        captured['model_id'] = model_id
        captured['session_id'] = session_id
        return {
            'answer': 'ok',
            'model_id': model_id or 'mock_static',
            'provider': 'fake',
            'plan_kind': 'analysis',
            'confidence': 0.5,
            'traces': [],
            'requested_model_id': model_id or 'mock_static',
            'resolved_model_id': model_id or 'mock_static',
            'fallback_applied': False,
            'fallback_reason': None,
        }

    monkeypatch.setattr(chat.engine, 'run', fake_run)

    response = chat.chat(ChatRequest(message='Explain local model routing', model_id='ollama_qwen3'), user=None)
    assert response['answer'] == 'ok'
    assert captured['session_id'] == 'anonymous::ollama_qwen3'


def test_agent_query_alias_round_trip(monkeypatch):
    _pin_resolution(monkeypatch, 'ollama_qwen3')
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    payload = chat.agent_query(AgentQueryRequest(query='Explain local model routing', model_id='ollama_qwen3'), user=None)

    assert payload['answer']
    assert payload['model_id'] == 'ollama_qwen3'
    assert payload['traces']
    assert payload['confidence'] > 0


def test_chat_stream_emits_final_event(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    events = list(chat._stream_chat('Explain providers', 'ollama_qwen3', None))

    assert events
    assert any(event.get('kind') == 'final' for event in events)


def test_agent_stream_alias_emits_legacy_result_event(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    events = list(chat._legacy_stream_events('Explain providers', 'ollama_qwen3', None))

    assert events
    assert any(event.get('kind') == 'result' for event in events)


def test_chat_returns_503_when_provider_is_offline(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: OfflineProvider())
    try:
        chat._run_chat('Explain local model routing', 'ollama_qwen3', None)
    except HTTPException as exc:
        assert exc.status_code == 503
        assert 'ollama is unavailable' in str(exc.detail)
    else:
        raise AssertionError('Expected HTTPException')


def test_chat_stream_emits_error_event_when_provider_is_offline(monkeypatch):
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: OfflineProvider())
    events = list(chat._stream_chat('Explain providers', 'ollama_qwen3', None))

    assert any(event.get('kind') == 'error' for event in events)
    assert any('ollama is unavailable' in str(event.get('data', {}).get('detail', '')) for event in events)


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
