"""Parsers for Starfield Plugins.txt and ContentCatalog.txt files."""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from starfield_tool.models import Creation, GameInstallation


@dataclass
class PluginEntry:
    filename: str
    is_active: bool
    position: int


@dataclass
class CatalogEntry:
    content_id: str
    title: str
    version: str
    author: str
    timestamp: datetime | None = None
    files: list[str] = field(default_factory=list)


def _parse_version_field(raw: str) -> tuple[str, datetime | None]:
    """Split '<unix_timestamp>.<version>' into (version, datetime).

    Bethesda's ContentCatalog stores versions as e.g. '1764942763.1.1.2'
    where the leading number is a Unix epoch timestamp.
    """
    parts = raw.split(".", 1)
    if len(parts) == 2:
        try:
            ts = int(parts[0])
            if ts > 1_000_000_000:  # plausible Unix timestamp
                return parts[1], datetime.fromtimestamp(ts)
        except (ValueError, OSError):
            pass
    return raw, None


def parse_plugins_txt(path: Path) -> list[PluginEntry]:
    """Parse Plugins.txt and return entries in load order."""
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return []

    entries = []
    position = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        is_active = line.startswith("*")
        filename = line.lstrip("*")
        entries.append(PluginEntry(
            filename=filename,
            is_active=is_active,
            position=position,
        ))
        position += 1

    return entries


def parse_content_catalog(path: Path) -> list[CatalogEntry]:
    """Parse ContentCatalog.txt and return catalog entries."""
    try:
        text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return []

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []

    entries = []
    for content_id, info in data.items():
        if not isinstance(info, dict):
            continue
        # Skip the metadata entry (has "Description" but no "Files")
        if "Files" not in info:
            continue
        version, timestamp = _parse_version_field(info.get("Version", ""))
        entries.append(CatalogEntry(
            content_id=content_id,
            title=info.get("Title", ""),
            version=version,
            author=info.get("Author", ""),
            timestamp=timestamp,
            files=info.get("Files", []),
        ))

    return entries


def build_creation_list(game_install: GameInstallation) -> list[Creation]:
    """Build the merged Creation list from ContentCatalog + Plugins.txt.

    Returns only Bethesda store Creations (items in ContentCatalog),
    sorted by their load order position in Plugins.txt.
    """
    catalog_entries = parse_content_catalog(game_install.content_catalog)
    plugin_entries = parse_plugins_txt(game_install.plugins_txt)

    # Index plugins by filename for quick lookup
    plugin_index: dict[str, PluginEntry] = {
        pe.filename: pe for pe in plugin_entries
    }

    creations = []
    for ce in catalog_entries:
        # Find the primary plugin file for this creation
        plugin_files_esm = [f for f in ce.files if f.endswith((".esm", ".esp", ".esl"))]

        # Determine load position from the first matching plugin in Plugins.txt
        load_position = None
        is_active = False
        for pf in plugin_files_esm:
            if pf in plugin_index:
                load_position = plugin_index[pf].position
                is_active = plugin_index[pf].is_active
                break

        # Check if plugin files exist in Data dir
        file_missing = False
        for pf in plugin_files_esm:
            if not (game_install.data_dir / pf).exists():
                file_missing = True
                break

        creations.append(Creation(
            content_id=ce.content_id,
            display_name=ce.title,
            author=ce.author,
            installed_version=ce.version,
            plugin_files=ce.files,
            timestamp=ce.timestamp,
            load_position=load_position,
            is_active=is_active,
            file_missing=file_missing,
        ))

    # Sort by load position (None last), then re-number sequentially
    creations.sort(key=lambda c: (c.load_position is None, c.load_position or 0))
    for i, c in enumerate(creations):
        if c.load_position is not None:
            c.load_position = i
    return creations
