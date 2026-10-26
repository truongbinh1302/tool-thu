"""SQLite snapshots with relational constraints, optimistic writes and consistent backups."""
import sqlite3, threading, json, io, zipfile, hashlib
from pathlib import Path
from .common import AppError, canonical, digest, empty_state, demo_state, uid
VERSION=2; APP_ID=0x54485531
TABLES=('teachers','classes','aliases','meetings','templates','sources','tasks','processes','events','metrics','errors','importBatches','reports')
class Store:
    def __init__(self,directory,mode):
        self.mode=mode;self.directory=Path(directory);self.directory.mkdir(parents=True,exist_ok=True)
        self.path=self.directory/(mode+'.sqlite3');self.lock=threading.RLock();self.migrate()
    def connect(self):
        c=sqlite3.connect(self.path,timeout=3,isolation_level=None);c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA trusted_schema=OFF');return c
    def migrate(self):
        c=self.connect()
        try:
            version=c.execute('PRAGMA user_version').fetchone()[0]
            app=c.execute('PRAGMA application_id').fetchone()[0]
            if version>VERSION or app not in (0,APP_ID):raise AppError('Phiên bản dữ liệu không tương thích.',409)
            if version==1:
                dst=sqlite3.connect(self.directory/(self.mode+'-before-v2.sqlite3'));c.backup(dst);dst.close()
            c.execute('BEGIN IMMEDIATE')
            if version==0:
                c.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
                c.execute('CREATE TABLE preferences(key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
                for table in TABLES:
                    cols=''
                    if table=='teachers':cols=', code TEXT UNIQUE NOT NULL'
                    if table=='classes':cols=', code TEXT UNIQUE NOT NULL, teacher TEXT REFERENCES teachers(id)'
                    if table=='aliases':cols=', alias_key TEXT UNIQUE NOT NULL, teacher TEXT NOT NULL REFERENCES teachers(id)'
                    if table in ('tasks','processes','metrics','errors'):cols=', teacher TEXT REFERENCES teachers(id), class_id TEXT REFERENCES classes(id)'
                    if table=='tasks':cols+=', meeting_id TEXT REFERENCES meetings(id)'
                    if table=='events':cols=', source_key TEXT UNIQUE, meeting_id TEXT REFERENCES meetings(id)'
                    if table=='reports':cols=', period TEXT, version INTEGER, UNIQUE(period,version)'
                    if table=='importBatches':cols=', fingerprint TEXT UNIQUE'
                    c.execute(f'CREATE TABLE {table}(id TEXT PRIMARY KEY,payload TEXT NOT NULL{cols})')
                c.execute('CREATE TABLE attendance(meeting_id TEXT REFERENCES meetings(id),teacher_id TEXT REFERENCES teachers(id),status TEXT NOT NULL,PRIMARY KEY(meeting_id,teacher_id))')
                c.execute('CREATE TABLE audit(stamp TEXT,revision INTEGER,action TEXT)')
                c.execute('INSERT INTO meta VALUES(?,?)',('revision','0'))
                self._write(c,demo_state() if self.mode=='demo' else empty_state())
            if version<2:c.execute('CREATE TABLE requests(id TEXT PRIMARY KEY,digest TEXT NOT NULL,revision INTEGER NOT NULL)')
            c.execute(f'PRAGMA application_id={APP_ID}');c.execute(f'PRAGMA user_version={VERSION}');c.commit()
        except: c.rollback();raise
        finally:c.close()
    def _read(self,c):
        s=empty_state()
        for t in TABLES:s[t]=[json.loads(r[0]) for r in c.execute(f'SELECT payload FROM {t} ORDER BY rowid')]
        for k,v in c.execute('SELECT key,payload FROM preferences'):s[k]=json.loads(v)
        s['_revision']=int(c.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0]);return s
    def read(self):
        with self.lock:
            c=self.connect()
            try:
                c.execute('BEGIN');s=self._read(c);c.commit();return s
            finally:c.close()
    def _write(self,c,s):
        c.execute('DELETE FROM attendance')
        for t in reversed(TABLES):c.execute(f'DELETE FROM {t}')
        for t in TABLES:
            for r in s[t]:
                fields={'id':r['id'],'payload':canonical(r)}
                if t in ('teachers','classes'):fields['code']=r['code']
                if t in ('classes','aliases','tasks','processes','metrics','errors'):fields['teacher']=r.get('teacher') or None
                if t=='aliases':fields['alias_key']=r['alias_key']
                if t in ('tasks','processes','metrics','errors'):fields['class_id']=r.get('classId') or None
                if t in ('tasks','events'):fields['meeting_id']=r.get('meetingId') or None
                if t=='events':fields['source_key']=r.get('sourceKey') or None
                if t=='reports':fields.update(period=r['period'],version=r['version'])
                if t=='importBatches':fields['fingerprint']=r['fingerprint']
                c.execute(f"INSERT INTO {t} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",list(fields.values()))
        for m in s['meetings']:
            for tid in m.get('invited',[]):c.execute('INSERT INTO attendance VALUES(?,?,?)',(m['id'],tid,m.get('attendees',{}).get(tid,'pending')))
        c.execute('DELETE FROM preferences')
        for k,v in s.items():
            if k not in TABLES and not k.startswith('_'):c.execute('INSERT INTO preferences VALUES(?,?)',(k,canonical(v)))
    def request_seen(self,request_id,action,payload):
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100:raise AppError('Thiếu mã thao tác an toàn.')
        c=self.connect()
        try:row=c.execute('SELECT digest FROM requests WHERE id=?',(request_id,)).fetchone()
        finally:c.close()
        if row and row[0]!=digest([action,payload]):raise AppError('Mã thao tác đã dùng cho nội dung khác.',409,'IDEMPOTENCY')
        return row is not None
    def mutate(self,expected,request_id,action,payload,fn,stamp):
        if not isinstance(request_id,str) or not 8<=len(request_id)<=100:raise AppError('Thiếu mã thao tác an toàn.')
        signature=digest([action,payload])
        with self.lock:
            c=self.connect()
            try:
                c.execute('BEGIN IMMEDIATE');prev=c.execute('SELECT digest FROM requests WHERE id=?',(request_id,)).fetchone()
                if prev:
                    if prev[0]!=signature:raise AppError('Mã thao tác đã dùng cho nội dung khác.',409,'IDEMPOTENCY')
                    s=self._read(c);c.commit();return s,{'replayed':True}
                s=self._read(c)
                if type(expected)!=int or expected!=s['_revision']:raise AppError('Dữ liệu đã thay đổi. Bản mới đã được tải; hãy kiểm tra rồi lưu lại.',409,'STALE')
                result=fn(s);self._write(c,s);rev=expected+1
                c.execute("UPDATE meta SET value=? WHERE key='revision'",(str(rev),));c.execute('INSERT INTO requests VALUES(?,?,?)',(request_id,signature,rev));c.execute('INSERT INTO audit VALUES(?,?,?)',(stamp,rev,action));c.commit();s['_revision']=rev;return s,result
            except sqlite3.IntegrityError: c.rollback();raise AppError('Mã bị trùng hoặc liên kết dữ liệu không hợp lệ; chưa có thay đổi nào được lưu.',409,'CONSTRAINT')
            except: c.rollback();raise
            finally:c.close()
    def audit(self):
        c=self.connect()
        try:return [dict(zip(('stamp','revision','action'),r)) for r in c.execute('SELECT stamp,revision,action FROM audit ORDER BY rowid DESC LIMIT 100')]
        finally:c.close()
    def backup(self):
        with self.lock:
            src=self.connect();out=sqlite3.connect(':memory:')
            try:src.backup(out);raw=out.serialize()
            finally:src.close();out.close()
            manifest={'app':'tool-thu','schema':VERSION,'mode':self.mode,'sha256':hashlib.sha256(raw).hexdigest()}
            buf=io.BytesIO()
            with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('manifest.json',canonical(manifest));z.writestr('data.sqlite3',raw)
            return buf.getvalue()
    def inspect_backup(self,raw):
        if len(raw)>30*1024*1024:raise AppError('Bản sao lưu quá lớn.')
        try:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                if set(z.namelist())!={'manifest.json','data.sqlite3'} or sum(i.file_size for i in z.infolist())>100*1024*1024:raise ValueError()
                m=json.loads(z.read('manifest.json'));db=z.read('data.sqlite3')
            if m['app']!='tool-thu' or m['mode']!=self.mode or m['schema']!=VERSION or m['sha256']!=hashlib.sha256(db).hexdigest():raise ValueError()
            c=sqlite3.connect(':memory:');c.deserialize(db)
            try:
                c.execute('PRAGMA trusted_schema=OFF')
                if c.execute('PRAGMA application_id').fetchone()[0]!=APP_ID or c.execute('PRAGMA user_version').fetchone()[0]!=VERSION or c.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError()
                s=self._read(c)
            finally:c.close()
            return m,s
        except Exception:raise AppError('Bản sao lưu hỏng, khác chế độ hoặc không tương thích. Dữ liệu hiện tại được giữ nguyên.')
    def restore(self,raw,expected,request_id,stamp):
        m,s=self.inspect_backup(raw)
        with self.lock:
            c=self.connect()
            try:replay=c.execute('SELECT 1 FROM requests WHERE id=?',(request_id,)).fetchone() is not None
            finally:c.close()
            if not replay and self.read()['_revision']!=expected:raise AppError('Dữ liệu đã thay đổi. Hãy xem trước bản khôi phục lại.',409,'STALE')
            backup_path=self.directory/f'{self.mode}-before-restore-{uid()}.thubackup';backup_path.write_bytes(self.backup())
            def apply(current):
                revision=current['_revision'];current.clear();current.update(s);current['_revision']=revision
                return {'beforeBackup':str(backup_path)}
            return self.mutate(expected,request_id,'backup.restore',{'sha256':m['sha256']},apply,stamp)
