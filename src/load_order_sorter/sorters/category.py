"""Category-based sorter — maps Bethesda API categories to the 11-tier system."""
from load_order_sorter.models import SortItem, SortConstraint

SORTER_NAME = "CAT"
PRIORITY = 10  # lowest priority sorter

# Mapping from Bethesda API category names to community tier numbers.
# Mapping from Bethesda API category names to community tier numbers.
# "Load Order Neutral" and "Lore Friendly" are meta-tags (not placement
# hints) and intentionally unmapped — the content category determines tier.
_CATEGORY_TO_TIER: dict[str, int] = {
    # Tier 3 — Invasive World Edits
    "Overhaul": 3,
    "Quests": 3,
    "Dungeons": 3,
    "World": 3,
    "Planets": 3,
    "Creatures": 3,
    # Tier 4 — Workshop
    "Outpost": 4,
    # Tier 5 — Gameplay Changes
    "Gameplay": 5,
    "Immersion": 5,
    # Tier 6 — Companions
    "Followers": 6,
    # Tier 7 — Audio / Visual
    "Visuals": 7,
    "Environmental": 7,
    # Tier 8 — HUD / UI
    "UI": 8,
    # Tier 9 — Ship Additions / Default
    "Ships": 9,
    "Miscellaneous": 9,
    # Tier 10 — Character Wearables
    "Gear": 10,
    "Weapons": 10,
    "Apparel": 10,
    "Skins": 10,
    "Body": 10,
    # Tier 11 — Non-Invasive World Edits
    "Homes": 11,
    "Vehicles": 11,
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
            sorter_name=f"{SORTER_NAME}({tier})",
            priority=PRIORITY,
        ))
    return constraints


def _resolve_tier(item: SortItem) -> int:
    # All creations sort by their content categories.  Base-game master
    # files (SFBGS prefix) never appear in the creation list — they are
    # filtered out by the parser — so no special-casing is needed here.
    #
    # Use the highest-priority (lowest-numbered) tier from mapped categories
    matched = [
        _CATEGORY_TO_TIER[cat]
        for cat in item.categories
        if cat in _CATEGORY_TO_TIER
    ]
    return min(matched) if matched else DEFAULT_TIER
