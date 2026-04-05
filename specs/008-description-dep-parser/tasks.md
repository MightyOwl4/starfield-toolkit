# Tasks: Description Dependency Parser

**Input**: Design documents from `/specs/008-description-dep-parser/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/llm-schema.md, quickstart.md

**Tests**: Included (constitution principle II).

**Organization**: Two user stories. US1 (parser + rule book) is the core. US2 (confidence + report) builds on US1's extraction results.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [ ] T001 Create `src/description_parser/` package with `__init__.py`
- [ ] T002 Add `anthropic` SDK to dev dependencies in pyproject.toml

---

## Phase 2: Foundational

- [ ] T003 [P] Implement candidate filtering in src/description_parser/analyzer.py — function `filter_candidates(catalogue: dict) -> list[dict]` that returns entries where title contains "patch"/"compatibility"/"addon"/"fix" (case-insensitive) OR `required_mods` is non-empty. Returns list of `{content_id, title, description, plugin_files}`.
- [ ] T004 [P] Implement reference list builder in src/description_parser/analyzer.py — function `build_reference_list(catalogue: dict) -> str` that builds a text block of all creations formatted as `Title (filename.esm)`, one per line. Uses `plugin_summary.Files` to extract `.esm`/`.esp`/`.esl` filenames. Creations without plugin_summary get title only.
- [ ] T005 Implement system prompt in src/description_parser/prompts.py — constant `SYSTEM_PROMPT` defining the extraction task, JSON response schema (per contracts/llm-schema.md), and confidence level guidelines. Constant `build_user_message(description, reference_list, creation_title)` that formats the user message.
- [ ] T006 [P] Write tests in tests/test_description_parser.py — test candidate filtering (patch in title, required_mods, combined, empty catalogue), test reference list building (includes filenames, handles missing plugin_summary), test response parsing (valid JSON, empty dependencies, malformed response).

**Checkpoint**: Filtering, reference list, and prompt ready. LLM orchestration can proceed.

---

## Phase 3: User Story 1 - Generate Rule Book (Priority: P1) 🎯 MVP

- [ ] T007 [US1] Implement LLM extraction orchestrator in src/description_parser/analyzer.py — function `analyze_creation(client, description, reference_list, creation_title, model) -> dict` that sends one API call and parses the JSON response. Handle malformed responses (return empty dependencies). Retry on transient API errors (up to 2 retries with back-off).
- [ ] T008 [US1] Implement batch processor in src/description_parser/analyzer.py — function `process_candidates(candidates, reference_list, model, max_entries) -> list[ExtractionResult]` that iterates candidates, calls `analyze_creation` for each, displays in-place progress counter, collects results. Respects `max_entries` limit.
- [ ] T009 [US1] Implement rule book generator in src/description_parser/analyzer.py — function `generate_rulebook(results: list) -> dict` that converts extraction results into 007-compatible rule book format. Each dependency becomes a `load_after` rule with confidence and source text in the note field. Deduplicates rules.
- [ ] T010 [US1] Implement CLI entrypoint in src/parse_descriptions.py — argparse with `--dry-run`, `--max-entries`, `--model` (default `claude-sonnet-4-6`). Loads catalogue, filters candidates, builds reference list, runs batch processor, generates and saves rule book to `%APPDATA%/StarfieldToolkit/patch_order_rules.json`. Prints summary (candidates found, API calls made, rules generated, cost estimate).
- [ ] T011 [P] [US1] Write integration tests in tests/test_description_parser.py — test analyze_creation with mocked API response, test rule book generation from sample extractions, test CLI dry-run mode, test max-entries respected.

**Checkpoint**: Parser generates a valid rule book from catalogue descriptions.

---

## Phase 4: User Story 2 - Confidence Scoring and Report (Priority: P2)

- [ ] T012 [US2] Implement report generator in src/description_parser/report.py — function `generate_report(results, output_path)` that writes a markdown file grouped by confidence level (high/medium/low). Each entry shows: creation title, detected dependencies, source text excerpt, confidence, reasoning. Includes summary stats at the top.
- [ ] T013 [US2] Wire report generation into CLI in src/parse_descriptions.py — after rule book is saved, generate report at `%APPDATA%/StarfieldToolkit/patch_order_report.md`. Print report path in summary.
- [ ] T014 [P] [US2] Write tests for report in tests/test_description_parser.py — test report contains confidence sections, test summary stats correct, test markdown formatting.

**Checkpoint**: Full pipeline: catalogue → LLM analysis → rule book + report.

---

## Phase 5: Polish

- [ ] T015 Run full project lint (`ruff check .`) and fix any issues
- [ ] T016 Run full test suite (`pytest`) and verify all pass
- [ ] T017 Run `--dry-run` against real catalogue to verify candidate count
- [ ] T018 Run `--max-entries 5` against real API to verify end-to-end

---

## Dependencies & Execution Order

```
T001, T002 (setup)
  → T003, T004, T005 (parallel, foundational)
    → T006 (tests)
      → T007 → T008 → T009 → T010 (US1 sequential)
        → T011 (tests)
          → T012 → T013 (US2)
            → T014 (tests)
              → T015-T018 (polish)
```

---

## Notes

- `anthropic` is a dev-only dependency — not in the app distribution
- API key via `ANTHROPIC_API_KEY` env var (standard Anthropic SDK pattern)
- Default model: `claude-sonnet-4-6`
- Each API call: ~50K input tokens (reference list) + ~250 tokens (description) + ~200 output tokens
- Total for 1,136 candidates: ~$5-7, ~50 minutes sequential
