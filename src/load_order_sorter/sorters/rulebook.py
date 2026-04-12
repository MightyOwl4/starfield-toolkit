"""Rule book sorter — produces constraints from user and curated rule books.

Supports two book types (determined by the ``"type"`` field in the JSON):
- ``"order"`` (default): produces ``load_after`` constraints from ordering rules.
- ``"tier"``: produces ``tier`` constraints that override the category sorter.
"""
import logging
from pathlib import Path

from load_order_sorter.models import SortItem, SortConstraint
from load_order_sorter.rulebook import (
    check_applicability,
    check_tier_applicability,
    discover_rulebooks,
    load_rulebook,
    normalize_rules,
    reconcile_registry,
)

SORTER_NAME_CURATED = "RULE"
SORTER_NAME_USER = "RULE"
PRIORITY_CURATED = 30
PRIORITY_USER_BASE = 40

log = logging.getLogger(__name__)


def sort(
    items: list[SortItem],
    user_dir: Path,
    curated_dir: Path | None = None,
    registry: list[dict] | None = None,
    installed_plugins: dict[str, str] | None = None,
) -> list[SortConstraint]:
    """Produce load_after constraints from all enabled, applicable rule books.

    Args:
        items: The creation list being sorted.
        user_dir: Path to user rule book directory.
        curated_dir: Path to curated (bundled) rule book directory.
        registry: Saved registry from AppSettings (ordered, with enabled state).
        installed_plugins: Dict mapping plugin filename to content_id.

    Returns:
        List of SortConstraint with appropriate priorities.
    """
    if installed_plugins is None:
        return []

    installed_set = set(installed_plugins.keys())

    # Discover and reconcile
    discovered = discover_rulebooks(user_dir, curated_dir)
    active_registry = reconcile_registry(discovered, registry or [])

    # Build filepath lookup from discovered
    filepath_map = {
        (d["filename"], d["source"]): d["filepath"] for d in discovered
    }

    constraints: list[SortConstraint] = []
    user_position = 0

    for entry in active_registry:
        if not entry.get("enabled", True):
            continue

        key = (entry["filename"], entry["source"])
        filepath = filepath_map.get(key)
        if not filepath:
            continue

        book = load_rulebook(filepath)
        if book is None:
            log.warning("Corrupted rule book: %s", entry["filename"])
            continue

        # Determine priority
        if entry["source"] == "curated":
            priority = PRIORITY_CURATED
        else:
            priority = PRIORITY_USER_BASE + user_position
            user_position += 1

        # Qualify sorter_name with the rulebook filename so the diff
        # dialog's hints view can show which book contributed each hint.
        filename = entry["filename"]
        sorter_name = f"RULE:{filename}"

        book_type = book.get("type", "order")

        if book_type == "tier":
            # Tier book: emit tier constraints directly
            applicable, _missing, is_applicable = check_tier_applicability(
                book.get("rules", []), installed_set
            )
            if not is_applicable:
                continue
            for rule in applicable:
                tier = rule["tier"]
                constraints.append(SortConstraint(
                    plugin_name=rule["plugin"],
                    type="tier",
                    tier=tier,
                    sorter_name=f"{sorter_name}({tier})",
                    priority=priority,
                    note=rule.get("note", ""),
                ))
        else:
            # Order book (default): emit load_after constraints.
            # normalize_rules merges notes per plugin; look them up by name.
            raw_rules = book.get("rules", [])
            notes_by_plugin = {
                r.get("plugin", ""): r.get("note", "")
                for r in raw_rules if r.get("note")
            }
            rules = normalize_rules(raw_rules)
            applicable, _missing, is_applicable = check_applicability(
                rules, installed_set
            )
            if not is_applicable:
                continue
            for rule in applicable:
                plugin = rule["plugin"]
                rule_note = notes_by_plugin.get(plugin, "") or rule.get("note", "")
                for dep in rule.get("load_after", []):
                    constraints.append(SortConstraint(
                        plugin_name=plugin,
                        type="load_after",
                        after=dep,
                        sorter_name=sorter_name,
                        priority=priority,
                        note=rule_note,
                    ))

    return constraints
