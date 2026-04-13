# Quickstart: TES4 Master Dependency Sorting

**Branch**: `006-tes4-master-sort`

## What This Feature Does

Adds TES4 master dependency awareness to the load order sorter. The system reads plugin file headers to discover which creations depend on which other creations, then uses these as the highest-priority sorting constraints. Additionally, a non-bypassable validation check prevents users from saving load orders that violate master dependencies.

## How to Test

### Auto-Sort with TES4 Dependencies

1. Install two creations where one depends on the other (e.g., a base mod and its addon)
2. Open the Creation Load Order tool
3. Click "Auto Sort"
4. Verify the dependent creation is placed after its master, even if category tiers would suggest otherwise
5. The diff dialog should show `TES4` as the sorter name for the affected items

### Validation on Apply

1. Open the Creation Load Order tool
2. Manually drag a creation ABOVE one of its master dependencies
3. Click "Apply"
4. Verify: write is blocked, message shows which creation is out of order and what it depends on
5. Dismiss the message → order is unchanged (broken order not written)
6. Click "Auto Sort" → violations resolved automatically

## Key Files

| File | Purpose |
|------|---------|
| `src/load_order_sorter/tes4_parser.py` | [NEW] Binary parser for TES4 MAST subrecords |
| `src/load_order_sorter/sorters/tes4.py` | [NEW] TES4 sorter producing load_after constraints |
| `src/load_order_sorter/pipeline.py` | [MODIFIED] Cross-tier dependency promotion, TES4 sorter integration |
| `src/load_order_sorter/validation.py` | [NEW] Pre-write TES4 order validation |
| `src/starfield_tool/tools/load_order.py` | [MODIFIED] Validation check in _apply(), auto-sort includes TES4 |
| `tests/test_tes4_parser.py` | [NEW] Tests for binary header parsing |
| `tests/test_tes4_sorter.py` | [NEW] Tests for constraint generation and cross-tier resolution |
| `tests/test_tes4_validation.py` | [NEW] Tests for apply validation logic |
