# Quickstart: Creations Grid Modes & Details Dialog

**Branch**: `004-creations-grid-modes` | **Date**: 2026-04-01

## What This Feature Does

Adds two display modes to the installed creations tab (text list with author column, rich media with thumbnails) and a reusable creation details dialog.

## Key Files to Touch

| File | Change |
|------|--------|
| `src/starfield_tool/creations.py` | Add `get_cached_info_any()` — reads cache ignoring session freshness |
| `src/starfield_tool/tools/creation_load_order.py` | Add mode toggle, author column, rich media grid, details button |
| `src/starfield_tool/dialogs/__init__.py` | New package for shared dialogs |
| `src/starfield_tool/dialogs/creation_details.py` | New `CreationDetailsDialog` — reusable, decoupled from any tab |
| `tests/test_creation_details_dialog.py` | Tests for the details dialog |
| `tests/test_grid_modes.py` | Tests for mode switching, author column, placeholder behavior |

## Architecture Decisions

1. **Text list stays as `ttk.Treeview`** — fast, proven, just add an Author column
2. **Rich media uses scrollable `CTkFrame` rows** — Treeview can't do inline images + multi-line text
3. **Details dialog is standalone** — lives in `dialogs/` not `tools/`, accepts `CreationInfo` + display name
4. **Cache read without freshness** — new `get_cached_info_any()` function, doesn't modify existing API
5. **Pillow for thumbnails** — already a transitive dep of customtkinter, used for JPEG support + resizing

## Threading Model

Same pattern as existing update/achievement checks:
1. Spawn daemon thread for cache fetch / image download
2. Use `widget.after(0, callback)` to update UI on main thread
3. Status bar progress via existing `StatusBarAPI`

## How to Test

```bash
pytest tests/test_creation_details_dialog.py tests/test_grid_modes.py
```

Manual: Launch app → Installed Creations tab → toggle modes, click Details button.
