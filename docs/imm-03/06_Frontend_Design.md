# 06 — Thiết kế Frontend — IMM-03 Đánh giá Nhà cung cấp & Quyết định Mua sắm

> ✅ Module LIVE — Wave 2. Vue components, Pinia store, TypeScript API client đã implement. Ground truth: `frontend/src/views/procurement/` (KHÔNG phải `views/imm03/`).

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-03 — Vendor Evaluation & Procurement Decision |
| Phiên bản | 0.1.0 |
| Ngày | 2026-05-18 |
| Trạng thái | LIVE — Wave 2 (fix view path: `views/procurement/` không phải `views/imm03/`) |

---

## I. Sitemap & Routes (LIVE)

> ✅ Routes thực tế. Ground truth: `frontend/src/router/index.ts` + `frontend/src/views/procurement/`.

| Route | Component (path: `frontend/src/views/procurement/`) | Mô tả |
|---|---|---|
| `/vendor-profiles` | `VendorProfileListView.vue` | Danh sách Vendor Profile (qua `list_vendor_profiles`) |
| `/vendor-profiles/:id` | `VendorProfileDetailView.vue` | Chi tiết Vendor Profile 4 tab + add cert |
| `/vendor-evaluations` | `VendorEvalListView.vue` | Danh sách Vendor Evaluation |
| `/vendor-evaluations/:id` | `VendorEvalDetailView.vue` | Chi tiết Evaluation (tabs Candidates/Scoring/Summary) |
| `/approved-vendors` | `AvlListView.vue` | Danh sách AVL |
| `/procurement-decisions` | `DecisionListView.vue` | Danh sách Procurement Decision |
| `/procurement-decisions/:id` | `DecisionDetailView.vue` | Chi tiết Decision (Award form + Contract recorder) |

**Spec-only (chưa có code FE):** AvlDetail, ScorecardView (radar), SupplierAuditDetail, Imm03Dashboard (KPI tiles). Endpoint `dashboard_kpis`, `get_vendor_scorecard` đã sẵn ở BE.

---

## II. Component Catalog

> ✅ = đã implement (Wave 2 LIVE); _(Spec only)_ = chưa có code.

### II.1 `VendorProfileListView.vue` ✅ LIVE (`frontend/src/views/procurement/VendorProfileListView.vue`)

Wired tới `listVendorProfiles({avl_status, device_category, min_score, audit_overdue}, page=1, page_size=100)`. Hiển thị badge `imm_avl_status` (Approved/Conditional/Suspended/Expired/Not Applicable), điểm `imm_overall_score`, count `cert_count` + `cert_expiring_soon`.

```
Nhà cung cấp                                           [+ Tạo profile]
───────────────────────────────────────────────────────────────────────
Filter: [AVL Status▾] [Category▾] [Score ≥▾] [Audit quá hạn ⏰]   🔍
───────────────────────────────────────────────────────────────────────
┌─────────────────────────────────────────────────────────────────────┐
│  VINAMED      │ Vinamed JSC     │ Imaging, Life  │ ✓ Approved 4.3★ │
│               │ MST: 030123...  │ Support        │ Audit: 2026-01  │
│               │ Cert: ISO 9001✓ │                │ Next: 2027-01   │
│               │ ISO 13485 ⚠30d  │                │                 │
├─────────────────────────────────────────────────────────────────────┤
│  HAMILTON-VN  │ Hamilton VN     │ Imaging        │ ⚠ Conditional   │
│               │ MST: 030456...  │                │ 3.8★ Audit ⏰   │
└─────────────────────────────────────────────────────────────────────┘
  Trang 1/2  [←] [→]                              Tổng: 24 vendors
```

**Props:** Không có (fetch from store)
**Emits:** `select(name: string)`

---

### II.2 `VendorProfileDetailView.vue` ✅ LIVE (`frontend/src/views/procurement/VendorProfileDetailView.vue`)

Wired tới `getVendorProfile(id)` + `addVendorCert(...)`. Hiển thị: AC Supplier core (`supplier_name`, `country`, `tax_id`, `email_id`, `phone`...), custom fields IMM (`imm_avl_status`, `imm_avl_categories`, `imm_overall_score`, `imm_last_audit_date`, `imm_next_audit_date`), child table `imm_certifications`, derived `avl_entries`, `scorecard_history`.

```
← Danh sách                   VINAMED · Vinamed JSC · ★★★★ 4.3 · ✓ Approved
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [1. Hồ sơ]  [2. Chứng chỉ]  [3. AVL]  [4. Scorecard & Audit]

  Tab 1: Hồ sơ
    Tên pháp lý: CTCP Vinamed     MST: 0301234567    Quốc gia: Việt Nam
    Đại diện: Nguyễn Văn A       Điện thoại: 0901...  Email: a@vinamed.vn
    Nhóm thiết bị: Imaging, Life Support
    Xếp loại tài chính: A
    Phạm vi cung ứng: [Long text...]

  Tab 2: Chứng chỉ
    ┌───────────┬────────────────┬───────────┬────────────┬────────────┐
    │ Loại      │ Số chứng chỉ  │ Cơ quan CP│ Hết hạn    │ Trạng thái │
    ├───────────┼────────────────┼───────────┼────────────┼────────────┤
    │ ISO 9001  │ ISO-9001-2024  │ BV        │ 2027-01-15 │ ✓ Active   │
    │ ĐKLH BYT  │ ĐKLH-456-BYT  │ BYT       │ 2026-05-30 │ ⚠ 22d     │
    └───────────┴────────────────┴───────────┴────────────┴────────────┘
    [+ Thêm chứng chỉ]

  Tab 3: AVL
    [Imaging]  ✓ Approved  2026-05-01 → 2028-04-30  VP Block1  [Chi tiết]
    ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░   Còn 722 ngày
    [+ Tạo AVL mới]

  Tab 4: Scorecard & Audit
    Trendline overall_score 5 quý:  Q2/25(3.9) Q3/25(4.1) Q4/25(4.2) Q1/26(4.1) Q2/26(4.3)
    [Xem Scorecard đầy đủ]
    Audit history:
      2026-01-15  Periodic  Pass    0 finding   [Chi tiết]
      2025-01-10  Periodic  Pass    1 Minor      [Chi tiết]
```

**Props:** `name: string`

---

### II.3 `VendorEvalDetailView.vue` ✅ (tên cũ trong spec: `EvaluationDetail.vue`)

```
← Danh sách                          VE-26-00120 · TS-26-00045
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stepper: [Draft] ▶ [Open RFQ] ▶ [Quotation Received] ▶ [Evaluated]
                              (current)

  [1. Candidates & RFQ]  [2. Chấm điểm]  [3. Tổng hợp]

  Tab 1:
    Phương án: Đấu thầu rộng rãi (cần ≥ 3 candidate)
    ┌──────────────┬────────┬─────────────────┬──────────┬────────────┐
    │ Vendor       │ AVL?   │ Báo giá          │ Hiệu lực │ Giá        │
    ├──────────────┼────────┼─────────────────┼──────────┼────────────┤
    │ Vinamed      │ ✓      │ QT-2026-001     │ 60 ngày  │ 2.1 tỷ VND │
    │ Hamilton VN  │ ⚠      │ QT-2026-002     │ 60 ngày  │ 1.9 tỷ VND │
    │ Mindray VN   │ ✓      │ QT-2026-003     │ 45 ngày  │ 1.4 tỷ VND │
    └──────────────┴────────┴─────────────────┴──────────┴────────────┘
    [+ Thêm candidate]   [Open RFQ]   [Upload bulk quotation]

  Tab 2: Chấm điểm
    Group: [Technical ▾] (HTM Engineer)
    ┌──────────────────┬──────────┬──────────┬──────────┐
    │ Tiêu chí         │ Vinamed  │ Hamilton │ Mindray  │
    ├──────────────────┼──────────┼──────────┼──────────┤
    │ Spec match (35%) │    5     │    4     │    3     │
    │ Brand (35%)      │    4     │    4     │    4     │
    │ Local sup (30%)  │    4     │    5     │    3     │
    └──────────────────┴──────────┴──────────┴──────────┘
    Sticky panel phải: Weighted scores: Vinamed 4.32 | Hamilton 4.18 | Mindray 3.45

  Tab 3: Tổng hợp
    ★ Đề xuất: Vinamed (4.32) — highest weighted score
    Compare table 3 vendor side-by-side (price / score / delivery / warranty)
    [Tạo Procurement Decision →]
```

**Props:** `name: string`

---

### II.4 `DecisionDetailView.vue` ✅ (tên cũ trong spec: `DecisionDetail.vue`)

```
← Danh sách                  PD-26-00045 · TS-26-00045 · PP-26-001
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stepper: [Draft]▶[Method]▶[Negotiation]▶[Recommended]▶[Pending]▶[Awarded]▶[Signed]▶[PO]
                                                        (current)

  Block "Phương án mua sắm"
    Phương án: [Đấu thầu rộng rãi ▾]    ✓ Hợp lệ với gói 6 tỷ + ≥ 3 báo giá
    Cơ sở pháp lý: [disabled với Đấu thầu rộng rãi]

  Block "Nhà cung cấp trúng thầu"
    Ứng viên đề xuất: [Vinamed (4.32) ▾] → Nhà cung cấp: Vinamed JSC (auto fill)
    Giá trúng thầu: [2,000,000,000 VND]
    Envelope budget: 2,500,000,000 VND
    ████████████████████░░░░░  80%  ✓ Trong ngưỡng
    Nguồn vốn: [NSNN ▾]   Chứng từ: [upload]

  Block "Phê duyệt"
    Người phê duyệt: [vp.block1@... ▾]
    Hợp đồng: [upload PDF]

Action footer (theo state + role):
  [Trình BGĐ]    (PTP Khối 1, state Award Recommended)
  [Awarded ✓]    (VP Block1, state Pending Approval)
  [Huỷ]         (Dept Head, trước Awarded)

Sau Awarded:
  Tab phụ "AC Purchase" → AC-PUR-2026-00112 [Click để xem]
```

**Props:** `name: string`
**Computed:** `isEditable`, `availableActions` (theo role + state)

---

### II.5 `AvlDetail.vue` _(Spec only — AvlListView.vue đã implement nhưng AvlDetail chưa có)_

```
← Danh sách AVL           AVL-2026-00045 · VINAMED · Imaging
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trạng thái: ✓ Approved
Phê duyệt bởi: VP Block1 ngày 2026-05-15
Hiệu lực: 2026-05-01 → 2028-04-30  (2 năm)
Còn: 722 ngày

Timeline:
  May 2026          May 2027          Apr 2028
  ├─────────────────────────────────────────┤
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░
  Hiện tại                        Hết hạn
  ⚠ Cảnh báo 60 ngày: 2028-02-28
  ⚠ Cảnh báo 30 ngày: 2028-03-30

[Đình chỉ AVL]  (QA Risk / VP Block1)
```

**Props:** `name: string`

---

### II.6 `ScorecardView.vue` _(Spec only)_

```
Vendor: [VINAMED ▾]    Kỳ: [2026 ▾] [Q2 ▾]    [Tải PDF]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Overall: 4.3 ★★★★   Xếp hạng: #2/24 vendors

Radar chart 5 chiều:
              Delivery
            4.5
           ╱     ╲
  Comp 4.0          Quality 4.4
           ╲     ╱
     Spare 4.1  Aftersales 4.2

Trendline 5 quý:
  Q2/25  Q3/25  Q4/25  Q1/26  Q2/26
   3.9    4.1    4.2    4.1    4.3  ↑

Chi tiết dimension:
┌─────────────┬──────┬─────────┬────────────┬──────────┬──────────────┐
│ Chiều       │ Wt % │ Raw val │ Normalized │ Weighted │ Nguồn        │
├─────────────┼──────┼─────────┼────────────┼──────────┼──────────────┤
│ Delivery    │ 20%  │ 94.5%   │ 4.5        │ 0.90     │ IMM-04       │
│ Quality     │ 25%  │ 0.5% NC │ 4.4        │ 1.10     │ IMM-04/IMM-10│
│ Aftersales  │ 20%  │ 18.3h   │ 4.2        │ 0.84     │ IMM-09       │
│ Spare       │ 15%  │ 97.0%   │ 4.1        │ 0.62     │ IMM-15       │
│ Compliance  │ 20%  │ 0 NC    │ 4.0        │ 0.80     │ IMM-10       │
└─────────────┴──────┴─────────┴────────────┴──────────┴──────────────┘
```

**Props:** `supplier?: string, year?: number, quarter?: number`

---

### II.7 `Imm03Dashboard.vue` _(Spec only — KPI data available via dashboard_kpis endpoint)_

```
IMM-03 Dashboard — Mua sắm & Nhà cung cấp          Kỳ: [2026-Q2 ▾]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KPI Tiles:
┌──────────────┬──────────────┬──────────────┬──────────────┐
│ Lead time    │ AVL coverage │ Avg score    │ AVL pick rate│
│ Eval→Awarded │              │              │              │
│  55d / 60d   │  82% / 80%   │  4.1 / 4.0  │  92% / 90%  │
│  ✓ green     │  ✓ green     │  ✓ green     │  ✓ green     │
├──────────────┼──────────────┼──────────────┼──────────────┤
│ Audit compl. │ Supplier NC  │ Cost saving  │              │
│  97% / 95%   │  0.8% ↓      │  7.2% / 5%  │              │
│  ✓ green     │  ✓ trend OK  │  ✓ green     │              │
└──────────────┴──────────────┴──────────────┴──────────────┘

Charts:
  [Funnel: Eval Draft→Awarded→PO Issued]   [AVL expiry timeline 6 tháng tới]

  [Vendor scorecard ranking top 10]        [NC heatmap Vendor × Tháng]
```

---

### II.8 `SupplierAuditDetail.vue` _(Spec only)_

```
← Danh sách               SA-26-00012 · DRAGER-VN · Periodic
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ngày audit: 2026-05-10    Kiểm toán viên: QA Risk Team
Kết quả: ⚠ Conditional   CAPA cần: Có

Phát hiện:
┌──────┬────────────┬─────────────────────────────────┬─────────┬──────────┐
│ Mức  │ Danh mục   │ Mô tả                           │ Chủ sở  │ Hạn      │
├──────┼────────────┼─────────────────────────────────┼─────────┼──────────┤
│ Minor│ Documentation│ Thiếu batch record 2 lô        │ drager@ │ 2026-06-10│
└──────┴────────────┴─────────────────────────────────┴─────────┴──────────┘
[+ Thêm finding]     [Submit Audit]
```

---

## III. Atomic Components

| Component | Props | Emits | Mô tả |
|---|---|---|---|
| `<VendorAvlBadge>` | `status: AVLStatus` | — | Badge màu theo status |
| `<CertTable>` | `certs: VendorCert[]`, `editable: bool` | `add`, `remove` | Bảng cert với badge expiry |
| `<AvlTimeline>` | `avl: AVLEntry` | — | Timeline bar + cảnh báo ngày |
| `<EvalCandidateGrid>` | `evaluation: VendorEvaluation` | `addCandidate`, `removeCandidate` | Candidate + AVL badge + quotation |
| `<ScoreGroupGrid>` | `evaluation`, `role: string` | `scoreUpdated` | Chấm điểm by group, scorer |
| `<WeightedScorePanel>` | `candidates: EvalCandidate[]` | — | Sticky panel kết quả tính điểm |
| `<DecisionMethodPicker>` | `method: ProcurementMethod`, `price: number` | `methodChange` | Select method + auto G04 check |
| `<EnvelopeGauge>` | `awarded: number`, `budget: number` | — | Gauge bar xanh/vàng/đỏ |
| `<ScorecardRadar>` | `scorecard: VendorScorecard` | — | Radar 5 chiều + trendline |
| `<AuditFindingTable>` | `findings: AuditFinding[]`, `editable: bool` | `add`, `update` | Findings + CAPA tracker |
| `<WorkflowStepper>` | `state: string`, `states: string[]` | — | Stepper theo state hiện tại |

---

## IV. Pinia Store (LIVE — Composition API)

> ✅ Store thực tế dùng `defineStore('imm03', () => {...})` (Composition setup) — KHÔNG Options API. Tối thiểu chỉ chứa state + 6 fetcher (`fetchEvaluations`, `fetchEvaluation`, `fetchAvl`, `fetchDecisions`, `fetchDecision`, `fetchKpis`). Các mutator (createDecision/award/addCandidate/score/recordContract/transition) **KHÔNG sống trong store** — views import trực tiếp từ `@/api/imm03` (xem `DecisionDetailView.vue`). Error wrapping qua `ApiError`.

```typescript
// frontend/src/stores/imm03.ts — GROUND TRUTH (78 lines)
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/imm03'
import type {
  EvalListItem, EvalDoc, AvlListItem, DecisionListItem, DecisionDoc, DashboardKpis,
} from '@/types/imm03'
import { ApiError } from '@/api/errors'

export const useImm03Store = defineStore('imm03', () => {
  // State
  const evaluations = ref<EvalListItem[]>([])
  const currentEval = ref<EvalDoc | null>(null)
  const avlEntries = ref<AvlListItem[]>([])
  const decisions = ref<DecisionListItem[]>([])
  const currentDecision = ref<DecisionDoc | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const kpis = ref<DashboardKpis | null>(null)

  function clearError() { error.value = null }
  function _setError(e: unknown) {
    error.value = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : String(e))
  }

  async function fetchEvaluations(filters = {}, page = 1, page_size = 20) {
    loading.value = true; error.value = null
    try { evaluations.value = (await api.listEvaluations(filters, page, page_size)).items }
    catch (e) { _setError(e) } finally { loading.value = false }
  }
  async function fetchEvaluation(name: string) {
    loading.value = true; error.value = null
    try { currentEval.value = await api.getEvaluation(name) }
    catch (e) { _setError(e); throw e } finally { loading.value = false }
  }
  async function fetchAvl(filters = {}) {
    loading.value = true; error.value = null
    try { avlEntries.value = (await api.listAvl(filters)).items }
    catch (e) { _setError(e) } finally { loading.value = false }
  }
  async function fetchDecisions(filters = {}) {
    loading.value = true; error.value = null
    try { decisions.value = (await api.listDecisions(filters)).items }
    catch (e) { _setError(e) } finally { loading.value = false }
  }
  async function fetchDecision(name: string) {
    loading.value = true; error.value = null
    try { currentDecision.value = await api.getDecision(name) }
    catch (e) { _setError(e); throw e } finally { loading.value = false }
  }
  async function fetchKpis() {
    try { kpis.value = await api.getDashboardKpis() } catch (e) { _setError(e) }
  }

  return {
    evaluations, currentEval, avlEntries, decisions, currentDecision,
    loading, error, kpis, clearError,
    fetchEvaluations, fetchEvaluation, fetchAvl, fetchDecisions, fetchDecision, fetchKpis,
  }
})
```

**Notes:**
- `awardDecision` được gọi từ `DecisionDetailView.vue` qua `import { awardDecision } from '@/api/imm03'`. Payload args: `(name, winner_supplier, awarded_price, funding_source, board_approver, contract_doc, remarks)` — KHÔNG có `winner_candidate`/`awarded_vendor`.
- `scoreEvaluation` args: `(name, scorer_role, scores_by_supplier)` — key của map là supplier name (khớp `cand.supplier`), KHÔNG phải row name.
- Vendor Profile pages KHÔNG dùng store — views gọi `listVendorProfiles`/`getVendorProfile`/`addVendorCert` trực tiếp.

<details><summary>Spec-only block (Options API, ignore)</summary>

```typescript
// LEGACY SPEC — KHÔNG còn được implement
import { defineStore } from "pinia";
import { useApi } from "@/composables/useApi";

export const useImm03Store = defineStore("imm03", {
  state: () => ({
    // Vendor Profile
    vendorProfiles: [] as VendorProfile[],
    vendorProfileTotal: 0,
    currentVendorProfile: null as VendorProfile | null,
    vendorProfileFilters: {
      avl_status: "",
      device_category: "",
      min_score: null as number | null,
      audit_overdue: false,
    },

    // AVL
    avlEntries: [] as AVLEntry[],
    avlTotal: 0,
    currentAvl: null as AVLEntry | null,

    // Evaluation
    evaluations: [] as VendorEvaluation[],
    evaluationTotal: 0,
    currentEvaluation: null as VendorEvaluation | null,

    // Decision
    decisions: [] as ProcurementDecision[],
    decisionTotal: 0,
    currentDecision: null as ProcurementDecision | null,

    // Scorecard
    currentScorecard: null as VendorScorecard | null,

    // Dashboard
    dashboardKpis: null as Record<string, unknown> | null,

    // Loading states
    loading: false,
    error: null as string | null,
  }),

  actions: {
    // Vendor Profile actions
    async fetchVendorProfiles(page = 1) {
      await useApi().run(
        "imm03.list_vendor_profiles",
        { ...this.vendorProfileFilters, page },
        (data) => {
          this.vendorProfiles = data.items;
          this.vendorProfileTotal = data.total;
        }
      );
    },

    async fetchVendorProfile(name: string) {
      await useApi().run(
        "imm03.get_vendor_profile",
        { name },
        (data) => { this.currentVendorProfile = data; }
      );
    },

    async createVendorProfile(payload: Partial<VendorProfile>) {
      return await useApi().run(
        "imm03.create_vendor_profile",
        payload,
        () => { this.fetchVendorProfiles(); }
      );
    },

    // AVL actions
    async fetchAvlEntries(filters = {}) {
      await useApi().run(
        "imm03.list_avl",
        filters,
        (data) => {
          this.avlEntries = data.items;
          this.avlTotal = data.total;
        }
      );
    },

    async createAvlEntry(payload: Partial<AVLEntry>) {
      return await useApi().run("imm03.create_avl_entry", payload);
    },

    async approveAvl(name: string, approver: string, approval_doc: string) {
      return await useApi().run(
        "imm03.approve_avl",
        { name, approver, approval_doc },
        () => { this.fetchAvlEntries(); }
      );
    },

    async suspendAvl(name: string, suspension_reason: string) {
      return await useApi().run(
        "imm03.suspend_avl",
        { name, suspension_reason },
        () => { this.fetchAvlEntries(); }
      );
    },

    // Evaluation actions
    async fetchEvaluations(filters = {}) {
      await useApi().run(
        "imm03.list_evaluations",
        filters,
        (data) => {
          this.evaluations = data.items;
          this.evaluationTotal = data.total;
        }
      );
    },

    async addCandidate(name: string, supplier: string) {
      return await useApi().run(
        "imm03.add_candidate",
        { name, supplier },
        () => { this.fetchEvaluation(name); }
      );
    },

    async submitQuotations(name: string, quotations: unknown[]) {
      return await useApi().run(
        "imm03.submit_quotations",
        { name, quotations },
        () => { this.fetchEvaluation(name); }
      );
    },

    async scoreEvaluation(name: string, scorer_role: string, scores_by_supplier: Record<string, Record<string, number>>) {
      // ⚠️ Tham số thực tế là scores_by_supplier (theo supplier name), không phải scores_by_candidate (row name)
      return await useApi().run(
        "imm03.score_evaluation",
        { name, scorer_role, scores_by_supplier },
        (data) => {
          if (this.currentEvaluation) {
            this.currentEvaluation.candidates.forEach((c) => {
              c.weighted_score = data.weighted_scores[c.name] ?? c.weighted_score;
            });
          }
        }
      );
    },

    async transitionEvalWorkflow(name: string, action: string) {
      return await useApi().run(
        "imm03.transition_eval_workflow",
        { name, action },
        () => { this.fetchEvaluation(name); }
      );
    },

    async fetchEvaluation(name: string) {
      await useApi().run(
        "imm03.get_evaluation",
        { name },
        (data) => { this.currentEvaluation = data; }
      );
    },

    // Decision actions
    async createDecision(payload: Partial<ProcurementDecision>) {
      return await useApi().run("imm03.create_decision", payload);
    },

    async awardDecision(payload: {
      name: string;
      winner_candidate: string;
      awarded_vendor: string;
      awarded_price: number;
      funding_source: string;
      board_approver: string;
      contract_doc: string;
    }) {
      return await useApi().run(
        "imm03.award_decision",
        payload,
        () => { this.fetchDecision(payload.name); }
      );
    },

    async recordContract(name: string, contract_no: string, contract_doc: string, signed_date: string) {
      return await useApi().run(
        "imm03.record_contract",
        { name, contract_no, contract_doc, signed_date }
      );
    },

    async fetchDecision(name: string) {
      await useApi().run(
        "imm03.get_decision",
        { name },
        (data) => { this.currentDecision = data; }
      );
    },

    // Scorecard & Dashboard
    async fetchScorecard(supplier: string, year: number, quarter: number) {
      await useApi().run(
        "imm03.get_vendor_scorecard",
        { supplier, year, quarter },
        (data) => { this.currentScorecard = data; }
      );
    },

    async fetchDashboardKpis(period: string) {
      await useApi().run(
        "imm03.dashboard_kpis",
        { period },
        (data) => { this.dashboardKpis = data; }
      );
    },
  },
});
```

</details>

---

## V. i18n Key Table

| Key | Tiếng Việt | Ngữ cảnh |
|---|---|---|
| `imm03.title` | Nhà cung cấp & Mua sắm | Sidebar |
| `imm03.vendor_profile.title` | Hồ sơ nhà cung cấp | Page title |
| `imm03.vendor_profile.create` | Tạo hồ sơ nhà cung cấp | Button |
| `imm03.avl.title` | Danh sách nhà cung cấp được phê duyệt | — |
| `imm03.avl.status.approved` | ✓ Được chấp thuận | Badge |
| `imm03.avl.status.conditional` | ⚠ Điều kiện | Badge |
| `imm03.avl.status.suspended` | 🚫 Đình chỉ | Badge |
| `imm03.avl.status.expired` | Hết hạn | Badge |
| `imm03.avl.approve_action` | Phê duyệt AVL | Button |
| `imm03.avl.suspend_action` | Đình chỉ AVL | Button |
| `imm03.evaluation.title` | Đánh giá nhà cung cấp | — |
| `imm03.evaluation.add_candidate` | Thêm nhà cung cấp | Button |
| `imm03.evaluation.open_rfq` | Mở RFQ | Button |
| `imm03.evaluation.score_group` | Chấm điểm nhóm | Tab label |
| `imm03.evaluation.recommended` | Nhà cung cấp đề xuất | Label |
| `imm03.decision.title` | Quyết định mua sắm | — |
| `imm03.decision.award` | Phê duyệt & Award | Button |
| `imm03.decision.submit_bgd` | Trình BGĐ | Button |
| `imm03.decision.method` | Phương án mua sắm | Field label |
| `imm03.decision.envelope_gauge` | % Ngân sách đã dùng | Label |
| `imm03.scorecard.title` | Bảng điểm nhà cung cấp | — |
| `imm03.scorecard.overall` | Điểm tổng hợp | Label |
| `imm03.dashboard.lead_time` | Thời gian Đánh giá → Award | KPI label |
| `imm03.dashboard.avl_coverage` | Độ bao phủ AVL | KPI label |
| `imm03.dashboard.avg_score` | Điểm trung bình NCC | KPI label |
| `imm03.dashboard.cost_saving` | Tiết kiệm chi phí | KPI label |
| `imm03.cert.status.active` | Còn hiệu lực | Badge |
| `imm03.cert.status.expiring` | Sắp hết hạn | Badge (vàng) |
| `imm03.cert.status.expired` | Hết hạn | Badge (đỏ) |
| `imm03.error.avl_required` | Nhà cung cấp không có AVL cho danh mục này | Toast |
| `imm03.error.po_mint_fail` | Không thể tạo AC Purchase — kiểm tra cấu hình Tech Spec | Toast |
| `imm03.warning.non_avl` | Nhà cung cấp ngoài AVL — cần phê duyệt từ VP Block1 | Warning inline |
| `imm03.confirm.award_title` | Xác nhận Award Decision | Dialog |
| `imm03.confirm.award_body` | Bạn đang award {vendor} với giá {price}. Thao tác này sẽ tạo AC Purchase. Tiếp tục? | Dialog |

---

## VI. UX Rules

1. **AVL badge nhất quán:**
   - ✓ Approved — màu xanh lá (`#16a34a`)
   - ⚠ Conditional — màu vàng cam (`#d97706`)
   - 🚫 Suspended — màu đỏ (`#dc2626`)
   - Hết hạn — màu xám (`#6b7280`)

2. **Permlevel field ẩn:** `awarded_price`, `envelope_check_pct`, `funding_source` hiển thị `***` nếu user thiếu quyền permlevel 1.

3. **Method select tự validate G04:** Khi chọn phương án, hiển thị inline badge hợp lệ/không hợp lệ dựa trên giá trị và loại hàng.

4. **Confirm dialog khi Award:** Hiện summary — vendor, giá, envelope %, nguồn vốn, người phê duyệt — trước khi submit.

5. **PO mint async:** Toast "Đang tạo AC Purchase..." → redirect đến AC Purchase khi xong. Nếu fail: rollback toast + link "Kiểm tra Tech Spec".

6. **Suspend AVL bắt buộc reason:** Dialog yêu cầu nhập `suspension_reason` (min 20 ký tự). Cảnh báo nếu vendor đang được dùng trong Evaluation đang Open.

7. **Audit findings Critical:** Modal escalation tự mở khi submit audit có finding Critical.

8. **Empty states:**
   - Vendor list trống: "Chưa có nhà cung cấp — tạo từ AC Supplier"
   - Evaluation candidates trống: "Thêm tối thiểu 3 nhà cung cấp cho phương án Đấu thầu rộng rãi"
   - AVL hết: "Chưa có AVL cho danh mục này — tạo mới"
