---
name: cad-automation
description: Tự động hóa Autodesk AutoCAD trên Windows bằng Python COM/pywin32, AutoLISP và DXF; tạo, sửa, kiểm tra và xuất bản vẽ 2D/3D an toàn, chống treo, có kiểm chứng.
version: 1.1.0
category: engineering-cad
---

# CAD AUTOMATION — Autodesk AutoCAD Production Workflow v1.1

## 1. Vai trò, phạm vi và hợp đồng thực thi

Skill này chịu trách nhiệm **thực thi** yêu cầu đã được `cad-designer` chuẩn hóa. Hỗ trợ cơ khí, kiến trúc, kết cấu, MEP, điện, hạ tầng, bản vẽ sơ đồ và bố trí công nghiệp. Không tự tuyên bố bản vẽ đã đạt tiêu chuẩn, an toàn hay đủ điều kiện thi công/chế tạo nếu chưa có người có chuyên môn duyệt.

**Ưu tiên công nghệ:** AutoCAD trên Windows → `pywin32` ActiveX/COM; các thao tác lặp tương tác phức tạp → AutoLISP đã kiểm tra; không có AutoCAD → `ezdxf` xuất DXF (không giả làm DWG); 3D tham số chuyên sâu → CadQuery/FreeCAD nếu được phép và có cài đặt. `pyautocad` là tiện ích bọc COM, không bắt buộc. Không giả định `win32com` chạy trên Linux/macOS. AutoCAD LT và các phiên bản AutoCAD khác nhau có thể không hỗ trợ cùng một bề mặt tự động hóa; kiểm tra phiên bản/edition trước khi dùng.

**Quy tắc bắt buộc:**
1. Trước khi sửa DWG của người dùng: xác nhận đường dẫn, sao lưu, làm việc trên bản sao, không đóng tài liệu khác, không xóa nội dung không thuộc phạm vi.
2. Phân biệt `đã sinh code`, `đã chạy`, `đã kiểm tra hình học`, `đã kiểm tra PDF`, `đã được kỹ sư duyệt`.
3. Mọi giá trị thiếu về kích thước, vật liệu, tải trọng, dung sai, điện áp, PCCC phải hỏi hoặc gắn nhãn `ASSUMPTION / CẦN XÁC NHẬN`; không tự bịa thông số sản xuất.
4. Model Space: hình học đúng kích thước thực trong **đơn vị của dự án**; mm là mặc định chỉ khi dự án dùng mm. Paper Space: khung tên, viewport, tỉ lệ in.
5. Mọi thao tác có tác động không thể đảo ngược (xóa, purge, ghi đè, đóng, kết thúc tiến trình) phải có phạm vi rõ ràng, sao lưu và chấp thuận tương ứng.
6. Mọi lần chạy xuất log, danh sách đối tượng và kết quả kiểm tra; lỗi không được báo thành công.

## 2. Đầu vào và đầu ra chuẩn

```yaml
request:
  discipline: mechanical|architectural|structural|mep|electrical|civil|general
  task: create|modify|audit|convert|plot
  source_dwg: null             # đường dẫn nếu sửa file có sẵn
  output_dir: D:/CAD_OUTPUT
  units: mm                    # mm|m|inch|feet|project-defined
  geometry: {}                 # tọa độ, kích thước, đối tượng, quan hệ
  standards: {}                # quốc gia, bộ tiêu chuẩn, phiên bản, quy định dự án
  sheets: []                   # A0-A4 hoặc custom; tỉ lệ viewport
  required_outputs: [dwg, pdf, validation_json]
  allow_overwrite: false
  allow_destructive_cleanup: false
```

Kết quả tối thiểu: đường dẫn file thực tế, phiên bản AutoCAD, loại đối tượng, số lượng theo layer, đơn vị, danh sách kiểm tra PASS/FAIL/NOT_CHECKED, warnings, assumptions. Khi chưa chạy AutoCAD, ghi rõ `NOT_EXECUTED`.

## 3. Kiểm tra môi trường và an toàn phiên làm việc

- Chạy trên Windows, Python tương thích bản `pywin32` đã cài; `python -m pip install pywin32`.
- Không tự động mở hoặc chiếm quyền tài liệu đang sửa nếu người dùng chưa cho phép. Ưu tiên tạo tài liệu mới cho yêu cầu tạo mới; với sửa file, mở **bản sao** từ thư mục staging.
- COM thường dùng STA: mỗi thread gọi COM phải `pythoncom.CoInitialize()` và `CoUninitialize()` trong `finally`; không truyền COM proxy tùy tiện giữa các thread.
- `GetActiveObject('AutoCAD.Application')` có thể kết nối phiên đang chạy; `Dispatch` có thể khởi tạo/điều phối phiên theo cấu hình COM. Không tự đóng hoặc kill phiên không do tác vụ sở hữu.
- Phát hiện phiên bản qua `app.Version`, kiểm tra `doc.ReadOnly`, `doc.FullName`, `doc.GetVariable('INSUNITS')`; không đoán ProgID có sẵn.
- Đọc trạng thái lệnh (`CMDACTIVE`) và `IsQuiescent` khi khả dụng; không gọi hàng loạt `SendCommand` khi AutoCAD đang hỏi tham số.

### 3.1 COM retry có giới hạn (mẫu Python chạy được)

```python
import time
import pythoncom
import pywintypes
import win32com.client

RETRYABLE = { -2147418111, -2147417846, -2147417848 }

def com_call(operation, timeout=15.0, delay=0.25):
    """operation phải là lambda bao trùm TOÀN BỘ chuỗi COM access."""
    deadline = time.monotonic() + timeout
    while True:
        try:
            return operation()
        except pywintypes.com_error as exc:
            hr = exc.hresult
            if hr not in RETRYABLE or time.monotonic() >= deadline:
                raise
            pythoncom.PumpWaitingMessages()
            time.sleep(delay)

def connect_existing_autocad():
    pythoncom.CoInitialize()
    try:
        app = com_call(lambda: win32com.client.GetActiveObject('AutoCAD.Application'))
        version = com_call(lambda: app.Version)
        return app, version
    except Exception:
        pythoncom.CoUninitialize()
        raise
# Sau khi sử dụng xong COM trong cùng thread: pythoncom.CoUninitialize()
```

**Lưu ý:** timeout ở đây chỉ giới hạn **khoảng retry sau khi COM trả lỗi**. Nếu một lệnh COM bị kẹt bên trong và không trả về, wrapper này **không** thể ngắt cuộc gọi. Với pipeline tự động hoàn toàn, dùng **process giám sát riêng**, timeout ở cấp process, file heartbeat và quy trình phục hồi có sự chấp thuận. Không dùng `taskkill /F` tự động với AutoCAD của người dùng.

## 4. Ví dụ tạo bản vẽ mới và xác minh (Python COM)

Ví dụ dưới đây tạo bản vẽ mới, vẽ hình chữ nhật 100×60 mm và lỗ Ø20 mm, kiểm tra tọa độ, lưu vào file mới. Chạy bằng Python trên Windows có AutoCAD và pywin32; chỉnh `OUTPUT` thành đường dẫn phù hợp. Không tác động tài liệu đang mở.

```python
from pathlib import Path
import math
import pythoncom
import win32com.client
from win32com.client import VARIANT

OUTPUT = Path(r'D:\CAD_OUTPUT\demo_plate.dwg')


def point(x, y, z=0):
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(x), float(y), float(z)])


def doubles(values):
    return VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [float(v) for v in values])


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT.exists():
        raise FileExistsError(f'Không ghi đè: {OUTPUT}')
    pythoncom.CoInitialize()
    doc = None
    try:
        app = win32com.client.Dispatch('AutoCAD.Application')
        app.Visible = True
        doc = app.Documents.Add()
        doc.SetVariable('INSUNITS', 4)  # 4 = millimeters; chỉ cho bản vẽ demo mới
        layers = doc.Layers
        if not any(layer.Name.upper() == 'PART' for layer in layers):
            layers.Add('PART')
        ms = doc.ModelSpace
        pl = ms.AddLightWeightPolyline(doubles([0, 0, 100, 0, 100, 60, 0, 60]))
        pl.Closed = True
        pl.Layer = 'PART'
        hole = ms.AddCircle(point(50, 30), 10)
        hole.Layer = 'PART'
        assert pl.Closed
        assert abs(hole.Radius - 10.0) < 1e-8
        assert abs(hole.Center[0] - 50.0) < 1e-8
        assert abs(hole.Center[1] - 30.0) < 1e-8
        assert sum(1 for _ in ms) >= 2
        doc.SaveAs(str(OUTPUT))
        assert OUTPUT.is_file() and OUTPUT.stat().st_size > 0
        print(f'CREATED: {OUTPUT}')
    finally:
        # Không đóng hay xóa tài liệu; để người dùng kiểm tra bản vẽ mới.
        pythoncom.CoUninitialize()

if __name__ == '__main__':
    main()
```

Ví dụ minh họa, **chưa được thực thi trên AutoCAD trong môi trường tạo skill này**. Khi chạy thật, ghi lại phiên bản, kết quả và lỗi. Với kích thước bản vẽ thực tế, xác minh thêm bounding box, tâm, bán kính, độ kín, diện tích, lớp, đơn vị và quan hệ hình học.

## 5. API cookbook đã chỉnh sửa

| Tác vụ | Cách dùng / lưu ý |
|---|---|
| Line | `ms.AddLine(point(0,0), point(100,0))` |
| Circle | `ms.AddCircle(point(50,30), 10.0)` |
| LWPOLYLINE | `ms.AddLightWeightPolyline(doubles([x1,y1,x2,y2,...]))`; phải đặt `.Closed=True` nếu cần kín |
| Arc | `ms.AddArc(center, radius, start_radians, end_radians)` |
| Text | `ms.AddText('TEXT', point(x,y), height)`; kiểm tra font và mã Unicode |
| MText | `ms.AddMText(point(x,y), width, 'Line 1\\PLine 2')` |
| Aligned dim | `ms.AddDimAligned(point1, point2, text_position)` |
| Rotated dim | `ms.AddDimRotated(point1, point2, text_position, angle_radians)` |
| Radial dim | `ms.AddDimRadial(center, chord_point, leader_length)` — KHÔNG truyền đối tượng circle vào tham số thứ hai |
| Diametric dim | `ms.AddDimDiametric(chord_point, far_chord_point, leader_length)` — ba tham số là các điểm trên đường kính và độ dài leader; không truyền circle object |
| Angular dim | Dùng chữ ký phù hợp đối tượng/phiên bản ActiveX (`AddDimAngular`); xác minh bằng test trước khi đưa vào production |
| 3D revolve | `ms.AddRevolvedSolid(region, axis_point, axis_direction, 2 * math.pi)` — radian, không dùng 360 |
| Hatch | `AddHatch` → `AppendOuterLoop` bằng SAFEARRAY of DISPATCH → `Evaluate`; bảo đảm biên dạng kín và các đảo hợp lệ |
| Region | `AddRegion` cần vòng khép kín không tự cắt; kết quả có thể là tập nhiều region |
| Plot | Cấu hình `Layout` (không cấu hình `doc.Plot` như `Layout`); `doc.Plot.PlotToFile(path)` sau khi cấu hình máy in và khổ giấy |

**Chú ý:** một số API có overload/giới hạn theo bản AutoCAD. Kiểm tra tài liệu ActiveX theo phiên bản đang chạy và thử trên bản vẽ mới. Không thay thế kích thước liên kết bằng `TextOverride` giả trừ khi chỉ là chú thích, có nhãn và kiểm tra chéo với hình học.

## 6. Quản lý layer, kiểu nét, block, thuộc tính

- Dùng layer theo quy ước của dự án; màu/linetype/lineweight **ByLayer** cho đối tượng thông thường, ngoại lệ có ghi nhận.
- Kiểm tra layer đã tồn tại trước khi `Layers.Add`. Linetype CENTER/HIDDEN phải load từ `.lin` tương thích trước khi gán; không giả định luôn có sẵn.
- Layer `0` được phép cho đối tượng không thuộc block khi phù hợp tiêu chuẩn dự án; bên trong block, layer 0/ByBlock/ByLayer có ý nghĩa kế thừa riêng. Không tự động xóa layer 0 hay Defpoints.
- Block: `doc.Blocks.Add(base_point, name)`, thêm entity, `ms.InsertBlock(insert_point, name, sx, sy, sz, rotation_radians)`; với block có thuộc tính kiểm tra `HasAttributes` trước `GetAttributes()`.
- Xref: kiểm tra đường dẫn, đường dẫn tương đối, trạng thái loaded/unresolved, không tự bind nếu chưa được yêu cầu.
- Không sửa các block động, annotative, xref hoặc proxy entity theo cách phá hủy mà chưa có chiến lược bảo toàn.

## 7. Kích thước, dung sai và văn bản

- `AddDimAligned`, `AddDimRotated`, `AddDimRadial`, `AddDimDiametric` phải được kiểm tra bằng phép đo hình học, không chỉ nhìn text hiển thị.
- Tạo và gán `DimStyle` theo template; thiết lập `DIMTXT`, `DIMASZ`, `DIMEXO`, `DIMEXE`, `DIMDEC`, `DIMZIN`, `DIMSCALE`, `DIMASSOC` theo yêu cầu, không gán giá trị chung cho mọi tỉ lệ.
- `%%c`, `%%d`, `%%p` có thể dùng trong text AutoCAD, nhưng khả năng hiển thị phụ thuộc loại text/font. Với dung sai xếp chồng dùng cú pháp MText phù hợp và test PDF.
- Kích thước sản xuất phải được gắn với đặc tính thực; không chỉ chèn TEXT thay cho DIMENSION nếu người dùng cần chỉnh sửa kích thước liên kết.
- Font: kiểm tra SHX/TTF và BigFont theo môi trường; cảnh báo khi thiếu font; không tự đổi font gây sai ký tự.

## 8. 3D và tham số hóa

- COM có thể tạo box/cylinder/cone/sphere/region/extrude/revolve và boolean; không giả định toàn bộ tính năng SolidWorks/Inventor tồn tại trong AutoCAD.
- Mỗi feature cần kiểm tra tọa độ, hướng trục, kích thước, tính kín và kết quả boolean. Góc của API hình học thường là radian.
- Đối với STEP/IGES/mesh, kiểm tra khả năng xuất thực tế của phiên bản/phần mềm; không tuyên bố đã xuất nếu chỉ có chuỗi extension.
- Với cơ khí cần gia công, dùng CAD 3D chuyên dụng khi cần feature history, constraints, BOM liên kết và kiểm chứng dung sai chuyên sâu.

## 9. AutoLISP an toàn và script

```lisp
(defun c:CADTEST (/ oldcm *error*)
  (setq oldcm (getvar "CMDECHO"))
  (defun *error* (msg)
    (if oldcm (setvar "CMDECHO" oldcm))
    (if msg (princ (strcat "\nCADTEST error: " msg)))
    (princ))
  (setvar "CMDECHO" 0)
  (entmakex (list '(0 . "CIRCLE") '(100 . "AcDbEntity")
                  '(100 . "AcDbCircle") '(10 0.0 0.0 0.0)
                  '(40 . 10.0)))
  (setvar "CMDECHO" oldcm)
  (princ "\nCADTEST: circle created")
  (princ))
```

- Kiểm tra `ssget` trả về `nil` trước `sslength`; khai báo tất cả biến cục bộ.
- Khi sửa `entget`, dùng `subst` chỉ khi group code đã có; nếu chưa có thì `append` hoặc API đối tượng.
- Dùng `vl-catch-all-apply`/error handler và khôi phục biến hệ thống khi có lỗi; với undo grouping chỉ tạo/đóng nhóm nếu lệnh thực sự bắt đầu.
- Không tự `APPLOAD`, thay đổi `SECURELOAD`/`TRUSTEDPATHS` hoặc tải code từ Internet. Người dùng phải chủ động chọn đường dẫn tin cậy.
- `SendCommand` là **bất đồng bộ trong một số tình huống**, phụ thuộc prompt/ngôn ngữ/phiên bản. Ưu tiên API không tương tác. Nếu bắt buộc, dùng lệnh có tiền tố `_`/`-` đúng cách, thử trên file mới, timeout bằng giám sát độc lập; không giả định Ctrl+C từ COM sẽ giải phóng được lời gọi đang kẹt.

## 10. Chống treo, rollback, kiểm soát lỗi

### 10.1 Phân loại lỗi

| Nhóm | Xử lý |
|---|---|
| COM `RPC_E_CALL_REJECTED` / busy | retry ngắn có backoff và deadline; log HRESULT |
| COM call treo không trả | supervisor **process** riêng; đánh dấu TIMEOUT; không kill phiên người dùng |
| Lệnh chờ prompt | dừng gửi lệnh mới, báo trạng thái, yêu cầu can thiệp; không spam Escape |
| Đối tượng không hợp lệ / bị xóa | đọc lại handle, xác minh document và transaction trước khi sửa |
| Layer/linetype/font thiếu | nạp nguồn hợp lệ hoặc báo lỗi rõ; không âm thầm thay thế |
| File bị khóa / read-only | tạo bản sao output khác tên; không ghi đè |
| Plot PDF không xuất hiện | kiểm tra plot configuration, background plot, trạng thái file, thời hạn chờ |

### 10.2 Quy trình transaction theo file

1. Tạo thư mục staging riêng và file backup nguyên bản (nếu sửa file).
2. Xác minh nguồn tồn tại và hash, tạo bản sao làm việc.
3. Thực thi các thao tác có log; nếu lỗi, không ghi đè bản gốc.
4. Lưu vào file mới có tên version hoặc timestamp do chương trình sinh; kiểm tra file tồn tại, dung lượng và mở lại khi có thể.
5. Chạy L1-L4, ghi `validation.json`; chỉ promote output khi đạt các gate được yêu cầu.
6. Cleanup **chỉ** các tài nguyên do tác vụ tạo, trong `finally`; không đóng mọi bản vẽ, không xóa toàn bộ selection sets của người dùng.

### 10.3 AUDIT, PURGE, OVERKILL

`doc.PurgeAll()` là thao tác COM không có prompt nhưng vẫn thay đổi file và có thể loại bỏ định nghĩa không dùng; **chỉ chạy trên bản sao và khi đã được phép**. `AUDIT`, `-PURGE`, `OVERKILL`, `-EXPORT`, `-PLOT` có thể có prompt phụ tùy cấu hình; không gửi mù chuỗi `SendCommand` rồi chờ vô hạn. `AUDIT` không thay thế kiểm tra hình học. Không chạy tự động mọi lệnh này sau mỗi thao tác vẽ.

## 11. Xuất bản vẽ và plot PDF

- ModelSpace hình học theo đơn vị dự án; Layout xác định khổ giấy, orientation, viewport, scale, CTB/STB.
- Cấu hình `doc.ActiveLayout.ConfigName`, `CanonicalMediaName` từ `GetCanonicalMediaNames()` (không hardcode nếu thiết bị không có), `PlotType`, `StandardScale`/`CustomScale`, `CenterPlot`, `StyleSheet`.
- `BACKGROUNDPLOT=0` chỉ áp dụng trong phiên tác vụ khi cần đồng bộ; lưu giá trị cũ và khôi phục trong `finally`.
- `doc.Plot.PlotToFile(str(pdf_path))` trả trạng thái; xác minh PDF thực sự tồn tại, số trang, kích thước giấy, font, khung và nét. Không đánh đồng `PlotToFile` trả thành công với PDF đúng.
- DXF: có thể tạo bằng ezdxf offline, nhưng conversion DXF→DWG cần AutoCAD hoặc công cụ có khả năng tương thích đã xác nhận.
- Với nhiều layout, in từng layout hoặc publish theo danh sách kiểm soát; kiểm tra tên file trùng và thứ tự trang.

## 12. Bộ kiểm thử và các cấp xác minh

**L0**: phân tích yêu cầu, đủ dữ liệu, kiểm tra đơn vị, đường dẫn, quyền ghi.

**L1**: API không báo lỗi và file output tồn tại.

**L2**: entity count theo loại/layer; có block/text/dim/hatch cần thiết; không có entity rỗng.

**L3**: đo bounding boxes, diện tích, chu vi, bán kính, tâm, độ kín, giao cắt, kích thước thực, dung sai hình học, layer/linetype/lineweight, units; kiểm tra bằng giá trị kỳ vọng với epsilon phù hợp.

**L4**: xem hình plot/render từng sheet, kiểm tra chồng chữ, thiếu font, nét, tỉ lệ, hướng trang, ký hiệu và bố cục. **L4 không chứng minh độ đúng kỹ thuật**; vẫn cần đối chiếu dữ liệu và kỹ sư duyệt.

Ví dụ các case tối thiểu trước khi dùng production:

| Test | Dữ liệu | Kết quả mong đợi |
|---|---|---|
| Rectangle | 100×60 | closed polyline; bounds 100×60; area 6000 |
| Circle | center (50,30), R10 | center và radius chính xác; đường kính 20 |
| Layer | PART, DIM, CENTER | entity đúng layer; không hardcode màu nếu không yêu cầu |
| Annotation | kích thước 100, 60, Ø20 | dim đo khớp hình học; không đè nhau |
| PDF A3 | 420×297 mm | trang đúng kích thước, viewport đúng tỉ lệ |
| Busy COM | mô phỏng HRESULT retryable | dừng sau deadline, log lỗi |
| File exists | output đã tồn tại | không ghi đè nếu `allow_overwrite=false` |
| Invalid input | radius âm/đường hở | từ chối hoặc báo FAIL |

## 13. Báo cáo máy đọc được

```json
{
  "skill": "cad-automation", "version": "4.0.0",
  "execution": "NOT_EXECUTED", "cad_version": null,
  "source_file": null, "output_files": [],
  "units": "mm", "discipline": "general",
  "validation": {"L0":"NOT_CHECKED","L1":"NOT_CHECKED","L2":"NOT_CHECKED","L3":"NOT_CHECKED","L4":"NOT_CHECKED"},
  "assumptions": [], "warnings": [], "errors": [], "requires_engineer_approval": true
}
```

## 14. Tích hợp DeepSeek Harness / AI local

- Skill là **hướng dẫn** cho agent, không tự cấp quyền điều khiển AutoCAD.
- Agent cần công cụ thực thi Python/PowerShell hoặc bridge có quyền rõ ràng trên **máy Windows cài AutoCAD**. Nếu AI chạy trên máy khác, kết nối đến một service bridge được xác thực và giới hạn quyền, không mở COM/DCOM trực tiếp ra Internet.
- Chỉ cho phép các thư mục dự án/đầu ra trong allowlist; log mọi lệnh; mặc định không chạy lệnh hệ thống tùy ý từ prompt.
- Luồng: user → `cad-designer` xác nhận spec → agent sinh code → người dùng phê duyệt thao tác ghi/xóa → bridge chạy → validator → preview → deliver.
- Với model nhỏ, chia thành bước ngắn, sử dụng schema JSON, template code đã kiểm thử và test case cố định thay vì yêu cầu model tự viết toàn bộ hệ thống trong một lượt.

## 15. Kiến thức gốc, giới hạn và nguồn

Kế thừa phạm vi từ `cad-automation` v1.2.0: Python COM/pyautocad, AutoLISP, layer, dimension, blocks, 3D, plotting, batch, compatibility, workflow kiểm chứng. Đã sửa các mâu thuẫn về chữ ký dimension, góc radian, AUDIT/PURGE, COM retry, thao tác destructive, đơn vị, xuất file và độ tin cậy của L4. Mọi ví dụ ở bản này là **mẫu kỹ thuật chưa kiểm thử trực tiếp trên AutoCAD trong phiên tạo file**; phải chạy regression trên phiên bản đích. Khi sử dụng code hoặc thư viện bên thứ ba, ghi nhận license/attribution thích hợp. Tham khảo tài liệu Autodesk ActiveX Automation và API chính thức theo phiên bản AutoCAD đang sử dụng.

## 21. Vietnam TCVN/QCVN Execution Contract v3.0

Bắt buộc nhận `standards_manifest` từ `cad-designer` và nạp `../standards/registry.json`. Không hard-code mọi ngành dùng cùng một khung tên/layer/dimension style. Chỉ tạo bản vẽ theo template DWT và quy tắc dự án đã được duyệt. Nếu chưa có template, tạo bản vẽ **minh họa** và đánh dấu `PROJECT_RULE`, không gọi là bản vẽ đạt TCVN.

### 21.1 Safe execution, chống treo
- Khởi động kết nối COM theo phiên bản AutoCAD/Windows đã xác nhận; kết nối đúng document, không thao tác ActiveDocument mù quáng sau khi mở file.
- Mọi batch chạy trên bản sao và có timeout từ **process supervisor** độc lập; `SendCommand` là bất đồng bộ, không dùng `sleep` cố định làm bằng chứng hoàn thành.
- Chỉ gửi lệnh sau khi xác minh `CMDACTIVE`/trạng thái tương tác; dùng API COM trực tiếp cho geometry, layer, layout khi khả thi. Không chèn chuỗi lệnh tương tác chưa xác định prompt.
- Retry lỗi COM `RPC_E_CALL_REJECTED` có backoff và số lần hữu hạn; không retry lệnh tạo hình không idempotent nếu không có transaction/marker chống trùng.
- Khi timeout: dừng gửi lệnh, log trạng thái, giữ bản gốc; không tự động `taskkill` AutoCAD đang có tài liệu người dùng.
- `AUDIT`, `PURGE`, `OVERKILL`, `SAVEAS`, `PLOT` phải được chạy trong quy trình xác nhận prompt hoặc API được kiểm thử cho phiên bản cụ thể; không thực hiện cleanup phá hủy mặc định.
- Lưu `*.working.dwg` trước, chỉ chuyển thành bản giao khi kiểm tra file tồn tại, kích thước hợp lý, reopen được và người dùng cho phép ghi đè.

### 21.2 Validator tích hợp
Dùng `../tools/validate_dxf.py` để kiểm tra DXF có cấu trúc, layer, đối tượng, bounding box, entity dimensions sơ bộ. Kiểm tra này không phải xác nhận TCVN. DWG phải được kiểm bằng AutoCAD hoặc chuyển DXF trên bản sao trước; tuyệt đối không đổi phần mở rộng DWG thành DXF.

### 21.3 Quality gate
`NOT_EXECUTED` khi chưa có AutoCAD thực; `EXECUTED_UNVERIFIED` khi chỉ gọi API thành công; `GEOMETRY_CHECKED` khi đã kiểm số liệu; `SHEET_CHECKED` khi đã so PDF; `READY_FOR_ENGINEER_REVIEW` khi không có lỗi tự động; `APPROVED` chỉ theo phê duyệt có người chịu trách nhiệm.


## 22. v1.1 Executable Bridge — primary runtime contract

Read `../README.md`, `../bridge/geometry.py`, `../bridge/server.py`, and `../bridge/worker.py` before issuing executable jobs. v4 supports **new 2D DWG** from structured JSON only: line, circle, polyline. Do not claim modify/plot/3D features are implemented in bridge. Do not generate arbitrary Python/AutoLISP and send it to bridge. Use only `POST /v1/draw` with authorized local token. On TIMEOUT, never retry automatically: AutoCAD may have an unsaved drawing. Never expose port outside localhost. Run offline tests first; run Windows smoke test before production. Output status `EXECUTED_UNVERIFIED` and TCVN `NOT_CHECKED`.


## DSH AutoCAD MCP Execution Contract v5.0

Runtime `autocad_agent.mcp_server` implements `cad_capabilities`, `cad_template`, `cad_validate`, `cad_preview`, `cad_prepare`, `cad_create_dwg`, `cad_audit_dxf`, `cad_catalog`, `cad_check_project_rules`, `cad_screen_standards`, `cad_probe_autocad`. **Only claim functions explicitly returned by `cad_capabilities`.**

Workflow: derive concise JSON job -> `cad_validate` -> `cad_preview` -> human reviews DXF/PDF -> `cad_prepare` -> human manually runs `python -m autocad_agent.cli approve <ticket>` -> `cad_create_dwg(ticket)` -> inspect DWG in AutoCAD 2025.

No AutoCAD editing of existing DWG, no true scale-accurate layout plotting, no 3D model, no certified TCVN clause testing. Do NOT invent tool calls. All templates are `concept_only` and use illustrative defaults. Source standard catalog is **not** a validated standard clause. Show `NOT_CHECKED` for TCVN compliance. DSH approval policy and out-of-band CLI approval both matter; tool cannot approve itself.


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
