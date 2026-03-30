"""Load Order tool — manage plugin load order with sorting and snapshots."""
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from pathlib import Path

import customtkinter as ctk

from dataclasses import dataclass, field

from starfield_tool.base import ToolModule, ModuleContext


@dataclass
class _CreationGroup:
    """A creation that may contain one or more plugin files, treated as a unit."""
    key: str  # first plugin filename — used as group identity
    display_name: str  # creation title from catalog
    files: list[str] = field(default_factory=list)  # all plugin files in order
    content_id: str = ""
    categories: list[str] = field(default_factory=list)

    @property
    def plugin_label(self) -> str:
        if len(self.files) <= 1:
            return self.files[0] if self.files else ""
        return f"{self.files[0]}, and {len(self.files) - 1} more"


class LoadOrderTool(ToolModule):
    name = "Load Order"
    description = "Manage plugin load order with drag-and-drop, auto sort, and snapshots"

    def __init__(self):
        self._context: ModuleContext | None = None
        self._plugins: list[str] = []  # current saved order (plugin filenames)
        self._groups: list[_CreationGroup] = []  # saved grouped order
        self._working_groups: list[_CreationGroup] = []  # working grouped order
        self._dirty_items: set[str] = set()  # group keys that moved
        self._original_positions: dict[str, int] = {}  # group key → position before move
        self._tree: ttk.Treeview | None = None
        self._apply_btn = None
        self._discard_btn = None

    def initialize(self, context: ModuleContext) -> None:
        self._context = context
        frame = context.content_frame

        # Top bar
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(2, 4))

        _btn_color = "#314c79"
        _btn_hover = "#3d5f99"
        _btn_font = ctk.CTkFont(size=12)
        _btn_kw = dict(height=26, corner_radius=4, font=_btn_font,
                       fg_color=_btn_color, hover_color=_btn_hover)

        ctk.CTkButton(
            top, text="Refresh", width=70, command=self._refresh, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        self._apply_btn = ctk.CTkButton(
            top, text="Apply", width=60, command=self._apply, **_btn_kw,
        )
        self._apply_btn.pack(side="left", padx=(0, 6))

        self._discard_btn = ctk.CTkButton(
            top, text="Discard", width=70, command=self._discard, **_btn_kw,
        )
        self._discard_btn.pack(side="left", padx=(0, 6))

        # Separator — fixed height, horizontally centered between button groups
        sep = tk.Frame(top, width=1, height=20, bg="#444444")
        sep.pack(side="left", padx=(4, 10))
        sep.pack_propagate(False)

        ctk.CTkButton(
            top, text="Auto Sort", width=80, command=self._auto_sort, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Save Snapshot", width=100, command=self._save_snapshot, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Load Snapshot", width=100, command=self._load_snapshot, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        self._status_label = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=11))
        self._status_label.pack(side="left", padx=8)

        # Theme
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if is_dark else "#ffffff"
        fg = "#dcdcdc" if is_dark else "#000000"
        heading_bg = "#1f1f1f" if is_dark else "#e0e0e0"
        heading_fg = "#aaaaaa" if is_dark else "#333333"

        style = ttk.Style()
        style.configure("LO.Treeview", background=bg, foreground=fg,
                        fieldbackground=bg, rowheight=28, borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("LO.Treeview.Heading", background=heading_bg,
                        foreground=heading_fg, borderwidth=1, relief="flat",
                        font=("Segoe UI", 9, "bold"))
        style.map("LO.Treeview",
                  background=[("selected", "#314c79")],
                  foreground=[("selected", fg)])

        # Treeview
        tree_frame = tk.Frame(frame, bg=bg, highlightthickness=0)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        columns = ("#", "From", "Name", "Plugin")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            selectmode="browse", style="LO.Treeview",
        )
        self._tree.heading("#", text="#", anchor="center")
        self._tree.heading("From", text="From", anchor="center")
        self._tree.heading("Name", text="Creation Name", anchor="w")
        self._tree.heading("Plugin", text="Plugin", anchor="w")
        self._tree.column("#", width=40, anchor="center", stretch=False)
        self._tree.column("From", width=50, anchor="center", stretch=False)
        self._tree.column("Name", width=400, anchor="w")
        self._tree.column("Plugin", width=200, anchor="w", stretch=False)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical",
                                  command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self._tree.tag_configure("dirty",
                                  background="#dba54b", foreground="#1a1a1a")

        # Drag-and-drop bindings
        self._drag_item = None
        self._tree.bind("<ButtonPress-1>", self._on_drag_start)
        self._tree.bind("<B1-Motion>", self._on_drag_motion)
        self._tree.bind("<ButtonRelease-1>", self._on_drag_end)

        # Empty state
        self._empty_label = ctk.CTkLabel(
            frame, text="", font=ctk.CTkFont(size=14)
        )

        self._update_buttons()
        self._refresh()
        self._update_masterlist_on_startup()

    # --- Data loading ---

    def _refresh(self):
        if not self._context:
            return
        self._context.status_bar.set_task("Loading load order...")
        install = self._context.game_installation
        plugins_path = install.plugins_txt
        try:
            lines = plugins_path.read_text(encoding="utf-8").splitlines()
            self._plugins = [
                line.lstrip("*").strip()
                for line in lines
                if line.strip() and not line.strip().startswith("#")
            ]
        except (FileNotFoundError, OSError):
            self._plugins = []
        self._groups = self._build_groups()
        self._working_groups = [g for g in self._groups]
        self._dirty_items.clear()
        self._original_positions.clear()
        self._populate_tree()
        self._update_buttons()
        self._context.status_bar.clear_task()

    def _build_groups(self) -> list[_CreationGroup]:
        """Group plugin files by creation from the catalog.

        Plugins belonging to the same creation are merged into one group.
        The group's position is determined by the earliest file in the
        load order. Ungrouped plugins become single-file groups.
        """
        from starfield_tool.parsers import parse_content_catalog

        if not self._context:
            return [_CreationGroup(key=p, display_name=p, files=[p])
                    for p in self._plugins]

        catalog = parse_content_catalog(
            self._context.game_installation.content_catalog
        )

        # Map each plugin filename to its catalog entry
        file_to_entry: dict[str, object] = {}
        for entry in catalog:
            for filename in entry.files:
                file_to_entry[filename] = entry

        # Walk the load order, grouping consecutive or scattered files
        seen_entries: set[str] = set()  # content_id of entries already grouped
        groups: list[_CreationGroup] = []

        for plugin in self._plugins:
            entry = file_to_entry.get(plugin)
            if entry and entry.content_id not in seen_entries:
                seen_entries.add(entry.content_id)
                # Collect all files for this entry that are in the plugin list
                entry_files = [f for f in entry.files if f in set(self._plugins)]
                groups.append(_CreationGroup(
                    key=entry_files[0] if entry_files else plugin,
                    display_name=entry.title,
                    files=entry_files,
                    content_id=entry.content_id,
                ))
            elif entry is None:
                # Plugin not in catalog — standalone
                groups.append(_CreationGroup(
                    key=plugin, display_name=plugin, files=[plugin],
                ))
            # else: file belongs to an entry already grouped, skip

        return groups

    def _populate_tree(self):
        if not self._tree:
            return
        for item in self._tree.get_children():
            self._tree.delete(item)
        if not self._working_groups:
            self._empty_label.configure(text="No plugins found in Plugins.txt")
            self._empty_label.pack(pady=20)
            return
        self._empty_label.pack_forget()
        for i, group in enumerate(self._working_groups):
            is_dirty = group.key in self._dirty_items
            from_col = ""
            if is_dirty and group.key in self._original_positions:
                from_col = str(self._original_positions[group.key] + 1)
            tags = ("dirty",) if is_dirty else ()
            self._tree.insert(
                "", "end",
                values=(i + 1, from_col, group.display_name, group.plugin_label),
                tags=tags,
            )

    # --- Drag and drop ---

    def _on_drag_start(self, event):
        item = self._tree.identify_row(event.y)
        if item:
            self._drag_item = item

    def _on_drag_motion(self, event):
        if not self._drag_item:
            return
        target = self._tree.identify_row(event.y)
        if target and target != self._drag_item:
            src_idx = self._tree.index(self._drag_item)
            dst_idx = self._tree.index(target)
            group = self._working_groups[src_idx]
            # Record original position on first move
            if group.key not in self._original_positions:
                self._original_positions[group.key] = src_idx
            self._working_groups.pop(src_idx)
            self._working_groups.insert(dst_idx, group)
            # Check if group is back at its original saved position
            saved_idx = next(
                (i for i, g in enumerate(self._groups) if g.key == group.key), -1
            )
            if dst_idx == saved_idx:
                self._dirty_items.discard(group.key)
                self._original_positions.pop(group.key, None)
            else:
                self._dirty_items.add(group.key)
            self._populate_tree()
            # Re-identify the dragged item
            children = self._tree.get_children()
            if dst_idx < len(children):
                self._drag_item = children[dst_idx]
            self._update_buttons()

    def _on_drag_end(self, _event):
        self._drag_item = None

    # --- Apply / Discard ---

    def _is_starfield_running(self) -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Starfield.exe", "/NH"],
                capture_output=True, text=True, timeout=5,
            )
            return "Starfield.exe" in result.stdout
        except (subprocess.SubprocessError, OSError):
            return False

    def _apply(self):
        if not self._context or not self._dirty_items:
            return
        if self._is_starfield_running():
            messagebox.showwarning(
                "Starfield Running",
                "Close Starfield before applying load order changes.",
            )
            return
        plugins_path = self._context.game_installation.plugins_txt
        try:
            # Preserve the * prefix for active plugins
            original_lines = {}
            try:
                for line in plugins_path.read_text(encoding="utf-8").splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        name = stripped.lstrip("*").strip()
                        original_lines[name] = stripped
            except (FileNotFoundError, OSError):
                pass

            lines = []
            for group in self._working_groups:
                for filename in group.files:
                    if filename in original_lines:
                        lines.append(original_lines[filename])
                    else:
                        lines.append(f"*{filename}")
            plugins_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._plugins = [f for g in self._working_groups for f in g.files]
            self._groups = list(self._working_groups)
            self._dirty_items.clear()
            self._original_positions.clear()
            self._populate_tree()
            self._update_buttons()
            self._status_label.configure(text="Order saved", text_color="green")
            self._tree.after(2000, lambda: self._status_label.configure(text=""))
        except OSError as e:
            messagebox.showerror("Write Error", f"Cannot write Plugins.txt: {e}")

    def _discard(self):
        self._working_groups = list(self._groups)
        self._dirty_items.clear()
        self._original_positions.clear()
        self._populate_tree()
        self._update_buttons()

    def _update_buttons(self):
        has_dirty = bool(self._dirty_items)
        if self._apply_btn:
            self._apply_btn.configure(
                state="normal" if has_dirty else "disabled"
            )
        if self._discard_btn:
            self._discard_btn.configure(
                state="normal" if has_dirty else "disabled"
            )

    # --- Auto Sort ---

    def _auto_sort(self):
        if not self._context or not self._working_groups:
            return
        self._context.status_bar.set_task("Sorting...")

        def _run():
            from load_order_sorter import sort_creations, SortItem
            from starfield_tool.creations import get_cached_info, _make_client
            from bethesda_creations import ContentQuery

            # Try cache first; if empty, fetch from API
            cached = get_cached_info(self._context.app_start_time)
            if not cached:
                self._context.status_bar.set_task(
                    "Fetching creation info for sorting..."
                )
                client = _make_client(
                    self._context.status_bar,
                    self._context.app_start_time,
                )
                queries = [
                    ContentQuery(
                        content_id=g.content_id or g.key,
                        display_name=g.display_name,
                    )
                    for g in self._working_groups
                    if g.content_id
                ]
                try:
                    cached = client.fetch_info(queries)
                except Exception:
                    pass  # proceed with what we have
                self._context.status_bar.set_task("Sorting...")

            items = []
            for i, group in enumerate(self._working_groups):
                info = cached.get(group.content_id) if group.content_id else None
                categories = info.categories if info else group.categories
                author = info.author if info else ""
                items.append(SortItem(
                    plugin_name=group.key,
                    content_id=group.content_id or group.key,
                    display_name=group.display_name,
                    categories=categories,
                    author=author or "",
                    original_index=i,
                ))

            active = ["category"]
            masterlist_path = self._get_masterlist_path()
            loot_available = masterlist_path is not None and masterlist_path.exists()
            if loot_available:
                active.append("loot")

            result = sort_creations(items, sorters=active,
                                    masterlist_path=masterlist_path)

            self._tree.after(
                0, lambda: self._on_sort_complete(result, loot_available)
            )

        threading.Thread(target=_run, daemon=True).start()

    def _get_masterlist_path(self) -> Path | None:
        """Return the LOOT masterlist path, checking cache then bundled."""
        from starfield_tool.config import _config_path
        from load_order_sorter.loot_masterlist import get_masterlist
        data_dir = _config_path().parent
        bundled = self._get_bundled_masterlist_path()
        return get_masterlist(data_dir, bundled)

    def _get_bundled_masterlist_path(self) -> Path | None:
        """Find the bundled masterlist shipped with the EXE."""
        import sys
        # PyInstaller extracts --add-data to sys._MEIPASS/data/
        if hasattr(sys, "_MEIPASS"):
            p = Path(sys._MEIPASS) / "data" / "loot_masterlist.yaml"
            if p.exists():
                return p
        # Dev mode: check build directory
        p = Path(__file__).resolve().parents[3] / "build" / "loot_masterlist.yaml"
        if p.exists():
            return p
        return None

    def _update_masterlist_on_startup(self):
        """Try to fetch a fresh masterlist in the background."""
        def _run():
            from starfield_tool.config import _config_path
            from load_order_sorter.loot_masterlist import update_masterlist
            data_dir = _config_path().parent
            update_masterlist(data_dir)
        threading.Thread(target=_run, daemon=True).start()

    def _on_sort_complete(self, result, loot_available=True):
        self._context.status_bar.clear_task()

        if not loot_available:
            messagebox.showwarning(
                "LOOT Masterlist Unavailable",
                "The LOOT masterlist could not be found or downloaded.\n\n"
                "Sorting is based on categories only, which may be less "
                "accurate. The masterlist will be fetched automatically "
                "on next startup if an internet connection is available.",
            )

        if result.unchanged:
            self._status_label.configure(
                text="Already in optimal order", text_color="green"
            )
            self._tree.after(2000, lambda: self._status_label.configure(text=""))
            return

        self._show_diff(result)

    def _show_diff(self, result):
        from starfield_tool.tools.load_order_diff import DiffDialog

        current_keys = [g.key for g in self._working_groups]
        dialog = DiffDialog(
            self._tree.winfo_toplevel(),
            current_keys,
            result.items,
        )
        self._tree.winfo_toplevel().wait_window(dialog)

        if dialog.result is not None:
            # Reorder working_groups to match the accepted key order
            key_to_group = {g.key: g for g in self._working_groups}
            new_groups = [key_to_group[k] for k in dialog.result if k in key_to_group]
            for i, group in enumerate(new_groups):
                saved_idx = next(
                    (j for j, g in enumerate(self._groups) if g.key == group.key), -1
                )
                if saved_idx != i:
                    self._dirty_items.add(group.key)
                    if group.key not in self._original_positions:
                        self._original_positions[group.key] = saved_idx
            self._working_groups = new_groups
            self._populate_tree()
            self._update_buttons()

    # --- Snapshots ---

    def _save_snapshot(self):
        if not self._working_groups:
            return
        path = filedialog.asksaveasfilename(
            title="Save Load Order Snapshot",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        from load_order_sorter import save_snapshot, SnapshotEntry
        from starfield_tool import __version__
        entries = [
            SnapshotEntry(
                content_id=g.content_id or g.key,
                display_name=g.display_name,
                files=g.files,
            )
            for g in self._working_groups
        ]
        save_snapshot(
            name=Path(path).stem,
            entries=entries,
            path=Path(path),
            tool_version=__version__ or "dev",
        )
        self._status_label.configure(text="Snapshot saved", text_color="green")
        self._tree.after(2000, lambda: self._status_label.configure(text=""))

    def _load_snapshot(self):
        path = filedialog.askopenfilename(
            title="Load Snapshot",
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return
        from load_order_sorter import load_snapshot
        try:
            snapshot = load_snapshot(Path(path))
        except ValueError as e:
            messagebox.showerror("Invalid Snapshot", str(e))
            return

        # Map snapshot entries to current groups by content_id
        id_to_group = {}
        for g in self._working_groups:
            cid = g.content_id or g.key
            id_to_group[cid] = g
            # Also map by key for legacy snapshots
            id_to_group[g.key] = g

        snapshot_id_set = {e.content_id for e in snapshot.entries}

        skipped = [e for e in snapshot.entries if e.content_id not in id_to_group]
        appended = [g for g in self._working_groups
                    if (g.content_id or g.key) not in snapshot_id_set]

        proposed_keys = []
        for entry in snapshot.entries:
            group = id_to_group.get(entry.content_id)
            if group:
                proposed_keys.append(group.key)
        for g in appended:
            proposed_keys.append(g.key)

        if skipped or appended:
            parts = []
            if skipped:
                names = ", ".join(e.display_name or e.content_id for e in skipped)
                parts.append(f"{len(skipped)} creation(s) from snapshot not installed: {names}")
            if appended:
                parts.append(f"{len(appended)} new creation(s) appended at end")
            messagebox.showinfo("Snapshot Import", "\n".join(parts))

        # Show in diff view
        from load_order_sorter.models import SortedItem, SortResult, SortDecision
        current_keys_list = [g.key for g in self._working_groups]
        key_to_group = {g.key: g for g in self._working_groups}
        items = []
        for i, key in enumerate(proposed_keys):
            orig_idx = current_keys_list.index(key) if key in current_keys_list else i
            group = key_to_group.get(key)
            items.append(SortedItem(
                plugin_name=key,
                content_id=group.content_id if group else key,
                display_name=group.display_name if group else key,
                original_index=orig_idx,
                new_index=i,
                moved=orig_idx != i,
                decision=SortDecision(sorter_name="SNAP") if orig_idx != i else None,
            ))

        result = SortResult(items=items, unchanged=all(not si.moved for si in items))
        if result.unchanged:
            self._status_label.configure(text="Snapshot matches current order",
                                          text_color="green")
            self._tree.after(2000, lambda: self._status_label.configure(text=""))
            return

        self._show_diff(result)
