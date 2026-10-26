import unittest,tempfile,subprocess,sys,json,socket,time
from pathlib import Path
from start import health
class Launcher(unittest.TestCase):
 def test_port_busy_open_twice_stop_and_path_with_spaces(self):
  with tempfile.TemporaryDirectory(prefix='tool Thư test ') as directory:
   directory=Path(directory);sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.listen();script=str(Path(__file__).resolve().parents[1]/'start.py')
   def run(*args):return subprocess.run([sys.executable,script,'--data-dir',str(directory),'--no-browser','--port',str(port),*args],capture_output=True,text=True,encoding='utf-8',timeout=30)
   try:
    r=run();self.assertEqual(r.returncode,0,r.stderr);first=json.loads((directory/'runtime.json').read_text());self.assertNotEqual(first['port'],port);self.assertIsNotNone(health(directory));r=run();self.assertEqual(r.returncode,0);second=json.loads((directory/'runtime.json').read_text());self.assertEqual(first,second)
   finally:run('--stop');sock.close()
   for _ in range(20):
    if not health(directory):break
    time.sleep(.1)
   self.assertIsNone(health(directory));self.assertTrue((directory/'real.sqlite3').exists())
