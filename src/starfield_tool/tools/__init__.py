from starfield_tool.base import ToolModule
from starfield_tool.tools.broken_updates import BrokenUpdatesTool
from starfield_tool.tools.creation_load_order import CreationLoadOrderTool
from starfield_tool.tools.dependency_inspector import DependencyInspectorTool
from starfield_tool.tools.fast_lane_check import FastLaneCheckTool
from starfield_tool.tools.load_order import LoadOrderTool
from starfield_tool.tools.rulebook_manager import RuleBookTool


MODULES: list[type[ToolModule]] = [
    CreationLoadOrderTool,
    LoadOrderTool,
    RuleBookTool,
    FastLaneCheckTool,
    DependencyInspectorTool,
    BrokenUpdatesTool,
]
