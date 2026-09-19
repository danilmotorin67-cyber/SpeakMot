"""Журнал работы: без него любая поломка у пользователя разбирается вслепую."""

import logging
import platform
import sys
import threading
from logging.handlers import RotatingFileHandler

from . import __version__
from .config import CONFIG_DIR

LOG_PATH = CONFIG_DIR / "speakmot.log"
FORMAT = "%(asctime)s  %(levelname)-7s %(name)-18s %(message)s"


def log_path():
    return LOG_PATH


def setup(level: int = logging.INFO) -> None:
    """Включает запись в файл с ограничением размера."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    if any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        return

    handler = RotatingFileHandler(
        LOG_PATH, maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(FORMAT))
    root.addHandler(handler)
    root.setLevel(level)

    install_hooks()
    logging.getLogger("speakmot").info("--- запуск %s ---", environment())


def environment() -> str:
    """Строка с версиями — первое, что нужно знать при разборе ошибки."""
    parts = [f"SpeakMotor {__version__}", f"Python {platform.python_version()}",
             platform.platform()]
    try:
        import PySide6

        parts.append(f"PySide6 {PySide6.__version__}")
    except Exception:
        pass
    return " · ".join(parts)


def install_hooks() -> None:
    """Ловит исключения, которые иначе исчезли бы в окне без консоли."""
    logger = logging.getLogger("speakmot.crash")

    def handle(exc_type, exc_value, traceback):
        logger.error("необработанная ошибка", exc_info=(exc_type, exc_value, traceback))
        previous(exc_type, exc_value, traceback)

    previous = sys.excepthook
    sys.excepthook = handle

    def handle_thread(args):
        logger.error(
            "необработанная ошибка в потоке %s",
            args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = handle_thread
