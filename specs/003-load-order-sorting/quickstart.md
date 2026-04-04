# Quickstart: Load Order Sorting Tool

## What This Feature Does

Adds load order management to the "Load Order" tab: drag-and-drop reordering with dirty-state protection, automated sorting via a priority-based pipeline (category + LOOT), a git-merge-style diff view for reviewing proposed changes, and snapshot export/import.

## Key Files

| File | Role |
|------|------|
| `src/load_order_sorter/__init__.py` | NEW — public API re-exports |
| `src/load_order_sorter/pipeline.py` | NEW — constraint-based sorter pipeline + stable merge |
| `src/load_order_sorter/loot_masterlist.py` | NEW — LOOT masterlist fetch, cache, locate |
| `src/load_order_sorter/sorters/category.py` | NEW — 11-tier category mapping + author detection |
| `src/load_order_sorter/sorters/loot.py` | NEW — LOOT masterlist YAML parser |
| `src/load_order_sorter/snapshot.py` | NEW — snapshot export/import |
| `src/load_order_sorter/models.py` | NEW — SortItem, SortResult, etc. |
| `src/starfield_tool/tools/load_order.py` | NEW — Load Order tab UI (grouping, drag-drop, auto sort) |
| `src/starfield_tool/tools/load_order_diff.py` | NEW — Git-merge-style diff dialog |
| `tests/test_load_order_sorter.py` | NEW — sorter + pipeline tests |

## Implementation Order

1. **models.py** — data classes (no dependencies)
2. **sorters/category.py** — standalone, testable with fixture data
3. **sorters/loot.py** — requires PyYAML, testable with sample YAML
4. **pipeline.py** — combines sorters, stable sort logic
5. **snapshot.py** — JSON read/write
6. **starfield_tool/tools/load_order.py** — UI (drag-drop, diff view, buttons)

## How to Test

```bash
# Sorter package (no GUI)
uv run pytest tests/test_load_order_sorter.py -v

# Full suite
uv run pytest tests/ -v
```

## Stable Sort Example

```
Input:  [A, B, C, D, E]  (current order)
Sorter says: A→tier1, C→tier1, E→tier3
No opinion on: B, D

Output: [A, C, B, D, E]
         ↑  ↑  ↑  ↑  ↑
        t1  t1  default(kept relative)  t3

B and D kept their relative order (B before D).
A and C both tier1, A kept before C (stable within tier).
```
