import threading

from PySide6.QtCore import QPoint, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFileDialog,
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

from .. import __version__, autostart, hotkeys, updater
from .. import engine as engine_states
from ..audio import list_input_devices
from ..output import copy_text
from ..textproc import format_replacements, parse_replacements
from . import theme
from .hotkey_edit import HotkeyEdit
from .models_page import ModelsPage
from .profiles_page import ProfilesPage
from .widgets import Card, MicButton, NavButton, StatusDot, ToggleSwitch, Waveform

LANGUAGES = {"Русский": "ru", "English": "en", "Автоопределение": "auto"}
MODES = {"Переключением": "toggle", "Удержанием": "hold"}
PASTE_METHODS = {"Вставкой (Ctrl+V)": "clipboard", "Вводом символов": "typing"}
THEMES = {"Тёмная": "dark", "Светлая": "light"}
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

    update_checked = Signal(bool, str, str)

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
        self.models_page = ModelsPage(self.controller)
        self.pages.addWidget(self.models_page)
        self.profiles_page = ProfilesPage(self.controller)
        self.pages.addWidget(self.profiles_page)
        self.pages.addWidget(self._build_settings_page())
        body.addWidget(self.pages, 1)

        self.update_checked.connect(self._on_update_checked)

        self._level_timer = QTimer(self)
        self._level_timer.timeout.connect(self._poll_level)
        self._level_timer.start(45)

    # --- построение интерфейса ---

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(228)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(6)

        brand = QLabel("SpeakMotor")
        brand.setObjectName("brand")
        subtitle = QLabel("ДИКТОВКА")
        subtitle.setObjectName("brandSub")
        layout.addWidget(brand)
        layout.addWidget(subtitle)
        layout.addSpacing(26)

        section = QLabel("РАЗДЕЛЫ")
        section.setObjectName("sidebarSection")
        layout.addWidget(section)
        layout.addSpacing(6)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        nav_items = (
            ("Запись", "mic"),
            ("История", "clock"),
            ("Модели", "box"),
            ("Профили", "sliders"),
            ("Настройки", "gear"),
        )
        for index, (label, icon) in enumerate(nav_items):
            button = NavButton(label, icon)
            button.clicked.connect(lambda _checked, i=index: self.pages.setCurrentIndex(i))
            self.nav_group.addButton(button, index)
            layout.addWidget(button)
        self.nav_group.button(0).setChecked(True)

        layout.addStretch(1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.model_badge = QLabel(self.cfg.model_size)
        self.model_badge.setObjectName("badgeAccent")
        self.model_badge.setAlignment(Qt.AlignCenter)
        footer.addWidget(self.model_badge)
        version = QLabel(f"v{__version__}")
        version.setObjectName("badge")
        version.setAlignment(Qt.AlignCenter)
        footer.addWidget(version)
        layout.addLayout(footer)
        return sidebar

    def _build_home_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 20, 36, 28)
        layout.setSpacing(18)

        layout.addStretch(1)

        self.mic_button = MicButton()
        self.mic_button.clicked.connect(self.controller.toggle_recording)
        mic_row = QHBoxLayout()
        mic_row.addStretch(1)
        mic_row.addWidget(self.mic_button)
        mic_row.addStretch(1)
        layout.addLayout(mic_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        status_row.addStretch(1)
        self.status_dot = StatusDot()
        status_row.addWidget(self.status_dot)
        self.status_label = QLabel("Готов к работе")
        self.status_label.setObjectName("status")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        hint_row = QHBoxLayout()
        hint_row.addStretch(1)
        prefix = QLabel("Нажмите")
        prefix.setObjectName("statusHint")
        self.hotkey_badge = QLabel(hotkeys.pretty(self.cfg.hotkey))
        self.hotkey_badge.setObjectName("kbd")
        suffix = QLabel("или кнопку выше")
        suffix.setObjectName("statusHint")
        hint_row.addWidget(prefix)
        hint_row.addWidget(self.hotkey_badge)
        hint_row.addWidget(suffix)
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
        export_button = QPushButton("Экспорт")
        export_button.setObjectName("ghost")
        export_button.setCursor(Qt.PointingHandCursor)
        export_button.clicked.connect(self._export_history)
        header.addWidget(export_button)

        clear_button = QPushButton("Очистить")
        clear_button.setObjectName("danger")
        clear_button.setCursor(Qt.PointingHandCursor)
        clear_button.clicked.connect(self._clear_history)
        header.addWidget(clear_button)
        layout.addLayout(header)

        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Поиск по истории")
        self.history_search.textChanged.connect(self._filter_history)
        layout.addWidget(self.history_search)

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
        self.hotkey_edit = HotkeyEdit(self.cfg.hotkey)
        self.hotkey_edit.setFixedWidth(210)
        hotkey_card.body().addLayout(
            self._setting_row(
                "Горячая клавиша",
                "Нажмите поле и задайте сочетание",
                self.hotkey_edit,
            )
        )

        self.language_hotkey_edit = HotkeyEdit(self.cfg.language_hotkey)
        self.language_hotkey_edit.setFixedWidth(210)
        hotkey_card.body().addLayout(
            self._setting_row(
                "Смена языка",
                "Переключает русский → английский → автоопределение",
                self.language_hotkey_edit,
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
        self.model_value = QLabel(self.cfg.model_size)
        self.model_value.setObjectName("settingDesc")
        open_models = QPushButton("Управление моделями")
        open_models.setObjectName("ghost")
        open_models.setCursor(Qt.PointingHandCursor)
        open_models.clicked.connect(lambda: self._go_to_page(2))
        model_card.body().addLayout(
            self._setting_row("Модель Whisper", self.model_value, open_models)
        )

        self.lang_combo = QComboBox()
        self.lang_combo.addItems(LANGUAGES.keys())
        self.lang_combo.setCurrentText(
            next(k for k, v in LANGUAGES.items() if v == self.cfg.language)
        )
        model_card.body().addLayout(
            self._setting_row("Язык", "Указание языка ускоряет распознавание", self.lang_combo)
        )
        self.translate_switch = ToggleSwitch(self.cfg.translate_to_english)
        model_card.body().addLayout(
            self._setting_row(
                "Переводить на английский",
                "Речь на любом языке — текст на английском",
                self.translate_switch,
            )
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

        self.commands_switch = ToggleSwitch(self.cfg.voice_commands)
        behavior_card.body().addLayout(
            self._setting_row(
                "Голосовые команды",
                "«точка», «запятая», «новый абзац» превращаются в знаки",
                self.commands_switch,
            )
        )

        self.preview_switch = ToggleSwitch(self.cfg.preview_before_paste)
        behavior_card.body().addLayout(
            self._setting_row(
                "Показывать перед вставкой",
                "Окно с текстом, который можно поправить или отклонить",
                self.preview_switch,
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

        # внешний вид
        appearance_card = Card("Внешний вид")
        self.theme_combo = QComboBox()
        for label, value in THEMES.items():
            self.theme_combo.addItem(label, value)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(self.cfg.theme)))
        self.theme_combo.currentIndexChanged.connect(self._preview_appearance)
        appearance_card.body().addLayout(self._setting_row("Тема", "", self.theme_combo))

        self.accent_combo = QComboBox()
        for label, value in theme.ACCENTS.items():
            self.accent_combo.addItem(label, value)
        self.accent_combo.setCurrentIndex(max(0, self.accent_combo.findData(self.cfg.accent)))
        self.accent_combo.currentIndexChanged.connect(self._preview_appearance)
        appearance_card.body().addLayout(
            self._setting_row("Акцентный цвет", "", self.accent_combo)
        )
        layout.addWidget(appearance_card)

        # обновления
        update_card = Card("Обновление")
        self.update_status = QLabel(f"Установлена версия {__version__}")
        self.update_status.setObjectName("settingDesc")
        self.update_status.setWordWrap(True)
        self.check_update_button = QPushButton("Проверить")
        self.check_update_button.setObjectName("ghost")
        self.check_update_button.setCursor(Qt.PointingHandCursor)
        self.check_update_button.clicked.connect(self._check_updates)
        update_card.body().addLayout(
            self._setting_row("Версия", self.update_status, self.check_update_button)
        )
        layout.addWidget(update_card)

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

    def _check_updates(self) -> None:
        self.check_update_button.setEnabled(False)
        self.update_status.setText("Проверяю…")

        def worker():
            self.update_checked.emit(*updater.check())

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_checked(self, available: bool, version: str, page: str) -> None:
        self.check_update_button.setEnabled(True)
        if available:
            self.update_status.setText(f"Доступна версия {version}")
            self.check_update_button.setText("Скачать")
            self.check_update_button.clicked.disconnect()
            self.check_update_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(page))
            )
        elif version:
            self.update_status.setText(f"Установлена последняя версия {__version__}")
        else:
            self.update_status.setText("Не удалось проверить обновления")

    def _preview_appearance(self) -> None:
        """Показывает тему сразу, не дожидаясь кнопки «Сохранить»."""
        self.controller.apply_appearance(
            self.theme_combo.currentData(), self.accent_combo.currentData()
        )

    def _go_to_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.nav_group.button(index).setChecked(True)

    def show_model(self, size: str) -> None:
        self.model_badge.setText(size)
        self.model_value.setText(size)

    # --- реакция на состояние ---

    def apply_state(self, state: str, message: str) -> None:
        recording = state == engine_states.RECORDING
        self.mic_button.set_recording(recording)
        self.mic_button.setEnabled(state != engine_states.LOADING)
        self.home_waveform.set_active(recording)

        dots = {
            engine_states.IDLE: "success",
            engine_states.RECORDING: "danger",
            engine_states.TRANSCRIBING: "accent",
            engine_states.LOADING: "accent",
            engine_states.ERROR: "danger",
        }
        role = dots.get(state, "success")
        self.status_dot.set_color(theme.color(role))
        self.home_waveform.set_role("danger" if recording else "accent")

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
        card.history_text = text
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

    def _filter_history(self, query: str) -> None:
        needle = query.strip().lower()
        for index in range(self.history_layout.count()):
            item = self.history_layout.itemAt(index)
            card = item.widget()
            if card is None:
                continue
            text = getattr(card, "history_text", "")
            card.setVisible(needle in text.lower())

    def _export_history(self) -> None:
        if not self.cfg.history:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить историю", "speakmot-history.txt", "Текст (*.txt)"
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n\n".join(self.cfg.history))
        except OSError as exc:
            self.history_search.setPlaceholderText(f"Не удалось сохранить: {exc}")

    def _clear_history(self) -> None:
        self.cfg.history.clear()
        self.cfg.save()
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.history_search.clear()

    # --- настройки ---

    def _save_settings(self) -> None:
        cfg = self.cfg
        cfg.hotkey = self.hotkey_edit.combo() or "ctrl+alt+space"
        cfg.hotkey_mode = MODES[self.mode_combo.currentText()]
        cfg.language = LANGUAGES[self.lang_combo.currentText()]
        cfg.input_device = self.device_combo.currentData()
        cfg.auto_paste = self.paste_switch.isChecked()
        cfg.paste_method = self.method_combo.currentData()
        cfg.sound_feedback = self.sound_switch.isChecked()
        cfg.silence_stop = self.silence_combo.currentData()
        cfg.replacements = parse_replacements(self.replacements_edit.toPlainText())

        cfg.voice_commands = self.commands_switch.isChecked()
        cfg.translate_to_english = self.translate_switch.isChecked()
        cfg.language_hotkey = self.language_hotkey_edit.combo()
        cfg.preview_before_paste = self.preview_switch.isChecked()
        cfg.theme = self.theme_combo.currentData()
        cfg.accent = self.accent_combo.currentData()

        cfg.autostart = self.autostart_switch.isChecked()
        try:
            autostart.set_enabled(cfg.autostart)
        except OSError as exc:
            self.status_label.setText(f"Не удалось изменить автозапуск: {exc}")

        cfg.save()

        self.hotkey_badge.setText(hotkeys.pretty(cfg.hotkey))
        self.controller.reload(model_changed=False)

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
