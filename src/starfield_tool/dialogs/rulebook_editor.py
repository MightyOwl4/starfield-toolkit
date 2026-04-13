"""Rule book editor dialog — create and edit load order rule books."""
from pathlib import Path
from tkinter import ttk

import customtkinter as ctk

from starfield_tool.models import GameInstallation


class RuleBookEditorDialog(ctk.CTkToplevel):
    """Dialog for creating or editing a rule book.

    In create mode: empty form, user picks creations and arranges them.
    In edit mode: pre-populated from existing book data.
    In readonly mode: all fields disabled, no save.
    """

    def __init__(
        self,
        parent,
        game_installation: GameInstallation,
        save_dir: Path,
        existing_book: dict | None = None,
        readonly: bool = False,
    ):
        super().__init__(parent)
        self.saved = False
        self._save_dir = save_dir
        self._game_install = game_installation
        self._existing = existing_book
        self._readonly = readonly

        title = (
            "View Rule Book" if readonly
            else "Edit Rule Book" if existing_book
            else "New Rule Book"
        )
        self.title(title)
        self.minsize(500, 400)

        from starfield_tool.dialogs import center_dialog
        center_dialog(self, 700, 550)

        # DiffDialog windowing pattern — no grab_set / transient
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        from starfield_tool.app import _icon_path
        icon = _icon_path()
        if icon.exists():
            self.after(200, lambda: self.iconbitmap(str(icon)))

        self._build_ui()
        if existing_book:
            self._load_existing(existing_book)

        self.bind("<Escape>", lambda _e: self.destroy())

    def _build_ui(self):
        _btn_color = "#314c79"
        _btn_hover = "#3d5f99"
        _btn_font = ctk.CTkFont(size=12)
        _btn_kw = dict(
            height=26, corner_radius=4, font=_btn_font,
            fg_color=_btn_color, hover_color=_btn_hover,
        )

        # Name and description
        meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        meta_frame.pack(fill="x", padx=10, pady=(10, 4))

        ctk.CTkLabel(meta_frame, text="Name:", font=ctk.CTkFont(size=12)).grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        self._name_entry = ctk.CTkEntry(meta_frame, width=300)
        self._name_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ctk.CTkLabel(meta_frame, text="Description:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=(4, 0)
        )
        self._desc_entry = ctk.CTkEntry(meta_frame, width=300)
        self._desc_entry.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(4, 0))
        meta_frame.columnconfigure(1, weight=1)

        # Main area: available (left) + selected (right)
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=4)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.columnconfigure(2, weight=1)
        main.rowconfigure(0, weight=1)

        # Available creations
        avail_frame = ctk.CTkFrame(main)
        avail_frame.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            avail_frame, text="Available Creations",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(padx=6, pady=(4, 2), anchor="w")

        self._avail_tree = ttk.Treeview(
            avail_frame, show="tree", selectmode="extended",
        )
        self._avail_tree.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Center buttons (add/remove)
        btn_frame = ctk.CTkFrame(main, fg_color="transparent")
        btn_frame.grid(row=0, column=1, padx=6)

        ctk.CTkButton(
            btn_frame, text="→", width=30, command=self._add_selected, **_btn_kw,
        ).pack(pady=(80, 4))

        ctk.CTkButton(
            btn_frame, text="←", width=30, command=self._remove_selected, **_btn_kw,
        ).pack(pady=4)

        ctk.CTkButton(
            btn_frame, text="↑", width=30, command=self._move_sel_up, **_btn_kw,
        ).pack(pady=(20, 4))

        ctk.CTkButton(
            btn_frame, text="↓", width=30, command=self._move_sel_down, **_btn_kw,
        ).pack(pady=4)

        # Selected creations (rule order)
        sel_frame = ctk.CTkFrame(main)
        sel_frame.grid(row=0, column=2, sticky="nsew")

        ctk.CTkLabel(
            sel_frame, text="Rule Order (top loads first)",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(padx=6, pady=(4, 2), anchor="w")

        self._sel_tree = ttk.Treeview(
            sel_frame, show="tree", selectmode="browse",
        )
        self._sel_tree.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        # Warning tag for missing creations
        self._sel_tree.tag_configure("missing", foreground="#e7943c")

        # Bottom buttons
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=(4, 10))

        if not self._readonly:
            ctk.CTkButton(
                bottom, text="Save", width=80, command=self._save, **_btn_kw,
            ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            bottom, text="Close" if self._readonly else "Cancel",
            width=80, command=self.destroy, **_btn_kw,
        ).pack(side="right")

        # Populate available creations
        self._populate_available()

        if self._readonly:
            self._name_entry.configure(state="disabled")
            self._desc_entry.configure(state="disabled")

    def _populate_available(self):
        """Fill the available creations list in load order with # and name.

        Only shows creations that have a load position (are in plugins.txt).
        """
        if not self._game_install:
            return
        from starfield_tool.parsers import build_creation_list

        creations = build_creation_list(self._game_install)

        for creation in creations:
            if creation.load_position is None:
                continue  # not in load order, skip
            display = f"#{creation.load_position + 1}  {creation.display_name}"
            for f in creation.plugin_files:
                if f.endswith((".esm", ".esp", ".esl")):
                    self._avail_tree.insert("", "end", iid=f, text=display)
                    break

    def _load_existing(self, book: dict):
        """Pre-populate from an existing rule book."""
        self._name_entry.insert(0, book.get("name", ""))
        self._desc_entry.insert(0, book.get("description", ""))

        # Get available creation names for display
        avail_by_filename = {
            iid: self._avail_tree.item(iid)["text"]
            for iid in self._avail_tree.get_children()
        }

        # Build ordered list from rules
        seen = set()
        for rule in book.get("rules", []):
            plugin = rule.get("plugin", "")
            if plugin in seen:
                continue
            seen.add(plugin)

            display = avail_by_filename.get(plugin, plugin)
            tags = () if plugin in avail_by_filename else ("missing",)
            self._sel_tree.insert("", "end", iid=plugin, text=display, tags=tags)

            # Also add load_after targets that aren't already in the list
            for dep in rule.get("load_after", []):
                if dep not in seen:
                    seen.add(dep)
                    dep_display = avail_by_filename.get(dep, dep)
                    dep_tags = () if dep in avail_by_filename else ("missing",)
                    # Insert before the current plugin
                    idx = list(self._sel_tree.get_children()).index(plugin)
                    self._sel_tree.move(
                        self._sel_tree.insert(
                            "", "end", iid=dep, text=dep_display, tags=dep_tags
                        ),
                        "", idx,
                    )

    def _add_selected(self):
        if self._readonly:
            return
        for iid in self._avail_tree.selection():
            if iid not in self._sel_tree.get_children():
                text = self._avail_tree.item(iid)["text"]
                self._sel_tree.insert("", "end", iid=iid, text=text)

    def _remove_selected(self):
        if self._readonly:
            return
        for iid in self._sel_tree.selection():
            self._sel_tree.delete(iid)

    def _move_sel_up(self):
        if self._readonly:
            return
        sel = self._sel_tree.selection()
        if not sel:
            return
        iid = sel[0]
        children = list(self._sel_tree.get_children())
        idx = children.index(iid)
        if idx > 0:
            self._sel_tree.move(iid, "", idx - 1)

    def _move_sel_down(self):
        if self._readonly:
            return
        sel = self._sel_tree.selection()
        if not sel:
            return
        iid = sel[0]
        children = list(self._sel_tree.get_children())
        idx = children.index(iid)
        if idx < len(children) - 1:
            self._sel_tree.move(iid, "", idx + 1)

    def _save(self):
        from load_order_sorter.rulebook import save_rulebook

        name = self._name_entry.get().strip()
        if not name:
            from tkinter import messagebox
            messagebox.showwarning("Missing Name", "Please enter a rule book name.")
            return

        description = self._desc_entry.get().strip()
        children = list(self._sel_tree.get_children())

        if len(children) < 2:
            from tkinter import messagebox
            messagebox.showwarning(
                "Not Enough Creations",
                "A rule book needs at least 2 creations to define ordering."
            )
            return

        # Generate rules: each creation has load_after pointing to the one above
        rules = []
        for i, plugin in enumerate(children):
            if i == 0:
                continue  # first item has no load_after
            rules.append({
                "plugin": plugin,
                "load_after": [children[i - 1]],
            })

        book = {
            "name": name,
            "description": description,
            "version": "1.0",
            "rules": rules,
        }

        # Determine filename
        if self._existing and self._existing.get("source") == "user":
            filepath = self._existing["filepath"]
        else:
            # Generate filename from name
            safe_name = "".join(
                c if c.isalnum() or c in "-_ " else ""
                for c in name
            ).strip().replace(" ", "_").lower()
            filepath = self._save_dir / f"{safe_name}.json"

        save_rulebook(book, filepath)
        self.saved = True
        self.destroy()
