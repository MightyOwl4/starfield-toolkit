# Feature Specification: Diff Dialog Visual Connectors and Hint Dialog

**Feature Branch**: `010-diff-connectors`
**Created**: 2026-04-12
**Status**: Draft
**Input**: User description: "Diff dialog visual enhancements: add colored Bezier curve connectors in the gap between the left (Current Order) and right (Proposed Order) treeviews of the load order diff dialog, one per moved item. Each connector has small colored dots at the endpoints and no arrowheads. Each moved row in the right tree gets a colored eye icon (ⓘ) prefix in the Info column; clicking the icon opens a hints dialog listing every SortConstraint that influenced the move in priority order, with winner highlighting for the tier winner AND each load_after edge winner, and showing the source rulebook filename for RULE constraints plus the rule's note. Row click continues to toggle accept/reject. Per-move color cycled from a small palette is shared between the connector, its endpoint dots, and the eye icon. Connector drawing uses a tk.Canvas placed in a fixed ~80px middle column; trees scroll in lockstep via a shared scrollbar; connectors redraw on scroll, resize, collapse-toggle, and accept-toggle. Requires architectural changes to preserve losing constraints: SortDecision.all_constraints is new, SortConstraint gets a note field, and rulebook SortConstraints carry sorter_name='RULE:{filename}' to identify their source book."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visual connectors show where each moved item came from and went to (Priority: P1)

When a user runs Auto-Sort and the diff dialog opens, they can immediately see which items moved by following colored curved lines drawn in the gap between the Current Order and Proposed Order panels. Each truly-moved item has one connector line in a unique color; the same color appears on small dots at the line's two endpoints (next to the item's old row on the left and new row on the right) and on the row's hint icon. Items that did not truly move (positional shifts only) have no connector, consistent with the existing minimal-diff presentation.

**Why this priority**: This is the headline visual change. Users want to see *at a glance* where things moved. Without it, the feature is just a refactor with no perceived benefit.

**Independent Test**: Open the diff dialog with a sort result containing at least two moves that cross each other in position (e.g., item at #5 moves to #20, item at #36 moves to #20's neighbour). Verify that two distinct-colored curves appear, dots match at both ends, and tracing each curve end-to-end identifies the correct row pair.

**Acceptance Scenarios**:

1. **Given** the diff dialog opens with two moved items, **When** the user views the gap between the two panels, **Then** two colored curved lines are drawn, each with a small filled dot at the left and right endpoints, with no arrowheads.
2. **Given** two moves that cross each other's vertical span, **When** the user traces each curve by eye, **Then** the distinct colors at the endpoints and on the lines make it obvious which origin row pairs with which destination row.
3. **Given** the diff dialog displays a set of moved items, **When** the user scrolls either panel, **Then** both panels scroll together and connector curves remain aligned with the actual row positions of the items they represent.
4. **Given** the user resizes the dialog window, **When** the resize completes, **Then** connectors are redrawn with endpoints still aligned to their rows.
5. **Given** the user toggles the "Collapse unchanged" switch, **When** rows reflow, **Then** connectors redraw with endpoints at the new visible row positions.

---

### User Story 2 - Hint icon reveals every rule that shaped a move (Priority: P1)

Each moved row in the right panel shows a small colored hint icon (ⓘ) prefixed to its Info column text. Clicking the icon opens a dialog titled "Hints for {plugin name}" that lists every ordering or tier constraint that touched this plugin — not just the winning one — sorted with highest-priority first. For each constraint the user sees the sorter that produced it (e.g., `CAT(3)`, `TES4`, `LOOT`, `RULE:001_patch_description_parsing_high.json`), the constraint type and value (`tier 3` or `load_after PlaceDoorsYourself.esm`), the numeric priority, a winner badge if this constraint actually prevailed for its concern, and any rule note from the originating rulebook. The dialog shows *multiple* winner badges when multiple concerns exist: one for the tier assignment and one per accepted `load_after` edge.

**Why this priority**: Without this, the user cannot answer "why did this move happen?" The visual connector tells them *that* something moved; the hint dialog tells them *why*. Without the why, curated rulebooks feel opaque.

**Independent Test**: Open the diff dialog for a sort where one moved item was constrained by at least two sorters with different tiers and at least one `load_after` rule. Click its hint icon. Verify the dialog lists all constraints including the loser(s), the priorities, and the winner badges in the right places.

**Acceptance Scenarios**:

1. **Given** a moved item has two tier constraints (one from CAT, one from a curated rulebook), **When** the user clicks the hint icon, **Then** both constraints are listed with priorities and only the higher-priority one shows the "WINNER" badge for tier.
2. **Given** a moved item has a `load_after` constraint from a rulebook, **When** the user opens its hint dialog, **Then** the source rulebook filename is shown inline with the sorter label (e.g., `RULE:000_tier_corrections.json`), and the rule's `note` text is shown in a subordinate greyed style.
3. **Given** a plugin has both a tier winner and an independent load_after winner (different sorters), **When** the user views the hint dialog, **Then** both entries carry a "WINNER" badge because they won for different concerns.
4. **Given** the user closes the hint dialog, **When** they return to the diff dialog, **Then** the diff dialog's state (accepted/rejected rows, scroll position, connectors) is unchanged.
5. **Given** the user clicks on the row body (not the hint icon) in the right panel, **When** the click is processed, **Then** the accept/reject state toggles as before and the hint dialog does NOT open.

---

### User Story 3 - Per-move color coding ties everything together (Priority: P2)

The color assigned to each move is consistent across the connector line, the dots at its endpoints, and the hint icon in the Info column of the right panel. Colors cycle through a small palette so any given diff rarely reuses a color within the visible set, making visual tracing unambiguous even when lines cross.

**Why this priority**: Color tying is what makes the crossings readable. Without it, two curves that cross look indistinguishable and the user has to count rows.

**Independent Test**: Open the diff dialog with two moves; note the color of the connector. Verify the two endpoint dots share that exact color, and the hint icon in the Info column on the right panel has the same color.

**Acceptance Scenarios**:

1. **Given** three moved items, **When** the user compares any connector line to its two endpoint dots and the right-side hint icon, **Then** all four elements share the same color.
2. **Given** more moved items than palette entries, **When** the colors cycle, **Then** no two items with overlapping visible positions share the same color (best-effort via ordering).

---

### Edge Cases

- A moved item is scrolled out of view on one panel but visible on the other → the connector is not drawn for that frame (both endpoints must be visible); it reappears when the item scrolls back into view.
- A sort produces many moves (20+) → connectors remain readable; if crossings stack into an unusable tangle at a given scroll position, the color coding + hint icons still let the user resolve identity per item.
- The user toggles "Collapse unchanged" with moves still at their non-collapsed positions → connectors redraw against the new visible row geometry.
- A plugin has zero constraints (unchanged item) → no hint icon and no connector; it should not appear in the moved set at all.
- A rulebook contains a rule for a plugin but no `note` → the hint dialog omits the subordinate note line gracefully (no empty "note:" label).
- A corrupted or disabled rulebook → that rulebook contributes no constraints, so it does not appear in any hint dialog. Consistent with existing sort behavior.
- The dialog is resized to be very narrow, squeezing the middle canvas → the canvas retains its fixed width and the trees shrink around it; if the window is narrower than the minimum, the dialog enforces its minimum size as it already does.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The diff dialog MUST draw a visual connector between each truly-moved item's current-order row and its proposed-order row, in the gap between the two panels.
- **FR-002**: Connectors MUST be curved (smooth, non-straight) and MUST NOT include arrowheads; direction is implied by left=current, right=proposed.
- **FR-003**: Each connector MUST have a small filled dot at each endpoint, aligned to the vertical center of its corresponding row.
- **FR-004**: The system MUST assign a color per moved item from a small fixed palette, cycled deterministically, and use the same color for the connector line, its two endpoint dots, and the hint icon in the right panel Info column for that item.
- **FR-005**: The system MUST show a small hint icon (ⓘ or visually equivalent) as a prefix to the Info column text on every moved row in the proposed-order panel.
- **FR-006**: Clicking the hint icon MUST open a hints dialog for that plugin; clicking elsewhere on the row MUST continue to toggle accept/reject state.
- **FR-007**: The hints dialog MUST list every sort constraint that affected the plugin, including losers, sorted by priority descending with stable secondary sort.
- **FR-008**: Each hint entry MUST display: the sorter name, the constraint type and value, the priority number, and a winner badge when applicable.
- **FR-009**: For rulebook-sourced hints, the sorter name MUST include the originating rulebook filename (e.g., `RULE:000_tier_corrections.json`).
- **FR-010**: Each rulebook-sourced hint MUST show the rule's `note` text in a visually subordinate (greyed) treatment when a note is present; when absent, the note line MUST be omitted.
- **FR-011**: Winner badges MUST be applied independently per concern: the single tier winner gets a badge; each `load_after` edge's attributed winner gets its own badge. Multiple winner badges per plugin are permitted.
- **FR-012**: The two panels MUST scroll in lockstep so that connector endpoints remain meaningful.
- **FR-013**: Connectors MUST redraw accurately in response to: scrolling, window resize, toggle of the "Collapse unchanged" switch, accept/reject state changes, and the dialog opening.
- **FR-014**: The system MUST preserve all constraints (winners and losers) in the sort decision record, so that the hints dialog has access to them. Current behavior of only surfacing the winner in the main load order view is unchanged.
- **FR-015**: The system MUST attach the rule's `note` to the constraint object so it flows through to the hints dialog.
- **FR-016**: The visual enhancements MUST NOT alter the semantics of Auto-Sort, accept/reject, or the final accepted order. All changes are presentational or additive.

### Key Entities

- **Move**: A truly-moved plugin between the current and proposed orderings (already identified by the existing minimal-diff logic). Gains an assigned color for this session.
- **Hint (SortConstraint)**: A single constraint produced by a sorter. Gains a `note` field carrying the rule's explanatory text when sourced from a rulebook. Rulebook-sourced hints gain filename-qualified sorter identifiers.
- **Sort Decision (SortDecision)**: The merged outcome for a plugin. Gains a complete list of every constraint that contributed (not just the winners) so the hints dialog can render the full picture.
- **Connector**: A visual element drawn in the gap between panels, bound to a single Move. Composed of one curved line and two endpoint dots, all sharing the move's assigned color.
- **Hint Icon**: A small colored ⓘ prefix in the right panel's Info column for a moved row, clickable to open the hints dialog for that plugin.
- **Hints Dialog**: A transient window listing all constraints for a single moved plugin, with winner badges and rulebook attribution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user viewing the diff dialog for any Auto-Sort result can identify, without scrolling or clicking, which items moved and where they moved to, in under 5 seconds.
- **SC-002**: For any moved item, a user can determine every rule that influenced its position — including losing rules — within 3 clicks (open diff, click hint icon, read dialog).
- **SC-003**: When a move was caused by a curated rulebook, the user can identify which specific rulebook file caused it without leaving the diff dialog.
- **SC-004**: With up to 10 moved items, the visual connector display remains legible: each line can be traced to its correct endpoint pair without counting rows, and each hint icon's color matches its connector.
- **SC-005**: Row-level accept/reject behavior remains unchanged for users who ignore the new visual features; existing test coverage continues to pass.
- **SC-006**: No regression in sort correctness: the same Auto-Sort inputs produce the same final accepted order before and after this change.

## Assumptions

- Users typically see between 0 and ~20 moved items per Auto-Sort run; higher counts are out of scope for visual tuning.
- The existing minimal-diff logic (`SequenceMatcher`-based) correctly identifies which items truly moved; this feature builds on that, not replaces it.
- The palette used for move colors is chosen once and is fixed; user customization of the palette is out of scope for v1.
- Users do not need a way to export the hints dialog content; it is view-only.
- The hints dialog is dismissed by explicit user action (close button or window close); it is not modal-blocking beyond the diff dialog itself.
- Screen DPI scaling at 100%–150% is supported; extreme DPI scaling may require manual sizing adjustments out of scope for v1.
- The diff dialog continues to be used only for reviewing Auto-Sort results; the main load order grid is unaffected.
