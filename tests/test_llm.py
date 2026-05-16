import pytest
from unittest.mock import patch, MagicMock
from llm import generate_repo_content, format_for_feishu_cell


def _mock_resp(content: str):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": content}}]
    }
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def test_generate_returns_both_fields():
    mock_content = """【仓库解读】
这是一个很棒的工具。
【快速上手】
1. 安装 2. 运行
【推荐初稿】
项目名：owner/repo

中文定位：一个很好用的工具

它解决的问题：
帮你省时间。

你为什么这周选它：
因为适合新手先看一眼。

Star / Fork / 日期：
1.2k / 300 / 2026-05-15

优点标签：
适合小白、效率提升、值得收藏
"""
    with patch("llm.requests.post", return_value=_mock_resp(mock_content)):
        result = generate_repo_content(
            name="owner/repo",
            description="A cool tool",
            language="Python",
            readme="# Hello\nThis is a tool.",
            stars=1200,
            forks=300,
            created_at="2026-05-15",
        )
    assert "仓库解读" in result
    assert "快速上手" in result
    assert "推荐初稿" in result


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
            stars=1200,
            forks=300,
            created_at="2026-05-15",
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
            stars=1200,
            forks=300,
            created_at="2026-05-15",
        )
    assert result == {"仓库解读": "", "快速上手": "", "推荐初稿": ""}


def test_generate_formats_quick_start_for_feishu_readability():
    mock_content = """【仓库解读】
这是一个很棒的工具。
【快速上手】
**① 核心功能**
- 支持批量处理
- 支持自动导出
**② 上手步骤**
1. 安装依赖
2. 运行命令
【推荐初稿】
项目名：owner/repo

中文定位：一个很好用的工具

它解决的问题：
帮你省时间。
"""
    with patch("llm.requests.post", return_value=_mock_resp(mock_content)):
        result = generate_repo_content(
            name="owner/repo",
            description="A cool tool",
            language="Python",
            readme="# Hello\nThis is a tool.",
            stars=1200,
            forks=300,
            created_at="2026-05-15",
        )
    assert result["快速上手"] == "① 核心功能\n- 支持批量处理\n- 支持自动导出\n\n② 上手步骤\n1. 安装依赖\n2. 运行命令"


def test_format_for_feishu_cell_splits_dense_paragraphs():
    text = "第一句。第二句。第三句。"
    assert format_for_feishu_cell(text) == "第一句。\n第二句。\n第三句。"


def test_generate_formats_recommendation_draft_for_feishu_readability():
    mock_content = """【仓库解读】
这是一个很棒的工具。
【快速上手】
直接使用。
【推荐初稿】
项目名：owner/repo

中文定位：一个很好用的工具

它解决的问题：
帮你省时间，减少重复操作。

你为什么这周选它：
它不是最复杂的项目，但价值很直接。

Star / Fork / 日期：
1.2k / 300 / 2026-05-15

优点标签：
适合小白、效率提升、值得收藏
"""
    with patch("llm.requests.post", return_value=_mock_resp(mock_content)):
        result = generate_repo_content(
            name="owner/repo",
            description="A cool tool",
            language="Python",
            readme="# Hello\nThis is a tool.",
            stars=1200,
            forks=300,
            created_at="2026-05-15",
        )
    assert result["推荐初稿"] == """项目名：owner/repo

中文定位：一个很好用的工具

它解决的问题：
帮你省时间，减少重复操作。

你为什么这周选它：
它不是最复杂的项目，但价值很直接。

Star / Fork / 日期：
1.2k / 300 / 2026-05-15

优点标签：
适合小白、效率提升、值得收藏"""
