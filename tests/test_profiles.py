from speakmot.config import Config
from speakmot.profiles import INHERIT, Profile, match_profile, resolve


def test_matches_by_process_name():
    profiles = [Profile(match="code.exe")]
    assert match_profile(profiles, "Code.exe", "main.py") is not None


def test_matches_by_window_title():
    profiles = [Profile(match="telegram")]
    assert match_profile(profiles, "tg.exe", "Telegram — Иван") is not None


def test_no_match_returns_none():
    assert match_profile([Profile(match="code.exe")], "notepad.exe", "Заметки") is None


def test_empty_pattern_never_matches():
    assert match_profile([Profile(match="  ")], "notepad.exe", "Заметки") is None


def test_first_matching_profile_wins():
    profiles = [Profile(match="code", language="en"), Profile(match="code.exe", language="ru")]
    assert match_profile(profiles, "code.exe", "").language == "en"


def test_resolve_without_profiles_keeps_general_settings():
    cfg = Config(language="ru", voice_commands=True, paste_method="clipboard")
    result = resolve(cfg, [], "notepad.exe", "")
    assert (result.language, result.voice_commands, result.paste_method) == (
        "ru",
        True,
        "clipboard",
    )
    assert result.profile_name == ""


def test_profile_overrides_only_what_it_sets():
    cfg = Config(language="ru", voice_commands=True, paste_method="clipboard")
    profiles = [Profile(match="code.exe", language="en", voice_commands="off")]
    result = resolve(cfg, profiles, "code.exe", "main.py")
    assert result.language == "en"
    assert result.voice_commands is False
    assert result.paste_method == "clipboard"
    assert result.profile_name == "code.exe"


def test_inherit_values_change_nothing():
    cfg = Config(language="ru", voice_commands=False, paste_method="typing")
    profiles = [Profile(match="code.exe", language=INHERIT, voice_commands=INHERIT)]
    result = resolve(cfg, profiles, "code.exe", "")
    assert result.language == "ru"
    assert result.voice_commands is False
    assert result.paste_method == "typing"


def test_profile_survives_a_dict_round_trip():
    profile = Profile(match="code.exe", language="en", paste_method="typing")
    assert Profile.from_dict(profile.to_dict()) == profile
