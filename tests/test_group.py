"""Bộ sheet của tổ: tự nhận bảng, lọc theo danh sách GV, cập nhật khi bấm nút. Dữ liệu giả lập (không phải dữ liệu khách)."""
import json
import re
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from thu.common import AppError, uid  # noqa: E402
from thu.service import Service  # noqa: E402
from thu import group  # noqa: E402
from tests.test_google import CLIENT, FakeGoogle, Resp  # noqa: E402

D = lambda iso: (__import__('datetime').date.fromisoformat(iso) - __import__('datetime').date(1899, 12, 30)).days

IDS = {k: k.upper() + '_' + 'x' * 30 for k in group.KINDS}


def books():
    teachers = {'title': 'Danh sách Giáo viên - Tổ trưởng Mẫu', 'tabs': {
        'Danh sách GV': [['STT', 'Họ và tên', 'Số điện thoại', 'Mã GV'], ['C1', 'Người Ngoài Tổ', 912345678, 111]],
        'Danh sách GV TT': [['STT', 'Tình trạng', 'Mã GV', 'Họ và tên', 'Thể loại', 'Level ban đầu', 'Level hiện tại', 'SĐT', 'Ngày sinh', 'Email'],
                            [1, 'Đang dạy', 1001, 'Lê Văn An', 'Freetime', 'Level 2', 'Level 3', 912000001, D('2001-02-03'), 'an@example.com'],
                            [2, 'Đang dạy', 1002, 'Phạm Thị Bình', 'Parttime 4', 'Level 4', 'Level 4', 912000002, '', 'binh@example.com'],
                            [3, 'Tạm nghỉ', 1003, 'Đỗ Minh Châu', 'Parttime 6', 'Level 1', 'Level 1', 912000003, '', 'chau@example.com']]}}
    head = ['Lọc trùng', 'STT', 'Mốc thời gian', 'Ngày cập nhật', 'Mã lớp', 'Loại lớp', 'Ngày thi', 'File quản lý lớp', 'Giáo viên đứng lớp',
            'Trưởng nhóm phụ trách', 'Tổng HV', 'HV pass', 'Tỷ lệ']
    top = ['THÔNG TIN LỚP', '', '', '', '', '', '', '', '', '', 'TỶ LỆ PASS', '', '', 'Deadline xử lý', 'PIC', 'Phương án xử lý']

    def lop(cls, gv, upd, pic, plan=''):
        return [1, 1, '', D(upd), cls, 'Lớp thường', D(upd) - 7, 'https://docs.google.com/spreadsheets/d/' + cls, gv, 'TN Mẫu', 8, 4, 0.5,
                D(upd) + 3, pic, plan]
    deadlines = {'title': 'Quy trình xử lý 14 ngày', 'tabs': {
        'Quy trình': [['Bước 1', 'Tiếp nhận']],
        'Danh sách lớp xử lý': [top, head,
                                lop('L-01', 'Lê Văn An', '2026-10-25', 'Ms. Thư', 'Đã trao đổi'),
                                lop('L-02', 'Phạm Thị Bình', '2026-10-28', 'Ms. Thư'),
                                lop('L-03', 'Lê Văn An', '2026-10-29', 'Tổ trưởng'),
                                lop('L-04', 'Người Ngoài Tổ', '2026-10-28', 'Ms. Thư'),
                                lop('L-05', 'Đỗ Minh Châu', '2026-10-29', 'Ms. Thư'),
                                lop('L-06', 'Phạm Thị Bình', '2026-10-10', 'Ms. Thư')]}}
    homework = {'title': 'Quản lý chỉ số CCBTVN', 'tabs': {'Sheet1': [
        ['Trưởng nhóm quản lý', 'TN Mẫu'], ['Số lượng lớp đang quản lý', 3],
        ['Họ và tên GV', 'Mã lớp', 'Lịch học', 'Ngày khai giảng', 'Ngày thi giữa kỳ', 'Ngày thi cuối kỳ', 'Lớp đang đến buổi', '', ''],
        ['Lê Văn An', 'L-01', '2,5 - 18h', D('2026-09-01'), D('2026-10-01'), D('2026-11-01'), 10, '#N/A', '#N/A'],
        ['Người Ngoài Tổ', 'L-04', '3,6 - 18h', D('2026-09-02'), D('2026-10-02'), D('2026-11-02'), 9, '#N/A', '#N/A'],
        ['', '', '', '', '', '', '', '#N/A', '#N/A']]}}
    stage = ['Số HV dự kiến Pass', 'Ti lệ Pass dự kiến', 'Phương án tiếp theo', 'Đề xuất hỗ trợ']
    pas = {'title': 'Kiểm soát tỷ lệ Pass đầu ra band cao', 'tabs': {'Sheet1': [
        ['', '', '', '', '', '', 'GIAI ĐOẠN I', '', '', '', 'GIAI ĐOẠN II'],
        ['Họ và tên GV', 'Mã lớp', 'Ngày khai giảng', 'Ngày thi cuối khóa', 'Tổng số HV lớp'] + stage + stage,
        ['Lê Văn An', 'P-01', D('2026-08-01'), D('2026-12-01'), 8, 6, 0.75, 'Ổn', '', 3, 0.375, 'Ôn tập thêm', ''],
        ['Phạm Thị Bình', 'P-02', D('2026-08-02'), D('2026-12-02'), 8, 6, 0.75, '', '@Thư giúp mình', '', 0, '', ''],
        ['Người Ngoài Tổ', 'P-03', D('2026-08-03'), D('2026-12-03'), 8, 1, 0.125, '', '', '', '', '', '']]}}
    errhead = ['Thời gian phát sinh lỗi', 'Điểm quý\n(CODE)', 'ID giáo viên', 'Nhãn', 'Họ và tên GV', 'Mã lớp', 'Buổi', 'Mã lớp - Buổi\n(CODE)',
               'Chi tiết lỗi', 'Số ca lỗi trong quý\n(CODE)', 'Hình thức xử lý']
    e = lambda d, code, gv, cls, b, txt, n: [D(d), 'Q4', code, 'EC', gv, cls, b, txt, n, '', '']
    errors = {'title': 'Xử lý lỗi GV', 'tabs': {
        'Quy trình': [['Lỗi', 'Hình thức']],
        'Danh sách lỗi': [errhead,
                          e('2026-10-01', 'C1', 'Lê Văn An', 'L-01', 3, 'Giáo viên Lê Văn An điểm danh muộn buổi 3 lớp L-01', 1),
                          e('2026-10-05', 'C1', 'Lê Văn An', 'L-01', 4, 'Giáo viên Lê Văn An chưa chấm BTVN buổi 4 lớp L-01', 2),
                          e('2026-10-09', 'C1', 'Lê Văn An', 'L-03', 2, 'Giáo viên Lê Văn An vào lớp muộn buổi 2 lớp L-03', 3),
                          e('2026-10-07', 'C9', 'Người Ngoài Tổ', 'L-04', 1, 'Giáo viên Người Ngoài Tổ chưa điểm danh', 1),
                          [D('2026-07-15'), 'Q3', 'C2', 'EC', 'Phạm Thị Bình', 'L-02', 5, 'Giáo viên Phạm Thị Bình chưa chấm bài', 1]],
        'Báo cáo lỗi': [['Tổng hợp']] + [[i] for i in range(40)]}}
    return {IDS['teachers']: teachers, IDS['deadlines']: deadlines, IDS['homework']: homework, IDS['pass']: pas, IDS['errors']: errors}


class SheetsGoogle(FakeGoogle):
    def __init__(self):
        super().__init__()
        self.books = books()
        self.ranges = []

    def open(self, req, timeout=None):
        url = req.full_url
        if not url.startswith('https://sheets.googleapis.com') or self.offline or self.sheet_status:
            return super().open(req, timeout)
        self.calls.append((url, {}, dict(req.header_items())))
        sid = re.search(r'/spreadsheets/([^/?]+)', url).group(1)
        book = self.books[sid]
        if '/values:batchGet' not in url:
            return Resp(200, {'properties': {'title': book['title']}, 'sheets': [{'properties': {'title': t}} for t in book['tabs']]})
        out = []
        for rng in urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['ranges']:
            self.ranges.append(rng)
            m = re.fullmatch(r"'(.*)'(?:!1:(\d+))?", rng)
            values = book['tabs'][m.group(1).replace("''", "'")]
            out.append({'range': rng, 'values': values[:int(m.group(2))] if m.group(2) else values})
        return Resp(200, {'valueRanges': out})


class GroupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.svc = Service(self.tmp.name)
        self.fake = SheetsGoogle()
        self.svc.google.opener = self.fake
        g = self.svc.google
        g.save_client(json.dumps(CLIENT))
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(g.start('http://127.0.0.1:1/')).query)
        g.finish(q['state'][0], 'code')
        self.today = '2026-10-27'

    def tearDown(self):
        self.tmp.cleanup()

    def rev(self):
        return self.svc.stores['real'].read()['_revision']

    def setup_all(self, kinds=group.KINDS):
        return self.svc.group_setup('real', self.rev(), uid(), {k: 'https://docs.google.com/spreadsheets/d/' + IDS[k] + '/edit' for k in kinds})

    def g(self):
        return self.svc.stores['real'].read()['group']

    def test_teacher_list_comes_first(self):
        with self.assertRaises(AppError):
            self.setup_all(['deadlines'])

    def test_setup_detects_tabs_headers_and_filters_by_team(self):
        r = self.setup_all()['result']
        self.assertEqual(r['errors'], {})
        src = self.g()['sources']
        self.assertEqual(src['teachers']['sheet'], 'Danh sách GV TT')
        self.assertEqual((src['deadlines']['sheet'], src['deadlines']['header']), ('Danh sách lớp xử lý', 2))
        self.assertEqual(src['homework']['header'], 3)
        self.assertEqual(src['errors']['sheet'], 'Danh sách lỗi')
        # the big report tab is only probed (first rows), never read in full
        self.assertNotIn("'Báo cáo lỗi'", self.fake.ranges)
        data = self.g()['data']
        state = self.svc.stores['real'].read()
        names = sorted(t['name'] for t in state['teachers'])
        self.assertEqual(names, ['Lê Văn An', 'Phạm Thị Bình', 'Đỗ Minh Châu'])
        chau = next(t for t in state['teachers'] if t['name'] == 'Đỗ Minh Châu')
        self.assertEqual((chau['code'], chau['status']), ('1003', 'inactive'))
        an = next(t for t in state['teachers'] if t['name'] == 'Lê Văn An')
        self.assertEqual((an['level'], an['type'], an['phone']), ('Level 3', 'Freetime', '0912000001'))
        self.assertEqual(data['teachers']['rows'][0]['values']['Ngày sinh'], '2001-02-03')
        # 14 ngày: GV ngoài tổ bị bỏ; PIC giữ lại để lọc khi hiển thị; deadline từ cột gộp
        rows = data['deadlines']['rows']
        self.assertEqual([r['class'] for r in rows], ['L-06', 'L-01', 'L-02', 'L-03', 'L-05'])
        self.assertEqual(rows[1]['deadline'], '2026-10-28')
        self.assertEqual((rows[1]['pic'], rows[1]['plan']), ('Ms. Thư', 'Đã trao đổi'))
        self.assertTrue(rows[1]['file'].startswith('https://'))
        # CCBTVN: cột #N/A bị bỏ, ngày đổi sang ISO
        hw = data['homework']
        self.assertEqual([c['label'] for c in hw['columns']], ['Họ và tên GV', 'Mã lớp', 'Lịch học', 'Ngày khai giảng', 'Ngày thi giữa kỳ', 'Ngày thi cuối kỳ', 'Lớp đang đến buổi'])
        self.assertEqual(hw['rows'][0]['cells'][3], '2026-09-01')
        self.assertEqual((len(hw['rows']), hw['outside']), (1, 1))
        # Pass: đủ 2 giai đoạn, tỷ lệ thành %
        ps = data['pass']
        self.assertEqual([c['stage'] for c in ps['columns']][5:], ['Giai đoạn I'] * 4 + ['Giai đoạn II'] * 4)
        self.assertEqual(ps['rows'][0]['cells'][10], 37.5)
        self.assertEqual(len(ps['rows']), 2)
        # Lỗi: nội dung từ cột (CODE), đếm theo quý, mức xử lý
        er = data['errors']['rows']
        self.assertEqual(len(er), 4)
        an_q4 = [x for x in er if x['teacher'] == 'Lê Văn An']
        self.assertEqual([x['suggested'] for x in an_q4], ['Nhắc nhở', 'Cảnh cáo', 'Trừ 1/2 công'])
        self.assertIn('điểm danh muộn', an_q4[0]['content'])
        self.assertEqual((an_q4[0]['class'], an_q4[0]['session'], an_q4[0]['detail']), ('L-01', 3, 1))
        self.assertEqual(next(x for x in er if x['teacher'] == 'Phạm Thị Bình')['period'], '2026-Q3')

    def test_update_button_rereads_replaces_and_archives(self):
        self.setup_all()
        reads = len(self.fake.ranges)
        self.svc.snapshot('real')
        self.assertEqual(len(self.fake.ranges), reads, 'no read without the button')
        b = self.fake.books
        b[IDS['deadlines']]['tabs']['Danh sách lớp xử lý'].pop(2)  # L-01 removed from source
        b[IDS['teachers']]['tabs']['Danh sách GV TT'].pop(2)  # Phạm Thị Bình leaves the team
        r = self.svc.track('real', self.rev(), uid(), ['group'])['result']
        self.assertEqual(r['status'], 'SUCCESS', r)
        self.assertEqual(len(self.fake.ranges), reads + 5, 'one read per configured sheet, tabs already known')
        data = self.g()['data']
        self.assertEqual([x['class'] for x in data['deadlines']['rows']], ['L-03', 'L-05'])
        state = self.svc.stores['real'].read()
        self.assertEqual(next(t for t in state['teachers'] if t['name'] == 'Phạm Thị Bình')['status'], 'archived')
        self.assertTrue(all(x['teacher'] != 'Phạm Thị Bình' for x in data['errors']['rows']))

    def test_changed_layout_reports_error_and_keeps_old_data(self):
        self.setup_all()
        old = self.g()['data']['pass']
        self.fake.books[IDS['pass']]['tabs']['Sheet1'][1][0] = 'Giáo viên'
        r = self.svc.track('real', self.rev(), uid(), ['group'])['result']
        self.assertEqual(r['status'], 'PARTIAL')
        self.assertEqual(next(x for x in r['sources'] if x['id'] == 'group:pass')['code'], 'SOURCE_SCHEMA')
        self.assertEqual(self.g()['data']['pass']['rows'], old['rows'])

    def test_copy_without_merged_headers(self):
        """A pasted copy loses merges: deadline column is found as 'ngày cập nhật + 3'."""
        tab = self.fake.books[IDS['deadlines']]['tabs']['Danh sách lớp xử lý']
        tab[0] = ['THÔNG TIN LỚP', 'TỶ LỆ PASS', 'Deadline xử lý', 'PIC', 'Phương án xử lý']
        self.setup_all(['teachers', 'deadlines'])
        rows = self.g()['data']['deadlines']['rows']
        self.assertEqual(rows[1]['deadline'], '2026-10-28')
        self.assertEqual(rows[1]['pic'], 'Ms. Thư')

    def test_settings_and_remove(self):
        self.setup_all()
        s = self.svc.command('real', self.rev(), uid(), 'group.settings', {'pic': ['Ms. Thư', 'Tổ trưởng'], 'passThreshold': 60})
        self.assertEqual(s['result']['settings']['passThreshold'], 60)
        with self.assertRaises(AppError):
            self.svc.command('real', self.rev(), uid(), 'group.remove', {'kind': 'teachers'})
        self.svc.command('real', self.rev(), uid(), 'group.remove', {'kind': 'pass'})
        self.assertNotIn('pass', self.g()['sources'])
        self.assertNotIn('pass', self.g()['data'])

    def test_name_matching(self):
        self.assertEqual(group.name_key('Ms. Lê  Văn An '), group.name_key('lê văn an'))
        self.assertEqual(group.to_percent('37.50%'), 37.5)
        self.assertEqual(group.to_percent(0.5), 50)
        self.assertEqual(group.to_day(D('2026-10-28')), '2026-10-28')


if __name__ == '__main__':
    unittest.main()
