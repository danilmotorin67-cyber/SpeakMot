import re

# Что говорим → что подставляем. Более длинные фразы должны идти первыми,
# иначе «восклицательный знак» разберётся как «знак».
PUNCTUATION = {
    "новый абзац": "\n\n",
    "новая строка": "\n",
    "с новой строки": "\n",
    "вопросительный знак": "?",
    "восклицательный знак": "!",
    "открыть скобку": "(",
    "закрыть скобку": ")",
    "открыть кавычки": "«",
    "закрыть кавычки": "»",
    "многоточие": "…",
    "двоеточие": ":",
    "точка с запятой": ";",
    "запятая": ",",
    "точка": ".",
    "дефис": "-",
    "тире": "—",
    "процент": "%",
    # то же самое по-английски — распознавание умеет оба языка
    "new paragraph": "\n\n",
    "new line": "\n",
    "question mark": "?",
    "exclamation mark": "!",
    "exclamation point": "!",
    "open bracket": "(",
    "close bracket": ")",
    "open quote": "\u201c",
    "close quote": "\u201d",
    "ellipsis": "…",
    "semicolon": ";",
    "colon": ":",
    "full stop": ".",
    "period": ".",
    "comma": ",",
    "hyphen": "-",
    "dash": "—",
    "percent sign": "%",
}

NO_SPACE_BEFORE = set(".,!?:;%…»)\u201d")
OPENING = set("(«\u201c")
SENTENCE_END = set(".!?…")


def _pattern() -> re.Pattern:
    phrases = sorted(PUNCTUATION, key=len, reverse=True)
    joined = "|".join(re.escape(phrase) for phrase in phrases)
    return re.compile(rf"(?<!\w)({joined})(?!\w)", re.IGNORECASE)


_COMMAND_RE = _pattern()


def apply_commands(text: str) -> str:
    """Заменяет продиктованные названия знаков на сами знаки.

    После замены текст приводится в порядок: убираются пробелы перед знаками
    препинания и ставится заглавная буква в начале нового предложения.
    """
    if not text:
        return text

    replaced = _COMMAND_RE.sub(lambda match: PUNCTUATION[match.group(1).lower()], text)
    return _tidy(replaced)


def _tidy(text: str) -> str:
    # пробелы вокруг знаков
    text = re.sub(r"\s+([" + re.escape("".join(NO_SPACE_BEFORE)) + r"])", r"\1", text)
    text = re.sub(r"([" + re.escape("".join(OPENING)) + r"])\s+", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _capitalize(text.strip())


def _capitalize(text: str) -> str:
    result = []
    start_of_sentence = True
    for char in text:
        if start_of_sentence and char.isalpha():
            result.append(char.upper())
            start_of_sentence = False
            continue
        result.append(char)
        if char in SENTENCE_END or char == "\n":
            start_of_sentence = True
    return "".join(result)
