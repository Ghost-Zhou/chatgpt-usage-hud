#!/usr/bin/env bash
set -euo pipefail
LABEL='com.local.chatgpt-usage-hud'
SERVICE="gui/$(id -u)/${LABEL}"
PLIST="${HOME}/Library/LaunchAgents/${LABEL}.plist"
if [[ -f "${PLIST}" ]] && [[ "$(/usr/libexec/PlistBuddy -c 'Print :Label' "${PLIST}")" != "${LABEL}" ]]; then
  echo 'Refusing to remove an unrelated LaunchAgent.' >&2
  exit 1
fi
launchctl disable "${SERVICE}"
if launchctl print "${SERVICE}" >/dev/null 2>&1; then
  launchctl bootout "${SERVICE}"
fi
if [[ -f "${PLIST}" ]]; then rm "${PLIST}"; fi
echo 'Automatic startup removed. Runtime files and app data were preserved.'
echo '已移除自動啟動設定；執行副本及 App 資料均保留。'
echo 'Quit/reopen the app normally to remove the current HUD and debugging port.'
echo '正常退出並重開 App，即可移除目前 HUD 與除錯連線。'
