from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    model_id: str | None = None


class AgentQueryRequest(BaseModel):
    query: str = Field(min_length=1)
    model_id: str | None = None


class ChatResponse(BaseModel):
    answer: str
    model_id: str
    provider: str
    plan_kind: str
    confidence: float
    traces: list[dict]
