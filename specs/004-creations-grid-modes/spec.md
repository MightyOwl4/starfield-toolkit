# Feature Specification: Creations Grid Modes & Details Dialog

**Feature Branch**: `004-creations-grid-modes`  
**Created**: 2026-04-01  
**Status**: Draft  
**Input**: User description: "Enhanced installed creations tab with two grid modes (text list and rich media), author column from cache, thumbnail display, loading placeholders, and a reusable creation details dialog."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Text List Mode with Author Column (Priority: P1)

A user viewing the installed creations tab sees the familiar text list with an additional "Author" column. If cached data is available (even if not considered fresh), the author name appears. If no cache exists, the column shows "n/a". Viewing the text list never triggers a cache fetch.

**Why this priority**: This is the lowest-risk enhancement — it augments the existing view without requiring network activity and provides immediate value to users who have previously fetched cache data.

**Independent Test**: Can be tested by viewing the installed creations tab with and without a populated cache file on disk. Delivers author attribution at a glance without any loading delay.

**Acceptance Scenarios**:

1. **Given** the cache file contains entries for installed creations, **When** the user views the text list mode, **Then** the "Author" column displays the cached author name for each matching creation.
2. **Given** the cache file does not exist or has no entries for a creation, **When** the user views the text list mode, **Then** the "Author" column displays "n/a" for that creation.
3. **Given** the cache file exists but the session is not fresh (stale cache), **When** the user views the text list mode, **Then** the "Author" column still displays the cached author name (no freshness requirement for author data).
4. **Given** the user is in text list mode, **When** the tab loads or refreshes, **Then** no network request is triggered to populate the author column.

---

### User Story 2 - Rich Media Grid Mode (Priority: P2)

A user switches from text list to rich media mode using a toggle control. The rich media grid displays a thumbnail image (approximately 3 text rows tall), the creation name in bold on the first line, and a description excerpt underneath that fills the available space without expanding the row height. The remaining columns from the text list are preserved.

**Why this priority**: This is the signature visual enhancement that makes the creations tab far more informative and visually appealing, but it depends on cache data and network fetching.

**Independent Test**: Can be tested by toggling to rich media mode and verifying that thumbnails, bold names, and description excerpts render correctly with cached data present.

**Acceptance Scenarios**:

1. **Given** the user is in text list mode, **When** they switch to rich media mode and cache data is available, **Then** each row shows: thumbnail image (~3 line heights tall), creation name in bold, description excerpt below the name, plus the remaining standard columns.
2. **Given** the user switches to rich media mode and the cache is cold (no data), **When** the mode switch occurs, **Then** a cache fetch is triggered automatically.
3. **Given** a cache fetch is in progress after switching to rich media mode, **When** data is not yet available, **Then** placeholder content is displayed for thumbnails (gray box or spinner), name (placeholder text), and description (placeholder text).
4. **Given** the cache fetch completes, **When** data arrives, **Then** the placeholders are replaced with actual thumbnails, names, and descriptions.
5. **Given** the description text is longer than the available space in the row, **When** the row renders, **Then** the description is truncated to fit without increasing the row height.

---

### User Story 3 - Creation Details Dialog (Priority: P2)

A user clicks a "Details" button on any creation row (in either grid mode) and a dialog opens showing the full creation details available in the cache, including title, author, description, version, price, installation size, categories, achievement friendliness, creation date, and last updated date.

**Why this priority**: Tied with rich media mode — the details dialog provides deep-dive information and is designed as a reusable component for use across the application.

**Independent Test**: Can be tested by clicking the details button on any creation row and verifying the dialog displays all cached fields correctly, is visible in the OS taskbar/alt-tab order, and can be closed without affecting the main window.

**Acceptance Scenarios**:

1. **Given** the user clicks the "Details" button on a creation row, **When** cached data exists for that creation, **Then** a dialog opens displaying all available cached fields (title, author, description, version, price, installation size, categories, achievement friendliness, creation date, last updated date, thumbnail).
2. **Given** the details dialog is open, **When** the user presses Alt+Tab or uses the OS task switcher, **Then** the dialog appears as a separate window in the task order (not hidden behind the main window).
3. **Given** the details dialog is open, **When** the user closes it, **Then** focus returns to the main application window and no state is lost.
4. **Given** cached data is missing for some fields, **When** the dialog opens, **Then** missing fields display "n/a" or are omitted gracefully.
5. **Given** the details dialog component is invoked from a different part of the UI (not the installed creations tab), **When** it receives a creation identifier and cached data, **Then** it displays the same details view correctly (the dialog is decoupled from the creations tab).

---

### User Story 4 - Mode Switching and Persistence (Priority: P3)

A user can toggle between text list and rich media modes. The toggle is clearly visible and the current mode is visually indicated. The selected mode is remembered for the duration of the session.

**Why this priority**: Supporting feature that enhances usability of the two grid modes but is not core functionality.

**Independent Test**: Can be tested by switching modes back and forth and verifying the grid updates correctly each time.

**Acceptance Scenarios**:

1. **Given** the user is in text list mode, **When** they click the mode toggle, **Then** the grid switches to rich media mode.
2. **Given** the user is in rich media mode, **When** they click the mode toggle, **Then** the grid switches back to text list mode.
3. **Given** the user switches modes, **When** the grid redraws, **Then** all creation data is preserved (no data loss on mode switch).

---

### Edge Cases

- What happens when the thumbnail URL in the cache is invalid or the image fails to download? The thumbnail area should display a fallback placeholder image.
- What happens when a creation has no description in the cache? The description area in rich media mode should remain blank (no placeholder text needed).
- What happens when the cache fetch fails due to network error while switching to rich media mode? The loading placeholders should be replaced with an error indicator or remain as placeholders, and the user should be informed via the status bar.
- What happens when the user rapidly toggles between modes while a cache fetch is in progress? The fetch should complete and the grid should reflect the final selected mode.
- What happens when the user clears the cache while in rich media mode? The view should immediately reset to loading placeholders and trigger a fresh cache fetch.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide two grid display modes for the installed creations tab: "text list" and "rich media."
- **FR-002**: System MUST display a mode toggle control in the installed creations tab that allows switching between the two modes.
- **FR-003**: In text list mode, the grid MUST include an "Author" column populated from cached data. If cache data is unavailable, the column MUST display "n/a."
- **FR-004**: In text list mode, author data MUST be read from the cache regardless of cache freshness (stale cache is acceptable for author data).
- **FR-005**: In text list mode, viewing the grid MUST NOT trigger a cache fetch or network request.
- **FR-006**: In rich media mode, each row MUST display a thumbnail image at approximately 3 text line heights.
- **FR-007**: In rich media mode, each row MUST display the creation name in bold, with a description excerpt underneath that does not expand the row height.
- **FR-008**: In rich media mode, the remaining columns from text list mode MUST be preserved.
- **FR-009**: Switching to rich media mode MUST trigger a cache fetch if the cache is cold (no data available).
- **FR-010**: While cache data is loading in rich media mode, the grid MUST display loading placeholders for thumbnail, name, and description fields.
- **FR-011**: Both grid modes MUST include a "Details" button on each creation row.
- **FR-012**: The "Details" button MUST open a dialog displaying all cached creation fields: title, author, description, version, price, installation size, categories, achievement friendliness, thumbnail, creation date, and last updated date.
- **FR-013**: The details dialog MUST appear as a separate window in the OS task switcher (Alt+Tab), following the same windowing pattern as the existing diff dialog.
- **FR-014**: The details dialog MUST be a decoupled, reusable component that can be invoked from any part of the UI with a creation identifier and cached data.
- **FR-015**: When cached fields are missing, the details dialog MUST display "n/a" or gracefully omit the field.

### Key Entities

- **Creation**: An installed Bethesda Creation with local metadata (name, version, date, load position) and optional cached remote metadata (author, description, thumbnail, price, categories, etc.).
- **Cache Entry**: A stored record of creation metadata fetched from the Bethesda API, keyed by content ID, with a freshness timestamp.
- **Grid Mode**: The current display style of the installed creations list — either "text list" (compact, text-only) or "rich media" (thumbnails and formatted text).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can see the author of each creation at a glance in text list mode without triggering any network activity, whenever cached data exists.
- **SC-002**: Users can switch to rich media mode and see thumbnails and description excerpts for all creations within the normal cache fetch time.
- **SC-003**: Users can access full creation details (including price) for any creation in two clicks or fewer (click Details button, view dialog).
- **SC-004**: The details dialog is reachable via OS task switcher (Alt+Tab) and keyboard navigation.
- **SC-005**: Switching between grid modes completes visually within 1 second when cache data is already available.
- **SC-006**: The details dialog component can be instantiated from any UI context by passing a creation identifier and data, with no dependency on the installed creations tab.

## Assumptions

- The existing cache file structure and fields (author, description, thumbnail_url, price, etc.) are sufficient for all display needs — no new API calls or cache schema changes are required.
- Thumbnail images are fetched from the URL stored in the cache at display time; image downloading and caching is a new concern handled within the rich media mode implementation.
- The default grid mode when the tab first loads is "text list" to avoid forcing a cache fetch on startup.
- The mode toggle state is session-scoped (not persisted to disk across app restarts).
- The details dialog follows the same windowing pattern as the existing diff dialog (non-modal, no focus grab, topmost toggling for OS task order visibility).
- Price is displayed as "Free" when the value is 0, and as a numeric credits value otherwise.
