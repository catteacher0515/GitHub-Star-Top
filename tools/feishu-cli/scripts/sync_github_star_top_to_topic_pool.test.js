const test = require("node:test");
const assert = require("node:assert/strict");

const {
  collectPendingSourceRecords,
  isWeeklyTable,
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
