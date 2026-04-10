"""Tests for the description dependency parser."""
import pytest
from unittest.mock import MagicMock

from description_parser.analyzer import (
    _recover_truncated_deps,
    analyze_creation,
    build_reference_list,
    filter_candidates,
    generate_rulebook,
    process_candidates,
)
from description_parser.report import generate_report


def _make_entry(title, description="", required_mods=None, plugin_summary=None):
    return {
        "title": title,
        "description": description,
        "required_mods": required_mods or [],
        "plugin_summary": plugin_summary,
    }


# --- filter_candidates ---


def test_filter_patch_in_title():
    catalogue = {
        "a": _make_entry("My Patch", "fixes things"),
        "b": _make_entry("Cool Mod", "does stuff"),
    }
    result = filter_candidates(catalogue)
    assert len(result) == 1
    assert result[0]["title"] == "My Patch"


def test_filter_required_mods():
    catalogue = {
        "a": _make_entry("Cool Mod", "desc", required_mods=["dep-id"]),
    }
    result = filter_candidates(catalogue)
    assert len(result) == 1


def test_filter_multiple_keywords():
    catalogue = {
        "a": _make_entry("Compatibility Fix", "desc"),
        "b": _make_entry("Cool Addon", "desc"),
        "c": _make_entry("Just a Mod", "desc"),
    }
    result = filter_candidates(catalogue)
    assert len(result) == 2


def test_filter_empty_description_skipped():
    catalogue = {
        "a": _make_entry("My Patch", ""),
    }
    result = filter_candidates(catalogue)
    assert len(result) == 0


def test_filter_empty_catalogue():
    assert filter_candidates({}) == []


def test_filter_extracts_plugin_file():
    catalogue = {
        "a": _make_entry(
            "My Patch", "desc",
            plugin_summary={"Files": ["Data\\MyPatch.esm", "Data\\MyPatch - Main.ba2"]},
        ),
    }
    result = filter_candidates(catalogue)
    assert result[0]["plugin_file"] == "MyPatch.esm"


# --- build_reference_list ---


def test_reference_list_includes_filenames():
    catalogue = {
        "a": _make_entry(
            "Cool Mod",
            plugin_summary={"Files": ["Data\\CoolMod.esm"]},
        ),
    }
    ref = build_reference_list(catalogue)
    assert "CoolMod.esm = Cool Mod" in ref


def test_reference_list_no_summary_excluded():
    catalogue = {
        "a": _make_entry("Title Only"),
    }
    ref = build_reference_list(catalogue)
    assert ref == ""  # no plugin files = excluded


def test_reference_list_sorted():
    catalogue = {
        "z": _make_entry("Zebra Mod", plugin_summary={"Files": ["Data\\Zebra.esm"]}),
        "a": _make_entry("Alpha Mod", plugin_summary={"Files": ["Data\\Alpha.esm"]}),
    }
    ref = build_reference_list(catalogue)
    lines = ref.strip().split("\n")
    assert lines[0].startswith("Alpha")
    assert lines[1].startswith("Zebra")


# --- analyze_creation (mocked) ---


def test_analyze_creation_parses_response():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"dependencies": [{"source_plugin": "A.esm", "load_after": "B.esm", "matched_creation": "Mod B", "confidence": "high", "source_text": "load after B", "reasoning": "explicit"}]}')]
    mock_client.messages.create.return_value = mock_response

    deps = analyze_creation(mock_client, "desc", "ref list", "Mod A", "A.esm")
    assert len(deps) == 1
    assert deps[0]["source_plugin"] == "A.esm"
    assert deps[0]["load_after"] == "B.esm"


def test_analyze_creation_empty_deps():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"dependencies": []}')]
    mock_client.messages.create.return_value = mock_response

    deps = analyze_creation(mock_client, "no deps here", "ref list", "Mod", "mod.esm")
    assert deps == []


def test_analyze_creation_malformed_json():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="This is not JSON")]
    mock_client.messages.create.return_value = mock_response

    deps = analyze_creation(mock_client, "desc", "ref", "Mod", "mod.esm")
    assert deps == []


class _FakeAPIError(Exception):
    """Mimics anthropic.APIStatusError — has a status_code attribute."""
    def __init__(self, status_code, message="api error"):
        super().__init__(message)
        self.status_code = status_code


def test_analyze_creation_fatal_400_propagates(monkeypatch):
    """A 400 (e.g. depleted credits) must halt the run, NOT return []."""
    # No real sleeps in the retry path
    monkeypatch.setattr("description_parser.analyzer.time.sleep", lambda *_a, **_kw: None)

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = _FakeAPIError(400, "credit balance too low")

    with pytest.raises(_FakeAPIError) as exc_info:
        analyze_creation(mock_client, "desc", "ref", "Mod", "mod.esm")
    assert exc_info.value.status_code == 400
    # Must NOT have retried — fatal errors should fail fast
    assert mock_client.messages.create.call_count == 1


def test_analyze_creation_fatal_401_propagates(monkeypatch):
    """A 401 (bad auth) must also halt immediately."""
    monkeypatch.setattr("description_parser.analyzer.time.sleep", lambda *_a, **_kw: None)
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = _FakeAPIError(401, "auth")
    with pytest.raises(_FakeAPIError):
        analyze_creation(mock_client, "desc", "ref", "Mod", "mod.esm")
    assert mock_client.messages.create.call_count == 1


def test_analyze_creation_transient_error_still_retries(monkeypatch):
    """Non-fatal errors (no status_code, or 5xx) keep the retry behaviour."""
    monkeypatch.setattr("description_parser.analyzer.time.sleep", lambda *_a, **_kw: None)
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = RuntimeError("transient")
    deps = analyze_creation(
        mock_client, "desc", "ref", "Mod", "mod.esm", max_retries=2,
    )
    assert deps == []
    # Initial + 2 retries = 3 calls
    assert mock_client.messages.create.call_count == 3


def test_process_candidates_does_not_save_on_fatal_error(monkeypatch):
    """A fatal API error must propagate out of process_candidates BEFORE
    save_callback runs — otherwise the failing creation gets baked into the
    resume cache and skipped on subsequent runs."""
    monkeypatch.setattr("description_parser.analyzer.time.sleep", lambda *_a, **_kw: None)

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = _FakeAPIError(400, "credit balance too low")

    saved = []

    def _save(results):
        saved.append(list(results))

    candidates = [
        {"content_id": "id-1", "title": "Patch A", "description": "desc",
         "plugin_file": "a.esm"},
    ]

    with pytest.raises(_FakeAPIError):
        process_candidates(
            mock_client, candidates, "ref list", save_callback=_save,
        )

    # Crucial: save_callback must NOT have been called — otherwise the
    # creation would be marked as processed and skipped on resume.
    assert saved == []


def test_analyze_creation_handles_code_block():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='```json\n{"dependencies": [{"source_plugin": "X.esm", "load_after": "Y.esm", "matched_creation": "Y", "confidence": "high", "source_text": "test", "reasoning": "test"}]}\n```')]
    mock_client.messages.create.return_value = mock_response

    deps = analyze_creation(mock_client, "desc", "ref", "X", "X.esm")
    assert len(deps) == 1


# --- _recover_truncated_deps ---


def test_recover_truncated_mid_object():
    """Response truncated in the middle of the 3rd dependency."""
    text = '''{"dependencies": [
        {"source_plugin": "A.esm", "load_after": "B.esm", "confidence": "high", "reasoning": "explicit"},
        {"source_plugin": "A.esm", "load_after": "C.esm", "confidence": "high", "reasoning": "explicit"},
        {"source_plugin": "A.esm", "load_after": "D.esm", "confidence": "me'''
    recovered = _recover_truncated_deps(text)
    assert len(recovered) == 2
    assert recovered[0]["source_plugin"] == "A.esm"
    assert recovered[0]["load_after"] == "B.esm"
    assert recovered[1]["load_after"] == "C.esm"


def test_recover_truncated_complete_but_unterminated_array():
    """All objects complete but the array is not closed."""
    text = '{"dependencies": [{"source_plugin": "A.esm", "load_after": "B.esm"}, {"source_plugin": "A.esm", "load_after": "C.esm"}'
    recovered = _recover_truncated_deps(text)
    assert len(recovered) == 2


def test_recover_no_dependencies_key():
    assert _recover_truncated_deps("some random text") == []


def test_recover_empty_array():
    text = '{"dependencies": []'
    assert _recover_truncated_deps(text) == []


def test_recover_handles_escaped_quotes_in_strings():
    """String contains braces and quotes that could confuse the parser."""
    text = '{"dependencies": [{"source_plugin": "A.esm", "load_after": "B.esm", "source_text": "quote with \\"braces {}\\" inside"}]}'
    recovered = _recover_truncated_deps(text)
    assert len(recovered) == 1
    assert 'braces' in recovered[0]["source_text"]


# --- generate_rulebook ---


def test_rulebook_from_results():
    results = [{
        "content_id": "abc",
        "title": "Patch",
        "plugin_file": "Patch.esm",
        "dependencies": [
            {"source_plugin": "Patch.esm", "load_after": "Base.esm",
             "confidence": "high", "source_text": "load order", "reasoning": "explicit"},
        ],
    }]
    book = generate_rulebook(results)
    assert book["name"] == "Auto-detected Patch Order Rules"
    assert len(book["rules"]) == 1
    assert book["rules"][0]["plugin"] == "Patch.esm"
    assert book["rules"][0]["load_after"] == ["Base.esm"]


def test_rulebook_deduplicates():
    results = [
        {"content_id": "a", "title": "A", "plugin_file": "A.esm",
         "dependencies": [
             {"source_plugin": "A.esm", "load_after": "B.esm", "confidence": "high",
              "source_text": "", "reasoning": ""},
         ]},
        {"content_id": "a2", "title": "A2", "plugin_file": "A.esm",
         "dependencies": [
             {"source_plugin": "A.esm", "load_after": "B.esm", "confidence": "medium",
              "source_text": "", "reasoning": ""},
         ]},
    ]
    book = generate_rulebook(results)
    assert len(book["rules"]) == 1  # deduplicated


def test_rulebook_empty_results():
    book = generate_rulebook([])
    assert book["rules"] == []


def test_rulebook_skips_non_dict_dependencies():
    """Older cache files may contain malformed entries (e.g. bare strings).
    generate_rulebook must not crash on them."""
    results = [{
        "content_id": "abc",
        "title": "Patch",
        "plugin_file": "Patch.esm",
        "dependencies": [
            "junk string from a bad LLM response",
            None,
            42,
            {"source_plugin": "Patch.esm", "load_after": "Base.esm",
             "confidence": "high", "source_text": "", "reasoning": ""},
        ],
    }]
    book = generate_rulebook(results)
    assert len(book["rules"]) == 1
    assert book["rules"][0]["plugin"] == "Patch.esm"


def test_analyze_creation_filters_non_dict_deps():
    """LLM returning a malformed dependencies array is sanitised before save."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=(
        '{"dependencies": ['
        '"some bare string", '
        '{"source_plugin": "A.esm", "load_after": "B.esm", '
        '"confidence": "high", "source_text": "x", "reasoning": "y"}, '
        'null'
        ']}'
    ))]
    mock_client.messages.create.return_value = mock_response

    deps = analyze_creation(mock_client, "desc", "ref", "Mod", "mod.esm")
    assert len(deps) == 1
    assert deps[0]["source_plugin"] == "A.esm"


# --- generate_report ---


def test_report_contains_sections(tmp_path):
    results = [{
        "content_id": "abc",
        "title": "Test Patch",
        "plugin_file": "test.esm",
        "dependencies": [
            {"source_plugin": "test.esm", "load_after": "base.esm",
             "matched_creation": "Base Mod", "confidence": "high",
             "source_text": "load after base", "reasoning": "explicit order"},
        ],
    }]
    report_path = tmp_path / "report.md"
    generate_report(results, report_path)

    content = report_path.read_text(encoding="utf-8")
    assert "High Confidence" in content
    assert "Test Patch" in content
    assert "Base Mod" in content
    assert "explicit order" in content


def test_report_empty_results(tmp_path):
    report_path = tmp_path / "report.md"
    generate_report([], report_path)
    content = report_path.read_text(encoding="utf-8")
    assert "**Total rules detected**: 0" in content
