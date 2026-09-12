import sys

from PySide6.QtCore import QObject, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .. import engine as engine_states
from ..config import Config
from ..engine import Engine
from . import theme
from .main_window import MainWindow, center_on_screen
from .overlay import RecordingOverlay


class Bridge(QObject):
    """Переносит колбэки движка из фоновых потоков в поток интерфейса."""

    state_changed = Signal(str, str)
    result_ready = Signal(str)


def build_icon(recording: bool = False) -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(theme.DANGER if recording else theme.ACCENT))
    painter.drawRoundedRect(QRectF(4, 4, 56, 56), 16, 16)
    painter.setBrush(QColor("#ffffff"))
    painter.drawRoundedRect(QRectF(25, 15, 14, 22), 7, 7)
    painter.drawRoundedRect(QRectF(21, 42, 22, 4), 2, 2)
    painter.drawRoundedRect(QRectF(30, 37, 4, 6), 2, 2)
    painter.end()
    return QIcon(pixmap)


class SpeakMotApp:
    def __init__(self):
        self.qt = QApplication(sys.argv)
        self.qt.setApplicationName("SpeakMot")
        self.qt.setQuitOnLastWindowClosed(False)
        self.qt.setStyleSheet(theme.QSS)

        self.cfg = Config.load()
        self.bridge = Bridge()
        self.engine = Engine(
            self.cfg,
            on_state=lambda state, message="": self.bridge.state_changed.emit(state, message),
            on_result=self.bridge.result_ready.emit,
        )

        self.window = MainWindow(self)
        self.overlay = RecordingOverlay()
        center_on_screen(self.window)

        self.bridge.state_changed.connect(self._on_state)
        self.bridge.result_ready.connect(self.window.show_result)

        self._build_tray()

        self._overlay_timer = QTimer()
        self._overlay_timer.timeout.connect(self._push_overlay_level)
        self._overlay_timer.start(45)

        self.engine.install_hotkey()
        self.engine.preload_model()

    # --- трей ---

    def _build_tray(self) -> None:
        self.tray = QSystemTrayIcon(build_icon(), self.qt)
        self.tray.setToolTip("SpeakMot")

        menu = QMenu()
        open_action = QAction("Открыть SpeakMot", menu)
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
            self.overlay.show_recording(self.window._pretty_hotkey(self.cfg.hotkey))
        elif state == engine_states.TRANSCRIBING:
            self.overlay.show_transcribing()
        elif state == engine_states.IDLE:
            self.overlay.show_done("Готово")
        elif state == engine_states.ERROR:
            self.overlay.show_error(message or "Ошибка")
            self.tray.showMessage("SpeakMot", message or "Ошибка", build_icon(), 4000)
            QTimer.singleShot(
                3000, lambda: self.window.apply_state(engine_states.IDLE, "")
            )

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
        return self.qt.exec()
