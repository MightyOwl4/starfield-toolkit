"""Diff view dialog for reviewing proposed load order changes.

Visualises the minimal set of moves between the saved and proposed orderings
(via difflib.SequenceMatcher).  Draws colored Bezier curves on a canvas
between the two treeviews and shows a clickable hint icon on each moved row
whose click opens a per-move hints dialog listing every constraint that
influenced the move.
"""
import tkinter as tk
from difflib import SequenceMatcher
from tkinter import ttk

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from load_order_sorter.models import SortedItem

# Collapse equal runs longer than this into a summary row
_COLLAPSE_THRESHOLD = 3

# Palette cycled per move.  Assigned by proposed-order position so the same
# sort reliably produces the same color assignment.
_MOVE_COLORS = [
    "#4a9eff", "#48c774", "#f39c12",
    "#e55353", "#9c6ad6", "#1abc9c",
]

# Middle canvas width in pixels.  Wide enough for Bezier curves to breathe
# and for the endpoint dots to sit clear of the tree edges.  Wider values
# help readability when many connectors cross each other.
_CANVAS_WIDTH = 160

# Endpoint dot radius.
_DOT_RADIUS = 4


def _hex_with_alpha(hex_color: str, alpha: int) -> tuple[int, int, int, int]:
    """Convert #RRGGBB to an RGBA tuple for PIL with the given alpha (0-255)."""
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16)
    g = int(h[2:4], 16)
    b = int(h[4:6], 16)
    return (r, g, b, alpha)


def truly_moved_keys(saved: list[str], current: list[str]) -> set[str]:
    """Return the keys that truly moved between two orderings.

    Uses SequenceMatcher to find the longest common subsequence; only
    items outside the LCS are considered moved.  This avoids flagging
    items that merely shifted index because a neighbour moved.
    """
    moved: set[str] = set()
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, saved, current).get_opcodes():
        if tag != "equal":
            for k in range(i1, i2):
                moved.add(saved[k])
            for k in range(j1, j2):
                moved.add(current[k])
    return moved


class DiffDialog(ctk.CTkToplevel):
    """Side-by-side diff view for proposed load order changes.

    Uses difflib.SequenceMatcher to find the minimal set of actual moves,
    so only truly relocated items are highlighted (not everything that
    shifted index because of a neighbour moving).

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
        # On QHD-class monitors (>=2560 px wide) open wider by default so
        # connectors have room to breathe.  Fall back to the compact default
        # on narrower screens.
        try:
            screen_w = self.winfo_screenwidth()
        except tk.TclError:
            screen_w = 0
        default_w = 1500 if screen_w >= 2560 else 900
        default_h = 800 if screen_w >= 2560 else 600
        center_dialog(self, default_w, default_h)
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
        self._collapsed = True  # start collapsed

        # Build lookup from plugin_name → SortedItem for info display
        self._proposed_map: dict[str, SortedItem] = {
            si.plugin_name: si for si in proposed
        }

        # Compute the true diff using SequenceMatcher
        proposed_keys = [si.plugin_name for si in proposed]
        self._opcodes = SequenceMatcher(
            None, current, proposed_keys,
        ).get_opcodes()

        # Identify truly moved items via LCS
        self._moved_names = truly_moved_keys(current, proposed_keys)

        # Assign a color per moved item, cycled from _MOVE_COLORS in
        # proposed-order.  Deterministic and stable across repeated sorts.
        self._move_colors: dict[str, str] = {}
        color_idx = 0
        for key in proposed_keys:
            if key in self._moved_names:
                self._move_colors[key] = _MOVE_COLORS[color_idx % len(_MOVE_COLORS)]
                color_idx += 1

        # Populated by _populate(): plugin_name → tree iid per side
        self._left_iid_by_name: dict[str, str] = {}
        self._right_iid_by_name: dict[str, str] = {}
        # Reverse: iid → plugin_name, for hover detection.
        self._left_name_by_iid: dict[str, str] = {}
        self._right_name_by_iid: dict[str, str] = {}

        # Hover state for cross-pane highlighting.
        self._hovered_name: str | None = None

        # Accept/reject tracking — only for truly moved items
        self._accepted: dict[str, bool] = {
            name: False for name in self._moved_names
        }

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        # Dark theme only — diff dialog is visually tuned for dark mode;
        # supporting light theme here isn't a realistic test/maintenance
        # investment for the expected audience.
        bg = "#2b2b2b"
        fg = "#dcdcdc"
        self._bg = bg
        self._moved_bg = "#3d4f2f"
        self._sep_bg = "#383838"
        self._sep_fg = "#888888"
        header_bg = "#1f1f1f"

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

        # "Collapse unchanged" toggle — right-aligned, switch style
        _toggle_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        _toggle_frame.pack(side="right", padx=(0, 4))
        ctk.CTkLabel(
            _toggle_frame, text="Collapse unchanged",
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 6))
        self._collapse_switch = ctk.CTkSwitch(
            _toggle_frame, text="", width=40,
            command=self._toggle_collapse,
        )
        self._collapse_switch.pack(side="left")
        if self._collapsed:
            self._collapse_switch.select()

        self._status_label = ctk.CTkLabel(btn_frame, text="", font=ctk.CTkFont(size=11))
        self._status_label.pack(side="left", padx=8)
        self._update_status()

        # Main split pane — 3 columns: left tree, connector canvas, right tree
        pane = ctk.CTkFrame(self, fg_color="transparent")
        pane.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        # Weights favor the right pane (weight=3) over the left (weight=2)
        # because the right tree carries both Name and Info, while the left
        # tree only uses Name in practice.  Middle canvas is fixed width.
        pane.grid_columnconfigure(0, weight=2)
        pane.grid_columnconfigure(1, weight=0, minsize=_CANVAS_WIDTH)
        pane.grid_columnconfigure(2, weight=3)
        pane.grid_rowconfigure(0, weight=1)

        # Style for treeviews — font/rowheight driven by user setting
        from starfield_tool.grid_style import (
            grid_font, grid_heading_font, grid_rowheight,
        )
        style = ttk.Style()
        style.configure("Diff.Treeview", background=bg, foreground=fg,
                        fieldbackground=bg, rowheight=grid_rowheight(),
                        borderwidth=0,
                        font=grid_font())
        style.configure("Diff.Treeview.Heading", background=header_bg,
                        foreground=fg, borderwidth=1,
                        relief="flat", font=grid_heading_font())

        # Left: current order — Info column is always empty, shrink it so
        # Name gets more horizontal space.
        left_frame = ctk.CTkFrame(pane, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        ctk.CTkLabel(left_frame, text="Current Order",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self._left_tree = self._make_tree(left_frame, info_width=10)

        # Middle: connector canvas (aligns vertically with tree content).
        # Use a holder frame so the canvas starts below the left/right labels
        # (one label's worth of vertical space) — matches tree row positions.
        canvas_holder = ctk.CTkFrame(pane, fg_color="transparent")
        canvas_holder.grid(row=0, column=1, sticky="ns")
        # Spacer matching the bold header label height
        ctk.CTkLabel(canvas_holder, text=" ",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self._connector_canvas = tk.Canvas(
            canvas_holder, width=_CANVAS_WIDTH,
            highlightthickness=0, bd=0, bg=bg,
        )
        self._connector_canvas.pack(fill="y", expand=True, pady=(2, 0))

        # Right: proposed order — tree + shared scrollbar in a grid container
        right_frame = ctk.CTkFrame(pane, fg_color="transparent")
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        ctk.CTkLabel(right_frame, text="Proposed Order",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")

        right_tree_container = ctk.CTkFrame(right_frame, fg_color="transparent")
        right_tree_container.pack(fill="both", expand=True, pady=(2, 0))
        right_tree_container.grid_rowconfigure(0, weight=1)
        right_tree_container.grid_columnconfigure(0, weight=1)

        self._right_tree = self._make_tree(right_tree_container, pack=False)
        self._right_tree.grid(row=0, column=0, sticky="nsew")

        self._shared_scrollbar = ttk.Scrollbar(
            right_tree_container, orient="vertical",
            command=self._shared_yview,
        )
        self._shared_scrollbar.grid(row=0, column=1, sticky="ns")

        # Tags for visual styling
        for tree in (self._left_tree, self._right_tree):
            tree.tag_configure("moved", background=self._moved_bg)
            tree.tag_configure("separator",
                               background=self._sep_bg,
                               foreground=self._sep_fg)
        self._right_tree.tag_configure(
            "accepted",
            background="#314c79",
            foreground="#ffffff",
        )

        # Hover tag: bold font, colors untouched.  Full inversion was too
        # heavy-handed and masked the accept/reject tint.
        for tree in (self._left_tree, self._right_tree):
            tree.tag_configure("hovered", font=grid_font(bold=True))

        self._left_tree.configure(yscrollcommand=self._on_tree_yscroll)
        self._right_tree.configure(yscrollcommand=self._on_tree_yscroll)

        # Wheel events on either tree scroll both (Windows: MouseWheel,
        # Linux: Button-4/5).
        for tree in (self._left_tree, self._right_tree):
            tree.bind("<MouseWheel>", self._on_mousewheel)
            tree.bind("<Button-4>", self._on_mousewheel)
            tree.bind("<Button-5>", self._on_mousewheel)

        # Hover: highlight the moved pair + its connector on both sides.
        self._left_tree.bind(
            "<Motion>", lambda e: self._on_tree_motion(e, side="left"))
        self._right_tree.bind(
            "<Motion>", lambda e: self._on_tree_motion(e, side="right"))
        self._left_tree.bind("<Leave>", lambda _e: self._clear_hover())
        self._right_tree.bind("<Leave>", lambda _e: self._clear_hover())

        # Redraw connectors on canvas resize and tree layout changes.
        self._connector_canvas.bind("<Configure>",
                                    lambda _e: self._redraw_connectors())

        self._populate()

    def _make_tree(
        self, parent, pack: bool = True, info_width: int = 150,
    ) -> ttk.Treeview:
        columns = ("#", "Name", "Info")
        tree = ttk.Treeview(parent, columns=columns, show="headings",
                            selectmode="none", style="Diff.Treeview")
        tree.heading("#", text="#", anchor="center")
        tree.heading("Name", text="Name", anchor="w")
        tree.heading("Info", text="Info", anchor="w")
        tree.column("#", width=35, anchor="center", stretch=False)
        tree.column("Name", width=250, anchor="w", stretch=True)
        tree.column("Info", width=info_width, anchor="w", stretch=False)
        if pack:
            tree.pack(fill="both", expand=True, pady=(2, 0))
        return tree

    # ---------------------------------------------------- shared scrolling

    def _shared_yview(self, *args):
        """Scrollbar command: move both trees together."""
        self._left_tree.yview(*args)
        self._right_tree.yview(*args)
        self._redraw_connectors()

    def _on_tree_yscroll(self, first: str, last: str):
        """yscrollcommand callback: update the shared scrollbar and keep
        both trees' vertical offsets in sync."""
        self._shared_scrollbar.set(first, last)
        # Mirror the first tree's position to the other without infinite
        # feedback — Tk's yscrollcommand only fires on actual change.
        try:
            lf, _ = self._left_tree.yview()
            rf, _ = self._right_tree.yview()
            if abs(lf - rf) > 1e-4:
                # Someone scrolled; align the other to match `first`.
                target = float(first)
                self._left_tree.yview_moveto(target)
                self._right_tree.yview_moveto(target)
        except (ValueError, tk.TclError):
            pass
        self._redraw_connectors()

    def _on_mousewheel(self, event):
        """Wheel events on either tree scroll both trees together."""
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            # Windows MouseWheel: event.delta is multiples of 120
            delta = -1 if event.delta > 0 else 1
        self._left_tree.yview_scroll(delta, "units")
        self._right_tree.yview_scroll(delta, "units")
        self._redraw_connectors()
        return "break"

    # -------------------------------------------------------- hover highlight

    def _on_tree_motion(self, event, side: str):
        """Hover handler: identify the moved row under cursor and
        cross-highlight its pair + connector."""
        tree = self._left_tree if side == "left" else self._right_tree
        reverse = (self._left_name_by_iid if side == "left"
                   else self._right_name_by_iid)
        iid = tree.identify_row(event.y)
        new_name = reverse.get(iid) if iid else None
        if new_name == self._hovered_name:
            return  # no change; avoid redraw spam
        self._set_hover(new_name)

    def _clear_hover(self):
        if self._hovered_name is None:
            return
        self._set_hover(None)

    def _set_hover(self, name: str | None):
        """Apply/remove the hovered tag on both trees' rows and redraw."""
        prev = self._hovered_name
        self._hovered_name = name

        def _update_tags(tree, iid, add: bool):
            try:
                tags = list(tree.item(iid, "tags") or ())
            except tk.TclError:
                return
            if add and "hovered" not in tags:
                tags.append("hovered")
            elif not add and "hovered" in tags:
                tags.remove("hovered")
            tree.item(iid, tags=tuple(tags))

        if prev is not None:
            li = self._left_iid_by_name.get(prev)
            ri = self._right_iid_by_name.get(prev)
            if li:
                _update_tags(self._left_tree, li, add=False)
            if ri:
                _update_tags(self._right_tree, ri, add=False)

        if name is not None:
            li = self._left_iid_by_name.get(name)
            ri = self._right_iid_by_name.get(name)
            if li:
                _update_tags(self._left_tree, li, add=True)
            if ri:
                _update_tags(self._right_tree, ri, add=True)

        self._redraw_connectors()

    # --------------------------------------------------- connector drawing

    def _rebuild_iid_maps(self):
        """Map plugin_name → tree iid for both trees, for moved items only.

        Walks tree children in order and matches them against the opcodes
        layout — because the trees use auto-generated iids, we figure out
        which child corresponds to which plugin_name by replaying the same
        opcode walk that _populate() used.
        """
        self._left_iid_by_name.clear()
        self._right_iid_by_name.clear()
        self._left_name_by_iid.clear()
        self._right_name_by_iid.clear()

        left_iids = list(self._left_tree.get_children())
        right_iids = list(self._right_tree.get_children())

        proposed_keys = [si.plugin_name for si in self._proposed]
        li = 0
        ri = 0
        for tag, i1, i2, j1, j2 in self._opcodes:
            if tag == "equal":
                n = i2 - i1
                if not self._collapsed or n <= _COLLAPSE_THRESHOLD:
                    rows = n
                else:
                    rows = 3  # first, separator, last
                # Equal-run rows are not moved items; skip them.
                li += rows
                ri += rows
            elif tag in ("replace", "delete"):
                for k in range(i1, i2):
                    name = self._current[k]
                    if name in self._moved_names and li < len(left_iids):
                        iid = left_iids[li]
                        self._left_iid_by_name[name] = iid
                        self._left_name_by_iid[iid] = name
                    li += 1
                if tag == "replace":
                    for k in range(j1, j2):
                        name = proposed_keys[k]
                        if name in self._moved_names and ri < len(right_iids):
                            iid = right_iids[ri]
                            self._right_iid_by_name[name] = iid
                            self._right_name_by_iid[iid] = name
                        ri += 1
            elif tag == "insert":
                for k in range(j1, j2):
                    name = proposed_keys[k]
                    if name in self._moved_names and ri < len(right_iids):
                        iid = right_iids[ri]
                        self._right_iid_by_name[name] = iid
                        self._right_name_by_iid[iid] = name
                    ri += 1

    def _row_y_or_clamped(
        self, tree: ttk.Treeview, iid: str, canvas_y_abs: int, canvas_h: int,
    ) -> tuple[int, bool]:
        """Return (y_on_canvas, is_visible) for a row.

        If the row is visible, y is the center Y of its bbox mapped onto
        canvas coordinates.  If scrolled above the viewport, y is clamped
        to -20 (just above the canvas).  If below, clamped to canvas_h + 20.
        Used so connectors still draw when one endpoint is off-screen.
        """
        bbox = tree.bbox(iid)
        if bbox:
            y = (tree.winfo_rooty() + bbox[1] + bbox[3] // 2 - canvas_y_abs)
            return y, True

        # Off-screen: determine above or below via the row's index vs. the
        # visible range. ttk.Treeview.yview() returns (top_frac, bottom_frac)
        # over the total row count.
        try:
            children = tree.get_children()
            total = len(children)
            if total == 0:
                return -20, False
            row_idx = children.index(iid)
            top_frac, _ = tree.yview()
            top_row = top_frac * total
            if row_idx < top_row:
                return -20, False
            return canvas_h + 20, False
        except (ValueError, tk.TclError):
            return -20, False

    def _redraw_connectors(self):
        """Draw antialiased Bezier curves + endpoint dots using PIL.

        Tk's native Canvas lines don't antialias.  We render the whole
        connector graphic into an off-screen PIL image at 2x supersampling,
        downscale with LANCZOS, then blit it as a single Canvas image for
        smooth edges.

        When one endpoint is scrolled out of view, the curve is still drawn
        anchored to the visible endpoint with its other end clamped just
        outside the canvas — so users keep the visual reference to where
        the item is headed.
        """
        canvas = self._connector_canvas
        canvas.delete("connector")

        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()
        if canvas_w <= 1 or canvas_h <= 1:
            return  # not realized yet

        # Determine parent theme bg so the blit is invisible outside curves.
        bg = canvas.cget("bg")

        # Supersample factor for antialiasing via downscale.
        SS = 2
        img = Image.new("RGBA", (canvas_w * SS, canvas_h * SS), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        canvas_y_abs = canvas.winfo_rooty()
        r = _DOT_RADIUS
        drew_anything = False
        hovered = self._hovered_name
        has_hover = hovered is not None

        # Draw non-hovered first (dimmed when something else is hovered),
        # then the hovered one on top so it's always on top visually.
        names_sorted = sorted(
            self._moved_names, key=lambda n: (n == hovered, n),
        )
        for name in names_sorted:
            left_iid = self._left_iid_by_name.get(name)
            right_iid = self._right_iid_by_name.get(name)
            if not left_iid or not right_iid:
                continue

            ly, l_visible = self._row_y_or_clamped(
                self._left_tree, left_iid, canvas_y_abs, canvas_h)
            ry, r_visible = self._row_y_or_clamped(
                self._right_tree, right_iid, canvas_y_abs, canvas_h)

            # If BOTH endpoints are off-screen, skip — nothing meaningful
            # to draw (the curve would cross the canvas without anchoring
            # to any visible row).
            if not l_visible and not r_visible:
                continue

            base_color = self._move_colors.get(name, "#888888")
            if name == hovered:
                # Hovered: bright white for maximum contrast
                color = "#ffffff"
                line_width = 3 * SS
            elif has_hover:
                # Dim other connectors when something is hovered
                color = _hex_with_alpha(base_color, 90)
                line_width = 2 * SS
            else:
                color = base_color
                line_width = 2 * SS

            # Build a cubic Bezier polyline:
            # P0 = (2r, ly), P1 = (w/3, ly), P2 = (2w/3, ry), P3 = (w-2r, ry)
            p0 = (2 * r, ly)
            p1 = (canvas_w / 3, ly)
            p2 = (2 * canvas_w / 3, ry)
            p3 = (canvas_w - 2 * r, ry)

            steps = 40
            pts = []
            for i in range(steps + 1):
                t = i / steps
                mt = 1 - t
                x = (mt**3 * p0[0] + 3 * mt**2 * t * p1[0]
                     + 3 * mt * t**2 * p2[0] + t**3 * p3[0])
                y = (mt**3 * p0[1] + 3 * mt**2 * t * p1[1]
                     + 3 * mt * t**2 * p2[1] + t**3 * p3[1])
                pts.append((x * SS, y * SS))

            # Soft glow for the hovered connector — wider, low-alpha white
            # drawn first so the crisp line sits on top.
            if name == hovered:
                glow = _hex_with_alpha("#ffffff", 60)
                draw.line(pts, fill=glow, width=8 * SS, joint="curve")

            # Bezier line (antialiased after downscale)
            draw.line(pts, fill=color, width=line_width, joint="curve")

            # Endpoint dots — only on visible sides.  Hovered dots get a
            # subtle size bump and solid white fill to mirror the line.
            dot_r = r + 1 if name == hovered else r
            dot_fill = color
            if l_visible:
                lx0, ly0 = 0, (ly - dot_r) * SS
                lx1, ly1 = (2 * dot_r) * SS, (ly + dot_r) * SS
                draw.ellipse([lx0, ly0, lx1, ly1], fill=dot_fill)
            if r_visible:
                rx0, ry0 = (canvas_w - 2 * dot_r) * SS, (ry - dot_r) * SS
                rx1, ry1 = canvas_w * SS, (ry + dot_r) * SS
                draw.ellipse([rx0, ry0, rx1, ry1], fill=dot_fill)

            drew_anything = True

        if not drew_anything:
            return

        # Downscale to canvas size (LANCZOS for smooth edges)
        smoothed = img.resize((canvas_w, canvas_h), Image.LANCZOS)

        # Composite over the canvas background color so the PhotoImage
        # doesn't render transparent pixels as black on some platforms.
        try:
            bg_rgb = self.winfo_rgb(bg)
            bg_tuple = (bg_rgb[0] // 256, bg_rgb[1] // 256,
                        bg_rgb[2] // 256, 255)
        except tk.TclError:
            bg_tuple = (43, 43, 43, 255)
        background = Image.new("RGBA", smoothed.size, bg_tuple)
        background.paste(smoothed, (0, 0), smoothed)

        # Keep a reference so PhotoImage isn't garbage-collected.
        self._connector_photo = ImageTk.PhotoImage(background)
        canvas.create_image(
            0, 0, image=self._connector_photo,
            anchor="nw", tags="connector",
        )

    # ----------------------------------------------------------- populate

    def _populate(self):
        proposed_keys = [si.plugin_name for si in self._proposed]
        display = {si.plugin_name: si.display_name for si in self._proposed}

        for tree in (self._left_tree, self._right_tree):
            for item in tree.get_children():
                tree.delete(item)

        # Walk opcodes and populate both trees in sync
        for tag, i1, i2, j1, j2 in self._opcodes:
            if tag == "equal":
                self._insert_equal_run(
                    self._current[i1:i2], proposed_keys[j1:j2],
                    i1, j1, display,
                )
            elif tag == "replace":
                # Items removed from current and inserted into proposed
                self._insert_moved_left(self._current[i1:i2], i1, display)
                self._insert_moved_right(proposed_keys[j1:j2], j1)
            elif tag == "delete":
                self._insert_moved_left(self._current[i1:i2], i1, display)
            elif tag == "insert":
                self._insert_moved_right(proposed_keys[j1:j2], j1)

        # Bind click for per-item toggle on right tree
        self._right_tree.bind("<ButtonRelease-1>", self._on_right_click)

        # Rebuild name→iid maps for connector drawing
        self._rebuild_iid_maps()

        # Redraw connectors after geometry is realized
        self.after(10, self._redraw_connectors)

    def _insert_equal_run(
        self,
        left_names: list[str],
        right_names: list[str],
        left_start: int,
        right_start: int,
        display: dict[str, str],
    ):
        """Insert an unchanged run. Collapse if longer than threshold."""
        n = len(left_names)
        if not self._collapsed or n <= _COLLAPSE_THRESHOLD:
            # Show all rows
            for offset, (ln, rn) in enumerate(zip(left_names, right_names)):
                left_pos = left_start + offset + 1
                right_pos = right_start + offset + 1
                label_l = display.get(ln, ln)
                label_r = display.get(rn, rn)
                self._left_tree.insert(
                    "", "end", values=(left_pos, label_l, ""))
                self._right_tree.insert(
                    "", "end", values=(right_pos, label_r, ""))
        else:
            # Show first, separator, last
            first_l = display.get(left_names[0], left_names[0])
            first_r = display.get(right_names[0], right_names[0])
            self._left_tree.insert(
                "", "end",
                values=(left_start + 1, first_l, ""))
            self._right_tree.insert(
                "", "end",
                values=(right_start + 1, first_r, ""))

            hidden = n - 2
            self._left_tree.insert(
                "", "end",
                values=("", f"\u2014 {hidden} unchanged \u2014", ""),
                tags=("separator",))
            self._right_tree.insert(
                "", "end",
                values=("", f"\u2014 {hidden} unchanged \u2014", ""),
                tags=("separator",))

            last_l = display.get(left_names[-1], left_names[-1])
            last_r = display.get(right_names[-1], right_names[-1])
            self._left_tree.insert(
                "", "end",
                values=(left_start + n, last_l, ""))
            self._right_tree.insert(
                "", "end",
                values=(right_start + n, last_r, ""))

    def _insert_moved_left(
        self, names: list[str], start: int, display: dict[str, str],
    ):
        """Items that left their current position (delete side)."""
        for offset, name in enumerate(names):
            label = display.get(name, name)
            color_tag = f"mcolor_{name}"
            self._left_tree.tag_configure(
                color_tag, foreground=self._move_colors.get(name, ""),
            )
            self._left_tree.insert(
                "", "end",
                values=(start + offset + 1, label, ""),
                tags=("moved", color_tag),
            )

    def _insert_moved_right(self, names: list[str], start: int):
        """Items arriving at their proposed position (insert side)."""
        for offset, name in enumerate(names):
            si = self._proposed_map.get(name)
            label = si.display_name if si else name

            info_parts = ["\u24d8"]  # circled ⓘ — clickable for hints dialog
            if si:
                info_parts.append(f"was #{si.original_index + 1}")
                if si.decision and si.decision.sorter_name:
                    info_parts.append(si.decision.sorter_name)
                if (si.decision and si.decision.load_after_sorters
                        and any(s in si.decision.load_after_sorters.values()
                                for s in ("TES4", "RULE"))):
                    extra = set(si.decision.load_after_sorters.values()) - {
                        si.decision.sorter_name}
                    for s in sorted(extra):
                        info_parts.append(s)
            if self._accepted.get(name):
                info_parts.append("\u2713")

            info = " ".join(info_parts)
            accepted = self._accepted.get(name, False)
            color_tag = f"mcolor_{name}"
            self._right_tree.tag_configure(
                color_tag, foreground=self._move_colors.get(name, ""),
            )
            if accepted:
                tags = ("accepted", color_tag)
            else:
                tags = ("moved", color_tag)

            self._right_tree.insert(
                "", "end",
                values=(start + offset + 1, label, info),
                tags=tags,
            )

    # -------------------------------------------------------- interaction

    def _on_right_click(self, event):
        """Row body click toggles accept; Info column click opens hints."""
        item_id = self._right_tree.identify_row(event.y)
        if not item_id:
            return
        vals = self._right_tree.item(item_id, "values")
        if not vals or not vals[0]:
            return  # separator row
        row_idx = self._right_tree.index(item_id)
        name = self._right_row_to_name(row_idx)
        if name is None or name not in self._accepted:
            return

        # Info column (#3) → open hints dialog; other columns → toggle accept
        col = self._right_tree.identify_column(event.x)
        if col == "#3":
            self._show_hint_dialog(name)
            return

        self._accepted[name] = not self._accepted[name]
        self._populate()
        self._update_status()

    def _right_row_to_name(self, row_idx: int) -> str | None:
        """Map a visual row index in the right tree to a plugin name."""
        proposed_keys = [si.plugin_name for si in self._proposed]
        idx = 0
        for tag, _i1, _i2, j1, j2 in self._opcodes:
            if tag == "equal":
                n = j2 - j1
                if not self._collapsed or n <= _COLLAPSE_THRESHOLD:
                    rows = n
                else:
                    rows = 3  # first + separator + last
                if row_idx < idx + rows:
                    # Inside an equal run — not clickable
                    return None
                idx += rows
            elif tag in ("replace", "insert"):
                n = j2 - j1
                if idx <= row_idx < idx + n:
                    return proposed_keys[j1 + (row_idx - idx)]
                idx += n
            # 'delete' adds rows to left tree only, not right
        return None

    def _apply_all(self):
        for name in self._accepted:
            self._accepted[name] = True
        self._populate()
        self._update_status()

    def _toggle_collapse(self):
        self._collapsed = self._collapse_switch.get() == 1
        self._populate()

    def _update_status(self):
        total = len(self._accepted)
        accepted = sum(1 for v in self._accepted.values() if v)
        if total == 0:
            self._status_label.configure(text="No changes proposed")
        else:
            self._status_label.configure(
                text=f"{accepted}/{total} moves accepted"
            )

    # --------------------------------------------------------------- done

    def _done(self):
        """Build final order: apply accepted moves, keep ignored in place."""
        accepted_names = {n for n, v in self._accepted.items() if v}
        if not accepted_names:
            self.result = list(self._current)
        elif len(accepted_names) == len(self._accepted):
            self.result = [si.plugin_name for si in self._proposed]
        else:
            self.result = self._merge_partial(accepted_names)
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
            if name in accepted_names and name in self._moved_names:
                continue  # placed by proposed order below
            fixed_queue.append(name)

        # Walk the proposed order to build the result
        result: list[str] = []
        fixed_iter = iter(fixed_queue)
        for si in self._proposed:
            if si.plugin_name in accepted_names and si.plugin_name in self._moved_names:
                result.append(si.plugin_name)
            else:
                item = next(fixed_iter, None)
                if item is not None:
                    result.append(item)

        # Append any remaining fixed items
        for item in fixed_iter:
            result.append(item)

        return result

    def _cancel(self):
        self.result = None
        self.destroy()

    # ---------------------------------------------------------- hints dialog

    def _show_hint_dialog(self, plugin_name: str):
        """Open a transient dialog listing every constraint that touched
        this plugin, with winner badges per concern and rulebook filename
        attribution."""
        si = self._proposed_map.get(plugin_name)
        if si is None or si.decision is None:
            return

        decision = si.decision
        color = self._move_colors.get(plugin_name, "#888888")
        dlg = ctk.CTkToplevel(self)
        dlg.title(f"Hints for {si.display_name}")
        dlg.minsize(480, 300)
        from starfield_tool.dialogs import center_dialog
        center_dialog(dlg, 560, 420)
        dlg.attributes("-topmost", True)
        dlg.after(100, lambda: dlg.attributes("-topmost", False))

        # --- header: swatch + name + tier/position summary
        header = ctk.CTkFrame(dlg, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(10, 4))

        swatch = tk.Frame(header, bg=color, width=16, height=16)
        swatch.pack(side="left", padx=(0, 8))
        swatch.pack_propagate(False)

        ctk.CTkLabel(
            header, text=si.display_name,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        summary = (f"tier {decision.tier}  "
                   f"\u00b7  was #{si.original_index + 1} "
                   f"\u2192 #{si.new_index + 1}")
        ctk.CTkLabel(
            dlg, text=summary, font=ctk.CTkFont(size=11),
            text_color="#aaaaaa",
        ).pack(padx=12, anchor="w", pady=(0, 6))

        # --- body: scrollable list of constraints
        body = ctk.CTkScrollableFrame(dlg, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=(4, 4))

        constraints = sorted(
            decision.all_constraints,
            key=lambda c: (-c.priority, c.sorter_name),
        )

        winner_bg = "#2e5c3a"
        winner_fg = "#cdeecf"
        note_fg = "#888888"

        if not constraints:
            ctk.CTkLabel(
                body, text="No constraint data available.",
                font=ctk.CTkFont(size=11),
                text_color=note_fg,
            ).pack(anchor="w", padx=4, pady=8)

        for c in constraints:
            is_tier_winner = (
                c.type == "tier"
                and c.sorter_name == decision.sorter_name
            )
            is_edge_winner = (
                c.type == "load_after"
                and decision.load_after_sorters.get(c.after) == c.sorter_name
            )
            is_winner = is_tier_winner or is_edge_winner

            # Container for the constraint — stacks sorter row + detail row
            container = ctk.CTkFrame(
                body,
                fg_color=winner_bg if is_winner else "transparent",
                corner_radius=4,
            )
            container.pack(fill="x", padx=2, pady=2)

            # Top row: sorter name (left), priority + WINNER badge (right)
            top = ctk.CTkFrame(container, fg_color="transparent")
            top.pack(fill="x")

            ctk.CTkLabel(
                top, text=c.sorter_name or "?",
                font=ctk.CTkFont(family="Consolas", size=11),
                text_color=winner_fg if is_winner else None,
                anchor="w", justify="left",
            ).pack(side="left", padx=(8, 6), pady=(4, 0))

            if is_winner:
                badge_text = "WINNER: tier" if is_tier_winner else "WINNER: edge"
                ctk.CTkLabel(
                    top, text=badge_text,
                    font=ctk.CTkFont(size=9, weight="bold"),
                    text_color=winner_fg,
                ).pack(side="right", padx=(0, 8), pady=(4, 0))

            ctk.CTkLabel(
                top, text=f"p={c.priority}",
                font=ctk.CTkFont(size=10),
                text_color=winner_fg if is_winner else note_fg,
            ).pack(side="right", padx=(0, 6), pady=(4, 0))

            # Second row: constraint detail, indented
            if c.type == "tier":
                detail = f"\u2192 tier {c.tier}"
            elif c.type == "load_after":
                detail = f"\u2192 load_after {c.after}"
            else:
                detail = f"\u2192 {c.type}"
            ctk.CTkLabel(
                container, text=detail,
                font=ctk.CTkFont(size=11),
                text_color=winner_fg if is_winner else None,
                anchor="w", justify="left",
            ).pack(fill="x", padx=(24, 8), pady=(0, 4))

            # Greyed note below the container, indented — only when present
            if c.note:
                ctk.CTkLabel(
                    body, text=c.note,
                    font=ctk.CTkFont(size=10),
                    text_color=note_fg,
                    wraplength=480, justify="left", anchor="w",
                ).pack(fill="x", padx=(28, 8), pady=(0, 4))

        # --- close button
        ctk.CTkButton(
            dlg, text="Close", width=80,
            command=dlg.destroy,
            height=26, corner_radius=4,
            font=ctk.CTkFont(size=12),
            fg_color="#314c79", hover_color="#3d5f99",
        ).pack(pady=(4, 10))
