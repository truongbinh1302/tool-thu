# Tool Thư · Mây Teacher Space

**0.4.8 (27/10/2026):** nút **Cập nhật dữ liệu** chạy được trong kho dữ liệu thật. Khi nhập từ Google Sheet, ở bước 3 tick **Lưu làm nguồn để bấm Cập nhật dữ liệu**; từ đó mỗi lần bấm nút, tool đọc lại các sheet đã lưu một lần: thêm dòng mới, cập nhật dòng đã đổi, giữ nguyên dòng bạn đã sửa trong tool, không xóa gì. Nếu cột trong sheet đổi tên/vị trí, tool báo lỗi và giữ dữ liệu cũ. Không có đọc ngầm. Thanh bên cuộn được trên màn hình thấp.

**0.4.7 (27/10/2026):** đọc đúng cột có tiêu đề gộp 2 hàng (vd. Deadline xử lý, PIC, Phương án xử lý) và cột chỉ có dữ liệu ở các dòng sau; tự chọn sheet nhiều dữ liệu nhất; hiện tên sheet đang dùng ở bước ánh xạ.

**0.4.6 (26/10/2026):** kết nối Google Sheets (chỉ xem): ở Nguồn dữ liệu chọn file OAuth client (Desktop app) một lần, bấm **Kết nối Google** để đăng nhập, rồi **Nhập từ Google Sheet** bằng link, qua cùng các bước ánh xạ/xem trước như Excel. Chỉ gọi Google khi bạn bấm nút; token lưu trong thư mục dữ liệu, không nằm trong DB hay bản sao lưu. Hướng dẫn tạo OAuth client: `docs/GOOGLE_OAUTH_SETUP.md`.

**0.4.5 (26/10/2026):** có bản app Mac chip Apple (`Tool Thư.app`, không cần cài Python), build và kiểm thử tự động trên macOS bằng GitHub Actions. Sửa lỗi server mở chậm/treo trên macOS do tra ngược DNS khi khởi động. Không đổi giao diện, schema (vẫn 2) hay dữ liệu.

Bản local 0.4.8 dành cho tổ giáo viên, giao diện hồng pastel. Đây là bản để thử và góp ý trước nghiệm thu; đã đọc được Google Sheets (chỉ xem), chưa kết nối iCloud.

Bản 0.4.4 sửa nhập giờ Excel dạng số, từ chối CSV hỏng/tệp rỗng và phát hiện dòng thiếu ngày, trường quá dài, hạn lớp trước ngày tiếp nhận ngay ở bản xem trước. Ngày Excel ngoài phạm vi báo lỗi dữ liệu. Sửa phản hồi 401/403 đôi lúc bị Windows ngắt kết nối khi POST có body chưa đọc hết; kiểm tra phiên/Origin/CSRF giữ nguyên. Không đổi schema (vẫn 2), thiết kế hoặc cách track thủ công.

Kiểm tra mới ngày 24/10/2026: **70/70 unittest đạt trên Windows 11/Python 3.13.5**, cùng 10 bước tích hợp Windows batch/API, 18 lượt render template và 7 kiểm tra cú pháp JavaScript. Đã nâng từ chính gói 0.4.3, giữ toàn bộ dữ liệu thử/revision; đã đối chiếu backup/restore và kết quả CSV/ICS. Browser localhost bị từ chối quyền: chưa xác nhận UI, ảnh, zoom, DPI 100/125/150%, Mac hoặc Calendar client thật. Xem **qa/ACCEPTANCE-0.4.4.md** và các log đi kèm; chưa đủ điều kiện bàn giao toàn sản phẩm.

Bản 0.4.3 sửa bộ mở để nhận diện đúng phiên bản và thư mục mã. Khi bạn mở bản mới, ứng dụng dừng sạch server cũ của cùng kho dữ liệu rồi mở bản mới; mở lại cùng bản sẽ dùng lại một server. Có nhật ký lỗi khởi động và file **Kiem_tra_Tool_Thu_Windows.bat**. Số phiên bản lấy từ server hiển thị ở cuối giao diện.

Lịch sử 0.4.3: báo cáo trước ghi 55 unittest Windows. Lần 24/10 đã chạy lại 55 ca nền, tất cả đạt trong 26.274 giây, trước khi sửa 0.4.4. Báo cáo nâng 0.4.2 → 0.4.3 cũ được giữ tại `qa/ACCEPTANCE-0.4.3.md`; ca nâng mới dùng gói 0.4.3 → 0.4.4, không nhận kết quả cũ làm kết quả mới.

Bản vá 0.4.2 phục hồi CSS bị hỏng ở đầu file, dùng lại font Be Vietnam Pro/Lora của bản mẫu và đóng gói font offline. Bố cục 761–1000 px cho thẻ số liệu thành hai cột, giữ khoảng trống cho tiêu đề tiếng Việt. Xem `qa/ACCEPTANCE-0.4.2.md` về phạm vi kiểm tra thực tế.

Cập nhật trên Windows: lưu các form đang nhập và tạo sao lưu trong app. Giải nén toàn bộ bản mới vào thư mục mới rồi chạy Mo_tool_Thu_Windows.bat. Bộ mở sẽ chuyển server cũ sang bản trong thư mục vừa mở. Dữ liệu lưu ngoài thư mục mã nên không cần chép/xóa DB. Tải lại các tab đã mở trước đó; phiên đăng nhập local cũ cần tải lại sau khi chuyển server. Chẩn đoán phải báo version 0.4.4 và current: true; footer dự kiến hiển thị Tool Thư 0.4.4, còn chờ xác minh trực quan.

Bản vá 0.4.1 sửa lỗi khởi động trên Windows khi mã hóa mặc định là cp1252: đọc dữ liệu mẫu bằng UTF-8 rõ ràng. Không đổi schema hoặc xóa dữ liệu đã lưu. Nếu đang dùng 0.4.0 và gặp `UnicodeDecodeError`, có thể mở tạm bằng `py -3 -X utf8 start.py --serve --no-browser` tại thư mục tool, rồi mở địa chỉ được hiển thị và giữ cửa sổ máy chủ chạy.

## Yêu cầu mới đã ghi nhận — 20/10/2026

Google Sheets là nguồn chính. Khách chỉ muốn track khi bấm **Cập nhật dữ liệu**, không tự track nền. Calendar cần có nội dung công việc/cuộc họp, thời gian và người tham gia. Xem `docs/CUSTOMER_REQUIREMENTS.md` về phạm vi/tiêu chí nghiệm thu mới.

Bản 0.4.0 đã có nút ở Tổng quan/Nguồn dữ liệu, luồng đọc nguồn giả lập có chủ động, trạng thái/lỗi/hàng chờ đối chiếu, cùng tên người dự kiến tham gia trong lịch và .ics. **Google/iCloud thật vẫn chưa kết nối.** Xem `docs/TRY_MANUAL_TRACK.md` để thử từng bước.

Kiểm tra bản 0.4.2: 48 unittest PASS trên Linux, 18 lượt render template, 7 kiểm tra cú pháp JavaScript và unit điều phối nút. Đã kiểm tra Chrome cloud với dữ liệu giả cho các màn hình/kích thước ghi trong `qa/ACCEPTANCE-0.4.2.md`. Mac/Windows thật, DPI/zoom thật và Apple Calendar client vẫn chưa xác minh đầy đủ.

## Bản app cho Mac (không cần cài Python)

Có bản `Tool Thư.app` đóng gói sẵn cho Mac chip Apple, tải file `.dmg` ở mục Releases. Hướng dẫn cài: `packaging/CAI_DAT_MAC.md`. App ký ad-hoc (miễn phí, chưa đăng ký với Apple), nên lần đầu cần gỡ dấu tải về bằng `xattr` hoặc bấm **Vẫn mở** trong Quyền riêng tư & Bảo mật. Dữ liệu dùng chung thư mục với bản chạy từ mã nguồn.

Build: đẩy tag `vX.Y.Z` lên GitHub, workflow `build-mac.yml` chạy test trên macOS, đóng gói, chạy thử app và gắn DMG vào Release. Build tay trên Mac: `bash packaging/build_mac.sh`.

## Mở ứng dụng

1. Giải nén toàn bộ ZIP. Bạn sẽ có thư mục **tool-thu**. Đặt thư mục ở nơi dễ tìm, ví dụ Documents.
2. Máy cần **Python 3.11 trở lên**, tải từ https://www.python.org/downloads/ nếu chưa có. Windows chọn “Add Python to PATH” khi cài. Bản này chưa đóng gói Python thành ứng dụng cài độc lập.
3. Windows: mở **Mo_tool_Thu_Windows.bat**. Mac: mở **Mo_tool_Thu_Mac.command**.
4. Trình duyệt mở trang local. Nếu không tự mở, xem địa chỉ được bộ khởi động hiển thị (thông thường http://127.0.0.1:28765).
5. Ban đầu dùng **Dùng thử**. Chuyển **Dữ liệu thật** ở góc trên để nhập dữ liệu của tổ. Hai kho hoàn toàn riêng.

Không mở `web/index.html` trực tiếp: trang cần máy chủ local. Không chạy bên trong cửa sổ ZIP chưa giải nén.

Mac nếu tệp .command chưa có quyền chạy sau giải nén: mở Terminal tại thư mục và dùng `chmod +x *.command`, sau đó mở lại. Không cần tắt cơ chế bảo vệ hệ điều hành. Có thể chạy trực tiếp `python3 start.py` tại thư mục này. **Chưa kiểm thử trên Mac thật**.

Đóng tab không dừng máy chủ. Dừng bằng **Tùy chỉnh → Dừng Tool Thư** hoặc file **Dung_tool_Thu_…**. Mở lại bộ khởi động để tiếp tục. Mở hai lần sẽ dùng lại phiên đang chạy. Nếu cổng bận, bộ khởi động thử cổng kế tiếp.

## Thử nút track mới

Chọn **Dùng thử → Nguồn dữ liệu → Chuẩn bị / đổi nguồn thử**, chọn tình huống và xác nhận phạm vi. Sau đó bấm **Cập nhật dữ liệu**. Chuẩn bị nguồn, tải lại trang hoặc mở app không tự đọc nguồn. Nguồn A/B có dữ liệu giả của GV001 để thử đổi số liệu, mất quyền/kết nối và mâu thuẫn. Kho thật vẫn dùng nhập file trong lúc chờ Lệnh 12.

## Nên thử theo thứ tự

1. Xem Tổng quan và hồ sơ mẫu. Tạo một công việc, chuyển trạng thái rồi tải lại trang.
2. Sang **Dữ liệu thật**. Thêm giáo viên bằng mã chuẩn hoặc nhập file ở Nguồn dữ liệu.
3. Nhập giáo viên trước → xác minh mã/alias → tạo lớp → nhập chỉ số, lỗi và hồ sơ lớp. Không nhập cả danh sách lỗi toàn hệ thống như danh sách giáo viên tổ.
4. Với Excel: chọn sheet và đúng hàng tiêu đề → ánh xạ cột → kiểm tra bản xem trước → xác minh người chưa khớp mã → xác nhận nhập. Dòng lỗi/chờ đối chiếu không được nhập nếu chưa chủ động chọn nhập riêng dòng hợp lệ.
5. Sửa hồ sơ lớp, phương án/hạn rồi chuyển bước trong cùng lần lưu. Hoàn tất hoặc quay lại bước cần lý do. Ngày tiếp nhận, ngày thi và ngày cập nhật nguồn là các trường riêng.
6. Tạo buổi họp → chọn người mời → điểm danh, đóng góp và link báo cáo. Danh sách được giữ theo từng buổi; thêm giáo viên mới không tự đổi mẫu số của cuộc họp cũ.
7. Vào Báo cáo, chọn tuần, xem số đếm gốc, ghi chú, xuất CSV hoặc in bằng trình duyệt. Chỉ chốt khi đã xác nhận ngưỡng/quy ước tuần tại Tùy chỉnh. Chốt lại tạo phiên bản mới và cần lý do.
8. Tạo sao lưu trước khi nhập nhiều dữ liệu. Thử khôi phục bằng kho dùng thử trước.

Thư mục `examples` có CSV mẫu giả lập. Không nhập dữ liệu minh họa vào kho thật để vận hành. File gốc của khách hàng và mật khẩu không được đưa vào gói bàn giao.

## Cách hiểu số liệu

- Ô trống ≠ 0. `—` nghĩa là chưa có số liệu đủ điều kiện.
- Tổng tỷ lệ = tổng tử số / tổng mẫu số, không phải trung bình các % có mẫu số khác nhau.
- Chỉ có % nguồn nhưng không có số đếm: giữ % để xem, không dùng để tính tổng hoặc khẳng định đạt ngưỡng.
- Một kỳ có cả tổng giáo viên và số liệu từng lớp của cùng người: báo chờ đối chiếu để tránh cộng hai lần.
- Chuyên cần, có làm BTVN, BTVN đạt chuẩn, đạt năng lực BTVN, đạt năng lực và học viên đạt năng lực được lưu riêng.
- Tuần tạm đề xuất thứ Hai–Chủ nhật, giờ Việt Nam. Kho thật chưa có xác nhận quy tắc ban đầu.
- Ngưỡng `>` và `>=` cấu hình riêng. So sánh trước khi làm tròn. Phiên bản báo cáo đã chốt giữ nguyên khi sửa nguồn/ngưỡng.
- Một phần trăm cần ghi rõ đơn vị 0–1 hay 0–100 khi nhập. Không tự đoán đơn vị trộn lẫn.

Các quy định công thức/phạm vi chính thức, mốc 48h/72h/14 ngày, chế tài QC và mẫu báo cáo cuối còn trong `docs/codex/OPEN_RULES.md`. Bản này lưu hạn thủ công và chưa tự đánh giá theo quy tắc chưa xác nhận.

## Lịch

Lịch nội bộ theo UTC+7; hạn công việc và hạn hồ sơ lớp cập nhật theo bản ghi nguồn. Bấm sự kiện liên kết sẽ mở công việc/hồ sơ/buổi họp để sửa đúng nguồn. Hoàn tất/hủy sẽ hủy sự kiện tương ứng; không nhân bản khi đổi hạn.

Sự kiện và `.ics` có nội dung, thời gian và người dự kiến tham gia. Buổi họp giữ danh sách mời theo buổi, cho nhập khách ngoài tổ dưới dạng tên, không tạo giáo viên giả và không tự điểm danh có mặt.

Xuất `.ics` để nhập thủ công vào Calendar. Đây **chưa phải đồng bộ iCloud**. Nhắc trước được ghi trong .ics; tool không tự gửi thông báo hệ thống/email. Sửa/hủy lịch lặp tác động cả chuỗi, chưa hỗ trợ ngoại lệ từng lần. Lặp tháng theo ngày 31 bỏ tháng không có ngày 31; mẫu công việc lặp tháng có quy ước riêng: lấy ngày cuối tháng nếu thiếu ngày.

## Dữ liệu, sao lưu và cập nhật

- Windows: `%LOCALAPPDATA%\ToolThu`
- Mac: `~/Library/Application Support/ToolThu`
- Linux: `$XDG_DATA_HOME/tool-thu`, mặc định `~/.local/share/tool-thu`

`demo.sqlite3` và `real.sqlite3` là hai kho. Không đặt DB vào thư mục source để tránh mất khi cập nhật. Sao lưu nhất quán dùng SQLite backup, có checksum/chế độ/schema trong tệp `.thubackup`. Khôi phục chỉ nhận đúng chế độ, kiểm tra trước khi ghi và giữ tệp `*-before-restore-*.thubackup`. Trước nhập có tệp `*-before-import-*` trong thư mục dữ liệu. Các bản này chưa tự dọn theo thời gian.

Bản sao lưu chứa dữ liệu hồ sơ của kho đang chọn; giữ ở nơi riêng. Chỉ chuyển file cho người cần dùng. Không coi thư mục source là bản sao lưu dữ liệu vận hành.

Cập nhật: sao lưu → dừng ứng dụng → thay thư mục mã bằng bản mới → mở lại. Dữ liệu giữ ngoài thư mục mã. Muốn quay lại sau thay schema, giữ cả mã cũ và bản dữ liệu trước migration; không chép đè DB khi máy chủ còn chạy.

## Khi có lỗi

- Mở **Kiem_tra_Tool_Thu_Windows.bat** để xem phiên bản, Python, vị trí mã/dữ liệu và server đang chạy. `current: true` nghĩa là server khớp bản trong thư mục này. File này chỉ kiểm tra, không mở server hoặc đổi dữ liệu.
- Lỗi khởi động được lưu tại thư mục dữ liệu, file `startup.log`. Bộ mở hiển thị đường dẫn chính xác khi lỗi. Log chỉ ghi trạng thái/loại lỗi, không ghi nội dung hồ sơ. Không cần xóa dữ liệu để sửa lỗi mở app.
- Thông báo phiên cũ chưa dừng: chờ thao tác đang xử lý hoàn tất rồi mở lại. Bộ mở không ép tắt tiến trình hoặc mở chồng lên kho đang dùng.

- “Thiếu Python”: cài Python 3.11+; kiểm tra `python --version` (Windows) hoặc `python3 --version` (Mac).
- “Dữ liệu đã thay đổi”: có tab/thao tác khác vừa lưu. App tải phiên bản mới; kiểm tra lại nội dung form rồi lưu lại. Không tự ghi đè.
- “Kết nối gián đoạn”: mở lại app, xem dữ liệu đã lưu trước khi thử lại. Mỗi yêu cầu ghi có mã chống ghi lặp.
- “Kho dữ liệu đang bận/không ghi được”: kiểm tra phiên app khác, quyền thư mục và dung lượng. Không xóa DB để sửa lỗi.
- “Bản xem trước hết hạn”: chọn và xem trước file lại (giữ 20 phút).
- File `.xls`, `.xlsm`, CSV không phải UTF-8, file >20 MB không nhận. Xuất lại `.xlsx` hoặc CSV UTF-8 trên bản sao nguồn.
- Cột giờ XLSX hỗ trợ giá trị số Excel từ 00:00 đến 23:59; cột giờ văn bản dùng HH:MM. Giờ có giây cần đổi thành giờ/phút trước khi nhập. Ô ngày bắt buộc trống và trường vượt độ dài được báo theo dòng ngay ở bản xem trước; có thể xác nhận chỉ nhập dòng hợp lệ.
- Workbook có công thức không cache: mở/lưu bản snapshot có kết quả trong công cụ bảng tính hoặc lấy nguồn số đếm phù hợp. Tool không chạy IMPORTRANGE hay đọc tài khoản trong file.
- Mã có số 0 đầu cần ở dạng chuỗi hoặc định dạng Excel `000…`. Nếu nguồn đã biến `00123` thành số `123` không có định dạng, tool không thể đoán lại mã gốc.
- Không tự mở URL ngoài để kiểm tra link báo cáo; app chỉ lưu URL http/https hợp lệ.

## Dành cho Codex tiếp tục

Đọc `AGENTS.md`, `docs/codex/AGENTS.md`, `docs/codex/WORKLOG.md`, `qa/ACCEPTANCE-0.4.md` và `docs/TRY_MANUAL_TRACK.md`. Lệnh 12 vẫn DEFERRED. Không triển khai tài khoản thật trước khi có yêu cầu riêng.

Chạy kiểm tra trong thư mục này:

```sh
python3 -m unittest discover -s tests -v
python3 verify_package.py
```

Windows dùng `py -3` thay `python3`. Kiểm tra cú pháp frontend bằng `node --check web/<tên-file>.js` nếu máy phát triển có Node; **Node không cần để chạy app**.

Chạy dev có output lỗi: `python3 start.py --serve --no-browser`. DB thử riêng: `python3 start.py --data-dir /đường/dẫn/thử --no-browser`. Máy chủ chỉ nghe `127.0.0.1` và không mở LAN.
