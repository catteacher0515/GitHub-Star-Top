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
    feishu.upsert_record.assert_called_once()
    fields = feishu.upsert_record.call_args.args[1]
    assert fields["推荐初稿"] == "推荐初稿内容"
