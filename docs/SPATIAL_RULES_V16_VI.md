# Quy tắc ràng buộc hình học và bố trí — v1.6 local

Mục tiêu: sinh bản vẽ từ quan hệ tường–ô mở–cửa–phòng–thiết bị, thay vì chèn
các ký hiệu theo những tọa độ độc lập. Đây là **quy tắc hình học của dự án**;
không phải chứng nhận TCVN, tính chịu lực hoặc thẩm duyệt PCCC.

## 1. Hợp đồng dữ liệu

- Mọi tường, ô mở, phòng và vật thể có ID và tầng. Hình học công trình dùng mm.
- Ô mở tham chiếu `host_wall` (tùy chọn khi có đúng một tường khớp). Không khớp
  hoặc có nhiều tường phù hợp thì báo lỗi, không chọn tường bằng phỏng đoán.
- Tường ngoài có ID OUT_W, OUT_E, OUT_S, OUT_N. Tường trong dùng ID partition.
- `position` của opening là đầu khoảng ô mở ở mặt min của dải tường; `width`
  chạy theo trục tường. `vertical` phải khớp hướng tường. `hinge=start|end`,
  `swing=1|-1` chọn đầu bản lề và phía mở; mặc định start/+1 để tương thích.
- Phòng có điểm đại diện trong vùng phòng; có thể khai báo thêm
  `label_zone=[x,y,width,height]`. Không di chuyển vật thể để né lỗi trình bày.
- Vật thể vệ sinh và nội thất tùy chỉnh phải có `host_room`. Phòng phải có
  `usage` (bathroom/bedroom/kitchen/living/hall/technical) và `boundary` hình chữ
  nhật để kiểm phạm vi. Thiết bị vệ sinh phải ở bathroom; giường phải ở bedroom.
  Không đoán công năng chỉ từ vị trí chèn hoặc tên block.
- Kích thước và cao độ của mặt bằng, mặt đứng và mặt cắt lấy từ cùng model.
  Bản DXF cũ không có ID ngữ nghĩa phải ghi rõ phần chưa kiểm được.

## 2. Quy tắc bắt buộc khi sinh bản vẽ

| Nhóm | Quy tắc và cách xử lý |
|---|---|
| Tường–cửa | Đúng một host, song song trục, khoảng cửa nằm trọn trong host |
| Ô chờ | Dùng cùng một khoảng để cắt nét tường **và hatch**; chỉ cắt tường chủ |
| Giao kết cấu | Không đặt ô mở qua cột hay giao vách; báo lỗi để sửa đầu vào |
| Cửa | Bản lề nằm trên mặt tường; cánh đóng và cánh mở chung bản lề/bán kính |
| Quét cánh | Kiểm vùng một phần tư đĩa với tường, đồ, thiết bị và ô thang; không chỉ kiểm đầu cánh |
| Cửa sổ | Lấy cùng khoảng ô mở khi dựng mặt đứng; không chồng cửa sổ/cửa đi khác |
| Vật thể | Kiểm toàn bộ footprint với vách, vật thể khác và ô giữ chỗ; không chỉ kiểm điểm chèn |
| Phòng | Điểm phòng phải ở vùng trống, đi tới được qua các ô mở từ cửa vào tầng/tiếp cận thang |
| Cửa sổ và đường đi | Ô kính không được coi là lối đi; đồ và thiết bị phải nằm trong vùng phòng được khai báo |
| Nhãn phòng | Đặt trong vùng khai báo hoặc ô cục bộ được giới hạn bởi tường; tránh đồ/vách/ô thang và nhãn khác |
| Cỡ chữ | Nhãn phòng dùng 2.5 mm trên giấy; không thu nhỏ vô hạn để nhét nội dung |
| Chú dẫn | Đầu leader phải chỉ đối tượng; ghi chú/chi tiết ở panel đã phân vùng; không ghi đè khung tên |
| Tờ và khung | Kiểm view nằm trong vùng nội dung, không chồng viewport/khung tên, đúng tỷ lệ |
| Kích thước | Đối chiếu giá trị DIMENSION đọc lại; không dùng chữ thay số để che hình học sai |
| Phối hợp | Kiểm đủ tầng/tờ/tham chiếu; kiểm tuyến–kết cấu và độ dốc trong phạm vi model |
| Phát hành | Có lỗi hình học/bố trí thì chặn prepare/export, trả ID và repair_queue; không đổi lỗi thành cảnh báo để xuất |
| Bàn giao | Một DWG chung Model + layout; không tự xuất PDF |

Danh sách mã lỗi và tham số thực thi:
`standards/rules/spatial_geometry_v1.json`. Tolerance tiếp xúc 1 mm trong model.
Quét cánh được xấp xỉ đa giác với độ lệch cung tối đa tolerance/4.
Kiểm đường đi là liên thông hình học, **không** xác nhận bề rộng thông thủy,
chiều dài thoát nạn, tiếp cận người khuyết tật hoặc công năng được duyệt.

## 3. Lỗi trong ảnh BT01 và tình trạng kiểm tra

| Ảnh / vấn đề | Kiểm được | Giới hạn / xử lý |
|---|---|---|
| Bìa chồng chữ/khung | Ước lượng giao text–text, vùng giấy | Cần bố trí lại bìa theo panel, không chỉ đổi font |
| Cửa rời tường, tường xuyên ô cửa | Hướng, vị trí theo phương pháp tuyến, phần tường/hatch còn lại | Chỉ sửa tự động khi có host đủ rõ |
| Cửa đụng cột/giao tường | Kiểm hình học | Giữ lỗi chặn, không tự xóa cột hoặc dịch cửa dọc tường |
| Nội thất/thiết bị chồng | Kiểm footprint với tường và vật thể trong model mới | Legacy DXF kiểm AABB và yêu cầu xác nhận các cảnh báo |
| Mặt đứng/cắt chưa khớp | Model mới dùng chung opening/level; đọc lại native | Legacy thiếu ID mặt bằng–mặt đứng thì NOT_CHECKED, không báo đồng bộ |
| Thang/ô sàn | Vùng giữ chỗ, cánh cửa, liên thông tầng | Chưa kiểm đầu người, lan can, kết cấu thang theo quy chuẩn |
| Các lớp/leader chi tiết | Kiểm panel/khung, rà PNG | Chưa có solver tổng quát cho mọi đường leader và glyph |
| Đường thoát nạn chéo | Không xem một polyline là đường đi đã được kiểm | Phải có dữ liệu phòng/cửa và kiểm chuyên ngành; không phát hành tự động |

## 4. Luồng kiểm tra

`cad_project_catalog` trả rule pack. `cad_project_check` trả thêm `spatial_rules`.
Khi có lỗi, sửa đúng ID/floor trong `repair_queue`, chạy lại check và preview.
`cad_project_prepare`/export thực thi lại gate. Preview mặc định một DXF tổng,
không PDF. Bản native vẫn cần rà hình ảnh và người duyệt chuyên ngành.
Viewport được nhận dạng bằng vị trí/kích thước, ép sang IAcadPViewport rồi bật
Display/khóa tỷ lệ và kiểm ViewportOn, ngay cả khi không in PDF. Native readback
kiểm các ID/trạng thái đã khởi tạo để tránh bàn giao các layout nhập DXF còn trắng.

Đối với DXF cũ, CLI đọc toàn bộ Model và từng layout:

```
python -m tools.audit_spatial_dxf INPUT.dxf --output AUDIT.json
```

`--repair-copy NEW.dxf` chỉ tạo bản sao mới: xoay cửa theo host, căn theo phương
pháp tuyến trong giới hạn đã ghi log và cắt outline/hatch của đúng host. Không
dịch dọc tường, không xóa cửa mồ côi, không tự sửa công năng. Cửa qua cột/giao
tường bị loại khỏi danh sách sửa tự động. Báo cáo trước/sau tách Model/layout;
không cộng hai biểu diễn của cùng một chi tiết để tuyên bố số lỗi độc lập.
Không xuất bản sửa như hồ sơ hoàn chỉnh nếu vẫn còn lỗi chặn.
