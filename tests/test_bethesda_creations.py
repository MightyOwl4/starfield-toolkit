    """Tests for the bethesda_creations package."""
import json
import time
from pathlib import Path

from bethesda_creations.models import CreationInfo
from bethesda_creations._api import parse_response, content_id_to_uuid
from bethesda_creations._cache import (
    load_cache, save_cache, clear_cache, is_session_fresh,
    info_to_entry, entry_to_info, merge_with_cached, CACHE_VERSION,
)
from bethesda_creations._version_cmp import compare_versions


class TestParseResponse:
    def test_parses_all_fields(self):
        data = {
            "platform": {
                "response": {
                    "author_displayname": "SomeAuthor",
                    "achievement_friendly": True,
                    "categories": ["Gear", "Lore Friendly", "Quests"],
                    "release_notes": [
                        {
                            "hardware_platform": "WINDOWS",
                            "release_notes": [
                                {"version_name": "1.2.3"}
                            ],
                        }
                    ],
                    "download": [
                        {
                            "hardware_platform": "WINDOWS",
                            "published": [
                                {
                                    "client": {
                                        "_slot": {"size": 125829120}
                                    }
                                }
                            ],
                        }
                    ],
                    "first_ptime": 1736467200,
                    "utime": 1741132800,
                    "catalog_info": [
                        {"prices": [{"amount": 400}]}
                    ],
                    "preview_image": {
                        "s3bucket": "ugcmods.bethesda.net",
                        "s3key": "public/content/thumb.jpg",
                    },
                }
            }
        }
        info = parse_response(data)
        assert info.version == "1.2.3"
        assert info.installation_size == "120.00 MB"
        assert info.author == "SomeAuthor"
        assert info.price == 400
        assert info.achievement_friendly is True
        assert info.categories == ["Gear", "Lore Friendly", "Quests"]
        assert info.thumbnail_url == "https://ugcmods.bethesda.net/public/content/thumb.jpg"
        assert info.created_on is not None
        assert info.last_updated is not None

    def test_parses_free_creation(self):
        data = {
            "platform": {
                "response": {
                    "author_displayname": "ModderName",
                    "achievement_friendly": False,
                    "categories": [],
                    "release_notes": [
                        {
                            "hardware_platform": "WINDOWS",
                            "release_notes": [
                                {"version_name": "2.0"}
                            ],
                        }
                    ],
                }
            }
        }
        info = parse_response(data)
        assert info.version == "2.0"
        assert info.price == 0
        assert info.achievement_friendly is False
        assert info.author == "ModderName"

    def test_empty_response(self):
        data = {"platform": {"response": {}}}
        info = parse_response(data)
        assert info.version is None
        assert info.author is None
        assert info.price == 0
        assert info.categories == []
        assert info.achievement_friendly is False


class TestContentIdToUuid:
    def test_tm_prefix(self):
        assert content_id_to_uuid("TM_abc-123") == "abc-123"

    def test_uuid_passthrough(self):
        assert content_id_to_uuid("4bf1a31f-46d5-47bf-a5e6-d0f9e2496d0c") == "4bf1a31f-46d5-47bf-a5e6-d0f9e2496d0c"

    def test_non_uuid(self):
        assert content_id_to_uuid("SFBGS006") is None


class TestVersionComparison:
    def test_newer(self):
        assert compare_versions("1.0.0", "1.1.0") is True

    def test_same(self):
        assert compare_versions("1.0.0", "1.0.0") is False

    def test_older(self):
        assert compare_versions("2.0.0", "1.0.0") is False


class TestCache:
    def test_missing_file_returns_empty(self, tmp_path):
        assert load_cache(tmp_path / "nonexistent.json") == {}

    def test_corrupt_file_returns_empty(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        assert load_cache(bad) == {}

    def test_wrong_version_returns_empty(self, tmp_path):
        f = tmp_path / "cache.json"
        f.write_text(json.dumps({"version": 999, "entries": {"A": {}}}))
        assert load_cache(f) == {}

    def test_round_trip(self, tmp_path):
        f = tmp_path / "cache.json"
        entries = {"X": {"author": "Alice", "version": "1.0"}}
        save_cache(entries, f)
        assert load_cache(f) == entries

    def test_clear(self, tmp_path):
        f = tmp_path / "cache.json"
        f.write_text("{}")
        clear_cache(f)
        assert not f.exists()

    def test_clear_missing_ok(self, tmp_path):
        clear_cache(tmp_path / "nonexistent.json")

    def test_session_fresh(self):
        assert is_session_fresh(time.monotonic() - 10, 1800) is True

    def test_session_expired(self):
        assert is_session_fresh(time.monotonic() - 1801, 1800) is False


class TestEntryConversion:
    def test_round_trip(self):
        info = CreationInfo(
            version="2.0", author="Bob", price=300,
            categories=["Gear"], achievement_friendly=True,
        )
        entry = info_to_entry(info)
        restored = entry_to_info(entry)
        assert restored.author == "Bob"
        assert restored.version == "2.0"
        assert restored.price == 300
        assert restored.achievement_friendly is True

    def test_merge_immutable_from_cache(self):
        fresh = CreationInfo(version="2.0", price=500)
        cached = {"author": "Cached", "achievement_friendly": True, "categories": ["Gear"], "thumbnail_url": "url"}
        merged = merge_with_cached(fresh, cached)
        assert merged.author == "Cached"
        assert merged.version == "2.0"
        assert merged.price == 500
