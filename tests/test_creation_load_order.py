from pathlib import Path

from starfield_tool.models import GameInstallation
from starfield_tool.parsers import build_creation_list

FIXTURES = Path(__file__).parent / "fixtures"


def _make_install(fixtures_dir: Path) -> GameInstallation:
    return GameInstallation(
        game_root=fixtures_dir,
        source="manual",
        _plugins_txt_override=fixtures_dir / "Plugins.txt",
    )


class TestBuildCreationList:
    def test_filters_to_store_creations_only(self):
        install = _make_install(FIXTURES)
        creations = build_creation_list(install)
        names = [c.display_name for c in creations]
        # Base game ESMs should be excluded
        assert "Starfield.esm" not in [c.content_id for c in creations]
        # Store creations should be included
        assert "Vulture's Roost" in names

    def test_load_position_sequential(self):
        install = _make_install(FIXTURES)
        creations = build_creation_list(install)
        # Positions should be sequential (0, 1, 2, ...) without gaps
        positions = [c.load_position for c in creations if c.load_position is not None]
        assert positions == list(range(len(positions)))

    def test_marks_missing_files(self):
        install = _make_install(FIXTURES)
        creations = build_creation_list(install)
        cc01 = [c for c in creations if c.content_id == "CC01"][0]
        # CreationClub01.esl does not exist in Data/
        assert cc01.file_missing is True

    def test_existing_files_not_marked_missing(self):
        install = _make_install(FIXTURES)
        creations = build_creation_list(install)
        bgs007 = [c for c in creations if c.content_id == "SFBGS007"][0]
        assert bgs007.file_missing is False

    def test_active_status(self):
        install = _make_install(FIXTURES)
        creations = build_creation_list(install)
        bgs007 = [c for c in creations if c.content_id == "SFBGS007"][0]
        assert bgs007.is_active is True
        cc01 = [c for c in creations if c.content_id == "CC01"][0]
        assert cc01.is_active is False

    def test_empty_content_catalog(self, tmp_path):
        data_dir = tmp_path / "Data"
        data_dir.mkdir()
        (data_dir / "Starfield.esm").touch()
        (tmp_path / "ContentCatalog.txt").write_text('{"ContentCatalog":{"Version":"1.1"}}', encoding="utf-8")
        plugins = tmp_path / "Plugins.txt"
        plugins.write_text("", encoding="utf-8")
        install = GameInstallation(game_root=tmp_path, _plugins_txt_override=plugins)
        creations = build_creation_list(install)
        assert creations == []

    def test_sorted_by_load_position(self):
        install = _make_install(FIXTURES)
        creations = build_creation_list(install)
        positions = [c.load_position for c in creations if c.load_position is not None]
        assert positions == sorted(positions)
