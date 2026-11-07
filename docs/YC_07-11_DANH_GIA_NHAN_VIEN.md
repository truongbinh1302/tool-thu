# Yêu cầu 07/11/2026 — Đánh giá nhân viên (bản 1.1.0)

> Tài liệu này viết cho người thực hiện **chưa biết gì về dự án**. Đọc hết trước khi sửa code.

## 0. Bối cảnh dự án

- **Tool Thư** là app quản lý giáo viên chạy **local** trên MacBook (Apple Silicon) của khách hàng tên Thư, một tổ trưởng quản lý khoảng 10–30 giáo viên. Không có server ngoài, không đăng nhập, một người dùng.
- Kiến trúc: `start.py` khởi động server Python (thư viện chuẩn, **không dependency pip lúc chạy**) phục vụ giao diện web tại `127.0.0.1`; trình duyệt mở giao diện. Đóng gói thành app Mac bằng PyInstaller (`packaging/`), build trên GitHub Actions (`.github/workflows/build-mac.yml`).
- Bản đã bàn giao: **1.0.0** (nhánh `ban-1.0.0`, commit 4419d56) — **tuyệt đối không sửa nhánh này**. Mọi việc làm trên nhánh **`phat-trien`**.
- Đọc trước: `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/CUSTOMER_REQUIREMENTS.md`.
- Repo **public**: không commit dữ liệu khách thật, DB, file sao lưu, token, mật khẩu, đường dẫn máy cá nhân. Test chỉ dùng tên giả.

### Bản đồ code cần biết

| File | Vai trò |
|---|---|
| `thu/__init__.py` | `__version__` — build đọc số phiên bản từ đây |
| `thu/common.py` | Clock, validate (`text`, `day`, `url`…), `empty_state()` |
| `thu/store.py` | SQLite. `TABLES` = danh sách bảng; mỗi bảng giữ JSON payload. `VERSION` = schema hiện tại (2), `migrate()`, `backup()`, `restore()` |
| `thu/service.py` | **Nơi duy nhất** thay đổi nghiệp vụ. Mỗi lệnh là `cmd_<tên>(self,s,p,clock)`; frontend gọi bằng tên dạng `task.upsert` → `cmd_task_upsert`. Dùng helper `record`, `put`, `ref`, `find` |
| `thu/metrics.py` | Nơi duy nhất tính tổng/trạng thái/kỳ báo cáo |
| `thu/group.py` | Bộ sheet của tổ (5 Google Sheet): dữ liệu nằm ở `state['group']` — danh sách GV tổ, lớp 14 ngày + deadline, CCBTVN, Pass band cao, Lỗi GV (đếm theo quý, mức xử lý) |
| `thu/calendar_service.py` | Họp, lịch, xuất .ics |
| `web/core.js` | Gọi API, hàng đợi ghi, modal, định dạng (`esc`, `dt`, `pct`…) |
| `web/views.js` | Các trang (`teachersPage`, `tasksPage`, `reportsPage`…) |
| `web/forms.js` | Form/modal; **`teacherProfile(id)` = hồ sơ GV hiện tại** (mở khi bấm tên GV, `data-teacher`/`teacher:<id>`) |
| `web/group.js` | Trang Theo dõi tổ (`teamPage`) |
| `web/app.js` | Điều phối sự kiện, route |
| `web/style.css` | Giao diện hồng — giữ nguyên phong cách |
| `tests/` | Python unittest + 2 file kiểm tra Node (`check_views.js`, `check_tracking_ui.js`) |

Chạy test: `python3 -m unittest discover -s tests -v` và `node --check web/<file>.js`, `node tests/check_views.js`, `node tests/check_tracking_ui.js`.

Bảng `tasks` **đã có** trường `teacher` (xem `cmd_task_upsert`): task gắn GV đã tồn tại sẵn.

## 1. Yêu cầu gốc của khách (giữ nguyên ý)

1. Thang điểm **50 / 1 quý**.
2. Nhập thủ công: có 2 lựa chọn **+1** và **−1** để Thư tự nhập.
3. Tổng hợp **tất cả thông tin** của từng nhân viên: mọi thông tin và deadline liên quan tới nhân viên đó. Có chỗ **nhập task thủ công** để Thư tự thêm task cho nhân viên đó.
4. Nút **xuất PDF**: báo cáo chi tiết riêng cho từng nhân viên, và báo cáo tổng quát cho tất cả nhân viên. **Xếp hạng** nhân viên theo điểm từ cao xuống thấp.

"Nhân viên" = giáo viên (bảng `teachers`, trang Đội ngũ giáo viên).

## 2. Đặc tả triển khai

### 2.1 Điểm quý
- Mỗi GV bắt đầu mỗi quý với **50 điểm**. Quý theo lịch: Q1 = T1–T3, Q2 = T4–T6, Q3 = T7–T9, Q4 = T10–T12 (khớp cách đếm quý của Lỗi GV trong `thu/group.py`). Quý xác định theo **ngày ghi nhận** của bản ghi (UTC+7, dùng Clock trong `common.py`).
- Điểm = 50 + số bản ghi +1 − số bản ghi −1 trong quý. Sang quý mới tự về 50; quý cũ giữ nguyên, xem lại được.
- Bản ghi mới, bảng **`scoreEntries`**: `id`, `teacher` (id GV, bắt buộc), `delta` (chỉ nhận `1` hoặc `-1`), `date` (YYYY-MM-DD, mặc định hôm nay), `reason` (bắt buộc, ≤ 1000 ký tự), `createdBy` (mặc định "Thư"), `created`, `updated`.
- Lệnh service: `score.add` (thêm/sửa), `score.delete` (xóa). Validate: GV tồn tại, delta ∈ {1,−1}, reason không rỗng.
- Tính điểm/xếp hạng đặt trong **`thu/metrics.py`** (theo quy ước "một chỗ tính"), frontend chỉ hiển thị kết quả trả về.
- **Không** tự cộng/trừ điểm từ lỗi QC, Lỗi GV, chỉ số hay deadline — chỉ hiển thị cạnh điểm để Thư tự quyết.
- **Không giới hạn** trên/dưới (điểm có thể > 50 hoặc < 0).

### 2.2 Task thủ công của nhân viên
- **Dùng lại bảng `tasks` có sẵn** (trường `teacher`), không tạo bảng mới. Trên hồ sơ GV có nút "Thêm task" mở form task hiện có với `teacher` điền sẵn; danh sách task của GV đó, sửa/đổi trạng thái (todo/doing/done) ngay tại hồ sơ.
- Task tạo ở hồ sơ GV vẫn hiện bình thường ở trang Công việc của tôi.

### 2.3 Hồ sơ nhân viên (tổng hợp)
Mở rộng `teacherProfile(id)` (hoặc chuyển thành trang riêng nếu modal quá chật — tùy chọn, ghi lý do trong commit). Gồm các thẻ:
1. **Thông tin GV**: mã, thể loại, level, SĐT, email, ngày sinh, trạng thái.
2. **Điểm quý**: điểm hiện tại lớn, nút **+1** và **−1** (mỗi nút mở form nhỏ: ngày, lý do bắt buộc), lịch sử bản ghi trong quý (ngày, ±1, lý do, sửa/xóa), ô chọn quý.
3. **Task của nhân viên** (mục 2.2).
4. **Deadline & việc liên quan** — một danh sách gộp, sắp theo hạn tăng dần: task của GV (chưa xong), lớp 14 ngày của GV trong `state['group']`, hồ sơ xử lý lớp, buổi họp có mời GV, sự kiện lịch liên quan. Tô **đỏ** quá hạn, **vàng** trong 7 ngày tới. Mỗi dòng ghi nguồn (Task / 14 ngày / Hồ sơ / Họp / Lịch).
5. **Chỉ số & lỗi** (chỉ đọc): CCBTVN, Pass band cao, Lỗi GV theo quý (số lỗi + mức xử lý), lỗi QC nhập tay.
- Mở hồ sơ **không gọi Google** (quy tắc C03: chỉ đọc nguồn khi bấm Cập nhật dữ liệu).

### 2.4 Xếp hạng quý
- Thêm mục **Xếp hạng quý** (thẻ trên trang Đội ngũ giáo viên hoặc trang Báo cáo — chọn chỗ hợp lý, có ô chọn quý).
- Chỉ GV **Đang dạy/đang hoạt động**. Sắp **điểm cao → thấp**; hòa điểm xếp theo tên A–Z (so sánh có dấu tiếng Việt, dùng `localeCompare('vi')`). Hạng đồng hạng khi bằng điểm (1, 2, 2, 4).
- Cột: Hạng, GV (bấm mở hồ sơ), Điểm, Số lần +1, Số lần −1, Lỗi GV trong quý, Task chưa xong, Task quá hạn.

### 2.5 Xuất PDF
- **PDF từng GV**: nút "Xuất PDF" trên hồ sơ GV → báo cáo quý đang chọn: thông tin GV, điểm + toàn bộ lịch sử ±1 kèm lý do, task, deadline, chỉ số & lỗi.
- **PDF tổng quát**: nút "Xuất PDF" ở Xếp hạng quý → bảng xếp hạng toàn tổ + 1–2 dòng tóm tắt mỗi GV.
- Đầu báo cáo: "Tool Thư — Báo cáo đánh giá", quý (vd. Q4/2026), ngày xuất. Tiêu đề trang (document.title) đặt theo tên file gợi ý: `BaoCao_<TenGVKhongDau>_2026-Q4`, `XepHang_To_2026-Q4` để hộp thoại lưu PDF tự lấy tên.
- **Cách làm bắt buộc**: tạo khung in riêng + CSS `@media print` rồi gọi `window.print()`; người dùng chọn "Lưu dưới dạng PDF". **Không thêm thư viện PDF** (không pip/npm). Trang in: nền trắng, ẩn thanh bên/nút, bảng không bị cắt ngang dòng (`break-inside: avoid`), lặp tiêu đề bảng khi sang trang, tiếng Việt có dấu hiển thị đúng (dùng font sẵn trong `web/fonts`).

### 2.6 Dữ liệu, migrate, sao lưu
- Thêm `'scoreEntries'` vào `TABLES` trong `store.py`, nâng `VERSION` lên **3**, viết migrate 2 → 3 (tạo bảng mới, không đụng dữ liệu cũ). Kho 1.0.0 mở bằng 1.1.0 phải chạy bình thường, giữ nguyên dữ liệu.
- `empty_state()` có `scoreEntries: []`. Sao lưu/khôi phục/kho dùng thử/đặt lại bao gồm `scoreEntries`. Khôi phục file sao lưu tạo từ 1.0.0 (schema 2) vào 1.1.0 phải được (migrate sau khi khôi phục) — nếu `restore()` đang chặn schema khác `VERSION` thì sửa cho nhận schema 2 và nâng lên 3.
- Xóa GV: xử lý `scoreEntries` theo cùng cách các bảng liên quan khác đang làm (xem cách `tasks`/`errors` xử lý tham chiếu GV) — không để bản ghi mồ côi làm lỗi.
- Ghi nhật ký thao tác cho score.add/score.delete như các lệnh khác.
- (Tuỳ chọn) Xuất CSV lịch sử điểm quý.

### 2.7 Phiên bản
- `thu/__init__.py`: `__version__ = '1.1.0'`. Cập nhật README (mục lịch sử phiên bản) và `packaging/CAI_DAT_MAC.md` (hướng dẫn dùng tính năng mới, tiếng Việt, ngắn gọn cho người không rành máy tính).

## 3. Nghiệm thu

Thêm test vào `tests/` (đặt tên ví dụ `test_scores.py`):
- Điểm quý: 50 khi chưa có bản ghi; +1/−1 cộng đúng; bản ghi quý khác không ảnh hưởng; sang quý mới về 50; sửa/xóa bản ghi cập nhật điểm; điểm vượt 50 và âm vẫn đúng.
- Validate: delta khác ±1, thiếu lý do, GV không tồn tại → lỗi `AppError`.
- Xếp hạng: giảm dần, hòa điểm theo tên tiếng Việt, đồng hạng, bỏ GV ngừng hoạt động.
- Task gắn GV hiện đúng ở hồ sơ và ở trang Công việc.
- Migrate: tạo kho schema 2 (như 1.0.0) → mở bằng code mới → schema 3, dữ liệu cũ nguyên vẹn.
- Sao lưu/khôi phục có `scoreEntries`; khôi phục bản sao lưu schema 2.
- Frontend: `node --check` mọi file JS; cập nhật `tests/check_views.js` để render hồ sơ GV, xếp hạng, khung in không lỗi.
- **Toàn bộ test cũ vẫn pass.** Không giảm số test.

## 4. Quyết định đã chốt (chủ dự án duyệt 07/11/2026)
1. Điểm **không giới hạn** 0–50.
2. Lỗi GV **không** tự trừ điểm, chỉ hiển thị.
3. Lý do +1/−1 là **chữ tự do**.
4. Xếp hạng **chỉ GV đang dạy/đang hoạt động**.

## 5. Quy trình làm & bàn giao
1. `git checkout phat-trien && git pull`.
2. Làm theo thứ tự, mỗi bước một commit rõ ràng (tiếng Việt): (a) store/migrate + service + metrics + test backend; (b) hồ sơ GV + task; (c) xếp hạng; (d) xuất PDF; (e) version 1.1.0 + tài liệu.
3. Chạy toàn bộ test sau mỗi bước. Push lên `phat-trien`.
4. **Build DMG 1.1.0**: chạy workflow **Build Mac app** trên nhánh `phat-trien` (`gh workflow run build-mac.yml --ref phat-trien`, **không** bật `release`). Chờ run xong, xác nhận thành công và artifact `ToolThu-mac-arm64` chứa `ToolThu-1.1.0-mac-arm64.dmg`. Workflow cũng chạy toàn bộ unittest trên macOS — nếu fail thì sửa rồi chạy lại.
5. Nếu không có quyền chạy workflow: dừng ở đây và báo để chủ dự án tự bấm Actions → Build Mac app → Run workflow (chọn nhánh `phat-trien`).
6. Báo cáo cuối: danh sách commit, số test pass, link run build, những gì chưa làm được/giả định đã dùng.

Không được: sửa nhánh `ban-1.0.0`/`main`, tạo tag/Release, thêm dependency runtime, gọi Google/iCloud thật, commit dữ liệu thật.
