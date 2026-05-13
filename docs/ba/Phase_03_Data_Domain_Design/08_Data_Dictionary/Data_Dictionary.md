> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DATA DICTIONARY — ASSETCORE (Wave 1 Selected)

**Phiên bản:** 1.0
**Owner:** BA Lead + Data Architect

---

## Cấu trúc
Mỗi field có:
- **Field**, **Label**, **DocType**, **Type**, **Length/Format**, **Mandatory**, **Default**, **Business Definition**, **Allowed Values / Pattern**, **Source / Computation**.

---

## 1. AC Medical Asset (selected)

| Field | Label | Type | Mandatory | Default | Business Definition | Allowed |
|-------|-------|------|-----------|---------|---------------------|---------|
| asset_code | Mã tài sản | Data 64 | Y | autogen | Mã định danh duy nhất của thiết bị trong toàn BV | `^[A-Z0-9]{2,4}-[A-Z]{2,5}-[A-Z0-9]{2,5}-\d{4,8}$` |
| device_model | Model | Link | Y | – | Catalog model thiết bị | – |
| serial_no | Serial NSX | Data 128 | Y | – | Số serial do nhà sản xuất phát hành | – |
| facility | Cơ sở | Link | Y | – | Cơ sở bệnh viện | – |
| department | Khoa | Link | Y | – | Khoa sở hữu/triển khai | – |
| custodian_user | Người trông giữ | Link User | Y | – | Người chịu trách nhiệm vận hành | – |
| criticality | Tính trọng yếu | Select | Y | C | Mức độ quan trọng cho dịch vụ y tế | A/B/C/D |
| risk_class | Phân loại rủi ro | Select | Y | – | Theo NĐ 98/2021 | 1/2a/2b/3 |
| commission_date | Ngày commission | Date | – | – | Ngày commission xong | – |
| state | Trạng thái HTM | Select | Y | draft | State machine | draft/installed/commissioned/released_for_use/stand_down/retired/disposed |
| erpnext_asset | ERPNext Asset | Link | – | – | Đồng bộ kế toán | – |
| qr_url | QR | Data | – | autogen | URL deep-link để scan | `^https?://` |
| rfid_epc | RFID EPC | Data 24 | – | – | EPC code RFID | hex |
| pm_compliance | PM tuân thủ | Check | – | 1 | Tự tính theo BR-027 | – |
| imported_from_legacy | Migration | Check | – | 0 | – | – |

## 2. AC Work Order (selected)

| Field | Label | Type | Mandatory | Default | Business Definition |
|-------|-------|------|-----------|---------|----------------------|
| wo_type | Loại WO | Select | Y | – | PM/CM/Calibration/Inspection/Installation/Recall/Retirement |
| medical_asset | Thiết bị | Link | Y | – | – |
| priority | Độ ưu tiên | Select | Y | Medium | Low/Medium/High/Critical |
| severity | Mức nghiêm trọng (CM) | Select | – | – | 1..5 (CM) |
| sla_due_at | SLA hạn | Datetime | Y | computed | Tính từ rule SLA |
| sla_breached | Vi phạm SLA | Check | – | 0 | Auto |
| actual_start_at / actual_end_at | Thời gian thực tế | Datetime | – | – | – |
| downtime_minutes | Downtime | Int | – | 0 | Auto = repaired-failure_reported - paused |
| close_code | Mã đóng | Select | Y khi close | – | Repaired/Replaced/Beyond Repair/No Fault Found/Pending Parts/Vendor Action |
| validation_result | Kết quả validate | Select | Y khi validate | – | Pass/Fail/N/A |
| state | Trạng thái | Workflow | Y | draft | xem State Machine |

## 3. AC Lifecycle Event (selected)

| Field | Label | Type | Mandatory | Description |
|-------|-------|------|-----------|-------------|
| event_type | Loại event | Link AC Event Type | Y | – |
| occurred_at | Thời điểm | Datetime | Y | – |
| actor_user | Người thực hiện | Link User | Y | – |
| actor_role | Vai trò actor | Data | Y | – |
| subject_doctype | DocType chủ thể | Data | Y | – |
| subject_name | Tên chủ thể | Dynamic Link | Y | – |
| source_doctype / source_name | Nguồn phát | – | Y | – |
| payload | Payload JSON | JSON | Y | Schema theo Event Type |
| audit_class | Class audit | Select | Y | info/critical/QMS-critical |
| immutable | Immutable | Check | Y, default 1 | Không cho update |
| correlation_id | ID truy vết | Data | – | – |

## 4. AC Document Record (selected)

| Field | Label | Type | M | Description |
|-------|-------|------|---|-------------|
| document_type | Loại tài liệu | Select | Y | LEGAL/TECH/IQOQPQ/CALCERT/MAINT/TRAINING/COMP/CAPA/MOVE/DECOM/CONTRACT/VENDOR |
| subtype | Phân loại con | Data | Y | License/CE/FDA/Manual/SOP… |
| document_no | Số hiệu | Data | Y | unique theo type |
| linked_asset (table) | Asset | Link | – | nhiều asset |
| issuing_authority | Cơ quan phát hành | Data | Y (LEGAL/CALCERT) | – |
| effective_date / expiry_date | Hiệu lực | Date | Y | – |
| version | Phiên bản | Data | Y | semver |
| supersedes / superseded_by | Quan hệ phiên bản | Link Document Record | – | – |
| confidentiality | Bảo mật | Select | Y | Public/Internal/Restricted |
| state | Trạng thái | Workflow | Y | – |
| imported_from_legacy / legacy_ref | Migration | – | – | – |

## 5. AC CAPA (selected)

| Field | Label | Type | M |
|-------|-------|------|---|
| capa_no | Mã CAPA | Naming | Y |
| capa_type | Loại | Select Corrective/Preventive/Both | Y |
| source_nc | Nguồn NC (table) | Link | Y (≥1) |
| owner_user | Owner | Link User | Y |
| approver_user | Approver | Link User | Y |
| root_cause | Nguyên nhân | Long Text | Y |
| rca_method | Phương pháp | Select | – |
| effectiveness_check_plan | Kế hoạch check | Table | Y |
| effectiveness_result | Kết quả | Select | – |
| state | Trạng thái | Workflow | Y |

## 6. AC Compliance Case (selected)

| Field | Label | Type | M |
|-------|-------|------|---|
| case_no | Mã case | Naming | Y |
| case_type | Loại | Select | Y |
| linked_asset / linked_doc / linked_wo / linked_capa | – | Link | – |
| severity | Mức nghiêm trọng | Select | Y |
| regulatory_authority | Cơ quan quản lý | Select | – |
| disclosure_required | Cần công bố | Check | – |
| disclosure_due_at | Hạn công bố | Datetime | – |
| state | Trạng thái | Workflow | Y |

## 7. AC Metric Definition (selected)

| Field | Label | Type | M |
|-------|-------|------|---|
| metric_id | Mã KPI | Data unique | Y |
| metric_name | Tên | Data | Y |
| business_owner | Owner nghiệp vụ | Link User | Y |
| data_owner | Owner dữ liệu | Link User | Y |
| formula | Công thức | Code/JSON | Y |
| source_doctype | Bảng nguồn | Data | Y |
| source_filter | Filter | JSON | – |
| data_lineage | Lineage | Long Text | Y |
| period_grain | Chu kỳ | Select | Y |
| target_value / threshold_warning / threshold_critical | Ngưỡng | Float | – |
| state | Trạng thái | Select | Y |

## 8. Quy tắc đặt tên field chung

- Boolean: `is_*` / `has_*` / `requires_*`.
- Date: `*_date`.
- Datetime: `*_at`.
- Money: ép currency Frappe + UOM.
- Computed field: prefix `auto_` (vd `auto_downtime_minutes`).
- Migration field: `imported_from_legacy`, `legacy_ref`.

## 9. Field encryption

- `signature_payload`, `private_token`, `api_key` → Frappe encrypted text.
- File QMS-critical: lưu trên bucket immutable; metadata trên DB không chứa nội dung nhạy cảm.

## 10. Tiêu chí nghiệm thu
- 100% field Wave 1 có entry trong Data Dictionary.
- Mỗi field có ít nhất Business Definition + Source.
- Naming convention compliance được linter kiểm tra.
