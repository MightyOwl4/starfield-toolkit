# Feature Specification: Starfield Tabbed GUI Toolbox

**Feature Branch**: `001-starfield-tabbed-toolbox`
**Created**: 2026-03-28
**Status**: Draft
**Input**: User description: "I need a GUI application to host various potentially unrelated tools related to Bethesda's game Starfield. The UI needs to be organized in tabs - one per tool. Adding new tabs/tools should be easy and not requiring modifying a lot of code. First tool will list all installed creations from bethesda's store in their loading order, inspecting the game folder to get that information"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Installed Creations in Load Order (Priority: P1)

A Starfield player wants to see which Creations (from Bethesda's Creation store) are currently installed in their game, displayed in the order they are loaded. The user launches the application, and the Creation Load Order tab shows a list of all installed Creations read from the game's data files. Each entry shows at minimum the plugin filename and its position in the load order. The user can quickly confirm which Creations are active and in what order they load.

**Why this priority**: This is the first and only concrete tool requested. It delivers immediate value by letting players inspect their creation setup without manually reading config files.

**Independent Test**: Can be fully tested by pointing the application at a Starfield game folder (or a test folder mimicking its structure) and verifying the correct list of creations appears in the correct load order.

**Acceptance Scenarios**:

1. **Given** a valid Starfield game installation with Creations installed, **When** the user launches the application and opens the Creation Load Order tab, **Then** all installed Creations are listed in their load order with plugin filenames visible.
2. **Given** a Starfield installation with no Creations installed, **When** the user opens the Creation Load Order tab, **Then** the tab displays a clear message indicating no Creations were found.
3. **Given** the configured game folder path does not exist or is invalid, **When** the application tries to read creation data, **Then** a clear error message is shown explaining the path is invalid and how to configure it.

---

### User Story 2 - Tabbed Tool Shell (Priority: P1)

A user launches the application and sees a tabbed interface. Each tab hosts a different tool. The application starts with at least the Creation Load Order tab. The tab layout is the foundation that all future tools will plug into.

**Why this priority**: Equal to P1 because the tabbed shell is the structural prerequisite — without it, no tool can be displayed. It is co-dependent with User Story 1.

**Independent Test**: Can be tested by verifying the application launches, displays a tab bar, and tabs are selectable. Adding a new dummy tab requires only a minimal code change (creating one new component/module and registering it).

**Acceptance Scenarios**:

1. **Given** the application is installed, **When** the user launches it, **Then** a window appears with a tab bar containing at least one tab (Creation Load Order).
2. **Given** the application is running, **When** the user clicks a tab, **Then** the corresponding tool's content is displayed in the main area.
3. **Given** a developer wants to add a new tool, **When** they create a new tab module, **Then** they only need to register it in one place (a single list or config) to make it appear in the tab bar.

---

### User Story 3 - Startup Game Detection & Configuration (Priority: P1)

On startup, the application checks its config file (`%APPDATA%/StarfieldToolkit/config.json`). If a game path is already stored, the app validates that path and initializes modules directly — skipping auto-detection entirely. Only when no config file exists (first launch) does the app run the full Steam auto-detection flow. If auto-detection fails, a file browser dialog prompts the user to manually point to the install directory. If the user cancels, the skeleton app launches with tabs visible but uninitialized, showing a "Starfield not found" warning in each tab's content area with buttons to browse manually or retry auto-detection. Any successfully detected or manually set path is immediately saved to the config file.

**Why this priority**: Elevated to P1 because module initialization depends on a verified game path. This is a prerequisite for all tool functionality.

**Independent Test**: Can be tested by: (1) launching with no config file → auto-detect flow, (2) launching with valid config → fast path, (3) launching with stale config (path no longer valid) → re-prompt flow.

**Acceptance Scenarios**:

1. **Given** the config file exists with a valid game path, **When** the application starts, **Then** it validates the stored path and initializes modules without auto-detection or prompting.
2. **Given** the config file exists but the stored path is no longer valid, **When** the application starts, **Then** it shows a file browser dialog to re-select the path (and falls through to the "not found" skeleton if cancelled).
3. **Given** no config file exists and Steam has Starfield installed, **When** the application starts, **Then** it auto-detects the Starfield folder from Steam library locations, saves the path to config, and initializes modules.
4. **Given** no config file exists and auto-detection fails, **When** the application starts, **Then** a file browser dialog appears prompting the user to select the install directory.
5. **Given** the user cancels the file browser dialog, **When** the skeleton app loads, **Then** all tabs are visible but uninitialized. Each tab's content area shows a "Starfield not found" warning with buttons to browse manually or retry auto-detection.
6. **Given** the user provides a valid path (via dialog or in-tab button), **When** the path is verified, **Then** it is saved to the config file and modules initialize immediately.

---

### User Story 4 - Check for Creation Updates (Priority: P2)

A user wants to know if any of their installed Creations have newer versions available. They click a "Check for Updates" button on the Creation Load Order tab. The application checks for newer versions and, if updates are found, highlights the affected Creations in the list showing the new version next to the current one. A summary message "X updates available" is displayed in the tab's general area.

**Why this priority**: Adds significant value on top of the load order view (P1) but is not required for the core display to be useful. Depends on User Story 1 being complete.

**Independent Test**: Can be tested by providing a mock data source where some Creations have newer versions than what is locally installed, clicking the check button, and verifying the correct entries are highlighted with version info and the summary count is accurate.

**Acceptance Scenarios**:

1. **Given** installed Creations are displayed, **When** the user clicks "Check for Updates", **Then** the application checks for newer versions and highlights Creations that have updates, showing the available version next to the installed version.
2. **Given** updates are found for some Creations, **When** the check completes, **Then** a summary message "X updates available" is displayed in the tab's general area.
3. **Given** no updates are available, **When** the check completes, **Then** the application indicates all Creations are up to date.
4. **Given** the update check fails (network error, service unavailable), **When** the check completes, **Then** a clear error message is shown without disrupting the existing list display.

---

### User Story 5 - Status Bar (Priority: P1)

The application displays a persistent status bar at the bottom of the window with two segments: (1) the configured Starfield install location, or a warning if the path is unknown/invalid; (2) a human-readable description of the currently executing task (e.g., "Reading ESM list from C:/Games/Starfield/Data/...", "Checking Creation X for updates..."). The status bar API is available to all tool modules so any tab can report its activity.

**Why this priority**: P1 because it provides essential feedback for every operation across all tools. Without it, users have no visibility into what the application is doing during file reads or network requests.

**Independent Test**: Can be tested by verifying the status bar renders both segments on launch, shows the correct game path (or warning), and updates the task segment when any operation starts and clears it when done.

**Acceptance Scenarios**:

1. **Given** a valid game path is configured, **When** the application is running, **Then** the status bar's first segment displays the Starfield install path.
2. **Given** no game path is configured or the path is invalid, **When** the application is running, **Then** the status bar's first segment displays a warning (e.g., "Starfield path not set").
3. **Given** a tool module is performing an operation, **When** the operation starts, **Then** the status bar's second segment shows a human-readable task description. When the operation completes, the segment clears or shows "Ready".
4. **Given** a developer is building a new tool tab, **When** they need to report activity, **Then** they can use the status bar API to set/clear the current task message without modifying the status bar code.

---

### Edge Cases

- What happens when Starfield game files are being updated by Steam/Xbox while the application reads them? → Display whatever was read successfully; if a file is locked, show an error for that file only.
- What happens when the Plugins.txt or ContentCatalog.txt files are malformed or partially written? → Show a clear error message identifying which file is malformed; display whatever valid entries were parsed.
- How does the application behave when the user has multiple Steam library folders? → Auto-detection scans all local Steam library locations and picks the first valid Starfield installation found; user can override via manual path selection.
- What happens when creation plugin files (.esm/.esp/.esl) referenced in load order files are missing from the Data folder? → Show the entry in the list but mark it as "missing" so the user is aware of the inconsistency.
- What happens if the update check is slow or times out? → Show a loading indicator during the check; if it times out, display an error without losing the current list state.
- What happens if version comparison is ambiguous (non-standard version formats)? → Compare version strings as reported; if comparison is not possible, skip that Creation for update detection.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Application MUST display a tabbed interface where each tab hosts an independent tool.
- **FR-002**: Adding a new tool tab MUST require creating only one new module and registering it in a single location (no multi-file scaffolding).
- **FR-002a**: Every tool module MUST implement a common interface. The interface MUST require: a short name (displayed on the tab), and a description (accessible to the bootstrapper).
- **FR-002b**: The bootstrapper MUST pass each module all app requisites upon initialization: the detected game/data locations (as a structured model), the status bar API, and the content area with its modification API.
- **FR-002c**: Future scope: the application architecture MUST accommodate a later addition of external (user-installed) modules that are auto-detected and bootstrapped alongside built-in modules. This does not need to be implemented now but MUST NOT be precluded by the design.
- **FR-003**: Application MUST read the Starfield Plugins.txt file to determine creation load order.
- **FR-004**: Application MUST scan the Starfield Data folder to identify installed Creation plugin files (.esm, .esp, .esl).
- **FR-005**: Application MUST display installed Creations in their load order. Each entry MUST show: load position (as leading number), full Creation name (as listed on Bethesda's site), author, and version.
- **FR-006**: Application MUST allow the user to configure the Starfield game folder path.
- **FR-007**: Application MUST persist the game folder path and other settings in a config file at `%APPDATA%/StarfieldToolkit/config.json`.
- **FR-008**: On startup, application MUST first check the config file for a stored game path. If found, validate it and initialize modules directly (no auto-detection).
- **FR-008a**: Only when no config file exists (or no game path is stored) MUST the application run Steam auto-detection by scanning all local Steam library locations.
- **FR-008b**: If auto-detection fails, application MUST show a file browser dialog for the user to manually select the install directory.
- **FR-008c**: If the user cancels the file browser, the skeleton app MUST still launch with tabs visible but uninitialized. Each tab's content area MUST display a prominent "Starfield not found" warning with buttons to browse manually or retry auto-detection.
- **FR-008d**: Tool modules MUST NOT initialize until a valid Starfield game path is verified by the skeleton app.
- **FR-008e**: Once a valid path is provided (by any method), it MUST be saved to the config file immediately and modules MUST initialize without requiring a restart.
- **FR-008f**: If the config file contains a path that is no longer valid (e.g., game was uninstalled/moved), the application MUST treat it as if no path is stored and re-prompt the user.
- **FR-009**: Application MUST display clear error messages when the game folder is invalid or creation data cannot be read.
- **FR-010**: Application MUST show only Creations from Bethesda's Creation store, excluding base game ESMs and sideloaded mods. The ContentCatalog.txt file MUST be used to identify which plugins are store Creations.
- **FR-011**: The Creation Load Order display MUST be a static snapshot rendered at load time. No auto-refresh.
- **FR-012**: The Creation Load Order tab MUST include a "Refresh" button that re-reads game files and updates the display.
- **FR-013**: Application MUST monitor Plugins.txt and ContentCatalog.txt for changes and display an "outdated" indicator when the displayed data no longer reflects the current file contents.
- **FR-014**: The Creation Load Order tab MUST include a "Check for Updates" button that checks whether newer versions exist for installed Creations. This is a manual action only — no automatic checking.
- **FR-015**: When updates are found, affected Creations MUST be visually highlighted in the list, with the available version displayed next to the installed version.
- **FR-016**: When updates are found, a summary message "X updates available" MUST be displayed in the tab's general information area.
- **FR-017**: When no updates are found, the application MUST indicate that all Creations are up to date.
- **FR-018**: If the update check fails, the application MUST show a clear error without disrupting the existing Creation list display.
- **FR-019**: Application MUST display a persistent status bar at the bottom of the window with two segments: (1) Starfield install location or a warning if unknown/invalid, and (2) current task description.
- **FR-020**: The status bar's task segment MUST show human-readable descriptions of in-progress operations (e.g., "Reading ESM list from .../Data/", "Checking X for updates...") and clear to "Ready" when idle.
- **FR-021**: The status bar MUST expose an API available to all tool modules, allowing any tab to report its current activity without modifying status bar code.

### Key Entities

- **Creation**: A plugin file from Bethesda's Creation store installed in the game's Data folder. Has a filename, load order position, file type (.esm/.esp/.esl), display name, author, and version (sourced from ContentCatalog.txt).
- **Load Order**: The sequence in which the game loads plugin files, as defined in Plugins.txt. Determines which content takes precedence in case of conflicts.
- **Game Installation**: The root folder of a Starfield installation containing the Data subfolder with plugin files and configuration.
- **Status Bar**: Persistent UI component at the bottom of the window. Two segments: install location and current task. Provides a shared API for all tool modules to report activity.
- **Tool Module**: A self-contained unit implementing the common module interface. Provides a short name and description. Receives app requisites (game locations model, status bar API, content area API) from the bootstrapper at initialization.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can view their complete Creation load order within 3 seconds of opening the tab.
- **SC-002**: A developer can add a new tool tab by modifying no more than 2 files (the new tool module + one registration point).
- **SC-003**: Application correctly detects Starfield installation across all local Steam library locations on first launch for 90%+ of users with Steam installations.
- **SC-004**: All installed Creations are listed with 100% accuracy compared to manually inspecting the game files.
- **SC-005**: Application handles missing or malformed game data gracefully — no crashes, always a user-friendly message.

## Clarifications

### Session 2026-03-28

- Q: Should data displays auto-refresh or be static? → A: All informational displays are static snapshots, valid at the time of rendering. No live/auto-refresh.
- Q: How does the user refresh stale data? → A: An explicit "Refresh" button on the Creation Load Order tab triggers a re-read of game files.
- Q: How is staleness communicated? → A: The application monitors relevant files (Plugins.txt, ContentCatalog.txt) for changes and displays an "outdated" indicator when the on-screen data no longer matches the files on disk.
- Q: What metadata to show per Creation? → A: Load position (leading number), full Creation name (as per Bethesda site), author, and version.
- Q: Version check trigger model? → A: Manual only — explicit "Check for Updates" button. Highlights outdated Creations, shows new version next to current, displays "X updates available" summary.
- Q: Where does latest version info come from? → A: Query Bethesda's Creations platform online (web scraping or API if available).
- Q: Should update check results persist across sessions? → A: No — update status is ephemeral, lost on refresh or app restart. No caching.
- Q: Status bar design? → A: Two-segment persistent bar: (1) Starfield install path or warning if unknown, (2) current task description, human-readable. API available to all modules.
- Q: Startup game detection flow? → A: Auto-detect from Steam library locations on startup. If fails, show file browser dialog. If cancelled, skeleton app shows tabs but content areas display "Starfield not found" warning with browse and auto-detect buttons. Modules only initialize after valid path is verified.
- Q: Which install sources does auto-detection cover? → A: Steam only. Scans all local Steam library locations.
- Q: Module interface contract? → A: Common interface required. Each module provides short name (tab label) and description. Bootstrapper passes app requisites: game locations model, status bar API, content area API. Design must not preclude future external module support.
- Q: Startup flow optimization? → A: Config file at `%APPDATA%/StarfieldToolkit/config.json` stores game path. On startup: if config has path → validate and init (skip auto-detection). Only run full Steam scan on first launch or when config path is invalid/missing.

## Assumptions

- Users are running Starfield on Windows (the game is Windows-only for PC).
- The Starfield Plugins.txt file is located in `%LOCALAPPDATA%\Starfield\` following Bethesda's standard convention.
- The game's Data folder contains the Creation plugin files and ContentCatalog.txt for store metadata.
- The application runs locally on the same machine where Starfield is installed.
- Users have read access to the game folder and local app data folder.
- The application does not modify any game files — it is read-only.
- Internet connectivity is available when the user chooses to check for updates (not required for core functionality).
- Bethesda's Creations platform exposes version information accessible via web scraping or API.
