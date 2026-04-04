# Implementation Plan: Load Order Sorting Tool

**Branch**: `003-load-order-sorting` | **Date**: 2026-03-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-load-order-sorting/spec.md`

## Summary

Implement load order management in a standalone `load_order_sorter` package with a clean API. Sorters produce **constraints** (tier assignments, load-after rules), not positions. The pipeline merges all constraints with priority-based conflict resolution, then a single solver produces the final order. This avoids multi-pass risks and correctly handles cross-sorter interactions. Unsorted items preserve relative positions (stable sort). The `starfield_tool` is responsible only for UI: drag-and-drop, dirty state, diff view with sorter attribution, and Starfield process detection.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: PyYAML (new — for LOOT masterlist parsing), httpx (existing — for masterlist fetch), customtkinter (existing — UI)
**Storage**: Plugins.txt (read/write), snapshot files (JSON), LOOT masterlist YAML (fetched/bundled)
**Testing**: pytest (existing)
**Target Platform**: Windows (desktop GUI)
**Project Type**: Desktop application (3 packages: `bethesda_creations`, `load_order_sorter`, `starfield_tool`)
**Performance Goals**: Auto sort under 2 seconds for 50+ creations
**Constraints**: Sort must be stable — unsorted creations preserve relative positions
**Scale/Scope**: 5–50 creations typical, max ~150

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Simplicity First (KISS) | PASS | Flat functions for sorters, simple priority list. No strategy pattern or factory — just a list of callables. Stable sort via Python's `sorted()` with `key` function. |
| II. Test Coverage | PASS | Each sorter testable independently with fixture data. Pipeline merge logic testable. Snapshot round-trip testable. No GUI mocking needed for the sorter package. |
| III. Minimal Dependencies | PASS | Only PyYAML added (for LOOT masterlist). Standard library otherwise. PyYAML is small, well-maintained, MIT-licensed. |
| IV. Clear Interfaces | PASS | `load_order_sorter` exposes: `sort_creations()` returning `SortResult` with per-item attribution. No hidden state. starfield_tool only calls this API. |

**Gate result**: All principles pass. One new dependency (PyYAML) justified — LOOT masterlists are YAML, no stdlib alternative.

## Project Structure

### Documentation (this feature)

```text
specs/003-load-order-sorting/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── sorter-api.md
└── tasks.md
```

### Source Code (repository root)

```text
src/
  load_order_sorter/              # NEW standalone package
    __init__.py                   # Re-exports: sort_creations, SortResult, SortItem, Snapshot
    pipeline.py                   # Constraint-based sorter pipeline + stable merge
    loot_masterlist.py            # LOOT masterlist fetch, cache, and locate
    sorters/
      __init__.py
      category.py                 # Category-based sorter (11-tier + author detection)
      loot.py                     # LOOT masterlist YAML parser + sorter
    snapshot.py                   # Snapshot export/import
    models.py                     # SortItem, SortResult, SortDecision, Snapshot models

  starfield_tool/
    tools/
      load_order.py               # NEW — Load Order tab UI (drag-drop, diff view, buttons)
      load_order_diff.py          # NEW — Git-merge-style diff dialog
      creation_load_order.py      # EXISTING — Installed Creations tab (unchanged)

tests/
  test_load_order_sorter.py       # Pipeline, sorters, snapshots
```

**Structure Decision**: New `load_order_sorter` package alongside `bethesda_creations` and `starfield_tool`. Three peer packages in `src/`, each with distinct responsibilities and no circular dependencies.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| 3rd package (`load_order_sorter`) | Sorting logic is complex and will grow (custom rules in future). Clean API boundary prevents coupling with GUI code. | Putting it in `starfield_tool` would mix sorting algorithms with UI code, making testing harder and preventing reuse. |

---
