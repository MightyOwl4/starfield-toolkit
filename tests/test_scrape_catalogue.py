"""Tests for the enumerate_creations API function and scrape_catalogue CLI."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from bethesda_creations._api import enumerate_creations


def _mock_client(response_data: dict, status_code: int = 200):
    """Create a mock httpx.Client that returns the given response."""
    mock = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response
        )
    mock.get.return_value = mock_response
    return mock


def _make_api_response(items: list, total: int) -> dict:
    return {
        "platform": {
            "response": {
                "data": items,
                "total": total,
                "page": 1,
                "size": 20,
            }
        }
    }


def _make_creation(content_id: str, title: str = "Test") -> dict:
    return {
        "content_id": content_id,
        "title": title,
        "description": f"Description for {title}",
        "overview": "",
        "author_displayname": "Author",
        "categories": ["Gear"],
        "achievement_friendly": False,
        "catalog_info": [],
        "release_notes": [],
        "required_mods": [],
    }


# --- enumerate_creations tests ---


def test_enumerate_creations_returns_items_and_total():
    items = [{"content_id": "abc", "title": "Test"}]
    client = _mock_client(_make_api_response(items, 100))
    result_items, total = enumerate_creations(client, page=1, size=20)
    assert result_items == items
    assert total == 100
    client.get.assert_called_once()
    call_kwargs = client.get.call_args
    assert call_kwargs[1]["params"]["product"] == "GENESIS"
    assert call_kwargs[1]["params"]["page"] == 1


def test_enumerate_creations_empty_results():
    client = _mock_client(_make_api_response([], 0))
    items, total = enumerate_creations(client, page=1)
    assert items == []
    assert total == 0


def test_enumerate_creations_http_error():
    client = _mock_client({}, status_code=500)
    with pytest.raises(httpx.HTTPStatusError):
        enumerate_creations(client, page=1)


def test_enumerate_creations_pagination():
    page1_items = [{"content_id": f"id-{i}"} for i in range(20)]
    page2_items = [{"content_id": f"id-{i}"} for i in range(20, 25)]

    mock = MagicMock(spec=httpx.Client)
    responses = [
        MagicMock(
            status_code=200,
            json=MagicMock(return_value=_make_api_response(page1_items, 25)),
            raise_for_status=MagicMock(),
        ),
        MagicMock(
            status_code=200,
            json=MagicMock(return_value=_make_api_response(page2_items, 25)),
            raise_for_status=MagicMock(),
        ),
    ]
    mock.get.side_effect = responses

    items1, total1 = enumerate_creations(mock, page=1)
    items2, total2 = enumerate_creations(mock, page=2)
    assert len(items1) == 20
    assert len(items2) == 5
    assert total1 == 25


# --- scrape_catalogue CLI tests ---


def _mock_enumerate(items_per_page: list[list[dict]], total: int):
    """Create a side_effect for enumerate_creations that returns pages."""
    pages = iter(items_per_page)
    def side_effect(client, page=1, size=20):
        try:
            return next(pages), total
        except StopIteration:
            return [], total
    return side_effect


@patch("scrape_catalogue.fetch_bnet_key", return_value="fake-key")
@patch("scrape_catalogue.enumerate_creations")
@patch("scrape_catalogue.httpx.Client")
def test_dry_run_reports_count(mock_client_cls, mock_enumerate, mock_key, capsys):
    from scrape_catalogue import run

    items = [_make_creation(f"id-{i}") for i in range(5)]
    mock_enumerate.return_value = (items, 42)
    mock_client_cls.return_value = MagicMock()

    code = run(["--dry-run"])
    assert code == 0
    captured = capsys.readouterr()
    assert "42" in captured.out


@patch("scrape_catalogue.fetch_bnet_key", return_value="fake-key")
@patch("scrape_catalogue.enumerate_creations")
@patch("scrape_catalogue.httpx.Client")
@patch("scrape_catalogue.save_catalogue")
@patch("scrape_catalogue.load_catalogue", return_value={})
def test_max_entries_stops_after_limit(
    mock_load, mock_save, mock_client_cls, mock_enumerate, mock_key, capsys
):
    from scrape_catalogue import run

    items = [_make_creation(f"id-{i}") for i in range(10)]
    mock_enumerate.return_value = (items, 100)
    mock_client_cls.return_value = MagicMock()

    code = run(["--max-entries", "3"])
    assert code == 1  # partial completion
    # save_catalogue should have been called with 3 new entries
    saved = mock_save.call_args[0][0]
    assert len(saved) == 3


@patch("scrape_catalogue.fetch_bnet_key", return_value="fake-key")
@patch("scrape_catalogue.enumerate_creations")
@patch("scrape_catalogue.httpx.Client")
@patch("scrape_catalogue.save_catalogue")
@patch("scrape_catalogue.load_catalogue")
def test_resume_skips_existing(
    mock_load, mock_save, mock_client_cls, mock_enumerate, mock_key, capsys
):
    from scrape_catalogue import run

    existing = {"id-0": {"title": "Existing"}, "id-1": {"title": "Existing2"}}
    mock_load.return_value = existing.copy()
    items = [_make_creation(f"id-{i}") for i in range(5)]
    mock_enumerate.side_effect = [(items, 5), ([], 5)]
    mock_client_cls.return_value = MagicMock()

    code = run([])
    assert code == 0
    saved = mock_save.call_args[0][0]
    # Should have 5 entries total (2 existing + 3 new)
    assert len(saved) == 5
    # Existing entries preserved
    assert saved["id-0"]["title"] == "Existing"


@patch("scrape_catalogue.fetch_bnet_key", return_value="fake-key")
@patch("scrape_catalogue.enumerate_creations")
@patch("scrape_catalogue.httpx.Client")
@patch("scrape_catalogue.save_catalogue")
@patch("scrape_catalogue.load_catalogue", return_value={})
def test_force_refreshes_existing(
    mock_load, mock_save, mock_client_cls, mock_enumerate, mock_key, capsys
):
    from scrape_catalogue import run

    mock_load.return_value = {"id-0": {"title": "Old"}}
    items = [_make_creation("id-0", title="New")]
    mock_enumerate.side_effect = [(items, 1), ([], 1)]
    mock_client_cls.return_value = MagicMock()

    code = run(["--force"])
    assert code == 0
    saved = mock_save.call_args[0][0]
    assert saved["id-0"]["title"] == "New"


@patch("scrape_catalogue.fetch_bnet_key", return_value="fake-key")
@patch("scrape_catalogue._fetch_page_with_retry")
@patch("scrape_catalogue.httpx.Client")
@patch("scrape_catalogue.save_catalogue")
@patch("scrape_catalogue.load_catalogue", return_value={})
def test_429_terminates_session(
    mock_load, mock_save, mock_client_cls, mock_fetch, mock_key, capsys
):
    from scrape_catalogue import run, RateLimitExhausted

    mock_fetch.side_effect = RateLimitExhausted("rate limited")
    mock_client_cls.return_value = MagicMock()

    code = run([])
    assert code == 1  # partial completion
    mock_save.assert_called()  # progress saved


@patch("scrape_catalogue.fetch_bnet_key", return_value="fake-key")
@patch("scrape_catalogue.enumerate_creations")
@patch("scrape_catalogue.httpx.Client")
@patch("scrape_catalogue.save_catalogue")
@patch("scrape_catalogue.load_catalogue", return_value={})
def test_full_run_multiple_pages(
    mock_load, mock_save, mock_client_cls, mock_enumerate, mock_key, capsys
):
    from scrape_catalogue import run

    page1 = [_make_creation(f"id-{i}") for i in range(20)]
    page2 = [_make_creation(f"id-{i}") for i in range(20, 25)]
    mock_enumerate.side_effect = [(page1, 25), (page2, 25)]
    mock_client_cls.return_value = MagicMock()

    code = run([])
    assert code == 0
    saved = mock_save.call_args[0][0]
    assert len(saved) == 25
