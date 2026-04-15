# Tasks: Remove Creation (Disable + Delete)

**Branch**: `013-remove-creation`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data model**: [data-model.md](./data-model.md) | **Contracts**: [contracts/removal_api.md](./contracts/removal_api.md)

**Tests**: Included — the project Constitution (principle II) makes tests non-negotiable, and the feature spec's acceptance scenarios and success criteria require them.

**Organization**: Phased by user story so each story is an independent, testable slice. P1 stories (US1, US2, US3) together form the MVP.

## Format

`- [ ] TaskID [P?] [Story?] Description with file path`

- `[P]` = parallelizable (distinct files, no blocking deps)
- `[USn]` = user story label (phase 3+ only)

## Path Conventions

Single project layout: `src/starfield_tool/`, `tests/` at repo root. Invoke tooling via `uv run ...`.

---

## Phase 1: Setup

**Purpose**: trivial preparation. No new infrastructure needed.

- [X] T001 Confirm branch `013-remove-creation` is current and `uv run pytest -x -q` is green on `dev` base; record baseline test count in the PR description later.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: shared code every user story depends on. Must be complete before Phase 3.

- [X] T002 Add `enable_dangerous_ops: bool = False` field to `AppSettings` in `src/starfield_tool/config.py`. Default MUST be False; field MUST round-trip through `load_config` / `save_config`. No migration needed (absent field → default).
- [X] T003 Create `src/starfield_tool/game_process.py` exposing `is_starfield_running() -> bool`, `is_launcher_running() -> bool`, `is_starfield_or_launcher_running() -> bool`. Reuse the `subprocess.run(["tasklist", "/FI", "IMAGENAME eq X", "/NH"], capture_output=True, text=True, timeout=5)` pattern currently inside `LoadOrderTool._is_starfield_running`. Launcher images to check: `BethesdaNetLauncher.exe`, `Starfield_BGS.exe`.
- [X] T004 Refactor `src/starfield_tool/tools/load_order.py` to delegate its running-game check to `game_process.is_starfield_running()` instead of the private `_is_starfield_running` method. Keep existing call sites unchanged in behaviour.
- [X] T005 [P] Add `tests/test_game_process.py` covering: all processes absent → False; Starfield.exe present → True for `is_starfield_running` and `is_starfield_or_launcher_running`; launcher present but Starfield absent → True for `is_launcher_running` and the combined probe, False for `is_starfield_running`; subprocess timeout → False (fail-safe). Inject a fake `subprocess.run` via `monkeypatch`.
- [X] T006 [P] Add / extend `tests/test_config.py` to assert a fresh `AppSettings()` has `enable_dangerous_ops is False`, a round-trip through JSON preserves `True` and `False`, and loading a JSON file missing the field yields `False`.

**Checkpoint**: foundational tests green. The existing Apply tool still works (manual smoke not required in CI; re-run full suite).

---

## Phase 3: User Story 1 — Remove a working, installed Creation (P1) 🎯 MVP core

**Story goal**: dangerous-ops ON + game closed + healthy Creation → click Remove → confirm → Plugins.txt line stripped, files deleted, list refreshed.

**Independent test**: per spec acceptance scenarios US1.1 and US1.2 (see quickstart.md walkthrough).

- [X] T007 [P] [US1] Create `src/starfield_tool/removal.py` with `RemovalPlan`, `FileOutcome`, `RemovalResult` dataclasses exactly matching data-model.md. No behaviour yet — dataclasses + enum-style string literals for `FileOutcome.status`.
- [X] T008 [US1] Implement `plan_removal(creation, plugins_txt, data_dir) -> RemovalPlan` in `src/starfield_tool/removal.py`: resolves each entry in `creation.plugin_files + [f for f in creation.plugin_files_all if non-plugin]` (use `Creation.plugin_files`, which already contains the full Files list) against `data_dir`. For each file, if `(data_dir / f).resolve()` is a descendant of `data_dir.resolve()`, add to `files_to_delete`; otherwise add the raw string to `out_of_tree_files`. `plugin_files` returned is the subset ending in `.esm`/`.esp`/`.esl`. Pure — no mutation, no reads of Plugins.txt beyond what data-model requires (none for planning).
- [X] T009 [US1] Implement `execute_removal(plan, plugins_txt, process_probe=is_starfield_or_launcher_running) -> RemovalResult` in `src/starfield_tool/removal.py`. Flow: probe first → if True, return `RemovalResult(game_was_running=True, ...)` and stop. Otherwise read Plugins.txt, drop any line whose stripped-`*`, case-insensitive filename matches any entry in `plan.plugin_files`; write back atomically (`plugins.txt.tmp` + `os.replace`) preserving the original newline style. Track dropped lines verbatim in `plugin_lines_dropped`. Then iterate `plan.files_to_delete` calling `os.remove`, capturing `FileNotFoundError → "already_gone"`, `OSError → "failed"` with `str(exc)` as reason, otherwise `"deleted"`. Return a fully populated `RemovalResult`. No exception escapes.
- [X] T010 [P] [US1] Create `tests/test_removal.py` with a `tmp_path`-based happy-path test: 2 files on disk, plugin line present in Plugins.txt, fake probe returns False → result has `plugins_txt_updated=True`, one line in `plugin_lines_dropped`, all outcomes `deleted`, files gone from disk, Plugins.txt rewritten without the line.
- [X] T011 [US1] Create `src/starfield_tool/dialogs/remove_creation.py` with two classes: `RemoveConfirmDialog(parent, plan, on_confirm: Callable[[], None])` and `RemoveResultDialog(parent, result)`. Both use the `load_order_diff.py` CTkToplevel recipe: `attributes("-topmost", True)` then `after(100, lambda: attributes("-topmost", False))`, `center_dialog(...)`, explicit Cancel/Close button, `protocol("WM_DELETE_WINDOW", ...)` routing to cancel (no-op) / close. No `transient()`, no `grab_set()`. Confirm dialog body lists `plan.plugin_files` and `plan.files_to_delete`; if `plan.out_of_tree_files` is non-empty, show a blocking error and disable the Confirm button.
- [X] T012 [US1] Modify `src/starfield_tool/dialogs/creation_details.py` to accept an optional `on_remove: Callable[[], None] | None = None` parameter and, when it is not None, construct a "Remove" button next to the Close button. When None, do NOT construct the button (absence, not `state="disabled"`).
- [X] T013 [US1] Wire the controller in `src/starfield_tool/tools/creation_load_order.py`: when opening `CreationDetailsDialog`, pass `on_remove=self._start_remove` only if `self._context.settings.enable_dangerous_ops` is True (read freshly each open). Implement `_start_remove(creation)` that (a) closes the details dialog, (b) calls `plan_removal(...)`, (c) opens `RemoveConfirmDialog` with an `on_confirm` callback that spawns a worker thread running `execute_removal(...)` and, on completion via `dlg.after(0, ...)`, opens `RemoveResultDialog` and calls `self._refresh()`. Use the existing `status_bar.set_task/clear_task` around the worker.
- [X] T014 [P] [US1] Add to `tests/test_removal.py`: esm-less creation (Files list has only `.ba2` entries) → `plan.plugin_files` is empty, `execute_removal` does not touch Plugins.txt, `plugins_txt_updated=False`, files are still deleted.
- [X] T015 [P] [US1] Add to `tests/test_removal.py`: multi-plugin creation (two `.esm` files listed) → both lines stripped from Plugins.txt, both file paths deleted.
- [X] T016 [P] [US1] Add to `tests/test_removal.py`: case-insensitive and `*`-prefix matching. Plugins.txt contains both `*Foo.esm` and `bar.esm`; creation lists `foo.esm` and `BAR.ESM` — both lines must be dropped.

**Checkpoint**: MVP core is demonstrable end-to-end with the game closed.

---

## Phase 4: User Story 2 — Abort removal (P1)

**Story goal**: Cancel leaves zero side effects. Win+D during confirm keeps dialog recoverable.

**Independent test**: per spec acceptance US2.1 and US2.2.

- [X] T017 [P] [US2] Add a test in `tests/test_removal.py` (or new `tests/test_removal_dialog.py` if tkinter is available in CI — otherwise keep logic-only): `execute_removal` is not invoked unless the caller calls it. I.e. `plan_removal(...)` alone mutates nothing (assert Plugins.txt and Data dir are byte-identical pre/post).
- [X] T018 [US2] In `src/starfield_tool/dialogs/remove_creation.py`, verify (by code review + manual smoke documented in the PR) that the Cancel button and `WM_DELETE_WINDOW` both destroy the dialog without calling `on_confirm`. Add an assertion-only test if a CI tkinter fake is already in use (check `tests/` for patterns first); otherwise document the manual verification in the dialog file's module docstring.

**Checkpoint**: Cancel path proven safe.

---

## Phase 5: User Story 3 — Refuse while game is running (P1)

**Story goal**: Starfield.exe or launcher running at Confirm time → op refused, nothing changed.

**Independent test**: per spec acceptance US3.1 and US3.2.

- [X] T019 [P] [US3] Add to `tests/test_removal.py`: inject `process_probe=lambda: True` → result has `game_was_running=True`, `plugins_txt_updated=False`, `file_outcomes == []`, and Plugins.txt and the tmp Data dir are byte-identical pre/post (verify with file hash).
- [X] T020 [US3] In `src/starfield_tool/dialogs/remove_creation.py::RemoveResultDialog`, render a distinct "game was running" message when `result.game_was_running is True`, directing the user to close Starfield / the launcher and retry.

**Checkpoint**: safety rule enforced and surfaced.

---

## Phase 6: User Story 4 — Partially-broken Creation recovery (P2)

**Story goal**: Creation whose files are partly already-gone and whose plugin is already absent from Plugins.txt is removable in one click.

**Independent test**: per spec acceptance US4.1 and US4.2.

- [X] T021 [P] [US4] Add to `tests/test_removal.py`: Files list names three files, only two exist on disk → result has two `deleted`, one `already_gone`; no exception raised.
- [X] T022 [P] [US4] Add to `tests/test_removal.py`: Plugins.txt does not contain the Creation's plugin line → `plugins_txt_updated=False` (no write occurred — verify file mtime unchanged), no error.

**Checkpoint**: recovery paths covered.

---

## Phase 7: User Story 5 — Per-file permission failure reporting (P2)

**Story goal**: One locked file does not abort the op; result names the failures.

**Independent test**: per spec acceptance US5.1 and US5.2.

- [X] T023 [P] [US5] Add to `tests/test_removal.py`: monkeypatch `os.remove` to raise `PermissionError("locked")` for one specific path in the plan — all other files still get deleted, Plugins.txt is still rewritten, `file_outcomes` for the locked path has `status="failed"` and `reason` contains "locked".
- [X] T024 [P] [US5] Add to `tests/test_removal.py`: monkeypatch `os.remove` to always raise `PermissionError` — all outcomes are `failed`, `plugins_txt_updated=True` (Plugins.txt was independently edited), result is surfaced without exception.
- [X] T025 [US5] Ensure `RemoveResultDialog` renders a grouped summary: deleted count, already-gone count, failed list with per-file reason text. Keep the dialog compact; if the failed list is long, make the inner container scrollable (reuse `CTkScrollableFrame` as in `creation_load_order.py`).

**Checkpoint**: partial-failure reporting fully exercised.

---

## Phase 8: Settings UI + polish

- [X] T026 Add the "Enable dangerous operations" checkbox in the existing Settings view (locate via grep for `beta_acknowledged` rendering — add the new checkbox next to it). Bind to `AppSettings.enable_dangerous_ops`; write-through on toggle via `save_config(...)`.
- [X] T027 [P] Full-project lint / test sweep: `uv run ruff check .` (report any new violations — do not fix pre-existing ones in this PR) and `uv run pytest -x -q` (all green).
- [ ] T028 [P] Manual smoke test checklist, documented in the PR description: (a) setting OFF → no Remove button anywhere, (b) setting ON → Remove button appears, (c) Cancel path leaves disk untouched, (d) Remove a healthy test Creation end-to-end with game closed, (e) launch Starfield → attempt Remove → refusal surfaced, (f) Win+D during confirm dialog → dialog recoverable.
- [ ] T029 Update `README.md` only if it currently documents the feature set at a level where adding Remove is warranted (grep for existing tool descriptions — if none exist, skip). Per project conventions, do not add standalone feature docs.

---

## Dependencies

- Phase 1 → Phase 2 → Phase 3.
- Phases 4, 5, 6, 7 each depend on Phase 3 (they add tests/UI polish to the MVP core).
- Phase 8 depends on all prior phases.

## Parallel Execution Examples

- After T007 lands, T010, T014, T015, T016 can be written in parallel (same file but logically independent; author sequentially if the same dev is writing them).
- T005 and T006 in Phase 2 are independent — can be written in parallel.
- T019, T021, T022, T023, T024 across P1/P2 phases all add tests to the same file; merge-order sequential, authoring parallel.
- T027 and T028 in Phase 8 are independent.

## Implementation Strategy

**MVP = Phases 1–3 + Phase 8 (minus US2/US3/US4/US5 polish).**
That delivers: a gated Remove button, working Remove for healthy Creations with the game closed, and the settings toggle. Ship it behind the setting and iterate on the safety / recovery polish (P1 US2/US3, P2 US4/US5) in the same PR because the Constitution's test-coverage principle requires them before merge.

Actual merge gate: all phases complete, `uv run pytest` green, manual smoke test checklist in T028 executed.

## Validation

- ✅ Every user story has at least one test task.
- ✅ Every FR in spec.md maps to at least one task (FR-001→T002+T026, FR-002/003/004/005→T011/T012/T013, FR-006→T011, FR-007→T009/T019, FR-008→T009/T015/T016, FR-009→T009, FR-010→T009/T023/T024, FR-011→T009/T021/T022, FR-012→T009/T025, FR-013→T013, FR-014→T009 (no ContentCatalog write), FR-015→T002/T009 (no admin), FR-016→T013 (single-creation entry point)).
- ✅ Every task has a checkbox, ID, optional [P], optional [USn], description, and file path.
- ✅ Constitution Check re-verified: tests present for every public interface (principle II), no new deps (III), clear function signatures (IV), no premature abstraction (I).
