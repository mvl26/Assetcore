> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# MIGRATION TEMPLATE & STRATEGY — ASSETCORE

**Phiên bản:** 1.0
**Owner:** Migration Lead + Data Architect

---

## 1. Mục tiêu
- Đưa dữ liệu legacy (Excel, giấy số hóa, CMMS cũ) vào AssetCore với chất lượng đủ để vận hành.
- Mỗi batch phải có pre-validate, dry-run, audit log, rollback.

## 2. Migration order (lock)

```
1. AC Manufacturer
2. AC Location (Facility/Building/Department/Room)
3. Item ERPNext (cập nhật flag is_medical_device + custom field)
4. AC Device Model
5. Supplier ERPNext + AC Service Provider
6. AC Contract (cơ bản)
7. AC Medical Asset (KHỐI LỚN NHẤT)
8. AC Asset Identifier
9. AC Custodian Assignment (current)
10. AC Document Record (LEGAL, IQOQPQ, MANUAL, CALCERT)
11. AC PM Plan
12. AC Calibration Plan
13. (Optional) Lịch sử PM/CM 24 tháng → bulk insert AC Work Order historical
14. (Optional) Lịch sử Calibration Record
```

## 3. Excel Template chuẩn (mỗi entity 1 sheet)

### 3.1 Sheet: `manufacturer.csv`
Columns:
```
name,country,contact_email,contact_phone,parent_group,regulatory_certifications
```

### 3.2 Sheet: `location.csv`
```
location_type(Facility|Building|Department|Room),code,name1,parent_code,is_active
```

### 3.3 Sheet: `device_model.csv`
```
model_code,name1,manufacturer_code,item_code(ERPNext),risk_class,default_pm_frequency,default_calibration_frequency,operating_manual_doc_no,service_manual_doc_no,is_active
```

### 3.4 Sheet: `medical_asset.csv` (chính)
```
asset_code,device_model_code,serial_no,manufacturer_serial,facility_code,building_code,department_code,room_code,custodian_user_email,owner_department_code,criticality,risk_class,commission_date,warranty_expiry,erpnext_asset_name,state(default=installed|released_for_use),qr_url,rfid_epc,legacy_ref
```

### 3.5 Sheet: `asset_identifier.csv`
```
asset_code,identifier_type(QR|RFID|Asset Tag|Barcode|Vendor Serial),identifier_value,issued_at,valid_until,state(default=Active)
```

### 3.6 Sheet: `document_record.csv`
```
asset_code,document_type(LEGAL|IQOQPQ|CALCERT|MANUAL|CONTRACT...),subtype,document_no,issuing_authority,effective_date,expiry_date,version,language,attachment_path(relative),confidentiality(default=Internal),original_lost(default=0),legacy_ref
```

### 3.7 Sheet: `pm_plan.csv`
```
plan_code,asset_code,frequency,lead_time_days,tasks_template_code,validator_required,vendor_service_provider_code,sla_minutes,state
```

### 3.8 Sheet: `calibration_plan.csv`
```
plan_code,asset_code,frequency,standard_reference,acceptance_criteria,lab_or_vendor_code,validator_required,state
```

### 3.9 Sheet: `wo_history.csv` (optional — historical 24 tháng)
```
wo_type(PM|CM|Cal|Inspection|Installation),asset_code,planned_start_at,planned_end_at,actual_start_at,actual_end_at,assignee_email,executed_by_vendor(0/1),vendor_email,downtime_minutes,close_code,validation_result,root_cause,action_taken,cost_labor,cost_parts,attachments_path,legacy_ref
```

### 3.10 Sheet: `calibration_history.csv`
```
asset_code,performed_by_email,performed_at,result(Pass|Fail),measurements_json,certificate_path,next_due_at,legacy_ref
```

## 4. Pre-validate (chạy trước khi import)

| Check | Output |
|-------|--------|
| Schema columns | OK / Missing column list |
| Type coercion (date, int, currency) | List rows fail |
| Uniqueness keys | List duplicates |
| Referential integrity (FK) | List missing parents |
| Allowed values | List invalid |
| Cross-sheet consistency | List inconsistencies |
| Naming pattern (asset_code regex…) | List violations |

Output: `migration_validation_report.xlsx` với 3 sheet (Errors, Warnings, Stats).

## 5. Dry-run (chạy trên DEV)
- Import vào DB DEV.
- Chạy DQ rule audit.
- Sinh report số lượng + sample.
- Test các scenario: tạo MA → release_for_use giả lập.
- Rollback DEV trước Production import.

## 6. Production Import

### 6.1 Chuẩn bị
- Lấy snapshot PROD (backup full).
- Khóa user nhập liệu trong cửa sổ migration.
- Bật `migration_mode=true` (cờ trong AC Settings) → bypass một số trigger không cần thiết để tăng tốc.

### 6.2 Quy trình
1. Migration Lead khởi chạy import qua tool chính thức.
2. Tool chia batch (mỗi batch ≤ 1.000 record) — gọi API `assetcore.migration.import_batch`.
3. Mỗi batch:
   - Tạo `AC Migration Batch` record (master).
   - Import từng row → log success/fail vào `AC Migration Row`.
   - Sinh `LE-63 data_migration_batch_loaded`.
4. Sau khi import xong, tắt `migration_mode`, chạy DQ audit toàn hệ thống.
5. Báo cáo migration (counts, failures) + plan xử lý failures.

### 6.3 Rollback strategy
- Mỗi batch có thể rollback (xóa record có `imported_from_legacy=1` thuộc batch).
- Lifecycle Event KHÔNG rollback (giữ audit trail).

## 7. Attachment migration
- File scan/PDF được lưu trên file storage tạm theo path tham chiếu trong CSV.
- Tool migration upload qua Frappe File API + link vào Document Record.
- Hash file → đối chiếu duplicate; nếu trùng, link cùng file.

## 8. Failure handling
- Row fail → entry trong `AC Data Quality Issue` với rule_id (DQ-MIG-XX).
- Owner: Migration Lead + Data Steward.
- Cải thiện theo batch follow-up.

## 9. Migration sign-off

| Tiêu chí | Ngưỡng |
|----------|--------|
| Master data import (Manufacturer/Location/Device Model/Supplier) | 100% |
| Item update (`is_medical_device`) | 100% |
| Medical Asset import | ≥ 95% (Wave 1 in scope) |
| Asset Identifier mỗi MA | ≥ 1 |
| Document License (LEGAL) | ≥ 90% MA có license effective |
| Document Manual | ≥ 80% Device Model có manual |
| PM Plan | ≥ 70% MA criticality A/B có plan |
| Calibration Plan | ≥ 70% MA cần Cal có plan |
| Historical WO 24m | best effort, chỉ migrate khi BV cung cấp đầy đủ |

## 10. Tooling
- Migration tool dạng custom Python script + Frappe API.
- Có thể dùng Frappe Data Import tool cho master nhỏ.
- Lớn → custom job background.

## 11. Tiêu chí nghiệm thu Migration
- Pre-validate report sạch (≤ 5% warning, 0 error trên dữ liệu in-scope).
- Dry-run DEV pass.
- Production import đạt ngưỡng sign-off §9.
- Mọi failure có owner xử lý.
- Migration Batch + Row log hoàn chỉnh.
