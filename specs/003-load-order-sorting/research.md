# Research: Load Order Sorting Tool

## R1: Standalone Package Architecture

**Decision**: Create `load_order_sorter` as a third peer package alongside `bethesda_creations` and `starfield_tool`.

**Rationale**: The sorting logic is already complex (priority pipeline, stable sort, LOOT parsing, category mapping) and will grow (custom rules). Extracting it prevents coupling with GUI code and enables independent testing. The package exposes a clean function-based API — no classes needed for the sorters themselves.

**Alternatives considered**:
- Inside `starfield_tool`: Mixes domain logic with UI, harder to test, prevents reuse.
- Inside `bethesda_creations`: Wrong concern — Bethesda API ≠ sort logic.

## R2: LOOT Masterlist Format

**Decision**: Parse LOOT's Starfield masterlist YAML from `https://raw.githubusercontent.com/loot/starfield/v0.21/masterlist.yaml`. Use PyYAML for parsing.

**Key structure**:
- **Groups**: Named groups with `after` dependencies forming a DAG. E.g., "Fixes & Resources" loads after "Main Plugins".
- **Plugins**: Each entry has `name`, `group` (reference), optional `after` (load-after dependencies), `msg` (warnings), `requirements`, `incompatibilities`.
- **Conditions**: `file()` and `active()` checks — we'll evaluate basic file-existence conditions.
- **YAML anchors/aliases**: Used extensively for message reuse. PyYAML handles these natively.

**What we extract per plugin**:
- Group assignment → determines tier position
- `after` dependencies → relative ordering constraints
- `msg` entries → warnings shown in diff view
- `requirements` / `incompatibilities` → warnings only (we don't enforce)

## R3: Constraint-Based Sorting (Not Position-Based)

**Decision**: Sorters produce **constraints** (not positions). The pipeline collects all constraints from all sorters, merges them with priority-based conflict resolution, then a single constraint solver produces the final order.

**Why not position-based**: If sorters output positions, they can't see each other's effects. Example: category says "C → tier 1" (position 1), LOOT says "C loads after A". In a position-based multi-pass approach, LOOT wouldn't produce a constraint on pass 1 (C is already after A), but after category moves C to position 1, LOOT's rule is violated. Multi-pass risks infinite loops. A constraint-based single-pass resolves this by considering all rules simultaneously.

**Constraint types**:
- **Tier assignment**: "Plugin X belongs in tier N" (from category sorter, LOOT groups)
- **Relative ordering**: "Plugin X must load after plugin Y" (from LOOT `after` rules)
- **Pinning**: "Plugin X must not move from its current position" (future: user rules)

**Stable sort guarantee**: Items with no constraints from any sorter retain their original relative positions. Within a tier, items are ordered by: (1) relative ordering constraints, (2) original position as tiebreaker. This uses Python's stable Timsort.

**Alternatives considered**:
- Multi-pass iterative sorting: Risks infinite loops, hard to reason about correctness.
- Position-based dict merge (last writer wins): Misses cross-sorter interactions like the A-B-C example above.

## R4: Constraint Merge and Priority Resolution

**Decision**: All sorters run independently on the **original** order (they don't see each other's output). Each produces a list of `SortConstraint` objects. The pipeline merges all constraints into a single set with these rules:

1. **Tier conflicts**: When two sorters assign different tiers to the same plugin, the higher-priority sorter's tier wins. The losing constraint is discarded.
2. **Relative ordering**: All `load_after` constraints are accumulated (union). Conflicts (A after B AND B after A) are detected and the lower-priority constraint is dropped.
3. **No constraint**: Items with no tier assignment from any sorter are placed in a default tier (tier 9 — Default).

The merged constraint set is then solved in a single pass:
1. Group items by their assigned tier.
2. Within each tier, apply topological sort for relative ordering constraints.
3. Items with no relative constraints within a tier are ordered by original position (stable).

**Priority order** (v1):
1. Category-based sorter (lowest priority)
2. LOOT masterlist sorter (higher priority)
3. _(Future: user-defined custom rules — highest priority)_

**Attribution**: Each constraint carries its `sorter_name`. The winning constraint for each item is propagated to `SortedItem.decision` for display in the diff view.

**Rationale**: Single-pass constraint solving is deterministic, has no loop risk, and correctly handles cross-sorter interactions. Topological sort within tiers handles LOOT's `load_after` dependencies naturally.

## R5: Category-to-Tier Mapping

**Decision**: Map Bethesda API categories to the 11-tier system. SFBGS-prefixed content IDs always map to tier 1 (Master Files). Multi-category creations use the highest-priority (lowest-numbered) tier from their category list. Unknown categories map to tier 9 (Default — between Ship Additions and Character Wearables).

**Mapping table**:

| API Category | Sort Tier |
|---|---|
| (SFBGS prefix) | 1 — Master Files |
| Overhaul | 3 — Invasive World Edits |
| Quests | 3 — Invasive World Edits |
| Dungeons | 3 — Invasive World Edits |
| Outpost | 4 — Workshop |
| Gameplay | 5 — Gameplay Changes |
| Immersion | 5 — Gameplay Changes |
| Visuals | 7 — Audio / Visual |
| Gear | 10 — Character Wearables |
| Weapons | 10 — Character Wearables |
| Apparel | 10 — Character Wearables |
| Homes | 11 — Non-Invasive World Edits |
| Vehicles | 11 — Non-Invasive World Edits |
| Miscellaneous | 9 — Default |
| Cheats | 11 — Non-Invasive World Edits |

## R6: Snapshot Format

**Decision**: JSON file with creation identifiers in order, plus metadata.

```json
{
  "name": "My Safe Order",
  "created": "2026-03-30T12:00:00",
  "tool_version": "0.2.0",
  "plugins": ["SFBGS003.esm", "SFBGS006.esm", "TM_abc-123.esm", ...]
}
```

**Rationale**: JSON is human-readable, already used for config and cache. Plugin filenames (not content IDs) are used as the ordering key since Plugins.txt lists filenames.

## R7: PyYAML Dependency

**Decision**: Add `pyyaml>=6.0` as a dependency.

**Rationale**: LOOT masterlists are YAML with anchors/aliases. No stdlib YAML parser exists in Python. PyYAML is the standard choice — small, MIT-licensed, well-maintained, zero transitive dependencies.

**Alternatives considered**:
- `ruamel.yaml`: More features but heavier, unnecessary for read-only parsing.
- Manual parsing: YAML anchors make this impractical.

## R8: LOOT Masterlist Lifecycle

**Decision**: Three-tier availability — bundled → cached → fetched.

1. **Build time**: `bin/build.sh` downloads the masterlist from `raw.githubusercontent.com/loot/starfield/v0.21/masterlist.yaml` and bundles it with the EXE via PyInstaller `--add-data`.
2. **Startup**: Background thread fetches from GitHub if the last check was >24 hours ago. Cached to `%APPDATA%/StarfieldToolkit/loot_masterlist.yaml`. Failure is silent — uses existing cache or bundled copy.
3. **Auto Sort**: Checks cached copy first, then bundled. If neither exists, sorts category-only and shows a warning dialog.

**Rationale**: The bundled copy ensures LOOT sorting works offline and on first run. The startup fetch keeps it current without blocking the UI. The 24-hour check interval avoids hammering GitHub.

## R9: Multi-File Creation Grouping

**Decision**: Creations with multiple plugin files (e.g., Trackers Alliance with 6 ESMs) are grouped into a single row using ContentCatalog data. The group's key is the first plugin filename. All files move as a pack during drag, sort, and snapshot operations. On write, files are expanded back into individual Plugins.txt lines.

**Rationale**: The in-game Creations menu shows one entry per creation, not per file. Exposing individual files leads to broken states (e.g., sorting one ESM of Trackers Alliance away from its siblings).

## R10: Author-Based Tier 1 Assignment

**Decision**: The category sorter checks both `content_id.startswith("SFBGS")` and `author == "BethesdaGameStudios"` for tier 1 assignment. This catches official Bethesda creations published under `TM_` UUIDs (e.g., Trackers Alliance, At Hell's Gate).

**Rationale**: Not all Bethesda creations use the `SFBGS` prefix. The author field from the Bethesda API is authoritative.
