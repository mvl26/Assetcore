# Role Redesign — Module-Based RBAC (BE + FE)

> Trạng thái: **Design / Analysis** — duyệt trước khi triển khai.
> Ngày: 2026-05-19 · Branch: `feature/hieuc/wave-2` · Tác giả: AssetCore Team
> Quyết định brainstorming: 2-tier Manager/User · 2 lớp role (System / Domain) · hierarchy qua permission union · wipe persona cũ · chỉ 13 module đã build.

---

## 1. Mục tiêu

Thay mô hình **persona role** hiện tại (20 role kiểu `IMM Workshop Lead`, `IMM QA Officer`...) bằng **RBAC chuẩn theo module**, đúng 3 nguyên tắc:

1. **Check Permission, không hardcode Role** — đổi quyền = sửa data (DocPerm / Workflow Transition) ở admin UI, **0 dòng code, 0 deploy**.
2. **Backend là biên bảo mật** — FE chỉ ẩn/hiện nút cho đẹp; mọi chặn thật ở BE.
3. **Cache permission** — resolve 1 lần lúc login, không query role↔permission mỗi click.

Phạm vi tái cấu trúc:

- **BE (Frappe gốc)**: tạo/xóa Role, viết lại DocPerm trên 105 DocType JSON, tầng capability, migration patch.
- **FE (UI hiện tại)**: 1 trang riêng để gán role cho user (kèm mô tả quyền từng role), bỏ mọi hardcode role-name, dùng capability cache.

---

## 2. Hiện trạng & 3 sai lầm đang mắc

| Sai lầm | Nơi vi phạm trong code | Hậu quả |
|---|---|---|
| #1 Hardcode role-name | BE `services/shared/constants.py::Roles.CAN_*` (tuple tên role); FE `stores/auth.ts` (`hasRole(ROLE_SYS_ADMIN)`), `composables/usePermissions.ts` (`roles.includes('IMM QA Officer')`), `directives/permission.ts` (`v-permission="'IMM System Admin'"`), `constants/roles.ts` (~30 `ROLES_*` group), `router/index.ts` (`requiredRoles`) | Thêm/đổi role phải sửa code + deploy lại |
| #2 Tin FE | Một số nút chỉ gate bằng `v-permission`/status string; báo cáo audit 2026-05-13 ghi "BE enforce role, FE gap UX only" → nghĩa là có chỗ BE chưa chặn chặt | Bypass bằng Postman/API trực tiếp |
| #3 Query lặp | Mỗi computed `isXxx` đọc lại `roles` từng lần render | Chưa nghiêm trọng (roles nằm sẵn ở session) nhưng pattern sai khi mở rộng |

**Nguồn chân lý phân quyền hiện tại**: block `permissions` trong từng `assetcore/doctype/<dt>/<dt>.json` (105 file) → Frappe sync vào `tabDocPerm` khi `bench migrate`. `setup/setup_permissions.py` chỉ dọn role legacy. → Tái cấu trúc = viết lại các block `permissions` này.

---

## 2.1. Kiểm kê 54 role trong Frappe & quyết định xử lý

Danh sách `Role List` (`/app/role`) có **54 role**. Phân loại & xử lý:

| Nhóm | Role | Xử lý |
|---|---|---|
| **AssetCore persona (xóa)** — 19 | IMM System Admin, IMM Operations Manager, IMM Department Head, IMM Deputy Department Head, IMM Workshop Lead, IMM QA Officer, IMM Biomed Technician, IMM Technician, IMM Document Officer, IMM Storekeeper, IMM Clinical User, IMM Auditor, IMM Planning Officer, IMM Finance Officer, IMM HTM Engineer, IMM Procurement Officer, IMM Risk Officer, IMM Board Approver, IMM Training Officer | **DELETE** sau khi detach khỏi User + xóa DocPerm + remap workflow |
| **Giữ & tái phạm vi** — 1 | `Vendor Engineer` | **KEEP** — tái dùng làm System Role (cô lập), viết lại DocPerm/scope |
| **AssetCore legacy (xóa)** — đã disabled/sót | HTM Technician, Tổ HC-QLCL, IMM Manager, Kho vật tư, Workshop Manager, Clinical Head, CMMS Admin, QA Risk Team, VP Block2, Workshop Head, Biomed Engineer (= `setup_permissions._LEGACY_ROLES`) | **DELETE** (hiện chỉ disable — nâng thành xóa hẳn trong patch) |
| **App khác sở hữu — REMAP tham chiếu chéo** | `Internal Auditor` — do app **`normcore_dmktkt`** tạo, KHÔNG phải AssetCore, nhưng AssetCore **tham chiếu chéo** trong DocPerm `imm_internal_audit.json`, `imm_compliance_finding.json` và workflow IMM-16 (`workflow.json`, `imm_16_internal_audit.json`) | **KHÔNG xóa** (app khác sở hữu). **Gỡ tham chiếu chéo** trong JSON/workflow AssetCore → thay bằng `Compliance Manager` / `AssetCore Auditor`. Xóa thẳng sẽ vỡ IMM-16 + ảnh hưởng `normcore_dmktkt`. |
| **App khác / Frappe core sở hữu (giữ nguyên)** | `normcore_dmktkt`/`norm_himedic`: Norm Manager, Norm User, Laboratory User, Healthcare Administrator, Internal Auditor. Frappe core: System Manager, Administrator, Guest, All, Website Manager, Report Manager, Newsletter Manager, Workspace Manager... | **KEEP** — không do AssetCore tạo, AssetCore không được xóa role của app khác / Frappe core (CLAUDE.md §19: không modify core). Không đụng tới. |

> `IMM Auditor` (persona, xóa) ≠ `Internal Auditor` (Quality core, giữ) ≠ `AssetCore Auditor` (System Role mới). Ba thực thể khác nhau — tài liệu/đào tạo phải phân biệt.

### Role Profile / Module Profile (xóa hết — không dùng trong mô hình mới)

- **Role Profile (16)**: `AssetCore — System Admin/Operations Manager/Department Head/Department Deputy/Workshop Lead/Biomed Technician/Technician/Clinical User/QA Officer/Auditor/Storekeeper/Document Officer/Planning Officer/Procurement Officer/Vendor Engineer/Training Officer` → **DELETE**.
- **Role Profile legacy**: `IMM - Internal Auditor` (+ các `IMM - *` cũ) — đã có patch `assetcore/patches/v3_1/005_remove_legacy_imm_role_profiles.py`, tái dùng/ mở rộng.
- **Module Profile (3)**: `IMM - Admin`, `IMM - Standard`, `IMM - Vendor` → **DELETE**.
- Mô hình mới **không dùng Role Profile/Module Profile** — gán role trực tiếp qua `Has Role` (Frappe `/app` User form **hoặc** trang FE `/admin/roles`).

---

---

## 3. Kiến trúc role mới

### 3.1. Hai lớp role (tổng 30)

**A. System Roles** — cố định, toàn hệ thống, không gắn module (4):

| Role | Mô tả quyền (hiển thị trên FE) |
|---|---|
| `AssetCore Super Admin` | Toàn quyền: cấu hình hệ thống, quản lý User/Role/Permission, full CRUD mọi DocType. **Umbrella role** — tự động bao trùm role quản trị Frappe (`System Manager`...) qua hook (§6). Đỉnh hierarchy. |
| `AssetCore System User` | **Role nền — mọi user IMM bắt buộc có.** Đăng nhập, vào dashboard, đọc shared-core (Asset/Location/Department/Model read-only). Thay cho `hasAnyImmRole` cũ. |
| `AssetCore Auditor` | Chỉ đọc **toàn bộ** DocType + đọc `imm_audit_trail`. Không ghi. |
| `Vendor Engineer` | Bên thứ ba, **cô lập dữ liệu**: chỉ Work Order/Asset được phân công (qua User Permission + `permission_query_conditions`). |

> ⚠️ `AssetCore System User` (Role) ≠ Frappe `user_type = "System User"`. Trùng khái niệm, tài liệu/đào tạo phải nói rõ. Mọi user nội bộ đặt `user_type = "System User"` (Frappe) **và** gán Role `AssetCore System User`.

**B. Domain / Business Roles** — theo module, 13 × 2 = 26:

| Module | Domain word | Manager | User |
|---|---|---|---|
| IMM-00 Dữ liệu nền | **Data** | `Data Manager` | `Data User` |
| IMM-01 Nhu cầu & Dự toán | **Needs** | `Needs Manager` | `Needs User` |
| IMM-02 Thông số kỹ thuật | **Spec** | `Spec Manager` | `Spec User` |
| IMM-03 NCC & Mua sắm | **Procurement** | `Procurement Manager` | `Procurement User` |
| IMM-04 Lắp đặt & Nghiệm thu | **Commissioning** | `Commissioning Manager` | `Commissioning User` |
| IMM-05 Hồ sơ | **Document** | `Document Manager` | `Document User` |
| IMM-06 Đào tạo | **Training** | `Training Manager` | `Training User` |
| IMM-08 Bảo trì định kỳ | **PM** | `PM Manager` | `PM User` |
| IMM-09 Sửa chữa | **Repair** | `Repair Manager` | `Repair User` |
| IMM-11 Hiệu chuẩn | **Calibration** | `Calibration Manager` | `Calibration User` |
| IMM-12 Bảo trì khắc phục | **Corrective** | `Corrective Manager` | `Corrective User` |
| IMM-15 Tồn kho phụ tùng | **Inventory** | `Inventory Manager` | `Inventory User` |
| IMM-16 Tuân thủ / QMS | **Compliance** | `Compliance Manager` | `Compliance User` |

Module chưa build (IMM-07, 10, 13, 14, 17) → thêm role khi module ra đời (Performance, PostMarket, Disposition, Decommission, Analytics).

### 3.2. Ngữ nghĩa quyền

| Tier | DocPerm trên doctype sở hữu | Workflow |
|---|---|---|
| `<Domain> User` | read, write, create, print, email | transition các bước **thao tác thường** (không phải approval gate) |
| `<Domain> Manager` | read, write, create, **delete, submit, cancel, amend**, print, email, report, export | transition cả bước **duyệt/hủy** |
| `AssetCore System User` | read shared-core | — |
| `AssetCore Auditor` | read + report + export **mọi** doctype | — |
| `AssetCore Super Admin` | full mọi doctype | mọi transition |

### 3.3. Role Hierarchy — qua **permission union**, KHÔNG nest tên role

Frappe không có role inheritance gốc. Hierarchy biểu diễn ở tầng **permission**, không lồng tên role trong code:

- **Trong module**: DocPerm của `Manager` là **superset chặt** của `User`. → Gán `Manager` là tự đủ, không cần kèm `User`.
- **Toàn cục**: `Super Admin` ⊇ tất cả; `System User` là sàn (mọi domain role mặc nhiên kèm — grid FE auto-tick, đào tạo nêu rõ).
- **Capability resolution tự có hierarchy**: `can('pm.write')` = true nếu *bất kỳ* role của user có DocPerm cấp nó. Vì `Manager` ⊇ `User`, cấp cao tự bao cấp thấp — đúng RBAC (union quyền).
- **Metadata `rank`** (chỉ phục vụ UX grid, KHÔNG dùng để enforce): `SuperAdmin 100 > Manager 50 > User 10 > SystemUser 0`.

---

## 4. Tầng Capability (mới) — Permission, không Role

### 4.1. Nguyên tắc

Code (BE + FE) **không bao giờ** so tên role. Code hỏi capability. Binding capability → role nằm trong **data** (DocPerm + Workflow Transition), sửa ở `/app` không deploy.

### 4.2. CAPABILITY_MAP (BE — `assetcore/services/shared/rbac.py`)

```python
# capability_key -> (doctype, ptype)  hoặc  (doctype, ptype, "workflow:<transition>")
CAPABILITY_MAP = {
  # CRUD theo module — resolve qua frappe.has_permission(doctype, ptype)
  "pm.read":     ("PM Work Order", "read"),
  "pm.write":    ("PM Work Order", "write"),
  "pm.create":   ("PM Work Order", "create"),
  "pm.delete":   ("PM Work Order", "delete"),
  "pm.submit":   ("PM Work Order", "submit"),
  # Action cap — gate bằng workflow transition state + has_permission, KHÔNG role-name
  "pm.reschedule":        ("PM Work Order", "write"),
  "incident.acknowledge": ("Incident Report", "write"),
  "cal.send_lab":         ("IMM Asset Calibration", "write"),
  "doc.approve":          ("Asset Document", "submit"),
  "capa.close":           ("IMM CAPA Record", "submit"),
  "data.admin":           ("IMM Device Model", "delete"),
  # ... 1 entry / capability, sinh tự động cho 13 module
}
```

### 4.3. API BE

```python
# assetcore/services/shared/rbac.py
def can(cap: str, doc=None) -> bool:
    dt, ptype, *_ = CAPABILITY_MAP[cap]
    return frappe.has_permission(dt, ptype, doc=doc)

def require(cap: str, doc=None) -> None:
    if not can(cap, doc):
        frappe.throw(_("Không đủ quyền: {0}").format(cap), frappe.PermissionError)

def get_capabilities() -> dict[str, bool]:
    """Resolve toàn bộ cap cho user hiện tại — cache theo user."""
    user = frappe.session.user
    key = f"ac_caps::{user}"
    cached = frappe.cache().get_value(key)
    if cached is not None:
        return cached
    caps = {c: can(c) for c in CAPABILITY_MAP}
    frappe.cache().set_value(key, caps, expires_in_sec=3600)
    return caps
```

- Cache invalidate: hook `on_update` của `Has Role` / `User` / `Custom DocPerm` → `frappe.cache().delete_value("ac_caps::*")` (theo user liên quan).
- **Mọi** `@frappe.whitelist` của service/api Wave 1+2 bọc `rbac.require("<cap>")` ở đầu (Sai lầm #2). Không method nào đọc `frappe.get_roles()` để so tên.

### 4.4. Endpoint FE

`assetcore/api/auth.py::get_capabilities` (whitelisted) → trả `{"pm.write": true, "incident.acknowledge": false, ...}`. FE gọi **1 lần** sau login, cache Pinia (persisted) + rehydrate từ `frappe.boot` nếu có (Sai lầm #3).

---

## 5. Doctype → Module → DocPerm (105 DocType)

`U` = `<Domain> User` (read/write/create) · `M` = `<Domain> Manager` (+delete/submit/cancel/amend) · `SU` = System User (read) · `AU` = Auditor (read) · `SA` = Super Admin (full, ngầm định cho mọi dòng).

### 5.1. Shared-core (read cho mọi `*User`+`*Manager`+SU+AU; write/create theo module sở hữu vòng đời)

| DocType | Owner write |
|---|---|
| `ac_asset` | Commissioning (tạo) · PM/Repair/Calibration/Corrective (write trạng thái) |
| `asset_lifecycle_event` | mọi module sinh event (create) — không sửa/xóa (chỉ M xóa) |
| `ac_asset_depreciation_schedule`, `ac_asset_downtime_log` | Data M / Corrective |

### 5.2. Map theo domain

| Domain | DocType |
|---|---|
| **Data** (IMM-00) | ac_asset_category, ac_department, ac_location, ac_supplier, ac_uom, ac_uom_conversion, imm_device_model, imm_device_spare_part, ac_authorized_technician, service_contract, service_contract_asset, required_document_type, imm_sla_policy |
| **Needs** (IMM-01) | imm_needs_request, needs_priority_scoring, imm_demand_forecast, forecast_driver, budget_estimate_line, imm_procurement_plan, procurement_plan_line |
| **Spec** (IMM-02) | imm_tech_spec, tech_spec_document, tech_spec_requirement, imm_market_benchmark, benchmark_candidate, infra_compatibility_item, imm_lock_in_risk_assessment, lock_in_risk_item |
| **Procurement** (IMM-03) | imm_vendor_evaluation, vendor_eval_candidate, vendor_eval_criterion, imm_vendor_scorecard, imm_avl_entry, imm_procurement_decision, imm_supplier_audit, vendor_quotation_line, vendor_cert, ac_purchase, ac_purchase_item, ac_purchase_device_item |
| **Commissioning** (IMM-04) | asset_commissioning, commissioning_checklist, commissioning_document_record, asset_transfer |
| **Document** (IMM-05) | asset_document, document_request, expiry_alert_log |
| **Training** (IMM-06) | imm_training_program, imm_training_session, imm_training_participant, imm_trainer, imm_user_competency, imm_competency_alert_log, imm_competency_gap_report, imm_gap_detail_row |
| **PM** (IMM-08) | pm_work_order, pm_schedule, pm_task_log, pm_checklist_template, pm_checklist_item, pm_checklist_result |
| **Repair** (IMM-09) | asset_repair, repair_checklist, spare_parts_used, firmware_change_request |
| **Calibration** (IMM-11) | imm_asset_calibration, imm_calibration_schedule, imm_calibration_measurement |
| **Corrective** (IMM-12) | incident_report, imm_rca_record, imm_rca_five_why_step, imm_rca_related_incident, asset_qa_non_conformance |
| **Inventory** (IMM-15) | ac_spare_part, ac_spare_part_stock, ac_stock_movement, ac_stock_movement_item, ac_warehouse, imm_spare_allocation, imm_spare_allocation_item, imm_spare_alternative, imm_spare_batch, imm_spare_part_forecast, imm_spare_forecast_item, imm_critical_spare_watchlist, imm_stock_cycle_count, imm_stock_cycle_count_item, imm_cycle_count_item |
| **Compliance** (IMM-16) | imm_compliance_finding, imm_compliance_rule, imm_compliance_scorecard, imm_scorecard_department_row, imm_scorecard_module_row, scorecard_kpi_row, imm_capa_record, imm_capa_action_step, imm_internal_audit, imm_audit_checklist_item, audit_finding, imm_management_review, imm_mr_attendee, imm_mr_output_action |
| **Audit-only** | imm_audit_trail → chỉ `AssetCore Auditor` + `Super Admin` read; không ai write (ghi qua code `ignore_permissions`) |

> Child table (rows) kế thừa quyền parent — DocPerm đặt theo parent doctype; child chỉ cần role giống parent để Frappe cho phép thao tác inline.

---

## 6. Phạm vi sửa — BE

| # | File / hành động |
|---|---|
| B1 | **105 DocType JSON** `assetcore/doctype/<dt>/<dt>.json` — viết lại block `permissions` theo §5 (script sinh tự động từ map domain để tránh sai sót thủ công) |
| B2 | `assetcore/services/shared/rbac.py` **(mới)** — `CAPABILITY_MAP`, `can()`, `require()`, `get_capabilities()` + cache invalidate hooks |
| B3 | `assetcore/services/shared/constants.py` — `class Roles` còn 30 hằng tên (cho fixture/migration); **xóa `CAN_*`**; thêm `ROLE_RANK`, `SYSTEM_ROLES`, `DOMAIN_ROLES` |
| B4 | `assetcore/api/auth.py` — endpoint `get_capabilities` (whitelisted, cache) |
| B5 | Refactor mọi service/api Wave 1+2 đang dùng `Roles.CAN_*` / `frappe.get_roles()` so tên → `rbac.require("<cap>")` |
| B6 | `assetcore/hooks.py` — `_IMM_ROLES` = 30 role mới; bỏ `_IMM_ROLE_PROFILES`, `_IMM_MODULE_PROFILES` khỏi `fixtures`; thêm cache-invalidate vào `doc_events`; thêm `Has Role` hook umbrella (gán/gỡ `AssetCore Super Admin` ↔ `System Manager`, idempotent) |
| B7 | `fixtures/role.json` regenerate (30 role + mô tả); **xóa** `fixtures/role_profile.json`, `fixtures/module_profile.json` |
| B8 | `setup/setup_role_profiles.py` — xóa (không còn Role Profile/Module Profile); `setup/setup_permissions.py` — `_LEGACY_ROLES` += 19 persona; **xóa hẳn** thay vì chỉ `disabled=1` |
| B9 | **Patch** `patches/v3_x/0xx_module_role_redesign.py`: (1) detach 19 persona + 11 legacy khỏi mọi `Has Role`; (2) `frappe.delete_doc` 19 persona Role + 11 legacy Role + 16 Role Profile + legacy Role Profile + 3 Module Profile; (3) xóa DocPerm/Custom DocPerm tham chiếu persona/legacy; (4) **KHÔNG** xóa role do `normcore_dmktkt`/`norm_himedic` hoặc Frappe core sở hữu (`Internal Auditor`, `Norm Manager/User`, `Laboratory User`, `Healthcare Administrator`, `System Manager`...); (5) `Vendor Engineer` giữ — chỉ viết lại DocPerm/scope; (6) đăng ký `patches.txt`; tái dùng `v3_1/005_remove_legacy_imm_role_profiles.py`. Role mới do JSON/fixture tạo khi migrate. |
| B10 | Workflow `fixtures/workflow.json` + `workflow_action_master.json` + `assetcore/workflow/*.json` — remap `allowed`/`allow_edit` từ persona **và `Internal Auditor`** → `<Domain> Manager/User` / `AssetCore Auditor`. Đặc biệt IMM-16 (`imm_16_internal_audit.json`, `imm_internal_audit.json`, `imm_compliance_finding.json` đang tham chiếu `Internal Auditor`). Bỏ sót → workflow không transition. |
| B11 | `tests/` — thay mọi tên persona hard-code bằng role/capability mới; thêm test `rbac.can/require`, test DocPerm Manager⊇User, test endpoint `get_capabilities`, test Vendor isolation |

### 6.1. 4 mặt thiết lập role trong Frappe — xử lý từng mặt (BE) & ánh xạ FE

| Mặt Frappe (`/app`) | Hiện tại | Mô hình mới — BE | Mô hình mới — FE |
|---|---|---|---|
| **Role** (`/app/role`) | 54 role (19 persona + Vendor + legacy + core) | Xóa 19 persona + 11 legacy + Role Profile/Module Profile (B8/B9). Giữ Vendor (re-scope), core, Frappe system. Tạo 30 role mới qua fixture (B7) | Trang `/admin/roles` phần 1: catalog 30 role + **mô tả quyền** (chỉ đọc) |
| **Role Profile** (`/app/role-profile`) | 16 `AssetCore — *` + legacy `IMM - *` | **Xóa hết** — không dùng (B8/B9). Gán role trực tiếp | Không hiển thị Role Profile trên FE — bỏ khái niệm |
| **Role Permission Manager** (`/app/permission-manager`) ↔ DocPerm | DocPerm trong 105 JSON theo persona | Viết lại 105 JSON theo `<Domain> Manager/User` + System roles (B1). `permission-manager` của Frappe vẫn chỉnh tay được (cùng `tabCustom DocPerm`) → admin tinh chỉnh runtime không deploy | Không build lại UI DocPerm trên FE — dùng Frappe `/app/permission-manager` (BE). FE chỉ *đọc* kết quả qua capability |
| **Gán role cho User** (`Has Role` trong User form) | Gán persona / Role Profile | Gán trực tiếp 30 role qua `Has Role` (B-none: data) | Trang `/admin/roles` phần 2: chọn user → grid module×(Manager/User) + System roles → ghi `Has Role` qua `api/user.py`. **Đồng bộ 2 chiều** với Frappe User form (cùng bảng) |

> Nguyên tắc: **Role + DocPerm = data**, sửa được ở cả Frappe `/app` (BE) lẫn trang FE `/admin/roles`, không lệch nguồn vì cùng `tabRole`/`tabHas Role`/`tabCustom DocPerm`. Code chỉ đọc qua capability (§4) — đổi quyền không cần deploy.

**Quyết định (đã chốt)**: `AssetCore Super Admin` là role **bao trùm** — tự động kèm các role quản trị Frappe (`System Manager`, và các core role cần để quản lý User/Role/Permission/Workspace). Triển khai:

- Hook `Has Role` `after_insert`/`on_update`: khi user được gán `AssetCore Super Admin` → tự thêm `System Manager` (idempotent); khi gỡ → gỡ `System Manager` nếu user không có nguồn khác.
- Patch B9 backfill: mọi user đang có `AssetCore Super Admin` được bổ sung `System Manager`.
- Ý nghĩa: gán **1 role** `AssetCore Super Admin` là đủ toàn quyền cả AssetCore lẫn quản trị Frappe — không phải tick thủ công nhiều role. Đây là "umbrella role" duy nhất; các role khác KHÔNG bao trùm role Frappe.

---

## 7. Phạm vi sửa — FE

### 7.1. Trang quản lý Role/User (yêu cầu chính của user)

**Trang mới**: `/admin/roles` — `frontend/src/views/admin/RoleAdminView.vue` (guard `meta.requiredCapabilities = ['data.admin']` hoặc Super Admin).

Gồm 2 phần:

1. **Catalog role + giải thích quyền** — bảng 30 role: tên, lớp (System/Domain), module, `rank`, mô tả "role này làm được gì" (lấy từ §3.1/§3.2). Read-only, để admin hiểu trước khi gán.
2. **Gán role cho user** — chọn user → **grid module × (Manager / User)** + nhóm System Roles (checkbox). Tick Manager auto-hiển thị bao User (theo `rank`, chỉ UX). Lưu → ghi thẳng `Has Role` của User qua API (`assetcore/api/user.py`). Cùng Role records → set được cả ở Frappe `/app` lẫn FE.

> Vì là cùng `Has Role`/`Role`/`DocPerm`, admin có thể thiết lập **song song**: Frappe `/app` (Role List, Role Permission Manager, User form) **hoặc** trang FE này — không lệch nguồn.

### 7.2. Bỏ hardcode role-name, chuyển sang capability

| # | File | Thay đổi |
|---|---|---|
| F1 | `frontend/src/constants/roles.ts` | Còn: danh mục 30 role (name, label, layer, module, rank, **description**) cho catalog/grid. **Xóa** mọi `ROLES_*` group, `ALL_IMM_ROLES`, `Roles.CAN_*` dùng cho logic |
| F2 | `frontend/src/stores/auth.ts` | Thêm `capabilities: Record<string,boolean>`; bỏ `isSystemAdmin/isQAOfficer/...`; giữ `roles` chỉ để hiển thị. Fetch `get_capabilities` 1 lần sau login, persist |
| F3 | `frontend/src/composables/useCapabilities.ts` **(mới)** | `can('pm.write')` đọc từ store cache |
| F4 | `frontend/src/composables/usePermissions.ts` | Deprecate → wrap `useCapabilities` (giữ tạm để không vỡ import, refactor dần) |
| F5 | `frontend/src/directives/permission.ts` → `v-can` | `v-can="'pm.delete'"` đọc capability; bỏ `v-permission` role-name |
| F6 | `frontend/src/router/index.ts` | `meta.requiredRoles` → `meta.requiredCapabilities`; guard check capability cache |
| F7 | `frontend/src/constants/modules.ts` | `roles` mỗi card → `requiredCapabilities: ['<domain>.read']` |
| F8 | 14 file FE import `constants/roles` (`api/user.ts`, các `views/**`, `ApprovalPanel.vue`...) | Đổi sang `useCapabilities().can(...)` |
| F9 | `frontend/src/api/auth.ts` | Thêm `fetchCapabilities()` |

**Nguyên tắc FE (in đậm trong UI guideline)**: ẩn nút theo `can()` chỉ để UX. **Không** coi đó là bảo mật — BE `rbac.require` mới là chốt chặn. Mọi action gọi API; BE từ chối nếu thiếu cap dù FE có lỡ hiện nút.

---

## 8. Migration (wipe — không auto-map)

Site dev/test chưa go-live → chọn wipe sạch:

1. Patch B9 detach 19 persona + 11 legacy khỏi User → xóa 19 persona + 11 legacy Role + 16 Role Profile + legacy Role Profile + 3 Module Profile + DocPerm liên quan. **Giữ** `Vendor Engineer` (re-scope) và mọi role do app khác (`normcore_dmktkt`/`norm_himedic`) hoặc Frappe core sở hữu.
2. `bench migrate` → JSON/fixture tạo 30 role mới + DocPerm mới.
3. Admin gán lại quyền qua trang FE `/admin/roles` hoặc Frappe `/app`.
4. **Không** auto-assign cho user cũ — admin chủ động gán.

Rollback: revert branch + `bench migrate` (role cũ tái tạo từ fixture cũ ở commit trước). Khuyến nghị backup DB trước patch (`bench --site <site> backup`).

---

## 9. Thứ tự triển khai (checklist)

```
[ ] 0. bench backup + tạo branch con
[ ] 1. B3 constants.py (Roles 30, ROLE_RANK, layers) — SOT tên role
[ ] 2. B2 rbac.py + CAPABILITY_MAP (test trước — TDD §17 CLAUDE.md)
[ ] 3. B1 script sinh permissions block cho 105 JSON theo §5
[ ] 4. B5 refactor service/api → rbac.require (bỏ CAN_*)
[ ] 5. B4 api/auth.get_capabilities + cache invalidate (B6 doc_events)
[ ] 6. B10 remap workflow fixtures
[ ] 7. B7/B8 fixtures + setup cleanup
[ ] 8. B9 migration patch + patches.txt
[ ] 9. bench migrate (site test) → verify 30 role, DocPerm Manager⊇User
[ ] 10. B11 BE tests pass (rbac, DocPerm, vendor isolation, workflow)
[ ] 11. F1–F9 FE refactor + trang /admin/roles
[ ] 12. FE build + Playwright: gán role qua grid, verify ẩn nút + BE chặn khi bypass
[ ] 13. Cập nhật docs/imm-00 (RBAC), CLAUDE.md nếu phát sinh pattern
```

---

## 10. Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Workflow vỡ do `allowed` role persona | B10 remap đồng thời; test smoke từng workflow |
| 105 JSON sửa tay sai sót | B1 sinh bằng script từ map domain, review diff |
| Endpoint/dashboard/report lọc theo persona role | Grep `frappe.get_roles`, tên persona; refactor B5 |
| FE còn import `ROLES_*` rải rác | F8 grep toàn bộ `constants/roles`; CI typecheck |
| Cache cap stale sau khi đổi role | Invalidate ở `Has Role`/`DocPerm` on_update (B6) |
| Super Admin không quản được User/Role | Đã chốt: umbrella role auto-kèm `System Manager` qua hook `Has Role` (§6) |

---

## 11. Định nghĩa hoàn thành (DoD)

- 30 role tồn tại; 19 persona + 11 legacy + Role/Module Profile xóa sạch; role do `normcore_dmktkt`/`norm_himedic`/Frappe core sở hữu (`Internal Auditor`, `Norm Manager/User`, `Laboratory User`, `Healthcare Administrator`, `System Manager`...) còn nguyên; `Vendor Engineer` re-scope (kiểm `tabRole`, `tabHas Role`, `tabCustom DocPerm`).
- `grep -r "IMM System Admin\|CAN_\|hasRole(\|v-permission" assetcore frontend/src` = 0 kết quả logic (chỉ còn catalog/migration).
- Mọi whitelisted method có `rbac.require`; test bypass (gọi API thiếu cap) bị từ chối.
- Trang FE `/admin/roles`: xem mô tả role + gán role grid; thay đổi phản ánh ở Frappe `/app` và ngược lại.
- BE tests + Playwright pass; `frappe.has_permission` là chốt chặn duy nhất.
