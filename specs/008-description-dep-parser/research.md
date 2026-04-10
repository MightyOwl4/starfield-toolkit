# Research: Description Dependency Parser

**Date**: 2026-04-05 | **Branch**: `008-description-dep-parser`

## Decision 1: Extraction Approach — LLM vs Regex

**Decision**: Use the Anthropic API (Sonnet model) for extraction and entity resolution. No regex.

**Rationale**: The hard problem is not pattern detection but entity matching. Descriptions reference creations by abbreviations ("PDY"), partial names ("Watchtower"), author self-references ("my base mod"), and `.esm` filenames that don't match titles. An LLM can reason about all these in one pass given a reference list of known creations. Regex would require increasingly complex heuristics and still miss informal references.

**Cost**: ~$3-5 per full run on ~618 patch creations with Sonnet. Acceptable for an occasional offline tool.

**Alternatives considered**:
- Regex-only: Cheap but cannot resolve informal name references — the core problem
- Opus: More capable but ~5x cost with no measurable advantage for structured extraction
- Haiku: Cheapest but may miss nuanced references; Sonnet is the sweet spot

## Decision 2: Candidate Filtering Strategy

**Decision**: Filter creations before sending to the API. Candidates are creations with "patch", "compatibility", "addon", "fix" in the title, OR creations with non-empty `required_mods` field. This reduces API calls from ~4,954 to ~800-1,000.

**Rationale**: Most creations are standalone mods with no ordering dependencies. Patch/addon creations are where ordering matters. The `required_mods` field also signals dependency relationships worth analyzing.

**Alternatives considered**:
- Process all 4,954: Higher cost (~$13 Sonnet) with diminishing returns — most non-patch descriptions won't contain ordering hints
- Only "patch" in title: Too narrow — misses "addon", "compatibility", "fix" creations

## Decision 3: Creation Reference List Format

**Decision**: Build a compact reference list with format `Title (filename.esm)` for each creation. Pass the full list (~4,954 entries) in each API request. Estimated ~50K tokens for the list.

**Rationale**: The LLM needs the full list to match both title references and filename references. 50K tokens fits comfortably in Sonnet's 200K context. Passing per-request avoids state management complexity.

**Format example**:
```
Place Doors Yourself (placedoorsyourself.esm)
Luxurious Ship Habs (dwn_luxhabs.esm)
Command NPCs - Order your followers and allies (CommandNPCs.esm)
```

**Alternatives considered**:
- Per-request filtered list (same author/category): Reduces tokens but risks missing cross-author references
- Filename-only list: Misses title-based references
- Two-pass (detect then resolve): More complex, higher latency, more API calls

## Decision 4: LLM Prompt and Response Schema

**Decision**: Use a system prompt defining the task and expected JSON output schema. Each request sends one creation's description + the full reference list. The response is structured JSON with a list of detected dependencies.

**Response schema**:
```json
{
  "dependencies": [
    {
      "source_plugin": "dwn_luxhabs_pdypatch.esm",
      "load_after": "placedoorsyourself.esm",
      "matched_creation": "Place Doors Yourself",
      "confidence": "high",
      "source_text": "PlaceDoorsYourself.esm\nDWN_LuxHabs.esm\nDWN_LuxHabs_PDYPatch.esm",
      "reasoning": "Explicit load order list in description"
    }
  ]
}
```

**Alternatives considered**:
- Free-text response parsed with regex: Fragile, defeats the purpose of using an LLM
- Tool use / function calling: Adds complexity for no benefit — JSON in the response is sufficient
- Batch multiple descriptions per request: Saves on reference list tokens but complicates parsing; single description per request is simpler

## Decision 5: Output Files

**Decision**: Generate two files:
1. `patch_order_rules.json` — standard rule book format (007-compatible)
2. `patch_order_report.md` — human-readable markdown report

Both written to the data directory alongside the catalogue.

**Rationale**: The rule book is the machine-consumable output; the report is for human review. Markdown for the report because it renders well in any viewer and supports tables.

## Decision 6: Entrypoint Pattern

**Decision**: Standalone script at `src/parse_descriptions.py` following the same pattern as `src/scrape_catalogue.py`. Uses argparse with `--dry-run`, `--max-entries`, `--model` flags.

**Rationale**: Consistent with existing developer tools. Not included in the app distribution.

## Decision 7: API Key Configuration

**Decision**: Read the Anthropic API key from the `ANTHROPIC_API_KEY` environment variable (standard for the Anthropic SDK).

**Rationale**: This is the standard pattern used by the Anthropic Python SDK. No custom configuration needed.

**Alternatives considered**:
- Config file: Extra complexity for a developer tool
- Interactive prompt: Not scriptable
