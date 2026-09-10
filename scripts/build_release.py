#!/usr/bin/env python3
"""Build the audited source package without local context or Git history."""
import hashlib
from pathlib import Path
import shutil
import zipfile

VERSION = '0.1.0'
FILES = (
    '.gitignore', 'README.md', 'README.zh-CN.md', 'LICENSE', 'CHANGELOG.md',
    'install.sh', 'uninstall.sh', 'docs/TESTING.md',
    'assets/hud-compact.png', 'assets/hud-expanded.png',
    'scripts/start_codex_monitor.sh', 'scripts/reopen_codex_with_debug.sh',
    'scripts/port_utils.sh', 'scripts/context_token_injector.py',
    'scripts/context_token_inspector.py', 'scripts/quota_reader.py',
    'scripts/quota_hud.js', 'scripts/manage_service.py', 'scripts/build_release.py',
    'tests/test_runtime_scripts.py', 'tests/test_context_token_inspector.py',
    'tests/test_quota_reader.py', 'tests/test_quota_hud.py',
    'tests/test_distribution.py', 'tests/quota_hud.browser.cjs',
)


def build(source, output):
    for name in FILES:
        if not (source / name).is_file():
            raise ValueError(f'Missing release file: {name}')
    title = f'chatgpt-usage-hud-v{VERSION}'
    staged = output / 'source' / title
    if staged.exists():
        unexpected = [p for p in staged.rglob('*')
                      if p.is_symlink() or p.is_file() and p.relative_to(staged).as_posix() not in FILES]
        if unexpected:
            raise ValueError('Unexpected staged files; use a clean output directory')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'{title}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
        for name in FILES:
            src = source / name
            dest = staged / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            # Pin archive timestamps and permissions for reproducible packages.
            entry = zipfile.ZipInfo(f'{title}/{name}', date_time=(2026, 9, 9, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o100755 if name.endswith('.sh') else 0o100644
            entry.external_attr = mode << 16
            bundle.writestr(entry, src.read_bytes())
    checksum = output / 'SHA256SUMS.txt'
    checksum.write_text(f'{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n')
    return archive, checksum, staged


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    for output in build(root, root / 'dist'):
        print(output)
