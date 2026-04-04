# Tasks: Load Order Sorting Tool

**Input**: Design documents from `/specs/003-load-order-sorting/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/sorter-api.md, quickstart.md

**Organization**: Tasks grouped by user story. The `load_order_sorter` package is built first (Phases 1-2), then UI stories layer on top.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Includes exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create the `load_order_sorter` package skeleton and add PyYAML dependency.

- [x] T001 Create package directory structure: src/load_order_sorter/__init__.py, src/load_order_sorter/sorters/__init__.py
- [x] T002 Add `pyyaml>=6.0` to project dependencies in pyproject.toml and add `src/load_order_sorter` to the packages list
- [x] T003 [P] Create data models in src/load_order_sorter/models.py — SortItem, SortConstraint, SortDecision, SortedItem, SortResult dataclasses per data-model.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the constraint-based sorting pipeline and individual sorters. All user stories depend on this.

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 [P] Implement category-based sorter in src/load_order_sorter/sorters/category.py — function that takes list[SortItem] and returns list[SortConstraint] with tier assignments. Map API categories to the 11-tier system per research.md R5 mapping table. SFBGS-prefixed content IDs always get tier 1.
- [x] T005 [P] Implement LOOT masterlist parser and sorter in src/load_order_sorter/sorters/loot.py — function that takes list[SortItem] and a masterlist YAML path, parses groups/plugins/after rules, returns list[SortConstraint] with tier assignments and load_after constraints. Handle missing/corrupt YAML gracefully (return empty list).
- [x] T006 Implement constraint merger in src/load_order_sorter/pipeline.py — function `_merge_constraints(constraints: list[SortConstraint]) -> dict[str, SortDecision]` that resolves tier conflicts by priority (higher wins), accumulates load_after rules (union), and breaks cycles by dropping lower-priority constraint.
- [x] T007 Implement constraint solver in src/load_order_sorter/pipeline.py — function `_solve(items: list[SortItem], decisions: dict[str, SortDecision]) -> list[SortedItem]` that groups items by assigned tier, applies topological sort for load_after within each tier, uses original_index as tiebreaker. Items with no decision go to default tier (9) preserving relative order.
- [x] T008 Implement `sort_creations()` entry point in src/load_order_sorter/pipeline.py — runs active sorters on original order, collects constraints, calls merger then solver, returns SortResult with unchanged flag. Per contracts/sorter-api.md.
- [x] T009 [P] Implement snapshot export/import in src/load_order_sorter/snapshot.py — `save_snapshot(name, plugins, path)` writes JSON, `load_snapshot(path)` reads and validates. Per data-model.md Snapshot entity.
- [x] T010 Wire public API re-exports in src/load_order_sorter/__init__.py — export sort_creations, SortResult, SortItem, SortedItem, SortConstraint, SortDecision, save_snapshot, load_snapshot.
- [x] T011 [P] Create tests in tests/test_load_order_sorter.py — test category sorter (SFBGS→tier1, Quests→tier3, unknown→default), LOOT sorter (parse sample YAML, load_after constraints), constraint merger (priority resolution, cycle breaking), solver (stable sort, topological ordering within tier), sort_creations end-to-end, snapshot round-trip.

**Checkpoint**: `load_order_sorter` package complete and tested. `sort_creations()` produces correct constraint-based sorted output. All sorter tests pass.

---

## Phase 3: User Story 1 — Manual Drag-and-Drop Reordering (Priority: P1) MVP

**Goal**: Load Order tab with drag-and-drop reordering, dirty state, Apply/Discard, and Starfield process detection.

**Independent Test**: Open Load Order tab, drag a creation, verify highlight. Click Apply, verify Plugins.txt updated. With Starfield running, verify Apply is disabled.

- [x] T012 [US1] Create Load Order tab module skeleton in src/starfield_tool/tools/load_order.py — register as a ToolModule with name "Load Order", implement initialize() with the creation list display (reuse existing Treeview pattern from creation_load_order.py).
- [x] T013 [US1] Register the Load Order tab in src/starfield_tool/tools/__init__.py alongside existing modules.
- [x] T014 [US1] Implement drag-and-drop reordering in src/starfield_tool/tools/load_order.py — bind Treeview mouse events for drag, update item positions on drop, track dirty state with a set of moved item IDs, highlight moved items with a "dirty" tag.
- [x] T015 [US1] Add Apply and Discard buttons in src/starfield_tool/tools/load_order.py toolbar — Apply writes new order to Plugins.txt (using the existing parsers module's path), Discard reverts to last-saved order. Both clear dirty state.
- [x] T016 [US1] Implement Starfield process detection in src/starfield_tool/tools/load_order.py — check if `Starfield.exe` is running (via `psutil` or `subprocess` with `tasklist`), disable Apply button while running, show tooltip message. Check on Apply click and on a timer.
- [x] T017 [US1] Add SFBGS position warning in src/starfield_tool/tools/load_order.py — when user drops an SFBGS-prefixed creation below a non-SFBGS creation, show a warning dialog.

**Checkpoint**: Load Order tab functional with manual reordering, dirty state, Apply/Discard, and game detection. This is the MVP.

---

## Phase 4: User Story 3 — Diff View for Proposed Changes (Priority: P1)

**Goal**: Conflict-resolution-style side-by-side diff view with per-creation Apply/Ignore controls and sorter attribution labels.

**Independent Test**: Generate a proposed order (hardcoded for now), open diff view, verify side-by-side display with movement arrows, per-item Apply/Ignore, Apply All, Done, Cancel.

- [x] T018 [US3] Create diff view dialog in src/starfield_tool/tools/load_order_diff.py — modal window with two side-by-side list panels (current left, proposed right), using Treeview or Frame-based layout.
- [x] T019 [US3] Implement movement indicators in src/starfield_tool/tools/load_order_diff.py — for each moved item, draw visual indicator (colored row + delta label like "+3" or "-2") and sorter attribution label ("LOOT", "CAT") near the item.
- [x] T020 [US3] Implement per-creation Apply/Ignore controls in src/starfield_tool/tools/load_order_diff.py — each moved item gets two buttons. Apply accepts the move, Ignore keeps current position. Update the right panel in real-time as user makes selections.
- [x] T021 [US3] Implement Apply All, Done, and Cancel buttons in src/starfield_tool/tools/load_order_diff.py — Apply All selects all moves, Done returns the final merged order to the caller, Cancel returns None.
- [x] T022 [US3] Wire diff view into load_order.py — add a helper method `_show_diff(current, proposed) -> list | None` that opens the diff dialog and returns the accepted order or None on cancel.

**Checkpoint**: Diff view fully functional as a reusable dialog. Can be opened with any two orders and returns user's selective choices.

---

## Phase 5: User Story 2 — Automated Sorting Pipeline (Priority: P2)

**Goal**: Auto Sort button triggers the sorter pipeline, results shown in the diff view.

**Independent Test**: Click Auto Sort with mixed creations, verify diff view opens with correct tier grouping, LOOT attribution where applicable, per-item controls work.

- [x] T023 [US2] Add Auto Sort button in src/starfield_tool/tools/load_order.py toolbar — clicking runs sort_creations() from the load_order_sorter package with current creation list, then opens the diff view with the result.
- [x] T024 [US2] Build SortItem list from current creations in src/starfield_tool/tools/load_order.py — map Creation objects to SortItem (plugin_name from files, content_id, display_name, categories from cached bethesda_creations info, original_index from current position).
- [x] T025 [US2] Add sorter settings panel in src/starfield_tool/tools/load_order.py — checkboxes for enabling/disabling category sorter and LOOT sorter. Store preferences in app config. Pass active sorter list to sort_creations().
- [x] T026 [US2] Handle LOOT masterlist availability in src/starfield_tool/tools/load_order.py — on first Auto Sort with LOOT enabled, fetch masterlist from GitHub raw URL if not already cached locally. Show progress in status bar. If unavailable, auto-disable LOOT sorter and proceed with category only.
- [x] T027 [US2] Wire sort result into diff view in src/starfield_tool/tools/load_order.py — convert SortResult items into the format expected by the diff dialog, including sorter attribution from SortedItem.decision. On Done, write accepted order to Plugins.txt.

**Checkpoint**: Full auto sort pipeline works: sorters → constraints → merge → solve → diff view → selective apply → write.

---

## Phase 6: User Story 4 — Snapshot Export and Import (Priority: P3)

**Goal**: Save/Load Snapshot buttons for backup and configuration switching.

**Independent Test**: Save current order as snapshot, rearrange, load snapshot, verify diff view shows the restore, apply, verify order restored.

- [x] T028 [US4] Add Save Snapshot button in src/starfield_tool/tools/load_order.py toolbar — opens file save dialog, calls save_snapshot() from load_order_sorter with current plugin list.
- [x] T029 [US4] Add Load Snapshot button in src/starfield_tool/tools/load_order.py toolbar — opens file open dialog, calls load_snapshot(), maps snapshot plugins to current creations (skip missing, append new at end), shows result in the diff view.
- [x] T030 [US4] Handle snapshot edge cases in src/starfield_tool/tools/load_order.py — show message listing skipped creations (in snapshot but not installed) and appended creations (installed but not in snapshot).

**Checkpoint**: Snapshot export/import fully functional with diff view preview.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T031 Run full test suite (`uv run pytest tests/ -v`) and fix any regressions
- [x] T032 Run linter (`uv run ruff check src/`) and fix any issues
- [x] T033 Verify Plugins.txt write is blocked when Starfield is running across all write paths (Apply, Done in diff, snapshot apply)
- [x] T034 Update README.md with Load Order tool description in the Tools section

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1
- **Phase 3 (US1 — MVP)**: Depends on Phase 2 for models only (drag-drop doesn't need sorters yet)
- **Phase 4 (US3 — Diff View)**: Depends on Phase 3 (needs the tab to exist)
- **Phase 5 (US2 — Auto Sort)**: Depends on Phase 2 (sorter pipeline) AND Phase 4 (diff view)
- **Phase 6 (US4 — Snapshots)**: Depends on Phase 4 (diff view for preview)
- **Phase 7 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on other stories
- **US3 (P1)**: Depends on US1 (tab must exist to host diff view)
- **US2 (P2)**: Depends on US3 (diff view) and Phase 2 (sorter pipeline)
- **US4 (P3)**: Depends on US3 (diff view for snapshot preview)

### Parallel Opportunities

- T003, T004, T005 can run in parallel (different files, no dependencies)
- T009 (snapshots) can run in parallel with T006-T008 (pipeline)
- T011 (tests) can run in parallel with T010 (init exports)
- Phase 6 (US4) can run in parallel with Phase 5 (US2) after Phase 4 is complete

---

## Implementation Strategy

### MVP First (Phase 1 + 2 + 3)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational — sorter package (T004-T011)
3. Complete Phase 3: US1 — manual reordering with dirty state (T012-T017)
4. **STOP and VALIDATE**: Drag-drop works, Apply/Discard work, game detection works

### Incremental Delivery

1. MVP (Phases 1-3) → Manual reordering works
2. Add US3 (Phase 4) → Diff view available
3. Add US2 (Phase 5) → Auto sort with diff review
4. Add US4 (Phase 6) → Snapshots
5. Polish (Phase 7) → Final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- The `load_order_sorter` package has zero dependencies on `starfield_tool` or `bethesda_creations`
- Starfield process detection (T016) may need `psutil` — evaluate if `tasklist` subprocess is simpler per constitution (Minimal Dependencies)
- Commit after each phase or logical group
