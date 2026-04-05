# Data Model: Description Dependency Parser

**Date**: 2026-04-05 | **Branch**: `008-description-dep-parser`

## Entities

### CreationReference

A single entry in the reference list passed to the LLM.

| Field | Type | Description |
|-------|------|-------------|
| content_id | string | Creation UUID |
| title | string | Creation display name |
| plugin_files | list[string] | `.esm`/`.esp`/`.esl` filenames from `plugin_summary.Files` |
| formatted | string | `Title (filename.esm)` for the LLM prompt |

### ExtractionResult

The structured output from a single LLM API call for one creation.

| Field | Type | Description |
|-------|------|-------------|
| source_content_id | string | The creation whose description was analyzed |
| source_title | string | Title of the analyzed creation |
| dependencies | list[Dependency] | Detected ordering relationships |

### Dependency

A single detected ordering relationship.

| Field | Type | Description |
|-------|------|-------------|
| source_plugin | string | Plugin filename of the creation being ordered |
| load_after | string | Plugin filename that must load before it |
| matched_creation | string | Title of the matched creation from the reference list |
| confidence | string | "high", "medium", or "low" |
| source_text | string | The excerpt from the description that triggered detection |
| reasoning | string | LLM's explanation of why this match was made |

### Generated Files

**Rule book** (`patch_order_rules.json`):
```json
{
  "name": "Auto-detected Patch Order Rules",
  "description": "Generated from creation descriptions by the dependency parser",
  "version": "1.0",
  "rules": [
    {
      "plugin": "dwn_luxhabs.esm",
      "load_after": ["placedoorsyourself.esm"],
      "note": "[HIGH] Explicit load order in description: 'PlaceDoorsYourself.esm / DWN_LuxHabs.esm'"
    }
  ]
}
```

**Report** (`patch_order_report.md`):
```markdown
# Description Dependency Analysis Report
Generated: 2026-04-05 | Creations analyzed: 618 | Rules generated: 245

## High Confidence (142 rules)
### Luxurious Ship Habs - Patch - Place Doors Yourself
- **load_after**: Place Doors Yourself → Luxurious Ship Habs → Patch
- **Source**: "PlaceDoorsYourself.esm / DWN_LuxHabs.esm / DWN_LuxHabs_PDYPatch.esm"
- **Confidence**: HIGH — explicit .esm filename load order list
...
```
