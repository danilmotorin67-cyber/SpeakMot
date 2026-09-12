import contextlib
import threading
import traceback

import keyboard

from . import output
from .audio import Recorder
from .config import Config
from .textproc import apply_replacements
from .transcriber import Transcriber

IDLE = "idle"
RECORDING = "recording"
TRANSCRIBING = "transcribing"
LOADING = "loading"
ERROR = "error"

MODIFIERS = {"ctrl", "alt", "shift", "windows", "win", "cmd"}


def hotkey_keys(hotkey: str) -> set[str]:
    return {part.strip().lower() for part in hotkey.split("+") if part.strip()}


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
        self._release_hook = None
        self._cancel_hook = None
        self._watchdog: threading.Thread | None = None
        self._busy = threading.Lock()

    def _set_state(self, state: str, message: str = "") -> None:
        self.state = state
        self.on_state(state, message)

    # --- горячие клавиши ---

    def install_hotkey(self) -> None:
        self.remove_hotkey()
        try:
            self._hotkey_handles.append(
                keyboard.add_hotkey(
                    self.cfg.hotkey,
                    self.start_recording if self.cfg.hotkey_mode == "hold" else self.toggle,
                    suppress=False,
                )
            )
            if self.cfg.hotkey_mode == "hold":
                self._release_hook = keyboard.hook(self._on_key_event)
        except Exception as exc:
            self._set_state(ERROR, f"Не удалось назначить {self.cfg.hotkey}: {exc}")
            return
        if self.state in (IDLE, ERROR):
            self._set_state(IDLE)

    def _on_key_event(self, event) -> None:
        """В режиме удержания останавливает запись, когда отпущена любая клавиша комбинации.

        Собственный хук вместо on_release_key: комбинация может заканчиваться
        модификатором, а чужие хуки трогать нельзя.
        """
        if event.event_type != "up" or not self.recorder.is_recording:
            return
        name = (event.name or "").lower()
        keys = hotkey_keys(self.cfg.hotkey)
        if name in keys or (name in MODIFIERS and keys & MODIFIERS):
            self.stop_and_transcribe()

    def remove_hotkey(self) -> None:
        for handle in self._hotkey_handles:
            with contextlib.suppress(Exception):
                keyboard.remove_hotkey(handle)
        self._hotkey_handles.clear()
        for hook in (self._release_hook, self._cancel_hook):
            if hook is not None:
                with contextlib.suppress(Exception):
                    keyboard.unhook(hook)
        self._release_hook = None
        self._cancel_hook = None

    def _install_cancel_hotkey(self) -> None:
        if self._cancel_hook is not None:
            return
        try:
            self._cancel_hook = keyboard.add_hotkey("esc", self.cancel, suppress=False)
        except Exception:
            self._cancel_hook = None

    def _remove_cancel_hotkey(self) -> None:
        if self._cancel_hook is None:
            return
        with contextlib.suppress(Exception):
            keyboard.remove_hotkey(self._cancel_hook)
        self._cancel_hook = None

    # --- запись ---

    def toggle(self) -> None:
        if self.recorder.is_recording:
            self.stop_and_transcribe()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        if self.recorder.is_recording or self.state == TRANSCRIBING:
            return
        if not self.transcriber.is_loaded:
            self._set_state(LOADING, "Модель ещё загружается, подождите")
            return
        try:
            self.recorder.device = self.cfg.input_device
            self.recorder.silence_stop = self.cfg.silence_stop
            self.recorder.start()
        except Exception as exc:
            self._set_state(ERROR, f"Микрофон недоступен: {exc}")
            return
        if self.cfg.sound_feedback:
            output.beep(True)
        self._install_cancel_hotkey()
        self._start_watchdog()
        self._set_state(RECORDING)

    def _start_watchdog(self) -> None:
        """Следит за тишиной: сам останавливает запись, когда пользователь замолчал."""
        if self.cfg.silence_stop <= 0:
            return

        def watch():
            while self.recorder.is_recording:
                if self.recorder.silence_reached:
                    self.stop_and_transcribe()
                    return
                threading.Event().wait(0.1)

        self._watchdog = threading.Thread(target=watch, daemon=True)
        self._watchdog.start()

    def stop_and_transcribe(self) -> None:
        if not self.recorder.is_recording:
            return
        audio = self.recorder.stop()
        self._remove_cancel_hotkey()
        if self.cfg.sound_feedback:
            output.beep(False)
        self._set_state(TRANSCRIBING)
        threading.Thread(target=self._transcribe_worker, args=(audio,), daemon=True).start()

    def cancel(self) -> None:
        """Выбрасывает начатую запись, ничего не распознавая."""
        if not self.recorder.is_recording:
            return
        self.recorder.stop()
        self._remove_cancel_hotkey()
        self._set_state(IDLE, "Запись отменена")

    def _transcribe_worker(self, audio) -> None:
        with self._busy:
            try:
                text = self.transcriber.transcribe(audio)
            except Exception:
                traceback.print_exc()
                self._set_state(ERROR, "Ошибка распознавания")
                return

            text = apply_replacements(text, self.cfg.replacements)
            if not text:
                self._set_state(ERROR, "Ничего не распознано")
                return

            if self.cfg.auto_paste:
                output.deliver(text, self.cfg.paste_method)
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
        self._set_state(LOADING, f"Подготовка модели {self.cfg.model_size}…")
        try:
            self.transcriber.load(progress=lambda message: self._set_state(LOADING, message))
        except Exception as exc:
            self._set_state(ERROR, f"Модель не загрузилась: {exc}")
            return
        self._set_state(IDLE)

    def shutdown(self) -> None:
        self.remove_hotkey()
        if self.recorder.is_recording:
            self.recorder.stop()
