import io
import sys


def ensure_streams() -> None:
    """Подставляет заглушки вместо отсутствующих потоков вывода.

    В сборке PyInstaller с ключом --windowed у процесса нет консоли, поэтому
    sys.stdout и sys.stderr равны None. Любая библиотека, которая печатает
    прогресс или предупреждение, падает на этом с AttributeError.
    """
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            setattr(sys, name, io.StringIO())


def selftest(report_path: str) -> int:
    """Проверяет, что собранное приложение умеет всё, что нужно в бою.

    Сначала импорты (сборка легко теряет C-расширения вроде av._core), затем
    настоящее скачивание самой маленькой модели — причём с отключёнными
    потоками вывода, как в реальном окне без консоли.
    """
    from speakmot import models

    lines = []
    failed = False
    checks = [
        ("faster_whisper", lambda: __import__("faster_whisper").WhisperModel),
        ("av", lambda: __import__("av").open),
        ("ctranslate2", lambda: __import__("ctranslate2").get_cuda_device_count()),
        ("huggingface_hub", lambda: __import__("huggingface_hub").snapshot_download),
        ("sounddevice", lambda: __import__("sounddevice").query_devices),
        ("keyboard", lambda: __import__("keyboard").add_hotkey),
        ("tokenizers", lambda: __import__("tokenizers").Tokenizer),
    ]
    for name, probe in checks:
        try:
            probe()
            lines.append(f"OK    импорт {name}")
        except Exception as exc:
            failed = True
            lines.append(f"FAIL  импорт {name}: {type(exc).__name__}: {exc}")

    percents: list[int] = []
    saved = sys.stdout, sys.stderr
    try:
        # воспроизводим окно без консоли: так ловится вывод в несуществующий поток
        sys.stdout = sys.stderr = None
        models.download("tiny", percents.append)
        installed = models.is_installed("tiny")
    except Exception as exc:
        installed = False
        failed = True
        error = f"{type(exc).__name__}: {exc}"
    else:
        error = ""
    finally:
        sys.stdout, sys.stderr = saved

    if error:
        lines.append(f"FAIL  загрузка модели tiny: {error}")
    elif not installed:
        failed = True
        lines.append("FAIL  загрузка модели tiny: файлы не появились на диске")
    else:
        lines.append(f"OK    загрузка модели tiny, шагов прогресса: {len(percents)}")

    if installed:
        line = _check_transcription()
        failed = failed or line.startswith("FAIL")
        lines.append(line)

    line = _check_icon()
    failed = failed or line.startswith("FAIL")
    lines.append(line)

    for line in _check_windows_paths():
        failed = failed or line.startswith("FAIL")
        lines.append(line)

    report = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report + "\n")
    print(report)
    return 1 if failed else 0


def _check_icon() -> str:
    """Без файла .ico панель задач рисует пустой квадрат."""
    from speakmot import branding

    path = branding.resource_path(branding.ICON_FILE)
    if not path.exists():
        return f"FAIL  значок: файл {path} не попал в сборку"
    return f"OK    значок: {path.name}, {path.stat().st_size} байт"


def _check_transcription() -> str:
    """Прогоняет через модель настоящий звук.

    Импорт библиотеки ещё ничего не доказывает: ctranslate2 и tokenizers
    подтягивают свои DLL уже при создании модели, а распознавание — единственный
    путь, который это выполняет.
    """
    import numpy as np

    from speakmot.config import Config
    from speakmot.transcriber import Transcriber

    try:
        cfg = Config()
        cfg.model_size = "tiny"
        cfg.language = "en"
        transcriber = Transcriber(cfg)

        seconds, rate = 2.0, 16000
        time_axis = np.linspace(0, seconds, int(rate * seconds), dtype=np.float32)
        # тон с затуханием: распознать нечего, но весь конвейер отрабатывает
        audio = (0.2 * np.sin(2 * np.pi * 220 * time_axis) * np.exp(-time_axis)).astype(
            np.float32
        )

        text = transcriber.transcribe(audio)
    except Exception as exc:
        return f"FAIL  распознавание: {type(exc).__name__}: {exc}"

    if not isinstance(text, str):
        return f"FAIL  распознавание: вернулся {type(text).__name__}, а не строка"
    return f"OK    распознавание отработало, символов в ответе: {len(text)}"


def _check_windows_paths() -> list[str]:
    """Проверяет то, что работает только на Windows и только у пользователя.

    Горячие клавиши, буфер обмена и автозапуск живут вне нашего кода, и
    сломаться могут молча — здесь они хотя бы раз выполняются по-настоящему.
    """
    if sys.platform != "win32":
        return ["SKIP  проверки Windows: выполняются только на Windows"]

    results = []

    try:
        import keyboard

        handle = keyboard.add_hotkey("ctrl+alt+f24", lambda: None, suppress=False)
        keyboard.remove_hotkey(handle)
        results.append("OK    назначение горячей клавиши")
    except Exception as exc:
        results.append(f"FAIL  назначение горячей клавиши: {type(exc).__name__}: {exc}")

    try:
        import pyperclip

        previous = pyperclip.paste()
        pyperclip.copy("проверка буфера SpeakMotor")
        restored = pyperclip.paste()
        pyperclip.copy(previous)
        if restored == "проверка буфера SpeakMotor":
            results.append("OK    буфер обмена")
        else:
            results.append(f"FAIL  буфер обмена: прочитано {restored!r}")
    except Exception as exc:
        results.append(f"FAIL  буфер обмена: {type(exc).__name__}: {exc}")

    try:
        from speakmot import autostart

        was_enabled = autostart.is_enabled()
        autostart.set_enabled(True)
        turned_on = autostart.is_enabled()
        autostart.set_enabled(was_enabled)
        if turned_on:
            results.append("OK    автозапуск через реестр")
        else:
            results.append("FAIL  автозапуск: запись не появилась в реестре")
    except Exception as exc:
        results.append(f"FAIL  автозапуск: {type(exc).__name__}: {exc}")

    return results


if __name__ == "__main__":
    ensure_streams()

    from speakmot import journal

    journal.setup()

    if "--selftest" in sys.argv:
        index = sys.argv.index("--selftest")
        path = sys.argv[index + 1] if len(sys.argv) > index + 1 else "selftest.txt"
        sys.exit(selftest(path))

    from speakmot.ui.app import SpeakMotApp

    sys.exit(SpeakMotApp().run())
