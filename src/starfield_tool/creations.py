"""Adapter between the bethesda_creations library and the starfield_tool app."""
from copy import deepcopy
from typing import NamedTuple

from bethesda_creations import CreationsClient, ClientConfig, ContentQuery, CreationInfo
from bethesda_creations._version_cmp import compare_versions

from starfield_tool.base import StatusBarAPI
from starfield_tool.config import _config_path
from starfield_tool.models import Creation

_CACHE_FILE = _config_path().parent / "creations_cache.json"


class CheckResult(NamedTuple):
    """Result of a check operation with skipped-creation count."""
    creations: list[Creation]
    skipped: int


def _make_client(
    status_bar: StatusBarAPI | None = None,
    app_start_time: float = 0.0,
) -> CreationsClient:
    return CreationsClient(ClientConfig(
        cache_path=_CACHE_FILE,
        session_start_time=app_start_time,
        progress_callback=status_bar.set_task if status_bar else None,
    ))


def _to_queries(creations: list[Creation]) -> list[ContentQuery]:
    return [
        ContentQuery(content_id=c.content_id, display_name=c.display_name)
        for c in creations
    ]


def check_for_updates(
    creations: list[Creation],
    status_bar: StatusBarAPI,
    app_start_time: float = 0.0,
) -> CheckResult:
    """Check for updates and return a new list with update info populated."""
    try:
        client = _make_client(status_bar, app_start_time)
        latest = client.fetch_info(_to_queries(creations))
    except Exception:
        return CheckResult([deepcopy(c) for c in creations], 0)

    result = []
    skipped = 0
    for creation in creations:
        c = deepcopy(creation)
        info = latest.get(c.content_id)
        if info and info.version:
            c.available_version = info.version
            c.has_update = compare_versions(c.installed_version, info.version)
        elif not info:
            skipped += 1
        result.append(c)

    return CheckResult(result, skipped)


def check_achievements(
    creations: list[Creation],
    status_bar: StatusBarAPI,
    app_start_time: float = 0.0,
) -> CheckResult:
    """Check achievement friendliness for all creations."""
    try:
        client = _make_client(status_bar, app_start_time)
        info_map = client.fetch_info(_to_queries(creations))
    except Exception:
        return CheckResult([deepcopy(c) for c in creations], 0)

    result = []
    skipped = 0
    for creation in creations:
        c = deepcopy(creation)
        info = info_map.get(c.content_id)
        if info:
            c.achievement_friendly = info.achievement_friendly
        else:
            skipped += 1
        result.append(c)

    return CheckResult(result, skipped)


def get_cached_info(app_start_time: float = 0.0) -> dict[str, CreationInfo]:
    """Return all cached creation info within the session window."""
    from bethesda_creations._cache import load_cache, is_session_fresh, entry_to_info
    cache = load_cache(_CACHE_FILE)
    if not cache or not is_session_fresh(app_start_time, 1800):
        return {}
    return {cid: entry_to_info(entry) for cid, entry in cache.items()}


def get_cached_info_any() -> dict[str, CreationInfo]:
    """Return all cached creation info regardless of session freshness.

    Useful for reading immutable fields (author, description, etc.)
    that never change after publish.  Returns empty dict if the cache
    file is missing or corrupt.
    """
    from bethesda_creations._cache import load_cache, entry_to_info
    cache = load_cache(_CACHE_FILE)
    if not cache:
        return {}
    return {cid: entry_to_info(entry) for cid, entry in cache.items()}


def clear_cache() -> None:
    """Delete all cached API responses."""
    client = CreationsClient(ClientConfig(cache_path=_CACHE_FILE))
    client.clear_cache()
