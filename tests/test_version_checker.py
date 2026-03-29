from unittest.mock import patch, MagicMock

from starfield_tool.models import Creation
from starfield_tool.version_checker import (
    check_for_updates,
    CheckResult,
    CreationPageInfo,
    _parse_api_response,
)
from starfield_tool.status_bar import StatusBarImpl


def _make_creation(content_id: str, version: str) -> Creation:
    return Creation(
        content_id=content_id,
        display_name=f"Creation {content_id}",
        installed_version=version,
    )


def _make_page_info(version: str) -> CreationPageInfo:
    return CreationPageInfo(version=version)


_MOCK_PATH = "starfield_tool.version_checker._fetch_creation_info"


class TestCheckForUpdates:
    def test_detects_updates(self):
        creations = [
            _make_creation("A", "1.0.0"),
            _make_creation("B", "2.0.0"),
        ]
        mock_info = {
            "A": _make_page_info("1.1.0"),
            "B": _make_page_info("2.0.0"),
        }
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, return_value=mock_info):
            result = check_for_updates(creations, bar)

        a = [c for c in result.creations if c.content_id == "A"][0]
        assert a.has_update is True
        assert a.available_version == "1.1.0"

        b = [c for c in result.creations if c.content_id == "B"][0]
        assert b.has_update is False
        assert result.skipped == 0

    def test_network_error_returns_unchanged(self):
        creations = [_make_creation("A", "1.0.0")]
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, side_effect=Exception("Network error")):
            result = check_for_updates(creations, bar)

        assert result.creations[0].has_update is False
        assert result.creations[0].available_version is None

    def test_results_are_ephemeral(self):
        creations = [_make_creation("A", "1.0.0")]
        bar = StatusBarImpl()

        mock_info = {"A": _make_page_info("2.0.0")}
        with patch(_MOCK_PATH, return_value=mock_info):
            result = check_for_updates(creations, bar)

        assert result.creations[0].has_update is True
        # Original object should not be mutated
        assert creations[0].has_update is False

    def test_version_comparison(self):
        creations = [
            _make_creation("A", "1.0.0"),
            _make_creation("B", "2.0.0"),
            _make_creation("C", "3.0.0"),
        ]
        mock_info = {
            "A": _make_page_info("1.0.0"),
            "B": _make_page_info("1.9.0"),
            "C": _make_page_info("3.1.0"),
        }
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, return_value=mock_info):
            result = check_for_updates(creations, bar)

        a = [c for c in result.creations if c.content_id == "A"][0]
        assert a.has_update is False  # same version

        b = [c for c in result.creations if c.content_id == "B"][0]
        assert b.has_update is False  # older available than installed

        c = [c for c in result.creations if c.content_id == "C"][0]
        assert c.has_update is True  # newer available

    def test_skipped_count_for_missing_creations(self):
        creations = [
            _make_creation("A", "1.0.0"),
            _make_creation("B", "2.0.0"),
        ]
        # Only A is found on Creations, B is a Nexus mod
        mock_info = {"A": _make_page_info("1.1.0")}
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, return_value=mock_info):
            result = check_for_updates(creations, bar)

        assert result.skipped == 1


class TestParseApiResponse:
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
        info = _parse_api_response(data)
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
        info = _parse_api_response(data)
        assert info.version == "2.0"
        assert info.price == 0
        assert info.achievement_friendly is False
        assert info.author == "ModderName"

    def test_empty_response(self):
        data = {"platform": {"response": {}}}
        info = _parse_api_response(data)
        assert info.version is None
        assert info.author is None
        assert info.price == 0
        assert info.categories == []
        assert info.achievement_friendly is False
