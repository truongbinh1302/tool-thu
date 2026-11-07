# Yêu cầu 07/11/2026 — Đánh giá nhân viên (bản 1.1.0)

Nguồn: buổi họp gần nhất với khách, chủ dự án ghi nhận ngày 07/11/2026. Làm trên nhánh `phat-trien`. Nhánh `ban-1.0.0` là bản đã bàn giao, **không sửa**.

Đọc trước: `AGENTS.md`, `docs/CUSTOMER_REQUIREMENTS.md`, `docs/ARCHITECTURE.md`. Giữ giao diện hồng hiện có. Repo public: không commit dữ liệu khách.

## Yêu cầu gốc của khách (giữ nguyên ý)

1. Thang điểm **50 / 1 quý**.
2. Nhập thủ công: có 2 lựa chọn **+1** và **−1** để Thư tự nhập.
3. Tổng hợp **tất cả thông tin** của từng nhân viên: mọi thông tin và deadline liên quan tới nhân viên đó. Có chỗ **nhập task thủ công** để Thư tự thêm task cho nhân viên đó.
4. Nút **xuất PDF**: báo cáo chi tiết riêng cho từng nhân viên, và báo cáo tổng quát cho tất cả nhân viên. **Xếp hạng** nhân viên theo điểm từ cao xuống thấp.

"Nhân viên" = giáo viên trong danh sách tổ ("Danh sách GV TT", trang Đội ngũ giáo viên).

## Cách hiểu dùng để triển khai (mặc định, đổi được)

### Điểm quý
- Mỗi GV bắt đầu mỗi quý với **50 điểm**. Quý theo lịch: Q1 = T1–T3, Q2 = T4–T6, Q3 = T7–T9, Q4 = T10–T12 (khớp cách đếm quý của tab Lỗi GV).
- Điểm hiện tại = 50 + tổng các lần +1 − tổng các lần −1 trong quý đó. Sang quý mới tự về 50; lịch sử quý cũ giữ nguyên, xem lại được.
- Mỗi lần +1/−1 là **một bản ghi**: GV, quý, dấu (+1/−1), ngày, lý do (bắt buộc), người nhập (mặc định "Thư"), thời điểm tạo. Sửa/xóa được từng bản ghi; có ghi vào nhật ký thao tác như các bản ghi khác.
- **Không** tự cộng/trừ điểm từ lỗi QC, Lỗi GV, chỉ số hay deadline. Chỉ hiện các thông tin đó cạnh điểm để Thư tự quyết. (Đúng nguyên tắc hiện có: "chưa tự áp dụng chế tài, điểm phạt hoặc xếp loại quý".)
- Không chặn trên/dưới (điểm có thể > 50 hoặc < 0). Xem câu hỏi mở 1.

### Trang hồ sơ nhân viên (tổng hợp)
Mở từ trang Đội ngũ giáo viên (bấm tên GV). Một trang gom đủ, mỗi phần là một thẻ:
- Thông tin GV (mã, thể loại, level, SĐT, email, ngày sinh, trạng thái…) như danh sách tổ.
- **Điểm quý**: điểm hiện tại, nút **+1** / **−1** (mở form nhỏ nhập lý do), lịch sử điểm trong quý, chọn quý.
- **Task của nhân viên** (mới): Thư tự nhập. Trường: tiêu đề, mô tả, hạn (ngày, tùy chọn), trạng thái (Chưa làm / Đang làm / Xong), ghi chú. Thêm/sửa/xóa, đánh dấu xong.
- **Deadline & việc liên quan**: gom từ dữ liệu đã có — lớp 14 ngày (Bộ sheet của tổ), công việc của tôi có gắn GV, hồ sơ xử lý lớp, họp có mời GV, lịch, cùng task thủ công ở trên; sắp theo hạn, tô màu quá hạn / sắp tới hạn (7 ngày).
- Chỉ số CCBTVN, Pass band cao, Lỗi GV theo quý (số lỗi + mức xử lý), lỗi QC nhập tay — lấy từ dữ liệu sẵn có, chỉ đọc.
- Không gọi Google khi mở trang (C03: chỉ đọc nguồn khi khách bấm Cập nhật dữ liệu).

### Xếp hạng & xuất PDF
- Trang/thẻ **Xếp hạng quý**: bảng tất cả GV đang dạy, sắp **điểm cao → thấp**; cùng điểm thì xếp theo tên (A–Z). Cột: hạng, GV, điểm, số lần +1, số lần −1, số lỗi GV trong quý, số task chưa xong / quá hạn.
- **Xuất PDF từng nhân viên**: nút trên trang hồ sơ → báo cáo chi tiết của GV đó trong quý đang chọn (thông tin, điểm + lịch sử +1/−1 kèm lý do, task, deadline, chỉ số, lỗi).
- **Xuất PDF tổng quát**: nút trên trang Xếp hạng → bảng xếp hạng toàn tổ + tóm tắt từng GV (1–2 dòng/GV).
- Đầu báo cáo: tên tổ/Thư, quý, ngày xuất. Tên file gợi ý: `BaoCao_<TenGV>_<2026-Q4>.pdf`, `XepHang_To_<2026-Q4>.pdf`.
- Cách làm đề xuất: trang in riêng + CSS `@media print`, mở hộp thoại in của trình duyệt để "Lưu dưới dạng PDF" — không thêm thư viện vào gói PyInstaller. Nếu dùng thư viện tạo PDF phía Python thì phải chạy được trong bản đóng gói Mac (arm64) và có test frozen. Tiếng Việt có dấu phải hiển thị đúng.

## Dữ liệu & kỹ thuật
- Lưu trong kho local hiện có (`thu/store.py`), thêm bảng/collection: `scoreEntries`, `teacherTasks`. Có migrate cho kho cũ (bản 1.0.0 mở lên không lỗi, không mất dữ liệu).
- Sao lưu / khôi phục / kho dùng thử / đặt lại phải bao gồm 2 loại dữ liệu mới.
- Xuất CSV (nếu tiện): lịch sử điểm quý.
- Tăng phiên bản lên **1.1.0** (hiện ở cuối trang và trong Info.plist khi build).

## Nghiệm thu (tối thiểu)
- Unit test: tính điểm theo quý (50 ± bản ghi, sang quý mới về 50, sửa/xóa bản ghi), xếp hạng (giảm dần, hòa điểm theo tên), task CRUD, migrate kho 1.0.0, sao lưu/khôi phục có dữ liệu mới.
- UI: +1/−1 bắt buộc lý do; trang hồ sơ hiện đủ các thẻ; quá hạn tô màu; in/xuất PDF từng GV và tổng quát, kiểm tra dấu tiếng Việt và ngắt trang.
- Toàn bộ test cũ vẫn pass; build Mac (`.github/workflows/build-mac.yml`) thành công.

## Câu hỏi mở (hỏi Thư, chưa chặn việc làm)
1. Điểm có giới hạn 0–50 không, hay được vượt 50 / xuống dưới 0? (Mặc định: không giới hạn.)
2. Lỗi GV (nhắc nhở/cảnh cáo/trừ công) có tự trừ điểm không? (Mặc định: không, chỉ hiển thị.)
3. +1/−1 có cần chọn "loại lý do" cố định (vd: chuyên cần, BTVN, lỗi QC…) hay chỉ ghi chữ tự do? (Mặc định: chữ tự do.)
4. Xếp hạng chỉ GV "Đang dạy" hay cả GV đã nghỉ trong quý? (Mặc định: chỉ Đang dạy.)
