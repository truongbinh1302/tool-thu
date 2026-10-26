"""Windows integration checks for stale servers, upgrades and saved data."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from start import running_info
from thu.common import uid
from thu.service import Service
from thu import __version__

ROOT = Path(__file__).resolve().parents[1]


class LauncherUpgrade(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='Tool Thư nâng cấp ')
        self.base = Path(self.tmp.name)
        self.data = self.base / 'dữ liệu'
        self.data.mkdir()
        self.env = {**os.environ, 'PYTHONIOENCODING': 'utf-8', 'TOOL_THU_NO_PAUSE': '1'}

    def tearDown(self):
        self.run_cli('--stop')
        self.tmp.cleanup()

    def command(self, *args, root=ROOT):
        return [sys.executable, '-X', 'utf8', str(root / 'start.py'),
                '--data-dir', str(self.data), '--no-browser', *args]

    def run_cli(self, *args, root=ROOT):
        return subprocess.run(self.command(*args, root=root), capture_output=True,
                              encoding='utf-8', env=self.env, timeout=35)

    def start(self, root=ROOT):
        result = self.run_cli(root=root)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads((self.data / 'runtime.json').read_text(encoding='utf-8'))

    def copy_source(self):
        target = self.base / 'bản mới có dấu'
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns('__pycache__', '.git'))
        return target

    def save_teacher(self):
        service = Service(self.data)
        service.command('real', 0, uid(), 'teacher.upsert',
                        {'code': '00123', 'name': 'Cô thử nâng cấp'})
        return service.stores['real'].read()

    def test_legacy_server_without_build_upgrades_and_preserves_data(self):
        before = self.save_teacher()
        legacy = self.base / 'legacy.py'
        legacy.write_text(
            "import sys,json,os\n"
            "from pathlib import Path\n"
            f"sys.path.insert(0,{str(ROOT)!r})\n"
            "from thu.server import LocalServer,Handler\n"
            "original=Handler.get\n"
            "def get(self):\n"
            " if self.path=='/api/health':\n"
            "  return self.send(200,{'app':'tool-thu-local','version':'0.4.2','instance':self.server.instance})\n"
            " return original(self)\n"
            "Handler.get=get\n"
            "d=Path(sys.argv[1]);s=LocalServer(('127.0.0.1',0),d,Path(sys.argv[2])/'web')\n"
            "(d/'starting.lock').touch()\n"
            "(d/'runtime.json').write_text(json.dumps({'pid':os.getpid(),'port':s.server_port}),encoding='utf8')\n"
            "try:s.serve_forever(poll_interval=.1)\n"
            "finally:\n"
            " s.server_close();(d/'runtime.json').unlink(missing_ok=True);(d/'starting.lock').unlink(missing_ok=True)\n",
            encoding='utf-8')
        old = subprocess.Popen([sys.executable, str(legacy), str(self.data), str(ROOT)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=self.env)
        try:
            for _ in range(50):
                if running_info(self.data):
                    break
                time.sleep(.1)
            self.assertEqual(running_info(self.data)['version'], '0.4.2')
            current = self.start()
            self.assertNotEqual(current['pid'], old.pid)
            self.assertEqual(running_info(self.data)['version'], __version__)
            self.assertTrue(running_info(self.data)['build'])
            self.assertEqual(Service(self.data).stores['real'].read(), before)
            old.wait(timeout=5)
        finally:
            if old.poll() is None:
                old.terminate()
                old.wait(timeout=5)

    def test_new_folder_and_edited_css_restart_same_version(self):
        before = self.save_teacher()
        first = self.start()
        copied = self.copy_source()
        second = self.start(root=copied)
        self.assertNotEqual(first['pid'], second['pid'])
        self.assertNotEqual(first['build'], second['build'])
        css = copied / 'web/style.css'
        with css.open('a', encoding='utf-8') as handle:
            handle.write('\n/* changed asset for restart regression */\n')
        third = self.start(root=copied)
        self.assertNotEqual(second['pid'], third['pid'])
        self.assertEqual(self.start(root=copied), third)
        self.assertEqual(Service(self.data).stores['real'].read(), before)

    def test_concurrent_open_reuses_one_server(self):
        processes = [subprocess.Popen(self.command(), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      env=self.env) for _ in range(4)]
        for process in processes:
            output, error = process.communicate(timeout=35)
            self.assertEqual(process.returncode, 0, error.decode('utf-8') + output.decode('utf-8'))
        info = self.start()
        self.assertEqual(self.start(), info)

    def test_corrupt_database_logs_failure_without_overwriting(self):
        raw = b'invalid sqlite fixture'
        (self.data / 'real.sqlite3').write_bytes(raw)
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('startup.log', result.stderr)
        self.assertIn('DatabaseError', (self.data / 'startup.log').read_text(encoding='utf-8'))
        self.assertEqual((self.data / 'real.sqlite3').read_bytes(), raw)
        self.assertIsNone(running_info(self.data))
        self.assertFalse((self.data / 'starting.lock').exists())

    def test_diagnose_does_not_start_or_create_database(self):
        result = self.run_cli('--diagnose')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['current'])
        self.assertEqual(list(self.data.iterdir()), [])
        self.start()
        self.assertTrue(json.loads(self.run_cli('--diagnose').stdout)['current'])

    def test_invalid_or_foreign_runtime_is_not_reused(self):
        for raw in ('[]', '{"port":null}', '{"port":1}', 'bad json'):
            (self.data / 'runtime.json').write_text(raw, encoding='utf-8')
            self.assertIsNone(running_info(self.data))
        other = self.base / 'other-data'
        other.mkdir()
        current = self.start()
        (other / 'runtime.json').write_text(json.dumps(current), encoding='utf-8')
        self.assertIsNone(running_info(other))
        self.assertEqual(self.start(), current)

    @unittest.skipUnless(os.name == 'nt', 'Windows batch launchers')
    def test_windows_batch_open_diagnose_stop(self):
        def batch(name, *args):
            return subprocess.run([str(ROOT / name), '--data-dir', str(self.data), *args],
                                  capture_output=True, encoding='utf-8', env=self.env, timeout=35)
        opened = batch('Mo_tool_Thu_Windows.bat', '--no-browser')
        self.assertEqual(opened.returncode, 0, opened.stdout + opened.stderr)
        checked = batch('Kiem_tra_Tool_Thu_Windows.bat')
        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
        self.assertTrue(json.loads(checked.stdout)['current'])
        stopped = batch('Dung_tool_Thu_Windows.bat')
        self.assertEqual(stopped.returncode, 0, stopped.stdout + stopped.stderr)
        self.assertIsNone(running_info(self.data))

