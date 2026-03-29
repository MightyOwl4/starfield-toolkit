"""Disk cache for Bethesda Creations API responses."""
import json
import time
from pathlib import Path

from bethesda_creations.models import CreationInfo

CACHE_VERSION = 1

# Fields that never change once a Creation is published.
_IMMUTABLE_FIELDS = {"author", "achievement_friendly", "categories", "thumbnail_url"}


def load_cache(path: Path) -> dict[str, dict]:
    """Load cache from disk. Returns empty dict on missing/corrupt file."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("version") != CACHE_VERSION:
            return {}
        return data.get("entries", {})
    except (FileNotFoundError, json.JSONDecodeError, OSError, KeyError):
        return {}


def save_cache(entries: dict[str, dict], path: Path) -> None:
    """Write cache to disk. Silently ignores write failures."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"version": CACHE_VERSION, "entries": entries}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def clear_cache(path: Path) -> None:
    """Delete the cache file from disk."""
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def is_session_fresh(start_time: float, window: int) -> bool:
    """Return True if within the session window (seconds since start_time)."""
    return (time.monotonic() - start_time) < window


def info_to_entry(info: CreationInfo) -> dict:
    """Convert a CreationInfo to a cache entry dict."""
    return {
        "fetched_at": time.time(),
        "author": info.author,
        "achievement_friendly": info.achievement_friendly,
        "categories": info.categories,
        "thumbnail_url": info.thumbnail_url,
        "version": info.version,
        "price": info.price,
        "installation_size": info.installation_size,
        "last_updated": info.last_updated,
        "created_on": info.created_on,
    }


def entry_to_info(entry: dict) -> CreationInfo:
    """Convert a cache entry dict to a CreationInfo."""
    return CreationInfo(
        version=entry.get("version"),
        author=entry.get("author"),
        price=entry.get("price", 0),
        installation_size=entry.get("installation_size"),
        last_updated=entry.get("last_updated"),
        created_on=entry.get("created_on"),
        categories=entry.get("categories", []),
        achievement_friendly=entry.get("achievement_friendly", False),
        thumbnail_url=entry.get("thumbnail_url"),
    )


def merge_with_cached(fresh: CreationInfo, cached_entry: dict) -> CreationInfo:
    """Merge fresh API data with cached immutable fields."""
    for field_name in _IMMUTABLE_FIELDS:
        cached_val = cached_entry.get(field_name)
        if cached_val is not None:
            setattr(fresh, field_name, cached_val)
    return fresh
