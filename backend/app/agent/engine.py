import logging
from typing import Generator

from app.agent.memory import CognitiveState
from app.agent.planner import Planner
from app.agent.tools import ToolRouter
from app.models.router import ModelRouter
from app.providers.manager import ProviderManager

log = logging.getLogger('app.agent.engine')


class AgentEngine:
    def __init__(self) -> None:
        self.router = ModelRouter()
        self.planner = Planner()
        self.providers = ProviderManager()
        self.tools = ToolRouter()

    def _build_traces(self, query: str, spec, provider) -> tuple[dict, list[dict], list[str]]:
        state = CognitiveState(goal=query)
        plan = self.planner.create_plan(query)
        traces = [
            {'kind': 'plan', 'message': 'plan selected', 'data': {'kind': plan.kind, 'steps': plan.steps}},
            {'kind': 'model', 'message': 'model selected', 'data': {'id': spec.id, 'provider': spec.provider, 'family': spec.family}},
        ]
        notes = []
        for idx, step in enumerate(plan.steps, start=1):
            tool_result = self.tools.execute(query, step)
            prompt = f"Goal: {query}\nStep: {step}\nNotes: {tool_result}"
            generated = provider.generate(spec.value, prompt)
            preview = generated.text[:160]
            note = f'step {idx}: {step} | tool={tool_result} | {preview}'
            state.remember(note)
            notes.append(note)
            traces.append({'kind': 'step', 'message': f'completed {step}', 'data': {'index': idx, 'step': step, 'tool_result': tool_result, 'preview': preview}})
        final_prompt = f'Compose a final answer for goal={query} using notes={notes}'
        answer = provider.generate(spec.value, final_prompt).text
        state.answer = answer
        state.confidence = min(0.95, 0.55 + 0.1 * len(plan.steps))
        traces.append({'kind': 'final', 'message': 'answer synthesized', 'data': {'answer': answer[:300]}})
        payload = {'answer': state.answer, 'model_id': spec.id, 'provider': spec.provider, 'plan_kind': plan.kind, 'confidence': state.confidence}
        return payload, traces, notes

    def run(self, query: str, model_id: str | None = None) -> dict:
        resolution = self.router.resolve(self.providers, model_id, query=query)
        fallback_event = None
        if resolution.fallback_reason:
            fallback_event = {
                'kind': 'fallback',
                'message': 'model fallback applied',
                'data': {
                    'requested_model_id': resolution.requested_model_id,
                    'resolved_model_id': resolution.resolved_model.id,
                    'fallback_candidates': resolution.fallback_candidates,
                    'reason': resolution.fallback_reason,
                    'health_snapshot': resolution.health_snapshot,
                    'routing_notes': resolution.routing_notes,
                },
            }
        provider = self.providers.get(resolution.resolved_model)
        payload, traces, _ = self._build_traces(query, resolution.resolved_model, provider)
        if fallback_event is not None:
            traces.insert(0, fallback_event)
        payload.update({
            'requested_model_id': resolution.requested_model_id,
            'resolved_model_id': resolution.resolved_model.id,
            'fallback_applied': resolution.resolved_model.id != resolution.requested_model_id,
            'fallback_reason': resolution.fallback_reason,
        })
        log.info('agent_completed', extra={'model_id': resolution.resolved_model.id})
        return {**payload, 'traces': traces}

    def run_stream(self, query: str, model_id: str | None = None) -> Generator[dict, None, None]:
        resolution = self.router.resolve(self.providers, model_id, query=query, requires_stream=True)
        provider = self.providers.get(resolution.resolved_model)
        if resolution.fallback_reason:
            yield {
                'kind': 'fallback',
                'message': 'model fallback applied',
                'data': {
                    'requested_model_id': resolution.requested_model_id,
                    'resolved_model_id': resolution.resolved_model.id,
                    'fallback_candidates': resolution.fallback_candidates,
                    'reason': resolution.fallback_reason,
                    'health_snapshot': resolution.health_snapshot,
                    'routing_notes': resolution.routing_notes,
                },
            }
        plan = self.planner.create_plan(query)
        yield {'kind': 'plan', 'message': 'plan selected', 'data': {'kind': plan.kind, 'steps': plan.steps}}
        yield {'kind': 'model', 'message': 'model selected', 'data': {'id': resolution.resolved_model.id, 'provider': resolution.resolved_model.provider}}
        notes = []
        for idx, step in enumerate(plan.steps, start=1):
            tool_result = self.tools.execute(query, step)
            prompt = f"Goal: {query}\nStep: {step}\nNotes: {tool_result}"
            preview_parts = []
            for chunk in provider.stream(resolution.resolved_model.value, prompt):
                preview_parts.append(chunk)
                if len(''.join(preview_parts)) >= 160:
                    break
            preview = ''.join(preview_parts).strip()
            notes.append(f'step {idx}:{step}:{preview}')
            yield {'kind': 'step', 'message': f'completed {step}', 'data': {'index': idx, 'step': step, 'tool_result': tool_result, 'preview': preview}}
        final_prompt = f'Compose a final answer for goal={query} using notes={notes}'
        answer_parts = []
        for chunk in provider.stream(resolution.resolved_model.value, final_prompt):
            answer_parts.append(chunk)
            yield {'kind': 'token', 'message': 'stream', 'data': {'token': chunk}}
        answer = ''.join(answer_parts).strip()
        yield {
            'kind': 'final',
            'message': 'answer synthesized',
            'data': {
                'answer': answer,
                'model_id': resolution.resolved_model.id,
                'requested_model_id': resolution.requested_model_id,
                'fallback_applied': resolution.resolved_model.id != resolution.requested_model_id,
            },
        }
