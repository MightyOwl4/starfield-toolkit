"""Shared grid/treeview font+rowheight helpers.

All ttk.Treeview styles across the app should use these helpers so a single
user-configurable font size drives everything consistently.  Rowheight is
derived from font size so rows always have breathing room.
"""
from starfield_tool.config import load_config


def grid_font_size() -> int:
    """Current user-configured grid body font size."""
    return load_config().grid_font_size


def grid_font(bold: bool = False) -> tuple:
    """Tk font tuple for the Treeview body.  Pass bold=True for bold rows."""
    size = grid_font_size()
    if bold:
        return ("Segoe UI", size, "bold")
    return ("Segoe UI", size)


def grid_rowheight(extra: int = 0) -> int:
    """Row height derived from font size, with optional extra padding.

    Formula tuned so size=10→24, size=11→26, size=12→29, size=13→31.
    """
    size = grid_font_size()
    return max(20, int(size * 2.4) + extra)


def grid_heading_font() -> tuple:
    """Heading uses a slightly smaller bold font by convention."""
    size = grid_font_size()
    return ("Segoe UI", max(8, size - 2), "bold")


# Registry of (style_name, rowheight_extra) pairs for every Treeview style
# used in the app.  Each tool's style.configure() adds its name here so the
# "Grid font size..." setting can refresh all grids live without restart.
_STYLE_NAMES: list[tuple[str, int]] = [
    ("Diff.Treeview", 0),
    ("RuleBook.Treeview", 0),
    ("FastLane.Treeview", 0),
    ("LO.Treeview", 4),
    ("Treeview", 4),  # used by creation_load_order
]

_HEADING_STYLE_NAMES: list[str] = [
    "Diff.Treeview.Heading",
    "LO.Treeview.Heading",
    "Treeview.Heading",
]


def refresh_all_grid_styles():
    """Re-apply font + rowheight to every known Treeview style.

    Call after the user changes grid_font_size — ttk.Style.configure on an
    existing style name pushes the update to already-rendered widgets.
    """
    from tkinter import ttk
    style = ttk.Style()
    body = grid_font()
    heading = grid_heading_font()
    for name, extra in _STYLE_NAMES:
        style.configure(name, font=body, rowheight=grid_rowheight(extra=extra))
    for name in _HEADING_STYLE_NAMES:
        style.configure(name, font=heading)
