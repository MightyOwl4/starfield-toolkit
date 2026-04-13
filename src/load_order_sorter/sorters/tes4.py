"""TES4 master dependency sorter — highest-priority load_after constraints."""
from pathlib import Path

from load_order_sorter.models import SortItem, SortConstraint
from load_order_sorter.tes4_parser import build_master_map

SORTER_NAME = "TES4"
PRIORITY = 100  # highest priority; gaps at 25-90 for future sources


def sort(
    items: list[SortItem],
    data_dir: Path,
    installed_plugins: dict[str, str],
) -> list[SortConstraint]:
    """Produce load_after constraints from TES4 master dependencies.

    Args:
        items: The creation list being sorted.
        data_dir: Path to the game's Data directory.
        installed_plugins: Dict mapping plugin filename to content_id
            (only these are considered as potential masters).

    Returns:
        List of SortConstraint with type="load_after" for each
        creation-to-creation master dependency found.
    """
    master_map = build_master_map(data_dir, installed_plugins)

    constraints: list[SortConstraint] = []
    for item in items:
        masters = master_map.get(item.plugin_name, [])
        for master in masters:
            constraints.append(SortConstraint(
                plugin_name=item.plugin_name,
                type="load_after",
                after=master,
                sorter_name=SORTER_NAME,
                priority=PRIORITY,
            ))

    return constraints
