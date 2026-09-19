import logging

import speakmot.journal as journal


def test_writes_a_file_and_records_the_environment(tmp_path, monkeypatch):
    monkeypatch.setattr(journal, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(journal, "LOG_PATH", tmp_path / "speakmot.log")

    root = logging.getLogger()
    saved = list(root.handlers)
    try:
        root.handlers.clear()
        journal.setup()
        logging.getLogger("speakmot.test").warning("проверка записи")
        for handler in root.handlers:
            handler.flush()
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers[:] = saved

    written = (tmp_path / "speakmot.log").read_text(encoding="utf-8")
    assert "проверка записи" in written
    assert "запуск" in written
    assert "SpeakMotor" in written


def test_environment_names_the_versions():
    line = journal.environment()
    assert "SpeakMotor" in line
    assert "Python" in line


def test_thread_errors_are_written_down(tmp_path, monkeypatch):
    """Ошибка в фоновом потоке без журнала исчезает бесследно."""
    import threading

    monkeypatch.setattr(journal, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(journal, "LOG_PATH", tmp_path / "speakmot.log")

    root = logging.getLogger()
    saved, saved_hook = list(root.handlers), threading.excepthook
    try:
        root.handlers.clear()
        journal.setup()

        def boom():
            raise ValueError("поломка в потоке")

        thread = threading.Thread(target=boom)
        thread.start()
        thread.join()
        for handler in root.handlers:
            handler.flush()
    finally:
        for handler in root.handlers:
            handler.close()
        root.handlers[:] = saved
        threading.excepthook = saved_hook

    written = (tmp_path / "speakmot.log").read_text(encoding="utf-8")
    assert "поломка в потоке" in written
