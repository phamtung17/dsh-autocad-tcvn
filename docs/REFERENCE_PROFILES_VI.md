# Xuất hồ sơ theo bộ tham chiếu — 1.2.0-local

Profile `stu4_fitout_v12` được đo từ thư mục người dùng cung cấp, gồm 19 DWG
(11 bản vẽ chính và 8 tài nguyên/Xref), 35 layout và 18 nhóm nội dung.
Tài nguyên dự án được giữ cục bộ tại `output/profiles/`; không đưa vào gói mã nguồn.

## Những thành phần được giữ nguyên

Tờ bìa/tờ trình và danh mục; hiện trạng; kích thước; cấu tạo/hoàn thiện tường;
sàn và len chân tường; trần hoàn thiện, định vị đèn, phối hợp MEP; ổ cắm;
định vị mặt đứng, mặt đứng; chi tiết tường/sàn/trần và mặt cắt.

Đường xuất mới dùng bản sao DWG native, vì vậy giữ hatch vật liệu, DIMENSION,
leader, block ký hiệu, bảng native, khung tên/logo, ghi chú, clipping viewport,
layer overrides, tỷ lệ, cửa sổ in và CTB. Không dựng lại chúng bằng hình xấp xỉ.
Thông tin viewport được ghi cả khi viewport nằm trên layout không đang kích hoạt.

## Năm công cụ mới

| Công cụ | Chức năng |
|---|---|
| `cad_reference_profiles` | Danh sách profile đã cài |
| `cad_reference_profile` | Thành phần, layout, tài nguyên, viewport và tag khung tên |
| `cad_reference_plan` | Kiểm tra đầy đủ tờ, Xref, CTB, font và thay đổi thuộc tính |
| `cad_reference_prepare` | Đóng băng job cùng mã băm profile để phê duyệt |
| `cad_reference_export` | Xuất bằng vé đã duyệt; không nhận đường dẫn/mã lệnh tùy ý |

Mặc định phải đủ các tờ trong profile. Chỉ xuất một phần khi đặt rõ
`require_complete: false`; báo cáo vẫn liệt kê các nhóm/tờ còn thiếu.
Thiếu Xref/CTB luôn chặn. Thiếu font chặn cho đến khi có lựa chọn rõ ràng
`accept_font_substitution: true`; lựa chọn này vẫn giữ cảnh báo trong báo cáo.

Đầu ra gồm DWG cùng Xref/tài nguyên, PDF từng layout, PDF gộp có bookmark,
`SHEET_INDEX.csv` và `PUBLISH_REPORT.json`. Mỗi lần dùng `project_id` mới;
không ghi đè hồ sơ trước và không sửa thư mục nguồn.

## Job minh họa

```json
{
  "profile_id": "stu4_fitout_v12",
  "project_id": "du_an_moi_001",
  "mode": "reference_reissue",
  "require_complete": true,
  "accept_font_substitution": false,
  "attributes": {}
}
```

Muốn đổi thuộc tính khung tên, đọc `title_blocks` trong profile trước.
Ví dụ với tờ kích thước có tag `FIT-OUT`:

```json
"attributes": {"s007": {"FIT-OUT": "TEN GOI HO SO"}}
```

Chỉ chấp nhận tag thực sự tồn tại; giá trị là chữ thuần, không nhận field expression
hoặc script. Thuộc tính đổi được ghi trong báo cáo; hình học tham chiếu giữ nguyên.

Phê duyệt MCP vẫn dùng CLI cục bộ `python -m autocad_agent.cli approve-reference TICKET`.
Vé và permit worker có chữ ký, dùng một lần; profile thay đổi làm vé mất hiệu lực.

## Giới hạn cần hiểu đúng

Đây là chế độ **tái xuất/đóng gói theo hồ sơ mẫu**, giữ nội dung thiết kế tham chiếu.
Thay tên dự án trong khung tên không biến mặt bằng cũ thành thiết kế mới.
Để thiết kế một căn/phòng/công trình khác cần dữ liệu hình học, kích thước, vật liệu,
MEP và nội dung từng tờ. Không tuyên bố tự thiết kế hoàn chỉnh hay đạt TCVN.

Nguồn có font SHX không được gửi kèm. Bộ thử chấp nhận font thay thế để kiểm tra
xuất native; cần cung cấp font gốc nếu yêu cầu giống tuyệt đối và dùng để phát hành.
Đường xuất giữ cached field của bộ mẫu bằng FIELDEVAL=0, không tự cập nhật DST từ
máy tác giả. Bảng danh mục native và DST gốc được giữ; danh mục CSV/PDF bookmarks
được tạo lại từ đúng danh sách tờ đã chọn. Không tự tái tạo cơ sở dữ liệu Sheet Set.

CTB bản sao dùng tiền tố `PROFILE_` trong thư mục `PlotStyles`. Khi mở DWG trên
máy khác, thêm thư mục đó vào Plot Style Table Search Path để tái in đúng nét.
Plugin chỉ thêm đường dẫn này tạm thời khi xuất rồi khôi phục thiết lập AutoCAD.

## Cài profile từ một bộ khác

Thực hiện bằng CLI quản trị khi người dùng đã chỉ rõ thư mục tham chiếu:

```powershell
python -m tools.inspect_reference SOURCE_FOLDER INSPECTION_FOLDER
python -m tools.publish_reference import PROFILE_ID INSPECTION_FOLDER
python -m tools.publish_reference plan JOB.json
python -m tools.publish_reference publish JOB.json
```

CLI publish là đường chạy cục bộ được người dùng khởi chạy trực tiếp. MCP vẫn
giữ cổng phê duyệt. Đặt `CAD_OUTPUT_DIR` và `CAD_PROFILE_DIR` giống cấu hình MCP.
