---
description: "Task list for 010-diff-connectors: visual connectors and hint dialog in the load order diff dialog"
---

# Tasks: Diff Dialog Visual Connectors and Hint Dialog

**Input**: Design documents from `/specs/010-diff-connectors/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: YES — this feature introduces new data behavior (`all_constraints` preservation, `sorter_name` filename qualification, `note` propagation). Constitution II (Test Coverage) is non-negotiable for functional behavior. UI-only behavior (Canvas drawing, dialog rendering) is verified manually per project precedent and is not covered by automated tests.

**Organization**: Tasks are grouped by user story (P1 stories first, then P2). Foundational data-model changes precede all user stories because both US1 and US2 depend on them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 per spec.md

## Path Conventions

Single-project layout. `src/` and `tests/` at repo root. All paths are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: None — no setup required. All changes are in existing files.

*(No tasks in this phase.)*

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data-model changes required by BOTH user stories. Must complete before any US work.

- [X] T001 Add `note: str = ""` field to `SortConstraint` dataclass in `src/load_order_sorter/models.py`
- [X] T002 Add `all_constraints: list[SortConstraint] = field(default_factory=list)` to `SortDecision` dataclass in `src/load_order_sorter/models.py`
- [X] T003 In `_merge_constraints` of `src/load_order_sorter/pipeline.py`, populate `decision.all_constraints = list(plugin_constraints)` before storing the decision (around line 122)
- [X] T004 In `src/load_order_sorter/sorters/rulebook.py`, change `sorter_name` to `f"RULE:{entry['filename']}"` for order constraints and `f"RULE:{entry['filename']}({tier})"` for tier constraints. Pass `note=rule.get("note", "")` into every `SortConstraint(...)` constructor call in the sort function.
- [X] T005 [P] Add test in `tests/test_load_order_sorter.py` verifying `SortDecision.all_constraints` contains every `SortConstraint` (winners and losers) for a plugin constrained by multiple sorters of different priorities
- [X] T006 [P] Add tests in `tests/test_rulebook_sorter.py` verifying (a) order-book `sorter_name` is `RULE:<filename>` format, (b) tier-book `sorter_name` is `RULE:<filename>(<tier>)` format, (c) `SortConstraint.note` matches the rule's `note` field for both branches
- [X] T007 Run full test suite and ruff to confirm foundational changes are green: `.venv/Scripts/python.exe -m pytest tests/ -x -q && .venv/Scripts/python.exe -m ruff check .`

**Checkpoint**: Foundational data-model changes in place. Existing 305 tests still pass; new tests added for the three new behaviors.

---

## Phase 3: User Story 1 — Visual connectors (Priority: P1)

**Goal**: Draw colored Bezier curves with endpoint dots between moved items on a new Canvas in the gap between the two treeviews. Both panels scroll in lockstep.

**Independent Test**: Open the diff dialog with at least 2 moves that cross each other (see quickstart.md §2). Verify: two distinct-colored curves, small colored dots at both endpoints, both panels scroll together, connectors redraw on scroll/resize/collapse-toggle.

- [X] T008 [US1] In `src/starfield_tool/tools/load_order_diff.py`, define module-level constant `_MOVE_COLORS = ["#4a9eff", "#48c774", "#f39c12", "#e55353", "#9c6ad6", "#1abc9c"]`
- [X] T009 [US1] In `DiffDialog.__init__`, compute `self._move_colors: dict[str, str]` by iterating `self._moved_names` in proposed-order sequence (use `self._proposed` order) and assigning `_MOVE_COLORS[i % len(_MOVE_COLORS)]`
- [X] T010 [US1] In `DiffDialog._build_ui`, replace the left/right `pack`-based layout of the `pane` frame with a `grid` layout: col 0 = left_frame (weight=1, sticky="nsew"), col 1 = new `tk.Canvas` stored as `self._connector_canvas` with `width=80, highlightthickness=0, bg=<tree bg>`, sticky="ns", no weight; col 2 = right_frame (weight=1, sticky="nsew")
- [X] T011 [US1] Add shared vertical `ttk.Scrollbar` next to the right tree. Replace the trees' independent scrollbars with this single shared scrollbar. Wire `Treeview.yscrollcommand` on both trees to a wrapper function that updates the scrollbar AND calls `_redraw_connectors()`. Set the scrollbar's `command` to a wrapper that calls `yview_moveto` on both trees. Result: scrolling either tree moves the other in lockstep.
- [X] T012 [US1] Implement `DiffDialog._redraw_connectors(self)`: clear tag `"connector"` on canvas; build a `name → iid` map for both trees (cache in `self._left_iid_by_name` and `self._right_iid_by_name`, rebuilt in `_populate()`); for each `name in self._moved_names`, look up both iids, get `bbox()` on each, skip if either is `()`. Compute canvas-relative Y using root-based coordinates. Draw left dot `create_oval`, right dot, and Bezier via `create_line(..., smooth=True, splinesteps=24)` with control points at 1/3 and 2/3 width.
- [X] T013 [US1] In `DiffDialog._populate()`, at the end (after trees are populated), cache the `name → iid` maps and call `self._redraw_connectors()` via `self.after(10, self._redraw_connectors)` so bbox queries run after geometry is realized
- [X] T014 [US1] Bind `<Configure>` on the connector canvas to trigger `_redraw_connectors()` (handles window resize and initial layout)
- [X] T015 [US1] Collapse-toggle redraw is handled: `_toggle_collapse()` calls `_populate()` which schedules `_redraw_connectors()` via `after(10, ...)`.
- [X] T016 [US1] Accept-toggle redraw is handled: `_on_right_click()` and `_apply_all()` both call `_populate()` which schedules the redraw.

**Checkpoint**: US1 complete. Canvas is visible, connectors are drawn, scroll/resize/collapse/accept all redraw correctly.

---

## Phase 4: User Story 2 — Hint icon and hints dialog (Priority: P1)

**Goal**: Every moved row in the right panel has a colored ⓘ icon in its Info column. Clicking the icon opens a dialog listing every constraint that shaped the move, with winner badges and rulebook filename attribution.

**Independent Test**: Click the ⓘ icon on a moved row with at least two tier constraints (one CAT, one RULE). Verify the dialog shows both, with the winner badge only on the higher-priority one. Row click elsewhere still toggles accept/reject.

- [X] T017 [US2] In `DiffDialog._insert_moved_right()` in `src/starfield_tool/tools/load_order_diff.py`, prepend `"\u24d8 "` (circled ⓘ) to the `info` string for moved rows. Configure a per-plugin tree tag with `foreground=self._move_colors[plugin_name]` via `self._right_tree.tag_configure(...)` and add the tag to the inserted row. Same for left side dots via `_insert_moved_left`.
- [X] T018 [US2] In `DiffDialog._on_right_click()`, use `self._right_tree.identify_column(event.x)`. If the click lands on column `"#3"` (Info) AND the row maps to a moved plugin, call `self._show_hint_dialog(plugin_name)` and return. Otherwise continue with the existing accept/reject toggle behavior.
- [X] T019 [US2] Implement `DiffDialog._show_hint_dialog(self, plugin_name: str)` as a new method: create a `ctk.CTkToplevel`, title `f"Hints for {display_name}"`, center via `center_dialog`.
- [X] T020 [US2] Build hint dialog header: `tk.Frame` color swatch, bold display name, secondary label "tier {decision.tier}  ·  was #{orig+1} → #{new+1}".
- [X] T021 [US2] Body is a `CTkScrollableFrame`. Constraints sorted by `-priority, sorter_name`. Each row shows sorter name (monospaced Consolas), type+value, priority, and WINNER badge when applicable (tier winner OR attributed edge winner).
- [X] T022 [US2] Greyed note label appears below the row only when `c.note` is non-empty.
- [X] T023 [US2] Close button at the bottom calls `dlg.destroy()`.

**Checkpoint**: US2 complete. Hint icons visible and colored per move; clicking them opens a functional hint dialog with correct winner badges.

---

## Phase 5: User Story 3 — Per-move color coding parity (Priority: P2)

**Goal**: The color assigned to a move is identical across: the connector line, both endpoint dots, the ⓘ icon in the Info column, and the color swatch in the hints dialog header.

**Independent Test**: With 3+ moves, trace each connector and verify the 4 elements (line, two dots, icon) share exactly the same hex color. Note that `_move_colors` is the single source of truth consumed by both the canvas drawing (T012) and the ttk tag (T017) and the hint dialog header swatch (T020).

No additional implementation tasks — US3 is satisfied by consistent use of `self._move_colors[plugin_name]` in T012, T017, and T020. Verification task follows.

- [X] T024 [US3] Color parity is guaranteed by shared lookup `self._move_colors[plugin_name]` used by canvas drawing (T012), ttk tag on both trees (T017 for left and right), and the hint dialog swatch (T020). Manual verification to be confirmed by the user on first run.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T025 [P] Updated `src/starfield_tool/tools/load_order_diff.py` module docstring to describe the connector/hint features (done in T008).
- [X] T026 [P] Full test suite and ruff: 309 tests pass, `src/` lint-clean. Remaining lint errors in `bin/dev.py` and `tests/test_app.py` are pre-existing, unrelated to this feature.
- [ ] T027 Manual walkthrough per `specs/010-diff-connectors/quickstart.md` §2–§8 — **awaiting user verification** with live Falkland/PDY load order.

---

## Dependencies

- **Phase 2 (T001–T007)** blocks Phase 3 and Phase 4 (both user stories need `all_constraints`, `note`, and filename-qualified `sorter_name`).
- **Phase 3 (T008–T016)** is independent of Phase 4 at the code level but shares `_move_colors` (T009) with Phase 4. T009 is a prerequisite for both T012 and T017.
- **Phase 4 (T017–T023)** depends on T009 (for color map) and T008 (for palette constant).
- **Phase 5 (T024)** depends on T012, T017, T020 being complete.
- **Phase 6 (T025–T027)** depends on all prior phases.

## Parallel Opportunities

- **T005 and T006** can run in parallel — different test files.
- **T017 and T019–T023** can run in parallel with **T010–T016** once T008–T009 are done — they touch different regions of the same file but the changes are additive; one developer could serialize them without conflict in practice.
- **T025 and T026** can run in parallel — different targets.

## Independent Test Criteria per Story

- **US1**: Visual + interaction test. Two crossing moves show two distinct colored curves. Scrolling either tree scrolls both and redraws cleanly. Resize redraws. Collapse-toggle redraws. Accept-toggle redraws.
- **US2**: Interaction test. Hint icon on a moved row (not elsewhere) opens a dialog listing all constraints with correct winner badges. Row-body click still toggles accept. Rulebook-sourced hints show `RULE:<filename>` and the rule's `note`.
- **US3**: Visual parity test. The four color-bearing elements per move share the same hex.

## MVP Scope

**Minimum**: Phase 2 (T001–T007) + Phase 3 (T008–T016). Delivers visual connectors with lockstep scrolling — the headline win. Users see the "what moved" instantly. Hint dialog (US2) can follow in a second increment and remains valuable on its own.

**Recommended for single delivery**: All phases. The value compounds — connectors tell you *what*, hints tell you *why*. Delivering both together matches the originating user request ("that's awesome, and please also show why").

## Total Task Count

27 tasks across 6 phases. Task distribution: Foundational 7, US1 9, US2 7, US3 1, Polish 3, Setup 0.
