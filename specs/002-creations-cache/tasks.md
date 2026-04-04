# Tasks: Creations API Response Caching

**Input**: Design documents from `/specs/002-creations-cache/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Includes exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: No new project structure needed. Existing project is already set up.

- [x] T001 Create cache module skeleton in src/starfield_tool/cache.py with cache file path constant and CacheEntry type

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core cache infrastructure that all user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Implement `load_cache()` in src/starfield_tool/cache.py — read JSON cache file from data dir, return dict of CacheEntry dicts keyed by content_id. Handle missing/corrupt files by returning empty dict.
- [x] T003 Implement `save_cache()` in src/starfield_tool/cache.py — write cache dict to JSON file. Silently ignore write failures (permissions, full disk).
- [x] T004 Implement `clear_cache()` in src/starfield_tool/cache.py — delete the cache file from disk.
- [x] T005 Implement `is_session_fresh(app_start_time)` in src/starfield_tool/cache.py — return True if monotonic time since app_start_time is less than 30 minutes.
- [x] T006 Implement `entry_to_page_info()` and `page_info_to_entry()` converters in src/starfield_tool/cache.py — convert between CacheEntry dicts and CreationPageInfo dataclass, preserving fetched_at timestamp.
- [x] T007 [P] Create test file tests/test_cache.py with tests for load_cache (missing file, corrupt file, valid file), save_cache (round-trip), clear_cache, is_session_fresh (within/outside window), and entry conversion.
- [x] T008 Record app startup time using `time.monotonic()` in src/starfield_tool/app.py and store it on the app instance or pass through ModuleContext.

**Checkpoint**: Cache module is complete and tested. Session timing is available. User story implementation can begin.

---

## Phase 3: User Story 1+2 — Cached Checks & Session Freshness (Priority: P1) MVP

**Goal**: `_fetch_creation_info` uses cache to skip API calls for cached Creations. Volatile data is re-fetched when session window expires. Immutable data is never re-fetched.

**Independent Test**: Run "Check for Updates" twice within 30 minutes on 5+ Creations. Second check completes near-instantly. After 30 minutes, volatile data is re-fetched.

- [x] T009 [US1] Modify `_fetch_creation_info()` in src/starfield_tool/version_checker.py to accept `app_start_time` parameter and load cache at start of function.
- [x] T010 [US1] Add cache lookup logic in `_fetch_creation_info()` — for each creation, check if cache entry exists. If session is fresh and entry exists, use cached data. If session expired, use only immutable fields from cache and re-fetch volatile fields.
- [x] T011 [US1] After API fetch loop, merge fresh results with cached immutable data and save updated cache to disk in `_fetch_creation_info()`.
- [x] T012 [US1] Update `check_for_updates()` in src/starfield_tool/version_checker.py to pass `app_start_time` through to `_fetch_creation_info()`.
- [x] T013 [US1] Update `check_achievements()` in src/starfield_tool/version_checker.py to pass `app_start_time` through to `_fetch_creation_info()`.
- [x] T014 [US1] Update `_check_updates()` and `_check_achievements()` in src/starfield_tool/tools/creation_load_order.py to pass `app_start_time` from context.
- [x] T015 [P] [US1] Add tests in tests/test_version_checker.py: mock `_fetch_creation_info` with cache to verify cached data is returned without API calls; verify volatile data is re-fetched after session expiry; verify immutable data survives across sessions.

**Checkpoint**: Cached checks work. Repeated checks are fast. Session window controls volatile staleness.

---

## Phase 4: User Story 3 — Post-Update State Preservation (Priority: P2)

**Goal**: After a file-change-triggered refresh, update/achievement indicators persist from cache instead of being lost.

**Independent Test**: Run "Check for Updates" showing updates, modify Plugins.txt, click Refresh. Update indicators persist.

- [x] T016 [US3] Modify `_on_refresh_complete()` in src/starfield_tool/tools/creation_load_order.py — after reloading creations, check if cached check results exist (within session window). If so, reapply `available_version`, `has_update`, and `achievement_friendly` from cache to the refreshed creation list.
- [x] T017 [US3] Ensure `_populate_tree()` in src/starfield_tool/tools/creation_load_order.py respects the restored state (no changes needed if flags are set correctly on Creation objects).

**Checkpoint**: Refreshing the creation list preserves check state from cache.

---

## Phase 5: User Story 4 — Explicit Cache Clear (Priority: P3)

**Goal**: User can click "Clear Cache" to remove all cached data and force fresh API fetches.

**Independent Test**: Run a check, click "Clear Cache", run check again. Second check takes full API fetch time.

- [x] T018 [US4] Add "Clear Cache" button in the toolbar in src/starfield_tool/tools/creation_load_order.py, using the same button style as existing buttons.
- [x] T019 [US4] Implement `_clear_cache()` handler in src/starfield_tool/tools/creation_load_order.py — call `clear_cache()` from cache module, reset check state flags, repopulate tree, show brief confirmation in status bar.

**Checkpoint**: Users can force a full re-fetch by clearing cache.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T020 Run full test suite (`uv run pytest tests/ -v`) and fix any regressions
- [x] T021 Run linter (`uv run ruff check src/`) and fix any issues
- [x] T022 Verify quickstart.md scenarios manually: first check caches, second check is fast, clear cache works, session expiry re-fetches

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies
- **Phase 2 (Foundational)**: Depends on Phase 1
- **Phase 3 (US1+2)**: Depends on Phase 2 — this is the MVP
- **Phase 4 (US3)**: Depends on Phase 3 (needs cache integration in place)
- **Phase 5 (US4)**: Depends on Phase 2 only (cache clear is independent of check integration)
- **Phase 6 (Polish)**: Depends on all previous phases

### User Story Dependencies

- **US1+2 (P1)**: Can start after Foundational — no dependencies on other stories
- **US3 (P2)**: Depends on US1+2 (needs cached check results to preserve)
- **US4 (P3)**: Can start after Foundational — independent of US1+2

### Parallel Opportunities

- T007 (cache tests) can run in parallel with T008 (app startup time)
- T015 (version checker tests) can run in parallel with T014 (UI wiring)
- Phase 5 (US4) can run in parallel with Phase 4 (US3) — both depend only on Phase 2/3

---

## Implementation Strategy

### MVP First (Phase 1 + 2 + 3)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T008)
3. Complete Phase 3: US1+2 cache integration (T009-T015)
4. **STOP and VALIDATE**: Run checks twice, verify second is instant
5. This alone delivers the core value

### Incremental Delivery

1. MVP (Phases 1-3) → Cached checks work
2. Add US3 (Phase 4) → Refresh preserves state
3. Add US4 (Phase 5) → Clear Cache button
4. Polish (Phase 6) → Final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story
- US1 and US2 are combined into one phase since they share the same implementation (cache + session window)
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
