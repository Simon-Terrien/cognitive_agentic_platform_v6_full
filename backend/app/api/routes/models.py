from fastapi import APIRouter, HTTPException

from app.models.catalog import get_model_spec, list_model_specs
from app.providers.manager import ProviderManager

router = APIRouter()
providers = ProviderManager()


@router.get('/models')
def list_models():
    return [spec.to_dict() for spec in list_model_specs()]


@router.get('/models/{model_id}')
def get_model(model_id: str):
    try:
        return get_model_spec(model_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f'Unknown model: {model_id}') from exc


@router.get('/providers/status')
def provider_status():
    return providers.health_matrix()
