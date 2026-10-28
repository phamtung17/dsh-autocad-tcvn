# Bản nâng cấp cục bộ 1.1.3-local

Nguồn: https://github.com/phamtung17/dsh-autocad-TCVN. Bản nâng cấp được giữ ở
`E:/0.codex/dsh-autocad-TCVN`; chưa đẩy thay đổi lên GitHub.

## Cài đặt trên máy này

- Python riêng: `.venv/Scripts/python.exe`; không thay thư viện Python toàn máy.
- Đã đăng ký MCP `dsh_autocad_tcvn` trong `C:/Users/Admin/.codex/config.toml`.
- Có bản sao cấu hình `config.toml.before-dsh-*.bak` bên cạnh cấu hình.
- Đã cài 10 kỹ năng qua trình cài kỹ năng Codex vào `C:/Users/Admin/.codex/skills/`.
- Công cụ mới cần được Codex nạp ở phiên mới; kỹ năng khả dụng ở lượt kế tiếp.
- Không cần DeepSeek Harness để dùng đường MCP trực tiếp này. Khởi động giao diện
  DeepSeek Harness chưa được kiểm chứng trong lần cài này.
- Chế độ tạo DWG qua MCP vẫn là `manual`. Các kiểm thử thật chạy bằng chương trình
  kiểm thử riêng, không sửa cơ chế cấp phép hay tự tạo vé phê duyệt.

Nếu cần đăng ký lại sau khi di chuyển checkout, kiểm tra đường dẫn hiện có trước.
Trình cài `python -m tools.install_codex` từ chối ghi đè máy chủ thuộc checkout khác.

## Các lỗi đã sửa

1. MCP 2.x bỏ `FastMCP`: giới hạn thư viện về nhánh 1.x và kiểm tra đúng import.
2. Hai thư mục kỹ năng PCCC làm phát hiện 11 thay vì 10: lưu bản cũ dưới `LEGACY.md`.
3. COM liên kết muộn trả đối tượng thiếu phương thức: sinh wrapper kiểu AutoCAD.
4. Phân biệt đối tượng `IAcadEntity` với Circle/Dimension khi đo lại bản vẽ.
5. Thuộc tính `CenterPlot` không hợp lệ khi in `acLayout`: bỏ thao tác gây lỗi.
6. Khung nhìn có tâm DCS thừa: kích hoạt đúng viewport, ZoomCenter rồi khóa tỷ lệ.
7. Giữ viewport giấy chính, bỏ viewport mô hình mặc định trên layout mới.
8. Chọn media PDF ít lề nhất; từ chối lề cắt khung. Dùng A3 full bleed trên máy này.
9. Nét khung nhìn ở lớp không in; nét đậm/mảnh, tâm/khuất được phân lớp rõ.
10. Font TrueType Unicode và cỡ chữ/mũi tên kích thước theo mm trên giấy.
11. PDF xem trước vẽ từ DXF thật: có block đã biến đổi, mũi tên và đường kích thước;
    không còn thay tiếng Việt thành dấu hỏi hay vẽ dấu X thay block.
12. Bao hình học có kích thước chữ và phép biến đổi block; cảnh báo chữ nhỏ,
    khả năng chồng chữ, không vừa khổ giấy. Đây là kiểm tra ước lượng, không phải
    bộ giải tự động mọi va chạm giữa kích thước, chữ và hình học.
13. Nạp thư viện native trước vòng lặp MCP; tách stdin của tiến trình COM khỏi
    luồng giao thức MCP và kết thúc COM đúng cách, tránh treo công cụ probe.

## Cách dùng

Qua MCP: `cad_template` → sửa job theo thông số → `cad_validate` → `cad_preview`
→ kiểm tra hình ảnh → `cad_plot_plan` → `cad_quality_gate` → `cad_prepare`.
Sau bước phê duyệt vé theo chính sách cục bộ, dùng `cad_create_dwg`.
`cad_validate` và báo cáo xem trước có thêm mục `presentation`.

Khung tên tùy chọn trong job (chỉ hiện trên layout AutoCAD, không nằm trong
PDF tự co giãn của `cad_preview`):

```json
"titleblock": {
  "title": "TẤM LẮP - BẢN MẪU",
  "drawing_number": "DEMO-M-001",
  "revision": "A",
  "author": "CAD AGENT",
  "material": "TBD"
},
"plot": {"enabled": true, "pdf": true, "ctb": "monochrome.ctb"}
```

Khung tên là mẫu quy ước dự án; không khẳng định chứng nhận ISO/TCVN.
Mẫu minh họa giả định mm, A3 ngang, tỷ lệ 1:1, tấm 200 × 100 × 12,
lỗ giữa Ø26 và 4 lỗ Ø9. Vật liệu và dung sai để TBD.

## Chạy kiểm tra

Từ thư mục checkout, dùng `.venv/Scripts/python.exe` thay cho `python`:

```powershell
New-Item -ItemType Directory -Force output | Out-Null
python -m pytest tests -q --basetemp=output/test-run-UNIQUE
node --test tests_node/*.test.cjs
python tools/check_skills.py
python -m tools.verify_local_install
$env:CAD_OUTPUT_DIR='E:/0.codex/dsh-autocad-TCVN/output/native'
python -m tools.autocad_2025_regression --pdf
$env:CAD_OUTPUT_DIR='E:/0.codex/dsh-autocad-TCVN/output/demo'
python -m tools.demo_drafting
python -m tools.verify_demo
```

Dùng tên `--basetemp` mới cho mỗi lượt; pytest có thể dọn đường dẫn này.
Kiểm thử thật tạo DWG mới có tên duy nhất, giữ nguyên tài liệu người dùng.
`verify_demo` mở lại DWG, xuất DXF gốc, đo 11 kích thước/5 lỗ, kiểm tra viewport,
lớp không in, khung tên, và đo cạnh 200 mm trên vector PDF.
Hình kiểm tra là `output/demo/FINAL_PREVIEW.png`; bằng chứng số nằm trong
`output/demo/VERIFICATION.json` và `output/native/reports/`.

## Giới hạn thực tế

Mẫu 8 chuyên ngành là bản sơ bộ. Chưa có chỉnh sửa DWG hiện hữu, bộ giải va chạm
toàn diện, tính thiết kế kết cấu/điện/thủy lực, 3D hay chứng nhận điều khoản TCVN.
Danh mục tiêu chuẩn là đầu mối tham khảo; không có bộ quy tắc quốc gia đã xác thực.
DWG, khung tên và in PDF đã kiểm tra trên AutoCAD 2025 của máy này; bản xem trước
ngoại tuyến vẫn tự co giãn và không được gọi là bản in đúng tỷ lệ.
Nội dung nhãn tiếng Việt đã kiểm tra trên PDF gốc AutoCAD. Trình bày của một bản
vẽ công trình/sản phẩm cụ thể còn phụ thuộc dữ liệu và quy ước người dùng cung cấp.
