# Implementation Plan: Creations API Response Caching

**Branch**: `002-creations-cache` | **Date**: 2026-03-29 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-creations-cache/spec.md`

## Summary

Cache Bethesda Creations API responses to disk, splitting fields into immutable (cached permanently) and volatile (cached with a 30-minute session window). Reuse cached data across checks and refreshes within a session. Provide an explicit "Clear Cache" button.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: httpx (existing), json (stdlib)
**Storage**: JSON file in app data directory (alongside existing config)
**Testing**: pytest (existing)
**Target Platform**: Windows (desktop GUI via customtkinter)
**Project Type**: Desktop application
**Performance Goals**: Repeated checks complete in under 2 seconds for 20+ Creations
**Constraints**: Cache must survive app restarts; volatile data max 30 min stale
**Scale/Scope**: Typical user has 5-50 Creations installed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
| --------- | ------ | ----- |
| I. Simplicity First (KISS) | PASS | Single JSON file, no ORM or database. Plain dict-based cache with timestamp checks. No design patterns needed. |
| II. Test Coverage | PASS | Cache read/write, staleness logic, merge behavior, and corruption recovery all testable. Mock only clock and filesystem. |
| III. Minimal Dependencies | PASS | No new dependencies. Uses stdlib `json`, `time`, and `pathlib`. |
| IV. Clear Interfaces | PASS | `_fetch_creation_info` gains an optional cache parameter. Cache module exposes load/save/clear. Failure is silent fallback to API. |

**Gate result**: All principles pass. No violations to track.

## Project Structure

### Documentation (this feature)

```text
specs/002-creations-cache/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/starfield_tool/
├── cache.py             # NEW: cache load/save/clear, staleness logic
├── version_checker.py   # MODIFIED: integrate cache into _fetch_creation_info
├── app.py               # MODIFIED: record startup time, pass to modules
└── tools/
    └── creation_load_order.py  # MODIFIED: add "Clear Cache" button, reuse cached state on refresh

tests/
├── test_cache.py        # NEW: cache read/write, staleness, corruption, merge
└── test_version_checker.py  # MODIFIED: test cache integration
```

**Structure Decision**: Single new module `cache.py` alongside existing code. No new directories or packages needed.

## Complexity Tracking

No violations. Table not needed.
