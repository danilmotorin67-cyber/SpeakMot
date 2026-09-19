from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..profiles import INHERIT, Profile
from .widgets import Card, EmptyState, QuietComboBox

LANGUAGES = {
    "как в настройках": INHERIT,
    "Русский": "ru",
    "English": "en",
    "Автоопределение": "auto",
}
COMMANDS = {"как в настройках": INHERIT, "Включены": "on", "Выключены": "off"}
METHODS = {
    "как в настройках": INHERIT,
    "Вставкой (Ctrl+V)": "clipboard",
    "Вводом символов": "typing",
}


class ProfileCard(Card):
    """Правила для одной программы."""

    def __init__(self, profile: Profile, page: "ProfilesPage"):
        super().__init__()
        self.page = page
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.match_edit = QLineEdit(profile.match)
        self.match_edit.setPlaceholderText(tr("code.exe или часть заголовка окна"))
        top.addWidget(self.match_edit, 1)

        remove = QPushButton(tr("Удалить"))
        remove.setObjectName("danger")
        remove.setCursor(Qt.PointingHandCursor)
        remove.clicked.connect(lambda: page.remove_card(self))
        remove.setFixedWidth(110)
        top.addWidget(remove)
        self.body().addLayout(top)

        options = QHBoxLayout()
        options.setSpacing(10)
        self.language_combo = self._combo(LANGUAGES, profile.language, tr("Язык"), options)
        self.commands_combo = self._combo(
            COMMANDS, profile.voice_commands, tr("Команды"), options
        )
        self.method_combo = self._combo(METHODS, profile.paste_method, tr("Вставка"), options)
        self.body().addLayout(options)

    def _combo(self, mapping, value, label, parent_layout) -> QComboBox:
        column = QVBoxLayout()
        column.setSpacing(3)
        caption = QLabel(label)
        caption.setObjectName("settingDesc")
        combo = QuietComboBox()
        for text, data in mapping.items():
            combo.addItem(tr(text), data)
        combo.setCurrentIndex(max(0, combo.findData(value)))
        column.addWidget(caption)
        column.addWidget(combo)
        parent_layout.addLayout(column, 1)
        return combo

    def to_profile(self) -> Profile:
        return Profile(
            match=self.match_edit.text().strip(),
            language=self.language_combo.currentData(),
            voice_commands=self.commands_combo.currentData(),
            paste_method=self.method_combo.currentData(),
        )


class ProfilesPage(QWidget):
    """Правила под конкретные программы поверх общих настроек."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.cfg = controller.cfg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 26)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel(tr("Профили"))
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch(1)

        add = QPushButton(tr("Добавить"))
        add.setObjectName("ghost")
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(lambda: self.add_card(Profile()))
        header.addWidget(add)

        save = QPushButton(tr("Сохранить"))
        save.setObjectName("primary")
        save.setCursor(Qt.PointingHandCursor)
        save.clicked.connect(self.save)
        header.addWidget(save)
        layout.addLayout(header)

        self.hint = QLabel(
            tr("Профиль срабатывает, когда его строка встречается в имени программы "
            "или в заголовке активного окна. Первый подошедший профиль и применяется.")
        )
        self.hint.setObjectName("pageHint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        self.cards_layout = QVBoxLayout(container)
        self.cards_layout.setContentsMargins(0, 0, 8, 0)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch(1)
        scroll.setWidget(container)
        self.scroll = scroll
        layout.addWidget(scroll, 1)

        self.empty = EmptyState(
            "sliders",
            tr("Профилей пока нет"),
            tr("Добавьте профиль, чтобы у отдельной программы были свои настройки."),
        )
        layout.addWidget(self.empty, 1)

        self.cards: list[ProfileCard] = []
        for item in self.cfg.profiles:
            self.add_card(Profile.from_dict(item))
        self._update_empty()

    def add_card(self, profile: Profile) -> None:
        card = ProfileCard(profile, self)
        self.cards.append(card)
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        self._update_empty()

    def remove_card(self, card: ProfileCard) -> None:
        self.cards.remove(card)
        card.setParent(None)
        card.deleteLater()
        self._update_empty()

    def _update_empty(self) -> None:
        empty = not self.cards
        self.empty.setVisible(empty)
        self.scroll.setVisible(not empty)

    def save(self) -> None:
        profiles = [card.to_profile() for card in self.cards]
        self.cfg.profiles = [p.to_dict() for p in profiles if p.match]
        self.cfg.save()
        self.hint.setText(tr("Сохранено профилей: ") + str(len(self.cfg.profiles)))
