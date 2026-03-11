import asyncio
import json

from app import main


class FakeTrainingResponse:
    def __init__(self, payload: dict, status_code: int = 200, media_type: str = 'application/json') -> None:
        self.content = json.dumps(payload).encode()
        self.status_code = status_code
        self.headers = {'content-type': media_type}


class FakeAsyncClient:
    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def request(self, method: str, url: str, params: dict | None = None, content: bytes | None = None, headers: dict | None = None):
        self.calls.append({'method': method, 'url': url, 'params': params, 'content': content, 'headers': headers})
        if url.endswith('/status'):
            return FakeTrainingResponse({'running': False, 'idle_seconds': 120, 'last_dataset': None, 'last_result': None})
        return FakeTrainingResponse({'backend': 'unsloth', 'dataset_id': 'demo', 'normalized_rows': 12})


class FakeRequest:
    def __init__(self, method: str, query_params: dict | None = None, body: bytes = b'', headers: dict | None = None) -> None:
        self.method = method
        self.query_params = query_params or {}
        self._body = body
        self.headers = headers or {}

    async def body(self) -> bytes:
        return self._body


def test_training_status_proxy(monkeypatch):
    main.settings.training_service_url = 'http://training.example'
    fake_client = FakeAsyncClient()
    monkeypatch.setattr(main.httpx, 'AsyncClient', lambda timeout=120.0: fake_client)

    async def run():
        request = FakeRequest(method='GET')
        response = await main.proxy_training('status', request)
        assert response.status_code == 200
        assert json.loads(response.body)['idle_seconds'] == 120
        assert fake_client.calls[0]['method'] == 'GET'
        assert fake_client.calls[0]['url'] == 'http://training.example/api/training/status'

    asyncio.run(run())


def test_training_plan_proxy_preserves_query_params(monkeypatch):
    main.settings.training_service_url = 'http://training.example'
    fake_client = FakeAsyncClient()
    monkeypatch.setattr(main.httpx, 'AsyncClient', lambda timeout=120.0: fake_client)

    async def run():
        request = FakeRequest(method='GET', query_params={'model_id': 'ollama_qwen3', 'dataset_id': 'demo'})
        response = await main.proxy_training('plan', request)
        assert response.status_code == 200
        assert json.loads(response.body)['backend'] == 'unsloth'
        assert fake_client.calls[0]['params'] == {'model_id': 'ollama_qwen3', 'dataset_id': 'demo'}
        assert fake_client.calls[0]['url'] == 'http://training.example/api/training/plan'

    asyncio.run(run())
