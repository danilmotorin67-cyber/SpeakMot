import re


def apply_replacements(text: str, replacements: dict[str, str]) -> str:
    """Заменяет слова и фразы из пользовательского словаря.

    Совпадение ищется без учёта регистра и только по границам слов, поэтому
    «Клод» в «Клодом» не тронется, а «пайтон» → «Python» сработает.
    """
    if not text or not replacements:
        return text
    for source, target in replacements.items():
        source = source.strip()
        if not source:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(source)}(?!\w)", re.IGNORECASE)
        text = pattern.sub(target, text)
    return text


def parse_replacements(raw: str) -> dict[str, str]:
    """Разбирает словарь из текста вида «было = стало», по одной паре в строке."""
    result: dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        source, target = line.split("=", 1)
        source = source.strip()
        if source:
            result[source] = target.strip()
    return result


def format_replacements(replacements: dict[str, str]) -> str:
    return "\n".join(f"{source} = {target}" for source, target in replacements.items())
