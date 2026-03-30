"""Snapshot export and import for load orders."""
import json
from datetime import datetime, timezone
from pathlib import Path

from load_order_sorter.models import Snapshot, SnapshotEntry


def save_snapshot(
    name: str,
    entries: list[SnapshotEntry],
    path: Path,
    tool_version: str = "",
) -> None:
    """Write a load order snapshot to a JSON file."""
    snapshot = {
        "name": name,
        "created": datetime.now(tz=timezone.utc).isoformat(),
        "tool": {
            "name": "Starfield Toolkit",
            "version": tool_version,
            "url": "https://github.com/MightyOwl4/starfield-toolkit",
        },
        "creations": [
            {
                "id": e.content_id,
                "name": e.display_name,
                "files": e.files,
            }
            for e in entries
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")


def load_snapshot(path: Path) -> Snapshot:
    """Read a load order snapshot from a JSON file.

    Raises ValueError if the file format is invalid.
    Supports both new format (creations array) and legacy (plugins array).
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        raise ValueError(f"Invalid snapshot file: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("Snapshot file must be a JSON object")

    entries: list[SnapshotEntry] = []

    if "creations" in data:
        # New format
        creations = data["creations"]
        if not isinstance(creations, list):
            raise ValueError("Snapshot 'creations' must be a list")
        for item in creations:
            if not isinstance(item, dict) or "id" not in item:
                raise ValueError("Each creation must have an 'id' field")
            entries.append(SnapshotEntry(
                content_id=item["id"],
                display_name=item.get("name", ""),
                files=item.get("files", []),
            ))
    elif "plugins" in data:
        # Legacy format — bare filename list
        plugins = data["plugins"]
        if not isinstance(plugins, list):
            raise ValueError("Snapshot 'plugins' must be a list")
        for p in plugins:
            if isinstance(p, str):
                entries.append(SnapshotEntry(
                    content_id=p, display_name=p, files=[p],
                ))
    else:
        raise ValueError("Snapshot missing 'creations' or 'plugins' field")

    # Support both new "tool" object and legacy "tool_version" string
    tool = data.get("tool", {})
    if isinstance(tool, dict):
        tool_version = tool.get("version", "")
    else:
        tool_version = data.get("tool_version", "")

    return Snapshot(
        name=data.get("name", ""),
        created=data.get("created", ""),
        tool_version=tool_version,
        entries=entries,
    )
