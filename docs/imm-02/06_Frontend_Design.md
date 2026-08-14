# IMM-02 — Frontend Design

> **Wave 2 — Live.** Vue components, Pinia store và API client đã implement đầy đủ. Tài liệu này phản ánh code thực tế.

| Mục | Giá trị |
|---|---|
| Module | **IMM-02 — Thông số Kỹ thuật & Phân tích Thị trường** |
| Phiên bản | 1.0.1 |
| Ngày cập nhật | 2026-05-14 |
| Stack | Vue 3 + TypeScript + Pinia + TanStack Query + TailwindCSS |
| Owner | FE Lead |
| Liên kết | [05 API Specification](./05_API_Specification.md) · [07 Testing QA](./07_Testing_QA.md) |

---

# Phần I — Sitemap & Routes

**Vue files thực tế:** `frontend/src/views/tech-specs/`

**Routes (`frontend/src/router/index.ts`):**

| Path | Component | Module key |
|---|---|---|
| `/tech-specs` | `views/tech-specs/TechSpecListView.vue` | `imm02` |
| `/tech-specs/new` | `views/tech-specs/TechSpecCreateView.vue` | `imm02` |
| `/tech-specs/:id` | `views/tech-specs/TechSpecDetailView.vue` | `imm02` |

Route-to-module map dùng regex `[/^\/tech-specs/, 'imm02']` để gắn breadcrumb + sidebar group.

| File (.vue) | API calls chính | Ghi chú |
|---|---|---|
| `TechSpecListView.vue` | `list_tech_specs`, `dashboard_kpis` | List với filter + KPI tiles; filter lock_in_bucket áp dụng client-side |
| `TechSpecCreateView.vue` | `create_tech_spec` | Form create Tech Spec |
| `TechSpecDetailView.vue` | `get_tech_spec`, `transition_workflow`, `lock_spec`, `withdraw_spec`, `reissue_spec` | Detail với workflow stepper + tabs |

> **Components CHƯA implement:** `MarketBenchmarkDetail.vue`, `LockInRiskDetail.vue`, `Imm02Dashboard.vue` — chưa có file Vue riêng. Benchmark + Lock-in submit qua API trực tiếp từ TechSpecDetail hoặc còn là TODO.

Sidebar group: **Khối 1 — Hoạch định** > Đặc tả kỹ thuật.

---

# Phần II — Component Catalog

## II.1. TechSpecList

```
Tech Spec                                              [+ Tạo từ Plan]
─────────────────────────────────────────────────────────────────────
Filter: [Trạng thái▾] [Khoa▾] [Danh mục▾] [Năm▾] [Lock-in ≤▾]   🔍
─────────────────────────────────────────────────────────────────────
TS-26-00045  v1.0  Máy thở Hamilton C6   ICU    Risk Assessed   45ms
                  Bắt buộc 12  Ứng viên 3  Lock-in 3.2 ⚠
TS-26-00044  v2.0  Lồng ấp Dräger        NICU   Locked          🔒
                  Bắt buộc  8  Ứng viên 4  Lock-in 1.8 ✓
TS-26-00043  v1.0  Monitor BN Mindray    Phẫu   Draft           ✏️
                  Bắt buộc  3  Ứng viên 0  Lock-in —
─────────────────────────────────────────────────────────────────────
        Hiển thị 1–20 / 67                         [ < ]  [1] [2] [ > ]
```

**Props / State:**
- `filters`: `{ workflow_state, device_category, fiscal_year, lock_in_max }`
- `sort`: `{ field: 'modified' | 'creation' | 'lock_in_score', dir: 'asc' | 'desc' }`
- Uses `useImm02Store.fetchList()`

**Behaviors:**
- Color badge per state (Draft=gray, Reviewing=yellow, Benchmarked=blue, Risk Assessed=orange, Pending Approval=purple, Locked=green, Withdrawn=red)
- Lock-in score: ≤ 2.0 = ✓ green, 2.1–3.5 = ⚠ yellow, > 3.5 = 🔴 red
- "Tạo từ Plan" button → opens PlanPickerModal

## II.2. TechSpecDetail (4 tabs + workflow stepper)

```
TS-26-00045 — Máy thở Hamilton C6                    [Hành động ▾]
Version 1.0  |  Nguồn: PP-26-001 / NR-26-04-00012
─────────────────────────────────────────────────────────────────────
Stepper: Draft ▶ Reviewing ▶ Benchmarked ▶ Risk Assessed ▶ Pending ▶ Locked
                                                         ●

[1. Tổng quan] [2. Yêu cầu KT] [3. Benchmark] [4. Hạ tầng + Lock-in]
─────────────────────────────────────────────────────────────────────

Tab 1 — Tổng quan:
┌─────────────────────────────────┬────────────────────────────────┐
│ Thiết bị: Hamilton C6           │ Nguồn kế hoạch: PP-26-001      │
│ Danh mục: Life Support          │ Yêu cầu gốc: NR-26-04-00012    │
│ Số lượng: 2                     │ Năm mục tiêu: 2027             │
│ Phiên bản: 1.0                  │ Phiên bản cha: —               │
└─────────────────────────────────┴────────────────────────────────┘
Tài liệu đính kèm: [Datasheet] [HSMT Excerpt] [+ Thêm]

Tab 2 — Yêu cầu kỹ thuật:
─────────────────────────────────────────────────────────────────────
[+ Thêm dòng] [Import Excel] [Áp dụng template]
Nhóm      Thông số           Giá trị/Phạm vi  M/O  Phương pháp KT
──────────────────────────────────────────────────────────────────
Hiệu suất  Tidal Volume       20–2000 mL       M    IEC 60601-2-12
Hiệu suất  FiO2 Range         21–100%          M    Bench test
An toàn    Alarm Priority     P1/P2/P3 theo IEC M   Manual verify
…          …                  …                …    …
──────────────────────────────────────────────────────────────────
Bắt buộc: 12 / 12 có PP KT ✓      Tùy chọn: 5
[Gửi rà soát G01 →]

Tab 3 — Benchmark:
─────────────────────────────────────────────────────────────────────
Trọng số: [Spec 40%] [Giá 30%] [Hỗ trợ 20%] [Thương hiệu 10%]  [Tính lại]
Nhà SX          Model          KT Match  Giá (VNĐ)   Hỗ trợ  Điểm   ⭐
Hamilton Med.   C6             95.5%     450.000.000  Tier1    87.2   ✓
Dräger          Evita V600     88.0%     480.000.000  Tier1    80.1
Mindray         SV600          80.0%     290.000.000  Tier2    72.4
[+ Thêm ứng viên]
Khuyến nghị: Hamilton C6 (87.2 điểm)
[Hoàn tất benchmark G02 →]

Tab 4 — Hạ tầng + Lock-in:
─────────────────────────────────────────────────────────────────────
Hạ tầng:
Điện           ✅ Compatible     220V/50Hz ↔ 220V/50Hz
Khí y tế       ⚠ Need Upgrade   O2+Air → O2+Air+Vac  [Chi phí: 50tr]
Mạng/CNTT      ⚠ Need Upgrade   LAN 1Gbps → +WiFi 6
HIS-PACS-LIS   ⚠ Need Upgrade   HL7 v2.3 → HL7 v2.5+FHIR
HVAC           ✅ Compatible     22°C → 22±2°C
Không gian     ✅ Compatible     12m² ≥ 10m²
Tình trạng tổng: Partial (3 Need Upgrade)

Lock-in Risk:
                    [Biểu đồ radar 5 chiều]
                 Giao thức
                    5
           Dịch vụ  ●  Tiêu hao
              ●         ●
         Phụ tùng    Phần mềm
Điểm lock-in: 3.05 / 5.00  ⚠ Vượt ngưỡng!
Kế hoạch giảm thiểu: [text area]
[Trình duyệt G03 →]
```

### II.2.1. CTA duyệt hồ sơ — server-driven gating (GATE-8 / LL-FE-51, vòng 6)

Thanh hành động (`.action-bar`) có 3 nút: **Chốt hồ sơ** / **Rút hồ sơ** / **Phát hành lại (phiên bản mới)**. Ground truth spec: `05_API_Specification.md` §3.2 (cờ) + `02_Analysis_Design.md` §IV.3 + ADR-IMM02-01.

**Đặc tả bắt buộc:**
- 3 computed `canLock` / `canWithdraw` / `canReissue` đọc **DUY NHẤT cờ server** `store.currentSpec?.can_lock` / `can_withdraw` / `can_reissue` (coerce `Boolean()`):
  ```ts
  const canLock     = computed(() => Boolean(store.currentSpec?.can_lock))
  const canWithdraw = computed(() => Boolean(store.currentSpec?.can_withdraw))
  const canReissue  = computed(() => Boolean(store.currentSpec?.can_reissue))
  ```
- **ZERO `workflow_state ===`** trong 3 computed CTA này (grep count = 0). Gỡ hardcode cũ (`TechSpecDetailView.vue` l.233-238: `workflow_state === 'Pending Approval'` v.v.). *(Lưu ý: `workflow_state ===` ở phần hiển thị khác — badge, điều kiện show `withdrawal_reason`, `stepClass` — KHÔNG thuộc CTA gating, được phép giữ.)*
- Nút **ẩn** (`v-if`, không chỉ `:disabled`) khi cờ false — user thiếu quyền/sai state KHÔNG thấy nút.
- Cờ thiếu (BE cũ chưa deploy / spec state lạ) → `Boolean(undefined)=false` → không nút; `allowed_transitions` default `[]` → **không lỗi console**.
- Types `frontend/src/types/imm02.ts` (`TechSpecDoc`): thêm `allowed_transitions?: string[]`, `can_lock?: 0|1`, `can_withdraw?: 0|1`, `can_reissue?: 0|1`.
- Test `TechSpecDetailView.ctaGating.test.ts`: assert ma trận cờ→nút (Pending Approval: Chốt+Rút hiện; Locked: chỉ Rút; Withdrawn: chỉ Phát hành lại; cờ=0 → nút ẩn; cờ thiếu → không lỗi + không nút).

### II.2.2. CTA 6 transition trung gian — server-driven `allowed_actions` (CR-WF-02-SPEC, vòng 24)

Đóng bug **"hidden-CTA-câm"**: action-bar cũ chỉ có 3 nút terminal (§II.2.1). Thêm cụm nút **1 nút / mỗi entry `allowed_actions`** (nhãn action VI trực tiếp). Ground truth: `05_API_Specification.md` §3.2 (`allowed_actions`) + `02_Analysis_Design.md` §IV.4 + ADR-IMM02-02. **Mirror IMM-01 Needs** (`NeedsRequestDetailView.vue` — render 1 nút/action từ `allowed_transitions`).

**Đặc tả bắt buộc:**
- Computed đọc DUY NHẤT field server:
  ```ts
  const wfActions = computed<string[]>(
    () => (store.currentSpec as { allowed_actions?: string[] } | null)?.allowed_actions ?? [])
  ```
- Slug ổn định cho `data-testid` (strip dấu + `đ`→`d` + hyphenate):
  ```ts
  function actionSlug(a: string): string {
    return a.normalize('NFD').replace(/[̀-ͯ]/g, '')
            .replace(/đ/g, 'd').replace(/Đ/g, 'D')
            .toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  }
  // 'Gửi rà soát'→'gui-ra-soat' · 'Yêu cầu chỉnh spec'→'yeu-cau-chinh-spec'
  // 'Hoàn tất benchmark'→'hoan-tat-benchmark' · 'Đánh giá rủi ro xong'→'danh-gia-rui-ro-xong'
  // 'Trình duyệt spec'→'trinh-duyet-spec' · 'Yêu cầu chỉnh risk'→'yeu-cau-chinh-risk'
  ```
- Render trong `.action-bar` (đặt TRƯỚC 3 nút terminal), label = action VI trực tiếp:
  ```html
  <button v-for="act in wfActions" :key="act"
          :data-testid="`cta-wf-${actionSlug(act)}`"
          class="btn btn-primary" @click="doTransition(act)">
    {{ act }}
  </button>
  ```
- Handler refetch sau transition (mirror `doLock`):
  ```ts
  async function doTransition(action: string) {
    const name = store.currentSpec?.name
    if (!name) return
    await store.transitionWorkflow(name, action)
    await store.fetchOne(name)
  }
  ```
- **Store**: đổi tên action `transition(name, action)` → **`transitionWorkflow(name, action)`** (không caller nào khác dùng `store.transition` — đã grep). Vẫn gọi `api.transitionSpecWorkflow` (`transition_workflow`).
- **Cụm ẩn khi `allowed_actions` rỗng** — `v-for` mảng rỗng render 0 nút (tự nhiên). State lạ / field thiếu → `?? []` → không lỗi console.
- **KHÔNG double-render**: `Phê duyệt spec`/`Rút spec` ∉ `allowed_actions` (exception) → 3 nút terminal `cta-lock`/`cta-withdraw`/`cta-reissue` (§II.2.1) GIỮ NGUYÊN, không trùng.
- **ZERO `workflow_state ===`** cho nút wf (gate DUY NHẤT theo membership `allowed_actions`; grep = 0). *(Badge/stepClass/`withdrawal_reason` hiển thị KHÔNG thuộc CTA — được giữ.)*
- **Types** `frontend/src/types/imm02.ts` (`TechSpecDoc`): thêm `allowed_actions?: string[]`.
- Test `TechSpecDetailView.ctaGating.test.ts`: Draft+`allowed_actions:['Gửi rà soát']` → có `cta-wf-gui-ra-soat`, click gọi `store.transitionWorkflow('...','Gửi rà soát')` + `fetchOne`; `allowed_actions:[]`/thiếu → 0 nút wf + không lỗi; Pending Approval có cả nút wf `cta-wf-yeu-cau-chinh-risk` LẪN `cta-lock`/`cta-withdraw` (không nuốt nhau).

## II.3. RequirementEditor

Inline-editable table với keyboard navigation:

```
┌─────┬──────────┬─────────────────┬────────────────┬─────┬───┬──────────────────────┐
│ Seq │ Nhóm     │ Thông số        │ Giá trị/Phạm vi│ M/O │ W │ Phương pháp KT       │
├─────┼──────────┼─────────────────┼────────────────┼─────┼───┼──────────────────────┤
│  1  │ Hiệu suất│ Tidal Volume    │ 20–2000 mL     │ M   │ 8 │ IEC 60601-2-12       │
│  2  │ An toàn  │ Alarm Priority  │ P1/P2/P3       │ M   │ 7 │ Manual verify IEC     │
│  3  │ Kết nối  │ Ethernet port   │ 2× RJ45 1Gbps  │ O   │ 5 │                      │
└─────┴──────────┴─────────────────┴────────────────┴─────┴───┴──────────────────────┘
[+ Thêm dòng]    [Import Excel ↑]    Bắt buộc: 8/12 ✓   Thiếu PP KT: 0
```

- `M` = Mandatory (màu đỏ nếu thiếu test_method), `O` = Optional
- `W` = Weight 1–10
- Import Excel: drag & drop → parse + preview → confirm insert

## II.4. BenchmarkTable

```
┌─────────────────┬──────────┬──────────┬────────────┬─────────┬───────┬──────┐
│ Nhà sản xuất    │ Model    │ KT Match │ Giá (VNĐ)  │ Hỗ trợ │ Điểm  │      │
├─────────────────┼──────────┼──────────┼────────────┼─────────┼───────┼──────┤
│ ⭐ Hamilton Med.│ C6       │ 95.5%    │ 450tr      │ Tier1   │ 87.2  │ [✏] │
│ Dräger          │ Evita V6 │ 88.0%    │ 480tr      │ Tier1   │ 80.1  │ [✏] │
│ Mindray         │ SV600    │ 80.0%    │ 290tr      │ Tier2   │ 72.4  │ [✏] │
│ [+ Thêm]        │          │          │            │         │       │     │
└─────────────────┴──────────┴──────────┴────────────┴─────────┴───────┴──────┘
```

Trọng số tuning panel (slider):
```
Spec ████████████████ 40%    Giá █████████████ 30%
Hỗ trợ █████████ 20%         Thương hiệu ████ 10%
Tổng: 100%  [Tính lại điểm]
```

## II.5. InfraCompatCardGrid

```
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ ⚡ Điện          │ │ 💨 Khí y tế      │ │ 🌐 Mạng/CNTT    │
│ ✅ Compatible    │ │ ⚠️ Need Upgrade  │ │ ⚠️ Need Upgrade  │
│ 220V/50Hz        │ │ O2+Air → +Vac    │ │ LAN → +WiFi 6   │
│                  │ │ CP: 50 triệu     │ │ ETA: Q3/2026    │
└──────────────────┘ └──────────────────┘ └──────────────────┘
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ 🏥 HIS-PACS-LIS  │ │ ❄️ HVAC          │ │ 📐 Không gian   │
│ ⚠️ Need Upgrade  │ │ ✅ Compatible    │ │ ✅ Compatible    │
│ HL7→FHIR R4      │ │ 22°C, 50% RH     │ │ 12m² ≥ 10m²     │
│ Owner: CNTT      │ │                  │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

Click vào card → expand form chi tiết để edit.

## II.6. LockInRadar

Biểu đồ radar 5 chiều (sử dụng Chart.js):

```
                  Giao thức
                     5
                    4●
                   3
             Dịch ───────── Tiêu
             vụ  2   ●      hao
                  1
                    ●
            Phụ tùng  Phần mềm

Điểm: 3.05 / 5.00  🟡 Ngưỡng: 3.50
Kết quả: Trong ngưỡng cho phép ✓
```

Hiển thị ngưỡng (threshold line) trên radar.

## II.7. WorkflowStepper

```
● Draft ─────── ● Reviewing ─────── ○ Benchmarked ─────── ○ Risk Assessed ─────── ○ Pending ─── ○ Locked
                     [current]
Action button: [Hoàn tất benchmark →]
```

- State hiện tại highlight màu xanh
- States completed = filled circle, pending = empty circle
- Action button tương ứng transition tiếp theo
- Nếu gate chưa đủ điều kiện → tooltip "Cần đủ 8 yêu cầu bắt buộc trước khi chuyển"

## II.8. VersionTimeline

```
Lịch sử phiên bản:
v2.0  TS-26-00048  Draft       2026-05-08  [Reissue từ v1.0]  [Đang xem]
v1.0  TS-26-00045  Withdrawn   2026-05-07  [Rút: cần cập nhật]  [Xem]
```

---

# Phần III — Pinia Store

File: `frontend/src/stores/imm02.ts` — **Đã implement.** Store ID: `'imm02'`.

**State:**

| Field | Type | Mô tả |
|---|---|---|
| `specs` | `TechSpecListItem[]` | Danh sách trang hiện tại |
| `total` | `number` | Tổng số bản ghi |
| `page` / `pageSize` | `number` | Pagination state |
| `loading` | `boolean` | Loading flag |
| `error` | `string \| null` | Error message |
| `currentSpec` | `TechSpecDoc \| null` | Detail document đang xem |
| `kpis` | `DashboardKpis \| null` | KPIs (`by_state`, `avg_lock_in_score`, `backlog_over_30d`) |

**Actions (tên thực tế):**

| Action | Gọi API | Ghi chú |
|---|---|---|
| `fetchList(filters, page, pageSize)` | `list_tech_specs` | |
| `fetchOne(name)` | `get_tech_spec` | |
| `fetchKpis()` | `dashboard_kpis` | |
| `transitionWorkflow(name, action)` | `transition_workflow` | `transitionSpecWorkflow` trong api/imm02.ts (đổi tên từ `transition` — CR-WF-02-SPEC vòng 24; render 1 nút/`allowed_actions`) |
| `lock(name, approver, remarks)` | `lock_spec` | |
| `withdraw(name, reason)` | `withdraw_spec` | reason → `withdrawal_reason` param |
| `reissue(from)` | `reissue_spec` | from → `from_spec` param |

> **Actions KHÔNG có trong store thực tế** (chỉ trong design cũ): `addRequirement`, `bulkImportRequirements`, `submitBenchmark`, `submitInfraCompat`, `submitLockInAssessment`. Gọi API client trực tiếp từ component khi cần.

---

# Phần IV — i18n Table

## IV.1. Workflow States

| Key | Tiếng Việt |
|---|---|
| `state.Draft` | Nháp |
| `state.Reviewing` | Đang rà soát |
| `state.Benchmarked` | Đã benchmark |
| `state.Risk Assessed` | Đã đánh giá rủi ro |
| `state.Pending Approval` | Chờ phê duyệt |
| `state.Locked` | Đã khóa |
| `state.Withdrawn` | Đã rút |

## IV.2. Workflow Actions

| Key | Tiếng Việt |
|---|---|
| `action.Gửi rà soát` | Gửi rà soát |
| `action.Yêu cầu chỉnh sửa` | Yêu cầu chỉnh sửa |
| `action.Hoàn tất benchmark` | Hoàn tất benchmark |
| `action.Hoàn tất đánh giá rủi ro` | Hoàn tất đánh giá rủi ro |
| `action.Trình duyệt` | Trình duyệt |
| `action.Phê duyệt` | Phê duyệt |
| `action.Rút hồ sơ` | Rút hồ sơ |
| `action.Yêu cầu đánh giá lại rủi ro` | Yêu cầu đánh giá lại rủi ro |

## IV.3. Lock-in Dimensions

| Key | Tiếng Việt | Weight |
|---|---|---|
| `lockin.Protocol Standard` | Giao thức tiêu chuẩn | 30% |
| `lockin.Consumable Source` | Nguồn tiêu hao | 20% |
| `lockin.Software License` | Giấy phép phần mềm | 20% |
| `lockin.Parts Source` | Nguồn phụ tùng | 15% |
| `lockin.Service Tooling` | Công cụ dịch vụ | 15% |

## IV.4. Infra Domains

| Key | Tiếng Việt |
|---|---|
| `infra.Electrical` | Điện |
| `infra.Medical Gas` | Khí y tế |
| `infra.Network/IT` | Mạng/CNTT |
| `infra.HIS-PACS-LIS` | HIS-PACS-LIS |
| `infra.HVAC` | Điều hòa không khí |
| `infra.Space-Layout` | Không gian bố trí |

## IV.5. Compatibility Status

| Key | Tiếng Việt | Badge Color |
|---|---|---|
| `compat.Compatible` | Tương thích | green |
| `compat.Need Upgrade` | Cần nâng cấp | yellow |
| `compat.Need Major Upgrade` | Cần nâng cấp lớn | red |
| `compat.N/A` | Không áp dụng | gray |

## IV.6. Error Messages

| Code | Tiếng Việt |
|---|---|
| `VR-02-01` | Plan line đã có thông số kỹ thuật đang hoạt động |
| `VR-02-02` | Phải có ít nhất 1 yêu cầu bắt buộc |
| `VR-02-03` | Yêu cầu bắt buộc thiếu phương pháp kiểm tra |
| `VR-02-04` | Benchmark cần ít nhất 3 ứng viên so sánh |
| `VR-02-05` | Chưa đánh giá đủ 6 hạng mục hạ tầng |
| `G01` | Cần ≥ 8 yêu cầu bắt buộc với phương pháp kiểm tra |
| `G02` | Cần ít nhất 3 ứng viên benchmark |
| `G03` | Chưa đủ đánh giá 6 hạng mục hạ tầng |
| `G04` | Nguy cơ lock-in cao, cần kế hoạch giảm thiểu được phê duyệt |
| `LOCKED_IMMUTABLE` | Hồ sơ đã khóa không thể chỉnh sửa. Vui lòng rút và tái phát hành |
| `REISSUE_BAD_STATE` | Chỉ hồ sơ đã rút mới có thể tái phát hành |
