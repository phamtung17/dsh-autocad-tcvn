# Hồ sơ TCVN/QCVN theo ngành — bản định tuyến, KHÔNG thay thế văn bản chuẩn

Mỗi dự án phải khai báo: loại công trình/sản phẩm, giai đoạn, địa điểm, phiên bản quy chuẩn/tiêu chuẩn trong hợp đồng, nguồn văn bản hợp pháp, ngày đối chiếu, người phê duyệt.

| Ngành | Bộ chuẩn tham chiếu ban đầu | Nội dung phải xác nhận riêng |
|---|---|---|
| Chung | TCVN 7285:2003; 7286:2003; 8-20:2002; 7583-1:2006 | Bố cục, khổ giấy, nét, tỷ lệ, kích thước; yêu cầu đối chiếu văn bản gốc |
| Cơ khí/chế tạo | Nhóm TCVN 8; 7583; 8-44:2003 | Hình chiếu, mặt cắt, dung sai lắp ghép, GD&T, nhám, vật liệu, nhiệt luyện, BOM; chọn đúng TCVN tương ứng theo loại sản phẩm |
| Kiến trúc | TCVN chung; QCVN 06:2022/BXD và sửa đổi nếu áp dụng | Công năng, thoát nạn, tiếp cận, kích thước sử dụng, hồ sơ kiến trúc, giấy phép; không tự suy ra giải pháp PCCC |
| Kết cấu | TCVN 5574:2018; TCVN 2737:2023; TCVN 6084:2012; 6085:2012 | Tải trọng, tổ hợp, bê tông/cốt thép, móng, cấu tạo, thuyết minh tính toán và người chủ trì |
| Điện | TCVN 7447 đúng phần và năm; quy định điện áp/lắp đặt theo dự án | Sơ đồ một sợi, phân phối tải, cáp, bảo vệ, nối đất, ngắn mạch, phân cấp điện; không tự chọn tiết diện/CB |
| MEP HVAC | TCVN/QCVN chuyên ngành được dự án phê duyệt | Lưu lượng, áp suất, thông gió, chống cháy, kiểm soát va chạm, thiết bị, thông số hãng |
| Cấp thoát nước | TCVN/QCVN chuyên ngành được dự án phê duyệt | Cao độ, lưu lượng, độ dốc, thủy lực, điểm đấu nối, kiểm tra xung đột |
| Hạ tầng/giao thông | Tiêu chuẩn ngành, dự án và cơ quan quản lý được xác minh | VN-2000/hệ tọa độ dự án, trắc dọc/trắc ngang, lý trình, cao độ, hành lang an toàn, cấp đường |
| PCCC | QCVN 06 và các sửa đổi, TCVN chuyên ngành theo loại hệ thống | Phân loại nguy hiểm cháy, thiết kế thoát nạn, chữa cháy, báo cháy; bắt buộc chuyên gia phê duyệt |

## Trạng thái kiểm chứng
- `VERIFIED_CLAUSE`: có toàn văn được phép sử dụng + điều khoản chính xác + logic kiểm thử + minh chứng.
- `CATALOG_VERIFIED`: xác minh số hiệu/tên/trạng thái trong danh mục, CHƯA chứng minh nội dung điều khoản.
- `PROJECT_RULE`: quy tắc riêng dự án, không được gắn nhãn TCVN.
- `NOT_CHECKED`: chưa có dữ liệu để kiểm tra.
- `MANUAL_REVIEW`: kỹ sư cần duyệt.
- `FAIL`: kiểm thử có cơ sở không đạt.

## Nguyên tắc quan trọng
TCVN là tiêu chuẩn; QCVN là quy chuẩn kỹ thuật. Tính bắt buộc của tiêu chuẩn tùy luật, viện dẫn, hợp đồng và phạm vi dự án. Không gộp hai loại thành một chứng nhận. Khi có thay thế/sửa đổi, tra cứu lại nguồn chính thức trước khi sử dụng.
