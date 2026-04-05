"""TES4 binary header parser — extracts master dependencies from plugin files."""
import re
import struct
from pathlib import Path

# Base game masters that are always loaded by the engine before creation plugins.
_BASE_GAME_MASTERS = frozenset({
    "starfield.esm",
    "blueprintships-starfield.esm",
    "starfield - localization.esm",
    "constellation.esm",
    "oldmars.esm",
    "sfbgs003.esm",
    "sfbgs004.esm",
    "sfbgs005.esm",
    "sfbgs006.esm",
    "sfbgs007.esm",
    "sfbgs008.esm",
})
_SFBGS_PATTERN = re.compile(r"^sfbgs\d+\.esm$", re.IGNORECASE)


def parse_masters(filepath: Path) -> list[str]:
    """Read the TES4 record from a plugin file and extract MAST subrecords.

    Returns a list of master filenames. Returns empty list on any error
    (file not found, corrupted, non-TES4 record, etc.).
    """
    try:
        with open(filepath, "rb") as f:
            # Record header: 24 bytes
            header = f.read(24)
            if len(header) < 24:
                return []

            record_type = header[0:4]
            if record_type != b"TES4":
                return []

            data_size = struct.unpack_from("<I", header, 4)[0]

            # Read the subrecord data
            data = f.read(data_size)
            if len(data) < data_size:
                return []

        # Parse subrecords for MAST entries
        masters = []
        offset = 0
        while offset + 6 <= len(data):
            sub_type = data[offset:offset + 4]
            sub_size = struct.unpack_from("<H", data, offset + 4)[0]
            offset += 6

            if offset + sub_size > len(data):
                break

            if sub_type == b"MAST":
                # Null-terminated string
                raw = data[offset:offset + sub_size]
                name = raw.rstrip(b"\x00").decode("utf-8", errors="replace")
                if name:
                    masters.append(name)

            offset += sub_size

        return masters
    except (OSError, struct.error, UnicodeDecodeError):
        return []


def filter_base_game_masters(masters: list[str]) -> list[str]:
    """Remove known base game and DLC masters, returning only creation plugins."""
    result = []
    for name in masters:
        lower = name.lower()
        if lower in _BASE_GAME_MASTERS:
            continue
        if _SFBGS_PATTERN.match(name):
            continue
        result.append(name)
    return result


def build_master_map(
    data_dir: Path,
    plugin_files: dict[str, str],
) -> dict[str, list[str]]:
    """Build a map of plugin filename → list of creation-only master filenames.

    Args:
        data_dir: Path to the game's Data directory containing .esm files.
        plugin_files: Dict mapping plugin filename (e.g., "MyMod.esm") to
            content_id. Only masters present in this dict are retained.

    Returns:
        Dict mapping each plugin filename to its filtered master list.
        Plugins with no creation-only masters are omitted.
    """
    # Build case-insensitive lookup for installed plugins
    installed_lower = {name.lower(): name for name in plugin_files}

    master_map: dict[str, list[str]] = {}
    for plugin_name in plugin_files:
        filepath = data_dir / plugin_name
        if not filepath.exists():
            continue

        raw_masters = parse_masters(filepath)
        filtered = filter_base_game_masters(raw_masters)

        # Only keep masters that are installed creation plugins
        creation_masters = []
        for master in filtered:
            canonical = installed_lower.get(master.lower())
            if canonical:
                creation_masters.append(canonical)

        if creation_masters:
            master_map[plugin_name] = creation_masters

    return master_map
