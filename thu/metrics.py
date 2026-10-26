"""One owner for metric aggregation, rule evaluation and report generation."""
from copy import deepcopy
from datetime import date,timedelta
from .common import KINDS, monday

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
