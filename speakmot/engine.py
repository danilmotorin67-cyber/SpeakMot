import threading
import traceback

import keyboard

from . import output
from .audio import Recorder
from .config import Config
from .transcriber import Transcriber


class Engine:
    """Связывает горячую клавишу, запись и распознавание."""

    def __init__(self, cfg: Config, on_status=None, on_result=None):
        self.cfg = cfg
        self.on_status = on_status or (lambda text: None)
        self.on_result = on_result or (lambda text: None)
        self.recorder = Recorder(cfg.sample_rate, cfg.input_device)
        self.transcriber = Transcriber(cfg)
        self._hotkey_handles: list = []
        self._busy = threading.Lock()

    # --- горячие клавиши ---

    def install_hotkey(self) -> None:
        self.remove_hotkey()
        if self.cfg.hotkey_mode == "hold":
            self._hotkey_handles.append(
                keyboard.add_hotkey(self.cfg.hotkey, self.start_recording, suppress=False)
            )
            keyboard.on_release_key(
                self.cfg.hotkey.split("+")[-1], lambda _e: self.stop_and_transcribe()
            )
        else:
            self._hotkey_handles.append(
                keyboard.add_hotkey(self.cfg.hotkey, self.toggle, suppress=False)
            )
        self.on_status(f"Готов · {self.cfg.hotkey}")

    def remove_hotkey(self) -> None:
        for handle in self._hotkey_handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:
                pass
        self._hotkey_handles.clear()
        if self.cfg.hotkey_mode == "hold":
            keyboard.unhook_all()

    # --- запись ---

    def toggle(self) -> None:
        if self.recorder.is_recording:
            self.stop_and_transcribe()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        if self.recorder.is_recording:
            return
        try:
            self.recorder.device = self.cfg.input_device
            self.recorder.start()
        except Exception as exc:
            self.on_status(f"Ошибка микрофона: {exc}")
            return
        if self.cfg.sound_feedback:
            output.beep(True)
        self.on_status("Запись…")

    def stop_and_transcribe(self) -> None:
        if not self.recorder.is_recording:
            return
        audio = self.recorder.stop()
        if self.cfg.sound_feedback:
            output.beep(False)
        threading.Thread(target=self._transcribe_worker, args=(audio,), daemon=True).start()

    def _transcribe_worker(self, audio) -> None:
        with self._busy:
            self.on_status("Распознавание…")
            try:
                text = self.transcriber.transcribe(audio)
            except Exception:
                traceback.print_exc()
                self.on_status("Ошибка распознавания")
                return

            if not text:
                self.on_status("Ничего не распознано")
                return

            if self.cfg.auto_paste:
                output.paste_text(text)
            else:
                output.copy_text(text)

            self.cfg.history.insert(0, text)
            del self.cfg.history[20:]
            self.cfg.save()

            self.on_result(text)
            self.on_status(f"Готов · {self.cfg.hotkey}")

    def preload_model(self) -> None:
        threading.Thread(
            target=lambda: self._safe_load(), daemon=True
        ).start()

    def _safe_load(self) -> None:
        try:
            self.transcriber.load(progress=self.on_status)
            self.on_status(f"Готов · {self.cfg.hotkey}")
        except Exception as exc:
            self.on_status(f"Модель не загрузилась: {exc}")
