"""Значок программы: один рисунок для трея, окна и файла .ico."""

import contextlib
import ctypes
import sys
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

APP_ID = "SpeakMotor.Dictation"
ACCENT = "#e2603c"
BACKDROP = "#141110"


def resource_path(relative: str) -> Path:
    """Путь к файлу рядом с программой — и в исходниках, и внутри сборки."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parent.parent
    return root / relative


ICON_FILE = "assets/icon.ico"


def mark_pixmap(size: int, color: str = ACCENT) -> QPixmap:
    """Квадрат с микрофоном. Пропорции подобраны так, чтобы читалось и в 16 px."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    scale = size / 64.0
    painter.scale(scale, scale)

    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(BACKDROP))
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 14, 14)

    painter.setBrush(QColor(color))
    painter.drawRoundedRect(QRectF(26, 13, 12, 22), 6, 6)
    painter.drawRoundedRect(QRectF(30.5, 40, 3, 8), 1.5, 1.5)
    painter.drawRoundedRect(QRectF(22, 48, 20, 3), 1.5, 1.5)

    # дужка микрофона
    pen = QPen(QColor(color), 3.4, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawArc(QRectF(20, 20, 24, 22), 180 * 16, 180 * 16)
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    """Готовый .ico, если он рядом, иначе рисуем на лету."""
    path = resource_path(ICON_FILE)
    if path.exists():
        icon = QIcon(str(path))
        if not icon.isNull():
            return icon
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(mark_pixmap(size))
    return icon


def set_app_user_model_id() -> None:
    """Без своего идентификатора Windows показывает в панели значок Python."""
    if sys.platform != "win32":
        return
    # значок — не повод падать
    with contextlib.suppress(Exception):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
