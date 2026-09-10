import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

class QuotaReaderTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('quota_reader'), 'quota reader must exist')
        import quota_reader
        self.q = quota_reader

    def test_windows_use_duration_and_keyed_bucket(self):
        result = self.q.parse_quota({'rateLimits': {'primary': window(99)},
            'rateLimitsByLimitId': {'codex': {'secondary': window(0), 'primary': window(42, 10080)}}})
        self.assertEqual(result['windows']['5h']['usedPercent'], 0)
        self.assertEqual(result['windows']['7d']['usedPercent'], 42)

    def test_legacy_and_missing(self):
        self.assertEqual(self.q.parse_quota({'rateLimits': {'primary': window(67)}})['windows']['5h']['usedPercent'], 67)
        for raw in ({}, None, [], {'rateLimitsByLimitId': {'other': {}}}, {'rateLimits': {'limitId': 'other', 'primary': window(67)}}):
            self.assertIsNone(self.q.parse_quota(raw)['windows']['5h'])

    def test_invalid_windows(self):
        for value in (None, True, '67', -1, 101, float('nan'), float('inf')):
            with self.subTest(value=value):
                self.assertIsNone(self.q.parse_quota({'rateLimits': {'primary': window(value)}})['windows']['5h'])
        for reset in (None, True, -1, '2000000000'):
            w = window(67); w['resetsAt'] = reset
            self.assertIsNone(self.q.parse_quota({'rateLimits': {'primary': w}})['windows']['5h']['resetsAt'])

    def test_credits_and_privacy(self):
        raw = {'accountId': 'PRIVATE_SENTINEL', 'rateLimits': {'credits': {'balance': '12.50', 'unlimited': False, 'secret': 'PRIVATE_SENTINEL'}}}
        result = self.q.parse_quota(raw)
        self.assertEqual(result['credits'], {'balance': '12.50', 'unlimited': False})
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))
        raw['rateLimits']['credits']['balance'] = '<script>'
        self.assertIsNone(self.q.parse_quota(raw)['credits'])

    def child(self, tail):
        return [sys.executable, '-u', '-c', '''import sys,json,time,os
m=json.loads(sys.stdin.readline());assert m['method']=='initialize'
print(json.dumps({'id':m['id'],'result':{}}),flush=True)
n=json.loads(sys.stdin.readline());assert n['method']=='initialized'
m=json.loads(sys.stdin.readline());assert m['method']=='account/rateLimits/read'
''' + tail]

    def test_reader_protocol_and_notifications(self):
        result = self.q.read_quota(self.child("print(json.dumps({'method':'notice'}));print(json.dumps({'id':m['id'],'result':{'rateLimits':{'primary':" + repr(window(67)) + "}}}),flush=True)"))
        self.assertEqual(result['windows']['5h']['usedPercent'], 67)

    def test_reader_failures_are_sanitized(self):
        for tail in ("print(json.dumps({'id':m['id'],'error':{'message':'PRIVATE_SENTINEL'}}),flush=True)", "print('PRIVATE_SENTINEL',flush=True)", "sys.exit(0)"):
            with self.subTest(tail=tail), self.assertRaises(self.q.QuotaError) as caught:
                self.q.read_quota(self.child(tail), timeout=2)
            self.assertNotIn('PRIVATE_SENTINEL', str(caught.exception))

    def test_timeout_reaps_child(self):
        with tempfile.TemporaryDirectory() as directory:
            pidfile = Path(directory) / 'pid'
            with self.assertRaises(self.q.QuotaError):
                self.q.read_quota(self.child(f"open({str(pidfile)!r},'w').write(str(os.getpid()));time.sleep(30)"), timeout=.5)
            pid = int(pidfile.read_text())
            with self.assertRaises(ProcessLookupError): os.kill(pid, 0)


def window(percent, minutes=300):
    return {'usedPercent': percent, 'windowDurationMins': minutes, 'resetsAt': 2000000000}
