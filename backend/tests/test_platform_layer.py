from __future__ import annotations
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.core import auth as auth_core
from app.core.auth import AuthManager
from app.core.config import reset_settings_cache
from app.api.routes import auth as auth_routes
from app.api.routes import chat


class FakeProvider:
    def generate(self, model: str, prompt: str):
        from app.providers.base import ProviderResult

        return ProviderResult(text=f'generated:{model}', provider='fake', model=model)

    def stream(self, model: str, prompt: str):
        yield 'chunk-1 '
        yield 'chunk-2'


def _reset_auth_env(monkeypatch, tmp_path: Path, auth_required: bool = False) -> AuthManager:
    monkeypatch.setenv('APP_AUTH_STORE_DIR', str(tmp_path / 'auth-store'))
    monkeypatch.setenv('APP_AUTH_REQUIRED', 'true' if auth_required else 'false')
    monkeypatch.setenv('APP_AUTH_BOOTSTRAP_EMAIL', 'operator@test.local')
    monkeypatch.setenv('APP_AUTH_BOOTSTRAP_PASSWORD', 'operator-demo-pass')
    monkeypatch.setenv('APP_AUTH_SECRET', 'test-secret-value')
    reset_settings_cache()
    manager = AuthManager()
    monkeypatch.setattr(auth_core, 'auth_manager', manager)
    monkeypatch.setattr(auth_routes, 'auth_manager', manager)
    return manager


def test_auth_register_login_and_me(monkeypatch, tmp_path):
    _reset_auth_env(monkeypatch, tmp_path)
    with TestClient(app) as client:
        register_response = client.post(
            '/api/auth/register',
            json={'email': 'demo@example.com', 'password': 'demo-pass-123'},
        )
        assert register_response.status_code == 201
        payload = register_response.json()
        assert payload['token_type'] == 'bearer'
        assert payload['user']['email'] == 'demo@example.com'

        login_response = client.post(
            '/api/auth/login',
            json={'email': 'demo@example.com', 'password': 'demo-pass-123'},
        )
        assert login_response.status_code == 200
        token = login_response.json()['access_token']

        me_response = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
        assert me_response.status_code == 200
        assert me_response.json()['role'] == 'operator'


def test_chat_requires_auth_when_enabled(monkeypatch, tmp_path):
    _reset_auth_env(monkeypatch, tmp_path, auth_required=True)
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())
    with TestClient(app) as client:
        unauthorized = client.post('/api/chat', json={'message': 'say ok', 'model_id': 'mock_static'})
        assert unauthorized.status_code == 401

        login_response = client.post(
            '/api/auth/login',
            json={'email': 'operator@test.local', 'password': 'operator-demo-pass'},
        )
        assert login_response.status_code == 200
        token = login_response.json()['access_token']

        authorized = client.post(
            '/api/chat',
            json={'message': 'say ok', 'model_id': 'mock_static'},
            headers={'Authorization': f'Bearer {token}'},
        )
        assert authorized.status_code == 200


def test_metrics_and_request_id_headers(monkeypatch, tmp_path):
    _reset_auth_env(monkeypatch, tmp_path)
    with TestClient(app) as client:
        response = client.get('/api/health', headers={'X-Request-ID': 'req-123'})
        assert response.status_code == 200
        assert response.headers['X-Request-ID'] == 'req-123'

        client.post('/api/auth/login', json={'email': 'operator@test.local', 'password': 'wrong'})

        metrics = client.get('/metrics')
        assert metrics.status_code == 200
        body = metrics.text
        assert 'cap_http_requests_total' in body
        assert 'endpoint="/api/health"' in body
        assert 'cap_auth_attempts_total' in body
        assert 'method="login",outcome="failure"' in body
