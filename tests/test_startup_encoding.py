"""Reproduce Windows cp1252 text defaults without requiring a Windows host."""
import io,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from thu.common import demo_state
from thu.service import Service

class StartupEncoding(unittest.TestCase):
 def setUp(self):
  self.original_open=io.open
  seed=Path(__file__).resolve().parents[1]/'examples/demo-seed.json'
  self.raw=seed.read_bytes()
  self.expected=json.loads(self.raw.decode('utf-8'))['teachers'][0]['name']
 def ansi_open(self,file,mode='r',buffering=-1,encoding=None,*args,**kwargs):
  if 'b' not in mode and encoding in (None,'locale'):encoding='cp1252'
  return self.original_open(file,mode,buffering,encoding,*args,**kwargs)
 def test_seed_vietnamese_with_windows_ansi_default(self):
  with self.assertRaises(UnicodeDecodeError):self.raw.decode('cp1252')
  with patch('io.open',side_effect=self.ansi_open):state=demo_state()
  self.assertEqual(state['teachers'][0]['name'],self.expected)
  self.assertEqual(len(state['teachers']),20)
 def test_first_start_and_reopen_with_windows_ansi_default(self):
  with tempfile.TemporaryDirectory(prefix='tool Thư ANSI ') as directory:
   with patch('io.open',side_effect=self.ansi_open):
    first=Service(directory)
    demo=first.snapshot('demo')
    self.assertEqual(demo['teachers'][0]['name'],self.expected)
    self.assertEqual(first.snapshot('real')['teachers'],[])
    again=Service(directory).snapshot('demo')
    self.assertEqual(again['teachers'][0]['id'],demo['teachers'][0]['id'])
    self.assertEqual(again['teachers'][0]['name'],self.expected)
