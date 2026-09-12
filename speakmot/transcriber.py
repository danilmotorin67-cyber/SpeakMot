import threading
import time

import numpy as np

from .config import MODELS_DIR, Config

# Приблизительный размер моделей на диске — для расчёта прогресса скачивания.
MODEL_BYTES = {
    "tiny": 75_000_000,
    "base": 145_000_000,
    "small": 484_000_000,
    "medium": 1_530_000_000,
    "large-v3": 3_090_000_000,
}


def _downloaded_bytes() -> int:
    if not MODELS_DIR.exists():
        return 0
    return sum(f.stat().st_size for f in MODELS_DIR.rglob("*") if f.is_file())


class Transcriber:
    """Обёртка над faster-whisper. Модель грузится лениво, при первом использовании."""

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

    def _watch_download(self, progress, stop_event: threading.Event) -> None:
        """Пока идёт скачивание, оценивает прогресс по размеру папки с моделями."""
        total = MODEL_BYTES.get(self.cfg.model_size, 0)
        start = _downloaded_bytes()
        while not stop_event.wait(0.7):
            done = _downloaded_bytes() - start
            if total and done > 0:
                percent = min(99, int(done * 100 / total))
                progress(f"Загрузка модели {self.cfg.model_size} — {percent}%")

    def load(self, progress=None) -> None:
        progress = progress or (lambda _message: None)
        with self._lock:
            if self._model is not None:
                return

            from faster_whisper import WhisperModel

            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            device, compute_type = self._resolve_device()

            progress(f"Подготовка модели {self.cfg.model_size}…")
            stop_event = threading.Event()
            watcher = threading.Thread(
                target=self._watch_download, args=(progress, stop_event), daemon=True
            )
            watcher.start()
            try:
                self._model = self._build(WhisperModel, device, compute_type, progress)
            finally:
                stop_event.set()

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
            )
            self.device_in_use = device
            return model
        except Exception:
            if device != "cuda":
                raise
            progress("Видеокарта недоступна, перехожу на процессор…")
            time.sleep(0.2)
            model = WhisperModel(
                self.cfg.model_size,
                device="cpu",
                compute_type="int8",
                download_root=str(MODELS_DIR),
            )
            self.device_in_use = "cpu"
            return model

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
        return " ".join(segment.text.strip() for segment in segments).strip()
