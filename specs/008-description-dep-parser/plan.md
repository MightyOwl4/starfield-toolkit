# Implementation Plan: Description Dependency Parser

**Branch**: `008-description-dep-parser` | **Date**: 2026-04-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/008-description-dep-parser/spec.md`

## Summary

Standalone offline tool that reads the creations catalogue (005), filters for candidate creations likely to contain dependency hints (~618 patches + addons), sends each description to the Anthropic API (Sonnet) alongside a full creation reference list (titles + .esm filenames), and collects structured dependency extractions. Generates a 007-compatible rule book JSON file and a human-readable markdown report with confidence levels. Uses the Anthropic Python SDK for API calls with retry logic.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: anthropic (Anthropic Python SDK — new dependency)
**Storage**: Reads catalogue from `%APPDATA%/StarfieldToolkit/creations_catalogue.json`, writes rule book + report to same directory
**Testing**: pytest (with mocked API responses)
**Target Platform**: Windows (developer workstation)
**Project Type**: CLI script (standalone entrypoint)
**Performance Goals**: Process ~618 candidates in under 30 minutes (API latency-bound, not CPU)
**Constraints**: API cost under $10 per full run; ANTHROPIC_API_KEY required
**Scale/Scope**: ~618 candidate creations, ~4,954 entry reference list (~50K tokens)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity First (KISS)
- **PASS**: Three modules (analyzer, prompts, report) + one entrypoint. No class hierarchies. The LLM does the complex work; our code just orchestrates API calls and formats output.

### II. Test Coverage (NON-NEGOTIABLE)
- **PASS**: Tests for candidate filtering, reference list building, response parsing, rule book generation, and report formatting. API calls mocked at the SDK boundary.

### III. Minimal Dependencies
- **VIOLATION (justified)**: Adds `anthropic` SDK as a new dependency. This is a dev-only dependency not needed by the distributed app. The SDK is the standard way to call the Anthropic API — rolling our own HTTP client would be more code and less reliable.

### IV. Clear Interfaces
- **PASS**: CLI with explicit argparse options. LLM response schema documented in contracts/llm-schema.md. Output files are standard JSON (rule book) and markdown (report).

## Project Structure

### Documentation (this feature)

```text
specs/008-description-dep-parser/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/           # LLM response schema
├── quickstart.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
├── parse_descriptions.py            # Standalone CLI entrypoint (argparse)
└── description_parser/
    ├── __init__.py
    ├── analyzer.py                  # Core: candidate filtering, ref list, LLM orchestration
    ├── prompts.py                   # System prompt text and response schema
    └── report.py                    # Markdown report generation

tests/
└── test_description_parser.py       # Tests for filtering, parsing, rule generation
```

**Structure Decision**: New `description_parser` package in `src/` (not inside `bethesda_creations` or `load_order_sorter` — this is a standalone analysis tool, not a library component). Entrypoint at `src/parse_descriptions.py` following the `scrape_catalogue.py` pattern.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `anthropic` SDK dependency | Required for API access to Sonnet; standard SDK | Raw httpx calls would require more code for auth, streaming, retries, response parsing |

**Note**: This dependency is dev-only. The `parse_descriptions.py` script is not included in the PyInstaller distribution. The output (rule book JSON) is consumed by the app, not the SDK itself.
