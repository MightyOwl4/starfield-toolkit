"""Tests for dependency graph construction, closure traversal, and
deterministic palette-color assignment.

Spec: 012-dependency-inspector
"""
from starfield_tool.models import Creation
from starfield_tool.tools.dependency_inspector import (
    ancestors,
    build_dependency_graph,
    descendants,
)
from starfield_tool.tools.load_order_diff import _MOVE_COLORS


def _make(cid: str, pos: int, files: list[str] | None = None) -> Creation:
    return Creation(
        content_id=cid,
        display_name=cid.upper(),
        load_position=pos,
        plugin_files=files or [],
    )


def _cat(**req_mods: list[str]) -> dict[str, dict]:
    """Build a catalogue dict where kwargs are content_id -> required_mods list."""
    return {cid: {"required_mods": targets} for cid, targets in req_mods.items()}


# ---------------------------------------------------------------- build

class TestBuildHardOnly:
    def test_simple_chain(self):
        creations = [_make("a", 0), _make("b", 1), _make("c", 2)]
        catalogue = _cat(b=["a"], c=["b"])
        g = build_dependency_graph(creations, catalogue, {})
        assert g.out_edges["c"] == ["b"]
        assert g.out_edges["b"] == ["a"]
        assert g.in_edges["a"] == ["b"]
        assert g.in_edges["b"] == ["c"]
        assert g.no_deps == set()
        assert g.missing_hard == {}

    def test_missing_hard_recorded_and_no_edge(self):
        creations = [_make("a", 0), _make("b", 1)]
        catalogue = _cat(b=["a", "ghost"])
        g = build_dependency_graph(creations, catalogue, {})
        assert g.missing_hard == {"b": ["ghost"]}
        # only the in-grid edge survives
        assert ("b", "a") in g.edge_kind
        assert all(t != "ghost" for t in g.out_edges["b"])

    def test_forward_pointing_edge_dropped(self):
        # Catalogue says a depends on b, but a is loaded *before* b — drop.
        creations = [_make("a", 0), _make("b", 1)]
        catalogue = _cat(a=["b"])
        g = build_dependency_graph(creations, catalogue, {})
        assert g.edge_kind == {}
        assert g.no_deps == {"a", "b"}


class TestSoftAndKindMerging:
    def test_hard_overrides_soft(self):
        creations = [_make("a", 0), _make("b", 1)]
        catalogue = _cat(b=["a"])
        soft = {"b": ["a"]}
        g = build_dependency_graph(creations, catalogue, soft)
        assert g.edge_kind[("b", "a")] == "hard"

    def test_soft_only_edge(self):
        creations = [_make("a", 0), _make("b", 1)]
        g = build_dependency_graph(creations, {}, {"b": ["a"]})
        assert g.edge_kind[("b", "a")] == "soft"

    def test_missing_soft_silently_dropped(self):
        creations = [_make("a", 0)]
        g = build_dependency_graph(creations, {}, {"a": ["ghost"]})
        assert g.edge_kind == {}
        assert g.missing_hard == {}


class TestNoDeps:
    def test_no_deps_set(self):
        creations = [_make("a", 0), _make("b", 1), _make("c", 2)]
        catalogue = _cat(c=["a"])
        g = build_dependency_graph(creations, catalogue, {})
        assert g.no_deps == {"b"}


class TestSortedAdjacency:
    def test_out_edges_sorted_by_load_position(self):
        # d depends on a, b, c — but listed in catalogue out of order.
        creations = [_make("a", 0), _make("b", 1), _make("c", 2), _make("d", 3)]
        catalogue = _cat(d=["c", "a", "b"])
        g = build_dependency_graph(creations, catalogue, {})
        assert g.out_edges["d"] == ["a", "b", "c"]

    def test_in_edges_sorted_by_load_position(self):
        # b, c, d all depend on a.
        creations = [_make("a", 0), _make("b", 1), _make("c", 2), _make("d", 3)]
        catalogue = _cat(b=["a"], c=["a"], d=["a"])
        g = build_dependency_graph(creations, catalogue, {})
        assert g.in_edges["a"] == ["b", "c", "d"]


class TestPaletteColor:
    def test_outgoing_takes_precedence(self):
        # b has both an outgoing edge (b→a) and an incoming edge (c→b).
        creations = [_make("a", 0), _make("b", 1), _make("c", 2)]
        catalogue = _cat(b=["a"], c=["b"])
        g = build_dependency_graph(creations, catalogue, {})
        # b's color must equal the (b, a) edge color.
        # canonical edge order = sorted by (pos[s], pos[t]):
        # (b, a) has (1, 0); (c, b) has (2, 1). So (b, a) is first → palette[0].
        assert g.palette_color["b"] == _MOVE_COLORS[0]

    def test_incoming_fallback(self):
        # a has no outgoing edges; it has an incoming edge b→a.
        creations = [_make("a", 0), _make("b", 1)]
        catalogue = _cat(b=["a"])
        g = build_dependency_graph(creations, catalogue, {})
        # Only one edge (b, a); a's color = that edge's color.
        assert g.palette_color["a"] == _MOVE_COLORS[0]

    def test_first_outgoing_is_earliest_target(self):
        creations = [_make("a", 0), _make("b", 1), _make("c", 2), _make("d", 3)]
        # d depends on b and c. "First" outgoing = earliest-position target = b.
        catalogue = _cat(d=["b", "c"])
        g = build_dependency_graph(creations, catalogue, {})
        # Determine expected color by reproducing canonical order.
        # Edges: (d, b) = (3, 1), (d, c) = (3, 2). Sorted by (pos[s], pos[t]):
        # (d, b) first → palette[0]; (d, c) second → palette[1].
        assert g.palette_color["d"] == _MOVE_COLORS[0]

    def test_no_dep_creation_has_no_color(self):
        creations = [_make("a", 0), _make("b", 1)]
        g = build_dependency_graph(creations, {}, {})
        assert "a" not in g.palette_color
        assert "b" not in g.palette_color


class TestCycleSafety:
    def test_cycle_does_not_crash_build(self):
        # b depends on a (b after a, OK). a depends on b (forward — dropped).
        # Builds without infinite loop.
        creations = [_make("a", 0), _make("b", 1)]
        catalogue = _cat(b=["a"], a=["b"])
        g = build_dependency_graph(creations, catalogue, {})
        # Forward-pointing (a, b) was dropped; only (b, a) survives.
        assert ("b", "a") in g.edge_kind
        assert ("a", "b") not in g.edge_kind


# ---------------------------------------------------------------- closure

class TestClosure:
    def test_simple_chain_ancestors_and_descendants(self):
        creations = [_make("a", 0), _make("b", 1), _make("c", 2)]
        g = build_dependency_graph(creations, _cat(b=["a"], c=["b"]), {})
        assert ancestors(g, "c") == {"a", "b"}
        assert descendants(g, "a") == {"b", "c"}
        assert ancestors(g, "a") == set()
        assert descendants(g, "c") == set()

    def test_diamond_siblings_not_in_closure(self):
        # a is the shared ancestor of b and c; selecting b does not pull c.
        creations = [_make("a", 0), _make("b", 1), _make("c", 2)]
        g = build_dependency_graph(creations, _cat(b=["a"], c=["a"]), {})
        assert ancestors(g, "b") == {"a"}
        assert descendants(g, "b") == set()
        assert "c" not in (ancestors(g, "b") | descendants(g, "b"))

    def test_visible_edges_predicate_filters_traversal(self):
        creations = [_make("a", 0), _make("b", 1), _make("c", 2)]
        g = build_dependency_graph(creations, _cat(c=["b"]), {"b": ["a"]})
        # Hide soft: c→b survives (hard), b→a hidden (soft).
        pred = lambda s, t: g.edge_kind[(s, t)] != "soft"  # noqa: E731
        anc = ancestors(g, "c", visible_edges=pred)
        assert anc == {"b"}  # not {"a", "b"}

    def test_cycle_does_not_loop(self):
        # Synthetic cycle by hand-mutating the graph (build won't naturally
        # produce one — forward-pointing edges are dropped).
        creations = [_make("a", 0), _make("b", 1)]
        g = build_dependency_graph(creations, _cat(b=["a"]), {})
        g.out_edges["a"].append("b")
        g.edge_kind[("a", "b")] = "soft"
        # ancestors of b should hit a, then a→b loop terminates via visited.
        anc = ancestors(g, "b")
        assert anc == {"a"}

    def test_isolated_node_returns_empty(self):
        creations = [_make("a", 0), _make("b", 1)]
        g = build_dependency_graph(creations, {}, {})
        assert ancestors(g, "a") == set()
        assert descendants(g, "a") == set()
