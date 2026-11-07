"""Quarterly manual evaluation, upgrades and saved-state employee summaries."""
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from thu.common import AppError, Clock, VN, canonical, uid
from thu.metrics import evaluations, score_report
from thu.service import Service
from thu.store import Store


class Scores(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.svc=Service(self.tmp.name);self.db=self.svc.stores['real']
        self.clock=Clock('real',datetime(2026,11,7,10,tzinfo=VN))
        self.tid=self.cmd('teacher.upsert',{'code':'TEST01','name':'An Thử'})['id']

    def tearDown(self):self.tmp.cleanup()

    def cmd(self,name,p):
        return self.svc.command('real',self.db.read()['_revision'],uid(),name,p)['result']

    def add(self,delta=1,**kw):
        return self.cmd('score.add',{'teacher':self.tid,'delta':delta,'date':'2026-11-07','reason':'Tình huống giả lập',**kw})['id']

    def report(self,q='2026-Q4'):
        return score_report(self.svc.snapshot('real'),q)['teachers'][self.tid]

    def test_baseline_quarter_boundary_and_clock(self):
        self.assertEqual(self.report()['score'],50)
        self.add();self.add(-1);self.add(date='2026-09-30')
        self.assertEqual(self.report()['score'],50)
        self.assertEqual(self.report('2026-Q3')['score'],51)
        self.assertEqual(self.report('2027-Q1')['score'],50)
        with patch('thu.service.Clock',return_value=self.clock):
            self.cmd('score.add',{'teacher':self.tid,'delta':1,'reason':'Ngày mặc định'})
        self.assertEqual(self.db.read()['scoreEntries'][-1]['date'],'2026-11-07')
        self.assertEqual(self.db.read()['scoreEntries'][-1]['createdBy'],'Thư')

    def test_edit_delete_and_audit(self):
        eid=self.add();original=self.db.read()['scoreEntries'][0]['created']
        self.add(-1,id=eid,reason='Sửa ghi nhận')
        self.assertEqual(self.report()['score'],49)
        self.assertEqual(self.db.read()['scoreEntries'][0]['created'],original)
        self.cmd('score.delete',{'id':eid});self.assertEqual(self.report()['score'],50)
        self.assertEqual([a['action'] for a in self.db.audit()][:2],['score.delete','score.add'])
        with self.assertRaises(AppError):self.cmd('score.delete',{'id':eid})

    def test_unbounded_score(self):
        s=self.db.read()
        s['scoreEntries']=[{'id':str(i),'teacher':self.tid,'date':'2026-11-07','created':'','reason':'Test','delta':-1} for i in range(52)]
        self.assertEqual(score_report(s,'2026-Q4')['teachers'][self.tid]['score'],-2)
        for e in s['scoreEntries']:e['delta']=1
        self.assertEqual(score_report(s,'2026-Q4')['teachers'][self.tid]['score'],102)

    def test_validation_atomic(self):
        for delta in (0,2,-2,1.0,True,'1',None):
            with self.subTest(delta=delta),self.assertRaises(AppError):self.add(delta)
        for p in ({'reason':''},{'reason':' '*4},{'reason':'a'*1001},{'teacher':'missing'},{'date':'2026-02-30'},{'id':'missing'}):
            with self.subTest(p=p),self.assertRaises(AppError):self.add(**p)
        self.assertEqual(self.db.read()['scoreEntries'],[])

    def test_ranking_vietnamese_ties_inactive(self):
        for i,name in enumerate(('Ân Thử','Ăn Thử','Đan Thử','Dân Thử')):
            self.cmd('teacher.upsert',{'code':'T'+str(i),'name':name})
        off=self.cmd('teacher.upsert',{'code':'OFF','name':'Ẩn Thử','status':'inactive'})['id']
        self.add(teacher=off);self.add()
        ranking=score_report(self.db.read(),'2026-Q4')['ranking']
        self.assertEqual([r['name'] for r in ranking],['An Thử','Ăn Thử','Ân Thử','Dân Thử','Đan Thử'])
        self.assertEqual([r['rank'] for r in ranking],[1,2,2,2,2])
        second=ranking[1]['id'];self.add(teacher=second)
        self.assertEqual([r['rank'] for r in score_report(self.db.read(),'2026-Q4')['ranking']],[1,1,3,3,3])

    def test_profile_tasks_deadlines_sources_and_no_network(self):
        self.cmd('task.upsert',{'title':'Việc thử','date':'2026-11-06','teacher':self.tid})
        self.cmd('process.upsert',{'code':'LOPTEST','teacher':self.tid,'due':'2026-11-08'})
        self.cmd('meeting.upsert',{'title':'Họp thử','date':'2026-11-10','time':'09:00'})
        self.cmd('event.upsert',{'title':'Lịch thử','date':'2026-11-14','allDay':True,'participantNames':['An Thử']})
        self.cmd('error.upsert',{'teacher':self.tid,'date':'2026-11-07','detail':'QC thử'})
        s=self.db.read();s['group']={'data':{'deadlines':{'rows':[{'row':2,'teacher':'An Thử','class':'LOP14','deadline':'2026-11-09'}]},'homework':{'columns':[],'rows':[{'teacher':'An Thử','cells':[90]}]},'errors':{'rows':[{'teacher':'An Thử','date':'2026-11-07','content':'Lỗi thử'}]}}}
        s=self.svc.decorate(s,'real');r=evaluations(s,self.clock)
        profile=r['employees'][self.tid]
        self.assertEqual(len(profile['tasks']),1)
        self.assertEqual(len(s['tasks']),1)
        self.assertEqual([d['source'] for d in profile['deadlines']],['Task','Hồ sơ','14 ngày','Họp','Lịch'])
        self.assertEqual([d['urgency'] for d in profile['deadlines']],['overdue','soon','soon','soon','soon'])
        self.assertEqual(len(profile['tables']['homework']['rows']),1)
        q=r['quarters']['2026-Q4']['teachers'][self.tid]
        self.assertEqual((q['score'],q['errorCount'],q['handling'],len(q['qc'])),(50,1,'Nhắc nhở',1))
        with patch.object(self.svc.google,'read_book',side_effect=AssertionError('must not fetch')):
            self.svc.snapshot('real')

    def test_score_fk_archive_demo_reset_and_replay(self):
        req=uid();rev=self.db.read()['_revision'];p={'teacher':self.tid,'delta':1,'reason':'Thử'}
        self.svc.command('real',rev,req,'score.add',p);self.svc.command('real',rev,req,'score.add',p)
        self.assertEqual(len(self.db.read()['scoreEntries']),1)
        t=self.db.read()['teachers'][0];self.cmd('teacher.upsert',{**t,'status':'archived'})
        self.assertEqual(self.report()['score'],51)
        self.assertEqual(score_report(self.db.read(),'2026-Q4')['ranking'],[])
        with self.assertRaises(AppError):
            self.db.mutate(self.db.read()['_revision'],uid(),'bad',{},lambda s:s['teachers'].clear(),self.clock.stamp())
        demo=self.svc.stores['demo'];tid=demo.read()['teachers'][0]['id']
        self.svc.command('demo',demo.read()['_revision'],uid(),'score.add',{'teacher':tid,'delta':1,'reason':'Thử'})
        self.svc.command('demo',demo.read()['_revision'],uid(),'demo.reset',{})
        self.assertEqual(demo.read()['scoreEntries'],[])

    def schema2(self):
        c=self.db.connect();c.execute('DROP TABLE scoreEntries');c.execute('PRAGMA user_version=2');c.close()

    def test_schema2_upgrade_preserves_all_existing_data(self):
        self.cmd('task.upsert',{'title':'Giữ việc','teacher':self.tid,'date':'2026-11-07'})
        before=self.db.read();self.schema2();up=Store(self.tmp.name,'real')
        self.assertEqual(up.read(),before)
        c=up.connect();self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],3);c.close()
        self.add();self.assertEqual(len(up.read()['scoreEntries']),1)

    def test_backup_score_round_trip(self):
        self.add();raw=self.db.backup();self.add(-1)
        restored,res=self.db.restore(raw,self.db.read()['_revision'],uid(),self.clock.stamp())
        self.assertEqual(len(restored['scoreEntries']),1)
        self.assertTrue(Path(res['beforeBackup']).exists())
        self.assertEqual(self.report()['score'],51)

    def test_restore_schema2_and_reject_manifest_mismatch(self):
        before=self.db.read();self.schema2();c=self.db.connect();raw=c.serialize();c.close()
        manifest={'app':'tool-thu','schema':2,'mode':'real','sha256':hashlib.sha256(raw).hexdigest()}
        def archive(m):
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w') as z:z.writestr('manifest.json',canonical(m));z.writestr('data.sqlite3',raw)
            return buf.getvalue()
        Store(self.tmp.name,'real');self.add()
        restored,_=self.db.restore(archive(manifest),self.db.read()['_revision'],uid(),self.clock.stamp())
        self.assertEqual(restored['teachers'],before['teachers']);self.assertEqual(restored['scoreEntries'],[])
        with self.assertRaises(AppError):self.db.inspect_backup(archive({**manifest,'schema':3}))
        self.add();self.assertEqual(self.report()['score'],51)
