import contextlib
import logging
import threading
import time

import keyboard

from . import output, profiles, voice_commands, winapi
from .audio import Recorder, normalize
from .config import Config
from .profiles import Profile
from .textproc import apply_replacements
from .transcriber import ModelNotInstalled, Transcriber

IDLE = "idle"
RECORDING = "recording"
TRANSCRIBING = "transcribing"
LOADING = "loading"
ERROR = "error"

log = logging.getLogger("speakmot.engine")

MODIFIERS = {"ctrl", "alt", "shift", "windows", "win", "cmd"}
LANGUAGE_NAMES = {"ru": "русский", "en": "английский", "auto": "автоопределение"}


def hotkey_keys(hotkey: str) -> set[str]:
    return {part.strip().lower() for part in hotkey.split("+") if part.strip()}


class Engine:
    """Связывает горячую клавишу, запись и распознавание.

    Колбэки вызываются из фоновых потоков — интерфейс обязан
    переносить их в свой поток самостоятельно.
    """

    def __init__(
        self,
        cfg: Config,
        on_state=None,
        on_result=None,
        on_language_changed=None,
        on_partial=None,
    ):
        self.cfg = cfg
        self.on_state = on_state or (lambda state, message: None)
        self.on_result = on_result or (lambda text: None)
        self.on_language_changed = on_language_changed or (lambda language: None)
        self.on_partial = on_partial or (lambda text: None)
        self.recorder = Recorder(cfg.sample_rate, cfg.input_device)
        self.transcriber = Transcriber(cfg)
        self.state = IDLE
        self._hotkey_handles: list = []
        self._release_hook = None
        self._cancel_hook = None
        self._watchdog: threading.Thread | None = None
        self._busy = threading.Lock()
        self.target_window = 0
        self.resolved = None
        self.last_text = ""
        self._started_at = 0.0

    def _set_state(self, state: str, message: str = "") -> None:
        self.state = state
        self.on_state(state, message)

    # --- горячие клавиши ---

    def install_hotkey(self) -> None:
        self.remove_hotkey()
        log.info("назначаю горячую клавишу %s (%s)", self.cfg.hotkey, self.cfg.hotkey_mode)
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
            if self.cfg.repeat_hotkey.strip():
                self._hotkey_handles.append(
                    keyboard.add_hotkey(
                        self.cfg.repeat_hotkey.strip(),
                        self.repeat_last,
                        suppress=False,
                    )
                )
            if self.cfg.language_hotkey.strip():
                self._hotkey_handles.append(
                    keyboard.add_hotkey(
                        self.cfg.language_hotkey.strip(),
                        self.switch_language,
                        suppress=False,
                    )
                )
        except Exception as exc:
            log.exception("горячая клавиша не назначилась")
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

    def repeat_last(self) -> None:
        """Вставляет последний распознанный текст ещё раз."""
        if not self.last_text:
            self._set_state(IDLE, "Нечего повторять")
            return
        self.target_window = winapi.foreground_window()
        self.deliver(self.last_text, restore_focus=False)
        self._set_state(IDLE, "Вставлено повторно")

    def switch_language(self) -> None:
        """Переключает язык между русским и английским прямо во время работы."""
        order = ["ru", "en", "auto"]
        try:
            following = order[(order.index(self.cfg.language) + 1) % len(order)]
        except ValueError:
            following = "ru"
        self.cfg.language = following
        self.cfg.save()
        self.on_language_changed(following)
        self._set_state(IDLE, f"Язык: {LANGUAGE_NAMES.get(following, following)}")

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
            self._set_state(LOADING, "Модель ещё готовится, подождите")
            return
        self._resolve_context()
        try:
            self.recorder.device = self.cfg.input_device
            self.recorder.silence_stop = self.cfg.silence_stop
            self.recorder.start()
        except Exception as exc:
            self._set_state(ERROR, f"Микрофон недоступен: {exc}")
            return
        log.info(
            "запись начата, профиль %r, язык %s",
            self.resolved.profile_name or "общий",
            self.resolved.language,
        )
        if self.cfg.sound_feedback:
            output.beep(True)
        self._started_at = time.monotonic()
        self._install_cancel_hotkey()
        self._start_watchdog()
        self._start_streaming()
        self._set_state(RECORDING)

    def _resolve_context(self) -> None:
        """Запоминает окно, куда пойдёт текст, и настройки его профиля."""
        self.target_window = winapi.foreground_window()
        loaded = [Profile.from_dict(item) for item in self.cfg.profiles]
        self.resolved = profiles.resolve(
            self.cfg,
            loaded,
            winapi.process_name(self.target_window),
            winapi.window_title(self.target_window),
        )

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

    def _start_streaming(self) -> None:
        """Показывает распознанное по ходу речи.

        Модель запускается на накопленном куске целиком: это дороже, чем
        досчитывать хвост, зато не путает границы слов. Текст только
        показывается — вставляется по-прежнему итоговый.
        """
        if not self.cfg.streaming:
            return

        def watch():
            settings = self.resolved
            while self.recorder.is_recording:
                threading.Event().wait(2.5)
                if not self.recorder.is_recording:
                    return
                audio = self.recorder.snapshot()
                if audio.size < self.cfg.sample_rate:
                    continue
                try:
                    text = self.transcriber.transcribe(
                        normalize(audio), language=settings.language
                    )
                except Exception:
                    log.exception("предпросмотр по ходу речи не удался")
                    return
                if text and self.recorder.is_recording:
                    self.on_partial(text)

        threading.Thread(target=watch, daemon=True).start()

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
            settings = self.resolved or profiles.resolve(self.cfg, [], "", "")
            try:
                text = self.transcriber.transcribe(
                    normalize(audio),
                    language=settings.language,
                    translate=self.cfg.translate_to_english,
                )
            except Exception:
                log.exception("распознавание не удалось")
                self._set_state(ERROR, "Ошибка распознавания")
                return

            text = apply_replacements(text, self.cfg.replacements)
            if settings.voice_commands:
                text = voice_commands.apply_commands(text)
            if not text:
                self._set_state(ERROR, "Ничего не распознано")
                return

            self.last_text = text
            self._record_stats(text)
            self.cfg.history.insert(0, text)
            del self.cfg.history[50:]
            self.cfg.save()

            # с предпросмотром текст отдаёт интерфейс — после подтверждения
            if not self.cfg.preview_before_paste:
                self.deliver(text)

            self.on_result(text)
            self._set_state(IDLE)

    def deliver(self, text: str, restore_focus: bool = False) -> None:
        """Отправляет готовый текст в активное окно или в буфер обмена."""
        if not text:
            return
        settings = self.resolved or profiles.resolve(self.cfg, [], "", "")
        if restore_focus:
            winapi.focus_window(self.target_window)
        if self.cfg.auto_paste:
            output.deliver(text, settings.paste_method)
        else:
            output.copy_text(text)

    def _record_stats(self, text: str) -> None:
        """Копит, сколько всего надиктовано — просто приятно видеть."""
        stats = self.cfg.stats
        stats["count"] = stats.get("count", 0) + 1
        stats["words"] = stats.get("words", 0) + len(text.split())
        if self._started_at:
            stats["seconds"] = stats.get("seconds", 0) + (
                time.monotonic() - self._started_at
            )

    # --- модель ---

    def preload_model(self) -> None:
        threading.Thread(target=self._load_worker, daemon=True).start()

    def _load_worker(self) -> None:
        self._set_state(LOADING, f"Подготовка модели {self.cfg.model_size}…")
        try:
            self.transcriber.load(progress=lambda message: self._set_state(LOADING, message))
        except ModelNotInstalled:
            self._set_state(ERROR, f"Модель {self.cfg.model_size} не установлена")
            return
        except Exception as exc:
            self._set_state(ERROR, f"Модель не загрузилась: {exc}")
            return
        self._set_state(IDLE)

    def shutdown(self) -> None:
        self.remove_hotkey()
        if self.recorder.is_recording:
            self.recorder.stop()
