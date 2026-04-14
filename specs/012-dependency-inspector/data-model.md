# Data Model: Dependency Inspector

**Phase 1 output** — entities, fields, relationships, and state used by the feature.

The inspector introduces no persistent data. All structures are in-memory, rebuilt on tab activation or refresh. Types below live inside `src/starfield_tool/tools/dependency_inspector.py` unless noted.

---

## Kind (enum)

```python
Kind = Literal["hard", "soft"]
```

- `"hard"` — sourced from catalogue `required_mods` (authoritative; missing one means the creation will likely fail to load).
- `"soft"` — sourced from description-parser output (suggested ordering; missing one is usually cosmetic).

---

## Edge

```python
@dataclass(frozen=True)
class Edge:
    source: str       # content_id of the dependent creation
    target: str       # content_id of the depended-on creation
    kind: Kind
```

- `source` and `target` are both `content_id`s that exist in the installed creations set (missing endpoints are filtered out upstream).
- Direction: `source` "depends on" `target`. Load-order-wise, `target` must be loaded before `source` (we draw the edge accordingly).

---

## MissingDep

```python
@dataclass(frozen=True)
class MissingDep:
    dependent: str    # content_id present in installed set
    missing: str      # content_id referenced but not installed
    kind: Kind        # only "hard" misses are recorded; soft misses are silently dropped
```

---

## DependencyGraph

```python
@dataclass
class DependencyGraph:
    # All installed creations in load order (source of truth for positions).
    order: list[str]                            # content_ids
    position: dict[str, int]                    # content_id -> index in order

    # Adjacency maps. Keys are content_ids; values are sorted by load position of the other endpoint.
    out_edges: dict[str, list[str]]             # a -> [targets]
    in_edges: dict[str, list[str]]              # b -> [sources]
    edge_kind: dict[tuple[str, str], Kind]      # (source, target) -> kind

    # Derived, computed once at build time.
    palette_color: dict[str, str]               # content_id -> "#RRGGBB" (only for participating creations)
    no_deps: set[str]                           # content_ids with zero in+out edges
    missing_hard: dict[str, list[str]]          # content_id -> list of missing target content_ids
```

### Invariants

- Every key in `out_edges`, `in_edges`, `palette_color`, and every element of `order` is a currently-installed `content_id`.
- `palette_color` contains exactly those content_ids *not* in `no_deps`.
- `no_deps ∪ participating == set(order)` and they are disjoint.
- `out_edges[a]` is sorted by `position[target]` ascending (so `out_edges[a][0]` is the "first outgoing" per FR-009).
- `in_edges[b]` is sorted by `position[source]` ascending.
- For every edge `(s, t)` in `edge_kind`, `t ∈ out_edges[s]` and `s ∈ in_edges[t]` and `position[t] < position[s]` (dependencies point at earlier-loading creations).

### State transitions

The graph itself is immutable after construction. Only *view state* mutates — see below.

---

## InspectorViewState

Lives on the tool instance, not on the graph.

```python
@dataclass
class InspectorViewState:
    hide_soft: bool = False
    hide_no_deps: bool = False
    selected: str | None = None   # content_id, or None when nothing selected
```

### Derived at render time

- **Visible edges**: all edges if `hide_soft` is False; else only `kind == "hard"`.
- **Visible rows**: all `order` if `hide_no_deps` is False; else `order` minus `no_deps`.
- **Highlight set**: `{selected} ∪ ancestors(selected) ∪ descendants(selected)`, traversing only visible edges. Empty if `selected is None`.
- **Highlighted edges**: visible edges `(s, t)` where both `s` and `t` are in the highlight set.

### Reset conditions

- Load-order, profile, or catalogue change → rebuild `DependencyGraph`, clear `InspectorViewState.selected`, preserve toggles.
- User clicks empty canvas / clicks selected row again → `selected = None`.

---

## Side (enum for connector routing)

```python
Side = Literal["left", "right"]
```

Routing output (not stored on the graph; recomputed per render when edge visibility changes):

```python
EdgeRouting = dict[tuple[str, str], Side]
```

---

## Relationships to existing models

- **Creation** (`src/starfield_tool/models.py`): read-only input — supplies `content_id`, `display_name`, and `load_position`.
- **Catalogue entry dict** (`src/bethesda_creations/catalogue.py`): read-only input — supplies `required_mods` for hard edges.
- **Description-parser output JSON** (feature 008): read-only input — supplies soft edges via its existing `filename → content_id` mapping.

No existing type is modified.
