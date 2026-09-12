import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

CONFIG_DIR = Path.home() / ".speakmot"
CONFIG_PATH = CONFIG_DIR / "config.json"
MODELS_DIR = CONFIG_DIR / "models"


@dataclass
class Config:
    hotkey: str = "ctrl+alt+space"
    hotkey_mode: str = "toggle"  # "toggle" | "hold"
    model_size: str = "small"
    language: str = "ru"  # "auto" для автоопределения
    device: str = "auto"  # "auto" | "cpu" | "cuda"
    compute_type: str = "auto"
    input_device: int | None = None
    sample_rate: int = 16000
    auto_paste: bool = True
    paste_method: str = "clipboard"  # "clipboard" | "typing"
    sound_feedback: bool = True
    autostart: bool = False
    theme: str = "dark"  # "dark" | "light"
    accent: str = "#5b8cff"
    voice_commands: bool = True
    preview_before_paste: bool = False
    profiles: list[dict] = field(default_factory=list)
    silence_stop: float = 0.0  # секунды тишины до автостопа, 0 — выключено
    replacements: dict[str, str] = field(default_factory=dict)
    history: list[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            cfg = cls()
            cfg.save()
            return cfg
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        known = {f: data[f] for f in cls.__dataclass_fields__ if f in data}
        return cls(**known)

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )
