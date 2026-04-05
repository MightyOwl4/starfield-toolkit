"""Pre-write validation for TES4 master dependency ordering."""
from dataclasses import dataclass


@dataclass
class ValidationViolation:
    """A single ordering violation where a plugin appears before its master."""
    plugin_name: str
    display_name: str
    master_name: str
    master_display_name: str
    current_position: int
    master_position: int


def validate_tes4_order(
    plugin_order: list[str],
    master_map: dict[str, list[str]],
    display_names: dict[str, str] | None = None,
) -> list[ValidationViolation]:
    """Check that all TES4 master dependencies are satisfied in the given order.

    Returns a list of violations (empty = valid order). Each violation
    indicates a plugin that appears before one of its masters.

    Args:
        plugin_order: List of plugin filenames in proposed load order.
        master_map: Dict mapping plugin filename to list of master filenames.
        display_names: Optional dict mapping plugin filename to display name.
    """
    names = display_names or {}
    position = {name: i for i, name in enumerate(plugin_order)}
    violations: list[ValidationViolation] = []

    for plugin in plugin_order:
        masters = master_map.get(plugin, [])
        plugin_pos = position[plugin]
        for master in masters:
            master_pos = position.get(master)
            if master_pos is not None and master_pos > plugin_pos:
                violations.append(ValidationViolation(
                    plugin_name=plugin,
                    display_name=names.get(plugin, plugin),
                    master_name=master,
                    master_display_name=names.get(master, master),
                    current_position=plugin_pos,
                    master_position=master_pos,
                ))

    return violations


def format_violations(violations: list[ValidationViolation], max_shown: int = 5) -> str:
    """Format violations into a user-facing message."""
    if not violations:
        return ""

    lines = ["The following creations are placed before plugins they depend on:\n"]
    for v in violations[:max_shown]:
        lines.append(
            f"  \u2022 {v.display_name} must load after {v.master_display_name}"
        )

    remaining = len(violations) - max_shown
    if remaining > 0:
        lines.append(f"\n  ...and {remaining} more violation(s)")

    lines.append(
        "\nThis load order would crash the game. "
        "Use Auto Sort to fix the order automatically."
    )
    return "\n".join(lines)
