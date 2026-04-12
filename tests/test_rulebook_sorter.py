"""Tests for rule book sorter integration."""
import json

from load_order_sorter.models import SortItem
from load_order_sorter.pipeline import sort_creations
from load_order_sorter.sorters.rulebook import (
    PRIORITY_CURATED,
    PRIORITY_USER_BASE,
    sort,
)


def _item(name, index=0, categories=None):
    return SortItem(
        plugin_name=name,
        content_id=name,
        display_name=name,
        categories=categories or [],
        original_index=index,
    )


def _make_book(name, rules):
    return {"name": name, "description": "test", "version": "1.0", "rules": rules}


# --- Sorter constraint generation ---


def test_user_book_produces_constraints(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    book = _make_book("Test", [
        {"plugin": "B.esm", "load_after": ["A.esm"]}
    ])
    (user_dir / "test.json").write_text(json.dumps(book), encoding="utf-8")

    items = [_item("A.esm", 0), _item("B.esm", 1)]
    plugins = {"A.esm": "1", "B.esm": "2"}
    registry = [{"filename": "test.json", "source": "user", "enabled": True}]

    constraints = sort(items, user_dir, registry=registry, installed_plugins=plugins)
    assert len(constraints) == 1
    assert constraints[0].plugin_name == "B.esm"
    assert constraints[0].after == "A.esm"
    assert constraints[0].priority >= PRIORITY_USER_BASE


def test_curated_book_lower_priority(tmp_path):
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    book = _make_book("Curated", [
        {"plugin": "B.esm", "load_after": ["A.esm"]}
    ])
    (curated_dir / "001_test.json").write_text(json.dumps(book), encoding="utf-8")

    user_dir = tmp_path / "rules"
    user_dir.mkdir()

    items = [_item("A.esm"), _item("B.esm")]
    plugins = {"A.esm": "1", "B.esm": "2"}
    registry = [{"filename": "001_test.json", "source": "curated", "enabled": True}]

    constraints = sort(items, user_dir, curated_dir, registry, plugins)
    assert len(constraints) == 1
    assert constraints[0].priority == PRIORITY_CURATED


def test_disabled_book_skipped(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    book = _make_book("Test", [
        {"plugin": "B.esm", "load_after": ["A.esm"]}
    ])
    (user_dir / "test.json").write_text(json.dumps(book), encoding="utf-8")

    items = [_item("A.esm"), _item("B.esm")]
    plugins = {"A.esm": "1", "B.esm": "2"}
    registry = [{"filename": "test.json", "source": "user", "enabled": False}]

    constraints = sort(items, user_dir, registry=registry, installed_plugins=plugins)
    assert constraints == []


def test_inapplicable_book_skipped(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    book = _make_book("Test", [
        {"plugin": "Missing.esm", "load_after": ["Also.Missing.esm"]}
    ])
    (user_dir / "test.json").write_text(json.dumps(book), encoding="utf-8")

    items = [_item("A.esm")]
    plugins = {"A.esm": "1"}
    registry = [{"filename": "test.json", "source": "user", "enabled": True}]

    constraints = sort(items, user_dir, registry=registry, installed_plugins=plugins)
    assert constraints == []


def test_corrupted_book_skipped(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    (user_dir / "bad.json").write_text("{corrupt!", encoding="utf-8")

    items = [_item("A.esm")]
    plugins = {"A.esm": "1"}
    registry = [{"filename": "bad.json", "source": "user", "enabled": True}]

    constraints = sort(items, user_dir, registry=registry, installed_plugins=plugins)
    assert constraints == []


def test_load_before_produces_correct_constraints(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    book = _make_book("Test", [
        {"plugin": "Patch.esm", "load_after": ["Base.esm"], "load_before": ["Overhaul.esm"]}
    ])
    (user_dir / "test.json").write_text(json.dumps(book), encoding="utf-8")

    items = [_item("Base.esm"), _item("Patch.esm"), _item("Overhaul.esm")]
    plugins = {"Base.esm": "1", "Patch.esm": "2", "Overhaul.esm": "3"}
    registry = [{"filename": "test.json", "source": "user", "enabled": True}]

    constraints = sort(items, user_dir, registry=registry, installed_plugins=plugins)
    after_map = {(c.plugin_name, c.after) for c in constraints}
    assert ("Patch.esm", "Base.esm") in after_map
    assert ("Overhaul.esm", "Patch.esm") in after_map


def test_user_beats_curated_on_conflict(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()

    # Curated says B after A
    (curated_dir / "001.json").write_text(
        json.dumps(_make_book("C", [{"plugin": "B.esm", "load_after": ["A.esm"]}])),
        encoding="utf-8",
    )
    # User says A after B (conflict!)
    (user_dir / "mine.json").write_text(
        json.dumps(_make_book("U", [{"plugin": "A.esm", "load_after": ["B.esm"]}])),
        encoding="utf-8",
    )

    items = [_item("A.esm"), _item("B.esm")]
    plugins = {"A.esm": "1", "B.esm": "2"}
    registry = [
        {"filename": "mine.json", "source": "user", "enabled": True},
        {"filename": "001.json", "source": "curated", "enabled": True},
    ]

    constraints = sort(items, user_dir, curated_dir, registry, plugins)
    # Both constraints present; user has higher priority
    user_c = [c for c in constraints if c.plugin_name == "A.esm"]
    curated_c = [c for c in constraints if c.plugin_name == "B.esm"]
    assert user_c[0].priority > curated_c[0].priority


# --- Tier-type rule books ---


def test_tier_book_produces_tier_constraints(tmp_path):
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    book = {"name": "Tiers", "type": "tier", "rules": [
        {"plugin": "PDY.esm", "tier": 3, "note": "ship builder overhaul"},
    ]}
    (curated_dir / "000_tiers.json").write_text(
        json.dumps(book), encoding="utf-8"
    )

    user_dir = tmp_path / "rules"
    user_dir.mkdir()

    items = [_item("PDY.esm")]
    plugins = {"PDY.esm": "1"}
    registry = [{"filename": "000_tiers.json", "source": "curated", "enabled": True}]

    constraints = sort(items, user_dir, curated_dir, registry, plugins)
    assert len(constraints) == 1
    assert constraints[0].type == "tier"
    assert constraints[0].tier == 3
    assert constraints[0].plugin_name == "PDY.esm"
    assert constraints[0].priority == PRIORITY_CURATED


def test_tier_book_missing_plugin_skipped(tmp_path):
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    book = {"name": "Tiers", "type": "tier", "rules": [
        {"plugin": "NotInstalled.esm", "tier": 3},
    ]}
    (curated_dir / "000_tiers.json").write_text(
        json.dumps(book), encoding="utf-8"
    )

    user_dir = tmp_path / "rules"
    user_dir.mkdir()

    items = [_item("A.esm")]
    plugins = {"A.esm": "1"}
    registry = [{"filename": "000_tiers.json", "source": "curated", "enabled": True}]

    constraints = sort(items, user_dir, curated_dir, registry, plugins)
    assert constraints == []


def test_tier_book_user_beats_curated(tmp_path):
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    user_dir = tmp_path / "rules"
    user_dir.mkdir()

    # Curated says tier 5
    (curated_dir / "000_tiers.json").write_text(json.dumps(
        {"name": "C", "type": "tier", "rules": [{"plugin": "X.esm", "tier": 5}]}
    ), encoding="utf-8")
    # User says tier 3
    (user_dir / "my_tiers.json").write_text(json.dumps(
        {"name": "U", "type": "tier", "rules": [{"plugin": "X.esm", "tier": 3}]}
    ), encoding="utf-8")

    items = [_item("X.esm")]
    plugins = {"X.esm": "1"}
    registry = [
        {"filename": "my_tiers.json", "source": "user", "enabled": True},
        {"filename": "000_tiers.json", "source": "curated", "enabled": True},
    ]

    constraints = sort(items, user_dir, curated_dir, registry, plugins)
    # Both constraints present; user has higher priority so wins in merger
    user_c = [c for c in constraints if c.priority >= PRIORITY_USER_BASE]
    curated_c = [c for c in constraints if c.priority == PRIORITY_CURATED]
    assert len(user_c) == 1
    assert user_c[0].tier == 3
    assert len(curated_c) == 1
    assert curated_c[0].tier == 5
    assert user_c[0].priority > curated_c[0].priority


def test_order_book_ignores_tier_field(tmp_path):
    """An order-type book with tier fields in rules should not emit tier constraints."""
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    # Order book (default type) with a tier field — should be ignored
    book = _make_book("Test", [
        {"plugin": "B.esm", "load_after": ["A.esm"], "tier": 3}
    ])
    (user_dir / "test.json").write_text(json.dumps(book), encoding="utf-8")

    items = [_item("A.esm"), _item("B.esm")]
    plugins = {"A.esm": "1", "B.esm": "2"}
    registry = [{"filename": "test.json", "source": "user", "enabled": True}]

    constraints = sort(items, user_dir, registry=registry, installed_plugins=plugins)
    assert all(c.type == "load_after" for c in constraints)


# --- End-to-end with pipeline ---


def test_sort_creations_with_rulebook(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    book = _make_book("Test", [
        {"plugin": "B.esm", "load_after": ["A.esm"]}
    ])
    (user_dir / "test.json").write_text(json.dumps(book), encoding="utf-8")

    items = [
        _item("B.esm", 0, categories=["Gear"]),
        _item("A.esm", 1, categories=["Gear"]),
    ]
    plugins = {"A.esm": "1", "B.esm": "2"}
    registry = [{"filename": "test.json", "source": "user", "enabled": True}]

    result = sort_creations(
        items,
        sorters=["category", "rulebook"],
        user_rules_dir=user_dir,
        installed_plugins=plugins,
        rulebook_registry=registry,
    )

    names = [si.plugin_name for si in result.items]
    assert names.index("A.esm") < names.index("B.esm")


def test_tier_book_overrides_category_in_pipeline(tmp_path):
    """Tier book at priority 30 beats category sorter at priority 10.

    Simulates the PDY/Falkland scenario: PDY is categorized as Gameplay
    (tier 5) but a tier book overrides it to tier 3.  With both in tier 3,
    a load_after rule keeps them ordered without cross-tier promotion.
    """
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    user_dir = tmp_path / "rules"
    user_dir.mkdir()

    # Tier book: move PDY from Gameplay (tier 5) to tier 3
    (curated_dir / "000_tiers.json").write_text(json.dumps(
        {"name": "Tier Fix", "type": "tier", "rules": [
            {"plugin": "PDY.esm", "tier": 3},
        ]}
    ), encoding="utf-8")

    # Order book: Falkland loads after PDY
    (curated_dir / "001_order.json").write_text(json.dumps(
        {"name": "Order", "rules": [
            {"plugin": "Falkland.esm", "load_after": ["PDY.esm"]},
        ]}
    ), encoding="utf-8")

    items = [
        _item("Falkland.esm", 0, categories=["World"]),   # cat → tier 3
        _item("PDY.esm", 1, categories=["Gameplay"]),      # cat → tier 5, tier book → 3
        _item("Other.esm", 2, categories=["Gameplay"]),    # cat → tier 5, stays
    ]
    plugins = {"Falkland.esm": "1", "PDY.esm": "2", "Other.esm": "3"}
    registry = [
        {"filename": "000_tiers.json", "source": "curated", "enabled": True},
        {"filename": "001_order.json", "source": "curated", "enabled": True},
    ]

    result = sort_creations(
        items,
        sorters=["category", "rulebook"],
        user_rules_dir=user_dir,
        curated_rules_dir=curated_dir,
        installed_plugins=plugins,
        rulebook_registry=registry,
    )

    names = [si.plugin_name for si in result.items]
    # PDY and Falkland both in tier 3, with Falkland after PDY
    assert names.index("PDY.esm") < names.index("Falkland.esm")
    # Other stays in tier 5, so after both tier 3 items
    assert names.index("Falkland.esm") < names.index("Other.esm")
    # Falkland should NOT be promoted to tier 5 (the old bug)
    falkland_item = next(si for si in result.items if si.plugin_name == "Falkland.esm")
    assert falkland_item.decision.tier == 3


# --- Sorter name carries rulebook filename ---


def test_order_sorter_name_includes_filename(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    book = _make_book("Test", [
        {"plugin": "B.esm", "load_after": ["A.esm"], "note": "because reasons"}
    ])
    (user_dir / "my_book.json").write_text(json.dumps(book), encoding="utf-8")

    items = [_item("A.esm"), _item("B.esm")]
    plugins = {"A.esm": "1", "B.esm": "2"}
    registry = [{"filename": "my_book.json", "source": "user", "enabled": True}]

    constraints = sort(items, user_dir, registry=registry, installed_plugins=plugins)
    assert len(constraints) == 1
    assert constraints[0].sorter_name == "RULE:my_book.json"
    assert constraints[0].note == "because reasons"


def test_tier_sorter_name_includes_filename_and_tier(tmp_path):
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    book = {"name": "Tiers", "type": "tier", "rules": [
        {"plugin": "X.esm", "tier": 3, "note": "ship overhaul"},
    ]}
    (curated_dir / "000_tiers.json").write_text(json.dumps(book), encoding="utf-8")

    user_dir = tmp_path / "rules"
    user_dir.mkdir()

    items = [_item("X.esm")]
    plugins = {"X.esm": "1"}
    registry = [{"filename": "000_tiers.json", "source": "curated", "enabled": True}]

    constraints = sort(items, user_dir, curated_dir, registry, plugins)
    assert len(constraints) == 1
    assert constraints[0].sorter_name == "RULE:000_tiers.json(3)"
    assert constraints[0].note == "ship overhaul"


def test_empty_note_yields_empty_string(tmp_path):
    user_dir = tmp_path / "rules"
    user_dir.mkdir()
    book = _make_book("Test", [
        {"plugin": "B.esm", "load_after": ["A.esm"]},  # no note
    ])
    (user_dir / "test.json").write_text(json.dumps(book), encoding="utf-8")

    items = [_item("A.esm"), _item("B.esm")]
    plugins = {"A.esm": "1", "B.esm": "2"}
    registry = [{"filename": "test.json", "source": "user", "enabled": True}]

    constraints = sort(items, user_dir, registry=registry, installed_plugins=plugins)
    assert constraints[0].note == ""
