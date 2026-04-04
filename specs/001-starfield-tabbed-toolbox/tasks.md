# Tasks: Starfield Tabbed GUI Toolbox

**Input**: Design documents from `/specs/001-starfield-tabbed-toolbox/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included (constitution mandates test coverage as NON-NEGOTIABLE).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup

**Purpose**: Project initialization and basic structure

- [x] T001 Create project directory structure per plan.md (`src/starfield_tool/`, `src/starfield_tool/tools/`, `tests/`, `tests/fixtures/`, `assets/`, `bin/`, `.github/workflows/`)
- [x] T002 Create `pyproject.toml` with uv config: Python 3.12+, dependencies (customtkinter, watchdog, httpx, beautifulsoup4), dev dependencies (pytest), project metadata, and `[tool.pytest.ini_options]`
- [x] T003 Run `uv sync` to generate `uv.lock` and verify dependency installation
- [x] T004 [P] Create `_version.py` with `__version__ = "dev"` at project root
- [x] T005 [P] Create `Makefile` with targets: `test` (uv run pytest), `build` (bin/build-win.sh), `clean` (rm -rf build/)
- [x] T006 [P] Create `src/starfield_tool/__init__.py` importing `__version__` from `_version`
- [x] T007 [P] Create `src/starfield_tool/__main__.py` with entry point: set AppUserModelID via `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID()`, import and launch app
- [x] T008 [P] Add placeholder `assets/icon.ico` (can be a simple default icon, replaced later with proper branding)

**Checkpoint**: Project builds, `uv run python -m starfield_tool` launches without error (even if it does nothing yet)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, interfaces, and config that ALL user stories depend on

- [x] T009 Create `src/starfield_tool/models.py` with dataclasses: `GameInstallation` (game_root, data_dir, content_catalog, plugins_txt, source, is_valid) and `Creation` (content_id, display_name, author, installed_version, plugin_files, load_position, is_active, file_missing, available_version, has_update) per data-model.md
- [x] T010 Create `src/starfield_tool/base.py` with `ToolModule` ABC (class attrs: `name`, `description`; abstract method: `initialize(context: ModuleContext)`) and `ModuleContext` dataclass (game_installation, status_bar, content_frame) and `StatusBarAPI` protocol (set_task, clear_task) per contracts/module-interface.md
- [x] T011 Create `src/starfield_tool/config.py` with `AppSettings` dataclass (game_path, window_geometry), `load_config()` reading from `%APPDATA%/StarfieldToolkit/config.json`, `save_config()` writing to same path. Handle missing file/dir gracefully (return defaults).
- [x] T012 [P] Create `src/starfield_tool/tools/__init__.py` with empty `MODULES: list[type[ToolModule]] = []` registry list

### Tests for Phase 2

- [x] T013 [P] Create `tests/test_models.py` — test GameInstallation validation (valid dir, missing dir, missing Data subdir), test Creation defaults (available_version=None, has_update=False)
- [x] T014 [P] Create `tests/test_config.py` — test load_config with missing file returns defaults, test save_config creates file and dir, test round-trip save then load preserves values, test load_config with corrupted JSON returns defaults

**Checkpoint**: `make test` passes. Core data structures and config in place.

---

## Phase 3: User Story 2+5 - App Shell + Status Bar (Priority: P1)

**Goal**: Application window with tabbed interface and status bar. No game detection yet — just the skeleton.

**Independent Test**: Launch app, verify tab bar and status bar render. Add a dummy module and confirm it appears as a tab.

### Tests for US2+US5

- [x] T015 [P] [US2] Create `tests/test_app.py` — test that App creates a window with a tab bar, test that registering a module adds a tab with the module's name, test that the "not found" placeholder is shown when modules are not initialized
- [x] T016 [P] [US5] Add tests to `tests/test_app.py` — test that status bar renders two segments, test set_task updates segment 2 text, test clear_task resets to "Ready", test segment 1 shows path warning when no game path set

### Implementation for US2+US5

- [x] T017 [US5] Create `src/starfield_tool/status_bar.py` — `StatusBar` widget (customtkinter frame with two label segments: game path + task), implement `StatusBarAPI` protocol (set_task, clear_task methods)
- [x] T018 [US2] Create `src/starfield_tool/app.py` — `App` class extending `customtkinter.CTk`: window title "Starfield Toolkit", icon from assets/, `CTkTabview` for tabs, `StatusBar` at bottom, module discovery from `tools.MODULES`, tab creation loop reading module `name`, placeholder "Starfield not found" content with Browse/Auto-detect buttons per FR-008c, `initialize_modules(game_installation)` method that replaces placeholders and calls each module's `initialize()`
- [x] T019 [US2] Update `src/starfield_tool/__main__.py` to instantiate and run `App`

**Checkpoint**: `uv run python -m starfield_tool` shows window with tab bar (empty or placeholder), status bar with "Starfield path not set" and "Ready".

---

## Phase 4: User Story 3 - Startup Game Detection & Configuration (Priority: P1)

**Goal**: On startup, resolve the Starfield install path via config → Steam auto-detect → manual browse fallback. Persist result. Initialize modules when found.

**Independent Test**: Launch with no config → auto-detection runs. Launch with valid config → fast path. Launch with stale config → re-prompt.

### Tests for US3

- [x] T020 [P] [US3] Create `tests/test_steam.py` — test parsing a mock `libraryfolders.vdf` file to extract library paths, test finding Starfield in a mock Steam library structure, test handling missing registry key gracefully, test handling missing vdf file gracefully
- [x] T021 [P] [US3] Create `tests/fixtures/libraryfolders.vdf` with sample Valve KeyValues data containing 2 library paths
- [x] T022 [P] [US3] Create `tests/fixtures/` mock Starfield install structure: `fixtures/fake_starfield/Data/` with dummy `.esm` file and a `fixtures/fake_starfield/ContentCatalog.txt`

### Implementation for US3

- [x] T023 [US3] Create `src/starfield_tool/steam.py` — `find_steam_install()` reading registry (`HKLM\SOFTWARE\WOW6432Node\Valve\Steam\InstallPath`), `parse_library_folders(vdf_path)` parsing `libraryfolders.vdf`, `find_starfield_in_libraries(library_paths)` checking each `<path>/steamapps/common/Starfield/` for valid install, top-level `auto_detect_starfield() -> GameInstallation | None`
- [x] T024 [US3] Add startup flow to `src/starfield_tool/app.py` — on init: load config → if game_path set and valid, call `initialize_modules()` → else run `auto_detect_starfield()` → if found, save config and init → else show file browser dialog (tkinter.filedialog.askdirectory) → if selected and valid, save and init → else show skeleton with placeholders. Wire Browse/Auto-detect buttons in placeholder to re-trigger this flow.
- [x] T025 [US3] Integrate status bar segment 1: update game path display after successful detection/configuration, show warning when not set

**Checkpoint**: Full startup flow works. Config persists between sessions. Status bar shows path.

---

## Phase 5: User Story 1 - View Installed Creations in Load Order (Priority: P1) MVP

**Goal**: The Creation Load Order tab displays all Bethesda store Creations in their load order with position, name, author, and version. Refresh button re-reads files. File monitoring shows "outdated" indicator.

**Independent Test**: Point at a test fixture folder, verify correct Creations listed in correct order with correct metadata.

### Tests for US1

- [x] T026 [P] [US1] Create `tests/fixtures/Plugins.txt` with sample entries (mix of `*`-prefixed active and inactive plugins, including base game ESMs and Creation store plugins)
- [x] T027 [P] [US1] Create `tests/fixtures/ContentCatalog.txt` with sample entries matching some plugins from Plugins.txt (with Title, Version, Author, Files fields)
- [x] T028 [P] [US1] Create `tests/fixtures/Data/` with dummy `.esm`/`.esp` files matching ContentCatalog entries (empty files, just need to exist). Include one referenced file that is deliberately missing to test `file_missing` flag.
- [x] T029 [P] [US1] Create `tests/test_parsers.py` — test `parse_plugins_txt`: correct order, active/inactive detection, comment/blank line handling. Test `parse_content_catalog`: extract content_id, display_name, author, version, plugin_files. Test malformed file handling (partial parse, error reported). Test empty file handling.
- [x] T030 [P] [US1] Create `tests/test_creation_load_order.py` — test `build_creation_list`: merges ContentCatalog + Plugins.txt data correctly, filters to store Creations only (excludes base game ESMs), sets load_position from Plugins.txt order, marks missing files. Test empty Creations scenario. Test no-Plugins.txt scenario.

### Implementation for US1

- [x] T031 [US1] Create `src/starfield_tool/parsers.py` — `parse_plugins_txt(path) -> list[PluginEntry]` (filename, is_active, position), `parse_content_catalog(path) -> list[CatalogEntry]` (content_id, title, author, version, files). Both must handle malformed input gracefully (parse what they can, report errors).
- [x] T032 [US1] Add `build_creation_list(game_install: GameInstallation) -> list[Creation]` function to `src/starfield_tool/parsers.py` (or a new `src/starfield_tool/creation_service.py` if parsers.py gets too large) — cross-references ContentCatalog + Plugins.txt, filters to store Creations only per FR-010, sets load_position, checks file existence in Data dir
- [x] T033 [US1] Create `src/starfield_tool/tools/creation_load_order.py` — `CreationLoadOrderTool(ToolModule)`: name="Creation Load Order", builds UI in content_frame with `ttk.Treeview` table (columns: #, Name, Author, Version), Refresh button calling `build_creation_list` and repopulating table, empty state message "No Creations found", error state for invalid/unreadable files. Use status bar API to report "Reading Creation list from ..." during load.
- [x] T034 [US1] Register `CreationLoadOrderTool` in `src/starfield_tool/tools/__init__.py` MODULES list
- [x] T035 [US1] Add file monitoring to `src/starfield_tool/tools/creation_load_order.py` — use `watchdog` Observer to watch Plugins.txt and ContentCatalog.txt, show "outdated" indicator (label or banner) when files change, clear indicator on Refresh

**Checkpoint**: Full MVP. App launches, detects Starfield, shows Creation load order tab with correct data. Refresh works. Outdated indicator works.

---

## Phase 6: User Story 4 - Check for Creation Updates (Priority: P2)

**Goal**: "Check for Updates" button queries Bethesda's platform for newer versions, highlights outdated Creations, shows "X updates available" summary.

**Independent Test**: Mock HTTP responses with some Creations having newer versions, verify highlighting and count.

### Tests for US4

- [x] T036 [P] [US4] Create `tests/test_version_checker.py` — test `check_for_updates` with mocked HTTP: some Creations have updates, some don't, some fail. Test network error handling (timeout, connection refused). Test version comparison logic. Test that results are ephemeral (not persisted).

### Implementation for US4

- [x] T037 [US4] Create `src/starfield_tool/version_checker.py` — `check_for_updates(creations: list[Creation]) -> list[Creation]` using httpx to query Bethesda's Creations platform. Populate `available_version` and `has_update` on each Creation. Handle network errors gracefully (return unchanged list + error info). Use status bar "Checking Creation X for updates..."
- [x] T038 [US4] Add "Check for Updates" button to `src/starfield_tool/tools/creation_load_order.py` — calls `check_for_updates`, highlights rows with `has_update=True` (change row background color), shows available version next to installed version in a new column or inline, displays "X updates available" summary label in the tab's header area. Handle errors with message display (no crash, list intact per FR-018).

**Checkpoint**: Update check works end-to-end. Highlighted rows and count are accurate.

---

## Phase 7: Polish & Build Infrastructure

**Purpose**: Build tooling, CI/CD, and cross-cutting refinements

- [x] T039 [P] Create `bin/build-win.sh` — accept optional version arg (default "dev"), stamp `_version.py`, install PyInstaller if needed (`uv pip install pyinstaller`), run `pyinstaller --onefile --windowed --name StarfieldToolkit --icon assets/icon.ico --add-data "assets/icon.ico:assets" src/starfield_tool/__main__.py`, output to `build/win/dist/`
- [x] T040 [P] Create `.github/workflows/test.yml` — trigger on PR to main + push to main + workflow_dispatch, `ubuntu-latest` runner (for non-GUI test logic), setup Python 3.12 + uv, `uv sync`, `uv run pytest -v`
- [x] T041 [P] Create `.github/workflows/release-win.yml` — trigger on tag push `[0-9]*`, `windows-latest` runner, setup Python 3.12 + uv, `uv sync`, `make build`, rename exe to `StarfieldToolkit-${GITHUB_REF_NAME}.exe`, create release via `softprops/action-gh-release` with exe attached
- [x] T042 [P] Create proper `assets/icon.ico` — design or source a Starfield-themed application icon in .ico format (16x16, 32x32, 48x48, 256x256 sizes)
- [x] T043 Window geometry persistence — save window size/position to config on close, restore on startup in `src/starfield_tool/app.py`
- [x] T044 Run full test suite (`make test`) and verify all tests pass
- [x] T045 Test PyInstaller build locally (`make build`) and verify the exe launches correctly

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US2+US5 (Phase 3)**: Depends on Foundational (models, base, config)
- **US3 (Phase 4)**: Depends on US2+US5 (needs app shell to integrate startup flow)
- **US1 (Phase 5)**: Depends on US3 (needs game path resolved to read files)
- **US4 (Phase 6)**: Depends on US1 (needs Creation list to check for updates)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US2+US5 (App Shell + Status Bar)**: Can start after Foundational. No dependency on other stories.
- **US3 (Game Detection)**: Depends on US2+US5 (needs the app window and status bar to integrate into)
- **US1 (Creation Load Order)**: Depends on US3 (needs a resolved game path to read files from)
- **US4 (Update Check)**: Depends on US1 (needs the Creation list populated to check versions against)

### Within Each Phase

- Tests MUST be written and FAIL before implementation
- Models/data before services/logic
- Services/logic before UI integration
- Core implementation before polish features (e.g., file monitoring after basic display)

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel (T004-T008)
- All Foundational tests marked [P] can run in parallel (T013-T014)
- All fixture files for US1 can be created in parallel (T026-T028)
- All test files for US1 can be created in parallel (T029-T030)
- All Phase 7 tasks marked [P] can run in parallel (T039-T042)

---

## Implementation Strategy

### MVP First (Through Phase 5)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US2+US5 (App Shell + Status Bar)
4. Complete Phase 4: US3 (Game Detection)
5. Complete Phase 5: US1 (Creation Load Order)
6. **STOP and VALIDATE**: Full MVP is functional — user can see their Creations
7. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Project skeleton ready
2. Add US2+US5 → App window with tabs and status bar (visual shell)
3. Add US3 → Starfield detection works, config persists
4. Add US1 → Creation Load Order displays — **MVP complete**
5. Add US4 → Update checking adds value on top of MVP
6. Add Phase 7 → Build infrastructure, CI/CD, polish

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Tests are MANDATORY per constitution (Principle II: Test Coverage)
- Commit after each task or logical group
- Stop at any checkpoint to validate independently
- US2 and US5 are combined into one phase because the status bar is structurally part of the app shell
