---
name: autocad-structural
description: Quy trình vẽ AutoCAD 2025 theo chuyên ngành Kết cấu, định tuyến tiêu chuẩn Việt Nam và QA.
version: 1.1.0
---

# Kết cấu — AutoCAD agent

1. Hỏi những thông số bắt buộc theo nhu cầu; không tự bịa tải trọng, công suất, độ dốc, dung sai hay thông số an toàn.
2. Bắt đầu với `cad_template(discipline="structural")` nếu người dùng muốn bản vẽ mẫu; sửa JSON dựa trên dữ liệu thật của dự án.
3. Gọi `cad_catalog(discipline="structural")` để tìm tiêu chuẩn tham khảo; tra cứu hiệu lực và điều khoản từ nguồn chính thức. Không tuyên bố đạt TCVN từ catalog.
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


## Hồ sơ công trình 14 bước — 1.4.0-local

Khi cần hồ sơ công trình nhiều bộ môn từ khảo sát đến bàn giao, ưu tiên
`cad_project_catalog` → `cad_project_example` (chỉ để xem schema/demo) →
`cad_project_plan` → `cad_project_check` → `cad_project_preview` →
`cad_project_prepare` → `cad_project_export` → `cad_project_verify_delivery`.
Lấy dữ liệu thực của dự án; không tự gán số liệu demo là khảo sát/tính toán thật.
Bộ sinh hiện hỗ trợ thư viện nhà chữ nhật thấp tầng 1–3 tầng, 14 giai đoạn;
không phải bộ thiết kế tùy ý mọi công trình. `cad_project_change_impact` cho biết
những bước/bản vẽ/review phải làm lại khi đổi dữ liệu. Có lỗi thì sửa theo
`repair_queue` rồi chạy lại bước 14; không bỏ tờ thiếu để giả đủ hồ sơ.

Mỗi tầng phải có kiến trúc, kết cấu, nước, điện, điện nhẹ, điều hòa, nội thất,
sàn và trần. Dự toán phải nêu phạm vi, hạng mục bổ sung, đơn giá và phần loại trừ.
Chữ ký/review là khai báo do người dùng cung cấp, không phải chứng chỉ do AI xác minh.
`READY_FOR_HUMAN_RELEASE` chỉ là đủ điều kiện trình người có trách nhiệm phát hành.
Không tự suy ra thép, móng, CB, cỡ dây hoặc ống từ ví dụ. PCCC, tính địa kỹ thuật,
tính kết cấu/điện/thủy lực và phối hợp BIM toàn phần chưa được tự động triển khai.
Giữ boyxpxt.io.vn tạm thời; hỏi lại khung tên/logo trước khi xuất hồ sơ thật.
Chi tiết ở `docs/PROJECT_WORKFLOW_V14_VI.md` trong checkout plugin.
