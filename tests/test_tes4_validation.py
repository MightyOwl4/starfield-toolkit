"""Tests for TES4 pre-write validation logic."""
from load_order_sorter.validation import (
    ValidationViolation,
    format_violations,
    validate_tes4_order,
)


# --- validate_tes4_order tests ---


def test_valid_order_returns_empty():
    order = ["Base.esm", "Addon.esm"]
    master_map = {"Addon.esm": ["Base.esm"]}
    assert validate_tes4_order(order, master_map) == []


def test_single_violation_detected():
    order = ["Addon.esm", "Base.esm"]  # wrong: Addon before its master
    master_map = {"Addon.esm": ["Base.esm"]}
    violations = validate_tes4_order(order, master_map)

    assert len(violations) == 1
    v = violations[0]
    assert v.plugin_name == "Addon.esm"
    assert v.master_name == "Base.esm"
    assert v.current_position == 0
    assert v.master_position == 1


def test_multiple_violations():
    order = ["C.esm", "B.esm", "A.esm"]
    master_map = {
        "C.esm": ["A.esm"],  # C before A → violation
        "B.esm": ["A.esm"],  # B before A → violation
    }
    violations = validate_tes4_order(order, master_map)
    assert len(violations) == 2


def test_chain_violation():
    order = ["C.esm", "B.esm", "A.esm"]  # all reversed
    master_map = {
        "B.esm": ["A.esm"],  # B depends on A
        "C.esm": ["B.esm"],  # C depends on B
    }
    violations = validate_tes4_order(order, master_map)
    # C before B → violation, B before A → violation
    assert len(violations) == 2


def test_no_masters_means_no_violations():
    order = ["A.esm", "B.esm", "C.esm"]
    master_map = {}  # no dependencies
    assert validate_tes4_order(order, master_map) == []


def test_master_not_in_order_ignored():
    order = ["Addon.esm"]
    master_map = {"Addon.esm": ["NotInOrder.esm"]}
    # NotInOrder.esm not in the plugin_order → no violation
    assert validate_tes4_order(order, master_map) == []


def test_display_names_included():
    order = ["Addon.esm", "Base.esm"]
    master_map = {"Addon.esm": ["Base.esm"]}
    names = {"Addon.esm": "Cool Addon", "Base.esm": "Base Mod"}
    violations = validate_tes4_order(order, master_map, display_names=names)

    assert violations[0].display_name == "Cool Addon"
    assert violations[0].master_display_name == "Base Mod"


def test_display_names_fallback_to_filename():
    order = ["Addon.esm", "Base.esm"]
    master_map = {"Addon.esm": ["Base.esm"]}
    violations = validate_tes4_order(order, master_map)  # no display_names

    assert violations[0].display_name == "Addon.esm"
    assert violations[0].master_display_name == "Base.esm"


# --- format_violations tests ---


def test_format_empty_violations():
    assert format_violations([]) == ""


def test_format_single_violation():
    violations = [
        ValidationViolation(
            plugin_name="Addon.esm",
            display_name="Cool Addon",
            master_name="Base.esm",
            master_display_name="Base Mod",
            current_position=0,
            master_position=1,
        )
    ]
    msg = format_violations(violations)
    assert "Cool Addon" in msg
    assert "Base Mod" in msg
    assert "Auto Sort" in msg


def test_format_max_shown():
    violations = [
        ValidationViolation(
            plugin_name=f"Mod{i}.esm",
            display_name=f"Mod {i}",
            master_name="Base.esm",
            master_display_name="Base",
            current_position=0,
            master_position=i + 1,
        )
        for i in range(8)
    ]
    msg = format_violations(violations, max_shown=5)
    assert "Mod 0" in msg
    assert "Mod 4" in msg
    assert "3 more" in msg  # 8 - 5 = 3
    assert "Mod 5" not in msg
