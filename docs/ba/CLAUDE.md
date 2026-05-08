# CLAUDE.md — AssetCore (Frappe v15 — Frappe-only)
> Tài liệu điều hướng cho Claude Code khi build app `assetcore`.
> **Đã reconcile với codebase thực tế** (xem `00_RECONCILIATION_v3.md` cho mapping đầy đủ với BA pack gốc).
> **Phiên bản:** 3.0 — 2026-05-07.

---

## 1. PROJECT OVERVIEW

| Thuộc tính | Giá trị |
|------------|---------|
| **Tên app** | `assetcore` |
| **Frappe app name** | `assetcore` (snake_case) |
| **Frappe version** | v15 — **Frappe-only**, KHÔNG dependency ERPNext |
| **Module Frappe** | `AssetCore` (single — toàn bộ DocType nằm trong 1 module) |
| **Site DEV** | `assetcore.local` |
| **Mục tiêu** | Quản lý vòng đời thiết bị y tế (HTM/IMMIS) — từ nhu cầu đầu tư → giải nhiệm |
| **Wave hiện tại** | **Wave 1 + Wave 2 đã ship** (IMM-00 → IMM-12, trừ IMM-06/07/10) |
| **Frontend** | Vue 3 + TypeScript + Pinia + TanStack Query + Tailwind, thư mục `frontend/` |

> **Khác biệt lớn so với BA pack gốc:** AssetCore là app Frappe độc lập, **không** extend ERPNext, **không** đồng bộ `Asset` / `Item` / `Supplier`. Mọi master data (asset, supplier, location, UOM, warehouse, purchase, stock movement) đều có DocType `AC ` riêng.

---

## 2. ARCHITECTURE RULES (bất biến)

### R-01 · Frappe-only — không dependency ERPNext
- Không `bench install-app erpnext`.
- Không tham chiếu DocType `Item`, `Asset`, `Supplier`, `Stock Entry`, `Purchase Receipt`, `Department` (ERPNext) trong code.
- `hooks.py` xác nhận: `override_doctype_class = {}`.

### R-02 · 3 tiers strict (API → Service → DocType controller)
- **API layer** (`assetcore/api/imm<NN>.py`): chỉ whitelist + validate input + delegate.
- **Service layer** (`assetcore/services/imm<NN>.py`): toàn bộ business logic, side-effect, audit.
- **Controller DocType** (`assetcore/assetcore/doctype/<dt>/<dt>.py`): chỉ validate cấu trúc; gọi service nếu cần.
- Không viết logic nghiệp vụ trong API hoặc controller.

### R-03 · Mọi state change → Frappe Workflow
- Không `doc.workflow_state = "..."` rồi `doc.save()`.
- Không `frappe.db.set_value()` để bypass workflow.
- Dùng `frappe.workflow.apply_workflow(doc, action)` hoặc workflow JSON action.

### R-04 · Audit Trail là immutable hash chain
- DocType `IMM Audit Trail` lưu chuỗi SHA-256 (`hash_sha256` + `prev_hash`).
- API duy nhất để insert: `assetcore.utils.lifecycle.log_audit_event(...)`.
- Không update / delete `IMM Audit Trail` sau khi insert.
- Verify chain: `assetcore.utils.lifecycle.verify_audit_chain(asset)`.

### R-05 · Lifecycle Event cho mọi sự kiện vòng đời
- DocType `Asset Lifecycle Event` lưu các event (`installed`, `commissioned`, `released`, `decommissioned`, `pm_completed`, `failure_reported`, `repaired`, `calibrated`, …).
- API duy nhất: `assetcore.utils.lifecycle.create_lifecycle_event(...)`.

### R-06 · 3 prefix DocType song song (xem §3)
- `AC <Name>` cho foundation/master không gắn module IMM cụ thể.
- `IMM <Name>` cho DocType chỉ tồn tại trong 1 module IMM-XX.
- (no prefix) cho DocType cross-module / shared lifecycle.

### R-07 · Role prefix `IMM ` (không phải `AC `)
- Internal: `IMM System Admin`, `IMM HTM Engineer`, `IMM QA Officer`, …
- External: `Vendor Engineer` (không prefix).
- Quản lý qua `Role Profile` + `Module Profile` trong fixtures.

### R-08 · Permission qua `permission_query_conditions`
- Khai báo trong `hooks.py` → handler trong `assetcore/permissions.py`.
- Hiện đã wire cho: `AC Asset`, `Incident Report`, `Asset Repair`, `PM Work Order`.

### R-09 · Không hardcode secret / config
- Dùng `frappe.conf` / `frappe.get_site_config()` cho credentials.
- Cấu hình SLA dùng fixture `IMM SLA Policy`.

### R-10 · Workflow naming convention
- `IMM-<NN> <Tên>` cho module workflow (vd `IMM-08 PM Workflow`).
- `AC <Tên>` cho workflow shared (vd `AC Asset Lifecycle`).
- State name: **Title Case có space** (`In Progress`, `Pending Review`, `Cannot Repair`).
- Action label: **tiếng Việt có dấu** (`Bắt đầu sửa chữa`, `Phê duyệt`, `Yêu cầu RCA`).

---

## 3. DOCTYPES MANIFEST — toàn bộ Wave 1 + Wave 2 (đã ship)

> **Module:** `AssetCore` (single) cho mọi DocType.
> **Folder file:** `assetcore/assetcore/doctype/<doctype_snake>/<doctype_snake>.json`.

### 3.1 Foundation / Audit / Lifecycle
| DocType | Submittable | Naming | Mục đích |
|---------|-------------|--------|----------|
| `Asset Lifecycle Event` | No | `naming_series:` | Sự kiện vòng đời tài sản (cradle-to-grave) |
| `IMM Audit Trail` | No | `naming_series:` | Hash chain SHA-256 immutable cho mọi action quan trọng |
| `IMM SLA Policy` | No | `field:policy_name` | Cấu hình SLA + thời gian eskalat |

### 3.2 Master Data — `AC ` prefix
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `AC Asset` | Yes | `naming_series:` |
| `AC Asset Category` | No | `field:category_name` |
| `AC Asset Depreciation Schedule` | No | — |
| `AC Asset Downtime Log` | No | `naming_series:` |
| `AC Authorized Technician` | No | — |
| `AC Department` | No | (autoname) |
| `AC Location` | No | (autoname) |
| `AC Spare Part` | No | `naming_series:` |
| `AC Spare Part Stock` | No | `field:stock_key` |
| `AC Supplier` | Yes | `naming_series:` |
| `AC UOM` | No | `field:uom_name` |
| `AC UOM Conversion` (child) | — | — |
| `AC Warehouse` | No | `format:AC-WH-{####}` |

### 3.3 Procurement / Stock — `AC ` prefix (Wave 2)
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `AC Purchase` | Yes | `naming_series:` |
| `AC Purchase Item` (child) | — | — |
| `AC Purchase Device Item` (child) | — | — |
| `AC Stock Movement` | Yes | `naming_series:` |
| `AC Stock Movement Item` (child) | — | — |

### 3.4 IMM-01 Needs / Plan / Forecast
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `IMM Needs Request` | Yes | `NR-.YY.-.MM.-.#####` |
| `Needs Priority Scoring` (child) | — | — |
| `IMM Demand Forecast` | No | `DF-.YYYY.-.#####` |
| `Forecast Driver` (child) | — | — |
| `IMM Procurement Plan` | Yes | `PP-.YY.-.#####` |
| `Procurement Plan Line` (child) | — | — |
| `Budget Estimate Line` (child) | — | — |

### 3.5 IMM-02 Tech Spec / Benchmark / Risk
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `IMM Tech Spec` | Yes | `TS-.YY.-.#####` |
| `Tech Spec Requirement` (child) | — | — |
| `Tech Spec Document` (child) | — | — |
| `IMM Market Benchmark` | Yes | `MB-.YY.-.#####` |
| `Benchmark Candidate` (child) | — | — |
| `IMM Lock-in Risk Assessment` | Yes | `LR-.YY.-.#####` |
| `Lock-in Risk Item` (child) | — | — |
| `Infra Compatibility Item` (child) | — | — |
| `Firmware Change Request` | Yes | `FCR-.YYYY.-.#####` |

### 3.6 IMM-03 Vendor / AVL / Audit / Decision
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `IMM AVL Entry` | Yes | `AVL-.YYYY.-.#####` |
| `Vendor Cert` (child) | — | — |
| `IMM Vendor Evaluation` | Yes | `VE-.YY.-.#####` |
| `Vendor Eval Candidate` (child) | — | — |
| `Vendor Eval Criterion` (child) | — | — |
| `Vendor Quotation Line` (child) | — | — |
| `IMM Supplier Audit` | Yes | `SA-.YY.-.#####` |
| `Audit Finding` (child) | — | — |
| `IMM Vendor Scorecard` | No | `format:VS-{period_year}-Q{period_q}-{supplier}` |
| `Scorecard KPI Row` (child) | — | — |
| `IMM Procurement Decision` | Yes | `PD-.YY.-.#####` |

### 3.7 IMM-04 Commissioning
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `Asset Commissioning` | Yes | `ACC-.YY.-.MM.-.#####` |
| `Commissioning Checklist` (child) | — | — |
| `Commissioning Document Record` (child) | — | — |

### 3.8 IMM-05 Document Management
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `Asset Document` | No | `format:DOC-{asset_ref}-{YYYY}-{####}` |
| `Document Request` | No | `format:DOCREQ-{YYYY}-{MM}-{####}` |
| `Required Document Type` | No | `field:type_name` |
| `Expiry Alert Log` | No | `format:EAL-{YYYY}-{MM}-{#####}` |

### 3.9 IMM-08 Preventive Maintenance
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `PM Work Order` | Yes | `PM-WO-.YYYY.-.#####` |
| `PM Schedule` | No | `format:PMS-{asset_ref}-{pm_type}-{####}` |
| `PM Checklist Template` | No | `format:PMCT-{asset_category}-{####}` |
| `PM Checklist Item` (child) | — | — |
| `PM Checklist Result` (child) | — | — |
| `PM Task Log` (child) | — | — |

### 3.10 IMM-09 Repair (Corrective Maintenance)
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `Asset Repair` | Yes | `WO-CM-.YYYY.-.#####` |
| `Repair Checklist` (child) | — | — |
| `Spare Parts Used` (child) | — | — |
| `Asset Transfer` | No | `naming_series:` |

### 3.11 IMM-11 Calibration
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `IMM Asset Calibration` | Yes | `CAL-.YYYY.-.#####` |
| `IMM Calibration Schedule` | No | `CAL-SCH-.YYYY.-.#####` |
| `IMM Calibration Measurement` (child) | — | — |
| `IMM Device Spare Part` (child) | — | — |
| `IMM Device Model` | No | `naming_series:` |

### 3.12 IMM-12 Incident → RCA → CAPA
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `Incident Report` | Yes | `naming_series:` |
| `IMM RCA Record` | Yes | `naming_series:` |
| `IMM RCA Five Why Step` (child) | — | — |
| `IMM RCA Related Incident` (child) | — | (autoincrement) |
| `IMM CAPA Record` | Yes | `naming_series:` |
| `Asset QA Non Conformance` | Yes | `format:NC-.YY.-.MM.-.#####` |

### 3.13 Other / Service Contract
| DocType | Submittable | Naming |
|---------|-------------|--------|
| `Service Contract` | No | `naming_series:` |
| `Service Contract Asset` (child) | — | — |

---

## 4. NAMING CONVENTIONS

### 4.1 DocType — 3 prefix song song
| Loại | Prefix | Ví dụ |
|---|---|---|
| Foundation/master không gắn IMM module cụ thể | `AC ` | `AC Asset`, `AC Supplier`, `AC Location`, `AC Spare Part` |
| DocType chỉ tồn tại trong 1 module IMM-XX | `IMM ` | `IMM Needs Request`, `IMM CAPA Record`, `IMM Audit Trail` |
| Cross-module / shared lifecycle | (không) | `Asset Repair`, `PM Work Order`, `Incident Report`, `Asset Document` |

### 4.2 Field (snake_case)
- FK Link: `<entity>` — `asset`, `device_model`, `supplier`.
- Date: `*_date` — `pm_due_date`, `expiry_date`.
- Datetime: `*_at` — `released_at`, `performed_at`.
- Boolean: `is_*` / `has_*` — `is_critical`, `has_calibration_required`.
- State machine: dùng field chuẩn `workflow_state` (Frappe convention).

### 4.3 Naming Series (đầu mã)
| Module | Mã | DocType |
|---|---|---|
| IMM-01 | `NR-`, `PP-`, `DF-` | Needs Request, Procurement Plan, Demand Forecast |
| IMM-02 | `TS-`, `MB-`, `LR-`, `FCR-` | Tech Spec, Market Benchmark, Lock-in Risk, Firmware Change |
| IMM-03 | `AVL-`, `VE-`, `SA-`, `PD-` | AVL, Vendor Eval, Supplier Audit, Procurement Decision |
| IMM-04 | `ACC-` | Asset Commissioning |
| IMM-05 | `DOC-`, `DOCREQ-`, `EAL-` | Asset Document, Document Request, Expiry Alert |
| IMM-08 | `PM-WO-`, `PMS-`, `PMCT-` | PM Work Order, PM Schedule, PM Checklist Template |
| IMM-09 | `WO-CM-` | Asset Repair |
| IMM-11 | `CAL-`, `CAL-SCH-` | Asset Calibration, Calibration Schedule |
| IMM-12 | `NC-` | Asset QA Non Conformance |
| Cross | `AC-WH-`, `VS-` | Warehouse, Vendor Scorecard |

### 4.4 Roles (prefix `IMM `)
**Wave 1 — core HTM operations:**
```
IMM System Admin             — quản trị hệ thống
IMM Operations Manager       — Trưởng VTTBYT
IMM Department Head          — Trưởng khoa
IMM Deputy Department Head   — Phó trưởng khoa
IMM Workshop Lead            — Trưởng xưởng kỹ thuật
IMM Biomed Technician        — KTV BME (vận hành)
IMM Technician               — KTV thiết bị
IMM QA Officer               — QC/QMS
IMM Auditor                  — kiểm toán nội bộ (read-only)
IMM Storekeeper              — quản lý kho phụ tùng
IMM Document Officer         — quản lý hồ sơ + giấy phép
IMM Clinical User            — người dùng cuối khoa
Vendor Engineer              — kỹ sư vendor (external, scoped)
```
**Wave 2 — planning & procurement:**
```
IMM Planning Officer         — chủ trì IMM-01 Needs/Plan
IMM Finance Officer          — KTTC
IMM HTM Engineer             — kỹ sư HTM (spec, benchmark, AVL)
IMM Procurement Officer      — mua sắm
IMM Risk Officer             — owner risk register + lock-in risk
IMM Board Approver           — phê duyệt BGĐ
```

**Role Profile** (bundle): `IMM - System Administrator`, `IMM - Operations Manager`, `IMM - Department Head`, `IMM - Deputy Department Head`, `IMM - Workshop Lead`, `IMM - Biomed Technician`, `IMM - Field Technician`, `IMM - QA Officer`, `IMM - Internal Auditor`, `IMM - Storekeeper`, `IMM - Document Officer`, `IMM - Clinical User`, `IMM - Vendor Engineer`, `IMM - Planning Officer`, `IMM - Finance Officer`, `IMM - HTM Engineer`, `IMM - Procurement Officer`, `IMM - Risk Officer`, `IMM - Board Approver`.

**Module Profile**: `IMM - Standard`, `IMM - Admin`, `IMM - Vendor`.

### 4.5 Workflow
- `IMM-<NN> <Tên>`: workflow gắn module (`IMM-01 Needs Workflow`, `IMM-08 PM Workflow`, …).
- `AC <Tên>`: workflow shared (`AC Asset Lifecycle`).
- **State name:** Title Case có space — `Pending Review`, `In Progress`, `Cannot Repair`, `Re Inspection`.
- **Action label:** tiếng Việt có dấu — `Bắt đầu sửa chữa`, `Phê duyệt`, `Yêu cầu RCA`.

### 4.6 File path
```
assetcore/
  api/
    imm00.py … imm12.py        # REST endpoints
    auth.py, dashboard.py, layout.py, inventory.py, purchase.py, depreciation.py, user.py
  services/
    imm00.py … imm12.py        # business logic
    auth_service.py, depreciation.py, inventory.py, purchase.py, uom.py
    shared/
  assetcore/
    doctype/<dt_snake>/        # JSON schema + .py controller
    workflow/<workflow>.json
  utils/
    lifecycle.py               # log_audit_event, create_lifecycle_event, verify_audit_chain
    api_endpoint.py, email.py, helpers.py, pagination.py, response.py
  permissions.py               # query_conditions handlers
  hooks.py
  setup/
    install.py, setup_core_permissions.py
  fixtures/
    role_profile.json, ...
  patches/                     # migration scripts (v3_0/...)
  tests/
  scripts/uat/                 # UAT scripts
frontend/                      # Vue 3 + TS app
```

---

## 5. WORKFLOWS — toàn bộ thực tế (14)

| Workflow | DocType | States | Transitions |
|---|---|---|---|
| `AC Asset Lifecycle` | `AC Asset` | 8 | 16 |
| `IMM-01 Needs Workflow` | `IMM Needs Request` | 8 | 24 |
| `IMM-01 Plan Workflow` | `IMM Procurement Plan` | 4 | 4 |
| `IMM-02 Spec Workflow` | `IMM Tech Spec` | 7 | 9 |
| `IMM-03 AVL Workflow` | `IMM AVL Entry` | 5 | 7 |
| `IMM-03 Vendor Eval Workflow` | `IMM Vendor Evaluation` | 5 | 6 |
| `IMM-03 Decision Workflow` | `IMM Procurement Decision` | 9 | 8 |
| `IMM-04 Workflow` | `Asset Commissioning` | 11 | 23 |
| `IMM-05 Document Workflow` | `Asset Document` | 6 | 9 |
| `IMM-08 PM Workflow` | `PM Work Order` | 7 | 13 |
| `IMM-09 Repair Workflow` | `Asset Repair` | 9 | 15 |
| `IMM-11 Calibration Workflow` | `IMM Asset Calibration` | 8 | 13 |
| `IMM-12 Incident Workflow` | `Incident Report` | 7 | 10 |
| `IMM-12 RCA Workflow` | `IMM RCA Record` | 4 | 4 |

(Chi tiết states/transitions xem `Phase_04_Process_Workflow_Design/01_Workflow_Specification/Workflow_Specification.md` đã rewrite.)

---

## 6. HOOKS & EVENTS — thực tế (`assetcore/hooks.py`)

### 6.1 doc_events
```python
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
        ],
    },
    "AC Stock Movement": {
        "on_submit": ["assetcore.services.purchase.auto_mark_purchase_received"],
        "on_cancel": ["assetcore.services.purchase.auto_unmark_purchase_received"],
    },
    "AC Purchase": {
        "validate": "assetcore.services.imm03.validate_ac_purchase_imm_link",
    },
}
```

### 6.2 scheduler_events (16 jobs)
**daily:**
- `imm00.check_capa_overdue`, `imm00.check_vendor_contract_expiry`, `imm00.check_registration_expiry`, `imm00.check_insurance_expiry`, `imm00.check_service_contract_expiry`
- `imm05.check_document_expiry`
- `imm08.generate_pm_work_orders_from_schedule`
- `imm11.create_due_calibration_wos`, `imm11.check_calibration_expiry`
- `imm12.detect_chronic_failures`
- `inventory.check_low_stock`
- `imm01.check_pending_request_overdue`, `imm02.check_overdue_drafts`
- `imm03.check_avl_expiry`, `imm03.check_audit_due`, `imm03.check_decision_overdue`

**weekly:**
- `imm01.budget_envelope_alert`, `imm02.benchmark_freshness_alert`

**monthly:**
- `imm00.rollup_asset_kpi`, `depreciation.run_due_depreciation`, `imm01.generate_demand_forecast`

**cron** (quarterly Q1/Q4):
- `0 2 1 1,4,7,10 *`: `imm03.update_vendor_scorecard`

### 6.3 permission_query_conditions
```python
permission_query_conditions = {
    "AC Asset": "assetcore.permissions.ac_asset_query",
    "Incident Report": "assetcore.permissions.incident_report_query",
    "Asset Repair": "assetcore.permissions.asset_repair_query",
    "PM Work Order": "assetcore.permissions.pm_work_order_query",
}
```

### 6.4 Lifecycle / Audit API
```python
# assetcore/utils/lifecycle.py — API duy nhất
log_audit_event(asset, event_type, actor=None, ref_doctype=None, ref_name=None,
                change_summary="", from_status=None, to_status=None) -> str
create_lifecycle_event(asset, event_type, actor=None, from_status=None, to_status=None,
                       root_doctype=None, root_record=None, notes="") -> str
verify_audit_chain(asset) -> bool
```

### 6.5 Fixtures (`hooks.py`)
- `Role` (19 IMM roles + Vendor Engineer)
- `Role Profile`, `Has Role`, `Module Profile`
- `IMM SLA Policy`
- `Workspace` (`IMM Operations`)
- `Workflow` (8 workflows được declare; tổng 14 workflow JSON nằm trong code, có thể bổ sung sau)
- `Workflow State` (~50 state)
- `Workflow Action Master` (~80 action — đa số tiếng Việt)

---

## 7. TESTING REQUIREMENTS

### 7.1 Acceptance Criteria tối thiểu
| # | Tiêu chí | Cách kiểm tra |
|---|----------|---------------|
| T-01 | Naming Series sinh đúng format | Unit test 3 record |
| T-02 | Mandatory fields block submit | `frappe.throw` test |
| T-03 | Workflow transitions đúng roles | Test với role / không role |
| T-04 | Link fields trỏ đúng DocType | `frappe.get_doc()` |
| T-05 | Audit Trail hash chain hợp lệ | `verify_audit_chain()` sau N action |
| T-06 | Lifecycle Event publish sau state change | Assert count + 1 |
| T-07 | Permission Query Conditions trả đúng scope | Login role X → assert chỉ thấy data X được phép |
| T-08 | SLA breach trigger đúng giờ | Mock clock + scheduler |
| T-09 | Service ≠ controller — controller chỉ delegate | Code review + lint |
| T-10 | Idempotency cho on_submit hooks | Submit 2 lần → 1 side effect |

### 7.2 Coverage
- Unit test ≥ 70% Python.
- E2E: ít nhất 1 Golden Scenario / module (xem `scripts/uat/uat_imm*.py`).

### 7.3 Test commands
```bash
bench --site assetcore.local run-tests --app assetcore
bench --site assetcore.local execute assetcore.scripts.uat.uat_imm09.run
```

### 7.4 Golden Scenarios (UAT scripts hiện có)
1. **IMM-04** Commissioning end-to-end (`uat_imm04.py`)
2. **IMM-05** Document Management (`uat_imm05.py`)
3. **IMM-08** PM auto-WO → execute → close → KPI
4. **IMM-09** Incident → Repair → Spare → Close (`uat_imm09.py`)
5. **IMM-11** Calibration plan → Cal → Fail → CAPA → Re-cal
6. **IMM-12** Incident P1 → SLA breach → escalate → close

---

## 8. FORBIDDEN PATTERNS

```python
# ❌ Set state bypass workflow
doc.workflow_state = "Released"
doc.save()  # → dùng frappe.workflow.apply_workflow()

# ❌ Update / Delete IMM Audit Trail
frappe.db.delete("IMM Audit Trail", {"name": x})  # → IMMUTABLE

# ❌ Insert IMM Audit Trail trực tiếp
frappe.get_doc({"doctype": "IMM Audit Trail", ...}).insert()
# → dùng assetcore.utils.lifecycle.log_audit_event(...)

# ❌ Hardcode credentials
api_key = "abc123"  # → dùng frappe.conf

# ❌ Reference ERPNext DocType (đã loại bỏ)
frappe.get_doc("Asset", ...)  # → AssetCore là Frappe-only
frappe.get_doc("Item", ...)
frappe.get_doc("Supplier", ...)

# ❌ Logic nghiệp vụ trong API hoặc controller
@frappe.whitelist()
def submit_repair(asset):
    # 50 dòng business logic ở đây — SAI
    # → đẩy sang assetcore.services.imm09.submit_repair(asset)

# ❌ DocType custom không theo 3 prefix
class FooBarDocType(Document):  # → phải là AC Foo Bar / IMM Foo Bar / Foo Bar (cross)

# ❌ Tự đặt prefix `Asset Core ` hay `AssetCore `
"AssetCore Repair"  # → SAI; thực tế là "Asset Repair" (cross-module)
```

---

## 9. QUICK REFERENCE — vị trí spec

| Cần biết | Đọc ở đâu |
|---|---|
| **Mapping BA gốc ↔ thực tế** | `00_RECONCILIATION_v3.md` (file này tham chiếu) |
| Glossary + naming convention | `Phase_00/07_Glossary_Naming_Convention/` |
| Wave plan | `Phase_00/06_Wave_Plan/` |
| Actor map | `Phase_01/03_Actor_Map/` |
| DocType spec đầy đủ | `Phase_03/05_DocType_Specification_Sheet/` (đã rewrite) **+** `DocType_Spec_Normalized.md` (top-level) |
| Workflow spec | `Phase_04/01_Workflow_Specification/` |
| Permission matrix | `Phase_04/02_Permission_Matrix/` |
| ERPNext mapping | `Phase_03/07_Mapping_ERPNext_AssetCore/` (đã rewrite — note: out of scope) |
| Code thật | `assetcore/{api,services,utils}/`, `assetcore/assetcore/{doctype,workflow}/`, `assetcore/permissions.py`, `assetcore/hooks.py` |
| UAT scripts | `assetcore/scripts/uat/uat_imm*.py` |
| Patches migration | `assetcore/patches/v3_0/` |

---

## 10. ENVIRONMENT SETUP

```bash
# Frappe v15 only — KHÔNG cài ERPNext
bench init frappe-bench --frappe-branch version-15
cd frappe-bench
bench new-site assetcore.local --db-name assetcore_db

bench get-app assetcore <repo-url>
bench --site assetcore.local install-app assetcore

bench --site assetcore.local migrate
bench --site assetcore.local export-fixtures   # dev
```

**Frontend:**
```bash
cd apps/assetcore/frontend
npm install
npm run dev   # Vite dev server
```

**Tooling:** Python 3.11+, Node 20+, MariaDB 10.6+, Redis, pytest, Playwright (E2E).

---

*Phiên bản 3.0 — 2026-05-07. Owner: Tech Lead. Reconciled to v3 codebase. Reference: `00_RECONCILIATION_v3.md`.*
