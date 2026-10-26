"""Bounded, offline XLSX/CSV reader. Never evaluates workbook formulas or opens links."""
import csv,io,zipfile,re,posixpath
import xml.etree.ElementTree as ET
from datetime import date,datetime,timedelta
from .common import *
from .service import find
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
SENSITIVE=re.compile(r'(password|passwd|mat khau|mail app|tai khoan dang nhap|login|credential|token|secret)',re.I)
INLINE_SECRET=re.compile(r'(pass(?:word)?|mật khẩu|mat khau|token)\s*[:=]',re.I)
BASE_FIELDS={'teacherCode':'Mã giáo viên','teacherName':'Tên giáo viên (cần xác minh)','classCode':'Mã lớp','sourceId':'Mã quan sát/sự kiện từ nguồn'}
FIELDS={
 'teachers':{'code':'Mã giáo viên *','name':'Họ tên *','level':'Chứng chỉ/cấp độ','type':'Hình thức','phone':'Số điện thoại','email':'Email liên hệ','alias':'Mã tương ứng đã xác minh'},
 'tasks':{'title':'Tên công việc *','date':'Ngày hạn *','time':'Giờ hạn','category':'Hạng mục','teacherCode':'Mã giáo viên','teacherName':'Tên giáo viên','note':'Ghi chú','sourceId':'Mã công việc nguồn'},
 'cases':{**BASE_FIELDS,'code':'Mã lớp *','start':'Ngày tiếp nhận','due':'Hạn nhập thủ công','examDate':'Ngày thi','sourceUpdated':'Ngày cập nhật nguồn','students':'Sĩ số','passed':'Số đạt','plan':'Phương án','owner':'Người phụ trách'},
 'qc':{**BASE_FIELDS,'date':'Ngày lỗi *','detail':'Nội dung lỗi *','category':'Loại lỗi','handling':'Xử lý'},
 'metrics':{**BASE_FIELDS,'period':'Ngày trong tuần báo cáo',**{k+'_'+suffix:label+' — '+description for k,label in KINDS.items() for suffix,description in [('n','Tử số'),('d','Mẫu số'),('pct','% nguồn (không mẫu số)')]}}
}
ALIASES={'code':['ma giao vien','ma gv','code'],'name':['ho va ten','ho ten','ten giao vien','ten gv'],'teacherCode':['ma giao vien','ma gv'],'teacherName':['giao vien','ten giao vien','ho va ten'],'title':['cong viec','ten cong viec','noi dung cong viec'],'date':['ngay','ngay ghi nhan','ngay loi','deadline'],'detail':['noi dung loi','loi','mo ta loi'],'students':['si so','so hoc vien'],'passed':['so dat','so hoc vien dat'],'plan':['phuong an','huong xu ly'],'code_case':['ma lop','lop'],'classCode':['ma lop'],'due':['han','han xu ly'],'start':['ngay tiep nhan'],'period':['tuan','ky bao cao'],'phone':['so dien thoai','sdt'],'email':['email lien he','email'],'level':['chung chi','cap do','ielts'],'type':['hinh thuc'],'note':['ghi chu'],'sourceId':['id','ma su kien']}

def col_index(s):
    n=0
    for c in s:n=n*26+ord(c.upper())-64
    return n-1

def scrub_sheets(sheets):
    for sheet in sheets:
        forbidden=set();warnings=sheet.setdefault('warnings',[])
        for row in sheet['rows']:
            for i,v in enumerate(row):
                if isinstance(v,str) and SENSITIVE.search(fold(v)):
                    forbidden.add(i)
        if forbidden:warnings.append('Đã bỏ các cột có nhãn thông tin đăng nhập; không dùng để nhập dữ liệu.')
        for row in sheet['rows']:
            for i,v in enumerate(row):
                if i in forbidden or (isinstance(v,str) and INLINE_SECRET.search(v)):row[i]='[ĐÃ ẨN]'
        # Suggest only; customer must select the actual header row.
        best=max(range(min(15,len(sheet['rows']))),key=lambda i:sum(any(term in fold(v) for term in ('ma gv','giao vien','ho ten','ma lop','noi dung','cong viec','ngay')) for v in sheet['rows'][i]),default=0)
        sheet['suggestedHeader']=sheet['rowNumbers'][best] if sheet['rowNumbers'] else 1

def read_workbook(raw,filename):
    if len(raw)>20*1024*1024:raise AppError('File vượt giới hạn 20 MB.')
    filename=text(filename,True,240);sheets=[];missing=0;epoch='1900'
    if filename.lower().endswith('.csv'):
        try:
            decoded=raw.decode('utf-8-sig');rows=list(csv.reader(io.StringIO(decoded),strict=True))
            if len(rows)>50000 or any(len(r)>256 for r in rows):raise AppError('CSV quá nhiều hàng/cột.')
            nonempty=[(i+1,r) for i,r in enumerate(rows) if any(v.strip() for v in r)]
            sheets=[{'name':'CSV','rows':[r for _,r in nonempty],'rowNumbers':[i for i,_ in nonempty],'warnings':[]}]
        except (UnicodeDecodeError,csv.Error):raise AppError('CSV cần mã hóa UTF-8 và cấu trúc hợp lệ.')
    elif filename.lower().endswith('.xlsx'):
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                infos=z.infolist()
                if len(infos)>10000 or sum(i.file_size for i in infos)>100*1024*1024 or any(i.file_size>50*1024*1024 for i in infos):raise AppError('Workbook vượt giới hạn giải nén an toàn.')
                if any('vbaproject' in i.filename.lower() for i in infos):raise AppError('Không nhận workbook có macro.')
                def xml(name):
                    data=z.read(name)
                    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise AppError('XML không được chứa khai báo thực thể.')
                    return ET.fromstring(data)
                shared=[]
                if 'xl/sharedStrings.xml' in z.namelist():shared=[''.join(x.itertext()) if False else ''.join(t.text or '' for t in x.findall('.//m:t',NS)) for x in xml('xl/sharedStrings.xml')]
                wb=xml('xl/workbook.xml');prop=wb.find('m:workbookPr',NS)
                if prop is not None and prop.get('date1904') in ('1','true'):epoch='1904'
                rels={r.get('Id'):r.get('Target') for r in xml('xl/_rels/workbook.xml.rels') if r.get('TargetMode')!='External'}
                formats={}
                if 'xl/styles.xml' in z.namelist():
                    styles=xml('xl/styles.xml');custom={int(n.get('numFmtId')):n.get('formatCode','') for n in styles.findall('m:numFmts/m:numFmt',NS)}
                    formats={i:custom.get(int(x.get('numFmtId','0')),'') for i,x in enumerate(styles.findall('m:cellXfs/m:xf',NS))}
                total=0
                for sh in wb.findall('m:sheets/m:sheet',NS):
                    target=rels.get(sh.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'),'')
                    path=posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
                    if not path.startswith('xl/worksheets/') or not path.endswith('.xml'):continue
                    rows=[];numbers=[];warnings=[]
                    for row in xml(path).findall('m:sheetData/m:row',NS):
                        cells={}
                        for cell in row.findall('m:c',NS):
                            v=cell.find('m:v',NS);formula=cell.find('m:f',NS);inline=cell.find('m:is',NS)
                            if v is None and formula is None and inline is None:continue # Styled blanks are not observations.
                            index=col_index(re.sub('[^A-Za-z]','',cell.get('r','A1')))
                            if not 0<=index<256:raise AppError('Dữ liệu có hơn 256 cột có nội dung.')
                            total+=1
                            if total>500000:raise AppError('Workbook có quá nhiều ô có nội dung.')
                            typ=cell.get('t');value=v.text if v is not None else None
                            if formula is not None and value is None:missing+=1;value=None
                            elif typ=='s':value=shared[int(value)] if value is not None else None
                            elif typ=='inlineStr':value=''.join(t.text or '' for t in inline.findall('.//m:t',NS)) if inline is not None else ''
                            elif typ=='e':value=None;warnings.append('Một số ô nguồn có lỗi công thức; được giữ là thiếu dữ liệu.')
                            elif value is not None and typ not in ('str','b'):
                                try:
                                    n=float(value);value=int(n) if n.is_integer() else n
                                except ValueError:pass
                            fmt=formats.get(int(cell.get('s','0')),'')
                            if isinstance(value,int) and re.fullmatch(r'0{2,}',fmt):value=str(value).zfill(len(fmt))
                            cells[index]=value
                        if cells:
                            rows.append([cells.get(i) for i in range(max(cells)+1)]);numbers.append(int(row.get('r',len(rows))))
                            if len(rows)>50000:raise AppError('Sheet có hơn 50.000 hàng dữ liệu.')
                    sheets.append({'name':sh.get('name','Sheet'),'rows':rows,'rowNumbers':numbers,'warnings':list(dict.fromkeys(warnings))})
        except AppError:raise
        except (zipfile.BadZipFile,KeyError,ET.ParseError,ValueError,IndexError,TypeError,OverflowError):raise AppError('Workbook XLSX không hợp lệ hoặc bị hỏng.')
    else:raise AppError('Chỉ nhận .xlsx hoặc .csv UTF-8; không nhận .xls/.xlsm.')
    if not any(sheet['rows'] for sheet in sheets):raise AppError('File không có dữ liệu để nhập. Hãy kiểm tra sheet và hàng tiêu đề.')
    scrub_sheets(sheets)
    return {'filename':filename,'sha256':hashlib.sha256(raw).hexdigest(),'epoch':epoch,'missingCache':missing,'sheets':sheets}

def excel_day(value,epoch='1900',year=None):
    if value is None or value=='':return ''
    if isinstance(value,(int,float)):
        try:
            if isinstance(value,bool):raise ValueError()
            n=int(value)
            if epoch=='1904':d=date(1904,1,1)+timedelta(days=n)
            else:
                if n==60:raise AppError('Ngày giả 29/02/1900 trong Excel không hợp lệ.')
                d=date(1899,12,31)+timedelta(days=n-(1 if n>60 else 0))
        except (ValueError,OverflowError):raise AppError('Ngày Excel nằm ngoài phạm vi hợp lệ.')
        return day(d.isoformat())
    s=str(value).strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}',s):return day(s[:10])
    m=re.search(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?',s)
    if m:
        y=int(m[3]) if m[3] else int(year) if year else None
        if not y:raise AppError('Ngày thiếu năm; hãy chọn năm nguồn trong bước ánh xạ.')
        try:return date(y,int(m[2]),int(m[1])).isoformat()
        except ValueError:raise AppError('Ngày trong nguồn không hợp lệ.')
    raise AppError('Không đọc được ngày từ nguồn.')

def excel_time(value):
    if value is None or value=='':return ''
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        if not math.isfinite(value) or not 0<=value<1:raise AppError('Giờ Excel phải nằm trong một ngày (00:00–23:59).')
        seconds=round(value*86400)
        if seconds>=86400 or seconds%60:raise AppError('Giờ nguồn có giây; hãy đổi thành giờ/phút trước khi nhập.')
        return f'{seconds//3600:02d}:{seconds%3600//60:02d}'
    return time_of(str(value).strip())

def get_sheet(book,name):
    sheet=next((x for x in book['sheets'] if x['name']==name),None)
    if sheet is None:raise AppError('Sheet không tồn tại.')
    return sheet

def columns(book,sheet_name,header,template):
    sheet=get_sheet(book,sheet_name)
    if template not in FIELDS:raise AppError('Mẫu nhập không hợp lệ.')
    if header not in sheet['rowNumbers']:raise AppError('Hàng tiêu đề phải có dữ liệu trong sheet.')
    index=sheet['rowNumbers'].index(header);labels=sheet['rows'][index];cols=[];mapping={}
    width=max([len(labels)]+[len(r) for r in sheet['rows'][index+1:index+7]])
    for i in range(width):
        label=labels[i] if len(labels)>i else None
        if label=='[ĐÃ ẨN]':continue
        if label in (None,''):
            if not any(len(r)>i and r[i] not in (None,'','[ĐÃ ẨN]') for r in sheet['rows'][index+1:index+7]):continue
            label='Cột '+str(i+1)+' (không tiêu đề)'
        cols.append({'index':i,'label':str(label),'samples':[str(r[i])[:120] for r in sheet['rows'][index+1:index+5] if len(r)>i and r[i] is not None and r[i]!='[ĐÃ ẨN]'][:3]})
    for field in FIELDS[template]:
        terms=ALIASES.get('code_case' if field=='code' and template=='cases' else field,[])
        matches=[c['index'] for c in cols if fold(c['label']) in terms]
        if len(matches)==1:mapping[field]=matches[0]
    return {'fields':FIELDS[template],'columns':cols,'mapping':mapping,'warnings':sheet['warnings'],'preview':sheet['rows'][index+1:index+7]}

def build_plan(book,sheet_name,header,template,mapping,options,state,clock):
    sheet=get_sheet(book,sheet_name)
    if template not in FIELDS or not isinstance(mapping,dict) or not isinstance(options,dict):raise AppError('Cấu hình nhập không hợp lệ.')
    if header not in sheet['rowNumbers']:raise AppError('Hàng tiêu đề không tồn tại.')
    if any(k not in FIELDS[template] or type(v)!=int or not 0<=v<256 for k,v in mapping.items()):raise AppError('Ánh xạ cột không hợp lệ.')
    required={'teachers':['code','name'],'tasks':['title','date'],'cases':['code'],'qc':['date','detail'],'metrics':[]}[template]
    if any(k not in mapping for k in required):raise AppError('Chưa ánh xạ đủ cột bắt buộc.')
    source=text(options.get('sourceName') or book['filename'],True,240);policy=options.get('policy','fill')
    if policy not in ('fill','overwrite','skip'):raise AppError('Chính sách cập nhật không hợp lệ.')
    teacher_map=options.get('teacherMap',{})
    if not isinstance(teacher_map,dict):raise AppError('Ánh xạ giáo viên không hợp lệ.')
    def cell(row,key):
        index=mapping.get(key);return row[index] if index is not None and len(row)>index and row[index]!='[ĐÃ ẨN]' else None
    def string(v):return '' if v is None else str(v).strip()
    def teacher_for(row):
        code=string(cell(row,'teacherCode'));name=string(cell(row,'teacherName'));key=('code:'+code) if code else ('name:'+name)
        if key in teacher_map:
            tid=ref_teacher(teacher_map[key]);return tid,key,code
        candidates=[]
        if code:
            candidates=[t for t in state['teachers'] if fold(t['code'])==fold(code)]
            alias=next((a for a in state['aliases'] if a['alias_key']==fold(source)+'|'+fold(code)),None)
            if alias:candidates=[find(state,'teachers',alias['teacher'])]
            if len(candidates)==1 and (not name or fold(candidates[0]['name'])==fold(name)):return candidates[0]['id'],key,''
        if template=='tasks' and not code and not name:return '',key,''
        if not code and not name:raise AppError('Thiếu mã/tên giáo viên. Hãy kiểm tra ánh xạ cột nguồn.')
        suggestions=[t['id'] for t in state['teachers'] if name and fold(t['name'])==fold(name)]
        unresolved[key]={'key':key,'code':code,'name':name,'suggestions':suggestions};raise AppError('Cần xác minh giáo viên '+(code or name or '(thiếu mã/tên)'),400,'REVIEW')
    def ref_teacher(id):return find(state,'teachers',id)['id']
    items=[];seen=set();unresolved={};start=sheet['rowNumbers'].index(header)+1
    for i,row in enumerate(sheet['rows'][start:],start):
        if not any(v not in (None,'','[ĐÃ ẨN]') for v in row):continue
        line=sheet['rowNumbers'][i];item={'row':line,'status':'create','message':'','changes':[]}
        try:
            data={};target='';alias_code='';tid=''
            if template=='teachers':
                code=string(cell(row,'code'));name=string(cell(row,'name'))
                if not code or not name:raise AppError('Thiếu mã/họ tên; dòng tiêu đề hoặc ghi chú không được coi là giáo viên.')
                if SENSITIVE.search(fold(name)):raise AppError('Dòng có dấu hiệu chứa thông tin đăng nhập.')
                limits={'code':80,'name':160,'level':120,'type':80,'phone':40,'email':160}
                data={k:text(string(cell(row,k)),k in ('code','name'),limits[k]) for k in limits if k in mapping};data.update(status='active');key='teacher:'+fold(code);target='teachers'
                old=next((t for t in state['teachers'] if fold(t['code'])==fold(code)),None)
                if old:data={**old,**data,'status':old['status']}
                if old and fold(old['name'])!=fold(name) and policy!='overwrite':raise AppError('Cùng mã nhưng khác tên; cần đối chiếu trước khi chọn ghi đè.',400,'REVIEW')
            else:
                tid,resolve_key,alias_code=teacher_for(row);data['teacher']=tid;old=None
                if template=='tasks':
                    data.update(title=text(string(cell(row,'title')),True,240),date=day(excel_day(cell(row,'date'),book['epoch'],options.get('year'))),time=excel_time(cell(row,'time')),category=text(string(cell(row,'category')) or 'Nhập file',maximum=100),note=text(string(cell(row,'note')),maximum=10000));target='tasks'
                elif template=='cases':
                    data.update(code=text(string(cell(row,'code')),True,100),**{k:excel_day(cell(row,k),book['epoch'],options.get('year')) for k in ('start','due','examDate','sourceUpdated')},students=number(cell(row,'students'),optional=True,whole=True),passed=number(cell(row,'passed'),optional=True,whole=True),plan=text(string(cell(row,'plan')),maximum=10000),owner=text(string(cell(row,'owner')),maximum=160));target='processes'
                    if data['passed'] is not None and (data['students'] is None or data['passed']>data['students']):raise AppError('Số đạt không hợp lệ.')
                    if data['start'] and data['due'] and data['due']<data['start']:raise AppError('Hạn xử lý không thể trước ngày tiếp nhận.')
                    old=next((p for p in state['processes'] if fold(p['code'])==fold(data['code']) and p['step']<4),None)
                    closed=any(fold(p['code'])==fold(data['code']) and p['step']==4 for p in state['processes'])
                    if closed and not old and not (data['start'] or cell(row,'sourceId')):raise AppError('Lớp đã có hồ sơ hoàn tất; cần ngày tiếp nhận/mã đợt để tạo lần xử lý mới.',400,'REVIEW')
                elif template=='qc':
                    raw_detail=cell(row,'detail')
                    if not isinstance(raw_detail,str) or not raw_detail.strip() or re.fullmatch(r'[0-9.,%\s]+',raw_detail):raise AppError('Nội dung lỗi không phải văn bản; có thể đang lệch cột.')
                    data.update(date=day(excel_day(cell(row,'date'),book['epoch'],options.get('year'))),detail=text(raw_detail,True,10000),category=text(string(cell(row,'category')),maximum=160),handling=text(string(cell(row,'handling')),maximum=10000),source=source);target='errors'
                else:
                    period=excel_day(cell(row,'period'),book['epoch'],options.get('year')) or options.get('period')
                    if not period:raise AppError('Cần chọn kỳ báo cáo.')
                    data.update(period=monday(period),source=source);target='metrics'
                if 'classCode' in mapping and template!='cases':
                    cc=string(cell(row,'classCode'))
                    if cc:
                        cls=next((c for c in state['classes'] if fold(c['code'])==fold(cc)),None)
                        if not cls:raise AppError('Chưa có mã lớp '+cc+'; hãy tạo lớp trước.')
                        if cls['teacher']!=tid:raise AppError('Giáo viên/lớp không khớp.')
                        data['classId']=cls['id']
                identity=string(cell(row,'sourceId')) or (data['code']+':'+data.get('start','') if template=='cases' else digest({k:v for k,v in data.items() if k in ('teacher','title','date','time')}) if template=='tasks' else digest({k:v for k,v in data.items() if k not in ('handling','category','source')}))
                key=template+':'+digest([source,identity]);data['importKey']=key
                if old is None:old=next((r for r in state[target] if r.get('importKey')==key),None)
            if key in seen:raise AppError('Trùng khóa nghiệp vụ trong cùng file; cần kiểm tra dòng thay vì tự xóa trùng.',400,'REVIEW')
            seen.add(key)
            if template=='metrics':
                metrics=[];observation=string(cell(row,'sourceId')) or 'summary'
                for k in KINDS:
                    n=cell(row,k+'_n');d=cell(row,k+'_d');pct=cell(row,k+'_pct')
                    if n in (None,'') and d in (None,'') and pct in (None,''):continue
                    n=number(n,optional=True);d=number(d,optional=True)
                    if (n is None)!=(d is None) or (n is not None and n>d):raise AppError('Cặp tử số/mẫu số không hợp lệ.')
                    if pct not in (None,''):
                        if isinstance(pct,str) and pct.strip().endswith('%'):pct=number(pct.strip()[:-1],0,100)
                        else:
                            if options.get('percentUnit') not in ('0-1','0-100'):raise AppError('Chọn đơn vị cho cột phần trăm nguồn.')
                            pct=number(pct,0,1 if options['percentUnit']=='0-1' else 100)*(100 if options['percentUnit']=='0-1' else 1)
                    else:pct=None
                    metric={**data,'kind':k,'numerator':n,'denominator':d,'sourcePercent':pct,'observationId':observation,'importKey':key+':'+k}
                    existing=next((x for x in state['metrics'] if (x['teacher'],x.get('classId',''),x['period'],x['kind'],x.get('observationId','summary'))==(tid,data.get('classId',''),data['period'],k,observation)),None)
                    metrics.append({'data':metric,'old':existing})
                if not metrics:item.update(status='skipped',message='Không có số liệu; ô trống giữ là thiếu dữ liệu.')
                for m in metrics:
                    if m['old']:
                        m['data']['id']=m['old']['id']
                        if policy=='skip':m['skip']=True
                        elif all(m['old'].get(k)==v for k,v in m['data'].items() if k!='importKey'):m['skip']=True
                        elif policy=='fill':raise AppError('Chỉ số đã tồn tại; cần đối chiếu rồi chọn ghi đè.',400,'REVIEW')
                item['metrics']=metrics
                if metrics and all(x.get('skip') for x in metrics):item.update(status='duplicate',message='Quan sát đã tồn tại.')
                elif metrics and all(x['old'] is not None for x in metrics):item['status']='update'
            elif old:
                changes=[k for k,v in data.items() if k!='importKey' and v not in ('',None) and old.get(k)!=v]
                item['changes']=changes
                if not changes:item.update(status='duplicate',message='Không có thay đổi.')
                elif policy=='skip':item.update(status='skipped',message='Bỏ qua bản ghi đã tồn tại.')
                elif policy=='fill':
                    conflicts=[k for k in changes if old.get(k) not in ('',None)]
                    if conflicts:raise AppError('Xung đột trường: '+', '.join(conflicts)+'. Chọn ghi đè sau khi đối chiếu.',400,'REVIEW')
                    data={**old,**{k:v for k,v in data.items() if old.get(k) in ('',None)}};item['status']='update'
                else:data={**old,**data};item['status']='update'
                data['id']=old['id']
            if template=='teachers':
                alias_code=string(cell(row,'alias'))
                if alias_code:
                    known=next((a for a in state['aliases'] if a['alias_key']==fold(source)+'|'+fold(alias_code)),None)
                    if known and (not old or known['teacher']!=old['id']):raise AppError('Mã alias thuộc giáo viên khác.',400,'REVIEW')
                    if old and not known and item['status']=='duplicate':item['status']='update'
            if alias_code:
                text(alias_code,True,80);text(source,True,180)
            item.update(data=data,target=target,key=key,teacher=tid,aliasCode=alias_code,summary=(data.get('name') or data.get('title') or data.get('code') or data.get('detail') or (find(state,'teachers',tid)['name'] if tid else ''))[:160])
        except AppError as e:item.update(status='review' if e.code=='REVIEW' else 'error',message=str(e))
        items.append(item)
    fingerprint=digest([book['sha256'],sheet_name,header,template,mapping,options]);prior=next((b for b in state['importBatches'] if b['fingerprint']==fingerprint),None)
    return {'fingerprint':fingerprint,'filename':book['filename'],'source':source,'template':template,'sheet':sheet_name,'header':header,'items':items,'unresolved':list(unresolved.values()),'counts':{k:sum(x['status']==k for x in items) for k in ('create','update','duplicate','skipped','review','error')},'previousBatch':prior['id'] if prior else None,'revision':state['_revision'],'missingCache':book['missingCache']}

def apply_plan(service,state,plan,clock,allow_partial):
    previous=next((b for b in state['importBatches'] if b['fingerprint']==plan['fingerprint']),None)
    if previous:return {'batchId':previous['id'],'replayed':True}
    excluded=[x for x in plan['items'] if x['status'] in ('error','review')]
    if excluded and not allow_partial:raise AppError('Còn dòng lỗi/chờ xác minh. Chưa nhập dữ liệu; hãy sửa hoặc xác nhận nhập riêng các dòng hợp lệ.')
    added=0
    command={'teachers':'teacher_upsert','tasks':'task_upsert','cases':'process_upsert','qc':'error_upsert'}
    for item in plan['items']:
        if item['status'] not in ('create','update'):continue
        if plan['template']=='metrics':
            for m in item.get('metrics',[]):
                if m.get('skip'):continue
                r=service.cmd_metric_upsert(state,m['data'],clock);find(state,'metrics',r['id']).update(importKey=m['data']['importKey'],provenance={'sheet':plan['sheet'],'row':item['row'],'file':plan['filename']});added+=1
        else:
            result=getattr(service,'cmd_'+command[plan['template']])(state,item['data'],clock)
            find(state,item['target'],result['id']).update(importKey=item['key'],provenance={'sheet':plan['sheet'],'row':item['row'],'file':plan['filename']});added+=1
        if item.get('aliasCode'):service.cmd_teacher_alias(state,{'teacher':result['id'] if plan['template']=='teachers' else item['teacher'],'source':plan['source'],'code':item['aliasCode']},clock)
    batch={'id':uid(),'fingerprint':plan['fingerprint'],'filename':plan['filename'],'sheet':plan['sheet'],'template':plan['template'],'counts':plan['counts'],'applied':added,'excluded':[{'row':x['row'],'status':x['status'],'message':x['message']} for x in excluded],'stamp':clock.stamp()}
    state['importBatches'].append(batch);state['sources'].append({'id':uid(),'name':plan['source'],'file':plan['filename'],'type':'File local','status':'imported','batchId':batch['id'],'created':clock.stamp()});return {'batchId':batch['id'],'applied':added}
