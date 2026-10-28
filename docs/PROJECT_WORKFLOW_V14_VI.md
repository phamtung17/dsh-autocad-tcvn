# Bộ hồ sơ 14 bước — v1.4.0-local

Đây là đường sinh bản vẽ **mới** từ mô hình chung; không lấy hình học từ DWG
tham chiếu. Thư viện thể hiện bổ sung kích thước, trục, cao độ, hatch vật liệu,
leader, ký hiệu, bảng native, chi tiết phóng to, tham chiếu giữa các tờ, trần/sàn
và bản vẽ theo từng tầng. Tên/logo chữ tạm thời: **boyxpxt.io.vn**.

## Phạm vi đã triển khai

Bộ sinh mẫu nhà chữ nhật 1–3 tầng, rộng 9–12 m, sâu 7–14 m, dùng dữ liệu đầu vào
rõ ràng. Ví dụ hai tầng tạo **58 tờ A3**:

| Bước | Nội dung bản vẽ |
|---|---|
| 1 | Ranh, mốc, điểm khảo sát và mặt cắt từ điểm được cấp |
| 2 | Tổng mặt bằng, hướng Bắc, gốc tọa độ và bảng định vị trục |
| 3 | Kiến trúc từng tầng: tường, ô mở, cửa, thang, thiết bị, kích thước |
| 4 | Bốn mặt đứng và mặt cắt qua các tầng; cao độ dùng cùng mô hình |
| 5 | Mái, độ dốc đầu vào, thoát mái, tường chắn và tham chiếu chi tiết |
| 6 | Bậc/thang, cửa và khung cửa, chống thấm, phễu, mép mái |
| 7 | Móng, dầm sàn từng tầng, móng chi tiết, dầm/cột 1:5, bản sàn, thép thang |
| 8 | Cấp/thoát từng tầng, trục đứng, van/bẫy nước và ghi đường kính/cao độ |
| 9 | Đèn, ổ cắm từng tầng, sơ đồ đơn tuyến và tiếp địa |
| 10 | Mạng/camera, tuyến điều hòa từng tầng, lắp đặt và thoát ngưng |
| 11 | Nội thất từng tầng, tủ bếp, vệ sinh, sàn và trần từng tầng |
| 12 | Cây xanh, lát sân, định hướng thoát nước, hố ga |
| 13 | Khối lượng tính từ mô hình, đơn giá được cấp, hạng mục bổ sung/phạm vi loại trừ |
| 14 | Phối hợp, danh mục đầy đủ kể cả các trang danh mục, revision và kiểm tra bàn giao |

Thay đổi số tầng hoặc số dòng dự toán sẽ thay đổi số tờ; bảng dài tự chia trang.
Tuyến cấp/thoát có nhánh đến thiết bị từ cùng mô hình dùng cho khối lượng.
Các tuyến mạch điện và nhánh DATA/CAM cũng được dùng chung cho bản vẽ/QA/khối lượng.
Chiều dài ống điện và mạng trong demo giả định ống riêng từng tuyến; không tự gộp
ống chung hoặc quy đổi thành tổng chiều dài lõi dây/cáp. Vị trí thiết bị, đường đi
và đường kính nhánh là đề xuất thư viện cần người thiết kế kiểm tra.

Một tờ xuất native phải qua kiểm tra DIMENSION, HATCH, ACAD_TABLE, số viewport,
tỷ lệ viewport, audit DXF và khổ PDF A3. Kiểm tra này xác nhận việc xuất bản vẽ,
không thay thế kiểm duyệt thiết kế.

## Quy trình MCP

1. `cad_project_catalog()` xem giai đoạn, điều kiện và giới hạn.
2. `cad_project_example()` xem schema. Không dùng số liệu demo làm dữ liệu thật.
3. `cad_project_plan(spec)` lập danh mục, hình học và khối lượng.
4. `cad_project_check(spec)` kiểm thiếu tờ/tầng/chi tiết, tham chiếu hỏng, bản vẽ
   cũ so với đầu vào, review hết hiệu lực, lỗi độ dốc và xung đột được mô hình hóa.
5. `cad_project_preview(spec, branding)` xuất PDF vector/DXF để xem bố cục.
6. Sửa theo `repair_queue`, rồi chạy lại kiểm tra. Khi sửa đầu vào,
   `cad_project_change_impact(before, after)` chỉ ra bước trực tiếp và các bước
   hạ nguồn cần làm lại. Thay đơn giá ảnh hưởng bước 13–14; đổi hình học ảnh hưởng
   các bộ môn phụ thuộc; đổi revision yêu cầu cập nhật tất cả.
7. `cad_project_prepare` đóng băng mô hình, mã bộ sinh và hash logo. Có lỗi hình
   học/phối hợp thì chặn. Dự án thật phải hỏi lại khung tên/logo và xác nhận chúng.
8. Người dùng chạy CLI `approve-design` được trả về. `cad_project_export(ticket)`
   dùng vé một lần, xuất DWG/PDF mới; không sửa thư mục tham chiếu.
9. `cad_project_verify_delivery(project_id)` đối chiếu SHA256; thiếu/sửa file làm
   bàn giao bị chặn. File xuất gồm danh mục CSV, khối lượng/chi phí CSV, QA và manifest.

Ví dụ CLI thử cục bộ, dùng dữ liệu DEMO:

```powershell
.\.venv\Scripts\python.exe -m tools.publish_new_design --input examples\building_fourteen_stages.json --project-id ten_demo_moi
```

## Dữ liệu và kiểm duyệt

`site`, `building`, `structure`, `finishes`, `systems` và `prices` là dữ liệu dùng
chung. Không có phép tự chọn móng/thép/CB/tiết diện dây/đường kính ống từ văn bản
mơ hồ. Bố trí phòng, phụ kiện, thiết bị và một số cấu tạo trong thư viện còn dùng
mẫu cố định; schema sẽ từ chối giá trị không phù hợp mẫu.

Nguồn khảo sát, kết cấu, MEP và đơn giá phải ghi trong `source`. Các thông số demo
được in với trạng thái DEMO. Khảo sát là biểu diễn dữ liệu được cung cấp; plugin
không đi khảo sát hiện trường hoặc tự dựng mô hình địa hình TIN từ vài điểm.

`reviews` nhận tên người rà soát, mã bằng chứng và hash đầu vào từng giai đoạn.
Đó là **khai báo do người dùng cung cấp**, không phải chữ ký pháp lý đã được AI
xác minh. `READY_FOR_HUMAN_RELEASE` chỉ cho phép trình người có trách nhiệm phát hành.
Xuất bộ DEMO/review không chuyển nó thành hồ sơ được phép thi công.

## Giới hạn thực tế

- Chưa sinh tùy ý mọi công trình, hình khối, phương án mặt bằng hoặc mọi chuyên ngành.
- Chưa có phân tích kết cấu/địa kỹ thuật, chọn thép theo tải trọng, tính thủy lực,
  phối hợp bảo vệ điện, tính tải lạnh, thiết kế PCCC hoặc chứng nhận TCVN.
- Phối hợp kiểm hộp bao tuyến 3D với cột/dầm/sàn và độ dốc thoát trong mô hình;
  đây là phép kiểm bảo thủ, chưa là clash BIM toàn bộ. Lỗ xuyên/sleeve và hệ chưa
  mô hình hóa phải được người thiết kế phối hợp thêm.
- Khối lượng bê tông tách phần bản/dầm/cột để tránh đếm chồng, sàn hoàn thiện trừ
  ô thang/vách. Các cấu kiện hoặc phụ kiện ngoài mô hình không tự có khối lượng.
- Dự toán ghi rõ `estimate_scope`: thêm dòng có cơ sở, đơn giá, phần loại trừ và
  xác nhận phạm vi. Không mặc định CSV một số hạng mục là dự toán trọn công trình.
- Phong cách tham chiếu là mục tiêu thể hiện; số tờ lớn hoặc có đủ loại entity
  không tự chứng minh đã chi tiết bằng mọi hồ sơ tham chiếu ở mọi bộ môn.

Bản nâng cấp này không sửa hay xuất lại thiết kế trong thư mục tham chiếu; phần
`cad_reference_*` vẫn là luồng riêng để phát hành lại thiết kế cũ khi được yêu cầu.


## Tái kiểm chứng đầu ra và sửa từng tờ

`python -m tools.verify_building_output PROJECT_ID` đọc lại tất cả native DXF/PDF,
đối chiếu tọa độ line/polyline/circle/arc/block, hình học block, kích thước và tỷ lệ
với mô hình hiện tại. Sau đó phải xem PDF; kiểm số lượng entity không thay cho
kiểm tra trình bày hoặc kiểm duyệt chuyên ngành.

CLI tin cậy có `publish_new_design --sheets LV-101,LV-102` để dựng lại tờ chọn
lọc. Đầu ra này bị ghi rõ PARTIAL và không được bàn giao như bộ đầy đủ.
`tools.merge_native_revision BASE REVISION TARGET` chỉ ghép khi dữ liệu/khung tên
không đổi, tạo thư mục mới, giữ số thứ tự tờ và kiểm lại toàn bộ bộ hồ sơ theo
mã sinh hiện tại trước khi tạo manifest. Đường MCP xuất dự án vẫn xuất toàn bộ.

Sau khi cập nhật mã nguồn đang chạy, nạp lại MCP hoặc mở phiên Codex mới để
Python dùng các bản sửa cuối thay cho module đã nạp trong bộ nhớ.
