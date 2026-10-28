# Chính sách quyền riêng tư — Tool Thư

*Privacy policy — Tool Thư (English summary below)*

Tool Thư là ứng dụng quản lý tổ giáo viên chạy **trên máy của người dùng** (macOS/Windows). Ứng dụng không có máy chủ riêng và không gửi dữ liệu cho nhà phát triển hay bên thứ ba.

## Dữ liệu Google mà ứng dụng truy cập

- Quyền duy nhất: **xem Google Trang tính** (`spreadsheets.readonly`), cùng email để hiển thị tài khoản đang kết nối (`openid`, `email`).
- Ứng dụng **chỉ đọc** các bảng tính mà người dùng tự dán link, và **chỉ khi người dùng bấm nút** (Kết nối Google, Nhập từ Google Sheet, Cập nhật dữ liệu). Không đọc ngầm, không sửa, không xóa bảng tính.
- Không đọc Gmail, Google Drive hay dữ liệu Google nào khác.

## Lưu trữ

- Dữ liệu đọc được và thông tin đăng nhập Google (token) chỉ lưu trong thư mục dữ liệu của ứng dụng trên máy người dùng (Mac: `~/Library/Application Support/ToolThu`).
- Không chia sẻ, bán hay chuyển dữ liệu cho ai. Không dùng dữ liệu để quảng cáo hay huấn luyện mô hình.

## Thu hồi quyền

- Trong ứng dụng: **Nguồn dữ liệu → Ngắt kết nối Google** (thu hồi quyền và xóa token trên máy).
- Hoặc trong tài khoản Google: https://myaccount.google.com/permissions

Việc sử dụng thông tin nhận được từ Google API tuân thủ [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), bao gồm các yêu cầu Limited Use.

Liên hệ: https://github.com/truongbinh1302/tool-thu/issues

---

**English summary.** Tool Thư is a desktop app that runs locally on the user's computer. It requests read-only access to Google Sheets (`spreadsheets.readonly`) plus the user's email, reads only spreadsheets the user links, and only when the user clicks a button. Data and tokens are stored only on the user's computer and are never sent to the developer or third parties. Access can be revoked in the app (Disconnect Google) or at https://myaccount.google.com/permissions. Use of information received from Google APIs adheres to the Google API Services User Data Policy, including the Limited Use requirements. Contact: https://github.com/truongbinh1302/tool-thu/issues
