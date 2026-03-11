from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class DatasetSpec:
    id: str
    purpose: str
    source: str
    format_hint: str
    recommended_for: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


_DATASETS = [
    DatasetSpec(
        id='TeichAI/Aurora-Alpha-15.5k',
        purpose='reasoning SFT / distillation',
        source='huggingface',
        format_hint='prompt/reasoning/answer conversational traces',
        recommended_for=['reasoning student', 'idle fine-tuning', 'benchmark seed'],
    ),
    DatasetSpec(
        id='TeichAI/Pony-Alpha-15k',
        purpose='reasoning SFT / small-model experiments',
        source='huggingface',
        format_hint='chat-like JSON/text',
        recommended_for=['small students', 'prompt normalization'],
    ),
    DatasetSpec(
        id='TeichAI/claude-4.5-opus-high-reasoning-250x',
        purpose='high-signal reasoning distillation',
        source='huggingface',
        format_hint='compact reasoning set',
        recommended_for=['teacher-student distillation', 'verifier experiments'],
    ),
]


def list_dataset_specs() -> list[DatasetSpec]:
    return _DATASETS


def get_dataset_spec(dataset_id: str) -> DatasetSpec:
    for spec in _DATASETS:
        if spec.id == dataset_id:
            return spec
    raise KeyError(dataset_id)


def get_default_dataset() -> DatasetSpec:
    return _DATASETS[0]
