import time

import keyboard
import pyperclip


def paste_text(text: str) -> None:
    """Кладёт текст в буфер обмена и вставляет его в активное окно через Ctrl+V.

    Прежнее содержимое буфера восстанавливается — вставка не должна
    затирать то, что пользователь скопировал раньше.
    """
    if not text:
        return
    try:
        previous = pyperclip.paste()
    except Exception:
        previous = None

    pyperclip.copy(text)
    time.sleep(0.05)
    keyboard.send("ctrl+v")

    if previous is not None:
        time.sleep(0.3)
        try:
            pyperclip.copy(previous)
        except Exception:
            pass


def copy_text(text: str) -> None:
    if text:
        pyperclip.copy(text)


def beep(start: bool) -> None:
    try:
        import winsound

        winsound.Beep(880 if start else 620, 90)
    except Exception:
        pass
