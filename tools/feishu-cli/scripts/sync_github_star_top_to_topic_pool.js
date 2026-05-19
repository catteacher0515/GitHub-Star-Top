#!/usr/bin/env node

const { execFileSync } = require("node:child_process");
const { buildTargetPayload } = require("./topic_pool_payload");

const DRY_RUN = process.argv.includes("--dry-run");

const CONFIG = {
  source: {
    baseToken: "FB5wbrAOMaQoKqsQeuPcoOQXnx1",
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
      added: "已加入",
      duplicate: "重复待确认",
    },
  },
  target: {
    baseToken: "VYACbsa3qaLk2LsRfIXcrSimn5g",
    tableId: "tblh5mwVpDTGF6VN",
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

function runLark(args, options = {}) {
  const normalizedArgs = [...args];
  if (options.forceJsonFormat && !normalizedArgs.includes("--format")) {
    normalizedArgs.push("--format", "json");
  }

  const output = execFileSync("lark-cli", normalizedArgs, {
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
  const trimmed = output.trim();
  const start = trimmed.indexOf("{");
  if (start === -1) {
    throw new Error(`Unexpected lark-cli output: ${trimmed}`);
  }
  const parsed = JSON.parse(trimmed.slice(start));
  if (parsed.ok === false) {
    throw new Error(parsed.error?.message || "Unknown lark-cli error");
  }
  return parsed;
}

function getTableFields(baseToken, tableId) {
  const result = runLark([
    "base",
    "+field-list",
    "--base-token",
    baseToken,
    "--table-id",
    tableId,
  ]);
  return result.data.fields;
}

function listSourceTables(baseToken) {
  const result = runLark([
    "base",
    "+table-list",
    "--base-token",
    baseToken,
  ]);
  return result.data.tables || [];
}

function getFieldMap(fields) {
  return new Map(fields.map((field) => [field.name, field]));
}

function listRecords(baseToken, tableId, fieldNames) {
  const args = [
    "base",
    "+record-list",
    "--base-token",
    baseToken,
    "--table-id",
    tableId,
    "--offset",
    "0",
    "--limit",
    "200",
  ];

  for (const fieldName of fieldNames) {
    args.push("--field-id", fieldName);
  }

  const result = runLark(args, { forceJsonFormat: true });
  const rows = result.data.data || [];
  const fields = result.data.fields || [];
  const recordIds = result.data.record_id_list || [];

  return rows.map((row, index) => ({
    recordId: recordIds[index],
    values: Object.fromEntries(fields.map((field, fieldIndex) => [field, row[fieldIndex]])),
  }));
}

function selectContains(optionValue, expected) {
  if (!optionValue) return false;
  if (Array.isArray(optionValue)) {
    return optionValue.includes(expected);
  }
  return optionValue === expected;
}

function normalizeText(value) {
  if (value == null) return "";
  if (Array.isArray(value)) return value.join(" ").trim();
  return String(value).trim();
}

function normalizeUrl(value) {
  return normalizeText(value).replace(/\/+$/, "");
}

function formatNow() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
  ].join("-") + " " + [
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds()),
  ].join(":");
}

function ensureRequiredFields(fieldMap, fieldNames, label) {
  for (const name of fieldNames) {
    if (!fieldMap.has(name)) {
      throw new Error(`${label} missing field: ${name}`);
    }
  }
}

function hasAllFields(fieldMap, fieldNames) {
  return fieldNames.every((name) => fieldMap.has(name));
}

function isWeeklyTable(name) {
  return /^20\d{2}-W\d{2}$/.test(String(name || "").trim());
}

function collectPendingSourceRecords(config, sourceTables, deps) {
  const pending = [];
  const requiredSource = Object.values(config.source.fieldNames);

  for (const table of sourceTables.filter((item) => isWeeklyTable(item.name))) {
    const fieldMap = deps.getFieldMap(
      deps.getTableFields(config.source.baseToken, table.id)
    );
    if (!hasAllFields(fieldMap, requiredSource)) {
      continue;
    }

    const records = deps.listRecords(
      config.source.baseToken,
      table.id,
      requiredSource
    );

    for (const record of records) {
      if (
        selectContains(
          record.values[config.source.fieldNames.syncStatus],
          config.source.status.pending
        )
      ) {
        pending.push({
          tableId: table.id,
          tableName: table.name,
          recordId: record.recordId,
          values: record.values,
        });
      }
    }
  }

  return pending;
}

function updateSourceRecord(tableId, recordId, patch) {
  if (DRY_RUN) {
    return { dryRun: true, tableId, recordId, patch };
  }
  runLark([
    "base",
    "+record-upsert",
    "--base-token",
    CONFIG.source.baseToken,
    "--table-id",
    tableId,
    "--record-id",
    recordId,
    "--json",
    JSON.stringify(patch),
  ]);
}

function createTargetRecord(payload) {
  if (DRY_RUN) {
    return `dry-run-${Math.random().toString(36).slice(2, 10)}`;
  }
  const result = runLark([
    "base",
    "+record-upsert",
    "--base-token",
    CONFIG.target.baseToken,
    "--table-id",
    CONFIG.target.tableId,
    "--json",
    JSON.stringify(payload),
  ]);
  return result.data.record.record_id_list[0];
}

function getTargetRecordUrl(recordId) {
  return `https://my.feishu.cn/base/${CONFIG.target.baseToken}?table=${CONFIG.target.tableId}&recordId=${recordId}`;
}

function main() {
  const sourceTables = listSourceTables(CONFIG.source.baseToken);
  const pending = collectPendingSourceRecords(CONFIG, sourceTables, {
    getTableFields,
    listRecords,
    getFieldMap,
  });

  const targetFields = getFieldMap(getTableFields(CONFIG.target.baseToken, CONFIG.target.tableId));
  const requiredTarget = Object.values(CONFIG.target.fieldNames);
  ensureRequiredFields(targetFields, requiredTarget, "Target table");

  const targetRecords = listRecords(CONFIG.target.baseToken, CONFIG.target.tableId, requiredTarget);
  const targetByName = new Map();
  const targetByUrl = new Map();

  for (const target of targetRecords) {
    const topic = normalizeText(target.values[CONFIG.target.fieldNames.topic]);
    const url = normalizeUrl(target.values[CONFIG.target.fieldNames.link]);
    if (topic) targetByName.set(topic, target);
    if (url) targetByUrl.set(url, target);
  }

  const summary = {
    dryRun: DRY_RUN,
    processed: pending.length,
    created: [],
    duplicates: [],
  };

  for (const source of pending) {
    const repoName = normalizeText(source.values[CONFIG.source.fieldNames.repoName]);
    const repoUrl = normalizeUrl(source.values[CONFIG.source.fieldNames.repoUrl]);
    const repoNotes = normalizeText(source.values[CONFIG.source.fieldNames.repoNotes]);
    const repoDraft = normalizeText(source.values[CONFIG.source.fieldNames.draft]);

    const duplicate =
      (repoName && targetByName.get(repoName)) ||
      (repoUrl && targetByUrl.get(repoUrl));

    if (duplicate) {
      updateSourceRecord(source.tableId, source.recordId, {
        [CONFIG.source.fieldNames.syncStatus]: CONFIG.source.status.duplicate,
      });
      summary.duplicates.push({
        sourceRecordId: source.recordId,
        sourceTableName: source.tableName,
        repoName,
        repoUrl,
        existing: {
          topic: duplicate.values[CONFIG.target.fieldNames.topic],
          link: duplicate.values[CONFIG.target.fieldNames.link],
          publishProgress: duplicate.values[CONFIG.target.fieldNames.publishProgress],
          topicStatus: duplicate.values[CONFIG.target.fieldNames.topicStatus],
          priority: duplicate.values[CONFIG.target.fieldNames.priority],
        },
      });
      continue;
    }

    const createdRecordId = createTargetRecord(
      buildTargetPayload(
        {
          repoName,
          repoUrl,
          repoNotes,
          repoDraft,
        },
        formatNow()
      )
    );

    const targetRecordUrl = getTargetRecordUrl(createdRecordId);
    updateSourceRecord(source.tableId, source.recordId, {
      [CONFIG.source.fieldNames.syncStatus]: CONFIG.source.status.added,
      [CONFIG.source.fieldNames.targetRecordUrl]: targetRecordUrl,
    });

    summary.created.push({
      sourceRecordId: source.recordId,
      sourceTableName: source.tableName,
      targetRecordId: createdRecordId,
      repoName,
      targetRecordUrl,
    });
  }

  console.log(JSON.stringify(summary, null, 2));
  return summary;
}

module.exports = {
  CONFIG,
  collectPendingSourceRecords,
  getFieldMap,
  hasAllFields,
  isWeeklyTable,
  listRecords,
  listSourceTables,
  normalizeText,
  normalizeUrl,
  runLark,
};

if (require.main === module) {
  main();
}
