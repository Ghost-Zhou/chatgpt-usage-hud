#!/usr/bin/env python3
"""Install the user-scoped HUD service using only the standard library."""
import argparse
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys

LABEL = 'com.local.chatgpt-usage-hud'
RUNTIME_FILES = (
    'start_codex_monitor.sh', 'reopen_codex_with_debug.sh', 'port_utils.sh',
    'context_token_injector.py', 'context_token_inspector.py',
    'quota_reader.py', 'quota_hud.js',
)


def prepare_install(source, home, python, port):
    if not 1 <= port <= 65535:
        raise ValueError('Port must be between 1 and 65535')
    for name in RUNTIME_FILES:
        if not (source / 'scripts' / name).is_file():
            raise ValueError('Incomplete package: missing runtime file')
    if not (source / 'LICENSE').is_file():
        raise ValueError('Incomplete package: missing LICENSE')
    runtime = home / 'Library/Application Support/chatgpt-usage-hud/runtime'
    (runtime / 'scripts').mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_FILES:
        shutil.copy2(source / 'scripts' / name, runtime / 'scripts' / name)
        if name.endswith('.sh'):
            (runtime / 'scripts' / name).chmod(0o755)
    shutil.copy2(source / 'LICENSE', runtime / 'LICENSE')
    plist = home / 'Library/LaunchAgents' / f'{LABEL}.plist'
    plist.parent.mkdir(parents=True, exist_ok=True)
    config = {
        'Label': LABEL,
        'ProgramArguments': ['/bin/bash', str(runtime / 'scripts/start_codex_monitor.sh'), str(port), '--no-reopen-after-quit'],
        'RunAtLoad': True, 'KeepAlive': True, 'ProcessType': 'Background',
        'ThrottleInterval': 15, 'StandardOutPath': '/dev/null', 'StandardErrorPath': '/dev/null',
        'EnvironmentVariables': {
            'PATH': str(Path(python).parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
            'PYTHONDONTWRITEBYTECODE': '1',
        },
    }
    with plist.open('wb') as handle:
        plistlib.dump(config, handle)
    plist.chmod(0o600)
    return plist


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=9222)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This installer requires macOS')
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535')
    source = Path(__file__).resolve().parents[1]
    home = Path.home()
    # Validate the download before stopping an existing working installation.
    if not all((source / 'scripts' / name).is_file() for name in RUNTIME_FILES) or not (source / 'LICENSE').is_file():
        parser.error('Incomplete package; extract the full ZIP before installing')
    domain = f'gui/{os.getuid()}'
    service = domain + '/' + LABEL
    installed = home / 'Library/LaunchAgents' / f'{LABEL}.plist'
    if installed.exists() and plistlib.loads(installed.read_bytes()).get('Label') != LABEL:
        parser.error('Refusing to overwrite an unrelated LaunchAgent')
    loaded = subprocess.run(['launchctl', 'print', service], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if loaded:
        subprocess.run(['launchctl', 'bootout', service], check=True)
    plist = prepare_install(source, home, sys.executable, args.port)
    subprocess.run(['plutil', '-lint', str(plist)], check=True)
    subprocess.run(['launchctl', 'enable', service], check=True)
    subprocess.run(['launchctl', 'bootstrap', domain, str(plist)], check=True)
    print('Installed. The HUD waits for ChatGPT/Codex to open.')
    print('安裝完成。HUD 會等待 ChatGPT/Codex 開啟。')
    print('A normal app restart may occur to enable local debugging; active quit refusals are retried later.')
    print('可能正常重開 App 一次以啟用本機除錯；App 暫時拒絕退出時會稍後重試。')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError):
        print('Installation failed. Check the package and rerun install.sh; no app data was removed.', file=sys.stderr)
        raise SystemExit(1)
