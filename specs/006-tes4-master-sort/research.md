# Research: TES4 Master Dependency Sorting

**Date**: 2026-04-05 | **Branch**: `006-tes4-master-sort`

## Decision 1: TES4 Binary Header Parsing Approach

**Decision**: Read the first record of each `.esm`/`.esp`/`.esl` file and extract MAST subrecords using stdlib binary I/O. No external dependencies.

**Rationale**: The TES4 record is always the first record in the file. The format is stable across all Creation Engine games (Oblivion through Starfield). MAST subrecords are null-terminated strings within the first few KB. Reading just the TES4 record data (not the full file) is sufficient and fast.

**Format**:
```
Record header (24 bytes):
  Bytes 0-3:   "TES4" (ASCII)
  Bytes 4-7:   data_size (uint32 LE) — size of subrecord data
  Bytes 8-11:  flags (uint32 LE)
  Bytes 12-15: form_id (uint32 LE)
  Bytes 16-23: version control info

Subrecords (within data_size bytes):
  Each: 4-byte type + 2-byte size (uint16 LE) + size bytes of data
  MAST subrecord: type="MAST", data=null-terminated filename string
  DATA subrecord: follows each MAST, 8 bytes (master file size)
```

**Alternatives considered**:
- `summaryPC.json` from API: Already explored in 005, but that's the plugin's OWN filename, not its masters
- External library (e.g., `esm-reader`): Unnecessary dependency, the format is trivial
- Full file parsing with record iteration: Overkill — we only need the first record

## Decision 2: Priority Assignment for TES4 Sorter

**Decision**: TES4 sorter gets priority 100. Existing priorities: CAT=10, LOOT=20. Gap of 30-90 left for future constraint sources (rule books at 30-90, patch analysis at 25).

**Rationale**: The priority system uses integer comparison (higher wins). TES4 at 100 leaves ample room for the planned constraint hierarchy:
```
Priority 10:  Category sorter (existing)
Priority 20:  LOOT sorter (existing)
Priority 25:  Patch analysis (future)
Priority 30+: Curated rule book (future)
Priority 40+: User rule books (future, ordered)
Priority 100: TES4 master dependencies
```

**Alternatives considered**:
- Priority 30: Too close to LOOT, not enough gap for future sources
- Priority 1000: Works but unnecessarily large; 100 is sufficient

## Decision 3: Cross-Tier Dependency Resolution

**Decision**: Modify the solver to handle cross-tier `load_after` constraints by promoting the dependent item to the same tier as its dependency (or the latest tier among all its dependencies).

**Rationale**: The current solver silently drops cross-tier dependencies (`pipeline.py:138` — `if dep in names_in_bucket`). This is acceptable for LOOT/CAT soft constraints but unacceptable for TES4 hard dependencies. When a TES4 constraint says "A must load after B" and A is in tier 3 but B is in tier 5, A must be moved to tier 5 (or later). This is a pre-solve fixup: scan all load_after constraints, and if any target a different tier, promote the dependent to the target's tier (taking the max tier among all dependencies).

**Alternatives considered**:
- Flatten all items into a single tier: Loses the tier structure entirely
- Run a global topological sort ignoring tiers: Same problem — destroys tier grouping
- Only promote for TES4 constraints (flag on SortConstraint): Cleaner but adds complexity; promoting for all cross-tier deps is simpler and more correct

## Decision 4: Base Game Master Filtering

**Decision**: Filter out masters matching known base game patterns: `Starfield.esm`, `BlueprintShips-Starfield.esm`, and any plugin matching `SFBGS*.esm` or `sfbgs*.esm` (case-insensitive). Also filter `Starfield - Localization.esm` and the Shattered Space DLC master.

**Rationale**: These files are managed by the engine and always loaded before any creation plugins. Including them would generate constraints against files not in the load order tool's management scope.

**Implementation**: A set of known filenames + a pattern match for `sfbgs\d+\.esm` (case-insensitive).

**Alternatives considered**:
- Only filter by checking if the master exists in the creation list: Would miss non-creation masters that happen to exist in Data/ but aren't managed by the tool
- Hardcode every known base game filename: Brittle, new DLCs/updates would require code changes. Pattern match is more resilient.

## Decision 5: Validation Check Integration Point

**Decision**: Add validation as a pre-write check in the `_apply()` method of `load_order.py`, before the `plugins_path.write_text()` call. Parse TES4 headers on-demand (cached for the session).

**Rationale**: The validation must run on every apply, whether the user manually reordered or accepted a partial auto-sort. Placing it in `_apply()` is the single choke point for all writes. TES4 headers don't change during a session, so parsing once and caching the master map is sufficient.

**Alternatives considered**:
- Validate in real-time as user drags items: Too expensive for continuous feedback; batch validation on apply is sufficient
- Validate only after auto-sort: Would miss manual reordering violations

## Decision 6: TES4 Header Caching Strategy

**Decision**: Parse TES4 headers once per auto-sort invocation and cache the master map for the session. The cached map is also used by the apply validation. Invalidation happens on any file system change detected by the existing file watcher.

**Rationale**: Plugin files don't change during normal app usage. Parsing all headers takes <1 second for ~600 files. Caching avoids re-parsing on every apply while the file watcher ensures the cache stays current if the user installs/removes creations.

**Alternatives considered**:
- Parse on app startup: Could add latency to startup for users who don't use the load order tool
- Parse on every apply: Unnecessary I/O, headers don't change mid-session
- Persistent disk cache: Over-engineered — in-memory cache sufficient given fast parsing
