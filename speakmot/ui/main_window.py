import threading

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import autostart
from .. import engine as engine_states
from ..audio import list_input_devices
from ..output import copy_text
from ..textproc import format_replacements, parse_replacements
from .widgets import Card, MicButton, ToggleSwitch, Waveform

MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
MODEL_HINTS = {
    "tiny": "75 МБ · мгновенно, качество низкое",
    "base": "145 МБ · быстро, качество среднее",
    "small": "490 МБ · баланс скорости и качества",
    "medium": "1.5 ГБ · медленнее, качество высокое",
    "large-v3": "3 ГБ · лучшее качество, нужна видеокарта",
}
LANGUAGES = {"Русский": "ru", "English": "en", "Автоопределение": "auto"}
MODES = {"Переключением": "toggle", "Удержанием": "hold"}
PASTE_METHODS = {"Вставкой (Ctrl+V)": "clipboard", "Вводом символов": "typing"}
SILENCE_OPTIONS = {
    "Выключен": 0.0,
    "Через 1 секунду": 1.0,
    "Через 2 секунды": 2.0,
    "Через 3 секунды": 3.0,
}


class TitleBar(QWidget):
    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self.setObjectName("titleBar")
        self.setFixedHeight(44)
        self._window = window
        self._drag_offset: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 10, 0)
        layout.setSpacing(6)

        title = QLabel("SPEAKMOT")
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        layout.addStretch(1)

        for text, name, slot in (
            ("—", "winBtn", window.showMinimized),
            ("✕", "winBtnClose", window.hide),
        ):
            button = QPushButton(text)
            button.setObjectName(name if name == "winBtnClose" else "winBtn")
            if name == "winBtnClose":
                button.setProperty("class", "close")
                button.setObjectName("winBtnClose")
            button.setFixedSize(32, 30)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(slot)
            layout.addWidget(button)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None


class MainWindow(QWidget):
    """Главное окно: боковая навигация и три страницы."""

    hotkey_captured = Signal(str)

    def __init__(self, app_controller):
        super().__init__()
        self.controller = app_controller
        self.cfg = app_controller.cfg

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(880, 600)
        self.setMinimumSize(780, 540)

        root = QFrame()
        root.setObjectName("root")
        wrapper = QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(root)

        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(TitleBar(self))

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root_layout.addLayout(body)

        body.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        self.pages.setObjectName("page")
        self.pages.addWidget(self._build_home_page())
        self.pages.addWidget(self._build_history_page())
        self.pages.addWidget(self._build_settings_page())
        body.addWidget(self.pages, 1)

        self.hotkey_captured.connect(self._on_hotkey_captured)

        self._level_timer = QTimer(self)
        self._level_timer.timeout.connect(self._poll_level)
        self._level_timer.start(45)

    # --- построение интерфейса ---

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(212)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(6)

        brand = QLabel("SpeakMot")
        brand.setObjectName("brand")
        subtitle = QLabel("ГОЛОС В ТЕКСТ")
        subtitle.setObjectName("brandSub")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(22)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        for index, label in enumerate(("  Запись", "  История", "  Настройки")):
            button = QPushButton(label)
            button.setObjectName("navBtn")
            button.setCheckable(True)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda _checked, i=index: self.pages.setCurrentIndex(i))
            self.nav_group.addButton(button, index)
            layout.addWidget(button)
        self.nav_group.button(0).setChecked(True)

        layout.addStretch(1)
        self.model_badge = QLabel(self.cfg.model_size)
        self.model_badge.setObjectName("badge")
        self.model_badge.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.model_badge)
        return sidebar

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 26)
        layout.setSpacing(16)

        layout.addStretch(1)

        self.mic_button = MicButton()
        self.mic_button.clicked.connect(self.controller.toggle_recording)
        mic_row = QHBoxLayout()
        mic_row.addStretch(1)
        mic_row.addWidget(self.mic_button)
        mic_row.addStretch(1)
        layout.addLayout(mic_row)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setObjectName("status")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        hint_row = QHBoxLayout()
        hint_row.addStretch(1)
        prefix = QLabel("Горячая клавиша")
        prefix.setObjectName("hint")
        self.hotkey_badge = QLabel(self._pretty_hotkey(self.cfg.hotkey))
        self.hotkey_badge.setObjectName("kbd")
        hint_row.addWidget(prefix)
        hint_row.addWidget(self.hotkey_badge)
        hint_row.addStretch(1)
        layout.addLayout(hint_row)

        self.home_waveform = Waveform(bars=40)
        self.home_waveform.setFixedHeight(58)
        layout.addWidget(self.home_waveform)

        layout.addStretch(1)

        result_card = Card("Последний результат")
        self.result_label = QLabel("Здесь появится распознанный текст.")
        self.result_label.setObjectName("resultText")
        self.result_label.setWordWrap(True)
        self.result_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        result_card.add(self.result_label)

        copy_button = QPushButton("Копировать")
        copy_button.setObjectName("ghost")
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.clicked.connect(lambda: copy_text(self.result_label.text()))
        button_row = QHBoxLayout()
        button_row.addStretch(1)
        button_row.addWidget(copy_button)
        result_card.body().addLayout(button_row)

        layout.addWidget(result_card)
        if self.cfg.history:
            self.result_label.setText(self.cfg.history[0])
        return page

    def _build_history_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 24, 30, 26)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("История")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch(1)
        clear_button = QPushButton("Очистить")
        clear_button.setObjectName("ghost")
        clear_button.setCursor(Qt.PointingHandCursor)
        clear_button.clicked.connect(self._clear_history)
        header.addWidget(clear_button)
        layout.addLayout(header)

        scroll = _scroll_area()
        container = QWidget()
        self.history_layout = QVBoxLayout(container)
        self.history_layout.setContentsMargins(0, 0, 8, 0)
        self.history_layout.setSpacing(10)
        self.history_layout.addStretch(1)
        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        for text in self.cfg.history:
            self._append_history_card(text, to_top=False)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(30, 24, 30, 26)
        outer.setSpacing(14)

        title = QLabel("Настройки")
        title.setObjectName("pageTitle")
        outer.addWidget(title)

        scroll = _scroll_area()
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(14)
        scroll.setWidget(container)
        outer.addWidget(scroll, 1)

        # горячая клавиша
        hotkey_card = Card("Управление")
        self.hotkey_edit = QLineEdit(self.cfg.hotkey)
        self.capture_button = QPushButton("Назначить")
        self.capture_button.setObjectName("ghost")
        self.capture_button.setCursor(Qt.PointingHandCursor)
        self.capture_button.clicked.connect(self._capture_hotkey)
        hotkey_card.body().addLayout(
            self._setting_row(
                "Горячая клавиша",
                "Комбинация для старта и остановки записи",
                self.hotkey_edit,
                self.capture_button,
            )
        )

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(MODES.keys())
        self.mode_combo.setCurrentText(
            next(k for k, v in MODES.items() if v == self.cfg.hotkey_mode)
        )
        hotkey_card.body().addLayout(
            self._setting_row("Режим", "Как срабатывает горячая клавиша", self.mode_combo)
        )
        layout.addWidget(hotkey_card)

        # распознавание
        model_card = Card("Распознавание")
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_SIZES)
        self.model_combo.setCurrentText(self.cfg.model_size)
        self.model_hint = QLabel(MODEL_HINTS[self.cfg.model_size])
        self.model_hint.setObjectName("settingDesc")
        self.model_combo.currentTextChanged.connect(
            lambda value: self.model_hint.setText(MODEL_HINTS.get(value, ""))
        )
        model_card.body().addLayout(
            self._setting_row("Модель Whisper", self.model_hint, self.model_combo)
        )

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(LANGUAGES.keys())
        self.lang_combo.setCurrentText(
            next(k for k, v in LANGUAGES.items() if v == self.cfg.language)
        )
        model_card.body().addLayout(
            self._setting_row("Язык", "Указание языка ускоряет распознавание", self.lang_combo)
        )
        layout.addWidget(model_card)

        # звук
        audio_card = Card("Звук")
        self.devices = list_input_devices()
        self.device_combo = QComboBox()
        self.device_combo.addItem("По умолчанию", None)
        for index, name in self.devices:
            self.device_combo.addItem(name, index)
        position = self.device_combo.findData(self.cfg.input_device)
        self.device_combo.setCurrentIndex(max(0, position))
        audio_card.body().addLayout(self._setting_row("Микрофон", "", self.device_combo))

        self.silence_combo = QComboBox()
        for label, value in SILENCE_OPTIONS.items():
            self.silence_combo.addItem(label, value)
        silence_position = self.silence_combo.findData(self.cfg.silence_stop)
        self.silence_combo.setCurrentIndex(max(0, silence_position))
        audio_card.body().addLayout(
            self._setting_row(
                "Автостоп по тишине",
                "Запись закончится сама, когда вы замолчите",
                self.silence_combo,
            )
        )
        layout.addWidget(audio_card)

        # поведение
        behavior_card = Card("Поведение")
        self.paste_switch = ToggleSwitch(self.cfg.auto_paste)
        behavior_card.body().addLayout(
            self._setting_row(
                "Автовставка",
                "Вставлять текст в активное окно через Ctrl+V",
                self.paste_switch,
            )
        )
        self.method_combo = QComboBox()
        for label, value in PASTE_METHODS.items():
            self.method_combo.addItem(label, value)
        method_position = self.method_combo.findData(self.cfg.paste_method)
        self.method_combo.setCurrentIndex(max(0, method_position))
        behavior_card.body().addLayout(
            self._setting_row(
                "Способ вставки",
                "Если Ctrl+V не срабатывает, выберите ввод символами",
                self.method_combo,
            )
        )

        self.sound_switch = ToggleSwitch(self.cfg.sound_feedback)
        behavior_card.body().addLayout(
            self._setting_row(
                "Звуковой сигнал", "Короткий сигнал в начале и в конце записи", self.sound_switch
            )
        )

        self.autostart_switch = ToggleSwitch(self.cfg.autostart)
        behavior_card.body().addLayout(
            self._setting_row(
                "Запуск вместе с Windows",
                "Приложение будет стартовать свёрнутым в трей",
                self.autostart_switch,
            )
        )
        layout.addWidget(behavior_card)

        # словарь замен
        replacements_card = Card("Словарь замен")
        description = QLabel(
            "По одной паре в строке: «было = стало». Применяется к каждому "
            "распознанному тексту без учёта регистра."
        )
        description.setObjectName("settingDesc")
        description.setWordWrap(True)
        replacements_card.add(description)

        self.replacements_edit = QPlainTextEdit(format_replacements(self.cfg.replacements))
        self.replacements_edit.setPlaceholderText("пайтон = Python\nгит хаб = GitHub")
        self.replacements_edit.setFixedHeight(120)
        replacements_card.add(self.replacements_edit)
        layout.addWidget(replacements_card)
        layout.addStretch(1)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("primary")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self._save_settings)
        save_row.addWidget(self.save_button)
        outer.addLayout(save_row)
        return page

    def _setting_row(self, label: str, description, *widgets) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(12)
        column = QVBoxLayout()
        column.setSpacing(1)
        name = QLabel(label)
        name.setObjectName("settingLabel")
        column.addWidget(name)
        if isinstance(description, QLabel):
            column.addWidget(description)
        elif description:
            desc = QLabel(description)
            desc.setObjectName("settingDesc")
            desc.setWordWrap(True)
            column.addWidget(desc)
        row.addLayout(column, 1)
        for widget in widgets:
            if isinstance(widget, (QComboBox, QLineEdit)):
                widget.setMinimumWidth(150)
                widget.setMaximumWidth(210)
            row.addWidget(widget, 0)
        return row

    # --- реакция на состояние ---

    def _pretty_hotkey(self, hotkey: str) -> str:
        return " + ".join(part.strip().title() for part in hotkey.split("+"))

    def apply_state(self, state: str, message: str) -> None:
        recording = state == engine_states.RECORDING
        self.mic_button.set_recording(recording)
        self.mic_button.setEnabled(state != engine_states.LOADING)
        self.home_waveform.set_active(recording)

        texts = {
            engine_states.IDLE: "Готов к работе",
            engine_states.RECORDING: "Слушаю…",
            engine_states.TRANSCRIBING: "Распознаю речь…",
            engine_states.LOADING: message or "Загрузка модели…",
            engine_states.ERROR: message or "Ошибка",
        }
        self.status_label.setText(texts.get(state, message))

    def show_result(self, text: str) -> None:
        self.result_label.setText(text)
        self._append_history_card(text, to_top=True)

    def _poll_level(self) -> None:
        if self.controller.engine.recorder.is_recording:
            self.home_waveform.push(self.controller.engine.recorder.level)

    # --- история ---

    def _append_history_card(self, text: str, to_top: bool) -> None:
        card = Card()
        label = QLabel(text)
        label.setObjectName("resultText")
        label.setWordWrap(True)
        card.add(label)

        copy_button = QPushButton("Копировать")
        copy_button.setObjectName("ghost")
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.clicked.connect(lambda: copy_text(text))
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(copy_button)
        card.body().addLayout(row)

        index = 0 if to_top else self.history_layout.count() - 1
        self.history_layout.insertWidget(index, card)

    def _clear_history(self) -> None:
        self.cfg.history.clear()
        self.cfg.save()
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    # --- настройки ---

    def _capture_hotkey(self) -> None:
        self.capture_button.setText("Нажмите…")
        self.capture_button.setEnabled(False)

        def worker():
            import keyboard

            try:
                combo = keyboard.read_hotkey(suppress=False)
            except Exception:
                combo = ""
            self.hotkey_captured.emit(combo)

        threading.Thread(target=worker, daemon=True).start()

    def _on_hotkey_captured(self, combo: str) -> None:
        self.capture_button.setText("Назначить")
        self.capture_button.setEnabled(True)
        if combo:
            self.hotkey_edit.setText(combo)

    def _save_settings(self) -> None:
        cfg = self.cfg
        cfg.hotkey = self.hotkey_edit.text().strip() or "ctrl+alt+space"
        cfg.hotkey_mode = MODES[self.mode_combo.currentText()]
        cfg.language = LANGUAGES[self.lang_combo.currentText()]
        cfg.input_device = self.device_combo.currentData()
        cfg.auto_paste = self.paste_switch.isChecked()
        cfg.paste_method = self.method_combo.currentData()
        cfg.sound_feedback = self.sound_switch.isChecked()
        cfg.silence_stop = self.silence_combo.currentData()
        cfg.replacements = parse_replacements(self.replacements_edit.toPlainText())

        cfg.autostart = self.autostart_switch.isChecked()
        try:
            autostart.set_enabled(cfg.autostart)
        except OSError as exc:
            self.status_label.setText(f"Не удалось изменить автозапуск: {exc}")

        model_changed = cfg.model_size != self.model_combo.currentText()
        cfg.model_size = self.model_combo.currentText()
        cfg.save()

        self.hotkey_badge.setText(self._pretty_hotkey(cfg.hotkey))
        self.model_badge.setText(cfg.model_size)
        self.controller.reload(model_changed)

        self.save_button.setText("Сохранено ✓")
        QTimer.singleShot(1500, lambda: self.save_button.setText("Сохранить"))

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide()


def _scroll_area() -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    return scroll


def center_on_screen(window: QWidget) -> None:
    screen = QApplication.primaryScreen()
    if screen is None:
        return
    geometry = screen.availableGeometry()
    window.move(
        geometry.center().x() - window.width() // 2,
        geometry.center().y() - window.height() // 2,
    )
