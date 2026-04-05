"""Tests for TES4 sorter, cross-tier promotion, and pipeline integration."""
import struct

from load_order_sorter.models import SortItem, SortDecision
from load_order_sorter.pipeline import sort_creations, _promote_cross_tier
from load_order_sorter.sorters.tes4 import PRIORITY, SORTER_NAME, sort


def _make_tes4_file(*master_names: str) -> bytes:
    """Build a minimal TES4 binary file with the given master names."""
    subrecords = b"HEDR" + struct.pack("<H", 12) + b"\x00" * 12
    for name in master_names:
        encoded = name.encode("utf-8") + b"\x00"
        subrecords += b"MAST" + struct.pack("<H", len(encoded)) + encoded
        subrecords += b"DATA" + struct.pack("<H", 8) + b"\x00" * 8
    header = b"TES4" + struct.pack("<I", len(subrecords)) + b"\x00" * 16
    return header + subrecords


def _item(name, index=0, categories=None):
    return SortItem(
        plugin_name=name,
        content_id=name,
        display_name=name,
        categories=categories or [],
        original_index=index,
    )


# --- TES4 sorter constraint generation ---


def test_sorter_produces_load_after_constraints(tmp_path):
    (tmp_path / "Base.esm").write_bytes(_make_tes4_file("Starfield.esm"))
    (tmp_path / "Addon.esm").write_bytes(
        _make_tes4_file("Starfield.esm", "Base.esm")
    )

    items = [_item("Base.esm", 0), _item("Addon.esm", 1)]
    plugins = {"Base.esm": "id-1", "Addon.esm": "id-2"}
    constraints = sort(items, tmp_path, plugins)

    assert len(constraints) == 1
    c = constraints[0]
    assert c.plugin_name == "Addon.esm"
    assert c.type == "load_after"
    assert c.after == "Base.esm"
    assert c.priority == PRIORITY
    assert c.sorter_name == SORTER_NAME


def test_sorter_filters_base_game_masters(tmp_path):
    (tmp_path / "Mod.esm").write_bytes(
        _make_tes4_file("Starfield.esm", "SFBGS004.esm")
    )

    items = [_item("Mod.esm")]
    plugins = {"Mod.esm": "id-1"}
    constraints = sort(items, tmp_path, plugins)

    assert constraints == []  # all masters are base game


def test_sorter_chain_dependencies(tmp_path):
    (tmp_path / "A.esm").write_bytes(_make_tes4_file("Starfield.esm"))
    (tmp_path / "B.esm").write_bytes(_make_tes4_file("Starfield.esm", "A.esm"))
    (tmp_path / "C.esm").write_bytes(_make_tes4_file("Starfield.esm", "B.esm"))

    items = [_item("A.esm", 0), _item("B.esm", 1), _item("C.esm", 2)]
    plugins = {"A.esm": "1", "B.esm": "2", "C.esm": "3"}
    constraints = sort(items, tmp_path, plugins)

    after_map = {c.plugin_name: c.after for c in constraints}
    assert after_map["B.esm"] == "A.esm"
    assert after_map["C.esm"] == "B.esm"


# --- Cross-tier promotion ---


def test_promote_cross_tier_basic():
    items = [_item("A.esm", 0), _item("B.esm", 1)]
    decisions = {
        "A.esm": SortDecision(tier=3),
        "B.esm": SortDecision(tier=5, load_after=[]),
    }
    # A is tier 3, depends on B which is tier 5 → A should be promoted to 5
    decisions["A.esm"].load_after = ["B.esm"]

    _promote_cross_tier(items, decisions)

    assert decisions["A.esm"].tier == 5


def test_promote_cross_tier_chain():
    items = [_item("A.esm"), _item("B.esm"), _item("C.esm")]
    decisions = {
        "A.esm": SortDecision(tier=3, load_after=["B.esm"]),
        "B.esm": SortDecision(tier=5, load_after=["C.esm"]),
        "C.esm": SortDecision(tier=9, load_after=[]),
    }

    _promote_cross_tier(items, decisions)

    # B promoted to 9 (depends on C at 9), A promoted to 9 (depends on B now at 9)
    assert decisions["A.esm"].tier == 9
    assert decisions["B.esm"].tier == 9
    assert decisions["C.esm"].tier == 9


def test_promote_no_change_when_same_tier():
    items = [_item("A.esm"), _item("B.esm")]
    decisions = {
        "A.esm": SortDecision(tier=5, load_after=["B.esm"]),
        "B.esm": SortDecision(tier=5, load_after=[]),
    }

    _promote_cross_tier(items, decisions)

    assert decisions["A.esm"].tier == 5  # unchanged


def test_promote_no_change_when_dep_in_earlier_tier():
    items = [_item("A.esm"), _item("B.esm")]
    decisions = {
        "A.esm": SortDecision(tier=5, load_after=["B.esm"]),
        "B.esm": SortDecision(tier=3, load_after=[]),
    }

    _promote_cross_tier(items, decisions)

    assert decisions["A.esm"].tier == 5  # already after B's tier


# --- End-to-end pipeline with TES4 ---


def test_sort_creations_tes4_overrides_category(tmp_path):
    """A creation in CAT tier 3 depends on one in tier 10 → placed after it."""
    (tmp_path / "Overhaul.esm").write_bytes(_make_tes4_file("Starfield.esm"))
    (tmp_path / "Addon.esm").write_bytes(
        _make_tes4_file("Starfield.esm", "Overhaul.esm")
    )

    items = [
        _item("Addon.esm", 0, categories=["Weapons"]),     # CAT tier 10
        _item("Overhaul.esm", 1, categories=["Overhaul"]),  # CAT tier 3
    ]
    plugins = {"Addon.esm": "1", "Overhaul.esm": "2"}

    result = sort_creations(
        items,
        sorters=["category", "tes4"],
        data_dir=tmp_path,
        installed_plugins=plugins,
    )

    names = [si.plugin_name for si in result.items]
    assert names.index("Overhaul.esm") < names.index("Addon.esm")


def test_sort_creations_preserves_existing_when_no_tes4():
    """Without TES4 constraints, existing CAT/LOOT behavior unchanged."""
    items = [
        _item("A.esm", 0, categories=["Weapons"]),   # tier 10
        _item("B.esm", 1, categories=["Overhaul"]),   # tier 3
    ]

    result = sort_creations(items, sorters=["category"])

    names = [si.plugin_name for si in result.items]
    assert names.index("B.esm") < names.index("A.esm")  # tier 3 before tier 10


def test_sort_creations_tes4_chain(tmp_path):
    (tmp_path / "C.esm").write_bytes(_make_tes4_file("Starfield.esm"))
    (tmp_path / "B.esm").write_bytes(_make_tes4_file("Starfield.esm", "C.esm"))
    (tmp_path / "A.esm").write_bytes(_make_tes4_file("Starfield.esm", "B.esm"))

    items = [
        _item("A.esm", 0, categories=["Cheats"]),     # tier 11
        _item("B.esm", 1, categories=["Gameplay"]),    # tier 5
        _item("C.esm", 2, categories=["Overhaul"]),    # tier 3
    ]
    plugins = {"A.esm": "1", "B.esm": "2", "C.esm": "3"}

    result = sort_creations(
        items,
        sorters=["category", "tes4"],
        data_dir=tmp_path,
        installed_plugins=plugins,
    )

    names = [si.plugin_name for si in result.items]
    assert names.index("C.esm") < names.index("B.esm") < names.index("A.esm")
