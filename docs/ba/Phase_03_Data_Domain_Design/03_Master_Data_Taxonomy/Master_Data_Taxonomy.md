> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# MASTER DATA TAXONOMY — ASSETCORE

**Phiên bản:** 1.0
**Owner:** BA Lead + Data Architect

---

## 1. Mục đích
Phân loại + định nghĩa các master data + danh mục mã chuẩn — là nền tảng cho ERD, mapping, migration.

## 2. Master Data List

### 2.1 Item / Device Item Master (ERPNext Item)
- Custom field: `is_medical_device` (Check), `risk_class` (Select), `criticality` (Select).
- Item Group: "Medical Device" + sub-group theo loại (Imaging, Lab, Life Support, Monitoring, Surgical, Others).
- Liên kết với `AC Device Model`.

### 2.2 AC Device Model
- Catalog model.
- Fields chính: model_code, manufacturer, item_template, default PM/Cal frequency, manuals, BOM template.
- Quản lý bởi VTTBYT.

### 2.3 AC Manufacturer
- Hãng sản xuất.
- Fields: name, country, contact, regulatory_certifications, parent_group.

### 2.4 Supplier (ERPNext) + AC Service Provider (custom)
- ERPNext Supplier cho mua sắm + cung ứng phụ tùng.
- AC Service Provider là entity riêng cho dịch vụ bảo trì/hiệu chuẩn (vendor có thể là 1 trong 2 hoặc cả 2).
- Custom field trên Supplier: `is_service_provider`.

### 2.5 AC Contract
- Loại: Mua, Bảo trì, Hiệu chuẩn, Bảo hiểm, Donation.
- Fields: contract_no, vendor, scope_assets, scope_models, start_date, end_date, value, sla, deliverables.

### 2.6 AC Location Hierarchy
- 4 cấp: Facility → Building → Department → Room.
- Frappe Tree DocType.
- Code chuẩn: facility-code (BV01), building-code (B1), department-code (CDH), room-code (P101).

### 2.7 AC Spare Part Master (Wave 2 đầy đủ)
- Liên kết Item ERPNext.
- Tagging "spare-critical".
- BOM mapping per Device Model.

### 2.8 AC Risk Class / Criticality Reference
| Risk Class | Mô tả (theo NĐ 98/2021) |
|-----------|--------------------------|
| 1 | Mức rủi ro thấp |
| 2a | Rủi ro thấp-trung |
| 2b | Trung bình-cao |
| 3 | Cao |

| Criticality | Mô tả (HTM internal) |
|-------------|----------------------|
| A | Life-critical |
| B | High |
| C | Medium |
| D | Low |

### 2.9 Document Type / Subtype
- Theo `Phase_01/11_Evidence_Document_Inventory`.

### 2.10 AC Event Type
- Theo `Phase_01/06_Event_List`.

### 2.11 AC Role Master
- Theo `Phase_00/07_Glossary_Naming_Convention §2.5`.

### 2.12 AC Department / Team
- Department: tận dụng Frappe Department.
- Team: custom (có thể trùng Department) cho assignment WO.

### 2.13 AC User Role Mapping
- Map user thực ↔ Role AssetCore (xem Phase 04).

### 2.14 Naming Series Master
- Ngân hàng naming series (Phase_00/07 §2.3).

### 2.15 AC Holiday Calendar
- Cho SLA giờ hành chính.

### 2.16 Currency / UoM
- ERPNext core.
- Mặc định VND.

## 3. Code Taxonomy

### 3.1 Asset Code
- Format: `BV01-IMG-CT-000123` (facility - device class - subclass - serial).
- Class theo Item Group.

### 3.2 Document Number
- LEGAL: `LIC-<vendor>-<yyyy>-<seq>`.
- CALCERT: `CAL-CERT-<lab>-<yyyy>-<seq>`.
- IQOQPQ: `IQOQPQ-<asset_code>-<yyyy>`.
- QMS Artifact: `QMS-<TIER>-<dept>-<yyyy>-<seq>` (vd `QMS-PR-VTTBYT-2026-0007`).

### 3.3 Work Order
- Series `WO-.YYYY.-.######`.

### 3.4 Lifecycle Event
- Series `LCE-.YYYY.-.########`.

## 4. Quy tắc bảo trì master data

| Master | Owner cập nhật | Tần suất |
|--------|---------------|---------|
| Item Group / Item | VTTBYT + Mua hàng | Khi có model mới |
| AC Device Model | VTTBYT + Kỹ sư BME | Khi onboard model mới |
| AC Manufacturer | VTTBYT | Khi xuất hiện |
| Supplier / Service Provider | Mua hàng | Theo nhu cầu |
| AC Location | Hành chính + IT | Khi tổ chức thay đổi |
| AC Contract | Mua hàng + Pháp chế | Khi ký mới |
| AC Spare Part | Kho + Kỹ sư BME | Khi onboard model + theo BOM |
| Risk/Criticality | QMS | Theo hướng dẫn pháp lý |
| Naming Series | IT (sau ARB approval) | Hiếm |
| AC Event Type | SA + QMS | Per wave release |

## 5. Quan hệ giữa master data

```
Item Group ─► Item ─► AC Device Model ─► AC Medical Asset
AC Manufacturer ─► AC Device Model
Supplier (ERPNext) ─► AC Contract ─► AC Medical Asset (qua scope_assets)
AC Service Provider ─► AC Contract ─► (PM/Cal vendor)
AC Location ─► AC Medical Asset
Risk/Criticality ─► AC Medical Asset (validate)
AC Spare Part ─► AC Device Model.bom (Wave 2)
```

## 6. Migration order (Wave 1)

1. AC Manufacturer
2. AC Location
3. AC Device Model
4. Supplier + AC Service Provider
5. Item (cập nhật flag `is_medical_device`)
6. AC Medical Asset
7. AC Document Record (LEGAL, IQOQPQ, MANUAL, CALCERT)
8. AC PM Plan (nếu có)
9. AC Calibration Plan (nếu có)
10. Work Order historical (24 tháng) — nếu BV chấp nhận

## 7. Tiêu chí nghiệm thu master taxonomy
- 100% master data có owner cập nhật.
- Không có "Other / Misc" rỗng nghĩa.
- Tất cả code có quy tắc + ví dụ.
- Migration dry-run pass ít nhất 1 lần.
