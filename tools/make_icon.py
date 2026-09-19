"""Собирает assets/icon.ico из того же рисунка, что показывает программа.

Запуск: QT_QPA_PLATFORM=offscreen python tools/make_icon.py
"""

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray
from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from speakmot.branding import mark_pixmap  # noqa: E402

SIZES = (16, 24, 32, 48, 64, 128, 256)


def png_bytes(size: int) -> bytes:
    store = QByteArray()
    buffer = QBuffer(store)
    buffer.open(QBuffer.WriteOnly)
    mark_pixmap(size).save(buffer, "PNG")
    buffer.close()
    return bytes(store)


def build_ico(path: Path) -> None:
    images = [(size, png_bytes(size)) for size in SIZES]
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, payload = b"", b""
    for size, data in images:
        entries += struct.pack(
            "<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32, len(data), offset
        )
        payload += data
        offset += len(data)
    path.write_bytes(header + entries + payload)


if __name__ == "__main__":
    QApplication(sys.argv)
    target = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
    target.parent.mkdir(exist_ok=True)
    build_ico(target)
    print(f"готово: {target} ({target.stat().st_size} байт)")
