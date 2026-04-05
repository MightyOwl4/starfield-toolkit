# Implementation Plan: Creations Text Catalogue

**Branch**: `005-creations-catalogue` | **Date**: 2026-04-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-creations-catalogue/spec.md`

## Summary

Build a standalone catalogue builder that enumerates all Starfield creations via Bethesda's paginated JSON API (`/ugcmods/v2/content?product=GENESIS&page=N&size=20`), collecting description text, release notes (version history), metadata, and dependency declarations (`required_mods`) for each. Results are persisted as a local JSON catalogue with timestamps and SHA-256 content hashes. The builder uses a TBF rate limiter (100 req/5min default), supports multi-pass operation (resume from where it left off), and retries on HTTP 429 with exponential back-off (max 2 retries, then terminates session gracefully). No web scraping or HTML parsing needed — all data comes from the JSON API. This is a developer tool not included in the app distribution, serving as a data-gathering prerequisite for feature 006 (dependency graph). Total: ~4,954 creations across ~248 API pages.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: httpx (HTTP client, already in project)
**Storage**: JSON file at `%APPDATA%/StarfieldToolkit/creations_catalogue.json`
**Testing**: pytest
**Target Platform**: Windows (developer workstation)
**Project Type**: CLI script (standalone entrypoint)
**Performance Goals**: Complete full catalogue build in ~12 minutes at default rate limit (~248 page requests)
**Constraints**: Must not trigger Bethesda's DDoS/scraping detection; TBF rate limiter with configurable 5-min window
**Scale/Scope**: ~4,954 creations (as of 2026-04-05); ~248 pages at size=20; catalogue file estimated 20-100 MB

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS)
- **PASS**: Flat module structure (2 new files + 1 entrypoint + extension to existing `_api.py`). Plain functions, no class hierarchies beyond a simple TBF class. argparse for CLI (stdlib). No design patterns. No HTML parsing — pure JSON API.

### II. Test Coverage (NON-NEGOTIABLE)
- **PASS**: Plan includes tests for all modules: catalogue I/O + hashing, rate limiter, API enumeration logic (mocked HTTP at I/O boundary). Happy path, error cases, and edge cases covered.

### III. Minimal Dependencies
- **PASS**: No new external dependencies. Uses only httpx (already in project). Previous research indicated html.parser/beautifulsoup4 might be needed — browser investigation confirmed this is unnecessary.

### IV. Clear Interfaces
- **PASS**: CLI entrypoint with explicit argparse options. Catalogue module has clear load/save/merge functions. Rate limiter has a single `acquire()` method. All errors logged explicitly, never swallowed.

## Project Structure

### Documentation (this feature)

```text
specs/005-creations-catalogue/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── scrape_catalogue.py              # Standalone CLI entrypoint (argparse)
└── bethesda_creations/
    ├── _api.py                      # [EXISTING] Add enumerate_all_creations() function
    ├── catalogue.py                 # [NEW] Catalogue file I/O, hashing, merge
    └── rate_limiter.py              # [NEW] Token Bucket Filter

tests/
├── test_catalogue.py               # [NEW] Catalogue I/O, hashing, merge
├── test_rate_limiter.py             # [NEW] TBF behavior tests
└── test_scrape_catalogue.py         # [NEW] End-to-end scraper logic (mocked HTTP)
```

**Structure Decision**: Extends existing `bethesda_creations` package with 2 new modules (down from 3 — no scraper.py needed since no HTML parsing). The enumeration function is added to existing `_api.py` alongside the existing search/fetch functions. Tests follow existing flat test directory pattern.

## Complexity Tracking

No constitution violations. No entries needed.
