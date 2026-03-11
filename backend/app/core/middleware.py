from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import metrics_registry


def _normalize_endpoint(path: str) -> str:
    dynamic_prefixes = (
        '/api/models/',
        '/api/training/',
    )
    for prefix in dynamic_prefixes:
        if path.startswith(prefix):
            if prefix == '/api/training/' and path in {'/api/training/status', '/api/training/start', '/api/training/stop', '/api/training/datasets', '/api/training/plan'}:
                return path
            if prefix == '/api/models/' and path != '/api/models':
                return '/api/models/{model_id}'
    return path


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        metrics_registry.record_request(
            request.method,
            _normalize_endpoint(request.url.path),
            response.status_code,
            time.perf_counter() - started,
        )
        return response
