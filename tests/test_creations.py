"""Tests for the starfield_tool.creations adapter."""
from unittest.mock import patch

from starfield_tool.models import Creation
from starfield_tool.creations import check_for_updates, check_achievements, CheckResult
from starfield_tool.status_bar import StatusBarImpl
from bethesda_creations import CreationInfo


def _make_creation(content_id: str, version: str) -> Creation:
    return Creation(
        content_id=content_id,
        display_name=f"Creation {content_id}",
        installed_version=version,
    )


def _make_info(version: str, **kwargs) -> CreationInfo:
    return CreationInfo(version=version, **kwargs)


_MOCK_PATH = "starfield_tool.creations._make_client"


class _FakeClient:
    def __init__(self, info_map):
        self._info_map = info_map

    def fetch_info(self, queries):
        return {q.content_id: self._info_map[q.content_id]
                for q in queries if q.content_id in self._info_map}


class TestCheckForUpdates:
    def test_detects_updates(self):
        creations = [_make_creation("A", "1.0.0"), _make_creation("B", "2.0.0")]
        fake = _FakeClient({"A": _make_info("1.1.0"), "B": _make_info("2.0.0")})
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, return_value=fake):
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

    def test_skipped_count(self):
        creations = [_make_creation("A", "1.0"), _make_creation("B", "2.0")]
        fake = _FakeClient({"A": _make_info("1.1")})
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, return_value=fake):
            result = check_for_updates(creations, bar)

        assert result.skipped == 1

    def test_results_are_ephemeral(self):
        creations = [_make_creation("A", "1.0.0")]
        fake = _FakeClient({"A": _make_info("2.0.0")})
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, return_value=fake):
            result = check_for_updates(creations, bar)

        assert result.creations[0].has_update is True
        assert creations[0].has_update is False  # original unchanged

    def test_version_comparison(self):
        creations = [
            _make_creation("A", "1.0.0"),
            _make_creation("B", "2.0.0"),
            _make_creation("C", "3.0.0"),
        ]
        fake = _FakeClient({
            "A": _make_info("1.0.0"),
            "B": _make_info("1.9.0"),
            "C": _make_info("3.1.0"),
        })
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, return_value=fake):
            result = check_for_updates(creations, bar)

        a = [c for c in result.creations if c.content_id == "A"][0]
        assert a.has_update is False
        b = [c for c in result.creations if c.content_id == "B"][0]
        assert b.has_update is False
        c = [c for c in result.creations if c.content_id == "C"][0]
        assert c.has_update is True


class TestCheckAchievements:
    def test_detects_blockers(self):
        creations = [_make_creation("A", "1.0")]
        fake = _FakeClient({"A": _make_info("1.0", achievement_friendly=False)})
        bar = StatusBarImpl()

        with patch(_MOCK_PATH, return_value=fake):
            result = check_achievements(creations, bar)

        assert result.creations[0].achievement_friendly is False
