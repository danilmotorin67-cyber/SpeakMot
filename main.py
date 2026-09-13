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

    report = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report + "\n")
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    ensure_streams()

    if "--selftest" in sys.argv:
        index = sys.argv.index("--selftest")
        path = sys.argv[index + 1] if len(sys.argv) > index + 1 else "selftest.txt"
        sys.exit(selftest(path))

    from speakmot.ui.app import SpeakMotApp

    sys.exit(SpeakMotApp().run())
