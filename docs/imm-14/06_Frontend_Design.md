# 06 — Frontend Design (IMM-14 Giải nhiệm thiết bị)

| Mục | Giá trị |
|---|---|
| Module | IMM-14 — Giải nhiệm thiết bị |
| Phạm vi | Sitemap + UI/UX + Cascade + Validation |
| Owner | FE Lead + UX Designer |
| Liên kết | [04 Backend](./04_Backend_Design.md) · [05 API](./05_API_Specification.md) |

> Stack chuẩn AssetCore: **Vue 3 + TypeScript + Pinia + Vue Router + TailwindCSS + TanStack Query** (refer `.claude/skills/assetcore-fe-module/SKILL.md`). Design system tham chiếu `docs/res/design/design-frontend.md`.

---

## 1. Sitemap

```
/imm-14
├── /imm-14                    # List closure (mặc định status = active workflow states)
├── /imm-14/new                # Create closure — chọn Decommission Decision (IMM-13)
├── /imm-14/:closure_no        # Detail page (4 tab)
│   ├── tab Reconciliation     # Đối soát kho + kế toán + WO + docs
│   ├── tab Sanitization       # Checklist PII/PHI + ký DPO
│   ├── tab Documents          # Biên bản, scan, ảnh
│   └── tab Audit              # Lifecycle event + audit trail
├── /imm-14/dashboard          # Dashboard end-of-life
└── /imm-14/archived           # List asset đã decommissioned (read-only)
```

---

## 2. Trang List

- **Filter**: workflow_state, asset_no (autocomplete), năm, disposal_method, lý do (`reason_category`).
- **Cột**: Closure No, Asset No (link đến IMM-04 detail), Asset name, Workflow State (badge màu theo state), Reason, Disposal Method, Created By, Created On, Approved On.
- **Action bar**: New (HTM Engineer), Export (Auditor), Filter saved view.
- **Empty state**: "Chưa có closure record nào — bắt đầu từ Decommission Decision IMM-13".

---

## 3. Trang Create (Step Form 3 bước)

| Bước | Nội dung |
|---|---|
| 1. Pick decision | Combobox load Decommission Decisions ở state `Approved` mà chưa có closure active. Hiển thị asset_no, lý do. |
| 2. Snapshot review | Hiện asset summary (name, model, serial, location), purchase_value, book_value, lifecycle history tóm tắt. |
| 3. Confirm create | Tạo closure draft + redirect detail page tab Reconciliation |

Cascade fields: chọn `decision_no` → auto-fill `asset_no`, `reason`, `disposal_method` (cho phép user override sau).

---

## 4. Trang Detail — 4 tab

### 4.1. Tab Reconciliation

Bảng có 4 phân nhóm (collapsible card):

- **A. Work Order còn mở** (scope=`work_order`): list WO PM/CM/Calib chưa đóng. Action: "Đóng WO" (link IMM-08/09/11) hoặc "Transfer".
- **B. Phụ tùng tồn kho** (scope=`spare_stock`): list dòng IMM-15 stock. Action cho Storekeeper: chọn `decision = reuse | scrap | transfer` cho từng dòng.
- **C. Sổ tài sản** (scope=`book_value`): hiện `book_value` hiện tại, ô nhập `final_value`, ô chọn `disposal_method` (disposal/donation/sale/trade-in/internal_reassignment). Chỉ Accountant edit.
- **D. Hồ sơ pháp lý** (scope=`document`): list IMM-05 docs còn `active`. Mỗi dòng có nút "Mark archive-ready" (QLCL Officer).

Mỗi line có badge status: ⏳ pending / ✅ done / ⚠️ blocker.

### 4.2. Tab Sanitization

- Checklist 5–8 items theo template (load từ BE theo asset).
- Ô chữ ký DPO + nút "Ký xác nhận" (chỉ visible nếu user role = DPO).
- Trường note kèm timestamp.
- Nếu `asset.has_patient_data = false` → tab hiện chế độ "Không bắt buộc, vẫn nên ghi log" với template ngắn hơn.

### 4.3. Tab Documents

- Upload đa file (PDF, ảnh).
- Bảng hiện: file name, type (biên bản huỷ, biên bản giao nhận, ảnh hiện trạng, scan QĐ), uploaded by, uploaded at.
- Mỗi file mở preview inline.

### 4.4. Tab Audit

- Timeline workflow state transition.
- Bảng lifecycle event của asset (filter event của closure này).
- Liên kết `IMM Audit Trail` đầy đủ — chỉ-đọc.

### 4.5. Action bar

- **Submit for Approval** — visible khi state Reconciling và đủ 7 mục (BR-14-01).
- **Approve** — visible cho Department Head khi state Pending Approval.
- **Send back** — visible cho Department Head khi state Pending Approval.
- **Request Rollback** — visible khi state Closed và còn trong window.
- **Confirm Rollback** — visible cho Accountant khi state Rollback Requested.
- **Print Closure Report** — visible mọi state ≥ Pending Approval (PDF cho audit).

Disable action với guard tooltip giải thích lý do (vd "Còn 2 WO chưa đóng").

---

## 5. Pinia store (skeleton)

```typescript
// frontend/src/stores/imm14.ts (gợi ý — chốt sprint W3-2)
export const useClosureStore = defineStore('imm14_closure', {
  state: () => ({
    current: null as Closure | null,
    list: [] as Closure[],
    filters: { /* ... */ },
  }),
  actions: {
    async createFromDecision(decisionNo: string) { /* call api/imm14.ts */ },
    async finalize(closureNo: string) { /* ... */ },
    async requestRollback(closureNo: string, reason: string) { /* ... */ },
  },
});
```

API client: `frontend/src/api/imm14.ts` — wrap `frappe.call` theo pattern `assetcore-fe-module`.

TanStack Query keys:

- `['imm14', 'list', filters]`
- `['imm14', 'detail', closureNo]`
- `['imm14', 'dashboard', period]`

Invalidate khi mutate (finalize, rollback, sanitization sign).

---

## 6. Validation rules (FE-side, mirror BE BR)

| BR | Hiển thị |
|---|---|
| BR-14-01 (7 mục) | Action "Submit for Approval" disabled + tooltip checklist còn thiếu |
| BR-14-02 (SoD) | Action "Approve" hidden nếu `current_user = created_by` |
| BR-14-04 (rollback window) | Action "Request Rollback" disabled nếu quá window, tooltip ngày hết hạn |
| BR-14-05 (sanitization) | Tab Sanitization có badge ❗ nếu `has_patient_data` và chưa ký |
| BR-14-06 (asset lock) | Trang IMM-04 cho asset `decommissioned` ẩn nút Edit |
| BR-14-08 (phụ tùng) | Mục B reconciliation có badge ⚠️ nếu còn dòng pending |

Mọi validation FE chỉ là UX — BE phải re-validate (defense in depth).

---

## 7. Cascade fields

| Field cha | Field con auto | Nguồn |
|---|---|---|
| `decision_no` | `asset_no`, `reason`, `disposal_method` (initial) | IMM-13 Decommission Decision |
| `asset_no` | `gmdn_classification`, `has_patient_data`, `book_value`, `purchase_value` | AC Asset |
| `disposal_method` | template `Sanitization Item` (default) | Theo classification + method |
| `scope` (line) | required role (read/edit) | Permission map |

---

## 8. Dashboard (`/imm-14/dashboard`)

Card / chart:

- KPI card: số closure trong năm, % đầy đủ 7 mục, thời gian đóng trung bình, % rollback.
- Bar chart: số asset giải nhiệm theo tháng (tách theo disposal_method).
- Pie chart: lý do giải nhiệm (recall, end-of-life, repair-not-economical, donation, replaced).
- Table: top 10 asset có chi phí giải nhiệm cao nhất.
- Filter: năm, khoa, model.

Refer cách dashboard IMM-08 / IMM-12 đã implement (chia sẻ component).

---

## 9. Print Format — Closure Report

Template PDF: trang A4, header bệnh viện, 7 section khớp 7 mục bắt buộc + chữ ký 5 chỗ (HTM, Storekeeper, Accountant, DPO, Department Head). Footer: closure_no + watermark "AUDIT EVIDENCE — IMM-14".

Format file: `assetcore/print_format/imm_14_closure_report.json` *(scaffold sprint W3-3.)*

---

## 10. UX rules (must)

- Mọi action không thể đảo ngược (Approve, Confirm Rollback) → modal xác nhận 2 bước (text typing tên closure_no).
- Mọi error code BE → toast với message i18n + nút "Xem chi tiết" mở console log.
- Field tiền tệ format VND (1.000.000 đ), DPO sign timestamp format `dd/MM/yyyy HH:mm`.
- Empty list / loading / error states đầy đủ — không bao giờ trắng tinh.

---

---

## 11. Wave 2 MVP — Entrypoint THẬT trên màn Asset Detail (IMM-00) — CHỐT

> **Self-Correction (2026-06-04):** vòng 2 KHÔNG build sitemap `/imm-14` đầy đủ (§1) — chỉ thêm **1 entrypoint thật** trên màn chi tiết thiết bị + 1 modal closure-record gọi 2 API mới. List/dashboard/4-tab giữ làm `[ROADMAP]` Đợt 3.

### 11.1. Vị trí (file thật)

- **View:** `frontend/src/views/asset/AssetDetailView.vue` (màn chi tiết thiết bị IMM-00 — đã tồn tại).
- **API client:** thêm vào `frontend/src/api/imm14.ts` (NEW): `createDecommission(payload)`, `approveDecommission(name)` — wrap `frappe.call`, parse envelope, throw `ApiError` chuẩn (`frontend/src/api/errors.ts`).
- **Store:** dùng store asset hiện có (`frontend/src/stores/imm00.ts`) để refresh asset sau khi giải nhiệm; KHÔNG bắt buộc store IMM-14 riêng ở MVP.

### 11.2. Nút "Giải nhiệm thiết bị"

- Đặt ở action bar màn AssetDetailView, **chỉ hiện** khi:
  - `auth.can('decommission.create') === true` (capability, KHÔNG so role-name), VÀ
  - `asset.lifecycle_status !== 'Decommissioned'` (terminal → ẩn nút, hiện badge "Đã giải nhiệm").
- **Stale-safe cap (USER REWORK IMM-14, 2026-06-04 — xem imm-00 06 §II.4b):** cap `decommission.*` phải tới FE sau release dù user có persisted-caps cũ. Phụ thuộc 2 fix shared: (a) `fetchSession` LUÔN gọi `loadCapabilities` (bỏ empty-check) → AC3; (b) version-stamp invalidate persisted-caps cũ khi BE bump `CAP_SET_VERSION` → AC4. KHÔNG cần xóa `localStorage` tay để nút hiện.
- Nhãn nút: **"Giải nhiệm thiết bị"** (VI 100%).
- Nếu asset đang Under Maintenance/Repair/Calibrating → nút vẫn hiện nhưng bấm sẽ nhận lỗi gate NEG-09 từ BE → toast cảnh báo (KHÔNG disable cứng ở FE để tránh drift; BE là SoT). Khuyến nghị: tooltip nhắc "Cần đóng phiếu bảo trì/sửa/hiệu chuẩn trước".

### 11.3. Modal "Hồ sơ giải nhiệm"

Trường nhập (nhãn VI):

| Field | Control | Ràng buộc FE (mirror BE) |
|---|---|---|
| Phương thức xử lý | Select | options: Huỷ / Điều chuyển/Donation / Bán/Trade-in / Lưu trữ — bắt buộc |
| Xác nhận đã xử lý dữ liệu bệnh nhân | Checkbox | nếu `asset.risk_classification ∈ {High, Critical}` → checkbox bắt buộc tick + label cảnh báo "Thiết bị phân loại C/D — bắt buộc (WHO §3.6)" |
| Ghi chú xử lý dữ liệu | Textarea | optional |
| Lý do giải nhiệm | Textarea | bắt buộc, ≥ 20 ký tự, hiện counter |
| Người chịu trách nhiệm | User-select | bắt buộc, default = current user |

- **Flow submit:** modal có 1 nút "Xác nhận giải nhiệm". Vì hành động không đảo ngược → modal xác nhận 2 bước (gõ tên/serial thiết bị để confirm — theo §10 UX rule).
- **Gọi API:** submit → `createDecommission(payload)` rồi `approveDecommission(name)` liên tiếp (hoặc 1 endpoint gộp nếu BE chọn — chốt BE). MVP khuyến nghị 2-call tuần tự, hiển thị loading.
- **Thành công:** đóng modal, toast "Đã giải nhiệm thiết bị thành công", refresh asset (status → Decommissioned, ẩn nút).

### 11.4. Xử lý lỗi (KHÔNG leak EN/raw status, KHÔNG "Lỗi hệ thống")

- Mọi lỗi BE trả envelope `{success:false, code, error}` → FE map `code` → toast **cảnh báo** (warning, không phải error đỏ "Lỗi hệ thống") với `error` (đã là message VI từ BE):
  - `BUSINESS_RULE` → toast vàng nội dung field thiếu / sanitization gate.
  - `BAD_STATE` (NEG-09 / terminal / gate) → toast cảnh báo nội dung từ BE (đã VI hoá).
  - `CONFLICT` → toast "Thiết bị đã có hồ sơ giải nhiệm đang xử lý".
- KHÔNG render raw `lifecycle_status` EN ("Decommissioned") cho user — map qua bảng nhãn VI hiện có (`statusLabel`/i18n). Badge VI: "Đã giải nhiệm".
- KHÔNG để traceback / "Internal Server Error" lọt ra UI.

### 11.5. i18n keys mới (thêm vào `frontend/src/locales/vi.json`)

`imm14.btn.decommission`, `imm14.modal.title`, `imm14.field.disposal_method`, `imm14.field.patient_data_sanitized`, `imm14.field.reason`, `imm14.field.responsible`, `imm14.toast.success`, `imm14.confirm.type_name` — tất cả VI.

---

## 12. Wave 2 Vòng 2 — Danh sách "Biên bản giải nhiệm" (`/decommissions`) — CHỐT

> **Delta (2026-07-02).** Vòng 2 chỉ có write-path (§11, nút trên asset detail) → IMM-14 **vô hình** (sidebar `items: []`). §12 thêm 1 màn danh sách read-only + route + sidebar để tra cứu/báo cáo. KHÔNG closure detail view (row-click → asset — ADR-IMM14-LIST-02).

### 12.1. Vị trí (file thật)

- **View (NEW):** `frontend/src/views/decommission/DecommissionListView.vue`.
- **Route (NEW):** `frontend/src/router/index.ts` — `path: '/decommissions'`, `name: 'DecommissionList'`, `component: DecommissionListView`, `meta: { requiresAuth: true, title: 'Biên bản giải nhiệm', moduleId: 'imm14', requiredCapabilities: ['decommission.read'] }`.
- **API client (EXTEND):** `frontend/src/api/imm14.ts` — thêm `listDecommissions(filters, page, pageSize)` + type `DecommissionListRow` + `ListResp<T>` (mirror `api/imm16.ts`).
- **Sidebar (EDIT):** `frontend/src/constants/sidebarNav.ts` — `imm14.items` từ `[]` → 1 item.
- **Test (NEW):** `frontend/src/views/decommission/DecommissionList.render.test.ts` (mirror `views/inventory/cycleCountList.render.test.ts`).

### 12.2. FE API client (thêm vào `api/imm14.ts`)

```typescript
// DecommissionState HIỆN là 'Draft' | 'Approved' → PHẢI thêm 'Cancelled' cho list (khớp Select DocType).
export type DecommissionState = 'Draft' | 'Approved' | 'Cancelled'

export interface DecommissionListRow {
  name: string
  asset: string
  asset_name_snapshot: string
  risk_classification_snapshot: string
  workflow_state: DecommissionState
  disposal_method: DisposalMethod
  decommissioned_on: string | null
  responsible: string          // email — KHÔNG render ra UI (chỉ khoá kỹ thuật)
  responsible_name: string | null  // full name — render cột "Người chịu trách nhiệm"
}

export interface ListResp<T> { data: T[]; pagination: { page: number; page_size: number; total: number; total_pages: number } }

export const listDecommissions = (
  filters: Record<string, unknown> = {}, page = 1, pageSize = 20,
) => frappeGet<ListResp<DecommissionListRow>>(`${BASE}.list_decommissions`, {
  filters: JSON.stringify(filters), page, page_size: pageSize,
})
```

### 12.3. Bảng — cột (nhãn VI 100%)

| Cột | Field | Render |
|---|---|---|
| Số hồ sơ | `name` | text (DECOM-YYYY-####). KHÔNG link tới closure detail (ADR-IMM14-LIST-02). |
| Thiết bị | `asset_name_snapshot` (fallback `asset`) | text; cả row click-được → `/assets/:asset`. |
| Phương thức xử lý | `disposal_method` | enum value render **as-is** (SSoT enum, exempt dịch theo LL-FE-53): Huỷ / Điều chuyển/Donation / Bán/Trade-in / Lưu trữ. |
| Trạng thái | `workflow_state` | `StatusBadge` map VI: **Draft→Bản nháp · Approved→Đã duyệt · Cancelled→Đã huỷ**. KHÔNG leak raw EN. |
| Ngày giải nhiệm | `decommissioned_on` | format `dd/MM/yyyy` (dùng formatter hiện có); NULL (Draft) → "—". |
| Người chịu trách nhiệm | `responsible_name` | tên đầy đủ; NULL → "—". **KHÔNG render `responsible` (email)** — BR-14-W2-11. |

- **Phân loại rủi ro** (`risk_classification_snapshot`) có sẵn trong row — tùy chọn hiển thị badge phụ (không bắt buộc ở acceptance).

### 12.4. Filter bar (đo được)

- **Trạng thái** (Select): Tất cả / Bản nháp (Draft) / Đã duyệt (Approved) / Đã huỷ (Cancelled) → gửi `filters.workflow_state`.
- **Phương thức xử lý** (Select): Tất cả / 4 enum value → gửi `filters.disposal_method`.
- (Tùy chọn) **Thiết bị**: ô lọc theo `asset` → `filters.asset`. Acceptance yêu cầu filter theo trạng thái + phương thức là bắt buộc; `asset` optional ở UI nhưng endpoint hỗ trợ.
- Đổi filter → refetch (TanStack key `['imm14','decommissions','list', filters, page]`); reset về page 1.

### 12.5. UX states

- **Empty-state:** khi `data.length === 0` — "Chưa có biên bản giải nhiệm nào." (VI). KHÔNG trắng tinh.
- **Loading / error:** skeleton + toast lỗi (map `code` → message VI; KHÔNG "Lỗi hệ thống"). Thiếu `decommission.read` → router guard chặn trước (requiredCapabilities) → không tới màn; nếu lọt (race) BE trả 403 → toast + điều hướng.
- **Pagination:** dùng `pagination.total` / `total_pages` từ envelope (component phân trang hiện có). **Invariant FE:** `data.length ≤ pagination.page_size`.
- **Row-click:** ~~`router.push('/assets/' + row.asset)` (ADR-IMM14-LIST-02)~~ → **Superseded vòng 17 (§13.4):** row-click → `/decommissions/:id` (biên bản); link asset chuyển xuống vị trí phụ. Xem ADR-IMM14-DETAIL-03.

### 12.6. Sidebar (`constants/sidebarNav.ts`)

```typescript
imm14: {
  code: 'IMM-14', title: 'Giải nhiệm thiết bị', icon: 'trending',
  items: [
    { label: 'Biên bản giải nhiệm', path: '/decommissions', icon: 'trending', cap: 'decommission.read' },
  ],
},
```

→ module IMM-14 hết vô hình (mirror cách imm13 có 1 item "Phiếu điều chuyển").

### 12.7. Render test (mirror `cycleCountList.render.test.ts`)

- Mock `listDecommissions` trả 3 row (mỗi workflow_state 1 trạng thái + đủ 4 disposal_method mẫu, `responsible_name` set, `responsible` email set).
- Assert: (a) 3 dòng render; (b) badge VI **Bản nháp/Đã duyệt/Đã huỷ** xuất hiện, KHÔNG có 'Draft'/'Approved'/'Cancelled' raw EN trong DOM; (c) cột người render `responsible_name`, **KHÔNG** xuất hiện chuỗi email `responsible` trong DOM (anti-leak); (d) empty-state hiện khi mock trả `data:[]`; (e) click row gọi `router.push('/assets/<asset>')`.

---

## 13. Vòng 17 — Màn Chi tiết & DUYỆT biên bản (`/decommissions/:id`) — CHỐT

> **Delta (2026-07-10).** Supersede ADR-IMM14-LIST-02 → build `DecommissionDetailView` + đổi drill row → biên bản. Gate CTA Duyệt **server-driven** (`can_approve===1`, KHÔNG hardcode docstatus/workflow_state=== — GATE-8/LL-FE-51). Ref ADR-IMM14-DETAIL-03 + ADR-IMM14-APPROVE-04 (`02 §VIII.5`) + `05 §8`.
>
> **⚠️ Đính chính path (report):** §12.1 ghi list view ở `views/decommission/DecommissionListView.vue`, nhưng file THẬT nằm ở `frontend/src/views/eol/DecommissionListView.vue`. Vòng 17 dùng đúng path thật `views/eol/`.

### 13.1. Vị trí (file thật)

- **View (NEW):** `frontend/src/views/eol/DecommissionDetailView.vue`.
- **Route (NEW):** `frontend/src/router/index.ts` — `path: '/decommissions/:id'`, `name: 'DecommissionDetail'`, `component: () => import('@/views/eol/DecommissionDetailView.vue')`, `meta: { requiresAuth: true, title: 'Biên bản giải nhiệm', moduleId: 'imm14', requiredCapabilities: ['decommission.read'] }`. Đặt **trước/sau** route `/decommissions` (list) sao cho matcher không nuốt (path param `:id` khác path tĩnh — Vue Router phân biệt được).
- **API client (EXTEND):** `frontend/src/api/imm14.ts` — mở rộng `DecommissionRecord` (return của `getDecommission`) thêm 7 field (`05 §8.4`). `getDecommission` + `approveDecommission` đã tồn tại — KHÔNG thêm hàm mới.
- **Test (NEW):** `frontend/src/views/eol/decommissionDetailCtaGate.test.ts`.

### 13.2. Layout màn chi tiết (nhãn VI 100%)

Section đọc biên bản (mirror `DocumentDetailView` card style):

| Nhãn | Field | Render |
|---|---|---|
| Số hồ sơ | `name` | text (DECOM-YYYY-####). |
| Thiết bị | `asset_name` (fallback `asset` chỉ khi rỗng) | text; **KHÔNG** render `asset` Link-id thô. Kèm nút phụ "Xem thiết bị" → `/assets/:asset`. |
| Phân loại rủi ro | `risk_classification_snapshot` | badge phụ (Low/Medium/High/Critical → nhãn VI nếu có map; giá trị enum SSoT). |
| Phương thức xử lý | `disposal_method` | enum render as-is (SSoT, exempt dịch — LL-FE-53). |
| Lý do giải nhiệm | `decommission_reason` | text (multiline). |
| Đã xử lý dữ liệu bệnh nhân | `patient_data_sanitized` | "Có"/"Không" (ép boolean từ int). |
| Ghi chú xử lý dữ liệu | `sanitization_note` | text; rỗng → "—". |
| Người chịu trách nhiệm | `responsible_name` | tên đầy đủ; NULL → "—". **KHÔNG** render `responsible` email (BR-14-W2-15). |
| Ngày giải nhiệm | `decommissioned_on` | format dd/MM/yyyy; NULL (Draft) → "—". |
| Trạng thái | `workflow_state` | `StatusBadge` VI: Draft→Bản nháp / Approved→Đã duyệt / Cancelled→Đã huỷ. KHÔNG raw EN. |

### 13.3. CTA "Duyệt giải nhiệm" — server-driven gate (GATE-8/LL-FE-51)

```typescript
const canApprove = computed<boolean>(() => rec.value?.can_approve === 1)
// KHÔNG: v-if="rec.docstatus === 0" / "rec.workflow_state === 'Draft'"  ← dead-gate, CẤM.
```

- Nút render **⇔ `canApprove === true`** (tức `can_approve === 1`). Trạng thái/flag lạ / thiếu field → degrade an toàn = KHÔNG nút.
- Bấm → `useNotify.confirm` (xác nhận, hành động không đảo ngược) → `approveDecommission(name)` qua `useApi().run` (interceptor map lỗi VN, KHÔNG echo traceback) → thành công: toast "Đã giải nhiệm thiết bị", **refetch `getDecommission`** → `can_approve` về 0 (reason "…đã được duyệt."), badge `workflow_state`→"Đã duyệt", CTA tự ẩn.
- **`can_approve === 0` → KHÔNG render nút** + hiện **hint** = `rec.approve_blocked_reason` (chuỗi VI từ BE) trong 1 vùng thông báo phụ (`role="status"`, không phải `role="alert"` đỏ). No dead-control (LL-FE-47).
- `data-testid`: `cta-approve` (nút), `approve-blocked-hint` (vùng hint).

### 13.4. Drill từ list (đổi target — supersede §12.5)

- `DecommissionListView` row-click → `router.push('/decommissions/' + row.name)` (biên bản), thay `/assets/:asset`.
- Link tới asset chuyển xuống **vị trí phụ**: giữ 1 icon-link/nút phụ trong row (hoặc chỉ trong màn detail — nút "Xem thiết bị"). Row-click chính = mở biên bản.
- Cập nhật `DecommissionList.render.test.ts`: assert click row gọi `router.push('/decommissions/<name>')` (thay assertion cũ `/assets/<asset>`).

### 13.5. Không hồi quy quyền (acceptance 5)

- Super Admin / Compliance Manager / Commissioning Manager (submit=1) mở draft → `can_approve=1` → thấy CTA.
- Commissioning User (create=1/submit=0) mở CÙNG biên bản → xem đủ, CTA **ẩn**, hint = "Bạn không đủ quyền duyệt giải nhiệm.". KHÔNG cấp/nới DocPerm — cờ do BE (`rbac.can`) quyết định.

### 13.6. Render/CTA gate test (`decommissionDetailCtaGate.test.ts`)

Matrix state × flag (mock `getDecommission`):
- (a) `can_approve=1` (draft, approver) → nút `cta-approve` render; click → gọi `approveDecommission(name)`.
- (b) `can_approve=0` + reason "Bạn không đủ quyền duyệt giải nhiệm." (Commissioning User) → KHÔNG nút; hint hiện chuỗi VI đó.
- (c) `can_approve=0` + reason "Hồ sơ giải nhiệm đã được duyệt." (Approved) → KHÔNG nút; badge "Đã duyệt".
- (d) Anti-dead-control: KHÔNG dựa `docstatus`/`workflow_state` để render nút (mock `docstatus=0` nhưng `can_approve=0` → vẫn KHÔNG nút).
- (e) Anti-PII: `responsible` email + `asset` Link-id KHÔNG xuất hiện trong DOM (render `responsible_name`/`asset_name`); KHÔNG raw EN status ('Draft'/'Approved') trong DOM.
- (f) Degrade: thiếu `can_approve` (undefined) → KHÔNG nút (an toàn).

*Hết file 06. §11 (entrypoint asset-detail) + §12 (danh sách /decommissions) là CHỐT cho vòng 2; §13 (chi tiết + duyệt) là CHỐT cho vòng 17. Wireframe / sitemap đầy đủ §1–§10 giữ làm Đợt 3.*
