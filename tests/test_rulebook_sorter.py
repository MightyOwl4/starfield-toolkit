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
