"""LOOT masterlist management — fetch, cache, and locate."""
import json
import time
from pathlib import Path

import httpx

# LOOT's Starfield masterlist on GitHub (v0.21 branch is current stable)
_MASTERLIST_URL = (
    "https://raw.githubusercontent.com/loot/starfield/v0.21/masterlist.yaml"
)
_META_FILENAME = "loot_masterlist_meta.json"
_MASTERLIST_FILENAME = "loot_masterlist.yaml"
_CHECK_INTERVAL = 86400  # re-check GitHub at most once per day (seconds)


def get_masterlist(
    data_dir: Path,
    bundled_path: Path | None = None,
) -> Path | None:
    """Return the path to the best available LOOT masterlist.

    Priority:
    1. Cached copy in data_dir (if fresh or fetch fails)
    2. Bundled copy (shipped with the EXE)
    3. None (LOOT sorting unavailable)
    """
    cached = data_dir / _MASTERLIST_FILENAME
    if cached.exists():
        return cached
    if bundled_path and bundled_path.exists():
        return bundled_path
    return None


def update_masterlist(
    data_dir: Path,
    progress_callback=None,
) -> Path | None:
    """Try to fetch the latest masterlist from GitHub.

    Returns the path to the cached masterlist, or None on failure.
    Skips the fetch if the last successful check was within the
    check interval.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    cached = data_dir / _MASTERLIST_FILENAME
    meta_path = data_dir / _META_FILENAME

    # Check if we fetched recently
    if _is_check_recent(meta_path):
        return cached if cached.exists() else None

    if progress_callback:
        progress_callback("Updating LOOT masterlist...")

    try:
        resp = httpx.get(_MASTERLIST_URL, timeout=30, follow_redirects=True)
        if resp.status_code == 200 and len(resp.text) > 100:
            cached.write_text(resp.text, encoding="utf-8")
            _write_meta(meta_path)
            return cached
    except (httpx.HTTPError, OSError):
        pass

    # Fetch failed — return cached if it exists from a previous run
    return cached if cached.exists() else None


def _is_check_recent(meta_path: Path) -> bool:
    """Return True if we checked GitHub within the check interval."""
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        last_check = meta.get("last_check", 0)
        return (time.time() - last_check) < _CHECK_INTERVAL
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return False


def _write_meta(meta_path: Path) -> None:
    """Record the current time as last check."""
    try:
        meta_path.write_text(
            json.dumps({"last_check": time.time()}),
            encoding="utf-8",
        )
    except OSError:
        pass
