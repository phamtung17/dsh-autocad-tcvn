---
name: autocad-architectural
description: Quy trình vẽ AutoCAD 2025 theo chuyên ngành Kiến trúc, định tuyến tiêu chuẩn Việt Nam và QA.
version: 1.1.0
---

# Kiến trúc — AutoCAD agent

1. Hỏi những thông số bắt buộc theo nhu cầu; không tự bịa tải trọng, công suất, độ dốc, dung sai hay thông số an toàn.
2. Bắt đầu với `cad_template(discipline="architectural")` nếu người dùng muốn bản vẽ mẫu; sửa JSON dựa trên dữ liệu thật của dự án.
3. Gọi `cad_catalog(discipline="architectural")` để tìm tiêu chuẩn tham khảo; tra cứu hiệu lực và điều khoản từ nguồn chính thức. Không tuyên bố đạt TCVN từ catalog.
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


## Hồ sơ tham chiếu native — 1.2.0-local

Khi người dùng chỉ rõ một thư mục hồ sơ mẫu và muốn giữ cách trình bày/thành phần,
ưu tiên `cad_reference_profiles` → `cad_reference_profile` → `cad_reference_plan`.
Đường này giữ khung tên, logo, DIMENSION, hatch, leader, bảng, block ký hiệu, Xref,
viewport clipping/layer overrides và các thiết lập in native. Không thay chúng
bằng một trang schematic hay khung tên cơ khí mặc định.

Mặc định yêu cầu đủ tờ; chỉ dùng `require_complete=false` khi người dùng cần một
phần bộ hồ sơ. Thiếu Xref/CTB phải xử lý trước; font thay thế phải được ghi rõ.
`cad_reference_prepare` đóng băng job/profile; `cad_reference_export` dùng vé được
phê duyệt theo cơ chế cục bộ. Đầu ra có PDF gộp, PDF từng tờ, DWG/tài nguyên,
CSV danh mục và báo cáo. Không ghi đè thư mục nguồn.

Chế độ `reference_reissue` giữ nguyên thiết kế tham chiếu. Thay thuộc tính khung
 tên không đồng nghĩa đã thiết kế một mặt bằng mới. Với dự án mới cần nội dung,
hình học và thông số chuyên ngành của dự án; không tự bịa đủ thiết kế hoặc chứng
nhận TCVN. Chi tiết API tại checkout plugin `docs/REFERENCE_PROFILES_VI.md`.


## Sinh thiết kế mới — 1.3.0-local (ưu tiên cho yêu cầu vẽ dự án mới)

Dùng `cad_fitout_example` → `cad_fitout_plan` → `cad_fitout_preview` →
`cad_fitout_prepare` → `cad_fitout_export` cho studio có tham số. Không dùng
`cad_reference_export` để giả làm thiết kế mới. Bộ sinh mới có 11 tờ, kích thước,
hatch, leader, block, ACAD_TABLE native và viewport theo tỷ lệ. Dự án thật cần
số liệu đã chốt và rà soát chuyên ngành; không tự gán dữ liệu demo là dữ liệu thật.

Theo yêu cầu người dùng, tạm dùng **boyxpxt.io.vn** cho khung tên/logo chữ.
Khi xuất dự án thật phải hỏi lại khung tên và logo; chỉ khi đã chốt mới đặt
`branding.confirmed=true`. Chi tiết xem `docs/NEW_DESIGN_V13_VI.md` tại checkout.


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


## Luồng xuất mặc định 1.5 local — ưu tiên hơn mô tả bản cũ

cad_project_export/cad_fitout_export xuất **một PROJECT.dwg cho toàn bộ layout**.
Plan/preview/prepare không khởi động AutoCAD. Export sau vé được duyệt mới kết nối
hoặc khởi động AutoCAD, đặt Visible=True, đợi idle, xuất DWG định dạng native,
mở lại DWG cuối và để mở. Không báo DXF là DWG; không tự chuyển sang ezdxf khi
export lỗi rồi báo hoàn tất. Trả lỗi và đường dẫn báo cáo để sửa đúng tầng.
Không dùng SendCommand/SCRIPT để phá modal, không tự kill AutoCAD của người dùng.
Mẫu extensions trong examples/villa_18x17_explicit_demo.json hỗ trợ bố trí rõ theo
 tầng, nhiều thiết bị/mạch, mái hip. Pool chỉ footprint, elevator chỉ ô giữ chỗ;
không suy ra tính toán kỹ thuật. Xem docs/SINGLE_DWG_V15_VI.md. Tiếp tục dùng
boyxpxt.io.vn tạm và hỏi lại branding trước khi xuất dự án thật.


## Yêu cầu ưu tiên 1.5.1 — một bản vẽ, không tự xuất PDF

Người dùng yêu cầu mọi mục chung trong MỘT DWG, cùng Model và có layout để in;
không tạo thư mục bàn giao với DXF/DWG riêng từng mục. Mặc định mở Model.
Không tự xuất PDF, cả khi preview. Dùng export_pdf=False (mặc định) ở preview/prepare.
Chỉ đổi True sau khi người dùng nói rõ cần PDF. Không chạy các script cũ xuất PDF
hoặc tách tờ rồi gọi đó là hoàn thành. DXF trung gian chỉ là cache kỹ thuật riêng.
Với BT01 mở 00_DWG_CHUNG/BT01_TOAN_BO_HO_SO.dwg; giữ nguyên nội dung/khung tên hiện có.
