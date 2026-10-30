# Tool Thư — Hướng dẫn cài đặt và sử dụng (Mac)

Dành cho Mac chip Apple (M1, M2, M3, M4…), macOS 11 trở lên. Không cần cài Python.

## 1. Cài lần đầu

1. Mở file `ToolThu-…-mac-arm64.dmg`.
2. Kéo **Tool Thư** vào thư mục **Applications** (Ứng dụng).
3. Mở **Terminal** và chạy lệnh dưới đây một lần. Lệnh này gỡ dấu "tải từ Internet" để macOS cho mở app chưa đăng ký với Apple:

   ```sh
   xattr -dr com.apple.quarantine "/Applications/Tool Thư.app"
   ```

   Cách khác, không dùng Terminal: mở app một lần, macOS báo không mở được → bấm **Xong** → vào **Cài đặt hệ thống → Quyền riêng tư & Bảo mật** → kéo xuống dưới → bấm **Vẫn mở** → nhập mật khẩu máy.

4. Mở **Tool Thư** từ Launchpad hoặc Applications. Trình duyệt sẽ mở trang của tool. Có thể kéo app vào Dock cho tiện.
5. Ở góc trên, chọn **Dữ liệu thật** (kho **Dùng thử** chỉ để xem thử, dữ liệu hai kho tách riêng).

## 2. Kết nối Google (làm một lần)

1. **Nguồn dữ liệu** → thẻ **Google Sheets** → **Chọn file OAuth client** → chọn file `client_secret_….json` được gửi kèm → **Lưu file**.
2. Bấm **Kết nối Google** → đăng nhập tài khoản Google xem được các sheet của tổ.
3. Google báo "Google chưa xác minh ứng dụng này" là bình thường với app dùng riêng: bấm **Nâng cao** → **Chuyển tới Tool Thư (không an toàn)** → tick quyền **Xem bảng tính** → **Tiếp tục**.
4. Trang báo **Kết nối thành công** rồi tự quay lại tool.

Tool chỉ có quyền **xem** bảng tính (không sửa, không xóa, không đọc email hay file khác). Thông tin đăng nhập chỉ lưu trên máy này. Muốn gỡ: **Nguồn dữ liệu → Ngắt kết nối Google**.

## 3. Bộ sheet của tổ (làm một lần)

1. **Nguồn dữ liệu** → thẻ **Bộ sheet của tổ** → **Dán link các sheet**.
2. Dán link 5 Google Sheet:
   - **Danh sách giáo viên** (bắt buộc) — tool dùng trang **"Danh sách GV TT"** làm danh sách chuẩn của tổ.
   - Quy trình xử lý 14 ngày · Quản lý chỉ số CCBTVN · Kiểm soát tỷ lệ Pass band cao · Xử lý lỗi GV.
3. Bấm **Lưu và đọc thử**. Tool tự tìm đúng trang, hàng tiêu đề, cột và báo mỗi sheet có bao nhiêu dòng của tổ.

Các sheet khác chỉ lấy dòng của giáo viên có trong danh sách (khớp theo họ tên).

## 4. Sử dụng hằng ngày

- **Cập nhật dữ liệu** (nút hồng ở Tổng quan, Theo dõi tổ, Nguồn dữ liệu): tool đọc lại các sheet đúng một lần và thay bằng dữ liệu mới nhất. Tool **không tự đọc ngầm** — chỉ đọc khi bấm nút.
- **Tổng quan**: thẻ **Hạn xử lý lớp sắp tới** (deadline 14 ngày, PIC "Ms. Thư"); lớp qua hạn tự ẩn.
- **Theo dõi tổ**:
  - *Quy trình xử lý 14 ngày*: deadline sắp xếp theo ngày, giáo viên, nút **Mở file** quản lý lớp; xem lại lớp đã qua hạn; **Chọn PIC** để thêm/bớt PIC.
  - *Quản lý chỉ số CCBTVN*: mọi cột có thông tin.
  - *Kiểm soát tỷ lệ Pass band cao*: như sheet, đủ các giai đoạn; ô đỏ = tỷ lệ dự kiến dưới ngưỡng ở giai đoạn mới nhất, ô vàng = có đề xuất hỗ trợ; **Đổi ngưỡng** (mặc định 50%).
  - *Xử lý lỗi GV*: chọn quý; số lỗi mỗi giáo viên và mức xử lý (1 nhắc nhở · 2 cảnh cáo · 3 trừ 1/2 công · từ 4 trừ 1 công); danh sách lỗi.
  - *Danh sách GV*: thông tin giáo viên từ sheet. Giáo viên không còn "Đang dạy" chuyển sang Ngừng hoạt động và được ẩn khỏi các bảng.
- Đóng tab trình duyệt **không** tắt tool. Tắt hẳn: **Tùy chỉnh → Dừng Tool Thư**.
- Dữ liệu lưu tại `~/Library/Application Support/ToolThu` (không nằm trong app). Xóa hay thay app không mất dữ liệu.
- Nên tạo **sao lưu** (Tùy chỉnh) định kỳ.

## 5. Khi có thông báo

| Thông báo | Cách xử lý |
|---|---|
| Chưa kết nối Google / phiên đã hết hạn | Nguồn dữ liệu → **Kết nối Google** lại. Dữ liệu cũ vẫn còn. |
| Không thấy bảng "…" trong file này | Sheet đã đổi tên cột/bố cục. Dữ liệu cũ của sheet đó được giữ. Thử **Thiết lập sheet** → **Lưu và đọc thử**; nếu vẫn lỗi, báo người hỗ trợ (nằm trong bảo hành). |
| Không có quyền xem bảng tính | Tài khoản Google đang kết nối chưa được chia sẻ sheet. |
| Mất kết nối mạng | Kiểm tra Internet rồi bấm Cập nhật dữ liệu lại. |

## 6. Cập nhật bản mới

1. Trong tool: tạo sao lưu, rồi **Tùy chỉnh → Dừng Tool Thư**.
2. Mở DMG mới, kéo **Tool Thư** vào Applications, chọn **Thay thế**.
3. Chạy lại lệnh `xattr` ở mục 1 (hoặc bấm **Vẫn mở** một lần).
4. Mở app. Phiên bản hiện ở cuối trang. Dữ liệu, kết nối Google và link các sheet được giữ nguyên.

## 7. Khi có lỗi

- App báo lỗi khi mở: gửi file `~/Library/Application Support/ToolThu/startup.log` cho người hỗ trợ. Log không chứa nội dung hồ sơ.
- Không xóa thư mục dữ liệu để sửa lỗi mở app.
