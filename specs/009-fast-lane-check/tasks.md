# Tasks: Fast Lane Creation Check

**Input**: Design documents from `/specs/009-fast-lane-check/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included (constitution principle II: Test Coverage is NON-NEGOTIABLE).

**Organization**: Three user stories. US1 (Import Installed + Check) is the core MVP. US2 (Import from File) extends with file loading. US3 (baseline metadata visibility) folds naturally into US1's warning banner implementation and is captured within US1 tasks.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: Verify existing infrastructure and prepare the data directory.

- [x] T001 Verify existing dependencies are in place: `compare_versions` in src/bethesda_creations/_version_cmp.py, `build_creation_list` in src/starfield_tool/parsers.py, `get_cached_info_any` in src/starfield_tool/creations.py, `ToolModule`/`ModuleContext` in src/starfield_tool/base.py, and `MODULES` list in src/starfield_tool/tools/__init__.py
- [x] T002 Create `data/` directory at project root if it does not exist (will hold the bundled baseline file)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Export format update and baseline file — both required before either user story can function. The export update feeds US2's import path; the baseline feeds both US1 and US2's Check action.

**⚠️ CRITICAL**: Both user stories depend on the baseline file existing and the export carrying Content ID.

### Export Format Update (FR-020)

- [x] T003 Update export format in src/starfield_tool/tools/creation_load_order.py `_export()` method — add `Content ID` as the second column (after `#`), rename `Version` header to `Installed Version`, update the rows tuple to include `c.content_id` in position 1. Preserve the Markdown table format parity with CSV (same column set, same order).
- [x] T004 [P] Update or add tests in tests/test_creation_load_order.py (or create a focused test file) — verify the export now includes `Content ID` column, verify column header renamed to `Installed Version`, verify CSV and Markdown formats stay in sync.

### Baseline Generator and File

- [x] T005 Implement baseline generator at src/starfield_tool/tools/fast_lane_baseline_generator.py — CLI script with argparse supporting `--output PATH` (default: `data/creations_baseline.json` relative to project root) and `--catalogue PATH` (default: `%APPDATA%/StarfieldToolkit/creations_catalogue.json`). Loads the full catalogue, extracts `title`, `author`, and latest `version` per entry (via `release_notes` max ctime across all platforms), writes trimmed JSON with schema `{"version": 1, "snapshot_date": "<ISO UTC>", "entries": {<content_id>: {title, author, version}}}`. Fall back to "unknown" if no release_notes exist for an entry.
- [x] T006 [P] Tests for baseline generator in tests/test_fast_lane_baseline_generator.py — test with a mocked full catalogue containing entries with release_notes, verify trimmed schema, verify version extraction picks the latest ctime across platforms, verify missing release_notes get "unknown", verify snapshot_date is a valid ISO timestamp, verify JSON file is valid on disk.
- [x] T007 Run the baseline generator against the real catalogue to produce `data/creations_baseline.json` — commit the file to the repo as a bundled asset. Verify file size is under 500 KB (target ~200 KB).

**Checkpoint**: Export format updated, baseline generator tested, baseline file committed. Both user stories can now proceed.

---

## Phase 3: User Story 1 - Import Installed + Check (Priority: P1) 🎯 MVP

**Goal**: Full two-phase UI for the installed-creations flow — empty state with warning + "Import Installed" button; loaded state with grid + Reset/Check buttons; Check action compares against baseline using the existing creations cache.

**Independent Test**: Open the app, navigate to the Fast Lane Creation Check tab, click "Import Installed", verify the grid populates with installed creations, click "Check", verify the grid updates with baseline/current versions and status column with highlighted "not updated" rows.

### Baseline Loader

- [x] T008 [US1] Implement baseline file loader at src/starfield_tool/tools/fast_lane_check.py — top-of-file helper `_load_baseline() -> dict | None` that finds the baseline file (check `sys._MEIPASS/data/creations_baseline.json` first, then project root `data/creations_baseline.json` for dev mode). Parse JSON, validate schema version == 1, return the dict or None on any error.

### Tool Module Skeleton + Empty State (FR-001, FR-002, FR-003, FR-018)

- [x] T009 [US1] Create FastLaneCheckTool class in src/starfield_tool/tools/fast_lane_check.py — ToolModule subclass with `name = "Fast Lane Creation Check"`, `description = "Check which installed creations have not been updated since a pre-Fast-Lanes baseline"`. Stub `initialize(context)` method, instance state: `_context`, `_baseline`, `_rows` (loaded data), `_checked` (bool), `_empty_frame`, `_loaded_frame`, `_tree` (treeview), `_warning_label`, `_status_label`.
- [x] T010 [US1] Implement warning banner in src/starfield_tool/tools/fast_lane_check.py — persistent label at the top of the tab content area, yellow/orange background (Constellation warning color). Text includes: approximate check disclaimer, detection method summary, baseline snapshot date (from loaded baseline), recommendation to run "Check for Updates" in Installed Creations tab first. Visible in both empty and loaded states. (FR-002, FR-018)
- [x] T011 [US1] Implement empty state layout in src/starfield_tool/tools/fast_lane_check.py — below warning banner, centered frame with two large CTkButtons: "Import Installed" and "Import from File". Both buttons styled consistently (Constellation blue). Populated during `initialize()`. (FR-003)
- [x] T012 [US1] Register FastLaneCheckTool in src/starfield_tool/tools/__init__.py — import the class, add to MODULES list after RuleBookTool.

### Loaded State UI (FR-006, FR-007)

- [x] T013 [US1] Implement loaded state layout in src/starfield_tool/tools/fast_lane_check.py — a frame with: top button bar containing "Reset" and "Check" buttons + summary label; below it a ttk.Treeview with columns `#`, `Title`, `Author`, `Installed Version`, `Baseline Version`, `Status`. Configure tree tags: `not_updated` (yellow background), `unknown` (gray text). Initially hidden until data loads. (FR-006)
- [x] T014 [US1] Implement state transition helpers in src/starfield_tool/tools/fast_lane_check.py — `_show_empty_state()` hides loaded frame, shows empty frame; `_show_loaded_state()` hides empty frame, shows loaded frame, populates tree from `_rows`. Called by Import buttons and Reset button.
- [x] T015 [US1] Implement Reset button handler in src/starfield_tool/tools/fast_lane_check.py — clears `_rows`, `_checked`, and any loaded data, then calls `_show_empty_state()`. (FR-007)

### Import Installed Flow (FR-004)

- [x] T016 [US1] Implement `_import_installed()` handler in src/starfield_tool/tools/fast_lane_check.py — uses `build_creation_list(self._context.game_installation)` from starfield_tool.parsers to get the installed creations, maps each to the `_rows` structure with fields `{content_id, title, author, installed_version, baseline_version: None, current_version: None, status: None}`, then calls `_show_loaded_state()`. Handles errors (no game installation) with a user-visible message. (FR-004)

### Check Action and Comparison Logic (FR-008, FR-010, FR-011, FR-012, FR-013, FR-015, FR-016, FR-019)

- [x] T017 [US1] Implement baseline lookup in src/starfield_tool/tools/fast_lane_check.py — function `_lookup_baseline(row, baseline_entries) -> dict | None` that matches by content_id first, falls back to `(title.lower(), author.lower())` tuple match across baseline entries if content_id is not found (needed for file-imported rows without content_id).
- [x] T018 [US1] Implement comparison logic in src/starfield_tool/tools/fast_lane_check.py — function `_classify(current: str, baseline: str) -> str` returning "updated" / "not_updated" / "unknown". Uses `compare_versions` from `bethesda_creations._version_cmp`. Handles missing/empty versions as "unknown". (FR-012, FR-016)
- [x] T019 [US1] Implement `_check()` button handler in src/starfield_tool/tools/fast_lane_check.py — for each row in `_rows`: look up baseline entry, determine current version per input mode (installed: use `get_cached_info_any()` lookup by content_id → `info.version`; file mode: use `installed_version` from the row), call `_classify`, store result. After all rows processed, sort by status (not_updated first, then unknown, then updated), re-populate tree with baseline and current version columns and status tag. Update summary label with counts. Set `self._checked = True`. (FR-008, FR-010, FR-011, FR-015, FR-019)
- [x] T020 [US1] Apply highlighting in the treeview re-population code — rows with status="not_updated" get the `not_updated` tag (yellow background); rows with status="unknown" get the `unknown` tag (gray text); "updated" rows use no tag. (FR-013)

### Tests for US1

- [x] T021 [P] [US1] Write tests in tests/test_fast_lane_check.py covering: `_load_baseline` with valid file, missing file, corrupted JSON, wrong schema version; `_lookup_baseline` with content_id match, title+author fallback, no match; `_classify` for updated/not_updated/unknown cases including empty strings and non-semantic versions ("1.0a" vs "1.0.1"); a full check flow with mock rows + mock baseline + mock cache producing expected classifications.

**Checkpoint**: User Story 1 complete — users can open the tab, click Import Installed, click Check, and see highlighted "not updated" creations.

---

## Phase 4: User Story 2 - Import from File (Priority: P2)

**Goal**: File-based input flow — user clicks "Import from File", picks a CSV or Markdown export, parser populates the grid (supporting both new-format with Content ID and legacy exports).

**Independent Test**: Export a creations list from the Installed Creations tab (new format with Content ID), click "Import from File" in Fast Lane Check, select the file, verify grid populates; click "Check", verify comparison runs using exported `Installed Version` as the current-version source.

### Import Parsers (FR-005, FR-021)

- [x] T022 [US2] Implement CSV parser in src/starfield_tool/tools/fast_lane_check.py — function `_parse_csv(filepath) -> tuple[list[dict], bool]` returning `(rows, is_legacy)`. Use stdlib `csv.DictReader`. Detect header shape: if `Content ID` column present, new format; otherwise legacy. For each row produce `{content_id, title, author, installed_version, baseline_version: None, current_version: None, status: None}`. For legacy rows set `content_id = ""` (triggers title+author fallback during lookup).
- [x] T023 [US2] Implement Markdown table parser in src/starfield_tool/tools/fast_lane_check.py — function `_parse_markdown(filepath) -> tuple[list[dict], bool]`. Split on `|`, strip whitespace, skip the separator row (`---`). Same detection logic as CSV (Content ID header or not), same row structure.
- [x] T024 [US2] Implement format auto-detection in src/starfield_tool/tools/fast_lane_check.py — function `_parse_export(filepath) -> tuple[list[dict], bool]` that reads the first line and delegates to `_parse_csv` or `_parse_markdown` based on whether the header starts with `#,` (CSV) or `| #` (Markdown).

### File Picker and Handler (FR-005)

- [x] T025 [US2] Implement `_import_from_file()` handler in src/starfield_tool/tools/fast_lane_check.py — opens a tkinter file dialog (`filedialog.askopenfilename`) filtering for `.csv` and `.txt`. On selection, calls `_parse_export`, stores returned rows in `_rows`, calls `_show_loaded_state()`. On parse error, shows a messagebox with the error and stays in empty state. If `is_legacy=True`, shows a warning messagebox: "Legacy export detected — matching will use Name + Author as fallback. For best results, re-export from the Installed Creations tab." (FR-021)

### File-Mode Check Behavior (FR-011)

- [x] T026 [US2] Update `_check()` handler in src/starfield_tool/tools/fast_lane_check.py to branch on input mode — detect file mode by whether the rows came from an import file (add `_source_mode` instance state: "installed" or "file"). In file mode, use the row's own `installed_version` as the current version (do NOT call `get_cached_info_any()`, since the file represents someone else's install). All other comparison logic identical to installed mode. (FR-011)

### Tests for US2

- [x] T027 [P] [US2] Write tests in tests/test_fast_lane_check.py covering: `_parse_csv` with new-format file, `_parse_csv` with legacy file (no Content ID column), `_parse_csv` with malformed file (bad headers); `_parse_markdown` with new and legacy formats; format auto-detection via `_parse_export`; file-mode check flow using exported installed_version as current; legacy-format warning message triggered when loading legacy CSV.

**Checkpoint**: User Story 2 complete — users can load a CSV/Markdown export from either the current format or a legacy format.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Build integration, final validation, cleanup.

- [x] T028 Update bin/build.sh to bundle the baseline file — add `BASELINE_DATA_FLAG=""` variable, check if `data/creations_baseline.json` exists, set `BASELINE_DATA_FLAG="--add-data ${PROJECT_ROOT}/data/creations_baseline.json${PATHSEP}data"` if present, include `$BASELINE_DATA_FLAG` in the pyinstaller args alongside `$LOOT_DATA_FLAG` and `$RULES_DATA_FLAG`.
- [x] T029 Run full project lint (`ruff check .`) and fix any issues
- [x] T030 Run full test suite (`pytest`) and verify all pass — including the new fast_lane tests and the updated creation_load_order export tests
- [x] T031 Manual validation: open the app, verify the new "Fast Lane Creation Check" tab appears after RuleBookTool. Test full US1 flow (Import Installed → Check → Reset). Test full US2 flow (Export from Installed Creations → Import from File → Check). Verify warning banner is visible in both states and shows the baseline snapshot date.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup
  - Export update (T003, T004) is independent of baseline (T005, T006, T007)
  - T003 and T005 can run in parallel
  - T007 (generate actual baseline file) blocks both user stories
- **US1 (Phase 3)**: Depends on Foundational (needs baseline file)
  - T008 → T009, T010, T011, T012 can follow sequentially (all in fast_lane_check.py)
  - T013-T015 depend on T009
  - T016 depends on T014 (needs `_show_loaded_state`)
  - T017, T018 are pure helpers, can be written alongside T019
  - T019 depends on T017, T018, T014
  - T020 depends on T019
  - T021 (tests) after T020
- **US2 (Phase 4)**: Depends on US1 (needs loaded state, `_check()`, `_show_loaded_state()`)
  - T022, T023, T024 are pure parser functions, can be developed in parallel
  - T025 depends on T022/T023/T024 and T014
  - T026 depends on T019 (updating existing `_check`)
  - T027 (tests) after T026
- **Polish (Phase 5)**: Depends on all prior phases

### Within Phase 2 (Foundational)

```
T003 (export update) ──┐
                       ├── T004 (export tests) [P]
                       │
T005 (generator)    ───┤
                       ├── T006 (generator tests) [P]
                       │
                       └── T007 (run generator -> baseline file)
```

### Within Phase 3 (User Story 1)

```
T008 (baseline loader)
  → T009 (tool skeleton)
    → T010 (warning banner)
    → T011 (empty state)
    → T012 (register in MODULES)
      → T013 (loaded state UI)
        → T014 (state transitions)
          → T015 (reset) + T016 (import installed)
            → T017 (lookup) + T018 (classify) [parallel]
              → T019 (check action)
                → T020 (highlighting)
                  → T021 (tests) [P]
```

### Within Phase 4 (User Story 2)

```
T022, T023, T024 (parsers) ─── all parallel [P]
  → T025 (file picker handler)
  → T026 (file-mode check branching)
    → T027 (tests) [P]
```

### Parallel Opportunities

- **Phase 2**: T003 and T005 on different files, T004 and T006 as tests alongside
- **Phase 3**: Helper functions T017 and T018 can be written in parallel while working on T019
- **Phase 4**: All three parser functions (T022, T023, T024) can be developed in parallel before wiring them together in T025

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Verify setup
2. Complete Phase 2: Export update + baseline file + generator + tests
3. Complete Phase 3: Full Import Installed + Check flow with UI
4. **STOP and VALIDATE**: Open the app, click Import Installed → Check, confirm classification and highlighting work
5. Continue to US2 for file-based input

### Incremental Delivery

Since this is a developer tool with short-lived relevance, delivery is quick and linear:
1. Foundation → baseline file committed, export format updated
2. US1 MVP → Import Installed + Check works end-to-end for the primary use case
3. US2 extension → Import from File supports helping friends / checking exports
4. Polish → bundle via build.sh, lint, full test suite, manual validation

---

## Notes

- [P] tasks = different files or independent functions, no dependencies on incomplete tasks
- [US1] = Import Installed + Check flow (the core MVP)
- [US2] = Import from File flow
- US3 (baseline metadata visibility) is folded into US1's warning banner implementation (T010 displays the snapshot date)
- All feature 009 code is co-located in `src/starfield_tool/tools/fast_lane_*` for easy cleanup when the feature is retired
- No new external dependencies — pure stdlib + existing project modules
- No new API calls at runtime — the Check action reads the existing creations cache
- The `_source_mode` instance state (introduced in T026) is cleanly removed when the feature is retired
- Commit after each phase or logical group
