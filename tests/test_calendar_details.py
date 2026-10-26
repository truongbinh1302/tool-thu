import unittest,tempfile
from thu.service import Service
from thu.common import uid,canonical,AppError
from thu.calendar_service import calendar_events,calendar_ics
class CalendarDetails(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.svc=Service(self.tmp.name);self.db=self.svc.stores['real']
 def tearDown(self):self.tmp.cleanup()
 def cmd(self,n,p):return self.svc.command('real',self.db.read()['_revision'],uid(),n,p)['result']
 def test_meeting_people_content_time_no_invitations_or_attendance(self):
  a=self.cmd('teacher.upsert',{'code':'T01','name':'Cô Hà'})['id'];mid=self.cmd('meeting.upsert',{'title':'Hẹn trao đổi','date':'2026-12-31','time':'20:00','duration':90,'description':'Trao đổi nội dung lớp','invited':[a],'externalGuests':['Chị Linh phụ huynh']})['id'];s=self.db.read();e=s['events'][0]
  self.assertEqual(e['participantNames'],['Cô Hà','Chị Linh phụ huynh']);self.assertEqual(s['meetings'][0]['attendees'],{});self.assertEqual(len(s['teachers']),1)
  unfolded=calendar_ics(calendar_events(s)).decode().replace('\r\n ','');self.assertIn('Trao đổi nội dung lớp',unfolded);self.assertIn('Cô Hà',unfolded);self.assertIn('Chị Linh phụ huynh',unfolded);self.assertIn('DTSTART:20261231T130000Z',unfolded);self.assertIn('DTEND:20261231T143000Z',unfolded);self.assertNotIn('ATTENDEE',unfolded);self.assertNotIn('METHOD:REQUEST',unfolded)
  eid=e['id'];self.cmd('meeting.upsert',{'id':mid,'title':'Đổi nội dung','date':'2027-01-01','time':'19:00','duration':60,'description':'Nội dung mới','invited':[],'externalGuests':['Anh Nam']});events=self.db.read()['events'];self.assertEqual(len(events),1);self.assertEqual(events[0]['id'],eid);self.assertEqual(events[0]['participantNames'],['Anh Nam']);self.assertGreater(events[0]['sequence'],e['sequence'])
 def test_direct_event_guests_normalized_and_historical_roster_stable(self):
  self.cmd('event.upsert',{'title':'Hẹn người ngoài','date':'2026-10-22','time':'08:00','participantNames':' Chị Mai\nChị Mai\nAnh Nam\n'});self.assertEqual(self.db.read()['events'][0]['participantNames'],['Chị Mai','Anh Nam']);self.assertEqual(self.db.read()['teachers'],[])
  tid=self.cmd('teacher.upsert',{'code':'GV','name':'Tên cũ'})['id'];self.cmd('meeting.upsert',{'title':'Họp','date':'2026-10-22','time':'20:00','invited':[tid]});self.cmd('teacher.upsert',{'id':tid,'code':'GV','name':'Tên mới'});self.assertEqual(calendar_events(self.db.read())[-1]['participantNames'],['Tên cũ'])
 def test_legacy_projection_enriches_without_mutating_storage(self):
  store=self.svc.stores['demo'];before=canonical(store.read());e=calendar_events(store.read());self.assertTrue(next(x for x in e if x.get('meetingId'))['participantNames']);self.assertEqual(canonical(store.read()),before)
 def test_invalid_participants_rollback(self):
  rev=self.db.read()['_revision']
  with self.assertRaises(AppError):self.cmd('event.upsert',{'title':'Bad','date':'2026-10-22','time':'08:00','participantNames':['A\nB']})
  self.assertEqual(self.db.read()['_revision'],rev);self.assertEqual(self.db.read()['events'],[])

 def test_same_names_remain_distinguishable_by_teacher_code(self):
  a=self.cmd('teacher.upsert',{'code':'A01','name':'Cô Trùng Tên'})['id'];b=self.cmd('teacher.upsert',{'code':'A02','name':'Cô Trùng Tên'})['id'];self.cmd('meeting.upsert',{'title':'Họp','date':'2026-10-22','time':'20:00','invited':[a,b]});names=self.db.read()['events'][0]['participantNames'];self.assertEqual(len(names),2);self.assertIn('Cô Trùng Tên (A01)',names);self.assertIn('Cô Trùng Tên (A02)',names)
