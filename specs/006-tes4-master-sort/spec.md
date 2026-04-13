# Feature Specification: TES4 Master Dependency Sorting

**Feature Branch**: `006-tes4-master-sort`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "Implement the TES4 part of the dependency resolution master plan. TES4 sorter with highest priority (leave gaps for future expansion). Non-bypassable check on apply that prevents writing broken load orders, displays offending creations, and suggests auto-sort."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - TES4 Master Dependencies in Auto-Sort (Priority: P1)

A user clicks "Auto Sort" on their creation load order. The system reads the TES4 header from each installed creation's plugin file to discover master dependencies (which plugins each creation requires to be loaded before it). These master dependencies are used as the highest-priority constraints in the sorting algorithm, ensuring that no creation is ever placed before a plugin it depends on — regardless of category tier or other sorting rules.

**Why this priority**: Without the TES4 sorter, the load order solver cannot account for hard engine-level dependencies. This is the foundation that all other sorting constraints build on.

**Independent Test**: Can be fully tested by auto-sorting a load order where one creation has a master dependency on another, and verifying the dependent creation is always placed after its master — even if their category tiers would normally place them in the opposite order.

**Acceptance Scenarios**:

1. **Given** Creation A lists Creation B's plugin as a master in its TES4 header, **When** the user runs auto-sort, **Then** Creation B appears before Creation A in the sorted result regardless of their category tiers.
2. **Given** a creation has multiple masters (e.g., Starfield.esm, SFBGS004.esm, and a community mod), **When** the system parses its TES4 header, **Then** only masters that correspond to installed creations are used as sorting constraints (base game masters like Starfield.esm are ignored as they are always loaded first by the engine).
3. **Given** the TES4 sorter produces a constraint that contradicts a category tier assignment, **When** constraints are merged, **Then** the TES4 constraint wins because it has the highest priority.
4. **Given** TES4 master dependencies create a chain (A depends on B, B depends on C), **When** auto-sort runs, **Then** the solver produces the correct order: C, then B, then A.
5. **Given** a plugin file is unreadable or corrupted, **When** the system attempts to parse its TES4 header, **Then** the creation is skipped with a warning and sorting continues with the remaining constraints.

---

### User Story 2 - Non-Bypassable Validation on Apply (Priority: P2)

When a user attempts to apply (save) any load order change — whether from manual drag-and-drop or partial auto-sort acceptance — the system validates that the proposed order does not violate any TES4 master dependencies. If violations are found, the system blocks the write, shows which creations break the TES4 order (limited to the first few offenders if many), and offers a suggestion to auto-sort.

This check is non-bypassable: the user cannot force-write a broken load order. The only way forward is to fix the order (manually or via auto-sort).

**Why this priority**: Preventing CTDs caused by incorrect load order is the primary safety value. Even if the user manually rearranges creations, the system must refuse to write an order that would crash the game.

**Independent Test**: Can be tested by manually dragging a creation above one of its masters, clicking Apply, and verifying the write is blocked with an informative message.

**Acceptance Scenarios**:

1. **Given** the user has manually dragged Creation A above its master dependency B, **When** they click Apply, **Then** the system blocks the write and shows a message listing Creation A as an offender that must load after Creation B.
2. **Given** multiple creations violate TES4 ordering, **When** the user clicks Apply, **Then** the system shows the first few offenders (up to 5) with a note that more exist, and suggests using auto-sort to fix the order.
3. **Given** the proposed order has no TES4 violations, **When** the user clicks Apply, **Then** the write proceeds normally (existing behavior preserved).
4. **Given** the validation message is shown, **When** the user dismisses it, **Then** the load order remains unchanged (the broken order is not written to disk).
5. **Given** the user sees the validation message with auto-sort suggestion, **When** they choose to auto-sort, **Then** the auto-sort runs and resolves the violations.

---

### Edge Cases

- What happens when a creation's master is not installed? The system ignores dependencies on non-installed plugins (they are either base game files or missing mods, and cannot be reordered).
- What happens when TES4 master dependencies form a cycle? This should not happen with valid plugins, but if detected, the system logs a warning and skips the cyclic constraints (the solver's existing cycle handling applies).
- What happens when a creation has no plugin files on disk (file_missing=true)? The system skips TES4 parsing for that creation since there is no header to read.
- What happens when base game masters (Starfield.esm, SFBGS*.esm) appear in MAST entries? These are filtered out — they are always loaded by the engine before any creation plugins and are not managed by the load order tool.
- What happens when a TES4 load_after dependency crosses tier boundaries? The constraint is honored regardless — TES4 master constraints must not be dropped even if the dependency is in a different tier than the dependent.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read the TES4 record header from each installed creation's plugin file to extract the list of master dependencies (MAST subrecords).
- **FR-002**: System MUST filter out base game masters (Starfield.esm and official DLC/update plugins) from the extracted dependency list, retaining only masters that correspond to other installed creation plugins.
- **FR-003**: System MUST produce sorting constraints from TES4 masters as `load_after` rules with the highest priority in the constraint system, with priority gaps left for future constraint sources between TES4 and existing sorters.
- **FR-004**: TES4 master `load_after` constraints MUST be honored across tier boundaries — they must not be silently dropped when the dependency target is in a different tier than the dependent creation.
- **FR-005**: System MUST integrate the TES4 sorter into the existing auto-sort pipeline alongside the category and LOOT sorters.
- **FR-006**: System MUST validate the proposed load order against TES4 master dependencies before writing to disk, blocking the write if any violations are found.
- **FR-007**: The validation check MUST be non-bypassable — there is no user option to force-write a load order that violates TES4 master dependencies.
- **FR-008**: When validation fails, the system MUST display an informational message listing the offending creations (up to 5) and which masters they must load after, with a suggestion to use auto-sort.
- **FR-009**: System MUST handle unreadable or corrupted plugin files gracefully — skip them with a warning and continue with remaining creations.
- **FR-010**: The TES4 header parser MUST operate on locally installed files only (no network access required).

### Key Entities

- **Master Dependency**: A relationship between two plugins where one (the dependent) lists the other (the master) in its TES4 header MAST subrecords. The master must be loaded before the dependent.
- **TES4 Header**: The first record in every .esm/.esp/.esl file, containing plugin metadata including the MAST subrecords that declare master dependencies.
- **Validation Violation**: An entry in the proposed load order where a creation appears before one or more of its TES4 masters. Contains: the offending creation, the master(s) it must load after, and their current positions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Auto-sort never produces a load order that violates TES4 master dependencies.
- **SC-002**: Users cannot save a load order to disk that would cause crashes due to missing master dependencies (100% prevention of TES4-order CTDs for managed plugins).
- **SC-003**: TES4 header parsing completes in under 2 seconds for up to 600 installed creations.
- **SC-004**: Validation messages clearly identify which creations are out of order and what they depend on, enabling users to understand and fix the issue.
- **SC-005**: Existing auto-sort behavior for category tiers and LOOT rules is preserved — TES4 constraints only override when there is a direct conflict.

## Assumptions

- Plugin files (.esm/.esp/.esl) are available in the game's Data directory and follow the standard TES4 record format used by Bethesda's Creation Engine.
- The TES4 header is always the first record in the file and the MAST subrecords are within the first few kilobytes — reading the full file is not necessary.
- Base game master files (Starfield.esm, SFBGS*.esm) are identifiable by a known prefix/pattern and are always loaded before creation plugins by the engine.
- The existing constraint merger and topological solver can be extended to support cross-tier load_after constraints without a full rewrite.
- The existing apply workflow in the load order tool can be extended with a pre-write validation step.
- Users have a reasonable number of installed creations (up to ~600) making per-file TES4 header parsing feasible at startup or sort time.
