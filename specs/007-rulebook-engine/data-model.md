# Data Model: Load Order Rule Books

**Date**: 2026-04-05 | **Branch**: `007-rulebook-engine`

## Entities

### RuleBook (file on disk)

A JSON file containing ordering rules between creations.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Display name for the rule book |
| description | string | Brief explanation of what the book fixes/addresses |
| version | string | Optional version string for tracking changes |
| rules | list[Rule] | Ordered list of ordering constraints |

**File locations**:
- User books: `%APPDATA%/StarfieldToolkit/rules/*.json`
- Curated books: bundled `data/rules/*.json` (e.g., `001_base_fixes.json`)

### Rule

A single ordering constraint within a rule book.

| Field | Type | Description |
|-------|------|-------------|
| plugin | string | Plugin filename of the creation being constrained |
| load_after | list[string] (optional) | Plugin filenames that must load before this one |
| load_before | list[string] (optional) | Plugin filenames that must load after this one |
| note | string (optional) | Human-readable explanation for why this order matters |

**Normalization**: At load time, `load_before` entries are converted to equivalent `load_after` constraints. If plugin A has `load_before: ["B"]`, the system produces a `load_after: ["A"]` constraint on plugin B. This means the sorting pipeline only ever sees `load_after` constraints.

**Note**: Both `load_after` and `load_before` may reference plugins that are NOT entries in the rule book. This allows rules like "put this patch between ModA and ModB" where only the patch is a book entry. Missing (uninstalled) referenced plugins are skipped as per FR-004.

### RuleBookRegistryEntry (in config)

Persistent state for a known rule book, stored in `config.json`.

| Field | Type | Description |
|-------|------|-------------|
| filename | string | Rule book filename (e.g., `my_rules.json`) |
| source | string | `"user"` or `"curated"` |
| enabled | boolean | Whether this book participates in sorting |

**Stored as**: Ordered list in `AppSettings.rulebook_registry` — list position = priority (index 0 = highest priority user book).

### RuleBookState (runtime)

In-memory representation combining file content with registry state and applicability.

| Field | Type | Description |
|-------|------|-------------|
| filename | string | File identifier |
| name | string | From JSON `name` field |
| description | string | From JSON `description` field |
| source | string | `"user"` or `"curated"` |
| enabled | boolean | From registry |
| rules | list[Rule] | From JSON |
| rule_count | integer | Total rules in the book |
| applicable_count | integer | Rules where all referenced plugins are installed |
| missing_plugins | set[string] | Plugin filenames referenced but not installed |
| is_applicable | boolean | `applicable_count >= 1` (at least one valid rule) |
| is_corrupted | boolean | File present but JSON unparseable |
| sorter_priority | integer | Computed: 30 for curated, 40+ for user (by list position) |

**State transitions**:
- `active`: enabled=true, is_applicable=true, not corrupted → participates in sorting
- `disabled`: enabled=false → visible in manager, skipped by sorter
- `inapplicable`: is_applicable=false → visible with red error, skipped by sorter
- `corrupted`: is_corrupted=true → error dialog on startup, auto-deactivated

## Relationships

- **RuleBookRegistryEntry** 1:1 **RuleBook** file (matched by filename)
- **RuleBookState** merges data from both the file and the registry entry
- **Rule** references creations by plugin filename (matched against installed plugins)
- **RuleBookState.sorter_priority** determines constraint priority in the merger

## File Format Examples

### Using load_after only
```json
{
  "name": "Luxurious Habs Patch Order",
  "description": "Ensures correct load order for LuxHabs + PDY patch",
  "version": "1.0",
  "rules": [
    {
      "plugin": "dwn_luxhabs.esm",
      "load_after": ["placedoorsyourself.esm"],
      "note": "LuxHabs must load after PDY per author instructions"
    },
    {
      "plugin": "dwn_luxhabs_pdypatch.esm",
      "load_after": ["placedoorsyourself.esm", "dwn_luxhabs.esm"],
      "note": "Patch must load after both parents"
    }
  ]
}
```

### Using load_before to position a patch between two mods
```json
{
  "name": "Insert Patch Between Mods",
  "description": "Position a compatibility patch between its two parent mods",
  "version": "1.0",
  "rules": [
    {
      "plugin": "compat_patch.esm",
      "load_after": ["base_mod.esm"],
      "load_before": ["overhaul_mod.esm"],
      "note": "Patch must sit between base and overhaul"
    }
  ]
}
```

The `load_before` example is normalized at load time to:
- `compat_patch.esm` load_after `base_mod.esm` (explicit)
- `overhaul_mod.esm` load_after `compat_patch.esm` (from load_before conversion)
