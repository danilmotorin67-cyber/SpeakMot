"""Палитра и таблица стилей. Тема и акцент меняются на лету."""

FONT = "Segoe UI Variable, Segoe UI, Inter, sans-serif"

ACCENTS = {
    "Синий": "#5b8cff",
    "Фиолетовый": "#a86bff",
    "Зелёный": "#2fbf71",
    "Оранжевый": "#ff8a3d",
    "Розовый": "#ff5c8a",
    "Бирюзовый": "#17b8bd",
}

PALETTES = {
    "dark": {
        "bg": "#0f1117",
        "surface": "#171a23",
        "surface2": "#1e222d",
        "border": "#272c3a",
        "border_hover": "#333a4d",
        "text": "#e7e9ee",
        "text_dim": "#8b93a7",
        "danger": "#ff5d5d",
        "success": "#3ddc97",
        "overlay_bg": "rgba(15, 17, 23, 235)",
        "scroll": "#39415a",
        "on_accent": "#ffffff",
    },
    "light": {
        "bg": "#f4f6fa",
        "surface": "#ffffff",
        "surface2": "#eceff5",
        "border": "#dce1ea",
        "border_hover": "#c3cbd9",
        "text": "#171a21",
        "text_dim": "#5f6878",
        "danger": "#e04343",
        "success": "#1f9d63",
        "overlay_bg": "rgba(255, 255, 255, 240)",
        "scroll": "#b9c1d0",
        "on_accent": "#ffffff",
    },
}

_current = dict(PALETTES["dark"], accent=ACCENTS["Синий"])


def apply(theme: str, accent: str) -> None:
    """Запоминает выбранную тему и акцент как текущие."""
    _current.clear()
    _current.update(PALETTES.get(theme, PALETTES["dark"]))
    _current["accent"] = accent


def color(key: str) -> str:
    return _current[key]


def _shift(hex_color: str, amount: int) -> str:
    """Осветляет или затемняет цвет — для состояния наведения."""
    hex_color = hex_color.lstrip("#")
    channels = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]
    channels = [max(0, min(255, value + amount)) for value in channels]
    return "#{:02x}{:02x}{:02x}".format(*channels)


def qss() -> str:
    palette = dict(_current)
    palette["accent_hover"] = _shift(palette["accent"], 20)
    palette["font"] = FONT
    return _TEMPLATE.format(**palette)


_TEMPLATE = """
* {{
    font-family: {font};
    color: {text};
    font-size: 14px;
}}

#root {{
    background: {bg};
    border: 1px solid {border};
    border-radius: 14px;
}}

#titleBar {{ background: transparent; }}
#titleLabel {{
    color: {text_dim};
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.4px;
}}
#winBtn, #winBtnClose {{
    background: transparent;
    border: none;
    outline: none;
    border-radius: 6px;
    color: {text_dim};
    font-size: 15px;
    padding: 0px;
}}
#winBtn:hover {{ background: {surface2}; color: {text}; }}
#winBtnClose:hover {{ background: {danger}; color: #ffffff; }}

#sidebar {{
    background: {surface};
    border-right: 1px solid {border};
    border-top-left-radius: 14px;
    border-bottom-left-radius: 14px;
}}
#navBtn {{
    background: transparent;
    border: none;
    border-radius: 9px;
    padding: 10px 14px;
    text-align: left;
    color: {text_dim};
    font-size: 14px;
    font-weight: 500;
}}
#navBtn:hover {{ background: {surface2}; color: {text}; }}
#navBtn:checked {{ background: {surface2}; color: {text}; font-weight: 600; }}
#brand {{ font-size: 17px; font-weight: 700; letter-spacing: 0.3px; }}
#brandSub {{
    color: {text_dim};
    font-size: 11px;
    letter-spacing: 1.6px;
    font-weight: 600;
}}

#page {{
    background: {bg};
    border-top-right-radius: 14px;
    border-bottom-right-radius: 14px;
}}
#pageTitle {{ font-size: 21px; font-weight: 700; }}
#pageHint, #hint {{ color: {text_dim}; font-size: 13px; }}

#card {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 12px;
}}
#cardTitle {{
    font-size: 12px;
    font-weight: 700;
    color: {text_dim};
    letter-spacing: 1.2px;
}}

#status {{ font-size: 15px; font-weight: 600; }}
#kbd {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 5px 10px;
    color: {text};
    font-size: 13px;
    font-weight: 600;
}}
#resultText {{
    background: transparent;
    border: none;
    font-size: 15px;
    line-height: 150%;
}}

QPushButton#primary {{
    background: {accent};
    border: none;
    border-radius: 9px;
    padding: 10px 18px;
    color: {on_accent};
    font-weight: 600;
}}
QPushButton#primary:hover {{ background: {accent_hover}; }}
QPushButton#primary:disabled {{ background: {surface2}; color: {text_dim}; }}

QPushButton#ghost {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 9px;
    padding: 9px 16px;
    color: {text};
    font-weight: 500;
}}
QPushButton#ghost:hover {{ border-color: {accent}; color: {accent}; }}

QPushButton#danger {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 9px;
    padding: 9px 16px;
    color: {text_dim};
    font-weight: 500;
}}
QPushButton#danger:hover {{ border-color: {danger}; color: {danger}; }}

QComboBox, QLineEdit, QPlainTextEdit, QTextEdit {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 9px;
    padding: 8px 12px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QComboBox:hover, QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover {{
    border-color: {border_hover};
}}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {accent};
}}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 9px;
    padding: 4px;
    outline: none;
    selection-background-color: {accent};
}}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {border}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {scroll}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

#overlay, #previewRoot {{
    background: {overlay_bg};
    border: 1px solid {border};
    border-radius: 18px;
}}
#overlayText {{ font-size: 13px; font-weight: 600; color: {text}; }}
#overlayHint {{ font-size: 11px; color: {text_dim}; }}

#previewTitle {{ font-size: 13px; font-weight: 700; color: {text_dim};
    letter-spacing: 1px; }}
#previewEdit {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 12px;
    font-size: 15px;
}}

QProgressBar {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 8px;
    height: 16px;
    text-align: center;
    color: {text};
    font-size: 11px;
    font-weight: 600;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 7px; }}

#settingLabel {{ font-size: 14px; font-weight: 500; }}
#settingDesc {{ color: {text_dim}; font-size: 12px; }}
#badge {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 3px 9px;
    color: {text_dim};
    font-size: 11px;
    font-weight: 600;
}}
"""
