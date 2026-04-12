# Quickstart: Diff Dialog Visual Connectors and Hint Dialog

**Date**: 2026-04-12 | **Branch**: `010-diff-connectors`

## What this feature adds

- Colored Bezier curve connectors between moved items in the Review Proposed Load Order dialog.
- A clickable ⓘ hint icon next to each moved row's Info text on the right panel.
- A hints dialog that lists every constraint that influenced the move, with winner badges and rulebook filenames.
- All presentational/additive — Auto-Sort semantics unchanged.

## How to exercise it

### 1. Automated tests (stdlib, no Tk)
```bash
.venv/Scripts/python.exe -m pytest tests/ -x -q
.venv/Scripts/python.exe -m ruff check .
```
Expected: all pass. New tests added for `all_constraints` preservation, `sorter_name` filename qualification, and `note` propagation.

### 2. Manual UI walkthrough (the Falkland/PDY scenario)
1. Launch the app from `src/` (entry point per project README).
2. Open the **Load Order** tab.
3. Click **Auto-Sort**.
4. In the **Review Proposed Load Order** dialog:
   - **P1 connectors (US1)**: See two colored Bezier curves between the panels — one for PDY (#36 → #20), one for Falkland (#5 → #21). They cross cleanly. Small colored dots sit next to each row.
   - **P1 hint icon (US2)**: Each moved row on the right panel shows a colored ⓘ before its existing Info text. The icon's color matches the connector dots.
   - **P2 color coding (US3)**: Trace any connector — line, both dots, and right-panel icon share the same color.

### 3. Click the ⓘ for PDY
Expected dialog content:
- Header: "Hints for Place Doors Yourself" with a color swatch matching the connector.
- Body rows (priority desc):
  - `RULE:000_tier_corrections.json(3)` | `tier 3` | p=30 | **WINNER** | note="PDY rewrites all HAB records..."
  - `CAT(5)` | `tier 5` | p=10 | (no badge — loser for tier)

### 4. Click the ⓘ for Falkland
Expected dialog content:
- Header: "Hints for Falkland Systems Ship Services" with matching swatch.
- Body rows (priority desc):
  - `RULE:001_patch_description_parsing_high.json` | `load_after PlaceDoorsYourself.esm` | p=30 | **WINNER (this edge)** | note="...source string..."
  - `CAT(3)` | `tier 3` | p=10 | **WINNER (tier)**

**Two winner badges for the same plugin** — correct per FR-011.

### 5. Scroll both panels
- Scroll either panel with the mouse wheel: both panels move in lockstep.
- Connectors redraw, endpoints stay aligned to the correct rows.

### 6. Resize the window
- Drag the window edge: canvas stays at ~80px, trees shrink, connectors redraw.

### 7. Toggle "Collapse unchanged"
- Flip the switch: rows reflow; connectors redraw against the new geometry.

### 8. Regression check: row click accept/reject
- Click the row body (not the ⓘ) on PDY: Info column shows the ✓ (accepted), row tint changes to blue, connector remains unchanged.
- Click the ⓘ: hints dialog opens. Dialog close leaves accept state intact.

## Troubleshooting

- **No connectors visible**: the sort produced no moves — try editing the load order first, or verify the rulebooks that should trigger moves are enabled.
- **Connector endpoints detached from rows**: usually a scroll/resize race; redraw happens on `<Configure>` of the canvas. Filing a bug, check `_redraw_connectors` bindings first.
- **ⓘ click toggles accept instead of opening dialog**: ensure the click lands on the Info column; `identify_column(event.x)` must return `"#3"`.
- **Missing rulebook filename in hints**: confirm the sorter is setting `sorter_name="RULE:<filename>"` for both order and tier branches; check tests for this.

## Dev references

- Feature spec: `spec.md`
- Plan: `plan.md`
- Research: `research.md`
- Data model: `data-model.md`
- Task list (generated next): `tasks.md`
