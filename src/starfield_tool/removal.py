"""Pure logic for removing a Creation: plan + execute.

Separated from the UI so it can be tested without a display. The UI layer
in ``dialogs/remove_creation.py`` wraps these two functions with a
confirmation dialog and a result dialog.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from starfield_tool.game_process import is_starfield_or_launcher_running
from starfield_tool.models import Creation


_PLUGIN_EXTS = (".esm", ".esp", ".esl")

FileStatus = Literal["deleted", "already_gone", "failed"]


@dataclass
class FileOutcome:
    path: Path
    status: FileStatus
    reason: str | None = None


@dataclass
class RemovalPlan:
    content_id: str
    display_name: str
    plugin_files: list[str] = field(default_factory=list)
    files_to_delete: list[Path] = field(default_factory=list)
    out_of_tree_files: list[str] = field(default_factory=list)


@dataclass
class RemovalResult:
    game_was_running: bool = False
    plugins_txt_updated: bool = False
    plugin_lines_dropped: list[str] = field(default_factory=list)
    file_outcomes: list[FileOutcome] = field(default_factory=list)


def plan_removal(
    creation: Creation,
    plugins_txt: Path,
    data_dir: Path,
) -> RemovalPlan:
    """Compute the side effects Remove would cause. Pure — no mutation."""
    plan = RemovalPlan(
        content_id=creation.content_id,
        display_name=creation.display_name,
    )
    plan.plugin_files = [
        f for f in creation.plugin_files if f.lower().endswith(_PLUGIN_EXTS)
    ]

    data_root = data_dir.resolve()
    for entry in creation.plugin_files:
        candidate = (data_dir / entry).resolve()
        try:
            candidate.relative_to(data_root)
        except ValueError:
            plan.out_of_tree_files.append(entry)
            continue
        plan.files_to_delete.append(candidate)

    return plan


def _strip_plugin_lines(
    plugins_txt: Path,
    plugin_files: list[str],
) -> tuple[bool, list[str]]:
    """Remove matching lines from Plugins.txt atomically.

    Returns (was_updated, dropped_lines). If the file is missing or contains
    no matching lines, returns (False, []).
    """
    if not plugin_files:
        return False, []
    try:
        raw = plugins_txt.read_bytes()
    except FileNotFoundError:
        return False, []

    # Preserve existing newline style by working on bytes and splitting on \n.
    text = raw.decode("utf-8-sig")
    lines = text.splitlines(keepends=True)

    wanted = {f.lower() for f in plugin_files}
    kept: list[str] = []
    dropped: list[str] = []
    for line in lines:
        bare = line.rstrip("\r\n").lstrip("*").strip().lower()
        if bare in wanted:
            dropped.append(line.rstrip("\r\n"))
        else:
            kept.append(line)

    if not dropped:
        return False, []

    tmp = plugins_txt.with_suffix(plugins_txt.suffix + ".tmp")
    tmp.write_bytes("".join(kept).encode("utf-8"))
    os.replace(tmp, plugins_txt)
    return True, dropped


def execute_removal(
    plan: RemovalPlan,
    plugins_txt: Path,
    process_probe: Callable[[], bool] = is_starfield_or_launcher_running,
) -> RemovalResult:
    """Execute a confirmed RemovalPlan. No exception escapes."""
    result = RemovalResult()

    if process_probe():
        result.game_was_running = True
        return result

    updated, dropped = _strip_plugin_lines(plugins_txt, plan.plugin_files)
    result.plugins_txt_updated = updated
    result.plugin_lines_dropped = dropped

    for path in plan.files_to_delete:
        try:
            os.remove(path)
            result.file_outcomes.append(FileOutcome(path=path, status="deleted"))
        except FileNotFoundError:
            result.file_outcomes.append(FileOutcome(path=path, status="already_gone"))
        except OSError as exc:
            result.file_outcomes.append(
                FileOutcome(path=path, status="failed", reason=str(exc))
            )

    return result
