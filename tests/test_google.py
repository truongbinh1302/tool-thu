"""Google Sheets connection with a fake Google: OAuth/PKCE, refresh, errors, no reads without a user action."""
import base64
import hashlib
import http.cookiejar
import io
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from thu.common import AppError  # noqa: E402
from thu.google import GoogleClient, spreadsheet_id  # noqa: E402
from thu.server import LocalServer  # noqa: E402

SID = '1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789'
CLIENT = {'installed': {'client_id': '123-abc.apps.googleusercontent.com', 'client_secret': 'GOCSPX-test',
                        'redirect_uris': ['http://localhost']}}


class Resp(io.BytesIO):
    def __init__(self, status, payload):
        super().__init__(json.dumps(payload).encode())
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class FakeGoogle:
    """Answers like Google's endpoints; records every request."""

    def __init__(self):
        self.calls = []
        self.sheet_status = []  # queued statuses for the next Sheets calls
        self.token_ok = True
        self.offline = False
        self.access = 'access-1'

    def open(self, req, timeout=None):
        url = req.full_url
        body = urllib.parse.parse_qs(req.data.decode()) if req.data else {}
        self.calls.append((url, body, dict(req.header_items())))
        if self.offline:
            raise urllib.error.URLError('offline')
        if url.startswith('https://oauth2.googleapis.com/token'):
            if not self.token_ok:
                return self._err(400, {'error': 'invalid_grant'})
            if body.get('grant_type') == ['authorization_code']:
                return Resp(200, {'access_token': self.access, 'expires_in': 3599, 'refresh_token': 'refresh-1',
                                  'scope': 'openid https://www.googleapis.com/auth/spreadsheets.readonly email'})
            self.access = 'access-2'
            return Resp(200, {'access_token': self.access, 'expires_in': 3599})
        if url.startswith('https://openidconnect.googleapis.com'):
            return Resp(200, {'email': 'thu@example.com'})
        if url.startswith('https://oauth2.googleapis.com/revoke'):
            return Resp(200, {})
        if url.startswith('https://sheets.googleapis.com'):
            if self.sheet_status:
                status = self.sheet_status.pop(0)
                if status != 200:
                    return self._err(status, {'error': {'code': status}})
            auth = dict((k.lower(), v) for k, v in req.header_items()).get('authorization', '')
            if auth != 'Bearer ' + self.access:
                return self._err(401, {'error': {'code': 401}})
            if '/values:batchGet' in url:
                return Resp(200, {'valueRanges': [
                    {'range': "'Danh sách GV'!A1:Z3", 'values': [['STT', 'Họ và tên', 'Mã GV', 'Ngày'],
                                                                 ['C357', 'Trần Anh Thư', 2966661, 46023],
                                                                 ['C98', 'Nguyễn Thọ Tường Vy', 373476.0, '']]}]})
            return Resp(200, {'properties': {'title': 'Danh sách Giáo viên'},
                              'sheets': [{'properties': {'title': 'Danh sách GV'}}]})
        raise AssertionError('unexpected URL ' + url)

    @staticmethod
    def _err(status, payload):
        return urllib.error.HTTPError('https://x', status, 'err', {}, io.BytesIO(json.dumps(payload).encode()))


class GoogleClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.fake = FakeGoogle()
        self.g = GoogleClient(self.tmp.name, opener=self.fake)

    def tearDown(self):
        self.tmp.cleanup()

    def connect(self):
        self.g.save_client(json.dumps(CLIENT))
        url = self.g.start('http://127.0.0.1:28765/')
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        return self.g.finish(q['state'][0], 'auth-code'), q

    def test_client_file_validation(self):
        with self.assertRaises(AppError):
            self.g.save_client('{"web": {"client_id": "x.apps.googleusercontent.com"}}')
        with self.assertRaises(AppError):
            self.g.save_client('{"installed": {"client_id": "not-google"}}')
        self.assertTrue(self.g.save_client(json.dumps(CLIENT))['configured'])

    def test_oauth_uses_pkce_readonly_scope_and_stores_token_outside_db(self):
        info, q = self.connect()
        self.assertEqual(info, {'configured': True, 'connected': True, 'email': 'thu@example.com', 'connectedAt': info['connectedAt']})
        self.assertIn('spreadsheets.readonly', q['scope'][0])
        self.assertNotIn('spreadsheets ', q['scope'][0] + ' ')  # never full read/write scope
        self.assertEqual(q['code_challenge_method'], ['S256'])
        exchange = [b for u, b, h in self.fake.calls if b.get('grant_type') == ['authorization_code']][0]
        verifier = exchange['code_verifier'][0]
        expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        self.assertEqual(q['code_challenge'][0], expected)
        self.assertEqual(exchange['redirect_uri'], ['http://127.0.0.1:28765/'])
        self.assertTrue((Path(self.tmp.name) / 'google-token.json').exists())

    def test_state_is_single_use(self):
        self.connect()
        with self.assertRaises(AppError):
            self.g.finish('unknown', 'code')

    def test_read_book_shape_dates_and_numbers(self):
        self.connect()
        book = self.g.read_book('https://docs.google.com/spreadsheets/d/' + SID + '/edit#gid=0')
        sheet = book['sheets'][0]
        self.assertEqual(sheet['name'], 'Danh sách GV')
        self.assertEqual(sheet['rows'][1], ['C357', 'Trần Anh Thư', 2966661, 46023])
        self.assertEqual(sheet['rows'][2][2], 373476)  # float integers become ints
        self.assertEqual(book['google']['spreadsheetId'], SID)
        from thu.importer import excel_day
        self.assertEqual(excel_day(46023, book['epoch']), '2026-01-01')  # Sheets serial date

    def test_expired_access_token_refreshes_once(self):
        self.connect()
        self.fake.access = 'access-rotated'  # Google rejects the stored token
        with mock.patch('time.sleep'):
            self.fake.access = 'access-rotated'
            book = self.g.read_book(SID)
        self.assertTrue(book['sheets'])
        self.assertEqual(sum(1 for u, b, h in self.fake.calls if b.get('grant_type') == ['refresh_token']), 1)

    def test_revoked_refresh_token_asks_to_login_again(self):
        self.connect()
        self.fake.access = 'other'
        self.fake.token_ok = False
        with self.assertRaises(AppError) as e:
            self.g.read_book(SID)
        self.assertEqual(e.exception.code, 'GOOGLE_LOGIN')

    def test_permission_and_missing_sheet(self):
        self.connect()
        self.fake.sheet_status = [403]
        with self.assertRaises(AppError) as e:
            self.g.read_book(SID)
        self.assertEqual(e.exception.code, 'SOURCE_DENIED')
        with self.assertRaises(AppError) as e:
            self.g.read_book(SID, tabs=['Không có'])
        self.assertEqual(e.exception.code, 'SOURCE_SCHEMA')

    def test_rate_limit_retries_bounded(self):
        self.connect()
        with mock.patch('time.sleep') as slept:
            self.fake.sheet_status = [429, 503]
            self.assertTrue(self.g.read_book(SID)['sheets'])
            self.assertEqual(slept.call_count, 2)
            self.fake.sheet_status = [500, 500, 500]
            with self.assertRaises(AppError) as e:
                self.g.read_book(SID)
            self.assertEqual(e.exception.code, 'SOURCE_ERROR')

    def test_offline(self):
        self.connect()
        self.fake.offline = True
        with self.assertRaises(AppError) as e:
            self.g.read_book(SID)
        self.assertEqual(e.exception.code, 'SOURCE_OFFLINE')

    def test_disconnect_revokes_and_forgets(self):
        self.connect()
        self.assertFalse(self.g.disconnect()['connected'])
        self.assertTrue(any('revoke' in u for u, b, h in self.fake.calls))
        self.assertFalse((Path(self.tmp.name) / 'google-token.json').exists())

    def test_link_parsing(self):
        self.assertEqual(spreadsheet_id('https://docs.google.com/spreadsheets/d/' + SID + '/edit?usp=sharing'), SID)
        with self.assertRaises(AppError):
            spreadsheet_id('https://example.com/abc')


class GoogleHttpTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.server = LocalServer(('127.0.0.1', 0), self.tmp.name, ROOT / 'web')
        self.fake = FakeGoogle()
        self.server.service.google.opener = self.fake
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.jar = http.cookiejar.CookieJar()
        self.http = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(self.jar),
                                                NoRedirect())
        self.csrf = self.get('/api/bootstrap')['csrf']

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def get(self, path):
        with self.http.open(self.base + path, timeout=5) as r:
            return json.load(r)

    def post(self, path, body, mode='real'):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), headers={
            'Content-Type': 'application/json', 'Origin': self.base, 'X-Tool-CSRF': self.csrf, 'X-Tool-Mode': mode})
        try:
            with self.http.open(req, timeout=5) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_full_flow_and_no_google_calls_without_user_action(self):
        state = self.get('/api/bootstrap')['state']
        self.assertEqual(state['_google'], {'configured': False, 'connected': False, 'email': '', 'connectedAt': ''})
        self.get('/api/state')
        self.assertEqual(self.fake.calls, [], 'opening the app must not contact Google')

        status, r = self.post('/api/google/start', {})
        self.assertEqual((status, r['code']), (409, 'GOOGLE_CLIENT'))
        self.assertEqual(self.post('/api/google/client', {'json': json.dumps(CLIENT)})[0], 200)
        status, r = self.post('/api/google/start', {})
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(r['url']).query)
        self.assertEqual(q['redirect_uri'], [self.base + '/'])

        # Google redirects the browser back to the loopback root (no session cookie: SameSite=Strict).
        bare = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with bare.open(self.base + '/?state=' + q['state'][0] + '&code=xyz&scope=x', timeout=5) as page:
            html = page.read().decode()
        self.assertIn('Kết nối thành công', html)
        self.assertIn('thu@example.com', html)
        self.assertTrue(self.get('/api/state')['state']['_google']['connected'])

        status, r = self.post('/api/import/google/open', {'link': 'https://docs.google.com/spreadsheets/d/' + SID + '/edit'})
        self.assertEqual(status, 200, r)
        self.assertEqual(r['sheets'][0]['name'], 'Danh sách GV')
        status, cols = self.post('/api/import/columns', {'uploadId': r['uploadId'], 'sheet': 'Danh sách GV', 'header': 1, 'template': 'teachers'})
        self.assertEqual(status, 200, cols)

        self.assertFalse(self.post('/api/google/disconnect', {})[1]['google']['connected'])

    def test_callback_with_unknown_state_is_ignored(self):
        with urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect()).open(self.base + '/?state=forged&code=x', timeout=5) as r:
            self.assertEqual(r.status, 302)
        self.assertEqual(self.fake.calls, [])

    def test_google_endpoints_need_csrf(self):
        req = urllib.request.Request(self.base + '/api/google/start', data=b'{}', headers={'Content-Type': 'application/json', 'Origin': self.base})
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.http.open(req, timeout=5)
        self.assertEqual(e.exception.code, 403)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None

    def http_error_302(self, req, fp, code, msg, headers):
        return fp


if __name__ == '__main__':
    unittest.main()
