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


def test_caption_follows_the_open_page(window):
    """Подпись в заголовке окна должна совпадать с открытым разделом."""
    for index in range(window.pages.count()):
        window.pages.setCurrentIndex(index)
        expected = window.nav_group.button(index).text()
        assert window.title_bar.caption.text() == expected


def test_window_edges_report_resize_cursors(window):
    from PySide6.QtCore import QPoint, Qt

    window.resize(900, 620)
    assert window._edges_at(QPoint(2, 300)) == Qt.LeftEdge
    assert window._edges_at(QPoint(898, 300)) == Qt.RightEdge
    assert window._edges_at(QPoint(450, 618)) == Qt.BottomEdge
    assert window._edges_at(QPoint(450, 300)) is None
    assert window._cursor_for(None) == Qt.ArrowCursor
    assert window._edges_at(QPoint(2, 2)) == (Qt.LeftEdge | Qt.TopEdge)


def test_empty_history_explains_itself(window):
    """Пустой список без подсказки читается как поломка."""
    window.cfg.history.clear()
    window._clear_history()
    # страница скрыта стеком, пока не открыта, поэтому смотрим на явное скрытие
    assert not window.history_empty.isHidden()
    assert window.history_search.isHidden()

    window.show_result("проверка")
    assert window.history_empty.isHidden()
    assert not window.history_search.isHidden()


def test_statistics_tiles_show_numbers(window):
    window.cfg.stats = {"words": 120, "count": 7, "seconds": 300}
    window._refresh_stats()
    assert window.tile_words.value.text() == "120"
    assert window.tile_count.value.text() == "7"
    assert window.tile_minutes.value.text() == "5"


def test_old_accent_from_config_falls_back_to_palette():
    """После смены палитры сохранённый синий цвет больше не существует."""
    from speakmot.ui import theme

    assert theme.normalize_accent("#5b8cff") == theme.DEFAULT_ACCENT
    assert theme.normalize_accent("#d79921") == "#d79921"


def test_every_palette_colour_is_valid(window):
    """Опечатка в цвете рушит отрисовку уже во время работы."""
    from PySide6.QtGui import QColor

    from speakmot.ui import theme

    for palette in theme.PALETTES.values():
        for key, value in palette.items():
            if value.startswith("#"):
                assert QColor(value).isValid(), f"{key}={value}"
    for value in theme.ACCENTS.values():
        assert QColor(value).isValid(), value


def test_status_bar_follows_state(window):
    """Нижняя строка повторяет состояние движка и показывает часы."""
    from speakmot import engine as engine_states

    window.apply_state(engine_states.RECORDING, "")
    assert window.status_bar_text.text() == "слушаю"
    assert len(window.clock.text()) == 8
    assert len(window.title_bar.dots) == 3


def test_icon_file_is_shipped_and_multisize():
    """Пустой значок в панели задач — это отсутствующий или однослойный .ico."""
    from PySide6.QtGui import QIcon

    from speakmot import branding

    path = branding.resource_path(branding.ICON_FILE)
    assert path.exists(), path
    icon = QIcon(str(path))
    sizes = {size.width() for size in icon.availableSizes()}
    assert {16, 32, 48, 256} <= sizes, sizes


def test_app_icon_never_empty(window):
    from speakmot import branding

    icon = branding.app_icon()
    assert not icon.isNull()
    assert not branding.mark_pixmap(16).isNull()
