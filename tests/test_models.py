import speakmot.models as models


def _redirect(tmp_path, monkeypatch):
    monkeypatch.setattr(models, "MODELS_DIR", tmp_path)


def _install(tmp_path, size: str, payload: bytes = b"x" * 1024) -> None:
    directory = models.model_dir(size) / "snapshots" / "abc"
    directory.mkdir(parents=True)
    (directory / "model.bin").write_bytes(payload)


def test_not_installed_on_empty_directory(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    assert not models.is_installed("small")
    assert models.local_bytes("small") == 0


def test_detects_installed_model(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    _install(tmp_path, "small")
    assert models.is_installed("small")
    assert models.local_bytes("small") == 1024


def test_directory_without_weights_is_not_installed(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    (models.model_dir("small") / "snapshots").mkdir(parents=True)
    assert not models.is_installed("small")


def test_models_do_not_interfere(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    _install(tmp_path, "tiny")
    assert models.is_installed("tiny")
    assert not models.is_installed("medium")


def test_delete_removes_the_model(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    _install(tmp_path, "base")
    models.delete("base")
    assert not models.is_installed("base")


def test_delete_is_safe_when_nothing_is_installed(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    models.delete("base")


def test_remote_size_falls_back_without_network(tmp_path, monkeypatch):
    _redirect(tmp_path, monkeypatch)
    monkeypatch.setattr(
        models, "MODEL_REPOS", {"small": "definitely/not-a-real-repo-speakmot"}
    )
    monkeypatch.setattr(models, "FALLBACK_BYTES", {"small": 123})
    assert models.remote_bytes("small") == 123
