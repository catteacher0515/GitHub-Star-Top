function shouldTriggerSync(text) {
  return String(text || "").trim() === "同步待加入选题池";
}

function buildReplyText(summary) {
  if (!summary || summary.processed === 0) {
    return "没有发现「待加入选题池」的记录。";
  }

  const lines = [
    `本次共处理 ${summary.processed} 条候选记录。`,
    `成功加入 ${summary.created.length} 条。`,
    `发现重复 ${summary.duplicates.length} 条。`,
  ];

  if (summary.created.length > 0) {
    lines.push("");
    lines.push("已加入选题池：");
    for (const item of summary.created.slice(0, 10)) {
      lines.push(`- ${item.repoName}: ${item.targetRecordUrl}`);
    }
  }

  if (summary.duplicates.length > 0) {
    lines.push("");
    lines.push("重复待确认：");
    for (const item of summary.duplicates.slice(0, 10)) {
      lines.push(`- ${item.repoName}`);
      lines.push(`  选题: ${item.existing.topic || "-"}`);
      lines.push(`  链接: ${item.existing.link || "-"}`);
      lines.push(`  发布进度: ${item.existing.publishProgress || "-"}`);
      lines.push(`  选题状态: ${item.existing.topicStatus || "-"}`);
      lines.push(`  优先级: ${item.existing.priority || "-"}`);
    }
  }

  return lines.join("\n");
}

module.exports = {
  shouldTriggerSync,
  buildReplyText,
};
