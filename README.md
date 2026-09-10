# ChatGPT Usage HUD

[简体中文](README.zh-CN.md) · [Testing](docs/TESTING.md) · [MIT license](LICENSE)

A small **Codex usage HUD inside the macOS ChatGPT/Codex desktop window**. The compact view docks in free header space and shows 5-hour and 7-day progress bars. Expand it for reset countdowns, available credits and session-token details.

**The percentages mean quota used, not remaining. This does not measure every ChatGPT model's quota.** It uses the Codex account signed in to the app's bundled Codex service.

![Compact HUD with synthetic example values](assets/hud-compact.png)

![Expanded HUD with synthetic example values](assets/hud-expanded.png)

Screenshots contain synthetic example data, not a real account's usage.

## Requirements

- macOS with the current integrated ChatGPT desktop app or a compatible Codex desktop app.
- A signed-in Codex account and an app bundle containing `Contents/Resources/codex`.
- A working **Python 3.10+**. No pip packages are needed for normal use. The installer tries your existing Python, common Homebrew locations, then Codex's bundled Python runtime if present.
- An app build that supports Chromium's local remote-debugging flags. The separate native ChatGPT client without the Codex renderer/bundled service is not supported.

The initial runtime was tested on Apple Silicon with ChatGPT **26.901.51231** and bundled Codex **0.153.4**. Compatibility can change after app updates; other builds are not guaranteed.

## Install and enable automatic startup

1. Download the `chatgpt-usage-hud-v0.1.0.zip` release asset, or download the repository using **Code → Download ZIP**.
2. Extract the ZIP completely. Keep the `scripts` folder alongside `install.sh`.
3. Finish or save active app work. Open Terminal, type `cd `, drag the extracted folder into Terminal, then press Return.
4. Run:

```sh
bash install.sh
```

No `sudo` is needed. The installer copies the runtime to:

```text
~/Library/Application Support/chatgpt-usage-hud/runtime
```

It registers this user-only background service:

```text
~/Library/LaunchAgents/com.local.chatgpt-usage-hud.plist
```

The runtime is copied out of Downloads/Documents so macOS background-file restrictions do not block it. You may move the extracted download afterward. Keep the Python installation available.

### What happens when you open the app

- The service waits while ChatGPT/Codex is closed. It does **not** open the app by itself.
- When you open the app normally, the HUD may take roughly 15–30 seconds to appear.
- If local debugging is absent, the service asks the app to **quit normally and reopen once** with loopback debugging enabled. It never force-quits.
- If the app refuses to quit, the service waits at least 60 seconds before trying again. Save/finish active work and allow time for the retry.
- If an app successfully reopens but rejects debugging, the service avoids repeatedly restarting that same process. See troubleshooting below.
- The service is registered for your future sign-ins. A full logout/login acceptance test has not yet been completed.

A custom starting port can be supplied with `bash install.sh --port 9333`. An occupied foreign port is skipped automatically.

## Everyday use

- **Header:** 5H and 7D show the percentage used with progress bars. Click **+** or the compact label to expand.
- **Expanded:** see reset time/countdown, credits when available, and original context/turn/session token details. The raw/K/M controls apply to token counts.
- **Move:** drag an empty area of the expanded panel's top strip. Collapse with **−** to return to the header.
- **Small window:** if no safe header space exists, the compact HUD floats instead of covering header controls.
- **Refresh:** Codex quota is read in the background every 120 seconds; session data refreshes every 10 seconds; countdowns tick every second.
- **Missing/old data:** `—` means unavailable, not zero. Data older than 240 seconds is marked stale. An elapsed reset says “Awaiting refresh”; it does not assume a reset already happened.
- The HUD follows the app's light/dark appearance. No-session pages can still show quota.

## Update

Download and extract the new version, then run `bash install.sh` from that version's folder. This refreshes the installed runtime and reloads the same service. **Editing or pulling the source checkout alone does not update the installed copy.** App conversations, session files and login data are not removed.

## Stop or uninstall

From an extracted package, run:

```sh
bash uninstall.sh
```

This disables automatic startup and removes this project's LaunchAgent registration. It preserves runtime files and app data. Then quit and reopen the app normally to remove the current HUD and close its debugging port.

For a temporary stop without removing the registration:

```sh
launchctl bootout "gui/$(id -u)/com.local.chatgpt-usage-hud"
```

Run `bash install.sh` again to restore it. The upstream `scripts/install_launch_agent.sh` and `scripts/uninstall_launch_agent.sh` target a different service; they are not part of this release's installation workflow.

## Troubleshooting

| Symptom | Check / action |
| --- | --- |
| HUD missing just after startup | Allow 15–30 seconds; if the app deferred quitting, allow at least 60 seconds after finishing work. |
| Still missing | Run the status command below. If the service is absent, reinstall from the latest extracted package. |
| Service running, no HUD | Check the local port. Finish app work, then restart the service with the command below. The app may reopen normally. |
| Python/Xcode error | The installer tries an alternative runnable Python without accepting Xcode's license or changing Xcode settings. If none works, install Python 3.10+ from a trusted distribution and rerun. |
| `Operation not permitted` under Documents | Use this release's `install.sh`, which copies the runtime into Application Support. Do not point a custom LaunchAgent at the Documents checkout. |
| Quota unavailable | Confirm Codex is signed in and the app includes its bundled service; wait for the next refresh. Do not paste auth files or tokens into an issue. |
| Broke after an app update | The app may have changed its renderer or debugging support. Reinstall the current release and report only app version and sanitized errors. |

```sh
# Service status (a running service is not proof that the HUD is visible)
launchctl print "gui/$(id -u)/com.local.chatgpt-usage-hud"

# Default loopback listener; use your chosen/resolved port if different
lsof -nP -iTCP:9222 -sTCP:LISTEN

# Restart this service after finishing active app work
launchctl kickstart -k "gui/$(id -u)/com.local.chatgpt-usage-hud"
```

## Privacy and limits

The HUD uses runtime CDP/DOM injection and the official local `account/rateLimits/read` protocol. It does not patch the app bundle, ask for an API key, redeem reset credits, or upload data to a third-party usage service. The app's official service may contact OpenAI to fetch account quota.

Only normalized quota data is passed to the HUD. Usage snapshots stay in memory; the installed service discards stdout/stderr. Existing local session logs are read for token details. This repository/package excludes private chat handoff files, account snapshots, credentials and local paths from development notes.

Local debugging grants powerful renderer access to local processes. It binds only to loopback; never expose it to your LAN. Normal app launch without the debug flags closes this access after the automatic service has been stopped.

## Attribution

Based on [KevinKE93/Codex-Monitor](https://github.com/KevinKE93/Codex-Monitor), upstream revision `56b2ea3`. The original MIT copyright/license is preserved. This derivative adds Codex quota, header progress bars, safe startup retries and a portable installer. The visual “Made by Kevin” label is removed; authorship is credited here and in LICENSE. This is an independent project, not an official OpenAI product.
