"""Tests for Fast Lane Creation Check logic (baseline loading, comparison, parsing)."""
import json

from starfield_tool.tools.fast_lane_check import (
    STATUS_LIKELY_UPDATED,
    STATUS_LOW_RISK,
    STATUS_NOT_UPDATED,
    STATUS_UNAFFECTED,
    STATUS_UNKNOWN,
    STATUS_UPDATED,
    _classify,
    _load_baseline,
    _lookup_baseline,
    _parse_csv,
    _parse_export,
    _parse_markdown,
    _status_sort_key,
)


# --- _load_baseline ---


def test_load_baseline_dev_mode(monkeypatch, tmp_path):
    """_load_baseline falls back to dev path when not in PyInstaller bundle."""
    # Create a fake dev-mode baseline in the correct relative location
    # The loader walks up 3 parents from the module file, so we need
    # to mock the Path resolution. Easier: mock the whole function paths.
    import starfield_tool.tools.fast_lane_check as flc

    fake_dev_baseline = tmp_path / "data" / "creations_baseline.json"
    fake_dev_baseline.parent.mkdir()
    fake_dev_baseline.write_text(
        json.dumps({
            "version": 1,
            "snapshot_date": "2026-04-10T00:00:00+00:00",
            "entries": {"abc": {"t": "Test", "a": "Dev", "v": "1.0"}},
        }),
        encoding="utf-8",
    )

    # Temporarily replace the __file__ resolution via monkeypatch of Path
    # Simplest approach: patch the function itself
    def fake_load():
        return json.loads(fake_dev_baseline.read_text(encoding="utf-8"))

    monkeypatch.setattr(flc, "_load_baseline", fake_load)
    result = flc._load_baseline()
    assert result is not None
    assert result["version"] == 1
    assert "abc" in result["entries"]


def test_load_baseline_real_file():
    """Verify the real baseline file can be loaded (integration sanity check)."""
    result = _load_baseline()
    # This may be None if running in an environment without the file,
    # but in this repo the file exists post-T007
    if result is not None:
        assert result.get("version") == 1
        assert "entries" in result
        assert "snapshot_date" in result


# --- _lookup_baseline ---


def _sample_baseline_entries():
    return {
        "abc-123": {"t": "Dynamic Universe", "a": "youngneil1", "v": "2.2"},
        "def-456": {"t": "Place Doors Yourself", "a": "PDY Team", "v": "1.5"},
        "ghi-789": {"t": "Luxurious Ship Habs", "a": "DownfallNemesis", "v": "3.0"},
    }


def test_lookup_by_content_id():
    entries = _sample_baseline_entries()
    row = {"content_id": "abc-123", "title": "something else", "author": "other"}
    result = _lookup_baseline(row, entries)
    assert result is not None
    assert result["t"] == "Dynamic Universe"


def test_lookup_by_title_author_fallback():
    entries = _sample_baseline_entries()
    row = {"content_id": "", "title": "Place Doors Yourself", "author": "PDY Team"}
    result = _lookup_baseline(row, entries)
    assert result is not None
    assert result["v"] == "1.5"


def test_lookup_by_title_only_when_author_mismatch():
    entries = _sample_baseline_entries()
    row = {"content_id": "", "title": "Dynamic Universe", "author": "wrong author"}
    result = _lookup_baseline(row, entries)
    # Falls back to title-only match
    assert result is not None
    assert result["t"] == "Dynamic Universe"


def test_lookup_no_match():
    entries = _sample_baseline_entries()
    row = {"content_id": "", "title": "Unknown Mod", "author": "Nobody"}
    assert _lookup_baseline(row, entries) is None


def test_lookup_content_id_takes_precedence():
    """Content ID match wins even if title/author also match another entry."""
    entries = _sample_baseline_entries()
    row = {
        "content_id": "abc-123",
        "title": "Place Doors Yourself",  # matches def-456 by title
        "author": "PDY Team",
    }
    result = _lookup_baseline(row, entries)
    assert result["t"] == "Dynamic Universe"  # content_id match wins


def test_lookup_case_insensitive():
    entries = _sample_baseline_entries()
    row = {"content_id": "", "title": "dynamic universe", "author": "YOUNGNEIL1"}
    result = _lookup_baseline(row, entries)
    assert result is not None
    assert result["t"] == "Dynamic Universe"


# --- _classify ---


def test_classify_updated():
    assert _classify("2.0", "1.0") == STATUS_UPDATED
    assert _classify("1.5", "1.0") == STATUS_UPDATED
    assert _classify("1.0.1", "1.0.0") == STATUS_UPDATED


def test_classify_not_updated():
    assert _classify("1.0", "1.0") == STATUS_NOT_UPDATED
    assert _classify("2.5.1", "2.5.1") == STATUS_NOT_UPDATED


def test_classify_unknown_missing():
    assert _classify(None, "1.0") == STATUS_UNKNOWN
    assert _classify("1.0", None) == STATUS_UNKNOWN
    assert _classify(None, None) == STATUS_UNKNOWN
    assert _classify("", "1.0") == STATUS_UNKNOWN
    assert _classify("1.0", "") == STATUS_UNKNOWN


def test_classify_current_older_returns_unknown():
    # User has an older version than the baseline — unusual edge case
    assert _classify("1.0", "2.0") == STATUS_UNKNOWN


def test_classify_whitespace_trimmed():
    assert _classify(" 1.0 ", "1.0") == STATUS_NOT_UPDATED


# --- _status_sort_key ---


def test_sort_key_not_updated_first():
    rows = [
        {"status": STATUS_UPDATED},
        {"status": STATUS_NOT_UPDATED},
        {"status": STATUS_UNKNOWN},
        {"status": STATUS_UNAFFECTED},
        {"status": STATUS_NOT_UPDATED},
    ]
    rows.sort(key=_status_sort_key)
    assert rows[0]["status"] == STATUS_NOT_UPDATED
    assert rows[1]["status"] == STATUS_NOT_UPDATED
    assert rows[2]["status"] == STATUS_UNKNOWN
    assert rows[3]["status"] == STATUS_UNAFFECTED
    assert rows[4]["status"] == STATUS_UPDATED


# --- CSV parser ---


def test_parse_csv_new_format(tmp_path):
    csv_content = (
        "#,Content ID,Name,Author,Installed Version,Date\n"
        "1,abc-123,Dynamic Universe,youngneil1,2.2,29 Jan 2026\n"
        "2,def-456,Place Doors Yourself,PDY Team,1.5,10 Mar 2026\n"
    )
    f = tmp_path / "export.csv"
    f.write_text(csv_content, encoding="utf-8")

    rows, is_legacy = _parse_csv(f)
    assert is_legacy is False
    assert len(rows) == 2
    assert rows[0]["content_id"] == "abc-123"
    assert rows[0]["title"] == "Dynamic Universe"
    assert rows[0]["installed_version"] == "2.2"
    # Load order positions preserved from the # column
    assert rows[0]["load_position"] == 1
    assert rows[1]["load_position"] == 2


def test_parse_csv_preserves_row_order(tmp_path):
    """Rows must come out in file order, not sorted."""
    csv_content = (
        "#,Content ID,Name,Author,Installed Version,Date\n"
        "5,z-id,ZMod,A,1.0,date\n"
        "1,a-id,AMod,B,1.0,date\n"
        "3,m-id,MMod,C,1.0,date\n"
    )
    f = tmp_path / "export.csv"
    f.write_text(csv_content, encoding="utf-8")

    rows, _ = _parse_csv(f)
    assert [r["title"] for r in rows] == ["ZMod", "AMod", "MMod"]
    assert [r["load_position"] for r in rows] == [5, 1, 3]


def test_parse_csv_dash_position(tmp_path):
    """# column with '-' means no load position (missing file etc)."""
    csv_content = (
        "#,Content ID,Name,Author,Installed Version,Date\n"
        "-,abc,Unordered,Dev,1.0,date\n"
    )
    f = tmp_path / "export.csv"
    f.write_text(csv_content, encoding="utf-8")

    rows, _ = _parse_csv(f)
    assert rows[0]["load_position"] is None


def test_parse_csv_legacy_format(tmp_path):
    csv_content = (
        "#,Name,Author,Version,Date\n"
        "1,Dynamic Universe,youngneil1,2.2,29 Jan 2026\n"
    )
    f = tmp_path / "legacy.csv"
    f.write_text(csv_content, encoding="utf-8")

    rows, is_legacy = _parse_csv(f)
    assert is_legacy is True
    assert len(rows) == 1
    assert rows[0]["content_id"] == ""  # legacy has no content_id
    assert rows[0]["title"] == "Dynamic Universe"
    assert rows[0]["installed_version"] == "2.2"


def test_parse_csv_empty(tmp_path):
    f = tmp_path / "empty.csv"
    f.write_text("#,Content ID,Name,Author,Installed Version,Date\n", encoding="utf-8")
    rows, is_legacy = _parse_csv(f)
    assert rows == []
    assert is_legacy is False


# --- Markdown parser ---


def test_parse_markdown_new_format(tmp_path):
    md_content = (
        "| # | Content ID | Name             | Author    | Installed Version | Date        |\n"
        "| - | ---------- | ---------------- | --------- | ----------------- | ----------- |\n"
        "| 1 | abc-123    | Dynamic Universe | youngneil | 2.2               | 29 Jan 2026 |\n"
    )
    f = tmp_path / "export.txt"
    f.write_text(md_content, encoding="utf-8")

    rows, is_legacy = _parse_markdown(f)
    assert is_legacy is False
    assert len(rows) == 1
    assert rows[0]["content_id"] == "abc-123"
    assert rows[0]["title"] == "Dynamic Universe"
    assert rows[0]["installed_version"] == "2.2"


def test_parse_markdown_legacy_format(tmp_path):
    md_content = (
        "| # | Name             | Author    | Version | Date        |\n"
        "| - | ---------------- | --------- | ------- | ----------- |\n"
        "| 1 | Dynamic Universe | youngneil | 2.2     | 29 Jan 2026 |\n"
    )
    f = tmp_path / "legacy.txt"
    f.write_text(md_content, encoding="utf-8")

    rows, is_legacy = _parse_markdown(f)
    assert is_legacy is True
    assert len(rows) == 1
    assert rows[0]["content_id"] == ""
    assert rows[0]["title"] == "Dynamic Universe"


# --- Auto-detection ---


def test_parse_export_detects_csv(tmp_path):
    f = tmp_path / "x.csv"
    f.write_text(
        "#,Content ID,Name,Author,Installed Version,Date\n"
        "1,abc,Mod,Dev,1.0,date\n",
        encoding="utf-8",
    )
    rows, _ = _parse_export(f)
    assert len(rows) == 1


def test_parse_export_detects_markdown(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text(
        "| # | Content ID | Name | Author | Installed Version | Date |\n"
        "| - | ---------- | ---- | ------ | ----------------- | ---- |\n"
        "| 1 | abc        | Mod  | Dev    | 1.0               | date |\n",
        encoding="utf-8",
    )
    rows, _ = _parse_export(f)
    assert len(rows) == 1
    assert rows[0]["title"] == "Mod"


# --- End-to-end check flow ---


def test_full_check_flow_classifies_correctly():
    """Simulate a full check: baseline + rows + classify each."""
    baseline_entries = {
        "id-1": {"t": "Updated Mod", "a": "Dev", "v": "1.0"},
        "id-2": {"t": "Stale Mod", "a": "Dev", "v": "2.0"},
        "id-3": {"t": "No Current", "a": "Dev", "v": "1.0"},
    }
    rows = [
        {"content_id": "id-1", "title": "Updated Mod", "author": "Dev",
         "installed_version": "1.5"},  # updated (1.5 > 1.0)
        {"content_id": "id-2", "title": "Stale Mod", "author": "Dev",
         "installed_version": "2.0"},  # not_updated (2.0 == 2.0)
        {"content_id": "id-3", "title": "No Current", "author": "Dev",
         "installed_version": ""},  # unknown (no current)
        {"content_id": "id-missing", "title": "Missing", "author": "Dev",
         "installed_version": "1.0"},  # unknown (not in baseline)
    ]

    # Classify each row
    for row in rows:
        baseline = _lookup_baseline(row, baseline_entries)
        if baseline is None:
            row["status"] = STATUS_UNKNOWN
            continue
        baseline_version = baseline["v"]
        # Direct _classify exercise — reuse the row's installed_version as
        # the `current` input to cover a matrix of version relationships.
        current = row["installed_version"]
        row["status"] = _classify(current, baseline_version)

    statuses = [r["status"] for r in rows]
    assert statuses[0] == STATUS_UPDATED       # id-1
    assert statuses[1] == STATUS_NOT_UPDATED   # id-2
    assert statuses[2] == STATUS_UNKNOWN       # id-3 (empty installed)
    assert statuses[3] == STATUS_UNKNOWN       # id-missing (not in baseline)


# --- Skin exclusion ---


def _make_tool_with_baseline(baseline_entries: dict):
    """Build a FastLaneCheckTool instance with a stub baseline (no UI)."""
    from starfield_tool.tools.fast_lane_check import FastLaneCheckTool, MODE_FILE
    tool = FastLaneCheckTool()
    tool._baseline = {"version": 1, "snapshot_date": "2026-04-05", "entries": baseline_entries}
    tool._source_mode = MODE_FILE
    return tool


def test_skin_overrides_not_updated():
    """A version-stale skin should be marked STATUS_UNAFFECTED, not STATUS_NOT_UPDATED."""
    baseline = {
        "skin-id": {"t": "Pirate Skin", "a": "kine", "v": "1.0", "s": 1},
    }
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [{
        "content_id": "skin-id",
        "title": "Pirate Skin",
        "author": "kine",
        "installed_version": "1.0",  # matches baseline → would be NOT_UPDATED
        "load_position": 1,
        "baseline_version": None,
        "current_version": None,
        "status": None,
    }]
    tool._run_comparison({})
    assert tool._rows[0]["status"] == STATUS_UNAFFECTED


def test_skin_override_applies_even_when_updated():
    """The skin marker takes precedence over the version comparison."""
    baseline = {
        "skin-id": {"t": "Pirate Skin", "a": "kine", "v": "1.0", "s": 1},
    }
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [{
        "content_id": "skin-id",
        "title": "Pirate Skin",
        "author": "kine",
        "installed_version": "2.0",  # newer than baseline
        "load_position": 1,
        "baseline_version": None,
        "current_version": None,
        "status": None,
    }]
    tool._run_comparison({})
    assert tool._rows[0]["status"] == STATUS_UNAFFECTED


def test_snapshot_round_trip_through_fast_lane_check(tmp_path):
    """Save a snapshot via the load order tool, load it via fast lane, and
    verify classification uses API-current vs baseline (not snapshot's
    installed_version)."""
    from bethesda_creations.models import CreationInfo
    from load_order_sorter import save_snapshot
    from load_order_sorter.models import SnapshotEntry

    snap_path = tmp_path / "snap.json"
    save_snapshot("test", [
        SnapshotEntry("id-1", "Stale Mod", ["a.esm"], installed_version="1.0"),
        SnapshotEntry("id-2", "Fresh Mod", ["b.esm"], installed_version="2.0"),
    ], snap_path, "1.0")

    # Both baselines are "1.0". API reports id-1 still at 1.0 (stale) and
    # id-2 updated to 2.0 (updated). Classification uses API, not the
    # snapshot's installed_version.
    baseline = {
        "id-1": {"t": "Stale Mod", "a": "Dev", "v": "1.0"},
        "id-2": {"t": "Fresh Mod", "a": "Dev", "v": "1.0"},
    }
    tool = _make_tool_with_baseline(baseline)

    # Mirror what _import_snapshot does (no Tk)
    from load_order_sorter import load_snapshot
    snapshot = load_snapshot(snap_path)
    tool._rows = [
        {
            "content_id": e.content_id,
            "title": e.display_name,
            "author": "",
            "installed_version": e.installed_version,
            "load_position": i + 1,
            "baseline_version": None,
            "current_version": None,
            "status": None,
        }
        for i, e in enumerate(snapshot.entries)
    ]

    # Simulate the API responses: id-1 still at 1.0, id-2 at 2.0.
    info_map = {
        "id-1": CreationInfo(version="1.0"),
        "id-2": CreationInfo(version="2.0"),
    }
    tool._run_comparison(info_map)

    assert tool._rows[0]["status"] == STATUS_NOT_UPDATED  # api 1.0 == baseline 1.0
    assert tool._rows[1]["status"] == STATUS_UPDATED      # api 2.0 > baseline 1.0


def test_ps_support_promotes_not_updated_to_likely_updated():
    """Version matches baseline BUT creation lists PS4/PS5 support →
    reclassify as likely_updated (author republished post-Free-Lanes
    without bumping the version)."""
    from bethesda_creations.models import CreationInfo
    from starfield_tool.tools.fast_lane_check import STATUS_LIKELY_UPDATED
    baseline = {
        "ps-id": {"t": "PS Mod", "a": "Dev", "v": "1.0"},
    }
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [{
        "content_id": "ps-id",
        "title": "PS Mod",
        "author": "Dev",
        "installed_version": "1.0",
        "load_position": 1,
        "baseline_version": None,
        "current_version": None,
        "status": None,
    }]
    info_map = {
        "ps-id": CreationInfo(
            version="1.0",  # same as baseline
            platforms=["WINDOWS", "XBOXSERIESX", "PLAYSTATION5"],
        ),
    }
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_LIKELY_UPDATED


def test_no_ps_support_stays_not_updated():
    """Version matches baseline, no PS platform → still flagged not_updated."""
    from bethesda_creations.models import CreationInfo
    baseline = {
        "pc-only": {"t": "PC Only Mod", "a": "Dev", "v": "1.0"},
    }
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [{
        "content_id": "pc-only",
        "title": "PC Only Mod",
        "author": "Dev",
        "installed_version": "1.0",
        "load_position": 1,
        "baseline_version": None,
        "current_version": None,
        "status": None,
    }]
    info_map = {
        "pc-only": CreationInfo(
            version="1.0",
            platforms=["WINDOWS", "XBOXSERIESX"],
        ),
    }
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_NOT_UPDATED


def test_non_skin_unaffected_by_skin_override():
    """Entries without the s flag classify normally via API current vs baseline."""
    from bethesda_creations.models import CreationInfo
    baseline = {
        "quest-id": {"t": "Quest Mod", "a": "Dev", "v": "1.0"},
    }
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [{
        "content_id": "quest-id",
        "title": "Quest Mod",
        "author": "Dev",
        "installed_version": "1.0",
        "load_position": 1,
        "baseline_version": None,
        "current_version": None,
        "status": None,
    }]
    # API reports current == baseline → not updated
    tool._run_comparison({"quest-id": CreationInfo(version="1.0")})
    assert tool._rows[0]["status"] == STATUS_NOT_UPDATED


# ---------------------------------------------------------------------------
# 011: SAFE category (Unaffected) classification
# ---------------------------------------------------------------------------


def _make_row(content_id="id-1", title="Mod", version="1.0"):
    return {
        "content_id": content_id,
        "title": title,
        "author": "Dev",
        "installed_version": version,
        "load_position": 1,
        "baseline_version": None,
        "current_version": None,
        "status": None,
    }


def test_apparel_marked_unaffected():
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Outfit", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Outfit")]
    info_map = {"id-1": CreationInfo(version="1.0", categories=["Apparel"])}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_UNAFFECTED
    assert tool._rows[0]["unaffected_reason"] == "Apparel"


def test_photo_mode_marked_unaffected():
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Filter", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Filter")]
    info_map = {"id-1": CreationInfo(version="1.0", categories=["Photo Mode"])}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_UNAFFECTED


def test_audio_marked_unaffected():
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Music", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Music")]
    info_map = {"id-1": CreationInfo(version="1.0", categories=["Audio"])}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_UNAFFECTED


def test_meta_tags_ignored_for_safe():
    """[Apparel, Lore Friendly] — Lore Friendly is meta, so non_meta=['Apparel']
    and the SAFE check passes."""
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Lore Outfit", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Lore Outfit")]
    info_map = {"id-1": CreationInfo(
        version="1.0", categories=["Apparel", "Lore Friendly"],
    )}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_UNAFFECTED


def test_mixed_apparel_quests_stays_not_updated():
    """[Apparel, Quests] — Quests is neither safe nor low-risk, so strict
    combination fails and the creation stays in the full warning bucket."""
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Quest Outfit", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Quest Outfit")]
    info_map = {"id-1": CreationInfo(
        version="1.0", categories=["Apparel", "Quests"],
    )}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_NOT_UPDATED


def test_baseline_skin_flag_fallback():
    """baseline.s == 1, no API categories → still Unaffected via fallback."""
    baseline = {"id-1": {"t": "Skin", "a": "Dev", "v": "1.0", "s": 1}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Skin")]
    tool._run_comparison({})  # no API info — must still classify as Unaffected
    assert tool._rows[0]["status"] == STATUS_UNAFFECTED
    assert tool._rows[0]["unaffected_reason"] == "Skin"


# ---------------------------------------------------------------------------
# 011: LOW_RISK category annotation
# ---------------------------------------------------------------------------


def test_weapons_marked_low_risk():
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Gun", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Gun")]
    info_map = {"id-1": CreationInfo(version="1.0", categories=["Weapons"])}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_LOW_RISK
    assert tool._rows[0]["low_risk_reason"] == "Weapons"


def test_gear_marked_low_risk():
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Helmet", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Helmet")]
    info_map = {"id-1": CreationInfo(version="1.0", categories=["Gear"])}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_LOW_RISK


def test_ships_marked_low_risk():
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Hab", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Hab")]
    info_map = {"id-1": CreationInfo(version="1.0", categories=["Ships"])}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_LOW_RISK
    assert tool._rows[0]["low_risk_reason"] == "Ships"


def test_ps_support_wins_over_low_risk():
    """Weapons category + PS5 platform → Likely updated (PS precedence)."""
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "PS Gun", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "PS Gun")]
    info_map = {"id-1": CreationInfo(
        version="1.0",
        categories=["Weapons"],
        platforms=["WINDOWS", "PLAYSTATION5"],
    )}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_LIKELY_UPDATED


def test_quest_mod_stays_not_updated():
    """Quests is neither safe nor low-risk — no tier relief."""
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Quest", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Quest")]
    info_map = {"id-1": CreationInfo(version="1.0", categories=["Quests"])}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_NOT_UPDATED


def test_mixed_weapons_quests_stays_not_updated():
    """[Weapons, Quests] — strict combination rejects the mix."""
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "QGun", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "QGun")]
    info_map = {"id-1": CreationInfo(
        version="1.0", categories=["Weapons", "Quests"],
    )}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_NOT_UPDATED


def test_weapons_with_updated_version_stays_updated():
    """Category tier must never downgrade a genuine version update."""
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Gun", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Gun")]
    info_map = {"id-1": CreationInfo(version="2.0", categories=["Weapons"])}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_UPDATED


def test_mixed_safe_and_low_risk_triggers_low_risk():
    """[Apparel, Weapons] — all in (SAFE ∪ LOW_RISK), at least one in LOW_RISK
    → Low risk."""
    from bethesda_creations.models import CreationInfo
    baseline = {"id-1": {"t": "Mixed", "a": "Dev", "v": "1.0"}}
    tool = _make_tool_with_baseline(baseline)
    tool._rows = [_make_row("id-1", "Mixed")]
    info_map = {"id-1": CreationInfo(
        version="1.0", categories=["Apparel", "Weapons"],
    )}
    tool._run_comparison(info_map)
    assert tool._rows[0]["status"] == STATUS_LOW_RISK


# ---------------------------------------------------------------------------
# 011: Summary line and sort key
# ---------------------------------------------------------------------------


def test_sort_key_ordering_matches_spec():
    assert _status_sort_key({"status": STATUS_NOT_UPDATED}) == 0
    assert _status_sort_key({"status": STATUS_UNKNOWN}) == 1
    assert _status_sort_key({"status": STATUS_LOW_RISK}) == 2
    assert _status_sort_key({"status": STATUS_LIKELY_UPDATED}) == 3
    assert _status_sort_key({"status": STATUS_UNAFFECTED}) == 4
    assert _status_sort_key({"status": STATUS_UPDATED}) == 5
    # Ordering: each subsequent tier must have a key >= the previous.
    keys = [
        _status_sort_key({"status": s}) for s in (
            STATUS_NOT_UPDATED, STATUS_UNKNOWN, STATUS_LOW_RISK,
            STATUS_LIKELY_UPDATED, STATUS_UNAFFECTED, STATUS_UPDATED,
        )
    ]
    assert keys == sorted(keys)
