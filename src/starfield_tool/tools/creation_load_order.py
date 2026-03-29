"""Creation Load Order tool — displays Bethesda store Creations in load order."""
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

import customtkinter as ctk

from starfield_tool.base import ToolModule, ModuleContext
from starfield_tool.models import Creation
from starfield_tool.parsers import build_creation_list


class CreationLoadOrderTool(ToolModule):
    name = "Installed Creations"
    description = "View installed Bethesda Creations in their load order, check for updates, export list"

    def __init__(self):
        self._context: ModuleContext | None = None
        self._creations: list[Creation] = []
        self._tree: ttk.Treeview | None = None
        self._outdated_label: ctk.CTkLabel | None = None
        self._update_summary: ctk.CTkLabel | None = None
        self._observer = None

    def initialize(self, context: ModuleContext) -> None:
        self._context = context
        frame = context.content_frame

        # Top bar with buttons left, status right
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(2, 4))

        _btn_color = "#314c79"  # Constellation blue
        _btn_hover = "#3d5f99"

        _btn_font = ctk.CTkFont(size=12)
        _btn_kw = dict(
            height=26, corner_radius=4, font=_btn_font,
            fg_color=_btn_color, hover_color=_btn_hover,
        )

        ctk.CTkButton(
            top, text="Refresh", width=70, command=self._refresh, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        self._update_btn = ctk.CTkButton(
            top, text="Check for Updates", width=120,
            command=self._check_updates, **_btn_kw,
        )
        self._update_btn.pack(side="left", padx=(0, 6))

        self._achiev_btn = ctk.CTkButton(
            top, text="Check Achievements", width=130,
            command=self._check_achievements, **_btn_kw,
        )
        self._achiev_btn.pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Export", width=60, command=self._export, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        self._update_summary = ctk.CTkLabel(top, text="")
        self._update_summary.pack(side="left", padx=8)

        self._achiev_summary = ctk.CTkLabel(top, text="")
        self._achiev_summary.pack(side="left", padx=8)

        self._outdated_label = ctk.CTkLabel(
            top, text="", text_color="orange"
        )
        self._outdated_label.pack(side="right", padx=8)

        # Theme detection
        is_dark = ctk.get_appearance_mode() == "Dark"
        if is_dark:
            bg = "#2b2b2b"
            fg = "#dcdcdc"
            sel_bg = "#314c79"
            heading_bg = "#1f1f1f"
            heading_fg = "#aaaaaa"
            border_color = "#3a3a3a"
        else:
            bg = "#ffffff"
            fg = "#000000"
            sel_bg = "#314c79"
            heading_bg = "#e0e0e0"
            heading_fg = "#333333"
            border_color = "#cccccc"

        # Style treeview to match dark/light theme
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=bg,
            foreground=fg,
            fieldbackground=bg,
            rowheight=28,
            borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background=heading_bg,
            foreground=heading_fg,
            borderwidth=1,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", sel_bg)],
            foreground=[("selected", fg)],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", border_color)],
        )
        # Style scrollbar to match
        style.configure(
            "Vertical.TScrollbar",
            background=heading_bg,
            troughcolor=bg,
            borderwidth=0,
            arrowcolor=fg,
        )

        # Treeview for creation list — use a tk.Frame for seamless bg
        tree_frame = tk.Frame(frame, bg=bg, highlightthickness=0)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        columns = ("#", "Name", "Version", "Date")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings", selectmode="browse"
        )
        self._tree.heading("#", text="#", anchor="center")
        self._tree.heading("Name", text="Name", anchor="w")
        self._tree.heading("Version", text="Version", anchor="w")
        self._tree.heading("Date", text="Date", anchor="w")

        self._tree.column("#", width=40, anchor="center", stretch=False)
        self._tree.column("Name", width=500, anchor="w")
        self._tree.column("Version", width=100, anchor="w", stretch=False)
        self._tree.column("Date", width=120, anchor="w", stretch=False)

        scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.tag_configure("missing", foreground="#666666")
        self._tree.tag_configure(
            "has_update", background="#dba54b", foreground="#1a1a1a"
        )
        self._tree.tag_configure(
            "not_achievement_friendly", background="#dba54b", foreground="#1a1a1a"
        )
        self._checked = False  # whether update check has been run
        self._achievements_checked = False

        # Empty state label (shown when no creations)
        self._empty_label = ctk.CTkLabel(
            frame, text="", font=ctk.CTkFont(size=14)
        )

        # Load data
        self._refresh()

        # Start file monitoring
        self._start_monitoring()

    def _refresh(self):
        if not self._context:
            return

        self._context.status_bar.set_task(
            f"Reading Creation list from {self._context.game_installation.data_dir}..."
        )

        # Clear outdated indicator
        if self._outdated_label:
            self._outdated_label.configure(text="")

        def _run():
            try:
                creations = build_creation_list(
                    self._context.game_installation
                )
                self._tree.after(0, lambda: self._on_refresh_complete(creations))
            except Exception as e:
                msg = str(e)
                self._tree.after(0, lambda: self._on_refresh_error(msg))

        threading.Thread(target=_run, daemon=True).start()

    def _on_refresh_complete(self, creations):
        self._creations = creations
        self._checked = False
        self._achievements_checked = False
        if self._update_summary:
            self._update_summary.configure(text="")
        if self._achiev_summary:
            self._achiev_summary.configure(text="")
        self._populate_tree()
        self._context.status_bar.clear_task()

    def _on_refresh_error(self, message):
        self._show_error(message)
        self._context.status_bar.clear_task()

        self._context.status_bar.clear_task()

    def _populate_tree(self):
        if not self._tree:
            return

        # Clear existing items
        for item in self._tree.get_children():
            self._tree.delete(item)

        if not self._creations:
            self._empty_label.configure(text="No Creations found")
            self._empty_label.pack(pady=20)
            return

        self._empty_label.pack_forget()

        for creation in self._creations:
            pos = str(creation.load_position + 1) if creation.load_position is not None else "-"
            version_text = creation.installed_version
            if self._checked and creation.has_update and creation.available_version:
                version_text = f"\u26a0 {creation.installed_version} \u2192 {creation.available_version}"
            elif self._checked and not creation.has_update:
                version_text = f"\u2713 {creation.installed_version}"

            tags = []
            if creation.file_missing:
                tags.append("missing")
            elif self._checked and creation.has_update:
                tags.append("has_update")
            elif self._achievements_checked and creation.achievement_friendly is False:
                tags.append("not_achievement_friendly")

            date_text = ""
            if creation.timestamp:
                date_text = creation.timestamp.strftime("%d %b %Y")

            self._tree.insert(
                "", "end",
                values=(pos, creation.display_name, version_text, date_text),
                tags=tuple(tags),
            )

    def _check_updates(self):
        if not self._context or not self._creations:
            return

        # Clear previous achievement check state to avoid mixed highlights
        self._achievements_checked = False
        if self._achiev_summary:
            self._achiev_summary.configure(text="")
        self._populate_tree()

        self._context.status_bar.set_task("Checking for updates...")
        self._update_btn.configure(state="disabled")

        def _run():
            try:
                from starfield_tool.version_checker import check_for_updates
                updated = check_for_updates(
                    self._creations, self._context.status_bar
                )
                # Schedule UI update on the main thread
                self._tree.after(0, lambda: self._on_updates_complete(updated))
            except Exception:
                self._tree.after(0, self._on_updates_failed)

        threading.Thread(target=_run, daemon=True).start()

    def _on_updates_complete(self, check_result):
        self._creations = check_result.creations
        self._checked = True
        update_count = sum(1 for c in self._creations if c.has_update)
        skipped = check_result.skipped
        if self._update_summary:
            parts = []
            if update_count > 0:
                parts.append(
                    f"{update_count} update{'s' if update_count != 1 else ''} available"
                )
            if skipped > 0:
                parts.append(
                    f"{skipped} skipped (not on Creations)"
                )
            if parts:
                self._update_summary.configure(
                    text=" \u2022 ".join(parts),
                    text_color="orange",
                )
            else:
                self._update_summary.configure(
                    text="All Creations up to date",
                    text_color="green",
                )
        self._populate_tree()
        self._context.status_bar.clear_task()
        self._update_btn.configure(state="normal")

    def _on_updates_failed(self):
        if self._update_summary:
            self._update_summary.configure(
                text="Update check failed", text_color="red"
            )
        self._context.status_bar.clear_task()
        self._update_btn.configure(state="normal")

    def _check_achievements(self):
        if not self._context or not self._creations:
            return

        # Clear previous update check state to avoid mixed highlights
        self._checked = False
        if self._update_summary:
            self._update_summary.configure(text="")
        self._populate_tree()

        self._context.status_bar.set_task("Checking achievements...")
        self._achiev_btn.configure(state="disabled")

        def _run():
            try:
                from starfield_tool.version_checker import check_achievements
                updated = check_achievements(
                    self._creations, self._context.status_bar
                )
                self._tree.after(0, lambda: self._on_achievements_complete(updated))
            except Exception:
                self._tree.after(0, self._on_achievements_failed)

        threading.Thread(target=_run, daemon=True).start()

    def _on_achievements_complete(self, check_result):
        self._creations = check_result.creations
        self._achievements_checked = True
        blockers = [c for c in self._creations if c.achievement_friendly is False]
        skipped = check_result.skipped
        if self._achiev_summary:
            if blockers:
                msg = "\u26a0 You have creations that will disable achievements"
                if skipped > 0:
                    msg += f" \u2022 {skipped} skipped (not on Creations)"
                self._achiev_summary.configure(
                    text=msg,
                    text_color="orange",
                )
            else:
                msg = "\u2713 All creations are achievement friendly"
                if skipped > 0:
                    msg += f" \u2022 {skipped} skipped (not on Creations)"
                self._achiev_summary.configure(
                    text=msg,
                    text_color="green" if skipped == 0 else "orange",
                )
        self._populate_tree()
        self._context.status_bar.clear_task()
        self._achiev_btn.configure(state="normal")

    def _on_achievements_failed(self):
        if self._achiev_summary:
            self._achiev_summary.configure(
                text="Achievement check failed", text_color="red"
            )
        self._context.status_bar.clear_task()
        self._achiev_btn.configure(state="normal")

    def _show_error(self, message: str):
        if self._tree:
            for item in self._tree.get_children():
                self._tree.delete(item)
        self._empty_label.configure(text=f"Error: {message}")
        self._empty_label.pack(pady=20)

    def _export(self):
        """Export the creation list as markdown table (.txt) or CSV."""
        if not self._creations:
            return

        path = filedialog.asksaveasfilename(
            title="Export Creation List",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv")],
        )
        if not path:
            return

        rows = []
        for c in self._creations:
            pos = str(c.load_position + 1) if c.load_position is not None else "-"
            date = c.timestamp.strftime("%d %b %Y") if c.timestamp else ""
            rows.append((pos, c.display_name, c.author, c.installed_version, date))

        headers = ("#", "Name", "Author", "Version", "Date")

        if path.endswith(".csv"):
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(rows)
        else:
            # Markdown table with space-padded columns
            widths = [len(h) for h in headers]
            for row in rows:
                for i, val in enumerate(row):
                    widths[i] = max(widths[i], len(val))

            def _fmt_row(values):
                cells = [v.ljust(widths[i]) for i, v in enumerate(values)]
                return "| " + " | ".join(cells) + " |"

            lines = [
                _fmt_row(headers),
                "| " + " | ".join("-" * w for w in widths) + " |",
            ]
            for row in rows:
                lines.append(_fmt_row(row))

            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

    def _start_monitoring(self):
        """Watch Plugins.txt and ContentCatalog.txt for changes."""
        if not self._context:
            return

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            install = self._context.game_installation
            files_to_watch = {
                install.content_catalog.name,
                install.plugins_txt.name,
            }
            dirs_to_watch = set()
            if install.content_catalog.parent.exists():
                dirs_to_watch.add(str(install.content_catalog.parent))
            if install.plugins_txt.parent.exists():
                dirs_to_watch.add(str(install.plugins_txt.parent))

            tool = self

            class ChangeHandler(FileSystemEventHandler):
                def on_modified(self, event):
                    if Path(event.src_path).name in files_to_watch:
                        if tool._outdated_label:
                            tool._outdated_label.configure(
                                text="Data outdated — click Refresh"
                            )

            handler = ChangeHandler()
            self._observer = Observer()
            for d in dirs_to_watch:
                self._observer.schedule(handler, d, recursive=False)
            self._observer.daemon = True
            self._observer.start()
        except Exception:
            pass  # File monitoring is best-effort
