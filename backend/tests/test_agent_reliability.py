from __future__ import annotations

from types import SimpleNamespace

from app.agent.engine import AgentEngine
from app.agent.memory import get_memory_store, reset_memory_store
from app.core import config
from app.models.catalog import get_model_spec
from app.providers.base import ProviderResult


class FakeProvider:
    def generate(self, model: str, prompt: str) -> ProviderResult:
        return ProviderResult(text=f'generated output for {model}', provider='fake', model=model)

    def stream(self, model: str, prompt: str):
        yield 'generated '
        yield 'stream'


def _build_engine_with_fake_resolution() -> AgentEngine:
    engine = AgentEngine()
    spec = get_model_spec('mock_static')
    engine.router.resolve = lambda providers, model_id, **kwargs: SimpleNamespace(
        requested_model_id=model_id or spec.id,
        resolved_model=spec,
        fallback_reason=None,
        fallback_candidates=[spec.id],
        health_snapshot=[],
        routing_notes=[],
    )
    engine.providers.get = lambda _: FakeProvider()
    return engine


def test_memory_persistence_and_ranked_retrieval(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_AGENT_MEMORY_DB_PATH', str(tmp_path / 'agent-memory.db'))
    config.reset_settings_cache()
    reset_memory_store()

    store = get_memory_store()
    store.append(session_id='session-a', goal='debug python error', note='tool=reasoning step for python traceback', importance=0.9)
    store.append(session_id='session-a', goal='debug python error', note='tool=benchmark step for gpu latency', importance=0.2)

    retrieved = store.retrieve(session_id='session-a', goal='debug python error', query='python traceback fix', top_k=2)

    assert len(retrieved) == 2
    assert retrieved[0].note.startswith('tool=reasoning')
    assert retrieved[0].score >= retrieved[1].score


def test_tool_policy_blocks_dangerous_pattern(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_AGENT_MEMORY_DB_PATH', str(tmp_path / 'agent-memory.db'))
    monkeypatch.setenv('APP_AGENT_BLOCK_PATTERNS', 'delete memory')
    config.reset_settings_cache()
    reset_memory_store()

    engine = _build_engine_with_fake_resolution()
    payload = engine.run('Please delete memory now', model_id='mock_static')

    audit_events = [t for t in payload['traces'] if t.get('kind') == 'audit']
    assert audit_events
    assert any(event['data']['allowed'] is False for event in audit_events)
    assert any('blocked_pattern' in event['data']['reason'] for event in audit_events)


def test_governor_limits_iterations(monkeypatch, tmp_path):
    monkeypatch.setenv('APP_AGENT_MEMORY_DB_PATH', str(tmp_path / 'agent-memory.db'))
    monkeypatch.setenv('APP_AGENT_MAX_ITERATIONS', '1')
    config.reset_settings_cache()
    reset_memory_store()

    engine = _build_engine_with_fake_resolution()
    payload = engine.run('Explain local model routing', model_id='mock_static')

    governor_events = [t for t in payload['traces'] if t.get('kind') == 'governor']
    assert governor_events
    assert any(event['data']['reason'] == 'max_iterations_reached' for event in governor_events)
    assert payload['governance']['usage']['iterations'] == 1
