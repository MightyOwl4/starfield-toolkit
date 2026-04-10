"""Tests for the Fast Lane baseline generator script."""
import json

from starfield_tool.tools.fast_lane_baseline_generator import (
    extract_latest_version,
    run,
    trim_catalogue,
)


def _release_note(version, ctime, note="release"):
    return {"version_name": version, "ctime": ctime, "note": note}


def _platform_group(platform, notes):
    return {"hardware_platform": platform, "release_notes": notes}


# --- extract_latest_version ---


def test_extract_single_platform_single_version():
    entry = {
        "release_notes": [
            _platform_group("WINDOWS", [_release_note("1.0", 1000)]),
        ]
    }
    assert extract_latest_version(entry) == "1.0"


def test_extract_picks_latest_ctime():
    entry = {
        "release_notes": [
            _platform_group("WINDOWS", [
                _release_note("1.0", 1000),
                _release_note("1.2", 3000),
                _release_note("1.1", 2000),
            ]),
        ]
    }
    assert extract_latest_version(entry) == "1.2"


def test_extract_across_platforms():
    entry = {
        "release_notes": [
            _platform_group("WINDOWS", [_release_note("1.0", 1000)]),
            _platform_group("XBOXSERIESX", [_release_note("1.5", 5000)]),
            _platform_group("XBOXONE", [_release_note("1.2", 2000)]),
        ]
    }
    assert extract_latest_version(entry) == "1.5"


def test_extract_missing_release_notes():
    assert extract_latest_version({}) == "unknown"
    assert extract_latest_version({"release_notes": []}) == "unknown"
    assert extract_latest_version({"release_notes": None}) == "unknown"


def test_extract_malformed_release_notes():
    entry = {
        "release_notes": [
            {"hardware_platform": "WINDOWS"},  # no nested release_notes
        ]
    }
    assert extract_latest_version(entry) == "unknown"


# --- trim_catalogue ---


def test_trim_basic():
    """Trimmed entries use short keys: t=title, a=author, v=version."""
    full = {
        "version": 1,
        "entries": {
            "abc": {
                "title": "Mod A",
                "author": "Alice",
                "description": "very long...",
                "content_hash": "deadbeef",
                "release_notes": [
                    _platform_group("WINDOWS", [_release_note("2.0", 5000)]),
                ],
            },
        },
    }
    trimmed = trim_catalogue(full)
    assert trimmed["version"] == 1
    assert "snapshot_date" in trimmed
    assert "abc" in trimmed["entries"]
    entry = trimmed["entries"]["abc"]
    assert entry == {"t": "Mod A", "a": "Alice", "v": "2.0"}
    # Original irrelevant fields must not leak through
    assert "description" not in entry
    assert "content_hash" not in entry
    # Long keys must not be present (compact format)
    assert "title" not in entry
    assert "author" not in entry
    assert "version" not in entry


def test_trim_multiple_entries():
    full = {
        "version": 1,
        "entries": {
            "id-1": {"title": "A", "author": "x", "release_notes": [
                _platform_group("WINDOWS", [_release_note("1.0", 100)]),
            ]},
            "id-2": {"title": "B", "author": "y", "release_notes": [
                _platform_group("WINDOWS", [_release_note("2.5", 200)]),
            ]},
        },
    }
    trimmed = trim_catalogue(full)
    assert len(trimmed["entries"]) == 2
    assert trimmed["entries"]["id-1"]["v"] == "1.0"
    assert trimmed["entries"]["id-2"]["v"] == "2.5"


def test_trim_marks_skin_entries():
    """Entries in the 'Skins' category get an s=1 flag."""
    full = {
        "version": 1,
        "entries": {
            "skin-id": {
                "title": "Pirate Skin Pack",
                "author": "kine",
                "categories": ["Apparel", "Load Order Neutral", "Skins"],
                "release_notes": [
                    _platform_group("WINDOWS", [_release_note("1.0", 100)]),
                ],
            },
            "non-skin-id": {
                "title": "Quest Mod",
                "author": "alice",
                "categories": ["Quests", "World"],
                "release_notes": [
                    _platform_group("WINDOWS", [_release_note("1.0", 100)]),
                ],
            },
        },
    }
    trimmed = trim_catalogue(full)
    assert trimmed["entries"]["skin-id"]["s"] == 1
    assert "s" not in trimmed["entries"]["non-skin-id"]


def test_trim_skin_flag_absent_when_no_categories():
    """Entries without categories don't get an s flag."""
    full = {
        "version": 1,
        "entries": {
            "abc": {
                "title": "Mod",
                "author": "x",
                "release_notes": [
                    _platform_group("WINDOWS", [_release_note("1.0", 100)]),
                ],
            },
        },
    }
    trimmed = trim_catalogue(full)
    assert "s" not in trimmed["entries"]["abc"]


def test_trim_missing_title_author():
    full = {
        "version": 1,
        "entries": {
            "abc": {"release_notes": []},
        },
    }
    trimmed = trim_catalogue(full)
    assert trimmed["entries"]["abc"]["t"] == ""
    assert trimmed["entries"]["abc"]["a"] == ""
    assert trimmed["entries"]["abc"]["v"] == "unknown"


def test_trim_snapshot_date_is_iso():
    full = {"version": 1, "entries": {}}
    trimmed = trim_catalogue(full)
    # Should parse as ISO format
    from datetime import datetime
    datetime.fromisoformat(trimmed["snapshot_date"])


def test_trim_snapshot_date_uses_earliest_fetched_at():
    """The baseline's snapshot_date comes from the catalogue, not generation time."""
    full = {
        "version": 1,
        "entries": {
            "a": {
                "title": "A",
                "author": "x",
                "fetched_at": "2026-04-05T11:18:00+00:00",  # later
                "release_notes": [],
            },
            "b": {
                "title": "B",
                "author": "y",
                "fetched_at": "2026-04-05T11:10:00+00:00",  # earliest
                "release_notes": [],
            },
            "c": {
                "title": "C",
                "author": "z",
                "fetched_at": "2026-04-05T11:15:00+00:00",
                "release_notes": [],
            },
        },
    }
    trimmed = trim_catalogue(full)
    # Should pick the earliest fetched_at across all entries
    assert trimmed["snapshot_date"] == "2026-04-05T11:10:00+00:00"


def test_trim_snapshot_date_falls_back_to_now_when_no_fetched_at():
    """If entries lack fetched_at, falls back to current time."""
    full = {
        "version": 1,
        "entries": {
            "a": {"title": "A", "author": "x", "release_notes": []},
        },
    }
    trimmed = trim_catalogue(full)
    # Should still be a valid ISO timestamp
    from datetime import datetime
    datetime.fromisoformat(trimmed["snapshot_date"])


# --- CLI integration ---


def test_run_writes_valid_json(tmp_path):
    catalogue_path = tmp_path / "catalogue.json"
    output_path = tmp_path / "baseline.json"

    catalogue_path.write_text(json.dumps({
        "version": 1,
        "entries": {
            "abc": {
                "title": "Mod",
                "author": "Dev",
                "release_notes": [
                    _platform_group("WINDOWS", [_release_note("1.2.3", 1000)]),
                ],
            },
        },
    }), encoding="utf-8")

    exit_code = run([
        "--catalogue", str(catalogue_path),
        "--output", str(output_path),
    ])

    assert exit_code == 0
    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert "snapshot_date" in data
    assert data["entries"]["abc"]["v"] == "1.2.3"


def test_run_missing_catalogue_returns_error(tmp_path):
    exit_code = run([
        "--catalogue", str(tmp_path / "nope.json"),
        "--output", str(tmp_path / "baseline.json"),
    ])
    assert exit_code == 2


def test_run_corrupted_catalogue_returns_error(tmp_path):
    catalogue_path = tmp_path / "bad.json"
    catalogue_path.write_text("{not valid", encoding="utf-8")
    exit_code = run([
        "--catalogue", str(catalogue_path),
        "--output", str(tmp_path / "baseline.json"),
    ])
    assert exit_code == 2
