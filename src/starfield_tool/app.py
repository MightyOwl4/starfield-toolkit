"""Main application window with tabbed interface and status bar."""
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from starfield_tool.base import ModuleContext
from starfield_tool.config import load_config, save_config, AppSettings
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


def _create_constellation_stripe(parent, height: int = 4) -> tk.Canvas:
    """Create the Constellation faction stripe as a thin canvas bar."""
    canvas = tk.Canvas(
        parent, height=height, highlightthickness=0, bd=0,
    )
    colors = CONSTELLATION_COLORS
    band_count = len(colors)

    def _draw(event=None):
        canvas.delete("all")
        w = canvas.winfo_width() or 1
        band_h = height / band_count
        for i, color in enumerate(colors):
            y0 = i * band_h
            canvas.create_rectangle(0, y0, w, y0 + band_h + 1, fill=color, outline="")

    canvas.bind("<Configure>", _draw)
    return canvas


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

        # Stripe between tab bar and content
        self._stripe_top = _create_constellation_stripe(self, height=20)
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
        """Startup flow: config → auto-detect → dialog → skeleton."""
        self._status_bar.set_task("Checking configuration...")
        settings = load_config()

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
        save_config(AppSettings(game_path=str(install.game_root)))
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

    def _on_close(self):
        """Save window geometry and close."""
        settings = load_config()
        settings.window_geometry = self.geometry()
        save_config(settings)
        self.destroy()
