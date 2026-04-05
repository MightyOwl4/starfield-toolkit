# Quickstart: Load Order Rule Books

**Branch**: `007-rulebook-engine`

## What This Feature Does

Adds a rule book system to the load order sorter. Users can create, share, and manage JSON files that define explicit ordering rules between creations. The sorter respects these rules alongside TES4 master dependencies, LOOT masterlist, and category tiers.

## How to Use

### As a File-Only User (No UI Needed)

1. Create a JSON file in `%APPDATA%/StarfieldToolkit/rules/`:
```json
{
  "name": "My Rules",
  "description": "Fix order for my mods",
  "version": "1.0",
  "rules": [
    {
      "plugin": "ModB.esm",
      "load_after": ["ModA.esm"],
      "note": "B patches A"
    }
  ]
}
```
2. Restart the app (or click Rescan in the Rule Books tab)
3. Run Auto Sort — the rules are applied automatically

### Using the Management Tool

1. Open the "Rule Books" tab in the app
2. See all discovered books (curated + user)
3. Enable/disable individual books
4. Drag to reorder priority (higher = more important)
5. Click "New" to create a rule book via the editor
6. Click "Rescan" to pick up newly added files

### Creating a Rule Book via the Editor

1. Click "New Rule Book" in the management tool
2. Enter a name and description
3. Select creations from the installed list
4. Arrange them in desired load order
5. Save — the file is created in the rules directory

## Key Files

| File | Purpose |
|------|---------|
| `src/load_order_sorter/rulebook.py` | [NEW] Rule book I/O, parsing, applicability checking |
| `src/load_order_sorter/sorters/rulebook.py` | [NEW] Rule book sorter producing load_after constraints |
| `src/starfield_tool/tools/rulebook_manager.py` | [NEW] Management tool tab (ToolModule) |
| `src/starfield_tool/dialogs/rulebook_editor.py` | [NEW] Editor dialog for create/edit |
| `src/starfield_tool/config.py` | [MODIFIED] Add rulebook_registry to AppSettings |
| `src/starfield_tool/tools/__init__.py` | [MODIFIED] Register RuleBookTool in MODULES |
| `src/load_order_sorter/pipeline.py` | [MODIFIED] Register rulebook sorter |
| `bin/build.sh` | [MODIFIED] Bundle curated rule books via --add-data |
| `data/rules/` | [NEW] Curated rule book files (bundled with app) |
| `tests/test_rulebook.py` | [NEW] Rule book I/O and applicability tests |
| `tests/test_rulebook_sorter.py` | [NEW] Sorter integration tests |

## Priority Hierarchy

```
TES4 masters:    100  (crash if violated)
User rule books: 40+  (ordered by user, position 0 = highest)
Curated books:   30   (shipped defaults)
LOOT masterlist: 20   (community rules)
Category tiers:  10   (heuristic grouping)
```
