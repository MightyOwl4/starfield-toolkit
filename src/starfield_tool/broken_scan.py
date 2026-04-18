"""Pure on-disk detector for half-broken Creations.

Emits a list of ``FlaggedCreation`` describing Creations that trip any of
three signals: partial on-disk files, esm-having creation whose plugin
line is absent from Plugins.txt, and mtime skew among on-disk files.

No mutation, no network — feed parsed catalog + plugin entries in and get
a sorted list back.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from load_order_sorter.tes4_parser import parse_masters
from starfield_tool.models import Creation
from starfield_tool.parsers import CatalogEntry, PluginEntry
from starfield_tool.removal import RemovalPlan, RemovalResult, plan_removal


DetectionReason = Literal[
    "partial_files",
    "esm_without_plugins_line",
    "mtime_skew",
    "out_of_tree",
]

_PLUGIN_EXTS = (".esm", ".esp", ".esl")


@dataclass
class FlaggedCreation:
    content_id: str
    display_name: str
    author: str = ""
    catalog_version: str = ""
    catalog_files: list[str] = field(default_factory=list)
    plugin_files: list[str] = field(default_factory=list)
    files_present: list[Path] = field(default_factory=list)
    files_missing: list[str] = field(default_factory=list)
    reasons: list[DetectionReason] = field(default_factory=list)


@dataclass
class BrokenDeletePlan:
    flagged: list[FlaggedCreation] = field(default_factory=list)
    removal_plans: list[RemovalPlan] = field(default_factory=list)


@dataclass
class BrokenDeleteResult:
    game_was_running: bool = False
    results: list[tuple[FlaggedCreation, RemovalResult]] = field(default_factory=list)
    display_names_processed: list[str] = field(default_factory=list)


def _safe_mtime(path: Path) -> float | None:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def scan_broken(
    catalog_entries: list[CatalogEntry],
    plugin_entries: list[PluginEntry],
    data_dir: Path,
    now_fn: Callable[[], float] = time.time,
    mtime_skew_threshold_s: float = 300.0,
) -> list[FlaggedCreation]:
    """Return every catalog entry that trips any detection signal."""
    del now_fn  # reserved for future signals

    plugin_names = {pe.filename.lower() for pe in plugin_entries}
    data_root = data_dir.resolve()

    # Extend with auto-loaded masters: for every esm in Plugins.txt, read its
    # TES4 MAST subrecords. Those masters are implicitly loaded by the engine
    # and don't need their own Plugins.txt entry.
    auto_loaded: set[str] = set()
    for pe in plugin_entries:
        candidate = (data_dir / pe.filename).resolve()
        try:
            candidate.relative_to(data_root)
        except ValueError:
            continue
        if candidate.is_file():
            for m in parse_masters(candidate):
                auto_loaded.add(m.lower())
    plugin_names |= auto_loaded

    flagged: list[FlaggedCreation] = []
    for ce in catalog_entries:
        if not ce.files:
            continue

        files_present: list[Path] = []
        in_tree_missing: list[str] = []
        out_of_tree_missing: list[str] = []

        for entry in ce.files:
            candidate = (data_dir / entry).resolve()
            try:
                candidate.relative_to(data_root)
            except ValueError:
                out_of_tree_missing.append(entry)
                continue
            if candidate.is_file():
                files_present.append(candidate)
            else:
                in_tree_missing.append(entry)

        reasons: list[DetectionReason] = []

        if out_of_tree_missing:
            reasons.append("out_of_tree")

        # Signal (a): at least one present AND at least one in-tree missing.
        if files_present and in_tree_missing:
            reasons.append("partial_files")

        # Signal (b): the Creation has present esm-like files but NONE of them
        # are in the effective plugin set (direct plugins.txt + auto-loaded
        # masters). Per-file mismatches (e.g. a sibling blueprint esm that the
        # engine picks up via a different mechanism) are ignored — we only
        # flag when the Creation as a whole appears unloaded.
        present_esms_lower = {
            p.name.lower() for p in files_present
            if p.name.lower().endswith(_PLUGIN_EXTS)
        }
        if present_esms_lower and present_esms_lower.isdisjoint(plugin_names):
            reasons.append("esm_without_plugins_line")

        # Signal (c): mtime skew among present files.
        if len(files_present) >= 2:
            mtimes = [m for m in (_safe_mtime(p) for p in files_present) if m is not None]
            if len(mtimes) >= 2 and (max(mtimes) - min(mtimes)) > mtime_skew_threshold_s:
                reasons.append("mtime_skew")

        if not reasons:
            continue

        flagged.append(FlaggedCreation(
            content_id=ce.content_id,
            display_name=ce.title,
            author=ce.author,
            catalog_version=ce.version,
            catalog_files=list(ce.files),
            plugin_files=[f for f in ce.files if f.lower().endswith(_PLUGIN_EXTS)],
            files_present=files_present,
            files_missing=in_tree_missing + out_of_tree_missing,
            reasons=reasons,
        ))

    flagged.sort(key=lambda f: f.display_name.casefold())
    return flagged


def build_delete_plan(
    flagged: list[FlaggedCreation],
    plugins_txt: Path,
    data_dir: Path,
) -> BrokenDeletePlan:
    """Aggregate per-creation removal plans for the selection."""
    plans: list[RemovalPlan] = []
    for f in flagged:
        synthetic = Creation(
            content_id=f.content_id,
            display_name=f.display_name,
            plugin_files=list(f.catalog_files),
        )
        plans.append(plan_removal(synthetic, plugins_txt, data_dir))
    return BrokenDeletePlan(flagged=list(flagged), removal_plans=plans)
