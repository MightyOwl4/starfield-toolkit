# Tasks: Creations Grid Modes & Details Dialog

**Input**: Design documents from `/specs/004-creations-grid-modes/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the new `dialogs` package and the freshness-agnostic cache access function that multiple stories depend on.

- [x] T001 Create dialogs package with `src/starfield_tool/dialogs/__init__.py` (empty `__init__.py`)
- [x] T002 Add `get_cached_info_any()` function to `src/starfield_tool/creations.py` — calls `load_cache()` and `entry_to_info()` without `is_session_fresh()` gate, returns `dict[str, CreationInfo]` (empty dict if cache missing/corrupt)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the reusable details dialog component before it's wired into the grid. This is shared across all user stories.

**⚠️ CRITICAL**: The details dialog must be complete before any user story wires the "Details" button.

- [x] T003 Implement `CreationDetailsDialog` class in `src/starfield_tool/dialogs/creation_details.py` — `CTkToplevel` subclass following DiffDialog windowing pattern (no `grab_set()`, topmost then immediate unset). Constructor: `(parent, display_name, info: CreationInfo | None, thumbnail_image: PIL.Image | None = None)`. Layout: header with thumbnail + bold title, metadata grid (author, version, price displayed as "Free"/"{n} Credits", size, created, updated, achievement friendly), categories list, scrollable description area, Close button. Escape key and window close button dismiss. Missing fields show "n/a".
- [x] T004 Add thumbnail download helper function in `src/starfield_tool/dialogs/creation_details.py` (or a small helper alongside it) — accepts a `thumbnail_url: str`, downloads via `urllib.request`, returns `PIL.Image` resized to dialog header size. Returns `None` on failure. This is used both by the dialog header and by rich media rows.

**Checkpoint**: Details dialog can be opened standalone with test data.

---

## Phase 3: User Story 1 — Text List Mode with Author Column (Priority: P1) 🎯 MVP

**Goal**: Extend the existing text list treeview with an "Author" column populated from cache (stale OK), no network activity triggered.

**Independent Test**: View installed creations tab with/without cache file. Author shows cached value or "n/a".

### Implementation for User Story 1

- [x] T005 [US1] Modify treeview column definition in `src/starfield_tool/tools/creation_load_order.py` — add "Author" column after "Name" (columns become `("#", "Name", "Author", "Version", "Date")`), set Author column width ~120px, adjust Name column width to accommodate
- [x] T006 [US1] Update `_populate_tree()` in `src/starfield_tool/tools/creation_load_order.py` — call `get_cached_info_any()` once at the start, look up each creation's `content_id` in the result, insert author value (or "n/a" if not found) into the Author column of each row
- [x] T007 [US1] Add "Details" button column to treeview rows in `src/starfield_tool/tools/creation_load_order.py` — bind click on the row (or add a button mechanism) that opens `CreationDetailsDialog` with the creation's cached info. Pass the cached `CreationInfo` from `get_cached_info_any()` and creation's `display_name`. If no cache entry, open dialog with `info=None`.

**Checkpoint**: Text list shows Author column from stale cache. Details button opens dialog. No network requests made.

---

## Phase 4: User Story 2 — Rich Media Grid Mode (Priority: P2)

**Goal**: Provide a rich media display mode with thumbnails, bold creation names, description excerpts, and loading placeholders when cache is cold.

**Independent Test**: Toggle to rich media mode — see thumbnails and formatted text with warm cache, or loading placeholders with cold cache that resolve after fetch.

### Implementation for User Story 2

- [x] T008 [US2] Add mode toggle control (segmented button or icon toggle) to the button bar in `src/starfield_tool/tools/creation_load_order.py` — two states: "List" (default) and "Media". Store current mode in instance variable (e.g., `self._grid_mode`). Toggle calls a method to switch the displayed grid.
- [x] T009 [US2] Implement rich media scrollable container in `src/starfield_tool/tools/creation_load_order.py` — create a `CTkScrollableFrame` that replaces (hides) the treeview when in rich media mode. When switching back to text list, hide the scrollable frame and show the treeview.
- [x] T010 [US2] Implement rich media row widget builder in `src/starfield_tool/tools/creation_load_order.py` — each row is a `CTkFrame` containing: thumbnail `CTkLabel` (~3 line heights, ~84px tall), text block frame (bold `CTkLabel` for name on first line + `CTkLabel` for description excerpt below, truncated to fit without expanding height), plus labels for the remaining columns (position, author, version, date). Include a "Details" button on each row that opens `CreationDetailsDialog`.
- [x] T011 [US2] Implement thumbnail download and in-memory caching in `src/starfield_tool/tools/creation_load_order.py` — maintain `self._thumbnail_cache: dict[str, CTkImage]`. Download thumbnails in a daemon thread using the helper from T004, convert to `CTkImage`, cache by `content_id`. Use `widget.after(0, callback)` to update the row's thumbnail label on the main thread. Show gray placeholder while downloading. Handle download failures with a fallback placeholder.
- [x] T012 [US2] Implement cache-cold placeholder rendering in `src/starfield_tool/tools/creation_load_order.py` — when switching to rich media mode and `get_cached_info_any()` returns empty (or `get_cached_info()` with session freshness returns empty), render placeholder rows (gray thumbnail box, "Loading..." name, empty description). Trigger a full cache fetch in a daemon thread using existing `check_for_updates`-style threading pattern. On fetch complete, call `widget.after(0, ...)` to re-render rich media rows with actual data.
- [x] T013 [US2] Handle cache clear while in rich media mode in `src/starfield_tool/tools/creation_load_order.py` — if cache is cleared (e.g., via `clear_cache()`), detect this and immediately reset rich media rows to loading placeholders, then trigger a fresh cache fetch as in T012.

**Checkpoint**: Rich media mode shows thumbnails, bold names, and description excerpts. Switching to it with cold cache shows placeholders then resolves. Cache clear resets and re-fetches.

---

## Phase 5: User Story 3 — Creation Details Dialog Integration (Priority: P2)

**Goal**: The details dialog is already built (T003). This story ensures it's fully wired in both modes with correct data.

**Independent Test**: Click "Details" on any creation in either mode. Dialog shows all cached fields. Dialog visible in Alt+Tab. Close returns focus to main window.

### Implementation for User Story 3

- [x] T014 [US3] Wire details button in rich media mode in `src/starfield_tool/tools/creation_load_order.py` — the "Details" button on each rich media row (from T010) opens `CreationDetailsDialog`. Pass the `CreationInfo` from cache lookup and the creation's `display_name`. If a thumbnail is already downloaded (from `self._thumbnail_cache`), convert and pass as `thumbnail_image` to avoid re-downloading.
- [x] T015 [US3] Ensure details dialog works with missing cache data — when "Details" is clicked but no cache entry exists for the creation, open dialog with `info=None` so all fields show "n/a". Verify this works for both text list and rich media modes.

**Checkpoint**: Details dialog opens from both modes with full cached data or graceful "n/a" fallback. Visible in OS task switcher.

---

## Phase 6: User Story 4 — Mode Switching and Persistence (Priority: P3)

**Goal**: Smooth toggling between modes with visual indication of current mode. Session-scoped persistence.

**Independent Test**: Switch modes back and forth. Grid redraws correctly each time. No data loss.

### Implementation for User Story 4

- [x] T016 [US4] Implement mode switch logic in `src/starfield_tool/tools/creation_load_order.py` — switching from rich media to text list hides the scrollable frame, shows the treeview, and calls `_populate_tree()` to refresh. Switching from text list to rich media hides the treeview, shows the scrollable frame, and renders rich media rows. The toggle button visually indicates the active mode.
- [x] T017 [US4] Preserve scroll position and selection state across mode switches in `src/starfield_tool/tools/creation_load_order.py` — when switching modes, remember which creation was selected (if any) and restore it in the new mode. Ensure no data is lost during redraws.

**Checkpoint**: Modes toggle cleanly. Current mode is visually indicated. Data preserved across switches.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Edge cases, error handling, and cleanup that affect multiple stories.

- [x] T018 Handle thumbnail download failure gracefully in `src/starfield_tool/tools/creation_load_order.py` — invalid URLs, network errors, non-image responses should all result in a fallback placeholder image (gray box), not exceptions or broken UI.
- [x] T019 Handle network error during cache fetch in rich media mode in `src/starfield_tool/tools/creation_load_order.py` — if fetch fails, leave placeholders in place and show error message via status bar. Do not crash or leave the grid in a broken state.
- [x] T020 Handle rapid mode toggling in `src/starfield_tool/tools/creation_load_order.py` — if user toggles while a cache fetch or thumbnail download is in progress, the fetch should complete and the grid should reflect the final selected mode (not an intermediate state).
- [x] T021 Run full test suite and verify no regressions — `pytest` from repo root. Fix any failures.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (`dialogs/` package exists for T003)
- **US1 (Phase 3)**: Depends on Phase 1 (T002 for `get_cached_info_any()`) and Phase 2 (T003 for details dialog)
- **US2 (Phase 4)**: Depends on Phase 1 + Phase 2. Can run in parallel with US1 but T011 uses helper from T004.
- **US3 (Phase 5)**: Depends on US1 and US2 (wiring details button in both modes)
- **US4 (Phase 6)**: Depends on US1 and US2 (both modes must exist to toggle between them)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Depends on Phase 1 + 2 only — independently testable as MVP
- **User Story 2 (P2)**: Depends on Phase 1 + 2 only — can run in parallel with US1
- **User Story 3 (P2)**: Depends on US1 + US2 (details button must exist in both modes)
- **User Story 4 (P3)**: Depends on US1 + US2 (both modes must exist for toggling)

### Within Each User Story

- UI structure before data population
- Data population before interaction handlers
- Core implementation before edge case handling

### Parallel Opportunities

- T001 and T002 can run in parallel (different files)
- T003 and T004 can run in parallel (same file but independent functions)
- US1 (Phase 3) and US2 (Phase 4) can run in parallel after Phase 2 completes
- T018, T019, T020 can all run in parallel (different concerns, same file but independent code paths)

---

## Parallel Example: Setup + Foundational

```
# Phase 1 — run in parallel:
Task T001: "Create dialogs package __init__.py"
Task T002: "Add get_cached_info_any() to creations.py"

# Phase 2 — run in parallel:
Task T003: "Implement CreationDetailsDialog"
Task T004: "Add thumbnail download helper"
```

## Parallel Example: User Stories 1 + 2

```
# After Phase 2 completes, run US1 and US2 in parallel:

# US1 stream:
Task T005: "Add Author column to treeview"
Task T006: "Update _populate_tree() with cache lookup"
Task T007: "Add Details button to text list"

# US2 stream (parallel):
Task T008: "Add mode toggle control"
Task T009: "Implement rich media scrollable container"
Task T010: "Implement rich media row widget builder"
Task T011: "Implement thumbnail download and caching"
Task T012: "Implement cache-cold placeholder rendering"
Task T013: "Handle cache clear in rich media mode"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T004)
3. Complete Phase 3: User Story 1 (T005-T007)
4. **STOP and VALIDATE**: Text list shows Author column, Details button works
5. This is a shippable MVP — existing UI enhanced with no breaking changes

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Author column + Details button (MVP!)
3. Add User Story 2 → Rich media grid with thumbnails
4. Add User Story 3 → Details dialog wired in both modes
5. Add User Story 4 → Smooth mode toggling
6. Polish → Edge cases and error handling

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Details dialog (T003) is intentionally in Foundational because it's shared across US1, US2, US3
