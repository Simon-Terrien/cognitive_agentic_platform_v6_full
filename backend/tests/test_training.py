from app.api.routes import training


class FakePlan:
    def __init__(self) -> None:
        self.backend = 'unsloth'
        self.dataset_id = 'TeichAI/Aurora-Alpha-15.5k'
        self.normalized_rows = 12
        self.command_hint = 'python scripts/unsloth_sft_example.py --model-name qwen3:4b'
        self.export_targets = ['gguf', 'ollama']
        self.notes = ['fake plan']


def test_training_plan_endpoint(monkeypatch):
    monkeypatch.setattr(training.trainer, 'plan_training', lambda dataset, model: FakePlan())
    dataset_payload = training.training_datasets()
    assert isinstance(dataset_payload, list)
    assert dataset_payload
    assert training.datasets() == dataset_payload
    payload = training.training_plan(dataset_id=None, model_id='ollama_qwen3')
    assert payload['backend'] == 'unsloth'
    assert 'export_targets' in payload
    assert payload['dataset_id']


def test_training_plan_writes_jsonl_to_demo_safe_location(monkeypatch):
    monkeypatch.setattr(
        training.trainer.loader,
        'load_normalized_rows',
        lambda dataset, limit=200: [{'prompt': 'p', 'reasoning': 'r', 'answer': 'a'}],
    )
    captured: dict[str, object] = {}

    def fake_build_plan(dataset_id, jsonl_path, row_count, model_name):
        captured['dataset_id'] = dataset_id
        captured['jsonl_path'] = str(jsonl_path)
        captured['row_count'] = row_count
        captured['model_name'] = model_name
        return FakePlan()

    monkeypatch.setattr(training.trainer.unsloth, 'build_plan', fake_build_plan)

    payload = training.training_plan(dataset_id=None, model_id='ollama_qwen3')

    assert payload['backend'] == 'unsloth'
    assert captured['row_count'] == 1
    assert 'TeichAI__Aurora-Alpha-15.5k.jsonl' in captured['jsonl_path']
    assert captured['jsonl_path'].startswith(('/home/lupise/dev/cognitive_agentic_platform_v6_full/backend/.cache/training/', '/tmp/cognitive_agentic_training/'))
