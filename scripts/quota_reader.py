#!/usr/bin/env python3
"""Read normalized Codex quota through the app's official local stdio protocol."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import time


class QuotaError(RuntimeError):
    """Safe to display: never includes raw RPC output or credentials."""


def parse_quota(result):
    result = result if isinstance(result, dict) else {}
    buckets = result.get('rateLimitsByLimitId')
    bucket = buckets.get('codex') if isinstance(buckets, dict) and buckets else result.get('rateLimits')
    bucket = bucket if isinstance(bucket, dict) else {}
    if bucket.get('limitId') not in (None, 'codex'):
        bucket = {}
    windows = {'5h': None, '7d': None}
    for key in ('primary', 'secondary'):
        value = bucket.get(key)
        if not isinstance(value, dict):
            continue
        minutes = value.get('windowDurationMins')
        name = '5h' if minutes == 300 else '7d' if minutes == 10080 else None
        percent = value.get('usedPercent')
        if name is None or type(percent) not in (int, float) or not math.isfinite(percent) or not 0 <= percent <= 100:
            continue
        reset = value.get('resetsAt')
        # Bound to representable calendar timestamps; bool is not a timestamp.
        reset = reset if type(reset) is int and 0 < reset <= 253402300799 else None
        windows[name] = {'usedPercent': percent, 'resetsAt': reset}
    credits = None
    raw = bucket.get('credits')
    if isinstance(raw, dict):
        balance = raw.get('balance')
        unlimited = raw.get('unlimited') is True
        if isinstance(balance, str) and re.fullmatch(r'\d{1,18}(?:\.\d{1,8})?', balance):
            credits = {'balance': balance, 'unlimited': unlimited}
        elif unlimited:
            credits = {'balance': None, 'unlimited': True}
    return {'source': 'codex', 'windows': windows, 'credits': credits, 'observedAt': int(time.time())}


def read_quota(command=None, timeout=15):
    if timeout <= 0 or not math.isfinite(timeout):
        raise QuotaError('Invalid quota timeout')
    if command is None:
        candidates = [Path('/Applications/ChatGPT.app'), Path('/Applications/Codex.app'),
                      Path.home() / 'Applications/ChatGPT.app', Path.home() / 'Applications/Codex.app']
        binary = next((p / 'Contents/Resources/codex' for p in candidates
                       if os.access(p / 'Contents/Resources/codex', os.X_OK)), None)
        if binary is None:
            raise QuotaError('Bundled Codex executable unavailable')
        command = [str(binary), 'app-server']
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, bufsize=0)
    except OSError:
        raise QuotaError('Unable to start quota reader') from None
    selector = selectors.DefaultSelector()
    try:
        selector.register(process.stdout, selectors.EVENT_READ)
        def send(message):
            process.stdin.write((json.dumps(message) + '\n').encode())
            process.stdin.flush()
        send({'id': 1, 'method': 'initialize', 'params': {
            'clientInfo': {'name': 'chatgpt_usage_hud', 'version': '0.1.0'}}})
        deadline = time.monotonic() + timeout
        pending = b''
        expected = 1
        while time.monotonic() < deadline:
            if not selector.select(max(0, deadline - time.monotonic())):
                break
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                raise QuotaError('Quota reader closed before response')
            pending += chunk
            if len(pending) > 1024 * 1024:
                raise QuotaError('Quota response exceeds size limit')
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                try:
                    message = json.loads(line)
                except (ValueError, UnicodeError):
                    raise QuotaError('Invalid quota response') from None
                if not isinstance(message, dict):
                    raise QuotaError('Invalid quota response')
                if message.get('id') != expected:
                    continue
                if 'error' in message:
                    raise QuotaError('Quota request unavailable; check existing Codex sign-in')
                if not isinstance(message.get('result'), dict):
                    raise QuotaError('Invalid quota response')
                if expected == 1:
                    send({'method': 'initialized'})
                    send({'id': 2, 'method': 'account/rateLimits/read', 'params': {}})
                    expected = 2
                else:
                    return parse_quota(message['result'])
        raise QuotaError('Quota request timed out')
    except OSError:
        raise QuotaError('Quota transport unavailable') from None
    finally:
        selector.close()
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stdin.close()
        process.stdout.close()


if __name__ == '__main__':
    try:
        print(json.dumps(read_quota(), ensure_ascii=False, allow_nan=False))
    except QuotaError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
