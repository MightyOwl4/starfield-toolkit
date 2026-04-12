"""Tests for rule book I/O, normalization, applicability, discovery, and registry."""
import json
import time

from load_order_sorter.rulebook import (
    check_applicability,
    check_tier_applicability,
    discover_rulebooks,
    load_rulebook,
    normalize_rules,
    reconcile_registry,
    save_rulebook,
)


def _make_book(name="Test", rules=None):
    return {"name": name, "description": "test", "version": "1.0", "rules": rules or []}


# --- load/save ---


def test_load_valid_json(tmp_path):
    f = tmp_path / "book.json"
    f.write_text(json.dumps(_make_book()), encoding="utf-8")
    result = load_rulebook(f)
    assert result is not None
    assert result["name"] == "Test"


def test_load_corrupted_returns_none(tmp_path):
    f = tmp_path / "book.json"
    f.write_text("{bad json!", encoding="utf-8")
    assert load_rulebook(f) is None


def test_load_missing_name_returns_none(tmp_path):
    f = tmp_path / "book.json"
    f.write_text(json.dumps({"rules": []}), encoding="utf-8")
    assert load_rulebook(f) is None


def test_load_missing_rules_returns_none(tmp_path):
    f = tmp_path / "book.json"
    f.write_text(json.dumps({"name": "X"}), encoding="utf-8")
    assert load_rulebook(f) is None


def test_load_missing_file(tmp_path):
    assert load_rulebook(tmp_path / "nope.json") is None


def test_save_creates_file(tmp_path):
    f = tmp_path / "book.json"
    save_rulebook(_make_book(), f)
    assert f.exists()
    loaded = json.loads(f.read_text(encoding="utf-8"))
    assert loaded["name"] == "Test"


def test_save_creates_parent_dirs(tmp_path):
    f = tmp_path / "sub" / "dir" / "book.json"
    save_rulebook(_make_book(), f)
    assert f.exists()


# --- normalize_rules ---


def test_normalize_load_after_preserved():
    rules = [{"plugin": "A.esm", "load_after": ["B.esm"]}]
    result = normalize_rules(rules)
    assert len(result) == 1
    assert result[0]["plugin"] == "A.esm"
    assert result[0]["load_after"] == ["B.esm"]


def test_normalize_load_before_converted():
    rules = [{"plugin": "A.esm", "load_before": ["B.esm"]}]
    result = normalize_rules(rules)
    # A.load_before=[B] → B.load_after=[A]
    b_rule = next(r for r in result if r["plugin"] == "B.esm")
    assert "A.esm" in b_rule["load_after"]


def test_normalize_combined_after_and_before():
    rules = [{
        "plugin": "Patch.esm",
        "load_after": ["Base.esm"],
        "load_before": ["Overhaul.esm"],
    }]
    result = normalize_rules(rules)
    patch_rule = next(r for r in result if r["plugin"] == "Patch.esm")
    assert "Base.esm" in patch_rule["load_after"]
    overhaul_rule = next(r for r in result if r["plugin"] == "Overhaul.esm")
    assert "Patch.esm" in overhaul_rule["load_after"]


def test_normalize_empty_rules():
    assert normalize_rules([]) == []


def test_normalize_merges_duplicates():
    rules = [
        {"plugin": "A.esm", "load_after": ["B.esm"]},
        {"plugin": "A.esm", "load_after": ["C.esm"]},
    ]
    result = normalize_rules(rules)
    a_rule = next(r for r in result if r["plugin"] == "A.esm")
    assert set(a_rule["load_after"]) == {"B.esm", "C.esm"}


# --- check_applicability ---


def test_applicability_all_installed():
    rules = [{"plugin": "A.esm", "load_after": ["B.esm"]}]
    applicable, missing, is_ok = check_applicability(rules, {"A.esm", "B.esm"})
    assert len(applicable) == 1
    assert missing == set()
    assert is_ok is True


def test_applicability_missing_target():
    rules = [{"plugin": "A.esm", "load_after": ["B.esm", "C.esm"]}]
    applicable, missing, is_ok = check_applicability(rules, {"A.esm", "B.esm"})
    assert len(applicable) == 1
    assert applicable[0]["load_after"] == ["B.esm"]
    assert "C.esm" in missing
    assert is_ok is True


def test_applicability_missing_plugin():
    rules = [{"plugin": "A.esm", "load_after": ["B.esm"]}]
    applicable, missing, is_ok = check_applicability(rules, {"B.esm"})
    assert len(applicable) == 0
    assert "A.esm" in missing
    assert is_ok is False


def test_applicability_all_missing():
    rules = [{"plugin": "A.esm", "load_after": ["B.esm"]}]
    applicable, missing, is_ok = check_applicability(rules, set())
    assert is_ok is False


def test_applicability_case_insensitive():
    rules = [{"plugin": "mymod.esm", "load_after": ["BASE.ESM"]}]
    applicable, missing, is_ok = check_applicability(
        rules, {"MyMod.esm", "base.esm"}
    )
    assert is_ok is True
    assert len(applicable) == 1


# --- discover_rulebooks ---


def test_discover_user_sorted_by_date(tmp_path):
    f1 = tmp_path / "old.json"
    f1.write_text(json.dumps(_make_book("Old")), encoding="utf-8")
    time.sleep(0.05)
    f2 = tmp_path / "new.json"
    f2.write_text(json.dumps(_make_book("New")), encoding="utf-8")

    result = discover_rulebooks(tmp_path)
    assert result[0]["filename"] == "new.json"  # newest first
    assert result[1]["filename"] == "old.json"


def test_discover_curated_sorted_by_name(tmp_path):
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    (curated_dir / "010_second.json").write_text(
        json.dumps(_make_book()), encoding="utf-8"
    )
    (curated_dir / "001_first.json").write_text(
        json.dumps(_make_book()), encoding="utf-8"
    )

    result = discover_rulebooks(user_dir, curated_dir)
    assert result[0]["filename"] == "001_first.json"
    assert result[1]["filename"] == "010_second.json"


def test_discover_mixed_sources(tmp_path):
    user_dir = tmp_path / "user"
    user_dir.mkdir()
    curated_dir = tmp_path / "curated"
    curated_dir.mkdir()
    (user_dir / "my.json").write_text(json.dumps(_make_book()), encoding="utf-8")
    (curated_dir / "001.json").write_text(json.dumps(_make_book()), encoding="utf-8")

    result = discover_rulebooks(user_dir, curated_dir)
    assert result[0]["source"] == "user"
    assert result[1]["source"] == "curated"


def test_discover_empty_dirs(tmp_path):
    assert discover_rulebooks(tmp_path / "nope") == []


# --- reconcile_registry ---


def test_reconcile_new_files_at_top():
    discovered = [
        {"filename": "new.json", "source": "user"},
        {"filename": "old.json", "source": "user"},
    ]
    saved = [{"filename": "old.json", "source": "user", "enabled": True}]
    result = reconcile_registry(discovered, saved)
    assert result[0]["filename"] == "new.json"
    assert result[0]["enabled"] is True  # default enabled
    assert result[1]["filename"] == "old.json"


def test_reconcile_stale_removed():
    discovered = [{"filename": "exists.json", "source": "user"}]
    saved = [
        {"filename": "exists.json", "source": "user", "enabled": True},
        {"filename": "gone.json", "source": "user", "enabled": True},
    ]
    result = reconcile_registry(discovered, saved)
    assert len(result) == 1
    assert result[0]["filename"] == "exists.json"


def test_reconcile_preserves_enabled_state():
    discovered = [{"filename": "book.json", "source": "user"}]
    saved = [{"filename": "book.json", "source": "user", "enabled": False}]
    result = reconcile_registry(discovered, saved)
    assert result[0]["enabled"] is False


def test_reconcile_curated_below_user():
    discovered = [
        {"filename": "user.json", "source": "user"},
        {"filename": "001.json", "source": "curated"},
    ]
    saved = []
    result = reconcile_registry(discovered, saved)
    assert result[0]["source"] == "user"
    assert result[1]["source"] == "curated"


def test_reconcile_saved_order_preserved():
    discovered = [
        {"filename": "a.json", "source": "user"},
        {"filename": "b.json", "source": "user"},
    ]
    # Saved order is b before a
    saved = [
        {"filename": "b.json", "source": "user", "enabled": True},
        {"filename": "a.json", "source": "user", "enabled": True},
    ]
    result = reconcile_registry(discovered, saved)
    assert result[0]["filename"] == "b.json"
    assert result[1]["filename"] == "a.json"


# --- check_tier_applicability ---


def test_tier_applicability_installed():
    rules = [{"plugin": "A.esm", "tier": 3}]
    applicable, missing, is_ok = check_tier_applicability(rules, {"A.esm"})
    assert len(applicable) == 1
    assert applicable[0]["tier"] == 3
    assert is_ok is True


def test_tier_applicability_missing_plugin():
    rules = [{"plugin": "A.esm", "tier": 3}]
    applicable, missing, is_ok = check_tier_applicability(rules, {"B.esm"})
    assert len(applicable) == 0
    assert "A.esm" in missing
    assert is_ok is False


def test_tier_applicability_invalid_tier_skipped():
    rules = [
        {"plugin": "A.esm", "tier": 99},
        {"plugin": "B.esm", "tier": 0},
        {"plugin": "C.esm", "tier": "bad"},
        {"plugin": "D.esm", "tier": 5},
    ]
    applicable, _, is_ok = check_tier_applicability(
        rules, {"A.esm", "B.esm", "C.esm", "D.esm"}
    )
    assert len(applicable) == 1
    assert applicable[0]["plugin"] == "D.esm"
    assert is_ok is True


def test_tier_applicability_case_insensitive():
    rules = [{"plugin": "mymod.esm", "tier": 7}]
    applicable, _, is_ok = check_tier_applicability(rules, {"MyMod.esm"})
    assert is_ok is True
    assert applicable[0]["plugin"] == "MyMod.esm"


def test_tier_applicability_preserves_note():
    rules = [{"plugin": "A.esm", "tier": 3, "note": "overhaul mod"}]
    applicable, _, _ = check_tier_applicability(rules, {"A.esm"})
    assert applicable[0]["note"] == "overhaul mod"
