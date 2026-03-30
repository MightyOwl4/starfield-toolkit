"""Constraint-based sorting pipeline with priority resolution."""
from collections import defaultdict
from pathlib import Path

from load_order_sorter.models import (
    SortItem, SortConstraint, SortDecision, SortedItem, SortResult,
)
from load_order_sorter.sorters import category as category_sorter
from load_order_sorter.sorters import loot as loot_sorter

_SORTERS = {
    "category": category_sorter,
    "loot": loot_sorter,
}

DEFAULT_TIER = 9


def sort_creations(
    items: list[SortItem],
    sorters: list[str] | None = None,
    masterlist_path: Path | None = None,
) -> SortResult:
    """Run the sorter pipeline and return a proposed order.

    All active sorters run independently on the original order.
    Constraints are merged with priority resolution, then solved
    in a single pass.
    """
    if sorters is None:
        sorters = ["category"]

    # Collect constraints from all sorters
    all_constraints: list[SortConstraint] = []
    for name in sorters:
        if name == "loot":
            if masterlist_path and masterlist_path.exists():
                all_constraints.extend(loot_sorter.sort(items, masterlist_path))
        elif name == "category":
            all_constraints.extend(category_sorter.sort(items))

    # Merge constraints
    decisions = _merge_constraints(all_constraints)

    # Solve to produce final order
    sorted_items = _solve(items, decisions)

    # Check if order actually changed
    unchanged = all(
        si.original_index == si.new_index for si in sorted_items
    )

    return SortResult(items=sorted_items, unchanged=unchanged)


def _merge_constraints(
    constraints: list[SortConstraint],
) -> dict[str, SortDecision]:
    """Merge all constraints with priority-based conflict resolution."""
    decisions: dict[str, SortDecision] = {}

    # Group constraints by plugin
    by_plugin: dict[str, list[SortConstraint]] = defaultdict(list)
    for c in constraints:
        by_plugin[c.plugin_name].append(c)

    for plugin_name, plugin_constraints in by_plugin.items():
        decision = SortDecision(tier=DEFAULT_TIER)

        # Resolve tier: highest-priority sorter wins
        best_tier_priority = -1
        for c in plugin_constraints:
            if c.type == "tier" and c.tier is not None:
                if c.priority > best_tier_priority:
                    decision.tier = c.tier
                    decision.sorter_name = c.sorter_name
                    best_tier_priority = c.priority

        # Accumulate load_after (union)
        after_set: set[str] = set()
        for c in plugin_constraints:
            if c.type == "load_after" and c.after:
                after_set.add(c.after)
        decision.load_after = sorted(after_set)

        # Merge warnings from all sorters
        all_warnings: list[str] = []
        for c in plugin_constraints:
            all_warnings.extend(c.warnings)
        decision.warnings = all_warnings

        decisions[plugin_name] = decision

    return decisions


def _solve(
    items: list[SortItem],
    decisions: dict[str, SortDecision],
) -> list[SortedItem]:
    """Produce final order: group by tier, topological sort within tier."""
    # Assign each item to its tier
    tier_buckets: dict[int, list[SortItem]] = defaultdict(list)
    for item in items:
        decision = decisions.get(item.plugin_name)
        tier = decision.tier if decision else DEFAULT_TIER
        tier_buckets[tier].append(item)

    # Within each tier: topological sort respecting load_after, with
    # original_index as tiebreaker for stability
    result: list[SortedItem] = []
    for tier in sorted(tier_buckets.keys()):
        bucket = tier_buckets[tier]
        ordered = _topo_sort_bucket(bucket, decisions)
        result.extend(ordered)

    # Assign new indices and detect movement
    for i, si in enumerate(result):
        si.new_index = i
        si.moved = si.original_index != i

    return result


def _topo_sort_bucket(
    bucket: list[SortItem],
    decisions: dict[str, SortDecision],
) -> list[SortedItem]:
    """Topological sort within a tier, stable by original_index."""
    names_in_bucket = {item.plugin_name for item in bucket}

    # Build adjacency: plugin → set of plugins it must come after
    must_come_after: dict[str, set[str]] = defaultdict(set)
    for item in bucket:
        decision = decisions.get(item.plugin_name)
        if decision:
            for dep in decision.load_after:
                if dep in names_in_bucket:
                    must_come_after[item.plugin_name].add(dep)

    # Kahn's algorithm with stable tiebreaking
    in_degree: dict[str, int] = {item.plugin_name: 0 for item in bucket}
    dependents: dict[str, list[str]] = defaultdict(list)
    for plugin, deps in must_come_after.items():
        in_degree[plugin] = len(deps)
        for dep in deps:
            dependents[dep].append(plugin)

    # Start with items that have no dependencies, ordered by original_index
    item_map = {item.plugin_name: item for item in bucket}
    ready = sorted(
        [name for name, deg in in_degree.items() if deg == 0],
        key=lambda n: item_map[n].original_index,
    )

    ordered: list[SortedItem] = []
    while ready:
        name = ready.pop(0)
        item = item_map[name]
        decision = decisions.get(name)
        ordered.append(SortedItem(
            plugin_name=item.plugin_name,
            content_id=item.content_id,
            display_name=item.display_name,
            original_index=item.original_index,
            decision=decision,
        ))

        for dependent in dependents.get(name, []):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                # Insert in sorted position by original_index (stable)
                idx = 0
                dep_orig = item_map[dependent].original_index
                while idx < len(ready) and item_map[ready[idx]].original_index < dep_orig:
                    idx += 1
                ready.insert(idx, dependent)

    # If there are cycles (shouldn't happen after merge), append remaining
    for item in bucket:
        if item.plugin_name not in {si.plugin_name for si in ordered}:
            decision = decisions.get(item.plugin_name)
            ordered.append(SortedItem(
                plugin_name=item.plugin_name,
                content_id=item.content_id,
                display_name=item.display_name,
                original_index=item.original_index,
                decision=decision,
            ))

    return ordered
