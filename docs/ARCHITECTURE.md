# Nền local

HTML/CSS/JavaScript không framework, giữ CSS/SVG từ prototype Mây `d50fb57`. Bản local ở thư mục riêng; không sửa Site hoặc audience.

`start.py` kiểm tra Python, chọn thư mục dữ liệu người dùng, health/single-instance/lock và port. `thu/server.py` phục vụ static và API loopback; session HttpOnly/SameSite + CSRF/Origin/Host trên ghi. Không CORS hoặc request logging chứa nội dung người dùng.

`thu/common.py`: Clock và validation. Ngày nghiệp vụ YYYY-MM-DD theo UTC+7; timestamp ISO UTC. Demo cố định, real dùng giờ thật. `service.py`: duy nhất nơi sở hữu các thay đổi nghiệp vụ. `metrics.py`: duy nhất nơi tính tổng, trạng thái và kỳ báo cáo; frontend và CSV dùng cùng kết quả. `calendar_service.py`: buổi họp/lịch/.ics; `adapters.py`: contract và fake adapter, không gọi mạng.

`store.py` dùng SQLite schema 2, FK, unique, revision optimistic và request ledger. Mỗi lần ghi aggregate nhỏ (~20–30 GV) trong một transaction, các bảng quan hệ và JSON payload giữ chi tiết linh hoạt. Hiện đọc/ghi aggregate cả kho; phù hợp quy mô local nhỏ, chưa tối ưu cho hàng trăm nghìn quan sát hoặc nhiều người dùng đồng thời.

`importer.py`: ZIP/XML XLSX + CSV bằng thư viện chuẩn, giới hạn dung lượng/hàng/cột/ô; không đánh giá công thức, không truy cập relationship external. Workbook và preview chỉ giữ tạm trong bộ nhớ 20 phút; DB giữ dữ liệu hợp lệ/provenance và batch. Cột có nhãn đăng nhập bị che, nội dung có dấu hiệu secret bị ẩn. Đây không phải công cụ lọc dữ liệu nhạy cảm tổng quát: người nhập vẫn cần kiểm tra nguồn/preview.

`web/core.js`: API, hàng đợi ghi, mã chống retry, focus/modal và định dạng. `views.js`: trình bày. `forms.js`: form nghiệp vụ. `import.js`: wizard ba bước. `app.js`: điều phối sự kiện, bootstrap và mode. localStorage chỉ nhớ chế độ; không chứa dữ liệu nghiệp vụ.

Không có dependency pip/npm cho runtime. Kiểm thử phát triển có Python unittest và Node (cú pháp/template). Bộ khởi động cần Python 3.11+. Chưa có installer/binary macOS/Windows tự chứa runtime.

Restore kiểm tra archive, checksum/schema/mode/integrity/FK, giữ bản hiện tại rồi ghi trạng thái phục hồi trong transaction. Không chép DB đang chạy. Revision luôn tăng. Import có backup trước ghi. Chưa có rollback chọn riêng một batch sau khi đã có nhiều sửa tay; dùng restore toàn kho từ bản phù hợp và bảo toàn dữ liệu mới bằng backup.


## Bổ sung 0.4.0

`thu/tracking.py` điều phối một lượt đọc thủ công; `FakeSheetsSourceAdapter` chưa gọi mạng. Service khởi tạo adapter nhưng không đọc khi bootstrap/snapshot/đổi trang. Chỉ POST `/api/tracking/run` với session/Origin/CSRF và request ID mới gọi đọc các nguồn đã chọn. Giữ khóa một lượt/mode; đọc trước transaction; ghi dùng revision CAS. Retry request đã commit trả kết quả lưu và không đọc lại. Lỗi một nguồn không xóa cache; nguồn hợp lệ có thể áp dụng, kết quả PARTIAL nêu rõ nguồn lỗi.

Lượt đọc tái dùng parser/validation/importer; phát hiện hai nguồn mâu thuẫn và sửa tay local so với checkpoint lần trước. Review queue trong preferences có đối chiếu local/nguồn; áp dụng nguồn cần lý do và kiểm tra phiên bản giá trị hiện tại; giữ local được nhớ khi hai phía chưa đổi. Số lượt lưu gần nhất 20, hàng chờ tối đa 200 pending, 30 quyết định đã xử lý gần nhất. Không polling, không thread lịch nguồn, không tự đọc khi đăng nhập. Nền hiện chỉ có profile nguồn giả lập chỉ số GV001; connector Sheets và profile dữ liệu thật ở Lệnh 12.

`web/tracking.js` sở hữu nút, lựa chọn nguồn, trạng thái đang chạy, retry ID và hàng chờ; module không gọi API đọc dữ liệu nguồn khi load. Không nhầm nút refresh state local với đọc nguồn ngoài. Kho real chưa kết nối và không nhận fixture demo.

`calendar_events` chiếu dữ liệu cuộc họp cũ/mới ra lịch mà không ghi DB hoặc đọc nguồn. `participantNames`, `externalGuests` và snapshot `teacherCodes` là trường JSON bổ sung, không đổi schema 2. ICS đưa người dự kiến vào DESCRIPTION, không ATTENDEE/REQUEST. Người trùng tên được phân biệt bằng mã; không tạo hồ sơ GV cho khách ngoài. Điểm danh vẫn riêng biệt.
