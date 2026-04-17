# Tasks: Detect Broken Updates

**Branch**: `014-detect-broken-updates` (off 013 per user decision — 013 not yet merged)
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data model**: [data-model.md](./data-model.md) | **Contracts**: [contracts/detector_api.md](./contracts/detector_api.md)

**Tests**: Included — Constitution principle II is non-negotiable.

**Organization**: Phased by user story. The P1 stories (US1, US2, US3) together form the MVP.

## Format

`- [ ] TaskID [P?] [Story?] Description with file path`

## Path Conventions

`src/starfield_tool/`, `tests/`. All tooling via `uv run ...`.

---

## Phase 1: Setup

- [X] T001 Confirm `uv run pytest -x -q` is green on the 014 base (should show 368 passed inherited from 013). Record the baseline for the PR description.

---

## Phase 2: Foundational

**Purpose**: shared pure logic all user stories depend on.

- [X] T002 Create `src/starfield_tool/broken_scan.py` with `DetectionReason` (string literal type), `FlaggedCreation` dataclass, `BrokenDeletePlan` dataclass, `BrokenDeleteResult` dataclass exactly matching data-model.md. No behaviour yet.
- [X] T003 Implement `scan_broken(catalog_entries, plugin_entries, data_dir, now_fn=time.time, mtime_skew_threshold_s=60.0) -> list[FlaggedCreation]` in `src/starfield_tool/broken_scan.py`. Logic:
    - Build a case-insensitive set of Plugins.txt filenames (stripped `*` + lowercased).
    - For each catalog entry with non-empty `files`:
        - Resolve each file under `data_dir`; entries that escape the tree go into `files_missing` AND add reason `"out_of_tree"`.
        - For in-tree entries, classify into `files_present` / `files_missing` via `Path.exists()` (stat failure counts as missing).
        - Signal (a): both `files_present` and `files_missing` are non-empty → `"partial_files"`.
        - Signal (b): any plugin file (`.esm`/`.esp`/`.esl`) is in `files_present` but its filename is not in the plugins set → `"esm_without_plugins_line"`.
        - Signal (c): among `files_present`, compute `max(mtime) - min(mtime)`; if > threshold → `"mtime_skew"`. Skip if fewer than 2 present files.
    - Emit `FlaggedCreation` only when `reasons` is non-empty.
    - Sort result by `display_name.casefold()`.
- [X] T004 [P] Add `tests/test_broken_scan.py` with a `tmp_path` fixture helper `_layout(files, plugins_text, *, mtimes=None)` that builds `Data/`, Plugins.txt, and a catalog-entry-list stand-in for one or more Creations. Include at least these unit tests:
    - All files present + in plugins + close mtimes → empty list (healthy baseline).
    - Signal (a) only: half-present files → one entry with `["partial_files"]`.
    - Signal (b) only: all files present, plugins.txt empty → `["esm_without_plugins_line"]`.
    - Signal (c) only: two files, mtimes 120 s apart → `["mtime_skew"]`; mtimes 30 s apart → empty.
    - Signals a + b + c together → one entry with all three reasons, no dupes.
    - Esm-less Creation (Files = just a .ba2) with signal (c) → flagged by c only.
    - Out-of-tree: Files entry `"..\\evil.esm"` → `"out_of_tree"` in reasons; the escaping entry appears in `files_missing`; in-tree entries still classified normally.
    - Plugins.txt missing entirely → signal (b) fires for every esm-having Creation.
    - Catalog empty → empty result.
    - Sort order: two flagged creations with names "zebra" and "Apple" → result order `[Apple, zebra]` (casefold).
    - Deterministic threshold: pass `now_fn=lambda: 1_000_000` and explicit file mtimes so the test is wall-clock-independent.

**Checkpoint**: detector is pure, fully tested, ready to drive a UI.

---

## Phase 3: US1 — Find and clean a stranded partial-update (P1) 🎯 MVP

- [X] T005 [P] [US1] Create `src/starfield_tool/tools/broken_updates.py` with a `BrokenUpdatesTool(ToolModule)` class. `name = "Detect Broken Updates"`. `initialize(context)` builds a toolbar with a Scan button and a (disabled) Delete button, a Treeview with columns (# / Name / Author / Version / Date / Reason), an empty-state label, a status line. Follow the `CreationLoadOrderTool` layout conventions (same column widths + tag-configure for the flagged highlight: `tag_configure("flagged", background="#5a2a2a", foreground="#ffdddd")` — distinct from 013's "missing" grey).
- [X] T006 [US1] Wire the Scan button in `broken_updates.py`: read ContentCatalog + Plugins.txt from `context.game_installation`, call `scan_broken(...)`, populate the tree with one row per `FlaggedCreation`. Reason column renders `" + ".join(r.replace("_", " ") for r in creation.reasons)`. If the result is empty, hide the tree and show the empty-state label with text "No broken updates detected."
- [X] T007 [US1] Implement Delete flow in `broken_updates.py`: enable the Delete button when selection non-empty. On click, probe `is_starfield_or_launcher_running()`; if True, show an inline error and stop. Otherwise build per-Creation synthetic `Creation` objects and feed through `plan_removal(...)` into a `BrokenDeletePlan`, then open `BrokenConfirmDialog`.
- [X] T008 [US1] Register `BrokenUpdatesTool` in `src/starfield_tool/tools/__init__.py::MODULES` (append at end so it doesn't reshuffle existing tab order).
- [X] T009 [P] [US1] Create `src/starfield_tool/dialogs/broken_updates.py` with `BrokenConfirmDialog(parent, plan, on_confirm)`. Body: grouped list (one sub-section per flagged creation) showing files-to-delete and plugins.txt-lines-to-strip; a prominent yellow/orange warning banner "⚠ This operation does NOT perform a dependency check. If another Creation depends on one you delete, you are responsible for the fallout."; Cancel + Confirm buttons. Topmost-flash CTkToplevel pattern (no transient / no grab_set). `WM_DELETE_WINDOW` → destroy (cancel path).
- [X] T010 [US1] Add `BrokenResultDialog(parent, result)` to the same file. Renders (a) the alphabetical `CTkTextbox` of processed display names (selectable, copyable, `state="disabled"` after insert), (b) per-creation per-file outcome list. Distinct red banner when `result.game_was_running`.
- [X] T011 [US1] Wire the on-confirm callback in `broken_updates.py`: in a worker thread iterate `plan.removal_plans` calling `execute_removal(p, plugins_txt, process_probe=lambda: False)`; collect into `BrokenDeleteResult`; on main thread open `BrokenResultDialog` and re-run Scan automatically.
- [X] T012 [P] [US1] Add to `tests/test_broken_scan.py` a `build_removal_plans_from_flagged` round-trip test: given a flagged creation with two in-tree files, confirm the synthetic `Creation` + `plan_removal(...)` yields a `RemovalPlan` whose `files_to_delete` match the flagged `files_present ∪ files_missing` (in-tree subset) and whose `plugin_files` are the esm-like subset.

---

## Phase 4: US2 — Refuse while game is running (P1)

- [X] T013 [P] [US2] Add to `tests/test_broken_scan.py` an integration-style test (or new `tests/test_broken_delete_flow.py` if it'll exceed ~150 lines): inject a fake `process_probe=lambda: True` into a helper that drives the same execute loop used by the tab; assert `BrokenDeleteResult.game_was_running is True`, zero mutations on the tmp Data dir and Plugins.txt (verify via file hash), `results == []`.
- [X] T014 [US2] Surface the refusal in the UI: when the pre-flight check fails, show it via `BrokenResultDialog` (with the red banner) — not via inline status text — so the safety message has equal weight to a completed op. (Matches feature 013's behaviour.)

---

## Phase 5: US3 — Dependency-ignorant confirmation (P1)

- [X] T015 [P] [US3] Add to the test suite: helper that constructs a `BrokenDeletePlan` from two flagged creations and asserts the aggregated files-to-delete across them matches the union of per-creation plans. (Logic lives in the tab's build step; add a small extractable function `build_delete_plan(flagged_list, plugins_txt, data_dir) -> BrokenDeletePlan` in `broken_scan.py` to make it testable.)
- [X] T016 [US3] In `dialogs/broken_updates.py::BrokenConfirmDialog._build_ui`, ensure the "no dependency check" warning is rendered in a visually-distinct frame (orange/yellow fg, bold font) ABOVE the file list so the user can't miss it. Smoke-test via code review — no tk-in-CI test needed.
- [X] T017 [US3] Verify (code review item in the PR description) that Cancel and `WM_DELETE_WINDOW` both route to a no-op close. Test coverage is satisfied by T013's "no mutations" hash-check when `on_confirm` is never called.

---

## Phase 6: US4 — Offline scan (P2)

- [X] T018 [P] [US4] Add to `tests/test_broken_scan.py`: `scan_broken` must not import or call anything under `starfield_tool.creations` or `bethesda_creations.*`. Verify via a module-level assertion — grep the `broken_scan.py` file content in the test for banned imports (cheap belt-and-suspenders check that also guards future regressions).

---

## Phase 7: US5 — Empty result (P2)

- [X] T019 [P] [US5] Add to `tests/test_broken_scan.py`: scan on a fully-healthy fixture returns `[]`. Combined with T006's UI behaviour, satisfies SC-007.

---

## Phase 8: Polish

- [X] T020 Full lint + test sweep: `uv run ruff check .` on every file touched by this feature (not the whole repo — we don't fix pre-existing lint in this PR); `uv run pytest -x -q` green.
- [ ] T021 [P] Manual smoke test checklist in PR description: (a) fresh install, no broken → Scan shows empty-state, Delete disabled; (b) deliberately delete one `.ba2` out of a two-file Creation → Scan flags it with "partial files"; (c) launch Starfield → select + Delete → refusal via result dialog; (d) multi-select two flagged → Confirm dialog shows grouped file list + dependency warning; (e) Cancel leaves state untouched; (f) Confirm + clean removal → result dialog lists names alphabetically, tree refreshes to empty.
- [ ] T022 Update any user-facing docs only if explicitly present in the repo (no standalone docs added — per project convention).

---

## Dependencies

Phase 1 → Phase 2 → Phase 3. Phases 4–7 ride on Phase 3 (they add tests/UI polish to the MVP). Phase 8 last.

## Parallel Execution Examples

- T005 and T009 (different files) can be authored in parallel after T002/T003 land.
- T012, T013, T015, T018, T019 all land in the same test file but are independent tests → author in parallel, commit in any order.
- T021 and T022 in Phase 8 are independent.

## Implementation Strategy

**MVP = Phases 1–3 + Phase 4 + Phase 5.** All P1 stories + the game-running and dependency-warning guardrails. US4 and US5 are polish tests that harden correctness but don't change what the feature does; they can land in the same PR or a fast follow-up. Merge gate: all tests green, manual smoke checklist run, and one clean broken-creation recovered end-to-end through the UI.

## Validation

- ✅ Every user story has ≥1 test task.
- ✅ Every FR maps: FR-001→T005+T008, FR-002→T006, FR-003→T003+T004, FR-004→T006, FR-005→T005+T006, FR-006→T003+T004, FR-007→T007, FR-008→T007+T013, FR-009→T009, FR-010→T009+T016, FR-011→T009, FR-012→T009+T010, FR-013→T011+T012+T015, FR-014→(inherited from 013, covered in its tests), FR-015→(inherited from 013), FR-016→T010, FR-017→T018, FR-018→(by omission — no settings gate wired in T007), FR-019→(by omission — T011 does not touch ContentCatalog.txt; 013 already doesn't), FR-020→T006+T019.
- ✅ Every task has checkbox + ID + optional [P] + (for phase 3+) [USn] + description + file path.
- ✅ Constitution re-verified post-task-decomposition: pure detector, no new deps, reuse of 013, explicit interfaces.
