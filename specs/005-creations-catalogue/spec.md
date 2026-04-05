# Feature Specification: Creations Text Catalogue

**Feature Branch**: `005-creations-catalogue`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "Scrap full list of creations from Bethesda's site, persist it as a local catalogue for future analysis. Reuse current creation cache fetcher, extend it to collect full text information on the creation page - description and history tabs. Propagate to standard creations cache and details page. Catalogue saved in data dir with no expiration. Include fetch timestamp and sha256 hash of concatenated text content."

## Clarifications

### Session 2026-04-05

- Q: Should catalogue entries store basic metadata (title, author, categories, price) alongside text fields? → A: Yes, store basic metadata so the catalogue is self-contained for analysis.
- Q: Should the catalogue fetch provide real-time progress feedback during a full site scrape? → A: Yes, show a progress indicator (counter/bar) during fetch.
- Q: Is the catalogue integrated into the GUI app (cache extension, details dialog)? → A: No. The scraper is a separate entrypoint, not included in the app distribution. It produces a standalone catalogue file for offline analysis. No changes to the existing creations cache or details dialog. This is a data-gathering step for feature 006 (dependency graph from creation descriptions).
- Q: How should the scraper avoid automated flagging from Bethesda for DDoS/scraping? → A: Implement a Token Bucket Filter (TBF) rate limiter with configurable limits on a 5-minute span.
- Q: What should the default TBF rate limit be? → A: 100 requests per 5-minute window (~1 request per 3 seconds).
- Q: How should the scraper react to HTTP 429 rate-limit responses? → A: Exponential back-off with up to 2 retries. If still rate-limited, terminate the session gracefully (save progress) rather than skip-and-continue -- completion is left to subsequent sessions.
- Q: How should CLI progress feedback work? → A: After first page fetch, derive approximate total from page count * items per page. Display an in-place counter (updated in place, no scrolling) in the format `[5 of ~1678]`. The total is approximate since `(pages-1)*items_per_page < total <= pages*items_per_page`.
- Q: Should the user be able to cap how many entries are processed per session? → A: Yes, add an optional `--max-entries` argument. When set, the scraper stops after processing that many new entries and saves progress for the next session.
- Q: How should the scraper identify itself to Bethesda's servers? → A: Set a `User-Agent` header with tool name and a link to the project's GitHub issues page, following the standard bot identification convention (`+URL` in parens).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build Full Creations Text Catalogue (Priority: P1)

A developer/analyst wants to build a local catalogue of ALL creations available on Bethesda's site, capturing full text content (description and history) and basic metadata, so the data can be analyzed in a future feature (006) to extract dependency information and build a dependency graph similar to LOOT.

The user runs the scraper as a standalone entrypoint. The scraper enumerates all available Starfield creations on Bethesda's site, scrapes the "description" and "history" tab content for each, and persists them locally as a catalogue file in the data directory. Each entry includes basic metadata (title, author, categories, price), the fetched timestamp, and a SHA-256 hash of the concatenated description and history text. The catalogue has no expiration -- once fetched, entries persist indefinitely until the user explicitly refreshes them.

**Why this priority**: This is the only feature -- without the catalogue, the downstream dependency graph analysis (006) cannot proceed.

**Independent Test**: Can be fully tested by running the scraper and verifying the resulting catalogue file contains correct description text, history text, metadata, timestamps, and hashes for all discovered creations.

**Acceptance Scenarios**:

1. **Given** the user runs the scraper, **When** the fetch completes, **Then** the system has enumerated all Starfield creations on Bethesda's site, scraped description and history text for each, and saved them with metadata in a catalogue file in the data directory.
2. **Given** a catalogue file already exists with some entries, **When** the user runs the scraper, **Then** only creations missing from the catalogue are fetched (existing entries are preserved as-is).
3. **Given** the user force-refreshes a specific creation or the entire catalogue, **When** the fetch completes, **Then** the affected entries' text, metadata, timestamp, and hash are updated.
4. **Given** a creation's page is unreachable or returns an error, **When** the scraper runs, **Then** the system skips that creation, logs the failure, and continues with remaining creations without corrupting existing catalogue data.
5. **Given** the scraper is running, **When** creations are being processed, **Then** the user sees a progress indicator showing how many creations have been processed out of the total discovered.

---

### Edge Cases

- What happens when Bethesda's site structure changes and scraping fails? The system handles parsing errors gracefully, skips the affected creation, and logs the issue.
- What happens when the catalogue file is corrupted or manually edited with invalid JSON? The system detects corruption, logs a warning, and treats it as an empty catalogue (rebuilding on next fetch).
- What happens when a creation has an empty description or history tab? The system stores empty strings and computes the hash accordingly.
- What happens when the scraper is interrupted mid-run (e.g., network failure, user cancellation)? Already-fetched entries in the catalogue are preserved; only the interrupted entry is lost.
- What happens when Bethesda's server returns HTTP 429 (Too Many Requests) or similar rate-limit responses? The scraper performs exponential back-off with up to 2 retries. If still blocked, it terminates the session gracefully, saving all progress. The next run picks up where this session stopped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Scraper MUST enumerate ALL Starfield creations available on Bethesda's site (not limited to installed creations).
- **FR-002**: Scraper MUST collect the full description text and release notes (version history) for each creation via Bethesda's JSON API (no web scraping or HTML parsing required).
- **FR-003**: Scraper MUST persist scraped data in a catalogue file stored in the application's data directory.
- **FR-004**: Catalogue entries MUST include: creation identifier, basic metadata (title, author, categories, price), description text, release notes (version history), required_mods (dependency declarations), fetch timestamp (ISO 8601), and a SHA-256 hash of the concatenated description and release notes text.
- **FR-005**: Catalogue entries MUST have no expiration -- once fetched, an entry persists until explicitly refreshed by the user.
- **FR-006**: The catalogue file itself MUST have no file-level expiration or automatic invalidation.
- **FR-007**: Scraper MUST skip creations that are already present in the catalogue during a standard run (only fetch missing entries).
- **FR-008**: Scraper MUST support force-refreshing individual creations or the entire catalogue, updating text, metadata, timestamp, and hash.
- **FR-009**: Scraper MUST handle scraping failures gracefully -- skip failed creations without corrupting the catalogue or blocking other fetches.
- **FR-010**: The SHA-256 hash MUST be computed from the concatenation of description text and history text (in that order), enabling change detection without re-fetching.
- **FR-011**: Scraper MUST display an in-place progress counter (no scrolling output) during fetch operations, in the format `[N of ~TOTAL]` (e.g., `[5 of ~4954]`). The exact total is returned by the API's `total` field on the first page response.
- **FR-012**: Scraper MUST be a standalone entrypoint, separate from the main GUI application and not included in the app distribution.
- **FR-013**: Scraper MUST reuse the existing creation cache fetcher's HTTP/API infrastructure where applicable (API key retrieval, HTTP client setup).
- **FR-014**: Scraper MUST implement a Token Bucket Filter (TBF) rate limiter to avoid triggering automated DDoS/scraping detection by Bethesda's servers.
- **FR-015**: The TBF rate limiter MUST use a configurable bucket size and refill rate over a 5-minute window.
- **FR-016**: The rate limiter MUST default to 100 requests per 5-minute window (~1 request per 3 seconds), configurable by the user.
- **FR-017**: When receiving an HTTP 429 (or similar rate-limit response), the scraper MUST perform exponential back-off and retry up to 2 times. If still rate-limited after 2 retries, the scraper MUST terminate the session gracefully -- saving all progress to the catalogue file so the next run resumes from where it stopped.
- **FR-018**: Scraper MUST support multi-pass operation: on each run, it picks up where the previous session left off by scraping only creations not yet present in the catalogue (including those skipped due to errors or rate-limiting in prior runs).
- **FR-019**: Scraper MUST accept an optional `--max-entries` argument that caps the number of new entries processed in a single session. When the limit is reached, the scraper saves progress and exits gracefully, leaving remaining entries for subsequent sessions.
- **FR-020**: Scraper MUST set a `User-Agent` header identifying the tool and providing a contact URL (the project's GitHub issues page), following the standard bot identification convention: `StarfieldToolkit/1.0 (+https://github.com/MightyOwl4/starfield-tool/issues)`.

### Key Entities

- **Catalogue Entry**: Represents a single creation's scraped text content and metadata. Contains: creation identifier (content_id), title, author, categories, price, description text, history text, fetched-at timestamp, and content hash (SHA-256 of description + history).
- **Catalogue File**: A persistent JSON file in the data directory containing all catalogue entries. Has no expiration at any level. Separate from the existing creations cache.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can build a complete text catalogue of all Starfield creations available on Bethesda's site across one or more scraper runs (multi-pass).
- **SC-002**: Catalogue entries persist across runs with no data loss or expiration.
- **SC-003**: Users can detect content changes by comparing stored hashes against freshly computed hashes after a re-fetch.
- **SC-004**: Scraping failures for individual creations do not prevent the remaining creations from being catalogued.
- **SC-005**: Subsequent scraper runs complete faster by skipping already-catalogued creations.

## Assumptions

- The Bethesda API (`/ugcmods/v2/content`) returns full creation details including description, release notes, and required_mods in its paginated listing response (confirmed via browser investigation 2026-04-05: `page`/`size` params, `total: 4954`, ~248 pages at size=20).
- The existing creations cache fetcher's HTTP/API infrastructure (API key retrieval, HTTP client) can be reused by the scraper.
- The application's data directory is writable and has sufficient space for a JSON catalogue file covering all Starfield creations.
- The catalogue covers ALL Starfield creations available on Bethesda's site, not just those installed by the user.
- The concatenation order for hash computation is description followed by history, with no separator.
- The scraper is a developer/analyst tool, not a user-facing feature in the distributed application.
- This catalogue is a prerequisite for feature 006 (dependency graph extraction from creation descriptions).
