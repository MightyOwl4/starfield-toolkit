# Quickstart: Description Dependency Parser

**Branch**: `008-description-dep-parser`

## What This Feature Does

An offline tool that reads creation descriptions from the catalogue, sends them to the Anthropic API (Sonnet) for dependency extraction and entity matching, and generates a rule book JSON file compatible with the rule book engine (007).

## Prerequisites

1. Catalogue built: `uv run src/scrape_catalogue.py` (feature 005) — must have completed both phases
2. Anthropic API key: `export ANTHROPIC_API_KEY=sk-ant-...`
3. Rule book engine in place (feature 007) — to use the generated rule book

## How to Run

```bash
# Dry run — show candidate count without API calls
uv run src/parse_descriptions.py --dry-run

# Process first 10 candidates (for testing / cost control)
uv run src/parse_descriptions.py --max-entries 10

# Full run — process all candidates
uv run src/parse_descriptions.py

# Use a specific model (default: claude-sonnet-4-6)
uv run src/parse_descriptions.py --model claude-opus-4-6
```

## Output

Two files in `%APPDATA%/StarfieldToolkit/`:

1. **`patch_order_rules.json`** — rule book file, copy to `rules/` directory for auto-sort
2. **`patch_order_report.md`** — human-readable report for review

## Key Files

| File | Purpose |
|------|---------|
| `src/parse_descriptions.py` | Standalone CLI entrypoint |
| `src/description_parser/analyzer.py` | Core analysis logic: candidate filtering, reference list building, LLM extraction |
| `src/description_parser/prompts.py` | System prompt and response schema definition |
| `src/description_parser/report.py` | Report generation (markdown) |
| `tests/test_description_parser.py` | Tests for candidate filtering, reference list, rule generation |

## Cost Estimate

| Scope | Sonnet Cost |
|-------|-------------|
| Dry run | $0 |
| 10 candidates | ~$0.05 |
| All ~618 patches | ~$3-5 |
| All ~4,954 creations | ~$13 |
