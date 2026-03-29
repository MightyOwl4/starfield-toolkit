from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class GameInstallation:
    game_root: Path
    source: str = "manual"  # "auto-steam", "manual", "persisted"
    _plugins_txt_override: Path | None = None

    @property
    def data_dir(self) -> Path:
        return self.game_root / "Data"

    @property
    def content_catalog(self) -> Path:
        if self._plugins_txt_override:
            # Test mode — content catalog next to plugins.txt override
            return self._plugins_txt_override.parent / "ContentCatalog.txt"
        import os
        local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
        return local_app_data / "Starfield" / "ContentCatalog.txt"

    @property
    def plugins_txt(self) -> Path:
        if self._plugins_txt_override:
            return self._plugins_txt_override
        import os
        local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
        return local_app_data / "Starfield" / "Plugins.txt"

    @property
    def is_valid(self) -> bool:
        if not self.game_root.is_dir():
            return False
        if not self.data_dir.is_dir():
            return False
        # Data dir must contain at least one .esm file
        return any(self.data_dir.glob("*.esm"))


@dataclass
class Creation:
    content_id: str
    display_name: str
    author: str = ""
    installed_version: str = ""
    plugin_files: list[str] = field(default_factory=list)
    timestamp: datetime | None = None
    load_position: int | None = None
    is_active: bool = False
    file_missing: bool = False
    available_version: str | None = None
    has_update: bool = False
    achievement_friendly: bool | None = None  # None = not checked yet
