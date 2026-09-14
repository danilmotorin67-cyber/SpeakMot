"""Иконки рисуются кодом: никаких файлов, любой цвет и размер."""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen


def _pen(color: str, width: float = 1.7) -> QPen:
    pen = QPen(color)
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def draw(painter: QPainter, name: str, rect: QRectF, color: str) -> None:
    """Рисует иконку внутри прямоугольника. Сетка условно 24×24."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    painter.translate(rect.topLeft())
    painter.scale(rect.width() / 24.0, rect.height() / 24.0)
    painter.setPen(_pen(color))
    painter.setBrush(Qt.NoBrush)

    drawer = _ICONS.get(name)
    if drawer:
        drawer(painter, color)
    painter.restore()


def _microphone(painter: QPainter, color: str) -> None:
    painter.drawRoundedRect(QRectF(9, 3, 6, 11), 3, 3)
    path = QPainterPath()
    path.arcMoveTo(QRectF(5, 8, 14, 12), 200)
    path.arcTo(QRectF(5, 8, 14, 12), 200, 140)
    painter.drawPath(path)
    painter.drawLine(QPointF(12, 18), QPointF(12, 21))


def _clock(painter: QPainter, color: str) -> None:
    painter.drawEllipse(QRectF(3.5, 3.5, 17, 17))
    painter.drawLine(QPointF(12, 7.5), QPointF(12, 12))
    painter.drawLine(QPointF(12, 12), QPointF(15.5, 14))


def _box(painter: QPainter, color: str) -> None:
    painter.drawRoundedRect(QRectF(3.5, 7, 17, 13), 2.5, 2.5)
    painter.drawLine(QPointF(3.5, 11.5), QPointF(20.5, 11.5))
    painter.drawLine(QPointF(8, 4), QPointF(8, 7))
    painter.drawLine(QPointF(16, 4), QPointF(16, 7))


def _sliders(painter: QPainter, color: str) -> None:
    for y in (7.0, 12.0, 17.0):
        painter.drawLine(QPointF(4, y), QPointF(20, y))
    painter.setBrush(color)
    for x, y in ((9.0, 7.0), (15.0, 12.0), (7.5, 17.0)):
        painter.drawEllipse(QPointF(x, y), 2.4, 2.4)
    painter.setBrush(Qt.NoBrush)


def _gear(painter: QPainter, color: str) -> None:
    painter.drawEllipse(QRectF(9, 9, 6, 6))
    painter.drawEllipse(QRectF(4.5, 4.5, 15, 15))
    for angle in range(0, 360, 45):
        path = QPainterPath()
        path.arcMoveTo(QRectF(4.5, 4.5, 15, 15), angle)
        start = path.currentPosition()
        path.arcMoveTo(QRectF(2.6, 2.6, 18.8, 18.8), angle)
        painter.drawLine(start, path.currentPosition())


def _search(painter: QPainter, color: str) -> None:
    painter.drawEllipse(QRectF(4, 4, 12, 12))
    painter.drawLine(QPointF(15, 15), QPointF(20, 20))


def _copy(painter: QPainter, color: str) -> None:
    painter.drawRoundedRect(QRectF(8, 8, 12, 12), 2.5, 2.5)
    path = QPainterPath()
    path.moveTo(5.5, 15.5)
    path.lineTo(4, 15.5)
    path.arcTo(QRectF(4, 4, 4, 4), 180, -90)
    path.lineTo(15.5, 4)
    painter.drawPath(path)


def _download(painter: QPainter, color: str) -> None:
    painter.drawLine(QPointF(12, 4), QPointF(12, 14))
    painter.drawLine(QPointF(8, 10.5), QPointF(12, 14.5))
    painter.drawLine(QPointF(16, 10.5), QPointF(12, 14.5))
    painter.drawLine(QPointF(5, 19), QPointF(19, 19))


_ICONS = {
    "mic": _microphone,
    "clock": _clock,
    "box": _box,
    "sliders": _sliders,
    "gear": _gear,
    "search": _search,
    "copy": _copy,
    "download": _download,
}
