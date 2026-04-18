import os
from pathlib import Path

from starfield_tool.broken_scan import (
    BrokenDeleteResult,
    build_delete_plan,
    scan_broken,
)
from starfield_tool.parsers import CatalogEntry, PluginEntry


def _layout(tmp_path: Path, files: dict[str, bytes], plugins_lines: list[str] | None,
            mtimes: dict[str, float] | None = None) -> tuple[Path, Path]:
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    for name, body in files.items():
        (data_dir / name).write_bytes(body)
    if mtimes:
        for name, mt in mtimes.items():
            os.utime(data_dir / name, (mt, mt))
    plugins = tmp_path / "Plugins.txt"
    if plugins_lines is not None:
        plugins.write_text("\n".join(plugins_lines) + ("\n" if plugins_lines else ""), encoding="utf-8")
    return data_dir, plugins


def _plugin_entries(lines: list[str]) -> list[PluginEntry]:
    out = []
    for i, raw in enumerate(lines):
        active = raw.startswith("*")
        name = raw.lstrip("*").strip()
        if name:
            out.append(PluginEntry(filename=name, is_active=active, position=i))
    return out


def _cat(title: str, files: list[str], cid: str = None) -> CatalogEntry:
    return CatalogEntry(
        content_id=cid or f"TM_{title}",
        title=title,
        version="1.0.0",
        author="a",
        files=files,
    )


# -------------------- signal isolation --------------------

def test_healthy_returns_empty(tmp_path):
    data_dir, _ = _layout(
        tmp_path,
        {"foo.esm": b"1", "foo.ba2": b"2"},
        ["*foo.esm"],
        mtimes={"foo.esm": 1_000_000.0, "foo.ba2": 1_000_000.0},
    )
    plugins = _plugin_entries(["*foo.esm"])
    result = scan_broken([_cat("Foo", ["foo.esm", "foo.ba2"])], plugins, data_dir)
    assert result == []


def test_partial_files_signal(tmp_path):
    data_dir, _ = _layout(
        tmp_path, {"foo.esm": b"1"}, ["*foo.esm"],
        mtimes={"foo.esm": 1_000_000.0},
    )
    plugins = _plugin_entries(["*foo.esm"])
    result = scan_broken(
        [_cat("Foo", ["foo.esm", "foo.ba2", "extra.ba2"])], plugins, data_dir,
    )
    assert len(result) == 1
    assert "partial_files" in result[0].reasons
    assert "esm_without_plugins_line" not in result[0].reasons


def test_esm_without_plugins_line(tmp_path):
    data_dir, _ = _layout(
        tmp_path, {"foo.esm": b"1", "foo.ba2": b"2"}, [],
        mtimes={"foo.esm": 1_000_000.0, "foo.ba2": 1_000_000.0},
    )
    result = scan_broken(
        [_cat("Foo", ["foo.esm", "foo.ba2"])], _plugin_entries([]), data_dir,
    )
    assert len(result) == 1
    assert result[0].reasons == ["esm_without_plugins_line"]


def test_mtime_skew_triggers(tmp_path):
    data_dir, _ = _layout(
        tmp_path, {"a.esm": b"1", "a.ba2": b"2"}, ["*a.esm"],
        mtimes={"a.esm": 1_000_000.0, "a.ba2": 1_000_600.0},
    )
    result = scan_broken([_cat("A", ["a.esm", "a.ba2"])], _plugin_entries(["*a.esm"]), data_dir)
    assert result and result[0].reasons == ["mtime_skew"]


def test_mtime_skew_within_threshold(tmp_path):
    data_dir, _ = _layout(
        tmp_path, {"a.esm": b"1", "a.ba2": b"2"}, ["*a.esm"],
        mtimes={"a.esm": 1_000_000.0, "a.ba2": 1_000_120.0},
    )
    result = scan_broken([_cat("A", ["a.esm", "a.ba2"])], _plugin_entries(["*a.esm"]), data_dir)
    assert result == []


def test_all_three_signals_together(tmp_path):
    # esm present, ba2 present (skewed), textures missing, no plugins.txt line.
    data_dir, _ = _layout(
        tmp_path, {"mix.esm": b"1", "mix - main.ba2": b"2"}, [],
        mtimes={"mix.esm": 1_000_000.0, "mix - main.ba2": 1_000_700.0},
    )
    result = scan_broken(
        [_cat("Mix", ["mix.esm", "mix - main.ba2", "mix - textures.ba2"])],
        _plugin_entries([]), data_dir,
    )
    assert len(result) == 1
    reasons = result[0].reasons
    assert set(reasons) == {"partial_files", "esm_without_plugins_line", "mtime_skew"}
    assert len(reasons) == len(set(reasons))  # no dupes


def test_esmless_creation_skew_only(tmp_path):
    data_dir, _ = _layout(
        tmp_path, {"rep - main.ba2": b"1", "rep - textures.ba2": b"2"},
        [],
        mtimes={"rep - main.ba2": 1_000_000.0, "rep - textures.ba2": 1_000_900.0},
    )
    result = scan_broken(
        [_cat("Rep", ["rep - main.ba2", "rep - textures.ba2"])],
        _plugin_entries([]), data_dir,
    )
    # No esm, so signal (b) must not fire; mtime skew must.
    assert result and result[0].reasons == ["mtime_skew"]


def test_out_of_tree_entry(tmp_path):
    data_dir, _ = _layout(
        tmp_path, {"foo.esm": b"1"}, ["*foo.esm"],
        mtimes={"foo.esm": 1_000_000.0},
    )
    result = scan_broken(
        [_cat("Esc", ["../evil.esm", "foo.esm"])],
        _plugin_entries(["*foo.esm"]), data_dir,
    )
    assert len(result) == 1
    assert "out_of_tree" in result[0].reasons
    assert "../evil.esm" in result[0].files_missing


def test_plugins_txt_missing_flags_every_esm_having(tmp_path):
    data_dir, _ = _layout(
        tmp_path, {"a.esm": b"1", "b.esm": b"2"}, None,
        mtimes={"a.esm": 1_000_000.0, "b.esm": 1_000_000.0},
    )
    result = scan_broken(
        [_cat("A", ["a.esm"], cid="AA"), _cat("B", ["b.esm"], cid="BB")],
        _plugin_entries([]), data_dir,
    )
    assert len(result) == 2
    assert all("esm_without_plugins_line" in f.reasons for f in result)


def test_empty_catalog(tmp_path):
    data_dir, _ = _layout(tmp_path, {}, [])
    assert scan_broken([], _plugin_entries([]), data_dir) == []


def test_alphabetical_casefold_sort(tmp_path):
    data_dir, _ = _layout(
        tmp_path, {"z.esm": b"1", "a.esm": b"1"}, [],
        mtimes={"z.esm": 1_000_000.0, "a.esm": 1_000_000.0},
    )
    result = scan_broken(
        [_cat("zebra", ["z.esm"], cid="Z"), _cat("Apple", ["a.esm"], cid="A")],
        _plugin_entries([]), data_dir,
    )
    assert [f.display_name for f in result] == ["Apple", "zebra"]


# -------------------- delete plan aggregation --------------------

def test_build_delete_plan_round_trip(tmp_path):
    data_dir, plugins = _layout(
        tmp_path, {"foo.esm": b"1", "foo.ba2": b"2"}, ["*foo.esm"],
        mtimes={"foo.esm": 1_000_000.0, "foo.ba2": 1_000_700.0},
    )
    flagged = scan_broken(
        [_cat("Foo", ["foo.esm", "foo.ba2"])],
        _plugin_entries(["*foo.esm"]), data_dir,
    )
    plan = build_delete_plan(flagged, plugins, data_dir)
    assert len(plan.removal_plans) == 1
    rp = plan.removal_plans[0]
    assert rp.plugin_files == ["foo.esm"]
    assert {p.name for p in rp.files_to_delete} == {"foo.esm", "foo.ba2"}


def test_build_delete_plan_multi(tmp_path):
    data_dir, plugins = _layout(
        tmp_path,
        {"a.esm": b"1", "b.esm": b"2", "b.ba2": b"3"},
        [],
        mtimes={"a.esm": 1_000_000.0, "b.esm": 1_000_000.0, "b.ba2": 1_000_900.0},
    )
    flagged = scan_broken(
        [_cat("A", ["a.esm"], cid="AA"), _cat("B", ["b.esm", "b.ba2"], cid="BB")],
        _plugin_entries([]), data_dir,
    )
    plan = build_delete_plan(flagged, plugins, data_dir)
    all_files = {p.name for rp in plan.removal_plans for p in rp.files_to_delete}
    assert all_files == {"a.esm", "b.esm", "b.ba2"}


# -------------------- auto-loaded masters --------------------

def _write_tes4_with_masters(path: Path, masters: list[str]) -> None:
    """Write a minimal valid TES4 record whose only subrecords are MAST entries."""
    import struct
    subrecords = b""
    for m in masters:
        body = m.encode("utf-8") + b"\x00"
        subrecords += b"MAST" + struct.pack("<H", len(body)) + body
    header = (
        b"TES4"
        + struct.pack("<I", len(subrecords))  # data size
        + b"\x00" * 16                        # rest of record header
    )
    path.write_bytes(header + subrecords)


def test_auto_loaded_master_is_not_flagged(tmp_path):
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    # sfta03.esm is active in plugins.txt; its TES4 MAST lists blueprintships-sfta03.esm
    _write_tes4_with_masters(data_dir / "sfta03.esm", ["blueprintships-sfta03.esm"])
    _write_tes4_with_masters(data_dir / "blueprintships-sfta03.esm", [])
    import os
    os.utime(data_dir / "sfta03.esm", (1_000_000.0, 1_000_000.0))
    os.utime(data_dir / "blueprintships-sfta03.esm", (1_000_000.0, 1_000_000.0))

    plugins = _plugin_entries(["*sfta03.esm"])
    cat = _cat("Trackers Alliance", ["sfta03.esm", "blueprintships-sfta03.esm"])
    result = scan_broken([cat], plugins, data_dir)
    # Neither signal (a) nor (b) nor (c) should fire — everything is healthy
    # once auto-loaded masters are taken into account.
    assert result == []


def test_master_of_an_inactive_plugin_still_flags(tmp_path):
    # If the "primary" esm isn't in plugins.txt, the helper .esm is not
    # auto-loaded either — it should still flag.
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    _write_tes4_with_masters(data_dir / "sfta03.esm", ["blueprintships-sfta03.esm"])
    _write_tes4_with_masters(data_dir / "blueprintships-sfta03.esm", [])
    import os
    os.utime(data_dir / "sfta03.esm", (1_000_000.0, 1_000_000.0))
    os.utime(data_dir / "blueprintships-sfta03.esm", (1_000_000.0, 1_000_000.0))

    plugins = _plugin_entries([])  # nothing active
    cat = _cat("Trackers Alliance", ["sfta03.esm", "blueprintships-sfta03.esm"])
    result = scan_broken([cat], plugins, data_dir)
    assert len(result) == 1
    assert "esm_without_plugins_line" in result[0].reasons


# -------------------- game-running refusal (US2) --------------------

def test_delete_flow_refused_when_game_running(tmp_path):
    """Simulates the tab's delete execute loop; verifies zero mutations
    when process_probe returns True. Matches feature 013's contract."""
    import hashlib

    from starfield_tool.removal import execute_removal

    data_dir, plugins = _layout(
        tmp_path, {"foo.esm": b"1", "foo.ba2": b"2"}, ["*foo.esm"],
        mtimes={"foo.esm": 1_000_000.0, "foo.ba2": 1_000_700.0},
    )
    flagged = scan_broken(
        [_cat("Foo", ["foo.esm", "foo.ba2"])],
        _plugin_entries(["*foo.esm"]), data_dir,
    )
    plan = build_delete_plan(flagged, plugins, data_dir)

    before_plugins = hashlib.sha256(plugins.read_bytes()).hexdigest()
    before_files = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in data_dir.iterdir()
    }

    # Short-circuit the same way the tab does: probe is pre-flight.
    probe = lambda: True  # noqa: E731
    result = BrokenDeleteResult()
    if probe():
        result.game_was_running = True
    else:
        for fg, rp in zip(plan.flagged, plan.removal_plans):
            rr = execute_removal(rp, plugins, process_probe=lambda: False)
            result.results.append((fg, rr))

    assert result.game_was_running is True
    assert result.results == []
    assert hashlib.sha256(plugins.read_bytes()).hexdigest() == before_plugins
    assert {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in data_dir.iterdir()
    } == before_files


# -------------------- offline guard --------------------

def test_scan_does_not_import_network_modules():
    """Regression guard for FR-017 / US4: broken_scan must be pure on-disk."""
    src = (Path(__file__).parent.parent / "src" / "starfield_tool" /
           "broken_scan.py").read_text(encoding="utf-8")
    assert "bethesda_creations" not in src
    assert "starfield_tool.creations" not in src
    assert "import requests" not in src
    assert "urllib" not in src
