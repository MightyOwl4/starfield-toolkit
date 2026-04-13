# Research: Creations Text Catalogue

**Date**: 2026-04-05 | **Branch**: `005-creations-catalogue`

## Decision 1: How to Enumerate All Creations

**Decision**: Use the Bethesda listing API (`GET /ugcmods/v2/content?product=GENESIS&page=N&size=20`) with page-based pagination to enumerate all Starfield creations.

**Rationale**: Browser investigation confirmed the API supports `page` and `size` parameters. The endpoint returns `total: 4954` (as of 2026-04-05) with up to 20 items per page (~248 pages). Each item in the `data[]` array contains the FULL creation detail, including `description`, `release_notes`, metadata, and even `required_mods`.

**Alternatives considered**:
- Web crawling a listing page: Unnecessary — the API returns structured paginated data
- Brute-force UUID scanning: Impractical, no enumerable ID space
- Individual detail fetches per UUID: Unnecessary — the listing already returns full details

**Implementation note**: Since the listing returns full details per item, we do NOT need a two-phase approach (enumerate then fetch). A single page-by-page traversal collects everything. This reduces total API calls from ~5000 (one per creation) to ~248 (one per page). Multi-pass resume works by skipping pages where all items are already in the catalogue.

## Decision 2: How to Get Description and History Text

**Decision**: Use the JSON API exclusively. No web scraping or HTML parsing needed.

**Rationale**: Browser investigation revealed that the API response at `/ugcmods/v2/content` (both listing and individual endpoints) returns:
- `description`: The creation's description text (matches the "Overview" tab on the website)
- `overview`: An additional overview field (often empty, but present)
- `release_notes`: Full version history per platform, with version name, note text, and timestamps — this IS the "History" tab data
- `required_mods`: Dependency information (bonus for feature 006)

The website's "Overview" tab renders `description`, and the "History" tab renders `release_notes`. Both are available in the JSON API with no HTML parsing required.

**Alternatives considered**:
- Web scraping with HTML parser: Completely unnecessary — all data is in the API
- Headless browser (Playwright): Overkill, heavy dependency

**Key API response fields** (from `/ugcmods/v2/content/{uuid}`):
```
content_id, title, description, overview, product, categories,
author_buid, author_displayname, achievement_friendly,
release_notes[].hardware_platform, release_notes[].release_notes[].version_name,
release_notes[].release_notes[].note, release_notes[].release_notes[].ctime,
required_mods, required_dlc, catalog_info, download, stats,
preview_image, cover_image, first_ptime, utime
```

## Decision 3: HTML Parsing Approach

**Decision**: REMOVED — no HTML parsing needed. The API returns all data as JSON.

**Rationale**: See Decision 2. No new dependencies required.

## Decision 4: Catalogue File Format and Location

**Decision**: Store the catalogue as a single JSON file at `%APPDATA%/StarfieldToolkit/creations_catalogue.json`, separate from the existing `creations_cache.json`.

**Rationale**: Consistent with existing data directory pattern. JSON is already used for the creations cache and config. Single file simplifies atomic writes and multi-pass resume logic (load, merge new entries, save). Separate from cache to avoid coupling with cache expiration logic.

**Alternatives considered**:
- SQLite: Overkill for this use case, adds complexity
- One file per creation: Harder to manage, filesystem overhead for thousands of entries
- Extend existing cache file: Would couple catalogue (no expiration) with cache (session expiration)

## Decision 5: Rate Limiter Implementation

**Decision**: Implement a Token Bucket Filter (TBF) as a simple Python class with configurable bucket size and refill rate over a 5-minute window. Default: 100 requests per 5 minutes.

**Rationale**: TBF is simple to implement (~30 lines), requires no external dependencies, and provides smooth request distribution. The 5-minute window with 100 tokens means ~1 request per 3 seconds average, which is well below typical scraping detection thresholds. With ~248 pages total, the full catalogue can be built in ~12 minutes at default rate.

**Alternatives considered**:
- Fixed delay between requests: Less flexible, doesn't allow burst-then-wait patterns
- External rate-limiter library: Unnecessary dependency for a simple use case
- Leaky bucket: Slightly more complex, no practical advantage here

## Decision 6: Multi-Pass Resume Strategy

**Decision**: Resume is implicit via catalogue entry lookup. Each run traverses pages, skipping items already in the catalogue. On rate-limit (HTTP 429 after 2 retries), the session terminates gracefully and saves progress.

**Rationale**: The catalogue itself IS the resume checkpoint. With page-based traversal, each page is processed and its new items merged into the catalogue immediately. If the session is interrupted or rate-limited, next run starts from the beginning but skips existing entries quickly (O(1) dict lookup per item).

**Alternatives considered**:
- Session state file tracking last-processed page: Extra complexity, but could speed up resume by skipping already-fully-processed pages. Worth considering as an optimization if page traversal overhead is significant.
- Cursor-based resume with bookmark: Requires stable ordering from the API, which may not be guaranteed

## Decision 7: Scraper Entrypoint

**Decision**: Create a standalone Python script in `src/` (e.g., `src/scrape_catalogue.py`) that can be run with `python src/scrape_catalogue.py`. Not included in the PyInstaller distribution.

**Rationale**: Constitution principle I (Simplicity First). A plain script with `if __name__ == "__main__"` and `argparse` for CLI options is the simplest approach. It imports from `bethesda_creations` package for HTTP infrastructure reuse (FR-013).

**Alternatives considered**:
- Click/Typer CLI framework: Unnecessary dependency for a single-command script
- Subcommand in main app: Violates FR-012 (must be separate entrypoint)

## Decision 8: Data to Store in Catalogue Entries

**Decision**: Store `description` + concatenated `release_notes` (all platform notes merged) as the text content for hashing and analysis. Also store basic metadata and the raw `release_notes` and `required_mods` structures for feature 006.

**Rationale**: The `release_notes` field is structured (per-platform, per-version). For the SHA-256 hash, we concatenate `description` + a normalized text representation of all release notes. Storing the raw `release_notes` array preserves version-level detail for future use. The `required_mods` field is a bonus — it contains explicit dependency declarations from authors, directly useful for the dependency graph in feature 006.

**Alternatives considered**:
- Store only text: Loses structured version info
- Store entire API response: Too large, includes irrelevant data (stats, images, etc.)
