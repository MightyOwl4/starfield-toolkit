# Contract: load_order_sorter Public API

The `load_order_sorter` package exposes a functional API. The `starfield_tool` UI calls these functions and renders the results. There is no shared mutable state.

## sort_creations()

Main entry point. Collects constraints from all active sorters, merges with priority resolution, solves to produce a proposed order.

```
sort_creations(
    items: list[SortItem],
    sorters: list[str] = ["category"],  # names of active sorters in priority order (last = highest)
    masterlist_path: Path | None = None,  # path to LOOT masterlist YAML (required if "loot" in sorters)
) -> SortResult
```

**Behavior**:
- All active sorters run independently on the original order.
- Each sorter produces a list of `SortConstraint` (tier assignments, load-after rules).
- Constraints are merged: tier conflicts resolved by priority (higher wins), load-after rules accumulated (cycles broken by dropping lower-priority constraint).
- A single solver pass produces the final order: group by tier → topological sort within tier → original position as tiebreaker.
- Items with no constraints retain original relative positions (stable).
- Returns `SortResult` with `unchanged=True` if proposed order matches current.
- Each `SortedItem.decision` carries attribution (`sorter_name`) for the winning tier constraint.

**Errors**:
- If `"loot"` is in sorters but `masterlist_path` is None or file is unreadable, the LOOT sorter is silently skipped (falls back to remaining sorters).

## load_snapshot() / save_snapshot()

```
save_snapshot(
    name: str,
    plugins: list[str],
    path: Path,
    tool_version: str = "",
) -> None

load_snapshot(path: Path) -> Snapshot
```

**Behavior**:
- `save_snapshot`: Writes a JSON snapshot file.
- `load_snapshot`: Reads and validates a snapshot file. Raises `ValueError` on invalid format.

## clear_masterlist_cache() (future consideration)

If the masterlist is fetched from GitHub, a future function may manage local caching. For v1, the masterlist is either bundled or fetched on demand by the UI layer.

## Dependency Direction

```
load_order_sorter → pyyaml, stdlib only
load_order_sorter → NEVER imports bethesda_creations or starfield_tool
starfield_tool → load_order_sorter (calls sort_creations, load/save_snapshot)
starfield_tool → bethesda_creations (for categories via CreationInfo)
```
