---
name: autocad-mechanical
description: Quy trình vẽ AutoCAD 2025 theo chuyên ngành Cơ khí / chế tạo, định tuyến tiêu chuẩn Việt Nam và QA.
version: 1.1.0
---

# Cơ khí / chế tạo — AutoCAD agent

1. Hỏi những thông số bắt buộc theo nhu cầu; không tự bịa tải trọng, công suất, độ dốc, dung sai hay thông số an toàn.
2. Bắt đầu với `cad_template(discipline="mechanical")` nếu người dùng muốn bản vẽ mẫu; sửa JSON dựa trên dữ liệu thật của dự án.
3. Gọi `cad_catalog(discipline="mechanical")` để tìm tiêu chuẩn tham khảo; tra cứu hiệu lực và điều khoản từ nguồn chính thức. Không tuyên bố đạt TCVN từ catalog.
4. Chạy `cad_validate` và `cad_preview`, đọc báo cáo, kiểm tra hình học và PDF schematic.
5. Nếu user yêu cầu DWG thật: `cad_prepare`, đưa lệnh approve cho người dùng, sau đó `cad_create_dwg(ticket)`; vẫn cần mở DWG xem trên AutoCAD 2025.
6. Chỉ dùng cho mẫu nguyên lý/concept cho đến khi có dữ liệu tính toán, kiểm tra chuyên ngành và người chịu trách nhiệm phê duyệt.

File pdf preview KHÔNG phải bản in tỷ lệ chính xác; kích thước AutoCAD trong ModelSpace dùng đúng đơn vị và cần kiểm tra thực tế.


## Contract thực thi v1.1 (ưu tiên hơn hướng dẫn chung nếu mâu thuẫn)

- MCP tool thực thi thực tế: `cad_capabilities`, `cad_quality_gate`, `cad_template`, `cad_validate`, `cad_preview`, `cad_plot_plan`, `cad_prepare`, `cad_create_dwg`, `cad_check_clause_rules`, `cad_screen_standards`.
- Chỉ hỗ trợ tạo DWG **mới**; KHÔNG có API sửa bản vẽ hiện hữu, dựng 3D, tính kết cấu, tính an toàn, hoặc chứng nhận TCVN.
- Trước `cad_prepare`, phải qua `cad_quality_gate`. Bản vẽ concept khác hồ sơ thi công/chế tạo.
- Nếu cần PDF đúng tỷ lệ, đặt `plot.enabled=true`, `plot.pdf=true`, kiểm tra kết quả `cad_plot_plan`, rồi thử thật trên AutoCAD 2025. PDF từ `cad_preview` chỉ là sơ đồ KHÔNG đúng tỷ lệ kỹ thuật.
- File `.dwt` chỉ cho phép tên file đã đặt thủ công trong `CAD_DWT_DIR`; CTB cần có trong môi trường AutoCAD.
- `cad_check_clause_rules` chỉ đọc rule pack cục bộ đã được chuyên gia rà soát. Không có rule TCVN chính thức kèm theo; PASS của rule được gắn thẩm quyền người cung cấp, không phải chứng nhận pháp lý.
