import hashlib
import os
from pathlib import Path

from starfield_tool.models import Creation
from starfield_tool.removal import execute_removal, plan_removal


def _make_layout(tmp_path: Path, files: dict[str, bytes], plugins_txt: str | None):
    data_dir = tmp_path / "Data"
    data_dir.mkdir()
    for name, body in files.items():
        (data_dir / name).write_bytes(body)
    plugins = tmp_path / "Plugins.txt"
    if plugins_txt is not None:
        plugins.write_text(plugins_txt, encoding="utf-8")
    return data_dir, plugins


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _creation(name: str, files: list[str]) -> Creation:
    return Creation(
        content_id=f"ID_{name}",
        display_name=name,
        plugin_files=files,
    )


# -------------------- plan_removal --------------------

def test_plan_basic(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path, {"foo.esm": b"x", "foo - main.ba2": b"y"}, "*foo.esm\n"
    )
    plan = plan_removal(
        _creation("Foo", ["foo.esm", "foo - main.ba2"]), plugins, data_dir
    )
    assert plan.plugin_files == ["foo.esm"]
    assert len(plan.files_to_delete) == 2
    assert plan.out_of_tree_files == []


def test_plan_rejects_out_of_tree(tmp_path):
    data_dir, plugins = _make_layout(tmp_path, {}, "")
    plan = plan_removal(
        _creation("Esc", ["..\\evil.esm", "foo.esm"]), plugins, data_dir
    )
    assert "..\\evil.esm" in plan.out_of_tree_files
    # foo.esm stays accepted
    assert any(p.name == "foo.esm" for p in plan.files_to_delete)


def test_plan_has_no_side_effects(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path, {"foo.esm": b"x"}, "*foo.esm\n"
    )
    before_plugins = _sha(plugins)
    before_file = _sha(data_dir / "foo.esm")
    plan_removal(_creation("Foo", ["foo.esm"]), plugins, data_dir)
    assert _sha(plugins) == before_plugins
    assert _sha(data_dir / "foo.esm") == before_file


# -------------------- execute_removal --------------------

def test_execute_happy_path(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path,
        {"foo.esm": b"x", "foo - main.ba2": b"y"},
        "*Starfield.esm\n*foo.esm\n",
    )
    plan = plan_removal(
        _creation("Foo", ["foo.esm", "foo - main.ba2"]), plugins, data_dir
    )
    result = execute_removal(plan, plugins, process_probe=lambda: False)
    assert result.plugins_txt_updated is True
    assert len(result.plugin_lines_dropped) == 1
    assert all(o.status == "deleted" for o in result.file_outcomes)
    assert not (data_dir / "foo.esm").exists()
    assert not (data_dir / "foo - main.ba2").exists()
    assert "foo.esm" not in plugins.read_text(encoding="utf-8")
    assert "*Starfield.esm" in plugins.read_text(encoding="utf-8")


def test_execute_esmless(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path,
        {"ba2replacer.ba2": b"x"},
        "*Starfield.esm\n",
    )
    plan = plan_removal(
        _creation("Replacer", ["ba2replacer.ba2"]), plugins, data_dir
    )
    before = _sha(plugins)
    result = execute_removal(plan, plugins, process_probe=lambda: False)
    assert result.plugins_txt_updated is False
    assert _sha(plugins) == before
    assert result.file_outcomes[0].status == "deleted"
    assert not (data_dir / "ba2replacer.ba2").exists()


def test_execute_multi_plugin(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path,
        {"a.esm": b"1", "b.esm": b"2"},
        "*a.esm\n*b.esm\n*Starfield.esm\n",
    )
    plan = plan_removal(_creation("Multi", ["a.esm", "b.esm"]), plugins, data_dir)
    result = execute_removal(plan, plugins, process_probe=lambda: False)
    assert len(result.plugin_lines_dropped) == 2
    txt = plugins.read_text(encoding="utf-8")
    assert "a.esm" not in txt and "b.esm" not in txt
    assert "*Starfield.esm" in txt


def test_execute_case_and_star_insensitive(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path,
        {"Foo.esm": b"1", "bar.esm": b"2"},
        "*Foo.esm\nbar.esm\n",
    )
    plan = plan_removal(_creation("Mix", ["foo.esm", "BAR.ESM"]), plugins, data_dir)
    result = execute_removal(plan, plugins, process_probe=lambda: False)
    assert len(result.plugin_lines_dropped) == 2
    assert plugins.read_text(encoding="utf-8").strip() == ""


def test_execute_refuses_when_game_running(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path, {"foo.esm": b"x"}, "*foo.esm\n"
    )
    before_plugins = _sha(plugins)
    before_file = _sha(data_dir / "foo.esm")
    plan = plan_removal(_creation("Foo", ["foo.esm"]), plugins, data_dir)
    result = execute_removal(plan, plugins, process_probe=lambda: True)
    assert result.game_was_running is True
    assert result.plugins_txt_updated is False
    assert result.file_outcomes == []
    assert _sha(plugins) == before_plugins
    assert _sha(data_dir / "foo.esm") == before_file


def test_execute_already_gone_idempotent(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path, {"there.esm": b"x"}, "*there.esm\n*missing.esm\n"
    )
    # Creation lists three files; only one exists; plugin line exists for both.
    plan = plan_removal(
        _creation("Mix", ["there.esm", "missing.ba2", "missing.esm"]),
        plugins, data_dir,
    )
    result = execute_removal(plan, plugins, process_probe=lambda: False)
    statuses = [o.status for o in result.file_outcomes]
    assert statuses.count("deleted") == 1
    assert statuses.count("already_gone") == 2


def test_execute_plugins_line_already_absent(tmp_path):
    data_dir, plugins = _make_layout(
        tmp_path, {"foo.esm": b"x"}, "*Starfield.esm\n"
    )
    before = _sha(plugins)
    mtime_before = plugins.stat().st_mtime_ns
    plan = plan_removal(_creation("Foo", ["foo.esm"]), plugins, data_dir)
    result = execute_removal(plan, plugins, process_probe=lambda: False)
    assert result.plugins_txt_updated is False
    assert _sha(plugins) == before
    assert plugins.stat().st_mtime_ns == mtime_before


def test_execute_permission_error_on_one_file(tmp_path, monkeypatch):
    data_dir, plugins = _make_layout(
        tmp_path,
        {"foo.esm": b"1", "foo.ba2": b"2", "extra.ba2": b"3"},
        "*foo.esm\n",
    )
    plan = plan_removal(
        _creation("Foo", ["foo.esm", "foo.ba2", "extra.ba2"]), plugins, data_dir
    )
    locked = data_dir.resolve() / "foo.ba2"
    real_remove = os.remove

    def _remove(path, *a, **kw):
        if Path(path) == locked:
            raise PermissionError("locked by antivirus")
        return real_remove(path, *a, **kw)

    monkeypatch.setattr(os, "remove", _remove)
    result = execute_removal(plan, plugins, process_probe=lambda: False)
    by_name = {o.path.name: o for o in result.file_outcomes}
    assert by_name["foo.esm"].status == "deleted"
    assert by_name["foo.ba2"].status == "failed"
    assert "locked by antivirus" in by_name["foo.ba2"].reason
    assert by_name["extra.ba2"].status == "deleted"
    assert result.plugins_txt_updated is True


def test_execute_all_files_failed(tmp_path, monkeypatch):
    data_dir, plugins = _make_layout(
        tmp_path, {"foo.esm": b"x", "foo.ba2": b"y"}, "*foo.esm\n"
    )
    plan = plan_removal(_creation("Foo", ["foo.esm", "foo.ba2"]), plugins, data_dir)

    def _boom(path, *a, **kw):
        raise PermissionError("everything locked")

    monkeypatch.setattr(os, "remove", _boom)
    result = execute_removal(plan, plugins, process_probe=lambda: False)
    assert all(o.status == "failed" for o in result.file_outcomes)
    assert result.plugins_txt_updated is True  # plugins edit happens before deletions
