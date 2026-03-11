from fastapi import APIRouter, Depends

from app.core.auth import require_user
from app.core.platform_store import get_platform_store
from app.schemas.users import UserPreferenceRead, UserPreferenceUpdate, UserRead

router = APIRouter()


def _user_payload(user) -> UserRead:
    return UserRead(
        id=user.user_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_seen_at=user.last_seen_at,
    )


@router.get('/users/me', response_model=UserRead)
def get_me(user=Depends(require_user)):
    return _user_payload(user)


@router.get('/users/me/preferences', response_model=UserPreferenceRead)
def get_preferences(user=Depends(require_user)):
    pref = get_platform_store().get_preferences(user.user_id)
    return UserPreferenceRead(**pref.__dict__)


@router.patch('/users/me/preferences', response_model=UserPreferenceRead)
def update_preferences(update: UserPreferenceUpdate, user=Depends(require_user)):
    pref = get_platform_store().update_preferences(
        user.user_id,
        selected_model_id=update.selected_model_id if 'selected_model_id' in update.model_fields_set else ...,
        selected_dataset_id=update.selected_dataset_id if 'selected_dataset_id' in update.model_fields_set else ...,
        max_new_tokens=update.max_new_tokens if 'max_new_tokens' in update.model_fields_set else ...,
        blocked_tools=update.blocked_tools if 'blocked_tools' in update.model_fields_set else ...,
    )
    return UserPreferenceRead(**pref.__dict__)
