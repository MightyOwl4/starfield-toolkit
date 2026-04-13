# Feature Specification: Load Order Rule Books

**Feature Branch**: `007-rulebook-engine`  
**Created**: 2026-04-05  
**Status**: Draft  
**Input**: User description: "Implement rulebook support with dedicated management tool, two-tier priority system (curated vs user), creation picker editor, missing creation detection, and rulebook sorter integration."

## Clarifications

### Session 2026-04-05

- Q: How should curated rule books be default-ordered? → A: By numeric prefix in filename (e.g., `001_base_fixes.json` before `010_patch_order.json`).
- Q: How should user rule books be default-ordered? → A: By file creation date, newest first (highest priority). This ensures newly added books surface to the top without requiring manual reordering.
- Q: How should new (undiscovered) books merge with previously saved order? → A: New books go to the top of the list, above previously-saved books. This gives file-only users predictable behavior without touching the management tool.
- Q: What happens to registry entries for rule book files that no longer exist? → A: Silently discarded on next use or settings save. No error, no stale entries.
- Q: What happens when a rule book file is present but has corrupted/unparseable content? → A: Show error dialog on startup ("Corrupted rulebook detected: {name}" with instructions). Auto-deactivate but keep in registry so user sees it in the management tool and can take action.
- Q: Should rules support `load_before` in addition to `load_after`? → A: Yes. `load_before` lets a rule express "this plugin must come before X" — useful for positioning patches between two mods without including both as full book entries. Internally, `load_before: [B]` on plugin A is converted to a `load_after: [A]` constraint on B.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rule Book Sorter Integration (Priority: P1)

A user clicks "Auto Sort" on their load order. The sorting pipeline now includes rule book constraints alongside TES4, LOOT, and category sorting. Rule books define explicit `load_after` ordering between creations. Two priority tiers exist: curated rule books (shipped with the app, lower priority) and user rule books (stored in the data directory, higher priority). When multiple rule books conflict, higher-priority books win. Rule books that reference creations not installed locally are handled gracefully -- missing creations are skipped, and if skipping makes the rule book inapplicable (e.g., a two-creation book with one missing), the entire book is ignored for that sort.

**Why this priority**: The sorter integration is the core engine that makes rule books useful. Without it, the management UI has nothing to drive.

**Independent Test**: Can be tested by placing a rule book file in the data directory, running auto-sort, and verifying the specified creation order is respected.

**Acceptance Scenarios**:

1. **Given** a user rule book specifies Creation A must load after Creation B, **When** auto-sort runs, **Then** Creation B appears before Creation A in the result, regardless of category tier.
2. **Given** a curated rule book and a user rule book both specify ordering for the same creation but conflict, **When** auto-sort runs, **Then** the user rule book wins because it has higher priority.
3. **Given** a rule book references a creation that is not installed, **When** auto-sort runs, **Then** that creation's rules are skipped and the remaining rules in the book are still applied.
4. **Given** a rule book has only two creations and one is not installed, **When** auto-sort runs, **Then** the entire book is ignored (it has no applicable rules left).
5. **Given** multiple user rule books exist with an explicit priority order, **When** auto-sort runs, **Then** higher-ranked books take precedence over lower-ranked ones on conflict.
6. **Given** no rule books are present, **When** auto-sort runs, **Then** existing behavior (TES4 + LOOT + category) is preserved unchanged.

---

### User Story 2 - Rule Book Management Tool (Priority: P2)

A user opens the Rule Books tool (a dedicated tab in the app). They see a list of all discovered rule books -- both curated (shipped with the app) and user-created (from the data directory). Each book shows its name, description, number of rules, enabled/disabled status, and applicability status. The user can enable/disable individual books, reorder them by priority (drag or up/down), and rescan the data directory for newly added books. Newly scanned books are added at the top of the user list (sorted by file creation date, newest first), enabled by default. This ensures users who manage rule books by adding/removing files get predictable behavior without needing to open the management tool.

**Why this priority**: Users need a way to see and control which rule books are active and in what order, before they can create or edit their own.

**Independent Test**: Can be tested by placing rule book files in the data directory, opening the tool, and verifying they appear in the list with correct metadata.

**Acceptance Scenarios**:

1. **Given** rule book files exist in the data directory, **When** the user opens the Rule Books tool, **Then** all books are listed with name, description, rule count, and enabled status.
2. **Given** a curated rule book is shipped with the app, **When** the user opens the tool, **Then** curated books appear in a separate section below user books, visually distinct.
3. **Given** the user disables a rule book, **When** they run auto-sort, **Then** that book's rules are not applied.
4. **Given** the user reorders rule books by dragging, **When** they run auto-sort, **Then** the new priority order is respected.
5. **Given** the user clicks "Rescan", **When** new rule book files have been added to the data directory, **Then** they appear at the top of the user list (sorted by creation date, newest first), enabled by default.
6. **Given** a rule book contains creations not installed locally, **When** the user views its details, **Then** missing creations are highlighted with a yellow warning style, and if the book is entirely inapplicable, a red error message is shown.

---

### User Story 3 - Rule Book Creator/Editor (Priority: P3)

A user creates a new rule book from scratch or based on their current load order. They open the editor, give the book a name and description, then pick which creations to include by selecting from their installed creation list. The editor shows the selected creations in their current load order positions -- the user can reorder them to define the desired ordering rules. Saving produces a rule book file in the data directory. The user can also open and edit existing user rule books (curated books are read-only).

**Why this priority**: Creating and editing books is the power-user workflow. The management tool (US2) and sorter (US1) provide value even with manually authored rule book files.

**Independent Test**: Can be tested by creating a new rule book, selecting creations, saving, and verifying the resulting file is loaded by the sorter on next auto-sort.

**Acceptance Scenarios**:

1. **Given** the user clicks "New Rule Book", **When** they enter a name, select creations, and save, **Then** a rule book file is created in the data directory and appears in the management list.
2. **Given** the user selects creations from their installed list, **When** they arrange them in the editor, **Then** the resulting rule book defines `load_after` relationships matching the specified order.
3. **Given** the user opens an existing user rule book for editing, **When** they modify it and save, **Then** the changes are persisted to the same file.
4. **Given** the user tries to edit a curated rule book, **When** they open it, **Then** it opens in read-only mode (view only, no save).
5. **Given** the user is editing a rule book that references creations they later uninstall, **When** they reopen the editor, **Then** missing creations are highlighted in yellow with a warning.

---

### Edge Cases

- What happens when a rule book file has invalid or corrupted content? The system shows an error dialog on startup: "Corrupted rulebook detected: {name}" with instructions to reinstall, undo manual changes, or delete from the data directory. The book is automatically deactivated but NOT removed from the registry -- it remains visible in the management tool (marked as corrupted) so the user can see it exists and take action.
- What happens when a curated rule book and a user rule book have the same filename? The user book takes precedence; the curated version is shadowed and not loaded.
- What happens when all creations in a rule book are uninstalled? The book is marked as inapplicable (red error in management tool) and ignored during sorting.
- What happens when a rule book creates a cycle with another book's rules? The existing solver cycle handling applies -- items in cycles are placed in their original order with a warning.
- What happens when the data directory does not exist at startup? It is created automatically when the first user rule book is saved.
- What happens when two user rule books at the same priority level conflict? The book appearing higher in the user's ordered list wins.
- What happens when a rule book file is deleted but still referenced in the registry? The entry is silently discarded on next use or settings save -- no error shown, no stale entries persist.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support two tiers of rule books: curated (shipped with the app) at lower priority, and user-created (in the data directory) at higher priority.
- **FR-002**: Rule books MUST support both `load_after` and `load_before` ordering relationships between creations identified by plugin filename or content ID. Both rule types may reference plugins that are not entries in the book itself (e.g., referencing installed plugins not managed by the book).
- **FR-002a**: `load_before` rules MUST be normalized to equivalent `load_after` constraints before entering the sorting pipeline. If rule A specifies `load_before: [B]`, the system produces a `load_after: [A]` constraint on plugin B.
- **FR-003**: The rule book sorter MUST integrate into the existing sorting pipeline at a priority level between LOOT (20) and TES4 (100), with curated books at a lower priority than user books.
- **FR-004**: Rule books MUST gracefully handle missing creations: skip rules referencing non-installed creations, and ignore the entire book if skipping makes it inapplicable (fewer than 2 applicable creations remaining).
- **FR-005**: System MUST provide a dedicated Rule Books management tool (app tab) showing all discovered books with name, description, rule count, enabled status, and applicability.
- **FR-006**: Users MUST be able to enable/disable individual rule books and reorder them by priority.
- **FR-007**: System MUST scan the data directory for user rule book files on startup, and provide a manual rescan button.
- **FR-008**: Newly discovered user rule book files MUST be added at the TOP of the user priority list (above previously-saved books), enabled by default, sorted by file creation date (newest first) among themselves.
- **FR-009**: The management tool MUST highlight missing creations in yellow (warning) and show a red error message when a book is entirely inapplicable.
- **FR-010**: System MUST provide a rule book editor for creating new books and editing existing user books.
- **FR-011**: The editor MUST allow selecting creations from the installed list and arranging them to define ordering rules.
- **FR-012**: Curated rule books MUST be viewable but not editable by the user.
- **FR-013**: Users MUST be able to disable curated rule books and change their relative sort order among curated books.
- **FR-014**: Rule book priority order and enabled/disabled state MUST persist across app restarts.
- **FR-015**: The rule book file format MUST be human-readable and manually editable outside the app.
- **FR-016**: Curated rule books MUST be default-ordered by numeric prefix in their filename (e.g., `001_` before `010_`).
- **FR-017**: Registry entries for rule book files that no longer exist on disk MUST be silently discarded on next use or settings save.
- **FR-018**: When a rule book file is present but cannot be parsed (corrupted JSON), the system MUST show an error dialog on startup identifying the file, suggesting corrective actions (reinstall, undo changes, or delete), and auto-deactivate the book. The book MUST remain in the registry and management tool (marked as corrupted) rather than being dropped.

### Key Entities

- **Rule Book**: A named collection of ordering rules between creations. Contains: name, description, source type (curated or user), enabled status, priority position, and a list of rules.
- **Rule**: A single ordering constraint within a rule book. Specifies that one creation must load after and/or before other creations, optionally with a note explaining why. Supports both `load_after` (this plugin needs those loaded first) and `load_before` (this plugin must come before those).
- **Rule Book Registry**: The app's persistent record of all known rule books, their enabled status, and priority order. Separate from the rule book files themselves.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a rule book and see its effects in auto-sort within one app session.
- **SC-002**: Rule books with missing creations degrade gracefully -- the app never crashes or produces incorrect results due to uninstalled creations referenced in a book.
- **SC-003**: Users can manage (enable, disable, reorder) all rule books from a single tool tab without editing files manually.
- **SC-004**: Curated rule books provide sensible defaults that work out of the box for common creation combinations.
- **SC-005**: The rule book file format is simple enough that users can share books by copying a single file.

## Assumptions

- The existing sorting pipeline (TES4 at priority 100, LOOT at 20, category at 10) is in place and extensible for additional constraint sources.
- The data directory (`%APPDATA%/StarfieldToolkit/`) is writable and available for storing user rule books and the registry.
- Curated rule books are bundled as static files within the app distribution.
- The app's tabbed tool system supports adding a new tool tab without architectural changes.
- Users manage a reasonable number of rule books (under 50) making list-based management practical.
- Rule books reference creations by plugin filename (primary) with content ID as fallback for robustness.
