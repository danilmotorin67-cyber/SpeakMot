import io
import shutil
import sys
import threading
from pathlib import Path

from .config import MODELS_DIR

MODEL_REPOS = {
    "tiny": "Systran/faster-whisper-tiny",
    "base": "Systran/faster-whisper-base",
    "small": "Systran/faster-whisper-small",
    "medium": "Systran/faster-whisper-medium",
    "large-v3": "Systran/faster-whisper-large-v3",
}

# Запасные размеры, если список файлов не удалось получить с сервера.
FALLBACK_BYTES = {
    "tiny": 75_000_000,
    "base": 145_000_000,
    "small": 484_000_000,
    "medium": 1_530_000_000,
    "large-v3": 3_090_000_000,
}

DESCRIPTIONS = {
    "tiny": "Мгновенно, качество низкое — для коротких команд",
    "base": "Быстро, качество среднее",
    "small": "Баланс скорости и качества — рекомендуется",
    "medium": "Медленнее, качество высокое",
    "large-v3": "Лучшее качество, желательна видеокарта",
}


def model_dir(size: str) -> Path:
    repo = MODEL_REPOS[size]
    return MODELS_DIR / f"models--{repo.replace('/', '--')}"


def is_installed(size: str) -> bool:
    directory = model_dir(size)
    return directory.exists() and any(directory.rglob("model.bin"))


def local_bytes(size: str) -> int:
    directory = model_dir(size)
    if not directory.exists():
        return 0
    return sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())


def remote_bytes(size: str) -> int:
    """Суммарный размер файлов модели на сервере.

    Нужен для честного процента; при отсутствии сети берём оценку из таблицы.
    """
    try:
        from huggingface_hub import HfApi

        info = HfApi().model_info(MODEL_REPOS[size], files_metadata=True)
        total = sum(f.size or 0 for f in info.siblings)
        if total > 0:
            return total
    except Exception:
        pass
    return FALLBACK_BYTES[size]


def delete(size: str) -> None:
    shutil.rmtree(model_dir(size), ignore_errors=True)


def _with_streams(function):
    """Гарантирует потоки вывода на время работы функции.

    В сборке без консоли sys.stdout и sys.stderr равны None, и печать из
    любой библиотеки роняет загрузку.
    """

    def wrapper(*args, **kwargs):
        saved = sys.stdout, sys.stderr
        if sys.stdout is None:
            sys.stdout = io.StringIO()
        if sys.stderr is None:
            sys.stderr = io.StringIO()
        try:
            return function(*args, **kwargs)
        finally:
            sys.stdout, sys.stderr = saved

    return wrapper


def download(size: str, on_progress) -> None:
    """Скачивает модель, сообщая прогресс от 0 до 100.

    huggingface_hub не отдаёт прогресс в виде колбэка, поэтому загрузка идёт
    в отдельном потоке, а процент считается по размеру папки на диске.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    total = remote_bytes(size)
    start = local_bytes(size)
    finished = threading.Event()
    error: list[Exception] = []

    def worker():
        try:
            from huggingface_hub import snapshot_download
            from huggingface_hub.utils import disable_progress_bars

            # прогресс рисуем сами; полоска tqdm пишет в stderr, которого
            # в окне без консоли просто нет
            disable_progress_bars()

            # качаем напрямую из хаба: faster_whisper при импорте тянет PyAV,
            # который для скачивания не нужен
            snapshot_download(
                MODEL_REPOS[size],
                cache_dir=str(MODELS_DIR),
                allow_patterns=["*.bin", "*.json", "*.txt", "*.model"],
            )
        except Exception as exc:
            error.append(exc)
        finally:
            finished.set()

    thread = threading.Thread(target=_with_streams(worker), daemon=True)
    thread.start()

    on_progress(0)
    while not finished.wait(0.5):
        done = max(0, local_bytes(size) - start)
        on_progress(min(99, int(done * 100 / total)) if total else 0)

    thread.join()
    if error:
        raise error[0]
    on_progress(100)
