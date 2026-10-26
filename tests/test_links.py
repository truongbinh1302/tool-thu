from test_local import Domain
from thu.common import *
from thu.adapters import FakeCalendarAdapter
class Links(Domain):
 # Inherit only helpers, not the suite a second time (loader below).
 def test_calendar_follows_task_and_case(self):
  t=self.cmd('task.upsert',{'title':'A','date':'2026-10-20'})['id'];event=self.db.read()['events'][0];self.assertEqual(event['taskId'],t);eid=event['id'];self.cmd('task.status',{'id':t,'status':'done'});self.assertTrue(self.db.read()['events'][0]['cancelled']);self.cmd('task.status',{'id':t,'status':'doing'});self.assertFalse(self.db.read()['events'][0]['cancelled']);self.assertEqual(self.db.read()['events'][0]['id'],eid)
  a=self.teacher();p={'code':'L','teacher':a,'due':'2026-10-21','plan':'P'};id=self.cmd('process.upsert',p)['id'];self.cmd('process.upsert',{**p,'id':id,'due':'2026-10-23'});events=[e for e in self.db.read()['events'] if e.get('processId')==id];self.assertEqual(len(events),1);self.assertEqual(events[0]['date'],'2026-10-23');self.cmd('process.milestone',{'id':id,'title':'Liên hệ','date':'2026-10-20'});self.assertEqual(len([e for e in self.db.read()['events'] if e.get('processId')==id]),2)
 def test_fake_adapter_retry_atomic(self):
  adapter=FakeCalendarAdapter();adapter.fail_next=True
  with self.assertRaises(AppError):adapter.upsert('meeting:1',{'title':'M'})
  self.assertEqual(adapter.list(),[]);adapter.upsert('meeting:1',{'title':'M'});adapter.upsert('meeting:1',{'title':'Edited'});self.assertEqual(len(adapter.list()),1);adapter.cancel('meeting:1');self.assertTrue(adapter.list()[0]['cancelled'])
def load_tests(loader,suite,pattern):
 import unittest
 return unittest.TestSuite(Links(n) for n in ('test_calendar_follows_task_and_case','test_fake_adapter_retry_atomic'))
