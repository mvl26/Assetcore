# Technical Specification: IMM-04 – Lắp đặt, định danh và kiểm tra ban đầu

Bản đặc tả kiến trúc (Architectural Spec) dựa trên tiêu chuẩn thiết kế HTM Lifecycle và Hệ khung 18 điểm kiểm soát của AssetCore (IMMIS).

---

### 1. Mục tiêu
Tiếp nhận bàn giao thiết bị từ quá trình Procurement, đối chiếu tính trọn vẹn của thiết bị/phụ kiện/hồ sơ, tiến hành lắp đặt, thực hiện định danh đa lớp (Multi-layer ID), thiết lập mốc Baseline (thông số kỹ thuật ban đầu) và kiểm tra chất lượng (Initial Inspection) tạo "Release Gate" trước khi đưa vào Clinical Use.

### 2. Phạm vi
- Bắt đầu: Khi thiết bị vật lý đã được vận chuyển đến chân công trình khoa phòng (Kết thúc Procurement Transport).
- Kết thúc: Điểm neo khi thiết bị được dán thẻ định danh (Tagging), vượt qua các khâu đo lường an toàn điện/bức xạ/hoạt động và chính thức chuyển trạng thái `Available for clinical use` trên lõi ERPNext.

### 3. Giả định
- Giai đoạn Mua sắm (Procurement) đã tạo đủ dữ liệu Master Data như Item, Manufacturer, Supplier và sinh ra Purchase Receipt thành công.
- Không gian/vị trí lắp đặt (Site) đã được thi công thô trước đó.

### 4. Actor (Vai trò thực thi thực tế)
- `Biomed Engineer` (Kỹ sư y sinh của viện): Đảm nhiệm đo kiểm Baseline, dán nhãn định danh và chốt Acceptance.
- `Vendor Technician` (Kỹ sư hãng/nhà thầu): Người trực tiếp thi công lắp đặt và cấu hình phần cứng.
- `Clinical Dept Head` (Khối lâm sàng/Khoa nhận): Cử đại diện giám sát vật lý và tham gia Confirm bàn giao.
- `QA/Regulatory Officer` (Kiểm định viên): Nếu máy móc thuộc loại yêu cầu chứng chỉ kiểm định an toàn/Cục đo lường.

### 5. Workflow states
| State | Mô tả |
|---|---|
| `Draft` | Bản nháp khởi tạo thông tin chuẩn bị bàn giao. |
| `Pending Site Verify` | Kỹ sư rà soát xem lưới điện/khí có đáp ứng thông số lắp máy chưa. |
| `To Be Installed` | Tình trạng lý tưởng, cho phép Hãng khui thùng. |
| `Installing` | Kỹ sư Hãng đang bắt ốc, cấu hình phần cứng/phần mềm. |
| `Identification & Tagging`| Nhập mã pháp lý, serial, dán bar-code/QR nội bộ bệnh viện đa lớp. |
| `Initial Inspection` | Kỹ sư viện nhảy vào đo thông số điện, dòng dò, Calibration -> Tạo Baseline. |
| `Clinical Hold` | Máy móc "rớt" bài test hoặc chờ Cục Đo Lường thẩm định. Cấm dùng. |
| `Clinical Release` | Vượt qua mọi rào cản, chính thức đẩy trạng thái thành Active Asset. |

### 6. State machine (Bảng chuyển đổi hệ thống)
- `Draft` -> `Pending Site Verify` (Submit)
- `Pending Site Verify` -> `To Be Installed` (Confirm Site Ready)
- `To Be Installed` -> `Installing` (Start Installation Work)
- `Installing` -> `Identification & Tagging` (Mark Physical Install Complete)
- `Identification & Tagging` -> `Initial Inspection` (Save Tags & Gen Baseline Form)
- `Initial Inspection` -> `Clinical Release` (Pass all Baseline Checks)
- `Initial Inspection` -> `Clinical Hold` (Fail Baseline or Await Govt Auth)
- `Clinical Hold` -> `Clinical Release` (Upload clearance doc & Re-pass)
- `*` -> `Cancelled / Returned` (Nếu máy chết cứng không thể cứu chữa)

### 7. DocType (Dữ liệu nền tảng)
1. Lõi: `Installation & Initial Inspection` (DocType)
2. Child: `Multi-Layer Identity Log` (Lưu 5 loại mã vạch chồng chéo)
3. Child: `Installation Baseline Test` (Bảng lưu các tiêu chí test an toàn tĩnh)

### 8. Field list (Đặc tả trường dữ liệu quan trọng)
- **Main Doc:** 
  - `master_item`: Link, Bắt buộc (Bản thể Master từ kho)
  - `po_reference`: Link, Bắt buộc (Móc về chứng từ mua)
  - `visual_inspection`: Select (Hỏng vỏ/Hỏng mạch/Đạt), Bắt buộc.
- **Child (Identification):**
  - `identity_type`: Select (Internal Asset Tag, Barcode, Vendor Serial Number, BYT_Law_Code, Legacy Code).
  - `identity_value`: Data, Bắt buộc.
- **Child (Baseline):**
  - `parameter`: Data (Tên chuẩn đầu ra, vd: Dòng rò).
  - `measured_value`: Float
  - `result`: Select (Pass/Fail).

### 9. Permission matrix (Quyền tương tác Actor)
- `Biomed Engineer`: Read/Write toàn bộ, Submit chuyển node `Initial Inspection` -> `Clinical Release`.
- `Vendor Technician` (Bắn API từ App ngoài): Write tại node `Installing`, chỉ cho phép upload ảnh và log công việc.
- `Clinical Dept Head`: Read-only, nhấn nút `Ack` (Acknowledge - Thừa nhận) máy đã vào Khoa mình.

### 10. Validation rules
- Không cho phép nhập 2 `identity_value` giống nhau trong hệ thống (Check trùng lắp Multi-layer Identity ID trên toàn bộ ERP).
- Khi Submit tại nút `Initial Inspection`, nếu bất kỳ `Baseline Test` nào có result = 'Fail', BẮT BUỘC hệ thống đá trạng thái sang `Clinical Hold`, cấm không cho sang `Release`.

### 11. Event model
- `imm04.install.started`: Đánh dấu Time-to-Install, lưu timestamp gửi QA.
- `imm04.identity.assigned`: Tạo Record gốc vào `Asset` module của ERPNext (Sinh mã tài sản số học).
- `imm04.clinical.released`: Kích hoạt vòng đời sử dụng, đổi trạng thái Asset Asset sang `In Use` và setup Ngày Khấu Hao = Date.now.

### 12. Approval matrix
Cho máy trị giá lớn (Ví dụ > 1 Tỷ / Life-support device):
- Step 1: Kỹ sư lập biên bản Initial Inspection (Biomed Engineer duyệt).
- Step 2: Kỹ sư Trưởng (Chief Engineer) Review thông số Calibration.
- Step 3: Giám Đốc/Hội đồng (Board Level) bấm Release.

### 13. QMS controls
Toàn bộ `Baseline Test` sinh ra làm nền tảng (Foundation) cho mọi kỳ Preventive Maintenance sau này. Không có Baseline -> Các kỹ sư đi sau không thể biết máy này sinh ra chuẩn là bao nhiêu dB, mA hay kVp. Đây là nguyên tắc cốt lõi của QMS trong cấu hình thiết bị y tế.

### 14. Audit trail
Track mọi IP, user, timestamp lúc chuyển State. Bản lưu trữ Audit Table đính kèm không bao giờ được phép `Delete()`. Chữ ký trên Form lúc `Release` phải ghi nhận Tọa độ GPS hoặc Access Token để đề phòng Ký hộ.

### 15. ERPNext mapping
Ghi đè hoặc sinh song song bảng (Override mechanism):
- Móc chặt vào DocType: `Asset`.
- Override tiến trình `Asset Receipt` vốn rất đơn giản của ERPNext bằng DocType đồ sộ này, không cho phép User tạo Asset trực tiếp (Bấm New) mà chỉ được sinh qua ống xả của form IMM-04.

### 16. API / automation trigger
- API `api/method/imm04.receive_vendor_log`: Mở Endpoint để máy chủ của cấu trúc Nhà cung cấp (Vendor) đẩy log tự chụp hình lúc dỡ bo mạch.
- Bắn thông điệp sang Hệ thống Tài chính `Asset Capitalization` ngay khi chốt `Clinical Release`.

### 17. KPI / dashboard
- `Time to Release Gate`: (Avg Days), Số ngày tính từ khi khui hộp đến khi Bác sĩ được phép dùng đo đạc.
- `DOA Rate` (Dead On Arrival): Tỷ lệ máy hỏng ngay lúc Install chia cho tổng số. Rất mạnh để phạt Partner.
- `Hold Ageing`: Danh sách máy bị kẹt ở `Clinical Hold` quá 15 ngày trên viện.

### 18. Rủi ro và ngoại lệ
- Biến dòng điện (Surge/Spike) cháy thiết bị ngay ở lúc `Installing`: Dừng luồng, tạo exception trigger luồng `Return Goods` & khiếu nại bảo hiểm.
- Số Serial của Hãng bị mờ, không trùng với tờ khai hải quan: Rớt ngay tại bước `Pending Site Verify / Identification`, gọi thanh tra vật tư can thiệp.
