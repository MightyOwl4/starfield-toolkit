# Research: Creations API Response Caching

## R1: Cache Storage Format

**Decision**: Single JSON file at `{config_dir}/creations_cache.json`

**Rationale**: The app already uses JSON for config persistence (`config.py`). A single file keeps it simple — no need for SQLite or multiple files. The dataset is small (50 Creations max, ~100 bytes each = ~5KB).

**Alternatives considered**:
- SQLite: Overkill for <100 entries. Adds complexity and potentially a dependency.
- One file per Creation: Creates filesystem clutter, harder to clear atomically.
- Pickle: Not human-readable, security concerns with untrusted data.

## R2: Cache Key Strategy

**Decision**: Use `content_id` (e.g., `SFBGS006`, `TM_<uuid>`) as the cache key, matching the existing Creation model.

**Rationale**: `content_id` is the unique identifier already used throughout the codebase. It's stable across sessions and available before any API call.

**Alternatives considered**:
- UUID only: Would lose the mapping for non-UUID IDs (official DLC like `SFBGS006`) that require title-based search.
- Display name: Not unique, could collide.

## R3: Session Window Implementation

**Decision**: Record `app_start_time = time.monotonic()` at startup. A cached volatile entry is fresh if `time.monotonic() - app_start_time < 1800` (30 minutes). Per-creation `fetched_at` uses `time.time()` (wall clock) for persistence across restarts.

**Rationale**: Monotonic time for session window avoids issues with system clock changes. Wall clock for `fetched_at` timestamps because they need to be meaningful across app restarts (to determine if immutable data was ever fetched).

**Alternatives considered**:
- Wall clock for everything: Vulnerable to clock skew/changes.
- Monotonic for everything: Can't persist across restarts (resets to 0).

## R4: Immutable vs Volatile Field Split

**Decision**:
- **Immutable** (never re-fetched once cached): `author`, `achievement_friendly`, `categories`, `thumbnail_url`
- **Volatile** (re-fetched when session window expires): `version`, `price`, `installation_size`, `last_updated`, `created_on`

**Rationale**: Author and achievement status are set at publish time and don't change. Version and price can change with updates or sales. This split matches the user's explicit description.

## R5: Cache Integration Point

**Decision**: Add cache as an optional parameter to `_fetch_creation_info()`. The function checks cache first, fetches only uncached/stale entries from the API, then merges and saves.

**Rationale**: Keeps the change minimal — one function gains cache awareness. Callers (`check_for_updates`, `check_achievements`) pass the cache through. The cache module itself is a simple standalone module with no coupling to the API logic.

**Alternatives considered**:
- Decorator/middleware pattern: Over-engineered for a single function.
- Cache at the caller level: Would duplicate cache logic in both `check_for_updates` and `check_achievements`.

## R6: Refresh State Preservation

**Decision**: On refresh, if cached check results exist (within session window), reapply `available_version`, `has_update`, and `achievement_friendly` from the cache to the newly loaded Creations list.

**Rationale**: This directly addresses the user's concern about losing "5 updates available" state after a single in-game update triggers a refresh. The cache serves double duty: reducing API calls AND preserving check state.
