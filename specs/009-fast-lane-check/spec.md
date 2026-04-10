# Feature Specification: Fast Lane Creation Check

**Feature Branch**: `009-fast-lane-check`  
**Created**: 2026-04-10  
**Status**: Draft  
**Input**: User description: "Implement a feature to check if a creation has been updated since the Fast Lanes release. Separate tool working off currently installed creations or an exported list. Tool named 'Fast lane creation check'. Uses a trimmed down version of the scraped creations catalog. Compares available version against local catalog; a newer version means updated. Creations with no newer version are highlighted. Always-visible warning stating this is not 100% reliable with short explanation of the detection method."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Check Installed Creations Against Baseline (Priority: P1)

A user has installed a set of creations on their machine. The Starfield Fast Lanes update has been released and broken many mods. The user opens the "Fast Lane Creation Check" tab and sees an empty state with a prominent warning banner and two large buttons centered below it: "Import Installed" and "Import from File". They click "Import Installed", and the buttons are replaced by the familiar creation list grid showing all installed creations. They then click the "Check" button at the top of the grid — the tool reads the existing creations cache (populated by the Installed Creations tab's "Check for Updates") and compares each creation's current available version against the bundled baseline snapshot. Creations where no newer version exists (meaning the author hasn't published an update since the baseline) are highlighted as potentially incompatible with Fast Lanes. The warning banner remains visible at all times.

**Why this priority**: This is the core use case — identifying which installed creations might be broken by the Fast Lanes update, so users can troubleshoot load order issues or disable problematic mods proactively.

**Independent Test**: Can be fully tested by opening the tab, clicking "Import Installed", clicking "Check", and verifying that creations known to be outdated are highlighted while recently-updated ones are not.

**Acceptance Scenarios**:

1. **Given** the user has installed creations and the baseline catalog is bundled, **When** the user opens the Fast Lane Creation Check tab, **Then** an empty state is shown with the warning banner and two buttons ("Import Installed", "Import from File") centered below it.
2. **Given** the tab is in empty state, **When** the user clicks "Import Installed", **Then** the installed creations are loaded and displayed in the grid, and the two import buttons are replaced by "Reset" and "Check" action buttons.
3. **Given** the grid is populated with installed creations, **When** the user clicks "Check", **Then** the tool uses the existing creations cache to get current versions and compares them against the baseline, updating the grid with baseline version, current version, and status columns.
4. **Given** a creation's current available version is newer than the baseline, **When** the comparison runs, **Then** that creation is marked as "updated since baseline" and NOT highlighted.
5. **Given** a creation's current version matches the baseline version (no update has been published), **When** the comparison runs, **Then** that creation is highlighted as "not updated since baseline".
6. **Given** a creation is installed but NOT present in the baseline catalog, **When** the comparison runs, **Then** the creation is shown with an "unknown" status (not enough data to compare).
7. **Given** the user has loaded data and run a check, **When** they click "Reset", **Then** the state is cleared and the tab returns to the empty state with the two import buttons visible.
8. **Given** the user is in any state (empty or loaded), **When** the tab is visible, **Then** a prominent warning banner is shown at the top explaining the approximate nature of the check and the detection method.

---

### User Story 2 - Check Exported Creation List (Priority: P2)

A user has previously exported their installed creations list from the Installed Creations tab (perhaps from another machine, or a friend's export they are helping troubleshoot). They open the Fast Lane Creation Check tab, see the empty state, and click "Import from File". A file picker opens; they select the exported CSV or Markdown file, and the list populates the grid. They click "Check" to run the baseline comparison — the tool uses the installed version values from the file as the comparison source (since no live creations cache exists for someone else's install). The comparison logic is otherwise identical to the live installed check.

**Why this priority**: Enables offline analysis, helping friends without requiring direct game access, and supports scenarios where the user wants to plan updates before installing.

**Independent Test**: Can be tested by exporting a list from the Installed Creations tab, clicking "Import from File" in Fast Lane Check, selecting the file, clicking "Check", and verifying the comparison runs correctly against the baseline.

**Acceptance Scenarios**:

1. **Given** the user has an exported list file, **When** they click "Import from File" and select it, **Then** the list is parsed and displayed in the grid, with the Reset and Check buttons now visible.
2. **Given** the exported file format is invalid or corrupted, **When** the user imports it, **Then** a clear error message is shown and the tab remains in the empty state.
3. **Given** the imported file is from a legacy export (no Content ID column), **When** the list loads, **Then** a warning is shown explaining that matching will use Name + Author as fallback.
4. **Given** the user has loaded from a file and wants to switch sources, **When** they click "Reset" and then "Import Installed", **Then** the current state is cleared and the installed creations are loaded fresh.

---

### User Story 3 - Baseline Metadata Visibility (Priority: P3)

A user wants to know how old the baseline catalog is and when it was taken. The tool displays the baseline snapshot date prominently alongside the warning banner, so the user understands how much time has passed since the reference point.

**Why this priority**: Transparency about the reference data builds trust and helps users judge the reliability of results (older baselines have more drift).

**Independent Test**: Can be tested by viewing the tab and confirming the baseline date and version count are visible.

**Acceptance Scenarios**:

1. **Given** the bundled baseline has a snapshot date, **When** the user views the tab, **Then** the date is displayed (e.g., "Baseline snapshot: 2026-04-06") along with the count of creations in the baseline.

---

### Edge Cases

- What happens when the baseline catalog is missing from the app bundle? The tool displays an error message explaining that the baseline is unavailable and disables the check.
- What happens when a creation has no version information (empty or "unknown")? That creation is shown with "unknown" status and excluded from the "not updated" highlighting.
- What happens when version strings are non-semantic (e.g., "1.0a" vs "1.0.1")? The comparison uses the existing version comparison logic from the load order sorter, which handles mixed formats.
- What happens when a creation in the baseline is no longer installed? It is not shown — only installed creations are checked.
- What happens when the user imports an exported list from a different game version or tool version? Best-effort parsing: compatible fields are used, incompatible fields are ignored with a warning.
- What happens when many creations (hundreds) are shown? The list supports scrolling and sorting by status (highlighted first) for easy review.
- What happens when the "current available version" cannot be determined because the creations cache is empty and no network is available? The tool shows "no data" for those entries and prompts the user to run "Check for Updates" in the Installed Creations tab first.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a new tab named "Fast Lane Creation Check" in the main application.
- **FR-002**: Tool MUST display a prominent, always-visible warning banner at the top of the tab (in both empty and loaded states) stating:
    - This check is approximate and not 100% reliable
    - How the detection works (comparison against a baseline snapshot taken at a specific date)
    - The baseline snapshot date, so users understand how stale the reference is
    - Recommendation to run "Check for Updates" in the Installed Creations tab first for best accuracy
- **FR-003**: On tab open, tool MUST show an empty state with the warning banner and two large centered buttons below: "Import Installed" and "Import from File". No data is loaded and no comparison runs automatically.
- **FR-004**: "Import Installed" button MUST load the currently installed creations from the game installation (same source as the Installed Creations tab) and display them in the grid.
- **FR-005**: "Import from File" button MUST open a file picker that accepts CSV and Markdown exports produced by the Installed Creations tab, parse the selected file, and display the parsed creations in the grid.
- **FR-006**: When data is loaded (by either import action), the import buttons MUST be replaced by two action buttons at the top of the grid: "Reset" and "Check".
- **FR-007**: "Reset" button MUST clear the loaded data and return the tab to the empty state.
- **FR-008**: "Check" button MUST run the baseline comparison on the currently loaded data. In installed mode, the check uses the shared creations client (same path as the Installed Creations tab's "Check for Updates") to obtain current version data — this respects the session-fresh window (no API calls if the cache is fresh within the current session) and re-fetches from the Bethesda API when the cache is stale or missing. In file mode (US2), no API calls are made — the exported installed_version is used as the current version.
- **FR-009**: Tool MUST include a bundled baseline catalog file — a trimmed version of the full creations catalog containing only the minimum data needed for version comparison (content_id, title, author, version, and snapshot timestamp).
- **FR-010**: For each creation in the loaded list, the Check action MUST look it up in the baseline catalog by content_id (preferred) or by title+author (fallback for legacy exports) and compare the current version against the baseline version.
- **FR-011**: The "current version" source depends on the input mode:
    - **Import Installed**: fetched via the shared creations client (same session-fresh + API refresh rules as the Installed Creations tab). If an API call is needed, it runs in a background thread so the UI stays responsive; a status bar message indicates progress. If a creation has no available version after the fetch, the row is classified as "unknown".
    - **Import from File**: use the installed version from the file row as the current version (no API calls, since the file represents someone else's install)
- **FR-012**: A creation MUST be classified as:
    - **Updated since baseline**: current version > baseline version
    - **Not updated since baseline**: current version equals the baseline version (highlighted)
    - **Unknown**: creation not present in baseline, OR no current version data available
- **FR-013**: Tool MUST visually highlight creations classified as "not updated since baseline" using a consistent warning style (distinct background or marker).
- **FR-014**: Tool MUST NOT modify the load order or make any changes to installed files — it is read-only.
- **FR-015**: Tool MUST provide a summary showing the total count of creations in each status category (updated / not updated / unknown) after the Check action completes.
- **FR-016**: Version comparison MUST reuse the existing version comparison logic from the load order sorter to handle non-semantic versions consistently.
- **FR-017**: The baseline catalog MUST be bundled with the application distribution and regeneratable as a developer task (not a user-facing operation).
- **FR-018**: The tool MUST display the baseline snapshot date alongside the warning banner, so users can judge the freshness of the reference.
- **FR-019**: Results MUST be sortable by status (highlighted "not updated" first) to help users focus on potentially broken creations.
- **FR-020**: The Installed Creations tab export (both CSV and Markdown formats) MUST include the `content_id` column so that Fast Lane Check can reliably match exported rows to baseline entries by UUID without title/author heuristics. The new column is added as the second column (after `#`) and named "Content ID". The column `Version` is renamed to `Installed Version` for clarity.
- **FR-021**: The Fast Lane Check import parser MUST accept both new-format exports (with `Content ID` column) and legacy exports (without `Content ID`, matching by `Name` and `Author` as a fallback). The parser MUST show a warning when importing a legacy export so users know matching is less reliable.

### Key Entities

- **Baseline Catalog**: A trimmed-down version of the full creations catalog, containing only fields necessary for version comparison: `content_id`, `title`, `version`, and a global `snapshot_date`. Bundled with the app distribution.
- **Creation Check Result**: One row per input creation, containing: title, content_id, baseline version (or "not in baseline"), current version (or "unknown"), status (updated / not updated / unknown), and a visual highlight flag.
- **Exported Creation List**: A file produced by the Installed Creations tab's Export action. The format is updated by this feature to include a `Content ID` column alongside the existing `Name`, `Author`, and `Installed Version` columns. Fast Lane Check uses the file as an alternative input source — matching by content_id when present, falling back to title+author for legacy exports.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can complete the full flow (open tab → Import Installed → Check) and see which creations have not been updated in under 5 seconds of clicking the Check button (assuming cached version data exists).
- **SC-002**: The baseline catalog adds less than 600 KB to the app distribution size (achieved via compact JSON with short keys: ~520 KB for ~5,000 entries).
- **SC-003**: The warning banner is visible at all times the tab is open and explains the detection method in under 100 words.
- **SC-004**: At least 90% of installed creations in the baseline receive a definitive "updated" or "not updated" classification (under 10% "unknown" rate for users running up-to-date "Check for Updates").
- **SC-005**: Users understand the tool is approximate and not a substitute for manual verification (verified through the mandatory warning banner presence).

## Assumptions

- The existing creations catalogue scraper (feature 005) will be extended or a companion script will be added to generate the trimmed baseline catalog on demand (developer task, not end-user task).
- The baseline catalog is a static snapshot bundled with the app — it does NOT auto-update at runtime.
- "Current available version" data comes from the existing creations cache populated by the Installed Creations tab's "Check for Updates" feature (feature 001/002). No new API calls are made by this tool.
- The exported list file format is the same as the export produced by the Installed Creations tab (no new format is required).
- Fast Lanes refers to the Starfield update planned for April 7, 2026. The baseline snapshot is taken shortly before that date.
- The comparison is not perfect — some creations may have been updated with fixes not yet published, or may have been updated in ways that don't bump the version number. The warning banner makes this clear to users.
- The tool is purely informational — it does not block, disable, or modify any creations.
- The baseline catalog file location follows the existing bundled-data pattern (`sys._MEIPASS/data/` for PyInstaller, `data/` for dev mode).
