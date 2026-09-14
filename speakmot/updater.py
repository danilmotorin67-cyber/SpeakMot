"""Проверка новых версий через релизы GitHub."""

import json
import re
import urllib.request

from . import __version__

RELEASES_URL = "https://api.github.com/repos/danilmotorin67-cyber/SpeakMot/releases/latest"
TIMEOUT = 10


def parse_version(text: str) -> tuple[int, ...]:
    """Превращает «v1.2.3» в (1, 2, 3). Непонятные куски считаются нулями."""
    numbers = re.findall(r"\d+", text or "")
    return tuple(int(number) for number in numbers[:3]) or (0,)


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


def fetch_latest(url: str = RELEASES_URL) -> dict:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode("utf-8"))


def check(current: str = __version__) -> tuple[bool, str, str]:
    """Возвращает: есть ли обновление, версию и ссылку на страницу релиза.

    Ошибки сети не пробрасываются — проверка обновлений не повод падать.
    """
    try:
        release = fetch_latest()
    except Exception:
        return False, "", ""

    tag = release.get("tag_name") or ""
    page = release.get("html_url") or ""
    return is_newer(tag, current), tag.lstrip("v"), page
