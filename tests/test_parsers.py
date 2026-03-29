from pathlib import Path

from starfield_tool.parsers import parse_plugins_txt, parse_content_catalog

FIXTURES = Path(__file__).parent / "fixtures"


class TestParsePluginsTxt:
    def test_correct_order(self):
        entries = parse_plugins_txt(FIXTURES / "Plugins.txt")
        filenames = [e.filename for e in entries]
        assert filenames[0] == "Starfield.esm"
        assert filenames[-1] == "CreationClub01.esl"

    def test_active_detection(self):
        entries = parse_plugins_txt(FIXTURES / "Plugins.txt")
        # All *-prefixed are active
        starfield = entries[0]
        assert starfield.is_active is True
        # CreationClub01.esl has no * prefix
        cc01 = [e for e in entries if e.filename == "CreationClub01.esl"][0]
        assert cc01.is_active is False

    def test_position_assigned(self):
        entries = parse_plugins_txt(FIXTURES / "Plugins.txt")
        for i, entry in enumerate(entries):
            assert entry.position == i

    def test_comments_and_blanks_skipped(self, tmp_path):
        p = tmp_path / "Plugins.txt"
        p.write_text("# comment\n\n*Test.esm\n\n", encoding="utf-8")
        entries = parse_plugins_txt(p)
        assert len(entries) == 1
        assert entries[0].filename == "Test.esm"

    def test_empty_file(self, tmp_path):
        p = tmp_path / "Plugins.txt"
        p.write_text("", encoding="utf-8")
        entries = parse_plugins_txt(p)
        assert entries == []

    def test_missing_file(self, tmp_path):
        entries = parse_plugins_txt(tmp_path / "nonexistent.txt")
        assert entries == []


class TestParseContentCatalog:
    def test_extract_entries(self):
        entries = parse_content_catalog(FIXTURES / "ContentCatalog.txt")
        assert len(entries) == 4
        ids = {e.content_id for e in entries}
        assert "SFBGS007" in ids
        assert "CC01" in ids

    def test_fields_populated(self):
        entries = parse_content_catalog(FIXTURES / "ContentCatalog.txt")
        bgs007 = [e for e in entries if e.content_id == "SFBGS007"][0]
        assert bgs007.title == "Vulture's Roost"
        assert bgs007.version == "1.2.0"
        assert bgs007.timestamp is not None
        assert "SFBGS007.esm" in bgs007.files

    def test_missing_file(self, tmp_path):
        entries = parse_content_catalog(tmp_path / "nonexistent.txt")
        assert entries == []

    def test_malformed_file(self, tmp_path):
        p = tmp_path / "ContentCatalog.txt"
        p.write_text("not json at all", encoding="utf-8")
        entries = parse_content_catalog(p)
        assert entries == []
