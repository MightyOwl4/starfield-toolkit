"""Confirmation and result dialogs for the Detect Broken Updates tab.

Follow the same topmost-flash CTkToplevel pattern as remove_creation.py —
Win+D recoverable, no transient()/grab_set().
"""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from starfield_tool.broken_scan import BrokenDeletePlan, BrokenDeleteResult
from starfield_tool.dialogs import center_dialog


_CONFIRM_WIDTH = 640
_CONFIRM_HEIGHT = 540
_RESULT_WIDTH = 640
_RESULT_HEIGHT = 520


def _install_chrome(dlg: ctk.CTkToplevel, title: str) -> None:
    dlg.title(title)
    dlg.attributes("-topmost", True)
    dlg.after(100, lambda: dlg.attributes("-topmost", False))
    from starfield_tool.app import _icon_path
    icon = _icon_path()
    if icon.exists():
        dlg.after(200, lambda: dlg.iconbitmap(str(icon)))
    dlg.bind("<Escape>", lambda _e: dlg.destroy())


class BrokenConfirmDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        plan: BrokenDeletePlan,
        on_confirm: Callable[[], None],
    ):
        super().__init__(parent)
        _install_chrome(self, f"Delete {len(plan.flagged)} broken Creation(s)")
        center_dialog(self, _CONFIRM_WIDTH, _CONFIRM_HEIGHT)
        self.minsize(480, 360)

        self._plan = plan
        self._on_confirm = on_confirm
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self):
        button_row = ctk.CTkFrame(self, fg_color="transparent")
        button_row.pack(side="bottom", pady=(4, 10))
        ctk.CTkButton(
            button_row, text="Cancel", width=90, command=self.destroy,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            button_row, text="Confirm delete", width=150,
            fg_color="#a33", hover_color="#c44",
            command=self._do_confirm,
        ).pack(side="left", padx=4)

        # Warning banner — prominent, ABOVE the file list (FR-010).
        warn = ctk.CTkFrame(self, fg_color="#6a4a1a", corner_radius=4)
        warn.pack(fill="x", padx=14, pady=(12, 8))
        ctk.CTkLabel(
            warn,
            text=(
                "\u26a0  This operation does NOT perform a dependency check. "
                "If another Creation depends on one you delete, you are "
                "responsible for the fallout."
            ),
            text_color="#ffe4a0",
            wraplength=560, justify="left", anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(fill="x", padx=10, pady=8)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(4, 4))

        for flagged, rp in zip(self._plan.flagged, self._plan.removal_plans):
            ctk.CTkLabel(
                body, text=flagged.display_name, anchor="w",
                font=ctk.CTkFont(size=13, weight="bold"),
            ).pack(anchor="w", pady=(8, 2))
            if rp.plugin_files:
                ctk.CTkLabel(
                    body, text="  Plugins.txt lines to strip:", anchor="w",
                    text_color="#cccccc",
                ).pack(anchor="w")
                for pf in rp.plugin_files:
                    ctk.CTkLabel(
                        body, text=f"    \u2022 {pf}", anchor="w",
                        font=ctk.CTkFont(family="Consolas", size=12),
                    ).pack(anchor="w")
            if rp.files_to_delete:
                ctk.CTkLabel(
                    body, text="  Files to delete:", anchor="w",
                    text_color="#cccccc",
                ).pack(anchor="w", pady=(4, 0))
                for p in rp.files_to_delete:
                    ctk.CTkLabel(
                        body, text=f"    \u2022 {p.name}", anchor="w",
                        font=ctk.CTkFont(family="Consolas", size=12),
                    ).pack(anchor="w")
            if rp.out_of_tree_files:
                ctk.CTkLabel(
                    body, text="  Refused (out-of-tree — not touched):",
                    anchor="w", text_color="#ff9999",
                ).pack(anchor="w", pady=(4, 0))
                for e in rp.out_of_tree_files:
                    ctk.CTkLabel(
                        body, text=f"    \u2022 {e}", anchor="w",
                        font=ctk.CTkFont(family="Consolas", size=12),
                    ).pack(anchor="w")

    def _do_confirm(self):
        cb = self._on_confirm
        self.destroy()
        cb()


class BrokenResultDialog(ctk.CTkToplevel):
    def __init__(self, parent, result: BrokenDeleteResult):
        super().__init__(parent)
        _install_chrome(self, "Broken updates — result")
        center_dialog(self, _RESULT_WIDTH, _RESULT_HEIGHT)
        self.minsize(480, 320)

        self._result = result
        self._build_ui()

    def _build_ui(self):
        ctk.CTkButton(
            self, text="Close", width=90, command=self.destroy,
        ).pack(side="bottom", pady=(4, 10))

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=(12, 4))

        if self._result.game_was_running:
            ctk.CTkLabel(
                body,
                text=(
                    "Refused: Starfield or the Bethesda launcher was running. "
                    "Close both and retry."
                ),
                text_color="#ff6b6b",
                font=ctk.CTkFont(size=14, weight="bold"),
                wraplength=560, justify="left", anchor="w",
            ).pack(anchor="w")
            return

        # Alphabetical, selectable list of processed names.
        ctk.CTkLabel(
            body,
            text=f"Processed {len(self._result.display_names_processed)} Creation(s) "
                 "(select + copy to paste into the in-game Creations menu):",
            anchor="w", justify="left", wraplength=560,
        ).pack(anchor="w", pady=(0, 4))

        textbox = ctk.CTkTextbox(
            body, wrap="none", height=140,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        textbox.pack(fill="x")
        textbox.insert("1.0", "\n".join(self._result.display_names_processed))
        textbox.configure(state="disabled")

        # Per-Creation per-file outcomes.
        ctk.CTkLabel(
            body, text="Outcomes:", anchor="w",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", pady=(12, 2))

        for flagged, rr in self._result.results:
            deleted = sum(1 for o in rr.file_outcomes if o.status == "deleted")
            already = sum(1 for o in rr.file_outcomes if o.status == "already_gone")
            failed = [o for o in rr.file_outcomes if o.status == "failed"]
            color = "#ff6b6b" if failed else "#6bc46b"
            header = (
                f"{flagged.display_name}: "
                f"{deleted} deleted, {already} already gone, {len(failed)} failed"
                f"{' — plugins.txt updated' if rr.plugins_txt_updated else ''}"
            )
            ctk.CTkLabel(
                body, text=header, anchor="w",
                text_color=color, wraplength=560, justify="left",
            ).pack(anchor="w", pady=(6, 0))
            for o in failed:
                ctk.CTkLabel(
                    body,
                    text=f"    \u2022 {o.path.name} — {o.reason or 'unknown'}",
                    anchor="w", wraplength=560, justify="left",
                    font=ctk.CTkFont(family="Consolas", size=12),
                ).pack(anchor="w")
