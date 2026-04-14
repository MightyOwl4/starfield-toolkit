"""Tests for the greedy connector side-router (assign_sides).

Spec: 012-dependency-inspector
"""
from starfield_tool.tools.dependency_inspector import (
    _segments_cross,
    assign_sides,
)


def _crossings_all_left(edges, position):
    """Baseline: all edges on one side, count pairwise crossings."""
    edge_list = list(edges)
    crossings = 0
    for i in range(len(edge_list)):
        for j in range(i + 1, len(edge_list)):
            if _segments_cross(edge_list[i], edge_list[j], position):
                crossings += 1
    return crossings


def _crossings(routed, position):
    by_side = {"left": [], "right": []}
    for e, s in routed.items():
        by_side[s].append(e)
    total = 0
    for side_edges in by_side.values():
        for i in range(len(side_edges)):
            for j in range(i + 1, len(side_edges)):
                if _segments_cross(side_edges[i], side_edges[j], position):
                    total += 1
    return total


def test_empty_input():
    assert assign_sides([], {}) == {}


def test_deterministic():
    edges = [("a", "z"), ("b", "y"), ("c", "x")]
    pos = {"a": 0, "b": 1, "c": 2, "x": 3, "y": 4, "z": 5}
    r1 = assign_sides(edges, pos)
    r2 = assign_sides(list(reversed(edges)), pos)
    assert r1 == r2


def test_two_non_crossing_edges_balanced():
    # Two edges that don't cross — router should still try to balance,
    # so one goes to each side.
    edges = [("a", "b"), ("c", "d")]
    pos = {"a": 0, "b": 1, "c": 2, "d": 3}
    routed = assign_sides(edges, pos)
    sides = sorted(routed.values())
    assert sides == ["left", "right"]


def test_router_beats_all_same_side_on_crossing_heavy_set():
    # Classic crossing-heavy fixture: nested + interleaved edges.
    nodes = list("abcdefghij")  # 10 nodes
    pos = {n: i for i, n in enumerate(nodes)}
    edges = [
        ("c", "a"),  # 2->0
        ("d", "b"),  # 3->1, crosses (c,a)
        ("e", "a"),
        ("f", "b"),
        ("g", "a"),
        ("h", "b"),
        ("i", "c"),
        ("j", "d"),
    ]
    baseline = _crossings_all_left(edges, pos)
    routed = assign_sides(edges, pos)
    actual = _crossings(routed, pos)
    assert actual < baseline, (
        f"router crossings {actual} not better than baseline {baseline}"
    )


def test_segments_cross_basic():
    pos = {"a": 0, "b": 1, "c": 2, "d": 3}
    # (a, c) spans 0..2; (b, d) spans 1..3 — they interleave → cross.
    assert _segments_cross(("a", "c"), ("b", "d"), pos)
    # Nested: (a, d) 0..3 contains (b, c) 1..2 — no cross.
    assert not _segments_cross(("a", "d"), ("b", "c"), pos)
    # Disjoint: (a, b) 0..1 vs (c, d) 2..3 — no cross.
    assert not _segments_cross(("a", "b"), ("c", "d"), pos)
