import json
import os
import pytest
from unittest.mock import patch
from dedup import DedupState, DEDUP_FILE


@pytest.fixture(autouse=True)
def clean_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    yield
    if os.path.exists(DEDUP_FILE):
        os.remove(DEDUP_FILE)


def test_new_repo_is_added():
    state = DedupState()
    result = state.check_and_update("https://github.com/a/b", 1000, "2026-W13")
    assert result == "new"


def test_existing_repo_no_change_is_skipped():
    state = DedupState()
    state.check_and_update("https://github.com/a/b", 1000, "2026-W13")
    result = state.check_and_update("https://github.com/a/b", 1200, "2026-W13")
    assert result == "skip"


def test_existing_repo_large_increase_is_updated():
    state = DedupState()
    state.check_and_update("https://github.com/a/b", 1000, "2026-W13")
    result = state.check_and_update("https://github.com/a/b", 1600, "2026-W13")
    assert result == "update"


def test_weekly_reset():
    state = DedupState()
    state.check_and_update("https://github.com/a/b", 1000, "2026-W13")
    result = state.check_and_update("https://github.com/a/b", 1000, "2026-W14")
    assert result == "new"


def test_state_persists_to_file():
    state = DedupState()
    state.check_and_update("https://github.com/a/b", 1000, "2026-W13")
    state.save()
    state2 = DedupState()
    result = state2.check_and_update("https://github.com/a/b", 1200, "2026-W13")
    assert result == "skip"


def test_first_seen_persists_across_weeks():
    state = DedupState()
    state.check_and_update("https://github.com/a/b", 1000, "2026-W13")
    state.save()
    state2 = DedupState()
    # 新的一周，仓库重新出现
    state2.check_and_update("https://github.com/a/b", 1200, "2026-W14")
    first_seen = state2.get_first_seen("https://github.com/a/b")
    # first_seen 应该是 W13 时记录的日期，不是 W14
    assert first_seen is not None
    assert len(first_seen) == 10  # YYYY-MM-DD 格式
