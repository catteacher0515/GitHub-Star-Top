# GitHub Star Tracker — 设计文档

**日期：** 2026-03-28
**状态：** 已确认

---

## 目标

每天自动抓取 GitHub 热门仓库，去重后写入飞书多维表格，按周分表组织数据。同时支持手动触发。用途：个人学习参考 + 自媒体内容素材（知乎、稀土掘金、微信公众号、小红书）。

---

## 整体架构

```
GitHub Search API
       ↓
  fetcher.py（抓取热门仓库，前 30 个，按周筛选）
       ↓
  dedup.py（去重 + star 变化检测）
       ↓
  feishu.py（写入飞书多维表格，按周分表）
       ↓
  main.py（串联入口，支持参数覆盖）
       ↓
.github/workflows/daily.yml（每天 UTC 1:00 = 北京时间 9:00 触发）
```

---

## 模块说明

### fetcher.py
调用 GitHub Search API，按 star 数降序排列，筛选本周新创建的仓库，默认抓取前 30 个，不限语言。

### dedup.py
去重逻辑：
- 以仓库 URL 为唯一键
- 每周重置（新一周开始时清空去重记录）
- 同一仓库在本周已存在时：若 star 涨幅 ≥ 500，更新已有记录；否则跳过

去重状态存储在本地 `dedup_state.json`，由 GitHub Actions 通过 cache 在每次运行间持久化。

### feishu.py
调用飞书开放平台 API，写入指定多维表格。按周自动创建数据表，表名格式：`YYYY-WXX`（如 `2026-W13`）。

若当周数据表不存在则自动创建，字段结构固定（见下方）。

### main.py
CLI 入口，串联所有模块。支持以下参数：
- `--top N`：抓取数量，默认 30
- `--period`：today / weekly / monthly，默认 weekly
- `--lang`：语言筛选，可选
- `--dry-run`：只抓取和去重，不写入飞书，用于本地调试

---

## 飞书多维表格结构

**文档 app_token：** `FB5wbrAOMaQoKqsQeuPcoOQXnx1`

每周一张数据表，表名：`YYYY-WXX`

| 字段名 | 类型 | 说明 |
|--------|------|------|
| 仓库名 | 文本 | `owner/repo` 格式 |
| 描述 | 文本 | 仓库描述 |
| Stars | 数字 | 当前 star 数 |
| Star 涨幅 | 数字 | 本次与上次抓取的差值 |
| 语言 | 文本 | 主要编程语言 |
| 链接 | 超链接 | GitHub 仓库地址 |
| 首次入榜时间 | 日期 | 第一次被抓取的日期 |
| 最后更新时间 | 日期 | 最近一次更新的日期 |

---

## GitHub Actions 工作流

文件：`.github/workflows/daily.yml`

- 触发方式：每天 UTC 1:00（北京时间 9:00）自动触发，同时支持 `workflow_dispatch` 手动触发
- 运行环境：`ubuntu-latest`，Python 3.11
- 缓存：`dedup_state.json` 通过 `actions/cache` 在运行间持久化

---

## 环境变量 / GitHub Secrets

| 密钥名 | 说明 |
|--------|------|
| `GITHUB_TOKEN` | GitHub Personal Access Token，提升 Search API rate limit |
| `FEISHU_APP_ID` | 飞书应用 ID |
| `FEISHU_APP_SECRET` | 飞书应用密钥 |
| `FEISHU_BITABLE_APP_TOKEN` | 飞书多维表格文档 ID |

---

## 不在本期范围内

- 内容生成（文章草稿）— 后续版本
- 多语言适配不同平台格式 — 后续版本
- Web 界面 — 不做
