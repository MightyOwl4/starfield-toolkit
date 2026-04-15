# Data Model: Remove Creation

All types live in `src/starfield_tool/removal.py` unless noted.

## `AppSettings` (modified — in `src/starfield_tool/config.py`)

Existing dataclass gains one field:

| Field                   | Type | Default | Notes                                                                 |
|-------------------------|------|---------|-----------------------------------------------------------------------|
| `enable_dangerous_ops`  | bool | `False` | Gates visibility of the Remove button everywhere. Persisted to JSON.  |

Round-trip semantics are unchanged: `load_config()` returns the new default when the field is absent in an older JSON file; `save_config()` writes it on next save.

## `RemovalPlan`

Precomputed by `plan_removal(...)` and shown in the confirmation dialog. Pure data; no behaviour.

| Field                | Type               | Notes                                                                        |
|----------------------|--------------------|------------------------------------------------------------------------------|
| `content_id`         | `str`              | The Creation's ContentCatalog key, for display and log trail.                |
| `display_name`       | `str`              | Human-readable title shown in the confirmation dialog.                       |
| `plugin_files`       | `list[str]`        | `.esm`/`.esp`/`.esl` names that should be stripped from Plugins.txt.         |
| `files_to_delete`    | `list[Path]`       | Absolute paths inside `data_dir` that will be removed.                       |
| `out_of_tree_files`  | `list[str]`        | Files whose relative path escapes `data_dir` — refused pre-confirm.          |

**Invariant**: every `Path` in `files_to_delete` resolves to a descendant of `data_dir`. Entries that fail this are routed to `out_of_tree_files` instead.

**Refusal rule**: if `out_of_tree_files` is non-empty, the plan is still returned but the confirmation dialog MUST show a blocking error and disable the Confirm button. This is a spec edge case (ContentCatalog with a `..` path) handled safely.

## `FileOutcome`

One entry per file attempted.

| Field    | Type                                | Notes                                                                 |
|----------|-------------------------------------|-----------------------------------------------------------------------|
| `path`   | `Path`                              | The file we tried to delete.                                          |
| `status` | `"deleted" \| "already_gone" \| "failed"` | `already_gone` = idempotent success (FileNotFoundError treated so). |
| `reason` | `str \| None`                       | Human-readable failure reason when `status == "failed"`.              |

## `RemovalResult`

Returned by `execute_removal(...)`.

| Field                 | Type                  | Notes                                                                                  |
|-----------------------|-----------------------|----------------------------------------------------------------------------------------|
| `game_was_running`    | `bool`                | When True, nothing else in the result mutated state.                                   |
| `plugins_txt_updated` | `bool`                | Whether Plugins.txt was rewritten.                                                     |
| `plugin_lines_dropped`| `list[str]`           | Verbatim lines removed from Plugins.txt (for the result summary).                      |
| `file_outcomes`       | `list[FileOutcome]`   | One per entry in `plan.files_to_delete`.                                               |

**Success criterion**: the operation is considered successful if `not game_was_running` and every outcome is `deleted` or `already_gone`. Partial failure is any `failed` outcome.

## State Transitions

```text
plan_removal()
    │
    ▼
RemovalPlan ──(out_of_tree non-empty)──► show blocking error in dialog (no execute)
    │
    └─(Confirm)──► execute_removal() ──► RemovalResult ──► show result dialog
                                                     │
                                                     └──► trigger CreationLoadOrderTool._refresh()
```

## Error Model

- `FileNotFoundError` on a Files entry → `status="already_gone"` (idempotent).
- `PermissionError` / other `OSError` on a Files entry → `status="failed"` with `reason=str(exc)`.
- Plugins.txt missing entirely → `plugins_txt_updated=False`, no error (nothing to strip).
- Plugins.txt present but none of the Creation's plugins listed → `plugins_txt_updated=False`, no error.
- Game-running pre-check positive → `game_was_running=True`, no mutations, empty `file_outcomes`.
