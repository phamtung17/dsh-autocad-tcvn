# Sinh bản vẽ mới — 1.3.0-local

Đường `cad_fitout_*` tạo hình học mới từ thông số studio; không đọc hay sao chép
hình học trong thư mục tham chiếu. `cad_reference_*` vẫn chỉ phát hành lại thiết kế cũ.

11 tờ: danh mục, mặt bằng nội thất, vách, sàn, trần/đèn, điểm điện, mặt đứng bếp,
mặt đứng đầu giường, cấu tạo chân tường/trần, cấu tạo khu ướt, bảng vật liệu/thống kê.
Có kích thước thật, hatch, leader, block nội thất/ký hiệu, nhiều viewport theo tỷ lệ.
Xuất native dùng AutoCAD 2025, tạo bảng ACAD_TABLE có thể sửa, DWG và PDF A3.

1. `cad_fitout_example`: xem thông số demo đầy đủ; dự án thật phải thay bằng số liệu đã chốt.
2. `cad_fitout_plan(spec, branding)` kiểm tra đầu vào và danh mục.
3. `cad_fitout_preview(spec, branding)` tạo PDF vector/DXF để rà soát.
4. `cad_fitout_prepare` đóng băng thông số và hash logo.
5. Người dùng chạy lệnh `approve-design` được trả về; `cad_fitout_export(ticket)`
   dùng vé một lần để xuất native. Không sửa file nguồn hoặc ghi đè dự án trước.

Mặc định tạm thời tên công ty, logo chữ và liên hệ là **boyxpxt.io.vn**.
Khi xuất dự án thật, hỏi lại khung tên và logo; chỉ đặt `branding.confirmed=true`
sau khi người dùng chốt. Không xem lựa chọn tạm này là xác nhận cho hồ sơ thật.
Các trường: company, wordmark, owner, designer, checker, revision, project_code,
contact, logo_asset, column_width (58–70 mm).

Logo PNG/JPG/DXF được đăng ký cục bộ bằng `branding.register_asset` sau khi người
dùng cung cấp đường dẫn. Asset được sao chép và kiểm hash. Logo raster đi kèm thư
mục assets. Khung DXF chỉ hỗ trợ nền nét trống A3 theo lưới cột phải của bộ sinh;
chưa hỗ trợ tự suy luận ô khung tên bất kỳ đã điền sẵn.

Giới hạn: đây là thư viện studio có tham số, chưa phải hệ thiết kế tùy ý cho mọi
công trình. Phụ kiện và bố trí demo có mặc định thư viện; điểm điện không có tính
toán tải, cấu tạo phải được chuyên gia dự án rà soát. Không chứng nhận TCVN hoặc
sẵn sàng thi công. Bản thử kiểm native không thay thế kiểm duyệt kỹ thuật dự án.

CLI thử: `.venv\Scripts\python.exe -m tools.publish_new_design --project-id TEN_MOI`
(chạy trực tiếp có quyền COM; đường MCP vẫn giữ phê duyệt ngoài luồng).
