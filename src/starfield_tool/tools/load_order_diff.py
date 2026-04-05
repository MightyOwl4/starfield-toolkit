"""Diff view dialog for reviewing proposed load order changes."""
from tkinter import ttk

import customtkinter as ctk

from load_order_sorter.models import SortedItem


class DiffDialog(ctk.CTkToplevel):
    """Side-by-side diff view for proposed load order changes.

    Returns the accepted order via self.result (list of plugin names),
    or None if cancelled.
    """

    def __init__(
        self,
        parent,
        current: list[str],
        proposed: list[SortedItem],
    ):
        super().__init__(parent)
        self.title("Review Proposed Load Order")
        self.minsize(800, 400)

        from starfield_tool.dialogs import center_dialog
        center_dialog(self, 900, 600)
        # No transient/grab_set — those break Win+D recovery on Windows.
        # Show as a regular taskbar window so Alt+Tab always works.
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        from starfield_tool.app import _icon_path
        icon = _icon_path()
        if icon.exists():
            self.after(200, lambda: self.iconbitmap(str(icon)))

        self.result: list[str] | None = None
        self._current = current
        self._proposed = proposed
        self._accepted: dict[str, bool] = {}  # plugin_name → accepted?

        # Track which items moved
        for item in proposed:
            if item.moved:
                self._accepted[item.plugin_name] = False  # default: not accepted

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _build_ui(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = "#2b2b2b" if is_dark else "#ffffff"
        fg = "#dcdcdc" if is_dark else "#000000"
        moved_bg = "#3d4f2f" if is_dark else "#d4edda"
        header_bg = "#1f1f1f" if is_dark else "#e0e0e0"

        # Top button bar
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=4)

        _btn_color = "#314c79"
        _btn_hover = "#3d5f99"
        _btn_kw = dict(height=26, corner_radius=4, font=ctk.CTkFont(size=12),
                       fg_color=_btn_color, hover_color=_btn_hover)

        ctk.CTkButton(
            btn_frame, text="Apply All", width=80,
            command=self._apply_all, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Done", width=60,
            command=self._done, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_frame, text="Cancel", width=60,
            command=self._cancel, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        self._status_label = ctk.CTkLabel(btn_frame, text="", font=ctk.CTkFont(size=11))
        self._status_label.pack(side="left", padx=8)
        self._update_status()

        # Main split pane
        pane = ctk.CTkFrame(self, fg_color="transparent")
        pane.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Style for treeviews
        style = ttk.Style()
        style.configure("Diff.Treeview", background=bg, foreground=fg,
                        fieldbackground=bg, rowheight=24, borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Diff.Treeview.Heading", background=header_bg,
                        foreground=fg if is_dark else "#333", borderwidth=1,
                        relief="flat", font=("Segoe UI", 9, "bold"))

        # Left: current order
        left_frame = ctk.CTkFrame(pane, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 4))
        ctk.CTkLabel(left_frame, text="Current Order",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self._left_tree = self._make_tree(left_frame)

        # Right: proposed order
        right_frame = ctk.CTkFrame(pane, fg_color="transparent")
        right_frame.pack(side="right", fill="both", expand=True, padx=(4, 0))
        ctk.CTkLabel(right_frame, text="Proposed Order",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self._right_tree = self._make_tree(right_frame)

        # Tag for moved items
        self._left_tree.tag_configure("moved", background=moved_bg)
        self._right_tree.tag_configure("moved", background=moved_bg)
        self._right_tree.tag_configure("accepted",
                                        background="#314c79" if is_dark else "#b8daff",
                                        foreground="#ffffff" if is_dark else "#000000")

        self._populate()

    def _make_tree(self, parent) -> ttk.Treeview:
        columns = ("#", "Name", "Info")
        tree = ttk.Treeview(parent, columns=columns, show="headings",
                            selectmode="none", style="Diff.Treeview")
        tree.heading("#", text="#", anchor="center")
        tree.heading("Name", text="Name", anchor="w")
        tree.heading("Info", text="Info", anchor="w")
        tree.column("#", width=35, anchor="center", stretch=False)
        tree.column("Name", width=250, anchor="w")
        tree.column("Info", width=150, anchor="w", stretch=False)
        tree.pack(fill="both", expand=True, pady=(2, 0))
        return tree

    def _populate(self):
        # Build key → display name lookup from proposed items
        display_names = {si.plugin_name: si.display_name for si in self._proposed}

        # Left: current order
        for item in self._left_tree.get_children():
            self._left_tree.delete(item)
        for i, name in enumerate(self._current):
            proposed_item = self._find_proposed(name)
            tags = ("moved",) if proposed_item and proposed_item.moved else ()
            label = display_names.get(name, name)
            self._left_tree.insert("", "end", values=(i + 1, label, ""), tags=tags)

        # Right: proposed order
        self._populate_right()

    def _populate_right(self):
        for item in self._right_tree.get_children():
            self._right_tree.delete(item)

        for si in self._proposed:
            info_parts = []
            if si.moved:
                # Show original position (where it was on the left side)
                info_parts.append(f"was #{si.original_index + 1}")
                if si.decision and si.decision.sorter_name:
                    info_parts.append(si.decision.sorter_name)
                if (si.decision and si.decision.load_after_sorters
                        and "TES4" in si.decision.load_after_sorters.values()):
                    info_parts.append("TES4")
                if self._accepted.get(si.plugin_name):
                    info_parts.append("\u2713")

            info = " ".join(info_parts)
            accepted = self._accepted.get(si.plugin_name, False)
            if si.moved and accepted:
                tags = ("accepted",)
            elif si.moved:
                tags = ("moved",)
            else:
                tags = ()

            self._right_tree.insert(
                "", "end",
                values=(si.new_index + 1, si.display_name, info),
                tags=tags,
            )

        # Bind click for per-item toggle
        self._right_tree.bind("<ButtonRelease-1>", self._on_right_click)

    def _on_right_click(self, event):
        """Toggle accept/ignore for clicked item."""
        item_id = self._right_tree.identify_row(event.y)
        if not item_id:
            return
        idx = self._right_tree.index(item_id)
        if idx >= len(self._proposed):
            return
        si = self._proposed[idx]
        if not si.moved:
            return
        # Toggle
        current = self._accepted.get(si.plugin_name, False)
        self._accepted[si.plugin_name] = not current
        self._populate_right()
        self._update_status()

    def _find_proposed(self, plugin_name: str) -> SortedItem | None:
        for si in self._proposed:
            if si.plugin_name == plugin_name:
                return si
        return None

    def _apply_all(self):
        for name in self._accepted:
            self._accepted[name] = True
        self._populate_right()
        self._update_status()

    def _update_status(self):
        total = len(self._accepted)
        accepted = sum(1 for v in self._accepted.values() if v)
        if total == 0:
            self._status_label.configure(text="No changes proposed")
        else:
            self._status_label.configure(
                text=f"{accepted}/{total} moves accepted"
            )

    def _done(self):
        """Build final order: apply accepted moves, keep ignored in place."""
        # Start with current order
        result = list(self._current)

        # For accepted moves, rearrange to match proposed positions
        accepted_names = {n for n, v in self._accepted.items() if v}
        if accepted_names:
            if len(accepted_names) == len(self._accepted):
                result = [si.plugin_name for si in self._proposed]
            else:
                result = self._merge_partial(accepted_names)

        self.result = result
        self.destroy()

    def _merge_partial(self, accepted_names: set[str]) -> list[str]:
        """Merge partial accept: accepted items at proposed positions,
        ignored items stay at current positions.

        Build the result by walking the proposed order.  For each slot we
        pick either the next accepted item (if the proposed list says an
        accepted item goes here) or the next non-accepted item from the
        current order (preserving their relative sequence).
        """
        # Queue of non-accepted items in their current-order sequence
        fixed_queue: list[str] = []
        for name in self._current:
            proposed = self._find_proposed(name)
            if proposed and proposed.moved and name in accepted_names:
                continue  # placed by proposed order below
            fixed_queue.append(name)

        # Walk the proposed order to build the result
        result: list[str] = []
        fixed_iter = iter(fixed_queue)
        for si in self._proposed:
            if si.plugin_name in accepted_names and si.moved:
                result.append(si.plugin_name)
            else:
                # Pull the next item from the fixed queue
                item = next(fixed_iter, None)
                if item is not None:
                    result.append(item)

        # Append any remaining fixed items (shouldn't happen in normal
        # operation, but guards against length mismatches)
        for item in fixed_iter:
            result.append(item)

        return result

    def _cancel(self):
        self.result = None
        self.destroy()
