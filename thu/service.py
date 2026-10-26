from copy import deepcopy
from datetime import date,datetime,timedelta
import calendar
from .common import *
from .store import Store
from .metrics import report
from .calendar_service import CalendarMixin,calendar_events
from .tracking import TrackingMixin,tracking_state
from .adapters import FakeSheetsSourceAdapter
import threading

def find(s,key,id):
    r=next((r for r in s[key] if r['id']==id),None)
    if r is None:raise AppError('Bản ghi không còn tồn tại.',404)
    return r

def ref(s,key,id,required=False):
    if not id and not required:return ''
    return find(s,key,text(id,True,100))['id']

def record(s,key,p):
    id=text(p.get('id') or p.get('_newId'),maximum=100) or uid();old=next((r for r in s[key] if r['id']==id),None)
    if p.get('id') and old is None:raise AppError('Bản ghi cần sửa không tồn tại.',404)
    r=deepcopy(old) if old else {'id':id}
    return r,old

def put(s,key,r,old):
    if old is None:s[key].append(r)
    else:old.clear();old.update(r)
    return {'id':r['id']}

def overdue(t,clock):
    if t.get('archived') or t['status']=='done':return False
    return datetime.fromisoformat(t['date']+'T'+t['time']+':00+07:00')<clock.now() if t.get('time') else t['date']<clock.today()

class Service(TrackingMixin,CalendarMixin):
    def __init__(self,directory,source_adapters=None):
        self.stores={m:Store(directory,m) for m in ('demo','real')}
        self.source_adapters=source_adapters if source_adapters is not None else {'fakeSheets':FakeSheetsSourceAdapter()}
        self.tracking_locks={m:threading.Lock() for m in ('demo','real')}
    def snapshot(self,mode,period=None):return self.decorate(self.stores[mode].read(),mode,period)
    def decorate(self,s,mode,period=None):
        s=deepcopy(s);tracking_state(s);s['events']=calendar_events(s);clock=Clock(mode);p=monday(period or clock.today());s.update(_mode=mode,_today=clock.today(),_now=clock.stamp(),_report=report(s,p))
        prev=(date.fromisoformat(p)-timedelta(days=7)).isoformat();s['_reportPrevious']=report(s,prev)
        s['_trend']=[report(s,(date.fromisoformat(monday(clock.today()))-timedelta(days=7*i)).isoformat()) for i in reversed(range(6))]
        byid={r['id']:r for r in s['_report']['teachers']}
        for t in s['teachers']:
            r=byid.get(t['id']);t['metricStatus']=r['status'] if r else 'NO_DATA';t['metricDetail']=r['values'] if r else {};t['qc']=r['qc'] if r else 0
            for k in ('attendance','homework','skill'):t[k]=r['values'][k]['displayPct'] if r else None
            t['classes']=sum(c['teacher']==t['id'] and c['status']=='active' for c in s['classes'])
        for t in s['tasks']:t['overdue']=overdue(t,clock)
        return s
    def command(self,mode,expected,request_id,name,p):
        if not isinstance(p,dict):raise AppError('Nội dung thao tác không hợp lệ.')
        fn=getattr(self,'cmd_'+name.replace('.','_'),None)
        if not fn or name.startswith('_'):raise AppError('Thao tác chưa được hỗ trợ.',404)
        clock=Clock(mode)
        s,r=self.stores[mode].mutate(expected,request_id,name,p,lambda s:fn(s,p,clock),clock.stamp());return {'state':self.decorate(s,mode),'result':r}
    def cmd_teacher_upsert(self,s,p,clock):
        r,old=record(s,'teachers',p);code=text(p.get('code'),True,80)
        if any(x['id']!=r['id'] and fold(x['code'])==fold(code) for x in s['teachers']):raise AppError('Mã giáo viên đã tồn tại.',409)
        status=p.get('status','active')
        if status not in ('active','inactive','archived'):raise AppError('Trạng thái giáo viên không hợp lệ.')
        history=r.get('statusHistory') or [{'date':r.get('created',clock.today())[:10],'status':r.get('status',status)}]
        if old and old.get('status')!=status:history.append({'date':clock.today(),'status':status})
        r['statusHistory']=history
        r.update(code=code,name=text(p.get('name'),True,160),level=text(p.get('level'),maximum=120),type=text(p.get('type'),maximum=80),phone=text(p.get('phone'),maximum=40),email=text(p.get('email'),maximum=160),status=status,note=text(p.get('note',r.get('note','')),maximum=10000),created=r.get('created',clock.today()),updated=clock.stamp(),color=r.get('color',['pink','green','blue','orange'][len(s['teachers'])%4]))
        return put(s,'teachers',r,old)
    def cmd_teacher_note(self,s,p,clock):
        t=find(s,'teachers',p['id']);t['note']=text(p.get('note'),maximum=10000);t['updated']=clock.stamp();return {'id':t['id']}
    def cmd_teacher_alias(self,s,p,clock):
        teacher=ref(s,'teachers',p.get('teacher'),True);source=text(p.get('source'),True,180);code=text(p.get('code'),True,80);key=fold(source)+'|'+fold(code)
        old=next((a for a in s['aliases'] if a['alias_key']==key),None)
        if old:
            if old['teacher']!=teacher:raise AppError('Mã nguồn đã được gán cho giáo viên khác.',409)
            return {'id':old['id']}
        a={'id':uid(),'source':source,'code':code,'alias_key':key,'teacher':teacher,'confirmed':clock.stamp()};s['aliases'].append(a);return {'id':a['id']}
    def cmd_class_upsert(self,s,p,clock):
        r,old=record(s,'classes',p);code=text(p.get('code'),True,100);teacher=ref(s,'teachers',p.get('teacher'),True)
        if any(c['id']!=r['id'] and fold(c['code'])==fold(code) for c in s['classes']):raise AppError('Mã lớp đã tồn tại.',409)
        status=p.get('status','active')
        if status not in ('active','closed'):raise AppError('Trạng thái lớp không hợp lệ.')
        hist=r.get('assignments',[])
        if r.get('teacher')!=teacher:hist.append({'teacher':teacher,'effectiveDate':day(p.get('effectiveDate') or clock.today()),'stamp':clock.stamp()})
        r.update(code=code,teacher=teacher,status=status,assignments=hist,note=text(p.get('note')),created=r.get('created',clock.today()))
        return put(s,'classes',r,old)
    def cmd_task_upsert(self,s,p,clock):
        r,old=record(s,'tasks',p);status=p.get('status','todo')
        if status not in ('todo','doing','done'):raise AppError('Trạng thái công việc không hợp lệ.')
        tid=ref(s,'teachers',p.get('teacher'));cid=ref(s,'classes',p.get('classId'))
        if tid and cid and find(s,'classes',cid)['teacher']!=tid:raise AppError('Lớp thuộc giáo viên khác. Hãy kiểm tra liên kết.')
        r.update(title=text(p.get('title'),True,240),category=text(p.get('category') or 'Khác',maximum=100),date=day(p.get('date')),time=time_of(p.get('time')),teacher=tid,classId=cid,meetingId=ref(s,'meetings',p.get('meetingId')),owner=text(p.get('owner'),maximum=160),note=text(p.get('note'),maximum=10000),productURL=url(p.get('productURL')),status=status,archived=bool(p.get('archived',False)),created=r.get('created',clock.stamp()),updated=clock.stamp())
        r['completedAt']=r.get('completedAt') or clock.stamp() if status=='done' else ''
        result=put(s,'tasks',r,old);self.sync_source_event(s,'task',r,clock);return result
    def cmd_task_status(self,s,p,clock):
        return self.cmd_task_upsert(s,{**find(s,'tasks',p['id']),**p},clock)
    def cmd_template_add(self,s,p,clock):
        freq=p.get('frequency')
        if freq not in ('daily','weekly','monthly'):raise AppError('Chu kỳ không hợp lệ.')
        r={'id':uid(),'title':text(p.get('title'),True,240),'frequency':freq,'start':day(p.get('start')),'time':time_of(p.get('time')),'teacher':ref(s,'teachers',p.get('teacher')),'enabled':True};s['templates'].append(r);return {'id':r['id']}
    def cmd_tasks_generate(self,s,p,clock):
        end=date.fromisoformat(day(p.get('end') or clock.today()));start=date.fromisoformat(day(p.get('start') or clock.today()));today=date.fromisoformat(clock.today())
        if start>end or start<today-timedelta(days=30) or end>today+timedelta(days=7):raise AppError('Chỉ sinh công việc từ 30 ngày trước đến 7 ngày sau hôm nay.')
        created=0
        for t in s['templates']:
            anchor=date.fromisoformat(t['start'])
            for offset in range((end-start).days+1):
                d=start+timedelta(days=offset)
                if d<anchor or not t['enabled']:continue
                match=t['frequency']=='daily' or (t['frequency']=='weekly' and d.weekday()==anchor.weekday()) or (t['frequency']=='monthly' and d.day==min(anchor.day,calendar.monthrange(d.year,d.month)[1]))
                id=digest([t['id'],d.isoformat()])[:32]
                if match and not any(r['id']==id for r in s['tasks']):
                    self.cmd_task_upsert(s,{'_newId':id,'title':t['title'],'teacher':t['teacher'],'date':d.isoformat(),'time':t['time'],'category':'Lịch lặp'},clock);s['tasks'][-1]['templateId']=t['id'];created+=1
        return {'created':created}
    def cmd_process_upsert(self,s,p,clock):
        r,old=record(s,'processes',p);code=text(p.get('code'),True,100);teacher=ref(s,'teachers',p.get('teacher'),True)
        cls=next((c for c in s['classes'] if fold(c['code'])==fold(code)),None)
        if not cls:
            cid=self.cmd_class_upsert(s,{'code':code,'teacher':teacher},clock)['id'];cls=find(s,'classes',cid)
        if cls['teacher']!=teacher:raise AppError('Giáo viên phụ trách lớp không khớp. Hãy sửa phân công lớp trước.')
        if any(x['classId']==cls['id'] and x['id']!=r['id'] and x['step']<4 for x in s['processes']):raise AppError('Lớp đang có một hồ sơ xử lý chưa hoàn tất.',409)
        students=number(p.get('students'),optional=True,whole=True);passed=number(p.get('passed'),optional=True,whole=True)
        if passed is not None and (students is None or passed>students):raise AppError('Số đạt phải có sĩ số và không vượt sĩ số.')
        start=day(p.get('start'),True);due=day(p.get('due'),True)
        if start and due and due<start:raise AppError('Hạn xử lý không thể trước ngày tiếp nhận.')
        r.update(code=code,classId=cls['id'],teacher=teacher,start=start,due=due,examDate=day(p.get('examDate'),True),sourceUpdated=day(p.get('sourceUpdated'),True),students=students,passed=passed,plan=text(p.get('plan'),maximum=10000),owner=text(p.get('owner'),maximum=160),step=r.get('step',0),history=r.get('history',[]),milestones=r.get('milestones',[]),episode=r.get('episode',1+sum(x['classId']==cls['id'] for x in s['processes'])),created=r.get('created',clock.stamp()),updated=clock.stamp())
        result=put(s,'processes',r,old);self.sync_source_event(s,'process',r,clock);return result
    def cmd_process_transition(self,s,p,clock):
        result=self.cmd_process_upsert(s,p,clock);r=find(s,'processes',result['id']);step=number(p.get('step'),0,4,whole=True)
        if abs(step-r['step'])>1:raise AppError('Chỉ chuyển sang bước liền kề.')
        if step!=r['step']:
            reason=text(p.get('reason'),required=step==4 or step<r['step'])
            if step==4 and not r['plan']:raise AppError('Cần phương án/kết quả và lý do trước khi hoàn tất.')
            r['history'].append({'from':r['step'],'to':step,'reason':reason,'owner':r['owner'],'stamp':clock.stamp()});r['step']=step
        self.sync_source_event(s,'process',r,clock)
        return result
    def cmd_process_milestone(self,s,p,clock):
        r=find(s,'processes',p['id']);m={'id':uid(),'title':text(p.get('title'),True,240),'date':day(p.get('date')),'time':time_of(p.get('time')),'note':text(p.get('note')),'stamp':clock.stamp()};r['milestones'].append(m)
        eid=self.cmd_event_upsert(s,{**m,'title':r['code']+' · '+m['title'],'allDay':not bool(m['time']),'duration':30,'alarm':0,'_fromSource':True,'id':''},clock)['id'];find(s,'events',eid).update(sourceKey='milestone:'+m['id'],processId=r['id']);return {'id':r['id']}
    def sync_source_event(self,s,kind,r,clock):
        key=kind+':'+r['id'];old=next((e for e in s['events'] if e.get('sourceKey')==key),None)
        due=r['date'] if kind=='task' else r.get('due')
        if not due:
            if old:old.update(cancelled=True,sequence=old.get('sequence',0)+1,updated=clock.stamp())
            return
        cancelled=(r.get('archived') or r['status']=='done') if kind=='task' else r['step']==4
        payload={'title':r['title'] if kind=='task' else 'Hạn xử lý lớp '+r['code'],'date':due,'time':r.get('time') or '', 'allDay':not bool(r.get('time')),'duration':30,'alarm':0,'type':'Hạn công việc' if kind=='task' else 'Hạn hồ sơ lớp','note':r.get('note') or r.get('plan',''),'cancelled':bool(cancelled),'participantNames':[find(s,'teachers',r['teacher'])['name']] if r.get('teacher') else [],'_fromSource':True}
        if old:payload['id']=old['id']
        eid=self.cmd_event_upsert(s,payload,clock)['id'];e=find(s,'events',eid);e.update(sourceKey=key,taskId=r['id'] if kind=='task' else '',processId=r['id'] if kind=='process' else '')
    def cmd_metric_upsert(self,s,p,clock):
        teacher=ref(s,'teachers',p.get('teacher'),True);cid=ref(s,'classes',p.get('classId'))
        if cid and find(s,'classes',cid)['teacher']!=teacher:raise AppError('Lớp không thuộc giáo viên đã chọn.')
        kind=p.get('kind');period=monday(p.get('period'))
        if kind not in KINDS:raise AppError('Loại chỉ số không hợp lệ.')
        n=number(p.get('numerator'),optional=True);d=number(p.get('denominator'),optional=True);pct=number(p.get('sourcePercent'),0,100,optional=True)
        if (n is None)!=(d is None) or (n is not None and n>d):raise AppError('Tử số/mẫu số cần đi cùng nhau và tử số không vượt mẫu số.')
        if n is None and pct is None:raise AppError('Cần số đếm hoặc phần trăm nguồn; ô trống không phải 0.')
        observation=text(p.get('observationId') or 'summary',True,160)
        existing=next((x for x in s['metrics'] if (x['teacher'],x.get('classId',''),x['period'],x['kind'],x.get('observationId','summary'))==(teacher,cid,period,kind,observation)),None)
        if existing and existing['id']!=p.get('id'):raise AppError('Đã có quan sát cho cùng giáo viên/lớp/kỳ/chỉ số. Hãy sửa bản ghi hiện có.',409)
        r,old=record(s,'metrics',p);r.update(teacher=teacher,classId=cid,period=period,kind=kind,numerator=n,denominator=d,sourcePercent=pct,observationId=observation,source=text(p.get('source') or 'Nhập tay',maximum=240),updated=clock.stamp())
        return put(s,'metrics',r,old)
    def cmd_error_upsert(self,s,p,clock):
        r,old=record(s,'errors',p);status=p.get('status','open')
        if status not in ('open','reviewed','closed'):raise AppError('Trạng thái lỗi không hợp lệ.')
        teacher=ref(s,'teachers',p.get('teacher'),True);cid=ref(s,'classes',p.get('classId'))
        if cid and find(s,'classes',cid)['teacher']!=teacher:raise AppError('Lớp không thuộc giáo viên đã chọn.')
        r.update(teacher=teacher,classId=cid,date=day(p.get('date')),category=text(p.get('category'),maximum=160),detail=text(p.get('detail'),True,10000),handling=text(p.get('handling'),maximum=10000),status=status,source=text(p.get('source') or 'Nhập tay',maximum=240),history=r.get('history',[])+[{'stamp':clock.stamp(),'status':status}]);return put(s,'errors',r,old)
    def cmd_settings_update(self,s,p,clock):
        if p.get('operator') not in ('>','>='):raise AppError('Toán tử ngưỡng không hợp lệ.')
        confirmed=bool(p.get('confirmed'));reason=text(p.get('reason'),required=confirmed,maximum=2000)
        r={k:number(p.get(k),0,100) for k in ('attendance','homework','skill')};r.update(operator=p['operator'],confirmed=confirmed,weekConfirmed=bool(p.get('weekConfirmed')),effectiveDate=day(p.get('effectiveDate') or clock.today()),version=uid()[:10],reason=reason,recorded=clock.stamp())
        if s['settings'].get('effectiveDate'):s['ruleDecisions'].append(deepcopy(s['settings']))
        s['settings']=r;return {'version':r['version']}
    def cmd_report_note(self,s,p,clock):s['reportNotes'][monday(p.get('period'))]=text(p.get('note'),maximum=12000)
    def cmd_report_seal(self,s,p,clock):
        r=report(s,p.get('period'));rules=r['rules']
        if not rules.get('confirmed') or not rules.get('weekConfirmed'):raise AppError('Cần xác nhận ngưỡng và quy ước tuần trong Tùy chỉnh trước khi chốt.')
        if not r['teachers']:raise AppError('Chưa có giáo viên trong kỳ.')
        if r['incompleteCount'] and not p.get('acknowledgeIncomplete'):raise AppError('Báo cáo còn thiếu dữ liệu; cần xác nhận rõ trước khi chốt.')
        version=1+sum(x['period']==r['period'] for x in s['reports']);reason=text(p.get('reason'),required=version>1)
        r.update(status='SEALED',id=uid(),version=version,sealedAt=clock.stamp(),reason=reason);s['reports'].append(r);return {'id':r['id']}
    def cmd_source_add(self,s,p,clock):
        r={'id':uid(),'name':text(p.get('name'),True,180),'url':url(p.get('url')),'type':'Link tham chiếu','status':'DEFERRED','created':clock.stamp()};s['sources'].append(r);return {'id':r['id']}
    def cmd_feedback_add(self,s,p,clock):s['feedback'].append({'id':uid(),'text':text(p.get('text'),True,10000),'stamp':clock.stamp()})
    def cmd_demo_reset(self,s,p,clock):
        if clock.mode!='demo':raise AppError('Chỉ có thể đặt lại dữ liệu dùng thử.')
        rev=s['_revision'];s.clear();s.update(demo_state());s['_revision']=rev
