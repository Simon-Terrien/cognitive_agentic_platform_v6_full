from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings
from app.core.metrics import metrics_registry
from app.core.platform_store import UserRecord, get_platform_store


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(data: str) -> bytes:
    padding = '=' * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuthManager:
    def __init__(self) -> None:
        self._store = get_platform_store()
        self._bootstrap_default_user()

    def _bootstrap_default_user(self) -> None:
        settings = get_settings()
        if not settings.auth_bootstrap_email or not settings.auth_bootstrap_password:
            return
        existing = self._store.get_user_by_email(settings.auth_bootstrap_email)
        if existing is None:
            password_hash = self.hash_password(settings.auth_bootstrap_password)
            self._store.create_user(
                user_id=secrets.token_hex(16),
                email=settings.auth_bootstrap_email,
                password_hash=password_hash,
                role=settings.auth_bootstrap_role,
            )

    @property
    def store(self) -> UserStore:
        return self._store

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 120000)
        return f'{_b64url_encode(salt)}.{_b64url_encode(digest)}'

    @staticmethod
    def verify_password(password: str, encoded: str) -> bool:
        try:
            salt_b64, digest_b64 = encoded.split('.', 1)
            salt = _b64url_decode(salt_b64)
            expected = _b64url_decode(digest_b64)
        except Exception:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 120000)
        return hmac.compare_digest(actual, expected)

    def issue_token(self, user: UserRecord) -> str:
        settings = get_settings()
        header = {'alg': 'HS256', 'typ': 'JWT'}
        payload = {
            'sub': user.user_id,
            'email': user.email,
            'role': user.role,
            'exp': int((_utcnow() + timedelta(minutes=settings.auth_access_token_expire_minutes)).timestamp()),
        }
        header_part = _b64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
        payload_part = _b64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
        signature = hmac.new(
            settings.auth_secret.encode('utf-8'),
            f'{header_part}.{payload_part}'.encode('utf-8'),
            hashlib.sha256,
        ).digest()
        return f'{header_part}.{payload_part}.{_b64url_encode(signature)}'

    def authenticate(self, email: str, password: str) -> UserRecord | None:
        user = self._store.get_user_by_email(email)
        if user is None or not self.verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        self._store.touch_user(user.user_id)
        user = self._store.get_user_by_id(user.user_id) or user
        return user

    def create_user(self, email: str, password: str, role: str = 'operator') -> UserRecord:
        password_hash = self.hash_password(password)
        return self._store.create_user(email=email, password_hash=password_hash, role=role)

    def decode_token(self, token: str) -> dict[str, Any]:
        settings = get_settings()
        try:
            header_part, payload_part, signature_part = token.split('.')
        except ValueError as exc:
            raise ValueError('Malformed bearer token') from exc
        expected = hmac.new(
            settings.auth_secret.encode('utf-8'),
            f'{header_part}.{payload_part}'.encode('utf-8'),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(expected, _b64url_decode(signature_part)):
            raise ValueError('Invalid bearer token')
        payload = json.loads(_b64url_decode(payload_part))
        if int(payload.get('exp', 0)) < int(_utcnow().timestamp()):
            raise ValueError('Bearer token expired')
        return payload

    def current_user(self, authorization: str | None) -> UserRecord | None:
        if not authorization:
            return None
        scheme, _, token = authorization.partition(' ')
        if scheme.lower() != 'bearer' or not token:
            raise ValueError('Expected Bearer token')
        payload = self.decode_token(token)
        user = self._store.get_user_by_id(str(payload['sub']))
        if user is None:
            raise ValueError('User not found')
        if not user.is_active:
            raise ValueError('User is inactive')
        return user


auth_manager = AuthManager()


async def get_optional_user(authorization: str | None = Header(default=None)) -> UserRecord | None:
    if not authorization:
        return None
    try:
        return auth_manager.current_user(authorization)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


async def require_user(
    authorization: str | None = Header(default=None),
) -> UserRecord:
    user = await get_optional_user(authorization)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing bearer token')
    return user


async def require_user_if_enabled(user: UserRecord | None = Depends(get_optional_user)) -> UserRecord | None:
    settings = get_settings()
    if settings.auth_required and user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Authentication required')
    return user


def record_auth(method: str, outcome: str) -> None:
    metrics_registry.record_auth_attempt(method, outcome)
