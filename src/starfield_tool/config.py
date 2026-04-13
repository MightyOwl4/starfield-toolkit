import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


def _config_path() -> Path:
    app_data = os.environ.get("APPDATA", "")
    return Path(app_data) / "StarfieldToolkit" / "config.json"


@dataclass
class AppSettings:
    game_path: str | None = None
    window_geometry: str | None = None
    beta_acknowledged: bool = False
    rulebook_registry: list = None
    grid_font_size: int = 11  # Treeview body font size in pt

    def __post_init__(self):
        if self.rulebook_registry is None:
            self.rulebook_registry = []


def load_config(path: Path | None = None) -> AppSettings:
    p = path or _config_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return AppSettings(
            game_path=data.get("game_path"),
            window_geometry=data.get("window_geometry"),
            beta_acknowledged=data.get("beta_acknowledged", False),
            rulebook_registry=data.get("rulebook_registry", []),
            grid_font_size=data.get("grid_font_size", 11),
        )
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return AppSettings()


def save_config(settings: AppSettings, path: Path | None = None) -> None:
    p = path or _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
