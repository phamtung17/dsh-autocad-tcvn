# Vẽ trực tiếp trong AutoCAD — v1.7 local

## Hành vi mặc định

Luồng `cad_project_export` và `cad_fitout_export` tự kết nối AutoCAD đang chạy hoặc khởi động AutoCAD qua COM, bật cửa sổ và tạo bản vẽ mới riêng của tác vụ. Không sửa hoặc đóng bản vẽ người dùng đang làm.

Sau khi kiểm tra đầu vào, plugin tính hình học và chuẩn bị tài nguyên/layout trong cache riêng. Model đích bắt đầu trống. Các đối tượng native được **tạo thật** qua deep-clone theo thứ tự sinh, từng nhóm cùng layer tối đa 12 đối tượng. Không dùng ẩn/hiện một bản vẽ hoàn chỉnh để giả lập tiến độ. Block có thể chứa nhiều nét và được thêm như một chi tiết; bảng native tạo theo từng bảng. Khung tên/layout và định nghĩa block được nạp trước, không phải từng nét khung cũng được diễn hoạt.

Mỗi nhóm được Regen, nhường UI một khoảng ngắn và ghi `[DSH LIVE]` vào dòng lệnh AutoCAD. Khung nhìn chuyển tới vùng bản vẽ đang làm khi sang tờ. Tất cả bộ môn tiếp tục nằm trong **một Model, một PROJECT.dwg**, có các layout. DXF nguồn/cache là trung gian kỹ thuật riêng, không phải các bản vẽ bàn giao rời.

## Theo dõi tới đâu

Dùng `cad_project_progress(project_id)` để đọc:

- `phase`: PREPARING / PLANNING_GEOMETRY / OPENING_AUTOCAD / DRAWING / INITIALIZING_LAYOUTS / SAVING_DWG / VERIFYING_NATIVE / COMPLETED / FAILED.
- `sheet`, `title`, `sheet_index`, `stage`, `detail_layer`: tờ, mục, nhóm chi tiết đang xử lý.
- `completed_entities`, `total_entities`, `completed_sheets`, `total_sheets`. Đây là số đối tượng nguồn/bảng đã tạo, không phải số nét bên trong block.
- `drawing_percent`: phần trăm bước tạo đối tượng. **100% vẽ chưa có nghĩa lưu và kiểm tra đã xong**. Chỉ `COMPLETED_NEEDS_REVIEW` xác nhận luồng đã kết thúc thành công.
- `heartbeat_age_seconds`, `possibly_stalled`: cảnh báo có thể đang chờ COM nếu quá 60 giây không cập nhật; không tự kết luận AutoCAD bị treo.

Các file `LIVE_PROGRESS.json` và `LIVE_EVENTS.jsonl` nằm cùng thư mục kết quả dưới `generated_projects/<project_id>`. Nhật ký lưu từng mốc thực tế, lỗi giữ số đối tượng đã hoàn thành. Không có chức năng resume tự động hoặc hoàn tác sau lỗi ở phiên bản này. Phần việc chưa hoàn tất được giữ trong tài liệu AutoCAD đang mở để kiểm tra; chưa bảo đảm đã được lưu thành DWG trên đĩa.

## Cách yêu cầu trong Harness

“Vẽ trực tiếp trong AutoCAD để tôi theo dõi, dùng một DWG chung, không xuất PDF. Báo tiến độ từ cad_project_progress, không chỉ tạo DXF offline.”

Làm plan/check/preview để duyệt dữ liệu, rồi prepare và export theo cơ chế phê duyệt ticket hiện có. `preview` là xem trước offline, **không phải lệnh vẽ trực tiếp**. Không bỏ qua lỗi bố trí hoặc đổi chế độ phê duyệt để ép chạy. Chỉ có thể bắt đầu native khi máy có AutoCAD và đầu vào vượt qua kiểm tra; modal/lệnh đang chờ phải được xử lý trước. Trong lúc vẽ nên theo dõi, tránh nhập lệnh hoặc chuyển tài liệu để khung nhìn theo dõi ổn định.

Chỉ xuất PDF khi người dùng yêu cầu rõ. Thương hiệu tạm boyxpxt.io.vn; bản thật hỏi thông tin khung tên/logo theo quy tắc hiện có.

Vẽ trực tiếp không bổ sung tính toán kỹ thuật hoặc chứng nhận hồ sơ. Bản BT01 cũ không tự trở thành bản đã sửa bằng cách bật chế độ live.
