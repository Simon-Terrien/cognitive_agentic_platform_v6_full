import logging

from app.models.catalog import ModelSpec
from app.training.dataset_loader import DatasetLoader
from app.training.registry import DatasetSpec
from app.training.unsloth_adapter import UnslothAdapter, UnslothPlan

log = logging.getLogger('app.training.trainer')


class Trainer:
    def __init__(self) -> None:
        self.loader = DatasetLoader()
        self.unsloth = UnslothAdapter()

    def plan_training(self, dataset: DatasetSpec, model: ModelSpec) -> UnslothPlan:
        rows = self.loader.load_normalized_rows(dataset, limit=200)
        path = self.loader.dump_jsonl(dataset.id, rows)
        log.info('training_plan_built', extra={'dataset_id': dataset.id, 'rows': len(rows), 'model_id': model.id})
        return self.unsloth.build_plan(dataset_id=dataset.id, jsonl_path=path, row_count=len(rows), model_name=model.value)
