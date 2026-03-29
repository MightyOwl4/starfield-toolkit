"""Steam library detection for finding Starfield installations."""
import re
import sys
from pathlib import Path

from starfield_tool.models import GameInstallation

STARFIELD_APP_ID = "1716740"


def find_steam_install_path() -> Path | None:
    """Find Steam install path from Windows registry."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        for hive, subkey in [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam"),
        ]:
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    value, _ = winreg.QueryValueEx(key, "InstallPath")
                    path = Path(value)
                    if path.is_dir():
                        return path
            except OSError:
                continue
    except ImportError:
        pass
    return None


def parse_library_folders(vdf_path: Path) -> list[Path]:
    """Parse Steam's libraryfolders.vdf to extract library paths."""
    try:
        text = vdf_path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return []

    paths = []
    # Match "path" value entries in VDF format
    for match in re.finditer(r'"path"\s+"([^"]+)"', text):
        raw_path = match.group(1).replace("\\\\", "/").replace("\\", "/")
        paths.append(Path(raw_path))

    return paths


def find_starfield_in_libraries(
    library_paths: list[Path],
) -> GameInstallation | None:
    """Check each Steam library for a valid Starfield installation."""
    for lib_path in library_paths:
        game_root = lib_path / "steamapps" / "common" / "Starfield"
        install = GameInstallation(game_root=game_root, source="auto-steam")
        if install.is_valid:
            return install
    return None


def auto_detect_starfield() -> GameInstallation | None:
    """Full auto-detection: find Steam → parse libraries → find Starfield."""
    steam_path = find_steam_install_path()
    if not steam_path:
        return None

    vdf = steam_path / "steamapps" / "libraryfolders.vdf"
    library_paths = parse_library_folders(vdf)
    if not library_paths:
        return None

    return find_starfield_in_libraries(library_paths)
