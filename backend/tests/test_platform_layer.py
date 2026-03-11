from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import HTTPException

from app.api.routes import auth as auth_routes
from app.api.routes import health
from app.core import auth as auth_core
from app.core.auth import AuthManager, require_user_if_enabled
from app.core.config import reset_settings_cache
from app.core.metrics import metrics_registry
from app.core.platform_store import reset_platform_store
from app.api.routes import chat
from app.schemas.auth import LoginRequest, RegisterRequest


class FakeProvider:
    def generate(self, model: str, prompt: str):
        from app.providers.base import ProviderResult

        return ProviderResult(text=f'generated:{model}', provider='fake', model=model)

    def stream(self, model: str, prompt: str):
        yield 'chunk-1 '
        yield 'chunk-2'


def _reset_auth_env(monkeypatch, tmp_path: Path, auth_required: bool = False) -> AuthManager:
    monkeypatch.setenv('APP_AUTH_STORE_DIR', str(tmp_path / 'auth-store'))
    monkeypatch.setenv('APP_PLATFORM_DB_PATH', str(tmp_path / 'platform' / 'platform.db'))
    monkeypatch.setenv('APP_AUTH_REQUIRED', 'true' if auth_required else 'false')
    monkeypatch.setenv('APP_AUTH_BOOTSTRAP_EMAIL', 'operator@test.local')
    monkeypatch.setenv('APP_AUTH_BOOTSTRAP_PASSWORD', 'operator-demo-pass')
    monkeypatch.setenv('APP_AUTH_SECRET', 'test-secret-value')
    reset_settings_cache()
    reset_platform_store()
    manager = AuthManager()
    monkeypatch.setattr(auth_core, 'auth_manager', manager)
    monkeypatch.setattr(auth_routes, 'auth_manager', manager)
    return manager


def test_auth_register_login_and_me(monkeypatch, tmp_path):
    _reset_auth_env(monkeypatch, tmp_path)

    register_response = auth_routes.register(RegisterRequest(email='demo@example.com', password='demo-pass-123'))
    assert register_response.token_type == 'bearer'
    assert register_response.user['email'] == 'demo@example.com'

    login_response = auth_routes.login(LoginRequest(email='demo@example.com', password='demo-pass-123'))
    token = login_response.access_token
    assert token

    user = auth_core.auth_manager.current_user(f'Bearer {token}')
    me_payload = auth_routes.me(user=user)
    assert me_payload['role'] == 'operator'


def test_chat_requires_auth_when_enabled(monkeypatch, tmp_path):
    _reset_auth_env(monkeypatch, tmp_path, auth_required=True)
    monkeypatch.setattr(chat.engine.providers, 'get', lambda spec: FakeProvider())

    async def _unauthorized_check():
        try:
            await require_user_if_enabled(user=None)
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError('Expected HTTPException for missing auth')

    asyncio.run(_unauthorized_check())

    login_response = auth_routes.login(LoginRequest(email='operator@test.local', password='operator-demo-pass'))
    token = login_response.access_token
    assert token


def test_metrics_and_health_exposure(monkeypatch, tmp_path):
    _reset_auth_env(monkeypatch, tmp_path)

    payload = health.health()
    assert payload['ok'] is True

    metrics_registry.record_auth_attempt('login', 'failure')
    metrics_registry.record_request('GET', '/api/health', 200, 0.01)

    body = metrics_registry.render_prometheus()
    assert 'cap_http_requests_total' in body
    assert 'endpoint="/api/health"' in body
    assert 'cap_auth_attempts_total' in body
    assert 'method="login",outcome="failure"' in body
