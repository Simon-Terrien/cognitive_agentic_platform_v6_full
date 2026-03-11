from dataclasses import asdict, dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class ModelSpec:
    id: str
    label: str
    provider: str
    family: str
    transport: str
    value: str
    recommended_for: list[str]
    fallback_ids: list[str] = ()
    max_context_tokens: int = 8192
    gpu_required: bool = False
    supports_stream: bool = True
    supports_tools: bool = False
    offline_ready: bool = False
    requires_service: bool = True
    priority: int = 100
    degraded_message: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_BASE_MODEL_SPECS = [
    ModelSpec(
        id='mock_static',
        label='Mock / Deterministic',
        provider='mock',
        family='mock',
        transport='in-process',
        value='mock-static',
        recommended_for=['smoke tests', 'benchmarks', 'offline development'],
        fallback_ids=[],
        max_context_tokens=4096,
        offline_ready=True,
        requires_service=False,
        priority=1000,
        degraded_message='Using deterministic mock runtime because no live provider is available.',
    ),
    ModelSpec(
        id='ollama_qwen3',
        label='Ollama / Qwen3',
        provider='ollama',
        family='qwen',
        transport='pydantic-ai',
        value='qwen3:4b',
        recommended_for=['easy local setup', 'chat', 'baseline local serving'],
        fallback_ids=['transformers_qwen3_0_6b', 'mock_static'],
        max_context_tokens=32768,
        offline_ready=False,
        requires_service=True,
        priority=90,
        degraded_message='Ollama is offline. Falling back to a local-safe runtime.',
    ),
    ModelSpec(
        id='vllm_qwen3_8b',
        label='vLLM / Qwen3 8B',
        provider='vllm',
        family='qwen',
        transport='pydantic-ai',
        value='Qwen/Qwen3-8B',
        recommended_for=['gpu serving', 'throughput', 'bigger local model'],
        fallback_ids=['ollama_qwen3', 'transformers_qwen3_0_6b', 'mock_static'],
        max_context_tokens=32768,
        gpu_required=True,
        offline_ready=False,
        requires_service=True,
        priority=70,
        degraded_message='vLLM is offline. Falling back to a smaller local runtime.',
    ),
    ModelSpec(
        id='transformers_qwen3_0_6b',
        label='Transformers / Qwen3 0.6B',
        provider='transformers',
        family='qwen',
        transport='in-process',
        value='Qwen/Qwen3-0.6B',
        recommended_for=['local cpu testing', 'small qwen baseline', 'offline experiments'],
        fallback_ids=['mock_static'],
        max_context_tokens=8192,
        offline_ready=True,
        requires_service=False,
        priority=80,
        degraded_message='Using local Transformers fallback.',
    ),
    ModelSpec(
        id='transformers_lfm2_700m',
        label='Transformers / LFM2 700M',
        provider='transformers',
        family='lfm2',
        transport='in-process',
        value='LiquidAI/LFM2-700M',
        recommended_for=['local cpu testing', 'small liquid model', 'benchmark comparisons'],
        fallback_ids=['mock_static'],
        max_context_tokens=8192,
        offline_ready=True,
        requires_service=False,
        priority=75,
        degraded_message='Using local Transformers fallback.',
    ),
    ModelSpec(
        id='transformers_lfm2_1_2b',
        label='Transformers / LFM2 1.2B',
        provider='transformers',
        family='lfm2',
        transport='in-process',
        value='LiquidAI/LFM2-1.2B',
        recommended_for=['higher quality local runs', 'cpu stress tests', 'quality comparisons'],
        fallback_ids=['transformers_lfm2_700m', 'mock_static'],
        max_context_tokens=8192,
        offline_ready=True,
        requires_service=False,
        priority=78,
        degraded_message='Using local Transformers fallback.',
    ),
    ModelSpec(
        id='vllm_lfm2_700m',
        label='vLLM / LFM2 700M',
        provider='vllm',
        family='lfm2',
        transport='pydantic-ai',
        value='LiquidAI/LFM2-700M',
        recommended_for=['server-backed liquid runs', 'repeatable comparisons', 'lower startup overhead'],
        fallback_ids=['transformers_lfm2_700m', 'mock_static'],
        max_context_tokens=16384,
        gpu_required=True,
        offline_ready=False,
        requires_service=True,
        priority=65,
        degraded_message='vLLM LFM2 is offline. Falling back to a local-safe runtime.',
    ),
    ModelSpec(
        id='llamacpp_local_gguf',
        label='llama.cpp / GGUF',
        provider='llama.cpp',
        family='gguf',
        transport='pydantic-ai',
        value='local-gguf',
        recommended_for=['gguf', 'laptop deployment', 'quantized inference'],
        fallback_ids=['ollama_qwen3', 'mock_static'],
        max_context_tokens=8192,
        offline_ready=False,
        requires_service=True,
        priority=60,
        degraded_message='llama.cpp is offline. Falling back to another local runtime.',
    ),
    ModelSpec(
        id='transformers_tiny_gpt2',
        label='Transformers / Tiny GPT-2',
        provider='transformers',
        family='gpt2',
        transport='in-process',
        value='sshleifer/tiny-gpt2',
        recommended_for=['debugging', 'tiny experiments', 'offline local adapter testing'],
        fallback_ids=['mock_static'],
        max_context_tokens=2048,
        offline_ready=True,
        requires_service=False,
        priority=50,
        degraded_message='Using tiny local debug runtime.',
    ),
]


def list_model_specs() -> list[ModelSpec]:
    settings = get_settings()
    specs = list(_BASE_MODEL_SPECS)
    if settings.openai_model_name:
        specs.append(
            ModelSpec(
                id='openai_default',
                label=f'OpenAI / {settings.openai_model_name}',
                provider='openai',
                family='hosted',
                transport='pydantic-ai',
                value=settings.openai_model_name,
                recommended_for=['managed api', 'hosted inference', 'provider portability'],
                fallback_ids=['transformers_qwen3_0_6b', 'mock_static'],
                max_context_tokens=131072,
                gpu_required=True,
                supports_tools=True,
                offline_ready=False,
                requires_service=True,
                priority=40,
                degraded_message='OpenAI endpoint is unavailable. Falling back locally.',
            )
        )
    if settings.anthropic_model_name:
        specs.append(
            ModelSpec(
                id='anthropic_default',
                label=f'Anthropic / {settings.anthropic_model_name}',
                provider='anthropic',
                family='hosted',
                transport='pydantic-ai',
                value=settings.anthropic_model_name,
                recommended_for=['managed api', 'hosted inference', 'provider portability'],
                fallback_ids=['transformers_qwen3_0_6b', 'mock_static'],
                max_context_tokens=200000,
                gpu_required=True,
                supports_tools=True,
                offline_ready=False,
                requires_service=True,
                priority=40,
                degraded_message='Anthropic endpoint is unavailable. Falling back locally.',
            )
        )
    return specs


def get_model_spec(model_id: str) -> ModelSpec:
    for spec in list_model_specs():
        if spec.id == model_id:
            return spec
    raise KeyError(model_id)
