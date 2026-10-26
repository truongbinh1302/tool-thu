"""Interfaces for the final connection stage. No account or network access."""
from typing import Protocol
from copy import deepcopy
from .common import AppError
class CalendarAdapter(Protocol):
    def upsert(self,source_key:str,event:dict)->dict:...
    def cancel(self,source_key:str)->None:...
    def list(self)->list[dict]:...
class FakeCalendarAdapter:
    def __init__(self):self.events={};self.fail_next=False
    def _check(self):
        if self.fail_next:self.fail_next=False;raise AppError('Lỗi kết nối giả lập; chưa thay đổi lịch.',503)
    def upsert(self,source_key,event):
        self._check();self.events[source_key]={**deepcopy(event),'sourceKey':source_key,'cancelled':False};return deepcopy(self.events[source_key])
    def cancel(self,source_key):
        self._check()
        if source_key in self.events:self.events[source_key]['cancelled']=True
    def list(self):self._check();return deepcopy(list(self.events.values()))

class SheetsSourceAdapter(Protocol):
    def read(self, source:dict)->tuple[bytes,str]:...

class FakeSheetsSourceAdapter:
    """Read only when invoked by an explicit tracking action. No network/timers."""
    def __init__(self):self.read_count=0
    def read(self,source):
        self.read_count+=1
        scenario=source.get('scenario','baseline')
        if scenario=='offline':raise AppError('Nguồn thử đang mất kết nối. Bấm cập nhật lại khi sẵn sàng.',503,'SOURCE_OFFLINE')
        if scenario=='denied':raise AppError('Nguồn thử bị thu hồi quyền đọc. Dữ liệu đã lưu được giữ nguyên.',403,'SOURCE_DENIED')
        values={'baseline':(82,74,68),'changed':(97,93,90),'conflict':(55,50,45),'missing':('', '', '')}.get(scenario)
        if values is None:raise AppError('Kịch bản nguồn thử không hợp lệ.')
        a,h,k=values;period=source['period'];code='GV001'
        header='Code,Period,Observation,Attendance N,Attendance D,Homework N,Homework D,Skill N,Skill D\n'
        if scenario=='missing':row=f'{code},{period},demo,,,,,,\n'
        else:row=f'{code},{period},demo,{a},100,{h},100,{k},100\n'
        return (header+row).encode('utf-8'),source['id']+'.csv'
