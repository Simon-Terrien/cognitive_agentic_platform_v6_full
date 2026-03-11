from pydantic import BaseModel


class ProviderHealth(BaseModel):
    provider: str
    ok: bool
    detail: str


class ModelCard(BaseModel):
    id: str
    label: str
    provider: str
    family: str
    transport: str
    recommended_for: list[str]
