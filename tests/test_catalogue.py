"""Tests for catalogue file I/O, hashing, and entry conversion."""
import json

from bethesda_creations.catalogue import (
    api_response_to_entry,
    compute_content_hash,
    load_catalogue,
    normalize_release_notes,
    save_catalogue,
)


def test_load_save_roundtrip(tmp_path):
    cat_path = tmp_path / "catalogue.json"
    entries = {
        "abc-123": {
            "title": "Test Creation",
            "description": "A test",
            "content_hash": "deadbeef",
        }
    }
    save_catalogue(entries, cat_path)
    loaded = load_catalogue(cat_path)
    assert loaded == entries


def test_load_missing_file_returns_empty(tmp_path):
    cat_path = tmp_path / "nonexistent.json"
    assert load_catalogue(cat_path) == {}


def test_load_corrupted_json_returns_empty(tmp_path):
    cat_path = tmp_path / "catalogue.json"
    cat_path.write_text("{bad json!!!", encoding="utf-8")
    assert load_catalogue(cat_path) == {}


def test_load_wrong_version_returns_empty(tmp_path):
    cat_path = tmp_path / "catalogue.json"
    cat_path.write_text(
        json.dumps({"version": 999, "entries": {"a": {}}}), encoding="utf-8"
    )
    assert load_catalogue(cat_path) == {}


def test_atomic_write_creates_parent_dirs(tmp_path):
    cat_path = tmp_path / "sub" / "dir" / "catalogue.json"
    save_catalogue({"x": {}}, cat_path)
    assert cat_path.exists()
    loaded = load_catalogue(cat_path)
    assert "x" in loaded


def test_compute_content_hash_deterministic():
    h1 = compute_content_hash("hello", "world")
    h2 = compute_content_hash("hello", "world")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_compute_content_hash_empty_strings():
    h = compute_content_hash("", "")
    assert len(h) == 64


def test_compute_content_hash_different_inputs():
    h1 = compute_content_hash("a", "b")
    h2 = compute_content_hash("ab", "")
    assert h1 == h2  # "a"+"b" == "ab"+""


def test_normalize_release_notes():
    notes = [
        {
            "hardware_platform": "WINDOWS",
            "release_notes": [
                {"version_name": "1.0", "note": "Initial Upload"},
                {"version_name": "1.1", "note": "Bug fix"},
            ],
        }
    ]
    text = normalize_release_notes(notes)
    assert "1.0" in text
    assert "Initial Upload" in text
    assert "1.1" in text
    assert "Bug fix" in text


def test_normalize_release_notes_empty():
    assert normalize_release_notes([]) == ""
    assert normalize_release_notes(None) == ""


def test_api_response_to_entry():
    item = {
        "content_id": "abc-123",
        "title": "My Creation",
        "description": "A cool creation",
        "overview": "Extra info",
        "author_displayname": "TestAuthor",
        "categories": ["Weapons"],
        "achievement_friendly": True,
        "catalog_info": [{"prices": [{"amount": 500}]}],
        "release_notes": [
            {
                "hardware_platform": "WINDOWS",
                "release_notes": [
                    {"version_name": "1.0", "note": "First release", "ctime": 12345},
                ],
            }
        ],
        "required_mods": ["some-uuid"],
    }
    entry = api_response_to_entry(item)
    assert entry["title"] == "My Creation"
    assert entry["description"] == "A cool creation"
    assert entry["overview"] == "Extra info"
    assert entry["author"] == "TestAuthor"
    assert entry["categories"] == ["Weapons"]
    assert entry["price"] == 500
    assert entry["achievement_friendly"] is True
    assert entry["required_mods"] == ["some-uuid"]
    assert len(entry["content_hash"]) == 64
    assert entry["fetched_at"]  # non-empty ISO timestamp


def test_api_response_to_entry_minimal():
    entry = api_response_to_entry({})
    assert entry["title"] == ""
    assert entry["description"] == ""
    assert entry["price"] == 0
    assert entry["release_notes"] == []
    assert entry["required_mods"] == []
    assert len(entry["content_hash"]) == 64


def test_merge_preserves_existing(tmp_path):
    cat_path = tmp_path / "catalogue.json"
    original = {"abc": {"title": "Original"}}
    save_catalogue(original, cat_path)
    loaded = load_catalogue(cat_path)
    loaded["def"] = {"title": "New"}
    save_catalogue(loaded, cat_path)
    final = load_catalogue(cat_path)
    assert "abc" in final
    assert "def" in final
    assert final["abc"]["title"] == "Original"
