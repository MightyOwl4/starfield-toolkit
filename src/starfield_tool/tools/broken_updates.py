"""Detect Broken Updates tool — find Creations with half-broken on-disk state."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from starfield_tool.base import ModuleContext, ToolModule
from starfield_tool.broken_scan import (
    BrokenDeleteResult,
    FlaggedCreation,
    build_delete_plan,
    scan_broken,
)
from starfield_tool.game_process import is_starfield_or_launcher_running
from starfield_tool.parsers import parse_content_catalog, parse_plugins_txt
from starfield_tool.removal import execute_removal


_REASON_LABEL = {
    "partial_files": "partial files",
    "esm_without_plugins_line": "esm without plugins.txt line",
    "mtime_skew": "mtime skew",
    "out_of_tree": "out of tree",
}


class BrokenUpdatesTool(ToolModule):
    name = "Detect Broken Updates"
    description = "Scan disk for half-broken Creations and clean them up"

    def __init__(self):
        self._context: ModuleContext | None = None
        self._flagged: list[FlaggedCreation] = []
        self._tree: ttk.Treeview | None = None
        self._empty_label: ctk.CTkLabel | None = None
        self._delete_btn: ctk.CTkButton | None = None

    def initialize(self, context: ModuleContext) -> None:
        self._context = context
        frame = context.content_frame

        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(2, 4))

        _btn_kw = dict(height=26, corner_radius=4)
        ctk.CTkButton(
            top, text="Scan", width=80, command=self._scan, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        self._delete_btn = ctk.CTkButton(
            top, text="Delete selected", width=140,
            fg_color="#a33", hover_color="#c44", state="disabled",
            command=self._start_delete, **_btn_kw,
        )
        self._delete_btn.pack(side="left", padx=(0, 6))

        intro = ctk.CTkLabel(
            top,
            text=(
                "Finds Creations with partial files, stripped plugins.txt "
                "lines, or mixed mtimes. Aggressive on purpose."
            ),
            text_color="#999999",
            font=ctk.CTkFont(size=11),
        )
        intro.pack(side="left", padx=(8, 0))

        self._tree_frame = tk.Frame(frame)
        self._tree_frame.pack(fill="both", expand=True, padx=8, pady=4)

        columns = ("Name", "Author", "Version", "Reason")
        self._tree = ttk.Treeview(
            self._tree_frame, columns=columns, show="headings",
            selectmode="extended",
        )
        for col, width in [("Name", 280), ("Author", 120), ("Version", 110),
                            ("Reason", 280)]:
            self._tree.heading(col, text=col, anchor="w")
            self._tree.column(col, width=width, anchor="w")

        scrollbar = ttk.Scrollbar(
            self._tree_frame, orient="vertical", command=self._tree.yview,
        )
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.tag_configure(
            "flagged", background="#5a2a2a", foreground="#ffdddd",
        )
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

        self._empty_label = ctk.CTkLabel(
            frame, text="Click Scan to check for broken updates.",
            font=ctk.CTkFont(size=13),
        )
        self._empty_label.pack(pady=12)

    # --- scan ---

    def _scan(self):
        if not self._context:
            return
        install = self._context.game_installation
        self._context.status_bar.set_task("Scanning for broken updates...")
        try:
            catalog = parse_content_catalog(install.content_catalog)
            plugins = parse_plugins_txt(install.plugins_txt)
            self._flagged = scan_broken(catalog, plugins, install.data_dir)
        finally:
            self._context.status_bar.clear_task()
        self._populate()

    def _populate(self):
        assert self._tree is not None
        for iid in self._tree.get_children():
            self._tree.delete(iid)

        if not self._flagged:
            self._empty_label.configure(text="No broken updates detected.")
            self._empty_label.pack(pady=12)
            self._delete_btn.configure(state="disabled")
            return

        self._empty_label.pack_forget()
        for f in self._flagged:
            reasons = " + ".join(_REASON_LABEL[r] for r in f.reasons)
            self._tree.insert(
                "", "end", iid=f.content_id,
                values=(f.display_name, f.author or "", f.catalog_version or "", reasons),
                tags=("flagged",),
            )
        self._delete_btn.configure(state="disabled")

    def _on_select(self, _event=None):
        if not self._tree:
            return
        has = bool(self._tree.selection())
        self._delete_btn.configure(state="normal" if has else "disabled")

    # --- delete ---

    def _selected_flagged(self) -> list[FlaggedCreation]:
        if not self._tree:
            return []
        selected = set(self._tree.selection())
        return [f for f in self._flagged if f.content_id in selected]

    def _start_delete(self):
        if not self._context:
            return
        selection = self._selected_flagged()
        if not selection:
            return

        if is_starfield_or_launcher_running():
            from starfield_tool.dialogs.broken_updates import BrokenResultDialog
            result = BrokenDeleteResult(game_was_running=True)
            BrokenResultDialog(self._tree, result)
            return

        install = self._context.game_installation
        plan = build_delete_plan(selection, install.plugins_txt, install.data_dir)

        from starfield_tool.dialogs.broken_updates import BrokenConfirmDialog

        def _on_confirm():
            self._context.status_bar.set_task(
                f"Deleting {len(selection)} Creation(s)..."
            )

            def _work():
                result = BrokenDeleteResult()
                for flagged, rp in zip(plan.flagged, plan.removal_plans):
                    rr = execute_removal(
                        rp, install.plugins_txt, process_probe=lambda: False,
                    )
                    result.results.append((flagged, rr))
                result.display_names_processed = sorted(
                    (f.display_name for f in plan.flagged), key=str.casefold,
                )
                self._tree.after(0, lambda: _on_complete(result))

            threading.Thread(target=_work, daemon=True).start()

        def _on_complete(result: BrokenDeleteResult):
            self._context.status_bar.clear_task()
            from starfield_tool.dialogs.broken_updates import BrokenResultDialog
            BrokenResultDialog(self._tree, result)
            self._scan()

        BrokenConfirmDialog(self._tree, plan, _on_confirm)
