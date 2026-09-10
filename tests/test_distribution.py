import importlib.util
import pathlib
import plistlib
import tempfile
import unittest
import zipfile
import hashlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def test_release_uses_allowlist_and_correct_checksum(self):
        path = ROOT / 'scripts/build_release.py'
        self.assertTrue(path.exists(), 'release builder is missing')
        spec = importlib.util.spec_from_file_location('build_release', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            archive, checksum, staged = module.build(ROOT, pathlib.Path(directory))
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
                self.assertEqual(len(names), len(module.FILES))
                self.assertFalse(any('.local-context' in n or 'PROJECT_CONTEXT' in n or '/.git/' in n for n in names))
                self.assertTrue(any(n.endswith('/README.zh-CN.md') for n in names))
            self.assertIn(hashlib.sha256(archive.read_bytes()).hexdigest(), checksum.read_text())
            self.assertEqual((staged / 'LICENSE').read_bytes(), (ROOT / 'LICENSE').read_bytes())
            (staged / 'private-note.txt').write_text('synthetic local note')
            with self.assertRaisesRegex(ValueError, 'Unexpected staged files'):
                module.build(ROOT, pathlib.Path(directory))

    def test_installer_prepares_only_runtime_files_and_portable_plist(self):
        path = ROOT / 'scripts' / 'manage_service.py'
        self.assertTrue(path.exists(), 'portable service installer is missing')
        spec = importlib.util.spec_from_file_location('manage_service', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='hud test & ') as directory:
            home = pathlib.Path(directory)
            plist = module.prepare_install(ROOT, home, '/test path/python3', 9333)
            config = plistlib.loads(plist.read_bytes())
            self.assertEqual(config['Label'], 'com.local.chatgpt-usage-hud')
            self.assertEqual(config['ProgramArguments'][-2:], ['9333', '--no-reopen-after-quit'])
            runtime = home / 'Library/Application Support/chatgpt-usage-hud/runtime'
            self.assertEqual((runtime / 'LICENSE').read_bytes(), (ROOT / 'LICENSE').read_bytes())
            for name in module.RUNTIME_FILES:
                self.assertEqual((runtime / 'scripts' / name).read_bytes(), (ROOT / 'scripts' / name).read_bytes())
            self.assertFalse((runtime / 'PROJECT_CONTEXT.md').exists())
            self.assertFalse((runtime / '.local-context').exists())
            self.assertEqual(config['StandardErrorPath'], '/dev/null')
            self.assertTrue(config['EnvironmentVariables']['PATH'].startswith('/test path:'))

    def test_installer_rejects_invalid_ports_before_writing(self):
        path = ROOT / 'scripts' / 'manage_service.py'
        self.assertTrue(path.exists(), 'portable service installer is missing')
        spec = importlib.util.spec_from_file_location('manage_service', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            for port in [0, -1, 65536]:
                with self.assertRaises(ValueError):
                    module.prepare_install(ROOT, home, '/test/python3', port)
            self.assertEqual(list(home.iterdir()), [])
