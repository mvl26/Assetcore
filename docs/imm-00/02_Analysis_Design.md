# 02 — Phân tích thiết kế nghiệp vụ — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — cung cấp cho toàn bộ hệ thống |
| Owner | BA + System Architect |
| Liên kết | [03 Diagrams](./03_Diagrams.md) · [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) · [06 Frontend](./06_Frontend_Design.md) |
| Chuẩn tham chiếu | WHO HTM 2025, NĐ 98/2021/NĐ-CP, ISO 13485:2016, ISO/IEC 17025 |
| Phiên bản | 4.1.0 |
| Trạng thái | **Live ✅** — BE foundation + scheduler + service layer đã implement; FE đang cuốn chiếu (synced 2026-05-14) |

---

# Phần I — Module Overview

## I.0. Khảo sát hiện trạng (As-Is)

IMM-00 là **foundation layer** — không có quy trình "as-is" tương ứng tại bệnh viện theo nghĩa nghiệp vụ đơn lẻ. Khảo sát hiện trạng được tổng hợp ở mức **lớp kiến trúc nền** (theo `docs/architecture/Ho_so_kien_truc_IMMIS.md` §"Lớp kiến trúc"):

| Lớp kiến trúc hiện trạng | Tình trạng phổ biến tại đơn vị y tế VN | Khoảng trống IMM-00 phải lấp |
|---|---|---|
| Lớp người dùng | Excel/giấy phân tán theo khoa; quyền hạn không bám actor thật | Cần portal nội bộ + RBAC theo 8 vai trò IMM |
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
- Thiết lập vai trò (8 roles), scheduler jobs (4 daily), và permission query

Nguyên tắc kiến trúc bắt buộc: AssetCore **chỉ phụ thuộc Frappe Framework v15** — không cần ERPNext. Các DocType core được thiết kế theo mẫu schema của ERPNext nhưng **tái tạo native** với prefix `AC` / `IMM`, không extend hay link sang DocType của ERPNext.

## I.2. Trạng thái triển khai (Live vs. Planned)

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| 5 Core DocTypes (AC prefix) | **Live ✅** | AC Asset, AC Supplier, AC Location, AC Department, AC Asset Category đã có trong `assetcore/assetcore/doctype/` |
| 6 Governance DocTypes (IMM prefix) | **Live ✅** | IMM Audit Trail, IMM CAPA Record, Asset Lifecycle Event, Incident Report, IMM Device Model, IMM SLA Policy |
| 5 Inventory DocTypes (v4) | **Live ✅** | AC Warehouse, AC Spare Part, AC Spare Part Stock, AC Stock Movement (+ Item child), AC Stock Movement Item |
| Services (imm00.py) | **Live ✅** | 22 public functions implement (transfer, GMDN, scheduler, KPI rollup) |
| Role fixtures | **Live ✅** | 20 IMM roles seed qua `fixtures/role.json` (commit `5b4158e`) |
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

| Vai trò | Người dùng thực | Quan tâm chính | Loại |
|---|---|---|---|
| IMM System Admin | Quản trị viên CNTT | Cấu hình SLA, Device Model, seed fixtures, phân quyền | Primary |
| IMM Department Head | Trưởng phòng HTM / BGĐ kỹ thuật | Nhận cảnh báo HĐ NCC, BYT expiry; xem dashboard KPI | Primary |
| IMM Operations Manager | Quản lý vận hành | CRUD AC Asset, AC Supplier; quản lý dữ liệu vận hành | Primary |
| IMM Workshop Lead | Trưởng xưởng kỹ thuật | Cập nhật Device Model; tạo CAPA; đóng Incident | Secondary |
| IMM Technician | Kỹ thuật viên | Xem AC Asset được gán; cập nhật PM/cal date | Secondary |
| IMM Document Officer | Nhân viên tài liệu | Xem Audit Trail; xuất báo cáo traceability | Auditor |
| IMM Storekeeper | Thủ kho | Cập nhật AC Supplier, spare parts catalog, tồn kho | Secondary |
| IMM QA Officer | Nhân viên QA/QC | Tạo/đóng CAPA; verify hash chain; audit review | Approver |

## I.5. Scope

**In-scope:**
- 27 DocTypes foundation IMM-00 (5 core + 6 governance + 5 inventory + 11 child/support) — verified vs `assetcore/assetcore/doctype/`
- Lifecycle state machine cho AC Asset.lifecycle_status (8 states: Draft, Commissioned, Active, Under Maintenance, Under Repair, Calibrating, Out of Service, Decommissioned)
- Audit Trail bất biến với SHA-256 chain
- CAPA workflow (Open → In Progress → Pending Verification → Closed / Overdue)
- SLA lookup engine theo priority × risk_class
- Incident Report → trigger Repair WO + CAPA
- 5 daily scheduler jobs + 1 monthly (`rollup_asset_kpi`)
- 20 role fixtures (Wave 1 + Wave 2) + permission query
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
| Giai đoạn 1 — Foundation core | 5 Core DocType (AC prefix) + 6 Governance DocType + service `imm00.py` cốt lõi + 8 role + permission query | QC-IMMIS nền + audit trail kích hoạt | Trước/Đồng thời Đợt 1 |
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
│  20 role fixtures + permission.py                           │
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

## III.6. Role fixtures (20 IMM roles)

> Wave 1 (13 role) + Wave 2 (7 role, incl. IMM Training Officer) — danh sách đầy đủ trong `assetcore/services/shared/constants.py::Roles`.

| Role | Quyền hạn chính |
|---|---|
| IMM System Admin | Create/Write/Delete mọi DocType AssetCore |
| IMM Operations Manager | Duyệt cuối phiếu lớn; CRUD AC Asset, AC Supplier |
| IMM Department Head | Duyệt cấp khoa + hủy phiếu; nhận cảnh báo scheduler |
| IMM Deputy Department Head | Hỗ trợ trưởng khoa (không được hủy) |
| IMM Workshop Lead | Phân công + duyệt Work Order; Create CAPA |
| IMM QA Officer | QMS, CAPA, RCA, verify hash chain |
| IMM Biomed Technician | Thực hiện WO, nhập checklist, báo sự cố |
| IMM Technician | Legacy alias; Read AC Asset scoped |
| IMM Document Officer | Quản lý hồ sơ IMM-05 |
| IMM Storekeeper | Quản lý kho, phụ tùng, stock movement |
| IMM Clinical User | Xem thiết bị khoa mình, báo sự cố |
| IMM Auditor | Read-only — truy vết audit trail |
| Vendor Engineer | Bên thứ ba (KTV nhà cung cấp) |
| IMM Planning / Finance / HTM Engineer / Procurement / Risk / Board Approver | Wave 2 (IMM-01→03) |
| IMM Training Officer | Wave 2 (IMM-06) |

## III.7. Scheduler jobs

> Đăng ký tại `assetcore/hooks.py::scheduler_events`. Riêng IMM-00 foundation đóng góp 5 daily jobs (cũ: 4 — đã bổ sung `check_insurance_expiry` và `check_service_contract_expiry`).

| Job | Tần suất | Logic |
|---|---|---|
| `check_capa_overdue` | Daily | CAPA Open/In Progress + due_date < today → Overdue + email QA Officer |
| `check_vendor_contract_expiry` | Daily | contract_end in {90,60,30} ngày → email Dept Head |
| `check_registration_expiry` | Daily | byt_reg_expiry in {90,60,30,7} ngày, non-Decommissioned → email |
| `check_insurance_expiry` | Daily | Cảnh báo hết hạn bảo hiểm thiết bị {90,60,30,7} ngày |
| `check_service_contract_expiry` | Daily | Cảnh báo Service Contract end {90,60,30} ngày |
| `rollup_asset_kpi` | Monthly | Tính MTTR avg, uptime % cho từng asset (no email) |

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
| FR-00-25 | `close_capa()` đóng CAPA, set `closed_date = today()` | QA Officer | Service call |
| FR-00-26 | Auto-mark Overdue khi quá due_date | System (scheduler) | `check_capa_overdue()` |
| FR-00-27 | Liên kết CAPA với Incident Report (`linked_incident`) bidirectional | System | `on_submit()` |

## IV.5. Nhóm Asset Lifecycle Event (FR-00-28 → FR-00-30)

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-28 | `create_lifecycle_event()` — tạo event chuẩn hoá | System (tất cả modules) | Service call |
| FR-00-29 | Append-only enforcement (`in_create=1`, `validate()` block update) | System | Controller + perm |
| FR-00-30 | `transition_asset_status()` bắt buộc tạo 1 ALE mỗi lần đổi status | System | Service layer |

## IV.6. (Đã loại bỏ — Nhóm quản lý trạng thái sử dụng GMDN)

> **Note (2026-05-19):** Nhóm FR-00-38 → FR-00-42 (quản lý trạng thái sử dụng GMDN trên từng Asset) đã bị loại bỏ. Trạng thái sử dụng thiết bị đã được bao trùm bởi `lifecycle_status`; trục lọc/quản lý nhóm thiết bị nay là `gmdn_code` (kế thừa từ Asset Category). Field tương ứng trên `AC Asset` đã drop qua patch `v3_1/008`. Tham chiếu: [docs/res/gmdn-asset-category-analysis.md](../res/gmdn-asset-category-analysis.md) §6.

## IV.7. Nhóm GMDN Code Hierarchy (FR-00-43 → FR-00-46)

> GMDN code xác định danh mục thiết bị theo chuẩn quốc tế. AssetCore quản lý chuỗi kế thừa 3 cấp: Category → Device Model → Asset.

| FR ID | Mô tả | Actor | Phương thức |
|---|---|---|---|
| FR-00-43 | `AC Asset Category` có fields `gmdn_code` và `gmdn_term` là **nguồn kế thừa cấp 1** cho toàn bộ thiết bị trong danh mục; hiển thị khi user chọn danh mục trong form Device Model | System Admin, Workshop Lead | DocType field / `create_asset_category` |
| FR-00-44 | `IMM Device Model` kế thừa `gmdn_code` + `gmdn_term` tự động từ `asset_category` khi tạo mới nếu các trường đó trống; FE auto-fill khi user chọn danh mục; người dùng có thể override thủ công | Workshop Lead | `_inherit_pm_calibration_defaults()` tại `before_insert`; FE `watch(asset_category)` |
| FR-00-45 | `AC Asset` kế thừa `gmdn_code` từ `device_model.gmdn_code` tại `before_insert`; FE auto-fill khi user chọn model (gọi `getDeviceModel`); người dùng có thể override | System / User | `ACAsset.before_insert()` → `_inherit_gmdn_from_device_model()`; FE `watch(device_model)` |
| FR-00-46 | `list_device_models()` hỗ trợ filter theo `gmdn_code` để tra cứu thiết bị cùng mã GMDN | Tất cả role IMM | GET `list_device_models?gmdn_code=...` |

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
| BR-00-09 | CAPA quá due_date → auto Overdue qua daily scheduler | `check_capa_overdue()` | Internal |
| BR-00-10 | Mọi thay đổi lifecycle_status → sinh 1 Asset Lifecycle Event | `transition_asset_status()` | Audit trail |
| ~~BR-00-11~~ | *(Đã loại bỏ 2026-05-19 — trạng thái sử dụng GMDN bỏ; bao trùm bởi `lifecycle_status`)* | — | — |
| ~~BR-00-12~~ | *(Đã loại bỏ 2026-05-19 — xem [analysis §6](../res/gmdn-asset-category-analysis.md))* | — | — |
| BR-00-13 | `gmdn_code` + `gmdn_term` là thuộc tính cấp danh mục. `AC Asset Category` là nguồn kế thừa cấp 1. `IMM Device Model` kế thừa tự động khi tạo mới nếu trống. `AC Asset` kế thừa từ `device_model` tại `before_insert`. Kế thừa một chiều: **Category → Model → Asset**. | `IMMDeviceModel.before_insert()` → `_inherit_pm_calibration_defaults()`; `ACAsset.before_insert()` → `_inherit_gmdn_from_device_model()` | Internal |
| BR-00-14 | Override GMDN được phép tại **cả 3 cấp** (Category, Device Model, Asset) — kế thừa chỉ xảy ra một lần tại `before_insert` nếu field đang trống; nhập tay sau đó không bị ghi đè. | `before_insert` chỉ điền khi trống | Internal |
| BR-INV-01→08 | Inventory rules: stock không âm, audit trail per movement, etc. | `services/inventory.py` | Internal |

---

## DoD — File 02 hoàn chỉnh

### I. Module Overview
- [x] I.0 Khảo sát hiện trạng (As-Is theo lớp kiến trúc)
- [x] Đặc điểm đặc biệt IMM-00 (foundation, không phải per-module)
- [x] Trạng thái Live vs Planned
- [x] WHO HTM lifecycle position
- [x] Stakeholders + Actors (8 roles)
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
- [x] Role fixtures (8 roles)
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
