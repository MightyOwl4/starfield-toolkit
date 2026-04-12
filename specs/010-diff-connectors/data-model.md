# Data Model: Diff Dialog Visual Connectors and Hint Dialog

**Date**: 2026-04-12 | **Branch**: `010-diff-connectors`

## Modified entities

### `SortConstraint` (src/load_order_sorter/models.py)

Existing fields unchanged. One new field:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| note  | str  | `""`    | Optional explanatory text from the constraint source. Populated by the rulebook sorter from the rule's `note` field. Empty for sorters that don't have a natural note concept (CAT, TES4; LOOT may later populate with masterlist `msg` content but is out of scope here). |

**Validation**: No constraint on content — free-form text. Empty string is the sentinel for "no note".

### `SortDecision` (src/load_order_sorter/models.py)

Existing fields unchanged (`tier`, `sorter_name`, `load_after`, `load_after_sorters`, `warnings` remain as-is). One new field:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| all_constraints | `list[SortConstraint]` | `[]` | Every `SortConstraint` that targeted this plugin during the merge, regardless of whether it won its concern. Populated by `_merge_constraints`. Preserves raw per-plugin input so the UI can explain the decision without re-running sorters. |

**Validation**: Order is preserved from merge-time iteration; no sorting is applied. Consumers that need priority order should sort on read.

## New behavior in existing pipeline

### `_merge_constraints` (src/load_order_sorter/pipeline.py)

After computing `decision.tier`, `decision.load_after`, `decision.load_after_sorters`, and `decision.warnings` (lines 92-120 today), add:
```python
decision.all_constraints = list(plugin_constraints)
```
before storing the decision. This captures *every* constraint touching the plugin, winners and losers alike.

### Rulebook sorter (src/load_order_sorter/sorters/rulebook.py)

For every `SortConstraint` emitted (both order and tier branches, both curated and user):
- Set `sorter_name=f"RULE:{entry['filename']}"` for `type="load_after"` constraints.
- Set `sorter_name=f"RULE:{entry['filename']}({tier})"` for `type="tier"` constraints — retains the tier-in-label convention established by category/LOOT sorters.
- Set `note=rule.get("note", "")`.

## UI-only entities (no schema change)

These are runtime objects within the diff dialog, not persisted:

### `Move` (runtime, `DiffDialog._move_colors` lookup)

| Field | Type | Description |
|-------|------|-------------|
| plugin_name | str | Key into `_proposed_map` / `_accepted` / etc. |
| color | str | Hex color from `_MOVE_COLORS` palette, assigned by proposed-order position. |

### Connector (runtime, drawn on Canvas)

Composed of three canvas items per move, all tagged `"connector"` for bulk deletion:
1. Left endpoint dot — small filled oval at `(r, ly)` where `r` is the dot radius.
2. Right endpoint dot — small filled oval at `(W-r, ry)` where `W` is canvas width.
3. Bezier curve — smooth line from the two endpoints with two midpoint control points for the S-curve shape.

All three items share the move's assigned color.

### Hints dialog state (runtime, `CTkToplevel`)

Transient. Displays `plugin.decision.all_constraints` sorted by `priority` desc, with:
- Per-row widget tree: sorter label, type+value, priority, optional WINNER badge, optional greyed note line.
- No persistence.

## Relationships

- `SortedItem.decision` → `SortDecision.all_constraints` → list of `SortConstraint` — this is the read path the hints dialog uses.
- `DiffDialog._proposed_map[name]` returns the `SortedItem`, whose `.decision.all_constraints` drives the hints dialog content.
- `DiffDialog._move_colors[name]` assigns UI color; used by both the canvas drawing and the ttk tag that colors the Info column.

## Backward compatibility

- Adding `note` and `all_constraints` as defaulted dataclass fields is backward compatible with existing constructor calls in tests and production code.
- `SortConstraint(plugin_name="X", type="tier", tier=3, sorter_name="CAT", priority=10)` still works — `note=""` is implicit.
- All existing tests continue to pass with no edits required.
