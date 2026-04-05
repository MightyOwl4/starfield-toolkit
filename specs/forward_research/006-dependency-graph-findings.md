# Forward Research: Dependency Graph Data Sources (Feature 006)

**Date**: 2026-04-05 | **From**: 005-creations-catalogue browser investigation

## Summary

During implementation of the creations catalogue scraper, we discovered three distinct data sources for building a dependency graph. Each has different availability, reliability, and scraping cost.

## Source 1: `required_mods` field (API listing)

**Already in catalogue.** Available from the paginated listing endpoint at no extra cost.

- **Coverage**: 990 of 4,954 creations (20.0%) declare dependencies
- **Format**: Array of content_id UUIDs pointing to other creations
- **Reliability**: High — structured, author-declared, machine-readable
- **Cost**: Zero — already collected in the catalogue

**Example**:
```json
"required_mods": ["e9a3a69e-f8b7-412c-a553-121006d10278"]
```

## Source 2: `summaryPC.json` from download slots (individual detail endpoint)

**NOT in catalogue.** Requires per-creation API calls + summary file fetch.

The individual detail endpoint (`/ugcmods/v2/content/{uuid}`) returns a `download` field (absent from the listing endpoint). Within it, each platform's published version has a `client.summary` slot containing a `summaryPC.json` URL. This JSON contains:

```json
{
  "Dependencies": ["CommandNPCs.esm"],
  "Files": ["Data\\CommandNPCs.esm", "Data\\CommandNPCs - Main.ba2"],
  "FormCount": 8,
  "IsESL": false,
  "IsESLCompatible": true
}
```

### Key fields:
- **`Dependencies`**: Array of `.esm` master file dependencies — this is the TES plugin master record list, the most authoritative dependency source
- **`Files`**: Array of files installed by the creation (`.esm`, `.ba2`, etc.) — enables mapping creation UUID to plugin filename
- **`IsESL`** / **`IsESLCompatible`**: Light plugin metadata

### Scraping cost:
- ~4,954 individual detail API calls (one per creation) to get download URLs
- ~4,954 summary JSON fetches (one per creation) to get the actual data
- Total: ~9,908 requests at ~1 req/3s = ~8.3 hours at default rate limit
- Multi-pass friendly — same resume pattern as catalogue scraper

### Value for 006:
- **Plugin filename ↔ creation UUID mapping**: Enables matching `.esm` names mentioned in descriptions to actual creations
- **TES master dependencies**: The definitive dependency graph at the plugin level
- **ESL status**: Useful for load order slot planning

## Source 3: Description text parsing (already in catalogue)

**Already in catalogue.** Requires NLP/fuzzy matching.

618 creations have "patch" in their title. These commonly list load orders and dependency chains in their description text, using various formats:

### Format patterns observed:

**1. Plugin filename lists** (most structured):
```
*starfield_crowd_overhaul_z.esm
*milkywayvixens.esm
*MWV_OutfitTweaksforTattoos.esm
```

**2. Named load order** (structured):
```
Encounters! (GRiNDTerraverseProcGenEncounters.esm)
Random Planetary Encounter System (GRiNDTerraEncounters.esm)
THIS FILE the MERGE patch (GRiNDTerraEncountersMerge.esm)
```

**3. Informal mod names** (needs fuzzy matching):
```
"Place Doors Yourself patch for Vault Habs"
"Useful Brigs patch for Perditus Fleet"
```

### Challenge:
Mod names in descriptions do NOT necessarily match exact creation titles. Example: `milkywayvixens.esm` is the plugin filename for the creation titled "MWV Tattoos and Freckles". The `summaryPC.json` Files field (Source 2) would be needed to bridge this gap.

## Source 4: Local ESM header parsing (runtime, installed creations only)

**No network required.** Reads TES4 header from `.esm` files in the game's `Data/` directory.

Every `.esm`/`.esp`/`.esl` file starts with a TES4 record containing `MAST` subrecords — the master dependency list that the engine enforces at load time. This is the same data shown in tools like xEdit (see `esm_header.png` for Watchtower example).

### What the header contains:
```
kinggathcreations_spaceship.esm:
  Enabled Masters: SFBGS004.esm, SFBGS006.esm, SFBGS007.esm,
                   SFBGS008.esm, Starfield.esm, sfbgs003.esm
  Loads Archives: kinggathcreations_spaceship - main.ba2,
                  kinggathcreations_spaceship - textures.ba2
```

### TES4 binary format (simple to parse):
```
Bytes 0-3:   "TES4" (record type identifier)
Bytes 4-7:   data size (uint32 little-endian)
Bytes 8-23:  flags, form ID, version control info
Subrecords:
  HEDR (header metadata)
  MAST (master filename, null-terminated string) ← dependencies
  DATA (8 bytes, follows each MAST)
  ... other subrecords
```

Only the first ~1KB of each file needs to be read. Pure stdlib binary parsing, no external dependencies.

### What we already have locally in the app:
- **`GameInstallation.data_dir`** → `game_root/Data/` where all `.esm` files live
- **`Creation.plugin_files`** → list of `.esm`/`.esp`/`.esl` per creation (from `ContentCatalog.txt`)
- **`ContentCatalog.txt`** → maps `content_id` → file list (parsed in `parsers.py`)
- **`Plugins.txt`** → current load order with active/inactive status

### Cost and coverage:

| Metric | Value |
|--------|-------|
| Network cost | Zero |
| Speed | <1 second for all installed plugins |
| Coverage | Installed creations only (not full catalogue) |
| Reliability | Authoritative — this is what the engine enforces |

### How the engine uses master dependencies:

The `MAST` entries are **not used for automatic ordering**. The engine loads plugins in exactly the order listed in `Plugins.txt`, without reordering. What the engine does with masters:

1. **Form ID resolution**: When a plugin references a form from a master (e.g., `CommandNPCs_MuteAddon.esm` references form `FE0FF807` from `CommandNPCs.esm`), the engine resolves it by looking up the already-loaded master.
2. **If a master is missing entirely**: crash or undefined behavior.
3. **If a master is loaded AFTER its dependent** (wrong order in `Plugins.txt`): the dependent plugin tries to resolve references to a master that hasn't been loaded yet — CTD or broken behavior.

What the engine does **NOT** do:
- Does not reorder `Plugins.txt` — loads in exactly the listed order
- Does not warn about wrong ordering or missing masters
- Does not resolve conflicts between two plugins editing the same record — **last loaded wins**, silently

**This is why the MAST data is critical for the tool**: the master entries define hard dependency constraints that MUST be satisfied by correct ordering in `Plugins.txt`, but the engine does not enforce this ordering itself. The tool must. The existing `load_order_sorter` already does constraint-based topological sorting with LOOT rules and category tiers — ESM master dependencies would add the most authoritative constraint layer: hard requirements that, if violated, cause crashes.

### Value for 006:
- **Hard dependency constraints** for the load order solver — masters MUST be loaded before dependents, non-negotiable
- **Conflict detection foundation** — per mod creator intel: mods modifying the same cell can CTD if load order is wrong. The master list + record analysis could detect overlapping edits
- **Filename ↔ content_id mapping** already available via `ContentCatalog.txt`
- **Zero-cost complement** to API sources — use locally for installed mods, API for global catalogue analysis

### Mod creator intel (2026-04-05):
> Dependencies are defined in the .esm header. Some mod developers use a meta.ini or modinfo.json file. Just having mods that modify the same cell is enough to cause problems. If a mod overwrites the same cell, you'll end up with a CTD if another mod that modifies the cell expects objects and doesn't find them.

This confirms the ESM header is the ground truth for dependencies. The deeper conflict detection (same-cell edits) would require parsing beyond the TES4 header into the actual record groups — significantly more complex but possible with the `detailPC.json` form data (available from Source 2's API endpoint).

## Validation Case: Luxurious Ship Habs PDY Patch (2026-04-05)

A real-world example that demonstrates the gap between TES4 headers and full dependency resolution, validating the need for Sources 3 (description parsing) and rule books.

**The creations**:
- **Place Doors Yourself** (`PlaceDoorsYourself.esm`)
- **Luxurious Ship Habs** (`DWN_LuxHabs.esm`)
- **Luxurious Ship Habs - Patch - Place Doors Yourself** (`DWN_LuxHabs_PDYPatch.esm`)

**What TES4 headers express**:
The patch's MAST entries list both `PlaceDoorsYourself.esm` and `DWN_LuxHabs.esm` as masters. This tells the solver: "patch must load after BOTH masters." But MAST entries are an unordered set — they cannot express that PDY must come before LuxHabs.

**What the description explicitly states**:
```
### Load Order
PlaceDoorsYourself.esm
DWN_LuxHabs.esm
DWN_LuxHabs_PDYPatch.esm
```

The author specifies that PDY must load **before** LuxHabs, then the patch after both. This inter-master ordering is critical for correctness but invisible to TES4 parsing.

**What the TES4 sorter (006 Phase A) produces**:
The solver correctly places the patch after both masters, but the relative order of PDY vs LuxHabs is determined by category tiers/original position — which may be wrong. In this case: `DWN_LuxHabs.esm` → `PlaceDoorsYourself.esm` → `DWN_LuxHabs_PDYPatch.esm` (LuxHabs before PDY, opposite of what the author requires).

**What's needed to fix this**:
- **Source 3 (description parsing, feature 006)**: Could detect the explicit `.esm` filename sequence in the description and produce a `load_after` constraint: `DWN_LuxHabs.esm` after `PlaceDoorsYourself.esm`
- **Rule books (feature 007)**: A user or curated rule book could capture this constraint explicitly

**Key insight**: TES4 headers express "what I need" but not "what order my dependencies need relative to each other." That inter-dependency ordering can only come from description analysis, rule books, or user knowledge. This is why the full constraint hierarchy (TES4 → rule books → patch analysis → LOOT → category) is needed — each layer covers gaps the others can't.

## Recommended Approach for 006

### For installed creations (runtime, in the app):

1. **Source 4** (local ESM header parsing) — zero-cost, authoritative master dependencies for all installed plugins. Parse TES4 `MAST` subrecords from `.esm` files in `Data/`. Map filenames to `content_id` via `ContentCatalog.txt`. This alone builds a complete dependency graph for the user's installed mods.

### For global catalogue analysis (offline, developer tool):

1. **Source 1** (`required_mods`) — free, already in catalogue, covers 20% of all creations
2. **Source 2** (`summaryPC.json`) — build the plugin filename ↔ UUID mapping for all creations, get TES master dependencies globally. Most complete but requires ~10K API calls
3. **Source 3** (description parsing) — use the filename mapping from Source 2 to resolve `.esm` references in descriptions, plus fuzzy title matching for informal references

### Recommended priority:

Source 4 first — it's the highest-value, lowest-cost option and directly serves the app's load order tool. Sources 1-3 extend coverage to non-installed creations for proactive recommendations (e.g., "this patch exists for two mods you have installed").

## Master Plan: Constraint-Based Load Order System

### Constraint Hierarchy (single-pass solver)

The load order solver resolves all constraints in a single topological sort. When constraints conflict, higher-priority source wins.

```
Priority  Source               Authority   Notes
───────── ──────────────────── ─────────── ──────────────────────────────────────
1 (top)   TES4 masters         MUST        Engine-enforced. Crash if violated.
2         User rule books      SHOULD      User-created via rule book editor.
                                           Stackable, ordered by user (higher
                                           position = higher priority).
3         Curated rule book    SHOULD      Project-provided (if shipped).
                                           Sits below user books.
4         Patch analysis       SHOULD      Auto-detected from catalogue
                                           descriptions (feature 006 core).
5         LOOT rules           SHOULD      Community-curated, possibly stale.
6 (base)  Category tiers       PREFER      Heuristic grouping, cosmetic.
```

### Conflict Resolution

When a higher-priority constraint contradicts a lower one (e.g., TES4 says a CAT3 plugin must load after a CAT5 plugin):
- The higher-priority constraint wins — always
- The affected plugin is moved down past its dependency, not the dependency moved up
- A warning is emitted explaining the override (e.g., "ModA (Gear) placed after ModB (Quest) due to master dependency")
- Philosophy: "load as early as your tier allows, but never before your masters"

### Rule Book System

**Storage**: JSON files in `%APPDATA%/StarfieldToolkit/rules/` (or `data/rules/` relative to app).

**Discovery**: On startup, scan the rules directory for `.json` files. Newly discovered books are added at the bottom of the priority list (lowest priority among user books) until the user explicitly reorders them.

**UI Components**:
- **Rule Book Editor** (new tool/tab): Create and edit rule books. Each book contains a set of `load_after` constraints, warnings, and notes.
- **Rule Book Manager** (part of editor or separate): Enable/disable individual books, drag to reorder priority. Shows: name, description, entry count, enabled/disabled toggle.

**Rule Book Format** (conceptual):
```json
{
  "name": "My Custom Rules",
  "description": "Fixes for my personal mod list",
  "version": "1.0",
  "rules": [
    {
      "plugin": "SomeAddon.esm",
      "load_after": ["BaseMod.esm"],
      "note": "Addon patches records from BaseMod"
    },
    {
      "plugin": "PatchAB.esm",
      "load_after": ["ModA.esm", "ModB.esm"],
      "note": "Compatibility patch, must load after both"
    }
  ]
}
```

**Curated book**: If the project gains traction, a `curated-rules.json` can be shipped with the app (or fetched from the repo). It sits at priority 3, below any user-created books but above auto-detected patch analysis.

### Implementation Phases

**Phase A: TES4 Header Parser**
- Parse MAST subrecords from local `.esm` files (~30 lines stdlib)
- Integrate as highest-priority constraint source in existing solver
- Zero network cost, instant, covers all installed plugins

**Phase B: Patch Analysis (catalogue-based)**
- Parse description text from catalogue for load order patterns
- Detect `*.esm` filenames, plugin lists, informal mod name references
- Generate `load_after` constraints from detected patterns
- Use `plugin_summary.Files` from catalogue to map filenames ↔ content_ids

**Phase C: Rule Book Engine**
- Rule book file format and I/O (load/save JSON)
- Rule book discovery (scan rules directory on startup)
- Constraint merger integration (ordered priority)
- Rule book manager UI (enable/disable, reorder)

**Phase D: Rule Book Editor**
- UI for creating/editing individual rule books
- Add/remove/edit rules within a book
- Validate plugin names against installed creations

**Phase E: Curated Rule Book (if warranted)**
- Project-maintained rule book with community-contributed rules
- Shipped with app or fetched from repo
- Auto-updates mechanism (optional)

## API Endpoint Reference

| Endpoint | Has `download`? | Has `required_mods`? | Cost |
|----------|----------------|---------------------|------|
| `GET /ugcmods/v2/content?product=GENESIS&page=N&size=20` (listing) | No | Yes | 1 call per 20 creations |
| `GET /ugcmods/v2/content/{uuid}` (individual) | Yes | Yes | 1 call per creation |
| `GET {summary.download_url}` (summaryPC.json) | N/A | Has `Dependencies` | 1 call per creation |
