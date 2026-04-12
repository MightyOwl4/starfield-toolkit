"""Fast Lane Creation Check tool.

Compares installed creations against a bundled pre-Fast-Lanes baseline
snapshot to identify mods that have not been updated since the baseline.

This is a short-lived feature — all related code lives here (and in
fast_lane_baseline_generator.py) for easy removal when the tool loses
relevance.
"""
import csv
import json
import logging
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from bethesda_creations._version_cmp import compare_versions
from starfield_tool.base import ModuleContext, ToolModule

log = logging.getLogger(__name__)

# Constellation color palette (matches existing tools)
_BTN_COLOR = "#314c79"
_BTN_HOVER = "#3d5f99"
_WARNING_BG = "#d4a71a"  # Constellation yellow
_WARNING_FG = "#1a1a1a"
_NOT_UPDATED_BG = "#d4a71a"  # yellow highlight
_LIKELY_UPDATED_BG = "#5f7f3a"  # muted green — cautiously optimistic
_LIKELY_UPDATED_FG = "#ffffff"
_UNKNOWN_FG = "#888888"
_SKIN_FG = "#888888"  # muted grey — non-obtrusive marker

# Status constants
STATUS_UPDATED = "updated"
STATUS_NOT_UPDATED = "not_updated"
STATUS_LIKELY_UPDATED = "likely_updated"  # version matches baseline BUT PS
#                                           support present → almost certainly
#                                           republished post-Free-Lanes without
#                                           a version bump.
STATUS_UNKNOWN = "unknown"
STATUS_SKIN = "skin"  # excluded from outdated check (skins rarely affected)

# Platform identifiers that prove post-Free-Lanes republish.
# (Free Lanes + PS5 launch: 2026-04-07)
_POST_FREE_LANES_PLATFORMS = frozenset({"PLAYSTATION4", "PLAYSTATION5"})

# Input mode constants
MODE_INSTALLED = "installed"
MODE_FILE = "file"


# --- Baseline Loader ---

def _load_baseline() -> dict | None:
    """Load the bundled baseline file. Returns None on any error.

    Checks PyInstaller bundle location first, then dev project root.
    """
    # Production: PyInstaller bundle
    if hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "data" / "creations_baseline.json"
        if bundled.exists():
            try:
                data = json.loads(bundled.read_text(encoding="utf-8"))
                if data.get("version") == 1:
                    return data
            except (OSError, json.JSONDecodeError):
                pass

    # Dev: project root / data / creations_baseline.json
    dev_path = Path(__file__).resolve().parents[3] / "data" / "creations_baseline.json"
    if dev_path.exists():
        try:
            data = json.loads(dev_path.read_text(encoding="utf-8"))
            if data.get("version") == 1:
                return data
        except (OSError, json.JSONDecodeError):
            pass

    return None


# --- Lookup and Classification ---

def _lookup_baseline(row: dict, baseline_entries: dict) -> dict | None:
    """Find a baseline entry for a row, matching by content_id or (title, author).

    Returns the baseline entry dict (with keys t, a, v) or None.
    """
    content_id = row.get("content_id", "")
    if content_id and content_id in baseline_entries:
        return baseline_entries[content_id]

    # Fallback: match by (title, author) case-insensitive
    row_title = (row.get("title") or "").strip().lower()
    row_author = (row.get("author") or "").strip().lower()
    if not row_title:
        return None

    for entry in baseline_entries.values():
        if (entry.get("t", "").strip().lower() == row_title
                and entry.get("a", "").strip().lower() == row_author):
            return entry

    # Title-only fallback (author strings are often inconsistent)
    for entry in baseline_entries.values():
        if entry.get("t", "").strip().lower() == row_title:
            return entry

    return None


def _classify(current: str | None, baseline: str | None) -> str:
    """Classify a comparison result.

    - updated: current > baseline
    - not_updated: current == baseline
    - unknown: either version missing
    """
    if not current or not baseline:
        return STATUS_UNKNOWN
    current = current.strip()
    baseline = baseline.strip()
    if not current or not baseline:
        return STATUS_UNKNOWN
    if current == baseline:
        return STATUS_NOT_UPDATED
    # compare_versions(installed, available) returns True if available > installed
    # We want: current > baseline → updated
    if compare_versions(baseline, current):
        return STATUS_UPDATED
    # current < baseline (user has an even older version somehow) or parse failure
    return STATUS_UNKNOWN


def _status_sort_key(row: dict) -> int:
    status = row.get("status")
    if status == STATUS_NOT_UPDATED:
        return 0
    if status == STATUS_UNKNOWN:
        return 1
    if status == STATUS_LIKELY_UPDATED:
        return 2
    if status == STATUS_SKIN:
        return 3
    return 4  # updated


# --- Export File Parsers ---

def _parse_csv(filepath: Path) -> tuple[list[dict], bool]:
    """Parse a CSV export. Returns (rows, is_legacy).

    Detects new-format by presence of 'Content ID' column.
    """
    rows = []
    is_legacy = False
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        is_legacy = "Content ID" not in fieldnames
        for raw in reader:
            rows.append(_row_from_dict(raw, is_legacy))
    return rows, is_legacy


def _parse_markdown(filepath: Path) -> tuple[list[dict], bool]:
    """Parse a Markdown table export. Returns (rows, is_legacy)."""
    content = filepath.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return [], False

    # Header
    header_cells = [c.strip() for c in lines[0].split("|") if c.strip()]
    is_legacy = "Content ID" not in header_cells

    # Skip separator row (line 1), parse data rows
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.split("|") if c.strip() or c == ""]
        # Remove empty leading/trailing from the split
        cells = [c for c in cells if c is not None]
        cells = [c.strip() for c in line.split("|")]
        # First and last are empty due to leading/trailing pipes
        cells = cells[1:-1] if len(cells) >= 2 else cells
        cells = [c.strip() for c in cells]

        if len(cells) < len(header_cells):
            continue
        raw = dict(zip(header_cells, cells))
        rows.append(_row_from_dict(raw, is_legacy))
    return rows, is_legacy


def _row_from_dict(raw: dict, is_legacy: bool) -> dict:
    """Build a standard row dict from parsed CSV/Markdown fields."""
    # Parse the "#" column as the load position. Exports use "-" for items
    # without a position, which we convert to None.
    pos_raw = (raw.get("#") or "").strip()
    try:
        load_position = int(pos_raw) if pos_raw and pos_raw != "-" else None
    except ValueError:
        load_position = None

    if is_legacy:
        # Legacy: #, Name, Author, Version, Date
        return {
            "content_id": "",
            "title": raw.get("Name", ""),
            "author": raw.get("Author", ""),
            "installed_version": raw.get("Version", ""),
            "load_position": load_position,
            "baseline_version": None,
            "current_version": None,
            "status": None,
        }
    # New format: #, Content ID, Name, Author, Installed Version, Date
    return {
        "content_id": raw.get("Content ID", ""),
        "title": raw.get("Name", ""),
        "author": raw.get("Author", ""),
        "installed_version": raw.get("Installed Version", ""),
        "load_position": load_position,
        "baseline_version": None,
        "current_version": None,
        "status": None,
    }


def _parse_export(filepath: Path) -> tuple[list[dict], bool]:
    """Auto-detect format and parse."""
    with open(filepath, encoding="utf-8") as f:
        first_line = f.readline().strip()
    if first_line.startswith("|"):
        return _parse_markdown(filepath)
    return _parse_csv(filepath)


# --- Tool Module ---

class FastLaneCheckTool(ToolModule):
    name = "Fast Lane Compatibility Check"
    description = (
        "Check which installed creations have not been updated since a "
        "pre-Fast-Lanes baseline — identifies mods likely broken by the update"
    )

    def __init__(self):
        self._context: ModuleContext | None = None
        self._baseline: dict | None = None
        self._rows: list[dict] = []
        self._checked: bool = False
        self._source_mode: str = MODE_INSTALLED
        # UI refs
        self._root_frame = None
        self._warning_label = None
        self._empty_frame = None
        self._loaded_frame = None
        self._tree: ttk.Treeview | None = None
        self._summary_label = None

    def initialize(self, context: ModuleContext) -> None:
        self._context = context
        self._baseline = _load_baseline()

        frame = context.content_frame
        self._root_frame = frame

        # --- Warning banner (always visible) ---
        self._build_warning_banner(frame)

        # --- Empty state (default) ---
        self._empty_frame = self._build_empty_state(frame)

        # --- Loaded state (hidden until data loads) ---
        self._loaded_frame = self._build_loaded_state(frame)
        self._loaded_frame.pack_forget()

    # ----- UI Construction -----

    def _build_warning_banner(self, parent):
        snapshot_text = "unknown date"
        if self._baseline:
            snap = self._baseline.get("snapshot_date", "")
            if snap:
                # Trim to YYYY-MM-DD for display
                snapshot_text = snap[:10]

        warning_text = (
            f"\u26A0 This check is APPROXIMATE. It compares each creation's current "
            f"published version (from Bethesda's API) against a baseline snapshot "
            f"(dated {snapshot_text}). A creation is flagged as \"not updated\" if "
            f"its current version still exactly matches the baseline. A creation "
            f"whose version matches the baseline BUT that now lists PlayStation "
            f"support is reclassified as \"likely updated\" — PS support was only "
            f"possible after the Free Lanes update (2026-04-07), so the author "
            f"republished even though they didn't bump the version. Skins are "
            f"excluded from the check as they are unlikely to be affected. Always "
            f"verify manually before making decisions."
        )

        banner = ctk.CTkFrame(parent, fg_color=_WARNING_BG, corner_radius=4)
        banner.pack(fill="x", padx=8, pady=(6, 4))

        self._warning_label = ctk.CTkLabel(
            banner,
            text=warning_text,
            text_color=_WARNING_FG,
            font=ctk.CTkFont(size=11, weight="bold"),
            wraplength=900,
            justify="left",
            anchor="w",
        )
        self._warning_label.pack(fill="x", padx=12, pady=8)

        if not self._baseline:
            # Extra error line if baseline is missing
            err_label = ctk.CTkLabel(
                banner,
                text="ERROR: Baseline file not found. The check cannot run.",
                text_color="#8b0000",
                font=ctk.CTkFont(size=11, weight="bold"),
            )
            err_label.pack(fill="x", padx=12, pady=(0, 8))

    def _build_empty_state(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=8, pady=20)

        # Centered content
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.place(relx=0.5, rely=0.4, anchor="center")

        prompt = ctk.CTkLabel(
            inner,
            text="Choose an input source to begin:",
            font=ctk.CTkFont(size=14),
        )
        prompt.pack(pady=(0, 16))

        _btn_kw = dict(
            height=50, width=240, corner_radius=6,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=_BTN_COLOR, hover_color=_BTN_HOVER,
        )

        ctk.CTkButton(
        inner, text="Import Installed creations",
            command=self._import_installed, **_btn_kw,
        ).pack(pady=6)

        ctk.CTkButton(
            inner, text="Import from snapshot",
            command=self._import_snapshot, **_btn_kw,
        ).pack(pady=6)

        ctk.CTkButton(
            inner, text="Import from CSV/TXT export",
            command=self._import_from_file, **_btn_kw,
        ).pack(pady=6)

        return frame

    def _build_loaded_state(self, parent):
        frame = ctk.CTkFrame(parent, fg_color="transparent")

        # Top button bar
        top = ctk.CTkFrame(frame, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(4, 4))

        _btn_kw = dict(
            height=30, corner_radius=4,
            font=ctk.CTkFont(size=12),
            fg_color=_BTN_COLOR, hover_color=_BTN_HOVER,
        )

        ctk.CTkButton(
            top, text="Reset", width=80,
            command=self._reset, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            top, text="Check", width=100,
            command=self._check, **_btn_kw,
        ).pack(side="left", padx=(0, 6))

        self._summary_label = ctk.CTkLabel(
            top, text="", font=ctk.CTkFont(size=12),
        )
        self._summary_label.pack(side="left", padx=(12, 0))

        # Treeview
        is_dark = ctk.get_appearance_mode() == "Dark"
        tree_bg = "#2b2b2b" if is_dark else "#ffffff"
        tree_fg = "#dcdcdc" if is_dark else "#1a1a1a"
        sel_bg = "#3d5f99" if is_dark else "#cce0ff"

        from starfield_tool.grid_style import grid_font, grid_rowheight
        style = ttk.Style()
        style.configure(
            "FastLane.Treeview",
            background=tree_bg, foreground=tree_fg,
            fieldbackground=tree_bg, rowheight=grid_rowheight(),
            font=grid_font(),
        )
        style.map("FastLane.Treeview", background=[("selected", sel_bg)])

        tree_frame = tk.Frame(frame, bg=tree_bg)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        columns = ("pos", "info", "title", "author",
                   "current", "baseline", "status")
        self._tree = ttk.Treeview(
            tree_frame, columns=columns, show="headings",
            style="FastLane.Treeview", selectmode="browse",
        )
        self._tree.heading("pos", text="#", anchor="w")
        self._tree.heading("info", text="", anchor="center")
        self._tree.heading("title", text="Title", anchor="w")
        self._tree.heading("author", text="Author", anchor="w")
        self._tree.heading("current", text="Current Version", anchor="w")
        self._tree.heading("baseline", text="Baseline Version", anchor="w")
        self._tree.heading("status", text="Status", anchor="w")

        self._tree.column("pos", width=50, minwidth=40, anchor="e")
        self._tree.column("info", width=28, minwidth=22, anchor="center",
                          stretch=False)
        self._tree.column("title", width=260, minwidth=150)
        self._tree.column("author", width=140, minwidth=100)
        self._tree.column("current", width=110, minwidth=80)
        self._tree.column("baseline", width=110, minwidth=80)
        self._tree.column("status", width=130, minwidth=100)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scrollbar.set)
        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Double-click row → show details (if cached info available).
        # Single-click on the info column → same.
        self._tree.bind("<Double-1>", self._on_tree_double_click)
        self._tree.bind("<Button-1>", self._on_tree_click)
        self._tree.configure(cursor="hand2")

        # Tag colors
        self._tree.tag_configure(
            "not_updated", background=_NOT_UPDATED_BG, foreground="#1a1a1a",
        )
        self._tree.tag_configure(
            "likely_updated",
            background=_LIKELY_UPDATED_BG, foreground=_LIKELY_UPDATED_FG,
        )
        self._tree.tag_configure("unknown", foreground=_UNKNOWN_FG)
        self._tree.tag_configure("skin", foreground=_SKIN_FG)

        return frame

    # ----- State Transitions -----

    def _show_empty_state(self):
        if self._loaded_frame:
            self._loaded_frame.pack_forget()
        if self._empty_frame:
            self._empty_frame.pack(fill="both", expand=True, padx=8, pady=20)

    def _show_loaded_state(self):
        if self._empty_frame:
            self._empty_frame.pack_forget()
        if self._loaded_frame:
            self._loaded_frame.pack(fill="both", expand=True)
        self._populate_tree()
        self._update_summary()

    def _populate_tree(self):
        if not self._tree:
            return
        self._tree.delete(*self._tree.get_children())
        for i, row in enumerate(self._rows):
            status = row.get("status")
            if status == STATUS_NOT_UPDATED:
                tags = ("not_updated",)
                status_text = "Not updated"
            elif status == STATUS_LIKELY_UPDATED:
                tags = ("likely_updated",)
                status_text = "Likely updated (PS)"
            elif status == STATUS_UPDATED:
                tags = ()
                status_text = "Updated"
            elif status == STATUS_UNKNOWN:
                tags = ("unknown",)
                status_text = "Unknown"
            elif status == STATUS_SKIN:
                tags = ("skin",)
                status_text = "\u26A0 Skin"
            else:
                tags = ()
                status_text = "(not checked)"

            # Load position for display — the row stores it from the import source
            pos = row.get("load_position")
            pos_text = str(pos) if pos is not None else "-"

            # Show API current version (from fetch_info) after the check;
            # before the check, fall back to installed_version as a hint of
            # what the row is about.
            current_display = (
                row.get("current_version")
                or row.get("installed_version", "")
                or "—"
            )
            # ⓘ icon visible only when we have cached info for this row
            info_cell = "\u24d8" if row.get("info") is not None else ""
            self._tree.insert(
                "", "end",
                iid=str(i),
                values=(
                    pos_text,
                    info_cell,
                    row.get("title", ""),
                    row.get("author", ""),
                    current_display,
                    row.get("baseline_version") or "",
                    status_text,
                ),
                tags=tags,
            )

    def _update_summary(self):
        if not self._summary_label:
            return
        total = len(self._rows)
        if not self._checked:
            self._summary_label.configure(
                text=f"{total} creation(s) loaded — click Check to compare"
            )
            return
        not_updated = sum(1 for r in self._rows if r.get("status") == STATUS_NOT_UPDATED)
        likely = sum(1 for r in self._rows if r.get("status") == STATUS_LIKELY_UPDATED)
        updated = sum(1 for r in self._rows if r.get("status") == STATUS_UPDATED)
        unknown = sum(1 for r in self._rows if r.get("status") == STATUS_UNKNOWN)
        skins = sum(1 for r in self._rows if r.get("status") == STATUS_SKIN)
        self._summary_label.configure(
            text=f"{total} total | {not_updated} not updated | "
                 f"{likely} likely updated | {updated} updated | "
                 f"{unknown} unknown | {skins} skins"
        )

    # ----- Row interaction: open details dialog -----

    def _on_tree_double_click(self, event):
        """Double-click anywhere on a row opens details (if info cached)."""
        item_id = self._tree.identify_row(event.y)
        if not item_id:
            return
        self._open_details_for_iid(item_id)

    def _on_tree_click(self, event):
        """Single-click on the info column opens details (if info cached).
        Other columns fall through to default selection behavior."""
        region = self._tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self._tree.identify_column(event.x)
        # Column "#2" is "info" (after "pos" which is "#1")
        if col != "#2":
            return
        item_id = self._tree.identify_row(event.y)
        if not item_id:
            return
        self._open_details_for_iid(item_id)
        # Prevent the click from also changing selection in an unexpected way
        return "break"

    def _open_details_for_iid(self, item_id: str):
        """Safeguarded open: skip silently if the row has no cached info."""
        try:
            idx = int(item_id)
        except ValueError:
            return
        if idx < 0 or idx >= len(self._rows):
            return
        row = self._rows[idx]
        info = row.get("info")
        if info is None:
            return  # safeguard — no cached info, nothing useful to show

        content_id = row.get("content_id", "")
        display_name = row.get("title", "") or "Creation"

        # Try to pull a thumbnail from the shared image cache; fall back to
        # a download if the URL is available.  Failure is non-fatal — the
        # dialog handles a missing thumbnail.
        thumb = None
        if info.thumbnail_url:
            from starfield_tool.dialogs.creation_details import (
                download_thumbnail,
            )
            try:
                thumb = download_thumbnail(
                    info.thumbnail_url, content_id=content_id,
                )
            except Exception:
                thumb = None

        from starfield_tool.dialogs.creation_details import (
            CreationDetailsDialog,
        )
        CreationDetailsDialog(
            self._tree, display_name, info, thumb,
            content_id=content_id,
        )

    # ----- Actions -----

    def _reset(self):
        self._rows = []
        self._checked = False
        self._source_mode = MODE_INSTALLED
        self._show_empty_state()

    def _import_installed(self):
        if not self._context or not self._context.game_installation:
            messagebox.showwarning(
                "No Game Installation",
                "Game installation is not configured.",
            )
            return
        try:
            from starfield_tool.parsers import build_creation_list
            creations = build_creation_list(self._context.game_installation)
        except Exception as exc:
            messagebox.showerror("Load Failed", f"Could not load installed creations:\n{exc}")
            return

        # Preserve the load order from build_creation_list. The returned list is
        # already sorted by load_position, so we use the list index (1-based) as
        # the display position — this matches what the Installed Creations tab
        # shows in its #-column.
        self._rows = [
            {
                "content_id": c.content_id,
                "title": c.display_name,
                "author": c.author or "",
                "installed_version": c.installed_version or "",
                "load_position": i + 1,
                "baseline_version": None,
                "current_version": None,
                "status": None,
            }
            for i, c in enumerate(creations)
        ]
        self._source_mode = MODE_INSTALLED
        self._checked = False
        self._show_loaded_state()

    def _import_snapshot(self):
        """Load a load-order snapshot saved from the Load Order tool.

        The saved installed_version is retained for reference only; the
        check itself always queries the API for each creation's current
        published version and compares that against the baseline.
        """
        path_str = filedialog.askopenfilename(
            title="Load Load-Order Snapshot",
            filetypes=[("JSON snapshots", "*.json")],
        )
        if not path_str:
            return

        from load_order_sorter import load_snapshot
        try:
            snapshot = load_snapshot(Path(path_str))
        except ValueError as exc:
            messagebox.showerror(
                "Invalid Snapshot",
                f"Could not load the snapshot:\n{exc}",
            )
            return

        if not snapshot.entries:
            messagebox.showwarning(
                "Empty Snapshot",
                "The snapshot contains no creations.",
            )
            return

        missing_versions = sum(
            1 for e in snapshot.entries if not e.installed_version
        )
        if missing_versions == len(snapshot.entries):
            messagebox.showwarning(
                "Old Snapshot Format",
                "This snapshot was saved before per-creation versions were "
                "tracked, so the check will not be able to compare versions. "
                "Re-save the snapshot from the Load Order tab to enable the check.",
            )

        self._rows = [
            {
                "content_id": e.content_id,
                "title": e.display_name,
                "author": "",  # snapshots don't carry author; lookup uses content_id
                "installed_version": e.installed_version or "",
                "load_position": i + 1,
                "baseline_version": None,
                "current_version": None,
                "status": None,
            }
            for i, e in enumerate(snapshot.entries)
        ]
        self._source_mode = MODE_FILE
        self._checked = False
        self._show_loaded_state()

    def _import_from_file(self):
        path_str = filedialog.askopenfilename(
            title="Select Exported Creation List",
            filetypes=[
                ("All supported", "*.csv *.txt"),
                ("CSV files", "*.csv"),
                ("Markdown exports", "*.txt"),
            ],
        )
        if not path_str:
            return

        path = Path(path_str)
        try:
            rows, is_legacy = _parse_export(path)
        except Exception as exc:
            messagebox.showerror(
                "Import Failed",
                f"Could not parse the file:\n{exc}",
            )
            return

        if not rows:
            messagebox.showwarning(
                "Empty File",
                "The file contains no creation entries.",
            )
            return

        self._rows = rows
        self._source_mode = MODE_FILE
        self._checked = False

        if is_legacy:
            messagebox.showwarning(
                "Legacy Export Format",
                "This export does not include Content IDs. Matching will "
                "use Name + Author as fallback, which is less reliable. "
                "For best results, re-export from the Installed Creations "
                "tab using the updated format.",
            )

        self._show_loaded_state()

    def _check(self):
        if not self._baseline:
            messagebox.showerror(
                "No Baseline",
                "The baseline file is not available. The check cannot run.",
            )
            return
        if not self._rows:
            return

        # Always compare API's current version against the baseline, in both
        # file and installed modes.  The tool's question is "has the author
        # updated this post-baseline?" — that's API-vs-baseline, not
        # what-happens-to-be-installed.  The exported installed_version is
        # retained as reference-only in the row data.
        if not self._context:
            return
        self._context.status_bar.set_task("Fast Lane Check: fetching current versions...")

        import threading

        def _run():
            try:
                from starfield_tool.creations import _make_client
                from bethesda_creations import ContentQuery

                client = _make_client(
                    self._context.status_bar,
                    self._context.app_start_time,
                    self._context.app_start_wall,
                )
                queries = [
                    ContentQuery(content_id=row["content_id"], display_name=row["title"])
                    for row in self._rows
                    if row.get("content_id")
                ]
                info_map = client.fetch_info(queries)
            except Exception as exc:
                log.warning("Failed to fetch current versions: %s", exc)
                info_map = {}

            # Schedule UI update on main thread
            if self._tree:
                self._tree.after(0, lambda: self._run_comparison(info_map))
            else:
                self._run_comparison(info_map)

        threading.Thread(target=_run, daemon=True).start()

    def _run_comparison(self, info_map: dict):
        """Apply the baseline comparison using a pre-fetched info_map.

        info_map is {content_id: CreationInfo} (populated from the API for
        installed mode, or empty for file mode).
        """
        if not self._baseline:
            return
        baseline_entries = self._baseline.get("entries", {})

        for row in self._rows:
            baseline_entry = _lookup_baseline(row, baseline_entries)
            if baseline_entry is None:
                row["baseline_version"] = None
                row["current_version"] = None
                row["status"] = STATUS_UNKNOWN
                continue

            baseline_version = baseline_entry.get("v", "")
            row["baseline_version"] = baseline_version

            # Current version always comes from the API — the tool's purpose
            # is "has the mod author published a post-baseline version?",
            # which only API-current-vs-baseline can answer.  The exported
            # installed_version (if any) stays on the row for display but
            # doesn't drive classification.
            info = info_map.get(row["content_id"])
            row["info"] = info  # stored for the details dialog
            current_version = info.version if info else None
            row["current_version"] = current_version
            # Record PS support for the PS-override below and for display.
            platforms = info.platforms if info else []
            row["platforms"] = platforms
            has_ps = any(p in _POST_FREE_LANES_PLATFORMS for p in platforms)
            row["has_ps_support"] = has_ps
            # Skins are excluded from the outdated check — they almost never
            # break across game updates. We still surface them with a low-key
            # marker so the user knows the row was recognised.
            if baseline_entry.get("s") == 1:
                row["status"] = STATUS_SKIN
            else:
                status = _classify(current_version, baseline_version)
                # PS support implies post-Free-Lanes republish.  If the
                # version still matches the baseline, the author republished
                # (for PS) without bumping the version — a stale-version
                # alert here would be a false positive.
                if status == STATUS_NOT_UPDATED and has_ps:
                    status = STATUS_LIKELY_UPDATED
                row["status"] = status

        # Preserve load order — do NOT sort. Rows stay in the order they were
        # loaded (installed: game's load order; file: export's row order).
        # Status is communicated via row highlighting, not reordering.
        self._checked = True
        self._populate_tree()
        self._update_summary()

        if self._context and self._source_mode == MODE_INSTALLED:
            self._context.status_bar.clear_task()
