# IMM-12 — UAT Script
## User Acceptance Testing — Corrective Maintenance & SLA Management

**Module:** IMM-12
**Version:** 1.0
**Ngày:** 2026-04-17
**Trạng thái:** Draft — Chờ thực thi UAT
**Tác giả:** AssetCore QA Team

---

## Hướng dẫn sử dụng

- **Môi trường:** UAT / Staging server — KHÔNG chạy trên Production
- **Dữ liệu:** Sử dụng Seed Data ở Section 3 trước khi bắt đầu
- **Kết quả:** Ghi PASS / FAIL / BLOCKED cho từng test step
- **Log lỗi:** Chụp màn hình hoặc ghi log lỗi vào cột "Ghi chú"
- **Reset:** Chạy `bench --site uat.assetcore reset-imm12-test-data` sau mỗi test run

---

## Section 1: Test Cases

---

### TC-12-01: Tạo Incident Report — Luồng cơ bản

**Mục tiêu:** Nhân viên khoa phòng có thể tạo IR thành công
**Actor:** Reporting User
**Priority Coverage:** Tất cả (luồng tạo không phụ thuộc priority)
**Điều kiện tiên quyết:** Đã login với role `Reporting User`, asset `ACC-ASS-UAT-001` tồn tại

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Vào `/imm-12/incidents/new` | Form tạo IR hiển thị rõ ràng | | |
| 2 | Nhập asset: `ACC-ASS-UAT-001` (Máy thở Drager Evita 800) | Auto-fill: department = ICU, location = Phòng 302 | | |
| 3 | Chọn fault_code: `VENT_ALARM_HIGH` | Dropdown hiển thị đầy đủ fault codes | | |
| 4 | Nhập fault_description: "Máy báo alarm P_HIGH liên tục" | Text area nhận input | | |
| 5 | Chọn "Hoàn toàn không hoạt động" | Radio button chọn được | | |
| 6 | Tích workaround_applied = True | Checkbox tích được | | |
| 7 | Click "Gửi báo cáo" | IR được tạo với naming IR-YYYY-##### | | |
| 8 | Kiểm tra IR status = "New" | Status = New hiển thị đúng | | |
| 9 | Kiểm tra created_at được set = now() | Thời gian tạo chính xác (±1 phút) | | |
| 10 | Kiểm tra priority = null (chưa classify) | Priority trống — chờ Workshop classify | | |
| 11 | Kiểm tra SLA timer CHƯA hiển thị (priority null) | Timer chỉ hiển thị sau Acknowledge | | |

---

### TC-12-02: Tạo IR P1 — Validate clinical_impact bắt buộc (BR-12-01 prerequisite)

**Mục tiêu:** P1 incident bắt buộc có clinical_impact
**Actor:** Reporting User
**Điều kiện tiên quyết:** Asset `ACC-ASS-UAT-001` có flag `is_life_support = True`

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Tạo IR với asset `ACC-ASS-UAT-001` | Form hiển thị section "Tác động lâm sàng" | | |
| 2 | Để trống `clinical_impact` | | | |
| 3 | Điền các field còn lại | | | |
| 4 | Click "Gửi báo cáo" | Error: "Sự cố P1 bắt buộc phải mô tả tác động lâm sàng" | | |
| 5 | Điền `clinical_impact`: "Bệnh nhân phụ thuộc, đã chuẩn bị bóng ambu" | | | |
| 6 | Click "Gửi báo cáo" lại | IR tạo thành công | | |

---

### TC-12-03: Acknowledge IR — SLA Response cho P1 (30 phút)

**Mục tiêu:** Workshop Manager Acknowledge trong SLA, SLA timer bắt đầu đúng
**Actor:** Workshop Manager
**Điều kiện tiên quyết:** IR-UAT-001 (status = New, chưa classify)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Login với Workshop Manager | | | |
| 2 | Vào `/imm-12/incidents/IR-UAT-001` | IR form hiển thị | | |
| 3 | Click "Tiếp nhận" (Acknowledge button) | Dialog mở: chọn Priority + Assign KTV | | |
| 4 | Chọn Priority = P1 Critical | | | |
| 5 | Assign KTV: `ktv.nguyen.uat@hospital.vn` | | | |
| 6 | Confirm Acknowledge | IR status → Acknowledged | | |
| 7 | Kiểm tra `response_at` được set = now() | Timestamp chính xác | | |
| 8 | Kiểm tra `sla_response_hours` = 0.5 (30 phút) | SLA limit đúng với P1 | | |
| 9 | Kiểm tra SLA timer hiển thị màu ĐỎ (P1) | Timer màu đỏ với countdown | | |
| 10 | Kiểm tra `sla_resolution_deadline` = created_at + 4h | Deadline đúng với P1 | | |
| 11 | Kiểm tra `sla_response_breached = False` | Chưa breach (response trong 30 phút) | | |
| 12 | Kiểm tra Asset Lifecycle Event tạo: event_type = "incident_acknowledged" | Audit trail đầy đủ | | |

---

### TC-12-04: SLA Response Breach P1 — Auto-escalate BGĐ (BR-12-01)

**Mục tiêu:** Khi P1 không Acknowledge trong 30 phút → hệ thống auto-escalate
**Actor:** CMMS Scheduler (simulate bằng manual trigger)
**Điều kiện tiên quyết:** IR-UAT-002 (P1, status = New, created_at = 35 phút trước)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Tạo IR-UAT-002 với timestamp backdated 35 phút | IR tạo thành công | | |
| 2 | Chạy: `bench execute assetcore.services.imm12.check_sla_timers` | Scheduler function chạy không lỗi | | |
| 3 | Kiểm tra `IR-UAT-002.sla_response_breached = True` | Breach flag set đúng | | |
| 4 | Kiểm tra `IR-UAT-002.sla_status = "Breached"` | SLA status cập nhật | | |
| 5 | Kiểm tra SLA Compliance Log entry tạo với breach_type = "Response" | Log được tạo | | |
| 6 | Kiểm tra email gửi đến `giam_doc@hospital.vn` | Email có đầy đủ thông tin IR | | |
| 7 | Kiểm tra email gửi đến `ptp_khoi2@hospital.vn` | Email có đầy đủ thông tin IR | | |
| 8 | Thử DELETE SLA Compliance Log entry | Error 403: "Nhật ký SLA là bất biến" (BR-12-05) | | |
| 9 | Thử EDIT SLA Compliance Log entry | Error 403: không thể sửa | | |
| 10 | Chạy scheduler lần 2 | KHÔNG tạo thêm SLA Compliance Log duplicate (idempotent) | | |

---

### TC-12-05: SLA Resolution Breach P2 — Escalate PTP Khối 2

**Mục tiêu:** P2 breach resolution SLA → escalate đúng PTP Khối 2
**Actor:** CMMS Scheduler (simulate)
**Điều kiện tiên quyết:** IR-UAT-003 (P2, Acknowledged, created_at = 9 giờ trước)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Chuẩn bị IR-UAT-003: priority P2, acknowledged, created 9h trước | IR in Acknowledged status | | |
| 2 | Chạy `check_sla_timers()` | | | |
| 3 | Kiểm tra `sla_resolution_breached = True` (P2 resolution = 8h) | Breach đúng sau 9h | | |
| 4 | Kiểm tra SLA Compliance Log: breach_type = "Resolution", overage_hours ≈ 1.0 | Overage được tính đúng | | |
| 5 | Kiểm tra email gửi đến `ptp_khoi2@hospital.vn` ONLY (không gửi BGĐ) | Escalation đúng cấp | | |
| 6 | Kiểm tra KHÔNG gửi email đến `giam_doc@hospital.vn` | BGĐ chỉ nhận P1 | | |

---

### TC-12-06: SLA At Risk Warning (80% threshold)

**Mục tiêu:** Khi đạt 80% SLA time → status "At Risk", gửi cảnh báo nội bộ
**Actor:** CMMS Scheduler (simulate)
**Điều kiện tiên quyết:** IR-UAT-004 (P3, Acknowledged, created_at = 3.5 giờ trước)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Chuẩn bị IR-UAT-004: P3, Acknowledged, created 3.5h trước (80% of 4h response) | IR in Acknowledged | | |
| 2 | Chạy `check_sla_timers()` | | | |
| 3 | Kiểm tra `sla_status = "At Risk"` | At Risk được set | | |
| 4 | Kiểm tra KHÔNG có SLA Compliance Log tạo (chưa breach) | Không có breach log | | |
| 5 | Kiểm tra alert gửi đến Workshop Manager | Alert nội bộ gửi đúng | | |
| 6 | Kiểm tra màu SLA timer trên UI = vàng/cam | Color coding đúng cho At Risk | | |

---

### TC-12-07: Link Repair Work Order (IMM-09) vào IR

**Mục tiêu:** Workshop Manager link Asset Repair WO vào IR thành công
**Actor:** Workshop Manager
**Điều kiện tiên quyết:** IR-UAT-005 (Acknowledged), AR-UAT-001 (Asset Repair WO Open)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Mở IR-UAT-005 | IR form hiển thị | | |
| 2 | Click "Link Work Order" | Dialog tìm kiếm WO | | |
| 3 | Chọn AR-UAT-001 | | | |
| 4 | Confirm | IR.status = "In Progress" | | |
| 5 | Kiểm tra `repair_wo = AR-UAT-001` | Link đúng | | |
| 6 | Kiểm tra Asset Lifecycle Event: "incident_wo_linked" | Audit trail | | |
| 7 | Thử link một WO đã Completed | Error: "Work Order đã hoàn thành — không thể link vào sự cố đang mở" | | |

---

### TC-12-08: Resolve Incident — P3 không cần RCA

**Mục tiêu:** P3 IR resolved thành công, KHÔNG trigger RCA, có thể Close trực tiếp
**Actor:** KTV HTM
**Điều kiện tiên quyết:** IR-UAT-006 (P3, In Progress, repair_wo Completed)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | KTV login, mở IR-UAT-006 | | | |
| 2 | Click "Đánh dấu Resolved" | Dialog nhập resolution_notes | | |
| 3 | Nhập resolution_notes: "Đã thay thế module display, kiểm tra OK" | | | |
| 4 | Confirm Resolved | IR.status = "Resolved" | | |
| 5 | Kiểm tra `resolved_at = now()` | Timestamp đúng | | |
| 6 | Kiểm tra `rca_required = False` (P3, không chronic) | RCA không bắt buộc | | |
| 7 | Kiểm tra KHÔNG có RCA Record tạo | | | |
| 8 | Kiểm tra `sla_resolution_breached` | Tính toán đúng dựa trên created_at vs resolved_at | | |
| 9 | Click "Close Incident" | IR.status = "Closed" thành công | | |
| 10 | Kiểm tra `closed_at = now()` | | | |
| 11 | Kiểm tra Asset Lifecycle Event: "incident_closed" | Audit trail | | |

---

### TC-12-09: Resolve P1 Incident — Auto-trigger RCA (BR-12-04)

**Mục tiêu:** Khi P1 Resolved → tự động tạo RCA, block Close cho đến khi RCA Completed
**Actor:** KTV HTM + Workshop Manager
**Điều kiện tiên quyết:** IR-UAT-007 (P1, In Progress, repair WO Completed)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Resolve IR-UAT-007 với resolution_notes đầy đủ | IR.status = "Resolved" | | |
| 2 | Kiểm tra `rca_required = True` | | | |
| 3 | Kiểm tra RCA Record được tạo tự động | RCA-YYYY-##### tạo mới | | |
| 4 | Kiểm tra RCA.trigger_type = "P1 Incident" | | | |
| 5 | Kiểm tra RCA.due_date = today + 7 ngày | Deadline 7 ngày cho P1 | | |
| 6 | Kiểm tra IR.status = "RCA Required" (chứ không phải Resolved) | IR state chuyển đúng | | |
| 7 | Thử Close IR-UAT-007 ngay (RCA chưa Completed) | Error IR-004: "Không thể đóng sự cố P1/P2 khi RCA chưa hoàn thành" | | |
| 8 | Điền RCA: root_cause, why_1→5, corrective_action, preventive_action | | | |
| 9 | Submit RCA Record | RCA.status = "RCA Completed" | | |
| 10 | Close IR-UAT-007 lại | IR.status = "Closed" thành công | | |

---

### TC-12-10: P2 Incident — RCA gate + 8h Resolution SLA

**Mục tiêu:** P2 full lifecycle — Acknowledge, Repair, Resolve, RCA, Close
**Actor:** Workshop Manager + KTV HTM + KTV Senior
**Điều kiện tiên quyết:** Asset `ACC-ASS-UAT-002` (siêu âm tim mạch)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Tạo IR với asset ACC-ASS-UAT-002, fault_code "PROBE_FAIL" | IR-UAT-008 created | | |
| 2 | Acknowledge với P2 High trong 2h | response_at set, sla_response_breached = False | | |
| 3 | Mở Asset Repair WO, link vào IR | IR status = In Progress | | |
| 4 | KTV hoàn thành repair, Resolve IR (trong 8h tổng) | resolved_at set, sla_resolution_breached = False | | |
| 5 | Kiểm tra RCA Record auto-created | RCA.trigger_type = "P2 Incident" | | |
| 6 | Kiểm tra RCA.due_date = today + 7 | | | |
| 7 | Workshop Manager thử Close IR | BLOCKED — IR-004 | | |
| 8 | KTV Senior điền RCA đầy đủ và Submit | RCA.status = Completed | | |
| 9 | Close IR thành công | IR.status = Closed | | |
| 10 | Kiểm tra SLA Compliance summary trên Dashboard | P2 compliance = 100% cho case này | | |

---

### TC-12-11: Chronic Failure Detection — ≥3 incidents same fault (BR-12-03)

**Mục tiêu:** Khi asset có ≥3 incidents cùng fault_code trong 90 ngày → auto-open RCA
**Actor:** CMMS Scheduler (simulate daily job)
**Điều kiện tiên quyết:** Asset `ACC-ASS-UAT-003` có IR-UAT-009 và IR-UAT-010 (cùng fault_code PROBE_DISCONNECT, trong 90 ngày)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Tạo IR-UAT-011 mới: asset ACC-ASS-UAT-003, fault_code "PROBE_DISCONNECT" | IR-UAT-011 created | | |
| 2 | Chạy `bench execute assetcore.services.imm12.detect_chronic_failures` | Scheduler chạy không lỗi | | |
| 3 | Kiểm tra COUNT = 3 incidents cùng fault_code trong 90 ngày | | | |
| 4 | Kiểm tra RCA Record được tạo tự động | RCA.trigger_type = "Chronic Failure" | | |
| 5 | Kiểm tra RCA.due_date = today + 14 ngày (chronic = 14 ngày) | | | |
| 6 | Kiểm tra `IR-UAT-009.is_chronic = True` | | | |
| 7 | Kiểm tra `IR-UAT-010.is_chronic = True` | | | |
| 8 | Kiểm tra `IR-UAT-011.is_chronic = True` | | | |
| 9 | Kiểm tra notification gửi Workshop Manager | Email "Chronic Failure Detected" | | |
| 10 | Kiểm tra notification gửi PTP Khối 2 | | | |
| 11 | Chạy detect_chronic_failures() lần 2 | KHÔNG tạo RCA Record thứ 2 (idempotent) | | |
| 12 | Tạo thêm IR-UAT-012 cùng fault_code | | | |
| 13 | Chạy detect_chronic_failures() lần 3 | Vẫn chỉ 1 RCA open (không duplicate) | | |

---

### TC-12-12: SLA Compliance Log — Immutability (BR-12-05)

**Mục tiêu:** SLA Compliance Log không thể bị xóa hoặc sửa bởi bất kỳ user nào
**Actor:** CMMS Admin (role cao nhất)
**Điều kiện tiên quyết:** Có SLA Compliance Log entries từ các TC trước

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Login với CMMS Admin | | | |
| 2 | Mở SLA Compliance Log list | Danh sách hiển thị đầy đủ | | |
| 3 | Click vào 1 log entry | Form mở ở chế độ read-only | | |
| 4 | Thử Edit bất kỳ field nào | Không có nút Save/Edit — chỉ read-only | | |
| 5 | Thử DELETE via API: `DELETE /api/resource/SLA Compliance Log/SLALOG-001` | 403 Forbidden: "Nhật ký SLA là bất biến" | | |
| 6 | Thử xóa via Frappe UI | Nút Delete bị ẩn hoặc disabled | | |
| 7 | Kiểm tra `is_immutable = True` trên mọi log entry | | | |

---

### TC-12-13: P4 Incident — Full Lifecycle (Low Priority)

**Mục tiêu:** P4 incident hoàn thành đúng quy trình, không cần RCA
**Actor:** Reporting User + Workshop Manager + KTV HTM
**Điều kiện tiên quyết:** Asset `ACC-ASS-UAT-004` (monitor thông thường)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Tạo IR với fault "Đèn LED màn hình tắt" | IR created | | |
| 2 | Acknowledge với P4 Low (trong 8h) | SLA response timer P4: 8h | | |
| 3 | Kiểm tra SLA timer màu XANH (P4 = green) | Color coding đúng | | |
| 4 | Assign WO, KTV resolve sau 48h (trong 72h SLA) | Resolved thành công | | |
| 5 | Kiểm tra `sla_response_breached = False` | | | |
| 6 | Kiểm tra `sla_resolution_breached = False` | | | |
| 7 | Kiểm tra `rca_required = False` | P4 không cần RCA | | |
| 8 | Close IR trực tiếp | Thành công — không có RCA gate | | |

---

### TC-12-14: RCA Form — 5-Why Analysis Completion

**Mục tiêu:** KTV Senior có thể điền đầy đủ RCA 5-Why và Submit
**Actor:** KTV Senior
**Điều kiện tiên quyết:** RCA Record `RCA-UAT-001` (status = RCA In Progress)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Login KTV Senior, vào `/imm-12/rca/RCA-UAT-001` | RCA form hiển thị | | |
| 2 | Thử Submit RCA khi root_cause_summary trống | Error RCA-002: "Phân tích RCA chưa đầy đủ" | | |
| 3 | Điền root_cause_summary | | | |
| 4 | Thử Submit khi corrective_action trống | Error RCA-002 | | |
| 5 | Điền why_1 → why_5 | | | |
| 6 | Điền corrective_action: "Đã thay thế pressure sensor chính hãng" | | | |
| 7 | Điền preventive_action: "Lên lịch kiểm tra sensor định kỳ 6 tháng" | | | |
| 8 | Submit RCA | RCA.status = "RCA Completed" | | |
| 9 | Kiểm tra completed_date = today | | | |
| 10 | Kiểm tra IR liên kết (IR-UAT-007) có thể Close | IR Close thành công | | |

---

### TC-12-15: SLA Dashboard KPI — PTP View

**Mục tiêu:** PTP Khối 2 xem SLA dashboard đầy đủ với đúng metrics
**Actor:** PTP Khối 2
**Điều kiện tiên quyết:** Đã có dữ liệu test từ TC-12-01 đến TC-12-14

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Login PTP Khối 2, vào `/imm-12/dashboard` | Dashboard hiển thị | | |
| 2 | Chọn tháng hiện tại | Data load đúng | | |
| 3 | Kiểm tra SLA compliance rate hiển thị theo 4 priority | 4 cards riêng biệt P1/P2/P3/P4 | | |
| 4 | Kiểm tra MTTA (Mean Time to Acknowledge) | Tính đúng từ (response_at - created_at) trung bình | | |
| 5 | Kiểm tra MTTR (Mean Time to Resolve) | Tính đúng từ (resolved_at - created_at) trung bình | | |
| 6 | Kiểm tra Open Incidents list với SLA countdown | Countdown chạy realtime | | |
| 7 | Kiểm tra màu SLA timer đúng theo priority | P1=đỏ, P2=cam, P3=vàng, P4=xanh | | |
| 8 | Click vào một IR trong danh sách | Navigate đến `/imm-12/incidents/:id` | | |
| 9 | Kiểm tra Chronic Failure count trong dashboard | Hiển thị số lượng chronic assets | | |
| 10 | Kiểm tra 6-month breach trend chart | Chart data đúng | | |

---

### TC-12-16: Reporting User — Không có quyền Acknowledge hoặc Close

**Mục tiêu:** Reporting User bị giới hạn đúng quyền hạn
**Actor:** Reporting User
**Điều kiện tiên quyết:** IR-UAT-013 (status = New)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Login Reporting User | | | |
| 2 | Mở IR-UAT-013 | Form hiển thị — read-only phần priority/assign | | |
| 3 | Thử click "Acknowledge" | Button bị ẩn hoặc 403 Forbidden | | |
| 4 | Thử API: `POST acknowledge_incident` | 403: "Bạn không có quyền thực hiện thao tác này" | | |
| 5 | Thử vào `/imm-12/dashboard` | Redirect hoặc 403 (route guard) | | |

---

### TC-12-17: Cancel Incident — False Alarm

**Mục tiêu:** Workshop Manager có thể hủy IR khi là false alarm
**Actor:** Workshop Manager
**Điều kiện tiên quyết:** IR-UAT-014 (status = New hoặc Acknowledged)

| # | Bước thực hiện | Kết quả kỳ vọng | PASS/FAIL | Ghi chú |
|---|---|---|---|---|
| 1 | Mở IR-UAT-014 | | | |
| 2 | Click "Hủy sự cố" | Dialog yêu cầu nhập lý do | | |
| 3 | Để trống lý do | Error: lý do hủy bắt buộc | | |
| 4 | Nhập lý do: "False alarm — nhân viên nhấn nút nhầm" | | | |
| 5 | Confirm Cancel | IR.status = "Cancelled" | | |
| 6 | Kiểm tra IR KHÔNG tính vào SLA compliance | | | |
| 7 | Thử Cancel IR-UAT-015 đang có Repair WO In Progress | Error IR-009: "Không thể hủy sự cố khi WO đang In Progress" | | |

---

## Section 2: Edge Cases

---

### EC-12-01: Cùng lúc tạo nhiều P1 IR

**Scenario:** 3 Reporting User cùng tạo IR cho 3 asset P1 trong cùng 1 phút

**Mục đích:** Kiểm tra hệ thống không conflict, SLA timer bắt đầu độc lập cho từng IR

**Kiểm tra:**
- Mỗi IR có `created_at` riêng chính xác
- SLA countdown độc lập cho mỗi IR
- Escalation gửi riêng cho từng IR (không merge notification)
- Không có race condition trong database

---

### EC-12-02: IR P1 — Repair WO hoàn thành nhưng asset vẫn lỗi

**Scenario:** KTV submit Repair WO là Completed, nhưng thiết bị vẫn báo alarm

**Mục đích:** Workshop không thể Close IR khi asset thực tế chưa ổn

**Kiểm tra:**
- Workshop Manager có thể Unlink Repair WO và mở WO mới
- IR ở lại "In Progress" với SLA timer vẫn chạy
- Ghi chú lý do mở WO thứ 2 vào IR
- SLA Resolution Breach khi tổng thời gian vượt 4h

---

### EC-12-03: Chronic Failure — RCA Cancelled và detect lại

**Scenario:** RCA-UAT-002 bị Cancel (lý do hợp lệ). Scheduler detect lại cùng fault_code

**Mục đích:** Sau khi RCA bị Cancel, chronic detection phải mở RCA mới

**Kiểm tra:**
- `detect_chronic_failures()` thấy RCA cũ đã Cancelled
- Tạo RCA mới cho cùng (asset, fault_code)
- Không ảnh hưởng đến SLA Compliance Log đã có

---

### EC-12-04: RCA Due Date quá hạn

**Scenario:** RCA-UAT-003 có due_date = hôm qua, status vẫn In Progress

**Kiểm tra:**
- `is_overdue` = True được set daily
- PTP Khối 2 nhận alert daily "RCA Overdue"
- IR liên kết KHÔNG tự động Close (vẫn phải chờ RCA)
- Alert leo thang sau 3 ngày trễ

---

### EC-12-05: Incident tạo cho Asset đang Out of Service

**Scenario:** Asset đã Out of Service từ IR trước, nhân viên tạo IR mới cho cùng asset

**Kiểm tra:**
- Hệ thống cho phép tạo IR (để tracking)
- Warning hiển thị: "Thiết bị đang Out of Service từ {date}"
- IR mới link đến IR cũ (cùng asset, gần nhau)
- Workshop Manager thấy cả 2 IR trong queue

---

### EC-12-06: SLA Breach — Timestamp backdating attempt

**Scenario:** Ai đó cố sửa `response_at` để tránh SLA breach

**Kiểm tra:**
- Không thể sửa `response_at` nếu đã set (read-only sau khi Acknowledge)
- Không thể sửa `created_at` (set by system, không cho user edit)
- SLA Compliance Log đã tạo KHÔNG bị ảnh hưởng
- Audit trail ghi lại attempt nếu có

---

### EC-12-07: Incident Group — Mất điện ảnh hưởng nhiều assets

**Scenario:** Mất điện ảnh hưởng 5 assets khác nhau cùng lúc

**Mục đích:** Hệ thống xử lý nhóm sự cố đúng cách

**Kiểm tra:**
- 5 IR riêng biệt tạo, mỗi IR có `incident_group_id` chung
- SLA của mỗi IR tính độc lập theo priority của từng asset
- Workshop thấy group view trên dashboard
- Resolve từng IR riêng (không bulk resolve)

---

## Section 3: Seed Data

### 3.1 Assets cần chuẩn bị

```python
# Chạy script seed: bench execute assetcore.tests.seed_imm12.setup_uat_data

ASSETS = [
    {
        "name": "ACC-ASS-UAT-001",
        "asset_name": "Máy thở Drager Evita 800 [UAT]",
        "asset_category": "Ventilator",
        "department": "ICU — Hồi sức tích cực",
        "location": "Phòng 302, Tầng 3",
        "status": "Active",
        "risk_class": "Class III",
        "is_life_support": True,
        "serial_no": "DRAGER-UAT-001",
    },
    {
        "name": "ACC-ASS-UAT-002",
        "asset_name": "Máy siêu âm tim GE Vivid E10 [UAT]",
        "asset_category": "Ultrasound",
        "department": "Tim mạch",
        "location": "Phòng siêu âm, Tầng 2",
        "status": "Active",
        "risk_class": "Class II",
        "is_life_support": False,
        "serial_no": "GE-UAT-001",
    },
    {
        "name": "ACC-ASS-UAT-003",
        "asset_name": "Máy siêu âm GE Vivid E9 [UAT]",
        "asset_category": "Ultrasound",
        "department": "Tim mạch",
        "location": "Phòng siêu âm 2, Tầng 2",
        "status": "Active",
        "risk_class": "Class II",
        "is_life_support": False,
        "serial_no": "GE-UAT-002",
    },
    {
        "name": "ACC-ASS-UAT-004",
        "asset_name": "Monitor Bệnh nhân Philips MX550 [UAT]",
        "asset_category": "Patient Monitor",
        "department": "Nội tổng quát",
        "location": "Phòng 108, Tầng 1",
        "status": "Active",
        "risk_class": "Class II",
        "is_life_support": False,
        "serial_no": "PHIL-UAT-001",
    },
]
```

### 3.2 Fault Codes cần có

```python
FAULT_CODES = [
    {"name": "VENT_ALARM_HIGH",    "label": "Báo động áp suất cao — Máy thở"},
    {"name": "VENT_ALARM_LOW",     "label": "Báo động áp suất thấp — Máy thở"},
    {"name": "PROBE_DISCONNECT",   "label": "Đầu dò siêu âm mất kết nối"},
    {"name": "PROBE_FAIL",         "label": "Đầu dò siêu âm hỏng"},
    {"name": "DISPLAY_LED_FAIL",   "label": "Đèn LED màn hình tắt"},
    {"name": "POWER_UNIT_FAIL",    "label": "Bộ nguồn hỏng"},
    {"name": "SENSOR_PRESSURE",    "label": "Cảm biến áp suất hỏng"},
    {"name": "CALIBRATION_DRIFT",  "label": "Sai số hiệu chuẩn vượt ngưỡng"},
]
```

### 3.3 Users cần chuẩn bị

```python
USERS = [
    {
        "email": "nurse.uat@hospital.vn",
        "full_name": "Nguyễn Thị Lan (UAT Nurse)",
        "role": "Reporting User",
        "department": "ICU",
    },
    {
        "email": "manager.uat@hospital.vn",
        "full_name": "Trần Văn Minh (UAT Workshop Manager)",
        "role": "Workshop Manager",
    },
    {
        "email": "ktv.nguyen.uat@hospital.vn",
        "full_name": "Lê Hoàng Nam (UAT KTV HTM)",
        "role": "KTV HTM",
    },
    {
        "email": "ktv.senior.uat@hospital.vn",
        "full_name": "Phạm Thị Hoa (UAT KTV Senior)",
        "role": "KTV HTM",
        "is_senior": True,
    },
    {
        "email": "ptp.uat@hospital.vn",
        "full_name": "Ngô Đức Thành (UAT PTP Khối 2)",
        "role": "PTP Khối 2",
    },
    {
        "email": "giam_doc.uat@hospital.vn",
        "full_name": "Dr. Vũ Trọng Nghĩa (UAT BGĐ)",
        "role": "Board Director",
    },
]
```

### 3.4 Pre-created IR cho TC-12-04 (P1 không Acknowledge trong 30 phút)

```python
# IR-UAT-002 — timestamp backdated 35 phút
{
    "name": "IR-UAT-002",
    "asset": "ACC-ASS-UAT-001",
    "fault_code": "VENT_ALARM_HIGH",
    "fault_description": "Máy thở báo alarm P_HIGH [TEST CASE TC-12-04]",
    "clinical_impact": "Test case: bệnh nhân giả lập",
    "status": "New",
    "priority": None,  # chưa classify
    "created_at": frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-35),
    "reported_by": "nurse.uat@hospital.vn",
}
```

### 3.5 Pre-created IR cho TC-12-11 (Chronic Failure test)

```python
# 2 IR cũ cùng fault_code PROBE_DISCONNECT trên ACC-ASS-UAT-003
IR_CHRONIC_HISTORY = [
    {
        "name": "IR-UAT-009",
        "asset": "ACC-ASS-UAT-003",
        "fault_code": "PROBE_DISCONNECT",
        "status": "Closed",
        "created_at": frappe.utils.add_days(frappe.utils.nowdate(), -60),  # 60 ngày trước
    },
    {
        "name": "IR-UAT-010",
        "asset": "ACC-ASS-UAT-003",
        "fault_code": "PROBE_DISCONNECT",
        "status": "Closed",
        "created_at": frappe.utils.add_days(frappe.utils.nowdate(), -28),  # 28 ngày trước
    },
]
# IR-UAT-011 sẽ được tạo trong TC-12-11 bước 1 — là incident thứ 3 trigger chronic
```

### 3.6 Asset Repair WO mẫu

```python
REPAIR_WO = {
    "name": "AR-UAT-001",
    "asset": "ACC-ASS-UAT-001",
    "status": "Open",
    "wo_type": "Corrective",
    "priority": "P1 Critical",
    "assigned_to": "ktv.nguyen.uat@hospital.vn",
    "fault_description": "WO sửa chữa cho TC-12-07",
}
```

---

## Checklists UAT Sign-off

### Sign-off điều kiện

Để UAT IMM-12 được duyệt, CẦN đạt:

| Điều kiện | Yêu cầu | Mức chấp nhận |
|---|---|---|
| Test cases passed | TC-12-01 đến TC-12-17 | ≥ 95% PASS (≥ 16/17) |
| Critical TCs (P1 flow) | TC-12-03, TC-12-04, TC-12-09 | 100% PASS — KHÔNG thỏa hiệp |
| SLA immutability | TC-12-12 | 100% PASS |
| Chronic detection | TC-12-11 | 100% PASS |
| Edge cases | EC-12-01 đến EC-12-07 | ≥ 80% PASS |
| Performance | SLA dashboard load < 3s | Đo trong TC-12-15 |
| No data corruption | Audit trail đầy đủ mọi TC | 100% |

### Người ký duyệt

| Vai trò | Họ tên | Chữ ký | Ngày |
|---|---|---|---|
| QA Lead | | | |
| Workshop Manager | | | |
| PTP Khối 2 | | | |
| Product Owner | | | |
