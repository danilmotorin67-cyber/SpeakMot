"""Палитра и таблица стилей в духе терминала: моноширинный шрифт,
тёплый почти-чёрный фон, тонкие рамки и ни одного градиента."""

FONT = (
    "Cascadia Mono, Consolas, JetBrains Mono, "
    "DejaVu Sans Mono, Menlo, monospace"
)

ACCENTS = {
    "Терракота": "#e2603c",
    "Янтарь": "#d79921",
    "Хвоя": "#7fa650",
    "Бирюза": "#4d9a9a",
    "Лаванда": "#a98fd0",
    "Малина": "#d3697f",
}

PALETTES = {
    "dark": {
        "bg": "#0f0d0c",
        "surface": "#141110",
        "surface2": "#191514",
        "surface3": "#221c19",
        "border": "#2b2421",
        "border_hover": "#3d332d",
        "text": "#d8d0c8",
        "text_dim": "#9a9189",
        "text_faint": "#6a625b",
        "danger": "#d9544d",
        "success": "#7fa650",
        "overlay_bg": "rgba(15, 13, 12, 245)",
        "scroll": "#3d332d",
        "on_accent": "#0f0d0c",
        "dot": "#3d332d",
    },
    "light": {
        "bg": "#f6f2ec",
        "surface": "#fffdf9",
        "surface2": "#efe9e0",
        "surface3": "#e5ddd2",
        "border": "#ddd4c7",
        "border_hover": "#c3b7a6",
        "text": "#2b2421",
        "text_dim": "#6b6159",
        "text_faint": "#918a80",
        "danger": "#b4332d",
        "success": "#4f7a2f",
        "overlay_bg": "rgba(255, 253, 249, 246)",
        "scroll": "#c3b7a6",
        "on_accent": "#fffdf9",
        "dot": "#c3b7a6",
    },
}

_current = dict(PALETTES["dark"], accent=ACCENTS["Терракота"])


DEFAULT_ACCENT = ACCENTS["Терракота"]


def normalize_accent(accent: str) -> str:
    """Старые настройки могли хранить цвет из прежней палитры."""
    return accent if accent in ACCENTS.values() else DEFAULT_ACCENT


def apply(theme: str, accent: str) -> None:
    """Запоминает выбранную тему и акцент как текущие."""
    _current.clear()
    _current.update(PALETTES.get(theme, PALETTES["dark"]))
    _current["accent"] = normalize_accent(accent)


def color(key: str) -> str:
    return _current[key]


def is_dark() -> bool:
    return _current["bg"] == PALETTES["dark"]["bg"]


def shift(hex_color: str, amount: int) -> str:
    """Осветляет или затемняет цвет — для наведения."""
    hex_color = hex_color.lstrip("#")
    channels = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]
    channels = [max(0, min(255, value + amount)) for value in channels]
    return "#{:02x}{:02x}{:02x}".format(*channels)


def qss() -> str:
    palette = dict(_current)
    palette["accent_hover"] = shift(palette["accent"], 22)
    palette["accent_soft"] = shift(palette["accent"], -130 if is_dark() else 140)
    palette["font"] = FONT
    return _TEMPLATE.format(**palette)


_TEMPLATE = """
* {{
    font-family: {font};
    color: {text};
    font-size: 13px;
}}

#root {{
    background: {bg};
    border: 1px solid {border};
    border-radius: 10px;
}}

/* --- заголовок окна --- */
#titleBar {{
    background: transparent;
    border-bottom: 1px solid {border};
}}
#titleLabel {{
    color: {text_dim};
    font-size: 12px;
    letter-spacing: 0.6px;
}}
#winBtn, #winBtnClose {{
    background: transparent;
    border: none;
    outline: none;
    border-radius: 4px;
    color: {text_faint};
    font-size: 13px;
    padding: 0px;
}}
#winBtn:hover {{ background: {surface3}; color: {text}; }}
#winBtnClose:hover {{ background: {danger}; color: #ffffff; }}

/* --- строка состояния внизу --- */
#statusBar {{
    background: transparent;
    border-top: 1px solid {border};
}}
#statusBarText, #clock {{
    color: {text_faint};
    font-size: 11px;
    letter-spacing: 0.4px;
}}

/* --- боковая панель --- */
#sidebar {{
    background: transparent;
    border-right: 1px solid {border};
}}
#brand {{
    font-size: 17px;
    font-weight: 700;
    color: {accent};
    letter-spacing: 3px;
}}
#brandSub {{
    color: {text_faint};
    font-size: 10px;
    letter-spacing: 2px;
}}
#navBtn {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0px;
    padding: 9px 12px;
    text-align: left;
    color: {text_dim};
    font-size: 13px;
}}
#navBtn:hover {{ color: {text}; background: {surface2}; }}
#navBtn:checked {{
    border-left: 2px solid {accent};
    background: {surface2};
    color: {accent};
}}
#sidebarSection {{
    color: {text_faint};
    font-size: 10px;
    letter-spacing: 1.8px;
}}

/* --- страницы --- */
#page {{ background: {bg}; }}
#pageTitle {{
    font-size: 19px;
    font-weight: 700;
    color: {text};
    letter-spacing: 1px;
}}
#pageHint, #hint {{ color: {text_faint}; font-size: 12px; }}

/* --- карточки: рамка без заливки --- */
#card {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 6px;
}}
#card:hover {{ border-color: {border_hover}; }}
#cardTitle {{
    font-size: 10px;
    color: {accent};
    letter-spacing: 2px;
}}
#divider {{ background: {border}; border: none; max-height: 1px; }}

#statTile {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 6px;
}}
#statValue {{ font-size: 19px; font-weight: 700; color: {accent}; }}
#statCaption {{ color: {text_faint}; font-size: 10px; letter-spacing: 1.4px; }}

#emptyTitle {{ font-size: 13px; color: {text_dim}; letter-spacing: 1px; }}
#emptyHint {{ font-size: 12px; color: {text_faint}; }}

#status {{ font-size: 16px; font-weight: 700; letter-spacing: 0.5px; }}
#statusHint {{ color: {text_faint}; font-size: 12px; }}
#kbd {{
    background: transparent;
    border: 1px solid {border_hover};
    border-radius: 4px;
    padding: 3px 8px;
    color: {text_dim};
    font-size: 11px;
}}
#resultText {{
    background: transparent;
    border: none;
    font-size: 13px;
    line-height: 165%;
}}

/* --- кнопки-чипы --- */
QPushButton#primary {{
    background: transparent;
    border: 1px solid {accent};
    border-radius: 5px;
    padding: 8px 16px;
    color: {accent};
}}
QPushButton#primary:hover {{ background: {accent}; color: {on_accent}; }}
QPushButton#primary:disabled {{ border-color: {border}; color: {text_faint}; }}

QPushButton#ghost {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 5px;
    padding: 8px 14px;
    color: {text_dim};
}}
QPushButton#ghost:hover {{ border-color: {border_hover}; color: {text}; }}
QPushButton#ghost:disabled {{ color: {text_faint}; }}

QPushButton#danger {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 5px;
    padding: 8px 14px;
    color: {text_faint};
}}
QPushButton#danger:hover {{ border-color: {danger}; color: {danger}; }}

#hotkeyEdit {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 5px;
    padding: 8px 14px;
    color: {text};
    letter-spacing: 0.6px;
}}
#hotkeyEdit:hover {{ border-color: {border_hover}; }}
#hotkeyEdit:checked {{ border-color: {accent}; color: {accent}; }}

/* --- поля ввода --- */
QComboBox, QLineEdit, QPlainTextEdit, QTextEdit {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 5px;
    padding: 7px 11px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QComboBox:hover, QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover {{
    border-color: {border_hover};
}}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {accent};
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 5px;
    padding: 3px;
    outline: none;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}

/* --- прокрутка --- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {border}; border-radius: 4px; min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{ background: {scroll}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* --- плавающие окна --- */
#overlay, #previewRoot {{
    background: {overlay_bg};
    border: 1px solid {border_hover};
    border-radius: 8px;
}}
#overlayText {{ font-size: 13px; color: {text}; }}
#overlayHint {{ font-size: 11px; color: {text_faint}; }}
#previewTitle {{ font-size: 10px; color: {accent}; letter-spacing: 2px; }}
#previewEdit {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 10px 12px;
    font-size: 13px;
}}

QProgressBar {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 4px;
    height: 16px;
    text-align: center;
    color: {text_dim};
    font-size: 10px;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 3px; }}

#settingLabel {{ font-size: 13px; color: {text}; }}
#settingDesc {{ color: {text_faint}; font-size: 11px; }}
#badge {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 4px;
    padding: 4px 9px;
    color: {text_faint};
    font-size: 10px;
    letter-spacing: 1px;
}}
#badgeAccent {{
    background: transparent;
    border: 1px solid {accent};
    border-radius: 4px;
    padding: 4px 9px;
    color: {accent};
    font-size: 10px;
    letter-spacing: 1px;
}}
/* --- меню (в том числе в трее) --- */
QMenu {{
    background: {surface};
    border: 1px solid {border_hover};
    border-radius: 6px;
    padding: 6px;
    color: {accent};
}}
QMenu::item {{
    background: transparent;
    color: {accent};
    padding: 7px 18px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {accent};
    color: {on_accent};
}}
QMenu::item:disabled {{ color: {text_faint}; }}
QMenu::separator {{
    height: 1px;
    background: {border};
    margin: 5px 8px;
}}

QToolTip {{
    background: {surface3};
    color: {text};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 5px 9px;
}}
"""
