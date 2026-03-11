import logging
import threading
import time

from app.schemas.training import TrainingStatusResponse
from app.models.catalog import get_model_spec
from app.training.registry import get_default_dataset
from app.training.trainer import Trainer

log = logging.getLogger('app.training.scheduler')


class TrainingScheduler:
    def __init__(self, idle_seconds: int = 900, default_model_id: str = 'ollama_qwen3') -> None:
        self.idle_seconds = idle_seconds
        self.default_model_id = default_model_id
        self.last_activity_ts = time.time()
        self.last_dataset: str | None = None
        self.last_result: str | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self.trainer = Trainer()

    def mark_activity(self) -> None:
        self.last_activity_ts = time.time()

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        log.info('training_scheduler_started')

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        log.info('training_scheduler_stopped')

    def status(self) -> TrainingStatusResponse:
        return TrainingStatusResponse(
            running=self._running,
            idle_seconds=int(time.time() - self.last_activity_ts),
            last_dataset=self.last_dataset,
            last_result=self.last_result,
        )

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            idle_for = time.time() - self.last_activity_ts
            if idle_for >= self.idle_seconds:
                dataset = get_default_dataset()
                model = get_model_spec(self.default_model_id)
                plan = self.trainer.plan_training(dataset, model)
                self.last_dataset = dataset.id
                self.last_result = f'{plan.backend}: {plan.command_hint}'
                self.last_activity_ts = time.time()
            time.sleep(1.0)
