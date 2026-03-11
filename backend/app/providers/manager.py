import logging
import time
from typing import Iterable
import inspect

from app.core.config import get_settings
from app.models.catalog import ModelSpec, get_model_spec
from app.providers.base import Provider
from app.providers.mock import MockProvider
from app.providers.pydantic_adapter import NamedPydanticAIProvider
from app.providers.pydantic_adapter import env_api_key
from app.providers.ollama import OllamaProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.providers.transformers_local import TransformersLocalProvider

logger = logging.getLogger(__name__)


class ProviderManager:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.providers: dict[str, Provider] = {
            'mock': MockProvider(delay_ms=settings.mock_delay_ms),
            'ollama': OllamaProvider(settings.ollama_base_url),
            'vllm': OpenAICompatibleProvider(settings.vllm_base_url, 'vllm', api_key=settings.vllm_api_key),
            'llama.cpp': OpenAICompatibleProvider(settings.llamacpp_base_url, 'llama.cpp', api_key=settings.llamacpp_api_key),
        }
        self._health_snapshot_cache: list[dict] | None = None
        self._health_snapshot_at = 0.0
        try:
            transformers_provider = TransformersLocalProvider(
                device=settings.transformers_device,
                max_new_tokens=settings.transformers_max_new_tokens,
            )
        except RuntimeError as exc:
            logging.getLogger(__name__).warning('Transformers provider unavailable: %s', exc)
        else:
            self.providers['transformers'] = transformers_provider
        if settings.openai_model_name:
            self.providers['openai'] = NamedPydanticAIProvider(
                provider_name='openai',
                model_prefix='openai',
                api_key=env_api_key('APP_OPENAI_API_KEY', 'OPENAI_API_KEY'),
                missing_key_hint='missing APP_OPENAI_API_KEY or OPENAI_API_KEY',
            )
        if settings.anthropic_model_name:
            self.providers['anthropic'] = NamedPydanticAIProvider(
                provider_name='anthropic',
                model_prefix='anthropic',
                api_key=env_api_key('APP_ANTHROPIC_API_KEY', 'ANTHROPIC_API_KEY'),
                missing_key_hint='missing APP_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY',
            )

    def get(self, spec: ModelSpec) -> Provider:
        return self.providers[spec.provider]

    def health_snapshot(self, ttl_seconds: int | None = None) -> list[dict]:
        ttl = self.settings.provider_health_cache_seconds if ttl_seconds is None else ttl_seconds
        now = time.monotonic()
        if self._health_snapshot_cache is not None and now - self._health_snapshot_at < ttl:
            return [dict(item) for item in self._health_snapshot_cache]
        results: list[dict] = []
        for name, provider in self.providers.items():
            started = time.monotonic()
            try:
                health_result = provider.health()
                if inspect.iscoroutine(health_result):
                    try:
                        health_result.close()
                    except Exception:
                        pass
                    ok, detail = False, 'provider health() returned coroutine; expected sync tuple'
                else:
                    ok, detail = health_result
            except Exception as exc:
                ok, detail = False, str(exc)
            latency_ms = round((time.monotonic() - started) * 1000.0, 2)
            results.append({'provider': name, 'ok': ok, 'detail': detail, 'latency_ms': latency_ms})
        self._health_snapshot_cache = results
        self._health_snapshot_at = now
        return [dict(item) for item in results]

    def health_matrix(self) -> list[dict]:
        return self.health_snapshot()

    def provider_status(self, provider_name: str, ttl_seconds: int | None = None) -> tuple[bool, str]:
        snapshot = self.health_snapshot(ttl_seconds=ttl_seconds)
        for item in snapshot:
            if item['provider'] == provider_name:
                return bool(item['ok']), str(item['detail'])
        return False, 'provider not registered'

    def resolve_candidates(self, candidate_ids: Iterable[str]) -> tuple[ModelSpec, list[str], list[dict], str | None]:
        snapshot = self.health_snapshot()
        status_by_provider = {item['provider']: (bool(item['ok']), str(item['detail'])) for item in snapshot}
        specs: list[ModelSpec] = []
        for model_id in candidate_ids:
            try:
                specs.append(get_model_spec(model_id))
            except KeyError:
                logger.warning('Unknown model candidate %s', model_id)
        if not specs:
            raise RuntimeError('No valid model candidates provided')
        for spec in specs:
            ok, _ = status_by_provider.get(spec.provider, (False, 'provider not registered'))
            if ok:
                return spec, list(candidate_ids), snapshot, None
        for spec in sorted(specs, key=lambda item: item.priority, reverse=True):
            if spec.offline_ready:
                return spec, list(candidate_ids), snapshot, spec.degraded_message
        return specs[0], list(candidate_ids), snapshot, specs[0].degraded_message
