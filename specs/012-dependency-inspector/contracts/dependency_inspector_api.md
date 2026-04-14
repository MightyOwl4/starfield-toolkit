# Internal Module Contract: `starfield_tool.tools.dependency_inspector`

Public (intra-project) API surface of the new tool module. All functions are pure unless noted; side-effecting UI code lives on `DependencyInspectorTool` and is not part of this contract.

---

## `build_dependency_graph`

```python
def build_dependency_graph(
    creations: list[Creation],            # in load order, installed only
    catalogue: Mapping[str, dict],        # content_id -> catalogue entry (must expose "required_mods")
    soft_deps: Mapping[str, list[str]],   # content_id -> list of target content_ids (soft)
) -> DependencyGraph: ...
```

**Inputs**

- `creations`: already filtered to installed creations, sorted by `load_position`.
- `catalogue`: as produced by `bethesda_creations.catalogue`. Missing entries tolerated (creation contributes no hard deps).
- `soft_deps`: as produced by the description-parser pipeline and mapped through the existing filename→content_id map; empty dict is valid.

**Behaviour**

- Builds `out_edges`, `in_edges`, `edge_kind` from the union of hard (`required_mods`) and soft (`soft_deps`) edges.
- Drops any edge where either endpoint is not installed. Hard drops are recorded in `missing_hard`; soft drops are silent.
- Drops edges where `position[target] >= position[source]` (would imply a later creation being a prerequisite — treated as data error; silently ignored).
- Computes `palette_color` per Decision 3 of `research.md`.
- `no_deps` = creations with zero in+out edges after filtering.

**Failure modes**: none — any malformed input is skipped silently except hard misses which are surfaced in `missing_hard`.

---

## `closure`

```python
def ancestors(graph: DependencyGraph, node: str, visible_edges: Callable[[str, str], bool]) -> set[str]: ...
def descendants(graph: DependencyGraph, node: str, visible_edges: Callable[[str, str], bool]) -> set[str]: ...
```

- BFS over `in_edges` / `out_edges` respectively.
- `visible_edges(source, target)` is the predicate applied to each edge during traversal (used to honour the `hide_soft` toggle).
- Handles cycles via visited set. The returned sets do **not** include `node` itself.

---

## `assign_sides`

```python
def assign_sides(
    edges: Iterable[tuple[str, str]],
    position: Mapping[str, int],
) -> dict[tuple[str, str], Side]: ...
```

- Returns a `Side` ("left" / "right") per edge, chosen by the greedy longest-first heuristic in Decision 4.
- Deterministic: identical inputs yield identical outputs.

**Contract test**: for a canned set of crossing-heavy edges, the total crossings under `assign_sides` must be strictly less than the all-same-side baseline. (SC-005 proxy.)

---

## `DependencyInspectorTool(ToolModule)`

Implements the existing `ToolModule` interface so it integrates with `starfield_tool.app` just like the other tools.

- `name = "Dependency Inspector"`
- `description = "Visualise hard and soft dependencies across the load order"`
- Mounts a `ttk.Treeview` (centered datagrid) flanked by two `tkinter.Canvas` widgets (left + right connectors) inside a `ctk.CTkFrame`.
- Toolbar: two `ctk.CTkCheckBox` controls — "Hide soft dependencies", "Hide creations with no dependencies".
- Subscribes to the same `ModuleContext` refresh/change notifications that `CreationLoadOrderTool` uses; rebuilds the graph and re-renders in response.
- Publishes no events; does not mutate any shared state.
