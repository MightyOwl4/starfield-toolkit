"""Version string comparison utility."""


def compare_versions(installed: str, available: str) -> bool:
    """Return True if available is newer than installed.

    Uses simple tuple comparison of numeric version parts.
    Falls back to string comparison if non-numeric.
    """
    try:
        inst_parts = tuple(int(x) for x in installed.split("."))
        avail_parts = tuple(int(x) for x in available.split("."))
        return avail_parts > inst_parts
    except (ValueError, AttributeError):
        return available > installed
