#!/bin/zsh
set -euo pipefail

SERVICE_NAME="com.huapingyu.github-star-top.topic-pool-sync-bot"
PLIST_PATH="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"

launchctl bootout "gui/$(id -u)/${SERVICE_NAME}" >/dev/null 2>&1 || true
rm -f "$PLIST_PATH"

echo "uninstalled ${SERVICE_NAME}"
