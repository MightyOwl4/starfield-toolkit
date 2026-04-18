"""Confirmation and result dialogs for the Remove Creation flow.

Both use the DiffDialog / CreationDetailsDialog topmost-flash pattern so
they survive Win+D minimise/restore and do not trap focus. No transient()
and no grab_set() — enforced by project UX convention.
"""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from starfield_tool.dialogs import center_dialog
from starfield_tool.removal import RemovalPlan, RemovalResult


_CONFIRM_WIDTH = 560
_CONFIRM_HEIGHT = 480
_RESULT_WIDTH = 560
_RESULT_HEIGHT = 460


def _install_window_chrome(dialog: ctk.CTkToplevel, title: str) -> None:
    dialog.title(title)
    dialog.attributes("-topmost", True)
    dialog.after(100, lambda: dialog.attributes("-topmost", False))
    from starfield_tool.app import _icon_path
    icon = _icon_path()
    if icon.exists():
        dialog.after(200, lambda: dialog.iconbitmap(str(icon)))
    dialog.bind("<Escape>", lambda _e: dialog.destroy())


class RemoveConfirmDialog(ctk.CTkToplevel):
    """Blocks only by convention — user must click Confirm or Cancel."""

    def __init__(
        self,
        parent,
        plan: RemovalPlan,
        on_confirm: Callable[[], None],
    ):
        super().__init__(parent)
        _install_window_chrome(self, f"Remove — {plan.display_name}")
        center_dialog(self, _CONFIRM_WIDTH, _CONFIRM_HEIGHT)
        self.minsize(420, 320)

        self._on_confirm = on_confirm
        self._plan = plan
        self._build_ui()

        # Closing the window is equivalent to Cancel — no mutation.
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self) -> None:
        plan = self._plan

        # Bottom button row
        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(side="bottom", pady=(4, 10))
        ctk.CTkButton(
            button_row, text="Cancel", width=90, command=self.destroy,
        ).pack(side="left", padx=4)
        confirm_btn = ctk.CTkButton(
            button_row, text="Confirm remove", width=140,
            fg_color="#a33", hover_color="#c44",
            command=self._do_confirm,
        )
        confirm_btn.pack(side="left", padx=4)

        # Body
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(12, 4))

        ctk.CTkLabel(
            body,
            text=f"Remove \u201c{plan.display_name}\u201d?",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
            wraplength=500,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        if plan.out_of_tree_files:
            confirm_btn.configure(state="disabled")
            ctk.CTkLabel(
                body,
                text=(
                    "Refused: one or more files in this Creation's catalog "
                    "entry resolve outside the Data directory. Remove is "
                    "blocked for safety."
                ),
                text_color="#ff6b6b",
                wraplength=500,
                justify="left",
                anchor="w",
            ).pack(anchor="w", pady=(0, 6))
            for entry in plan.out_of_tree_files:
                ctk.CTkLabel(
                    body, text=f"  • {entry}", anchor="w",
                ).pack(anchor="w")
            return

        if plan.plugin_files:
            ctk.CTkLabel(
                body,
                text="Plugin line(s) that will be stripped from Plugins.txt:",
                anchor="w", justify="left",
            ).pack(anchor="w", pady=(6, 2))
            for pf in plan.plugin_files:
                ctk.CTkLabel(
                    body, text=f"  • {pf}", anchor="w",
                    font=ctk.CTkFont(family="Consolas", size=12),
                ).pack(anchor="w")
        else:
            ctk.CTkLabel(
                body,
                text="No plugin file; Plugins.txt will not be modified.",
                anchor="w", justify="left",
                text_color="#999999",
            ).pack(anchor="w", pady=(6, 2))

        ctk.CTkLabel(
            body,
            text="Files that will be deleted from the Data directory:",
            anchor="w", justify="left",
        ).pack(anchor="w", pady=(10, 2))
        for path in plan.files_to_delete:
            ctk.CTkLabel(
                body, text=f"  • {path.name}", anchor="w",
                font=ctk.CTkFont(family="Consolas", size=12),
            ).pack(anchor="w")

        ctk.CTkLabel(
            body,
            text=(
                "Starfield and the Bethesda launcher MUST be closed. "
                "The operation will be refused otherwise."
            ),
            text_color="#dba54b",
            wraplength=500, justify="left", anchor="w",
        ).pack(anchor="w", pady=(12, 0))

    def _do_confirm(self) -> None:
        cb = self._on_confirm
        self.destroy()
        cb()


class RemoveResultDialog(ctk.CTkToplevel):
    def __init__(self, parent, result: RemovalResult, display_name: str):
        super().__init__(parent)
        _install_window_chrome(self, f"Remove result — {display_name}")
        center_dialog(self, _RESULT_WIDTH, _RESULT_HEIGHT)
        self.minsize(420, 280)

        self._result = result
        self._display_name = display_name
        self._build_ui()

    def _build_ui(self) -> None:
        result = self._result

        ctk.CTkButton(
            self, text="Close", width=90, command=self.destroy,
        ).pack(side="bottom", pady=(4, 10))

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(12, 4))

        if result.game_was_running:
            ctk.CTkLabel(
                body,
                text=(
                    "Refused: Starfield or the Bethesda launcher was running. "
                    "Close both and retry."
                ),
                text_color="#ff6b6b",
                wraplength=500, justify="left", anchor="w",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(anchor="w", pady=(0, 6))
            return

        deleted = [o for o in result.file_outcomes if o.status == "deleted"]
        already = [o for o in result.file_outcomes if o.status == "already_gone"]
        failed = [o for o in result.file_outcomes if o.status == "failed"]

        summary_color = "#ff6b6b" if failed else "#6bc46b"
        summary = (
            f"Deleted: {len(deleted)}  |  Already gone: {len(already)}  |  "
            f"Failed: {len(failed)}"
        )
        ctk.CTkLabel(
            body, text=summary, anchor="w",
            text_color=summary_color,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", pady=(0, 6))

        if result.plugins_txt_updated:
            ctk.CTkLabel(
                body,
                text=f"Plugins.txt updated — {len(result.plugin_lines_dropped)} line(s) removed.",
                anchor="w",
            ).pack(anchor="w", pady=(0, 2))
            for line in result.plugin_lines_dropped:
                ctk.CTkLabel(
                    body, text=f"  • {line}", anchor="w",
                    font=ctk.CTkFont(family="Consolas", size=12),
                ).pack(anchor="w")
        else:
            ctk.CTkLabel(
                body, text="Plugins.txt unchanged.",
                anchor="w", text_color="#999999",
            ).pack(anchor="w", pady=(0, 2))

        if failed:
            ctk.CTkLabel(
                body, text="Files that could NOT be removed:",
                anchor="w", text_color="#ff6b6b",
                font=ctk.CTkFont(weight="bold"),
            ).pack(anchor="w", pady=(10, 2))
            for o in failed:
                ctk.CTkLabel(
                    body,
                    text=f"  • {o.path.name} — {o.reason or 'unknown'}",
                    anchor="w", wraplength=500, justify="left",
                    font=ctk.CTkFont(family="Consolas", size=12),
                ).pack(anchor="w")
