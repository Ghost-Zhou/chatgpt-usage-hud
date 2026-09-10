import http.server
import json
import os
import pathlib
import plistlib
import subprocess
import tempfile
import threading
import unittest


PLUGIN_ROOT = pathlib.Path(__file__).resolve().parents[1]
PORT_UTILS = PLUGIN_ROOT / "scripts" / "port_utils.sh"


class RuntimeScriptTests(unittest.TestCase):
    def test_deferred_relaunch_retries_after_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            script = (PLUGIN_ROOT / 'scripts/start_codex_monitor.sh').read_text()
            (root / 'launcher.sh').write_text(script.split('\nwhile true; do', 1)[0])
            (root / 'port_utils.sh').write_text('''
codex_monitor_resolve_port() { echo 9222; }
codex_monitor_devtools_ready() { test -f "$TEST_DIR/ready"; }
codex_monitor_app_running() { return 0; }
codex_monitor_app_pid() { echo 42; }
codex_monitor_wait_for_devtools() { return 0; }
''')
            reopen = root / 'reopen_codex_with_debug.sh'
            reopen.write_text('''#!/bin/bash
echo attempt >> "$TEST_DIR/attempts"
if [[ $(wc -l < "$TEST_DIR/attempts") -lt 2 ]]; then exit 1; fi
touch "$TEST_DIR/ready"
''')
            reopen.chmod(0o700)
            env = os.environ.copy()
            env['TEST_DIR'] = directory
            result = self.run_bash('''
source "$TEST_DIR/launcher.sh"
ensure_devtools || true
ensure_devtools || true
echo "before=$(wc -l < "$TEST_DIR/attempts" | tr -d ' ')"
SECONDS=61
ensure_devtools || true
echo "after=$(wc -l < "$TEST_DIR/attempts" | tr -d ' ')"
test -f "$TEST_DIR/ready" && echo ready || true
''', env)
            self.assertIn('before=1', result)
            self.assertIn('after=2', result)
            self.assertIn('ready', result)

    def make_app(self, executable="FutureCodex", bundle_id="com.example.future-codex"):
        root = pathlib.Path(tempfile.mkdtemp()) / "Future.app"
        contents = root / "Contents"
        contents.mkdir(parents=True)
        with (contents / "Info.plist").open("wb") as handle:
            plistlib.dump(
                {"CFBundleExecutable": executable, "CFBundleIdentifier": bundle_id},
                handle,
            )
        return root

    def run_bash(self, command, env=None):
        return subprocess.run(
            ["/bin/bash", "-c", command],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        ).stdout

    def serve_devtools_targets(self, targets):
        payload = json.dumps(targets).encode("utf-8")

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path != "/json":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *_args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server.server_port

    def test_app_override_supports_future_bundle_names(self):
        app = self.make_app()
        env = os.environ.copy()
        env["CODEX_MONITOR_APP_PATH"] = str(app)

        output = self.run_bash(
            f'source "{PORT_UTILS}"; codex_monitor_find_app; '
            "codex_monitor_app_executable; codex_monitor_app_bundle_id",
            env,
        ).splitlines()

        self.assertEqual(output, [str(app), "FutureCodex", "com.example.future-codex"])

    def test_app_discovery_does_not_require_home(self):
        app = self.make_app()
        env = os.environ.copy()
        env.pop("HOME", None)
        env["CODEX_MONITOR_APP_PATH"] = str(app)

        output = self.run_bash(
            f'set -u; source "{PORT_UTILS}"; codex_monitor_find_app',
            env,
        ).strip()

        self.assertEqual(output, str(app))

    def test_runtime_shell_scripts_parse(self):
        scripts = sorted((PLUGIN_ROOT / "scripts").glob("*.sh"))
        subprocess.run(["/bin/bash", "-n", *map(str, scripts)], check=True)

    def test_launch_agent_wait_loop_uses_bounded_polling(self):
        script = (PLUGIN_ROOT / "scripts" / "start_codex_monitor.sh").read_text(encoding="utf-8")

        self.assertIn('CODEX_MONITOR_APP_POLL_INTERVAL:-15', script)
        self.assertIn('sleep "${APP_POLL_INTERVAL}"', script)

    def test_devtools_readiness_rejects_foreign_browser_target(self):
        port = self.serve_devtools_targets(
            [{"type": "page", "title": "Example", "url": "https://example.test"}]
        )

        result = subprocess.run(
            [
                "/bin/bash",
                "-c",
                f'source "{PORT_UTILS}"; codex_monitor_devtools_ready "{port}"',
            ],
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        resolved = self.run_bash(
            f'source "{PORT_UTILS}"; codex_monitor_resolve_port "{port}"'
        ).strip()
        self.assertNotEqual(resolved, str(port))

    def test_devtools_ownership_waits_for_integrated_main_window(self):
        port = self.serve_devtools_targets(
            [
                {
                    "type": "page",
                    "title": "Codex",
                    "url": "app://-/index.html?initialRoute=%2Favatar-overlay",
                }
            ]
        )

        owned = subprocess.run(
            ["/bin/bash", "-c", f'source "{PORT_UTILS}"; codex_monitor_devtools_owned "{port}"']
        )
        ready = subprocess.run(
            ["/bin/bash", "-c", f'source "{PORT_UTILS}"; codex_monitor_devtools_ready "{port}"']
        )

        self.assertEqual(owned.returncode, 0)
        self.assertNotEqual(ready.returncode, 0)


if __name__ == "__main__":
    unittest.main()
