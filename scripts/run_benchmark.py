#!/usr/bin/env python3
import argparse
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / 'backend'
PRESET_KEYS = {
    'APP_DEFAULT_MODEL_ID',
    'APP_OLLAMA_BASE_URL',
    'APP_VLLM_BASE_URL',
    'APP_VLLM_API_KEY',
    'APP_LLAMACPP_BASE_URL',
    'APP_LLAMACPP_API_KEY',
    'APP_TRANSFORMERS_DEVICE',
    'APP_TRANSFORMERS_MAX_NEW_TOKENS',
    'APP_MOCK_DELAY_MS',
}

RUNNER = """
import json
import time

from app.agent.engine import AgentEngine

goal = {goal!r}
started = time.perf_counter()
engine = AgentEngine()
result = engine.run(goal)
duration_ms = round((time.perf_counter() - started) * 1000, 2)
traces = result.get('traces', [])
payload = {{
    'goal': goal,
    'duration_ms': duration_ms,
    'model_id': result.get('model_id'),
    'provider': result.get('provider'),
    'plan_kind': result.get('plan_kind'),
    'confidence': result.get('confidence'),
    'step_count': sum(1 for item in traces if item.get('kind') == 'step'),
    'trace_count': len(traces),
    'answer_preview': (result.get('answer') or '')[:160],
}}
print(json.dumps(payload))
"""

SUITES = {
    'default': [
        'Explain how the local model router chooses a provider.',
        'Compare Qwen and LFM2 for a CPU-only workstation.',
        'Summarize when to use Ollama versus vLLM in this repo.',
    ],
    'speed': [
        'Say hello.',
        'Summarize the active model in one sentence.',
        'List two benchmark risks.',
    ],
    'planning': [
        'Plan a benchmark for qwen and lfm2 presets.',
        'Design a latency comparison between Ollama and vLLM.',
    ],
    'benchmark': [
        'Benchmark local providers for latency and summarize tradeoffs.',
        'Recommend a repeatable benchmark setup for model comparisons.',
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run benchmark comparisons across .env presets.')
    parser.add_argument(
        '--env-file',
        dest='env_files',
        action='append',
        help='Preset file to load through APP_ENV_FILE. Can be passed multiple times.',
    )
    parser.add_argument(
        '--suite',
        choices=sorted(SUITES),
        default='default',
        help='Built-in goal suite to run.',
    )
    parser.add_argument(
        '--goal',
        dest='goals',
        action='append',
        help='Extra goal to run. If provided, goals are appended to the selected suite.',
    )
    parser.add_argument('--iterations', type=int, default=1, help='Runs per goal and env preset.')
    parser.add_argument('--python', default=sys.executable, help='Python interpreter to use for child runs.')
    parser.add_argument('--json', action='store_true', help='Emit machine-readable JSON summary.')
    return parser.parse_args()


def resolve_env_file(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def run_once(python_bin: str, env_file: Path, goal: str) -> dict:
    env = os.environ.copy()
    for key in PRESET_KEYS:
        env.pop(key, None)
    existing_path = env.get('PYTHONPATH')
    env['PYTHONPATH'] = '.' if not existing_path else f'.{os.pathsep}{existing_path}'
    env['APP_ENV_FILE'] = str(env_file)
    proc = subprocess.run(
        [python_bin, '-c', RUNNER.format(goal=goal)],
        cwd=BACKEND_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return {
            'goal': goal,
            'error': proc.stderr.strip() or proc.stdout.strip() or f'child exited with {proc.returncode}',
        }
    return json.loads(proc.stdout.strip())


def benchmark_label(env_file: Path) -> str:
    name = env_file.name
    if name.startswith('.env.'):
        return name[5:]
    if name.startswith('.env'):
        return name[4:] or 'default'
    return name


def summarize_runs(rows: list[dict]) -> dict:
    durations = [row['duration_ms'] for row in rows if 'duration_ms' in row]
    confidence_values = [row['confidence'] for row in rows if 'confidence' in row]
    base = dict(rows[-1])
    base['iterations'] = len(rows)
    base['avg_duration_ms'] = round(statistics.mean(durations), 2) if durations else None
    base['min_duration_ms'] = round(min(durations), 2) if durations else None
    base['max_duration_ms'] = round(max(durations), 2) if durations else None
    base['confidence'] = round(statistics.mean(confidence_values), 3) if confidence_values else None
    return base


def print_table(results: list[dict]) -> None:
    headers = ['preset', 'goal', 'avg_ms', 'provider', 'model', 'plan', 'steps']
    widths = {header: len(header) for header in headers}
    rendered_rows = []
    for row in results:
        rendered = {
            'preset': row['preset'],
            'goal': row['goal'][:44],
            'avg_ms': 'ERR' if row.get('error') else f"{row.get('avg_duration_ms', 0):.2f}",
            'provider': row.get('provider', '-'),
            'model': row.get('model_id', '-'),
            'plan': row.get('plan_kind', '-'),
            'steps': str(row.get('step_count', '-')),
        }
        for key, value in rendered.items():
            widths[key] = max(widths[key], len(value))
        rendered_rows.append((rendered, row))

    line = '  '.join(header.ljust(widths[header]) for header in headers)
    print(line)
    print('  '.join('-' * widths[header] for header in headers))
    for rendered, source in rendered_rows:
        print('  '.join(rendered[header].ljust(widths[header]) for header in headers))
        if source.get('error'):
            print(f"  error: {source['error']}")


def main() -> int:
    args = parse_args()
    env_files = args.env_files or ['.env.mock']
    goals = list(SUITES[args.suite])
    if args.goals:
        goals.extend(args.goals)

    results = []
    for env_file_text in env_files:
        env_file = resolve_env_file(env_file_text)
        if not env_file.is_file():
            results.append({'preset': benchmark_label(env_file), 'goal': '-', 'error': f'missing env file: {env_file}'})
            continue
        for goal in goals:
            rows = [run_once(args.python, env_file, goal) for _ in range(max(1, args.iterations))]
            summary = summarize_runs(rows)
            summary['preset'] = benchmark_label(env_file)
            results.append(summary)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f'Benchmark suite: {args.suite}')
        print(f'Goals: {len(goals)} | Presets: {len(env_files)} | Iterations: {max(1, args.iterations)}')
        print_table(results)
    return 0 if not any(row.get('error') for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
