const test = require("node:test");
const assert = require("node:assert/strict");

const { buildTargetPayload } = require("./topic_pool_payload");

test("buildTargetPayload fills default publish progress and inspiration time", () => {
  const now = "2026-05-16 15:20:00";
  const payload = buildTargetPayload(
    {
      repoName: "demo/repo",
      repoUrl: "https://github.com/demo/repo",
      repoNotes: "notes",
      repoDraft: "draft",
    },
    now
  );

  assert.deepEqual(payload, {
    选题: "demo/repo",
    参考链接: "https://github.com/demo/repo",
    创作备注: "notes",
    推荐初稿: "draft",
    发布进度: "未发布",
    灵感时间: "2026-05-16 15:20:00",
  });
});
