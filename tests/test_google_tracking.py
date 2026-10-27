"""Saved Google Sheets sources + "Cập nhật dữ liệu" in the real store (manual only, C03)."""
import json
import sys
import threading
import unittest
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from thu.common import uid  # noqa: E402
from tests.test_google import CLIENT, SID, FakeGoogle, GoogleHttpTest, Resp  # noqa: E402


class SheetGoogle(FakeGoogle):
    """FakeGoogle whose sheet values the test can change between reads."""

    def __init__(self):
        super().__init__()
        self.values = [['STT', 'Họ và tên', 'Level'], ['C357', 'Trần Anh Thư', 'L1'], ['C98', 'Nguyễn Vy', 'L2']]

    def open(self, req, timeout=None):
        if '/values:batchGet' in req.full_url and not self.offline and not self.sheet_status:
            super().open(req, timeout)  # keeps auth checks and call log
            return Resp(200, {'valueRanges': [{'range': "'Danh sách GV'!A1:C9", 'values': self.values}]})
        return super().open(req, timeout)


class GoogleTrackingTest(GoogleHttpTest):
    # Inherited HTTP tests already run in test_google.
    test_full_flow_and_no_google_calls_without_user_action = None
    test_callback_with_unknown_state_is_ignored = None
    test_google_endpoints_need_csrf = None

    def setUp(self):
        super().setUp()
        self.fake = SheetGoogle()
        self.server.service.google.opener = self.fake
        self.post('/api/google/client', {'json': json.dumps(CLIENT)})
        r = self.post('/api/google/start', {})[1]
        state = urllib.parse.parse_qs(urllib.parse.urlsplit(r['url']).query)['state'][0]
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(self.base + '/?state=' + state + '&code=x', timeout=5).read()

    def state(self):
        req = urllib.request.Request(self.base + '/api/state', headers={'X-Tool-Mode': 'real'})
        with self.http.open(req, timeout=5) as r:
            return json.load(r)['state']

    def reads(self):
        return sum('/values:batchGet' in u for u, b, h in self.fake.calls)

    def import_sheet(self, save=True):
        status, book = self.post('/api/import/google/open', {'link': SID})
        self.assertEqual(status, 200, book)
        status, plan = self.post('/api/import/plan', {'uploadId': book['uploadId'], 'sheet': 'Danh sách GV', 'header': 1, 'template': 'teachers',
                                                      'mapping': {'code': 0, 'name': 1, 'level': 2}, 'options': {'policy': 'fill'}})
        self.assertEqual(status, 200, plan)
        self.assertTrue(plan['trackable'])
        self.assertNotIn('_track', plan)
        status, r = self.post('/api/import/commit', {'previewId': plan['previewId'], 'requestId': uid(), 'confirmed': True, 'saveSource': save})
        self.assertEqual(status, 200, r)
        return r

    def track(self):
        s = self.state()
        ids = [x['id'] for x in s['tracking']['sources']]
        status, r = self.post('/api/tracking/run', {'revision': s['_revision'], 'requestId': uid(), 'sourceIds': ids})
        self.assertEqual(status, 200, r)
        return r['result']

    def teacher(self, code):
        return next(t for t in self.state()['teachers'] if t['code'] == code)

    def test_save_source_then_update_only_on_button(self):
        r = self.import_sheet()
        self.assertTrue(r['result']['savedSource'].startswith('g-'))
        sources = self.state()['tracking']['sources']
        self.assertEqual([(s['name'], s['adapter'], s['sheet']) for s in sources], [('Danh sách Giáo viên · Danh sách GV', 'googleSheets', 'Danh sách GV')])
        before = self.reads()
        self.get('/api/bootstrap')
        self.state()
        self.assertEqual(self.reads(), before, 'no read without pressing the button')

        self.fake.values[2][1] = 'Nguyễn Thọ Tường Vy'
        self.fake.values.append(['C400', 'Lê Mới', 'L1'])
        result = self.track()
        self.assertEqual(self.reads(), before + 1)
        self.assertEqual(result['status'], 'SUCCESS', result)
        self.assertEqual((result['sources'][0]['counts']['create'], result['sources'][0]['counts']['update']), (1, 1))
        self.assertEqual(self.teacher('C98')['name'], 'Nguyễn Thọ Tường Vy')
        self.assertEqual(self.teacher('C400')['name'], 'Lê Mới')
        self.assertEqual(len(self.state()['teachers']), 3)

        again = self.track()  # nothing changed in the sheet
        self.assertEqual(again['appliedRecords'], 0)
        self.assertEqual(len(self.state()['teachers']), 3)

    def test_local_edit_is_kept(self):
        self.import_sheet()
        t = self.teacher('C357')
        s = self.state()
        status, r = self.post('/api/commands', {'revision': s['_revision'], 'requestId': uid(), 'name': 'teacher.upsert',
                                                 'payload': {**t, 'name': 'Trần Anh Thư (tổ trưởng)', 'status': 'inactive'}})
        self.assertEqual(status, 200, r)
        self.fake.values[1][2] = 'L3'
        result = self.track()
        self.assertEqual(result['sources'][0]['counts']['kept'], 1, result)
        t = self.teacher('C357')
        self.assertEqual((t['name'], t['level'], t['status']), ('Trần Anh Thư (tổ trưởng)', 'L1', 'inactive'))

    def test_teacher_status_not_reset_by_update(self):
        self.import_sheet()
        t = self.teacher('C98')
        s = self.state()
        self.post('/api/commands', {'revision': s['_revision'], 'requestId': uid(), 'name': 'teacher.upsert', 'payload': {**t, 'status': 'inactive'}})
        self.fake.values[2][2] = 'L5'
        self.track()
        t = self.teacher('C98')
        self.assertEqual((t['level'], t['status']), ('L5', 'inactive'))

    def test_changed_header_keeps_old_data(self):
        self.import_sheet()
        old = self.state()['teachers']
        self.fake.values[0] = ['STT', 'Level', 'Họ và tên']
        result = self.track()
        self.assertEqual(result['status'], 'ERROR')
        self.assertEqual(result['sources'][0]['code'], 'SOURCE_SCHEMA')
        self.assertEqual(self.state()['teachers'], old)

    def test_not_saved_without_tick_and_remove_source(self):
        self.import_sheet(save=False)
        self.assertEqual(self.state()['tracking']['sources'], [])
        self.import_sheet()
        s = self.state()
        sid = s['tracking']['sources'][0]['id']
        status, r = self.post('/api/commands', {'revision': s['_revision'], 'requestId': uid(), 'name': 'tracking.source_remove', 'payload': {'id': sid}})
        self.assertEqual(status, 200, r)
        self.assertEqual(self.state()['tracking']['sources'], [])

    def test_disconnected_google_reads_nothing(self):
        self.import_sheet()
        self.post('/api/google/disconnect', {})
        s = self.state()
        before = self.reads()
        status, r = self.post('/api/tracking/run', {'revision': s['_revision'], 'requestId': uid(), 'sourceIds': [s['tracking']['sources'][0]['id']]})
        self.assertEqual((status, r['code']), (409, 'GOOGLE_LOGIN'))
        self.assertEqual(self.reads(), before)



if __name__ == '__main__':
    unittest.main()
