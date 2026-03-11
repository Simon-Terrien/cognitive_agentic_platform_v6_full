from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get('/health')
def health():
    settings = get_settings()
    return {
        'ok': True,
        'auth_required': settings.auth_required,
        'default_model_id': settings.default_model_id,
    }
