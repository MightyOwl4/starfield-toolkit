"""Rule book file I/O, normalization, applicability checking, and discovery."""
import json
import os
import tempfile
from collections import defaultdict
from pathlib import Path


def load_rulebook(filepath: Path) -> dict | None:
    """Load a rule book JSON file. Returns None on any error."""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        if not isinstance(data.get("name"), str) or not isinstance(
            data.get("rules"), list
        ):
            return None
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError, KeyError):
        return None


def save_rulebook(data: dict, filepath: Path) -> None:
    """Atomically save a rule book JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2, ensure_ascii=False)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(filepath.parent), suffix=".tmp", prefix="rulebook_"
    )
    try:
        os.write(fd, content.encode("utf-8"))
        os.close(fd)
        os.replace(tmp_path, str(filepath))
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def normalize_rules(rules: list[dict]) -> list[dict]:
    """Convert load_before entries to equivalent load_after constraints.

    If rule A has load_before: ["B"], produces an additional rule
    {"plugin": "B", "load_after": ["A"]}. Returns normalized rules
    with only load_after (no load_before).
    """
    # Accumulate all load_after by plugin
    after_map: dict[str, set[str]] = defaultdict(set)
    notes_map: dict[str, str] = {}

    for rule in rules:
        plugin = rule.get("plugin", "")
        if not plugin:
            continue

        # Direct load_after
        for dep in rule.get("load_after", []):
            after_map[plugin].add(dep)

        # Convert load_before: if A.load_before = [B], then B.load_after += [A]
        for target in rule.get("load_before", []):
            after_map[target].add(plugin)

        if rule.get("note"):
            notes_map[plugin] = rule["note"]

    # Build normalized rule list
    normalized = []
    for plugin, deps in sorted(after_map.items()):
        entry: dict = {"plugin": plugin, "load_after": sorted(deps)}
        if plugin in notes_map:
            entry["note"] = notes_map[plugin]
        normalized.append(entry)

    return normalized


def check_applicability(
    rules: list[dict], installed_plugins: set[str]
) -> tuple[list[dict], set[str], bool]:
    """Check which rules are applicable given installed plugins.

    Returns:
        (applicable_rules, missing_plugins, is_applicable)
        - applicable_rules: rules where plugin is installed, with
          load_after filtered to installed-only targets
        - missing_plugins: set of plugin names referenced but not installed
        - is_applicable: True if at least 1 rule has a valid load_after target
    """
    installed_lower = {p.lower(): p for p in installed_plugins}
    missing: set[str] = set()
    applicable: list[dict] = []

    for rule in rules:
        plugin = rule.get("plugin", "")
        canonical = installed_lower.get(plugin.lower())
        if not canonical:
            missing.add(plugin)
            continue

        # Filter load_after to installed targets only
        valid_after = []
        for dep in rule.get("load_after", []):
            dep_canonical = installed_lower.get(dep.lower())
            if dep_canonical:
                valid_after.append(dep_canonical)
            else:
                missing.add(dep)

        if valid_after:
            applicable.append({
                "plugin": canonical,
                "load_after": valid_after,
                "note": rule.get("note", ""),
            })

    is_applicable = len(applicable) >= 1
    return applicable, missing, is_applicable


def check_tier_applicability(
    rules: list[dict], installed_plugins: set[str]
) -> tuple[list[dict], set[str], bool]:
    """Check which tier rules are applicable given installed plugins.

    Tier rules only need the plugin itself to be installed (no dependency
    targets to filter).

    Returns:
        (applicable_rules, missing_plugins, is_applicable)
    """
    installed_lower = {p.lower(): p for p in installed_plugins}
    missing: set[str] = set()
    applicable: list[dict] = []

    for rule in rules:
        plugin = rule.get("plugin", "")
        canonical = installed_lower.get(plugin.lower())
        if not canonical:
            missing.add(plugin)
            continue

        tier = rule.get("tier")
        if not isinstance(tier, int) or not 1 <= tier <= 11:
            continue

        applicable.append({
            "plugin": canonical,
            "tier": tier,
            "note": rule.get("note", ""),
        })

    return applicable, missing, len(applicable) >= 1


def discover_rulebooks(
    user_dir: Path, curated_dir: Path | None = None
) -> list[dict]:
    """Scan directories for rule book JSON files.

    Returns list of {filepath, filename, source, created_time}.
    Curated books sorted by filename (numeric prefix).
    User books sorted by file creation date (newest first).
    """
    results: list[dict] = []

    # User books: sorted by creation date, newest first
    if user_dir.is_dir():
        user_files = sorted(
            user_dir.glob("*.json"),
            key=lambda p: p.stat().st_ctime,
            reverse=True,
        )
        for fp in user_files:
            results.append({
                "filepath": fp,
                "filename": fp.name,
                "source": "user",
                "created_time": fp.stat().st_ctime,
            })

    # Curated books: sorted by filename (numeric prefix)
    if curated_dir and curated_dir.is_dir():
        curated_files = sorted(curated_dir.glob("*.json"), key=lambda p: p.name)
        for fp in curated_files:
            results.append({
                "filepath": fp,
                "filename": fp.name,
                "source": "curated",
                "created_time": fp.stat().st_ctime,
            })

    return results


def reconcile_registry(
    discovered: list[dict], saved_registry: list[dict]
) -> list[dict]:
    """Merge discovered files with saved registry state.

    - New user files go to top (above saved entries), enabled by default
    - Stale entries (file no longer exists) are discarded
    - Preserved entries keep their enabled state and relative order
    - Curated books maintain filename-based order
    """
    # Build lookup from saved registry
    saved_map = {
        (e["filename"], e["source"]): e for e in saved_registry
    }
    discovered_set = {(d["filename"], d["source"]) for d in discovered}

    # Separate user and curated discovered files
    user_discovered = [d for d in discovered if d["source"] == "user"]
    curated_discovered = [d for d in discovered if d["source"] == "curated"]

    # User books: new ones at top, then saved order for known ones
    new_user = []
    known_user_saved_order = []

    for d in user_discovered:
        key = (d["filename"], d["source"])
        if key in saved_map:
            # Preserve saved state
            known_user_saved_order.append(saved_map[key])
        else:
            # New book: enabled by default, at top
            new_user.append({
                "filename": d["filename"],
                "source": "user",
                "enabled": True,
            })

    # Reorder known user books by saved registry order (not discovery order)
    known_user_by_saved = []
    for saved in saved_registry:
        if saved["source"] != "user":
            continue
        key = (saved["filename"], saved["source"])
        if key in discovered_set:
            known_user_by_saved.append(saved)

    # Curated books: preserve saved enabled state, keep filename order
    curated = []
    for d in curated_discovered:
        key = (d["filename"], d["source"])
        if key in saved_map:
            curated.append(saved_map[key])
        else:
            curated.append({
                "filename": d["filename"],
                "source": "curated",
                "enabled": True,
            })

    return new_user + known_user_by_saved + curated
