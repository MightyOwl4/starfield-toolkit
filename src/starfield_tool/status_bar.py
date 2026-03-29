"""Status bar widget and headless API implementation."""
import customtkinter as ctk


class StatusBarImpl:
    """Headless status bar state, usable without GUI for testing."""

    def __init__(self):
        self.current_path: str = "Starfield path not set"
        self.current_task: str = "Ready"

    def set_task(self, message: str) -> None:
        self.current_task = message

    def clear_task(self) -> None:
        self.current_task = "Ready"

    def set_game_path(self, path: str) -> None:
        self.current_path = path


class StatusBar(ctk.CTkFrame):
    """GUI status bar with two segments: game path and current task."""

    def __init__(self, master, **kwargs):
        super().__init__(master, height=28, **kwargs)
        self._impl = StatusBarImpl()

        self._path_label = ctk.CTkLabel(
            self, text=self._impl.current_path, anchor="w",
        )
        self._path_label.pack(side="left", padx=(8, 16))

        self._separator = ctk.CTkLabel(self, text="|", width=10)
        self._separator.pack(side="left")

        self._task_label = ctk.CTkLabel(
            self, text=self._impl.current_task, anchor="w",
        )
        self._task_label.pack(side="left", padx=(16, 8), fill="x", expand=True)

        self.pack_propagate(False)

    def set_task(self, message: str) -> None:
        self._impl.set_task(message)
        self._task_label.configure(text=message)

    def clear_task(self) -> None:
        self._impl.clear_task()
        self._task_label.configure(text="Ready")

    def set_game_path(self, path: str) -> None:
        self._impl.set_game_path(path)
        self._path_label.configure(text=path)

    @property
    def current_task(self) -> str:
        return self._impl.current_task

    @property
    def current_path(self) -> str:
        return self._impl.current_path
