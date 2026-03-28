import pytest
from unittest.mock import patch, MagicMock
from readme_fetcher import fetch_readme


def test_fetch_readme_success():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"content": "SGVsbG8gV29ybGQ=\n", "encoding": "base64"}
    mock_resp.raise_for_status = MagicMock()
    with patch("readme_fetcher.requests.get", return_value=mock_resp):
        result = fetch_readme("owner/repo")
    assert result == "Hello World"


def test_fetch_readme_not_found():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = Exception("404")
    with patch("readme_fetcher.requests.get", return_value=mock_resp):
        result = fetch_readme("owner/repo")
    assert result == ""


def test_fetch_readme_empty_token():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"content": "SGVsbG8=\n", "encoding": "base64"}
    mock_resp.raise_for_status = MagicMock()
    with patch("readme_fetcher.requests.get", return_value=mock_resp):
        with patch("readme_fetcher.GITHUB_TOKEN", ""):
            result = fetch_readme("owner/repo")
    assert result == "Hello"
