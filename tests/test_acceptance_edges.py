"""Acceptance regressions using disposable data; no connected accounts."""
import csv
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from thu.common import AppError, Clock, uid
from thu.importer import read_workbook, build_plan, apply_plan, excel_day, excel_time
from thu.service import Service
from thu.calendar_service import calendar_ics


def task_workbook():
    """Excel stores 08:30 as a fraction of a day, not the text '08:30'."""
    buf = io.BytesIO()
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('xl/workbook.xml', f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Việc" r:id="r1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/styles.xml', f'<styleSheet xmlns="{ns}"><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="20"/></cellXfs></styleSheet>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet xmlns="{ns}"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>Công việc</t></is></c><c r="B1" t="inlineStr"><is><t>Ngày</t></is></c><c r="C1" t="inlineStr"><is><t>Giờ</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>Ôn bài tiếng Việt</t></is></c><c r="B2" t="inlineStr"><is><t>24/10/2026</t></is></c><c r="C2" s="1"><v>0.3541666666666667</v></c></row></sheetData></worksheet>')
    return buf.getvalue()


class AcceptanceEdges(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='Thu QA dữ liệu ')
        self.svc = Service(self.tmp.name)
        self.db = self.svc.stores['real']
        self.clock = Clock('real')

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, raw, template, mapping, filename='qa.csv'):
        book = read_workbook(raw, filename)
        return build_plan(book, book['sheets'][0]['name'], 1, template, mapping,
                          {'sourceName': 'QA only'}, self.db.read(), self.clock)

    def commit(self, plan, partial=False):
        return self.db.mutate(plan['revision'], uid(), 'import.commit',
                              {'fingerprint': plan['fingerprint']},
                              lambda s: apply_plan(self.svc, s, plan, self.clock, partial),
                              self.clock.stamp())

    def test_excel_numeric_time_import_and_utc_export(self):
        plan = self.plan(task_workbook(), 'tasks', {'title': 0, 'date': 1, 'time': 2}, 'qa.xlsx')
        self.assertEqual(plan['counts']['error'], 0, plan['items'])
        self.commit(plan)
        task = self.db.read()['tasks'][0]
        self.assertEqual((task['date'], task['time']), ('2026-10-24', '08:30'))
        self.assertIn(b'DTSTART:20261024T013000Z', calendar_ics(self.db.read()['events']))

    def test_malformed_csv_quote_rejected(self):
        with self.assertRaises(AppError):
            read_workbook(b'Code,Name\n001,"unfinished\n002,Other\n', 'qa.csv')

    def test_csv_multiline_bom_unicode_remain_valid(self):
        raw = '\ufeffCode,Name,Note\n001,Cô Thư,"Dòng một\nDòng hai, dấu phẩy"\n'.encode('utf-8')
        book = read_workbook(raw, 'qa.csv')
        self.assertEqual(book['sheets'][0]['rows'][1], ['001', 'Cô Thư', 'Dòng một\nDòng hai, dấu phẩy'])

    def test_missing_task_date_flagged_before_partial_commit(self):
        plan = self.plan('Title,Date\nThiếu ngày,\nViệc hợp lệ,2026-10-24\n'.encode(),
                         'tasks', {'title': 0, 'date': 1})
        self.assertEqual(plan['counts']['error'], 1, plan['items'])
        self.assertEqual(plan['counts']['create'], 1)
        self.commit(plan, True)
        self.assertEqual([t['title'] for t in self.db.read()['tasks']], ['Việc hợp lệ'])

    def test_missing_qc_date_flagged_before_partial_commit(self):
        self.svc.command('real', 0, uid(), 'teacher.upsert', {'code': '001', 'name': 'Cô Thư'})
        plan = self.plan('Code,Date,Detail\n001,,Thiếu ngày\n001,2026-10-24,Lỗi thử\n'.encode(),
                         'qc', {'teacherCode': 0, 'date': 1, 'detail': 2})
        self.assertEqual(plan['counts']['error'], 1, plan['items'])
        self.commit(plan, True)
        self.assertEqual([e['detail'] for e in self.db.read()['errors']], ['Lỗi thử'])

    def test_oversized_teacher_field_flagged_before_commit(self):
        plan = self.plan(('Code,Name\n' + 'X' * 81 + ',Quá dài\n001,Cô Thư\n').encode(),
                         'teachers', {'code': 0, 'name': 1})
        self.assertEqual(plan['counts']['error'], 1, plan['items'])
        self.commit(plan, True)
        self.assertEqual([t['code'] for t in self.db.read()['teachers']], ['001'])

    def test_out_of_range_excel_date_is_validation_error(self):
        for value in (float('nan'), float('inf'), 1e50, -1e50):
            with self.subTest(value=value), self.assertRaises(AppError):
                excel_day(value)

    def test_blank_and_non_utf8_csv_rejected(self):
        for raw in (b'', b'\n,\n', b'Code,Name\n001,\xff\n'):
            with self.subTest(raw=raw), self.assertRaises(AppError):
                read_workbook(raw, 'qa.csv')

    def test_corrupt_xlsx_and_unsupported_formats_rejected(self):
        for raw, name in ((b'not a zip', 'qa.xlsx'), (task_workbook()[:-12], 'qa.xlsx'),
                          (b'Code,Name\n001,Test\n', 'qa.xls'), (task_workbook(), 'qa.xlsm')):
            with self.subTest(name=name), self.assertRaises(AppError):
                read_workbook(raw, name)
        self.assertEqual(self.db.read()['_revision'], 0)

    def test_missing_required_mapping_does_not_write(self):
        with self.assertRaises(AppError):
            self.plan(b'Code\n001\n', 'teachers', {'code': 0})
        self.assertEqual(self.db.read()['_revision'], 0)

    def test_excel_time_boundaries_and_invalid_values(self):
        for value, expected in ((0, '00:00'), (0.5, '12:00'), (1439/1440, '23:59'), ('08:30', '08:30'), (None, '')):
            self.assertEqual(excel_time(value), expected)
        for value in (-0.5, 1, True, float('nan'), float('inf'), 1/86400, '25:00'):
            with self.subTest(value=value), self.assertRaises(AppError):
                excel_time(value)

    def test_case_due_before_start_flagged_before_commit(self):
        self.svc.command('real', 0, uid(), 'teacher.upsert', {'code': '001', 'name': 'Cô Thư'})
        plan = self.plan(b'Code,Class,Start,Due\n001,L01,2026-10-24,2026-10-23\n',
                         'cases', {'teacherCode': 0, 'code': 1, 'start': 2, 'due': 3})
        self.assertEqual(plan['counts']['error'], 1)
        with self.assertRaises(AppError):
            self.commit(plan)
        self.assertEqual(self.db.read()['processes'], [])

    def test_restore_all_domain_collections_and_pre_restore_copy(self):
        db = self.svc.stores['demo']
        def cmd(name, payload):
            return self.svc.command('demo', db.read()['_revision'], uid(), name, payload)
        cmd('teacher.alias', {'teacher': 'GV001', 'source': 'QA', 'code': '001'})
        cmd('template.add', {'title': 'Lịch thử', 'frequency': 'weekly', 'start': '2026-10-19'})
        cmd('report.note', {'period': '2026-10-19', 'note': 'Ghi chú thử tiếng Việt'})
        cmd('report.seal', {'period': '2026-10-19', 'acknowledgeIncomplete': True})
        cmd('tracking.fixture', {'sourceId': 'demo-sheet-main', 'scenario': 'changed', 'approved': True})
        self.svc.track('demo', db.read()['_revision'], uid(), ['demo-sheet-main'])
        expected = db.read()
        raw = db.backup()
        cmd('teacher.note', {'id': 'GV001', 'note': 'Thay đổi sau backup'})
        changed = db.read()
        restored, result = db.restore(raw, changed['_revision'], uid(), self.clock.stamp())
        self.assertGreater(restored.pop('_revision'), changed['_revision'])
        expected.pop('_revision')
        self.assertEqual(restored, expected)
        _, preserved = db.inspect_backup(Path(result['beforeBackup']).read_bytes())
        self.assertEqual(preserved, changed)
        reopened = Service(self.tmp.name).stores['demo'].read()
        reopened.pop('_revision')
        self.assertEqual(reopened, expected)


if __name__ == '__main__':
    unittest.main()
