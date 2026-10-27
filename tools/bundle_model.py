"""Скачивает модель для установщика «со встроенной моделью».

Раскладка — как у кэша huggingface_hub, чтобы программа нашла модель без
сети. Ссылки из snapshots на blobs заменяются настоящими файлами, а blobs
удаляются: иначе установщик понёс бы модель дважды.

Запуск: python tools/bundle_model.py small bundle/models
"""

import shutil
import sys
from pathlib import Path

from huggingface_hub import snapshot_download

REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
}


def main(size: str, target: str) -> None:
    repo = REPOS[size]
    cache = Path(target)
    snapshot_download(
        repo,
        cache_dir=str(cache),
        allow_patterns=["*.bin", "*.json", "*.txt", "*.model"],
    )
    model_root = cache / f"models--{repo.replace('/', '--')}"
    for path in (model_root / "snapshots").rglob("*"):
        if path.is_symlink():
            data = path.resolve().read_bytes()
            path.unlink()
            path.write_bytes(data)
    shutil.rmtree(model_root / "blobs", ignore_errors=True)
    shutil.rmtree(cache / ".locks", ignore_errors=True)

    weights = list(model_root.rglob("model.bin"))
    if not weights or weights[0].stat().st_size < 1_000_000:
        sys.exit("model.bin не скачался")
    if not (model_root / "refs" / "main").exists():
        sys.exit("нет refs/main — без сети модель не найдётся")
    print(f"готово: {weights[0]} ({weights[0].stat().st_size} байт)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
