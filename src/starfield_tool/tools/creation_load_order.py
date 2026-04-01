"""Creation Load Order tool — displays Bethesda store Creations in load order."""
import threading
import tkinter as tk
from tkinter import filedialog, ttk
from pathlib import Path

import customtkinter as ctk

from bethesda_creations.models import CreationInfo
from starfield_tool.base import ToolModule, ModuleContext
from starfield_tool.models import Creation
from starfield_tool.parsers import build_creation_list

import html as _html


def _decode_html(text: str) -> str:
    """Decode HTML entities like ``&#39;`` → ``'``."""
    return _html.unescape(text)


def _truncate_at_word(text: str, limit: int) -> str:
    """Truncate *text* at a word boundary near *limit* chars, adding ellipsis."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "..."


_GRID_MODE_LIST = "list"
_GRID_MODE_MEDIA = "media"
_ROW_HEIGHT = 110
_ROW_CORNER = 8
_THUMB_HEIGHT = _ROW_HEIGHT
_THUMB_WIDTH = int(_THUMB_HEIGHT * 16 / 9)  # 16:9 aspect
_THUMB_ROW_SIZE = (_THUMB_WIDTH, _THUMB_HEIGHT)


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
        self._cached_info: dict[str, CreationInfo] = {}
        self._grid_mode: str = _GRID_MODE_LIST
        self._media_frame: ctk.CTkScrollableFrame | None = None
        self._media_rows: list[ctk.CTkFrame] = []
        self._thumbnail_cache: dict[str, ctk.CTkImage] = {}
        self._tree_frame: tk.Frame | None = None
        self._mode_toggle: ctk.CTkSegmentedButton | None = None
        self._fetching_cache: bool = False

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

        self._details_btn = ctk.CTkButton(
            top, text="Details", width=60, command=self._show_details, **_btn_kw,
        )
        self._details_btn.pack(side="left", padx=(0, 6))

        self._update_summary = ctk.CTkLabel(top, text="")
        self._update_summary.pack(side="left", padx=8)

        self._achiev_summary = ctk.CTkLabel(top, text="")
        self._achiev_summary.pack(side="left", padx=8)

        self._mode_toggle = ctk.CTkSegmentedButton(
            top, values=["List", "Media"],
            command=self._on_mode_toggle,
            width=120,
        )
        self._mode_toggle.set("List")
        self._mode_toggle.pack(side="right", padx=8)

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
        self._tree_frame = tk.Frame(frame, bg=bg, highlightthickness=0)
        self._tree_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))

        columns = ("#", "Name", "Author", "Version", "Date")
        self._tree = ttk.Treeview(
            self._tree_frame, columns=columns, show="headings", selectmode="browse"
        )
        self._tree.heading("#", text="#", anchor="center")
        self._tree.heading("Name", text="Name", anchor="w")
        self._tree.heading("Author", text="Author", anchor="w")
        self._tree.heading("Version", text="Version", anchor="w")
        self._tree.heading("Date", text="Date", anchor="w")

        self._tree.column("#", width=40, anchor="center", stretch=False)
        self._tree.column("Name", width=380, anchor="w")
        self._tree.column("Author", width=120, anchor="w", stretch=False)
        self._tree.column("Version", width=100, anchor="w", stretch=False)
        self._tree.column("Date", width=120, anchor="w", stretch=False)

        scrollbar = ttk.Scrollbar(
            self._tree_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=scrollbar.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Rich media scrollable frame (hidden initially)
        self._media_frame = ctk.CTkScrollableFrame(
            frame, fg_color="transparent",
        )

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
        # Restore cached check state if within session window
        self._restore_cached_state()
        self._populate_tree()
        self._context.status_bar.clear_task()

    def _restore_cached_state(self):
        """Reapply cached check results to the current creation list."""
        from starfield_tool.creations import get_cached_info
        from bethesda_creations._version_cmp import compare_versions

        cached = get_cached_info(self._context.app_start_time)
        if not cached:
            self._checked = False
            self._achievements_checked = False
            if self._update_summary:
                self._update_summary.configure(text="")
            if self._achiev_summary:
                self._achiev_summary.configure(text="")
            return

        for creation in self._creations:
            info = cached.get(creation.content_id)
            if not info:
                continue
            if info.version:
                creation.available_version = info.version
                creation.has_update = compare_versions(
                    creation.installed_version, info.version
                )
            if info.achievement_friendly is not None:
                creation.achievement_friendly = info.achievement_friendly

    def _on_refresh_error(self, message):
        self._show_error(message)
        self._context.status_bar.clear_task()

        self._context.status_bar.clear_task()

    def _populate_tree(self):
        if not self._tree:
            return

        # Load cached info (stale OK — author is immutable)
        from starfield_tool.creations import get_cached_info_any
        self._cached_info = get_cached_info_any()

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

            info = self._cached_info.get(creation.content_id)
            author_text = info.author if info and info.author else "n/a"

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
                values=(pos, creation.display_name, author_text, version_text, date_text),
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
                from starfield_tool.creations import check_for_updates
                updated = check_for_updates(
                    self._creations, self._context.status_bar,
                    self._context.app_start_time,
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
                from starfield_tool.creations import check_achievements
                updated = check_achievements(
                    self._creations, self._context.status_bar,
                    self._context.app_start_time,
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

    # -- Details dialog ------------------------------------------------

    def _show_details(self):
        """Open the details dialog for the currently selected creation."""
        creation = self._get_selected_creation()
        if not creation:
            return
        info = self._cached_info.get(creation.content_id)
        thumb = None
        if info and info.thumbnail_url:
            ctk_img = self._thumbnail_cache.get(creation.content_id)
            if ctk_img is not None:
                thumb = ctk_img._light_image
            else:
                from starfield_tool.dialogs.creation_details import download_thumbnail
                thumb = download_thumbnail(
                    info.thumbnail_url, content_id=creation.content_id,
                )
        from starfield_tool.dialogs.creation_details import CreationDetailsDialog
        CreationDetailsDialog(self._tree, creation.display_name, info, thumb)

    def _get_selected_creation(self) -> Creation | None:
        """Return the creation currently selected in the active grid mode."""
        if self._grid_mode == _GRID_MODE_LIST and self._tree:
            sel = self._tree.selection()
            if not sel:
                return None
            idx = self._tree.index(sel[0])
            if 0 <= idx < len(self._creations):
                return self._creations[idx]
        elif self._grid_mode == _GRID_MODE_MEDIA:
            # In media mode, selection is not tracked via treeview.
            # The Details button on each row passes the creation directly.
            return None
        return None

    # -- Mode toggle ---------------------------------------------------

    def _on_mode_toggle(self, value: str):
        if value == "List" and self._grid_mode != _GRID_MODE_LIST:
            self._grid_mode = _GRID_MODE_LIST
            self._show_list_mode()
        elif value == "Media" and self._grid_mode != _GRID_MODE_MEDIA:
            self._grid_mode = _GRID_MODE_MEDIA
            self._show_media_mode()

    def _show_list_mode(self):
        if self._media_frame:
            self._media_frame.pack_forget()
        if self._tree_frame:
            self._tree_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self._populate_tree()

    def _show_media_mode(self):
        if self._tree_frame:
            self._tree_frame.pack_forget()
        if self._media_frame:
            self._media_frame.pack(fill="both", expand=True, padx=8, pady=(4, 8))
        self._populate_media()

    # -- Rich media mode -----------------------------------------------

    def _populate_media(self):
        """Build or rebuild the rich media grid rows."""
        if not self._media_frame:
            return

        # Clear existing rows
        for row in self._media_rows:
            row.destroy()
        self._media_rows.clear()

        if not self._creations:
            lbl = ctk.CTkLabel(self._media_frame, text="No Creations found")
            lbl.pack(pady=20)
            self._media_rows.append(lbl)
            return

        # Load cached info
        from starfield_tool.creations import get_cached_info_any
        self._cached_info = get_cached_info_any()

        has_any_cache = bool(self._cached_info)

        if not has_any_cache and not self._fetching_cache:
            # Cache is cold — show placeholders and trigger fetch
            self._render_media_placeholders()
            self._trigger_cache_fetch()
            return

        self._render_media_rows()

    def _render_media_placeholders(self):
        """Show loading placeholders for each creation in media mode."""
        for creation in self._creations:
            row = self._build_media_row(
                creation,
                info=None,
                is_placeholder=True,
            )
            row.pack(fill="x", padx=4, pady=2)
            self._media_rows.append(row)

    def _render_media_rows(self):
        """Render fully populated media rows with cached data."""
        for creation in self._creations:
            info = self._cached_info.get(creation.content_id)
            row = self._build_media_row(creation, info, is_placeholder=False)
            row.pack(fill="x", padx=4, pady=2)
            self._media_rows.append(row)

        # Start downloading thumbnails in background
        self._download_thumbnails()

    def _build_media_row(
        self,
        creation: Creation,
        info: CreationInfo | None,
        is_placeholder: bool,
    ) -> ctk.CTkFrame:
        """Build a single rich media row widget."""
        is_dark = ctk.get_appearance_mode() == "Dark"
        row_bg = "#333333" if is_dark else "#f0f0f0"

        row = ctk.CTkFrame(
            self._media_frame, height=_ROW_HEIGHT,
            fg_color=row_bg, corner_radius=_ROW_CORNER,
        )
        row.pack_propagate(False)

        # Thumbnail — flush left, full row height, no rounding
        cached_ctk = self._thumbnail_cache.get(creation.content_id)
        if cached_ctk is not None:
            thumb_label = ctk.CTkLabel(
                row, text="", image=cached_ctk,
                width=_THUMB_WIDTH, height=_THUMB_HEIGHT,
                fg_color="transparent", corner_radius=0,
            )
        else:
            thumb_label = ctk.CTkLabel(
                row, text="", width=_THUMB_WIDTH, height=_THUMB_HEIGHT,
                fg_color="#555555" if is_dark else "#cccccc",
                corner_radius=0,
            )
        thumb_label.pack(side="left", padx=(0, 8), pady=0)
        thumb_label._creation_cid = creation.content_id

        # Text block: name (bold, larger) + description — selectable, wrapping
        text_block = ctk.CTkFrame(row, fg_color="transparent")
        text_block.pack(side="left", fill="both", expand=True, pady=4)

        pos = str(creation.load_position + 1) if creation.load_position is not None else "-"

        if is_placeholder:
            name_text = f"#{pos} — Loading..."
            desc_text = ""
        else:
            title = info.title if info and info.title else creation.display_name
            name_text = f"#{pos} — {_decode_html(title)}"
            desc_text = ""
            if info and info.description:
                desc_text = _truncate_at_word(
                    _decode_html(info.description).replace("\n", " ").replace("\r", ""),
                    350,
                )

        title_box = ctk.CTkTextbox(
            text_block, height=30, wrap="word",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="transparent", border_width=0, border_spacing=0,
            activate_scrollbars=False,
        )
        title_box._textbox.configure(pady=0)
        title_box.insert("1.0", name_text)
        title_box.configure(state="disabled")
        title_box.pack(fill="x")

        if desc_text:
            dim_color = "#aaaaaa" if is_dark else "#666666"
            desc_box = ctk.CTkTextbox(
                text_block, wrap="word",
                font=ctk.CTkFont(size=12),
                text_color=dim_color,
                fg_color="transparent", border_width=0, border_spacing=0,
                activate_scrollbars=False,
            )
            desc_box._textbox.configure(spacing1=3, spacing2=3, spacing3=3, pady=0)
            desc_box.insert("1.0", desc_text)
            desc_box.configure(state="disabled")
            desc_box.pack(fill="both", expand=True)

        # Right-side: author, version/date, details button stacked
        info_frame = ctk.CTkFrame(row, fg_color="transparent")
        info_frame.pack(side="right", pady=8, padx=(0, 10))

        small_font = ctk.CTkFont(size=11)
        author = info.author if info and info.author else "n/a"
        version = creation.installed_version
        date = creation.timestamp.strftime("%d %b %Y") if creation.timestamp else ""

        ctk.CTkLabel(
            info_frame, text=author, font=small_font, anchor="e",
        ).pack(anchor="e", pady=0)

        version_line = f"v{version}" + (f"  •  {date}" if date else "")
        ctk.CTkLabel(
            info_frame, text=version_line, font=small_font, anchor="e",
        ).pack(anchor="e", pady=0)

        _btn_color = "#314c79"
        _btn_hover = "#3d5f99"
        ctk.CTkButton(
            info_frame, text="Details", width=60, height=26,
            corner_radius=4, font=ctk.CTkFont(size=11),
            fg_color=_btn_color, hover_color=_btn_hover,
            command=lambda c=creation: self._show_details_for(c),
        ).pack(anchor="e", pady=(6, 0))

        return row

    def _show_details_for(self, creation: Creation):
        """Open details dialog for a specific creation (used by media rows)."""
        info = self._cached_info.get(creation.content_id)
        thumb = None
        ctk_img = self._thumbnail_cache.get(creation.content_id)
        if ctk_img is not None:
            thumb = ctk_img._light_image
        elif info and info.thumbnail_url:
            from starfield_tool.dialogs.creation_details import download_thumbnail
            thumb = download_thumbnail(
                info.thumbnail_url, content_id=creation.content_id,
            )
        from starfield_tool.dialogs.creation_details import CreationDetailsDialog
        CreationDetailsDialog(
            self._media_frame, creation.display_name, info, thumb,
        )

    def _download_thumbnails(self):
        """Download thumbnails for all visible media rows in a background thread.

        On failure the remaining items are retried after a cooldown that
        doubles with each consecutive error (1 s → 2 s → 4 s, capped at
        30 s).  A single success resets the cooldown.  Gives up after 3
        full passes with zero progress.
        """
        to_download = []
        for creation in self._creations:
            if creation.content_id in self._thumbnail_cache:
                continue
            info = self._cached_info.get(creation.content_id)
            if info and info.thumbnail_url:
                to_download.append((creation.content_id, info.thumbnail_url))

        if not to_download:
            return

        def _run():
            import time as _time
            from starfield_tool.dialogs.creation_details import download_thumbnail

            pending = list(to_download)
            cooldown = 1.0
            max_cooldown = 30.0
            stale_passes = 0

            while pending:
                failed: list[tuple[str, str]] = []
                made_progress = False

                for cid, url in pending:
                    if not (self._media_frame and self._media_frame.winfo_exists()):
                        return  # widget gone, abort
                    if cid in self._thumbnail_cache:
                        continue  # filled by another path

                    pil_img = download_thumbnail(url, _THUMB_ROW_SIZE, content_id=cid)
                    if pil_img:
                        made_progress = True
                        cooldown = 1.0  # reset on success
                        self._media_frame.after(
                            0, lambda c=cid, img=pil_img: self._apply_thumbnail(c, img),
                        )
                    else:
                        failed.append((cid, url))
                        # Pause before next attempt so the CDN can recover
                        _time.sleep(cooldown)
                        cooldown = min(cooldown * 2, max_cooldown)

                if not failed:
                    break

                if made_progress:
                    stale_passes = 0
                else:
                    stale_passes += 1
                    if stale_passes >= 3:
                        break  # no progress in 3 full passes, give up

                pending = failed

        threading.Thread(target=_run, daemon=True).start()

    def _apply_thumbnail(self, content_id: str, pil_img):
        """Apply a downloaded thumbnail to the corresponding media row."""
        ctk_img = ctk.CTkImage(
            light_image=pil_img, dark_image=pil_img,
            size=_THUMB_ROW_SIZE,
        )
        self._thumbnail_cache[content_id] = ctk_img

        # Find the row's thumbnail label and update it
        for row in self._media_rows:
            if not row.winfo_exists():
                continue
            for child in row.winfo_children():
                if (
                    isinstance(child, ctk.CTkLabel)
                    and hasattr(child, "_creation_cid")
                    and child._creation_cid == content_id
                ):
                    child.configure(image=ctk_img, fg_color="transparent")
                    return

    def _trigger_cache_fetch(self):
        """Fetch cache data in a background thread, then re-render media rows."""
        if self._fetching_cache:
            return
        self._fetching_cache = True
        self._context.status_bar.set_task("Fetching creation info...")

        def _run():
            try:
                from starfield_tool.creations import check_for_updates
                check_for_updates(
                    self._creations, self._context.status_bar,
                    self._context.app_start_time,
                )
                if self._media_frame and self._media_frame.winfo_exists():
                    self._media_frame.after(0, self._on_cache_fetch_complete)
            except Exception:
                if self._media_frame and self._media_frame.winfo_exists():
                    self._media_frame.after(0, self._on_cache_fetch_failed)

        threading.Thread(target=_run, daemon=True).start()

    def _on_cache_fetch_complete(self):
        self._fetching_cache = False
        self._context.status_bar.clear_task()
        if self._grid_mode == _GRID_MODE_MEDIA:
            # Clear and re-render with real data
            for row in self._media_rows:
                row.destroy()
            self._media_rows.clear()
            from starfield_tool.creations import get_cached_info_any
            self._cached_info = get_cached_info_any()
            self._render_media_rows()

    def _on_cache_fetch_failed(self):
        self._fetching_cache = False
        self._context.status_bar.clear_task()

    def on_cache_cleared(self):
        """React to cache being cleared — reset media mode if active."""
        self._cached_info.clear()
        self._thumbnail_cache.clear()
        if self._grid_mode == _GRID_MODE_MEDIA:
            for row in self._media_rows:
                row.destroy()
            self._media_rows.clear()
            self._render_media_placeholders()
            self._trigger_cache_fetch()
        elif self._grid_mode == _GRID_MODE_LIST:
            self._populate_tree()

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
