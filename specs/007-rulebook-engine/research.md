# Research: Load Order Rule Books

**Date**: 2026-04-05 | **Branch**: `007-rulebook-engine`

## Decision 1: Rule Book File Format

**Decision**: JSON with a simple schema. Each file is a self-contained rule book.

**Rationale**: Constitution principle I (Simplicity First) and FR-015 (human-readable, manually editable). JSON is already used throughout the project (config, cache, catalogue). The modding community is comfortable with JSON. No new dependencies needed.

**Schema**:
```json
{
  "name": "My Rule Book",
  "description": "Fixes load order for XYZ mods",
  "version": "1.0",
  "rules": [
    {
      "plugin": "Addon.esm",
      "load_after": ["BaseMod.esm"],
      "note": "Addon patches records from BaseMod"
    }
  ]
}
```

**Rule types**: Both `load_after` and `load_before` are supported. `load_before` is normalized to an equivalent `load_after` constraint at load time — if A specifies `load_before: [B]`, the system emits `B.load_after = [A]`. This means the sorting pipeline only ever sees `load_after` constraints, requiring zero changes to the merger or solver. The `load_before` syntax is useful for positioning patches between two mods without including both as full book entries.

**Alternatives considered**:
- YAML: Would require pyyaml (already a dependency), but less common for user-edited configs in gaming communities
- Binary format: Rejected — reduces transparency, modding community expects editable configs
- `load_after` only: Simpler but can't express "insert between X and Y" when Y isn't a book entry

## Decision 2: Storage Locations

**Decision**: 
- User rule books: `%APPDATA%/StarfieldToolkit/rules/` (scanned on startup)
- Curated rule books: Bundled via PyInstaller `--add-data rules;data/rules` → `sys._MEIPASS/data/rules/` at runtime
- Dev mode curated: `data/rules/` relative to project root

**Rationale**: Follows existing patterns — LOOT masterlist uses the same `sys._MEIPASS/data/` pattern, config uses `%APPDATA%/StarfieldToolkit/`. User directory is separate from curated to avoid shadowing issues.

**Alternatives considered**:
- Single directory for both: Would require metadata to distinguish curated from user — adds complexity
- Subdirectories within rules/ (curated/ and user/): Slightly cleaner but unnecessary separation for small file counts

## Decision 3: Rule Book Registry Persistence

**Decision**: Extend `AppSettings` with a `rulebook_registry` field storing a list of `{filename, enabled, source}` entries in priority order. Saved in the existing `config.json`.

**Rationale**: Follows the existing config pattern. The registry is small (under 50 entries). Storing in config.json keeps it alongside other app settings. On load: reconcile registry with discovered files — discard entries for missing files, add new files at the top.

**Alternatives considered**:
- Separate registry file (rulebook_registry.json): Extra file to manage, extra I/O, no real benefit
- Store state inside each rule book file: Would modify shared files, breaking read-only curated books

## Decision 4: Sorter Priority Assignment

**Decision**: Curated rule books at priority 30. User rule books at priority 40 as base, with each book in the user's priority list getting +1 to differentiate (book at position 0 = 40 + N - 0, book at position N-1 = 41). This ensures user books always beat curated, and within user books, list order determines priority.

**Rationale**: Fits the established hierarchy: CAT=10, LOOT=20, curated=30, user=40+, TES4=100. The +1 per position means the merger resolves conflicts between user books by the user's explicit priority ordering.

**Alternatives considered**:
- All user books at same priority (40): Would make ordering between user books undefined on conflict
- Curated at 25: Too close to LOOT, leaves no room for future auto-generated books (feature 008)

## Decision 5: Rule Book Management Tool Architecture

**Decision**: New ToolModule class `RuleBookTool` in `src/starfield_tool/tools/rulebook_manager.py`. Registered in `tools/__init__.py` MODULES list. The editor is a dialog (CTkToplevel) launched from the management tool, similar to how CreationDetailsDialog works.

**Rationale**: Follows existing patterns exactly. The management list view is the main tab content; the editor is a pop-up dialog for create/edit workflows. This avoids cluttering the tab with editor UI when the user is just browsing.

**Alternatives considered**:
- Editor as a separate tab: Would add a tab for infrequent use
- Inline editor in the management tab: Switches between list and editor modes — adds state complexity

## Decision 6: Missing Creation Detection

**Decision**: At rule book load time, resolve each plugin filename against installed creations (from ContentCatalog.txt). Mark unresolved entries as missing. A book is "inapplicable" if fewer than 2 of its referenced creations are installed. Checking uses the same `plugin_files` dict already built for the TES4 sorter.

**Rationale**: Reuses existing infrastructure. The check is cheap (dict lookup) and happens once at load time. The inapplicability threshold of 2 makes sense — a single-creation book has no ordering rules, and a two-creation book with one missing has no applicable rules.

**Alternatives considered**:
- Check at sort time only: Would delay error feedback — user wouldn't know until they try to sort
- Check by content_id only: Plugin filenames are more robust since they're what the sorter operates on

## Decision 7: Default Ordering Strategy

**Decision**: Per clarification session:
- Curated books: sorted by numeric filename prefix (`001_` before `010_`)
- User books (new/unregistered): sorted by file creation date, newest first
- On reconciliation: new books placed at top, above previously-saved order
- Stale registry entries (file deleted): silently discarded

**Rationale**: Newest-first for user books means the most recently added rule book gets highest priority — matching the typical workflow of "I just added this to fix a specific problem." Numeric prefixes for curated books give the project control over default ordering. Stale cleanup keeps the registry tidy.

**Alternatives considered**:
- Alphabetical for new books: Doesn't reflect recency or intent
- Newest at bottom: Counter-intuitive — user's latest fix would have lowest priority
