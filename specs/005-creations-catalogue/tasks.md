# Tasks: Creations Text Catalogue

**Input**: Design documents from `/specs/005-creations-catalogue/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md

**Tests**: Included (constitution principle II: Test Coverage is NON-NEGOTIABLE).

**Organization**: Single user story (P1). Tasks grouped into foundational infrastructure, then the main feature.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: No new project structure needed — extends existing `bethesda_creations` package.

- [x] T001 Verify existing project structure: confirm `src/bethesda_creations/__init__.py` exists and `_api.py` has `fetch_bnet_key()` and `CREATIONS_SEARCH_API` available for reuse

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Rate limiter and catalogue I/O modules — shared infrastructure that the CLI entrypoint depends on.

**⚠️ CRITICAL**: CLI entrypoint (Phase 3) cannot begin until this phase is complete.

### Implementation

- [x] T002 [P] Implement Token Bucket Filter rate limiter in src/bethesda_creations/rate_limiter.py — class with `acquire()` method, configurable bucket size and refill rate over a 5-minute window, default 100 requests per 5 minutes (FR-014, FR-015, FR-016)
- [x] T003 [P] Implement catalogue file I/O in src/bethesda_creations/catalogue.py — `load_catalogue(path)`, `save_catalogue(entries, path)` with atomic write (temp file + rename), `compute_content_hash(description, release_notes_text)` returning SHA-256 hex digest, `api_response_to_entry(response_item)` extracting CatalogueEntry fields from API response per data-model.md (FR-003, FR-004, FR-005, FR-006, FR-010)
- [x] T004 [P] Add `enumerate_creations(client, page, size)` function to src/bethesda_creations/_api.py — calls `GET /ugcmods/v2/content?product=GENESIS&page=N&size=20`, returns `(items, total)` tuple where items is `data[]` from response and total is `total` field. Reuse existing `fetch_bnet_key()` and httpx client setup with custom `User-Agent: StarfieldToolkit/1.0 (+https://github.com/MightyOwl4/starfield-tool/issues)` header (FR-001, FR-013, FR-020)

### Tests

- [x] T005 [P] Write tests for rate limiter in tests/test_rate_limiter.py — test `acquire()` blocks when bucket empty, test refill over time, test configurable bucket size, test burst then throttle behavior
- [x] T006 [P] Write tests for catalogue I/O in tests/test_catalogue.py — test load/save roundtrip, test atomic write (no corruption on failure), test `compute_content_hash` determinism, test `api_response_to_entry` field extraction, test load of corrupted JSON returns empty catalogue, test merge preserves existing entries
- [x] T007 [P] Write tests for enumerate_creations in tests/test_scrape_catalogue.py — test pagination returns items and total, test empty search results, test HTTP error handling, mock httpx responses

**Checkpoint**: Foundation ready — rate limiter, catalogue I/O, and API enumeration all tested. CLI entrypoint can now be built.

---

## Phase 3: User Story 1 - Build Full Creations Text Catalogue (Priority: P1) 🎯 MVP

**Goal**: Standalone CLI tool that enumerates all Starfield creations via paginated API, collects description + release notes + metadata, and persists as a local JSON catalogue with content hashes and timestamps.

**Independent Test**: Run `python src/scrape_catalogue.py --dry-run` to verify enumeration, then `python src/scrape_catalogue.py --max-entries 5` to verify end-to-end with a small batch.

### Implementation

- [x] T008 [US1] Implement main scraper loop in src/scrape_catalogue.py — argparse CLI with `--force`, `--id`, `--rate-limit`, `--max-entries`, `--dry-run` flags per contracts/cli.md. Main loop: fetch bnet key, paginate through all creations, for each page: check each item against existing catalogue (skip if present unless `--force`), convert API response to catalogue entry via `api_response_to_entry()`, save catalogue after each page. Integrate rate limiter `acquire()` before each API call (FR-007, FR-008, FR-012, FR-019)
- [x] T009 [US1] Add in-place progress counter to src/scrape_catalogue.py — print `\r[N of ~TOTAL]` to stderr using carriage return (no newline), derive total from API response `total` field on first page. Print summary line to stdout on completion with counts of new/skipped/failed (FR-011)
- [x] T010 [US1] Add HTTP 429 handling and session termination to src/scrape_catalogue.py — on 429 response, exponential back-off (2s, 8s) with up to 2 retries. If still 429 after retries, save catalogue and exit with code 1. Log rate-limit event to stderr (FR-017)
- [x] T011 [US1] Add error handling and graceful shutdown to src/scrape_catalogue.py — catch KeyboardInterrupt to save progress, catch per-item parsing errors (skip and log), catch network errors (save and exit code 2). Ensure catalogue is never corrupted by partial writes (FR-009, FR-018)
- [x] T012 [US1] Add exit codes to src/scrape_catalogue.py — 0 for full success, 1 for partial completion (rate-limited or max-entries reached), 2 for fatal error per contracts/cli.md

### Tests

- [x] T013 [US1] Write end-to-end tests in tests/test_scrape_catalogue.py — test full run with mocked API (multiple pages), test `--force` refreshes existing entries, test `--max-entries` stops after N new entries, test `--dry-run` reports count without writing, test `--id` fetches specific creation, test 429 handling triggers session termination after 2 retries, test resume skips existing entries on second run, test KeyboardInterrupt saves progress

**Checkpoint**: User Story 1 fully functional — the catalogue builder can enumerate, fetch, persist, resume, and rate-limit.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and cleanup.

- [x] T014 Run full project lint (`ruff check .`) and fix any issues
- [x] T015 Run full test suite (`pytest`) and verify all tests pass
- [x] T016 Validate quickstart.md scenarios: run `--dry-run`, `--max-entries 5`, and `--force --id <uuid>` against real API to confirm end-to-end behavior

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — verification only
- **Foundational (Phase 2)**: Depends on Setup. Three implementation tasks (T002, T003, T004) can run in parallel. Three test tasks (T005, T006, T007) can run in parallel.
- **User Story 1 (Phase 3)**: Depends on Foundational completion. T008 is the core, T009-T012 build on it sequentially. T013 tests run after implementation.
- **Polish (Phase 4)**: Depends on all Phase 3 tasks complete.

### Within Phase 2 (Foundational)

```
T002 (rate_limiter.py) ──┐
T003 (catalogue.py)   ───┤── all parallel, different files
T004 (_api.py)        ───┘

T005 (test rate_limiter) ──┐
T006 (test catalogue)   ───┤── all parallel, different files
T007 (test enumerate)   ───┘
```

### Within Phase 3 (User Story 1)

```
T008 (main loop)
 ├── T009 (progress counter)
 ├── T010 (429 handling)
 ├── T011 (error handling)
 └── T012 (exit codes)
      └── T013 (end-to-end tests)
```

### Parallel Opportunities

- **Phase 2**: All 3 implementation tasks (T002, T003, T004) can run in parallel. All 3 test tasks (T005, T006, T007) can run in parallel.
- **Phase 3**: T009, T010, T011 can be developed in parallel as they add independent concerns to the main loop (T008).

---

## Implementation Strategy

### MVP First (Single Story)

1. Complete Phase 1: Verify setup
2. Complete Phase 2: Build rate_limiter.py + catalogue.py + _api.py enumeration (with tests)
3. Complete Phase 3: Build CLI entrypoint with all features
4. **STOP and VALIDATE**: Run `python src/scrape_catalogue.py --dry-run` then `--max-entries 20`
5. Run full test suite

### Incremental Delivery

Since this feature has a single user story, delivery is:
1. Foundation → testable modules with unit tests
2. MVP CLI → `--dry-run` and `--max-entries` working
3. Full CLI → all flags, 429 handling, graceful shutdown
4. Polish → lint, full tests, real API validation

---

## Notes

- [P] tasks = different files, no dependencies
- [US1] = all tasks belong to the single user story
- Constitution requires tests — all modules have corresponding test files
- Commit after each task or logical group
- The `--dry-run` flag is valuable for testing enumeration without writing the catalogue
- Real API validation (T016) should use `--max-entries` to avoid full catalogue build during testing
