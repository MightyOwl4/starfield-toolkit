# Data Model: Fast Lane Category-Based Classification Refinement

**Date**: 2026-04-13 | **Branch**: `011-fast-lane-categories`

## New constants (module-level in `src/starfield_tool/tools/fast_lane_check.py`)

### `_SAFE_CATEGORIES: frozenset[str]`

```
Skins, Apparel, Body, Photo Mode, Audio
```

Categories considered entirely unaffected by the Free Lanes update. Creations whose non-meta categories are all members of this set skip the version check and render as Unaffected.

### `_LOW_RISK_CATEGORIES: frozenset[str]`

```
Weapons, Gear, Ships
```

Categories considered unlikely to be affected but worth surfacing for optional verification. Creations whose non-meta categories are all members of `(SAFE ∪ LOW_RISK)` AND have at least one LOW_RISK category are shown with Low-risk annotation when their version would otherwise flag as Not updated.

### `_META_CATEGORIES: frozenset[str]`

```
Load Order Neutral, Lore Friendly, Work in Progress
```

Auxiliary descriptors stripped from category lists before set-membership evaluation. They never count as "in" either SAFE or LOW_RISK.

## New and renamed status constants

| Old | New | Meaning |
|-----|-----|---------|
| `STATUS_SKIN` | `STATUS_UNAFFECTED` | Rename-only. Applies when SAFE check passes or baseline `s=1`. |
| — | `STATUS_LOW_RISK` | New. Version would flag Not-updated, but LOW_RISK check passes. |
| `STATUS_UPDATED` | unchanged | Current > baseline. |
| `STATUS_LIKELY_UPDATED` | unchanged | Current == baseline AND PS4/PS5 in platforms. |
| `STATUS_NOT_UPDATED` | unchanged | Current == baseline, no PS support, no tier relief. |
| `STATUS_UNKNOWN` | unchanged | Missing baseline or current version. |

## Row dict additions (runtime only)

Each row in `FastLaneCheckTool._rows` is a plain `dict` populated during `_run_comparison`. Two optional keys are added:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `unaffected_reason` | `str` | `""` | First matching category from the creation's category list (e.g., `"Apparel"`), or `"Skin"` when the baseline `s=1` flag triggered. Shown in the status text. |
| `low_risk_reason` | `str` | `""` | First matching LOW_RISK category name. Shown in the status text. |

These are read by `_populate_tree` to format the status cell.

## Classification flow (decision order in `_run_comparison`)

For each row after the API fetch:

```
if baseline_entry is None:
    → STATUS_UNKNOWN

non_meta = categories - _META_CATEGORIES

if baseline.s == 1 or (non_meta and non_meta ⊆ _SAFE_CATEGORIES):
    → STATUS_UNAFFECTED (reason = first matching safe cat / "Skin")

status = _classify(current_version, baseline_version)
# STATUS_UPDATED, STATUS_NOT_UPDATED, or STATUS_UNKNOWN

if status == STATUS_NOT_UPDATED and has_ps:
    status = STATUS_LIKELY_UPDATED

if status == STATUS_NOT_UPDATED and non_meta:
    if non_meta ⊆ (_SAFE_CATEGORIES ∪ _LOW_RISK_CATEGORIES) \
       and non_meta ∩ _LOW_RISK_CATEGORIES:
        status = STATUS_LOW_RISK
        reason = first matching low-risk cat

→ status
```

## Tree tag configuration

| Tag name | Foreground | Background | Notes |
|----------|------------|------------|-------|
| `unaffected` | `#888888` (grey) | none | Renamed from `skin`. Same styling. |
| `low_risk` | `#1a1a1a` or white (tbd for contrast) | `#a37015` muted amber | New. Softer than `not_updated` (`#d4a71a`). |
| `not_updated` | `#1a1a1a` | `#d4a71a` | Unchanged. |
| `likely_updated` | white | `#5f7f3a` muted green | Unchanged from 010. |
| `unknown` | `#888888` | none | Unchanged. |

## Sort key (`_status_sort_key`)

Mapping (lower = higher urgency):

| Status | Key |
|--------|-----|
| `STATUS_NOT_UPDATED` | 0 |
| `STATUS_UNKNOWN` | 1 |
| `STATUS_LOW_RISK` | 2 |
| `STATUS_LIKELY_UPDATED` | 3 |
| `STATUS_UNAFFECTED` | 4 |
| `STATUS_UPDATED` | 5 |

## Summary line output

```
{total} total | {not_updated} not updated | {low_risk} low risk |
{likely} likely updated | {updated} updated | {unknown} unknown |
{unaffected} unaffected
```

## Unchanged interfaces

- `data/creations_baseline.json` schema: no change, no regeneration needed.
- `CreationInfo.categories`: already populated by `parse_response`, consumed as-is.
- Public `FastLaneCheckTool.initialize / start` / `ToolModule` contract: no change.
- Existing `_classify(current, baseline)` function: no change. The new logic wraps it, not replaces it.

## Backward compatibility

- Rows persisted in memory only (no disk state affected).
- Old tests that import `STATUS_SKIN` need a rename; there is no production consumer outside the module and its tests.
- Baseline file bundle unchanged — no installer rebuild needed just for this feature.
