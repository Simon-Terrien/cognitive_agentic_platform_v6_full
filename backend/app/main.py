import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from app.api.routes import auth, chat, health, models, users
from app.core.metrics import metrics_registry
from app.core.middleware import MetricsMiddleware, RequestIDMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level, loki_enabled=settings.loki_enabled)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    loki_task: asyncio.Task | None = None
    if settings.loki_enabled:
        from app.core.loki import get_loki_sink

        loki_task = asyncio.create_task(get_loki_sink().run_forever())
    try:
        yield
    finally:
        if loki_task is not None:
            loki_task.cancel()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=_lifespan)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(MetricsMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r'https?://(localhost|127\.0\.0\.1)(:\d+)?',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(health.router, prefix='/api')
app.include_router(auth.router, prefix='/api')
app.include_router(users.router, prefix='/api')
app.include_router(models.router, prefix='/api')
app.include_router(chat.router, prefix='/api')


@app.api_route('/api/training/{path:path}', methods=['GET', 'POST', 'DELETE'])
async def proxy_training(path: str, request: Request) -> Response:
    url = f'{settings.training_service_url}/api/training/{path}'
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            params=dict(request.query_params),
            content=await request.body(),
            headers={'content-type': request.headers.get('content-type', 'application/json')},
        )
    return Response(content=resp.content, status_code=resp.status_code,
                    media_type=resp.headers.get('content-type'))


@app.get('/metrics')
def metrics() -> PlainTextResponse:
    return PlainTextResponse(metrics_registry.render_prometheus())
