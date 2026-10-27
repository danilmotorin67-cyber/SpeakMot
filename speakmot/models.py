import io
import logging
import shutil
import sys
import threading
from pathlib import Path

from .config import MODELS_DIR

log = logging.getLogger("speakmot.models")

# Основной сервер и зеркало: huggingface.co бывает недоступен из некоторых
# сетей, а зеркало отдаёт те же файлы.
ENDPOINTS = ("https://huggingface.co", "https://hf-mirror.com")

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


def remote_bytes(size: str, endpoint: str = ENDPOINTS[0]) -> int:
    """Суммарный размер файлов модели на сервере.

    Нужен для честного процента; при отсутствии сети берём оценку из таблицы.
    """
    try:
        from huggingface_hub import HfApi

        info = HfApi(endpoint=endpoint).model_info(MODEL_REPOS[size], files_metadata=True)
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


def describe_error(exc: BaseException) -> str:
    """Текст ошибки для человека. У части исключений str() пустой."""
    text = str(exc).strip()
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def download(size: str, on_progress) -> None:
    """Скачивает модель, сообщая прогресс от 0 до 100.

    Сначала с основного сервера, при неудаче — с зеркала. Успехом считается
    только модель, которая действительно появилась на диске.
    """
    errors = []
    for endpoint in ENDPOINTS:
        try:
            _download_from(size, endpoint, on_progress)
        except Exception as exc:
            log.warning("загрузка %s с %s не удалась: %s", size, endpoint, describe_error(exc))
            errors.append(f"{endpoint}: {describe_error(exc)}")
            continue
        if is_installed(size):
            log.info("модель %s скачана с %s", size, endpoint)
            on_progress(100)
            return
        errors.append(f"{endpoint}: файлы модели не появились на диске")
    raise RuntimeError("; ".join(errors))


def _download_from(size: str, endpoint: str, on_progress) -> None:
    """Одна попытка загрузки с указанного сервера.

    huggingface_hub не отдаёт прогресс в виде колбэка, поэтому загрузка идёт
    в отдельном потоке, а процент считается по размеру папки на диске.
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    total = remote_bytes(size, endpoint)
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
                endpoint=endpoint,
                etag_timeout=20,
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
