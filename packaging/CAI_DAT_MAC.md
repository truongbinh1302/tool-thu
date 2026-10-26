# Cài Tool Thư trên Mac

Dành cho Mac chip Apple (M1, M2, M3, M4…), macOS 11 trở lên. Không cần cài Python.

## Cài lần đầu

1. Mở file `ToolThu-…-mac-arm64.dmg`.
2. Kéo **Tool Thư** vào thư mục **Applications** (Ứng dụng).
3. Mở **Terminal** và chạy lệnh dưới đây một lần. Lệnh này gỡ dấu "tải từ Internet" để macOS cho mở app chưa đăng ký với Apple:

   ```sh
   xattr -dr com.apple.quarantine "/Applications/Tool Thư.app"
   ```

   Cách khác, không dùng Terminal: mở app một lần, macOS báo không mở được → bấm **Xong** → vào **Cài đặt hệ thống → Quyền riêng tư & Bảo mật** → kéo xuống dưới → bấm **Vẫn mở** → nhập mật khẩu máy.

4. Mở **Tool Thư** từ Launchpad hoặc Applications. Trình duyệt sẽ mở trang của tool. Có thể kéo app vào Dock cho tiện.

## Sử dụng hằng ngày

- Mở app: nhấp vào **Tool Thư**. Nếu tool đang chạy, app chỉ mở lại trang trong trình duyệt.
- Đóng tab trình duyệt **không** tắt tool. Tắt hẳn: trong tool vào **Tùy chỉnh → Dừng Tool Thư**.
- Dữ liệu lưu tại `~/Library/Application Support/ToolThu` (không nằm trong app). Xóa hay thay app không mất dữ liệu.
- Nên tạo **sao lưu** trong tool định kỳ và trước khi nhập nhiều dữ liệu.

## Cập nhật bản mới

1. Trong tool: lưu các form đang nhập, tạo sao lưu, rồi **Tùy chỉnh → Dừng Tool Thư**.
2. Mở DMG mới, kéo **Tool Thư** vào Applications, chọn **Thay thế**.
3. Chạy lại lệnh `xattr` ở bước 3 phần cài lần đầu (hoặc bấm **Vẫn mở** một lần).
4. Mở app. Phiên bản hiện ở cuối trang.

## Khi có lỗi

- App báo lỗi khi mở: xem file `~/Library/Application Support/ToolThu/startup.log` và gửi cho người hỗ trợ. Log không chứa nội dung hồ sơ.
- Không xóa thư mục dữ liệu để sửa lỗi mở app.
