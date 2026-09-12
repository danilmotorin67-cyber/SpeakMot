from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .widgets import Waveform


class RecordingOverlay(QWidget):
    """Плавающая панель поверх всех окон: показывает запись и распознавание."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        panel = QFrame()
        panel.setObjectName("overlay")
        outer.addWidget(panel)

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(18, 12, 20, 12)
        layout.setSpacing(14)

        self.waveform = Waveform(bars=22)
        self.waveform.setFixedSize(150, 32)
        layout.addWidget(self.waveform)

        text_column = QVBoxLayout()
        text_column.setSpacing(1)
        self.title = QLabel("Слушаю…")
        self.title.setObjectName("overlayText")
        self.hint = QLabel("нажмите горячую клавишу ещё раз")
        self.hint.setObjectName("overlayHint")
        text_column.addWidget(self.title)
        text_column.addWidget(self.hint)
        layout.addLayout(text_column)

        self.setFixedSize(400, 62)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def _reposition(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(
            area.center().x() - self.width() // 2,
            area.bottom() - self.height() - 70,
        )

    def show_recording(self, hotkey: str) -> None:
        self._hide_timer.stop()
        self.title.setText("Слушаю…")
        self.hint.setText(f"{hotkey} — стоп")
        self.waveform.set_active(True)
        self._reposition()
        self.show()

    def show_transcribing(self) -> None:
        self._hide_timer.stop()
        self.title.setText("Распознаю…")
        self.hint.setText("почти готово")
        self.waveform.set_active(False)
        self._reposition()
        self.show()

    def show_done(self, message: str) -> None:
        self.title.setText(message)
        self.hint.setText("текст вставлен")
        self.waveform.set_active(False)
        self._hide_timer.start(1400)

    def show_error(self, message: str) -> None:
        self.title.setText(message)
        self.hint.setText("")
        self.waveform.set_active(False)
        self._reposition()
        self.show()
        self._hide_timer.start(2600)

    def push_level(self, level: float) -> None:
        self.waveform.push(level)
