"""Tests for the updated export format (feature 009 FR-020).

Verifies that the Installed Creations tab export now includes Content ID
as the second column and renames Version to Installed Version.

These tests exercise the _export() logic by constructing a minimal tool
instance and calling the export with a tmp_path destination.
"""
import csv
from unittest.mock import patch

from starfield_tool.models import Creation


def _make_creation(content_id, display_name, author, version, position=0):
    return Creation(
        content_id=content_id,
        display_name=display_name,
        author=author,
        installed_version=version,
        plugin_files=[f"{content_id}.esm"],
        load_position=position,
    )


def _run_export(tmp_path, creations, suffix=".csv"):
    """Invoke _export() by instantiating the tool and mocking the file dialog."""
    from starfield_tool.tools.creation_load_order import CreationLoadOrderTool

    tool = CreationLoadOrderTool()
    tool._creations = creations

    out_path = tmp_path / f"export{suffix}"
    with patch(
        "starfield_tool.tools.creation_load_order.filedialog.asksaveasfilename",
        return_value=str(out_path),
    ):
        tool._export()
    return out_path


def test_csv_export_includes_content_id_column(tmp_path):
    creations = [
        _make_creation("abc-123", "My Mod", "AuthorName", "1.2.3", position=0),
    ]
    out_path = _run_export(tmp_path, creations, suffix=".csv")

    with open(out_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader)
        row = next(reader)

    assert headers == ["#", "Content ID", "Name", "Author", "Installed Version", "Date"]
    assert row[1] == "abc-123"  # Content ID in position 1
    assert row[2] == "My Mod"
    assert row[3] == "AuthorName"
    assert row[4] == "1.2.3"


def test_csv_export_version_header_renamed(tmp_path):
    creations = [_make_creation("a", "A", "x", "1.0")]
    out_path = _run_export(tmp_path, creations, suffix=".csv")

    with open(out_path, newline="", encoding="utf-8") as f:
        headers = next(csv.reader(f))

    # Old name "Version" must be gone; new name "Installed Version" present
    assert "Version" not in headers
    assert "Installed Version" in headers


def test_csv_export_multiple_rows(tmp_path):
    creations = [
        _make_creation("id-1", "Mod A", "Author One", "1.0", position=0),
        _make_creation("id-2", "Mod B", "Author Two", "2.5.1", position=1),
    ]
    out_path = _run_export(tmp_path, creations, suffix=".csv")

    with open(out_path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        rows = list(reader)

    assert len(rows) == 2
    assert rows[0][1] == "id-1"
    assert rows[1][1] == "id-2"


def test_markdown_export_includes_content_id_column(tmp_path):
    creations = [_make_creation("xyz-789", "Cool Mod", "Coder", "3.0")]
    out_path = _run_export(tmp_path, creations, suffix=".txt")

    content = out_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # Header row should include all 6 columns
    header_cells = [c.strip() for c in lines[0].split("|") if c.strip()]
    assert header_cells == ["#", "Content ID", "Name", "Author", "Installed Version", "Date"]

    # Data row
    data_cells = [c.strip() for c in lines[2].split("|") if c.strip()]
    assert data_cells[1] == "xyz-789"
    assert data_cells[2] == "Cool Mod"


def test_csv_and_markdown_have_same_columns(tmp_path):
    """Parity check: both formats must produce identical column sets."""
    creations = [_make_creation("id-a", "Mod", "Dev", "1.0")]
    md_dir = tmp_path / "md"
    md_dir.mkdir()

    csv_path = _run_export(tmp_path, creations, suffix=".csv")
    md_path = _run_export(md_dir, creations, suffix=".txt")

    with open(csv_path, newline="", encoding="utf-8") as f:
        csv_headers = next(csv.reader(f))

    md_content = md_path.read_text(encoding="utf-8")
    md_headers = [c.strip() for c in md_content.split("\n")[0].split("|") if c.strip()]

    assert csv_headers == md_headers
