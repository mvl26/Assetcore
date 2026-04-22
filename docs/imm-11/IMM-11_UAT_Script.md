# IMM-11 — UAT Script
## User Acceptance Testing — Calibration Module

**Module:** IMM-11
**Version:** 1.0
**Ngày:** 2026-04-17
**Môi trường:** UAT (staging.assetcore.vn)
**Tester:** QA Officer / Workshop Manager
**Trạng thái:** Chờ thực hiện

---

## Seed Data

### SD-01: Thiết bị thử nghiệm

| Asset ID | Tên thiết bị | Model | Khoa | Status | next_cal_date | interval |
|---|---|---|---|---|---|---|
| `ACC-ASS-UAT-001` | Máy phân tích huyết học Sysmex XN-1000 | Sysmex XN-1000 | XN Máu | Active | 2026-05-01 | 365 |
| `ACC-ASS-UAT-002` | Monitor BP Mindray MEC-1200 | Mindray MEC-1200 | Nội tim mạch | Active | 2026-04-10 (OVERDUE) | 365 |
| `ACC-ASS-UAT-003` | Máy thở Drager V500 | Drager V500 | ICU | Active | 2026-06-01 | 180 |
| `ACC-ASS-UAT-004` | Đồng hồ đo áp lực Breas | Breas VIVO 45 | Hô hấp | Active | 2026-05-15 | 365 |
| `ACC-ASS-UAT-005` | Sysmex XN-1000 (cùng model với UAT-001) | Sysmex XN-1000 | Cấp cứu | Active | 2026-07-01 | 365 |
| `ACC-ASS-UAT-006` | Sysmex XN-1000 (cùng model với UAT-001) | Sysmex XN-1000 | ICU | Active | 2026-08-01 | 365 |
| `ACC-ASS-UAT-007` | Máy calibration thủ công (In-House) | Fluke ESA620 | Workshop | Active | 2026-05-20 | 365 |

### SD-02: Users thử nghiệm

| User | Role | Email |
|---|---|---|
| KTV HTM | KTV HTM | ktv.uat@hospital.vn |
| Workshop Manager | Workshop Manager | manager.uat@hospital.vn |
| QA Officer | QA Officer | qa.uat@hospital.vn |
| PTP Khối 2 | PTP Khối 2 | ptp.uat@hospital.vn |

### SD-03: Device Models

| Model | calibration_interval_days | calibration_type_default |
|---|---|---|
| Sysmex XN-1000 | 365 | External |
| Mindray MEC-1200 | 365 | External |
| Drager V500 | 180 | External |
| Fluke ESA620 | 365 | In-House |

### SD-04: Lab thử nghiệm

| Lab Name | Accreditation No | Valid Until |
|---|---|---|
| Trung tâm Đo lường Chất lượng 3 | VLAS-T-028 | 2027-12-31 |
| Viện Đo lường Việt Nam | VLAS-T-001 | 2027-06-30 |

### SD-05: Sample Calibration Certificate

- File: `UAT_CAL_Certificate_Sysmex_XN_2026.pdf` (chuẩn bị trước, PDF giả lập)
- Ngày cấp: 2026-04-24
- Lab: Trung tâm Đo lường Chất lượng 3

---

## Test Cases

### TC-11-01: Dashboard Hiển thị Thiết bị Đến hạn

**Priority:** P0 (Critical)
**Actor:** Workshop Manager
**Precondition:** SD-01 đã được tạo, `ACC-ASS-UAT-002` overdue 7 ngày, `ACC-ASS-UAT-001` còn 14 ngày

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Đăng nhập với `manager.uat@hospital.vn` | Email + mật khẩu | Đăng nhập thành công | | |
| 2 | Vào `/imm-11/` (Dashboard) | — | Dashboard hiển thị đầy đủ 4 KPI card | | |
| 3 | Kiểm tra KPI "Compliance Rate" | — | Hiển thị con số % | | |
| 4 | Kiểm tra widget "Overdue" | — | `ACC-ASS-UAT-002` xuất hiện trong danh sách Overdue với badge đỏ | | |
| 5 | Kiểm tra widget "Due Soon" | — | `ACC-ASS-UAT-001` xuất hiện trong danh sách Due Soon | | |
| 6 | Click [Tạo CAL] cạnh `ACC-ASS-UAT-002` | — | Redirect đến `/imm-11/create` với `asset_ref` đã pre-fill | | |

---

### TC-11-02: Tạo Calibration Record — External Track

**Priority:** P0 (Critical)
**Actor:** KTV HTM
**Precondition:** `ACC-ASS-UAT-001` ở trạng thái Active, không có CAL record đang mở

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Đăng nhập với `ktv.uat@hospital.vn` | — | Đăng nhập OK | | |
| 2 | Vào `/imm-11/create` | — | Form tạo CAL hiển thị | | |
| 3 | Chọn Thiết bị = `ACC-ASS-UAT-001` | — | Auto-populate: device_model = "Sysmex XN-1000", calibration_interval_days = 365, due_date = 2026-05-01 | | |
| 4 | Chọn Loại hiệu chuẩn = "External" | — | Phần Lab Info hiển thị (fields: lab_name, accreditation_number, v.v.) | | |
| 5 | Điền Tên lab = "Trung tâm Đo lường Chất lượng 3" | — | Field accepted | | |
| 6 | Điền Số công nhận = "VLAS-T-028" | — | Field accepted | | |
| 7 | Điền Số hợp đồng = "HĐ-2026-KĐ-015" | — | Field accepted | | |
| 8 | Click [Lưu] | — | Record lưu thành công, status = "Scheduled", name = "CAL-2026-xxxxx" | | |
| 9 | Kiểm tra Asset Calibration list | — | Record mới xuất hiện với status "Scheduled" | | |

---

### TC-11-03: Gửi Thiết bị Đến Lab

**Priority:** P1
**Actor:** KTV HTM
**Precondition:** CAL-2026-xxxxx đang ở trạng thái "Scheduled" (kết quả TC-11-02)

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Mở CAL record từ TC-11-02 | — | Record chi tiết hiển thị | | |
| 2 | Click action "Gửi đến Lab" | — | Modal/section nhập sent_date, sent_by hiển thị | | |
| 3 | Điền Ngày gửi = 2026-04-20, Người bàn giao = KTV UAT | — | Fields accepted | | |
| 4 | Click [Xác nhận Gửi] | — | Status chuyển → "Sent to Lab", sent_date được ghi, Asset Lifecycle Event tạo | | |
| 5 | Kiểm tra Asset Lifecycle Events | — | Event type = "calibration_sent_to_lab" xuất hiện với timestamp | | |

---

### TC-11-04: Submit Kết quả — Pass Case (External)

**Priority:** P0 (Critical)
**Actor:** KTV HTM
**Precondition:** CAL record ở "Sent to Lab", file PDF chứng chỉ UAT đã chuẩn bị

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Mở CAL record | — | Hiển thị status "Sent to Lab" | | |
| 2 | Click "Nhận Chứng chỉ" → status = "Certificate Received" | Ngày nhận: 2026-04-25 | Status cập nhật OK | | |
| 3 | Upload Certificate PDF | `UAT_CAL_Certificate_Sysmex_XN_2026.pdf` | Upload thành công, PDF preview hiển thị | | |
| 4 | Điền Ngày cấp chứng chỉ = 2026-04-24 | — | Field accepted | | |
| 5 | Điền Số chứng chỉ = "2026-KĐ-01234" | — | Field accepted | | |
| 6 | Thêm tham số WBC: nominal=7.5, tol±3%, measured=7.6 | — | Row thêm OK, hệ thống tính: deviation=0.1, tol=0.225 → Pass (xanh) | | |
| 7 | Thêm tham số PLT: nominal=250, tol±5%, measured=245 | — | Pass (xanh) | | |
| 8 | Thêm tham số HGB: nominal=14.0, tol±3%, measured=14.2 | — | Pass (xanh) — kết quả tổng: ✅ PASSED | | |
| 9 | Tích "Đã gắn sticker", upload ảnh sticker | — | Upload OK | | |
| 10 | Click [Submit] | — | Submit thành công không có dialog cảnh báo | | |
| 11 | Kiểm tra record sau submit | — | Status = "Passed", next_calibration_date = 2027-04-24 (2026-04-24 + 365) | | |
| 12 | Kiểm tra Asset `ACC-ASS-UAT-001` | — | custom_last_calibration_date = 2026-04-24, custom_next_calibration_date = 2027-04-24, custom_calibration_status = "On Schedule" | | |
| 13 | Kiểm tra Asset Lifecycle Events | — | Event "calibration_completed" tạo với timestamp, actor | | |
| 14 | Thử xóa record | — | Nút Delete không có / bị block (BR-11-05) | | |

---

### TC-11-05: Submit Kết quả — Fail Case + Auto CAPA

**Priority:** P0 (Critical — đây là business rule quan trọng nhất)
**Actor:** KTV HTM
**Precondition:** `ACC-ASS-UAT-001` Active, tạo CAL record mới (CAL-2026-xxxxx+1)

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Tạo CAL record mới cho `ACC-ASS-UAT-001` | External, lab UAT | Record tạo OK | | |
| 2 | Hoàn thành các bước Sent to Lab → Certificate Received | — | Status đúng | | |
| 3 | Upload certificate PDF | — | OK | | |
| 4 | Thêm tham số WBC: nominal=7.5, tol±3%, measured=7.6 | — | ✅ Pass (xanh) | | |
| 5 | Thêm tham số HGB: nominal=14.0, tol±3%, measured=**15.0** | — | ❌ Fail (đỏ) — deviation=1.0, tol=0.42 → out_of_tolerance | | |
| 6 | Kiểm tra kết quả tổng | — | Badge "❌ FAILED" hiển thị trên form | | |
| 7 | Click [Submit] | — | Dialog cảnh báo xuất hiện với thông tin: 1 tham số Fail, danh sách tác động (OOS, CAPA, Lookback) | | |
| 8 | Click [Xác nhận Submit] | — | Submit thành công | | |
| 9 | Kiểm tra CAL record | — | Status = "Failed", overall_result = "Failed" | | |
| 10 | Kiểm tra Asset `ACC-ASS-UAT-001` | — | status = "Out of Service" (BR-11-02) | | |
| 11 | Kiểm tra CAPA Records | — | CAPA-2026-xxxxx được tạo tự động với: asset_ref=ACC-ASS-UAT-001, calibration_ref=CAL-..., status="Open", lookback_required=True, lookback_status="Pending" | | |
| 12 | Kiểm tra lookback_assets trong CAPA | — | Chứa ["ACC-ASS-UAT-005", "ACC-ASS-UAT-006"] (cùng model Sysmex XN-1000) | | |
| 13 | Kiểm tra notifications | — | Email gửi đến `qa.uat@hospital.vn` và `ptp.uat@hospital.vn` | | |
| 14 | Kiểm tra Asset Lifecycle Events | — | Event "calibration_failed" + event "asset_out_of_service" | | |
| 15 | Thử set lại asset về Active thủ công | — | Bị block hoặc cảnh báo: "CAPA chưa đóng" | | |

---

### TC-11-06: Lookback Assessment

**Priority:** P0 (Critical — BR-11-03)
**Actor:** QA Officer
**Precondition:** TC-11-05 đã hoàn thành, CAPA-2026-xxxxx đang Open với lookback_status=Pending

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Đăng nhập với `qa.uat@hospital.vn` | — | OK | | |
| 2 | Vào `/imm-11/capa` | — | Danh sách CAPA hiển thị, CAPA-2026-xxxxx ở đầu với badge "Lookback Pending" | | |
| 3 | Mở CAPA Detail | — | Panel Lookback hiển thị danh sách 2 thiết bị: ACC-ASS-UAT-005, ACC-ASS-UAT-006 | | |
| 4 | Review thiết bị UAT-005 (click [Review]) | — | Chuyển đến trang calibration history của UAT-005 | | |
| 5 | Review thiết bị UAT-006 (click [Review]) | — | Tương tự | | |
| 6 | Chọn Kết luận Lookback = "Cleared" | — | Radio button selected | | |
| 7 | Điền Ghi chú = "Đã kiểm tra 2 thiết bị Sysmex XN-1000. Không phát hiện drift. Lỗi riêng biệt tại ACC-UAT-001." | — | Textarea accepted | | |
| 8 | Click [Lưu Lookback Findings] | — | lookback_status = "Cleared", CAPA.status = "In Review" | | |
| 9 | Thử đóng CAPA ngay khi lookback = Cleared nhưng chưa điền RCA | — | Block: "Phân tích nguyên nhân gốc rễ (RCA) là bắt buộc" | | |

---

### TC-11-07: Đóng CAPA Record

**Priority:** P1
**Actor:** QA Officer
**Precondition:** TC-11-06 hoàn thành, lookback_status = "Cleared"

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Mở CAPA record | — | Status = "In Review", lookback = Cleared | | |
| 2 | Điền Root Cause Analysis | "Detector drift do nhiệt độ bảo quản mẫu. Phát hiện cảm biến nhiệt độ tủ lưu mẫu hỏng." | Accepted | | |
| 3 | Điền Corrective Action | "Sửa cảm biến nhiệt độ. Tái hiệu chuẩn thiết bị." | Accepted | | |
| 4 | Điền Preventive Action | "Lịch kiểm tra cảm biến nhiệt độ định kỳ hàng tháng." | Accepted | | |
| 5 | Click [Đóng CAPA] | — | CAPA status = "Closed", actual_close_date = hôm nay | | |
| 6 | Ghi chú: thiết bị vẫn OOS cho đến khi có CAL mới pass | — | Asset vẫn "Out of Service" | | |
| 7 | Tạo CAL record mới (recalibration) → Submit với tất cả Pass | — | Sau khi CAL mới Pass → Asset tự động về "Active" | | |
| 8 | Kiểm tra Asset Lifecycle Events | — | Event "calibration_conditionally_passed" xuất hiện | | |

---

### TC-11-08: Block Submit khi không có Certificate (External)

**Priority:** P0 (BR-11-01 validation)
**Actor:** KTV HTM

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Tạo CAL record, type=External | — | Record tạo OK | | |
| 2 | Nhập tất cả measurements (tất cả Pass) | — | OK | | |
| 3 | KHÔNG upload certificate file | — | — | | |
| 4 | Click [Submit] | — | Error: "Vui lòng upload Calibration Certificate trước khi Submit (BR-11-01)" | | |
| 5 | Upload certificate, click Submit | — | Submit thành công | | |

---

### TC-11-09: Block Submit khi không có Lab Accreditation Number (External)

**Priority:** P0 (BR-11-01 validation)
**Actor:** KTV HTM

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Tạo CAL record, type=External | — | OK | | |
| 2 | Điền lab_name nhưng BỎ TRỐNG accreditation_number | — | — | | |
| 3 | Upload certificate, nhập measurements | — | — | | |
| 4 | Click [Submit] | — | Error: "Vui lòng nhập Số công nhận ISO/IEC 17025 của tổ chức kiểm định (BR-11-01)" | | |

---

### TC-11-10: In-House Calibration Track

**Priority:** P1
**Actor:** KTV HTM
**Precondition:** `ACC-ASS-UAT-007` Active (model Fluke ESA620, in-house default)

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Tạo CAL record, type=In-House | — | Lab fields ẩn, In-House fields hiện | | |
| 2 | Điền reference_standard_serial = "FLUKE-REF-001" | — | Accepted | | |
| 3 | Điền traceability_reference = "VLAS-T-099-REF" | — | Accepted | | |
| 4 | Thêm measurements (tất cả Pass) | — | Pass indicators xanh | | |
| 5 | Click Submit (không cần certificate file) | — | Submit thành công — không có lỗi BR-11-01 | | |
| 6 | Kiểm tra next_calibration_date | — | completion_date + 365 (vì không có certificate_date) | | |

---

### TC-11-11: Amend (Sửa đổi) Record sau Submit

**Priority:** P1 (BR-11-05)
**Actor:** KTV HTM / Workshop Manager

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Mở CAL record đã Submit (Passed) | — | Record ở chế độ read-only | | |
| 2 | Thử xóa record | — | Nút Delete không xuất hiện hoặc bị block (BR-11-05) | | |
| 3 | Thử Cancel | — | Error: "Không thể hủy Phiếu Hiệu chuẩn đã Submit. Vui lòng dùng Amend (BR-11-05)" | | |
| 4 | Click [Amend] | — | Form Amend mở, field `amendment_reason` bắt buộc | | |
| 5 | Thử Submit Amend mà không điền amendment_reason | — | Error: "Lý do sửa đổi là bắt buộc khi Amend" | | |
| 6 | Điền amendment_reason = "Sửa số chứng chỉ bị nhập sai" | — | Accepted | | |
| 7 | Sửa certificate_number, Submit | — | Record mới tạo với `amended_from` link về record cũ | | |
| 8 | Kiểm tra record cũ | — | Record cũ vẫn tồn tại (immutable audit trail) | | |

---

### TC-11-12: Tính next_calibration_date từ certificate_date (BR-11-04)

**Priority:** P0 (BR-11-04 — business rule về cách tính ngày)
**Actor:** KTV HTM

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Thiết bị có next_calibration_date = 2026-05-01 | — | — | | |
| 2 | Tạo CAL, gửi lab, nhận về | — | — | | |
| 3 | Nhập certificate_date = 2026-04-24 (trước due_date 7 ngày) | — | — | | |
| 4 | Submit (Pass) | — | next_calibration_date = 2027-04-24 (KHÔNG phải 2027-05-01) | | |
| 5 | Kiểm tra Asset | — | custom_next_calibration_date = 2027-04-24 xác nhận BR-11-04 | | |

---

### TC-11-13: Calibration KPI Compliance Report

**Priority:** P1
**Actor:** PTP Khối 2

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Đăng nhập với `ptp.uat@hospital.vn` | — | OK | | |
| 2 | Vào `/imm-11/report/compliance` | — | Trang báo cáo hiển thị | | |
| 3 | Chọn Period = Tháng 4/2026 | — | Filters applied | | |
| 4 | Kiểm tra Compliance Rate | — | % tính đúng = (on_time / total_scheduled) × 100 | | |
| 5 | Kiểm tra OOT Rate | — | % = (failed_measurements / total_measurements) × 100 | | |
| 6 | Kiểm tra CAPA Closure Rate | — | % = closed_within_30d / total_opened × 100 | | |
| 7 | Kiểm tra danh sách overdue | — | `ACC-ASS-UAT-002` xuất hiện với số ngày overdue | | |
| 8 | Kiểm tra trend chart 6 tháng | — | Line chart hiển thị với data points đúng | | |

---

### TC-11-14: Lịch sử Calibration của 1 Thiết bị

**Priority:** P1
**Actor:** KTV HTM

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Vào `/imm-11/asset/ACC-ASS-UAT-001/history` | — | Trang lịch sử hiển thị | | |
| 2 | Kiểm tra timeline | — | Hiển thị tất cả CAL records của UAT-001 theo thứ tự thời gian | | |
| 3 | Kiểm tra record Pass từ TC-11-04 | — | Hiển thị với badge ✅, certificate_date, lab name | | |
| 4 | Kiểm tra record Fail từ TC-11-05 | — | Hiển thị với badge ❌, CAPA reference | | |
| 5 | Click vào record để xem chi tiết | — | Redirect đến CalibrationDetail | | |

---

### TC-11-15: Calibration Record liên kết PM Work Order (IMM-08)

**Priority:** P2
**Actor:** KTV HTM / Workshop Manager

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Đảm bảo có PM Work Order `PM-WO-2026-00001` cho `ACC-ASS-UAT-003` | — | PM WO tồn tại | | |
| 2 | Tạo CAL record cho `ACC-ASS-UAT-003` | — | Form hiển thị | | |
| 3 | Điền PM Work Order = `PM-WO-2026-00001` | — | Link field accepted | | |
| 4 | Hoàn thành và Submit CAL (Pass) | — | Submit OK | | |
| 5 | Kiểm tra PM Work Order | — | PM WO hiển thị reference đến CAL record | | |
| 6 | Kiểm tra KPI PM và KPI CAL | — | Được tính riêng biệt (compliance PM không gộp vào CAL) | | |

---

### TC-11-16: CAPA Overdue Alert (> 30 ngày)

**Priority:** P1
**Actor:** System Scheduler / QA Officer

| # | Bước | Dữ liệu đầu vào | Kết quả mong đợi | Pass/Fail | Ghi chú |
|---|---|---|---|---|---|
| 1 | Tạo CAPA record với opened_date = hôm nay - 31 ngày (chỉnh DB) | — | CAPA quá hạn | | |
| 2 | Chạy scheduler job `check_capa_overdue` | — | — | | |
| 3 | Kiểm tra notifications | — | Email gửi QA Officer và PTP Khối 2: "CAPA {name} quá hạn 31 ngày" | | |
| 4 | Kiểm tra Dashboard | — | CAPA hiển thị badge "Overdue" màu đỏ | | |

---

## Edge Cases

### EC-11-01: Tạo CAL khi thiết bị đang "Out of Service"

| Tình huống | Kết quả mong đợi |
|---|---|
| `ACC-ASS-UAT-001` đang "Out of Service" (do fail cal), Workshop Manager cố tạo CAL mới | Hệ thống **cho phép** tạo CAL mới (để gửi tái hiệu chuẩn) nhưng hiển thị cảnh báo: "Thiết bị đang Out of Service — đây là recalibration sau CAPA" |

### EC-11-02: Duplicate CAL record

| Tình huống | Kết quả mong đợi |
|---|---|
| `ACC-ASS-UAT-001` đã có CAL-2026-00001 ở "Sent to Lab", Manager tạo thêm CAL mới | Error ERR-11-012: "Thiết bị đã có Phiếu Hiệu chuẩn đang xử lý: CAL-2026-00001" |

### EC-11-03: Measurement Table trống khi Submit

| Tình huống | Kết quả mong đợi |
|---|---|
| KTV không thêm bất kỳ tham số nào vào Measurement table rồi Submit | Error ERR-11-003: "Vui lòng nhập giá trị đo cho tất cả tham số trước khi Submit" |

### EC-11-04: Đóng CAPA khi Lookback chưa hoàn thành

| Tình huống | Kết quả mong đợi |
|---|---|
| QA Officer cố đóng CAPA khi lookback_status = "Pending" | Error ERR-11-008: "CAPA Record chưa hoàn thành Lookback" |

### EC-11-05: Device Model không có calibration_interval_days

| Tình huống | Kết quả mong đợi |
|---|---|
| KTV tạo CAL cho thiết bị có Device Model chưa điền calibration_interval_days | Cảnh báo: "Device Model chưa có chu kỳ hiệu chuẩn" — cho phép tạo nhưng nhắc CMMS Admin cập nhật |

### EC-11-06: Tolerance = 0 (tham số không có tolerance)

| Tình huống | Kết quả mong đợi |
|---|---|
| KTV nhập tolerance_plus = 0 và tolerance_minus = 0 cho một tham số | Hệ thống xử lý đặc biệt: chỉ Pass nếu measured_value == nominal_value (exact match), ngược lại Fail |

### EC-11-07: KTV không có quyền Submit

| Tình huống | Kết quả mong đợi |
|---|---|
| User có role "KTV HTM" cố Submit CAL record của KTV khác (không phải owner) | Error 403: "Bạn không có quyền thực hiện thao tác này" |

### EC-11-08: Certificate Date sau ngày hôm nay

| Tình huống | Kết quả mong đợi |
|---|---|
| KTV nhập certificate_date = ngày trong tương lai | Cảnh báo: "Ngày cấp chứng chỉ không thể là ngày trong tương lai" |

### EC-11-09: Lookback khi không có thiết bị cùng model

| Tình huống | Kết quả mong đợi |
|---|---|
| Calibration fail cho thiết bị duy nhất của model đó (không có asset khác cùng model) | CAPA vẫn tạo với lookback_required = True nhưng lookback_assets = [], lookback_findings = "Không có thiết bị cùng model khác đang Active" |

### EC-11-10: Submit Fail khi PDF không parse được

| Tình huống | Kết quả mong đợi |
|---|---|
| KTV upload file không phải PDF (ví dụ: .docx) | Validation ngay tại client: "Chỉ chấp nhận file PDF cho Calibration Certificate" |

---

## Checklist Cuối UAT

| # | Hạng mục | Đạt | Không đạt | Ghi chú |
|---|---|---|---|---|
| 1 | BR-11-01: External cal bắt buộc certificate + accreditation number | | | |
| 2 | BR-11-02: Fail → OOS tự động + CAPA tự động tạo | | | |
| 3 | BR-11-03: Lookback assets cùng model populated tự động | | | |
| 4 | BR-11-04: next_cal = certificate_date + interval (không phải due_date) | | | |
| 5 | BR-11-05: Không thể Delete/Cancel sau Submit — chỉ Amend với lý do | | | |
| 6 | Dashboard hiển thị overdue và due soon chính xác | | | |
| 7 | KPI Compliance Report tính đúng | | | |
| 8 | In-House track không yêu cầu certificate upload | | | |
| 9 | Measurement table tự động tính Pass/Fail với màu indicator | | | |
| 10 | Asset Lifecycle Event tạo cho mọi hành động chính | | | |
| 11 | Notification gửi đến QA Officer + PTP khi fail | | | |
| 12 | CAPA không thể đóng khi lookback chưa hoàn thành | | | |
| 13 | Amend bắt buộc amendment_reason | | | |
| 14 | Asset restore về Active sau CAPA closed + recalibration pass | | | |
| 15 | PM Work Order link hoạt động, KPI tính riêng biệt | | | |

---

## Sign-off

| Người kiểm tra | Vai trò | Ngày | Chữ ký |
|---|---|---|---|
| | Workshop Manager | | |
| | QA Officer | | |
| | KTV HTM | | |
| | PTP Khối 2 | | |
| | Dev Lead | | |
