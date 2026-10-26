import unittest,tempfile,sqlite3,io,zipfile,json,threading,urllib.request,urllib.error,csv,base64
from pathlib import Path
from datetime import datetime
from thu.common import *
from thu.store import Store
from thu.service import Service,overdue
from thu.importer import read_workbook,build_plan,apply_plan,excel_day
from thu.metrics import aggregate,evaluate
from thu.calendar_service import calendar_ics
from thu.exporting import report_csv
from thu.server import LocalServer
class Domain(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.svc=Service(self.tmp.name);self.db=self.svc.stores['real'];self.clock=Clock('real',datetime(2026,10,20,13,tzinfo=VN))
 def tearDown(self):self.tmp.cleanup()
 def cmd(self,n,p=None):return self.svc.command('real',self.db.read()['_revision'],uid(),n,p or {})['result']
 def teacher(self,code='00123',name='Cô Thử'):return self.cmd('teacher.upsert',{'code':code,'name':name})['id']
 def plan(self,content,kind,mapping,options=None):return build_plan(read_workbook(content.encode(),'fixture.csv'),'CSV',1,kind,mapping,options or {'sourceName':'fixture','year':2026},self.db.read(),self.clock)
 def commit(self,p,partial=False):return self.db.mutate(p['revision'],uid(),'import',{'fp':p['fingerprint']},lambda s:apply_plan(self.svc,s,p,self.clock,partial),self.clock.stamp())
 def test_modes_and_persistence(self):
  self.assertEqual(len(self.svc.stores['demo'].read()['teachers']),20);self.assertEqual(self.db.read()['teachers'],[]);self.teacher();self.assertEqual(Service(self.tmp.name).stores['real'].read()['teachers'][0]['code'],'00123')
 def test_identity_alias_conflict(self):
  a=self.teacher();b=self.teacher('123');self.assertNotEqual(a,b);self.cmd('teacher.alias',{'teacher':a,'source':'A','code':'C01'})
  with self.assertRaises(AppError):self.cmd('teacher.alias',{'teacher':b,'source':'A','code':'C01'})
 def test_idempotency_and_stale(self):
  req=uid();p={'code':'a','name':'A'};self.svc.command('real',0,req,'teacher.upsert',p);self.assertTrue(self.svc.command('real',0,req,'teacher.upsert',p)['result']['replayed']);self.assertEqual(len(self.db.read()['teachers']),1)
  with self.assertRaises(AppError):self.svc.command('real',0,req,'teacher.upsert',{'code':'b','name':'B'})
  with self.assertRaises(AppError) as e:self.svc.command('real',0,uid(),'teacher.upsert',p)
  self.assertEqual(e.exception.code,'STALE')
 def test_transaction_fk_rollback(self):
  def fail(s):s['teachers'].append({'id':'temp','code':'T','name':'T'});s['tasks'].append({'id':'bad','teacher':'missing'})
  with self.assertRaises(AppError):self.db.mutate(0,uid(),'test',{},fail,self.clock.stamp())
  self.assertEqual(self.db.read()['teachers'],[]);self.assertEqual(self.db.read()['_revision'],0)
 def test_backup_restore(self):
  self.teacher();raw=self.db.backup();self.teacher('other');rev=self.db.read()['_revision'];s,r=self.db.restore(raw,rev,uid(),self.clock.stamp());self.assertEqual(len(s['teachers']),1);self.assertGreater(s['_revision'],rev);self.assertTrue(Path(r['beforeBackup']).exists())
  for bad in (raw[:-8],b'bad',self.svc.stores['demo'].backup()):
   with self.assertRaises(AppError):self.db.inspect_backup(bad)
 def test_migration_repeat_and_failure(self):
  self.teacher();c=self.db.connect();c.execute('DROP TABLE requests');c.execute('PRAGMA user_version=1');c.close();Store(self.tmp.name,'real');Store(self.tmp.name,'real');self.assertEqual(len(self.db.read()['teachers']),1);self.assertTrue((Path(self.tmp.name)/'real-before-v2.sqlite3').exists())
  c=self.db.connect();c.execute('PRAGMA user_version=1');c.close()
  with self.assertRaises(sqlite3.OperationalError):Store(self.tmp.name,'real')
  c=self.db.connect();self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],1);c.close()
 def test_busy_db_does_not_write(self):
  c=self.db.connect();c.execute('BEGIN IMMEDIATE')
  try:
   with self.assertRaises(sqlite3.OperationalError):self.teacher()
  finally:c.rollback();c.close()
  self.assertEqual(self.db.read()['teachers'],[])
 def test_teacher_import_repeat_conflict(self):
  p=self.plan('Code,Name\n00123,Cô Một\nC123,Cô Hai\n','teachers',{'code':0,'name':1});self.commit(p);p['revision']=self.db.read()['_revision'];self.commit(p);self.assertEqual(len(self.db.read()['teachers']),2);self.assertEqual(len(self.db.read()['importBatches']),1)
  p=self.plan('Code,Name\n00123,Khác tên\n','teachers',{'code':0,'name':1});self.assertEqual(p['counts']['review'],1)
 def test_name_mapping_must_be_explicit(self):
  a=self.teacher();self.teacher('other');raw='Name,Date,Detail\nCô Thử,20/10/2026,Lỗi thử\n';mapping={'teacherName':0,'date':1,'detail':2};self.assertEqual(self.plan(raw,'qc',mapping)['counts']['review'],1)
  p=self.plan(raw,'qc',mapping,{'teacherMap':{'name:Cô Thử':a}});self.commit(p);self.assertEqual(self.db.read()['errors'][0]['teacher'],a)
 def test_alias_remembered_and_partial_atomic(self):
  a=self.teacher();mapping={'teacherCode':0,'date':1,'detail':2};raw='Code,Date,Detail\nC01,20/10/2026,Lỗi thử\nC01,20/10/2026,\n';p=self.plan(raw,'qc',mapping,{'sourceName':'fixture','teacherMap':{'code:C01':a}})
  with self.assertRaises(AppError):self.commit(p)
  self.assertEqual(self.db.read()['errors'],[]);self.commit(p,True);self.assertEqual(len(self.db.read()['errors']),1);self.assertEqual(len(self.db.read()['aliases']),1)
  p=self.plan('Code,Date,Detail\nC01,21/10/2026,Lỗi khác\n','qc',mapping);self.assertEqual(p['counts']['create'],1)
 def test_metric_blanks_zero_units_and_weighted(self):
  self.teacher();p=self.plan('Code,Pct,N,D\n00123,0.85,0,10\n','metrics',{'teacherCode':0,'attendance_pct':1,'homework_n':2,'homework_d':3},{'period':'2026-10-19','percentUnit':'0-1'});self.commit(p);rows=self.db.read()['metrics'];self.assertEqual(len(rows),2);self.assertEqual(next(r for r in rows if r['kind']=='attendance')['sourcePercent'],85);self.assertEqual(next(r for r in rows if r['kind']=='homework')['numerator'],0)
  rows=[{'teacher':'t','classId':'a','numerator':1,'denominator':2},{'teacher':'t','classId':'b','numerator':8,'denominator':8}];self.assertEqual(aggregate(rows)['pct'],90);self.assertEqual(aggregate(rows+[{'teacher':'t','classId':'','numerator':9,'denominator':10}])['status'],'NEEDS_REVIEW');self.assertEqual(aggregate([])['status'],'NO_DATA')
 def test_threshold_boundaries(self):
  for p in (69.99,70,70.01):
   values={k:{'status':'OK','pct':p} for k in KINDS};rules={'confirmed':True,'weekConfirmed':True,'operator':'>=',**{k:70 for k in ('attendance','homework','skill')}};self.assertEqual(evaluate(values,rules),'PASS' if p>=70 else 'BELOW_THRESHOLD');rules['operator']='>';self.assertEqual(evaluate(values,rules),'PASS' if p>70 else 'BELOW_THRESHOLD')
 def test_dates_workbook_formula_secret_styled_blank(self):
  self.assertEqual(excel_day(1),'1900-01-01');self.assertEqual(excel_day(0,'1904'),'1904-01-01');self.assertEqual(excel_day('17h00 23/09',year=2026),'2026-09-23')
  with self.assertRaises(AppError):excel_day(60)
  with self.assertRaises(AppError):excel_day('23/09')
  b=read_workbook(mini_xlsx(),'fixture.xlsx');self.assertEqual(b['missingCache'],1);self.assertNotIn('sensitive-value',canonical(b));self.assertIsNone(b['sheets'][0]['rows'][1][2]);self.assertEqual(b['sheets'][0]['rows'][1][0],'00123')
 def test_tasks_due_reopen_and_repeat_month_end(self):
  id=self.cmd('task.upsert',{'title':'Việc','date':'2026-10-20'})['id'];t=self.db.read()['tasks'][0];self.assertFalse(overdue(t,self.clock));t['time']='12:59';self.assertTrue(overdue(t,self.clock));t['time']='13:00';self.assertFalse(overdue(t,self.clock));self.cmd('task.status',{'id':id,'status':'done'});self.assertTrue(self.db.read()['tasks'][0]['completedAt']);self.cmd('task.status',{'id':id,'status':'todo'});self.assertFalse(self.db.read()['tasks'][0]['completedAt'])
  s=empty_state();self.svc.cmd_template_add(s,{'title':'Monthly','frequency':'monthly','start':'2026-01-31'},self.clock);clock=Clock('demo',datetime(2026,2,28,9,tzinfo=VN));p={'start':'2026-02-28','end':'2026-02-28'};self.svc.cmd_tasks_generate(s,p,clock);self.svc.cmd_tasks_generate(s,p,clock);self.assertEqual(len(s['tasks']),1)
 def test_case_atomic_steps_and_episodes(self):
  a=self.teacher();p={'code':'L1','teacher':a,'plan':'Hỗ trợ'};id=self.cmd('process.upsert',p)['id']
  with self.assertRaises(AppError):self.cmd('process.transition',{**p,'id':id,'plan':'Changed','step':4})
  self.assertEqual(self.db.read()['processes'][0]['plan'],'Hỗ trợ')
  for n in (1,2,3):self.cmd('process.transition',{**p,'id':id,'step':n})
  with self.assertRaises(AppError):self.cmd('process.transition',{**p,'id':id,'step':4})
  self.cmd('process.transition',{**p,'id':id,'step':4,'reason':'Đã kiểm tra'});self.cmd('process.upsert',p);self.assertEqual([r['episode'] for r in self.db.read()['processes']],[1,2])
  with self.assertRaises(AppError):self.cmd('process.upsert',{'code':'BAD','teacher':a,'students':2,'passed':3})
  self.assertEqual(len(self.db.read()['classes']),1)
 def test_report_snapshot_and_csv_safety(self):
  a=self.teacher(name='=SUM(1,2)');p=monday(Clock('real').today());self.cmd('settings.update',{'attendance':70,'homework':70,'skill':70,'operator':'>=','confirmed':True,'weekConfirmed':True,'effectiveDate':p,'reason':'Test-only'})
  for kind in ('attendance','homework','skill'):self.cmd('metric.upsert',{'teacher':a,'period':p,'kind':kind,'numerator':7,'denominator':10})
  self.cmd('report.seal',{'period':p});before=canonical(self.db.read()['reports'][0]);m=self.db.read()['metrics'][0];self.cmd('metric.upsert',{**m,'numerator':0});self.assertEqual(canonical(self.db.read()['reports'][0]),before);rows=list(csv.reader(io.StringIO(report_csv(self.db.read()['reports'][0]).decode('utf-8-sig'))));self.assertEqual(rows[2][0],"'00123");self.assertTrue(rows[2][1].startswith("'="));self.assertEqual(float(rows[2][3]),70)
 def test_meeting_snapshot_events_task_dedup(self):
  a=self.teacher();b=self.teacher('b');mid=self.cmd('meeting.upsert',{'title':'Họp','date':'2026-10-22','time':'20:00'})['id'];self.teacher('c');self.assertEqual(len(self.db.read()['meetings'][0]['invited']),2)
  p={'id':mid,'attendees':{a:'present',b:'present'},'contributions':{a:'Góp ý\nxuống dòng'},'reports':{a:'https://example.com/report'},'note':'Ghi chú'};self.cmd('meeting.attendance',p);self.cmd('meeting.attendance',p);self.assertEqual(sum(v=='present' for v in self.db.read()['meetings'][0]['attendees'].values()),2)
  with self.assertRaises(AppError):self.cmd('meeting.attendance',{**p,'reports':{a:'javascript:alert(1)'}})
  self.cmd('meeting.upsert',{'id':mid,'title':'Đổi lịch','date':'2026-10-23','time':'19:00'});self.assertEqual(len(self.db.read()['events']),1)
  task={'meetingId':mid,'decisionId':'D1','title':'Sau họp','date':'2026-10-24'};self.cmd('meeting.task',task);self.cmd('meeting.task',task);self.assertEqual(len(self.db.read()['tasks']),1)
 def test_ics_time_uid_folding_all_day(self):
  self.cmd('event.upsert',{'title':'Chia sẻ, kỹ năng; '+('Tiếng Việt '*18),'date':'2026-12-31','time':'20:00','duration':90,'recurrence':'weekly','alarm':15,'note':'Dòng 1\nDòng 2'});self.cmd('event.upsert',{'title':'Nghỉ','date':'2026-12-31','endDate':'2027-01-01','allDay':True});raw=calendar_ics(self.db.read()['events']);self.assertIn(b'DTSTART:20261231T130000Z',raw);self.assertIn(b'DTEND:20261231T143000Z',raw);self.assertIn(b'DTEND;VALUE=DATE:20270102',raw);self.assertTrue(all(len(x)<=75 for x in raw.split(b'\r\n')));raw.decode();self.assertEqual(raw,calendar_ics(self.db.read()['events']))
def mini_xlsx():
 b=io.BytesIO();ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
 with zipfile.ZipFile(b,'w') as z:
  z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="GV" r:id="r1"/></sheets></workbook>');z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>');z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Mã GV</t></is></c><c r="B1" t="inlineStr"><is><t>Password</t></is></c><c r="C1" t="inlineStr"><is><t>Metric</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>00123</t></is></c><c r="B2" t="inlineStr"><is><t>sensitive-value</t></is></c><c r="C2"><f>IMPORTRANGE()</f></c><c r="XFD2" s="1"/></row></sheetData></worksheet>')
 return b.getvalue()
class HTTP(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.server=LocalServer(('127.0.0.1',0),self.tmp.name,Path(__file__).resolve().parents[1]/'web');self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.origin=self.server.origin;self.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor());self.csrf=self.request('/api/bootstrap')[1]['csrf']
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
 def request(self,path,body=None,headers=None,client=None,raw=False):
  h={'X-Tool-Mode':'real'}
  if body is not None:h.update({'Content-Type':'application/json','Origin':self.origin,'X-Tool-CSRF':getattr(self,'csrf','')})
  h.update(headers or {});req=urllib.request.Request(self.origin+path,data=canonical(body).encode() if body is not None else None,headers=h)
  try:r=(client or self.client).open(req,timeout=10)
  except urllib.error.HTTPError as e:r=e
  with r:
   b=r.read();return r.status,b if raw else json.loads(b)
 def command(self,n,p):return self.request('/api/commands',{'revision':self.request('/api/state')[1]['state']['_revision'],'requestId':uid(),'name':n,'payload':p})
 def test_security_and_assets(self):
  self.assertEqual(self.request('/api/state',client=urllib.request.build_opener())[0],401);self.assertEqual(self.request('/api/commands',{},headers={'Origin':'https://example.com'})[0],403);self.assertEqual(self.request('/api/commands',{},headers={'X-Tool-CSRF':'bad'})[0],403);self.assertEqual(self.request('/api/health',headers={'Host':'evil.example'})[0],403);self.assertEqual(self.request('/%2e%2e/start.py')[0],404);self.assertEqual(self.request('/core.js',raw=True)[0],200)
 def test_full_api_workflow(self):
  opened=self.request('/api/import/open',{'filename':'teachers.csv','base64':base64.b64encode('Code,Name\n00123,Cô Thử\n'.encode()).decode()})[1];plan=self.request('/api/import/plan',{'uploadId':opened['uploadId'],'sheet':'CSV','header':1,'template':'teachers','mapping':{'code':0,'name':1},'options':{}})[1];req={'previewId':plan['previewId'],'confirmed':True,'requestId':uid()};status,saved=self.request('/api/import/commit',req);self.assertEqual(status,200);self.assertEqual(self.request('/api/import/commit',req)[0],200);tid=saved['state']['teachers'][0]['id']
  self.assertEqual(self.command('teacher.note',{'id':tid,'note':'Offline'})[0],200);self.assertEqual(self.command('task.upsert',{'title':'Coaching','date':'2026-10-22','teacher':tid})[0],200);self.assertEqual(self.command('process.transition',{'code':'L1','teacher':tid,'plan':'Hỗ trợ','step':0})[0],200);self.assertEqual(self.command('meeting.upsert',{'title':'Họp','date':'2026-10-22','time':'20:00'})[0],200);self.assertEqual(self.request('/api/report.csv',raw=True)[0],200);self.assertIn(b'BEGIN:VEVENT',self.request('/api/calendar.ics',raw=True)[1])
  file=self.request('/api/backup',{})[1]['filename'];raw=self.request('/api/download/'+file,raw=True)[1];self.command('teacher.upsert',{'code':'other','name':'Other'});preview=self.request('/api/restore/preview',{'base64':base64.b64encode(raw).decode()})[1];status,result=self.request('/api/restore/commit',{'previewId':preview['previewId'],'requestId':uid(),'confirmed':True});self.assertEqual(status,200);self.assertEqual(len(result['state']['teachers']),1);self.assertEqual(result['state']['teachers'][0]['note'],'Offline')
if __name__=='__main__':unittest.main()
