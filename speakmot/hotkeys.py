"""Сборка названия горячей клавиши из того, что нажал пользователь."""

MODIFIER_ORDER = ["ctrl", "alt", "shift", "windows"]

# Qt называет клавиши по-своему, библиотека перехвата — иначе.
KEY_ALIASES = {
    "return": "enter",
    "escape": "esc",
    "del": "delete",
    "ins": "insert",
    "pgup": "page up",
    "pgdown": "page down",
    "page up": "page up",
    "page down": "page down",
    "backspace": "backspace",
    "spacebar": "space",
}

# Комбинации без обычной клавиши бесполезны, а эти и вовсе опасны:
# перехватив их, можно остаться без выхода из приложения.
FORBIDDEN = {"", "alt+f4", "ctrl+alt+delete"}


def normalize_key(name: str) -> str:
    """Приводит название клавиши к виду, понятному библиотеке перехвата."""
    name = (name or "").strip().lower()
    name = name.removeprefix("num ")
    return KEY_ALIASES.get(name, name)


def build(modifiers, key: str) -> str:
    """Собирает «ctrl+alt+space» из набора модификаторов и клавиши.

    Возвращает пустую строку, если комбинация не годится: одни модификаторы
    без клавиши или сочетание, которое нельзя перехватывать.
    """
    key = normalize_key(key)
    if not key or key in MODIFIER_ORDER:
        return ""

    ordered = [name for name in MODIFIER_ORDER if name in set(modifiers)]
    combo = "+".join([*ordered, key])
    if combo in FORBIDDEN:
        return ""
    # одиночная буква или цифра слишком легко нажимается случайно
    if not ordered and len(key) == 1:
        return ""
    return combo


def pretty(combo: str) -> str:
    """Человеческий вид комбинации для показа в интерфейсе."""
    if not combo:
        return "не назначена"
    return " + ".join(part.strip().title() for part in combo.split("+") if part.strip())
