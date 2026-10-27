"""Manual-only source tracking, sharing import validation and transaction rules."""
from copy import deepcopy
import threading
from .common import AppError,Clock,text,uid,digest,monday
from . import group

def tracking_state(state):
    return state.setdefault('tracking',{'sources':[],'runs':[],'reviewQueue':[],'lastAttempt':'','lastSuccess':'','lastApplied':''})

def metric_key(m):return (m['teacher'],m.get('classId',''),m['period'],m['kind'],m.get('observationId','summary'))
def value_signature(m):return digest([float(m[k]) if m.get(k) is not None else None for k in ('numerator','denominator','sourcePercent')]) if m else 'missing'
def current_metric(state,payload):return next((m for m in state['metrics'] if metric_key(m)==metric_key(payload)),None)
def key_string(m):return digest(metric_key(m))


TARGETS={'teachers':'teachers','tasks':'tasks','cases':'processes','qc':'errors'}
def record_for(state,template,item):
    target=TARGETS.get(template)
    if not target:return None
    rid=(item.get('data') or {}).get('id')
    return next((r for r in state[target] if (rid and r['id']==rid) or (not rid and r.get('importKey')==item.get('key'))),None)
def field_signature(rec,fields):return digest([rec.get(f) for f in fields]) if rec else 'missing'
def google_source_id(track):return 'g-'+digest([track['spreadsheetId'],track['sheet'],track['template']])[:16]
def save_google_source(state,plan,clock):
    """Remember an imported Google sheet so "Cập nhật dữ liệu" can re-read it later (only on button press)."""
    track=plan['_track'];cfg=tracking_state(state);sid=google_source_id(track)
    baseline={}
    for item in plan['items']:
        if item['status'] in ('create','update','duplicate'):
            rec=record_for(state,plan['template'],item)
            if rec:baseline[item['key']]=field_signature(rec,item.get('fields',[]))
    old=next((x for x in cfg['sources'] if x['id']==sid),None)
    source={'id':sid,'name':track['title']+' · '+track['sheet'],'adapter':'googleSheets','spreadsheetId':track['spreadsheetId'],'title':track['title'],'sheet':track['sheet'],'header':track['header'],'template':track['template'],'mapping':track['mapping'],'options':track['options'],'headerLabels':track['headerLabels'],'approved':True,'baseline':{**(old or {}).get('baseline',{}),**baseline},'created':(old or {}).get('created',clock.stamp()),'lastSuccess':clock.stamp()}
    if old:cfg['sources'][cfg['sources'].index(old)]=source
    else:cfg['sources'].append(source)
    return sid

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
        if mode!='demo':return self.track_google(mode,expected,request_id,source_ids)
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

    def track_google(self,mode,expected,request_id,source_ids):
        """Re-read saved Google Sheets sources once, because the user pressed the button (C03)."""
        if not isinstance(source_ids,list) or not 1<=len(source_ids)<=20 or any(not isinstance(x,str) for x in source_ids) or len(set(source_ids))!=len(source_ids):raise AppError('Chọn từ 1 đến 20 nguồn, không lặp.')
        source_ids=sorted(source_ids);payload={'sourceIds':source_ids};store=self.stores[mode];clock=Clock(mode)
        if not self.tracking_locks[mode].acquire(blocking=False):raise AppError('Một lượt cập nhật đang chạy. Hãy chờ lượt đó hoàn tất.',423,'TRACK_BUSY')
        try:
            if store.request_seen(request_id,'tracking.run',payload):
                s=store.read();run=next((r for r in tracking_state(s)['runs'] if r['id']==request_id),{})
                return {'state':self.decorate(s,mode),'result':{**run,'replayed':True}}
            initial=store.read()
            if type(expected)!=int or initial['_revision']!=expected:raise AppError('Dữ liệu đã thay đổi. Kiểm tra bản mới trước khi bấm cập nhật lại.',409,'STALE')
            cfg=tracking_state(initial);use_group='group' in source_ids
            if use_group and not group.configured(initial):raise AppError('Chưa thiết lập Bộ sheet của tổ. Vào Nguồn dữ liệu → Bộ sheet của tổ để dán link.')
            selected=[next((s for s in cfg['sources'] if s['id']==sid),None) for sid in source_ids if sid!='group']
            if any(s is None or not s.get('approved') or s.get('adapter')!='googleSheets' for s in selected):raise AppError('Nguồn chưa được lưu. Hãy nhập Google Sheet và tick "Lưu làm nguồn" trước.')
            if not self.google.status().get('connected'):raise AppError('Chưa kết nối Google (hoặc phiên đã hết hạn). Vào Nguồn dữ liệu → Kết nối Google rồi bấm lại.',409,'GOOGLE_LOGIN')
            from .importer import build_plan,columns
            plans=[];failures=[]
            # Network reads happen before the write transaction; the commit uses CAS on the revision.
            for source in selected:
                try:
                    book=self.google.read_book(source['spreadsheetId'],tabs=[source['sheet']])
                    labels={str(c['index']):c['label'] for c in columns(book,source['sheet'],source['header'],source['template'])['columns']}
                    for index,label in source.get('headerLabels',{}).items():
                        if labels.get(index)!=label:raise AppError('Cột "'+label+'" trong sheet đã đổi vị trí hoặc tên'+((' (giờ là "'+labels[index]+'")') if labels.get(index) else '')+'. Dữ liệu cũ được giữ; hãy nhập lại sheet này để ánh xạ lại.',409,'SOURCE_SCHEMA')
                    plan=build_plan(book,source['sheet'],source['header'],source['template'],source['mapping'],{**source.get('options',{}),'policy':'overwrite'},initial,clock)
                    plans.append((source,plan))
                except AppError as e:failures.append({'id':source['id'],'name':source['name'],'status':'ERROR','message':str(e),'code':e.code})
            group_parsed,group_failures=group.read_all(self.google,group.group_state(initial)['sources']) if use_group else ({},{})
            for kind,e in group_failures.items():failures.append({'id':'group:'+kind,'name':group.NAMES[kind],'status':'ERROR','message':str(e),'code':e.code})
            def commit(state):
                from .importer import apply_plan
                conf=tracking_state(state);results=list(failures);applied=0
                if group_parsed:
                    summary=group.apply_parsed(self,state,group_parsed,clock)
                    for kind in group.KINDS:
                        if kind in summary:results.append({'id':'group:'+kind,'name':group.NAMES[kind],'status':'SUCCESS','counts':None,'appliedRecords':summary[kind]['kept'],'message':group.message(kind,summary[kind])})
                    applied+=sum(x['kept'] for x in summary.values())
                for source,plan in plans:
                    persisted=next(x for x in conf['sources'] if x['id']==source['id']);baseline=persisted.setdefault('baseline',{})
                    kept=0;valid=[];notes=[]
                    for item in plan['items']:
                        if item['status'] in ('review','error'):notes.append('Dòng '+str(item['row'])+': '+item['message']);continue
                        if item['status']!='update':
                            if item['status']=='create':valid.append(item)
                            continue
                        rec=record_for(state,plan['template'],item);base=baseline.get(item['key'])
                        if rec and base and field_signature(rec,item.get('fields',[]))!=base:
                            item.update(status='kept',message='Giữ bản bạn đã sửa trong tool.');kept+=1;continue
                        if rec and plan['template']=='teachers':item['data']['status']=rec.get('status','active')
                        valid.append(item)
                    counts={k:sum(i['status']==k for i in plan['items']) for k in ('create','update','duplicate','skipped','review','error','kept')}
                    count=0
                    if valid:
                        prepared=deepcopy(plan);prepared['items']=valid;prepared['fingerprint']=digest(['manual-track',source['id'],request_id]);prepared['counts']=counts
                        count=apply_plan(self,state,prepared,clock,False)['applied'];applied+=count
                        state['sources'].pop()  # the saved source is already listed; history stays in importBatches
                    for item in plan['items']:
                        if item['status'] in ('create','update','duplicate'):
                            rec=record_for(state,plan['template'],item)
                            if rec:baseline[item['key']]=field_signature(rec,item.get('fields',[]))
                    persisted['lastSuccess']=clock.stamp()
                    waiting=counts['review']+counts['error']
                    message='Đã đọc lại sheet: '+str(counts['create'])+' dòng mới, '+str(counts['update'])+' dòng thay đổi'+(', giữ '+str(kept)+' dòng bạn đã sửa' if kept else '')+(', '+str(waiting)+' dòng cần kiểm tra (chưa nhập)' if waiting else '')+'.'
                    results.append({'id':source['id'],'name':source['name'],'status':'REVIEW' if waiting else 'SUCCESS','counts':counts,'appliedRecords':count,'message':message,'notes':notes[:20]})
                ok=bool(plans or group_parsed)
                status='ERROR' if not ok else 'PARTIAL' if failures else 'REVIEW' if any(r['status']=='REVIEW' for r in results) else 'SUCCESS'
                run={'id':request_id,'status':status,'stamp':clock.stamp(),'sourceIds':source_ids,'sources':results,'appliedRecords':applied}
                conf['lastAttempt']=clock.stamp()
                if ok and not failures:conf['lastSuccess']=clock.stamp()
                if applied:conf['lastApplied']=clock.stamp()
                conf['runs']=(conf['runs']+[run])[-20:]
                return run
            state,result=store.mutate(expected,request_id,'tracking.run',payload,commit,clock.stamp())
            return {'state':self.decorate(state,mode),'result':result}
        finally:self.tracking_locks[mode].release()

    def group_setup(self,mode,expected,request_id,links):
        """Save the team's sheet links: read each once now (button press), find its table, apply it."""
        if not isinstance(links,dict) or not links or any(k not in group.KINDS or not isinstance(v,str) for k,v in links.items()):raise AppError('Danh sách link không hợp lệ.')
        links={k:text(v,maximum=2000).strip() for k,v in links.items() if v.strip()}
        if not links:raise AppError('Dán ít nhất một link Google Sheet.')
        store=self.stores[mode];clock=Clock(mode)
        if not self.google.status().get('connected'):raise AppError('Chưa kết nối Google. Bấm Kết nối Google trước.',409,'GOOGLE_LOGIN')
        if not self.tracking_locks[mode].acquire(blocking=False):raise AppError('Một lượt cập nhật đang chạy. Hãy chờ lượt đó hoàn tất.',423,'TRACK_BUSY')
        try:
            payload={'links':links}
            if store.request_seen(request_id,'group.setup',payload):
                s=store.read();return {'state':self.decorate(s,mode),'result':{'replayed':True}}
            initial=store.read()
            if type(expected)!=int or initial['_revision']!=expected:raise AppError('Dữ liệu đã thay đổi. Tải lại rồi lưu lại.',409,'STALE')
            if 'teachers' not in links and not group.configured(initial):raise AppError('Cần link "Danh sách giáo viên" trước: các sheet khác được lọc theo danh sách này.')
            parsed,infos,errors={},{},{}
            for kind in group.KINDS:
                if kind not in links:continue
                try:parsed[kind],infos[kind]=group.read_kind(self.google,kind,links[kind])
                except AppError as e:errors[kind]=e
            if 'teachers' in errors and not group.configured(initial):raise AppError('Danh sách giáo viên: '+str(errors['teachers']),409,errors['teachers'].code)
            def commit(state):
                g=group.group_state(state)
                for kind,info in infos.items():
                    g['sources'][kind]={'spreadsheetId':info['spreadsheetId'],'title':info['title'],'sheet':parsed[kind]['sheet'],'header':parsed[kind]['header'],'link':links[kind],'saved':clock.stamp()}
                summary=group.apply_parsed(self,state,parsed,clock)
                return {'saved':sorted(infos),'summary':{k:{'message':group.message(k,v),'sheet':g['sources'][k]['sheet'],'title':g['sources'][k]['title']} for k,v in summary.items()},'errors':{k:str(e) for k,e in errors.items()}}
            state,result=store.mutate(expected,request_id,'group.setup',payload,commit,clock.stamp())
            return {'state':self.decorate(state,mode),'result':result}
        finally:self.tracking_locks[mode].release()

    def cmd_group_remove(self,s,p,clock):
        g=group.group_state(s);kind=p.get('kind')
        if kind not in group.KINDS or kind not in g['sources']:raise AppError('Không tìm thấy sheet này.',404)
        if kind=='teachers' and len(g['sources'])>1:raise AppError('Gỡ các sheet khác trước khi gỡ Danh sách giáo viên.')
        g['sources'].pop(kind);g['data'].pop(kind,None);return {'kind':kind}

    def cmd_group_settings(self,s,p,clock):
        g=group.group_state(s);pics=p.get('pic',g['settings']['pic'])
        if not isinstance(pics,list) or not pics or len(pics)>10 or any(not isinstance(x,str) or not x.strip() for x in pics):raise AppError('Chọn ít nhất một PIC.')
        try:threshold=float(p.get('passThreshold',g['settings']['passThreshold']))
        except (TypeError,ValueError):raise AppError('Ngưỡng Pass không hợp lệ.')
        if not 0<=threshold<=100:raise AppError('Ngưỡng Pass phải từ 0 đến 100%.')
        g['settings']={'pic':[text(x,True,60) for x in pics],'passThreshold':threshold}
        return {'settings':g['settings']}

    def cmd_tracking_source_remove(self,s,p,clock):
        cfg=tracking_state(s);source=next((x for x in cfg['sources'] if x['id']==p.get('id')),None)
        if not source:raise AppError('Không tìm thấy nguồn.',404)
        if source.get('adapter')!='googleSheets':raise AppError('Chỉ gỡ được nguồn Google Sheets đã lưu.')
        cfg['sources'].remove(source);return {'id':source['id'],'removed':True}

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
