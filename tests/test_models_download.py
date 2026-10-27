import sys

import pytest

import speakmot.models as models


@pytest.fixture
def hub(tmp_path, monkeypatch):
    """Подменяет загрузку с сервера на создание файлов на диске."""
    monkeypatch.setattr(models, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(models, "remote_bytes", lambda size, endpoint=None: 1000)

    module = type(sys)("huggingface_hub")
    utils = type(sys)("huggingface_hub.utils")

    def snapshot_download(repo_id, cache_dir=None, allow_patterns=None, **kwargs):
        # tqdm внутри библиотеки пишет в stderr напрямую — так же делаем и мы
        sys.stderr.write("downloading\n")
        directory = models.model_dir("tiny") / "snapshots" / "abc"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "model.bin").write_bytes(b"x" * 1000)

    module.snapshot_download = snapshot_download
    utils.disable_progress_bars = lambda: None
    module.utils = utils
    monkeypatch.setitem(sys.modules, "huggingface_hub", module)
    monkeypatch.setitem(sys.modules, "huggingface_hub.utils", utils)
    return module


def test_download_reports_progress_and_installs(hub):
    percents = []
    models.download("tiny", percents.append)
    assert models.is_installed("tiny")
    assert percents[0] == 0
    assert percents[-1] == 100


def test_download_survives_missing_output_streams(hub, monkeypatch):
    """Окно без консоли: sys.stdout и sys.stderr равны None."""
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    models.download("tiny", lambda percent: None)

    assert models.is_installed("tiny")


def test_download_reports_server_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(models, "remote_bytes", lambda size, endpoint=None: 1000)

    module = type(sys)("huggingface_hub")
    utils = type(sys)("huggingface_hub.utils")

    def failing(*args, **kwargs):
        raise OSError("сеть недоступна")

    module.snapshot_download = failing
    utils.disable_progress_bars = lambda: None
    monkeypatch.setitem(sys.modules, "huggingface_hub", module)
    monkeypatch.setitem(sys.modules, "huggingface_hub.utils", utils)

    with pytest.raises(RuntimeError, match="сеть недоступна"):
        models.download("tiny", lambda percent: None)


def _fake_hub(monkeypatch, snapshot_download):
    module = type(sys)("huggingface_hub")
    utils = type(sys)("huggingface_hub.utils")
    module.snapshot_download = snapshot_download
    utils.disable_progress_bars = lambda: None
    monkeypatch.setitem(sys.modules, "huggingface_hub", module)
    monkeypatch.setitem(sys.modules, "huggingface_hub.utils", utils)


def test_download_falls_back_to_the_mirror(tmp_path, monkeypatch):
    """Основной сервер недоступен — модель приходит с зеркала."""
    monkeypatch.setattr(models, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(models, "remote_bytes", lambda size, endpoint=None: 1000)
    tried = []

    def snapshot_download(repo_id, endpoint=None, **kwargs):
        tried.append(endpoint)
        if endpoint == models.ENDPOINTS[0]:
            raise ConnectionError("huggingface.co недоступен")
        directory = models.model_dir("base") / "snapshots" / "abc"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "model.bin").write_bytes(b"x")

    _fake_hub(monkeypatch, snapshot_download)
    models.download("base", lambda percent: None)
    assert tried == list(models.ENDPOINTS)
    assert models.is_installed("base")


def test_download_without_files_is_a_failure(tmp_path, monkeypatch):
    """Загрузка «прошла», а модели нет — раньше это считалось успехом,
    и кнопка «Установить» молча возвращалась."""
    monkeypatch.setattr(models, "MODELS_DIR", tmp_path)
    monkeypatch.setattr(models, "remote_bytes", lambda size, endpoint=None: 1000)
    _fake_hub(monkeypatch, lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="не появились"):
        models.download("base", lambda percent: None)


def test_errors_without_text_still_say_something():
    class Silent(Exception):
        pass

    assert models.describe_error(Silent()) == "Silent"
    assert models.describe_error(OSError("нет сети")) == "OSError: нет сети"
