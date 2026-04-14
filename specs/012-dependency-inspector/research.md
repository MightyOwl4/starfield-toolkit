# Research: Dependency Inspector

**Phase 0 output** — resolves technical unknowns before design.

All spec-level ambiguities were resolved in `/speckit.clarify` (see spec Clarifications section). This document captures technical approach decisions and alternatives considered.

---

## Decision 1 — Dependency data sources

**Decision**: Aggregate from two existing sources already present in the repo:

1. **Hard dependencies** — `required_mods` field on each catalogue entry (`src/bethesda_creations/catalogue.py`, already populated from the Bethesda API `summaryPC.json` / catalogue fetch). Matched by `content_id`.
2. **Soft dependencies** — JSON output of the description-dependency parser (`src/description_parser/`, feature 008). Matched by the existing `filename → content_id` mapping already established during that feature.

**Rationale**: Both sources are already populated by earlier features (006, 008) and consumed by the sort pipeline. Re-using them avoids any new scraping, LLM calls, or API traffic, and keeps the inspector in sync with the data the sorter already trusts.

**Alternatives considered**:

- Parse descriptions live from within the inspector — rejected: violates KISS, duplicates feature 008, and blocks UI on a slow path.
- Build a new unified dependency file — rejected: adds persistence surface for no benefit; memory-only aggregation at tab load is fast enough (SC-001 ≤ 2 s for 500 creations).

---

## Decision 2 — Graph representation

**Decision**: Two plain `dict[str, list[str]]` adjacency maps keyed by `content_id` — `out_edges[a] = [b, c]` means "a depends on b, a depends on c"; `in_edges[b] = [a]` is the reverse index. Edge kind (hard/soft) stored alongside as `dict[tuple[str, str], Kind]`.

**Rationale**: The operations we need are: enumerate edges for drawing, BFS ancestors/descendants from a node, look up "first outgoing" by load-order position. Two dicts + a kind map cover all three with zero indirection. No networkx.

**Alternatives considered**:

- `networkx.DiGraph` — rejected: new dependency for trivial BFS that's ~10 lines.
- Edge-list-only — rejected: ancestor BFS becomes O(|E|) per hop instead of O(|neighbours|).

---

## Decision 3 — Palette-color assignment algorithm

**Decision**: Deterministic, computed once at graph build.

1. Assign palette colors to edges in a canonical edge order: sort edges by `(load_position(source), load_position(target))`, then rotate through the 6-color palette already defined in `load_order_diff._MOVE_COLORS`.
2. For each Creation `c` with any edges:
   - If `c` has outgoing edges: its color = color of the outgoing edge whose *target* has the earliest load-order position.
   - Else (only incoming): its color = color of the incoming edge whose *source* has the earliest load-order position.
3. Creations with no edges → regular (non-palette) row color.

**Rationale**: Per clarification Q4, "first" is by load-order position of the other endpoint. Freezing the assignment at build time (per Q2) means toggles never re-run this. Using the diff dialog's existing palette keeps visual language consistent.

**Alternatives considered**:

- Per-node color (rainbow across nodes) — rejected: the spec specifies edge-derived colors to make chains traceable visually.
- Graph-coloring minimisation — rejected: over-engineered; the rotating palette already provides enough separation in practice.

---

## Decision 4 — Connector side router (left vs right)

**Decision**: Greedy heuristic — process edges in descending order of vertical span `|load_position(source) - load_position(target)|`. For each edge, count the number of already-placed edges it would cross on the **left** side vs the **right** side; choose the side with fewer crossings. Ties broken by current imbalance (pick the less-full side).

**Rationale**: Minimising crossings exactly is a well-known hard problem (related to 2-page book embedding). A greedy longest-first heuristic routinely gets within 10–15% of optimum on small graphs, runs in O(|E|²) which is fine at our scale (<1000 edges even in the 500-creation case), is one function, and is easy to unit-test by comparing crossing counts against the all-same-side baseline (SC-005 requires ≥80% improvement, not optimality).

**Alternatives considered**:

- Optimal crossing minimisation (ILP) — rejected: massive complexity, new dependency, out of scope.
- Simple side-by-parity (odd on left, even on right) — rejected: doesn't react to actual edge geometry; fails SC-005 on adversarial inputs.
- Barycenter/sweep methods — rejected: overkill; not materially better than greedy for our scale.

---

## Decision 5 — Selection highlight — transitive closure

**Decision**: On select, compute `ancestors(node) = BFS over in_edges` and `descendants(node) = BFS over out_edges` (respecting the current soft-hidden toggle — hidden edges are not traversed). The highlight set is `{node} ∪ ancestors ∪ descendants`; highlighted edges are those whose both endpoints are in the highlight set *and* whose direction agrees with the chain (outgoing from ancestors' side, incoming to descendants' side).

**Rationale**: Matches clarification Q1 — directed closure, no siblings. BFS handles cycles naturally (visited set). Respecting the soft-hidden toggle during traversal means hiding soft deps also shrinks the highlighted chain, which matches user intuition ("I hid these, they should be out of the picture").

**Alternatives considered**:

- Connected-component highlight — rejected per Q1.
- Cache per-node closures at build time — rejected: graph is small, toggles change traversability; building lazily on click is simpler and stays under the 200 ms budget.

---

## Decision 6 — Missing-endpoint handling

**Decision**: During aggregation, any dependency edge where either endpoint's `content_id` is not in the installed-creations set is dropped before the graph is constructed. A separate list `missing_hard: dict[str, list[MissingDep]]` records dropped *hard* dependencies keyed by the dependent creation's `content_id`. Rows for those creations render a warning icon in a dedicated status column; clicking the icon (future enhancement — not in scope here) would list the missing targets. Missing soft dependencies are silently discarded.

**Rationale**: Matches clarification Q5. Keeps the graph clean (no stub nodes muddying closures or color), while preserving the actionable information ("this creation is probably broken") as a row-level signal.

---

## Decision 7 — Tab registration and refresh

**Decision**: Register a new `DependencyInspectorTool(ToolModule)` alongside the existing tools in `starfield_tool/app.py`. It consumes the same `ModuleContext` and subscribes to the same installation / catalogue refresh signals that `CreationLoadOrderTool` ("Installed Creations") already uses — so manual refresh and cache-invalidation behaviour come for free.

**Rationale**: Matches clarification Q3 — read-only, replicates Installed Order's refresh/outdated behaviour. No new infra.

---

## Open questions

None. All spec clarifications applied; all technical choices default to the simplest viable option under the constitution.
