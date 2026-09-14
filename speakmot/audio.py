import queue
import threading

import numpy as np
import sounddevice as sd

SPEECH_THRESHOLD = 0.02


class Recorder:
    """Пишет моно-аудио с микрофона в память, пока идёт запись."""

    def __init__(self, sample_rate: int = 16000, device: int | None = None):
        self.sample_rate = sample_rate
        self.device = device
        self._chunks: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.level = 0.0
        self.silence_stop = 0.0
        self.silence_reached = False
        self._heard_speech = False
        self._silent_samples = 0

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def _callback(self, indata, frames, time_info, status):
        chunk = indata[:, 0].copy()
        self.level = float(np.abs(chunk).max())
        self._chunks.put(chunk)
        self._track_silence(chunk)

    def _track_silence(self, chunk: np.ndarray) -> None:
        """Отмечает, что после речи наступила достаточно долгая тишина."""
        if self.silence_stop <= 0:
            return
        if self.level >= SPEECH_THRESHOLD:
            self._heard_speech = True
            self._silent_samples = 0
            return
        if not self._heard_speech:
            return
        self._silent_samples += len(chunk)
        if self._silent_samples >= self.silence_stop * self.sample_rate:
            self.silence_reached = True

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = queue.Queue()
            self.silence_reached = False
            self._heard_speech = False
            self._silent_samples = 0
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.device,
                blocksize=1024,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> np.ndarray:
        """Останавливает запись и возвращает накопленный сигнал."""
        with self._lock:
            if self._stream is None:
                return np.zeros(0, dtype=np.float32)
            self._stream.stop()
            self._stream.close()
            self._stream = None
        self.level = 0.0
        self.silence_reached = False

        parts = []
        while not self._chunks.empty():
            parts.append(self._chunks.get())
        if not parts:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(parts).astype(np.float32)


def normalize(audio: np.ndarray, target_peak: float = 0.9) -> np.ndarray:
    """Подтягивает громкость записи к рабочему уровню.

    Тихий микрофон — частая причина пропущенных слов: Whisper хуже слышит
    сигнал с пиком в пару процентов. Совсем тихую дорожку не трогаем, иначе
    вместе с шумом усилится и он.
    """
    if audio.size == 0:
        return audio
    peak = float(np.abs(audio).max())
    if peak < 0.005 or peak >= target_peak:
        return audio
    return (audio * (target_peak / peak)).astype(np.float32)


def list_input_devices() -> list[tuple[int, str]]:
    devices = []
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] > 0:
            devices.append((index, device["name"]))
    return devices
