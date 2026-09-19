import threading

from PySide6.QtCore import QPoint, Qt, QTime, QTimer, QUrl, Signal
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

from .. import __version__, autostart, hotkeys, i18n, journal, updater
from .. import engine as engine_states
from ..audio import list_input_devices
from ..i18n import tr
from ..output import copy_text
from ..textproc import format_replacements, parse_replacements
from . import theme
from .hotkey_edit import HotkeyEdit
from .models_page import ModelsPage
from .profiles_page import ProfilesPage
from .widgets import (
    BrandMark,
    Card,
    EmptyState,
    MicButton,
    NavButton,
    QuietComboBox,
    StatTile,
    StatusDot,
    ToggleSwitch,
    Waveform,
    divider,
)

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
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(6)

        layout.addStretch(1)

        self.caption = QLabel(tr("Запись"))
        self.caption.setObjectName("titleLabel")
        self.caption.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.caption)
        layout.addStretch(1)

        self.maximize_button = None
        for text, name, slot in (
            ("—", "winBtn", window.showMinimized),
            ("□", "winBtn", self.toggle_maximized),
            ("✕", "winBtnClose", window.hide),
        ):
            button = QPushButton(text)
            button.setObjectName(name)
            button.setFixedSize(32, 30)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(slot)
            layout.addWidget(button)
            if slot == self.toggle_maximized:
                self.maximize_button = button
                button.setToolTip(tr("Развернуть на весь экран"))

    def toggle_maximized(self) -> None:
        """Разворачивает окно на весь экран и возвращает обратно."""
        window = self._window
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()
        self.sync_maximize_button()

    def sync_maximize_button(self) -> None:
        maximized = self._window.isMaximized()
        self.maximize_button.setText("❐" if maximized else "□")
        self.maximize_button.setToolTip(
            tr("Вернуть прежний размер") if maximized else tr("Развернуть на весь экран")
        )

    def mouseDoubleClickEvent(self, event):
        self.toggle_maximized()

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
        self.title_bar = TitleBar(self)
        root_layout.addWidget(self.title_bar)

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

        root_layout.addWidget(self._build_status_bar())

        self.pages.currentChanged.connect(self._sync_caption)
        self.update_checked.connect(self._on_update_checked)

        self._level_timer = QTimer(self)
        self._level_timer.timeout.connect(self._poll_level)
        self._level_timer.start(45)

        # безрамочное окно само по себе не тянется за края
        self.setMouseTracking(True)

    # --- построение интерфейса ---

    def _build_status_bar(self) -> QWidget:
        """Тонкая строка внизу окна: подсказка слева, часы справа."""
        bar = QWidget()
        bar.setObjectName("statusBar")
        bar.setFixedHeight(26)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(10)

        self.status_bar_text = QLabel(tr("готов"))
        self.status_bar_text.setObjectName("statusBarText")
        layout.addWidget(self.status_bar_text)
        layout.addStretch(1)

        self.clock = QLabel("")
        self.clock.setObjectName("clock")
        layout.addWidget(self.clock)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick_clock)
        self._clock_timer.start(1000)
        self._tick_clock()
        return bar

    def _tick_clock(self) -> None:
        self.clock.setText(QTime.currentTime().toString("HH:mm:ss"))

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(228)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 8, 16, 16)
        layout.setSpacing(6)

        self.brand_mark = BrandMark("SPEAKMOTOR")
        subtitle = QLabel(tr("ДИКТОВКА"))
        subtitle.setObjectName("brandSub")
        layout.addWidget(self.brand_mark)
        layout.addWidget(subtitle)
        layout.addSpacing(26)

        section = QLabel(tr("РАЗДЕЛЫ"))
        section.setObjectName("sidebarSection")
        layout.addWidget(section)
        layout.addSpacing(6)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        nav_items = (
            (tr("Запись"), "mic"),
            (tr("История"), "clock"),
            (tr("Модели"), "box"),
            (tr("Профили"), "sliders"),
            (tr("Настройки"), "gear"),
        )
        for index, (label, icon) in enumerate(nav_items):
            button = NavButton(label, icon)
            button.clicked.connect(lambda _checked, i=index: self._go_to_page(i))
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
        self.status_label = QLabel(tr("Готов к работе"))
        self.status_label.setObjectName("status")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        hint_row = QHBoxLayout()
        hint_row.addStretch(1)
        prefix = QLabel(tr("Нажмите"))
        prefix.setObjectName("statusHint")
        self.hotkey_badge = QLabel(hotkeys.pretty(self.cfg.hotkey))
        self.hotkey_badge.setObjectName("kbd")
        suffix = QLabel(tr("или кнопку выше"))
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

        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        self.tile_words = StatTile("0", tr("СЛОВ"))
        self.tile_count = StatTile("0", tr("ДИКТОВОК"))
        self.tile_minutes = StatTile("0", tr("МИНУТ"))
        for tile in (self.tile_words, self.tile_count, self.tile_minutes):
            tiles.addWidget(tile, 1)
        layout.addLayout(tiles)
        self._refresh_stats()

        result_card = Card(tr("Последний результат"))
        self.result_label = QLabel(tr("Здесь появится распознанный текст."))
        self.result_label.setObjectName("resultText")
        self.result_label.setWordWrap(True)
        self.result_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        result_card.add(self.result_label)

        copy_button = QPushButton(tr("Копировать"))
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
        title = QLabel(tr("История"))
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch(1)
        export_button = QPushButton(tr("Экспорт"))
        export_button.setObjectName("ghost")
        export_button.setCursor(Qt.PointingHandCursor)
        export_button.clicked.connect(self._export_history)
        header.addWidget(export_button)

        clear_button = QPushButton(tr("Очистить"))
        clear_button.setObjectName("danger")
        clear_button.setCursor(Qt.PointingHandCursor)
        clear_button.clicked.connect(self._clear_history)
        header.addWidget(clear_button)
        layout.addLayout(header)

        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText(tr("Поиск по истории"))
        self.history_search.textChanged.connect(self._filter_history)
        layout.addWidget(self.history_search)

        scroll = _scroll_area()
        container = QWidget()
        self.history_layout = QVBoxLayout(container)
        self.history_layout.setContentsMargins(0, 0, 8, 0)
        self.history_layout.setSpacing(10)
        self.history_layout.addStretch(1)
        scroll.setWidget(container)
        self.history_scroll = scroll
        layout.addWidget(scroll, 1)

        self.history_empty = EmptyState(
            "clock",
            tr("История пуста"),
            tr("Здесь появится всё, что вы надиктуете."),
        )
        layout.addWidget(self.history_empty, 1)

        for text in self.cfg.history:
            self._append_history_card(text, to_top=False)
        self._update_history_visibility()
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(30, 24, 30, 26)
        outer.setSpacing(14)

        title = QLabel(tr("Настройки"))
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
        hotkey_card = Card(tr("Управление"))
        self.hotkey_edit = HotkeyEdit(self.cfg.hotkey)
        self.hotkey_edit.setFixedWidth(210)
        self._add_setting(
            hotkey_card,
            tr("Горячая клавиша"),
            tr("Нажмите поле и задайте сочетание"),
            self.hotkey_edit,
        )

        self.language_hotkey_edit = HotkeyEdit(self.cfg.language_hotkey)
        self.language_hotkey_edit.setFixedWidth(210)
        self._add_setting(
            hotkey_card,
            tr("Смена языка"),
            tr("Переключает русский → английский → автоопределение"),
            self.language_hotkey_edit,
        )

        self.repeat_hotkey_edit = HotkeyEdit(self.cfg.repeat_hotkey)
        self.repeat_hotkey_edit.setFixedWidth(210)
        self._add_setting(
            hotkey_card,
            tr("Повторить вставку"),
            tr("Вставляет последний распознанный текст ещё раз"),
            self.repeat_hotkey_edit,
        )

        self.mode_combo = QuietComboBox()
        for label, value in MODES.items():
            self.mode_combo.addItem(tr(label), value)
        self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(self.cfg.hotkey_mode)))
        self._add_setting(
            hotkey_card,
            tr("Режим"), tr("Как срабатывает горячая клавиша"), self.mode_combo
        )
        layout.addWidget(hotkey_card)

        # распознавание
        model_card = Card(tr("Распознавание"))
        self.model_value = QLabel(self.cfg.model_size)
        self.model_value.setObjectName("settingDesc")
        open_models = QPushButton(tr("Управление моделями"))
        open_models.setObjectName("ghost")
        open_models.setCursor(Qt.PointingHandCursor)
        open_models.clicked.connect(lambda: self._go_to_page(2))
        self._add_setting(
            model_card,
            tr("Модель Whisper"), self.model_value, open_models
        )

        self.lang_combo = QuietComboBox()
        for label, value in LANGUAGES.items():
            self.lang_combo.addItem(tr(label), value)
        self.lang_combo.setCurrentIndex(max(0, self.lang_combo.findData(self.cfg.language)))
        self._add_setting(
            model_card,
            tr("Язык"), tr("Указание языка ускоряет распознавание"), self.lang_combo
        )
        self.translate_switch = ToggleSwitch(self.cfg.translate_to_english)
        self._add_setting(
            model_card,
            tr("Переводить на английский"),
            tr("Речь на любом языке — текст на английском"),
            self.translate_switch,
        )
        layout.addWidget(model_card)

        # звук
        audio_card = Card(tr("Звук"))
        self.devices = list_input_devices()
        self.device_combo = QuietComboBox()
        self.device_combo.addItem(tr("По умолчанию"), None)
        for index, name in self.devices:
            self.device_combo.addItem(name, index)
        position = self.device_combo.findData(self.cfg.input_device)
        self.device_combo.setCurrentIndex(max(0, position))
        self._add_setting(
            audio_card,
            tr("Микрофон"), "", self.device_combo
        )

        self.silence_combo = QuietComboBox()
        for label, value in SILENCE_OPTIONS.items():
            self.silence_combo.addItem(tr(label), value)
        silence_position = self.silence_combo.findData(self.cfg.silence_stop)
        self.silence_combo.setCurrentIndex(max(0, silence_position))
        self._add_setting(
            audio_card,
            tr("Автостоп по тишине"),
            tr("Запись закончится сама, когда вы замолчите"),
            self.silence_combo,
        )
        layout.addWidget(audio_card)

        # поведение
        behavior_card = Card(tr("Поведение"))
        self.paste_switch = ToggleSwitch(self.cfg.auto_paste)
        self._add_setting(
            behavior_card,
            tr("Автовставка"),
            tr("Вставлять текст в активное окно через Ctrl+V"),
            self.paste_switch,
        )
        self.method_combo = QuietComboBox()
        for label, value in PASTE_METHODS.items():
            self.method_combo.addItem(tr(label), value)
        method_position = self.method_combo.findData(self.cfg.paste_method)
        self.method_combo.setCurrentIndex(max(0, method_position))
        self._add_setting(
            behavior_card,
            tr("Способ вставки"),
            tr("Если Ctrl+V не срабатывает, выберите ввод символами"),
            self.method_combo,
        )

        self.sound_switch = ToggleSwitch(self.cfg.sound_feedback)
        self._add_setting(
            behavior_card,
            tr("Звуковой сигнал"),
            tr("Короткий сигнал в начале и в конце записи"),
            self.sound_switch,
        )

        self.commands_switch = ToggleSwitch(self.cfg.voice_commands)
        self._add_setting(
            behavior_card,
            tr("Голосовые команды"),
            tr("«точка», «запятая», «новый абзац» превращаются в знаки"),
            self.commands_switch,
        )

        self.streaming_switch = ToggleSwitch(self.cfg.streaming)
        self._add_setting(
            behavior_card,
            tr("Показывать по ходу речи"),
            tr("Текст появляется в панели ещё во время диктовки"),
            self.streaming_switch,
        )

        self.preview_switch = ToggleSwitch(self.cfg.preview_before_paste)
        self._add_setting(
            behavior_card,
            tr("Показывать перед вставкой"),
            tr("Окно с текстом, который можно поправить или отклонить"),
            self.preview_switch,
        )

        self.autostart_switch = ToggleSwitch(self.cfg.autostart)
        self._add_setting(
            behavior_card,
            tr("Запуск вместе с Windows"),
            tr("Приложение будет стартовать свёрнутым в трей"),
            self.autostart_switch,
        )
        layout.addWidget(behavior_card)

        # внешний вид
        appearance_card = Card(tr("Внешний вид"))
        self.theme_combo = QuietComboBox()
        for label, value in THEMES.items():
            self.theme_combo.addItem(tr(label), value)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(self.cfg.theme)))
        self.theme_combo.currentIndexChanged.connect(self._preview_appearance)
        self._add_setting(
            appearance_card,
            tr("Тема"), "", self.theme_combo
        )

        self.accent_combo = QuietComboBox()
        for label, value in theme.ACCENTS.items():
            self.accent_combo.addItem(tr(label), value)
        saved_accent = theme.normalize_accent(self.cfg.accent)
        self.accent_combo.setCurrentIndex(max(0, self.accent_combo.findData(saved_accent)))
        self.accent_combo.currentIndexChanged.connect(self._preview_appearance)
        self._add_setting(
            appearance_card,
            tr("Акцентный цвет"), "", self.accent_combo
        )
        self.ui_language_combo = QuietComboBox()
        for label, value in i18n.LANGUAGES.items():
            self.ui_language_combo.addItem(label, value)
        self.ui_language_combo.setCurrentIndex(
            max(0, self.ui_language_combo.findData(self.cfg.ui_language))
        )
        self.ui_language_combo.currentIndexChanged.connect(self._switch_ui_language)
        self._add_setting(
            appearance_card,
            tr("Язык интерфейса"),
            tr("Меняется сразу, перезапуск не нужен"),
            self.ui_language_combo,
        )
        layout.addWidget(appearance_card)

        # обновления
        update_card = Card(tr("Обновление"))
        self.update_status = QLabel(tr("Установлена версия ") + __version__)
        self.update_status.setObjectName("settingDesc")
        self.update_status.setWordWrap(True)
        self.check_update_button = QPushButton(tr("Проверить"))
        self.check_update_button.setObjectName("ghost")
        self.check_update_button.setCursor(Qt.PointingHandCursor)
        self.check_update_button.clicked.connect(self._check_updates)
        self._add_setting(
            update_card,
            tr("Версия"), self.update_status, self.check_update_button
        )
        layout.addWidget(update_card)

        journal_card = Card(tr("Диагностика"))
        journal_hint = QLabel(
            tr("Журнал пишется при каждом запуске. Если что-то пошло не так, "
            "он ответит на вопрос «что именно».")
        )
        journal_hint.setObjectName("settingDesc")
        journal_hint.setWordWrap(True)
        open_journal = QPushButton(tr("Открыть журнал"))
        open_journal.setObjectName("ghost")
        open_journal.setCursor(Qt.PointingHandCursor)
        open_journal.clicked.connect(self._open_journal)
        self._add_setting(
            journal_card,
            tr("Журнал работы"), journal_hint, open_journal
        )
        layout.addWidget(journal_card)

        # словарь замен
        replacements_card = Card(tr("Словарь замен"))
        description = QLabel(
            tr("По одной паре в строке: «было = стало». Применяется к каждому "
            "распознанному тексту без учёта регистра.")
        )
        description.setObjectName("settingDesc")
        description.setWordWrap(True)
        replacements_card.add(description)

        self.replacements_edit = QPlainTextEdit(format_replacements(self.cfg.replacements))
        self.replacements_edit.setPlaceholderText(tr("пайтон = Python\nгит хаб = GitHub"))
        self.replacements_edit.setFixedHeight(120)
        replacements_card.add(self.replacements_edit)
        layout.addWidget(replacements_card)
        layout.addStretch(1)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_button = QPushButton(tr("Сохранить"))
        self.save_button.setObjectName("primary")
        self.save_button.setCursor(Qt.PointingHandCursor)
        self.save_button.clicked.connect(self._save_settings)
        save_row.addWidget(self.save_button)
        outer.addLayout(save_row)
        return page

    def _add_setting(self, card, label: str, description, *widgets) -> None:
        """Добавляет строку настройки, отделяя её от предыдущей линией."""
        body = card.body()
        # первый элемент карточки — её заголовок, после него линия не нужна
        if body.count() > 1:
            body.addWidget(divider())
        body.addLayout(self._setting_row(label, description, *widgets))

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

    def _open_journal(self) -> None:
        path = journal.log_path()
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _check_updates(self) -> None:
        self.check_update_button.setEnabled(False)
        self.update_status.setText(tr("Проверяю…"))

        def worker():
            self.update_checked.emit(*updater.check())

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_checked(self, available: bool, version: str, page: str) -> None:
        self.check_update_button.setEnabled(True)
        if available:
            self.update_status.setText(tr("Доступна версия ") + version)
            self.check_update_button.setText(tr("Скачать"))
            self.check_update_button.clicked.disconnect()
            self.check_update_button.clicked.connect(
                lambda: QDesktopServices.openUrl(QUrl(page))
            )
        elif version:
            self.update_status.setText(tr("Установлена последняя версия ") + __version__)
        else:
            self.update_status.setText(tr("Не удалось проверить обновления"))

    def _switch_ui_language(self) -> None:
        """Язык интерфейса виден только после пересборки окна."""
        code = self.ui_language_combo.currentData()
        if code == self.cfg.ui_language:
            return
        self.cfg.ui_language = code
        self.cfg.save()
        self.controller.apply_ui_language(code)

    def _preview_appearance(self) -> None:
        """Показывает тему сразу, не дожидаясь кнопки «Сохранить»."""
        self.controller.apply_appearance(
            self.theme_combo.currentData(), self.accent_combo.currentData()
        )

    def _refresh_stats(self) -> None:
        stats = self.cfg.stats
        self.tile_words.set_value(f"{int(stats.get('words', 0))}")
        self.tile_count.set_value(f"{int(stats.get('count', 0))}")
        self.tile_minutes.set_value(f"{stats.get('seconds', 0) / 60:.0f}")

    def changeEvent(self, event):
        super().changeEvent(event)
        # событие приходит и во время сборки окна, когда панели ещё нет
        if getattr(self, "title_bar", None) is not None:
            self.title_bar.sync_maximize_button()

    def refresh_icons(self) -> None:
        """Иконки меню нарисованы в цвет темы, после смены их надо перерисовать."""
        for button in self.nav_group.buttons():
            button.refresh_icon()
        self.brand_mark.refresh_theme()

    def _go_to_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        self.nav_group.button(index).setChecked(True)

    def _sync_caption(self, index: int) -> None:
        button = self.nav_group.button(index)
        if button is not None:
            self.title_bar.caption.setText(button.text())
            button.setChecked(True)

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
            engine_states.IDLE: tr("Готов к работе"),
            engine_states.RECORDING: tr("Слушаю…"),
            engine_states.TRANSCRIBING: tr("Распознаю речь…"),
            engine_states.LOADING: message or tr("Загрузка модели…"),
            engine_states.ERROR: message or tr("Ошибка"),
        }
        self.status_label.setText(texts.get(state, message))
        self.status_bar_text.setText(texts.get(state, message).lower().rstrip("…"))

    def show_result(self, text: str) -> None:
        self.result_label.setText(text)
        self._refresh_stats()
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

        copy_button = QPushButton(tr("Копировать"))
        copy_button.setObjectName("ghost")
        copy_button.setCursor(Qt.PointingHandCursor)
        copy_button.clicked.connect(lambda: copy_text(text))
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(copy_button)
        card.body().addLayout(row)

        index = 0 if to_top else self.history_layout.count() - 1
        self.history_layout.insertWidget(index, card)
        self._update_history_visibility()

    def _update_history_visibility(self) -> None:
        """Пустой список без объяснения выглядит как поломка."""
        empty = self.history_layout.count() <= 1
        self.history_empty.setVisible(empty)
        self.history_scroll.setVisible(not empty)
        self.history_search.setVisible(not empty)

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
            self, tr("Сохранить историю"), "speakmot-history.txt", tr("Текст (*.txt)")
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("\n\n".join(self.cfg.history))
        except OSError as exc:
            self.history_search.setPlaceholderText(tr("Не удалось сохранить: ") + str(exc))

    def _clear_history(self) -> None:
        self.cfg.history.clear()
        self.cfg.save()
        while self.history_layout.count() > 1:
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.history_search.clear()
        self._update_history_visibility()

    # --- настройки ---

    def _save_settings(self) -> None:
        cfg = self.cfg
        cfg.hotkey = self.hotkey_edit.combo() or "ctrl+alt+space"
        cfg.hotkey_mode = self.mode_combo.currentData()
        cfg.language = self.lang_combo.currentData()
        cfg.input_device = self.device_combo.currentData()
        cfg.auto_paste = self.paste_switch.isChecked()
        cfg.paste_method = self.method_combo.currentData()
        cfg.sound_feedback = self.sound_switch.isChecked()
        cfg.silence_stop = self.silence_combo.currentData()
        cfg.replacements = parse_replacements(self.replacements_edit.toPlainText())

        cfg.voice_commands = self.commands_switch.isChecked()
        cfg.translate_to_english = self.translate_switch.isChecked()
        cfg.language_hotkey = self.language_hotkey_edit.combo()
        cfg.repeat_hotkey = self.repeat_hotkey_edit.combo()
        cfg.streaming = self.streaming_switch.isChecked()
        cfg.preview_before_paste = self.preview_switch.isChecked()
        cfg.theme = self.theme_combo.currentData()
        cfg.accent = self.accent_combo.currentData()

        cfg.autostart = self.autostart_switch.isChecked()
        try:
            autostart.set_enabled(cfg.autostart)
        except OSError as exc:
            self.status_label.setText(tr("Не удалось изменить автозапуск: ") + str(exc))

        cfg.save()

        self.hotkey_badge.setText(hotkeys.pretty(cfg.hotkey))
        self.controller.reload(model_changed=False)

        self.save_button.setText(tr("Сохранено ✓"))
        QTimer.singleShot(1500, lambda: self.save_button.setText(tr("Сохранить")))

    # --- изменение размера безрамочного окна ---

    def _edges_at(self, position):
        """Какие края окна под курсором. Ничего — None.

        Пустое значение флагов Qt приходится обходить: его конструктор ведёт
        себя по-разному в зависимости от того, откуда импортирован Qt.
        """
        margin = 6
        found = []
        if position.x() <= margin:
            found.append(Qt.LeftEdge)
        if position.x() >= self.width() - margin:
            found.append(Qt.RightEdge)
        if position.y() <= margin:
            found.append(Qt.TopEdge)
        if position.y() >= self.height() - margin:
            found.append(Qt.BottomEdge)

        if not found:
            return None
        edges = found[0]
        for edge in found[1:]:
            edges |= edge
        return edges

    def _cursor_for(self, edges):
        if edges is None:
            return Qt.ArrowCursor
        if edges in (Qt.LeftEdge | Qt.TopEdge, Qt.RightEdge | Qt.BottomEdge):
            return Qt.SizeFDiagCursor
        if edges in (Qt.RightEdge | Qt.TopEdge, Qt.LeftEdge | Qt.BottomEdge):
            return Qt.SizeBDiagCursor
        if edges & (Qt.LeftEdge | Qt.RightEdge):
            return Qt.SizeHorCursor
        if edges & (Qt.TopEdge | Qt.BottomEdge):
            return Qt.SizeVerCursor
        return Qt.ArrowCursor

    def mouseMoveEvent(self, event):
        self.setCursor(self._cursor_for(self._edges_at(event.position().toPoint())))
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        edges = self._edges_at(event.position().toPoint())
        handle = self.windowHandle()
        if event.button() == Qt.LeftButton and edges is not None and handle is not None:
            handle.startSystemResize(edges)
            return
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self.unsetCursor()
        super().leaveEvent(event)

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
