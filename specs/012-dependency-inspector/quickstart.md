# Quickstart: Dependency Inspector

**Audience**: developer implementing the feature or manually verifying it.

## Prerequisites

- Working Starfield Tool checkout with the repo's standard dev environment (Python 3.12+, `customtkinter`, `pytest`, `ruff`).
- An installed Starfield setup with at least a handful of creations that have cross-dependencies (e.g., any patch creation that lists `required_mods`).
- A populated creations catalogue cache (produced by feature 005) and — if available — a description-parser output file (feature 008) for soft-dependency coverage.

## Run tests

```bash
pytest
ruff check .
```

Tests to expect:

- `tests/test_dependency_inspector_graph.py` — unit tests for `build_dependency_graph`, `ancestors`, `descendants`, palette-color assignment, missing-hard tracking, no-deps detection.
- `tests/test_dependency_inspector_router.py` — `assign_sides` produces fewer crossings than the all-same-side baseline on a canned fixture.

## Manual UI verification

1. Launch the app: `python -m starfield_tool`.
2. Switch to the new **Dependency Inspector** tab.
3. Confirm the centered datagrid lists your installed creations in load order; creations with no dependency info render collapsed in the regular row color.
4. Confirm creations with dependencies render colored per the palette and connectors are drawn on *both* sides of the grid.
5. Select a creation that has both incoming and outgoing edges:
   - Its full directed closure (ancestors + descendants) highlights in white with a glow.
   - Unrelated connectors dim.
   - Siblings that share a common dependency but don't depend on the selected creation stay dim (sanity check for clarification Q1).
6. Toggle **Hide soft dependencies** — soft connectors disappear, hard stay; palette colors and collapse states do **not** change (clarification Q2). Re-enable — soft connectors return.
7. Toggle **Hide creations with no dependencies** — collapsed rows vanish; connectors between remaining rows still render correctly across the gaps.
8. Click empty canvas — selection clears, all connectors return to their default (non-highlighted) look.
9. Refresh the catalogue / change load order in the Installed Creations tab — return to Dependency Inspector and confirm the graph rebuilds, selection clears, and toggle states persist.
10. If any installed creation has a *hard* required_mod that is not installed, its row must show a warning indicator (no connector drawn).

## Performance smoke check

On a load order of ~100–500 creations:

- Tab switch + initial render completes in under 2 seconds (SC-001).
- Clicking a row updates the highlight visibly within ~200 ms (SC-002).
- Toggling either checkbox updates within ~300 ms without losing scroll position (SC-004).

If any of the above exceed budget, profile — the likely culprit is re-drawing every connector on every scroll; consider batching Canvas updates per the pattern already used in `load_order_diff.py`.
