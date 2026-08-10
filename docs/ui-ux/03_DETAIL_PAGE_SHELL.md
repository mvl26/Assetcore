# Khuôn màn CHI TIẾT — `DetailPageShell` (Core Doc VÒNG 4)

| Mục | Giá trị |
|---|---|
| Phạm vi | `frontend/src/components/common/DetailPageShell.vue` (**tier-1**, KHÔNG phải primitive `ui/` thứ 9) + **3 màn chi tiết thật** — **cross-cutting, KHÔNG thuộc IMM-XX** |
| Loại tài liệu | Core Doc cross-cutting (UI/UX) — spec thi hành cho FE dev vòng 4 |
| Owner | BA (đặc tả) · FE dev (thi hành) · QA (chấm A0–A13) |
| Trạng thái | **Chốt để code** — spec-before-code gate ĐẠT |
| Ngày đo | 2026-07-31 (mọi số/dòng trích trong tài liệu này đo TỪ ĐĨA hôm nay, sau vòng 3) |
| Nhánh | `feature/hieuc/core-refinement` @ `3a6a391` + working tree vòng 2–3 (chưa commit) |
| Tài liệu mẹ | [`00_AUDIT_HIEN_TRANG.md`](./00_AUDIT_HIEN_TRANG.md) — §6 sổ `AC-UX-048…053` · §9 **ADR-UX-06**, **ADR-UX-07** |
| Tài liệu anh | [`01_DESIGN_SYSTEM.md`](./01_DESIGN_SYSTEM.md) (tầng 0) · [`02_LIST_PAGE_SHELL.md`](./02_LIST_PAGE_SHELL.md) (khuôn màn DANH SÁCH — **ADR-UX-05**) |

> **Vì sao có tài liệu này.** Vòng 3 đóng *false-empty* cho lớp **danh sách**. Lớp **chi tiết** có một nợ
> song song nhưng đau hơn: khi nạp bản ghi hỏng, **21/32** màn chi tiết không có bất kỳ lối nạp lại nào —
> hoặc **trang trắng**, hoặc **một dòng chữ đỏ cụt**, hoặc tệ nhất là **khung chi tiết rỗng mà panel thao tác
> vẫn hiện** (người dùng bấm nút trên một bản ghi không tồn tại). Nợ này đã được ghi ngay trong chú thích
> của `DetailLoadError.vue:6-8` từ CR-74 nhưng chỉ vá được **11/32** màn. Vòng 4 dựng **một khuôn**
> (`DetailPageShell`) đóng dứt điểm 4 trạng thái + tắt panel thao tác ngoài trạng thái có-dữ-liệu, rồi áp
> thật cho **3 màn** — không vá lẻ từng màn.

---

## §0. Phạm vi & Boundaries

**Always (bắt buộc mọi thay đổi vòng 4):**
- **4 trạng thái LOẠI TRỪ LẪN NHAU** — `error` · `loading` · `notfound` · `content`, quyết định bằng **cấu trúc**
  (một chuỗi `v-if / v-else-if / v-else`), không bằng quy ước.
- **Lỗi thắng tất cả**: có `errorKind` ⇒ luôn thấy `DetailLoadError`, kể cả khi đang `loading` hoặc còn dữ liệu cũ.
- **Không dead-end**: mọi trạng thái hỏng đều có nút quay về danh sách; `unknown` thêm nút nạp lại.
- **Panel thao tác / tab / dải KPI CHỈ render ở `content`** (nợ ghi trong `DetailLoadError.vue:7`).
- **No-fork**: chuỗi + nhánh lỗi là SSoT của `DetailLoadError.vue`; thanh tab là SSoT của `DetailTabBar.vue`.
  Shell **compose**, KHÔNG viết lại.
- Gate CTA giữ nguyên **server-driven** `allowed_transitions` + cờ capability (GATE-8 / LL-FE-51).
- Mỗi hàm nạp: **xoá lỗi ở ĐẦU lượt** · `doc = null` khi hỏng · **luôn** hạ `loading` trong `finally` ·
  khởi tạo `loading = ref(true)`.

**Ask first (hỏi BA/PM trước khi làm):**
- Thêm/bớt trạng thái ngoài 4 trạng thái đã chốt, hoặc đổi thứ tự ưu tiên §2.
- Áp `DetailPageShell` cho màn chi tiết **thứ 4** trở đi trong cùng vòng (adoption diện rộng = `AC-UX-048`, vòng 5).
- Đưa `DetailPageShell` xuống `components/ui/` (thành primitive #9) — xem **ADR-UX-06**, hiện là **KHÔNG**.
- Thêm prop mới cho `DetailLoadError.vue` / `DetailTabBar.vue` (2 file đang được 11 + 5 màn dùng chung).

**Never (tuyệt đối không, vòng 4):**
- **KHÔNG** đặt shell trong `frontend/src/components/ui/` — guard `uiPrimitiveHygiene.test.ts` đếm
  `số export == số .vue == số test`; primitive thứ 9 làm ĐỎ ngay (A1).
- **KHÔNG** sửa `frontend/src/stores/**`, `frontend/src/api/**`, bất kỳ `.py` nào (A11). BE **không phải sửa**:
  `get_capa` / `get_audit` / `get_management_review` đã emit `allowed_transitions` + cờ capability.
- **KHÔNG** khai lại chuỗi nút nạp lại trong shell — **kể cả trong comment** (A2 chấm bằng `grep -c`, comment cũng tính).
- **KHÔNG** đổi tên `data-testid` đang bị test khoá: `cta-start`, `cta-close`, `cta-close-confirm`, `cta-edit`,
  `cta-advance`, `cta-reopen`, `cta-transition-<state>`, `transition-confirm`, `no-actions-hint`,
  `checklist-editor`, `checklist-readonly`, `readonly-verdict`.
- **KHÔNG** đổi nhãn 3 tab của màn kiểm toán (`Tổng quan` / `Bảng kiểm` / `Báo cáo & Phát hiện`) — test cũ
  tìm nút **bằng đúng chuỗi** `b.text() === 'Bảng kiểm'` (`internalAuditCtaGate.test.ts:84`,
  `internalAuditChecklistHydration.test.ts:69`).
- **KHÔNG** đụng `ProcurementPlanDetailView.vue` (5 chỗ hardcode `workflow_state === 'Draft'`) — cần cờ server
  `can_edit`, là **hard-dependency BE** ⇒ `AC-UX-049`, vòng 5.
- **KHÔNG** re-spec màn DANH SÁCH (vòng 3 đã đóng — xem §1.3 bằng chứng A0).

---

## §1. Hiện trạng đo từ đĩa — bằng chứng phải sửa (2026-07-31)

### 1.1 Ba màn đích — triệu chứng THẬT khi nạp bản ghi hỏng

| # | View | Mã hiện tại | Người dùng thấy gì | Lối nạp lại |
|---|---|---|---|---|
| 1 | `views/incident/CAPADetailView.vue` (390 dòng) | `load()` `:81-90` bắt lỗi vào **một chuỗi phẳng** `loadError` (không phân loại 403/404/khác); template `:180` `v-else-if="!capa"` in **dòng chữ đỏ** `text-red-500` với câu mặc định *«Không tìm thấy…»* | 403 thiếu quyền và 500 mất mạng đều bị **dán nhãn 404**; hết đường đi (không nút quay lại, không nút nạp lại) | ❌ |
| 2 | `views/compliance/InternalAuditDetailView.vue` (404 dòng) | ĐÃ dùng `DetailLoadError` `:190-199`, nhưng `const loading = ref(false)` `:24` ⇒ **lượt render đầu tiên** (trước khi `onMounted` chạy) rơi vào nhánh `!audit` ⇒ **nháy 404 một nhịp** rồi mới ra khung xương | Nháy trạng thái sai; tab + CTA tự chế nằm rải trong `<template v-else>` | ✅ (có `@retry`) |
| 3 | `views/compliance/ManagementReviewDetailView.vue` (402 dòng) | ĐÃ dùng `DetailLoadError` `:206-215`; `loading = ref(true)` `:32` đúng | CTA nằm trong `#actions` của `PageHeader` — đúng vị trí nhưng **mỗi màn tự bố trí một kiểu** | ✅ |

**Điểm chung cần khuôn hoá:** cả 3 màn tự viết lại chuỗi `v-if loading → v-else-if !record → v-else content`.
Ba bản sao ⇒ ba cách sai khác nhau (bảng trên), và mỗi màn mới lại chép thêm một bản.

### 1.2 Nợ nền của lớp chi tiết (đo trên toàn bộ 32 màn `*DetailView.vue`)

```bash
ls frontend/src/views/*/*DetailView.vue | wc -l                       # 32
grep -rl DetailLoadError frontend/src/views --include=*DetailView.vue | wc -l   # 11
grep -rln 'text-red-500' frontend/src/views/*/*DetailView.vue | wc -l          # 14
grep -rl DetailTabBar   frontend/src/views --include=*.vue | wc -l              # 5
```

| Số đo | Giá trị | Ý nghĩa |
|---|---|---|
| Màn chi tiết | **32** | mẫu số |
| Dùng `DetailLoadError` | **11** | có empty-state chuẩn + lối thoát |
| **KHÔNG** có lối nạp lại nào (`DetailLoadError` lẫn `@retry`) | **21** | `AC-UX-048` — danh sách đầy đủ ở §6 tài liệu mẹ |
| Còn dùng dòng chữ đỏ `text-red-500` | **14** | dead-end kinh điển |
| Dùng `DetailTabBar` | **5** | 27 màn còn lại tự chế tab (`AC-UX-052`) |
| Dùng `useDetailAccess` | **3** (`pm`, `cm`, `incident`) | composable đã có nhưng chưa lan |

### 1.3 Baseline đo lúc bắt đầu vòng 4 (nguồn chấm DELTA)

| Mốc | Lệnh | Kết quả đo 14:2x hôm nay |
|---|---|---|
| **A0** carry-over vòng 3 | `npx vitest run src/components/ui/ListPageShell.test.ts src/views/purchase/purchaseListStates.test.ts src/views/auth/userProfileListStates.test.ts src/views/procurement/vendorProfileListStates.test.ts src/views/needs/procurementPlanListStates.test.ts` | **5 passed / 40 passed** ⇒ vòng 3 **XONG** |
| **A10** 5 test bám 3 view | `npx vitest run src/views/incident/capaCtaGate.test.ts src/views/incident/CAPADetailView.test.ts src/views/compliance/internalAuditCtaGate.test.ts src/views/compliance/internalAuditChecklistHydration.test.ts src/views/compliance/managementReviewCtaGate.test.ts` | **5 passed / 50 passed** |
| **A12** toàn bộ FE | `npx vitest run` | **305 file / 2951 test — 0 file ĐỎ** |
| **A1** primitive tầng 0 | `ls frontend/src/components/ui/*.vue \| wc -l` | **8** |
| **A8** chống thoái lui | `grep -cE 'v-if="[^"]*(status\|workflow_state) ===' <3 file>` | **0 / 0 / 0** |
| **A13** sổ backlog | `grep -rhoE 'AC-UX-[0-9]{3}' docs/ \| sort -u \| tail -1` · `AC-CR-*` | **AC-UX-047** · **AC-CR-123** |

> **Danh sách ĐỎ đầu vòng = RỖNG.** Vì vậy A12 chấm gắt: sau vòng vẫn phải **0 file đỏ**, và **+4** file test.

---

## §2. Máy trạng thái — 4 trạng thái loại trừ lẫn nhau

### 2.1 Định nghĩa (SSoT — cài đúng 1 lần trong `DetailPageShell.vue`)

```ts
type DetailState = 'error' | 'loading' | 'notfound' | 'content'

const state = computed<DetailState>(() => {
  if (props.errorKind) return 'error'      // '' | null | undefined = không lỗi
  if (props.loading) return 'loading'
  if (!props.doc) return 'notfound'
  return 'content'
})
```

**Thứ tự ưu tiên: `error` > `loading` > `notfound` > `content`.**

| `errorKind` | `loading` | `doc` | Trạng thái | Thân bài render |
|---|---|---|---|---|
| `'unknown'` / `'forbidden'` / `'notfound'` | * | * | **error** | `DetailLoadError :kind="errorKind"` |
| rỗng | `true` | * | **loading** | slot `#skeleton` (mặc định `SkeletonLoader variant="form" rows=6`) |
| rỗng | `false` | `null` | **notfound** | `DetailLoadError kind="notfound"` |
| rỗng | `false` | có | **content** | `#header` + `#actions` + `#kpi` + tab + slot mặc định |

*Vì sao `error` đứng trước `loading` (A4):* bất biến là **“có lỗi thì người dùng LUÔN nhìn thấy lỗi”**. Nếu
`loading` thắng, cú bấm «nạp lại» sẽ **nuốt** thông báo lỗi cũ trong khi request mới đang bay ⇒ nút trông như chết.
Đổi lại, mọi hàm nạp **bắt buộc** xoá lỗi ở đầu lượt (INV-UX4-7).

*Vì sao `error` cũng thắng `doc` còn giá trị (A4):* dữ liệu đang hiện là ảnh chụp của lần nạp TRƯỚC. Giữ nó dưới
một banner lỗi khiến người dùng tin bản ghi vẫn đúng — cùng lớp bug với *false-empty* của vòng 3, nhưng ở màn
chi tiết thì hậu quả nặng hơn: **thao tác trên dữ liệu cũ**.

*Vì sao `notfound` là trạng thái RIÊNG chứ không phải “content rỗng”:* `doc = null` sau khi nạp xong là tín hiệu
dứt khoát “không có bản ghi”. Render khung chi tiết với mọi trường `—` (hiện trạng 14 màn) là **trang trắng có
viền** — người dùng tưởng bản ghi mất dữ liệu, không biết là mã sai.

### 2.2 Cái gì hiện ở trạng thái nào

| Vùng | error | loading | notfound | content |
|---|---|---|---|---|
| `#title` (tiêu đề tĩnh + nút ← Quay lại) | ✅ | ✅ | ✅ | ✅ |
| `DetailLoadError` | ✅ | — | ✅ (`kind="notfound"`) | — |
| `#skeleton` | — | ✅ | — | — |
| `#header` (PageHeader / thẻ tóm tắt bản ghi) | — | — | — | ✅ |
| `#actions` (**panel thao tác**) | **—** | **—** | **—** | ✅ |
| `#kpi` (dải chỉ số) | **—** | **—** | **—** | ✅ |
| Thanh tab (`DetailTabBar`, prop `tabs`) | **—** | **—** | **—** | ✅ |
| slot mặc định (nội dung + `RecordHistory` + modal) | — | — | — | ✅ |

> `#title` là vùng **duy nhất** hiện ở mọi trạng thái ⇒ nội dung của nó **KHÔNG được** deref bản ghi
> (INV-UX4-12). Mục đích: người dùng luôn biết mình đang ở màn nào và luôn có đường quay lại, kể cả khi 404.

---

## §3. Hợp đồng API — `frontend/src/components/common/DetailPageShell.vue`

### 3.0 Vị trí & luật tầng

`DetailPageShell` là **tier-1** (`components/common/`), **KHÔNG** phải primitive tầng 0 — quyết định **ADR-UX-06**.
Lý do cứng (không phải khẩu hiệu):

1. Nó **compose** hai component tier-1 đang là SSoT: `DetailLoadError.vue` (11 màn dùng) và `DetailTabBar.vue`
   (5 màn dùng). Primitive tầng 0 bị cấm import ngược lên tier-1 (`02 §3.4`).
2. Guard `uiPrimitiveHygiene.test.ts:22-31,98-114` khoá `EXPECTED_PRIMITIVES` = **8** và đối chiếu 3 vế
   *(số export barrel == số `.vue` == số test)*. Thêm file thứ 9 vào `ui/` ⇒ **đỏ ngay** (đó chính là phép đo A1).
3. Nó **có tiếng Việt trong hợp đồng** (nhãn thực thể / nhãn nút quay lại truyền từ view), khác luật primitive
   “copy khai trong `withDefaults`”.

Kế thừa từ tầng 0: **dumb** — KHÔNG import `vue-router`, `@/stores/*`, `@/api/*` (client), KHÔNG tự gọi gì.
Được phép: `import type { DetailLoadKind } from '@/api/errors'` (chỉ **kiểu**, bị xoá lúc biên dịch) —
đúng như `DetailLoadError.vue:19` đang làm.

### 3.1 Props

| Prop | Kiểu | Mặc định | Ghi chú |
|---|---|---|---|
| `loading` | `boolean` | `false` | đang nạp |
| `errorKind` | `'' \| DetailLoadKind \| null` | `null` | **có giá trị ⇒ trạng thái `error`**; truyền thẳng `kind` cho `DetailLoadError` |
| `errorMessage` | `string` | `''` | message THẬT từ envelope → `DetailLoadError.message` |
| `doc` | `unknown` | `null` | bản ghi đã nạp; `null`/`undefined` ⇒ `notfound` |
| `notFound` | `boolean` | `false` | *(bổ sung sau khi §3 được viết — đo lại `DetailPageShell.vue:43,:83` ngày 2026-08-03)* cờ 404 **tường minh** cho view tự phân loại; `notFound === true` ⇒ `notfound` kể cả khi `doc` còn giá trị |
| `entityLabel` | `string` | *(bắt buộc)* | nhãn VI viết thường, vd `'hành động khắc phục/phòng ngừa'` |
| `recordId` | `string` | `undefined` | mã bản ghi hiện trong thông báo |
| `backLabel` | `string` | *(bắt buộc)* | nhãn nút quay về danh sách, vd `'Về danh sách kiểm toán'` |
| `tabs` | `{ key: string; label: string }[]` | `() => []` | rỗng ⇒ **không** render thanh tab |
| `activeTab` | `string` | `''` | dùng với `v-model:active-tab` |
| `skeletonVariant` | `'table' \| 'kpi-cards' \| 'form' \| 'card' \| 'list'` | `'form'` | → `SkeletonLoader.variant` |
| `skeletonRows` | `number` | `6` | → `SkeletonLoader.rows` |

> ⚠️ **Mọi prop PHẢI khai** trong `defineProps`. Prop không khai rơi vào `$attrs` và **in thẳng ra DOM**
> (`entity-label="…"` nằm trên thẻ gốc ở **mọi** trạng thái) — bẫy đã cắn ở vòng 3 (`02 §7.1`).
>
> ⚠️ **KHÔNG khai `retryLabel` / `retryHint`.** Nhãn nút nạp lại là SSoT của `DetailLoadError.vue:71` (A2).
>
> ⚠️ **Kiểu tab khai INLINE** (`{ key: string; label: string }[]`), KHÔNG `import type { DetailTab } from
> './DetailTabBar.vue'` — tránh phụ thuộc vào việc `export interface` trong `<script setup>` có resolve qua
> `vue-tsc` hay không. Hình dạng trùng khít `DetailTabBar.vue:13-18`.

### 3.2 Emits

| Emit | Khi nào | Ghi chú |
|---|---|---|
| `retry` | người dùng bấm nút nạp lại của `DetailLoadError` (chỉ có ở `kind='unknown'`) | shell **chuyển tiếp**, không tự gọi gì |
| `back` | bấm nút quay về danh sách (có ở **cả 3** kind) | view quyết định route đích |
| `update:activeTab` | bấm một tab | dùng `v-model:active-tab` ở view |

### 3.3 Slots

| Slot | Hiện ở trạng thái | Nội dung điển hình |
|---|---|---|
| `title` | **mọi** | tiêu đề tĩnh + nút «← Quay lại» — **cấm deref bản ghi** |
| `skeleton` | `loading` | ghi đè khung xương mặc định |
| `header` | `content` | `<PageHeader>` (KHÔNG kèm `#actions`) hoặc thẻ tóm tắt bản ghi |
| `actions` | `content` | **panel thao tác**: mọi CTA vòng đời + `no-actions-hint` |
| `kpi` | `content` | dải `<KpiCard>` (shell tự bọc lưới `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`) |
| *(mặc định)* | `content` | nội dung chính + panel tab + `RecordHistory` + mọi `BaseModal` |

Thanh tab **không phải slot** — là **vùng prop-driven** do shell sở hữu (`tabs` + `activeTab`). Đây là bản
hiện thân chặt hơn của “slot tab” trong acceptance A9: slot cho phép mỗi màn tự chế lại tab bar (đúng nợ đang
phải trả — 27/32 màn tự chế), còn vùng prop-driven **ép** dùng `DetailTabBar` ⇒ `grep -c DetailTabBar
DetailPageShell.vue` = 1 (A2). Xem **ADR-UX-07**.

### 3.4 Khuôn template (cài đúng như dưới — đây là hợp đồng, không phải gợi ý)

```vue
<template>
  <div
    class="page-container animate-fade-in space-y-5"
    :data-state="state"
    data-testid="detail-page-shell">
    <slot name="title" />

    <DetailLoadError
      v-if="state === 'error'"
      :kind="errorKind || 'unknown'"
      :entity-label="entityLabel"
      :record-id="recordId"
      :message="errorMessage"
      :back-label="backLabel"
      @retry="emit('retry')"
      @back="emit('back')" />

    <div v-else-if="state === 'loading'" class="p-6" data-testid="detail-skeleton">
      <slot name="skeleton">
        <SkeletonLoader :variant="skeletonVariant" :rows="skeletonRows" />
      </slot>
    </div>

    <DetailLoadError
      v-else-if="state === 'notfound'"
      kind="notfound"
      :entity-label="entityLabel"
      :record-id="recordId"
      :back-label="backLabel"
      @retry="emit('retry')"
      @back="emit('back')" />

    <div v-else class="space-y-5" data-testid="detail-content">
      <slot name="header" />

      <div
        v-if="$slots.actions"
        class="card p-4 flex flex-wrap items-center gap-2"
        data-testid="detail-actions">
        <slot name="actions" />
      </div>

      <div
        v-if="$slots.kpi"
        class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        data-testid="detail-kpi">
        <slot name="kpi" />
      </div>

      <div v-if="tabs.length" data-testid="detail-tabs">
        <DetailTabBar
          :tabs="tabs"
          :model-value="activeTab"
          @update:model-value="emit('update:activeTab', $event)" />
      </div>

      <slot />
    </div>
  </div>
</template>
```

Ràng buộc cấu trúc:
- Thẻ gốc **duy nhất** ⇒ fallthrough attrs hoạt động; `data-state` là hợp đồng chấm A3
  (`wrapper.attributes('data-state')`).
- 4 nhánh thân bài nối bằng **MỘT** chuỗi `v-if / v-else-if / v-else` ⇒ loại trừ **bằng cấu trúc**.
  Hai nhánh `error` và `notfound` cùng render `DetailLoadError` nhưng **khác `kind`** ⇒ trong DOM luôn có
  **đúng 1** phần tử `[data-testid="detail-load-error"]`, phân biệt bằng `[data-kind]`.
- `#actions` / `#kpi` / vùng tab nằm **BÊN TRONG** nhánh `content` ⇒ A5 đúng **bằng cấu trúc**, không nhờ prop.
- Import **chỉ** 3 file cùng thư mục (`DetailLoadError.vue`, `DetailTabBar.vue`, `SkeletonLoader.vue`) + 1 import
  **type-only** từ `@/api/errors`.
- Chỉ dùng class `@layer` (`page-container`, `card`) + utility phi màu (`p-6`, `gap-4`, `grid-cols-*`).
  **0** class palette thô. **0** class `min-[…]:` / `max-[…]:` (guard `TC-RWD-01`).
- **0** lần xuất hiện chuỗi nhãn nút nạp lại trong file — **kể cả trong comment** (A2).

---

## §4. Áp cho 3 màn thật — delta bắt buộc từng file

### 4.0 Khuôn chung phần `<script setup>` (cả 3 màn)

```ts
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { loadErrorKind, toApiError, type DetailLoadKind } from '@/api/errors'

const loading = ref(true)                       // ⚠️ true, KHÔNG false (chống nháy 404 một nhịp)
const loadFailed = ref<'' | DetailLoadKind>('')
const loadErrMsg = ref('')

async function load() {
  loading.value = true
  loadFailed.value = ''                          // xoá lỗi ĐẦU lượt (INV-UX4-7)
  loadErrMsg.value = ''
  try {
    record.value = await <fetch>(<id>)
  } catch (e: unknown) {
    loadFailed.value = loadErrorKind(e)
    loadErrMsg.value = toApiError(e).message
    record.value = null                          // hỏng ⇒ dọn dữ liệu cũ
  } finally {
    loading.value = false
  }
}
```

Khuôn chung phần `<template>`: `DetailPageShell` là **thẻ gốc duy nhất** của view (bỏ `<div class="page-container
animate-fade-in space-y-5">` cũ — nếu giữ sẽ lồng 2 lớp `page-container`). Mọi slot có deref bản ghi phải bọc
`<template v-if="<record>">` (INV-UX4-12): vừa khôi phục type-narrowing cho `vue-tsc` (mất khi rời khỏi
`v-else` cũ), vừa là lớp phòng vệ nếu sau này ai đó đổi điều kiện render slot.

### 4.1 `views/incident/CAPADetailView.vue` — nặng nhất (chưa có `DetailLoadError`)

| Việc | Chi tiết |
|---|---|
| Xoá | `loadError` (chuỗi phẳng) `:80`; nhánh `v-else-if="!capa"` `:180` (**dòng `text-red-500` duy nhất của file**); `<div v-if="loading">` `:179`; thẻ gốc `page-container` `:173`; import `SkeletonLoader` (shell lo) |
| Thêm | `loadFailed` / `loadErrMsg` theo §4.0; import `DetailPageShell`, `loadErrorKind`, `toApiError` |
| `#title` | giữ nguyên khối `:174-177` (nút «← Quay lại» + `<h1>Chi tiết hành động khắc phục/phòng ngừa</h1>`) — **tĩnh, không deref `capa`** |
| `#header` | thẻ `card` `:184-241` (mã + mô tả + 3 badge + lưới 4 ô + link nguồn), bọc `<template v-if="capa">` |
| `#actions` | **nội dung** của `:244-258` — bỏ thẻ `<div class="card p-4 flex flex-wrap items-center gap-2">` (shell đã bọc), giữ nguyên mọi `data-testid` |
| mặc định | `card` nội dung QMS `:261-288` + `<RecordHistory>` `:291` + **cả 3** `<BaseModal>` `:295-388` |
| Props shell | `entity-label="hành động khắc phục/phòng ngừa"` · `:record-id="name"` · `back-label="Về danh sách hành động khắc phục/phòng ngừa"` · `@retry="load()"` · `@back="router.push('/capas')"` |
| Không đụng | `text-red-600` `:218` (tô đỏ **hạn xử lý quá hạn** — khác nghiệp vụ, A7c chỉ cấm `text-red-500`) |

### 4.2 `views/compliance/InternalAuditDetailView.vue` — thêm tab + KPI

| Việc | Chi tiết |
|---|---|
| Sửa | `const loading = ref(false)` `:24` → `ref(true)` (**AC-UX-050**); `const activeTab = ref<string>('overview')` (nới kiểu — emit trả `string`) |
| Xoá | `<div v-if="loading">` `:188`; `<DetailLoadError v-else-if="!audit">` `:190-199`; `<template v-else>` `:201`; **cả khối `<nav>` tab tự chế `:244-265`**; thẻ gốc `page-container` `:187` |
| Thêm | `const AUDIT_TABS = [{ key: 'overview', label: 'Tổng quan' }, { key: 'checklist', label: 'Bảng kiểm' }, { key: 'report', label: 'Báo cáo & Phát hiện' }]` — **nhãn giữ NGUYÊN chuỗi** (Never §0) |
| Thêm | `const nonConformingCount = computed(() => persistedChecklist.value.filter(r => r.result === 'Non-Conforming').length)` |
| `#title` | *(không dùng — `PageHeader` đã có breadcrumb + back; giữ nguyên hành vi hiện tại)* |
| `#header` | `<PageHeader>` `:202-219` **bỏ `<template #actions>`** + thẻ tóm tắt `:222-241`, bọc `<template v-if="audit">` |
| `#actions` | 2 nút + hint `:213-217` (`cta-start`, `cta-close`, `no-actions-hint`) — nguyên văn |
| `#kpi` | **MỚI** 3 `<KpiCard>`: «Số phát hiện» = `audit.findings_count`, «Số mục bảng kiểm» = `persistedChecklist.length`, «Mục không phù hợp» = `nonConformingCount` (color `warning` / `info` / `danger`) — **0 field mới**, tất cả đã có trong `get_audit` |
| Tab | `:tabs="AUDIT_TABS"` + `v-model:active-tab="activeTab"` |
| mặc định | 3 panel `:268-388` giữ nguyên `v-if="activeTab === 'overview'"` / `v-else-if` … + `<BaseModal>` `:391-402` |
| Props shell | `entity-label="cuộc kiểm toán nội bộ"` · `:record-id="props.id"` · `back-label="Về danh sách kiểm toán"` · `@retry="load()"` · `@back="router.push('/compliance/audits')"` |

### 4.3 `views/compliance/ManagementReviewDetailView.vue` — dời panel thao tác

| Việc | Chi tiết |
|---|---|
| Xoá | `<div v-if="loading">` `:205`; `<DetailLoadError v-else-if="!mr">` `:206-215`; `<template v-else>` `:217`; thẻ gốc `page-container` `:204` |
| `#header` | `<PageHeader>` `:218-249` **bỏ `<template #actions>`** + thẻ trạng thái `:251-268`, bọc `<template v-if="mr">` |
| `#actions` | 4 phần tử `:228-247` (nút «Sửa nội dung», `cta-advance`, `cta-close`, `no-actions-hint`) — nguyên văn, nguyên `data-testid` |
| mặc định | `:270-316` (tóm tắt / thành viên / hành động đầu ra / `RecordHistory`) + 2 `<BaseModal>` `:320-400` |
| Props shell | `entity-label="cuộc soát xét quản lý"` · `:record-id="name"` · `back-label="Về danh sách soát xét"` · `@retry="load()"` · `@back="router.push('/compliance/mr')"` |
| Không thêm | `#kpi` (A9 chỉ đòi **≥1** view có dải KPI — đã chọn màn kiểm toán; thêm ở đây là **lan phạm vi**) |

---

## §5. Bất biến đo được (INV-UX4-*)

| Mã | Bất biến | Đo bằng |
|---|---|---|
| **INV-UX4-1** | Đúng **một** chuỗi `v-if/v-else-if/v-else` 4 nhánh trong shell, thứ tự `error > loading > notfound > content` | đọc file + `DetailPageShell.test.ts` (ma trận 16 tổ hợp) |
| **INV-UX4-2** | Mọi tổ hợp props ⇒ **đúng 1** trong `[detail-skeleton, detail-load-error, detail-content]` có mặt, 2 cái kia = 0 | `findAll(...).length` |
| **INV-UX4-3** | `errorKind` thắng **cả** `loading` **lẫn** `doc` còn giá trị | TC-UX4-03 |
| **INV-UX4-4** | `doc=null` + hết `loading` + không lỗi ⇒ nhánh `notfound` (không khung rỗng, không trang trắng) | TC-UX4-04 |
| **INV-UX4-5** | `#actions` / `#kpi` / tab **không** render ở `error`/`loading`/`notfound` | TC-UX4-05 (probe `probe-cta`) |
| **INV-UX4-6** | Shell **0** lần khai chuỗi nút nạp lại; **≥1** lần dùng `DetailLoadError`; **≥1** lần dùng `DetailTabBar` | `grep -c` (A2) |
| **INV-UX4-7** | Mọi `load()` xoá lỗi ở đầu lượt, `doc=null` khi hỏng, hạ `loading` trong `finally` | đọc 3 view + test trạng thái |
| **INV-UX4-8** | `loading` khởi tạo `true` ở cả 3 view (chống nháy 404 một nhịp) | `grep -n 'const loading = ref('` |
| **INV-UX4-9** | 3 view **0** lần `v-if="… status/workflow_state === …"` (GATE-8 / LL-FE-51) | A8 |
| **INV-UX4-10** | Mọi `data-testid` cũ giữ nguyên tên | A10 (5 file test cũ XANH) |
| **INV-UX4-11** | Shell là thẻ gốc **duy nhất** của view; **0** `page-container` lồng nhau | `grep -c 'page-container'` mỗi view = 0 |
| **INV-UX4-12** | Slot có deref bản ghi được bọc `v-if`; `#title` **không** deref bản ghi | `npm run typecheck` XANH + đọc file |
| **INV-UX4-13** | Shell dumb: **0** import `vue-router` / `@/stores/*` / client `@/api/*` (chỉ import **type**) | `grep -nE "from '(vue-router\|@/stores\|@/api)" DetailPageShell.vue` = chỉ dòng `import type` |

---

## §6. Test-case & lệnh chấm

### 6.1 `frontend/src/components/common/DetailPageShell.test.ts` (mount THẬT, ≥12 case)

| TC | Nội dung | Neo acceptance |
|---|---|---|
| **TC-UX4-01** | **Ma trận 16 tổ hợp** `loading ∈ {false,true}` × `errorKind ∈ {null,'unknown','forbidden','notfound'}` × `doc ∈ {null,{…}}`: mỗi tổ hợp ⇒ `findAll('[data-testid="detail-skeleton"]')`, `findAll('[data-testid="detail-load-error"]')`, `findAll('[data-testid="detail-content"]')` có **tổng độ dài = 1** | A3 |
| **TC-UX4-02** | `data-state` khớp bảng §2.1 ở cả 16 tổ hợp | A3 |
| **TC-UX4-03** | `errorKind='unknown'` + `loading=true` + `doc={…}` ⇒ có `detail-load-error`, **0** `detail-content`, **0** `detail-skeleton` | A4 |
| **TC-UX4-04** | `errorKind=null` + `loading=false` + `doc=null` ⇒ `detail-load-error[data-kind="notfound"]`, **0** `detail-content` | A4 |
| **TC-UX4-05** | slot `#actions` = `<button data-testid="probe-cta">`: **false** ở error/loading/notfound, **true** ở content | A5 |
| **TC-UX4-06** | như trên cho `#kpi` (`probe-kpi`) và vùng tab (`detail-tabs`) | A5 |
| **TC-UX4-07** | `errorKind='unknown'` ⇒ có nút nạp lại; bấm 1 lần ⇒ `emitted('retry')` độ dài **1** | A6 |
| **TC-UX4-08** | `errorKind='forbidden'` ⇒ **0** nút nạp lại, **có** nút quay lại; bấm ⇒ `emitted('back')` độ dài 1; `[data-kind="forbidden"]` | A6 |
| **TC-UX4-09** | `errorKind='notfound'` ⇒ như TC-UX4-08 với `[data-kind="notfound"]` | A6 |
| **TC-UX4-10** | `errorMessage` truyền xuống hiện đúng nguyên văn (không bị thay bằng câu mặc định) | A2 |
| **TC-UX4-11** | `tabs=[]` ⇒ **0** `detail-tabs`; `tabs=[…3…]` + click `[data-testid="tab-checklist"]` ⇒ `emitted('update:activeTab')` = `['checklist']` | A9 |
| **TC-UX4-12** | `#title` render ở **cả 4** trạng thái | §2.2 |

> Test **KHÔNG** stub `DetailLoadError` / `DetailTabBar` — phải mount thật, nếu không hợp đồng no-fork không được kiểm chứng.

### 6.2 Ba test trạng thái bám view thật (mỗi file ≥5 case)

`views/incident/capaDetailStates.test.ts` · `views/compliance/internalAuditDetailStates.test.ts` ·
`views/compliance/managementReviewDetailStates.test.ts` — mock lớp API/store **y như** 5 file test cũ
(`vi.mock('@/api/imm16')` / `vi.mock('@/stores/imm16')` / `vi.mock('vue-router')` / `useApi` call-through):

| TC | Nội dung | Neo |
|---|---|---|
| **TC-UX4-2x-a** | fetch reject `ApiError(404)` ⇒ `detail-load-error[data-kind="notfound"]`, **0** `detail-content`, **0** `probe`-CTA cũ (`cta-start`/`cta-edit`/`cta-advance`) | A5, A7 |
| **TC-UX4-2x-b** | fetch reject 403 in-envelope ⇒ `[data-kind="forbidden"]`, **0** nút nạp lại, **có** nút quay lại | A6 |
| **TC-UX4-2x-c** | fetch reject lỗi mạng ⇒ `[data-kind="unknown"]`; bấm nút nạp lại ⇒ hàm fetch được gọi **lần 2** | A6 |
| **TC-UX4-2x-d** | fetch resolve `null` ⇒ nhánh `notfound` (không phải content rỗng) | A4 |
| **TC-UX4-2x-e** | fetch resolve bản ghi ⇒ `detail-content` + CTA theo `allowed_transitions` (giữ nguyên hành vi cũ) | A8 |
| **TC-UX4-22-f** *(chỉ màn kiểm toán)* | click `[data-testid="tab-checklist"]` ⇒ `checklist-editor` **hoặc** `checklist-readonly` xuất hiện; dải `detail-kpi` có mặt ở content | A9 |

### 6.3 Lệnh chấm (QA **tự đo lại**, không nhận báo cáo suông)

```bash
cd frontend

# A1 — vị trí + guard tầng 0 không đổi
ls src/components/ui/*.vue | wc -l                      # == 8
test -f src/components/common/DetailPageShell.vue && echo OK
test ! -f src/components/ui/DetailPageShell.vue && echo OK
npx vitest run src/components/ui                        # XANH

# A2 — no-fork
grep -c 'DetailLoadError' src/components/common/DetailPageShell.vue   # >= 1
grep -c 'DetailTabBar'    src/components/common/DetailPageShell.vue   # >= 1
grep -c 'Thử lại'         src/components/common/DetailPageShell.vue   # == 0

# A3 / A4 / A5 / A6 / A9 — ma trận + probe + kind-aware
npx vitest run src/components/common/DetailPageShell.test.ts

# A7 — áp vào 3 màn thật
for f in src/views/incident/CAPADetailView.vue \
         src/views/compliance/InternalAuditDetailView.vue \
         src/views/compliance/ManagementReviewDetailView.vue; do
  echo "$f: shell=$(grep -c DetailPageShell $f)" \
       "deadend=$(grep -cE 'v-else-if="!(capa|audit|mr)"' $f)" \
       "red500=$(grep -c 'text-red-500' $f)"
done            # shell>=1 · deadend==0 · red500==0

# A8 — chống thoái lui GATE-8
for f in src/views/incident/CAPADetailView.vue \
         src/views/compliance/InternalAuditDetailView.vue \
         src/views/compliance/ManagementReviewDetailView.vue; do
  grep -cE 'v-if="[^"]*(status|workflow_state) ===' $f    # == 0 cả 3
done

# A10 — không thoái lui 5 test cũ
npx vitest run src/views/incident/capaCtaGate.test.ts src/views/incident/CAPADetailView.test.ts \
  src/views/compliance/internalAuditCtaGate.test.ts \
  src/views/compliance/internalAuditChecklistHydration.test.ts \
  src/views/compliance/managementReviewCtaGate.test.ts       # >= 50 tests passed

# A11 — hàng rào phạm vi (3 vế QA TỰ đo)
cd .. && git status --short -uall | grep -E '\.py$' | wc -l            # == 0
git status --short -uall | grep -E 'frontend/src/stores/' | wc -l      # == 0
git status --short -uall | grep -E 'frontend/src/api/'    | wc -l      # == 0
git status --short -uall | grep -E 'frontend/src/views/'                # ⊆ 3 view + 3 test mới

# A12 — delta suite
find frontend/src -name '*.test.ts' -o -name '*.spec.ts' | wc -l       # 305 -> 309
cd frontend && npx vitest run                                          # 0 file đỏ MỚI
npm run typecheck                                                      # XANH (INV-UX4-12)

# A13 — sổ backlog + guard doc
npx vitest run src/router/uiAuditDocParity.test.ts                     # 15/15 XANH
```

---

## §7. Bẫy đã biết — ĐỌC TRƯỚC KHI CODE

### 7.1 `grep -c 'Thử lại'` đếm **cả comment**
A2 chấm bằng `grep`, không phải bằng parser. Muốn giải thích “nhãn nút do `DetailLoadError` sở hữu” thì viết
“**nhãn nút nạp lại**”, tuyệt đối không gõ đúng chuỗi đó trong comment của shell.

### 7.2 Type-narrowing biến mất khi rời `<template v-else>`
Hiện tại `v-else-if="!audit"` + `<template v-else>` khiến `vue-tsc` biết `audit` khác `null` trong toàn bộ khối.
Đưa nội dung vào slot ⇒ mất narrowing ⇒ `npm run typecheck` đỏ hàng loạt (`'audit' is possibly 'null'`).
**Cách đúng**: bọc `<template v-if="audit">` ngay bên trong mỗi slot có deref (INV-UX4-12).
**Cách sai**: rải `!` (`audit!.name`) — che lỗi thật và vi phạm “không dead-control”.

### 7.3 Ba test cũ tìm tab **bằng đúng chuỗi nhãn**
`internalAuditCtaGate.test.ts:84` và `internalAuditChecklistHydration.test.ts:69` dùng
`w.findAll('button').find(b => b.text() === 'Bảng kiểm')`. `DetailTabBar` render `{{ tab.label }}` trong
`<button>` ⇒ vẫn khớp **nếu** nhãn giữ nguyên **chính xác** `Bảng kiểm` (không thêm số đếm, không thêm icon,
không đổi thành «Bảng kiểm (3)»).

### 7.4 `activeTab` phải là `ref<string>`
`update:activeTab` phát `string`; nếu ref khai kiểu hẹp `ref<'overview' | 'checklist' | 'report'>` thì
`v-model:active-tab` **đỏ typecheck**. Nới thành `ref<string>('overview')`; các panel vẫn so bằng
`activeTab === 'checklist'` nên hành vi không đổi.

### 7.5 5 file test cũ **không** stub `DetailPageShell`
Chúng chỉ stub `PageHeader`, `BaseModal`, `StatusBadge`, `SkeletonLoader`, `RecordHistory`, `RouterLink`.
Shell sẽ mount **thật** — đây là điều ta muốn (test cũ trở thành test tích hợp cho khuôn mới). Hệ quả:
**mọi CTA phải nằm trong `content`**, nếu không 5 file đó đỏ ngay. Đồng thời `SkeletonLoader: true` là stub
component ⇒ vùng `detail-skeleton` vẫn tồn tại (ta đếm `div` bọc, không đếm ruột khung xương).

### 7.6 `PageHeader` bị **stub khác nhau** giữa các test
`internalAuditCtaGate.test.ts:45` stub `PageHeader` có render `<slot name="actions" />`, còn
`managementReviewCtaGate.test.ts` **không** stub (dùng `PageHeader` thật). Vì CTA nay chuyển sang `#actions`
của shell, cả hai đường đều tìm thấy nút bằng `data-testid` ở gốc wrapper ⇒ an toàn cả 2 kiểu stub. **Đừng**
để CTA nằm đồng thời ở 2 nơi (PageHeader `#actions` **và** shell `#actions`) — sẽ có 2 nút cùng `data-testid`,
`w.find()` lấy nút đầu và `findAll().length` = 2 làm test đếm đỏ.

### 7.7 `ref="historyRef"` nằm trong slot vẫn hoạt động
Nội dung slot được biên dịch trong **phạm vi của view cha**, nên `<RecordHistory ref="historyRef">` vẫn gán
đúng. Khi ở trạng thái lỗi/404 slot không render ⇒ `historyRef.value` là `null`; `refreshAll()` đã dùng
`historyRef.value?.reload()` nên an toàn — **giữ nguyên dấu `?.`**.

### 7.8 Nhánh `notfound` là mặc định khi `doc` chưa nạp
Vì `state` trả `notfound` khi `doc` rỗng, **thứ tự khởi tạo** quyết định có nháy 404 hay không:
`loading = ref(false)` (hiện trạng `InternalAuditDetailView.vue:24`) ⇒ lượt render **trước** `onMounted` rơi
vào `notfound`. Bắt buộc `ref(true)` (INV-UX4-8).

### 7.9 `page-container` lồng nhau
Shell đã mang `page-container animate-fade-in space-y-5`. Nếu view giữ lại `<div class="page-container …">`
bọc ngoài thì padding/max-width nhân đôi. Xoá thẻ gốc cũ (INV-UX4-11).

### 7.10 Guard `TC-RWD-01` cấm breakpoint tuỳ biến trong `src/views`
`src/__tests__/responsiveDoD.test.ts:32` cấm `min-[…]:` / `max-[…]:` **trong `src/views`**. Dải KPI dùng
`grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` (breakpoint chuẩn) — an toàn.

### 7.11 Sổ `AC-UX-*` bị guard doc khoá
`src/router/uiAuditDocParity.test.ts:180-224` yêu cầu §6 của `00_AUDIT_HIEN_TRANG.md`: mã **liên tục từ 001**,
mỗi dòng đúng **6 ô**, cột *Đau* ∈ {P0,P1,P2}, cột *Vòng* ∈ {2,3,4,5}, và dòng `**Tổng: N mục` **khớp** số
dòng. Thêm mục mới mà quên sửa `Tổng` ⇒ đỏ.

⚠️ Bẫy đã cắn khi viết tài liệu này: `cellsOf()` (`:60-63`) **split thô** trên ký tự `|`. Một ô chứa `\|`
(escape pipe của markdown, vd trong đoạn lệnh `grep -L 'A\|B'`) tạo **7 ô** ⇒ dòng bị **bỏ qua**, làm dãy
`AC-UX-*` “nhảy cóc” và `Tổng` lệch — hai test đỏ cùng lúc, thông báo lỗi lại chỉ nói về số tổng. Trong §6
**không** dùng `|` dưới mọi hình thức; diễn đạt lại bằng lời.

---

## §8. Danh mục file được phép chạm — vòng 4 (A11)

| # | File | Loại | Ghi chú |
|---|---|---|---|
| 1 | `frontend/src/components/common/DetailPageShell.vue` | **mới** | §3.4 |
| 2 | `frontend/src/components/common/DetailPageShell.test.ts` | **mới** | §6.1 |
| 3 | `frontend/src/views/incident/CAPADetailView.vue` | sửa | §4.1 |
| 4 | `frontend/src/views/compliance/InternalAuditDetailView.vue` | sửa | §4.2 |
| 5 | `frontend/src/views/compliance/ManagementReviewDetailView.vue` | sửa | §4.3 |
| 6 | `frontend/src/views/incident/capaDetailStates.test.ts` | **mới** | §6.2 |
| 7 | `frontend/src/views/compliance/internalAuditDetailStates.test.ts` | **mới** | §6.2 |
| 8 | `frontend/src/views/compliance/managementReviewDetailStates.test.ts` | **mới** | §6.2 |
| 9 | `docs/ui-ux/03_DETAIL_PAGE_SHELL.md` | **mới** | tài liệu này |
| 10 | `docs/ui-ux/00_AUDIT_HIEN_TRANG.md` | sửa (light-touch) | §Tài liệu liên quan · §6 sổ · §9 ADR · §10 ghim |

**Ngoài danh sách trên = ngoài phạm vi.** Đặc biệt: **0** file `.py`, **0** file dưới `frontend/src/stores/`,
**0** file dưới `frontend/src/api/`, **0** file `frontend/src/components/ui/**`.

---

## §9. Truy vết Acceptance A0–A13 ⇄ spec ⇄ lệnh đo

| AC | Yêu cầu | Spec | Lệnh đo |
|---|---|---|---|
| **A0** | vòng 3 đã đóng | §1.3 (đo lại: 5 file / 40 test XANH) | §6.3 (đã chạy 14:31) |
| **A1** | shell ở `common/`, `ui/` vẫn 8 | §3.0 + **ADR-UX-06** | `ls … \| wc -l` · `vitest run src/components/ui` |
| **A2** | no-fork `DetailLoadError` + `DetailTabBar`, 0 chuỗi nút nạp lại | §3.3, §3.4, §7.1, INV-UX4-6 | 3 lệnh `grep -c` |
| **A3** | 4 trạng thái loại trừ bằng cấu trúc, ma trận ≥8 | §2.1, §3.4, TC-UX4-01/02 | `vitest run DetailPageShell.test.ts` |
| **A4** | ưu tiên lỗi; `doc=null` ⇒ notfound | §2.1 (giải thích), TC-UX4-03/04 | như trên |
| **A5** | panel thao tác/tab/KPI chỉ ở content | §2.2, §3.4, TC-UX4-05/06 | như trên |
| **A6** | kind-aware retry/back | §3.2, TC-UX4-07/08/09 | như trên |
| **A7** | áp 3 màn thật, xoá nhánh ngõ cụt + `text-red-500` | §4.1–4.3 | vòng lặp `grep` §6.3 |
| **A8** | GATE-8 giữ nguyên | §0 Always, INV-UX4-9 | `grep -cE 'v-if=…==='` |
| **A9** | tab qua `DetailTabBar` + ≥1 dải KPI | §3.3, §4.2, TC-UX4-11, TC-UX4-22-f | `vitest run` 2 file |
| **A10** | 5 test cũ ≥50 test XANH, testid giữ tên | §0 Never, §7.3, §7.5, §7.6, INV-UX4-10 | `vitest run` 5 file |
| **A11** | hàng rào phạm vi | §8 | 4 lệnh `git status` |
| **A12** | delta suite +4 file, 0 đỏ mới | §1.3 (baseline 305/2951/0 đỏ) | `find … \| wc -l` · `vitest run` · `npm run typecheck` |
| **A13** | sổ mở từ `AC-UX-048`, ghi 2 khoản nợ bắt buộc | §6 tài liệu mẹ (`AC-UX-048`, `AC-UX-049`) + §7.11 | `vitest run uiAuditDocParity.test.ts` |

---

## §10. Rủi ro & việc để lại vòng 5

| Rủi ro | Xác suất | Giảm thiểu |
|---|---|---|
| 5 test cũ đỏ vì CTA rơi ra ngoài `content` | trung bình | §7.5 + chạy A10 **trước** khi khai báo xong |
| `vue-tsc` đỏ do mất narrowing | **cao** | §7.2 — bọc `v-if` trong slot; `npm run typecheck` là điều kiện đóng |
| Đổi vị trí CTA (từ `PageHeader` sang panel riêng) gây phản hồi UX | thấp | panel `card p-4` ngay dưới header, cùng khuôn với màn CAPA hiện có; nếu USER phản đối ⇒ đảo lại **chỉ** ở lớp view, hợp đồng shell không đổi |
| Nháy tab khi `activeTab` nới kiểu `string` | thấp | panel vẫn so chuỗi; test TC-UX4-22-f khoá |

**Để lại (KHÔNG làm ở vòng 4):**
- `AC-UX-048` — **20/32** màn chi tiết còn lại chưa có lối nạp lại (sau khi CAPA nhận khuôn ở vòng này). Chia lô theo module, mỗi lô kèm test trạng thái.
- `AC-UX-049` — 5 chỗ hardcode `plan.workflow_state === 'Draft'` ở `ProcurementPlanDetailView.vue:168,192,219,231,241`; **hard-dependency**: cần BE emit cờ `can_edit` trong `get_procurement_plan` trước.
- `AC-UX-052` — 27/32 màn chi tiết chưa dùng `DetailTabBar`.
- `AC-UX-053` — `useDetailAccess` mới lan tới 3/32 màn; cân nhắc để `DetailPageShell` nhận thẳng `access` thay vì 3 prop rời (đo lại sau khi có ≥8 màn áp khuôn).

---

## §11. Quyết định kiến trúc

Xem **ADR-UX-06** và **ADR-UX-07** ở [`00_AUDIT_HIEN_TRANG.md` §9](./00_AUDIT_HIEN_TRANG.md) (SSoT của mọi ADR
lớp UI/UX — không nhân bản nội dung ADR ở đây).

---

## §12. LÔ 1 adoption `DetailPageShell` — 8 màn CHI TIẾT (`AC-UX-048`, đo 2026-08-03)

| Mục | Giá trị |
|---|---|
| Đề mục | `AC-UX-048` **lô 1** — KHÔNG cấp số sổ mới (sổ `AC-UX` đóng băng ở **058**) |
| Phạm vi | **đúng 8** màn CHI TIẾT thuộc IMM-03/07/10/14/15/16 — danh sách chốt ở §12.2 |
| Loại | Core Doc cross-cutting (UI/UX) — spec thi hành cho FE dev, **spec-before-code gate** |
| Ngày đo | **2026-08-03** — mọi số dưới đây đo TỪ ĐĨA hôm nay, KHÔNG kế thừa số trong prompt/STATE |
| Nhánh | `feature/hieuc/core-refinement` |
| Tài liệu cha | §0–§11 của chính tài liệu này (khuôn + hợp đồng API `DetailPageShell` đã chốt vòng 4) |
| Tài liệu anh | [`02_LIST_PAGE_SHELL.md §12`](./02_LIST_PAGE_SHELL.md) — lô 1 lớp DANH SÁCH (khuôn sổ-lô + guard parity mà lô này mô phỏng) |
| Trạng thái | **Chốt để code** |

> **Vì sao đúng 8 màn này.** Cả 8 đều nằm trong **20 màn chi tiết còn nợ** của `AC-UX-048` (`00 §6`, dòng sổ đã
> có từ vòng 4) và cả 8 **cùng một triệu chứng đo được**: `grep -LE 'DetailLoadError|@retry|DetailPageShell'`
> → **0 hit** ⇒ hôm nay nạp bản ghi hỏng ở 8 màn này, người dùng KHÔNG có bất kỳ lối nạp lại nào. Tệ hơn lớp
> danh sách: **panel thao tác vẫn hiện trên bản ghi hỏng** (`SupplierDetailView.vue:89-110` render `PageHeader`
> + 2 nút NGOÀI chuỗi trạng thái; `AssetTransferDetailView.vue:163-196` render cả cụm CTA vòng đời TRƯỚC nhánh
> `v-if="loading"`), và một màn **báo lỗi bằng dải MÀU XANH thành công** (`WarehouseDetailView.vue:26` gán lỗi
> nạp vào `toast`, template `:81` tô `bg-emerald-50 text-emerald-700`). Đây đúng class-of-bug mà vòng 4 dựng
> khuôn để diệt — lô 1 áp khuôn, **không vá lẻ**.

### 12.1 Số đo TỪ ĐĨA hôm nay (baseline chấm DELTA) — có DRIFT so với tài liệu ĐO

| Đại lượng | Lệnh | **Đĩa 2026-08-03** | Prompt/STATE | Kết luận |
|---|---|---|---|---|
| `*DetailView.vue` tổng | `find frontend/src/views -name '*DetailView.vue'` | **32** | 32 | khớp |
| Màn đã dùng shell | `grep -rl DetailPageShell … --include=*DetailView.vue` | **3** | 3 | khớp |
| Màn CHƯA dùng shell | `grep -L DetailPageShell $(find … -name '*DetailView.vue')` | **29** | 29 | khớp — sau lô 1 phải là **21** |
| Màn **0 lối nạp lại** (không `DetailLoadError`, không `@retry`, không shell) | vòng lặp `grep -qE` | **20** | 20 | khớp — mốc token `[NO-DET=…]` |
| `text-red-500` trong 8 file lô 1 | vòng lặp `grep -cE` | **4** (AssetTransfer **3** · FirmwareCr **1**) | 3 + 1 | khớp |
| `TC-UX4-*` lớn nhất | `grep -rhoE 'TC-UX4-[0-9]+' docs frontend/src` | **TC-UX4-23** | 23 | khớp — lô 1 dùng **24…31** |
| `INV-UX4-*` lớn nhất | grep | **INV-UX4-13** | — | lô 1 dùng namespace MỚI `INV-UX4L1-1…6` |
| Sổ `AC-UX` lớn nhất / tổng | `grep -rhoE 'AC-UX-[0-9]{3}' docs frontend/src` | **058 / 58 mục** | 058 | khớp — **CẤM cấp số mới** |
| `ADR-UX-*` lớn nhất | grep | **ADR-UX-11** | — | lô 1 dùng **ADR-UX-12** |
| File test FE **trước** bước BA | `find frontend/src -name '*.test.ts' -o -name '*.spec.ts'` | **327** | — | mốc DELTA của cả vòng: cuối vòng phải **336** (+9) |
| File test FE **sau** bước BA | như trên | **328** (+1 = guard `uiDetailShellLot1Parity.test.ts`, **17 TC**) | — | ⇒ phần FE còn lại là **+8** file test trạng thái |
| Suite FE **sau** bước BA | `npx vitest run` (đo 13:54) | **328 file / 3222 test — 0 ĐỎ** | — | mốc chấm delta của FE; cuối vòng phải **336 file**, vẫn 0 đỏ |
| `npm run typecheck` sau bước BA | `vue-tsc --noEmit` | **XANH** | — | điều kiện đóng vòng |

**Số đo SAU khi FE land lô 1 (2026-08-03 14:29 — đo lại TỪ ĐĨA, không chép lại số ở trên):**

| Đại lượng | **Trước lô 1** | **Sau lô 1** | Delta |
|---|---|---|---|
| `grep -L DetailPageShell $(find frontend/src/views -name '*DetailView.vue')` | 29 | **21** | −8 ✅ |
| Màn `*DetailView.vue` **0 lối nạp lại** (token `[NO-DET=N]`) | 20 | **12** | −8 ✅ |
| `text-red-500` trong 8 file lô 1 | 4 | **0** | −4 ✅ (đổi sang `text-danger-500`, dấu sao GIỮ) |
| `page-container` trong 8 file lô 1 | 8 | **0** | −8 ✅ (shell mang lớp bao) |
| File test FE (`*.test.ts` + `*.spec.ts`) | 327 (trước BA) / 328 (sau BA) | **336** | +9 ✅ (8 file trạng thái + 1 guard) |
| `npx vitest run` toàn bộ `frontend/` | 328 file / 3222 test — 0 đỏ | **336 file / 3287 test — 0 đỏ** | +65 case, 0 thoái lui |
| `npm run typecheck` (`vue-tsc --noEmit`) | XANH | **XANH** | — |
| Sổ `AC-UX` lớn nhất | 058 | **058** | KHÔNG cấp số mới ✅ |

**Bằng chứng render THẬT** (Playwright @ `localhost:3000`, ảnh ở `.playwright/eval/`, gitignored):
`acux048-lot1-firmware-notfound.png` (`/cm/firmware/FCR-KHONG-TON-TAI-9999`) và
`acux048-lot1-supplier-notfound.png` (`/suppliers/SUP-KHONG-TON-TAI-9999`) — cả hai cho thấy
`data-state="error"` · `data-kind="notfound"` · thông báo tiếng Việt kèm **mã người dùng đã gõ** ·
nút quay về danh sách · **0** `detail-actions` · **0** nút «Thử lại» (đúng cho 404) · tiêu đề màn vẫn hiện.
⚠️ Ảnh trạng thái **content** live CHƯA chụp được: phiên đang đăng nhập (`Phạm Văn Đức`) có
`inventory.read=false` + `procurement.read=false` (chặn 5/8 route ngay ở router guard) và 2 route còn
tới được (`/cm/firmware`, `/suppliers`) đang **0 bản ghi / 403 ở lớp danh sách**. Trạng thái `content`
được phủ bằng **mount THẬT** ở cả 8 file `*DetailStates.test.ts` (sub-case *f*). → việc của [QA].

**Chốt BA (ràng buộc nghiệm thu, thay số phỏng đoán trong prompt):**
- Nợ `AC-UX-048` = **20 → 12** sau lô 1 (token `[NO-DET=N]` ở `00 §6`). Vòng 4 đóng 1 màn (CAPA) từ 21 ⇒ hôm nay
  đúng **20**, đã đo lại bằng vòng lặp `grep` chứ không đọc lại chữ trong sổ.
- `grep -L DetailPageShell` = **29 → 21** (DELTA đúng **−8**). Hai phép đếm này **khác nhau** và **không được
  trộn**: `32 − 3 = 29` là *chưa dùng khuôn*; **20** là *chưa có lối nạp lại nào* (9 màn dùng
  `DetailLoadError`/`@retry` mà chưa dùng shell). Lô 1 làm giảm **cả hai**, mỗi phép đúng −8.
- `text-red-500` trong 8 file: **4 → 0**. Cả 4 lần đều là **dấu sao trường bắt buộc**
  (`<span class="text-red-500">*</span>`) — thay bằng token ngữ nghĩa **`text-danger-500`**
  (`tailwind.config.js:61` = `#dc2626`, có `--ac-color-danger-500` đối ứng `main.css:33`). **KHÔNG** xoá dấu sao
  (mất tín hiệu trường bắt buộc = lỗi a11y mới), **KHÔNG** đổi sang `text-red-600`.
- **DRIFT đã phát hiện trong tài liệu ĐO** — ghi lại để không ai "sửa cho tròn":
  1. `00 §3.1` dòng **134** `/procurement-decisions/:id` đang chấm ô *Lỗi+Thử lại* = **✅**, nhưng đĩa hôm nay
     `grep -cE 'DetailLoadError|@retry|Thử lại'` trên `DecisionDetailView.vue` = **0** ⇒ ô ✅ đó **sai từ bảng
     tay vòng 1**. Vì vậy guard lô 1 bám cột «Trạng thái» của **sổ lô** (§12.2), **không** bám ô §3.1 hai chiều
     (xem **ADR-UX-12**). Sau khi FE land, dòng 134 sẽ ✅ **đúng lý do**.
  2. `DetailPageShell.vue:43` có prop **`notFound?: boolean`** không nằm trong bảng props §3.1 của tài liệu này
     (thêm sau khi §3 được viết). Prop có thật, mặc định `false`, tham gia `state` tại `:83`
     (`if (props.notFound || !props.doc) return 'notfound'`). Đã bổ sung vào §3.1; lô 1 **được phép dùng** khi
     view muốn phân loại 404 tường minh.

### 12.2 Sổ lô 1 — 8 route (SSoT; guard `uiDetailShellLot1Parity.test.ts` đọc CHÍNH bảng này)

| # | Route | View file | Hàm nạp | Nguồn lỗi sau sửa | Module cần `vi.mock` | Trạng thái | TC |
|---|---|---|---|---|---|---|---|
| 1 | `/stock-movements/:name` | `frontend/src/views/inventory/StockMovementDetailView.vue` | `load()` `:18` | `loadKind` + `loadMsg` (ref MỚI) — `load()` hiện **0 catch** | `@/api/inventory` → `getStockMovement` + `submitStockMovement` + `cancelStockMovement` + `deleteStockMovement` | ĐÃ ĐÓNG | `TC-UX4-24` |
| 2 | `/warehouses/:name` | `frontend/src/views/inventory/WarehouseDetailView.vue` | `load()` `:23` | ref MỚI — **GỠ** lỗi nạp khỏi `toast` `:26` | `@/api/inventory` → `getWarehouse` + `updateWarehouse` + `deleteWarehouse` | ĐÃ ĐÓNG | `TC-UX4-25` |
| 3 | `/spare-parts/:name` | `frontend/src/views/inventory/SparePartDetailView.vue` | `load()` `:33` | ref MỚI — `load()` hiện **0 catch** | `@/api/inventory` → `getSparePart` + `updateSparePart` + `deleteSparePart` · `@/api/purchase` → `getPartPurchases` | ĐÃ ĐÓNG | `TC-UX4-26` |
| 4 | `/asset-transfers/:id` | `frontend/src/views/asset/AssetTransferDetailView.vue` | `load()` `:89` | ref MỚI — **KHÔNG** dùng `err` `:18` (đang là lỗi HÀNH ĐỘNG) | `@/api/imm00` → `getTransferFull` + `updateTransfer` + `approveTransfer` · `@/api/helpers` → `frappePost` | ĐÃ ĐÓNG | `TC-UX4-27` |
| 5 | `/cm/firmware/:id` | `frontend/src/views/document/FirmwareCrDetailView.vue` | `load()` `:21` | **`err` `:19` ĐÃ CÓ** (chỉ phục vụ nạp) → thay bằng cặp kind + message | `@/api/imm00` → `getFirmwareCr` + `transitionFirmwareCr` · `@/composables/useApi` · `@/composables/useNotify` | ĐÃ ĐÓNG | `TC-UX4-28` |
| 6 | `/compliance/findings/:id` | `frontend/src/views/compliance/FindingDetailView.vue` | `load()` `:28` | ref MỚI — `catch` hiện **nuốt lỗi vào `console.error`** `:33` | `@/api/imm16` → `getFinding` · `@/stores/imm16` · `@/composables/useApi` · `@/composables/useCapabilities` | ĐÃ ĐÓNG | `TC-UX4-29` |
| 7 | `/suppliers/:id` | `frontend/src/views/purchase/SupplierDetailView.vue` | `load()` `:36` | ref MỚI — **KHÔNG** tái dùng `error` `:18` (đang DÙNG CHUNG với `remove()` `:63`) | `@/api/imm00` → `getSupplier` + `deleteSupplier` · `@/api/purchase` → `listPurchases` | ĐÃ ĐÓNG | `TC-UX4-30` |
| 8 | `/procurement-decisions/:id` | `frontend/src/views/procurement/DecisionDetailView.vue` | `onMounted` `:348` → `store.fetchDecision` | ref MỚI **trong view** — `store.error` là CHUỖI, không phân loại được kind | `@/api/imm03` → `getDecision` + `getEvaluation` + `awardDecision` + `recordContract` + `transitionDecisionWorkflow` · `@/composables/useNotify` · cần Pinia | ĐÃ ĐÓNG | `TC-UX4-31` |

**Cột «Trạng thái» là cờ tiến độ do guard đọc:** `CHƯA` (BA chốt spec) → `ĐÃ ĐÓNG` (FE land trong CÙNG lượt với
mã). Guard ép **2 chiều**: `view import DetailPageShell` ⟺ ô = `ĐÃ ĐÓNG`. Đổi ô mà không land mã, hoặc land mã
mà quên đổi ô ⇒ **ĐỎ ngay** (INV-UX4L1-4).

**Bốn biến thể nguồn lỗi — không có biến thể thứ năm:**
- **A. `load()` KHÔNG có `catch`** (màn 1, 3) — lỗi nổi lên thành unhandled rejection, view kẹt ở nhánh
  `v-else-if="<record>"` false ⇒ **trang trắng câm**. Thêm `catch` + 2 ref mới.
- **B. lỗi nạp đi nhầm kênh** (màn 2, 6) — Warehouse gán vào `toast` (dải **XANH** thành công), Finding gán vào
  `console.error` (người dùng thấy **trang trắng**). Gỡ khỏi kênh cũ, đưa vào `errorKind`.
- **C. có ref lỗi nhưng DÙNG CHUNG với hành động** (màn 4, 7) — nối thẳng vào shell sẽ khiến **1 lần bấm
  Xoá/Phê duyệt hỏng xoá trắng cả bản ghi đang xem**. Bắt buộc **ref MỚI** cho lượt nạp; ref cũ giữ nhiệm vụ cũ.
- **D. lỗi nạp nằm trong store** (màn 8) + **1 màn đã sạch** (màn 5 — `err` chỉ phục vụ nạp). Với màn 8:
  `stores/imm03.ts:102-107` `fetchDecision` **`throw e` lại** sau khi set `error` ⇒ `onMounted` hiện **không
  bắt** (unhandled rejection). View phải tự `try/catch` và tự phân loại; **KHÔNG sửa `stores/`**.

### 12.3 Boundaries lô 1

**Always:**
- Giữ nguyên 4 trạng thái loại trừ + thứ tự `error > loading > notfound > content` của §2 — **không** khai lại
  máy trạng thái trong view, **không** thêm nhánh thứ 5.
- Mỗi hàm nạp theo đúng khuôn §12.4.0: **xoá lỗi ở DÒNG ĐẦU** (`INV-UX4-7`), `catch` phân loại bằng
  `loadErrorKind(e)` + lấy câu thật bằng `toApiError(e).message`, **dọn bản ghi về `null`** khi hỏng, `finally`
  hạ `loading`, và `const loading = ref(true)` (`INV-UX4-8` — chống nháy 404 một nhịp).
- **Mọi CTA vòng đời** chuyển vào slot `#actions` của shell — kể cả CTA đang nằm trong `PageHeader #actions`.
  Đây là giá trị lõi của lô: hết bấm nút vòng đời trên bản ghi không tồn tại.
- Shell là **thẻ gốc duy nhất** của view (`INV-UX4-11`); xoá thẻ `page-container` cũ.
- Mọi slot có deref bản ghi bọc `<template v-if="<record>">` (`INV-UX4-12`) — khôi phục type-narrowing cho `vue-tsc`.
- `tabs` để **mặc định `[]`** cho **cả 8 màn** — thanh tab là `AC-UX-052`, **vòng 5**.

**Ask first (dừng, hỏi BA/PM):**
- Áp shell cho màn chi tiết **thứ 9** trở đi trong cùng vòng (đó là lô 2).
- Sửa `frontend/src/stores/**`, `frontend/src/api/**`, `frontend/src/components/ui/**`, hoặc
  `components/common/DetailPageShell.vue` — lô 1 **không cần** (đã kiểm chứng từng màn ở §12.2).
- Dùng slot `#kpi`. Hai màn có dải KPI sẵn (2, 3) **giữ NGUYÊN vị trí hiện tại** trong slot mặc định; dời sang
  `#kpi` = đổi lưới = rủi ro layout không cần thiết cho lô này.
- Trích `useDetailLoad()` composable (nợ `AC-UX-053`) — **không** làm ở lô 1: 8 màn cùng lúc + đổi khuôn là 2
  rủi ro chồng nhau.
- Đổi bất kỳ `data-testid` nào đang bị test cũ khoá (danh sách ở §12.7 mục 7.13).

**Never:**
- **KHÔNG** đụng bất kỳ file `.py` nào (`git status --porcelain -- '*.py'` phải RỖNG cuối vòng).
- **KHÔNG** sửa `frontend/src/api/errors.ts` — `loadErrorKind` / `toApiError` / `DetailLoadKind` là hợp đồng đã
  chốt (CR-74); lô 1 chỉ **tiêu thụ**.
- **KHÔNG** đụng `DetailPageShell.vue` / `DetailLoadError.vue` / `DetailTabBar.vue` — khuôn đã chốt vòng 4.
- **KHÔNG** kéo `DetailTabBar` / `AC-UX-052` vào lô này.
- **KHÔNG** di trú overlay tự vẽ (`AC-UX-055/056`): 3 file lô 1 nằm trong allowlist đóng băng 30 của
  `modalOverlayHygiene.test.ts:61-97` (`AssetTransferDetailView` `:66` · `SparePartDetailView` `:77` ·
  `WarehouseDetailView` `:80`). Thêm overlay mới ⇒ ĐỎ; bỏ overlay cũ ⇒ ngoài phạm vi lô.
- **KHÔNG** đưa lỗi HÀNH ĐỘNG (lưu / duyệt / xoá / chuyển trạng thái) vào `:error-kind` — 1 lần bấm hỏng sẽ
  **thay cả màn bằng banner lỗi**. Lỗi hành động giữ nguyên kênh cũ (`err` / `toast` / `notify`).
- **KHÔNG** thêm `console.error` mới; **KHÔNG** để `catch {}` rỗng.

### 12.4 Delta bắt buộc từng file

#### 12.4.0 Khuôn chung `<script setup>` — áp cho cả 8 màn (bản lô-1 của §4.0)

```ts
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { loadErrorKind, toApiError, type DetailLoadKind } from '@/api/errors'

const loading = ref(true)                       // ⚠️ true, KHÔNG false
const loadKind = ref<'' | DetailLoadKind>('')
const loadMsg = ref('')

async function load() {
  loadKind.value = ''                            // DÒNG ĐẦU — xoá lỗi (INV-UX4-7 / AC (g))
  loadMsg.value = ''
  loading.value = true
  try {
    record.value = await <fetch>(<id>)
  } catch (e: unknown) {
    loadKind.value = loadErrorKind(e)
    loadMsg.value = toApiError(e).message
    record.value = null                          // hỏng ⇒ dọn dữ liệu cũ
  } finally {
    loading.value = false
  }
}
```

Khuôn chung `<template>` — shell là thẻ gốc **duy nhất**:

```vue
<DetailPageShell
  :loading="loading"
  :error-kind="loadKind"
  :error-message="loadMsg"
  :doc="<record>"
  entity-label="<nhãn VI viết thường>"
  :record-id="<mã bản ghi>"
  back-label="<Về danh sách …>"
  @retry="load()"
  @back="router.push('<route danh sách>')">
  <template #header> … </template>
  <template #actions> … </template>
  … slot mặc định …
</DetailPageShell>
```

**Luật `#title` của lô 1** (quyết định BA — chống tranh cãi từng màn): chỉ đặt tiêu đề/`PageHeader` vào `#title`
khi **mọi** biểu thức trong đó null-safe (`?.` kèm chuỗi dự phòng, hoặc chỉ dùng `props.id` / route param).
Ngược lại → `#header`. Áp dụng: `#title` dùng ở **4 màn** (4, 5, 7, 8); 4 màn còn lại (1, 2, 3, 6) không dùng
`#title` — lối thoát là nút quay lại của `DetailLoadError`, đúng như 3 màn vòng 4.

#### 12.4.1 `views/inventory/StockMovementDetailView.vue` (222 dòng)

| Việc | Chi tiết |
|---|---|
| Sửa | `const loading = ref(false)` `:14` → `ref(true)`; `load()` `:18-22` thêm `catch` theo §12.4.0 (hiện **0 catch**) |
| Thêm | `loadKind` / `loadMsg`; import `DetailPageShell`, `loadErrorKind`, `toApiError` |
| Xoá | thẻ gốc `page-container` `:86`; nhánh `v-if="loading && !doc"` `:87`; `v-else-if="doc"` `:89` |
| `#header` | `<PageHeader>` `:90-106` **bỏ `<template #actions>`** + cụm badge `:107-116`, bọc `<template v-if="doc">` |
| `#actions` | nội dung `:96-105` (Chỉnh sửa · Xoá · Duyệt phiếu · Huỷ phiếu) — nguyên văn, KHÔNG thẻ bọc riêng |
| mặc định | dải `toast` `:118` + mọi thẻ nội dung `:120-220`, bọc `<template v-if="doc">` |
| Props shell | `entity-label="phiếu kho"` · `:record-id="props.name"` · `back-label="Về danh sách phiếu kho"` · `@retry="load()"` · `@back="router.push('/stock-movements')"` |
| Không đụng | `text-red-600` trên nút Xoá/Huỷ `:98,:102` (màu nút hành động, không phải thông báo lỗi) |

#### 12.4.2 `views/inventory/WarehouseDetailView.vue` (234 dòng) — **màn của acceptance (d)**

| Việc | Chi tiết |
|---|---|
| Sửa | `loading = ref(false)` `:17` → `ref(true)`; `load()` `:23-27`: **xoá** `catch … toast.value = … 'Lỗi tải kho'` `:26`, thay bằng `catch` chuẩn §12.4.0 |
| Bất biến | sau sửa `grep -n 'Lỗi tải kho'` = **0 kết quả** — chuỗi biến mất hoàn toàn; câu hiển thị do server + `DetailLoadError` quyết |
| Giữ | `toast` `:20` **nguyên vai trò cũ** = thông báo HÀNH ĐỘNG (`:50` lưu thành công · `:53` lỗi lưu · `:62`/`:66` ngừng hoạt động). Dải `bg-emerald-50` `:81` giữ nguyên nhưng chỉ còn nhận nội dung hành động |
| Xoá | `page-container` `:80`; `v-if="loading && !wh"` `:83`; `v-else-if="wh"` `:85` |
| `#header` | `<PageHeader>` `:86-96` **bỏ `#actions`** + lưới KPI `:99-117`, bọc `<template v-if="wh">` |
| `#actions` | 2 nút `:93-94` (Chỉnh sửa · Ngừng hoạt động) |
| mặc định | dải `toast` `:81` (**dời vào trong** slot mặc định) + `:120-174` + hộp thoại sửa `:179-226` |
| Props shell | `entity-label="kho"` · `:record-id="props.name"` · `back-label="Về danh sách kho"` · `@retry="load()"` · `@back="router.push('/warehouses')"` |

#### 12.4.3 `views/inventory/SparePartDetailView.vue` (390 dòng)

| Việc | Chi tiết |
|---|---|
| Sửa | `loading = ref(false)` `:27` → `ref(true)`; `load()` `:33-43` thêm `catch` (hiện **0 catch**) |
| Xoá | `page-container` `:113`; `v-if="loading && !part"` `:116`; `v-else-if="part"` `:118` |
| `#header` | `<PageHeader>` `:119-129` **bỏ `#actions`** + lưới KPI `:132-150`, bọc `<template v-if="part">` |
| `#actions` | 2 nút `:126-127` (Chỉnh sửa · Ngừng sử dụng) |
| mặc định | `toast` `:114` + `:153-304` (gồm nút tạo đơn mua `:250-251` — **giữ nguyên** gate `can('purchase.create')`, đang bị `router/createButtonAffordance.test.ts:37` khoá) + hộp thoại sửa `:309-382` |
| Props shell | `entity-label="phụ tùng"` · `:record-id="props.name"` · `back-label="Về danh mục phụ tùng"` · `@retry="load()"` · `@back="router.push('/spare-parts')"` |
| Không đụng | `CurrencyInput v-model="form.unit_cost"` — `components/common/currencyInputRollout.test.ts:21` khoá |

#### 12.4.4 `views/asset/AssetTransferDetailView.vue` (342 dòng) — **panel thao tác đang ở NGOÀI mọi trạng thái**

| Việc | Chi tiết |
|---|---|
| Sửa | `loading = ref(false)` `:16` → `ref(true)`; `load()` `:89-95` thêm `catch` chuẩn (hiện **0 catch**) và `form.value = {}` khi hỏng |
| Thêm | `loadKind` / `loadMsg` — **ref MỚI**. `err` `:18` **giữ nguyên** cho 5 hành động (`save` `:109` · `approve` `:117` · `reject` `:122,:133` · `confirmReceipt` `:145` · `cancel` `:154`) |
| Xoá | `page-container` `:161`; `v-if="loading"` `:199`; `v-else` `:201` |
| `#title` | phần **tĩnh** của khối `:163-168`: eyebrow «Phiếu Luân chuyển» + `<h1>{{ name }}</h1>` (`name` = route param, **không** deref bản ghi) |
| `#header` | dòng meta `:167` (`transferTypeLabel(form.transfer_type)` · `form.transfer_date`) + badge trạng thái `:170-172`, bọc `<template v-if="form.name">` |
| `#actions` | **toàn bộ cụm CTA `:173-194`** (`cta-approve` `:179` · `cta-reject` `:182` · `cta-cancel` `:186` · `cta-receive` `:188` · `transfer-no-actions-hint` `:192`) — **bỏ thẻ bọc** `<div class="flex flex-wrap items-center gap-3">` `:169`/`:195` (shell đã bọc). Delta quan trọng nhất của màn này |
| mặc định | banner `err` `:198` (giữ — lỗi HÀNH ĐỘNG) + `:201-325` + hộp thoại từ chối `:328-339` |
| `text-red-500` → | `text-danger-500` tại **3** chỗ: `:248` · `:281` · `:332` (dấu sao trường bắt buộc) |
| Props shell | `entity-label="phiếu luân chuyển"` · `:record-id="name"` · `back-label="Về danh sách phiếu luân chuyển"` · `@retry="load()"` · `@back="router.push('/asset-transfers')"` |
| Không đụng | 4 computed server-driven `:35-46` (`can_edit` / `can_approve` / `can_receive` / `can_cancel`) — GATE-8, 3 test cũ khoá |

#### 12.4.5 `views/document/FirmwareCrDetailView.vue` (318 dòng)

| Việc | Chi tiết |
|---|---|
| Sửa | `loading = ref(false)` `:18` → `ref(true)`; `load()` `:21-27`: thay `err.value = …` bằng cặp `loadKind`/`loadMsg` chuẩn + `fcr.value = null` |
| Xoá | `err` `:19` (**duy nhất** phục vụ nạp — biến thể D); `page-container` `:118`; `v-if="loading"` `:135`; `v-else-if="err"` `:136`; `v-else-if="fcr"` `:138` |
| `#title` | `<PageHeader>` `:119-133` **đủ điều kiện null-safe** (`fcr ? … : props.id` `:120-121`, breadcrumb dùng `props.id` `:128`, `#actions` chỉ có `StatusBadge v-if="fcr?.status"` `:131`) ⇒ giữ ở `#title`; header hiện ở **mọi** trạng thái như hôm nay |
| `#actions` | nội dung của `:233-274` — **bỏ thẻ bọc** `<div class="flex … justify-end gap-3">` `:233`/`:274` (shell đã bọc), giữ nguyên **cả 5** phần tử con: nút «Quay lại» `:234-239` · `cta-rollback` `:240` · `cta-approve` `:249` · `cta-deploy` `:258` · `no-actions-hint` `:267` |
| ⚠️ Quyết định | **GIỮ** nút «Quay lại» trong `#actions` — nó là điều hướng ở trạng thái `content`, không phải lối thoát khẩn (lối thoát khẩn do `DetailLoadError` lo). Xoá nó = delta hành vi ngoài phạm vi lô. **Không** nhân bản nó sang `#title` |
| mặc định | `:140-229` (thẻ bước · thông tin · ghi chú) + `<BaseModal>` rollback `:278-316`, bọc `<template v-if="fcr">` |
| `text-red-500` → | `text-danger-500` tại `:286` |
| Props shell | `entity-label="yêu cầu thay đổi firmware"` · `:record-id="props.id"` · `back-label="Về danh sách yêu cầu thay đổi firmware"` · `@retry="load()"` · `@back="router.push('/cm/firmware')"` |

#### 12.4.6 `views/compliance/FindingDetailView.vue` (364 dòng)

| Việc | Chi tiết |
|---|---|
| Sửa | `loading = ref(false)` `:26` → `ref(true)`; `load()` `:28-36`: **xoá `console.error(e)` `:33`**, thay bằng `catch` chuẩn + `finding.value = null` |
| Xoá | `page-container` `:148`; `v-if="loading"` `:149` (khung xương do shell lo — mặc định `variant="form"` `rows=6` **trùng khít** hành vi cũ); `v-else-if="finding"` `:151`; import `SkeletonLoader` `:16` nếu không còn dùng |
| `#header` | `<PageHeader>` `:152-170` **bỏ `#actions`** + thẻ tóm tắt `:173-243`, bọc `<template v-if="finding">` |
| `#actions` | 6 CTA `:162-169` (`cta-start-review` · `cta-confirm` · `cta-mark-false` · `cta-waive` · `cta-create-capa` · `cta-link-capa`) — nguyên `data-testid`, nguyên điều kiện gate |
| mặc định | `<RecordHistory>` `:246` + **cả 6** `<BaseModal>` `:250-364` |
| Props shell | `entity-label="phát hiện tuân thủ"` · `:record-id="props.id"` · `back-label="Về danh sách phát hiện"` · `@retry="load()"` · `@back="router.push('/compliance/findings')"` |
| Không đụng | 6 computed gate `:52-58` (server-driven `allowed_transitions` + `can_create_capa`) — `findingDetailCtaGating.test.ts` khoá 9 case |

#### 12.4.7 `views/purchase/SupplierDetailView.vue` (235 dòng)

| Việc | Chi tiết |
|---|---|
| Giữ | `loading = ref(true)` `:17` — **đã đúng**, không sửa |
| Thêm | `loadKind` / `loadMsg` — **ref MỚI**. `error` `:18` giữ lại nhưng CHỈ còn phục vụ `remove()` `:63` (xoá dòng gán trong `catch` của `load()` `:47`) |
| Sửa | `load()` `:36-52`: `catch` chuẩn + `supplier.value = null` |
| Xoá | `page-container` `:88`; `v-if="loading"` `:113`; `v-else-if="!supplier"` `:114` (**nhánh 404 tự chế** — shell thay bằng `DetailLoadError kind="notfound"`); `v-else` `:116` |
| `#title` | `<PageHeader>` `:89-110` null-safe (`supplier?.supplier_name` kèm chuỗi dự phòng `:91`, breadcrumb fallback `name` `:96`) ⇒ giữ ở `#title`, **nhưng bỏ `<template #actions>` `:98-109`** |
| `#actions` | 2 nút Sửa · Xóa `:99-108` — bỏ `v-if="supplier"` (shell đã bảo đảm chỉ render ở `content`) |
| mặc định | banner `error` `:112` (giữ — nay chỉ là lỗi xoá) + `:118-232` |
| Props shell | `entity-label="nhà cung cấp"` · `:record-id="name"` · `back-label="Về danh sách nhà cung cấp"` · `@retry="load()"` · `@back="router.push('/suppliers')"` |
| Không đụng | `expiryClass()` `:76-83` (`text-red-700` / `text-red-600` = cảnh báo hạn giấy phép, khác nghiệp vụ) |

#### 12.4.8 `views/procurement/DecisionDetailView.vue` (399 dòng) — **nặng nhất: template-first + store**

| Việc | Chi tiết |
|---|---|
| Thêm | `load()` cục bộ bọc `store.fetchDecision` — hiện `onMounted` `:348-351` **await trần**, mà `fetchDecision` (`stores/imm03.ts:105`) **`throw e` lại** ⇒ unhandled rejection |
| Khuôn | `async function load() { loadKind.value=''; loadMsg.value=''; try { await store.fetchDecision(id); await loadEvalCandidates() } catch (e) { loadKind.value = loadErrorKind(e); loadMsg.value = toApiError(e).message; store.currentDecision = null } }` — gán `store.currentDecision = null` là **ghi state qua ref Pinia expose**, KHÔNG sửa file `stores/` |
| Loading | dùng thẳng `:loading="store.loading"` (store set/hạ đúng `:103-106`) |
| Xoá | `<div class="decision-detail" v-if="store.currentDecision">` `:2`; `v-else-if="store.loading"` `:179`; `v-else` «Không có dữ liệu» `:180`; CSS rule `.decision-detail { padding: 1.5rem; }` `:355` (shell mang `page-container`) |
| `#title` | `<div class="page-header">` `:3-12` **rút gọn**: `<h1>{{ props.id }}</h1>` + nút «← Quay lại». Dòng `.meta` `:6-9` (deref `spec_ref` / `evaluation_ref`) **dời xuống `#header`** |
| `#header` | `.meta` `:6-9` + `.stepper` `:14-18`, bọc `<template v-if="store.currentDecision">` |
| `#actions` | `.action-bar` `:170-176` — **bỏ thẻ `<div class="action-bar">`**, giữ vòng `v-for` + mọi `data-testid="workflow-action"` / `:data-action`. **KHÔNG** dời 2 form `cta-award` `:83` / `cta-record-contract` `:142` (là biểu mẫu, không phải nút — ở slot mặc định) |
| mặc định | banner `store.error` `:20-23` (giữ — nay chỉ còn lỗi transition/award) + `.grid-2col` `:25-80` + `cta-award` `:83-139` + `cta-record-contract` `:142-167` |
| Props shell | `entity-label="quyết định mua sắm"` · `:record-id="props.id"` · `back-label="Về danh sách quyết định mua sắm"` · `@retry="load()"` |
| ⚠️ Router | view hiện **không** `import { useRouter }`; `decisionAvlEligibilityBadge.test.ts:87` chỉ cấp `mocks: { $router }`. ⇒ `@back` viết **trong template**: `@back="$router.back()"`. **KHÔNG** thêm `useRouter()` — thêm sẽ làm test đó đỏ (`useRouter()` trả `undefined` khi router không được cài) |
| Không đụng | `CurrencyInput v-model="awardForm.awarded_price"` (`currencyInputRollout.test.ts:28`); computed `workflowActions` `:268` (GATE-8 — `DecisionDetailView.ctaGating.test.ts` khoá 7 case, trong đó 1 case đọc `?raw` source) |

### 12.5 Bất biến lô 1 (namespace MỚI `INV-UX4L1-*` — KHÔNG tái dùng `INV-UX4-*`)

| Mã | Bất biến | Đo bằng |
|---|---|---|
| **INV-UX4L1-1** | Sổ §12.2 có **đúng 8** dòng, đánh số 1…8, tập route **trùng khít** 8 route đã chốt | `uiDetailShellLot1Parity.test.ts` |
| **INV-UX4L1-2** | Mã TC là `TC-UX4-24 … TC-UX4-31` (nối tiếp max 23 trên đĩa, không tái dùng ≤ 23, không trùng); §12.6 khai đủ 8 file đặt tên `*DetailStates.test.ts`, khớp mã TC của sổ | như trên |
| **INV-UX4L1-3** | Mọi route trong sổ là route **THẬT** (`router/index.ts`); view file **tồn tại trên đĩa** và **trùng khít** ô view file tương ứng ở `00 §3.1` | như trên |
| **INV-UX4L1-4** | **Parity 2 CHIỀU**: view có `import DetailPageShell` ⟺ ô «Trạng thái» của route đó = `ĐÃ ĐÓNG`. Kèm 1 chiều: `ĐÃ ĐÓNG` ⇒ ô *Lỗi+Thử lại* của route đó ở `00 §3.1` = ✅, và ⇒ file test trạng thái **tồn tại trên đĩa** | như trên |
| **INV-UX4L1-5** | Token `[NO-DET=N]` của `AC-UX-048` (`00 §6`) == `20 − số route lô 1 ĐÃ ĐÓNG`, **và** == số `*DetailView.vue` trên đĩa không có bất kỳ lối nạp lại nào (đo lại từ đĩa, không tin doc) | như trên |
| **INV-UX4L1-6** | Trong mọi view `ĐÃ ĐÓNG`: `DetailPageShell` ≥ 1 · `text-red-500` == 0 · `page-container` == 0 · **0** nhánh `v-if`/`v-else-if` chứa từ khoá `loading` · `<DetailPageShell` là **thẻ gốc duy nhất** của khối `<template>` | như trên |

> **Vì sao INV-UX4L1-6 không bắt «định danh trần»** (`v-else-if="doc"` / `v-else-if="!supplier"`): hai biểu thức
> hợp lệ đang tồn tại có cùng hình dạng — `v-else-if="showReadOnlyHint"` (`AssetTransferDetailView.vue:295`) và
> `v-else-if="doc.reference_name"` (`StockMovementDetailView.vue:160`). Guard bắt định danh trần sẽ **ĐỎ oan**
> và ép FE viết vòng vo. Nhánh `!<record>` bị chặn **gián tiếp nhưng chắc hơn** bằng phép «shell là thẻ gốc duy
> nhất»: khi shell là gốc, view **không còn chỗ** đặt một chuỗi trạng thái song song.

> Lỗi HÀNH ĐỘNG không được nối vào `:error-kind` — bất biến này **không** đo được bằng grep (`err` hợp lệ ở
> banner riêng). Chấm bằng **đọc mã** ở review + sub-case (e) của §12.6 (bản ghi hợp lệ ⇒ `detail-content` còn,
> nghĩa là lỗi hành động không thay cả màn).

### 12.6 Bộ test — 8 file trạng thái (mỗi file **≥ 5 case**, mount THẬT)

| TC | file |
|---|---|
| `TC-UX4-24` | `frontend/src/views/inventory/stockMovementDetailStates.test.ts` |
| `TC-UX4-25` | `frontend/src/views/inventory/warehouseDetailStates.test.ts` |
| `TC-UX4-26` | `frontend/src/views/inventory/sparePartDetailStates.test.ts` |
| `TC-UX4-27` | `frontend/src/views/asset/assetTransferDetailStates.test.ts` |
| `TC-UX4-28` | `frontend/src/views/document/firmwareCrDetailStates.test.ts` |
| `TC-UX4-29` | `frontend/src/views/compliance/findingDetailStates.test.ts` |
| `TC-UX4-30` | `frontend/src/views/purchase/supplierDetailStates.test.ts` |
| `TC-UX4-31` | `frontend/src/views/procurement/decisionDetailStates.test.ts` |

**Sub-case bắt buộc** (5 × 8 = **≥ 40 case**):

| Sub-case | Nội dung | Neo acceptance |
|---|---|---|
| **a — 404** | hàm nạp reject `new ApiError('…', ErrorCode.NOT_FOUND, 404)` ⇒ `[data-testid="detail-load-error"][data-kind="notfound"]` có mặt · **0** `detail-content` · **0** `detail-actions` · **0** nút mang nhãn nạp lại | (e) (f) |
| **b — 403 in-envelope** | reject `new ApiError('Bạn không có quyền xem…', ErrorCode.FORBIDDEN, 403)` ⇒ `[data-kind="forbidden"]` · **0** nút nạp lại · **có** nút quay lại · `router.push` **KHÔNG** được gọi với `/login` · message THẬT của server hiện nguyên văn | (e) (f) |
| **c — mạng/500 + nạp lại** | reject `new Error('Network Error')` ⇒ `[data-kind="unknown"]` · **có** nút nạp lại · click ⇒ hàm nạp được gọi **lần thứ 2** (`toHaveBeenCalledTimes(2)`) | (f) |
| **d — xoá lỗi đầu lượt** | nối tiếp case c: lần gọi thứ 2 **resolve** bản ghi hợp lệ ⇒ `detail-load-error` **biến mất**, `detail-content` **xuất hiện**, `detail-actions` **xuất hiện** | (g) |
| **e — content** | resolve bản ghi hợp lệ ngay từ đầu ⇒ `detail-content` + `detail-actions` có mặt; **≥ 1** `data-testid` CTA cũ của màn đó tìm thấy được | (e) |

**Ràng buộc viết test (bẫy §7.5 — bắt buộc):**
- **KHÔNG** stub `DetailPageShell`, `DetailLoadError`, `SkeletonLoader` — mount THẬT. Stub `DetailPageShell` làm
  mọi assert về `detail-actions` / `detail-content` **xanh giả**.
- Stub được phép: `PageHeader` (**phải render `<slot />` + `<slot name="actions" />`** nếu màn đó còn CTA trong
  `PageHeader`; khuôn ở `findingDetailCtaGating.test.ts:46-52`), `BaseModal`, `StatusBadge`, `RecordHistory`,
  `SmartSelect`, `ApproverSelect`, `CurrencyInput`, `DateInput`, `FileUploadField`, `UomConverter`, `RouterLink`.
- `vi.mock('vue-router')` trả `useRoute` + `useRouter` (khuôn `@/test/vueRouterMock`, đang dùng ở
  `firmwareCrCtaGate.test.ts:15`). **Riêng màn 8** dùng `mocks: { $router }` — **không** mock `useRouter`.
- Màn 6 và 8 cần `setActivePinia(createPinia())`.
- Assert «0 panel thao tác» phải dùng **2 lớp**: `[data-testid="detail-actions"]` **và** ≥ 1 testid CTA cụ thể
  của màn (testid panel có thể đổi; testid CTA bị test cũ khoá nên ổn định hơn).

### 12.7 Bẫy đã biết — ĐỌC TRƯỚC KHI CODE (bổ sung cho §7)

**7.12 — 10 file test cũ bám 6/8 màn, mount THẬT ⇒ trở thành test tích hợp của khuôn.**
`assetTransferDetailCtaGate` · `assetTransferDetailEditGate` · `assetTransferDetailNames` · `firmwareCrCtaGate` ·
`findingDetailCtaGating` · `DecisionDetailView.ctaGating` · `decisionAvlEligibilityBadge` ·
`modalOverlayHygiene` · `currencyInputRollout` · `createButtonAffordance`. Hệ quả: **mọi CTA phải nằm trong
`content`**, nếu không chúng đỏ ngay. Chạy 10 file này **trước** khi khai báo xong.

**7.13 — `data-testid` bị khoá, CẤM đổi tên:**
`cta-approve` · `cta-reject` · `cta-cancel` · `cta-receive` · `transfer-no-actions-hint` · `transfer-save` ·
`transfer-readonly-hint` · `field-reason` · `field-notes` · `asset-name` · `from-*-name` / `to-*-name` ·
`cta-rollback` · `cta-deploy` · `rollback-submit` · `no-actions-hint` · `cta-start-review` · `cta-confirm` ·
`cta-mark-false` · `cta-waive` · `cta-create-capa` · `cta-link-capa` · `workflow-action` (+ `data-action`) ·
`cta-award` · `cta-record-contract`.

**7.14 — `DecisionDetailView.ctaGating.test.ts:147` đọc `?raw` source.**
Case (g) grep chính văn bản file: cấm `workflow_state ===` và cấm `TRANSITIONS_BY_STATE`. Chèn shell **không**
được vô tình thêm 2 chuỗi đó, **kể cả trong comment**.

**7.15 — `store.currentDecision` là state DÙNG CHUNG, không reset khi đổi route.**
Mở quyết định A thành công rồi mở B lỗi ⇒ `currentDecision` vẫn là A. `errorKind` thắng `doc` nên màn **hiển thị
đúng**, nhưng vẫn bắt buộc gán `store.currentDecision = null` trong `catch` để lần điều hướng kế tiếp không nháy
dữ liệu cũ (INV-UX4-7).

**7.16 — `Promise.all` 2 nguồn (màn 3 và màn 7).**
`getSparePart` + `getPartPurchases` (và `getSupplier` + `listPurchases`) chạy song song ⇒ nguồn **phụ** hỏng cũng
đẩy cả lượt vào nhánh lỗi. Đây là **chấp nhận có chủ đích** ở lô 1 (đơn giản, không nuốt lỗi); tách nguồn phụ ra
lượt nạp riêng là việc của `AC-UX-053`, **không** làm ở lô này.

**7.17 — Dấu sao bắt buộc ≠ thông báo lỗi.**
`text-red-500` bị chấm 0 vì nó là **màu thô**, không phải vì dấu sao sai. Thay bằng `text-danger-500` (token ngữ
nghĩa). Đừng xoá `<span>*</span>` — mất tín hiệu trường bắt buộc là lỗi a11y mới.

**7.18 — Khung xương mặc định đã đúng cho cả 8 màn.**
Shell mặc định `variant="form"` `rows=6` — trùng khít khung xương đang có ở màn 6 (`:149`). 7 màn còn lại hôm nay
chỉ có dòng chữ «Đang tải…» ⇒ nhận khung xương là **nâng cấp**, không cần khai prop.

**7.19 — Hai phép đếm delta KHÁC NHAU, đừng gộp.**
`grep -L DetailPageShell` (29 → 21) là *chưa dùng khuôn*; *0 lối nạp lại* (20 → 12) là mốc của token
`[NO-DET=N]`. Guard chấm phép thứ hai; acceptance (b) chấm phép thứ nhất.

**7.20 — `cellsOf()` của guard split thô trên ký tự `|`.**
Trong §12.2 và §12.6 **không** dùng `|` dưới mọi hình thức bên trong ô (kể cả escape `\|`) — một ô lẻ có `|` sẽ
làm dòng bị bỏ qua và guard báo «sổ không đủ 8 dòng» mà không nói lý do thật. Dùng `·` để liệt kê.

### 12.8 Lệnh chấm (QA **tự đo lại**, không nhận báo cáo suông)

```bash
cd frontend

# (b) adoption đo được: 29 -> 21
grep -L DetailPageShell $(find src/views -name '*DetailView.vue') | wc -l      # == 21

# (c) xoá ngõ cụt tự chế
for f in src/views/inventory/StockMovementDetailView.vue \
         src/views/inventory/WarehouseDetailView.vue \
         src/views/inventory/SparePartDetailView.vue \
         src/views/asset/AssetTransferDetailView.vue \
         src/views/document/FirmwareCrDetailView.vue \
         src/views/compliance/FindingDetailView.vue \
         src/views/purchase/SupplierDetailView.vue \
         src/views/procurement/DecisionDetailView.vue; do
  echo "$f shell=$(grep -c DetailPageShell $f) red500=$(grep -cE 'text-red-500' $f) pc=$(grep -c page-container $f)"
done            # shell>=1 · red500==0 · pc==0

# (d) lỗi không giả dạng thành công
grep -n 'Lỗi tải kho' src/views/inventory/WarehouseDetailView.vue              # 0 kết quả

# (e)(f)(g)(h)(i) test trạng thái + guard parity
npx vitest run src/views/inventory/stockMovementDetailStates.test.ts \
  src/views/inventory/warehouseDetailStates.test.ts \
  src/views/inventory/sparePartDetailStates.test.ts \
  src/views/asset/assetTransferDetailStates.test.ts \
  src/views/document/firmwareCrDetailStates.test.ts \
  src/views/compliance/findingDetailStates.test.ts \
  src/views/purchase/supplierDetailStates.test.ts \
  src/views/procurement/decisionDetailStates.test.ts \
  src/router/uiDetailShellLot1Parity.test.ts        # 9 file XANH, >= 40 case

# (j) chống thoái lui — 10 file test cũ bám 6/8 màn + 7 guard/khuôn vòng trước
npx vitest run src/views/asset/assetTransferDetailCtaGate.test.ts \
  src/views/asset/assetTransferDetailEditGate.test.ts \
  src/views/asset/assetTransferDetailNames.test.ts \
  src/views/document/firmwareCrCtaGate.test.ts \
  src/views/compliance/findingDetailCtaGating.test.ts \
  src/views/procurement/DecisionDetailView.ctaGating.test.ts \
  src/views/procurement/decisionAvlEligibilityBadge.test.ts \
  src/components/common/modalOverlayHygiene.test.ts \
  src/components/common/currencyInputRollout.test.ts \
  src/router/createButtonAffordance.test.ts
npx vitest run src/router/uiAuditDocParity.test.ts src/router/uiFixPlanParity.test.ts \
  src/router/uiListShellLot1Parity.test.ts src/components/common/DetailPageShell.test.ts \
  src/views/incident/capaDetailStates.test.ts \
  src/views/compliance/internalAuditDetailStates.test.ts \
  src/views/compliance/managementReviewDetailStates.test.ts

find src -name '*.test.ts' -o -name '*.spec.ts' | wc -l   # 327 -> 336 (+9)
npx vitest run                                            # 0 file ĐỎ
npm run typecheck                                         # XANH

# (l) hàng rào phạm vi — ĐO TRÊN THAY ĐỔI CỦA VÒNG NÀY, không trên toàn working tree
cd .. && git status --porcelain -- '*.py' | wc -l                                     # 0
git diff --name-only -- frontend/src/api frontend/src/stores frontend/src/components/ui \
  frontend/src/components/common/DetailPageShell.vue | wc -l                          # 0

# (m) đánh số
grep -rhoE "AC-UX-[0-9]{3}" docs/ frontend/src/ | sort -u | tail -1                   # AC-UX-058
```

> ⚠️ **Bẫy chấm hàng rào phạm vi (l) — đọc trước khi kết luận «vi phạm».** Working tree hiện có **21 đường dẫn
> untracked của run-5 CHƯA COMMIT**, trong đó có đúng 2 thứ nằm trong danh sách cấm:
> `frontend/src/components/common/DetailPageShell.vue` và `frontend/src/components/ui/`. `git status --porcelain`
> **luôn** liệt kê chúng (`??`) cho tới khi user commit ⇒ chấm bằng `git status` sẽ **ĐỎ OAN**. Phép chấm đúng là
> `git diff --name-only` (thay đổi trên file đã theo dõi) + đối chiếu danh sách untracked với ảnh chụp **đầu
> vòng**. File `.py` thì `git status` vẫn đúng vì run-5 có **0** file `.py`.

**Truy vết acceptance ⇄ spec ⇄ guard:**

| AC | Spec | Chấm bằng |
|---|---|---|
| (a) phạm vi đóng băng 8 route | §12.2 (8 route hardcode trong guard) | INV-UX4L1-1 |
| (b) adoption đo được 29 → 21 | §12.1, §12.8 | lệnh `grep -L` |
| (c) xoá ngõ cụt tự chế | §12.4.1–8 | INV-UX4L1-6 |
| (d) lỗi ≠ thành công | §12.4.2 | `grep -n 'Lỗi tải kho'` + TC-UX4-25 |
| (e) panel thao tác tắt ngoài content | §12.3 Always · §12.4 cột `#actions` | sub-case a/b/c/e |
| (f) kind-aware 3 nhánh | §12.4.0 · §12.6 | sub-case a/b/c |
| (g) xoá lỗi đầu lượt | §12.4.0 (dòng đầu `load()`) | sub-case d |
| (h) 8 test + 1 guard · TC từ 24 · INV namespace mới | §12.5, §12.6 | INV-UX4L1-1/2 |
| (i) guard doc⇄đĩa 2 chiều | §12.2, §12.5 | INV-UX4L1-1…5 |
| (j) không thoái lui | §12.7 (7.12–7.14), §12.8 | suite đầy đủ + `typecheck` |
| (k) bằng chứng render thật | §12.9 | Playwright |
| (l) hàng rào phạm vi | §12.3 Never | `git status` |
| (m) đánh số | §12.1 | `grep` sổ |

### 12.9 Bằng chứng render thật (acceptance k)

Tối thiểu **2/8** route, mỗi route **2 ảnh** lưu `.playwright/eval/`:

| Route | Ảnh 1 — `content` | Ảnh 2 — trạng thái lỗi |
|---|---|---|
| `/warehouses/:name` | mở kho có thật ⇒ thấy `detail-actions` + lưới KPI | mở `/warehouses/KHO-KHONG-TON-TAI` ⇒ thông báo VI + nút quay lại + **KHÔNG** `detail-actions`, **KHÔNG** dải xanh |
| `/suppliers/:id` | mở NCC có thật ⇒ 2 nút Sửa/Xóa nằm trong `detail-actions` | mở `/suppliers/NCC-KHONG-TON-TAI` ⇒ «Không tìm thấy nhà cung cấp: …» + nút «Về danh sách nhà cung cấp», **0** nút Sửa/Xóa |

Tên ảnh: `.playwright/eval/uidetail-lot1-<route>-<content|error>.png`. Dọn rác sau khi xong bằng
`bash .claude/scripts/tidy-eval-artifacts.sh` (CLAUDE.md §21).

### 12.10 Quyết định kiến trúc

Xem **ADR-UX-12** ở [`00_AUDIT_HIEN_TRANG.md` §9](./00_AUDIT_HIEN_TRANG.md) — SSoT của mọi ADR lớp UI/UX.

---

## §13. LÔ 2 adoption `DetailPageShell` — **21 màn CHI TIẾT CUỐI CÙNG** (`AC-UX-048` + `AC-UX-053`, đo 2026-08-04)

| Mục | Giá trị |
|---|---|
| Đề mục | `AC-UX-048` **lô 2 (ĐÓNG HẲN)** + `AC-UX-053` (lan SSoT `useDetailAccess`) |
| Sổ số hiệu MỚI | **`AC-UX-071`** (guard adoption) · **`AC-UX-072`** (guard SSoT lỗi) · **`AC-UX-073`** (quyết định chống 2 thanh tab) — max trên đĩa trước vòng này = **070**, đã `grep` xác nhận |
| Phạm vi | **đúng 21** màn `*DetailView.vue` còn lại — danh sách chốt ở §13.2. Sau lô này adoption = **32/32**, non-adopter = **0** vĩnh viễn |
| Loại | Core Doc cross-cutting (UI/UX) — spec thi hành cho FE dev, **spec-before-code gate** |
| Ngày đo | **2026-08-04** — mọi số dưới đây đo TỪ ĐĨA hôm nay; số trong prompt/STATE **không** được kế thừa |
| Nhánh | `feature/hieuc/core-refinement` |
| Tài liệu cha | §0–§11 (hợp đồng `DetailPageShell`) + §12 (lô 1, 8 màn — khuôn sổ-lô và guard parity mà lô này kế thừa) |
| Tài liệu anh | [`02 §14`](./02_LIST_PAGE_SHELL.md) — lô 3 lớp DANH SÁCH đã ĐÓNG HẲN 40/40 (khuôn guard CHỈ-GIẢM `listShellAdoption.test.ts` mà `AC-UX-071` sao chép) · [`07`](./07_DETAIL_TAB_BAR_SSOT.md) — SSoT thanh tab |
| Trạng thái | **Chốt để code** |

> **Vì sao lô này phải là lô CUỐI.** Lớp danh sách đã học xong bài học của nó: đóng «12 route cuối cùng» theo
> **cột bộ dò** rồi phát hiện còn 12 màn chưa áp khuôn, phải mở thêm lô 3 (`ADR-UX-23`). Lớp chi tiết không
> lặp lại: phép đo của lô 2 **không** phải cột *Lỗi+Thử lại* mà là **dấu vân tay IMPORT**
> `from '@/components/common/DetailPageShell.vue'` trên họ `*DetailView.vue` — đúng thứ ép 4 trạng thái loại
> trừ nhau bằng **CẤU TRÚC**. Hôm nay 11/32; sau lô 2 phải là **32/32** và bị **đóng băng ở 0 nợ** bằng guard
> `AC-UX-071`, cùng khuôn với `AC-UX-070` của lớp danh sách.

### 13.1 Số đo TỪ ĐĨA hôm nay (baseline chấm DELTA) — kèm **3 đính chính BA** so với prompt

| Đại lượng | Lệnh (chạy tại `frontend/`) | **Đĩa 2026-08-04** | Prompt | Kết luận |
|---|---|---|---|---|
| `*DetailView.vue` tổng | `find src/views -name '*DetailView.vue' \| wc -l` | **32** | 32 | khớp |
| Đã import `DetailPageShell` | `grep -rl "from '@/components/common/DetailPageShell.vue'" --include='*DetailView.vue' src/views \| wc -l` | **11** | 11 | khớp — nợ đúng **21** |
| Dùng `useDetailAccess` | `grep -rl useDetailAccess --include='*DetailView.vue' src/views \| wc -l` | **3** (`cm` · `incident` · `pm`) | 3 | khớp |
| Đích của `useDetailAccess` sau lô 2 | như trên | **21** | ~~24~~ | ⚠️ **ĐÍNH CHÍNH 1** — xem dưới |
| Màn chi tiết **0 lối nạp lại** (token `NO-DET` ở `00 §6`) | vòng lặp `grep -qE 'DetailLoadError\|@retry\|DetailPageShell'` | **12** | — | sau lô 2 phải là **0** |
| Màn có thanh tab **import trực tiếp** `DetailTabBar` | `grep -rl DetailTabBar --include='*DetailView.vue' src/views` | **8** (7 trực tiếp + `InternalAudit` gián tiếp) | 7 | khớp — 7 nằm trong 21, `InternalAudit` đã là adopter |
| Ô ❌ cột *Lỗi+Thử lại* (bộ dò LIVE) | `node scripts/ui-audit-inventory.mjs --summary` | **57** | — | 7/21 route của lô đang ❌ ⇒ xem **ĐÍNH CHÍNH 2** |
| File test FE | `find src -name '*.test.ts' -o -name '*.spec.ts' \| wc -l` | **377** | 377 (340 là STALE) | khớp — cuối vòng phải **400** (+21 trạng thái +2 guard) |
| Suite FE **sau bước BA** | `npx vitest run` (đo 16:59) | **377 file / 3731 test — 0 ĐỎ** | ~~3352~~ STALE | mốc chấm delta của FE; cuối vòng **400 file**, vẫn 0 đỏ |
| `TC-UX4-*` lớn nhất | `grep -rhoE 'TC-UX4-[0-9]+' docs frontend/src` | **TC-UX4-31** | — | lô 2 dùng **32…52** |
| `ADR-UX-*` lớn nhất | grep | **ADR-UX-24** | — | lô 2 dùng **25, 26, 27** |
| Sổ `AC-UX` lớn nhất / tổng | `grep -rhoE 'AC-UX-[0-9]{3}' docs frontend/src \| sort -u` | **070 / 70 mục** | 070 | khớp — cấp **071/072/073**, tổng thành **73** |
| `INV-UX4L*` | grep | `INV-UX4L1-1…6` | — | lô 2 dùng namespace MỚI **`INV-UX4L2-1…8`** |

**⚠️ ĐÍNH CHÍNH 1 (BA Self-Correction) — «`useDetailAccess` 3 → 24» là số KHÔNG đo được.**
Acceptance A2 ghi đích **24**. Phép cộng đó giả định 3 màn đang dùng composable nằm NGOÀI 21 màn của lô —
sai: `cm/CMWorkOrderDetailView` · `incident/IncidentDetailView` · `pm/PMWorkOrderDetailView` **chính là**
3 trong 21 màn chưa áp khuôn (chúng có `useDetailAccess` nhưng chưa có shell). 11 màn đã áp khuôn thì A2
lại **đóng băng** ở `loadErrorKind` cục bộ (`LEGACY_LOCAL_KIND_BUDGET`, cấm thêm dòng). Vậy trần đo được
của vòng này là **21/32**, delta **+18** — không phải 24. Đích **24** chỉ đạt được nếu di trú thêm 3 màn
legacy, việc mà chính A2 cấm. **Chốt: 3 → 21.** Lệnh nghiệm thu ghi ở §13.10 (c).

**⚠️ ĐÍNH CHÍNH 2 — cột *Lỗi+Thử lại* của `00 §3.1` KHÔNG được lật ở bước BA.**
`uiListShellLot1Parity.test.ts` (INV-UX3L-6, `ADR-UX-22`) ép **parity từng ô trên cả 148 dòng** giữa `00 §3.1`
và **bộ dò đo LIVE**. Trong 21 route của lô, hôm nay có **7 ô ❌**: `/rca/:id` (#68) · `/service-contracts/:id`
(#89) · `/purchases/:name` (#111) · `/procurement-plans/:id` (#126) · `/tech-specs/:id` (#129) ·
`/vendor-evaluations/:id` (#131) · `/vendor-profiles/:id` (#136). 14 ô còn lại đang ✅ — trong đó **5 ô ✅ sai
lý do** (`/assets/:id` · `/commissioning/:id` · `/documents/view/:name` · `/needs-requests/:id` ·
`/imm06/competencies/:name` nằm trong nhóm **0 lối nạp lại**; đúng loại drift bảng-tay mà `ADR-UX-12` đã ghi).
BA **giữ nguyên** cả 21 ô. **FE lật 7 ô ❌ → ✅ và cập nhật token `NO-CON` bằng số bộ dò in ra, trong CÙNG lượt
với mã** (§13.8 mục 3). Sau lô 2, 5 ô ✅-sai-lý-do trở thành ✅ **đúng lý do** mà không ai phải chấm tay lại.

**⚠️ ĐÍNH CHÍNH 3 — token `NO-DET` sẽ về 0, và công thức của guard lô 1 PHẢI được nới trong cùng lượt.**
`uiDetailShellLot1Parity.test.ts` (INV-UX4L1-5) ép **hai** đẳng thức cùng lúc: `N == 20 − số route lô 1 ĐÃ ĐÓNG`
(= 12, đã đông cứng vì lô 1 đóng hết) **và** `N == số màn 0-lối-nạp-lại đo lại từ đĩa`. Lô 2 kéo vế thứ hai về
**0** ⇒ **guard ĐỎ** nếu không sửa. Đây là bẫy chắc chắn nổ, không phải rủi ro giả định — cách sửa duy nhất
được phép ghi ở §13.8 mục 2 (**ADR-UX-26**).

### 13.2 Sổ lô 2 — 21 route (SSoT; guard `detailShellAdoption.test.ts` đọc CHÍNH bảng này)

| # | Route | View file | Hàm nạp | Nguồn lỗi sau sửa | Nhóm | Trạng thái | TC |
|---|---|---|---|---|---|---|---|
| 1 | `/assets/:id` | `frontend/src/views/asset/AssetDetailView.vue` | `store.fetchOne` `:174`, `:320` (Pinia `imm05`) | ref MỚI `loadError` trong view + `useDetailAccess` — store chỉ giữ chuỗi | N4+TAB | **ĐÃ ĐÓNG** | `TC-UX4-32` |
| 2 | `/calibration/:id` | `frontend/src/views/calibration/CalibrationDetailView.vue` | `load()` `:326` | ĐÃ có `loadFailed` `:50` + `loadErrMsg` `:51` → thay bằng `useDetailAccess` | N1+TAB | **ĐÃ ĐÓNG** | `TC-UX4-33` |
| 3 | `/cm/work-orders/:id` | `frontend/src/views/cm/CMWorkOrderDetailView.vue` | `store.fetchWorkOrder` `:54` | **giữ nguyên** `useDetailAccess` `:91` — chỉ chuyển sang prop shell | N2+TAB | **ĐÃ ĐÓNG** | `TC-UX4-34` |
| 4 | `/commissioning/:id` | `frontend/src/views/commissioning/CommissioningDetailView.vue` | `load()` `:181` | ref MỚI + `useDetailAccess`; lỗi nạp hiện đi `toast` `:28` | N4+TAB | **ĐÃ ĐÓNG** | `TC-UX4-35` |
| 5 | `/compliance/rules/:id` | `frontend/src/views/compliance/ComplianceRuleDetailView.vue` | `load()` `:38` | ĐÃ có `loadFailed` `:28` + `loadErrMsg` `:29` → `useDetailAccess` | N1 | **ĐÃ ĐÓNG** | `TC-UX4-36` |
| 6 | `/documents/view/:name` | `frontend/src/views/document/DocumentDetailView.vue` | `load()` `:71` → `loadDocument()` `:77` | `error` `:33` là CHUỖI dùng chung → ref MỚI cho lượt nạp | N3 | **ĐÃ ĐÓNG** | `TC-UX4-37` |
| 7 | `/decommissions/:id` | `frontend/src/views/eol/DecommissionDetailView.vue` | `load()` `:47` | ĐÃ có `loadFailed` `:45` (từ `api.lastError`) → `useDetailAccess` | N1 | **ĐÃ ĐÓNG** | `TC-UX4-38` |
| 8 | `/incidents/:id` | `frontend/src/views/incident/IncidentDetailView.vue` | `load()` `:163` | **giữ nguyên** `useDetailAccess` `:68` (nguồn `loadErr` `:66`) | N2+TAB | **ĐÃ ĐÓNG** | `TC-UX4-39` |
| 9 | `/rca/:id` | `frontend/src/views/incident/RCADetailView.vue` | `load()` `:151` | `err` `:26` DÙNG CHUNG với hành động → **ref MỚI** cho lượt nạp | N3 | **ĐÃ ĐÓNG** | `TC-UX4-40` |
| 10 | `/inventory/cycle-counts/:name` | `frontend/src/views/inventory/CycleCountDetailView.vue` | `load()` `:73` → `store.fetchCycleCount` | `loadFailed` `:44` là `computed` từ store → `useDetailAccess(() => …lastApiError)` | N1 | **ĐÃ ĐÓNG** | `TC-UX4-41` |
| 11 | `/needs-requests/:id` | `frontend/src/views/needs/NeedsRequestDetailView.vue` | `store.fetchOne` (`onMounted` `:345`) | ref MỚI trong view — `error` `:33` là chuỗi từ store | N4+TAB | **ĐÃ ĐÓNG** | `TC-UX4-42` |
| 12 | `/procurement-plans/:id` | `frontend/src/views/needs/ProcurementPlanDetailView.vue` | `loadPlan()` `:66` | `error` `:18` DÙNG CHUNG với 5 hành động → **ref MỚI** | N3 | **ĐÃ ĐÓNG** | `TC-UX4-43` |
| 13 | `/pm/work-orders/:id` | `frontend/src/views/pm/PMWorkOrderDetailView.vue` | `store.fetchWorkOrder` `:57` | **giữ nguyên** `useDetailAccess` `:67-71` | N2+TAB | **ĐÃ ĐÓNG** | `TC-UX4-44` |
| 14 | `/vendor-evaluations/:id` | `frontend/src/views/procurement/VendorEvalDetailView.vue` | `loadScorecard()` `:366` + `onMounted` `:537` | `catch (e: any)` `:374` — ref MỚI + bỏ `any` (dùng `unknown`) | N4 | **ĐÃ ĐÓNG** | `TC-UX4-45` |
| 15 | `/vendor-profiles/:id` | `frontend/src/views/procurement/VendorProfileDetailView.vue` | `load()` `:47` | `error` `:35` dùng chung → **ref MỚI**; **2** `page-container` phải về 0 | N3 | **ĐÃ ĐÓNG** | `TC-UX4-46` |
| 16 | `/purchases/:name` | `frontend/src/views/purchase/PurchaseDetailView.vue` | `load()` `:61` | lỗi nạp đang đi `toast` `:29` (dải chữ) → ref MỚI, **gỡ khỏi toast** | N3 | **ĐÃ ĐÓNG** | `TC-UX4-47` |
| 17 | `/service-contracts/:id` | `frontend/src/views/purchase/ServiceContractDetailView.vue` | `load()` `:29` | `error` `:16` dùng chung với 2 hành động → **ref MỚI** | N3 | **ĐÃ ĐÓNG** | `TC-UX4-48` |
| 18 | `/tech-specs/:id` | `frontend/src/views/tech-specs/TechSpecDetailView.vue` | `store.fetchOne` (`onMounted` `:362`, **0 catch**) | ref MỚI + `try/catch` trong view — **KHÔNG** sửa `stores/` | N4 | **ĐÃ ĐÓNG** | `TC-UX4-49` |
| 19 | `/imm06/competencies/:name` | `frontend/src/views/training/CompetencyDetailView.vue` | `load()` `:110` | `error` `:17` dùng chung → **ref MỚI** | N3 | **ĐÃ ĐÓNG** | `TC-UX4-50` |
| 20 | `/imm06/programs/:name` (+ `/new`) | `frontend/src/views/training/ProgramDetailView.vue` | `load()` `:90` → `store.fetchProgram` | `loadFailed` `:25` computed → `useDetailAccess`; **lưỡng dụng tạo/sửa** | N1+NEW | **ĐÃ ĐÓNG** | `TC-UX4-51` |
| 21 | `/imm06/sessions/:name` (+ `/new`) | `frontend/src/views/training/SessionDetailView.vue` | `store.fetchSession` `:74` | `loadFailed` `:34` computed → `useDetailAccess`; **lưỡng dụng tạo/sửa** | N1+NEW | **ĐÃ ĐÓNG** | `TC-UX4-52` |

**Cột «Trạng thái» là cờ tiến độ do guard đọc:** `CHƯA` (BA chốt spec) → `ĐÃ ĐÓNG` (FE land trong CÙNG lượt
với mã). Guard `AC-UX-071` ép **2 chiều**: `view import DetailPageShell` ⟺ ô = `ĐÃ ĐÓNG`.

> **Lô 2 ĐÃ LAND — đo lại từ đĩa 2026-08-04 sau bước FE:** cả **21/21** ô ở trên là `ĐÃ ĐÓNG`;
> `grep -rl "from '@/components/common/DetailPageShell.vue'" --include='*DetailView.vue' src/views | wc -l`
> = **32** (adoption ĐÓNG HẲN 32/32, non-adopter = 0) và
> `grep -rl useDetailAccess --include='*DetailView.vue' src/views | wc -l` = **21**
> (11 màn legacy còn `loadErrorKind` cục bộ vẫn đóng băng trong `LEGACY_LOCAL_KIND_BUDGET`).
> `NON_ADOPTER_BUDGET` của `views/detailShellAdoption.test.ts` nay **RỖNG** ⇒ guard chuyển sang chế độ
> đóng băng 0: một `*DetailView.vue` mới không có khuôn sẽ làm ĐỎ ngay.

**Bốn nhóm — không có nhóm thứ năm** (nhóm quyết định khối lượng, không phải module):

| Nhóm | Số màn | Đặc trưng | Delta cốt lõi |
|---|---|---|---|
| **N1** — đã có `DetailLoadError` + kind cục bộ | 6 (2, 5, 7, 10, 20, 21) | Đã phân loại lỗi đúng, chỉ thiếu khuôn | Bọc shell · **thay** kind cục bộ bằng `useDetailAccess` · xoá `<DetailLoadError>` rời (shell tự render) |
| **N2** — đã dùng `useDetailAccess` | 3 (3, 8, 13) | 3 màn workflow của CR-74 | Bọc shell · **giữ nguyên** composable · xoá `<DetailLoadError>` rời · hoisting thanh tab |
| **N3** — 0 lối nạp lại, ref lỗi dùng CHUNG với hành động | 7 (6, 9, 12, 15, 16, 17, 19) | Nối thẳng ref cũ vào shell ⇒ **1 lần bấm Xoá hỏng xoá trắng cả bản ghi đang xem** | **ref MỚI** cho lượt nạp; ref cũ giữ nhiệm vụ cũ |
| **N4** — 0 lối nạp lại, lỗi nằm trong store / 0 `catch` | 5 (1, 4, 11, 14, 18) | Store chỉ giữ **chuỗi** ⇒ không phân loại được kind; `TechSpec` không `catch` gì | View tự `try/catch` + ref MỚI; **KHÔNG** sửa `stores/` |

Bảy màn cột `TAB` (1, 2, 3, 4, 8, 11, 13) thi hành thêm **AC-UX-073 / ADR-UX-25** (§13.11). Hai màn cột `NEW`
(20, 21) thi hành thêm hợp đồng **lưỡng dụng tạo/sửa** (§13.4.3).

### 13.3 Boundaries lô 2

**Always:**
- Giữ nguyên 4 trạng thái loại trừ + thứ tự `error > loading > notfound > content` (§2). Không khai lại máy
  trạng thái trong view, không thêm nhánh thứ 5.
- `DetailPageShell` là **thẻ gốc duy nhất** của `<template>` (INV-UX4-11); xoá `page-container` cũ
  (**18/21 màn** đang có — `VendorProfile` và `ProcurementPlan` có **2**; `CM`, `VendorEval`, `TechSpec` có 0).
- **Nguồn lỗi nạp = `useDetailAccess`** cho **cả 21 màn** (AC-UX-053). Destructure có đổi tên:
  `const { kind: loadKind, message: loadMsg, blocked: loadBlocked } = useDetailAccess(() => …)`.
- Mỗi hàm nạp theo khuôn §13.4.0: xoá lỗi ở **DÒNG ĐẦU** (INV-UX4-7), `catch` gán **nguyên** lỗi vào ref
  (KHÔNG `String(e)`), dọn bản ghi về `null` khi hỏng, `finally` hạ `loading`, `const loading = ref(true)`
  (INV-UX4-8 — chống nháy 404 một nhịp).
- **Mọi CTA vòng đời** vào slot `#actions` — kể cả CTA đang nằm trong `PageHeader #actions`
  (**12/21** màn có `PageHeader`). Đây là giá trị lõi của `AC-UX-053`: `blocked === true` ⇒ **0** phần tử CTA.
- Mọi slot có deref bản ghi bọc `<template v-if="<record>">` (INV-UX4-12) — khôi phục type-narrowing cho `vue-tsc`.
- 7 màn có thanh tab: **hoisting** `:tabs` + `active-tab` lên shell (ADR-UX-25), gỡ `import DetailTabBar`.
- UI copy **100% tiếng Việt** (LL-FE-53) — kể cả `entityLabel` / `backLabel` mới.

**Ask first (dừng, hỏi BA/PM):**
- Áp shell cho bất kỳ file `.vue` **không** thuộc họ `*DetailView.vue` (ngoài phạm vi lô).
- Sửa `frontend/src/stores/**` hoặc `frontend/src/api/**` — 21 màn đã được kiểm chứng là **không cần**
  (§13.2 cột «Nguồn lỗi sau sửa»).
- Dùng slot `#kpi`: màn nào đang có dải KPI thì **giữ NGUYÊN vị trí** trong slot mặc định; dời sang `#kpi`
  = đổi lưới = rủi ro layout không cần thiết cho lô này.
- Đổi bất kỳ `data-testid` nào đang bị **97 file test cũ** khoá (danh sách ở §13.9 mục 13.9.9).

**Never:**
- **KHÔNG** đụng bất kỳ file `.py` nào (`git status --porcelain -- '*.py'` phải RỖNG cuối vòng ⇒ không sinh
  nhu cầu restart gunicorn); **KHÔNG** `bench migrate`; **KHÔNG** `git commit`/`push`.
- **KHÔNG** sửa `frontend/src/api/errors.ts` (`loadErrorKind` / `toApiError` / `DetailLoadKind` là hợp đồng
  CR-74) và **KHÔNG** sửa `composables/useDetailAccess.ts` — lô 2 chỉ **tiêu thụ**.
- **KHÔNG** sửa `DetailPageShell.vue` ngoài **đúng một** thay đổi được cấp phép ở §13.4.4 (nới KIỂU prop
  `tabs` thành `DetailTab[]`). Mọi sửa khác = Ask first.
- **KHÔNG** đưa lỗi HÀNH ĐỘNG (lưu / duyệt / xoá / chuyển trạng thái) vào `:error-kind` — 1 lần bấm hỏng sẽ
  **thay cả màn bằng banner lỗi**. Lỗi hành động giữ nguyên kênh cũ (`err` / `toast` / `notify` / inline modal).
- **KHÔNG** di trú overlay tự vẽ (`AC-UX-055/056`): **12/21** màn của lô nằm trong allowlist đóng băng của
  `modalOverlayHygiene.test.ts` (`AssetDetailView` ở `ALLOWLIST_HYBRID`; `Calibration` · `CM` · `Commissioning` ·
  `Document` · `Incident` · `PM` · `Purchase` · `Competency` · `Session` ở `ALLOWLIST_SELF_DRAWN`). Thêm overlay
  mới ⇒ ĐỎ; bỏ overlay cũ ⇒ ngoài phạm vi lô (và phải hạ sổ cùng lượt).
- **KHÔNG** đổi `loadErrorKind` cục bộ của **11 màn legacy** sang `useDetailAccess` ở vòng này — đó là
  `LEGACY_LOCAL_KIND_BUDGET` của `AC-UX-072`, chỉ được xoá dòng khi có vòng riêng.
- **KHÔNG** thêm `console.error` mới; **KHÔNG** để `catch {}` rỗng.

### 13.4 Delta bắt buộc

#### 13.4.0 Khuôn chung `<script setup>` — áp cho cả 21 màn

```ts
import DetailPageShell from '@/components/common/DetailPageShell.vue'
import { useDetailAccess } from '@/composables/useDetailAccess'

// Lỗi của LƯỢT NẠP — ref RIÊNG, KHÔNG dùng chung với lỗi hành động (nhóm N3).
// Giữ NGUYÊN đối tượng lỗi (không String(e)) để `loadErrorKind` phân loại được.
const loadError = ref<unknown>(null)
const loading = ref(true)                       // INV-UX4-8 — chống nháy 404 một nhịp

// SSoT phân loại lỗi nạp (AC-UX-053). Destructure ĐỔI TÊN ⇒ template dùng trực tiếp,
// KHÔNG phải `access.kind.value` (bẫy 13.9.1).
const { kind: loadKind, message: loadMsg, blocked: loadBlocked } = useDetailAccess(() => loadError.value)

async function load(): Promise<void> {
  loadError.value = null                        // INV-UX4-7 — xoá lỗi ở DÒNG ĐẦU
  loading.value = true
  try {
    doc.value = await getX(id.value)
  } catch (e: unknown) {
    loadError.value = e                         // nguyên đối tượng
    doc.value = null                            // dọn ảnh chụp cũ
  } finally {
    loading.value = false
  }
}
```

Với màn store-driven (N4 + một phần N1): getter đọc lỗi của store, đúng khuôn 3 màn N2 đã chạy 2 vòng:

```ts
const { kind: loadKind, message: loadMsg, blocked: loadBlocked } =
  useDetailAccess(() => (store.currentX ? null : store.lastApiError))
```

Nếu store **không** phơi `lastApiError` (kiểm chứng từng store trước khi viết): view tự `try/catch` quanh lời
gọi store và giữ ref `loadError` của riêng nó — **không** sửa `stores/`.

#### 13.4.1 Khuôn chung `<template>`

```vue
<template>
  <DetailPageShell
    :loading="loading"
    :error-kind="loadKind"
    :error-message="loadMsg"
    :doc="doc"
    entity-label="phiếu bảo trì định kỳ"        <!-- VI viết thường, ghép sau "Không tìm thấy" -->
    :record-id="props.id"
    back-label="Về danh sách bảo trì định kỳ"
    @retry="load"
    @back="router.push('/pm/work-orders')">
    <template #title><PageHeader … /></template>  <!-- vùng DUY NHẤT hiện ở mọi trạng thái -->
    <template #actions>…CTA vòng đời…</template>  <!-- CHỈ render ở trạng thái content -->
    <template v-if="doc">…thân bài…</template>
  </DetailPageShell>
</template>
```

`entityLabel` / `backLabel` phải là **tiếng Việt đầy đủ** và khớp nhãn màn danh sách tương ứng
(vd «hồ sơ năng lực» / «Về danh sách năng lực», **không** «competency»).

#### 13.4.2 Bảy màn có thanh tab — hoisting (ADR-UX-25)

| Màn | Ràng buộc **không được hồi quy** | Cách nối vào shell |
|---|---|---|
| `AssetDetailView` | Nạp **lười** tab «Bản ghi liên quan»: `onTabChange` gọi đúng **1** lần/lần bấm, panel giữ `v-if` | `:tabs="ASSET_TABS"` + `:active-tab="activeTab"` + `@update:active-tab="onTabChange"` |
| `CalibrationDetailView` | 2 tab `detail`/`related`; panel liên quan mount LƯỜI | `v-model:active-tab="activeTab"` |
| `CMWorkOrderDetailView` | như trên | `v-model:active-tab="activeTab"` |
| `CommissioningDetailView` | Tab **theo route**: bấm vẫn `router.push`, `activeTab` là **`computed`** từ `route.name`, cấm state cục bộ. Badge «Không phù hợp × N» (`DetailTab.badge`) phải còn | `:active-tab="activeTab"` + `@update:active-tab="onTab"` — **cấm** `v-model` (computed không setter ⇒ vỡ, bẫy 13.9.2) |
| `IncidentDetailView` | `<DetailTabBar v-if="!loading && form.status">` **biến mất**: nhánh `content` của shell đã bao hàm điều kiện đó. Không tái tạo `v-if` | `v-model:active-tab="activeTab"` |
| `NeedsRequestDetailView` | Panel dùng **`v-show`** để không mất chữ đã gõ ở «Chấm điểm ưu tiên» / «Dự toán» | `v-model:active-tab="activeTab"` |
| `PMWorkOrderDetailView` | 2 tab `detail`/`related`; giữ `v-show` panel `detail` | `v-model:active-tab="activeTab"` |

Mỗi màn: **xoá** `import DetailTabBar…` và **xoá** thẻ `<DetailTabBar …>`; DOM sau khi render phải có
**đúng 1** `[data-testid="detail-tabs"]` và **đúng 1** `[role="tablist"]` (A6).

#### 13.4.3 Hai màn lưỡng dụng tạo/sửa (`ProgramDetailView` · `SessionDetailView`)

Router trỏ **cùng một view** cho `/imm06/programs/new` và `/imm06/programs/:name` (tương tự `sessions`).
Nối shell theo lối ngây thơ ⇒ ở chế độ **tạo mới** `doc` rỗng ⇒ shell rơi vào `notfound` và **biểu mẫu tạo
biến mất**. Hợp đồng bắt buộc:

```vue
<DetailPageShell
  :loading="isCreateMode ? false : loading"
  :error-kind="isCreateMode ? '' : loadKind"
  :doc="isCreateMode ? form : currentProgram"
  :not-found="!isCreateMode && !loading && !currentProgram"
  …>
```

Test `TC-UX4-51/52` **bắt buộc** có sub-case *(g)*: mount ở chế độ tạo ⇒ `data-state="content"`,
**0** phần tử `DetailLoadError`, nút «Tạo …» vẫn render.

#### 13.4.4 Thay đổi DUY NHẤT được cấp phép ở `DetailPageShell.vue`

`tabs` đang khai `{ key: string; label: string }[]` — hẹp hơn SSoT `DetailTab` (đã có trường tuỳ chọn
`badge`, `AC-UX-067`). Hoisting `COMMISSIONING_TABS` (có `badge`) qua prop hẹp là **hợp đồng nói dối**:
kiểu công bố không diễn đạt được thứ component con render. Sửa **type-only**:

```ts
import DetailTabBar, { type DetailTab } from './DetailTabBar.vue'
…
tabs?: DetailTab[]        // thay cho { key: string; label: string }[]
```

Không đổi mặc định (`() => []`), không đổi template, không đổi emit. `DetailPageShell.test.ts` (24 TC) phải
**0 dòng đổi** — nếu phải sửa test cũ thì thay đổi đã vượt phạm vi cho phép, dừng và hỏi BA.

### 13.5 Bất biến đo được — namespace MỚI `INV-UX4L2-*`

| Mã | Bất biến | Đo bằng |
|---|---|---|
| `INV-UX4L2-1` | **Adoption đóng hẳn**: 32/32 `*DetailView.vue` import shell; non-adopter = 0 | `AC-UX-071` phần A |
| `INV-UX4L2-2` | Sổ §13.2 có **đúng 21** dòng, đánh số 1…21, TC liên tục `TC-UX4-32…52`, route THẬT trong router, view file có trên đĩa | `AC-UX-071` phần B |
| `INV-UX4L2-3` | Parity **2 chiều**: `import DetailPageShell` ⟺ ô «Trạng thái» = `ĐÃ ĐÓNG` | `AC-UX-071` phần B |
| `INV-UX4L2-4` | Mỗi màn `ĐÃ ĐÓNG` có `<tên>DetailStates.test.ts` **đặt cạnh nó**, khai đúng ở §13.6 | `AC-UX-071` phần C |
| `INV-UX4L2-5` | Màn `ĐÃ ĐÓNG`: shell là **thẻ gốc duy nhất** · `page-container` == 0 · `text-red-500` == 0 · **0** nhánh `v-if/v-else-if` tự quyết trạng thái TẢI | `AC-UX-071` phần D |
| `INV-UX4L2-6` | **SSoT lỗi**: mọi màn `ĐÃ ĐÓNG` import `useDetailAccess` và **0** lần gọi `loadErrorKind` trực tiếp; 11 màn legacy đóng băng, CHỈ-GIẢM | `AC-UX-072` |
| `INV-UX4L2-7` | **1 thanh tab**: DOM đã render của 7 màn có **đúng 1** `[data-testid="detail-tabs"]` và **đúng 1** `[role="tablist"]`; **0** `<DetailTabBar` trong nguồn view | `TC-UX4-32/33/34/35/39/42/44` + `detailTabBarAdoption` |
| `INV-UX4L2-8` | **0 nút chết**: `blocked === true` ⇒ `detail-actions` == 0 **và** mọi `data-testid` CTA của màn == 0 | 21 file trạng thái, sub-case *(d)* |

### 13.6 Bộ test — 21 file trạng thái (mỗi file **≥ 6 case**, mount THẬT)

| TC | File test |
|---|---|
| `TC-UX4-32` | `frontend/src/views/asset/assetDetailStates.test.ts` |
| `TC-UX4-33` | `frontend/src/views/calibration/calibrationDetailStates.test.ts` |
| `TC-UX4-34` | `frontend/src/views/cm/cmWorkOrderDetailStates.test.ts` |
| `TC-UX4-35` | `frontend/src/views/commissioning/commissioningDetailStates.test.ts` |
| `TC-UX4-36` | `frontend/src/views/compliance/complianceRuleDetailStates.test.ts` |
| `TC-UX4-37` | `frontend/src/views/document/documentDetailStates.test.ts` |
| `TC-UX4-38` | `frontend/src/views/eol/decommissionDetailStates.test.ts` |
| `TC-UX4-39` | `frontend/src/views/incident/incidentDetailStates.test.ts` |
| `TC-UX4-40` | `frontend/src/views/incident/rcaDetailStates.test.ts` |
| `TC-UX4-41` | `frontend/src/views/inventory/cycleCountDetailStates.test.ts` |
| `TC-UX4-42` | `frontend/src/views/needs/needsRequestDetailStates.test.ts` |
| `TC-UX4-43` | `frontend/src/views/needs/procurementPlanDetailStates.test.ts` |
| `TC-UX4-44` | `frontend/src/views/pm/pmWorkOrderDetailStates.test.ts` |
| `TC-UX4-45` | `frontend/src/views/procurement/vendorEvalDetailStates.test.ts` |
| `TC-UX4-46` | `frontend/src/views/procurement/vendorProfileDetailStates.test.ts` |
| `TC-UX4-47` | `frontend/src/views/purchase/purchaseDetailStates.test.ts` |
| `TC-UX4-48` | `frontend/src/views/purchase/serviceContractDetailStates.test.ts` |
| `TC-UX4-49` | `frontend/src/views/tech-specs/techSpecDetailStates.test.ts` |
| `TC-UX4-50` | `frontend/src/views/training/competencyDetailStates.test.ts` |
| `TC-UX4-51` | `frontend/src/views/training/programDetailStates.test.ts` |
| `TC-UX4-52` | `frontend/src/views/training/sessionDetailStates.test.ts` |

**Sub-case BẮT BUỘC (lô 2)** — mỗi file phải có đủ, mount THẬT (không `shallowMount`, không stub shell):

- **(a) đang tải** — `data-state="loading"`, có `detail-skeleton`, **0** `detail-actions`, **0** `detail-content`.
- **(b) lỗi mạng** (`kind='unknown'`) — `data-state="error"`, câu VI riêng, **có** nút «Thử lại», bấm ⇒ gọi lại
  **đúng hàm nạp** (spy đếm), **0** `detail-content`.
- **(c) 403 in-envelope** (`ApiError` `code='FORBIDDEN'` / `httpStatus=403` trên **HTTP-200**) — `data-kind="forbidden"`,
  hiện **message THẬT của server** + hằng `ACCESS_DENIED_HINT`; **KHÔNG** gọi `logout`, **KHÔNG**
  `router.push('/login')` (phân biệt dispatcher-403 ở `api/axios.ts::handle403`).
- **(d) 0 nút chết** — ở cả (b), (c) và trạng thái `notfound`: `detail-actions` == 0 **và** từng `data-testid`
  CTA đặc thù của màn == 0 (liệt kê tường minh trong test, không dùng ước lệ).
- **(e) 404 / bản ghi rỗng** — `data-kind="notfound"`, câu VI **kèm mã người dùng đã gõ**, nút quay về danh sách,
  **0** «Thử lại» thừa, **0** `detail-actions`.
- **(f) có dữ liệu** — `data-state="content"`, `detail-actions` ≥ 1, **0** phần tử `DetailLoadError`.
- **(g) — CHỈ 7 màn có tab**: `[data-testid="detail-tabs"]` xuất hiện **đúng 1** lần và `[role="tablist"]`
  **đúng 1** lần; bấm tab thứ 2 ⇒ `activeTab` đổi đúng 1 lần (Commissioning: `router.push` được gọi, state cục
  bộ **không** đổi).
- **(g') — CHỈ 2 màn lưỡng dụng**: chế độ tạo ⇒ `content`, biểu mẫu còn nguyên (§13.4.3).

**Ba trạng thái lỗi phải cho ra BA CÂU KHÁC NHAU** (A4). Câu do `DetailLoadError.vue` sở hữu — test assert
**khác nhau từng đôi một**, không assert chuỗi cứng chép tay ở 21 file (chép tay ⇒ đổi copy 1 nơi, đỏ 21 nơi).

### 13.7 Hai guard MỚI — hợp đồng

#### 13.7.1 `frontend/src/views/detailShellAdoption.test.ts` (**AC-UX-071**)

Sao chép khuôn `views/listShellAdoption.test.ts` (`AC-UX-070`) — **không viết bộ quét thứ hai**.

```ts
const SHELL_IMPORT = /from\s+'@\/components\/common\/DetailPageShell\.vue'/
const TOTAL_DETAIL_VIEWS = 32
const NON_ADOPTER_BUDGET: readonly string[] = [ /* 21 dòng lúc mở lô → RỖNG cuối vòng */ ]
```

| Phần | Bất biến |
|---|---|
| **A** | `files.length === TOTAL_DETAIL_VIEWS` · mọi dòng sổ trỏ file có thật · **nợ không mọc thêm** (non-adopter ∉ sổ ⇒ ĐỎ) · **trả nợ phải hạ sổ** (adopter còn trong sổ ⇒ ĐỎ) · `sổ == tập non-adopter` (không thừa không thiếu) |
| **B** | Sổ §13.2 đúng 21 dòng, số 1…21, TC `TC-UX4-32…52` không trùng · route THẬT trong `router/index.ts` · view file tồn tại và **trùng ô view file** ở `00 §3.1` · parity 2 chiều `import` ⟺ `ĐÃ ĐÓNG` |
| **C** | Mỗi adopter có `<tên>DetailStates.test.ts` **đặt cạnh** (so khớp không phân biệt hoa/thường — quy ước camelCase của repo không đều ở tiền tố viết tắt `RCA`/`PM`/`CM`) và được khai ở §13.6 |
| **D** | Màn `ĐÃ ĐÓNG`: thẻ gốc `<DetailPageShell` · `page-container` == 0 · `text-red-500` == 0 · 0 nhánh `v-(if\|else-if)="…loading…"` tự chế |

Cuối vòng: `NON_ADOPTER_BUDGET` **RỖNG** ⇒ guard chuyển sang chế độ **đóng băng 0**: thêm `*DetailView.vue`
mới không có khuôn ⇒ ĐỎ ngay.

#### 13.7.2 `frontend/src/views/detailAccessAdoption.test.ts` (**AC-UX-072**)

```ts
/** 11 màn đã áp shell nhưng còn `loadErrorKind` cục bộ — ĐÓNG BĂNG, CHỈ ĐƯỢC XOÁ DÒNG. */
const LEGACY_LOCAL_KIND_BUDGET: readonly string[] = [
  'views/asset/AssetTransferDetailView.vue',
  'views/compliance/FindingDetailView.vue',
  'views/compliance/InternalAuditDetailView.vue',
  'views/compliance/ManagementReviewDetailView.vue',
  'views/document/FirmwareCrDetailView.vue',
  'views/incident/CAPADetailView.vue',
  'views/inventory/SparePartDetailView.vue',
  'views/inventory/StockMovementDetailView.vue',
  'views/inventory/WarehouseDetailView.vue',
  'views/procurement/DecisionDetailView.vue',
  'views/purchase/SupplierDetailView.vue',
]
```

Bất biến:
1. **Adopter ⇒ SSoT**: mọi `*DetailView.vue` import `DetailPageShell` phải import `useDetailAccess`,
   **trừ** dòng có trong `LEGACY_LOCAL_KIND_BUDGET`.
2. **Không gọi trực tiếp**: màn ngoài sổ legacy có **0** hit `loadErrorKind(` (comment đã `stripComments`).
3. **CHỈ-GIẢM**: dòng legacy nào đã dùng `useDetailAccess` ⇒ **ĐỎ** (phải xoá dòng cùng lượt); sổ phải khớp
   khít tập đo được (không thừa, không thiếu) ⇒ **cấm thêm dòng**.
4. **Bộ đếm công bố**: `grep -l useDetailAccess` == **21** ở cuối vòng, và số này bằng số dòng `ĐÃ ĐÓNG` của
   sổ §13.2 (chống «doc nói 21, đĩa 19»).
5. Mọi dòng trong sổ legacy phải trỏ file **có thật** (chống sổ chết).

### 13.8 Sửa guard cũ **trong CÙNG lượt** — 3 việc bắt buộc, tamper-evident

1. **`views/detailTabBarAdoption.test.ts` (AC-UX-069) — di trú danh sách, KHÔNG xoá assert.**
   Phần B (e) hiện ép **7 màn** `import DetailTabBar` + có đúng 1 thẻ `<DetailTabBar>`. Sau hoisting, 7 màn
   đó **không còn import** ⇒ ĐỎ. Sửa: chuyển 7 đường dẫn từ `MUST_USE_SSOT` sang danh sách mới
   `MUST_USE_SSOT_VIA_SHELL`, gộp với `InternalAuditDetailView` (đã sẵn ở test (h)) ⇒ **8 mục**, assert cho
   từng mục: `import DetailTabBar` == **false** · chứa `DetailPageShell` · chứa `active-tab` · `<DetailTabBar`
   == **0**. Thêm `expect(MUST_USE_SSOT_VIA_SHELL).toHaveLength(8)` để việc rút ngắn danh sách là tamper-evident.
   **Giữ nguyên** phần A (bản đồ nút-tab tự chế) và assert (g) `role="tablist"` chỉ ở SSoT.
2. **`router/uiDetailShellLot1Parity.test.ts` (INV-UX4L1-5) — nới công thức token (ADR-UX-26).**
   Thêm hằng `LOT2_NO_RECOVERY` = **12** đường dẫn đang thuộc nhóm 0-lối-nạp-lại
   (`asset/AssetDetailView` · `commissioning/CommissioningDetailView` · `document/DocumentDetailView` ·
   `incident/RCADetailView` · `needs/NeedsRequestDetailView` · `needs/ProcurementPlanDetailView` ·
   `procurement/VendorEvalDetailView` · `procurement/VendorProfileDetailView` · `purchase/PurchaseDetailView` ·
   `purchase/ServiceContractDetailView` · `tech-specs/TechSpecDetailView` · `training/CompetencyDetailView`),
   rồi đổi đẳng thức thành `N == 20 − closedLot1 − closedLot2NoRecovery` (đếm từ cột «Trạng thái» của §13.2).
   **Giữ nguyên** đẳng thức `N == số đo lại từ đĩa` — đó mới là bất biến thật. Cập nhật token `NO-DET` ở
   `00 §6` về **0** trong cùng lượt.
3. **`router/uiListShellLot1Parity.test.ts` (INV-UX3L-5/6) — lật 7 ô + đo lại token.**
   Sau khi 21 màn có `@retry`, bộ dò sẽ lật **7 ô ❌ → ✅** (danh sách ở ĐÍNH CHÍNH 2). Chạy
   `node frontend/scripts/ui-audit-inventory.mjs --check`, sửa **đúng những ô nó báo lệch** ở `00 §3.1`, rồi
   ghi token `NO-CON` = **số bộ dò in ra** (kỳ vọng 57 − 7 = **50**, nhưng **ghi số đo được**, không ghi số kỳ vọng).

Guard `AC-UX-071/072` phải **ĐỎ trước, XANH sau**: viết guard với sổ 21 dòng ⇒ xanh; land 1 màn mà quên hạ sổ
⇒ đỏ. QA phải chứng kiến ít nhất **một** lần đỏ có chủ đích (mutation test) trên mỗi guard.

### 13.9 Bẫy đã biết — ĐỌC TRƯỚC KHI CODE (bổ sung cho §7 và §12.7)

**13.9.1 `useDetailAccess` trả về object chứa `ComputedRef` — template KHÔNG tự bóc.**
`const access = useDetailAccess(…)` rồi `:error-kind="access.kind"` truyền **cả ref** ⇒ shell nhận object
truthy ⇒ **màn nào cũng kẹt ở trạng thái `error`**. Bắt buộc destructure đổi tên (khuôn §13.4.0), đúng như
`PMWorkOrderDetailView.vue:67-71` đã làm.

**13.9.2 `v-model:active-tab` trên một `computed` không setter = vỡ.**
`CommissioningDetailView` lấy `activeTab` từ `route.name`. Dùng `:active-tab` + `@update:active-tab` (đẩy
`router.push`), **không** `v-model`.

**13.9.3 `activeTab` phải là `ref<string>`.**
4 màn đang khai `ref<'detail' | 'related'>`. Prop/emit của shell là `string` ⇒ `vue-tsc` báo
`string not assignable to 'detail' | 'related'`. Đổi thành `ref<string>('detail')` (tiền lệ
`InternalAuditDetailView.vue:32`), giữ khoá tab trong hằng `DetailTab[]`. Đây là §7.4 áp lại cho lô 2.

**13.9.4 Type-narrowing biến mất khi rời `<template v-else>`.**
Mọi slot deref bản ghi phải bọc `<template v-if="doc">` — nếu không `vue-tsc` báo `possibly null` hàng loạt
(§7.2, INV-UX4-12).

**13.9.5 `page-container` lồng nhau.** Shell đã mang lớp bao. `VendorProfileDetailView` và
`ProcurementPlanDetailView` có **2** lần `page-container` — cả hai phải về 0, nếu không padding/max-width nhân đôi.

**13.9.6 `text-red-500` → `text-danger-500`.** Còn **36** lần ở **11** màn của lô (Asset 5 · Calibration 7 ·
Incident 4 · Competency 4 · Session 4 · RCA 3 · PM 3 · Program 3 · CM 1 · Commissioning 1 · ProcurementPlan 1). Dấu sao
trường bắt buộc **KHÔNG được xoá** (mất tín hiệu a11y) — chỉ đổi token màu (`tailwind.config.js` `danger-500`
= `#dc2626`, có `--ac-color-danger-500` đối ứng). `INV-UX4L2-5` ép về 0 cho màn `ĐÃ ĐÓNG`.

**13.9.7 Lỗi HÀNH ĐỘNG ≠ lỗi NẠP.** 7 màn nhóm N3 dùng CHUNG một ref cho cả hai. Nối ref cũ vào
`:error-kind` ⇒ bấm «Xoá» hỏng sẽ **thay cả trang bằng banner lỗi** và người dùng mất luôn dữ liệu đang xem.

**13.9.8 404 trên HTTP-200.** BE trả `{success:false, code:'NOT_FOUND', http_status:404}` trong envelope
(HTTP-200). Test phải dựng `ApiError` **theo envelope**, không giả `status: 404` ở tầng axios — nếu không
`loadErrorKind` cho ra `unknown` và sub-case (e) xanh giả.

**13.9.9 85 file test cũ (distinct) bám 21 màn này.** Đông nhất: `AssetDetailView` **24** file ·
`CMWorkOrderDetailView` **15** · `IncidentDetailView` **13** · `PMWorkOrderDetailView` **13** ·
`CalibrationDetailView` **13**. Chúng khoá
`data-testid`, nhãn nút, và **cấu trúc DOM** (`detailReadForbiddenGate` · `detailBlockedNoTabBar` ·
`relatedRecordsTabParity` · `*CtaGating` · `modalOverlayHygiene`). Luật: **0 assert cũ bị xoá**; nếu một test
cũ đỏ vì DOM đổi, sửa **selector** chứ không sửa **kỳ vọng**. `VendorProfileDetailView` là màn **duy nhất**
0 test cũ.

**13.9.10 `detailBlockedNoTabBar.test.ts` vẫn phải xanh.** Nó ép «phiếu bị chặn đọc ⇒ 0 thanh tab». Sau
hoisting, điều đó **đúng bằng cấu trúc** (thanh tab nằm trong nhánh `content`). Đừng thêm `v-if` bù.

**13.9.11 Guard `TC-RWD-01`** cấm breakpoint tuỳ biến trong `src/views` — đừng bê class responsive của thanh
tab cũ vào view (SSoT đã có `overflow-x-auto` + `shrink-0`).

**13.9.12 Đếm adoption bằng IMPORT, không bằng chuỗi.** `grep -c DetailPageShell` đếm cả chú thích. Dấu vân
tay duy nhất: `from '@/components/common/DetailPageShell.vue'`.

### 13.10 Lệnh chấm (QA **tự đo lại**, không nhận báo cáo suông)

```bash
cd /home/miyano/frappe-bench/apps/assetcore/frontend

# (a) A1 — adoption ĐÓNG HẲN 32/32, non-adopter 0
find src/views -name '*DetailView.vue' | wc -l                                   # 32
grep -rl "from '@/components/common/DetailPageShell.vue'" --include='*DetailView.vue' src/views | wc -l   # 32

# (b) A2 — SSoT lỗi lan đủ (đích ĐÃ ĐÍNH CHÍNH: 21, không phải 24)
grep -rl useDetailAccess --include='*DetailView.vue' src/views | wc -l           # 21
# 21 màn lô 2 không được gọi trực tiếp:
grep -rln "loadErrorKind(" --include='*DetailView.vue' src/views | wc -l          # 11 (đúng bằng sổ legacy)

# (c) A6 — 1 thanh tab: 0 view nào còn import trực tiếp trong 7 màn hoisting
grep -rl "import DetailTabBar" --include='*DetailView.vue' src/views | wc -l      # 0

# (d) A3/A5 — 21 file trạng thái + guard mới
ls src/views/*/*DetailStates.test.ts | wc -l                                      # 32 (11 hiện có + 21 mới)
npx vitest run src/views/detailShellAdoption.test.ts src/views/detailAccessAdoption.test.ts

# (e) A8 — guard cũ KHÔNG đỏ
npx vitest run src/router/uiAuditDocParity.test.ts src/router/uiFixPlanParity.test.ts \
  src/views/listShellAdoption.test.ts src/views/detailTabBarAdoption.test.ts \
  src/router/uiDetailShellLot1Parity.test.ts src/router/uiListShellLot1Parity.test.ts \
  src/components/common/modalOverlayHygiene.test.ts src/components/ui/uiPrimitiveHygiene.test.ts \
  src/design/tokens.parity.test.ts

# (f) A7 — suite + kiểu, ĐỌC BẰNG MẮT
npx vitest run            # kỳ vọng 377 + 23 = 400 file, 0 đỏ
npx vue-tsc --noEmit      # 0 lỗi

# (g) bộ dò + token (§13.8 mục 3)
node scripts/ui-audit-inventory.mjs --check
node scripts/ui-audit-inventory.mjs --summary     # ghi ĐÚNG số in ra vào token NO-CON

# (h) A10 — vệ sinh
cd /home/miyano/frappe-bench/apps/assetcore && git status --porcelain -- '*.py'   # RỖNG
ls *.png 2>/dev/null | wc -l                                                     # 0
```

**DoD lô 2 (đủ 10 ô mới được tuyên bố xong):** adoption 32/32 · `useDetailAccess` 21 · 0 import trực tiếp
`DetailTabBar` ở 7 màn · 21 file trạng thái xanh, mỗi file ≥ 6 case · 2 guard mới xanh **và** đã chứng kiến 1
lần đỏ có chủ đích · 3 guard cũ đã sửa theo §13.8 và xanh · suite 400 file / 0 đỏ · `vue-tsc` 0 lỗi · doc
(`00`, `03`, `04`) đồng bộ với đĩa · `git status -- '*.py'` rỗng, repo root sạch.

### 13.11 Quyết định kiến trúc — ADR-UX-25 / 26 / 27

#### ADR-UX-25 (`AC-UX-073`): thanh tab **hoisting lên prop shell**, không giữ tab cục bộ
- **Status**: Accepted — 2026-08-04
- **Context**: 7/21 màn của lô đang tự gắn `<DetailTabBar>` trong template của mình. Bọc chúng vào
  `DetailPageShell` mà không quyết định gì ⇒ hai đường vẽ tab cùng tồn tại (prop `tabs` của shell **và** thẻ
  cục bộ) ⇒ nguy cơ **2 thanh tab** trong một màn, hoặc 2 `role="tablist"` — lỗi a11y nặng hơn trước khi sửa.
  Tiền lệ đã có: `InternalAuditDetailView` (lô vòng 4) đi **gián tiếp** qua shell (`ADR-UX-07`) và guard
  `detailTabBarAdoption` test (h) đã khoá đúng hình dạng ấy.
- **Decision**: **Hoisting.** 7 màn khai `DetailTab[]` rồi truyền `:tabs` + `active-tab` cho shell; **xoá**
  `import DetailTabBar` và thẻ cục bộ. Shell là nơi **duy nhất** quyết định thanh tab nằm trong nhánh
  `content`. Kiểu prop `tabs` nới thành `DetailTab[]` (§13.4.4) để `badge` không bị hợp đồng che mất.
- **Alternatives**: (a) *giữ tab cục bộ + shell `tabs` rỗng* — loại: `[data-testid="detail-tabs"]` sẽ **0**,
  không đo được «đúng 1 lần» của A6, và tồn tại 2 cách làm cùng việc ⇒ màn sau lại chọn nhầm; (b) *prop
  `tabsPosition`* — loại: thêm bậc tự do cho một quyết định đáng ra phải nhất quán; (c) *bỏ `DetailTabBar`,
  shell tự vẽ tab* — loại: fork markup, phá SSoT `AC-UX-067`.
- **Consequences**: `detailTabBarAdoption.test.ts` phải di trú 7 đường dẫn sang `MUST_USE_SSOT_VIA_SHELL`
  (§13.8 mục 1) — **cùng lượt**, kèm assert độ dài 8 để không ai rút ngắn danh sách. Thanh tab luôn nằm
  **dưới** `#actions`/`#kpi` và **trên** nội dung — thứ tự này từ nay là hợp đồng, không phải tuỳ màn.
  `Commissioning` phải dùng cặp `:active-tab` + `@update:active-tab` (computed không setter).

#### ADR-UX-26: token `NO-DET` giữ **hai** phép đo, nới công thức thay vì bỏ đẳng thức
- **Status**: Accepted — 2026-08-04
- **Context**: `INV-UX4L1-5` ép đồng thời `N == 20 − closedLot1` và `N == đo lại từ đĩa`. Lô 2 kéo vế đĩa về 0
  trong khi vế số học đông cứng ở 12 ⇒ guard ĐỎ dù mã hoàn toàn đúng.
- **Decision**: **nới** vế số học bằng số hạng lô 2 (`LOT2_NO_RECOVERY`, 12 đường dẫn tường minh), **giữ**
  vế đo-từ-đĩa nguyên vẹn.
- **Alternatives**: (a) xoá vế số học — loại: mất khả năng phát hiện «doc quên cập nhật khi lô đóng»;
  (b) đổi mốc 20 thành số mới — loại: đúng loại «mốc sẽ lại stale» mà `ADR-UX-22` đã bác;
  (c) để guard đỏ rồi skip — loại tuyệt đối.
- **Consequences**: mỗi lô chi tiết mới phải **khai tường minh** phần đóng góp của mình vào token; đổi lại
  không lô nào đóng được mà quên cập nhật tài liệu ĐO.

#### ADR-UX-27: `useDetailAccess` là **SSoT lỗi nạp** cho màn chi tiết; nợ cũ đóng băng theo sổ
- **Status**: Accepted — 2026-08-04 (đóng `AC-UX-053` phần hợp đồng)
- **Context**: `AC-UX-053` để ngỏ câu hỏi «shell nhận thẳng object `access` hay giữ 3 prop rời». Hôm nay 11
  màn đã áp shell nhưng **tự gọi** `loadErrorKind` (3 bản sao logic phân loại), 3 màn dùng composable.
- **Decision**: **giữ 3 prop rời** (`errorKind` / `errorMessage` / `doc`) ở shell — shell vẫn «dumb như tầng
  0», không biết composable nào tồn tại; **nguồn** của 3 prop đó bắt buộc là `useDetailAccess` ở phía view.
  11 màn legacy **đóng băng** trong `LEGACY_LOCAL_KIND_BUDGET` (CHỈ-GIẢM), không di trú ở vòng này.
- **Alternatives**: (a) shell nhận `access` object — loại: shell phải import composable ⇒ vi phạm luật tầng
  (§3.0) và mọi test shell phải dựng composable; (b) di trú luôn 11 màn legacy — loại: 32 màn đổi trong một
  vòng, rủi ro chồng rủi ro, và `AC-UX-072` sẽ mất mốc CHỈ-GIẢM để đo.
- **Consequences**: sau vòng này còn **đúng 11** màn nợ SSoT lỗi, đo được bằng một dòng `grep`, đóng dần
  bằng cách **xoá dòng** khỏi sổ — không bao giờ thêm dòng.
