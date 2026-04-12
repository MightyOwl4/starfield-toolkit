# Implementation Plan: Diff Dialog Visual Connectors and Hint Dialog

**Branch**: `010-diff-connectors` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-diff-connectors/spec.md`

## Summary

Add visual connectors and a per-move hints dialog to the Load Order diff dialog. Truly-moved items get a colored Bezier curve drawn on a middle Canvas column between the two treeviews, with colored endpoint dots. Each moved row in the right panel gains a colored ⓘ icon in the Info column whose click opens a dialog listing every constraint that shaped the move (winners and losers alike), sorted by priority, with rulebook filenames and notes for RULE-sourced hints. Multiple winner badges per plugin are supported (one for tier, one per `load_after` edge). To make losing constraints available to the UI, `SortDecision` gains `all_constraints`, `SortConstraint` gains `note`, and the rulebook sorter tags constraints with `sorter_name="RULE:<filename>"`.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: customtkinter (already present), stdlib `tkinter` (Canvas, ttk), stdlib `difflib` (already used for minimal-diff)
**Storage**: N/A (UI-only state; data model changes are in-memory per-sort)
**Testing**: pytest (headless — no Tk event loop); UI behavior verified manually per existing project pattern
**Target Platform**: Windows desktop (primary), Linux/macOS (secondary per project support)
**Project Type**: Desktop application (single project — `src/` + `tests/`)
**Performance Goals**: Connector redraw on scroll/resize must keep 60 fps feel with ≤20 connectors (≤50 lines + dots). No sort-pipeline performance impact.
**Constraints**: No new external dependencies. Must work at 100–150% DPI. Must not alter Auto-Sort semantics.
**Scale/Scope**: Up to ~200 plugins in a load order, up to ~20 moves per sort in realistic usage.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS) — PASS
- Reuses existing `SequenceMatcher` move detection, existing `SortConstraint`/`SortDecision` dataclasses, existing `CTkToplevel`+`center_dialog` dialog pattern.
- `all_constraints` is a plain list field on an existing dataclass — no new patterns.
- Bezier drawing is one `canvas.create_line(..., smooth=True)` call per move — no custom graphics library.
- Color palette is a 6-entry `list[str]` constant; cycle via `index % len`.
- No factory/strategy/observer patterns added.

### II. Test Coverage (NON-NEGOTIABLE) — PASS
- New data behavior (`SortDecision.all_constraints` populated, rulebook `sorter_name` carries filename, `SortConstraint.note` propagated) is testable via existing pytest infrastructure without Tk.
- Tests added per behavior: one test for all_constraints preservation, one for filename-qualified sorter_name in both order and tier rulebook paths, one for note propagation.
- UI-only behavior (Canvas drawing, dialog rendering) follows project precedent of manual verification — documented in quickstart.md.

### III. Minimal Dependencies — PASS
- No new dependencies. All drawing uses stdlib `tkinter.Canvas`. All widgets reuse customtkinter already in use.

### IV. Clear Interfaces — PASS
- `SortDecision.all_constraints: list[SortConstraint]` — clear, typed, default empty.
- `SortConstraint.note: str = ""` — clear, typed, default empty.
- `sorter_name` string convention `"RULE:<filename>"` is documented in both the rulebook sorter module docstring and the data-model.md.
- No silent error swallowing introduced; existing behavior preserved.

**Gate status: PASS. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/010-diff-connectors/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (written by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── load_order_sorter/
│   ├── models.py                       # MODIFY: add note to SortConstraint, all_constraints to SortDecision
│   ├── pipeline.py                     # MODIFY: populate all_constraints in _merge_constraints
│   └── sorters/
│       └── rulebook.py                 # MODIFY: sorter_name="RULE:<filename>", pass note through
└── starfield_tool/
    └── tools/
        └── load_order_diff.py          # MODIFY: Canvas column, connectors, hint icon, hints dialog

tests/
├── test_load_order_sorter.py           # ADD: test all_constraints contains losers
├── test_rulebook_sorter.py             # ADD: test sorter_name includes filename, note propagated
└── test_rulebook.py                    # possibly touch for note roundtrip
```

**Structure Decision**: Single-project layout (matches existing repo). No new modules; all changes are in existing files except the new docs in `specs/010-diff-connectors/`.

## Complexity Tracking

No constitution violations. Table omitted.
