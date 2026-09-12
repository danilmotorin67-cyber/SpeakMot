import math
from collections import deque

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from . import theme


class Card(QFrame):
    """Скруглённая карточка-контейнер с необязательным заголовком."""

    def __init__(self, title: str | None = None, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(18, 16, 18, 16)
        self._layout.setSpacing(10)
        if title:
            label = QLabel(title.upper())
            label.setObjectName("cardTitle")
            self._layout.addWidget(label)

    def body(self) -> QVBoxLayout:
        return self._layout

    def add(self, widget: QWidget) -> None:
        self._layout.addWidget(widget)


class ToggleSwitch(QWidget):
    """Переключатель в стиле iOS."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._offset = 1.0 if checked else 0.0
        self.setFixedSize(46, 26)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, value: float) -> None:
        self._offset = value
        self.update()

    offset = Property(float, get_offset, set_offset)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        if value == self._checked:
            return
        self._checked = value
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if value else 0.0)
        self._anim.start()

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track_off = QColor(theme.color("surface2"))
        track_on = QColor(theme.color("accent"))
        color = QColor(
            int(track_off.red() + (track_on.red() - track_off.red()) * self._offset),
            int(track_off.green() + (track_on.green() - track_off.green()) * self._offset),
            int(track_off.blue() + (track_on.blue() - track_off.blue()) * self._offset),
        )
        painter.setPen(QPen(QColor(theme.color("border")), 1))
        painter.setBrush(color)
        painter.drawRoundedRect(QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), 13, 13)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        x = 3 + self._offset * (self.width() - 23)
        painter.drawEllipse(QRectF(x, 3, 20, 20))


class Waveform(QWidget):
    """Полосы, отражающие громкость микрофона в реальном времени."""

    def __init__(self, bars: int = 28, parent=None):
        super().__init__(parent)
        self._levels = deque([0.0] * bars, maxlen=bars)
        self._bars = bars
        self._phase = 0.0
        self._active = False
        self.setMinimumHeight(34)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(45)

    def set_active(self, active: bool) -> None:
        self._active = active
        if not active:
            self._levels = deque([0.0] * self._bars, maxlen=self._bars)
        self.update()

    def push(self, level: float) -> None:
        self._levels.append(min(1.0, level * 3.2))

    def _tick(self) -> None:
        self._phase += 0.28
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        count = len(self._levels)
        if count == 0:
            return
        gap = 3
        width = max(2.0, (self.width() - gap * (count - 1)) / count)
        middle = self.height() / 2
        accent = QColor(theme.color("accent"))

        for index, level in enumerate(self._levels):
            if self._active:
                # лёгкое колебание, чтобы полосы жили даже в тишине
                wobble = 0.22 + 0.12 * math.sin(self._phase + index * 0.5)
                amplitude = max(wobble, level)
            else:
                amplitude = 0.06
            height = max(3.0, amplitude * (self.height() - 4))
            color = QColor(accent)
            color.setAlphaF(0.35 + 0.65 * min(1.0, amplitude))
            painter.setBrush(color)
            x = index * (width + gap)
            painter.drawRoundedRect(
                QRectF(x, middle - height / 2, width, height), width / 2, width / 2
            )


class MicButton(QWidget):
    """Большая круглая кнопка записи с пульсацией."""

    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(112, 112)
        self.setCursor(Qt.PointingHandCursor)
        self._recording = False
        self._pulse = 0.0
        self._hover = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(38)
        self._shadow.setOffset(0, 6)
        self.refresh_theme()
        self.setGraphicsEffect(self._shadow)

    def refresh_theme(self) -> None:
        glow = QColor(theme.color("accent"))
        glow.setAlpha(90)
        self._shadow.setColor(glow)
        self.update()

    def set_recording(self, recording: bool) -> None:
        self._recording = recording
        if recording:
            self._timer.start(33)
        else:
            self._timer.stop()
            self._pulse = 0.0
        self.update()

    def _tick(self) -> None:
        self._pulse = (self._pulse + 0.05) % 1.0
        self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self.update()

    def mousePressEvent(self, event):
        if self.isEnabled():
            self.clicked.emit()

    def sizeHint(self) -> QSize:
        return QSize(112, 112)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        radius = 44.0

        if self._recording:
            ring = radius + 6 + self._pulse * 16
            color = QColor(theme.color("danger"))
            color.setAlphaF(max(0.0, 0.35 * (1.0 - self._pulse)))
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawEllipse(center, ring, ring)

        base = QColor(theme.color("danger") if self._recording else theme.color("accent"))
        if self._hover:
            base = base.lighter(112)
        painter.setPen(Qt.NoPen)
        painter.setBrush(base)
        painter.drawEllipse(center, radius, radius)

        painter.setPen(QPen(QColor("#ffffff"), 3.2, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        cx, cy = center.x(), center.y()
        if self._recording:
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(cx - 11, cy - 11, 22, 22), 5, 5)
        else:
            capsule = QRectF(cx - 9, cy - 20, 18, 26)
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(capsule, 9, 9)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#ffffff"), 3.2, Qt.SolidLine, Qt.RoundCap))
            arc = QPainterPath()
            arc.arcMoveTo(QRectF(cx - 16, cy - 12, 32, 32), 200)
            arc.arcTo(QRectF(cx - 16, cy - 12, 32, 32), 200, 140)
            painter.drawPath(arc)
            painter.drawLine(cx, cy + 20, cx, cy + 26)


def row(*widgets: QWidget, spacing: int = 10) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    return container
