import sys
import unittest
import threading
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import context_token_injector as hud
from quota_reader import QuotaError


class QuotaCacheTests(unittest.TestCase):
    def test_background_refresh_does_not_block_or_overlap(self):
        self.assertTrue(hasattr(hud, '_QUOTA_WORKER'), 'background refresh is not implemented')
        hud._QUOTA_CACHE = None
        entered, release = threading.Event(), threading.Event()
        snapshot = {'source': 'codex', 'windows': {'5h': None, '7d': None}}
        def read():
            entered.set()
            release.wait(2)
            return snapshot
        with patch.object(hud, 'read_quota', side_effect=read) as reader:
            try:
                initial = hud.cached_quota(background=True)
                self.assertTrue(entered.wait(1))
                self.assertIsNone(initial['windows']['5h'])
                hud.cached_quota(background=True)
                self.assertEqual(reader.call_count, 1)
            finally:
                release.set()
                hud._QUOTA_WORKER.join(2)
            self.assertEqual(hud.cached_quota(background=True), snapshot)

    def test_refresh_is_cached_and_failure_replaces_old_values(self):
        self.assertTrue(hasattr(hud, 'cached_quota'), 'quota cache is not implemented')
        hud._QUOTA_CACHE = None
        snapshot = {'source': 'codex', 'windows': {'5h': {'usedPercent': 67}}}
        with patch.object(hud, 'read_quota', side_effect=[snapshot, QuotaError('Quota request timed out')]) as read:
            with patch.object(hud.time, 'monotonic', return_value=100):
                self.assertEqual(hud.cached_quota(), snapshot)
            with patch.object(hud.time, 'monotonic', return_value=219):
                self.assertEqual(hud.cached_quota(), snapshot)
                self.assertEqual(read.call_count, 1)
            with patch.object(hud.time, 'monotonic', return_value=220):
                failed = hud.cached_quota()
                self.assertIsNone(failed['windows']['5h'])
                self.assertEqual(failed['error'], 'Quota unavailable')
                self.assertEqual(read.call_count, 2)
