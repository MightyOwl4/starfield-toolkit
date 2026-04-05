# Tasks: TES4 Master Dependency Sorting

**Input**: Design documents from `/specs/006-tes4-master-sort/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included (constitution principle II: Test Coverage is NON-NEGOTIABLE).

**Organization**: Two user stories. US1 (TES4 sorter) is foundational; US2 (validation on apply) depends on the parser from US1 but is independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: Verify existing infrastructure and understand integration points.

- [x] T001 Verify existing sorter infrastructure: confirm `src/load_order_sorter/sorters/` directory exists, `pipeline.py` has `_SORTERS` dict and `sort_creations()`, and `models.py` has `SortConstraint` with `priority` field

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: TES4 binary parser — shared by both the sorter (US1) and the validation check (US2).

**⚠️ CRITICAL**: Both user stories depend on this parser.

### Implementation

- [x] T002 Implement TES4 binary header parser in src/load_order_sorter/tes4_parser.py — function `parse_masters(filepath: Path) -> list[str]` that reads the first record of an .esm/.esp/.esl file, extracts MAST subrecord strings, and returns the list of master filenames. Use stdlib `struct` for binary unpacking. Read only the TES4 record data (first 24-byte header gives data_size, then read data_size bytes of subrecords). Handle: file not found, file too small, non-TES4 first record, corrupted data — all return empty list (FR-009).
- [x] T003 Implement base game master filter in src/load_order_sorter/tes4_parser.py — function `filter_base_game_masters(masters: list[str]) -> list[str]` that removes known base game files: `Starfield.esm`, `BlueprintShips-Starfield.esm`, `Starfield - Localization.esm`, and any matching pattern `sfbgs\d+\.esm` (case-insensitive). Also filter DLC masters like Shattered Space. Return only creation-plugin masters (FR-002).
- [x] T004 Implement master map builder in src/load_order_sorter/tes4_parser.py — function `build_master_map(data_dir: Path, plugin_files: dict[str, str]) -> dict[str, list[str]]` that iterates all plugin files, calls `parse_masters()` for each, filters base game masters, and further filters to only include masters that exist in the `plugin_files` dict (installed creation plugins). The `plugin_files` dict maps plugin filename to content_id.

### Tests

- [x] T005 [P] Write tests for TES4 parser in tests/test_tes4_parser.py — test `parse_masters()` with a synthetic binary TES4 record containing known MAST entries, test with empty file, test with non-TES4 file, test with file containing multiple MAST subrecords. Test `filter_base_game_masters()` with known base game names, SFBGS pattern (case variations), and community plugin names that should pass through. Test `build_master_map()` with mock data directory and plugin_files dict — verify filtering of non-installed masters.

**Checkpoint**: TES4 parser tested and ready. Both user stories can now proceed.

---

## Phase 3: User Story 1 - TES4 Master Dependencies in Auto-Sort (Priority: P1) 🎯 MVP

**Goal**: Auto-sort uses TES4 master dependencies as highest-priority `load_after` constraints, including cross-tier support.

**Independent Test**: Auto-sort a list where creation A (CAT tier 3) depends on creation B (CAT tier 5). Verify B appears before A in the result.

### Implementation

- [x] T006 [US1] Implement TES4 sorter in src/load_order_sorter/sorters/tes4.py — function `sort(items: list[SortItem], data_dir: Path, installed_plugins: dict[str, str]) -> list[SortConstraint]` following the pattern of category.py and loot.py. Constants: `SORTER_NAME = "TES4"`, `PRIORITY = 100`. For each item, look up its masters from `build_master_map()`, produce a `SortConstraint(type="load_after", after=master, priority=100, sorter_name="TES4")` for each creation-plugin master (FR-003, FR-005).
- [x] T007 [US1] Fix cross-tier dependency resolution in src/load_order_sorter/pipeline.py — add a pre-solve step in `_solve()` (before tier bucketing) that promotes items to the tier of their latest dependency. For each item with `load_after` targets, find the max tier among all targets. If the item's own tier is lower (earlier), promote it to the target's tier. Iterate until no more promotions needed (transitive chains). This ensures TES4 load_after constraints are never dropped by the within-tier topological sort (FR-004).
- [x] T008 [US1] Register TES4 sorter in src/load_order_sorter/pipeline.py — add `"tes4"` to `_SORTERS` dict, update `sort_creations()` to accept `data_dir` and `installed_plugins` parameters (passed through to TES4 sorter). The TES4 sorter runs alongside category and LOOT sorters, producing constraints that merge via the existing priority-based merger.
- [x] T009 [US1] Integrate TES4 sorter into auto-sort in src/starfield_tool/tools/load_order.py — update `_auto_sort()` to pass `game_install.data_dir` and a `plugin_files` dict (mapping plugin filename to content_id, built from `_working_groups`) to `sort_creations()`. Add `"tes4"` to the active sorters list.

### Tests

- [x] T010 [P] [US1] Write tests for TES4 sorter in tests/test_tes4_sorter.py — test constraint generation (correct load_after with priority 100), test base game masters excluded, test chain dependencies (A→B→C), test cross-tier promotion in the solver (item in tier 3 with dependency in tier 5 gets promoted to tier 5), test that existing CAT/LOOT behavior is preserved when no TES4 constraints exist, test sort_creations end-to-end with all three sorters active.

**Checkpoint**: Auto-sort now respects TES4 master dependencies. Cross-tier constraints work. Existing behavior preserved.

---

## Phase 4: User Story 2 - Non-Bypassable Validation on Apply (Priority: P2)

**Goal**: Prevent saving broken load orders by validating against TES4 master dependencies before writing to disk.

**Independent Test**: Manually drag a creation above its master dependency, click Apply, verify write is blocked with informative message.

### Implementation

- [x] T011 [US2] Implement validation function in src/load_order_sorter/validation.py — function `validate_tes4_order(plugin_order: list[str], master_map: dict[str, list[str]], display_names: dict[str, str]) -> list[ValidationViolation]` that checks each plugin's position against its masters. For each plugin, if any master appears AFTER it in the order, create a `ValidationViolation` with plugin name, master name, display names, and positions. Return list of all violations (empty = valid) (FR-006).
- [x] T012 [US2] Integrate validation into _apply() in src/starfield_tool/tools/load_order.py — before the `plugins_path.write_text()` call, build the master map (reuse cached if available from last auto-sort), extract the proposed plugin order from `_working_groups`, call `validate_tes4_order()`. If violations found: block the write, show a messagebox with up to 5 violations formatted as "CreationName must load after MasterName", plus a count of remaining violations if >5, and a suggestion to use Auto Sort. Return without writing (FR-007, FR-008).
- [x] T013 [US2] Cache master map for reuse between auto-sort and apply in src/starfield_tool/tools/load_order.py — store the master map as an instance variable `_tes4_master_map`. Populate it during auto-sort (T009). If not populated when _apply() needs it (user never ran auto-sort), build it on demand. Invalidate when file watcher detects Data directory changes.

### Tests

- [x] T014 [P] [US2] Write tests for validation in tests/test_tes4_validation.py — test valid order returns empty violations list, test single violation detected (plugin before its master), test multiple violations, test chain violation (A before B before C where C→B→A), test max 5 violations reported (with "and N more" count), test that base game masters don't trigger violations, test display names included in violations.

**Checkpoint**: Users cannot save broken load orders. Validation message is clear and actionable.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup.

- [x] T015 Run full project lint (`ruff check .`) and fix any issues
- [x] T016 Run full test suite (`pytest`) and verify all tests pass including existing load order sorter tests
- [ ] T017 Validate quickstart.md scenarios manually: auto-sort with TES4 deps, validation block on apply

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verification only
- **Foundational (Phase 2)**: Depends on Setup. T002→T003→T004 sequential (same file). T005 can run after T004.
- **User Story 1 (Phase 3)**: Depends on Foundational. T006→T007→T008→T009 sequential (different files but each depends on prior). T010 after T008.
- **User Story 2 (Phase 4)**: Depends on Foundational (parser). Can run in parallel with US1 for T011 (validation.py is independent). T012-T013 depend on T009 (auto-sort integration) for cache sharing.
- **Polish (Phase 5)**: Depends on all prior phases complete.

### Within Phase 2 (Foundational)

```
T002 (parse_masters) → T003 (filter) → T004 (build_master_map)
                                              └── T005 (tests) [P]
```

### Within Phase 3 (User Story 1)

```
T006 (tes4 sorter) → T007 (cross-tier fix) → T008 (register sorter) → T009 (UI integration)
                                                                              └── T010 (tests) [P]
```

### Within Phase 4 (User Story 2)

```
T011 (validation fn) [P, can start after T004]
T012 (integrate _apply) [after T009 + T011]
T013 (cache master map) [after T012]
T014 (tests) [P, after T011]
```

### Parallel Opportunities

- **T005** (parser tests) can run in parallel with T006-T009
- **T010** (sorter tests) can run in parallel with T011-T013
- **T011** (validation function) can start after foundational, in parallel with US1 work
- **T014** (validation tests) can run in parallel with T012-T013

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1: Verify setup
2. Complete Phase 2: TES4 parser with tests
3. Complete Phase 3: TES4 sorter + cross-tier fix + integration
4. **STOP and VALIDATE**: Auto-sort with TES4 dependencies works correctly
5. Continue to Phase 4: Validation on apply

### Incremental Delivery

1. Parser → standalone utility, testable independently
2. Sorter + cross-tier → auto-sort now TES4-aware (MVP!)
3. Validation → safety net for manual ordering
4. Polish → lint, full tests, manual validation

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] = TES4 sorter in auto-sort
- [US2] = validation check on apply
- Constitution requires tests — all modules have corresponding test files
- The cross-tier fix (T007) is critical — without it, TES4 constraints silently fail when dependency is in a different tier
- Priority 100 for TES4, leaving gaps at 25/30-90 for future constraint sources per master plan
- Commit after each phase or logical group
