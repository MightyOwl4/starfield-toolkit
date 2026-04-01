"""Tests for the load_order_sorter package."""
import json
from pathlib import Path

import yaml

from load_order_sorter import sort_creations, save_snapshot, load_snapshot
from load_order_sorter.models import SortItem, SortConstraint, SortDecision
from load_order_sorter.sorters.category import sort as category_sort
from load_order_sorter.sorters.loot import sort as loot_sort
from load_order_sorter.pipeline import _merge_constraints, _solve


def _item(name, content_id="", categories=None, index=0, author=""):
    return SortItem(
        plugin_name=name,
        content_id=content_id or name,
        display_name=name,
        categories=categories or [],
        author=author,
        original_index=index,
    )


class TestCategorySorter:
    def test_sfbgs_no_special_tier(self):
        """SFBGS prefix no longer gets special tier-1 treatment."""
        items = [_item("SFBGS006.esm", "SFBGS006")]
        constraints = category_sort(items)
        assert constraints[0].tier == 9  # default — no categories mapped

    def test_quest_category_gets_tier3(self):
        items = [_item("mod.esm", "TM_abc", categories=["Quests"])]
        constraints = category_sort(items)
        assert constraints[0].tier == 3

    def test_unknown_category_gets_default(self):
        items = [_item("mod.esm", "TM_xyz", categories=["SomeNewCategory"])]
        constraints = category_sort(items)
        assert constraints[0].tier == 9

    def test_multi_category_uses_lowest_tier(self):
        items = [_item("mod.esm", "TM_abc", categories=["Gear", "Quests"])]
        constraints = category_sort(items)
        # Quests=3, Gear=10 → should pick 3
        assert constraints[0].tier == 3

    def test_no_categories_gets_default(self):
        items = [_item("mod.esm", "TM_abc")]
        constraints = category_sort(items)
        assert constraints[0].tier == 9

    def test_bethesda_author_sorts_by_category(self):
        """BGS marketplace creations sort by content category, not tier 1."""
        items = [_item("mod.esm", "TM_abc", author="BethesdaGameStudios",
                        categories=["Skins"])]
        constraints = category_sort(items)
        assert constraints[0].tier == 10  # Skins tier, not pinned to 1

    def test_sfbgs_prefix_gets_default_tier(self):
        """SFBGS items without categories get the default tier (not special-cased)."""
        items = [_item("Starfield.esm", "SFBGS001")]
        constraints = category_sort(items)
        assert constraints[0].tier == 9  # default, no special tier-1 override


class TestLootSorter:
    def test_parses_masterlist(self, tmp_path):
        masterlist = {
            "plugins": [
                {
                    "name": "mymod.esm",
                    "group": "Late Loaders",
                    "after": [{"name": "base.esm"}],
                    "msg": [{"type": "warn", "content": "Needs patch"}],
                }
            ]
        }
        ml_path = tmp_path / "masterlist.yaml"
        ml_path.write_text(yaml.dump(masterlist), encoding="utf-8")

        items = [
            _item("mymod.esm", index=0),
            _item("base.esm", index=1),
        ]
        constraints = loot_sort(items, ml_path)

        # Should have tier constraint + load_after constraint
        tier_c = [c for c in constraints if c.type == "tier"]
        after_c = [c for c in constraints if c.type == "load_after"]
        assert len(tier_c) == 1
        assert tier_c[0].tier == 11  # Late Loaders
        assert tier_c[0].warnings == ["Needs patch"]
        assert len(after_c) == 1
        assert after_c[0].after == "base.esm"

    def test_missing_file_returns_empty(self, tmp_path):
        items = [_item("mod.esm")]
        constraints = loot_sort(items, tmp_path / "nonexistent.yaml")
        assert constraints == []

    def test_corrupt_yaml_returns_empty(self, tmp_path):
        bad = tmp_path / "bad.yaml"
        bad.write_text("{{{{not yaml", encoding="utf-8")
        constraints = loot_sort([_item("mod.esm")], bad)
        assert constraints == []


class TestConstraintMerger:
    def test_higher_priority_tier_wins(self):
        constraints = [
            SortConstraint(plugin_name="mod.esm", type="tier", tier=9,
                           sorter_name="CAT", priority=10),
            SortConstraint(plugin_name="mod.esm", type="tier", tier=3,
                           sorter_name="LOOT", priority=20),
        ]
        decisions = _merge_constraints(constraints)
        assert decisions["mod.esm"].tier == 3
        assert decisions["mod.esm"].sorter_name == "LOOT"

    def test_load_after_accumulated(self):
        constraints = [
            SortConstraint(plugin_name="c.esm", type="load_after",
                           after="a.esm", sorter_name="CAT", priority=10),
            SortConstraint(plugin_name="c.esm", type="load_after",
                           after="b.esm", sorter_name="LOOT", priority=20),
        ]
        decisions = _merge_constraints(constraints)
        assert set(decisions["c.esm"].load_after) == {"a.esm", "b.esm"}

    def test_warnings_merged(self):
        constraints = [
            SortConstraint(plugin_name="mod.esm", type="tier", tier=5,
                           sorter_name="CAT", priority=10, warnings=["w1"]),
            SortConstraint(plugin_name="mod.esm", type="tier", tier=3,
                           sorter_name="LOOT", priority=20, warnings=["w2"]),
        ]
        decisions = _merge_constraints(constraints)
        assert decisions["mod.esm"].warnings == ["w1", "w2"]


class TestSolver:
    def test_stable_sort_unsorted_items(self):
        items = [_item("a.esm", index=0), _item("b.esm", index=1),
                 _item("c.esm", index=2)]
        # No decisions — all go to default tier, preserve order
        result = _solve(items, {})
        names = [si.plugin_name for si in result]
        assert names == ["a.esm", "b.esm", "c.esm"]
        assert all(not si.moved for si in result)

    def test_tier_ordering(self):
        items = [_item("gear.esm", index=0), _item("quest.esm", index=1),
                 _item("bgs.esm", index=2)]
        decisions = {
            "gear.esm": SortDecision(tier=10, sorter_name="CAT"),
            "quest.esm": SortDecision(tier=3, sorter_name="CAT"),
            "bgs.esm": SortDecision(tier=1, sorter_name="CAT"),
        }
        result = _solve(items, decisions)
        names = [si.plugin_name for si in result]
        assert names == ["bgs.esm", "quest.esm", "gear.esm"]

    def test_load_after_within_tier(self):
        items = [_item("a.esm", index=0), _item("b.esm", index=1)]
        decisions = {
            "a.esm": SortDecision(tier=5, load_after=["b.esm"]),
            "b.esm": SortDecision(tier=5),
        }
        result = _solve(items, decisions)
        names = [si.plugin_name for si in result]
        assert names == ["b.esm", "a.esm"]  # a must come after b

    def test_unsorted_preserve_relative_order(self):
        items = [
            _item("x.esm", index=0), _item("sorted.esm", index=1),
            _item("y.esm", index=2), _item("z.esm", index=3),
        ]
        # Only sorted.esm gets a tier assignment (tier 1)
        decisions = {
            "sorted.esm": SortDecision(tier=1, sorter_name="CAT"),
        }
        result = _solve(items, decisions)
        names = [si.plugin_name for si in result]
        # sorted.esm should be first (tier 1), then x, y, z in original order (tier 9)
        assert names[0] == "sorted.esm"
        unsorted = [n for n in names if n != "sorted.esm"]
        assert unsorted == ["x.esm", "y.esm", "z.esm"]


class TestSortCreations:
    def test_end_to_end_category_only(self):
        items = [
            _item("gear.esm", "TM_1", ["Gear"], 0),
            _item("misc.esm", "TM_3", [], 1),
            _item("quest.esm", "TM_2", ["Quests"], 2),
        ]
        result = sort_creations(items, sorters=["category"])
        names = [si.plugin_name for si in result.items]
        # quest tier3, misc default tier9, gear tier10
        assert names == ["quest.esm", "misc.esm", "gear.esm"]
        assert not result.unchanged

    def test_unchanged_order(self):
        items = [
            _item("quest.esm", "TM_1", ["Quests"], 0),
            _item("misc.esm", "TM_3", [], 1),
            _item("gear.esm", "TM_2", ["Gear"], 2),
        ]
        result = sort_creations(items, sorters=["category"])
        assert result.unchanged

    def test_loot_overrides_category(self, tmp_path):
        masterlist = {
            "plugins": [
                {"name": "mod.esm", "group": "Late Loaders"}
            ]
        }
        ml_path = tmp_path / "masterlist.yaml"
        ml_path.write_text(yaml.dump(masterlist), encoding="utf-8")

        items = [
            _item("mod.esm", "TM_1", ["Quests"], 0),  # CAT=tier3
            _item("other.esm", "TM_2", ["Gear"], 1),   # CAT=tier10
        ]
        result = sort_creations(items, sorters=["category", "loot"],
                                masterlist_path=ml_path)
        names = [si.plugin_name for si in result.items]
        # mod.esm: LOOT says tier11, overrides CAT tier3
        # other.esm: only CAT, tier10
        assert names == ["other.esm", "mod.esm"]
        # Verify attribution
        mod_item = [si for si in result.items if si.plugin_name == "mod.esm"][0]
        assert mod_item.decision.sorter_name == "LOOT(11)"


class TestSnapshot:
    def test_round_trip(self, tmp_path):
        from load_order_sorter.models import SnapshotEntry
        path = tmp_path / "snapshot.json"
        entries = [
            SnapshotEntry("SFBGS006", "Starborn Gravis Suit", ["SFBGS006.esm"]),
            SnapshotEntry("TM_abc", "Trackers Alliance", ["sfta01.esm", "sfta02.esm"]),
        ]
        save_snapshot("Test Order", entries, path, "1.0")

        snap = load_snapshot(path)
        assert snap.name == "Test Order"
        assert len(snap.entries) == 2
        assert snap.entries[0].content_id == "SFBGS006"
        assert snap.entries[0].display_name == "Starborn Gravis Suit"
        assert snap.entries[0].files == ["SFBGS006.esm"]
        assert snap.entries[1].files == ["sfta01.esm", "sfta02.esm"]
        assert snap.tool_version == "1.0"
        assert snap.created != ""

    def test_legacy_format(self, tmp_path):
        """Load a snapshot saved in the old plain-filenames format."""
        f = tmp_path / "legacy.json"
        f.write_text(json.dumps({
            "name": "old", "plugins": ["a.esm", "b.esm"],
        }), encoding="utf-8")
        snap = load_snapshot(f)
        assert len(snap.entries) == 2
        assert snap.entries[0].content_id == "a.esm"
        assert snap.entries[0].files == ["a.esm"]

    def test_invalid_file_raises(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        try:
            load_snapshot(bad)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_missing_fields_raises(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text(json.dumps({"name": "test"}), encoding="utf-8")
        try:
            load_snapshot(f)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
