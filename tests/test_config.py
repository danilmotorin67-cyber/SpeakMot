import json

from speakmot import config
from speakmot.config import Config


def _redirect(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.json")


def test_creates_defaults_when_missing(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    cfg = Config.load()
    assert cfg.hotkey == "ctrl+alt+space"
    assert (tmp_path / "config.json").exists()


def test_round_trips_values(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    cfg = Config()
    cfg.model_size = "medium"
    cfg.silence_stop = 2.0
    cfg.replacements = {"пайтон": "Python"}
    cfg.save()

    loaded = Config.load()
    assert loaded.model_size == "medium"
    assert loaded.silence_stop == 2.0
    assert loaded.replacements == {"пайтон": "Python"}


def test_ignores_unknown_keys(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    (tmp_path / "config.json").write_text(
        json.dumps({"hotkey": "ctrl+q", "legacy_option": 1}), encoding="utf-8"
    )
    assert Config.load().hotkey == "ctrl+q"


def test_falls_back_to_defaults_on_broken_file(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    (tmp_path / "config.json").write_text("{не json", encoding="utf-8")
    assert Config.load().hotkey == "ctrl+alt+space"
