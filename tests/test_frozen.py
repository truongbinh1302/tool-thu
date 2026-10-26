"""Packaged-app (PyInstaller) behaviour, simulated by setting sys.frozen / sys._MEIPASS."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import start  # noqa: E402
from thu import runtime  # noqa: E402
from thu.common import demo_state  # noqa: E402


class FrozenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='thu frozen ố '))
        self.bundle = self.tmp / 'Tool Thư.app' / 'Contents' / 'Resources'
        shutil.copytree(ROOT / 'web', self.bundle / 'web')
        (self.bundle / 'examples').mkdir(parents=True)
        shutil.copy(ROOT / 'examples' / 'demo-seed.json', self.bundle / 'examples')
        self.exe = self.tmp / 'Tool Thư.app' / 'Contents' / 'MacOS' / 'ToolThu'
        self.exe.parent.mkdir(parents=True)
        self.exe.write_bytes(b'fake executable')
        self.patches = [mock.patch.object(sys, 'frozen', True, create=True),
                        mock.patch.object(sys, '_MEIPASS', str(self.bundle), create=True),
                        mock.patch.object(sys, 'executable', str(self.exe))]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_resources_come_from_bundle(self):
        self.assertTrue(runtime.is_frozen())
        self.assertEqual(runtime.resource_root(), self.bundle.resolve())
        self.assertGreater(len(demo_state()['teachers']), 0)

    def test_server_command_reruns_app_without_script_or_python_flags(self):
        cmd = start.server_command(Path('/data dir/ToolThu'), 28765)
        self.assertEqual(cmd[0], str(self.exe))
        self.assertNotIn('-X', cmd)
        self.assertFalse(any(part.endswith('start.py') for part in cmd))
        self.assertIn('--serve', cmd)
        self.assertEqual(cmd[cmd.index('--data-dir') + 1], '/data dir/ToolThu')

    def test_build_id_without_source_files_changes_with_app(self):
        first = runtime.build_id()
        self.assertEqual(first, runtime.build_id())
        self.exe.write_bytes(b'newer executable')
        self.assertNotEqual(first, runtime.build_id())

    def test_source_mode_unchanged(self):
        with mock.patch.object(sys, 'frozen', False):
            self.assertEqual(runtime.resource_root(), ROOT)
            cmd = start.server_command(Path('/d'), 1234)
            self.assertEqual(cmd[1:4], ['-X', 'utf8', str(ROOT / 'start.py')])


if __name__ == '__main__':
    unittest.main()
