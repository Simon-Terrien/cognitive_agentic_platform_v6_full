class ToolRouter:
    def execute(self, query: str, step: str) -> str:
        lowered = query.lower()
        if 'dataset' in lowered:
            return 'tool=dataset_registry'
        if 'benchmark' in lowered or 'latency' in lowered:
            return 'tool=benchmark_notes'
        if 'train' in lowered or 'lora' in lowered:
            return 'tool=training_notes'
        return f'tool=reasoning::{step}'
