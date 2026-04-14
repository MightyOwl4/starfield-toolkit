---

description: "Tasks for Dependency Inspector (feature 012)"
---

# Tasks: Dependency Inspector

**Input**: Design documents from `/specs/012-dependency-inspector/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/dependency_inspector_api.md, quickstart.md

**Tests**: REQUIRED — constitution principle II (Test Coverage, NON-NEGOTIABLE) mandates tests for every functional behaviour. Test tasks are included below for each pure function.

**Organization**: Tasks are grouped by user story (from spec.md) so each story can be implemented and verified independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 — maps to user stories in spec.md
- File paths are exact; single-project layout rooted at repo root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the module skeleton. No new tooling or dependencies are introduced — Python 3.12+, customtkinter, pytest, ruff are already configured.

- [X] T001 Create empty module `src/starfield_tool/tools/dependency_inspector.py` with module docstring and a `# Public API: build_dependency_graph, ancestors, descendants, assign_sides, DependencyInspectorTool` comment header.
- [X] T002 [P] Create empty test file `tests/test_dependency_inspector_graph.py` with a top-level docstring ("Tests for dependency graph construction, closure, and color assignment.").
- [X] T003 [P] Create empty test file `tests/test_dependency_inspector_router.py` with a top-level docstring ("Tests for the greedy connector side-router.").

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the pure-function core used by every user story — graph construction, closure, router, and the `ToolModule` shell registered in `app.py`. No UI rendering yet.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Add `Kind`, `Edge`, `MissingDep`, `DependencyGraph`, `InspectorViewState`, and `Side` type/dataclass declarations (per `specs/012-dependency-inspector/data-model.md`) to `src/starfield_tool/tools/dependency_inspector.py`.
- [X] T005 Implement `build_dependency_graph(creations, catalogue, soft_deps) -> DependencyGraph` in `src/starfield_tool/tools/dependency_inspector.py` per research.md Decisions 1–3 and 6: aggregate hard (`required_mods`) + soft edges, filter missing endpoints, drop forward-pointing edges, sort adjacency lists by load position, compute `no_deps` and `missing_hard`, compute `palette_color` using the 6-color palette imported from `starfield_tool.tools.load_order_diff._MOVE_COLORS`.
- [X] T006 [P] Implement `ancestors(graph, node, visible_edges)` and `descendants(graph, node, visible_edges)` as BFS helpers in `src/starfield_tool/tools/dependency_inspector.py`; must handle cycles via a visited set and exclude `node` from the returned set.
- [X] T007 [P] Implement `assign_sides(edges, position) -> dict[tuple[str, str], Side]` in `src/starfield_tool/tools/dependency_inspector.py` per research.md Decision 4: greedy longest-first, count crossings against already-placed edges on each side, tie-break on imbalance.
- [X] T008 Add `class DependencyInspectorTool(ToolModule)` skeleton to `src/starfield_tool/tools/dependency_inspector.py` with `name = "Dependency Inspector"`, `description = ...`, a no-op `mount(parent, context)` that builds an empty `ctk.CTkFrame`, and `on_refresh()` that rebuilds the graph via `build_dependency_graph` but does not yet render it.
- [X] T009 Register `DependencyInspectorTool` in `src/starfield_tool/app.py` alongside the existing tools (follow the pattern used by `CreationLoadOrderTool`); wire it into the same refresh/context plumbing the Installed Creations tab uses.
- [X] T010 [P] Write tests in `tests/test_dependency_inspector_graph.py` covering `build_dependency_graph`: (a) hard-only graph, (b) hard+soft merged, (c) edge with missing installed endpoint dropped + recorded in `missing_hard` only for hard, (d) `no_deps` set correctly, (e) adjacency lists sorted by load position, (f) forward-pointing edge silently dropped, (g) palette color of a node with only incoming edges falls back to incoming, (h) palette color with both present uses outgoing (precedence), (i) tie in "first" resolved by load-position tiebreak, (j) cycle does not infinite-loop during build.
- [X] T011 [P] Write tests in `tests/test_dependency_inspector_graph.py` covering `ancestors` / `descendants`: (a) simple chain, (b) diamond (shared ancestor NOT treated as sibling), (c) cycle participants all returned, (d) `visible_edges` predicate excludes hidden edges from traversal, (e) node with no edges returns empty sets.
- [X] T012 [P] Write tests in `tests/test_dependency_inspector_router.py` covering `assign_sides`: (a) deterministic output for identical input, (b) on a canned crossing-heavy fixture, total crossings under `assign_sides` is strictly less than the all-left-side baseline (SC-005 proxy), (c) empty edge list returns empty dict, (d) two non-crossing edges are both assigned the same side only if that doesn't create imbalance.

**Checkpoint**: `pytest` green. `ruff check .` clean. The tab appears in the app but renders an empty frame.

---

## Phase 3: User Story 1 — Inspect dependency impact before removing a creation (Priority: P1) 🎯 MVP

**Goal**: Full read-only visualisation: centered datagrid of installed creations in load order, connectors drawn on both sides between dependency pairs, palette-coloured rows for participating creations, collapsed (regular-coloured) rows for creations with no dependency info, warning icon on rows with missing hard dependencies, and click-to-highlight directed-closure with the diff-dialog white-glow + dim treatment.

**Independent Test**: Launch the app with a profile containing creations whose hard dependencies are known. Open the Dependency Inspector tab, select a creation with both upstream and downstream edges, and verify the full directed closure highlights (ancestors + descendants), siblings remain dim, and rows with missing hard deps show a warning indicator.

### Implementation for User Story 1

- [X] T013 [US1] In `src/starfield_tool/tools/dependency_inspector.py`, implement the UI layout inside `DependencyInspectorTool.mount`: a central `ttk.Treeview` flanked by a left `tkinter.Canvas` and a right `tkinter.Canvas` inside a single `ctk.CTkFrame` container. Match row height and font conventions with `load_order_diff.py`.
- [X] T014 [US1] Populate the datagrid from `DependencyGraph.order` using `Creation.display_name`; apply `DependencyGraph.palette_color[content_id]` as the row foreground for participating rows and the regular row color for `no_deps` rows (collapsed). Add a leading warning-indicator column that renders an icon whenever `content_id in missing_hard`.
- [X] T015 [US1] Call `assign_sides(...)` over the currently visible edges and draw each edge on the appropriate Canvas as a Bezier `create_line(..., smooth=True)` in the source row's palette color, with `_DOT_RADIUS` endpoint dots — mirror the drawing helper pattern in `src/starfield_tool/tools/load_order_diff.py`.
- [X] T016 [US1] Bind Treeview row selection to update `InspectorViewState.selected`; recompute `ancestors ∪ descendants` (using a `visible_edges` predicate that honours the current `hide_soft` value — False by default in this story) and re-render connectors in two passes: highlighted edges drawn in white with a slight glow (reuse the PIL alpha-outline trick from `load_order_diff._hex_with_alpha`), all other edges dimmed by reducing opacity. Rows not in the highlight set also dim.
- [X] T017 [US1] Bind click on empty canvas / click on the already-selected row to clear `selected` and re-render with default (non-highlighted) styling.
- [X] T018 [US1] Wire `DependencyInspectorTool.on_refresh` (from T008) to rebuild the graph from the current `ModuleContext` snapshot, clear `selected`, preserve toggle state, and fully re-render. Trigger it on the same signals the Installed Creations tab listens to.
- [ ] T019 [US1] Verify manually against `specs/012-dependency-inspector/quickstart.md` steps 1–5 and step 10 (warning icon for missing hard deps). Record any deviations in-line. **(deferred — requires running the GUI against a real Starfield profile)**

**Checkpoint**: MVP — Dependency Inspector renders the graph, highlights directed closures on selection, and surfaces missing-hard-dep warnings. Soft-toggle and no-deps-toggle not yet wired (show both by default).

---

## Phase 4: User Story 2 — Filter out soft dependencies to focus on hard ones (Priority: P2)

**Goal**: Add a "Hide soft dependencies" toggle in the inspector toolbar. Toggling it updates connector visibility (and the closure traversal during highlighting) but MUST NOT recompute palette colours or collapse state (per clarification Q2).

**Independent Test**: With a creation that has a mix of hard and soft outgoing deps, toggle "Hide soft dependencies" and confirm only hard connectors remain; confirm the creation's palette colour and its collapsed/expanded status are unchanged; re-enable and confirm soft connectors return without a reload.

### Implementation for User Story 2

- [X] T020 [US2] Add a `ctk.CTkCheckBox` labelled "Hide soft dependencies" to the toolbar area of the inspector frame in `src/starfield_tool/tools/dependency_inspector.py`; bind its variable to `InspectorViewState.hide_soft`.
- [X] T021 [US2] Wire the checkbox callback to trigger a connector re-render only (no graph rebuild, no palette/collapse recomputation). The `visible_edges` predicate used by the router and by the highlight traversal must filter out `edge_kind == "soft"` when `hide_soft` is True.
- [ ] T022 [US2] Verify manually against `specs/012-dependency-inspector/quickstart.md` step 6, including the non-recomputation invariant (palette color and collapsed state of a soft-only creation stay the same when soft is hidden). **(deferred — requires GUI)**

**Checkpoint**: Hard-only view works; palette colours and collapse states remain stable across toggle flips.

---

## Phase 5: User Story 3 — Hide creations with no dependencies to declutter (Priority: P3)

**Goal**: Add a "Hide creations with no dependencies" toggle that removes `no_deps` rows from the grid; connectors must still render correctly across the resulting row gaps.

**Independent Test**: Toggle "Hide creations with no dependencies" on a load order containing both kinds of rows — only participating rows remain; selecting any creation still highlights its full directed closure; connectors between two visible rows that used to span hidden rows render correctly.

### Implementation for User Story 3

- [X] T023 [US3] Add a `ctk.CTkCheckBox` labelled "Hide creations with no dependencies" to the toolbar area in `src/starfield_tool/tools/dependency_inspector.py`; bind its variable to `InspectorViewState.hide_no_deps`.
- [X] T024 [US3] Wire the checkbox callback to hide/show rows whose `content_id` is in `DependencyGraph.no_deps` and re-run `assign_sides` + canvas redraw (row positions shift, so connector endpoints must be re-snapped to new row Y coordinates). Do NOT rebuild the graph. Do NOT recompute palette or collapse sets.
- [ ] T025 [US3] Verify manually against `specs/012-dependency-inspector/quickstart.md` step 7 — including the edge case where a highlighted chain spans hidden rows. **(deferred — requires GUI)**

**Checkpoint**: All three user stories independently functional. All toggles composable (both on at once works).

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T026 Run `ruff check .` and fix any lint findings in `src/starfield_tool/tools/dependency_inspector.py`, `src/starfield_tool/app.py`, and the two new test modules.
- [X] T027 Run the full `pytest` suite from the repo root and fix any regressions elsewhere caused by the `app.py` registration change.
- [ ] T028 Performance smoke-check per `specs/012-dependency-inspector/quickstart.md`: initial render ≤ 2 s for a 500-creation fixture (SC-001), selection highlight ≤ 200 ms (SC-002), toggle update ≤ 300 ms (SC-004). **(deferred — requires GUI)**
- [ ] T029 Run full `quickstart.md` end-to-end and confirm every listed check passes. **(deferred — requires GUI)**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Phase 1. **Blocks all user stories.**
- **User Story 1 (Phase 3, P1)**: depends on Phase 2.
- **User Story 2 (Phase 4, P2)**: depends on Phase 3 (re-uses the mounted UI + render pipeline).
- **User Story 3 (Phase 5, P3)**: depends on Phase 3 (same reason). Independent of Phase 4.
- **Polish (Phase 6)**: depends on any shipped story; final run after all stories complete.

### Within Each Phase

- Foundational: T004 first (types), then T005 (graph build uses types). T006, T007, and T008 are [P] after T004. T009 depends on T008. Test tasks T010–T012 [P] can run in parallel as soon as their target function exists.
- US1: T013 before T014–T017 (UI scaffolding first). T014 and T015 must precede T016. T018 after the above.
- US2 and US3 are each small and self-contained; they share the `dependency_inspector.py` file so T020→T021 and T023→T024 are sequential within each story, but US2 and US3 could be split across developers once US1 is merged.

### Parallel Opportunities

- Phase 1: T002, T003 in parallel.
- Phase 2: T006, T007 in parallel after T004. Test tasks T010, T011, T012 all [P].
- Phase 6: T026, T027 can run in parallel.

---

## Parallel Example: Phase 2 (Foundational)

```bash
# After T004 (types) lands:
Task: "T006 Implement ancestors/descendants BFS"
Task: "T007 Implement assign_sides greedy router"

# After T005, T006, T007 land, run all tests in parallel:
Task: "T010 Write build_dependency_graph tests"
Task: "T011 Write closure tests"
Task: "T012 Write router tests"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational) — pure functions tested and green; empty tab visible in the app.
3. Complete Phase 3 (US1) — full visualisation, selection highlight, missing-hard warnings.
4. **STOP and validate** against quickstart.md steps 1–5 + 10. MVP is demonstrable here.

### Incremental Delivery

1. Ship MVP (Phase 1 + 2 + 3).
2. Add Phase 4 (US2) — soft-dep toggle. Validate, ship.
3. Add Phase 5 (US3) — no-deps toggle. Validate, ship.
4. Polish (Phase 6) before final merge to `dev`.

---

## Notes

- All tasks target single-project layout: `src/starfield_tool/...` and `tests/...` at repo root.
- Tests are mandatory (constitution II). Manual UI verification follows project precedent; it supplements — does not replace — the pytest coverage of pure functions.
- No new external dependencies are introduced.
- Branch convention: continue on `012-dependency-inspector` (cut from `dev` per `project_branches` memory). Never target `main` directly.
