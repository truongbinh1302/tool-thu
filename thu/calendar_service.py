from datetime import datetime,date,timedelta,timezone
from copy import deepcopy
from .common import *

def participant_names(value):
    if isinstance(value,str):value=value.splitlines()
    if value is None:value=[]
    if not isinstance(value,list) or len(value)>100:raise AppError('Danh sách người tham gia không hợp lệ (tối đa 100 tên).')
    result=[];seen=set()
    for name in value:
        name=text(name,maximum=160)
        if '\n' in name or '\r' in name:raise AppError('Mỗi tên người tham gia cần nằm trên một dòng.')
        if name and fold(name) not in seen:result.append(name);seen.add(fold(name))
    return result

def meeting_participants(meeting,state):
    names=meeting.get('teacherNames',{});teachers={t['id']:t for t in state['teachers']};ids=meeting.get('invited',[])
    labels=[names.get(tid) or teachers.get(tid,{}).get('name') or tid for tid in ids];result=[]
    for tid,name in zip(ids,labels):
        if sum(fold(n)==fold(name) for n in labels)>1:name+=' ('+meeting.get('teacherCodes',{}).get(tid,teachers.get(tid,{}).get('code',tid))+')'
        result.append(name)
    for guest in meeting.get('externalGuests',[]):result.append(guest+' (khách ngoài tổ)' if any(fold(n)==fold(guest) for n in labels) else guest)
    return participant_names(result)

def event_description(event):
    note=event.get('note','');names=event.get('participantNames',[])
    if names:note+=('\n\n' if note else '')+'Người tham gia (dự kiến):\n'+'\n'.join('- '+n for n in names)
    return note

def calendar_events(state):
    """Project legacy and current linked records without writing or reading sources."""
    events=deepcopy(state['events']);meetings={m['id']:m for m in state['meetings']};teachers={t['id']:t['name'] for t in state['teachers']}
    for event in events:
        names=event.get('participantNames',[])
        if event.get('meetingId') in meetings:
            m=meetings[event['meetingId']];names=meeting_participants(m,state)
            event.update(title=m['title'],date=m['date'],time=m['time'],duration=m.get('duration',90),note=m.get('description',''),cancelled=m.get('status')=='cancelled')
        elif event.get('taskId'):
            task=next((t for t in state['tasks'] if t['id']==event['taskId']),None)
            if task:names=[teachers[task['teacher']]] if task.get('teacher') in teachers else []
        elif event.get('processId'):
            case=next((p for p in state['processes'] if p['id']==event['processId']),None)
            if case:names=[teachers[case['teacher']]] if case.get('teacher') in teachers else []
        if names!=event.get('participantNames',[]):event['sequence']=event.get('sequence',0)+1
        event['participantNames']=names
    return events

class CalendarMixin:
    def cmd_event_upsert(self,s,p,clock):
        from .service import record,put,ref
        r,old=record(s,'events',p)
        if old and (old.get('taskId') or old.get('processId')) and not p.get('_fromSource'):raise AppError('Hãy sửa tại công việc hoặc hồ sơ nguồn để giữ lịch đồng nhất.')
        if old and old.get('meetingId') and not p.get('_fromMeeting'):raise AppError('Hãy sửa lịch tại buổi họp liên quan để giữ dữ liệu đồng nhất.')
        recurrence=p.get('recurrence','')
        if recurrence not in ('','daily','weekly','monthly'):raise AppError('Chu kỳ lặp không hợp lệ.')
        d=day(p.get('date'));end=day(p.get('endDate'),True);all_day=bool(p.get('allDay'))
        if all_day and end and end<d:raise AppError('Ngày kết thúc phải từ ngày bắt đầu trở đi.')
        r.update(participantNames=participant_names(p.get('participantNames',r.get('participantNames',[]))),title=text(p.get('title'),True,240),date=d,time=time_of(p.get('time'),optional=all_day),duration=number(p.get('duration',60),5,4320,whole=True),endDate=end,allDay=all_day,recurrence=recurrence,alarm=number(p.get('alarm',15),0,10080,whole=True),type=text(p.get('type') or 'Công việc',maximum=100),note=text(p.get('note'),maximum=10000),cancelled=bool(p.get('cancelled')),meetingId=ref(s,'meetings',p.get('meetingId')),sourceKey=r.get('sourceKey',''),sequence=r.get('sequence',-1)+1,updated=clock.stamp(),color=p.get('color') if p.get('color') in ('pink','green','purple') else 'pink')
        return put(s,'events',r,old)
    def cmd_meeting_upsert(self,s,p,clock):
        from .service import record,put,ref,find
        r,old=record(s,'meetings',p);status=p.get('status','upcoming')
        if status not in ('upcoming','past','cancelled'):raise AppError('Trạng thái họp không hợp lệ.')
        invited=p.get('invited',r.get('invited',[t['id'] for t in s['teachers'] if t['status']=='active']))
        if not isinstance(invited,list) or len(set(invited))!=len(invited):raise AppError('Danh sách người mời không hợp lệ.')
        for tid in invited:ref(s,'teachers',tid,True)
        r.update(title=text(p.get('title'),True,240),date=day(p.get('date')),time=time_of(p.get('time'),False),duration=number(p.get('duration',90),5,4320,whole=True),description=text(p.get('description'),maximum=10000),status=status,invited=invited,teacherNames={t['id']:r.get('teacherNames',{}).get(t['id'],t['name']) for t in s['teachers'] if t['id'] in invited},teacherCodes={t['id']:r.get('teacherCodes',{}).get(t['id'],t['code']) for t in s['teachers'] if t['id'] in invited},externalGuests=participant_names(p.get('externalGuests',r.get('externalGuests',[]))),attendees=r.get('attendees',{}),contributions=r.get('contributions',{}),reports=r.get('reports',{}),note=text(p.get('note',r.get('note','')),maximum=12000),updated=clock.stamp())
        result=put(s,'meetings',r,old);e=next((e for e in s['events'] if e.get('sourceKey')=='meeting:'+r['id']),None)
        event={'title':r['title'],'date':r['date'],'time':r['time'],'duration':r['duration'],'note':r['description'],'participantNames':meeting_participants(r,s),'type':'Họp tổ','meetingId':r['id'],'_fromMeeting':True,'cancelled':status=='cancelled'}
        if e:event['id']=e['id']
        eid=self.cmd_event_upsert(s,event,clock)['id'];find(s,'events',eid)['sourceKey']='meeting:'+r['id'];return result
    def cmd_meeting_attendance(self,s,p,clock):
        from .service import find
        m=find(s,'meetings',p['id']);attendance=p.get('attendees',{});contributions=p.get('contributions',{});reports=p.get('reports',{})
        if not all(isinstance(x,dict) for x in (attendance,contributions,reports)):raise AppError('Dữ liệu điểm danh không hợp lệ.')
        if any(k not in m['invited'] for obj in (attendance,contributions,reports) for k in obj):raise AppError('Người được ghi nhận không thuộc danh sách buổi họp.')
        for tid in m['invited']:
            status=attendance.get(tid,'pending')
            if status not in ('pending','present','absent','excused'):raise AppError('Trạng thái điểm danh không hợp lệ.')
            m['attendees'][tid]=status;m['contributions'][tid]=text(contributions.get(tid),maximum=4000);m['reports'][tid]=url(reports.get(tid))
        m['note']=text(p.get('note'),maximum=12000);m['updated']=clock.stamp();return {'id':m['id']}
    def cmd_meeting_task(self,s,p,clock):
        from .service import find
        m=find(s,'meetings',p['meetingId']);key=m['id']+':'+text(p.get('decisionId'),True,100)
        old=next((t for t in s['tasks'] if t.get('decisionKey')==key),None)
        if old:return {'id':old['id']}
        r=self.cmd_task_upsert(s,{**p,'meetingId':m['id'],'category':'Sau cuộc họp'},clock);find(s,'tasks',r['id'])['decisionKey']=key;return r

def ics_escape(v):return str(v or '').replace('\\','\\\\').replace('\r\n','\n').replace('\r','\n').replace('\n','\\n').replace(';','\\;').replace(',','\\,')
def fold_ics(line):
    out=[];current='';size=0
    for c in line:
        n=len(c.encode('utf-8'))
        if size+n>75:out.append(current);current=' ';size=1
        current+=c;size+=n
    out.append(current);return '\r\n'.join(out)

def calendar_ics(events):
    lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Tool Thu//Local Calendar//VI','CALSCALE:GREGORIAN','METHOD:PUBLISH','X-WR-CALNAME:Tool Thư — Lịch nội bộ']
    for e in events:
        lines+=['BEGIN:VEVENT','UID:'+e['id']+'@tool-thu.local','DTSTAMP:'+datetime.fromisoformat(e['updated']).astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),'SEQUENCE:'+str(e.get('sequence',0))]
        if e.get('allDay'):
            lines+=['DTSTART;VALUE=DATE:'+e['date'].replace('-',''),'DTEND;VALUE=DATE:'+(date.fromisoformat(e.get('endDate') or e['date'])+timedelta(days=1)).strftime('%Y%m%d')]
        else:
            d=datetime.fromisoformat(e['date']+'T'+e['time']+':00+07:00');end=d+timedelta(minutes=e['duration'])
            lines+=['DTSTART:'+d.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),'DTEND:'+end.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')]
        lines+=['SUMMARY:'+ics_escape(e['title']),'DESCRIPTION:'+ics_escape(event_description(e)),'STATUS:'+('CANCELLED' if e.get('cancelled') else 'CONFIRMED')]
        if e.get('recurrence'):lines+=['RRULE:FREQ='+e['recurrence'].upper()]
        if e.get('alarm') and not e.get('cancelled'):lines+=['BEGIN:VALARM','TRIGGER:-PT'+str(e['alarm'])+'M','ACTION:DISPLAY','DESCRIPTION:'+ics_escape(e['title']),'END:VALARM']
        lines+=['END:VEVENT']
    lines+=['END:VCALENDAR'];return ('\r\n'.join(fold_ics(l) for l in lines)+'\r\n').encode('utf-8')
