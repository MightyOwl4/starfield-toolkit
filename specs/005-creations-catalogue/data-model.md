# Data Model: Creations Text Catalogue

**Date**: 2026-04-05 | **Branch**: `005-creations-catalogue`

## Entities

### CatalogueEntry

Represents a single creation's text content, metadata, and dependency info from the Bethesda API.

| Field | Type | Description |
|-------|------|-------------|
| content_id | string | Unique creation identifier (UUID, e.g., `beefc7ae-59f4-4934-b2a5-d04e5264f029`) |
| title | string | Creation title |
| author | string | Author display name (`author_displayname` from API) |
| categories | list[string] | Category tags |
| price | integer | Price in credits (0 = free, from `catalog_info`) |
| description | string | Full description text (from API `description` field) |
| overview | string | Additional overview text (from API `overview` field, often empty) |
| release_notes | list[dict] | Structured version history per platform (from API `release_notes` field). Each entry: `{hardware_platform, release_notes: [{version_name, note, ctime}]}` |
| required_mods | list | Dependency declarations from the author (from API `required_mods` field, for feature 006) |
| achievement_friendly | bool | Whether the creation is achievement-friendly |
| content_hash | string | SHA-256 hex digest of `description + normalized_release_notes_text` (concatenated, no separator) |
| fetched_at | string | ISO 8601 timestamp of when this entry was fetched |

**Identity**: `content_id` (UUID) is the unique key.

**Lifecycle**:
- Created when fetched from the API for the first time
- Never expires or auto-invalidates
- Updated only on explicit force-refresh (all fields overwritten)
- Content change detection: compare `content_hash` after re-fetch

### CatalogueFile

The on-disk JSON file containing all catalogue entries.

**Location**: `%APPDATA%/StarfieldToolkit/creations_catalogue.json`

**Structure**:
```json
{
  "version": 1,
  "entries": {
    "<content_id>": {
      "title": "string",
      "author": "string",
      "categories": ["string"],
      "price": 0,
      "description": "string",
      "overview": "string",
      "release_notes": [
        {
          "hardware_platform": "WINDOWS",
          "release_notes": [
            {"version_name": "1.0", "note": "Initial Upload", "ctime": 1717532554}
          ]
        }
      ],
      "required_mods": [],
      "achievement_friendly": true,
      "content_hash": "sha256hex",
      "fetched_at": "2026-04-05T12:00:00Z"
    }
  }
}
```

**Invariants**:
- `version` field for future schema migrations
- `entries` is a dict keyed by `content_id` for O(1) lookup (skip-existing check)
- No expiration fields at file or entry level
- File is atomically overwritten after each batch of entries is added (write to temp file, rename)

## Relationships

- **CatalogueFile** contains 0..N **CatalogueEntry** objects
- **CatalogueEntry** is independent of `CreationInfo` (existing cache model) — no foreign key or coupling
- **CatalogueEntry.content_id** may correspond to an installed creation's content_id, but this is not enforced
- **CatalogueEntry.required_mods** will be consumed by feature 006 for dependency graph construction

## Data Volume Estimates

- Starfield creations catalogue: ~4,954 entries (as of 2026-04-05)
- Each entry: ~2-20 KB (description + structured release notes + metadata)
- Total catalogue file size: estimated 20-100 MB (manageable as single JSON file)
- API pages: ~248 at size=20
