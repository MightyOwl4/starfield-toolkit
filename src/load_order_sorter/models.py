"""Data models for load order sorting."""
from dataclasses import dataclass, field


@dataclass
class SortItem:
    """Input to the sorting pipeline — one per creation."""
    plugin_name: str
    content_id: str
    display_name: str
    categories: list[str] = field(default_factory=list)
    author: str = ""
    original_index: int = 0


@dataclass
class SortConstraint:
    """A single sorting rule produced by a sorter."""
    plugin_name: str
    type: str  # "tier", "load_after", "pin"
    tier: int | None = None  # 1-11, for type="tier"
    after: str | None = None  # plugin that must load first, for type="load_after"
    sorter_name: str = ""
    priority: int = 0  # higher = wins on conflict
    warnings: list[str] = field(default_factory=list)


@dataclass
class SortDecision:
    """The winning constraint(s) for a single item after merge."""
    tier: int = 9  # default tier
    sorter_name: str = ""
    load_after: list[str] = field(default_factory=list)
    load_after_sorters: dict[str, str] = field(default_factory=dict)  # dep → sorter name
    warnings: list[str] = field(default_factory=list)


@dataclass
class SortedItem:
    """A single item in the proposed sort result."""
    plugin_name: str
    content_id: str
    display_name: str
    original_index: int
    new_index: int = 0
    moved: bool = False
    decision: SortDecision | None = None


@dataclass
class SortResult:
    """Output of the sorting pipeline."""
    items: list[SortedItem] = field(default_factory=list)
    unchanged: bool = True


@dataclass
class SnapshotEntry:
    """A single creation in a snapshot."""
    content_id: str
    display_name: str
    files: list[str] = field(default_factory=list)


@dataclass
class Snapshot:
    """Saved load order for export/import."""
    name: str = ""
    created: str = ""
    tool_version: str = ""
    entries: list[SnapshotEntry] = field(default_factory=list)
