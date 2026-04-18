# Phase 0 Research: Detect Broken Updates

## Decisions

### D-01: Three OR'd signals are sufficient
- **Decision**: Implement exactly the three detection signals named in the spec (partial-file, esm-without-plugins-line, mtime skew). Use OR composition with all reasons recorded per flagged Creation.
- **Rationale**: Both live failure modes observed in this repo's history (McClarence: partial files; Constellation HFSP: esm replaced while ba2s locked → mtime skew + esm still present but plugins.txt stripped → hits all three signals) are covered. Additional signals are speculative; principle I says build for what we've seen, not what might happen.
- **Alternatives considered**: (a) Parse the .esm TES4 header and compare its embedded version tuple against ContentCatalog.Version — feasible (we have the TES4 parser from feature 006) but ~100× more expensive per scan and redundant for the documented failure modes. (b) Compare file sizes against ContentCatalog.FilesSize — we noticed `FilesSize` is sometimes `0` in the wild, so not reliable.

### D-02: 60-second mtime skew threshold
- **Decision**: Default threshold: newest mtime − oldest mtime > 60 s → flag.
- **Rationale**: A healthy install of a multi-file Creation writes all files within a few seconds — tested against live install timestamps (e.g. Constellation .esm Mar 28 12:07 vs .ba2 Mar 28 11:43 is 24 minutes — clearly a repack, not a fresh install). 60 s gives plenty of headroom for a slow SSD or antivirus-throttled write without catching the interesting partial-update cases.
- **Alternatives considered**: 30 s (too tight, might flag slow writes), 300 s (too loose, would miss the Constellation pattern if the ba2 was written a few minutes before the esm).

### D-03: Reuse `plan_removal` + `execute_removal` from 013
- **Decision**: For each selected flagged Creation, construct a synthetic `Creation` (content_id, display_name, plugin_files=the full Files list) and feed it through the existing 013 removal pipeline.
- **Rationale**: Principle I and IV — no duplicated line-stripping or per-file error-tolerance logic; inputs/outputs of 013 are already documented and tested.
- **Alternatives considered**: Writing a multi-creation `execute_removal_many` — rejected; calling the existing function in a loop is simpler and retains per-Creation outcome traceability.

### D-04: Scan is synchronous on the main thread
- **Decision**: Scan runs synchronously. SC-002 budget is 3 s; actual work is ~1k stat calls.
- **Rationale**: Principle I. Threading adds complexity (main-thread marshalling, cancel handling, races with the delete path) for a sub-second win. If we measure >1 s in real-world data we add a background thread in a follow-up.
- **Alternatives considered**: A background thread with progress bar — rejected as YAGNI.

### D-05: Game-running check gates Delete only, not Scan
- **Decision**: Scan is read-only and runs regardless of process state. Delete aborts if Starfield or the launcher is detected at Confirm time.
- **Rationale**: Users who notice weird state mid-session should be able to *look* at it. They just can't *touch* it until they quit the game.
- **Alternatives considered**: Gate Scan too — rejected; read-only ops don't need the guard.

### D-06: Aggressive behaviour when Plugins.txt is missing
- **Decision**: If Plugins.txt cannot be read, signal (b) fires for every esm-having Creation.
- **Rationale**: A missing Plugins.txt is an abnormal state; surfacing the whole install as suspicious is the correct aggressive posture.
- **Alternatives considered**: Suppress signal (b) entirely when Plugins.txt is missing — rejected; would silently hide a catastrophic state.

### D-07: Dedicated dialog file rather than reusing 013's
- **Decision**: Add `src/starfield_tool/dialogs/broken_updates.py` with a multi-creation `BrokenConfirmDialog` and `BrokenResultDialog` rather than parameterising 013's `RemoveConfirmDialog`.
- **Rationale**: Multi-creation aggregation + the mandatory "no dependency check" warning diverge enough from 013's single-creation shape that cramming both into one class obscures intent. Cost: ~80 extra lines.
- **Alternatives considered**: Parameterise 013's dialogs with an optional warning-banner + list-of-lists mode — rejected as principle I violation (one class, two unrelated responsibilities).

### D-08: Alphabetical order is case-insensitive
- **Decision**: Sort flagged list and result-dialog names via `str.casefold` key.
- **Rationale**: Matches the "show list" feature we shipped in 013's branch, so users have a consistent ordering experience across the app.

## Resolved Clarifications

None — the spec passed the requirements checklist without markers.
