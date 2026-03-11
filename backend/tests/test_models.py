import asyncio

import httpx

from app.main import app
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
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            models_response = await client.get('/api/models')
            assert models_response.status_code == 200
            payload = models_response.json()
            assert isinstance(payload, list)
            ids = {item['id'] for item in payload}
            assert 'mock_static' in ids
            assert 'transformers_qwen3_0_6b' in ids
            assert 'transformers_lfm2_700m' in ids
            assert any(item['provider'] == 'ollama' for item in payload)
            detail = await client.get('/api/models/ollama_qwen3')
            assert detail.status_code == 200
            assert detail.json()['id'] == 'ollama_qwen3'
            missing = await client.get('/api/models/does-not-exist')
            assert missing.status_code == 404
            status = await client.get('/api/providers/status')
            assert status.status_code == 200
            assert isinstance(status.json(), list)

    asyncio.run(run())
