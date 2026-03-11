from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx


log = logging.getLogger('app.core.loki')


class LokiSink:
    def __init__(self, loki_url: str, labels: dict[str, str] | None = None) -> None:
        self.loki_url = loki_url.rstrip('/')
        self.base_labels = labels or {'app': 'cognitive-agentic-platform'}
        self._queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=10000)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._batch_size = 20
        self._flush_interval = 2.0

    def __call__(self, payload: Any) -> None:
        if self._loop is not None and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._enqueue, payload)
            return
        self._enqueue(payload)

    def _enqueue(self, payload: Any) -> None:
        try:
            self._queue.put_nowait(payload)
        except asyncio.QueueFull:
            log.warning('dropping loki payload because the queue is full')

    async def run_forever(self) -> None:
        self._loop = asyncio.get_running_loop()
        while True:
            batch: list[Any] = []
            deadline = self._loop.time() + self._flush_interval
            while len(batch) < self._batch_size:
                remaining = deadline - self._loop.time()
                if remaining <= 0:
                    break
                try:
                    item = await asyncio.wait_for(self._queue.get(), timeout=remaining)
                except asyncio.TimeoutError:
                    break
                batch.append(item)
            if batch:
                await self._push_batch(batch)

    async def _push_batch(self, batch: list[Any]) -> None:
        streams = []
        for item in batch:
            if isinstance(item, dict):
                labels = dict(self.base_labels)
                labels['event'] = str(item.get('event', 'log'))[:32]
                level = item.get('level')
                if level:
                    labels['level'] = str(level).lower()[:16]
                stream_line = json.dumps(item, default=str)
            else:
                labels = dict(self.base_labels)
                labels['event'] = 'log'
                stream_line = str(item)
            streams.append(
                {
                    'stream': labels,
                    'values': [[str(int(time.time() * 1e9)), stream_line]],
                }
            )
        payload = {'streams': streams}
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(f'{self.loki_url}/loki/api/v1/push', json=payload)
                response.raise_for_status()
        except Exception as exc:
            log.debug('loki push failed: %s', exc)


class LokiLogHandler(logging.Handler):
    def __init__(self, sink: LokiSink) -> None:
        super().__init__()
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._sink(
                {
                    'event': 'log',
                    'logger': record.name,
                    'level': record.levelname,
                    'message': record.getMessage(),
                }
            )
        except Exception:
            log.debug('failed to enqueue log record for loki', exc_info=True)


_sink: LokiSink | None = None


def get_loki_sink() -> LokiSink:
    global _sink
    if _sink is None:
        from app.core.config import get_settings

        settings = get_settings()
        _sink = LokiSink(
            loki_url=settings.loki_url,
            labels={
                'app': 'cognitive-agentic-platform',
                'env': settings.environment,
            },
        )
    return _sink
