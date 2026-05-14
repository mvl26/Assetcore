# IMM-09 — UAT Script
## User Acceptance Test Cases

**Module:** IMM-09  
**Version:** 1.0  
**Ngày:** 2026-04-17  
**Trạng thái:** Draft — Chờ ký duyệt  
**Tester:** QA Engineer / BA Lead  
**Environment:** UAT Server — site: uat.assetcore.vn

---

## Seed Data (Dữ liệu chuẩn bị)

### Assets

| Asset Name | Asset Ref | Category | Risk Class | Status | Serial | Dept | Warranty Exp |
|---|---|---|---|---|---|---|---|
| Máy thở Drager Evita V800 | ACC-ASS-2026-00042 | Ventilator | Class III | Active | DRG-2024-001234 | ICU | 2027-12-31 |
| Monitor Philips MX550 | ACC-ASS-2026-00055 | Patient Monitor | Class II | Active | PHL-2023-005678 | Ward 2 | 2025-06-30 (expired) |
| Máy bơm tiêm Braun | ACC-ASS-2026-00061 | Infusion Pump | Class II | Active | BRN-2025-009012 | OR 1 | 2028-03-31 |
| Defib ZOLL M Series | ACC-ASS-2026-00033 | Defibrillator | Class III | Active | ZOL-2022-003456 | Ward 3 | 2024-12-31 (expired) |
| X-Quang Di Động | ACC-ASS-2026-00070 | X-Ray Mobile | Class III | Active | XRM-2024-007890 | Radiology | 2027-06-30 |

### Incident Reports (pre-created)

| IR Ref | Asset | Reported By | Description |
|---|---|---|---|
| IR-2026-00123 | ACC-ASS-2026-00042 | bs.hung@hospital.vn | Máy thở báo alarm E-04, không tạo được áp suất |
| IR-2026-00124 | ACC-ASS-2026-00055 | dd.hanh@hospital.vn | Màn hình monitor không sáng |
| IR-2026-00125 | ACC-ASS-2026-00061 | bs.lan@hospital.vn | Bơm tiêm báo lỗi occlusion liên tục |

### PM Work Orders (pre-created & submitted)

| PM WO | Asset | Status | Failure Note |
|---|---|---|---|
| PM-WO-2026-00088 | ACC-ASS-2026-00033 | Halted–Major Failure | Battery module không sạc |
| PM-WO-2026-00092 | ACC-ASS-2026-00070 | Completed | Minor: tay cầm lỏng |

### Users & Roles

| User | Email | Role |
|---|---|---|
| Workshop Manager | manager.ws@hospital.vn | Workshop Manager |
| KTV Nguyễn Văn A | ktv.anha@hospital.vn | KTV HTM |
| KTV Lê Thị Bình | ktv.binh@hospital.vn | KTV HTM |
| Nhân viên kho | kho.vt@hospital.vn | Kho vật tư |
| Trưởng ICU | truong.icu@hospital.vn | Trưởng khoa phòng |
| PTP Khối 2 | ptp.k2@hospital.vn | PTP Khối 2 |

### Spare Parts (pre-stocked in Warehouse: Workshop-Store)

| Item Code | Item Name | Stock Qty | Unit Price |
|---|---|---|---|
| CAP-100UF-25V | Tụ điện 100uF 25V | 5 Cái | 25,000 VNĐ |
| FUSE-5A-250V | Cầu chì 5A 250V | 10 Cái | 15,000 VNĐ |
| BATT-ZOLL-M | Pin thay thế ZOLL M Series | 2 Cái | 2,500,000 VNĐ |
| RELAY-24V | Relay 24V DC | 3 Cái | 120,000 VNĐ |

### Stock Entries (pre-created for test use)

| Stock Entry | Items | WO Reference |
|---|---|---|
| STE-2026-00456 | CAP-100UF-25V × 2, FUSE-5A-250V × 1 | WO-CM-2026-00042 |
| STE-2026-00457 | BATT-ZOLL-M × 1 | WO-CM-2026-00033 |
| STE-2026-00458 | RELAY-24V × 1 | For TC-09-08 |

---

## Phần 1: Test Cases Chính

---

### TC-09-01: Tạo Repair WO với Incident Report nguồn (BR-09-01 — Happy Path)

**Module:** IMM-09  
**Business Rule:** BR-09-01  
**Priority:** Critical  
**Actor:** Workshop Manager

**Preconditions:**
- Asset `ACC-ASS-2026-00042` status = Active
- Incident Report `IR-2026-00123` đã tồn tại
- User đăng nhập với role Workshop Manager

**Test Steps:**

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|
| 1 | Mở `/imm-09/create` | — | Form tạo WO hiển thị đầy đủ |
| 2 | Chọn Asset | `ACC-ASS-2026-00042` | Auto-fill: Tên thiết bị, serial, risk class = Class III, AssetInfoCard hiển thị |
| 3 | Điền Incident Report | `IR-2026-00123` | Source validated, badge "IR-2026-00123" hiển thị |
| 4 | Để trống PM WO nguồn | — | Không cần — đã có IR |
| 5 | Chọn Loại sửa chữa | Corrective | — |
| 6 | Chọn Ưu tiên | Urgent | — |
| 7 | Điền Mô tả sự cố | "Máy thở không tạo được áp suất, báo alarm E-04" | — |
| 8 | Bấm "Tạo" | — | WO được tạo thành công |

**Expected Results:**
- WO được tạo: `WO-CM-2026-XXXXX`
- `status = Open`
- `Asset.status = Under Repair`
- `Asset Lifecycle Event` tạo với event_type = "repair_opened"
- `sla_target_hours = 24.0` (Class III + Urgent)
- Toast success: "Phiếu sửa chữa đã được tạo"
- Redirect đến `/imm-09/WO-CM-2026-XXXXX`

**Pass/Fail:** ___________  
**Tester:** ___________  
**Ngày:** ___________

---

### TC-09-02: Tạo Repair WO không có nguồn — vi phạm BR-09-01

**Business Rule:** BR-09-01  
**Priority:** Critical  
**Actor:** Workshop Manager

**Test Steps:**

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|
| 1 | Mở `/imm-09/create` | — | Form hiển thị |
| 2 | Chọn Asset | `ACC-ASS-2026-00055` | AssetInfoCard hiển thị |
| 3 | Để trống cả IR và PM WO | — | — |
| 4 | Điền Loại | Corrective | — |
| 5 | Bấm "Tạo" | — | Lỗi block |

**Expected Results:**
- Error message: "Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc"
- WO không được tạo
- Form giữ nguyên dữ liệu đã nhập
- Trường source highlight màu đỏ

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-03: Tạo Repair WO từ PM WO nguồn

**Business Rule:** BR-09-01  
**Priority:** High  
**Actor:** Workshop Manager hoặc CMMS Auto

**Preconditions:**
- PM WO `PM-WO-2026-00088` đang ở status "Halted–Major Failure" cho `ACC-ASS-2026-00033`

**Test Steps:**

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|
| 1 | Tạo WO | Asset: ACC-ASS-2026-00033, PM WO: PM-WO-2026-00088 | — |
| 2 | Điền thông tin còn lại | Priority: Urgent | — |
| 3 | Bấm Tạo | — | WO tạo thành công |

**Expected Results:**
- `source_pm_wo = PM-WO-2026-00088`
- `incident_report = null`
- WO detail hiển thị `RepairSourceBadge` với PM WO ref
- Link từ PM WO sang CM WO được tạo

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-04: Phân công KTV và chẩn đoán

**Priority:** Critical  
**Actor:** Workshop Manager → KTV HTM

**Preconditions:** WO `WO-CM-2026-00042` ở status Open (từ TC-09-01)

**Test Steps:**

| # | Bước | Actor | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|---|
| 1 | Mở WO detail | Workshop Manager | `/imm-09/WO-CM-2026-00042` | Detail hiển thị, DurationTimer chạy |
| 2 | Bấm "Phân công KTV" | Workshop Manager | Chọn `ktv.anha@hospital.vn` | Status = Assigned |
| 3 | KTV đăng nhập, mở WO | KTV Nguyễn Văn A | — | WO hiển thị, action "Bắt đầu chẩn đoán" visible |
| 4 | Bấm "Bắt đầu chẩn đoán" | KTV | — | WO status = Diagnosing, form diagnose mở |
| 5 | Điền nguyên nhân gốc rễ | KTV | Electrical | — |
| 6 | Điền mô tả chi tiết | KTV | "Tụ điện C12 board nguồn bị cháy" | — |
| 7 | Chọn "Cần vật tư = Có" | KTV | — | — |
| 8 | Upload ảnh thiết bị hỏng | KTV | photo_broken.jpg | Ảnh được đính kèm |
| 9 | Bấm "Lưu chẩn đoán" | KTV | — | WO status = Pending Parts |

**Expected Results:**
- `diagnosis_notes` lưu đúng
- `root_cause_category = Electrical`
- Status = Pending Parts
- Notification gửi đến `kho.vt@hospital.vn`
- Lifecycle Event: diagnosis_submitted
- Timeline trên UI cập nhật

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-05: Xuất kho vật tư và xác nhận Stock Entry (BR-09-02)

**Business Rule:** BR-09-02  
**Priority:** Critical  
**Actor:** KTV HTM + Kho vật tư

**Preconditions:** WO ở status Pending Parts

**Test Steps:**

| # | Bước | Actor | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|---|
| 1 | Mở tab Vật tư | KTV | `/imm-09/WO-CM-2026-00042/parts` | SparePartsTable hiển thị |
| 2 | Tìm và thêm vật tư 1 | KTV | CAP-100UF-25V, qty=2 | Hiển thị tồn kho: 5 cái |
| 3 | Thêm vật tư 2 | KTV | FUSE-5A-250V, qty=1 | Hiển thị tồn kho: 10 cái |
| 4 | Để trống Stock Entry | KTV | — | Icon ⚠ đỏ hiển thị |
| 5 | Thử lưu | KTV | — | Lỗi: "CAP-100UF-25V thiếu phiếu xuất kho" |
| 6 | Kho xuất vật tư | Kho vật tư | Tạo Stock Entry → STE-2026-00456 | — |
| 7 | KTV điền stock_entry_ref | KTV | STE-2026-00456 | Icon ✓ xanh hiển thị |
| 8 | Bấm lưu | KTV | — | Vật tư lưu thành công |
| 9 | Bấm "Xác nhận đã có vật tư" | KTV | — | WO status = In Repair |

**Expected Results:**
- `spare_parts_used` table lưu đúng 2 dòng
- `total_parts_cost = 65,000 VNĐ`
- `stock_entry_ref = STE-2026-00456`
- WO status = In Repair
- Lifecycle Event: parts_received

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-06: Vật tư không có Stock Entry — block Submit (BR-09-02)

**Business Rule:** BR-09-02  
**Priority:** Critical

**Test Steps:**

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|
| 1 | Thêm vật tư vào WO | RELAY-24V, qty=1, stock_entry_ref = TRỐNG | — |
| 2 | Gọi API submit_repair_result | Spare parts list với RELAY-24V, stock_entry_ref = null | 400 error |

**Expected Results:**
- API trả về HTTP 400
- Error code: `CM-003`
- Message: "Vật tư 'Relay 24V DC' (dòng 1) thiếu phiếu xuất kho (Stock Entry Reference)"
- WO không chuyển sang Pending Inspection

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-07: Firmware Update — yêu cầu FCR (BR-09-03)

**Business Rule:** BR-09-03  
**Priority:** High  
**Actor:** KTV HTM + Workshop Manager

**Preconditions:** WO `WO-CM-2026-00042` ở status In Repair

**Test Steps:**

| # | Bước | Actor | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|---|
| 1 | KTV đánh dấu "Đã cập nhật Firmware" | KTV | checkbox = True | Popup: "Bạn cần tạo Firmware Change Request" |
| 2 | Thử Submit WO không có FCR | KTV | firmware_updated=True, firmware_change_request=null | Error CM-005 |
| 3 | Tạo FCR | KTV | version_before="2.1.0", version_after="2.3.1" | FCR tạo: FCR-2026-XXXXX, status=Pending Approval |
| 4 | Manager phê duyệt FCR | Workshop Manager | Approve | FCR.status = Approved |
| 5 | KTV link FCR vào WO | KTV | firmware_change_request = FCR-2026-XXXXX | — |
| 6 | Submit repair result | KTV | firmware_updated=True với FCR linked | Success |

**Expected Results:**
- Bước 2: Error code CM-005, WO không Submit
- Bước 6: WO submit thành công
- `Asset.custom_firmware_version` cập nhật = "2.3.1"
- FCR.status = Applied

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-08: Repair Checklist — 100% Pass bắt buộc (BR-09-04)

**Business Rule:** BR-09-04  
**Priority:** Critical  
**Actor:** KTV HTM

**Preconditions:** WO ở status Pending Inspection, checklist có 5 mục

**Test Steps:**

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|
| 1 | Mở Checklist tab | — | ChecklistProgressBar: 0/5 Pass |
| 2 | Điền mục 1–3 = Pass | — | Progress: 3/5 |
| 3 | Điền mục 4 = Fail | — | Mục 4 highlight đỏ, warning hiển thị |
| 4 | Để trống mục 5 | — | — |
| 5 | Bấm "Hoàn thành sửa chữa" | — | Button disabled — không click được |
| 6 | Điền mục 4 = Pass | — | Progress: 4/5 |
| 7 | Điền mục 5 = Pass | — | Progress: 5/5, button enabled |
| 8 | Điền tên Trưởng khoa | BS. Nguyễn Văn Hùng | — |
| 9 | Bấm "Hoàn thành sửa chữa" | — | Confirm dialog |
| 10 | Xác nhận | — | WO Completed |

**Expected Results:**
- Bước 5: nút disabled, không submit được
- Bước 10: WO.status = Completed
- `Asset.status = Active`
- `mttr_hours` tính đúng
- Toast: "Sửa chữa hoàn thành. MTTR: XX.X giờ"
- PDF biên bản bàn giao có thể tải về

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-09: Asset status về Active khi WO Complete (BR-09-05)

**Business Rule:** BR-09-05  
**Priority:** Critical

**Preconditions:** WO đang In Repair, Asset.status = Under Repair

**Test Steps:**

| # | Bước | Kết quả mong đợi |
|---|---|---|
| 1 | Kiểm tra Asset trước | Asset.status = Under Repair |
| 2 | Thử tạo PM WO cho cùng asset | Error: "Thiết bị đang sửa chữa" |
| 3 | Thử tạo Calibration WO | Error: "Thiết bị đang sửa chữa" |
| 4 | Complete Repair WO | WO status = Completed |
| 5 | Kiểm tra Asset sau | Asset.status = Active |
| 6 | Tạo PM WO | Tạo được bình thường |

**Expected Results:**
- Trong lúc sửa: không tạo được PM/Calibration WO
- Sau khi Complete: Asset = Active, có thể tạo WO mới
- `Asset.custom_last_repair_date = today`

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-10: MTTR Calculation — kiểm tra tính toán đúng

**Priority:** High  
**Actor:** System

**Test Setup:**
- WO tạo lúc: 2026-04-14 07:15:00 (thứ Tư)
- WO complete lúc: 2026-04-15 11:45:00 (thứ Năm)
- Working hours: 07:00–17:00, Mon–Fri
- Không có ngày lễ

**Kỳ vọng:**
- 14/04: 07:15 → 17:00 = 9.75h làm việc
- 15/04: 07:00 → 11:45 = 4.75h làm việc
- MTTR = 9.75 + 4.75 = **14.5 giờ**

**Test Steps:**

| # | Bước | Kết quả mong đợi |
|---|---|---|
| 1 | Complete WO tại thời điểm đã thiết lập | WO.status = Completed |
| 2 | Kiểm tra `mttr_hours` | = 14.5 |
| 3 | Kiểm tra `sla_breached` | False (SLA = 24h) |
| 4 | Kiểm tra MTTR Report | mttr_avg cập nhật đúng |

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-11: Emergency Fast-Track — skip Pending Parts

**Priority:** High  
**Actor:** KTV HTM

**Preconditions:** WO với priority=Emergency, không cần vật tư

**Test Steps:**

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|
| 1 | Tạo WO | priority=Emergency, asset=ACC-ASS-2026-00042 | WO: Open, SLA=4h |
| 2 | Assign và chẩn đoán | needs_parts=false | WO chuyển thẳng: Diagnosing → In Repair |
| 3 | Kiểm tra status history | — | Không có trạng thái "Pending Parts" trong timeline |
| 4 | Hoàn thành checklist | — | Complete thành công |

**Expected Results:**
- Timeline chỉ có: Open → Assigned → Diagnosing → In Repair → Pending Inspection → Completed
- Không có bước Pending Parts
- PTP Khối 2 nhận notification "Sửa chữa khẩn cấp đang tiến hành"
- Nếu MTTR > 4h → sla_breached = True

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-12: Cannot Repair — thiết bị không thể sửa

**Priority:** High  
**Actor:** KTV HTM + Workshop Manager

**Test Steps:**

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi |
|---|---|---|---|
| 1 | WO ở status In Repair | — | — |
| 2 | KTV bấm "Không thể sửa" | cannot_repair_reason = "Board nguồn hỏng hoàn toàn, không có phụ tùng thay thế" | Confirm dialog |
| 3 | Xác nhận | — | WO status = Cannot Repair |
| 4 | Kiểm tra Asset | — | Asset.status = Out of Service |
| 5 | Kiểm tra notification | — | Alert gửi Workshop Manager + PTP |
| 6 | Kiểm tra hành động tiếp theo | — | Button "Khởi tạo quy trình EOL (IMM-13/14)" hiển thị |

**Expected Results:**
- `cannot_repair_reason` bắt buộc — không thể để trống
- Asset.status = Out of Service
- Lifecycle Event: cannot_repair
- Không tính MTTR (WO không Complete)

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-13: Tái hỏng trong 30 ngày — Repeat Failure flag

**Priority:** Medium  
**Actor:** Workshop Manager

**Preconditions:**
- WO `WO-CM-2026-00039` cho `ACC-ASS-2026-00061` đã Complete cách đây 15 ngày

**Test Steps:**

| # | Bước | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo WO mới cho `ACC-ASS-2026-00061` | — |
| 2 | Kiểm tra banner trên Create Form | Banner: "⚠ Thiết bị đã được sửa trong 30 ngày qua (WO-CM-2026-00039)" |
| 3 | Tạo WO thành công | `is_repeat_failure = True` |
| 4 | Kiểm tra MTTR Report | First-Time Fix Rate giảm tương ứng |

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-14: MTTR Report — kiểm tra KPI tháng

**Priority:** Medium  
**Actor:** PTP Khối 2

**Preconditions:** Có ít nhất 5 WO Completed trong tháng 4/2026

**Test Steps:**

| # | Bước | Kết quả mong đợi |
|---|---|---|
| 1 | Mở `/imm-09/reports/mttr?year=2026&month=4` | Report hiển thị |
| 2 | Kiểm tra MTTR avg | Khớp với tính toán thủ công từ các WO |
| 3 | Kiểm tra First-Time Fix Rate | = (WO không repeat) / total × 100% |
| 4 | Kiểm tra Backlog count | = WO đang Open + Assigned |
| 5 | Kiểm tra Trend Chart | 6 điểm dữ liệu theo tháng |
| 6 | Xuất PDF/Excel | File tải về đúng định dạng |

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-15: Thiết bị bảo hành — Warranty Claim

**Priority:** Medium  
**Actor:** Workshop Manager

**Preconditions:** Asset `ACC-ASS-2026-00042` có warranty_expiry = 2027-12-31

**Test Steps:**

| # | Bước | Kết quả mong đợi |
|---|---|---|
| 1 | Tạo WO cho asset trong bảo hành | is_warranty_claim = True tự động (hoặc Manager tick) |
| 2 | Kiểm tra thông báo | Banner: "Thiết bị trong thời hạn bảo hành — xem xét claim trước khi xuất kho vật tư" |
| 3 | Điền warranty_claim_ref | "WRN-DRG-2026-001" | — |
| 4 | Hoàn thành sửa chữa | WO Completed, is_warranty_claim = True |
| 5 | Kiểm tra cost report | WO được đánh dấu warranty trong MTTR Report |

**Pass/Fail:** ___________  
**Tester:** ___________

---

### TC-09-16: Phân quyền — KTV không thể tạo WO

**Priority:** High  
**Actor:** KTV HTM (limited permission)

**Test Steps:**

| # | Bước | Kết quả mong đợi |
|---|---|---|
| 1 | KTV đăng nhập | — |
| 2 | Truy cập `/imm-09/create` | Button "Tạo WO" ẩn / không render |
| 3 | Gọi trực tiếp API create_repair_wo | 403 Forbidden — "Bạn không có quyền thực hiện thao tác này" |
| 4 | Mở WO được assign cho KTV | Hiển thị bình thường, action buttons phù hợp |
| 5 | Cố Assign KTV khác | Button "Phân công KTV" ẩn |

**Pass/Fail:** ___________  
**Tester:** ___________

---

## Phần 2: Edge Cases

---

### EC-09-01: Tạo WO khi Asset đã có WO đang mở

**Tình huống:** Manager cố tạo WO thứ hai khi WO đầu tiên chưa đóng

**Test Steps:**
1. WO `WO-CM-2026-00042` đang ở status In Repair
2. Manager tạo WO mới với cùng asset `ACC-ASS-2026-00042`

**Expected:** Error CM-002 — "Thiết bị đang có phiếu sửa chữa đang mở: WO-CM-2026-00042"  
**Actual:** ___________  
**Pass/Fail:** ___________

---

### EC-09-02: FCR version_before = version_after

**Tình huống:** KTV tạo FCR nhưng nhập cùng version

**Test Steps:**
1. Tạo FCR với version_before = "2.1.0", version_after = "2.1.0"

**Expected:** Error CM-014 — "Firmware version trước và sau không thể giống nhau"  
**Actual:** ___________  
**Pass/Fail:** ___________

---

### EC-09-03: Submit WO khi stock_entry_ref không tồn tại trong DB

**Tình huống:** KTV nhập sai mã phiếu xuất kho

**Test Steps:**
1. Nhập stock_entry_ref = "STE-INVALID-99999" (không tồn tại)
2. Submit repair result

**Expected:** Error CM-004 — "Phiếu xuất kho 'STE-INVALID-99999' không tồn tại trong hệ thống"  
**Actual:** ___________  
**Pass/Fail:** ___________

---

### EC-09-04: SLA breach — Class III Emergency > 4 giờ

**Tình huống:** WO Emergency không hoàn thành trong 4 giờ

**Test Steps:**
1. Tạo WO priority=Emergency, risk_class=Class III
2. Đợi 4+ giờ (hoặc mock time)
3. Kiểm tra scheduler check_repair_sla_breach

**Expected:**
- `sla_breached = True` được set
- PTP Khối 2 và BGĐ nhận escalation alert
- WO hiển thị badge "SLA VI PHẠM" màu đỏ

**Actual:** ___________  
**Pass/Fail:** ___________

---

### EC-09-05: Hủy WO — Asset status rollback

**Tình huống:** Manager hủy WO sau khi đã tạo (chưa Assign)

**Test Steps:**
1. WO ở status Open, Asset.status = Under Repair
2. Manager cancel WO (điền lý do)
3. Kiểm tra Asset status

**Expected:**
- WO.status = Cancelled (docstatus = 2)
- Asset.status rollback về "Active"
- Lifecycle Event: repair_cancelled
- Lý do hủy được lưu trong WO

**Actual:** ___________  
**Pass/Fail:** ___________

---

### EC-09-06: Checklist trống khi submit complete_repair

**Tình huống:** KTV gọi complete_repair API với repair_checklist rỗng

**Test Steps:**
1. Gọi `complete_repair` với `repair_checklist = []`

**Expected:**
- Error CM-007: "Phải điền Repair Checklist trước khi hoàn thành sửa chữa"
- WO không Complete

**Actual:** ___________  
**Pass/Fail:** ___________

---

### EC-09-07: Thiếu Trưởng khoa xác nhận

**Tình huống:** KTV điền checklist 100% Pass nhưng để trống `dept_head_name`

**Test Steps:**
1. Tất cả checklist items = Pass
2. Để trống `dept_head_name`
3. Bấm "Hoàn thành sửa chữa"

**Expected:**
- Error CM-013: "Phải có xác nhận của Trưởng khoa phòng trước khi hoàn thành"
- WO không Complete

**Actual:** ___________  
**Pass/Fail:** ___________

---

### EC-09-08: WO từ PM WO nguồn — link phải chính xác

**Tình huống:** PM WO nguồn không tồn tại

**Test Steps:**
1. Tạo WO với source_pm_wo = "PM-WO-INVALID-99999"

**Expected:**
- Error: "PM Work Order 'PM-WO-INVALID-99999' không tồn tại"
- WO không được tạo

**Actual:** ___________  
**Pass/Fail:** ___________

---

## Phần 3: Regression & Integration Tests

| TC | Mô tả | Link với Module |
|---|---|---|
| IT-09-01 | WO tạo từ PM failure → source_pm_wo link đúng | IMM-08 |
| IT-09-02 | Asset status lifecycle: Active → Under Repair → Active | Asset Core |
| IT-09-03 | Stock Entry từ Frappe Stock Module được link đúng | ERPNext Stock |
| IT-09-04 | MTTR aggregation chạy đúng sau monthly scheduler | Scheduler |
| IT-09-05 | Lifecycle Event tạo đầy đủ cho mọi status transition | Audit Trail |
| IT-09-06 | FCR → Asset firmware_version update khi applied | Asset Core |
| IT-09-07 | Cannot Repair → IMM-13 EOL process được kích hoạt | IMM-13/14 |
| IT-09-08 | WO Completed → PM Schedule không block tạo WO mới | IMM-08 |
| IT-09-09 | Print Format "Biên bản bàn giao" xuất đúng dữ liệu | Print |
| IT-09-10 | Notification đến đúng actor theo từng bước workflow | Notification |

---

## Sign-off

| Vai trò | Tên | Chữ ký | Ngày |
|---|---|---|---|
| QA Lead | | | |
| BA Lead | | | |
| Workshop Manager (UAT) | | | |
| PTP Khối 2 (UAT) | | | |
| Dev Lead | | | |

**Kết quả UAT tổng thể:**  
- Tổng số TC: 24 (16 main + 8 edge)  
- Passed: ___  
- Failed: ___  
- Blocked: ___  
- Pass rate: ___%  

**Ghi chú:**  
___________________________________  
___________________________________
