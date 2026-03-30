"""Category-based sorter — maps Bethesda API categories to the 11-tier system."""
from load_order_sorter.models import SortItem, SortConstraint

SORTER_NAME = "CAT"
PRIORITY = 10  # lowest priority sorter

# Mapping from Bethesda API category names to community tier numbers.
_CATEGORY_TO_TIER: dict[str, int] = {
    "Overhaul": 3,
    "Quests": 3,
    "Dungeons": 3,
    "Outpost": 4,
    "Gameplay": 5,
    "Immersion": 5,
    "Visuals": 7,
    "Gear": 10,
    "Weapons": 10,
    "Apparel": 10,
    "Homes": 11,
    "Vehicles": 11,
    "Miscellaneous": 9,
    "Cheats": 11,
}

DEFAULT_TIER = 9  # Ship Additions / Default


def sort(items: list[SortItem]) -> list[SortConstraint]:
    """Produce tier-assignment constraints from Bethesda API categories."""
    constraints: list[SortConstraint] = []
    for item in items:
        tier = _resolve_tier(item)
        constraints.append(SortConstraint(
            plugin_name=item.plugin_name,
            type="tier",
            tier=tier,
            sorter_name=SORTER_NAME,
            priority=PRIORITY,
        ))
    return constraints


_BETHESDA_AUTHORS = {"BethesdaGameStudios", "Bethesda Game Studios"}


def _resolve_tier(item: SortItem) -> int:
    # Official Bethesda creations always tier 1
    if item.content_id.startswith("SFBGS") or item.author in _BETHESDA_AUTHORS:
        return 1
    # Use the highest-priority (lowest-numbered) tier from categories
    best = DEFAULT_TIER
    for cat in item.categories:
        tier = _CATEGORY_TO_TIER.get(cat)
        if tier is not None and tier < best:
            best = tier
    return best
