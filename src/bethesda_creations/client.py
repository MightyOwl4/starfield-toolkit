"""Bethesda Creations API client with transparent caching."""
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import httpx

from bethesda_creations.models import CreationInfo
from bethesda_creations._api import (
    fetch_bnet_key, content_id_to_uuid, search_uuid_by_title,
    parse_response, CREATIONS_API,
)
from bethesda_creations._cache import (
    load_cache, save_cache, clear_cache as _clear_cache,
    is_session_fresh, entry_to_info, info_to_entry, merge_with_cached,
)


@dataclass(frozen=True)
class ClientConfig:
    """Configuration for the Creations API client."""
    cache_path: Path | None = None
    session_start_time: float = 0.0  # time.monotonic() at session start
    session_start_wall: float = 0.0  # time.time() at session start (unix epoch)
    session_window: int = 1800  # 30 minutes
    request_timeout: int = 15
    progress_callback: Callable[[str], None] | None = None


@dataclass(frozen=True)
class ContentQuery:
    """Minimal input for a creation lookup."""
    content_id: str
    display_name: str


class CreationsClient:
    """Client for the Bethesda Creations API with disk caching."""

    def __init__(self, config: ClientConfig | None = None):
        self._config = config or ClientConfig()

    def fetch_info(
        self, queries: list[ContentQuery],
    ) -> dict[str, CreationInfo]:
        """Fetch metadata for creations, using cache where possible.

        A cache entry is only reused if it was fetched DURING the current
        session. Entries from previous sessions are revalidated via the API.
        This means the first call in a session always makes network requests
        (to refresh stale data), and subsequent calls within the session reuse
        the freshly fetched data without extra API traffic.

        Returns a dict mapping content_id -> CreationInfo.
        """
        cfg = self._config
        cache = self._load_cache()
        results: dict[str, CreationInfo] = {}
        needs_fetch: list[ContentQuery] = []

        # Resolve from cache: an entry is "session-fresh" only if it was
        # fetched during the current session (fetched_at >= session_start_wall).
        # Pre-existing cache entries from previous sessions must be revalidated.
        for q in queries:
            entry = cache.get(q.content_id)
            if entry and self._entry_is_session_fresh(entry):
                results[q.content_id] = entry_to_info(entry)
            else:
                needs_fetch.append(q)

        if not needs_fetch:
            return results

        # Fetch missing/stale from API
        bnet_key = fetch_bnet_key(cfg.request_timeout)
        client = httpx.Client(
            timeout=cfg.request_timeout,
            follow_redirects=True,
            headers={
                "x-bnet-key": bnet_key,
                "Content-Type": "application/json",
            },
        )

        try:
            for i, q in enumerate(needs_fetch):
                if cfg.progress_callback:
                    cfg.progress_callback(
                        f"Fetching creation info ({i + 1}/{len(needs_fetch)})..."
                    )

                uuid = content_id_to_uuid(q.content_id)
                if not uuid:
                    uuid = search_uuid_by_title(client, q.display_name)
                if not uuid:
                    cached_entry = cache.get(q.content_id)
                    if cached_entry:
                        results[q.content_id] = entry_to_info(cached_entry)
                    continue

                try:
                    url = CREATIONS_API.format(uuid=uuid)
                    resp = client.get(url)
                    if resp.status_code == 200:
                        info = parse_response(resp.json())
                        cached_entry = cache.get(q.content_id)
                        if cached_entry:
                            info = merge_with_cached(info, cached_entry)
                        results[q.content_id] = info
                        cache[q.content_id] = info_to_entry(info)
                except httpx.HTTPError:
                    continue
        finally:
            client.close()

        self._save_cache(cache)
        return results

    def get_cached(
        self, content_ids: list[str],
    ) -> dict[str, CreationInfo]:
        """Return cached data only (no network calls).

        Returns only entries that were fetched during the current session
        (fetched_at >= session_start_wall). Entries from previous sessions
        are excluded to avoid serving stale data.
        """
        cache = self._load_cache()
        if not cache:
            return {}
        results: dict[str, CreationInfo] = {}
        for cid in content_ids:
            entry = cache.get(cid)
            if entry and self._entry_is_session_fresh(entry):
                results[cid] = entry_to_info(entry)
        return results

    def clear_cache(self) -> None:
        """Delete the cache file from disk."""
        if self._config.cache_path:
            _clear_cache(self._config.cache_path)

    def _load_cache(self) -> dict[str, dict]:
        if self._config.cache_path:
            return load_cache(self._config.cache_path)
        return {}

    def _save_cache(self, entries: dict[str, dict]) -> None:
        if self._config.cache_path:
            save_cache(entries, self._config.cache_path)

    def _is_session_fresh(self) -> bool:
        return is_session_fresh(
            self._config.session_start_time, self._config.session_window,
        )

    def _entry_is_session_fresh(self, entry: dict) -> bool:
        """True if the entry was fetched during the current session window.

        Checks:
        1. We're still within the session window (monotonic time)
        2. The entry's fetched_at (wall-clock) is >= session_start_wall
           — i.e., it was fetched AFTER the current session started, not
           left over from a previous session's cache.
        """
        if not self._is_session_fresh():
            return False
        fetched_at = entry.get("fetched_at", 0) or 0
        return fetched_at >= self._config.session_start_wall
