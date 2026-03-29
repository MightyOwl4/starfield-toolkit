from starfield_tool.base import ToolModule, ModuleContext
from starfield_tool.tools.creation_load_order import CreationLoadOrderTool


class _LoadOrderPlaceholder(ToolModule):
    name = "Load Order"
    description = "Manage plugin load order (coming soon)"

    def initialize(self, context: ModuleContext) -> None:
        import customtkinter as ctk
        ctk.CTkLabel(
            context.content_frame, text="Coming soon",
            font=ctk.CTkFont(size=16), text_color="#777777",
        ).place(relx=0.5, rely=0.4, anchor="center")


MODULES: list[type[ToolModule]] = [
    CreationLoadOrderTool,
    _LoadOrderPlaceholder,
]
