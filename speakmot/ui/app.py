import logging
import sys

from PySide6.QtCore import QObject, QTimer, QtMsgType, Signal, qInstallMessageHandler
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .. import autostart, branding, hotkeys, models
from .. import engine as engine_states
from ..config import Config
from ..engine import Engine
from . import theme
from .main_window import MainWindow, center_on_screen
from .overlay import RecordingOverlay
from .preview import PreviewWindow

_QT_LEVELS = {
    QtMsgType.QtDebugMsg: logging.DEBUG,
    QtMsgType.QtInfoMsg: logging.INFO,
    QtMsgType.QtWarningMsg: logging.WARNING,
    QtMsgType.QtCriticalMsg: logging.ERROR,
    QtMsgType.QtFatalMsg: logging.CRITICAL,
}


def _route_qt_messages(mode, context, message) -> None:
    """Предупреждения Qt уходят в stderr, которого в окне без консоли нет."""
    logging.getLogger("qt").log(_QT_LEVELS.get(mode, logging.INFO), message)


class Bridge(QObject):
    """Переносит колбэки движка из фоновых потоков в поток интерфейса."""

    state_changed = Signal(str, str)
    result_ready = Signal(str)
    partial_ready = Signal(str)


def build_icon(recording: bool = False) -> QIcon:
    """Значок трея: тот же знак, но красный во время записи."""
    color = theme.color("danger") if recording else branding.ACCENT
    icon = QIcon()
    for size in (16, 24, 32, 48, 64):
        icon.addPixmap(branding.mark_pixmap(size, color))
    return icon


class SpeakMotApp:
    def __init__(self):
        qInstallMessageHandler(_route_qt_messages)
        self.qt = QApplication(sys.argv)
        self.qt.setApplicationName("SpeakMotor")
        branding.set_app_user_model_id()
        self.app_icon = branding.app_icon()
        self.qt.setWindowIcon(self.app_icon)
        self.qt.setQuitOnLastWindowClosed(False)

        self.cfg = Config.load()
        theme.apply(self.cfg.theme, self.cfg.accent)
        self.qt.setStyleSheet(theme.qss())
        self.bridge = Bridge()
        self.engine = Engine(
            self.cfg,
            on_state=lambda state, message="": self.bridge.state_changed.emit(state, message),
            on_result=self.bridge.result_ready.emit,
            on_partial=self.bridge.partial_ready.emit,
        )

        self.window = MainWindow(self)
        self.overlay = RecordingOverlay()
        self.preview = PreviewWindow()
        for window in (self.window, self.overlay, self.preview):
            window.setWindowIcon(self.app_icon)
        self.preview.accepted.connect(self._on_preview_accepted)
        self.preview.rejected.connect(lambda: self.overlay.hide())
        center_on_screen(self.window)

        self.bridge.state_changed.connect(self._on_state)
        self.bridge.result_ready.connect(self._on_result)
        self.bridge.partial_ready.connect(self.overlay.show_partial)

        self._build_tray()

        self._overlay_timer = QTimer()
        self._overlay_timer.timeout.connect(self._push_overlay_level)
        self._overlay_timer.start(45)

        self._sync_autostart()
        self.engine.install_hotkey()
        if models.is_installed(self.cfg.model_size):
            self.engine.preload_model()

    def _sync_autostart(self) -> None:
        """Приводит запись в реестре в соответствие с настройкой.

        Путь к приложению меняется при переустановке, поэтому запись
        переписывается при каждом запуске.
        """
        try:
            if self.cfg.autostart or autostart.is_enabled():
                autostart.set_enabled(self.cfg.autostart)
        except OSError:
            pass

    # --- трей ---

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(build_icon(), self.qt)
        self.tray.setToolTip("SpeakMotor — диктовка")

        menu = QMenu()
        open_action = QAction("Открыть SpeakMotor", menu)
        open_action.triggered.connect(self.show_window)
        record_action = QAction("Начать / остановить запись", menu)
        record_action.triggered.connect(self.toggle_recording)
        quit_action = QAction("Выход", menu)
        quit_action.triggered.connect(self.quit)

        menu.addAction(open_action)
        menu.addAction(record_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.show_window()

    # --- состояние ---

    def _on_state(self, state: str, message: str) -> None:
        self.window.apply_state(state, message)
        self.tray.setIcon(build_icon(state == engine_states.RECORDING))

        if state == engine_states.RECORDING:
            self.overlay.show_recording(hotkeys.pretty(self.cfg.hotkey))
        elif state == engine_states.TRANSCRIBING:
            self.overlay.show_transcribing()
        elif state == engine_states.IDLE:
            self.overlay.show_done(message or "Готово")
        elif state == engine_states.ERROR:
            self.overlay.show_error(message or "Ошибка")
            self.tray.showMessage("SpeakMotor", message or "Ошибка", build_icon(), 4000)
            QTimer.singleShot(
                3000, lambda: self.window.apply_state(engine_states.IDLE, "")
            )

    def _on_result(self, text: str) -> None:
        self.window.show_result(text)
        if self.cfg.preview_before_paste:
            self.overlay.hide()
            self.preview.show_text(text)

    def _on_preview_accepted(self, text: str) -> None:
        self.overlay.hide()
        self.engine.deliver(text, restore_focus=True)

    def apply_appearance(self, theme_name: str, accent: str) -> None:
        """Перекрашивает интерфейс на лету."""
        theme.apply(theme_name, accent)
        self.qt.setStyleSheet(theme.qss())
        self.window.mic_button.refresh_theme()
        self.window.refresh_icons()
        self.tray.setIcon(build_icon(self.engine.state == engine_states.RECORDING))

    def _push_overlay_level(self) -> None:
        if self.engine.recorder.is_recording:
            self.overlay.push_level(self.engine.recorder.level)

    # --- действия ---

    def toggle_recording(self) -> None:
        self.engine.toggle()

    def show_window(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def model_selected(self, size: str) -> None:
        self.window.show_model(size)
        self.engine.transcriber.unload()
        self.engine.preload_model()

    def reload(self, model_changed: bool) -> None:
        self.engine.install_hotkey()
        if model_changed:
            self.engine.transcriber.unload()
            self.engine.preload_model()

    def quit(self) -> None:
        self.engine.shutdown()
        self.tray.hide()
        self.qt.quit()

    def run(self) -> int:
        self.window.show()
        if not models.is_installed(self.cfg.model_size):
            # первый запуск: сразу показываем, что модель надо установить
            self.window._go_to_page(2)
            self.window.models_page.report(
                "Модель ещё не установлена. Выберите её и нажмите «Установить»."
            )
        return self.qt.exec()
