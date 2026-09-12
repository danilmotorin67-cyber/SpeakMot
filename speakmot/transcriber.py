import threading

import numpy as np

from . import models
from .config import MODELS_DIR, Config


class ModelNotInstalled(Exception):
    pass


class Transcriber:
    """Обёртка над faster-whisper. Модель грузится с диска, ничего не скачивая."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._model = None
        self._lock = threading.Lock()
        self.device_in_use = "cpu"

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _resolve_device(self) -> tuple[str, str]:
        device = self.cfg.device
        if device == "auto":
            try:
                import ctranslate2

                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:
                device = "cpu"
        compute_type = self.cfg.compute_type
        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"
        return device, compute_type

    def load(self, progress=None) -> None:
        progress = progress or (lambda _message: None)
        with self._lock:
            if self._model is not None:
                return
            if not models.is_installed(self.cfg.model_size):
                raise ModelNotInstalled(self.cfg.model_size)

            from faster_whisper import WhisperModel

            device, compute_type = self._resolve_device()
            progress(f"Загрузка модели {self.cfg.model_size} в память…")
            self._model = self._build(WhisperModel, device, compute_type, progress)

    def _build(self, WhisperModel, device: str, compute_type: str, progress):
        """Создаёт модель, откатываясь на CPU, если видеокарта не готова.

        Сборки ctranslate2 с CUDA падают без cuDNN — сообщение при этом
        невнятное, поэтому пробуем ещё раз на процессоре.
        """
        try:
            model = WhisperModel(
                self.cfg.model_size,
                device=device,
                compute_type=compute_type,
                download_root=str(MODELS_DIR),
                local_files_only=True,
            )
            self.device_in_use = device
            return model
        except Exception:
            if device != "cuda":
                raise
            progress("Видеокарта недоступна, перехожу на процессор…")
            model = WhisperModel(
                self.cfg.model_size,
                device="cpu",
                compute_type="int8",
                download_root=str(MODELS_DIR),
                local_files_only=True,
            )
            self.device_in_use = "cpu"
            return model

    def unload(self) -> None:
        with self._lock:
            self._model = None

    def transcribe(self, audio: np.ndarray, language: str | None = None) -> str:
        if audio.size == 0:
            return ""
        self.load()
        language = language or self.cfg.language
        language = None if language == "auto" else language
        segments, _ = self._model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()
