# Tasks: Load Order Rule Books

**Input**: Design documents from `/specs/007-rulebook-engine/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included (constitution principle II: Test Coverage is NON-NEGOTIABLE).

**Organization**: Three user stories. US1 (sorter) is foundational engine work; US2 (management tool) and US3 (editor) are UI. US2 depends on the rule book I/O from US1's foundation. US3 depends on US2 for the management tool context.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: Create directories and verify integration points.

- [x] T001 Create `data/rules/` directory for curated rule book files at project root
- [x] T002 Verify existing sorter infrastructure: confirm `pipeline.py` has `_SORTERS` dict, `sort_creations()` accepts `data_dir` and `installed_plugins` params (from feature 006), and `tools/__init__.py` has `MODULES` list

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Rule book I/O, parsing, normalization, and applicability checking — shared by all three user stories.

**⚠️ CRITICAL**: All user stories depend on this foundation.

### Implementation

- [x] T003 Implement rule book file I/O in src/load_order_sorter/rulebook.py — functions: `load_rulebook(filepath: Path) -> dict | None` (returns parsed JSON or None on error), `save_rulebook(data: dict, filepath: Path)` (atomic write). Handle corrupted files by returning None (caller decides error handling). Validate schema: must have `name` (str) and `rules` (list) fields.
- [x] T004 Implement load_before normalization in src/load_order_sorter/rulebook.py — function `normalize_rules(rules: list[dict]) -> list[dict]` that converts `load_before` entries to equivalent `load_after` constraints. If rule A has `load_before: ["B"]`, produce an additional rule `{"plugin": "B", "load_after": ["A"]}`. Merge with any existing load_after for that plugin. Return normalized rules with only `load_after` (no `load_before`).
- [x] T005 Implement applicability checking in src/load_order_sorter/rulebook.py — function `check_applicability(rules: list[dict], installed_plugins: set[str]) -> tuple[list[dict], set[str], bool]` returning (applicable_rules, missing_plugins, is_applicable). Filter rules to only include those where `plugin` is installed. Skip individual `load_after` targets that aren't installed. A book is inapplicable if fewer than 1 rule remains with at least one valid load_after target.
- [x] T006 Implement rule book discovery in src/load_order_sorter/rulebook.py — function `discover_rulebooks(user_dir: Path, curated_dir: Path | None) -> list[dict]` that scans both directories for `*.json` files. Returns list of `{filepath, filename, source ("user"/"curated"), created_time}`. Curated sorted by filename (numeric prefix). User sorted by file creation date (newest first).
- [x] T007 Implement registry reconciliation in src/load_order_sorter/rulebook.py — function `reconcile_registry(discovered: list[dict], saved_registry: list[dict]) -> list[dict]` that merges discovered files with saved registry state. New user files go to top (above saved entries). Stale entries (file no longer exists) are discarded. Preserved entries keep their enabled/disabled state and relative order.
- [x] T008 Extend AppSettings with rulebook_registry in src/starfield_tool/config.py — add field `rulebook_registry: list[dict]` (default empty list) to the `AppSettings` dataclass. Each entry: `{filename, source, enabled}`. Update `load_config` and `save_config` to handle the new field.

### Tests

- [x] T009 [P] Write tests for rule book I/O in tests/test_rulebook.py — test load valid JSON, test load corrupted file returns None, test load missing required fields returns None, test save creates file, test atomic write. Test normalize_rules: load_before converted, load_after preserved, combined load_before+load_after on same rule, load_before on plugin not in book. Test check_applicability: all installed (full apply), one missing (partial), all missing (inapplicable), single-rule book validity. Test discover_rulebooks: user sorted by date, curated sorted by prefix, mixed sources. Test reconcile_registry: new files at top, stale removed, saved order preserved.

**Checkpoint**: Rule book I/O, normalization, and discovery tested. All stories can now proceed.

---

## Phase 3: User Story 1 - Rule Book Sorter Integration (Priority: P1) 🎯 MVP

**Goal**: Auto-sort uses rule book constraints at two priority tiers (curated=30, user=40+) alongside TES4, LOOT, and category.

**Independent Test**: Place a rule book JSON in the rules directory, run auto-sort, verify the specified creation order is respected.

### Implementation

- [x] T010 [US1] Implement rule book sorter in src/load_order_sorter/sorters/rulebook.py — function `sort(items: list[SortItem], user_dir: Path, curated_dir: Path | None, registry: list[dict], installed_plugins: dict[str, str]) -> list[SortConstraint]`. For each enabled, applicable book: load, normalize, check applicability, produce SortConstraint(type="load_after", priority=30 for curated or 40+position for user). Skip corrupted books (log warning). Skip inapplicable books.
- [x] T011 [US1] Register rule book sorter in src/load_order_sorter/pipeline.py — add `"rulebook"` to `_SORTERS` dict. Update `sort_creations()` to accept `user_rules_dir`, `curated_rules_dir`, and `rulebook_registry` parameters. Pass through to rulebook sorter when `"rulebook"` is in active sorters list.
- [x] T012 [US1] Integrate rule book sorter into auto-sort in src/starfield_tool/tools/load_order.py — update `_auto_sort()` to pass user rules directory (`_config_path().parent / "rules"`), curated rules directory (from bundled path via `sys._MEIPASS` or dev fallback), and rulebook registry (from loaded AppSettings) to `sort_creations()`. Add `"rulebook"` to active sorters list.
- [x] T013 [US1] Add corrupted rule book detection on startup in src/starfield_tool/tools/load_order.py — during `initialize()`, scan rule books and detect corrupted files. For each corrupted book: show error dialog with filename, instructions ("reinstall, undo changes, or delete"), and auto-deactivate in registry. Save updated registry (FR-018).

### Tests

- [x] T014 [P] [US1] Write tests for rule book sorter in tests/test_rulebook_sorter.py — test curated book at priority 30, test user book at priority 40+, test user beats curated on conflict, test multiple user books priority by position, test disabled book skipped, test inapplicable book skipped, test corrupted book skipped with warning, test load_before normalization produces correct constraints, test missing creation in load_after skipped, test sort_creations end-to-end with rulebook+category+tes4 sorters active.

**Checkpoint**: Auto-sort respects rule book constraints. Curated and user books work at correct priorities. MVP complete.

---

## Phase 4: User Story 2 - Rule Book Management Tool (Priority: P2)

**Goal**: Dedicated app tab for viewing, enabling, disabling, and reordering rule books. Missing creation warnings and inapplicability errors displayed.

**Independent Test**: Place rule book files in the data directory, open the Rule Books tab, verify books appear with correct metadata and can be toggled/reordered.

### Implementation

- [ ] T015 [US2] Create RuleBookTool skeleton in src/starfield_tool/tools/rulebook_manager.py — class inheriting ToolModule with `name = "Rule Books"`, `description = "Manage load order rule books..."`. Implement `initialize(context)` creating the content frame layout: top button bar (New, Rescan, buttons) and main list area.
- [ ] T016 [US2] Register RuleBookTool in src/starfield_tool/tools/__init__.py — import RuleBookTool, add to MODULES list after LoadOrderTool.
- [ ] T017 [US2] Implement rule book list view in src/starfield_tool/tools/rulebook_manager.py — treeview showing all discovered books with columns: Name, Description, Rules count, Status (active/disabled/inapplicable/corrupted), Source (user/curated). User books section above curated section. Enable/disable toggle via checkbox or button. Theme-aware styling matching existing tools.
- [ ] T018 [US2] Implement priority reordering in src/starfield_tool/tools/rulebook_manager.py — drag-and-drop or up/down buttons to reorder user books. Curated books reorderable among themselves but always below user section. Save updated registry to AppSettings on reorder.
- [ ] T019 [US2] Implement rescan button in src/starfield_tool/tools/rulebook_manager.py — button that re-runs discovery + reconciliation, refreshes the list view. New books appear at top of user section, enabled by default.
- [ ] T020 [US2] Implement book details/applicability display in src/starfield_tool/tools/rulebook_manager.py — when selecting a book in the list, show details panel with: full description, rule list, and applicability status. Missing creations highlighted in Constellation yellow. Inapplicable books show red error message. Corrupted books show red error with file path.
- [ ] T021 [US2] Implement curated rule book path resolution in src/starfield_tool/tools/rulebook_manager.py — helper to find curated books directory: `sys._MEIPASS/data/rules/` when frozen (PyInstaller), or `data/rules/` relative to project root in dev mode. Reuse pattern from `_get_bundled_masterlist_path()`.

### Tests

- [ ] T022 [P] [US2] Write tests for management tool logic in tests/test_rulebook.py — test registry save/load roundtrip via AppSettings, test rescan picks up new files at top, test reorder persists to registry, test curated books stay below user books. (UI rendering not tested — logic only.)

**Checkpoint**: Users can view, manage, and reorder rule books from the app. Applicability status visible.

---

## Phase 5: User Story 3 - Rule Book Creator/Editor (Priority: P3)

**Goal**: Dialog for creating new rule books and editing existing user books. Select creations from installed list, arrange order, save.

**Independent Test**: Click "New Rule Book", select creations, arrange, save, verify file appears and is loaded by sorter.

### Implementation

- [ ] T023 [US3] Implement rule book editor dialog in src/starfield_tool/dialogs/rulebook_editor.py — CTkToplevel dialog with: name/description text fields, creation picker (list of installed creations with checkboxes), selected creations list (reorderable), save/cancel buttons. On save: generate rules from the ordered selection (each creation gets `load_after` pointing to the one above it in the list), call `save_rulebook()`, close dialog.
- [ ] T024 [US3] Implement edit mode in src/starfield_tool/dialogs/rulebook_editor.py — when editing an existing book: pre-populate name, description, and selected creations from the loaded rule book. Highlight missing creations in yellow. Curated books open in read-only mode (all fields disabled, no save button).
- [ ] T025 [US3] Wire editor to management tool in src/starfield_tool/tools/rulebook_manager.py — "New" button opens editor in create mode. Double-click or "Edit" button opens editor for selected book (edit mode for user, read-only for curated). After save: rescan and refresh list.

### Tests

- [ ] T026 [P] [US3] Write tests for editor logic in tests/test_rulebook.py — test rule generation from ordered creation list (correct load_after chain), test save produces valid JSON file, test pre-population from existing book. (Dialog rendering not tested — logic only.)

**Checkpoint**: Full rule book lifecycle: create, edit, manage, sort. Feature complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Build integration, final validation, cleanup.

- [ ] T027 Update bin/build.sh to bundle curated rule books via `--add-data data/rules;data/rules` flag
- [ ] T028 Run full project lint (`ruff check .`) and fix any issues
- [ ] T029 Run full test suite (`pytest`) and verify all tests pass including existing sorter tests
- [ ] T030 Validate quickstart.md scenarios: file-only workflow, management tool, editor create/save

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup. T003→T004→T005→T006→T007 sequential (same file). T008 parallel (different file). T009 after T007+T008.
- **US1 (Phase 3)**: Depends on Foundational. T010→T011→T012→T013 sequential. T014 after T012.
- **US2 (Phase 4)**: Depends on Foundational + T012 (auto-sort integration for curated path resolution). T015→T016→T017→T018→T019→T020→T021 mostly sequential (same file). T022 after T021.
- **US3 (Phase 5)**: Depends on US2 (editor launched from management tool). T023→T024→T025 sequential. T026 after T024.
- **Polish (Phase 6)**: Depends on all prior phases.

### Parallel Opportunities

- **Phase 2**: T008 (config.py) in parallel with T003-T007 (rulebook.py). T009 (tests) after both.
- **Phase 3**: T014 (sorter tests) can run alongside T013 (startup detection).
- **Phase 4**: T022 (management tests) after T021. T021 (curated path) can start alongside T017-T020.
- **Phase 5**: T026 (editor tests) after T024.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Setup directories
2. Complete Phase 2: Rule book I/O, normalization, discovery, registry
3. Complete Phase 3: Rule book sorter + pipeline integration
4. **STOP and VALIDATE**: Place a JSON rule book in the rules dir, run auto-sort, verify rules applied
5. Continue to US2 + US3 for UI

### Incremental Delivery

1. Foundation → testable rule book engine with no UI
2. US1 (sorter) → rules applied in auto-sort via file-only workflow (MVP!)
3. US2 (management) → view, toggle, reorder in the app
4. US3 (editor) → create and edit books in the app
5. Polish → build integration, lint, full tests

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] = rule book sorter integration
- [US2] = management tool tab
- [US3] = editor dialog
- Constitution requires tests — all modules have corresponding test tasks
- Priority hierarchy: curated=30, user=40+, fitting between LOOT(20) and TES4(100)
- `load_before` is normalized to `load_after` in the foundation layer — sorter only sees load_after
- Commit after each phase or logical group
- UI tests cover logic only, not rendering (no GUI test framework)
