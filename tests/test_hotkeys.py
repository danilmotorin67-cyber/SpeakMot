from speakmot import hotkeys


def test_builds_combination_in_a_stable_order():
    assert hotkeys.build(["alt", "ctrl"], "Space") == "ctrl+alt+space"
    assert hotkeys.build(["shift", "ctrl"], "F5") == "ctrl+shift+f5"


def test_modifiers_alone_are_rejected():
    assert hotkeys.build(["ctrl"], "") == ""
    assert hotkeys.build(["ctrl"], "Ctrl") == ""


def test_single_letter_without_modifier_is_rejected():
    assert hotkeys.build([], "A") == ""


def test_function_key_without_modifier_is_allowed():
    assert hotkeys.build([], "F9") == "f9"


def test_dangerous_combinations_are_rejected():
    assert hotkeys.build(["alt"], "F4") == ""


def test_qt_names_are_translated():
    assert hotkeys.build(["ctrl"], "Return") == "ctrl+enter"
    assert hotkeys.build(["ctrl"], "Num Space") == "ctrl+space"


def test_pretty_reads_naturally():
    assert hotkeys.pretty("ctrl+alt+space") == "Ctrl + Alt + Space"
    assert hotkeys.pretty("") == "не назначена"
