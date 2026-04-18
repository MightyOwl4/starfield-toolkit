# Data Model: Detect Broken Updates

All types live in `src/starfield_tool/broken_scan.py` unless noted.

## `DetectionReason` (string-typed enum-like)

String literals, not an `enum.Enum`, to match 013's convention:

| Value                        | When it fires                                                                              |
|------------------------------|--------------------------------------------------------------------------------------------|
| `"partial_files"`            | At least one of the Creation's Files is on disk AND at least one is absent.                |
| `"esm_without_plugins_line"` | An `.esm`/`.esp`/`.esl` is on disk but its filename does not appear in Plugins.txt.        |
| `"mtime_skew"`               | Among files that exist on disk, newest − oldest mtime exceeds 60 seconds.                  |
| `"out_of_tree"`              | One of the Creation's Files resolves outside the Data directory (safety refusal).          |

## `FlaggedCreation`

One per flagged Creation.

| Field                  | Type                | Notes                                                        |
|------------------------|---------------------|--------------------------------------------------------------|
| `content_id`           | `str`               | ContentCatalog key.                                          |
| `display_name`         | `str`               | Catalog Title (stale names are OK for this tab's purpose).   |
| `author`               | `str`               | Catalog Author.                                              |
| `catalog_version`      | `str`               | Catalog Version field (raw).                                 |
| `catalog_files`        | `list[str]`         | Full Files list as recorded in ContentCatalog.               |
| `plugin_files`         | `list[str]`         | Subset of catalog_files ending in `.esm`/`.esp`/`.esl`.      |
| `files_present`        | `list[Path]`        | Absolute paths of files currently on disk (inside Data).     |
| `files_missing`        | `list[str]`         | Files entries that aren't on disk (raw strings).             |
| `reasons`              | `list[DetectionReason]` | All signals that fired; at least one.                    |

**Invariants**:

- `len(reasons) >= 1`.
- `files_present ∪ files_missing == set(catalog_files except out_of_tree ones)`.
- If `"out_of_tree"` in reasons, the offending entries are reported via `files_missing` (they are not deleted).

## Detector signature

```python
def scan_broken(
    catalog_entries: list[CatalogEntry],     # from starfield_tool.parsers.parse_content_catalog
    plugin_entries: list[PluginEntry],       # from starfield_tool.parsers.parse_plugins_txt
    data_dir: Path,
    now_fn: Callable[[], float] = time.time, # injectable for deterministic tests
    mtime_skew_threshold_s: float = 60.0,
) -> list[FlaggedCreation]: ...
```

- Plugins absent / empty → treat as "no active lines", which triggers signal (b) for every esm-having Creation (aggressive by design, per D-06).
- Catalog absent / empty → empty result (nothing to scan).
- Return order: sort by `display_name.casefold()` for FR-006.

## Delete aggregation

The tab builds a selection-level plan out of per-Creation 013 plans, and executes them one by one.

```python
@dataclass
class BrokenDeletePlan:
    flagged: list[FlaggedCreation]           # the user's selection, in display order
    removal_plans: list[RemovalPlan]         # one per flagged, built via plan_removal()

@dataclass
class BrokenDeleteResult:
    game_was_running: bool = False
    results: list[tuple[FlaggedCreation, RemovalResult]] = field(default_factory=list)
    display_names_processed: list[str] = field(default_factory=list)   # alphabetical, case-insensitive
```

**Execution**:

```text
pre-flight game-running check (once, up front)
    ├── True  → BrokenDeleteResult(game_was_running=True); show Result dialog; stop.
    └── False → for each (flagged, plan):
                   result = execute_removal(plan, plugins_txt, process_probe=lambda: False)
                   results.append((flagged, result))
                display_names_processed = sorted(
                    (f.display_name for f in flagged),
                    key=str.casefold,
                )
                show Result dialog
```

We pass `process_probe=lambda: False` into `execute_removal` because we already did the pre-flight check; calling `tasklist` once per Creation would be wasteful.

## State Transitions

```text
tab opens
    └── empty state (no flagged rows; Delete disabled)

Scan clicked
    ├── no flagged → empty-state message (FR-020)
    └── flagged    → tree populated; selection empty; Delete disabled

selection changed
    ├── empty → Delete disabled
    └── ≥1    → Delete enabled

Delete clicked
    └── open BrokenConfirmDialog

Confirm clicked
    └── execute_removal loop → BrokenResultDialog → tree refreshed (auto-rescan)

Cancel / close confirm
    └── no-op, tree unchanged
```

## Error Model

- Plugins.txt missing → signal (b) fires aggressively; no exception.
- ContentCatalog.txt missing → empty scan result; no exception.
- Data dir missing → all entries marked `files_missing` for everything → signal (a) fires for multi-file Creations, signal (b) does not fire (nothing on disk).
- Individual stat failure → treat the file as not-on-disk; no exception.
- Per-file delete failure → recorded in `RemovalResult.file_outcomes` (inherited from 013).
