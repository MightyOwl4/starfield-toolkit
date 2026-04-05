# Data Model: TES4 Master Dependency Sorting

**Date**: 2026-04-05 | **Branch**: `006-tes4-master-sort`

## Entities

### MasterMap

A mapping from each creation's plugin filename to the list of master plugin filenames it depends on (extracted from TES4 headers, filtered to creation-only masters).

| Field | Type | Description |
|-------|------|-------------|
| key | string | Plugin filename (e.g., `CommandNPCs_MuteResponses.esm`) |
| value | list[string] | Master filenames this plugin depends on (e.g., `["CommandNPCs.esm"]`) |

**Built from**: Parsing TES4 MAST subrecords from `.esm`/`.esp`/`.esl` files in the game's Data directory.

**Lifecycle**:
- Built once per auto-sort invocation
- Cached in memory for the session
- Invalidated when file watcher detects changes in Data directory
- Filtered: base game masters (Starfield.esm, SFBGS*.esm, etc.) excluded
- Filtered: masters not matching any installed creation plugin excluded

### ValidationViolation

Describes a single ordering violation where a creation appears before one of its TES4 masters.

| Field | Type | Description |
|-------|------|-------------|
| plugin_name | string | The dependent plugin that is out of order |
| display_name | string | User-visible creation name |
| master_name | string | The master plugin it must load after |
| master_display_name | string | User-visible name of the master creation |
| current_position | integer | Where the dependent is in the proposed order |
| master_position | integer | Where the master is in the proposed order |

**Used by**: The apply validation check to produce the error message.

## Integration with Existing Models

### SortConstraint (existing, no changes needed)

The TES4 sorter produces standard `SortConstraint` objects:
- `type = "load_after"`
- `after = <master plugin name>`
- `priority = 100`
- `sorter_name = "TES4"`

### SortDecision (existing, no changes needed)

The merger accumulates TES4 `load_after` constraints into the existing `load_after` list via set union. TES4 does not produce tier constraints.

### Solver (existing, needs modification)

The `_solve` function needs a pre-solve step: promote items to higher tiers when their `load_after` targets are in a higher tier. This ensures cross-tier TES4 dependencies are not dropped.
