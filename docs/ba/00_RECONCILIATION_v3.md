# 00 — RECONCILIATION: BA Pack ↔ Phần mềm hiện tại (v3)

> **Mục đích:** Tài liệu này là **single source of truth** cho việc đối chiếu giữa bộ tài liệu BA gốc (viết theo giả định "ERPNext + AC prefix") và **codebase thực tế** của AssetCore v3 (Frappe-only, nhiều DocType prefix).
>
> **Ngày:** 2026-05-07
> **Owner:** Tech Lead + BA Lead
> **Áp dụng cho:** Tất cả file trong `docs/ba/Phase_*` — khi đọc bất kỳ file BA nào hãy ánh xạ tên thông qua các bảng dưới đây.

---

## 0. Thay đổi kiến trúc lớn (so với BA gốc)

| Giả định BA gốc | Thực tế code |
|---|---|
| AssetCore là **lớp HTM trên ERPNext v15** | AssetCore là **app Frappe-only** — `hooks.py` ghi rõ: *"AssetCore is Frappe-only (no ERPNext dep)"* |
| ERPNext `Asset` là System of Record kế toán | Có `AC Asset` thay thế (custom DocType, không link ERPNext Asset) |
| ERPNext `Item` ↔ `AC Device Model` (1-1) | Có `IMM Device Model` độc lập, không gắn Item |
| ERPNext `Supplier` ↔ `AC Service Provider` | Có `AC Supplier` thay thế |
| ERPNext `Purchase Receipt`, `Stock Entry` hooks | Có `AC Purchase`, `AC Stock Movement` thay thế (custom) |
| Custom Field thêm vào core (Item, Asset, Supplier, Department) | **Không có** — `override_doctype_class = {}` trong `hooks.py` |
| `AC ` prefix duy nhất cho mọi DocType custom | **3 prefix song song**: `AC ` (foundation), `IMM ` (module-specific), không prefix (cross-cutting) |
| 17 IMM modules + Wave 1 = 6 module | **Wave 1 + Wave 2 đã ship**: IMM-00 (foundation), IMM-01, 02, 03, 04, 05, 08, 09, 11, 12 |
| Roles `AC Asset Manager`, `AC BME Engineer`, … | Roles `IMM Operations Manager`, `IMM HTM Engineer`, … (xem §3) |
| `AC Lifecycle Event` là DocType chính của audit | **Hai DocType**: `Asset Lifecycle Event` (sự kiện vòng đời) **+** `IMM Audit Trail` (chuỗi SHA-256, immutable) |
| `assetcore.lifecycle.publisher.publish()` là API duy nhất | API là `assetcore.utils.lifecycle.log_audit_event(...)` và `create_lifecycle_event(...)` |

> **Hệ quả:** Tất cả phần BA nói về *ERPNext sync*, *Custom Field on Item/Asset*, *erpnext_asset link*, *ERPNextAssetSync service* → **không áp dụng**. Cần đánh dấu là *deprecated* hoặc *out-of-scope* khi đọc.

---

## 1. Quy ước đặt tên DocType — thực tế

Codebase dùng **3 prefix song song**, không phải 1 như BA gốc giả định:

| Prefix | Khi nào dùng | Folder file | Ví dụ DocType label |
|---|---|---|---|
| `AC ` | Foundation / master / kế toán nội bộ | `ac_*` | `AC Asset`, `AC Supplier`, `AC Location`, `AC Department`, `AC Spare Part`, `AC Purchase`, `AC Stock Movement`, `AC UOM`, `AC Warehouse` |
| `IMM ` | DocType gắn rõ với 1 module IMM-XX (planning, vendor, calibration, CAPA, audit) | `imm_*` | `IMM Needs Request`, `IMM Tech Spec`, `IMM AVL Entry`, `IMM Vendor Evaluation`, `IMM Procurement Decision`, `IMM Asset Calibration`, `IMM CAPA Record`, `IMM RCA Record`, `IMM Audit Trail`, `IMM SLA Policy`, `IMM Device Model` |
| (không prefix) | Cross-cutting / shared lifecycle / nghiệp vụ chia sẻ giữa nhiều module | bare `<name>_*` | `Asset Lifecycle Event`, `Asset Commissioning`, `Asset Document`, `Asset Repair`, `Asset Transfer`, `Incident Report`, `PM Work Order`, `PM Schedule`, `Service Contract`, `Vendor Cert`, `Audit Finding`, `Document Request` |

**Module Frappe:** tất cả DocType nằm trong **module duy nhất** `AssetCore` (BA gốc giả định nhiều module: `Asset Core`, `Asset Registry`, `Work Order`, `Maintenance`, `Calibration`, `Compliance`, `Document QMS`, `Dashboard` — không tồn tại trong code).

**Folder Python:** `assetcore/assetcore/doctype/<doctype_snake>/<doctype_snake>.json` (đường dẫn phẳng theo `<doctype_snake>`, không phân theo domain folder như BA gốc gợi ý).

---

## 2. Mapping BA name → tên thực tế

### 2.1 Foundation / Lifecycle / Audit

| BA gốc | Thực tế | Ghi chú |
|---|---|---|
| `AC Lifecycle Event` (single, immutable) | `Asset Lifecycle Event` + `IMM Audit Trail` | Hai DocType: 1 cho event, 1 cho hash chain |
| `AC Event Type` (seed data) | (không có DocType riêng) | Event type là field `event_type` (string), seed nằm trong service |
| `AssetCore Settings` (Single) | (không tồn tại) | Cấu hình app nằm trong `assetcore/setup/` và `IMM SLA Policy` fixture |
| `AC Audit Trail` (BA Phase 04 §05) | `IMM Audit Trail` | Có chuỗi SHA-256, prev_hash → immutable, verify chain qua `assetcore.utils.lifecycle.verify_audit_chain` |

### 2.2 Master Data

| BA gốc | Thực tế |
|---|---|
| `AC Manufacturer` | (chưa tách — manufacturer là field text trên `IMM Device Model` / `AC Asset`) |
| `AC Location` | `AC Location` ✓ |
| `AC Device Model` | `IMM Device Model` |
| `AC Service Provider` | `AC Supplier` (gộp với supplier; có trường phân loại) |
| `AC Contract` | `Service Contract` (+ child `Service Contract Asset`) |
| ERPNext `Item` | (không dùng) — thiết bị có ID là `IMM Device Model.model_code`; vật tư là `AC Spare Part` |
| ERPNext `Department` | `AC Department` |
| ERPNext `UOM` | `AC UOM` (+ `AC UOM Conversion`) |

### 2.3 Asset Registry

| BA gốc | Thực tế |
|---|---|
| `AC Medical Asset` | `AC Asset` |
| `AC Asset Identifier` | (chưa tách — identifier là các field `serial_no`, `qr_code`, `rfid_tag` trên `AC Asset`) |
| `AC Custodian Assignment` | (chưa tách — custodian là field link User trên `AC Asset`; lịch sử lưu qua `Asset Lifecycle Event`) |
| `AC Asset Movement` | `Asset Transfer` |
| `AC Stand-Down Record` | (chưa tách — biểu hiện qua state `Out of Service` trên workflow `AC Asset Lifecycle` + `AC Asset Downtime Log`) |
| `AC Decommission Record` | (chưa tách — state `Decommissioned` trên `AC Asset Lifecycle`) |
| `AC Disposal Record` | (chưa tách — state `Decommissioned` + `AC Asset Depreciation Schedule`) |

### 2.4 Document & QMS

| BA gốc | Thực tế |
|---|---|
| `AC Document Record` | `Asset Document` (+ `Document Request`, `Required Document Type`, `Expiry Alert Log`) |
| `AC QMS Artifact` (Tier 1/2/3/4) | (không có DocType riêng — QMS artifact hiện được track qua `Asset Document` với phân loại; tier system chưa hard-code) |
| `AC Commissioning Document Record` | `Commissioning Document Record` |
| `AC IQ OQ PQ Record` | `Commissioning Checklist` (+ `Asset Commissioning` workflow) |

### 2.5 Work Order Engine

| BA gốc | Thực tế |
|---|---|
| `AC Work Order` (unified — PM/CM/Cal/Insp/Install) | **Tách 3 DocType chuyên biệt**: `PM Work Order` (PM), `Asset Repair` (CM), `IMM Asset Calibration` (Cal); commissioning có riêng `Asset Commissioning` |
| `AC Work Order Task` (child) | `PM Task Log`, `PM Checklist Result` (PM); `Repair Checklist` (CM); `IMM Calibration Measurement` (Cal) |
| `AC Work Order Spare Item` (child) | `Spare Parts Used` (CM); `IMM Device Spare Part` (BOM) |
| `AC Failure Report` | `Incident Report` |
| `AC PM Plan` | `PM Schedule` (+ `PM Checklist Template`, `PM Checklist Item`) |
| `AC PM Task Detail` (child) | `PM Checklist Item` |
| `AC Calibration Plan` | `IMM Calibration Schedule` |
| `AC Calibration Record` | `IMM Asset Calibration` |
| `AC Calibration Measurement` (child) | `IMM Calibration Measurement` |

### 2.6 Compliance / CAPA / Audit

| BA gốc | Thực tế |
|---|---|
| `AC Nonconformity` | `Asset QA Non Conformance` |
| `AC CAPA` | `IMM CAPA Record` |
| `AC CAPA Action` (child) | (lồng trong `IMM CAPA Record`, không tách child) |
| `AC Compliance Case` | (chưa có — gộp logic vào `Incident Report` + `IMM RCA Record` + `IMM CAPA Record`) |
| `AC Risk Entry` | `IMM Lock-in Risk Assessment` (+ `Lock-in Risk Item` child) — cho risk vendor lock-in; risk lâm sàng/an toàn chưa tách |
| `AC Change Control Request` | `Firmware Change Request` (chỉ cho firmware; CCR chung chưa có) |
| `AC Audit` (internal) | `IMM Supplier Audit` (audit vendor) + `Audit Finding` (child); audit nội bộ QMS chưa có |
| `AC Management Review` | (chưa có) |

### 2.7 Procurement / Planning (BA gốc xếp Wave 2 nhưng đã ship)

| BA gốc / mới | Thực tế |
|---|---|
| (Wave 2 — chưa spec) `AC Needs Request` | `IMM Needs Request` (+ `Needs Priority Scoring`) |
| (Wave 2) `AC Demand Forecast` | `IMM Demand Forecast` (+ `Forecast Driver`) |
| (Wave 2) `AC Procurement Plan` | `IMM Procurement Plan` (+ `Procurement Plan Line`, `Budget Estimate Line`) |
| (Wave 2) `AC Tech Spec` | `IMM Tech Spec` (+ `Tech Spec Requirement`, `Tech Spec Document`, `Infra Compatibility Item`) |
| (Wave 2) `AC Market Benchmark` | `IMM Market Benchmark` (+ `Benchmark Candidate`) |
| (Wave 2) `AC AVL Entry` | `IMM AVL Entry` (+ `Vendor Cert`) |
| (Wave 2) `AC Vendor Evaluation` | `IMM Vendor Evaluation` (+ `Vendor Eval Candidate`, `Vendor Eval Criterion`, `Vendor Quotation Line`) |
| (Wave 2) `AC Vendor Scorecard` | `IMM Vendor Scorecard` (+ `Scorecard KPI Row`) |
| (Wave 2) `AC Procurement Decision` | `IMM Procurement Decision` |
| (Wave 2) `AC Stock Movement` | `AC Stock Movement` (+ `AC Stock Movement Item`) |
| (Wave 2) `AC Purchase Order` | `AC Purchase` (+ `AC Purchase Item`, `AC Purchase Device Item`) |

### 2.8 Dashboard / Metric

| BA gốc | Thực tế |
|---|---|
| `AC Metric Definition` | (chưa có — KPI compute trong `assetcore/services/imm00.py`) |
| `AC Dashboard Snapshot` | (chưa có — query trực tiếp qua `assetcore/api/dashboard.py`) |
| `AC Dashboard Widget` | (chưa có) |
| `AC Alert Rule` | `Expiry Alert Log` (cho document/license expiry); alert khác là cron scheduled trong `hooks.py` |

---

## 3. Mapping role: BA gốc → thực tế

> Code dùng prefix `IMM ` (không có space ở đầu — đây là 1 từ "IMM"), khác với BA gốc dùng prefix `AC `.

| BA gốc | Thực tế (`assetcore/fixtures/role_profile.json` + `hooks.py`) |
|---|---|
| `AC System Admin` | `IMM System Admin` |
| `AC Asset Manager` (Trưởng/Phó VTTBYT) | `IMM Operations Manager`, `IMM Department Head`, `IMM Deputy Department Head` |
| `AC BME Engineer` | `IMM HTM Engineer` (planning/spec) **hoặc** `IMM Biomed Technician` (vận hành) |
| `AC Technician` | `IMM Technician` |
| `AC Calibration Lab Engineer` | (gộp vào `IMM Biomed Technician` / `Vendor Engineer`) |
| `AC Spare Warehouse Officer` | `IMM Storekeeper` |
| `AC QMS Officer` | `IMM QA Officer` |
| `AC QMS Lead` | `IMM QA Officer` (+ `IMM Operations Manager` cho approval cao cấp) |
| `AC Department Head` | `IMM Department Head` (+ `IMM Deputy Department Head`) |
| `AC Clinical User` | `IMM Clinical User` |
| `AC Procurement Officer` | `IMM Procurement Officer` |
| `AC Finance Officer` | `IMM Finance Officer` |
| `AC Legal Officer` | `IMM Document Officer` (đảm nhiệm hồ sơ + giấy phép) |
| `AC Auditor` | `IMM Auditor` |
| `AC Vendor Service Engineer` (external) | `Vendor Engineer` (không có prefix `IMM`) |
| `AC Vendor Calibration` (external) | `Vendor Engineer` (cùng role, scope qua workflow) |
| `AC Vendor Trainer` (external) | (không có — out of scope hiện tại) |
| `AC Executive Viewer` (BGĐ) | `IMM Operations Manager` (read dashboard) **hoặc** chưa tách role riêng |
| (BA chưa có) `IMM Planning Officer` | Wave 2 — chủ trì IMM-01 Needs/Plan |
| (BA chưa có) `IMM Workshop Lead` | Quản lý đội kỹ thuật xưởng |
| (BA chưa có) `IMM Risk Officer` | Owner `IMM Lock-in Risk Assessment` + risk register |
| (BA chưa có) `IMM Board Approver` | Phê duyệt cấp BGĐ cho procurement decision lớn |

**Role profiles** (gói role bundles — fixture trong `role_profile.json`):
- `IMM - System Administrator`, `IMM - Operations Manager`, `IMM - Department Head`, `IMM - Deputy Department Head`, `IMM - Workshop Lead`
- `IMM - Biomed Technician`, `IMM - Field Technician`, `IMM - QA Officer`, `IMM - Internal Auditor`, `IMM - Storekeeper`
- `IMM - Document Officer`, `IMM - Clinical User`, `IMM - Vendor Engineer`
- Wave 2: `IMM - Planning Officer`, `IMM - Finance Officer`, `IMM - HTM Engineer`, `IMM - Procurement Officer`, `IMM - Risk Officer`, `IMM - Board Approver`

**Module profiles:** `IMM - Standard`, `IMM - Admin`, `IMM - Vendor`.

---

## 4. Mapping Workflow: BA gốc → thực tế

| BA gốc | Thực tế | DocType target |
|---|---|---|
| `AC Medical Asset Workflow` | `AC Asset Lifecycle` | `AC Asset` |
| `AC Document Record Workflow` | `IMM-05 Document Workflow` | `Asset Document` |
| `AC QMS Artifact Workflow` | (chưa có workflow riêng) | — |
| `AC Work Order Workflow` (unified) | **Tách 3 workflow**: `IMM-08 PM Workflow` (PM Work Order), `IMM-09 Repair Workflow` (Asset Repair), `IMM-11 Calibration Workflow` (IMM Asset Calibration) | — |
| `AC Failure Report Workflow` | `IMM-12 Incident Workflow` | `Incident Report` |
| `AC Calibration Record Workflow` | `IMM-11 Calibration Workflow` | `IMM Asset Calibration` |
| `AC Nonconformity Workflow` | (chưa có — `Asset QA Non Conformance` không có workflow JSON) | — |
| `AC CAPA Workflow` | (chưa có — orchestration trong `services/imm12.py`) | — |
| `AC Compliance Case Workflow` | (gộp vào incident + RCA workflow) | — |
| `AC Risk Entry Workflow` | (chưa có — submit-only trên `IMM Lock-in Risk Assessment`) | — |
| `AC Change Control Request Workflow` | (submit-only trên `Firmware Change Request`) | — |
| `AC Asset Movement Workflow` | (submit-only trên `Asset Transfer`; multi-level approval đã được giản lược) | — |
| `AC Decommission/Disposal Workflows` | (state cuối của `AC Asset Lifecycle`: `Decommissioned`) | — |
| `AC Audit / Management Review` | (chưa có) | — |
| (BA chưa có) | `IMM-01 Needs Workflow` | `IMM Needs Request` |
| (BA chưa có) | `IMM-01 Plan Workflow` | `IMM Procurement Plan` |
| (BA chưa có) | `IMM-02 Spec Workflow` | `IMM Tech Spec` |
| (BA chưa có) | `IMM-03 AVL Workflow` | `IMM AVL Entry` |
| (BA chưa có) | `IMM-03 Vendor Eval Workflow` | `IMM Vendor Evaluation` |
| (BA chưa có) | `IMM-03 Decision Workflow` | `IMM Procurement Decision` |
| (BA chưa có) | `IMM-04 Workflow` | `Asset Commissioning` |
| (BA chưa có) | `IMM-12 RCA Workflow` | `IMM RCA Record` |

**Convention thực tế:** workflow name = `IMM-<NN> <Tên>` (không phải `AC <DocType> Workflow`).

---

## 5. Mapping Naming Series: BA gốc → thực tế

| BA gốc | Thực tế |
|---|---|
| `MA-.YYYY.-.####` (Medical Asset) | (theo `naming_series` field; AC Asset không hard-code series tiền tố ở filename) |
| `WO-.YYYY.-.######` (Work Order) | `WO-CM-.YYYY.-.#####` (Asset Repair) **+** `PM-WO-.YYYY.-.#####` (PM Work Order) |
| `PMP-.YYYY.-.####` (PM Plan) | `PMS-{asset_ref}-{pm_type}` (PM Schedule) |
| `CAL-.YYYY.-.######` (Calibration Record) | `CAL-.YYYY.-.#####` (IMM Asset Calibration) |
| `CPL-.YYYY.-.####` (Calibration Plan) | `CAL-SCH-.YYYY.-.#####` (IMM Calibration Schedule) |
| `DOC-.YYYY.-.######` | `DOC-{asset_ref}-{YYYY}-...` (Asset Document) |
| `FR-.YYYY.-.######` (Failure Report) | (Incident Report dùng `naming_series` field) |
| `NC-.YYYY.-.####` (Nonconformity) | `NC-.YY.-.MM.-.#####` (Asset QA Non Conformance) |
| `CAPA-.YYYY.-.####` | (IMM CAPA Record dùng `naming_series` field) |
| `LCE-.YYYY.-.########` (Lifecycle Event) | (Asset Lifecycle Event dùng `naming_series` field) |
| (Wave 2 mới) | `NR-.YY.-.MM.-.#####` (Needs Request); `TS-.YY.-.#####` (Tech Spec); `MB-.YY.-.#####` (Market Benchmark); `LR-.YY.-.#####` (Lock-in Risk); `AVL-.YYYY.-.#####`; `VE-.YY.-.#####` (Vendor Evaluation); `PP-.YY.-.#####` (Procurement Plan); `PD-.YY.-.#####` (Procurement Decision); `SA-.YY.-.#####` (Supplier Audit); `DF-.YYYY.-.#####` (Demand Forecast); `ACC-.YY.-.MM.-.#####` (Asset Commissioning); `FCR-.YYYY.-.#####` (Firmware Change Request); `EAL-{YYYY}-{MM}-...` (Expiry Alert Log) |

---

## 6. Mapping Service / API: BA gốc → thực tế

BA gốc giả định service layer là `assetcore/<domain>/<doctype>/<event>.py` (theo domain folder). Thực tế:

| Layer | Path thực tế | Wave 1 | Wave 2 |
|---|---|---|---|
| Service business logic | `assetcore/services/imm<NN>.py` | `imm04`, `imm05`, `imm08`, `imm09`, `imm11`, `imm12` | `imm00` (foundation), `imm01`, `imm02`, `imm03` |
| API REST endpoints | `assetcore/api/imm<NN>.py` | (cùng module name) | (cùng) |
| Auth | `assetcore/api/auth.py`, `assetcore/services/auth_service.py` | ✓ | — |
| Lifecycle helpers | `assetcore/utils/lifecycle.py` (`log_audit_event`, `create_lifecycle_event`, `verify_audit_chain`) | ✓ | — |
| Permission | `assetcore/permissions.py` (query conditions cho `AC Asset`, `Incident Report`, `Asset Repair`, `PM Work Order`) | ✓ | — |
| Inventory | `assetcore/services/inventory.py`, `api/inventory.py` | ✓ | — |
| Purchase | `assetcore/services/purchase.py`, `api/purchase.py` | — | ✓ |
| Depreciation | `assetcore/services/depreciation.py` | ✓ | — |
| Dashboard | `assetcore/api/dashboard.py` | ✓ | — |
| Layout (FE) | `assetcore/api/layout.py` | ✓ | — |
| Cross-cutting helpers | `assetcore/utils/{api_endpoint, email, helpers, pagination, response}.py` | ✓ | — |

**Hooks lớn (`hooks.py`):**
- `doc_events`: `Asset Commissioning.on_submit` → tạo PM Schedule + Calibration Schedule; `AC Stock Movement` → auto-mark purchase received; `AC Purchase.validate` → bắt link IMM-03 Decision.
- `scheduler_events`: ~16 daily/weekly/monthly tasks (CAPA overdue, contract expiry, document expiry, PM auto-WO, calibration auto-WO, chronic failure detection, low-stock, demand forecast, vendor scorecard, depreciation).

---

## 7. Wave Plan thực tế (so với BA gốc)

BA gốc nói:
- **Wave 1**: IMM-04, 05, 08, 09, 11, 12 (6 module)
- **Wave 1.5**: QMS strengthening
- **Wave 2**: IMM-01, 02, 03, 06, 07, 10, 13, 14, 15, 16

**Thực tế đã ship:**
- **IMM-00 (foundation)** ✓ — fixtures, role profiles, audit trail engine, lifecycle event, SLA policy, depreciation
- **IMM-01 Needs & Plan** ✓ (Wave 2 đã làm xong BE + FE)
- **IMM-02 Spec & Benchmark** ✓
- **IMM-03 AVL & Vendor Eval & Decision** ✓
- **IMM-04 Commissioning** ✓
- **IMM-05 Document Management** ✓
- **IMM-08 Preventive Maintenance** ✓
- **IMM-09 Corrective Maintenance / Repair** ✓
- **IMM-11 Calibration** ✓
- **IMM-12 Incident → RCA → CAPA** ✓
- **Chưa làm**: IMM-06 Training, IMM-07 Performance, IMM-10 Post-market, IMM-13 Stand-down/Transfer (1 phần qua Asset Transfer), IMM-14 Decommission/Disposal, IMM-15 Spare (foundation đã có qua AC Spare Part), IMM-16 Compliance dashboard, IMM-17 Predictive

---

## 8. Quy ước mới (canonical, dùng cho BA pack v3 trở đi)

### 8.1 DocType naming
- `AC <Name>` — foundation/master không gắn module IMM cụ thể.
- `IMM <Name>` — DocType chỉ tồn tại trong module IMM-XX (planning, vendor, calibration record, CAPA, audit chain).
- (no prefix) — DocType cross-module (Incident Report, Asset Document, Asset Repair, PM Work Order, Service Contract).
- **Module Frappe**: luôn là `AssetCore` (single).

### 8.2 Role naming
- `IMM <Name>` — internal user (System Admin, Operations Manager, HTM Engineer, …).
- `Vendor Engineer` — external (no prefix).

### 8.3 Workflow naming
- `IMM-<NN> <Tên>` cho workflow gắn module (vd `IMM-08 PM Workflow`).
- `AC <Tên>` cho workflow shared (vd `AC Asset Lifecycle`).
- State name: tiếng Anh, Title Case có space (`Pending Review`, `In Progress`, `Cannot Repair`) — KHÔNG snake_case như BA gốc gợi ý.
- Action name: tiếng Việt với dấu (`Bắt đầu sửa chữa`, `Phê duyệt`, `Yêu cầu RCA`).

### 8.4 Audit / Lifecycle
- Mọi thay đổi state quan trọng → gọi `assetcore.utils.lifecycle.log_audit_event(...)` (chuỗi SHA-256).
- Sự kiện vòng đời tài sản → gọi `create_lifecycle_event(...)` (tạo `Asset Lifecycle Event`).
- Verify chain qua `verify_audit_chain(asset_name)`.

### 8.5 Service layer
- Logic nghiệp vụ → `assetcore/services/imm<NN>.py`.
- API endpoint → `assetcore/api/imm<NN>.py` (whitelist `@frappe.whitelist()`).
- Controller DocType chỉ làm validate + delegate sang service.

### 8.6 Bỏ qua (KHÔNG dùng nữa)
- ERPNext core (Item, Asset, Supplier, Department, Stock Entry, Purchase Receipt) — không có dependency.
- `AC ` prefix universal — đã thay bằng 3 prefix song song.
- `assetcore.lifecycle.publisher.publish` — thay bằng `assetcore.utils.lifecycle.log_audit_event` + `create_lifecycle_event`.

---

## 9. Cách dùng tài liệu BA hiện tại (legacy)

Khi đọc bất kỳ file nào trong `Phase_*`:

1. **Tên DocType** → tra cứu §2 để map về tên thực tế.
2. **Tên role** → tra cứu §3.
3. **Tên workflow** → tra cứu §4.
4. **Tên naming series** → tra cứu §5.
5. **Hooks ERPNext / sync** → coi như **out of scope** (Frappe-only).
6. **Custom Field trên ERPNext core** → coi như **out of scope**.

Các file đã được rewrite theo reality v3 (đánh dấu trong header `> Reconciled to v3 codebase — 2026-05-07`):

**Foundation / Index:**
- `docs/ba/CLAUDE.md`
- `docs/ba/DocType_Spec_Normalized.md` (banner + redirect)

**Phase 00 — Project Initiation:**
- `Phase_00_Project_Initiation/06_Wave_Plan/Wave_Plan.md`
- `Phase_00_Project_Initiation/07_Glossary_Naming_Convention/Glossary_Naming_Convention.md`

**Phase 01 — Discovery & Business Analysis:**
- `Phase_01_Discovery_Business_Analysis/03_Actor_Map/Actor_Map.md`

**Phase 02 — Solution Architecture:**
- `Phase_02_Solution_Architecture/01_Architecture_Blueprint/Architecture_Blueprint.md`

**Phase 03 — Data & Domain Design:**
- `Phase_03_Data_Domain_Design/05_DocType_Specification_Sheet/DocType_Spec_Wave1.md`
- `Phase_03_Data_Domain_Design/07_Mapping_ERPNext_AssetCore/Mapping_ERPNext_AssetCore.md` (đánh dấu DEPRECATED)

**Phase 04 — Process & Workflow Design:**
- `Phase_04_Process_Workflow_Design/01_Workflow_Specification/Workflow_Specification.md`
- `Phase_04_Process_Workflow_Design/02_Permission_Matrix/Permission_Matrix.md`

**Phase 05 — QMS Governance Design:**
- `Phase_05_QMS_Governance_Design/03_CAPA_Workflow_Spec/CAPA_Workflow_Spec.md`

**Phase 06 — UX Screen & Dashboard:**
- `Phase_06_UX_Screen_Dashboard_Design/05_KPI_KRI_Metric_Dictionary/KPI_KRI_Metric_Dictionary.md`

**Phase 07 — Integration & API:**
- `Phase_07_Integration_API_Design/05_API_Contract_OpenAPI/API_Contract_OpenAPI.md`

Các file phase còn lại (≈103 file) đã được prepend **legacy banner** chỉ dẫn đọc tài liệu này để ánh xạ. Khi cần dùng đến file cụ thể nào → ưu tiên rewrite riêng từng file (đặc biệt Phase 02/03/04/05/06/07 còn các spec con quan trọng: Engine Spec, Domain Model, ERD, Audit Trail Spec, SLA Catalog, Integration Survey, Acceptance Criteria, Sprint Backlog).

---

## 10. Phê duyệt

| Vai trò | Họ tên | Ngày |
|---|---|---|
| Tech Lead |  | 2026-05-07 |
| BA Lead |  | 2026-05-07 |
| QA / QMS Officer |  | 2026-05-07 |
