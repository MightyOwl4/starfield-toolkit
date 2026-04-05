"""Rule Book management tool — view, enable/disable, reorder, create rule books."""
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import customtkinter as ctk

from starfield_tool.base import ToolModule, ModuleContext
from starfield_tool.config import _config_path, load_config, save_config


class RuleBookTool(ToolModule):
    name = "Rule Books"
    description = "Manage load order rule books — enable, disable, reorder, and create"

    def __init__(self):
        self._context: ModuleContext | None = None
        self._tree: ttk.Treeview | None = None
        self._registry: list[dict] = []
        self._book_data: dict[str, dict] = {}  # filename → loaded book data
        self._detail_text: ctk.CTkTextbox | None = None
        self._status_label: ctk.CTkLabel | None = None

    def initialize(self, context: ModuleContext) -> None:
        self._context = context
        frame = context.content_frame

        _btn_color = "#314c79"
        _btn_hover = "#3d5f99"
        _btn_font = ctk.CTkFont(size=12)
        _btn_kw = dict(
            height=26, corner_radius=4, font=_btn_font,
            fg_color=_btn_color, hover_color=_btn_hover,
        )

        # Top bar
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(2, 4))

        ctk.CTkButton(
            top, text="New", width=60, command=self._new_book, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Edit", width=60, command=self._edit_book, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Rescan", width=70, command=self._rescan, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Move Up", width=70, command=self._move_up, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Move Down", width=80, command=self._move_down, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Toggle", width=70, command=self._toggle_enabled, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        self._status_label = ctk.CTkLabel(top, text="")
        self._status_label.pack(side="right", padx=(8, 0))

        # Main area: tree (left) + details (right)
        main = ctk.CTkFrame(frame, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        # Treeview
        is_dark = ctk.get_appearance_mode() == "Dark"
        tree_bg = "#2b2b2b" if is_dark else "#ffffff"
        tree_fg = "#dcdcdc" if is_dark else "#1a1a1a"
        sel_bg = "#3d5f99" if is_dark else "#cce0ff"

        style = ttk.Style()
        style.configure(
            "RuleBook.Treeview",
            background=tree_bg, foreground=tree_fg, fieldbackground=tree_bg,
            rowheight=24, font=("Segoe UI", 10),
        )
        style.map("RuleBook.Treeview", background=[("selected", sel_bg)])

        tree_frame = tk.Frame(main, bg=tree_bg)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        columns = ("status", "source", "rules", "applicable")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="tree headings",
            style="RuleBook.Treeview", selectmode="browse",
        )
        self._tree.heading("#0", text="Name", anchor="w")
        self._tree.heading("status", text="Status", anchor="w")
        self._tree.heading("source", text="Source", anchor="w")
        self._tree.heading("rules", text="Rules", anchor="center")
        self._tree.heading("applicable", text="Match", anchor="center")

        self._tree.column("#0", width=200, minwidth=120)
        self._tree.column("status", width=80, minwidth=60)
        self._tree.column("source", width=70, minwidth=50)
        self._tree.column("rules", width=50, minwidth=40)
        self._tree.column("applicable", width=50, minwidth=40)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda _e: self._edit_book())
        self._tree.bind("<Button-1>", self._on_click_deselect)

        # Tag colors
        self._tree.tag_configure("disabled", foreground="#888888")
        self._tree.tag_configure("corrupted", foreground="#e74c3c")
        self._tree.tag_configure("inapplicable", foreground="#e7943c")
        self._tree.tag_configure("curated", foreground="#7a9ec4")

        # Details panel
        detail_frame = ctk.CTkFrame(main)
        detail_frame.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            detail_frame, text="Details", font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(padx=8, pady=(6, 2), anchor="w")

        self._detail_text = ctk.CTkTextbox(
            detail_frame, wrap="word", font=ctk.CTkFont(size=11),
            state="disabled", height=200,
        )
        self._detail_text.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        # Load data
        self._scan_and_populate()
        self._check_corrupted_on_startup()

    # --- Data loading ---

    def _get_user_rules_dir(self) -> Path:
        return _config_path().parent / "rules"

    def _get_curated_rules_dir(self) -> Path | None:
        if hasattr(sys, "_MEIPASS"):
            p = Path(sys._MEIPASS) / "data" / "rules"
            if p.is_dir():
                return p
        dev_path = Path(__file__).parent.parent.parent.parent / "data" / "rules"
        if dev_path.is_dir():
            return dev_path
        return None

    def _scan_and_populate(self):
        from load_order_sorter.rulebook import (
            discover_rulebooks, reconcile_registry, load_rulebook,
            normalize_rules, check_applicability,
        )

        user_dir = self._get_user_rules_dir()
        curated_dir = self._get_curated_rules_dir()
        discovered = discover_rulebooks(user_dir, curated_dir)

        settings = load_config()
        self._registry = reconcile_registry(discovered, settings.rulebook_registry)

        # Save reconciled registry
        settings.rulebook_registry = self._registry
        save_config(settings)

        # Build filepath lookup
        filepath_map = {
            (d["filename"], d["source"]): d["filepath"] for d in discovered
        }

        # Get installed plugins for applicability
        installed = set()
        if self._context and self._context.game_installation:
            from starfield_tool.parsers import parse_content_catalog
            entries = parse_content_catalog(
                self._context.game_installation.content_catalog
            )
            for e in entries:
                for f in e.files:
                    if f.endswith((".esm", ".esp", ".esl")):
                        installed.add(f)

        # Load each book
        self._book_data.clear()
        for entry in self._registry:
            key = (entry["filename"], entry["source"])
            filepath = filepath_map.get(key)
            if not filepath:
                continue

            book = load_rulebook(filepath)
            info = {
                "filename": entry["filename"],
                "source": entry["source"],
                "enabled": entry.get("enabled", True),
                "filepath": filepath,
            }

            if book is None:
                info.update(
                    name=entry["filename"],
                    description="",
                    rules=[],
                    rule_count=0,
                    applicable_count=0,
                    missing_plugins=set(),
                    is_applicable=False,
                    is_corrupted=True,
                )
            else:
                rules = normalize_rules(book.get("rules", []))
                applicable, missing, is_ok = check_applicability(rules, installed)
                info.update(
                    name=book.get("name", entry["filename"]),
                    description=book.get("description", ""),
                    rules=rules,
                    rule_count=len(rules),
                    applicable_count=len(applicable),
                    missing_plugins=missing,
                    is_applicable=is_ok,
                    is_corrupted=False,
                )

            self._book_data[entry["filename"]] = info

        self._populate_tree()

    def _populate_tree(self):
        if not self._tree:
            return
        self._tree.delete(*self._tree.get_children())

        for entry in self._registry:
            info = self._book_data.get(entry["filename"])
            if not info:
                continue

            enabled = entry.get("enabled", True)
            is_corrupted = info.get("is_corrupted", False)
            is_applicable = info.get("is_applicable", True)

            if is_corrupted:
                status = "CORRUPTED"
                tags = ("corrupted",)
            elif not enabled:
                status = "Disabled"
                tags = ("disabled",)
            elif not is_applicable:
                status = "N/A"
                tags = ("inapplicable",)
            else:
                status = "Active"
                tags = ("curated",) if entry["source"] == "curated" else ()

            source_label = "Curated" if entry["source"] == "curated" else "User"
            rule_count = info.get("rule_count", 0)
            applicable = info.get("applicable_count", 0)

            self._tree.insert(
                "", "end",
                iid=entry["filename"],
                text=info.get("name", entry["filename"]),
                values=(status, source_label, rule_count, applicable),
                tags=tags,
            )

    def _on_click_deselect(self, event):
        """Deselect when clicking on empty area of the treeview."""
        item = self._tree.identify_row(event.y)
        if not item:
            self._tree.selection_remove(*self._tree.selection())

    def _on_select(self, _event):
        sel = self._tree.selection()
        if not sel:
            return
        filename = sel[0]
        info = self._book_data.get(filename)
        if not info:
            return

        self._detail_text.configure(state="normal")
        self._detail_text.delete("1.0", "end")

        lines = []
        lines.append(f"Name: {info.get('name', '')}")
        lines.append(f"File: {info.get('filename', '')}")
        lines.append(f"Source: {info.get('source', '').title()}")
        lines.append(f"Description: {info.get('description', '')}")
        lines.append("")

        if info.get("is_corrupted"):
            lines.append("ERROR: This rule book could not be parsed.")
            lines.append("Reinstall, undo manual changes, or delete the file.")
            lines.append(f"Path: {info.get('filepath', '')}")
        elif not info.get("is_applicable"):
            lines.append("ERROR: This rule book is not applicable.")
            lines.append("None of its rules match installed creations.")
        else:
            lines.append(f"Rules: {info.get('rule_count', 0)} total, "
                         f"{info.get('applicable_count', 0)} applicable")

        missing = info.get("missing_plugins", set())
        if missing:
            lines.append("")
            lines.append("WARNING: Missing creations (not installed):")
            for m in sorted(missing):
                lines.append(f"  - {m}")

        if info.get("rules"):
            lines.append("")
            lines.append("--- Rules ---")
            for rule in info["rules"]:
                plugin = rule.get("plugin", "")
                after = ", ".join(rule.get("load_after", []))
                note = rule.get("note", "")
                lines.append(f"  {plugin} after [{after}]")
                if note:
                    lines.append(f"    Note: {note}")

        self._detail_text.insert("1.0", "\n".join(lines))
        self._detail_text.configure(state="disabled")

    # --- Actions ---

    def _toggle_enabled(self):
        sel = self._tree.selection()
        if not sel:
            return
        filename = sel[0]
        for entry in self._registry:
            if entry["filename"] == filename:
                entry["enabled"] = not entry.get("enabled", True)
                break
        self._save_registry()
        self._populate_tree()
        self._tree.selection_set(filename)

    def _move_up(self):
        self._move_selected(-1)

    def _move_down(self):
        self._move_selected(1)

    def _move_selected(self, direction: int):
        sel = self._tree.selection()
        if not sel:
            return
        filename = sel[0]

        # Find index in registry
        idx = None
        for i, entry in enumerate(self._registry):
            if entry["filename"] == filename:
                idx = i
                break
        if idx is None:
            return

        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self._registry):
            return

        # Only allow movement within same source group
        if self._registry[idx]["source"] != self._registry[new_idx]["source"]:
            return

        self._registry[idx], self._registry[new_idx] = (
            self._registry[new_idx], self._registry[idx]
        )
        self._save_registry()
        self._populate_tree()
        self._tree.selection_set(filename)

    def _rescan(self):
        self._scan_and_populate()
        self._set_status("Rescanned", "green")

    def _new_book(self):
        from starfield_tool.dialogs.rulebook_editor import RuleBookEditorDialog
        if not self._context:
            return
        dialog = RuleBookEditorDialog(
            self._tree,
            game_installation=self._context.game_installation,
            save_dir=self._get_user_rules_dir(),
        )
        dialog.wait_window()
        if dialog.saved:
            self._scan_and_populate()
            self._set_status("Rule book created", "green")

    def _edit_book(self):
        sel = self._tree.selection()
        if not sel:
            return
        filename = sel[0]
        info = self._book_data.get(filename)
        if not info:
            return

        from starfield_tool.dialogs.rulebook_editor import RuleBookEditorDialog
        if not self._context:
            return

        readonly = info.get("source") == "curated"
        dialog = RuleBookEditorDialog(
            self._tree,
            game_installation=self._context.game_installation,
            save_dir=self._get_user_rules_dir(),
            existing_book=info,
            readonly=readonly,
        )
        dialog.wait_window()
        if dialog.saved:
            self._scan_and_populate()
            self._set_status("Rule book updated", "green")

    def _check_corrupted_on_startup(self):
        """Show error dialog for any corrupted rule books, then deactivate them."""
        corrupted = [
            info for info in self._book_data.values()
            if info.get("is_corrupted")
        ]
        for info in corrupted:
            # Deactivate in registry
            for entry in self._registry:
                if entry["filename"] == info["filename"]:
                    entry["enabled"] = False
                    break

            messagebox.showerror(
                "Corrupted Rule Book",
                f"Corrupted rulebook detected: {info['filename']}\n\n"
                f"Either reinstall, undo any manual changes, "
                f"or delete from the data dir:\n"
                f"{info.get('filepath', '')}\n\n"
                f"Rulebook has been deactivated!",
            )

        if corrupted:
            self._save_registry()
            self._populate_tree()

    # --- Helpers ---

    def _save_registry(self):
        settings = load_config()
        settings.rulebook_registry = self._registry
        save_config(settings)

    def _set_status(self, text: str, color: str = ""):
        if self._status_label:
            self._status_label.configure(text=text, text_color=color)
            if self._tree:
                self._tree.after(
                    2000, lambda: self._status_label.configure(text="")
                )
