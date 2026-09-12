import threading
import traceback

import keyboard

from . import output
from .audio import Recorder
from .config import Config
from .transcriber import Transcriber

IDLE = "idle"
RECORDING = "recording"
TRANSCRIBING = "transcribing"
LOADING = "loading"
ERROR = "error"


class Engine:
    """Связывает горячую клавишу, запись и распознавание.

    Колбэки вызываются из фоновых потоков — интерфейс обязан
    переносить их в свой поток самостоятельно.
    """

    def __init__(self, cfg: Config, on_state=None, on_result=None):
        self.cfg = cfg
        self.on_state = on_state or (lambda state, message: None)
        self.on_result = on_result or (lambda text: None)
        self.recorder = Recorder(cfg.sample_rate, cfg.input_device)
        self.transcriber = Transcriber(cfg)
        self.state = IDLE
        self._hotkey_handles: list = []
        self._busy = threading.Lock()

    def _set_state(self, state: str, message: str = "") -> None:
        self.state = state
        self.on_state(state, message)

    # --- горячие клавиши ---

    def install_hotkey(self) -> None:
        self.remove_hotkey()
        try:
            if self.cfg.hotkey_mode == "hold":
                self._hotkey_handles.append(
                    keyboard.add_hotkey(self.cfg.hotkey, self.start_recording, suppress=False)
                )
                self._hotkey_handles.append(
                    keyboard.on_release_key(
                        self.cfg.hotkey.split("+")[-1],
                        lambda _event: self.stop_and_transcribe(),
                    )
                )
            else:
                self._hotkey_handles.append(
                    keyboard.add_hotkey(self.cfg.hotkey, self.toggle, suppress=False)
                )
        except Exception as exc:
            self._set_state(ERROR, f"Не удалось назначить {self.cfg.hotkey}: {exc}")
            return
        if self.state in (IDLE, ERROR):
            self._set_state(IDLE)

    def remove_hotkey(self) -> None:
        for handle in self._hotkey_handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                try:
                    keyboard.unhook(handle)
                except Exception:
                    pass
        self._hotkey_handles.clear()

    # --- запись ---

    def toggle(self) -> None:
        if self.recorder.is_recording:
            self.stop_and_transcribe()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        if self.recorder.is_recording or self.state == TRANSCRIBING:
            return
        try:
            self.recorder.device = self.cfg.input_device
            self.recorder.start()
        except Exception as exc:
            self._set_state(ERROR, f"Микрофон недоступен: {exc}")
            return
        if self.cfg.sound_feedback:
            output.beep(True)
        self._set_state(RECORDING)

    def stop_and_transcribe(self) -> None:
        if not self.recorder.is_recording:
            return
        audio = self.recorder.stop()
        if self.cfg.sound_feedback:
            output.beep(False)
        self._set_state(TRANSCRIBING)
        threading.Thread(target=self._transcribe_worker, args=(audio,), daemon=True).start()

    def _transcribe_worker(self, audio) -> None:
        with self._busy:
            try:
                text = self.transcriber.transcribe(audio)
            except Exception:
                traceback.print_exc()
                self._set_state(ERROR, "Ошибка распознавания")
                return

            if not text:
                self._set_state(ERROR, "Ничего не распознано")
                return

            if self.cfg.auto_paste:
                output.paste_text(text)
            else:
                output.copy_text(text)

            self.cfg.history.insert(0, text)
            del self.cfg.history[50:]
            self.cfg.save()

            self.on_result(text)
            self._set_state(IDLE)

    # --- модель ---

    def preload_model(self) -> None:
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        self._set_state(LOADING, f"Загрузка модели {self.cfg.model_size}…")
        try:
            self.transcriber.load()
        except Exception as exc:
            self._set_state(ERROR, f"Модель не загрузилась: {exc}")
            return
        self._set_state(IDLE)

    def shutdown(self) -> None:
        self.remove_hotkey()
        if self.recorder.is_recording:
            self.recorder.stop()
