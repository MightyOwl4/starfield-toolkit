"""Tests for the TES4 binary header parser."""
import struct

from load_order_sorter.tes4_parser import (
    build_master_map,
    filter_base_game_masters,
    parse_masters,
)


def _make_mast_subrecord(name: str) -> bytes:
    """Build a MAST subrecord: 4-byte type + 2-byte size + null-terminated string."""
    encoded = name.encode("utf-8") + b"\x00"
    return b"MAST" + struct.pack("<H", len(encoded)) + encoded


def _make_data_subrecord() -> bytes:
    """Build a DATA subrecord (8 bytes of zeros, follows each MAST)."""
    return b"DATA" + struct.pack("<H", 8) + b"\x00" * 8


def _make_hedr_subrecord() -> bytes:
    """Build a minimal HEDR subrecord (12 bytes)."""
    return b"HEDR" + struct.pack("<H", 12) + b"\x00" * 12


def _make_tes4_file(*master_names: str) -> bytes:
    """Build a minimal TES4 file with the given master names."""
    # Build subrecords
    subrecords = _make_hedr_subrecord()
    for name in master_names:
        subrecords += _make_mast_subrecord(name)
        subrecords += _make_data_subrecord()

    # TES4 record header: type(4) + data_size(4) + flags(4) + form_id(4) + vc(8) = 24
    header = b"TES4" + struct.pack("<I", len(subrecords)) + b"\x00" * 16
    return header + subrecords


# --- parse_masters tests ---


def test_parse_single_master(tmp_path):
    f = tmp_path / "test.esm"
    f.write_bytes(_make_tes4_file("Starfield.esm"))
    assert parse_masters(f) == ["Starfield.esm"]


def test_parse_multiple_masters(tmp_path):
    f = tmp_path / "test.esm"
    f.write_bytes(_make_tes4_file("Starfield.esm", "SFBGS004.esm", "MyMod.esm"))
    assert parse_masters(f) == ["Starfield.esm", "SFBGS004.esm", "MyMod.esm"]


def test_parse_empty_file(tmp_path):
    f = tmp_path / "test.esm"
    f.write_bytes(b"")
    assert parse_masters(f) == []


def test_parse_too_small_file(tmp_path):
    f = tmp_path / "test.esm"
    f.write_bytes(b"TES4" + b"\x00" * 10)
    assert parse_masters(f) == []


def test_parse_non_tes4_file(tmp_path):
    f = tmp_path / "test.esm"
    f.write_bytes(b"GRUP" + b"\x00" * 20)
    assert parse_masters(f) == []


def test_parse_missing_file(tmp_path):
    f = tmp_path / "nonexistent.esm"
    assert parse_masters(f) == []


def test_parse_no_masters(tmp_path):
    """TES4 record with HEDR but no MAST subrecords."""
    subrecords = _make_hedr_subrecord()
    header = b"TES4" + struct.pack("<I", len(subrecords)) + b"\x00" * 16
    f = tmp_path / "test.esm"
    f.write_bytes(header + subrecords)
    assert parse_masters(f) == []


# --- filter_base_game_masters tests ---


def test_filter_removes_starfield_esm():
    result = filter_base_game_masters(["Starfield.esm", "MyMod.esm"])
    assert result == ["MyMod.esm"]


def test_filter_removes_sfbgs_pattern():
    masters = ["SFBGS004.esm", "sfbgs007.esm", "SFBGS999.esm", "MyMod.esm"]
    result = filter_base_game_masters(masters)
    assert result == ["MyMod.esm"]


def test_filter_removes_known_base_game():
    masters = [
        "Starfield.esm",
        "BlueprintShips-Starfield.esm",
        "Starfield - Localization.esm",
        "Constellation.esm",
        "OldMars.esm",
        "CommunityMod.esm",
    ]
    result = filter_base_game_masters(masters)
    assert result == ["CommunityMod.esm"]


def test_filter_case_insensitive():
    result = filter_base_game_masters(["STARFIELD.ESM", "mymod.esm"])
    assert result == ["mymod.esm"]


def test_filter_empty_list():
    assert filter_base_game_masters([]) == []


def test_filter_all_base_game():
    result = filter_base_game_masters(["Starfield.esm", "SFBGS004.esm"])
    assert result == []


# --- build_master_map tests ---


def test_build_master_map_basic(tmp_path):
    # Create two plugin files: ModB depends on ModA
    (tmp_path / "ModA.esm").write_bytes(_make_tes4_file("Starfield.esm"))
    (tmp_path / "ModB.esm").write_bytes(
        _make_tes4_file("Starfield.esm", "ModA.esm")
    )

    plugin_files = {"ModA.esm": "id-a", "ModB.esm": "id-b"}
    result = build_master_map(tmp_path, plugin_files)

    assert "ModB.esm" in result
    assert result["ModB.esm"] == ["ModA.esm"]
    # ModA only has Starfield.esm (base game), so no entry
    assert "ModA.esm" not in result


def test_build_master_map_filters_non_installed(tmp_path):
    (tmp_path / "ModA.esm").write_bytes(
        _make_tes4_file("Starfield.esm", "NotInstalled.esm")
    )

    plugin_files = {"ModA.esm": "id-a"}
    result = build_master_map(tmp_path, plugin_files)
    assert result == {}  # NotInstalled.esm is not in plugin_files


def test_build_master_map_chain(tmp_path):
    (tmp_path / "Base.esm").write_bytes(_make_tes4_file("Starfield.esm"))
    (tmp_path / "Middle.esm").write_bytes(
        _make_tes4_file("Starfield.esm", "Base.esm")
    )
    (tmp_path / "Top.esm").write_bytes(
        _make_tes4_file("Starfield.esm", "Base.esm", "Middle.esm")
    )

    plugin_files = {
        "Base.esm": "id-1",
        "Middle.esm": "id-2",
        "Top.esm": "id-3",
    }
    result = build_master_map(tmp_path, plugin_files)
    assert result["Middle.esm"] == ["Base.esm"]
    assert set(result["Top.esm"]) == {"Base.esm", "Middle.esm"}


def test_build_master_map_missing_file(tmp_path):
    # Plugin listed but file doesn't exist on disk
    plugin_files = {"Missing.esm": "id-x"}
    result = build_master_map(tmp_path, plugin_files)
    assert result == {}


def test_build_master_map_case_insensitive_lookup(tmp_path):
    (tmp_path / "mymod.esm").write_bytes(_make_tes4_file("Starfield.esm"))
    (tmp_path / "Addon.esm").write_bytes(
        _make_tes4_file("Starfield.esm", "MyMod.esm")  # different case
    )

    plugin_files = {"mymod.esm": "id-1", "Addon.esm": "id-2"}
    result = build_master_map(tmp_path, plugin_files)
    assert result["Addon.esm"] == ["mymod.esm"]  # resolved to canonical case
