# 02 — Phân tích thiết kế nghiệp vụ — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — cung cấp cho toàn bộ hệ thống |
| Owner | BA + System Architect |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |
| Chuẩn tham chiếu | WHO HTM 2025, NĐ 98/2021/NĐ-CP, ISO 13485:2016, ISO/IEC 17025 |
| Phiên bản | 0.0.2 |
| Cập nhật | 2026-06-03 |
| Trạng thái | **Live ✅** — BE foundation + scheduler + service layer đã implement; FE đang cuốn chiếu. Depreciation RC-03/04/05 (Self-Correction kế thừa luật khấu hao Category→Asset) bổ sung 2026-06-03. |

---

# Phần I — Module Overview

## I.0. Khảo sát hiện trạng (As-Is)

IMM-00 là **foundation layer** — không có quy trình "as-is" tương ứng tại bệnh viện theo nghĩa nghiệp vụ đơn lẻ. Khảo sát hiện trạng được tổng hợp ở mức **lớp kiến trúc nền** (theo `docs/architecture/Ho_so_kien_truc_IMMIS.md` §"Lớp kiến trúc"):

| Lớp kiến trúc hiện trạng | Tình trạng phổ biến tại đơn vị y tế VN | Khoảng trống IMM-00 phải lấp |
|---|---|---|
| Lớp người dùng | Excel/giấy phân tán theo khoa; quyền hạn không bám actor thật | Cần portal nội bộ + RBAC theo 30 roles (4 System + 26 Domain = 13 module × Manager/User) |
| Lớp workflow & dịch vụ | Workflow ngầm, không có engine; không SLA, không audit | Workflow + SLA + audit trail bắt buộc cho mọi state mutation |
| Lớp nghiệp vụ | Module rời rạc, không liên kết lifecycle | 17 module IMM-01→17 chia 4 khối, đều phụ thuộc IMM-00 |
| Lớp dữ liệu | Item/Asset/Vendor/Document gộp lẫn lộn | Tách đúng AC Asset / IMM Device Model / AC Supplier / Document repo |
| Lớp tích hợp | Manual export Excel sang HIS/LIS | OpenAPI + FHIR-ready |
| Lớp phân tích & điều hành | Báo cáo tĩnh, không drill-down | Dashboard có drill-down về bản ghi nguồn |
| Lớp QMS & governance | QMS giấy, không change-control | QC → PR → WI → BM → HS → KPI điện tử + CAPA + audit |

> Nguồn: `docs/architecture/Ho_so_kien_truc_IMMIS.md` (bảng "Lớp kiến trúc" line ~232–240). *(Khảo sát chi tiết theo từng đơn vị: cần khảo sát baseline)*

## I.1. Đặc điểm đặc biệt của IMM-00

IMM-00 **không phải** module nghiệp vụ thông thường theo Wave 1/2/3. Đây là **foundation layer tự chứa** — lớp nền tảng mà tất cả 17 module IMM-xx đều phụ thuộc vào. IMM-00:

- Cung cấp toàn bộ DocType lõi (AC Asset, AC Supplier, AC Location, AC Department, AC Asset Category)
- Định nghĩa domain catalog (IMM Device Model, IMM SLA Policy)
- Cung cấp governance records (IMM Audit Trail, IMM CAPA Record, Asset Lifecycle Event, Incident Report)
- Xuất shared service functions được gọi bởi IMM-04, IMM-08, IMM-09, IMM-11, IMM-12, IMM-13
- Thiết lập vai trò (30 roles = 4 System + 26 Domain), scheduler jobs (4 daily), và permission query

Nguyên tắc kiến trúc bắt buộc: AssetCore **chỉ phụ thuộc Frappe Framework v15** — không cần ERPNext. Các DocType core được thiết kế theo mẫu schema của ERPNext nhưng **tái tạo native** với prefix `AC` / `IMM`, không extend hay link sang DocType của ERPNext.

## I.2. Trạng thái triển khai (Live vs. Planned)

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| 5 Core DocTypes (AC prefix) | **Live ✅** | AC Asset, AC Supplier, AC Location, AC Department, AC Asset Category đã có trong `assetcore/assetcore/doctype/` |
| 6 Governance DocTypes (IMM prefix) | **Live ✅** | IMM Audit Trail, IMM CAPA Record, Asset Lifecycle Event, Incident Report, IMM Device Model, IMM SLA Policy |
| 5 Inventory DocTypes (v4) | **Live ✅** | AC Warehouse, AC Spare Part, AC Spare Part Stock, AC Stock Movement (+ Item child), AC Stock Movement Item |
| Services (imm00.py) | **Live ✅** | 22 public functions implement (transfer, GMDN, scheduler, KPI rollup) |
| Role fixtures | **Live ✅** | 30 roles (4 System + 26 Domain = 13 module × Manager/User) seed qua `fixtures/role.json`; nguồn canonical: `services/shared/constants.py::Roles` |
| Permission query | **Live ✅** | `permission.py` cho AC Asset (scoped theo `responsible_technician`) |
| Scheduler | **Live ✅** | 5 daily IMM-00 jobs + weekly + monthly (xem §III.7) |
| FE shell + views | **Partial** | 12+ views built (asset/ ×10, audit/ ×2, master-data/ ×2); phần còn lại cuốn chiếu |

> Wave 1 (IMM-04/08/09/11/12) đã refactor sang AC Asset registry; không còn phụ thuộc ERPNext Asset.

## I.3. Vị trí trong kiến trúc WHO HTM lifecycle

| Phase | Chạm? | Ghi chú |
|---|---|---|
| Needs (IMM-01→03) | ✅ | AC Asset, AC Supplier làm master data |
| Procurement (IMM-01→03) | ✅ | AC Supplier là nguồn NCC |
| Install (IMM-04→06) | ✅ | `create_lifecycle_event("commissioned")`, validate_asset_for_operations() |
| Operation | ✅ | AC Asset registry, lifecycle_status state machine |
| **Maintenance (IMM-08/09/11/12)** | ✅ **xuyên suốt** | `get_sla_policy()`, `transition_asset_status()`, `create_capa()` |
| Decommission (IMM-13→14) | ✅ | `transition_asset_status(→ Decommissioned)`, suspend schedules |

## I.4. Stakeholders & Actors

> Canonical role catalog: **30 roles** = 4 System + 26 Domain (13 module × Manager/User). Nguồn: `assetcore/fixtures/role.json` + `assetcore/services/shared/constants.py::Roles`. Các persona role cũ (IMM System Admin, IMM Department Head, IMM Workshop Lead, Trưởng khoa, KTV HTM, v.v.) đã bị thay thế qua patch `v3_2.001_module_role_redesign`.

### System roles (4)

| Role | Mục đích |
|---|---|
| `AssetCore Super Admin` | Toàn quyền, bao trùm Frappe System Manager |
| `AssetCore System User` | Role nền: đăng nhập, dashboard, đọc shared-core |
| `AssetCore Auditor` | Chỉ đọc toàn bộ + audit trail |
| `Vendor Engineer` | Bên thứ ba, cô lập theo WO/Asset được phân công |

### Domain roles (26 = 13 module × Manager/User)

| Module | Manager role | User role |
|---|---|---|
| IMM-00 (Dữ liệu nền) | `Data Manager` | `Data User` |
| IMM-01 (Nhu cầu) | `Needs Manager` | `Needs User` |
| IMM-02 (Tech Spec) | `Spec Manager` | `Spec User` |
| IMM-03 (NCC & Mua sắm) | `Procurement Manager` | `Procurement User` |
| IMM-04 (Lắp đặt) | `Commissioning Manager` | `Commissioning User` |
| IMM-05 (Hồ sơ) | `Document Manager` | `Document User` |
| IMM-06 (Đào tạo) | `Training Manager` | `Training User` |
| IMM-08 (PM) | `PM Manager` | `PM User` |
| IMM-09 (Sửa chữa) | `Repair Manager` | `Repair User` |
| IMM-11 (Hiệu chuẩn) | `Calibration Manager` | `Calibration User` |
| IMM-12 (BT khắc phục / Incident) | `Corrective Manager` | `Corrective User` |
| IMM-15 (Tồn kho) | `Inventory Manager` | `Inventory User` |
| IMM-16 (Compliance) | `Compliance Manager` | `Compliance User` |

## I.5. Scope

**In-scope:**
- 27 DocTypes foundation IMM-00 (5 core + 6 governance + 5 inventory + 11 child/support) — verified vs `assetcore/assetcore/doctype/`
- Lifecycle state machine cho AC Asset.lifecycle_status (8 states: Draft, Commissioned, Active, Under Maintenance, Under Repair, Calibrating, Out of Service, Decommissioned)
- Audit Trail bất biến với SHA-256 chain
- CAPA workflow (Open → In Progress → Pending Verification → Closed / Overdue)
- SLA lookup engine theo priority × risk_class
- Incident Report → trigger Repair WO + CAPA
- 5 daily scheduler jobs + 1 monthly (`rollup_asset_kpi`)
- 30 role fixtures (4 System + 26 Domain = 13 module × Manager/User) + permission query
- 107 whitelisted REST endpoints trong `api/imm00.py`

**Out-of-scope (defer sang giai đoạn sau):**
- AC Purchase Request (mua phụ tùng khi tồn < min) — Wave 2
- AC Asset Component (linh kiện gắn trên thiết bị có SN riêng) — Wave 2
- Work Order DocType (PM/CM/Cal) — thuộc IMM-08/09/11
- FHIR/HIS integration — IMM-15/16/17
- FE form builders ngoài AC Asset — làm cuốn chiếu theo từng IMM-xx

## I.6. KPI và mục tiêu hệ thống

| KPI | Định nghĩa | Target |
|---|---|---|
| Audit trail coverage | % action có IMM Audit Trail entry | 100% mọi mutation |
| SLA policy coverage | % Work Order lookup được SLA | 100% (fallback is_default) |
| Scheduler reliability | 4 jobs idempotent, retry ≤ 3 lần | 0 missed run / ngày |
| Permission accuracy | IMM Technician không thấy asset không được gán | 100% enforce |
| Hash chain integrity | `verify_audit_chain` trả `{valid: true}` | 100% |
| Registration expiry alert | Cảnh báo BYT 90/60/30/7 ngày trước hạn | 100% coverage active assets |

## I.7. Ràng buộc Compliance

| Quy định | Yêu cầu áp lên module | Doc tham chiếu |
|---|---|---|
| NĐ 98/2021 | Hồ sơ thiết bị ≥ 7 năm; truy xuất nguồn gốc đầy đủ | Điều 4, 28, 31 |
| WHO HTM 2025 | CM WO bắt buộc; traceability toàn lifecycle | §3.2.3, §5.4 |
| ISO 13485:2016 §7.5.9 | Hồ sơ immutable (audit trail không xóa/sửa) | §7.5.9 |
| ISO 13485:2016 §8.5 | CAPA bắt buộc cho sự cố và tái hỏng | §8.5.2, §8.5.3 |
| ISO/IEC 17025 | Lab hiệu chuẩn phải có chứng chỉ | §6.2.1 |

## I.8. Rủi ro & giảm thiểu (Risk)

Vì IMM-00 là foundation cho 17 module downstream, mọi sai sót lan truyền toàn hệ thống. Các nhóm rủi ro chính:

| ID | Rủi ro | Tác động | Giảm thiểu |
|---|---|---|---|
| RISK-00-01 | Hash chain audit trail bị phá vỡ (insert sai, lỗi trigger) | Mất tính bất biến → vi phạm ISO 13485 §7.5.9, NĐ98 | `verify_audit_chain` chạy daily; controller `IMMAuditTrail` chặn update/delete |
| RISK-00-02 | `transition_asset_status()` bị bypass (sửa `lifecycle_status` trực tiếp) | State machine vỡ; IMM-08/09/11/12 đọc sai trạng thái | BR-00-02 enforce qua service-only mutation; permission deny cho field |
| RISK-00-03 | Scheduler job miss run (server down, bench scheduler fail) | CAPA Overdue không được flag, expiry không cảnh báo | NFR-00-12 idempotent + retry ≤3; alert email Admin khi fail |
| RISK-00-04 | Permission Query lỗi → IMM Technician thấy asset không được gán | Vi phạm RBAC, lộ dữ liệu | NFR-00-07 + test TC-S permission gate trong 07_Testing_QA |
| RISK-00-05 | DocType migration phá schema downstream | IMM-04→17 break chain | Patch versioned + backup full DB trước migrate (08_Deployment) |
| RISK-00-06 | Phụ thuộc Frappe v15 thay đổi API | Refactor lan rộng | Pin version Frappe; smoke test mỗi upgrade minor |
| RISK-00-07 | Override `gmdn_code` tại Device Model gây lệch danh mục | Báo cáo NĐ98 sai phân loại A/B/C/D | BR-00-13/14 ràng buộc fetch_from + audit log mỗi override |

*(BA bổ sung risk owner + likelihood/impact score trong sprint kế tiếp)*

## I.9. Roadmap (lộ trình đồng bộ với QMS & Đợt triển khai)

Roadmap IMM-00 gắn với 3 đợt triển khai và lớp QMS theo `Ho_so_kien_truc_IMMIS.md` (§"Lớp QMS và governance" + §"Đợt triển khai"):

| Giai đoạn | Phạm vi IMM-00 | Đầu ra QMS | Mốc Đợt |
|---|---|---|---|
| Giai đoạn 1 — Foundation core | 5 Core DocType (AC prefix) + 6 Governance DocType + service `imm00.py` cốt lõi + 30 roles (4 System + 26 Domain) + permission query | QC-IMMIS nền + audit trail kích hoạt | Trước/Đồng thời Đợt 1 |
| Giai đoạn 2 — Inventory + Catalog | 5 Inventory DocType v4 + IMM Device Model BOM + GMDN hierarchy | PR/WI/BM cho master data | Cùng Đợt 2 |
| Giai đoạn 3 — Analytics hooks | KPI rollup scheduler, drill-down API cho IMM-07/10/17 | KPI-DASH-IMMIS + change control | Cùng Đợt 3 |
| Hậu Đợt 3 — Continuous improvement | Pentest, FHIR/HIS adapter, predictive cockpit hooks | Management review + CAPA loop | Sau Đợt 3 |

> Tham chiếu QMS chuỗi: QC → PR → WI/JD → BM/HS → KPI-DASH (theo Architecture). Mọi thay đổi DocType / service IMM-00 phải đi qua change control.

*(Mốc thời gian cụ thể: cần khảo sát baseline + đồng bộ với plan triển khai từng đơn vị)*

---

# Phần II — Kiến trúc vị trí IMM-00

## II.1. Dependency map — IMM-00 cung cấp cho tất cả module

```
┌─────────────────────────────────────────────────────────────┐
│                  Frappe Framework v15 only                  │
└──────────────────────────────┬──────────────────────────────┘
                               │ dependency DUY NHẤT
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  IMM-00 Foundation Layer                    │
│                                                             │
│  [AC Asset]  [AC Supplier]  [AC Location]  [AC Department]  │
│  [AC Asset Category]  [IMM Device Model]  [IMM SLA Policy]  │
│  [IMM Audit Trail]  [IMM CAPA Record]                       │
│  [Asset Lifecycle Event]  [Incident Report]                 │
│  [Inventory: AC Warehouse, AC Spare Part, ...]              │
│                                                             │
│  services/imm00.py: 22 public functions                     │
│  utils/: response.py, lifecycle.py, email.py, pagination.py │
│  5 daily + 1 monthly scheduler jobs                         │
│  30 role fixtures (4 System + 26 Domain) + permission.py    │
└────┬────────┬──────┬──────┬──────┬──────┬──────┬──────┬────┘
     │        │      │      │      │      │      │      │
  IMM-04   IMM-05 IMM-08 IMM-09 IMM-11 IMM-12 IMM-13 IMM-15/16
  Install  Reg    PM     Repair  Cal   CAPA   EOL    Integration
```

## II.2. Quan hệ với từng module downstream

| Module | Sử dụng từ IMM-00 |
|---|---|
| IMM-04 Installation | `create_lifecycle_event("commissioned")`, `validate_asset_for_operations()`, AC Asset.commissioning_date |
| IMM-05 Registration | AC Asset.byt_reg_no, byt_reg_expiry, `check_registration_expiry` scheduler |
| IMM-08 PM | `get_sla_policy()`, `validate_asset_for_operations()`, AC Asset.next_pm_date, `create_lifecycle_event("pm_completed")` |
| IMM-09 Repair | Incident Report trigger, `transition_asset_status(Active ↔ Under Repair)`, `create_capa()` |
| IMM-11 Calibration | AC Supplier.iso_17025_cert gate, AC Asset.next_calibration_date, `get_sla_policy()` |
| IMM-12 Corrective | `create_capa()` từ audit finding, `transition_asset_status(→ Out of Service)` |
| IMM-13 End of Life | `transition_asset_status(→ Decommissioned)`, suspend PM/Cal schedules |

## II.3. Layer architecture

```
HTTP Request / Frappe Scheduler
           │
           ▼
    API Layer (api/imm00.py + api/inventory.py)
           │   @frappe.whitelist()
           │   107 endpoints trong api/imm00.py (Asset, Supplier, Location/Dept/Cat,
           │   Device Model, SLA, Audit, CAPA, ALE, Incident, GMDN, Transfer,
           │   Service Contract, PM Schedule/Template, Firmware CR, Document Request,
           │   Depreciation, Downtime Metrics, Scheduler triggers)
           ▼
    Service Layer (services/imm00.py + services/inventory.py)
           │   Business logic · SLA lookup · validation gates
           │   log_audit_event · create_lifecycle_event · transition_asset_status
           ▼
    Controller Layer (DocType controllers)
           │   validate() · before_submit() · on_submit() · on_trash()
           ▼
    Data Layer (Frappe ORM → MariaDB)
           │
           ▼
    Side Effects: IMM Audit Trail · Asset Lifecycle Event · Email · Scheduler
```

**Quy tắc bất biến:** Không viết business logic trong controller. Controller chỉ gọi service function. Logic nghiệp vụ nằm toàn bộ trong `services/imm00.py`.

---

# Phần III — Feature Inventory

## III.1. Master data DocTypes

| DocType | Prefix | Mục đích | Trạng thái |
|---|---|---|---|
| AC Asset | AC-ASSET- | Bản ghi thiết bị y tế với HTM fields first-class | Live ✅ |
| AC Supplier | AC-SUP- | NCC, lab hiệu chuẩn, đơn vị bảo trì | Live ✅ |
| AC Location | AC-LOC- | Vị trí vật lý (tree) | Live ✅ |
| AC Department | AC-DEPT- | Khoa/phòng (tree) | Live ✅ |
| AC Asset Category | (by name) | Phân loại thiết bị | Live ✅ |

## III.2. Domain catalog DocTypes

| DocType | Prefix | Mục đích | Trạng thái |
|---|---|---|---|
| IMM Device Model | IMM-MDL- | Master template thiết bị với BOM spare parts | Live ✅ |
| IMM SLA Policy | (by name) | Ma trận SLA P1–P4 × risk_class | Live ✅ |

## III.3. Governance / Audit DocTypes

| DocType | Prefix | Mục đích | Trạng thái |
|---|---|---|---|
| IMM Audit Trail | IMM-AUD- | Log bất biến SHA-256 chain | Live ✅ |
| IMM CAPA Record | CAPA- | Corrective/Preventive Actions (ISO 13485:8.5) | Live ✅ |
| Asset Lifecycle Event | ALE- | Sự kiện vòng đời chuẩn hoá (append-only) | Live ✅ |
| Incident Report | IR- | Sự cố thiết bị → trigger CM/CAPA | Live ✅ |

## III.4. Inventory DocTypes (v4 mới)

| DocType | Prefix | Mục đích | Trạng thái |
|---|---|---|---|
| AC Warehouse | AC-WH- | Kho vật tư | Live ✅ |
| AC Spare Part | AC-SP- | Master catalog phụ tùng | Live ✅ |
| AC Spare Part Stock | {warehouse}::{spare_part} | Tồn kho thực tế | Live ✅ |
| AC Stock Movement | AC-SM- | Phiếu nhập/xuất/chuyển/điều chỉnh | Live ✅ |

## III.5. Shared utilities

| Module | Export chính | Dùng ở |
|---|---|---|
| `utils/response.py` | `_ok(data)`, `_err(msg, code)` | Toàn bộ API endpoint |
| `utils/lifecycle.py` | `create_lifecycle_event()`, `transition_status()` | Service layer |
| `utils/email.py` | `get_role_emails(roles)`, `safe_sendmail()` | Scheduler jobs |
| `utils/pagination.py` | `paginate(query, page, page_size)` | List APIs |

## III.6. Role fixtures (30 roles — 4 System + 26 Domain)

> Canonical source: `assetcore/fixtures/role.json` + `assetcore/services/shared/constants.py::Roles`. Patch áp dụng: `v3_2.001_module_role_redesign`. Các persona role cũ (IMM System Admin, IMM Department Head, IMM Workshop Lead, KTV HTM, Workshop Manager, Trưởng khoa, PTP Khối 2, v.v.) đã bị thay thế — không còn tồn tại trong fixtures.

**System roles (4):**

| Role | Quyền hạn chính |
|---|---|
| `AssetCore Super Admin` | Toàn quyền, bao trùm Frappe System Manager |
| `AssetCore System User` | Role nền: đăng nhập, dashboard, đọc shared-core |
| `AssetCore Auditor` | Read-only toàn bộ + audit trail |
| `Vendor Engineer` | Bên thứ ba, cô lập theo WO/Asset được phân công |

**Domain roles (26 = 13 module × Manager/User):**

| Module | Manager role | User role |
|---|---|---|
| IMM-00 | `Data Manager` | `Data User` |
| IMM-01 | `Needs Manager` | `Needs User` |
| IMM-02 | `Spec Manager` | `Spec User` |
| IMM-03 | `Procurement Manager` | `Procurement User` |
| IMM-04 | `Commissioning Manager` | `Commissioning User` |
| IMM-05 | `Document Manager` | `Document User` |
| IMM-06 | `Training Manager` | `Training User` |
| IMM-08 | `PM Manager` | `PM User` |
| IMM-09 | `Repair Manager` | `Repair User` |
| IMM-11 | `Calibration Manager` | `Calibration User` |
| IMM-12 | `Corrective Manager` | `Corrective User` |
| IMM-15 | `Inventory Manager` | `Inventory User` |
| IMM-16 | `Compliance Manager` | `Compliance User` |

## III.7. Scheduler jobs

> Đăng ký tại `assetcore/hooks.py::scheduler_events`. Riêng IMM-00 foundation đóng góp 5 daily jobs (cũ: 4 — đã bổ sung `check_insurance_expiry` và `check_service_contract_expiry`).

| Job | Tần suất | Logic |
|---|---|---|
| `check_capa_overdue` | Daily | CAPA {Open, In Progress, Pending Verification} + due_date < today → Overdue + email QA Officer. Idempotent (không re-flip Overdue, không động Closed); null-guard (due_date NULL không bao giờ flip). Cùng INVARIANT SoT `_overdue_capa_filter()`. **KHÔNG đổi `capa_open` count** (Overdue vẫn NOT IN Closed = vẫn open — `_open_capa_filter()` bất biến dưới flip) |
| `check_vendor_contract_expiry` | Daily | contract_end in {90,60,30} ngày → email Dept Head |
| `check_registration_expiry` | Daily | byt_reg_expiry in {90,60,30,7} ngày, non-Decommissioned → email |
| `check_insurance_expiry` | Daily | Cảnh báo hết hạn bảo hiểm thiết bị {90,60,30,7} ngày |
| `check_service_contract_expiry` | Daily | Cảnh báo Service Contract end {90,60,30} ngày |
| `rollup_asset_kpi` | Monthly | Tính MTTR avg, uptime % cho từng asset (no email) |

---

## III.8. Notification Framework (Foundation — Wave N1)

> **Mục tiêu:** Khi một sự kiện vòng đời liên quan trực tiếp tới user xảy ra, user nhận thông báo qua **2 kênh**: (1) **In-app** tại chuông góc phải (Frappe Notification Log), (2) **Email** SMTP — user **tự bật/tắt** per-user.
>
> **Frappe-first — KHÔNG modify core, KHÔNG tạo DocType mới:**
> - In-app: tái dùng DocType **Notification Log** (Frappe core) qua `frappe.desk.doctype.notification_log.notification_log.enqueue_create_notification(users, doc)`. Đây đã là record có audit trail (for_user, subject, type, document_type/name, creation).
> - Toggle email per-user: tái dùng DocType **Notification Settings** (Frappe core), field `enable_email_notifications` + `enabled`. Service phải kiểm tra setting này **trước** khi gửi email.
> - Email gửi qua `frappe.sendmail` (wrap bằng `utils/helpers.py::_safe_sendmail`). Cấu hình SMTP runtime (Email Account / site_config) — **không hardcode, không commit secret**.

### Sự kiện vòng 1 (MVP — 2 events)

| ID | Sự kiện | Trigger | Recipient resolution | Kênh |
|---|---|---|---|---|
| **E1** `notify_assignment` | Work Order được gán cho kỹ thuật viên | `PM Work Order` / `Asset Repair` `on_update` + `on_submit` khi `assigned_to` set/đổi | user ở field `assigned_to` (loại trừ self-assign: actor == assignee) | In-app + Email |
| **E2** `notify_approval_pending` | Workflow doc chuyển sang state cần duyệt | doc có `workflow_state` đổi sang state pending-approval (`validate`/`on_update`) | approver: field `supervisor` nếu có, fallback users có allowed-role của transition kế tiếp | In-app + Email |

> **OUT-of-scope vòng 1** (backlog): SLA sắp hết hạn (đã có scheduler riêng `tasks.py`/`imm00`), Incident mới, Calibration đến hạn, SMS/push, digest, notification preferences UI nâng cao. Thêm event sau = chỉ thêm mapping, dùng lại engine.

### FR Notification (FR-00-NTF-01 → 07)

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-NTF-01 | Khi WO gán `assigned_to` → tạo Notification Log cho assignee | System (hook) | `notify_assignment` |
| FR-00-NTF-02 | Khi workflow doc vào state **cần duyệt** → tạo Notification Log cho approver. "State cần duyệt" + approver xác định **động** từ Workflow metadata (transition rời state có `allowed` ∈ role phê duyệt, mặc định `System Manager`), **không hard-code tên state/field**; bổ sung `supervisor` nếu doc có. Xem 04 §III.1b-1. | System (hook) | `notify_approval_pending`, `resolve_approvers_by_workflow` |
| FR-00-NTF-03 | Gửi email cho recipient **chỉ khi** `Notification Settings.enable_email_notifications=1 AND enabled=1` | System | `_user_wants_email` |
| FR-00-NTF-04 | **Mặc định không tự-notify** (actor == recipient → skip) cho mọi event điều phối/phê duyệt/cảnh báo (assignment, approval, escalation, calibration, SLA) — người gây action KHÔNG tự nhận noise. | System | `resolve_recipients` (mặc định `include_self=False`) |
| FR-00-NTF-07 | **Self-confirm (NGOẠI LỆ có kiểm soát của FR-00-NTF-04):** với event mà **người báo chính là bên cần được xác nhận đã ghi nhận**, gửi 1 Notification Log "xác nhận" cho chính người báo dù họ là actor. Phạm vi áp dụng = **chỉ Incident Report tự báo** (`reported_by == actor` và chưa phân công người khác) → "Đã ghi nhận sự cố của bạn". Opt-in per-event qua cờ `self_confirm`; KHÔNG đổi hành vi mặc định của `resolve_recipients`; KHÔNG áp cho assignment/approval/escalation/calibration/SLA. Xem 04 §III.1b-2b. | System (hook) | `notify_incident_created` (cờ `self_confirm`) |
| FR-00-NTF-05 | User đọc trạng thái toggle email của mình | End-user | API `get_notification_preferences` |
| FR-00-NTF-06 | User bật/tắt nhận email | End-user | API `set_email_enabled` |

### Audit trail
- Mỗi notification = 1 record **Notification Log** (immutable, có `for_user`, `subject`, `creation`) → audit trail tự nhiên.
- Listener idempotent + handle `docstatus`/cancel (Pattern A) → không tạo record trùng khi save lặp.

### KPI (gợi ý — backlog đo lường)
- Notification delivery rate (số gửi / số trigger).
- Email opt-out rate (% user tắt email).
- Median thời gian từ assignment → assignee xem (read) Notification Log.

---

# Phần IV — Functional Requirements

## IV.1. Nhóm AC Asset (FR-00-01 → FR-00-05)

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-01 | Tạo mới AC Asset với auto naming | Operations Manager, System Admin | POST `create_asset` |
| FR-00-02 | List AC Asset với filter theo department, location, lifecycle_status, risk_classification | Tất cả role IMM | GET `list_assets` |
| FR-00-03 | Cập nhật AC Asset (trừ lifecycle_status) | Operations Manager | PUT `update_asset` |
| FR-00-04 | Chuyển `lifecycle_status` qua `transition_asset_status()` | Workshop Lead, Ops Manager | Service call |
| FR-00-05 | Gate `validate_asset_for_operations()` — block Out of Service / Decommissioned | Caller modules | Service call |

## IV.2. Nhóm AC Supplier (FR-00-06 → FR-00-09)

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-06 | Tạo NCC với autoname | Storekeeper, Ops Manager | POST `create_supplier` |
| FR-00-07 | Validate ISO 17025 bắt buộc khi vendor_type = Calibration Lab | System | `validate()` controller |
| FR-00-08 | Quản lý child table authorized_technicians | Storekeeper | Child table CRUD |
| FR-00-09 | Đánh dấu NCC không hoạt động — block AC Asset tham chiếu | System | `validate()` AC Asset |

## IV.3. Nhóm IMM Audit Trail (FR-00-19 → FR-00-22)

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-19 | `log_audit_event()` tạo record append-only với SHA-256 chain | System (tất cả modules) | Service call |
| FR-00-20 | Tính `hash_sha256` và liên kết `prev_hash` tạo hash chain | System | `log_audit_event()` |
| FR-00-21 | Block mọi update/delete trên IMM Audit Trail | System | Controller + perm |
| FR-00-22 | API `verify_audit_chain` kiểm tra tính toàn vẹn hash chain | QA Officer | GET verify |

## IV.4. Nhóm IMM CAPA Record (FR-00-23 → FR-00-27)

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-23 | `create_capa()` tạo CAPA Draft | Workshop Lead, QA Officer | Service call |
| FR-00-24 | Validate `before_submit`: root_cause + corrective_action + preventive_action | System | `before_submit()` |
| FR-00-25 | `close_capa()` đóng CAPA, set `closed_date = today()` — **chỉ khi qua cổng hiệu quả** `assert_capa_effectiveness_gate` (VR-06/VR-07, round 12) | QA Officer | Service call |
| FR-00-26 | Auto-mark Overdue khi quá due_date | System (scheduler) | `check_capa_overdue()` |
| FR-00-27 | Liên kết CAPA với Incident Report (`linked_incident`) bidirectional | System | `on_submit()` |
| FR-00-59 | **Cổng hiệu quả CAPA — SoT đơn (round 12).** Mọi đường đóng CAPA (`close_capa` legacy + `capa_record_validate` khi status=Closed) gọi CÙNG predicate `assert_capa_effectiveness_gate(doc)`: `effectiveness_check` reqd (VR-06) + phải = `Effective` (VR-07) → mới được Close. Bít legacy bypass. | System / QA Officer | `assert_capa_effectiveness_gate()` |

## IV.5. Nhóm Asset Lifecycle Event (FR-00-28 → FR-00-30)

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-28 | `create_lifecycle_event()` — tạo event chuẩn hoá | System (tất cả modules) | Service call |
| FR-00-29 | Append-only enforcement (`in_create=1`, `validate()` block update) | System | Controller + perm |
| FR-00-30 | `transition_asset_status()` bắt buộc tạo 1 ALE mỗi lần đổi status | System | Service layer |

## IV.6. (Đã loại bỏ — Nhóm quản lý trạng thái sử dụng GMDN)

> **Note (2026-05-19):** Nhóm FR-00-38 → FR-00-42 (quản lý trạng thái sử dụng GMDN trên từng Asset) đã bị loại bỏ. Trạng thái sử dụng thiết bị đã được bao trùm bởi `lifecycle_status`; trục lọc/quản lý nhóm thiết bị nay là `gmdn_code` (kế thừa từ Asset Category). Field tương ứng trên `AC Asset` đã drop qua patch `v3_1/008`. Tham chiếu: [docs/res/analysis/gmdn-asset-category-analysis.md](../res/analysis/gmdn-asset-category-analysis.md) §6.

## IV.7. Nhóm GMDN Code Hierarchy (FR-00-43 → FR-00-46)

> GMDN code xác định danh mục thiết bị theo chuẩn quốc tế. AssetCore quản lý chuỗi kế thừa 3 cấp: Category → Device Model → Asset.

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-43 | `AC Asset Category` có fields `gmdn_code` và `gmdn_term` là **nguồn kế thừa cấp 1** cho toàn bộ thiết bị trong danh mục; hiển thị khi user chọn danh mục trong form Device Model | System Admin, Workshop Lead | DocType field / `create_asset_category` |
| FR-00-44 | `IMM Device Model` kế thừa `gmdn_code` + `gmdn_term` tự động từ `asset_category` khi tạo mới nếu các trường đó trống; FE auto-fill khi user chọn danh mục; người dùng có thể override thủ công | Workshop Lead | `_inherit_pm_calibration_defaults()` tại `before_insert`; FE `watch(asset_category)` |
| FR-00-45 | `AC Asset` kế thừa `gmdn_code` từ `device_model.gmdn_code` tại `before_insert`; FE auto-fill khi user chọn model (gọi `getDeviceModel`); người dùng có thể override | System / User | `ACAsset.before_insert()` → `_inherit_gmdn_from_device_model()`; FE `watch(device_model)` |
| FR-00-46 | `list_device_models()` hỗ trợ filter theo `gmdn_code` để tra cứu thiết bị cùng mã GMDN | Tất cả role IMM | GET `list_device_models?gmdn_code=...` |

## IV.8. Nhóm Kế thừa luật khấu hao Category → Asset (FR-00-47 → FR-00-52)

> **Self-Correction 2026-06-03 (root-cause).** Trước đây luật khấu hao (`total_depreciation_months`, `residual_value`) CHỈ được điền khi tài sản đi qua đường `create_ac_asset` (IMM-04). Tài sản tạo trực-tiếp / import thiếu số tháng → `before_insert` chỉ kế thừa `gmdn_code`; `before_save` (RC-02) chỉ điền `method/frequency/start_date` nhưng **KHÔNG** điền `total_depreciation_months` hay `residual_value`. Hệ quả: gọi `regenerate_depreciation_schedule` trả **422 "Thiếu: Số tháng khấu hao"** dù Category ĐÃ có luật (xác minh live trên site miyano 2026-06-03: Category CAT-0659 có rule=120 tháng nhưng asset sau `before_insert` vẫn `total_depreciation_months=None`). Đây là **lỗi user báo**. Thiết kế gốc thiếu đặc tả kế thừa luật khấu hao tại NGUỒN → bổ sung nhóm FR này + BR-00-18..21 + Single-Source-of-Truth `inherit_depreciation_rules_from_category()`.

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-47 | **SoT DUY NHẤT** `inherit_depreciation_rules_from_category(asset_doc)` (`services/depreciation.py`) đọc luật từ `AC Asset Category` của asset và điền vào asset khi **đang thiếu**. Trả số field đã backfill (≥1 ⇒ "đã inherit"). KHÔNG raise khi Category thiếu luật. CẢ `before_insert`, `compute_all_depreciation`, `regenerate_depreciation_schedule` (RC-04) lẫn `bulk_regenerate_by_category` (RC-05) PHẢI gọi chung helper này — không nhánh tự copy `months/residual` (grep-guard, **chỉ trừ `create_ac_asset` insert-path** sau Round-4, đối chiếu để KHÔNG lệch công thức residual `round(...,2)`). | System | `services/depreciation.py::inherit_depreciation_rules_from_category()` |
| FR-00-48 | `AC Asset.before_insert()` gọi `inherit_depreciation_rules_from_category(self)` **sau** `_inherit_gmdn_from_device_model()`. Điều kiện điền: `gross_purchase_amount > 0` ∧ `asset_category` có luật (`total_depreciation_months > 0`) ∧ asset **đang thiếu** (`total_depreciation_months ≤ 0` cho months, `residual_value` chưa set / == 0 cho residual). Sau `before_insert`: `total_depreciation_months == Category.total_depreciation_months` và `residual_value == round(gross * Category.default_residual_value_pct/100, 2)`. | System / User | `ACAsset.before_insert()` |
| FR-00-49 | **Không clobber giá trị user nhập tay.** Nếu asset ĐÃ có `total_depreciation_months > 0` → giữ nguyên months. Nếu `residual_value` đã set (khác 0) → giữ nguyên residual. Đường `create_ac_asset` (IMM-04) đã set sẵn months/residual → `before_insert` no-op cho field đó (không double-apply lệch). Kế thừa độc lập theo từng field. | System | `inherit_depreciation_rules_from_category()` |
| FR-00-50 | **Category KHÔNG có luật** (`total_depreciation_months = 0`): `before_insert` KHÔNG bịa số, KHÔNG raise; asset lưu được với `months = 0`. `regenerate_depreciation_schedule` vẫn trả **422 đúng** ("Thiếu: Số tháng khấu hao" — vì Category cũng thiếu) → KHÔNG che lỗi cấu hình thật. | System | `inherit_depreciation_rules_from_category()` (no-op) |
| FR-00-51 | Sau khi backfill ở case FR-00-48, `regenerate_depreciation_schedule(asset)` **KHÔNG còn trả 422** "Thiếu: Số tháng khấu hao" — sinh được schedule (`periods > 0`). | System / User | `api/imm00.regenerate_depreciation_schedule()` |
| FR-00-52 | Nút global **"Áp dụng khấu hao cho TẤT CẢ tài sản"** (`compute_all_depreciation`): với asset có `gross > 0` + Category có luật nhưng asset đang thiếu `method/months` → **backfill luật từ Category TRƯỚC rồi generate** (KHÔNG còn skip). Asset có ≥1 kỳ **Executed** → KHÔNG backfill/regenerate (bảo toàn lịch sử) → đếm vào `skipped_has_history`. **Idempotent:** chạy 2 lần liên tiếp trên cùng dataset → lần 2 `inherited = 0` và KHÔNG tạo trùng schedule / đổi `accumulated` của asset đã Executed. Sinh lifecycle/audit event cho hành động backfill (audit trail — CLAUDE.md §5). RBAC giữ `_assert_system_admin()` → non-admin nhận **403**. | System Admin | `api/imm00.compute_all_depreciation()` |
| FR-00-53 | **Per-asset self-heal khi sinh lịch (RC-04, Round-2).** `regenerate_depreciation_schedule(asset_name)`: với asset CŨ (tạo TRƯỚC khi `before_insert` wire SoT) có `gross > 0` + Category có luật nhưng `asset.total_depreciation_months = 0` → endpoint **TỰ kế thừa luật** (months + residual + method + frequency) từ Category qua **SoT DUY NHẤT** `inherit_depreciation_rules_from_category(asset)` (gọi **TRƯỚC** pre-check), save, rồi sinh lịch **THÀNH CÔNG** (HTTP 200, `periods > 0`) — KHÔNG còn 422 "Thiếu: Số tháng khấu hao". Self-heal là **1 đường DUY NHẤT** (không inline copy months/residual trong `api/imm00.py`). Pre-check 4-field **chạy LẠI SAU** inherit → chỉ pass khi đã đủ. | System / User | `api/imm00.regenerate_depreciation_schedule()` |
| FR-00-54 | **Self-heal KHÔNG che lỗi cấu hình + KHÔNG clobber user.** GIVEN asset `gross>0` nhưng Category cũng thiếu luật (`cat.months<=0`) HOẶC asset không có `asset_category` → regenerate **VẪN 422** với message liệt kê đúng field còn thiếu (months / start_date / gross / method). GIVEN asset đã có `total_depreciation_months>0` hoặc `residual_value` do user nhập tay → inherit **no-op** trên field đã có (giá trị user GIỮ NGUYÊN). GIVEN asset đã có kỳ **Executed** → self-heal KHÔNG override months/residual đã chạy (giữ invariant không phá lịch sử). | System | `inherit_depreciation_rules_from_category()` (no-op) + `regenerate_depreciation_schedule()` |
| FR-00-55 | **Audit + idempotent self-heal.** Mỗi lần self-heal có kế thừa thật (`did_inherit=True`) → sinh **1** Asset Lifecycle Event `event_type='depreciation_rules_inherited'` (option đã thêm round-1) **+ 1** IMM Audit Trail (`event_type='System'`). Inherit no-op (`did_inherit=False`) → **KHÔNG** sinh event rác. Gọi regenerate 2 lần liên tiếp trên cùng asset → cùng số `periods`; lần 2 `did_inherit=False` → không event. | System | `api/imm00.regenerate_depreciation_schedule()` (audit best-effort) |

> **Self-Correction 2026-06-03 (Round-4 — RC-05): hợp nhất `bulk_regenerate_by_category` về SoT.** Thiết kế round-1 (BR-00-18 grep-guard) cho phép `bulk_regenerate_by_category` (`services/depreciation.py`) là **1 trong 3 đường được copy `months/residual` từ Category** — tức vẫn **inline** 4 dòng gán `asset_doc.depreciation_method/total_depreciation_months/depreciation_frequency/residual_value` (`:495-504`). Đây là **lỗi thiết kế gốc**: (a) inline copy → **clobber** field user nhập tay (asset đã có `months>0` / `residual≠0` / method / frequency → bị ghi đè khi admin chạy "Áp dụng khấu hao theo từng Danh mục"); (b) **N+1** — `frappe.db.count(executed)` per-asset trong loop (`:485-488`); (c) **không audit/lifecycle**; (d) payload thiếu `inherited` + `skipped_no_rule` (không khớp `compute_all`). Round-4 **route 100% qua SoT** `inherit_depreciation_rules_from_category` (no-clobber) + **mirror N+1 fix của `compute_all`** (1 query GROUP BY parent prefetch `executed_parents`) + thêm audit + chuẩn hoá payload 7-key. Sau round-4: **chỉ còn `create_ac_asset` (đường insert) + SoT** được copy months/residual — `bulk_regenerate_by_category` KHÔNG còn nhánh inline. Bổ sung FR-00-56..58 + BR-00-23.

| FR-00-56 | **`bulk_regenerate_by_category` route qua SoT — KHÔNG clobber (RC-05).** Nút **"Áp dụng khấu hao theo từng Danh mục"** (`ReferenceDataView.vue` → `bulk_regenerate_schedule_by_category`): với mỗi asset thuộc Category, gọi **SoT DUY NHẤT** `inherit_depreciation_rules_from_category(asset)` thay cho 4 dòng inline gán `depreciation_method/total_depreciation_months/depreciation_frequency/residual_value`. GIVEN asset đã có `total_depreciation_months>0` HOẶC `residual_value≠0` HOẶC `depreciation_method` HOẶC `depreciation_frequency` do user nhập → **GIỮ NGUYÊN** sau khi chạy bulk (no-clobber — BR-00-19). Grep-guard: trong `bulk_regenerate_by_category` **0 occurrence** copy `months/residual` từ Category ngoài lời gọi SoT (giống guard round-1 cho regenerate path). | System Admin | `services/depreciation.bulk_regenerate_by_category()` → `inherit_depreciation_rules_from_category()` |
| FR-00-57 | **N+1 đóng + payload chuẩn hoá khớp `compute_all` (RC-05).** Phép kiểm `executed-history` per-asset (`frappe.db.count(parent=…, status='Executed')`) trong loop bị thay bằng **ĐÚNG 1 query GROUP BY parent** (`executed_parents` set) chạy **MỘT LẦN trước loop** → số query của bulk KHÔNG còn phụ thuộc tuyến tính vào N cho phép kiểm executed-history (mirror N+1 fix `compute_all` round-3). Payload trả **7-key**: `{category, total_assets, inherited, regenerated, skipped_has_history, skipped_no_rule, errors}` — thêm `inherited` (số asset được SoT kế thừa ≥1 field) + `skipped_no_rule` (asset `gross<=0` HOẶC Category cũng thiếu luật → KHÔNG che lỗi master-data). Asset có ≥1 kỳ **Executed** vẫn `skipped_has_history` (qua `executed_parents` prefetch) → `accumulated_depreciation/current_book_value` **bất biến** sau bulk. **Idempotent:** chạy bulk lần 2 trên cùng dataset → `inherited=0`, `regenerated=0` (asset đã có schedule rows → `generate_schedule` skip), payload ổn định. | System Admin | `services/depreciation.bulk_regenerate_by_category()` |
| FR-00-58 | **Audit/lifecycle cho bulk theo Danh mục (RC-05).** Với mỗi asset được SoT kế thừa luật → sinh **1** Asset Lifecycle Event `event_type='depreciation_rules_inherited'` (option đã có sẵn round-1, **KHÔNG migrate thêm**); thêm **1** IMM Audit Trail `event_type='System'` **TỔNG** cho lần bulk (actor + category + inherited/regenerated count). Best-effort try/except — lỗi audit **KHÔNG** chặn payload (CLAUDE.md §5). FE `ReferenceDataView.applyToExistingAssets`: thay `window.confirm()` bằng **BaseModal** xác nhận (WAVE2 pattern); toast kết quả hiển thị `inherited + regenerated + skipped_has_history + skipped_no_rule + errors` (KHÔNG leak raw method/token). `api/imm00.ts` type trả về bổ sung `inherited + skipped_no_rule`. | System Admin / Admin (FE) | `services/depreciation.bulk_regenerate_by_category()` + `ReferenceDataView.applyToExistingAssets()` |

## IV.9. Nhóm Thanh lý tài sản → Hủy kỳ khấu hao Pending còn lại (FR-00-59 → FR-00-62)

> **Self-Correction 2026-06-03 (Vòng 8 — RC-07): Decommission KHÔNG hủy kỳ khấu hao Pending → phantom backlog.** Thiết kế gốc khi `transition_asset_status(asset, 'Decommissioned')` chỉ gọi `_suspend_all_schedules()` — hàm này **CHỈ** set `is_pm_required=0 / is_calibration_required=0 / next_pm_date=None / next_calibration_date=None` (BR-00-04, lịch PM/Hiệu chuẩn). Nó **KHÔNG đụng** child table `AC Asset Depreciation Schedule`. Hệ quả với asset **thanh lý giữa vòng đời** (mid-life, còn nhiều kỳ chưa chạy): mọi dòng `status='Pending'` **vẫn nằm lại**. `get_depreciation_schedule(asset).summary.pending_periods > 0` vĩnh viễn, và — nghiêm trọng hơn — cron `run_due_depreciation` HIỆN ĐÃ lọc `a.lifecycle_status NOT IN ('Decommissioned','Out of Service')` (`depreciation.py:416`) nên kỳ Pending **không bao giờ chạy nữa** nhưng cũng **không bao giờ đóng** → "phantom overdue" treo mãi trong KPI/drill. Đây là **lỗi thiết kế gốc** (BA chưa đặc tả việc chốt sổ khấu hao tại thời điểm thanh lý). Bổ sung nhóm FR này + **BR-00-24** + helper `_cancel_pending_depreciation_on_decommission()`. **Lưu ý schema:** option `status='Cancelled'` ĐÃ có sẵn trong `AC Asset Depreciation Schedule` (`Pending\nExecuted\nCancelled`) → KHÔNG migrate child table; chỉ cần thêm option `depreciation_stopped` vào Select `event_type` của **Asset Lifecycle Event** (xem BR-00-24, là schema-delta DUY NHẤT của vòng này).

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-59 | **Hủy mọi kỳ Pending khi thanh lý.** Khi `transition_asset_status(asset, 'Decommissioned')` chạy thành công (sau khi `lifecycle_status` đã set `Decommissioned`), helper `_cancel_pending_depreciation_on_decommission(asset)` chuyển **MỌI** dòng `AC Asset Depreciation Schedule` của asset có `status='Pending'` → `status='Cancelled'`. Dòng `status='Executed'` **GIỮ NGUYÊN bất biến** (không đụng `depreciation_amount/accumulated_amount/remaining_value/executed_on`). Sau transition: `get_depreciation_schedule(asset).summary.pending_periods == 0`; `executed_periods`, `accumulated_depreciation`, `current_book_value` **KHÔNG đổi**. | System | `services/imm00.py::_cancel_pending_depreciation_on_decommission()` (gọi trong `transition_asset_status` nhánh Decommissioned) |
| FR-00-60 | **Idempotent.** Gọi lại `transition_asset_status(asset, 'Decommissioned')` lần 2 (hoặc helper chạy lại) → 0 dòng Pending còn lại để hủy → KHÔNG có thay đổi DB thêm, KHÔNG sinh event/audit thừa (chỉ sinh khi `cancelled_count ≥ 1`). `transition_asset_status` đã có guard `prev_status == to_status → return` ở đầu hàm (chặn re-entry khi asset đã Decommissioned), helper vẫn phải tự an toàn khi gọi trực tiếp với 0 Pending. | System | `_cancel_pending_depreciation_on_decommission()` |
| FR-00-61 | **Cron không "đào lại" kỳ đã hủy.** `run_due_depreciation(as_of=<tương-lai-xa>)` cho asset Decommissioned trả `executed_rows = 0` cho asset đó — hai lớp chặn: (a) query đã lọc `a.lifecycle_status NOT IN ('Decommissioned','Out of Service')` (đã có); (b) dòng Pending đã thành `Cancelled` nên kể cả nới filter cũng KHÔNG khớp `status='Pending'`. Không còn phantom overdue chờ chạy. | System | `services/depreciation.run_due_depreciation()` |
| FR-00-62 | **Audit/lifecycle khi chốt sổ khấu hao (CLAUDE.md §5).** Mỗi lần thanh lý hủy `cancelled_count ≥ 1` kỳ Pending → sinh **ĐÚNG 1** Asset Lifecycle Event `event_type='depreciation_stopped'` (asset, `root_doctype='AC Asset'`, `root_record=asset`, `notes` nêu **số kỳ hủy** + **book value chốt** `current_book_value`) **+ 1** IMM Audit Trail `event_type='System'` (`ref_doctype='AC Asset'`, `change_summary` nêu số kỳ + book value). `cancelled_count == 0` → **KHÔNG** sinh event/audit (no garbage). **Best-effort:** lỗi ghi audit/event được nuốt bằng try/except — KHÔNG làm vỡ transition (`lifecycle_status` vẫn `Decommissioned` và các dòng Pending vẫn được Cancelled trước khi audit chạy). Lưu ý: event `depreciation_stopped` này SONG SONG với event `decommissioned` mà `transition_asset_status` đã sinh sẵn (state-change) — KHÔNG thay thế. | System | `_cancel_pending_depreciation_on_decommission()` (audit best-effort) |

## IV.10. Nhóm Tạm ngừng sử dụng → TẠM DỪNG khấu hao + DỜI lịch khi khôi phục (FR-00-63 → FR-00-68)

> **Self-Correction 2026-06-03 (Vòng 9 — RC-08): Out of Service KHÔNG dời lịch khấu hao → "phantom catch-up" trích bù toàn bộ kỳ idle.** Thiết kế gốc xử lý `Out of Service` theo cơ chế **"pause-không-dời"**: executor `run_due_depreciation` đã lọc `a.lifecycle_status NOT IN ('Decommissioned','Out of Service')` (`depreciation.py:422`) nên trong **suốt** thời gian asset Out of Service (OoS), mọi kỳ `Pending` có `scheduled_date` rơi vào khoảng OoS **KHÔNG** bị trích (đúng) — `accumulated_depreciation`/`current_book_value` bất biến (đúng). **NHƯNG** khi asset khôi phục `Out of Service → Active`, thiết kế gốc **KHÔNG dời** `scheduled_date` của các kỳ Pending. Hệ quả nghiêm trọng: tất cả kỳ Pending có `scheduled_date < restore_date` (đã quá hạn trong lúc OoS) **lập tức "đến hạn"**, và lần `run_due_depreciation(today)` kế tiếp **trích bù 1 lần toàn bộ N kỳ idle** (back-dated catch-up) → `current_book_value` **tụt đột ngột** đúng bằng tổng khấu hao của cả khoảng ngừng sử dụng. Đây là **lỗi thiết kế gốc** vi phạm nguyên tắc kế toán: tài sản **tạm ngừng** KHÔNG trích khấu hao **trong** kỳ ngừng (Thông tư 45/2018/TT-BTC §9 + Thông tư 23/2023/TT-BTC), thời gian ngừng phải **kéo dài** vòng đời khấu hao tương ứng (dời lịch), KHÔNG dồn-trích-bù. Bổ sung nhóm FR này + **BR-00-25** + 2 helper `_pause_depreciation_on_oos()` (best-effort note pause) và `_reschedule_pending_depreciation_on_restore()` (dời `scheduled_date` += `oos_days`). **Lưu ý schema:** KHÔNG schema-delta — event_type `out_of_service` + `restored` ĐÃ có trong `Asset Lifecycle Event` (round-1), child `AC Asset Depreciation Schedule.scheduled_date` (Date) + `status` ĐÃ đủ field. Phân biệt rõ với BR-00-24 (Decommissioned = HỦY kỳ Pending vĩnh viễn): OoS = **DỜI** kỳ Pending (không mất kỳ, không trích bù).

> **Self-Correction 2026-06-04 (Vòng 12 — RC-CAPA-EFF): hai cổng đóng CAPA lệch nhau → legacy `close_capa` bypass xác minh hiệu quả (VR-06/VR-07).** Thiết kế gốc có **HAI** đường đóng CAPA với độ chặt khác nhau: (1) `services/imm16.py::advance_capa_state` (workflow API) enforce VR-06 (`effectiveness_check` reqd) + VR-07 (phải = `Effective`) **đúng**; nhưng (2) `services/imm00.py::close_capa` (legacy, gọi bởi IMM-12 + API `close_capa_record`) **chỉ** kiểm 3-field BR-00-08 qua `capa_record_before_submit` → cho phép `Open → Closed + submit` với `effectiveness_check = None` hoặc `'Not Effective'`/`'Partially Effective'`. Thêm nữa, controller-gate `capa_record_validate` để **điều kiện kép** `status=='Closed' AND workflow_state=='Closed'` (`imm16.py:616`) → mọi đường save-to-Closed **không** set `workflow_state='Closed'` (controller UI, `set_value` submit) **lọt** cổng. Hệ quả: CAPA đóng mà chưa chứng minh hiệu quả khắc phục — vi phạm **ISO 13485 §8.5.2** (CAPA effectiveness verification) + **NĐ98/2021 Điều 67** (CAPA cho sự cố nghiêm trọng) → audit/QMS phát hiện đóng khống. Đây là **lỗi thiết kế gốc** (BA chưa hợp nhất 2 cổng về 1 SoT). Bổ sung **FR-00-59 + BR-00-26 + guard `assert_capa_effectiveness_gate(doc)`** (SoT đơn, INVARIANT-1) gọi bởi CẢ `close_capa` (trước submit) lẫn `capa_record_validate` (khi `status=='Closed'` BẤT KỂ `workflow_state`). `advance_capa_state` (đã đúng) GIỮ NGUYÊN hành vi. **Schema-delta: KHÔNG** — `effectiveness_check` (field text/enum) đã có; chỉ siết nghĩa: enum `Effective`/`Partially Effective`/`Not Effective`/null. **REGRESSION:** `_open_capa_filter`/`is_capa_open` (CAPA chưa qua effectiveness vẫn đếm "mở") + KPI `capa_open`/`capa_overdue` KHÔNG đổi; test_close_capa happy-path (effectiveness=`Effective`) vẫn xanh. Chi tiết predicate + 2 đường gọi: 04 §II.5.a.

> **Self-Correction 2026-06-04 (Vòng 14 — RC-09): nhãn sự kiện vòng đời `Out of Service → Active` SAI + double-emit.** Thiết kế gốc map nhãn lifecycle event **chỉ theo `to_status`** (`_lifecycle_event_for(to_status)` → `Active`=`activated` luôn). Khôi phục sau **tạm ngừng sử dụng** (OoS→Active) — về mặt nghiệp vụ là **`restored`** — lại bị gắn nhãn `activated` (đồng nhất với kích hoạt mới / phục hồi sau repair). Tệ hơn: helper RESCHEDULE `_reschedule_pending_depreciation_on_restore` (RC-08, Vòng 9) **tự** emit thêm 1 ALE `restored` — nhưng **chỉ khi** có kỳ Pending để dời (`oos_days>0` ∧ tồn tại Pending). Hệ quả **double-emit + KHÔNG nhất quán**: có-Pending → 2 event [`activated` (transition) + `restored` (helper)]; không-Pending → 1 event [`activated`] (helper no-op, không có `restored`). Trên timeline → cặp `activated`+`restored` trùng cho 1 lần khôi phục, hoặc thiếu hẳn `restored`. Đây là **lỗi thiết kế gốc** (RC-08 đặt ALE ở sai layer + helper `_lifecycle_event_for` thiếu `from_status` để phân biệt 2 ngữ nghĩa của `to='Active'`). Fix: (1) `_lifecycle_event_for(to_status, from_status)` — OoS→Active=`restored`, các from khác về Active=`activated`; (2) `transition_asset_status` emit ALE `restored` DUY NHẤT theo (from,to); (3) helper RESCHEDULE BỎ `create_lifecycle_event('restored')`, CHỈ giữ `log_audit_event 'State Change'` (note dời kỳ — chi tiết KH vẫn truy được) + GIỮ `{rescheduled, oos_days}` + logic dời; (4) áp dụng đồng nhất call-site workflow-action `ac_asset.on_update`. Bổ sung **FR-00-69 + BR-00-27**. **Schema-delta: KHÔNG** (`restored`/`activated` đã có round-1). **REGRESSION:** test_imm09:839 (`activated` Under Repair→Active) + test_imm11:1317/branch-A (`activated` Calibrating→Active) + test_depreciation_oos GIỮ NGUYÊN.

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-63 | **PAUSE — tạm dừng trích khi Out of Service (đã có, GIỮ).** Khi `transition_asset_status(asset, 'Out of Service')`, mọi kỳ `Pending` có `scheduled_date` thuộc khoảng OoS **KHÔNG** bị executor trích trong suốt thời gian OoS — bảo đảm bởi filter `lifecycle_status NOT IN ('Decommissioned','Out of Service')` trong `run_due_depreciation` (đã có, `depreciation.py:422`). `accumulated_depreciation` & `current_book_value` **BẤT BIẾN** trong toàn bộ window OoS: chạy `run_due_depreciation` 1+ lần khi asset đang OoS → `executed_rows = 0` cho asset đó, book value KHÔNG đổi. **KHÔNG hủy kỳ** (khác Decommissioned). | System | `services/depreciation.run_due_depreciation()` (filter đã có) |
| FR-00-64 | **PAUSE audit — ghi note khi vào OoS.** Mỗi lần `transition_asset_status(asset, 'Out of Service')` thành công → ngoài event state-change `out_of_service` mà `transition_asset_status` đã sinh sẵn, helper `_pause_depreciation_on_oos(asset)` ghi **best-effort** 1 ALE `event_type='out_of_service'` (note `'depreciation paused'` + số kỳ Pending bị tạm dừng) để audit nêu rõ khấu hao đã tạm dừng. Lỗi audit KHÔNG làm vỡ transition. Asset không cấu hình khấu hao / 0 kỳ Pending → no-op (không ghi event rác, không lỗi). | System | `services/imm00.py::_pause_depreciation_on_oos()` |
| FR-00-65 | **NO PHANTOM CATCH-UP (bug chính) — không trích bù kỳ idle khi khôi phục.** Asset OoS có N kỳ `Pending` quá hạn (`scheduled_date < restore_date`); chuyển `Out of Service → Active` rồi chạy `run_due_depreciation(today)` → **KHÔNG** trích bù N kỳ idle 1 lần. `current_book_value` KHÔNG tụt đột ngột do back-dated catch-up. Đo: `delta_accumulated` sau restore **== 0** cho các kỳ rơi trong khoảng OoS; **chỉ** kỳ đến hạn **SAU** ngày restore (sau khi đã dời lịch) mới được trích bình thường. Bảo đảm bởi FR-00-66 (dời lịch đẩy mọi kỳ Pending sang tương lai trước khi executor chạy). | System | `_reschedule_pending_depreciation_on_restore()` + `run_due_depreciation()` |
| FR-00-66 | **RESCHEDULE — dời lịch theo gap khi khôi phục (Out of Service → Active).** Khi `transition_asset_status(asset, 'Active')` từ `prev_status='Out of Service'`, helper `_reschedule_pending_depreciation_on_restore(asset)` DỜI `scheduled_date` của **MỌI** kỳ `status='Pending'` (chưa Executed): `scheduled_date_mới = scheduled_date_cũ + oos_days`, với `oos_days = restore_date − oos_start_date` (số ngày nguyên). GIỮ NGUYÊN `depreciation_amount`, `period_number`, số kỳ; **KHÔNG** đụng `accumulated_amount`/`remaining_value` (lịch trích tiền không đổi, chỉ dời ngày). **Bất biến đếm:** `count(Pending) trước == sau`, `sum(depreciation_amount Pending) trước == sau` (không mất/không thêm kỳ, tổng depreciable không đổi); mỗi `scheduled_date` dịch đúng `oos_days`. Kỳ `Executed`/`Cancelled` **BẤT BIẾN** (chỉ dời Pending). Trả `{rescheduled: N, oos_days: int}`. | System | `services/imm00.py::_reschedule_pending_depreciation_on_restore()` |
| FR-00-67 | **`oos_start_date` SoT + fallback an toàn.** `oos_start_date` lấy theo thứ tự ưu tiên: (1) `start_time` của AC Asset Downtime Log Out-of-Service **gần nhất** (`reason='Hỏng hóc'` = reason map cho OoS) của asset — nguồn chuẩn (downtime log mở tại transition vào OoS qua `_sync_downtime_log`). **KHÔNG lọc `is_open=1`** vì tại nhánh restore, `_sync_downtime_log` đã ĐÓNG log (`is_open=0`) TRƯỚC khi reschedule chạy (ordering — xem [04 §II.1e ⚠️ ORDERING](./04_Backend_Design.md)); lấy theo `start_time desc` (đóng/mở đều đúng vì `start_time` bất biến khi đóng). (2) fallback nếu không có downtime log OoS: `creation` của Asset Lifecycle Event `event_type='out_of_service'` **gần nhất** của asset. Cả 2 thiếu → **KHÔNG raise**: `_reschedule_…` trả `{rescheduled: 0, oos_days: 0}` (no-op an toàn — không dời sai khi không biết mốc). `oos_days <= 0` (cùng ngày / đồng hồ lệch) → no-op, không dời lùi. | System | `services/imm00.py::_resolve_oos_start_date()` (helper SoT) |
| FR-00-68 | **RESUME audit + idempotent/guard (RC-09, Vòng 14 — SỬA nguồn double-emit).** Khôi phục `Out of Service → Active`: ALE `event_type='restored'` **DUY NHẤT** do `transition_asset_status` emit (1 transition → 1 event, xem FR-00-69). `_reschedule_pending_depreciation_on_restore` **KHÔNG còn** sinh ALE `restored` (trước đây tự emit ⇒ double-emit khi có kỳ Pending dời) — chỉ còn ghi **best-effort 1** IMM Audit Trail `event_type='State Change'` (`change_summary` nêu **số kỳ đã dời** + **`oos_days`** — chi tiết khấu hao vẫn truy được). Lỗi audit KHÔNG làm vỡ transition (status đã `Active`, rows đã dời trước khi audit chạy). **IDEMPOTENT & GUARD:** (a) chạy reschedule 2 lần liên tiếp (hoặc `transition_asset_status` same-status `Active→Active` no-op qua guard `prev==to → return` đầu hàm) → **KHÔNG** dời kép; (b) **chỉ** dời kỳ `Pending` — `Executed`/`Cancelled` BẤT BIẾN; (c) asset không cấu hình khấu hao / 0 kỳ Pending → no-op không lỗi; (d) `oos_start_date` không xác định → fallback FR-00-67 → no-op không raise. **GIỮ NGUYÊN** `{rescheduled, oos_days}` + logic dời ngày. | System | `_reschedule_pending_depreciation_on_restore()` (CHỈ audit, KHÔNG ALE) |
| FR-00-69 | **Nhãn sự kiện vòng đời khôi phục: `restored` ĐÚNG 1, KHÔNG `activated` (RC-09, Vòng 14 — bug chính).** MỘT transition `Out of Service → Active` (qua `transition_asset_status` HOẶC workflow-action `ac_asset.on_update`) sinh **ĐÚNG 1** Asset Lifecycle Event `event_type='restored'` + **0** event `activated` — **bất kể** có kỳ Pending để dời hay không (consistency). Trước fix: có-Pending→2 event [`activated`+`restored`], không-Pending→1 event [`activated`] (mislabel + double-emit). `_lifecycle_event_for(to='Active', from='Out of Service')=='restored'`; `_lifecycle_event_for(to='Active', from∈{Under Repair, Calibrating, Under Maintenance, Commissioned})=='activated'` (KHÔNG đổi nhãn đường phục hồi sau repair/calib/PM/commission). **Audit-trail bất biến:** IMM Audit Trail vẫn có ≥1 entry `State Change` cho transition (hash-chain KHÔNG vỡ; count KHÔNG giảm). | System | `_lifecycle_event_for(to_status, from_status)` + 2 call-site |

## IV.11. Nhóm RBAC Capability Resolution stale-safe (FR-00-70 → FR-00-75)

> **Self-Correction 2026-06-04 (Vòng 3 — RC-RBAC: USER REWORK IMM-14 — capability resolution KHÔNG stale-safe).** Thiết kế gốc của lớp RBAC shared (`services/shared/rbac.py`) gãy end-to-end trên **gunicorn worker đang chạy** (Playwright THẬT, không suy đoán), trong khi QA "PASS" hợp lệ ở `bench console` (process fresh) đã che lỗi. Ba khiếm khuyết thiết kế gốc: (1) **fail-loud** — `can()` dùng `CAPABILITY_MAP[cap]` → cap lạ (worker cũ chưa nạp map mới) raise `KeyError` → `require()`/endpoint trả **HTTP 500** traceback lọt UI thay vì 403 deny; (2) **cache không bust khi deploy** — `get_capabilities` cache Redis `ac_caps::*` TTL 1h, `after_migrate` KHÔNG gọi `invalidate_capabilities()` → cap mới (`decommission.*`) chờ tới 1h mới tới FE; (3) **FE skip refresh** — `fetchSession` chỉ gọi `loadCapabilities` khi `capabilities` rỗng → user có persisted-caps cũ (provisioned trước release) KHÔNG bao giờ nạp lại → nút "Giải nhiệm thiết bị" không hiện. Đây là **lỗi thiết kế gốc** (BA chưa đặc tả ngữ nghĩa stale-safe của capability resolution + cache lifecycle khi deploy). Bổ sung nhóm FR này + **BR-00-28** + version-stamp `CAP_SET_VERSION`. **Schema-delta: KHÔNG** (capability binding là code-map, không DocType). Chi tiết: [04 §III.1c](./04_Backend_Design.md), [05 §I.2b](./05_API_Specification.md), [06 §II.4b](./06_Frontend_Design.md), [08 §III.6b](./08_Deployment.md).

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-70 | **BE no-500 trên cap lạ (AC1).** `rbac.can('cap.khong.ton.tai')` trả **`False`** (`CAPABILITY_MAP.get(cap)` → None → deny), TUYỆT ĐỐI KHÔNG `KeyError`. `rbac.require('cap.khong.ton.tai')` raise `frappe.PermissionError` (**HTTP 403**, message VI "Khong du quyen: {cap}"), KHÔNG KeyError→500. Verify: gọi `api.imm14.create_decommission(...)` khi `decommission.create` chưa có trong worker map → **403 VI**, KHÔNG '500 KeyError'. | System | `services/shared/rbac.py::can()/require()` |
| FR-00-71 | **BE cache-bust on deploy (AC2).** Sau `bench migrate`, cache Redis `ac_caps::*` đã bị xóa — `after_migrate` (setup/install.py) gọi `rbac.invalidate_capabilities()` SAU khi DocPerm/role matrix đã sync. `get_capabilities(<user có DocPerm Asset Decommission>)` trả dict CHỨA `decommission.read/create/approve = True` ngay **lần gọi đầu** sau migrate, KHÔNG đợi TTL 1h. | System | `setup/install.py::after_migrate()` → `rbac.invalidate_capabilities()` |
| FR-00-72 | **FE latest-cap honored (AC3).** User có persisted caps non-empty (provisioned trước release) khi vào lại app → `loadCapabilities` LUÔN được gọi (bỏ empty-check trong `fetchSession`) → `capabilities.value` + localStorage được **overwrite** bằng cap-set mới nhất từ BE. Verify: `localStorage['assetcore.capabilities']` chứa `decommission.*` sau khi `ensureFresh`/`fetchSession` chạy. | User (FE) | `stores/auth.ts::fetchSession()` → `loadCapabilities()` (luôn) |
| FR-00-73 | **FE version invalidation (AC4).** BE response `get_capabilities` gắn `__cap_set_version__` (= hằng `CAP_SET_VERSION`); khi tập cap đổi (số lượng/tên khác bản đã cache) → bump version. FE phát hiện version-stamp lệch → **invalidate persisted caps cũ** trước render gate-button. Verify: bump `CAP_SET_VERSION` → persisted caps cũ bị bỏ, nút IMM-14 "Giải nhiệm thiết bị" render sau reload **KHÔNG cần xóa localStorage tay**. | User (FE) | `stores/auth.ts::loadPersistedCaps()/loadCapabilities()` + BE `CAP_SET_VERSION` |
| FR-00-74 | **No-regression (AC5).** Mọi cap hợp lệ hiện hữu vẫn `can()=True` đúng như cũ; `get_capabilities` cache vẫn hoạt động (TTL **1h** cho cap hợp lệ); 30-role catalog + DocPerm invariants + endpoint `get_capabilities` **không đổi shape** (`{success, data:{cap:bool}}` + khóa kỹ thuật `__cap_set_version__`). `test_rbac` + `test_imm14` + FE auth/cap suite GREEN. | System | `services/shared/rbac.py` (regression guard) |
| FR-00-75 | **Deploy runbook (AC6).** `assetcore-deploy` runbook ghi rõ: sau thêm capability mới → `bench migrate` TỰ bust `ac_caps::*`; nếu hot-add KHÔNG qua migrate thì `bench restart` (reload gunicorn `--preload` worker) + `invalidate_capabilities()`. | Deploy | `assetcore-deploy` SKILL §"Update app" + [08 §III.6b](./08_Deployment.md) |

---

# Phần V — Non-Functional Requirements

## V.1. Hiệu năng

| NFR ID | Yêu cầu | Target |
|---|---|---|
| NFR-00-01 | GET list AC Asset với filter chuẩn | P95 < 200 ms với 100k records |
| NFR-00-02 | GET single AC Asset (full) | P95 < 500 ms |
| NFR-00-03 | `log_audit_event()` | P95 < 100 ms |
| NFR-00-14 | Hệ thống chịu 500k AC Asset, 5M IMM Audit Trail | Index theo §10 Technical Design |

## V.2. Bảo mật

| NFR ID | Yêu cầu | Target |
|---|---|---|
| NFR-00-07 | Role-based + Permission Query cho IMM Technician | Enforced qua `permission.py` |
| NFR-00-08 | SHA-256 chain phải verify thành công | `verify_audit_chain` trả `{valid: true, count, last_hash}` |

## V.3. Khả dụng & Bảo trì

| NFR ID | Yêu cầu | Target |
|---|---|---|
| NFR-00-04 | Cùng 1 AC Asset bị 2 user edit | Optimistic lock qua Frappe modified timestamp |
| NFR-00-05 | Không xóa IMM Audit Trail, ALE | Giữ tối thiểu 7 năm (NĐ98) |
| NFR-00-06 | Daily full DB backup + hourly binlog | RPO ≤ 1h, RTO ≤ 4h |
| NFR-00-09 | Error message qua `frappe._()` | Gói ngôn ngữ `vi.csv` |
| NFR-00-10 | Tất cả service function log request_id + actor | `frappe.logger("imm00")` |
| NFR-00-11 | Response chuẩn `_ok(data)` / `_err(msg, code)` | Enforce qua `utils/response.py` |
| NFR-00-12 | 5 daily + 1 monthly scheduler jobs idempotent | Retry tối đa 3 lần; fail → ERROR log + email admin |
| NFR-00-13 | AC Location tree depth ≤ 6 | Lft/rgt nested set (Frappe NestedSet) |

---

# Phần VI — Business Rules tổng hợp

| BR ID | Business Rule | Enforce tại | Chuẩn |
|---|---|---|---|
| BR-00-01 | Class I → Low; Class II → Medium; Class III → High/Critical | `IMMDeviceModel.validate()` | NĐ 98/2021 |
| BR-00-02 | `AC Asset.lifecycle_status` chỉ thay đổi qua `transition_asset_status()` | Service layer | Internal |
| BR-00-03 | IMM Audit Trail và Asset Lifecycle Event immutable | Controller + Permission | ISO 13485:7.5.9 |
| BR-00-04 | Decommissioned → suspend tất cả PM/Calibration Schedules | `transition_asset_status()` | WHO HTM |
| BR-00-05 | Out of Service / Decommissioned → block tạo Work Order | `validate_asset_for_operations()` | WHO HTM |
| BR-00-06 | AC Supplier Calibration Lab thiếu iso_17025_cert → warning | `ACSupplier.validate()` | ISO/IEC 17025 |
| BR-00-07 | SLA response_time_minutes < resolution_time_hours × 60 | `IMMSLAPolicy.validate()` | Internal |
| BR-00-08 | CAPA before_submit: root_cause + corrective_action + preventive_action | `IMMCAPARecord.before_submit()` | ISO 13485:8.5 |
| BR-00-26 | **Cổng hiệu quả CAPA — SoT đơn, bít legacy bypass (RC-CAPA-EFF, Vòng 12 — INVARIANT-1).** Tồn tại **1 predicate DUY NHẤT** `assert_capa_effectiveness_gate(doc)` (`services/imm00.py`) định nghĩa điều kiện đóng CAPA: `effectiveness_check` NOT NULL/rỗng (VR-06) **VÀ** == `'Effective'` (VR-07). (1) **SoT đơn:** CẢ `close_capa` (legacy, trước `doc.submit()`) lẫn `capa_record_validate` (khi `status=='Closed'`, **BẤT KỂ** `workflow_state` — bỏ điều kiện kép cũ) gọi CÙNG predicate — grep xác nhận 0 literal điều kiện effectiveness lặp ở >1 nơi với độ chặt khác. (2) **Bít legacy bypass:** `close_capa()`/`POST close_capa_record` với `effectiveness_check=None` (hoặc thiếu) → RAISE `ServiceError(VALIDATION, message_code='FIN-007')` (msg VI 'VR-06: ...bắt buộc xác minh hiệu quả'); CAPA KHÔNG đổi Closed, KHÔNG submit. (3) **VR-07 enforce legacy:** `effectiveness_check ∈ {'Not Effective','Partially Effective'}` → RAISE FIN-007 (VR-07 'phải = Effective'), KHÔNG đóng. (4) **Happy-path bất biến:** 3-field đầy đủ + `effectiveness_check='Effective'` → đóng OK (`status='Closed'`, `closed_date` set, submitted), ghi IMM Audit Trail `event_type='CAPA'` (change_summary có effectiveness) + ALE — KHÔNG regress `test_close_capa`. (5) **`advance_capa_state` KHÔNG đổi:** VR-06/VR-07 đã đúng (raise `ServiceError('FIN-007', ...)`), GIỮ NGUYÊN. (6) **Không lệch SoT count:** CAPA chưa qua effectiveness vẫn `_open_capa_filter` đếm 'mở' (status NOT IN Closed) → KPI `capa_open`/`capa_overdue` KHÔNG đổi; không CAPA kẹt trạng thái lai. **BE delta:** `api/imm00.py::close_capa_record` PHẢI thêm `except ServiceError` (hiện chỉ bắt `ValidationError`) → trả 422 + `message_code=FIN-007`. **Schema-delta: KHÔNG.** | `assert_capa_effectiveness_gate()`; gọi bởi `close_capa()` + `capa_record_validate()` | ISO 13485 §8.5.2 (CAPA effectiveness verification) + NĐ98/2021 Điều 67 |
| BR-00-09 | CAPA quá hạn (SoT INVARIANT): `status NOT IN ('Closed') AND due_date IS NOT NULL AND due_date < today` (strict `<`). Daily scheduler flip {Open, In Progress, Pending Verification} quá hạn → Overdue. Mọi KPI/scorecard/quality-dash/drill gọi `_overdue_capa_filter()` → count == drill byte-for-byte | `is_capa_overdue()` / `_overdue_capa_filter()` / `check_capa_overdue()` | Internal |
| BR-00-10 | Mọi thay đổi lifecycle_status → sinh 1 Asset Lifecycle Event | `transition_asset_status()` | Audit trail |
| ~~BR-00-11~~ | *(Đã loại bỏ 2026-05-19 — trạng thái sử dụng GMDN bỏ; bao trùm bởi `lifecycle_status`)* | — | — |
| ~~BR-00-12~~ | *(Đã loại bỏ 2026-05-19 — xem [analysis §6](../res/analysis/gmdn-asset-category-analysis.md))* | — | — |
| BR-00-13 | `gmdn_code` + `gmdn_term` là thuộc tính cấp danh mục. `AC Asset Category` là nguồn kế thừa cấp 1. `IMM Device Model` kế thừa tự động khi tạo mới nếu trống. `AC Asset` kế thừa từ `device_model` tại `before_insert`. Kế thừa một chiều: **Category → Model → Asset**. | `IMMDeviceModel.before_insert()` → `_inherit_pm_calibration_defaults()`; `ACAsset.before_insert()` → `_inherit_gmdn_from_device_model()` | Internal |
| BR-00-14 | Override GMDN được phép tại **cả 3 cấp** (Category, Device Model, Asset) — kế thừa chỉ xảy ra một lần tại `before_insert` nếu field đang trống; nhập tay sau đó không bị ghi đè. | `before_insert` chỉ điền khi trống | Internal |
| BR-00-15 | CAPA "đang xử lý / chưa đóng" (capa_open) — SoT INVARIANT: `open ⟺ status NOT IN ('Closed')`. `'open'` là **SUPERSET** của `'overdue'` (BR-00-09): CAPA `'Overdue'` VẪN open vì chưa đóng. Hệ quả: cron `check_capa_overdue` flip Open→Overdue **KHÔNG** làm capa_open count đổi (count bất biến dưới cron). Mọi KPI dashboard / scorecard `capa_open_count` / quality-dash `capa_open` / drill `list_capas(not_closed=1)` / `get_capa_aging` `total_open` PHẢI gọi `_open_capa_filter()` — KHÔNG inline `status IN [Open, In Progress, ...]` (bỏ sót Overdue/Pending Verification → đếm thiếu). `get_capa_aging`: `total_open == sum(buckets)` — record `opened_date` NULL bị loại khỏi CẢ HAI cách đếm. | `is_capa_open()` / `_open_capa_filter()` | Internal |
| BR-00-16 | **Filter composition của `list_capas` (conjoin, KHÔNG clobber).** explicit `status` (vd `Overdue`/`Open`/`Closed`) và virtual `not_closed`/`overdue` đặt điều kiện trên CÙNG field `status` → PHẢI **conjoin (AND)**, KHÔNG được để virtual filter ghi đè (clobber) explicit status. Vì Frappe **dict-filter chỉ giữ 1 điều kiện/field**, endpoint build filter dạng **list-of-conditions** để cả `["status","=",status]` lẫn `["status","not in",["Closed"]]` cùng tồn tại. INVARIANT: `?not_closed=1&status=Overdue` → CHỈ tập Overdue (KHÔNG full open-set); `?not_closed=1&status=Closed` → 0 rows (tập rỗng); `?overdue=1&status=Open` → 0 rows (Open ∉ tập đã flip Overdue). KHÔNG có explicit status: `not_closed=1` == `_open_capa_filter()` & `overdue=1` == `_overdue_capa_filter()` byte-for-byte (no-regression BR-00-15/BR-00-09). `frappe.db.count` và `frappe.get_list` dùng CÙNG bộ filter conjoined → `pagination.total == len(items)` cho mọi tổ hợp. Self-Correction: thiết kế gốc (BR-00-15/05 §III.7) định nghĩa virtual filter nhưng KHÔNG đặc tả conjoin với explicit status → code dùng `dict.update()` clobber (bug #4 USER Vòng 12 — "chọn status=Quá hạn mà vẫn 117"). | `list_capas()` (`api/imm00.py`) | Internal |
| BR-00-17 | **Số ĐKLH BYT sắp/đã hết hạn (SoT INVARIANT — count == drill).** Predicate DUY NHẤT `byt_expiry_filter(bucket)` (services/imm00): `'expiring'` ⟺ `byt_reg_expiry BETWEEN [today, today+BYT_EXPIRY_SOON_DAYS]` (`BYT_EXPIRY_SOON_DAYS=30`, named const KHÔNG literal); `'expired'` ⟺ `byt_reg_expiry < today` (strict `<`). CẢ HAI bucket LOẠI `byt_reg_expiry IS NULL/''` (chưa khai số ĐKLH ≠ hết hạn). KPI `dashboard.get_overview().assets.byt_expiring_30d`/`byt_expired` (count) **và** drill `list_assets(byt_status='expiring'\|'expired')` (list) gọi CÙNG helper → `pagination.total == số tile` byte-for-byte trên CÙNG vendor scope (`apply_vendor_scope` áp SAU merge). `byt_status` hợp nhất (AND) với mọi filter sẵn có (lifecycle_status/department/…) KHÔNG clobber; giá trị khác → no-op (KHÔNG throw). KHÔNG inline literal window NGOÀI thân SoT (grep-guard = 0). Self-Correction Vòng 31: thiết kế gốc đếm literal inline ở `api/dashboard.py:62-63` + `list_assets` thiếu param → KPI không drill (xem [04 Backend §III.1a](./04_Backend_Design.md)). NĐ98/2021: ĐKLH là điều kiện pháp lý lưu hành — hết hạn ⇒ rủi ro phải dừng khai thác lâm sàng. | `byt_expiry_filter()` (`services/imm00.py`); gọi bởi `get_overview` (count) + `list_assets` (drill) | NĐ98/2021 |
| BR-00-18 | **Kế thừa luật khấu hao Category → Asset (SoT INVARIANT — RC-03).** Helper DUY NHẤT `inherit_depreciation_rules_from_category(asset_doc)` (`services/depreciation.py`) là nguồn copy `months/residual` từ Category xuống Asset. Điều kiện điền field: chỉ khi `gross_purchase_amount > 0` **và** field đó đang thiếu (months ⟺ `total_depreciation_months ≤ 0`; residual ⟺ `residual_value` chưa set / == 0) **và** Category có luật tương ứng (`total_depreciation_months > 0`). Công thức residual **chuẩn hoá**: `residual_value = round(gross * Category.default_residual_value_pct / 100, 2)`. Idempotent: gọi lại trên asset đã đủ luật → 0 field thay đổi. KHÔNG raise khi Category thiếu luật. **Grep-guard (cập nhật Round-4 / RC-05):** NGOÀI helper này, **chỉ `create_ac_asset` (IMM-04, insert-path)** được phép copy `months/residual` từ Category — phải đối chiếu công thức residual để KHÔNG lệch (`round(gross*pct/100,2)`). `bulk_regenerate_by_category` **KHÔNG còn** là đường inline-copy (round-1 từng cho phép → BR-00-23 đã route qua SoT). | `inherit_depreciation_rules_from_category()`; gọi bởi `ACAsset.before_insert()` + `compute_all_depreciation()` + `bulk_regenerate_by_category()` | Internal / Thông tư 23/2023/TT-BTC (khấu hao TSCĐ) |
| BR-00-19 | **Không clobber giá trị user/IMM-04.** `before_insert` GIỮ NGUYÊN field user đã nhập: `total_depreciation_months > 0` → không ghi đè months; `residual_value` khác 0 → không ghi đè residual. Kế thừa độc lập theo từng field (có thể inherit months mà giữ residual user nhập, hoặc ngược lại). Đường `create_ac_asset` đã set sẵn → `before_insert` không double-apply. | `inherit_depreciation_rules_from_category()` (chỉ điền field trống) | Internal |
| BR-00-20 | **KHÔNG che lỗi cấu hình thật.** Category `total_depreciation_months = 0` → `before_insert` KHÔNG bịa số, asset lưu với `months = 0`; `regenerate_depreciation_schedule` vẫn trả 422 đúng (thiếu months vì Category cũng thiếu). Phân biệt rõ "asset thiếu vì chưa kế thừa" (đã fix RC-03) với "Category chưa cấu hình luật" (lỗi master-data, không được auto-fill). | `inherit_depreciation_rules_from_category()` + `regenerate_depreciation_schedule()` | Internal |
| BR-00-21 | **Backfill global bảo toàn lịch sử + audit.** `compute_all_depreciation`: asset có ≥1 kỳ **Executed** → KHÔNG backfill/regenerate (preserve accumulated/book history) → `skipped_has_history`. Asset không có cả luật ở Category → `skipped_no_rule`. Mỗi lần backfill ≥1 field cho ≥1 asset → sinh lifecycle/audit event (1 event tổng hoặc per-asset inherited) để có audit trail (CLAUDE.md §5 "mọi nghiệp vụ phải có record"). Idempotent: lần chạy thứ 2 `inherited = 0`, không tạo trùng schedule. RBAC: `_assert_system_admin()` → non-admin **403**, không leak. | `compute_all_depreciation()` | Internal + audit trail |
| BR-00-22 | **Per-asset self-heal tại `regenerate_depreciation_schedule` (RC-04, Round-2 — INVARIANT).** Endpoint gọi SoT DUY NHẤT `inherit_depreciation_rules_from_category(asset)` (round-1) **TRƯỚC** pre-check 4-field; pre-check **chạy LẠI SAU** inherit (đọc state SAU self-heal). (1) asset cũ months=0 + Category có luật → inherit → **200**, `periods>0`, hết 422 "Thiếu: Số tháng". (2) Category cũng thiếu luật / không `asset_category` → inherit no-op → **VẪN 422** liệt kê đúng field thiếu (KHÔNG che lỗi master-data — BR-00-20). (3) months/residual user đã nhập → inherit no-op (no-clobber — BR-00-19). (4) asset có kỳ Executed → self-heal KHÔNG override months/residual đã chạy (BR-00-21). (5) Idempotent: gọi 2 lần → cùng `periods`, lần 2 `did_inherit=False`. **Audit:** `did_inherit=True` → 1 ALE `depreciation_rules_inherited` + 1 IMM Audit Trail `System`; no-op → KHÔNG event rác. **Grep-guard:** `api/imm00.py` 0 occurrence copy months/residual từ Category ngoài lời gọi SoT. | `regenerate_depreciation_schedule()` → `inherit_depreciation_rules_from_category()` | Internal + audit trail / Thông tư 23/2023/TT-BTC |
| BR-00-23 | **`bulk_regenerate_by_category` route qua SoT (RC-05, Round-4 — INVARIANT).** Đường bulk theo Danh mục gọi SoT DUY NHẤT `inherit_depreciation_rules_from_category(asset)` cho từng asset, **KHÔNG** inline 4 dòng gán `method/months/frequency/residual` từ Category. (1) **No-clobber:** asset đã có `total_depreciation_months>0` / `residual_value≠0` / `depreciation_method` / `depreciation_frequency` user nhập → GIỮ NGUYÊN sau bulk (BR-00-19). (2) **N+1 đóng:** check executed-history qua **1 query GROUP BY parent** (`executed_parents` set) chạy MỘT LẦN trước loop — KHÔNG `frappe.db.count` per-asset (mirror `compute_all` round-3). (3) **Bảo toàn lịch sử:** asset có ≥1 kỳ **Executed** → `skipped_has_history`, `accumulated_depreciation/current_book_value` **bất biến**. (4) **Không che lỗi master-data:** asset `gross<=0` HOẶC Category thiếu luật (`cat.months<=0`) → `skipped_no_rule` (BR-00-20). (5) **Idempotent:** bulk lần 2 → `inherited=0`, `regenerated=0` (đã có schedule rows). **Payload 7-key** `{category, total_assets, inherited, regenerated, skipped_has_history, skipped_no_rule, errors}` (thêm `inherited` + `skipped_no_rule` khớp `compute_all`). **Audit:** per-asset ALE `depreciation_rules_inherited` (option có sẵn round-1) + 1 IMM Audit Trail `System` TỔNG cho lần bulk — best-effort try/except, KHÔNG chặn payload. **Grep-guard:** trong `bulk_regenerate_by_category` 0 occurrence copy months/residual từ Category ngoài lời gọi SoT. **Đường copy hợp lệ NGOÀI SoT chỉ còn `create_ac_asset` (insert path, IMM-04).** | `bulk_regenerate_by_category()` → `inherit_depreciation_rules_from_category()` | Internal + audit trail / Thông tư 23/2023/TT-BTC |
| BR-00-24 | **Thanh lý chốt sổ khấu hao: HỦY mọi kỳ Pending còn lại (RC-07, Vòng 8 — INVARIANT).** Khi `transition_asset_status(asset, 'Decommissioned')` chuyển asset sang `Decommissioned`, helper `_cancel_pending_depreciation_on_decommission(asset)` PHẢI chuyển **MỌI** dòng `AC Asset Depreciation Schedule` của asset có `status='Pending'` → `'Cancelled'`. (1) **Bất biến lịch sử:** dòng `status='Executed'` GIỮ NGUYÊN — KHÔNG đụng `depreciation_amount/accumulated_amount/remaining_value/executed_on`; `asset.accumulated_depreciation/current_book_value` KHÔNG đổi (helper KHÔNG ghi lại 2 field này — chốt tại giá trị hiện hành). (2) **pending_periods → 0:** sau transition `get_depreciation_schedule(asset).summary.pending_periods == 0` (trước fix > 0 nếu thanh lý mid-life). (3) **Cron không đào lại:** `run_due_depreciation(as_of=future)` cho asset Decommissioned → `executed_rows=0` (hai lớp: filter `lifecycle_status NOT IN (...)` + dòng đã `Cancelled` không khớp `status='Pending'`). (4) **Idempotent:** 0 Pending còn lại → 0 thay đổi, 0 event thừa. (5) **Audit (CLAUDE.md §5):** `cancelled_count≥1` → ĐÚNG **1** ALE `event_type='depreciation_stopped'` (notes nêu số kỳ hủy + book value chốt) + **1** IMM Audit Trail `event_type='System'`; `cancelled_count==0` → KHÔNG sinh. (6) **Best-effort audit:** lỗi ghi event/audit nuốt bằng try/except — KHÔNG vỡ transition (status vẫn Decommissioned, rows vẫn Cancelled). **Schema-delta DUY NHẤT:** thêm option `depreciation_stopped` vào Select `event_type` của `Asset Lifecycle Event` (child `AC Asset Depreciation Schedule.status` đã có `Cancelled` — KHÔNG migrate; IMM Audit Trail `event_type` dùng `System` đã có sẵn). | `transition_asset_status()` → `_cancel_pending_depreciation_on_decommission()` | Internal + audit trail / Thông tư 23/2023/TT-BTC + NĐ98 (thanh lý thiết bị y tế) |
| BR-00-25 | **Tạm ngừng sử dụng: TẠM DỪNG khấu hao + DỜI lịch theo gap, KHÔNG trích bù (RC-08, Vòng 9 — INVARIANT).** Phân biệt rõ với BR-00-24 (Decommissioned = HỦY kỳ Pending vĩnh viễn): `Out of Service` = **DỜI** kỳ Pending (không mất kỳ, không trích bù). (1) **PAUSE:** trong toàn bộ window OoS, executor `run_due_depreciation` KHÔNG trích kỳ nào của asset OoS (filter `lifecycle_status NOT IN ('Decommissioned','Out of Service')` đã có — GIỮ); `accumulated_depreciation`/`current_book_value` BẤT BIẾN (chạy executor 1+ lần khi OoS → `executed_rows=0`, book không đổi). (2) **NO PHANTOM CATCH-UP (bug chính):** khi `Out of Service → Active`, các kỳ Pending quá hạn (`scheduled_date < restore_date`) KHÔNG bị trích bù 1 lần; `delta_accumulated` sau restore == 0 cho kỳ rơi trong khoảng OoS — chỉ kỳ đến hạn SAU restore (sau dời) mới trích. (3) **RESCHEDULE:** `_reschedule_pending_depreciation_on_restore(asset)` dời `scheduled_date` của MỌI kỳ `status='Pending'` chưa Executed: `mới = cũ + oos_days`, `oos_days = restore_date − oos_start_date`; GIỮ NGUYÊN `depreciation_amount`/`period_number`/số kỳ; `Executed`/`Cancelled` BẤT BIẾN. Bất biến: `count(Pending) trước==sau`, `sum(depreciation_amount Pending) trước==sau`, mỗi `scheduled_date` dịch đúng `oos_days`. (4) **`oos_start_date` SoT + fallback:** (a) `start_time` Downtime Log OoS gần nhất (`reason='Hỏng hóc'`, KHÔNG lọc `is_open` — log đã đóng bởi `_sync_downtime_log` trước reschedule, xem ordering 04 §II.1e); (b) fallback `creation` ALE `out_of_service` gần nhất; cả 2 thiếu HOẶC `oos_days<=0` → no-op (`{rescheduled:0, oos_days:0}`), KHÔNG raise. (5) **AUDIT (RC-09, Vòng 14 — SỬA):** PAUSE → best-effort 1 ALE `out_of_service` (note `'depreciation paused'`); RESUME → ALE `restored` **DUY NHẤT** emit bởi `transition_asset_status` (xem BR-00-27) — `_reschedule_pending_depreciation_on_restore` **KHÔNG còn** emit ALE, CHỈ best-effort 1 IMM Audit Trail `State Change` (note nêu số kỳ dời + oos_days, chi tiết khấu hao vẫn truy được); lỗi audit KHÔNG vỡ transition. (6) **IDEMPOTENT/GUARD:** reschedule 2 lần (hoặc `Active→Active` no-op qua guard `prev==to → return`) → KHÔNG dời kép; chỉ dời Pending; asset không cấu hình KH / 0 kỳ Pending → no-op không lỗi. **Schema-delta: KHÔNG** (event_type `out_of_service`/`restored` đã có round-1; `scheduled_date` Date + `status` đã đủ — KHÔNG migrate). **REGRESSION:** BR-00-24 (decommission cancel-pending) + BR-05-11/12 (floor residual / clamp accumulated executor) GIỮ NGUYÊN. | `transition_asset_status()` → `_pause_depreciation_on_oos()` (vào OoS) + `_reschedule_pending_depreciation_on_restore()` (về Active) | Internal + audit trail / Thông tư 45/2018/TT-BTC §9 (TSCĐ tạm ngừng không trích KH) + Thông tư 23/2023/TT-BTC + NĐ98/2021 (thiết bị y tế ngừng sử dụng) |
| BR-00-27 | **Nhãn sự kiện khôi phục `restored` ĐÚNG 1 — single-emit theo from-status (RC-09, Vòng 14 — INVARIANT, bug chính).** Khôi phục sau **tạm ngừng** (`Out of Service → Active`) phải sinh **ĐÚNG 1** Asset Lifecycle Event `event_type='restored'` + **0** event `activated`, **bất kể** có kỳ khấu hao Pending để dời hay không (consistency). (1) **SoT nhãn theo (from,to):** `_lifecycle_event_for(to_status, from_status)` — `to='Active'` ∧ `from='Out of Service'`→`restored`; `to='Active'` ∧ from khác (Under Repair/Calibrating/Under Maintenance/Commissioned)→`activated` (**KHÔNG** đổi nhãn các đường phục hồi sau repair/calib/PM/commission — bảo toàn semantics + test_imm09/test_imm11). (2) **Kill double-emit:** `_reschedule_pending_depreciation_on_restore` **KHÔNG** gọi `create_lifecycle_event('restored')` nữa (trước đây tự emit ⇒ có-Pending→2 event [activated+restored], không-Pending→1 event [activated]); GIỮ `log_audit_event 'State Change'` (note dời kỳ KH) + GIỮ `{rescheduled, oos_days}` + logic dời ngày. (3) **Đồng nhất 2 call-site:** service `transition_asset_status` + controller workflow-action `ac_asset.on_update` (đổi OoS→Active qua Frappe Workflow) — fix tại helper `_lifecycle_event_for` áp dụng cả 2. (4) **Audit-trail bất biến:** IMM Audit Trail vẫn ≥1 entry `State Change` cho transition (hash-chain KHÔNG vỡ; count KHÔNG giảm). **Schema-delta: KHÔNG** (`restored`/`activated` đã có round-1). **REGRESSION:** test_imm09:839 (`activated` từ Under Repair) + test_imm11:1317 (`activated` cho path Calibrating→Active branch A) + test_depreciation_oos GIỮ NGUYÊN. | `_lifecycle_event_for(to, from)`; gọi bởi `transition_asset_status()` + `ac_asset.on_update()` | CLAUDE.md §10 (Lifecycle Event traceability) + NĐ98/2021 (truy xuất vòng đời thiết bị) |
| BR-00-28 | **RBAC capability resolution stale-safe — deny-by-default + cache-bust on deploy + FE latest-cap honored (RC-RBAC, Vòng 3 — USER REWORK IMM-14, INVARIANT).** (1) **Deny-by-default (AC1):** `rbac.can(cap)` resolve qua `CAPABILITY_MAP.get(cap)` → cap LẠ trả `False` (KHÔNG `KeyError`); `rbac.require(cap)` cap lạ → `frappe.PermissionError` (HTTP 403, VI 'Khong du quyen: {cap}'), KHÔNG 500. Cap hợp lệ → `bool(frappe.has_permission(dt, ptype, doc))`. (2) **Cache-bust on deploy (AC2):** `after_migrate` gọi `rbac.invalidate_capabilities()` (sau DocPerm/role sync) → xoá `ac_caps::*`; `get_capabilities(user)` trả cap mới (vd `decommission.*`) ngay lần gọi đầu sau migrate, KHÔNG đợi TTL. (3) **TTL bất biến (AC5):** cache `ac_caps::<user>` TTL **3600s** cho cap hợp lệ — GIỮ NGUYÊN; runtime-bust qua hook `role_hooks.invalidate_caps` (User/Has Role/Role Profile) GIỮ NGUYÊN. (4) **FE latest-cap honored (AC3):** `stores/auth.ts::fetchSession` LUÔN gọi `loadCapabilities` (BỎ empty-check `length===0`) → overwrite `capabilities.value`+localStorage bằng cap-set mới nhất; persisted-caps cũ KHÔNG còn che cap mới. (5) **FE version-stamp invalidation (AC4):** BE response gắn `__cap_set_version__` (= `CAP_SET_VERSION`); bump khi tập cap đổi → FE phát hiện version lệch → bỏ persisted-caps cũ trước render gate-button (KHÔNG cần xoá localStorage tay). (6) **No-regression (AC5):** mọi cap hợp lệ vẫn `can()=True` như cũ; endpoint `get_capabilities` không đổi shape (`{success,data:{cap:bool}}` + khóa `__`-prefix); 30-role catalog + DocPerm invariants không đổi; `test_rbac`+`test_imm14`+FE auth/cap suite GREEN. **Schema-delta: KHÔNG** (capability binding là code-map). **REGRESSION:** anti-pattern "RBAC dead-gate" (gate bằng role-name không tồn tại) KHÔNG tái diễn — gate qua capability THẬT (DocPerm). | `services/shared/rbac.py::can()/require()/get_capabilities()/invalidate_capabilities()` + `setup/install.py::after_migrate()` + `stores/auth.ts` + `api/auth.py::get_capabilities` | Internal / NĐ98/2021 (kiểm soát truy cập hồ sơ thiết bị) + ISO 13485 §4.1.6 (kiểm soát phần mềm/quyền) |
| BR-05-13 | **Giá trị còn lại "hiệu dụng" qua SoT `effective_book_value` — fix falsy-zero (RC-06, Self-Correction 2026-06-03).** Suy `current_book_value` ở 3 call-site BE (`compute_depreciation` `:1640`, `_depr_enrich_row` `:2232`, `get_depreciation_stats` `:2355`) trước đây dùng idiom **falsy** `float(current_book_value or gross)` → KHÔNG phân biệt `None` (chưa chạy KH ⟹ đúng fallback `gross`) với `0.0` (đã KH **hết** về 0, residual=0 ⟹ giá trị thật). `0.0 or gross` → **phantom `gross`**. SoT DUY NHẤT `effective_book_value(asset_row) -> float` (`services/depreciation.py`): trả `gross` **CHỈ khi** `current_book_value IS NONE`; trả `float(current_book_value)` khi đã set (**kể cả 0.0**). 3 call-site + predicate `is_fully_depreciated` gọi chung — XOÁ idiom `or gross` inline. **INVARIANT:** (a) asset `gross>0 ∧ residual=0 ∧ configured ∧ book=0.0` → `is_fully_depreciated=True` → ĐƯỢC đếm `fully_depreciated` (INV-DEP-6); (b) `total_book_value` & `by_category[cat]` KHÔNG cộng phantom `gross` (INV-DEP-7); (c) `book IS NULL/None` → `==gross` (no regression — INV-DEP-8); (d) `fully_depreciated == de-dup len(drill 'fully_depreciated')` GIỮ count==drill (INV-DEP-5). **Grep-guard:** `grep 'current_book_value") or gross' api/imm00.py` → **0 occurrence**. FE zero-change (render verbatim `a.current_book_value` / `stats.total_book_value` / `c.book_value`). | `effective_book_value()`; gọi bởi `compute_depreciation()` + `_depr_enrich_row()` + `get_depreciation_stats()` + `is_fully_depreciated()` | Internal / Thông tư 23/2023/TT-BTC (khấu hao TSCĐ) |
| BR-INV-01→08 | Inventory rules: stock không âm, audit trail per movement, etc. | `services/inventory.py` | Internal |

---

## DoD — File 02 hoàn chỉnh

### I. Module Overview
- [x] I.0 Khảo sát hiện trạng (As-Is theo lớp kiến trúc)
- [x] Đặc điểm đặc biệt IMM-00 (foundation, không phải per-module)
- [x] Trạng thái Live vs Planned
- [x] WHO HTM lifecycle position
- [x] Stakeholders + Actors (30 roles = 4 System + 26 Domain)
- [x] Scope In + Out + Assumptions
- [x] I.8 Risk & giảm thiểu
- [x] I.9 Roadmap (đồng bộ QMS + Đợt triển khai)

### II. Architecture position
- [x] Dependency map (mọi IMM-xx phụ thuộc IMM-00)
- [x] Quan hệ downstream từng module
- [x] Layer architecture

### III. Feature inventory
- [x] 5 master data DocTypes
- [x] Domain catalog DocTypes
- [x] Governance DocTypes
- [x] Inventory DocTypes (v4)
- [x] Shared utilities
- [x] Role fixtures (30 roles — 4 System + 26 Domain)
- [x] Scheduler jobs (4 daily)

### IV. Functional Requirements
- [x] FR grouped by DocType / feature area
- [x] ~~GMDN Status Management FR~~ (đã loại bỏ 2026-05-19 — lọc theo `gmdn_code`)

### V. NFR
- [x] Performance targets
- [x] Security targets
- [x] Compliance NĐ98 + WHO HTM + ISO 13485

### VI. Business Rules
- [x] 12 core BRs (BR-00-01 → BR-00-12)
- [x] Inventory BRs
