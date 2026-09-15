import math
from collections import deque

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QLinearGradient,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme


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


class NavButton(QPushButton):
    """Пункт бокового меню.

    Раньше и значок, и подпись рисовались вручную в paintEvent — на Windows
    подпись пропадала. Теперь это обычная кнопка: Qt рисует текст сам, а от
    нас только готовая иконка.
    """

    def __init__(self, label: str, icon_name: str, parent=None):
        super().__init__(label, parent)
        self.setObjectName("navBtn")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(18, 18))
        self._icon_name = icon_name
        # группа снимает отметку с соседней кнопки из C++, минуя наши методы,
        # поэтому слушаем сигнал, а не переопределяем setChecked
        self.toggled.connect(lambda _checked: self.refresh_icon())
        self.refresh_icon()

    def refresh_icon(self) -> None:
        tint = theme.color("text") if self.isChecked() else theme.color("text_dim")
        self.setIcon(icons.icon(self._icon_name, 18, tint))


class StatusDot(QWidget):
    """Цветная точка состояния с мягким ореолом."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self._color = theme.color("success")

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        halo = QColor(self._color)
        halo.setAlpha(60)
        painter.setBrush(halo)
        painter.drawEllipse(self.rect())
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(self.rect().adjusted(3, 3, -3, -3))


class Waveform(QWidget):
    """Полосы, отражающие громкость микрофона в реальном времени."""

    def __init__(self, bars: int = 28, parent=None):
        super().__init__(parent)
        self._levels = deque([0.0] * bars, maxlen=bars)
        self._bars = bars
        self._phase = 0.0
        self._active = False
        self._role = "accent"
        self.setMinimumHeight(34)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(45)

    def set_role(self, role: str) -> None:
        self._role = role
        self.update()

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
        accent = QColor(theme.color(self._role))

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
        self.setFixedSize(150, 150)
        self.setCursor(Qt.PointingHandCursor)
        self._recording = False
        self._pulse = 0.0
        self._hover = False
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def refresh_theme(self) -> None:
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
        return QSize(150, 150)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(self.rect().center())
        radius = 46.0
        base = QColor(theme.color("danger") if self._recording else theme.color("accent"))

        # расходящиеся кольца во время записи
        if self._recording:
            for offset in (0.0, 0.5):
                phase = (self._pulse + offset) % 1.0
                ring = radius + 4 + phase * 22
                glow = QColor(base)
                glow.setAlphaF(max(0.0, 0.30 * (1.0 - phase)))
                painter.setPen(Qt.NoPen)
                painter.setBrush(glow)
                painter.drawEllipse(center, ring, ring)

        # мягкая подложка под кнопкой
        halo = QRadialGradient(center, radius * 1.55)
        soft = QColor(base)
        soft.setAlpha(34 if self._hover else 22)
        halo.setColorAt(0.62, soft)
        soft_edge = QColor(base)
        soft_edge.setAlpha(0)
        halo.setColorAt(1.0, soft_edge)
        painter.setPen(Qt.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(center, radius * 1.55, radius * 1.55)

        gradient = QLinearGradient(
            center.x(), center.y() - radius, center.x(), center.y() + radius
        )
        top = base.lighter(122 if self._hover else 114)
        gradient.setColorAt(0.0, top)
        gradient.setColorAt(1.0, base.darker(112))
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)

        # тонкий блик по верхней кромке
        rim = QColor("#ffffff")
        rim.setAlpha(38)
        painter.setPen(QPen(rim, 1.4))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, radius - 0.7, radius - 0.7)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        cx, cy = center.x(), center.y()
        if self._recording:
            painter.drawRoundedRect(QRectF(cx - 11, cy - 11, 22, 22), 6, 6)
        else:
            icons.draw(painter, "mic", QRectF(cx - 23, cy - 23, 46, 46), "#ffffff")
