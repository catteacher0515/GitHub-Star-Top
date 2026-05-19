function buildTargetPayload(source, now) {
  return {
    选题: source.repoName,
    参考链接: source.repoUrl,
    创作备注: source.repoNotes,
    推荐初稿: source.repoDraft,
    发布进度: "未发布",
    灵感时间: now,
  };
}

module.exports = {
  buildTargetPayload,
};
