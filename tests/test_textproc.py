from speakmot.textproc import apply_replacements, format_replacements, parse_replacements


def test_replaces_whole_words_ignoring_case():
    assert apply_replacements("Пайтон и пайтон", {"пайтон": "Python"}) == "Python и Python"


def test_keeps_words_that_only_contain_the_source():
    assert apply_replacements("пайтоновский код", {"пайтон": "Python"}) == "пайтоновский код"


def test_handles_multiword_phrases():
    assert apply_replacements("открой гит хаб", {"гит хаб": "GitHub"}) == "открой GitHub"


def test_empty_inputs_are_returned_unchanged():
    assert apply_replacements("", {"а": "б"}) == ""
    assert apply_replacements("текст", {}) == "текст"


def test_special_characters_are_not_treated_as_regex():
    assert apply_replacements("цена 1+1", {"1+1": "два"}) == "цена два"


def test_parses_pairs_and_skips_junk():
    raw = "пайтон = Python\n\n# комментарий\nбез разделителя\n гит хаб = GitHub "
    assert parse_replacements(raw) == {"пайтон": "Python", "гит хаб": "GitHub"}


def test_parse_and_format_round_trip():
    replacements = {"пайтон": "Python", "гит хаб": "GitHub"}
    assert parse_replacements(format_replacements(replacements)) == replacements
