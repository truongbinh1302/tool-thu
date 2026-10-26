"""Manual-only source tracking, sharing import validation and transaction rules."""
from copy import deepcopy
import threading
from .common import AppError,Clock,text,uid,digest,monday

def tracking_state(state):
    return state.setdefault('tracking',{'sources':[],'runs':[],'reviewQueue':[],'lastAttempt':'','lastSuccess':'','lastApplied':''})

def metric_key(m):return (m['teacher'],m.get('classId',''),m['period'],m['kind'],m.get('observationId','summary'))
def value_signature(m):return digest([float(m[k]) if m.get(k) is not None else None for k in ('numerator','denominator','sourcePercent')]) if m else 'missing'
def current_metric(state,payload):return next((m for m in state['metrics'] if metric_key(m)==metric_key(payload)),None)
def key_string(m):return digest(metric_key(m))

class TrackingMixin:
    def cmd_tracking_fixture(self,s,p,clock):
        if clock.mode!='demo':raise AppError('Nguồn thử chỉ dùng trong kho Dùng thử. Google Sheets thật vẫn chưa kết nối.',409,'DEFERRED')
        if p.get('approved') is not True:raise AppError('Cần xác nhận phạm vi và ánh xạ nguồn thử.')
        sid=p.get('sourceId','demo-sheet-main');scenario=p.get('scenario','baseline')
        if sid not in ('demo-sheet-main','demo-sheet-extra') or scenario not in ('baseline','changed','conflict','missing','offline','denied'):raise AppError('Cấu hình nguồn thử không hợp lệ.')
        cfg=tracking_state(s);old=next((x for x in cfg['sources'] if x['id']==sid),None)
        source={'id':sid,'name':'Nguồn thử '+('A' if sid=='demo-sheet-main' else 'B'),'adapter':'fakeSheets','scenario':scenario,'period':monday(clock.today()),'approved':True,'lastSuccess':old.get('lastSuccess','') if old else '','baseline':old.get('baseline',{}) if old else {},'keptLocal':old.get('keptLocal',{}) if old else {}}
        if old:old.update(source)
        else:cfg['sources'].append(source)
        return {'id':sid,'staged':True,'readPerformed':False}

    def track(self,mode,expected,request_id,source_ids):
        if mode!='demo':raise AppError('Google Sheets thật chưa kết nối. Bạn có thể nhập Excel/CSV hoặc thử luồng trong kho Dùng thử.',409,'DEFERRED')
        if not isinstance(source_ids,list) or not 1<=len(source_ids)<=10 or any(not isinstance(x,str) for x in source_ids) or len(set(source_ids))!=len(source_ids):raise AppError('Chọn từ 1 đến 10 nguồn, không lặp.')
        source_ids=sorted(source_ids);payload={'sourceIds':source_ids};store=self.stores[mode];clock=Clock(mode)
        if not self.tracking_locks[mode].acquire(blocking=False):raise AppError('Một lượt cập nhật đang chạy. Hãy chờ lượt đó hoàn tất.',423,'TRACK_BUSY')
        try:
            if store.request_seen(request_id,'tracking.run',payload):
                s=store.read();run=next((r for r in tracking_state(s)['runs'] if r['id']==request_id),{})
                return {'state':self.decorate(s,mode),'result':{**run,'replayed':True}}
            initial=store.read()
            if type(expected)!=int or initial['_revision']!=expected:raise AppError('Dữ liệu đã thay đổi. Kiểm tra bản mới trước khi bấm cập nhật lại.',409,'STALE')
            cfg=tracking_state(initial);selected=[next((s for s in cfg['sources'] if s['id']==sid),None) for sid in source_ids]
            if any(s is None or not s.get('approved') for s in selected):raise AppError('Nguồn chưa được cấu hình và xác nhận ánh xạ.')
            # External reads happen before the SQLite write transaction; commit uses CAS.
            from .importer import read_workbook,build_plan,apply_plan
            plans=[];failures=[]
            for source in selected:
                try:
                    adapter=self.source_adapters.get(source['adapter'])
                    if adapter is None:raise AppError('Bộ kết nối nguồn này chưa được bật.',409,'DEFERRED')
                    raw,filename=adapter.read(deepcopy(source));book=read_workbook(raw,filename)
                    expected_header=['Code','Period','Observation','Attendance N','Attendance D','Homework N','Homework D','Skill N','Skill D']
                    if not book['sheets'] or not book['sheets'][0]['rows'] or book['sheets'][0]['rows'][0]!=expected_header:raise AppError('Cấu trúc cột nguồn đã thay đổi. Giữ dữ liệu cũ và đối chiếu ánh xạ trước khi đọc lại.',409,'SOURCE_SCHEMA')
                    mapping={'teacherCode':0,'period':1,'sourceId':2,'attendance_n':3,'attendance_d':4,'homework_n':5,'homework_d':6,'skill_n':7,'skill_d':8}
                    plan=build_plan(book,'CSV',1,'metrics',mapping,{'sourceName':source['name'],'policy':'overwrite','percentUnit':'0-100'},initial,clock)
                    plans.append((source,plan))
                except AppError as e:failures.append({'id':source['id'],'name':source['name'],'status':'ERROR','message':str(e),'code':e.code})
            # Detect contradictory values across selected sources before applying either.
            observations={}
            for source,plan in plans:
                for item in plan['items']:
                    for metric in item.get('metrics',[]):observations.setdefault(metric_key(metric['data']),[]).append((source,item,metric))
            for entries in observations.values():
                if len({value_signature(m['data']) for _,_,m in entries})>1:
                    for source,item,metric in entries:item.update(status='review',message='Hai nguồn đưa số liệu khác nhau cho cùng quan sát. Cần chọn nguồn sau khi đối chiếu.')
            for source,plan in plans:
                for item in plan['items']:
                    for metric in item.get('metrics',[]):
                        checkpoint=source.get('baseline',{}).get(key_string(metric['data']));current=current_metric(initial,metric['data'])
                        kept=source.get('keptLocal',{}).get(key_string(metric['data']))
                        if kept=={'source':value_signature(metric['data']),'local':value_signature(current)}:
                            metric['skip']=True
                            continue
                        if checkpoint and value_signature(current)!=checkpoint and value_signature(metric['data'])!=value_signature(current):item.update(status='review',message='Số liệu local đã được sửa sau lần track trước; giữ lại để đối chiếu.')
                    if item.get('metrics') and item['status']!='review' and all(m.get('skip') for m in item['metrics']):item.update(status='duplicate',message='Giữ nguyên dữ liệu đã có hoặc quyết định giữ local đã xác nhận.')
            def commit(state):
                conf=tracking_state(state);review_queue=conf['reviewQueue'];results=list(failures);applied=0
                for source,plan in plans:
                    persisted=next(x for x in conf['sources'] if x['id']==source['id']);persisted['lastSuccess']=clock.stamp()
                    counts={k:sum(i['status']==k for i in plan['items']) for k in ('create','update','duplicate','skipped','review','error')}
                    for item in plan['items']:
                        if item['status'] not in ('review','error'):continue
                        fingerprint=digest([source['id'],item.get('key'),item['row'],[value_signature(m['data']) for m in item.get('metrics',[])],item['message']])
                        if not any(q['fingerprint']==fingerprint and q['status']=='pending' for q in review_queue):
                            if sum(q['status']=='pending' for q in review_queue)>=200:raise AppError('Hàng chờ có 200 mục. Hãy đối chiếu trước khi track thêm.',409)
                            review_queue.append({'id':uid(),'fingerprint':fingerprint,'status':'pending','sourceId':source['id'],'sourceName':source['name'],'row':item['row'],'summary':item.get('summary',''),'message':item['message'],'metrics':[deepcopy(m['data']) for m in item.get('metrics',[])],'current':{key_string(m['data']):value_signature(current_metric(state,m['data'])) for m in item.get('metrics',[])},'created':clock.stamp()})
                    # Use the shared importer for valid rows only, and do not create empty batches.
                    valid=[i for i in plan['items'] if i['status'] in ('create','update') and any(not m.get('skip') for m in i.get('metrics',[]))]
                    count=0
                    if valid:
                        prepared=deepcopy(plan);prepared['items']=valid;prepared['fingerprint']=digest(['manual-track',source['id'],request_id]);prepared['counts']=counts
                        count=apply_plan(self,state,prepared,clock,False)['applied'];applied+=count
                        for item in valid:
                            for metric in item.get('metrics',[]):persisted['baseline'][key_string(metric['data'])]=value_signature(current_metric(state,metric['data']))
                    results.append({'id':source['id'],'name':source['name'],'status':'REVIEW' if counts['review'] or counts['error'] else 'SUCCESS','counts':counts,'appliedRecords':count,'message':'Đã đọc nguồn thử; các mục xung đột được giữ để đối chiếu.' if counts['review'] or counts['error'] else 'Đã đọc nguồn thử theo yêu cầu.'})
                status='ERROR' if not plans else 'PARTIAL' if failures else 'REVIEW' if any(r['status']=='REVIEW' for r in results) else 'SUCCESS'
                run={'id':request_id,'status':status,'stamp':clock.stamp(),'sourceIds':source_ids,'sources':results,'appliedRecords':applied}
                conf['lastAttempt']=clock.stamp()
                if plans and not failures:conf['lastSuccess']=clock.stamp()
                if applied:conf['lastApplied']=clock.stamp()
                conf['runs']=(conf['runs']+[run])[-20:];conf['reviewQueue']=[q for q in review_queue if q['status']=='pending']+[q for q in review_queue if q['status']!='pending'][-30:]
                return run
            state,result=store.mutate(expected,request_id,'tracking.run',payload,commit,clock.stamp())
            return {'state':self.decorate(state,mode),'result':result}
        finally:self.tracking_locks[mode].release()

    def cmd_tracking_review(self,s,p,clock):
        if clock.mode!='demo':raise AppError('Luồng nguồn thử chỉ có trong kho Dùng thử.',409,'DEFERRED')
        cfg=tracking_state(s);issue=next((q for q in cfg['reviewQueue'] if q['id']==p.get('id')),None)
        if not issue:raise AppError('Không tìm thấy mục đối chiếu.',404)
        if issue['status']!='pending':return {'id':issue['id'],'replayed':True}
        decision=p.get('decision');reason=text(p.get('reason'),True,2000)
        if decision not in ('source','local'):raise AppError('Chọn giữ local hoặc áp dụng nguồn đã đối chiếu.')
        if decision=='source':
            if not issue['metrics']:raise AppError('Dòng lỗi không đủ dữ liệu. Hãy sửa nguồn rồi bấm cập nhật lại.')
            for m in issue['metrics']:
                if value_signature(current_metric(s,m))!=issue['current'].get(key_string(m)):raise AppError('Số liệu đã đổi kể từ lúc đưa vào hàng chờ. Bấm cập nhật để đối chiếu lại.',409,'REVIEW_STALE')
            for m in issue['metrics']:
                data=deepcopy(m);existing=current_metric(s,data)
                if existing:data['id']=existing['id']
                else:data.pop('id',None)
                self.cmd_metric_upsert(s,data,clock)
            source=next(x for x in cfg['sources'] if x['id']==issue['sourceId'])
            for m in issue['metrics']:
                source['baseline'][key_string(m)]=value_signature(current_metric(s,m));source.setdefault('keptLocal',{}).pop(key_string(m),None)
        if decision=='local':
            source=next(x for x in cfg['sources'] if x['id']==issue['sourceId'])
            for m in issue['metrics']:source.setdefault('keptLocal',{})[key_string(m)]={'source':value_signature(m),'local':value_signature(current_metric(s,m))}
        issue.update(status='resolved',decision=decision,reason=reason,resolvedAt=clock.stamp());return {'id':issue['id']}
