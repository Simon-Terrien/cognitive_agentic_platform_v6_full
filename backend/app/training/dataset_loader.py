import json
from pathlib import Path

from app.training.registry import DatasetSpec


class DatasetLoader:
    def __init__(self) -> None:
        backend_root = Path(__file__).resolve().parents[2]
        self.cache_dir = self._ensure_cache_dir(backend_root / '.cache' / 'training')

    def _ensure_cache_dir(self, preferred: Path) -> Path:
        try:
            preferred.mkdir(parents=True, exist_ok=True)
            return preferred
        except OSError:
            fallback = Path('/tmp/cognitive_agentic_training')
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

    def load_normalized_rows(self, spec: DatasetSpec, limit: int = 200) -> list[dict]:
        try:
            from datasets import DownloadConfig, load_dataset
        except Exception:
            return self._fallback_rows()
        download_config = DownloadConfig(local_files_only=True)
        try:
            ds = load_dataset(spec.id, split='train', download_config=download_config)
        except Exception:
            try:
                ds = load_dataset(spec.id, download_config=download_config)
                split_name = next(iter(ds.keys()))
                ds = ds[split_name]
            except Exception:
                return self._fallback_rows()
        rows = []
        for item in ds:
            normalized = self._normalize_item(item)
            if normalized:
                rows.append(normalized)
            if len(rows) >= limit:
                break
        return rows or self._fallback_rows()

    def dump_jsonl(self, dataset_id: str, rows: list[dict]) -> Path:
        safe_name = dataset_id.replace('/', '__')
        out_path = self.cache_dir / f'{safe_name}.jsonl'
        try:
            with out_path.open('w', encoding='utf-8') as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + '\n')
        except OSError:
            self.cache_dir = self._ensure_cache_dir(Path('/tmp/cognitive_agentic_training'))
            out_path = self.cache_dir / f'{safe_name}.jsonl'
            with out_path.open('w', encoding='utf-8') as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + '\n')
        return out_path

    def _normalize_item(self, item: dict) -> dict | None:
        if 'prompt' in item and 'answer' in item:
            reasoning = item.get('reasoning') or item.get('cot') or ''
            return {'prompt': str(item['prompt']), 'reasoning': str(reasoning), 'answer': str(item['answer'])}
        if 'instruction' in item and 'output' in item:
            return {'prompt': str(item['instruction']), 'reasoning': '', 'answer': str(item['output'])}
        if 'messages' in item:
            prompt, answer = [], []
            for message in item['messages']:
                role = message.get('role', '')
                content = message.get('content', '')
                if role in {'user', 'system'}:
                    prompt.append(content)
                elif role == 'assistant':
                    answer.append(content)
            if prompt or answer:
                return {'prompt': '\n'.join(prompt).strip(), 'reasoning': '', 'answer': '\n'.join(answer).strip()}
        return None

    def _fallback_rows(self) -> list[dict]:
        return [
            {
                'prompt': 'Explain recursive reasoning in simple terms.',
                'reasoning': 'Break the concept into a small iterative loop.',
                'answer': 'Recursive reasoning repeatedly updates an answer using earlier partial results.',
            },
            {
                'prompt': 'Why use multiple local inference backends?',
                'reasoning': 'Different backends optimize different constraints.',
                'answer': 'Because Ollama, vLLM, llama.cpp and Transformers serve different hardware and deployment needs.',
            },
        ]
