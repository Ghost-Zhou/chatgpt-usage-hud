# Testing / 测试

Normal use needs only Python 3.10+ and macOS. Development browser checks additionally need Node.js and an existing Playwright installation. Nothing is downloaded by the test runner.

日常使用仅需 Python 3.10+ 和 macOS。浏览器开发测试另需 Node.js 与已安装的 Playwright；测试脚本不会自动下载依赖。

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
bash -n install.sh uninstall.sh
node tests/quota_hud.browser.cjs
```

If Playwright is not in the default module search path, set `NODE_PATH` to its existing `node_modules` directory. Set `PYTHON` to a working Python executable. If bundled Chromium is unavailable, set `CHROME_PATH` to an existing Chrome executable. Tests launch an isolated browser profile with synthetic data, not the user's live browser.

如果找不到 Playwright，请把 `NODE_PATH` 指向现有的 `node_modules`，用 `PYTHON` 指定可运行的 Python。缺少 Chromium 时，可用 `CHROME_PATH` 指向已安装的 Chrome 可执行文件。测试使用隔离浏览器和模拟数据，不操作用户的真实浏览器。

Coverage includes quota parsing, subprocess cleanup, failure/cooldown recovery, non-overlapping background refresh, portable installation files, header controls, missing/stale data, countdowns, dragging, reinjection, narrow windows, theme inheritance and preventing countdown-triggered session rescans.

覆盖额度解析、子进程清理、启动失败后的冷却重试、后台读取不重叠、安装文件、header 按钮、缺失／过期状态、倒计时、拖动、重注入、窄窗口、主题继承，以及防止倒计时触发 session 重扫。

## Acceptance boundaries / 验收边界

Verified locally: live quota, header placement, expand/collapse, ticking countdown, session-token presence, launchd runtime loading from Application Support, app relaunch with loopback CDP and child injector startup. These are point-in-time observations, not a guarantee for all app builds.

本机已验证真实额度、header 定位、展开／收起、倒计时、session token、Application Support 中的 launchd 运行副本、带 loopback CDP 的 App 重开及 injector 启动。这些是当时的验证结果，不保证所有版本兼容。

Not yet fully verified: a logout/login cycle, every manual cross-task transition, and future app-update/renderer-replacement recovery. Do not describe this release as universally compatible or fully unattended across all updates.

尚未全面验证：注销／重新登录、所有手动跨任务切换，以及未来 App 更新／renderer 替换后的恢复。不要把本发行版描述为保证兼容所有更新的完全无人值守方案。

## Release build / 打包

```sh
python3 scripts/build_release.py
```

The builder uses an explicit allowlist. It writes a source ZIP and SHA-256 checksums into `dist/`; it excludes Git history, local context, logs, account data and development handoff notes. `dist/` is not added to Git; upload the ZIP/checksum as release assets.

打包器只收录明确列出的文件，在 `dist/` 生成 ZIP 与 SHA-256 校验文件；不包含 Git 历史、本地上下文、日志、账号数据或私人开发移交记录。`dist/` 不加入 Git，ZIP／校验文件作为 Release 附件上传。
