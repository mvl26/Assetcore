# IMM-05 — Frontend Design

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-05 — Asset Document Repository |
| Template | 06_Frontend_Design v4.1+ |
| Ngày tạo | 2026-05-08 |
| Trạng thái | Live (Wave 1) |

---

## §1 — Sitemap

> Source of truth: `frontend/src/router/index.ts` (Section 4 — IMM-05 Document Repository)

| # | Route | Route name | Component thực tế | Mô tả |
|---|---|---|---|---|
| 1 | `/documents` | `DocumentManagement` | `views/document/DocumentManagement.vue` | Danh sách Tài liệu |
| 2 | `/documents/new` | `DocumentCreate` | `views/document/DocumentCreateView.vue` | Tạo Tài liệu mới |
| 3 | `/documents/view/:name` | `DocumentDetail` | `views/document/DocumentDetailView.vue` | Chi tiết Tài liệu |
| 4 | `/documents/requests` | `DocumentRequestList` | `views/document/DocumentRequestListView.vue` | Yêu cầu Hồ sơ |
| 5 | `/documents/asset/:assetId` | `DocumentsByAsset` | (redirect → `/documents?asset=:assetId`) | Deep-link từ QR |

**Không có route riêng cho dashboard (`/imm05/dashboard`)** — dashboard compliance chưa có route trong router hiện tại. Route `/imm05/documents` cũng không đúng — tất cả routes dùng `/documents` (không có prefix `/imm05`).

**Lưu ý tên route param:** Detail view dùng `/documents/view/:name` (có `/view/`), không phải `/documents/:name` thẳng.

---

## §2 — Sidebar Navigation

```typescript
// frontend/src/router/sidebar.ts — entry cho IMM-05
// ⚠️ Routes thực tế dùng /documents (không có prefix /imm05)
// Dashboard Compliance (/imm05/dashboard) chưa có route — planned Wave 3

{
  label: "Hồ sơ Tài liệu",
  icon: "folder",
  to: "/documents",
  roles: ["HTM Technician", "Biomed Engineer", "Tổ HC-QLCL",
          "Workshop Head", "VP Block2", "CMMS Admin", "Clinical Head"],
  children: [
    {
      label: "Danh sách Tài liệu",
      to: "/documents",
    },
    {
      label: "Yêu cầu Hồ sơ",
      to: "/documents/requests",
    },
    // Dashboard Compliance planned Wave 3 — route chưa implement
  ],
}
```

---

## §3 — Mockups (Pre-build)

### §3.a Mockup 1 — Danh sách Tài liệu

```
┌──────────────────────────────────────────────────────────────────────┐
│ Hồ sơ Tài liệu                                  [+ Tạo Tài liệu mới] │
│ ──────────────────────────────────────────────────────────────────── │
│  Filter:                                                              │
│  [Asset ▼]  [Nhóm ▼]  [Trạng thái ▼]  [Ngày hết hạn ▼]  [🔍 Tìm kiếm] │
│                                                                       │
│ ┌───────────────────────────────────────────────────────────────────┐ │
│ │ # │ Số hiệu       │ Loại               │ Tài sản      │ Trạng thái│ │
│ │   │               │                    │              │ Hết hạn   │ │
│ ├───────────────────────────────────────────────────────────────────┤ │
│ │ 1 │ NK-2026-0042  │ Giấy phép NK       │ AC-ASSET-... │ ✅ Active │ │
│ │   │               │                    │              │ 442 ngày  │ │
│ │ 2 │ CO-2025-12    │ Chứng nhận XX      │ AC-ASSET-... │ ⏳ Chờ duyệt│ │
│ │ 3 │ RAD-2024-001  │ Giấy phép bức xạ  │ AC-ASSET-... │ ⚠️ Hết hạn│ │
│ └───────────────────────────────────────────────────────────────────┘ │
│  ◀ 1 2 3 ... 7 ▶   Hiển thị 1-20/137                                  │
└──────────────────────────────────────────────────────────────────────┘
```

### §3.b Mockup 2 — Form Tạo Tài liệu mới

```
┌──────────────────────────────────────────────────────────────────┐
│ Tạo Tài liệu mới                               Status: [Draft ●] │
│ ──────────────────────────────────────────────────────────────── │
│ ┌─ Liên kết Thiết bị ─────────────────────────────────────────┐  │
│ │ Tài sản*:   [Tìm AC-ASSET...    ▼]   Phiếu Commissioning:   │  │
│ │ Model:      [Auto-fetch          ]   [Auto-fetch         ▼] │  │
│ │ Khoa:       [Auto-fetch          ]   ☐ Áp dụng toàn Model   │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ┌─ Phân loại Tài liệu ────────────────────────────────────────┐  │
│ │ Nhóm*:    [Legal              ▼]   Số hiệu*: [             ]│  │
│ │ Loại*:    [Giấy phép nhập... ▼]   Phiên bản: [1.0          ]│  │
│ └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ┌─ Thông tin Hiệu lực ────────────────────────────────────────┐  │
│ │ Ngày cấp*:    [📅 2026-01-15]   Cơ quan cấp*: [Bộ Y tế    ] │  │
│ │ Ngày hết hạn: [📅 2027-06-30]   Còn lại: 442 ngày           │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ┌─ File đính kèm ─────────────────────────────────────────────┐  │
│ │ 📎 [Chọn file...] hoặc kéo thả                               │  │
│ │ ⓘ Chấp nhận: PDF, JPG, PNG, DOCX (tối đa 25 MB)              │  │
│ └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│ ┌─ Phạm vi xem ───────────────────────────────────────────────┐  │
│ │ ⦿ Công khai (Public)     ○ Nội bộ (Internal_Only)            │  │
│ └─────────────────────────────────────────────────────────────┘  │
│ ──────────────────────────────────────────────────────────────── │
│  [Hủy]                              [Lưu Draft] [Gửi duyệt →]    │
└──────────────────────────────────────────────────────────────────┘
```

### §3.c Mockup 3 — Chi tiết Tài liệu (Active state)

```
┌──────────────────────────────────────────────────────────────────┐
│ DOC-AC-ASSET-2026-0001-2026-00001                                 │
│ Giấy phép nhập khẩu — NK-2026-0042                               │
│ ✅ Đang hiệu lực   🌐 Công khai   [Lịch sử] [Tải file] [Upload v2]│
│ ──────────────────────────────────────────────────────────────── │
│ Tài sản:        AC-ASSET-2026-0001 (Monitor Philips — ICU)        │
│ Nhóm:           Legal                                             │
│ Phiên bản:      1.0                                               │
│ Ngày cấp:       15/01/2026                                        │
│ Hết hạn:        30/06/2027  🟢 Còn 442 ngày                       │
│ Cơ quan cấp:    Bộ Y tế                                           │
│ File:           nk-2026-0042.pdf  [📥 Tải xuống]                  │
│                                                                   │
│ Phê duyệt bởi:  qlcl@hosp.vn    Ngày: 18/04/2026                 │
│ ──────────────────────────────────────────────────────────────── │
│ [Thông tin]   [Lịch sử thay đổi]                                  │
│                                                                   │
│  2026-04-18 10:00 | qlcl@hosp.vn | Pending Review → Active       │
│  2026-04-17 15:30 | ktv@hosp.vn  | Tạo mới Draft                  │
└──────────────────────────────────────────────────────────────────┘
```

### §3.d Mockup 4 — Dashboard Compliance

```
┌──────────────────────────────────────────────────────────────────┐
│ IMM-05 — Dashboard Compliance Tài liệu                           │
│ ──────────────────────────────────────────────────────────────── │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│ │ Active   │ │ Sắp hết  │ │ Đã hết   │ │ Thiếu    │            │
│ │  412     │ │  28      │ │  5       │ │  17 TB   │            │
│ │ tài liệu │ │ 90 ngày  │ │ hạn      │ │ hồ sơ    │            │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘            │
│                                                                   │
│ ┌─── Sắp hết hạn (90 ngày) ──────────┐ ┌── Theo khoa ────────┐  │
│ │ Loại              Thiết bị   Còn   │ │ ICU  ████████ 92%   │  │
│ │ CN hiệu chuẩn     AC-...-001    7d │ │ OR   ██████   78%   │  │
│ │ GP nhập khẩu      AC-...-014   14d │ │ ER   ████     65%   │  │
│ │ CN ĐK lưu hành    AC-...-022   30d │ │ CT   ██       42%   │  │
│ └─────────────────────────────────────┘ └────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### §3.e Screenshot spec (Post-build)

| Màn hình | File | Breakpoint | Ghi chú |
|---|---|---|---|
| Document List | `screenshots/imm05-list.png` | 1440px | Filter active + pagination |
| Document Create | `screenshots/imm05-create.png` | 1440px | Form điền đầy đủ |
| Document Detail Active | `screenshots/imm05-detail-active.png` | 1440px | Badge xanh + countdown |
| Asset Documents Tab | `screenshots/imm05-asset-tab.png` | 1440px | Compliance bar + grouped |
| Document Request Modal | `screenshots/imm05-request-modal.png` | 1440px | Modal open |
| Exempt Modal | `screenshots/imm05-exempt-modal.png` | 1440px | Modal với warning text |

### §3.f Filter "Ngày hết hạn" + KPI drill "Đã hết hạn" — 1 SoT (BR-05-16)

> Source: `frontend/src/views/document/documentFilters.ts` (pure builders) + dashboard tile.

**Dropdown EXPIRY_OPTIONS** (giữ nguyên 5 lựa chọn, KHÔNG đổi label):

| value | label | Filter gửi BE (`list_documents`) |
|---|---|---|
| `''` | Mọi hết hạn | `{}` |
| `'expired'` | Đã hết hạn | **`{ expiry_status: 'expired' }`** ← đổi (cũ: `{workflow_state:'Expired'}`) |
| `'30'` | Trong 30 ngày | `{ workflow_state:'Active', expiry_date:['between',[today, today+30]] }` |
| `'60'` | Trong 60 ngày | `{ ..., today+60 }` |
| `'90'` | Trong 90 ngày | `{ ..., today+90 }` |

**Quy tắc (đo bằng INV-EXP-1):**
- `buildExpiryFilter('expired')` **và** `buildKpiFilter('expired')` PHẢI cùng trả `{ expiry_status: 'expired' }` (marker semantic — BE dịch sang `EXPIRED_FILTER`). **KHÔNG còn literal `{ workflow_state: 'Expired' }`** ở 2 hàm này (grep-guard).
- Tile KPI "Đã hết hạn" (`KPI_FILTERS[kind='expired']`) **vẫn `clickable: true`** — click dẫn về `list_documents({expiry_status:'expired'})`, KHÔNG dead-end. Số trên tile (`expired_not_renewed`) == số dòng list sau khi áp filter (cùng SoT).
- Dropdown chọn "Đã hết hạn" và click tile **cùng** một đích lọc (1 SoT) → không divergence.
- No-leak: label hiển thị "Đã hết hạn" (VI), KHÔNG rò `expired`/`Expired`/raw-state ra UI.

**Counterexample (acceptance):** asset có 1 doc Active, `expiry_date=today-5`, `is_expired=1` → tile "Đã hết hạn" đếm ≥1 VÀ click tile → list chứa đúng doc đó. (Trước fix: list 0 dòng vì lọc dead-state `Expired`.)

---

## §4 — Components

### §4.1 Component Catalog

| Component | File | Props | Mô tả |
|---|---|---|---|
| `DocumentStatusBadge` | `components/imm05/DocumentStatusBadge.vue` | `state: DocumentWorkflowState` | Badge màu theo workflow state |
| `ExpiryCountdown` | `components/imm05/ExpiryCountdown.vue` | `days: number \| null` | Countdown chip màu theo ngưỡng |
| `VisibilityBadge` | `components/imm05/VisibilityBadge.vue` | `visibility: DocumentVisibility` | 🌐 Public / 🔒 Internal |
| `DocumentRequestModal` | `components/imm05/DocumentRequestModal.vue` | `assetRef: string`, `show: boolean` | Modal tạo Document Request |
| `ExemptModal` | `components/imm05/ExemptModal.vue` | `assetRef: string`, `show: boolean` | Modal đánh dấu Exempt NĐ98 |
| `AssetDocumentsTab` | `components/imm05/AssetDocumentsTab.vue` | `assetRef: string` | Tab embed trong Asset Detail |
| `ComplianceProgressBar` | `components/imm05/ComplianceProgressBar.vue` | `pct: number`, `status: string` | Progress bar + % text |

### §4.2 `DocumentStatusBadge` — spec

> **Lưu ý:** Workflow state values dùng **space** (`Pending Review`) — đồng bộ giữa `services/imm05.py` class `DocState`, workflow fixture `imm_05_document_workflow.json`, và `stores/imm05.ts`.

```typescript
// Props
interface DocumentStatusBadgeProps {
  state: DocumentWorkflowState;
}

// DocState values (ground truth từ services/imm05.py).
// BR-05-16: KHÔNG có EXPIRED — "hết hạn" là thuộc tính dẫn xuất (is_expired),
// hiển thị qua ExpiryCountdown (badge đỏ "Đã hết hạn"), KHÔNG phải workflow_state.
class DocState {
  DRAFT = "Draft"
  PENDING_REVIEW = "Pending Review"  // space, không phải underscore
  ACTIVE = "Active"
  ARCHIVED = "Archived"
  REJECTED = "Rejected"
}

// Badge mapping — 5 live state từ DocState. "Expired" = declared-dead terminal
// (không xuất hiện qua flow — ADR-IMM-05-02); nếu gặp legacy → fallback badge default.
const BADGE_MAP: Record<string, { label: string; class: string }> = {
  "Draft":          { label: "Nháp",           class: "badge-gray" },
  "Pending Review": { label: "Chờ duyệt",      class: "badge-yellow" },
  "Active":         { label: "Đang hiệu lực",  class: "badge-green" },
  "Rejected":       { label: "Bị từ chối",     class: "badge-red" },
  "Archived":       { label: "Đã lưu trữ",     class: "badge-gray" },
  // Legacy fallback CHỈ để hiển thị record cũ (pre-Vòng 19) nếu còn sót — KHÔNG
  // tạo mới state này; tình trạng hết hạn dùng ExpiryCountdown (is_expired).
  "Expired":        { label: "Đã hết hạn",     class: "badge-red" },
};
```

> **Cờ "đã hết hạn" trên hàng list** dùng `ExpiryCountdown` (`days_until_expiry < 0` → đỏ "Đã hết hạn"), độc lập với badge workflow_state. Một hàng có thể đồng thời badge "Đang hiệu lực" (Active) + cờ đỏ "Đã hết hạn" (quá hạn) — đúng ngữ nghĩa BR-05-16.

### §4.3 `ExpiryCountdown` — spec

```typescript
interface ExpiryCountdownProps {
  days: number | null; // null = no expiry
}

// Color logic
function getExpiryClass(days: number | null): string {
  if (days === null) return "text-gray";  // Không có ngày hết hạn
  if (days < 0)      return "text-red";   // Đã hết hạn
  if (days <= 30)    return "text-orange";// Nguy hiểm
  if (days <= 90)    return "text-yellow";// Cảnh báo
  return "text-green";                    // Bình thường
}
```

---

## §5 — Pinia Store

> Source of truth: `frontend/src/stores/imm05.ts`

**File:** `frontend/src/stores/imm05.ts` — export `useImm05Store`

Store dùng **Composition API** pattern (`defineStore('imm05', () => {...})`), không phải Options API.

**State refs thực tế:**
```typescript
const documents = ref<AssetDocumentItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const pagination = ref<Pagination>({...})
const currentFilters = ref<DocumentFilters>({})
const assetDocuments = ref<Record<string, AssetDocumentItem[]>>({})
const assetCompletenessPct = ref(0)
const assetDocumentStatus = ref('')      // "Complete" | "Incomplete"
const missingRequired = ref<string[]>([])
const dashboardStats = ref<DashboardStats | null>(null)
const dashboardLoading = ref(false)
const documentRequests = ref<DocumentRequest[]>([])
const expiringDocs = ref<AssetDocumentItem[]>([])
const currentDocument = ref<AssetDocumentDetail | null>(null)
```

**Getters thực tế:**
- `totalDocuments` — `pagination.total`
- `pendingReviewDocs` — filter `workflow_state === 'Pending Review'`
- `expiredDocs` — filter **derived** (BR-05-16): `expiry_date != null && expiry_date < today && !['Archived','Rejected'].includes(workflow_state)` — **KHÔNG** `workflow_state === 'Expired'` (dead-state). Mirror predicate `EXPIRED_FILTER` của BE. *(Self-Correction Vòng 19.)*
- `kpis` — from `dashboardStats.kpis`
- `openRequests` — filter `status === 'Open' || 'Overdue'`

**Actions thực tế:** `fetchDocuments`, `fetchAssetDocuments`, `fetchDashboardStats`, `approveDocument`, `rejectDocument`, `createRequest`, `fetchDocumentRequests`, `fetchExpiringDocuments`, `fetchDocument`, `updateDocument`, `createDocument`, `fetchDocumentHistory`, `changePage`, `clearError`

**Lưu ý types:** `imm05.ts` trong `frontend/src/types/` chỉ là re-export từ `@/api/imm05`. Types thực tế (`AssetDocumentItem`, `AssetDocumentDetail`, `DocumentFilters`, `DocumentRequest`, `DashboardStats`, `Pagination`) được định nghĩa trong `frontend/src/api/imm05.ts`.

---

## §6 — Vue Query Keys & API Integration

### §6.1 Query key factory

```typescript
// frontend/src/api/imm05.ts

export const imm05Keys = {
  all: ["imm05"] as const,
  lists: () => [...imm05Keys.all, "list"] as const,
  list: (filters: object) => [...imm05Keys.lists(), filters] as const,
  detail: (name: string) => [...imm05Keys.all, "detail", name] as const,
  history: (name: string) => [...imm05Keys.all, "history", name] as const,
  assetDocs: (assetRef: string) => [...imm05Keys.all, "asset", assetRef] as const,
  dashboard: () => [...imm05Keys.all, "dashboard"] as const,
  compliance: () => [...imm05Keys.all, "compliance"] as const,
  requests: (assetRef?: string) => [...imm05Keys.all, "requests", assetRef] as const,
};
```

### §6.2 Invalidate rules

| Action | Invalidate keys |
|---|---|
| Tạo tài liệu | `imm05Keys.lists()`, `imm05Keys.assetDocs(asset_ref)` |
| Approve / Reject | `imm05Keys.detail(name)`, `imm05Keys.lists()`, `imm05Keys.assetDocs(asset_ref)`, `imm05Keys.dashboard()` |
| Archive auto | `imm05Keys.assetDocs(asset_ref)` |
| mark_exempt | `imm05Keys.assetDocs(asset_ref)`, `imm05Keys.compliance()` |
| create_document_request | `imm05Keys.requests(asset_ref)` |
| Scheduler (expiry) | `imm05Keys.dashboard()`, `imm05Keys.compliance()` |

### §6.3 `useApi().run()` pattern

```typescript
// Approve document — mutation với auto-toast
const { run: approveDoc, loading: approving } = useApi();

async function handleApprove(name: string) {
  await approveDoc({
    method: "assetcore.api.imm05.approve_document",
    args: { name },
    onSuccess: (data) => {
      // Frappe toast tự hiện "✅ Đã phê duyệt"
      queryClient.invalidateQueries({ queryKey: imm05Keys.detail(name) });
      router.push(`/imm05/documents/${name}`);
    },
    onError: (err) => {
      // Toast lỗi tiếng Việt từ err.error
    },
    successMessage: "Đã phê duyệt tài liệu.",
    loadingMessage: "Đang phê duyệt...",
  });
}
```

---

## §7 — Ngôn ngữ & UX Rules

### §7.1 Nguyên tắc ngôn ngữ

- 100% tiếng Việt trong UI: labels, buttons, toast, error messages, placeholder
- Entity hiển thị: `"DOC-AC-ASSET-2026-0001-2026-00001"` (technical ID) + `"Giấy phép nhập khẩu"` (doc_type_detail)
- Format ngày: `dd/MM/yyyy` — hiển thị; `yyyy-MM-dd` — API transfer

### §7.2 Vocabulary mapping

| Tiếng Việt | Technical value |
|---|---|
| Hồ sơ Tài liệu | Asset Document |
| Yêu cầu Tài liệu | Document Request |
| Loại Tài liệu Bắt buộc | Required Document Type |
| Đang hiệu lực | Active |
| Chờ duyệt | Pending Review |
| Đã lưu trữ | Archived |
| Đã hết hạn | `expiry_status='expired'` (thuộc tính dẫn xuất, **không** phải workflow_state — BR-05-16) |
| Miễn đăng ký | Exempt (NĐ98) |
| Công khai | Public |
| Nội bộ | Internal_Only |

### §7.3 Cascade fields

| Field A (trigger) | Field B (reset) | Logic |
|---|---|---|
| `asset_ref` | `model_ref`, `clinical_dept` | fetch_from server khi chọn asset |
| `doc_category` | `doc_type_detail` (suggestion list) | Load từ Required Document Type theo category |
| `doc_category = Legal` | `expiry_date` (required), `issuing_authority` (required) | VR-04, VR-07 enforce FE |
| `version != "1.0"` | `change_summary` (required) | VR-09 enforce FE |
| `is_exempt = 1` | `exempt_reason` (required), `exempt_proof` (required) | VR-10 enforce FE |

```typescript
// Vue watch pattern cho cascade asset_ref → model_ref, clinical_dept
watch(() => form.asset_ref, async (newVal) => {
  if (!newVal) {
    form.model_ref = "";
    form.clinical_dept = "";
    return;
  }
  const asset = await fetchAsset(newVal);
  form.model_ref = asset.item_code ?? "";
  form.clinical_dept = asset.location ?? "";
});

// Watch doc_category → conditional required
watch(() => form.doc_category, (cat) => {
  const isLegalOrCert = ["Legal", "Certification"].includes(cat);
  form._expiryRequired = isLegalOrCert;
  form._authorityRequired = cat === "Legal";
});
```

### §7.4 Input tight rules

| Field | Input type | Validation |
|---|---|---|
| `asset_ref` | Link picker | Must exist in AC Asset |
| `doc_category` | Select (closed list) | Enum: Legal/Technical/Certification/Training/QA |
| `doc_type_detail` | Autocomplete từ Required Document Type | Free text allowed |
| `issued_date` | Date picker | ≤ today |
| `expiry_date` | Date picker | > issued_date (VR-01) |
| `file_attachment` | File upload | ext IN {.pdf, .jpg, .jpeg, .png, .docx}, max 25 MB (VR-08) |
| `version` | Data | Pattern: `^\d+\.\d+$` |
| `exempt_reason` | Textarea | min 30 ký tự khi is_exempt=1 |

**Confirm modal** trước khi:
- Approve: "Phê duyệt tài liệu này sẽ tự động lưu trữ phiên bản cũ. Tiếp tục?"
- mark_exempt: "Hành động này tạo tài liệu Active với is_exempt=1 và unblock GW-2. Xác nhận?"

---

## §7.5 — `DocumentDetailView` — CTA gating do SERVER lái (GATE-8 / LL-FE-51)

`DocumentDetailView.vue` render nút CTA workflow theo **server** (`get_document` phát `allowed_transitions` + `can_approve`, xem 05 §2.2 · 04 §3.4 · ADR-IMM-05-01), KHÔNG hardcode `doc.workflow_state === 'X'`.

**Computed nguồn:**
```ts
const allowedTransitions = computed<string[]>(() => doc.value?.allowed_transitions ?? [])
const canApprove = computed<boolean>(() => doc.value?.can_approve === 1)
```

**Bảng gate nút CTA transition (điều kiện render):**

| Nút | Điều kiện render (SAU đổi) | Nhãn | canApprove? |
|---|---|---|:---:|
| Gửi duyệt / Gửi lại | `allowedTransitions.includes('Pending Review')` | `workflow_state === 'Rejected' ? 'Gửi lại' : 'Gửi duyệt'` (nhãn display-only) | — |
| Phê duyệt | `allowedTransitions.includes('Active') && canApprove` | "Duyệt tài liệu" | ✓ |
| Từ chối | `allowedTransitions.includes('Rejected') && canApprove` | "Từ chối" | ✓ |
| Lưu trữ / Hủy bỏ | `allowedTransitions.includes('Archived') && canApprove` | `workflow_state === 'Draft' ? 'Hủy bỏ' : 'Lưu trữ'` (nhãn display-only) | ✓ |

> **Gộp "Gửi duyệt"↔"Gửi lại":** cả hai gọi `submitForReview` và cùng đích `Pending Review` → MỘT nút, gate `allowedTransitions.includes('Pending Review')`, nhãn chọn theo state (display-only, cho phép). KHÔNG dùng 2 nút gate bằng `workflow_state === 'Draft'` / `=== 'Rejected'` (điều kiện render CTA cấm dùng `workflow_state ===`).

**Quy tắc (khớp acceptance):**
- **0 nút CTA transition** (Gửi duyệt/Phê duyệt/Từ chối/Gửi lại/Lưu trữ/Hủy bỏ) còn gate bằng `doc.workflow_state === 'X'`. Tất cả gate bằng `allowedTransitions.includes(<next_state>)`.
- `workflow_state === '…'` CHỈ được phép ở **nhãn hiển thị read-only** (label state terminal "Đã hết hạn"/"Đã lưu trữ"; label "Gửi duyệt"↔"Gửi lại"; label "Lưu trữ"↔"Hủy bỏ") — TUYỆT ĐỐI KHÔNG ở điều kiện render nút.
- **Hết false-permissive:** user thiếu `doc.approve` (canApprove=false) KHÔNG còn thấy nút Phê duyệt/Từ chối/Lưu trữ trên phiếu Pending Review (trước đây thấy → bấm mới 403). User có `doc.approve` (Compliance Manager) hoặc AssetCore Super Admin thấy + bấm Phê duyệt → phiếu chuyển Active.

**Ngoài scope thay đổi này (KHÔNG phải nút transition — giữ nguyên gate hiện tại):**
- **Chỉnh sửa / Sửa lại** (`canEdit` = state ∈ {Draft, Rejected}): là toggle edit-mode field-mutation, KHÔNG phải state transition → giữ `canEdit`.
- **Tải lên phiên bản mới** (state ∈ {Active, Expired}): điều hướng tạo tài liệu MỚI (không transition phiếu hiện tại) → giữ nguyên.
- **Nhãn terminal read-only** (`isTerminalState` = state ∈ {Archived, Expired}): display-only, được phép dùng `workflow_state ===`.

**Test FE (vitest) bắt buộc:** file test CTA-gating mới (`views/document/documentDetailCtaGating.test.ts`) assert theo state × canApprove:
- Pending Review + `can_approve=0` → KHÔNG có nút "Duyệt tài liệu"/"Từ chối".
- Pending Review + `can_approve=1` → CÓ cả hai nút.
- Draft → có "Gửi duyệt" + "Hủy bỏ" (Hủy bỏ chỉ khi canApprove=1); KHÔNG có "Phê duyệt".
- Rejected → có "Gửi lại"; Active → có "Lưu trữ" (khi canApprove=1); Archived/Expired → 0 nút transition, hiện nhãn read-only.

---

## §8 — Empty / Error / Loading States

| Scenario | Loại | Copy |
|---|---|---|
| Document List trống | Empty | "Chưa có tài liệu nào. Nhấn [+ Tạo Tài liệu mới] để bắt đầu." |
| Asset Documents Tab trống | Empty | "Asset chưa có hồ sơ. Upload tài liệu đầu tiên để theo dõi compliance." |
| Dashboard không có dữ liệu | Empty | "Không có dữ liệu compliance. Vui lòng kiểm tra kết nối hoặc thử lại sau." |
| Document Requests trống | Empty | "Không có yêu cầu tài liệu nào." |
| API lỗi FORBIDDEN | Error | "Bạn không có quyền xem tài liệu này." |
| API lỗi NOT_FOUND | Error | "Không tìm thấy tài liệu. Có thể đã bị xóa hoặc lưu trữ." |
| API lỗi INVALID_STATE | Error | Hiển thị `response.error` (tiếng Việt từ server) |
| Đang tải danh sách | Loading | Skeleton loader 5 rows |
| Đang phê duyệt | Loading | Spinner trên nút [Approve] + disabled |

---

## §9 — Accessibility

| Yêu cầu | Implementation |
|---|---|
| Keyboard navigation | Tab order qua form fields, Enter submit, Escape đóng modal |
| ARIA labels | Buttons, status badges có `aria-label` tiếng Việt |
| Color contrast | Badge màu đảm bảo WCAG AA (4.5:1) — kiểm tra ExpiryCountdown |
| Screen reader | Toast dùng `role="alert"`, modal dùng `role="dialog"` với `aria-labelledby` |
| Responsive | Desktop ≥ 1280px: 2 col; Tablet 768-1279px: 1 col; Mobile < 768px: tab nav |
| Focus trap | Modal (DocumentRequestModal, ExemptModal) trap focus khi mở |
| Error announcement | VR failures announced via `aria-live="polite"` |

---

## §10 — Print Spec

| Màn hình | Nội dung in | Format |
|---|---|---|
| Document Detail | Thông tin tài liệu + trạng thái + lịch sử | A4 portrait, PDF |
| Asset Documents Tab | Bảng tóm tắt compliance theo category | A4 landscape, PDF |
| Dashboard | KPI + expiry timeline (90 ngày) | A4 landscape, PDF |

Print trigger: nút [In] ở header. Dùng `@media print` CSS — ẩn filter, sidebar, action buttons.

---

## DoD Checklist

- [x] Sitemap 7 routes/modals đầy đủ
- [x] Sidebar nav config TypeScript
- [x] 4 ASCII mockups (list, create form, detail, dashboard)
- [x] Screenshot spec table
- [x] 7 components với props spec
- [x] DocumentStatusBadge + ExpiryCountdown spec
- [x] Pinia store đầy đủ state + getters + persist
- [x] Vue Query key factory + invalidate rules
- [x] useApi().run() pattern example
- [x] Language + vocabulary rules
- [x] Cascade fields với Vue watch pattern
- [x] Input tight rules + confirm modals
- [x] Empty/Error/Loading copy (8 scenarios)
- [x] Accessibility checklist
- [x] Print spec
