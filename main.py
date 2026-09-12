import sys


def selftest(report_path: str) -> int:
    """Проверяет, что собранное приложение может импортировать всё, что ему нужно.

    Сборка PyInstaller легко теряет C-расширения (например av._core у PyAV),
    и обнаруживается это только в момент распознавания. Проверка гоняет те же
    импорты заранее, поэтому падает на сборке, а не у пользователя.
    """
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
            lines.append(f"OK    {name}")
        except Exception as exc:
            failed = True
            lines.append(f"FAIL  {name}: {type(exc).__name__}: {exc}")

    report = "\n".join(lines)
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(report + "\n")
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        index = sys.argv.index("--selftest")
        path = sys.argv[index + 1] if len(sys.argv) > index + 1 else "selftest.txt"
        sys.exit(selftest(path))

    from speakmot.ui.app import SpeakMotApp

    sys.exit(SpeakMotApp().run())
