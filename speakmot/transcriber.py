import threading

import numpy as np

from .config import MODELS_DIR, Config


class Transcriber:
    """Обёртка над faster-whisper. Модель грузится лениво, при первом использовании."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._model = None
        self._lock = threading.Lock()

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
        with self._lock:
            if self._model is not None:
                return
            if progress:
                progress(f"Загрузка модели {self.cfg.model_size}…")
            from faster_whisper import WhisperModel

            device, compute_type = self._resolve_device()
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            self._model = WhisperModel(
                self.cfg.model_size,
                device=device,
                compute_type=compute_type,
                download_root=str(MODELS_DIR),
            )

    def unload(self) -> None:
        with self._lock:
            self._model = None

    def transcribe(self, audio: np.ndarray) -> str:
        if audio.size == 0:
            return ""
        self.load()
        language = None if self.cfg.language == "auto" else self.cfg.language
        segments, _ = self._model.transcribe(
            audio,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()
