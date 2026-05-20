# GitHub Star Tracker

每天自动抓取 GitHub 优质热门仓库，用 AI 生成仓库解读，写入飞书多维表格，按周分表组织。

## 功能

- 每天定时抓取 GitHub 优质热门仓库（默认前 30 个）
- `weekly` 口径采用多源聚合：
  - 60% 来自 GitHub Trending 周榜
  - 30% 来自全站优质热门项目
  - 10% 来自新项目发现
- 支持按时间范围筛选：今天 / 本周 / 本月
- 自动过滤模拟器、ROM、启动器、破解/预激活/资源分发类仓库，保留壁纸引擎、桌面宠物等可接受的娱乐项目
- 自动抓取 README，调用 DeepSeek 生成：
  - **仓库解读**：口语化介绍，适合非技术读者，可直接用于自媒体内容
  - **快速上手**：结构化功能介绍 + 上手步骤，适合技术向读者
- 智能去重：同一仓库本周内只写入一次，star 涨幅超过 500 时自动更新
- 按周分表写入飞书多维表格（如 `2026-W13`）
- 支持 GitHub Actions 每天自动运行，也可手动触发

## 效果预览

飞书多维表格字段：

| 字段 | 说明 |
|------|------|
| 仓库名 | owner/repo 格式 |
| 描述 | 仓库原始描述 |
| Stars | 当前 star 数 |
| Star 涨幅 | 与上次记录的差值 |
| 语言 | 主要编程语言 |
| 链接 | GitHub 仓库地址 |
| 首次入榜时间 | 第一次被抓取的日期 |
| 最后更新时间 | 最近一次更新日期 |
| 仓库解读 | AI 生成的口语化介绍 |
| 快速上手 | AI 生成的结构化上手指南 |

## 快速开始

### 1. Fork 这个仓库

点击右上角 Fork，复制到你自己的 GitHub 账号下。

### 2. 创建飞书应用

1. 打开 [飞书开放平台](https://open.feishu.cn)，创建一个自建应用
2. 在「权限管理」中开启 `bitable:app`（读写多维表格）
3. 记录 App ID 和 App Secret

### 3. 准备飞书多维表格

1. 在飞书中创建一个多维表格文档
2. 将你的应用添加为文档协作者（文档右上角 → 分享 → 搜索应用名称）
3. 从文档 URL 中获取 `app_token`，格式如：`https://xxx.feishu.cn/base/xxxxxx`，其中 `xxxxxx` 即为 app_token

### 4. 配置 GitHub Secrets

在你 Fork 的仓库中，进入 Settings → Secrets and variables → Actions，添加以下 Secret：

| 名称 | 说明 |
|------|------|
| `FEISHU_APP_ID` | 飞书应用 ID |
| `FEISHU_APP_SECRET` | 飞书应用密钥 |
| `FEISHU_BITABLE_APP_TOKEN` | 飞书多维表格文档 ID |
| `DEEPSEEK_API_KEY` | DeepSeek API Key，[在此申请](https://platform.deepseek.com) |

> `GITHUB_TOKEN` 由 GitHub Actions 自动提供，无需手动添加。

### 5. 触发运行

进入仓库的 Actions 页面 → GitHub Star Tracker → Run workflow，手动触发一次验证配置是否正确。

之后每天北京时间早上 9 点会自动运行。

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 复制配置文件
cp .env.example .env
# 编辑 .env，填入各项 Token

# 运行（dry-run 模式，不写入飞书）
python main.py --dry-run

# 正常运行
python main.py --top 30 --period weekly

# 按语言筛选
python main.py --top 20 --period weekly --lang python

# 同时导出本地文件
python main.py --top 30 --export json
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--top` | 30 | 抓取前 N 个仓库 |
| `--period` | weekly | 时间范围：today / weekly / monthly；其中 `weekly` 默认走 60/30/10 多源聚合 |
| `--lang` | 不限 | 按编程语言筛选，如 python、javascript |
| `--export` | 不导出 | 导出本地文件：json / csv |
| `--dry-run` | 关闭 | 只抓取，不写入飞书 |

## 运行测试

```bash
pip install pytest
pytest tests/ -v
```

## 飞书选题池同步

仓库内置了配套的飞书 CLI 脚本，位置在 `tools/feishu-cli/`。

```bash
# 预演同步，不实际写入
node tools/feishu-cli/scripts/sync_github_star_top_to_topic_pool.js --dry-run

# 正式同步所有周表中“待加入选题池”的记录
node tools/feishu-cli/scripts/sync_github_star_top_to_topic_pool.js

# 启动飞书机器人监听，收到“同步待加入选题池”后自动执行
node tools/feishu-cli/scripts/run_topic_pool_sync_bot.js
```

相关 Node 测试：

```bash
node --test tools/feishu-cli/scripts/*.test.js
```

## License

MIT
