import sys
import threading
import time

import numpy as np
import pytest


@pytest.fixture
def engine_module(monkeypatch, tmp_path):
    keyboard = type(sys)("keyboard")
    keyboard.add_hotkey = lambda *a, **k: object()
    keyboard.remove_hotkey = lambda handle: None
    keyboard.hook = lambda *a, **k: object()
    keyboard.unhook = lambda handle: None
    monkeypatch.setitem(sys.modules, "keyboard", keyboard)
    pyperclip = type(sys)("pyperclip")
    pyperclip.copy = lambda text: None
    pyperclip.paste = lambda: ""
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)

    from speakmot import config

    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json", raising=False)

    import speakmot.engine as engine

    monkeypatch.setattr(engine, "TRANSCRIBE_TIMEOUT_BASE", 0.3)
    monkeypatch.setattr(engine, "TRANSCRIBE_TIMEOUT_PER_SECOND", 0.0)
    return engine


class _Recorder:
    is_recording = True

    def stop(self):
        self.is_recording = False
        return np.zeros(16000, dtype=np.float32)


class _StuckTranscriber:
    """Ведёт себя как модель на видеокарте без cuDNN: вызов не возвращается."""

    device_in_use = "cuda"

    def __init__(self):
        self.release = threading.Event()

    def transcribe(self, *args, **kwargs):
        self.release.wait(5)
        return "поздний текст"


def _wait_for(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_hung_transcription_does_not_hang_forever(engine_module, monkeypatch):
    from speakmot.config import Config

    states = []
    results = []
    cfg = Config()
    cfg.sound_feedback = False
    cfg.preview_before_paste = True
    engine = engine_module.Engine(
        cfg, on_state=lambda s, m: states.append((s, m)), on_result=results.append
    )
    engine.recorder = _Recorder()
    stuck = _StuckTranscriber()
    engine.transcriber = stuck

    engine.stop_and_transcribe()

    assert _wait_for(lambda: engine.state == engine_module.ERROR)
    assert "зависло" in states[-1][1]
    # следующая попытка идёт на процессоре и на свежем экземпляре модели
    assert cfg.device == "cpu"
    assert engine.transcriber is not stuck

    # запоздавший ответ зависшего вызова не должен никуда попасть
    stuck.release.set()
    time.sleep(0.3)
    assert results == []
    assert engine.state == engine_module.ERROR


def test_normal_transcription_is_not_interrupted(engine_module):
    from speakmot.config import Config

    class _Quick:
        device_in_use = "cpu"

        def transcribe(self, *args, **kwargs):
            return "привет"

    cfg = Config()
    cfg.sound_feedback = False
    cfg.preview_before_paste = True
    results = []
    engine = engine_module.Engine(cfg, on_result=results.append)
    engine.recorder = _Recorder()
    engine.transcriber = _Quick()

    engine.stop_and_transcribe()

    assert _wait_for(lambda: results == ["Привет"] or results == ["привет"])
    time.sleep(0.5)  # дольше, чем срок сторожа
    assert engine.state == engine_module.IDLE


def test_gpu_without_cuda_libraries_falls_back_to_cpu(monkeypatch):
    """Видеокарта есть, а cuDNN нет — считать надо на процессоре."""
    import speakmot.transcriber as transcriber
    from speakmot.config import Config

    ct2 = type(sys)("ctranslate2")
    ct2.get_cuda_device_count = lambda: 1
    monkeypatch.setitem(sys.modules, "ctranslate2", ct2)
    monkeypatch.setattr(transcriber.sys, "platform", "win32")

    def missing(name):
        raise OSError(f"{name} not found")

    monkeypatch.setattr(transcriber.ctypes, "WinDLL", missing, raising=False)

    assert transcriber.cuda_usable() is False
    device, compute = transcriber.Transcriber(Config())._resolve_device()
    assert (device, compute) == ("cpu", "int8")


def test_mouse_hotkey_uses_the_mouse_hook(engine_module, monkeypatch):
    from speakmot.config import Config

    installed = {}

    class FakeHook:
        def __init__(self, bindings):
            installed.update(bindings)
            self.error = ""

        def start(self):
            return True

        def stop(self):
            installed.clear()

    monkeypatch.setattr(engine_module.mousehook, "MouseHook", FakeHook)
    keyboard_calls = []
    monkeypatch.setattr(
        engine_module.keyboard, "add_hotkey", lambda combo, *a, **k: keyboard_calls.append(combo)
    )

    cfg = Config()
    cfg.hotkey = "mouse4"
    cfg.hotkey_mode = "hold"
    cfg.repeat_hotkey = "ctrl+alt+r"
    engine = engine_module.Engine(cfg)
    engine.install_hotkey()

    on_press, on_release = installed["mouse4"]
    assert on_press == engine.start_recording
    assert on_release == engine.stop_and_transcribe
    assert keyboard_calls == ["ctrl+alt+r"]
    assert engine.state == engine_module.IDLE

    engine.remove_hotkey()
    assert installed == {}


def test_mouse_hook_failure_is_reported(engine_module, monkeypatch):
    from speakmot.config import Config

    class BrokenHook:
        def __init__(self, bindings):
            self.error = "нет доступа"

        def start(self):
            return False

        def stop(self):
            pass

    monkeypatch.setattr(engine_module.mousehook, "MouseHook", BrokenHook)
    states = []
    cfg = Config()
    cfg.hotkey = "mouse5"
    engine = engine_module.Engine(cfg, on_state=lambda s, m: states.append((s, m)))
    engine.install_hotkey()
    assert engine.state == engine_module.ERROR
    assert "нет доступа" in states[-1][1]
