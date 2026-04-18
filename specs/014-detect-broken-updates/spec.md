# Feature Specification: Detect Broken Updates

**Feature Branch**: `014-detect-broken-updates`
**Created**: 2026-04-15
**Status**: Draft
**Input**: A new tab that scans disk state for Creations in a half-broken state (partial files, mid-update, stranded esm without a plugins.txt entry) and offers aggressive Delete as the recovery path. Not gated by the dangerous-ops setting; tab itself is the discoverability hurdle.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find and clean a stranded partial-update (Priority: P1)

A user's in-game update failed (Starfield was running; the `.esm` got replaced but `.ba2` files didn't — Constellation High Fidelity Skin Pack case, or some files disappeared entirely — McClarence case). The in-game Creations menu shows Update but Update keeps failing for the same reason. The user opens the tool, goes to the Detect Broken Updates tab, clicks Scan, sees their broken Creation highlighted, selects it, clicks Delete, confirms, and gets a clean slate. After the op completes, a dialog lists what was removed so they can paste the names into the in-game Creations menu for a fresh install.

**Why this priority**: This is the entire feature; every other story is a guardrail around it. Without this, there's no tab.

**Independent Test**: With the game closed and a Creation deliberately put into a partial-file state on disk (e.g. `.esm` present, `- main.ba2` missing, catalog entry intact), open the tab, click Scan, verify the Creation is flagged with a reason. Select it, click Delete, click Confirm, verify the remaining on-disk files are gone, Plugins.txt line (if any) is gone, and the result dialog lists the Creation's name.

**Acceptance Scenarios**:

1. **Given** a Creation whose ContentCatalog Files list contains three entries, only two of which exist in Data/, **When** the user clicks Scan, **Then** the Creation appears flagged with a reason that mentions the partial-file state.
2. **Given** a Creation whose `.esm` exists in Data/ but whose filename does not appear in Plugins.txt (neither with nor without a leading `*`), **When** the user clicks Scan, **Then** the Creation appears flagged with a reason that mentions the missing plugins.txt line.
3. **Given** a Creation whose files on disk have mtimes spread across more than 60 seconds, **When** the user clicks Scan, **Then** the Creation appears flagged with a reason that mentions the mtime skew.
4. **Given** a flagged Creation is selected, **When** the user clicks Delete and Confirm with the game closed, **Then** every file in the Creation's ContentCatalog Files list is attempted for deletion from Data/, the Plugins.txt line is stripped if present, and the user sees a result dialog naming the Creation in alphabetical order with any other simultaneously-deleted Creations.

---

### User Story 2 - Refuse while the game is running (Priority: P1)

The user tries to Delete while Starfield or the Bethesda launcher is running. The tool refuses, the same way Remove (feature 013) and Apply refuse. No file is touched, no Plugins.txt line is stripped.

**Why this priority**: Consistency with the rest of the app's destructive operations and the only way to avoid re-creating the same "mapped-ba2" failure that stranded the files in the first place.

**Independent Test**: Start Starfield, click Scan (allowed — read-only), select a flagged Creation, click Delete, Confirm; verify a clear error is shown and the on-disk state and Plugins.txt are unchanged.

**Acceptance Scenarios**:

1. **Given** Starfield.exe is running, **When** the user clicks Confirm in the Delete dialog, **Then** no files are deleted and no Plugins.txt lines are stripped; an error explains the game must be closed first.
2. **Given** the Bethesda launcher is running, **When** the user clicks Confirm, **Then** behaviour matches scenario 1.

---

### User Story 3 - Explicit, dependency-ignorant confirmation (Priority: P1)

The user reviews the confirmation dialog before any destructive action. The dialog lists every file that will be deleted and every plugins.txt line that will be stripped, AND it warns — prominently — that the tool does NOT run any dependency check. If the user deletes a Creation that another enabled Creation depends on, the user alone is responsible for dealing with the fallout.

**Why this priority**: The whole tab is aggressive-by-design. Without this explicit warning, users will blame the tool when they break their load order.

**Independent Test**: Open the Delete confirmation for any selection; verify the dialog contains the list of files/plugin lines and a visually-distinct warning about no dependency check. Click Cancel; verify nothing changed.

**Acceptance Scenarios**:

1. **Given** one or more flagged Creations are selected, **When** the user clicks Delete, **Then** a confirmation dialog opens showing all files to be deleted, all plugins.txt lines to be stripped, and an explicit warning that no dependency check is performed.
2. **Given** the confirmation dialog is open, **When** the user clicks Cancel or closes the window, **Then** no files are deleted, no Plugins.txt lines are stripped, and the flagged list is unchanged.
3. **Given** the confirmation dialog is open, **When** the user uses Win+D and re-focuses the app, **Then** the dialog is recoverable and no destructive action has run.

---

### User Story 4 - Offline scan (Priority: P2)

The user is offline or has not run the update-check. They should still be able to scan for broken updates — the whole mechanism is on-disk analysis.

**Why this priority**: Ensures the tab works in the failure mode (no network, Bethesda servers down, launcher misbehaving) where the user most needs it.

**Independent Test**: With no network access, open the tab, click Scan; verify the flagged list is produced and the Delete flow still works.

**Acceptance Scenarios**:

1. **Given** the app has no network access and the update cache is empty, **When** the user clicks Scan, **Then** the flagged list is produced using only on-disk data.

---

### User Story 5 - Empty result (Priority: P2)

The user clicks Scan on a healthy install. They get an obvious "nothing suspicious found" indication — not an empty list with no explanation.

**Why this priority**: Without this, a healthy user will wonder if the tab is broken.

**Independent Test**: On a known-healthy install, click Scan; verify an empty-state message is visible and the Delete button is disabled.

**Acceptance Scenarios**:

1. **Given** no Creation trips any detection signal, **When** the user clicks Scan, **Then** the tab displays an explicit empty-state message and the Delete button is disabled.

---

### Edge Cases

- Scan clicked twice in quick succession — the second scan supersedes the first; nothing breaks.
- A Creation has zero Files listed in ContentCatalog — treat as not-flagged (nothing to check).
- A Creation's Files reference a path that resolves outside the Data directory — flagged with a dedicated "out of tree" reason; Delete refuses to touch out-of-tree files but still handles in-tree ones.
- The same Creation trips multiple detection signals — all reasons are reported, not just the first.
- `ContentCatalog.txt` is missing entirely — Scan reports no flagged Creations (nothing to compare against).
- `Plugins.txt` is missing entirely — the "esm without plugins.txt line" signal fires for every esm-having Creation; this is the correct aggressive behaviour.
- A flagged Creation is also visible on the Installed Creations tab (because that tab's filter is more lenient) — both tabs coexist without conflict; this tab reports what disk state says.
- The user selects Creations and then re-runs Scan — the selection is cleared to avoid acting on stale identities.
- Delete encounters a per-file permission error — the operation is not aborted; remaining files and plugins.txt are still processed; the failed file is named in the result dialog.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST expose a new top-level tab titled "Detect Broken Updates" in the main tab strip.
- **FR-002**: The tab MUST provide a Scan button. Scan is the only way to run detection — the tool MUST NOT auto-scan on tab switch, on launch, or on file-system events.
- **FR-003**: Scan MUST flag a Creation when any of the following signals is true; the logic is OR'd, not AND'd:
    - (a) ContentCatalog.Files contains at least one entry that is present on disk AND at least one entry that is absent on disk (partial-file state).
    - (b) ContentCatalog.Files contains an `.esm` / `.esp` / `.esl` that exists on disk but whose filename does not appear in Plugins.txt (case-insensitive, with or without the `*` prefix).
    - (c) Among the files that exist on disk for that Creation, the spread between the newest and oldest mtime exceeds 60 seconds.
- **FR-004**: Each flagged Creation MUST display the reason(s) it was flagged. When multiple signals fire, all MUST be shown.
- **FR-005**: The flagged list MUST use the same column shape as the Installed Creations tab (position, name, author, version, date) and MUST visually distinguish flagged rows (e.g. red or orange tag).
- **FR-006**: Flagged list entries MUST be sorted consistently run-to-run. A stable order (by Creation display name, case-insensitive) is sufficient.
- **FR-007**: The tab MUST provide a Delete button that is enabled only when at least one flagged Creation is selected.
- **FR-008**: Clicking Delete MUST check whether Starfield or the Bethesda launcher is running and MUST refuse with a clear error if so; no state changes MUST occur.
- **FR-009**: When the game is not running, clicking Delete MUST open a confirmation dialog listing every file that will be deleted across all selected Creations and every Plugins.txt line that will be stripped.
- **FR-010**: The confirmation dialog MUST display a visually-distinct warning that the operation does NOT perform a dependency check and that broken dependencies are the user's responsibility.
- **FR-011**: The confirmation dialog MUST provide an explicit Cancel path that leaves all state unchanged.
- **FR-012**: All dialogs in this feature MUST be Win+D recoverable — no `transient()`, no `grab_set()`, no `tkinter.simpledialog.*`.
- **FR-013**: On Confirm, the tool MUST iterate the selected flagged Creations and, for each, strip matching Plugins.txt lines and attempt to delete every entry in the Creation's ContentCatalog Files list from the Data directory.
- **FR-014**: Deletions MUST be per-file fault-tolerant: a permission or I/O error on one file MUST NOT abort the overall operation; remaining files and plugins.txt edits MUST still be attempted.
- **FR-015**: Already-absent files and already-absent Plugins.txt lines MUST be treated as success (idempotent).
- **FR-016**: On completion, the tool MUST display a result dialog listing, at minimum, the display names of the Creations that were processed, sorted alphabetically (case-insensitive), in a text area the user can select and copy.
- **FR-017**: The Detect Broken Updates feature MUST be usable offline — detection MUST depend only on on-disk state (ContentCatalog.txt, Plugins.txt, Data/) and MUST NOT require any network call.
- **FR-018**: The Delete action in this tab MUST NOT be gated behind the "Enable dangerous operations" setting introduced by feature 013.
- **FR-019**: The tool MUST NOT modify ContentCatalog.txt as part of this operation.
- **FR-020**: When no Creation trips any detection signal, the tab MUST display an explicit empty-state message (e.g. "No broken updates detected") and keep the Delete button disabled.

### Key Entities

- **Detection reason**: A short categorical label (e.g. "partial files", "esm without plugins.txt line", "mtime skew", "out of tree") attached to each flagged Creation. Multiple reasons per Creation are supported.
- **Flagged Creation entry**: A row in the tab's list comprising the Creation's identity (content id, display name, author, catalog version) plus its list of detection reasons plus its list of files currently on disk. Drives both list rendering and the delete plan.
- **Delete plan (multi-Creation)**: The aggregate set of files-to-delete and plugins.txt-lines-to-strip across the user's current selection. Shown in the confirmation dialog. Executed per-Creation; reported atomically in the result dialog.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a known-broken Creation in any of the three documented patterns, the user can go from launching the tool to a clean slate (Creation fully removed from disk and Plugins.txt) in under 60 seconds with the game closed.
- **SC-002**: On a typical install with 50–200 ContentCatalog entries, Scan completes and renders the flagged list in under 3 seconds.
- **SC-003**: 100% of Delete attempts made while the game or launcher is running are refused with a clear message and leave disk state and Plugins.txt unchanged.
- **SC-004**: Zero destructive mutations occur in any path that does not pass through the confirmation dialog's explicit Confirm click.
- **SC-005**: When at least one file in the selection is locked by another process, the tool still deletes every unlocked file, still updates Plugins.txt, and names each failed file in the result summary.
- **SC-006**: 100% of Creations that match any detection signal in a curated fixture of partial-update states are flagged. No false negatives on the three documented patterns.
- **SC-007**: When run on a healthy install with zero broken states, Scan completes without error, displays the empty-state message, and leaves the Delete button disabled.

## Assumptions

- The existing game-running detection (Starfield.exe, BethesdaNetLauncher.exe, Starfield_BGS.exe — implemented in feature 013) is reusable.
- The per-file fault-tolerant deletion and plugins.txt-line-stripping machinery from feature 013 (`plan_removal`, `execute_removal`) is reusable and driven from this tab.
- The current tool/tab architecture (`ToolModule` subclasses in `src/starfield_tool/tools/`) is the right shape; no new plumbing in the main app shell beyond registering the new module.
- A 60-second mtime threshold is the right default for signal (c). If false positives surface, the threshold is tuneable in a follow-up without changing the spec.
- Users of this tab understand Starfield's modding concepts (ContentCatalog, Plugins.txt, Data/); the warning in the confirmation dialog is enough.
- Feature 013's filter behaviour (hiding disabled / ghost creations from the Installed Creations tab) is complementary — this tab may surface Creations the other tab hides, by design.
- Re-install after delete is handled by the user via the in-game Creations menu; the result dialog names the Creations to make that easy. The tool does not open browser windows or deep-link into the game for this flow.
