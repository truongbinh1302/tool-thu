from test_local import Domain
from thu.common import AppError
class Edges(Domain):
 def test_shifted_qc_duplicate_vs_distinct(self):
  self.teacher();p=self.plan('Code,Date,Detail\n00123,20/10/2026,123\n00123,20/10/2026,Lỗi A\n00123,20/10/2026,Lỗi A\n00123,20/10/2026,Lỗi B\n','qc',{'teacherCode':0,'date':1,'detail':2});self.assertEqual(p['counts']['error'],1);self.assertEqual(p['counts']['review'],1);self.assertEqual(p['counts']['create'],2)
 def test_teacher_alias_column_applied(self):
  p=self.plan('Code,Name,Alias\n00123,Cô Thử,C99\n','teachers',{'code':0,'name':1,'alias':2});self.commit(p);self.assertEqual(self.db.read()['aliases'][0]['code'],'C99')
 def test_task_changed_note_updates_same_identity(self):
  mapping={'title':0,'date':1,'note':2};self.commit(self.plan('Title,Date,Note\nViệc A,20/10/2026,Ghi chú 1\n','tasks',mapping));p=self.plan('Title,Date,Note\nViệc A,20/10/2026,Ghi chú 2\n','tasks',mapping,{'sourceName':'fixture','policy':'overwrite'});self.assertEqual(p['counts']['update'],1);self.commit(p);self.assertEqual(len(self.db.read()['tasks']),1);self.assertEqual(self.db.read()['tasks'][0]['note'],'Ghi chú 2')
def load_tests(loader,suite,pattern):
 import unittest
 return unittest.TestSuite(Edges(n) for n in ('test_shifted_qc_duplicate_vs_distinct','test_teacher_alias_column_applied','test_task_changed_note_updates_same_identity'))
