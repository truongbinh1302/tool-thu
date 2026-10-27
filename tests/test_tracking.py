import unittest,tempfile,threading
from copy import deepcopy
from thu.service import Service
from thu.common import AppError,uid,canonical,Clock
from thu.tracking import tracking_state
from thu.calendar_service import calendar_ics,calendar_events
from test_local import HTTP
class Tracking(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.svc=Service(self.tmp.name);self.db=self.svc.stores['demo'];self.adapter=self.svc.source_adapters['fakeSheets']
 def tearDown(self):self.tmp.cleanup()
 def cmd(self,name,p):return self.svc.command('demo',self.db.read()['_revision'],uid(),name,p)
 def stage(self,scenario='baseline',source='demo-sheet-main'):return self.cmd('tracking.fixture',{'scenario':scenario,'sourceId':source,'approved':True})
 def run_track(self,sources=None,request=None,revision=None):return self.svc.track('demo',self.db.read()['_revision'] if revision is None else revision,request or uid(),sources or ['demo-sheet-main'])
 def metric(self,kind='attendance'):return next(m for m in self.db.read()['metrics'] if m['teacher']=='GV001' and m['period']=='2026-10-19' and m['kind']==kind)
 def test_no_read_without_button_and_config_does_not_track(self):
  self.assertEqual(self.adapter.read_count,0)
  for _ in range(3):self.svc.snapshot('demo');self.svc.snapshot('real')
  self.stage('changed');self.svc.snapshot('demo');self.assertEqual(self.adapter.read_count,0);self.assertEqual(self.metric()['numerator'],82)
 def test_manual_change_and_idempotent_replay(self):
  self.stage('changed');id=uid();before=self.db.read()['_revision'];r=self.run_track(request=id);self.assertEqual(self.metric()['numerator'],97);self.assertEqual(r['result']['appliedRecords'],3);self.assertEqual(self.adapter.read_count,1)
  self.run_track(request=id,revision=before);self.assertEqual(self.adapter.read_count,1);self.assertEqual(len(self.db.read()['tracking']['runs']),1)
  self.run_track();self.assertEqual(self.adapter.read_count,2);self.assertEqual(len(self.db.read()['metrics']),120);self.assertEqual(self.db.read()['tracking']['runs'][-1]['appliedRecords'],0)
 def test_real_mode_cannot_read_fake_or_connect(self):
  with self.assertRaises(AppError):self.svc.command('real',0,uid(),'tracking.fixture',{'approved':True})
  with self.assertRaises(AppError) as e:self.svc.track('real',0,uid(),['demo-sheet-main'])
  self.assertIn('chưa được lưu',str(e.exception));self.assertEqual(self.adapter.read_count,0);self.assertEqual(self.svc.stores['real'].read()['teachers'],[])
 def test_failure_keeps_metrics_and_last_success_until_manual_retry(self):
  self.stage('changed');self.run_track();old=canonical(self.db.read()['metrics']);success=self.db.read()['tracking']['lastSuccess'];self.stage('offline');r=self.run_track();self.assertEqual(r['result']['status'],'ERROR');self.assertEqual(canonical(self.db.read()['metrics']),old);self.assertEqual(self.db.read()['tracking']['lastSuccess'],success)
  count=self.adapter.read_count;self.svc.snapshot('demo');self.assertEqual(self.adapter.read_count,count);self.stage('changed');self.assertEqual(self.adapter.read_count,count);self.run_track();self.assertEqual(self.adapter.read_count,count+1)
 def test_schema_change_preserves_saved_data(self):
  self.stage('changed');before=canonical(self.db.read()['metrics']);self.adapter.read=lambda source:(b'Code,Unexpected columns\nGV001,97\n','changed.csv');r=self.run_track();self.assertEqual(r['result']['status'],'ERROR');self.assertEqual(r['result']['sources'][0]['code'],'SOURCE_SCHEMA');self.assertEqual(canonical(self.db.read()['metrics']),before)
 def test_only_selected_sources_are_read(self):
  self.stage('changed');self.stage('denied','demo-sheet-extra');r=self.run_track();self.assertEqual(r['result']['status'],'SUCCESS');self.assertEqual(self.adapter.read_count,1)
 def test_cross_source_conflicts_queue_before_either_applied(self):
  self.stage('changed');self.stage('conflict','demo-sheet-extra');before=canonical(self.db.read()['metrics']);r=self.run_track(['demo-sheet-main','demo-sheet-extra']);self.assertEqual(r['result']['status'],'REVIEW');self.assertEqual(r['result']['appliedRecords'],0);self.assertEqual(canonical(self.db.read()['metrics']),before);pending=[q for q in self.db.read()['tracking']['reviewQueue'] if q['status']=='pending'];self.assertEqual(len(pending),2)
  self.run_track(['demo-sheet-main','demo-sheet-extra']);self.assertEqual(len([q for q in self.db.read()['tracking']['reviewQueue'] if q['status']=='pending']),2)
 def test_manual_local_edit_not_silently_overwritten_and_review_can_apply(self):
  self.stage();self.run_track();m=self.metric();self.cmd('metric.upsert',{**m,'numerator':40});self.stage('changed');r=self.run_track();self.assertEqual(r['result']['status'],'REVIEW');self.assertEqual(self.metric()['numerator'],40);q=next(q for q in self.db.read()['tracking']['reviewQueue'] if q['status']=='pending');self.cmd('tracking.review',{'id':q['id'],'decision':'source','reason':'Đã đối chiếu nguồn thử'});self.assertEqual(self.metric()['numerator'],97)
 def test_keep_local_decision_survives_unchanged_manual_reads(self):
  self.stage();self.run_track();self.cmd('metric.upsert',{**self.metric(),'numerator':40});self.stage('changed');self.run_track();q=next(q for q in self.db.read()['tracking']['reviewQueue'] if q['status']=='pending');self.cmd('tracking.review',{'id':q['id'],'decision':'local','reason':'Giữ điều chỉnh nội bộ'});self.run_track();self.assertEqual(self.metric()['numerator'],40);self.assertFalse(any(q['status']=='pending' for q in self.db.read()['tracking']['reviewQueue']))
 def test_stale_review_blocks_overwriting_newer_value(self):
  self.stage('changed');self.stage('conflict','demo-sheet-extra');self.run_track(['demo-sheet-main','demo-sheet-extra']);q=self.db.read()['tracking']['reviewQueue'][0];self.cmd('metric.upsert',{**self.metric(),'numerator':33})
  with self.assertRaises(AppError) as e:self.cmd('tracking.review',{'id':q['id'],'decision':'source','reason':'Test'})
  self.assertEqual(e.exception.code,'REVIEW_STALE');self.assertEqual(self.metric()['numerator'],33)
 def test_empty_cells_do_not_become_zero(self):
  self.stage('missing');r=self.run_track();self.assertEqual(self.metric()['numerator'],82);self.assertEqual(r['result']['appliedRecords'],0);self.assertEqual(r['result']['sources'][0]['counts']['skipped'],1)
 def test_partial_read_failure_and_atomic_rollback(self):
  self.stage('changed');self.stage('denied','demo-sheet-extra');r=self.run_track(['demo-sheet-main','demo-sheet-extra']);self.assertEqual(r['result']['status'],'PARTIAL');self.assertEqual(self.metric()['numerator'],97)
  self.stage('baseline');before=canonical(self.db.read()['metrics']);runs=len(self.db.read()['tracking']['runs']);original=self.svc.cmd_metric_upsert;calls=[]
  def fail(s,p,c):
   calls.append(1)
   if len(calls)==2:raise AppError('Synthetic failure')
   return original(s,p,c)
  self.svc.cmd_metric_upsert=fail
  with self.assertRaises(AppError):self.run_track()
  self.assertEqual(canonical(self.db.read()['metrics']),before);self.assertEqual(len(self.db.read()['tracking']['runs']),runs)
 def test_inflight_block_and_compare_and_swap(self):
  self.stage('changed');entered=threading.Event();release=threading.Event();original=self.adapter.read;errors=[]
  def blocking(source):entered.set();release.wait(3);return original(source)
  self.adapter.read=blocking
  def worker():
   try:self.run_track()
   except Exception as e:errors.append(e)
  thread=threading.Thread(target=worker);thread.start();self.assertTrue(entered.wait(2))
  try:
   with self.assertRaises(AppError) as e:self.run_track()
   self.assertEqual(e.exception.code,'TRACK_BUSY');self.cmd('teacher.note',{'id':'GV001','note':'Edited while reading'})
  finally:release.set();thread.join(5)
  self.assertFalse(thread.is_alive());self.assertEqual(errors[0].code,'STALE');self.assertEqual(self.metric()['numerator'],82);self.assertEqual(self.adapter.read_count,1)
 def test_retry_after_restart_no_extra_read(self):
  self.stage('changed');id=uid();rev=self.db.read()['_revision'];self.run_track(request=id);new=Service(self.tmp.name);r=new.track('demo',rev,id,['demo-sheet-main']);self.assertTrue(r['result']['replayed']);self.assertEqual(new.source_adapters['fakeSheets'].read_count,0)

class TrackingHTTP(HTTP):
 def test_bootstrap_gets_do_not_track_and_post_is_protected(self):
  self.assertEqual(self.server.service.source_adapters['fakeSheets'].read_count,0)
  status,b=self.request('/api/bootstrap',headers={'X-Tool-Mode':'demo'});rev=b['state']['_revision']
  status,r=self.request('/api/commands',{'revision':rev,'requestId':uid(),'name':'tracking.fixture','payload':{'approved':True,'scenario':'changed'}},headers={'X-Tool-Mode':'demo'});self.assertEqual(status,200)
  self.request('/api/state',headers={'X-Tool-Mode':'demo'});self.request('/api/calendar.ics',headers={'X-Tool-Mode':'demo'},raw=True);self.assertEqual(self.server.service.source_adapters['fakeSheets'].read_count,0)
  body={'revision':r['state']['_revision'],'requestId':uid(),'sourceIds':['demo-sheet-main']};self.assertEqual(self.request('/api/tracking/run',body,headers={'X-Tool-Mode':'demo','X-Tool-CSRF':'bad'})[0],403);self.assertEqual(self.server.service.source_adapters['fakeSheets'].read_count,0)
  status,r=self.request('/api/tracking/run',body,headers={'X-Tool-Mode':'demo'});self.assertEqual(status,200);self.assertEqual(r['result']['status'],'SUCCESS');self.assertEqual(self.server.service.source_adapters['fakeSheets'].read_count,1)

def load_tests(loader,suite,pattern):
 return unittest.TestSuite([loader.loadTestsFromTestCase(Tracking),TrackingHTTP('test_bootstrap_gets_do_not_track_and_post_is_protected')])
