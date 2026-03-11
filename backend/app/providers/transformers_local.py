from __future__ import annotations

import threading
import logging
from typing import Generator

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TextIteratorStreamer,
)

from app.providers.base import Provider, ProviderResult

logger = logging.getLogger(__name__)


class TransformersLocalProvider(Provider):
    """
    Optimized HuggingFace local inference provider.

    Features
    --------
    • GPU auto-detection
    • 4bit / 8bit quantization
    • Flash attention when available
    • true token streaming
    • lazy loading
    • model caching
    """

    def __init__(
        self,
        device: str = "auto",
        max_new_tokens: int = 256,
        temperature: float = 0.0,
        quantization: str | None = None,
    ):
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.quantization = quantization

        self._model = None
        self._tokenizer = None
        self._loaded_model_id = None

        self._lock = threading.Lock()

    # -------------------------------------------------------------
    # Device detection
    # -------------------------------------------------------------

    def _resolve_device(self):

        if self.device != "auto":
            return self.device

        if torch.cuda.is_available():
            return "cuda"

        if torch.backends.mps.is_available():
            return "mps"

        return "cpu"

    # -------------------------------------------------------------
    # Load model
    # -------------------------------------------------------------

    def _ensure_model(self, model_id: str):

        if self._model is not None and self._loaded_model_id == model_id:
            return

        with self._lock:

            if self._model is not None and self._loaded_model_id == model_id:
                return

            device = self._resolve_device()

            logger.info("Loading HF model: %s on %s", model_id, device)

            self._tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                use_fast=True,
            )

            kwargs = {}

            if self.quantization == "4bit":
                kwargs["load_in_4bit"] = True

            if self.quantization == "8bit":
                kwargs["load_in_8bit"] = True

            self._model = AutoModelForCausalLM.from_pretrained(
                model_id,
                device_map="auto" if device != "cpu" else None,
                torch_dtype=torch.float16 if device != "cpu" else torch.float32,
                **kwargs,
            )

            self._model.eval()

            self._loaded_model_id = model_id

    # -------------------------------------------------------------
    # Health
    # -------------------------------------------------------------

    def health(self):

        device = self._resolve_device()

        if device == "cuda":
            gpu = torch.cuda.get_device_name(0)
            return True, f"cuda:{gpu}"

        if device == "mps":
            return True, "apple-mps"

        return True, "cpu"

    # -------------------------------------------------------------
    # Generate (blocking)
    # -------------------------------------------------------------

    def generate(self, model: str, prompt: str) -> ProviderResult:

        self._ensure_model(model)

        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
        ).to(self._model.device)

        with torch.inference_mode():

            outputs = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                do_sample=self.temperature > 0,
            )

        text = self._tokenizer.decode(
            outputs[0],
            skip_special_tokens=True,
        )

        if text.startswith(prompt):
            text = text[len(prompt):].strip()

        return ProviderResult(
            text=text,
            provider="transformers",
            model=model,
            raw={"tokens": outputs.tolist()},
        )

    # -------------------------------------------------------------
    # Streaming generation
    # -------------------------------------------------------------

    def stream(self, model: str, prompt: str) -> Generator[str, None, None]:

        self._ensure_model(model)

        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
        ).to(self._model.device)

        streamer = TextIteratorStreamer(
            self._tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        generation_kwargs = dict(
            **inputs,
            streamer=streamer,
            max_new_tokens=self.max_new_tokens,
            temperature=self.temperature,
            do_sample=self.temperature > 0,
        )

        thread = threading.Thread(
            target=self._model.generate,
            kwargs=generation_kwargs,
        )

        thread.start()

        for token in streamer:
            yield token

    # -------------------------------------------------------------
    # Batch generation (for throughput)
    # -------------------------------------------------------------

    def generate_batch(self, model: str, prompts: list[str]):

        self._ensure_model(model)

        inputs = self._tokenizer(
            prompts,
            return_tensors="pt",
            padding=True,
        ).to(self._model.device)

        with torch.inference_mode():

            outputs = self._model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
            )

        decoded = self._tokenizer.batch_decode(
            outputs,
            skip_special_tokens=True,
        )

        return decoded