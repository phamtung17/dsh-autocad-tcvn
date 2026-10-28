# Quy tắc kiểm định tiêu chuẩn Việt Nam — chính sách an toàn

Bộ máy hiện tại đọc metadata từ `registry.json`, **không chứa toàn văn tiêu chuẩn có bản quyền** và **không xác nhận tình trạng hiệu lực** theo từng dự án. Chỉ có thể tự động PASS/FAIL những `PROJECT_RULE` do người dùng cấu hình, ví dụ layer, giới hạn tọa độ, độ cao chữ hoặc kích thước tối thiểu. Những con số này **không** được tuyên bố lấy từ TCVN.

## Mức xác minh

1. `CATALOG_ONLY`: có số hiệu/tên/đường dẫn tham chiếu; bắt buộc kiểm tra lại hiệu lực tại ngày áp dụng.
2. `NOT_CHECKED`: không có dữ liệu để kiểm điều khoản hoặc phạm vi không thích hợp.
3. `PROJECT_RULE_PASS/FAIL`: chỉ kiểm tra quy tắc dự án, không chứng nhận theo tiêu chuẩn quốc gia.
4. `CLAUSE_VERIFIED`: trạng thái dành cho quy trình phê duyệt **tương lai**, chỉ áp dụng nếu có văn bản có quyền sử dụng, điều khoản chính xác, phương pháp đo, bằng chứng, phiên bản văn bản và kỹ sư kiểm duyệt. **Không có rule nào mang trạng thái này trong bản phát hành.**
5. `APPROVED_FOR_CONSTRUCTION/MANUFACTURE`: **không do agent tự cấp**; chỉ người/cơ quan có thẩm quyền của dự án quyết định.

## Tuyến ngành

- Cơ khí: bản vẽ chế tạo/chi tiết, dung sai lắp ghép, GD&T và phương pháp ghi kích thước cần kỹ sư cơ khí kiểm tra.
- Kiến trúc: tiếp cận, thoát nạn, công năng và trình bày bản vẽ cần chuyên gia có thẩm quyền.
- Kết cấu: tải trọng, cấu kiện, bê tông, cốt thép, cấu tạo liên kết cần tính toán và ký duyệt.
- Điện: bảo vệ, ngắn mạch, cáp, nối đất và tiêu chuẩn theo phần/năm phải đối chiếu thiết kế cụ thể.
- HVAC, cấp thoát nước, PCCC: lưu lượng, áp suất, độ dốc, các thông số an toàn và bố trí thiết bị chỉ kiểm được nếu có cơ sở tính toán.
- Hạ tầng: hệ tọa độ, cao độ, hình học tuyến, tính toán và dữ liệu khảo sát phải được xác nhận.

Không được dùng bản vẽ schematic hoặc DXF/PDF preview làm hồ sơ thi công chỉ vì `cad_validate` trả về `PASS`.
