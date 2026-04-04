# Feature Specification: Creations API Response Caching

**Feature Branch**: `002-creations-cache`
**Created**: 2026-03-29
**Status**: Draft
**Input**: User description: "Implement caching of Bethesda Creations API responses to reduce overhead especially for larger lists. Cache immutable data permanently and volatile data with session-scoped staleness window. Per-creation update timestamps. Explicit cache clear option."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cached Checks Complete Faster (Priority: P1)

A user with 20+ installed Creations clicks "Check for Updates" or "Check Achievements". Instead of making 20+ API calls every time, the tool reuses cached responses for Creations whose data was fetched recently (within the current session window). Only Creations with stale or missing cache entries are fetched from the API.

**Why this priority**: This is the core value proposition. Large Creation lists currently require many sequential API calls, making checks slow and rate-limit-prone. Caching eliminates most of this overhead.

**Independent Test**: Install 5+ Creations, run "Check for Updates" twice within 30 minutes. The second check should complete near-instantly using cached data.

**Acceptance Scenarios**:

1. **Given** a user runs "Check for Updates" for the first time, **When** no cache exists, **Then** all Creations are fetched from the API and results are cached to disk.
2. **Given** a user runs "Check for Updates" again within the session window (30 minutes from app start), **When** cached data exists for a Creation, **Then** the cached response is used without an API call.
3. **Given** a user runs "Check Achievements" after a recent "Check for Updates", **When** cached data exists, **Then** achievement status is read from the cache without additional API calls.

---

### User Story 2 - Volatile Data Stays Fresh Within a Session (Priority: P1)

A user updates a Creation in-game, then runs "Check for Updates" in the toolkit. Because the cache tracks per-creation fetch timestamps and respects the session window, the version info used is recent enough to be reliable. If the app has been running for over 30 minutes since startup, volatile data (version, price) is considered stale and re-fetched.

**Why this priority**: Stale version data defeats the purpose of the update check. The session window ensures volatile data is trustworthy without requiring a full refresh every time.

**Independent Test**: Run "Check for Updates", note results, wait 30+ minutes, run again. The second run should re-fetch volatile data from the API.

**Acceptance Scenarios**:

1. **Given** cached data for a Creation was fetched 10 minutes ago and the app started 15 minutes ago, **When** the user runs a check, **Then** the cached data is used (within session window).
2. **Given** cached data for a Creation was fetched 25 minutes ago and the app started 35 minutes ago, **When** the user runs a check, **Then** volatile data is re-fetched from the API.
3. **Given** immutable data (author, achievement-friendly status) is cached from a previous session days ago, **When** the user runs a check, **Then** the immutable data is reused without re-fetching regardless of session window.

---

### User Story 3 - Post-Update State Preservation (Priority: P2)

A user runs "Check for Updates" and sees 5 updates available. They update one Creation in-game, which triggers a file change and an auto-refresh prompt. When they click Refresh, the remaining 4 updates should still be visible because the check results are preserved in the cache, not lost by the refresh.

**Why this priority**: Without caching, a refresh after updating one Creation loses the state of all other pending updates, forcing the user to re-run the full check. This is a key usability improvement.

**Independent Test**: Run "Check for Updates" showing multiple updates, simulate a file change (modify Plugins.txt), click Refresh, and verify the update indicators persist.

**Acceptance Scenarios**:

1. **Given** a check has found 5 updates and results are cached, **When** the user refreshes the Creation list, **Then** update indicators for the remaining Creations are preserved from cache.
2. **Given** a check has found achievement blockers and results are cached, **When** the user refreshes the Creation list, **Then** achievement warnings are preserved from cache.

---

### User Story 4 - Explicit Cache Clear (Priority: P3)

A user suspects cached data might be outdated or wants to force a full re-fetch. They click a "Clear Cache" button, which removes all cached API responses. The next check will fetch everything fresh from the API.

**Why this priority**: Provides a safety valve for users who want to ensure they're seeing the latest data, and helps troubleshoot edge cases where the cache might hold incorrect information.

**Independent Test**: Run a check (populating cache), click "Clear Cache", run the check again. The second check should take the same time as the first (full API fetch).

**Acceptance Scenarios**:

1. **Given** cached data exists on disk, **When** the user clicks "Clear Cache", **Then** all cached API responses are deleted.
2. **Given** cache has been cleared, **When** the user runs any check, **Then** all Creations are fetched from the API.
3. **Given** the user clears the cache, **When** the clear completes, **Then** a confirmation message is shown briefly.

---

### Edge Cases

- What happens when the cache file is corrupted or contains invalid data? The tool discards it and re-fetches from the API.
- What happens when a Creation is removed from the user's install between cache writes? The stale cache entry is harmless and ignored.
- What happens when the app has been running for over 30 minutes? Volatile data is considered stale and re-fetched on the next check.
- What happens when disk write fails (permissions, full disk)? The tool continues without caching, falling back to API-only behavior.
- What happens when the user runs "Check Achievements" right after "Check for Updates"? Achievement data is served from cache instantly since it was just fetched.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST persist API response data to a cache file in the application's data directory.
- **FR-002**: System MUST store a per-creation fetch timestamp with each cached entry.
- **FR-003**: System MUST record the application startup time when the app launches.
- **FR-004**: System MUST treat cached immutable fields (author, achievement-friendly status, categories, thumbnail URL) as permanently valid and never re-fetch them solely due to staleness.
- **FR-005**: System MUST treat cached volatile fields (version, price, installation size, dates) as valid only within the current session window (30 minutes from app startup).
- **FR-006**: System MUST re-fetch volatile data from the API when the session window has expired.
- **FR-007**: System MUST merge fresh API data with existing cached immutable data, updating only the fields that were re-fetched.
- **FR-008**: System MUST provide a "Clear Cache" button in the toolbar that deletes all cached API responses.
- **FR-009**: System MUST handle corrupted or unreadable cache files gracefully by discarding them and proceeding without cache.
- **FR-010**: System MUST fall back to full API fetching if the cache file cannot be written.
- **FR-011**: System MUST reuse cached check results (update status, achievement status) across refreshes within the same session, so that indicators are not lost when the Creation list is reloaded.

### Key Entities

- **CacheEntry**: Per-creation cached data including all API response fields, a fetch timestamp, and the creation's content ID as key.
- **Session Window**: The time span (30 minutes) from app startup during which volatile cached data is considered fresh. Resets only on app restart.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A repeated check within the session window completes in under 2 seconds for a list of 20+ Creations.
- **SC-002**: Immutable data (author, achievement status) is fetched from the API at most once per Creation across the lifetime of the cache.
- **SC-003**: Volatile data (version, price) is never more than 30 minutes stale within a running session.
- **SC-004**: Refreshing the Creation list after a check preserves all update/achievement indicators without requiring a re-check.
- **SC-005**: Clearing the cache and re-running a check produces identical results to a first-time check with no cache.

## Assumptions

- The application's data directory (used for config persistence) is writable and available for cache storage.
- Immutable fields (author, achievement status, categories) do not change for a given Creation once published on the Bethesda platform.
- 30 minutes is a reasonable session window; this value is not user-configurable in v1.
- The cache is local to the machine and not shared across installations.
- The cache file format is an implementation detail not prescribed by this spec.
