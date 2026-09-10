#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo 'Install/update automatic HUD startup. ChatGPT may quit and reopen normally.'
echo '安裝／更新 HUD 自動啟動；ChatGPT 可能正常退出並重開一次。'
for candidate in \
  "$(command -v python3 || true)" \
  /opt/homebrew/bin/python3 /usr/local/bin/python3 \
  "${HOME}/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"; do
  if [[ -x "${candidate}" ]] && "${candidate}" -c 'import sys; raise SystemExit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    export PYTHONDONTWRITEBYTECODE=1
    exec "${candidate}" "${SCRIPT_DIR}/scripts/manage_service.py" "$@"
  fi
done
echo 'Python 3.10+ is required. Install Python, then rerun this script.' >&2
echo '需要可執行的 Python 3.10 或更新版；安裝後請再執行本腳本。' >&2
exit 1
