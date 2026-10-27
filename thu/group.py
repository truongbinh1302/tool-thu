"""Bộ sheet của tổ: 5 Google Sheet đọc tự động (tự nhận trang, hàng tiêu đề, cột).

Thư chỉ dán link một lần. Mỗi lần bấm "Cập nhật dữ liệu", tool đọc lại các sheet, chỉ giữ dòng của
giáo viên có trong trang "Danh sách GV TT", rồi thay ảnh chụp cũ bằng ảnh chụp mới (dòng biến mất
khỏi nguồn thì cũng biến mất trong tool). Không đọc ngầm (C03).
"""
import re
from datetime import date, timedelta
from .common import AppError, fold, text

KINDS = ('teachers', 'deadlines', 'homework', 'pass', 'errors')
NAMES = {'teachers': 'Danh sách giáo viên', 'deadlines': 'Quy trình xử lý 14 ngày', 'homework': 'Quản lý chỉ số CCBTVN',
         'pass': 'Kiểm soát tỷ lệ Pass band cao', 'errors': 'Xử lý lỗi GV'}
REQUIRED = {'teachers': ['ho va ten', 'ma gv', 'tinh trang'],
            'deadlines': ['ma lop', 'giao vien dung lop', 'ngay cap nhat'],
            'homework': ['ho va ten gv', 'ma lop', 'lich hoc'],
            'pass': ['ho va ten gv', 'ma lop', 'du kien pass'],
            'errors': ['thoi gian phat sinh loi', 'ma lop', 'buoi']}
ERRORS = {'#n/a', '#ref!', '#value!', '#error!', '#div/0!', '#name?', '#null!', '#num!', 'loading...'}
LIMITS = {'level': 120, 'type': 80, 'phone': 40, 'email': 160}
LADDER = ['Nhắc nhở', 'Cảnh cáo', 'Trừ 1/2 công', 'Trừ 1 công']
STAGES = ['Giai đoạn I', 'Giai đoạn II', 'Giai đoạn III', 'Giai đoạn IV', 'Giai đoạn V', 'Giai đoạn VI']


def norm(label):
    """Folded label without '(CODE)' notes and extra spaces, for matching column names."""
    s = fold(str(label or '').replace('\n', ' '))
    s = re.sub(r'\(code\)', ' ', s)
    s = re.sub(r'\(.*?\)', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def name_key(v):
    s = fold(str(v or ''))
    s = re.sub(r'^(ms|mr|mrs|co|thay)\.?\s+', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def filled(v):
    return v not in (None, '', '[ĐÃ ẨN]')


def is_error(v):
    return isinstance(v, str) and v.strip().lower() in ERRORS


def cell(row, i):
    return row[i] if i is not None and i < len(row) else None


def find_col(labels, wanted, exact_first=True):
    keys = [norm(x) for x in labels]
    if exact_first and wanted in keys:
        return keys.index(wanted)
    return next((i for i, k in enumerate(keys) if wanted in k), None)


def to_day(v):
    """Google serial date (or ISO text, or dd/mm/yyyy) → 'YYYY-MM-DD'; '' when not a date."""
    if v is None or v == '' or isinstance(v, bool):
        return ''
    if isinstance(v, (int, float)):
        if 20000 < v < 80000:
            return (date(1899, 12, 30) + timedelta(days=int(v))).isoformat()
        return ''
    s = str(v).strip()
    m = re.fullmatch(r'(\d{4})-(\d{2})-(\d{2})(?:[ T].*)?', s)
    if m:
        return '-'.join(m.groups())
    m = re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4})', s)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return ''
    return ''


def to_percent(v):
    """'37.50%' / 0.375 / 37.5 → 37.5 (percent); None when empty or not a number."""
    if v is None or v == '' or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return round(v * 100, 2) if -1.5 <= v <= 1.5 else round(float(v), 2)
    s = str(v).strip().replace(',', '.')
    try:
        return round(float(s[:-1]), 2) if s.endswith('%') else to_percent(float(s))
    except ValueError:
        return None


def is_date_label(k):
    return any(w in k for w in ('ngay', 'thoi gian', 'deadline', 'moc thoi gian', 'khai giang'))


def display(label, v):
    """Value as shown in the tool: dates as ISO, rates as percent, phone with leading 0."""
    k = norm(label)
    if v is None or v == '[ĐÃ ẨN]':
        return v
    if is_date_label(k) or k == 'ngay sinh':
        d = to_day(v)
        if d:
            return d
    if 'ti le' in k or 'ty le' in k:
        p = to_percent(v)
        return p if p is not None else v
    if k in ('sdt', 'so dien thoai') and isinstance(v, int) and len(str(v)) == 9:
        return '0' + str(v)
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


# --------------------------------------------------------------------------- detection

def header_candidates(sheet, limit=12):
    for pos, (row, number) in enumerate(zip(sheet['rows'][:limit], sheet['rowNumbers'][:limit])):
        yield pos, number, [str(v) if v is not None else '' for v in row]


def detect(kind, book):
    """→ (sheet dict, header position in rows). Prefers the tab Thư named for the teacher list."""
    tabs = list(book['sheets'])
    if kind == 'teachers':
        tabs.sort(key=lambda s: 0 if norm(s['name']) == 'danh sach gv tt' else 1 if 'gv tt' in norm(s['name']) else 2)
    for sheet in tabs:
        for pos, number, labels in header_candidates(sheet):
            keys = [norm(x) for x in labels]
            if all(any(w in k for k in keys) for w in REQUIRED[kind]):
                return sheet, pos
    names = ', '.join('"' + s['name'] + '"' for s in book['sheets'][:6])
    raise AppError('Không thấy bảng "' + NAMES[kind] + '" trong file này (các trang: ' + names + '). '
                   'Kiểm tra lại link hoặc tên cột: cần có ' + ', '.join(REQUIRED[kind]) + '.', 409, 'SOURCE_SCHEMA')


def labels_with_above(sheet, pos):
    """Header labels; an empty header cell takes the label above it (merged 2-row headers)."""
    rows = sheet['rows']
    width = max([len(r) for r in rows[pos:pos + 400]] + [0])
    out = []
    for i in range(width):
        label = cell(rows[pos], i)
        if not filled(label):
            label = next((cell(r, i) for r in reversed(rows[:pos]) if filled(cell(r, i))), None)
        out.append(str(label).replace('\n', ' ').strip() if filled(label) else '')
    return out


def body(sheet, pos):
    return [(n, r) for n, r in zip(sheet['rowNumbers'][pos + 1:], sheet['rows'][pos + 1:]) if any(filled(v) for v in r)]


def info_columns(labels, rows, keep_labeled_empty=False):
    """Column indexes that carry information: drop error-only (#N/A) and empty unlabeled columns."""
    keep = []
    for i, label in enumerate(labels):
        values = [cell(r, i) for _, r in rows if filled(cell(r, i))]
        if values and all(is_error(v) for v in values):
            continue
        if not values and not (keep_labeled_empty and label):
            continue
        keep.append(i)
    return keep


# --------------------------------------------------------------------------- parsers (no filtering yet)

def parse(kind, book):
    sheet, pos = detect(kind, book)
    meta = {'sheet': sheet['name'], 'header': sheet['rowNumbers'][pos]}
    return {**meta, **PARSERS[kind](sheet, pos)}


def parse_teachers(sheet, pos):
    labels = labels_with_above(sheet, pos)
    rows = body(sheet, pos)
    name = find_col(labels, 'ho va ten')
    rows = [(n, r) for n, r in rows if filled(cell(r, name))]
    cols = info_columns(labels, rows)
    out = []
    for n, r in rows:
        values = {labels[i] or ('Cột ' + str(i + 1)): display(labels[i], cell(r, i)) for i in cols}
        out.append({'row': n, 'name': str(cell(r, name)).strip(), 'values': values})
    get = lambda key: find_col(labels, key)
    return {'columns': [labels[i] or ('Cột ' + str(i + 1)) for i in cols], 'rows': out,
            'fields': {k: (labels[get(w)] if get(w) is not None else '') for k, w in
                       (('code', 'ma gv'), ('status', 'tinh trang'), ('level', 'level hien tai'), ('type', 'the loai'),
                        ('phone', 'sdt'), ('email', 'email'), ('mode', 'hinh thuc'))}}


def parse_deadlines(sheet, pos):
    rows_all = sheet['rows']
    labels = labels_with_above(sheet, pos)
    header = [str(v) if v is not None else '' for v in rows_all[pos]]
    above = [[str(v) if v is not None else '' for v in r] for r in rows_all[:pos]]
    rows = body(sheet, pos)
    col = lambda w: find_col(header, w)
    c = {'class': col('ma lop'), 'teacher': col('giao vien dung lop'), 'updated': col('ngay cap nhat'),
         'exam': col('ngay thi'), 'file': col('file quan ly'), 'type': col('loai lop'), 'total': col('tong hv'),
         'passed': col('hv pass'), 'rate': col('ty le') if col('ty le') is not None else col('ti le')}
    # Group labels (Deadline xử lý / PIC / Phương án xử lý) sit in the row above, merged over 2 rows.
    def above_col(w):
        for r in reversed(above):
            i = next((j for j, v in enumerate(r) if w in norm(v) and not filled(cell(rows_all[pos], j))), None)
            if i is not None and any(filled(cell(x, i)) for _, x in rows):
                return i
        return None
    used = {v for v in c.values() if v is not None}
    deadline = above_col('deadline')
    if deadline is None:  # copy without merges: the date column that is "ngày cập nhật + 3"
        best = None
        for i in range(len(labels)):
            if i in used or c['updated'] is None:
                continue
            pairs = [(to_day(cell(r, i)), to_day(cell(r, c['updated']))) for _, r in rows]
            pairs = [(a, b) for a, b in pairs if a and b]
            if len(pairs) >= 3:
                score = sum(date.fromisoformat(a) - date.fromisoformat(b) == timedelta(days=3) for a, b in pairs) / len(pairs)
                if score >= 0.6 and (best is None or score > best[0]):
                    best = (score, i)
        deadline = best[1] if best else None
    if deadline is None:
        raise AppError('Không tìm thấy cột "Deadline xử lý" trong sheet 14 ngày.', 409, 'SOURCE_SCHEMA')
    used.add(deadline)
    pic = above_col('pic')
    if pic is None:
        marks = {'ms. thu', 'to truong', 'tn', 'mr. hieu', 'mr. dung'}
        pic = next((i for i in range(len(labels)) if i not in used and
                    sum(fold(str(cell(r, i) or '')).strip() in marks for _, r in rows) >= 2), None)
    plan = above_col('phuong an')
    if plan is None and pic is not None and pic + 1 not in used:
        plan = pic + 1
    out = []
    for n, r in rows:
        if not filled(cell(r, c['teacher'])) or not filled(cell(r, c['class'])):
            continue
        if norm(cell(r, c['class'])) == 'ma lop':
            continue
        out.append({'row': n, 'class': str(cell(r, c['class'])).strip(), 'teacher': str(cell(r, c['teacher'])).strip(),
                    'deadline': to_day(cell(r, deadline)), 'updated': to_day(cell(r, c['updated'])),
                    'exam': to_day(cell(r, c['exam'])), 'file': str(cell(r, c['file']) or ''),
                    'classType': str(cell(r, c['type']) or ''), 'total': cell(r, c['total']), 'passed': cell(r, c['passed']),
                    'rate': to_percent(cell(r, c['rate'])), 'pic': str(cell(r, pic) or '').strip() if pic is not None else '',
                    'plan': str(cell(r, plan) or '') if plan is not None else ''})
    return {'rows': out}


def parse_table(sheet, pos, staged=False):
    """Generic table (CCBTVN, Pass band cao): keep every column that has information, in sheet order."""
    rows = body(sheet, pos)
    header = [str(v).replace('\n', ' ').strip() if v is not None else '' for v in sheet['rows'][pos]]
    labels = labels_with_above(sheet, pos) if not staged else header
    name = find_col(header, 'ho va ten gv')
    rows = [(n, r) for n, r in rows if filled(cell(r, name)) and norm(cell(r, name)) != 'ho va ten gv' and not is_error(cell(r, name))]
    cols = info_columns(labels, rows, keep_labeled_empty=staged)
    columns, stage = [], -1
    for i in range(len(labels)):
        k = norm(header[i] if i < len(header) else '')
        if staged and 'so hv du kien pass' in k:
            stage += 1
        if i not in cols:
            continue
        label = labels[i] or ('Cột ' + str(i + 1))
        kind = 'date' if is_date_label(norm(label)) else 'rate' if ('ti le' in norm(label) or 'ty le' in norm(label)) else \
            'support' if 'de xuat ho tro' in norm(label) else 'text'
        columns.append({'index': i, 'label': label, 'stage': STAGES[stage] if staged and stage >= 0 else '', 'kind': kind})
    out = []
    for n, r in rows:
        out.append({'row': n, 'teacher': str(cell(r, name)).strip(),
                    'cells': [None if is_error(cell(r, c['index'])) else display(c['label'], cell(r, c['index'])) for c in columns]})
    return {'columns': [{k: v for k, v in c.items() if k != 'index'} for c in columns], 'rows': out}


def parse_errors(sheet, pos):
    labels = [str(v).replace('\n', ' ').strip() if v is not None else '' for v in sheet['rows'][pos]]
    rows = body(sheet, pos)
    col = lambda w: find_col(labels, w)
    c = {'date': col('thoi gian phat sinh loi'), 'quarter': col('diem quy'), 'code': col('id giao vien'),
         'name': col('ho va ten gv'), 'class': col('ma lop'), 'session': col('buoi'),
         'code_col': col('ma lop - buoi'), 'detail': col('chi tiet loi')}
    # Thư: the "(CODE)" column holds the error content. If it only holds "lớp - buổi" codes, use "Chi tiết lỗi".
    texts = [str(cell(r, c['code_col'])) for _, r in rows if filled(cell(r, c['code_col']))] if c['code_col'] is not None else []
    if texts and sum(len(t) for t in texts) / len(texts) > 20:
        content, detail = c['code_col'], c['detail']
    else:
        content, detail = c['detail'], None
    out = []
    for n, r in rows:
        if not filled(cell(r, c['name'])) or norm(cell(r, c['name'])) == 'ho va ten gv':
            continue
        d = to_day(cell(r, c['date']))
        q = str(cell(r, c['quarter']) or '').strip().upper()
        if not re.fullmatch(r'Q[1-4]', q):
            q = ('Q' + str((int(d[5:7]) - 1) // 3 + 1)) if d else ''
        out.append({'row': n, 'date': d, 'quarter': q, 'period': (d[:4] + '-' + q) if d and q else q,
                    'teacherCode': str(cell(r, c['code']) or '').strip(), 'teacher': str(cell(r, c['name'])).strip(),
                    'class': str(cell(r, c['class']) or '').strip(), 'session': display('buoi', cell(r, c['session'])),
                    'content': str(cell(r, content) or '').strip() if content is not None else '',
                    'detail': display('chi tiet', cell(r, detail)) if detail is not None else ''})
    return {'rows': out, 'labels': {'content': labels[content] if content is not None else '', 'detail': labels[detail] if detail is not None else ''}}


PARSERS = {'teachers': parse_teachers, 'deadlines': parse_deadlines,
           'homework': lambda s, p: parse_table(s, p), 'pass': lambda s, p: parse_table(s, p, staged=True),
           'errors': parse_errors}


# --------------------------------------------------------------------------- state

def group_state(state):
    g = state.setdefault('group', {})
    g.setdefault('sources', {})
    g.setdefault('data', {})
    g.setdefault('settings', {'pic': ['Ms. Thư'], 'passThreshold': 50})
    return g


def configured(state):
    return bool(group_state(state)['sources'].get('teachers'))


def roster(g):
    return {name_key(r['name']) for r in g['data'].get('teachers', {}).get('rows', [])}


def ladder(n):
    return LADDER[min(n, len(LADDER)) - 1] if n > 0 else ''


def apply_parsed(service, state, parsed, clock):
    """Write freshly read sheets into the store. `parsed` = {kind: parse() result}. Returns per-kind summary."""
    g = group_state(state)
    summary = {}
    for kind, p in parsed.items():  # the tab/header may have moved; remember where the table is now
        if kind in g['sources']:
            g['sources'][kind].update(sheet=p['sheet'], header=p['header'])
    if 'teachers' in parsed:
        g['data']['teachers'] = {**parsed['teachers'], 'read': clock.stamp()}
        summary['teachers'] = sync_teachers(service, state, g, clock)
    names = roster(g)
    pics = {name_key(p) for p in g['settings'].get('pic', [])}
    for kind in ('deadlines', 'homework', 'pass', 'errors'):
        if kind not in parsed:
            continue
        p = parsed[kind]
        rows = [r for r in p['rows'] if name_key(r['teacher']) in names]
        outside = len(p['rows']) - len(rows)
        mine = None
        if kind == 'deadlines':  # PIC is filtered when shown, so changing the PIC setting needs no re-read
            rows.sort(key=lambda r: (r['deadline'] or '9999', r['class']))
            mine = sum(name_key(r['pic']) in pics for r in rows)
        if kind == 'errors':
            rows.sort(key=lambda r: (r['date'] or '', r['row']))
            seen = {}
            for r in rows:
                k = (name_key(r['teacher']), r['period'])
                seen[k] = seen.get(k, 0) + 1
                r['nth'] = seen[k]
                r['suggested'] = ladder(seen[k])
        g['data'][kind] = {**{k: v for k, v in p.items() if k != 'rows'}, 'rows': rows, 'outside': outside, 'read': clock.stamp()}
        summary[kind] = {'kept': len(rows), 'outside': outside, 'mine': mine}
    g['lastRead'] = clock.stamp()
    return summary


def sync_teachers(service, state, g, clock):
    """Danh sách GV TT → teacher records (matched by name). Teachers dropped from the list are archived."""
    f = g['data']['teachers'].get('fields', {})
    created = updated = 0
    listed = set()
    problems = []
    for r in g['data']['teachers']['rows']:
        v = r['values']
        key = name_key(r['name'])
        listed.add(key)
        status_text = fold(str(v.get(f.get('status'), '') or ''))
        status = 'active' if (not status_text or 'dang day' in status_text) else 'inactive'
        old = next((t for t in state['teachers'] if name_key(t['name']) == key), None)
        code = str(v.get(f.get('code')) or '').strip() or (old['code'] if old else 'GV-' + str(r['row']))
        if any(t['code'].lower() == code.lower() and (old is None or t['id'] != old['id']) for t in state['teachers']):
            code = old['code'] if old else code + '-' + str(r['row'])
        payload = {**(old or {}), 'code': code[:80], 'name': r['name'][:160], 'status': status}
        for field in ('level', 'type', 'phone', 'email'):
            label = f.get(field)
            if label and v.get(label) not in (None, '', '[ĐÃ ẨN]'):
                payload[field] = str(v[label]).strip()[:LIMITS[field]]
        if not payload.get('type') and f.get('mode') and v.get(f['mode']):
            payload['type'] = str(v[f['mode']]).strip()[:LIMITS['type']]
        try:
            result = service.cmd_teacher_upsert(state, payload, clock)
        except AppError as e:  # one bad row must not block the whole update
            problems.append(r['name'] + ': ' + str(e))
            continue
        t = next(t for t in state['teachers'] if t['id'] == result['id'])
        t['groupManaged'] = True
        if old:
            updated += 1
        else:
            created += 1
    archived = 0
    for t in state['teachers']:
        if t.get('groupManaged') and name_key(t['name']) not in listed and t['status'] != 'archived':
            try:
                service.cmd_teacher_upsert(state, {**t, 'status': 'archived'}, clock)
                archived += 1
            except AppError as e:
                problems.append(t['name'] + ': ' + str(e))
    return {'kept': len(listed), 'created': created, 'updated': updated, 'archived': archived, 'problems': problems[:10]}


def message(kind, s):
    if kind == 'teachers':
        return (f"{s['kept']} giáo viên trong danh sách ({s['created']} mới, {s['updated']} cập nhật" + (f", {s['archived']} đã rời danh sách" if s['archived'] else '') + ')'
                + (f". Chưa lưu được {len(s['problems'])} GV: " + '; '.join(s['problems'][:3]) if s.get('problems') else ''))
    extra = f" ({s['mine']} dòng có PIC đã chọn)" if s.get('mine') is not None else ''
    return f"{s['kept']} dòng của tổ{extra}; bỏ qua {s['outside']} dòng của GV ngoài danh sách"


# --------------------------------------------------------------------------- reading (network; only after a button press)

def read_kind(google, kind, link, sheet=None):
    """Read one configured sheet. Without `sheet`, probe the first rows of every tab to find the table."""
    if sheet:
        try:
            book = google.read_book(link, tabs=[sheet])
            return parse(kind, book), book['google']
        except AppError as e:
            if e.code != 'SOURCE_SCHEMA':
                raise
            # Tab renamed or table moved: look through the other tabs before giving up.
    probe = google.read_book(link, probe=15)
    found, _ = detect(kind, probe)
    book = google.read_book(link, tabs=[found['name']])
    return parse(kind, book), book['google']


def read_all(google, sources, kinds=None):
    """→ (parsed {kind: result}, failures {kind: AppError}). Each kind is read independently."""
    parsed, failures = {}, {}
    for kind in KINDS:
        src = sources.get(kind)
        if not src or (kinds is not None and kind not in kinds):
            continue
        try:
            result, info = read_kind(google, kind, src['spreadsheetId'], src.get('sheet'))
            parsed[kind] = result
        except AppError as e:
            failures[kind] = e
    return parsed, failures
