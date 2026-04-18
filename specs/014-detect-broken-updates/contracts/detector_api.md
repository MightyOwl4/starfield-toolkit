# Contracts: Detect Broken Updates

The feature exposes one pure function and two dialog classes. Everything else is UI internal to `tools/broken_updates.py`.

## `scan_broken`

```python
def scan_broken(
    catalog_entries: list[CatalogEntry],
    plugin_entries: list[PluginEntry],
    data_dir: Path,
    now_fn: Callable[[], float] = time.time,
    mtime_skew_threshold_s: float = 60.0,
) -> list[FlaggedCreation]: ...
```

- **Inputs**: parsed CatalogEntry / PluginEntry lists (existing types from `starfield_tool.parsers`), the Data directory path, an injectable clock, and a tunable threshold.
- **Output**: list of `FlaggedCreation` sorted by `display_name.casefold()`.
- **Side effects**: reads file stat information only. No writes, no network.
- **Errors**: no exception escapes. Stat failures are treated as "file not present" for detection.

## Reused from feature 013

- `starfield_tool.game_process.is_starfield_or_launcher_running()` — used by the tab's Confirm handler.
- `starfield_tool.removal.plan_removal(creation, plugins_txt, data_dir) -> RemovalPlan` — used to build each per-Creation removal plan. A synthetic `Creation(content_id, display_name, plugin_files=catalog_files)` is constructed; `plan_removal` already filters `plugin_files` to esm-like files internally for the Plugins.txt side.
- `starfield_tool.removal.execute_removal(plan, plugins_txt, process_probe) -> RemovalResult` — called per flagged Creation with `process_probe=lambda: False` since the tab did the single up-front probe.

## UI contract

- **`BrokenUpdatesTool(ToolModule)`** registered in `src/starfield_tool/tools/__init__.py::MODULES`. `name = "Detect Broken Updates"`. No public methods beyond `initialize`.
- **`BrokenConfirmDialog(parent, plan: BrokenDeletePlan, on_confirm: Callable[[], None])`**: lists every file to delete (grouped by Creation), every plugins.txt line to strip, a prominent "no dependency check" warning banner, Cancel + Confirm buttons. No `transient()`, no `grab_set()`. Topmost flash pattern.
- **`BrokenResultDialog(parent, result: BrokenDeleteResult)`**: scrollable frame showing the alphabetical list of processed Creations in a selectable `CTkTextbox`, followed by per-Creation per-file outcomes. Distinct red banner when `result.game_was_running` is True.

## Settings contract

This feature adds **no** new settings fields. It deliberately does not gate Delete behind feature 013's `enable_dangerous_ops` — tab discoverability is the hurdle (FR-018).
