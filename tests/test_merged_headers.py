"""Header cells merged across two rows keep their text in the top row only (Google Sheets / XLSX)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from thu.importer import columns, scrub_sheets  # noqa: E402


def book(rows):
    sheets = [{'name': 'Danh sách lớp xử lý', 'rows': rows, 'rowNumbers': list(range(1, len(rows) + 1)), 'warnings': []}]
    scrub_sheets(sheets)
    return {'filename': 't', 'epoch': '1900', 'missingCache': 0, 'sheets': sheets}


class MergedHeaderTest(unittest.TestCase):
    def test_vertically_merged_headers_and_late_filled_columns(self):
        top = ['THÔNG TIN LỚP', None, None, None, 'TỶ LỆ PASS', None, None, 'Deadline xử lý', 'PIC', 'Phương án xử lý']
        head = ['Ngày cập nhật', 'Mã lớp', 'Giáo viên đứng lớp', 'Ngày thi', 'Tổng HV', 'HV pass', 'Tỷ lệ']
        early = [[46029, 'I4.5_%d' % i, 'Nguyễn Anh Thư', 46017, 8, 5, 0.625] for i in range(10)]
        late = [[46100, 'PRE_96', 'Lã Minh Khánh', 46090, 8, 5, 0.625, 46103, 'Ms. Thư', 'Đã trao đổi với GV']]
        result = columns(book([top, head] + early + late), 'Danh sách lớp xử lý', 2, 'cases')
        labels = {c['index']: c['label'] for c in result['columns']}
        self.assertEqual(labels[1], 'Mã lớp')
        self.assertEqual(labels[7], 'Deadline xử lý')
        self.assertEqual(labels[8], 'PIC')
        self.assertEqual(labels[9], 'Phương án xử lý')
        pic = next(c for c in result['columns'] if c['index'] == 8)
        self.assertEqual(pic['samples'], ['Ms. Thư'])

    def test_empty_column_still_hidden(self):
        result = columns(book([['A', 'B', None], [1, 2, None], [3, 4]]), 'Danh sách lớp xử lý', 1, 'cases')
        self.assertEqual([c['index'] for c in result['columns']], [0, 1])


if __name__ == '__main__':
    unittest.main()
