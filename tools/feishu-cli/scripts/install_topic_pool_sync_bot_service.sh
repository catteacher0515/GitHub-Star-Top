#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
NODE_BIN="$(command -v node)"
LARK_BIN="$(command -v lark-cli)"
SERVICE_NAME="com.huapingyu.github-star-top.topic-pool-sync-bot"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"
LOG_DIR="$HOME/Library/Logs/GitHub-Star-Top"
STDOUT_LOG="$LOG_DIR/topic-pool-sync-bot.stdout.log"
STDERR_LOG="$LOG_DIR/topic-pool-sync-bot.stderr.log"
BOT_SCRIPT="$REPO_ROOT/tools/feishu-cli/scripts/run_topic_pool_sync_bot.js"

mkdir -p "$LOG_DIR"
mkdir -p "$HOME/Library/LaunchAgents"

cat >"$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${SERVICE_NAME}</string>

    <key>ProgramArguments</key>
    <array>
      <string>${NODE_BIN}</string>
      <string>${BOT_SCRIPT}</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
      <key>PATH</key>
      <string>$(dirname "$NODE_BIN"):$(dirname "$LARK_BIN"):/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>${REPO_ROOT}</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${STDOUT_LOG}</string>

    <key>StandardErrorPath</key>
    <string>${STDERR_LOG}</string>
  </dict>
</plist>
PLIST

launchctl bootout "gui/$(id -u)/${SERVICE_NAME}" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/${SERVICE_NAME}"
launchctl kickstart -k "gui/$(id -u)/${SERVICE_NAME}"

echo "installed ${SERVICE_NAME}"
echo "plist: ${PLIST_PATH}"
echo "stdout: ${STDOUT_LOG}"
echo "stderr: ${STDERR_LOG}"
