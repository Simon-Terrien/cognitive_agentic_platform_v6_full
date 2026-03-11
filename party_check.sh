#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
SKIP_FRONTEND="${SKIP_FRONTEND:-0}"

echo "[party-check] backend contract check"
(
  cd "$ROOT/backend"
  if [ ! -x ".venv/bin/python" ]; then
    echo "[party-check] missing backend/.venv. Run: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
    exit 1
  fi

  PYTHONPATH=. .venv/bin/python - <<'PY'
from app.api.routes import health, models, chat, training
from app.providers.base import ProviderResult


class FakeProvider:
    def generate(self, model: str, prompt: str) -> ProviderResult:
        return ProviderResult(text=f'generated:{model}', provider='demo', model=model)

    def stream(self, model: str, prompt: str):
        yield 'chunk-1 '
        yield 'chunk-2'


chat.engine.providers.get = lambda spec: FakeProvider()

health_payload = health.health()
models_payload = models.list_models()
model_detail = models.get_model('ollama_qwen3')
chat_payload = chat.chat(chat.ChatRequest(message='demo request', model_id='ollama_qwen3'))
stream_payload = ''.join(list(chat.iter_sse(chat._stream_chat('demo request', 'ollama_qwen3'))))
legacy_stream = ''.join(list(chat.iter_sse(chat._legacy_stream_events('demo request', 'ollama_qwen3'))))
training_status = training.training_status()
training_start = training.training_start()
training_stop = training.training_stop()
training_datasets = training.training_datasets()
training_plan = training.training_plan(model_id='ollama_qwen3', dataset_id=None)

assert health_payload['ok'] is True
assert len(models_payload) >= 1
assert model_detail['id'] == 'ollama_qwen3'
assert chat_payload['answer']
assert ('"kind": "final"' in stream_payload) or ('"kind":"final"' in stream_payload)
assert ('"kind": "result"' in legacy_stream) or ('"kind":"result"' in legacy_stream)
assert isinstance(training_status.running, bool)
assert training_start.running is True
assert training_stop.running is False
assert len(training_datasets) >= 1
assert training_plan['backend'] == 'unsloth'
assert training_plan['dataset_id']
assert training_plan['normalized_rows'] >= 1

print('[ok] health/models/chat/training routes are demo-ready at contract level')
print(f"[ok] training plan dataset={training_plan['dataset_id']} rows={training_plan['normalized_rows']}")
print(f"[ok] training jsonl hint={training_plan['command_hint']}")
PY
)

if [ "$SKIP_FRONTEND" != "1" ]; then
  echo "[party-check] frontend verify"
  (
    cd "$ROOT/frontend"
    npm run verify
  )
fi

echo "[party-check] complete"
