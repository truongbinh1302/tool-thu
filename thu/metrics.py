"""One owner for metric aggregation, rule evaluation and report generation."""
from copy import deepcopy
from datetime import date,timedelta
from .common import KINDS, monday, fold
import unicodedata

def quarter(d):
    return d[:4]+'-Q'+str((int(d[5:7])-1)//3+1)

def vietnamese_key(name):
    # Vietnamese base letters remain distinct; tone marks are secondary.
    alphabet='aăâbcdđeêfghijklmnoôơpqrstuưvwxyz'
    tones='\u0300\u0309\u0303\u0301\u0323'
    letters=[];accent=[]
    for c in unicodedata.normalize('NFD',name.casefold()):
        if c in tones:
            if accent:accent[-1]=tones.index(c)+1
        elif unicodedata.combining(c):
            if letters:letters[-1]=unicodedata.normalize('NFC',letters[-1]+c)
        else:letters.append(c);accent.append(0)
    return ([alphabet.index(c)+1 if c in alphabet else ord(c)-1000 for c in letters],accent)

def score_report(s,period):
    """Scores are derived exclusively from manual entries, never from QC/deadlines."""
    from .group import name_key
    group_errors=s.get('group',{}).get('data',{}).get('errors',{}).get('rows',[])
    result=[]
    for t in s['teachers']:
        entries=sorted([e for e in s['scoreEntries'] if e['teacher']==t['id'] and quarter(e['date'])==period],key=lambda e:(e['date'],e['created'],e['id']))
        plus=sum(e['delta']==1 for e in entries);minus=len(entries)-plus
        errors=[r for r in group_errors if name_key(r['teacher'])==name_key(t['name']) and (quarter(r['date']) if r.get('date') else r.get('period'))==period]
        tasks=[r for r in s['tasks'] if r.get('teacher')==t['id'] and not r.get('archived') and r['status']!='done']
        qc=[r for r in s['errors'] if r['teacher']==t['id'] and quarter(r['date'])==period]
        n=len(errors)
        result.append({'id':t['id'],'name':t['name'],'code':t['code'],'score':50+plus-minus,'plus':plus,'minus':minus,'entries':entries,'groupErrors':errors,'errorCount':n,'handling':['','Nhắc nhở','Cảnh cáo','Trừ 1/2 công','Trừ 1 công'][min(n,4)],'qc':qc,'openTasks':len(tasks),'overdueTasks':sum(bool(r.get('overdue')) for r in tasks)})
    active={t['id'] for t in s['teachers'] if t['status']=='active'}
    ranking=sorted([r for r in result if r['id'] in active],key=lambda r:(-r['score'],vietnamese_key(r['name']),r['code']))
    for i,r in enumerate(ranking):r['rank']=i+1 if i==0 or r['score']!=ranking[i-1]['score'] else ranking[i-1]['rank']
    return {'teachers':{r['id']:r for r in result},'ranking':ranking}

def employee_details(s,t,clock):
    """Read only the saved state. Linked calendar projections are shown once."""
    from .group import name_key
    tid=t['id'];deadlines=[];g=s.get('group',{}).get('data',{})
    def add(source,r,d,title,action='',note='',time=''):
        if not d:return
        overdue=d<clock.today() or (d==clock.today() and bool(time) and time<clock.now().strftime('%H:%M'))
        deadlines.append({'source':source,'id':str(r.get('id',r.get('row',''))),'date':d,'time':time,'title':title,'action':action,'note':note,'urgency':'overdue' if overdue else 'soon' if d<=(date.fromisoformat(clock.today())+timedelta(days=7)).isoformat() else ''})
    tasks=[r for r in s['tasks'] if r.get('teacher')==tid]
    for r in tasks:
        if not r.get('archived') and r['status']!='done':add('Task',r,r['date'],r['title'],'task:'+r['id'],r.get('note',''),r.get('time',''))
    for r in g.get('deadlines',{}).get('rows',[]):
        if name_key(r['teacher'])==name_key(t['name']):add('14 ngày',r,r.get('deadline'),r['class'],note=r.get('pic',''))
    for r in s['processes']:
        if r['teacher']==tid and r['step']<4:
            add('Hồ sơ',r,r.get('due'),r['code'],'process:'+r['id'],r.get('plan',''))
    for r in s['meetings']:
        if tid in r.get('invited',[]) and r.get('status')!='cancelled':add('Họp',r,r['date'],r['title'],'meeting:'+r['id'],r.get('description',''),r.get('time',''))
    for r in s['events']:
        if r.get('cancelled') or r.get('taskId') or r.get('meetingId') or r.get('sourceKey','').startswith('process:'):continue
        process=next((p for p in s['processes'] if p['id']==r.get('processId')),None)
        if r.get('teacher')==tid or tid in r.get('teacherIds',[]) or any(fold(n)==fold(t['name']) for n in r.get('participantNames',[])) or (process and process['teacher']==tid):
            add('Lịch',r,r['date'],r['title'],'event:'+r['id'],r.get('note',''),'' if r.get('allDay') else r.get('time',''))
    tables={}
    for kind in ('homework','pass'):
        table=g.get(kind,{})
        tables[kind]={'columns':table.get('columns',[]),'rows':[r for r in table.get('rows',[]) if name_key(r['teacher'])==name_key(t['name'])]}
    return {'tasks':tasks,'deadlines':sorted(deadlines,key=lambda r:(r['date'],r['time'],r['source'],r['title'])),'tables':tables}

def evaluations(s,clock):
    periods={quarter(clock.today())}
    year=int(clock.today()[:4])
    for y in (year-1,year):periods.update(f'{y}-Q{q}' for q in range(1,5))
    for rows,key in ((s['scoreEntries'],'date'),(s['errors'],'date'),(s['metrics'],'period')):
        periods.update(quarter(r[key]) for r in rows if r.get(key))
    for r in s.get('group',{}).get('data',{}).get('errors',{}).get('rows',[]):
        if r.get('date'):periods.add(quarter(r['date']))
        elif len(r.get('period',''))==7:periods.add(r['period'])
    return {'current':quarter(clock.today()),'periods':sorted(periods,reverse=True),'quarters':{p:score_report(s,p) for p in periods},'employees':{t['id']:employee_details(s,t,clock) for t in s['teachers']}}

def aggregate(rows):
    base={'numerator':None,'denominator':None,'pct':None,'displayPct':None,'status':'NO_DATA','sources':list(dict.fromkeys(r.get('source','Nhập tay') for r in rows))}
    if not rows:return base
    # A teacher summary and class observations may describe the same students.
    by_teacher={}
    for r in rows:by_teacher.setdefault(r['teacher'],set()).add(bool(r.get('classId')))
    if any(len(x)>1 for x in by_teacher.values()):return {**base,'status':'NEEDS_REVIEW'}
    counts=[r for r in rows if r.get('numerator') is not None and r.get('denominator') is not None]
    if len(counts)!=len(rows):
        return {**base,'displayPct':rows[0].get('sourcePercent') if len(rows)==1 else None,'status':'INSUFFICIENT_DATA'}
    n=sum(r['numerator'] for r in counts);d=sum(r['denominator'] for r in counts)
    return {**base,'numerator':n,'denominator':d,'pct':n/d*100 if d else None,'displayPct':n/d*100 if d else None,'status':'OK' if d else 'INSUFFICIENT_DATA'}

def effective_rules(s,period):
    candidates=[x for x in s.get('ruleDecisions',[]) if x.get('effectiveDate','9999')<=period]+([s['settings']] if s['settings'].get('effectiveDate') and s['settings']['effectiveDate']<=period else [])
    return deepcopy(max(enumerate(candidates),key=lambda x:(x[1].get('effectiveDate',''),x[0]))[1]) if candidates else {**s['settings'],'confirmed':False}

def evaluate(values,rules):
    if all(v['status']=='NO_DATA' for v in values.values()):return 'NO_DATA'
    if not rules.get('confirmed') or not rules.get('weekConfirmed'):return 'NEEDS_REVIEW'
    if any(v['status']=='NEEDS_REVIEW' for v in values.values()):return 'NEEDS_REVIEW'
    for k in ('attendance','homework','skill'):
        p=values[k]['pct']
        if p is not None and (p<rules[k] if rules['operator']=='>=' else p<=rules[k]):return 'BELOW_THRESHOLD'
    if any(values[k]['status']!='OK' for k in ('attendance','homework','skill')):return 'INSUFFICIENT_DATA'
    return 'PASS'

def report(s,period):
    period=monday(period);end=(date.fromisoformat(period)+timedelta(days=6)).isoformat();rules=effective_rules(s,period)
    rows=[r for r in s['metrics'] if r['period']==period];observed={r['teacher'] for r in rows}
    def included(t):
        history=t.get('statusHistory') or [{'date':t.get('created','0000')[:10],'status':t.get('status')}]
        history=sorted(enumerate(history),key=lambda h:(h[1]['date'],h[0]))
        before=[h for _,h in history if h['date']<=period]
        active_start=bool(before and before[-1]['status']=='active')
        active_during=any(h['status']=='active' and period<=h['date']<=end for _,h in history)
        return (active_start or active_during) and t.get('created','0000')[:10]<=end
    teachers=[t for t in s['teachers'] if included(t) or t['id'] in observed]
    result=[]
    for t in teachers:
        values={k:aggregate([r for r in rows if r['teacher']==t['id'] and r['kind']==k]) for k in KINDS}
        result.append({'id':t['id'],'code':t['code'],'name':t['name'],'values':values,'status':evaluate(values,rules),'qc':sum(1 for e in s['errors'] if e['teacher']==t['id'] and period<=e['date']<=end)})
    return {'period':period,'end':end,'rules':rules,'status':'DRAFT','teachers':result,'totals':{k:aggregate([r for r in rows if r['kind']==k]) for k in KINDS},'riskCount':sum(t['status']=='BELOW_THRESHOLD' for t in result),'incompleteCount':sum(t['status'] not in ('PASS','BELOW_THRESHOLD') for t in result),'notes':s['reportNotes'].get(period,''),'sourceRevision':s['_revision']}
