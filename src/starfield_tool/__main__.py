import sys


def main():
    # Set Windows AppUserModelID for proper taskbar grouping
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "starfield.toolkit"
        )

    from starfield_tool.app import App
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
