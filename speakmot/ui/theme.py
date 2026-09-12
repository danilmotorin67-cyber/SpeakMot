BG = "#0f1117"
SURFACE = "#171a23"
SURFACE_2 = "#1e222d"
BORDER = "#272c3a"
TEXT = "#e7e9ee"
TEXT_DIM = "#8b93a7"
ACCENT = "#5b8cff"
ACCENT_HOVER = "#6f9bff"
DANGER = "#ff5d5d"
SUCCESS = "#3ddc97"

FONT = "Segoe UI Variable, Segoe UI, Inter, sans-serif"

QSS = f"""
* {{
    font-family: {FONT};
    color: {TEXT};
    font-size: 14px;
}}

#root {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}

#titleBar {{
    background: transparent;
}}
#titleLabel {{
    color: {TEXT_DIM};
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.4px;
}}
#winBtn, #winBtnClose {{
    background: transparent;
    border: none;
    outline: none;
    border-radius: 6px;
    color: {TEXT_DIM};
    font-size: 15px;
    padding: 0px;
}}
#winBtn:hover {{
    background: {SURFACE_2};
    color: {TEXT};
}}
#winBtnClose:hover {{
    background: {DANGER};
    color: #ffffff;
}}

#sidebar {{
    background: {SURFACE};
    border-right: 1px solid {BORDER};
    border-top-left-radius: 14px;
    border-bottom-left-radius: 14px;
}}
#navBtn {{
    background: transparent;
    border: none;
    border-radius: 9px;
    padding: 10px 14px;
    text-align: left;
    color: {TEXT_DIM};
    font-size: 14px;
    font-weight: 500;
}}
#navBtn:hover {{
    background: {SURFACE_2};
    color: {TEXT};
}}
#navBtn:checked {{
    background: {SURFACE_2};
    color: {TEXT};
    font-weight: 600;
}}
#brand {{
    font-size: 17px;
    font-weight: 700;
    letter-spacing: 0.3px;
}}
#brandSub {{
    color: {TEXT_DIM};
    font-size: 11px;
    letter-spacing: 1.6px;
    font-weight: 600;
}}

#page {{
    background: {BG};
    border-top-right-radius: 14px;
    border-bottom-right-radius: 14px;
}}
#pageTitle {{
    font-size: 21px;
    font-weight: 700;
}}
#pageHint, #hint {{
    color: {TEXT_DIM};
    font-size: 13px;
}}

#card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
#cardTitle {{
    font-size: 12px;
    font-weight: 700;
    color: {TEXT_DIM};
    letter-spacing: 1.2px;
}}

#status {{
    font-size: 15px;
    font-weight: 600;
}}
#kbd {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 5px 10px;
    color: {TEXT};
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
    background: {ACCENT};
    border: none;
    border-radius: 9px;
    padding: 10px 18px;
    color: #ffffff;
    font-weight: 600;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: {SURFACE_2}; color: {TEXT_DIM}; }}

QPushButton#ghost {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 9px 16px;
    color: {TEXT};
    font-weight: 500;
}}
QPushButton#ghost:hover {{ border-color: {ACCENT}; color: {ACCENT}; }}

QComboBox, QLineEdit, QPlainTextEdit {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 8px 12px;
    selection-background-color: {ACCENT};
}}
QComboBox:hover, QLineEdit:hover, QPlainTextEdit:hover {{ border-color: #333a4d; }}
QComboBox:focus, QLineEdit:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 4px;
    outline: none;
    selection-background-color: {ACCENT};
}}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 9px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: #39415a; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

#overlay {{
    background: rgba(15, 17, 23, 235);
    border: 1px solid {BORDER};
    border-radius: 18px;
}}
#overlayText {{
    font-size: 13px;
    font-weight: 600;
    color: {TEXT};
}}
#overlayHint {{
    font-size: 11px;
    color: {TEXT_DIM};
}}

QProgressBar {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 8px;
    height: 16px;
    text-align: center;
    color: {TEXT};
    font-size: 11px;
    font-weight: 600;
}}
QProgressBar::chunk {{
    background: {ACCENT};
    border-radius: 7px;
}}

#settingLabel {{
    font-size: 14px;
    font-weight: 500;
}}
#settingDesc {{
    color: {TEXT_DIM};
    font-size: 12px;
}}
#badge {{
    background: {SURFACE_2};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 3px 9px;
    color: {TEXT_DIM};
    font-size: 11px;
    font-weight: 600;
}}
"""
