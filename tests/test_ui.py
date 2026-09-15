"""Проверки интерфейса: окно должно собираться и рисоваться без ошибок.

Две поломки уехали пользователю именно потому, что интерфейс никто не
собирал в тестах: падение на QFont.setWeight и пустые страницы из-за
графических эффектов.
"""

import os
import sys
import types

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")


def _stub(name: str, **attrs) -> None:
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module


class _Stream:
    def __init__(self, **kwargs):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def close(self):
        pass


class _Model:
    def __init__(self, *args, **kwargs):
        pass

    def transcribe(self, *args, **kwargs):
        return ([], None)


@pytest.fixture(scope="module")
def window(tmp_path_factory):
    _stub(
        "keyboard",
        add_hotkey=lambda *a, **k: object(),
        hook=lambda *a, **k: object(),
        remove_hotkey=lambda handle: None,
        unhook=lambda handle: None,
        send=lambda *a: None,
        write=lambda *a, **k: None,
    )
    _stub("pyperclip", copy=lambda text: None, paste=lambda: "")
    _stub(
        "sounddevice",
        query_devices=lambda: [{"name": "Микрофон", "max_input_channels": 2}],
        InputStream=_Stream,
    )
    _stub("faster_whisper", WhisperModel=_Model)

    from speakmot import config

    directory = tmp_path_factory.mktemp("speakmot")
    config.CONFIG_DIR = directory
    config.CONFIG_PATH = directory / "config.json"

    from speakmot.ui.app import SpeakMotApp

    # QApplication создаёт само приложение — второй экземпляр Qt не допускает
    app = SpeakMotApp()
    yield app.window
    app.window.close()
    app.qt.processEvents()


def test_every_navigation_item_has_a_label(window):
    labels = [button.text() for button in window.nav_group.buttons()]
    assert labels == ["Запись", "История", "Модели", "Профили", "Настройки"]


def test_navigation_matches_the_number_of_pages(window):
    assert len(window.nav_group.buttons()) == window.pages.count()


def test_every_page_renders_without_errors(window):
    """Отрисовка каждой страницы — так ловятся падения внутри paintEvent."""
    for index in range(window.pages.count()):
        window.pages.setCurrentIndex(index)
        page = window.pages.widget(index)
        assert not page.grab().isNull()


def test_models_page_lists_every_model(window):
    from speakmot import models

    cards = window.models_page.cards
    assert [card.size for card in cards] == list(models.MODEL_REPOS)
    for card in cards:
        assert card.sizeHint().height() > 40


def test_settings_page_is_not_empty(window):
    from speakmot.ui.widgets import Card

    page = window.pages.widget(4)
    cards = page.findChildren(Card)
    assert len(cards) >= 5
    assert window.hotkey_edit.combo() == window.cfg.hotkey


def test_no_widget_uses_graphics_effects(window):
    """Эффекты Qt оставляли страницы пустыми на Windows — держим их вне игры."""
    from PySide6.QtWidgets import QWidget

    with_effects = [
        widget
        for widget in window.findChildren(QWidget)
        if widget.graphicsEffect() is not None
    ]
    assert with_effects == []


def test_active_navigation_item_updates_its_icon(window):
    first, second = window.nav_group.buttons()[0], window.nav_group.buttons()[1]
    first.setChecked(True)
    active = first.icon().pixmap(18, 18).toImage()
    second.setChecked(True)
    dimmed = first.icon().pixmap(18, 18).toImage()
    assert active != dimmed


def test_state_changes_keep_the_window_paintable(window):
    from speakmot import engine as states

    for state in (states.IDLE, states.RECORDING, states.TRANSCRIBING, states.ERROR):
        window.apply_state(state, "проверка")
        assert not window.grab().isNull()


def test_every_icon_draws(window):
    """Иконки рисуются напрямую вызовами Qt, где типы аргументов строгие."""
    from speakmot.ui import icons

    for name in icons._ICONS:
        pixmap = icons.icon(name, 18, "#8e97ab").pixmap(18, 18)
        assert not pixmap.isNull()
        assert pixmap.toImage().constBits() is not None
