# PERMISSION MATRIX — ASSETCORE (v3)

> **Reconciled to v3 codebase — 2026-05-07.** Role thực tế dùng prefix `IMM ` (không `AC `). 4 DocType có `permission_query_conditions` riêng. Tham chiếu: `00_RECONCILIATION_v3.md`.

**Phiên bản:** 3.0
**Owner:** Tech Lead + IT Lead
**Áp dụng:** Frappe DocType Permission + Role Profile + Module Profile + custom permission query

---

## 1. Quy ước
- Q = Read · C = Create · W = Write · S = Submit · X = Cancel · A = Amend · D = Delete
- Số trong dấu ngoặc = Permission Level (Frappe field-level)

---

## 2. Role list (thực tế — `fixtures/role_profile.json` + `hooks.py`)

### 2.1 Wave 1 — core HTM operations
| Role | Mô tả | Role Profile |
|------|-------|---|
| `IMM System Admin` | Quản trị hệ thống | `IMM - System Administrator` |
| `IMM Operations Manager` | Trưởng VTTBYT | `IMM - Operations Manager` |
| `IMM Department Head` | Trưởng khoa | `IMM - Department Head` |
| `IMM Deputy Department Head` | Phó trưởng khoa | `IMM - Deputy Department Head` |
| `IMM Workshop Lead` | Trưởng xưởng | `IMM - Workshop Lead` |
| `IMM Biomed Technician` | KTV BME | `IMM - Biomed Technician` |
| `IMM Technician` | KTV thiết bị | `IMM - Field Technician` |
| `IMM QA Officer` | QC/QA/QMS | `IMM - QA Officer` |
| `IMM Auditor` | Kiểm toán nội bộ (read-only) | `IMM - Internal Auditor` |
| `IMM Storekeeper` | Quản kho phụ tùng | `IMM - Storekeeper` |
| `IMM Document Officer` | Quản hồ sơ + giấy phép | `IMM - Document Officer` |
| `IMM Clinical User` | Người dùng cuối khoa | `IMM - Clinical User` |
| `Vendor Engineer` | Vendor (external) | `IMM - Vendor Engineer` |

### 2.2 Wave 2 — planning & procurement
| Role | Mô tả | Role Profile |
|------|-------|---|
| `IMM Planning Officer` | KHTH — chủ trì IMM-01 | `IMM - Planning Officer` |
| `IMM Finance Officer` | KTTC | `IMM - Finance Officer` |
| `IMM HTM Engineer` | Kỹ sư HTM (spec, AVL, evaluation) | `IMM - HTM Engineer` |
| `IMM Procurement Officer` | Mua sắm | `IMM - Procurement Officer` |
| `IMM Risk Officer` | Owner risk register + lock-in | `IMM - Risk Officer` |
| `IMM Board Approver` | Phê duyệt BGĐ | `IMM - Board Approver` |

### 2.3 Module Profile (gói)
- `IMM - Standard` — gói cho user nội bộ điển hình
- `IMM - Admin` — gói cho System Admin
- `IMM - Vendor` — gói cho Vendor Engineer (scoped permission)

---

## 3. Permission per DocType (key DocTypes)

### 3.1 `AC Asset`
| Role | Q | C | W | S | X | A |
|------|---|---|---|---|---|---|
| `IMM System Admin` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `IMM Operations Manager` | ✓ | ✓ | ✓ | ✓ | ✓ |   |
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |   |   |
| `IMM Workshop Lead` | ✓ |   | ✓ |   |   |   |
| `IMM Biomed Technician` | ✓ |   | ✓ (limited) |   |   |   |
| `IMM Technician` | ✓ (assigned) |   |   |   |   |   |
| `IMM QA Officer` | ✓ |   | ✓ (QA fields) | ✓ |   |   |
| `IMM Department Head` | ✓ (own dept) |   |   |   |   |   |
| `IMM Clinical User` | ✓ (own dept) |   |   |   |   |   |
| `IMM Document Officer` | ✓ |   | ✓ (license fields) |   |   |   |
| `IMM Finance Officer` | ✓ (financial fields) |   |   |   |   |   |
| `IMM Auditor` | ✓ (read-only) |   |   |   |   |   |
| `Vendor Engineer` | ✓ (assigned scope) |   |   |   |   |   |

**Permission Query:** `assetcore.permissions.ac_asset_query` — filter theo `department` + vendor scope.

### 3.2 `PM Work Order` (IMM-08)
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Operations Manager` | ✓ | ✓ | ✓ | ✓ |
| `IMM Workshop Lead` | ✓ | ✓ | ✓ | ✓ |
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM Biomed Technician` | ✓ (assigned) |   | ✓ (own assigned) | ✓ |
| `IMM Technician` | ✓ (assigned) |   | ✓ (own assigned) | ✓ |
| `IMM QA Officer` | ✓ |   | ✓ (validate) | ✓ |
| `Vendor Engineer` | ✓ (assigned, contract) |   | ✓ (limited) | ✓ |
| `IMM Auditor` | ✓ |   |   |   |

**Permission Query:** `assetcore.permissions.pm_work_order_query`.

### 3.3 `Asset Repair` (IMM-09)
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Operations Manager` | ✓ | ✓ | ✓ | ✓ |
| `IMM Workshop Lead` | ✓ | ✓ | ✓ | ✓ |
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM Biomed Technician` | ✓ (assigned) |   | ✓ | ✓ |
| `IMM Technician` | ✓ (assigned) |   | ✓ | ✓ |
| `IMM Storekeeper` | ✓ (parts fields) |   | ✓ (Spare Parts Used) |   |
| `IMM QA Officer` | ✓ |   |   |   |
| `Vendor Engineer` | ✓ (assigned, contract) |   | ✓ (limited) | ✓ |

**Permission Query:** `assetcore.permissions.asset_repair_query`.

### 3.4 `Incident Report` (IMM-12)
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Clinical User` | ✓ (own dept) | ✓ (report) |   | ✓ |
| `IMM Department Head` | ✓ (own dept) | ✓ | ✓ | ✓ |
| `IMM Biomed Technician` | ✓ | ✓ | ✓ | ✓ |
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM Workshop Lead` | ✓ |   | ✓ |   |
| `IMM QA Officer` | ✓ | ✓ | ✓ |   |
| `IMM Risk Officer` | ✓ |   | ✓ (severity) |   |
| `IMM Auditor` | ✓ |   |   |   |

**Permission Query:** `assetcore.permissions.incident_report_query`.

### 3.5 `IMM RCA Record`, `IMM CAPA Record`
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM QA Officer` | ✓ | ✓ | ✓ | ✓ |
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM Operations Manager` | ✓ |   | ✓ (approval) | ✓ |
| `IMM Risk Officer` | ✓ |   | ✓ (risk fields) |   |
| `IMM Auditor` | ✓ |   |   |   |

### 3.6 `Asset Document` (IMM-05)
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Document Officer` | ✓ | ✓ | ✓ | ✓ |
| `IMM QA Officer` | ✓ | ✓ | ✓ | ✓ |
| `IMM HTM Engineer` | ✓ | ✓ |   |   |
| `IMM Operations Manager` | ✓ |   | ✓ (approve) | ✓ |
| `IMM Auditor` | ✓ |   |   |   |
| `IMM Clinical User` | ✓ (effective + Internal scope) |   |   |   |

### 3.7 `Asset Commissioning` (IMM-04)
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM Biomed Technician` | ✓ | ✓ | ✓ | ✓ |
| `IMM QA Officer` | ✓ |   | ✓ (QA gate) | ✓ |
| `IMM Operations Manager` | ✓ |   | ✓ (release approve) | ✓ |
| `IMM Document Officer` | ✓ (doc verify) |   | ✓ (doc fields) |   |
| `Vendor Engineer` | ✓ (assigned) |   | ✓ (limited) |   |

### 3.8 `IMM Asset Calibration` (IMM-11)
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Biomed Technician` | ✓ (lab role) | ✓ | ✓ | ✓ |
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM QA Officer` | ✓ |   | ✓ (approve) | ✓ |
| `Vendor Engineer` | ✓ (lab vendor) |   | ✓ (own) | ✓ |
| `IMM Auditor` | ✓ |   |   |   |

### 3.9 `IMM Audit Trail`
| Role | Q | C | W | D | Note |
|------|---|---|---|---|---|
| `IMM Auditor` | ✓ |   |   |   | Read-only toàn |
| `IMM System Admin` | ✓ |   |   |   | Read-only |
| Mọi role khác | ✓ (own scope qua filter) |   |   |   | – |

> ❌ Không role nào được Write hoặc Delete `IMM Audit Trail`. Insert chỉ qua `assetcore.utils.lifecycle.log_audit_event(...)` với `ignore_permissions=True`.

### 3.10 `Asset Lifecycle Event`
| Role | Q | C | W |
|------|---|---|---|
| Mọi role | ✓ (own scope) |   |   |

> Insert chỉ qua `create_lifecycle_event(...)`.

### 3.11 `IMM-01 Needs Request` / `IMM Procurement Plan` / `IMM Demand Forecast`
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Planning Officer` | ✓ | ✓ | ✓ | ✓ |
| `IMM Department Head` | ✓ (own dept) | ✓ | ✓ | ✓ |
| `IMM HTM Engineer` | ✓ |   | ✓ (technical) |   |
| `IMM Finance Officer` | ✓ |   | ✓ (budget) |   |
| `IMM Operations Manager` | ✓ |   | ✓ (approve) | ✓ |
| `IMM Board Approver` | ✓ |   | ✓ (final approve) | ✓ |

### 3.12 `IMM Tech Spec` / `IMM Market Benchmark` / `IMM Lock-in Risk Assessment`
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM QA Officer` | ✓ |   | ✓ (QA review) | ✓ |
| `IMM Risk Officer` | ✓ | ✓ (Lock-in) | ✓ | ✓ |
| `IMM Operations Manager` | ✓ |   | ✓ (approve) | ✓ |
| `IMM Board Approver` | ✓ |   | ✓ (lock) | ✓ |

### 3.13 `IMM AVL Entry` / `IMM Vendor Evaluation` / `IMM Supplier Audit` / `IMM Procurement Decision`
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Procurement Officer` | ✓ | ✓ | ✓ | ✓ |
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM QA Officer` | ✓ | ✓ (Audit) | ✓ | ✓ |
| `IMM Risk Officer` | ✓ |   | ✓ (risk gate) |   |
| `IMM Finance Officer` | ✓ |   | ✓ (budget gate) |   |
| `IMM Operations Manager` | ✓ |   | ✓ (approve) | ✓ |
| `IMM Board Approver` | ✓ |   | ✓ (final) | ✓ |

### 3.14 `AC Purchase` / `AC Stock Movement` / `AC Spare Part`
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Procurement Officer` | ✓ | ✓ | ✓ | ✓ (Purchase) |
| `IMM Storekeeper` | ✓ | ✓ | ✓ | ✓ (Stock Movement) |
| `IMM Finance Officer` | ✓ |   | ✓ (price/budget) |   |
| `IMM Operations Manager` | ✓ |   |   |   |

### 3.15 `Service Contract`
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM Procurement Officer` | ✓ | ✓ | ✓ |   |
| `IMM Operations Manager` | ✓ |   | ✓ (approve) |   |
| `IMM Finance Officer` | ✓ |   | ✓ (financial) |   |

### 3.16 `Firmware Change Request`
| Role | Q | C | W | S |
|------|---|---|---|---|
| `IMM HTM Engineer` | ✓ | ✓ | ✓ | ✓ |
| `IMM QA Officer` | ✓ |   | ✓ | ✓ |
| `IMM Risk Officer` | ✓ |   | ✓ |   |

---

## 4. Permission Query Conditions (row-level — `hooks.py`)

```python
permission_query_conditions = {
    "AC Asset": "assetcore.permissions.ac_asset_query",
    "Incident Report": "assetcore.permissions.incident_report_query",
    "Asset Repair": "assetcore.permissions.asset_repair_query",
    "PM Work Order": "assetcore.permissions.pm_work_order_query",
}
```

| DocType | Logic |
|---|---|
| `AC Asset` | Filter theo department user; vendor chỉ thấy asset mình servicing |
| `Incident Report` | Clinical user chỉ thấy report trong khoa của mình; QA/HTM thấy toàn bộ |
| `Asset Repair` | Technician chỉ thấy assigned; vendor chỉ thấy WO contract liên quan |
| `PM Work Order` | Tương tự `Asset Repair` |

---

## 5. Field-level Permission (selected)

### 5.1 `AC Asset`
- `acquisition_cost`, `depreciation_value`: chỉ `IMM Finance Officer`, `IMM Operations Manager`, `IMM Board Approver` (read).
- `criticality`, `risk_class`: chỉ `IMM HTM Engineer`, `IMM QA Officer`, `IMM Risk Officer` (write); read all.

### 5.2 `Service Contract`
- `contract_value`, `payment_terms`: chỉ `IMM Procurement Officer`, `IMM Finance Officer`, `IMM Operations Manager`.

### 5.3 `PM Work Order` / `Asset Repair`
- `cost_labor`, `cost_parts`, `total_cost`: chỉ `IMM Operations Manager`, `IMM Finance Officer`, `IMM Workshop Lead` (read). Vendor không thấy.

### 5.4 `IMM Procurement Decision`
- `negotiated_price`, `vendor_quote_breakdown`: `IMM Procurement Officer` + `IMM Finance Officer`.

---

## 6. Segregation of Duty (SoD)

| Quy tắc | Enforce |
|---|---|
| WO creator ≠ validator | Workflow `IMM-08`/`IMM-09` chặn role đã tạo cũng đóng vai trò validate |
| Document creator ≠ approver | `IMM-05 Document Workflow` |
| CAPA submitter ≠ closer | Service `imm12` validate |
| Stock issue ≠ stock approve | `AC Stock Movement` validate |
| Procurement decision ≠ board approver (multi-stage) | `IMM-03 Decision Workflow` 9 stages |

---

## 7. ABAC custom (Domain Layer)

- `Vendor Engineer` chỉ thấy WO/Calibration `assigned_user = self`; không thấy `cost_*` field.
- `IMM Auditor` toàn hệ thống read-only (chưa hard-code; cần Custom DocPerm `permlevel`).
- Asset criticality A → action `Đưa ra khỏi sử dụng` chỉ `IMM Operations Manager` + `IMM QA Officer` (deny `IMM HTM Engineer`).

---

## 8. Tiêu chí nghiệm thu

- ✓ 19 IMM role + Vendor Engineer được tạo qua fixture; verify với `bench --site assetcore.local migrate`.
- ✓ Role Profile + Module Profile bundle deploy được.
- ✓ 4 permission_query_conditions test pass cho positive + negative scope.
- ✓ Field-level permission test pass.
- ✓ SoD test pass.
- ✓ Pen-test phát hiện 0 escalation path (vendor không escalate được; clinical không xem cross-dept).

---

## 9. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Tech Lead |  | 2026-05-07 |
| IT Lead |  | 2026-05-07 |
| QA Officer |  | 2026-05-07 |
