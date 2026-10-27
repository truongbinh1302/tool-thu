# Tạo OAuth client Google cho Tool Thư (làm một lần, miễn phí)

Tool Thư đọc Google Sheets bằng quyền **chỉ xem** (`spreadsheets.readonly`). Để Google cho phép, cần một "OAuth client" loại **Desktop app**. Người tạo (ví dụ Bình) và người đăng nhập dùng tool (Thư) có thể là hai tài khoản Google khác nhau.

## 1. Tạo project và bật Google Sheets API

1. Mở https://console.cloud.google.com, đăng nhập Google.
2. Chọn hộp chọn project ở thanh trên → **New project** → tên `Tool Thu` → **Create**, rồi chọn project vừa tạo.
3. Vào **APIs & Services → Library**, tìm **Google Sheets API** → **Enable**.

## 2. Màn hình xin quyền (Google Auth Platform)

1. Vào **APIs & Services → OAuth consent screen** (giao diện mới tên **Google Auth Platform**) → **Get started**.
2. **App name**: `Tool Thư`; **User support email**: email của bạn → Next.
3. **Audience**: chọn **External** → Next.
4. **Contact information**: email của bạn → Next → đồng ý điều khoản → **Create**.
5. Vào mục **Audience**:
   - Nên bấm **Publish app** (chuyển sang *In production*). Ở chế độ *Testing*, Google buộc đăng nhập lại sau mỗi **7 ngày**.
   - Không cần gửi xác minh. Khi đăng nhập, Google sẽ hiện cảnh báo "Google chưa xác minh ứng dụng này" (xem bước 4), đây là bình thường với ứng dụng dùng riêng.
   - Nếu để *Testing*: thêm email Google của Thư vào **Test users**.

## 3. Tạo OAuth client

1. Vào **Clients** (hoặc **APIs & Services → Credentials → Create credentials → OAuth client ID**).
2. **Application type**: **Desktop app**. Tên: `Tool Thu Desktop` → **Create**.
3. Bấm **Download JSON**. File có dạng `client_secret_….apps.googleusercontent.com.json`.
4. Gửi file này cho máy sẽ dùng tool (máy của Thư). File không chứa mật khẩu tài khoản; chỉ dùng cho Tool Thư.

## 4. Kết nối trong Tool Thư

1. Mở Tool Thư → **Nguồn dữ liệu** → thẻ **Google Sheets** → **Chọn file OAuth client** → chọn file JSON ở trên → **Lưu file**.
2. Bấm **Kết nối Google** → trình duyệt mở trang đăng nhập Google → đăng nhập tài khoản **có quyền xem các Google Sheet cần dùng**.
3. Nếu thấy "Google chưa xác minh ứng dụng này": bấm **Nâng cao (Advanced)** → **Chuyển tới Tool Thư (không an toàn)**. Ứng dụng là của chính bạn nên an toàn.
4. Tick quyền **Xem bảng tính Google Trang tính** → **Tiếp tục**.
5. Trang báo **Kết nối thành công** rồi tự quay lại Tool Thư.
6. Bấm **Nhập từ Google Sheet** → dán link sheet → chọn sheet, hàng tiêu đề, ánh xạ cột → xem trước → tick **Lưu làm nguồn để bấm Cập nhật dữ liệu** → nhập.
7. Lần sau khi sheet có thay đổi: bấm **Cập nhật dữ liệu** (Nguồn dữ liệu → thẻ Chủ động cập nhật khi cần). Tool đọc lại các sheet đã lưu; dòng bạn đã sửa trong tool được giữ nguyên.

## Lưu ý

- Sheet lấy dữ liệu bằng IMPORTRANGE/QUERY từ file khác: tài khoản đăng nhập cần quyền xem **cả file gốc**.
- Tool chỉ gọi Google khi bạn bấm nút (kết nối, đọc sheet). Mở app, tải lại trang không đọc dữ liệu.
- Thông tin đăng nhập lưu ở `google-token.json` trong thư mục dữ liệu (Mac: `~/Library/Application Support/ToolThu`). Không nằm trong DB hay bản sao lưu. **Ngắt kết nối Google** sẽ thu hồi và xóa file này.
- Lỗi "Phiên đăng nhập Google đã hết hạn": bấm **Kết nối Google** lại.
