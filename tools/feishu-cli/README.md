# Feishu CLI Helpers

## GitHub Star Top -> 自媒体选题池

批量同步脚本：

```bash
node tools/feishu-cli/scripts/sync_github_star_top_to_topic_pool.js
```

仅预演，不实际写入：

```bash
node tools/feishu-cli/scripts/sync_github_star_top_to_topic_pool.js --dry-run
```

### 同步规则

- 源表：`GitHub Star Top`
- 目标表：`自媒体选题池`
- 扫描所有周表（`YYYY-WXX`）
- 仅处理源表中 `入池状态 = 待加入选题池` 的记录
- 历史周表若缺少同步所需字段，会自动跳过

字段映射：

- `仓库名` -> `选题`
- `链接` -> `参考链接`
- `仓库解读` -> `创作备注`
- `推荐初稿` -> `推荐初稿`

重复判断：

- `仓库名` 相同，或
- `链接` 相同

处理结果：

- 成功写入目标表后，将源记录更新为 `已加入`
- 并回写 `选题池记录` 字段，保存目标记录链接
- 若检测到重复，则源记录更新为 `重复待确认`
- 不自动覆盖已有记录

## 飞书消息触发

启动监听机器人：

```bash
node tools/feishu-cli/scripts/run_topic_pool_sync_bot.js
```

触发方式：

- 给机器人发私聊消息：`同步待加入选题池`

行为：

- 监听机器人私聊文本消息
- 命中固定指令后执行同步脚本
- 将同步结果回复到该条消息

## 测试

```bash
node --test tools/feishu-cli/scripts/*.test.js
```
