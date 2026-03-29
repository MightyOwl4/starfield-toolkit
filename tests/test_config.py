import json

from starfield_tool.config import AppSettings, load_config, save_config


class TestLoadConfig:
    def test_missing_file_returns_defaults(self, tmp_config):
        settings = load_config(tmp_config)
        assert settings.game_path is None
        assert settings.window_geometry is None

    def test_corrupted_json_returns_defaults(self, tmp_config):
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text("not valid json {{{", encoding="utf-8")
        settings = load_config(tmp_config)
        assert settings.game_path is None

    def test_load_valid_config(self, tmp_config):
        tmp_config.parent.mkdir(parents=True, exist_ok=True)
        tmp_config.write_text(
            json.dumps({"game_path": "C:/Games/Starfield", "window_geometry": "800x600"}),
            encoding="utf-8",
        )
        settings = load_config(tmp_config)
        assert settings.game_path == "C:/Games/Starfield"
        assert settings.window_geometry == "800x600"


class TestSaveConfig:
    def test_creates_file_and_dir(self, tmp_path):
        config_path = tmp_path / "subdir" / "config.json"
        settings = AppSettings(game_path="C:/test")
        save_config(settings, config_path)
        assert config_path.exists()

    def test_round_trip(self, tmp_config):
        original = AppSettings(game_path="C:/Starfield", window_geometry="1024x768")
        save_config(original, tmp_config)
        loaded = load_config(tmp_config)
        assert loaded.game_path == original.game_path
        assert loaded.window_geometry == original.window_geometry
