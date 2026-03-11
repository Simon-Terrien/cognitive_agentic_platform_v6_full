from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    kind: str
    steps: list[str]


class Planner:
    def create_plan(self, goal: str) -> Plan:
        lowered = goal.lower()
        if any(word in lowered for word in ['benchmark', 'latency', 'throughput']):
            return Plan(kind='benchmark', steps=['inspect target', 'compare backends', 'summarize'])
        if any(word in lowered for word in ['train', 'fine-tune', 'finetune', 'dataset', 'lora']):
            return Plan(kind='training', steps=['inspect dataset', 'select backend', 'propose plan'])
        if any(word in lowered for word in ['debug', 'error', 'exception', 'trace']):
            return Plan(kind='debug', steps=['collect clues', 'test hypotheses', 'explain fix'])
        return Plan(kind='analysis', steps=['understand goal', 'reason stepwise', 'synthesize answer'])
