# Implementation Plan: Fast Lane Creation Check

**Branch**: `009-fast-lane-check` | **Date**: 2026-04-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/009-fast-lane-check/spec.md`

## Summary

Add a "Fast Lane Creation Check" tab that compares installed creations against a bundled baseline snapshot (trimmed pre-Fast-Lanes catalogue) to identify creations that have not been updated since the snapshot. The tool reuses the existing version comparison logic and creations cache from the Installed Creations tab — no new API calls. A developer script (`make_baseline.py`) generates the trimmed baseline from the full catalogue on demand. A prominent always-visible warning banner explains the approximate nature of the detection.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: customtkinter (existing), no new libraries
**Storage**: Bundled JSON baseline at `data/creations_baseline.json` (dev) / `sys._MEIPASS/data/creations_baseline.json` (production)
**Testing**: pytest
**Target Platform**: Windows (desktop app)
**Project Type**: Desktop app feature extension
**Performance Goals**: Tab loads in under 2 seconds for up to 1,000 installed creations
**Constraints**: Baseline file under 500 KB; no network access at runtime; no modifications to installed files
**Scale/Scope**: Up to 4,954 entries in baseline, up to ~1,000 installed creations per user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS)
- **PASS**: Single tool file (`fast_lane_check.py`) + one developer script (`make_baseline.py`). No class hierarchies, no abstractions. Reuses existing `compare_versions`, `build_creation_list`, `get_cached_info_any`, and ToolModule patterns.

### II. Test Coverage (NON-NEGOTIABLE)
- **PASS**: Tests cover baseline loading (valid/missing/corrupted), comparison logic (all 3 status outcomes), export file parsing (CSV + Markdown), content_id resolution by title fallback, and baseline generator script.

### III. Minimal Dependencies
- **PASS**: Zero new dependencies. Pure stdlib JSON + existing project modules.

### IV. Clear Interfaces
- **PASS**: Baseline file format documented in data-model.md. Tool follows ToolModule contract. Comparison logic in pure functions testable in isolation.

## Project Structure

### Documentation (this feature)

```text
specs/009-fast-lane-check/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
data/
└── creations_baseline.json                          # [NEW] Bundled baseline snapshot (committed)

src/
└── starfield_tool/
    └── tools/
        ├── __init__.py                              # [MODIFIED] Register FastLaneCheckTool
        ├── creation_load_order.py                   # [MODIFIED] Export now includes Content ID column
        ├── fast_lane_check.py                       # [NEW] Tool tab: UI, comparison, import parsing
        └── fast_lane_baseline_generator.py          # [NEW] Dev script: trim full catalogue -> baseline

bin/
└── build.sh                                         # [MODIFIED] Bundle baseline via --add-data

tests/
├── test_creation_load_order_export.py               # [MODIFIED or NEW] Cover new Content ID column
├── test_fast_lane_check.py                          # [NEW] Comparison, import, baseline loading
└── test_fast_lane_baseline_generator.py             # [NEW] Trimmed catalogue generation
```

**Structure Decision**: All feature 009 code is co-located inside `src/starfield_tool/tools/` with a `fast_lane_` prefix. The tool tab follows the existing `ToolModule` pattern (similar to `RuleBookTool`). The baseline generator sits alongside the tool — unconventional for a dev script but intentional: this feature is short-lived by design (fades in relevance as time passes since Fast Lanes), so consolidating all related files makes eventual cleanup trivial (delete two tool files, remove one line from `__init__.py`, delete the bundled data file). The baseline file itself is a committed bundled asset like the LOOT masterlist and curated rulebooks.

## Complexity Tracking

No constitution violations. No entries needed.
