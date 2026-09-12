"""Профили под приложение: свои настройки для конкретных программ."""

from dataclasses import asdict, dataclass, field

INHERIT = "inherit"


@dataclass
class Profile:
    match: str = ""  # часть имени процесса или заголовка окна
    language: str = INHERIT  # "ru" | "en" | "auto" | INHERIT
    voice_commands: str = INHERIT  # "on" | "off" | INHERIT
    paste_method: str = INHERIT  # "clipboard" | "typing" | INHERIT

    @classmethod
    def from_dict(cls, data: dict) -> "Profile":
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Resolved:
    """Итоговые настройки записи после наложения профиля."""

    language: str
    voice_commands: bool
    paste_method: str
    profile_name: str = field(default="")


def match_profile(profiles: list[Profile], process: str, title: str) -> Profile | None:
    """Ищет первый профиль, чей шаблон встречается в имени процесса или заголовке."""
    haystack = f"{process} {title}".lower()
    for profile in profiles:
        needle = profile.match.strip().lower()
        if needle and needle in haystack:
            return profile
    return None


def resolve(cfg, profiles: list[Profile], process: str, title: str) -> Resolved:
    """Накладывает подходящий профиль поверх общих настроек."""
    base = Resolved(
        language=cfg.language,
        voice_commands=cfg.voice_commands,
        paste_method=cfg.paste_method,
    )
    profile = match_profile(profiles, process, title)
    if profile is None:
        return base

    base.profile_name = profile.match
    if profile.language != INHERIT:
        base.language = profile.language
    if profile.voice_commands != INHERIT:
        base.voice_commands = profile.voice_commands == "on"
    if profile.paste_method != INHERIT:
        base.paste_method = profile.paste_method
    return base
