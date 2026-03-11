from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
import secrets
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.core.config import get_settings


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    email: str
    password_hash: str
    role: str
    is_active: bool
    created_at: str
    last_seen_at: str | None


@dataclass(frozen=True)
class UserPreferenceRecord:
    user_id: str
    selected_model_id: str | None
    selected_dataset_id: str | None
    max_new_tokens: int | None
    blocked_tools: list[str]
    updated_at: str


class PlatformStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.executescript(
                    '''
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        email TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        role TEXT NOT NULL,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL,
                        last_seen_at TEXT
                    );

                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                        selected_model_id TEXT,
                        selected_dataset_id TEXT,
                        max_new_tokens INTEGER,
                        blocked_tools TEXT NOT NULL DEFAULT '[]',
                        updated_at TEXT NOT NULL
                    );
                    '''
                )
                conn.commit()
            finally:
                conn.close()

    def list_users(self) -> list[UserRecord]:
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    'SELECT id, email, password_hash, role, is_active, created_at, last_seen_at FROM users ORDER BY created_at ASC'
                ).fetchall()
                return [self._row_to_user(row) for row in rows]
            finally:
                conn.close()

    def get_user_by_email(self, email: str) -> UserRecord | None:
        normalized = email.strip().lower()
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    'SELECT id, email, password_hash, role, is_active, created_at, last_seen_at FROM users WHERE email = ?',
                    (normalized,),
                ).fetchone()
                return self._row_to_user(row) if row else None
            finally:
                conn.close()

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    'SELECT id, email, password_hash, role, is_active, created_at, last_seen_at FROM users WHERE id = ?',
                    (user_id,),
                ).fetchone()
                return self._row_to_user(row) if row else None
            finally:
                conn.close()

    def create_user(self, email: str, password_hash: str, role: str, user_id: str | None = None) -> UserRecord:
        normalized = email.strip().lower()
        created_at = _utcnow_iso()
        resolved_user_id = user_id or secrets.token_hex(16)
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    '''
                    INSERT INTO users (id, email, password_hash, role, is_active, created_at, last_seen_at)
                    VALUES (?, ?, ?, ?, 1, ?, NULL)
                    ''',
                    (resolved_user_id, normalized, password_hash, role, created_at),
                )
                conn.execute(
                    '''
                    INSERT OR IGNORE INTO user_preferences
                    (user_id, selected_model_id, selected_dataset_id, max_new_tokens, blocked_tools, updated_at)
                    VALUES (?, NULL, NULL, NULL, '[]', ?)
                    ''',
                    (resolved_user_id, created_at),
                )
                conn.commit()
            except sqlite3.IntegrityError as exc:
                raise ValueError('Email already registered') from exc
            finally:
                conn.close()
        user = self.get_user_by_id(resolved_user_id)
        if user is None:
            raise RuntimeError('Failed to create user record')
        return user

    def touch_user(self, user_id: str) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute('UPDATE users SET last_seen_at = ? WHERE id = ?', (_utcnow_iso(), user_id))
                conn.commit()
            finally:
                conn.close()

    def get_preferences(self, user_id: str) -> UserPreferenceRecord:
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    '''
                    SELECT user_id, selected_model_id, selected_dataset_id, max_new_tokens, blocked_tools, updated_at
                    FROM user_preferences WHERE user_id = ?
                    ''',
                    (user_id,),
                ).fetchone()
                if row is None:
                    now = _utcnow_iso()
                    conn.execute(
                        '''
                        INSERT INTO user_preferences
                        (user_id, selected_model_id, selected_dataset_id, max_new_tokens, blocked_tools, updated_at)
                        VALUES (?, NULL, NULL, NULL, '[]', ?)
                        ''',
                        (user_id, now),
                    )
                    conn.commit()
                    row = conn.execute(
                        '''
                        SELECT user_id, selected_model_id, selected_dataset_id, max_new_tokens, blocked_tools, updated_at
                        FROM user_preferences WHERE user_id = ?
                        ''',
                        (user_id,),
                    ).fetchone()
                return self._row_to_preference(row)
            finally:
                conn.close()

    def update_preferences(
        self,
        user_id: str,
        *,
        selected_model_id: str | None | object = ...,
        selected_dataset_id: str | None | object = ...,
        max_new_tokens: int | None | object = ...,
        blocked_tools: list[str] | None | object = ...,
    ) -> UserPreferenceRecord:
        current = self.get_preferences(user_id)
        next_values = {
            'selected_model_id': current.selected_model_id if selected_model_id is ... else selected_model_id,
            'selected_dataset_id': current.selected_dataset_id if selected_dataset_id is ... else selected_dataset_id,
            'max_new_tokens': current.max_new_tokens if max_new_tokens is ... else max_new_tokens,
            'blocked_tools': current.blocked_tools if blocked_tools is ... else (blocked_tools or []),
            'updated_at': _utcnow_iso(),
        }
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    '''
                    UPDATE user_preferences
                    SET selected_model_id = ?, selected_dataset_id = ?, max_new_tokens = ?, blocked_tools = ?, updated_at = ?
                    WHERE user_id = ?
                    ''',
                    (
                        next_values['selected_model_id'],
                        next_values['selected_dataset_id'],
                        next_values['max_new_tokens'],
                        json.dumps(next_values['blocked_tools']),
                        next_values['updated_at'],
                        user_id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()
        return self.get_preferences(user_id)

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> UserRecord:
        return UserRecord(
            user_id=row['id'],
            email=row['email'],
            password_hash=row['password_hash'],
            role=row['role'],
            is_active=bool(row['is_active']),
            created_at=row['created_at'],
            last_seen_at=row['last_seen_at'],
        )

    @staticmethod
    def _row_to_preference(row: sqlite3.Row) -> UserPreferenceRecord:
        return UserPreferenceRecord(
            user_id=row['user_id'],
            selected_model_id=row['selected_model_id'],
            selected_dataset_id=row['selected_dataset_id'],
            max_new_tokens=row['max_new_tokens'],
            blocked_tools=json.loads(row['blocked_tools'] or '[]'),
            updated_at=row['updated_at'],
        )


_platform_store: PlatformStore | None = None


def get_platform_store() -> PlatformStore:
    global _platform_store
    if _platform_store is None:
        _platform_store = PlatformStore(get_settings().platform_db_path)
    return _platform_store


def reset_platform_store() -> None:
    global _platform_store
    _platform_store = None
