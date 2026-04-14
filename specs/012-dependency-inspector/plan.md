# Implementation Plan: Dependency Inspector

**Branch**: `012-dependency-inspector` | **Date**: 2026-04-14 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-dependency-inspector/spec.md`

## Summary

Add a new **Dependency Inspector** tab that visualises hard and soft dependencies among currently installed Creations, rendered in load order. Reuses the diff-dialog presentation model: a single centered datagrid with connectors drawn on a Canvas on *both* sides (left = outgoing / "depends on", right = incoming / "is depended on by" — final side choice made by a greedy router that minimises crossings). Palette color of each participating Creation is derived deterministically from the load-order-earliest neighbour of its first outgoing or (fallback) incoming edge, computed once at graph build. Selecting a row highlights only the directed transitive closure (ancestors ∪ descendants) in white with a glow; unrelated connectors dim. Soft connectors and no-dependency rows are independently toggle-able. Dependencies pointing to uninstalled creations are ignored; a warning icon flags rows with missing *hard* dependencies. Tool is read-only and piggy-backs on the existing Installed Creations refresh pipeline.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: customtkinter (already present), stdlib `tkinter` (Canvas, ttk), stdlib `dataclasses`, existing project packages `bethesda_creations` (catalogue — `required_mods`), `description_parser` output (soft deps — plain JSON), `starfield_tool.parsers.build_creation_list` (installed+load-order data).
**Storage**: N/A (UI-only state; dependency graph built in-memory from catalogue + description-parser output).
**Testing**: pytest (headless — no Tk event loop); UI behaviour verified manually per project convention, documented in quickstart.md.
**Target Platform**: Windows desktop (primary), Linux/macOS (secondary).
**Project Type**: Desktop application (single project — `src/` + `tests/`).
**Performance Goals**: Initial render ≤ 2 s for 500 creations (SC-001). Selection highlight ≤ 200 ms (SC-002). Toggle update ≤ 300 ms (SC-004).
**Constraints**: No new external dependencies. Must work at 100–150% DPI. Read-only — no mutation of load order, plugin files, or catalogue. Must not alter Installed Creations tab behaviour.
**Scale/Scope**: Up to ~500 installed creations; edge counts typically O(n) for hard deps, O(n) for soft deps in practice. Graph algorithms must be linear in |V|+|E|.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS) — PASS

- Reuses existing `DiffDialog` visual primitives — Bezier `canvas.create_line(..., smooth=True)`, 6-entry color palette constant, endpoint dot drawing, glow/dim styling.
- Graph representation is two plain `dict[str, list[str]]` adjacency maps (out-edges, in-edges) keyed by `content_id`. No graph library.
- Transitive closure is a plain BFS from the selected node over each direction — no caching layer, no observer pattern.
- Side-assignment router is a single-pass greedy heuristic (pick side that currently has fewer crossings with already-placed edges). No optimisation framework.
- No new data model classes in core packages — the inspector owns a single `DependencyGraph` dataclass internal to the tool module.

### II. Test Coverage (NON-NEGOTIABLE) — PASS

- Dependency aggregation (catalogue `required_mods` + description-parser soft deps → adjacency maps, with missing-endpoint filtering and hard-miss warning list) is a pure function — tested directly.
- Directed transitive closure (ancestors, descendants) is a pure function — tested for happy path, disconnected graph, cycle, self-loop.
- First-edge-by-earliest-endpoint color assignment is a pure function — tested for outgoing-precedence, incoming-fallback, no-connection-stays-regular, tie (stable load-order tiebreak).
- Connector side-router is a pure function over edges + load-order positions → `list[tuple[edge, "left"|"right"]]` — tested for crossing count is no worse than all-same-side on a canned set of edges.
- UI behaviour (selection dim/highlight, toggles) follows project precedent of manual verification — covered in quickstart.md.

### III. Minimal Dependencies — PASS

- No new external dependencies. Canvas drawing uses stdlib `tkinter.Canvas`. Widgets reuse customtkinter already in use.

### IV. Clear Interfaces — PASS

- `build_dependency_graph(creations, catalogue, soft_deps) -> DependencyGraph` — typed inputs, typed output, no I/O.
- `DependencyGraph` exposes `out_edges`, `in_edges`, `palette_color`, `missing_hard`, `no_deps` as plain attributes.
- `closure(graph, node) -> set[str]` for ancestors, descendants — two small functions, not one overloaded call.
- `assign_sides(edges, positions) -> list[tuple[Edge, Side]]` — pure, deterministic, order-independent input.
- No silent error swallowing: missing soft deps are explicitly dropped by the ingestion step (documented), missing hard deps explicitly surface in `DependencyGraph.missing_hard`.

**Gate status: PASS. No violations.**

## Project Structure

### Documentation (this feature)

```text
specs/012-dependency-inspector/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── dependency_inspector_api.md   # Internal module contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (written by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
└── starfield_tool/
    └── tools/
        └── dependency_inspector.py    # NEW: tab module (ToolModule), graph build, rendering

src/starfield_tool/
└── app.py                             # MODIFY: register DependencyInspectorTool tab

tests/
├── test_dependency_inspector_graph.py # NEW: build_dependency_graph, closure, color assignment
└── test_dependency_inspector_router.py# NEW: side-assignment router crossing count
```

**Structure Decision**: Single-project layout (matches existing repo). One new tool module plus one registration line in `app.py`; no changes to `load_order_sorter`, `bethesda_creations`, or `description_parser` — the inspector consumes their existing outputs.

## Complexity Tracking

No constitution violations. Table omitted.
