# Implementation Plan: Detect Broken Updates

**Branch**: `014-detect-broken-updates` | **Date**: 2026-04-15 | **Spec**: [spec.md](./spec.md)

## Summary

A new tab that reads disk state (ContentCatalog + Plugins.txt + Data/) and flags Creations that trip any of three OR'd signals — partial files, esm-without-plugins-line, mtime skew — then offers a multi-selection Delete that reuses feature 013's removal machinery with a dependency-ignorant confirmation and an alphabetical result summary. Ungated by settings; tab-level discoverability is the safety hurdle.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: customtkinter (GUI), standard library (`pathlib`, `os`); reuses `starfield_tool.removal` and `starfield_tool.game_process` from feature 013
**Storage**: read-only ContentCatalog.txt and Plugins.txt; write access (delete + line-strip) handled by the existing `execute_removal`
**Testing**: pytest via `uv run pytest` — unit tests for the detector and the delete-plan aggregator; no tkinter in CI
**Target Platform**: Windows desktop
**Project Type**: Desktop app, single project
**Performance Goals**: SC-002 — Scan under 3 s for 50–200 ContentCatalog entries (one stat call per file)
**Constraints**: No network I/O in the scan path; no mutations outside the explicit Confirm click; Win+D recoverable dialogs
**Scale/Scope**: Typical install ~200 Creations × ~5 files = ~1k stat calls per scan

## Constitution Check

*GATE: must pass before Phase 0, re-check after Phase 1.*

- **I. Simplicity First (KISS)** — PASS. One new detector module (`broken_scan.py`), one new tool module (`tools/broken_updates.py`), one pair of dialogs. No new class hierarchy; detector is plain functions returning dataclasses. Reuses 013's `plan_removal` / `execute_removal` rather than reimplementing.
- **II. Test Coverage (NON-NEGOTIABLE)** — PASS. Detector is pure (inputs: catalog entries, plugins lines, data-dir path, clock; outputs: list of flagged entries). Unit tests cover each signal individually, OR composition, multi-reason rows, empty-state, out-of-tree guard, and the alphabetical result-summary builder. No UI in CI.
- **III. Minimal Dependencies** — PASS. No new third-party deps.
- **IV. Clear Interfaces** — PASS. `scan_broken(catalog, plugins_txt, data_dir, now=time.time) -> list[FlaggedCreation]` has explicit inputs/outputs; the injected clock keeps mtime-skew tests deterministic.

No violations; Complexity Tracking table omitted.

## Project Structure

### Documentation (this feature)

```text
specs/014-detect-broken-updates/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── detector_api.md
├── checklists/
│   └── requirements.md
└── tasks.md        # /speckit.tasks output
```

### Source Code (repository root)

```text
src/starfield_tool/
├── broken_scan.py                    # NEW: pure detector + dataclasses
├── removal.py                        # reused from 013
├── game_process.py                   # reused from 013
├── tools/
│   ├── __init__.py                   # MODIFY: register BrokenUpdatesTool
│   └── broken_updates.py             # NEW: ToolModule — Scan button, tree, Delete flow
└── dialogs/
    └── broken_updates.py             # NEW: multi-creation confirm + result dialogs

tests/
└── test_broken_scan.py               # NEW: detector + delete-plan aggregation tests
```

**Structure Decision**: Pure logic at `src/starfield_tool/` top level (alongside `removal.py`, `parsers.py`), tab as a `ToolModule` in `tools/`, dialogs in `dialogs/`. We expected to reuse 013's `RemoveConfirmDialog` but the extra "no dependency check" warning plus multi-creation summary diverge enough from 013's single-creation shape that a dedicated dialog file is cleaner than parameterising.

## Key Design Decisions

1. **Pure detector.** `broken_scan.scan_broken(...)` returns a list of `FlaggedCreation` dataclasses. No tkinter, no disk mutation. Injects `now=time.time` for deterministic mtime-skew tests.
2. **Aggressive by design.** Signal (b) "esm-without-plugins-line" treats a missing or empty Plugins.txt as every esm-having Creation being flagged — matches the spec's edge case and produces the correct recovery behaviour when Plugins.txt is truly lost.
3. **Out-of-tree guard.** Reuses 013's safety model: a Files entry resolving outside `data_dir` tags the Creation with an "out of tree" reason; the delete plan processes the in-tree subset and reports out-of-tree entries without touching them.
4. **Multi-selection delete reuses 013.** For each selected `FlaggedCreation` we construct a synthetic `Creation` (content_id, display_name, plugin_files=the full Files list) and call `plan_removal(...)` + `execute_removal(...)`. Results are folded into a combined per-run outcome. Principle I in action — no parallel file-delete or line-strip implementation.
5. **Game-running check is pre-flight only.** Scan is read-only; no need to block it while the game runs. Delete calls `is_starfield_or_launcher_running()` at Confirm time and aborts cleanly before the first mutation.
6. **Result dialog.** One dialog with the alphabetical list of processed Creations in a selectable/copyable text area, plus per-Creation per-file outcomes (deleted / already_gone / failed with reason) for transparency.
7. **Tab registration.** One new entry appended to `tools/__init__.py::MODULES`. No changes to `app.py`'s tab plumbing.
8. **No auto-scan.** Tab opens showing the empty state with "Click Scan to begin." Explicit click is the only trigger (FR-002).

## Phase 0 — Research

See [research.md](./research.md). No outstanding NEEDS CLARIFICATION.

## Phase 1 — Design Artefacts

- [data-model.md](./data-model.md) — `FlaggedCreation`, `DetectionReason`, scan + delete-plan contracts
- [contracts/detector_api.md](./contracts/detector_api.md) — `scan_broken` signature, reuse points from 013
- [quickstart.md](./quickstart.md) — user walkthrough

Agent context file refreshed via `.specify/scripts/bash/update-agent-context.sh claude`.

## Post-Design Constitution Re-check

Re-verified after design: still PASS on all four principles. Reuse of 013's machinery reinforces principle I (no duplicated line-stripping); detector purity preserves principle II.

## Complexity Tracking

Not applicable.
