# Quickstart: Fast Lane Creation Check

**Branch**: `009-fast-lane-check`

## What This Feature Does

Adds a "Fast Lane Creation Check" tab to the app. Compares your installed creations against a bundled baseline snapshot (taken before the Starfield Fast Lanes update) and highlights creations that have not received a version bump since — those are the ones most likely to be broken by the update.

## Prerequisites

- **Existing creations cache populated** — run "Check for Updates" in the Installed Creations tab at least once per session, so the tool has current version data to compare against.
- **Baseline file present** — ships with the app automatically (bundled via PyInstaller). In dev mode, the file lives at `data/creations_baseline.json`.

## How to Use

### Check your installed creations (default mode)

1. Open the app
2. Go to "Installed Creations" tab and click "Check for Updates" once (populates the cache)
3. Switch to the "Fast Lane Creation Check" tab
4. Review the list — rows highlighted in warning color have not been updated since the baseline
5. Read the warning banner at the top — this check is approximate

### Check an exported list

1. In "Installed Creations" tab, click "Export" and save the CSV file
2. Switch to "Fast Lane Creation Check" tab
3. Click "Load from File" and select the exported file
4. Review the list — same comparison logic applies

## Regenerating the Baseline (developer task)

```bash
# From the repo root, after running scrape_catalogue.py at least once
uv run python src/starfield_tool/tools/fast_lane_baseline_generator.py

# Output goes to data/creations_baseline.json
# Commit the file before building the distribution
```

## Key Files

| File | Purpose |
|------|---------|
| `src/starfield_tool/tools/fast_lane_check.py` | [NEW] Tool tab — UI, comparison logic, result display |
| `src/starfield_tool/tools/fast_lane_baseline_generator.py` | [NEW] Developer script to generate the trimmed baseline |
| `src/starfield_tool/tools/__init__.py` | [MODIFIED] Register FastLaneCheckTool in MODULES |
| `src/starfield_tool/tools/creation_load_order.py` | [MODIFIED] Export gains `Content ID` column; `Version` → `Installed Version` |
| `data/creations_baseline.json` | [NEW] Bundled baseline file (ships with distribution) |
| `bin/build.sh` | [MODIFIED] Add `--add-data data/creations_baseline.json;data` |
| `tests/test_fast_lane_check.py` | [NEW] Tests for baseline loading, comparison logic, import parsing (new + legacy formats) |
| `tests/test_fast_lane_baseline_generator.py` | [NEW] Tests for baseline generation from full catalogue |

## Removing This Feature Later

When Fast Lanes is no longer relevant and this tool can be retired:

1. Delete `src/starfield_tool/tools/fast_lane_check.py`
2. Delete `src/starfield_tool/tools/fast_lane_baseline_generator.py`
3. Remove `FastLaneCheckTool` import and entry from `src/starfield_tool/tools/__init__.py`
4. Delete `data/creations_baseline.json`
5. Delete `tests/test_fast_lane_check.py` and `tests/test_fast_lane_baseline_generator.py`
6. Remove the `--add-data data/creations_baseline.json` line from `bin/build.sh`

Six files touched, all named with the `fast_lane_` prefix for easy `grep`/`find` removal.

## What Gets Highlighted

| Status | When | Highlighted |
|--------|------|-------------|
| **Updated since baseline** | current version > baseline version | No |
| **Not updated since baseline** | current version == baseline version | **Yes** |
| **Unknown** | not in baseline OR no current version cached | No |

## The Warning

A prominent banner at the top of the tab explains:
- The check is approximate
- How detection works (version comparison against baseline snapshot)
- The baseline snapshot date

The warning is **always visible** — it cannot be dismissed.
