"""Validation and time shared by storage, import and domain services."""
import json, math, hashlib, unicodedata, uuid
from datetime import datetime, date, timedelta, timezone
from urllib.parse import urlsplit
from pathlib import Path
VN = timezone(timedelta(hours=7), 'Asia/Ho_Chi_Minh')
KINDS = {'attendance':'Chuyên cần','homework':'Có làm BTVN','skill':'Đạt năng lực','homework_standard':'BTVN đạt chuẩn','homework_skill':'Đạt năng lực BTVN','student_skill':'Học viên đạt năng lực'}
class AppError(Exception):
    def __init__(self, message, status=400, code='INVALID'):
        super().__init__(message); self.status=status; self.code=code

def canonical(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
def digest(x): return hashlib.sha256(canonical(x).encode()).hexdigest()
def uid(): return uuid.uuid4().hex
def text(v, required=False, maximum=4000):
    if v is None: v=''
    if not isinstance(v, str): raise AppError('Nội dung phải là chuỗi văn bản.')
    v=v.strip()
    if required and not v: raise AppError('Vui lòng điền các trường bắt buộc.')
    if len(v)>maximum: raise AppError(f'Nội dung vượt quá {maximum} ký tự.')
    return v

def number(v, low=0, high=1000000, optional=False, whole=False):
    if v is None or v=='':
        if optional: return None
        raise AppError('Thiếu số liệu bắt buộc.')
    if isinstance(v, bool): raise AppError('Số liệu không hợp lệ.')
    try: n=float(v)
    except (ValueError,TypeError): raise AppError('Số liệu không hợp lệ.')
    if not math.isfinite(n) or not low<=n<=high or (whole and n!=int(n)): raise AppError('Số liệu nằm ngoài phạm vi hợp lệ.')
    return int(n) if whole else n

def day(v, optional=False):
    v=text(v)
    if not v and optional: return ''
    try:
        d=date.fromisoformat(v)
        if d.isoformat()!=v: raise ValueError()
        return v
    except ValueError: raise AppError('Ngày không hợp lệ (YYYY-MM-DD).')

def time_of(v, optional=True):
    v=text(v)
    if not v and optional: return ''
    try:
        if len(v)!=5 or datetime.strptime(v,'%H:%M').strftime('%H:%M')!=v: raise ValueError()
        return v
    except ValueError: raise AppError('Giờ không hợp lệ (HH:MM).')

def url(v):
    v=text(v,maximum=2000)
    if not v: return ''
    p=urlsplit(v)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or any(ord(c)<32 for c in v): raise AppError('Liên kết phải bắt đầu bằng http:// hoặc https:// và không chứa thông tin đăng nhập.')
    return v

def fold(v): return ''.join(c for c in unicodedata.normalize('NFD',str(v).lower().replace('đ','d')) if unicodedata.category(c)!='Mn').strip()
def monday(v):
    d=date.fromisoformat(day(v)); return (d-timedelta(days=d.weekday())).isoformat()

class Clock:
    def __init__(self, mode, fixed=None): self.mode=mode; self.fixed=fixed
    def now(self): return self.fixed or (datetime(2026,10,19,8,45,tzinfo=VN) if self.mode=='demo' else datetime.now(VN))
    def today(self): return self.now().date().isoformat()
    def stamp(self): return self.now().astimezone(timezone.utc).isoformat()

def empty_state():
    return {**{k:[] for k in ('teachers','classes','aliases','tasks','templates','processes','events','meetings','sources','metrics','errors','importBatches','reports','feedback')},'reportNotes':{},'settings':{'attendance':85,'homework':80,'skill':70,'operator':'>=','confirmed':False,'weekConfirmed':False,'effectiveDate':'','version':'unconfirmed'},'ruleDecisions':[],'connections':{'google':'DEFERRED','icloud':'DEFERRED','enabled':False}}

def demo_state():
    src=json.loads((Path(__file__).resolve().parents[1]/'examples/demo-seed.json').read_text(encoding='utf-8'))
    s=empty_state(); s['settings'].update(confirmed=True,weekConfirmed=True,effectiveDate='2026-01-01',version='DEMO-ONLY')
    for t in src['teachers']:
        teacher={k:v for k,v in t.items() if k not in ('classes','attendance','homework','skill','qc')}
        teacher.update(code=t['id'],status='active',email='',phone='');s['teachers'].append(teacher)
        for kind in ('attendance','homework','skill'):
            for period,delta in [('2026-10-19',0),('2026-10-12',-2)]:
                s['metrics'].append({'id':uid(),'teacher':t['id'],'classId':'','kind':kind,'period':period,'numerator':t[kind]+delta,'denominator':100,'sourcePercent':None,'observationId':'demo','source':'Mẫu minh họa, không phải số liệu khách hàng'})
        for i in range(t['qc']): s['errors'].append({'id':uid(),'teacher':t['id'],'classId':'','date':'2026-10-19','detail':'Tình huống minh họa cần theo dõi','category':'Minh họa','handling':'','status':'open','source':'Demo'})
    s['tasks']=src['tasks'];s['events']=src['events'];s['meetings']=src['meetings'];s['processes']=src['processes']
    for t in s['tasks']:t.update(owner='',classId='',meetingId='',productURL='',archived=False)
    for p in s['processes']:
        c={'id':uid(),'code':p['code'],'teacher':p['teacher'],'status':'active','assignments':[]};s['classes'].append(c);p.update(classId=c['id'],owner='',examDate='',sourceUpdated='',history=[],milestones=[],episode=1)
    for m in s['meetings']:
        m['invited']=[t['id'] for t in s['teachers']];m['teacherNames']={t['id']:t['name'] for t in s['teachers']};m['duration']=90
        old=next((e for e in s['events'] if e['title']==m['title']),None)
        e=old or {'id':uid(),'type':'Họp tổ','color':'pink'}
        e.update(title=m['title'],date=m['date'],time=m['time'],duration=90,note=m['description'],meetingId=m['id'],sourceKey='meeting:'+m['id'])
        if not old:s['events'].append(e)
    for e in s['events']:e.update(allDay=False,endDate='',recurrence='',alarm=15,cancelled=False,sequence=0,updated='2026-10-19T01:45:00+00:00')
    s['sources']=[dict(x,status='sample') for x in src['sources']]
    return s
