"""Работа с активным окном Windows. Вне Windows все функции безопасно пустые."""

import ctypes
import sys
from ctypes import wintypes

IS_WINDOWS = sys.platform == "win32"


def _user32():
    return ctypes.windll.user32


def foreground_window() -> int:
    if not IS_WINDOWS:
        return 0
    return int(_user32().GetForegroundWindow())


def focus_window(handle: int) -> None:
    """Возвращает фокус окну, которое было активно до нашего.

    Windows не даёт переднему плану произвольному процессу, поэтому окно
    сначала «будят» через AllowSetForegroundWindow-подобный трюк с потоками.
    """
    if not IS_WINDOWS or not handle:
        return
    user32 = _user32()
    try:
        current = ctypes.windll.kernel32.GetCurrentThreadId()
        target = user32.GetWindowThreadProcessId(handle, None)
        user32.AttachThreadInput(current, target, True)
        user32.SetForegroundWindow(handle)
        user32.AttachThreadInput(current, target, False)
    except Exception:
        pass


def window_title(handle: int | None = None) -> str:
    if not IS_WINDOWS:
        return ""
    user32 = _user32()
    handle = handle or foreground_window()
    if not handle:
        return ""
    length = user32.GetWindowTextLengthW(handle)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(handle, buffer, length + 1)
    return buffer.value


def process_name(handle: int | None = None) -> str:
    """Имя exe окна, например «code.exe»."""
    if not IS_WINDOWS:
        return ""
    handle = handle or foreground_window()
    if not handle:
        return ""
    try:
        pid = wintypes.DWORD()
        _user32().GetWindowThreadProcessId(handle, ctypes.byref(pid))
        kernel32 = ctypes.windll.kernel32
        # PROCESS_QUERY_LIMITED_INFORMATION
        process = kernel32.OpenProcess(0x1000, False, pid.value)
        if not process:
            return ""
        try:
            size = wintypes.DWORD(512)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(
                process, 0, buffer, ctypes.byref(size)
            ):
                return ""
            return buffer.value.rsplit("\\", 1)[-1]
        finally:
            kernel32.CloseHandle(process)
    except Exception:
        return ""
