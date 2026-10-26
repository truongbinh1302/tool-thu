import csv,io
from .common import KINDS

def csv_cell(x):
    if x is None:return ''
    if isinstance(x,(int,float)):return x
    x=str(x)
    return "'"+x if x.lstrip().startswith(('=','+','-','@','\t','\r','\n')) or (x.startswith('0') and x.isdigit()) else x

def report_csv(report):
    out=io.StringIO(newline='');w=csv.writer(out,quoting=csv.QUOTE_ALL,lineterminator='\r\n')
    def row(values):w.writerow([csv_cell(x) for x in values])
    row(['Tool Thư',report['status'],report['period'],report['end'],'Asia/Ho_Chi_Minh','Quy tắc',report['rules']['version']])
    row(['Mã','Giáo viên','Trạng thái',*[KINDS[k] for k in KINDS],'Số lỗi QC'])
    for t in report['teachers']:row([t['code'],t['name'],t['status'],*[t['values'][k]['displayPct'] for k in KINDS],t['qc']])
    row(['TỔNG','Tỷ lệ từ tổng số đếm','',*[report['totals'][k]['pct'] for k in KINDS]])
    row(['LƯU Ý','Ô trống = chưa đủ dữ liệu; phần trăm nguồn không có mẫu số không dùng để tính tổng.'])
    row(['Ghi chú',report['notes']]);return ('\ufeff'+out.getvalue()).encode('utf-8')
