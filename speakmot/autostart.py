import contextlib
import sys
from pathlib import Path

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SpeakMot"


def launch_command() -> str:
    """Команда запуска приложения — для собранного exe и для запуска из исходников."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable)}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interpreter = pythonw if pythonw.exists() else Path(sys.executable)
    main_script = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{interpreter}" "{main_script}"'


def _open_key(access):
    import winreg

    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, access)


def is_enabled() -> bool:
    try:
        import winreg

        with _open_key(winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
        return True
    except (ImportError, OSError):
        return False


def set_enabled(enabled: bool) -> None:
    """Включает или выключает запуск вместе с Windows. Вне Windows — ничего не делает."""
    try:
        import winreg
    except ImportError:
        return

    with _open_key(winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            with contextlib.suppress(FileNotFoundError):
                winreg.DeleteValue(key, APP_NAME)
