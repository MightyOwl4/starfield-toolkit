"""Catalogue file I/O, hashing, and entry conversion for the creations catalogue."""
import hashlib
import html
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CATALOGUE_VERSION = 1


def _default_catalogue_path() -> Path:
    app_data = os.environ.get("APPDATA", "")
    return Path(app_data) / "StarfieldToolkit" / "creations_catalogue.json"


def load_catalogue(path: Path | None = None) -> dict:
    """Load catalogue from disk. Returns empty entries dict on any error."""
    p = path or _default_catalogue_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("version") != CATALOGUE_VERSION:
            return {}
        return data.get("entries", {})
    except (FileNotFoundError, json.JSONDecodeError, OSError, KeyError):
        return {}


def save_catalogue(entries: dict, path: Path | None = None) -> None:
    """Atomically save catalogue to disk (write to temp file, then rename)."""
    p = path or _default_catalogue_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": CATALOGUE_VERSION, "entries": entries}
    content = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(p.parent), suffix=".tmp", prefix="catalogue_"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(p))
    except BaseException:
        os.close(fd) if not os.get_inheritable(fd) else None
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def compute_content_hash(description: str, release_notes_text: str) -> str:
    """SHA-256 hex digest of description + release_notes_text (no separator)."""
    combined = (description or "") + (release_notes_text or "")
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def normalize_release_notes(release_notes: list) -> str:
    """Convert structured release_notes list to a flat text for hashing."""
    parts = []
    for platform_entry in release_notes or []:
        for note in platform_entry.get("release_notes", []):
            version = note.get("version_name", "")
            text = html.unescape(note.get("note", "") or "")
            parts.append(f"{version}{text}")
    return "".join(parts)


def _decode(value: str) -> str:
    """Decode HTML entities in a string (e.g. &#39; → ')."""
    return html.unescape(value) if value else ""


def api_response_to_entry(item: dict) -> dict:
    """Extract a catalogue entry from a single API response item."""
    description = _decode(item.get("description", "") or "")
    overview = _decode(item.get("overview", "") or "")
    release_notes = item.get("release_notes", []) or []
    required_mods = item.get("required_mods", []) or []

    # Price from catalog_info
    price = 0
    for catalog in item.get("catalog_info", []):
        for price_entry in catalog.get("prices", []):
            amount = price_entry.get("amount", 0)
            if amount > 0:
                price = amount
                break
        if price > 0:
            break

    release_notes_text = normalize_release_notes(release_notes)

    return {
        "title": _decode(item.get("title", "") or ""),
        "author": _decode(item.get("author_displayname", "") or ""),
        "categories": item.get("categories", []),
        "price": price,
        "description": description,
        "overview": overview,
        "release_notes": release_notes,
        "required_mods": required_mods,
        "achievement_friendly": item.get("achievement_friendly", False),
        "content_hash": compute_content_hash(description, release_notes_text),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "plugin_summary": None,
    }
