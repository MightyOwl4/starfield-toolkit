from starfield_tool.base import ToolModule
from starfield_tool.tools.creation_load_order import CreationLoadOrderTool
from starfield_tool.tools.load_order import LoadOrderTool


MODULES: list[type[ToolModule]] = [
    CreationLoadOrderTool,
    LoadOrderTool,
]
