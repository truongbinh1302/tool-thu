# Yêu cầu khách hàng — cập nhật 20/10/2026

Bản cập nhật yêu cầu, chưa phải thông báo các kết nối đã hoạt động. Runtime hiện tại là local 0.4.0 (nguồn thử offline); Google/iCloud để Lệnh 12.

## Các quyết định hiện hành

| ID | Yêu cầu | Nguồn / mức xác nhận | Ảnh hưởng triển khai |
|---|---|---|---|
| C01 | Google Sheets là nguồn làm việc chính của khách | Khách nói dùng “gg sheet” trong image(6).png | Ưu tiên luồng đọc Google Sheets ở giai đoạn kết nối. Excel/CSV là nhập snapshot, thử nghiệm và dự phòng. |
| C02 | Calendar phải có nội dung công việc/cuộc họp, thời gian và người tham gia | image(4).png; khách xác nhận cần các thông tin này vì thường có hẹn với người khác | Sự kiện cần tên/nội dung, ngày giờ bắt đầu–kết thúc và danh sách người liên quan. Không chỉ hiện tên lịch và giờ. |
| C03 | Chỉ track khi khách bấm nút; không track tự động | Yêu cầu mới nhất của chủ dự án, 20/10/2026 lúc 14:55 (UTC+7) | Có nút **Cập nhật dữ liệu**. Không polling, lịch chạy nền, theo dõi thay đổi hoặc tự fetch dữ liệu nghiệp vụ khi mở app/đăng nhập/chuyển trang. |
| C04 | Kết nối Google/iCloud thực hiện sau cùng | Quyết định trước đó của chủ dự án, vẫn còn hiệu lực | Cập nhật đặc tả và chuẩn bị/test fake adapter trước; chưa đăng nhập, tạo token hoặc sửa nguồn/lịch thật. |

## Luồng track được yêu cầu

1. Khách cấu hình nguồn Google Sheets và ánh xạ đã xác minh trong giai đoạn được phép kết nối.
2. Khi cần, khách bấm **Cập nhật dữ liệu**; chỉ đọc các nguồn đã chọn và được cấp quyền.
3. Nút hiển thị đang xử lý, chặn nhấn lặp cùng lượt. Đọc → chuẩn hóa → kiểm tra → áp dụng các thay đổi hợp lệ theo chính sách đã xác nhận. Bản ghi/xung đột mới cần đối chiếu vẫn được giữ ở hàng chờ.
4. Sau khi lưu thành công, dashboard/báo cáo hiện dữ liệu mới; thông báo nguồn nào đã đọc, số thêm/sửa/trùng/chờ đối chiếu/lỗi, thời điểm thành công gần nhất.
5. Không bấm thì giữ bản dữ liệu đã lưu. Mở app, tải lại trang hoặc nguồn tự thay đổi không tự khởi động một lượt track.
6. Lỗi mất mạng/hết quyền/nguồn thay cấu trúc: giữ dữ liệu lần thành công trước, báo lỗi và cho bấm thử lại. Retry trong cùng lượt do khách khởi tạo phải hữu hạn và không tạo bản ghi trùng; không biến thành lịch chạy nền.
7. Track dữ liệu nguồn không tự gửi lời mời, email, tin nhắn hoặc ghi ngược Google Sheets. Phạm vi ghi Calendar được cấu hình riêng trong Lệnh 12; không dùng nút track như quyền gửi tới mọi người.

Vị trí đề xuất của nút: Nguồn dữ liệu, có thể thêm lối tắt trên Tổng quan. Đây là lựa chọn giao diện của dự án, khách mới xác nhận cần có nút chứ chưa chốt vị trí/tên nút.

## Nội dung Calendar

- Tên công việc/cuộc họp và mô tả nội dung cần làm.
- Ngày giờ bắt đầu/kết thúc; giữ múi giờ đã cấu hình, thời lượng và nhắc trước khi có.
- Người tham gia/được hẹn. Với họp tương lai, hiển thị danh sách dự kiến; không coi đó là kết quả điểm danh có mặt. Tình trạng tham gia thực tế vẫn thuộc sổ họp.
- Sửa nội dung/giờ/người liên quan phải cập nhật đúng sự kiện đã liên kết, không tạo sự kiện trùng và không ảnh hưởng cuộc hẹn cá nhân khác.
- Hiển thị tên người trong mô tả sự kiện không đồng nghĩa với gửi lời mời Calendar. Gửi invite và quản lý phản hồi chưa được khách yêu cầu.

Bản offline hiện cho nhập tên người ngoài tổ bằng văn bản, hiện danh sách dự kiến, không tích hợp danh bạ hoặc mời họp. Đây là lựa chọn triển khai để thử và có thể chỉnh. Trước kết nối thật, chốt nhu cầu danh bạ/kết quả tham gia và thao tác đẩy Calendar riêng hay gộp track. Không tự suy ra đồng bộ hai chiều.

## Nhật ký thay đổi quyết định

- image(5).png: trao đổi ban đầu đề xuất Sheet thay đổi thì web tự cập nhật, khách trả lời đồng ý.
- **20/10/2026 14:55 UTC+7:** chủ dự án bổ sung khách không muốn track tự động, muốn bấm nút khi cần. **C03 thay thế cơ chế tự cập nhật của image(5).png.** Giữ lại C01 về nguồn Google Sheets và C02 về thông tin Calendar.

## Tình trạng sản phẩm so với yêu cầu mới

| Phần | Hiện tại | Việc còn phải làm |
|---|---|---|
| Excel/CSV local | Có đọc file, mapping, preview và commit | Giữ vai trò snapshot/dự phòng, đối chiếu thêm file thật |
| Track theo nút | Đã triển khai nút + fake adapter, kiểm thử API/unit; không tự đọc nguồn | Kết nối Google thật ở Lệnh 12A, browser QA còn chờ |
| Calendar local / .ics | Có nội dung/giờ/người dự kiến, giữ ID liên kết; test logic/export PASS | Kiểm tra browser và Apple Calendar/iCloud thật còn chờ |
| iCloud trên thiết bị thật | Chưa kết nối | Lệnh 12B và kiểm tra trên Mac/iPhone/iPad thử nghiệm |

## Ca nghiệm thu và trạng thái kiểm tra

- MANUAL-01: mở app/đăng nhập/chuyển trang nhưng không bấm → không có lượt đọc dữ liệu nghiệp vụ từ Sheets.
- MANUAL-02: đổi giá trị trong sheet thử, chưa bấm → dữ liệu local giữ nguyên; bấm một lần → cập nhật đúng phạm vi.
- MANUAL-03: bấm liên tiếp/retry cùng lượt → một lượt đang chạy, không nhân đôi bản ghi.
- MANUAL-04: đọc lỗi/hết quyền → thông báo rõ, giữ thời điểm thành công/dữ liệu cũ; khách bấm thử lại mới khởi tạo lượt tiếp theo.
- MANUAL-05: hai nguồn cùng kỳ có xung đột → hàng chờ, không tự ghi đè hoặc biến thiếu dữ liệu thành 0.
- CAL-DETAIL-01: sự kiện có nội dung, bắt đầu/kết thúc và tên người dự kiến; tên này không biến thành điểm danh “có mặt”.
- CAL-DETAIL-02: đổi người/giờ/nội dung → đúng một sự kiện cập nhật, giữ liên kết, không gửi invite.
- CAL-DETAIL-03: cuộc hẹn có người ngoài tổ → xử lý theo thiết kế đã xác nhận, không tạo giáo viên giả chỉ để lưu tên người hẹn.

Từ build 0.4.0: đã chạy các ca tương ứng bằng fake source/API/unit và dữ liệu Calendar local trong bộ 46 unittest. Điều phối nút cũng có unit test JavaScript. **Google/iCloud thật, browser UI và Calendar client vẫn NOT_RUN/BLOCKED**, không dùng kết quả giả lập để nghiệm thu kết nối thật.
