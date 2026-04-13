"""Data models for Bethesda Creations API responses."""
from dataclasses import dataclass, field


@dataclass
class CreationInfo:
    """Metadata for a single Bethesda Creation."""
    title: str | None = None
    description: str | None = None
    version: str | None = None
    author: str | None = None
    price: int = 0  # 0 = free, >0 = Creations credits
    installation_size: str | None = None
    last_updated: str | None = None
    created_on: str | None = None
    categories: list[str] = field(default_factory=list)
    achievement_friendly: bool = False
    thumbnail_url: str | None = None
    # Platforms the creation has published binaries for — e.g.
    # ["WINDOWS", "XBOXONE", "XBOXSERIESX", "PLAYSTATION4", "PLAYSTATION5"].
    # Presence of PLAYSTATION4/5 implies the creation was republished
    # on or after 2026-04-07 (simultaneous with the Free Lanes update),
    # so it is very likely Free-Lanes-compatible.
    platforms: list[str] = field(default_factory=list)
