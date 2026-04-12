"""Reusable dialog for displaying full creation details from cache."""
from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from PIL import Image as PILImage
    from bethesda_creations.models import CreationInfo


_THUMB_SIZE = (320, 180)
_DIALOG_WIDTH = 720
_DIALOG_HEIGHT = 600


def download_thumbnail(
    url: str,
    size: tuple[int, int] = _THUMB_SIZE,
    content_id: str = "",
) -> "PILImage.Image | None":
    """Return a thumbnail image, using disk cache when available.

    Returns ``None`` on any failure (network, decode, etc.).
    """
    from starfield_tool.dialogs.image_cache import get_cached_image, download_and_cache
    if content_id:
        cached = get_cached_image(content_id, url, size)
        if cached is not None:
            return cached
        return download_and_cache(content_id, url, size)
    return download_and_cache("_tmp", url, size)


class CreationDetailsDialog(ctk.CTkToplevel):
    """Non-modal dialog showing full cached details for a single creation.

    Follows the same windowing pattern as ``DiffDialog`` so it appears
    in the OS task-switcher (Alt+Tab) and does not trap focus.
    """

    def __init__(
        self,
        parent,
        display_name: str,
        info: "CreationInfo | None",
        thumbnail_image: "PILImage.Image | None" = None,
        content_id: str = "",
    ):
        super().__init__(parent)
        self.title(f"Details — {display_name}")
        self.minsize(400, 400)

        from starfield_tool.dialogs import center_dialog
        center_dialog(self, _DIALOG_WIDTH, _DIALOG_HEIGHT)

        # DiffDialog windowing pattern — no grab_set / transient
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        from starfield_tool.app import _icon_path
        icon = _icon_path()
        if icon.exists():
            self.after(200, lambda: self.iconbitmap(str(icon)))

        self._content_id = content_id
        self._build_ui(display_name, info, thumbnail_image)

        self.bind("<Escape>", lambda _e: self.destroy())

    @staticmethod
    def _bethesda_url(content_id: str, display_name: str) -> str | None:
        """Build the Bethesda Creations page URL for this creation.

        Format: https://creations.bethesda.net/en/starfield/details/{uuid}/{slug}
        Returns None if content_id is missing or not a valid UUID-like id.
        """
        if not content_id:
            return None
        uuid = content_id[3:] if content_id.startswith("TM_") else content_id
        # Slug: replace non-alphanumeric with underscore, collapse runs
        import re
        slug = re.sub(r"[^A-Za-z0-9]+", "_", display_name or "").strip("_")
        if not slug:
            slug = "creation"
        return (
            f"https://creations.bethesda.net/en/starfield/details/"
            f"{uuid}/{slug}"
        )

    # ------------------------------------------------------------------
    def _build_ui(
        self,
        display_name: str,
        info: "CreationInfo | None",
        thumbnail_image: "PILImage.Image | None",
    ) -> None:
        import html as _html

        # Pack button first so it keeps its space when window shrinks
        ctk.CTkButton(
            self, text="Close", width=80, command=self.destroy,
        ).pack(side="bottom", pady=(4, 10))

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        # === Two-column top: left (thumbnail), right (title + attributes) ===
        top = ctk.CTkFrame(container, fg_color="transparent")
        top.pack(fill="x", pady=(0, 10))

        # Left column: thumbnail only
        if thumbnail_image is not None:
            # CTkImage handles display scaling; no PIL resize needed
            thumb_ctk = ctk.CTkImage(
                light_image=thumbnail_image, dark_image=thumbnail_image,
                size=_THUMB_SIZE,
            )
            ctk.CTkLabel(
                top, image=thumb_ctk, text="",
            ).pack(side="left", anchor="n", padx=(0, 14))

        # Right column: title at top, then attributes below
        right_col = ctk.CTkFrame(top, fg_color="transparent")
        right_col.pack(side="left", fill="both", expand=True, anchor="n")

        ctk.CTkLabel(
            right_col,
            text=display_name,
            font=ctk.CTkFont(size=16, weight="bold"),
            wraplength=350,
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(0, 2))

        # Link to Bethesda's Creation page (when we have a content_id)
        url = self._bethesda_url(self._content_id, display_name)
        if url:
            link = ctk.CTkLabel(
                right_col,
                text="\u2197 View on creations.bethesda.net",
                font=ctk.CTkFont(size=11, underline=True),
                text_color="#7aaaff",
                cursor="hand2",
                anchor="w",
            )
            link.pack(anchor="w", pady=(0, 8))

            def _open(_event=None, u=url):
                import webbrowser
                webbrowser.open(u)

            link.bind("<Button-1>", _open)

        # Attributes as a monospace-aligned table
        def _val(value, fallback="n/a"):
            if value is None or value == "":
                return fallback
            return str(value)

        if info is not None:
            price_text = "Free" if info.price == 0 else f"{info.price} Credits"
            achiev_text = "Yes" if info.achievement_friendly else "No"
            rows = [
                ("Author", _val(info.author)),
                ("Version", _val(info.version)),
                ("Price", price_text),
                ("Size", _val(info.installation_size)),
                ("Created", _val(info.created_on)),
                ("Updated", _val(info.last_updated)),
                ("Achievements", achiev_text),
            ]
        else:
            rows = [(k, "n/a") for k in
                    ("Author", "Version", "Price", "Size",
                     "Created", "Updated", "Achievements")]

        key_w = max(len(r[0]) for r in rows)
        table_lines = []
        for key, val in rows:
            table_lines.append(f"{key.rjust(key_w)}   {val}")
        table_text = "\n".join(table_lines)

        table_box = ctk.CTkTextbox(
            right_col, wrap="none",
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="transparent", border_width=0, border_spacing=0,
            activate_scrollbars=False,
            height=len(rows) * 22,
        )
        table_box._textbox.configure(pady=0)
        table_box.insert("1.0", table_text)
        table_box.configure(state="disabled")
        table_box.pack(anchor="w", fill="x")

        # === Category pills (full width, above description) ===
        cats = info.categories if info and info.categories else []
        if cats:
            is_dark = ctk.get_appearance_mode() == "Dark"
            pill_border = "#666666" if is_dark else "#aaaaaa"
            pill_fg = "#2b2b2b" if is_dark else "#f5f5f5"
            pill_frame = ctk.CTkFrame(container, fg_color="transparent")
            pill_frame.pack(fill="x", pady=(0, 8))
            for cat in cats:
                ctk.CTkButton(
                    pill_frame,
                    text=cat,
                    font=ctk.CTkFont(size=11),
                    corner_radius=10,
                    fg_color=pill_fg,
                    hover_color=pill_fg,
                    border_width=1,
                    border_color=pill_border,
                    text_color="#dcdcdc" if is_dark else "#333333",
                    height=24,
                    state="disabled",
                ).pack(side="left", padx=(0, 6))

        # === Full-width description ===
        desc = _html.unescape(info.description) if info and info.description else None
        if desc:
            desc_box = ctk.CTkTextbox(
                container, wrap="word", activate_scrollbars=True,
            )
            desc_box.insert("1.0", desc)
            desc_box.configure(state="disabled")
            desc_box.pack(fill="both", expand=True, pady=(0, 0))

            # Scroll the textbox but block propagation to parent window
            inner = desc_box._textbox
            def _on_mousewheel(event):
                inner.yview_scroll(int(-1 * (event.delta / 120)), "units")
                return "break"
            inner.bind("<MouseWheel>", _on_mousewheel)

