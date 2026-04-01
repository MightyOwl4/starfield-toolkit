# Implementation Plan: Creations Grid Modes & Details Dialog

**Branch**: `004-creations-grid-modes` | **Date**: 2026-04-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-creations-grid-modes/spec.md`

## Summary

Add two display modes (text list with author column, rich media with thumbnails) to the installed creations tab, plus a reusable creation details dialog. Text list mode reads cache without freshness checks. Rich media mode forces cache fetch when cold and shows loading placeholders. The details dialog is a standalone component following the existing diff dialog windowing pattern.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: customtkinter (GUI), Pillow (thumbnails — already transitive dep of customtkinter)  
**Storage**: Existing JSON cache file (`creations_cache.json`)  
**Testing**: pytest  
**Target Platform**: Windows (desktop)  
**Project Type**: Desktop application  
**Performance Goals**: Mode switch < 1s with warm cache; thumbnail download async  
**Constraints**: No new external dependencies; follow existing threading pattern  
**Scale/Scope**: ~50-200 installed creations typical

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Research Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First (KISS) | PASS | Text list extends existing Treeview; rich media uses simple CTkFrame rows; no design patterns introduced |
| II. Test Coverage | PASS | Plan includes tests for all public interfaces: cache access, dialog, mode switching |
| III. Minimal Dependencies | PASS | Pillow is already a transitive dependency of customtkinter, not a new addition |
| IV. Clear Interfaces | PASS | Details dialog has explicit constructor parameters; new cache function has clear name and return type |

### Post-Design Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First (KISS) | PASS | No factories, no observers, no abstract base classes. Dialog is a plain class. Mode toggle is a simple state variable. |
| II. Test Coverage | PASS | Tests cover: `get_cached_info_any()`, dialog construction, author column population, placeholder behavior |
| III. Minimal Dependencies | PASS | Only using Pillow (already installed) and stdlib `urllib.request` |
| IV. Clear Interfaces | PASS | `CreationDetailsDialog(parent, display_name, info, thumbnail_image)` — all inputs explicit, no hidden state |

## Project Structure

### Documentation (this feature)

```text
specs/004-creations-grid-modes/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── creation_details_dialog.md
│   └── cache_access.md
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── bethesda_creations/      # No changes to this package
│   ├── _cache.py            # (read-only reference for load_cache, entry_to_info)
│   ├── client.py
│   └── models.py            # CreationInfo — no changes needed
│
└── starfield_tool/
    ├── creations.py         # Add get_cached_info_any()
    ├── dialogs/             # NEW — shared dialog components
    │   ├── __init__.py
    │   └── creation_details.py  # CreationDetailsDialog
    └── tools/
        └── creation_load_order.py  # Mode toggle, author column, rich media grid, details button

tests/
├── test_creation_details_dialog.py  # Dialog construction and field display
└── test_grid_modes.py              # Mode switching, author column, placeholders
```

**Structure Decision**: Single project layout. New `dialogs/` package under `starfield_tool/` for reusable UI components (separate from `tools/` which are tab-bound modules). This keeps the details dialog decoupled per FR-014.

## Complexity Tracking

No constitution violations — table not needed.
