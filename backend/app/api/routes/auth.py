import secrets

from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import auth_manager, record_auth, require_user
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest

router = APIRouter()


def _user_payload(user) -> dict:
    return {
        'id': user.user_id,
        'email': user.email,
        'role': user.role,
        'is_active': user.is_active,
        'created_at': user.created_at,
        'last_seen_at': user.last_seen_at,
    }


@router.post('/auth/register', response_model=AuthResponse, status_code=201)
def register(req: RegisterRequest):
    try:
        user = auth_manager.create_user(req.email, req.password, role='operator')
    except ValueError as exc:
        record_auth('register', 'duplicate')
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_auth('register', 'success')
    return AuthResponse(access_token=auth_manager.issue_token(user), user=_user_payload(user))


@router.post('/auth/login', response_model=AuthResponse)
def login(req: LoginRequest):
    user = auth_manager.authenticate(req.email, req.password)
    if user is None:
        record_auth('login', 'failure')
        raise HTTPException(status_code=401, detail='Invalid credentials')
    record_auth('login', 'success')
    return AuthResponse(access_token=auth_manager.issue_token(user), user=_user_payload(user))


@router.get('/auth/me')
def me(user=Depends(require_user)):
    return _user_payload(user)
