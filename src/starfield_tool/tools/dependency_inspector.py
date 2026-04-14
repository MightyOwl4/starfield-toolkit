"""Dependency Inspector tool — visualise hard and soft dependencies
across the installed creations load order.

Public API:
    build_dependency_graph, ancestors, descendants, assign_sides,
    load_soft_dependencies, DependencyInspectorTool

Per spec 012-dependency-inspector: read-only inspector that mirrors the
diff-dialog presentation model (centered datagrid + side connectors).
"""
from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from tkinter import ttk
from typing import Callable, Iterable, Literal, Mapping

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from bethesda_creations.catalogue import load_catalogue
from starfield_tool.base import ModuleContext, ToolModule
from starfield_tool.models import Creation
from starfield_tool.parsers import build_creation_list
from starfield_tool.tools.load_order_diff import _MOVE_COLORS, _hex_with_alpha


Kind = Literal["hard", "soft"]
Side = Literal["left", "right"]


# ---------------------------------------------------------------- types

@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: Kind


@dataclass
class DependencyGraph:
    order: list[str]
    position: dict[str, int]
    out_edges: dict[str, list[str]]
    in_edges: dict[str, list[str]]
    edge_kind: dict[tuple[str, str], Kind]
    palette_color: dict[str, str]
    no_deps: set[str]
    missing_hard: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class InspectorViewState:
    hide_soft: bool = False
    hide_no_deps: bool = False
    selected: str | None = None


# ---------------------------------------------------------------- core

def build_dependency_graph(
    creations: list[Creation],
    catalogue: Mapping[str, dict],
    soft_deps: Mapping[str, list[str]],
) -> DependencyGraph:
    """Build a frozen-at-load dependency graph.

    See specs/012-dependency-inspector/research.md (Decisions 1, 2, 3, 6)
    and data-model.md for the invariants.
    """
    order = [c.content_id for c in creations]
    position = {cid: i for i, cid in enumerate(order)}
    installed = set(order)

    raw_edges: dict[tuple[str, str], Kind] = {}
    missing_hard: dict[str, list[str]] = {}

    for cid in order:
        entry = catalogue.get(cid) or {}
        for t in entry.get("required_mods", []) or []:
            if not isinstance(t, str) or t == cid:
                continue
            if t not in installed:
                missing_hard.setdefault(cid, []).append(t)
                continue
            raw_edges[(cid, t)] = "hard"

    for cid, targets in (soft_deps or {}).items():
        if cid not in installed:
            continue
        for t in targets:
            if not isinstance(t, str) or t == cid or t not in installed:
                continue
            raw_edges.setdefault((cid, t), "soft")

    edges: dict[tuple[str, str], Kind] = {}
    for (s, t), kind in raw_edges.items():
        if position[t] >= position[s]:
            continue
        edges[(s, t)] = kind

    out_edges: dict[str, list[str]] = {cid: [] for cid in order}
    in_edges: dict[str, list[str]] = {cid: [] for cid in order}
    for (s, t) in edges:
        out_edges[s].append(t)
        in_edges[t].append(s)

    for cid in order:
        out_edges[cid].sort(key=lambda x: position[x])
        in_edges[cid].sort(key=lambda x: position[x])

    no_deps = {cid for cid in order if not out_edges[cid] and not in_edges[cid]}

    edge_color: dict[tuple[str, str], str] = {}
    canonical = sorted(edges, key=lambda e: (position[e[0]], position[e[1]]))
    for i, e in enumerate(canonical):
        edge_color[e] = _MOVE_COLORS[i % len(_MOVE_COLORS)]

    palette_color: dict[str, str] = {}
    for cid in order:
        if cid in no_deps:
            continue
        if out_edges[cid]:
            palette_color[cid] = edge_color[(cid, out_edges[cid][0])]
        else:
            palette_color[cid] = edge_color[(in_edges[cid][0], cid)]

    return DependencyGraph(
        order=order,
        position=position,
        out_edges=out_edges,
        in_edges=in_edges,
        edge_kind=edges,
        palette_color=palette_color,
        no_deps=no_deps,
        missing_hard=missing_hard,
    )


def ancestors(
    graph: DependencyGraph,
    node: str,
    visible_edges: Callable[[str, str], bool] | None = None,
) -> set[str]:
    """All creations *node* transitively depends on (follow out_edges)."""
    pred = visible_edges or (lambda _s, _t: True)
    seen: set[str] = set()
    queue = deque([node])
    while queue:
        n = queue.popleft()
        for parent in graph.out_edges.get(n, []):
            if not pred(n, parent) or parent == node or parent in seen:
                continue
            seen.add(parent)
            queue.append(parent)
    return seen


def descendants(
    graph: DependencyGraph,
    node: str,
    visible_edges: Callable[[str, str], bool] | None = None,
) -> set[str]:
    """All creations that transitively depend on *node* (follow in_edges)."""
    pred = visible_edges or (lambda _s, _t: True)
    seen: set[str] = set()
    queue = deque([node])
    while queue:
        n = queue.popleft()
        for child in graph.in_edges.get(n, []):
            if not pred(child, n) or child == node or child in seen:
                continue
            seen.add(child)
            queue.append(child)
    return seen


def _segments_cross(
    e1: tuple[str, str],
    e2: tuple[str, str],
    pos: Mapping[str, int],
) -> bool:
    a1, b1 = sorted((pos[e1[0]], pos[e1[1]]))
    a2, b2 = sorted((pos[e2[0]], pos[e2[1]]))
    return (a1 < a2 < b1 < b2) or (a2 < a1 < b2 < b1)


def assign_sides(
    edges: Iterable[tuple[str, str]],
    position: Mapping[str, int],
) -> dict[tuple[str, str], Side]:
    """Greedy longest-first router (research.md Decision 4)."""
    edge_list = sorted(
        edges, key=lambda e: -abs(position[e[0]] - position[e[1]])
    )
    placed_left: list[tuple[str, str]] = []
    placed_right: list[tuple[str, str]] = []
    out: dict[tuple[str, str], Side] = {}
    for e in edge_list:
        cl = sum(1 for p in placed_left if _segments_cross(e, p, position))
        cr = sum(1 for p in placed_right if _segments_cross(e, p, position))
        if cl < cr:
            side: Side = "left"
        elif cr < cl:
            side = "right"
        else:
            side = "left" if len(placed_left) <= len(placed_right) else "right"
        out[e] = side
        (placed_left if side == "left" else placed_right).append(e)
    return out


# ---------------------------------------------------------- soft-dep I/O

def load_soft_dependencies(
    creations: list[Creation],
    rulebook_path: Path | None = None,
) -> dict[str, list[str]]:
    """Load soft dependencies from the description-parser rulebook and
    translate plugin filenames to content_ids using installed creations'
    plugin_files."""
    if rulebook_path is None:
        app_data = os.environ.get("APPDATA", "")
        if not app_data:
            return {}
        rulebook_path = (
            Path(app_data) / "StarfieldToolkit" / "patch_order_rules.json"
        )
    try:
        data = json.loads(rulebook_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}

    fn_to_cid: dict[str, str] = {}
    for c in creations:
        for fn in c.plugin_files:
            fn_to_cid.setdefault(fn.lower(), c.content_id)

    soft: dict[str, list[str]] = {}
    for rule in data.get("rules", []):
        if not isinstance(rule, dict):
            continue
        plugin = rule.get("plugin", "")
        if not isinstance(plugin, str):
            continue
        src = fn_to_cid.get(plugin.lower())
        if not src:
            continue
        for after in rule.get("load_after", []) or []:
            if not isinstance(after, str):
                continue
            tgt = fn_to_cid.get(after.lower())
            if not tgt or tgt == src:
                continue
            soft.setdefault(src, []).append(tgt)
    return soft


# ----------------------------------------------------------------- UI

_CONNECTOR_WIDTH = 120
_DOT_RADIUS = 4
_NO_DEP_FG = "#888888"
_WARN_COLOR = "#e55353"


class DependencyInspectorTool(ToolModule):
    name = "Dependency Inspector"
    description = (
        "Visualise hard and soft dependencies across installed creations"
    )

    def __init__(self):
        self._context: ModuleContext | None = None
        self._creations: list[Creation] = []
        self._graph: DependencyGraph | None = None
        self._state = InspectorViewState()
        self._tree: ttk.Treeview | None = None
        self._left_canvas: tk.Canvas | None = None
        self._right_canvas: tk.Canvas | None = None
        self._iid_by_cid: dict[str, str] = {}
        self._cid_by_iid: dict[str, str] = {}
        self._sides: dict[tuple[str, str], Side] = {}
        # PhotoImage refs to prevent GC.
        self._left_photo: ImageTk.PhotoImage | None = None
        self._right_photo: ImageTk.PhotoImage | None = None
        self._bg = "#2b2b2b"
        self._fg = "#dcdcdc"

    def initialize(self, context: ModuleContext) -> None:
        self._context = context
        frame = context.content_frame

        is_dark = ctk.get_appearance_mode() == "Dark"
        if is_dark:
            self._bg = "#2b2b2b"
            self._fg = "#dcdcdc"
            sel_bg = "#314c79"
            heading_bg = "#1f1f1f"
            heading_fg = "#aaaaaa"
        else:
            self._bg = "#ffffff"
            self._fg = "#000000"
            sel_bg = "#314c79"
            heading_bg = "#e0e0e0"
            heading_fg = "#333333"

        # Toolbar
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(2, 4))

        _btn_kw = dict(
            height=26, corner_radius=4, font=ctk.CTkFont(size=12),
            fg_color="#314c79", hover_color="#3d5f99",
        )
        ctk.CTkButton(
            top, text="Refresh", width=70, command=self._refresh, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        # Toggles use CTkSwitch to match the diff dialog.
        self._hide_soft_var = tk.IntVar(value=0)
        _soft_frame = ctk.CTkFrame(top, fg_color="transparent")
        _soft_frame.pack(side="left", padx=(8, 6))
        ctk.CTkLabel(
            _soft_frame, text="Hide soft dependencies",
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 6))
        self._hide_soft_switch = ctk.CTkSwitch(
            _soft_frame, text="", width=40,
            variable=self._hide_soft_var,
            command=self._on_hide_soft_toggle,
        )
        self._hide_soft_switch.pack(side="left")

        # "Collapse creations without dependencies" — on by default,
        # mirrors the diff dialog "Collapse unchanged" pattern (one
        # separator row per contiguous run of no-deps creations).
        self._collapse_no_deps_var = tk.IntVar(value=1)
        _collapse_frame = ctk.CTkFrame(top, fg_color="transparent")
        _collapse_frame.pack(side="left", padx=(8, 6))
        ctk.CTkLabel(
            _collapse_frame, text="Collapse creations without dependencies",
            font=ctk.CTkFont(size=11),
        ).pack(side="left", padx=(0, 6))
        self._collapse_switch = ctk.CTkSwitch(
            _collapse_frame, text="", width=40,
            variable=self._collapse_no_deps_var,
            command=self._on_collapse_toggle,
        )
        self._collapse_switch.pack(side="left")
        self._collapse_switch.select()  # default ON
        self._state.hide_no_deps = True

        self._summary = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=11))
        self._summary.pack(side="right", padx=8)

        # Treeview style
        from starfield_tool.grid_style import (
            grid_font, grid_heading_font, grid_rowheight,
        )
        style = ttk.Style()
        style.configure(
            "Inspector.Treeview",
            background=self._bg, foreground=self._fg,
            fieldbackground=self._bg, rowheight=grid_rowheight(extra=4),
            borderwidth=0, font=grid_font(),
        )
        style.configure(
            "Inspector.Treeview.Heading",
            background=heading_bg, foreground=heading_fg,
            borderwidth=1, relief="flat", font=grid_heading_font(),
        )
        style.map(
            "Inspector.Treeview",
            background=[("selected", sel_bg)],
            foreground=[("selected", "#ffffff")],
        )

        # Outer scrollable frame — the WHOLE row block (canvas | tree | canvas)
        # scrolls together, with one scrollbar at the right edge of the window.
        # Tree is sized to fit all rows; its internal scroll is unused.
        self._scroll_frame = ctk.CTkScrollableFrame(
            frame, fg_color=self._bg,
        )
        self._scroll_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        # 5-column layout inside the scrollable area: spacer | left canvas |
        # tree | right canvas | spacer.
        body = self._scroll_frame
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, minsize=_CONNECTOR_WIDTH, weight=0)
        body.grid_columnconfigure(2, weight=0)
        body.grid_columnconfigure(3, minsize=_CONNECTOR_WIDTH, weight=0)
        body.grid_columnconfigure(4, weight=1)

        self._left_canvas = tk.Canvas(
            body, width=_CONNECTOR_WIDTH, bg=self._bg,
            highlightthickness=0, bd=0,
        )
        self._left_canvas.grid(row=0, column=1, sticky="n")

        columns = ("warn", "#", "Name")
        self._tree = ttk.Treeview(
            body, columns=columns, show="headings",
            selectmode="browse", style="Inspector.Treeview",
            height=1,  # resized in _populate_tree to fit all rows
        )
        self._tree.heading("warn", text="!", anchor="center")
        self._tree.heading("#", text="#", anchor="center")
        self._tree.heading("Name", text="Name", anchor="w")
        self._tree.column("warn", width=24, anchor="center", stretch=False)
        self._tree.column("#", width=40, anchor="center", stretch=False)
        self._tree.column("Name", width=520, anchor="w", stretch=False)
        self._tree.grid(row=0, column=2, sticky="n")

        self._right_canvas = tk.Canvas(
            body, width=_CONNECTOR_WIDTH, bg=self._bg,
            highlightthickness=0, bd=0,
        )
        self._right_canvas.grid(row=0, column=3, sticky="n")

        # Tag for the warning indicator color
        self._tree.tag_configure("missing_hard", foreground=_WARN_COLOR)
        self._tree.tag_configure("no_dep", foreground=_NO_DEP_FG)
        # Zebra striping for row separation (Treeview can't draw per-row borders).
        zebra_bg = "#333333" if is_dark else "#f3f3f3"
        self._tree.tag_configure("zebra", background=zebra_bg)
        # Collapsed-run separator (matches diff dialog's "— N unchanged —").
        sep_bg = "#383838" if is_dark else "#dddddd"
        sep_fg = "#888888"
        self._tree.tag_configure(
            "separator", background=sep_bg, foreground=sep_fg,
        )

        # Selection / click handlers
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        # Click on already-selected row clears selection
        self._tree.bind("<Button-1>", self._on_click, add="+")
        self._left_canvas.bind("<Button-1>", lambda _e: self._clear_selection())
        self._right_canvas.bind("<Button-1>", lambda _e: self._clear_selection())
        # Empty area inside the scrollable frame (below tree, side margins).
        try:
            self._scroll_frame._parent_canvas.bind(
                "<Button-1>", lambda _e: self._clear_selection(), add="+",
            )
        except AttributeError:
            pass
        self._left_canvas.bind("<Configure>", lambda _e: self._redraw_connectors())
        self._right_canvas.bind("<Configure>", lambda _e: self._redraw_connectors())
        # Forward wheel events on the tree to the outer scrollable frame.
        # Plain bind (no add="+") + returning "break" suppresses the
        # Treeview class binding that would otherwise consume the event.
        # Canvases need no override — they have no native wheel handler,
        # and CTkScrollableFrame's all-binding handles them naturally.
        self._tree.bind("<MouseWheel>", self._forward_wheel)
        self._tree.bind("<Button-4>", self._forward_wheel)
        self._tree.bind("<Button-5>", self._forward_wheel)

        self._refresh()

    # --------------------------------------------------- data refresh

    def _refresh(self) -> None:
        if not self._context:
            return
        self._context.status_bar.set_task("Building dependency graph...")

        def _run():
            try:
                creations = build_creation_list(
                    self._context.game_installation
                )
                catalogue = load_catalogue()
                soft = load_soft_dependencies(creations)
                graph = build_dependency_graph(creations, catalogue, soft)
                self._tree.after(
                    0, lambda: self._on_built(creations, graph)
                )
            except Exception as e:  # pragma: no cover — UI-thread surface
                msg = str(e)
                self._tree.after(
                    0, lambda: self._on_error(msg)
                )

        threading.Thread(target=_run, daemon=True).start()

    def _on_built(
        self, creations: list[Creation], graph: DependencyGraph,
    ) -> None:
        self._creations = creations
        self._graph = graph
        self._state.selected = None
        self._populate_tree()
        self._update_summary()
        self._compute_sides()
        self._redraw_connectors()
        self._context.status_bar.clear_task()

    def _on_error(self, message: str) -> None:
        if self._context:
            self._context.status_bar.set_task(f"Error: {message}")
            self._tree.after(3000, self._context.status_bar.clear_task)

    def _update_summary(self) -> None:
        if not self._graph:
            self._summary.configure(text="")
            return
        total = len(self._graph.order)
        with_deps = total - len(self._graph.no_deps)
        edges = len(self._graph.edge_kind)
        miss = sum(len(v) for v in self._graph.missing_hard.values())
        text = f"{total} creations · {with_deps} with deps · {edges} edges"
        if miss:
            text += f" · {miss} missing hard"
        self._summary.configure(text=text)

    # ---------------------------------------------------- visible sets

    def _visible_edge(self, s: str, t: str) -> bool:
        if not self._graph:
            return False
        kind = self._graph.edge_kind.get((s, t))
        if kind is None:
            return False
        if self._state.hide_soft and kind == "soft":
            return False
        return True

    # ----------------------------------------------------- populate

    def _populate_tree(self) -> None:
        if not self._tree or not self._graph:
            return
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._iid_by_cid.clear()
        self._cid_by_iid.clear()

        creation_by_cid = {c.content_id: c for c in self._creations}
        used_colors: set[str] = set()
        n_rows = 0
        run: list[str] = []  # accumulating run of no_deps cids when collapsing

        def flush_run():
            nonlocal n_rows, run
            if not run:
                return
            n = len(run)
            if not self._state.hide_no_deps or n <= 1:
                # Don't collapse; emit each row individually.
                for cid in run:
                    self._insert_creation_row(cid, creation_by_cid, used_colors, n_rows)
                    n_rows += 1
            else:
                # Single separator row for the whole run.
                self._tree.insert(
                    "", "end",
                    values=("", "", f"\u2014 {n} collapsed \u2014"),
                    tags=("separator",),
                )
                n_rows += 1
            run = []

        for cid in self._graph.order:
            if cid in self._graph.no_deps:
                run.append(cid)
                continue
            flush_run()
            self._insert_creation_row(cid, creation_by_cid, used_colors, n_rows)
            n_rows += 1
        flush_run()

        # Size the tree to fit ALL rows so the outer scrollable frame is the
        # only scroller. Match the canvases' heights to the tree.
        self._tree.configure(height=max(n_rows, 1))
        self._tree.update_idletasks()
        rowheight = self._row_height()
        header = self._header_height()
        total_h = header + n_rows * rowheight + 4
        self._left_canvas.configure(height=total_h)
        self._right_canvas.configure(height=total_h)

    def _insert_creation_row(
        self,
        cid: str,
        creation_by_cid: dict[str, Creation],
        used_colors: set[str],
        row_idx: int,
    ) -> None:
        creation = creation_by_cid.get(cid)
        if creation is None:
            return
        pos_text = (
            str(creation.load_position + 1)
            if creation.load_position is not None else "-"
        )
        warn = "!" if cid in self._graph.missing_hard else ""
        tags: list[str] = []
        if cid in self._graph.no_deps:
            tags.append("no_dep")
        else:
            color = self._graph.palette_color.get(cid)
            if color:
                tag = f"color_{color.lstrip('#')}"
                if color not in used_colors:
                    self._tree.tag_configure(tag, foreground=color)
                    used_colors.add(color)
                tags.append(tag)
        if warn:
            tags.append("missing_hard")
        if row_idx % 2 == 1:
            tags.append("zebra")
        iid = self._tree.insert(
            "", "end",
            values=(warn, pos_text, creation.display_name),
            tags=tuple(tags),
        )
        self._iid_by_cid[cid] = iid
        self._cid_by_iid[iid] = cid

    # ---------------------------------------------------- selection

    def _on_select(self, _event=None) -> None:
        if not self._tree:
            return
        sel = self._tree.selection()
        if not sel:
            self._state.selected = None
        else:
            self._state.selected = self._cid_by_iid.get(sel[0])
        self._redraw_connectors()

    def _on_click(self, event) -> None:
        if not self._tree:
            return
        iid = self._tree.identify_row(event.y)
        if not iid:
            # Click on empty area below rows — clear selection.
            self._tree.after(1, self._clear_selection)
            return
        cid = self._cid_by_iid.get(iid)
        if cid is None:
            # Separator row — not selectable; clear any prior selection.
            self._tree.after(1, self._clear_selection)
            return
        if cid == self._state.selected:
            # Toggle off
            self._tree.after(1, self._clear_selection)

    def _clear_selection(self) -> None:
        if not self._tree:
            return
        self._tree.selection_remove(self._tree.selection())
        self._state.selected = None
        self._redraw_connectors()

    # ----------------------------------------------------- toggles

    def _on_hide_soft_toggle(self) -> None:
        self._state.hide_soft = bool(self._hide_soft_var.get())
        self._compute_sides()
        self._redraw_connectors()

    def _on_collapse_toggle(self) -> None:
        self._state.hide_no_deps = bool(self._collapse_no_deps_var.get())
        # Preserve selection if it still exists.
        prev_sel = self._state.selected
        self._populate_tree()
        if prev_sel and prev_sel in self._iid_by_cid:
            iid = self._iid_by_cid[prev_sel]
            self._tree.selection_set(iid)
            self._state.selected = prev_sel
        else:
            self._state.selected = None
        self._compute_sides()
        self._redraw_connectors()

    # ------------------------------------------------ side assignment

    def _compute_sides(self) -> None:
        if not self._graph:
            self._sides = {}
            return
        visible_edges = [
            e for e in self._graph.edge_kind
            if self._visible_edge(*e)
        ]
        self._sides = assign_sides(visible_edges, self._graph.position)

    # ----------------------------------------------------- scrolling

    def _forward_wheel(self, event):
        """Replicate CTkScrollableFrame's wheel behaviour for the tree.

        Returning "break" suppresses the Treeview class binding that
        would otherwise consume the wheel event and slow scrolling.
        """
        if not self._scroll_frame:
            return "break"
        try:
            inner = self._scroll_frame._parent_canvas  # CTk private
        except AttributeError:
            return "break"
        # Match CTkScrollableFrame._mouse_wheel_all exactly so wheel feel
        # is identical over the tree and over the side canvases. CTk sets
        # yscrollincrement=1 on Windows and scrolls by delta/6 units (~20 px
        # per 120-delta notch).
        import sys as _sys
        if event.num == 4:
            steps = -5
        elif event.num == 5:
            steps = 5
        elif _sys.platform.startswith("win"):
            steps = -int(event.delta / 6)
        else:
            steps = -event.delta
        try:
            inner.yview_scroll(steps, "units")
        except tk.TclError:
            pass
        return "break"

    # ----------------------------------------------------- geometry helpers

    def _row_height(self) -> int:
        try:
            return int(ttk.Style().lookup("Inspector.Treeview", "rowheight")) or 25
        except (ValueError, tk.TclError):
            return 25

    def _header_height(self) -> int:
        if not self._tree:
            return 22
        # Use the first row's bbox to derive header offset.
        children = self._tree.get_children()
        if children:
            bbox = self._tree.bbox(children[0])
            if bbox:
                return bbox[1]
        return 22

    # ---------------------------------------------------- highlights

    def _highlight_set(self) -> tuple[set[str], set[tuple[str, str]]]:
        """Return (highlighted_nodes, highlighted_edges)."""
        if not self._graph or self._state.selected is None:
            return set(), set()
        sel = self._state.selected
        anc = ancestors(self._graph, sel, self._visible_edge)
        desc = descendants(self._graph, sel, self._visible_edge)
        nodes = {sel} | anc | desc
        edges: set[tuple[str, str]] = set()
        # Edge in highlight if both endpoints in `nodes` AND edge is "in chain"
        # — i.e. one endpoint is sel or transitively reachable in the matching
        # direction from sel. Simpler check: both endpoints in nodes is fine
        # because directed-closure structure already excludes siblings.
        for (s, t) in self._graph.edge_kind:
            if not self._visible_edge(s, t):
                continue
            if s in nodes and t in nodes:
                edges.add((s, t))
        return nodes, edges

    # --------------------------------------------------- connector draw

    def _row_y(self, iid: str) -> int:
        """Y-center of a row in canvas coords.

        The canvases share their top edge with the tree (same grid row,
        sticky=n) and the entire scrollable area moves as a unit, so a
        row's Y inside the tree equals its Y inside either canvas.
        Computed from row index because off-screen rows return no bbox.
        """
        children = self._tree.get_children()
        try:
            row_idx = children.index(iid)
        except ValueError:
            return -20
        return self._header_height() + row_idx * self._row_height() + self._row_height() // 2

    def _redraw_connectors(self) -> None:
        if not self._graph or not self._left_canvas or not self._right_canvas:
            return

        hl_nodes, hl_edges = self._highlight_set()
        has_selection = self._state.selected is not None

        for canvas, side in (
            (self._left_canvas, "left"), (self._right_canvas, "right"),
        ):
            self._draw_side(canvas, side, hl_edges, has_selection)

    def _draw_side(
        self,
        canvas: tk.Canvas,
        side: Side,
        hl_edges: set[tuple[str, str]],
        has_selection: bool,
    ) -> None:
        canvas.delete("connector")
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return

        SS = 2
        img = Image.new("RGBA", (cw * SS, ch * SS), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        r = _DOT_RADIUS

        # Filter edges assigned to this side.
        edges_for_side = [
            e for e, s in self._sides.items() if s == side
        ]
        # Draw highlighted last so they sit on top.
        edges_for_side.sort(key=lambda e: e in hl_edges)

        drew = False
        for (src, tgt) in edges_for_side:
            li = self._iid_by_cid.get(src)
            ti = self._iid_by_cid.get(tgt)
            if not li or not ti:
                continue
            ys = self._row_y(li)
            yt = self._row_y(ti)
            if ys < 0 or yt < 0:
                continue

            kind = self._graph.edge_kind.get((src, tgt), "hard")
            base_color = self._graph.palette_color.get(src) or "#888888"
            highlighted = (src, tgt) in hl_edges
            if highlighted:
                color = "#ffffff"
                width = 3 * SS
            elif has_selection:
                color = _hex_with_alpha(base_color, 70)
                width = 2 * SS
            else:
                color = base_color
                width = 2 * SS
            # Soft edges are drawn with a thinner line as a visual cue.
            if kind == "soft" and not highlighted:
                width = max(1 * SS, width - SS)

            # Bezier control points: arc out to the canvas far edge.
            # Inner edge (touching the tree) is at x=0 for right, x=cw for left.
            if side == "right":
                inner_x = 0
                outer_x = cw * 0.85
            else:
                inner_x = cw
                outer_x = cw * 0.15
            p0 = (inner_x, ys)
            p1 = (outer_x, ys)
            p2 = (outer_x, yt)
            p3 = (inner_x, yt)

            steps = 32
            pts = []
            for i in range(steps + 1):
                t = i / steps
                mt = 1 - t
                x = (mt**3 * p0[0] + 3 * mt**2 * t * p1[0]
                     + 3 * mt * t**2 * p2[0] + t**3 * p3[0])
                y = (mt**3 * p0[1] + 3 * mt**2 * t * p1[1]
                     + 3 * mt * t**2 * p2[1] + t**3 * p3[1])
                pts.append((x * SS, y * SS))

            if highlighted:
                glow = _hex_with_alpha("#ffffff", 60)
                draw.line(pts, fill=glow, width=8 * SS, joint="curve")

            draw.line(pts, fill=color, width=width, joint="curve")

            dot_r = r + 1 if highlighted else r
            for xy_y in (ys, yt):
                if side == "right":
                    x0 = 0
                    x1 = (2 * dot_r) * SS
                else:
                    x0 = (cw - 2 * dot_r) * SS
                    x1 = cw * SS
                draw.ellipse(
                    [x0, (xy_y - dot_r) * SS,
                     x1, (xy_y + dot_r) * SS],
                    fill=color,
                )
            drew = True

        if not drew:
            return

        smoothed = img.resize((cw, ch), Image.LANCZOS)
        try:
            bg_rgb = canvas.winfo_rgb(self._bg)
            bg_tuple = (
                bg_rgb[0] // 256, bg_rgb[1] // 256, bg_rgb[2] // 256, 255,
            )
        except tk.TclError:
            bg_tuple = (43, 43, 43, 255)
        background = Image.new("RGBA", smoothed.size, bg_tuple)
        background.paste(smoothed, (0, 0), smoothed)
        photo = ImageTk.PhotoImage(background)
        if side == "left":
            self._left_photo = photo
        else:
            self._right_photo = photo
        canvas.create_image(0, 0, image=photo, anchor="nw", tags="connector")
