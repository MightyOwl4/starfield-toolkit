# Feature Specification: Description Dependency Parser

**Feature Branch**: `008-description-dep-parser`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "Offline analyzer that parses creation descriptions from the catalogue to detect load order patterns and dependency hints, then generates a rule book JSON file consumable by the rule book engine."

## Clarifications

### Session 2026-04-05

- Q: Should the parser use regex or LLM-based extraction? → A: LLM-based (Anthropic API, Sonnet model). Regex can detect patterns but cannot reliably match informal creation references (abbreviations like "PDY", partial names like "Watchtower", author self-references). The LLM receives the description plus a list of known creations and performs both detection and entity resolution in one pass.
- Q: Cost estimate? → A: ~$3-5 was the initial estimate but actual cost is ~$165 per full run (~1,136 candidates × ~48K reference list tokens per request). The reference list is sent with every request for entity resolution. Acceptable given this is an occasional offline tool and credits are prepaid.
- Q: Which candidate filter keywords? → A: title contains "patch", "compatibility", "addon", "fix" (case-insensitive) OR `required_mods` is non-empty. Filters ~4,954 creations down to ~1,136 candidates.
- Q: How to handle API rate limits? → A: Tier 3 (120K input tokens/min) required for practical throughput. 30-second sleep between API calls keeps usage under the limit. Lower tiers require longer delays (Tier 1: 120s, Tier 2: 60s).
- Q: How to handle multi-pass runs and resume after crashes? → A: Save ALL analyzed creations to a results cache file (`patch_order_results.json`), including those with empty dependency lists. On next run, the cached content_ids form a skip set so previously-analyzed creations are not re-processed — regardless of whether they had dependencies or not.
- Q: How to handle truncated LLM responses when max_tokens is exceeded? → A: Use `max_tokens=4096` as baseline (sufficient for ~20 dependencies per response). When JSON is still truncated, attempt recovery by parsing complete dependency objects from the partial array — string-aware brace matching extracts whatever complete objects exist before the cut.
- Q: How to prevent LLM from returning prose instead of JSON for ambiguous cases? → A: Tightened prompt rules: "if uncertain return empty array", "never write prose outside JSON", "skip unmatched references without explanation", "truncate source_text to 80 chars, reasoning to 120 chars", "prioritize confident matches if more than 8 deps".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Rule Book from Catalogue Descriptions (Priority: P1)

A developer runs the description parser as a standalone script. The parser reads the creations catalogue (built by the 005 scraper), identifies creations likely to contain dependency hints (primarily patches), and sends their descriptions to the Anthropic API (Sonnet model) for analysis. Each request includes the description text and a list of all known creation titles, enabling the model to both detect ordering patterns and match referenced creations by name — including abbreviations, partial names, and informal references.

The model extracts:
1. **Explicit load order sequences** (`.esm` filename lists, numbered steps)
2. **Dependency declarations** ("requires X", "load after X", "place below X")
3. **Implied relationships** (author self-references like "my base mod", contextual hints)

Each extraction includes the matched creation from the provided list and a confidence level. The parser collects all extractions and generates a rule book JSON file in the format defined by feature 007.

**Why this priority**: This is the core feature — generating the rule book is the entire purpose.

**Independent Test**: Can be tested by running the parser against the catalogue and verifying the generated rule book contains correct load_after rules for known patch creations (e.g., the Luxurious Ship Habs PDY patch should produce rules placing PDY before LuxHabs before the patch).

**Acceptance Scenarios**:

1. **Given** the catalogue exists with description data, **When** the parser runs, **Then** it produces a valid rule book JSON file with load_after rules derived from LLM analysis.
2. **Given** a creation description contains an explicit `.esm` filename load order list, **When** the LLM processes it with the creation list, **Then** it generates load_after rules matching the listed order with high confidence.
3. **Given** a creation description mentions a creation by abbreviation or partial name (e.g., "PDY" for "Place Doors Yourself"), **When** the LLM processes it, **Then** it resolves the reference to the correct creation from the provided list.
4. **Given** a creation description references a mod not in the catalogue, **When** the LLM processes it, **Then** it reports the reference as unresolved and no rule is generated for it.
5. **Given** the parser generates rules, **When** the rule book is loaded by the rule book engine (007), **Then** it is recognized and applied during auto-sort.
6. **Given** the parser is processing creations, **When** the API returns an error for a specific request, **Then** that creation is skipped and the parser continues with remaining creations.

---

### User Story 2 - Confidence Scoring and Reporting (Priority: P2)

Each detected rule is assigned a confidence level (high, medium, low) by the LLM based on how explicit the ordering hint is. The parser produces a human-readable report alongside the rule book showing what was detected, the source text that triggered it, the confidence level, and which creation it was matched to. This allows users to review the auto-generated rules before trusting them — particularly for low-confidence matches.

**Why this priority**: Without a review mechanism, users must blindly trust auto-generated rules. The report enables informed decisions about which rules to keep.

**Independent Test**: Can be tested by running the parser and checking that the report contains confidence labels, source quotes, and match explanations for each generated rule.

**Acceptance Scenarios**:

1. **Given** a rule was derived from an explicit `.esm` filename list, **When** the report is generated, **Then** the rule is marked as high confidence.
2. **Given** a rule was derived from an informal mention with fuzzy matching, **When** the report is generated, **Then** the rule is marked as low or medium confidence with the matching rationale.
3. **Given** the parser completes, **When** the report is viewed, **Then** each rule shows: the source creation, the matched text excerpt, the confidence level, the resolved creation name, and the generated load_after constraint.
4. **Given** the report file exists, **When** a user reviews it, **Then** they can identify and remove questionable rules before using the rule book.

---

### Edge Cases

- What happens when a creation description is empty? The creation is skipped — no API call made.
- What happens when the catalogue has no plugin_summary data for a creation? The creation is still processed — the LLM matches by title. Filename resolution is best-effort.
- What happens when two creations have very similar names and the LLM is ambiguous? The LLM should indicate ambiguity in its response, and the rule is marked low confidence.
- What happens when the LLM finds contradictory ordering hints in different descriptions? Both rules are generated — the rule book engine and solver handle conflict resolution.
- What happens when the catalogue is missing? The parser exits with an error instructing the user to run the catalogue scraper first.
- What happens when the API key is missing or invalid? The parser exits with a clear error message about API configuration.
- What happens when the API rate-limits the parser? The parser implements retry with back-off, similar to the catalogue scraper. At Tier 3, 30-second pacing between calls prevents rate limits entirely.
- What happens when a description references many plugins (20+) and the LLM response exceeds max_tokens? Truncated JSON is recovered by parsing complete dependency objects from the partial array; whatever complete objects exist before the cut-off are kept.
- What happens when the LLM returns prose or explanatory text instead of JSON (e.g., "I couldn't find exact matches for...")? The prompt explicitly forbids this — responses should be empty arrays on uncertainty. Any non-JSON responses are saved to a failed-responses file for later inspection.
- What happens when an analyzed creation has no detectable dependencies? Its result is still cached (with empty `dependencies: []`) so it won't be re-processed on subsequent runs — preventing wasted API calls.
- What happens on crash mid-run? Results are saved after every API call, so at most one response is lost. Resume skips all previously-analyzed creations.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Parser MUST read the creations catalogue file (from feature 005) and identify creations likely to contain dependency hints (filtering by title keywords like "patch", "compatibility", "addon", or by presence of `required_mods`).
- **FR-002**: Parser MUST build a creation reference list containing all creation titles AND their plugin filenames (from `plugin_summary.Files`), formatted as `Title (filename.esm)` pairs, to be included in each LLM request for entity resolution. This enables matching both by title ("PDY", "Watchtower") and by filename ("placedoorsyourself.esm", "dwn_luxhabs.esm") in a single pass.
- **FR-003**: Parser MUST send each candidate creation's description to the Anthropic API (Sonnet model) along with the creation reference list, requesting structured extraction of load order dependencies.
- **FR-004**: Parser MUST use a structured output format (JSON) from the LLM, specifying the expected schema in the prompt to ensure consistent, parseable responses.
- **FR-005**: Parser MUST collect all LLM-extracted rules and generate a rule book JSON file in the format defined by feature 007, with `load_after` and optionally `load_before` rules.
- **FR-006**: Each generated rule MUST include a confidence level (high, medium, low) and a note quoting the source text that triggered it.
- **FR-007**: Parser MUST be a standalone entrypoint, separate from the GUI application.
- **FR-008**: Parser MUST handle API errors gracefully — retry on transient failures with exponential back-off, skip on persistent errors, continue processing remaining creations.
- **FR-009**: Parser MUST produce a human-readable report file alongside the rule book, summarizing detections, confidence levels, and match rationale.
- **FR-010**: Parser MUST display an in-place progress counter during processing, showing current position relative to the number of creations remaining (not the full catalogue count when resuming).
- **FR-011**: Parser MUST support a `--dry-run` flag that identifies candidate creations and reports the count without making API calls.
- **FR-012**: Parser MUST accept an optional `--max-entries` flag to cap the number of creations processed (for cost control during testing).
- **FR-013**: Parser MUST support multi-pass operation: save ALL analyzed creations to a results cache file (`patch_order_results.json`), including those with empty dependency lists. On subsequent runs, cached content_ids form a skip set to avoid re-processing.
- **FR-014**: Parser MUST save progress after every successful LLM response (rule book, report, and results cache all updated), so an interrupted run loses at most one API call's worth of work.
- **FR-015**: Parser MUST save failed (unparseable) LLM responses to a separate file (`patch_order_failed.json`) for later inspection or recovery, containing the creation title, plugin, and raw response text.
- **FR-016**: Parser MUST attempt to recover complete dependency objects from truncated LLM responses (when the model exceeds max_tokens mid-response). Partial array parsing should extract whatever valid objects exist before the cut-off.
- **FR-017**: Parser MUST use a sufficiently large `max_tokens` value (4096) to accommodate patches with many listed dependencies (up to ~20 per response).
- **FR-018**: Parser MUST implement rate-limit-aware pacing between API calls (configurable per tier, default 30 seconds for Tier 3).

### Key Entities

- **Creation Reference List**: All creation titles paired with their `.esm`/`.esp`/`.esl` filenames (from `plugin_summary.Files`), formatted as `Title (filename.esm)`. Passed to the LLM for dual-mode entity resolution — matching by informal title references AND by explicit `.esm` filename references in descriptions.
- **LLM Extraction**: The structured response from a single API call. Contains: list of detected dependencies, each with source text, matched creation, confidence level, and load_after/load_before target.
- **Generated Rule Book**: The output JSON file, compatible with the rule book engine format, containing all extracted load_after rules with notes and confidence annotations.
- **Report**: A human-readable summary file listing each detection with source context, match rationale, and confidence — designed for user review before trusting the rule book.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The parser correctly identifies load order dependencies in at least 50% of the ~618 "patch" creations that contain ordering hints in their descriptions.
- **SC-002**: High-confidence rules have a false positive rate below 5% when manually reviewed against a sample of 20 creations.
- **SC-003**: The generated rule book is loadable by the rule book engine and produces correct sorting results for known test cases (e.g., Luxurious Ship Habs PDY patch).
- **SC-004**: Total API cost for processing all ~1,136 candidate creations stays under $170 per full run at Sonnet pricing. Subsequent runs skip already-analyzed creations and cost significantly less.
- **SC-006**: Malformed JSON response rate is under 5% of API calls. Recoverable truncation reduces effective failure rate further via partial parsing.
- **SC-007**: After the initial full run, incremental re-runs (after catalogue updates) only process newly added creations, not the full catalogue.
- **SC-005**: The report provides enough context for a user to validate each rule without opening the original description.

## Assumptions

- The creations catalogue (feature 005) has been built with descriptions and plugin summaries.
- The rule book engine (feature 007) is in place and can load the generated rule book file.
- An Anthropic API key is available and configured (environment variable or config file).
- Sonnet provides sufficient accuracy for structured extraction and entity matching (Opus is available as fallback but not expected to be necessary).
- The parser is a developer tool run occasionally — API cost per run is acceptable.
- The generated rule book is a starting point — users may review and edit via the rule book editor.
