"""Rule book sorter — produces load_after constraints from user and curated rule books."""
import logging
from pathlib import Path

from load_order_sorter.models import SortItem, SortConstraint
from load_order_sorter.rulebook import (
    check_applicability,
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

        rules = normalize_rules(book.get("rules", []))
        applicable, _missing, is_applicable = check_applicability(
            rules, installed_set
        )
        if not is_applicable:
            continue

        # Determine priority
        if entry["source"] == "curated":
            priority = PRIORITY_CURATED
            sorter_name = SORTER_NAME_CURATED
        else:
            priority = PRIORITY_USER_BASE + user_position
            sorter_name = SORTER_NAME_USER
            user_position += 1

        # Produce constraints
        for rule in applicable:
            plugin = rule["plugin"]
            for dep in rule.get("load_after", []):
                constraints.append(SortConstraint(
                    plugin_name=plugin,
                    type="load_after",
                    after=dep,
                    sorter_name=sorter_name,
                    priority=priority,
                ))

    return constraints
