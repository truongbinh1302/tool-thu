# Tool Thư — BÌNH - BUILD TOOL
Tài liệu nội bộ (docs/codex, qa, RECOVERY_NEEDED) được giữ riêng, không đưa lên repo public. Đọc docs/CUSTOMER_REQUIREMENTS.md và docs/ARCHITECTURE.md trước khi sửa.
Yêu cầu mới nhất cho phép triển khai lần lượt phần độc lập của 01–11; 12 luôn DEFERRED.
Giữ mẫu giao diện hồng. Không kết nối tài khoản thật. Không đưa dữ liệu khách hàng vào Git.
Repo này public: không commit dữ liệu khách, DB, sao lưu, mật khẩu, token, đường dẫn máy cá nhân.
Đóng gói Mac: packaging/ (PyInstaller, ký ad-hoc) và .github/workflows/build-mac.yml.
Mã chạy local tách biệt với Site mẫu, không ghi đè/publish Site.

Đọc docs/CUSTOMER_REQUIREMENTS.md (cập nhật 20/10/2026). C03: chỉ track khi khách bấm nút, không tự fetch/poll/schedule dữ liệu nguồn. C03 thay thế cơ chế tự cập nhật trong ảnh cũ. Tên người trong Calendar không tự cho phép gửi invite.
