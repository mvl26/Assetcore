> ⚠️ **LEGACY — Reconcile to v3 codebase before use (2026-05-07).** Tài liệu này viết theo BA pack gốc (giả định ERPNext + `AC ` prefix thống nhất + role `AC Asset Manager` / `AC BME Engineer`...). **Code thực tế là Frappe-only với 3 prefix song song** (`AC `, `IMM `, không prefix), role prefix `IMM `. Khi đọc, ánh xạ tên DocType / role / workflow qua **`docs/ba/00_RECONCILIATION_v3.md`**.

---

# CANONICAL DATA MODEL — ASSETCORE

**Phiên bản:** 1.0
**Owner:** SA Lead + Data Architect

---

## 1. Mục tiêu
Định nghĩa mô hình dữ liệu chuẩn để trao đổi giữa AssetCore và hệ thống bên ngoài; tránh ánh xạ trực tiếp giữa từng cặp hệ thống → giảm độ ghép chặt.

## 2. Strategy
- Chuẩn hóa theo **FHIR R4** cho dữ liệu y tế (Device, Location, Practitioner, ServiceRequest, Observation, DocumentReference).
- Chuẩn hóa **OpenAPI canonical resources** cho dữ liệu vận hành (WorkOrder, Maintenance, Document, Vendor, Contract).
- Dùng **internal transformer** giữa AssetCore native ↔ canonical ↔ partner-specific.

## 3. Canonical Resources

### 3.1 CR-Device (FHIR Device aligned)
| Field | FHIR | AssetCore mapping |
|-------|------|-------------------|
| identifier | Device.identifier | AC Asset Identifier (multi) |
| status | Device.status | derived from MA.state |
| manufacturer | Device.manufacturer | AC Manufacturer.name |
| modelNumber | Device.modelNumber | AC Device Model.model_code |
| serialNumber | Device.serialNumber | AC Medical Asset.serial_no |
| location | Device.location | AC Medical Asset.location (Facility/Building/Department/Room) |
| type | Device.type | derived from Device Model + Item Group |
| owner | Device.owner | Organization (BV) |
| safety | Device.safety | derived from risk_class + criticality |

### 3.2 CR-Location (FHIR Location)
| Field | AssetCore mapping |
|-------|---------------------|
| identifier | AC Location.code |
| name | AC Location.name1 |
| status | AC Location.is_active |
| partOf | AC Location.parent_location |
| physicalType | AC Location.location_type |

### 3.3 CR-Practitioner (FHIR Practitioner)
| Field | AssetCore mapping |
|-------|---------------------|
| identifier | Frappe User.name / Employee.id |
| name | User.full_name |
| qualification | role list |

### 3.4 CR-WorkOrder (custom canonical)
```json
{
  "wo_id": "WO-2026-000123",
  "wo_type": "PM | CM | Cal | Inspection | Installation | Recall | Retirement",
  "device_id": "MA-2026-0001",
  "priority": "Critical | High | Medium | Low",
  "severity": "1..5 (CM only)",
  "planned_window": {"start": "...", "end": "..."},
  "actual_window": {"start": "...", "end": "..."},
  "sla": {"due_at": "...", "breached": false},
  "assignee": {"user": "...", "vendor": "..."},
  "tasks": [...],
  "spare_items": [...],
  "outcome": {
    "close_code": "...",
    "validation_result": "Pass | Fail | N/A",
    "downtime_minutes": 120
  },
  "linked_documents": [...],
  "audit_class": "QMS-critical | critical | info"
}
```

### 3.5 CR-DocumentReference (FHIR DocumentReference)
| Field | AssetCore mapping |
|-------|---------------------|
| identifier | AC Document Record.document_no |
| status | state |
| type | document_type/subtype |
| subject | linked_asset (Device/Location) |
| date | effective_date |
| author | author/issuing_authority |
| content.attachment.url | file URL |

### 3.6 CR-Vendor / Service Provider
```json
{
  "vendor_id": "...",
  "name": "...",
  "type": "OEM | Distributor | Service Provider | Calibration Lab | Trainer",
  "regulatory_certifications": [],
  "contracts": [...]
}
```

### 3.7 CR-Contract
```json
{
  "contract_id": "...",
  "type": "Purchase | Maintenance | Calibration | Insurance | Donation",
  "vendor_id": "...",
  "scope": {"models": [...], "assets": [...]},
  "valid_from": "...",
  "valid_to": "...",
  "sla": {...}
}
```

### 3.8 CR-LifecycleEvent (canonical event envelope — Phase_01/06)

```json
{
  "event_id": "...",
  "event_type": "...",
  "occurred_at": "...",
  "subject_ref": {"type": "Device | WorkOrder | Document", "id": "..."},
  "source_ref": {"type": "...", "id": "..."},
  "payload": {...},
  "audit_class": "..."
}
```

## 4. Mapping pattern giữa native ↔ canonical

```
AC Medical Asset (native) ─► CR-Device (canonical) ─► Partner-specific (FHIR Device or other)
                              │
                              └─► OpenAPI consumer
```

Transformer: trong app `assetcore.integration.transformers.<resource>.to_canonical / from_canonical`.

## 5. ID strategy
- Internal ID: AssetCore native (asset_code, wo_no, doc_no…).
- External canonical ID: cùng giá trị trong field `identifier.value`.
- Partner-specific ID: lưu bổ sung qua `external_identifier` table khi cần (ví dụ HIS biểu thị `Device.id` ở định dạng riêng).

## 6. Versioning
- Canonical resources versioned (v1, v2…).
- Backward compatibility ≥ 1 major version.
- Deprecation notice ≥ 6 tháng.

## 7. Tiêu chí nghiệm thu
- 8 canonical resources Wave 1 lock.
- Transformer to_canonical / from_canonical implement cho 4 resources core (Device, Location, WorkOrder, DocumentReference).
- Test mapping toàn vẹn với sample data.
