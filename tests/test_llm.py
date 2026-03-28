import pytest
from unittest.mock import patch, MagicMock
from llm import analyze_repo


def test_analyze_repo_success():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": '{"summary": "A cool lib", "quickstart": "pip install foo"}'}}]
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("llm.requests.post", return_value=mock_resp):
        result = analyze_repo("owner/repo", "This is a readme")
    assert result["summary"] == "A cool lib"
    assert result["quickstart"] == "pip install foo"


def test_analyze_repo_retry_on_failure():
    mock_fail = MagicMock()
    mock_fail.raise_for_status.side_effect = Exception("500")

    mock_ok = MagicMock()
    mock_ok.json.return_value = {
        "choices": [{"message": {"content": '{"summary": "Retry worked", "quickstart": "npm install"}'}}]
    }
    mock_ok.raise_for_status = MagicMock()

    with patch("llm.requests.post", side_effect=[mock_fail, mock_ok]):
        result = analyze_repo("owner/repo", "readme text")
    assert result["summary"] == "Retry worked"


def test_analyze_repo_all_fail():
    mock_fail = MagicMock()
    mock_fail.raise_for_status.side_effect = Exception("500")

    with patch("llm.requests.post", side_effect=[mock_fail, mock_fail]):
        result = analyze_repo("owner/repo", "readme text")
    assert result == {"summary": "", "quickstart": ""}


def test_analyze_repo_invalid_json():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "not valid json"}}]
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("llm.requests.post", return_value=mock_resp):
        result = analyze_repo("owner/repo", "readme text")
    assert result == {"summary": "", "quickstart": ""}
