from speakmot.voice_commands import apply_commands


def test_replaces_period_and_capitalizes_next_sentence():
    assert apply_commands("привет точка как дела") == "Привет. Как дела"


def test_comma_sticks_to_the_previous_word():
    assert apply_commands("да запятая конечно") == "Да, конечно"


def test_longer_phrase_wins_over_shorter_one():
    assert apply_commands("правда восклицательный знак") == "Правда!"


def test_new_paragraph_becomes_a_blank_line():
    assert apply_commands("первое новый абзац второе") == "Первое\n\nВторое"


def test_new_line_capitalizes_too():
    assert apply_commands("шаг один новая строка шаг два") == "Шаг один\nШаг два"


def test_brackets_hug_their_content():
    assert apply_commands("тест открыть скобку раз закрыть скобку") == "Тест (раз)"


def test_words_containing_a_command_are_left_alone():
    assert apply_commands("точная запятая") == "Точная,"
    assert apply_commands("заточка") == "Заточка"


def test_several_commands_in_a_row():
    result = apply_commands("вопрос вопросительный знак ответ точка")
    assert result == "Вопрос? Ответ."


def test_empty_text():
    assert apply_commands("") == ""
