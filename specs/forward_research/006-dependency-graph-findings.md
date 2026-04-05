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

## Recommended Approach for 006

### For installed creations (runtime, in the app):

1. **Source 4** (local ESM header parsing) — zero-cost, authoritative master dependencies for all installed plugins. Parse TES4 `MAST` subrecords from `.esm` files in `Data/`. Map filenames to `content_id` via `ContentCatalog.txt`. This alone builds a complete dependency graph for the user's installed mods.

### For global catalogue analysis (offline, developer tool):

1. **Source 1** (`required_mods`) — free, already in catalogue, covers 20% of all creations
2. **Source 2** (`summaryPC.json`) — build the plugin filename ↔ UUID mapping for all creations, get TES master dependencies globally. Most complete but requires ~10K API calls
3. **Source 3** (description parsing) — use the filename mapping from Source 2 to resolve `.esm` references in descriptions, plus fuzzy title matching for informal references

### Recommended priority:

Source 4 first — it's the highest-value, lowest-cost option and directly serves the app's load order tool. Sources 1-3 extend coverage to non-installed creations for proactive recommendations (e.g., "this patch exists for two mods you have installed").

## API Endpoint Reference

| Endpoint | Has `download`? | Has `required_mods`? | Cost |
|----------|----------------|---------------------|------|
| `GET /ugcmods/v2/content?product=GENESIS&page=N&size=20` (listing) | No | Yes | 1 call per 20 creations |
| `GET /ugcmods/v2/content/{uuid}` (individual) | Yes | Yes | 1 call per creation |
| `GET {summary.download_url}` (summaryPC.json) | N/A | Has `Dependencies` | 1 call per creation |
