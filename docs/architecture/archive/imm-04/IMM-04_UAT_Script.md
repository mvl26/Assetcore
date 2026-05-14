# IMM-04 — UAT Script
## User Acceptance Testing — Asset Installation & Commissioning

**Module:** IMM-04  
**Version:** 1.0  
**Ngày:** 2026-04-17  
**Trạng thái:** Draft  
**Người thực hiện UAT:** TBYT Officer, Biomed Engineer, QA Officer, Board/CEO

---

## 1. Test Cases

### 1.1 Nhóm A — Tạo và Quản Lý Hồ Sơ (BR-04-01, BR-04-03)

---

**TC-04-01: Tạo Commissioning thành công từ PO**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-01 |
| **Title** | Tạo Commissioning record mới từ Purchase Order hợp lệ |
| **Business Rule** | BR-04-01 — Asset chỉ được tạo qua pipeline IMM-04 |
| **Actor** | TBYT Officer |
| **Precondition** | PO-2026-00023 tồn tại, status = To Receive; Item ITM-XRAY-PHILIPS-001 có is_fixed_asset=True, risk_class=C |
| **Steps** | 1. Đăng nhập với role TBYT Officer <br> 2. Vào `/imm-04/new` <br> 3. Chọn PO: `PO-2026-00023` <br> 4. Xác nhận Item, Vendor, Asset Category đã auto-fill <br> 5. Chọn Location: `Khoa Chẩn Đoán Hình Ảnh` <br> 6. Chọn Commissioned By: `biomed.nguyen@hospital.vn` <br> 7. Chọn Clinical Head: `dr.tran@hospital.vn` <br> 8. Nhập Reception Date: `2026-04-17` <br> 9. Click "Lưu" |
| **Expected Result** | - Record tạo thành công với naming `ACC-2026-XXXXX` <br> - Status = `Draft_Reception` <br> - Risk Class = `C` (auto-fill) — hiển thị badge đỏ <br> - 4 Document Record được tạo tự động: CO, CQ, Manual, License (tất cả status = Pending) <br> - 1 Lifecycle Event ghi: event_type=status_changed, to=Draft_Reception, actor=TBYT Officer |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-02: Block tạo Asset trực tiếp trong ERPNext (BR-04-01)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-02 |
| **Title** | Không thể tạo Asset ERPNext mà không qua IMM-04 |
| **Business Rule** | BR-04-01 |
| **Actor** | Biomed Engineer |
| **Precondition** | User có quyền System Manager (thử nghiệm bypass) |
| **Steps** | 1. Đăng nhập với role Biomed Engineer <br> 2. Vào ERPNext → Asset → New <br> 3. Chọn Item Code = `ITM-XRAY-PHILIPS-001` <br> 4. Cố gắng Save |
| **Expected Result** | - Frappe throw error: "Tài Sản thiết bị y tế phải được tạo qua Phiếu Nghiệm Thu IMM-04. Không thể tạo trực tiếp." <br> - Asset không được lưu |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-03: Validate Serial Number trùng (VR-01)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-03 |
| **Title** | Hệ thống block Serial Number đã tồn tại trong Asset khác |
| **Business Rule** | BR-04-03 — VR-01 |
| **Actor** | Biomed Engineer |
| **Precondition** | Asset `ACC-ASS-2025-00041` đã có vendor_sn = `PHI-XRAY-2025-SN11111` <br> Commissioning ACC-2026-00001 ở status Identification |
| **Steps** | 1. Mở ACC-2026-00001 → tab Identification <br> 2. Nhập Serial Number: `PHI-XRAY-2025-SN11111` <br> 3. Click ra ngoài field (blur event) |
| **Expected Result** | - Ngay khi blur: hiển thị error inline màu đỏ: "VR-01: Serial đã được gán cho thiết bị ACC-ASS-2025-00041" <br> - Nút "Xác Nhận Định Danh" disabled <br> - Record không được lưu nếu cố submit |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-04: Validate Serial Number hợp lệ và unique (VR-01)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-04 |
| **Title** | Serial Number mới, unique được chấp nhận |
| **Business Rule** | BR-04-03 — VR-01 |
| **Actor** | Biomed Engineer |
| **Precondition** | Commissioning ở status Identification; SN `PHI-XRAY-2026-SN98765` chưa tồn tại |
| **Steps** | 1. Mở ACC-2026-00001 → Identification tab <br> 2. Nhập SN: `PHI-XRAY-2026-SN98765` <br> 3. Click blur → quan sát validation <br> 4. Nhập Internal Tag: `BVNK-CDHA-2026-001` <br> 5. Click "Xác Nhận Định Danh" |
| **Expected Result** | - Sau blur: hiển thị checkmark xanh "Serial hợp lệ" <br> - QR code tự động generate và hiển thị <br> - Status chuyển sang `Initial_Inspection` <br> - Lifecycle Event ghi: event_type=tag_assigned |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

### 1.2 Nhóm B — Gate Tài Liệu (BR-04-02, VR-02)

---

**TC-04-05: Block chuyển trạng thái khi thiếu tài liệu bắt buộc (VR-02)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-05 |
| **Title** | Gate G01 block chuyển sang To_Be_Installed khi CO còn Pending |
| **Business Rule** | BR-04-02 — VR-02 |
| **Actor** | TBYT Officer |
| **Precondition** | Commissioning ACC-2026-00001 ở status Pending_Doc_Verify; CO status = Pending (chưa upload) |
| **Steps** | 1. Mở ACC-2026-00001 <br> 2. CQ, Manual, License đều = Received <br> 3. CO = Pending <br> 4. Click "Tiến Hành Lắp Đặt" |
| **Expected Result** | - Popup error: "VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: Chứng Nhận Xuất Xứ (CO)" <br> - Status không thay đổi <br> - Hướng dẫn user upload CO |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-06: Chuyển trạng thái thành công khi đủ tài liệu (G01 Pass)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-06 |
| **Title** | G01 Pass — Chuyển sang To_Be_Installed khi 100% mandatory docs = Received |
| **Business Rule** | BR-04-02 — VR-02 |
| **Actor** | TBYT Officer |
| **Precondition** | Commissioning ở Pending_Doc_Verify; CO, CQ, Manual, License đều status = Received |
| **Steps** | 1. Mở ACC-2026-00001 <br> 2. Xác nhận tất cả tài liệu = Received (progress bar = 100%) <br> 3. Tick "Cơ Sở Hạ Tầng Đạt" <br> 4. Click "Tiến Hành Lắp Đặt" |
| **Expected Result** | - Status = `To_Be_Installed` <br> - Lifecycle Event ghi transition G01 Pass <br> - Nút "Bắt Đầu Lắp Đặt" xuất hiện |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-07: Upload tài liệu và auto-validate expiry**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-07 |
| **Title** | Upload giấy phép đã hết hạn bị block |
| **Business Rule** | BR-04-02 |
| **Actor** | TBYT Officer |
| **Precondition** | Commissioning ở Pending_Doc_Verify |
| **Steps** | 1. Click Upload trên row "Giấy Phép Lưu Hành" <br> 2. Chọn file PDF <br> 3. Nhập Expiry Date: `2025-12-31` (đã qua) <br> 4. Click Lưu |
| **Expected Result** | - Error: "Tài liệu 'Giấy Phép Lưu Hành (Bộ Y Tế)' đã hết hạn vào ngày 2025-12-31. Vui lòng cập nhật." <br> - Document row không cập nhật status = Received |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

### 1.3 Nhóm C — Baseline Test & Gate G03 (BR-04-04, VR-03)

---

**TC-04-08: Block Release khi baseline fail (VR-03)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-08 |
| **Title** | Gate G03 chặn release khi có critical item Fail |
| **Business Rule** | BR-04-04 — VR-03 |
| **Actor** | Biomed Engineer |
| **Precondition** | Commissioning ở Initial_Inspection; checklist có 4 items, CHK-002 là critical item |
| **Steps** | 1. Mở tab Checklist <br> 2. Điền CHK-001: Pass, measured=220V <br> 3. Điền CHK-002 (QUAN TRỌNG): Fail, measured=3.5mA (expected max=2.0mA) <br> 4. Điền CHK-003, CHK-004: Pass <br> 5. Click "Nộp Kết Quả Kiểm Tra" |
| **Expected Result** | - Error: "VR-03 (Gate G03): Có 1 mục kiểm tra quan trọng chưa đạt: Dòng rò vỏ máy (IEC 60601-1)" <br> - Status chuyển sang `Re_Inspection` <br> - CHK-002 row highlight đỏ <br> - Checklist bị lock (read-only) <br> - Lifecycle Event ghi: event_type=status_changed, to=Re_Inspection |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-09: Baseline Pass cho thiết bị Class A/B → trực tiếp vào Clinical Release**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-09 |
| **Title** | G03 Pass + risk_class=B → không vào Clinical Hold |
| **Business Rule** | BR-04-04, BR-04-05 (negative case) |
| **Actor** | Biomed Engineer |
| **Precondition** | Commissioning với risk_class=B ở Initial_Inspection; không có NC Open |
| **Steps** | 1. Điền tất cả checklist items = Pass <br> 2. Click "Nộp Kết Quả Kiểm Tra" |
| **Expected Result** | - Status = `Initial_Inspection` với overall_inspection_result = Pass <br> - Nút "Phê Duyệt Release" xuất hiện (cho Board) <br> - Không có Clinical Hold notification <br> - overall_inspection_result = "Pass" |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

### 1.4 Nhóm D — Clinical Hold Radiation (BR-04-05, VR-07)

---

**TC-04-10: Auto-hold thiết bị Class C sau baseline pass (VR-07)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-10 |
| **Title** | Thiết bị Class C tự động vào Clinical Hold sau G03 Pass |
| **Business Rule** | BR-04-05 — VR-07 |
| **Actor** | Biomed Engineer |
| **Precondition** | Commissioning với risk_class=C ở Initial_Inspection; qa_officer = qa.pham@hospital.vn |
| **Steps** | 1. Điền tất cả checklist items = Pass <br> 2. Click "Nộp Kết Quả Kiểm Tra" |
| **Expected Result** | - Status tự động = `Clinical_Hold` (không phải Clinical_Release) <br> - Alert modal hiển thị: "Thiết bị phân loại C phải có Giấy Phép Lưu Hành BYT" <br> - Email + In-app notification gửi tới qa.pham@hospital.vn <br> - Nút "Phê Duyệt Release" disabled; hiển thị "Chờ QA Officer gỡ Hold" <br> - Lifecycle Event: event_type=status_changed, to=Clinical_Hold, remarks="VR-07: auto-hold risk_class=C" |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-11: QA gỡ Clinical Hold thành công sau upload license**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-11 |
| **Title** | Clinical Hold được gỡ khi QA upload License hợp lệ |
| **Business Rule** | BR-04-05 — G04 |
| **Actor** | QA Officer |
| **Precondition** | Commissioning ở Clinical_Hold; License row có status = Pending |
| **Steps** | 1. Đăng nhập với role QA Officer <br> 2. Mở ACC-2026-00001 → tab Documents <br> 3. Upload file PDF cho "Giấy Phép Lưu Hành" <br> 4. Nhập Expiry Date: `2028-06-30`, Doc Number: `1234/QĐ-BYT` <br> 5. Click "Gỡ Clinical Hold" |
| **Expected Result** | - Status = `Clinical_Release` (pending board) <br> - Nút "Phê Duyệt Release" xuất hiện cho Board/CEO <br> - Lifecycle Event: event_type=hold_cleared <br> - Thông báo gửi Board/CEO |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

### 1.5 Nhóm E — Non-Conformance (BR-04-06, VR-04)

---

**TC-04-12: Block Release khi còn NC Open (VR-04)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-12 |
| **Title** | Gate G05 chặn Clinical Release khi có NC chưa đóng |
| **Business Rule** | BR-04-06 — VR-04 |
| **Actor** | Board/CEO |
| **Precondition** | Commissioning ở Clinical_Release (pending); NC-ACC-2026-00001-01 status = Under Review |
| **Steps** | 1. Đăng nhập với role Board/CEO <br> 2. Chọn board_approver = ceo.nguyen@hospital.vn <br> 3. Click "Phê Duyệt Release" |
| **Expected Result** | - Error: "VR-04 (Gate G05): Còn 1 Phiếu Không Phù Hợp chưa đóng: NC-ACC-2026-00001-01. Vui lòng giải quyết trước khi Release." <br> - Asset không được tạo <br> - Status không thay đổi |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-13: Báo cáo DOA và chuyển Return_To_Vendor**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-13 |
| **Title** | Vendor khai báo DOA → tạo NC Critical → Return_To_Vendor |
| **Business Rule** | BR-04-06 |
| **Actor** | Vendor Tech, Workshop Manager |
| **Precondition** | Commissioning ở Installing |
| **Steps** | 1. Vendor Tech click "Khai Báo DOA / Lỗi" <br> 2. Điền: nc_type=DOA, severity=Critical, description="Mainboard không khởi động" <br> 3. Upload ảnh bằng chứng <br> 4. Submit <br> 5. Workshop Manager xem xét → click "Trả Hàng Vendor" |
| **Expected Result** | - NC record tạo với nc_code = NC-ACC-2026-00001-01, severity=Critical <br> - Status = `Non_Conformance` <br> - Sau "Trả Hàng Vendor": status = `Return_To_Vendor` (TERMINAL) <br> - Lifecycle Events ghi đủ transition history |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

### 1.6 Nhóm F — Audit Trail & Immutability (BR-04-07, VR-06)

---

**TC-04-14: Baseline test lock sau khi submit (BR-04-07)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-14 |
| **Title** | Checklist baseline bị lock sau khi nộp kết quả |
| **Business Rule** | BR-04-07 — VR-06 |
| **Actor** | Biomed Engineer |
| **Precondition** | Baseline checklist đã được submit (status = Re_Inspection hoặc Initial_Inspection passed) |
| **Steps** | 1. Mở Commissioning ở status ≠ Initial_Inspection <br> 2. Vào tab Checklist <br> 3. Cố gắng click vào ô Result của bất kỳ checklist item nào |
| **Expected Result** | - Tất cả fields trong Checklist tab = read-only <br> - Không có Edit button <br> - Tooltip: "Kết quả baseline đã được khóa sau khi nộp" |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-15: Block sửa Lifecycle Event (VR-06 — Immutable Audit Trail)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-15 |
| **Title** | Lifecycle Event không thể bị sửa bởi bất kỳ user nào |
| **Business Rule** | BR-04-07 — VR-06 |
| **Actor** | CMMS Admin (thử nghiệm bypass) |
| **Precondition** | Commissioning có ít nhất 1 lifecycle event đã lưu |
| **Steps** | 1. Đăng nhập với role System Manager / CMMS Admin <br> 2. Mở Commissioning → tab Timeline <br> 3. Thử sửa actor hoặc timestamp của một event row <br> 4. Click Save |
| **Expected Result** | - Error: "VR-06: Nhật ký sự kiện vòng đời không được chỉnh sửa. Dữ liệu audit trail bất biến theo quy định ISO 13485 §4.2.5." <br> - Record không được lưu <br> - Timeline tab chỉ hiển thị read-only |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

### 1.7 Nhóm G — Clinical Release & Board Approval (BR-04-08)

---

**TC-04-16: Clinical Release thành công — tạo Asset và trigger downstream**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-16 |
| **Title** | Toàn bộ flow commissioning thành công → Active Asset + PM Schedule + Device Record |
| **Business Rule** | BR-04-08 — G05 + G06 |
| **Actor** | Board/CEO |
| **Precondition** | Tất cả gates G01-G05 pass; không có NC Open; board_approver đã chọn |
| **Steps** | 1. Đăng nhập với role Board/CEO <br> 2. Mở Commissioning ở status Clinical_Release <br> 3. Chọn board_approver = ceo.nguyen@hospital.vn <br> 4. Nhập approval_remarks <br> 5. Click "Phê Duyệt Release" |
| **Expected Result** | - Asset ERPNext tạo với status = Active <br> - `Asset.vendor_sn = commissioning.vendor_sn` <br> - `Asset.commissioning_date = today` <br> - Commissioning.asset_ref = Asset.name <br> - Handover Document PDF tạo tự động <br> - PM Schedule tạo (IMM-08) — queue job <br> - Device Record tạo (IMM-05) — queue job <br> - Lifecycle Event: event_type=released <br> - Notification gửi toàn bộ actors |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

**TC-04-17: Block Release khi board_approver trống (G06)**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-17 |
| **Title** | Gate G06 block khi không có Board Approver |
| **Business Rule** | BR-04-08 |
| **Actor** | Biomed Engineer (thử nghiệm vượt quyền) |
| **Precondition** | Commissioning ở Clinical_Release; board_approver = null |
| **Steps** | 1. Mở Commissioning <br> 2. Không chọn board_approver <br> 3. Gọi API approve_clinical_release trực tiếp |
| **Expected Result** | - Error: "Gate G06: Cần chọn Người Phê Duyệt Ban Giám Đốc để hoàn thành Clinical Release." <br> - HTTP 422 <br> - Asset không được tạo |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

### 1.8 Nhóm H — Barcode Scanner Integration

---

**TC-04-18: Quét barcode USB HID điền SN tự động**

| Trường | Nội Dung |
|---|---|
| **TC-ID** | TC-04-18 |
| **Title** | USB barcode scanner tự động điền Serial Number field |
| **Business Rule** | BR-04-03 |
| **Actor** | Biomed Engineer |
| **Precondition** | USB barcode scanner kết nối với máy tính; Commissioning ở status Identification |
| **Steps** | 1. Mở tab Identification <br> 2. Focus vào trang (không cần click field SN) <br> 3. Quét barcode trên thân máy bằng scanner USB |
| **Expected Result** | - SN field tự động điền giá trị từ scanner <br> - Real-time validation VR-01 chạy ngay <br> - Nếu unique: checkmark xanh <br> - Không gây ra noise keydown trong các field khác |
| **Pass/Fail** | ☐ Pass ☐ Fail |

---

## 2. Edge Cases

### 2.1 Boundary Conditions

| ID | Scenario | Input | Expected Behavior |
|---|---|---|---|
| EC-01 | SN quá ngắn | vendor_sn = "AB" (2 ký tự) | Warning: "Serial Number quá ngắn (tối thiểu 3 ký tự)" |
| EC-02 | SN quá dài | vendor_sn = chuỗi 200 ký tự | Error: "Serial Number không được vượt quá 140 ký tự" |
| EC-03 | File upload quá lớn | File 25MB > 20MB limit | Error: "File không được vượt quá 20MB" |
| EC-04 | File upload sai định dạng | Upload .exe thay vì PDF | Error: "Chỉ chấp nhận file PDF, JPG, PNG, TIFF" |
| EC-05 | Checklist 0 items | Submit baseline khi checklist empty | Error: "Checklist chưa có mục kiểm tra nào. Liên hệ CMMS Admin để cấu hình template." |
| EC-06 | NC đóng thiếu evidence | Close NC không nhập root_cause | Error: "VR-NC: Phải điền Nguyên Nhân Gốc Rễ và Hành Động Khắc Phục trước khi đóng NC." |
| EC-07 | Reception date tương lai | reception_date = tomorrow | Error: "Ngày Nhận Hàng không được là ngày trong tương lai" |
| EC-08 | Giá trị đo âm | measured_value = -5 (khi expected_min = 0) | Auto-set result = Fail; highlight ô đỏ |
| EC-09 | Numeric item không nhập measured_value | Submit với measured_value = null khi type = Numeric | Error: "Mục 'Dòng rò vỏ máy' yêu cầu nhập Giá Trị Đo. Không để trống." |
| EC-10 | Cancel Commissioning sau khi Asset tạo | Cố cancel khi status = Clinical_Release | Error: "Không thể hủy Phiếu Nghiệm Thu 'ACC-2026-00001' vì Tài Sản 'ACC-ASS-2026-00001' đã được kích hoạt." |

---

### 2.2 Concurrent Access

| ID | Scenario | Expected Behavior |
|---|---|---|
| CC-01 | 2 Biomed Engineers submit baseline cùng lúc | Frappe optimistic locking: người submit sau nhận error "Record đã được cập nhật bởi người khác. Vui lòng reload." |
| CC-02 | TBYT Officer đang edit, QA Officer upload document cùng lúc | Document upload là partial update → không conflict với form đang mở; refresh thông báo khi có thay đổi từ user khác |
| CC-03 | Board approve trong khi Biomed mở NC modal | Sau board approve: NC modal vẫn mở nhưng "Trả Hàng Vendor" button không hoạt động (status đã = Clinical_Release) |
| CC-04 | 2 TBYT Officers cùng gán SN cho 2 Commissioning khác nhau với SN giống nhau | VR-01: Người save sau bị block — transaction-level unique check |

---

### 2.3 Large Data

| ID | Scenario | Expected Behavior |
|---|---|---|
| LD-01 | Checklist 100+ items | Pagination trong checklist table (50 items/page); scroll virtualization; không block UI |
| LD-02 | 500 Document rows | Lazy load; search/filter trong Documents tab |
| LD-03 | 1000+ Commissioning records trong List view | Phân trang server-side; filter hoạt động nhanh (< 2 giây) với index trên `status`, `reception_date`, `location` |
| LD-04 | File PDF 19.9MB (gần limit) | Upload thành công trong < 30 giây; progress indicator hiển thị |
| LD-05 | Timeline với 100+ lifecycle events | Virtual scroll trong Timeline tab; không load tất cả DOM cùng lúc |

---

### 2.4 Permission Boundary Tests

| ID | Scenario | Expected Behavior |
|---|---|---|
| PB-01 | Vendor Tech cố gán Internal Tag | HTTP 403: "Bạn không có quyền thực hiện thao tác này" |
| PB-02 | TBYT Officer cố approve Clinical Release | HTTP 403 khi gọi `approve_clinical_release` |
| PB-03 | Biomed Engineer mở Commissioning của hospital khác (multi-tenant) | HTTP 404 hoặc chỉ thấy record của hospital mình |
| PB-04 | Anonymous access (không login) gọi API | HTTP 401: "Bạn chưa đăng nhập. Vui lòng đăng nhập để tiếp tục." |

---

## 3. Seed Data — Môi Trường Kiểm Thử

### 3.1 Asset Categories

```python
# Chạy trong Frappe console: bench --site [site] execute assetcore.tests.fixtures.imm04_seed.seed_asset_categories

ASSET_CATEGORIES = [
    {"name": "Medical Imaging", "enable_cwip_accounting": 1},
    {"name": "Life Support", "enable_cwip_accounting": 1},
    {"name": "Diagnostic Equipment", "enable_cwip_accounting": 1},
    {"name": "Radiation Therapy", "enable_cwip_accounting": 1},
]
```

### 3.2 Locations

```python
LOCATIONS = [
    {"name": "Khoa Chẩn Đoán Hình Ảnh", "parent_location": "Tầng 3"},
    {"name": "Khoa Hồi Sức Tích Cực", "parent_location": "Tầng 2"},
    {"name": "Khoa Nhi", "parent_location": "Tầng 4"},
    {"name": "Khoa Ung Bướu", "parent_location": "Tầng 5"},
    {"name": "Phòng Mổ 1", "parent_location": "Tầng 2"},
]
```

### 3.3 Items (Device Models)

```python
ITEMS = [
    {
        "item_code": "ITM-XRAY-PHILIPS-001",
        "item_name": "Philips MobileDiagnost wDR",
        "item_group": "Medical Imaging",
        "asset_category": "Medical Imaging",
        "is_fixed_asset": 1,
        "risk_class": "C",   # Class C — triggers Clinical Hold
        "manufacturer": "Philips",
        "brand": "Philips Healthcare",
        "model_no": "MobileDiagnost wDR",
    },
    {
        "item_code": "ITM-VENT-DRAGER-001",
        "item_name": "Máy Thở Drager Evita V300",
        "item_group": "Life Support",
        "asset_category": "Life Support",
        "is_fixed_asset": 1,
        "risk_class": "D",   # Class D — strict Clinical Hold
        "manufacturer": "Dräger",
        "brand": "Drägerwerk AG",
        "model_no": "Evita V300",
    },
    {
        "item_code": "ITM-PUMP-BRAUN-001",
        "item_name": "Bơm Tiêm BBraun Perfusor Space",
        "item_group": "Diagnostic Equipment",
        "asset_category": "Diagnostic Equipment",
        "is_fixed_asset": 1,
        "risk_class": "B",   # Class B — no Clinical Hold
        "manufacturer": "B.Braun",
        "brand": "B.Braun Medical",
        "model_no": "Perfusor Space",
    },
    {
        "item_code": "ITM-LINAC-VARIAN-001",
        "item_name": "Máy Xạ Trị Varian TrueBeam",
        "item_group": "Radiation Therapy",
        "asset_category": "Radiation Therapy",
        "is_fixed_asset": 1,
        "risk_class": "Radiation",  # Radiation — requires radiation license
        "manufacturer": "Varian Medical Systems",
        "brand": "Varian",
        "model_no": "TrueBeam STx",
    },
]
```

### 3.4 Suppliers

```python
SUPPLIERS = [
    {"supplier_name": "Philips Healthcare VN", "supplier_group": "Medical Equipment", "country": "Vietnam"},
    {"supplier_name": "Dräger Vietnam", "supplier_group": "Medical Equipment", "country": "Vietnam"},
    {"supplier_name": "B.Braun Medical VN", "supplier_group": "Medical Equipment", "country": "Vietnam"},
    {"supplier_name": "Varian Medical VN", "supplier_group": "Medical Equipment", "country": "Vietnam"},
]
```

### 3.5 Purchase Orders

```python
PURCHASE_ORDERS = [
    {
        "name": "PO-2026-00023",
        "supplier": "Philips Healthcare VN",
        "transaction_date": "2026-03-01",
        "status": "To Receive and Bill",
        "items": [{"item_code": "ITM-XRAY-PHILIPS-001", "qty": 1, "rate": 850000000}],
    },
    {
        "name": "PO-2026-00024",
        "supplier": "Dräger Vietnam",
        "transaction_date": "2026-03-05",
        "status": "To Receive and Bill",
        "items": [{"item_code": "ITM-VENT-DRAGER-001", "qty": 2, "rate": 420000000}],
    },
    {
        "name": "PO-2026-00025",
        "supplier": "B.Braun Medical VN",
        "transaction_date": "2026-03-10",
        "status": "To Receive and Bill",
        "items": [{"item_code": "ITM-PUMP-BRAUN-001", "qty": 5, "rate": 45000000}],
    },
]
```

### 3.6 Test Users

```python
TEST_USERS = [
    {
        "email": "tbyt.le@hospital.vn",
        "full_name": "Lê Thị TBYT",
        "roles": ["TBYT Officer"],
        "password": "TestPass2026!",
    },
    {
        "email": "biomed.nguyen@hospital.vn",
        "full_name": "Nguyễn Văn Biomed",
        "roles": ["Biomed Engineer"],
        "password": "TestPass2026!",
    },
    {
        "email": "vendor.tech@philips.com",
        "full_name": "Kỹ Thuật Philips",
        "roles": ["Vendor Tech"],
        "password": "TestPass2026!",
    },
    {
        "email": "dr.tran@hospital.vn",
        "full_name": "BS. Trần Văn Clinical",
        "roles": ["Clinical Head"],
        "password": "TestPass2026!",
    },
    {
        "email": "qa.pham@hospital.vn",
        "full_name": "Phạm Thị QA",
        "roles": ["QA Officer"],
        "password": "TestPass2026!",
    },
    {
        "email": "ceo.nguyen@hospital.vn",
        "full_name": "Nguyễn Giám Đốc",
        "roles": ["Board", "System Manager"],
        "password": "TestPass2026!",
    },
    {
        "email": "workshop.manager@hospital.vn",
        "full_name": "Trưởng Xưởng Bảo Trì",
        "roles": ["Workshop Manager"],
        "password": "TestPass2026!",
    },
]
```

### 3.7 Commissioning Checklist Templates (Seed)

```python
# Template cho Medical Imaging (Class C)
BASELINE_CHECKLIST_TEMPLATE_IMAGING = [
    {
        "item_code": "CHK-ELEC-001",
        "description": "Kiểm tra điện áp đầu vào (220V ±10%)",
        "measurement_type": "Numeric",
        "unit": "V",
        "expected_min": 198.0,
        "expected_max": 242.0,
        "is_critical": True,
        "reference_section": "IEC 60601-1 §4.11",
    },
    {
        "item_code": "CHK-ELEC-002",
        "description": "Dòng rò vỏ máy (Earth Leakage)",
        "measurement_type": "Numeric",
        "unit": "mA",
        "expected_min": 0.0,
        "expected_max": 2.0,
        "is_critical": True,
        "reference_section": "IEC 60601-1 §8.7",
    },
    {
        "item_code": "CHK-ELEC-003",
        "description": "Điện trở dây tiếp đất",
        "measurement_type": "Numeric",
        "unit": "Ω",
        "expected_min": 0.0,
        "expected_max": 0.2,
        "is_critical": True,
        "reference_section": "IEC 60601-1 §8.6",
    },
    {
        "item_code": "CHK-FUNC-001",
        "description": "Kiểm tra khởi động phần mềm — không lỗi",
        "measurement_type": "Pass/Fail",
        "is_critical": True,
        "reference_section": "Service Manual §2.1",
    },
    {
        "item_code": "CHK-FUNC-002",
        "description": "Kiểm tra màn hình hiển thị — không điểm chết",
        "measurement_type": "Pass/Fail",
        "is_critical": False,
        "reference_section": "Service Manual §2.3",
    },
    {
        "item_code": "CHK-MECH-001",
        "description": "Kiểm tra cơ cấu di chuyển / khóa bánh xe",
        "measurement_type": "Pass/Fail",
        "is_critical": False,
        "reference_section": "Service Manual §3.1",
    },
]
```

### 3.8 Pre-built Test Records

```python
# Record đã ở trạng thái Clinical_Hold — dùng cho TC-04-11
SEED_COMMISSIONING_CLINICAL_HOLD = {
    "name": "ACC-TEST-CH-001",
    "purchase_order": "PO-2026-00023",
    "item_ref": "ITM-XRAY-PHILIPS-001",
    "vendor": "Philips Healthcare VN",
    "location": "Khoa Chẩn Đoán Hình Ảnh",
    "status": "Clinical_Hold",
    "risk_class": "C",
    "vendor_sn": "PHI-XRAY-TEST-SN00001",
    "internal_tag": "BVNK-CDHA-TEST-001",
    "reception_date": "2026-04-10",
    "commissioned_by": "biomed.nguyen@hospital.vn",
    "clinical_head": "dr.tran@hospital.vn",
    "qa_officer": "qa.pham@hospital.vn",
    "facility_checklist_pass": 1,
    "overall_inspection_result": "Pass",
}

# Record đã ở trạng thái Non_Conformance — dùng cho TC-04-12
SEED_COMMISSIONING_WITH_OPEN_NC = {
    "name": "ACC-TEST-NC-001",
    "status": "Non_Conformance",
    "risk_class": "B",
    "vendor_sn": "BBR-PUMP-TEST-SN00002",
    "overall_inspection_result": "Pass",
    "non_conformances": [
        {
            "nc_code": "NC-ACC-TEST-NC-001-01",
            "nc_type": "Technical",
            "severity": "Major",
            "status": "Under Review",
            "description": "Màn hình LCD xuất hiện vạch ngang",
        }
    ],
}
```

---

## 4. Checklist UAT Sign-off

| TC-ID | Mô Tả | Người Thực Hiện | Ngày | Kết Quả | Ghi Chú |
|---|---|---|---|---|---|
| TC-04-01 | Tạo Commissioning từ PO | | | ☐ Pass ☐ Fail | |
| TC-04-02 | Block tạo Asset trực tiếp | | | ☐ Pass ☐ Fail | |
| TC-04-03 | VR-01: Duplicate SN bị block | | | ☐ Pass ☐ Fail | |
| TC-04-04 | VR-01: SN unique được chấp nhận | | | ☐ Pass ☐ Fail | |
| TC-04-05 | VR-02: Gate G01 block khi thiếu doc | | | ☐ Pass ☐ Fail | |
| TC-04-06 | G01 Pass — chuyển To_Be_Installed | | | ☐ Pass ☐ Fail | |
| TC-04-07 | Block upload document hết hạn | | | ☐ Pass ☐ Fail | |
| TC-04-08 | VR-03: Baseline fail → Re_Inspection | | | ☐ Pass ☐ Fail | |
| TC-04-09 | Baseline Pass Class B → Clinical Release | | | ☐ Pass ☐ Fail | |
| TC-04-10 | VR-07: Auto-hold Class C | | | ☐ Pass ☐ Fail | |
| TC-04-11 | G04: Gỡ Clinical Hold | | | ☐ Pass ☐ Fail | |
| TC-04-12 | VR-04: Block Release khi có NC Open | | | ☐ Pass ☐ Fail | |
| TC-04-13 | DOA → Return_To_Vendor | | | ☐ Pass ☐ Fail | |
| TC-04-14 | Checklist lock sau submit | | | ☐ Pass ☐ Fail | |
| TC-04-15 | VR-06: Lifecycle Event immutable | | | ☐ Pass ☐ Fail | |
| TC-04-16 | Clinical Release thành công | | | ☐ Pass ☐ Fail | |
| TC-04-17 | G06: Block khi không có Board Approver | | | ☐ Pass ☐ Fail | |
| TC-04-18 | Barcode Scanner integration | | | ☐ Pass ☐ Fail | |

---

**Phê Duyệt UAT:**

| Vai Trò | Họ Tên | Chữ Ký | Ngày |
|---|---|---|---|
| TBYT Officer | | | |
| Biomed Engineer | | | |
| QA Officer | | | |
| Workshop Manager | | | |
| Clinical Head | | | |
| Board/CEO | | | |
