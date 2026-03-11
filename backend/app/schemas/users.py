from pydantic import BaseModel


class UserRead(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    created_at: str
    last_seen_at: str | None


class UserPreferenceRead(BaseModel):
    selected_model_id: str | None
    selected_dataset_id: str | None
    max_new_tokens: int | None
    blocked_tools: list[str]
    updated_at: str


class UserPreferenceUpdate(BaseModel):
    selected_model_id: str | None = None
    selected_dataset_id: str | None = None
    max_new_tokens: int | None = None
    blocked_tools: list[str] | None = None
