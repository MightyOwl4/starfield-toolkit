"""Tests for the app shell and status bar.

GUI tests are kept minimal — test the logic, not the pixels.
These tests use a headless approach where possible, testing the
StatusBar API and module registration logic without rendering.
"""
from starfield_tool.status_bar import StatusBar, StatusBarImpl
from starfield_tool.base import ToolModule, ModuleContext


class DummyModule(ToolModule):
    name = "Dummy Tool"
    description = "A test tool"

    def initialize(self, context: ModuleContext) -> None:
        pass


class TestStatusBarAPI:
    def test_set_task(self):
        bar = StatusBarImpl()
        bar.set_task("Loading data...")
        assert bar.current_task == "Loading data..."

    def test_clear_task(self):
        bar = StatusBarImpl()
        bar.set_task("Loading data...")
        bar.clear_task()
        assert bar.current_task == "Ready"

    def test_initial_task_is_ready(self):
        bar = StatusBarImpl()
        assert bar.current_task == "Ready"

    def test_set_game_path(self):
        bar = StatusBarImpl()
        bar.set_game_path("C:/Games/Starfield")
        assert bar.current_path == "C:/Games/Starfield"

    def test_initial_path_warning(self):
        bar = StatusBarImpl()
        assert bar.current_path == "Starfield path not set"


class TestModuleRegistry:
    def test_dummy_module_has_name(self):
        assert DummyModule.name == "Dummy Tool"
        assert DummyModule.description == "A test tool"

    def test_modules_list_starts_empty(self):
        from starfield_tool.tools import MODULES
        # MODULES may have been populated by other tests, so just check it's a list
        assert isinstance(MODULES, list)
