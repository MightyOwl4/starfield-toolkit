# Contract: Cache Access (Freshness-Agnostic)

**Type**: Internal function (adapter layer)

## New Function

### `get_cached_info_any()`

```
get_cached_info_any() -> dict[str, CreationInfo]
```

**Location**: `starfield_tool/creations.py`

**Behavior**: Reads all entries from the cache file on disk and converts them to `CreationInfo` objects. Does NOT check session freshness. Returns empty dict if cache file is missing or corrupt.

**Use case**: Populating the Author column in text list mode without triggering network activity. Safe because author is an immutable field (never changes after creation publish).

**Contrast with existing `get_cached_info(app_start_time)`**: The existing function gates on `is_session_fresh()` and returns empty dict if session has expired. The new function always returns whatever is on disk.
