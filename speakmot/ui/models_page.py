import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .. import models
from ..i18n import tr
from .widgets import Card


def restyle(widget: QWidget, name: str) -> None:
    """Меняет роль виджета и заставляет Qt перечитать стиль под новое имя."""
    widget.setObjectName(name)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def human_size(size_bytes: int) -> str:
    gigabytes = size_bytes / 1_000_000_000
    if gigabytes >= 1:
        return f"{gigabytes:.1f}{tr(' ГБ')}"
    return f"{size_bytes / 1_000_000:.0f}{tr(' МБ')}"


class ModelCard(Card):
    """Карточка одной модели: статус, установка с прогрессом, удаление."""

    progress_changed = Signal(int)
    finished = Signal(str)  # пустая строка — успех, иначе текст ошибки

    def __init__(self, size: str, page: "ModelsPage"):
        super().__init__()
        self.size = size
        self.page = page
        self._busy = False

        header = QHBoxLayout()
        header.setSpacing(10)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        name = QLabel(size)
        name.setObjectName("settingLabel")
        description = QLabel(
            f"{tr(models.DESCRIPTIONS[size])} · {human_size(models.FALLBACK_BYTES[size])}"
        )
        description.setObjectName("settingDesc")
        description.setWordWrap(True)
        titles.addWidget(name)
        titles.addWidget(description)
        header.addLayout(titles, 1)

        self.status = QLabel()
        self.status.setObjectName("badge")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setFixedWidth(128)
        header.addWidget(self.status)

        self.use_button = QPushButton(tr("Выбрать"))
        self.use_button.setObjectName("ghost")
        self.use_button.setCursor(Qt.PointingHandCursor)
        self.use_button.clicked.connect(self._use)
        self.use_button.setFixedWidth(96)
        header.addWidget(self.use_button)

        self.action_button = QPushButton()
        self.action_button.setObjectName("primary")
        self.action_button.setCursor(Qt.PointingHandCursor)
        self.action_button.clicked.connect(self._install_or_delete)
        self.action_button.setFixedWidth(124)
        header.addWidget(self.action_button)

        self.body().addLayout(header)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.hide()
        self.body().addWidget(self.progress)

        self.progress_changed.connect(self._on_progress)
        self.finished.connect(self._on_finished)
        self.refresh()

    # --- состояние ---

    def refresh(self) -> None:
        installed = models.is_installed(self.size)
        active = self.page.cfg.model_size == self.size

        if active and installed:
            self.status.setText(tr("используется"))
        elif installed:
            self.status.setText(tr("установлена"))
        else:
            self.status.setText(tr("не установлена"))

        self.use_button.setVisible(installed and not active)
        self.action_button.setText(tr("Удалить") if installed else tr("Установить"))
        restyle(self.action_button, "ghost" if installed else "primary")
        self.action_button.setEnabled(not self._busy and not (installed and active))
        self.setEnabled(True)

    # --- действия ---

    def _use(self) -> None:
        self.page.select_model(self.size)

    def _install_or_delete(self) -> None:
        if models.is_installed(self.size):
            models.delete(self.size)
            self.page.refresh_all()
            return
        self._start_download()

    def _start_download(self) -> None:
        self._busy = True
        self.action_button.setEnabled(False)
        self.action_button.setText(tr("Загрузка…"))
        self.progress.setValue(0)
        self.progress.show()

        def worker():
            try:
                models.download(self.size, self.progress_changed.emit)
            except Exception as exc:
                self.finished.emit(str(exc))
                return
            self.finished.emit("")

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, percent: int) -> None:
        self.progress.setValue(percent)

    def _on_finished(self, error: str) -> None:
        self._busy = False
        self.progress.hide()
        if error:
            self.page.report(tr("Не удалось скачать ") + f"{self.size}: {error}")
        else:
            self.page.report(tr("Модель ") + self.size + tr(" установлена"))
            if not models.is_installed(self.page.cfg.model_size):
                self.page.select_model(self.size)
        self.page.refresh_all()


class ModelsPage(QWidget):
    """Список моделей Whisper с установкой по кнопке."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.cfg = controller.cfg

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 26)
        layout.setSpacing(14)

        title = QLabel(tr("Модели"))
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        self.hint = QLabel(
            tr("Модели скачиваются один раз и работают офлайн. "
            "Чем крупнее модель, тем точнее распознавание и тем медленнее оно идёт.")
        )
        self.hint.setObjectName("pageHint")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget()
        cards_layout = QVBoxLayout(container)
        cards_layout.setContentsMargins(0, 0, 8, 0)
        cards_layout.setSpacing(12)

        self.cards = [ModelCard(size, self) for size in models.MODEL_REPOS]
        for card in self.cards:
            cards_layout.addWidget(card)
        cards_layout.addStretch(1)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

    def refresh_all(self) -> None:
        for card in self.cards:
            card.refresh()

    def report(self, message: str) -> None:
        self.hint.setText(message)

    def select_model(self, size: str) -> None:
        self.cfg.model_size = size
        self.cfg.save()
        self.controller.model_selected(size)
        self.refresh_all()
