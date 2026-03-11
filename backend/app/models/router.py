import math
from dataclasses import dataclass

from app.core.config import get_settings
from app.models.catalog import ModelSpec, get_model_spec
from app.providers.manager import ProviderManager


@dataclass(frozen=True)
class ModelResolution:
    requested_model_id: str
    resolved_model: ModelSpec
    fallback_candidates: list[str]
    fallback_reason: str | None
    health_snapshot: list[dict]
    routing_notes: list[str]


@dataclass(frozen=True)
class RoutingRequirements:
    prompt_chars: int = 0
    requires_stream: bool = False
    requires_tools: bool = False
    prefer_offline: bool = False


class ModelRouter:
    def resolve(
        self,
        providers: ProviderManager,
        requested_model_id: str | None = None,
        query: str | None = None,
        requires_stream: bool = False,
        requires_tools: bool = False,
        prefer_offline: bool = False,
    ) -> ModelResolution:
        settings = get_settings()
        candidate_id = requested_model_id or settings.default_model_id
        requirements = RoutingRequirements(
            prompt_chars=len(query or ''),
            requires_stream=requires_stream,
            requires_tools=requires_tools,
            prefer_offline=prefer_offline,
        )
        spec, candidates, snapshot, reason, notes = self._resolve_candidates(
            providers=providers,
            requested_model_id=candidate_id,
            requirements=requirements,
        )
        return ModelResolution(
            requested_model_id=candidate_id,
            resolved_model=spec,
            fallback_candidates=candidates,
            fallback_reason=reason,
            health_snapshot=snapshot,
            routing_notes=notes,
        )

    @staticmethod
    def _build_chain(model_id: str) -> list[str]:
        seen: list[str] = []
        queue = [model_id]
        while queue:
            current = queue.pop(0)
            if current in seen:
                continue
            seen.append(current)
            try:
                spec = get_model_spec(current)
            except KeyError:
                continue
            queue.extend(spec.fallback_ids)
        if 'mock_static' not in seen:
            seen.append('mock_static')
        return seen

    def _resolve_candidates(
        self,
        providers: ProviderManager,
        requested_model_id: str,
        requirements: RoutingRequirements,
    ) -> tuple[ModelSpec, list[str], list[dict], str | None, list[str]]:
        candidate_ids = self._build_chain(requested_model_id)
        snapshot = providers.health_snapshot()
        status_by_provider = {item['provider']: item for item in snapshot}
        notes: list[str] = []
        prompt_tokens = max(1, math.ceil(requirements.prompt_chars / 4))
        specs: list[ModelSpec] = []
        for model_id in candidate_ids:
            try:
                specs.append(get_model_spec(model_id))
            except KeyError:
                notes.append(f'candidate_skipped_unknown:{model_id}')
        if not specs:
            raise RuntimeError('No valid model candidates provided')

        requested_spec = specs[0]
        requested_status = status_by_provider.get(requested_spec.provider, {'ok': False, 'detail': 'provider not registered'})
        if self._is_compatible(requested_spec, prompt_tokens, requirements):
            if bool(requested_status.get('ok')):
                notes.append(f'selected_requested:{requested_spec.id}')
                return requested_spec, candidate_ids, snapshot, None, notes
            notes.append(f'requested_unhealthy:{requested_spec.provider}:{requested_status.get("detail", "unknown")}')
        else:
            notes.append(f'requested_incompatible:{requested_spec.id}')

        ranked: list[tuple[float, int, ModelSpec]] = []
        for idx, spec in enumerate(specs[1:], start=1):
            status = status_by_provider.get(spec.provider, {'ok': False, 'detail': 'provider not registered'})
            if not self._is_compatible(spec, prompt_tokens, requirements):
                notes.append(f'candidate_incompatible:{spec.id}')
                continue
            if not bool(status.get('ok')):
                notes.append(f'candidate_unhealthy:{spec.id}:{status.get("detail", "unknown")}')
                continue
            latency_ms = float(status.get('latency_ms') or 250.0)
            score = float(spec.priority)
            if spec.family == 'mock':
                # Keep deterministic mock as last-resort fallback even if its catalog priority is high.
                score -= 1000.0
            score -= min(latency_ms / 15.0, 35.0)
            score -= float(idx * 5)
            if requirements.prefer_offline and spec.offline_ready:
                score += 20.0
            if requirements.prefer_offline and spec.gpu_required:
                score -= 25.0
            ranked.append((score, idx, spec))
            notes.append(f'candidate_score:{spec.id}:{score:.2f}')

        if ranked:
            _, _, selected = max(ranked, key=lambda item: (item[0], -item[1]))
            reason = selected.degraded_message or f'Routed from {requested_spec.id} to {selected.id} based on health/capabilities.'
            return selected, candidate_ids, snapshot, reason, notes

        for spec in specs:
            if not self._is_compatible(spec, prompt_tokens, requirements):
                continue
            if spec.offline_ready:
                notes.append(f'selected_offline_ready:{spec.id}')
                reason = spec.degraded_message or f'No healthy providers for requested model {requested_spec.id}.'
                return spec, candidate_ids, snapshot, reason, notes

        notes.append(f'selected_requested_fallback:{requested_spec.id}')
        return requested_spec, candidate_ids, snapshot, requested_spec.degraded_message, notes

    @staticmethod
    def _is_compatible(spec: ModelSpec, prompt_tokens: int, requirements: RoutingRequirements) -> bool:
        if prompt_tokens > spec.max_context_tokens:
            return False
        if requirements.requires_stream and not spec.supports_stream:
            return False
        if requirements.requires_tools and not spec.supports_tools:
            return False
        return True
