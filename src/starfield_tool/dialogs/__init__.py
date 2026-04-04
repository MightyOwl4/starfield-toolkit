"""Shared dialog utilities."""


def center_dialog(dialog, width: int, height: int) -> None:
    """Position *dialog* centered horizontally on the app window,
    vertically at the top 1/4 of the app window.

    Falls back to screen center if the parent window geometry
    cannot be determined.
    """
    try:
        root = dialog.winfo_toplevel()
        # Walk up to the actual app window (CTk root)
        parent = dialog.master
        while parent and not hasattr(parent, "winfo_rootx"):
            parent = getattr(parent, "master", None)
        if parent is None:
            parent = root

        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()

        # Center horizontally on the parent
        x = px + (pw - width) // 2
        # Place dialog center at the top 1/4 of the parent
        y = py + ph // 4 - height // 2

        # Clamp to screen bounds
        sw = dialog.winfo_screenwidth()
        sh = dialog.winfo_screenheight()
        x = max(0, min(x, sw - width))
        y = max(0, min(y, sh - height))

        dialog.geometry(f"{width}x{height}+{x}+{y}")
    except Exception:
        dialog.geometry(f"{width}x{height}")
