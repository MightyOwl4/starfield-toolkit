"""Main application window with tabbed interface and status bar."""
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from starfield_tool.base import ModuleContext
from starfield_tool.config import load_config, save_config
from starfield_tool.models import GameInstallation
from starfield_tool.status_bar import StatusBar
from starfield_tool.tools import MODULES


def _icon_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS) / "assets"
    else:
        base = Path(__file__).parent.parent.parent / "assets"
    return base / "icon.ico"


CONSTELLATION_COLORS = ["#314c79", "#dba54b", "#e26137", "#c92337"]


def _create_constellation_stripe(parent, band_height: int = 4) -> tk.Frame:
    """Create the Constellation faction stripe as stacked Frame bands.

    band_height is the exact pixel height of each color band.
    Uses one Frame per color to avoid Canvas coordinate rounding
    issues with DPI scaling.
    """
    container = tk.Frame(parent, highlightthickness=0, bd=0)
    for color in CONSTELLATION_COLORS:
        band = tk.Frame(container, bg=color, height=band_height)
        band.pack(fill="x")
        band.pack_propagate(False)
    return container


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        from starfield_tool import __version__
        title = "Starfield Toolkit"
        if __version__ and __version__ != "dev":
            title += f" v{__version__}"
        self.title(title)

        # Restore window geometry or use default
        settings = load_config()
        if settings.window_geometry:
            self.geometry(settings.window_geometry)
        else:
            self.geometry("900x600")
        self.minsize(900, 0)

        icon = _icon_path()
        if icon.exists():
            self.iconbitmap(str(icon))

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._app_start_time = time.monotonic()
        self._app_start_wall = time.time()
        self._game_install: GameInstallation | None = None
        self._module_instances: list = []
        self._tab_frames: dict[str, ctk.CTkFrame] = {}

        # Theme colors
        is_dark = ctk.get_appearance_mode() == "Dark"
        self._active_fg = "#dcdcdc" if is_dark else "#111111"
        self._inactive_fg = "#777777" if is_dark else "#999999"
        self._border_color = CONSTELLATION_COLORS[0]  # blue
        self._inactive_border = "#444444" if is_dark else "#bbbbbb"
        self._bg_color = "#242424" if is_dark else "#ebebeb"
        self._active_tab_bg = CONSTELLATION_COLORS[0]  # blue

        # Status bar (pack first so it's at the very bottom)
        self._status_bar = StatusBar(self)
        self._status_bar.pack(fill="x", side="bottom", padx=0, pady=0)


        # Tab bar (plain tk.Frame to avoid CTk padding)
        self._tab_bar = tk.Frame(self, bg=self._bg_color, highlightthickness=0)
        self._tab_bar.pack(fill="x", side="top", padx=8, pady=(16, 0))

        # Leading spacer
        tk.Frame(self._tab_bar, width=8, bg=self._bg_color).pack(side="left")

        # Settings menu — right side of tab bar
        _dim_border = "#555555" if is_dark else "#aaaaaa"
        self._menu_btn = ctk.CTkButton(
            self._tab_bar,
            text="\u22ee",
            width=28, height=28,
            corner_radius=4,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffffff",
            fg_color=self._bg_color,
            hover_color=_dim_border,
            border_width=1,
            border_color=self._bg_color,
            command=lambda: self._show_settings_menu(None),
        )
        self._menu_btn.pack(side="right", padx=(0, 4))
        self._menu_btn.bind("<Button-1>", self._show_settings_menu)

        # Stripe between tab bar and content
        self._stripe_top = _create_constellation_stripe(self, band_height=5)
        self._stripe_top.pack(fill="x", side="top", padx=8, pady=0)

        self._tab_labels: dict[str, ctk.CTkLabel] = {}
        self._tab_wrappers: dict[str, tk.Frame] = {}
        self._content_container = tk.Frame(self, bg=self._bg_color, highlightthickness=0)
        self._content_container.pack(fill="both", expand=True, padx=0, pady=0)

        tab_names = [m.name for m in MODULES] or ["Welcome"]
        for tab_name in tab_names:
            # Wrapper frame provides the visible border
            wrapper = tk.Frame(
                self._tab_bar, bg=self._bg_color,
                highlightthickness=0, bd=0,
            )
            wrapper.pack(side="left", padx=(0, 4))

            label = tk.Label(
                wrapper,
                text=tab_name,
                font=("Segoe UI", 12, "bold"),
                bg=self._bg_color,
                padx=14, pady=6,
                cursor="hand2",
            )
            label.pack(padx=2, pady=(2, 0))  # border effect: top/left/right
            label.bind("<Button-1>", lambda e, n=tab_name: self._select_tab(n))
            wrapper.bind("<Button-1>", lambda e, n=tab_name: self._select_tab(n))
            label.bind("<Enter>", lambda e, n=tab_name: self._on_tab_hover(n, True))
            label.bind("<Leave>", lambda e, n=tab_name: self._on_tab_hover(n, False))

            self._tab_labels[tab_name] = label
            self._tab_wrappers[tab_name] = wrapper

            frame = ctk.CTkFrame(self._content_container, fg_color="transparent")
            frame.place(relwidth=1, relheight=1)
            self._tab_frames[tab_name] = frame

        self._active_tab: str | None = None
        if tab_names:
            self._select_tab(tab_names[0])

        # Run startup detection
        self.after(100, self._startup)

    def _on_tab_hover(self, tab_name: str, entering: bool):
        """Highlight inactive tab text on hover."""
        if tab_name == self._active_tab:
            return
        label = self._tab_labels[tab_name]
        label.configure(fg="#ffffff" if entering else self._inactive_fg)

    def _select_tab(self, tab_name: str):
        """Switch to the given tab."""
        for name, label in self._tab_labels.items():
            wrapper = self._tab_wrappers[name]
            if name == tab_name:
                label.configure(fg=self._active_fg, bg=self._active_tab_bg)
                wrapper.configure(bg=self._border_color)
                label.pack_configure(padx=2, pady=(2, 0))
            else:
                label.configure(fg=self._inactive_fg, bg=self._bg_color)
                wrapper.configure(bg=self._inactive_border)
                label.pack_configure(padx=1, pady=(1, 0))

        # Show/hide content frames
        for name, frame in self._tab_frames.items():
            if name == tab_name:
                frame.tkraise()

        self._active_tab = tab_name

    def _startup(self):
        """Startup flow: beta warning → config → auto-detect → dialog → skeleton."""
        settings = load_config()

        if not settings.beta_acknowledged:
            from tkinter import messagebox
            messagebox.showwarning(
                "Beta Software",
                "Starfield Toolkit is in early development and lightly tested.\n\n"
                "Please back up your Plugins.txt before making load order changes.\n\n"
                "Use at your own risk.",
            )
            settings.beta_acknowledged = True
            save_config(settings)

        self._status_bar.set_task("Checking configuration...")

        # Try persisted path first
        if settings.game_path:
            install = GameInstallation(
                game_root=Path(settings.game_path), source="persisted"
            )
            if install.is_valid:
                self._on_game_found(install)
                return

        # Try Steam auto-detection
        self._status_bar.set_task("Auto-detecting Starfield installation...")
        try:
            from starfield_tool.steam import auto_detect_starfield
            install = auto_detect_starfield()
            if install:
                self._on_game_found(install)
                return
        except Exception:
            pass

        # Show file browser dialog
        self._status_bar.set_task("Waiting for manual path selection...")
        path = filedialog.askdirectory(
            title="Select Starfield Installation Folder"
        )
        if path:
            install = GameInstallation(game_root=Path(path), source="manual")
            if install.is_valid:
                self._on_game_found(install)
                return

        # Nothing found — show skeleton with placeholders
        self._show_not_found_placeholders()
        self._status_bar.clear_task()

    def _on_game_found(self, install: GameInstallation):
        """Game path resolved — persist config and initialize modules."""
        self._game_install = install
        settings = load_config()
        settings.game_path = str(install.game_root)
        save_config(settings)
        self._status_bar.set_game_path(str(install.game_root))
        self._status_bar.set_task("Initializing modules...")
        self._initialize_modules()
        self._status_bar.clear_task()

    def _initialize_modules(self):
        """Initialize all registered tool modules with app context."""
        for module_cls in MODULES:
            tab_name = module_cls.name
            frame = self._tab_frames.get(tab_name)
            if not frame or not self._game_install:
                continue

            # Clear placeholder content
            for widget in frame.winfo_children():
                widget.destroy()

            # Description bar (rendered by skeleton, consistent across all tabs)
            if module_cls.description:
                ctk.CTkLabel(
                    frame, text=module_cls.description,
                    font=ctk.CTkFont(size=11), text_color="#888888",
                    anchor="e",
                ).pack(fill="x", padx=12, pady=(2, 0), anchor="e")

            # Module content area (below description)
            content = ctk.CTkFrame(frame, fg_color="transparent")
            content.pack(fill="both", expand=True, pady=0)

            module = module_cls()
            context = ModuleContext(
                game_installation=self._game_install,
                status_bar=self._status_bar,
                content_frame=content,
                app_start_time=self._app_start_time,
                app_start_wall=self._app_start_wall,
            )
            module.initialize(context)
            self._module_instances.append(module)

    def _show_not_found_placeholders(self):
        """Show 'Starfield not found' warning in each tab."""
        for tab_name, frame in self._tab_frames.items():
            for widget in frame.winfo_children():
                widget.destroy()
            self._create_not_found_content(frame)

        if not MODULES and "Welcome" in self._tab_frames:
            self._create_not_found_content(self._tab_frames["Welcome"])

    def _create_not_found_content(self, frame):
        """Create the 'not found' placeholder with action buttons."""
        container = ctk.CTkFrame(frame, fg_color="transparent")
        container.place(relx=0.5, rely=0.4, anchor="center")

        ctk.CTkLabel(
            container,
            text="Starfield Not Found",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=(0, 16))

        ctk.CTkLabel(
            container,
            text="Could not locate a Starfield installation.\n"
                 "Please browse to your install folder or try auto-detection.",
        ).pack(pady=(0, 24))

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(
            btn_frame, text="Browse...", command=self._browse_for_game
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame, text="Auto-Detect", command=self._retry_auto_detect
        ).pack(side="left", padx=8)

    def _browse_for_game(self):
        path = filedialog.askdirectory(
            title="Select Starfield Installation Folder"
        )
        if path:
            install = GameInstallation(game_root=Path(path), source="manual")
            if install.is_valid:
                self._on_game_found(install)

    def _retry_auto_detect(self):
        self._status_bar.set_task("Auto-detecting Starfield installation...")
        try:
            from starfield_tool.steam import auto_detect_starfield
            install = auto_detect_starfield()
            if install:
                self._on_game_found(install)
                return
        except Exception:
            pass
        self._status_bar.set_task("Auto-detection failed")
        self.after(3000, self._status_bar.clear_task)

    # --- Settings menu ---

    def _show_settings_menu(self, event=None):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Change game path...", command=self._settings_change_path)
        menu.add_command(label="Grid font size...", command=self._settings_grid_font_size)
        menu.add_command(label="Clear creations cache", command=self._settings_clear_cache)
        menu.add_command(label="Clear image cache", command=self._settings_clear_image_cache)
        menu.add_separator()
        dangerous_on = load_config().enable_dangerous_ops
        menu.add_checkbutton(
            label="Enable dangerous operations",
            command=self._settings_toggle_dangerous_ops,
            variable=tk.BooleanVar(value=dangerous_on),
        )
        menu.add_separator()
        menu.add_command(label="About", command=self._settings_about)
        # Position below the button
        x = self._menu_btn.winfo_rootx()
        y = self._menu_btn.winfo_rooty() + self._menu_btn.winfo_height()
        menu.tk_popup(x, y)

    def _settings_change_path(self):
        from tkinter import messagebox
        path = filedialog.askdirectory(
            title="Select Starfield installation folder",
        )
        if not path:
            return
        install = GameInstallation(game_root=Path(path), source="manual")
        if not install.is_valid:
            messagebox.showerror(
                "Invalid Path",
                f"{path} does not appear to be a valid Starfield installation.",
            )
            return
        settings = load_config()
        settings.game_path = str(install.game_root)
        save_config(settings)
        self._game_install = install
        self._status_bar.set_game_path(str(install.game_root))
        self._status_bar.set_task("Game path updated — restart to reload modules")
        self.after(3000, self._status_bar.clear_task)

    def _settings_toggle_dangerous_ops(self):
        settings = load_config()
        settings.enable_dangerous_ops = not settings.enable_dangerous_ops
        save_config(settings)
        state = "ON" if settings.enable_dangerous_ops else "OFF"
        self._status_bar.set_task(f"Dangerous operations: {state}")
        self.after(2000, self._status_bar.clear_task)

    def _settings_clear_cache(self):
        from starfield_tool.creations import clear_cache
        clear_cache()
        self._status_bar.set_task("Cache cleared")
        self.after(2000, self._status_bar.clear_task)

    def _settings_grid_font_size(self):
        """Prompt the user for a grid font size and save to config.

        Deferred via `after` so the popup menu fully dismisses (releases
        grab) before the modal dialog tries to take it — otherwise the
        dialog buttons are unresponsive and askinteger returns None.
        """
        self.after(50, self._grid_font_size_dialog)

    def _grid_font_size_dialog(self):
        """Custom CTkToplevel prompt — avoids tkinter.simpledialog which
        uses transient+grab and disappears on Win+D."""
        import customtkinter as ctk
        from starfield_tool.dialogs import center_dialog

        settings = load_config()
        current = settings.grid_font_size

        dlg = ctk.CTkToplevel(self)
        dlg.title("Grid font size")
        dlg.minsize(320, 160)
        center_dialog(dlg, 340, 170)
        # Regular taskbar window — survives Win+D
        dlg.attributes("-topmost", True)
        dlg.after(100, lambda: dlg.attributes("-topmost", False))

        icon = _icon_path()
        if icon.exists():
            dlg.after(200, lambda: dlg.iconbitmap(str(icon)))

        ctk.CTkLabel(
            dlg, text="Font size for all data grids (7–18):",
            font=ctk.CTkFont(size=12),
        ).pack(padx=16, pady=(16, 6), anchor="w")

        value_var = tk.StringVar(value=str(current))
        entry = ctk.CTkEntry(
            dlg, textvariable=value_var, width=80,
            font=ctk.CTkFont(size=12),
        )
        entry.pack(padx=16, pady=(0, 10), anchor="w")
        entry.focus_set()
        entry.select_range(0, "end")

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(padx=16, pady=(0, 14), fill="x")

        _btn_kw = dict(height=26, corner_radius=4,
                       font=ctk.CTkFont(size=12),
                       fg_color="#314c79", hover_color="#3d5f99")

        def _apply():
            from tkinter import messagebox
            raw = value_var.get().strip()
            try:
                new_size = int(raw)
            except ValueError:
                messagebox.showerror(
                    "Invalid value",
                    f"'{raw}' is not a number.",
                    parent=dlg,
                )
                return
            if not 7 <= new_size <= 18:
                messagebox.showerror(
                    "Out of range",
                    "Font size must be between 7 and 18.",
                    parent=dlg,
                )
                return
            if new_size != current:
                settings.grid_font_size = new_size
                save_config(settings)
                # Live refresh — re-apply font+rowheight across every
                # Treeview style used in the app.
                from starfield_tool.grid_style import refresh_all_grid_styles
                refresh_all_grid_styles()
                self._status_bar.set_task(
                    f"Grid font set to {new_size}pt")
                self.after(3000, self._status_bar.clear_task)
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        ctk.CTkButton(
            btn_row, text="OK", width=70, command=_apply, **_btn_kw,
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            btn_row, text="Cancel", width=70, command=_cancel, **_btn_kw,
        ).pack(side="right")

        dlg.bind("<Return>", lambda _e: _apply())
        dlg.bind("<Escape>", lambda _e: _cancel())
        dlg.protocol("WM_DELETE_WINDOW", _cancel)

    def _settings_clear_image_cache(self):
        from starfield_tool.dialogs.image_cache import clear_image_cache
        clear_image_cache()
        # Also clear in-memory thumbnail caches in modules
        for module in self._module_instances:
            if hasattr(module, "_thumbnail_cache"):
                module._thumbnail_cache.clear()
        self._status_bar.set_task("Image cache cleared")
        self.after(2000, self._status_bar.clear_task)

    def _settings_about(self):
        from tkinter import messagebox
        from starfield_tool import __version__
        ver = __version__ if __version__ else "development version"
        messagebox.showinfo(
            "About Starfield Toolkit",
            f"Starfield Toolkit — {ver}\n\n"
            "https://github.com/MightyOwl4/starfield-toolkit\n\n"
            "A lightweight tool for managing Bethesda Creations\n"
            "in Starfield — load order, updates, and achievements.\n\n"
            "This is an unofficial, community-built tool. It is not\n"
            "affiliated with, endorsed by, or sponsored by Bethesda\n"
            "Softworks, ZeniMax Media, or Microsoft. \"Starfield\" and\n"
            "\"Bethesda\" are trademarks of their respective owners.",
        )

    def _on_close(self):
        """Save window geometry and close."""
        settings = load_config()
        settings.window_geometry = self.geometry()
        save_config(settings)
        self.destroy()
