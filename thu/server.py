import base64,json,secrets,threading,time,mimetypes,sqlite3,hashlib,socketserver
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from urllib.parse import urlsplit,parse_qs,unquote
from pathlib import Path
from .common import *
from .service import Service,find
from .importer import read_workbook,columns,build_plan,apply_plan,FIELDS
from .calendar_service import calendar_ics,calendar_events
from .tracking import save_google_source
from .exporting import report_csv
from . import __version__
from .runtime import build_id
class LocalServer(ThreadingHTTPServer):
    daemon_threads=False
    def server_bind(self):
        # HTTPServer.server_bind calls socket.getfqdn(), a reverse-DNS lookup that can
        # stall for many seconds on macOS. Loopback needs no hostname.
        socketserver.TCPServer.server_bind(self)
        host,port=self.server_address[:2];self.server_name=host;self.server_port=port
    def __init__(self,address,directory,web):
        super().__init__(address,Handler)
        try:
            self.service=Service(directory);self.web=Path(web).resolve();self.build=build_id();self.session=secrets.token_urlsafe(32);self.csrf=secrets.token_urlsafe(32);self.previews={};self.preview_lock=threading.RLock();self.origin=f'http://127.0.0.1:{self.server_port}';self.instance=hashlib.sha256(str(Path(directory).resolve()).encode()).hexdigest()[:20]
        except BaseException:
            self.server_close();raise
    def hold(self,kind,mode,value):
        with self.preview_lock:
            now=time.monotonic();self.previews={k:v for k,v in self.previews.items() if now-v['time']<1200}
            if len(self.previews)>=12:raise AppError('Có quá nhiều bản xem trước. Đóng bảng nhập cũ rồi thử lại.',429)
            key=secrets.token_urlsafe(20);self.previews[key]={'kind':kind,'mode':mode,'value':value,'time':now};return key
    def held(self,key,kind,mode):
        with self.preview_lock:
            v=self.previews.get(key)
            if not v or v['kind']!=kind or v['mode']!=mode or time.monotonic()-v['time']>1200:raise AppError('Bản xem trước đã hết hạn. Vui lòng mở file lại.',409,'EXPIRED')
            return v['value']
class Handler(BaseHTTPRequestHandler):
    server_version='ToolThu';sys_version=''
    def log_message(self,*args):pass
    def send(self,status,body,typ='application/json; charset=utf-8',cookie=False,filename=None,location=None):
        raw=canonical(body).encode() if typ.startswith('application/json') else body
        self.send_response(status);self.send_header('Content-Type',typ);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if cookie:self.send_header('Set-Cookie',f'thu_session={self.server.session}; HttpOnly; SameSite=Strict; Path=/')
        if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        if location:self.send_header('Location',location)
        self.end_headers();self.wfile.write(raw)
    def guard(self,write=False,auth=True):
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed:raise AppError('Host không được phép.',403)
        if auth:
            cookie=self.headers.get('Cookie','');parts=dict(x.strip().split('=',1) for x in cookie.split(';') if '=' in x)
            if not secrets.compare_digest(parts.get('thu_session',''),self.server.session):raise AppError('Phiên làm việc hết hạn. Tải lại trang.',401)
        if write:
            if self.headers.get('Origin')!=self.server.origin:raise AppError('Nguồn yêu cầu không được phép.',403)
            if not secrets.compare_digest(self.headers.get('X-Tool-CSRF',''),self.server.csrf):raise AppError('Thiếu xác thực thao tác local. Tải lại trang.',403)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise AppError('Nội dung cần ở định dạng JSON.',415)
        mode=self.headers.get('X-Tool-Mode','demo')
        if mode not in ('demo','real'):raise AppError('Chế độ dữ liệu không hợp lệ.')
        return mode
    def run_safe(self,fn):
        try:fn()
        except AppError as e:self.send(e.status,{'error':str(e),'code':e.code})
        except sqlite3.OperationalError:self.send(503,{'error':'Kho dữ liệu đang bận hoặc không ghi được. Kiểm tra dung lượng/quyền thư mục rồi thử lại.','code':'DATABASE'})
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:
            print('Tool Thu: internal error '+type(e).__name__,flush=True)
            self.send(500,{'error':'Chưa hoàn tất thao tác. Dữ liệu chưa được xác nhận lưu; hãy tải lại và kiểm tra.','code':'INTERNAL'})
    def do_GET(self):self.run_safe(self.get)
    def get(self):
        path=urlsplit(self.path).path;q=parse_qs(urlsplit(self.path).query);self.guard(auth=False)
        if path=='/api/health':return self.send(200,{'app':'tool-thu-local','version':__version__,'build':self.server.build,'instance':self.server.instance})
        if path=='/api/bootstrap':
            mode=self.guard(auth=False);return self.send(200,{'version':__version__,'csrf':self.server.csrf,'state':self.server.service.snapshot(mode)},cookie=True)
        if path.startswith('/api/'):
            mode=self.guard();store=self.server.service.stores[mode]
            if path=='/api/state':return self.send(200,{'state':self.server.service.snapshot(mode,q.get('period',[None])[0])})
            if path=='/api/audit':return self.send(200,{'items':store.audit()})
            if path=='/api/report.csv':
                s=store.read();snapshot=q.get('snapshot',[''])[0]
                r=find(s,'reports',snapshot) if snapshot else self.server.service.snapshot(mode,q.get('period',[None])[0])['_report']
                return self.send(200,report_csv(r),'text/csv; charset=utf-8',filename='tool-thu-report.csv')
            if path=='/api/calendar.ics':
                events=calendar_events(store.read());eid=q.get('event',[''])[0]
                if eid:events=[e for e in events if e['id']==eid]
                return self.send(200,calendar_ics(events),'text/calendar; charset=utf-8',filename='tool-thu-calendar.ics')
            if path.startswith('/api/download/'):
                name=path.rsplit('/',1)[-1]
                if not name.startswith(mode+'-') or not name.endswith('.thubackup') or '/' in name or '..' in name:raise AppError('Tệp không hợp lệ.',404)
                dest=store.directory/name
                if not dest.is_file():raise AppError('Tệp không còn tồn tại.',404)
                return self.send(200,dest.read_bytes(),'application/octet-stream',filename=name)
            raise AppError('Không tìm thấy API.',404)
        if path=='/' and 'state' in q and ('code' in q or 'error' in q):return self.google_callback(q)
        requested=unquote(path).lstrip('/') or 'index.html';dest=(self.server.web/requested).resolve()
        if not dest.is_relative_to(self.server.web) or not dest.is_file():raise AppError('Không tìm thấy tài nguyên.',404)
        return self.send(200,dest.read_bytes(),mimetypes.guess_type(dest.name)[0] or 'application/octet-stream')
    def google_callback(self,q):
        state=q.get('state',[''])[0]
        if not self.server.service.google.is_pending(state):
            return self.send(302,b'',typ='text/html; charset=utf-8',location='/#sources')
        try:
            info=self.server.service.google.finish(state,q.get('code',[''])[0],q.get('error',[None])[0]);ok=True
            message='Đã kết nối Google'+((' với '+info['email']) if info.get('email') else '')+'. Đang quay lại Tool Thư…'
        except AppError as e:ok=False;message=str(e)
        import html
        page=('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="2;url=/#sources"><title>Tool Thư</title>'
              '<body style="font-family:system-ui,sans-serif;background:#fbf2f6;color:#4a3640;display:grid;place-items:center;height:100vh;margin:0">'
              '<div style="background:#fff;padding:32px 40px;border-radius:20px;max-width:460px;text-align:center"><h2>'+('✿ Kết nối thành công' if ok else 'Chưa kết nối được')+'</h2>'
              '<p>'+html.escape(message)+'</p><p><a href="/#sources" style="color:#b0507a">Quay lại Tool Thư</a></p></div></body>')
        return self.send(200 if ok else 400,page.encode('utf-8'),'text/html; charset=utf-8')
    def do_POST(self):self.run_safe(self.post)
    def body(self):
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:raise AppError('Kích thước yêu cầu không hợp lệ.')
        if not 0<n<=30*1024*1024:raise AppError('Yêu cầu rỗng hoặc quá lớn.',413)
        try:b=json.loads(self.rfile.read(n))
        except (json.JSONDecodeError,UnicodeDecodeError):raise AppError('JSON không hợp lệ.')
        if not isinstance(b,dict):raise AppError('Nội dung yêu cầu không hợp lệ.')
        return b
    def decode(self,b):
        try:raw=base64.b64decode(b.get('base64',''),validate=True)
        except (ValueError,TypeError):raise AppError('Dữ liệu file không hợp lệ.')
        if len(raw)>20*1024*1024:raise AppError('File vượt 20 MB.')
        return raw
    def discard_rejected_body(self):
        # Windows can reset a socket closed with an unread POST body, hiding
        # the intended 401/403 response. Drain only bounded bytes/time, without
        # parsing them or relaxing any authorization check.
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:return
        if not 0<n<=30*1024*1024:return
        previous_timeout=self.connection.gettimeout();deadline=time.monotonic()+2
        try:
            while n:
                remaining=deadline-time.monotonic()
                if remaining<=0:break
                self.connection.settimeout(remaining)
                chunk=self.rfile.read1(min(n,65536))
                if not chunk:break
                n-=len(chunk)
        except OSError:pass
        finally:self.connection.settimeout(previous_timeout)
    def post(self):
        try:mode=self.guard(write=True)
        except AppError:
            self.discard_rejected_body();raise
        b=self.body();path=urlsplit(self.path).path;service=self.server.service;store=service.stores[mode];clock=Clock(mode)
        if path=='/api/group/setup':return self.send(200,service.group_setup(mode,b.get('revision'),b.get('requestId'),b.get('links')))
        if path=='/api/tracking/run':return self.send(200,service.track(mode,b.get('revision'),b.get('requestId'),b.get('sourceIds')))
        if path=='/api/commands':return self.send(200,service.command(mode,b.get('revision'),b.get('requestId'),text(b.get('name'),True,80),b.get('payload',{})))
        if path=='/api/backup':
            name=mode+'-'+uid()+'.thubackup';(store.directory/name).write_bytes(store.backup());return self.send(200,{'filename':name})
        if path=='/api/restore/preview':
            raw=self.decode(b);manifest,s=store.inspect_backup(raw);key=self.server.hold('restore',mode,{'raw':raw,'revision':store.read()['_revision']})
            return self.send(200,{'previewId':key,'manifest':manifest,'counts':{k:len(s[k]) for k in ('teachers','classes','tasks','processes','metrics','errors','meetings','events')}})
        if path=='/api/restore/commit':
            if b.get('confirmed') is not True:raise AppError('Cần xác nhận khôi phục.')
            preview=self.server.held(b.get('previewId'),'restore',mode);s,result=store.restore(preview['raw'],preview['revision'],b.get('requestId'),clock.stamp());return self.send(200,{'state':service.decorate(s,mode),'result':result})
        if path=='/api/preview/discard':
            with self.server.preview_lock:
                for key in b.get('ids',[]):
                    if key in self.server.previews and self.server.previews[key]['mode']==mode:self.server.previews.pop(key)
            return self.send(200,{'ok':True})
        if path=='/api/import/open':
            book=read_workbook(self.decode(b),b.get('filename'));key=self.server.hold('workbook',mode,book)
            return self.send(200,{'uploadId':key,'filename':book['filename'],'missingCache':book['missingCache'],'templates':FIELDS,'sheets':[{'name':s['name'],'rows':len(s['rows']),'suggestedHeader':s['suggestedHeader'],'warnings':s['warnings']} for s in book['sheets']]})
        if path in ('/api/import/columns','/api/import/plan'):
            book=self.server.held(b.get('uploadId'),'workbook',mode);header=number(b.get('header'),1,1000000,whole=True)
            if path.endswith('columns'):return self.send(200,columns(book,b.get('sheet'),header,b.get('template')))
            plan=build_plan(book,b.get('sheet'),header,b.get('template'),b.get('mapping'),b.get('options',{}),store.read(),clock)
            if book.get('google') and plan['template'] in ('teachers','tasks','cases','qc'):
                labels={c['index']:c['label'] for c in columns(book,plan['sheet'],header,plan['template'])['columns']}
                plan['_track']={**book['google'],'sheet':plan['sheet'],'header':header,'template':plan['template'],'mapping':b.get('mapping'),'options':{k:v for k,v in b.get('options',{}).items() if k!='policy'}|{'sourceName':plan['source']},'headerLabels':{str(v):labels.get(v,'') for v in b.get('mapping').values()}}
            key=self.server.hold('import',mode,plan)
            safe={k:v for k,v in plan.items() if k not in ('items','_track')};safe.update(previewId=key,trackable=bool(plan.get('_track')),items=[{k:v for k,v in i.items() if k not in ('data','metrics')} for i in plan['items'][:150]],truncated=len(plan['items'])>150)
            return self.send(200,safe)
        if path=='/api/import/commit':
            if b.get('confirmed') is not True:raise AppError('Cần xác nhận bản xem trước trước khi nhập.')
            plan=self.server.held(b.get('previewId'),'import',mode)
            # Consistent SQLite checkpoint before import, never raw-copy a live DB.
            name=mode+'-before-import-'+uid()+'.thubackup';(store.directory/name).write_bytes(store.backup())
            save=bool(b.get('saveSource')) and bool(plan.get('_track'))
            def run(s):
                result=apply_plan(service,s,plan,clock,bool(b.get('allowPartial')))
                if plan.get('_track') and not result.get('replayed') and s['sources']:s['sources'][-1]['type']='Google Sheets'
                if save:result['savedSource']=save_google_source(s,plan,clock)
                return result
            s,result=store.mutate(plan['revision'],b.get('requestId'),'import.commit',{'fingerprint':plan['fingerprint'],'partial':bool(b.get('allowPartial')),'saveSource':save},run,clock.stamp());return self.send(200,{'state':service.decorate(s,mode),'result':result})
        if path=='/api/google/client':
            return self.send(200,{'google':service.google.save_client(text(b.get('json'),True,20000))})
        if path=='/api/google/start':
            return self.send(200,{'url':service.google.start(f'http://127.0.0.1:{self.server.server_port}/')})
        if path=='/api/google/disconnect':
            return self.send(200,{'google':service.google.disconnect()})
        if path=='/api/import/google/open':
            book=service.google.read_book(text(b.get('link'),True,2000));key=self.server.hold('workbook',mode,book)
            return self.send(200,{'uploadId':key,'filename':book['filename'],'missingCache':0,'templates':FIELDS,'google':book['google'],'sheets':[{'name':s['name'],'rows':len(s['rows']),'suggestedHeader':s['suggestedHeader'],'warnings':s['warnings']} for s in book['sheets']]})
        if path=='/api/shutdown':
            self.send(200,{'ok':True});threading.Thread(target=self.server.shutdown,daemon=True).start();return
        raise AppError('Không tìm thấy API.',404)
