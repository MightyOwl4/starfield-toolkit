# Data Model: Creations API Response Caching

## CacheFile

The top-level structure persisted to disk.

| Field       | Type                        | Description                          |
| ----------- | --------------------------- | ------------------------------------ |
| version     | int                         | Cache format version (currently `1`) |
| entries     | dict[str, CacheEntry]       | Keyed by `content_id`                |

## CacheEntry

Per-creation cached API response data.

| Field                 | Type         | Volatile | Description                                    |
| --------------------- | ------------ | -------- | ---------------------------------------------- |
| content_id            | str          | -        | Cache key, matches Creation.content_id         |
| fetched_at            | float        | -        | Wall-clock timestamp of last API fetch         |
| author                | str or null  | No       | Display name of the creation author            |
| achievement_friendly  | bool         | No       | Whether the creation is achievement safe       |
| categories            | list[str]    | No       | Category tags from the API                     |
| thumbnail_url         | str or null  | No       | Preview image URL                              |
| version               | str or null  | Yes      | Latest version string from API                 |
| price                 | int          | Yes      | Price in Creations credits (0 = free)          |
| installation_size     | str or null  | Yes      | Human-readable size string                     |
| last_updated          | str or null  | Yes      | Date string of last update                     |
| created_on            | str or null  | Yes      | Date string of creation publish                |

## Field Classification

- **Immutable fields** (`volatile=No`): Cached permanently. Only fetched from API if the entry doesn't exist in cache at all.
- **Volatile fields** (`volatile=Yes`): Cached but subject to session window staleness. Re-fetched if `time.monotonic() - app_start_time >= 1800`.

## State Transitions

```
No cache entry → API fetch → Cache entry created (all fields populated)
                                    │
            ┌───────────────────────┼───────────────────────┐
            ▼                       ▼                       ▼
    Within session window    Session window expired    Cache cleared
    (use all cached data)    (re-fetch volatile only)  (back to no entry)
```
