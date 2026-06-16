const test = require("node:test");
const assert = require("node:assert/strict");

const {
  collectPendingSourceRecords,
  isWeeklyTable,
  listRecords,
  syncPendingRecords,
} = require("./sync_github_star_top_to_topic_pool");

test("collectPendingSourceRecords scans all weekly source tables", () => {
  const tableFieldsById = {
    "tbl-w20": [
      { name: "仓库名" },
      { name: "链接" },
      { name: "仓库解读" },
      { name: "推荐初稿" },
      { name: "入池状态" },
      { name: "选题池记录" },
    ],
    "tbl-w21": [
      { name: "仓库名" },
      { name: "链接" },
      { name: "仓库解读" },
      { name: "推荐初稿" },
      { name: "入池状态" },
      { name: "选题池记录" },
    ],
  };

  const recordsByTableId = {
    "tbl-w20": [
      {
        recordId: "rec-old",
        values: {
          "仓库名": "old/repo",
          "入池状态": ["已加入"],
        },
      },
    ],
    "tbl-w21": [
      {
        recordId: "rec-new",
        values: {
          "仓库名": "new/repo",
          "链接": "https://github.com/new/repo",
          "仓库解读": "notes",
          "推荐初稿": "draft",
          "入池状态": ["待加入选题池"],
          "选题池记录": null,
        },
      },
    ],
  };

  const pending = collectPendingSourceRecords(
    {
      source: {
        baseToken: "base-source",
        fieldNames: {
          repoName: "仓库名",
          repoUrl: "链接",
          repoNotes: "仓库解读",
          draft: "推荐初稿",
          syncStatus: "入池状态",
          targetRecordUrl: "选题池记录",
        },
        status: {
          pending: "待加入选题池",
        },
      },
    },
    [
      { id: "tbl-w20", name: "2026-W20" },
      { id: "tbl-w21", name: "2026-W21" },
    ],
    {
      getTableFields(baseToken, tableId) {
        return tableFieldsById[tableId];
      },
      listRecords(baseToken, tableId) {
        return recordsByTableId[tableId];
      },
      getFieldMap(fields) {
        return new Map(fields.map((field) => [field.name, field]));
      },
    }
  );

  assert.equal(pending.length, 1);
  assert.equal(pending[0].recordId, "rec-new");
  assert.equal(pending[0].tableId, "tbl-w21");
  assert.equal(pending[0].tableName, "2026-W21");
});

test("isWeeklyTable only matches weekly source tables", () => {
  assert.equal(isWeeklyTable("2026-W21"), true);
  assert.equal(isWeeklyTable("数据表"), false);
  assert.equal(isWeeklyTable("2026-05"), false);
});

test("collectPendingSourceRecords skips weekly tables missing sync fields", () => {
  const pending = collectPendingSourceRecords(
    {
      source: {
        baseToken: "base-source",
        fieldNames: {
          repoName: "仓库名",
          repoUrl: "链接",
          repoNotes: "仓库解读",
          draft: "推荐初稿",
          syncStatus: "入池状态",
          targetRecordUrl: "选题池记录",
        },
        status: {
          pending: "待加入选题池",
        },
      },
    },
    [
      { id: "tbl-old", name: "2026-W13" },
      { id: "tbl-new", name: "2026-W21" },
    ],
    {
      getTableFields(baseToken, tableId) {
        if (tableId === "tbl-old") {
          return [{ name: "仓库名" }, { name: "链接" }];
        }
        return [
          { name: "仓库名" },
          { name: "链接" },
          { name: "仓库解读" },
          { name: "推荐初稿" },
          { name: "入池状态" },
          { name: "选题池记录" },
        ];
      },
      listRecords(baseToken, tableId) {
        if (tableId === "tbl-old") {
          throw new Error("should not read old table records");
        }
        return [
          {
            recordId: "rec-new",
            values: {
              "仓库名": "new/repo",
              "链接": "https://github.com/new/repo",
              "仓库解读": "notes",
              "推荐初稿": "draft",
              "入池状态": ["待加入选题池"],
              "选题池记录": null,
            },
          },
        ];
      },
      getFieldMap(fields) {
        return new Map(fields.map((field) => [field.name, field]));
      },
    }
  );

  assert.equal(pending.length, 1);
  assert.equal(pending[0].tableId, "tbl-new");
});

test("listRecords reads all pages when a table has more than 200 records", () => {
  const calls = [];
  const records = listRecords(
    "base-token",
    "table-id",
    ["选题", "参考链接"],
    (args, options) => {
      calls.push({ args, options });
      const offset = Number(args[args.indexOf("--offset") + 1]);
      if (offset === 0) {
        return {
          data: {
            fields: ["选题", "参考链接"],
            record_id_list: Array.from({ length: 200 }, (_, index) => `rec-${index}`),
            data: Array.from({ length: 200 }, (_, index) => [
              `repo-${index}`,
              `https://github.com/demo/repo-${index}`,
            ]),
          },
        };
      }
      return {
        data: {
          fields: ["选题", "参考链接"],
          record_id_list: ["rec-200"],
          data: [["repo-200", "https://github.com/demo/repo-200"]],
        },
      };
    }
  );

  assert.equal(records.length, 201);
  assert.equal(records[200].recordId, "rec-200");
  assert.equal(calls.length, 2);
  assert.equal(calls[0].args[calls[0].args.indexOf("--offset") + 1], "0");
  assert.equal(calls[1].args[calls[1].args.indexOf("--offset") + 1], "200");
});

test("syncPendingRecords treats records created earlier in the same run as duplicates", () => {
  const config = {
    source: {
      fieldNames: {
        repoName: "仓库名",
        repoUrl: "链接",
        repoNotes: "仓库解读",
        draft: "推荐初稿",
        syncStatus: "入池状态",
        targetRecordUrl: "选题池记录",
      },
      status: {
        added: "已加入",
        duplicate: "重复待确认",
      },
    },
    target: {
      baseToken: "target-base",
      tableId: "target-table",
      fieldNames: {
        topic: "选题",
        link: "参考链接",
        notes: "创作备注",
        draft: "推荐初稿",
        publishProgress: "发布进度",
        topicStatus: "选题状态",
        priority: "优先级",
      },
    },
  };
  const pending = [
    {
      tableId: "source-table",
      tableName: "2026-W25",
      recordId: "rec-a",
      values: {
        仓库名: "demo/repo",
        链接: "https://github.com/demo/repo",
        仓库解读: "notes-a",
        推荐初稿: "draft-a",
      },
    },
    {
      tableId: "source-table",
      tableName: "2026-W25",
      recordId: "rec-b",
      values: {
        仓库名: "demo/repo",
        链接: "https://github.com/demo/repo/",
        仓库解读: "notes-b",
        推荐初稿: "draft-b",
      },
    },
  ];
  const createdPayloads = [];
  const sourceUpdates = [];

  const summary = syncPendingRecords(config, pending, [], {
    createTargetRecord(payload) {
      createdPayloads.push(payload);
      return "target-rec-a";
    },
    updateSourceRecord(tableId, recordId, patch) {
      sourceUpdates.push({ tableId, recordId, patch });
    },
    getTargetRecordUrl(recordId) {
      return `https://example.test/base?recordId=${recordId}`;
    },
    formatNow() {
      return "2026-06-16 18:00:00";
    },
  });

  assert.equal(createdPayloads.length, 1);
  assert.equal(summary.created.length, 1);
  assert.equal(summary.duplicates.length, 1);
  assert.equal(summary.duplicates[0].sourceRecordId, "rec-b");
  assert.deepEqual(sourceUpdates, [
    {
      tableId: "source-table",
      recordId: "rec-a",
      patch: {
        入池状态: "已加入",
        选题池记录: "https://example.test/base?recordId=target-rec-a",
      },
    },
    {
      tableId: "source-table",
      recordId: "rec-b",
      patch: {
        入池状态: "重复待确认",
      },
    },
  ]);
});

test("syncPendingRecords detects same-run duplicates by normalized repo url", () => {
  const config = {
    source: {
      fieldNames: {
        repoName: "仓库名",
        repoUrl: "链接",
        repoNotes: "仓库解读",
        draft: "推荐初稿",
        syncStatus: "入池状态",
        targetRecordUrl: "选题池记录",
      },
      status: {
        added: "已加入",
        duplicate: "重复待确认",
      },
    },
    target: {
      fieldNames: {
        topic: "选题",
        link: "参考链接",
        notes: "创作备注",
        draft: "推荐初稿",
        publishProgress: "发布进度",
        topicStatus: "选题状态",
        priority: "优先级",
      },
    },
  };
  const pending = [
    {
      tableId: "source-table",
      tableName: "2026-W25",
      recordId: "rec-a",
      values: {
        仓库名: "demo/repo",
        链接: "https://github.com/demo/repo/",
      },
    },
    {
      tableId: "source-table",
      tableName: "2026-W25",
      recordId: "rec-b",
      values: {
        仓库名: "Demo Repo",
        链接: "https://github.com/demo/repo",
      },
    },
  ];
  let createCount = 0;

  const summary = syncPendingRecords(config, pending, [], {
    createTargetRecord() {
      createCount += 1;
      return "target-rec-a";
    },
    updateSourceRecord() {},
    getTargetRecordUrl(recordId) {
      return `https://example.test/base?recordId=${recordId}`;
    },
    formatNow() {
      return "2026-06-16 18:00:00";
    },
  });

  assert.equal(createCount, 1);
  assert.equal(summary.created.length, 1);
  assert.equal(summary.duplicates.length, 1);
  assert.equal(summary.duplicates[0].sourceRecordId, "rec-b");
});
