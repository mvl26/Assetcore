> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# BUSINESS RULES CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead
**Áp dụng:** Cross-module Wave 1 + 2

---

## Quy ước
- Mỗi rule có `BR-XXX`, mô tả, scope (DocType/Process), enforcement (validation/workflow/server script/report), độ ưu tiên.
- Enforcement: `V` (Validate field) | `W` (Workflow transition) | `S` (Server Script) | `R` (Report/exception) | `I` (Integration check).

---

## A. Asset Registry & Định danh

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-001 | Mỗi `AC Medical Asset` phải có `asset_code` duy nhất theo Naming Convention `<facility>-<category>-<serial>` | AC Medical Asset | V + S | 1 |
| BR-002 | Một thiết bị chỉ được liên kết với một `AC Device Model` | AC Medical Asset | V | 1 |
| BR-003 | Nếu `criticality ≥ A` thì bắt buộc có Calibration Plan + PM Plan | AC Medical Asset | V (cảnh báo) + R | 1 |
| BR-004 | Không cho phép xóa `AC Medical Asset` đã ở state ≥ commissioned | AC Medical Asset | S | 1 |
| BR-005 | Khi `release_for_use`, bắt buộc có ít nhất: license effective + IQ/OQ/PQ approved + training plan đã có | AC Medical Asset | W | 1 |
| BR-006 | `location` của asset phải nằm trong `facility/department/room` đã được định nghĩa | AC Medical Asset | V | 1 |
| BR-007 | `custodian` phải có user role `AC Department Head` hoặc `AC Asset Manager` | AC Medical Asset | V | 1 |
| BR-008 | Asset Code đã phát hành không được phép thay đổi (chỉ cho phép amend với e-signature + lý do) | AC Medical Asset | S + W | 1 |

## B. Hồ sơ pháp lý (Document)

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-011 | Mọi license/certification phải có `effective_date`, `expiry_date`, `issuing_authority` | AC Document Record (License) | V | 1 |
| BR-012 | License hết hạn (expiry_date < today) → state tự chuyển sang `expired` qua daily cron | AC Document Record | S (cron) | 1 |
| BR-013 | Asset có license `expired` không cho phép `release_for_use` | AC Medical Asset | W | 1 |
| BR-014 | Asset có license `expired` đã `released_for_use` → cảnh báo Compliance Officer + tạo Compliance Case bậc warning | AC Medical Asset | S | 1.5 |
| BR-015 | Document QMS Tier 1/2 yêu cầu approver tối thiểu 2 cấp (Trưởng đơn vị + Trưởng QLCL) | AC QMS Artifact | W | 1 |

## C. PM (Bảo trì định kỳ)

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-021 | PM Plan bắt buộc gắn với 1 asset cụ thể HOẶC 1 nhóm asset bằng filter | AC PM Plan | V | 1 |
| BR-022 | Mỗi PM Plan có `frequency` tối thiểu 1 lần/năm (trừ asset criticality C có thể custom) | AC PM Plan | V | 1 |
| BR-023 | Cron sinh WO PM `lead_time` ngày trước due (default 14, configurable per Plan) | AC PM Plan → AC Work Order | S (cron) | 1 |
| BR-024 | WO PM phải có ít nhất 1 task trong checklist task | AC Work Order | V | 1 |
| BR-025 | WO PM closed → cập nhật `last_pm_date` và `next_pm_due` trên asset + LE pm_completed | AC Work Order | S + W | 1 |
| BR-026 | Vi phạm SLA PM → tự sinh Compliance Case loại "PM overdue" (sau X ngày) | AC PM Plan | S | 1.5 |
| BR-027 | Asset chưa hoàn thành PM trong chu kỳ N+1 → flag `pm_compliance=false` (dùng cho dashboard) | AC Medical Asset | S | 1 |

## D. CM (Bảo trì khắc phục)

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-031 | Failure Report bắt buộc trường: asset, severity, location, problem_description, reporter | AC Failure Report | V | 1 |
| BR-032 | Severity = Critical (đe dọa bệnh nhân) → tự ưu tiên + escalate Trưởng VTTBYT trong 30 phút | AC Failure Report | S | 1 |
| BR-033 | WO CM phải nhập `root_cause` trước khi đóng nếu severity ≥ High | AC Work Order | W | 1 |
| BR-034 | Phụ tùng tiêu thụ trong WO CM phải có Stock Entry tương ứng | AC Work Order | I | 1 |
| BR-035 | WO CM lặp lại trên cùng asset ≥ 3 lần trong 90 ngày → tự sinh CAPA case | AC Work Order | S | 1.5 |
| BR-036 | Downtime tính = `repaired_at` − `failure_reported_at` − thời gian "paused" hợp lệ | AC Work Order | S | 1 |
| BR-037 | WO CM trên asset đang stand-down → cảnh báo conflict | AC Work Order | V | 2 |

## E. Hiệu chuẩn

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-041 | Calibration Plan bắt buộc có `frequency`, `standard_reference`, `acceptance_criteria` | AC Calibration Plan | V | 1 |
| BR-042 | Cal Record `Fail` → tự stand-down asset + CAPA | AC Calibration Record | W + S | 1 |
| BR-043 | Calibration Certificate bắt buộc upload PDF trước khi đóng WO Cal | AC Calibration Record | V | 1 |
| BR-044 | `next_calibration_due` tự cập nhật theo frequency sau mỗi Cal pass | AC Medical Asset | S | 1 |

## F. QMS / CAPA / Compliance

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-051 | NC nghiêm trọng (cấp 1) → bắt buộc mở CAPA trong 24h | AC Nonconformity | W + S | 1.5 |
| BR-052 | CAPA action overdue ≥ 7 ngày → escalate QMS Lead | AC CAPA | S | 1.5 |
| BR-053 | CAPA không đạt effectiveness → reopen + extend | AC CAPA | W | 1.5 |
| BR-054 | Document QMS chỉ effective khi đủ chu trình draft → review → approve | AC QMS Artifact | W | 1 |
| BR-055 | Approval QMS Tier 1 phải có e-signature 2 cấp | AC QMS Artifact | W | 1 |
| BR-056 | Recall workflow phải có timeline thông báo Bộ Y tế trong 48h kể từ khi confirmed | AC Compliance Case (Recall) | S | 1.5 |
| BR-057 | Mỗi CAPA phải link tới ≥ 1 source (NC, audit finding, complaint, recall) | AC CAPA | V | 1.5 |

## G. Phụ tùng / Stock

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-061 | Phụ tùng critical (BOM critical) → tồn kho min phải >= reorder level | AC Spare Part / Item | S + R | 2 |
| BR-062 | Stock Entry consumption từ WO không được phép manual input số âm | Stock Entry | V | 1 |
| BR-063 | Cấp phát phụ tùng phải có WO link | Stock Entry | V | 1 |

## H. Movement / Stand-down / Decommission

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-071 | Movement giữa khoa cần phê duyệt Trưởng khoa cũ + Trưởng khoa mới + Trưởng VTTBYT | AC Asset Movement | W | 2 |
| BR-072 | Stand-down kéo dài > 90 ngày → trigger đề xuất Decommission | AC Stand-Down Record | S | 2 |
| BR-073 | Decommission yêu cầu evidence: lý do, đánh giá kỹ thuật, đồng ý KTTC + Pháp chế + QMS | AC Decommission Record | W | 2 |
| BR-074 | Disposal phương thức "donation" → bắt buộc thêm hồ sơ donation theo WHO guidelines | AC Disposal Record | V | 2 |

## I. Permissions / Audit

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-081 | Người tạo WO không được tự đóng WO ở môi trường QMS-critical (cần validator khác) | AC Work Order | W | 1 |
| BR-082 | External vendor chỉ thấy WO được giao cho mình + asset liên quan | AC Work Order | V (User Permission) | 1 |
| BR-083 | Audit log không được phép xóa, kể cả System Admin | AC Lifecycle Event | S | 1 |
| BR-084 | Mọi chỉnh sửa hồ sơ pháp lý sau approve phải qua Amendment + e-signature | AC Document Record | W | 1 |

## J. Dữ liệu & Migration

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-091 | Migration batch chỉ được "import" qua tool chính thức, không qua DB manual | Migration | I + S | 1 |
| BR-092 | Mọi record migration có flag `imported_from_legacy` + `legacy_ref` | Mọi DocType lớn | V | 1 |
| BR-093 | Field bắt buộc thiếu trong legacy → đẩy vào "Data Quality Issue" để xử lý sau, không block | Migration | S | 1 |

## K. Báo cáo / KPI

| ID | Rule | Scope | Enforce | Wave |
|----|------|-------|---------|------|
| BR-101 | Mỗi KPI/KRI có owner business + owner data, công thức rõ, lineage tới record nguồn | AC Metric Definition | V | 1 |
| BR-102 | Snapshot KPI hàng tháng được lưu vào `AC Dashboard Snapshot` để truy lịch sử | AC Dashboard Snapshot | S | 1 |
| BR-103 | KPI trên dashboard mọi role phải có nút drill-down về record nguồn | UI | UX | 1 |

## Tổng kết
- 80+ business rules cốt lõi cho Wave 1.
- Phase 04 sẽ chuyển các rule này thành workflow + validation cụ thể.
- Phase 08 sẽ kéo các rule thành test case.
