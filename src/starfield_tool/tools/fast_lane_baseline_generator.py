"""Developer script to generate a trimmed baseline from the full creations catalogue.

This script is part of the Fast Lane Creation Check feature (009). It is a
developer-only tool that produces `data/creations_baseline.json` for bundling
with the app distribution.

Usage:
    uv run python src/starfield_tool/tools/fast_lane_baseline_generator.py
    uv run python src/starfield_tool/tools/fast_lane_baseline_generator.py --output custom/path.json
    uv run python src/starfield_tool/tools/fast_lane_baseline_generator.py --catalogue path/to/catalogue.json

The script is short-lived and will be removed along with the Fast Lane Check
feature when it loses relevance.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _default_catalogue_path() -> Path:
    app_data = os.environ.get("APPDATA", "")
    return Path(app_data) / "StarfieldToolkit" / "creations_catalogue.json"


def _default_output_path() -> Path:
    # Project root / data / creations_baseline.json
    return Path(__file__).resolve().parents[3] / "data" / "creations_baseline.json"


def extract_latest_version(entry: dict) -> str:
    """Find the latest version from release_notes across all platforms.

    Returns the version_name with the highest ctime across all platform
    release_notes groups. Returns "unknown" if no release_notes are present.
    """
    latest_ts = -1
    latest_version = None
    for platform_group in entry.get("release_notes", []) or []:
        if not isinstance(platform_group, dict):
            continue
        for note in platform_group.get("release_notes", []) or []:
            if not isinstance(note, dict):
                continue
            ts = note.get("ctime", 0) or 0
            if ts > latest_ts:
                latest_ts = ts
                latest_version = note.get("version_name")
    return latest_version or "unknown"


def _derive_snapshot_date(entries: dict) -> str:
    """Derive the snapshot date from entry fetched_at timestamps.

    Uses the earliest fetched_at (start of the scrape) as the canonical
    snapshot date. Falls back to current UTC time if no timestamps exist.
    """
    fetched_times = []
    for entry in entries.values():
        ts = entry.get("fetched_at")
        if isinstance(ts, str) and ts:
            fetched_times.append(ts)
    if fetched_times:
        return min(fetched_times)
    return datetime.now(timezone.utc).isoformat()


def trim_catalogue(full_catalogue: dict) -> dict:
    """Build a trimmed baseline from the full creations catalogue.

    Full catalogue format: {"version": 1, "entries": {<content_id>: {...}}}
    Baseline format: {"version": 1, "snapshot_date": "<ISO>", "entries": {<content_id>: {t, a, v, [s]}}}

    Uses short keys (t=title, a=author, v=version, s=skin flag) to stay
    under the 600 KB bundle size target with ~5000 entries. The "s" flag
    is only present (set to 1) for creations in the "Skins" category, so
    they can be excluded from the "possibly outdated" highlight in the
    Fast Lane Check tool.

    The snapshot_date is derived from the earliest fetched_at timestamp
    among catalogue entries — this represents when the catalogue snapshot
    was taken, NOT when the baseline file was generated.
    """
    entries = full_catalogue.get("entries", {})
    trimmed = {}
    for content_id, entry in entries.items():
        title = entry.get("title", "") or ""
        author = entry.get("author", "") or ""
        version = extract_latest_version(entry)
        trimmed_entry = {
            "t": title,
            "a": author,
            "v": version,
        }
        categories = entry.get("categories") or []
        if "Skins" in categories:
            trimmed_entry["s"] = 1
        trimmed[content_id] = trimmed_entry

    return {
        "version": 1,
        "snapshot_date": _derive_snapshot_date(entries),
        "entries": trimmed,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a trimmed baseline catalogue for Fast Lane Creation Check.",
    )
    parser.add_argument(
        "--catalogue",
        type=Path,
        default=_default_catalogue_path(),
        help="Path to the full creations catalogue (default: %%APPDATA%%/StarfieldToolkit/creations_catalogue.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_output_path(),
        help="Output path for the trimmed baseline (default: <project_root>/data/creations_baseline.json)",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if not args.catalogue.exists():
        print(
            f"Error: Full catalogue not found at {args.catalogue}\n"
            f"Run 'uv run src/scrape_catalogue.py' first to build the catalogue.",
            file=sys.stderr,
        )
        return 2

    try:
        full = json.loads(args.catalogue.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Error: Catalogue is not valid JSON: {exc}", file=sys.stderr)
        return 2

    trimmed = trim_catalogue(full)
    entry_count = len(trimmed.get("entries", {}))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Compact JSON (no pretty-printing) — this is a bundled asset,
    # not meant for human editing. Saves ~60% on file size.
    args.output.write_text(
        json.dumps(trimmed, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    size_kb = args.output.stat().st_size / 1024
    print(f"Baseline written to {args.output}")
    print(f"  Entries: {entry_count}")
    print(f"  Size: {size_kb:.1f} KB")
    print(f"  Snapshot date: {trimmed['snapshot_date']}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
