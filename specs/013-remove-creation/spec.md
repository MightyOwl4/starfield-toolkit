# Feature Specification: Remove Creation (Disable + Delete)

**Feature Branch**: `013-remove-creation`
**Created**: 2026-04-15
**Status**: Draft
**Input**: Remove a Creation from the tool — bundled disable + delete, gated behind an "Enable dangerous operations" setting, accessible from the Creation details dialog with explicit confirmation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove a working, installed Creation (Priority: P1)

A power user decides they no longer want a Creation they installed through the Bethesda store. They want one action that both disables the Creation (so the game stops loading it) and deletes its files (so disk space is reclaimed), without hunting through the in-game menu.

**Why this priority**: This is the core happy path; every other story is a variant or a safety net around it. Without this, the feature has no value.

**Independent Test**: With the dangerous-operations setting enabled, the game closed, and a healthy Creation installed, the user opens the details dialog, clicks Remove, confirms, and verifies that (a) the Creation no longer appears in the Installed Creations list after refresh, (b) the Plugins.txt entry is gone, (c) the Files listed for that Creation are gone from the Data directory.

**Acceptance Scenarios**:

1. **Given** the dangerous-operations setting is ON and the game is not running, **When** the user clicks Remove in the details dialog and confirms, **Then** the details dialog closes, a confirmation dialog opens listing the files and Plugins.txt line that will be affected, and on confirm the Creation's plugin line is stripped from Plugins.txt and every file in its ContentCatalog Files list is deleted from the Data directory.
2. **Given** a Remove operation completed, **When** the Installed Creations list is refreshed, **Then** the removed Creation no longer appears in the list.
3. **Given** the dangerous-operations setting is OFF, **When** the user opens the details dialog for any Creation, **Then** no Remove button is shown.

---

### User Story 2 - Abort removal before any change is made (Priority: P1)

The user opens the Remove confirmation by mistake, or reads the list of files and decides they don't actually want to proceed. They need a clearly labelled way to back out with zero side effects.

**Why this priority**: A destructive action without a reliable cancel path is unsafe to ship.

**Independent Test**: Open the confirmation dialog for a Creation, click Cancel (or close the window), and verify that Plugins.txt, the Data directory, and the Installed Creations list are all unchanged.

**Acceptance Scenarios**:

1. **Given** the confirmation dialog is open, **When** the user clicks Cancel or closes the window, **Then** no files are deleted, Plugins.txt is not modified, and the Installed Creations list is unchanged.
2. **Given** the confirmation dialog is open, **When** the user uses Win+D and then re-focuses the app, **Then** the confirmation dialog is still recoverable and the action has not executed.

---

### User Story 3 - Refuse to act while the game is running (Priority: P1)

The user tries to remove a Creation while Starfield or the Bethesda launcher is running. The tool must refuse, because modifying Plugins.txt mid-session corrupts load order state, and open files can't be deleted anyway.

**Why this priority**: Must match the existing Apply tool's guarantee. Inconsistent safety rules across destructive tools erode trust.

**Independent Test**: Start Starfield (or the launcher), attempt Remove on any Creation, observe that the operation is refused with a clear message and that Plugins.txt and the Data directory are unchanged.

**Acceptance Scenarios**:

1. **Given** Starfield.exe is running, **When** the user clicks Confirm in the remove dialog, **Then** the tool does not modify Plugins.txt or the Data directory and displays an error explaining the game must be closed first.
2. **Given** the Bethesda launcher is running, **When** the user clicks Confirm, **Then** the tool behaves as in scenario 1.

---

### User Story 4 - Recover a partially-broken Creation (Priority: P2)

A previous store update failed mid-flight, leaving stranded files on disk (e.g. the `.esm` and one `.ba2` survive while another `.ba2` is missing), and the in-game menu refuses to offer a Delete button because it sees a pending update. The user wants the tool to finish the cleanup the game couldn't.

**Why this priority**: Important recovery scenario and a strong motivator for the feature, but it rides on the P1 machinery.

**Independent Test**: Starting from a Creation whose ContentCatalog lists three files but only two exist on disk (and whose plugin is not in Plugins.txt because the launcher already stripped it), perform Remove and verify that the remaining on-disk files are deleted and the Creation is no longer listed.

**Acceptance Scenarios**:

1. **Given** a Creation's ContentCatalog Files list names files that are already missing from the Data directory, **When** the user performs Remove, **Then** the tool treats already-missing files as success and completes without error.
2. **Given** a Creation whose plugin line is already absent from Plugins.txt, **When** the user performs Remove, **Then** the tool treats the missing line as success and proceeds with file deletion.

---

### User Story 5 - Report per-file permission failures without aborting (Priority: P2)

One of a Creation's files is locked by another process (antivirus scan, explorer preview, stale game handle). The tool should delete every file it can, strip the Plugins.txt line, and then tell the user exactly which files it could not remove.

**Why this priority**: Safety net for the common partial-failure case.

**Independent Test**: Artificially hold a file handle on one of the Creation's `.ba2` files, perform Remove, and verify that (a) other files are deleted, (b) Plugins.txt is updated, (c) the user is shown a clear list of which specific files could not be deleted and why.

**Acceptance Scenarios**:

1. **Given** one of the Creation's files cannot be deleted because of an OS permission error, **When** the user performs Remove, **Then** all other files are deleted, Plugins.txt is still updated, and the result dialog lists the failed file(s) by name with the reason.
2. **Given** all of the Creation's files fail to delete, **When** the user performs Remove, **Then** Plugins.txt is still updated (if applicable) and the user is shown that no files were removed.

---

### Edge Cases

- Creation has no plugin files (esm-less ba2 replacer): Remove performs only the file-deletion step; no Plugins.txt edit is needed. The confirmation dialog must not mislead the user into thinking a plugin line will be stripped.
- Creation has multiple plugin files: every matching line must be stripped from Plugins.txt.
- Plugins.txt line appears with or without a leading `*`: both forms must be recognised and removed.
- Confirmation dialog is open when the game starts mid-operation: the game-running check happens at Confirm time, not at dialog open time, so a late start is still caught.
- Two details dialogs open for the same Creation: after Remove the stale dialog must not act on a now-gone Creation.
- ContentCatalog Files entry containing a path separator: treated as relative to the Data directory; if it resolves outside Data it is refused.
- Settings file read-only or corrupt: the dangerous-operations setting defaults to OFF and any persistence failure leaves it OFF.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Settings panel MUST expose a boolean option labelled "Enable dangerous operations" that defaults to OFF and persists across app restarts in the existing settings store.
- **FR-002**: The Creation details dialog MUST show a Remove button only when the dangerous-operations setting is ON; when OFF, the Remove button MUST be absent (not merely disabled).
- **FR-003**: Clicking Remove in the details dialog MUST close the details dialog and open a confirmation dialog.
- **FR-004**: The confirmation dialog MUST list the files that will be deleted (from the ContentCatalog Files entry for that Creation) and, when applicable, the Plugins.txt line(s) that will be stripped.
- **FR-005**: The confirmation dialog MUST provide an explicit Cancel path that closes the dialog without mutating any state.
- **FR-006**: The confirmation dialog MUST be Win+D recoverable — no transient()/grab_set() and no tkinter.simpledialog.* usage.
- **FR-007**: When the user confirms, the tool MUST first check whether Starfield or the Bethesda launcher is running and, if so, abort with a clear message and no state changes.
- **FR-008**: On confirm with the game not running, the tool MUST strip every line from Plugins.txt matching any of the Creation's plugin files (.esm/.esp/.esl), regardless of whether the line had a leading `*`.
- **FR-009**: On confirm with the game not running, the tool MUST attempt to delete every file listed in the Creation's ContentCatalog Files entry from the Data directory.
- **FR-010**: File deletions MUST be per-file fault-tolerant: a permission or I/O error on one file MUST NOT abort the operation; remaining files and the Plugins.txt edit MUST still be attempted.
- **FR-011**: Already-missing files and already-absent Plugins.txt lines MUST be treated as success (idempotent).
- **FR-012**: On completion (success or partial), the tool MUST show a result summary listing files successfully deleted and files that failed, with a human-readable reason per failure.
- **FR-013**: On completion, the Installed Creations list MUST refresh automatically.
- **FR-014**: The tool MUST NOT modify ContentCatalog.txt as part of this operation.
- **FR-015**: The tool MUST NOT require elevated/admin privileges for the normal case.
- **FR-016**: The Remove action MUST operate on a single Creation at a time; no multi-select is supported in this feature.

### Key Entities

- **Dangerous-operations setting**: A boolean flag in the app settings store. OFF by default. Gates visibility of the Remove button everywhere in the UI.
- **Remove plan**: The per-Creation precomputed list of side effects (files to delete, plugin lines to strip) displayed in the confirmation dialog and executed on confirm. Derived from the Creation's ContentCatalog entry and the current Plugins.txt.
- **Remove result**: The outcome of the operation — files deleted, files skipped as already-missing, files failed (with reasons), plugins.txt modified (yes/no). Displayed to the user post-confirm.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with the dangerous-operations setting ON can remove a healthy Creation (disable + delete + refreshed list) in fewer than 15 seconds from clicking Remove to seeing the list refresh, for typical Creation sizes.
- **SC-002**: Zero file-system or Plugins.txt mutations occur in any code path that does not pass through the confirmation dialog's explicit Confirm click.
- **SC-003**: 100% of Remove attempts made while the game or launcher is running are refused with a clear message and leave Plugins.txt and the Data directory unchanged.
- **SC-004**: When at least one file is locked by another process, the tool still deletes every other listed file, still updates Plugins.txt, and names each failed file in the result summary.
- **SC-005**: The dangerous-operations setting OFF state results in zero Remove buttons being rendered anywhere in the UI, verified by UI inspection of the Installed Creations tab and its details dialog.
- **SC-006**: Removing a partially-broken Creation (whose plugins.txt line is already absent and whose file list is partly already gone) completes successfully and removes it from the list.

## Assumptions

- The existing settings store (used for other persisted preferences) is available and reusable.
- The existing Apply tool's game-running detection logic can be reused or extended for the Remove operation's pre-flight check.
- ContentCatalog.txt's Files list is authoritative for what belongs to a Creation on disk.
- Users are responsible for closing any external process (antivirus, explorer previews) that may lock files; the tool surfaces the error but does not attempt to release locks.
- The launcher may later re-populate a ContentCatalog entry if the user re-subscribes through the store; this is acceptable and out of scope.
- The setting name "Enable dangerous operations" is general enough to gate future destructive actions; this feature only wires it to Remove.
