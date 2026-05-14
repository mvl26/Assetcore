# 06 — Frontend Design — IMM-00 Foundation (Master / Cross-cutting)

| Mục | Giá trị |
|---|---|
| Module | IMM-00 — Foundation / Master Cross-cutting |
| Phạm vi | Foundation — shared UI components + base views |
| Owner | FE Lead |
| Liên kết | [05 API Specification](./05_API_Specification.md) · [07 Testing & QA](./07_Testing_QA.md) |
| Tech Stack | Vue 3 · TypeScript · Pinia · Vue Router 4 · TailwindCSS · Frappe UI |
| Phiên bản | 3.1.0 |
| Trạng thái | **Live (partial) ✅** — 2 master-data views built (ReferenceData, SlaPolicyList); Asset List/Depreciation/Transfer/Audit + Inventory đã có view riêng (xem `frontend/src/views/asset/`, `inventory/`); sitemap chi tiết còn lại là spec. Synced vs code 2026-05-14. |

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

> **Verified từ `types/imm00.ts`:** LifecycleStatus = `'Commissioned' | 'Active' | 'Under Repair' | 'Calibrating' | 'Out of Service' | 'Decommissioned'`. (Không có 'Planned', 'Commissioning', 'Under Maintenance' trong type — 'Under Maintenance' tồn tại trong state machine nhưng không trong TS type.)

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

> **Verified từ code:** Chỉ 2 Vue views đã build trong `frontend/src/views/master-data/`:
> - `ReferenceDataView.vue` — Dữ liệu tham chiếu (Locations, Departments, Categories, Device Models)
> - `SlaPolicyListView.vue` — Danh sách và quản lý SLA Policies

Các routes dưới đây đánh dấu `[BUILT]` nếu có Vue component, `[SPEC]` nếu chỉ là spec chưa build.

```
/                           → Dashboard (IMM-00 overview KPIs)              [SPEC]
/assets                     → AC Asset List                                  [BUILT — xem module khác]
/assets/new                 → AC Asset Form (Create)                         [SPEC]
/assets/:name               → AC Asset Detail (6 tabs)                       [SPEC]
/assets/:name/edit          → AC Asset Form (Edit)                           [SPEC]
/assets/:name/lifecycle     → Asset Lifecycle Event Timeline                  [SPEC]
/suppliers                  → AC Supplier List                               [SPEC]
/suppliers/:name            → AC Supplier Detail + authorized_technicians    [SPEC]
/master-data                → ReferenceDataView.vue (Locations/Depts/Cats/Models) [BUILT]
/master-data/sla            → SlaPolicyListView.vue                          [BUILT]
/incidents                  → Incident Report List                           [SPEC]
/incidents/new              → Incident Wizard (3 steps)                      [SPEC]
/incidents/:name            → Incident Report Detail                         [SPEC]
/capa                       → IMM CAPA Record List                           [SPEC]
/capa/new                   → CAPA Form (Create)                             [SPEC]
/capa/:name                 → CAPA Detail + workflow bar                     [SPEC]
/audit-trail                → IMM Audit Trail Log (read-only)                [SPEC]
/inventory                  → Inventory Dashboard                            [SPEC]
/print/:doctype/:name       → Print-friendly view                            [SPEC]
/login                      → Frappe login (redirect)                        [BUILT — Frappe native]
/403                        → Forbidden403View                               [SPEC]
```

## II.4. Auth Guard

| Trạng thái | Hành vi |
|---|---|
| Chưa đăng nhập | Redirect `/login` |
| Đã đăng nhập, đủ role | Render route |
| Đã đăng nhập, thiếu role | Render `Forbidden403View` |
| API 401 | Xóa Pinia auth store, redirect `/login` |
| API 403 | Toast danger "Không có quyền thực hiện hành động này" |
| API 500 | `ErrorBoundary` với retry + error ID |

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
| Đăng ký BYT sắp hết | `list_assets?byt_expiry_within=90` | `/assets?byt_expiry=90d` |

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
| `gmdn_status` | — | select |

Filter sidebar (desktop) / drawer (mobile): `status, lifecycle_status, department, risk_class, next_pm_date` range.

Bulk actions: Gán KTV, In QR hàng loạt, Xuất Excel.

## III.3. AC Asset — Detail View

Route: `/assets/:name`

Header: `← AC-ASSET-... [Active ●] [Sửa] [Thao tác ▾]`

**6 tabs:**

| Tab | Nội dung |
|---|---|
| 1. Info HTM | asset_code, UDI, GMDN, BYT reg, device_model, class, risk, custodian, location, gmdn_status |
| 2. Vòng đời | Timeline Asset Lifecycle Event (vertical timeline) |
| 3. PM & Calibration | next_pm_date, pm_interval_days, next_calibration_date, lịch sử PM/Cal |
| 4. Tài liệu | Upload IQ/OQ/PQ, manual, biên bản — Frappe File |
| 5. Incident & CAPA | Danh sách Incident + CAPA liên quan, CTA tạo mới |
| 6. Audit Trail | Log immutable của asset, nút "Verify chain" |

Action menu ▾: Đổi trạng thái (modal chọn transition hợp lệ), Transfer khoa, Decommission, In QR, Xuất lý lịch PDF.

## III.4. AC Asset — Form (Create / Edit)

| Section | Fields |
|---|---|
| §1 Định danh | asset_code (auto), asset_name*, udi_code, gmdn_code, byt_reg_no, byt_reg_expiry |
| §2 Phân loại | device_model* (auto-fill: class, risk, pm_interval, asset_category) |
| §3 Vị trí & Trách nhiệm | department*, location, responsible_technician |
| §4 Lịch bảo trì | pm_interval_days (auto), next_pm_date, next_calibration_date |
| §5 Ghi chú | notes, attachments |

Auto-fill when device_model selected:
```
GET get_device_model_defaults?model=IMM-MDL-...
→ apply: device_class, risk_class, pm_interval_days, asset_category
```

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
async function updateGmdn(name: string, gmdn_status: GmdnStatus, reason: string): Promise<{ name, gmdn_status, previous }>
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

```typescript
export const GMDN_STATUS_LABEL: Record<string, string>  // {'In Use': 'Đang sử dụng', 'Not Use': 'Không sử dụng'}
export const GMDN_OPTIONS: Array<{ value: GmdnStatus; label: string }>
```

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
export async function updateGmdnStatus(name: string, gmdn_status: string, reason: string): Promise<...>
export async function toggleGmdnStatus(name: string): Promise<...>
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

// Transfer
export async function getTransferFull(name: string): Promise<...>
export async function approveTransfer(name: string): Promise<...>
export async function updateTransfer(name: string, data): Promise<...>

// Depreciation (Asset Finance Hub — full coverage)
export function computeDepreciation(name: string): Promise<DepreciationComputeResult>
export function listAssetsDepreciation(params: { page?, page_size?, method_filter?, status_filter?, category_filter? }): Promise<{ items: AssetDepreciationRow[]; pagination }>
export function getDepreciationStats(): Promise<DepreciationStats>
export function computeAllDepreciation(): Promise<{ generated_schedules, skipped, executed_rows, updated_assets }>
export async function getDepreciationSchedule(asset_name: string): Promise<DepreciationScheduleResponse>
export async function regenerateDepreciationSchedule(asset_name: string, force: 0|1): Promise<{ generated: number }>
export async function previewDepreciationSchedule(params: { gross, residual, method, total_months, frequency, start_date }): Promise<DepreciationPreviewRow[]>
export async function runDueDepreciationNow(as_of?: string): Promise<{ executed_rows; updated_assets }>
export async function bulkRegenerateScheduleByCategory(category_name: string): Promise<{ assets_processed: number }>

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
    "gmdn_status": "Trạng thái GMDN",
    "gmdn_in_use": "Đang sử dụng",
    "gmdn_not_in_use": "Không sử dụng",
    "decommission_confirm": "Xác nhận ngừng sử dụng thiết bị",
    "decommission_warn": "Thao tác này sẽ đổi lifecycle_status → Decommissioned và huỷ toàn bộ lịch PM/Cal"
  },
  "capa": {
    "list_title": "Danh sách CAPA",
    "overdue_warning": "CAPA quá hạn",
    "close_confirm": "Xác nhận đóng CAPA",
    "missing_root_cause": "Phải nhập phân tích nguyên nhân gốc rễ (BR-00-08)"
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
