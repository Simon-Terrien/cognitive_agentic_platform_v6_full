from fastapi import HTTPException

from app.api.routes import models as models_route


def test_models_and_provider_status(monkeypatch):
    monkeypatch.setattr(
        models_route.providers,
        'health_matrix',
        lambda: [
            {'provider': 'mock', 'ok': True, 'detail': 'deterministic-in-process'},
            {'provider': 'ollama', 'ok': True, 'detail': 'reachable'},
            {'provider': 'vllm', 'ok': False, 'detail': 'offline'},
        ],
    )

    payload = models_route.list_models()
    assert isinstance(payload, list)
    ids = {item['id'] for item in payload}
    assert 'mock_static' in ids
    assert 'transformers_qwen3_0_6b' in ids
    assert 'transformers_lfm2_700m' in ids
    assert any(item['provider'] == 'ollama' for item in payload)

    detail = models_route.get_model('ollama_qwen3')
    assert detail['id'] == 'ollama_qwen3'

    try:
        models_route.get_model('does-not-exist')
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError('Expected HTTPException for unknown model id')

    status = models_route.provider_status()
    assert isinstance(status, list)
