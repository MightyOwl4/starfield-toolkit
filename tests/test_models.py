from pathlib import Path

from starfield_tool.models import Creation, GameInstallation


class TestGameInstallation:
    def test_valid_installation(self, tmp_path):
        data_dir = tmp_path / "Data"
        data_dir.mkdir()
        (data_dir / "Starfield.esm").touch()
        install = GameInstallation(game_root=tmp_path)
        assert install.is_valid is True
        assert install.data_dir == data_dir

    def test_missing_directory(self):
        install = GameInstallation(game_root=Path("/nonexistent/path"))
        assert install.is_valid is False

    def test_missing_data_subdir(self, tmp_path):
        install = GameInstallation(game_root=tmp_path)
        assert install.is_valid is False

    def test_data_dir_without_esm(self, tmp_path):
        (tmp_path / "Data").mkdir()
        install = GameInstallation(game_root=tmp_path)
        assert install.is_valid is False

    def test_source_default(self):
        install = GameInstallation(game_root=Path("."))
        assert install.source == "manual"


class TestCreation:
    def test_defaults(self):
        c = Creation(content_id="abc", display_name="Test")
        assert c.available_version is None
        assert c.has_update is False
        assert c.file_missing is False
        assert c.load_position is None
        assert c.plugin_files == []

    def test_fields(self):
        c = Creation(
            content_id="123",
            display_name="My Creation",
            author="Author",
            installed_version="1.0",
            plugin_files=["test.esm"],
            load_position=5,
            is_active=True,
        )
        assert c.display_name == "My Creation"
        assert c.load_position == 5
        assert c.is_active is True
