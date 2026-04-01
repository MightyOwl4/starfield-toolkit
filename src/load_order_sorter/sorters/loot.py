"""LOOT masterlist sorter — parses YAML for groups and load-after rules."""
from pathlib import Path

import yaml

from load_order_sorter.models import SortItem, SortConstraint

SORTER_NAME = "LOOT"
PRIORITY = 20  # higher than category sorter

# Map LOOT group names to community tier numbers.
# "Bethesda Game Studios Creations" and "Trackers Alliance" are omitted
# so those plugins fall through to the category sorter, which places them
# by their content categories (skins, quests, ships, etc.) rather than
# pinning all BGS marketplace items to tier 1.
_GROUP_TO_TIER: dict[str, int] = {
    "Main Plugins": 1,
    "Fixes & Resources": 2,
    "Early Loaders": 2,
    "Verified Creations": 3,
    "High Priority Overrides": 3,
    "Core Mods": 5,
    "default": 9,
    "Low Priority Overrides": 10,
    "Late Loaders": 11,
    "Dynamic Patches": 11,
    "Late Fixes & Changes": 11,
}

DEFAULT_TIER = 9


def sort(
    items: list[SortItem], masterlist_path: Path,
) -> list[SortConstraint]:
    """Produce constraints from a LOOT masterlist YAML file."""
    try:
        text = masterlist_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except (FileNotFoundError, OSError, yaml.YAMLError):
        return []

    if not isinstance(data, dict):
        return []

    # Build plugin name → metadata lookup from masterlist
    plugin_meta = _parse_plugins(data)
    group_tiers = _parse_groups(data)

    # Map installed plugins to constraints
    constraints: list[SortConstraint] = []
    plugin_names = {item.plugin_name.lower(): item.plugin_name for item in items}

    # Groups to skip — let the category sorter handle these instead
    _SKIP_TIER_GROUPS = {
        "Bethesda Game Studios Creations",
        "Trackers Alliance",
    }

    for lower_name, original_name in plugin_names.items():
        meta = plugin_meta.get(lower_name)
        if not meta:
            continue

        group = meta.get("group", "default")
        warnings = meta.get("warnings", [])

        # Only emit a tier constraint if the group is in our map
        # and not in the skip set (those fall through to category sorter)
        if group not in _SKIP_TIER_GROUPS:
            tier = group_tiers.get(group, DEFAULT_TIER)
            constraints.append(SortConstraint(
                plugin_name=original_name,
                type="tier",
                tier=tier,
                sorter_name=f"{SORTER_NAME}({tier})",
                priority=PRIORITY,
                warnings=warnings,
            ))
        elif warnings:
            # Still surface warnings even when tier is skipped
            constraints.append(SortConstraint(
                plugin_name=original_name,
                type="tier",
                tier=None,
                sorter_name=SORTER_NAME,
                priority=0,  # won't win tier resolution
                warnings=warnings,
            ))

        # Load-after constraints
        for after_name in meta.get("after", []):
            # Only add if the referenced plugin is in our list
            if after_name.lower() in plugin_names:
                constraints.append(SortConstraint(
                    plugin_name=original_name,
                    type="load_after",
                    after=plugin_names[after_name.lower()],
                    sorter_name=SORTER_NAME,
                    priority=PRIORITY,
                ))

    return constraints


def _parse_plugins(data: dict) -> dict[str, dict]:
    """Extract plugin metadata from the masterlist."""
    result: dict[str, dict] = {}
    plugins = data.get("plugins", [])
    if not isinstance(plugins, list):
        return result

    for entry in plugins:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name", "")
        if not name:
            continue

        meta: dict = {}

        # Group assignment
        group = entry.get("group")
        if group:
            meta["group"] = group if isinstance(group, str) else str(group)

        # Load-after dependencies
        after_list = entry.get("after", [])
        if isinstance(after_list, list):
            after_names = []
            for a in after_list:
                if isinstance(a, dict):
                    a_name = a.get("name", "")
                    if a_name:
                        after_names.append(a_name)
                elif isinstance(a, str):
                    after_names.append(a)
            meta["after"] = after_names

        # Warnings from messages
        msgs = entry.get("msg", [])
        if isinstance(msgs, list):
            warnings = []
            for msg in msgs:
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    if content:
                        warnings.append(content)
            if warnings:
                meta["warnings"] = warnings

        result[name.lower()] = meta

    return result


def _parse_groups(data: dict) -> dict[str, int]:
    """Build group name → tier mapping from masterlist groups."""
    tiers = dict(_GROUP_TO_TIER)

    groups = data.get("groups", [])
    if not isinstance(groups, list):
        return tiers

    # For groups not in our hardcoded map, assign default tier
    for group in groups:
        if isinstance(group, dict):
            name = group.get("name", "")
            if name and name not in tiers:
                tiers[name] = DEFAULT_TIER

    return tiers
