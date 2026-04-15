# Contracts: Remove Creation

The feature exposes two pure functions plus one new field on the existing settings dataclass. All other surface is UI-internal.

## `plan_removal`

```python
def plan_removal(
    creation: Creation,
    plugins_txt: Path,
    data_dir: Path,
) -> RemovalPlan: ...
```

- **Inputs**:
    - `creation`: the current in-memory `Creation` object (has `content_id`, `display_name`, `plugin_files`).
    - `plugins_txt`: absolute path to Plugins.txt (so tests can pass a tmp path).
    - `data_dir`: absolute path to the Starfield Data directory.
- **Outputs**: a `RemovalPlan` (see data-model.md). Always returned; caller inspects `out_of_tree_files` to decide whether to allow Confirm.
- **Side effects**: none. Reads Plugins.txt only to classify which `plugin_files` are present; does not mutate anything.
- **Errors**: none raised for missing Plugins.txt or missing Data dir — the plan simply lists an empty set of targets for the missing side.

## `execute_removal`

```python
def execute_removal(
    plan: RemovalPlan,
    plugins_txt: Path,
    process_probe: Callable[[], bool] = is_starfield_or_launcher_running,
) -> RemovalResult: ...
```

- **Inputs**:
    - `plan`: the `RemovalPlan` the user confirmed.
    - `plugins_txt`: same path used during planning (must not have changed on disk in the meantime; caller is responsible for invoking on the main flow, not hours later).
    - `process_probe`: injectable game-running check. Defaults to the real probe; tests inject a lambda.
- **Outputs**: a `RemovalResult` describing every side effect, including whether the pre-flight probe blocked the op.
- **Side effects** (only when `process_probe()` returns False):
    - Plugins.txt is rewritten with matching lines removed.
    - Each file in `plan.files_to_delete` is attempted for deletion.
- **Errors**: no exceptions escape. All per-file failures are captured in `RemovalResult.file_outcomes`. Plugins.txt IO errors propagate only if the file cannot be read or rewritten — and in that case Plugins.txt must not be left in a half-written state (use atomic replace: write to `plugins.txt.tmp`, then `os.replace`).

## `is_starfield_or_launcher_running`

```python
def is_starfield_or_launcher_running() -> bool: ...
```

Lives in new module `src/starfield_tool/game_process.py`. Queries `tasklist` for Starfield.exe and the Bethesda launcher binaries. Returns True if any are running. Used by both the existing Apply tool (refactored to call this) and by Remove.

## Settings contract

`AppSettings.enable_dangerous_ops: bool = False`. Persisted via the existing JSON round-trip; no migration needed — missing field reads as `False` on load because the dataclass default kicks in.

## UI contract

- `CreationDetailsDialog(...)` gains an optional `on_remove: Callable[[], None] | None = None` parameter. When provided AND `enable_dangerous_ops` is True, a Remove button is constructed. When None or the flag is False, no button is constructed (absent, not hidden).
- A new `RemoveConfirmDialog(parent, plan, on_confirm)` and `RemoveResultDialog(parent, result)` live in `src/starfield_tool/dialogs/remove_creation.py`. Both follow the topmost-flash CTkToplevel pattern; neither uses `transient()` or `grab_set()`.
