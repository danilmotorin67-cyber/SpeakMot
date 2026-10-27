import time

from speakmot import mousehook


def test_only_side_buttons_are_decoded():
    down = mousehook.WM_XBUTTONDOWN
    up = mousehook.WM_XBUTTONUP
    assert mousehook.button_from_event(down, 1 << 16) == ("mouse4", True)
    assert mousehook.button_from_event(up, 2 << 16) == ("mouse5", False)
    assert mousehook.button_from_event(0x0201, 0) is None  # левая кнопка
    assert mousehook.button_from_event(down, 3 << 16) is None


def test_bound_button_is_swallowed_and_others_pass():
    """Назначенная кнопка не должна листать страницу назад в браузере."""
    calls = []
    hook = mousehook.MouseHook({"mouse4": (lambda: calls.append("down"), None)})
    import threading

    threading.Thread(target=hook._dispatch, daemon=True).start()
    assert hook.handle("mouse4", True) is True
    assert hook.handle("mouse4", False) is True  # отпускание тоже съедаем
    assert hook.handle("mouse5", True) is False  # чужая кнопка проходит
    deadline = time.monotonic() + 2
    while not calls and time.monotonic() < deadline:
        time.sleep(0.01)
    hook.stop()
    assert calls == ["down"]
