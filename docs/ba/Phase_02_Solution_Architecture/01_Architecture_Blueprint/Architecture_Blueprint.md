# ARCHITECTURE BLUEPRINT — ASSETCORE (v3)

> **Reconciled to v3 codebase — 2026-05-07.** Kiến trúc thực tế là **Frappe-only 3 tiers** (API → Service → Repository) + DocType controller, **không** dependency ERPNext. Tham chiếu: `docs/ba/00_RECONCILIATION_v3.md`.

**Phiên bản:** 3.0
**Owner:** Tech Lead
**Áp dụng:** AssetCore Frappe app v3.x (Wave 1 + Wave 2 đã ship)

---

## 1. Mục tiêu kiến trúc

1. **Quản lý vòng đời thiết bị y tế** từ Needs → Procurement → Installation → Operation → Maintenance → Decommission.
2. **Audit trail bất biến** (SHA-256 hash chain) cho mọi action có ý nghĩa pháp lý.
3. **Tách lớp nghiêm ngặt** — API mỏng, Service dày, Controller chỉ validate cấu trúc.
4. **Mở rộng theo module IMM-XX** — service & API per-module để dễ ship & maintain.
5. **Frappe-only** — không phụ thuộc ERPNext, giảm rủi ro upgrade chuỗi.

---

## 2. Kiến trúc tầng (3 tiers + Controller)

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend                                                        │
│  Vue 3 + TS + Pinia + TanStack Query + Tailwind                  │
│  apps/assetcore/frontend/                                        │
└──────────────────┬──────────────────────────────────────────────┘
                   │ HTTP (Frappe REST)
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Tier 1 — API Layer                                              │
│  assetcore/api/imm<NN>.py  (+ auth, dashboard, layout, ...)      │
│  • @frappe.whitelist() endpoints                                 │
│  • Input validation (lightweight)                                │
│  • Delegate to Service layer                                     │
└──────────────────┬──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Tier 2 — Service Layer                                          │
│  assetcore/services/imm<NN>.py                                   │
│  • Business logic (state transitions, side effects)              │
│  • Orchestration (cross-DocType operations)                      │
│  • Audit + Lifecycle event publish                               │
│  • Scheduler hooks (PM auto-WO, expiry checks)                   │
└──┬──────────────────┬─────────────────┬─────────────────────────┘
   │                  │                 │
   ▼                  ▼                 ▼
┌──────────┐   ┌──────────────┐   ┌──────────────────────────┐
│ Tier 3 — │   │ Tier 3 —     │   │ Cross-cutting utils      │
│ Frappe   │   │ Repositories │   │ assetcore/utils/         │
│ ORM      │   │ assetcore/   │   │ • lifecycle.py (audit +  │
│ via      │   │ repositories │   │   LE chain)              │
│ DocType  │   │ /            │   │ • api_endpoint, email,   │
│ controllr│   │              │   │   helpers, pagination,   │
│          │   │              │   │   response               │
└──────────┘   └──────────────┘   └──────────────────────────┘
                                          │
                                          ▼
                               ┌──────────────────────────┐
                               │  Frappe v15 Core         │
                               │  • DocType, Workflow     │
                               │  • Permission engine     │
                               │  • Naming Series         │
                               │  • Email / Notification  │
                               │  • File / Print Format   │
                               │  • Scheduler             │
                               └──────────────────────────┘
                                          │
                                          ▼
                               ┌──────────────────────────┐
                               │  MariaDB 10.6+           │
                               │  Redis (queue, cache)    │
                               └──────────────────────────┘
```

**Quy tắc nghiêm ngặt:**
- API **không** chứa business logic; chỉ whitelist + validate input + delegate.
- Service **không** trả ra `Document` object; trả `dict` JSON-serializable.
- DocType controller chỉ validate cấu trúc (mandatory, format); business logic gọi Service.
- Cross-module call: Service A → Service B (KHÔNG Service A → Controller B).

---

## 3. Source-of-truth tổng quan

| Khía cạnh | DocType / Module | API truy cập | Audit |
|---|---|---|---|
| Asset Registry | `AC Asset` | `api/imm00.list_assets`, `get_asset`, `create_asset`, `update_asset`, `transition_status` | qua `services/imm00.transition_asset_status` → `log_audit_event` + `create_lifecycle_event` |
| Lifecycle history | `Asset Lifecycle Event` | `api/imm00.list_lifecycle_events`, `get_lifecycle_event` | (chính nó là audit) |
| Audit chain | `IMM Audit Trail` | `api/imm00.list_audit_trail`, `get_audit_entry`, `verify_chain` | SHA-256, immutable |
| Master data | `AC Supplier`, `AC Location`, `AC Department`, `AC Asset Category`, `IMM Device Model`, `AC Spare Part`, `AC UOM`, `AC Warehouse` | `api/imm00.list_*` / `get_*` / `create_*` | log via service |
| Procurement | `IMM Needs Request` → `IMM Procurement Plan` → `IMM Tech Spec` → `IMM Vendor Evaluation` → `IMM Procurement Decision` → `AC Purchase` → `AC Stock Movement` | `api/imm01`, `imm02`, `imm03`, `purchase`, `inventory` | mỗi service-call → `log_audit_event` |
| Commissioning | `Asset Commissioning` | `api/imm04.*` | hooks tự sinh `PM Schedule` + `IMM Calibration Schedule` |
| Document mgmt | `Asset Document`, `Document Request`, `Required Document Type`, `Expiry Alert Log` | `api/imm05.*` | scheduler daily expiry |
| PM | `PM Work Order`, `PM Schedule`, `PM Checklist Template/Item/Result`, `PM Task Log` | `api/imm08.*` | scheduler daily auto-WO |
| Repair (CM) | `Asset Repair`, `Repair Checklist`, `Spare Parts Used`, `Asset Transfer` | `api/imm09.*` | hourly SLA check; MTTR rollup monthly |
| Calibration | `IMM Asset Calibration`, `IMM Calibration Schedule`, `IMM Calibration Measurement` | `api/imm11.*` | scheduler daily auto-WO + expiry |
| Incident → RCA → CAPA | `Incident Report`, `IMM RCA Record`, `IMM CAPA Record`, `Asset QA Non Conformance` | `api/imm12.*`, `api/imm00.list_capas` | scheduler daily CAPA overdue + chronic failure detection |
| KPI / Dashboard | (computed) | `api/dashboard.get_overview`, `api/dashboard.get_dashboard_data`, `services/imm00.rollup_asset_kpi` (monthly) | rollup scheduler |
| Auth | Frappe `User` | `api/auth.register_user`, `get_user_profile`, `change_password` | Frappe Activity Log |

---

## 4. Cross-cutting concerns

### 4.1 Audit trail (`assetcore/utils/lifecycle.py`)
- `log_audit_event(asset, event_type, ...)` → tạo `IMM Audit Trail` với `hash_sha256` + `prev_hash` (chuỗi SHA-256).
- `create_lifecycle_event(asset, event_type, ...)` → tạo `Asset Lifecycle Event` cho timeline.
- `verify_audit_chain(asset)` → walk back chain, verify hash integrity.

### 4.2 Permission (`assetcore/permissions.py` + `hooks.py`)
- Row-level filter cho 4 DocType: `AC Asset`, `Incident Report`, `Asset Repair`, `PM Work Order`.
- Vendor scope: chỉ thấy WO `assigned_user = self`.
- Department scope: clinical user chỉ thấy data trong khoa của mình.
- Field-level: cost / budget / contract_value chỉ Operations Manager + Finance Officer.

### 4.3 Workflow engine (Frappe core)
- 14 workflow JSON tại `assetcore/assetcore/workflow/`.
- State name Title Case có space; action label tiếng Việt có dấu.
- Mỗi transition gắn `assetcore.utils.lifecycle.log_audit_event` qua DocType controller `on_workflow_state_change` (hoặc service được gọi từ workflow action).

### 4.4 Scheduler (`hooks.py.scheduler_events`)
- **Daily** (16 jobs): CAPA overdue, contract/document/calibration expiry, PM auto-WO, calibration auto-WO, chronic failure, low-stock, AVL/audit/decision overdue.
- **Weekly**: budget envelope alert, benchmark freshness alert.
- **Monthly** (1st): KPI rollup, depreciation run, demand forecast generate.
- **Cron quarterly** (Q1/Q4 1st 02:00): vendor scorecard.
- **Hourly**: SLA breach check (qua service `imm09.check_repair_sla_breach`).

### 4.5 Notifications
- Frappe `Email Queue` cho mọi email gửi.
- `Expiry Alert Log` để chống duplicate notification (idempotency theo `<asset, doc_type, period>`).

---

## 5. Domain → Service map

| Domain | Service module | Hooks vào |
|---|---|---|
| IMM-00 Foundation | `services/imm00.py` | Master CRUD, asset transition, CAPA, KPI rollup, scheduler |
| IMM-01 Needs / Plan / Forecast | `services/imm01.py` | Workflow IMM-01 Needs/Plan, demand forecast monthly, overdue daily |
| IMM-02 Tech Spec / Benchmark / Risk | `services/imm02.py` | Workflow IMM-02 Spec, benchmark freshness weekly |
| IMM-03 Vendor / AVL / Audit / Decision | `services/imm03.py` | 3 workflows; AVL/audit/decision overdue daily; vendor scorecard quarterly; `AC Purchase.validate` link enforcement |
| IMM-04 Commissioning | `services/imm04.py` | Workflow IMM-04; on_submit → trigger imm08+imm11 schedule |
| IMM-05 Document | `services/imm05.py` | Workflow IMM-05; daily expiry; `Document Request` lifecycle |
| IMM-08 Preventive Maintenance | `services/imm08.py` | Workflow IMM-08 PM; daily auto-WO; commissioning hook |
| IMM-09 Repair (CM) | `services/imm09.py` | Workflow IMM-09; hourly SLA; daily overdue; monthly MTTR rollup |
| IMM-11 Calibration | `services/imm11.py` | Workflow IMM-11; daily auto-WO + expiry; commissioning + post-repair hooks |
| IMM-12 Incident / RCA / CAPA | `services/imm12.py` | Workflows IMM-12 Incident + RCA; daily chronic failure detect |
| Inventory | `services/inventory.py` | Daily low-stock alert |
| Purchase | `services/purchase.py` | `AC Stock Movement` on_submit/on_cancel → mark/unmark received |
| Depreciation | `services/depreciation.py` | Monthly run |
| Auth | `services/auth_service.py` | Login, register, profile |

---

## 6. Anti-patterns (đã quyết định loại)

| Anti-pattern | Lý do loại |
|---|---|
| ERPNext sync 2 chiều với `Asset` / `Item` | Tăng độ phức tạp upgrade; AssetCore không cần phân hệ kế toán đầy đủ ERPNext |
| Custom Field thêm vào DocType ERPNext core | Đã thay bằng DocType `AC `/`IMM ` riêng |
| Single `AC Work Order` unified cho PM/CM/Cal | Đã tách 3: `PM Work Order`, `Asset Repair`, `IMM Asset Calibration` — workflow rõ ràng hơn |
| `AC Lifecycle Event` đơn lẻ làm audit | Đã tách 2: `Asset Lifecycle Event` (timeline) + `IMM Audit Trail` (SHA-256 chain) |
| Logic trong API hoặc DocType controller | Phải đẩy hết sang Service layer |
| `frappe.db.set_value()` bypass workflow | Cấm tuyệt đối; dùng `frappe.workflow.apply_workflow` |

---

## 7. Production considerations

### 7.1 Performance
- Indexes trên `IMM Audit Trail.asset` + `timestamp` (cho `_latest_prev_hash` query SQL).
- `assetcore/utils/pagination.py` chuẩn hóa cursor pagination cho list endpoints lớn.
- Avoid N+1: service dùng `frappe.get_all(filters=, fields=)` thay vì loop `frappe.get_doc`.

### 7.2 Reliability
- Idempotency: `services/purchase.py` chống double-fire `auto_mark_purchase_received`.
- `Expiry Alert Log` chống duplicate notification.
- Scheduler retry tự động qua Frappe queue (Redis).

### 7.3 Security
- 4 `permission_query_conditions` enforce row-level filter.
- `IMM Audit Trail` immutable; chỉ Auditor + System Admin được read.
- E-signature (re-auth) cho QMS-critical action — đang spec, chưa hard-code.
- Vendor scope: không thấy `cost_*` / contract financial fields.

### 7.4 Observability
- Frappe Activity Log + `Login Log` cho session events.
- `IMM Audit Trail` cho domain events.
- `Expiry Alert Log` cho notification fatigue tracking.

---

## 8. Deployment topology (đề xuất prod)

```
                          ┌──────────────────────┐
                          │  Cloudflare / WAF    │
                          └──────────┬───────────┘
                                     │
                          ┌──────────▼───────────┐
                          │  Nginx (TLS)         │
                          └──────────┬───────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
   ┌──────────▼──────────┐ ┌─────────▼──────────┐ ┌────────▼─────────┐
   │ Frappe Web (gunicorn)│ │ Frappe Web         │ │ Frappe Schedule  │
   │ assetcore site       │ │ (replica)          │ │ + Background     │
   └──────────┬──────────┘ └─────────┬──────────┘ │ Workers          │
              │                      │             └────────┬─────────┘
              └──────────────────────┴──────────────────────┘
                                     │
                          ┌──────────▼───────────┐
                          │  Redis (queue/cache) │
                          └──────────┬───────────┘
                                     │
                          ┌──────────▼───────────┐
                          │  MariaDB 10.6+ (HA)  │
                          └──────────────────────┘
```

Backup: daily DB dump + private file backup (xem `assetcore-deployment` skill).

---

## 9. Tham chiếu

- Code thật: `assetcore/{api,services,utils}/`, `assetcore/assetcore/{doctype,workflow}/`.
- Mapping BA-name → reality: `docs/ba/00_RECONCILIATION_v3.md`.
- Naming convention: `Phase_00/07_Glossary_Naming_Convention/`.
- API contract: `Phase_07/05_API_Contract_OpenAPI/` (đã rewrite cùng).
- Workflow detail: `Phase_04/01_Workflow_Specification/`.
- Permission detail: `Phase_04/02_Permission_Matrix/`.

---

## 10. Phê duyệt
| Vai trò | Họ tên | Ngày |
|---------|--------|------|
| Tech Lead |  | 2026-05-07 |
| BA Lead |  | 2026-05-07 |
| Security / QA Lead |  | 2026-05-07 |
