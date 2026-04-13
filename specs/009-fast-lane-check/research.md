# Research: Fast Lane Creation Check

**Date**: 2026-04-10 | **Branch**: `009-fast-lane-check`

## Decision 1: Baseline Catalog Format

**Decision**: A single JSON file at `data/creations_baseline.json` with a top-level snapshot metadata object and a compact entries dict keyed by content_id. Fields per entry: `title`, `author`, `version`. Nothing else.

**Rationale**: The tool only needs three things per entry: title (for display), author (tiebreaker when titles clash), and version (the comparison target). Everything else the full catalogue tracks — description, release_notes, plugin_summary, hashes — is irrelevant here. Trimming aggressively keeps the bundle tiny (under 500 KB for 4,954 creations, easily ~200 KB with short version strings).

**Format**:
```json
{
  "version": 1,
  "snapshot_date": "2026-04-06T12:00:00Z",
  "entries": {
    "4bd2936a-139f-4177-a4c8-2ab26261bb74": {
      "title": "Dynamic Universe",
      "author": "youngneil1",
      "version": "2.2"
    }
  }
}
```

**Alternatives considered**:
- Reuse full catalogue file: Bundles ~50 MB into the exe — unacceptable
- CSV format: Slightly smaller but harder to parse and less extensible
- SQLite: Overkill; JSON loads instantly at this size
- No snapshot_date: Removes an important UX element (FR-013) — users need to know how stale the baseline is

## Decision 2: How to Generate the Baseline

**Decision**: A developer script co-located with the tool at `src/starfield_tool/tools/fast_lane_baseline_generator.py`. Reads the full catalogue (`%APPDATA%/StarfieldToolkit/creations_catalogue.json`) and writes the trimmed baseline to `data/creations_baseline.json` in the project root. Run manually before building the distribution.

**Rationale**: The baseline only updates when the developer decides to cut a new release. Automation is unnecessary and risky — an accidental regeneration post-Fast-Lanes would invalidate the baseline. A manual script keeps control in the developer's hands. The script extracts version from `release_notes` (latest version_name across all platforms) since that's where the scraper currently stores it.

**Co-location rationale**: This entire feature is intentionally short-lived (it loses relevance as more time passes since Fast Lanes). Keeping all feature 009 code inside `src/starfield_tool/tools/` with a `fast_lane_` prefix makes it trivial to remove cleanly: delete the two files, remove one line from `tools/__init__.py`, delete the bundled data file. No dev scripts to track across the repo.

**Script interface**:
```bash
uv run python src/starfield_tool/tools/fast_lane_baseline_generator.py
uv run python src/starfield_tool/tools/fast_lane_baseline_generator.py --output custom/path.json
```

**Alternatives considered**:
- Top-level `src/make_baseline.py`: Matches existing dev scripts (`scrape_catalogue.py`, `parse_descriptions.py`) but scatters feature 009 code across directories, making cleanup harder when the feature is removed
- Extend `scrape_catalogue.py` with a `--baseline` flag: Couples two concerns; baseline cut should be a deliberate separate step
- Generate at build time: Makes the build depend on the catalogue file being present, which isn't guaranteed in CI
- Download baseline at runtime: Defeats the "bundled, reproducible" model

## Decision 3: Version Extraction from Catalogue

**Decision**: For each catalogue entry, extract the latest version from `release_notes` by finding the most recent entry across all platforms. Fall back to "unknown" if no release_notes exist.

**Rationale**: The catalogue stores release_notes as a structured list per platform. Each platform has its own list of versions with timestamps. The latest version is the one with the maximum `ctime` across all platforms. This mirrors how the existing `check_for_updates` logic works.

**Code sketch**:
```python
def _extract_latest_version(entry):
    latest_ts = 0
    latest_version = None
    for platform_group in entry.get("release_notes", []):
        for note in platform_group.get("release_notes", []):
            ts = note.get("ctime", 0)
            if ts > latest_ts:
                latest_ts = ts
                latest_version = note.get("version_name")
    return latest_version or "unknown"
```

**Alternatives considered**:
- Use only WINDOWS platform: Cross-platform consistency matters; maximum across platforms is safer
- Store all versions in baseline: Wastes space for no analysis benefit
- Parse from `plugin_summary`: That field is for description_parser output, not version data

## Decision 4: Loading Current Version Data

**Decision**: Read the existing creations cache (populated by the Installed Creations tab's "Check for Updates") via `get_cached_info_any()` from `starfield_tool.creations`. This returns `dict[content_id, CreationInfo]` including the `version` field. If the cache is empty or stale, display a clear prompt telling the user to run "Check for Updates" in the Installed Creations tab first.

**Rationale**: Feature 009 should be purely read-only and side-effect-free. It shouldn't trigger API calls on its own. The existing cache is already populated when users actively maintain their load order, so piggybacking on it is both efficient and consistent with how the app manages version data. No network access, no credentials, no risk of rate limits.

**Alternatives considered**:
- Fetch versions live on tab open: Adds latency, requires network, duplicates existing functionality
- Read directly from Bethesda API: Same issue — we already have the data locally
- Store a separate cache: Data duplication for no benefit

## Decision 5: Exported List Import Format

**Decision**: Update the Installed Creations tab export to include a `Content ID` column (as the second column after `#`), and rename `Version` to `Installed Version` for clarity. Fast Lane Check accepts both new-format exports (reliable content_id matching) and legacy exports (fallback to title+author matching with a warning).

**New format**:
```csv
#,Content ID,Name,Author,Installed Version,Date
1,"4bd2936a-139f-4177-a4c8-2ab26261bb74","Dynamic Universe","youngneil1","2.2","29 Jan 2026"
```

**Rationale**: The current export uses `Name` (title) to identify creations. Matching by title is fragile because (1) two mods can share a name and (2) author strings can vary in formatting. Adding `content_id` makes matching UUID-exact. The rename from `Version` to `Installed Version` is a clarity improvement — the column always contained `c.installed_version`, but the shorter name was ambiguous when comparing against baseline/available versions.

**Backwards compatibility**: The import parser detects the new format by checking for the `Content ID` column in the header. For legacy exports (no Content ID), it falls back to matching by `(Name, Author)` tuple and displays a warning: "This is a legacy export without Content IDs. Matching is approximate." Users are encouraged to re-export.

**Alternatives considered**:
- Keep the old format and only match by title: Fragile, error-prone for common mod names
- Add a separate export just for Fast Lane Check: Fragments the export workflow
- Match by version fingerprint: Unreliable, titles+authors are a better signal anyway
- JSON-only export: Not user-friendly for a quick visual review

## Decision 6: UI Layout and Warning Banner

**Decision**: Two-phase UI. The tab starts in an **empty state** with the warning banner at the top and two large buttons centered below it: "Import Installed" and "Import from File". Pressing either button triggers the relevant load sequence and transitions the tab to the **loaded state**: a Treeview table showing the creations list (familiar columns from the Installed Creations tab) with two action buttons at the top — "Reset" (clears state, returns to empty state) and "Check" (runs the baseline comparison). The warning banner is persistent across both states.

**Rationale**:
- **Empty state first** makes the user's choice of input source explicit and prevents automatic scans that might surprise them
- **Reuses the familiar creations grid** reduces cognitive load — users already know what those columns mean from the Installed Creations tab
- **Check button is explicit** — the comparison isn't run automatically on load; it's a deliberate action. This matches how the Installed Creations tab's "Check for Updates" button works
- **Reset button** allows switching input sources (e.g., check installed, then reset and load a friend's export) without leaving the tab
- **Warning is always visible** across both phases so users can't miss it

**State transitions**:
```
[EMPTY STATE]
  Warning banner
  <Import Installed>  <Import from File>

  --> user clicks Import Installed or Import from File
  --> data loads into grid

[LOADED STATE]
  Warning banner
  <Reset>  <Check>   <summary: X loaded>
  ┌─────────────────────────────────────┐
  │ # │ Title │ Author │ Version │ Stat │
  ├───┼───────┼────────┼─────────┼──────┤
  │ 1 │  ...  │   ...  │   ...   │  ... │
  └─────────────────────────────────────┘

  --> user clicks Check
  --> baseline comparison runs (using existing creations cache)
  --> grid updates with baseline version, current version, status
  --> highlighted rows visible

  --> user clicks Reset
  --> state cleared, back to [EMPTY STATE]
```

**Check behavior**: When the user clicks "Check", the tool uses the existing creations cache (same access rules as the Installed Creations tab — session-fresh when available, any cache as fallback) to get the current available versions. If the cache has no data for a given creation, that row shows "Unknown" status. The Check button does NOT trigger new API calls — it only reads from the existing cache. Users are expected to have run "Check for Updates" in the Installed Creations tab at least once per session for best results (this is noted in the warning banner or a small info line near the Check button).

**Warning text**:
> ⚠ This check is approximate. It compares your installed creation versions against a baseline snapshot (dated YYYY-MM-DD). A creation is flagged as "not updated" if its current version exactly matches the baseline version — meaning no update has been published since the snapshot. Authors may have released fixes without bumping the version, and some mods may still work despite not being updated. For best results, run "Check for Updates" in the Installed Creations tab first. Always verify manually before making decisions.

**Alternatives considered**:
- Auto-load and auto-check on tab open: Surprising side effects, forces a specific input source
- Single "Run Check" button on empty state: Less discoverable for the two input modes
- Modal dialog on tab open: Annoying UX
- Dismissable warning: Defeats the purpose
- Warning in status bar: Too easy to overlook

## Decision 7: Tool Integration Point

**Decision**: New `ToolModule` subclass `FastLaneCheckTool` in `src/starfield_tool/tools/fast_lane_check.py`. Registered in `tools/__init__.py` MODULES list. Follows the same patterns as `RuleBookTool` (manager-style tab with treeview + button bar).

**Rationale**: Follows existing ToolModule architecture exactly. No new integration points needed.

**Alternatives considered**:
- Dialog launched from another tab: Less discoverable
- Menu item instead of tab: App has no menu bar, tabs are the navigation model
