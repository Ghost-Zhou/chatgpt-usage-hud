# Changelog / 更新记录

## 0.1.0 — 2026-09-09

- Codex 5H/7D percent-used progress bars in the app header, with a floating fallback.
- Expanded reset countdowns, credits and original session/context token details.
- Background quota polling; explicit unavailable/stale/expired states.
- Preserved expanded dragging and theme inheritance; prevented countdown-driven session rescans.
- Fixed permanent startup suppression after one deferred normal app quit; retries are spaced by at least 60 seconds.
- Portable user LaunchAgent installer, update/uninstall instructions and bilingual documentation.
- Preserved Kevin Ke's original MIT license and attribution.

- 在 App header 显示 Codex 5H／7D 已用额度进度条，空间不足时浮动。
- 展开显示重置倒计时、credits 和原有 session／context token。
- 后台读取额度，并明确标记不可用、过期与等待重置更新。
- 保留展开拖动与主题继承，避免倒计时触发重复 session 扫描。
- 修复 App 一次暂缓退出后不再重试的问题；重试至少间隔 60 秒。
- 提供用户级 LaunchAgent 安装器、更新／卸载方法和中英文说明。
- 保留 Kevin Ke 的原 MIT 许可证及署名。
