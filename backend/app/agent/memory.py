from __future__ import annotations

import math
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from app.core.config import get_settings


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tokenize(text: str) -> set[str]:
    return {item for item in re.findall(r'[a-z0-9]+', text.lower()) if len(item) > 1}


def _overlap_score(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    intersection = len(ta.intersection(tb))
    union = len(ta.union(tb))
    if union == 0:
        return 0.0
    return intersection / union


@dataclass
class CognitiveState:
    goal: str
    notes: list[str] = field(default_factory=list)
    answer: str | None = None
    confidence: float = 0.0

    def remember(self, note: str) -> None:
        self.notes.append(note)


@dataclass(frozen=True)
class RetrievedMemory:
    memory_id: int
    goal: str
    note: str
    importance: float
    created_at: str
    score: float
    score_components: dict[str, float]


class MemoryStore:
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
                    CREATE TABLE IF NOT EXISTS agent_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        goal TEXT NOT NULL,
                        note TEXT NOT NULL,
                        importance REAL NOT NULL DEFAULT 0.5,
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_agent_memory_session ON agent_memory(session_id, created_at DESC);
                    CREATE INDEX IF NOT EXISTS idx_agent_memory_goal ON agent_memory(goal);
                    '''
                )
                conn.commit()
            finally:
                conn.close()

    def append(self, session_id: str, goal: str, note: str, importance: float = 0.5) -> None:
        bounded_importance = max(0.0, min(1.0, importance))
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    '''
                    INSERT INTO agent_memory (session_id, goal, note, importance, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (session_id, goal, note, bounded_importance, _utcnow_iso()),
                )
                conn.commit()
            finally:
                conn.close()

    def retrieve(self, session_id: str, goal: str, query: str, top_k: int | None = None) -> list[RetrievedMemory]:
        settings = get_settings()
        limit = top_k or settings.agent_memory_top_k
        if limit <= 0:
            return []
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    '''
                    SELECT id, goal, note, importance, created_at
                    FROM agent_memory
                    WHERE session_id = ? OR goal = ?
                    ORDER BY created_at DESC
                    LIMIT 300
                    ''',
                    (session_id, goal),
                ).fetchall()
            finally:
                conn.close()

        now = datetime.now(timezone.utc)
        weighted: list[RetrievedMemory] = []
        for row in rows:
            try:
                created_at_dt = datetime.fromisoformat(row['created_at'])
            except ValueError:
                created_at_dt = now
            age_hours = max(0.0, (now - created_at_dt).total_seconds() / 3600.0)
            recency_score = math.exp(-age_hours / 24.0)
            semantic_score = _overlap_score(query, f"{row['goal']} {row['note']}")
            conversation_score = _overlap_score(goal, row['goal'])
            importance_score = max(0.0, min(1.0, float(row['importance'])))
            final_score = (
                settings.agent_memory_semantic_weight * semantic_score
                + settings.agent_memory_recency_weight * recency_score
                + settings.agent_memory_importance_weight * importance_score
                + settings.agent_memory_conversation_weight * conversation_score
            )
            weighted.append(
                RetrievedMemory(
                    memory_id=int(row['id']),
                    goal=row['goal'],
                    note=row['note'],
                    importance=importance_score,
                    created_at=row['created_at'],
                    score=final_score,
                    score_components={
                        'semantic': semantic_score,
                        'recency': recency_score,
                        'importance': importance_score,
                        'conversation': conversation_score,
                    },
                )
            )
        weighted.sort(key=lambda item: item.score, reverse=True)
        return weighted[:limit]


_memory_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore(get_settings().agent_memory_db_path)
    return _memory_store


def reset_memory_store() -> None:
    global _memory_store
    _memory_store = None
