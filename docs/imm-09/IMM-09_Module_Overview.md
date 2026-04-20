# IMM-09 — Corrective Maintenance / Repair

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-09 — Corrective Maintenance / Repair |
| Phiên bản | 2.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | LIVE |
| Tác giả | AssetCore Team |

---

## 1. Mục đích

IMM-09 quản lý toàn bộ vòng đời **sửa chữa khắc phục** (Corrective Maintenance) thiết bị y tế: tiếp nhận yêu cầu sửa chữa từ nhiều nguồn (PM Halted, Incident Report, manual), phân công kỹ thuật viên, chẩn đoán lỗi, xuất kho phụ tùng có chứng từ, thực hiện sửa chữa, nghiệm thu sau sửa chữa với checklist, và trả thiết bị về trạng thái Active. Module đo MTTR, gắn SLA target theo `risk_class × priority`, phát hiện tái hỏng (repeat failure) và tự sinh CAPA (IMM-12) khi có lỗi lặp lại.

**Nguyên tắc cốt lõi:**

| Nguyên tắc | Nội dung |
|---|---|
| Mọi sửa chữa = 1 Asset Repair WO | Không chấp nhận thao tác sửa chữa ngoài Work Order. |
| Nguồn bắt buộc | WO phải có `incident_report` HOẶC `source_pm_wo` (BR-09-01). |
| Vật tư phải có chứng từ | Mọi `Spare Parts Used` row bắt buộc `stock_entry_ref` (BR-09-02). |
| Firmware có change control | `firmware_updated = 1` phải link `Firmware Change Request` Approved (BR-09-03). |
| Nghiệm thu 100 % Pass | Tất cả `Repair Checklist` phải Pass mới Submit (BR-09-04). |
| Trạng thái Asset gắn liền WO | Asset chuyển sang `Under Repair` ngay khi WO mở; trả về `Active` khi Completed (BR-09-05). |

---

## 2. Vị trí trong kiến trúc

```
┌──────────────────────────────────────────────────────────────────┐
│           IMM-00 Foundation (AC Asset, ALE, SLA, CAPA)          │
└────────────────┬───────────────────────────────────┬─────────────┘
                 │ transition_asset_status           │ create_capa
                 │ create_lifecycle_event            │ (repeat failure)
                 ▼                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                   IMM-09 Corrective Maintenance                  │
│                                                                  │
│  DocTypes:                                                       │
│    • Asset Repair (WO-CM-YYYY-#####)         submittable        │
│    • Spare Parts Used         (child)                            │
│    • Repair Checklist         (child)                            │
│    • Firmware Change Request  (FCR-YYYY-#####)                   │
│                                                                  │
│  Service: assetcore/services/imm09.py                            │
│  API:     assetcore/api/imm09.py  (12 endpoints)                 │
│  FE:      frontend/src/views/CM*.vue + stores/imm09.ts           │
└────────┬─────────────────────────────────┬───────────────────────┘
         ▲                                 │
         │ source_pm_wo                    │ trigger
         │ (PM Halted)                     ▼
   ┌─────┴──────┐                  ┌──────────────┐
   │  IMM-08 PM │                  │  IMM-11 Cal. │ (post-repair calibration)
   └────────────┘                  └──────────────┘
         ▲                                 ▲
         │ incident_report                 │ Cannot Repair → EOL
         │                                 │
   ┌─────┴──────┐                  ┌──────┴───────┐
   │  IMM-12 IR │                  │ IMM-13/14 EOL│
   └────────────┘                  └──────────────┘
```

---

## 3. DocTypes

| DocType | Naming | Loại | Mục đích |
|---|---|---|---|
| Asset Repair | `WO-CM-.YYYY.-.#####` | Submittable | Phiếu sửa chữa chính, audit-immutable sau Submit |
| Spare Parts Used | (child) | Child Table | Vật tư đã dùng + `stock_entry_ref` bắt buộc |
| Repair Checklist | (child) | Child Table | Checklist nghiệm thu sau sửa chữa |
| Firmware Change Request | `FCR-.YYYY.-.#####` | Submittable | Kiểm soát thay đổi firmware (BR-09-03) |

### 3.1 Field map — Asset Repair (chính)

| Nhóm | Fields |
|---|---|
| Asset | `asset_ref` (Link Asset, reqd), `asset_name`, `asset_category`, `risk_class` (Class I/II/III), `serial_no` |
| Source | `incident_report` (Link), `source_pm_wo` (Link PM Work Order) — BR-09-01 |
| Phân loại | `repair_type` (Corrective / Emergency / Warranty Repair), `priority` (Normal / Urgent / Emergency), `status` |
| Thời gian | `open_datetime`, `assigned_datetime`, `completion_datetime` |
| SLA & MTTR | `sla_target_hours`, `mttr_hours`, `sla_breached`, `is_repeat_failure` |
| Phân công | `assigned_to` (User), `assigned_by` |
| Chẩn đoán | `diagnosis_notes`, `root_cause_category` (Mechanical / Electrical / Software / User Error / Wear and Tear / Unknown), `repair_summary` |
| Vật tư | `spare_parts_used` (Table), `total_parts_cost` |
| Checklist | `repair_checklist` (Table) |
| Firmware | `firmware_updated`, `firmware_change_request` (Link FCR) |
| Nghiệm thu | `dept_head_name`, `dept_head_confirmation_datetime` |
| Khác | `is_warranty_claim`, `warranty_claim_ref`, `cannot_repair_reason`, `technician_notes`, `attachments` |

### 3.2 Field map — Spare Parts Used (child)

`item_code` (Link Item, reqd) · `item_name` (fetch) · `qty` · `uom` · `unit_cost` · `total_cost` (auto) · `stock_entry_ref` (Link Stock Entry, reqd — BR-09-02) · `notes`

### 3.3 Field map — Repair Checklist (child)

`test_description` (reqd) · `test_category` (Electrical / Mechanical / Software / Safety / Performance) · `expected_value` · `measured_value` · `result` (Pass / Fail / N/A) · `notes` · `photo`

---

## 4. Service Functions

File: `assetcore/services/imm09.py`

| Function | Caller | Mô tả |
|---|---|---|
| `validate_repair_source(doc)` | `Asset Repair.before_insert` | BR-09-01 — chặn nếu thiếu cả `incident_report` và `source_pm_wo` |
| `validate_asset_not_under_repair(asset_ref)` | `before_insert` | Chặn duplicate WO cho cùng asset |
| `check_repeat_failure(asset_ref)` | `before_insert` | Đánh dấu `is_repeat_failure` nếu có WO Completed trong 30 ngày |
| `set_asset_under_repair(asset_ref, wo_name)` | `on_insert` | Đổi `Asset.status = Under Repair` + sinh ALE `repair_opened` |
| `validate_spare_parts_stock_entries(doc)` | `before_submit` | BR-09-02 — mỗi row phải có `stock_entry_ref` hợp lệ |
| `validate_firmware_change_request(doc)` | `before_submit` | BR-09-03 — FCR Approved nếu `firmware_updated` |
| `validate_repair_checklist_complete(doc)` | `before_submit` | BR-09-04 — checklist đầy đủ + 100 % Pass |
| `get_sla_target(risk_class, priority)` | API + Service | Tra ma trận SLA (giờ) |
| `complete_repair(doc)` | `on_submit` | Tính `mttr_hours`, set `sla_breached`, đổi Asset về Active, sinh ALE `repair_completed` |
| `_create_lifecycle_event(...)` | Internal | Sinh `Asset Lifecycle Event` (immutable) |
| `check_repair_sla_breach()` | Scheduler hourly | Đánh dấu WO vượt SLA, publish realtime `cm_sla_breached` |
| `check_repair_overdue()` | Scheduler daily 07:00 | Email Workshop Manager khi WO open > 7 ngày |
| `update_asset_mttr_avg()` | Scheduler monthly 01 06:00 | Cập nhật `Asset.custom_mttr_avg_hours` (12 WO gần nhất) |

---

## 5. Workflow States

```
                     ┌─────────────────────────────────────┐
[start] ──► Open ──► Assigned ──► Diagnosing                 │
                       │             │                       │
                       │             ├──► Pending Parts ──┐  │
                       │             │                    │  │
                       │             └────────► In Repair ◄──┤
                       │                          │          │
                       │                          ▼          │
                       │              Pending Inspection ────┤
                       │                          │          │
                       │                          ├─► Completed (Asset → Active)
                       │                          │
                       │                          └─► Cannot Repair (Asset → Out of Service)
                       └─► Cancelled
```

| State | Mô tả | Actor | Transition trigger |
|---|---|---|---|
| Open | WO vừa tạo, chưa phân công | Workshop Manager / system (PM Halted) | `create_repair_work_order` |
| Assigned | Đã chọn KTV; Asset → Under Repair | Workshop Manager | `assign_technician` |
| Diagnosing | KTV đang chẩn đoán | KTV HTM | (bắt đầu thao tác) |
| Pending Parts | Chờ kho xuất vật tư | KTV / Kho | `submit_diagnosis(needs_parts=1)` |
| In Repair | Đang sửa chữa | KTV HTM | `request_spare_parts` đủ HOẶC `start_repair` |
| Pending Inspection | Sửa xong, chờ nghiệm thu | KTV HTM | `close_work_order` (pre-submit) |
| Completed | Nghiệm thu pass, Asset → Active | KTV + Trưởng khoa | `close_work_order` submit |
| Cannot Repair | Không sửa được, Asset → Out of Service | Workshop Manager | `close_work_order(cannot_repair=1)` |
| Cancelled | Hủy WO có lý do | Workshop Manager | (manual) |

---

## 6. Roles & Permissions

| Role | Quyền chính |
|---|---|
| Workshop Manager | Create / Write / Submit / Cancel Asset Repair; phân công KTV; phê duyệt FCR |
| HTM Technician | Read / Write WO được gán (`if_owner = 1`); điền diagnosis, parts, checklist |
| Kho vật tư | Read WO; Write `Spare Parts Used.stock_entry_ref` |
| Trưởng khoa phòng | Read WO; xác nhận `dept_head_name` khi nghiệm thu |
| PTP Khối 2 | Read all; xem MTTR Report, dashboard KPI |
| CMMS Admin | Read / Write / Submit / Cancel / Delete |

Permission Query: `HTM Technician` chỉ thấy WO có `assigned_to = session.user`.

---

## 7. Business Rules

| ID | Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-09-01 | WO phải có ≥ 1 nguồn: `incident_report` OR `source_pm_wo` | `validate_repair_source()` (before_insert) | WHO HTM 2025 §5.4.2 |
| BR-09-02 | Mỗi `Spare Parts Used` row bắt buộc `stock_entry_ref` hợp lệ (Stock Entry tồn tại) | `validate_spare_parts_stock_entries()` (before_submit) | WHO Maintenance §6.3 |
| BR-09-03 | `firmware_updated = 1` → bắt buộc FCR linked + status `Approved` | `validate_firmware_change_request()` (before_submit) | WHO HTM 2025 §7.2 |
| BR-09-04 | `Repair Checklist` đầy đủ + tất cả `result = Pass` (không có Fail / N/A trống) trước Submit | `validate_repair_checklist_complete()` (before_submit) | WHO Maintenance §5.5.3 |
| BR-09-05 | `Asset.status = Under Repair` khi WO Open / Assigned; trả về `Active` khi Completed; `Out of Service` khi Cannot Repair | `set_asset_under_repair()` + `complete_repair()` + `_mark_cannot_repair()` | WHO HTM §3.3.1 |
| BR-09-06 | Lỗi lặp lại trong 30 ngày → `is_repeat_failure = 1` → khuyến nghị mở CAPA (IMM-12) | `check_repeat_failure()` (before_insert) | ISO 13485:8.5 |
| BR-09-07 | MTTR vượt SLA target → `sla_breached = 1`; Asset Repair record trở thành KPI tracker | `complete_repair()` + `check_repair_sla_breach()` | WHO HTM §6.1 |

### SLA Matrix (giờ — calendar time)

| Risk Class \ Priority | Emergency | Urgent | Normal |
|---|---|---|---|
| Class III | **4 h** | 24 h | 120 h |
| Class II | 8 h | 48 h | 72 h |
| Class I | 24 h | 72 h | 480 h |

Nguồn: `services.imm09.get_sla_target()`. Default fallback: 480 h.

---

## 8. Dependencies

| Module / Component | Tương tác | Hướng |
|---|---|---|
| IMM-00 Foundation | `transition_asset_status()`, `create_lifecycle_event()`, AC Asset, Asset Lifecycle Event | inbound |
| IMM-08 PM | `source_pm_wo` — auto tạo CM WO khi PM Halted (Major Failure) | inbound |
| IMM-12 Incident Report | `incident_report` — nguồn tạo CM WO | inbound |
| IMM-11 Calibration | Trigger post-repair Calibration nếu Device Model `requires_calibration` | outbound |
| IMM-12 CAPA | `is_repeat_failure = 1` → khuyến nghị `create_capa()` | outbound |
| IMM-13/14 EOL | Cannot Repair → Asset Out of Service → mở EOL | outbound |
| ERPNext Stock | `Stock Entry` — chứng từ xuất vật tư (BR-09-02) | inbound |
| Frappe File / Comment / Version | Attachments, audit native | inbound |

---

## 9. Trạng thái triển khai

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| DocType `Asset Repair` + 2 child + FCR | LIVE | `assetcore/assetcore/doctype/asset_repair/*.json` |
| Service layer `services/imm09.py` | LIVE | 13 functions |
| API layer `api/imm09.py` | LIVE | 12 endpoints whitelist |
| Frontend Vue 3 | LIVE | 7 views (CMDashboard, CMList, CMDetail, CMCreate, CMDiagnose, CMParts, CMChecklist, CMMttr) + `stores/imm09.ts` |
| Scheduler hooks | LIVE | hourly `check_repair_sla_breach`, daily `check_repair_overdue`, monthly `update_asset_mttr_avg` |
| Workflow JSON | Optional | State machine enforce qua controller — chưa cần Frappe Workflow record |
| Test suite | DRAFT | UAT scripts đầy đủ; pytest đang viết |
| QMS mapping | LIVE | WHO HTM 2025 + ISO 13485 + NĐ98 (xem Functional Specs §10) |

---

*End of Module Overview v2.0.0 — IMM-09 Corrective Maintenance.*
