from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr


class PreviewWindow(QWidget):
    """Показывает распознанный текст до вставки: можно поправить или отклонить."""

    accepted = Signal(str)
    rejected = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        panel = QFrame()
        panel.setObjectName("previewRoot")
        outer.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        header = QLabel(tr("РАСПОЗНАНО"))
        header.setObjectName("previewTitle")
        layout.addWidget(header)

        self.editor = QTextEdit()
        self.editor.setObjectName("previewEdit")
        self.editor.setAcceptRichText(False)
        self.editor.setMinimumHeight(96)
        layout.addWidget(self.editor)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        hint = QLabel(tr("Enter — вставить · Esc — отменить"))
        hint.setObjectName("overlayHint")
        buttons.addWidget(hint)
        buttons.addStretch(1)

        cancel = QPushButton(tr("Отменить"))
        cancel.setObjectName("ghost")
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self._reject)
        buttons.addWidget(cancel)

        insert = QPushButton(tr("Вставить"))
        insert.setObjectName("primary")
        insert.setCursor(Qt.PointingHandCursor)
        insert.clicked.connect(self._accept)
        buttons.addWidget(insert)
        layout.addLayout(buttons)

        self.setFixedWidth(560)

        # Enter вставляет, Shift+Enter оставляет перенос строки внутри текста
        for sequence in (QKeySequence(Qt.Key_Return), QKeySequence(Qt.Key_Enter)):
            shortcut = QShortcut(sequence, self.editor)
            shortcut.setContext(Qt.WidgetShortcut)
            shortcut.activated.connect(self._accept)

    def show_text(self, text: str) -> None:
        self.editor.setPlainText(text)
        self.editor.moveCursor(QTextCursor.End)
        self.adjustSize()
        self._reposition()
        self.show()
        self.raise_()
        self.activateWindow()
        self.editor.setFocus()

    def _reposition(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(
            area.center().x() - self.width() // 2,
            area.bottom() - self.height() - 90,
        )

    def _accept(self) -> None:
        text = self.editor.toPlainText().strip()
        self.hide()
        if text:
            self.accepted.emit(text)

    def _reject(self) -> None:
        self.hide()
        self.rejected.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._reject()
            return
        super().keyPressEvent(event)
