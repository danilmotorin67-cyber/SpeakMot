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
    QFont,
    QFontMetricsF,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import icons, theme

FONT_FAMILIES = [name.strip() for name in theme.FONT.split(",")]


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
        # поля слева и справа одинаковые, иначе шарик «выпадает» из дорожки
        margin, knob = 3.0, self.height() - 6.0
        travel = self.width() - knob - 2 * margin
        painter.drawEllipse(QRectF(margin + self._offset * travel, margin, knob, knob))


class BrandMark(QWidget):
    """Название программы контурными буквами — как на трафарете.

    Обычная подпись в таком начертании выглядела бы плоско: буквы рисуются
    контуром по акцентному цвету, без заливки.
    """

    def __init__(self, text: str = "SPEAKMOTOR", parent=None):
        super().__init__(parent)
        self._text = text
        self._font = QFont(FONT_FAMILIES[0])
        self._font.setPixelSize(25)
        self._font.setWeight(QFont.Weight.Bold)
        self._font.setLetterSpacing(QFont.AbsoluteSpacing, 2.0)
        self.setMinimumHeight(34)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def refresh_theme(self) -> None:
        self.update()

    def _path(self) -> QPainterPath:
        path = QPainterPath()
        metrics = QFontMetricsF(self._font)
        path.addText(0.0, metrics.ascent(), self._font, self._text)
        return path

    # буквы сжимаем по ширине и вытягиваем вверх — трафаретное начертание
    SQUEEZE, STRETCH = 0.82, 1.18

    def sizeHint(self) -> QSize:
        rect = self._path().boundingRect()
        return QSize(int(rect.width() * self.SQUEEZE) + 6, 34)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = self._path()
        rect = path.boundingRect()
        height = rect.height() * self.STRETCH
        painter.translate(1.5, (self.height() - height) / 2)
        painter.scale(self.SQUEEZE, self.STRETCH)
        painter.translate(-rect.left(), -rect.top())
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(theme.color("accent")), 1.2 / self.STRETCH))
        painter.drawPath(path)


class QuietComboBox(QComboBox):
    """Список, который не переключается колесом мыши.

    Прокрутка страницы над таким полем меняла настройку незаметно для
    человека — значение меняется только щелчком по самому списку.
    """

    def wheelEvent(self, event):
        event.ignore()


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


class StatTile(QFrame):
    """Плитка с крупным числом и подписью."""

    def __init__(self, value: str, caption: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statTile")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(2)

        self.value = QLabel(value)
        self.value.setObjectName("statValue")
        self.value.setAlignment(Qt.AlignCenter)
        caption_label = QLabel(caption)
        caption_label.setObjectName("statCaption")
        caption_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.value)
        layout.addWidget(caption_label)

    def set_value(self, value: str) -> None:
        self.value.setText(value)


class EmptyState(QWidget):
    """Заглушка для пустого раздела: значок, заголовок и подсказка."""

    def __init__(self, icon_name: str, title: str, hint: str, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.addStretch(1)

        glyph = QLabel()
        glyph.setAlignment(Qt.AlignCenter)
        glyph.setPixmap(icons.icon(icon_name, 44, theme.color("text_faint")).pixmap(44, 44))
        layout.addWidget(glyph)

        heading = QLabel(title)
        heading.setObjectName("emptyTitle")
        heading.setAlignment(Qt.AlignCenter)
        layout.addWidget(heading)

        message = QLabel(hint)
        message.setObjectName("emptyHint")
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)
        layout.addWidget(message)
        layout.addStretch(1)


def divider() -> QFrame:
    """Тонкая линия между строками настроек."""
    line = QFrame()
    line.setObjectName("divider")
    line.setFixedHeight(1)
    return line


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

        # тонкие расходящиеся кольца во время записи
        if self._recording:
            for offset in (0.0, 0.5):
                phase = (self._pulse + offset) % 1.0
                ring = radius + 4 + phase * 22
                line = QColor(base)
                line.setAlphaF(max(0.0, 0.45 * (1.0 - phase)))
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(line, 1.0))
                painter.drawEllipse(center, ring, ring)

        filled = self._recording or self._hover
        painter.setPen(QPen(base, 1.4))
        painter.setBrush(base if filled else Qt.NoBrush)
        painter.drawEllipse(center, radius, radius)

        ink = theme.color("on_accent") if filled else base.name()
        painter.setPen(Qt.NoPen)
        cx, cy = center.x(), center.y()
        if self._recording:
            painter.setBrush(QColor(ink))
            painter.drawRect(QRectF(cx - 10, cy - 10, 20, 20))
        else:
            icons.draw(painter, "mic", QRectF(cx - 23, cy - 23, 46, 46), ink)
