from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QPushButton

from .. import hotkeys

MODIFIER_KEYS = {Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta, Qt.Key_AltGr}


class HotkeyEdit(QPushButton):
    """Поле, которое запоминает нажатую комбинацию.

    Раньше комбинацию слушала библиотека глобального перехвата в фоновом
    потоке — она конфликтовала с уже назначенным хоткеем и молча ничего не
    возвращала. Здесь всё происходит внутри окна: нажали кнопку, нажали
    сочетание, оно записано.
    """

    changed = Signal(str)

    def __init__(self, combo: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("hotkeyEdit")
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self._combo = combo
        self._render()
        self.toggled.connect(self._on_toggled)

    def combo(self) -> str:
        return self._combo

    def set_combo(self, combo: str) -> None:
        self._combo = combo
        self._render()

    def _render(self) -> None:
        if self.isChecked():
            self.setText("Нажмите сочетание…")
        else:
            self.setText(hotkeys.pretty(self._combo))

    def _on_toggled(self, checked: bool) -> None:
        self._render()
        if checked:
            self.setFocus(Qt.ShortcutFocusReason)
            self.grabKeyboard()
        else:
            self.releaseKeyboard()

    def keyPressEvent(self, event):
        if not self.isChecked():
            super().keyPressEvent(event)
            return

        key = event.key()
        if key == Qt.Key_Escape:
            self.setChecked(False)
            return
        if key in MODIFIER_KEYS:
            return

        modifiers = []
        state = event.modifiers()
        if state & Qt.ControlModifier:
            modifiers.append("ctrl")
        if state & Qt.AltModifier:
            modifiers.append("alt")
        if state & Qt.ShiftModifier:
            modifiers.append("shift")
        if state & Qt.MetaModifier:
            modifiers.append("windows")

        combo = hotkeys.build(modifiers, QKeySequence(key).toString())
        if not combo:
            self.setText("Нужен модификатор и клавиша")
            return

        self._combo = combo
        self.setChecked(False)
        self.changed.emit(combo)

    def focusOutEvent(self, event):
        if self.isChecked():
            self.setChecked(False)
        super().focusOutEvent(event)
