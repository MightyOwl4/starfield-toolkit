# Research: Diff Dialog Visual Connectors and Hint Dialog

**Date**: 2026-04-12 | **Branch**: `010-diff-connectors`

## Decision 1: Drawing technology — `tk.Canvas`

**Decision**: Use a native `tk.Canvas` widget placed in a fixed-width middle grid column between the two `ttk.Treeview` panels.

**Rationale**:
- `tkinter.Canvas.create_line(..., smooth=True, splinesteps=N)` natively renders Bezier-smoothed curves with no external dependency.
- `create_oval(x-r, y-r, x+r, y+r, fill=color, outline="")` gives the small endpoint dots.
- The existing dialog already mixes `ttk` widgets inside a `ctk.CTkFrame`; adding a raw `tk.Canvas` beside them is consistent and requires no wrapper.
- Constitution I (Simplicity First) and III (Minimal Dependencies) — no new libraries.

**Alternatives considered**:
- HTML/tkhtmlview: rejected — heavy, new dependency, doesn't integrate with live tree bbox queries.
- Stacked `tk.Frame` bands (as `app.py:28-40`): rejected — works for static stripes but cannot draw curves or respond to row position.
- Pillow/PIL raster draw onto a label: rejected — blurs at DPI changes; reinvents canvas event handling.

## Decision 2: Getting row Y coordinates — `Treeview.bbox(item_id)`

**Decision**: Use `self._left_tree.bbox(iid)` and `self._right_tree.bbox(iid)` to get the viewport-relative row rectangle, convert to canvas-relative coordinates via `winfo_y()` offsets.

**Rationale**:
- `bbox()` returns `()` when the row is not visible — natural way to skip drawing off-screen connectors.
- The left tree, canvas, and right tree share the same parent grid row, so `winfo_y()` on each is measured against the same parent; conversion is `y_canvas = bbox[1] + bbox[3]//2 + (tree.winfo_y() - canvas.winfo_y())`.

**Alternatives considered**:
- Iterating all children and multiplying by row height: rejected — fragile under different font scales, doesn't handle scrolling.
- Computing positions from model indices: rejected — ignores the rendered viewport; connector endpoints would detach from visible rows.

## Decision 3: Linked scrolling between the two trees

**Decision**: Wire both trees to a single shared `ttk.Scrollbar`. Both `Treeview.yscrollcommand` call a wrapper that updates the scrollbar *and* triggers `_redraw_connectors()`. The scrollbar's `command` is set to a wrapper that calls `yview_moveto` on both trees.

**Rationale**:
- Makes connector endpoints always mutually visible or mutually invisible — no half-drawn lines.
- Drastically simplifies the "which connectors are visible now?" logic.
- Mouse wheel bindings on either tree continue to work per ttk defaults; the shared `yscrollcommand` handles position sync.

**Alternatives considered**:
- Independent scrollbars with bidirectional event re-dispatch: rejected — more events, timing edge cases, fragile.
- No link, redraw aggressively: rejected — creates visual anomalies when one tree scrolls but the other doesn't.

## Decision 4: Color palette

**Decision**: A fixed 6-color palette cycled by index:
```python
_MOVE_COLORS = ["#4a9eff", "#48c774", "#f39c12", "#e55353", "#9c6ad6", "#1abc9c"]
```
Assigned by proposed-order position of the moved item (stable deterministic ordering).

**Rationale**:
- Six hues, well-separated in hue space, legible on dark and light themes.
- Deterministic ordering means the same sort produces the same color assignment every time.
- Matches existing project tone (similar accent hues already in use for tag coloring).

**Alternatives considered**:
- HSV wheel with N-tuple distribution: rejected — overengineered for ≤20 items, produces muddy pastels.
- Color by winning sorter (TES4=red, etc.): rejected by user — not helpful for visual tracing when multiple moves share a sorter.

## Decision 5: Hint icon click detection

**Decision**: In `_on_right_click`, use `self._right_tree.identify_column(event.x)` to detect a click on column `"#3"` (Info). If the row is moved and the click landed on that column, open `_show_hint_dialog(plugin_name)`. Otherwise fall through to the existing accept/reject toggle.

**Rationale**:
- Clean separation of the click regions without overlay widgets.
- The ⓘ character is the first character of the Info text; visually implies it's the clickable target, but the entire column is a generous click target (users with small displays benefit).
- Reuses existing event binding — no new `<Button-*>` sequences.

**Alternatives considered**:
- Overlay a button via `place()` over the ⓘ character: rejected — positioning is fragile under scroll, and tree column clicks would pass through in unexpected ways.
- Right-click context menu: rejected — less discoverable; user explicitly wanted an icon.

## Decision 6: Constraint retention for hint dialog — `SortDecision.all_constraints`

**Decision**: Add `all_constraints: list[SortConstraint] = field(default_factory=list)` to `SortDecision`. Populate it in `_merge_constraints` (`pipeline.py`) with `decision.all_constraints = list(plugin_constraints)` before returning.

**Rationale**:
- Minimal data-flow change: constraints are already grouped per plugin in `_merge_constraints`; we just retain the list.
- No behavioral change for existing consumers (tier winner and `load_after_sorters` are still set).
- Enables the hints dialog to render winners and losers together without running sorters twice.

**Alternatives considered**:
- Re-run sorters on demand from the hints dialog: rejected — re-reads masterlists and rulebooks, not worth the complexity.
- Store constraints globally on `SortResult`: rejected — less local, harder to look up per plugin in the dialog.

## Decision 7: Rulebook source attribution via `sorter_name`

**Decision**: Change `sorters/rulebook.py` to set `sorter_name=f"RULE:{entry['filename']}"` for every constraint it emits, replacing the previous `"RULE"` (and the `f"RULE({tier})"` used in tier constraints — which becomes `f"RULE:{filename}({tier})"` to preserve tier visibility).

**Rationale**:
- Minimal schema change: uses an existing string field via convention.
- Existing UI that displays `sorter_name` (e.g., `load_order.py` Info column) transparently shows the filename — helpful everywhere, not just in the hints dialog.
- No new field means no migration concerns.

**Alternatives considered**:
- New `source_file` field on `SortConstraint`: rejected — two fields to maintain, no consumer needs it separately, and the display concatenation is trivial.
- Path relative to project: rejected — filename alone is unambiguous within the rules folder.

## Decision 8: Note propagation via `SortConstraint.note`

**Decision**: Add `note: str = ""` to `SortConstraint`. The rulebook sorter populates it from `rule.get("note", "")` for both order and tier rule types. Other sorters leave it empty.

**Rationale**:
- Generic enough for future LOOT `msg` text propagation without rework.
- Empty default means no migration needed.
- The hints dialog simply skips the note line when empty.

**Alternatives considered**:
- Warnings list overload: rejected — notes are explanatory text (often long), not warnings; mixing them confuses semantics.
- Store notes in a separate `dict[str, str]` on `SortDecision`: rejected — loses the link between a specific constraint and its note when multiple constraints come from the same sorter.

## Decision 9: Winner badge logic in the hints dialog

**Decision**: A constraint displays a WINNER badge when:
- It is a `tier` constraint AND its `sorter_name` equals `decision.sorter_name` (the stored tier winner), OR
- It is a `load_after` constraint AND `decision.load_after_sorters.get(c.after) == c.sorter_name` (the attributed winner for that edge).

Multiple badges per plugin are permitted (one tier winner + one per load_after edge).

**Rationale**:
- Uses data already computed in `_merge_constraints` without re-implementing priority resolution.
- Correctly shows "this sorter won this specific concern" semantics.
- Matches user's explicit requirement ("highlight more than one winner — CAT, TES4, Rulebooks").

**Alternatives considered**:
- Badge only the highest-priority constraint: rejected — incorrect; load_after edges are resolved independently from tier.
- Badge every constraint that "would win if others didn't exist": rejected — over-counts; misleading.

## Decision 10: Scope of UI change — diff dialog only

**Decision**: All visual changes are localized to `load_order_diff.py`. The main load order grid (`load_order.py`) does not gain any connectors or hint icons.

**Rationale**:
- The diff dialog is where the sort result is *reviewed* — the natural place for explanation.
- The main grid shows the live load order; explanations belong to the review step.
- Minimizes surface area of change; reduces regression risk.

**Alternatives considered**:
- Also add hint icons to the main grid's dirty rows: rejected — adds complexity for little value (the same info is one click away in the diff dialog).
