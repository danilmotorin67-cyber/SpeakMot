import queue
import threading

import numpy as np
import sounddevice as sd


class Recorder:
    """Пишет моно-аудио с микрофона в память, пока идёт запись."""

    def __init__(self, sample_rate: int = 16000, device: int | None = None):
        self.sample_rate = sample_rate
        self.device = device
        self._chunks: queue.Queue[np.ndarray] = queue.Queue()
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.level = 0.0

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    def _callback(self, indata, frames, time_info, status):
        chunk = indata[:, 0].copy()
        self.level = float(np.abs(chunk).max())
        self._chunks.put(chunk)

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = queue.Queue()
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

        parts = []
        while not self._chunks.empty():
            parts.append(self._chunks.get())
        if not parts:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(parts).astype(np.float32)


def list_input_devices() -> list[tuple[int, str]]:
    devices = []
    for idx, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            devices.append((idx, dev["name"]))
    return devices
