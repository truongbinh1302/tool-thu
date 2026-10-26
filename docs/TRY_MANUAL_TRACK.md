# Thử nút Cập nhật dữ liệu — bản 0.4.0

Dùng **kho Dùng thử**. Các nguồn A/B là nguồn giả lập có sẵn trong máy; không đọc Google Sheets hoặc tài khoản thật.

## Thử luồng bình thường

1. Mở Nguồn dữ liệu → **Chuẩn bị / đổi nguồn thử**.
2. Chọn Nguồn thử A → “Đã đổi: 97% / 93% / 90%”, xác nhận phạm vi thử, bấm chuẩn bị. Chỉ số của GV001 chưa đổi ở bước này.
3. Bấm **Cập nhật dữ liệu** tại Nguồn dữ liệu hoặc Tổng quan. Nút báo đang xử lý; lượt hoàn tất mới cập nhật dashboard. GV001 tuần 19/10/2026 có chuyên cần 97%, có làm BTVN 93%, đạt năng lực 90%.
4. Bấm lại: không tạo chỉ số trùng. Mỗi lần đọc hoàn tất có kết quả và lần đọc thành công gần nhất. Ngày demo cố định 19/10/2026 nên timestamp demo không dùng để đo độ trễ thực.
5. Đổi nguồn A sang “Ban đầu” nhưng chưa bấm cập nhật: dữ liệu local vẫn giữ nguyên. Tải lại trang cũng không track. Khi bấm thì nguồn mới được đọc.

## Thử mất kết nối và xung đột

- Chuẩn bị A là “Mất kết nối” hoặc “Hết quyền đọc” → bấm cập nhật: hiện nguồn lỗi, giữ số liệu và mốc thành công cũ. Chuẩn bị lại tình huống hợp lệ rồi chủ động bấm để thử lại.
- Chuẩn bị A “Đã đổi” và B “Mâu thuẫn”, chọn cả hai nguồn → bấm cập nhật: các quan sát xung đột vào **Hàng chờ đối chiếu**, chưa ghi đè local. Mỗi hàng chỉ số chứa 3 loại quan sát riêng.
- Mở hàng chờ, xem local/nguồn, ghi lý do rồi chọn giữ local hoặc áp dụng nguồn đã đối chiếu. Nếu dữ liệu đã đổi sau lúc đưa vào hàng chờ, không cho áp đè từ một bản đối chiếu cũ; bấm track để xem lại.
- Với một nguồn, sau lần track thành công hãy sửa tay số liệu gốc rồi track dữ liệu nguồn khác: giữ local và đưa hàng chờ. Quyết định giữ local được nhớ khi nội dung hai phía không đổi.
- Chọn chỉ một nguồn nếu muốn thử riêng; lối tắt Tổng quan dùng lựa chọn nguồn hiện tại, mặc định là tất cả nguồn đã chuẩn bị trong kho demo.

## Thử lịch và người tham gia

1. Tạo/sửa buổi họp, điền nội dung, ngày giờ/thời lượng, chọn người được mời.
2. Nếu hẹn người ngoài tổ, nhập tên ở **Khách mời ngoài tổ**, mỗi tên một dòng. Không cần tạo hồ sơ giáo viên cho họ.
3. Mở sự kiện từ lịch: buổi họp có danh sách người dự kiến; sự kiện độc lập có trường Người tham gia dự kiến. Tên trùng trong tổ được phân biệt bằng mã GV trong nội dung xuất.
4. Xuất `.ics`: mô tả có nội dung và tên người dự kiến, thời gian bắt đầu/kết thúc theo UTC+7. Đây là file nhập thủ công, chưa phải iCloud sync và không gửi invite. Chưa có bằng chứng mở bản này trong Apple Calendar thật.
5. Đổi người/giờ/nội dung của buổi họp cập nhật cùng sự kiện liên kết; người được mời không tự được điểm danh “có mặt”.

Kho **Dữ liệu thật** chưa kết nối Google; nút sẽ giải thích trạng thái và dẫn sang nhập Excel/CSV. Không đưa nguồn giả lập vào kho thật. Dữ liệu/Calendar thật chỉ làm ở Lệnh 12 khi được giao.

## Kiểm tra tái lập cho Codex

```sh
python3 -m unittest discover -s tests -v
node tests/check_views.js
node tests/check_tracking_ui.js
python3 verify_package.py
```

Node chỉ phục vụ kiểm tra phát triển, không cần để mở ứng dụng. Các ca node là template/unit, không thay thế browser QA.
