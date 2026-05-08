> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# UNIFIED WORK ORDER ENGINE — SPEC

**Phiên bản:** 1.0
**Owner:** SA Lead + BA Lead
**Wave:** 1

---

## 1. Mục tiêu
Một engine WO duy nhất cho:
- PM (Preventive Maintenance)
- CM (Corrective Maintenance)
- Calibration
- Inspection
- Installation / Commissioning
- Recall (Wave 1.5)
- Retirement (Wave 2)

Lý do: cấu trúc dữ liệu, thao tác, audit, KPI giống nhau ~80% — tách nhỏ làm tăng phức tạp.

## 2. DocType chính

### 2.1 AC Work Order
**Naming:** `WO-.YYYY.-.######`

**Trường chính:**
| Field | Type | Bắt buộc | Mô tả |
|-------|------|---------|-------|
| wo_type | Select PM / CM / Calibration / Inspection / Installation / Recall / Retirement | Có | – |
| medical_asset | Link AC Medical Asset | Có (trừ Inspection chung) | – |
| pm_plan / calibration_plan / failure_report / installation_request / recall_case / decommission_request | Link tương ứng | Tùy theo type | – |
| priority | Select Low / Medium / High / Critical | Có | – |
| severity | Select 1..5 (cho CM) | Tùy | – |
| planned_start_at / planned_end_at | Datetime | Có | – |
| actual_start_at / actual_end_at | Datetime | – | – |
| sla_due_at | Datetime | Có | – |
| sla_breached | Check | – | – |
| assigned_team | Link AC Team | Có | – |
| assigned_user | Link User | Có | – |
| executed_by_vendor | Check | – | – |
| vendor_service_user | Link User (External) | Tùy | – |
| location | Link AC Location | Có | – |
| downtime_minutes | Int | – | – |
| pause_log | Table (paused_from, paused_to, reason) | – | – |
| tasks | Table AC Work Order Task | Có | Checklist + result |
| spare_items | Table AC Work Order Spare Item | – | – |
| cost_labor | Currency | – | – |
| cost_parts | Currency | – | – |
| root_cause | Long Text | Tùy theo type | – |
| action_taken | Long Text | – | – |
| close_code | Select Repaired / Beyond Repair / Replaced / Pending Parts / Vendor Action / No Fault Found | Tùy | – |
| validation_result | Select Pass / Fail / N/A | – | – |
| linked_capa | Link AC CAPA | Tùy | – |
| evidence_refs | Table file refs | – | – |
| state | Workflow state | Có | – |

### 2.2 AC Work Order Task (child)
| Field | Mô tả |
|-------|-------|
| task_no, description, expected_value, actual_value, pass_fail, evidence, executed_by, executed_at |

### 2.3 AC Work Order Spare Item (child)
| Field | Mô tả |
|-------|-------|
| item, qty, uom, stock_entry, unit_cost |

### 2.4 AC Failure Report
- Trigger CM WO.
- Field: asset, severity, location, description, reporter_user, reported_at, attachments.

### 2.5 AC PM Plan
- Field: asset (hoặc filter), frequency, lead_time_days, tasks_template, validator_required, vendor_service_provider.

### 2.6 AC Calibration Plan
- Field: asset, frequency, standard_reference, acceptance_criteria, lab_or_vendor, validator_required.

## 3. State Machine WO (chung cho mọi type)

```
draft ─► planned ─► assigned ─► in_progress ─► completed ─► validated ─► closed
            │           │            │             │
            │           │            │             ▼
            │           │            │         on_hold/paused
            │           │            ▼
            │           ▼        cancelled
            ▼        cancelled
        cancelled
```

State `validated` chỉ áp dụng khi `validator_required=true` (mặc định cho QMS-critical).

## 4. SLA management
- Mỗi WO có `sla_due_at` tính từ rule (xem `09_SLA_Catalog`).
- Background worker chạy mỗi phút check breach → set `sla_breached=true` → publish `LE-49 wo_breach_sla`.
- Pause window không tính vào SLA (cấu hình per Plan).

## 5. Spare consumption flow
1. Trong WO, nhập spare cần dùng.
2. Submit "Issue Spare" → tự sinh ERPNext Stock Entry (Material Issue) với target = WO project / cost center.
3. Stock Entry submitted → cập nhật `cost_parts`.
4. Nếu spare không đủ → trigger Reorder + WO state `paused_waiting_parts`.

## 6. Generators
- **PM Scheduler** (cron daily): scan PM Plan → tạo WO PM trong cửa sổ `lead_time`.
- **Calibration Scheduler** (cron daily): tương tự.
- **Failure Report Hook**: on submit → create WO CM + assign theo rule.
- **Recall Workflow** (Wave 1.5): on Compliance Case Recall approved → bulk create WO type=Recall cho mỗi asset.

## 7. Assignment Rule
- Theo `AC Assignment Rule` (Frappe Auto Assignment).
- Match theo: wo_type, criticality, location, hợp đồng vendor.
- Round-robin trong team in-house.
- Vendor SE được assign theo contract.

## 8. Validation & Close
- WO QMS-critical (PM/Cal/Install) yêu cầu validate trước close.
- Validator phải khác executor (segregation of duty).
- Validate có e-signature.

## 9. KPI emit (Wave 1)
- WO created
- WO completed on-time vs late
- Avg downtime
- Avg time-to-repair
- Cost (labor + parts)
- WO breach SLA count
- Recurring failures (≥ 3 lần/90 ngày)

## 10. Public API
- `assetcore.work_order.create(wo_type, asset, ...)`
- `assetcore.work_order.assign(wo, assignee)`
- `assetcore.work_order.start(wo)`
- `assetcore.work_order.pause(wo, reason)`
- `assetcore.work_order.complete(wo, result)`
- `assetcore.work_order.validate(wo, decision, signature)`
- `assetcore.work_order.close(wo)`

## 11. Tiêu chí nghiệm thu Wave 1
- 6 wo_type hoạt động (PM, CM, Cal, Inspection, Installation, Recall).
- SLA breach detect chính xác.
- Spare consumption đồng bộ ERPNext Stock 100%.
- Validation segregation of duty enforced.
- 100% WO sinh đầy đủ Lifecycle Event tương ứng.
- 95th percentile thời gian xử lý create WO < 1s.
