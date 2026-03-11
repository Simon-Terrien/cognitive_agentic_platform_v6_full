from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.agent.engine import AgentEngine
from app.core.auth import require_user_if_enabled
from app.core.platform_store import get_platform_store
from app.core.sse import iter_sse
from app.providers.base import ProviderError
from app.schemas.chat import AgentQueryRequest, ChatRequest

router = APIRouter()
engine = AgentEngine()


def _preferred_model(user):
    if user is None:
        return None
    return get_platform_store().get_preferences(user.user_id).selected_model_id


def _run_chat(message: str, model_id: str | None, preferred_model_id: str | None):
    try:
        return engine.run(message, model_id)
    except ProviderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                'detail': exc.detail,
                'provider': exc.provider,
                'requested_model_id': model_id or preferred_model_id,
                'action': 'Start the provider or switch to a fallback such as Mock / Deterministic.',
            },
        ) from exc


def _stream_chat(message: str, model_id: str | None, preferred_model_id: str | None):
    try:
        yield from engine.run_stream(message, model_id)
    except ProviderError as exc:
        yield {
            'kind': 'error',
            'message': 'provider unavailable',
            'data': {
                'detail': exc.detail,
                'status_code': exc.status_code,
                'provider': exc.provider,
                'requested_model_id': model_id or preferred_model_id,
                'action': 'Start the provider or switch to a fallback such as Mock / Deterministic.',
            },
        }


@router.post('/chat')
def chat(req: ChatRequest, user=Depends(require_user_if_enabled)):
    return _run_chat(req.message, req.model_id, _preferred_model(user))


@router.get('/chat/stream')
def chat_stream(message: str = Query(..., min_length=1), model_id: str | None = None, user=Depends(require_user_if_enabled)):
    stream = iter_sse(_stream_chat(message, model_id, _preferred_model(user)))
    return StreamingResponse(stream, media_type='text/event-stream')


@router.post('/agent/query')
def agent_query(req: AgentQueryRequest, user=Depends(require_user_if_enabled)):
    return _run_chat(req.query, req.model_id, _preferred_model(user))


def _legacy_stream_events(query: str, model_id: str | None, preferred_model_id):
    for event in _stream_chat(query, model_id, preferred_model_id):
        if event.get('kind') == 'final':
            data = event.get('data', {})
            yield {
                'kind': 'result',
                'message': 'final answer',
                'data': {
                    'answer': data.get('answer'),
                    'plan_kind': data.get('plan_kind'),
                    'model_id': data.get('model_id'),
                    'confidence': data.get('confidence'),
                },
            }
        else:
            yield event


@router.get('/agent/stream')
def agent_stream(query: str = Query(..., min_length=1), model_id: str | None = None, user=Depends(require_user_if_enabled)):
    stream = iter_sse(_legacy_stream_events(query, model_id, _preferred_model(user)))
    return StreamingResponse(stream, media_type='text/event-stream')
