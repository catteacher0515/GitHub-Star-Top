from unittest.mock import MagicMock, patch

import main
from dedup import DedupState


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
    dedup.check_and_update.return_value = "new"
    dedup.has_seen.return_value = False
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


def test_main_aborts_before_writing_when_llm_generation_fails():
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
    dedup.check_and_update.return_value = "new"
    dedup.has_seen.return_value = False
    feishu = MagicMock()
    feishu.get_or_create_table.return_value = "tbl123"

    with patch("sys.argv", ["main.py", "--top", "1"]):
        with patch("main.fetch_top_repos", return_value=[repo]):
            with patch("main.DedupState", return_value=dedup):
                with patch("main.FeishuClient", return_value=feishu):
                    with patch("main.fetch_readme", return_value="# README"):
                        with patch("main.generate_repo_content", side_effect=RuntimeError("LLM 生成失败")):
                            with patch("sys.exit", side_effect=SystemExit) as mock_exit:
                                with patch.object(main.console, "print") as mock_print:
                                    try:
                                        main.main()
                                    except SystemExit:
                                        pass

    feishu.upsert_record.assert_not_called()
    mock_exit.assert_called_once_with(1)
    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "LLM 生成失败" in rendered


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


def test_min_new_target_fills_from_unseen_backlog():
    first_batch = [
        {
            "rank": 1,
            "name": "owner/seen-1",
            "description": "desc",
            "stars": 123,
            "forks": 45,
            "language": "Python",
            "url": "https://github.com/owner/seen-1",
            "created_at": "2026-05-15T00:00:00Z",
        },
        {
            "rank": 2,
            "name": "owner/seen-2",
            "description": "desc",
            "stars": 122,
            "forks": 44,
            "language": "Python",
            "url": "https://github.com/owner/seen-2",
            "created_at": "2026-05-15T00:00:00Z",
        },
    ]
    second_batch = [
        {
            "rank": 1,
            "name": "owner/seen-1",
            "description": "desc",
            "stars": 123,
            "forks": 45,
            "language": "Python",
            "url": "https://github.com/owner/seen-1",
            "created_at": "2026-05-15T00:00:00Z",
        },
        {
            "rank": 2,
            "name": "owner/seen-2",
            "description": "desc",
            "stars": 122,
            "forks": 44,
            "language": "Python",
            "url": "https://github.com/owner/seen-2",
            "created_at": "2026-05-15T00:00:00Z",
        },
        {
            "rank": 3,
            "name": "owner/new-1",
            "description": "desc",
            "stars": 121,
            "forks": 43,
            "language": "Python",
            "url": "https://github.com/owner/new-1",
            "created_at": "2026-05-15T00:00:00Z",
        },
        {
            "rank": 4,
            "name": "owner/new-2",
            "description": "desc",
            "stars": 120,
            "forks": 42,
            "language": "Python",
            "url": "https://github.com/owner/new-2",
            "created_at": "2026-05-15T00:00:00Z",
        },
    ]

    dedup = MagicMock()
    dedup.get_stars.side_effect = lambda url, week: {"https://github.com/owner/seen-1": 100, "https://github.com/owner/seen-2": 99}.get(url, 0)
    dedup.check_and_update.side_effect = ["skip", "skip", "new", "new"]
    dedup.get_first_seen.side_effect = lambda url: "2026-05-15"
    dedup.preview_action.side_effect = lambda url, stars, week: "skip" if url in {
        "https://github.com/owner/seen-1",
        "https://github.com/owner/seen-2",
    } else "new"
    dedup.has_seen.side_effect = lambda url: url in {
        "https://github.com/owner/seen-1",
        "https://github.com/owner/seen-2",
    }
    dedup.is_loaded_from_file.return_value = True
    feishu = MagicMock()
    feishu.get_or_create_table.return_value = "tbl123"

    with patch("sys.argv", ["main.py", "--top", "2", "--min-new", "2", "--dry-run"]):
        with patch("main.fetch_top_repos", side_effect=[first_batch, second_batch]) as mock_fetch:
            with patch("main.DedupState", return_value=dedup):
                with patch("main.FeishuClient", return_value=feishu):
                    with patch("main.fetch_readme"):
                        with patch("main.generate_repo_content"):
                            with patch.object(main.console, "print") as mock_print:
                                main.main()

    assert mock_fetch.call_count == 2
    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "开始补足到 2 条" in rendered
    assert "2 条" in rendered


def test_first_new_repo_counts_toward_min_new_with_real_dedup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    repo = {
        "rank": 1,
        "name": "owner/new-repo",
        "description": "desc",
        "stars": 123,
        "forks": 45,
        "language": "Python",
        "url": "https://github.com/owner/new-repo",
        "created_at": "2026-05-15T00:00:00Z",
    }

    dedup = DedupState()

    with patch("sys.argv", ["main.py", "--top", "1", "--min-new", "1", "--dry-run"]):
        with patch("main.fetch_top_repos", return_value=[repo]) as mock_fetch:
            with patch("main.DedupState", return_value=dedup):
                with patch.object(main.console, "print") as mock_print:
                    main.main()

    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "开始补足到 1 条" not in rendered
    assert "去重后待写入：1 条" in rendered
    assert mock_fetch.call_count == 1


def test_refill_fetch_failure_does_not_abort_run():
    repo = {
        "rank": 1,
        "name": "owner/seen-repo",
        "description": "desc",
        "stars": 123,
        "forks": 45,
        "language": "Python",
        "url": "https://github.com/owner/seen-repo",
        "created_at": "2026-05-15T00:00:00Z",
    }

    dedup = MagicMock()
    dedup.has_seen.return_value = True
    dedup.check_and_update.return_value = "skip"
    dedup.preview_action.return_value = "skip"

    with patch("sys.argv", ["main.py", "--top", "1", "--min-new", "1", "--dry-run"]):
        with patch("main.fetch_top_repos", side_effect=[[repo], RuntimeError("refill failed")]):
            with patch("main.DedupState", return_value=dedup):
                with patch.object(main.console, "print") as mock_print:
                    main.main()

    rendered = "\n".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "补位抓取失败" in rendered
    assert "refill failed" in rendered
    assert "dry-run 模式" in rendered
