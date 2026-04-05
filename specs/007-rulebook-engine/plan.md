# Implementation Plan: Load Order Rule Books

**Branch**: `007-rulebook-engine` | **Date**: 2026-04-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-rulebook-engine/spec.md`

## Summary

Add a rule book system with three layers: (1) a sorter that produces `load_after` constraints from JSON rule book files at two priority tiers (curated=30, user=40+), (2) a management tool tab for viewing, enabling, disabling, and reordering books, and (3) an editor dialog for creating and modifying rule books. Rule books gracefully handle missing creations and corrupted files. New user books default to highest priority (newest-first by creation date).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: customtkinter (GUI, already in project), json (stdlib)
**Storage**: JSON files in `%APPDATA%/StarfieldToolkit/rules/` (user) and bundled `data/rules/` (curated). Registry in existing `config.json`.
**Testing**: pytest
**Target Platform**: Windows (desktop app)
**Project Type**: Desktop app feature extension
**Performance Goals**: Rule book loading < 500ms for 50 books
**Constraints**: No new external dependencies; must integrate with existing sorter pipeline and tool tab system
**Scale/Scope**: Up to 50 rule books, each with up to 100 rules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS)
- **PASS**: Rule book I/O is JSON load/save. Sorter follows existing pattern (produces SortConstraint list). Management tool follows ToolModule pattern. Editor is a simple dialog. No design patterns or abstractions beyond what exists.

### II. Test Coverage (NON-NEGOTIABLE)
- **PASS**: Tests for rule book I/O, applicability checking, sorter constraint generation, registry reconciliation, and missing creation detection.

### III. Minimal Dependencies
- **PASS**: Zero new dependencies. JSON parsing is stdlib, GUI uses existing customtkinter.

### IV. Clear Interfaces
- **PASS**: Rule book file format is a documented JSON schema. Sorter has standard `sort()` interface. Management tool follows ToolModule contract. Editor has clear create/edit/save workflow.

## Project Structure

### Documentation (this feature)

```text
specs/007-rulebook-engine/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
data/
└── rules/                                   # [NEW] Curated rule book files (bundled)

src/
├── load_order_sorter/
│   ├── pipeline.py                          # [MODIFIED] Register rulebook sorter
│   ├── rulebook.py                          # [NEW] Rule book I/O, parsing, applicability
│   └── sorters/
│       └── rulebook.py                      # [NEW] Rule book sorter
└── starfield_tool/
    ├── config.py                            # [MODIFIED] Add rulebook_registry to AppSettings
    ├── tools/
    │   ├── __init__.py                      # [MODIFIED] Register RuleBookTool
    │   └── rulebook_manager.py              # [NEW] Management tool tab
    └── dialogs/
        └── rulebook_editor.py               # [NEW] Create/edit dialog

bin/
└── build.sh                                 # [MODIFIED] Bundle curated rules via --add-data

tests/
├── test_rulebook.py                         # [NEW] I/O, parsing, applicability, registry
└── test_rulebook_sorter.py                  # [NEW] Sorter integration tests
```

**Structure Decision**: Follows existing patterns — sorter in `sorters/rulebook.py`, I/O utility in `load_order_sorter/rulebook.py`, tool tab in `tools/rulebook_manager.py`, dialog in `dialogs/rulebook_editor.py`. Curated rule books in `data/rules/` alongside the LOOT masterlist pattern.

## Complexity Tracking

No constitution violations. No entries needed.
