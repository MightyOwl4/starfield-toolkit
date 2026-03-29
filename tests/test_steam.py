from pathlib import Path

from starfield_tool.steam import parse_library_folders, find_starfield_in_libraries


FIXTURES = Path(__file__).parent / "fixtures"


class TestParseLibraryFolders:
    def test_parses_two_library_paths(self):
        paths = parse_library_folders(FIXTURES / "libraryfolders.vdf")
        assert len(paths) == 2
        assert Path("C:/Program Files (x86)/Steam") in paths
        assert Path("D:/SteamLibrary") in paths

    def test_missing_file_returns_empty(self, tmp_path):
        paths = parse_library_folders(tmp_path / "nonexistent.vdf")
        assert paths == []

    def test_malformed_file_returns_empty(self, tmp_path):
        bad = tmp_path / "bad.vdf"
        bad.write_text("not a valid vdf file at all", encoding="utf-8")
        paths = parse_library_folders(bad)
        assert paths == []


class TestFindStarfieldInLibraries:
    def test_finds_starfield_in_mock_library(self, tmp_path):
        # Create a fake Steam library with Starfield
        game_dir = tmp_path / "steamapps" / "common" / "Starfield"
        data_dir = game_dir / "Data"
        data_dir.mkdir(parents=True)
        (data_dir / "Starfield.esm").touch()
        (game_dir / "ContentCatalog.txt").write_text("{}", encoding="utf-8")

        install = find_starfield_in_libraries([tmp_path])
        assert install is not None
        assert install.is_valid
        assert install.source == "auto-steam"

    def test_no_starfield_returns_none(self, tmp_path):
        install = find_starfield_in_libraries([tmp_path])
        assert install is None

    def test_empty_libraries_returns_none(self):
        install = find_starfield_in_libraries([])
        assert install is None
