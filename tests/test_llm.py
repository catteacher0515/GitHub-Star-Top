import pytest
from unittest.mock import patch, MagicMock
from llm import generate_repo_content


def _mock_resp(content: str):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_generate_returns_both_fields():
    mock_content = "【仓库解读】\n这是一个很棒的工具。\n【快速上手】\n1. 安装 2. 运行"
    with patch("llm.requests.post", return_value=_mock_resp(mock_content)):
        result = generate_repo_content(
            name="owner/repo",
            description="A cool tool",
            language="Python",
            readme="# Hello\nThis is a tool.",
        )
    assert "仓库解读" in result
    assert "快速上手" in result


def test_generate_retries_on_failure():
    mock_ok = _mock_resp("【仓库解读】\n好用。\n【快速上手】\n直接用。")
    mock_fail = MagicMock()
    mock_fail.raise_for_status.side_effect = Exception("500")
    with patch("llm.requests.post", side_effect=[mock_fail, mock_ok]):
        result = generate_repo_content(
            name="owner/repo",
            description="A tool",
            language="Python",
            readme="",
        )
    assert "仓库解读" in result


def test_generate_returns_empty_on_double_failure():
    mock_fail = MagicMock()
    mock_fail.raise_for_status.side_effect = Exception("500")
    with patch("llm.requests.post", side_effect=[mock_fail, mock_fail]):
        result = generate_repo_content(
            name="owner/repo",
            description="A tool",
            language="Python",
            readme="",
        )
    assert result == {"仓库解读": "", "快速上手": ""}
