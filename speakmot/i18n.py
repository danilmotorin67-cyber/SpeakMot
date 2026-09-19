"""Перевод интерфейса. Исходные строки русские, словарь даёт английские.

Строка, которой нет в словаре, показывается как есть — интерфейс не ломается,
даже если перевод забыли добавить (за этим следит отдельный тест).
"""

LANGUAGES = {"Русский": "ru", "English": "en"}

_current = "ru"

EN = {
    # окно и разделы
    "Запись": "Recording",
    "История": "History",
    "Модели": "Models",
    "Профили": "Profiles",
    "Настройки": "Settings",
    "ДИКТОВКА": "DICTATION",
    "РАЗДЕЛЫ": "SECTIONS",
    "готов": "ready",
    # трей
    "SpeakMotor — диктовка": "SpeakMotor — dictation",
    "Открыть SpeakMotor": "Open SpeakMotor",
    "Начать / остановить запись": "Start / stop recording",
    "Выход": "Quit",
    "Готово": "Done",
    "Ошибка": "Error",
    "Модель ещё не установлена. Выберите её и нажмите «Установить».": (
        "The model is not installed yet. Pick one and press «Install»."
    ),
    # горячие клавиши
    "Нажмите сочетание…": "Press a shortcut…",
    "Нужен модификатор и клавиша": "A modifier plus a key is required",
    "не назначена": "not set",
    # главная
    "Готов к работе": "Ready",
    "Слушаю…": "Listening…",
    "Распознаю речь…": "Transcribing…",
    "Загрузка модели…": "Loading the model…",
    "Нажмите": "Press",
    "или кнопку выше": "or the button above",
    "СЛОВ": "WORDS",
    "ДИКТОВОК": "SESSIONS",
    "МИНУТ": "MINUTES",
    "Последний результат": "Last result",
    "Здесь появится распознанный текст.": "Recognised text will appear here.",
    "Копировать": "Copy",
    "Запись отменена": "Recording cancelled",
    "Ошибка распознавания": "Transcription failed",
    # история
    "Экспорт": "Export",
    "Очистить": "Clear",
    "Поиск по истории": "Search history",
    "История пуста": "History is empty",
    "Здесь появится всё, что вы надиктуете.": "Everything you dictate shows up here.",
    "Сохранить историю": "Save history",
    "Текст (*.txt)": "Text (*.txt)",
    "Не удалось сохранить: ": "Could not save: ",
    # настройки
    "Управление": "Controls",
    "Горячая клавиша": "Hotkey",
    "Нажмите поле и задайте сочетание": "Click the field and press a shortcut",
    "Смена языка": "Switch language",
    "Переключает русский → английский → автоопределение": (
        "Cycles Russian → English → auto detection"
    ),
    "Повторить вставку": "Repeat paste",
    "Вставляет последний распознанный текст ещё раз": "Pastes the last text once more",
    "Режим": "Mode",
    "Как срабатывает горячая клавиша": "How the hotkey behaves",
    "Переключением": "Toggle",
    "Удержанием": "Hold",
    "Распознавание": "Recognition",
    "Управление моделями": "Manage models",
    "Модель Whisper": "Whisper model",
    "Язык": "Language",
    "Указание языка ускоряет распознавание": "Naming the language speeds recognition up",
    "Русский": "Russian",
    "Автоопределение": "Auto detect",
    "Переводить на английский": "Translate to English",
    "Речь на любом языке — текст на английском": "Speak any language — get English text",
    "Звук": "Audio",
    "По умолчанию": "System default",
    "Микрофон": "Microphone",
    "Автостоп по тишине": "Stop on silence",
    "Запись закончится сама, когда вы замолчите": "Recording ends once you stop talking",
    "Выключен": "Off",
    "Через 1 секунду": "After 1 second",
    "Через 2 секунды": "After 2 seconds",
    "Через 3 секунды": "After 3 seconds",
    "Поведение": "Behaviour",
    "Автовставка": "Auto paste",
    "Вставлять текст в активное окно через Ctrl+V": "Paste into the active window with Ctrl+V",
    "Способ вставки": "Paste method",
    "Если Ctrl+V не срабатывает, выберите ввод символами": (
        "If Ctrl+V does not work, choose typing"
    ),
    "Вставкой (Ctrl+V)": "Paste (Ctrl+V)",
    "Вводом символов": "Typing",
    "Звуковой сигнал": "Sound cue",
    "Короткий сигнал в начале и в конце записи": "A short beep when recording starts and ends",
    "Голосовые команды": "Voice commands",
    "«точка», «запятая», «новый абзац» превращаются в знаки": (
        "«period», «comma», «new paragraph» turn into punctuation"
    ),
    "Показывать по ходу речи": "Show while speaking",
    "Текст появляется в панели ещё во время диктовки": "Text appears in the panel as you talk",
    "Показывать перед вставкой": "Preview before pasting",
    "Окно с текстом, который можно поправить или отклонить": (
        "A window where the text can be edited or discarded"
    ),
    "Запуск вместе с Windows": "Start with Windows",
    "Приложение будет стартовать свёрнутым в трей": "The app starts minimised to the tray",
    "Не удалось изменить автозапуск: ": "Could not change autostart: ",
    "Внешний вид": "Appearance",
    "Тема": "Theme",
    "Тёмная": "Dark",
    "Светлая": "Light",
    "Акцентный цвет": "Accent colour",
    "Язык интерфейса": "Interface language",
    "Меняется сразу, перезапуск не нужен": "Applies immediately, no restart needed",
    "Терракота": "Terracotta",
    "Янтарь": "Amber",
    "Хвоя": "Pine",
    "Бирюза": "Teal",
    "Лаванда": "Lavender",
    "Малина": "Raspberry",
    "Развернуть на весь экран": "Maximise",
    "Вернуть прежний размер": "Restore size",
    "Обновление": "Updates",
    "Проверить": "Check",
    "Проверяю…": "Checking…",
    "Версия": "Version",
    "Установлена версия ": "Installed version ",
    "Установлена последняя версия ": "You are on the latest version ",
    "Доступна версия ": "Version available: ",
    "Скачать": "Download",
    "Не удалось проверить обновления": "Could not check for updates",
    "Диагностика": "Diagnostics",
    "Журнал пишется при каждом запуске. Если что-то пошло не так, "
    "он ответит на вопрос «что именно».": (
        "A log is written on every run. When something goes wrong, it says what exactly."
    ),
    "Открыть журнал": "Open the log",
    "Журнал работы": "Log file",
    "Словарь замен": "Replacements",
    "По одной паре в строке: «было = стало». Применяется к каждому "
    "распознанному тексту без учёта регистра.": (
        "One pair per line: «from = to». Applied to every recognised text, "
        "case-insensitively."
    ),
    "пайтон = Python\nгит хаб = GitHub": "pyton = Python\ngit hub = GitHub",
    "Сохранить": "Save",
    "Сохранено ✓": "Saved ✓",
    # модели
    "Модели скачиваются один раз и работают офлайн. Чем крупнее модель, "
    "тем точнее распознавание и тем медленнее оно идёт.": (
        "Models are downloaded once and then work offline. A bigger model is "
        "more accurate and slower."
    ),
    "Выбрать": "Use",
    "Удалить": "Delete",
    "Установить": "Install",
    "используется": "in use",
    "установлена": "installed",
    "не установлена": "not installed",
    "Загрузка…": "Downloading…",
    "Не удалось скачать ": "Could not download ",
    "Модель ": "Model ",
    " установлена": " installed",
    " МБ": " MB",
    " ГБ": " GB",
    "Мгновенно, качество низкое — для коротких команд": (
        "Instant, low quality — for short commands"
    ),
    "Быстро, качество среднее": "Fast, medium quality",
    "Баланс скорости и качества — рекомендуется": "Balanced speed and quality — recommended",
    "Медленнее, качество высокое": "Slower, high quality",
    "Лучшее качество, желательна видеокарта": "Best quality, a GPU is preferable",
    # панель и предпросмотр
    "нажмите горячую клавишу ещё раз": "press the hotkey again",
    " — стоп": " — stop",
    "слушаю дальше…": "still listening…",
    "Распознаю…": "Transcribing…",
    "почти готово": "almost there",
    "текст вставлен": "text pasted",
    "РАСПОЗНАНО": "RECOGNISED",
    "Enter — вставить · Esc — отменить": "Enter — paste · Esc — cancel",
    "Отменить": "Cancel",
    "Вставить": "Paste",
    # профили
    "как в настройках": "as in settings",
    "Включены": "On",
    "Выключены": "Off",
    "code.exe или часть заголовка окна": "code.exe or part of the window title",
    "Команды": "Commands",
    "Вставка": "Paste",
    "Добавить": "Add",
    "Профиль срабатывает, когда его строка встречается в имени программы "
    "или в заголовке активного окна. Первый подошедший профиль и применяется.": (
        "A profile applies when its text occurs in the program name or in the "
        "title of the active window. The first match wins."
    ),
    "Профилей пока нет": "No profiles yet",
    "Добавьте профиль, чтобы у отдельной программы были свои настройки.": (
        "Add a profile to give a single program its own settings."
    ),
    "Сохранено профилей: ": "Profiles saved: ",
    # состояние движка
    "Микрофон недоступен: ": "Microphone unavailable: ",
}


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES.values() else "ru"


def language() -> str:
    return _current


def tr(text: str) -> str:
    """Переводит строку интерфейса на текущий язык."""
    if _current == "ru":
        return text
    return EN.get(text, text)
