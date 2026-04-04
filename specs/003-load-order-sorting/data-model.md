# Data Model: Load Order Sorting

## CreationGroup (UI layer)

A creation that may contain one or more plugin files, treated as an atomic unit in the UI.

| Field          | Type        | Description                                                    |
|----------------|-------------|----------------------------------------------------------------|
| key            | str         | First plugin filename — used as group identity                 |
| display_name   | str         | Creation title from ContentCatalog                             |
| files          | list[str]   | All plugin files belonging to this creation, in order          |
| content_id     | str         | Creation content ID from ContentCatalog                        |
| categories     | list[str]   | Bethesda API categories (populated from cache)                 |

**Plugin label**: Single-file → "SFBGS006.esm". Multi-file → "SFTA01.esm, and 5 more".

## SortItem

Input to the sorting pipeline — one per creation group.

| Field          | Type        | Description                                      |
|----------------|-------------|--------------------------------------------------|
| plugin_name    | str         | Group key (first plugin filename)                |
| content_id     | str         | Creation content ID (e.g., "SFBGS006", "TM_...") |
| display_name   | str         | Human-readable creation name                     |
| categories     | list[str]   | Bethesda API categories (e.g., ["Gear", "Quests"]) |
| author         | str         | Creation author (for Bethesda-authored tier 1 detection) |
| original_index | int         | Position in the current load order (0-based)     |

## SortConstraint

A single sorting rule produced by a sorter. Constraints are merged across sorters with priority resolution.

| Field       | Type       | Description                                                    |
|-------------|------------|----------------------------------------------------------------|
| plugin_name | str        | Plugin this constraint applies to                              |
| type        | str        | One of: "tier", "load_after", "pin"                            |
| tier        | int/None   | Target tier (1–11), only for type="tier"                       |
| after       | str/None   | Plugin that must load before this one, only for type="load_after" |
| sorter_name | str        | Which sorter produced this (e.g., "LOOT", "CAT")              |
| priority    | int        | Sorter priority level (higher = wins on conflict)              |
| warnings    | list[str]  | Optional warnings from this sorter for this item               |

**Constraint types**:
- **tier**: "Plugin X belongs in tier N" — conflicts resolved by sorter priority
- **load_after**: "Plugin X must load after plugin Y" — accumulated (union), cycles broken by priority
- **pin**: "Plugin X must not move" — future use for user-defined rules

## SortDecision

The winning constraint(s) for a single item after merge resolution.

| Field       | Type       | Description                                       |
|-------------|------------|---------------------------------------------------|
| tier        | int        | Final assigned tier (1–11)                        |
| sorter_name | str        | Which sorter's tier assignment won                |
| load_after  | list[str]  | Accumulated load-after dependencies               |
| warnings    | list[str]  | Merged warnings from all sorters                  |

## SortResult

Output of the sorting pipeline.

| Field     | Type                          | Description                                   |
|-----------|-------------------------------|-----------------------------------------------|
| items     | list[SortedItem]              | Items in proposed order                       |
| unchanged | bool                          | True if proposed order equals current order   |

## SortedItem

A single item in the proposed sort result.

| Field          | Type              | Description                                      |
|----------------|-------------------|--------------------------------------------------|
| plugin_name    | str               | Plugin filename                                  |
| content_id     | str               | Creation content ID                              |
| display_name   | str               | Human-readable name                              |
| original_index | int               | Position in old order                            |
| new_index      | int               | Position in proposed order                       |
| moved          | bool              | True if original_index != new_index              |
| decision       | SortDecision/None | The winning decision (None if unsorted/unchanged)|

## Snapshot

Saved load order for export/import.

| Field        | Type       | Description                              |
|--------------|------------|------------------------------------------|
| name         | str        | User-provided snapshot name              |
| created      | str        | ISO 8601 timestamp                       |
| tool_version | str        | App version at time of snapshot          |
| plugins      | list[str]  | Plugin filenames in saved order          |

## SortTier (constant data)

The 11-tier community ordering system.

| Tier | Name                        | Locked |
|------|-----------------------------|--------|
| 1    | Master Files                | Yes    |
| 2    | Game Menu / Launch / Framework | No  |
| 3    | Invasive World Edits        | No     |
| 4    | Workshop                    | No     |
| 5    | Gameplay Changes            | No     |
| 6    | Companions                  | No     |
| 7    | Audio / Visual              | No     |
| 8    | HUD / UI                    | No     |
| 9    | Ship Additions              | No     |
| 10   | Character Wearables         | No     |
| 11   | Non-Invasive World Edits    | No     |

## Stability Guarantee

Creations with no constraints from any sorter retain their original relative positions. The solver places them in the default tier (9) and uses `original_index` as the sort key. Within any tier, items without relative ordering constraints are also ordered by `original_index`, preserving stability.

## Constraint Resolution Flow

```
Sorters run independently on original order
          │
          ▼
  ┌─────────────────┐
  │ Collect all      │
  │ SortConstraints  │
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ Merge: tier      │  Higher-priority sorter wins on conflict
  │ conflicts        │
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ Merge: load_after│  Union all; break cycles by dropping
  │ constraints      │  lower-priority constraint
  └────────┬────────┘
           ▼
  ┌─────────────────┐
  │ Solve:           │  Group by tier → topological sort
  │ produce order    │  within tier → original_index tiebreak
  └────────┬────────┘
           ▼
       SortResult
```
