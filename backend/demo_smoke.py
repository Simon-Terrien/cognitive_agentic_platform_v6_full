from app.api.routes import chat, health, models, training
from app.core.sse import iter_sse
from app.providers.base import ProviderResult


class FakeProvider:
    def generate(self, model: str, prompt: str) -> ProviderResult:
        return ProviderResult(text=f"generated:{model}", provider="demo", model=model)

    def stream(self, model: str, prompt: str):
        yield "chunk-1 "
        yield "chunk-2"


class FakePlan:
    def __init__(self) -> None:
        self.backend = "unsloth"
        self.dataset_id = "TeichAI/Aurora-Alpha-15.5k"
        self.normalized_rows = 12
        self.command_hint = "python scripts/unsloth_sft_example.py --model-name qwen3:4b"
        self.export_targets = ["gguf", "ollama"]
        self.notes = ["fake plan"]


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    chat.engine.providers.get = lambda spec: FakeProvider()
    models.providers.health_matrix = lambda: [
        {"provider": "ollama", "ok": True, "detail": "demo reachable"},
        {"provider": "vllm", "ok": False, "detail": "demo offline"},
    ]
    training.trainer.plan_training = lambda dataset, model: FakePlan()

    ensure(health.health()["ok"] is True, "health route failed")
    ensure(len(models.list_models()) >= 1, "model catalog is empty")
    ensure(models.get_model("ollama_qwen3")["id"] == "ollama_qwen3", "model detail route failed")
    ensure(len(models.provider_status()) == 2, "provider status route failed")

    chat_payload = chat.chat(chat.ChatRequest(message="demo", model_id="ollama_qwen3"))
    ensure(chat_payload["answer"].startswith("generated:"), "chat route failed")

    chat_stream = "".join(iter_sse(chat._stream_chat("demo", "ollama_qwen3")))
    ensure('"kind": "final"' in chat_stream or '"kind":"final"' in chat_stream, "chat stream route failed")

    alias_payload = chat.agent_query(chat.AgentQueryRequest(query="demo", model_id="ollama_qwen3"))
    ensure(alias_payload["answer"].startswith("generated:"), "agent query alias failed")

    legacy_stream = "".join(iter_sse(chat._legacy_stream_events("demo", "ollama_qwen3")))
    ensure('"kind": "result"' in legacy_stream or '"kind":"result"' in legacy_stream, "agent stream alias failed")

    ensure(training.training_status().running is False, "training status route failed")
    ensure(training.training_start().running is True, "training start route failed")
    ensure(training.training_stop().running is False, "training stop route failed")
    ensure(len(training.training_datasets()) >= 1, "training datasets route failed")
    ensure(len(training.datasets()) >= 1, "datasets alias route failed")

    plan_payload = training.training_plan(model_id="ollama_qwen3", dataset_id=None)
    ensure(plan_payload["backend"] == "unsloth", "training plan route failed")
    ensure(len(plan_payload["export_targets"]) >= 1, "training plan export targets missing")

    print("demo smoke passed")


if __name__ == "__main__":
    main()
