"""Палитра и таблица стилей. Тема и акцент меняются на лету."""

FONT = "Segoe UI Variable Display, Segoe UI, Inter, sans-serif"

ACCENTS = {
    "Индиго": "#6366f1",
    "Океан": "#0ea5e9",
    "Изумруд": "#10b981",
    "Янтарь": "#f59e0b",
    "Роза": "#f43f5e",
    "Аметист": "#a855f7",
}

PALETTES = {
    "dark": {
        "bg": "#0b0d13",
        "surface": "#12151d",
        "surface2": "#181c26",
        "surface3": "#1f2430",
        "border": "#242a37",
        "border_hover": "#333b4d",
        "text": "#eef1f7",
        "text_dim": "#8e97ab",
        "text_faint": "#5d6577",
        "danger": "#f4676b",
        "success": "#34d399",
        "overlay_bg": "rgba(12, 14, 20, 242)",
        "scroll": "#39415a",
        "on_accent": "#ffffff",
        "shadow": "rgba(0, 0, 0, 110)",
    },
    "light": {
        "bg": "#f3f5f9",
        "surface": "#ffffff",
        "surface2": "#f0f2f7",
        "surface3": "#e7eaf1",
        "border": "#e0e4ec",
        "border_hover": "#c4cbd9",
        "text": "#131720",
        "text_dim": "#5b6579",
        "text_faint": "#8b93a5",
        "danger": "#dc2f36",
        "success": "#0f9d63",
        "overlay_bg": "rgba(255, 255, 255, 245)",
        "scroll": "#b6becd",
        "on_accent": "#ffffff",
        "shadow": "rgba(15, 23, 42, 28)",
    },
}

_current = dict(PALETTES["dark"], accent=ACCENTS["Индиго"])


def apply(theme: str, accent: str) -> None:
    """Запоминает выбранную тему и акцент как текущие."""
    _current.clear()
    _current.update(PALETTES.get(theme, PALETTES["dark"]))
    _current["accent"] = accent


def color(key: str) -> str:
    return _current[key]


def is_dark() -> bool:
    return _current["bg"] == PALETTES["dark"]["bg"]


def shift(hex_color: str, amount: int) -> str:
    """Осветляет или затемняет цвет — для наведения и градиентов."""
    hex_color = hex_color.lstrip("#")
    channels = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]
    channels = [max(0, min(255, value + amount)) for value in channels]
    return "#{:02x}{:02x}{:02x}".format(*channels)


def qss() -> str:
    palette = dict(_current)
    palette["accent_hover"] = shift(palette["accent"], 18)
    palette["accent_press"] = shift(palette["accent"], -18)
    palette["accent_soft"] = shift(palette["accent"], -120 if is_dark() else 150)
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
    border-radius: 16px;
}}

/* --- заголовок окна --- */
#titleBar {{ background: transparent; }}
#winBtn, #winBtnClose {{
    background: transparent;
    border: none;
    outline: none;
    border-radius: 8px;
    color: {text_faint};
    font-size: 15px;
    padding: 0px;
}}
#winBtn:hover {{ background: {surface3}; color: {text}; }}
#winBtnClose:hover {{ background: {danger}; color: #ffffff; }}

/* --- боковая панель --- */
#sidebar {{
    background: {surface};
    border-right: 1px solid {border};
    border-top-left-radius: 16px;
    border-bottom-left-radius: 16px;
}}
#brand {{
    font-size: 19px;
    font-weight: 800;
    letter-spacing: -0.2px;
}}
#brandSub {{
    color: {accent};
    font-size: 10px;
    letter-spacing: 2.4px;
    font-weight: 700;
}}
#sidebarSection {{
    color: {text_faint};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.6px;
}}

/* --- страницы --- */
#page {{
    background: {bg};
    border-top-right-radius: 16px;
    border-bottom-right-radius: 16px;
}}
#pageTitle {{
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.4px;
}}
#pageHint, #hint {{ color: {text_dim}; font-size: 13px; }}

/* --- карточки --- */
#card {{
    background: {surface};
    border: 1px solid {border};
    border-radius: 14px;
}}
#cardTitle {{
    font-size: 11px;
    font-weight: 700;
    color: {text_faint};
    letter-spacing: 1.4px;
}}
#divider {{ background: {border}; border: none; }}

#status {{ font-size: 20px; font-weight: 700; letter-spacing: -0.3px; }}
#statusHint {{ color: {text_dim}; font-size: 13px; }}
#kbd {{
    background: {surface3};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 12px;
    color: {text};
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.4px;
}}
#resultText {{
    background: transparent;
    border: none;
    font-size: 15px;
    line-height: 155%;
}}

/* --- кнопки --- */
QPushButton#primary {{
    background: {accent};
    border: none;
    border-radius: 10px;
    padding: 11px 20px;
    color: {on_accent};
    font-weight: 600;
}}
QPushButton#primary:hover {{ background: {accent_hover}; }}
QPushButton#primary:pressed {{ background: {accent_press}; }}
QPushButton#primary:disabled {{ background: {surface3}; color: {text_faint}; }}

QPushButton#ghost {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 18px;
    color: {text};
    font-weight: 500;
}}
QPushButton#ghost:hover {{ background: {surface3}; border-color: {border_hover}; }}
QPushButton#ghost:pressed {{ background: {surface2}; }}
QPushButton#ghost:disabled {{ color: {text_faint}; }}

QPushButton#danger {{
    background: transparent;
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 18px;
    color: {text_dim};
    font-weight: 500;
}}
QPushButton#danger:hover {{ border-color: {danger}; color: {danger}; }}

/* --- поле горячей клавиши --- */
#hotkeyEdit {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 10px 16px;
    color: {text};
    font-weight: 700;
    letter-spacing: 0.4px;
}}
#hotkeyEdit:hover {{ border-color: {border_hover}; }}
#hotkeyEdit:checked {{
    border-color: {accent};
    background: {accent_soft};
    color: {accent};
}}

/* --- поля ввода --- */
QComboBox, QLineEdit, QPlainTextEdit, QTextEdit {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 9px 13px;
    selection-background-color: {accent};
    selection-color: {on_accent};
}}
QComboBox:hover, QLineEdit:hover, QPlainTextEdit:hover, QTextEdit:hover {{
    border-color: {border_hover};
}}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {{
    border-color: {accent};
}}
QComboBox::drop-down {{ border: none; width: 28px; }}
QComboBox QAbstractItemView {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 10px;
    padding: 5px;
    outline: none;
    selection-background-color: {accent};
}}

/* --- прокрутка --- */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{
    background: {border}; border-radius: 5px; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: {scroll}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* --- плавающие окна --- */
#overlay, #previewRoot {{
    background: {overlay_bg};
    border: 1px solid {border};
    border-radius: 20px;
}}
#overlayText {{ font-size: 14px; font-weight: 600; color: {text}; }}
#overlayHint {{ font-size: 11px; color: {text_dim}; }}
#previewTitle {{
    font-size: 11px; font-weight: 700; color: {text_faint}; letter-spacing: 1.4px;
}}
#previewEdit {{
    background: {surface2};
    border: 1px solid {border};
    border-radius: 12px;
    padding: 12px 14px;
    font-size: 15px;
}}

/* --- прочее --- */
QProgressBar {{
    background: {surface3};
    border: none;
    border-radius: 9px;
    height: 18px;
    text-align: center;
    color: {text};
    font-size: 11px;
    font-weight: 700;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 9px; }}

#settingLabel {{ font-size: 14px; font-weight: 600; }}
#settingDesc {{ color: {text_dim}; font-size: 12px; }}
#badge {{
    background: {surface3};
    border-radius: 8px;
    padding: 5px 11px;
    color: {text_dim};
    font-size: 11px;
    font-weight: 700;
}}
#badgeAccent {{
    background: {accent_soft};
    border-radius: 8px;
    padding: 5px 11px;
    color: {accent};
    font-size: 11px;
    font-weight: 700;
}}
QToolTip {{
    background: {surface3};
    color: {text};
    border: 1px solid {border};
    border-radius: 8px;
    padding: 6px 10px;
}}
"""
