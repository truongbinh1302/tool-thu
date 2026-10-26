"""Read-only Google Sheets access for an installed (desktop) OAuth client.

Network calls happen only when the user acts: connect, read a sheet, or press
"Cập nhật dữ liệu". Tokens live in the data folder (not SQLite, not backups).
"""
import base64
import hashlib
import json
import os
import re
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .common import AppError

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'
REVOKE_URL = 'https://oauth2.googleapis.com/revoke'
USERINFO_URL = 'https://openidconnect.googleapis.com/v1/userinfo'
SHEETS_URL = 'https://sheets.googleapis.com/v4/spreadsheets/'
SCOPES = 'openid email https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_FILE = 'google-client.json'
TOKEN_FILE = 'google-token.json'
PENDING_TTL = 600


def _write_private(path, payload):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, path)


def https_opener():
    """HTTPS opener that also works inside the packaged Mac app (bundled certifi CA list)."""
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=context))


def check_network():
    """Used by the build smoke test: can this runtime verify Google's TLS certificate?"""
    with https_opener().open('https://www.googleapis.com/discovery/v1/apis?name=sheets&preferred=true', timeout=20) as r:
        return r.status


def spreadsheet_id(link):
    link = (link or '').strip()
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]{20,})', link)
    if m:
        return m.group(1)
    if re.fullmatch(r'[a-zA-Z0-9_-]{20,}', link):
        return link
    raise AppError('Link Google Sheet không hợp lệ. Hãy dán link dạng https://docs.google.com/spreadsheets/d/…')


class GoogleClient:
    def __init__(self, directory, opener=None, clock=time.time):
        self.directory = Path(directory)
        self.opener = opener or https_opener()
        self.clock = clock
        self.pending = {}
        self.read_count = 0

    # ---------- files ----------
    @property
    def client_path(self):
        return self.directory / CLIENT_FILE

    @property
    def token_path(self):
        return self.directory / TOKEN_FILE

    def _client(self):
        try:
            data = json.loads(self.client_path.read_text(encoding='utf-8'))
            return data['client_id'], data.get('client_secret', '')
        except (OSError, ValueError, KeyError):
            raise AppError('Chưa có thông tin ứng dụng Google (OAuth client). Hãy chọn file JSON tải từ Google Cloud.', 409, 'GOOGLE_CLIENT')

    def _token(self):
        try:
            return json.loads(self.token_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None

    def status(self):
        token = self._token()
        return {'configured': self.client_path.exists(), 'connected': bool(token and token.get('refresh_token')),
                'email': (token or {}).get('email', ''), 'connectedAt': (token or {}).get('connectedAt', '')}

    def save_client(self, raw_json):
        try:
            data = json.loads(raw_json)
        except ValueError:
            raise AppError('File JSON không hợp lệ.')
        inner = data.get('installed') or data.get('web') or data
        if not isinstance(inner, dict) or not str(inner.get('client_id', '')).endswith('.apps.googleusercontent.com'):
            raise AppError('Đây không phải file OAuth client của Google (cần loại "Desktop app").')
        if 'web' in data:
            raise AppError('Cần OAuth client loại "Desktop app", không phải "Web application".')
        _write_private(self.client_path, {'client_id': inner['client_id'], 'client_secret': inner.get('client_secret', '')})
        return self.status()

    # ---------- HTTP ----------
    def _request(self, url, data=None, headers=None, timeout=20):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers or {})
        try:
            with self.opener.open(req, timeout=timeout) as r:
                raw = r.read()
                return r.status, json.loads(raw or b'{}')
        except urllib.error.HTTPError as e:
            try:
                payload = json.loads(e.read() or b'{}')
            except ValueError:
                payload = {}
            return e.code, payload
        except (urllib.error.URLError, TimeoutError, OSError):
            raise AppError('Không kết nối được tới Google. Kiểm tra mạng rồi bấm thử lại; dữ liệu đã lưu được giữ nguyên.', 503, 'SOURCE_OFFLINE')

    # ---------- OAuth ----------
    def start(self, redirect_uri):
        client_id, _ = self._client()
        now = self.clock()
        self.pending = {k: v for k, v in self.pending.items() if now - v['time'] < PENDING_TTL}
        verifier = secrets.token_urlsafe(64)[:96]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        state = secrets.token_urlsafe(24)
        self.pending[state] = {'verifier': verifier, 'redirect': redirect_uri, 'time': now}
        query = {'client_id': client_id, 'redirect_uri': redirect_uri, 'response_type': 'code', 'scope': SCOPES,
                 'code_challenge': challenge, 'code_challenge_method': 'S256', 'state': state,
                 'access_type': 'offline', 'prompt': 'consent'}
        return AUTH_URL + '?' + urllib.parse.urlencode(query)

    def is_pending(self, state):
        p = self.pending.get(state or '')
        return bool(p and self.clock() - p['time'] < PENDING_TTL)

    def finish(self, state, code, error=None):
        pending = self.pending.pop(state or '', None)
        if not pending or self.clock() - pending['time'] >= PENDING_TTL:
            raise AppError('Phiên đăng nhập Google đã hết hạn. Hãy bấm Kết nối Google lại.', 409, 'GOOGLE_STATE')
        if error:
            raise AppError('Bạn chưa cho phép quyền đọc Google Sheets nên chưa kết nối.', 403, 'GOOGLE_DENIED')
        client_id, client_secret = self._client()
        status, token = self._request(TOKEN_URL, {'client_id': client_id, 'client_secret': client_secret, 'code': code,
                                                  'code_verifier': pending['verifier'], 'grant_type': 'authorization_code',
                                                  'redirect_uri': pending['redirect']})
        if status != 200 or 'access_token' not in token:
            raise AppError('Google không cấp quyền truy cập (' + str(token.get('error', status)) + ').', 502, 'GOOGLE_TOKEN')
        if 'spreadsheets.readonly' not in token.get('scope', ''):
            raise AppError('Cần tick quyền "Xem bảng tính Google Sheets" khi đăng nhập. Hãy kết nối lại.', 403, 'GOOGLE_SCOPE')
        old = self._token() or {}
        record = {'access_token': token['access_token'], 'expires_at': self.clock() + int(token.get('expires_in', 3600)) - 60,
                  'refresh_token': token.get('refresh_token') or old.get('refresh_token', ''),
                  'connectedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        s, info = self._request(USERINFO_URL, headers={'Authorization': 'Bearer ' + token['access_token']})
        record['email'] = info.get('email', '') if s == 200 else ''
        _write_private(self.token_path, record)
        return self.status()

    def _access_token(self, force=False):
        token = self._token()
        if not token or not token.get('refresh_token'):
            raise AppError('Chưa kết nối Google. Hãy bấm Kết nối Google và đăng nhập.', 409, 'GOOGLE_LOGIN')
        if not force and token.get('access_token') and token.get('expires_at', 0) > self.clock():
            return token['access_token']
        client_id, client_secret = self._client()
        status, fresh = self._request(TOKEN_URL, {'client_id': client_id, 'client_secret': client_secret,
                                                  'refresh_token': token['refresh_token'], 'grant_type': 'refresh_token'})
        if status != 200 or 'access_token' not in fresh:
            raise AppError('Phiên đăng nhập Google đã hết hạn hoặc bị thu hồi. Hãy bấm Kết nối Google lại.', 401, 'GOOGLE_LOGIN')
        token.update(access_token=fresh['access_token'], expires_at=self.clock() + int(fresh.get('expires_in', 3600)) - 60)
        _write_private(self.token_path, token)
        return token['access_token']

    def disconnect(self):
        token = self._token()
        if token and token.get('refresh_token'):
            try:
                self._request(REVOKE_URL, {'token': token['refresh_token']}, timeout=10)
            except AppError:
                pass
        self.token_path.unlink(missing_ok=True)
        return self.status()

    # ---------- Sheets ----------
    def _get(self, url):
        """GET with one token refresh on 401 and bounded retries on 429/5xx (same user action)."""
        refreshed = False
        for attempt in range(3):
            status, payload = self._request(url, headers={'Authorization': 'Bearer ' + self._access_token(force=refreshed)})
            if status == 200:
                return payload
            if status == 401 and not refreshed:
                refreshed = True
                continue
            if status in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            if status in (403, 404):
                raise AppError('Tài khoản Google đang kết nối không có quyền xem sheet này, hoặc link không tồn tại. '
                               'Với sheet lấy dữ liệu từ file khác (IMPORTRANGE), tài khoản cũng cần quyền xem file gốc.', 403, 'SOURCE_DENIED')
            if status == 401:
                raise AppError('Phiên đăng nhập Google đã hết hạn. Hãy bấm Kết nối Google lại.', 401, 'GOOGLE_LOGIN')
            raise AppError('Google Sheets đang lỗi (' + str(status) + '). Bấm thử lại sau; dữ liệu đã lưu được giữ nguyên.', 503, 'SOURCE_ERROR')

    def read_book(self, link, tabs=None):
        """Read a spreadsheet as an importer 'book' (same shape as importer.read_workbook)."""
        sid = spreadsheet_id(link)
        self.read_count += 1
        meta = self._get(SHEETS_URL + sid + '?fields=properties.title,sheets.properties(title,hidden)')
        names = [s['properties']['title'] for s in meta.get('sheets', [])]
        if tabs:
            missing = [t for t in tabs if t not in names]
            if missing:
                raise AppError('Sheet "' + missing[0] + '" không còn trong bảng tính (có thể đã đổi tên). Dữ liệu cũ được giữ nguyên.', 409, 'SOURCE_SCHEMA')
            names = list(tabs)
        if not names:
            raise AppError('Bảng tính không có sheet nào.')
        query = [('ranges', "'" + n.replace("'", "''") + "'") for n in names[:30]]
        query += [('valueRenderOption', 'UNFORMATTED_VALUE'), ('dateTimeRenderOption', 'SERIAL_NUMBER'), ('majorDimension', 'ROWS')]
        values = self._get(SHEETS_URL + sid + '/values:batchGet?' + urllib.parse.urlencode(query))
        sheets = []
        total = 0
        for name, block in zip(names, values.get('valueRanges', [])):
            rows, numbers = [], []
            for i, row in enumerate(block.get('values', []), start=1):
                cleaned = [None if v == '' else (int(v) if isinstance(v, float) and v.is_integer() else v) for v in row[:256]]
                while cleaned and cleaned[-1] is None:
                    cleaned.pop()
                if any(v is not None for v in cleaned):
                    rows.append(cleaned)
                    numbers.append(i)
                    total += len(cleaned)
            if len(rows) > 50000 or total > 500000:
                raise AppError('Bảng tính quá lớn để đọc một lần. Hãy chọn sheet cụ thể.')
            sheets.append({'name': name, 'rows': rows, 'rowNumbers': numbers, 'warnings': []})
        if not any(s['rows'] for s in sheets):
            raise AppError('Bảng tính không có dữ liệu để nhập.')
        from .importer import scrub_sheets  # late import: importer depends on service
        scrub_sheets(sheets)
        title = meta.get('properties', {}).get('title', 'Google Sheet')
        digest = hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return {'filename': title + ' (Google Sheets)', 'sha256': digest, 'epoch': '1900', 'missingCache': 0,
                'sheets': sheets, 'google': {'spreadsheetId': sid, 'title': title}}
