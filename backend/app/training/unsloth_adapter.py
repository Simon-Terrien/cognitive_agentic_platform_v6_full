from dataclasses import dataclass
import importlib.util
from pathlib import Path


@dataclass
class UnslothPlan:
    backend: str
    dataset_id: str
    normalized_rows: int
    command_hint: str
    export_targets: list[str]
    notes: list[str]


class UnslothAdapter:
    def is_available(self) -> bool:
        return importlib.util.find_spec('unsloth') is not None

    def build_plan(self, dataset_id: str, jsonl_path: Path, row_count: int, model_name: str) -> UnslothPlan:
        command_hint = f'python scripts/unsloth_sft_example.py --model-name {model_name} --dataset-jsonl {jsonl_path}'
        notes = [
            'Normalize your dataset to prompt/reasoning/answer before SFT.',
            'Prefer a small student first for fast iteration.',
            'After fine-tuning, choose deployment target by hardware: GGUF/llama.cpp for quantized local use, Ollama for easy local serving, vLLM for GPU throughput.',
        ]
        if not self.is_available():
            notes.append('Unsloth is not installed in this environment, so this platform returns a training plan rather than pretending to fine-tune.')
        return UnslothPlan(
            backend='unsloth',
            dataset_id=dataset_id,
            normalized_rows=row_count,
            command_hint=command_hint,
            export_targets=['gguf', 'ollama', 'llama.cpp', 'vllm', 'transformers'],
            notes=notes,
        )

    def example_script(self) -> str:
        return '\n'.join([
            '# Example starter script for a future real Unsloth integration.',
            '# Fill this in on a GPU machine with the exact Unsloth install matching your CUDA/Torch stack.',
            '',
            'from unsloth import FastLanguageModel',
            'from datasets import load_dataset',
            '',
            '# model, tokenizer = FastLanguageModel.from_pretrained(',
            '#     model_name="Qwen/Qwen3-8B",',
            '#     max_seq_length=4096,',
            '#     load_in_4bit=True,',
            '# )',
            '',
            '# dataset = load_dataset("json", data_files="normalized.jsonl", split="train")',
            '# Then wire into your SFT/TRL flow and export to GGUF / Ollama / vLLM.',
        ])
