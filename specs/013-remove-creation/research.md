# Phase 0 Research: Remove Creation

## Decisions

### D-01: ContentCatalog.txt is not mutated
- **Decision**: Leave ContentCatalog.txt untouched during Remove.
- **Rationale**: Live tracing (see session notes) showed the game never prunes ContentCatalog on in-game delete — it leaves stale metadata. The tool's list builder already filters ghosts (entries whose files don't exist) since commit `d898fec`. Writing to the file would race the Bethesda launcher and gain nothing observable.
- **Alternatives considered**: (a) Prune the JSON on Remove — rejected as scope creep and race-prone. (b) Rewrite as null — rejected as launcher behaviour is opaque.

### D-02: Plugins.txt edit is plain-text line stripping
- **Decision**: Read lines, drop any whose trimmed filename (`* ` prefix optional, case-insensitive) matches a plugin file of the Creation, write back with original line endings preserved where trivially possible.
- **Rationale**: Plugins.txt is a flat list; empirical diffs on disable/delete confirmed the game writes single-line entries with `\r\n` endings on Windows. No nested structure to respect.
- **Alternatives considered**: Using an XML/TOML-style parser — not applicable, the format is just one-line-per-plugin.

### D-03: Game-running detection reuses `tasklist`
- **Decision**: Extract the existing `subprocess.run(["tasklist", "/FI", "IMAGENAME eq X", "/NH"])` call into a shared helper and extend it to check Starfield.exe, BethesdaNetLauncher.exe, and Starfield_BGS.exe.
- **Rationale**: Identical code already ships in `LoadOrderTool._is_starfield_running`. Extraction is one-for-one; no new behaviour introduced.
- **Alternatives considered**: `psutil` — rejected (new dependency, principle III). WMI — rejected (slower, COM overhead).

### D-04: Pure-logic module for plan + execute
- **Decision**: `removal.py` contains two functions and two dataclasses. No tkinter. No implicit state.
- **Rationale**: Principle II requires testable behaviour. A UI-coupled implementation can't be run in CI.
- **Alternatives considered**: A `RemovalService` class — rejected (principle I: no premature class hierarchy).

### D-05: Per-file error tolerance
- **Decision**: Iterate the Files list; wrap each `os.remove` in try/except catching `PermissionError`, `FileNotFoundError` (idempotent success), `OSError`. Collect outcomes into `RemovalResult.file_outcomes: list[FileOutcome]`.
- **Rationale**: Empirical McClarence failure showed OS locks are routine, not exceptional. An all-or-nothing model forces users into manual cleanup; per-file surfaces partial success honestly (FR-010, FR-012, SC-004).
- **Alternatives considered**: Transactional rollback (restore Plugins.txt if any file fails) — rejected (rolling back a partial delete is worse than reporting it; users can retry).

### D-06: Confirmation dialog follows `load_order_diff.py` pattern
- **Decision**: CTkToplevel with `attributes("-topmost", True)` and an `after(100, ...)` flash-to-false. No `transient()`, no `grab_set()`. Explicit Cancel button and `WM_DELETE_WINDOW` both call a no-op close.
- **Rationale**: Project memory ("Dialogs must survive Win+D"). Pattern is proven in `DiffDialog`.
- **Alternatives considered**: `tkinter.simpledialog.askyesno` — explicitly forbidden by memory.

### D-07: Post-remove refresh reuses existing `_refresh()`
- **Decision**: After execute completes, call `CreationLoadOrderTool._refresh()` on the main thread via `.after(0, ...)`.
- **Rationale**: The refresh path is already debounced and correct; reusing it avoids divergent list-building code (principle I).

### D-08: Settings UI — single checkbox near `beta_acknowledged`
- **Decision**: Add `enable_dangerous_ops: bool = False` to `AppSettings`, render one checkbox in the existing settings view.
- **Rationale**: Same pattern as the existing flag. No new settings infrastructure (principle III: nothing to add; principle I: mirror existing).

## Resolved Clarifications

None outstanding. All spec NEEDS CLARIFICATION markers were resolved in-session before the spec was finalised.
