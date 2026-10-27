"""Боковые кнопки мыши как горячая клавиша.

Библиотека keyboard слушает только клавиатуру, поэтому мышь перехватываем
сами — низкоуровневым хуком Windows. Выбранная кнопка «съедается»: иначе
браузер и проводник листали бы страницу назад, пока человек диктует.
Остальные кнопки проходят как обычно. Вне Windows хук ничего не делает.
"""

import ctypes
import logging
import queue
import sys
import threading

log = logging.getLogger("speakmot.mousehook")

IS_WINDOWS = sys.platform == "win32"

WH_MOUSE_LL = 14
WM_QUIT = 0x0012
WM_XBUTTONDOWN = 0x020B
WM_XBUTTONUP = 0x020C
XBUTTON_CODES = {1: "mouse4", 2: "mouse5"}


if IS_WINDOWS:
    from ctypes import wintypes

    LRESULT = ctypes.c_ssize_t
    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    class MSLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("pt", wintypes.POINT),
            ("mouseData", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        ]

    def _api():
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # без явных типов 64-битные дескрипторы обрезаются до 32 бит
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            HOOKPROC,
            wintypes.HINSTANCE,
            wintypes.DWORD,
        ]
        user32.SetWindowsHookExW.restype = wintypes.HHOOK
        user32.CallNextHookEx.argtypes = [
            wintypes.HHOOK,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallNextHookEx.restype = LRESULT
        user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        return user32, kernel32


def button_from_event(message: int, mouse_data: int) -> tuple[str, bool] | None:
    """Какая боковая кнопка и нажата ли она. Прочие события — None."""
    if message not in (WM_XBUTTONDOWN, WM_XBUTTONUP):
        return None
    name = XBUTTON_CODES.get((mouse_data >> 16) & 0xFFFF)
    if name is None:
        return None
    return name, message == WM_XBUTTONDOWN


class MouseHook:
    """Слушает боковые кнопки мыши.

    bindings: {"mouse4": (on_down, on_up)}, on_up может быть None.
    Колбэки вызываются из отдельного потока: процедура хука обязана
    возвращаться мгновенно, иначе Windows молча снимает хук.
    """

    def __init__(self, bindings: dict):
        self.bindings = dict(bindings)
        self._events: queue.Queue = queue.Queue()
        self._thread_id = 0
        self._ready = threading.Event()
        self._hook = None
        self._proc = None
        self.error: str = ""

    def start(self) -> bool:
        if not IS_WINDOWS or not self.bindings:
            return False
        threading.Thread(target=self._dispatch, daemon=True).start()
        threading.Thread(target=self._loop, daemon=True).start()
        self._ready.wait(3)
        return self._hook is not None

    def stop(self) -> None:
        self._events.put(None)
        if IS_WINDOWS and self._thread_id:
            user32, _ = _api()
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._thread_id = 0

    def handle(self, button: str, pressed: bool) -> bool:
        """Ставит событие в очередь. True — кнопку надо «съесть»."""
        if button not in self.bindings:
            return False
        self._events.put((button, pressed))
        return True

    def _dispatch(self) -> None:
        while True:
            item = self._events.get()
            if item is None:
                return
            button, pressed = item
            on_down, on_up = self.bindings[button]
            callback = on_down if pressed else on_up
            if callback is None:
                continue
            try:
                callback()
            except Exception:
                log.exception("обработчик кнопки мыши %s упал", button)

    def _loop(self) -> None:
        user32, kernel32 = _api()

        def procedure(code, wparam, lparam):
            if code == 0:
                info = ctypes.cast(lparam, ctypes.POINTER(MSLLHOOKSTRUCT)).contents
                found = button_from_event(wparam, info.mouseData)
                if found and self.handle(*found):
                    return 1
            return user32.CallNextHookEx(None, code, wparam, lparam)

        # ссылку держим, иначе сборщик мусора уничтожит колбэк под хуком
        self._proc = HOOKPROC(procedure)
        self._thread_id = kernel32.GetCurrentThreadId()
        self._hook = user32.SetWindowsHookExW(
            WH_MOUSE_LL, self._proc, kernel32.GetModuleHandleW(None), 0
        )
        if not self._hook:
            self.error = f"SetWindowsHookExW: ошибка {ctypes.get_last_error()}"
            log.error("хук мыши не установился: %s", self.error)
            self._ready.set()
            return
        log.info("хук мыши установлен: %s", ", ".join(self.bindings))
        self._ready.set()

        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            pass
        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
        log.info("хук мыши снят")
