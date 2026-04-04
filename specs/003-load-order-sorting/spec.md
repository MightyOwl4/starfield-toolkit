# Feature Specification: Load Order Sorting Tool

**Feature Branch**: `003-load-order-sorting`
**Created**: 2026-03-30
**Status**: Draft
**Input**: User description: "Implement the Load order tool with manual resorting, LOOT integration, category-based automated sorting, snapshot export/import, and diff-style approval view for proposed changes."

## Research Notes

Community research (hst12/Starfield-Creations-Mod-Manager, monster-cookie/starfield-modding-notes, LOOT project, [XSX] Starfield Load Orders spreadsheet) reveals a well-established 11-category tiered ordering system:

1. **Master Files** — core patches and requirements (locked)
2. **Game Menu / Launch / Framework** — startup mods, foundational tools
3. **Invasive World Edits** — quest mods, faction overhauls, planet/world modifications, enemy additions
4. **Workshop** — settlement building, outpost objects
5. **Gameplay Changes** — settings, animations, perks, skills, traits, Starborn powers
6. **Companions** — new companions, NPC behavior modifications
7. **Audio / Visual** — radio, textures, atmospheric improvements
8. **HUD / UI** — interface enhancements
9. **Ship Additions** — modules, weapons, rebalancing
10. **Character Wearables** — body models, weapons, armor, clothing, crafting
11. **Non-Invasive World Edits** — homes, settlements, weapon/armor modifications

Each category has subcategories (A, B, C...) for finer ordering within tiers. Entries are color-coded by working status (green = working, yellow = issues, red = non-functional).

Key constraints: Bethesda's system/DLC master files (SFBGS prefixed) always load first and are filtered out of the creation list by the parser. Bethesda marketplace creations sort by content category like any other creation. The "last loaded wins" rule means conflict resolution depends on position. Achievement-friendly status is already tracked by our existing tools. LOOT provides masterlist-based sorting via its own process. Changing load order mid-game is explicitly discouraged by Bethesda.

**Sources**:
- [XSX] Starfield Load Orders spreadsheet (11-tier community guide)
- monster-cookie/starfield-modding-notes LoadOrder.md
- Ortham's Load Order in Starfield blog post
- LOOT project documentation
- hst12/Starfield-Creations-Mod-Manager-and-Catalog-Fixer

## UI Context

This feature lives in the existing **"Load Order"** tab, which is separate from the "Installed Creations" tab. The creation list display is the same but the tab is segmented to keep sorting controls, diff view, and snapshot buttons separate from the check/export controls in Installed Creations.

**Future expansion note**: The tool currently only sees locally installed plugins. A future feature may integrate a browser component allowing users to log into their Bethesda account to scan their full Creation library (purchased but not installed). That feature will be a separate module/tab and is explicitly out of scope here, but the data model should not preclude it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Manual Drag-and-Drop Reordering (Priority: P1)

A user opens the Load Order tab and wants to change the load order. They drag a creation to a new position. The list enters a "dirty" state — moved items are visually highlighted but Plugins.txt is **not** written yet. The user must explicitly click "Apply" to save. This prevents accidental one-action changes from ruining a working order. If Starfield is running, the user can still drag to rearrange, but the "Apply" button is disabled until the game is closed.

**Why this priority**: Manual reordering is the foundation — all other sorting features produce a proposed order that the user can then fine-tune manually. The dirty-state pattern provides a safety net against accidental changes.

**Independent Test**: Open the tool with 5+ creations, drag one from position 4 to position 2, verify the item is highlighted as moved and Plugins.txt is unchanged. Click Apply, verify Plugins.txt now reflects the new order.

**Acceptance Scenarios**:

1. **Given** a list of 5 creations in load order, **When** the user drags creation #4 to position #2, **Then** the list updates visually, the moved item is highlighted, and the list enters a dirty state. Plugins.txt is **not** written.
2. **Given** the list is in a dirty state, **When** the user clicks "Apply", **Then** the new order is written to Plugins.txt and the dirty state is cleared.
3. **Given** the list is in a dirty state, **When** the user clicks "Discard", **Then** the list reverts to the last saved order and the dirty state is cleared.
4. **Given** Starfield is running, **When** the user drags items to rearrange, **Then** the list enters dirty state normally but the "Apply" button is disabled with a message that the game must be closed first.
5. *(Removed — system/DLC master files are filtered out by the parser; Bethesda marketplace creations sort by category like any other.)*

---

### User Story 2 — Automated Sorting with Priority-Based Sorter Pipeline (Priority: P2)

A single "Auto Sort" button triggers a sorting pipeline that combines multiple sorters in priority order. Each sorter proposes a position for each creation; when sorters disagree, the highest-priority sorter wins. The user configures which sorters are active via a settings panel. The result is presented in the diff view for review.

**Sorter priority (highest wins)**:
1. **LOOT masterlist rules** (highest) — curated community data, parsed from LOOT's public YAML. Available when the masterlist is bundled or fetched.
2. **Category-based sorting** (lowest) — maps Bethesda API categories to the 11-tier community system. Always available as a baseline.

A future feature will add user-defined custom rules as the highest-priority sorter, above LOOT.

**Why this priority**: A unified pipeline avoids confusing users with multiple sort buttons and ensures consistent conflict resolution. LOOT's curated data takes precedence over auto-guessed categories, which is the correct default.

**Independent Test**: With both sorters enabled, click "Auto Sort" on a list where LOOT and category sorting disagree on a creation's position. Verify the LOOT position wins. Disable LOOT, re-sort, verify category sorting is used.

**Acceptance Scenarios**:

1. **Given** both sorters are enabled, **When** the user clicks "Auto Sort", **Then** the pipeline runs all active sorters and the highest-priority decision wins for each creation. The result appears in the diff view.
2. **Given** LOOT rules place creation X at position 3 but category sorting places it at position 7, **Then** position 3 is proposed (LOOT wins).
3. **Given** LOOT has no opinion on creation Y but category sorting places it at position 5, **Then** position 5 is proposed (category fallback).
4. **Given** the user disables LOOT sorting in settings, **When** the user clicks "Auto Sort", **Then** only category-based sorting is used.
5. **Given** the LOOT masterlist is unavailable, **Then** the LOOT sorter is automatically disabled and category sorting is used as the sole sorter.
6. **Given** the LOOT masterlist contains warnings for specific plugins, **Then** those warnings are shown alongside the affected creations in the diff view.

---

### User Story 3 — Diff View for Proposed Changes (Priority: P1)

Before any automated sort is applied, the user sees a conflict-resolution-style side-by-side view (similar to git merge UIs). The left side shows the current active order, the right side shows the proposed order. Creations that would move are highlighted with visual indicators (arrows or connecting lines) showing where each item moves. Each moved item also shows a **sorter attribution label** (e.g., "LOOT", "CAT") near the movement indicator or the per-creation controls, so the user knows which sorter decided the move. The user has granular control: an "Apply All" button to accept the entire proposal, plus per-creation controls — "Apply" (accept this move) and "Ignore" (keep current position) — for each creation that changed position. Unmoved creations appear without controls. After the user has selectively applied/ignored changes, a "Done" button finalizes the result and writes to disk.

**Why this priority**: This is a safety mechanism that prevents automated sorting from silently breaking a working load order. Per-creation granularity lets users cherry-pick the moves they trust while keeping items they've manually positioned. Same philosophy as reviewing a pull request — but with line-level accept/reject.

**Independent Test**: Trigger any auto sort, verify the diff view shows both orders side-by-side with movement indicators, use per-creation Apply/Ignore on individual items, verify only applied moves are written.

**Acceptance Scenarios**:

1. **Given** the current order and a proposed order differ, **When** the diff view opens, **Then** both orders are shown side-by-side with moved items highlighted and visual indicators (arrows/lines) showing movement.
2. **Given** a creation moved from position 5 to position 2 by the LOOT sorter, **Then** it shows a visual indicator of the movement, a "LOOT" attribution label, and per-creation "Apply" / "Ignore" controls.
3. **Given** some creations didn't move, **Then** they appear unhighlighted without per-creation controls.
4. **Given** the user clicks "Apply All", **Then** all proposed moves are accepted.
5. **Given** the user clicks "Apply" on creation X and "Ignore" on creation Y, **Then** only creation X moves to its proposed position; creation Y stays in its current position.
6. **Given** the user clicks "Done" after selective apply/ignore, **Then** the accepted changes enter the dirty state in the main list, ready to be saved via "Apply".
7. **Given** the user clicks "Cancel", **Then** the diff view closes and no changes are made.

---

### User Story 4 — Snapshot Export and Import (Priority: P3)

A user can save the current load order as a named snapshot (exported to a file). They can later import a snapshot to restore that exact order. This serves as both a backup mechanism and a way to switch between configurations (e.g., "achievement-friendly order" vs "full mod order").

**Why this priority**: Snapshots provide a safety net for experimentation. Users can save a known-good order before making changes, and restore it if things break.

**Independent Test**: Save current order as a snapshot, change the order, import the snapshot, verify the order is restored.

**Acceptance Scenarios**:

1. **Given** a load order is displayed, **When** the user clicks "Save Snapshot", **Then** a file dialog appears and the current order is saved to a file.
2. **Given** a snapshot file exists, **When** the user clicks "Load Snapshot", **Then** the snapshot order is shown in the diff view (not applied immediately).
3. **Given** a snapshot references creations that are no longer installed, **Then** those entries are skipped and a message indicates which creations were not found.
4. **Given** a snapshot is applied, **Then** the order is written to Plugins.txt and the display updates.

---

### Edge Cases

- What happens when creations in a snapshot are no longer installed? They are skipped, and the remaining creations are ordered as specified.
- What happens when new creations exist that weren't in the snapshot? They are appended at the end in their current relative order.
- What happens if Plugins.txt is locked or read-only? The tool shows an error message and does not attempt to write.
- What happens if the user has no creations installed? The reordering UI is hidden and a message indicates there's nothing to sort.
- What happens when the LOOT masterlist is unavailable? The button is disabled; category-based and manual sorting remain available.
- What happens if the game is running when changes are made? The user can still drag to rearrange (dirty state), but the "Apply" button is disabled until Starfield is closed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to reorder creations via drag-and-drop in the list view.
- **FR-002**: System MUST NOT write to Plugins.txt on drag/move. Changes put the list into a dirty state (highlighted items). Writing occurs only when the user explicitly clicks "Apply".
- **FR-002a**: System MUST provide a "Discard" action to revert the list to the last saved order when in dirty state.
- **FR-003**: *(Removed — the community tier-1 rule applies to system/DLC master files which are filtered out by the parser, not to Bethesda marketplace creations. Ordinary BGS creations sort by content category like any other creation.)*
- **FR-004**: System MUST provide a single "Auto Sort" button that triggers a priority-based sorter pipeline. When sorters disagree on a creation's position, the highest-priority sorter's decision wins.
- **FR-004a**: System MUST include a category-based sorter (lowest priority) that maps Bethesda API categories to the community's 11-tier system.
- **FR-004b**: System MUST include a LOOT masterlist sorter (higher priority) that parses LOOT's publicly available Starfield masterlist YAML for plugin groups and load-after rules.
- **FR-004c**: The build process MUST download the latest LOOT masterlist and bundle it with the application binary.
- **FR-004d**: On startup, the system MUST attempt to fetch a newer masterlist from GitHub in the background. If the fetch fails, the bundled or previously cached copy is used silently.
- **FR-004e**: When LOOT sorting is unavailable (no masterlist found), the system MUST show a warning dialog explaining that sorting is category-only and LOOT data will be retried on next startup.
- **FR-005**: System MUST allow users to enable/disable individual sorters via a settings panel. Category sorting is always available; LOOT sorting requires the masterlist to be available.
- **FR-006**: System MUST fall back gracefully when a higher-priority sorter has no opinion on a creation — the next available sorter's decision is used.
- **FR-007**: System MUST show a conflict-resolution-style side-by-side diff view before applying any automated sort, with current order on the left and proposed order on the right.
- **FR-008**: System MUST visually indicate which creations moved using arrows or connecting lines between the two columns, and display a sorter attribution label (e.g., "LOOT", "CAT") on each moved item identifying which sorter decided its position.
- **FR-009**: System MUST provide an "Apply All" button to accept all proposed moves at once.
- **FR-009a**: System MUST provide per-creation "Apply" and "Ignore" controls for each creation that changed position, allowing selective acceptance.
- **FR-009b**: When the user clicks "Done" in the diff view, the accepted changes enter the dirty state in the main list. The user then clicks "Apply" to write to Plugins.txt, or "Discard" to revert. "Cancel" closes the diff view with no changes.
- **FR-010**: System MUST allow users to export the current load order as a named snapshot file.
- **FR-011**: System MUST allow users to import a snapshot file and preview it in the diff view before applying.
- **FR-012**: System MUST handle snapshot files that reference creations no longer installed by skipping those entries and reporting which were skipped.
- **FR-013**: System MUST handle snapshot files that don't include newly installed creations by appending them at the end.
- **FR-014**: System MUST show an error if Plugins.txt cannot be written (permissions, file locked).
- **FR-015**: System MUST detect if Starfield is running and disable the "Apply" button (blocking writes to Plugins.txt) while allowing drag-and-drop rearrangement in dirty state. A message explains that the game must be closed to apply changes.
- **FR-016**: System MUST group multi-file creations (e.g., Trackers Alliance with 6 ESMs) into a single row in the load order view. The Plugin column shows the first file and a count (e.g., "SFTA01.esm, and 5 more"). All files move as a pack during drag, sort, and snapshot operations.
- **FR-017**: *(Removed — the tier-1 rule applies to system/DLC master files which are filtered out by the parser. Bethesda-authored marketplace creations sort by their content categories like any other creation.)*

### Key Entities

- **LoadOrder**: An ordered list of creation identifiers representing the current or proposed plugin load sequence. Each entry maps to a line in Plugins.txt.
- **SortTier**: A classification level following the community's 11-category system (Master Files, Framework, Invasive World Edits, Workshop, Gameplay Changes, Companions, Audio/Visual, HUD/UI, Ship Additions, Wearables, Non-Invasive World Edits) with subcategories for finer ordering within each tier.
- **Snapshot**: A saved load order with a name and timestamp, exportable to and importable from a file.
- **Sorter**: A pluggable sorting strategy with a priority level. Multiple sorters are evaluated in priority order; the highest-priority sorter with an opinion on a given creation determines its position. Current sorters: category-based (lowest), LOOT masterlist (higher). Future: user-defined custom rules (highest).
- **DiffView**: A conflict-resolution-style side-by-side comparison of two load orders, with movement indicators (arrows/lines) and per-creation Apply/Ignore controls for selective acceptance.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can reorder any creation in under 3 seconds via drag-and-drop.
- **SC-002**: Category-based auto sort produces a valid tiered order for any combination of installed creations in under 2 seconds.
- **SC-003**: The diff view clearly shows all position changes, with 100% of moved items visually distinguished from unmoved items.
- **SC-004**: Snapshot export and import completes in under 2 seconds for lists of 50+ creations.
- **SC-005**: No automated sort is ever applied without explicit user approval through the diff view.
- **SC-006**: LOOT-based sorting produces a valid proposed order from the masterlist YAML without requiring LOOT to be installed.

## Clarifications

### Session 2026-03-30

- Q: Where does this feature live in the UI? → A: The existing "Load Order" tab (separate from "Installed Creations"). Same creation list display, segmented to avoid toolbar clutter.
- Q: How does the diff view work — bulk apply or granular? → A: Conflict-resolution style (like git merge): per-creation Apply/Ignore controls plus Apply All. User-defined override rules are a future feature, out of scope for now.
- Q: How are API categories mapped to sort tiers? → A: API categories map to the 11-tier system, unmatched go to Default. System/DLC master files (SFBGS-prefixed) are filtered out by the parser and never appear in the creation list. Bethesda marketplace creations sort by their content categories like any other creation.
- Q: How should LOOT integration work? → A: Parse LOOT's masterlist YAML files directly (publicly available on GitHub) and apply the sorting rules ourselves. No subprocess invocation or C++ library linking — just YAML parsing.
- Q: Should manual drag immediately write to Plugins.txt? → A: No. Dragging enters a dirty state (moved items highlighted). User must click "Apply" to save. Dragging is allowed while Starfield is running, but "Apply" is disabled until the game is closed.
- Q: How do LOOT and category sorting interact? → A: Unified "Auto Sort" button with a priority-based sorter pipeline. LOOT (curated) wins over category-based (auto-guessed) when they disagree. User can enable/disable sorters. Future: custom rules at highest priority.
- Q: Should the diff view show which sorter decided each move? → A: Yes. Each moved item displays a sorter attribution label (e.g., "LOOT", "CAT") near the movement indicator or per-creation controls.
- Q: How is the LOOT masterlist managed? → A: Bundled at build time, auto-fetched on startup (cached for 24h), warning dialog if unavailable.
- Q: How are multi-file creations handled? → A: Grouped into a single row, sorted as a pack. Plugin column shows first file + count.
- Q: Are Bethesda-authored TM_ creations treated as official? → A: No — the tier-1 rule applies only to system/DLC master files (filtered out by the parser). Bethesda marketplace creations (including TM_ UUIDs) sort by their content categories like any other creation.

## Assumptions

- The tool modifies Plugins.txt only (not ContentCatalog.txt) for load order changes, as Plugins.txt is the authoritative load order file for Starfield.
- Category information for sorting comes from the Bethesda Creations API (already fetched by the existing `bethesda_creations` package).
- LOOT integration parses the masterlist YAML directly (no LOOT installation required). The masterlist is either bundled with the app or fetched from LOOT's public GitHub repository.
- Snapshot files use a simple, human-readable format (implementation detail — not prescribed).
- The diff view is a modal dialog that blocks other interactions until the user approves or cancels.
- The category-based tier ordering follows community best practices documented in modding guides (Bethesda official first, overhauls before specific content, cosmetics last).
- User-defined custom sorting rules (highest priority in the sorter pipeline, above LOOT) are a future enhancement, out of scope for v1. The pipeline architecture should accommodate adding them later.
- Bethesda library scanning (login + browse uninstalled creations) is a separate future feature/module and out of scope here.
