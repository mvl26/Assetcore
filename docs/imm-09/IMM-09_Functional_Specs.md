# IMM-09 — Functional Specifications

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-09 — Corrective Maintenance / Repair |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Chuẩn tham chiếu | WHO HTM 2025, ISO 13485:2016, ISO 9001:2015, NĐ 98/2021/NĐ-CP |
| Dependency | Frappe v15, IMM-00 Foundation, IMM-08 PM, IMM-12 Incident |
| Tác giả | AssetCore Team |

---

## 1. Scope

### 1.1 In Scope

| # | Hạng mục |
|---|---|
| 1 | DocType `Asset Repair` (submittable) + 2 child (`Spare Parts Used`, `Repair Checklist`) + `Firmware Change Request` |
| 2 | State machine 9 trạng thái (Open → Completed / Cannot Repair / Cancelled) |
| 3 | 7 business rules (BR-09-01 → BR-09-07) enforce qua service + controller |
| 4 | Tính MTTR theo calendar time + SLA matrix `risk_class × priority` |
| 5 | 12 REST endpoints (CRUD + workflow actions + KPI) |
| 6 | 7 Frontend views Vue 3 (Dashboard, List, Detail, Create, Diagnose, Parts, Checklist, MTTR Report) |
| 7 | Scheduler: hourly SLA breach check, daily overdue email, monthly MTTR rollup |
| 8 | Tích hợp IMM-08 (PM Halted → CM), IMM-11 (post-repair Cal), IMM-12 (CAPA cho repeat failure) |

### 1.2 Out of Scope

| # | Hạng mục | Lý do |
|---|---|---|
| 1 | Procurement vật tư khẩn cấp | Thuộc module Inventory / Procurement |
| 2 | Vendor Service Order (gửi thiết bị ra ngoài hãng) | Phase sau (IMM-09.1) |
| 3 | Mobile native app | Web responsive là đủ Wave 1 |
| 4 | Predictive maintenance (AI) | Roadmap dài hạn |

---

## 2. Actors

| Actor | Mô tả | Trách nhiệm chính |
|---|---|---|
| Workshop Manager | Quản lý xưởng kỹ thuật | Tạo / phân công / cancel WO; review SLA breach; phê duyệt FCR |
| HTM Technician (KTV HTM) | Kỹ thuật viên thực hiện sửa chữa | Diagnose, request parts, execute repair, fill checklist |
| Kho vật tư | Thủ kho | Xuất vật tư theo `request_spare_parts`, gắn `stock_entry_ref` |
| Trưởng khoa phòng | Người dùng cuối thiết bị | Xác nhận nghiệm thu (ký `dept_head_name`) |
| PTP Khối 2 | Phó Trưởng phòng giám sát | Xem MTTR Dashboard, KPI compliance |
| CMMS Admin | System admin | Cấu hình, chạy scheduler manual, audit |
| CMMS Auto | System job | Auto tạo CM WO từ PM Halted |

---

## 3. User Stories (INVEST)

| ID | As | I want | So that | SP |
|---|---|---|---|---|
| US-09-01 | Workshop Manager | Tạo CM WO bắt buộc có nguồn (IR hoặc PM WO) | Mọi sửa chữa truy xuất được lý do | 5 |
| US-09-02 | Workshop Manager | Phân công KTV với priority phù hợp risk class | Phân bổ nhân lực hợp lý | 3 |
| US-09-03 | KTV HTM | Ghi chẩn đoán + chọn `root_cause_category` + ảnh thiết bị | Hồ sơ kỹ thuật đầy đủ cho audit | 5 |
| US-09-04 | KTV HTM | Yêu cầu vật tư trực tiếp trong WO và nhận notification khi xuất xong | Không cần liên lạc thủ công | 8 |
| US-09-05 | Kho vật tư | Xác nhận xuất vật tư bằng `stock_entry_ref` | Vật tư có chứng từ kế toán | 3 |
| US-09-06 | KTV HTM | Tạo Firmware Change Request liên kết với WO khi update firmware | Mọi thay đổi firmware có change control | 5 |
| US-09-07 | KTV HTM | Điền Repair Checklist; hệ thống chỉ cho Submit khi 100 % Pass | Đảm bảo an toàn trước khi trả thiết bị | 5 |
| US-09-08 | Trưởng khoa phòng | Xác nhận nhận lại thiết bị bằng chữ ký số (dept_head_name) | Bàn giao có biên bản | 3 |
| US-09-09 | KTV HTM | Đánh dấu Cannot Repair với lý do | Trigger EOL process | 3 |
| US-09-10 | PTP Khối 2 | Xem MTTR theo tháng + first-time fix rate + backlog | Báo cáo hiệu suất workshop | 5 |
| US-09-11 | PTP Khối 2 | Xem repair history của 1 thiết bị + MTTR average | Phát hiện thiết bị có vấn đề mãn tính | 3 |
| US-09-12 | System | Tự động tạo CM WO khi PM Halted (Major Failure) | Không bỏ sót lỗi từ PM | 5 |

---

## 4. Functional Requirements

### 4.1 Nhóm Repair Work Order (FR-09-01 → FR-09-08)

| FR ID | Mô tả | Actor | Endpoint |
|---|---|---|---|
| FR-09-01 | Tạo Asset Repair WO `WO-CM-.YYYY.-.#####` với nguồn bắt buộc | Workshop Manager | POST `create_repair_work_order` |
| FR-09-02 | List WO với filter (`status`, `priority`, `assigned_to`, `risk_class`) + pagination | All roles | GET `list_repair_work_orders` |
| FR-09-03 | Chi tiết WO + asset enrichment (`asset_info`) | All roles | GET `get_repair_work_order` |
| FR-09-04 | Phân công KTV (Open → Assigned) + set priority | Workshop Manager | POST `assign_technician` |
| FR-09-05 | Nộp diagnosis (Assigned/Diagnosing → Pending Parts hoặc In Repair) | KTV HTM | POST `submit_diagnosis` |
| FR-09-06 | Bắt đầu sửa chữa (→ In Repair) | KTV HTM | POST `start_repair` |
| FR-09-07 | Đóng WO (Pending Inspection → Completed) HOẶC đánh dấu Cannot Repair | KTV + Trưởng khoa | POST `close_work_order` |
| FR-09-08 | Lịch sử sửa chữa của 1 thiết bị (`asset_ref`) | All roles | GET `get_asset_repair_history` |

### 4.2 Nhóm Spare Parts (FR-09-09 → FR-09-11)

| FR ID | Mô tả | Actor | Endpoint |
|---|---|---|---|
| FR-09-09 | Yêu cầu xuất vật tư (cập nhật `stock_entry_ref` trên child rows) | KTV / Kho | POST `request_spare_parts` |
| FR-09-10 | Tìm kiếm Item vật tư trong catalog | KTV HTM | GET `search_spare_parts` |
| FR-09-11 | Tự tính `total_parts_cost = Σ (qty × unit_cost)` trên `validate()` | System | controller `_compute_parts_cost` |

### 4.3 Nhóm KPI & Reports (FR-09-12 → FR-09-13)

| FR ID | Mô tả | Actor | Endpoint |
|---|---|---|---|
| FR-09-12 | KPI tháng: total_completed, mttr_avg, sla_compliance %, repeat failure count, open WO count, root cause breakdown | PTP / Manager | GET `get_repair_kpis` |
| FR-09-13 | MTTR Report: trend 6 tháng, first-fix rate, backlog by department, cost per repair | PTP / Manager | GET `get_mttr_report` |

### 4.4 Nhóm Scheduler (FR-09-14 → FR-09-16)

| FR ID | Job | Tần suất | Logic |
|---|---|---|---|
| FR-09-14 | `check_repair_sla_breach` | Hourly | Mark `sla_breached = 1` khi `elapsed_hours ≥ sla_target_hours`; publish realtime `cm_sla_breached` |
| FR-09-15 | `check_repair_overdue` | Daily 07:00 | Email Workshop Manager khi WO `status IN (Open, Assigned, Pending Parts)` AND `open_datetime < today − 7d` |
| FR-09-16 | `update_asset_mttr_avg` | Monthly 01 06:00 | Cập nhật `Asset.custom_mttr_avg_hours` (trung bình 12 WO Completed gần nhất) |

---

## 5. Business Rules

| ID | Rule | Enforce | Hậu quả vi phạm |
|---|---|---|---|
| BR-09-01 | WO bắt buộc `incident_report` OR `source_pm_wo` | `validate_repair_source()` `before_insert` | Block insert — `CM-001` |
| BR-09-02 | Mỗi `spare_parts_used` row phải có `stock_entry_ref` tồn tại trong `Stock Entry` | `validate_spare_parts_stock_entries()` `before_submit` | Block submit — `CM-003`/`CM-004` |
| BR-09-03 | `firmware_updated = 1` → bắt buộc `firmware_change_request` linked + status `Approved` | `validate_firmware_change_request()` `before_submit` | Block submit — `CM-005`/`CM-006` |
| BR-09-04 | Tất cả `repair_checklist` row phải có `result` AND không Fail | `validate_repair_checklist_complete()` `before_submit` | Block submit — `CM-007`/`CM-008` |
| BR-09-05 | Asset → `Under Repair` khi `on_insert`; Asset → `Active` khi `on_submit` Completed; → `Out of Service` khi Cannot Repair | `set_asset_under_repair()` + `complete_repair()` + `_mark_cannot_repair()` | Asset state inconsistent |
| BR-09-06 | Lỗi lặp lại trong 30 ngày → `is_repeat_failure = 1`; gợi ý CAPA | `check_repeat_failure()` `before_insert` | Flag để KPI đo first-fix rate |
| BR-09-07 | `mttr_hours > sla_target_hours` → `sla_breached = 1` | `complete_repair()` | KPI rollup, email alert |

---

## 6. Permission Matrix

| Action | Workshop Manager | HTM Technician | Kho vật tư | Trưởng khoa | PTP Khối 2 | CMMS Admin |
|---|---|---|---|---|---|---|
| Create WO | ✅ | — | — | — | — | ✅ |
| Read WO | ✅ | ✅ (assigned) | ✅ | ✅ (own dept) | ✅ | ✅ |
| Assign technician | ✅ | — | — | — | — | ✅ |
| Submit diagnosis | — | ✅ | — | — | — | ✅ |
| Request spare parts | ✅ | ✅ | ✅ | — | — | ✅ |
| Start repair | — | ✅ | — | — | — | ✅ |
| Close WO (submit) | ✅ | ✅ | — | — | — | ✅ |
| Confirm dept_head | — | — | — | ✅ | — | ✅ |
| Mark Cannot Repair | ✅ | ✅ | — | — | — | ✅ |
| Cancel WO | ✅ | — | — | — | — | ✅ |
| View MTTR / KPI | ✅ | — | — | — | ✅ | ✅ |
| Approve FCR | ✅ | — | — | — | — | ✅ |

---

## 7. Validation Rules

| VR ID | Field / Object | Rule | Error Message (vi) |
|---|---|---|---|
| VR-09-01 | `incident_report` + `source_pm_wo` | Ít nhất 1 trong 2 phải có giá trị | "Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc" |
| VR-09-02 | `asset_ref` | Asset không đang có WO mở khác | "Thiết bị đang có phiếu sửa chữa đang mở: {wo}" |
| VR-09-03 | `repair_type` | Phải IN (Corrective, Emergency, Warranty Repair) | "Loại sửa chữa không hợp lệ" |
| VR-09-04 | `priority` | Phải IN (Normal, Urgent, Emergency) | "Ưu tiên không hợp lệ" |
| VR-09-05 | `spare_parts_used[*].stock_entry_ref` | Bắt buộc khi submit; phải tồn tại trong `Stock Entry` | "Vật tư '{item}' (dòng {idx}) thiếu phiếu xuất kho" |
| VR-09-06 | `firmware_change_request` | Reqd khi `firmware_updated = 1`; FCR.status = "Approved" | "Cập nhật firmware yêu cầu FCR đã được phê duyệt" |
| VR-09-07 | `repair_checklist[*].result` | Reqd; không được "Fail" | "Mục kiểm tra #{idx} '{desc}' chưa Pass — không thể hoàn thành" |
| VR-09-08 | `cannot_repair_reason` | Reqd khi `status = Cannot Repair` | "Vui lòng nhập lý do không thể sửa chữa" |
| VR-09-09 | `dept_head_name` | Reqd khi close_work_order (không phải Cannot Repair) | "Phải có xác nhận của Trưởng khoa phòng" |
| VR-09-10 | `assigned_to` | Reqd transition Open → Assigned; phải là User có role HTM Technician | "Phải chọn KTV để phân công" |
| VR-09-11 | `mttr_hours` | Auto = `(completion_datetime − open_datetime) / 3600` | (auto, read-only) |
| VR-09-12 | `sla_target_hours` | Auto từ `get_sla_target(risk_class, priority)` | (auto, read-only) |

---

## 8. Non-Functional Requirements

| NFR ID | Category | Yêu cầu | Target |
|---|---|---|---|
| NFR-09-01 | Performance | List WO với filter chuẩn (≤ 100k records) | P95 < 300 ms |
| NFR-09-02 | Performance | Detail WO + asset_info enrichment | P95 < 500 ms |
| NFR-09-03 | Performance | Spare parts search (Item catalog 10k items) | P95 < 800 ms |
| NFR-09-04 | Concurrency | 20 WO active đồng thời không conflict | Optimistic lock qua `modified` |
| NFR-09-05 | SLA alert latency | Cảnh báo khi vượt SLA | ≤ 1 giờ (scheduler hourly) |
| NFR-09-06 | Realtime push | `cm_sla_breached` đến KTV được gán | < 5 s |
| NFR-09-07 | Audit immutability | Asset Repair sau Submit không xoá / sửa được | Frappe submittable |
| NFR-09-08 | Lifecycle event | Mọi transition sinh `Asset Lifecycle Event` | 100 % coverage |
| NFR-09-09 | Localization | Tất cả error message qua `frappe._()` | vi.csv |
| NFR-09-10 | Logging | Service function log actor + WO name | `frappe.logger("imm09")` |
| NFR-09-11 | Mobile responsive | KTV thao tác trên tablet ≥ 768 px | Tested viewports |
| NFR-09-12 | Offline tolerance | Form diagnosis + checklist hỗ trợ offline queue | IndexedDB + sync on reconnect |

---

## 9. Acceptance Criteria (Gherkin)

### 9.1 Tạo WO bắt buộc nguồn (BR-09-01)

```gherkin
Scenario: Tạo CM WO không có nguồn → block
  Given Workshop Manager đăng nhập
  When POST create_repair_work_order với asset_ref="AC-ASSET-...", incident_report="", source_pm_wo=""
  Then response.success = false
   And response.error contains "Phải có nguồn sửa chữa"

Scenario: Tạo CM WO với incident_report → OK
  Given Incident Report "IR-2026-00123" đã submitted, asset_ref="AC-ASSET-2026-00042"
  When POST create_repair_work_order với incident_report="IR-2026-00123", repair_type="Corrective", priority="Urgent"
  Then response.data.name khớp regex "^WO-CM-2026-\d{5}$"
   And response.data.status = "Open"
   And response.data.sla_target_hours = 24.0  # Class III × Urgent
   And Asset.status = "Under Repair"
   And có 1 Asset Lifecycle Event event_type="repair_opened"
```

### 9.2 Spare parts bắt buộc stock_entry_ref (BR-09-02)

```gherkin
Scenario: Submit WO khi spare part thiếu stock_entry_ref → block
  Given WO ở "Pending Inspection" với spare_parts_used có 1 row thiếu stock_entry_ref
  When close_work_order
  Then throw ValidationError "Vật tư '{item}' (dòng 1) thiếu phiếu xuất kho"

Scenario: Stock entry không tồn tại → block
  Given spare_parts_used row có stock_entry_ref="STE-INVALID-001"
  When close_work_order
  Then throw "Phiếu xuất kho 'STE-INVALID-001' không tồn tại trong hệ thống"
```

### 9.3 Firmware change control (BR-09-03)

```gherkin
Scenario: firmware_updated=1 thiếu FCR → block
  Given WO firmware_updated=1, firmware_change_request=null
  When close_work_order
  Then throw "Cập nhật firmware yêu cầu FCR được phê duyệt và liên kết"

Scenario: FCR chưa Approved → block
  Given firmware_change_request="FCR-2026-00007" status="Pending Approval"
  When close_work_order
  Then throw "FCR 'FCR-2026-00007' chưa được phê duyệt (status: Pending Approval)"
```

### 9.4 Checklist 100 % Pass (BR-09-04)

```gherkin
Scenario: Checklist có row Fail → block
  Given repair_checklist gồm 5 row, 4 Pass + 1 Fail
  When close_work_order
  Then throw "Mục kiểm tra #3 '...' chưa Pass — không thể hoàn thành"

Scenario: Checklist trống → block
  Given repair_checklist = []
  When close_work_order
  Then throw "Phải điền Repair Checklist trước khi hoàn thành sửa chữa"
```

### 9.5 MTTR & SLA tracking (BR-09-07)

```gherkin
Scenario: MTTR vượt SLA → flag breach
  Given WO Class III × Urgent, sla_target_hours=24
   And open_datetime="2026-04-14 07:00:00"
  When close_work_order tại "2026-04-15 14:00:00" (31h)
  Then mttr_hours = 31.0
   And sla_breached = 1
   And Asset.status = "Active"
   And Asset.custom_last_repair_date = today
   And Asset Lifecycle Event "repair_completed" với notes "MTTR: 31.0h | SLA: Breached"
```

### 9.6 Cannot Repair → EOL trigger (BR-09-05)

```gherkin
Scenario: Cannot Repair
  Given WO ở "In Repair", KTV xác nhận không sửa được
  When close_work_order(cannot_repair=1, cannot_repair_reason="Mainboard cháy không có linh kiện thay thế")
  Then WO.status = "Cannot Repair"
   And Asset.status = "Out of Service"
   And có Asset Lifecycle Event event_type="cannot_repair"
   And IMM-13/14 EOL workflow được trigger (manual review)
```

### 9.7 Repeat failure detection (BR-09-06)

```gherkin
Scenario: Tạo WO thứ 2 trong 30 ngày
  Given WO Completed cho asset "AC-ASSET-X" tại "2026-04-01"
  When tạo WO mới cho asset "AC-ASSET-X" tại "2026-04-18"
  Then is_repeat_failure = 1
   And UI hiển thị banner "Tái hỏng — gợi ý mở CAPA (IMM-12)"
```

### 9.8 PM Halted → auto CM (IMM-08 → IMM-09)

```gherkin
Scenario: PM phát hiện Major Failure → auto CM WO
  Given PM Work Order "PM-WO-2026-00088" status="Halted–Major Failure"
  When IMM-08 trigger create_repair_work_order(source_pm_wo="PM-WO-2026-00088", priority="Urgent")
  Then CM WO "WO-CM-2026-XXXXX" được tạo
   And source_pm_wo = "PM-WO-2026-00088"
   And Asset.status = "Under Repair"
```

---

## 10. WHO HTM & QMS Mapping

| Yêu cầu IMM-09 | WHO HTM | ISO 13485 | ISO 9001 | NĐ98 |
|---|---|---|---|---|
| WO bắt buộc cho mọi sửa chữa | CMMS §3.2.3 | 7.5.1 | 8.5.1 | Điều 28 |
| Traceability nguồn (BR-09-01) | HTM 2025 §5.4.2 | 7.5.3 | 8.5.2 | Điều 29 |
| Spare parts có chứng từ (BR-09-02) | Maintenance §6.3 | 7.5.5 | 8.4.3 | Điều 31 |
| Firmware change control (BR-09-03) | HTM 2025 §7.2 | 7.3.7 | 8.5.6 | Điều 35 |
| Acceptance test sau sửa chữa (BR-09-04) | Maintenance §5.5.3 | 8.2.4 | 8.6 | Điều 30 |
| Asset status management (BR-09-05) | CMMS §3.3.1 | 7.5.1 | 8.5.1 | Điều 28 |
| MTTR / KPI tracking (BR-09-07) | HTM 2025 §6.1 | 8.2.5 | 9.1.1 | Điều 36 |
| Repeat failure → CAPA (BR-09-06) | HTM 2025 §6.4 | 8.5.2 | 10.2 | — |
| Hồ sơ immutable | Maintenance §5.5.5 | 4.2.5 | 7.5 | Điều 37 |
| Audit trail (Lifecycle Event) | HTM 2025 §6.4 | 4.2.5 | 7.5.3 | Điều 40 |

---

## 11. Revision History

| Version | Date | Author | Thay đổi chính |
|---|---|---|---|
| 1.0.0 | 2026-04-17 | AssetCore Team | Bản khởi tạo (extend ERPNext Asset Repair) |
| **2.0.0** | **2026-04-18** | **AssetCore Team** | **Refactor sang DocType native AssetCore; chuẩn hoá theo template IMM-00; bổ sung FR-09-12/13 KPI; SLA matrix sửa lại theo `get_sla_target` thực tế trong code; thêm BR-09-06/07; gắn integration IMM-12 CAPA cho repeat failure** |

---

*End of Functional Specifications v2.0.0 — IMM-09 Corrective Maintenance.*
