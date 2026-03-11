from app.models.router import ModelRouter


class FakeProviders:
    def __init__(self, snapshot: list[dict]) -> None:
        self._snapshot = snapshot

    def health_snapshot(self) -> list[dict]:
        return list(self._snapshot)


def test_router_falls_back_when_requested_provider_is_unhealthy():
    router = ModelRouter()
    providers = FakeProviders(
        [
            {'provider': 'ollama', 'ok': False, 'detail': 'connection refused', 'latency_ms': 1.1},
            {'provider': 'transformers', 'ok': True, 'detail': 'ready', 'latency_ms': 12.0},
            {'provider': 'mock', 'ok': True, 'detail': 'ready', 'latency_ms': 0.1},
        ]
    )

    resolution = router.resolve(providers, requested_model_id='ollama_qwen3', query='Explain local model routing.')

    assert resolution.requested_model_id == 'ollama_qwen3'
    assert resolution.resolved_model.id == 'transformers_qwen3_0_6b'
    assert resolution.fallback_reason is not None
    assert resolution.routing_notes


def test_router_uses_context_constraints_to_pick_compatible_fallback():
    router = ModelRouter()
    providers = FakeProviders(
        [
            {'provider': 'transformers', 'ok': True, 'detail': 'ready', 'latency_ms': 5.0},
            {'provider': 'mock', 'ok': True, 'detail': 'ready', 'latency_ms': 0.2},
        ]
    )

    very_long_query = 'x' * 10000
    resolution = router.resolve(providers, requested_model_id='transformers_tiny_gpt2', query=very_long_query)

    assert resolution.requested_model_id == 'transformers_tiny_gpt2'
    assert resolution.resolved_model.id == 'mock_static'
    assert resolution.fallback_reason is not None
