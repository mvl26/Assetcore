# Khuôn màn DANH SÁCH — `ListPageShell` (Core Doc VÒNG 3)

| Mục | Giá trị |
|---|---|
| Phạm vi | `frontend/src/components/ui/ListPageShell.vue` (primitive #8) + **4 màn danh sách thật** — **cross-cutting, KHÔNG thuộc IMM-XX** |
| Loại tài liệu | Core Doc cross-cutting (UI/UX) — spec thi hành cho FE dev vòng 3 |
| Owner | BA (đặc tả) · FE dev (thi hành) · QA (chấm A1–A12) |
| Trạng thái | **Chốt để code** — spec-before-code gate ĐẠT |
| Ngày đo | 2026-07-31 (mọi số/dòng trích trong tài liệu này đo TỪ ĐĨA hôm nay) |
| Nhánh | `feature/hieuc/core-refinement` @ `3a6a391` |
| Tài liệu mẹ | [`00_AUDIT_HIEN_TRANG.md`](./00_AUDIT_HIEN_TRANG.md) — §2.1 (nợ «Lỗi+Thử lại») · §6 sổ `AC-UX-041…047` · §9 **ADR-UX-05** |
| Tài liệu anh | [`01_DESIGN_SYSTEM.md`](./01_DESIGN_SYSTEM.md) — §3.0 luật chung primitive · §3.5 `EmptyState` · §3.6 `ErrorState` · §3.7 `Skeleton` · §6 guard vệ sinh |

> **Vì sao có tài liệu này.** Vòng 2 dựng xong tầng 0 nhưng **chưa màn nào dùng** (nợ `AC-UX-038`).
> Nợ nặng nhất còn lại của lớp danh sách **không phải** thiếu skeleton — mà là **lỗi giả dạng rỗng**
> (*false-empty*): API hỏng → view rơi vào nhánh «chưa có dữ liệu» → người dùng tin là **không có bản ghi**
> và không có đường thử lại. Bộ dò `ui-audit-inventory.mjs` đếm **94/148 route** thiếu lối «Thử lại» (đo 2026-07-31).
> Vòng 3 đóng **4 route** bằng cách dựng **một khuôn** (`ListPageShell`) rồi áp thật — không vá lẻ từng màn.

---

## §0. Phạm vi & Boundaries

**Always (bắt buộc mọi thay đổi vòng 3):**
- **4 trạng thái LOẠI TRỪ LẪN NHAU** — `loading` · `error` · `empty` · `content`. Mọi màn danh sách chỉ được render **đúng 1** trong 4 tại một thời điểm (bảo đảm bằng cấu trúc `v-if/v-else-if/v-else`, không phải bằng quy ước).
- **Lỗi LUÔN thắng trạng thái rỗng.** Có lỗi ⇒ **cấm** hiện bất kỳ câu «chưa có / không có dữ liệu» nào.
- Mọi trạng thái lỗi phải có **đúng 1** control «Thử lại» **gọi lại chính hàm nạp** (không phải chỉ xoá banner).
- **Bộ lọc không được biến mất khi lỗi** — người dùng phải sửa được chính bộ lọc gây lỗi.
- Shell **COMPOSE** `PageHeader.vue` / `ListFilterBar.vue` / `BasePagination.vue` **qua slot**; primitive giữ luật **dumb** của `01 §3.0` (0 API, 0 store, 0 router).
- Mỗi hàm nạp phải **xoá lỗi cũ ở ĐẦU lượt nạp** và **luôn hạ cờ `loading` trong `finally`**.

**Ask first (hỏi BA/PM trước khi làm):**
- Thêm primitive thứ **9** vào `components/ui/`.
- Thêm/bớt trạng thái ngoài 4 trạng thái đã chốt, hoặc đổi thứ tự ưu tiên ở §2.
- Áp `ListPageShell` cho màn **thứ 5** trở đi trong cùng vòng (adoption diện rộng = `AC-UX-047`, vòng 4).
  → **ĐÃ DUYỆT cho lô 1** (12 màn, danh sách đóng ở **§12.2**). Màn **thứ 13** trở đi vẫn phải hỏi lại.
- Đổi phân trang của 4 màn đích sang `BasePagination` (đụng hợp đồng `PaginationMeta` — vòng 4).

**Never (tuyệt đối không, vòng 3):**
- **KHÔNG** sửa `frontend/src/stores/**`, `frontend/src/api/**`, bất kỳ `.py` nào — kể cả khi lỗi gốc nằm ở đó (xem `AC-UX-044`: `stores/imm01.ts::fetchPlans` **không** set `loading`; view phải tự giữ cờ, **không** vá store ở vòng này).
- **KHÔNG** viết lại header / filter / pagination mới — chỉ đưa markup **đang có** vào slot.
- **KHÔNG** thêm phân trang cho màn mà store/API chưa hỗ trợ (`/vendor-profiles`, `/procurement-plans` hiện kéo 1 lượt: `listVendorProfiles(f, 1, 100)` tại `VendorProfileListView.vue:30`, `fetchPlans` mặc định `ps = 50` tại `stores/imm01.ts:108`).
- **KHÔNG** lồng `ErrorState` của `DataTable` (`01 §11` mục 7) bên trong `ListPageShell` ⇒ sẽ có **2** nút «Thử lại», vỡ bất biến A3.
- **KHÔNG** đổi `data-testid` đang được test khoá, **KHÔNG** đụng bảng §3.1 của tài liệu mẹ (ảnh chụp baseline).
  → **SUPERSEDED bởi ADR-UX-11** (`00 §9`) kể từ lô 1: `00 §3.1` là bảng **SỐNG** — mỗi lô adoption **phải** lật
  ô «Lỗi+Thử lại» của **đúng** các route trong lô (guard `uiListShellLot1Parity.test.ts` ép 2 chiều). Chỉ bảng
  tổng hợp `00 §2.1` còn đóng băng (`ADR-UX-10`).
- **KHÔNG** dùng class palette thô (`slate-*`, `emerald-*`…) trong `ListPageShell.vue` — guard `INV-UI-1` đỏ ngay.

---

## §1. Hiện trạng đo từ đĩa — bằng chứng phải sửa (2026-07-31)

### 1.1 Bốn màn đích — triệu chứng THẬT khi API hỏng

Nền tảng chung: `frappeGet` **ném lỗi** (`api/helpers.ts:87-90` → `unwrap` `:76-85` ném `ApiError` khi envelope `success=false`; lỗi HTTP do axios ném). Vậy mọi màn **không** `catch` đều rơi vào một trong hai kiểu hỏng dưới đây.

| # | Route / View | Mã hiện tại | Triệu chứng người dùng thấy khi API 500 | Cột «Lỗi+Thử lại» |
|---|---|---|---|---|
| 1 | `/purchases` · `views/purchase/PurchaseListView.vue` | `load()` `:80-92` có `try … finally`, **0 `catch`** ⇒ `rows` giữ `[]`; nhánh `v-else-if="!rows.length"` `:157` | **«Chưa có đơn hàng nào»** `:158` — *false-empty kinh điển* | ❌ |
| 2 | `/user-profiles` · `views/auth/UserProfileListView.vue` | `load()` `:92-107` **0 `try/catch`**; `loading.value = false` `:102` nằm SAU `await` ⇒ không bao giờ chạy khi ném | **Khung xương quay mãi** (`v-if="loading"` `:230`) + unhandled rejection trong `onMounted` `:113-117` | ❌ |
| 3 | `/vendor-profiles` · `views/procurement/VendorProfileListView.vue` | có `catch` `:33-35` + banner `.alert-error` `:88-90`, nhưng `items` vẫn `[]` ⇒ nhánh `v-else` `:167` chạy cùng lúc | **Banner lỗi VÀ «Chưa có nhà cung cấp nào.» `:168` cùng hiện** (double-state) — vẫn **0 nút thử lại** | ❌ |
| 4 | `/procurement-plans` · `views/needs/ProcurementPlanListView.vue` | banner `store.error` `:199-202`, nút `×` gọi `store.clearError()` **`:201`** (chỉ xoá banner); `store.plans` `[]` ⇒ nhánh `:297` | **«Không có kế hoạch nào phù hợp» `:298`** + nút `×` **giả dạng thử lại** | ❌ |

**Xác nhận A4 (đo lại được):**
```bash
grep -cE 'error|catch' frontend/src/views/auth/UserProfileListView.vue   # → 0
sed -n '157,158p' frontend/src/views/purchase/PurchaseListView.vue       # → v-else-if="!rows.length" / «Chưa có đơn hàng nào»
```

### 1.2 Hai khuyết tật NỀN phát hiện thêm khi đọc mã (ghi sổ, KHÔNG sửa ở vòng 3)

| Mã sổ | Bằng chứng | Hệ quả | Vòng |
|---|---|---|---|
| `AC-UX-044` | `stores/imm01.ts:108-113` — `fetchPlans` **không** set `loading`, **không** clear `error` đầu lượt, nuốt lỗi vào `_setError` | Nhánh `v-if="store.loading"` (`ProcurementPlanListView.vue:213`) là **mã chết**; lỗi cũ dính lại sau lượt nạp mới | 4 (đụng `stores/`) |
| `AC-UX-046` | `VendorProfileListView.vue:116-118` và `ProcurementPlanListView.vue:233-235` | Nhánh rỗng nằm **bên trong** `v-else-if="items.length"` / `v-else-if="store.plans.length"` ⇒ điều kiện `length === 0` **không bao giờ đúng** = mã chết in «Không có dữ liệu» | 3 (xoá cùng lượt refactor) |

### 1.3 Baseline bộ dò (nguồn chấm DELTA — A7)

```
node frontend/scripts/ui-audit-inventory.mjs   # 2026-07-31, trên đĩa
```
| Cột | ❌ | Ghi chú |
|---|---|---|
| **Lỗi+Thử lại** | **94** | bảng tay §2.1 ghi **83** — lệch quy ước, đã ghi sổ `AC-UX-031`; **dùng bộ dò làm nguồn chấm delta** |
| Rỗng+HD | 28 | bảng tay ghi 26 (cùng nguyên nhân lệch quy ước) |
| a11y | 78 | bảng tay ghi 87 |

4 dòng đích trong đầu ra baseline (thứ tự cột: Loading · Skeleton · Rỗng+HD · **Lỗi+Thử lại** · ≤768px · Nhãn VI · a11y):

| # | Route | Loading | Skeleton | Rỗng+HD | **Lỗi** | ≤768px | VI | a11y |
|---|---|---|---|---|---|---|---|---|
| 108 | `/purchases` | ✅ | ✅ | ✅ | **❌** | ❌ | ✅ | ❌ |
| 117 | `/user-profiles` | ✅ | ✅ | ✅ | **❌** | ✅ | **❌** | ❌ |
| 125 | `/procurement-plans` | ✅ | ❌ | ✅ | **❌** | ❌ | ✅ | ❌ |
| 135 | `/vendor-profiles` | ✅ | ❌ | ❌ | **❌** | ✅ | ✅ | ❌ |

**Kỳ vọng sau vòng 3:** cột *Lỗi+Thử lại* **94 → 90** (đúng −4). Cột *Skeleton* +2 ✅ (`/procurement-plans`, `/vendor-profiles`), cột *Rỗng+HD* +1 ✅ (`/vendor-profiles`), cột *Nhãn VI* +1 ✅ (`/user-profiles`) — **đều là cải thiện, không phải nợ mới**. **0** ô đang ✅ được phép lật thành ❌.

---

## §2. Máy trạng thái — 4 trạng thái loại trừ lẫn nhau

### 2.1 Định nghĩa (SSoT — cài đúng 1 lần trong `ListPageShell.vue`)

```ts
type ListState = 'error' | 'loading' | 'empty' | 'content'

const state = computed<ListState>(() => {
  if (props.errorMessage && props.errorMessage.trim()) return 'error'
  if (props.loading) return 'loading'
  if (props.isEmpty) return 'empty'
  return 'content'
})
```

**Thứ tự ưu tiên: `error` > `loading` > `empty` > `content`.**

| Tín hiệu vào | | | Trạng thái | Body render |
|---|---|---|---|---|
| `errorMessage` | `loading` | `isEmpty` | | |
| có (sau `trim`) | * | * | **error** | `ErrorState` (+ nút «Thử lại») |
| rỗng/null | `true` | * | **loading** | slot `#skeleton` (mặc định `Skeleton`) |
| rỗng/null | `false` | `true` | **empty** | `EmptyState` (+ slot `#empty-action`) |
| rỗng/null | `false` | `false` | **content** | slot `#toolbar` + slot mặc định + slot `#pagination` |

*Vì sao `error` đứng trước `loading`:* bất biến chính của vòng 3 là **“có lỗi thì người dùng LUÔN nhìn thấy lỗi”**. Đổi lại, mọi hàm nạp **bắt buộc** xoá lỗi ở đầu lượt (INV-UX3-4) để lần bấm «Thử lại» hiện ngay khung xương chứ không đứng im — nếu không, nút thử lại **trông như chết** (đúng lỗi đang phải sửa ở `/procurement-plans`).

*Vì sao không “giữ dữ liệu cũ khi nạp lại hỏng”:* danh sách đang xem là ảnh chụp của **bộ lọc cũ**; hiện bảng cũ dưới một banner lỗi khiến người dùng tin bộ lọc mới đã áp. Quy tắc: **hỏng ⇒ dọn `rows`/`total` về 0** (INV-UX3-5) rồi hiện lỗi.

### 2.2 Cái gì hiện ở trạng thái nào

| Vùng | loading | error | empty | content |
|---|---|---|---|---|
| `#header` (PageHeader + nút hành động) | ✅ | ✅ | ✅ | ✅ |
| `#summary` (dải KPI) | — | **—** | ✅ | ✅ |
| `#filters` (ListFilterBar / thanh lọc) | ✅ | **✅ (bắt buộc — A6)** | ✅ | ✅ |
| `#skeleton` | ✅ | — | — | — |
| `ErrorState` | — | ✅ | — | — |
| `EmptyState` + `#empty-action` | — | **—** | ✅ | — |
| `#toolbar` (dòng «Hiển thị N/M») | — | — | — | ✅ |
| slot mặc định (bảng/thẻ) + `#pagination` | — | — | — | ✅ |

> Dải KPI **ẩn khi lỗi** vì số 0 tính từ tập rỗng là **tín hiệu giả** thứ hai (cùng lớp bug với false-empty).
> `#toolbar` chỉ hiện ở `content` vì «Hiển thị 0 / 0» khi đang lỗi cũng là tín hiệu giả.

---

## §3. Hợp đồng API — `frontend/src/components/ui/ListPageShell.vue`

Kế thừa **toàn bộ** luật chung `01 §3.0` (no-fork · dumb · map tĩnh · `data-testid` tiền tố `ui-*`/`list-*` · copy VI khai trong `withDefaults` · fallthrough bật · barrel).

### 3.1 Props

| Prop | Kiểu | Mặc định | Ghi chú |
|---|---|---|---|
| `loading` | `boolean` | `false` | đang nạp |
| `errorMessage` | `string \| null` | `null` | **có chuỗi (sau `trim`) ⇒ trạng thái lỗi**; truyền thẳng vào `ErrorState.message` |
| `isEmpty` | `boolean` | `false` | nạp xong, 0 bản ghi (view tự tính `!rows.length`) |
| `emptyTitle` | `string` | `'Chưa có dữ liệu'` | → `EmptyState.title` |
| `emptyHint` | `string` | `undefined` | → `EmptyState.description` |
| `errorHint` | `string` | `undefined` | → `ErrorState.hint`; bỏ trống ⇒ dùng mặc định VI của `ErrorState` |

> ⚠️ **Mọi prop PHẢI được khai** (`defineProps`). Prop không khai sẽ rơi vào `$attrs` và **in thẳng ra DOM**
> (`empty-title="Chưa có đơn hàng nào"` nằm trên thẻ gốc ở **cả 4 trạng thái**) ⇒ vỡ A3 ngay.
>
> ⚠️ **Không khai `retryLabel`.** Nhãn nút thử lại là SSoT của `ErrorState` (`'Thử lại'`, khoá bởi `01 §5`).

### 3.2 Emits

| Emit | Khi nào |
|---|---|
| `retry` | người dùng bấm nút «Thử lại» của `ErrorState` (shell chỉ chuyển tiếp, **không** tự gọi gì) |

### 3.3 Slots

| Slot | Hiện ở trạng thái | Nội dung điển hình |
|---|---|---|
| `header` | mọi | `<PageHeader>` + `#actions` (nút Tạo/Import/Xuất) |
| `summary` | `empty`, `content` | dải `KpiCard` |
| `filters` | **mọi** | `<ListFilterBar>` hoặc thanh lọc sẵn có của màn |
| `skeleton` | `loading` | `<SkeletonLoader variant="table" :rows="6" />` — **mặc định** của shell là `<Skeleton :lines="6" />` |
| `empty-action` | `empty` | nút «Xoá bộ lọc…» / «+ Tạo … đầu tiên» (chuyển tiếp vào `EmptyState #action`) |
| `toolbar` | `content` | dòng «Hiển thị N / M …» + nút «Xóa tất cả» |
| *(mặc định)* | `content` | bảng desktop + `mobile-card-list` |
| `pagination` | `content` | pager sẵn có của màn **hoặc** `<BasePagination>` (render **bên trong** thẻ `.card`, giữ nguyên đường viền trên) |

### 3.4 Khuôn template (cài đúng như dưới — đây là hợp đồng, không phải gợi ý)

```vue
<template>
  <div class="page-container animate-fade-in" :data-state="state" data-testid="list-page-shell">
    <slot name="header" />

    <div v-if="state === 'empty' || state === 'content'" data-testid="list-summary">
      <slot name="summary" />
    </div>

    <div data-testid="list-filters"><slot name="filters" /></div>

    <div v-if="state === 'loading'" class="card p-6" data-testid="list-loading">
      <slot name="skeleton"><Skeleton :lines="6" /></slot>
    </div>

    <ErrorState
      v-else-if="state === 'error'"
      :message="errorMessage ?? undefined"
      :hint="errorHint"
      @retry="emit('retry')" />

    <EmptyState
      v-else-if="state === 'empty'"
      :title="emptyTitle"
      :description="emptyHint">
      <template #action><slot name="empty-action" /></template>
    </EmptyState>

    <div v-else class="card overflow-hidden" data-testid="list-content">
      <slot name="toolbar" />
      <slot />
      <slot name="pagination" />
    </div>
  </div>
</template>
```

Ràng buộc cấu trúc:
- Thẻ gốc **duy nhất** ⇒ fallthrough attrs hoạt động; `data-state` là **hợp đồng chấm A3** (`wrapper.attributes('data-state')`).
- 4 nhánh body nối bằng **một chuỗi** `v-if / v-else-if / v-else` ⇒ loại trừ **bằng cấu trúc**, không thể cùng tồn tại.
- Chỉ import từ `./` (`Skeleton.vue`, `EmptyState.vue`, `ErrorState.vue`) — **cấm** import `vue-router`, `@/stores/*`, `@/api/*`, `@/components/common/*`.
  *(Lý do cứng, không phải khẩu hiệu:* `ProcurementPlanCreate.test.ts:40` mock `vue-router` **chỉ** với `useRouter`; shell import `RouterLink` sẽ làm bộ test đó nổ. Import `common/SkeletonLoader` thì tạo vòng phụ thuộc ngược tầng 0 → tầng 1, vì `SkeletonLoader.vue` đã render qua `ui/Skeleton`.)
- Chỉ dùng class `@layer` (`page-container`, `card`) + utility **phi màu** (`p-6`, `overflow-hidden`). 0 class palette thô.

### 3.5 Barrel `index.ts` — thứ tự BẮT BUỘC

Guard `uiPrimitiveHygiene.test.ts` so `readdirSync().sort()` với `EXPECTED_PRIMITIVES` **theo thứ tự**. Alphabet đặt `ListPageShell` **trước** `Skeleton`:

```ts
export { default as Badge } from './Badge.vue'
export { default as Button } from './Button.vue'
export { default as Card } from './Card.vue'
export { default as DataTable } from './DataTable.vue'
export { default as EmptyState } from './EmptyState.vue'
export { default as ErrorState } from './ErrorState.vue'
export { default as ListPageShell } from './ListPageShell.vue'
export { default as Skeleton } from './Skeleton.vue'
```

Sửa guard: `EXPECTED_PRIMITIVES` thêm `'ListPageShell'` **đúng vị trí thứ 7**; 3 bất biến còn lại (`INV-UI-1/3/4`) giữ nguyên — số 7 trong `toHaveLength(EXPECTED_PRIMITIVES.length + 1)` là **suy ra**, không hardcode.

---

## §4. Áp cho 4 màn thật — delta bắt buộc từng file

### 4.0 Khuôn chung của phần `<script setup>`

```ts
const errorMessage = ref<string | null>(null)

async function load() {
  loading.value = true
  errorMessage.value = null            // INV-UX3-4 — xoá lỗi ĐẦU lượt
  try {
    const res = await <hàm nạp sẵn có>(…)
    rows.value = res…; total.value = res…
  } catch (e: unknown) {
    errorMessage.value = e instanceof Error ? e.message : String(e)
    rows.value = []; total.value = 0   // INV-UX3-5 — không giữ số cũ dưới banner lỗi
  } finally {
    loading.value = false              // INV-UX3-3 — luôn hạ cờ
  }
}
```

Và phần `<template>` (2 dòng chữ rỗng **phải là literal tĩnh, cạnh nhau** — xem bẫy §7.2):

```vue
<ListPageShell
  :loading="loading"
  :error-message="errorMessage"
  :is-empty="!rows.length"
  empty-title="Chưa có … nào"
  empty-hint="Hãy … hoặc xoá bộ lọc để xem tất cả."
  @retry="load">
```

### 4.1 `/purchases` — `views/purchase/PurchaseListView.vue`

| Việc | Chi tiết |
|---|---|
| script | thêm `errorMessage`; `load()` `:80-92` thêm `catch` theo §4.0 |
| header | `<PageHeader>` `:105-118` **nguyên vẹn** vào `#header` |
| filters | `<ListFilterBar>` `:120-145` vào `#filters` |
| toolbar | dòng info `:148-152` vào `#toolbar` |
| loading | `<SkeletonLoader variant="table" :rows="6" />` `:155` vào `#skeleton` |
| empty | **XOÁ** khối `:157-162`; thay bằng `empty-title="Chưa có đơn hàng nào"` + `empty-hint="Hãy tạo đơn hàng mới hoặc xoá bộ lọc để xem tất cả."` + `#empty-action` giữ nút «Xóa bộ lọc để xem tất cả» (`v-if="activeFilterCount > 0"`) |
| content | `mobile-card-list` `:166-186` + `<table>` `:189-237` vào slot mặc định |
| pagination | khối `:240-247` vào `#pagination` (giữ nguyên `border-t`) |

> 🔒 **Không được phá:** dòng chứa `router.push('/purchases/new')` `:111` phải **giữ `v-if="can('purchase.create')"` trong cùng cửa sổ ±8 dòng** — `src/router/createButtonAffordance.test.ts:35` quét tĩnh file này.

### 4.2 `/user-profiles` — `views/auth/UserProfileListView.vue`

| Việc | Chi tiết |
|---|---|
| script | `load()` `:92-107` viết lại theo §4.0 (đang **0** `try/catch`) |
| script | `onMounted` `:113-117`: bọc riêng `getAvailableImmRoles()` trong `try/catch` — **hỏng danh sách vai trò không được chặn** lượt nạp danh sách người dùng (`availableRoles.value = []` rồi vẫn `await load()`) |
| empty | **XOÁ** khối `:233-235` (gồm chuỗi «Không có dữ liệu.»); `empty-title="Chưa có người dùng nào"` + `empty-hint="Hãy đổi bộ lọc hoặc thêm người dùng mới."`; `#empty-action` = nút «Xóa bộ lọc để xem tất cả» khi `activeFilterCount > 0` |
| loading | `:230-232` (`<SkeletonLoader v-for="i in 5">`) vào `#skeleton` — giữ nguyên 5 khối |
| **A11 — nhãn VI** | `:164` text node «Import» → **«Nhập từ Excel»**; `:329` `title="Import Người dùng"` → **`title="Nhập người dùng từ Excel"`**. Sau sửa: `viLeaks()` của bộ dò trả `[]` ⇒ cột *Nhãn VI* ✅ |
| pagination | `:320-326` vào `#pagination` |

> Bộ dò bắt **cả hai** chỗ (`>Import<` và `title="Import …"`) qua cùng khoá `Import` — sửa thiếu 1 chỗ là cột VI vẫn ❌.

### 4.3 `/vendor-profiles` — `views/procurement/VendorProfileListView.vue`

| Việc | Chi tiết |
|---|---|
| script | đổi tên `error` → `errorMessage` (hoặc giữ tên, miễn truyền đúng prop); `load()` `:21-38` thêm `items.value = []; total.value = 0` trong `catch` |
| script | thêm `resetFilters()` (đặt 4 khoá của `filters` `:14-19` về mặc định rồi `load()`) — phục vụ `#empty-action` |
| error | **XOÁ** banner `.alert-error` `:88-90` (đã có `ErrorState`; giữ lại ⇒ 2 bề mặt lỗi) |
| filters | thanh lọc `:69-86` vào `#filters` **nguyên trạng** (màn này **không** dùng `ListFilterBar` — xem §5 INV-UX3-8) |
| loading | thay `<div>Đang tải...</div>` `:93` bằng `<SkeletonLoader variant="table" :rows="6" />` trong `#skeleton` |
| empty | **XOÁ** khối chết `:116-118` và khối `:167-169`; `empty-title="Chưa có nhà cung cấp nào"` + `empty-hint="Hãy xoá bộ lọc để xem tất cả nhà cung cấp."`; `#empty-action` = nút «Xóa bộ lọc để xem tất cả» → `resetFilters()` |
| content | `mobile-card-list` `:96-119` + bảng `:122-165` vào slot mặc định |
| pagination | **không có** — bỏ trống slot (Never §0: không thêm phân trang mới) |

### 4.4 `/procurement-plans` — `views/needs/ProcurementPlanListView.vue`

| Việc | Chi tiết |
|---|---|
| script | thêm `const listLoading = ref(false)` — **bắt buộc**, vì `store.loading` không bao giờ bật cho lượt nạp kế hoạch (`AC-UX-044`) |
| script | thêm `async function loadPlans() { listLoading.value = true; store.clearError(); try { await store.fetchPlans(buildPayload()) } finally { listLoading.value = false } }` |
| script | `onMounted` `:146`, `applyFilters` `:127`, `resetFilters` `:128-134`, `clearChip` `:135-139`, `quickFilter` `:140-144` → gọi `loadPlans()` (thay `store.fetchPlans(...)`) |
| script | `submitCreate` `:61-81` **giữ nguyên** (`store.fetchPlans()` rồi `router.push`) — giảm diện tích thay đổi |
| shell | `:loading="listLoading"` · `:error-message="store.error"` · `:is-empty="!store.plans.length"` · `@retry="loadPlans"` |
| error | **XOÁ** banner `:199-202` (gồm nút `×` `store.clearError()` — chính là “nút giả dạng thử lại” của A5) |
| summary | dải KPI `:158-172` vào `#summary` |
| loading | thay `<div>Đang tải...</div>` `:213` bằng `<SkeletonLoader variant="table" :rows="6" />` trong `#skeleton` |
| empty | **XOÁ** khối chết `:233-235` và khối `:297-309`; `empty-title="Chưa có kế hoạch mua sắm nào"` + `empty-hint="Hãy tạo kế hoạch từ đề xuất đã duyệt, hoặc xoá bộ lọc để xem tất cả."`; `#empty-action` giữ **nguyên 2 nút** («Xóa bộ lọc để xem tất cả» khi có bộ lọc · «+ Tạo kế hoạch đầu tiên» khi `canCreatePlan`) |
| modal | khối `:313-377` **giữ nguyên, nằm NGOÀI** `ListPageShell` (template nhiều gốc) |

> 🔒 **Không được phá:** `src/views/needs/ProcurementPlanCreate.test.ts` mở modal bằng cách tìm **nút có chữ «Tạo kế hoạch» trong body** (`PageHeader` bị stub nên nút ở header không render) với `fakeStore = { plans: [], loading: false, error: null }`. Trạng thái phải rơi vào **empty** và nút «+ Tạo kế hoạch đầu tiên» phải **render thật** trong `#empty-action`.
> `src/components/common/currencyInputRollout.test.ts:27` quét `CurrencyInput` cho `createForm.budget_envelope` — nằm trong modal, không đụng.

---

## §5. Bất biến đo được (INV-UX3-*)

| Mã | Bất biến | Cách chứng minh |
|---|---|---|
| **INV-UX3-1** | 4 trạng thái **loại trừ**: `data-state` ∈ {loading,error,empty,content} và **đúng 1** trong 4 vùng body tồn tại | đếm `[data-testid=list-loading] + ui-error + ui-empty + list-content` == 1 ở cả 4 trạng thái |
| **INV-UX3-2** | **Lỗi thắng rỗng**: `state='error'` ⇒ `queryByTestId('ui-empty') === null` **và** DOM **không** chứa: «Chưa có đơn hàng nào» · «Không có dữ liệu.» · «Không có dữ liệu» · «Không có kế hoạch nào phù hợp» · «Chưa có nhà cung cấp nào.» | 4 test render (A3) |
| **INV-UX3-3** | `loading` luôn hạ trong `finally` ⇒ **không** có trạng thái “xương vĩnh viễn” | test: API ném ⇒ sau `flushPromises`, `data-state === 'error'` (không phải `loading`) |
| **INV-UX3-4** | Hàm nạp xoá lỗi ở **đầu** lượt | test: sau khi bấm «Thử lại» và lượt 2 thành công ⇒ `data-state === 'content'`, `ui-error` biến mất |
| **INV-UX3-5** | Hỏng ⇒ `rows`/`total` về 0 (không giữ số cũ) | test: lượt 1 OK (n bản ghi) → lượt 2 hỏng ⇒ 0 hàng dữ liệu trong DOM |
| **INV-UX3-6** | **Đúng 1** control có tên máy-đọc «Thử lại» ở trạng thái lỗi | `getAllByRole('button', { name: 'Thử lại' })` (hoặc `findAll('button').filter(text==='Thử lại')`) length **== 1** |
| **INV-UX3-7** | «Thử lại» **gọi lại hàm nạp** | spy nạp (`listPurchases` / `listUsers` / `listVendorProfiles` / `store.fetchPlans`) `toHaveBeenCalledTimes(2)` |
| **INV-UX3-8** | **Bộ lọc sống ở mọi trạng thái**: `[data-testid=list-filters]` tồn tại ở cả 4 trạng thái; 3 màn có `ListFilterBar` thì component đó còn trong DOM khi `state='error'`; `/vendor-profiles` (không có `ListFilterBar`) chấm bằng ô `select` trạng thái duyệt còn trong DOM | A6 |
| **INV-UX3-9** | Copy nút thử lại là SSoT `ErrorState` — `ListPageShell.vue` **0 hit** chuỗi `'Thử lại'` | `grep -c 'Thử lại' frontend/src/components/ui/ListPageShell.vue` → 0 |
| **INV-UX3-10** | Shell là **dumb**: `ListPageShell.vue` **0 hit** `vue-router` / `@/stores` / `@/api` / `@/components/common` | grep |

---

## §6. Test-case & lệnh chấm

### 6.1 `frontend/src/components/ui/ListPageShell.test.ts` (mount THẬT, ≥8 case)

| TC | Nội dung |
|---|---|
| TC-UX3-01 | `loading=true` ⇒ `data-state='loading'`, có `list-loading`, **0** `ui-error` / `ui-empty` / `list-content` |
| TC-UX3-02 | `errorMessage='X'` ⇒ `data-state='error'`, `ui-error` hiện, `ui-empty` **null** (kể cả khi `isEmpty=true`) — **bất biến chính** |
| TC-UX3-03 | `errorMessage='X'` + `loading=true` ⇒ vẫn `error` (ưu tiên §2.1) |
| TC-UX3-04 | `isEmpty=true` ⇒ `ui-empty` + `emptyTitle`/`emptyHint` render; slot `#empty-action` render |
| TC-UX3-05 | mặc định ⇒ `data-state='content'`, slot mặc định + `#toolbar` + `#pagination` render |
| TC-UX3-06 | bấm `ui-error-retry` ⇒ phát **đúng 1** sự kiện `retry` |
| TC-UX3-07 | `#filters` render ở **cả 4** trạng thái; `#summary` render ở `empty`+`content` và **không** render ở `loading`+`error` |
| TC-UX3-08 | `emptyTitle` **không** rò ra DOM khi `state='error'` (chống bẫy prop-không-khai §7.1) |
| TC-UX3-09 | ở `state='error'` có **đúng 1** nút tên «Thử lại» |

### 6.2 4 test màn (mỗi màn ≥4 case) — mount view thật, mock lớp API/store

| File test | Spy nạp |
|---|---|
| `frontend/src/views/purchase/purchaseListStates.test.ts` | `@/api/purchase` → `listPurchases` |
| `frontend/src/views/auth/userProfileListStates.test.ts` | `@/api/user` → `listUsers`, `getAvailableImmRoles` |
| `frontend/src/views/procurement/vendorProfileListStates.test.ts` | `@/api/imm03` → `listVendorProfiles` |
| `frontend/src/views/needs/procurementPlanListStates.test.ts` | mock `@/stores/imm01` (khuôn `ProcurementPlanCreate.test.ts:25-32`) → `fetchPlans` |

Mỗi file chấm 4 case:
1. **lỗi ⇒ không rỗng**: nạp ném/`error` ⇒ `data-state='error'`, `ui-empty` null, DOM **không** chứa chuỗi rỗng cũ của màn đó (A3).
2. **đúng 1 «Thử lại»** ở trạng thái lỗi (A3).
3. **thử lại gọi lại hàm nạp**: bấm ⇒ spy `toHaveBeenCalledTimes(2)`; lượt 2 OK ⇒ `data-state='content'` (A5 + INV-UX3-4).
4. **bộ lọc sống khi lỗi**: `list-filters` tồn tại; `ListFilterBar` (3 màn) / ô `select` (`/vendor-profiles`) còn trong DOM (A6).

### 6.3 Lệnh chấm (QA **tự đo lại**, không tin ảnh chụp đầu vòng)

```bash
cd frontend
# A1
grep -c "^export { default as" src/components/ui/index.ts            # → 8
ls src/components/ui/*.vue | wc -l                                    # → 8
ls src/components/ui/*.test.ts | wc -l                                # → 9  (8 + hygiene guard)
npx vitest run src/components/ui/uiPrimitiveHygiene.test.ts           # → đọc dòng "Tests N passed" bằng MẮT
# A2
grep -l ListPageShell src/views/purchase/PurchaseListView.vue src/views/auth/UserProfileListView.vue \
  src/views/procurement/VendorProfileListView.vue src/views/needs/ProcurementPlanListView.vue | wc -l   # → 4
# A3 / A5 / A6
npx vitest run src/components/ui/ListPageShell.test.ts \
  src/views/purchase/purchaseListStates.test.ts src/views/auth/userProfileListStates.test.ts \
  src/views/procurement/vendorProfileListStates.test.ts src/views/needs/procurementPlanListStates.test.ts
# A4
grep -cE 'error|catch' src/views/auth/UserProfileListView.vue         # > 0 (baseline 0)
# A7  — chấm DELTA cột «Lỗi+Thử lại»
node scripts/ui-audit-inventory.mjs | awk -F'|' 'NR>1{gsub(/ /,"",$8); if($8=="❌") e++} END{print e}'   # 94 → 90
# A11
node -e "…viLeaks…" || grep -nE '>[^<]*\bImport\b|title="[^"]*Import' src/views/auth/UserProfileListView.vue   # → 0 hit
# A8 / A9 / A12
npx vitest run            # 0 file đỏ; 299 (baseline đo lại) + 5
npx vue-tsc --noEmit
npx vitest run src/router/uiAuditDocParity.test.ts    # 15/15
npx vitest run src/design/tokens.parity.test.ts
# A10
git status --short --untracked-files=all | grep -c '\.py$'                       # → 0
git status --short -uall | grep -cE '^.. frontend/src/(stores|api)/'             # → 0
```

---

## §7. Bẫy đã biết — ĐỌC TRƯỚC KHI CODE

### 7.1 Prop không khai ⇒ chữ rỗng rò ra DOM ở **mọi** trạng thái
Vue đưa attribute không khớp prop nào vào `$attrs` và **merge vào thẻ gốc**. Nếu quên khai `emptyTitle`,
`empty-title="Chưa có đơn hàng nào"` sẽ nằm trên `<div data-testid="list-page-shell">` kể cả khi đang lỗi ⇒
`html()` chứa chuỗi rỗng ⇒ **A3 đỏ**, và không ai hiểu vì sao.

### 7.2 Chữ rỗng phải là **literal tĩnh trong template của VIEW**, cạnh một từ hướng dẫn
Bộ dò `ui-audit-inventory.mjs:167-179` tìm cụm rỗng **trong template** rồi soi cửa sổ **±12 dòng** để tìm
`<button>` / `<router-link>` / từ hướng dẫn (`Hãy|Bấm|Nhấn|Tạo |Thử |Xoá bộ lọc|Xóa bộ lọc|Chọn |Đổi bộ lọc|đợi`).
⇒ **Cấm** đưa chữ rỗng vào `computed` (`:empty-title="emptyLabel"`) — cột *Rỗng+HD* của `/purchases`,
`/user-profiles`, `/procurement-plans` đang ✅ sẽ **lật thành ❌** và vi phạm A7. Đặt `empty-title` và
`empty-hint` **liền nhau** trên thẻ `<ListPageShell>` là cách an toàn nhất (không phụ thuộc vị trí slot).

### 7.3 Cột «Lỗi+Thử lại» chỉ ✅ khi có `@retry` **trong template của view**
`hasRetry` (`ui-audit-inventory.mjs:183-187`) khớp `@retry\b` · `<DetailLoadError` · `<RouteErrorBoundary` ·
hoặc chữ «Thử lại» + `@click`. Viết `@retry="load"` trên `<ListPageShell>` là đủ và **cũng** kích hoạt
hợp thành 1 cấp (`delegatedChildren` `:102-115` nhận `:loading` / `:error…` / `@retry`).

### 7.4 Cột *Skeleton* chỉ ✅ khi thấy `<SkeletonLoader` / `animate-pulse` / `class="…skeleton…"`
`<Skeleton />` (primitive) **không** khớp. ⇒ cả 4 màn truyền `<SkeletonLoader …>` vào `#skeleton`
(2 màn đang có sẵn — giữ nguyên; 2 màn `/procurement-plans`, `/vendor-profiles` được thêm ⇒ ✅ mới).

### 7.5 Thứ tự barrel & guard vệ sinh
`vueFiles` là `readdirSync().sort()`; `expect(vueFiles).toEqual(EXPECTED_PRIMITIVES.map(n => n + '.vue'))`
⇒ `ListPageShell` phải nằm **giữa `ErrorState` và `Skeleton`** trong cả mảng lẫn `index.ts`.

### 7.6 `ListPageShell.vue` chịu **toàn bộ** guard vệ sinh tầng 0
`INV-UI-1` (0 palette thô) · `INV-UI-3` (0 chuỗi hiển thị EN; allowlist text node hiện là **`{'Thử lại'}`** ⇒
shell **không được** có text node nào — chỉ component + slot) · `INV-UI-4` (chỉ bậc {50,500,700}).

### 7.7 Hai bộ test cũ đang khoá 4 màn đích
`createButtonAffordance.test.ts:35` (quét tĩnh `PurchaseListView.vue`) · `ProcurementPlanCreate.test.ts`
(mount thật, mở modal qua nút empty-state) · `currencyInputRollout.test.ts:27`. Xem 🔒 ở §4.1 và §4.4.

---

## §8. Danh mục file được phép chạm — vòng 3 (A10)

**Thêm mới (6):**
```
frontend/src/components/ui/ListPageShell.vue
frontend/src/components/ui/ListPageShell.test.ts
frontend/src/views/purchase/purchaseListStates.test.ts
frontend/src/views/auth/userProfileListStates.test.ts
frontend/src/views/procurement/vendorProfileListStates.test.ts
frontend/src/views/needs/procurementPlanListStates.test.ts
```
**Sửa (6):**
```
frontend/src/components/ui/index.ts                          (§3.5 — thêm 1 dòng export, đúng vị trí)
frontend/src/components/ui/uiPrimitiveHygiene.test.ts        (§3.5 — thêm 'ListPageShell' vào EXPECTED_PRIMITIVES)
frontend/src/views/purchase/PurchaseListView.vue             (§4.1)
frontend/src/views/auth/UserProfileListView.vue              (§4.2 + A11)
frontend/src/views/procurement/VendorProfileListView.vue     (§4.3)
frontend/src/views/needs/ProcurementPlanListView.vue         (§4.4)
```
**Doc (BA đã land trước khi code):** `docs/ui-ux/02_LIST_PAGE_SHELL.md` (file này) · `docs/ui-ux/00_AUDIT_HIEN_TRANG.md` (§Tài-liệu-liên-quan, §2.1 chú thích, §3.3 chú thích, §6 sổ `AC-UX-041…047`, §7.2 chú thích, §9 **ADR-UX-05**, §10 ghim).

**Ngoài danh mục trên: 0 file.** `git status --short -uall` phải cho **0** `.py`, **0** `frontend/src/stores/**`, **0** `frontend/src/api/**`.

---

## §9. Truy vết Acceptance A1–A12 ⇄ spec ⇄ lệnh đo

| AC | Mục spec | Chấm bằng |
|---|---|---|
| A1 | §3.1–3.5 | `ls ui/*.vue` → 8 · `index.ts` 8 export · guard hygiene XANH (đọc dòng `Tests N passed` bằng mắt) |
| A2 | §4.1–4.4 | `grep -l ListPageShell <4 file> \| wc -l` → 4; slot `#header`/`#filters`/`#pagination` chứa **markup cũ**, 0 component header/filter/pager mới |
| A3 | §2.1, §5 INV-UX3-2/6, §6.2 case 1–2 | 4 file test XANH |
| A4 | §1.1 | `grep -cE 'error\|catch' UserProfileListView.vue` > 0 · `/purchases` có nhánh lỗi riêng · 0 chuỗi rỗng trong nhánh lỗi |
| A5 | §5 INV-UX3-7, §6.2 case 3 | spy `toHaveBeenCalledTimes(2)` × 4 màn |
| A6 | §2.2, §5 INV-UX3-8, §6.2 case 4 | `list-filters` + `ListFilterBar`/`select` còn trong DOM khi lỗi |
| A7 | §1.3 | `node scripts/ui-audit-inventory.mjs` TRƯỚC/SAU; cột *Lỗi+Thử lại* **−4**; 0 ô ✅ → ❌ |
| A8 | §8 | `npx vitest run` 0 file đỏ; baseline đo lại (**299** trên đĩa hôm nay) **+5** |
| A9 | §8 | `npx vue-tsc --noEmit` 0 lỗi; ESLint 0 lỗi trên file mới/sửa |
| A10 | §8 | 2 lệnh `git status` ở §6.3 → 0 / 0 |
| A11 | §4.2 | 0 hit `Import` ở lớp hiển thị của `UserProfileListView.vue`; `AC-UX-029` hạ còn 3 route (00 §6) |
| A12 | §8 (doc) | `npx vitest run src/router/uiAuditDocParity.test.ts` → 15/15 · `src/design/tokens.parity.test.ts` XANH |

---

## §10. Rủi ro & việc để lại vòng 4

| # | Rủi ro / nợ | Xử lý |
|---|---|---|
| 1 | 90 route còn ❌ cột «Lỗi+Thử lại» sau vòng 3 | `AC-UX-047` — adoption diện rộng, chia lô theo module (vòng 4–5) |
| 2 | `stores/imm01.ts::fetchPlans` vẫn không set `loading`, không clear `error` | `AC-UX-044` (vòng 4, đụng `stores/` — ngoài Boundaries vòng 3) |
| 3 | Ưu tiên `error > loading` phụ thuộc **kỷ luật xoá lỗi đầu lượt** ở view | INV-UX3-4 + TC case 3; adoption vòng 4 nên đóng gói thành composable `useListLoad()` (**Ask first**) |
| 4 | 4 màn đích vẫn ❌ cột a11y; `/purchases`, `/procurement-plans` vẫn ❌ ≤768px | thuộc `AC-UX-006` / `AC-UX-007` — bọc `DataTable` + `FormField` ở vòng 3–4 (`AC-UX-038/039`) |
| 5 | `#pagination` của 2 màn vẫn là pager tự viết, không phải `BasePagination` | vòng 4, cùng lượt chuẩn hoá `PaginationMeta` |
| 6 | Lỗi 403/404 hiện dùng **chung** khuôn `ErrorState` (không phân biệt như `DetailLoadError`) | nếu cần phân biệt cho danh sách → ADR mới; vòng 3 giữ 1 khuôn |

---

## §11. Quyết định kiến trúc

Xem **ADR-UX-05** (bản gốc) ở [`00_AUDIT_HIEN_TRANG.md §9`](./00_AUDIT_HIEN_TRANG.md#9-quyết-định-kiến-trúc) — *“`ListPageShell` là primitive #8; 4 trạng thái loại trừ với ưu tiên `error > loading > empty > content`”*.

---

## §12. LÔ 1 adoption `ListPageShell` — 12 route (`AC-UX-047`, đo 2026-08-03)

| Mục | Giá trị |
|---|---|
| Đề mục | `AC-UX-047` **lô 1** — KHÔNG cấp số sổ mới (sổ AC-UX đóng băng ở **058**) |
| Phạm vi | **đúng 12** màn DANH SÁCH thuộc IMM-00/02/03/05/07/09/10/12/14/16 + master-data |
| Loại | Core Doc cross-cutting (UI/UX) — spec thi hành cho FE dev, **spec-before-code gate** |
| Ngày đo | **2026-08-03** — mọi số dưới đây đo TỪ ĐĨA hôm nay, KHÔNG kế thừa số trong prompt/STATE |
| Nhánh | `feature/hieuc/core-refinement` |
| Tài liệu cha | §0–§11 của chính tài liệu này (khuôn + hợp đồng API `ListPageShell` đã chốt vòng 3) |
| Trạng thái | **Chốt để code** |

> **Vì sao lô 1 là 12 màn này.** Cả 12 route đều nằm nhóm «Danh sách», **đợt B** trong `04 §11`
> (dòng 16/20/23/33/40/48/57/60/75/85/87/90), đều `Lỗi+Thử lại = ❌` ở CẢ bảng tay `00 §3.1`
> LẪN bộ dò, và **cả 12 file view có 0 hit** `grep -cE "ErrorState|errorMessage|Thử lại|retry"`.
> Tức: hôm nay API hỏng ở 12 màn này ⇒ người dùng thấy câu «Chưa có …» và **không có đường thử lại** —
> đúng class-of-bug *false-empty* mà vòng 3 dựng khuôn để diệt.

### 12.1 Số đo TỪ ĐĨA hôm nay (baseline chấm DELTA) — có DRIFT so với prompt

| Đại lượng | Lệnh | **Đĩa 2026-08-03** | Prompt/STATE | Kết luận |
|---|---|---|---|---|
| Màn đã dùng shell | `grep -rl "ui/ListPageShell" frontend/src/views --include=*.vue \| wc -l` | **4** | 4 | khớp |
| `*ListView.vue` có **0** token lỗi/thử-lại | vòng lặp `grep -cE "ErrorState\|errorMessage\|Thử lại\|retry"` | **24** | 23 | **prompt stale +1** |
| File `*ListStates.test.ts` | `find frontend/src/views -name "*ListStates.test.ts"` | **4** | 4 | khớp |
| `TC-UX3-*` lớn nhất | `grep -rhoE "TC-UX3-[0-9]+" docs frontend/src \| sort -u \| tail -1` | **TC-UX3-10** | 10 | khớp |
| Sổ `AC-UX` lớn nhất / tổng | `grep -rhoE "AC-UX-[0-9]{3}" docs frontend/src \| sort -u` | **058 / 58 mục** | 058 | khớp — **CẤM cấp số mới** |
| Bộ dò: cột *Lỗi+Thử lại* ❌ | `node frontend/scripts/ui-audit-inventory.mjs` (đếm cột 7) | **89** | 90 | **prompt stale −1** |
| `INV-UX3-*` lớn nhất | grep | **INV-UX3-10** | — | lô 1 dùng tiếp **11…17** |
| `ADR-UX-*` lớn nhất | grep | **ADR-UX-10** | — | lô 1 dùng **ADR-UX-11** |
| Suite FE trước bước BA | `npx vitest run` | **314 file / 3122 test** | 314/3122 | khớp |
| Suite FE **sau bước BA** (đã cộng guard mới) | `npx vitest run` | **315 file / 3133 test — 0 đỏ** | — | mốc chấm delta của FE |

**Chốt BA (ràng buộc nghiệm thu, thay số trong prompt):**
- Nợ còn lại sau lô 1 = **89 − 12 = 77** (KHÔNG phải 78). Prompt viết «90 → 78» dựa trên **dự đoán vòng 3**
  (`02 §1.3`: «94 → 90»); đĩa hôm nay đã là **89**. Luật đã chốt: *baseline trong prompt/STATE luôn có thể stale
  ⇒ chấm DELTA, đo từ đĩa* ⇒ **DELTA phải đúng −12**, con số tuyệt đối là **89 → 77**.
- Nợ nhóm «Danh sách» ở `04 §10.1` = **24 → 12** sau lô 1.
- Số `*ListView.vue` có 0 token lỗi: **24 → 12** (12 màn lô 1 rời khỏi tập này).

### 12.2 Sổ lô 1 — 12 route (SSoT; guard `uiListShellLot1Parity.test.ts` đọc chính bảng này)

| # | Route | View file | Hàm nạp | Nguồn lỗi sau sửa | Module cần `vi.mock` | TC |
|---|---|---|---|---|---|---|
| 1 | `/stock-movements` | `frontend/src/views/inventory/StockMovementListView.vue` | `load()` `:73` | `loadError` (ref MỚI) | `@/api/inventory` → `listStockMovements` | `TC-UX3-11` |
| 2 | `/asset-transfers` | `frontend/src/views/asset/AssetTransferListView.vue` | `load()` `:99` | `loadError` (ref MỚI) | `@/api/helpers` → `frappeGet` + `frappePost` | `TC-UX3-12` |
| 3 | `/warehouses` | `frontend/src/views/inventory/WarehouseListView.vue` | `load()` `:58` | `loadError` (ref MỚI) | `@/api/inventory` → `listWarehouses`(+`create/update/delete`) | `TC-UX3-13` |
| 4 | `/device-models` | `frontend/src/views/asset/DeviceModelListView.vue` | `load()` `:68` | **`error` ĐÃ CÓ** `:21` (chỉ dùng cho nạp) | `@/api/imm00` → `listDeviceModels`(+`deleteDeviceModel`) | `TC-UX3-14` |
| 5 | `/suppliers` | `frontend/src/views/purchase/SupplierListView.vue` | `load()` `:64` | **`error` ĐÃ CÓ** `:20` (chỉ dùng cho nạp) | `@/api/imm00` → `listSuppliers`(+`deleteSupplier`) | `TC-UX3-15` |
| 6 | `/spare-parts` | `frontend/src/views/inventory/SparePartListView.vue` | `load()` `:80` | `loadError` (ref MỚI) | `@/api/inventory` → `listSpareParts`(+`createSparePart`) | `TC-UX3-16` |
| 7 | `/documents/requests` | `frontend/src/views/document/DocumentRequestListView.vue` | `load()` `:90` | `loadError` (ref MỚI — **KHÔNG** dùng `err` `:27`) | `@/api/imm00` → `listDocumentRequests`(+4 hàm CRUD) | `TC-UX3-17` |
| 8 | `/pm/templates` | `frontend/src/views/pm/PmTemplateListView.vue` | `load()` `:82` | `loadError` (ref MỚI — **KHÔNG** dùng `err` `:26`) | `@/api/imm00` → `listPmTemplates`(+CRUD+`applyPmTemplateToCategory`) | `TC-UX3-18` |
| 9 | `/cm/firmware` | `frontend/src/views/document/FirmwareCrListView.vue` | `load()` `:162` | `loadError` (ref MỚI — **KHÔNG** dùng `err` `:27`) | `@/api/imm00` → `listFirmwareCrs`(+CRUD+`getAssetActionMeta`) · `@/api/imm09` → `listRepairWorkOrders` | `TC-UX3-19` |
| 10 | `/sla-policies` | `frontend/src/views/master-data/SlaPolicyListView.vue` | `load()` `:99` | `loadError` (ref MỚI — **KHÔNG** dùng `err` `:32`) | `@/api/imm00` → `listSlaPolicies`(+CRUD) · cần Pinia (`useAcUserStore`) | `TC-UX3-20` |
| 11 | `/incidents/list` | `frontend/src/views/incident/IncidentListView.vue` | `applyFilter()` `:163` → `store.fetchList` | **`store.error`** (`stores/imm12.ts:24`, đã clear đầu lượt `:64`) | `@/api/imm12` → `listIncidents` + `getIncidentStats` · cần Pinia | `TC-UX3-21` |
| 12 | `/rca` | `frontend/src/views/incident/RCAListView.vue` | `applyFilter()` `:67` → `store.fetchRcas` | **`store.rcaError`** (`stores/imm12.ts:35`, đã clear đầu lượt `:113`) | `@/api/imm12` → `listRcas` · cần Pinia | `TC-UX3-22` |

**Ba biến thể — không có biến thể thứ tư:**
- **A. ref MỚI `loadError`** (8 màn: 1,2,3,6,7,8,9,10) — view chưa có ref lỗi cho lượt nạp, hoặc có `err`/`error` nhưng **đang thuộc về việc khác** (lưu biểu mẫu / xoá bản ghi).
- **B. tái dùng `error` sẵn có** (2 màn: 4,5) — `error` chỉ được gán trong `catch` của `load()`; **xoá** banner `.alert-error` (`DeviceModelListView.vue:191`, `SupplierListView.vue:217`) rồi nối thẳng vào `:error-message`.
- **C. store** (2 màn: 11,12) — `error`/`rcaError` của `stores/imm12.ts` **đã** clear đầu lượt ⇒ **KHÔNG sửa `stores/`**; xoá banner `.alert-error` (`IncidentListView.vue:260`, `RCAListView.vue:149`).

### 12.3 Boundaries lô 1

**Always:**
- Giữ nguyên 4 trạng thái loại trừ + thứ tự ưu tiên `error > loading > empty > content` của §2 — **không** khai lại máy trạng thái trong view.
- Mỗi hàm nạp: xoá lỗi ở **đầu** lượt (`INV-UX3-4`), `catch` gán câu lỗi, `finally` hạ `loading` (`INV-UX3-3`), và **dọn dữ liệu cũ về rỗng** khi hỏng (`INV-UX3-5`).
- `@retry` phải viết **đúng dạng `@retry="…"`** (không `v-on:retry`): bộ dò `frontend/scripts/ui-audit-inventory.mjs:187` chỉ nhận `@retry` — viết kiểu khác thì mã đúng nhưng cột *Lỗi+Thử lại* **vẫn ❌** và DELTA không xuống.
- Đưa markup **đang có** vào slot; mọi chuỗi rỗng chuyển thành prop `empty-title` / `empty-hint` / slot `#empty-action`.
- Hộp thoại (`fixed inset-0`), `ImportWizardModal`, dải toast **đặt NGOÀI** 4 nhánh trạng thái (xem §12.5 `INV-UX3-17`).

**Ask first (dừng, hỏi BA/PM):**
- Áp shell cho màn **thứ 13** trở đi trong cùng vòng (đó là lô 2).
- Sửa `frontend/src/stores/**` hoặc `frontend/src/api/**` (lô 1 **không cần** — đã kiểm chứng ở §12.2 cột «Nguồn lỗi»).
- Trích `useListLoad()` composable (nợ đã ghi `02 §10` mục 3) — **không** làm trong lô 1: 12 màn cùng lúc + đổi khuôn = 2 rủi ro chồng nhau.
- Đổi pager tự viết sang `BasePagination`, hoặc đổi `data-testid` đang bị test khoá.

**Never:**
- **KHÔNG** đụng bất kỳ file `.py` nào (`git status --porcelain -- '*.py'` phải RỖNG cuối vòng).
- **KHÔNG** nối lỗi **biểu mẫu/xoá** (`err`, `toast`, `error` của `remove()`) vào `:error-message` — 1 lần lưu hỏng sẽ **xoá trắng cả danh sách** (`INV-UX3-13`).
- **KHÔNG** để 2 lối báo lỗi song song (banner `.alert-error` cũ **và** `ErrorState`) ⇒ vỡ `INV-UX3-6` (đúng 1 nút «Thử lại»).
- **KHÔNG** cấp mã sổ AC-UX mới (059 trở đi) trong vòng này — `uiAuditDocParity.test.ts:204` ép mỗi mục có «vòng xử lý ∈ {2,3,4,5}»; mục mới của vòng 6 sẽ **đỏ guard**. Sổ giữ nguyên **58 mục**.
- **KHÔNG** đổi bảng `04 §11` (135 dòng) và **KHÔNG** đổi bảng tay tổng hợp `00 §2.1` (đóng băng theo `ADR-UX-10`).
- **KHÔNG** lật ô của route NGOÀI 12 dòng lô 1 ở `00 §3.1` (kể cả 4 dòng vòng-3 đang stale — xem §12.8 ghi chú).

### 12.4 Delta bắt buộc từng file

Khuôn `<script setup>` (biến thể A/B) — giống `§4.0`, đặt tên **`loadError`** cho ref mới:

```ts
const loadError = ref<string | null>(null)

async function load() {
  loading.value = true
  loadError.value = null                 // INV-UX3-4 — xoá lỗi ĐẦU lượt
  try {
    const r = await <hàm nạp sẵn có>(…)
    rows.value = r?.items ?? []
    total.value = r?.pagination?.total ?? 0
  } catch (e: unknown) {
    loadError.value = e instanceof Error ? e.message : String(e)
    rows.value = []; total.value = 0     // INV-UX3-5
  } finally {
    loading.value = false                // INV-UX3-3
  }
}
```

Khuôn `<template>` — 6 slot, thứ tự cố định:

```vue
<ListPageShell
  :loading="loading"
  :error-message="loadError"
  :is-empty="!rows.length"
  :empty-title="emptyTitle"
  :empty-hint="emptyHint"
  @retry="load">
  <template #header> <PageHeader …/> </template>
  <template #summary> <!-- dòng «Hiển thị N / M», dải KPI --> </template>
  <template #filters> <ListFilterBar …/> </template>
  <template #skeleton> <SkeletonLoader …/> </template>
  <template #empty-action> <!-- nút «Xóa bộ lọc…» / «Tạo … đầu tiên» --> </template>
  <template #toolbar> <!-- dòng info trong khung card --> </template>
  <!-- slot mặc định: mobile-card-list + <table> -->
  <template #pagination> <!-- pager sẵn có --> </template>
</ListPageShell>
<!-- NGOÀI shell: hộp thoại / ImportWizardModal / toast -->
```

`emptyTitle` / `emptyHint` là `computed` phân biệt **có lọc** ⇄ **không lọc** (giữ đúng ngữ nghĩa hiện có):

| # | View | `empty-title` (không lọc) | `empty-title` (có lọc) | `empty-hint` | `#empty-action` |
|---|---|---|---|---|---|
| 1 | StockMovement | `Chưa có phiếu kho nào` | `Không có phiếu kho nào phù hợp` | `Hãy tạo phiếu kho mới hoặc xoá bộ lọc để xem tất cả.` | nút «Xóa bộ lọc để xem tất cả» (`activeFilterCount > 0`) · «Tạo phiếu kho đầu tiên» (`can('inventory.write')`) |
| 2 | AssetTransfer | `Chưa có lượt chuyển giao nào` | `Không có lượt chuyển giao nào phù hợp` | `Hãy tạo lượt chuyển giao mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 3 | Warehouse | `Chưa có kho nào` | `Không có kho nào phù hợp` | `Hãy tạo kho mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc…» · «Tạo kho đầu tiên» |
| 4 | DeviceModel | `Chưa có model thiết bị nào` | `Không tìm thấy model thiết bị nào phù hợp` | `Hãy thêm model mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 5 | Supplier | `Chưa có nhà cung cấp nào` | `Không có nhà cung cấp nào phù hợp` | `Hãy thêm nhà cung cấp mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 6 | SparePart | `Chưa có phụ tùng nào` | `Không có phụ tùng nào phù hợp` | `Hãy thêm phụ tùng mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc…» · «Thêm phụ tùng đầu tiên» |
| 7 | DocumentRequest | `Chưa có yêu cầu hồ sơ nào` | `Không có yêu cầu nào phù hợp` | `Hãy tạo yêu cầu hồ sơ mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 8 | PmTemplate | `Chưa có mẫu bảo trì nào` | `Không có mẫu bảo trì nào phù hợp` | `Hãy tạo mẫu bảo trì mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 9 | FirmwareCr | `Chưa có yêu cầu thay đổi phần mềm nào` | `Không có yêu cầu nào phù hợp` | `Hãy tạo yêu cầu mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 10 | SlaPolicy | `Chưa có chính sách cam kết mức dịch vụ` | `Không có chính sách nào phù hợp` | `Hãy tạo chính sách mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 11 | Incident | `Không có sự cố nào được báo cáo` | `Không có sự cố nào phù hợp` | `Hãy báo cáo sự cố mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc…» · «+ Báo cáo sự cố đầu tiên» (`can('corrective.create')`) |
| 12 | RCA | `Chưa có hồ sơ phân tích nguyên nhân gốc nào` | `Không có hồ sơ phân tích nào phù hợp` | `Phân tích nguyên nhân gốc được tạo tự động từ sự cố mức Cao/Nghiêm trọng hoặc lỗi lặp lại.` | «Xóa bộ lọc…» · «Đi tới danh sách sự cố» |

**Khối phải XOÁ (mã chết + chuỗi rỗng trùng lặp) — nếu để lại thì `INV-UX3-12` đỏ:**

| # | View | Xoá | Lý do |
|---|---|---|---|
| 1 | StockMovement | `:159-166` (nhánh rỗng) · **`:204-206`** «Không có dữ liệu» | `:204` nằm TRONG nhánh `v-else` có dữ liệu ⇒ mã chết (`AC-UX-046`) |
| 2 | AssetTransfer | `:191-196` · **`:225-227`** | như trên |
| 3 | Warehouse | `:166-172` · **`:204-206`** | như trên |
| 4 | DeviceModel | `:210-215` · banner `:191` `.alert-error` | banner thay bằng `ErrorState` |
| 5 | Supplier | `:237-241` · banner `:217` `.alert-error` | như trên |
| 6 | SparePart | `:181-187` · **`:218-220`** | mã chết |
| 7 | DocumentRequest | `:228-230` | — |
| 8 | PmTemplate | `:234-236` | — |
| 9 | FirmwareCr | `:297-299` | (giữ `err` trong hộp thoại `:393`) |
| 10 | SlaPolicy | `:234-236` | — |
| 11 | Incident | **`:312-314`** (rỗng trong nhánh mobile) · `:389-400` (rỗng desktop) · banner `:260` | 2 khối rỗng + banner song song |
| 12 | RCA | `:233-243` · banner `:149` | — |

**Đặt lại vị trí (không xoá):**

| # | View | Phần tử | Slot đích |
|---|---|---|---|
| 3, 6 | Warehouse `:134` · SparePart `:150` | dải `toast` (`bg-emerald-50`) | cuối `#header` (phải sống ở cả 4 trạng thái) |
| 2 | AssetTransfer `:181` | banner `error` của **xoá** | cuối `#header` (KHÔNG nối vào `:error-message`) |
| 11 | Incident `:224` | `<WorkOrderKpiStrip :items="kpiItems" />` | `#summary` — shell chỉ render `#summary` ở `empty`/`content` ⇒ **hết cảnh thẻ KPI in `0` khi API hỏng** |
| 11 | Incident `:268-272`, `:319-321` | dòng «Hiển thị N / M sự cố» | `#summary` (gộp 1 lần, bỏ bản trùng) |
| 11, 12 | Incident `:404` · RCA `:245` | `<BasePagination>` | `#pagination` |
| 3, 6, 7, 8, 9, 10 | Warehouse `:266` · SparePart `:293` · DocReq `:324` · PmTemplate `:318` · Firmware `:381` · SlaPolicy `:320`, `:381` | hộp thoại `fixed inset-0` | **NGOÀI** `</ListPageShell>` (node gốc thứ 2) |
| 4, 5 | DeviceModel `:317`, `:321` · Supplier `:346` | `ImportWizardModal` + xem ảnh | **NGOÀI** `</ListPageShell>` |

**Bẫy riêng theo màn (đọc trước khi sửa file tương ứng):**

| # | Bẫy | Xử lý |
|---|---|---|
| 2 | `AssetTransferListView.load()` `:99-108` **không có `try/finally`** — `loading.value = false` `:108` nằm SAU `await` ⇒ API hỏng thì **xương quay mãi** + unhandled rejection | viết lại theo khuôn §12.4 (đây là bug thật, không phải refactor thẩm mỹ) |
| 3, 10 | `filteredRows` / `filteredPolicies` là **lọc CLIENT** trên mảng đã nạp | `:is-empty` phải bám mảng **đang hiển thị** (`!filteredRows.length`), không bám `rows` |
| 8 | `listPmTemplates()` trả `{ data, pagination }` (**không** `items`) `:85-87` | giữ nguyên phép đọc; chỉ bọc `try/catch` |
| 9 | `load()` `:162` và `loadAssetMeta()` `:72` là **2 lượt nạp khác nhau**; `loadAssetMeta` đã tự nuốt lỗi `:82` | «Thử lại» chỉ gọi `load()` — spy `listFirmwareCrs` **== 2**, spy `getAssetActionMeta` **không đổi** |
| 11 | `onMounted` `:193-198` gọi `applyFilter()`/`fetchList()` **và** `fetchStats()` | «Thử lại» gọi **`applyFilter()`** (giữ bộ lọc), KHÔNG `store.fetchList()` trần (mất bộ lọc) ⇒ spy `listIncidents` == 2, spy `getIncidentStats` == 1 |
| 12 | `applyFilter(page = 1)` reset về trang 1 | chấp nhận: «Thử lại» = nạp lại trang 1 (ghi rõ để QA không tính là lỗi) |
| 4, 5 | `error` cũng là tên biến của… chỉ lượt nạp — **đã kiểm** (`remove()` dùng `toast.error`) | tái dùng an toàn (biến thể B) |
| 1 | `StockMovementListView.vue:109` nút tạo có `v-if="can('inventory.write')"` | giữ nút + điều kiện trong **cùng cửa sổ ±8 dòng** — `src/router/createButtonAffordance.test.ts` quét tĩnh |

### 12.5 Bất biến mới (`INV-UX3-11` … `INV-UX3-17`)

| Mã | Bất biến | Cách chứng minh |
|---|---|---|
| **INV-UX3-11** | Cả 12 view render **qua** shell: mỗi file có dòng `import ListPageShell from '@/components/ui/ListPageShell.vue'` và DOM có **đúng 1** `[data-testid="list-page-shell"]` | `grep -rl "ui/ListPageShell" frontend/src/views --include=*.vue \| wc -l` ≥ **16** · guard `uiListShellLot1Parity.test.ts` |
| **INV-UX3-12** | **Lỗi thắng rỗng** ở cả 12 màn: `data-state="error"` ⇒ **0** `[data-testid="list-content"]`, **0** `[data-testid="ui-empty"]`, và DOM **không** chứa chuỗi rỗng cũ của màn đó (bảng §12.4) | 12 test trạng thái, sub-case (b) |
| **INV-UX3-13** | **Tách nguồn lỗi**: `:error-message` chỉ nhận lỗi của **lượt nạp danh sách**; `err`/`toast`/`error`-xoá không được nối vào | đọc mã + test: mở hộp thoại, ép `save()` hỏng ⇒ `data-state` **vẫn** `content` |
| **INV-UX3-14** | «Thử lại» gọi lại **đúng hàm nạp, giữ bộ lọc/tham số**, đúng **1** lần | spy API danh sách `toHaveBeenCalledTimes(2)` sau 1 lần bấm (không 1 — nút trang trí; không 3 — nhân đôi request) |
| **INV-UX3-15** | **0 mã chết rỗng**: 5 file (1,2,3,6,11) không còn khối «Không có dữ liệu» nằm trong nhánh có-dữ-liệu | `grep -c "Không có dữ liệu" <file>` → 0 |
| **INV-UX3-16** | Cú pháp `@retry` **nguyên văn** (bộ dò `ui-audit-inventory.mjs:187` chỉ bắt `@retry`) | `grep -c "@retry" <file>` ≥ 1 cho cả 12 file; bộ dò cột *Lỗi+Thử lại* **89 → 77** |
| **INV-UX3-17** | Hộp thoại / wizard / toast **sống ở cả 4 trạng thái** (đặt ngoài nhánh) | test: ép `data-state="error"`, bấm nút mở hộp thoại ở `#header` ⇒ hộp thoại vẫn mount được |

### 12.6 Bộ test — `TC-UX3-11` … `TC-UX3-22` (12 file MỚI, ≥ 48 TC)

Đặt cạnh view, đúng khuôn 4 file đã có (`purchaseListStates.test.ts` là **mẫu tham chiếu**):

| TC | File test MỚI |
|---|---|
| `TC-UX3-11` | `frontend/src/views/inventory/stockMovementListStates.test.ts` |
| `TC-UX3-12` | `frontend/src/views/asset/assetTransferListStates.test.ts` |
| `TC-UX3-13` | `frontend/src/views/inventory/warehouseListStates.test.ts` |
| `TC-UX3-14` | `frontend/src/views/asset/deviceModelListStates.test.ts` |
| `TC-UX3-15` | `frontend/src/views/purchase/supplierListStates.test.ts` |
| `TC-UX3-16` | `frontend/src/views/inventory/sparePartListStates.test.ts` |
| `TC-UX3-17` | `frontend/src/views/document/documentRequestListStates.test.ts` |
| `TC-UX3-18` | `frontend/src/views/pm/pmTemplateListStates.test.ts` |
| `TC-UX3-19` | `frontend/src/views/document/firmwareCrListStates.test.ts` |
| `TC-UX3-20` | `frontend/src/views/master-data/slaPolicyListStates.test.ts` |
| `TC-UX3-21` | `frontend/src/views/incident/incidentListStates.test.ts` |
| `TC-UX3-22` | `frontend/src/views/incident/rcaListStates.test.ts` |

**Sub-case bắt buộc mỗi file (≥ 4; ⇒ tổng ≥ 48):**

- **(a) đang tải** ⇒ `data-state === 'loading'`, có `[data-testid="list-skeleton"]`, **0** `<table>`.
- **(b) lỗi** ⇒ `data-state === 'error'`, có `[data-testid="ui-error"]` + **đúng 1** control tên «Thử lại», **0** `[data-testid="list-content"]`, **0** `[data-testid="ui-empty"]`, `w.text()` **không** chứa chuỗi rỗng cũ của màn (§12.4).
- **(c) rỗng** ⇒ `data-state === 'empty'`, `ui-empty-title` khớp bảng §12.4, có `ui-empty-description`.
- **(d) có dữ liệu** ⇒ `data-state === 'content'`, đúng N dòng, **0** `ui-empty`, **0** `ui-error`.
- **(e) thử lại** (bắt buộc cho ĐỦ 12 màn — đây là `INV-UX3-4` + `INV-UX3-14`): lượt 1 reject → bấm «Thử lại» → lượt 2 resolve ⇒ spy nạp **== 2** và `data-state` chuyển `error` → `content`.
- **(f) bộ lọc sống khi lỗi** (màn có `ListFilterBar`): `[data-testid="list-filters"]` tồn tại ở trạng thái `error`.

**Khuôn mount:**
- 10 màn view-local: `vi.mock('<module>', …)` theo cột §12.2, `mount(View, { global: { stubs: { PageHeader: true, RouterLink: true }, mocks: { $router: { push: vi.fn() } } } })`.
- 2 màn store (`TC-UX3-21/22`) + `TC-UX3-20`: `setActivePinia(createPinia())` trong `beforeEach`; **spy ở lớp `@/api/imm12`** (không spy store) để đếm số lời gọi thật.
- `TC-UX3-19` phải mock **cả** `@/api/imm09` (`listRepairWorkOrders`) nếu không mount sẽ gọi mạng thật.

**Lệnh chấm (QA tự chạy, không nhận báo cáo suông):**

```bash
cd frontend
npx vitest run src/views/**/*ListStates.test.ts     # phải đọc thấy: Test Files 16 passed (16)
npx vitest run src/router/uiAuditDocParity.test.ts src/router/uiFixPlanParity.test.ts \
              src/router/uiListShellLot1Parity.test.ts
npx vitest run                                       # 0 đỏ; số file ≥ baseline + 12
npx vue-tsc --noEmit
node scripts/ui-audit-inventory.mjs | awk -F'|' 'NF>10 && $2 ~ /^ *[0-9]+ *$/ {gsub(/ /,"",$8); if($8=="❌") e++} END {print e}'   # 89 → 77
grep -rl "ui/ListPageShell" src/views --include=*.vue | wc -l                       # 4 → ≥16
cd .. && git status --porcelain -- '*.py'            # RỖNG
```

### 12.7 DoD lô 1 — 8 ô, thiếu 1 ô là CHƯA ĐÓNG

1. 12 file view có dòng `import ListPageShell from '@/components/ui/ListPageShell.vue'`; tổng adopter **≥ 16**.
2. 12 file test `*ListStates.test.ts` MỚI, đánh số `TC-UX3-11…22`, tổng TC mới **≥ 48**; `npx vitest run src/views/**/*ListStates.test.ts` in **`Test Files 16 passed (16)`**.
3. `npx vitest run` **0 đỏ**; số file test **≥ 327** (mốc sau bước BA = **315 file / 3133 test**, cộng 12 file trạng thái mới). Đo lại TRƯỚC/SAU và chấm **delta**, không dừng vì lệch số tuyệt đối.
4. 3 guard parity xanh: `uiAuditDocParity` · `uiFixPlanParity` · `uiListShellLot1Parity` (mới).
5. Bộ dò: cột *Lỗi+Thử lại* **89 → 77**; **0** ô đang ✅ bị lật thành ❌.
6. **Doc cập nhật CÙNG LƯỢT** (guard mục 4 sẽ đỏ nếu quên):
   - `00 §3.1`: cột «Lỗi+Thử lại» của **đúng 12 dòng** (số thứ tự 19, 23, 26, 37, 45, 54, 63, 67, 82, 92, 94, 97) `❌ → ✅`. **Không đụng dòng khác.**
   - `00 §6`: ô của `AC-UX-005` và `AC-UX-047` đổi `**còn 89**` → `**còn 77**`; §6 vẫn **58 mục**, **0** mã mới.
   - `04 §10.1`: khối «Lô 1» đổi trạng thái sang ĐÃ ĐÓNG + nợ nhóm `24 → 12`; bảng `§11` **135 dòng không đổi**.
7. Playwright render-verify **ảnh thật ≥ 3 màn** (ưu tiên `/suppliers`, `/spare-parts`, `/incidents/list`), mỗi màn 2 ảnh: có-dữ-liệu **và** lỗi (chặn request để ép nhánh lỗi). Ảnh phải **đọc được chữ báo lỗi + nút «Thử lại»** — ảnh trắng/khung xương **không tính**. Lưu `.playwright/eval/ux047-*.png`.
8. `git status --porcelain -- '*.py'` RỖNG · KHÔNG `bench migrate` · KHÔNG `git commit/push` · chạy `bash .claude/scripts/tidy-eval-artifacts.sh`, repo root 0 ảnh/junk.

### 12.8 Tại sao BA KHÔNG lật `00 §3.1` ngay ở bước đặc tả

`00_AUDIT_HIEN_TRANG.md` là **tài liệu ĐO**, không phải tài liệu kế hoạch: mỗi ô ✅ là một khẳng định về đĩa.
Lật ✅ trước khi mã land ⇒ tài liệu nói dối trong suốt cửa sổ giữa 2 bước, và nếu vòng vỡ giữa chừng thì lời
nói dối **ở lại vĩnh viễn** (đúng vết xe run-5: 3 đề mục bị báo sai trạng thái, suýt làm lại từ đầu).
Vì vậy lô 1 khoá bằng **guard parity 2 chiều** thay vì bằng lời hứa:

- `frontend/src/router/uiListShellLot1Parity.test.ts` đọc bảng **§12.2** làm SSoT rồi ép:
  *(1)* mỗi route trong sổ có view tồn tại trên đĩa và có dòng trong `00 §3.1`;
  *(2)* **`view import ListPageShell` ⟺ ô «Lỗi+Thử lại» của route đó = ✅** (2 chiều);
  *(3)* view đã import shell ⇒ **phải có** file `*ListStates.test.ts` cạnh nó;
  *(4)* số route trong sổ == **12**, và ô `AC-UX-047` ở `00 §6` công bố `còn N` với **N == 89 − (số route đã lật ✅)**.
- Hôm nay (0 adoption, 0 lật, `còn 89`) ⇒ **XANH**. Sau khi FE áp shell mà quên sửa doc ⇒ **ĐỎ ngay**.
  Không có trạng thái trung gian nào mà cả mã lẫn doc đều "trông có vẻ đúng".

> ⚠️ **Ghi chú nợ đã biết (KHÔNG sửa ở lô 1, tránh làm hỏng phép đếm của vòng này).**
> 4 dòng vòng 3 — `/purchases` (108), `/user-profiles` (117), `/procurement-plans` (125), `/vendor-profiles` (135)
> — **đã** dùng `ListPageShell` trên đĩa nhưng ô «Lỗi+Thử lại» ở `00 §3.1` **vẫn ❌** (vòng 3 quên lật).
> Bộ dò đã ghi nhận ✅ cho cả 4. ⇒ Xếp vào **lô 2** của `AC-UX-047`: lật 4 ô + mở rộng guard §12.8 phủ luôn
> 4 route đó. **KHÔNG** đụng ở vòng này (PM chốt «không đụng dòng khác»).

### 12.9 Quyết định kiến trúc

Xem **ADR-UX-11** ở [`00_AUDIT_HIEN_TRANG.md §9`](./00_AUDIT_HIEN_TRANG.md#9-quyết-định-kiến-trúc) —
*«`00 §3.1` là bảng SỐNG theo lô adoption (chỉ `§2.1` đóng băng); doc⇄đĩa khoá bằng guard parity 2 chiều, không bằng kỷ luật»*.
ADR này **làm rõ phạm vi** `ADR-UX-10` (không thay thế) và **thay** gạch đầu dòng
«KHÔNG đụng bảng §3.1 của tài liệu mẹ» ở `§0 Never` của vòng 3.

### 12.10 Rủi ro & để lại sau lô 1

| # | Rủi ro / nợ | Xử lý |
|---|---|---|
| 1 | Còn **77** route ❌ *Lỗi+Thử lại* | `AC-UX-047` lô 2+ — mỗi lô ≤ 12 màn cùng nhóm, khuôn §12.4 dùng lại nguyên |
| 2 | 4 dòng `00 §3.1` của vòng 3 còn stale ❌ | lô 2 (§12.8 ghi chú) |
| 3 | 12 màn lặp lại y hệt 15 dòng `try/catch/finally` | trích `useListLoad()` — **Ask first**, sớm nhất lô 3 khi khuôn đã ổn định qua 24 màn |
| 4 | Pager tự viết ở 10/12 màn chưa phải `BasePagination` | nợ cũ `02 §10` mục 5 |
| 5 | Cột a11y/≤768px của 12 màn **không** đổi ở lô này | `AC-UX-006/007/038/039` — cấm gộp vào lô 1 (2 rủi ro chồng nhau) |
| 6 | Bộ dò credit `@retry` bằng **quét chuỗi**: viết `v-on:retry` là mã đúng nhưng số không xuống | `INV-UX3-16` + lệnh chấm §12.6 |

---

## §13. LÔ 2 adoption `ListPageShell` — 12 route DANH SÁCH CUỐI CÙNG (`AC-UX-047`, đo 2026-08-04)

| Mục | Giá trị |
|---|---|
| Đề mục | `AC-UX-047` **lô 2** — KHÔNG cấp số sổ mới (sổ AC-UX đang ở **069**; lô là đơn vị thi hành, không phải mục sổ) |
| Phạm vi | **đúng 12** màn DANH SÁCH thuộc IMM-02/03/05/11/12/16 — **toàn bộ phần còn lại** của họ `*ListView` |
| Loại | Core Doc cross-cutting (UI/UX) — spec thi hành cho FE dev, **spec-before-code gate** |
| Ngày đo | **2026-08-04** — mọi số dưới đây đo TỪ ĐĨA hôm nay; số trong prompt/STATE coi như **stale** |
| Nhánh | `feature/hieuc/core-refinement` |
| Tài liệu cha | §0–§11 (khuôn + hợp đồng API `ListPageShell`) · §12 (lô 1, khuôn thi hành dùng lại nguyên) |
| Trạng thái | **Chốt để code** |

> **Vì sao lô 2 ĐÓNG HẲN họ danh sách.** Bộ dò 2026-08-04, lọc `cột «Lỗi+Thử lại» == ❌ AND file ~ /ListView/`
> ⇒ **đúng 12 route** — chính 12 route dưới đây. Sau lô 2, phép lọc đó phải trả **0 route**: mọi màn danh sách
> của hệ thống đều có 4 trạng thái loại trừ + đường nạp lại. Nợ còn lại của `AC-UX-047` (**57** route) từ đó
> **không còn dòng nào là màn danh sách** — toàn bộ là màn tạo/sửa/chi tiết/tiện ích, thuộc `AC-UX-048` và các lô sau.

### 13.1 Ba con số mâu thuẫn — chẩn đoán & cách chữa (BA Self-Correction)

Trước lô 2, cùng một đại lượng «bao nhiêu route thiếu lối nạp lại» có **ba** con số cùng "xanh":

| Nguồn | Số (trước) | Vì sao lệch |
|---|---|---|
| Bảng tay `00 §3.1`, đếm ô ❌ cột *Lỗi+Thử lại* | **64** | ảnh chụp vòng 1 (2026-07-31), 15 ô chưa đối soát |
| Bộ dò `ui-audit-inventory.mjs` (SSoT theo `ADR-UX-10`) | **69** | đo LIVE, đúng |
| Token `[NO-CON=N]` ở `00 §6` | **77** | phép trừ tay `89 − 12` với mốc 89 đo **2026-08-03** |

- **69 ⇄ 77 (lệch 8):** 8 đơn vị KHÔNG do lô danh sách mà do **lô 1 lớp CHI TIẾT** (`AC-UX-048`): 8 route áp
  `DetailPageShell` ⇒ có `@retry` ⇒ rời tập nợ. Phép trừ `89 − flipped` mù với mọi thay đổi ngoài lô của nó
  ⇒ **mốc 89 stale ngay ngày hôm sau**. Đây là lỗi **thiết kế guard**, không phải lỗi FE ⇒ sửa Core Doc + guard
  TRƯỚC (A6), không "chỉnh số cho khớp".
- **64 ⇄ 69 (lệch 15 ô, HAI CHIỀU):** 10 ô doc lạc quan hơn đĩa (✅ mà đĩa ❌) + 5 ô doc bi quan hơn đĩa
  (❌ mà đĩa ✅). Hai chiều ngược nhau ⇒ **không thể chữa bằng cách trừ thêm**; phải đối soát **từng ô**.
  Danh sách 15 ô + hướng lật: `00 §3.1` phần ⚠️ đầu bảng (đã lật, BA làm ở bước này).

**Chốt (thay mọi số trong prompt):**

| Đại lượng | Lệnh đo | Trước lô 2 | Sau lô 2 (nghiệm thu) |
|---|---|---|---|
| Bộ dò — ô ❌ cột *Lỗi+Thử lại* | `node frontend/scripts/ui-audit-inventory.mjs --summary` | **69** | **57** |
| `00 §3.1` — ô ❌ cột đó | đếm cột 7 của bảng | **69** (sau đối soát) | **57** |
| Token `[NO-CON=N]` (`00 §6`) | `grep "\[NO-CON=" docs/ui-ux/00_AUDIT_HIEN_TRANG.md` | **69** | **57** |
| Ô lệch doc ⇄ bộ dò, riêng cột này | `node frontend/scripts/ui-audit-inventory.mjs --check` | **0** | **0** |
| `*ListView.vue` có `import ListPageShell` | `grep -rl "ui/ListPageShell" frontend/src/views --include=*ListView.vue \| wc -l` | **16** | **28** |
| File `*ListStates.test.ts` | `ls frontend/src/views/*/*ListStates.test.ts \| wc -l` | **16** | **28** |
| Route `❌ AND /ListView/` | bộ dò `--json` + lọc | **12** | **0** |
| `TC-UX3-*` lớn nhất | `grep -rhoE "TC-UX3-[0-9]+" docs frontend/src \| sort -uV \| tail -1` | **TC-UX3-22** | **TC-UX3-34** |
| `INV-UX3-*` lớn nhất | như trên | **INV-UX3-17** | **INV-UX3-23** |
| `ADR-UX-*` lớn nhất | như trên | **ADR-UX-21** | **ADR-UX-22** |
| Sổ `AC-UX` | `grep -rhoE "AC-UX-[0-9]{3}" docs \| sort -u \| tail -1` | **069 / 69 mục** | **069 / 69 mục** (CẤM cấp mới) |

> ⚠️ **Suite FE**: đo TRƯỚC và SAU rồi chấm **DELTA**, đừng dừng vì lệch số tuyệt đối. Kỳ vọng **+12 file**
> (12 test trạng thái mới) và **≥ +72 test**. Mọi baseline viết trong prompt (351 file) coi như **stale**.
>
> **Mốc đo TỪ ĐĨA ngay sau bước BA (2026-08-04, `npx vitest run`): `Test Files 352 passed (352)` ·
> `Tests 3540 passed (3540)` — 0 ĐỎ** (bước BA chỉ viết lại guard trong **cùng 1 file**: 8 → 15 TC ⇒ **+0 file**).
> ⇒ Nghiệm thu A7 của FE: **≥ 364 file** (352 + 12) và **≥ 3612 test** (3540 + 72). `npx vue-tsc --noEmit` sạch.

### 13.2 Sổ lô 2 — 12 route (SSoT; guard `uiListShellLot1Parity.test.ts` đọc chính bảng này)

| # | Route | View file | Hàm nạp | Nguồn lỗi sau sửa | Module cần `vi.mock` | TC |
|---|---|---|---|---|---|---|
| 1 | `/assets` | `frontend/src/views/asset/AssetListView.vue` | `store.fetchList` (6 call-site) → gói vào `reload()` MỚI | **`store.error`** (`stores/imm00.ts:20`, clear đầu lượt `:24`) | `@/api/imm00` → `listAssets` + `listLocations`/`listDepartments`/`listAssetCategories`/`listDeviceModels`/`listSlaPolicies`/`listSuppliers` (refData) · cần Pinia | `TC-UX3-23` |
| 2 | `/calibration` | `frontend/src/views/calibration/CalibrationListView.vue` | `load(page)` `:102` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error` sau `await`) | `@/api/imm11` → `listCalibrations` + `getCalibrationKpis` · cần Pinia | `TC-UX3-24` |
| 3 | `/calibration/schedules` | `frontend/src/views/calibration/CalibrationScheduleListView.vue` | `load(toPage)` `:143` | `loadError` (ref MỚI — **KHÔNG** dùng `err` `:35` của biểu mẫu) | `@/api/imm11` → `listCalibrationSchedules`(+`createSchedule`/`updateSchedule`/`deleteSchedule`) · cần Pinia | `TC-UX3-25` |
| 4 | `/capas` | `frontend/src/views/incident/CAPAListView.vue` | `applyFilter()` `:118` → `reload()` MỚI | **`store.error`** (`stores/imm00.ts:111`, clear đầu lượt `:116`) | `@/api/imm00` → `listCapas` · cần Pinia | `TC-UX3-26` |
| 5 | `/compliance/rules` | `frontend/src/views/compliance/ComplianceRuleListView.vue` | `load(page)` `:59` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`; ô dùng chung, KHÔNG bind thẳng) | `@/api/imm16` → `listRules`(+`createRule`/`deactivateRule`/`reactivateRule`) · cần Pinia | `TC-UX3-27` |
| 6 | `/compliance/findings` | `frontend/src/views/compliance/FindingListView.vue` | `load(page)` `:72` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`) | `@/api/imm16` → `listFindings` + `runComplianceEvaluation` · cần Pinia | `TC-UX3-28` |
| 7 | `/compliance/audits` | `frontend/src/views/compliance/InternalAuditListView.vue` | `load(page)` `:68` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`) | `@/api/imm16` → `listAudits` + `createAudit` · cần Pinia | `TC-UX3-29` |
| 8 | `/compliance/mr` | `frontend/src/views/compliance/ManagementReviewListView.vue` | `load(page)` `:70` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`) | `@/api/imm16` → `listReviews`(+`createReview`) · cần Pinia | `TC-UX3-30` |
| 9 | `/tech-specs` | `frontend/src/views/tech-specs/TechSpecListView.vue` | `applyFilters()` `:60` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`; `fetchKpis` dùng chung ô) | `@/api/imm02` → `listTechSpecs` + `getDashboardKpis` · cần Pinia | `TC-UX3-31` |
| 10 | `/vendor-evaluations` | `frontend/src/views/procurement/VendorEvalListView.vue` | `applyFilters()` `:51` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`) | `@/api/imm03` → `listEvaluations` + `createEvaluation` · `@/api/imm02` → `listTechSpecs` · cần Pinia | `TC-UX3-32` |
| 11 | `/approved-vendors` | `frontend/src/views/procurement/AvlListView.vue` | `applyFilters()` `:81` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`; `fetchKpis` dùng chung ô) | `@/api/imm03` → `listAvl` + `getDashboardKpis` + `createAvlEntry`(+4 transition) · cần Pinia | `TC-UX3-33` |
| 12 | `/procurement-decisions` | `frontend/src/views/procurement/DecisionListView.vue` | `applyFilters()` `:70` → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`; `fetchKpis` dùng chung ô) | `@/api/imm03` → `listDecisions` + `getDashboardKpis` · cần Pinia | `TC-UX3-34` |

> Tên hàm API trong cột «Module cần `vi.mock`» là **gợi ý theo store**; FE **đọc `import` thật** của
> `stores/imm00|02|03|11|16.ts` rồi mock đúng tên — KHÔNG đoán. `stores/imm00.ts` và `imm02/03` import
> kiểu `import * as api from '@/api/immXX'` ⇒ mock **cả module**.

**Hai biến thể — không có biến thể thứ ba (khác lô 1: lô 2 KHÔNG có màn nào bind thẳng ô lỗi dùng chung):**

- **C. bind `store.error`** (2 màn: 1, 4) — `useAssetStore` / `useCapaStore` có ô `error` **riêng cho lượt nạp
  danh sách** và **clear ở đầu lượt** (`stores/imm00.ts:24` / `:116`) ⇒ bind thẳng `:error-message="store.error"`.
  Không có lời gọi thứ hai nào của cùng store trên màn này.
- **D. `loadError` + CHỤP LỖI SAU `await`** (10 màn còn lại) — store **nuốt lỗi** (`catch` gán `error` rồi
  KHÔNG ném lại) và **dùng chung một ô `error`** cho nhiều lời gọi (danh sách + KPI + tạo/sửa). Bind thẳng
  ⇒ một lần nạp KPI hỏng hoặc một lần tạo hỏng sẽ **xoá trắng danh sách** (vỡ `INV-UX3-13`).
  `stores/imm16.ts` còn **không clear** `error` ở đầu lượt ⇒ bind thẳng thì nút «Thử lại» **trông như chết**
  (vỡ `INV-UX3-4`). Khuôn chuẩn:

```ts
const loadError = ref<string | null>(null)

/** Nạp lại danh sách với ĐÚNG bộ lọc/trang hiện tại — điểm vào DUY NHẤT của «Thử lại». */
async function reload() {
  loadError.value = null
  store.error = null                       // ô dùng chung: dọn rác lượt trước (imm16 không tự dọn)
  await store.fetchXxx(<tham số hiện tại>)  // store nuốt lỗi ⇒ try/catch ở đây KHÔNG bắt được gì
  loadError.value = store.error ?? null     // CHỤP: chỉ lỗi của lượt nạp danh sách
  if (loadError.value) store.error = null   // trả ô dùng chung về sạch cho lời gọi khác
}
```

> **KHÔNG sửa `frontend/src/stores/**`** trong lô 2 (Ask-first). Ghi `store.error = null` từ view là **ghi
> vào state đã phơi ra**, không phải sửa file store. Nợ «`stores/imm16.ts` thiếu clear đầu lượt + 1 ô lỗi
> dùng chung 5 danh sách» ghi ở §13.9 cho lô sau.

### 13.3 Boundaries lô 2

**Always:**
- Giữ nguyên 4 trạng thái loại trừ + thứ tự `error > loading > empty > content` của §2 — **không** khai lại
  máy trạng thái trong view.
- Mỗi màn có **đúng một** hàm `reload()` là điểm vào của «Thử lại», nạp lại **đúng bộ lọc/trang hiện tại**.
- `@retry` viết **nguyên văn `@retry="reload"`** — bộ dò (`ui-audit-inventory.mjs:187`) chỉ nhận `@retry`;
  `v-on:retry` là mã đúng nhưng **số không xuống** và acceptance A1/A4 trượt.
- Đưa markup **đang có** vào slot; mọi chuỗi rỗng chuyển thành prop `empty-title` / `empty-hint` /
  slot `#empty-action` (bảng §13.4).
- Dải KPI / thẻ số đặt ở `#summary` (chỉ render ở `empty` + `content`) ⇒ **hết cảnh thẻ KPI in `0` khi API hỏng**.
- Hộp thoại (`fixed inset-0`), `BaseModal`, `ImportWizardModal`, dải toast đặt **NGOÀI** `</ListPageShell>`.
- Chữ hiển thị **100% tiếng Việt** (`LL-FE-53`): câu lỗi, câu rỗng-có-hướng-dẫn, nhãn «Thử lại».
  Giữ nguyên `QR`/`PIN` và từ VN phổ dụng; **không** để lọt từ tiếng Anh mới ở lớp hiển thị.

**Ask first (dừng, hỏi BA/PM):**
- Áp shell cho màn **thứ 13** trở đi (đó là lô khác — và với họ `*ListView` thì lô 2 là **lô cuối**).
- Sửa `frontend/src/stores/**` hoặc `frontend/src/api/**` (lô 2 **không cần** — đã kiểm chứng cột «Nguồn lỗi»).
- Trích `useListLoad()` composable (nợ `§10` mục 3) — **không** làm trong lô 2: 12 màn + đổi khuôn = 2 rủi ro chồng nhau.
- Đổi `data-testid` đang bị test khác khoá; đổi pager tự viết sang `BasePagination`.
- Sửa ô của **cột khác** trong `00 §3.1` (Skeleton/a11y/…): nếu việc áp shell làm đổi cột *Skeleton*
  của 4 màn Wave-2 (đang in chữ «Đang tải...»), **báo BA** — cột đó không nằm trong parity đang ép.

**Never:**
- **KHÔNG** đụng bất kỳ file `.py` nào (`git status --porcelain -- '*.py'` phải RỖNG cuối vòng) ⇒ không phát
  sinh nhu cầu user khởi động lại `gunicorn --preload`, **KHÔNG** `bench migrate`.
- **KHÔNG** nối lỗi **biểu mẫu / tạo / xoá / transition** (`err`, `createError`, `lastApiError`, toast) vào
  `:error-message` — một lần lưu hỏng sẽ **xoá trắng cả danh sách** (`INV-UX3-13`).
- **KHÔNG** để 2 lối báo lỗi song song (banner `.alert-error` cũ **và** `ErrorState`) ⇒ vỡ `INV-UX3-6`
  (đúng **1** nút «Thử lại» trên màn).
- **KHÔNG** cấp mã sổ `AC-UX` mới; sổ giữ **69 mục** (`uiAuditDocParity` ép «Tổng: N mục» khớp số đếm được).
- **KHÔNG** đổi bảng `04 §11` (135 dòng) và **KHÔNG** đổi bảng tổng hợp `00 §2.1` (đóng băng, `ADR-UX-10`).
- **KHÔNG** lật ô §3.1 của route NGOÀI 12 dòng lô 2 — 15 ô lệch đã được BA đối soát ở bước này, phần còn lại
  của cột đã **khớp từng ô** với bộ dò (`ADR-UX-22`); lật thêm = làm doc nói dối lần nữa.

### 13.4 Delta bắt buộc từng file

Khuôn `<template>` (giống §12.4, 6 slot, thứ tự cố định):

```vue
<ListPageShell
  :loading="loading"
  :error-message="loadError"
  :is-empty="!rows.length"
  :empty-title="emptyTitle"
  :empty-hint="emptyHint"
  @retry="reload">
  <template #header>   <PageHeader …/> </template>
  <template #summary>  <!-- dải KPI / thẻ số --> </template>
  <template #filters>  <ListFilterBar …/> </template>
  <template #skeleton> <SkeletonLoader variant="table" :rows="6" /> </template>
  <template #empty-action> <!-- «Xóa bộ lọc để xem tất cả» / «Tạo … đầu tiên» --> </template>
  <template #toolbar>  <!-- dòng «Hiển thị N / M …» + nút «Xóa tất cả» --> </template>
  <!-- slot mặc định: mobile-card-list + <table> -->
  <template #pagination> <BasePagination …/> </template>
</ListPageShell>
<!-- NGOÀI shell: BaseModal / overlay fixed inset-0 / ImportWizardModal / toast -->
```

`emptyTitle` / `emptyHint` là `computed` phân biệt **có lọc** ⇄ **không lọc** (giữ đúng ngữ nghĩa hiện có):

| # | View | `empty-title` (không lọc) | `empty-title` (có lọc) | `empty-hint` | `#empty-action` |
|---|---|---|---|---|---|
| 1 | AssetList | `Chưa có thiết bị nào` | `Không có thiết bị nào phù hợp` | `Hãy thêm thiết bị mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» (`activeFilterCount > 0`) |
| 2 | Calibration | `Chưa có phiếu hiệu chuẩn nào` | `Không có phiếu hiệu chuẩn nào phù hợp` | `Hãy tạo phiếu hiệu chuẩn mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 3 | CalibrationSchedule | `Chưa có lịch hiệu chuẩn nào` | `Không có lịch hiệu chuẩn nào phù hợp` | `Hãy tạo lịch hiệu chuẩn mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc…» · «Tạo lịch hiệu chuẩn đầu tiên» |
| 4 | CAPA | `Chưa có hành động khắc phục/phòng ngừa nào` | `Không có hành động khắc phục/phòng ngừa nào phù hợp` | `Hành động khắc phục/phòng ngừa được mở từ sự cố, phát hiện không phù hợp hoặc kết quả hiệu chuẩn không đạt.` | «Xóa bộ lọc để xem tất cả» |
| 5 | ComplianceRule | `Chưa có quy tắc tuân thủ nào` | `Không có quy tắc tuân thủ nào phù hợp` | `Hãy tạo quy tắc mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc…» · «Tạo quy tắc đầu tiên» (giữ nút `:189`) |
| 6 | Finding | `Chưa có phát hiện không phù hợp nào` | `Không có phát hiện nào phù hợp` | `Phát hiện được sinh tự động khi chạy đánh giá tuân thủ.` | «Xóa bộ lọc…» · «Chạy đánh giá tuân thủ» (dùng lại `runEvaluation`) |
| 7 | InternalAudit | `Chưa có đợt kiểm toán nội bộ nào` | `Không có đợt kiểm toán nào phù hợp` | `Hãy tạo đợt kiểm toán mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc…» · «Tạo đợt kiểm toán đầu tiên» |
| 8 | ManagementReview | `Chưa có cuộc soát xét quản lý nào` | `Không có cuộc soát xét nào phù hợp` | `Hãy tạo cuộc soát xét mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc…» · «Tạo cuộc soát xét đầu tiên» |
| 9 | TechSpec | `Chưa có hồ sơ kỹ thuật nào` | `Không có hồ sơ kỹ thuật nào phù hợp` | `Hãy tạo hồ sơ kỹ thuật mới hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 10 | VendorEval | `Chưa có phiếu đánh giá nhà cung cấp nào` | `Không có phiếu đánh giá nào phù hợp` | `Phiếu đánh giá được tạo từ hồ sơ kỹ thuật đã chốt.` | «Xóa bộ lọc để xem tất cả» |
| 11 | Avl | `Chưa có giấy phép nhà cung cấp nào` | `Không có giấy phép nào phù hợp` | `Hãy thêm nhà cung cấp vào danh sách được duyệt hoặc xoá bộ lọc để xem tất cả.` | «Xóa bộ lọc để xem tất cả» |
| 12 | Decision | `Chưa có quyết định mua sắm nào` | `Không có quyết định mua sắm nào phù hợp` | `Quyết định mua sắm được tạo sau khi chốt đánh giá nhà cung cấp.` | «Xóa bộ lọc để xem tất cả» |

**Khối phải XOÁ (banner lỗi song song + chuỗi rỗng trùng + mã chết) — để lại thì `INV-UX3-12`/`INV-UX3-6` đỏ:**

| # | View | Xoá | Lý do |
|---|---|---|---|
| 1 | AssetList | banner `:365` `.alert-error` · khối rỗng mobile `:414-427` · khối rỗng desktop `:521-529` | banner thay bằng `ErrorState`; 2 khối rỗng gộp về `EmptyState` của shell |
| 2 | Calibration | khối rỗng `:221-226` · **`:263`** «Không có dữ liệu» (trong nhánh CÓ dữ liệu ⇒ mã chết) | `AC-UX-046` |
| 3 | CalibrationSchedule | khối rỗng `:333-335` · **`:371`** «Không có dữ liệu» | mã chết |
| 4 | CAPA | banner `:180` · khối rỗng `:192-197` · **`:224`** «Không có dữ liệu» | banner + rỗng song song |
| 5 | ComplianceRule | khối rỗng `:184-190` | — |
| 6 | Finding | khối rỗng `:166-171` | — |
| 7 | InternalAudit | khối rỗng `:145-150` | — |
| 8 | ManagementReview | khối rỗng `:134-139` | — |
| 9 | TechSpec | banner `:155-157` · khối rỗng `:245-250` | banner thay bằng `ErrorState` |
| 10 | VendorEval | banner `:139-141` · **`:174`** «Không có dữ liệu» · khối rỗng `:226-231` | giữ `createError` trong hộp thoại `:240` |
| 11 | Avl | banner `:250-252` · **`:292`** «Không có dữ liệu» · khối rỗng `:350-355` | — |
| 12 | Decision | banner `:252-254` · **`:288`** «Không có dữ liệu» · khối rỗng `:352-357` | — |

**Đặt lại vị trí (không xoá):**

| # | View | Phần tử | Slot đích |
|---|---|---|---|
| 2 | Calibration `:184-209` | dải 6 thẻ KPI (`kpi-card`) | `#summary` — hết cảnh KPI in số khi danh sách hỏng |
| 9, 11, 12 | TechSpec `:141-153` · Avl `:241-248` · Decision `:215-250` | dải `<KpiCard>` | `#summary` |
| 1, 2, 4, 9, 10, 11, 12 | dòng «Hiển thị N / M …» + nút «Xóa tất cả» | `#toolbar` (trong khung card, chỉ ở trạng thái có dữ liệu) | |
| 1, 2, 3, 4, 5, 6, 7, 8 | `<BasePagination>` | `#pagination` | |
| 1 | AssetList `:535` `ImportWizardModal` | **NGOÀI** `</ListPageShell>` | |
| 3 | CalibSchedule `:439` overlay `fixed inset-0` · `:481` `BaseModal` | **NGOÀI** `</ListPageShell>` | |
| 5, 7, 8, 11 | ComplianceRule `:270` · InternalAudit `:211` · MR `:203` · Avl `:387`, `:428` `BaseModal` | **NGOÀI** `</ListPageShell>` | |
| 10 | VendorEval hộp thoại tạo (`showCreate`) | **NGOÀI** `</ListPageShell>` | |

**Bẫy riêng theo màn (đọc TRƯỚC khi sửa file tương ứng):**

| # | Bẫy | Xử lý |
|---|---|---|
| 1 | `AssetListView` **không có** hàm nạp duy nhất: `store.fetchList` được gọi ở `applyFilters:151` · `resetFilters:161` · `goToPage:167` · `onMounted:183` · `watch:195` · callback `useImportWizard:200` | thêm `function reload() { return store.fetchList(cleanParams.value) }` và **chỉ** `@retry="reload"`; **không** đổi 6 call-site kia (giữ hành vi `resetFilters` gọi `fetchList({})`) |
| 1 | `onMounted` chạy `Promise.all([fetchList, refData.fetchAll])`; `refData` **không có** ô lỗi | «Thử lại» chỉ gọi `reload()` ⇒ spy `listAssets` **== 2**, spy refData **không đổi** |
| 2 | `load()` `:102` và `loadKpis()` `:112` là **2 lượt nạp khác nhau**, dùng **chung** `store.error` (`_captureError`) | `onMounted`: `await load()` **rồi** `loadKpis()` (tuần tự, không `Promise.all`) ⇒ lỗi KPI không cướp trạng thái danh sách; spy `getCalibrationKpis` == 1 sau khi bấm «Thử lại» |
| 3 | `load()` `:143` `catch` gọi `store._captureError(e)` + `notify.fromError(...)` ⇒ lỗi chỉ đến bằng **toast tự tắt**, `items` giữ dữ liệu cũ ⇒ đúng *false-empty* | thay bằng `loadError.value = …`; **bỏ** `notify.fromError` **chỉ ở đường nạp** (giữ nguyên cho `save()`/`confirmRemove()`); `items.value = []` khi hỏng (`INV-UX3-5`) |
| 3 | `err` `:35` là lỗi **biểu mẫu** (`ModalInlineError` trong hộp thoại) | **KHÔNG** nối vào `:error-message` (`INV-UX3-13`) |
| 4 | `applyFilter()` `:118` nạp trang 1; URL là SSoT của bộ lọc `asset` (`dropAssetQuery`) | «Thử lại» = `applyFilter()` (giữ bộ lọc, về trang 1) — ghi rõ để QA không tính là lỗi |
| 5–8 | `stores/imm16.ts` **không clear** `error` đầu lượt (`:67-73`, `:78-84`, `:107-113`, `:172-178`) và **dùng chung** ô đó cho `createRule`/`deactivateRule`/`createAudit`/dashboard | bắt buộc biến thể **D** (chụp lỗi sau `await` + tự dọn ô dùng chung); bind thẳng `store.error` ⇒ nút «Thử lại» chết + lỗi tạo xoá trắng danh sách |
| 6 | `runEvaluation()` `:23` là hành động **ghi**, không phải nạp | lỗi của nó **không** vào `:error-message`; nút «Chạy đánh giá tuân thủ» ở `#empty-action` chỉ để mở đường thoát khi rỗng |
| 9, 11, 12 | `filteredSpecs` / `filteredAvl` / `filteredDecisions` là **lọc CLIENT** trên mảng đã nạp | `:is-empty` bám mảng **đang hiển thị** (`!filteredAvl.length`), không bám mảng gốc |
| 9, 11, 12 | `fetchKpis()` dùng **chung** `store.error` với danh sách (`imm02.ts:45` · `imm03.ts:109`) | `onMounted`: `await reload()` **rồi** `store.fetchKpis()`; biến thể D bắt buộc |
| 11 | `filters.workflow_state` mặc định `'Approved'` ⇒ `buildPayload()` **trùng khít** lời gọi `onMounted` `:198` | `reload()` = `applyFilters()` là đúng bộ lọc; **không** đổi mặc định |
| 12 | `applyQueryToFilters(force)` `:124` mới là đường nạp lúc mount (`:162`), có 2 nhánh `fetchDecisions(payload)` / `fetchDecisions()` | `reload()` gọi `applyFilters()` (nhánh có bộ lọc hiện tại); **không** gọi `applyQueryToFilters(true)` (sẽ ghi đè bộ lọc người dùng vừa chọn) |
| 9–12 | 4 màn Wave-2 in chữ **«Đang tải...»** thay cho khung xương | đưa `<SkeletonLoader variant="table" :rows="6" />` vào `#skeleton`; cột *Skeleton* của 4 dòng này ở `00 §3.1` **có thể** đổi ⇒ **báo BA**, không tự lật (Ask-first) |
| tất cả | `data-testid` đang bị test khác khoá (`createButtonAffordance.test.ts` quét **tĩnh** cửa sổ ±8 dòng quanh nút tạo) | giữ nút tạo + điều kiện `can(...)` trong **cùng cửa sổ**; chạy lại `npx vitest run src/router` sau khi dời markup |

### 13.5 Bất biến mới (`INV-UX3-18` … `INV-UX3-23`)

| Mã | Bất biến | Cách chứng minh |
|---|---|---|
| **INV-UX3-18** | **0 route** thoả `cột «Lỗi+Thử lại» == ❌ AND file ~ /ListView/` — họ danh sách ĐÓNG HẲN | bộ dò `--json` + lọc (lệnh §13.6) |
| **INV-UX3-19** | 12 view lô 2 render **qua** shell: mỗi file có `import ListPageShell from '@/components/ui/ListPageShell.vue'`, DOM có **đúng 1** `[data-testid="list-page-shell"]`; tổng adopter `*ListView` **16 → 28** | `grep -rl` + guard `uiListShellLot1Parity.test.ts` |
| **INV-UX3-20** | **Tách nguồn lỗi**: `:error-message` chỉ nhận lỗi của **lượt nạp danh sách**. Ép lỗi ở hành động ghi (tạo/duyệt/xoá/đánh giá) ⇒ `data-state` **vẫn** `content` | 12 test trạng thái, sub-case (f2) cho màn có hành động ghi |
| **INV-UX3-21** | «Thử lại» gọi lại **đúng hàm nạp danh sách**, giữ bộ lọc, đúng **1** lần; lời gọi phụ (KPI/refData/meta) **không tăng** | spy danh sách `toHaveBeenCalledTimes(2)`, spy phụ `toHaveBeenCalledTimes(1)` |
| **INV-UX3-22** | **0 mã chết rỗng**: 6 file (2, 3, 4, 10, 11, 12) không còn khối «Không có dữ liệu» nằm trong nhánh có-dữ-liệu | `grep -c "Không có dữ liệu" <file>` → 0 |
| **INV-UX3-23** | **Ba số bằng nhau**: `ô ❌ cột «Lỗi+Thử lại» ở 00 §3.1` == `số bộ dò` == `token [NO-CON=N]`, và **từng ô** của cột khớp bộ dò trên cả 148 dòng | guard `uiListShellLot1Parity.test.ts` (tự chạy bộ dò) + `--check` in `Lỗi+Thử lại 0` |

### 13.6 Bộ test — `TC-UX3-23` … `TC-UX3-34` (12 file MỚI, ≥ 72 TC)

Đặt cạnh view, đúng khuôn `frontend/src/views/purchase/supplierListStates.test.ts:50-115`:

| TC | File test MỚI |
|---|---|
| `TC-UX3-23` | `frontend/src/views/asset/assetListStates.test.ts` |
| `TC-UX3-24` | `frontend/src/views/calibration/calibrationListStates.test.ts` |
| `TC-UX3-25` | `frontend/src/views/calibration/calibrationScheduleListStates.test.ts` |
| `TC-UX3-26` | `frontend/src/views/incident/capaListStates.test.ts` |
| `TC-UX3-27` | `frontend/src/views/compliance/complianceRuleListStates.test.ts` |
| `TC-UX3-28` | `frontend/src/views/compliance/findingListStates.test.ts` |
| `TC-UX3-29` | `frontend/src/views/compliance/internalAuditListStates.test.ts` |
| `TC-UX3-30` | `frontend/src/views/compliance/managementReviewListStates.test.ts` |
| `TC-UX3-31` | `frontend/src/views/tech-specs/techSpecListStates.test.ts` |
| `TC-UX3-32` | `frontend/src/views/procurement/vendorEvalListStates.test.ts` |
| `TC-UX3-33` | `frontend/src/views/procurement/avlListStates.test.ts` |
| `TC-UX3-34` | `frontend/src/views/procurement/decisionListStates.test.ts` |

**Sub-case bắt buộc mỗi file (≥ 6 ⇒ tổng ≥ 72):**

- **(a) đang tải** ⇒ `data-state === 'loading'`, có `[data-testid="list-skeleton"]`, **0** `<table>`.
- **(b) lỗi + ĐÚNG 1 «Thử lại»** ⇒ `data-state === 'error'`, có `[data-testid="ui-error"]`, số control mang
  chữ «Thử lại» **=== 1**, **0** `[data-testid="list-content"]`, **0** `[data-testid="ui-empty"]`, và
  `w.text()` **không** chứa chuỗi rỗng cũ của màn đó (bảng §13.4).
- **(c) rỗng THẬT** ⇒ `data-state === 'empty'`, `ui-empty-title` khớp bảng §13.4, có `ui-empty-description`.
- **(d) có dữ liệu N dòng** ⇒ `data-state === 'content'`, đúng N dòng, **0** `ui-empty`, **0** `ui-error`.
- **(e) «Thử lại» gọi lại đúng 1 lần** ⇒ lượt 1 reject → bấm «Thử lại» → lượt 2 resolve ⇒ spy danh sách
  **== 2**, spy lời gọi phụ **== 1**, `data-state` chuyển `error` → `content`.
- **(f) loại trừ cấu trúc** ⇒ đúng **1** `[data-testid="list-page-shell"]`, đúng **1** trạng thái đang render
  (đếm `list-loading` + `ui-error` + `ui-empty` + `list-content` **=== 1**), và `[data-testid="list-filters"]`
  **vẫn tồn tại** ở trạng thái `error` (bộ lọc còn sống).

**Khuôn mount:** cả 12 màn đều dùng Pinia ⇒ `setActivePinia(createPinia())` trong `beforeEach`; **spy ở lớp
`@/api/immXX`** (KHÔNG spy store — spy store thì không đo được số lời gọi thật và che mất `INV-UX3-21`);
`mount(View, { global: { stubs: { PageHeader: true, RouterLink: true, ListFilterBar: false }, mocks: { $router: { push: vi.fn() } } } })`.
`ListFilterBar` **không** được stub (sub-case (f) cần nó sống trong DOM).

**Lệnh chấm (QA tự chạy, không nhận báo cáo suông):**

```bash
cd frontend
# A1 — họ danh sách ĐÓNG HẲN: phải in "0"
node scripts/ui-audit-inventory.mjs --json \
  | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{const r=JSON.parse(s).rows.filter(x=>x.cells&&x.cells.error==="❌"&&/ListView/.test(x.file||""));console.log(r.length);r.forEach(x=>console.log("  "+x.path))})'
# A2 — adoption THẬT: 16 → 28 (và grep -L không còn 12 file lô 2)
grep -rl "ui/ListPageShell" src/views --include=*ListView.vue | wc -l
# A3 — test trạng thái: 16 → 28 file
ls src/views/*/*ListStates.test.ts | wc -l
npx vitest run src/views/**/*ListStates.test.ts      # Test Files 28 passed (28)
# A4/A5/A6/A8 — 5 guard nền + guard lô (đã neo vào bộ dò)
npx vitest run src/router/uiAuditDocParity.test.ts src/router/uiFixPlanParity.test.ts \
              src/router/uiListShellLot1Parity.test.ts src/router/uiDetailShellLot1Parity.test.ts \
              src/components/common/modalOverlayHygiene.test.ts src/components/ui/uiPrimitiveHygiene.test.ts
# A4 — token == số bộ dò; A5 — 3 số bằng nhau
node scripts/ui-audit-inventory.mjs --summary | grep "Lỗi+Thử lại"       # ❌ 57
grep -o "\[NO-CON=[0-9]*\]" ../docs/ui-ux/00_AUDIT_HIEN_TRANG.md         # [NO-CON=57]
node scripts/ui-audit-inventory.mjs --check | grep "Lỗi+Thử lại"         # 0 ô lệch
# A7 — suite FULL, chấm DELTA bằng mắt
npx vitest run
npx vue-tsc --noEmit
# A10 — 0 file .py
cd .. && git status --porcelain -- '*.py'                                 # RỖNG
```

### 13.7 DoD lô 2 — 10 ô, thiếu 1 ô là CHƯA ĐÓNG

1. **A1** — bộ dò lọc `❌ AND /ListView/` ⇒ **0 route** (hôm nay đúng 12; danh sách ở §13.2).
2. **A2** — 12 file view có `import ListPageShell …`; `grep -rl … *ListView.vue | wc -l` = **28** (từ 16).
3. **A3** — **đúng 12** file `*ListStates.test.ts` MỚI (16 → **28**), mã `TC-UX3-23…34`, mỗi file **≥ 6** TC
   ⇒ **≥ +72 TC**; `npx vitest run src/views/**/*ListStates.test.ts` in `Test Files 28 passed (28)`.
4. **A4** — token `[NO-CON=N]` ở `00 §6` == số bộ dò in ra SAU khi land = **57** (69 − 12; **không** 77 − 12).
5. **A5** — ba số bằng nhau: ô ❌ `§3.1` == bộ dò == token == **57**; `--check` in `Lỗi+Thử lại 0`.
6. **A6** — guard `uiListShellLot1Parity.test.ts` **không còn** `89 − flipped`; neo vào bộ dò + parity 2 chiều.
   **Prove-It**: sửa tay 1 ô §3.1 **hoặc** gỡ 1 `import ListPageShell` ⇒ guard **ĐỎ** (chạy thật, dán output).
7. **A7** — `npx vitest run` **0 ĐỎ**; số file **+12** so với lần đo ngay trước khi FE bắt đầu (đọc bằng mắt).
8. **A8** — 4 guard nền xanh (`uiAuditDocParity` · `uiFixPlanParity` · `modalOverlayHygiene` ·
   `uiPrimitiveHygiene`) + `uiListShellLot1Parity` bản mới + `uiDetailShellLot1Parity` (không được vạ lây).
9. **A9/A11** — chữ hiển thị 100% tiếng Việt; **≥ 3 ảnh** Playwright ở `.playwright/eval/` cho
   `/compliance/findings` · `/approved-vendors` · `/calibration` **ở trạng thái LỖI** (chặn API), đọc được
   câu lỗi **và** nút «Thử lại» — ảnh trắng/khung xương **không tính**.
10. **A10/A12** — `git status --porcelain -- '*.py'` RỖNG · KHÔNG `bench migrate` · KHÔNG `git commit/push` ·
    `bash .claude/scripts/tidy-eval-artifacts.sh`, repo root 0 file scratch (`__qa_*`, `*_scan_junk*`, `page-*.yml`).

**Doc phải cập nhật CÙNG LƯỢT với mã** (guard sẽ đỏ nếu quên):
- `00 §3.1`: cột «Lỗi+Thử lại» của **đúng 12 dòng** lô 2 (số thứ tự **11, 58, 60, 69, 72, 74, 76, 79, 127,
  130, 132, 133**) `❌ → ✅`. **Không đụng dòng khác** — 15 ô lệch đã do BA đối soát ở bước spec.
- `00 §6`: token `[NO-CON=69]` → `[NO-CON=57]` (dòng `AC-UX-047`); ô `AC-UX-005` đổi «còn 69» → «còn 57».
  §6 vẫn **69 mục**, **0** mã mới.
- `04 §10.1`: nợ nhóm «Danh sách» `12 → 0` + bảng tiến độ `AC-UX-047` thêm dòng **lô 2 = ĐÃ ĐÓNG**.

### 13.8 Guard mới — neo vào BỘ DÒ, không vào phép trừ (A6, đã land ở bước BA)

`frontend/src/router/uiListShellLot1Parity.test.ts` (giữ nguyên tên file — đổi tên làm hỏng mọi tham chiếu)
được viết lại quanh **`ADR-UX-22`**:

| Bất biến | Nội dung |
|---|---|
| `INV-UX3L-1` | Sổ **lô 1** (`02 §12.2`) đúng 12 dòng · sổ **lô 2** (`02 §13.2`) đúng 12 dòng · mã TC `TC-UX3-11…22` và `TC-UX3-23…34`, không trùng, không nhảy cóc |
| `INV-UX3L-2` | Mọi route trong 2 sổ là route THẬT (`router/index.ts`); view file có trên đĩa và TRÙNG ô view file ở `00 §3.1` |
| `INV-UX3L-3` | **Parity 2 CHIỀU** cho cả 24 route: `view import ListPageShell` ⟺ ô «Lỗi+Thử lại» = ✅ |
| `INV-UX3L-4` | View đã áp khuôn ⇒ **phải có** file `*ListStates.test.ts` khai ở §12.6/§13.6 và tồn tại trên đĩa |
| `INV-UX3L-5` | **Neo vào bộ dò**: test tự chạy `node frontend/scripts/ui-audit-inventory.mjs --json` rồi ép `token [NO-CON=N]` == **số ô ❌ bộ dò đo LIVE** (KHÔNG phép trừ nào) |
| `INV-UX3L-6` | **Parity từng ô** cột «Lỗi+Thử lại» giữa `00 §3.1` và bộ dò trên **cả 148 dòng** (chặn ca 2 lỗi ngược chiều triệt tiêu nhau) |
| `INV-UX3L-7` | Chiều toàn cục: **mọi** view `.vue` có `import ListPageShell` ⇒ ô route của nó ở `§3.1` = ✅ (bắt cả màn ngoài 2 sổ) |

Guard XANH ở **cả hai đầu**: bước BA (0/12 lô 2 đã áp · `NO-CON=69`) và sau khi FE land (12/12 · `NO-CON=57`).
Không tồn tại trạng thái trung gian mà cả mã lẫn doc đều "trông có vẻ đúng".

### 13.9 Rủi ro & việc để lại sau lô 2

| # | Rủi ro / nợ | Xử lý |
|---|---|---|
| 1 | Còn **57** route ❌ *Lỗi+Thử lại* — **0** trong số đó là màn danh sách | `AC-UX-048` (chi tiết) + lô sau cho màn tạo/sửa/tiện ích; khuôn `ListPageShell` **không** áp cho màn biểu mẫu |
| 2 | `stores/imm16.ts` dùng **1 ô `error`** cho 5 danh sách + mọi hành động ghi, **không clear** đầu lượt | nợ BE-FE tầng store; lô 2 né bằng biến thể D. Sửa store = **Ask-first**, sớm nhất khi tách `useListLoad()` |
| 3 | 12 màn lặp lại khuôn `reload()` + `loadError` | trích `useListLoad()` — Ask-first, sau khi khuôn ổn định qua **28** màn |
| 4 | 4 màn Wave-2 (9–12) lọc **client-side** ⇒ `is-empty` bám mảng đã lọc; phân trang server chưa có | nợ cũ `§10`; không gộp vào lô 2 |
| 5 | Cột *Skeleton* của 4 màn Wave-2 có thể đổi khi thay «Đang tải...» bằng khung xương | FE **báo BA**; BA lật ô cột *Skeleton* trong cùng lượt (cột đó chưa bị parity ép) |
| 6 | Cột a11y/≤768px của 12 màn **không** đổi ở lô này | `AC-UX-006/007/038/039` — cấm gộp (2 rủi ro chồng nhau) |
| 7 | 6 cột còn lại của `§3.1` vẫn lệch bộ dò **49** ô | nợ đã biết, ghi ở `00 §3.1`; mở rộng parity sang cột khác là quyết định riêng (`ADR` mới) |

---

## §14. LÔ 3 adoption `ListPageShell` — 12 route DANH SÁCH CÒN LẠI THẬT SỰ (`AC-UX-047`, đo 2026-08-04)

| Mục | Giá trị |
|---|---|
| Đề mục | `AC-UX-047` **lô 3** (thi hành) + **`AC-UX-070`** (guard mới, số cấp sau khi grep sổ: max cũ = `AC-UX-069`) |
| Phạm vi | **đúng 12** màn `*ListView` CUỐI CÙNG chưa áp khuôn — IMM-00/01/04/06/08/09/14/15 |
| Loại | Core Doc cross-cutting (UI/UX) — spec thi hành cho FE dev, **spec-before-code gate** |
| Ngày đo | **2026-08-04** — mọi số dưới đây đo TỪ ĐĨA hôm nay; số trong prompt/STATE coi như **stale** |
| Nhánh | `feature/hieuc/core-refinement` |
| Tài liệu cha | §0–§11 (khuôn + hợp đồng API) · §12 (lô 1) · §13 (lô 2 — **có 1 khẳng định phải đính chính**, xem §14.1) |
| Trạng thái | **✅ ĐÃ ĐÓNG — FE land 2026-08-04 (vòng 9)**, xem §14.11 |

> **Lô 3 đóng HỌ `*ListView` theo nghĩa ĐẾM ĐƯỢC:** `grep -L ListPageShell views/*/*ListView.vue | wc -l`
> phải từ **12 → 0**, `grep -l` từ **28 → 40**. Đây là phép đo thay thế cho phép lọc bộ dò mà lô 2 đã dùng —
> lý do đổi phép đo nằm ở §14.1 (phép đo cũ **không sai số**, nó **đo sai đại lượng**).

### 14.1 Vì sao có lô 3 khi lô 2 đã ghi «DANH SÁCH CUỐI CÙNG» (BA Self-Correction)

`§13` khẳng định: sau lô 2, phép lọc `bộ dò: ô «Lỗi+Thử lại» == ❌ AND file ~ /ListView/` trả **0 route** ⇒
«họ danh sách hết nợ». Khẳng định đó **đúng theo phép đo của nó** và **vẫn đúng hôm nay** (đo lại
2026-08-04: 0 route). Nhưng nó **kết luận quá tay**: 12 màn danh sách còn lại **có** nút «Thử lại», nên bộ dò
chấm ✅ — trong khi thứ `AC-UX-047` thật sự phải trả là **4 trạng thái LOẠI TRỪ**, không phải *sự tồn tại của
một nút*.

| Đại lượng | Phép đo | Đo 2026-08-04 | Nói lên điều gì |
|---|---|---|---|
| Nợ *Lỗi+Thử lại* | `ui-audit-inventory.mjs` — **có mặt** chuỗi `@retry` / control mang chữ «Thử lại» trong file | **57** ❌ toàn hệ; **0** ❌ ở họ `*ListView` | có **một lối** nạp lại ở đâu đó trong file |
| Adoption khuôn | `grep -L ListPageShell views/*/*ListView.vue` | **12** file chưa áp (28/40 đã áp) | 4 trạng thái có **loại trừ nhau bằng CẤU TRÚC** hay không |

**Bộ dò là phép đo TRÌNH BÀY (có/không có phần tử), không phải phép đo BẤT BIẾN (loại trừ).** Một file có thể
vừa in banner lỗi vừa in khối «Chưa có dữ liệu» và vẫn được chấm ✅ cả hai cột *Lỗi+Thử lại* và *Rỗng+HD* —
đúng ca `/audit-trail` và `/needs-requests` dưới đây. Vì vậy lô 3 **không** đo bằng bộ dò; nó đo bằng
**guard adoption `AC-UX-070`** (§14.8) và bằng 12 bộ test trạng thái (§14.6).

**Đính chính ghi vào sổ (không xoá câu cũ — `P-DOC-3`):**
- `§13` tiêu đề + callout: «12 route DANH SÁCH CUỐI CÙNG» ⇒ đọc là **«12 route cuối cùng còn ❌ ở cột
  *Lỗi+Thử lại*»**. Đúng theo cột đó; **không** đồng nghĩa «mọi màn danh sách đã áp khuôn».
- `04 §10.1` dòng «Lô 3+ | 0 màn danh sách | không còn» ⇒ **SAI**, sửa thành lô 3 = 12 màn (BA sửa cùng lượt).
- Nợ nhóm «Danh sách» của `04 §10.1` ở tiêu chí *Lỗi+Thử lại* **vẫn = 0** (đo LIVE) — con số đó không đổi vì
  lô 3; cái đổi là **cột adoption**, một đại lượng `04 §10.1` chưa từng ghi.

**Số chốt (thay mọi số trong prompt — prompt viết `AC-UX-063` / `16 adopter` / `340 file test` / `49 confirm`):**

| Đại lượng | Lệnh đo | Trước lô 3 | Sau lô 3 (nghiệm thu) |
|---|---|---|---|
| Sổ `AC-UX` lớn nhất | `grep -rhoE "AC-UX-[0-9]{3}" docs/ \| sort -u \| tail -1` | **AC-UX-069** (69 mục) | **AC-UX-070** (70 mục) |
| `*ListView.vue` CHƯA áp khuôn | `cd frontend/src && grep -L ListPageShell views/*/*ListView.vue \| wc -l` | **12** | **0** |
| `*ListView.vue` ĐÃ áp khuôn | `grep -l …` | **28** / 40 | **40** / 40 |
| File `*ListStates.test.ts` | `ls frontend/src/views/*/*ListStates.test.ts \| wc -l` | **28** | **40** |
| File test FE | `find frontend/src -name '*.test.ts' \| wc -l` | **363** → **364** sau bước BA (+1 guard `AC-UX-070`) | **≥ 376** |
| `Test Files` do `npx vitest run` công bố | đọc bằng mắt cuối output | **365** sau bước BA *(364 `.test.ts` + 1 `.spec.ts` — vitest đếm cả hai, đừng so thẳng với `find`)* | **≥ 377** |
| `Tests` do `npx vitest run` công bố | như trên | **3638** (0 ĐỎ, đo sau bước BA) | **≥ 3710** (+72) |
| Bộ dò — ô ❌ *Lỗi+Thử lại* | `node frontend/scripts/ui-audit-inventory.mjs --summary` | **57** | **57** (KHÔNG đổi — xem §14.1) |
| Token `[NO-CON=N]` (`00 §6`) | `grep -o "\[NO-CON=[0-9]*\]" docs/ui-ux/00_AUDIT_HIEN_TRANG.md` | **57** | **57** |
| `TC-UX3-*` lớn nhất | `grep -rhoE "TC-UX3-[0-9]+" docs frontend/src \| sort -uV \| tail -1` | **TC-UX3-34** | **TC-UX3-46** |
| `INV-UX3-*` lớn nhất | như trên | **INV-UX3-23** | **INV-UX3-29** |
| `ADR-UX-*` lớn nhất | như trên | **ADR-UX-22** | **ADR-UX-23** |
| `confirm(` trần | `grep -rn "confirm(" frontend/src --include=*.vue --include=*.ts \| wc -l` | **80 thô** (42 sau lọc allowlist của `bareConfirmBudget`) | không đụng ở lô 3 |

> ⚠️ **Ô §3.1 của 12 route lô 3: KHÔNG lật ô nào.** Cả 12 dòng đã là ✅ ở cột *Lỗi+Thử lại* từ trước
> (bộ dò `--json` 2026-08-04: dòng 28, 41, 44, 49, 71, 85, 87, 104, 122, 138, 141, 145). Chạm vào là làm vỡ
> `INV-UX3L-6` (parity từng ô) và `INV-UX3L-5` (token == bộ dò).

### 14.2 Sổ lô 3 — 12 route (SSoT; guard `uiListShellLot1Parity.test.ts` đọc chính bảng này)

| # | Route | View file | Hàm nạp | Nguồn lỗi sau sửa | Module cần `vi.mock` | TC |
|---|---|---|---|---|---|---|
| 1 | `/audit-trail` | `frontend/src/views/audit/AuditTrailListView.vue` | `fetchTrails()` `:85` (đã là điểm vào duy nhất) | `fetchError` `:19` — **đổi giá trị "không lỗi"** từ chuỗi rỗng sang `null` | `@/api/helpers` → `frappeGet` · `@/api/imm00` → `verifyChain` | `TC-UX3-35` |
| 2 | `/cm/work-orders` | `frontend/src/views/cm/CMWorkOrderListView.vue` | `reload(page)` `:121` | **`store.error`** (`stores/imm09.ts:37`, clear đầu lượt `:71`) | `@/api/imm09` → `listRepairs` + `getRepairKpis` · cần Pinia | `TC-UX3-36` |
| 3 | `/service-contracts` | `frontend/src/views/purchase/ServiceContractListView.vue` | `load()` `:78` | `error` `:22` — **đổi giá trị "không lỗi"** từ chuỗi rỗng sang `null` | `@/api/helpers` → `frappeGet` | `TC-UX3-37` |
| 4 | `/decommissions` | `frontend/src/views/eol/DecommissionListView.vue` | `load()` `:81` | `errorMsg` `:67` (giữ nguyên, đã đúng) | `@/api/imm14` → `listDecommissions` | `TC-UX3-38` |
| 5 | `/inventory/cycle-counts` | `frontend/src/views/inventory/CycleCountListView.vue` | `load()` `:46` | `loadError` (ref MỚI — **chụp** `store.error`; `stores/imm15.ts:58` là ô DÙNG CHUNG cho cấp phát/xuất nhập/kiểm kê) | `@/api/inventory` → `listCycleCounts` + `listWarehouses` · cần Pinia | `TC-UX3-39` |
| 6 | `/pm/work-orders` | `frontend/src/views/pm/PMWorkOrderListView.vue` | `reload(page)` `:94` | **`store.error`** (`stores/imm08.ts:44`, clear đầu lượt `:92`) | `@/api/imm08` → `listWorkOrders` + `getDashboardStats` · cần Pinia | `TC-UX3-40` |
| 7 | `/pm/schedules` | `frontend/src/views/pm/PmScheduleListView.vue` | `load()` `:103` | `loadError` `:101` (giữ nguyên, đã đúng) | `@/api/imm08` → `listPmSchedules`(+`createPmSchedule`/`updatePmSchedule`/`deletePmSchedule`) · cần Pinia | `TC-UX3-41` |
| 8 | `/needs-requests` | `frontend/src/views/needs/NeedsRequestListView.vue` | `applyFilters()` `:85` → `reload()` MỚI | **`store.error`** (`stores/imm01.ts:27`, clear đầu lượt `:45`) | `@/api/imm01` → `listNeedsRequests` + `getNeedsKpis` · cần Pinia | `TC-UX3-42` |
| 9 | `/commissioning` | `frontend/src/views/commissioning/CommissioningListView.vue` | `store.fetchList` (`applyFilters` `:132` · `goToPage` `:167` · `refreshList` `:338` của store) → `reload()` MỚI | `loadError` (ref MỚI — **chụp** `store.error`; `stores/imm04.ts:73` dùng CHUNG với ~20 hành động ghi) | `@/api/imm04` → `listCommissioning` + `getDashboardStats` · cần Pinia | `TC-UX3-43` |
| 10 | `/imm06/programs` | `frontend/src/views/training/ProgramListView.vue` | `load(page)` `:66` | `loadError` (ref MỚI — **chụp** `store.error`; `stores/imm06.ts:40` dùng CHUNG cho 3 danh sách + mọi hành động ghi) | `@/api/imm06` → `listPrograms` · cần Pinia | `TC-UX3-44` |
| 11 | `/imm06/sessions` | `frontend/src/views/training/SessionListView.vue` | `load(page)` `:71` | `loadError` (ref MỚI — như trên) | `@/api/imm06` → `listSessions` · cần Pinia | `TC-UX3-45` |
| 12 | `/imm06/competencies` | `frontend/src/views/training/CompetencyListView.vue` | `load(page)` `:81` (2 nhánh: drill `expiring` / lọc thường) | `loadError` (ref MỚI — như trên) | `@/api/imm06` → `listCompetencies` + `getExpiringCompetencies` · cần Pinia | `TC-UX3-46` |

> Tên hàm ở cột «Module cần `vi.mock`» là **gợi ý theo store**; FE **đọc `import` thật** của
> `stores/imm01|04|06|08|09|15.ts` rồi mock đúng tên — KHÔNG đoán (bẫy «No export named …» của lô 2).

**Ba biến thể ô lỗi — chọn theo cột «Nguồn lỗi», không chọn theo cảm tính:**

- **A. ô lỗi CỤC BỘ đã có** (3 màn: 1, 3, 4, 7) — view tự giữ `fetchError`/`error`/`errorMsg`/`loadError`,
  clear ở đầu lượt nạp. Bind thẳng `:error-message`. Với màn 1 và 3 phải **đổi giá trị rỗng `''` → `null`**
  (prop `errorMessage?: string | null`; chuỗi rỗng vẫn được `ListPageShell` coi là "không lỗi" nhờ `.trim()`,
  nhưng `null` mới đúng kiểu và tránh `v-if=""` mơ hồ ở test).
- **C. bind `store.error`** (3 màn: 2, 6, 8) — `stores/imm08|09|01` có ô `error` **chỉ cho lượt nạp danh sách**
  và **clear ở đầu lượt** (`imm08:92` · `imm09:71` · `imm01:45`). Bind thẳng `:error-message="store.error"`.
  ⚠️ `store.filterError` (`imm08:50` · `imm09:43`) là **CẢNH BÁO bộ lọc** — bảng vẫn giữ dữ liệu ⇒ **KHÔNG**
  nối vào `:error-message`, giữ nguyên banner riêng đặt ở slot `#filters` (xem §14.4 bẫy 2/6).
- **D. `loadError` + CHỤP LỖI SAU `await`** (5 màn: 5, 9, 10, 11, 12) — store **nuốt lỗi** và **dùng chung một
  ô `error`** cho nhiều lời gọi. Khuôn y hệt §13.2:

```ts
const loadError = ref<string | null>(null)

/** Nạp lại danh sách với ĐÚNG bộ lọc/trang hiện tại — điểm vào DUY NHẤT của «Thử lại». */
async function reload() {
  loadError.value = null
  store.error = null                        // ô dùng chung: dọn rác lượt trước
  await store.fetchXxx(<tham số hiện tại>)   // store nuốt lỗi ⇒ try/catch ở đây KHÔNG bắt được gì
  loadError.value = store.error ?? null      // CHỤP: chỉ lỗi của lượt nạp danh sách
  if (loadError.value) store.error = null    // trả ô dùng chung về sạch cho lời gọi khác
}
```

> **Bẫy riêng của 3 màn IMM-06 (10, 11, 12):** `load()` hiện bọc `api.run(() => store.fetchPrograms(...))`.
> `useApi.run` chỉ bắt **exception**, mà store đã `catch` rồi ⇒ `api.lastError` **luôn null** khi danh sách
> hỏng. Đọc lỗi từ `api.lastError` = luôn thấy "không lỗi". Phải dùng biến thể **D** (chụp `store.error`).

### 14.3 Boundaries lô 3

**Always:**
- Giữ nguyên 4 trạng thái loại trừ + thứ tự `error > loading > empty > content` của §2 — **không** khai lại
  máy trạng thái trong view.
- Mỗi màn có **đúng một** hàm `reload()` (hoặc hàm nạp sẵn có được nêu ở §14.2) là điểm vào của «Thử lại»,
  nạp lại **đúng bộ lọc/trang hiện tại**.
- `@retry` viết **nguyên văn `@retry="reload"`** — bộ dò (`ui-audit-inventory.mjs:187`) chỉ nhận `@retry`.
- Dải KPI / thẻ số đặt ở `#summary` (chỉ render ở `empty` + `content`) ⇒ **hết cảnh KPI in `0` khi API hỏng**
  (4 màn có KPI: 2, 6, 8, 9).
- Hộp thoại (`fixed inset-0`), `BaseModal`, `ImportWizardModal`, dải toast đặt **NGOÀI** `</ListPageShell>`.
- Chữ hiển thị **100% tiếng Việt** (`LL-FE-53`) — bảng copy §14.4 là SSoT của chuỗi rỗng.
- Sau khi áp khuôn, mỗi màn còn **ĐÚNG 1** nguồn chữ rỗng và **ĐÚNG 1** nút «Thử lại».

**Ask first (dừng, hỏi BA/PM):**
- Sửa `frontend/src/stores/**` hoặc `frontend/src/api/**` (lô 3 **không cần** — đã kiểm chứng cột «Nguồn lỗi»).
- Trích `useListLoad()` composable (nợ `§10` mục 3) — **không** làm trong lô 3.
- Đổi `data-testid` đang bị test khác khoá — đặc biệt `list-empty-scoped` (`CommissioningListView.vue:296`)
  đang bị `commissioningScopedEmpty*.test.ts` khoá; giữ nguyên testid, chỉ ĐỔI CHỖ.
- Đổi pager tự viết (`/audit-trail` `:434` · `/service-contracts` `:282` · `/decommissions` `:287` ·
  `/inventory/cycle-counts` `:188`) sang `BasePagination`.
- Ô cột *Skeleton* / *a11y* / *≤768px* của `00 §3.1` đổi trạng thái do việc áp khuôn ⇒ **báo BA**, không tự lật.

**Never:**
- **KHÔNG** đụng bất kỳ file `.py` nào (`git status --porcelain -- '*.py'` phải RỖNG) · **KHÔNG** `bench migrate`
  · **KHÔNG** `git commit/push`.
- **KHÔNG** nối lỗi **biểu mẫu / tạo / xoá / transition** vào `:error-message` (`INV-UX3-13`) — cụ thể:
  `err` `:99` của `PmScheduleListView` (lỗi hộp thoại), `store.filterError` của IMM-08/09, lỗi
  `verifyChain()` `:134` của `/audit-trail` (kết quả kiểm tra chuỗi hash, không phải lỗi nạp).
- **KHÔNG** lật bất kỳ ô nào của `00 §3.1` ở lô này (§14.1 ⚠️).
- **KHÔNG** cấp thêm mã sổ `AC-UX` ngoài **`AC-UX-070`**; sổ chốt **70 mục**.
- **KHÔNG** đổi bảng `04 §11` (135 dòng) và bảng tổng hợp `00 §2.1` (đóng băng, `ADR-UX-10`).

### 14.4 Delta bắt buộc từng file

Khuôn `<template>` (giống §12.4/§13.4, 6 slot, thứ tự cố định):

```vue
<ListPageShell
  :loading="loading"
  :error-message="loadError"
  :is-empty="!rows.length"
  :empty-title="emptyTitle"
  :empty-hint="emptyHint"
  @retry="reload">
  <template #header>   <PageHeader …/> </template>
  <template #summary>  <!-- dải KPI / thẻ số --> </template>
  <template #filters>  <ListFilterBar …/> </template>
  <template #skeleton> <SkeletonLoader variant="table" :rows="6" /> </template>
  <template #empty-action> <!-- «Xóa bộ lọc để xem tất cả» / «Tạo … đầu tiên» --> </template>
  <template #toolbar>  <!-- dòng «Hiển thị N / M …» + nút «Xóa tất cả» --> </template>
  <!-- slot mặc định: mobile-card-list + <table> -->
  <template #pagination> <BasePagination …/> </template>
</ListPageShell>
<!-- NGOÀI shell: BaseModal / overlay fixed inset-0 / ImportWizardModal / toast -->
```

**Bảng copy tiếng Việt — `emptyTitle` / `emptyHint` là `computed` phân biệt có-lọc ⇄ không-lọc:**

| # | View | `empty-title` (không lọc) | `empty-title` (có lọc) | `empty-hint` | `#empty-action` |
|---|---|---|---|---|---|
| 1 | AuditTrail | `Chưa có bản ghi kiểm toán nào` | `Không có bản ghi kiểm toán nào phù hợp` | `Nhật ký kiểm toán được ghi tự động khi có thao tác trên thiết bị, phiếu bảo trì hoặc hồ sơ chất lượng.` | «Xóa bộ lọc để xem tất cả» (`activeFilterCount > 0`) |
| 2 | CMWorkOrder | `Chưa có lệnh sửa chữa nào` | `Không tìm thấy lệnh sửa chữa nào phù hợp` | `Lệnh sửa chữa được mở từ sự cố hoặc tạo trực tiếp khi thiết bị hỏng.` | «Xóa bộ lọc để xem tất cả» · «Tạo lệnh sửa chữa» (`can('repair.create')`) |
| 3 | ServiceContract | `Chưa có hợp đồng dịch vụ nào` | `Không có hợp đồng dịch vụ nào phù hợp` | `Hợp đồng dịch vụ là căn cứ theo dõi hạn bảo hành, bảo trì và hiệu chuẩn theo nhà cung cấp.` | «Xóa bộ lọc để xem tất cả» · «Thêm hợp đồng dịch vụ» (`can('data.create')`) |
| 4 | Decommission | `Chưa có biên bản giải nhiệm nào` | `Không có biên bản giải nhiệm nào phù hợp` | `Biên bản giải nhiệm được lập từ hồ sơ thiết bị (nút «Giải nhiệm»).` | «Xóa bộ lọc để xem tất cả» · «Đến danh sách thiết bị» (giữ nút `:233`) |
| 5 | CycleCount | `Chưa có phiếu kiểm kê nào` | `Không có phiếu kiểm kê nào phù hợp` | `Phiếu kiểm kê dùng để đối chiếu tồn kho thực tế với sổ sách theo từng kho.` | «Xóa bộ lọc để xem tất cả» · «Tạo phiếu kiểm kê đầu tiên» |
| 6 | PMWorkOrder | `Chưa có phiếu bảo trì định kỳ nào` | `Không tìm thấy phiếu bảo trì định kỳ nào phù hợp` | `Phiếu bảo trì định kỳ được sinh từ lịch bảo trì hoặc tạo thủ công cho một thiết bị.` | «Xóa bộ lọc để xem tất cả» · «Tạo phiếu bảo trì định kỳ» (`can('pm.create')`) |
| 7 | PmSchedule | `Chưa có lịch bảo trì định kỳ nào` | `Không có lịch bảo trì định kỳ nào phù hợp với bộ lọc` | `Lịch bảo trì định kỳ quyết định khi nào phiếu bảo trì được sinh cho từng thiết bị.` | «Xóa bộ lọc» · «+ Thêm lịch bảo trì định kỳ» (`:disabled="!canCreatePm"`, giữ nguyên `:311`) |
| 8 | NeedsRequest | `Chưa có đề xuất nhu cầu nào` | `Không có đề xuất nào phù hợp` | `Đề xuất nhu cầu là bước đầu của vòng đời thiết bị — khoa/phòng lập, phòng vật tư thẩm định.` | «Xóa bộ lọc để xem tất cả» · «Tạo đề xuất nhu cầu» (`can('needs.create')`) |
| 9 | Commissioning | `Chưa có phiếu nghiệm thu lắp đặt nào` | `Không tìm thấy phiếu nào phù hợp` | `Phiếu nghiệm thu lắp đặt được lập khi nhà cung cấp bàn giao thiết bị tại khoa.` | «Xóa bộ lọc để xem tất cả» · «Tạo phiếu nghiệm thu» (`can('commissioning.create')`) |
| 9b | Commissioning — **rỗng theo ngữ cảnh thiết bị** (`isScopedEmpty` `:110`) | `Thiết bị {mã} chưa có phiếu nghiệm thu lắp đặt nào` | (không áp dụng) | `Bấm «Xem tất cả» để bỏ giới hạn theo thiết bị.` | giữ **nguyên** nội dung khối `:295-329` **và** `data-testid="list-empty-scoped"` — chuyển vào `#empty-action`/`empty-title` bằng `computed`, KHÔNG xoá testid |
| 10 | Program | `Chưa có chương trình đào tạo nào` | `Không có chương trình đào tạo nào phù hợp` | `Chương trình đào tạo là khuôn nội dung; buổi đào tạo được mở theo chương trình.` | «Xóa bộ lọc để xem tất cả» · «Tạo chương trình đào tạo» (`canManage`) |
| 11 | Session | `Chưa có buổi đào tạo nào` | `Không có buổi đào tạo nào phù hợp` | `Buổi đào tạo được mở từ một chương trình đào tạo và ghi nhận người tham dự.` | «Xóa bộ lọc để xem tất cả» · «Tạo buổi đào tạo» (`canCreate`) |
| 12 | Competency | `Chưa có bản ghi năng lực nào` | `Không có bản ghi năng lực nào phù hợp` | `Bản ghi năng lực sinh ra khi người dùng hoàn thành buổi đào tạo và đạt điểm yêu cầu.` | «Xóa bộ lọc để xem tất cả» · «Bỏ lọc thời hạn» khi `drillWindow` (giữ `clearDrill()` `:95`) · «Tạo buổi đào tạo» (`canCreateSession`) |

**Khối phải XOÁ (lỗi giả dạng rỗng / khối rỗng trùng / mã chết) — đo từ đĩa 2026-08-04:**

| # | View | Xoá | Loại khuyết tật (đã xác minh) |
|---|---|---|---|
| 1 | AuditTrail | banner `:198-211` (`v-if="fetchError"`, độc lập) · khối rỗng `:240-248` | **α — LỖI GIẢ DẠNG RỖNG THẬT**: `catch` `:105` gán `trails=[]` rồi `fetchError` ⇒ hai khối **cùng render**: banner đỏ «Không tải được nhật ký kiểm toán» **và** minh hoạ «Không có bản ghi kiểm toán nào phù hợp». Người dùng đọc câu thứ hai và tin là **không có bản ghi** |
| 2 | CMWorkOrder | khối rỗng thẻ `:303-309` · khối rỗng bảng `:376-383` | **A5 — HAI nguồn chữ rỗng** cho cùng một câu hỏi; gộp về `EmptyState` của shell |
| 3 | ServiceContract | banner `:194-197` · khối rỗng `:209-214` (điều kiện `contracts.length === 0 && !error`) | **β — BẢNG RỖNG KHI LỖI**: `&& !error` đẩy trạng thái lỗi rơi vào `<template v-else>` `:215` ⇒ hiện **bảng 0 dòng** + dòng đếm «Hiển thị **0** / 0 hợp đồng» ngay dưới banner. Ba tín hiệu mâu thuẫn cùng màn |
| 4 | Decommission | banner-lỗi `:216-222` · khối rỗng `:223-237` | γ — đã tri-branch đúng; chuyển sang khuôn để **1 nơi** giữ hợp đồng (nút «Thử lại» hiện là `btn-secondary` tự chế, khác nhãn SSoT của `ErrorState`) |
| 5 | CycleCount | banner-lỗi `:137-140` · khối rỗng `:141-148` | γ + ô lỗi **dùng chung** `stores/imm15.ts:58` (cấp phát / xuất nhập / kiểm kê) ⇒ lỗi màn khác vẫn tô đỏ màn này ⇒ bắt buộc biến thể **D** |
| 6 | PMWorkOrder | khối rỗng thẻ `:324-326` · khối rỗng bảng `:383-393` | **A5 — HAI nguồn chữ rỗng**; câu bảng còn có dòng gợi ý mà bản thẻ không có (2 trải nghiệm khác nhau cùng 1 trạng thái) |
| 7 | PmSchedule | banner-lỗi `:299-303` · khối rỗng `:305-313` | γ — mẫu tốt nhất trong 12 màn (đã có `loadError` riêng); chỉ chuyển vào khuôn |
| 8 | NeedsRequest | banner `:209-216` (`v-if="store.error"`, độc lập) · khối rỗng `:348-355` · **mã chết `:261-263`** «Không có dữ liệu» | **α — LỖI GIẢ DẠNG RỖNG THẬT**: banner + `v-else` rỗng cùng render khi lượt nạp đầu hỏng (`stores/imm01.ts:53` set lỗi, `needsRequests` giữ `[]`). `:261` nằm **trong** nhánh `v-else-if="…length"` ⇒ không bao giờ chạy |
| 9 | Commissioning | banner-lỗi `:277-286` · khối rỗng thẻ `:362-365` · khối rỗng bảng `:442-456` | **A5 — BA khối rỗng** (kể cả `list-empty-scoped`); giữ **1** khối scoped + **1** `EmptyState` chung |
| 10 | Program | banner-lỗi `:133-136` · khối rỗng `:137-145` · **mã chết `:168-170`** | γ + A5 (mã chết trong nhánh có-dữ-liệu) |
| 11 | Session | banner-lỗi `:142-145` · khối rỗng `:146-154` · **mã chết `:175-177`** | γ + A5 |
| 12 | Competency | banner-lỗi `:215-218` · khối rỗng `:219-236` · **mã chết `:267-269`** | γ + A5 |

> **Ghi rõ để QA không chấm nhầm:** chỉ **2/12** màn (#1, #8) hôm nay in đồng thời «lỗi» + «Chưa có dữ liệu»
> (`α`), **1/12** (#3) in «lỗi» + **bảng rỗng** (`β`), **9/12** đã loại trừ đúng (`γ`) nhưng mỗi màn tự cài
> lại máy trạng thái + còn 2–3 nguồn chữ rỗng. Prompt vòng này liệt kê 8 màn `α` — **SAI 6 dòng**; giá trị
> thật của lô 3 là **thống nhất khuôn + diệt nguồn rỗng trùng + KPI-khi-lỗi**, không phải "diệt false-empty ở
> cả 12 màn". Đừng viết TC RED cho ca không tồn tại (§14.6 chia rõ 2 nhóm).

**Đặt lại vị trí (không xoá):**

| # | View | Phần tử | Slot đích |
|---|---|---|---|
| 2, 6 | CM `:184` · PM `:211` `<WorkOrderKpiStrip>` | dải KPI | `#summary` — **hết cảnh KPI in 0 khi danh sách lỗi** |
| 8 | NeedsRequest `:178-206` (4 `<KpiCard>`) | dải KPI | `#summary` |
| 9 | Commissioning `:241` `<WorkOrderKpiStrip>` | dải KPI (có `@kpi-click`) | `#summary` — giữ `onKpiClick` |
| 1, 2, 3, 6, 8 | dòng «Hiển thị N / M …» + nút «Xóa tất cả» | `#toolbar` (chỉ render ở trạng thái có dữ liệu) |
| 2, 6 | `store.filterError` (CM `:219-235` · PM `:263-279`) | `#filters` (dưới `ListFilterBar`) — **cảnh báo bộ lọc, KHÔNG phải lỗi nạp** |
| 1 | `verifyResult` `:214-222` (kết quả kiểm tra chuỗi hash) | `#filters` — độc lập với trạng thái danh sách |
| 12 | Competency `:171-182` dải drill + `:183-…` | `#filters` |
| 2, 6, 8, 9, 10, 11, 12 | `<BasePagination>` | `#pagination` |
| 3 | ServiceContract `:290` `ImportWizardModal` | **NGOÀI** `</ListPageShell>` |
| 7 | PmSchedule `:408` overlay `fixed inset-0` | **NGOÀI** `</ListPageShell>` |
| 1 | AuditTrail hộp thoại chi tiết (`selectedTrail`) | **NGOÀI** `</ListPageShell>` |

**Bẫy riêng theo màn (đọc TRƯỚC khi sửa file tương ứng):**

| # | Bẫy | Xử lý |
|---|---|---|
| 1 | `fetchError` kiểu `''` (chuỗi rỗng) — `errorMessage` prop nhận `string \| null` | đổi khai báo `ref<string \| null>(null)`; `:88` gán `null`, `:106` gán `msg`. `toast.error(msg)` `:107` **giữ** (2 kênh khác nhau: toast tự tắt, `ErrorState` ở lại) |
| 1 | `verify()` `:134` là hành động **đọc-kiểm-tra**, không phải nạp danh sách | lỗi của nó **không** vào `:error-message`; `verifyResult` giữ vị trí riêng |
| 2, 6 | `store.filterError` là CẢNH BÁO (`imm08.ts:47-50` · `imm09.ts:39-43` ghi rõ trong chú thích store): bảng **giữ dữ liệu đang xem** | giữ banner riêng ở `#filters`, giữ `data-test="cm-filter-error"`; **không** để nó lật `data-state` sang `error` |
| 2, 6 | KPI đến từ lời gọi thứ hai (`getRepairKpis`/`getDashboardStats`) dùng **chung** `store.error`? — KHÔNG: `imm08:92`/`imm09:71` chỉ clear ở `fetchWorkOrders` | `onMounted`: `await reload()` **rồi** nạp KPI (tuần tự) ⇒ lỗi KPI không cướp trạng thái danh sách; spy KPI `== 1` sau khi bấm «Thử lại» |
| 3 | `load()` `:78` `if (res)` — `frappeGet` trả `null` khi BE trả `message: null` ⇒ **không** vào `catch`, `contracts` giữ giá trị cũ, `error` rỗng | thêm nhánh `else { contracts.value = []; totalCount.value = 0; error.value = 'Không tải được danh sách hợp đồng dịch vụ.' }` — nếu không, lỗi `null` vẫn cho ra màn rỗng câm |
| 4 | `load()` `:81` dùng `useApi` với `silentError: true`; skeleton bám `api.loading.value && !rows.length` | `:loading="api.loading.value && !rows.length"` giữ nguyên ngữ nghĩa; `errorMsg` đã clear ở `:82` |
| 5 | `error` là ô **dùng chung** của `stores/imm15.ts`; `load()` `:46` **không** `await` (hàm `void`) | đổi `load()` thành `async` + `await store.fetchCycleCounts(...)` rồi chụp lỗi (biến thể D). Đây là đổi **trong view**, không đụng store |
| 5 | `listWarehouses()` `:70` (onMounted) hỏng ⇒ chỉ mất danh mục lọc | bọc `.catch(() => [])`, **không** đưa vào `:error-message` |
| 7 | `err` `:99` là lỗi **hộp thoại** (`ModalInlineError`), `loadError` `:101` là lỗi nạp | giữ **tách bạch**; `:disabled="!canCreatePm"` ở nút rỗng phải giữ (guard `createButtonAffordance`) |
| 8 | `applyFilters()` `:85` nạp **trang 1**; `goPage()` `:115` nạp trang p | `reload()` = nạp lại `buildPayload()` với **`store.page` hiện tại**, không ép về trang 1 (mất chỗ đang xem) |
| 8 | `store.clearError()` `:212` (nút ×) sẽ mất khi bỏ banner | không cần thay thế — `ErrorState` biến mất khi `reload()` thành công |
| 9 | `isScopedEmpty` `:110` = có `?asset=` **và** 0 dòng — khác rỗng thường | `empty-title` là `computed` 3 nhánh (scoped / có-lọc / không-lọc); `#empty-action` giữ nút «Xem tất cả»; **giữ** `data-testid="list-empty-scoped"` (test khác đang khoá) |
| 9 | `BasePagination` `:464` có `v-if="!isScopedEmpty"` | ở khuôn mới, `#pagination` chỉ render trong `content` ⇒ điều kiện thành thừa nhưng **giữ** để không đổi hành vi khi `store.list.length > 0` |
| 9 | `store.error` dùng chung với ~20 hành động ghi (`imm04.ts:73`, `_captureError`) | bắt buộc biến thể **D** |
| 10–12 | `api.run(() => store.fetchXxx())` — store đã nuốt lỗi ⇒ `api.lastError` **luôn null** | biến thể **D** (chụp `store.error`); **không** đọc `api.lastError` |
| 12 | `load()` `:81` có nhánh drill `expiring` (`fetchExpiringCompetencies`) | `reload()` phải gọi lại **đúng nhánh đang hiện hành** (đọc `drillWindow` tại thời điểm bấm), không cứng hoá 1 nhánh |
| tất cả | `data-testid` đang bị test khác khoá (`createButtonAffordance.test.ts` quét **tĩnh** cửa sổ ±8 dòng quanh nút tạo) | giữ nút tạo + điều kiện `can(...)` trong **cùng cửa sổ**; chạy lại `npx vitest run src/router` sau khi dời markup |

### 14.5 Bất biến mới (`INV-UX3-24` … `INV-UX3-29`)

| Mã | Bất biến | Cách chứng minh |
|---|---|---|
| **INV-UX3-24** | **Adoption ĐÓNG HẲN**: `grep -L ListPageShell views/*/*ListView.vue` = **0**; `grep -l` = **40/40** | guard `AC-UX-070` (`views/listShellAdoption.test.ts`) + lệnh §14.6 |
| **INV-UX3-25** | **Loại trừ**: ở trạng thái lỗi, DOM có **0** phần tử rỗng — không `[data-testid="ui-empty"]`, không chuỗi rỗng cũ của màn đó | 12 test trạng thái, sub-case (b) |
| **INV-UX3-26** | **Một nguồn chữ rỗng/màn**: mỗi view lô 3 chỉ còn **1** nơi sinh chữ rỗng (shell), trừ `/commissioning` được phép **2** (`list-empty-scoped` + `EmptyState`) và chúng **loại trừ nhau** | `grep -c` chuỗi rỗng cũ = 0 + sub-case (f) |
| **INV-UX3-27** | **KPI không nói dối**: 4 màn có dải KPI (2, 6, 8, 9) — ở trạng thái `error`, `[data-testid="list-summary"]` **không tồn tại** | sub-case (g) của 4 file test tương ứng |
| **INV-UX3-28** | **Tách nguồn lỗi**: `:error-message` chỉ nhận lỗi **lượt nạp danh sách**. Ép `store.filterError` (2, 6) hoặc lỗi hộp thoại (7) ⇒ `data-state` **vẫn** `content` | sub-case (h) của 3 file test tương ứng |
| **INV-UX3-29** | «Thử lại» gọi lại **đúng hàm nạp danh sách**, giữ bộ lọc/trang, đúng **1** lần; lời gọi phụ (KPI/danh mục/meta) **không tăng** | spy danh sách `toHaveBeenCalledTimes(2)`, spy phụ `toHaveBeenCalledTimes(1)` |

### 14.6 Bộ test — `TC-UX3-35` … `TC-UX3-46` (12 file MỚI, ≥ 72 TC)

Đặt cạnh view, đúng khuôn `frontend/src/views/compliance/findingListStates.test.ts`:

| TC | File test MỚI |
|---|---|
| `TC-UX3-35` | `frontend/src/views/audit/auditTrailListStates.test.ts` |
| `TC-UX3-36` | `frontend/src/views/cm/cmWorkOrderListStates.test.ts` |
| `TC-UX3-37` | `frontend/src/views/purchase/serviceContractListStates.test.ts` |
| `TC-UX3-38` | `frontend/src/views/eol/decommissionListStates.test.ts` |
| `TC-UX3-39` | `frontend/src/views/inventory/cycleCountListStates.test.ts` |
| `TC-UX3-40` | `frontend/src/views/pm/pmWorkOrderListStates.test.ts` |
| `TC-UX3-41` | `frontend/src/views/pm/pmScheduleListStates.test.ts` |
| `TC-UX3-42` | `frontend/src/views/needs/needsRequestListStates.test.ts` |
| `TC-UX3-43` | `frontend/src/views/commissioning/commissioningListStates.test.ts` |
| `TC-UX3-44` | `frontend/src/views/training/programListStates.test.ts` |
| `TC-UX3-45` | `frontend/src/views/training/sessionListStates.test.ts` |
| `TC-UX3-46` | `frontend/src/views/training/competencyListStates.test.ts` |

**Sub-case bắt buộc mỗi file (≥ 6 ⇒ tổng ≥ 72):**

- **(a) đang tải** ⇒ `data-state === 'loading'`, có `[data-testid="list-skeleton"]`, **0** `<table>`, **0** «Thử lại».
- **(b) lỗi + ĐÚNG 1 «Thử lại»** ⇒ `data-state === 'error'`, có `[data-testid="ui-error"]`, số control mang
  chữ «Thử lại» **=== 1**, **0** `[data-testid="list-content"]`, **0** `[data-testid="ui-empty"]`, và
  `w.text()` **không** chứa chuỗi rỗng cũ của màn đó (bảng §14.4).
- **(c) rỗng THẬT** ⇒ `data-state === 'empty'`, `ui-empty-title` khớp bảng §14.4, có `ui-empty-description`.
- **(d) có dữ liệu N dòng** ⇒ `data-state === 'content'`, đúng N dòng, **0** `ui-empty`, **0** `ui-error`.
- **(e) «Thử lại» gọi lại đúng 1 lần** ⇒ lượt 1 reject → bấm «Thử lại» → lượt 2 resolve ⇒ spy danh sách
  **== 2**, spy lời gọi phụ **== 1**, `data-state` chuyển `error` → `content`.
- **(f) loại trừ cấu trúc** ⇒ đúng **1** `[data-testid="list-page-shell"]`, tổng
  (`list-loading` + `ui-error` + `ui-empty` + `list-content`) **=== 1**, và `[data-testid="list-filters"]`
  **vẫn tồn tại** ở trạng thái `error`.

**Sub-case THEO MÀN (không viết cho màn không có tính chất đó — chống TC giả):**

| Sub-case | Áp cho | Nội dung |
|---|---|---|
| **(g) KPI im lặng khi lỗi** | 2, 6, 8, 9 | trạng thái `error` ⇒ `[data-testid="list-summary"]` **không tồn tại**; trạng thái `content` ⇒ tồn tại và in đúng số |
| **(h) lỗi bộ lọc ≠ lỗi nạp** | 2, 6 (`store.filterError`), 7 (`err` hộp thoại) | set nguồn lỗi phụ ⇒ `data-state` **vẫn** `content`, banner phụ vẫn hiện |
| **(i) rỗng theo ngữ cảnh thiết bị** | 9 | `?asset=AC-ASSET-…` + 0 dòng ⇒ `data-state === 'empty'`, có `[data-testid="list-empty-scoped"]`, **0** `ui-empty` chung |
| **(j) TC RED bắt buộc** | **1, 8** (`α`) và **3** (`β`) | **Viết TRƯỚC khi sửa view, phải ĐỎ**: mock lượt nạp reject ⇒ khẳng định `w.text()` **không** chứa `Không có bản ghi kiểm toán nào phù hợp` (1) / `Không có đề xuất nào phù hợp` (8) / `w.findAll('table')` **=== 0** (3). Dán output ĐỎ vào báo cáo vòng — 3 màn này là bằng chứng lỗi THẬT trên đĩa |

**Khuôn mount:** 9/12 màn dùng Pinia ⇒ `setActivePinia(createPinia())` trong `beforeEach` (trừ 1, 3 dùng
`frappeGet` trực tiếp; 4 dùng `useApi`). **Spy ở lớp `@/api/immXX`** (KHÔNG spy store);
`vi.mock('vue-router', … vueRouterMockFactory())`; `ListFilterBar` **không** stub.

**Lệnh chấm (QA tự chạy, không nhận báo cáo suông):**

```bash
cd frontend/src
# A1 — adoption ĐÓNG HẲN: phải in "0" rồi "40"
grep -L ListPageShell views/*/*ListView.vue | wc -l
grep -l ListPageShell views/*/*ListView.vue | wc -l
cd ..
# A3 — test trạng thái: 28 → 40 file
ls src/views/*/*ListStates.test.ts | wc -l
npx vitest run src/views/**/*ListStates.test.ts        # Test Files 40 passed (40)
# A4 — guard adoption mới (AC-UX-070) + 7 guard cũ
npx vitest run src/views/listShellAdoption.test.ts src/views/detailTabBarAdoption.test.ts \
              src/router/uiListShellLot1Parity.test.ts src/router/uiAuditDocParity.test.ts \
              src/router/uiFixPlanParity.test.ts src/components/common/modalOverlayHygiene.test.ts \
              src/components/ui/uiPrimitiveHygiene.test.ts src/components/common/bareConfirmBudget.test.ts
# A6 — bộ dò KHÔNG đổi (57) và token khớp: chứng minh lô 3 vô hình với phép đo cũ
node scripts/ui-audit-inventory.mjs --summary | grep "Lỗi+Thử lại"      # ❌ 57
grep -o "\[NO-CON=[0-9]*\]" ../docs/ui-ux/00_AUDIT_HIEN_TRANG.md        # [NO-CON=57]
node scripts/ui-audit-inventory.mjs --check | grep "Lỗi+Thử lại"        # 0 ô lệch
# A8 — suite FULL, chấm DELTA bằng mắt (baseline hôm nay: 363 file)
npx vitest run
npx vue-tsc --noEmit
# A9 — 0 file .py
cd .. && git status --porcelain -- '*.py'                               # RỖNG
```

### 14.7 DoD lô 3 — 10 ô, thiếu 1 ô là CHƯA ĐÓNG

1. **A1** — `grep -L ListPageShell views/*/*ListView.vue | wc -l` = **0**; `grep -l` = **40**.
2. **A2** — 12 view lô 3 đúng khuôn 6 slot; **0** banner lỗi song song, **0** khối rỗng trùng
   (bảng «Khối phải XOÁ» §14.4 hết sạch), `/commissioning` giữ đúng 1 khối scoped.
3. **A3** — **đúng 12** file `*ListStates.test.ts` MỚI (28 → **40**), mã `TC-UX3-35…46`, mỗi file **≥ 6** TC
   ⇒ **≥ +72 TC**; 3 TC RED (j) đã ĐỎ trước khi sửa (dán output).
4. **A4** — guard mới `views/listShellAdoption.test.ts` (`AC-UX-070`) XANH với **non-adopter = 0**;
   **Prove-It**: thêm tạm 1 `*ListView.vue` không có khuôn **hoặc** gỡ 1 `import ListPageShell` ⇒ guard **ĐỎ**.
5. **A5** — `uiListShellLot1Parity.test.ts` mở rộng: sổ lô 3 đúng 12 dòng, `TC-UX3-35…46` liên tục,
   12 file test khai ở §14.6 tồn tại trên đĩa.
6. **A6** — bộ dò **vẫn 57** và token `[NO-CON=57]` **không đổi**; `--check` in `Lỗi+Thử lại 0`.
   (Nếu số này đổi ⇒ có ai đó chạm ô §3.1 ngoài phạm vi ⇒ dừng, báo BA.)
7. **A7** — 7 guard cũ XANH: `uiAuditDocParity` · `uiFixPlanParity` · `uiListShellLot1Parity` ·
   `uiDetailShellLot1Parity` · `modalOverlayHygiene` · `uiPrimitiveHygiene` · `bareConfirmBudget` ·
   `detailTabBarAdoption`.
8. **A8** — `npx vitest run` **0 ĐỎ**; mốc đo NGAY SAU bước BA (đọc bằng mắt, 2026-08-04):
   `Test Files 365 passed (365)` · `Tests 3638 passed (3638)` ⇒ nghiệm thu FE **≥ 377 file** và
   **≥ 3710 test**; `npx vue-tsc --noEmit` sạch.
9. **A9** — chữ hiển thị 100% tiếng Việt; **≥ 3 ảnh** Playwright ở `.playwright/eval/` cho `/audit-trail`
   và `/needs-requests` **ở trạng thái LỖI** (chặn API), đọc được câu lỗi **và** nút «Thử lại», **không** còn
   chữ «Chưa có…»/«Không có…».
10. **A10** — `git status --porcelain -- '*.py'` RỖNG · KHÔNG `bench migrate` · KHÔNG `git commit/push` ·
    `bash .claude/scripts/tidy-eval-artifacts.sh`, repo root 0 file scratch.

**Doc phải cập nhật CÙNG LƯỢT với mã** (guard sẽ đỏ nếu quên):
- `00 §6`: dòng `AC-UX-047` → **ĐÓNG HẲN** (giữ token `[NO-CON=57]` nguyên vẹn) + **thêm dòng `AC-UX-070`** +
  dòng tổng **69 → 70 mục** *(BA đã làm ở bước spec)*.
- `04 §10.1`: bảng tiến độ — dòng «Lô 3+ | 0 màn danh sách» sửa thành **lô 3 = 12 màn**, trạng thái theo kết
  quả FE *(BA đã sửa phần đính chính ở bước spec; FE chỉ lật trạng thái sang ĐÃ ĐÓNG)*.

### 14.8 Guard `AC-UX-070` — ngân sách adoption CHỈ-GIẢM (đã land ở bước BA)

`frontend/src/views/listShellAdoption.test.ts` — khuôn theo `bareConfirmBudget.test.ts` /
`detailTabBarAdoption.test.ts` (cặp + CHỈ-GIẢM hai chiều):

| Bất biến | Nội dung |
|---|---|
| `INV-UX3A-1` | Quét `views/**` đệ quy, tập `*ListView.vue` — hôm nay **40** file; mỗi file gắn cặp `(đường dẫn, adopter: boolean)` bằng dấu vân tay `from '@/components/ui/ListPageShell.vue'` |
| `INV-UX3A-2` | **Sổ non-adopter đóng băng**: mọi file KHÔNG áp khuôn phải nằm trong `NON_ADOPTER_BUDGET` (12 dòng hôm nay) ⇒ thêm `*ListView.vue` mới không có khuôn = **ĐỎ** |
| `INV-UX3A-3` | **Chiều ngược lại**: file trong sổ mà ĐÃ áp khuôn cũng **ĐỎ** («giảm mà quên hạ sổ») ⇒ FE bắt buộc xoá dòng khỏi sổ trong CÙNG lượt land ⇒ kết thúc lô 3 sổ **rỗng = non-adopter 0** |
| `INV-UX3A-4` | Mỗi file đã áp khuôn phải có `*ListStates.test.ts` cạnh nó (đặt tên `camelCase` của view) ⇒ adoption không kèm test = ĐỎ |
| `INV-UX3A-5` | **Bộ đếm công bố**: số adopter đọc từ đĩa == số ghi trong `02 §14.1` (bảng «Số chốt», cột «Sau lô 3») ⇒ doc không rot |

Guard XANH ở **cả hai đầu**: bước BA (sổ 12 dòng · 28 adopter) và sau khi FE land (sổ rỗng · 40 adopter).
Không tồn tại trạng thái trung gian mà cả mã lẫn doc đều "trông có vẻ đúng".

### 14.9 Quyết định kiến trúc

#### ADR-UX-23: Phép đo adoption tách khỏi phép đo bộ dò
- **Status**: Accepted — 2026-08-04 · **bổ sung** `ADR-UX-22` (không thay thế: token `[NO-CON=N]` vẫn neo vào bộ dò)
- **Context**: `ADR-UX-22` chốt «con số duy nhất được tin là bộ dò đo LIVE». Đúng cho *nợ trình bày*, nhưng bộ
  dò chấm theo **sự có mặt** của phần tử (`@retry`, chuỗi «Thử lại», khối rỗng) — nó **không thể** thấy hai
  khối cùng render. Hệ quả đã xảy ra: lô 2 tuyên bố «họ danh sách CUỐI CÙNG» trong khi **12** màn danh sách
  chưa áp khuôn và **2** trong số đó (`/audit-trail`, `/needs-requests`) in lỗi **kèm** câu rỗng.
- **Decision**: mỗi nợ diện rộng phải khai **phép đo riêng khớp với bất biến của nó**. Với adoption khuôn,
  phép đo là **cặp (file, adopter)** quét từ đĩa, khoá bằng guard CHỈ-GIẢM hai chiều (`AC-UX-070`) — **không**
  suy ra từ cột nào của bộ dò. Bộ dò giữ nguyên vai trò cho cột *Lỗi+Thử lại*.
- **Alternatives**: (a) nới bộ dò để phát hiện «hai khối cùng render» — cần phân tích AST của chuỗi
  `v-if/v-else-if`, đắt và giòn; (b) tin bộ dò và đóng `AC-UX-047` — chính là lỗi đang sửa; (c) đếm tay mỗi
  vòng — đã hỏng 3 lần (`AC-UX-052` «27/32», `AC-UX-005` «89 − flipped», `AC-UX-047` lô 2).
- **Consequences**: (+) tuyên bố «ĐÓNG HẲN» từ nay phải kèm **lệnh grep tái lập được**, không kèm cột bộ dò;
  (+) hồi quy adoption bị chặn tự động; (−) thêm 1 guard phải bảo trì; (−) hai nguồn số cùng tồn tại
  (bộ dò 57 · adoption 40/40) ⇒ **bắt buộc** ghi rõ *đại lượng nào* mỗi khi trích số (§14.1 bảng 2 dòng).

#### ADR-UX-24: «Cảnh báo bộ lọc» không được lật máy trạng thái danh sách
- **Status**: Accepted — 2026-08-04
- **Context**: `stores/imm08.ts:47-50` và `imm09.ts:39-43` đã tách sẵn `error` (nạp hỏng, không có gì để hiện)
  ⇄ `filterError` (khoá lọc lạ, **bảng vẫn giữ dữ liệu**). Khi gộp mọi thứ vào `:error-message` thì một bộ
  lọc gõ sai sẽ **xoá trắng** danh sách đang xem — đúng lỗi mà `INV-UX3-13` cấm.
- **Decision**: `:error-message` **chỉ** nhận lỗi lượt nạp danh sách. Cảnh báo bộ lọc render ở slot
  `#filters`, giữ `role="alert"` + nút «Đặt lại bộ lọc» riêng, `data-state` **vẫn** `content`.
- **Alternatives**: thêm prop `warning` vào `ListPageShell` — hoãn: 2 màn dùng, chưa đủ áp lực để nới hợp đồng
  primitive tầng 0 (`01 §3.0` luật dumb).
- **Consequences**: (+) không mất dữ liệu đang xem; (−) 2 màn có 2 vùng thông báo — chấp nhận, chúng khác
  ngữ nghĩa và test (h) khoá lại hành vi.

### 14.11 Biên bản LAND — đo lại từ đĩa 2026-08-04 (vòng 9, FE)

Mọi số dưới đây **đo lại sau khi 12 view đã sửa**, không chép từ kế hoạch.

| Phép đo | Lệnh | Trước | Sau |
|---|---|---|---|
| Non-adopter | `cd frontend/src && grep -L ListPageShell views/*/*ListView.vue` rồi đếm dòng | **12** | **0** |
| Adopter | `grep -l ListPageShell views/*/*ListView.vue` rồi đếm dòng | **28** | **40** |
| Test trạng thái | `ls src/views/*/*ListStates.test.ts` rồi đếm dòng | **28** | **40** |
| File test FE | `find src -name '*.test.ts'` rồi đếm dòng | **363** | **376** |
| Bộ dò, cột *Lỗi+Thử lại* | `node scripts/ui-audit-inventory.mjs --summary` | ❌ **57** | ❌ **57** (KHÔNG đổi — đúng dự báo §14.1) |
| Bộ dò, ô lệch | `node scripts/ui-audit-inventory.mjs --check` | **0** | **0** |
| File `.py` đổi | `git status --porcelain -- '*.py'` | rỗng | rỗng |

**Ba lệch so với spec — đã sửa THEO ĐĨA, ghi lại để lô sau không vấp lại:**

1. **`@/api/immXX` đoán sai ở 3 màn.** Bảng §14.2 gợi ý theo *store*, nhưng `import` thật khác:
   `listPmSchedules` nằm ở **`@/api/imm00`** (không phải `imm08`); `stores/imm15.ts` lấy
   `listCycleCounts` từ **`@/api/imm15`** trong khi view lấy `listWarehouses` từ `@/api/inventory`
   (⇒ phải mock **hai** module); IMM-09 là `listRepairWorkOrders` / `getRepairKPIs` (không phải
   `listRepairs` / `getRepairKpis`). Chú thích dưới bảng §14.2 đã cảnh báo đúng — **đọc `import`
   thật, đừng tin cột gợi ý**.
2. **Biến thể C → D ở màn 2, 6, 8.** Spec xếp `/cm/work-orders`, `/pm/work-orders`,
   `/needs-requests` vào biến thể **C** (bind thẳng `store.error`) vì lượt nạp danh sách có dọn ô
   lỗi ở đầu. Nhưng lời gọi **thứ hai** ghi vào CÙNG ô: `imm08.ts:205 fetchDashboardStats` (ghi cả
   `error` LẪN `loading`), `imm09.ts:160 fetchKPIs`, `imm01.ts:118 fetchKpis`. Nạp tuần tự KHÔNG
   cứu được — lỗi thẻ chỉ số đến **sau** khi bảng đã hiện vẫn lật màn sang trạng thái lỗi. ⇒ cả ba
   dùng **D** (chụp lỗi sau `await`), PM/CM thêm cờ `listLoading` riêng để lượt nạp chỉ số không
   làm bảng nháy về khung xương. Nguồn lỗi vẫn là `store.error` như spec, chỉ là đọc **an toàn hơn**;
   khoá bằng sub-case (h2) của 2 file test tương ứng.
3. **`/commissioning`: 1 khối rỗng, không phải 2.** Spec vừa cho phép **2** nguồn rỗng loại trừ nhau
   (INV-UX3-26) vừa đòi **0** `ui-empty` ở sub-case (i) — hai câu này không thể cùng đúng nếu không
   sửa `ListPageShell` (mà §14.3 cấm). Đã chọn hướng chặt hơn: **ĐÚNG 1** `EmptyState`, nội dung
   `empty-title`/`empty-hint` đổi theo **ba** nguyên nhân (rỗng-theo-thiết-bị / rỗng-do-lọc /
   rỗng-thật); `data-testid="list-empty-scoped"` **giữ nguyên tên** (§14.3) và nay bọc phần **hành
   động** (nút «Xoá bộ lọc thiết bị»). Bất biến người dùng cảm nhận được không đổi: rỗng vì lọc thiết
   bị vẫn nêu **mã thiết bị** + có **lối bỏ lọc**, và câu rỗng vô danh không hiện cùng lúc.

**Test coupling đã phải sửa cùng lượt (LL-FE-53 — đổi 1 nhãn SSoT vỡ test ở module khác):**
`views/commissioning/commissioningScopedEmpty.test.ts` (5 assert: câu rỗng chung, vị trí câu ngữ
cảnh, `role="status"`, ô đếm 2 → **1** vì khuôn phát ô đếm một lần ở `#toolbar`) ·
`views/eol/DecommissionList.render.test.ts` (câu rỗng) · `views/cm/cmListFilterErrorBanner.test.ts`
+ `views/pm/pmListFilterErrorBanner.test.ts` (`.alert-error` → `ui-error`, bất biến «lỗi 500 đi
nhánh lỗi, không bị nuốt thành cảnh báo lọc» giữ nguyên).

### 14.10 Rủi ro & việc để lại sau lô 3

| # | Rủi ro / nợ | Xử lý |
|---|---|---|
| 1 | Sau lô 3, `AC-UX-047` đóng ở **cả hai** phép đo cho họ `*ListView`; nợ 57 route còn lại **không** thuộc họ này | `AC-UX-048` (chi tiết) + lô riêng cho màn tạo/sửa/tiện ích |
| 2 | `stores/imm04.ts` / `imm06.ts` / `imm15.ts` dùng **1 ô `error`** cho nhiều danh sách + mọi hành động ghi | nợ tầng store; lô 3 né bằng biến thể D. Sửa store = **Ask-first**, sớm nhất khi tách `useListLoad()` |
| 3 | 40 màn lặp lại khuôn `reload()` + `loadError` | trích `useListLoad()` — Ask-first, giờ đã đủ mẫu (40 màn) để thiết kế |
| 4 | 4 pager tự viết (`/audit-trail`, `/service-contracts`, `/decommissions`, `/inventory/cycle-counts`) chưa dùng `BasePagination` | nợ a11y (`AC-UX-002` đã sửa `BasePagination`, 4 màn này không hưởng) — lô riêng |
| 5 | Cột *a11y* của 10/12 màn lô 3 vẫn ❌; *≤768px* của 4 màn (2, 6, 7, 9) vẫn ❌ | `AC-UX-006/007/038/039` — cấm gộp vào lô 3 |
| 6 | `frappeGet` trả `null` **không** ném lỗi (màn 3) — cùng mẫu có thể tồn tại ở màn khác | quét riêng `grep -rn "frappeGet" src/views` sau lô 3; nếu ≥3 màn thì mở mục sổ mới |
| 7 | Bộ dò không thấy được «hai khối cùng render» | `ADR-UX-23` chốt là **không** mở rộng bộ dò; guard adoption + test trạng thái là lối chứng minh |
