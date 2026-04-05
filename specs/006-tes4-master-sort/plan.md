# Implementation Plan: TES4 Master Dependency Sorting

**Branch**: `006-tes4-master-sort` | **Date**: 2026-04-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-tes4-master-sort/spec.md`

## Summary

Add TES4 master dependency awareness to the load order sorter. Parse MAST subrecords from local `.esm` files to build a master dependency map, produce highest-priority `load_after` constraints (priority 100, gaps left for future sources at 25-90), fix the solver to honor cross-tier dependencies, and add a non-bypassable pre-write validation check that blocks saving broken load orders.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: None new (stdlib `struct` for binary parsing, existing `load_order_sorter` package)
**Storage**: In-memory master map (cached per session)
**Testing**: pytest
**Target Platform**: Windows (desktop app)
**Project Type**: Desktop app feature extension
**Performance Goals**: TES4 header parsing < 2 seconds for 600 plugins
**Constraints**: No new external dependencies; must integrate with existing sorter pipeline without breaking CAT/LOOT behavior
**Scale/Scope**: Up to ~600 installed creation plugins

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS)
- **PASS**: TES4 parser is ~40 lines of stdlib binary read. Sorter follows existing pattern (one module with `sort()` function). Validation is a single function checking order against master map. Cross-tier fix is a pre-solve promotion step (~15 lines).

### II. Test Coverage (NON-NEGOTIABLE)
- **PASS**: Tests for parser (real and synthetic binary files), sorter (constraint generation, cross-tier), validation (violations detected/clear), and integration (auto-sort with TES4 constraints).

### III. Minimal Dependencies
- **PASS**: Zero new dependencies. Uses only `struct` from stdlib for binary parsing. All other code uses existing project infrastructure.

### IV. Clear Interfaces
- **PASS**: Parser: `parse_masters(filepath) -> list[str]`. Sorter: `sort(items, data_dir, installed_plugins) -> list[SortConstraint]`. Validation: `validate_tes4_order(plugin_order, master_map) -> list[ValidationViolation]`.

## Project Structure

### Documentation (this feature)

```text
specs/006-tes4-master-sort/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
└── load_order_sorter/
    ├── pipeline.py                  # [MODIFIED] Add TES4 to sorter registry, cross-tier fix
    ├── tes4_parser.py               # [NEW] Binary TES4 header parser
    ├── validation.py                # [NEW] Pre-write TES4 order validation
    └── sorters/
        └── tes4.py                  # [NEW] TES4 sorter producing load_after constraints

src/
└── starfield_tool/
    └── tools/
        └── load_order.py            # [MODIFIED] Validation in _apply(), TES4 in auto-sort

tests/
├── test_tes4_parser.py              # [NEW] Binary parser tests
├── test_tes4_sorter.py              # [NEW] Sorter + cross-tier tests
└── test_tes4_validation.py          # [NEW] Validation logic tests
```

**Structure Decision**: Follows existing sorter pattern — new sorter in `sorters/tes4.py`, parser as a separate utility module, validation as its own module. Modifies `pipeline.py` for integration and cross-tier fix.

## Complexity Tracking

No constitution violations. No entries needed.
