from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

from starfield_tool.models import GameInstallation


class StatusBarAPI(Protocol):
    def set_task(self, message: str) -> None: ...
    def clear_task(self) -> None: ...


@dataclass
class ModuleContext:
    game_installation: GameInstallation
    status_bar: StatusBarAPI
    content_frame: object  # customtkinter frame, kept generic for testability
    app_start_time: float = 0.0  # time.monotonic() at app startup


class ToolModule(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def initialize(self, context: ModuleContext) -> None: ...
