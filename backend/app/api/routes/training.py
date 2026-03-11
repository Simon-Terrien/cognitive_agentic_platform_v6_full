from fastapi import APIRouter, Depends, Query

from app.core.auth import require_user_if_enabled
from app.core.config import get_settings
from app.models.catalog import get_model_spec
from app.core.platform_store import get_platform_store
from app.training.registry import get_default_dataset, get_dataset_spec, list_dataset_specs
from app.training.scheduler import TrainingScheduler
from app.training.trainer import Trainer

router = APIRouter()
settings = get_settings()
scheduler = TrainingScheduler(idle_seconds=settings.idle_training_seconds, default_model_id=settings.default_model_id)
trainer = Trainer()


@router.get('/training/status')
def training_status():
    return scheduler.status()


@router.post('/training/start')
def training_start(_user=Depends(require_user_if_enabled)):
    scheduler.start()
    return scheduler.status()


@router.post('/training/stop')
def training_stop(_user=Depends(require_user_if_enabled)):
    scheduler.stop()
    return scheduler.status()


@router.get('/training/datasets')
def training_datasets():
    return [spec.to_dict() for spec in list_dataset_specs()]


@router.get('/datasets')
def datasets():
    return [spec.to_dict() for spec in list_dataset_specs()]


@router.get('/training/plan')
def training_plan(dataset_id: str | None = Query(default=None), model_id: str | None = Query(default=None), _user=Depends(require_user_if_enabled)):
    pref = get_platform_store().get_preferences(_user.user_id) if _user else None
    dataset = get_dataset_spec(dataset_id or (pref.selected_dataset_id if pref else None)) if (dataset_id or (pref.selected_dataset_id if pref else None)) else get_default_dataset()
    model_choice = model_id or (pref.selected_model_id if pref else None) or settings.default_model_id
    model = get_model_spec(model_choice)
    plan = trainer.plan_training(dataset, model)
    payload = plan.__dict__
    payload['requested_model_id'] = model_choice
    payload['requested_dataset_id'] = dataset.id
    return payload
