# GitHub Star Tracker 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每天自动抓取 GitHub 热门仓库，去重后写入飞书多维表格，按周分表组织，支持手动触发。

**Architecture:** 现有 fetcher.py 负责抓取，新增 dedup.py 管理去重状态，新增 feishu.py 负责写入飞书多维表格，main.py 串联所有模块，GitHub Actions workflow 负责定时调度。去重状态通过 actions/cache 在每次运行间持久化。

**Tech Stack:** Python 3.11, requests, python-dotenv, pytest, GitHub Actions

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `dedup.py` | 新建 | 去重状态读写，周重置，star 涨幅检测 |
| `feishu.py` | 新建 | 飞书多维表格 API 封装，按周建表，写入记录 |
| `main.py` | 修改 | 串联 fetcher → dedup → feishu，加 --dry-run 参数 |
| `config.py` | 修改 | 新增飞书相关环境变量读取 |
| `requirements.txt` | 修改 | 无需新增依赖（requests 已有） |
| `.github/workflows/daily.yml` | 新建 | 定时 + 手动触发，缓存 dedup_state.json |
| `tests/test_dedup.py` | 新建 | dedup 模块单元测试 |
| `tests/test_feishu.py` | 新建 | feishu 模块单元测试（mock HTTP） |

---

## Task 1: 更新 config.py，加入飞书配置

**Files:**
- Modify: `config.py`

- [ ] **Step 1: 修改 config.py**

将 `config.py` 替换为以下内容：

```python
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID", "")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET", "")
FEISHU_BITABLE_APP_TOKEN = os.getenv("FEISHU_BITABLE_APP_TOKEN", "")
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

TIME_RANGES = {
    "today": 1,
    "weekly": 7,
    "monthly": 30,
}

def get_since_date(period: str) -> str:
    days = TIME_RANGES.get(period, 7)
    since = datetime.utcnow() - timedelta(days=days)
    return since.strftime("%Y-%m-%d")

def get_week_label() -> str:
    """返回当前周标签，格式 YYYY-WXX，如 2026-W13"""
    now = datetime.utcnow()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"
```

- [ ] **Step 2: 提交**

```bash
git add config.py
git commit -m "feat: add feishu config and week label helper"
```

---

## Task 2: 实现 dedup.py

**Files:**
- Create: `dedup.py`
- Create: `tests/test_dedup.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/test_dedup.py`：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/test_dedup.py -v
```

期望：`ImportError: No module named 'dedup'`

- [ ] **Step 3: 实现 dedup.py**

新建 `dedup.py`：

```python
import json
import os

DEDUP_FILE = "dedup_state.json"
STAR_INCREASE_THRESHOLD = 500


class DedupState:
    def __init__(self):
        self._data: dict = self._load()

    def _load(self) -> dict:
        if os.path.exists(DEDUP_FILE):
            with open(DEDUP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save(self):
        with open(DEDUP_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def check_and_update(self, url: str, stars: int, week: str) -> str:
        """
        返回值：
          "new"    — 本周首次出现，已写入
          "update" — 已存在但 star 涨幅 >= 阈值，已更新
          "skip"   — 已存在且涨幅不足，跳过
        """
        key = f"{week}:{url}"
        existing = self._data.get(key)

        if existing is None:
            self._data[key] = {"stars": stars, "first_seen": week}
            return "new"

        increase = stars - existing["stars"]
        if increase >= STAR_INCREASE_THRESHOLD:
            self._data[key]["stars"] = stars
            return "update"

        return "skip"

    def get_first_seen(self, url: str, week: str) -> str:
        key = f"{week}:{url}"
        return self._data.get(key, {}).get("first_seen", week)
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/test_dedup.py -v
```

期望：5 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add dedup.py tests/test_dedup.py
git commit -m "feat: add dedup module with weekly reset and star threshold"
```

---

## Task 3: 实现 feishu.py

**Files:**
- Create: `feishu.py`
- Create: `tests/test_feishu.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/test_feishu.py`：

```python
import pytest
from unittest.mock import patch, MagicMock
from feishu import FeishuClient


@pytest.fixture
def client():
    return FeishuClient(
        app_id="test_app_id",
        app_secret="test_app_secret",
        bitable_app_token="test_token",
    )


def test_get_access_token(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": 0, "tenant_access_token": "t-abc123", "expire": 7200}
    mock_resp.raise_for_status = MagicMock()
    with patch("feishu.requests.post", return_value=mock_resp):
        token = client._get_access_token()
    assert token == "t-abc123"


def test_get_or_create_table_existing(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "code": 0,
        "data": {"items": [{"table_id": "tbl123", "name": "2026-W13"}]}
    }
    mock_resp.raise_for_status = MagicMock()
    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.get", return_value=mock_resp):
            table_id = client.get_or_create_table("2026-W13")
    assert table_id == "tbl123"


def test_upsert_record_new(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": 0, "data": {"record": {"record_id": "rec123"}}}
    mock_resp.raise_for_status = MagicMock()
    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.post", return_value=mock_resp):
            client.upsert_record("tbl123", {
                "仓库名": "owner/repo",
                "Stars": 1000,
            }, record_id=None)


def test_upsert_record_update(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"code": 0, "data": {"record": {"record_id": "rec123"}}}
    mock_resp.raise_for_status = MagicMock()
    with patch.object(client, "_get_access_token", return_value="t-abc"):
        with patch("feishu.requests.put", return_value=mock_resp):
            client.upsert_record("tbl123", {
                "仓库名": "owner/repo",
                "Stars": 1500,
            }, record_id="rec123")
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
pytest tests/test_feishu.py -v
```

期望：`ImportError: No module named 'feishu'`

- [ ] **Step 3: 实现 feishu.py**

新建 `feishu.py`：

```python
import requests
from config import FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_BITABLE_APP_TOKEN, FEISHU_API_BASE


class FeishuClient:
    def __init__(self, app_id=None, app_secret=None, bitable_app_token=None):
        self.app_id = app_id or FEISHU_APP_ID
        self.app_secret = app_secret or FEISHU_APP_SECRET
        self.bitable_app_token = bitable_app_token or FEISHU_BITABLE_APP_TOKEN

    def _get_access_token(self) -> str:
        resp = requests.post(
            f"{FEISHU_API_BASE}/auth/v3/tenant_access_token/internal",
            json={"app_id": self.app_id, "app_secret": self.app_secret},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书获取 token 失败: {data}")
        return data["tenant_access_token"]

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def get_or_create_table(self, week_label: str) -> str:
        """获取或创建当周数据表，返回 table_id"""
        token = self._get_access_token()
        resp = requests.get(
            f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables",
            headers=self._headers(token),
            timeout=10,
        )
        resp.raise_for_status()
        items = resp.json().get("data", {}).get("items", [])
        for item in items:
            if item["name"] == week_label:
                return item["table_id"]

        # 不存在则创建
        resp = requests.post(
            f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables",
            headers=self._headers(token),
            json={"table": {"name": week_label, "fields": [
                {"field_name": "仓库名", "type": 1},
                {"field_name": "描述", "type": 1},
                {"field_name": "Stars", "type": 2},
                {"field_name": "Star 涨幅", "type": 2},
                {"field_name": "语言", "type": 1},
                {"field_name": "链接", "type": 15},
                {"field_name": "首次入榜时间", "type": 1},
                {"field_name": "最后更新时间", "type": 1},
            ]}},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书创建数据表失败: {data}")
        return data["data"]["table_id"]

    def upsert_record(self, table_id: str, fields: dict, record_id: str = None):
        """新增或更新一条记录"""
        token = self._get_access_token()
        if record_id is None:
            resp = requests.post(
                f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables/{table_id}/records",
                headers=self._headers(token),
                json={"fields": fields},
                timeout=10,
            )
        else:
            resp = requests.put(
                f"{FEISHU_API_BASE}/bitable/v1/apps/{self.bitable_app_token}/tables/{table_id}/records/{record_id}",
                headers=self._headers(token),
                json={"fields": fields},
                timeout=10,
            )
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"飞书写入记录失败: {data}")
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
pytest tests/test_feishu.py -v
```

期望：4 个测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add feishu.py tests/test_feishu.py
git commit -m "feat: add feishu bitable client with get_or_create_table and upsert_record"
```

---

## Task 4: 更新 main.py，串联完整流水线

**Files:**
- Modify: `main.py`

- [ ] **Step 1: 替换 main.py**

```python
import argparse
import sys
from datetime import datetime
from fetcher import fetch_top_repos
from formatter import print_repos, console
from exporter import export_json, export_csv
from dedup import DedupState
from feishu import FeishuClient
from config import get_week_label


def main():
    parser = argparse.ArgumentParser(description="抓取 GitHub 热门仓库并写入飞书")
    parser.add_argument("--top", type=int, default=30, help="抓取前 N 个仓库（默认 30）")
    parser.add_argument("--period", choices=["today", "weekly", "monthly"], default="weekly")
    parser.add_argument("--lang", type=str, default=None, help="按编程语言筛选")
    parser.add_argument("--export", choices=["json", "csv"], default=None, help="同时导出本地文件")
    parser.add_argument("--dry-run", action="store_true", help="只抓取和去重，不写入飞书")
    parser.add_argument("--token", type=str, default=None, help="GitHub Token（优先级高于 .env）")
    args = parser.parse_args()

    if args.token:
        import config, fetcher
        config.GITHUB_TOKEN = args.token
        fetcher.GITHUB_TOKEN = args.token

    console.print(f"[bold]正在抓取 GitHub 热门仓库...[/bold] period=[cyan]{args.period}[/cyan] top=[cyan]{args.top}[/cyan]")

    try:
        repos = fetch_top_repos(top=args.top, period=args.period, lang=args.lang)
    except RuntimeError as e:
        console.print(f"[red]错误：{e}[/red]")
        sys.exit(1)

    print_repos(repos, period=args.period, lang=args.lang)

    week = get_week_label()
    dedup = DedupState()
    to_write = []

    for repo in repos:
        action = dedup.check_and_update(repo["url"], repo["stars"], week)
        if action == "skip":
            continue
        repo["_dedup_action"] = action
        repo["first_seen"] = dedup.get_first_seen(repo["url"], week)
        to_write.append(repo)

    dedup.save()
    console.print(f"[dim]去重后待写入：{len(to_write)} 条（跳过 {len(repos) - len(to_write)} 条）[/dim]")

    if not args.dry_run and to_write:
        feishu = FeishuClient()
        table_id = feishu.get_or_create_table(week)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        for repo in to_write:
            fields = {
                "仓库名": repo["name"],
                "描述": repo["description"],
                "Stars": repo["stars"],
                "Star 涨幅": repo["stars"] - (repo["stars"] if repo["_dedup_action"] == "new" else 0),
                "语言": repo["language"],
                "链接": {"link": repo["url"], "text": repo["name"]},
                "首次入榜时间": repo["first_seen"],
                "最后更新时间": today,
            }
            feishu.upsert_record(table_id, fields)
        console.print(f"[green]已写入飞书表格 {week}，共 {len(to_write)} 条[/green]")
    elif args.dry_run:
        console.print("[yellow]dry-run 模式，跳过飞书写入[/yellow]")

    if args.export == "json":
        path = export_json(repos, args.period)
        console.print(f"[green]已导出 JSON：{path}[/green]")
    elif args.export == "csv":
        path = export_csv(repos, args.period)
        console.print(f"[green]已导出 CSV：{path}[/green]")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 提交**

```bash
git add main.py
git commit -m "feat: wire fetcher -> dedup -> feishu pipeline in main.py"
```

---

## Task 5: 创建 GitHub Actions workflow

**Files:**
- Create: `.github/workflows/daily.yml`

- [ ] **Step 1: 创建 workflow 文件**

新建 `.github/workflows/daily.yml`：

```yaml
name: GitHub Star Tracker

on:
  schedule:
    - cron: '0 1 * * *'   # 每天 UTC 1:00 = 北京时间 9:00
  workflow_dispatch:        # 支持手动触发

jobs:
  fetch-and-sync:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Restore dedup state cache
        uses: actions/cache@v4
        with:
          path: dedup_state.json
          key: dedup-state-${{ github.run_id }}
          restore-keys: |
            dedup-state-

      - name: Run tracker
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          FEISHU_APP_ID: ${{ secrets.FEISHU_APP_ID }}
          FEISHU_APP_SECRET: ${{ secrets.FEISHU_APP_SECRET }}
          FEISHU_BITABLE_APP_TOKEN: ${{ secrets.FEISHU_BITABLE_APP_TOKEN }}
        run: python main.py --top 30 --period weekly

      - name: Save dedup state cache
        uses: actions/cache@v4
        with:
          path: dedup_state.json
          key: dedup-state-${{ github.run_id }}
```

- [ ] **Step 2: 提交**

```bash
git add .github/workflows/daily.yml
git commit -m "feat: add GitHub Actions daily workflow with dedup cache"
```

---

## Task 6: 配置 GitHub Secrets 并验证

- [ ] **Step 1: 在 GitHub 仓库配置 Secrets**

进入仓库 → Settings → Secrets and variables → Actions → New repository secret，依次添加：

| 名称 | 值 |
|------|----|
| `FEISHU_APP_ID` | 你的飞书 App ID |
| `FEISHU_APP_SECRET` | 重置后的飞书 App Secret |
| `FEISHU_BITABLE_APP_TOKEN` | `FB5wbrAOMaQoKqsQeuPcoOQXnx1` |

> 注意：`GITHUB_TOKEN` 由 GitHub Actions 自动提供，无需手动添加。

- [ ] **Step 2: 确认飞书应用权限**

在飞书开放平台 → 你的应用 → 权限管理，确认已开启：
- `bitable:app`（读写多维表格）

并将应用添加为多维表格文档的协作者（文档右上角 → 分享 → 添加应用）。

- [ ] **Step 3: 手动触发 workflow 验证**

在 GitHub 仓库 → Actions → GitHub Star Tracker → Run workflow，点击运行，观察日志是否成功写入飞书。

---

## 自检结果

- **Spec 覆盖：** 所有需求均有对应 Task（抓取 ✓、去重 ✓、飞书写入 ✓、按周分表 ✓、定时触发 ✓、手动触发 ✓、dry-run ✓）
- **Placeholder 扫描：** 无 TBD/TODO
- **类型一致性：** `DedupState.check_and_update` 返回值 `"new"/"update"/"skip"` 在 Task 2 定义，Task 4 使用一致；`FeishuClient.upsert_record` 签名在 Task 3 定义，Task 4 调用一致
