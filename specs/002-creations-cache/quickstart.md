# Quickstart: Creations API Response Caching

## What This Feature Does

Caches Bethesda Creations API responses to disk so that repeated checks (updates, achievements) don't re-fetch data that was already retrieved recently. Immutable data (author, achievement status) is cached permanently. Volatile data (version, price) is cached for the duration of a session (30 minutes from app start).

## Key Files

| File | Role |
| ---- | ---- |
| `src/starfield_tool/cache.py` | NEW — cache load, save, clear, staleness checks |
| `src/starfield_tool/version_checker.py` | MODIFIED — integrate cache into fetch flow |
| `src/starfield_tool/app.py` | MODIFIED — record startup time |
| `src/starfield_tool/tools/creation_load_order.py` | MODIFIED — add Clear Cache button, reuse cached state on refresh |
| `tests/test_cache.py` | NEW — cache module tests |

## Implementation Order

1. **cache.py** — standalone module, no dependencies on existing code beyond `config.py` for the data dir path
2. **version_checker.py** — wire cache into `_fetch_creation_info`, `check_for_updates`, `check_achievements`
3. **app.py** — store `app_start_time` and pass through `ModuleContext`
4. **creation_load_order.py** — add Clear Cache button, restore cached state on refresh
5. **tests** — throughout, but `test_cache.py` can be written first as the module is standalone

## How to Test

```bash
uv run pytest tests/test_cache.py tests/test_version_checker.py -v
```

## Session Window Logic

```
app starts → record monotonic time
user clicks check → for each creation:
  if no cache entry → fetch from API, cache it
  if cache entry exists:
    if session window still open (< 30 min since app start):
      use cached data (all fields)
    else:
      re-fetch volatile fields only, keep immutable from cache
```
