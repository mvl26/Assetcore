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
/pending-approvals          → PendingApprovalsView.vue                      [BUILT — views/audit/]
/inventory                  → Inventory Dashboard                           [SPEC]
/print/:doctype/:name       → Print-friendly view                           [SPEC]
/login                      → Frappe login (redirect)                       [BUILT — Frappe native]
/403                        → Forbidden403View                              [SPEC]
```

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
   - **Header định danh:** `asset_name` (lớn, `text-lg font-semibold`) + `asset_code` (phụ) + **status pill VI** (`lifecycle_status_label` qua màu theo `lifecycle_status` — tái dùng `LIFECYCLE_STATUS_CLASS` từ `constants/labels.ts`). KHÔNG hiển thị mã EN thô.
   - **Thông tin:** `device_model_name`, `location_name` (mỗi dòng nhãn VI + giá trị; rỗng → "—").
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
  device_model_name: string; location_name: string;
  lifecycle_status: string; lifecycle_status_label: string;
  last_maintenance: { event_type: string; event_type_label: string; date: string } | null;
  next_pm_date: string | null;
  pm_overdue: boolean;   // NEW (Vòng 27 B / BR-00-36) — cờ PM quá hạn derive SERVER-SIDE; FE chỉ render
  next_calibration_date: string | null;   // NEW (Vòng 28 B / BR-00-37) — ngày hiệu chuẩn kế tiếp
  calibration_overdue: boolean;            // NEW (Vòng 28 B / BR-00-37) — cờ hiệu chuẩn quá hạn derive SERVER-SIDE; FE chỉ render
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
