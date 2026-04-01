# Data Model: Creations Grid Modes & Details Dialog

**Branch**: `004-creations-grid-modes` | **Date**: 2026-04-01

## Existing Entities (No Changes)

### CreationInfo (bethesda_creations/models.py)

Already contains all fields needed for both grid modes and the details dialog:

| Field | Type | Mutable | Used In |
|-------|------|---------|---------|
| title | str \| None | No | Rich media name, details dialog |
| description | str \| None | No | Rich media excerpt, details dialog |
| author | str \| None | No | Text list column, details dialog |
| version | str \| None | Yes | Details dialog |
| price | int | Yes | Details dialog (0 = Free) |
| installation_size | str \| None | Yes | Details dialog |
| last_updated | str \| None | Yes | Details dialog |
| created_on | str \| None | Yes | Details dialog |
| categories | list[str] | No | Details dialog |
| achievement_friendly | bool | No | Details dialog |
| thumbnail_url | str \| None | No | Rich media thumbnail, details dialog |

### Creation (starfield_tool/models.py)

Local metadata for installed creations. No changes needed — `content_id` links to cache entries.

### Cache Entry (bethesda_creations/_cache.py)

JSON dict stored on disk, keyed by `content_id`. No schema changes needed.

## New Concepts (In-Memory Only)

### GridMode (enum-like)

Represents the current display mode of the installed creations grid.

| Value | Description |
|-------|-------------|
| TEXT_LIST | Traditional treeview with text columns (default) |
| RICH_MEDIA | Custom widget rows with thumbnails and formatted text |

### ThumbnailCache (in-memory dict)

Session-scoped cache of downloaded thumbnail images, keyed by `content_id`.

| Key | Value | Lifecycle |
|-----|-------|-----------|
| content_id (str) | PIL Image object (resized) | Created on first display, cleared on app exit |

## Entity Relationships

```
Creation (installed, local)
  └── content_id ──→ Cache Entry (remote metadata, on disk)
                        └── entry_to_info() ──→ CreationInfo (in-memory)
                                                   ├── author → Text list column
                                                   ├── thumbnail_url → ThumbnailCache → Rich media row
                                                   └── all fields → Details dialog
```

## State Transitions

### Grid Mode State

```
TEXT_LIST (default on tab load)
  ├── Toggle → RICH_MEDIA
  │              ├── Cache warm → Render rows immediately
  │              └── Cache cold → Show placeholders → Trigger fetch → Render on complete
  └── Cache clear event → No effect (already text, author shows "n/a")

RICH_MEDIA
  ├── Toggle → TEXT_LIST (instant, no fetch needed)
  └── Cache clear event → Reset to placeholders → Trigger fetch → Render on complete
```
