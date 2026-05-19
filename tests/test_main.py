from unittest.mock import MagicMock, patch

import main


def test_force_write_bypasses_dedup_and_writes_records():
    repo = {
        "rank": 1,
        "name": "owner/repo",
        "description": "desc",
        "stars": 123,
        "forks": 45,
        "language": "Python",
        "url": "https://github.com/owner/repo",
        "created_at": "2026-05-15T00:00:00Z",
    }

    dedup = MagicMock()
    dedup.get_first_seen.return_value = "2026-05-15"
    feishu = MagicMock()
    feishu.get_or_create_table.return_value = "tbl123"

    with patch("sys.argv", ["main.py", "--top", "1", "--force-write"]):
        with patch("main.fetch_top_repos", return_value=[repo]):
            with patch("main.DedupState", return_value=dedup):
                with patch("main.FeishuClient", return_value=feishu):
                    with patch("main.fetch_readme", return_value="# README"):
                        with patch("main.generate_repo_content", return_value={"仓库解读": "解读", "快速上手": "上手", "推荐初稿": "推荐初稿内容"}):
                            main.main()

    dedup.check_and_update.assert_not_called()
    feishu.ensure_fields.assert_called_once_with("tbl123", ["仓库解读", "快速上手", "推荐初稿", "入池状态", "选题池记录"])
    feishu.upsert_record.assert_called_once()
    fields = feishu.upsert_record.call_args.args[1]
    assert fields["推荐初稿"] == "推荐初稿内容"
    assert fields["入池状态"] == "未处理"


def test_update_flow_preserves_existing_pool_status():
    repo = {
        "rank": 1,
        "name": "owner/repo",
        "description": "desc",
        "stars": 1234,
        "forks": 45,
        "language": "Python",
        "url": "https://github.com/owner/repo",
        "created_at": "2026-05-15T00:00:00Z",
    }

    dedup = MagicMock()
    dedup.get_stars.return_value = 1000
    dedup.check_and_update.return_value = "update"
    dedup.get_first_seen.return_value = "2026-05-15"
    dedup.is_loaded_from_file.return_value = True
    feishu = MagicMock()
    feishu.get_or_create_table.return_value = "tbl123"
    feishu.find_record_id.return_value = "rec123"

    with patch("sys.argv", ["main.py", "--top", "1"]):
        with patch("main.fetch_top_repos", return_value=[repo]):
            with patch("main.DedupState", return_value=dedup):
                with patch("main.FeishuClient", return_value=feishu):
                    with patch("main.fetch_readme", return_value="# README"):
                        with patch("main.generate_repo_content", return_value={"仓库解读": "解读", "快速上手": "上手", "推荐初稿": "推荐初稿内容"}):
                            main.main()

    feishu.find_record_id.assert_called_once_with("tbl123", "https://github.com/owner/repo")
    fields = feishu.upsert_record.call_args.args[1]
    assert "入池状态" not in fields


def test_debug_filter_prints_excluded_reasons():
    kept_repo = {
        "rank": 1,
        "name": "good/tool",
        "description": "desc",
        "stars": 123,
        "forks": 45,
        "language": "Python",
        "url": "https://github.com/good/tool",
        "created_at": "2026-05-15T00:00:00Z",
    }

    with patch("sys.argv", ["main.py", "--top", "1", "--dry-run", "--debug-filter"]):
        with patch("main.fetch_top_repos_with_debug", return_value=(
            [kept_repo],
            [{"name": "bad/gta-mod-menu", "reason": "game=gta, cheat=mod menu"}],
        )):
            with patch("main.print_repos") as mock_print_repos:
                with patch.object(main.console, "print") as mock_console_print:
                    main.main()

    mock_print_repos.assert_called_once()
    rendered = "\n".join(str(call.args[0]) for call in mock_console_print.call_args_list if call.args)
    assert "过滤明细" in rendered
    assert "bad/gta-mod-menu" in rendered
    assert "game=gta, cheat=mod menu" in rendered
