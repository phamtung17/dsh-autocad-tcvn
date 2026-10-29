# Nâng cấp 1.5.1 local — một DWG, PDF chỉ khi được yêu cầu

Quy định 1.5.1 ưu tiên các mô tả bản cũ: mặc định **chỉ một PROJECT.dwg**, tất cả
bộ môn nằm chung Model và có các layout; mở DWG ở Model. Không tự xuất PDF,
kể cả preview. `cad_project_preview` mặc định chỉ tạo một DXF tổng để xem trước.
DXF trung gian/đọc lại native nằm ở bộ nhớ làm việc riêng, không bàn giao theo tờ.
Tạo tạm từng tờ chỉ diễn ra trong thư mục tạm được dọn khi ghép xong.

Chỉ đặt `export_pdf=true` trong prepare/preview hoặc dùng CLI `--pdf` sau yêu cầu
PDF rõ ràng của người dùng. Tùy chọn này được đóng băng trong vé; không được thêm
PDF vào vé đã duyệt cho DWG. Xuất từng file bản vẽ qua `--sheets` đã bị tắt.
Những đoạn dưới mô tả thêm PDF chỉ áp dụng khi người dùng đã yêu cầu PDF.

`cad_project_export` và `cad_fitout_export` mặc định tạo **PROJECT.dwg**,
chứa hình học các tờ trong Model Space và toàn bộ layout có mã tờ tương ứng.
Các vùng hình học được dịch chuyển theo lưới atlas, không scale kích thước thật.
Viewport được dịch theo vùng tương ứng và khóa tỷ lệ. Không dùng Xref bên ngoài.
PDF vẫn có thể tách theo tờ để in và có thêm một PDF gộp.
DWG cuối được mở lại và để mở trong AutoCAD có `Visible=True`.

## Harness: phải phân biệt chuẩn bị và thực thi

1. `cad_capabilities` phải trả `1.5.0-local`.
2. Example/plan/check/preview/prepare là bước đọc và chuẩn bị; chúng không mở AutoCAD.
3. Prepare trả vé và lệnh `approve-design`. Chính sách ký một lần vẫn yêu cầu người
   dùng duyệt bằng CLI ở môi trường Python của plugin; tool không tự duyệt vé.
4. Sau đó gọi export. Plugin kết nối hoặc khởi động AutoCAD, chờ trạng thái idle,
   chỉ mở một DXF ghép rồi lưu **định dạng ac2018_dwg được chỉ định rõ**.
5. Chỉ báo thành công khi có chữ ký DWG thực, đủ layout, DIMENSION/ACAD_TABLE,
   audit, tọa độ hình học, block, giá trị kích thước, mục tiêu/tỷ lệ viewport và PDF A3.
6. Gọi verify_delivery. Không đồng nhất thành công kỹ thuật file với duyệt thi công.

Launcher stdout chỉ dành cho JSON-RPC; log ở stderr. Timeout bridge tăng từ
180 giây lên 900 giây, worker tối đa 840 giây. Busy/RPC retry có giới hạn.
Một COM call bị kẹt bên trong vẫn cần supervisor process; hết hạn đánh dấu
TIMEOUT_NEEDS_INSPECTION, không tự kill AutoCAD hoặc gửi Escape/SCRIPT mù.
Không tự thay driver/GPU hoặc tắt bảo mật, không đóng bản vẽ khác của người dùng.
Sau cập nhật thư mục package, khởi động lại kết nối plugin/harness để Python nạp mã mới.

## Đầu vào mở rộng

Xem `examples/villa_18x17_explicit_demo.json` và `building_extensions.py`.
Có thể lấy mẫu qua MCP: `cad_project_example(template="villa_18x17")`.
Vẫn dùng engine `building_v1`, nhà chữ nhật 1–3 tầng, kích thước 9–30 × 7–30 m.
Đây là giới hạn thư viện được kiểm thử, không phải bộ tổng hợp thiết kế mọi công trình.

Trường gốc `extensions` tùy chọn:

- `roof_type`: `flat` hoặc `hip`. Mái hip cùng độ dốc ở bốn mặt; ridge và cao độ
  đỉnh được tính từ kích thước **gồm đua mái**, eaves bằng cao độ cuối trong levels.
- `fixtures`: id/floor/kind/position, kind wc/basin/shower. Số lượng từng tầng phải
  khớp fixtures_per_floor; không còn khóa một WC. Nối nhánh vào trunk gần nhất;
  clash AABB vẫn có thể yêu cầu sửa tuyến, không tự bỏ lỗi.
- `devices`: lights/sockets/ac/data/camera với id/floor/kind/position. Thể hiện đúng
  vị trí khai báo, không tự coi sơ đồ là tính tải hoặc tuyến đã được kỹ sư duyệt.
- `partitions`: id/floor/start/end, vách trực giao. `rooms`: id/floor/name/position.
- `openings`: id/floor/kind/position/width/vertical. Tách khoảng hở vách theo cửa;
  mặt đứng lấy ô mở trên biên ngoài từ cùng dữ liệu.
- `furniture`: id/floor/kind/position/width/depth, bed/sofa/wardrobe/table.
- `pool`: origin/width/depth theo tọa độ khu đất. Kiểm nằm trong đất, không đè nhà;
  tránh cây tròn tại vị trí bị nhà/hồ chiếm. **Chỉ footprint**, chưa thiết kế hồ bơi.
- `elevator`: origin/width/depth trong nhà. Thể hiện vị trí giữ chỗ/ô sàn;
  **chưa thiết kế** pit, headroom, dầm viền, cơ khí, điện và điều khiển thang máy.
- `ceiling_service_zone`: phần không gian dịch vụ yêu cầu thêm dưới dầm; kiểm tra
  ceiling_drop với beam_depth + zone. Giá trị phải do người thiết kế cung cấp.

Circuits hỗ trợ C01/C02/C03 cùng tối đa 24 mạch tổng cộng. Mạch thêm cần tuyến power
có `circuit` tham chiếu đúng ID; route có thể chỉ định `floor`. Không tự chọn CB/cáp.
Khối lượng sàn tùy chỉnh trừ hợp các vách và ô thang; mái hip có hệ số độ dốc;
sân trừ hồ bơi. Dự toán vẫn phải khai báo phần loại trừ và hạng mục bổ sung.

## Đối chiếu các nhóm lỗi người dùng báo

| Nhóm | Xử lý / giới hạn |
|---|---|
| 1–3 | Mở kích thước, bố trí thiết bị theo tầng, thêm mạch và tuyến tham chiếu; cần khai báo bố trí, không tự suy ra biệt thự từ kích thước |
| 4–5, 7–10 | Mái hip có chung ridge/cao độ; hồ có kiểm biên/giao nhà; cây tròn tránh nhà/hồ. Chưa có thuật toán bố trí cảnh quan toàn diện |
| 6 | Giữ hình học mm, viewport đúng tỷ lệ và khóa; không sửa kích thước chỉ theo nhận xét nhìn ảnh |
| 11–18 | Không tích hợp các script ezdxf lỗi bên ngoài; dùng API thư viện hiện cài, không phụ thuộc site.py/struct.py/SCR của harness |
| 19–20 | Dùng Arial TrueType ở DXF/native AutoCAD, kiểm tra PDF; không dùng Helvetica mặc định để xuất tiếng Việt |
| 21–24 | Giữ bố cục và chi tiết đa tỷ lệ đã có; thêm chi tiết mái hip với leader tách hàng. Chưa có solver mọi va chạm chữ |
| 25 | Mở lại DWG và layout có nội dung đã kiểm qua PDF; chưa chứng minh sửa driver GTX 1050 hoặc mọi trường hợp vùng vẽ đen |
| 26–28 | Một lần mở, chờ idle, COM retry có giới hạn; không SendCommand/SCRIPT. Modal thực tế vẫn cần người dùng đóng khi bị chặn |
| 29 | Chỉ định định dạng SaveAs và kiểm header DWG, không chỉ đổi đuôi DXF |
| 30–35 | Báo thiếu chứng cứ địa chất/kết cấu/điện/PCCC/MEP và người duyệt. Không giả lập tính toán hay phê duyệt pháp lý |

Khung tên/logo đang dùng **boyxpxt.io.vn** tạm. Xuất dự án thật vẫn phải hỏi lại.
Luồng một DWG hiện nhận logo vector DXF hoặc chữ. Bitmap PNG/JPG bị từ chối rõ
để tránh Importer bỏ mất ảnh hoặc phụ thuộc ảnh ngoài mà không báo.
