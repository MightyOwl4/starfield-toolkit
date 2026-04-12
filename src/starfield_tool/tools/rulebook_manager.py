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
        self._installed: set[str] = set()
        self._hide_na_rules = True  # hide non-applicable rules in details

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

        # "Hide non-applicable rules" toggle — right-aligned
        _toggle_frame = ctk.CTkFrame(top, fg_color="transparent")
        _toggle_frame.pack(side="right", padx=(0, 4))
        ctk.CTkLabel(
            _toggle_frame, text="Hide non-applicable rules",
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 6))
        self._hide_na_switch = ctk.CTkSwitch(
            _toggle_frame, text="", width=40,
            command=self._toggle_hide_na_rules,
        )
        self._hide_na_switch.pack(side="left")
        if self._hide_na_rules:
            self._hide_na_switch.select()

        self._status_label = ctk.CTkLabel(top, text="")
        self._status_label.pack(side="right", padx=(8, 0))

        # Main area: tree (left) + details (right)
        main = ctk.CTkFrame(frame, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=8, pady=(0, 4))
        # minsize prevents either pane from being squeezed to zero when the
        # user drags the window smaller — weights alone aren't enough.
        main.columnconfigure(0, weight=2, minsize=300)
        main.columnconfigure(1, weight=3, minsize=280)
        main.rowconfigure(0, weight=1)

        # Treeview
        is_dark = ctk.get_appearance_mode() == "Dark"
        tree_bg = "#2b2b2b" if is_dark else "#ffffff"
        tree_fg = "#dcdcdc" if is_dark else "#1a1a1a"
        sel_bg = "#3d5f99" if is_dark else "#cce0ff"

        style = ttk.Style()
        from starfield_tool.grid_style import grid_font, grid_rowheight
        style.configure(
            "RuleBook.Treeview",
            background=tree_bg, foreground=tree_fg, fieldbackground=tree_bg,
            rowheight=grid_rowheight(), font=grid_font(),
        )
        style.map("RuleBook.Treeview", background=[("selected", sel_bg)])

        tree_frame = tk.Frame(main, bg=tree_bg)
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        columns = ("status", "maintainer", "rules", "applicable")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="tree headings",
            style="RuleBook.Treeview", selectmode="browse",
        )
        self._tree.heading("#0", text="Name", anchor="w")
        self._tree.heading("status", text="Status", anchor="w")
        self._tree.heading("maintainer", text="Maintainer", anchor="w")
        self._tree.heading("rules", text="Rules", anchor="center")
        self._tree.heading("applicable", text="Match", anchor="center")

        self._tree.column("#0", width=320, minwidth=180)
        self._tree.column("status", width=80, minwidth=60)
        self._tree.column("maintainer", width=140, minwidth=80)
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

        # Tags for styled text in detail panel
        self._detail_text._textbox.tag_configure(
            "bold", font=("Segoe UI", 11, "bold"))
        self._detail_text._textbox.tag_configure(
            "grey", foreground="#888888")

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
            normalize_rules, check_applicability, check_tier_applicability,
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
        self._installed = set()
        installed = self._installed
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
                    maintainer_name="n/a",
                    maintainer_url="",
                    rules=[],
                    rule_count=0,
                    applicable_count=0,
                    missing_plugins=set(),
                    is_applicable=False,
                    is_corrupted=True,
                )
            else:
                maintainer = book.get("maintainer", {})
                info["maintainer_name"] = maintainer.get("name", "n/a") if isinstance(maintainer, dict) else "n/a"
                info["maintainer_url"] = maintainer.get("url", "") if isinstance(maintainer, dict) else ""

                book_type = book.get("type", "order")
                raw_rules = book.get("rules", [])

                if book_type == "tier":
                    applicable, missing, is_ok = check_tier_applicability(
                        raw_rules, installed,
                    )
                    info.update(
                        name=book.get("name", entry["filename"]),
                        description=book.get("description", ""),
                        book_type="tier",
                        rules=raw_rules,
                        rule_count=len(raw_rules),
                        applicable_count=len(applicable),
                        missing_plugins=missing,
                        is_applicable=is_ok,
                        is_corrupted=False,
                    )
                else:
                    rules = normalize_rules(raw_rules)
                    applicable, missing, is_ok = check_applicability(
                        rules, installed,
                    )
                    info.update(
                        name=book.get("name", entry["filename"]),
                        description=book.get("description", ""),
                        book_type="order",
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

            maintainer = info.get("maintainer_name", "n/a")
            rule_count = info.get("rule_count", 0)
            applicable = info.get("applicable_count", 0)

            self._tree.insert(
                "", "end",
                iid=entry["filename"],
                text=info.get("name", entry["filename"]),
                values=(status, maintainer, rule_count, applicable),
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
        tw = self._detail_text._textbox

        def _kv(key: str, value: str, value_tag: str = ""):
            """Insert a bold key + normal value line."""
            tw.insert("end", key, "bold")
            if value_tag:
                tw.insert("end", f" {value}\n", value_tag)
            else:
                tw.insert("end", f" {value}\n")

        _kv("Name:", info.get("name", ""))
        if info.get("source") == "curated":
            _kv("Path:", "embedded", "grey")
        else:
            _kv("Path:", str(info.get("filepath", "")))
        _kv("Maintainer:", info.get("maintainer_name", "n/a"))
        maintainer_url = info.get("maintainer_url", "")
        if maintainer_url:
            _kv("URL:", maintainer_url)
        _kv("Description:", info.get("description", ""))
        tw.insert("end", "\n")

        if info.get("is_corrupted"):
            tw.insert("end", "ERROR: This rule book could not be parsed.\n")
            tw.insert("end", "Reinstall, undo manual changes, or delete the file.\n")
        elif not info.get("is_applicable"):
            tw.insert("end", "No rules match installed creations.\n")
        else:
            _kv("Rules:", f"{info.get('rule_count', 0)} total, "
                 f"{info.get('applicable_count', 0)} applicable")

        missing = info.get("missing_plugins", set())
        if missing:
            tw.insert("end", "\n")
            tw.insert("end", "Missing creations (not installed):\n", "bold")
            for m in sorted(missing):
                tw.insert("end", f"  - {m}\n")

        if info.get("rules"):
            is_tier = info.get("book_type") == "tier"
            installed_lower = {p.lower() for p in self._installed}

            def _rule_applicable(rule):
                p = rule.get("plugin", "").lower()
                if p not in installed_lower:
                    return False
                if is_tier:
                    return True
                return any(
                    d.lower() in installed_lower
                    for d in rule.get("load_after", [])
                )

            rules = info["rules"]
            if self._hide_na_rules:
                rules = [r for r in rules if _rule_applicable(r)]

            if rules:
                tw.insert("end", "\n")
                heading = "Tier Overrides" if is_tier else "Rules"
                tw.insert("end", f"{heading}\n", "bold")
                for rule in rules:
                    plugin = rule.get("plugin", "")
                    note = rule.get("note", "")
                    if is_tier:
                        tier = rule.get("tier", "?")
                        tw.insert("end", f"  {plugin} \u2192 tier {tier}\n")
                    else:
                        after = ", ".join(rule.get("load_after", []))
                        tw.insert("end", f"  {plugin} after [{after}]\n")
                    if note:
                        tw.insert("end", f"    {note}\n", "grey")

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

    def _toggle_hide_na_rules(self):
        self._hide_na_rules = self._hide_na_switch.get() == 1
        # Re-render the currently selected detail panel
        self._on_select(None)

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

        if info.get("book_type") == "tier":
            messagebox.showinfo(
                "Tier Rule Book",
                "Tier rule books must be edited as JSON files.\n\n"
                f"Path: {info.get('filepath', '')}",
            )
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
