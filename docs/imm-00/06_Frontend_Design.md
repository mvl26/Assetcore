# 06 — Frontend Design — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — shared UI components + base views |
| Owner | FE Lead |
| Liên kết | [05 API Specification](./05_API_Specification.md) · [07 Testing & QA](./07_Testing_QA.md) |
| Tech Stack | Vue 3 · TypeScript · Pinia · Vue Router 4 · TailwindCSS · Frappe UI |
| Phiên bản | 3.3.0 |
| Trạng thái | **Live (partial) ✅** — Synced vs code 2026-05-19; thêm III.4b (modal Vị trí + BR-00-FE-03 auto-fetch số liên hệ); BR-00-FE-01/02 (cascade + auto-fill PM/Cal). |

---

# Phần I — Design System Tokens

## I.1. Color Palette

| Token | Hex | Dùng cho |
|---|---|---|
| `--color-primary-500` | `#0E6FFF` | CTA chính, link, selected state |
| `--color-primary-600` | `#0957D1` | Hover primary |
| `--color-primary-50` | `#E8F1FF` | Background nhẹ, chip, SLA is_default highlight |
| `--color-success-500` | `#16A34A` | Active, Calibrated, hash verified |
| `--color-warning-500` | `#F59E0B` | PM đến hạn, ISO 17025 thiếu, Under Repair |
| `--color-danger-500` | `#DC2626` | Overdue, Out of Service, Critical severity |
| `--color-info-500` | `#0891B2` | Thông tin trung tính, Commissioning |
| `--color-neutral-900` | `#0F172A` | Text chính |
| `--color-neutral-600` | `#475569` | Text phụ |
| `--color-neutral-300` | `#CBD5E1` | Border |
| `--color-neutral-100` | `#F1F5F9` | Background section |
| `--color-neutral-0` | `#FFFFFF` | Canvas |

### Semantic colors — `AC Asset.lifecycle_status`

> **Verified từ `types/imm00.ts` (2026-05-18):** LifecycleStatus = `'Commissioned' | 'Active' | 'Under Repair' | 'Calibrating' | 'Out of Service' | 'Decommissioned'`.
>
> **Gap đã biết:** `'Draft'` và `'Under Maintenance'` tồn tại trong `_VALID_ASSET_TRANSITIONS` (service state machine) nhưng KHÔNG có trong type `LifecycleStatus` ở FE. Asset mới insert có `lifecycle_status = 'Draft'` (blank hoặc default từ DocType) trước khi đi qua IMM-04 commissioning. `'Under Maintenance'` dùng khi PM WO mở. FE hiện dùng fallback để render chip màu cho 2 giá trị này — không gây runtime error, nhưng type safety bị bỏ qua.

| lifecycle_status | Màu chip | Style |
|---|---|---|
| Commissioned | info-500 | soft |
| Active | success-500 | solid |
| Under Maintenance | warning-500 | soft |
| Under Repair | warning-500 | soft |
| Calibrating | info-500 | soft |
| Out of Service | danger-500 | soft |
| Decommissioned | neutral-900 | outline dashed |

### Semantic colors — `IMM CAPA.status`

| CAPA status | Màu |
|---|---|
| Open | info |
| In Progress | warning |
| Overdue | danger |
| Pending Verification | warning |
| Closed | success |

## I.2. Typography

Font chính: **Inter** (fallback: Roboto, system-ui).

| Token | Size / Line-height | Weight | Dùng cho |
|---|---|---|---|
| `text-xs` | 12/16 | 400 | Caption, helper text |
| `text-sm` | 14/20 | 400/500 | Body phụ, label form |
| `text-base` | 16/24 | 400 | Body chính |
| `text-lg` | 20/28 | 600 | Heading section |
| `text-xl` | 24/32 | 600 | Heading page |
| `text-2xl` | 30/38 | 700 | KPI number (dashboard) |

## I.3. Spacing Scale

`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64` px via `space-1…space-16`.
Gap grid: 16px (mobile) / 24px (desktop).

## I.4. Component Library

Base: `frappe/frappe-ui` + mở rộng `@assetcore/ui`.

| Component | Biến thể | Ghi chú |
|---|---|---|
| Button | primary / secondary / ghost / danger / icon | loading + disabled state |
| Input | text / number / textarea / password | label + helper + error slot |
| Select | single / multi / async search | async gọi `/api/method/…` |
| DatePicker | single / range | locale vi |
| Table | sortable / selectable / sticky header | Virtual scroll ≥ 500 rows |
| Modal | default / confirm / fullscreen | ESC đóng, focus trap |
| Toast | success / warning / danger / info | 3s auto-dismiss (success); persistent (error) |
| Tabs | line / card | Deep-link `?tab=` |
| Tree | expandable, lazy-load | AC Location / AC Department |
| FileUpload | drag-drop, multi | Frappe File |
| Drawer | right / bottom | Filter nâng cao, quick edit |
| Chip | status / severity / risk_class | Preset semantic color |
| Breadcrumb | auto từ route | truncation |
| Skeleton | list row / card / form | Thay spinner |
| Timeline | vertical | Lifecycle Event, Audit Trail |
| QRScanner | overlay + auto-close | `@zxing/browser` |
| StatusBadge | lifecycle / capa / incident | Preset colors |

## I.5. Icon Set

**Lucide** (primary) + **Heroicons** (fallback). Size: 16 / 20 / 24.

---

# Phần II — App Shell & Sitemap

## II.1. App Shell Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Topbar  [AC] AssetCore  [🔍 Tìm mã/UDI/tên…  ⌘K]  [🔔3] [👤▾]  │
├───────────┬──────────────────────────────────────────────────────┤
│           │  Breadcrumb: Trang chủ / Thiết bị / AC-ASSET-…       │
│  Sidebar  ├──────────────────────────────────────────────────────┤
│           │                                                      │
│  Dashboard│              Main content area                       │
│  Thiết bị │         (list / detail / form / tree)                │
│  NCC      │                                                      │
│  Vị trí   │                                                      │
│  Khoa     │                                                      │
│  Master   │                                                      │
│  Sự cố    │                                                      │
│  CAPA     │                                                      │
│  Audit    │                                                      │
│  Kho      │                                                      │
│           │                                                      │
└───────────┴──────────────────────────────────────────────────────┘
```

## II.2. Sidebar Navigation

| # | Nhãn | Icon (Lucide) | Route | Quyền tối thiểu |
|---|---|---|---|---|
| 1 | Dashboard | `layout-dashboard` | `/` | Mọi IMM role |
| 2 | Thiết bị (AC Asset) | `package` | `/assets` | IMM Technician+ |
| 3 | Nhà cung cấp | `truck` | `/suppliers` | Storekeeper+ |
| 4 | Vị trí (AC Location) | `map-pin` | `/locations` | Ops Manager+ |
| 5 | Khoa / Department | `building-2` | `/departments` | Ops Manager+ |
| 6 | Master Data | `database` | `/master-data` | Workshop Lead+ |
| | — IMM Device Model | | `/master-data/device-models` | |
| | — AC Asset Category | | `/master-data/categories` | |
| | — IMM SLA Policy | | `/master-data/sla` | |
| 7 | Sự cố (Incident) | `alert-triangle` | `/incidents` | IMM Technician+ |
| 8 | CAPA | `shield-check` | `/capa` | QA Officer, Workshop Lead |
| 9 | Audit Trail | `file-lock` | `/audit-trail` | QA Officer, System Admin |
| 10 | Kho vật tư | `archive` | `/inventory` | Storekeeper+ |

Sidebar ẩn item không có quyền (không grey-out). Collapse/expand lưu vào `localStorage`.

## II.3. Sitemap — Built vs Spec

> **Verified từ code 2026-05-18:** Views đã build:
>
> `frontend/src/views/asset/`:
> - `AssetListView.vue`, `AssetCreateView.vue`, `AssetDetailView.vue`, `AssetEditView.vue`
> - `AssetTransferListView.vue`, `AssetTransferCreateView.vue`, `AssetTransferDetailView.vue`
> - `DepreciationView.vue`
> - `DeviceModelListView.vue`, `DeviceModelFormView.vue`
>
> `frontend/src/views/master-data/`:
> - `ReferenceDataView.vue` — Locations, Departments, Categories, Device Models
> - `SlaPolicyListView.vue`
>
> `frontend/src/views/audit/`:
> - `AuditTrailListView.vue`
> - `PendingApprovalsView.vue`

Các routes dưới đây đánh dấu `[BUILT]` nếu có Vue component, `[SPEC]` nếu chỉ là spec chưa build.

```
/                           → Dashboard (IMM-00 overview KPIs)              [SPEC]
/assets                     → AC Asset List                                  [BUILT — AssetListView.vue]
/assets/new                 → AC Asset Form (Create)                        [BUILT — AssetCreateView.vue]
/assets/:name               → AC Asset Detail (admin, 5 tab)                [BUILT — AssetDetailView.vue]
/assets/:name/edit          → AC Asset Form (Edit)                          [BUILT — AssetEditView.vue]
/assets/:id/info            → Asset Scan Info (mobile-first, read-only)     [SPEC — A6/V7, xem II.3c]
/a/:token                   → QR deep-link resolve → redirect /info (A6)    [SPEC — A2/V3, xem II.3b]
/assets/:name/lifecycle     → Asset Lifecycle Event Timeline                [SPEC]
/assets/depreciation        → Depreciation hub                              [BUILT — DepreciationView.vue]
/assets/transfers           → Asset Transfer List                           [BUILT — AssetTransferListView.vue]
/assets/transfers/new       → Asset Transfer Form (Create)                  [BUILT — AssetTransferCreateView.vue]
/assets/transfers/:name     → Asset Transfer Detail                         [BUILT — AssetTransferDetailView.vue]
/assets/device-models       → Device Model List                             [BUILT — DeviceModelListView.vue]
/assets/device-models/new   → Device Model Form                             [BUILT — DeviceModelFormView.vue]
/suppliers                  → AC Supplier List                              [SPEC]
/suppliers/:name            → AC Supplier Detail + authorized_technicians   [SPEC]
/master-data                → ReferenceDataView.vue (Locations/Depts/Cats/Models) [BUILT]
/master-data/sla            → SlaPolicyListView.vue                         [BUILT]
/incidents                  → Incident Report List                          [SPEC]
/incidents/new              → Incident Wizard (3 steps)                     [SPEC]
/incidents/:name            → Incident Report Detail                        [SPEC]
/capa                       → IMM CAPA Record List                          [SPEC]
/capa/new                   → CAPA Form (Create)                            [SPEC]
/capa/:name                 → CAPA Detail + workflow bar                    [SPEC]
/audit-trail                → AuditTrailListView.vue                        [BUILT — views/audit/]
/approvals/pending          → PendingApprovalsView.vue (inbox 3-module, §III.11) [BUILT — views/audit/]
/inventory                  → Inventory Dashboard                           [SPEC]
/print/:doctype/:name       → Print-friendly view                           [SPEC]
/login                      → Frappe login (redirect)                       [BUILT — Frappe native]
/403                        → Forbidden403View                              [SPEC]
```

## II.3a-TRANSFERNAMES. `AssetTransferDetailView.vue` — hiển thị tên Khoa/Vị trí/Người giữ (Vòng 16 — FR-00-TRF-01)

> **Đề mục Vòng 16 (2026-07-10 — gỡ rò Link-id thô trên phiếu Điều chuyển).** Màn `AssetTransferDetailView.vue` consume `getTransferFull` (`imm00.ts:707` → `get_transfer_full`). Trước Vòng 16, view bind `v-model="form.from_location"` / `form.from_department` / `form.from_custodian` (+ `to_*`) vào **Link-id thô** (`AC-LOC-…`/`AC-DEPT-…`/`user@…`) trên các ô disabled → người dùng không đọc được Khoa/Vị trí/Người giữ. BE nay trả 6 `*_name` + `asset_name` (xem 05 §III.12-NAMES). FE render tên đọc được, fallback `'—'` khi rỗng, **KHÔNG còn Link-id thô**.

**Contract type (`imm00.ts` — `getTransferFull`/`listTransfers` trả thêm):**

```ts
interface Transfer {
  // … field cũ (from_location, to_department, … = Link-id thô, GIỮ cho POST update_transfer) …
  asset_name?: string
  from_location_name?: string;  to_location_name?: string
  from_department_name?: string; to_department_name?: string
  from_custodian_name?: string;  to_custodian_name?: string
}
```

**Quy tắc render (BR-FE):**
- **Ô "Từ (nguồn)"** (luôn read-only): thay `<input v-model="form.from_location">` bằng **hiển thị read-only** `form.from_location_name || '—'` (tương tự `from_department_name`, `from_custodian_name`). KHÔNG bind Link-id thô.
- **Ô "Đến (đích)"**: khi **KHÔNG editable** (Approved/Received/Rejected/Cancelled) → hiển thị `form.to_location_name || '—'` (đọc). Khi **editable** (Pending Approval) → GIỮ input Link-id để sửa + POST `update_transfer` (picker Link-id thô là nợ UX RIÊNG, [ROADMAP], KHÔNG mở Vòng 16). ⇒ chế-độ-đọc KHÔNG rò Link-id; chế-độ-sửa vẫn gửi được PK.
- **Ô "Thiết bị"** (line 152, hiện bind `form.asset` = Link-id thô `AC-ASSET-…`): hiển thị `form.asset_name || form.asset` (ưu tiên tên).
- Fallback rỗng dùng `'—'` (em-dash) — **KHÔNG** hiển thị chuỗi rỗng câm hay Link-id.

**Ngoài scope Vòng 16 ([BACKLOG]):** khối "Thông tin xử lý" (line 224-236) hiển thị `form.approved_by` / `form.rejected_by` / `form.received_by` = **User-id thô** (leak riêng). BE Vòng 16 CHỐT chỉ thêm 6 `*_name` from/to (KHÔNG `approved_by_name`…) → FE KHÔNG tự bịa field; leak processor-name là đề mục kế (cần BE enrich thêm `*_by_name` trước).

**Mobile feature 12 (Nhận bàn giao scan-confirm):** app mobile (repo UI riêng) consume `list_transfers`/`get_transfer` đã enrich → màn "Nhận bàn giao" render từ→đến Khoa/Vị trí/Người giữ đọc được cùng contract (One-Version). FE web + mobile chia 1 BE contract.

**Test (vitest — component-mount):** mount `AssetTransferDetailView` với stub `getTransferFull` trả `{from_department_name:'', from_location_name:'Khoa HSTC', to_custodian_name:'Nguyễn Văn A', …}` → assert (1) ô "Từ · Phòng ban" render `'—'` (rỗng→fallback), (2) ô "Từ · Vị trí" render `'Khoa HSTC'`, (3) 0 chuỗi `AC-DEPT-`/`AC-LOC-`/`@` nào trong DOM ô read-only, (4) chế-độ-sửa (Pending) `to_location` vẫn là input sửa được.

## II.3a-TRANSFERAUTHZ. `AssetTransferDetailView.vue` — gate 3 nút CTA theo capability server-driven (Vòng 48 — CR-WF-00-TRANSFER-AUTHZ / FR-00-TRF-02, GATE-8/LL-FE-51)

> **Đề mục Vòng 48 (Trục A — gỡ dead-button).** Hiện `AssetTransferDetailView.vue` render 3 nút CTA CHỈ theo `status` (`isPending` → Phê duyệt/Từ chối; `isApproved` → Xác nhận tiếp nhận), KHÔNG theo capability → **dead-button**: user thiếu quyền vẫn thấy nút (bấm approve/reject → 403; bấm "Xác nhận tiếp nhận" → THÀNH CÔNG SAI trước khi BE gate). Sau khi BE emit `can_approve`/`can_receive` (05 §III.12-AUTHZ), FE gate nút theo flag. Mirror `imm14` `DecommissionDetailView` (server-driven `can_approve`) / GATE-8.

**Computed MỚI (fail-closed — flag `undefined` → `false`):**
```ts
const canApprove = computed(() => form.value.can_approve === 1)   // undefined → false
const canReceive = computed(() => form.value.can_receive === 1)
```
> `=== 1` (KHÔNG truthy) → flag vắng/`0`/`undefined` = fail-closed = 0 nút. (BE trả int 0/1 — 05 §III.12-AUTHZ.)

**Gate template (3 nút CTA):**

| Nút | Trước (dead-button) | Sau (gated) |
|---|---|---|
| **Phê duyệt** | `v-if="isPending"` | `v-if="isPending && canApprove"` |
| **Từ chối** | `v-if="isPending"` | `v-if="isPending && canApprove"` |
| **Xác nhận tiếp nhận** | `v-if="isApproved"` | `v-if="isApproved && canReceive"` |
| Ghi chú bàn giao (textarea) | `v-if="isApproved"` | `v-if="isApproved && canReceive"` (không hiện input khi không có quyền nhận) |
| **Hủy phiếu** | `v-if="isPending"` | Vòng 48: GIỮ `v-if="isPending"` → **⚠️ SUPERSEDED Vòng 41 (CR-WF-00-CANCEL-AUTHZ): nay `v-if="canCancel"`** — xem §II.3a-CANCELAUTHZ |

> **⚠️ Restructure:** hiện Phê duyệt/Từ chối/Hủy phiếu cùng `<template v-if="isPending">`. TÁCH: Phê duyệt+Từ chối vào `<template v-if="isPending && canApprove">`; "Hủy phiếu" ra ngoài (Vòng 48 để `v-if="isPending"`; **⚠️ Vòng 41 đổi `v-if="canCancel"` — §II.3a-CANCELAUTHZ**). "Xác nhận tiếp nhận" + textarea ghi-chú-bàn-giao gate `isApproved && canReceive`.

**Boundaries (Always / Never):**
- **Always**: gate 3 nút CTA theo flag server (`can_approve`/`can_receive`); fail-closed khi flag undefined; giữ nút "Hủy phiếu" theo `isPending` (⚠️ SUPERSEDED Vòng 41 → gate theo `canCancel`; §II.3a-CANCELAUTHZ).
- **Never**: hardcode `status===`/role-name để quyết nút CTA (server-driven — GATE-8); dùng truthy thay `=== 1`; đụng logic edit-mode (`isEditable` GIỮ theo `isPending` — ⚠️ **SUPERSEDED Vòng 46 (CR-WF-00-EDIT-AUTHZ): nay `isEditable` ← `!!can_edit`** — §II.3a-EDITAUTHZ); tự gọi endpoint (chỉ đổi điều-kiện render).

**Test (vitest — component-mount):**
- stub `getTransferFull` trả `{status:'Approved', can_approve:0, can_receive:1}` → nút "Xác nhận tiếp nhận" HIỆN; `{...can_receive:0}` → KHÔNG hiện (dead-button gỡ).
- `{status:'Pending Approval', can_approve:1}` → Phê duyệt+Từ chối HIỆN; `{...can_approve:0}` → KHÔNG hiện; "Hủy phiếu" phụ thuộc `can_cancel` (⚠️ SUPERSEDED Vòng 41 — xem §II.3a-CANCELAUTHZ test-block).
- flag VẮNG (không key) → fail-closed 0 nút CTA.

## II.3a-CANCELAUTHZ. `AssetTransferDetailView.vue` — gate nút "Hủy phiếu" theo `can_cancel` server-driven (Vòng 41 — CR-WF-00-CANCEL-AUTHZ / FR-00-TRF-03, GATE-8/LL-FE-51)

> **Đề mục Vòng 41 (Trục A — bịt lỗ hủy thiếu-quyền + gỡ dead-button).** Hiện nút "Hủy phiếu" render `v-if="isPending"` (chỉ theo status) — user thiếu quyền vẫn thấy nút; bấm → trước Vòng 41 BE hủy THÀNH CÔNG SAI (missing-authz). Sau khi BE gate `cancel_transfer_request` + emit `can_cancel` (05 §III.12-CANCELAUTHZ), FE gate nút theo flag. **Supersede** §II.3a-TRANSFERAUTHZ (Vòng 48) chỗ để "Hủy phiếu" theo `isPending`. Mirror `canApprove`/`canReceive` / GATE-8.

**Computed MỚI (fail-closed — flag `undefined` → `false`):**
```ts
const canCancel = computed(() => form.value.can_cancel === 1)   // undefined → false
```
> `=== 1` (KHÔNG truthy) → flag vắng/`0`/`undefined` = fail-closed = ẩn nút. (BE trả int 0/1 — 05 §III.12-CANCELAUTHZ; `can_cancel=1` ⟺ `commissioning.write` ∧ status∈{Pending Approval, Rejected}.)

**Gate template + hint (chống silent-blank):**

| Phần tử | Trước (Vòng 48) | Sau (Vòng 41 — gated) |
|---|---|---|
| **Hủy phiếu** | `v-if="isPending"` | `v-if="canCancel"` (data-testid `cta-cancel`) |
| `showNoActionsHint` | `isApproved && !canReceive` | `(isApproved && !canReceive) \|\| (isPending && !canApprove && !canCancel)` — base user xem phiếu Pending không còn nút nào → hiện "Bạn không có quyền thao tác phiếu này" thay vì khoảng trống câm (LL-FE-23/26) |

> **⚠️ Lưu ý status Rejected:** `can_cancel=1` cả khi status `Rejected` (không chỉ Pending). Nút "Hủy phiếu" nay có thể hiện trên phiếu `Rejected` (nếu có cap) — ĐÚNG nghiệp vụ (rút phiếu đã bị từ chối). `isPending` cũ KHÔNG bao phủ Rejected → đây là mở-rộng đúng theo `can_cancel`. KHÔNG suy nút từ `status===` thô.

**Boundaries (Always / Never):**
- **Always**: gate nút "Hủy phiếu" theo `canCancel` (server flag, `=== 1` fail-closed); mở rộng `showNoActionsHint` để Pending-không-CTA không blank; chỉ đổi điều-kiện render (KHÔNG đổi hàm `cancel()` gọi `delete_transfer`).
- **Never**: hardcode `status==='Pending Approval'`/role-name để quyết nút Hủy (server-driven — GATE-8); dùng truthy thay `=== 1`; đụng `isEditable` (GIỮ theo `isPending` — edit-mode ⚠️ **nay trong scope Vòng 46: `isEditable` ← `!!can_edit`** — §II.3a-EDITAUTHZ); giữ `v-if="isPending"` cho nút Hủy (đó chính là dead-button đang gỡ).

**Test (vitest — `assetTransferDetailCtaGate.test.ts`, mirror block receive):**
- `{status:'Pending Approval', can_cancel:1}` → nút `cta-cancel` HIỆN; `{...can_cancel:0}` → ẩn + hint hiện (base user KHÔNG thấy nút — acceptance).
- `{status:'Rejected', can_cancel:1}` → nút `cta-cancel` HIỆN (rút phiếu đã từ chối).
- `{status:'Pending Approval'}` (không key `can_cancel`) → fail-closed ẩn.
- **Cập nhật test cũ:** 2 assert `expect(cta-cancel).exists()).toBe(true)` khi `can_approve:0` (dòng ~88-90, ~130) → đổi thành phụ thuộc `can_cancel` (thêm `can_cancel` vào stub `mountWith`). `vue-tsc --noEmit` sạch.

## II.3a-EDITAUTHZ. `AssetTransferDetailView.vue` — `isEditable` ← `can_edit` server-driven (Vòng 46 — CR-WF-00-EDIT-AUTHZ / FR-00-TRF-04, GATE-8/LL-FE-51)

> **Đề mục Vòng 46 (Trục A — bịt custody-hole edit + gỡ dead-affordance).** Hiện `isEditable = computed(() => isPending.value)` (`:26`) — CHỈ theo status ⇒ **mọi user** (kể cả chỉ `inventory.read`) thấy form editable + nút "Lưu thay đổi" trên phiếu Pending; bấm Lưu → trước Vòng 46 BE `update_transfer` cập nhật field THÀNH CÔNG SAI (missing-authorization write / custody-hole). Sau khi BE gate `update_transfer` + emit `can_edit` (05 §III.12-EDITAUTHZ), FE bind `isEditable` theo flag server. **HOÀN TẤT** bộ-bốn server-driven `canApprove`/`canReceive`/`canCancel`/`isEditable` — supersede §II.3a-TRANSFERAUTHZ (Vòng 48) + §II.3a-CANCELAUTHZ (Vòng 41) chỗ để "`isEditable` GIỮ theo `isPending`". Mirror `!!form.value.can_*` / GATE-8.

**Computed ĐỔI (`:26` — fail-closed, flag `undefined` → `false`):**
```ts
// TRƯỚC:  const isEditable = computed(() => isPending.value)
const isEditable = computed(() => !!form.value.can_edit)   // undefined/0 → false (mirror canApprove/canReceive/canCancel :32-37)
```
> `!!` (mirror convention `canApprove`/`canReceive`/`canCancel` `:32-37`) → flag vắng/`0`/`undefined` = fail-closed = form read-only + ẩn nút Lưu. (BE trả int 0/1 — 05 §III.12-EDITAUTHZ; `can_edit=1` ⟺ `commissioning.write` ∧ `status=='Pending Approval'`.) **`isPending` (`:24`) GIỮ NGUYÊN** (còn dùng cho gate nút Phê duyệt/Từ chối `:168` — CHỈ tách `isEditable` khỏi `isPending`).

**Chỗ `isEditable` gate (KHÔNG đổi markup, CHỈ đổi nguồn computed):**

| Phần tử | Binding (giữ nguyên) | Hiệu ứng khi `can_edit=0` |
|---|---|---|
| `transfer_type` select `:204` · `expected_return_date` `:214` · `reason` textarea `:272` · `notes` textarea `:276` | `:disabled="!isEditable"` | disabled (read-only) |
| Block sửa `to_*`/người-nhận `:239` | `v-if="isEditable"` | ẩn |
| Block nút Lưu `:279` + nút "Lưu thay đổi" `:281-282` | `v-if="isEditable"` | ẩn nút "Lưu thay đổi" |

> **INVARIANT button-affordance ⇔ action:** `can_edit=1` ⇒ form editable + nút Lưu hiện ⇒ `save()` (`:90` gọi `updateTransfer`) KHÔNG bị BE 403 (parity — BE `update_transfer` gate CÙNG cap `commissioning.write` mà `can_edit` suy ra). Base user / `inventory.read` → `can_edit=0` → form read-only, KHÔNG thấy nút Lưu (0 dead-affordance).

**Type (`frontend/src/types/imm00.ts` — interface phiếu detail):** thêm `can_edit?: 0 | 1` (mirror `can_approve`/`can_receive`/`can_cancel` optional int đã có; `form.value` bind từ `getTransferFull` response).

**Boundaries (Always / Never):**
- **Always**: bind `isEditable` theo `!!form.value.can_edit` (server flag fail-closed); GIỮ markup `:disabled="!isEditable"` / `v-if="isEditable"` (chỉ đổi nguồn computed); giữ `isPending` cho gate nút Phê duyệt/Từ chối; thêm `can_edit` vào type.
- **Never**: giữ `isEditable = isPending.value` (đó chính là custody-hole đang gỡ); hardcode `status===`/role-name để quyết edit-mode (server-driven — GATE-8, chống RBAC dead-gate); dùng `isPending` cho `isEditable`; đụng hàm `save()`/`updateTransfer` call (CHỈ đổi điều-kiện render/disable).

**Test (vitest — `AssetTransferDetailView` / mirror block CTA-gate):**
- stub `getTransferFull` trả `{status:'Pending Approval', can_edit:1}` → form fields KHÔNG disabled + nút "Lưu thay đổi" HIỆN.
- `{status:'Pending Approval', can_edit:0}` → form fields `disabled` + nút "Lưu thay đổi" ẩn (base user KHÔNG sửa được dù phiếu Pending — acceptance).
- `{status:'Pending Approval'}` (không key `can_edit`) → fail-closed read-only.
- `{status:'Approved', can_edit:0}` → read-only (sai status → 0). `vue-tsc --noEmit` sạch.

## II.3b. QR deep-link `/a/:token` — resolve + redirect (ADR-001 A2 / V3)

> **Đề mục A2.** Route ngắn `/a/:token` = đích camera điện thoại quét QR (URL build BE qua SSoT `_build_qr_url` — host = base-URL công khai cấu hình được `assetcore_qr_base_url`, fallback `get_url`; xem [`04 §II.1.8-QRBASE`](./04_Backend_Design.md) / BR-00-30). FE KHÔNG đụng (chỉ đọc `qr_url` từ BE). A2 CHỉ resolve + redirect — màn info đầy đủ ở `/assets/:id` (A6/V7).

**Route (`frontend/src/router/index.ts`):**
```ts
{
  path: '/a/:token',
  name: 'QrResolve',
  component: () => import('@/views/system/QrResolveView.vue'),  // NEW (A2)
  props: true,
  meta: { requiresAuth: true, title: 'Đang mở thiết bị…', requiredCapabilities: ['asset.read'] },
}
```

**Flow `QrResolveView.vue` (cập nhật A6 — đổi đích redirect):**
1. `onMounted` → gọi `resolve_qr_token(token)` (05 §III.1 `resolve_qr_token`).
2. **Thành công (200):** `router.replace({ name: 'AssetScanInfo', params: { id: data.name } })` (replace — KHÔNG để `/a/:token` trong history back). **Self-Correction A6:** ĐỔI từ `AssetDetail` (admin 926 dòng) → màn info mobile-first `AssetScanInfo` (§II.3c). **Regression test BẮT BUỘC:** `QrResolveView.test.ts` assert KHÔNG còn `push`/`replace` sang `AssetDetail` từ resolver nữa.
3. **404 (token sai):** màn lỗi rõ ràng VI — "Không tìm thấy thiết bị cho mã QR này" + nút **Quét lại** (`/qr-scan`) / **Nhập mã thủ công** / **Về trang chủ**. KHÔNG trang trắng.
4. **403 (không quyền / vendor ngoài scope):** màn lỗi VI — "Bạn không có quyền xem thiết bị này" + nút Về trang chủ. KHÔNG trang trắng.
5. **Loading:** spinner + "Đang mở thiết bị…" (resolve nhanh, nhưng phải có trạng thái chờ).

> **Tối ưu (khuyến nghị, không bắt buộc A6):** `AssetScanInfo` có thể nhận thẳng `token` (route phụ `/scan/:token`) và gọi `get_asset_scan_info(token=...)` 1 call — bỏ chặng resolver trung gian. Vòng A6 GIỮ luồng 2 chặng (resolver → `AssetScanInfo` by `id`) để regression test tối thiểu; gộp 1 chặng = `[ROADMAP]` vòng dọn.

**Auth + cap (A2):**
- Route gate `requiredCapabilities: ['asset.read']` (giữ literal `asset.read` — ADR D4; chỉ valid SAU khi BE A2 thêm domain Asset, xem 04 §III.1c-1a). KHÔNG fork sang `data.read`.
- Chưa đăng nhập → guard `beforeEach` redirect `/login?redirect=/a/:token` (deep-link giữ nguyên sau auth — đăng nhập xong quay lại resolve).
- **Cap-set version (lesson IMM-14):** BE thêm 6 cap `asset.*` → `CAP_SET_VERSION` đổi → bump hằng số `auth.ts::CAP_SET_VERSION` khớp giá trị BE mới (xem II.4b AC4) → persisted-caps cũ (rỗng `asset.*`) tự invalidate lúc init → route hoạt động sau migrate KHÔNG cần xóa localStorage tay.

## II.3c. Màn THÔNG TIN thiết bị mobile-first khi quét QR — `AssetScanInfoView.vue` (ADR-001 A6 / V7)

> **Đề mục A6.** Màn đích sau khi quét QR — **mobile-first, read-only**, KHÔNG phải `AssetDetailView` (admin 926 dòng / 5 tab). Hiển thị cốt lõi cho người dùng tại hiện trường: định danh + model + vị trí + trạng thái (pill VI) + bảo trì gần nhất. **KHÔNG cap/field/DocType/endpoint admin mới** — dùng `asset.read` + `get_asset_scan_info` (05 §III.1).

**Route MỚI (`frontend/src/router/index.ts`):**
```ts
{
  path: '/assets/:id/info',
  name: 'AssetScanInfo',
  component: () => import('@/views/asset/AssetScanInfoView.vue'),  // NEW (A6)
  props: true,
  meta: { requiresAuth: true, title: 'Thông tin thiết bị', requiredCapabilities: ['asset.read'] },
}
```
> Route name = **`AssetScanInfo`** (acceptance). Path `/assets/:id/info` (giữ tiền tố `/assets/` quen thuộc + hậu tố `/info` phân biệt với `/assets/:id` admin). KHÔNG đụng route `AssetDetail` hiện có.

**View `AssetScanInfoView.vue` (Vue 3 `<script setup lang="ts">` + TanStack Query):**
1. `onMounted`/`useQuery` → gọi `getAssetScanInfo({ name: route.params.id })` (api/imm00.ts — NEW, xem dưới). Cũng nhận `token` query nếu có (luồng gộp 1 chặng tương lai).
2. **Loading:** khối `aria-busy="true"` + spinner + "Đang tải thông tin thiết bị…". KHÔNG trang trắng.
3. **Thành công:** layout **1 cột trên mobile** (`max-w-md mx-auto`, `space-y-4`), font ≥ `text-base`, touch-target nút ≥ 44px:
   - **Header định danh:** `asset_name` (lớn, `text-lg font-semibold`) + `asset_code` (phụ) + **status pill VI** — text = `lifecycleStatusLabel(info.lifecycle_status)`, màu = `lifecycleStatusClass(info.lifecycle_status)` (cả 2 từ `constants/labels.ts`). **KHÔNG hiển thị mã EN thô** ngay cả khi `lifecycle_status` rỗng/lạ (legacy/drift): `lifecycleStatusLabel` trả nhãn VI an toàn `'Không xác định'` (FR-00-93 / BR-00-42 / ADR §D10) + `lifecycleStatusClass` trả chip trung tính gray. Xem §II.3e-PILLNOLEAK dưới. **A11y + anchor (Vòng 39 — FR-00-104 / BR-00-53):** pill mang `role="status"` + `aria-label="Trạng thái thiết bị: <nhãn VI>"` (dùng CHUNG `statusLabel` — SSoT, WCAG 1.4.1 parity badge quá hạn, KHÔNG-chỉ-bằng-màu) + `data-test="scan-status"` (anchor ổn định, đúng-1-pill). Xem §II.3e-PILLA11Y dưới.
   - **Thông tin:** `device_model_name`, `location_name` (mỗi dòng nhãn VI + giá trị; rỗng → `'Chưa gán'` qua `modelText`/`locationText` — KHÔNG `'—'` câm, vòng 22).
   - **Số serial NSX (Vòng 37 — A6-hardening, FR-00-103 / BR-00-52):** dòng **"Số serial NSX"** = `serialText` (`manufacturer_sn` nguyên văn; rỗng/null/undefined/whitespace → `'Chưa rõ'`). Định danh truy xuất NĐ98 để KTV xác nhận đúng thiết bị vật lý trước báo hỏng/tạo WO. TUYỆT ĐỐI KHÔNG fallback `info.name` (docname nội bộ). Xem §II.3d-SERIALSN dưới.
   - **Phân loại rủi ro + cờ urgency (Vòng 38 nhãn + Vòng 47 cờ — FR-00-105 / BR-00-54):** dòng **"Phân loại rủi ro"** = `riskText` (map enum EN Low/Medium/High/Critical→VI Thấp/Trung bình/Cao/Nghiêm trọng; rỗng→'Chưa phân loại'; ngoài-enum→'Khác' — vòng 38, GIỮ NGUYÊN). **Vòng 47:** khi `riskUrgent` (=`risk_classification ∈ {High, Critical}`, derive THUẦN enum-equality trên giá-trị server — **KHÔNG so client-clock**, parity overdue-SSoT vòng 21) → THÊM cờ cảnh báo trực quan (icon ⚠ + nhãn VI 'Rủi ro cao', màu cảnh báo) mang `role="status"` + `aria-label="Cảnh báo rủi ro cao: <nhãn VI>"` (dùng CHUNG `riskText` — SSoT, WCAG 1.4.1 KHÔNG-chỉ-bằng-màu) + `data-test="scan-risk-urgent"`. Low/Medium/rỗng/Khác → KHÔNG cờ (no-false-alarm). `data-test="scan-risk"` + `riskText` GIỮ NGUYÊN. Xem §II.3f-SCANRISKURGENT dưới.
   - **Bảo trì gần nhất:** nếu `last_maintenance`/`recent_maintenance` → "{event_type_label} · {date}"; nếu `null` → "Chưa có lịch sử bảo trì". `next_pm_date` → "PM kế tiếp: {date}" (rỗng → ẩn dòng).
   - **Cờ PM quá hạn (Vòng 27 B — A6-hardening, FR-00-85 / BR-00-36):** cạnh dòng "Bảo trì định kỳ kế tiếp" (`AssetScanInfoView.vue:182-187`), khi `info.pm_overdue === true` → render badge VI **"Quá hạn bảo trì"** (style cảnh báo đỏ). FE **CHỈ render cờ `pm_overdue` từ payload** — TUYỆT ĐỐI KHÔNG tự so sánh `next_pm_date` với `Date()`/đồng hồ client (SSoT quá-hạn ở BE, timezone-safe — chống lệch múi giờ máy quét vs server). `pm_overdue === false` → giữ NGUYÊN hiển thị ngày như cũ, KHÔNG badge. Xem §II.3c-PMOVERDUE dưới.
   - **Hiệu chuẩn kế tiếp + cờ quá hạn (Vòng 28 B — A6-hardening, FR-00-86 / BR-00-37 — chiều HIỆU CHUẨN):** trong CÙNG card "Bảo trì gần nhất", thêm dòng **"Hiệu chuẩn kế tiếp"** = `formatDate(info.next_calibration_date)` hoặc "Chưa lên lịch" khi rỗng; khi `info.calibration_overdue === true` → render badge VI **"Quá hạn hiệu chuẩn"** (style cảnh báo đỏ + `role="status"` + `aria-label`). FE **CHỈ render cờ `calibration_overdue` từ payload** — TUYỆT ĐỐI KHÔNG tự so `next_calibration_date` với `Date()`/client clock. `calibration_overdue === false` → giữ NGUYÊN ngày, KHÔNG badge. Xem §II.3d-CALOVERDUE dưới.
4. **Error (role=alert, VI, KHÔNG trang trắng):**
   - **403:** "Bạn không đủ quyền xem thiết bị này." + nút Về trang chủ.
   - **404:** "Không tìm thấy thiết bị." + nút Quét lại / Về trang chủ.
5. **Nút điều hướng (luôn có):** **Quét lại** (`router.push({name:'QRScan'})`) + **Về trang chủ** (`router.push({name:'Dashboard'})`). Touch-target lớn (`w-full` button mobile).
6. **READ-ONLY tuyệt đối:** KHÔNG nút edit / delete / transition / workflow. Chỉ xem + điều hướng (acceptance A6). Edit admin chỉ ở `AssetDetailView` (qua route riêng).

**API client (`frontend/src/api/imm00.ts`) — NEW:**
```ts
export interface AssetScanInfo {
  name: string; asset_code: string; asset_name: string;
  manufacturer_sn: string;   // NEW (Vòng 37 / FR-00-103 / BR-00-52) — Số serial NSX (định danh truy xuất NĐ98); BE coalesce '' → LUÔN str; FE serialText fallback 'Chưa rõ'
  device_model_name: string; location_name: string;
  lifecycle_status: string; lifecycle_status_label: string;
  last_maintenance: { event_type: string; event_type_label: string; date: string } | null;
  next_pm_date: string | null;
  pm_overdue: boolean;   // NEW (Vòng 27 B / BR-00-36) — cờ PM quá hạn derive SERVER-SIDE; FE chỉ render
  next_calibration_date: string | null;   // NEW (Vòng 28 B / BR-00-37) — ngày hiệu chuẩn kế tiếp
  calibration_overdue: boolean;            // NEW (Vòng 28 B / BR-00-37) — cờ hiệu chuẩn quá hạn derive SERVER-SIDE; FE chỉ render
  available_actions: ScanAction[];         // ADR §D1/D2/D9 — 4 CTA derive SERVER-SIDE (capability ∩ lifecycle)
}
// 4 CTA màn quét QR (BE-driven). reason VI từ BE (FR-00-92 — non-rỗng khi enabled=false); FE render nguyên văn, KHÔNG bịa.
export interface ScanAction {
  key: string; label: string; route: string; enabled: boolean; reason: string;
}
export function getAssetScanInfo(p: { name?: string; token?: string }): Promise<AssetScanInfo> {
  return get('assetcore.api.imm00.get_asset_scan_info', p)
}
```

> **Parity field-name:** mã hiện tại trả key bảo trì gần nhất là `recent_maintenance` (KHÔNG `last_maintenance`); interface mục tiêu ở trên dùng `last_maintenance`. Vòng 27 B CHỈ thêm `pm_overdue` — KHÔNG đổi tên field hiện có. View `AssetScanInfoView.vue` đọc `info.recent_maintenance` (line 174) GIỮ NGUYÊN; chỉ thêm consumer `info.pm_overdue`. Đồng bộ tên `recent_maintenance`↔`last_maintenance` = `[ROADMAP]` riêng.

#### II.3c-PMOVERDUE — Badge "Quá hạn bảo trì" (Vòng 27 B / A6-hardening, BR-00-36)

> **Đề mục Vòng 27 B (hardening / compliance signal).** Thêm tín hiệu trực quan PM quá hạn trên màn quét QR. FE **chỉ render** cờ `pm_overdue` (boolean) từ payload — SSoT quá-hạn ở BE (timezone-safe). **KHÔNG so ngày bằng client clock**, KHÔNG cap/route/store mới.

**Vị trí:** `AssetScanInfoView.vue:182-187` — block "Bảo trì định kỳ kế tiếp" trong card "Bảo trì gần nhất".

```vue
<div class="border-t border-slate-100 pt-3 flex items-center justify-between gap-3 text-sm">
  <span class="text-slate-500">Bảo trì định kỳ kế tiếp</span>
  <span class="flex items-center gap-2">
    <!-- Badge CHỈ khi BE cờ pm_overdue===true — KHÔNG tự so ngày client -->
    <span
      v-if="info.pm_overdue"
      role="status"
      aria-label="Cảnh báo: thiết bị quá hạn bảo trì"
      class="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-inset ring-red-300"
    >
      <!-- icon cảnh báo (không-chỉ-màu: có text + role + aria) -->
      Quá hạn bảo trì
    </span>
    <span class="text-right font-medium text-slate-800">
      {{ info.next_pm_date ? formatDate(info.next_pm_date) : 'Chưa lên lịch' }}
    </span>
  </span>
</div>
```

| Quy tắc FE | Lý do |
|---|---|
| Render `v-if="info.pm_overdue"` — KHÔNG tính lại từ `next_pm_date` | SSoT ở BE; client clock không đáng tin (timezone/đồng hồ máy quét) |
| Badge có **text "Quá hạn bảo trì" + `role="status"` + `aria-label`** | a11y — KHÔNG truyền tải chỉ bằng màu đỏ (WCAG 1.4.1) |
| `pm_overdue===false` → 0 badge, ngày hiển thị GIỮ NGUYÊN | non-overdue parity — KHÔNG đổi UI hiện có |
| Style cảnh báo đỏ (`bg-red-100 text-red-700 ring-red-300`) | thống nhất palette cảnh báo (tái dùng tone "Overdue" calibration `constants/labels.ts`) |

**Test (`AssetScanInfoView.test.ts`) — GREEN:** (a) mock `getAssetScanInfo` trả `pm_overdue:true` → badge "Quá hạn bảo trì" hiển thị (`getByText`/`role=status`); (b) `pm_overdue:false` → KHÔNG có text "Quá hạn bảo trì"; (c) ngày `next_pm_date` vẫn render ở cả 2 nhánh. `vue-tsc` 0 lỗi.

#### II.3d-CALOVERDUE — Dòng "Hiệu chuẩn kế tiếp" + badge "Quá hạn hiệu chuẩn" (Vòng 28 B / A6-hardening, BR-00-37)

> **Đề mục Vòng 28 B (hardening / compliance signal — chiều HIỆU CHUẨN).** Mirror II.3c-PMOVERDUE cho hiệu chuẩn. FE **chỉ render** cờ `calibration_overdue` (boolean) + ngày `next_calibration_date` từ payload — SSoT quá-hạn ở BE (timezone-safe). **KHÔNG so ngày bằng client clock**, KHÔNG cap/route/store mới. **DISTINCT** với cặp PM (Vòng 27).

**Vị trí:** dòng MỚI ngay DƯỚI block "Bảo trì định kỳ kế tiếp" (`AssetScanInfoView.vue:182-201`), trong CÙNG card "Bảo trì gần nhất". Cấu trúc song song dòng PM (`info.next_pm_date` → `info.next_calibration_date`; `info.pm_overdue` → `info.calibration_overdue`; text "bảo trì" → "hiệu chuẩn").

```vue
<div class="border-t border-slate-100 pt-3 flex justify-between gap-3 text-sm">
  <span class="text-slate-500">Hiệu chuẩn kế tiếp</span>
  <span class="flex flex-wrap items-center justify-end gap-2 text-right">
    <span class="font-medium text-slate-800">
      {{ info.next_calibration_date ? formatDate(info.next_calibration_date) : 'Chưa lên lịch' }}
    </span>
    <!-- Badge CHỈ khi BE cờ calibration_overdue===true — KHÔNG tự so ngày client -->
    <span
      v-if="info.calibration_overdue"
      role="status"
      aria-label="Cảnh báo: thiết bị quá hạn hiệu chuẩn"
      class="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-semibold text-rose-700"
    >
      <span aria-hidden="true">⚠</span>
      Quá hạn hiệu chuẩn
    </span>
  </span>
</div>
```

| Quy tắc FE | Lý do |
|---|---|
| Render `v-if="info.calibration_overdue"` — KHÔNG tính lại từ `next_calibration_date` | SSoT ở BE; client clock không đáng tin (timezone/đồng hồ máy quét) |
| Badge có **text "Quá hạn hiệu chuẩn" + `role="status"` + `aria-label`** | a11y — KHÔNG truyền tải chỉ bằng màu đỏ (WCAG 1.4.1) |
| `calibration_overdue===false` → 0 badge, ngày hiển thị GIỮ NGUYÊN | non-overdue parity |
| Ngày rỗng → "Chưa lên lịch" (parity dòng PM) | thống nhất hiển thị "chưa có lịch" |
| Style cảnh báo đỏ (`bg-rose-100 text-rose-700`) | thống nhất palette với badge PM quá hạn (cùng card) |

**Test (`AssetScanInfoView.test.ts`) — GREEN:** (a) mock `calibration_overdue:true` → badge "Quá hạn hiệu chuẩn" hiển thị (`getByText`/thứ 2 `role=status`) + ngày `next_calibration_date` vẫn render; (b) `calibration_overdue:false` → KHÔNG có text "Quá hạn hiệu chuẩn", ngày GIỮ NGUYÊN; (c) `next_calibration_date:null` → render "Chưa lên lịch"; (d) `calibration_overdue:false` NHƯNG `next_calibration_date` quá khứ → KHÔNG badge (FE KHÔNG tự so ngày). `vue-tsc` 0 lỗi.

**Auth + cap:** route gate `requiredCapabilities: ['asset.read']` (tái dùng A2 — KHÔNG cap mới). BE 403 → màn error 403 (không trang trắng); guard `beforeEach` chặn user thiếu cap trước cả khi vào view (defense-in-depth).

**KHÔNG hiển thị (mirror BE whitelist):** giá mua, khấu hao/giá trị còn lại, supplier code nội bộ, audit chain, số ĐKLH chi tiết. View chỉ render đúng các field payload trả về.

#### II.3d-SERIALSN — Dòng "Số serial NSX" (`manufacturer_sn`) qua computed `serialText` + fallback VI `'Chưa rõ'` (Vòng 37 / A6-hardening, FR-00-103 / BR-00-52) — **NEW**

> **Đề mục factory vòng 37 (2026-06-12 — Self-Correction parity định danh truy xuất NĐ98 với đường label-PDF D5).** BE bổ sung `manufacturer_sn: string` vào payload `get_asset_scan_info` (xem 04 §II.1.8d-SCANSN / 05). FE thêm dòng **"Số serial NSX"** vào card định danh để KTV cầm điện thoại quét tem **đối chiếu serial khắc trên thân máy → xác nhận đúng thiết bị vật lý** TRƯỚC khi báo hỏng / yêu cầu PM/CM/hiệu chuẩn. **FE-only render + 1 field type** — KHÔNG cap/route/store mới; `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`.

**Type (`api/imm00.ts::AssetScanInfo`):** THÊM `manufacturer_sn: string` (bắt buộc, parity BE — coalesce `''` ở BE nên LUÔN str; `getAssetScanInfo` mirror 1-1). `vue-tsc` 0.

**Computed (`AssetScanInfoView.vue`):** hằng mới `SERIAL_UNKNOWN = 'Chưa rõ'` (KHÁC `UNASSIGNED='Chưa gán'` / `ASSET_CODE_UNASSIGNED='Chưa gán mã'` — "Chưa rõ" = chưa-biết-giá-trị, đúng ngữ nghĩa serial KTV chưa nhập). Computed presence-aware (parity `modelText`/`locationText` vòng 22 + `assetCodeText` vòng 27):

```ts
const SERIAL_UNKNOWN = 'Chưa rõ'
// manufacturer_sn từ BE LUÔN là str (coalesce '' khi rỗng). Defensive runtime: trim
// rồi kiểm presence — chuỗi-có-giá-trị → render NGUYÊN VĂN (no-regress, vd 'SN-12345');
// '' / null / undefined / chỉ-whitespace → SERIAL_UNKNOWN. TUYỆT ĐỐI KHÔNG fallback
// info.name (docname Frappe nội bộ — record-ID thô, có thể hash). Thuần presentation.
const serialText = computed(() => (info.value?.manufacturer_sn ?? '').trim() || SERIAL_UNKNOWN)
```

**Render (dòng trong card định danh / card "Model & Vị trí"):**

```html
<!-- DÒNG SERIAL NSX (vòng 37): qua serialText — manufacturer_sn rỗng/null/undefined/
     whitespace → 'Chưa rõ' (SSoT VI), KHÔNG '—' câm, KHÔNG leak docname info.name. -->
<dd ... data-test="scan-serial">{{ serialText }}</dd>   <!-- nhãn "Số serial NSX" ở <dt> -->
```

| Quy tắc Vòng 37 (FE) | Lý do |
|---|---|
| `serialText` = `manufacturer_sn || 'Chưa rõ'` (presence-aware, trim) | parity no-em-dash vòng 22 (`modelText`/`locationText`); có-giá-trị → nguyên văn |
| **TUYỆT ĐỐI KHÔNG fallback `info.name`** | docname Frappe nội bộ = record-ID thô (có thể hash) — no-raw-docname-leak (parity assetCodeText vòng 27 / assetTitleText vòng 28) |
| Fallback = `'Chưa rõ'` (KHÁC `'Chưa gán'`/`'Chưa gán mã'`) | serial = chưa-biết (chưa nhập), KHÔNG phải chưa-gán-quan-hệ; no-EN-leak (i18n VI) |
| FE chỉ render str từ payload (BE coalesce `''`) | mirror BE whitelist; KHÔNG render `'null'`/`'undefined'`/`'—'` câm |

**Test (`AssetScanInfoView.test.ts`) — RED-first → GREEN:** (a) mock `manufacturer_sn:'SN-12345'` → `[data-test="scan-serial"]` text == `'SN-12345'` nguyên văn; (b) `manufacturer_sn` ∈ {`''`, `null`, `undefined`, `'   '`} → text == `'Chưa rõ'` (KHÔNG `'—'`, KHÔNG `'null'`/`'undefined'`); (c) `manufacturer_sn:''` + `name:'AST-0042-x9'` → text == `'Chưa rõ'` (KHÔNG render docname — no-leak); (d) grep `serialText` KHÔNG chứa `info.name`; đúng 1 hằng `SERIAL_UNKNOWN='Chưa rõ'`. `vue-tsc` 0 lỗi; full asset-domain vitest suite no-regression. **FE-only — KHÔNG cần reload/migrate.**

#### II.3c-ACTIONS — Cụm CTA `available_actions` + render `reason` an toàn (ADR §D1/D2/D9, FR-00-92 / BR-00-41) {#reason-render}

> **Đề mục factory vòng 7 (2026-06-11 — scan-action / reason-when-disabled).** `AssetScanInfoView.vue` render 4 CTA từ `info.available_actions` (BE-driven — FE KHÔNG tự tính quyền/lifecycle, SSoT BE D2). Mỗi nút `enabled=false` ở trạng thái **disabled + reason VI**. **Lỗi thiết kế gốc D2** (xem 02 §IV.18): khi BE trả `{enabled:false, reason:""}` (status rỗng/lạ + có cap — đã fix BE qua FR-00-92), FE phát sinh **dangling `aria-describedby`** + **trailing-rỗng `aria-label`** + mất tooltip. Vòng 7 fix BE (reason luôn non-rỗng) **VÀ** làm FE phòng-thủ-kép.

**Render (vị trí: cụm `<section>` "Thao tác nhanh" + `<ul aria-live>` reason — `AssetScanInfoView.vue:286-323`):**

| Attr nút disabled | Quy tắc | Lý do |
|---|---|---|
| `:disabled="!a.enabled"` + `:aria-disabled` | GIỮ — nút disabled không click | a11y: trạng thái rõ |
| `:title="a.enabled ? undefined : a.reason"` | reason hiển thị tooltip (BE non-rỗng ⟹ luôn có) | hover thấy lý do |
| `:aria-label` đuôi = `a.reason` thực | BE non-rỗng ⟹ KHÔNG còn `"… không khả dụng: "` trailing rỗng | screen-reader đọc đủ |
| `:aria-describedby="reason-${a.key}"` | trỏ `<li id="reason-${a.key}">` PHẢI tồn tại | **hết dangling** |

**Phòng-thủ-kép (DELTA Vòng 7 — đo được):** cụm `<li>` reason đổi filter từ `!x.enabled && x.reason` → **`!x.enabled`** (BỎ điều kiện `&& x.reason`) ⟹ MỌI nút disabled luôn có `<li id="reason-<key>">` tương ứng ⟹ `aria-describedby` KHÔNG bao giờ dangling (kể cả nếu BE — giả định — trả rỗng). Phương án thay thế tương đương: set `:aria-describedby` **có-điều-kiện** (chỉ khi `a.reason` non-rỗng). Chọn 1 (BA khuyến nghị bỏ `&& x.reason` — đơn giản + an toàn nhất; với BE non-rỗng thì hành vi không đổi cho 5 status đã biết). **KHÔNG còn nút disabled thiếu cả tooltip lẫn dòng giải thích.**

**SSoT reason ở BE — FE KHÔNG bịa:** FE render `a.reason` **nguyên văn** (`{{ a.reason }}` + `:title`/`:aria-label`); FE TUYỆT ĐỐI KHÔNG hardcode/dịch/ghép chuỗi reason (no-EN-leak — reason 100% VI từ BE). Nhãn nút lấy từ `a.label` (BE đã VI, F18) — KHÔNG hardcode. Phần info read-only (F19) + shape `available_actions` GIỮ NGUYÊN.

**Test (`AssetScanInfoView.test.ts`) — RED-first → GREEN:** (a) payload action `{enabled:false, reason:'Thiết bị đã thanh lý'}` → nút `disabled` + `title==reason` + tồn tại `<li id="reason-<key>">` (aria-describedby trỏ tới element THẬT, KHÔNG dangling) + `aria-label` kết thúc bằng reason thực (KHÔNG trailing `: `); (b) MỌI nút disabled trong payload đều có `<li>` reason tương ứng (đếm `li[id^=reason-]` == số nút disabled); (c) nút enabled → KHÔNG `aria-describedby`/`title`. `vue-tsc` 0 lỗi.

#### II.3e-PILLNOLEAK — Status pill VI an toàn: `lifecycleStatusLabel` no-EN/raw-code/empty leak (Vòng 8 — FR-00-93 / BR-00-42 / ADR §D10) {#status-pill-safe}

> **Đề mục factory vòng 8 (2026-06-11 — scan-action / status-pill no-EN-leak — Self-Correction lỗi thiết kế gốc FE-formatter).** Status pill header (§II.3c bước 3) render text qua `lifecycleStatusLabel(info.lifecycle_status)`. **Lỗi thiết kế gốc:** `lifecycleStatusLabel(v) { return LIFECYCLE_STATUS_LABEL[v] ?? v }` (`constants/labels.ts:237`) — fallback `?? v` trả mã thô khi `v` ∉ 7 mã canonical ⟹ leak mã EN/code (`'In Use'`/`'Retired'`/`'active'` legacy/drift) HOẶC box rỗng (`''` BE phát `or ""` cho asset legacy → `?? ''` → `''`). KHÁC §II.3c-ACTIONS reason (nút disabled, SSoT BE); đây là **nhãn pill** ở tầng formatter VI FE.

**Delta FE (1 SSoT formatter, `constants/labels.ts`):**

| Phần tử | Delta |
|---|---|
| Hằng mới | `export const LIFECYCLE_STATUS_UNKNOWN_LABEL = 'Không xác định'` (cạnh `LIFECYCLE_STATUS_LABEL`/`LIFECYCLE_STATUS_CLASS`). |
| `lifecycleStatusLabel` | đổi `?? v` → `?? LIFECYCLE_STATUS_UNKNOWN_LABEL` → với `v` ∉ map (mã lạ + `''`/null/undefined) trả `'Không xác định'`, KHÔNG raw, KHÔNG rỗng. |
| `lifecycleStatusClass` | **GIỮ NGUYÊN** fallback `'bg-gray-100 text-gray-600'` (mã lạ/rỗng → chip trung tính; verify giữ — KHÔNG rơi màu trạng thái khác). |
| 7 mã canonical | nhãn + màu **byte-for-byte** KHÔNG đổi (test FROZEN giữ xanh). |

**Bất biến đo được:** (1) `lifecycleStatusLabel('In Use') !== 'In Use'`, `!== 'Retired'`, `!== 'active'` (no-EN/raw-code leak); (2) `lifecycleStatusLabel('') === 'Không xác định'` (non-empty); (3) `lifecycleStatusLabel(<canonical>)` → nhãn VI cũ; (4) `lifecycleStatusClass(<lạ/rỗng>) === 'bg-gray-100 text-gray-600'`. **SSoT FE — BE KHÔNG đổi** (`or ""` giữ); pill là consumer thụ hưởng, mọi consumer khác của `lifecycleStatusLabel` cũng an toàn.

**Test:** `labels.test.ts` (RED-first — case mã-lạ/rỗng FAIL trước fix do `?? v`) + `AssetScanInfoView.test.ts` (payload `lifecycle_status` rỗng/lạ → text pill = `'Không xác định'`, snapshot/text KHÔNG chứa mã English `[A-Za-z]{2,}` ngoài từ VI có dấu). `vue-tsc` 0 lỗi; full asset-domain suite no-regression.

#### II.3e-PILLA11Y — Status pill lifecycle: a11y (`role="status"` + `aria-label` VI SSoT) + anchor ổn định `data-test="scan-status"` (Vòng 39 — FR-00-104 / BR-00-53 / ADR §D14) {#status-pill-a11y}

> **Đề mục factory vòng 39 (2026-06-12 — scan-action / status-pill a11y + test-anchor — Self-Correction lỗi thiết kế gốc: bất đối xứng a11y CÙNG card + test bám heuristic mong manh).** Status pill lifecycle (`AssetScanInfoView.vue:445-450`) render `{{ statusLabel }}` với `:class="statusClass"`. **Lỗi thiết kế gốc (2 mặt):** **(a) a11y bất đối xứng — trạng-thái-chỉ-bằng-màu:** badge "Quá hạn bảo trì"/"Quá hạn hiệu chuẩn" CÙNG màn đã có `role="status"` + `aria-label` (WCAG 1.4.1 — §II.3c-PMOVERDUE/§II.3d-CALOVERDUE) NHƯNG status pill — tín hiệu trạng-thái QUAN TRỌNG NHẤT của card định danh — KHÔNG có `role`/`aria-label`: screen-reader đọc text trần không ngữ-cảnh, và phân-biệt-trạng-thái dựa CHÍNH vào màu `statusClass` ⇒ vi phạm WCAG 1.4.1 (Use of Color); **(b) test-anchor mong manh:** pill thiếu `data-test` ⇒ test bám `findAll('span').find(s => s.classes().includes('rounded-full'))` — nhưng `rounded-full` xuất hiện **5 lần** (status pill + badge PM-overdue + badge cal-overdue + chip CTA-urgency + nút CTA) ⇒ match NHẦM phần tử → test giòn.

**Delta FE (CHỈ template — 3 attr trên `<span>` pill `:445-450`; KHÔNG đổi computed/class/logic):**

```vue
<!-- Status pill lifecycle (card định danh). Vòng 39: THÊM data-test (anchor ổn
     định — test bám selector này, KHÔNG heuristic 'rounded-full' match nhầm
     overdue-badge/CTA-chip) + role=status + aria-label VI dùng CHUNG statusLabel
     (SSoT lifecycleStatusLabel — KHÔNG rải literal). WCAG 1.4.1 parity badge quá
     hạn: trạng thái KHÔNG truyền tải CHỈ bằng màu. statusLabel/statusClass GIỮ. -->
<span
  class="shrink-0 inline-flex items-center rounded-full px-3 py-1 text-xs font-medium"
  :class="statusClass"
  data-test="scan-status"
  role="status"
  :aria-label="`Trạng thái thiết bị: ${statusLabel}`"
>
  {{ statusLabel }}
</span>
```

| Phần tử | Delta | Lý do |
|---|---|---|
| `data-test="scan-status"` | THÊM (anchor ổn định, đúng-1-pill) | test bám `[data-test="scan-status"]`, KHÔNG còn `findAll('span').find(...'rounded-full'...)` (đụng 2 overdue-badge + CTA-chip + nút CTA cùng dùng `rounded-full`) |
| `role="status"` | THÊM cố định | a11y — screen-reader nhận diện vùng tín hiệu trạng thái (parity badge quá hạn) |
| `:aria-label` | `` `Trạng thái thiết bị: ${statusLabel}` `` — **dùng CHUNG `statusLabel`** (SSoT `lifecycleStatusLabel`) | WCAG 1.4.1 — KHÔNG truyền tải CHỈ bằng màu; KHÔNG rải literal nhãn, KHÔNG hardcode wording riêng cho aria-label |
| `statusLabel` / `statusClass` / class màu | **GIỮ NGUYÊN byte-for-byte** | chỉ THÊM 3 attr; `lifecycleStatusLabel`/`lifecycleStatusClass` (fallback gray trung tính) KHÔNG đổi — KHÔNG đụng BE / `constants/labels.ts` logic |

**Bất biến đo được:** (1) `[data-test="scan-status"]` tồn tại + `role==='status'` + `aria-label !== ''`; (2) `aria-label === 'Trạng thái thiết bị: ' + statusLabel` (ghép từ CHÍNH `statusLabel` — đổi nhãn → aria-label đổi theo, KHÔNG drift); (3) **no-EN/raw-code/empty leak (parity §II.3e-PILLNOLEAK):** `lifecycle_status` rỗng/lạ (`'In Use'`/`'LegacyUnknown'`/`''`) → `statusLabel==='Không xác định'` ⇒ text pill VÀ `aria-label==='Trạng thái thiết bị: Không xác định'` — `aria-label` KHÔNG chứa mã English/code thô; (4) **exactly-one:** `findAll('[data-test="scan-status"]').length === 1` (CTA buttons + 2 overdue badges + CTA-urgency chip KHÔNG nhận selector); (5) overdue-badge a11y (`role=status`/`aria-label` của chúng) GIỮ NGUYÊN. **FE-only — BE KHÔNG đổi; `statusClass`/màu KHÔNG đổi.**

**Test:** `AssetScanInfoView.test.ts` (RED-first — assert `[data-test="scan-status"]` + `role="status"` + `aria-label` khớp `'Trạng thái thiết bị: ' + statusLabel` FAIL trước khi thêm 3 attr): (a) `lifecycle_status='Active'` → pill `data-test=scan-status`, `aria-label==='Trạng thái thiết bị: Đang hoạt động'`; (b) `''`/`'In Use'` → text VÀ aria-label = `'Trạng thái thiết bị: Không xác định'`, aria-label KHÔNG chứa `'In Use'`; (c) `findAll('[data-test="scan-status"]').length===1`; (d) overdue-badge test GIỮ XANH. `vue-tsc` 0 lỗi; full asset-domain suite no-regression. **Playwright/quét-QR-thật BLOCKED reload gunicorn --preload (HARD-STOP USER) → vitest + code-audit là gate.**

#### II.3f-SCANRISKURGENT — Dòng "Phân loại rủi ro": cờ CẢNH BÁO trực quan + a11y khi `risk_classification ∈ {High,Critical}` — derive THUẦN enum-equality từ giá-trị server (no client-clock) (Vòng 47 — FR-00-105 / BR-00-54 / ADR §D15) {#scan-risk-urgent}

> **Đề mục factory vòng 47 (2026-06-12 — scan-action / scan-risk urgency + a11y — Self-Correction lỗi thiết kế gốc: tín hiệu rủi-ro-cao render NEUTRAL giống Low/Medium).** Dòng "Phân loại rủi ro" (`AssetScanInfoView.vue:466-473`, vòng 38) render `{{ riskText }}` class `text-slate-500` NEUTRAL cho MỌI mức (`riskText`=map enum EN Low/Medium/High/Critical→VI Thấp/Trung bình/Cao/Nghiêm trọng; rỗng→'Chưa phân loại'; ngoài-enum→'Khác'). **Lỗi thiết kế gốc:** `risk_classification` là phân-loại an-toàn thiết bị (NĐ98 Class A/B/C/D — drive PM frequency/calibration bắt buộc Class C/D/Class D 24h CAPA SLA), nhưng thiết bị `High`/`Critical` KHÔNG có affordance cảnh báo nào (thị-giác lẫn a11y), ngang hàng Low/Medium — bất đối xứng CÙNG card với 2 overdue badge (§II.3c/§II.3d) + CTA-urgency (§II.3-CTA) đã mang affordance. KTV quét tem thiết bị Critical (vd máy thở ICU) KHÔNG nhận tín hiệu ưu tiên; người mù-màu/screen-reader không nhận-diện mức nguy hiểm.

**Delta FE (CHỈ `AssetScanInfoView.vue` — 1 computed + 3 hằng VI + 1 phần tử template; KHÔNG đổi `riskText`/`RISK_CLASSIFICATION_LABEL`/BE/payload):**

```ts
// Vòng 47: cờ urgency dòng "Phân loại rủi ro" — derive THUẦN enum-equality trên
// GIÁ-TRỊ-SERVER risk_classification (parity nguyên-tắc overdue-SSoT vòng 21:
// đọc enum server, TUYỆT ĐỐI KHÔNG so client-clock, KHÔNG nghiệp vụ FE). Tập
// urgency cố định = {High, Critical} (SSoT hằng RISK_URGENT_VALUES — test/grep bám).
// Low/Medium/rỗng/whitespace/ngoài-4-enum → false (no-false-alarm). riskText GIỮ NGUYÊN.
const RISK_URGENT_VALUES = ['High', 'Critical'] as const   // SSoT tập rủi-ro-cao (có thể đặt constants/labels.ts)
const RISK_URGENT_LABEL = 'Rủi ro cao'                      // nhãn VI urgency (no-EN-leak)
const RISK_URGENT_ARIA_PREFIX = 'Cảnh báo rủi ro cao: '     // tiền-tố VI aria-label (dùng CHUNG riskText)
const riskUrgent = computed(() => {
  const raw = (info.value?.risk_classification ?? '').trim()
  return (RISK_URGENT_VALUES as readonly string[]).includes(raw)   // enum-equality, KHÔNG Date()/client-clock
})
```

```vue
<!-- Dòng "Phân loại rủi ro" — data-test="scan-risk" GIỮ NGUYÊN (anchor cũ, no-regress).
     Vòng 47: KHI riskUrgent → THÊM phần tử cảnh báo (icon ⚠ + nhãn VI 'Rủi ro cao',
     màu cảnh báo amber/rose parity overdue badge) mang role="status" (BA chốt — KHÔNG
     alert: risk là thuộc-tính tĩnh, không sự-kiện ngắt) + aria-label VI dùng CHUNG
     riskText (SSoT). data-test="scan-risk-urgent" để test bám không-heuristic. -->
<p class="text-sm text-slate-500 mt-0.5 flex flex-wrap items-center gap-1.5" data-test="scan-risk">
  <span>Phân loại rủi ro: {{ riskText }}</span>
  <span
    v-if="riskUrgent"
    class="inline-flex items-center gap-1 rounded-full bg-rose-100 px-2 py-0.5 text-xs font-semibold text-rose-700"
    role="status"
    :aria-label="`${RISK_URGENT_ARIA_PREFIX}${riskText}`"
    data-test="scan-risk-urgent"
  >
    <span aria-hidden="true">⚠</span>
    {{ RISK_URGENT_LABEL }}
  </span>
</p>
```

| Phần tử | Delta | Lý do |
|---|---|---|
| `riskUrgent` (computed) | THÊM — `RISK_URGENT_VALUES.includes(raw)`, `raw=(risk_classification ?? '').trim()` | derive THUẦN enum-equality trên giá-trị server; High/Critical→true, còn lại→false; **KHÔNG `Date()`/client-clock** (parity overdue-SSoT vòng 21) |
| `data-test="scan-risk"` | **GIỮ NGUYÊN** trên dòng | no-regress anchor cũ (vòng 38) |
| `data-test="scan-risk-urgent"` | THÊM trên phần tử cảnh báo (chỉ render khi `riskUrgent`) | test bám không-heuristic; exactly-one khi true, 0 khi false |
| `role="status"` (KHÔNG `alert`) | THÊM — BA chốt | `risk_classification` tĩnh có-sẵn-khi-load → polite parity status-pill/overdue badge cùng màn; `alert` assertive ngắt SR sai ngữ-cảnh |
| `:aria-label` | `` `${RISK_URGENT_ARIA_PREFIX}${riskText}` `` — dùng CHUNG `riskText` | WCAG 1.4.1 — KHÔNG-chỉ-bằng-màu; no-EN-leak (ghép từ `riskText` VI); KHÔNG hardcode wording riêng |
| icon ⚠ + nhãn VI `RISK_URGENT_LABEL` | THÊM (text + màu cảnh báo) | non-color-only — có icon + text VI, KHÔNG chỉ màu |
| `riskText` / `RISK_CLASSIFICATION_LABEL` / 6 nhãn-mức | **GIỮ NGUYÊN byte-for-byte** | no-regress vòng 38/40 — chỉ THÊM cờ, KHÔNG đổi nhãn hiển thị |

**Bất biến đo được:** (1) High/Critical → `riskUrgent===true` + `findAll('[data-test="scan-risk-urgent"]').length===1` (icon + nhãn VI 'Rủi ro cao'); (2) **no-false-alarm:** `Low`/`Medium`/`''`/null/undefined/`'   '`/`'UNKNOWN_DRIFT'` → `false` + 0 urgent-anchor; (3) **no-client-clock:** grep source KHÔNG `Date`/`new Date`/so-ngày; tập = `RISK_URGENT_VALUES`; (4) `role==='status'` (KHÔNG `'alert'`); (5) `aria-label === 'Cảnh báo rủi ro cao: ' + riskText` (Critical→'…: Nghiêm trọng', High→'…: Cao'); (6) **no-EN-leak:** urgent-anchor+aria-label KHÔNG chứa `'High'`/`'Critical'` thô; (7) `[data-test="scan-risk"]` đúng-1 + `riskText` 6 nhãn byte-for-byte (no-regress); (8) WCAG 1.4.1 (icon+text+role+aria-label). **FE-only — BE `build_asset_scan_info` KHÔNG đổi (đã emit `risk_classification`); `constants/labels.ts` logic KHÔNG đổi (hằng urgency có thể THÊM làm SSoT).**

**Test:** `assetScanInfoRisk.test.ts` + `AssetScanInfoView.test.ts` (RED-first — urgent-anchor + `role="status"` + `aria-label` FAIL trước khi thêm): (a) `risk_classification='High'`/`'Critical'` → 1 urgent-anchor, `role=status`, `aria-label==='Cảnh báo rủi ro cao: Cao'`/`'…: Nghiêm trọng'`; (b) `'Low'`/`'Medium'`/`''`/null/`'   '`/`'UNKNOWN_DRIFT'` → 0 urgent-anchor; (c) grep source KHÔNG so client-clock; (d) `[data-test="scan-risk"]` đúng-1 + `riskText` 6 nhãn no-regress; (e) no-EN-leak. `vue-tsc` 0; full asset-domain no-regression (overdue badge/status-pill a11y/serial GIỮ XANH). **Playwright/quét-QR-thật BLOCKED reload gunicorn --preload (HARD-STOP USER) → vitest + code-audit là gate.**

### II.3d. In nhãn QR — gate `asset.print` (D6 EXECUTED Vòng 3 — least-privilege)

> **D6 (ADR-IMM00-QR-SCAN-ACTION, EXECUTED Vòng 3).** Mirror BE: in nhãn QR = quyền PRINT → FE chỉ hiện/cho-vào màn in cho user có cap **`asset.print`** (đổi từ `asset.write`). User KHÔNG có print (chỉ `asset.read`) KHÔNG thấy nút, KHÔNG vào được route (defense-in-depth với BE `require("asset.print")`). **2 cap mới** `asset.print`+`asset.qr.rotate` → `auth.ts::CAP_SET_VERSION` ĐÃ bump `v95.3388ee5629c1` → **`v97.c30c69b8974d`** (isCapCacheStale tự bỏ persisted-caps cũ). Nút "Sinh lại mã QR" gate `asset.qr.rotate` riêng (§II.3e).

| Điểm gate FE | Trước (Vòng B) | Sau (D6 EXECUTED Vòng 3) |
|---|---|---|
| Nút "In nhãn QR" — `AssetDetailView.vue` (~:388) | `v-if="can('asset.write')"` | **`v-if="can('asset.print')"`** |
| Nút "In nhãn hàng loạt" — `AssetListView.vue::canPrintLabel` | `computed(() => can('asset.write'))` | **`computed(() => can('asset.print'))`** |
| Route `AssetLabelPrint` (`/assets/labels/print`) — `router/index.ts` (~:139) | `meta.requiredCapabilities: ['asset.write']` | **`['asset.print']`** |
| Nút "Sinh lại mã QR" — `AssetDetailView.vue` (~:400) | `v-if="can('asset.write')"` | **`v-if="can('asset.qr.rotate')"`** |

- **`can('asset.print')` / `can('asset.qr.rotate')`** = `authStore.capabilities[...]` (Pinia, đã hydrate từ `get_capabilities`). DENY-safe: cap thiếu/stale → `false` → ẩn nút (KHÔNG vỡ trang — lesson IMM-14). `auth.ts::CAP_SET_VERSION` = `v97.c30c69b8974d` (đã bump).
- Nút "Chỉnh sửa" GIỮ `can('asset.write')` (sửa asset ≠ in/rotate).
- Read-only QR (`/a/:token`, `/assets/:id`, `/assets/:id/info`) GIỮ `asset.read`.
- **vue-tsc 0, vitest GREEN** sau đổi (chỉ literal cap string — KHÔNG đổi type/shape).

### II.3e. Sinh-lại (rotate) mã QR — nút "Sinh lại mã QR" + BaseModal cảnh báo (ADR-001 B-2)

> **D6 (EXECUTED Vòng 3).** `AssetDetailView` nút **"Sinh lại mã QR"** (cạnh "In nhãn QR") — vô hiệu hoá QR bị lộ + cấp token mới. Gate **`can('asset.qr.rotate')`** (TÁCH khỏi cổng in — least-privilege; persona vận hành in được NHƯNG KHÔNG rotate được). Vì rotate **vô hiệu hoá mọi nhãn đã in** (destructive về nhãn) → BẮT BUỘC xác nhận qua **BaseModal** (WAVE2 pattern — **KHÔNG `window.confirm`**, giống §III.10b-bis / §III.10d). Envelope BE ở [`05_API_Specification.md`](./05_API_Specification.md) §III.1 `regenerate_asset_qr_token`.

| Điểm | Spec |
|---|---|
| Nút "Sinh lại mã QR" — `AssetDetailView.vue` (card header QR, cạnh "In nhãn QR") | `v-if="can('asset.qr.rotate')"` (D6 — đổi từ `asset.write`; user chỉ-đọc/chỉ-print KHÔNG thấy — defense-in-depth với BE `require("asset.qr.rotate")`). |
| Xác nhận | Click → mở **`BaseModal`** cảnh báo VI: tiêu đề "Sinh lại mã QR?", nội dung **"Thao tác này sẽ vô hiệu hoá mọi nhãn QR đã in cho thiết bị này. Các tem cũ sẽ không còn quét được. Bạn có chắc chắn?"** + nút "Xác nhận" / "Huỷ". **`window.confirm` tuyệt đối KHÔNG được gọi.** API CHỈ gọi **sau** khi user bấm "Xác nhận". |
| Xác nhận → API | `regenerateAssetQrToken(route.params.id)` (api/imm00.ts — NEW, xem dưới) → **refetch asset** (invalidate query `['asset', id]` / `store.fetchAsset(id)`) để preview nhãn + `qr_url` phản ánh token MỚI → **toast VI thành công** ("Đã sinh lại mã QR. Vui lòng in lại nhãn cho thiết bị."). |
| Huỷ | Đóng modal, **no-op** (KHÔNG gọi API, KHÔNG đổi gì). |
| Lỗi 403/404/IDOR | 403 (thiếu `asset.qr.rotate`) / 404 / vendor IDOR → `notify.fromError(toApiError(e))` (toast/alert lỗi VI verbatim từ BE, KHÔNG leak raw method/token/mã EN). **Modal GIỮ MỞ** để user thử lại/huỷ. |
| **Lỗi 429 (rate-limit rotate — Vòng 27 B / FR-00-88)** | BE rotate bị throttle (BR-00-38) → **429**. `confirmRegenQr` catch nhận `ApiError.code === ErrorCode.RATE_LIMITED` (sau khi `httpStatusToCode` map — FR-00-87) HOẶC `httpStatus === 429` → hiển thị **message VI cố định** `'Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút.'` (toast warning) — **KHÔNG** render `e.message` thô (frappe trả EN "You hit the rate limit…" → EN-leak), **KHÔNG** raw-code. **Modal "Sinh lại mã QR" GIỮ MỞ** để user thử lại sau. Double-submit guard `regenerating` GIỮ NGUYÊN (reset ở `finally`). |

**API client (`api/imm00.ts`) — NEW:**
```ts
export interface RegenerateQrResult { name: string; qr_url: string }

export function regenerateAssetQrToken(asset: string): Promise<RegenerateQrResult> {
  // POST — path mirror EXACT: assetcore.api.imm00.regenerate_asset_qr_token
  return postMethod('assetcore.api.imm00.regenerate_asset_qr_token', { asset })
}
```

- **DoD FE (vitest):** assert (a) click "Sinh lại mã QR" **KHÔNG** gọi `window.confirm`, mở BaseModal, API **chưa** gọi; (b) bấm "Xác nhận" → API gọi 1 lần với đúng `id` + refetch asset + toast thành công; (c) bấm "Huỷ" → no-op (0 API call); (d) nút **ẩn** khi `can('asset.qr.rotate')` = false (mock useCapabilities — kể cả user chỉ có `asset.print`); (e) lỗi 403/404 → toast lỗi VI, KHÔNG leak token/mã EN, modal GIỮ MỞ; (f) **lỗi 429 → toast message VI `'Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút.'`, KHÔNG EN-leak ("rate limit"/"Too Many"), KHÔNG raw-code, modal GIỮ MỞ** (FR-00-88). **vue-tsc 0.**

#### II.3e-RATELIMIT — Map HTTP 429 → bucket lỗi VI (Vòng 27 B — FR-00-87/88, kèm BE BR-00-38) — **NEW**

> **Đề mục Vòng 27 B (FE).** `httpStatusToCode` (`frontend/src/api/errors.ts:118`) hiện **THIẾU `case 429`** → 429 rơi về `ErrorCode.UNKNOWN` (mis-bucket — KỂ CẢ 429 của resolve/scan đã throttle từ V12). `ErrorCode.RATE_LIMITED` ĐÃ tồn tại (`errors.ts:21`), chỉ thiếu wiring. **FE-only** — KHÔNG đụng BE; `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`.

**(1) `httpStatusToCode` — thêm case 429 (FR-00-87):**
```ts
// frontend/src/api/errors.ts — httpStatusToCode(status)
case 413: return ErrorCode.PAYLOAD_TOO_LARGE
case 417:
case 422: return ErrorCode.BUSINESS_RULE
case 429: return ErrorCode.RATE_LIMITED      // ← NEW (FR-00-87): mirror BE _HTTP_TO_CODE[429]
// case 500/503 …
```
Sau fix: axios interceptor nhánh `default` (`axios.ts:288`) build `ApiError(message, RATE_LIMITED, 429)` cho MỌI 429 (rotate + resolve/scan) thay vì `UNKNOWN`. KHÔNG đổi shape/severity code khác.

**(2) `confirmRegenQr` catch — message VI cố định cho 429 (FR-00-88):**
```ts
// frontend/src/views/asset/AssetDetailView.vue — confirmRegenQr catch
} catch (e: unknown) {
  const err = toApiError(e)
  if (err.code === ErrorCode.RATE_LIMITED || err.httpStatus === 429) {
    // 429 rotate (BR-00-38) — message VI cố định, KHÔNG render e.message (EN frappe).
    toast.warning('Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút.')
  } else {
    // 403/404/IDOR — VI verbatim từ BE.
    notify.fromError(err)
  }
  // Modal GIỮ MỞ (showRegenModal=true) — KHÔNG đóng, để user thử lại/huỷ.
} finally {
  regenerating.value = false   // double-submit guard GIỮ NGUYÊN
}
```

| Quy tắc FE | Lý do |
|---|---|
| `case 429 → RATE_LIMITED` trong `httpStatusToCode` | đóng mis-bucket UNKNOWN; áp cho MỌI 429 (rotate + resolve/scan). Mirror BE `_HTTP_TO_CODE[429]`. |
| 429 rotate → message VI cố định, KHÔNG `e.message` | frappe `RateLimitExceededError` trả EN ("You hit the rate limit…") → render thô = EN-leak. Dùng chuỗi VI cố định FE. |
| Modal "Sinh lại mã QR" GIỮ MỞ trên 429 | user retry sau ít phút mà KHÔNG mất ngữ cảnh; KHÔNG trang trắng. |
| `regenerating` (double-submit) GIỮ NGUYÊN | reset ở `finally` — KHÔNG đổi cơ chế guard. |
| grep gate | 0 EN-leak ("rate limit"/"Too Many Requests") + 0 raw-code trên đường 429 (test khẳng định). |

### II.3f. Khổ tem khi in nhãn QR — selector A4 / 50×30 / 70×40mm + `@page size` mm (ADR-001 B — print fidelity)

> **Đề mục B (print fidelity).** Bổ sung **selector khổ tem** ở CẢ 2 đường in — `AssetLabelPrintView` (in HÀNG LOẠT) và modal in-1-tem trong `AssetDetailView` — để in được trên **tem vật lý** (máy in tem nhiệt 50×30 / 70×40mm) ngoài lưới A4 nhiều-nhãn cũ. **FE-only, KHÔNG cap/field/DocType/route/BE; `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`.**

- **SSoT khổ tem:** hằng `LABEL_FORMATS` ở `frontend/src/constants/label.ts` — 1 nguồn dùng chung cho cả 2 view (tránh divergence). Mỗi format: `{ key, label (VI), pageSizeCss, qrSizePx, gridCols, physical }`.

| key | Nhãn VI | `@page size` | QR (px) | Lưới in | Ghi chú |
|---|---|---|---|---|---|
| `a4-multi` | A4 nhiều-nhãn | *(không ép `@page`)* | 140 | 2 cột / A4 | **mặc định — giữ NGUYÊN hành vi cũ (regression)** |
| `tem-50x30` | Tem 50×30mm | `50mm 30mm` | 96 | 1 nhãn/trang | tem vật lý khít khổ |
| `tem-70x40` | Tem 70×40mm | `70mm 40mm` | 132 | 1 nhãn/trang | tem vật lý khít khổ |

- **`@page { size: <mm> }` đúng kỹ thuật:** scoped CSS KHÔNG vươn tới `@page` → inject qua `<style>` global có guard (chỉ render khi chọn tem vật lý; `pageRuleFor(key)` sinh `@page { size: <mm>; margin: 0 }`). Chọn `A4 nhiều-nhãn` → **KHÔNG** inject `@page` (giữ lưới 2 cột A4 mặc định).
- **QR theo đơn vị mm:** `AssetQrLabel` nhận prop `qrSize` (px theo SSoT) + prop `format`; tem vật lý áp class `qr-label--physical` → QR + field scale theo mm, **KHÔNG còn pixel cố định 120px** → QR đủ lớn để camera điện thoại quét.
- **Giữ nguyên (no-regression):** `markLabelPrinted` ghi event chỉ sau in thật + chỉ name hợp lệ; preview-only KHÔNG ghi `label_printed`; error-bucket VI cố định (forbidden/notfound/unknown); checkbox-select + gate `can('asset.print')` (D6); ô lỗi `AC-E001` VI + `translateStatus` SSoT + `break-inside:avoid`; đường mã hoá QR vẫn encode `qr_url` (KHÔNG đổi).
- **DoD FE (vitest):** chọn `tem-50x30` → DOM chứa `@page size 50mm 30mm` + lưới 1-nhãn; `tem-70x40` → `70mm 40mm`; `a4-multi`/mặc định → KHÔNG ép `@page`, giữ lưới 2 cột A4; modal đổi khổ áp đúng `@page`/grid cho single-print + `markLabelPrinted([id])` 1 lần sau `window.print`; `AssetQrLabel` QR/field scale theo khổ (tem KHÔNG dùng 120px); regression no-leak error-bucket VI. **vue-tsc 0, eslint 0, vitest GREEN.**

### II.3f-PDF. In nhãn QR khổ tem 60×100mm qua PDF server-side — luồng iframe + preview WYSIWYG (ADR-IMM00-LABEL-PDF §D10–D12 — Vòng 2)

> **⚠️ V24 SUPERSEDE (ADR §D20):** trong `AssetDetailView` đường in nhãn legacy `window.print()` HTML **GỠ HẲN** — `AssetDetailView` CHỈ còn DUY NHẤT đường PDF khổ tem (§II.3f-PDF này). Mọi câu "GIỮ song song"/"luồng cũ regression XANH" dưới đây CHỈ còn đúng cho `AssetLabelPrintView` (batch, ngoài phạm vi V24), KHÔNG còn đúng cho `AssetDetailView`. Chi tiết symbol/CSS/test gỡ: ADR §D20.1–D20.8.

> **Đề mục LABEL-PDF Vòng 2 (FE).** USER có **máy in tem nhiệt 60×100mm** (portrait, LAN). Luồng `window.print()` + `@page` CSS cũ (§II.3f) KHÔNG đảm bảo ra đúng khổ tem (browser bỏ qua `@page mm` → in A4/lệch). **Phương án A (USER duyệt):** BE render **PDF server-side đúng khổ 60×100mm** (`print_asset_labels_pdf` — D1–D9 đã code), FE tải PDF blob → iframe ẩn → `iframe.print()` (hộp thoại in → chọn máy in tem → ra đúng khổ); preview = chính PDF đó (WYSIWYG thật). **V2: THÊM đường PDF cạnh luồng cũ (D12.7) → V24 (D20): GỠ HẲN luồng cũ khỏi `AssetDetailView`** (đường PDF là DUY NHẤT ở màn chi tiết); `AssetLabelPrintView` batch GIỮ. FE-only ở FE-tier; KHÔNG cap/field/DocType/route MỚI; `CAP_SET_VERSION` GIỮ `v97.c30c69b8974d`** (cap `asset.print` đã có từ §II.3d).

**API client (§D10) — `frontend/src/api/imm00.ts`:**
- `printAssetLabelsPdf(assets: string[], preset='tem-60x100'): Promise<Blob>` — `api.post('...print_asset_labels_pdf', {assets: JSON.stringify(assets), preset}, {responseType:'blob'})` qua axios **`api` raw** (NOT `frappeGet/frappePost` — 2 helper unwrap JSON envelope, không đọc Blob). Giữ `withCredentials`+CSRF (mặc định `api`). Batch = **1 lời gọi** giữ thứ tự `names` (BE render mỗi asset = 1 trang).
- Hằng MỚI `DEFAULT_LABEL_PRESET = 'tem-60x100'` ở `constants/label.ts` (mirror BE `_LABEL_PRESETS`/`services/imm00.py:873`). **TÁCH BIỆT** với `LabelFormatKey`/`LABEL_FORMATS` cũ (§II.3f `a4-multi`/`tem-50x30`/`tem-70x40` — đường print-CSS); KHÔNG thêm vào `LABEL_FORMATS`.

**Content-type guard (§D11 — Self-Correction CỐT LÕI):** BE trả **HTTP-200 cho CẢ** thành công (`application/pdf` blob) **LẪN** 4 nhánh lỗi nghiệp vụ `_err` (preset/empty/batch/IDOR — `application/json` envelope, KHÔNG raise→4xx). Với `responseType:'blob'`, axios interceptor **KHÔNG bắt** lỗi HTTP-200 → client PHẢI tự guard:

| Tình huống | HTTP | Content-Type | Ai bắt | Kết quả FE |
|---|---|---|---|---|
| THÀNH CÔNG | 200 | `application/pdf` | guard `extractPdfBlobOrThrow` → resolve Blob | iframe.print() |
| preset/empty-422 · IDOR-403 · batch-413 | 200 | `application/json` | guard → `res.data.text()`→JSON.parse→unwrap `{message:{error,code,http_status}}`→ **ném ApiError VI** | toast VI, **KHÔNG** iframe |
| cap-403 (`rbac.require` RAISE) · dispatcher-403 · 429 | 403/429 | application/json | axios interceptor `handle403`/`handle429` | toast VI (defense-in-depth) |

- **TUYỆT ĐỐI KHÔNG** đưa JSON-blob cho `<iframe>` (tránh in JSON thô). Guard dựa **content-type** (KHÔNG status-line — vì lỗi nghiệp vụ ở HTTP-200). Parse-fail → ApiError VI cố định (KHÔNG crash). Message VI lấy từ `envelope.error` (đã VI server-side).

**Luồng in + preview (§D12):**
- **AssetDetailView** — nút **"In nhãn QR"** (`v-if can('asset.print')`, §D12.6) → `printAssetLabelsPdf([id])` → `URL.createObjectURL(blob)` → preview `BaseModal` embed `<iframe>/<embed> src=Blob URL` (WYSIWYG — cùng file PDF sẽ in) → bấm in → `<iframe>` ẩn (`display:none`) append body → `iframe.onload`→`contentWindow.print()` (hộp thoại in → chọn máy in tem).
- **AssetListView** nút **"In nhãn hàng loạt"** (`v-if can('asset.print')`) + **AssetLabelPrintView** → `printAssetLabelsPdf(names)` **1 LẦN** toàn batch (D12.3) → cùng luồng iframe.print(). Giữ thứ tự + chỉ name hợp lệ.
- **markLabelPrinted-on-confirm (§D12.4 — audit-on-cancel):** `markLabelPrinted(names)` CHỈ ghi `label_printed` qua **nút tường minh "Đã in xong"** (ưu tiên) HOẶC `iframe.onafterprint` — **KHÔNG** ghi khi user mở hộp thoại rồi HUỶ (mirror preview-only cũ). `onafterprint` KHÔNG đảm bảo phân biệt huỷ trên mọi browser → ưu tiên nút "Đã in xong" (nếu dùng `onafterprint` → over-count nhẹ, chấp nhận + ghi rõ).
- **Revoke (§D12.5):** mọi Blob URL `URL.revokeObjectURL` SAU in/đóng modal/`onafterprint`/unmount; iframe ẩn remove khỏi DOM sau in (chống memory leak).
- **No EN-leak (§D12.8):** PDF đã VI server-side (D3); FE chỉ hiển thị PDF + toast lỗi VI — KHÔNG leak status/raw-code/email/token EN.

**No-regression (§D12.7 — ⚠️ V24/D20 thu hẹp phạm vi):** ~~luồng `window.print()` + `@page` CSS cũ trong `AssetDetailView` GIỮ song song~~ → **V24: đường legacy XOÁ khỏi `AssetDetailView`** (ADR §D20). No-regression nay = `AssetLabelPrintView` batch (`AssetLabelPrintView.test.ts`, `assetLabelFormat.test.ts`, `assetListBatchSelect.test.ts`) GIỮ XANH (vẫn `window.print()`+`LABEL_FORMATS`, ngoài phạm vi). `assetDetailQrPrint.test.ts` (đường PDF) 0 regression + grep-0 `window.print(` trong `AssetDetailView.vue` (lock `:187-194`).

**DoD FE (vitest — §D10/D11/D12):** mock `api.post` blob → (a) content-type `application/pdf` → `printAssetLabelsPdf` trả Blob (KHÔNG throw); (b) content-type `application/json` body `{message:{success:false,error:'Vui lòng chọn...',http_status:422}}` → ApiError `httpStatus===422` msg VI, **KHÔNG** trả Blob; (c) blob parse-fail → ApiError VI cố định; (d) bấm "In nhãn QR" → `printAssetLabelsPdf([id])` 1 lần + `createObjectURL` + tạo iframe + `contentWindow.print()` gọi; (e) preview src === blob URL; (f) chưa "Đã in xong" → `markLabelPrinted` KHÔNG gọi; bấm "Đã in xong" → `markLabelPrinted(names)` 1 lần (chỉ name hợp lệ); (g) đóng/onafterprint → `revokeObjectURL(url)` gọi; (h) thiếu `asset.print` → nút absent; (i) batch N asset → `api.post` **1 lần**; ~~(j) luồng `window.print()` cũ regression XANH~~ → **(j) V24/D20: `grep -c 'window.print(' AssetDetailView.vue`==0 + KHÔNG entry-point mở modal legacy (no nút "In tem"/`showLabelModal`/`label-page-rule`) + `grep -c 'markLabelPrinted(' AssetDetailView.vue`==1 (chỉ `markPrintedOnce`).** **vue-tsc 0 (no dead-import).**

**GIỚI HẠN GHI RÕ (KHÔNG tuyên bố vượt):** `print_asset_labels_pdf` là BE `.py` thêm SAU gunicorn `--preload` boot → **CHƯA live HTTP** tới khi USER reload gunicorn → **Playwright LIVE trên endpoint PDF = BLOCKED**. QA gate Vòng 2 = **vitest** (FE unit) + `bench run-tests` (BE đã GREEN Vòng 1). [USER] eval **KHÔNG** được tuyên bố "đã verify in thật trên HTTP / máy in tem".

#### II.3f-PDF-QREMPTY. `AssetQrLabel` guard `qr_url` rỗng → ô-fallback an toàn (re-verify, Vòng 30 — BR-00-49 / FR-00-100 / ADR §D20) — **NO BEHAVIOR CHANGE (parity với BE-PDF fix)**

> **Bối cảnh:** trên-màn (FE) đã AN TOÀN từ trước — `AssetQrLabel.vue:73` guard `if (!value) { qrFailed.value = true; return }` (trong `renderQr()`, SAU narrow `itemIsError`) → `qr_url` rỗng/null/undefined → KHÔNG gọi `QRCode.toDataURL` (chống QR-rác client-side) → render ô-fallback `<div class="qr-label__qr-fallback" role="alert">Không tạo được mã QR</div>` (`:123-124`). Vòng 30 fix bất đối xứng **CHỈ ở BE-PDF** (server-side `_label_block` chưa guard — §D20). FE task = **re-verify guard CÒN RĂNG** + parity nhãn VI; **KHÔNG đổi 1 dòng logic FE**.

- **Guard hiện hữu (KHÔNG sửa):** `AssetQrLabel.vue` `renderQr()` — `const value = props.label.qr_url; if (!value) { qrFailed.value = true; return }`. Narrow `itemIsError` (AC-E001) đã return TRƯỚC đó (`:71`) → guard `:73` áp cho item HỢP-LỆ nhưng `qr_url` rỗng. Empty-string `''`/`undefined`/`null` → falsy → guard bắt. Nhãn fallback VI `Không tạo được mã QR` (`:124`) = CÙNG chuỗi BE-PDF ô-QR-lỗi (§D20 parity) — KHÔNG EN-leak, KHÔNG raw token/qr_url.
- **DoD FE (vitest — revert-proof, LL-TEST-26):** (a) mount `AssetQrLabel` prop `label.qr_url=''` → `qrFailed===true` + DOM chứa `.qr-label__qr-fallback` text `Không tạo được mã QR` + KHÔNG `<canvas>`/`<img data-qr>` (KHÔNG gọi `QRCode.toDataURL`); lặp `null`/`undefined` → cùng kết quả; (b) `label.qr_url='/a/TOKEN'` (hợp lệ) → `qrFailed===false` + QR render (no-regression); (c) **revert-proof:** xoá guard `:73` (`if(!value){...}`) → test (a) ĐỎ (component cố `toDataURL('')` → qrFailed sai / junk); khôi phục → XANH (guard CÒN RĂNG). **vue-tsc 0, vitest GREEN.** **KHÔNG cần reload** (thuần FE — KHÔNG đụng BE/HTTP).

### II.3g. Cap kích thước batch nhãn QR — guard FE song song + map 413 (ADR-001 B-6 / BR-00-33 — Vòng 22)

> **Đề mục B-6 (payload-DoS cap).** Mirror BE cap `_MAX_LABEL_BATCH=200`: FE chặn user gửi request **chắc-chắn-413** (chọn quá nhiều tem) NGAY trước khi điều hướng/in, đồng thời nếu request 413 vẫn lọt (URL paste thủ công) → màn print map 413 sang **bucket lỗi VI** (KHÔNG trang trắng, KHÔNG EN-leak), parity với `QrResolveView`/`AssetScanInfoView`. **FE-only; KHÔNG cap/field/DocType/route/BE; `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`.**

- **SSoT hằng FE:** `_MAX_LABEL_BATCH = 200` ở `frontend/src/constants/label.ts` (cạnh `LABEL_FORMATS` — 1 nguồn cho cả 2 đường in; đồng bộ giá trị với `services/imm00.py::_MAX_LABEL_BATCH`). KHÔNG literal `200` rải rác trong view.
- **Guard 1 — `AssetListView.vue` (selectAll / in nhãn hàng loạt):** khi `selectedNames.length > _MAX_LABEL_BATCH` → **chặn điều hướng** sang `AssetLabelPrint` + hiện cảnh báo VI (toast/banner) `"Chỉ in tối đa 200 nhãn mỗi lần. Vui lòng chọn ít hơn."` (nội suy hằng). Nút "In nhãn hàng loạt" disable HOẶC click → cảnh báo (KHÔNG navigate). selectAll trên trang hiện tại thường ≤ page-size nên ít chạm; chạm khi user tích chọn nhiều trang/chọn-tất-cả-kết-quả.
- **Guard 2 — `AssetLabelPrintView.vue` (đọc `query.names` CSV):** parse `route.query.names` (CSV) → nếu `names.length > _MAX_LABEL_BATCH` → KHÔNG gọi `getAssetLabelDataBatch`; render thẳng **bucket lỗi VI** (cùng message) + nút quay lại danh sách. Tránh phóng request chắc-413 + tránh build N nhãn client-side.
- **Map 413 (defense-in-depth — request vẫn lọt):** nếu `getAssetLabelDataBatch`/`markLabelPrinted` trả **HTTP 413** (paste URL vượt cap, hoặc race) → handler map sang **bucket lỗi VI cố định** (`"Chỉ in tối đa 200 nhãn mỗi lần. Vui lòng chọn ít hơn."`), KHÔNG render raw `.message`, KHÔNG trang trắng, KHÔNG leak EN. Thêm `413` vào bộ phân loại lỗi của màn in cạnh `forbidden`/`notfound`/`unknown` (parity error-bucket §II.3f). FE đọc `error.response?.status === 413` (hoặc envelope code tương ứng) → bucket `too-large`.
- **No-regression:** ≤ cap → luồng preview/in GIỮ NGUYÊN (selection, gate `can('asset.print')` (D6), `markLabelPrinted` sau in thật, khổ tem §II.3f, encode `qr_url`, ô `AC-E001` VI). 0/1 tem → bình thường (KHÔNG cảnh báo cap).
- **DoD FE (vitest):** `selectedNames.length == 200` → navigate OK; `== 201` → chặn + cảnh báo VI, KHÔNG navigate; `AssetLabelPrintView` với `query.names` 201 phần tử → bucket lỗi VI, KHÔNG gọi API; mock API trả 413 → màn in render bucket `too-large` VI (KHÔNG raw message, KHÔNG blank). **vue-tsc 0, eslint 0, vitest GREEN.**

## II.4. Auth Guard

| Trạng thái | Hành vi |
|---|---|
| Chưa đăng nhập | Redirect `/login?redirect=<fullPath>` (deep-link `/a/:token` giữ nguyên). **Sau login, `LoginView` chỉ honor `redirect` NỘI BỘ hợp lệ qua `isSafeInternalRedirect` — xem §II.4c (BR-00-32).** |
| Đã đăng nhập, đủ cap | Render route |
| Đã đăng nhập, thiếu cap | Redirect `Unauthorized` (`query.forbidden=<fullPath>`) |
| API 401 | Xóa Pinia auth store, redirect `/login` |
| API 403 | Toast danger "Không có quyền thực hiện hành động này" |
| API 500 | `ErrorBoundary` với retry + error ID |

### II.4b. Capability sync — stale-safe (`stores/auth.ts`)

> **SSoT FE cho gate UX.** `can(cap)` đọc `capabilities.value[cap] === true`. Cap-set lấy từ BE `get_capabilities` (05 §I.2b), persist `localStorage['assetcore.capabilities']`. **Self-Correction (2026-06-04, USER REWORK IMM-14):** persisted-caps cũ (provisioned trước release) che mất cap mới (`decommission.*`) → nút "Giải nhiệm thiết bị" không hiện. Mục này định nghĩa hành vi luôn-honor-cap-mới-nhất.

**AC3 — luôn refresh cap mới nhất (bỏ empty-check skip):**
- Bug gốc: `fetchSession()` chỉ gọi `loadCapabilities()` khi `Object.keys(capabilities.value).length === 0`. User có persisted caps non-empty (stale) → KHÔNG bao giờ refresh → cap mới không tới FE.
- Fix: **luôn** gọi `loadCapabilities()` sau khi `fetchSession()` xác thực thành công (bỏ điều kiện empty-check). `loadCapabilities()` overwrite `capabilities.value` + `localStorage` bằng cap-set mới nhất từ BE.
- `ensureFresh()` (App mount, re-hydrate nền) giữ nguyên `fetchSession()` → `loadCapabilities()` tuần tự.
- **Invariant:** sau `ensureFresh`/`fetchSession`, `localStorage['assetcore.capabilities']` CHỨA `decommission.*` (nếu user có DocPerm tương ứng).

**AC4 — version-stamp invalidation (đổi tập cap):**
- BE trả `__cap_set_version__` (05 §I.2b). FE giữ hằng/khóa persist `assetcore.capabilities.version`.
- Khi load persisted-caps lúc khởi tạo store (`loadPersistedCaps`): nếu persisted version ≠ version BE đã biết (hoặc thiếu) → **bỏ persisted caps cũ** (trả `{}`), buộc `loadCapabilities` nạp lại trước render gate-button.
- `persistCaps` lưu kèm version hiện hành; `loadCapabilities` cập nhật version từ response (loại khóa `__cap_set_version__` khỏi map cap thường: bỏ mọi key prefix `__`).
- **Invariant:** bump `CAP_SET_VERSION` ở BE → persisted caps cũ bị bỏ → nút IMM-14 "Giải nhiệm thiết bị" render sau reload mà KHÔNG cần xóa `localStorage` thủ công.

**AC5 — no-regression:** mọi cap hợp lệ hiện hữu vẫn `can()=true` đúng như cũ; legacy `isXxx` wrapper quanh `can()` không đổi; shape store export không đổi.

### II.4c. Open-redirect safety trên login deep-link — `isSafeInternalRedirect` (BR-00-32 / Vòng 21 B) — **NEW**

> **Đề mục Vòng 21 B (hardening / security).** Vá open-redirect (CWE-601) trên luồng quét QR → 401 → login → màn thông tin thiết bị. Spec ràng buộc đầy đủ: [`02_Analysis_Design.md`](./02_Analysis_Design.md) **BR-00-32**. **FE-only** — KHÔNG đụng BE/DocType/route/schema/patch; `CAP_SET_VERSION` GIỮ `v95.3388ee5629c1`.

**Lỗi thiết kế gốc:** `LoginView.vue` lấy `route.query.redirect` rồi `router.push(redirect)` THÔ ở **2 call-site** — `onMounted` (đã-auth, `:26-27`) và sau-login-OK (`:68-69`). Giá trị tới từ URL ngoài tầm kiểm soát → `/login?redirect=https://evil.com` hoặc `//evil.com` đẩy nạn nhân sang site ngoài sau khi đăng nhập (phishing/credential-harvest).

**Helper SSoT (thuần, không side-effect):**

```ts
// frontend/src/utils/navigation.ts
/**
 * True nếu `raw` là một path NỘI BỘ điều hướng được an toàn:
 * bắt đầu bằng ĐÚNG MỘT '/', KHÔNG '//' (protocol-relative), KHÔNG scheme,
 * KHÔNG backslash. Dùng CHUNG cho mọi nơi consume query.redirect.
 * Thuần chuỗi → boolean; KHÔNG import store/router/window (unit-test không cần DOM).
 */
export function isSafeInternalRedirect(raw: unknown): boolean { /* … */ }
```

**Bảng quyết định (acceptance):**

| Input `redirect` | Kết quả | Lý do |
|---|---|---|
| `/dashboard`, `/a/<token>`, `/assets/AC-ASSET-2026-00001/info` | **ACCEPT** (push y nguyên) | single-leading-slash nội bộ |
| `//evil.com` | REJECT → `/dashboard` | protocol-relative |
| `https://x.com`, `http://x.com` | REJECT → `/dashboard` | absolute external |
| `javascript:alert(1)` | REJECT → `/dashboard` | scheme nguy hiểm |
| `\evil.com`, `/\evil` | REJECT → `/dashboard` | backslash ≡ `/` ở browser → protocol-relative trá hình |
| ` //evil` (whitespace/control-prefixed) | REJECT → `/dashboard` | sau trim vẫn không phải single-`/` hợp lệ |
| chuỗi không bắt đầu bằng đúng 1 `/` | REJECT → `/dashboard` | không phải path nội bộ |
| absent / rỗng / không-string | → `/dashboard` | hành vi cũ giữ nguyên |

**Wiring 2 call-site (BOTH qua helper):**

```ts
function safeRedirect(): string {
  const raw = route.query.redirect
  return (typeof raw === 'string' && isSafeInternalRedirect(raw)) ? raw : '/dashboard'
}
// onMounted (đã-auth): router.push(safeRedirect())
// sau login OK:        router.push(safeRedirect())
```

**Invariants:**
- `grep` toàn FE → **0 chỗ** còn `router.push(<route.query.redirect>)` không qua helper.
- QR deep-link ADR-001 D4 (`/a/<token>`, `/assets/:id/info`) đều single-leading-slash → ACCEPT → luồng quét-QR→401→login→màn info GIỮ NGUYÊN (KHÔNG hồi quy).
- Guard `beforeEach` set `redirect: to.fullPath` (router `:1081`) KHÔNG đổi — chỉ phía CONSUME (LoginView) thêm validate.
- LV-FE-07 (push `/dashboard` mặc định) + LV-FE-07b (push `/incidents` redirect hợp lệ) GIỮ XANH.

**DoD:** `LoginView.test.ts` thêm block redirect-safety (RED-first) phủ đủ ACCEPT/REJECT ở CẢ 2 call-site; `vitest` full GREEN; `vue-tsc` exit 0; eslint 0 error file chạm.

## II.5. Breadcrumb

Auto sinh từ `route.meta.breadcrumb`. Max 4 cấp, cắt giữa ("…") nếu dài. Click mọi cấp trừ cấp cuối.

---

# Phần III — View Specifications

## III.1. Dashboard (/)

KPI cards hàng đầu:

| KPI | Nguồn data | Click → |
|---|---|---|
| Tổng AC Asset | `list_assets` count | `/assets` |
| PM đến hạn 7 ngày | `get_assets_due_pm?within_days=7` | `/assets?next_pm_due=7d` |
| PM đến hạn 30 ngày | `get_assets_due_pm?within_days=30` | `/assets?next_pm_due=30d` |
| CAPA Overdue | `list_capas?status=Overdue` count | `/capa?status=Overdue` |
| Incident Open | `list_incidents?status=Open` count | `/incidents?status=Open` |
| HĐ NCC sắp hết (90d) | `list_suppliers?contract_end_within=90` | `/suppliers?expiring=90d` |
| ĐK Bộ Y tế sắp hết hạn (30 ngày) | `get_overview().assets.byt_expiring_30d` | `/assets?byt_status=expiring` |
| ĐK Bộ Y tế đã hết hạn | `get_overview().assets.byt_expired` | `/assets?byt_status=expired` |

Charts:
- Donut: Asset theo lifecycle_status
- Line: PM compliance theo tháng (từ `rollup_asset_kpi`)

Recent activity: 10 Asset Lifecycle Events gần nhất.

## III.2. AC Asset — List View

Route: `/assets`

| Cột | Sort | Filter |
|---|---|---|
| `asset_code` | ✓ | — |
| `asset_name` | ✓ | search |
| `device_model` | ✓ | — |
| `department` | ✓ | select |
| `lifecycle_status` | ✓ | multi-select |
| `next_pm_date` | ✓ | date range |
| `risk_class` | ✓ | multi-select |
| `gmdn_code` | ✓ | select (autocomplete từ Asset Category) |

Filter sidebar (desktop) / drawer (mobile): `status, lifecycle_status, department, risk_class, next_pm_date` range.

Bulk actions: Gán KTV, In QR hàng loạt, Xuất Excel.

## III.3. AC Asset — Detail View

Route: `/assets/:name`

Header: `← AC-ASSET-... [Active ●] [Sửa] [Thao tác ▾]`

**6 tabs:**

| Tab | Nội dung |
|---|---|
| 1. Info HTM | asset_code, UDI, gmdn_code (readonly), BYT reg, device_model, class, risk, custodian, location |
| 2. Vòng đời | Timeline Asset Lifecycle Event (vertical timeline) |
| 3. PM & Calibration | next_pm_date, pm_interval_days, next_calibration_date, lịch sử PM/Cal |
| 4. Tài liệu | Upload IQ/OQ/PQ, manual, biên bản — Frappe File |
| 5. Incident & CAPA | Danh sách Incident + CAPA liên quan, CTA tạo mới |
| 6. Audit Trail | Log immutable của asset, nút "Verify chain" |

Action menu ▾: Đổi trạng thái (modal chọn transition hợp lệ), Transfer khoa, Decommission, In QR, Xuất lý lịch PDF.

### III.3-SURFACE — Block "Chuyển trạng thái:" server-driven từ `asset.allowed_transitions` — xóa bảng hardcode `TRANSITIONS` (Vòng 41 — CR-WF-00-LIFECYCLE-SURFACE / FR-00-109) — **NEW**

> **Đề mục Vòng 41 (Trục A · FE-hardcoded-SSoT).** `AssetDetailView.vue:154-163` giữ `const TRANSITIONS: Record<string, LifecycleStatus[]>` — **bản-sao-thứ-2** của state-machine BE (`_VALID_ASSET_TRANSITIONS`), drift câm khi BE đổi. `get_asset` nay emit `allowed_transitions` server-derive + capability-filter (xem [05 §get_asset](./05_API_Specification.md) + [04 §II.1.7-SURFACE](./04_Backend_Design.md)) → FE bỏ hardcode, chỉ render list server cấp.

**Đổi (FE Bước-4):**
- **XÓA HẲN** `const TRANSITIONS = {...}` (`AssetDetailView.vue:154-163`) — KHÔNG còn bảng transition nào ở FE (SSoT DUY NHẤT ở BE).
- `type AcAsset` (`types/imm00.ts`) **+= `allowed_transitions?: LifecycleStatus[]`** (dẫn-xuất response get_asset — như `pm_overdue?`/`calibration_overdue?` cùng file).
- Block template "Chuyển trạng thái:" (`AssetDetailView.vue:491-501`) — render từ field server:
  ```vue
  <!-- Server-driven: allowed_transitions đã capability-filter (asset.write) ở BE.
       Bỏ client can('asset.write') khỏi block — server [] khi read-only ⇒ auto-ẩn. -->
  <div v-if="store.currentAsset.allowed_transitions?.length" class="mt-4 flex flex-wrap gap-2">
    <span class="text-xs text-slate-400 self-center">Chuyển trạng thái:</span>
    <button
      v-for="s in store.currentAsset.allowed_transitions"
      :key="s"
      class="px-3 py-1 text-xs rounded-md border border-slate-300 text-slate-600 hover:bg-slate-100 transition-colors"
      @click="openTransitionModal(s as LifecycleStatus)"
    >→ {{ lifecycleLabel[s] || s }}</button>
  </div>
  ```
- **GIỮ NGUYÊN:** `lifecycleLabel` + `statusColor` (map HIỂN THỊ nhãn/màu VI — KHÔNG phải bảng transition; server trả mã canonical, FE dịch VI). `openTransitionModal` / `confirmTransition` / modal (notification-contract CR-WF-00-TRANSITION-AUTHZ Vòng 39 — 403 → `notify.fromError`). Nút "🗑️ Giải nhiệm thiết bị" (IMM-14 closure, `v-if="canDecommission"`, gate `showDecommissionButton`/`decommission.approve`) — **KHÔNG đụng** (thanh lý KHÔNG bao giờ vào block chuyển-trạng-thái).

**Boundaries (Always / Never):**

| | Ràng buộc |
|---|---|
| **ALWAYS** | Danh sách nút →state dựng **CHỈ từ** `store.currentAsset.allowed_transitions`. · Gate block = `allowed_transitions?.length` (server đã capability-filter + fetch tươi theo get_asset ⇒ authoritative). · `lifecycleLabel[s]` dịch nhãn VI (mã canonical → VI). · Nút "Hồ sơ giải nhiệm" GIỮ gate riêng `canDecommission`. |
| **NEVER** | KHÔNG giữ/thêm BẤT KỲ bảng transition hardcode nào ở FE (`TRANSITIONS`, map, mảng literal). · KHÔNG suy danh sách đích từ `lifecycle_status` thô client-side. · KHÔNG thêm `'Decommissioned'` vào block chuyển-trạng-thái (đi qua IMM-14). · KHÔNG re-gate block bằng client `can('asset.write')` (thừa + persisted-caps có thể stale). |

Test: [07 §XII TC-00-WF-SURFACE (FE vitest)](./07_Testing_QA.md).

## III.4. AC Asset — Form (Create / Edit)

| Section | Fields |
|---|---|
| §1 Thông tin cơ bản | asset_name*, asset_category (cascade → device_model), device_model (filtered by category), department, location, supplier, lifecycle_status |
| §2 Mua sắm | purchase_date, gross_purchase_amount, warranty_expiry_date, commissioning_date |
| §3 Nhận dạng HTM | manufacturer_sn, udi_code, gmdn_code (auto), medical_device_class (auto), byt_reg_no, byt_reg_expiry |
| §4 Lịch bảo trì & Hiệu chuẩn | is_pm_required (auto), pm_interval_days (auto), is_calibration_required (auto), calibration_interval_days (auto) |

### BR-00-FE-01: Cascade dropdown — Category → Device Model

**Hành vi:**
- `asset_category` điều khiển bộ lọc của SmartSelect `device_model`
- Khi `asset_category` có giá trị: SmartSelect chỉ hiện các IMM Device Model thuộc category đó
- Khi `asset_category` rỗng: SmartSelect hiện tất cả Device Model
- Khi đổi `asset_category` → reset `device_model` về rỗng → reset PM/Cal về `0`

```typescript
// AssetCreateView.vue
function onCategoryChange() {
  form.value.device_model = ''
  form.value.is_pm_required = 0
  form.value.pm_interval_days = undefined
  form.value.is_calibration_required = 0
  form.value.calibration_interval_days = undefined
  form.value.medical_device_class = undefined
  form.value.gmdn_code = ''
}
```

**SmartSelect filter:**
```html
<SmartSelect
  v-model="form.device_model"
  doctype="IMM Device Model"
  :filters="form.asset_category ? { asset_category: form.asset_category } : {}"
  placeholder="Tìm model..."
/>
```

### BR-00-FE-02: Auto-fill PM/Calibration từ Device Model

Khi `device_model` được chọn, gọi `getDeviceModel(name)` và auto-điền vào form:

| Field form | Nguồn từ model | Override được? |
|---|---|---|
| `is_pm_required` | `model.is_pm_required` | ✅ |
| `pm_interval_days` | `model.pm_interval_days` | ✅ |
| `is_calibration_required` | `model.is_calibration_required` | ✅ |
| `calibration_interval_days` | `model.calibration_interval_days` | ✅ |
| `medical_device_class` | `model.medical_device_class` | ✅ |
| `gmdn_code` | `model.gmdn_code` | ✅ (chỉ fill nếu đang rỗng) |

**Endpoint thực tế:** `GET /api/method/assetcore.api.imm00.get_device_model?name=...`  
**TS wrapper:** `getDeviceModel(name: string): Promise<ImmDeviceModel>` trong `api/imm00.ts`

```typescript
// watch trong AssetCreateView.vue — sau khi fix BR-00-FE-02
watch(() => form.value.device_model, async (modelName) => {
  if (!modelName) return
  try {
    const model = await getDeviceModel(modelName)
    // PM/Calibration — luôn điền (override default cứng)
    form.value.is_pm_required = model.is_pm_required ?? 0
    form.value.pm_interval_days = model.pm_interval_days
    form.value.is_calibration_required = model.is_calibration_required ?? 0
    form.value.calibration_interval_days = model.calibration_interval_days
    // Medical class
    if (model.medical_device_class) form.value.medical_device_class = model.medical_device_class
    // GMDN — chỉ fill nếu user chưa nhập
    if (!form.value.gmdn_code && model.gmdn_code) form.value.gmdn_code = model.gmdn_code
  } catch {
    // silent — các trường vẫn có thể điền tay
  }
})
```

**UX note:** Tất cả giá trị auto-fill đều hiển thị với hint nhẹ "(từ model)" trong label, và người dùng có thể sửa tự do sau khi được điền.

## III.4b. Reference Data — Modal Vị trí (AC Location)

Route: `/reference-data` (tab "Vị trí") · Component: `ReferenceDataView.vue`

**Đổi schema 2026-05-19:** Modal thêm/sửa Vị trí trước đây có 3 trường liên hệ (`emergency_contact`, `dept_head`, `technical_contact`). Nay gộp còn 2:

| Field UI | DocType field | Hành vi |
|---|---|---|
| Người phụ trách | `dept_head` (Link → User) | SmartSelect User |
| Số liên hệ | `contact_phone` (Data) | Tự fetch từ User khi đổi người phụ trách; có thể sửa tay |

### BR-00-FE-03: Auto-fetch số liên hệ từ người phụ trách

Khi `dept_head` đổi → gọi `GET frappe.client.get_value` lấy `["phone", "mobile_no"]` của User, ưu tiên `phone`, fallback `mobile_no`. Ghi đè `contact_phone`.

- Flag `skipPhoneFetch` chặn auto-fetch trong lúc load dữ liệu edit (không ghi đè số đã lưu DB)
- 3 trạng thái hint cạnh label "Số liên hệ":
  - `loading` → "(đang lấy số...)"
  - `found` → "(đã lấy từ người phụ trách)" — màu xanh
  - `empty` → "(người phụ trách chưa có số — nhập tay)" — màu hổ phách
- Xóa người phụ trách → reset `contact_phone` về rỗng

```typescript
async function fetchUserMobile(userEmail: string): Promise<string> {
  const res = await api.get('/api/method/frappe.client.get_value', {
    params: {
      doctype: 'User',
      filters: JSON.stringify({ name: userEmail }),
      fieldname: JSON.stringify(['phone', 'mobile_no']),
    },
  })
  const m = res.data?.message
  return m?.phone || m?.mobile_no || ''
}
```

> DocType `ac_location.json` có `fetch_from: dept_head.phone` (Frappe Desk). Vue FE thực hiện fetch phía client (BR-00-FE-03) vì FE custom không chạy fetch_from của Frappe.

## III.5. SLA Policy — Matrix View

Route: `/master-data/sla`

Ma trận 2D: `priority (P1/P2/P3/P4) × risk_class (Low/Medium/High/Critical)`.

```
           │  Low      Medium     High       Critical
───────────┼──────────────────────────────────────────
  P1       │ 30/4h    15/2h      10/1h       5/30m
  P2       │ 60/8h    30/4h      20/2h      10/1h
  P3       │ 240/24h  120/12h    60/8h      30/4h
  P4       │ 480/72h  240/48h   120/24h     60/12h

  (Response minutes / Resolution time)
```

Cell clickable → modal edit. Row `is_default` highlight `primary-50`.

## III.6. IMM Audit Trail — Log View

Route: `/audit-trail` — **Read-only**. Không có nút Create / Edit / Delete.

Nút **Verify chain integrity** → spinner → modal kết quả:
- ✅ "Chain toàn vẹn — N entries, from HASH_0 to HASH_N"
- ❌ "Phát hiện break tại entry #K, hash_prev không khớp"

Row click → drawer phải hiển thị raw payload JSON.

## III.7. IMM CAPA — Workflow bar

```
[ Open ] ──▶ [ Root Cause ] ──▶ [ Corrective ] ──▶ [ Verification ] ──▶ [ Closed ]
   ●              ●                  ○                   ○                    ○
```

Warning banner đỏ nếu `due_date < today` "CAPA quá hạn (BR-00-09)".

Close CAPA: confirm modal liệt kê checklist BR-00-08.

**round 12 — cổng hiệu quả (AC-6, đồng bộ BR-00-26):**
- Nút **"Đóng CAPA"** disabled khi `effectiveness_check !== 'Effective'` (nếu form có chọn effectiveness) — chặn submit chắc chắn fail FIN-007. Tooltip: `capa.effectiveness_not_verified`.
- Khi BE trả lỗi `code=VALIDATION` + `message_code='FIN-007'` (gọi `closeCapaRecord`): hiển thị qua **notification-contract** thông báo VI `capa.effectiveness_not_verified` = "Chưa xác minh hiệu quả — không thể đóng CAPA". **KHÔNG** báo "Đã đóng", **KHÔNG** leak code thô `FIN-007` / message EN ra UI; CAPA giữ nguyên trạng thái (không Closed).
- `CAPADetailView` (`frontend/src/views/incident/CAPADetailView.vue:255`): khi `effectiveness_check` null/rỗng hiển thị `'— (chưa xác minh)'` (`capa.effectiveness_unverified_label`) — **giữ nguyên**, không đổi.

## III.8. Incident Report — Wizard 3 bước

Route: `/incidents/new`

**Bước 1 — Thông tin cơ bản:** asset*, occurred_at*, reported_by (auto), short_description*

**Bước 2 — Mức độ & Bệnh nhân:** severity*, patient_affected, patient_injury_level (conditional), witnesses table

Khi `severity = Critical AND patient_affected = true`:
```
┌──────────────────────────────────────────────────────┐
│ 🛑 BÁO CÁO BỘ Y TẾ BẮT BUỘC theo NĐ98/2021          │
│    Hồ sơ phải gửi trong 24h từ khi xảy ra sự cố.    │
└──────────────────────────────────────────────────────┘
```

**Bước 3 — Hành động tức thời:** immediate_action*, asset_status_after, create_capa checkbox, attachments.

---

## III.9. Notification Settings — Toggle email (Notification Framework Wave N1)

Route: `/settings/notifications` (folder `frontend/src/views/settings/`). Stack: Vue 3 + TS + Pinia + TanStack Query.

**Chuông in-app:** badge chuông góc phải là component **Frappe core desk** (Notification Log) — KHÔNG build lại. FE chỉ cần xác nhận hiển thị/đếm unread hoạt động.

**View `NotificationSettingsView.vue`:** một section gọn với 1 toggle:

```
┌──────────────────────────────────────────────┐
│  Thông báo                                     │
│                                                │
│  Nhận thông báo qua email          [  ●—  ]    │
│  Khi tắt, bạn vẫn nhận thông báo tại chuông.   │
└──────────────────────────────────────────────┘
```

- TanStack Query: `useQuery(['notif-prefs'], getNotificationPreferences)` → init toggle.
- `useMutation(setEmailEnabled)` → optimistic update + invalidate `['notif-prefs']`; toast lỗi nếu fail.
- API client: `frontend/src/api/notifications.ts` → `getNotificationPreferences()`, `setEmailEnabled(enabled: boolean)`. Dùng `frappePost` wrapper hiện có, `catch (e: unknown)` + `instanceof` guard.
- Store (nếu cần share): `frontend/src/stores/notifications.ts` (`defineStore('notif_prefs')`).

**Entry point (vòng 2 — UX):** thêm mục **"Cài đặt thông báo"** vào **user menu dropdown** trong `frontend/src/components/common/AppTopBar.vue` (khối "Menu items", cạnh "Hồ sơ cá nhân" / "Đổi mật khẩu"), `@click` push `/settings/notifications` (qua handler `goNotificationSettings()` gọi `closeAll()` rồi `router.push`). Lý do: trước vòng 2 route chỉ truy cập được qua gõ URL → user thật không dùng được toggle.
- **Ràng buộc cấm:** KHÔNG đụng sidebar nav / launcher / `sidebarNav.ts` / `AppSidebar.vue` / `FE_Persona_Navigation.md` (task FE-persona đang treo). Entry point đặt ở `AppTopBar.vue` (ngoài vùng treo).
- Icon SVG inline cùng style các item hiện có; label tiếng Việt; không thêm i18n key vào file messages đang treo.

---

## III.10b. Depreciation Hub — ô "Hết khấu hao" DRILLABLE (BR-05-15 / Vòng 30)

View `frontend/src/views/asset/DepreciationView.vue` (route `/assets/depreciation`).

**Bug thiết kế gốc:** card "Trạng thái cấu hình" hiển thị text câm `{{ stats.fully_depreciated }} hết KH` (`:189`) — không click được; status-filter dropdown (`:271`) không có lựa chọn "Hết khấu hao". KPI count tồn tại nhưng **không drill** về danh sách asset.

**Fix — ô "Hết khấu hao" trở thành DRILLABLE:**

| Yêu cầu | Quy tắc |
|---|---|
| State mới | Thêm `depreciationFilter = ref('')` (tách khỏi `statusFilter` — KHÔNG nhồi value `'fully_depreciated'` vào `statusFilter`/`lifecycle_status` để tránh leak sai field BE). |
| `loadList()` | Truyền `depreciation_filter: depreciationFilter.value` xuống `listAssetsDepreciation(...)`. |
| Drill từ card | Phần `… N hết KH` thành phần tử click được (button/link). Click → `depreciationFilter.value = 'fully_depreciated'` → `applyFilters()` (reset `page=1` + `loadList`). Bảng chỉ hiện asset hết KH; nhãn vẫn `'N hết KH'`. KHÔNG còn text câm. |
| Status-filter dropdown | Thêm `<option value="fully_depreciated">Hết khấu hao</option>` (nhãn VI). `@change` map value `'fully_depreciated'` → set `depreciationFilter` + clear `statusFilter`; các value lifecycle khác → set `statusFilter` + clear `depreciationFilter`. KHÔNG gửi `'fully_depreciated'` vào param `status_filter`. |
| Đồng bộ | Khi drill từ card, dropdown phản ánh lựa chọn `'fully_depreciated'` (1 nguồn UI-state). |
| Clear | Chọn "Tất cả" → clear cả `depreciationFilter` lẫn `statusFilter` → list về full. |

> **API client:** `listAssetsDepreciation` thêm optional `depreciation_filter?` (xem §V.1). BE: [imm-00/05 §III.18](./05_API_Specification.md); SoT + invariant: [imm-05/04 §2.5.1](../imm-05/04_Backend_Design.md).
> **DoD FE:** vue-tsc 0 lỗi; vitest cho DepreciationView GREEN (card count == drill rows; option "Hết khấu hao" lọc đúng; không leak `'fully_depreciated'` vào `status_filter`).

#### III.10b — Giá trị còn lại đúng cho asset KH hết — FE ZERO-CHANGE (BR-05-13 / RC-06)

**Bug user-facing (nguồn gốc ở BE — fix tại BE, KHÔNG ở FE):** asset đã khấu hao **hết** (`current_book_value=0.0`, residual=0) hiện **nguyên giá `gross`** thay vì `0đ` ở 3 chỗ render — vì BE trả phantom `gross` (idiom falsy `current_book_value or gross`). Sau khi BE route qua SoT `effective_book_value` (BR-05-13 / [imm-00/04 §III.1b](./04_Backend_Design.md)), 3 chỗ render dưới **tự hiển thị đúng** mà KHÔNG sửa logic FE:

| Render point | `DepreciationView.vue` | Sau fix BE |
|---|---|---|
| Cột "Giá trị còn lại" mỗi dòng asset | `{{ vnd(a.current_book_value) }}` (`:430`) | asset KH hết hiện **`0đ`** (trước: `gross`). |
| KPI tổng "Giá trị còn lại" | `{{ vndShort(stats.total_book_value) }}` (`:246`, `:289`) | KHÔNG còn over-count phantom `gross`. |
| Thanh "Giá trị còn lại theo Danh mục" | `{{ vndShort(c.book_value) }}` + width `c.book_value` (`:318`, `:323`) | category bar phản ánh book thật. |

> **DoD FE:** **zero-change logic** — FE render verbatim số BE trả. `vue-tsc` 0 lỗi, `vitest` GREEN **không cần sửa component** (chỉ confirm số mới đúng nếu test fixture có asset book=0.0). Đây là delta thuần BE; FE chỉ là beneficiary.

### III.10b-bis. Nút "Áp dụng khấu hao cho TẤT CẢ tài sản" (RC-03)

Trên `DepreciationView.vue`, nút global gọi `computeAllDepreciation()`. Sau khi BE trả shape 6-key mới (FR-00-52 / imm-00/05 §III.18), toast thành công hiển thị các con số VI:

| Field BE | Nhãn toast VI |
|---|---|
| `inherited` | Đã kế thừa luật khấu hao (N tài sản) |
| `generated` | Đã sinh lịch khấu hao (N) |
| `executed_rows` | Đã ghi nhận kỳ đến hạn (N) |
| `skipped_has_history` | Bỏ qua (đã có lịch sử khấu hao): N |
| `skipped_no_rule` | Bỏ qua (danh mục chưa cấu hình luật): N |

- Sau khi nút chạy xong → refetch `getDepreciationStats()` + `listAssetsDepreciation()` để `unconfigured_count` giảm và list cập nhật.
- `skipped_no_rule > 0` → gợi ý user mở Asset Category cấu hình `total_depreciation_months` (lỗi master-data, không phải lỗi hệ thống — BR-00-20).
- **DoD FE:** vue-tsc 0; vitest mock trả shape 6-key → assert toast render đủ 5 dòng + không crash khi key = 0.

### III.10d. Nút "Áp dụng khấu hao theo từng Danh mục" — BaseModal + toast (RC-05, Round-4)

`ReferenceDataView.vue` (`/master-data`, tab "Danh mục") — form sửa Category có nút **"Áp dụng khấu hao theo từng Danh mục"** gọi `applyToExistingAssets()` → `bulkRegenerateScheduleByCategory(editingName.value)`.

**Bug thiết kế gốc:** `applyToExistingAssets` dùng `window.confirm()` xác nhận (`:182-188`) — vi phạm WAVE2 pattern (confirm native không nhất quán UX, không testable). Payload BE cũ 5-key → toast không hiển thị `inherited`/`skipped_no_rule`.

**Fix:**

| Yêu cầu | Quy tắc |
|---|---|
| Xác nhận | Thay `window.confirm()` bằng **BaseModal** xác nhận (WAVE2 pattern — giống `DepreciationView` §III.10b-bis). API chỉ gọi **sau** khi user bấm "Xác nhận" trong modal; `window.confirm` tuyệt đối KHÔNG còn được gọi. |
| State | `showApplyConfirm = ref(false)` (mở modal) + `applyResult = ref<BulkRegenerateByCategoryResult \| null>(null)` (kết quả). |
| Toast kết quả | Sau khi API trả payload 7-key → toast/modal kết quả hiển thị `inherited + regenerated + skipped_has_history + skipped_no_rule + errors`. Nhãn VI (bảng dưới). KHÔNG leak raw method/token/field kỹ thuật. |
| Nhãn VI | `inherited`→"Đã kế thừa luật khấu hao (N)"; `regenerated`→"Đã sinh lại lịch khấu hao (N)"; `skipped_has_history`→"Bỏ qua (đã có lịch sử khấu hao): N"; `skipped_no_rule`→"Bỏ qua (chưa cấu hình luật / nguyên giá ≤ 0): N"; `errors`→"Lỗi: N" (chỉ hiện khi >0). |
| `skipped_no_rule > 0` | gợi ý user kiểm tra `total_depreciation_months` của Category (lỗi master-data — BR-00-20), KHÔNG báo lỗi hệ thống. |
| Type | `api/imm00.ts` đổi return type sang `BulkRegenerateByCategoryResult` (thêm `inherited` + `skipped_no_rule` — §V.1). |

- **DoD FE:** vue-tsc 0; vitest cho `ReferenceDataView` GREEN — assert (a) click nút KHÔNG gọi `window.confirm`, mở BaseModal, API **chưa** gọi; (b) bấm "Xác nhận" → API gọi 1 lần; (c) mock payload 7-key → toast/modal render đủ 5 số + không crash khi key = 0; (d) không leak raw method/token.

---

## III.10c. NĐ98 ĐKLH BYT — 2 tile dashboard DRILLABLE + chip AssetListView (BR-00-17 / Vòng 31)

**Bug thiết kế gốc:** `get_overview().assets.byt_expiring_30d` / `byt_expired` được BE trả về nhưng **không tile nào tiêu thụ** trên dashboard quản trị thiết bị; `AssetListView.vue` không có chip lọc theo ĐKLH BYT (chỉ có cột `byt_reg_expiry` tô đỏ ở `:396-397`, không drill được). → ô KPI compliance NĐ98 không hiển thị & không kiểm chứng được bằng danh sách.

**Fix A — 2 tile NĐ98 trên dashboard (Admin persona / IMM-00 overview view đang dùng):**

| Yêu cầu | Quy tắc |
|---|---|
| Tile 1 | `'ĐK Bộ Y tế sắp hết hạn (30 ngày)'`, value = `overview.assets.byt_expiring_30d`, tone **warn** (value>0) / **neutral** (value==0). Click → `router.push('/assets?byt_status=expiring')`. |
| Tile 2 | `'ĐK Bộ Y tế đã hết hạn'`, value = `overview.assets.byt_expired`, tone **danger** (value>0) / **neutral** (value==0). Click → `router.push('/assets?byt_status=expired')`. |
| value==0 | tone neutral nhưng **vẫn drill được** (list rỗng — không disable tile). |
| Nhãn | qua SSoT label (labels.ts) — KHÔNG hardcode rải rác; KHÔNG raw-EN leak. |

**Fix B — `AssetListView.vue` đọc `byt_status` + chip filter:**

| Yêu cầu | Quy tắc |
|---|---|
| Đọc route | `route.query.byt_status` ('expiring'\|'expired') → set vào filter state `f.byt_status` lúc mount; forward `byt_status` xuống `list_assets` (param mới). |
| Chip filter | Hiện chip VI `'ĐK BYT sắp hết hạn'` (expiring) / `'ĐK BYT đã hết hạn'` (expired) — nhãn qua **SSoT** (labels.ts), KHÔNG hardcode rải rác. Clear chip → bỏ param `byt_status` (router.replace) → list về full. |
| Header "Tổng N" | == `pagination.total` của `list_assets(byt_status=…)` == giá trị tile vừa click (INVARIANT BR-00-17). |
| Cột giữ nguyên | Cột `'ĐK Bộ Y tế hết hạn'` (`:396-397`) GIỮ; `byt_reg_expiry` tô đỏ khi quá hạn qua helper `isPmOverdue` hiện có; ngày render `formatDate`. KHÔNG đổi hành vi cột. |
| Conjoin | `byt_status` AND với mọi filter đang chọn (lifecycle_status/department/search…) — KHÔNG clobber; client chỉ forward param, BE merge (BR-00-17). |

> **API client:** `listAssets` thêm optional `byt_status?: 'expiring' \| 'expired'` (xem §V.1). BE: [imm-00/05 `list_assets`](./05_API_Specification.md) + INVARIANT count==drill; SoT predicate: [imm-00/04 §III.1a](./04_Backend_Design.md); compliance NĐ98: [imm-05/02 KPI-05](../imm-05/02_Analysis_Design.md).
> **DoD FE:** vue-tsc 0 lỗi; vitest GREEN (tile click → route `byt_status`; chip render VI từ SSoT; header "Tổng N" == tile value; clear chip bỏ param; tone neutral khi value==0 vẫn drill). KHÔNG raw-EN leak.

---

## III.11. Phiếu chờ tôi duyệt — `PendingApprovalsView.vue` đa-module (CR-32 APPROVAL-INBOX / BR-00-INBOX-01)

> **Hiện trạng:** view `frontend/src/views/audit/PendingApprovalsView.vue` CHỈ hiện phiếu Nghiệm thu (nguồn `listMyPendingApprovals` @`api/imm04.ts:349`, cột stage-specific, row-click hardcode `/commissioning/{name}`). **Nâng cấp:** đổi nguồn sang endpoint gộp `get_pending_approvals_inbox` ([05 §III.22](./05_API_Specification.md)) — **4 loại phiếu (CR-32: 3 · CR-42: +imm09)**: Nghiệm thu (imm04) · Điều chuyển (imm00) · Xuất kho phụ tùng (imm15) · **Nghiệm thu CM (imm09)**. BE spec + ADR: [`ADR-IMM00-APPROVAL-INBOX.md`](./ADR-IMM00-APPROVAL-INBOX.md).

### API client (`frontend/src/api/imm00.ts`)

```ts
export interface PendingApprovalItem {
  doctype: 'Asset Commissioning' | 'Asset Transfer' | 'IMM Spare Allocation' | 'Asset Repair' // CR-42 +Asset Repair
  name: string
  module: 'imm04' | 'imm00' | 'imm15' | 'imm09'  // CR-42 +imm09
  title: string
  asset: string            // '' khi chưa có (imm04)
  asset_name: string
  requested_by: string
  requested_by_name: string
  pending_since: string    // datetime string — server đã sort asc
  route: string            // deep-link server-computed, LUÔN non-empty (imm09 → /cm/work-orders/{name})
}
export interface PendingApprovalsInbox {
  items: PendingApprovalItem[]
  total: number
  by_module: { imm04: number; imm00: number; imm15: number; imm09: number }  // CR-42 +imm09
}
export const getPendingApprovalsInbox = () =>
  frappeGet<PendingApprovalsInbox>(`${BASE}.get_pending_approvals_inbox`)
```

> **🔺 CR-42 (nguồn thứ 4 imm09 — Nghiệm thu CM).** FE bổ sung nhãn `MODULE_LABEL.imm09 = 'Nghiệm thu CM'` (hoặc 'Chờ nghiệm thu CM') + `MODULE_CLASS.imm09` (badge màu phân biệt) — KHÔNG leak khóa `imm09`/EN doctype ra UI (LL-FE-53). Row-click GIỮ `router.push(item.route)` server-driven (`/cm/work-orders/{name}` đã có route `router/index.ts:360`, 0 hardcode). SoD (WO tự-đóng bị ẩn) do BE lọc — FE KHÔNG cần biết. `by_module` chip nếu render = 4 loại (số PHẢI lấy từ `by_module`). Subtitle header cập nhật để phủ 4 loại (xem Empty state bên dưới). **FE = slice sau (Bước-4) sau khi BE land nguồn-d live.**

`api/imm04.ts` `listMyPendingApprovals` + `PendingApprovalRow` **GIỮ NGUYÊN** (endpoint BE vẫn LIVE, không breaking); cleanup nếu hết consumer = [ROADMAP].

### View — hành vi

| Mục | Spec |
|---|---|
| Nguồn dữ liệu | `getPendingApprovalsInbox()` — 1 call; KHÔNG gọi thêm list imm04 riêng. |
| Nhãn module (VI) | `MODULE_LABEL: Record<module, string> = { imm04: 'Nghiệm thu', imm00: 'Điều chuyển', imm15: 'Xuất kho phụ tùng', imm09: 'Nghiệm thu CM' }` (CR-42 +imm09) + badge màu `MODULE_CLASS` phân biệt 4 loại (pattern STAGE_LABEL/STAGE_CLASS hiện có). KHÔNG leak khóa `imm04`/`imm09`/doctype EN ra UI (LL-FE-53). |
| Cột | Mã phiếu (`name`) · Loại phiếu (badge `MODULE_LABEL[module]`) · Nội dung (`title`, truncate + `:title` tooltip) · Thiết bị (`asset_name` fallback `asset` fallback '—') · Người yêu cầu (`requested_by_name` fallback `requested_by`) · Chờ từ (`formatDt(pending_since)` vi-VN — helper hiện có). |
| Deep-link | Row-click → `router.push(item.route)` — **server-driven** (ADR-…-B); FE KHÔNG tự map doctype→route, KHÔNG hardcode `/commissioning/`. |
| Sort | GIỮ thứ tự server (pending_since asc — phiếu chờ lâu nhất trên đầu); FE KHÔNG re-sort. |
| Hành động | **KHÔNG nút duyệt inline** — inbox chỉ đọc + điều hướng; Duyệt/Từ chối nằm ở detail view theo `allowed_transitions`/CTA-flag server-driven (GATE-8/LL-FE-51). |
| Empty state | Giữ pattern hiện có ("Không có phiếu nào đang chờ bạn duyệt"); subtitle header cập nhật (CR-42, phủ 4 loại): "Các phiếu nghiệm thu, điều chuyển, xuất kho phụ tùng, nghiệm thu sửa chữa (CM) đã được gửi đến bạn để duyệt." |
| Tổng/badge | Có thể hiện `total` + breakdown `by_module` (chip đếm theo loại) — optional, nếu render thì số PHẢI lấy từ `by_module` (KHÔNG tự đếm lại items). |

### Gate route/sidebar — GIỮ NGUYÊN

- Route `/approvals/pending` meta `{ requiresAuth: true }` (KHÔNG `requiredCapabilities`) @`router/index.ts:769` và sidebar item 'Phê duyệt chờ' (0 cap) @`constants/sidebarNav.ts:205` **KHÔNG ĐỔI** — user 0-quyền-duyệt thấy inbox rỗng success (BR-00-INBOX-01, không phải bug). Parity guard `sidebarRouteParity.test.ts` phải GIỮ XANH (0 cap ⇔ 0 cap — không tạo dead-gate/leak mới).

### DoD FE

- vue-tsc 0 lỗi; vitest FULL GREEN. Test mới (đề xuất `views/audit/pendingApprovalsInbox.test.ts`): render đủ **4 nhãn VI** (CR-42 +imm09='Nghiệm thu CM'; KHÔNG raw `imm04`/`imm09`/EN doctype leak) · row-click push ĐÚNG `item.route` (server-driven, không hardcode; imm09 → `/cm/work-orders/{name}`) · empty-state khi `items:[]` · không re-sort client (thứ tự render == thứ tự items).

---

# Phần IV — Pinia Stores (từ `frontend/src/stores/imm00.ts`)

> **Verified vs code 2026-05-14 (sau commits `33a9668` restructure + `820e3fe` role/launcher):** File `stores/imm00.ts` export 4 stores cho IMM-00 foundation. Các module IMM-01→16 có file store riêng (`stores/imm01.ts`, …, `stores/imm16.ts`); ngoài ra `stores/auth.ts`, `stores/dashboard.ts`, `stores/masterData.ts` là cross-cutting.

**Catalog tổng (16 stores):**

| File | Store key | Vai trò |
|---|---|---|
| `stores/auth.ts` | `auth` | Session + roles + permissions |
| `stores/dashboard.ts` | `dashboard` | Aggregated KPI cho launcher |
| `stores/masterData.ts` | `masterData` | Cross-module reference cache (locations, depts, categories, suppliers) |
| `stores/imm00.ts` | `imm00_asset` / `imm00_refdata` / `imm00_capa` / `imm00_incident` | IMM-00 foundation (4 stores trong cùng 1 file) |
| `stores/imm01.ts` | `imm01` | IMM-01 Needs Request |
| `stores/imm02.ts` | `imm02` | IMM-02 Tech Spec |
| `stores/imm03.ts` | `imm03` | IMM-03 Procurement Decision / Vendor Eval / AVL |
| `stores/imm04.ts` | `commissioning` | IMM-04 Commissioning (rename từ `imm04`) |
| `stores/imm05.ts` | `imm05` | IMM-05 Registration |
| `stores/imm06.ts` | `imm06` | IMM-06 Training & Competency |
| `stores/imm08.ts` | `imm08` | IMM-08 PM |
| `stores/imm09.ts` | `imm09` | IMM-09 Repair |
| `stores/imm11.ts` | `imm11` | IMM-11 Calibration |
| `stores/imm12.ts` | `imm12` | IMM-12 Corrective |
| `stores/imm15.ts` | `imm15` | IMM-15 Spare Parts |
| `stores/imm16.ts` | `imm16` | IMM-16 Compliance |

Stores nội bộ IMM-00 (chi tiết bên dưới):

## IV.1. `useAssetStore` — `defineStore('imm00_asset')`

```typescript
// State
const assets = ref<AcAssetListItem[]>([])
const currentAsset = ref<AcAsset | null>(null)
const pagination = ref<{ page, page_size, total, total_pages, offset }>()
const loading = ref(false)
const error = ref<string | null>(null)

// Actions
async function fetchList(params: AssetListParams = {}): Promise<void>
async function fetchOne(name: string): Promise<void>
async function transition(name: string, to_status: string, reason = ''): Promise<{ success, data }>
function reset(): void
```

## IV.2. `useRefDataStore` — `defineStore('imm00_refdata')`

Reference data (locations, departments, categories, device models, SLA policies, suppliers) với persist plugin.

```typescript
// State (persisted)
const locations = ref<AcLocation[]>([])
const departments = ref<AcDepartment[]>([])
const categories = ref<AcAssetCategory[]>([])
const deviceModels = ref<ImmDeviceModel[]>([])
const slaPolicies = ref<ImmSlaPolicy[]>([])
const suppliers = ref<AcSupplier[]>([])
const loading = ref(false)

// Actions
async function fetchAll(): Promise<void>  // Parallel fetch tất cả 6 lookups
```

## IV.3. `useCapaStore` — `defineStore('imm00_capa')`

```typescript
const capas = ref<ImmCapaRecord[]>([])
const pagination = ref(...)
const loading = ref(false)
const error = ref<string | null>(null)

async function fetchList(params: { page?, page_size?, status?, asset? }): Promise<void>
```

## IV.4. `useIncidentStore` — `defineStore('imm00_incident')`

```typescript
const incidents = ref<IncidentReport[]>([])
const pagination = ref(...)
const loading = ref(false)
const error = ref<string | null>(null)

async function fetchList(params: { page?, page_size?, status?, severity?, asset? }): Promise<void>
```

## IV.5. Helper constants export

> **Note (2026-05-19):** Các hằng số liên quan trạng thái sử dụng GMDN (cũ) đã bị loại bỏ. Bộ lọc GMDN trên AssetListView nay dựng động từ `refData.categories` (distinct `gmdn_code` + `gmdn_term`). Xem [analysis §6](../res/analysis/gmdn-asset-category-analysis.md).

---

# Phần V — API Client Layer (từ `frontend/src/api/imm00.ts`)

> **Verified vs code 2026-05-14:** `api/imm00.ts` export các hàm riêng lẻ (không phải object `imm00Api`). Wrapper `frappeCall<T>()` unwrap `.message.data` nên signatures dưới đây trả `T` thay vì `ApiResponse<T>`. File còn export inline interfaces (AssetDepreciationRow, DepreciationStats, PmSchedule, PmTemplate, FirmwareCR, DocumentRequest, DepreciationScheduleRow/Response, DepreciationPreviewRow, DeviceModelFileUploadResult).

## V.1. Key function signatures (actual exports)

```typescript
// AC Asset
export async function listAssets(params: AssetListParams): Promise<ApiResponse<PaginatedResponse<AcAssetListItem>>>
export async function getAsset(name: string): Promise<ApiResponse<AcAsset>>
export async function createAsset(data: Partial<AcAsset>): Promise<ApiResponse<{ name: string }>>
export async function updateAsset(name: string, data: Partial<AcAsset>): Promise<ApiResponse<{ name: string }>>
export async function transitionStatus(name: string, to_status: string, reason = ''): Promise<...>
export async function getAssetTimeline(name: string, page = 1, page_size = 50): Promise<...>
export async function getAssetKpi(name: string): Promise<ApiResponse<AssetKpi>>
export async function validateForOperations(name: string): Promise<ApiResponse<{ valid: boolean; reason?: string }>>
export async function deleteAsset(name: string): Promise<...>

// Audit Trail — actual endpoint names
export async function listAuditTrail(asset: string, page = 1, page_size = 50): Promise<...>
export async function verifyChain(asset: string): Promise<ApiResponse<ChainVerifyResult>>  // NOT verifyAuditChain

// SLA
export async function listSlaPolicies(): Promise<ApiResponse<ImmSlaPolicy[]>>
export async function getSlaPolicy(name: string): Promise<...>  // NOT getSlaFor
// resolve_sla_policy không có wrapper trong imm00.ts

// CAPA
export function listCapas(params): Promise<PaginatedResponse<ImmCapaRecord>>
export function getCapaOverdue(page, page_size): Promise<PaginatedResponse<ImmCapaRecord>>
export function openCapa(data: { asset, severity, description, responsible, source_type?, source_ref?, due_days? }): Promise<{ name: string }>
export function getCapa(name: string): Promise<ImmCapaRecord>
export function closeCapaRecord(name: string, data: { root_cause, corrective_action, preventive_action, effectiveness_check? }): Promise<{ name: string; status: string }>
// round 12 — khi BE trả lỗi cổng hiệu quả: code=VALIDATION (422) + message_code='FIN-007'
//   → handle qua notification-contract, hiển thị VI: "Chưa xác minh hiệu quả — không thể đóng CAPA"
//   KHÔNG báo "Đã đóng"; KHÔNG leak 'FIN-007' / message EN thô ra UI.

// Transfer
export async function getTransferFull(name: string): Promise<...>
export async function approveTransfer(name: string): Promise<...>
export async function updateTransfer(name: string, data): Promise<...>

// Depreciation (Asset Finance Hub — full coverage)
export function computeDepreciation(name: string): Promise<DepreciationComputeResult>
export function listAssetsDepreciation(params: { page?, page_size?, method_filter?, status_filter?, category_filter?, depreciation_filter? }): Promise<{ items: AssetDepreciationRow[]; pagination }>
export function getDepreciationStats(): Promise<DepreciationStats>
// RC-03: nút global backfill-rồi-sinh (xem imm-00/05 §III.18). Shape 6-key thay payload cũ.
export function computeAllDepreciation(): Promise<{ inherited; generated; executed_rows; updated_assets; skipped_has_history; skipped_no_rule }>
export async function getDepreciationSchedule(asset_name: string): Promise<DepreciationScheduleResponse>
// BR-00-25 / RC-08 (Vòng 9) — Out of Service PAUSE + RESCHEDULE: FE ZERO shape-change.
//   `AssetDepreciationSchedule.vue` render `rows[].scheduled_date` verbatim (:202) +
//   banner "Kỳ tiếp theo" = `nextPendingRow` = kỳ đầu tiên có `status === 'Pending'`
//   (:98), hiển thị `scheduled_date` của nó (:167). Khi BE dời `scheduled_date` các
//   kỳ Pending (transition Out of Service → Active), component TỰ render ngày đã dời
//   + ngày kỳ-tiếp-theo mới — KHÔNG cần đổi component, KHÔNG field mới trong response.
//   `statusLabel('Cancelled')→'Đã hủy'` + `statusLabel('Executed')→'Đã chạy'` +
//   `statusLabel('Pending')→'Chờ chạy'` GIỮ NGUYÊN (no leak raw EN). Test FE chỉ cần
//   regression: fixture Pending có scheduled_date đã-dời → render đúng + no-leak EN.
// BR-00-27 / RC-09 (Vòng 14) — Nhãn sự kiện khôi phục: FE ZERO shape-change.
//   Sửa là BE-side (1 transition Out of Service → Active ⇒ ĐÚNG 1 ALE `restored`,
//   0 `activated` — kill cặp `activated`+`restored` trùng). Dòng thời gian
//   (`CommissioningTimelineView.vue` / `AssetDetailView.vue` tab "Vòng đời" /
//   `AuditTrailListView.vue`) lấy `getAssetTimeline`/`list_lifecycle_events` ⇒ tự
//   hiển thị DUY NHẤT 1 mục cho lần khôi phục — KHÔNG cần đổi component, KHÔNG field
//   mới. Test FE = regression: fixture timeline OoS→Active có ĐÚNG 1 event `restored`
//   (KHÔNG cặp trùng).
//   ⚠️ NO RAW-EN LEAK (nếu/khi thêm map nhãn): các view trên hiện render
//   `event.event_type` THÔ (vd `AssetDetailView.vue:459`, `CommissioningTimelineView
//   .vue:169`) ⇒ rò "restored"/"activated" EN. Khuyến nghị thêm EVENT_LABEL VI cho
//   event_type của **Asset Lifecycle Event** (KHÁC EVENT_TYPES của IMM Audit Trail ở
//   `AuditTrailListView.vue:48` — vocab khác): `restored→'Khôi phục'`,
//   `activated→'Kích hoạt'`, `commissioned→'Nghiệm thu'`, `out_of_service→'Tạm ngừng'`,
//   `decommissioned→'Thanh lý'`, `pm_started→'Bắt đầu bảo trì'`,
//   `repair_opened→'Mở sửa chữa'`, `calibration_started→'Bắt đầu hiệu chuẩn'`,
//   `depreciation_stopped→'Dừng khấu hao'`, `transferred→'Luân chuyển'`. Render
//   `EVENT_LABEL[t.event_type] ?? t.event_type` (fallback raw cho event chưa map —
//   không vỡ UI). Đây là cải thiện FE độc lập; BE fix BR-00-27 KHÔNG phụ thuộc nó.
// RC-04 (Round-2): self-heal là BE-side — FE KHÔNG đổi contract. Component
// `AssetDepreciationSchedule.vue` (nút "Sinh lịch khấu hao") chỉ cần:
//   - asset CŨ thiếu luật + Category có luật → BE tự inherit → 200 {periods>0}
//     → render bảng lịch khấu hao (KHÔNG còn toast lỗi oan).
//   - chỉ hiện toast lỗi VI khi BE THẬT trả 422 (Category cũng thiếu luật) —
//     message giữ nhãn VI có tên field trong ngoặc (format round-1), KHÔNG leak
//     raw method/token/field-name kỹ thuật trần. catch (e) → showToast(e.message, true).
export async function regenerateDepreciationSchedule(asset_name: string, force: 0|1): Promise<{ periods: number; generated?: number }>
export async function previewDepreciationSchedule(params: { gross, residual, method, total_months, frequency, start_date }): Promise<DepreciationPreviewRow[]>
export async function runDueDepreciationNow(as_of?: string): Promise<{ executed_rows; updated_assets }>
// RC-05 (Round-4): payload chuẩn hoá 7-key — thêm `inherited` + `skipped_no_rule`
// (khớp `compute_all`). KHÔNG leak raw method/token; FE map sang toast (§III.10d).
export interface BulkRegenerateByCategoryResult {
  category: string
  total_assets: number
  inherited: number
  regenerated: number
  skipped_has_history: number
  skipped_no_rule: number
  errors: number
}
export async function bulkRegenerateScheduleByCategory(category_name: string): Promise<BulkRegenerateByCategoryResult>

// PM Schedule + PM Template + Firmware CR + Document Request — full CRUD wrappers
// listPmSchedules / getPmSchedule / createPmSchedule / updatePmSchedule / deletePmSchedule
// listPmTemplates / getPmTemplate / createPmTemplate / updatePmTemplate / deletePmTemplate
// listFirmwareCrs / getFirmwareCr / createFirmwareCr / updateFirmwareCr / deleteFirmwareCr
// listDocumentRequests / getDocumentRequest / createDocumentRequest / updateDocumentRequest / deleteDocumentRequest

// File upload
export async function uploadDeviceModelFile(file: File, fieldname: 'model_image'|'catalog_file', model_name = ''): Promise<DeviceModelFileUploadResult>
```

## V.2. Inline TypeScript interfaces trong `api/imm00.ts`

File này cũng export các interfaces không có trong `types/imm00.ts`:

```typescript
export interface DepreciationResult { accumulated, book_value, method?, days_elapsed?, note? }
export interface DepreciationScheduleRow { name, period_number, scheduled_date, depreciation_amount, accumulated_amount, remaining_value, status, executed_on?, journal_entry? }
export interface DepreciationScheduleResponse { asset, asset_info, rows, summary }
export interface PmSchedule { name, asset_ref, asset_name?, pm_type?, status?, pm_interval_days?, ... }
export interface PmTemplate { name, template_name, asset_category?, pm_type?, version?, checklist_items? }
export interface FirmwareCR { name, asset_ref, version_before?, version_after?, status?, ... }
export interface DocumentRequest { name, asset_ref, doc_type_required, status?, priority?, ... }
```

---

# Phần VI — i18n Shared Labels

File: `src/locales/vi.json`

```json
{
  "common": {
    "save": "Lưu",
    "cancel": "Huỷ",
    "confirm": "Xác nhận",
    "loading": "Đang tải...",
    "no_data": "Không có dữ liệu",
    "search": "Tìm kiếm",
    "filter": "Bộ lọc",
    "export": "Xuất file",
    "print": "In"
  },
  "asset": {
    "list_title": "Danh sách thiết bị",
    "create": "Tạo AC Asset mới",
    "lifecycle_status": "Trạng thái vòng đời",
    "risk_class": "Mức rủi ro",
    "next_pm_date": "Ngày PM tiếp theo",
    "gmdn_code": "Mã GMDN",
    "gmdn_in_use": "Đang sử dụng",
    "gmdn_not_in_use": "Không sử dụng",
    "decommission_confirm": "Xác nhận ngừng sử dụng thiết bị",
    "decommission_warn": "Thao tác này sẽ đổi lifecycle_status → Decommissioned và huỷ toàn bộ lịch PM/Cal"
  },
  "capa": {
    "list_title": "Danh sách CAPA",
    "overdue_warning": "CAPA quá hạn",
    "close_confirm": "Xác nhận đóng CAPA",
    "missing_root_cause": "Phải nhập phân tích nguyên nhân gốc rễ (BR-00-08)",
    "effectiveness_not_verified": "Chưa xác minh hiệu quả — không thể đóng CAPA",
    "effectiveness_unverified_label": "— (chưa xác minh)"
  },
  "audit": {
    "list_title": "Audit Trail",
    "verify_chain": "Xác minh tính toàn vẹn hash chain",
    "chain_valid": "Chain toàn vẹn",
    "chain_tampered": "Phát hiện vi phạm tại"
  },
  "incident": {
    "list_title": "Báo cáo sự cố",
    "wizard_step1": "Thông tin cơ bản",
    "wizard_step2": "Mức độ & Bệnh nhân",
    "wizard_step3": "Hành động tức thời",
    "byt_warning": "BÁO CÁO BỘ Y TẾ BẮT BUỘC theo NĐ98/2021"
  },
  "inventory": {
    "list_title": "Kho vật tư",
    "low_stock": "Tồn dưới mức tối thiểu",
    "movement_type_receipt": "Nhập kho",
    "movement_type_issue": "Xuất kho",
    "movement_type_transfer": "Chuyển kho",
    "movement_type_adjustment": "Điều chỉnh"
  }
}
```

---

# Phần VII — UX Patterns

## VII.1. Role-based UI

| Role | Dashboard ưu tiên | Action khả dụng |
|---|---|---|
| IMM Technician | "PM của tôi", "Sự cố đang xử lý" | Quick Log PM, Tạo Incident, QR scan |
| IMM QA Officer | "CAPA Overdue", "Audit exceptions" | Verify chain, Close CAPA, Review Incident |
| IMM Department Head | "Contract 90d", "BYT reg 90d" | Approve transfer, Sign-off decommission |
| IMM Operations Manager | "Asset utilization", "PM compliance" | Bulk assign KTV, CRUD assets |
| IMM System Admin | "System health" | Edit fixtures, Manage roles, Scheduler trigger |
| IMM Storekeeper | "Low stock alerts" | CRUD inventory, Stock movements |

Enforce bằng 2 lớp:
1. **FE:** `authStore.hasRole()` — ẩn menu / disable button.
2. **BE:** `has_permission` + `permission.py` — chặn data.

## VII.2. Confirmation Modal (destructive actions)

```
┌────────────────────────────────────────────────────────┐
│ Xác nhận ngừng sử dụng AC-ASSET-2026-00042             │
├────────────────────────────────────────────────────────┤
│ Thao tác này sẽ:                                       │
│   • Đổi lifecycle_status → Decommissioned              │
│   • Huỷ toàn bộ PM/Calibration schedule còn pending   │
│   • Ghi 1 Asset Lifecycle Event bất biến               │
│                                                        │
│ Nhập mã thiết bị để xác nhận: [___________________]   │
├────────────────────────────────────────────────────────┤
│                [ Huỷ ]     [ Xác nhận ngừng ] (red)   │
└────────────────────────────────────────────────────────┘
```

## VII.3. Offline Support

Form dài (AC Asset, CAPA, Incident Wizard) auto-save draft vào `localStorage` mỗi 10s.

Key naming: `draft:<doctype>:<user>:<name|new>`.

QR scan, PM log dùng IndexedDB offline queue + auto-sync khi online (ServiceWorker scope `/assets/assetcore/frontend/`).

## VII.4. Keyboard Shortcuts

| Phím | Hành động |
|---|---|
| `Ctrl+S / ⌘+S` | Lưu form hiện tại |
| `Ctrl+K / ⌘+K` | Mở global search |
| `Esc` | Đóng modal / drawer |
| `?` | Hiển thị cheat-sheet shortcut |
| `G` then `A` | Go to Assets |
| `G` then `D` | Go to Dashboard |

---

# Phần VIII — Tech Stack & Directory

## VIII.1. Core

| Công nghệ | Version | Ghi chú |
|---|---|---|
| Vue | 3.4+ (Composition API) | `<script setup lang="ts">` |
| TypeScript | 5.3+ strict | `"strict": true` |
| Frappe UI | latest | Button, Dialog, FormControl, ListView |
| Vite | 5+ | Dev server, build |
| PNPM | 8+ | Package manager |
| Pinia | 2.x | Global state |
| Vue Router | 4.x | File-based routing |
| VueUse | latest | `useLocalStorage`, `useEventListener` |
| vee-validate | 4 | Form validation |
| zod | 3.x | TS-first schema validation |
| vue-i18n | 9 | Locale vi + en |
| @zxing/browser | latest | QR scan |

## VIII.2. Directory Structure

```
frontend/
├─ src/
│  ├─ api/
│  │  ├─ client.ts          Axios + CSRF interceptor
│  │  ├─ imm00.ts           Foundation endpoints
│  │  └─ inventory.ts       Inventory endpoints
│  ├─ components/
│  │  ├─ shared/            Button, Chip, StatusBadge, Timeline, QRScanner
│  │  └─ forms/             ConfirmModal, FieldDisabledTooltip
│  ├─ composables/
│  │  ├─ useAuth.ts
│  │  ├─ usePagination.ts
│  │  └─ useOffline.ts
│  ├─ layouts/
│  │  ├─ AppShell.vue       Topbar + Sidebar + Breadcrumb
│  │  ├─ AuthLayout.vue
│  │  └─ PrintLayout.vue
│  ├─ locales/
│  │  ├─ vi.json
│  │  └─ en.json
│  ├─ pages/
│  │  ├─ index.vue                  Dashboard
│  │  ├─ assets/
│  │  ├─ suppliers/
│  │  ├─ locations/
│  │  ├─ departments/
│  │  ├─ master-data/
│  │  ├─ incidents/
│  │  ├─ capa/
│  │  ├─ audit-trail/
│  │  └─ inventory/
│  ├─ stores/
│  │  ├─ authStore.ts
│  │  ├─ uiStore.ts
│  │  └─ notifStore.ts
│  ├─ types/
│  │  └─ imm00.ts           AcAsset, AcSupplier, ImmCapa, etc.
│  ├─ utils/
│  │  ├─ formatDate.ts
│  │  ├─ qrScan.ts
│  │  └─ offlineQueue.ts
│  └─ main.ts
├─ index.html
├─ vite.config.ts
├─ tsconfig.json
└─ package.json
```

---

## VIII.3. AC-CR-80 — `ApproverSelect` đọc shape mới + dải "đang xem N/M" (spec cho [FE] Bước-4)

> Hợp đồng BE: [`05_API_Specification.md` §III.23](./05_API_Specification.md) · ADR: [`ADR-IMM00-TRUNCATION-SSOT.md` §7](./ADR-IMM00-TRUNCATION-SSOT.md).
> **Ràng buộc số 1 — 0 hồi quy call-site**: `props` + `v-model` của `ApproverSelect` **KHÔNG ĐỔI** ⇒ **51 file** đang dùng không phải sửa. Mọi thay đổi nằm **bên trong** component + tầng `api/user.ts`.

### VIII.3.1 `frontend/src/api/user.ts` — tolerant reader (ADR-IMM00-ASSIGN-04)

```ts
export interface AssignableUserItem {
  name: string; full_name: string | null; email: string | null; user_image?: string | null
}
/** Trang người-được-phép + meta cắt (AC-CR-80). `truncated` là 0|1 (int), KHÔNG boolean. */
export interface AssignableUserPage {
  items: AssignableUserItem[]; total: number; truncated: 0 | 1; limit: number
}

export const listAssignableUsers = async (
  context: string, search = '', limit = 20,
): Promise<AssignableUserPage> => {
  const res = await frappeGet<AssignableUserPage | AssignableUserItem[]>(
    `${BASE}.list_assignable_users`, { context, search, limit })
  // Cửa sổ gunicorn --preload CHƯA reload: BE cũ vẫn trả MẢNG TRẦN. Không chuẩn hoá
  // ở đây thì picker TRẮNG danh sách suốt cửa sổ đó (hồi quy nặng hơn lỗi đang sửa).
  return Array.isArray(res)
    ? { items: res, total: res.length, truncated: 0, limit }
    : res
}
```

- **KHÔNG** suy `truncated` từ `items.length >= limit` ở FE — client không biết trần **sau clamp** (D5).
- Giữ nguyên chữ ký 3 tham số + endpoint (test `userAssignableUsers.test.ts` đã ghim).

### VIII.3.2 `components/commissioning/ApproverSelect.vue`

| Thành phần | Thay đổi |
|---|---|
| `fetchUsers(q, limit)` | Trả `AssignableUserPage` cho **cả 2 nguồn**. Nhánh `role=` (`getUsersByRole`, IMM-04) chưa có meta ⇒ bọc `{items: rows, total: rows.length, truncated: 0, limit}` *(nhánh này vẫn cắt im lặng — backlog ADR §7.5)*. |
| state | `results` giữ `page.items`; thêm `total = ref(0)`, `truncated = ref<0\|1>(0)` |
| `doSearch` | gán cả 3; nhánh `catch` reset `truncated=0`, `total=0` (không hiện dải khi lỗi) |
| `loadInitialUser` | đọc `page.items` (đang đọc mảng trần — **PHẢI sửa**, nếu không chip người đã chọn hiện sai) |
| Dropdown | thêm **dải cảnh báo** ngay dưới danh sách kết quả khi `truncated === 1` |

**Dải cảnh báo (chuỗi CHỐT — test render bám theo):**

```
Đang hiển thị {{ results.length }}/{{ total }} người — gõ tên để tìm thêm
```

- Hiện **chỉ khi** `truncated === 1`; `truncated === 0` ⇒ **KHÔNG** render node nào (không để dải rỗng chiếm chỗ).
- Tiếng Việt đầy đủ (UI copy policy — không viết tắt EN).
- `role="status"` để trình đọc màn hình thông báo; style phụ trợ (nền vàng nhạt, chữ nhỏ) tuỳ FE, **nội dung chữ là bất biến**.

### VIII.3.3 Chống crash null (bắt buộc kèm)

`full_name` có thể `null` trên tài khoản cũ (hợp đồng khai `nullable`). Chỗ hiện dùng `user.full_name.charAt(0)` (avatar chữ cái đầu) và `{{ user.full_name }}` PHẢI fallback `full_name || name`. Đây là lỗi **tiềm ẩn sẵn**, AC-CR-80 chỉ làm nó tường minh.

### VIII.3.4 DoD FE

- `npx vue-tsc --noEmit` **0 lỗi**; `npx vitest run` xanh toàn bộ.
- `userAssignableUsers.test.ts`: bổ sung ca **shape mới** (object) + ca **shape cũ** (mảng — tolerant reader) + ghim `truncated` là số `0|1`, **không** boolean.
- **Test RENDER trên DOM** (không chỉ api-client): mount `ApproverSelect`, mock `listAssignableUsers` trả `{items: 20 người, total: 47, truncated: 1}` ⇒ DOM chứa chuỗi `Đang hiển thị 20/47 người`; mock `truncated: 0` ⇒ **không** chứa `Đang hiển thị`.
- `userSource.guard.test.ts` giữ xanh (không thêm đường lấy user mới).

## VIII.4. AC-CR-87 — «Bản ghi liên quan»: gọn hơn VÀ nói nhiều hơn (vòng 1 chỉ kiểu; UI ở vòng 2/3)

> Hợp đồng BE: [`05 §III.24`](./05_API_Specification.md) · ADR: [`ADR-IMM00-CONNECTIONS-TREE.md`](./ADR-IMM00-CONNECTIONS-TREE.md).
> **Vòng 1 (BE) — FE ĐƯỢC PHÉP CHẠM ĐÚNG 1 FILE**: `frontend/src/api/connections.ts`, **chỉ thêm field optional vào type**. `RelatedRecords.vue` và 5 màn Detail **KHÔNG đổi một dòng** (A11).

### VIII.4.1 Vòng 1 — chỉ mở rộng kiểu (không đổi hành vi)

```ts
// frontend/src/api/connections.ts — THÊM (không sửa/không xoá field cũ)
export interface ConnectionPreviewItem {
  name: string
  title: string
  status: string          // giá trị enum THÔ (dùng để so sánh/lọc)
  status_label: string     // nhãn tiếng Việt do BE dịch — dùng để HIỂN THỊ
  date: string             // 'YYYY-MM-DD' hoặc ''
}

export interface ConnectionItem {
  doctype: string
  label: string                    // LEGACY — sẽ gỡ ở vòng 3
  count: number                    // LEGACY — sẽ gỡ ở vòng 3
  capped: boolean                  // LEGACY — sẽ gỡ ở vòng 3
  filters: Record<string, unknown> // LEGACY — sẽ gỡ ở vòng 3
  label_vi?: string
  total?: number
  truncated?: 0 | 1                // KHÔNG boolean (CR-01)
  items?: ConnectionPreviewItem[]
  deep_link_filters?: Record<string, string>
  can_create?: boolean
  create_route_hint?: string
}
```

**Vì sao `optional`**: dự án chạy `gunicorn --preload` ⇒ giữa lúc sửa `api/*.py` và lúc USER reload, BE vẫn trả **shape cũ**. FE phải là *tolerant reader* (cùng lý lẽ ADR-IMM00-ASSIGN-04): `undefined` = *"không rõ"* ⇒ **giữ nguyên** cách hiển thị cũ, KHÔNG hiện dải cảnh báo, KHÔNG bịa số.

### VIII.4.2 Vòng 2 (AC-CR-88) — spec THỰC THI cho `RelatedRecords.vue` + helper

> Quyết định + lý lẽ đầy đủ: [`ADR-IMM00-CONNECTIONS-TREE.md` §10](./ADR-IMM00-CONNECTIONS-TREE.md) (**D-FE-1..11 · INV-CONNFE-1..11**). Mục này là **bản thực thi**: [FE] chép đúng chữ ký + đúng chuỗi hiển thị, không tự đặt thêm.
> **File được phép chạm (ĐÚNG 4)**: `frontend/src/api/connections.ts` · `frontend/src/components/common/RelatedRecords.vue` · `frontend/src/components/common/RelatedRecords.test.ts` (viết lại) · `frontend/src/api/connections.test.ts` (**chỉ APPEND** ca helper — 0 assert cũ bị sửa). **KHÔNG** chạm 5 màn Detail (vòng 3), **KHÔNG** chạm file BE nào.

#### (a) Helper hiển thị — thêm vào `frontend/src/api/connections.ts` (thuần, không import router/component)

```ts
/** Nhãn hiển thị của nhóm HOẶC ô: label_vi → label → doctype. KHÔNG bản đồ nhãn thứ hai ở FE. */
export function connectionLabel(x: { label?: string; label_vi?: string; doctype?: string }): string

/** Dòng preview đã chuẩn hoá. BE cũ (thiếu `items`) ⇒ [] ⇒ component vào chế độ LEGACY. */
export function previewRows(item: ConnectionItem): ConnectionPreviewRow[]

export interface ConnectionCounts {
  total: number      // item.total ?? item.count ?? 0
  capped: boolean    // item.capped === true
  shown: number      // previewRows(item).length
  truncated: boolean // item.truncated !== undefined ? item.truncated === 1 : (shown > 0 && total > shown)
  badge: string      // capped ? `${total}+` : String(total)     ⇒ chạm trần hiện '100+'
  band: string       // (shown > 0 && (truncated || capped)) ? `Đang xem ${shown}/${badge}` : ''
}
export function connectionCounts(item: ConnectionItem): ConnectionCounts

/**
 * Bộ lọc AN TOÀN cho query-string:
 *  - `deep_link_filters !== undefined` ⇒ dùng NGUYÊN nó, **kể cả `{}`** (CẤM fallback sang `filters`);
 *  - `undefined` (BE cũ) ⇒ chiếu `filters`, CHỈ giữ cặp có value scalar (string|number).
 */
export function deepLinkQuery(item: ConnectionItem): Record<string, string>

/** true ⟺ routeForDoctype(doctype) != null ∧ ≥1 khoá lọc ∧ counts.total > 0. */
export function canSeeAll(item: ConnectionItem): boolean
```

Cả 5 helper là **hàm thuần** ⇒ test được trong `connections.test.ts` mà không cần `mount` (nhanh, và tách được lỗi logic khỏi lỗi template).

#### (b) Hình dạng render (D-FE-1/4/5/6/8)

```
<div>                                   ← MỘT root duy nhất (giữ class fallthrough 'mt-4' của 5 view)
  [đang tải] | [lỗi + «Thử lại»] | [rỗng] | nhóm*
  nhóm  data-testid="conn-group"
    ├ tiêu đề nhóm         = connectionLabel(group)
    ├ ô có dữ liệu (total > 0)  data-testid="conn-cell" data-doctype="<doctype>"
    │   ├ nhãn ô           = connectionLabel(item)   + badge  data-testid="conn-badge" = counts.badge
    │   ├ ≤5 dòng preview  data-testid="conn-row" (bấm được) | "conn-row-static" (text tĩnh)
    │   │     title · chip status_label (bỏ chip khi '') · formatDate(date)
    │   ├ dải cắt          data-testid="conn-band"  = counts.band     (bỏ khi band === '')
    │   └ «Xem tất cả»     data-testid="conn-see-all" (chỉ khi canSeeAll(item))
    └ ô rỗng gộp 1 dòng    data-testid="conn-empty-summary" = «Chưa có: nhãn 1, nhãn 2, …»
</div>
```

- **KHÔNG** heading `"Bản ghi liên quan"`, **KHÔNG** `<section>` viền/`<header>`, **KHÔNG** dòng `"Tổng N"` — tiêu đề + badge là việc của **tab vòng 3**.
- `defineExpose({ reload, total })` — `total` = `payload.total` (tổng cộng dồn `count` mọi ô; **khác** `item.total`).
- Điều hướng: dòng ⇒ `router.push(detailRouteForDoctype(item.doctype, row.name))` (**chuỗi**); «Xem tất cả» ⇒ `router.push({ path: routeForDoctype(item.doctype)!, query: deepLinkQuery(item) })`.

#### (c) Bảng quyết định render (đọc thẳng khi code, không suy luận lại)

| Điều kiện dữ liệu | Kết quả DOM |
|---|---|
| `items === undefined` (BE chưa reload) | **LEGACY**: nhãn + badge; **0** dòng preview, **0** dải cắt (KHÔNG hiện `Đang xem 0/6`) |
| `total === 0` | Ô gộp vào dòng `conn-empty-summary`; **0** nút, **0** vùng preview, **vẫn có nhãn VI** |
| `detailRouteForDoctype(dt, name) === null` | Dòng là `conn-row-static` — KHÔNG `<button>`, KHÔNG `@click`, KHÔNG `role="button"` |
| `routeForDoctype(dt) === null` | **0** nút «Xem tất cả» (ô vẫn hiện preview bình thường) |
| `deep_link_filters === {}` ∧ `count > 0` | **0** nút «Xem tất cả» — *(đúng bug người dùng báo: bấm ra danh sách chung/trống)* |
| `filters` legacy `{name: ['in', [...]]}` ∧ thiếu `deep_link_filters` | Khoá bị **loại** ⇒ 0 khoá ⇒ **0** nút (đóng URL rác `?name=in,A,B`) |
| `truncated === 1 ∧ capped === false`, `shown=5`, `total=12` | Dải `Đang xem 5/12` |
| `capped === true` (`total = 100` nghĩa **≥100**) | Badge `100+`; dải `Đang xem 5/100+`; **CẤM** chuỗi `còn 95` / mọi phép `total - shown` |
| `status_label === ''` | Bỏ hẳn chip trạng thái (không placeholder) |
| `date === ''` | `formatDate('')` ⇒ `'—'` (chấp nhận); **cấm** `'undefined'`/`'null'` lọt DOM |
| `can_create === false ∨ create_route_hint === ''` | **0** `conn-create` trong ô đó (vòng 2 không render nút tạo ở bất kỳ ô nào — nút thuộc vòng 4) |

#### (d) Ba cái bẫy đã biết (đọc trước khi viết test)

1. **Root nhiều phần tử** ⇒ mất attribute fallthrough ⇒ `class="mt-4"` của 4 màn Detail rơi im lặng + Vue warn. Giữ **một** root.
2. **Nhãn thô lọt qua attribute**: `doctype` chỉ được đặt ở `data-doctype` (không hiển thị) ⇒ assert A1 chấm trên **`wrapper.text()`**, KHÔNG `wrapper.html()`.
3. **`formatDate` không zero-pad** (`toLocaleDateString('vi-VN')` ⇒ `20/7/2026`). Test dùng chính `formatDate(...)` hoặc regex `\d{1,2}\/\d{1,2}\/\d{4}`; hardcode `20/07/2026` là **test brittle**, không phải bug sản phẩm.

#### (e) Hệ quả tạm giữa vòng 2 và vòng 3 (QA đừng chấm là regression)

Bỏ card chrome ⇒ 5 màn Detail hiển thị khối này **không tiêu đề** cho tới khi vòng 3 gắn tab + badge từ `defineExpose({ total })`. Đây là hệ quả **đã ratify** của D-FE-1, không phải lỗi.

### VIII.4.3 DoD FE (vòng 1)

- `npx vue-tsc --noEmit` **0 lỗi**; `npx vitest run src/components/common/RelatedRecords.test.ts src/api` **xanh** — **không sửa assert nào** (field mới đều optional ⇒ không test nào phải đổi).
- `git diff --name-only` phía FE chỉ được chứa **duy nhất** `frontend/src/api/connections.ts`.

### VIII.4.4 DoD FE (vòng 2 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vitest run` **0 fail** — gồm `src/components/common/RelatedRecords.test.ts` (**viết lại**, phủ TC-CONNFE-01..16 @[`07 §XVIII.4`](./07_Testing_QA.md)) và ca helper TC-CONNFE-17 và `src/api/connections.test.ts` (**chỉ append**, 0 assert cũ bị sửa).
- `npx vue-tsc --noEmit` **0 lỗi**.
- ⛔ **KHÔNG** chạy `npm run build` — ghi thẳng `assetcore/public/frontend` + `emptyOutDir` = **deploy live** (LL-DEPLOY-09).
- Test **RENDER trên DOM** (không chỉ helper): payload phủ **toàn bộ 20 khoá** `DOCTYPE_ROUTE` ⇒ `wrapper.text()` chứa **0** chuỗi doctype tiếng Anh; ô `{total:12, truncated:1, items:5}` ⇒ chứa `Đang xem 5/12`; `truncated:0` ⇒ **không** chứa `Đang xem`; `capped:true` ⇒ chứa `100+` ∧ **không** chứa `còn `.
- Test **nút chết** (LL-FE-47): doctype ∉ `DOCTYPE_DETAIL_ROUTE` ⇒ dòng **không phải** phần tử bấm được ∧ click ⇒ `push` **không** được gọi; `deep_link_filters === {}` ∧ `count > 0` ⇒ **0** nút «Xem tất cả».
- Test **expose cho vòng 3**: `vm.total === payload.total` ∧ `typeof vm.reload === 'function'` ∧ `wrapper.findAll('section').length === 0` ∧ text **không** chứa `"Bản ghi liên quan"`.
- `git diff --name-only` phía FE **chỉ** chứa 4 file ở §VIII.4.2 (mọi file BE / 5 màn Detail phải sạch — A10).

### VIII.4.5 DoD FE (vòng 3/4 — để sẵn cho vòng sau)

- **Vòng 3**: gắn khối vào **tab** ở 5 màn Detail + **mount lười** ⇒ 0 request khi tab chưa mở. **Spec thực thi đã chốt tại §VIII.5 (cuối file này)**; ⚠️ mệnh đề "badge tab đọc `defineExpose({ total })`" của dòng này **đã bị supersede** bởi [ADR §11 D-TAB-4](./ADR-IMM00-CONNECTIONS-TREE.md) (badge = phải gọi API sớm = phá chính mục tiêu vòng 3) — vòng 3 tab **chỉ có nhãn chữ**, `defineExpose` giữ nguyên cho vòng 4.
- **Vòng 3 (cùng BE)**: gỡ `label`/`count`/`capped` khỏi type + component; bỏ nhánh LEGACY (D-FE-3) và nhánh fallback `filters` (D-FE-6).
- **Vòng 4**: nút «Tạo …» theo `can_create` + `create_route_hint` với **resolve-or-hide** (`router.resolve` — ADR §D8) + prefill; `create_route_hint` không phân giải được ⇒ **ẩn** nút. ⚠️ **Đính chính (BA Self-Correction 2026-07-28)**: mệnh đề *"prefill `deep_link_filters`"* của dòng này **SAI** — `deep_link_filters` khoá theo **Link fieldname** (`asset_ref`) để lọc **danh sách**, không phải khoá query của **màn tạo** (`asset`). Nguồn prefill đúng là khoá **MỚI** `create_prefill` do BE phát (ADR §12 D-CR4-4/§12.7). Spec thực thi: **§VIII.6** (cuối file này).

## VIII.5. AC-CR-89 (vòng 3/5) — TAB riêng + mount lười cho «Bản ghi liên quan»: `DetailTabBar.vue` + 5 màn Detail

> Quyết định + invariants: [`ADR-IMM00-CONNECTIONS-TREE.md` §11](./ADR-IMM00-CONNECTIONS-TREE.md) (**D-TAB-1..12 · INV-CONNTAB-1..12**) · test: [`07 §XVIII.5`](./07_Testing_QA.md) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) (FR-00-CONN-02 / BR-00-CONN-18..24).
> **Biên (A10)**: chỉ `DetailTabBar.vue` (MỚI) + 5 view + file `.test.ts` + `docs/imm-00/*`. **0 dòng** dưới `assetcore/`; **KHÔNG** chạm `RelatedRecords.vue` / `api/connections.ts` (đóng băng từ vòng 1+2); **KHÔNG** `npm run build`.

### VIII.5.1 `components/common/DetailTabBar.vue` (MỚI) — một hợp đồng tab cho mọi màn Detail

```vue
<script lang="ts">
export interface DetailTab { key: string; label: string }
/** SSoT nhãn VI cho 4 màn phiếu (PM · CM · Hiệu chuẩn · Sự cố). */
export const DETAIL_RELATED_TABS: readonly DetailTab[] = [
  { key: 'detail',  label: 'Chi tiết' },
  { key: 'related', label: 'Bản ghi liên quan' },
]
</script>

<script setup lang="ts">
defineProps<{ tabs: readonly DetailTab[]; modelValue: string }>()
const emit = defineEmits<{ (e: 'update:modelValue', key: string): void }>()
</script>

<template>
  <div role="tablist" data-testid="detail-tab-bar" class="flex gap-1 mb-4 border-b border-slate-200 overflow-x-auto">
    <button
      v-for="t in tabs" :key="t.key"
      type="button" role="tab"
      :aria-selected="t.key === modelValue"
      :data-testid="`tab-${t.key}`"
      class="shrink-0 whitespace-nowrap px-4 py-2 text-sm font-medium transition-colors"
      :class="t.key === modelValue ? 'text-blue-600 border-b-2 border-blue-600 -mb-px' : 'text-slate-500 hover:text-slate-800'"
      @click="emit('update:modelValue', t.key)"
    >{{ t.label }}</button>
  </div>
</template>
```

**Bắt buộc (INV-CONNTAB-11)**: `role="tablist"` · mỗi nút `role="tab"` + `type="button"` + `aria-selected` đúng (**đúng 1** nút `true`) · container `overflow-x-auto` · nút `shrink-0 whitespace-nowrap` (hợp đồng cuộn ngang mobile **TC-RWD-07** chuyển từ `AssetDetailView` sang đây).
**Cấm**: `aria-controls` trỏ panel `v-if` (id treo khi tab đóng) · badge số (D-TAB-4) · roving-tabindex/mũi tên (`[ROADMAP]`).

### VIII.5.2 Khuôn chung cho 4 màn phiếu (PM · CM · Hiệu chuẩn · Sự cố)

```ts
import DetailTabBar, { DETAIL_RELATED_TABS } from '@/components/common/DetailTabBar.vue'
const activeTab = ref<'detail' | 'related'>('detail')
```

```html
<DetailTabBar v-model="activeTab" :tabs="DETAIL_RELATED_TABS" />
<div v-show="activeTab === 'detail'" data-testid="tab-panel-detail" role="tabpanel">
  <!-- … TOÀN BỘ thân trang cũ, KHÔNG sửa nội dung … -->
</div>
<div v-if="activeTab === 'related'" data-testid="tab-panel-related" role="tabpanel">
  <RelatedRecords :doctype="…" :name="…" />
</div>
```

⚠️ **Hai thẻ mở panel PHẢI nằm gọn trên MỘT dòng, đúng thứ tự thuộc tính trên** — guard A1 quét mã nguồn theo khuôn này (D-TAB-9). Panel chính **`v-show`** (giữ dữ liệu đang nhập, không nạp lại) · panel liên quan **`v-if`** (0 request trước khi mở).
Bỏ luôn class `mt-4` / `md:col-span-2` đang truyền cho `RelatedRecords`: trong panel riêng nó không còn nằm trong grid hay cần bù khoảng cách. (`RelatedRecords.vue` **không** bị sửa — chỉ đổi class mà view truyền vào.)

### VIII.5.3 Biên tập từng màn (neo @source, verify 2026-07-28)

| Màn | File | Biên tập |
|---|---|---|
| **Bảo trì (PM)** | `views/pm/PMWorkOrderDetailView.vue` | Trong `<template v-else-if="wo">` (`:382`–`:639`): chèn `<DetailTabBar>` làm phần tử **đầu**; bọc phần còn lại vào panel chính; gỡ `<RelatedRecords class="mt-4" …>` @`:637` → đưa vào panel liên quan (`doctype="PM Work Order"` `:name="wo.name"`). Các con của template đều mang `mb-5` riêng ⇒ panel chính **không** cần class khoảng cách. |
| **Sửa chữa (CM)** | `views/cm/CMWorkOrderDetailView.vue` | Đổi `<div v-else-if="wo" class="grid grid-cols-1 md:grid-cols-5 gap-6">` @`:532` thành `<template v-else-if="wo">` (giữ **nguyên** chuỗi `v-if`/`v-else-if` với `loading` @`:512` và `DetailLoadError` @`:522`); bên trong: tab bar → panel chính bọc `<div class="grid grid-cols-1 md:grid-cols-5 gap-6">` cũ → panel liên quan. Xoá `<RelatedRecords v-if="wo" class="mt-4" …>` @`:1094` (**ngoài** chuỗi) — điều kiện `wo` nay do `v-else-if` của template gánh. |
| **Hiệu chuẩn** | `views/calibration/CalibrationDetailView.vue` | Trong `<template v-else>` (`:471`–`:702`, sau `loading` @`:457` / `loadFailed` @`:460`): tab bar đầu; panel chính `class="space-y-5"` (trang dùng `space-y-5` ở cấp cha) bọc thân; `<RelatedRecords>` @`:700` → panel liên quan (`doctype="IMM Asset Calibration"` `:name="props.id"`). |
| **Sự cố** | `views/incident/IncidentDetailView.vue` | Tab bar `v-if="!loading && form.status"` đặt ngay sau header; panel chính `class="space-y-5"` bọc **các khối thân trang `:492`–`:716`** (stepper · dải ảnh hưởng bệnh nhân · `err` · chuỗi `loading`/`loadBlocked`/thẻ chi tiết — **giữ nguyên chuỗi `v-if`/`v-else-if` bên trong**); `<RelatedRecords v-if="!loading && form.status" …>` @`:498` → panel liên quan (`doctype="Incident Report"` `:name="name"`). Các **modal** (`:719`+) nằm **NGOÀI** hai panel. |
| **Tài sản** | `views/asset/AssetDetailView.vue` | Thay tab bar inline `:637`–`:647` bằng `<DetailTabBar v-model="activeTab" :tabs="ASSET_TABS" />`; `ASSET_TABS` = 6 mục **giữ nguyên 5 nhãn cũ** + `{ key:'related', label:'Bản ghi liên quan' }`; mở rộng union `activeTab` (`:53`) thêm `'related'`; bọc 5 khối nội dung tab (`:649`–`:912`) trong panel chính `v-show="activeTab !== 'related'"` (**giữ nguyên `v-if` từng tab bên trong**); gỡ `<RelatedRecords class="md:col-span-2" …>` @`:654` khỏi tab `info` → panel liên quan (`doctype="AC Asset"` `:name="store.currentAsset.name"`). `onTabChange` (`:397`) **không** thêm side-effect cho `related` (mount lười tự lo). Modal in nhãn PDF (`:915`+) nằm ngoài panel. |

**Cấm phát sinh**: đổi nội dung/thứ tự các khối thân trang; thêm/bớt CTA; đổi điều kiện `v-if` sẵn có bên trong panel; đổi cặp `doctype`/`name` (D-TAB-6).

### VIII.5.4 DoD FE (vòng 3 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vue-tsc --noEmit` **0 lỗi** ∧ `npx vitest run` **0 fail** trên **toàn bộ** suite (≥268 file trước vòng, ≥273 sau vòng).
- Guard **vị trí** (A1): loop trên mảng **5 đường dẫn** — `<RelatedRecords` đúng **1** lần/file ∧ sau `data-testid="tab-panel-related"` ∧ thẻ mở panel liên quan có `v-if` không `v-show` ∧ thẻ mở panel chính có `v-show`.
- Guard **mount lười đo được** (A2): spy `getConnections` — mount ⇒ **0** gọi ∧ 0 `[data-testid="related-records"]`; click `[data-testid="tab-related"]` ⇒ **1** gọi ∧ **1** `related-records`.
- Guard **ẩn thân trang** (A3) + **không mất dữ liệu** (A4: gõ `#tech-notes` ở màn PM → đổi tab → quay lại ⇒ giá trị còn nguyên; `fetchWorkOrder`/`getIncident` **không** gọi lần 2).
- Guard **prop thật** (A5, đọc từ stub) + **nhãn VI** (A6, 5 màn) + **a11y/RWD** (A8) + **403 gate** (A7: `detailReadForbiddenGate.test.ts` xanh, **0 assert bị sửa**).
- `assetDetailTabBarResponsive.test.ts` cập nhật (6 tab; class cuộn ngang chấm trên `DetailTabBar.vue`) và **vẫn xanh** — breakage đã khai báo trước (ADR §11.5).
- `git diff --name-only`: **0** đường dẫn dưới `assetcore/`; **không** có `RelatedRecords.vue` / `api/connections.ts`.

## VIII.6. AC-CR-90 (vòng 4/5) — nút «Tạo …» sống đúng lúc + đẩy **ngữ cảnh cha** sang màn tạo

> Hợp đồng BE: [`05 §III.24.7`](./05_API_Specification.md) · quyết định: [ADR §12](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR4-4/5/9 · INV-CONN4-1/7/8) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) BR-00-CONN-30..32/34 · test: [`07 §XVIII.6`](./07_Testing_QA.md).
> **Biên FE (A-biên)**: `frontend/src/api/connections.ts` · `frontend/src/components/common/RelatedRecords.vue` · file `.test.ts`. **KHÔNG** chạm 5 màn Detail, `DetailTabBar.vue`, `router/index.ts`, hay bất kỳ file nào dưới `assetcore/`. **KHÔNG** `npm run build` (= deploy live, LL-DEPLOY-09).

### VIII.6.1 `api/connections.ts` — thêm **một** khoá kiểu + **một** helper thuần

```ts
export interface ConnectionItem {
  // … 12 khoá cũ, KHÔNG đổi …
  /**
   * Ngữ cảnh cha để màn tạo điền sẵn: `{query_key: giá trị}` — khoá là khoá query mà
   * CHÍNH màn tạo đó đọc (`asset` / `incident` / `pm_wo`), KHÔNG phải Link fieldname.
   *
   * Bất biến hai chiều với `can_create`: `can_create === false ⇒ {}`.
   * ⚠️ `{}` là CÂU TRẢ LỜI ("không có gì để điền sẵn"), KHÔNG phải thiếu dữ liệu ⇒
   * **CẤM** fallback sang `deep_link_filters` (khoá của nó dùng để lọc DANH SÁCH).
   */
  create_prefill?: Record<string, string>
}

/**
 * Query prefill cho nút tạo — `{}` khi không có gì để điền sẵn.
 *
 * Tolerant reader: BE chưa reload (`undefined`) ⇒ `{}` ⇒ điều hướng chỉ `path`
 * (đúng hành vi vòng 3, KHÔNG bịa khoá). Chỉ giữ value là chuỗi không rỗng —
 * một khoá có value rỗng đẩy vào URL thành `?asset=` là query rác.
 */
export function createPrefill(item: ConnectionItem): Record<string, string> {
  const src = item.create_prefill
  if (!src) return {}
  const out: Record<string, string> = {}
  for (const [k, v] of Object.entries(src)) {
    if (typeof v === 'string' && v !== '') out[k] = v
  }
  return out
}
```

`createPath(item)` (đã có từ vòng 2) **giữ nguyên** — nó là nơi cài luật `resolve-or-hide`.

### VIII.6.2 `RelatedRecords.vue` — điều hướng bằng `{ path, query }`

```ts
function openCreate(item: ConnectionItem): void {
  const path = createPath(item)          // đã gồm: can_create ∧ hint ≠ '' ∧ router.resolve OK
  if (!path) return
  const query = createPrefill(item)
  router.push(Object.keys(query).length ? { path, query } : { path })
}
```

- **Đối số là hợp đồng test** (INV-CONNFE4-2): test khẳng định `router.push` nhận **object** `{ path, query }` với đúng cặp khoá/giá trị — **không** chấp nhận chỉ `path`, **không** chấp nhận chuỗi đã ghép query bằng tay (ghép tay = tự lo escape = tự đẻ lỗi URL).
- Prefill rỗng ⇒ đẩy **chỉ `path`** (giữ nguyên hành vi cũ, không sinh `?` cụt).

### VIII.6.3 Nút tạo — hình thức & ngôn ngữ

```vue
<button
  v-if="createPath(item)"
  type="button"
  :data-testid="`related-create-${item.doctype}`"
  @click="openCreate(item)"
>Tạo {{ viLabel(item).toLowerCase() }}</button>
```

- Nhãn **luôn** derive từ `viLabel(item)` (`label_vi` → `label` → `doctype`) ⇒ «Tạo phiếu bảo trì định kỳ». **CẤM** chuỗi tiếng Anh, **CẤM** token capability, **CẤM** mã trạng thái tiếng Anh trong nhãn/tooltip/thông báo (LL-FE-53 · BR-00-CONN-34).
- `v-if` (**không** `:disabled`): nút không dùng được thì **không tồn tại** — nút xám vẫn là nút chết (LL-FE-47).
- Nút nằm trong ô, **không** nhân bản ra tiêu đề nhóm; ô `total === 0` vẫn **được** có nút tạo (đó chính là lúc cần tạo nhất) — nhưng ô rỗng vẫn giữ khuôn gộp một dòng của D-FE-8.
- **Không** thêm chrome mới (viền/card/tiêu đề) — hợp đồng D-FE-1/§11 giữ nguyên.

### VIII.6.4 Invariants FE vòng 4 (INV-CONNFE4-*) — chấm bằng `vitest`

| ID | Phát biểu |
|---|---|
| INV-CONNFE4-1 | `can_create === false` **hoặc** `create_route_hint === ''` **hoặc** route không phân giải được ⇒ **0** nút tạo trong DOM |
| INV-CONNFE4-2 | Click nút tạo ⇒ `router.push` được gọi với **`{ path, query }`**; `query` **bằng đúng** `create_prefill` của ô; prefill rỗng ⇒ đối số là `{ path }` |
| INV-CONNFE4-3 | `create_prefill === undefined` (BE chưa reload) ⇒ vẫn điều hướng được (chỉ `path`), **0** khoá bịa, **0** cảnh báo |
| INV-CONNFE4-4 | Nhãn nút = `viLabel(item)` ⇒ `wrapper.text()` **không** chứa tên DocType tiếng Anh nào, **không** chứa chuỗi khớp `/\b[a-z]+\.(create\|read\|write)\b/` (token capability) |
| INV-CONNFE4-5 | Ô `total === 0` mà `can_create === true` ⇒ **vẫn có** nút tạo (không bị khuôn "ô rỗng gộp một dòng" nuốt mất) |

### VIII.6.5 DoD FE (vòng 4 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vitest run` **0 fail**; `npx vue-tsc --noEmit` **0 lỗi**.
- Test **render + đối số push** (không chỉ helper): phủ INV-CONNFE4-1..5.
- `git diff --name-only` phía FE **chỉ** chứa `api/connections.ts` · `components/common/RelatedRecords.vue` · file test.
- ⛔ **KHÔNG** `npm run build`.

---

## VIII.7. AC-CR-91 (vòng 5/5) — «Xem tất cả» phải mở ra danh sách **ĐÃ LỌC** (ADR §13)

> **Bằng chứng audit (2026-07-28):** trên tab của **1 AC Asset** có **16 ô bấm được**; chỉ **3** mở ra danh sách đã lọc (`/calibration?asset=` · `/asset-transfers?asset=` · `/compliance/findings?asset=`). **13 ô** mở ra danh sách **không lọc** vì (a) BE gửi khoá **fieldname** (`asset_ref` / `final_asset` / `critical_asset`) trong khi màn đích đọc `route.query.asset` — 4 ô; hoặc (b) màn đích **chưa đọc khoá lọc nào** — 9 ô. Bảng đầy đủ + lý do gốc: **ADR-IMM00-CONNECTIONS-TREE §13.1**.
>
> **Sau vòng, đo trên CHÍNH tab đó** (persona đủ capability đọc — QTV/super admin): ô có nút «Xem tất cả» mở ra danh sách **đã lọc** ≥ **8** (dự kiến **9**) · nút mở ra danh sách **không lọc** hoặc 404/route chết = **0**. Ô mà màn đích chưa lọc được ⇒ **TUYỆT ĐỐI không dựng nút**, chỉ còn preview 5 dòng.

### VIII.7.1 `api/connections.ts` — 2 bảng SSoT + 1 helper thuần (+1 sửa lỗi cài đặt)

**(1) `DOCTYPE_LIST_TARGET` — 9 entry.** `queryKey` = khoá mà **chính file view của route đó đọc** (`route.query.<queryKey>`), **KHÔNG** phải fieldname DocType.

```ts
export const DOCTYPE_LIST_TARGET: Record<string, { path: string; queryKey: string }> = {
  'PM Work Order':          { path: '/pm/work-orders',       queryKey: 'asset' },
  'Asset Repair':           { path: '/cm/work-orders',       queryKey: 'asset' },
  'IMM Asset Calibration':  { path: '/calibration',          queryKey: 'asset' },
  'Incident Report':        { path: '/incidents/list',       queryKey: 'asset' },  // wire ở VIII.7.3
  'IMM RCA Record':         { path: '/rca',                  queryKey: 'asset' },  // wire ở VIII.7.3
  'IMM Compliance Finding': { path: '/compliance/findings',  queryKey: 'asset' },
  'Asset Document':         { path: '/documents',            queryKey: 'asset' },
  'Document Request':       { path: '/documents/requests',   queryKey: 'asset' },
  'Asset Transfer':         { path: '/asset-transfers',      queryKey: 'asset' },
}
```

**(2) `LIST_TARGET_NO_FILTER` — 11 doctype**, allowlist **chỉ-giảm** (có màn danh sách nhưng màn đó **chưa lọc được** theo bản ghi cha):

```ts
export const LIST_TARGET_NO_FILTER: readonly string[] = [
  'AC Asset', 'PM Schedule', 'Firmware Change Request', 'Asset Decommission',
  'IMM Critical Spare Watchlist', 'AC Supplier', 'IMM Device Model',
  'IMM Calibration Schedule', 'IMM CAPA Record', 'Asset Commissioning', 'AC Spare Part',
]
```

9 + 11 = **20** = `|DOCTYPE_ROUTE|` ⇒ **0 doctype vùng xám** (khoá bằng INV-CONNFE5-4). Lý do từng dòng: ADR §D-CR5-6.

**(3) `listTarget(item)` — hàm THUẦN** (không router, không capability, không Vue):

```
listTarget(item) -> { path, query } | null
  1. entry = DOCTYPE_LIST_TARGET[item.doctype];   !entry  ⇒ null
  2. src   = item.deep_link_filters !== undefined
             ? item.deep_link_filters              // D-FE-6 quy tắc 1 — KHÔNG fallback, kể cả {}
             : <chiếu scalar từ item.filters>      // backend CŨ (khoá VẮNG MẶT)
  3. keys  = Object.keys(src).filter(k => k !== 'name')   // 'name' = internal_links ⇒ loại
  4. keys.length !== 1                             ⇒ null
  5. value = String(src[keys[0]] ?? '').trim();    !value ⇒ null
  6. return { path: entry.path, query: { [entry.queryKey]: value } }   // DỊCH khoá, GIỮ value
```

- Bước 6 là toàn bộ nội dung của chữ "dịch": **value đi nguyên** (mã bản ghi cha — BE bảo đảm bằng INV-CONN-17), **khoá đổi**.
- **`null` là câu trả lời hợp lệ và hay gặp**, không phải lỗi ⇒ ô chỉ còn preview.
- **Liên kết nội bộ nhiều bản ghi** (`{name: 'a,b,c'}`) ⇒ `null` **luôn**: không màn danh sách nào đọc `route.query.name` dạng tập phân tách bằng dấu phẩy; dựng nút = dẫn ra danh sách toàn hệ thống.

**(4) Sửa `linkFilters` cho khớp D-FE-6 quy tắc 1 (Self-Correction, ADR §13.2):**

```ts
// TRƯỚC (SAI): if (deep && Object.keys(deep).length > 0) return { ...deep }   // {} rơi xuống fallback
// SAU  (ĐÚNG): if (deep !== undefined) return Object.keys(deep).length ? { ...deep } : null
```

Kèm sửa test đang ossify hành vi sai trong `api/connections.test.ts`: `'deep_link_filters rỗng ⇒ fallback filters (backend cũ)'` → `'deep_link_filters rỗng ⇒ null (BE đã nói: không có khoá an toàn)'`. Tolerant reader **không** bị phá — backend *thật sự cũ* gửi khoá **vắng mặt** (`undefined`), nhánh đó giữ nguyên.

### VIII.7.2 `components/common/RelatedRecords.vue` — ba lớp gác, giống khuôn nút «Tạo …»

```ts
function seeAllFor(item: ConnectionItem): { path: string; query: Record<string,string> } | null {
  const target = listTarget(item)                              // 1. hợp đồng dữ liệu (thuần)
  if (!target) return null
  if (!routeExists(target.path)) return null                   // 2. route CÓ THẬT (router.resolve)
  if (!canAccessDrill(target.path, can)) return null           // 3. capability route đích
  return target
}
```

- `canAccessDrill` import từ `@/router/routeAccess` (đã tồn tại) — **KHÔNG** đẻ bảng gác thứ hai. Thiếu lớp 3 ⇒ người dùng bấm rồi bị route-guard đá ra `/unauthorized`, **cũng là nút chết** (LL-FE-47 · §9.4.9 drill dead-gate).
- `canSeeAll(item)` ⇒ `seeAllFor(item) !== null`; `openAll(item)` ⇒ `router.push(seeAllFor(item))` (object `{path, query}`), **không** push khi `null`.
- **`v-if`, KHÔNG `:disabled`** — nút xám vẫn là nút chết.
- `data-testid="conn-see-all"` **giữ nguyên** (hợp đồng test hiện hành). Nhãn nút giữ nguyên **«Xem tất cả»**; `aria-label` giữ khuôn `Xem tất cả ${viLabel(item)} của hồ sơ này` (tiếng Việt, 0 tên DocType tiếng Anh).
- Ô mất nút **không** được mất dữ liệu: preview 5 dòng + badge + dải truncation **giữ nguyên**.
- ⚠️ **Số ô có nút phụ thuộc persona** (lớp 3). Chỉ tiêu ≥ 8 chấm với persona đủ capability đọc — persona hẹp thấy ít hơn là hành vi ĐÚNG.

### VIII.7.3 Wire lọc-theo-thiết-bị — **lọc THẬT**, đủ **bốn** vế (ADR §D-CR5-7)

Đọc `route.query.asset` mà không gọi API kèm `asset` ⇒ guard tĩnh xanh, người dùng vẫn thấy danh sách đầy đủ. Mỗi view PHẢI đủ cả bốn:

| # | Vế | Thiếu thì hỏng thế nào |
|---|---|---|
| 1 | **Khởi tạo** state lọc từ `route.query.asset` **trước** lần nạp đầu | nạp-rồi-lọc-lại: 2 lần gọi mạng + 1 nhịp nháy dữ liệu sai |
| 2 | **Truyền xuống API** (`asset` vào params của store) | lọc chỉ nằm trong DOM, dữ liệu vẫn toàn hệ thống |
| 3 | **Chip «Thiết bị: `<mã>`» + nút bỏ lọc** trong `ListFilterBar` | danh sách lọc câm trông như "hệ thống mất dữ liệu", và không thoát ra được |
| 4 | **`watch(() => route.query.asset)`** → cập nhật + nạp lại | bấm «Xem tất cả» từ thiết bị B khi đang lọc thiết bị A ⇒ **không đổi gì** (im lặng, khó chẩn đoán nhất) |

**Đường dữ liệu đã SẴN SÀNG — vòng này KHÔNG mở rộng store/API:**

| Màn | Store | API client | Endpoint BE (@source verify 2026-07-28) |
|---|---|---|---|
| `/incidents/list` | `stores/imm12.ts::fetchList({ asset })` | `api/imm12.ts::listIncidents({ asset })` | `api/imm12.py::list_incidents(asset: str = "")` |
| `/rca` | `stores/imm12.ts::fetchRcas({ asset })` | `api/imm12.ts::listRcas({ asset })` | `api/imm12.py::list_rcas(asset: str = "")` → `services/imm12.py::list_rcas` (`f["asset"] = asset`) |

**`views/incident/IncidentListView.vue`** — đã có khung `applyQueryToFilters()` (`:33`) + `watch(() => route.query, …)` (`:182`) ⇒ **bồi thêm** khoá `asset` vào đúng bốn chỗ đó, **không** viết cơ chế mới:
- thêm `const assetFilter = ref('')`; trong `applyQueryToFilters()` đọc `route.query.asset` → gán + `touched = true`;
- `applyFilter()` / `goToPage()` truyền `asset: assetFilter.value || undefined`;
- `interface Chip` mở rộng `key: … | 'asset'`; `activeChips` thêm `{ key: 'asset', label: \`Thiết bị: ${assetFilter.value}\` }` (mẫu nhãn **dùng lại nguyên văn** `FindingListView.vue:58`); `clearChip('asset')` + `resetFilters()` xoá `assetFilter`.

**`views/incident/RCAListView.vue`** — **chưa** đọc query nào ⇒ dựng khung tối thiểu theo **đúng khuôn** `IncidentListView` (`useRoute` + `applyQueryToFilters` + `watch` + chip), **không** phát minh khuôn thứ hai. `store.fetchRcas` đã nhận `asset`.

**Ranh giới khoá:** `asset` **độc lập** (AND) với `status`/`severity`/`open` (Incident) và `method`/`status` (RCA) — **không** loại trừ nhau như cặp `status` ⟂ `open`. Đặt lọc thiết bị **không** được xoá lọc trạng thái đang có và ngược lại.

### VIII.7.4 Invariants FE vòng 5 (INV-CONNFE5-1..11)

Bảng đầy đủ ở **ADR §13.3**. Tóm tắt loại test: **tĩnh** 1–4 (guard `router/connectionsListParity.test.ts`) · **thuần** 5–6 (`api/connections.test.ts`) · **render** 7–11 (`RelatedRecords.test.ts` + test 2 màn wire).

### VIII.7.5 DoD FE (vòng 5 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vitest run` **0 fail** (baseline trước vòng: **278 file / 2591 test**, toàn xanh — đo 2026-07-28); `npx vue-tsc --noEmit` **0 lỗi**.
- Guard mới `src/router/connectionsListParity.test.ts` tồn tại và phủ INV-CONNFE5-1..4.
- Đo lại trên tab của 1 AC Asset: ô có «Xem tất cả» **đã lọc** ≥ 8 · nút mở ra danh sách **không lọc** = 0 · route chết/404 = 0.
- UI **tiếng Việt đầy đủ**: 0 chuỗi `asset_ref` / `final_asset` / `critical_asset` / tên DocType tiếng Anh trong DOM (LL-FE-53).
- `git diff --name-only` phía FE **chỉ** chứa: `api/connections.ts` · `api/connections.test.ts` · `components/common/RelatedRecords.vue` · `components/common/RelatedRecords.test.ts` · `views/incident/IncidentListView.vue` · `views/incident/RCAListView.vue` · `router/connectionsListParity.test.ts` · (test render 2 màn wire).
- **Sạch tuyệt đối:** `router/index.ts` · `router/routeAccess.ts` · `stores/imm12.ts` · `api/imm12.ts` · mọi `*_dashboard.py` · `services/connections.py`.
- ⛔ **KHÔNG** `npm run build` (= deploy live) · **KHÔNG** `git commit` · **KHÔNG** `bench migrate`.

---

## VIII.8. AC-CR-93 — «Bản ghi liên quan»: **chỉ render ô có dữ liệu**, ô rỗng gộp **một dòng/nhóm** (ADR §14)

> Quyết định + lý lẽ + danh mục supersede: [`ADR-IMM00-CONNECTIONS-TREE.md` §14](./ADR-IMM00-CONNECTIONS-TREE.md) (**D-CR93-1..7 · INV-CONNFE6-1..9**) · test: [`07 §XVIII.8`](./07_Testing_QA.md) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) (FR-00-CONN-04 / BR-00-CONN-35..41).
> **Biên (A-biên)** — chạm ĐÚNG 4 file: `frontend/src/api/connections.ts` (**chỉ APPEND** 4 helper thuần) · `frontend/src/components/common/RelatedRecords.vue` · `frontend/src/api/connections.test.ts` (**append**) · `frontend/src/components/common/RelatedRecords.test.ts` (**append + đúng 1 TC sửa**, xem §VIII.8.5).
> **Sạch tuyệt đối**: mọi file `.py` · `DOCTYPE_ROUTE` / `DOCTYPE_DETAIL_ROUTE` / `DOCTYPE_LIST_TARGET` (`:287`) / `LIST_TARGET_NO_FILTER` (`:321`) / `CREATE_PREFILL_QUERY_KEYS` · `router/*` · 5 màn Detail · `DetailTabBar.vue`. **KHÔNG** `npm run build` (= deploy live, LL-DEPLOY-09).
> **Hiện trạng phải sửa (verify @source 2026-07-28)**: `RelatedRecords.vue:177` `v-for="item in group.items"` render **mọi** ô; `hasRecords` (`:70`-`:72`) chỉ gác thân ô (`:205`) ⇒ tab của 1 `AC Asset` dựng **19** khối cho **3** ô có dữ liệu; chuỗi `conn-empty-summary` **chưa tồn tại** trong `frontend/src`.

### VIII.8.1 `api/connections.ts` — **chỉ APPEND** 4 helper thuần (0 khoá kiểu mới, 0 bảng mới)

```ts
/**
 * Ô này có dữ liệu chưa? — SSoT DUY NHẤT của câu hỏi đó (component KHÔNG giữ bản sao).
 *
 * Đọc số đếm hiệu lực `total ?? count ?? 0` (cùng công thức `itemTotal` `:144`), TUYỆT ĐỐI
 * KHÔNG đọc `items.length`: ô LEGACY (backend chưa reload) không có `items` mà vẫn có `count`
 * ⇒ dùng `items.length` sẽ gộp oan ô CÓ dữ liệu (tái sinh "cắt câm" mà CR-69 xoá).
 */
export function hasConnectionRecords(item: ConnectionItem): boolean

/** Các ô CÓ dữ liệu của nhóm, GIỮ thứ tự payload (không sort). */
export function dataCells(group: ConnectionGroup): ConnectionItem[]

/**
 * Nhãn tiếng Việt của các ô RỖNG, đã loại chuỗi rỗng.
 * `viLabel` (`:139`) KHÔNG fallback `doctype` — cố ý (ADR §14.7 hàng 5): in tên DocType
 * tiếng Anh vi phạm LL-FE-53. Ô rỗng không có nhãn ⇒ im lặng, KHÔNG in mã kỹ thuật.
 */
export function emptyLabels(group: ConnectionGroup): string[]

/** `''` khi không có ô rỗng nào có nhãn; ngược lại `Chưa có: {nhãn 1}, {nhãn 2}, …`. */
export function emptySummary(group: ConnectionGroup): string
```

- Ngăn cách **đúng** `', '`; tiền tố **đúng** `'Chưa có: '` — **một** mẫu câu cho mọi ca (2 mẫu = 2 đường sinh lỗi, cùng lý lẽ D-FE-7).
- 4 hàm là **hàm thuần** ⇒ ca biên (`items` rỗng · thiếu `total` · nhãn rỗng · nhóm 0 ô) test được ở `connections.test.ts` **không cần `mount`**.

### VIII.8.2 `RelatedRecords.vue` — xoá vị-từ cục bộ, đổi **tập ô** được render

```ts
// XOÁ hẳn hàm cục bộ `hasRecords` (:70-:72) — vị-từ chuyển về SSoT `api/connections.ts`.
// Component KHÔNG import `hasConnectionRecords` (nó chỉ dùng gián tiếp qua 2 hàm dưới —
// import thừa = `vue-tsc`/lint đỏ, và là dấu hiệu component còn hỏi lại câu đã hỏi).
import {
  /* … import cũ … */ dataCells, emptySummary,
} from '@/api/connections'
// `computed` BỔ SUNG vào import 'vue' SẴN CÓ (`:21` `import { ref, onMounted, watch } from 'vue'`)
// — KHÔNG thêm câu `import … from 'vue'` thứ hai (lint `no-duplicate-imports`).

/** Có ít nhất một ô mang dữ liệu trên TOÀN payload? — điều kiện câu rỗng (D-CR93-6). */
const hasAnyData = computed(() => groups.value.some(g => dataCells(g).length > 0))
```

**Hai nhánh trở thành hằng-đúng sau khi lọc ⇒ GỠ, không để nhánh chết** (cùng họ với luật "0 nút chết"):

| Vị trí hiện tại | Sau vòng này |
|---|---|
| `:190` ternary class của `conn-count` (`hasRecords(item) ? 'bg-sky-…' : 'bg-slate-…'`) | dùng **thẳng** nhánh có-dữ-liệu (`bg-sky-100 …`) — mọi ô được render đều có dữ liệu ⇒ nhánh xám không còn đường tới |
| `:205` `<template v-if="hasRecords(item)">` bọc preview + 2 nút | **bỏ `v-if`**, giữ **nguyên** nội dung bên trong (đúng D-CR93-7: nội dung ô không đổi) |

⇒ Sau vòng, `hasConnectionRecords` được gọi **chỉ** từ `dataCells`/`emptyLabels` trong `api/connections.ts` (một chỗ quyết định, đúng một lần) — component không còn hỏi lại câu đã hỏi.

### VIII.8.3 Hình dạng render (SSoT — chép nguyên, không tự đặt thêm)

```
<div data-testid="related-records">                       ← MỘT root duy nhất (D-FE-1, KHÔNG đổi)
  [đang tải]  «Đang tải bản ghi liên quan…»
  | [lỗi]     thông điệp + nút «Thử lại»
  | ─ v-if !hasAnyData → <p> «Chưa có bản ghi nào liên quan tới hồ sơ này.»   ← chuỗi CŨ, giữ nguyên
    ─ nhóm*  v-if="dataCells(group).length || emptySummary(group)"   data-testid="conn-group"
        ├ tiêu đề nhóm  v-if="dataCells(group).length"  data-testid="conn-group-label" = viLabel(group)
        ├ <ul> ô CÓ dữ liệu*  v-for="item in dataCells(group)"  data-testid="conn-item"
        │     └ NỘI DUNG Ô GIỮ NGUYÊN 100%: nhãn · conn-count · conn-meta · conn-row* · conn-see-all · conn-create
        └ dòng gộp  v-if="emptySummary(group)"  data-testid="conn-empty-summary"
              = «Chưa có: {nhãn 1}, {nhãn 2}, …»   ← TEXT TĨNH: 0 button, 0 <a>, 0 @click, 0 data-doctype
</div>
```

- Thẻ dòng gộp: `<p class="mt-2 text-xs text-slate-500 dark:text-slate-400">` (đồng bộ thang chữ phụ của khối; **không** viền/nền/chip — không thêm chrome, D-FE-1).
- **`defineExpose({ reload, total })` KHÔNG đổi**: `total` vẫn là `payload.total` (bẫy đặt tên D4) ⇒ payload mọi ô rỗng thì `total === 0` **tự nhiên**.
- ⛔ **CẤM** thêm `data-doctype` vào bất kỳ phần tử nào (3 TC đang xanh assert `wrapper.html()` sạch tên DocType: `RelatedRecords.test.ts:130` · `:162` · `:544`).
- ⛔ **CẤM** đổi tên `conn-item` / `conn-count` / `conn-meta` / `conn-row` / `conn-see-all` / `conn-create` (23 TC neo vào chúng — ADR D-CR93-1).

### VIII.8.4 Bảng quyết định render (đọc thẳng khi code, không suy luận lại)

| Điều kiện dữ liệu | Kết quả DOM |
|---|---|
| `total ?? count ?? 0 > 0` | **1** `conn-item` — nội dung y như vòng 2/4/5 |
| `total === 0` (hoặc thiếu `total` ∧ `count === 0`) | **0** `conn-item`; nhãn VI đi vào `conn-empty-summary` của **chính nhóm** đó |
| `total === undefined ∧ count > 0` (ô LEGACY) | **1** `conn-item` (chế độ LEGACY D-FE-3: nhãn + badge, 0 preview, 0 dải cắt) |
| `total === 0` ∧ `can_create === true` | **0** nút tạo (không còn ô để treo nút — supersede INV-CONNFE4-5, ADR §14.7 hàng 2) |
| Nhóm có ≥1 ô có dữ liệu | `conn-group-label` render (nhãn nhóm VI) |
| Nhóm **mọi** ô rỗng | **0** `conn-group-label`, **0** `conn-item`, **1** `conn-empty-summary` |
| Nhóm `items: []` | **0** `conn-group` (không dựng khung trống) |
| Ô rỗng mà `viLabel(item) === ''` (BE shape rác) | bỏ khỏi câu gộp; **KHÔNG** in `doctype`; nếu mọi nhãn rỗng ⇒ **0** dòng gộp |
| Payload **mọi** ô rỗng (`groups` không rỗng) | **0** `conn-item` + câu «Chưa có bản ghi nào liên quan tới hồ sơ này.» + các dòng gộp + `vm.total === 0` |
| `groups: []` | chỉ câu VI (**0** dòng gộp) — hành vi vòng 2, giữ nguyên |
| `loading === true` | chỉ «Đang tải bản ghi liên quan…» — **0** dòng gộp (chưa biết gì thì không được nói "chưa có") |
| `errorMessage !== ''` | thông điệp + «Thử lại» — **0** dòng gộp |

### VIII.8.5 Breakage đã khai báo TRƯỚC — **đúng 1** TC (QA KHÔNG chấm là nới guard)

**TC-FE-CONN-10** @`frontend/src/components/common/RelatedRecords.test.ts:283`:

- **Đổi**: phạm vi chấm "ô `count 0` render gọn" từ `conn-item` (`:300`) → `[data-testid="conn-empty-summary"]`.
- **Giữ nguyên**: `0 button` (`:301`) · `0 conn-row` (`:302`) · 3 assert đầu (`không 'Bản ghi liên quan'` · `không SECTION` · `vm.total === 2`).
- **Bồi**: nhãn VI của ô rỗng (`Hồ sơ phân tích nguyên nhân gốc`) **phải** nằm trong dòng gộp.
- **Lý do hợp lệ**: assert cũ khoá một cài đặt **phản hợp đồng** (D-FE-8 từ vòng 2 nói ô rỗng **không** có ô riêng). Sửa test theo hợp đồng — tiền lệ `07 §XVIII.7.3`.
- **22 TC còn lại: 0 assert được sửa** (mọi ô trong fixture đều có số đếm > 0 — soát @source ADR §14.8).

### VIII.8.6 DoD FE (vòng AC-CR-93 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vitest run` **0 fail**; `npx vue-tsc --noEmit` **0 lỗi**.
- **Chấm theo DELTA, không theo số tuyệt đối** (số baseline trong tài liệu bàn giao **luôn có thể stale**): đọc số **trước** vòng ngay khi bắt đầu, báo cáo **trước → sau**. Đo trên đĩa 2026-07-28: **280 file** test (`find frontend/src -name '*.test.ts' | wc -l`); lần chạy đầy đủ gần nhất **280 file / 2649 test** (ADR §13.9). Ngưỡng: **≥ 278 file / ≥ 2591 test** ∧ **+≥6 test MỚI**.
- **Test RENDER trên DOM** (không chỉ helper) phủ **INV-CONNFE6-1..8** — bảng TC @[`07 §XVIII.8`](./07_Testing_QA.md).
- Fixture **giống thật**: một payload **19 ô / 3 có dữ liệu** (khuôn đồ thị `ac_asset_dashboard`) ⇒ assert `conn-item` **== 3** và giảm ≥ **84%**. Đếm bằng `findAll(testid).length`, **không** bằng `text().includes`.
- `git status`: **0** file `.py` thay đổi bởi vòng này; `git diff --name-only` phía FE **chỉ** 4 file ở §VIII.8; `git diff frontend/src/api/connections.ts` **không** chứa dòng nào của `DOCTYPE_LIST_TARGET` / `LIST_TARGET_NO_FILTER` (INV-CONNFE5-4 vẫn phủ kín 20 doctype).
- **Guard count: DELTA = 0** — **KHÔNG đụng** `_EXPECTED_TEST_COUNT` **1024** · `_GUARD_SUITE_SUM` **1167** · `_MOBILE_OAS_TOTAL` **1193** · OAS **paths 110 / schemas 290 / parameters 38** (4 giá trị **đọc THẲNG từ đĩa 2026-07-28**). Vòng FE-thuần ⇒ **KHÔNG** cần chạy suite BE; nếu phải chạy = **scope đã sai**.
- ⛔ **KHÔNG** `npm run build` · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate`.

---
## VIII.9. AC-CR-94 — «Xem tất cả» dẫn **ĐẾN ĐÍCH**: 2 màn LỊCH đọc `route.query.asset` (ADR §15)

> Quyết định + lý lẽ + đính chính: [`ADR-IMM00-CONNECTIONS-TREE.md` §15](./ADR-IMM00-CONNECTIONS-TREE.md) (**D-CR94-1..9 · INV-CONNFE7-1..8 · INV-CONN-18..22**) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) (FR-00-CONN-05 / BR-00-CONN-42..49) · test: [`07 §XVIII.9`](./07_Testing_QA.md) · hợp đồng drill: [`05 §III.24.8`](./05_API_Specification.md).
>
> **Biên (A-biên) — FE chạm ĐÚNG 3 file sản phẩm**: `frontend/src/api/connections.ts` (**chỉ chuyển 2 entry giữa 2 bảng** — `listTarget` / `DOCTYPE_ROUTE` / `DOCTYPE_DETAIL_ROUTE` / `CREATE_PREFILL_QUERY_KEYS` **không đổi một dòng**) · `frontend/src/views/pm/PmScheduleListView.vue` · `frontend/src/views/calibration/CalibrationScheduleListView.vue`. Test: append `frontend/src/api/connections.test.ts` + 2 file test render (khuôn tên có sẵn: `views/calibration/calibrationScheduleListDrilldown.test.ts` · `views/pm/pmListDrilldown.test.ts`).
> **Sạch tuyệt đối**: `router/connectionsListParity.test.ts` (**cấm sửa** — guard xanh **là** bằng chứng) · `router/index.ts` · `router/routeAccess.ts` · `RelatedRecords.vue` · `api/imm00.ts` · `api/imm11.ts` (cả hai **đã** nhận đủ khoá) · `services/connections.py` · mọi `*_dashboard.py`.
> **1 file `.py` prod đổi trong vòng này** (do [BE], không phải FE): `assetcore/services/imm11.py::_extract_asset_in_scope` — xem ADR §D-CR94-5 + [`../imm-11/05 §0.1.6`](../imm-11/05_API_Specification.md).

### VIII.9.1 `api/connections.ts` — 2 entry **chuyển tập** (11 → 9 / 9 → 11)

```ts
// THÊM vào DOCTYPE_LIST_TARGET (9 → 11) — sourceKeys = Link field THẬT trỏ AC Asset:
'PM Schedule':              { path: '/pm/schedules',          queryKey: 'asset', sourceKeys: ['asset_ref'] },
'IMM Calibration Schedule': { path: '/calibration/schedules', queryKey: 'asset', sourceKeys: ['asset'] },
// XOÁ 2 dòng tương ứng khỏi LIST_TARGET_NO_FILTER (11 → 9) + xoá 2 dòng "Lý do từng dòng"
// trong docblock của bảng đó (docblock là phần hợp đồng đọc được — để lại là nói dối).
```

- Phân hoạch giữ nguyên: 11 + 9 = **20** = `|DOCTYPE_ROUTE|` ⇒ INV-CONNFE5-4 xanh **mà không sửa guard**.
- `sourceKeys` **verify từ schema** (2026-07-28): `PM Schedule.asset_ref` và `IMM Calibration Schedule.asset` đều là `Link → AC Asset`, `reqd=1` ⇒ guard "sourceKeys là Link trỏ đúng neo" xanh.
- **KHÔNG** đụng `listTarget()`: dịch khoá đã đúng sẵn (bước 6 đổi khoá, giữ value).

### VIII.9.2 `views/pm/PmScheduleListView.vue` — wire đủ **bốn** vế (ADR §D-CR94-1)

| # | Vế | Cài đặt chốt |
|---|---|---|
| 1 | **Khởi tạo trước lần nạp đầu** | thêm `useRoute()`; `const assetFilter = ref((route.query.asset as string) || '')` **ở khai báo** (trước `onMounted(load)`) ⇒ request đầu tiên **đã** mang `asset`, không nạp-rồi-lọc-lại |
| 2 | **Truyền xuống API** | trong `load()`: `listPmSchedules({ page, page_size, asset: assetFilter.value || undefined, pm_type: …, status: …, search: … })` — `asset` **độc lập** với 3 khoá cũ (AND) |
| 3 | **Chip + bỏ chip** | `FilterChip.key` mở rộng `'asset'`; `activeChips` thêm `{ key: 'asset', label: \`Thiết bị: ${assetLabel}\` }` (khuôn ADR §15.2(3)); `clearChip('asset')` + `resetFilters()` xoá `assetFilter` **và** query (vế 3b) |
| 3b | **Bỏ chip xoá QUERY** | `router.replace({ query: { ...route.query, asset: undefined } })` rồi `page = 1; load()` ⇒ 0 lọc ẩn còn treo sau F5/back (BR-00-CONN-46) |
| 4 | **`watch`** | `watch(() => route.query.asset, (v) => { assetFilter.value = (v as string) \|\| ''; page.value = 1; load() })` — drill lần 2 từ thiết bị khác phải đổi kết quả |

- **`status` / `pm_type` GIỮ RỖNG** khi vào từ deep-link (BR-00-CONN-44) — `filters` mặc định đã rỗng, **cấm** thêm giá trị mặc định "cho gọn".
- `assetLabel` = `items.find(i => i.asset_ref === assetFilter.value)?.asset_name || assetFilter.value` — **0 request mới** (view đã có `asset_name` từ BE `list_pm_schedules`), và không bao giờ rỗng.
- Watcher `filters` (deep, debounce 300ms) **không** bao gồm `assetFilter` ⇒ tránh double-load; `assetFilter` có watcher riêng ở vế 4.
- Tiêu đề/`subtitle` giữ nguyên khuôn hiện có; **không** thêm chuỗi tiếng Anh, **không** in `asset_ref` như nhãn (LL-FE-53).

### VIII.9.3 `views/calibration/CalibrationScheduleListView.vue` — `asset` GIAO với chuỗi ưu tiên ngày

```ts
// filters ref: thêm 1 khoá, KHÔNG chạm 3 khoá drill cũ
asset: (route.query.asset as string) || '',

// buildFilters(): thêm NGOÀI chuỗi if/else if ưu tiên (overdue > due_soon > due_before)
if (filters.value.asset) f.asset = filters.value.asset      // AND — không clobber, không bị clobber

// activeChips: chip ĐẦU hoặc cuối đều được, nhãn theo khuôn duy nhất
if (filters.value.asset) chips.push({ key: 'asset', label: `Thiết bị: ${assetLabel.value}` })

// clearChip('asset'): filters.value.asset = '' + router.replace bỏ query.asset + load(1)
// watch(() => route.query.asset): cập nhật + load(1)  — cùng khuôn 3 watcher đã có (:135-137)
```

- `FilterChip.key` union thêm `'asset'`; `resetFilters()` thêm `asset: ''` **và** xoá query (nếu không, «Xóa tất cả» để lại lọc ẩn — chính lỗi BR-00-CONN-46).
- `is_active` **giữ rỗng** khi vào từ deep-link ⇒ lịch `is_active=0` vẫn hiện (BR-00-CONN-44) ⇒ `count == drill`.
- `assetLabel` = `items.find(i => i.asset === filters.value.asset)?.asset_name || filters.value.asset` (BE đã denorm `asset_name` trong `list_schedules`).
- ⚠️ **Phụ thuộc BE**: cho tới khi [BE] land nhánh vô hướng của `_extract_asset_in_scope`, `filters.asset` bị **nuốt câm** ⇒ test render (mock) xanh mà màn thật vẫn ra toàn viện. Vế (c) của D-CR94-1 chấm bằng **test BE** `07 §XVIII.9`, không bằng con mắt.

### VIII.9.4 Invariants FE (INV-CONNFE7-1..8)

Bảng đầy đủ ở **ADR §15.3**. Loại test: **tĩnh** 1 (guard cũ, không sửa) · **thuần** 2 (`api/connections.test.ts`) · **render** 3–8 (2 file test màn lịch).

### VIII.9.5 DoD FE (vòng AC-CR-94 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vitest run` **0 fail**; `npx vue-tsc --noEmit` **0 lỗi**.
- **Chấm theo DELTA, đọc baseline TỪ ĐĨA**: baseline đo 2026-07-28 (sau AC-CR-93) = **280 file / 2660 test** xanh — số trong prompt/STATE (278/2591) là **stale**. Delta yêu cầu **≥ +5 test**.
- Guard `router/connectionsListParity.test.ts` xanh **mà không sửa một dòng** (nếu phải nới ⇒ thăng hạng sai).
- Test RENDER (không chỉ helper) phủ **INV-CONNFE7-3..8** cho **cả hai** màn.
- `git diff --name-only` phía FE **chỉ** chứa 3 file sản phẩm + 3 file test kể ở đầu §VIII.9.
- **Guard count: DELTA = 0** — **KHÔNG đụng** `_EXPECTED_TEST_COUNT` · `_GUARD_SUITE_SUM` · `_MOBILE_OAS_TOTAL` (3 counter chỉ đếm 7 module guard mobile-OAS; đọc lại giá trị từ đĩa trước khi kết luận — ADR §D-CR94-9).
- ⛔ **KHÔNG** `npm run build` (= deploy live) · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate` / `bench restart`.

---

## VIII.10. AC-CR-95 — thăng hạng **4 màn đích** còn lại có hạ tầng BE sẵn: `LIST_TARGET_NO_FILTER` 9 → **5** (ADR §16)

> Quyết định + lý lẽ + đính chính: [`ADR-IMM00-CONNECTIONS-TREE.md` §16](./ADR-IMM00-CONNECTIONS-TREE.md) (**D-CR95-1..10 · INV-CONNFE8-1..10 · INV-CONN-23..28**) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) (FR-00-CONN-05 / BR-00-CONN-50..58) · test: [`07 §XVIII.10`](./07_Testing_QA.md) · hợp đồng drill: [`05 §III.24.9`](./05_API_Specification.md).
>
> **Biên (A-biên) — FE chạm ĐÚNG 6 file sản phẩm**: `frontend/src/api/connections.ts` (**chỉ chuyển 4 entry giữa 2 bảng** + cập nhật docblock — `listTarget` / `LIST_TARGET_ANCHOR` / `DOCTYPE_ROUTE` / `DOCTYPE_DETAIL_ROUTE` / `CREATE_PREFILL_QUERY_KEYS` **không đổi một dòng**) · `frontend/src/types/imm04.ts` (**thêm 1 field** `final_asset?: string`) · 4 view: `views/document/FirmwareCrListView.vue` · `views/commissioning/CommissioningListView.vue` · `views/eol/DecommissionListView.vue` · `views/incident/CAPAListView.vue`.
> **Sạch tuyệt đối**: `router/connectionsListParity.test.ts` (**cấm sửa** — guard xanh **là** bằng chứng) · `router/index.ts` · `RelatedRecords.vue` · `api/imm00.ts` · `api/imm04.ts` · `api/imm14.ts` · `stores/imm00.ts` · `stores/imm04.ts` (tất cả **đã** nhận đủ khoá) · mọi file `.py`.
> **0 file `.py` đổi ⇒ 0 blocker `bench restart` mới trong vòng này.** BE chỉ **thêm 1 file test guard**.

### VIII.10.1 `api/connections.ts` — 4 entry **chuyển tập** (11 → 15 / 9 → 5)

```ts
// THÊM vào DOCTYPE_LIST_TARGET (11 → 15) — sourceKeys = Link field THẬT trỏ AC Asset:
'Firmware Change Request': { path: '/cm/firmware',   queryKey: 'asset', sourceKeys: ['asset_ref'] },
'Asset Commissioning':     { path: '/commissioning', queryKey: 'asset', sourceKeys: ['final_asset'] },
'Asset Decommission':      { path: '/decommissions', queryKey: 'asset', sourceKeys: ['asset'] },
'IMM CAPA Record':         { path: '/capas',         queryKey: 'asset', sourceKeys: ['asset'] },
// XOÁ 4 dòng tương ứng khỏi LIST_TARGET_NO_FILTER (9 → 5) + XOÁ 4 dòng "Lý do từng dòng"
// trong docblock của bảng đó (docblock là hợp đồng đọc được — để lại là nói dối bằng comment).
```

- `LIST_TARGET_NO_FILTER` còn **đúng 5**: `AC Asset` · `AC Supplier` · `IMM Device Model` · `IMM Critical Spare Watchlist` · `AC Spare Part`. Phân hoạch 15 + 5 = **20** = `|DOCTYPE_ROUTE|` ⇒ INV-CONNFE5-4 xanh **mà không sửa guard**.
- `sourceKeys` **verify từ schema** (đọc `<slug>.json`, 2026-07-28): `Firmware Change Request.asset_ref` (reqd=1) · `Asset Commissioning.final_asset` · `Asset Decommission.asset` (reqd=1) · `IMM CAPA Record.asset` — **cả 4** là `Link → AC Asset`.
- **KHÔNG** đụng `listTarget()` và **KHÔNG** thêm khoá vào `LIST_TARGET_ANCHOR`: khoá URL cho thiết bị **luôn** là `asset` (ADR §D-CR95-2). Việc dịch sang khoá BE là việc của **view**.
- ⚠️ `sourceKeys` vòng này **thật sự chịu lực**: 4 doctype đến từ **8 hub** với **6 anchor** (bảng ADR §16.1-b). Thêm `vendor`/`master_item`/`linked_incident` vào `sourceKeys` = tự tay đẩy mã nhà cung cấp/mẫu thiết bị/sự cố vào `?asset=` ⇒ danh sách **RỖNG câm**.

### VIII.10.2 Bảng dịch khoá — **view** chịu tầng 1→2, **BE** chịu tầng 2→3

| Màn | Khoá URL đọc | Khoá gửi BE | Lời gọi | Thêm gì ở FE |
|---|---|---|---|---|
| `/cm/firmware` | `route.query.asset` | tham số `asset` | `listFirmwareCrs({ …, asset })` | 0 (view đã có `filters.asset`) |
| `/commissioning` | `route.query.asset` | `filters.final_asset` | `store.fetchList(cleanFilters(), 1)` | `final_asset?: string` vào `CommissioningFilters` (`types/imm04.ts:335`) |
| `/decommissions` | `route.query.asset` | `filters.asset` | `listDecommissions(filters, page, PAGE_SIZE)` | 0 (`DecommissionListFilters.asset` có sẵn `:155`) |
| `/capas` | `route.query.asset` | tham số `asset` | `store.fetchList(buildParams())` | 0 |

### VIII.10.3 Bốn vế D-CR94-1 × 4 màn — cài đặt chốt

| # | Vế | Cài đặt chốt (áp cho **cả 4** màn) |
|---|---|---|
| 1 | **Khởi tạo TRƯỚC lần nạp đầu** | thêm `useRoute()` ở **2/4** màn chưa import (`FirmwareCrListView.vue:4` · `DecommissionListView.vue:16` — `CAPAListView.vue:3` và `CommissioningListView.vue:3` đã có); khởi tạo state ở **khai báo** `(route.query.asset as string) \|\| ''`, **không** trong `onMounted` ⇒ request **đầu tiên** đã mang khoá (INV-CONNFE8-4) |
| 2 | **Truyền xuống API** | dịch theo bảng §VIII.10.2; khoá asset **độc lập** (AND) với mọi khoá lọc cũ — **không** clobber và **không** bị clobber |
| 3 | **Chip + bỏ chip** | `activeChips` thêm `{ key: 'asset', label: \`Thiết bị: ${assetLabel}\` }` (khuôn ADR §15.2(3) — **không** phát minh mẫu thứ hai); `clearChip('asset')` **và** `resetFilters()` xoá state **và** query |
| 3b | **Bỏ chip xoá QUERY** | `router.replace({ query })` sau khi `delete query.asset` (giữ query khác) rồi `page = 1` + nạp lại ⇒ 0 lọc ẩn còn treo sau F5/back/share (BR-00-CONN-56) |
| 4 | **`watch`** | `watch(() => route.query.asset, v => { <state> = (v as string) \|\| ''; page = 1; <load>() })` — drill lần 2 từ thiết bị khác trên **cùng** route không remount component |

**Nhãn chip — trường khớp mã trên từng màn (0 request mới, BE đã denorm):**

| Màn | Dòng khớp mã theo | Trường tên |
|---|---|---|
| `/commissioning` | `final_asset` | `asset_name` |
| `/decommissions` | `asset` | `asset_name_snapshot` (fallback `asset`) |
| `/capas` | `asset` | `asset_name` |
| `/cm/firmware` | `asset_ref` | `asset_name` |

`assetLabel = items.find(<khớp mã>)?.<trường tên> || <mã>` — **không bao giờ** rỗng, **không bao giờ** in fieldname (LL-FE-53).

### VIII.10.4 Ghi chú riêng từng màn (đọc trước khi sửa — 4 màn KHÔNG cùng khuôn)

- **`FirmwareCrListView.vue`** — rẻ nhất: `filters.asset` **đã** wire xuống BE (`:121`) và **đã** có `watch(filters, deep, 300ms)` (`:129`) ⇒ chỉ cần (a) `useRoute()` + init `asset` ở `:31`, (b) `dropAssetQuery()` trong `clearChip`/`resetFilters` (`:109-110`), (c) `watch(() => route.query.asset)`, (d) nâng nhãn chip từ mã thuần (`:100`) sang `asset_name || mã`. **KHÔNG** đụng input "Mã thiết bị" ở `:210` (người dùng vẫn tự gõ được).
- **`CommissioningListView.vue`** — thêm `final_asset` vào `filters` ref (`:23-29`) **và** `cleanFilters()` (`:69-78`) **và** `resetFilters()` (`:83`) **và** union `ChipKey` (`:46`); `onMounted` đã gọi `store.fetchList(cleanFilters(), 1)` (`:118`) ⇒ vế 1 tự đúng khi init từ `route.query`. `watch(() => route.query.workflow_state)` hiện có (`:124`) — **thêm** watcher thứ hai cho `asset`, **không** gộp.
- **`DecommissionListView.vue`** — màn **chưa có chip nào** (2 `<select>` + nút "Xóa bộ lọc", `:124-148`): thêm **đúng một** chip cho `asset` (markup tối thiểu, `data-testid` theo khuôn đang dùng), **KHÔNG** refactor sang `ListFilterBar` (ngoài A-biên). `activeFilterCount` (`:63`) phải tính thêm `asset`. `watch([stateFilter, methodFilter])` (`:91`) — thêm `assetFilter` vào mảng **hoặc** watcher riêng, miễn không double-load.
- **`CAPAListView.vue`** — `buildParams()` (`:64`) thêm `asset: assetFilter.value || undefined`; `showFilters` init (`:22`) **thêm** `route.query.asset` vào biểu thức (vào từ deep-link thì mở sẵn panel lọc để người dùng thấy mình đang lọc gì); `resetFilters()` (`:50`) gọi `store.fetchList()` **rỗng** ⇒ phải xoá query trước, nếu không F5 lọc lại.

### VIII.10.5 Cấm tự thêm bộ lọc trạng thái khi vào từ deep-link (BR-00-CONN-54)

| Màn | Khoá **cấm** tự set |
|---|---|
| `/commissioning` | `workflow_state`, `overdue` |
| `/decommissions` | `workflow_state`, `disposal_method` |
| `/capas` | `status`, `not_closed`, `overdue` |
| `/cm/firmware` | `status` |

Ô đếm **mọi** bản ghi của thiết bị ⇒ thêm bộ lọc mặc định phá `count == drill` theo hướng khó thấy nhất (`total` 3, bảng 2 dòng — trông như phân trang) **và** ẩn đúng thứ người dùng cần thấy (phiếu `Non Conformance`, CAPA `Closed`, FCR `Rolled Back`, biên bản `Cancelled`).

### VIII.10.6 Invariants FE (INV-CONNFE8-1..10)

Bảng đầy đủ ở **ADR §16.3**. Loại test: **tĩnh** 1 (guard cũ, không sửa) · **thuần** 2–3 (`api/connections.test.ts`) · **render** 4–10 (**4** file test mount, 1 file/màn).

⚠️ **INV-CONNFE8-3 phải dùng payload NGOẠI LAI THẬT** (ADR §16.7(3)): `{name:'FCR-…'}` · `{vendor:'SUP-…'}` · `{master_item:'MODEL-…'}` · `{linked_incident:'INC-…'}`. Khoá `asset_repair_wo` **không tồn tại** trong đồ thị cho `Firmware Change Request` (hub `Asset Repair` khai bằng `internal_links` ⇒ payload là `{name:…}`) ⇒ test bằng khoá đó là guard **vacuous**.

### VIII.10.7 DoD FE (vòng AC-CR-95 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `cd frontend && npx vitest run` **0 fail**; `npx vue-tsc --noEmit` **0 lỗi**.
- **Chấm theo DELTA, đọc baseline TỪ ĐĨA**: baseline đo 2026-07-28 **trước** vòng này = **282 file / 2682 test** xanh (số 280/2660 ở §VIII.9.5 và 278/2591 ở STATE đều **stale**). Delta yêu cầu **≥ +8 test**.
- Guard `router/connectionsListParity.test.ts` xanh **mà không sửa một dòng**.
- Test **mount** (không grep, không chỉ helper) phủ **INV-CONNFE8-4..10** cho **cả bốn** màn.
- **Mutation check** (chứng minh guard SỐNG): xoá `route.query.asset` khỏi **bất kỳ** 1 trong 4 view ⇒ **≥2** test ĐỎ (1 guard tĩnh phân hoạch + 1 test wire); đổi `sourceKeys` của `Asset Commissioning` thành `['vendor']` ⇒ ĐỎ ở guard schema (`connectionsListParity.test.ts:83`).
- `git diff --name-only` phía FE **chỉ** chứa 6 file sản phẩm ở đầu §VIII.10 + file test.
- **Guard count: DELTA = 0** — **KHÔNG đụng** `_EXPECTED_TEST_COUNT` (1024) · `_GUARD_SUITE_SUM` (1167) · `_MOBILE_OAS_TOTAL` (1193). Đề mục vòng này ghi "counter tăng đúng số TC thêm" là **SAI** — đã đính chính ở ADR §16.7(2); QA chấm delta-0 là **PASS**.
- ⛔ **KHÔNG** `npm run build` (= deploy live) · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate` / `bench restart` · **KHÔNG** sửa file `.py` prod.

---

---

## VIII.11. AC-CR-100 — tab «Lịch sử» (dòng thời gian vòng đời): TỔNG THẬT + «Tải thêm» + 3 trạng thái tách rời (ADR §8)

> **CR**: `AC-CR-100` — đề mục PM gọi «AC-CR-96», số đó **đã bị chiếm** (bảng đối chiếu [ADR §8.0](./ADR-IMM00-TRUNCATION-SSOT.md)). Quyết định: **ADR-IMM00-TRUNCATION-SSOT §8** (D-TL-1..9 · INV-TL-1..11 · microcopy §8.8). FR-00-TL-01 / BR-00-TL-01..09: [02 §IV.40](./02_Analysis_Design.md). Hợp đồng API: [05 §III.25](./05_API_Specification.md). Test + DoD: [07 §XIX](./07_Testing_QA.md).
>
> **Biên (A-biên — đo được)**: FE chạm **ĐÚNG 1** file sản phẩm `frontend/src/views/asset/AssetDetailView.vue` (chỉ vùng tab `timeline`) + **1 file test mới** `frontend/src/views/asset/assetDetailTimelinePagination.test.ts`. BE chạm **ĐÚNG 1 dòng** `assetcore/api/imm00.py:293` + **1 class guard** trong `assetcore/tests/test_imm00.py`. Bất kỳ file khác trong diff ⇒ **ra khỏi biên ⇒ ĐỎ**.

### VIII.11.1 Hiện trạng phải sửa (verify @source 2026-07-28 — chép nguyên, đừng đọc lại bằng trí nhớ)

| # | Vị trí | Sai gì |
|---|---|---|
| H1 | `AssetDetailView.vue:202` | `await getAssetTimeline(props.id, 1, 100) as unknown as { items?: typeof timeline.value }` — cast **xoá `pagination` khỏi kiểu**; `api/imm00.ts:71` vốn khai đúng `Promise<PaginatedResponse<AssetLifecycleEvent>>`, `types/imm00.ts:15` vốn có `pagination.total` |
| H2 | `AssetDetailView.vue:202` | gọi cứng `page = 1`, **không có** đường sang trang 2 ⇒ dữ liệu vượt trần **không thể** tới người dùng bằng bất kỳ tương tác nào |
| H3 | `AssetDetailView.vue:824-826` | `v-if="!timeline.length"` ⇒ *"Chưa có sự kiện vòng đời"* **cả khi API lỗi** (`loadTimeline` không `try/catch`; reject bị nuốt trong `onTabChange`) |
| H4 | `AssetDetailView.vue:399` | `if (tab === 'timeline' && !timeline.value.length)` — **cùng** vị-từ `length` làm cờ "chưa tải" ⇒ *rỗng thật* và *chưa tải* không phân biệt được ở lớp **logic** |
| H5 | `AssetDetailView.vue` (toàn tab) | 0 chỗ nào hiển thị **tổng**; người đọc không có cách biết đang xem một phần |

### VIII.11.2 State — thêm 6 `ref` + 3 `computed` (KHÔNG đụng `timeline` ref cũ ở `:45`)

**Import duy nhất phải thêm** (`AssetDetailView.vue:29`): bổ sung `PaginatedResponse` vào dòng `import type { AssetLifecycleEvent, AssetKpi, ChainVerifyResult, LifecycleStatus } from '@/types/imm00'` ⇒ `import type { AssetLifecycleEvent, AssetKpi, ChainVerifyResult, LifecycleStatus, PaginatedResponse } from '@/types/imm00'`. `notify` (`useNotify` `:32`) và `toApiError` (`:35`) **đã có sẵn** — KHÔNG thêm import mới nào khác.

```ts
// AC-CR-100 (ADR §8 D-TL-3/D-TL-4) — «Lịch sử» đọc nguồn ĐÃ phân trang: 3 trạng thái
// (chưa tải / rỗng thật / lỗi) phải có vị-từ RIÊNG; số công bố là total của SERVER.
// page_size CỐ ĐỊNH = trần thật của server (assetcore/utils/pagination.py:11 _MAX_PAGE_SIZE);
// xin lớn hơn chỉ nhận 100 ⇒ client sẽ tưởng đã lấy hết (INV-TRUNC-LIMIT / ADR §D5).
const TIMELINE_PAGE_SIZE = 100

const timelineTotal = ref(0)          // = pagination.total (SERVER) — KHÔNG suy từ timeline.length
const timelinePage = ref(0)           // trang đã tải xong cao nhất; 0 = CHƯA TẢI (vị-từ duy nhất)
const timelineLoading = ref(false)
const timelineError = ref<string | null>(null)
const timelineErrorPage = ref(1)                          // trang lỡ — để «Thử lại» đúng chỗ
const timelineErrorMode = ref<'reset' | 'append'>('reset')
const timelineExhausted = ref(false)  // trang trả 0 dòng MỚI ⇒ chống «Tải thêm» không tiến

const timelineHasMore = computed(
  () => !timelineExhausted.value && timeline.value.length < timelineTotal.value,
)
const timelineViewingPartial = computed(() => timeline.value.length < timelineTotal.value)
const timelineEmpty = computed(
  () => timelinePage.value > 0 && timelineError.value === null && timelineTotal.value === 0,
)
```

### VIII.11.3 Fetcher — 1 hàm lõi + 3 wrapper (thay `loadTimeline` cũ `:201-204`)

```ts
// Lõi: nạp 1 trang. mode='reset' → thay danh sách (refresh sau thao tác ghi, D-TL-9);
// mode='append' → nối + dedupe theo `name` (D-TL-5). KHÔNG cast — dùng đúng kiểu api-client (D-TL-1).
async function fetchTimelinePage(page: number, mode: 'reset' | 'append') {
  if (timelineLoading.value) return
  timelineLoading.value = true
  timelineError.value = null
  try {
    const res: PaginatedResponse<AssetLifecycleEvent> = await getAssetTimeline(
      props.id, page, TIMELINE_PAGE_SIZE,
    )
    const rows = res.items ?? []
    const base = mode === 'reset' ? [] : timeline.value
    const seen = new Set(base.map((e) => e.name))
    const fresh = rows.filter((e) => !seen.has(e.name))   // dedupe theo `name` (D-TL-5)
    timeline.value = base.concat(fresh)
    // D-TL-6: total của SERVER thắng, nhưng KHÔNG BAO GIỜ nhỏ hơn số dòng đang render.
    timelineTotal.value = Math.max(Number(res.pagination?.total ?? 0), timeline.value.length)
    timelinePage.value = page
    // D-TL-8 — hai điều kiện "hết nguồn": trang ngắn hơn trần, HOẶC 0 dòng MỚI sau dedupe.
    if (rows.length < TIMELINE_PAGE_SIZE) timelineExhausted.value = true
    if (mode === 'append' && fresh.length === 0) timelineExhausted.value = true
    // Hậu điều kiện DUY NHẤT chống INV-TL-8: hết nguồn mà vẫn thiếu ⇒ danh sách đã đổi
    // dưới chân người dùng ⇒ PHẢI có đường hành động (nút ẩn + dải lỗi + retry reset).
    if (timelineExhausted.value && timeline.value.length < timelineTotal.value) {
      timelineError.value = 'Danh sách sự kiện đã thay đổi trong lúc tải. Vui lòng tải lại.'
      timelineErrorPage.value = 1
      timelineErrorMode.value = 'reset'
    }
  } catch (e: unknown) {
    // "chưa tải được" ≠ "chưa có": dải lỗi riêng + KHÔNG chạm timelinePage ⇒ empty-state KHÔNG hiện.
    timelineError.value = 'Không tải được dòng thời gian vòng đời. Vui lòng thử lại.'
    timelineErrorPage.value = page
    timelineErrorMode.value = mode
    notify.fromError(toApiError(e))   // hợp đồng thông báo — KHÔNG nuốt lỗi im lặng
  } finally {
    timelineLoading.value = false
  }
}

async function loadTimeline() {                 // reset (2 call-site ghi hiện có GIỮ NGUYÊN tên gọi)
  timelineExhausted.value = false
  await fetchTimelinePage(1, 'reset')
}
async function loadMoreTimeline() {             // append — KHÔNG reset (A6)
  await fetchTimelinePage(timelinePage.value + 1, 'append')
}
async function retryTimeline() {                // tải lại ĐÚNG trang lỡ (D-TL-7)
  if (timelineErrorMode.value === 'reset') timelineExhausted.value = false
  await fetchTimelinePage(timelineErrorPage.value, timelineErrorMode.value)
}
```

**Guard nạp lười — sửa `onTabChange:399`** (H4): `if (tab === 'timeline' && timelinePage.value === 0 && !timelineLoading.value) await loadTimeline()`. **CẤM** quay lại `!timeline.value.length` (BR-00-TL-03). Hệ quả đúng: asset rỗng thật ⇒ **không** gọi lại API mỗi lần mở tab; lỗi ở **trang 1** ⇒ `timelinePage` vẫn `0` ⇒ mở lại tab **có** thử lại; lỗi ở trang ≥2 ⇒ đã có nút «Thử lại» (D-TL-7).

**2 call-site ghi GIỮ NGUYÊN** (`confirmTransition` + `confirmDecommission` → `Promise.all([store.fetchOne, loadTimeline()])`): ngữ nghĩa **reset** là chủ ý (event mới nhất đứng đầu).

### VIII.11.4 Template — chép nguyên hình dạng (thay khối `:823-826`, GIỮ nguyên vòng lặp `:829-860`)

```html
<div v-if="activeTab === 'timeline'">
  <!-- 1. dải lỗi — ĐỨNG TRƯỚC mọi thứ; loại trừ empty-state (INV-TL-7) -->
  <div v-if="timelineError" data-testid="timeline-error" role="alert" class="card p-4 mb-3 …">
    <p class="text-sm">{{ timelineError }}</p>
    <button type="button" data-testid="timeline-retry" :disabled="timelineLoading"
            class="…" @click="retryTimeline">Thử lại</button>
  </div>

  <!-- 2. header số THẬT — chỉ khi đã tải xong ≥1 trang và có dữ liệu -->
  <div v-if="timelinePage > 0 && timelineTotal > 0" class="flex items-center gap-2 mb-3 text-sm">
    <span data-testid="timeline-total" class="font-medium text-slate-700">{{ timelineTotal }} sự kiện</span>
    <span v-if="timelineViewingPartial" data-testid="timeline-viewing" class="text-slate-500">
      Đang xem {{ timeline.length }}/{{ timelineTotal }}
    </span>
  </div>

  <!-- 3. rỗng THẬT (chuỗi cũ GIỮ NGUYÊN) -->
  <div v-if="timelineEmpty" data-testid="timeline-empty" class="card p-8 text-center text-slate-400 text-sm">
    Chưa có sự kiện vòng đời
  </div>
  <!-- 4. đang tải trang ĐẦU (khác "chưa có") -->
  <div v-else-if="timelineLoading && timelinePage === 0" data-testid="timeline-loading"
       class="card p-8 text-center text-slate-400 text-sm">Đang tải dòng thời gian…</div>
  <!-- 5. danh sách — nguyên khối cũ, KHÔNG sửa nội dung từng dòng -->
  <div v-else-if="timeline.length" class="relative"> … (giữ nguyên :828-860) … </div>

  <!-- 6. «Tải thêm» — tồn tại ⟺ còn dữ liệu (INV-TL-3) -->
  <div v-if="timelineHasMore" class="mt-2 text-center">
    <button type="button" data-testid="timeline-load-more" :disabled="timelineLoading"
            class="btn-secondary text-sm" @click="loadMoreTimeline">
      {{ timelineLoading ? 'Đang tải…' : 'Tải thêm' }}
    </button>
  </div>
</div>
```

### VIII.11.5 Bảng quyết định render (đọc thẳng khi code — KHÔNG suy luận lại)

| Ca | `page` | `total` (N) | rendered (M) | `error` | `timeline-total` | `timeline-viewing` | `timeline-load-more` | `timeline-empty` | `timeline-error` |
|---|---|---|---|---|---|---|---|---|---|
| chưa mở tab | 0 | 0 | 0 | null | — | — | — | — | — |
| trang 1 đang tải | 0 | 0 | 0 | null | — | — | — | — | — |
| 137 sự kiện, đã tải 100 | 1 | 137 | 100 | null | `137 sự kiện` | `Đang xem 100/137` | ✅ | — | — |
| bấm «Tải thêm» xong | 2 | 137 | 137 | null | `137 sự kiện` | — | — | — | — |
| 7 sự kiện, đã tải 7 | 1 | 7 | 7 | null | `7 sự kiện` | — | — | — | — |
| rỗng THẬT | 1 | 0 | 0 | null | — | — | — | ✅ | — |
| lỗi trang 1 | 0 | 0 | 0 | set | — | — | — | **—** | ✅ + «Thử lại» (page 1, reset) |
| lỗi trang 2 | 1 | 137 | 100 | set | `137 sự kiện` | `Đang xem 100/137` | — | — | ✅ + «Thử lại» (page 2, append) |
| danh sách đổi giữa 2 trang (0 dòng mới) | 2 | 137 | 100 | set (D-TL-8) | `137 sự kiện` | `Đang xem 100/137` | — | — | ✅ + «Thử lại» (page 1, reset) |
| trang cuối **ngắn** + có dòng trùng ⇒ vẫn thiếu | 2 | 137 | 132 | set (D-TL-8) | `137 sự kiện` | `Đang xem 132/137` | — | — | ✅ + «Thử lại» (page 1, reset) |
| trang cuối ngắn, dedupe vẫn đủ | 2 | 137 | 137 | null | `137 sự kiện` | — | — | — | — |

### VIII.11.6 Invariants FE (INV-TL-1..8 + INV-TL-11) — chấm bằng `vitest` **mount**, không grep

Phát biểu đầy đủ ở [ADR §8.3](./ADR-IMM00-TRUNCATION-SSOT.md). Yêu cầu bổ sung riêng cho FE:
- Test phải **mount** view thật (khuôn `assetDetailTransitionAuthz.test.ts`), mock `@/api/imm00` → `getAssetTimeline` là `vi.fn()` **đếm được** và **kiểm tham số** (`page`, `page_size`).
- INV-TL-11 đo bằng **spy đếm lời gọi**: mount ở tab `info` ⇒ `getAssetTimeline` **0 lần**; tab `related` giữ `v-if` ⇒ `getConnections` **0 lần** (guard cũ `relatedRecordsTabParity.test.ts` **không sửa**).
- Assert `page_size === 100` **ở CẢ hai** lời gọi (trang 1 và trang 2) — A4 (chống "tăng page_size cho nhanh").
- **CẤM** đổi/xoá testid cũ trong vòng lặp dòng (`ale-event-type` / `ale-status-transition` / `ale-actor` / `ale-root-link`) — hợp đồng CR-60.

### VIII.11.7 DoD FE (vòng AC-CR-100 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `grep -n 'as unknown' frontend/src/views/asset/AssetDetailView.vue` **KHÔNG** còn hit nào trong họ hàm timeline (`fetchTimelinePage`/`loadTimeline`/`loadMoreTimeline`/`retryTimeline`). 2 hit còn lại ở `loadKpi`/`loadChain` là **nợ có tên `AC-CR-101`** (ADR §8.7) — QA **không** chấm là thiếu.
- `npx vue-tsc --noEmit` **0 lỗi**.
- `npx vitest run` **0 ĐỎ**; **đọc baseline TỪ ĐĨA ngay trước khi chấm** (đo lúc chốt spec 2026-07-28: **283 file** `*.test.ts`; số test tuyệt đối trong đề mục/STATE — 2591 hay 2682 — đều **có thể stale** ⇒ chấm theo **delta ≥ +10 test**, bộ TC ở `07 §XIX.3` có **15** ca).
- Test **mount** phủ đủ **11** dòng của bảng §VIII.11.5; **mutation check** chạy thật ≥2 dòng rồi **revert**: (a) đổi `timelineTotal` thành `timeline.value.length` ⇒ ≥1 test ĐỎ; (b) đổi điều kiện `timeline-empty` về `!timeline.length` ⇒ test ca "lỗi trang 1" ĐỎ.
- `git diff --name-only` phía FE **chỉ** `AssetDetailView.vue` + file test mới.
- ⛔ **KHÔNG** `npm run build` (= deploy live) · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate` / `bench restart`.

## VIII.12. AC-CR-92 — SIẾT hợp đồng «Bản ghi liên quan»: bỏ 4 khoá LEGACY, `capped` → `total_capped` (ADR §17)

> Hợp đồng BE: [`05 §III.24.10`](./05_API_Specification.md) · quyết định + invariants: [ADR §17](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR92-1..9 · INV-CONNFE9-1..6) · nghiệp vụ: [`02 §IV.39`](./02_Analysis_Design.md) BR-00-CONN-59..66 · test: [`07 §XVIII.11`](./07_Testing_QA.md).
> **Phạm vi FE (đóng kín)**: **1 file sản phẩm** `frontend/src/api/connections.ts` + **7 file test** (§VIII.12.4). `components/common/RelatedRecords.vue` **KHÔNG đổi một dòng** — đo 2026-07-28: nó đọc số/nhãn/dải **qua helper** (`countBadge`/`previewMeta`/`viLabel`/`dataCells`/`emptySummary`) và `:key="group.label"` dùng nhãn **NHÓM** (khoá được GIỮ) ⇒ 0 hit khoá legacy trong template. Đó chính là lợi tức của việc đặt hợp đồng ở `api/connections.ts`.
> ⛔ **KHÔNG** `npm run build` (= deploy live, LL-DEPLOY-09) · **KHÔNG** đụng `DOCTYPE_ROUTE` / `DOCTYPE_DETAIL_ROUTE` / `DOCTYPE_LIST_TARGET` / `LIST_TARGET_NO_FILTER` / `CREATE_PREFILL_QUERY_KEYS` / `router/connectionsListParity.test.ts` / `router/connectionsCreateParity.test.ts`.

### VIII.12.1 `ConnectionItem` — 4 khoá XOÁ, 8 khoá thành BẮT BUỘC

```ts
export interface ConnectionItem {
  doctype: string
  /** Nhãn tiếng Việt (SSoT `LABEL_VI` ở BE) — nhãn DUY NHẤT của ô sau AC-CR-92. */
  label_vi: string
  /** Số bản ghi user thấy, ĐÃ CHẶN TRẦN 100. `total_capped === 1` ⇒ đây là CẬN DƯỚI. */
  total: number
  /** `1` = còn bản ghi chưa nằm trong `items` (cắt so với preview_limit). int, KHÔNG bool. */
  truncated: 0 | 1
  /** `1` = `total` chạm trần đếm ⇒ PHẢI render `"100+"`; CẤM mọi phép trừ trên `total`. */
  total_capped: 0 | 1
  items: ConnectionPreviewRow[]
  deep_link_filters: Record<string, string>
  can_create: boolean
  create_route_hint: string
  /** CHƯA CÀI ở BE (ADR §17 D-CR92-7 · nợ `AC-CR-90(b)`) ⇒ GIỮ optional, đừng xoá. */
  create_prefill?: Record<string, string>
}
```

**XOÁ hẳn**: `label` · `count` · `capped` · `filters` (4 khoá). `ConnectionGroup` **KHÔNG đổi** (`label` + `label_vi?` + `items`) — nhãn nhóm là nguồn sự thật tiếng Việt, xem BR-00-CONN-63.

### VIII.12.2 Helper — 4 sửa, 2 xoá

| Hàm | Thay đổi |
|---|---|
| `itemTotal` | `item.total ?? item.count ?? 0` → **`item.total ?? 0`** (giữ `?? 0` cho cửa sổ chưa-reload, không crash) |
| `countBadge` | `item.capped ? …` → **`item.total_capped === 1 ? \`${n}+\` : String(n)`** — so sánh **tường minh** với `1`; khoá vắng ⇒ `'7'`, **không** `'7+'`, **không** optional-chaining |
| `previewMeta` | bỏ nhánh suy diễn `item.truncated ?? (shown < itemTotal(item) ? 1 : 0)` → **`if (!item.truncated) return ''`**. Khuôn câu giữ nguyên `Đang xem ${shown}/${countBadge(item)}` (không phép trừ — D-FE-7) |
| `linkFilters` | **XOÁ hàm** (0 caller sản phẩm; `listTarget` là đường duy nhất) + xoá import trong `connections.test.ts` và 6 `it` gọi nó (chuyển ca còn giá trị sang `listTarget`) |
| `scalarFilters` | **XOÁ hàm** (không còn đầu vào sau khi `filters` bị gỡ) |
| `listTarget` | bỏ nhánh legacy: `const source = deep !== undefined ? deep : scalarFilters(item.filters)` → **`const source: Record<string, unknown> = item.deep_link_filters ?? {}`**. Bước 3–6 (bỏ khoá `name` · đúng 1 khoá · `sourceKeys` · dịch sang `queryKey`) **KHÔNG đổi một dòng** — `router/connectionsListParity.test.ts` phải xanh **mà không bị sửa** |
| `hasConnectionRecords` / `dataCells` / `emptyLabels` / `emptySummary` / `viLabel` / `createTarget` / `createLabel` | **KHÔNG đổi** (đã đọc qua `itemTotal` hoặc khoá được giữ) |

### VIII.12.3 Guard tĩnh chống hồi sinh (file MỚI)

`frontend/src/api/connectionsLegacyKeysRetired.acr92.test.ts` — quét **mọi** `frontend/src/**/*.{ts,vue}` (kể cả `*.test.ts`), đòi **0 hit**:

```
/\.capped\b/  ·  /\bitem\.count\b/  ·  /\bitem\.filters\b/  ·  /\bscalarFilters\b/  ·  /\blinkFilters\b/
```

- **Allowlist duy nhất**: `frontend/src/api/imm00.ts` — `totals_uncapped` là khoá **KHÁC** của endpoint **KHÁC** (`get_dashboard_kpis`). Allowlist **chỉ-giảm**; thêm file vào đây là sai chiều.
- Vì sao guard **tĩnh** chứ không dựa vào `vue-tsc`: `vue-tsc` bắt được khai báo thừa trong object literal có kiểu, nhưng **không** bắt được `(item as any).count` hay chuỗi trong comment/test helper — mà "tạm cast cho qua" chính là đường hồi sinh.

### VIII.12.4 File test dựng fixture ô — bỏ 4 khoá legacy, thêm `total_capped: 0`

Phạm vi rà: `api/connections.test.ts` · `components/common/RelatedRecords.test.ts` · `views/asset/assetDetailRelatedTab.test.ts` · `views/pm/pmDetailRelatedTab.test.ts` · `views/cm/cmDetailRelatedTab.test.ts` · `views/calibration/calibrationDetailRelatedTab.test.ts` · `views/incident/incidentDetailRelatedTab.test.ts`.

**Đo khi cài (2026-07-28)**: chỉ **2** file đầu thật sự dựng fixture Ô; **5** file `*RelatedTab.test.ts` chỉ mock payload rỗng (`{doctype, name, total: 0, groups: []}`) vì chúng kiểm *tab mount lười*, không kiểm nội dung ô ⇒ **KHÔNG đổi một dòng** (`grep -c total_capped` = 0 ở cả 5). Đây không phải "quên": `vue-tsc` xanh chính là bằng chứng — khoá thành bắt buộc thì fixture Ô thiếu khoá là lỗi KIỂU, không phải lỗi ẩn.

### VIII.12.5 Test RENDER bắt buộc (mount, không unit hàm thuần)

| Ca | Payload ô | Kỳ vọng DOM |
|---|---|---|
| Chạm trần | `{total:100, total_capped:1, truncated:1, items: 5 dòng}` | `[data-testid=conn-count]`.textContent **=== `'100+'`** ∧ `[data-testid=conn-meta]` chứa **`'Đang xem 5/100+'`** ∧ **0** badge `'100'` trần ∧ **0** chuỗi từ phép trừ (`'còn 95'`, `'95'`) |
| Không chạm trần | `{total:7, total_capped:0, truncated:1, items: 5 dòng}` | badge **`'7'`** ∧ meta chứa `'Đang xem 5/7'` |
| Nhỏ hơn preview | `{total:3, total_capped:0, truncated:0, items: 3 dòng}` | badge `'3'` ∧ **không** có `[data-testid=conn-meta]` |
| BE stale | `countBadge({... total:7, total_capped: undefined })` (unit) | trả **`'7'`** — không crash, không `'7+'` |
| Mutation (phải ĐỎ khi bỏ) | ô 5/7 nhưng **bỏ** `truncated` | dải cắt **MẤT** (chứng minh `previewMeta` không tự suy từ `items.length`) |

### VIII.12.6 DoD FE (vòng AC-CR-92 — chấm ĐỎ nếu thiếu bất kỳ mục nào)

- `npx vue-tsc --noEmit` **0 lỗi** (là oracle chính của "khoá thành bắt buộc").
- `npm run test:unit` (`npx vitest run`) **0 ĐỎ**; **đọc baseline TỪ ĐĨA ngay trước khi chấm** (số 2591 trong đề mục **có thể stale** — đo lúc chốt spec: ADR §13.9 ghi 2649, sau AC-CR-93/94/95 còn cao hơn) ⇒ chấm theo **delta ≥ 0** (vòng dọn nợ có thể **giảm** số `it` do gỡ 6 ca `linkFilters`, nhưng **tổng** phải ≥ baseline: mỗi ca gỡ phải có ca thay ở `listTarget`/`countBadge`).
- Guard tĩnh §VIII.12.3 xanh; `grep -rn 'scalarFilters\|linkFilters' frontend/src` ⇒ **0 hit**.
- `router/connectionsListParity.test.ts` + `router/connectionsCreateParity.test.ts` xanh **mà không bị sửa một dòng**.
- `git diff --name-only` phía FE: **1** file sản phẩm (`api/connections.ts`) + **3** file test (2 fixture theo §VIII.12.4 + 1 guard mới `api/connectionsLegacyKeysRetired.acr92.test.ts`). File khác ⇒ ra khỏi biên ⇒ ĐỎ — kể cả `components/common/RelatedRecords.vue` (đã đo: 0 hit khoá legacy, `:key="group.label"` dùng khoá NHÓM được GIỮ).
- ⛔ **KHÔNG** `npm run build` · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate` / `bench restart`.

## VIII.13. AC-CR-102 — hồ sơ **VẬN HÀNH** của thiết bị **render THẬT** trong tab «Bản ghi liên quan» (3 nhánh Bảo trì · Sửa chữa · Sự cố) — spec cho **[FE] Bước-4**

> Quyết định + lý do: [`ADR-IMM00-ASSET-OP-HISTORY`](./ADR-IMM00-ASSET-OP-HISTORY.md) (D-OPH-1..16). Hợp đồng ĐỌC: [`05 §III.26`](./05_API_Specification.md). Invariant/test: [`07 §XX`](./07_Testing_QA.md). **Vòng FE-only: 0 dòng `.py` prod.**
>
> ⚠️ **Self-Correction đã đóng**: `AC-CR-100` từng ghi Never «KHÔNG render 3 nhánh … lên màn Chi tiết tài sản». Điều khoản đó **hết hiệu lực** từ vòng này (ADR §2) — nay 3 nhánh **PHẢI** render, kèm 3 điều kiện C1/C2/C3.

### VIII.13.1 File đụng — **đúng 8 đường sản phẩm + 3 file test**

| # | Đường | Thay đổi |
|---|---|---|
| 1 | `frontend/src/components/asset/AssetOperationalHistory.vue` | **MỚI** — khối 3 section (props: `assetName: string`) |
| 2 | `frontend/src/views/asset/AssetDetailView.vue` | **+1 import +1 dòng** trong `[data-testid=tab-panel-related]` (`:1043-1045`), **SAU** `<RelatedRecords>`. **KHÔNG** đổi thanh tab (`:700`, `:711`) |
| 3 | `frontend/src/api/imm08.ts` | `interface PMTaskLogHistoryItem` (**MỚI**, 10 field) + generic của `getAssetPMHistory` (`:251-259`) đổi từ `PMWorkOrder[]` |
| 4 | `frontend/src/api/connections.ts` | **+1 helper THUẦN** `listRouteForAsset(doctype, assetName): string \| null` đọc `DOCTYPE_LIST_TARGET` (`:292`) + kiểm `LIST_TARGET_ANCHOR` (`:283`). **KHÔNG** sửa 4 bảng route |
| 5 | `frontend/src/stores/imm08.ts` | `fetchPMHistory` (`:212`) + **4 state mới** (§VIII.13.3) + **đổi kiểu ref** `pmHistory` (`:21`) `PMWorkOrder[]` → `PMTaskLogHistoryItem[]` (bắt buộc, không đổi ⇒ `vue-tsc` ĐỎ) |
| 6 | `frontend/src/stores/imm09.ts` | `fetchRepairHistory` (`:160`) + **4 state mới** |
| 7 | `frontend/src/stores/imm12.ts` | **`fetchIncidentHistory` MỚI** + **7 state mới** (store này chưa có gì) |
| 8 | `frontend/src/constants/labels.ts` | **+1 dòng** `'Warranty Repair': 'Bảo hành'` vào `REPAIR_TYPE_LABEL` (`:660`) — bổ khuyết map GỐC, **không** map thứ hai |
| T1 | `frontend/src/components/asset/assetOperationalHistory.test.ts` | **MỚI** — render/lười/3 trạng thái/nhãn VI/đếm trung thực |
| T2 | `frontend/src/router/assetOpHistoryRouteParity.test.ts` | **MỚI** — parity route SSoT + chống link chết + 0 URL literal |
| T3 | `assetcore/tests/test_asset_operational_history_contract.py` | **MỚI (BE, chỉ đọc)** — parity `fields` @source ⇄ `05 §III.26.3` |

File khác trong `git diff --name-only` ⇒ **ra khỏi biên ⇒ ĐỎ**. Ngoại lệ **duy nhất được phép**: `frontend/src/stores/assetHistoryTruncation.test.ts` nếu guard cache làm nó đỏ (§VIII.13.3 ⚠️) — phải khai trong báo cáo.

### VIII.13.2 Cây DOM + testid (SSoT — đổi testid ⇒ sửa `07 §XX` TRƯỚC)

> ⚠️ **CẬP NHẬT 2026-07-30 (`AC-CR-115`)** — cây dưới đây đã sửa **2 chỗ sai/lỗi thời**: (1) **thứ tự khối đảo** (`D-OPH-18`: bản ghi TRƯỚC ô chức năng) — bản cũ ghi `<RelatedRecords>` trước; (2) **testid heading**: `op-history-heading`/`op-history-title`/`op-history-total` **chưa bao giờ tồn tại trên đĩa** — vai của chúng do `op-history-toggle` (chứa chuỗi tiêu đề) + `op-history-count` (badge số trần) đảm nhiệm (`AssetOperationalHistory.vue:318-334`). Xem [ADR §5.3 + §10.7](./ADR-IMM00-ASSET-OP-HISTORY.md).

```
[data-testid="tab-panel-related"]
├── [data-testid="asset-op-history"]                      ← ĐÚNG 1 · KHỐI 1 = BẢN GHI THẬT
│   ├── <h3 [data-testid="related-block-heading"]>  «Dữ liệu vận hành của thiết bị»
│   ├── [data-testid="op-history-section"][data-branch="pm"]
│   │   ├── [data-testid="op-history-toggle"] (aria-expanded, CHỨA chuỗi tiêu đề)
│   │   │   ├── «Kết quả bảo trì»
│   │   │   └── [data-testid="op-history-count"]   «{N}» (badge số trần, iff loaded)
│   │   └── (khi bung) — ĐÚNG MỘT trong 4 nhánh:
│   │       ├── [data-testid="op-history-loading"]  «Đang tải…»
│   │       ├── [data-testid="op-history-error"] + [data-testid="op-history-retry"] «Thử lại»
│   │       ├── [data-testid="op-history-empty"]    «Chưa có …»              (total===0)
│   │       └── M× [data-testid="op-history-row"][data-branch="pm"]
│   │             ├── <a  [data-testid="op-history-row-link"]>    (đích ≠ null)
│   │             └── <span [data-testid="op-history-row-static"]> (đích null — 0 <a>)
│   │           + [data-testid="op-history-truncation"][data-branch="pm"]   ← MỚI AC-CR-115
│   │             «Đang xem {M}/{N} — còn {N−M} chưa hiển thị»   (iff N−M > 0)
│   │           + [data-testid="op-history-see-all"]  (iff loaded ∧ N>0)
│   ├── … [data-branch="cm"]       «Lần sửa chữa đã hoàn thành»
│   └── … [data-branch="incident"] «Sự cố đã ghi nhận»
└── <div>                                                 ← KHỐI 2 = Ô CHỨC NĂNG (bọc MỚI)
    ├── <h3 [data-testid="related-block-heading"]>  «Liên kết nhanh theo chức năng»
    └── <RelatedRecords doctype="AC Asset" :name="…"/>     ← GIỮ NGUYÊN, KHÔNG sửa 1 dòng
```

Thứ tự section **bất biến**: `pm → cm → incident` (trục vòng đời: phòng ngừa → khắc phục → sự cố).
Thứ tự **khối** bất biến: `[asset-op-history]` → `[related-records]` (`D-OPH-18`, `BR-00-OPH-27`). **KHÔNG** có «Tải thêm» ở khối này (`D-OPH-19`, `BR-00-OPH-25`).

### VIII.13.3 Store — 3 nhánh CÙNG khuôn (cache khoá theo thiết bị)

| Store | Đã có | **THÊM** |
|---|---|---|
| `imm08` | `pmHistory` `pmHistoryTotal` `pmHistoryTruncated` | `pmHistoryAsset: string` · `pmHistoryLoaded: boolean` · `pmHistoryLoading: boolean` · `pmHistoryFailed: boolean` |
| `imm09` | `repairHistory` `repairHistoryTotal` `repairHistoryTruncated` | `repairHistoryAsset` · `repairHistoryLoaded` · `repairHistoryLoading` · `repairHistoryFailed` |
| `imm12` | **(không có)** | `incidentHistory` · `incidentHistoryTotal` · `incidentHistoryTruncated` · `incidentHistoryAsset` · `incidentHistoryLoaded` · `incidentHistoryLoading` · `incidentHistoryFailed` + **`fetchIncidentHistory(asset)`** |

Thân hàm fetch (cả 3 **giống nhau từng bước** — copy khuôn, đừng sáng tạo):

```ts
if (loaded && cachedAsset === arg) return                     // AC2 — thu/bung lại KHÔNG refetch
if (cachedAsset !== arg) { rows = []; total = 0; truncated = 0; loaded = false }   // đổi thiết bị ⇒ dọn
loading = true; failed = false
try {
  const res = await api(arg)                                  // imm12: res.items ?? []
  const list = res.history ?? []
  rows = list
  total = res.total ?? list.length                            // phòng thủ CR-69 — GIỮ
  truncated = Number(res.truncated) === 1 ? 1 : 0             // bẫy int-vs-bool — GIỮ
  cachedAsset = arg; loaded = true
} catch (e: unknown) { failed = true; _captureError(e) }       // KHÔNG giữ chuỗi lỗi (D-OPH-14)
finally { loading = false }
```

> ⚠️ **Guard cache có thể làm ĐỎ** `stores/assetHistoryTruncation.test.ts` nếu ca nào gọi fetch **2 lần / cùng store / cùng asset** và mong lần 2 vẫn bắn API. Được phép sửa **chính test đó**; **KHÔNG** được nới guard (AC2 chết).

### VIII.13.4 Điều hướng — **0 URL literal** (AC6)

```ts
// api/connections.ts — helper THUẦN mới, đặt cạnh DOCTYPE_LIST_TARGET (chỗ DUY NHẤT biết bảng)
export function listRouteForAsset(doctype: string, assetName: string): string | null {
  const spec = DOCTYPE_LIST_TARGET[doctype]
  if (!spec || !assetName) return null
  // Ta đang đẩy MÃ THIẾT BỊ ⇒ queryKey phải neo về AC Asset, nếu không sẽ lọc NHẦM hồ sơ.
  if (LIST_TARGET_ANCHOR[spec.queryKey] !== 'AC Asset') return null
  return `${spec.path}?${spec.queryKey}=${encodeURIComponent(assetName)}`
}
```

| Nhánh | Dòng → chi tiết | «Xem tất cả» |
|---|---|---|
| pm | `detailRouteForDoctype('PM Work Order', row.pm_work_order)` → `/pm/work-orders/<mã WO>` | `listRouteForAsset('PM Work Order', asset)` → `/pm/work-orders?asset=<mã TS>` |
| cm | `detailRouteForDoctype('Asset Repair', row.name)` → `/cm/work-orders/<name>` | `listRouteForAsset('Asset Repair', asset)` → `/cm/work-orders?asset=<mã TS>` |
| incident | `detailRouteForDoctype('Incident Report', row.name)` → `/incidents/<name>` | `listRouteForAsset('Incident Report', asset)` → `/incidents/list?asset=<mã TS>` |

- **PM dùng `row.pm_work_order`, KHÔNG `row.name`** — `row` là `PM Task Log`, doctype đó **không có màn chi tiết** (0 hit trong `connections.ts`).
- `pm_work_order` rỗng ⇒ `detailRouteForDoctype` trả `null` ⇒ render `op-history-row-static` («Chưa gắn phiếu bảo trì»), **0 `<a>`**.
- Cả 3 màn đích **đã verify** đọc `route.query.asset`: `PMWorkOrderListView.vue:26` · `CMWorkOrderListView.vue:23` · `IncidentListView.vue:41`.

### VIII.13.5 Nội dung dòng + nhãn VI (chép nguyên — `constants/labels.ts` là SSoT)

| Nhánh | Dòng gồm | Nhãn/format |
|---|---|---|
| pm | `formatDate(completion_date)` · link `pm_work_order` · **kết quả** · **trễ** (nếu có) · `summary` (truncate CSS) | `overallResultLabel(overall_result)` (`:702`) → `Đạt`/`Đạt (lỗi nhỏ)`/`Không đạt`; `isCheckOn(is_late)` ⇒ «Trễ {days_late} ngày» |
| cm | `formatDateTime(completion_datetime ?? open_datetime)` · link `name` · **loại** · **Thời gian khắc phục** · **cờ vượt cam kết** | `repairTypeLabel(repair_type)` (`:688`, đã bổ khuyết `'Warranty Repair'`); «Thời gian khắc phục: {mttr_hours} giờ» (verbatim BE, KHÔNG tự tính); `isCheckOn(sla_breached)` ⇒ chip «Vượt cam kết thời gian» |
| incident | `formatDateTime(reported_at)` · link `name` · **mức độ** · **mã lỗi** | `incidentSeverityLabel(severity)` (`:408`) → `Thấp`/`Trung bình`/`Cao`/`Nghiêm trọng`; «Mã lỗi: {fault_code}» chỉ khi `fault_code.trim()` khác rỗng |

**KHÔNG render `pm_type`** — field là **Data tự do** (`pm_task_log.json`) nên giá trị thực có thể ngoài 4 khoá `PM_TYPE_LABEL` (`:705`) ⇒ fallback in EN thô (`Preventive`…), vi phạm AC10/LL-FE-53.

Microcopy đầy đủ (empty / error / see-all / total): **bảng SSoT ở [`ADR §5.3`](./ADR-IMM00-ASSET-OP-HISTORY.md)** — chép nguyên, không tự đặt lại chuỗi.

### VIII.13.6 DoD FE (đo được — đọc baseline TỪ ĐĨA)

- `npx vue-tsc --noEmit` **0 lỗi** (oracle chính của AC11: `history` không còn khai `PMWorkOrder[]`).
- `npx vitest run` **0 ĐỎ**; số file `*.test.ts` **284 → ≥286** (đo lúc chốt spec: `find frontend/src -name '*.test.ts' | wc -l` = **284**) ⇒ chấm **delta**, không chấm số tuyệt đối.
- `grep -rn "'/pm/work-orders'\|'/cm/work-orders'\|'/incidents'" frontend/src/components/asset/AssetOperationalHistory.vue` ⇒ **0 hit**.
- `grep -rn 'as unknown\|as any' frontend/src/components/asset/AssetOperationalHistory.vue` ⇒ **0 hit**.
- `router/connectionsListParity.test.ts` + `connectionsCreateParity.test.ts` + `tabLabelParity` xanh **mà không bị sửa một dòng**.
- ⛔ **KHÔNG** `npm run build` · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate`/`bench restart`.

## VIII.14. AC-CR-105 — «Tạo từ ngữ cảnh cha» HẾT là nút chết: chip cho ô **0 bản ghi** + `create_prefill` thành khoá BẮT BUỘC (spec cho **[FE] Bước-4**)

> Quyết định: [ADR §18](./ADR-IMM00-CONNECTIONS-TREE.md) (D-CR105-2/7/8 · INV-CONN105-1..4) · hợp đồng API: [`05 §III.24.11`](./05_API_Specification.md) · nghiệp vụ: [`02 §IV.42`](./02_Analysis_Design.md) BR-00-CONN-67..76 · test + DoD: [`07 §XXI`](./07_Testing_QA.md).
> **Bối cảnh 1 dòng**: FE đã có SẴN toàn bộ đường tiêu thụ prefill từ 2026-07-28 (`CREATE_PREFILL_QUERY_KEYS` `:402` · `createTarget` `:432` · guard `connectionsCreateParity.test.ts`). Vòng này chỉ (a) siết kiểu, (b) **cho nút một chỗ đứng** vì từ AC-CR-93 ô `total == 0` không còn khối riêng.
> ⛔ **KHÔNG** `npm run build` (= deploy live) · **KHÔNG** chạy suite BE · **KHÔNG** đụng `router/index.ts`, `router/routeAccess.ts`, `DOCTYPE_ROUTE`, `DOCTYPE_LIST_TARGET`, `LIST_TARGET_NO_FILTER`, `connectionsListParity.test.ts`, `connectionsCreateParity.test.ts`.

### VIII.14.1 File đụng — **2 file sản phẩm + 3 file test**

| # | File | Đổi gì |
|---|---|---|
| 1 | `src/api/connections.ts` | `create_prefill` **bỏ dấu `?`** (`:111`) + cập chú thích hợp đồng (9 → **10** khoá, `:36-45`); **thêm** helper thuần `emptyCells(group)` và **viết lại `emptyLabels` trên nền nó** (0 đổi hành vi) |
| 2 | `src/components/common/RelatedRecords.vue` | **thêm** khối `conn-empty-actions` (sibling của `conn-empty-summary`) + hàm `emptyCreateCells(group)`; **không** đổi một dòng nào của khối ô có dữ liệu |
| 3 | `src/api/connectionsLegacyKeysRetired.acr92.test.ts` | tiêu đề "9 bắt buộc + create_prefill" → **10 bắt buộc** (`:80`); tập optional `['create_prefill']` → **`[]`** (`:94-97`) + cập chú thích `:92-93` |
| 4 | `src/components/common/RelatedRecords.test.ts` | +TC render (§XXI); **breakage khai trước: đúng 2 dòng `:772-773`**; **thêm `create_prefill: {}` vào factory `item()` `:66-79`** |
| 5 | `src/api/connections.test.ts` | +TC unit cho `emptyCells` / phân hoạch; thêm `create_prefill: {}` vào factory nếu factory dựng literal `ConnectionItem` |

> **Hệ quả cơ học của việc bỏ `?`**: mọi literal `ConnectionItem` trong test phải có `create_prefill` ⇒ **thiếu là `npx vue-tsc --noEmit` ĐỎ**. Đúng **5** file `.ts/.vue` chạm type này (đo 2026-07-30) — 5 file trong bảng trên, không có file thứ 6.

### VIII.14.2 Hợp đồng type — khoá thứ 10 BẮT BUỘC

```ts
export interface ConnectionItem {
  // … 9 khoá của AC-CR-92, 0 đổi nghĩa …
  /**
   * Giá trị điền sẵn cho màn tạo — `{khoá query: giá trị}` («Tạo từ ngữ cảnh cha»).
   * BẮT BUỘC từ AC-CR-105 (BE đã land): `{}` là **câu trả lời hợp lệ**, không phải thiếu dữ liệu.
   * Khoá là khoá URL mà CHÍNH màn tạo đọc (`asset`), KHÔNG phải Link fieldname (`asset_ref`).
   */
  create_prefill: Record<string, string>
}
```

`createTarget` (`:432-448`) **giữ nguyên từng dòng**, kể cả `item.create_prefill ?? {}`: đó là phòng thủ **hình dạng** cho cửa sổ worker BE chưa reload (khoá vắng mặt ⇒ push trần = hành vi cũ), **không** phải nhánh fallback hợp đồng.

### VIII.14.3 Helper thuần **MỚI** — phân hoạch ô, một chỗ duy nhất

```ts
/** Các ô RỖNG của nhóm — phần bù của `dataCells` trên CÙNG một vị-từ (`hasConnectionRecords`). */
export function emptyCells(group: ConnectionGroup): ConnectionItem[] {
  return (group.items ?? []).filter((item) => !hasConnectionRecords(item))
}

/** Nhãn VI của các ô rỗng — nay derive TỪ `emptyCells` (bỏ bản sao vị-từ). */
export function emptyLabels(group: ConnectionGroup): string[] {
  return emptyCells(group).map(viLabel).filter((label) => label !== '')
}
```

**Vì sao thêm hàm thay vì lọc trong template**: bất biến **INV-CONN105-3** `len(group.items) == len(dataCells) + len(emptyCells)` chỉ có nghĩa khi **cả hai phía** dùng **cùng một** vị-từ `hasConnectionRecords` (đọc `total`, **không** `items.length`). Lọc trong `.vue` là chỗ bản sao vị-từ thứ hai xuất hiện — và đó chính là chỗ hợp đồng bắt đầu lệch ở vòng 2 (`hasRecords` cũ trong component).
`emptyLabels` viết lại là **refactor 0 hành vi**: `TC-FE-CONN-42/43` đang canh nó, phải **xanh không sửa**.

### VIII.14.4 Cây DOM — chip là **SIBLING**, không lồng vào câu văn

```
[data-testid="conn-group"]
├── <h3 data-testid="conn-group-label">        ← v-if dataCells.length (LUẬT §14 GIỮ NGUYÊN — chip KHÔNG làm mọc tiêu đề)
├── <ul>  <li data-testid="conn-item"> …       ← ô CÓ dữ liệu (0 dòng đổi)
├── <p data-testid="conn-empty-summary">       ← «Chưa có: A, B, C» — TEXT TĨNH: 0 <button>, 0 <a>, 0 role="button"
└── <div data-testid="conn-empty-actions">     ← MỚI (v-if emptyCreateCells(group).length)
      └── <button data-testid="conn-create">   ← 0..n chip, ĐÚNG 1 chip / ô rỗng qua đủ 3 gate
```

```ts
/** Ô rỗng có đường tạo THẬT — qua đủ 3 lớp gate (giống hệt nút ở ô có dữ liệu). */
function emptyCreateCells(group: ConnectionGroup): ConnectionItem[] {
  return emptyCells(group).filter((item) => createFor(item) !== null)
}
```

Luật hiển thị của khối mới:

1. **Nhãn ô rỗng VẪN nằm trong câu «Chưa có: …» dù ô đó có chip** (dư thừa CÓ CHỦ ĐÍCH): câu = **kiểm kê**, chip = **hành động**. Tách nhãn khỏi câu khi có chip ⇒ sinh **mẫu câu thứ hai** + làm ĐỎ `TC-FE-CONN-25/27` (∀ ô `total==0` phải được nêu tên) + phá INV-CONN105-3.
2. **Nhãn chip == `createLabel(item)`** — **cùng một chuỗi** với nút ở ô có dữ liệu («Tạo phiếu sửa chữa», «Báo sự cố»). **KHÔNG** thêm ký tự `+`/`＋` vào **text**: nhãn nhìn thấy phải khớp `aria-label` (WCAG 2.5.3 label-in-name) và một affordance chỉ được có **một** nhãn. Muốn nó "trông như chip" thì dùng **style** (viền + bo tròn), không dùng chữ.
3. **`aria-label` = `` `${createLabel(item)} cho hồ sơ này` ``** (khuôn đã có ở nút ô có dữ liệu — giữ y nguyên để screen-reader không nghe hai giọng).
4. **Bấm chip ⇒ `openCreate(item)`** — **dùng lại** hàm sẵn có (`:152-158`), **không** viết đường điều hướng thứ hai: `router.push({ path, query })` khi có prefill, `router.push({ path })` khi `create_prefill == {}` (URL **không** mọc dấu `?`).
5. **`data-testid="conn-create"` dùng lại** (không đẻ testid thứ hai): một affordance = một testid, nếu không recipe QA + guard phải nhớ hai đường và một đường có thể chết âm thầm.
6. Nhóm **0 ô rỗng** ⇒ **không** render `conn-empty-actions` (không khung trống). Nhóm có ô rỗng nhưng **0 ô** qua gate ⇒ cũng **không** render khối.

### VIII.14.5 Ba lớp gate — **giữ nguyên thứ tự, giữ nguyên fail-CLOSED**

| Lớp | Hàm | Sai ⇒ | Vì sao không bỏ được |
|---|---|---|---|
| 1 | `createTarget(item)` (`api/connections.ts:432`) | `null` ⇒ **ẩn chip** | Hợp đồng BE: `can_create !== true` **hoặc** hint rỗng ⇒ không có đường |
| 2 | `routeExists(target.path)` (`router.resolve`) | ẩn chip | BE biết **quyền**, không biết **màn nào đã có** ⇒ tránh 404 |
| 3 | `canAccessCreateRoute(path, can)` (`routeAccess.ts:160`) | ẩn chip (**fail-CLOSED** với route chưa khai) | Bấm xong bị route-guard đá ra `/unauthorized` là "nút chết" tệ nhất — người dùng **đã tin** là làm được |

**Khác `canAccessDrill` (fail-OPEN) một cách có chủ đích**: drill là đường **XEM**, chip là lời mời **GHI**.

### VIII.14.6 Breakage khai báo TRƯỚC — **đúng 2 dòng** (QA không chấm là "nới guard")

`RelatedRecords.test.ts:772-773` (trong `TC-FE-CONN-26`) hiện khoá mệnh đề **đã bị supersede**:

```ts
// Không còn ô rỗng ⇒ không còn chỗ treo nút tạo (D-CR93-4, supersede INV-CONNFE4-5).
expect(w.findAll('[data-testid="conn-create"]')).toHaveLength(0)
```

Thay bằng assert **dương** (chip phải có, và phải nằm đúng chỗ):

```ts
// AC-CR-105 (ADR §18 D-CR105-7): ô rỗng qua đủ 3 gate có chip — trong khối SIBLING, KHÔNG trong câu.
const actions = w.findAll('[data-testid="conn-empty-actions"]')
expect(actions.length).toBeGreaterThan(0)
expect(w.findAll('[data-testid="conn-create"]').length).toBe(
  actions.reduce((n, a) => n + a.findAll('[data-testid="conn-create"]').length, 0),
)  // ⇒ 0 chip nào nằm ngoài khối actions
```

**7 assert in-summary (`:764-770`) giữ nguyên từng ký tự**, và hàng `TC-FE-CONN-26` trong [`07 §XVIII.8.2`](./07_Testing_QA.md) **không sửa một chữ** — phạm vi tài liệu của TC đó là *"trong mỗi `conn-empty-summary`"*, mà chip **không** nằm trong đó.
**Cấm chạm**: `TC-FE-CONN-24/25/27/28/29/30`, `connectionsListParity.test.ts`, `connectionsCreateParity.test.ts`, `RelatedRecords.vue` khối ô có dữ liệu.

### VIII.14.7 DoD FE (đo được — đọc baseline TỪ ĐĨA)

- `cd frontend && npx vitest run` **0 ĐỎ** (trừ `personaDashboards.test.ts` — **1 TC ĐỎ PRE-EXISTING**, đã chứng minh ở vòng 1 run-5, **không** tính vào DoD) — báo cáo **trước → sau**; số file `*.test.ts` **≥ 286** (`find frontend/src -name '*.test.ts' | wc -l` = **286** đo TỪ ĐĨA 2026-07-30 **sau vòng 1 run-5** — con số **284** trong `07 §XX.3` là snapshot TRƯỚC vòng đó ⇒ chấm **delta**, đừng chấm số tuyệt đối).
- `npx vue-tsc --noEmit` **0 lỗi** — đây là cổng phát hiện thiếu `create_prefill` trong fixture.
- Mutation-check (guard phải sống, không phải template): (a) bỏ `v-if` của `conn-empty-actions` ⇒ TC chip ĐỎ; (b) nhúng chip **vào trong** `<p conn-empty-summary>` ⇒ `TC-FE-CONN-26` ĐỎ; (c) đổi `emptyCells` sang lọc theo `items.length` ⇒ TC phân hoạch/`TC-FE-CONN-27` ĐỎ; (d) bỏ lớp gate 3 ⇒ TC "thiếu cap ⇒ 0 chip" ĐỎ; (e) trả lại `create_prefill?` ⇒ guard `connectionsLegacyKeysRetired.acr92` ĐỎ. **5 đột biến ⇒ 5 lần đỏ.**
- `git diff --name-only` phía FE: **đúng 5** file ở §VIII.14.1 (2 sản phẩm + 3 test). Phía `.py` **0 path** do FE gây ra.
- 3 counter guard **delta 0** (1024 / 1167 / 1193) · ⛔ **KHÔNG** `npm run build` · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate`/`bench restart`.

---

## VIII.15. AC-CR-115 — **dải cắt render THẬT** cho 3 nhánh vận hành + **BẢN GHI trước Ô CHỨC NĂNG** trong tab «Bản ghi liên quan» (spec cho **[FE] Bước-4**)

> Quyết định + lý do: [`ADR-IMM00-ASSET-OP-HISTORY §10`](./ADR-IMM00-ASSET-OP-HISTORY.md) (`D-OPH-17..20`, supersede `D-OPH-12` + nửa sau `D-OPH-1`). Nghiệp vụ: [`02 §IV.43`](./02_Analysis_Design.md) `FR-00-OPH-02` / `BR-00-OPH-19..30`. Hợp đồng đọc: [`05 §III.26.6`](./05_API_Specification.md). Test + DoD: [`07 §XXII`](./07_Testing_QA.md).
> **Bối cảnh 1 dòng**: tab + khối + store + BE `total`/`truncated` **ĐÃ XONG** từ `AC-CR-102` (đo từ đĩa 2026-07-30). Vòng này làm **đúng 4 việc**: (1) dải cắt, (2) đảo thứ tự 2 khối, (3) 2 tiêu đề khối, (4) đóng cite-drift.
> ⛔ **KHÔNG** sửa `stores/imm08|09|12.ts` (0 dòng) · **KHÔNG** sửa `RelatedRecords.vue` · **KHÔNG** đụng `.py` prod / OAS / `DOCTYPE_LIST_TARGET` / `LIST_TARGET_ANCHOR` · **KHÔNG** `npm run build`.

### VIII.15.1 File đụng — **2 file sản phẩm + 2–3 file test** (path thứ 4 phía FE = scope creep)

| # | File | Đổi gì |
|---|---|---|
| 1 | `src/components/asset/AssetOperationalHistory.vue` | (a) computed `shown`/`totalDisplay`/`hidden` per-section; (b) render `[op-history-truncation]` **trong** section, **trước** `[op-history-see-all]`; (c) **thêm testid** `related-block-heading` vào `<h3>` **đã có** (`:309-311`, **giữ nguyên chuỗi** «Dữ liệu vận hành của thiết bị»); (d) **viết lại comment `:38-39`** («vòng sau» → mô tả hành vi hiện tại) ⇒ `grep -n 'vòng sau' <file>` = **0 hit** |
| 2 | `src/views/asset/AssetDetailView.vue` | Trong `[tab-panel-related]` (`:1045-1052`): **đảo thứ tự** — `<AssetOperationalHistory>` **trước**; `<RelatedRecords>` bọc trong `<div>` có `<h3 data-testid="related-block-heading">Liên kết nhanh theo chức năng</h3>`; cập nhật comment `:1047-1050` cho khớp thứ tự mới |
| T1 | `src/components/asset/assetOperationalHistory.test.ts` | **Sửa `TC-FE-OPH-09` `:298-307`** (`not.toContain('Đang xem')` ⇄ AC1 — `D-OPH-20` **cho phép + bắt buộc**) + **thêm** `TC-FE-OPH-14..18` (§XXII) |
| T2 | `src/views/asset/assetDetailRelatedTab.test.ts` | **Thêm** TC thứ tự DOM + đếm `related-block-heading` (`TC-FE-OPH-19..20`); sửa TC cũ **chỉ nếu** thật sự đỏ |
| T3 | `assetcore/tests/test_asset_operational_history_contract.py` | **Thêm** `INV-OPH-27..30` vào file **đã có** (BE, **chỉ đọc**, 0 dòng prod) |

`stores/assetHistoryTruncation.test.ts` **phải xanh KHÔNG sửa** (khác vòng `AC-CR-102`) — nó đỏ ⇒ có người sửa store ngoài biên.

### VIII.15.2 Logic dải cắt — **1 computed, dùng cho CẢ badge và dải**

```ts
// trong computed `sections` đã có (:296-304) — thêm 3 trường, KHÔNG thêm state
const rows  = ui[spec.key].loaded ? spec.rows() : []
const shown = rows.length                          // M — phần ĐANG XEM
const totalDisplay = Math.max(spec.total(), shown)  // N — max() chống ca BE trả total < rows
const hidden = totalDisplay - shown                 // N − M
```

| Nơi dùng | Giá trị |
|---|---|
| `[op-history-count]` (badge tiêu đề) | **`totalDisplay`** — cùng một số với dải (một số, một nguồn; không để badge nói 34 mà dải nói 30) |
| `[op-history-truncation]` | `v-if="s.ui.loaded && !s.ui.error && s.hidden > 0"` · text `Đang xem {{ s.shown }}/{{ s.totalDisplay }} — còn {{ s.hidden }} chưa hiển thị` |
| `[op-history-empty]` | giữ nguyên điều kiện `totalDisplay === 0` (**không** đổi — `TC-FE-OPH-12` phải xanh) |

**Cấm tuyệt đối** (chấm bằng grep, `BR-00-OPH-20`):

```bash
grep -n 'Truncated' frontend/src/components/asset/AssetOperationalHistory.vue   # ⇒ 0 hit
grep -n 'Tải thêm'  frontend/src/components/asset/AssetOperationalHistory.vue   # ⇒ 0 hit
```

Cờ `truncated` **vẫn** ở store (hợp đồng mobile + `assetHistoryTruncation.test.ts`) nhưng **không** là đầu vào của bất kỳ điều kiện render nào — lý do đầy đủ ở [`05 §III.26.6(b)`](./05_API_Specification.md): cờ tính từ **`limit`**, thứ người dùng thấy là **`rows.length`**.

### VIII.15.3 Markup dải (chép khuôn — đừng sáng tạo class mới)

```vue
<!-- SAU </ul> dòng, TRƯỚC «Xem tất cả». Dải nằm TRONG section ⇒ luôn nói về ĐÚNG nhánh này. -->
<p
  v-if="s.hidden > 0"
  data-testid="op-history-truncation"
  :data-branch="s.spec.key"
  class="mt-2 text-xs text-slate-500 dark:text-slate-400"
>
  Đang xem {{ s.shown }}/{{ s.totalDisplay }} — còn {{ s.hidden }} chưa hiển thị
</p>
```

- Dấu `—` là **em dash** (khớp chuỗi trong test — copy nguyên, đừng gõ lại thành `-`).
- **KHÔNG** thêm nút nào cạnh dải: lối ra là `[op-history-see-all]` **đã có** ngay dưới (`BR-00-OPH-24`).

### VIII.15.4 Thứ tự khối + 2 tiêu đề (`AssetDetailView.vue`)

```vue
<div v-if="activeTab === 'related'" data-testid="tab-panel-related">
  <!-- KHỐI 1 — BẢN GHI THẬT của chính thiết bị này. Đứng TRƯỚC vì đây là câu người
       dùng hỏi trước («máy này bảo trì ra sao / đã sửa mấy lần / từng gây sự cố gì»).
       Heading của khối này nằm TRONG component (đã có). -->
  <AssetOperationalHistory :asset="store.currentAsset.name" />

  <!-- KHỐI 2 — LỐI ĐI tới chức năng (ô đếm + «Xem tất cả» toàn hệ thống). Heading đặt
       Ở ĐÂY, KHÔNG trong RelatedRecords.vue: component đó dùng chung 5 màn Detail ⇒
       tiêu đề là thuộc tính của CHỖ ĐẶT, không phải của component. -->
  <div class="mt-6">
    <h3
      data-testid="related-block-heading"
      class="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400"
    >
      Liên kết nhanh theo chức năng
    </h3>
    <RelatedRecords doctype="AC Asset" :name="store.currentAsset.name" />
  </div>
</div>
```

- Khối 1 hiện có `class="mt-6 border-t … pt-4"` (`AssetOperationalHistory.vue:308`) — khi lên đầu panel, đường kẻ trên **không còn phân tách gì**; [FE] được phép dời `border-t`/`mt-6` sang khối 2 để đường kẻ nằm **giữa** 2 khối. Đây là thay đổi **class thuần**, không đổi testid/chuỗi/điều kiện.
- **KHÔNG** đổi chuỗi heading khối 1 («Dữ liệu vận hành của thiết bị») — chỉ **thêm** `data-testid`.

### VIII.15.5 DoD FE (đo được — baseline đọc TỪ ĐĨA, chấm DELTA)

- `npx vitest run` **0 ĐỎ** (trừ `personaDashboards.test.ts` — 1 TC ĐỎ **PRE-EXISTING**, không tính vào DoD, **không** ai sửa cho xanh). **Delta ≥ +8 test case mới**; `find frontend/src -name '*.test.ts' | wc -l` = **287** đo TỪ ĐĨA 2026-07-30 (số **284**/**286** trong `07 §XX.3` và `§VIII.14` là snapshot cũ ⇒ **đo lại, chấm delta**).
- `npx vue-tsc --noEmit` **0 lỗi**.
- `grep -n 'Truncated\|Tải thêm\|vòng sau' frontend/src/components/asset/AssetOperationalHistory.vue` ⇒ **0 hit** (cả 3 chuỗi).
- `grep -n "'/pm/work-orders'\|'/cm/work-orders'\|'/incidents'" frontend/src/components/asset/AssetOperationalHistory.vue` ⇒ **0 hit** (giữ `INV-OPH-10`).
- `git diff --name-only` phía FE: **đúng 2 file sản phẩm** + **≤3 file test** (§VIII.15.1). Phía `.py`: **0 path** trong `assetcore/api/` và `assetcore/services/` (chỉ `assetcore/tests/`).
- Mutation-check (guard phải sống, không phải template): (a) đổi điều kiện dải sang `s.truncated === 1` ⇒ TC AC2 **và** AC3 ĐỎ; (b) đưa dải ra ngoài `[op-history-section]` ⇒ TC "dải trong đúng nhánh" ĐỎ; (c) đảo lại thứ tự 2 khối ⇒ TC thứ tự DOM ĐỎ; (d) xoá 1 heading ⇒ TC "đúng 2 `related-block-heading`" ĐỎ; (e) thêm nút «Tải thêm» ⇒ TC dead-control ĐỎ. **5 đột biến ⇒ 5 lần đỏ.**
- 3 counter guard **delta 0** (1024 / 1167 / 1193 — đọc lại từ đĩa) · ⛔ **KHÔNG** `npm run build` · **KHÔNG** `git commit/push` · **KHÔNG** `bench migrate`/`bench restart`.

---

## VIII.16. `AC-CR-119` — **trạng thái KHOÁ** cho 3 nhánh vận hành: hỏi quyền TRƯỚC khi gọi, 0 request vô vọng, 0 nút chết

> Nguồn quyết định: [`ADR-IMM00-ASSET-OP-HISTORY §11`](./ADR-IMM00-ASSET-OP-HISTORY.md) (`D-OPH-21..27`) · FR/BR: [`02 §IV.44`](./02_Analysis_Design.md) (`FR-00-OPH-03`, `BR-00-OPH-31..42`) · hợp đồng quyền BE: [`05 §III.26.7`](./05_API_Specification.md) · invariant + TC: [`07 §XXIII`](./07_Testing_QA.md).

### VIII.16.1 File đụng — **5 file sản phẩm + 1–2 file test** (path thứ 6 phía FE = scope creep)

| # | File | Sửa gì |
|---|---|---|
| 1 | `frontend/src/stores/auth.ts` | (a) **thêm** `capState(cap)` tam phân + export trong `return {…}`; (b) **bump** `CAP_SET_VERSION` (`:51`) sang **giá trị ĐO** từ BE. `can()` **KHÔNG đổi 1 ký tự**. |
| 2 | `frontend/src/stores/imm08.ts` | +`pmHistoryForbidden` (ref + reset + set trong `catch` + export) |
| 3 | `frontend/src/stores/imm09.ts` | +`repairHistoryForbidden` (idem) |
| 4 | `frontend/src/stores/imm12.ts` | +`incidentHistoryForbidden` (idem) + `import { isForbiddenError } from '@/api/errors'` (store này chưa có `lastApiError`) |
| 5 | `frontend/src/components/asset/AssetOperationalHistory.vue` | +`cap`/`forbiddenOf` trong `SectionSpec`; +`locked` trong `SectionUi`; `toggle()` chặn khi `denied`; `load()` phân loại 403; +khối `[op-history-locked]`; +attr `data-locked` |
| T1 | `frontend/src/components/asset/assetOperationalHistory.test.ts` | sửa 1 fixture gây nhầm (§VIII.16.5) + thêm TC-FE-OPH-22..29 |
| T2 | `frontend/src/stores/auth.capabilities.test.ts` | *(nếu thêm TC cho `capState`)* |

**KHÔNG** đụng: `RelatedRecords.vue` · `AssetDetailView.vue` · `api/imm08|09|12.ts` · `api/connections.ts` · `api/errors.ts` (chỉ **dùng** `isForbiddenError`, không sửa) · `constants/labels.ts` · `router/*` · `constants/sidebarNav.ts`.

### VIII.16.2 `auth.capState()` — tam phân, **SSoT của quyết định khoá**

```ts
export type CapState = 'granted' | 'denied' | 'unknown'

/**
 * Trạng thái BA GIÁ TRỊ của một capability. `can()` (nhị phân) KHÔNG phân biệt được
 * «server nói KHÔNG» với «server CHƯA BIẾT cap này» — hai thứ đòi hai hành vi UI khác
 * nhau (khoá vs cứ gọi rồi tự chữa). BE trả `caps = {c: can(c) for c in CAPABILITY_MAP}`
 * ⇒ MỌI cap của bản build có mặt tường minh true/false ⇒ **khoá vắng ≠ false**: nó nghĩa
 * là worker gunicorn `--preload` cũ / cache redis `ac_caps::*` chưa invalidate / caps đang
 * refetch sau khi `isCapCacheStale` drop persisted-caps.
 */
const capState = (cap: string): CapState =>
  isFrappeAdmin.value                     ? 'granted'
  : !(cap in capabilities.value)           ? 'unknown'
  : capabilities.value[cap] === true       ? 'granted'
  :                                         'denied'
```

Invariant khoá quan hệ với `can()` (`INV-OPH-42a/42b`): `can(cap) === (capState(cap) === 'granted')` cho **mọi** cap, **mọi** trạng thái store (kể cả `capabilities = {}`).

### VIII.16.3 Store — cờ 403 **RIÊNG mỗi nhánh** (khuôn chung 3 file)

```ts
// stores/imm08.ts (đối xứng imm09 / imm12)
const pmHistoryForbidden = ref(false)

async function fetchPMHistory(assetRef: string, limit = 10): Promise<boolean> {
  pmHistoryError.value = null
  pmHistoryForbidden.value = false          // reset MỖI lần gọi
  try { /* … không đổi … */ return true }
  catch (e: unknown) {
    _captureError(e)
    // Phân loại theo MÃ, KHÔNG theo chuỗi: message do registry MSG sinh và sẽ đổi.
    pmHistoryForbidden.value = isForbiddenError(e)
    pmHistoryError.value = lastApiError.value?.message ?? …   // giữ nguyên
    return false
  }
}
// export: pmHistoryForbidden
```

**Vì sao ref RIÊNG, không đọc `lastApiError`:** `lastApiError` là của **cả store** (mọi action ghi vào — `stores/imm08.ts:50-54`) ⇒ action song song ghi đè ⇒ nhánh này đọc mã lỗi của việc khác. Cùng lý do `AC-CR-102` đã tách `pmHistoryError` khỏi `error`. `stores/imm12.ts` **giữ** cách ghi `incidentHistoryError` hiện có (`:142`), chỉ **thêm** 1 dòng cờ + 1 import.

### VIII.16.4 Component — 5 trạng thái, `locked` **đứng trước** `error`

```ts
type SectionKey = 'pm' | 'cm' | 'incident'
interface SectionSpec {
  /* … giữ nguyên … */
  /** Cap SOUND của nhánh — CHÉP từ BE SSoT `connection_meta.OP_HISTORY_BRANCH_GATE`.
   *  FE KHÔNG giữ bản đồ DocType thứ hai (BR-00-OPH-33). */
  cap: string
  /** True ⟺ lần nạp gần nhất bị BE trả 403-in-envelope (caps stale → self-heal). */
  forbiddenOf: () => boolean
}
interface SectionUi { open: boolean; loading: boolean; loaded: boolean; error: string | null; locked: boolean }
```

Ba giá trị `cap` (đúng 3 chuỗi, không hơn): `pm` → `'pm.read_history'` · `cm` → `'repair.read'` · `incident` → `'corrective.read'`.

```ts
const auth = useAuthStore()

/** Server nói KHÔNG (khoá có mặt, false) ⇒ khoá TRƯỚC khi gọi. `unknown` KHÔNG khoá. */
function deniedByCap(spec: SectionSpec): boolean {
  return auth.capState(spec.cap) === 'denied'
}

async function toggle(spec: SectionSpec): Promise<void> {
  const s = ui[spec.key]
  s.open = !s.open
  if (!s.open) return
  if (deniedByCap(spec)) { s.locked = true; return }   // ⟵ 0 request (BR-00-OPH-38)
  if (s.loaded) return
  await load(spec)
}

async function load(spec: SectionSpec): Promise<void> {
  const s = ui[spec.key]
  if (deniedByCap(spec)) { s.locked = true; return }    // «Thử lại» không tồn tại ở khối locked,
  s.loading = true; s.error = null; s.locked = false    //   nhưng chặn ở đây là fail-safe.
  const ok = await spec.fetch()
  s.loading = false
  if (ok) { s.loaded = true; return }
  if (spec.forbiddenOf()) {
    // Caps nói ĐƯỢC mà BE nói 403 ⇒ CÙNG khối locked, KHÔNG phải error (D-OPH-25).
    s.locked = true; s.error = null; return
  }
  s.error = spec.errorOf() ?? FALLBACK_ERROR            // lỗi TẠM: giữ nguyên đường hồi phục
}
```

`sections` computed thêm `locked: ui[key].locked` (và `rows` vẫn chỉ tính khi `loaded`).

**Markup — chèn khối `locked` GIỮA `loading` và `error`** (thứ tự `v-if` là hợp đồng, `BR-00-OPH-35`):

```html
<p v-if="s.ui.loading" …>Đang tải…</p>

<div v-else-if="s.ui.locked" data-testid="op-history-locked" :data-branch="s.spec.key" class="py-2">
  <p class="text-sm text-slate-600 dark:text-slate-300">{{ s.spec.lockedVI }}</p>
  <p class="mt-1 text-xs text-slate-500 dark:text-slate-400">
    Liên hệ quản trị hệ thống nếu cần cấp thêm quyền.
  </p>
</div>

<div v-else-if="s.ui.error" data-testid="op-history-error" …>… + [op-history-retry] …</div>
<template v-else>… empty / rows / truncation / see-all (KHÔNG ĐỔI) …</template>
```

`lockedVI` per-nhánh (SSoT, chép nguyên — [ADR §11.5](./ADR-IMM00-ASSET-OP-HISTORY.md)):

| Nhánh | `lockedVI` |
|---|---|
| pm | `Bạn chưa được cấp quyền xem kết quả bảo trì của thiết bị này.` |
| cm | `Bạn chưa được cấp quyền xem lần sửa chữa của thiết bị này.` |
| incident | `Bạn chưa được cấp quyền xem sự cố của thiết bị này.` |

Trên `[op-history-toggle]` thêm **`:data-locked="s.ui.locked ? '1' : undefined"`** — nút **vẫn enabled** (`disabled` sẽ làm câu giải thích không đọc được bằng bàn phím ⇒ nằm ở «Ask first»). Badge `[op-history-count]` **giữ nguyên** điều kiện `v-if="s.ui.loaded"` ⇒ khoá ⇒ **0** badge (không cần sửa gì).

**Tone màu:** khối `locked` dùng **slate** (trung tính), **KHÔNG** `rose` — 403 không phải sự cố; đây là nửa hiển thị của `BR-00-OPH-41`.

### VIII.16.5 Test cũ gây NHẦM — sửa trong CÙNG vòng (không phải «test cũ chuyển đỏ»)

`frontend/src/components/asset/assetOperationalHistory.test.ts:385-396` (`TC-FE-OPH-11`) dựng fixture `mockRejectedValue(new Error('Bạn không có quyền đọc phiếu bảo trì.'))` rồi assert `[op-history-error]` chứa `'không có quyền'` + có `[op-history-retry]`.

Test này **vẫn XANH** sau vòng này (`new Error(...)` trần ⇒ `isForbiddenError` = `false` ⇒ đi nhánh `error`, đúng `BR-00-OPH-42`) — **nhưng nó dạy sai**: đọc vào tưởng «403 ⇒ error + retry», đúng điều `AC-CR-119` supersede.

**Quyết định:** [FE] **bắt buộc** sửa **đúng** fixture + assert đó trong cùng vòng — đổi message sang trung tính (vd `'Không tải được dữ liệu'`), đổi assert `.toContain('không có quyền')` theo, và đổi tên `it(...)` thành «**lỗi TẠM** (mạng/500) ⇒ …». Rồi **thêm** TC 403 THẬT dùng `new ApiError('…', { code: ErrorCode.FORBIDDEN, httpStatus: 403 })`. **Cấm** cách khác: không `skip`, không giữ fixture cũ rồi thêm comment.

### VIII.16.6 DoD FE (đo được — baseline đọc TỪ ĐĨA, chấm DELTA)

1. `npx vitest run` **XANH toàn bộ** (đọc **delta** so với baseline đầu vòng — số file test hiện tại đọc bằng `find frontend/src -name '*.test.ts' | wc -l`, **KHÔNG** tin số trong prompt/STATE).
2. `npx vue-tsc --noEmit` ⇒ **0 lỗi** (`CapState` export đúng, `SectionSpec` không `any`).
3. `grep -n "'403'\|FORBIDDEN\|AUTH-403" frontend/src/components/asset/AssetOperationalHistory.vue` ⇒ **0 hit** (mã lỗi không được rò vào component; phân loại nằm ở store qua `isForbiddenError`).
4. `grep -c "data-testid=\"op-history-retry\"" AssetOperationalHistory.vue` ⇒ **1** (đúng một chỗ, trong khối `error`).
5. `grep -n "as any\|as unknown" AssetOperationalHistory.vue` ⇒ **0 hit** (giữ `D-TL-1`).
6. `frontend/src/stores/auth.ts` `CAP_SET_VERSION` **khớp byte** giá trị BE đo được (`INV-OPH-42c`).
7. **KHÔNG** `npm run build` (`emptyOutDir` = deploy live — LL-DEPLOY-09), **KHÔNG** commit/push (HARD-STOP USER).

---

## VIII.17. AC-UX-062/063 — lỗi CHẶN hiện **INLINE trong hộp thoại** + làm sạch câu lỗi tại `axios` (spec cho **[FE] Bước-4**)

> **Spec đầy đủ (hợp đồng, delta từng dòng, bảng test, ADR-UX-13/14/15):** [`docs/ui-ux/05_MODAL_INLINE_ERROR.md`](../ui-ux/05_MODAL_INLINE_ERROR.md).
> Mục này là bản rút gọn cấp module — hai SSoT bị chạm đều thuộc IMM-00, **19** file `.vue` của IMM-01/03/05/07/10/11/12/16 thừa hưởng.

### VIII.17.1 Hiện trạng (đo từ đĩa 2026-08-03 — mẫu số chấm DELTA)

| Số đo | Giá trị |
|---|---|
| File `.vue` tiêu thụ `BaseModal` | **19** |
| Trong đó **0** vùng lỗi inline (0 `role="alert"` **và** 0 `data-testid="modal-error"`) | **15** |
| `data-testid="modal-error"` toàn FE | **0** |
| `grep -c setTimeout frontend/src/components/common/BaseModal.vue` | **0** (phải giữ **0**) |
| Kênh báo lỗi hiện hành | toast tự tắt sau **4000 ms** — `composables/useToast.ts:33` → `:45` |
| Cửa trả chữ thô của máy chủ | `api/axios.ts:182` (`handle400`) · `:277` (`makeBusinessRuleError` fallback, ném ở `:310`) — **cả hai** qua `parseServerMessages` `:136-146` |

### VIII.17.2 Business rules

| Mã | Luật |
|---|---|
| **BR-00-MODERR-01** | Lỗi làm **thất bại thao tác** đang thực hiện trong hộp thoại phải hiện **trong chính hộp thoại đó**: `data-testid="modal-error"` + `role="alert"` + `aria-live="assertive"`, đặt ở **đầu** `data-testid="modal-body"`, **không hẹn giờ tự tắt**, và hộp thoại **KHÔNG đóng**. Toast chỉ cho thông báo **không chặn**. |
| **BR-00-MODERR-02** | Một lỗi ⇒ **đúng một** kênh hiển thị và **đúng một** hộp thoại trên màn: `api.run(..., { silentError: true })` (hoặc gỡ `toast.*`/`notify.fromError` ở nhánh lỗi khi không dùng `useApi`) để `useNotify.fromError` không mở `useModal.alert` chồng lên (`useNotify.ts:65-73`, `:93-101`). Đo: `findAll('[data-testid="modal-card"]').length === 1`. |
| **BR-00-MODERR-03** | Vùng lỗi không tự tắt ⇒ phải xoá tường minh khi **mở lại**, **thử lại**, **đóng**. Nhánh lỗi **tuyệt đối không** set `show*Modal = false`. |
| **BR-00-MODERR-04** | Mọi chuỗi lỗi của máy chủ đi ra giao diện phải qua **một cửa** `sanitizeBusinessMessage` (bọc `parseServerMessages`). Khớp dấu hiệu kỹ thuật (traceback · `File "` · `line N, in ` · `<class '` · `cannot import name` · cặp từ khoá SQL · `tab<ChữHoa>` · `pymysql`/`OperationalError`/`ProgrammingError`/`IntegrityError` · `frappe.exceptions` · đuôi `.py` · thẻ `<…>` còn sót) ⇒ thay bằng **đúng một** câu VI trung tính: «Không thực hiện được thao tác do quy tắc nghiệp vụ. Vui lòng kiểm tra lại dữ liệu hoặc liên hệ quản trị hệ thống.» Câu VI sạch đi qua **nguyên văn**. |
| **BR-00-MODERR-05** | Chuỗi thô chỉ được ghi `console.debug` bọc `if (import.meta.env.DEV)`. DEV=false ⇒ không log **và** chuỗi thô không xuất hiện trong `ApiError.message`. Nhánh có `message_code` (`axios.ts:262-276`, đã render từ registry VI) **không** đi qua sanitizer. |

### VIII.17.3 Delta hợp đồng (CHỈ THÊM — bất biến 0-churn)

- `components/common/BaseModal.vue`: thêm prop tuỳ chọn `error?: string \| null` + `errorTitle?: string`; render `<ModalInlineError v-if="error" …>` ở đầu `modal-body`. **Giữ tuyệt đối** prop `title`/`size`/`danger` · emit `close` · testid `modal-card`/`modal-close`/`modal-body`/`modal-footer` · **toàn bộ chuỗi class**.
- `components/common/ModalInlineError.vue` (**MỚI**, tier-1 thuần trình bày) — nguồn DUY NHẤT của markup vùng lỗi; overlay **lai** (chưa được phép di trú sang `BaseModal`) tiêu thụ trực tiếp component này thay vì copy markup (ADR-UX-14).
- `api/axios.ts`: thêm `export function sanitizeBusinessMessage(raw: string): string` + bọc `parseServerMessages`.

### VIII.17.4 Boundaries

- **Always**: lỗi chặn → inline trong hộp thoại đang mở · một lỗi một kênh · xoá lỗi cũ khi mở/thử lại · làm sạch tại một cửa.
- **Ask first**: đổi bất kỳ prop/emit/testid/class **đã có** của `BaseModal` · di trú overlay tự vẽ sang `BaseModal` (**AC-UX-055/056**, không thuộc vòng này) · mở rộng bộ dấu hiệu kỹ thuật.
- **Never**: `setTimeout`/tự-ẩn cho vùng lỗi · `show*Modal = false` trong `catch` · toast **song song** với vùng inline · hộp thoại thứ hai chồng lên · echo traceback/SQL/`.py` ra giao diện · sửa 4 tệp test đã có (`BaseModalDialog` · `BaseModalA11y` · `BaseModalResponsive` · `modalOverlayHygiene`) cho vừa mã.

### VIII.17.5 DoD FE (đo được — baseline đọc TỪ ĐĨA, chấm DELTA)

1. `grep -c setTimeout frontend/src/components/common/BaseModal.vue` ⇒ **0**.
2. Bất biến 0-churn: `md5sum` 4 tệp test ở Boundaries **khớp 4/4** giá trị chốt ở [`05 §2.3`](../ui-ux/05_MODAL_INLINE_ERROR.md) và cả 4 **XANH**. **KHÔNG** dùng `git diff --stat` (3/4 tệp untracked ⇒ luôn rỗng = xanh giả).
3. Lô 1 = **5 file / 8 hộp thoại** (danh sách đóng băng ở `05 §5`): mỗi hộp thoại có test render «thất bại ⇒ còn mở + có `modal-error` + đúng 1 `modal-card`».
4. Guard CHỈ-GIẢM `modalInlineErrorAdoption.test.ts` (MỚI): tập file tiêu thụ `BaseModal` **thiếu** vùng lỗi inline là **tập con** của allowlist đóng băng **15** và kích thước **== 10** sau lô 1 (`05 §6`).
5. `sanitizeBusinessMessage` có test riêng phủ **14 ca** ở `05 §7.5` (gồm 2 ca khoá `import.meta.env.DEV` hai chiều và 1 ca `message_code` giữ nguyên văn).
6. `npx vitest run` **0 ĐỎ**; số file test ≥ **335** + số tệp test mới (đo lại từ đĩa: `find frontend/src -name '*.test.ts' | wc -l`).
7. 4 guard parity (`uiAuditDocParity` · `uiFixPlanParity` · `uiListShellLot1Parity` · `uiDetailShellLot1Parity`) **XANH**.
8. `npx vue-tsc --noEmit` ⇒ **0 lỗi**. **KHÔNG** `npm run build` (`emptyOutDir` = deploy live — LL-DEPLOY-09), **KHÔNG** commit/push (HARD-STOP USER), `git status -- '*.py'` ⇒ **rỗng**.

### VIII.17.6 Năm đính chính của [BA] so với đề mục đóng băng (chấm theo bản này)

| # | Đĩa nói | Quyết định |
|---|---|---|
| SC-1 | `CalibrationScheduleListView.vue:441` và `ReferenceDataView.vue:500` là **overlay tự vẽ**, `save()` **không** dùng `useApi` | Giữ trong lô 1 nhưng đi **đường B** (dùng `ModalInlineError` + gỡ kênh toast), **không** di trú overlay |
| SC-2 | `UserProfileFormView.vue` không có hộp thoại «lưu»; hộp thoại chặn thật là «Từ chối tài khoản» (`:632`), lỗi ghi vào banner **trang** `:231` nằm dưới lớp phủ | Đổi mục tiêu sang `confirmReject` `:217`; lô 1 vẫn **5 file / 8 hộp thoại** |
| SC-3 | Với thiết kế SSoT, file đường A chỉ chứa `:error="…"` ⇒ phép đo `grep -c 'modal-error'` **luôn = 0** | Phép đo chuẩn = vị ngữ 3 dạng ở `05 §6.1` do guard thực thi + test render |
| SC-4 | Câu VI hợp lệ có thể chứa chữ «update»; BE có dùng `<b>`/`<br>` khi định dạng | SQL dò theo **cặp** từ khoá; thẻ trình bày lành tính bị **gỡ** (giữ chữ), chỉ thẻ **còn sót** mới là dấu hiệu |
| SC-5 | 3/4 tệp test «0-churn» là **untracked** ⇒ `git diff --stat` luôn rỗng kể cả khi tệp bị sửa | Đo bất biến 0-churn bằng **md5 chốt** (`05 §2.3`), không bằng `git diff --stat` |

---

## VIII.18. AC-UX-064/065/066 — diệt `confirm()` trần, một SSoT hộp thoại xác nhận (spec cho **[FE] Bước-4**)

> **Spec đầy đủ (hợp đồng, delta từng dòng, bảng copy 21 call-site, bảng test, ADR-UX-16/17/18):** [`docs/ui-ux/06_CONFIRM_DIALOG_SSOT.md`](../ui-ux/06_CONFIRM_DIALOG_SSOT.md).
> Mục này là bản rút gọn cấp module. SSoT bị chạm thuộc IMM-00; view hưởng lợi thuộc IMM-03/05/07/08/10/15.

### VIII.18.1 Hiện trạng (đo từ đĩa 2026-08-04 — mẫu số chấm DELTA)

| Số đo | Giá trị |
|---|---|
| `confirm(` trần — quét thô `grep -rn "[^.a-zA-Z_]confirm(" src/views src/components --include=*.vue` | **47** / **31** file |
| … trừ **5** dòng chú thích ⇒ **call-site THẬT** | **42** / **28** file |
| Lô 1 (7 file nặng nhất) | **21** call-site = **50,0%** nợ |
| Còn lại sau lô 1 | **21** call-site / **21** file |
| `notify.confirm(` đang dùng đúng | **7** call-site / **5** view |
| View gọi `useModal()` trực tiếp | **0** (đúng — xem ADR-UX-16) |
| `NotificationModal.vue` | tự vẽ overlay `:48` · tự nghe `keydown` `:39` |

> **Đính chính số liệu:** «44/31» ở `04 §1.2/§10.6/§16` và `00 §6` đếm **thiếu strip-comment** và đã cũ; «49/33» của run-6 đếm thô trên cây bẩn. Mọi con số nợ trong doc từ nay phải kèm **công thức tái lập được**, và công thức đếm mã nguồn **phải strip comment**.

### VIII.18.2 Hai khuôn xác nhận HỢP LỆ — không mâu thuẫn với §II.3e / §III.10b-bis / §III.10d

Cả hai đều **cấm tuyệt đối** `confirm()` / `window.confirm()` trần. Chọn khuôn theo **nội dung hộp thoại**, không theo sở thích:

| Khuôn | Dùng khi | Tiền lệ trong repo |
|---|---|---|
| **P-A — `<BaseModal>` đặt ngay trong view** | Hộp thoại cần **UI thêm**: vùng lỗi chặn inline (AC-UX-062), ô nhập, xem trước, danh sách, trạng thái đang gửi | §II.3e (sinh lại QR) · §III.10b-bis (`DepreciationView`) · §III.10d (`ReferenceDataView`) |
| **P-B — `await useNotify().confirm({…})`** | Hộp thoại **chỉ có một câu hỏi có/không** trên một câu văn | `eol/DecommissionDetailView.vue:90` · `document/FirmwareCrDetailView.vue:54`/`:68` · `procurement/DecisionDetailView.vue:316`/`:360` |

**Toàn bộ 21 call-site của lô 1 thuộc P-B.** P-A **không bị** ADR-UX-16 thay thế — ADR-UX-16 chỉ cấm view nhập thẳng `useModal` (tầng hàng đợi).

### VIII.18.3 Ba delta trên SSoT

| Tệp | Delta | Ràng buộc |
|---|---|---|
| `components/common/NotificationModal.vue` | Render **qua `<BaseModal v-if="current">`**; **xoá** `onKey` + `onMounted`/`onBeforeUnmount` (`:35-40`); `tone ∈ {critical,error}` → `:danger`; nút vào slot `#footer` theo thứ tự **phụ trước, chính sau**; `@close="onCancel"` | `BaseModal` **không** có `v-if` nội tại — thiếu `v-if` ⇒ nền mờ phủ toàn app |
| `components/common/BaseModal.vue` | **THÊM** prop tuỳ chọn `layer?: 'default' \| 'system'` (mặc định `'default'` ⇒ `z-50` y hệt hôm nay; `'system'` ⇒ `z-[10000]`) | 19 file tiêu thụ **0 dòng đổi**; hai chuỗi class phải là **literal** (bẫy Tailwind JIT) |
| `composables/useNotify.ts` | **THÊM** `tone?` vào `ConfirmOpts` (`:31-40`) + chuyển tiếp 1 dòng ở `modal.confirm({…})` | Không truyền ⇒ giữ mặc định `'warning'` ⇒ 7 call-site đang có: 0 dòng đổi |
| `composables/useModal.ts` | **0 dòng đổi** — hợp đồng đối ngoại giữ nguyên tuyệt đối | `git diff --stat` cho tệp này phải **rỗng** |

### VIII.18.4 Lỗi P1 phải đóng: ESC kép **nuốt hộp thoại kế tiếp**

`useFocusTrap` nghe trên `document`, `NotificationModal` nghe trên `globalThis` ⇒ một lần nhấn `Escape` chạy **cả hai**; giữa hai nhịp, `current` (computed) **đã trỏ sang phần tử kế tiếp** của hàng đợi ⇒ phần tử đó bị `resolve(false)` **dù chưa từng hiển thị**.

> **Đính chính:** đây **không** phải «resolve 2 lần» — `dismiss` bất biến theo `id` (`useModal.ts:70-76`, `idx < 0` ⇒ thoát), nên hàng đợi 1 phần tử vẫn resolve đúng 1 lần. Test viết theo mô tả «2 lần» sẽ **XANH GIẢ**. Ca chứng minh là **hàng đợi 2 phần tử** (TC-UX6-02 ở `06 §4.3`): nhấn ESC 1 lần ⇒ A resolve `false`, **B còn nguyên**, `queue.length === 1`. Revert bản sửa ⇒ TC-UX6-02 phải ĐỎ.

### VIII.18.5 Boundaries

- **Always**: mọi xác nhận đi qua chuỗi `view → useNotify → useModal → NotificationModal → BaseModal` · một hộp thoại **đúng 1 chủ sở hữu `Escape`** · 100% chuỗi tiếng Việt, nút mặc định «Xác nhận»/«Huỷ» (LL-FE-53) · hành động phá huỷ ⇒ `tone: 'error'` ⇒ `danger`.
- **Ask first**: đổi prop/emit/testid/class **đã có** của `BaseModal` · đổi hợp đồng đối ngoại `useModal()` · di trú file ngoài 7 file lô 1 · gỡ overlay tự vẽ của 5 file lô 1 (đó là **AC-UX-055**).
- **Never**: `confirm(`/`window.confirm(`/`globalThis.confirm(` trần trong `.vue` · view import `useModal` · `NotificationModal` giữ `addEventListener('keydown'…)` · **thêm** dòng vào `ALLOWLIST_SELF_DRAWN` hoặc bản đồ `bareConfirmBudget` (cả hai CHỈ-GIẢM) · đổi **nghĩa** câu xác nhận đang có · sinh chuỗi tiếng Anh mới · dùng `vi.stubGlobal('confirm', …)` trong test mới.

### VIII.18.6 DoD FE (đo được — baseline đọc TỪ ĐĨA, chấm DELTA)

1. `grep -c 'fixed inset-0' frontend/src/components/common/NotificationModal.vue` ⇒ **0**; `grep -c "addEventListener('keydown'" …/NotificationModal.vue` ⇒ **0**; `git diff --stat -- frontend/src/composables/useModal.ts` ⇒ **rỗng**.
2. Nợ `confirm(` trần (công thức **có strip comment**, `06 §1.1`) ⇒ **21** call-site / **21** file; **7 file lô 1 = 0**.
3. `ALLOWLIST_SELF_DRAWN` của `modalOverlayHygiene.test.ts` **30 → 29** — xoá **đúng** dòng `NotificationModal.vue`, và hạ **3** chỗ số ở `:126` (`toHaveLength`), `:127` (`toBe`), `:141` (`toBeLessThanOrEqual`). Suite XANH.
4. Guard MỚI `components/common/bareConfirmBudget.test.ts`: bản đồ **(file, số lần)** = **21 file × 1**; ĐỎ khi tổng tăng · file lạ · vượt hạn mức · **và khi giảm mà quên hạ sổ** (INV-UXCONF-1…5, `06 §6.4`).
5. Bốn tệp test cũ: `grep -c "stubGlobal('confirm'" <file>` ⇒ **0** ở cả 4 (**KHÔNG** dùng `grep 'window.confirm'` — chuỗi đó chỉ nằm trong chú thích, phép đo vô nghĩa). Mỗi tệp thêm ≥ **2** ca: xác nhận ⇒ API gọi 1 lần · **huỷ ⇒ API KHÔNG gọi**.
6. `npx vitest run` **0 ĐỎ**; DELTA ≥ **+2 tệp test** / **+25 TC** so với baseline đĩa **340** (`find frontend/src -name '*.test.ts' | wc -l`).
7. 4 guard `uiAuditDocParity` · `uiFixPlanParity` · `modalOverlayHygiene` · `uiPrimitiveHygiene` **XANH**.
8. `npx vue-tsc --noEmit` ⇒ **0** lỗi. **KHÔNG** `npm run build` (`emptyOutDir` = deploy live — LL-DEPLOY-09), **KHÔNG** commit/push (HARD-STOP USER), `git status -- '*.py'` ⇒ **rỗng** (⇒ **không** cần restart gunicorn, **không** `bench migrate`).

### VIII.18.7 Bốn đính chính của [BA] so với đề mục đóng băng (chấm theo bản này)

| # | Đề mục ghi | Đĩa nói | Quyết định |
|---|---|---|---|
| SC-1 | baseline **42 call-site / 29 file** | **42 / 28** — 3 tệp chỉ chứa chú thích (`ProcurementPlanDetailView`, `CalibrationDetailView`, `NotificationModal`) ⇒ 31 − 3 = 28 | Chấm theo **42/28**; đích sau lô 1 = **21/21** |
| SC-2 | ESC kép ⇒ «`resolve` gọi **2 lần**» | `dismiss` bất biến theo `id` ⇒ hàng đợi 1 phần tử vẫn resolve **1 lần** | Ca chứng minh đổi sang **hàng đợi 2 phần tử** (TC-UX6-02); test theo mô tả cũ là **xanh giả** |
| SC-3 | nghiệm thu `grep -c 'window.confirm' <4 tệp>` = 0 | Đã **= 0** trước khi sửa (stub thật viết `vi.stubGlobal('confirm', …)`; chuỗi `window.confirm` chỉ ở chú thích, 1 hit ở 2 tệp) | Lệnh đúng = `grep -c "stubGlobal('confirm'"`. Thêm: `AssetDepreciationSchedule.test.ts` **không hề stub** ⇒ nhánh xác nhận **chưa từng được kiểm thử** (lỗ phủ, không phải test sẽ đỏ) |
| SC-4 | SSoT = `composables/useModal.ts`, view gọi `useModal().confirm` | `useNotify.ts:127-144` **đã** uỷ nhiệm cho `modal.confirm`; **7** call-site ở 5 view đã dùng `notify.confirm` và có test | View gọi **`useNotify().confirm()`** (ADR-UX-16); `useModal` là tầng hàng đợi, view **không** nhập. `ConfirmOpts` thêm `tone?` để nối `danger` |

> **Chặn thêm (đã gỡ ở bước BA):** `uiAuditDocParity.test.ts:35` `ROUND_VALUES` trước đó chỉ nhận `{2,3,4,5,6}` ⇒ ghi «vòng 7» cho mục mới làm guard ĐỎ — **đã nới thành `{2,…,7}`**. Và `:220` đối chiếu dòng «**Tổng: N mục**» ⇒ **đã sửa 63 → 66** cùng lượt với 3 mục mới. [FE] **không** cần chạm 2 chỗ này nữa.

---

## DoD — File 06 hoàn chỉnh

### I. Design System Tokens
- [x] Color palette + semantic colors (lifecycle_status, CAPA status)
- [x] Typography scale
- [x] Component library (19 components)
- [x] Icon set

### II. App Shell & Sitemap
- [x] App shell layout (Topbar + Sidebar + Main)
- [x] Sidebar navigation (10 groups)
- [x] Sitemap đầy đủ (30+ routes)
- [x] Auth guard states

### III. View Specifications
- [x] Dashboard (KPI cards + charts)
- [x] AC Asset List, Detail (6 tabs), Form
- [x] SLA Matrix view
- [x] Audit Trail view (verify chain)
- [x] CAPA workflow bar
- [x] Incident Wizard (3 steps)

### IV. Pinia Stores
- [x] authStore (hasRole)
- [x] uiStore (sidebar, tabs)
- [x] notifStore (scheduler alerts)
- [x] Module store pattern

### V. API Client
- [x] Axios wrapper + CSRF
- [x] imm00.ts endpoint bindings
- [x] Error handling

### VI. i18n
- [x] vi.json shared labels (6 namespaces)

### VII. UX Patterns
- [x] Role-based UI (5 roles)
- [x] Confirmation modal
- [x] Offline support
- [x] Keyboard shortcuts

### VIII. Tech stack & directory
- [x] Full tech stack list
- [x] Directory structure

---

## Khuôn trạng thái màn danh sách — `AC-UX-047` lô 3 (cross-cutting, 2026-08-04)

Màn danh sách của module này áp **khuôn dùng chung** `frontend/src/components/ui/ListPageShell.vue`
(4 trạng thái LOẠI TRỪ: đang tải / lỗi + «Thử lại» / rỗng + hướng dẫn / có dữ liệu). Đặc tả **KHÔNG** lặp
ở đây — SSoT là Core Doc UI/UX:

| Mục | Nơi chốt |
|---|---|
| Hợp đồng props/slots/`data-testid` | [`docs/ui-ux/02_LIST_PAGE_SHELL.md §3`](../ui-ux/02_LIST_PAGE_SHELL.md) |
| Sổ lô 3 + delta từng file + bảng copy tiếng Việt | [`§14.2` / `§14.4`](../ui-ux/02_LIST_PAGE_SHELL.md) |
| Bất biến `INV-UX3-24…29` + test `TC-UX3-35 / TC-UX3-37` | [`§14.5` / `§14.6`](../ui-ux/02_LIST_PAGE_SHELL.md) |
| Guard adoption CHỈ-GIẢM (`AC-UX-070`) | `frontend/src/views/listShellAdoption.test.ts` |

- **Route thuộc lô 3 của module này:** `/audit-trail` · `/service-contracts`
- **File view:** `views/audit/AuditTrailListView.vue` · `views/purchase/ServiceContractListView.vue`
- **Ràng buộc riêng phải giữ:** xem cột «Bẫy riêng theo màn» ở [`§14.4`](../ui-ux/02_LIST_PAGE_SHELL.md) —
  lỗi **lượt nạp danh sách** là nguồn DUY NHẤT của `:error-message`; lỗi biểu mẫu / cảnh báo bộ lọc /
  hành động ghi **không** được lật trạng thái danh sách (`ADR-UX-24`).
