# Implementation Plan: Fast Lane Category-Based Classification Refinement

**Branch**: `011-fast-lane-categories` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/011-fast-lane-categories/spec.md`

## Summary

Refine Fast Lane's stale-version warning with two category-based tiers:
**SAFE** categories (Skins, Apparel, Body, Photo Mode, Audio) skip the check entirely and render as "Unaffected". **LOW_RISK** categories (Weapons, Gear, Ships) still run the check but, if they would otherwise show "Not updated", are instead annotated as "Low risk" with softer styling. Meta-tags (Load Order Neutral, Lore Friendly, Work in Progress) are stripped before category evaluation. Combination logic is strict: every non-meta category of a creation must be in the relevant set. The PS-support override ("Likely updated") applies before the Low-risk annotation. Categories come from the API (`CreationInfo.categories`); the baseline's `s=1` flag remains a fallback for skins when API data is missing.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: customtkinter (existing), pytest (existing). No new runtime dependencies.
**Storage**: N/A — classification is computed per-check from in-memory data. No baseline regeneration required.
**Testing**: pytest (headless, no Tk event loop); manual verification for UI tier rendering
**Target Platform**: Windows desktop (primary), Linux/macOS (secondary)
**Project Type**: Desktop application (single-project layout — `src/` + `tests/`)
**Performance Goals**: Negligible — category-set checks are O(1) per row. ≤200 creations typical.
**Constraints**: No schema change to `data/creations_baseline.json`; keep PS-support override ordering intact; must not regress existing 313+ tests.
**Scale/Scope**: Typical Fast Lane run: ~200 rows. Each row triggers a handful of set-membership checks — trivially fast.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS) — PASS
- Two `frozenset` constants + a small `_classify_with_categories` helper that wraps the existing `_classify`. No new classes, no new patterns, no indirection.
- Reuses `CreationInfo.categories` already populated by `parse_response` — no new data plumbing.
- Tag configuration and tree rendering mirror the existing `skin` / `not_updated` patterns exactly.

### II. Test Coverage (NON-NEGOTIABLE) — PASS
- New behavior covered by unit tests in `tests/test_fast_lane_check.py`:
  - Safe category → Unaffected
  - Low-risk category → Low risk
  - Strict combination rejects mixed non-safe (e.g. `[Weapons, Quests]` stays Not updated)
  - Meta-tag stripped before evaluation
  - PS-support precedence over Low-risk
  - Baseline `s=1` fallback still works
  - Genuine Updated status never downgraded by a category tier

### III. Minimal Dependencies — PASS
- No new libraries or runtime dependencies.

### IV. Clear Interfaces — PASS
- New status `STATUS_LOW_RISK`. Renaming `STATUS_SKIN` → `STATUS_UNAFFECTED` is a rename-only in a single file; no external consumers.
- Category sets are module-level constants with type `frozenset[str]` — obvious and immutable.
- Row dict gains two optional keys (`low_risk_reason`, `unaffected_reason`) — string, empty by default.

**Gate status: PASS. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/011-fast-lane-categories/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (written by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
└── starfield_tool/
    └── tools/
        └── fast_lane_check.py      # MODIFY: constants, status values,
                                    #         _run_comparison flow, tree
                                    #         rendering, summary line, banner

tests/
└── test_fast_lane_check.py         # ADD: safe/low-risk/mixed/meta/PS-precedence tests
                                    # RENAME: STATUS_SKIN → STATUS_UNAFFECTED
```

No new files. The baseline generator is untouched.

**Structure Decision**: Single-project (existing). All changes confined to one source file and its test file, plus the feature's spec artifacts.

## Complexity Tracking

No constitution violations. Table omitted.
