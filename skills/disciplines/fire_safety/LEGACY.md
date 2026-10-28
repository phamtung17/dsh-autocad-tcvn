---
name: autocad-fire-safety-legacy
description: Quy trình vẽ AutoCAD 2025 theo chuyên ngành Phòng cháy chữa cháy, định tuyến tiêu chuẩn Việt Nam và QA.
version: 1.0.0
---

# Phòng cháy chữa cháy — AutoCAD agent

1. Hỏi những thông số bắt buộc theo nhu cầu; không tự bịa tải trọng, công suất, độ dốc, dung sai hay thông số an toàn.
2. Bắt đầu với `cad_template(discipline="fire_safety")` nếu người dùng muốn bản vẽ mẫu; sửa JSON dựa trên dữ liệu thật của dự án.
3. Gọi `cad_catalog(discipline="fire_safety")` để tìm tiêu chuẩn tham khảo; tra cứu hiệu lực và điều khoản từ nguồn chính thức. Không tuyên bố đạt TCVN từ catalog.
4. Chạy `cad_validate` và `cad_preview`, đọc báo cáo, kiểm tra hình học và PDF schematic.
5. Nếu user yêu cầu DWG thật: `cad_prepare`, đưa lệnh approve cho người dùng, sau đó `cad_create_dwg(ticket)`; vẫn cần mở DWG xem trên AutoCAD 2025.
6. Chỉ dùng cho mẫu nguyên lý/concept cho đến khi có dữ liệu tính toán, kiểm tra chuyên ngành và người chịu trách nhiệm phê duyệt.

File pdf preview KHÔNG phải bản in tỷ lệ chính xác; kích thước AutoCAD trong ModelSpace dùng đúng đơn vị và cần kiểm tra thực tế.
