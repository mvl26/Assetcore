> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# DATA QUALITY RULE CATALOG — ASSETCORE

**Phiên bản:** 1.0
**Owner:** Data Architect + BA Lead
**Áp dụng:** Master + Transactional + Migration

---

## 1. Phân loại rule
- **Uniqueness (UN):** không trùng lặp.
- **Completeness (CP):** không thiếu trường bắt buộc.
- **Consistency (CS):** đồng bộ giữa các record.
- **Validity (VL):** đúng format, allowed value.
- **Referential Integrity (RI):** link tới record tồn tại.
- **Timeliness (TI):** dữ liệu cập nhật đúng hạn.
- **Accuracy (AC):** đối chiếu thực tế.

---

## 2. Master Data

### 2.1 AC Manufacturer
| ID | Rule | Loại | Action khi vi phạm |
|----|------|------|---------------------|
| DQ-MAN-01 | Tên không trùng lặp | UN | Block |
| DQ-MAN-02 | Country phải nằm trong ISO list | VL | Block |

### 2.2 AC Device Model
| ID | Rule | Loại | Action |
|----|------|------|--------|
| DQ-DM-01 | model_code unique | UN | Block |
| DQ-DM-02 | manufacturer link tồn tại | RI | Block |
| DQ-DM-03 | item_template tồn tại + `is_medical_device=1` | RI + CS | Block |
| DQ-DM-04 | risk_class trong {1, 2a, 2b, 3} | VL | Block |
| DQ-DM-05 | Nếu default_calibration_frequency có → operating_manual phải có | CS | Warning |

### 2.3 AC Location
| ID | Rule | Loại |
|----|------|------|
| DQ-LOC-01 | Code unique trong cùng cấp | UN |
| DQ-LOC-02 | parent_location đúng cấp (Building → Department không cho phép skip cấp) | VL |
| DQ-LOC-03 | Không loop vòng | VL |

### 2.4 AC Spare Part
| ID | Rule |
|----|------|
| DQ-SP-01 | Item ERPNext tồn tại |
| DQ-SP-02 | Phụ tùng critical phải có reorder level |

## 3. Transactional Data

### 3.1 AC Medical Asset
| ID | Rule | Loại | Action |
|----|------|------|--------|
| DQ-MA-01 | asset_code match regex Naming | VL | Block |
| DQ-MA-02 | asset_code unique | UN | Block |
| DQ-MA-03 | Mỗi MA có ≥ 1 Asset Identifier active | CP | Block sau commission |
| DQ-MA-04 | facility/department tồn tại | RI | Block |
| DQ-MA-05 | custodian_user role hợp lệ | RI + VL | Block |
| DQ-MA-06 | criticality A/B → có PM Plan + Cal Plan (sau release_for_use) | CS | Warning + Compliance Case |
| DQ-MA-07 | next_pm_due ≥ today (sau khi PM done) | CS | Warning |
| DQ-MA-08 | erpnext_asset link tồn tại nếu state ≥ released_for_use | RI | Block |
| DQ-MA-09 | warranty_expiry ≥ commission_date | VL | Warning |

### 3.2 AC Document Record
| ID | Rule | Loại |
|----|------|------|
| DQ-DOC-01 | document_no unique theo (type, version) | UN |
| DQ-DOC-02 | effective_date ≤ expiry_date | VL |
| DQ-DOC-03 | LEGAL/CALCERT phải có expiry_date | CP |
| DQ-DOC-04 | Phiên bản mới effective → phiên bản cũ obsolete (consistency) | CS |
| DQ-DOC-05 | linked_asset có tồn tại | RI |

### 3.3 AC Work Order
| ID | Rule | Loại |
|----|------|------|
| DQ-WO-01 | sla_due_at ≥ created_at | VL |
| DQ-WO-02 | actual_end_at ≥ actual_start_at | VL |
| DQ-WO-03 | Tasks có ≥ 1 task per WO | CP |
| DQ-WO-04 | Spare items có Stock Entry tương ứng (nếu có) | CS |
| DQ-WO-05 | Validator ≠ Executor | VL |
| DQ-WO-06 | downtime_minutes không âm | VL |
| DQ-WO-07 | close_code không null khi state=closed | CP |
| DQ-WO-08 | sla_breached only true khi actual_end > sla_due | CS |

### 3.4 AC Calibration Record
| ID | Rule |
|----|------|
| DQ-CAL-01 | result Pass → cert_doc not null |
| DQ-CAL-02 | result Fail → CAPA mở trong 24h |
| DQ-CAL-03 | next_due_at = performed_at + frequency |
| DQ-CAL-04 | measurements có ≥ 1 row |

### 3.5 AC Failure Report
| ID | Rule |
|----|------|
| DQ-FR-01 | Tất cả field bắt buộc not null |
| DQ-FR-02 | severity Critical → linked_wo trong 30 phút |

### 3.6 AC Lifecycle Event
| ID | Rule | Loại |
|----|------|------|
| DQ-LE-01 | payload validate JSON Schema theo Event Type | VL |
| DQ-LE-02 | subject_doctype trong allowed_doctypes | RI |
| DQ-LE-03 | actor_user tồn tại + role match | RI + VL |
| DQ-LE-04 | immutable=1 — không cho update | constraint |
| DQ-LE-05 | occurred_at không xa hiện tại > 24h (chỉ cho phép trong test) | VL |

### 3.7 AC CAPA / Compliance Case
| ID | Rule |
|----|------|
| DQ-CAPA-01 | source_nc ≥ 1 |
| DQ-CAPA-02 | Effectiveness check plan có ≥ 1 timepoint |
| DQ-CMP-01 | Recall → disclosure_due_at ≤ 48h sau confirm |
| DQ-CMP-02 | Mọi linked_asset tồn tại |

## 4. Cross-record Consistency

| ID | Rule |
|----|------|
| DQ-X-01 | MA `last_pm_date` ≤ today |
| DQ-X-02 | MA `next_pm_due` = `last_pm_date` + frequency (theo PM Plan effective) |
| DQ-X-03 | MA `state=released_for_use` → có WO Install + Document License effective |
| DQ-X-04 | Stock Entry consumption qty ≤ Stock on hand |
| DQ-X-05 | Asset Movement to_location ≠ from_location |
| DQ-X-06 | MA và ERPNext Asset đồng bộ field critical (location, custodian, status) trong 5 phút |

## 5. Migration-specific

| ID | Rule |
|----|------|
| DQ-MIG-01 | Mọi record import có `imported_from_legacy=1` + `legacy_ref` |
| DQ-MIG-02 | Field thiếu → đẩy vào "Data Quality Issue" log; không block |
| DQ-MIG-03 | Duplicate detection theo (serial_no, device_model) |
| DQ-MIG-04 | Date format normalize sang `YYYY-MM-DD` |
| DQ-MIG-05 | Currency mặc định VND nếu không xác định |
| DQ-MIG-06 | Pháp lý tồn tại nếu state ≥ released_for_use, nếu thiếu → log + state về `installed` |

## 6. Cách thực thi rule

| Hình thức | Cài đặt |
|-----------|---------|
| **Block** | Frappe Validation hooks (`validate`, `before_save`, `before_submit`) |
| **Warning** | UI message + ghi vào AC Data Quality Issue |
| **Cron audit** | Daily job quét toàn bộ DocType báo cáo |
| **Migration check** | Pre-import + post-import |
| **Database constraint** | Unique key + FK ở DB |

## 7. AC Data Quality Issue (DocType)

| Field | Mô tả |
|-------|-------|
| issue_no | – |
| rule_id | DQ-XXX |
| subject_doctype/subject_name | – |
| severity | Block/Warning |
| description | – |
| state | Open/In-progress/Resolved |
| owner_user | – |
| evidence | Attach |

## 8. Tiêu chí nghiệm thu DQ
- 100% rule liệt kê có implement (hoặc trong roadmap).
- Migration dry-run pass tỉ lệ DQ ≥ 95%.
- Cron audit chạy daily, dashboard hiển thị issue mở.
- Issue nghiêm trọng có owner xử lý + SLA.
