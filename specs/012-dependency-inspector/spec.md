# Feature Specification: Dependency Inspector

**Feature Branch**: `012-dependency-inspector`
**Created**: 2026-04-14
**Status**: Draft
## Clarifications

### Session 2026-04-14

- Q: Scope — does this tab operate only on currently installed creations in load order? → A: Yes, only currently installed creations, shown in load order.
- Q: When a creation is selected, what is the scope of the highlighted dependency graph? → A: Directed transitive closure — ancestors + descendants of the selected creation only; siblings sharing a common dependency are not highlighted.
- Q: How do "hide soft dependencies" / "hide collapsed" toggles affect collapse state and palette color? → A: Freeze at load — collapse state and palette colors are computed once from all known dependencies (hard + soft) at graph build; toggles only change connector and row visibility, never recompute color or collapse.
- Q: Is the inspector read-only or does it expose mutating actions (disable/remove/re-order)? → A: Read-only. Users perform removal/disable via the game menu; this tab only visualises and complements that flow. It replicates the refresh/outdated behaviour of the existing Installed Order tab to stay in sync.
- Q: How is "first" defined for palette-color assignment when a creation has multiple outgoing (or incoming) connections? → A: By load-order position of the other endpoint — earliest target for outgoing, earliest source for incoming. Deterministic and stable across reloads.
- Q: How are dependencies whose target is not currently installed handled? → A: Ignore entirely — no stub connector, no contribution to collapse/color. If a *hard* dependency is missing, display a warning indicator on the dependent creation's row. Missing soft dependencies are silently ignored.

**Input**: User description: "Implement a new tool (separate tab) that shows creations dependencies across the load order. Not clearly communicated in game; hard to tell if removing a given creation will affect others. Show both hard and soft dependencies with option to hide soft ones. Reuse the diff box presentation model with a single centered datagrid, drawing connectors on both sides, splitting them to reduce intersections. Creations with no dependency info start collapsed (regular color) with a toggle to show/hide them. Creations with dependencies use color palette rotation — color matches first outgoing connection (depends on), or first incoming (is dependent by) if no outgoing; outgoing preferred when both exist. Selecting a creation highlights the entire dependency graph above and below (unrelated connectors dimmed, highlighted white with slight glow, same as diff dialog). Tool name: Dependency Inspector."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inspect dependency impact before removing a creation (Priority: P1)

A user who is pruning their creations list wants to know, before disabling or removing a creation, which other creations in the load order depend on it (would break) and which creations it itself relies on (must stay enabled).

**Why this priority**: This is the core value proposition. The in-game interface does not surface cross-creation dependencies, leading to broken load orders after removals. Delivering just this flow already lets users make informed removal decisions.

**Independent Test**: Load a profile with a known set of dependent creations, open the Dependency Inspector tab, select a creation that has both upstream and downstream dependencies, and confirm the connectors and colors accurately reflect the known relationships.

**Acceptance Scenarios**:

1. **Given** a loaded profile with creations that have known hard dependencies, **When** the user opens the Dependency Inspector tab, **Then** the centered datagrid shows all creations in load order and connectors are drawn between dependent pairs.
2. **Given** the datagrid is populated, **When** the user clicks a creation that depends on earlier creations and is depended upon by later ones, **Then** the full dependency chain above and below is highlighted in white with a glow effect while all unrelated connectors dim.
3. **Given** a creation has no known dependency information, **When** the inspector opens, **Then** that creation is rendered collapsed and in the regular (non-palette) color.

---

### User Story 2 - Filter out soft dependencies to focus on hard ones (Priority: P2)

A user reviewing their load order wants to distinguish dependencies that will definitely break functionality (hard) from those that are optional or cosmetic (soft), and be able to hide the soft ones to reduce visual noise.

**Why this priority**: Users can still act on dependency information without the filter, but on large load orders the combined graph becomes visually noisy. Hiding soft dependencies is a strong usability win but not blocking for initial usefulness.

**Independent Test**: Toggle the "hide soft dependencies" control and confirm connectors classified as soft disappear/reappear without affecting hard dependency connectors or the selected creation's highlight state.

**Acceptance Scenarios**:

1. **Given** a creation with both hard and soft outgoing dependencies, **When** the user enables "hide soft dependencies", **Then** only hard connectors remain visible and the creation's color is recomputed from remaining outgoing connections.
2. **Given** soft dependencies are hidden, **When** the user re-enables them, **Then** soft connectors reappear without requiring a reload.

---

### User Story 3 - Hide creations with no dependencies to declutter the view (Priority: P3)

A user scanning a large load order wants to collapse away creations that have no known dependencies so they can focus on the portion of the graph that actually has cross-references.

**Why this priority**: Quality-of-life refinement that becomes important for large load orders but is not required for the tool to deliver value on smaller ones.

**Acceptance Scenarios**:

1. **Given** the default view with collapsed no-dependency creations visible, **When** the user toggles "hide collapsed creations", **Then** only creations that participate in at least one dependency remain in the grid.
2. **Given** collapsed creations are hidden, **When** a selected creation's highlighted chain spans a gap where hidden rows would normally sit, **Then** connectors still render correctly between visible endpoints.

---

### Edge Cases

- A creation is involved in a dependency cycle (A → B → A): the inspector must render without infinite loops and the full cycle must highlight when any participant is selected.
- A dependency references a creation that is not currently installed: the dependency is ignored for connector drawing, color, and collapse purposes. If the missing dep is hard, a warning indicator appears on the dependent row; soft misses are silent.
- All creations have no dependency information: the grid renders entirely collapsed; the "hide collapsed" toggle produces an empty state with a helpful message.
- A creation has many dependencies on the same side (e.g., 20+ incoming): connector routing must remain legible; the inspector may fan connectors or group them, but must never overlap endpoints.
- The user switches profiles or reloads data while a creation is selected: selection state is cleared and the graph re-renders from the new data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST expose a new tab named "Dependency Inspector" alongside the existing tool tabs.
- **FR-002**: The inspector MUST render a single centered datagrid listing all creations in their current load order, reusing the visual conventions of the existing diff box.
- **FR-003**: The inspector MUST draw connectors on both sides of the datagrid between creations that have a dependency relationship, with the earlier (upstream) creation on one vertical side of the connector and the later (downstream) on the other.
- **FR-004**: Connector routing MUST attempt to minimize crossings by distributing connectors between the left and right sides of the grid.
- **FR-005**: The inspector MUST visually distinguish hard dependencies from soft dependencies.
- **FR-006**: Users MUST be able to toggle visibility of soft dependencies via a control in the inspector; the toggle MUST update connector visibility only. Collapse state and palette color assignments are computed once at graph build from the full dependency set (hard + soft) and MUST NOT be recomputed when toggles change.
- **FR-007**: Creations with no known dependencies MUST render in a collapsed state using the regular (non-palette) color by default.
- **FR-008**: Users MUST be able to toggle visibility of collapsed (no-dependency) creations via a control in the inspector.
- **FR-009**: Creations that participate in at least one dependency MUST be assigned a color from a rotating palette; the assigned color MUST match the color of the creation's first outgoing ("depends on") connection. If the creation has no outgoing connections, it MUST match its first incoming ("is depended on by") connection. When both exist, the outgoing color MUST take precedence. "First" is defined deterministically as the connection whose other endpoint has the earliest load-order position (earliest target for outgoing; earliest source for incoming).
- **FR-010**: Users MUST be able to select a creation by clicking its row; selection MUST highlight the creation together with its directed transitive closure — all ancestors (creations it transitively depends on) and all descendants (creations that transitively depend on it) — and the connectors between them. Creations that merely share a common dependency with the selection (siblings) MUST NOT be highlighted.
- **FR-010a**: The inspector MUST operate exclusively on creations currently installed in the active profile, rendered in load order; uninstalled or historical creations are out of scope for the grid (dependencies pointing at them are handled per FR-014).
- **FR-011**: When a creation is selected, highlighted connectors MUST render in white with a slight glow effect and unrelated connectors MUST dim, mirroring the existing diff dialog behavior.
- **FR-012**: Selecting empty space or toggling the current selection off MUST restore the default (unhighlighted) rendering of the graph.
- **FR-013**: The inspector MUST handle dependency cycles without infinite loops and MUST include all cycle participants in the highlight when any member is selected.
- **FR-014**: The inspector MUST ignore dependencies whose target (or source) is not present among the currently installed creations — no connector is drawn and such dependencies MUST NOT contribute to collapse state or palette-color computation.
- **FR-014a**: When a creation has one or more missing *hard* dependencies, the inspector MUST display a warning indicator on that creation's row. Missing *soft* dependencies MUST be silently ignored (no warning).
- **FR-015**: The inspector MUST react to load-order, profile, or data changes by rebuilding the graph and clearing any transient selection state.
- **FR-016**: The inspector MUST be read-only: it MUST NOT expose controls to disable, remove, or re-order creations. Users perform those actions via the game menu; the inspector only visualises the resulting state.
- **FR-017**: The inspector MUST replicate the refresh / outdated-data signalling behaviour already implemented by the Installed Order tab so that the displayed graph stays consistent with the authoritative load-order data source.

### Key Entities *(include if feature involves data)*

- **Creation**: An individual content module in the load order. Relevant attributes for this feature: identity, display name, position in load order, and whether it has any known dependency information.
- **Dependency**: A directed relationship from one creation (dependent) to another (target), classified as hard or soft. May reference a target that is not present in the current load order.
- **Dependency Graph**: The collection of creations and dependencies for the current load order, used to compute highlight sets, color assignments, and connector routing.
- **Inspector View State**: User-controlled toggles (hide soft, hide collapsed) and current selection; persists only for the life of the current view session.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a load order of up to 500 creations, opening the Dependency Inspector and rendering the initial graph completes in under 2 seconds on a typical user machine.
- **SC-002**: Selecting a creation updates the highlight state (graph highlight + dimming) in under 200 ms, consistent with the diff dialog's perceived responsiveness.
- **SC-003**: In usability testing, at least 90% of participants correctly identify, within 30 seconds, which creations would be broken by removing a given creation they select in the inspector.
- **SC-004**: Toggling "hide soft dependencies" or "hide collapsed creations" updates the visible graph in under 300 ms without losing scroll position.
- **SC-005**: Across a representative sample of load orders, connector rendering produces fewer crossings than a naive same-side layout in at least 80% of cases (validated against a reference routing).

## Assumptions

- Dependency data (both hard and soft) for installed creations is already available to the application via the existing dependency sources established in feature 006; this feature consumes that data and does not introduce new scraping or parsing.
- The existing diff-box presentation model (feature 010) provides reusable primitives for the centered datagrid, side connectors, selection highlight (white + glow), and dimming. This feature extends or reuses those primitives rather than re-implementing them.
- Soft vs. hard classification of each dependency is either already present in the data model or can be derived deterministically from existing fields; no new user-provided classification UI is required.
- The inspector operates on the currently loaded profile's load order; multi-profile comparison is out of scope for this feature.
- Performance targets assume load orders up to ~500 creations; larger load orders may degrade gracefully but are not a sizing target for v1.
- The color palette rotation reuses (or is consistent with) the palette already used in the diff box, so visual language remains coherent across tools.
