const test = require("node:test");
const assert = require("node:assert/strict");

const {
  shouldTriggerSync,
  buildReplyText,
} = require("./topic_pool_command_handler");

test("should trigger only on exact sync command", () => {
  assert.equal(shouldTriggerSync("同步待加入选题池"), true);
  assert.equal(shouldTriggerSync(" 同步待加入选题池 "), true);
  assert.equal(shouldTriggerSync("同步"), false);
  assert.equal(shouldTriggerSync("同步待加入选题池。"), false);
});

test("build reply text for successful sync summary", () => {
  const text = buildReplyText({
    dryRun: false,
    processed: 3,
    created: [
      { repoName: "repo-a", targetRecordUrl: "https://example.com/a" },
      { repoName: "repo-b", targetRecordUrl: "https://example.com/b" },
    ],
    duplicates: [
      {
        repoName: "repo-c",
        existing: {
          topic: "repo-c",
          link: "https://github.com/demo/repo-c",
          publishProgress: "未发布",
          topicStatus: "待整理",
          priority: "高优先级",
        },
      },
    ],
  });

  assert.match(text, /本次共处理 3 条候选记录/);
  assert.match(text, /成功加入 2 条/);
  assert.match(text, /发现重复 1 条/);
  assert.match(text, /repo-a/);
  assert.match(text, /repo-c/);
  assert.match(text, /高优先级/);
});

test("build reply text for empty run", () => {
  const text = buildReplyText({
    dryRun: false,
    processed: 0,
    created: [],
    duplicates: [],
  });

  assert.match(text, /没有发现「待加入选题池」的记录/);
});
