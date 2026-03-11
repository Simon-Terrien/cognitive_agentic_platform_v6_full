from pydantic import BaseModel


class TrainingStatusResponse(BaseModel):
    running: bool
    idle_seconds: int
    last_dataset: str | None = None
    last_result: str | None = None


class TrainingPlanResponse(BaseModel):
    backend: str
    dataset_id: str
    normalized_rows: int
    command_hint: str
    export_targets: list[str]
    notes: list[str]
