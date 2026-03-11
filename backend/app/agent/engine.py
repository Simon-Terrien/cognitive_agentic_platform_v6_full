import logging
from dataclasses import dataclass
from typing import Generator

from app.agent.memory import CognitiveState, get_memory_store
from app.agent.planner import Planner
from app.agent.tools import ToolPolicy, ToolRouter
from app.core.config import get_settings
from app.models.router import ModelRouter
from app.providers.manager import ProviderManager

log = logging.getLogger('app.agent.engine')


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


@dataclass
class ExecutionUsage:
    recursion_depth: int = 1
    iterations: int = 0
    tool_calls: int = 0
    prompt_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class AgentEngine:
    def __init__(self) -> None:
        self.router = ModelRouter()
        self.planner = Planner()
        self.providers = ProviderManager()
        self.tools = ToolRouter()
        self.policy = ToolPolicy()
        self.memory = get_memory_store()

    def _memory_context(self, session_id: str, query: str) -> tuple[list[str], list[dict]]:
        settings = get_settings()
        retrieved = self.memory.retrieve(session_id=session_id, goal=query, query=query, top_k=settings.agent_memory_top_k)
        context = [item.note for item in retrieved]
        traces = [
            {
                'kind': 'memory',
                'message': 'memory retrieved',
                'data': {
                    'memory_id': item.memory_id,
                    'score': round(item.score, 4),
                    'components': item.score_components,
                },
            }
            for item in retrieved
        ]
        return context, traces

    @staticmethod
    def _governor_trace(reason: str, usage: ExecutionUsage) -> dict:
        return {
            'kind': 'governor',
            'message': 'execution constrained',
            'data': {
                'reason': reason,
                'iterations': usage.iterations,
                'tool_calls': usage.tool_calls,
                'prompt_tokens': usage.prompt_tokens,
                'output_tokens': usage.output_tokens,
                'total_tokens': usage.total_tokens,
                'recursion_depth': usage.recursion_depth,
            },
        }

    def _build_traces(self, query: str, spec, provider) -> tuple[dict, list[dict], list[str]]:
        settings = get_settings()
        state = CognitiveState(goal=query)
        plan = self.planner.create_plan(query)
        usage = ExecutionUsage()
        memory_context, memory_traces = self._memory_context(session_id=spec.id, query=query)
        traces = [
            {'kind': 'plan', 'message': 'plan selected', 'data': {'kind': plan.kind, 'steps': plan.steps}},
            {'kind': 'model', 'message': 'model selected', 'data': {'id': spec.id, 'provider': spec.provider, 'family': spec.family}},
        ]
        traces.extend(memory_traces)
        notes = []
        if usage.recursion_depth > settings.agent_max_recursion_depth:
            traces.append(self._governor_trace('max_recursion_depth_exceeded', usage))
            payload = {'answer': 'Stopped: recursion depth limit reached.', 'model_id': spec.id, 'provider': spec.provider, 'plan_kind': plan.kind, 'confidence': 0.0}
            return payload, traces, notes

        limited_steps = plan.steps[: settings.agent_max_iterations]
        if len(limited_steps) < len(plan.steps):
            traces.append(self._governor_trace('max_iterations_reached', usage))

        for idx, step in enumerate(limited_steps, start=1):
            usage.iterations += 1
            if usage.tool_calls >= settings.agent_max_tool_calls:
                traces.append(self._governor_trace('max_tool_calls_reached', usage))
                break
            tool_id = self.tools.resolve(query, step)
            tool_decision = self.policy.evaluate(query, step, tool_id)
            traces.append({'kind': 'audit', 'message': 'tool policy evaluated', 'data': {'tool_id': tool_id, 'allowed': tool_decision.allowed, 'reason': tool_decision.reason}})
            if not tool_decision.allowed:
                tool_result = f'tool=blocked::{tool_decision.reason}'
            else:
                tool_result = self.tools.run(tool_id)
                usage.tool_calls += 1
            prompt = f"Goal: {query}\nStep: {step}\nMemory: {memory_context}\nNotes: {tool_result}"
            prompt_tokens = _estimate_tokens(prompt)
            if prompt_tokens > settings.agent_max_prompt_tokens:
                traces.append(self._governor_trace('max_prompt_tokens_reached', usage))
                break
            if usage.total_tokens + prompt_tokens > settings.agent_max_total_tokens:
                traces.append(self._governor_trace('max_total_tokens_reached', usage))
                break
            usage.prompt_tokens += prompt_tokens
            generated = provider.generate(spec.value, prompt)
            usage.output_tokens += _estimate_tokens(generated.text)
            usage.total_tokens = usage.prompt_tokens + usage.output_tokens
            if usage.total_tokens > settings.agent_max_total_tokens:
                traces.append(self._governor_trace('max_total_tokens_reached', usage))
                break
            preview = generated.text[:160]
            note = f'step {idx}: {step} | tool={tool_result} | {preview}'
            state.remember(note)
            self.memory.append(session_id=spec.id, goal=query, note=note, importance=min(1.0, 0.35 + 0.1 * idx))
            notes.append(note)
            traces.append({'kind': 'step', 'message': f'completed {step}', 'data': {'index': idx, 'step': step, 'tool_result': tool_result, 'preview': preview}})
        final_prompt = f'Compose a final answer for goal={query} using memory={memory_context} and notes={notes}'
        final_prompt_tokens = _estimate_tokens(final_prompt)
        if final_prompt_tokens <= settings.agent_max_prompt_tokens and usage.total_tokens + final_prompt_tokens <= settings.agent_max_total_tokens:
            usage.prompt_tokens += final_prompt_tokens
            answer = provider.generate(spec.value, final_prompt).text
            usage.output_tokens += _estimate_tokens(answer)
            usage.total_tokens = usage.prompt_tokens + usage.output_tokens
        else:
            traces.append(self._governor_trace('final_answer_budget_exceeded', usage))
            answer = 'Stopped early due to execution budget limits. Partial reasoning notes were collected.'
        state.answer = answer
        state.confidence = min(0.95, 0.55 + 0.1 * len(notes))
        traces.append({'kind': 'final', 'message': 'answer synthesized', 'data': {'answer': answer[:300]}})
        payload = {
            'answer': state.answer,
            'model_id': spec.id,
            'provider': spec.provider,
            'plan_kind': plan.kind,
            'confidence': state.confidence,
            'governance': {
                'max_recursion_depth': settings.agent_max_recursion_depth,
                'max_iterations': settings.agent_max_iterations,
                'max_tool_calls': settings.agent_max_tool_calls,
                'max_prompt_tokens': settings.agent_max_prompt_tokens,
                'max_total_tokens': settings.agent_max_total_tokens,
                'usage': {
                    'recursion_depth': usage.recursion_depth,
                    'iterations': usage.iterations,
                    'tool_calls': usage.tool_calls,
                    'prompt_tokens': usage.prompt_tokens,
                    'output_tokens': usage.output_tokens,
                    'total_tokens': usage.total_tokens,
                },
            },
        }
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
        settings = get_settings()
        usage = ExecutionUsage()
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
        memory_context, memory_traces = self._memory_context(session_id=resolution.resolved_model.id, query=query)
        for trace in memory_traces:
            yield trace
        yield {'kind': 'plan', 'message': 'plan selected', 'data': {'kind': plan.kind, 'steps': plan.steps}}
        yield {'kind': 'model', 'message': 'model selected', 'data': {'id': resolution.resolved_model.id, 'provider': resolution.resolved_model.provider}}
        notes = []
        if usage.recursion_depth > settings.agent_max_recursion_depth:
            yield self._governor_trace('max_recursion_depth_exceeded', usage)
            yield {'kind': 'final', 'message': 'answer synthesized', 'data': {'answer': 'Stopped: recursion depth limit reached.', 'model_id': resolution.resolved_model.id}}
            return
        limited_steps = plan.steps[: settings.agent_max_iterations]
        if len(limited_steps) < len(plan.steps):
            yield self._governor_trace('max_iterations_reached', usage)
        for idx, step in enumerate(limited_steps, start=1):
            usage.iterations += 1
            if usage.tool_calls >= settings.agent_max_tool_calls:
                yield self._governor_trace('max_tool_calls_reached', usage)
                break
            tool_id = self.tools.resolve(query, step)
            tool_decision = self.policy.evaluate(query, step, tool_id)
            yield {'kind': 'audit', 'message': 'tool policy evaluated', 'data': {'tool_id': tool_id, 'allowed': tool_decision.allowed, 'reason': tool_decision.reason}}
            if tool_decision.allowed:
                tool_result = self.tools.run(tool_id)
                usage.tool_calls += 1
            else:
                tool_result = f'tool=blocked::{tool_decision.reason}'
            prompt = f"Goal: {query}\nStep: {step}\nMemory: {memory_context}\nNotes: {tool_result}"
            prompt_tokens = _estimate_tokens(prompt)
            if prompt_tokens > settings.agent_max_prompt_tokens:
                yield self._governor_trace('max_prompt_tokens_reached', usage)
                break
            if usage.total_tokens + prompt_tokens > settings.agent_max_total_tokens:
                yield self._governor_trace('max_total_tokens_reached', usage)
                break
            usage.prompt_tokens += prompt_tokens
            preview_parts = []
            for chunk in provider.stream(resolution.resolved_model.value, prompt):
                preview_parts.append(chunk)
                if len(''.join(preview_parts)) >= 160:
                    break
            preview = ''.join(preview_parts).strip()
            usage.output_tokens += _estimate_tokens(preview)
            usage.total_tokens = usage.prompt_tokens + usage.output_tokens
            notes.append(f'step {idx}:{step}:{preview}')
            note = f'step {idx}: {step} | tool={tool_result} | {preview}'
            self.memory.append(session_id=resolution.resolved_model.id, goal=query, note=note, importance=min(1.0, 0.35 + 0.1 * idx))
            yield {'kind': 'step', 'message': f'completed {step}', 'data': {'index': idx, 'step': step, 'tool_result': tool_result, 'preview': preview}}
        final_prompt = f'Compose a final answer for goal={query} using memory={memory_context} and notes={notes}'
        final_prompt_tokens = _estimate_tokens(final_prompt)
        if final_prompt_tokens > settings.agent_max_prompt_tokens or usage.total_tokens + final_prompt_tokens > settings.agent_max_total_tokens:
            yield self._governor_trace('final_answer_budget_exceeded', usage)
            yield {'kind': 'final', 'message': 'answer synthesized', 'data': {'answer': 'Stopped early due to execution budget limits. Partial reasoning notes were collected.', 'model_id': resolution.resolved_model.id}}
            return
        usage.prompt_tokens += final_prompt_tokens
        answer_parts = []
        for chunk in provider.stream(resolution.resolved_model.value, final_prompt):
            answer_parts.append(chunk)
            yield {'kind': 'token', 'message': 'stream', 'data': {'token': chunk}}
        answer = ''.join(answer_parts).strip()
        usage.output_tokens += _estimate_tokens(answer)
        usage.total_tokens = usage.prompt_tokens + usage.output_tokens
        yield {
            'kind': 'final',
            'message': 'answer synthesized',
            'data': {
                'answer': answer,
                'model_id': resolution.resolved_model.id,
                'requested_model_id': resolution.requested_model_id,
                'fallback_applied': resolution.resolved_model.id != resolution.requested_model_id,
                'governance': {
                    'usage': {
                        'recursion_depth': usage.recursion_depth,
                        'iterations': usage.iterations,
                        'tool_calls': usage.tool_calls,
                        'prompt_tokens': usage.prompt_tokens,
                        'output_tokens': usage.output_tokens,
                        'total_tokens': usage.total_tokens,
                    }
                },
            },
        }
