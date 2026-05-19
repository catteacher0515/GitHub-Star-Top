#!/usr/bin/env node

const { spawn, execFileSync } = require("node:child_process");
const readline = require("node:readline");
const path = require("node:path");
const { shouldTriggerSync, buildReplyText } = require("./topic_pool_command_handler");

const SYNC_SCRIPT = path.join(__dirname, "sync_github_star_top_to_topic_pool.js");

function runSyncScript() {
  const output = execFileSync("node", [SYNC_SCRIPT], {
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function replyToMessage(messageId, text) {
  execFileSync(
    "lark-cli",
    [
      "im",
      "+messages-reply",
      "--as",
      "bot",
      "--message-id",
      messageId,
      "--text",
      text,
    ],
    { encoding: "utf8", maxBuffer: 10 * 1024 * 1024 }
  );
}

function main() {
  const child = spawn(
    "lark-cli",
    ["event", "consume", "im.message.receive_v1", "--as", "bot"],
    {
      stdio: ["pipe", "pipe", "pipe"],
    }
  );

  const stderrRl = readline.createInterface({ input: child.stderr });
  const stdoutRl = readline.createInterface({ input: child.stdout });

  stderrRl.on("line", (line) => {
    process.stderr.write(`${line}\n`);
  });

  stdoutRl.on("line", (line) => {
    if (!line.trim()) return;
    let event;
    try {
      event = JSON.parse(line);
    } catch (error) {
      process.stderr.write(`[sync-bot] invalid event json: ${error.message}\n`);
      return;
    }

    if (event.chat_type !== "p2p" || event.message_type !== "text") {
      return;
    }

    if (!shouldTriggerSync(event.content)) {
      return;
    }

    try {
      const summary = runSyncScript();
      const reply = buildReplyText(summary);
      replyToMessage(event.message_id, reply);
    } catch (error) {
      const message = `同步失败：${error.message}`;
      try {
        replyToMessage(event.message_id, message);
      } catch (replyError) {
        process.stderr.write(`[sync-bot] failed to reply error message: ${replyError.message}\n`);
      }
    }
  });

  child.on("exit", (code, signal) => {
    process.stderr.write(`[sync-bot] event consumer exited code=${code} signal=${signal}\n`);
    process.exit(code ?? 0);
  });
}

main();
