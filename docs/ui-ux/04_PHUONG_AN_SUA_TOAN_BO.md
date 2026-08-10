# Hợp đồng HỘP THOẠI (SSoT) + Phương án sửa TOÀN BỘ frontend — Core Doc VÒNG 5

| Mục | Giá trị |
|---|---|
| Phạm vi | Toàn FE — **cross-cutting, KHÔNG thuộc riêng IMM-XX** |
| Loại tài liệu | Core Doc vòng 5 (spec thi hành) **+ capstone** phương án cho 135 route còn lại |
| Owner | BA (đặc tả) · FE dev (thi hành) · QA (chấm bằng lệnh ở §7.4 và §12) |
| Trạng thái | Spec **ĐÃ CHỐT** — chờ FE code (Bước-4) |
| Ngày đo | 2026-07-31 (mọi con số đo lại từ đĩa, KHÔNG chép từ handoff) |
| Nhánh | `feature/hieuc/core-refinement` @ `3a6a391` |
| SSoT mã | `frontend/src/components/common/BaseModal.vue` · `frontend/src/composables/useFocusTrap.ts` (MỚI) |

## Tài liệu liên quan
- Bản đồ nợ gốc: [`00_AUDIT_HIEN_TRANG.md`](./00_AUDIT_HIEN_TRANG.md) — 148 route × 7 tiêu chí, sổ `AC-UX-*`, **ADR-UX-01…10** (§9)
- Tầng 0 (token + 8 primitive): [`01_DESIGN_SYSTEM.md`](./01_DESIGN_SYSTEM.md) — ADR-UX-04/05
- Khuôn màn danh sách: [`02_LIST_PAGE_SHELL.md`](./02_LIST_PAGE_SHELL.md) — ADR-UX-05
- Khuôn màn chi tiết: [`03_DETAIL_PAGE_SHELL.md`](./03_DETAIL_PAGE_SHELL.md) — ADR-UX-06/07
- Bộ đo lại (CHỈ ĐỌC): `frontend/scripts/ui-audit-inventory.mjs` (`--json` / `--summary` / `--check`)
- Chính sách chữ VI: `memory/ui_copy_language_policy.md` + `assetcore-fe` **LL-FE-53**
- Gate nút theo `allowed_transitions`: `assetcore-fe` **GATE-8 / LL-FE-51** (không hardcode `status ===`)

---

## §0. Phạm vi & Boundaries

Vòng 5 sửa **đúng một chỗ** (SSoT hộp thoại) và **viết phương án** cho phần còn lại. Không đụng màn nào.

**Always**
- Mọi hành vi bàn phím/a11y của hộp thoại cài **đúng 1 lần** tại `BaseModal.vue` + `useFocusTrap.ts`; 19 file tiêu thụ **thừa hưởng 0 dòng sửa**.
- Mọi chuỗi hiển thị mới là **tiếng Việt đầy đủ** (LL-FE-53); giữ `QR`/`PIN` + viết tắt VN thông dụng.
- Mọi bất biến khai ở §6 phải có **test render thật** (assert `document.activeElement`, KHÔNG assert số lần gọi hàm).
- Mọi con số trong tài liệu này đo bằng lệnh ghi kèm — vòng sau **đo lại**, chấm **DELTA**.

**Ask first (BA phải ratify trước khi làm)**
- Dời `BaseModal.vue` sang `components/ui/` hoặc biến nó thành primitive #9 (⇒ vỡ bất biến 0-churn — xem **ADR-UX-08**).
- Đổi/bỏ prop `title` `size` `danger`, slot `footer`, emit `close`, hoặc `data-testid="modal-card"` / `"modal-close"`.
- Thêm thư viện focus-trap ngoài (`focus-trap`, `@vueuse/core`…).
- Di trú bất kỳ file nào trong allowlist 30 (§5.2) sang `BaseModal` **trong vòng này**.

**Never**
- KHÔNG sửa 1 dòng nào trong 19 file tiêu thụ `BaseModal` (§3.4) — phải sửa view mới chạy được ⇒ **thiết kế sai, làm lại ở SSoT**.
- KHÔNG đụng `.py` / `stores/` / `api/` / `components/ui/` trong vòng này.
- KHÔNG đổi lớp CSS trên `[data-testid="modal-card"]` (4 test của `BaseModalResponsive.test.ts` khoá chuỗi class).
- KHÔNG thêm handler `Escape` thứ hai ở bất kỳ đâu trong `BaseModal.vue` (⇒ emit 2 lần, vỡ A3).

---

# PHẦN I — HỢP ĐỒNG HỘP THOẠI (SSoT)

## §1. Hiện trạng đo từ đĩa — bằng chứng phải sửa (2026-07-31)

### 1.1 `BaseModal.vue` (75 dòng) thiếu TOÀN BỘ hợp đồng hộp thoại

| Thiếu | Bằng chứng | Hậu quả người dùng |
|---|---|---|
| `role="dialog"` | `BaseModal.vue:29-39` — thẻ `[data-testid="modal-card"]` **0 thuộc tính ARIA** | Trình đọc màn hình đọc như một `div` thường: không báo "hộp thoại", không báo tiêu đề |
| `aria-modal="true"` | `grep -rn aria-modal src/` ⇒ **3 file** (`CommandPalette.vue`, `NotificationModal.vue`, `CalibrationDetailView.vue`) — **KHÔNG có** `BaseModal.vue` | Nội dung nền vẫn nằm trong cây đọc ⇒ người dùng "đọc xuyên" qua nền |
| `aria-labelledby` ⇄ `<h2>` | `BaseModal.vue:45-50` — `<h2>` **không có `id`** | Hộp thoại không tên |
| Đóng bằng `Escape` | `grep -n Escape BaseModal.vue` ⇒ **0 hit**; chỉ có `@click.self` (`:27`) + nút đóng (`:51-60`) | Bàn phím không đóng được; người dùng chuột mới thoát nhanh được |
| Bẫy focus | `grep -rlni "tabbable\|focusTrap" src/` ⇒ **đúng 1 file** `CommandPalette.vue` | Tab thứ N nhảy **ra sau nền**: người dùng bàn phím "biến mất" khỏi hộp thoại, vẫn kích hoạt được nút bị nền che |
| Trả focus về nơi mở | `grep -n "\.focus()" BaseModal.vue` ⇒ **0 hit** | Đóng hộp thoại ⇒ focus về `<body>`, mất chỗ đang làm; đọc lại từ đầu trang |
| Focus ban đầu | không có `onMounted` | Mở xong vẫn phải Tab từ đầu trang mới tới nội dung hộp thoại |

### 1.2 Bề mặt hộp thoại toàn FE — 3 lớp, chỉ 1 lớp có chủ

| Lớp | Số đo (lệnh) | Trạng thái a11y |
|---|---|---|
| Qua `BaseModal` | **36** lần `<BaseModal` trong **19** file `.vue` (`grep -ro "<BaseModal" src --include=*.vue \| wc -l`) | Thiếu **toàn bộ** hợp đồng ⇒ sửa 1 chỗ, khỏi 36 chỗ |
| Tự vẽ overlay | **30** file `fixed inset-0` không import `BaseModal` (§5.2) | `role="dialog"` **2/30** · có `Escape` **6/30** · bẫy focus **0/30** |
| Lai (vừa dùng vừa tự vẽ) | **4** file: `asset/AssetDetailView.vue` · `asset/DepreciationView.vue` · `calibration/CalibrationScheduleListView.vue` · `master-data/ReferenceDataView.vue` | Cùng 1 màn có 2 khuôn hộp thoại khác nhau ⇒ hành vi bàn phím không nhất quán |
| Hộp thoại **hệ điều hành** | **42** call-site / **28** file — đo lại 2026-08-04. Quét thô = **47/31**; **phải trừ 5 dòng chú thích** (công thức đủ ở [`06 §1.1`](./06_CONFIRM_DIALOG_SSOT.md)) | Không style được, nút OK/Cancel theo ngôn ngữ **trình duyệt** (vỡ LL-FE-53), không test render được |
| Hạ tầng thay thế — **KHÔNG chết** (đính chính 2026-08-04) | `composables/useModal.ts` là tầng **hàng đợi**; API của view là `composables/useNotify.ts:127` (uỷ nhiệm `modal.confirm`) — `grep -rn "notify\.confirm(" src/views` ⇒ **7** call-site / **5** view | Lối gọi đã đúng và đã có test; nợ nằm ở **độ phủ**, không ở hạ tầng (ADR-UX-16) |

> **Đọc số này đúng cách:** nợ hộp thoại **không** nằm ở 135 route mà nằm ở **1 file SSoT + 30 file tự chế**.
> Vì vậy vòng 5 sửa SSoT (rẻ, phủ 36 điểm) và **ghi phương án** cho 30 file kia (§10.6), không ôm luôn.

### 1.3 Baseline đo lúc bắt đầu vòng 5 (nguồn chấm DELTA — A10)

| Số đo | Giá trị | Lệnh |
|---|---|---|
| File test FE | **308** | `find frontend/src -name "*.test.ts" \| wc -l` |
| File `.vue` tiêu thụ `BaseModal` | **19** | `grep -rl "import BaseModal" frontend/src --include=*.vue \| wc -l` |
| File tự vẽ overlay (allowlist) | **30** | §5.2 |
| File lai | **4** | §5.3 |
| `BaseModalResponsive.test.ts` | **4** TC | `grep -c "  it(" …` |
| `CommandPalette.test.ts` | **7** TC | `grep -c "  it(" …` |
| Route thật / có view / redirect | **148 / 135 / 13** | `node frontend/scripts/ui-audit-inventory.mjs --summary` |

> ⚠️ **STATE ghi 300 file test là STALE** (ảnh chụp cuối vòng 2). Đo lại hôm nay = **308**. Chấm theo **DELTA**, không dừng vì lệch số tuyệt đối (LL: baseline trong prompt luôn có thể cũ).

---

## §2. Hợp đồng `frontend/src/composables/useFocusTrap.ts` (MỚI — nguồn DUY NHẤT)

### 2.0 Vị trí & luật tầng
- Đường dẫn **cố định**: `frontend/src/composables/useFocusTrap.ts`. Test co-located: `frontend/src/composables/useFocusTrap.test.ts`.
- Là **logic thuần DOM**: 0 import store, 0 router, 0 API, 0 component. Chỉ `vue` (`onBeforeUnmount`, `nextTick`, `Ref`).
- **Không** phải primitive `components/ui/` ⇒ `EXPECTED_PRIMITIVES` giữ **8**, `uiPrimitiveHygiene.test.ts` **không đổi** (xem ADR-UX-08).

### 2.1 API — khai đúng như dưới (đây là hợp đồng, không phải gợi ý)

```ts
import type { Ref } from 'vue'

export interface FocusTrapOptions {
  /** Phần tử gốc của vùng bẫy. Đọc TẠI THỜI ĐIỂM GỌI (ref có thể chưa gắn lúc setup). */
  container: Ref<HTMLElement | null>
  /** Có handler ⇒ composable tự đăng ký listener `keydown` trên `document` khi activate,
   *  và GỠ khi deactivate/unmount. Không truyền ⇒ KHÔNG đăng ký listener nào. */
  onEscape?: () => void
  /** Mặc định true — trả focus về phần tử đang focus TRƯỚC khi activate. */
  returnFocus?: boolean
  /** Phần tử focus đầu tiên. Mặc định = `tabbablesIn(container)[0]` ?? chính container. */
  initialFocus?: () => HTMLElement | null
}

export interface FocusTrap {
  /** Lưu opener → đẩy vào ngăn xếp → đăng ký listener (đồng bộ) → await nextTick → focus. */
  activate: () => Promise<void>
  /** Idempotent: gọi nhiều lần chỉ có tác dụng lần đầu. Gỡ listener + rời ngăn xếp + trả focus. */
  deactivate: () => void
  /** Gọi từ `@keydown` của container. Trả `true` nếu ĐÃ xử lý (đã `preventDefault`). */
  handleTabKey: (e: KeyboardEvent) => boolean
  /** Danh sách phần tử tab được trong container, tính lại mỗi lần gọi. */
  tabbables: () => HTMLElement[]
  /** Instance này có đang ở ĐỈNH ngăn xếp hộp thoại không. */
  isTopmost: () => boolean
}

export function useFocusTrap(options: FocusTrapOptions): FocusTrap

/** Dùng chung — KHÔNG nhân bản selector này ở bất kỳ file nào khác (guard §5.4 khoá). */
export function tabbablesIn(root: HTMLElement | null): HTMLElement[]

/** Sinh id duy nhất theo THỨ TỰ TẠO (module-scope counter). Không dùng `useId()` — xem ADR-UX-08. */
export function nextDialogId(prefix?: string): string
```

### 2.2 Thuật toán `tabbablesIn` — và **bẫy jsdom** phải né

```ts
const TABBABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')
```

Lọc "đang hiển thị" **KHÔNG được dùng `offsetParent !== null`**:

- jsdom **không cài layout** ⇒ `offsetParent` luôn `null` cho MỌI phần tử ⇒ danh sách rỗng ⇒ A4 đỏ vĩnh viễn.
- Mã cũ trong `CommandPalette.vue:113` phải "vá" bằng `|| el === inputEl.value` chính vì bẫy này — **đừng chép lại cái vá đó**.

Luật thay thế (chạy đúng ở cả jsdom lẫn trình duyệt):

```ts
function isVisible(el: HTMLElement): boolean {
  if (el.hasAttribute('hidden') || el.closest('[hidden]')) return false
  if (el.getAttribute('aria-hidden') === 'true') return false
  const s = typeof getComputedStyle === 'function' ? getComputedStyle(el) : null
  return !s || (s.display !== 'none' && s.visibility !== 'hidden')
}
```

- Thứ tự = **thứ tự DOM** (`querySelectorAll`). `tabindex` **dương** cố ý KHÔNG hỗ trợ (dự án 0 hit `tabindex="1"`+) — ghi ở §8.5 là giới hạn đã biết.
- Giới hạn đã biết #2: phần tử bị **cha** `display:none` che ở trình duyệt thật vẫn lọt (computed style của con không phải `none`). Chấp nhận: nội dung hộp thoại theo thiết kế là đang hiển thị.

### 2.3 Ngăn xếp hộp thoại (topmost) — vì sao bắt buộc

2 hộp thoại mở đồng thời (A1 yêu cầu id không trùng ⇒ tình huống này là THẬT):
nếu cả hai cùng nghe `Escape` trên `document` thì 1 lần nhấn đóng **cả hai** và `handleTabKey` của hộp dưới cũng cướp Tab.

```ts
const stack: symbol[] = []                 // module-scope, dùng chung mọi instance
// activate:   stack.push(token)
// deactivate: stack.splice(stack.indexOf(token), 1)
// isTopmost:  stack[stack.length - 1] === token
```

`onEscape` và `handleTabKey` **chỉ chạy khi `isTopmost()`**.

### 2.4 Khuôn cài đặt tham chiếu

```ts
export function useFocusTrap(options: FocusTrapOptions): FocusTrap {
  const token = Symbol('ac-focus-trap')
  let active = false
  let opener: HTMLElement | null = null

  const isTopmost = () => stack[stack.length - 1] === token
  const tabbables = () => tabbablesIn(options.container.value)

  function onDocKeydown(e: KeyboardEvent): void {
    if (e.key !== 'Escape' || !isTopmost()) return
    e.preventDefault()
    options.onEscape?.()
  }

  async function activate(): Promise<void> {
    if (active) return
    active = true
    opener = (document.activeElement as HTMLElement) ?? null
    stack.push(token)
    if (options.onEscape) document.addEventListener('keydown', onDocKeydown)  // ĐỒNG BỘ
    await nextTick()
    const target = options.initialFocus?.() ?? tabbables()[0] ?? options.container.value
    target?.focus()
  }

  function deactivate(): void {
    if (!active) return
    active = false
    if (options.onEscape) document.removeEventListener('keydown', onDocKeydown)
    const i = stack.indexOf(token)
    if (i >= 0) stack.splice(i, 1)
    if (options.returnFocus !== false && opener && document.contains(opener)) opener.focus()
    opener = null
  }

  function handleTabKey(e: KeyboardEvent): boolean {
    if (e.key !== 'Tab' || !isTopmost()) return false
    const items = tabbables()
    if (items.length === 0) { e.preventDefault(); return true }
    const first = items[0]
    const last = items[items.length - 1]
    const root = options.container.value
    const el = document.activeElement as HTMLElement | null
    const outside = !root || !el || !root.contains(el)
    if (e.shiftKey && (outside || el === first)) { e.preventDefault(); last.focus(); return true }
    if (!e.shiftKey && (outside || el === last)) { e.preventDefault(); first.focus(); return true }
    return false
  }

  onBeforeUnmount(deactivate)
  return { activate, deactivate, handleTabKey, tabbables, isTopmost }
}
```

**Bất biến cài đặt:** `activate()` đăng ký listener **đồng bộ** (trước `await nextTick()`) — nếu đăng ký sau `await`, nhấn `Escape` ngay nhịp đầu sẽ rơi vào khoảng chết.

---

## §3. Hợp đồng `frontend/src/components/common/BaseModal.vue`

> 🔗 **MỞ RỘNG VÒNG 6 (đã thi hành 2026-08-03) — lỗi CHẶN hành động hiện INLINE.**
> Hợp đồng `BaseModal` được **CHỈ THÊM** hai prop tuỳ chọn `error?: string | null` và
> `errorTitle?: string`; markup vùng lỗi nằm ở component tier-1 mới
> `frontend/src/components/common/ModalInlineError.vue` (ADR-UX-14). Đặc tả đầy đủ +
> lô 1 adoption (5 file / 8 hộp thoại) + hợp đồng làm sạch câu lỗi tại `api/axios.ts`:
> [`05_MODAL_INLINE_ERROR.md`](./05_MODAL_INLINE_ERROR.md).
>
> | Sổ | Nội dung | Trạng thái |
> |---|---|---|
> | **AC-UX-062** | Lỗi CHẶN hiện inline trong hộp thoại (`role="alert"`, không tự tắt, hộp thoại không đóng) | **ĐÓNG vòng 6** — SSoT + lô 1 (5 file / 8 hộp thoại); nợ còn lại = 10 file (guard `modalInlineErrorAdoption.test.ts`, CHỈ-GIẢM) |
> | **AC-UX-063** | Làm sạch câu lỗi 400/417/422 tại một cửa `parseServerMessages` (`sanitizeBusinessMessage`), log thô chỉ khi DEV | **ĐÓNG vòng 6** — 3 cửa còn lại (404/409/mặc định) ghi nợ ở `05 §11` |
>
> **Bất biến 0-churn §3.1 dưới đây vẫn áp nguyên** cho vòng 6: 4 tệp test hộp thoại
> (`BaseModalA11y` · `BaseModalDialog` · `BaseModalResponsive` · `modalOverlayHygiene`)
> XANH với **0 dòng sửa** — chấm bằng **md5 chốt** (`05 §2.3`), KHÔNG bằng
> `git diff --stat` (3/4 tệp untracked ⇒ luôn rỗng = xanh giả).

### 3.1 Bất biến 0-churn (điều kiện tồn tại của cả vòng)
Hợp đồng đối ngoại **giữ nguyên tuyệt đối**: prop `title: string` · `size?: 'sm'|'md'|'lg'|'xl'` · `danger?: boolean`; slot mặc định + slot `footer`; emit `close`; `data-testid` `modal-card` / `modal-close`; **toàn bộ chuỗi class** trên `modal-card` và nút đóng.
⇒ 19 file tiêu thụ (§3.4) **0 dòng đổi**. Nếu buộc phải sửa view mới chạy ⇒ **thiết kế sai, làm lại ở SSoT**.

### 3.2 Delta chính xác so với mã hiện tại

| # | Vị trí | Delta |
|---|---|---|
| D1 | `<script setup>` | `import { ref, onMounted } from 'vue'` + `import { useFocusTrap, tabbablesIn, nextDialogId } from '@/composables/useFocusTrap'` |
| D2 | `<script setup>` | `const cardEl = ref<HTMLElement \| null>(null)` |
| D3 | `<script setup>` | `const titleId = nextDialogId('ac-modal-title')` — **theo instance**, 2 hộp thoại đồng thời KHÔNG trùng |
| D4 | `<script setup>` | `const trap = useFocusTrap({ container: cardEl, onEscape: onClose, initialFocus: firstFocusTarget })` |
| D5 | `<script setup>` | `onMounted(() => { void trap.activate() })` — **KHÔNG** gọi `deactivate` thủ công (composable tự gỡ ở `onBeforeUnmount`) |
| D6 | `<script setup>` | `function onKeydown(e: KeyboardEvent) { trap.handleTabKey(e) }` |
| D7 | thẻ `modal-card` | thêm `ref="cardEl"` · `role="dialog"` · `aria-modal="true"` · `:aria-labelledby="titleId"` · `tabindex="-1"` · `@keydown="onKeydown"` — **`:class` giữ NGUYÊN** |
| D8 | `<h2>` | thêm `:id="titleId"` (giữ nguyên class + `{{ title }}`) |
| D9 | div thân bài (`:64`) | thêm `data-testid="modal-body"` (phục vụ D10 + test; additive) |
| D10 | `<script setup>` | hàm chọn focus ban đầu (bên dưới) |

```ts
// Thứ tự chọn focus ban đầu — KHÔNG chọn nút đóng nếu còn lựa chọn khác:
// nút đóng nằm ĐẦU DOM, focus vào đó thì gõ Enter theo phản xạ = đóng nhầm hộp thoại.
function firstFocusTarget(): HTMLElement | null {
  const root = cardEl.value
  if (!root) return null
  const auto = root.querySelector<HTMLElement>('[data-autofocus]')
  if (auto) return auto
  const closeBtn = root.querySelector<HTMLElement>('[data-testid="modal-close"]')
  const rest = tabbablesIn(root).filter((el) => el !== closeBtn)
  return rest[0] ?? closeBtn ?? root
}
```

### 3.3 Khuôn template sau khi sửa (phần đổi)

```html
<div
  ref="cardEl"
  data-testid="modal-card"
  role="dialog"
  aria-modal="true"
  :aria-labelledby="titleId"
  tabindex="-1"
  :class="[ /* NGUYÊN VĂN như hiện tại — không thêm/bớt 1 ký tự */ ]"
  @keydown="onKeydown"
>
  …
  <h2 :id="titleId" class="text-lg font-semibold" :class="danger ? 'text-red-700' : 'text-slate-800'">
    {{ title }}
  </h2>
  …
  <div data-testid="modal-body" class="flex-1 overflow-y-auto px-6 py-5"><slot /></div>
```

### 3.4 Tập ĐÓNG BĂNG — 19 file tiêu thụ, `git diff --stat` = 0 dòng (A2)

```
frontend/src/views/asset/AssetDetailView.vue
frontend/src/views/asset/AssetLabelPrintView.vue
frontend/src/views/asset/DepreciationView.vue
frontend/src/views/auth/UserProfileFormView.vue
frontend/src/views/calibration/CalibrationScheduleListView.vue
frontend/src/views/compliance/ComplianceRuleDetailView.vue
frontend/src/views/compliance/ComplianceRuleListView.vue
frontend/src/views/compliance/FindingDetailView.vue
frontend/src/views/compliance/InternalAuditDetailView.vue
frontend/src/views/compliance/InternalAuditListView.vue
frontend/src/views/compliance/ManagementReviewDetailView.vue
frontend/src/views/compliance/ManagementReviewListView.vue
frontend/src/views/document/FirmwareCrDetailView.vue
frontend/src/views/incident/CAPADetailView.vue
frontend/src/views/incident/RCADetailView.vue
frontend/src/views/inventory/CycleCountDetailView.vue
frontend/src/views/master-data/ReferenceDataView.vue
frontend/src/views/needs/NeedsRequestDetailView.vue
frontend/src/views/procurement/AvlListView.vue
```

> **Self-correction BA — đề bài ghi "20 file", đĩa đếm được 19.** Lệnh:
> `grep -rl "import BaseModal" frontend/src --include=*.vue | wc -l` ⇒ **19**.
> File thứ 20 trong danh sách của PM là `frontend/src/components/common/BaseModalResponsive.test.ts`
> (file `.ts` duy nhất còn lại có chuỗi `BaseModal`) — **cũng đóng băng** vì A7 yêu cầu nó xanh 4/4 mà không sửa.
> **`CommandPalette.vue` KHÔNG thuộc tập này**: nó chỉ nhắc `BaseModal` trong **chú thích** (`:2`), không import;
> nếu ai đóng băng nhầm nó thì A2 và A6 (di trú CommandPalette) **loại trừ nhau**.
> ⇒ Tập đóng băng chính thức = **19 `.vue` + `BaseModalResponsive.test.ts` = 20 đường dẫn**.

---

## §4. Di trú `CommandPalette.vue` — no-fork (A6)

| # | Vị trí hiện tại | Delta |
|---|---|---|
| M1 | `:109-114` `function tabbables()` | **XOÁ** — thay bằng `trap.tabbables()` của composable (cả cái vá `el === inputEl.value`) |
| M2 | `:132-144` `case 'Tab': { … }` | **XOÁ** thân khối — còn `case 'Tab': trap.handleTabKey(e); break` |
| M3 | `:20` `let returnFocusEl` · `:63` · `:67-73` · `:152` | **XOÁ** — return-focus do composable lo |
| M4 | `:61-74` `watch(open, …)` | mở ⇒ `activeIndex.value = 0; void trap.activate()`; đóng ⇒ `trap.deactivate()` |
| M5 | `<script setup>` | `const trap = useFocusTrap({ container: dialogEl, initialFocus: () => inputEl.value })` — **KHÔNG truyền `onEscape`** |
| M6 | `:118-121` `case 'Escape'` | **GIỮ NGUYÊN** (`store.closePalette()`) |

**Vì sao M5 không truyền `onEscape`:** CommandPalette đã tự xử lý `Escape` trong `switch` của nó (`:118`). Truyền thêm `onEscape` ⇒ **2 handler** ⇒ `closePalette()` chạy 2 lần và TC-CMDK-10 «Escape → đóng palette» dễ trở nên nhập nhằng. Một hộp thoại **chỉ được có đúng 1 chủ sở hữu phím Escape**.

**Hành vi đổi có chủ đích (ghi để QA không coi là regression):** bộ lọc "đang hiển thị" đổi từ `offsetParent` sang `isVisible()` (§2.2) ⇒ ở trình duyệt thật, danh sách tabbable của palette có thể **rộng hơn** trước. 7 TC hiện có không chạm Tab (chúng phủ Arrow/Enter/Escape/Home/End + 3 TC vai trò ARIA) ⇒ **phải xanh 7/7 nguyên trạng**.

---

## §5. Guard vệ sinh overlay — `frontend/src/components/common/modalOverlayHygiene.test.ts` (MỚI)

### 5.1 Nguyên tắc
Guard **CHỈ-GIẢM**: con số đóng băng là **trần**, không phải mục tiêu. File mới tự vẽ overlay ⇒ **ĐỎ**. Di trú bớt 1 file ⇒ xoá 1 dòng allowlist (số giảm) ⇒ vẫn xanh.

### 5.2 `ALLOWLIST_SELF_DRAWN` — đóng băng ở **30**
Định nghĩa: file `.vue` dưới `frontend/src` có chuỗi `fixed inset-0`, **không** import `BaseModal`, **trừ** 4 file khung
(`components/common/BaseModal.vue` · `LoadingSpinner.vue` · `AppLayout.vue` · `AppTopBar.vue` — overlay của chúng không phải hộp thoại).

```
src/components/commissioning/SubmitForApprovalModal.vue
src/components/commissioning/WorkflowActions.vue
src/components/common/NotificationModal.vue
src/components/import/ImportWizardModal.vue
src/views/asset/AssetTransferDetailView.vue
src/views/asset/DeviceModelFormView.vue
src/views/asset/DeviceModelListView.vue
src/views/audit/AuditTrailListView.vue
src/views/calibration/CalibrationDetailView.vue
src/views/cm/CMWorkOrderDetailView.vue
src/views/commissioning/CommissioningDetailView.vue
src/views/document/DocumentDetailView.vue
src/views/document/DocumentRequestListView.vue
src/views/document/FirmwareCrListView.vue
src/views/incident/IncidentDetailView.vue
src/views/inventory/SparePartDetailView.vue
src/views/inventory/SparePartListView.vue
src/views/inventory/UomConversionView.vue
src/views/inventory/WarehouseDetailView.vue
src/views/inventory/WarehouseListView.vue
src/views/inventory/WatchlistView.vue
src/views/master-data/SlaPolicyListView.vue
src/views/needs/ProcurementPlanListView.vue
src/views/pm/PMCalendarView.vue
src/views/pm/PmScheduleListView.vue
src/views/pm/PmTemplateListView.vue
src/views/pm/PMWorkOrderDetailView.vue
src/views/purchase/PurchaseDetailView.vue
src/views/training/CompetencyDetailView.vue
src/views/training/SessionDetailView.vue
```

### 5.3 `ALLOWLIST_HYBRID` — đóng băng ở **4**
File **vừa** import `BaseModal` **vừa** tự vẽ overlay (lỗ hổng của luật §5.2 — nếu không khoá riêng thì cứ thêm 1 `import BaseModal` là thoát guard):

```
src/views/asset/AssetDetailView.vue
src/views/asset/DepreciationView.vue
src/views/calibration/CalibrationScheduleListView.vue
src/views/master-data/ReferenceDataView.vue
```

### 5.4 Bất biến no-fork (khoá A6 bằng mã, không bằng lời hứa)
- `composables/useFocusTrap.ts` là file **DUY NHẤT** chứa chuỗi selector `[tabindex]:not([tabindex="-1"])` trong toàn `frontend/src` (trừ file test của chính nó).
- `CommandPalette.vue`: **0 hit** `function tabbables` · **0 hit** `returnFocusEl` · **≥1 hit** `useFocusTrap`.
- `BaseModal.vue`: **≥1 hit** `useFocusTrap` · **0 hit** `addEventListener` (ESC do composable lo, không tự đăng ký).

### 5.5 Giới hạn đã biết của guard (ghi rõ để không ai tưởng nó phủ hết)
Guard bắt overlay khai bằng **utility class** `fixed inset-0`. Overlay khai bằng **CSS scoped** (`position: fixed; inset: 0`) **không** bị bắt — hiện có đúng 1 ca hợp lệ là `CommandPalette.vue` (đã có `role="dialog"` + bẫy focus). Mở rộng guard sang `<style>` block ⇒ `[ROADMAP Đợt E]`, không làm ở vòng 5.

---

## §6. Bất biến đo được (INV-UX5-*)

| Mã | Bất biến | Cách chứng minh |
|---|---|---|
| **INV-UX5-1** | `[data-testid="modal-card"]` luôn có `role="dialog"` + `aria-modal="true"` | mount thật, đọc thuộc tính |
| **INV-UX5-2** | `aria-labelledby` **bằng đúng** `id` của `<h2>` tiêu đề | `expect(card.attributes('aria-labelledby')).toBe(h2.attributes('id'))` — **so khớp giá trị**, không chỉ tồn tại |
| **INV-UX5-3** | 2 hộp thoại đồng thời ⇒ 2 `id` **khác nhau** | mount 2 instance, so `id` |
| **INV-UX5-4** | `Escape` ⇒ emit `close` **đúng 1 lần**; sau `unmount` ⇒ **không** emit thêm | đếm `wrapper.emitted('close')!.length` trước/sau unmount |
| **INV-UX5-5** | Mở ⇒ `document.activeElement` nằm **trong** `modal-card` | `expect(card.element.contains(document.activeElement)).toBe(true)` |
| **INV-UX5-6** | Tab ở phần tử cuối ⇒ về đầu; Shift+Tab ở đầu ⇒ về cuối | assert `document.activeElement` **thật** |
| **INV-UX5-7** | Đóng/unmount ⇒ focus trở lại **đúng** phần tử đã mở | `expect(document.activeElement).toBe(opener)` |
| **INV-UX5-8** | 19 file tiêu thụ + `BaseModalResponsive.test.ts` = **0 dòng đổi** | `git diff --stat -- <20 đường dẫn>` |
| **INV-UX5-9** | Số file tự vẽ overlay **≤ 30**, tập con của allowlist | guard §5.2 |
| **INV-UX5-10** | Số file lai **≤ 4**, tập con của allowlist | guard §5.3 |
| **INV-UX5-11** | Logic Tab-wrap + return-focus tồn tại **đúng 1 nơi** | guard §5.4 |
| **INV-UX5-12** | Mọi route có view trong `00 §3.1` thuộc **đúng 1** nhóm ở §11 | guard §12 |
| **INV-UX5-13** | Hộp thoại **không** giành `Escape` khi không ở đỉnh ngăn xếp | 2 trap lồng nhau, ESC chỉ đóng cái trên |

---

## §7. Test-case & lệnh chấm

### 7.1 `frontend/src/composables/useFocusTrap.test.ts` (MỚI — ≥10 TC)
Mount **component thật** (định nghĩa tại chỗ trong test) với `attachTo: document.body`; **không** mock DOM.

| TC | Nội dung | Bất biến |
|---|---|---|
| TC-UX5-01 | `tabbablesIn` trả đúng thứ tự DOM, bỏ `[disabled]`, bỏ `tabindex="-1"` | §2.2 |
| TC-UX5-02 | `tabbablesIn` **không** rỗng trong jsdom (chống bẫy `offsetParent`) | §2.2 |
| TC-UX5-03 | `activate()` focus phần tử đầu (hoặc `initialFocus`) | INV-UX5-5 |
| TC-UX5-04 | Tab ở CUỐI → quay về ĐẦU (assert `document.activeElement`) | INV-UX5-6 |
| TC-UX5-05 | Shift+Tab ở ĐẦU → về CUỐI | INV-UX5-6 |
| TC-UX5-06 | focus đang **ngoài** container + Tab → về ĐẦU | §2.4 |
| TC-UX5-07 | `deactivate()` trả focus về opener | INV-UX5-7 |
| TC-UX5-08 | `deactivate()` gọi 2 lần **không** ném lỗi, không focus lại lần 2 | idempotent |
| TC-UX5-09 | `onEscape` chạy 1 lần; sau `unmount` dispatch tiếp ⇒ **0 lần** | INV-UX5-4 |
| TC-UX5-10 | 2 trap lồng nhau: ESC chỉ chạy `onEscape` của trap TRÊN; sau khi trap trên `deactivate`, ESC chạy của trap dưới | INV-UX5-13 |
| TC-UX5-11 | container rỗng (0 tabbable) + Tab ⇒ `preventDefault`, không ném lỗi | §2.4 |
| TC-UX5-12 | `nextDialogId()` sinh chuỗi khác nhau qua các lần gọi | INV-UX5-3 |

### 7.2 `frontend/src/components/common/BaseModalDialog.test.ts` (MỚI — ≥8 TC)

| TC | Nội dung | Acceptance |
|---|---|---|
| TC-UX5-20 | `role="dialog"` + `aria-modal="true"` trên `modal-card` | A1 |
| TC-UX5-21 | `aria-labelledby` **=== `id` của `<h2>`**, và `<h2>` chứa `title` | A1 |
| TC-UX5-22 | 2 modal mount đồng thời ⇒ `id` khác nhau (và `aria-labelledby` mỗi cái trỏ `<h2>` của CHÍNH nó) | A1 |
| TC-UX5-23 | Escape ⇒ `emitted('close')` có **đúng 1** phần tử | A3 |
| TC-UX5-24 | `unmount()` rồi dispatch Escape ⇒ tổng số emit **không tăng** | A3 |
| TC-UX5-25 | Mở ⇒ `card.element.contains(document.activeElement)` | A4 |
| TC-UX5-26 | Focus ban đầu **không** rơi vào `modal-close` khi thân bài có phần tử tab được | §3.2 D10 |
| TC-UX5-27 | Tab ở cuối → đầu; Shift+Tab ở đầu → cuối (dispatch trên `modal-card`) | A4 |
| TC-UX5-28 | opener (nút ngoài, đã `attachTo` body) được focus lại sau `unmount()` | A5 |
| TC-UX5-29 | Nhấn nút `modal-close` vẫn emit `close` (hợp đồng cũ) | A7 |

**Khuôn mount bắt buộc** (sai khuôn ⇒ focus không chạy trong jsdom):
```ts
const opener = document.createElement('button')
document.body.appendChild(opener)
opener.focus()
const w = mount(BaseModal, {
  props: { title: 'Tiêu đề' },
  slots: { default: '<button id="a">A</button><button id="b">B</button>' },
  attachTo: document.body,                      // BẮT BUỘC — không attach thì .focus() vô nghĩa
  global: { stubs: { teleport: true } },        // giữ nội dung trong wrapper để find() thấy
})
await nextTick()                                 // activate() await nextTick trước khi focus
```

### 7.3 `frontend/src/components/common/modalOverlayHygiene.test.ts` (MỚI — ≥5 TC)
TC-UX5-30 allowlist 30 (chỉ-giảm) · TC-UX5-31 hybrid 4 (chỉ-giảm) · TC-UX5-32 no-fork selector duy nhất · TC-UX5-33 `CommandPalette` sạch 3 dấu vết cũ · TC-UX5-34 `BaseModal` không tự `addEventListener`.

### 7.4 Lệnh chấm (QA **tự đo lại**, không nhận báo cáo suông)

```bash
cd frontend

# A1/A3/A4/A5 — hợp đồng hộp thoại
npx vitest run src/components/common/BaseModalDialog.test.ts src/composables/useFocusTrap.test.ts

# A2 — thừa hưởng 0-churn. CHẠY Ở GỐC REPO (không phải trong frontend/):
cd /home/miyano/frappe-bench/apps/assetcore
FROZEN=$(sed -n '/^frontend\/src\/views\//p' docs/ui-ux/04_PHUONG_AN_SUA_TOAN_BO.md)
echo "$FROZEN" | wc -l                                   # PHẢI = 19 (danh sách §3.4)
git diff --stat -- $FROZEN frontend/src/components/common/BaseModalResponsive.test.ts   # PHẢI RỖNG
cd frontend

# A6 — no-fork + 7 TC cũ
npx vitest run src/components/common/CommandPalette.test.ts        # 7/7
grep -c "function tabbables\|returnFocusEl" src/components/common/CommandPalette.vue   # 0
grep -c "useFocusTrap" src/components/common/CommandPalette.vue                        # >=1

# A7 — cổng responsive của vòng
npx vitest run src/components/common/BaseModalResponsive.test.ts   # 4/4

# A8 — guard vệ sinh
npx vitest run src/components/common/modalOverlayHygiene.test.ts

# A9 — mutation test 2 chiều (BẮT BUỘC ghi lại output cả 2 lần)
printf '<template>\n  <div class="fixed inset-0"></div>\n</template>\n' \
  > src/components/common/__mutation_probe_overlay.vue
npx vitest run src/components/common/modalOverlayHygiene.test.ts   # PHẢI ĐỎ, nêu đúng tên file
rm src/components/common/__mutation_probe_overlay.vue
npx vitest run src/components/common/modalOverlayHygiene.test.ts   # PHẢI XANH lại

# A10 — delta suite (308 + 4 file mới = 312)
find src -name "*.test.ts" | wc -l
npx vitest run                                                      # 0 file đỏ
npm run typecheck

# A11 — không đụng backend
git status --short -- '*.py'                                        # RỖNG

# A12 — capstone parity
npx vitest run src/router/uiFixPlanParity.test.ts src/router/uiAuditDocParity.test.ts
```

---

## §8. Bẫy đã biết — ĐỌC TRƯỚC KHI CODE

1. **`offsetParent` trong jsdom luôn `null`** ⇒ mọi bộ lọc "đang hiển thị" dựa trên nó cho **danh sách rỗng** ⇒ A4 đỏ mà nhìn mã thì "đúng". Dùng `isVisible()` ở §2.2. Đây chính là lý do `CommandPalette.vue:113` phải vá `|| el === inputEl.value`.
2. **`useId()` của Vue 3.5 đếm theo APP** — 2 lần `mount()` trong cùng file test tạo 2 app khác nhau và **cùng** cho `v-0` ⇒ TC-UX5-22 (id không trùng) đỏ oan. Dùng `nextDialogId()` (đếm theo module).
3. **`.focus()` không có tác dụng nếu component chưa gắn vào `document`** ⇒ mọi test focus phải `attachTo: document.body`.
4. **`stubs: { teleport: true }`** giữ nội dung trong wrapper. Bỏ stub thì `wrapper.find('[data-testid="modal-card"]')` **không thấy gì** (nội dung đã bay sang `document.body`).
5. **`activate()` là async** (await `nextTick`) ⇒ test phải `await nextTick()` (hoặc `await flushPromises()`) trước khi assert `document.activeElement`.
6. **Đăng ký listener phải ĐỒNG BỘ**, focus mới cần `nextTick` — đảo thứ tự là mất phím Escape ở nhịp đầu.
7. **Hai handler Escape = 2 lần emit.** Nếu thêm `@keydown.esc` trên `modal-card` "cho chắc" thì A3 đỏ ngay.
8. **`deactivate()` phải idempotent** — nó bị gọi cả từ `onBeforeUnmount` lẫn (ở CommandPalette) từ `watch(open)`.
9. **Trả focus phải chạy TRƯỚC khi DOM biến mất**: đặt trong `onBeforeUnmount`, không phải `onUnmounted`.
10. **`BaseModal` được ~36 chỗ dùng**: auto-focus lúc mở làm `document.activeElement` đổi trong nhiều test cũ đang mount view có modal. Nếu có test cũ đỏ ⇒ **đọc kỹ**: nếu nó assert focus thì sửa test; nếu nó đỏ vì lý do khác thì hoàn nguyên và báo BA (đừng "sửa cho xanh").
11. **`git diff --stat` trên tập đóng băng phải chạy SAU khi code xong**, không phải trước — và tính cả file test đóng băng.
12. **Guard đọc mã nguồn phải bỏ comment trước khi so** (khuôn `stripComments` đã có ở `uiPrimitiveHygiene.test.ts:53`), nếu không chú thích «KHÔNG dùng BaseModal» của `CommandPalette.vue:2` sẽ bị đếm nhầm.

---

# PHẦN II — PHƯƠNG ÁN SỬA TOÀN BỘ (capstone)

## §9. Nguyên tắc phân hoạch

### 9.1 Vì sao nhóm theo **khuôn** chứ không theo module
Nợ đo được (00 §2.1) tập trung ở 4 tiêu chí *Lỗi+Thử lại · Xương · a11y · Rỗng* — đây là **thuộc tính của khuôn màn**, không phải của nghiệp vụ. Sửa theo module (IMM-04 rồi IMM-08…) buộc mỗi lô phải dựng lại cả 4 khuôn; sửa theo khuôn thì **khuôn dựng 1 lần, áp N lần** — đúng cách 3 vòng vừa rồi đã chạy (`ListPageShell` vòng 3, `DetailPageShell` vòng 4, `BaseModal` vòng 5).

### 9.2 Luật gán nhóm (tất định — ai chạy lại cũng ra cùng kết quả)
Theo **tên file view** (`00 §3.1` cột 3):

| Nhóm | Luật | Số route |
|---|---|---|
| **Danh sách** | tên file kết thúc `ListView.vue` | 40 |
| **Chi tiết** | kết thúc `DetailView.vue` | 34 |
| **Biểu mẫu** | kết thúc `CreateView.vue` / `EditView.vue` / `FormView.vue` | 23 |
| **Bảng điều khiển** | kết thúc `DashboardView.vue`, hoặc tên chứa `Calendar` / `Heatmap` | 8 |
| **Khác** | phần còn lại (xác thực, công cụ, bước quy trình, màn hệ thống) | 30 |
| | **Tổng** | **135** |

13 route `redirect` **không có giao diện riêng** ⇒ ngoài phạm vi (mẫu số luôn là **135**, đúng như `00 §2.1`).

### 9.3 Luật gán đợt

| Đợt | Nội dung | Số route |
|---|---|---|
| **A** | **Mọi route mức đau P0**, bất kể nhóm — làn ưu tiên | 11 |
| **B** | Nhóm *Danh sách* còn lại (khuôn `ListPageShell` đã có ⇒ rẻ nhất) | 40 |
| **C** | Nhóm *Chi tiết* còn lại (khuôn `DetailPageShell` đã có) | 32 |
| **D** | Nhóm *Biểu mẫu* còn lại (**phải dựng `FormField` + `IconButton` trước** — AC-UX-039) | 19 |
| **E** | *Bảng điều khiển* + *Khác* còn lại (phần lớn chưa có khuôn) | 33 |

**Bất biến:** `đợt == 'A'` ⟺ `đau == 'P0'` (guard §12 kiểm tra 2 chiều).

### 9.4 Đơn giá ước lượng — suy ra từ 2 vòng đã chạy, KHÔNG bịa
- Vòng 3 đóng **4** màn danh sách + dựng 1 primitive trong 1 vòng.
- Vòng 4 đóng **3** màn chi tiết + dựng 1 shell trong 1 vòng.

⇒ Đơn giá dùng cho toàn bộ ước lượng dưới đây: **4 route/vòng** khi khuôn đã có · **3 route/vòng** khi chưa có khuôn · **+1 vòng** cho mỗi primitive/shell phải dựng mới.
*(Ước lượng = số VÒNG factory, không phải giờ công. Đây là con số quy hoạch, KHÔNG phải cam kết tiến độ.)*

---

## §10. Năm nhóm — nợ đo được, ước lượng, DoD

Số ❌ dưới đây đo bằng `node frontend/scripts/ui-audit-inventory.mjs --json` ngày 2026-07-31 (mẫu số = số route của nhóm).

### 10.1 Nhóm «Danh sách» — 40 route
- **Nợ**: Lỗi+Thử lại ❌ **0** *(24 lúc mở sổ; lô 1 đóng 12 route 2026-08-03; lô 2 đóng 12 route cuối cùng **2026-08-04 — ĐÃ LAND** ⇒ nhóm «Danh sách» **HẾT NỢ** ở tiêu chí này, đo LIVE bằng bộ dò)* · **adoption `ListPageShell` 28/40** *(đại lượng RIÊNG, không đọc được từ bộ dò — 12 file còn lại là lô 3, xem bảng tiến độ dưới và `ADR-UX-23`)* · a11y ❌ **28** · ≤768px ❌ **11** · Xương ❌ **5** · Tải ❌ 0 · Rỗng ❌ 0 · VI ❌ 0
- **Khuôn**: `components/ui/ListPageShell.vue` (đã có, vòng 3) + `ui/DataTable` + `ui/EmptyState` + `ui/ErrorState`
- **Ước lượng**: 40 ÷ 4 = **10 vòng** (khuôn đã có; mỗi vòng 1 lô 4 màn cùng module để tái dùng fixture test)
- **Thứ tự ưu tiên**: 1 (rẻ nhất/route, đóng luôn **AC-UX-047** — nợ P0 diện rộng lớn nhất còn lại)
- **DoD**: mỗi lô — (a) `grep -l ListPageShell` đủ số màn trong lô; (b) test render 4 trạng thái loại trừ cho từng màn (lỗi ⇒ **0** `ui-empty`, **đúng 1** nút «Thử lại», nút đó **gọi lại hàm nạp**); (c) bộ dò: *Lỗi+Thử lại* của nhóm **24 → 0** khi hết đợt B, **0 ô ✅ lật thành ❌**; (d) `vitest run` 0 file đỏ.

#### Tiến độ `AC-UX-047` theo lô

| Lô | Số route | Trạng thái | Sổ / đặc tả |
|---|---|---|---|
| **Lô 1** | **12** | **ĐÃ ĐÓNG — 12 route** (2026-08-03): nợ bộ dò `89 → 77`, nợ nhóm «Danh sách» `24 → 12`. 12 view import `ui/ListPageShell.vue`; 12 test trạng thái `TC-UX3-11…22` (72 TC) xanh; `npx vitest run src/views/**/*ListStates.test.ts` ⇒ **`Test Files 16 passed (16)`** | [`02_LIST_PAGE_SHELL.md §12`](./02_LIST_PAGE_SHELL.md) — sổ 12 route ở **§12.2**, DoD 8 ô ở **§12.7** |
| **Lô 2** | **12** | **ĐÃ ĐÓNG — 12 route DANH SÁCH CUỐI CÙNG** (2026-08-04): họ `*ListView` HẾT NỢ — phép lọc `bộ dò: ❌ AND file ~ /ListView/` trả **0 route** (đo LIVE). Nợ bộ dò `69 → 57` (**không** 77 → 65: token 77 đã stale 8 đơn vị vì lô 1 lớp CHI TIẾT — xem `ADR-UX-22`), nợ nhóm «Danh sách» `12 → 0`. Adopter `*ListView` **16 → 28**; test trạng thái `TC-UX3-23…34` (**+86 TC**), file `*ListStates.test.ts` **16 → 28**. Đã gộp **lật 4 ô stale của vòng 3** + đối soát **15 ô** lệch 2 chiều của cột này. Ba số bằng nhau: ô ❌ §3.1 == bộ dò == token == **57**; `--check` in `Lỗi+Thử lại 0` | [`02_LIST_PAGE_SHELL.md §13`](./02_LIST_PAGE_SHELL.md) — sổ 12 route ở **§13.2**, DoD 10 ô ở **§13.7** |
| **Lô 3** | **12** | **ĐÍNH CHÍNH 2026-08-04 — dòng cũ ghi «0 màn danh sách, không còn» là SAI** (`ADR-UX-23`): con số 0 đó đọc từ cột *Lỗi+Thử lại* của bộ dò, một phép đo **sự có mặt** của nút «Thử lại» — nó không thấy 12 màn danh sách **chưa áp khuôn** (adopter `*ListView` **28/40**), trong đó `/audit-trail` và `/needs-requests` in banner lỗi **KÈM** câu rỗng. Lô 3 = 12 route CÒN LẠI: `/audit-trail` · `/cm/work-orders` · `/service-contracts` · `/decommissions` · `/inventory/cycle-counts` · `/pm/work-orders` · `/pm/schedules` · `/needs-requests` · `/commissioning` · `/imm06/programs` · `/imm06/sessions` · `/imm06/competencies`. Nghiệm thu = adoption **28 → 40/40**, non-adopter **12 → 0** (guard `AC-UX-070`), test trạng thái **28 → 40** file, `TC-UX3-35…46`. Nợ *Lỗi+Thử lại* của nhóm **vẫn 0** trước và sau lô 3 — lô này trả **nợ adoption**, một đại lượng khác | [`02_LIST_PAGE_SHELL.md §14`](./02_LIST_PAGE_SHELL.md) — sổ 12 route ở **§14.2**, DoD 10 ô ở **§14.7** |
| Lô 4+ | **0 màn danh sách** | không còn | sau lô 3, họ `*ListView` đóng ở **cả hai** phép đo. Nợ *Lỗi+Thử lại* còn lại (**57**) thuộc màn tạo/sửa/chi tiết/tiện ích ⇒ `AC-UX-048` + lô riêng, **không** dùng `ListPageShell` |

**Lô 1 — đúng 12 route (không hơn, không kém):** `/stock-movements` · `/asset-transfers` · `/warehouses` ·
`/device-models` · `/suppliers` · `/spare-parts` · `/documents/requests` · `/pm/templates` · `/cm/firmware` ·
`/sla-policies` · `/incidents/list` · `/rca`. Cả 12 là dòng 16, 20, 23, 33, 40, 48, 57, 60, 75, 85, 87, 90 của
bảng **§11** (nhóm «Danh sách», đợt **B**) — **§11 giữ nguyên 135 dòng, 0 thay đổi** (guard `INV-UX5PLAN-*`).

**Lô 2 — đúng 12 route (không hơn, không kém):** `/assets` · `/calibration` · `/calibration/schedules` ·
`/capas` · `/compliance/rules` · `/compliance/findings` · `/compliance/audits` · `/compliance/mr` ·
`/tech-specs` · `/vendor-evaluations` · `/approved-vendors` · `/procurement-decisions` (dòng **11, 58, 60,
69, 72, 74, 76, 79, 127, 130, 132, 133** của `00 §3.1`) — **§11 vẫn giữ nguyên 135 dòng, 0 thay đổi**.

### 10.2 Nhóm «Chi tiết» — 34 route
- **Nợ**: Xương ❌ **22** · a11y ❌ **20** · Lỗi ❌ **15** · ≤768px ❌ **9** · Rỗng ❌ **8** · VI ❌ **3** · Tải ❌ 0
- **Khuôn**: `components/common/DetailPageShell.vue` (đã có, vòng 4) + `DetailTabBar` + `DetailLoadError`
- **Ước lượng**: 32 ÷ 4 = **8 vòng** (2 route P0 đã nằm ở đợt A)
- **Thứ tự ưu tiên**: 2 — đóng **AC-UX-048** (20 màn không có lối nạp lại) và **AC-UX-052** (thanh tab tự chế — **9 file / 12 nút-tab**, số cũ «27 màn» đã đính chính 2026-08-04, xem [`07 §1.1`](./07_DETAIL_TAB_BAR_SSOT.md))
- **DoD**: mỗi lô — (a) `grep -c DetailPageShell` ≥1 mỗi màn; (b) 4 test trạng thái (404 / 403 / lỗi mạng / `null`); (c) `text-red-500` ở màn chi tiết **14 → 0** khi hết đợt C; (d) panel thao tác **vắng mặt** ở mọi trạng thái ≠ `content` (probe `#actions`); (e) 0 hardcode `status ===` / `workflow_state ===` mới (GATE-8).
- **Tiến độ đợt C** — **lô 1 ĐÃ ĐÓNG 2026-08-03** (8/32 route, sổ ở [`03 §12`](./03_DETAIL_PAGE_SHELL.md)): `/stock-movements/:name` · `/warehouses/:name` · `/spare-parts/:name` · `/asset-transfers/:id` · `/cm/firmware/:id` · `/compliance/findings/:id` · `/suppliers/:id` · `/procurement-decisions/:id`. Đo lại từ đĩa: màn **chưa** dùng khuôn `29 → 21`; token nợ `AC-UX-048` `[NO-DET] 20 → 12`; `text-red-500` trong 8 file `4 → 0` (đổi sang token `text-danger-500`, GIỮ dấu sao bắt buộc). Bộ test: 8 file `*DetailStates.test.ts` (mount THẬT, 65 case) + guard `uiDetailShellLot1Parity.test.ts`. **Còn lại 24 route** cho lô 2–3; lô 1 truyền `tabs=[]` (8 màn đó vốn **không có tab**).
- **Tiến độ nhóm thanh tab (`AC-UX-052`)** — **lô 1 ĐÃ CHỐT SPEC 2026-08-04**, hợp đồng ở [`07_DETAIL_TAB_BAR_SSOT.md`](./07_DETAIL_TAB_BAR_SSOT.md). Đo lại từ đĩa (quét `src/views` **+** `src/components`, dấu vân tay `<button … :class="… (activeTab|tab) ===`): nợ thật = **9 file / 12 nút-tab tự chế**, **KHÔNG** phải «27 màn» (số cũ đếm cả 24 màn chi tiết **không có tab nào** — đính chính ở `07 §1.1`). Lô 1 đóng **3 file / 5 nút** (`asset/AssetDetailView` · `commissioning/CommissioningDetailView` · `needs/NeedsRequestDetailView`) ⇒ **12 → 7 nút, 9 → 6 file**; SSoT mở rộng CHỈ-THÊM prop `badge` (**AC-UX-067**); nợ còn lại đóng băng bằng guard CHỈ-GIẢM `views/detailTabBarAdoption.test.ts` (**AC-UX-069**). **Lô 2 = 6 file** (`tech-specs/TechSpecDetailView` · `procurement/VendorEvalDetailView` · `inventory/UomConversionView` · `master-data/ReferenceDataView` · `components/commissioning/CommissioningForm` · `components/commissioning/AssetDashboard`) — chưa mở. **§11 giữ nguyên 135 dòng, 0 thay đổi** (guard `INV-UX5PLAN-*`).

### 10.3 Nhóm «Biểu mẫu» — 23 route
- **Nợ**: Xương ❌ **23** · Lỗi ❌ **23** · Tải ❌ **13** · a11y ❌ **12** · ≤768px ❌ **6** · Rỗng ❌ **5** · VI ❌ 0
- **Khuôn**: **CHƯA CÓ** — cần `ui/FormField` (label ⇄ `for`, `aria-describedby` cho lỗi) + `ui/IconButton` (bắt buộc `aria-label`) — **AC-UX-039**
- **Ước lượng**: **1 vòng** dựng 2 primitive + 19 ÷ 4 ≈ 5 vòng áp = **6 vòng**
- **Thứ tự ưu tiên**: 3 — nhóm này giữ **4/11 route P0** (đã đẩy sang đợt A) và là nơi a11y sai nhiều nhất tính theo tỷ lệ (12/23 = 52%)
- **DoD**: (a) `ui/*.vue` = **10**, barrel 10 export, `uiPrimitiveHygiene` xanh; (b) mọi `<label>` trong màn đã áp có `for` trỏ `id` **có thật** (test render, không grep); (c) lỗi validate đọc được bằng trình đọc màn hình (`aria-describedby` trỏ đúng phần tử lỗi); (d) bộ dò: *a11y* của nhóm **12 → 0**, *Tải* **13 → 0**.

### 10.4 Nhóm «Bảng điều khiển» — 8 route
- **Nợ**: Rỗng ❌ **5** · Lỗi ❌ **5** · Tải ❌ **3** · Xương ❌ **3** · ≤768px ❌ **2** · a11y ❌ **1** · VI ❌ 0
- **Khuôn**: `PersonaDashboardShell.vue` (đã có, dùng cho 8 dashboard persona) + `ui/Card` + `ui/Skeleton`; thẻ KPI lỗi phải hiện «—» + dải «Không tải được số liệu» (**không** hiện `0`)
- **Ước lượng**: 7 ÷ 4 ≈ **2 vòng**
- **Thứ tự ưu tiên**: 4
- **DoD**: (a) mỗi dashboard có test "API lỗi ⇒ **0** thẻ KPI hiện số"; (b) `PMCalendarView` (P0, đợt A) có khuôn tải + rỗng + lỗi; (c) bộ dò: *Rỗng* **5 → 0**, *Lỗi* **5 → 0**.

### 10.5 Nhóm «Khác» — 30 route
Phân lớp con để chia lô (không phải nhóm riêng — guard chỉ biết 5 nhóm):

| Phân lớp | Route | Ghi chú |
|---|---|---|
| Xác thực & tài khoản | `/login` `/register` `/set-password` `/profile` `/unauthorized` `/account/change-password` `/settings/notifications` | 7 — nhiều màn tĩnh, chi phí thấp |
| Bước trong quy trình | `/commissioning/:id/nc` `/commissioning/:id/timeline` `/cm/work-orders/:id/diagnose` `/cm/work-orders/:id/parts` `/cm/work-orders/:id/checklist` | 5 — **2 route P0** (đợt A) |
| Công cụ & tra cứu | `/qr-scan` `/a/:token` `/assets/:id/info` `/assets/labels/print` `/reference-data` `/documents` `/stock` `/inventory/uom` `/inventory/forecasts` `/inventory/watchlist` `/depreciation` `/cm/mttr` `/compliance/scorecard` `/approvals/pending` | 14 — **1 route P0** (`/inventory/uom`, đợt A) |
| Quản trị & hệ thống | `/admin/roles` `/debug/asset-dashboard` `/:pathMatch(.*)*` | 3 — **1 route P0** (`/admin/roles`) + **AC-UX-030** (404 căn `min-h-[60vh]`) |
| Dashboard lẻ | `/calibration/dashboard` | 1 (tên file không kết thúc `DashboardView.vue`) |

- **Nợ**: Lỗi ❌ **22** · Xương ❌ **21** · a11y ❌ **13** · Tải ❌ **12** · Rỗng ❌ **10** · ≤768px ❌ **2** · VI ❌ 0
- **Ước lượng**: 26 ÷ 3 ≈ **9 vòng** (phần lớn không khớp khuôn nào ⇒ đơn giá 3/vòng)
- **Thứ tự ưu tiên**: 5 (trừ 4 route P0 đã ở đợt A)
- **DoD**: (a) mỗi màn có **đúng 1** khuôn trạng thái (dùng `ui/ErrorState` + `ui/EmptyState`, không tự chế); (b) 2 màn tự vẽ overlay thuộc nhóm này (`UomConversionView` `WatchlistView`) di trú sang `BaseModal` ⇒ allowlist §5.2 **30 → 28**, và 2 màn lai (`ReferenceDataView` `DepreciationView`) bỏ overlay tự vẽ ⇒ hybrid §5.3 **4 → 2**; (c) bộ dò: *Lỗi* **22 → 0**.

### 10.6 Hạng mục **không thuộc route** — nợ hộp thoại còn lại (chủ đề của chính vòng 5)
| Hạng mục | Số đo hôm nay | Đích | Đợt |
|---|---|---|---|
| File tự vẽ overlay | **30** | **0** (mọi hộp thoại đi qua `BaseModal`) | rải theo nhóm chủ quản (B–E), guard §5.2 chỉ-giảm |
| File lai | **4** | **0** | C/E |
| `confirm()` trần | **42** call-site / **28** file (đo 2026-08-04, đã strip comment) | **0** — thay bằng `await useNotify().confirm()` (ADR-UX-16). **Lô 1 ĐANG LÀM vòng 7**: 7 file / **21** call-site ⇒ còn **21/21** | lô 1 = [`06 §5`](./06_CONFIRM_DIALOG_SSOT.md); lô 2+ ở B–E. Mỗi lô hạ **bản đồ ngân sách** `bareConfirmBudget.test.ts` (ADR-UX-18) |
| `NotificationModal.vue` | tự vẽ overlay `fixed inset-0 … z-[10000]` + tự nghe `Escape` ⇒ **0** bẫy focus, **0** trả focus, và **ESC kép nuốt hộp thoại kế tiếp** trong hàng đợi | render **qua `BaseModal`** (thừa hưởng `useFocusTrap`), bỏ listener, thêm prop `layer` (ADR-UX-17) | **A — ĐANG LÀM vòng 7** (AC-UX-064, [`06 §3/§4`](./06_CONFIRM_DIALOG_SSOT.md)) |

---

## §11. Bảng phân hoạch 135 route (nguồn của guard §12)

Cột *Nợ* = các tiêu chí đang ❌ (Tải · Xương · Rỗng · Lỗi · RWD · VI · A11y), đo 2026-07-31 bằng `ui-audit-inventory.mjs`.

> **Nguồn của cột *Đau* là BỘ DÒ, không phải bảng tay `00 §3.1`** (ADR-UX-10). Hai bảng lệch **14/135** ô mức đau — đã đối chiếu từng dòng hôm nay:
> `/login` `/assets/:id/edit` `/reference-data` `/calibration/new` `/incidents/dashboard` `/account/change-password` `/procurement-decisions/:id` (tay P2 → dò **P1**) ·
> `/assets` `/purchases` `/user-profiles` `/procurement-plans` `/vendor-profiles` (tay P1 → dò **P2**) ·
> `/cm/dashboard` (tay **P0** → dò P1) · `/needs-requests/new` (tay P1 → dò **P0**).
> Tổng số P0 **trùng nhau ở 11** nhưng **tập hợp lệch đúng 1 phần tử** (`/cm/dashboard` ⇄ `/needs-requests/new`).
> ⇒ Đợt A theo **bộ dò**. Ai chấm đợt A bằng bảng tay sẽ sửa nhầm 1 màn — đọc ADR-UX-10 trước khi tranh luận.
> Cột *View file* thì **khớp 135/135** với `00 §3.1` (đã đối chiếu), nên guard §12 vẫn cross-check được cột file.

| # | Route (`path`) | View file | Nhóm | Đợt | Đau | Nợ |
|---|---|---|---|---|---|---|
| 1 | `/login` | `frontend/src/views/auth/LoginView.vue` | Khác | E | P1 | Xương Lỗi A11y |
| 2 | `/register` | `frontend/src/views/auth/RegisterView.vue` | Khác | E | P1 | Tải Xương Lỗi A11y |
| 3 | `/set-password` | `frontend/src/views/auth/SetPasswordView.vue` | Khác | E | P1 | Tải Xương Lỗi |
| 4 | `/profile` | `frontend/src/views/auth/ProfileView.vue` | Khác | E | P1 | Xương Rỗng Lỗi |
| 5 | `/settings/notifications` | `frontend/src/views/settings/NotificationSettingsView.vue` | Khác | E | P2 | Xương |
| 6 | `/unauthorized` | `frontend/src/views/auth/UnauthorizedView.vue` | Khác | E | P2 | — |
| 7 | `/dashboard` | `frontend/src/views/dashboard/DashboardView.vue` | Bảng điều khiển | E | P2 | Tải Xương |
| 8 | `/assets` | `frontend/src/views/asset/AssetListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 9 | `/qr-scan` | `frontend/src/views/system/QRScanView.vue` | Khác | E | P2 | — |
| 10 | `/a/:token` | `frontend/src/views/system/QrResolveView.vue` | Khác | E | P2 | Xương Lỗi |
| 11 | `/assets/:id/info` | `frontend/src/views/asset/AssetScanInfoView.vue` | Khác | E | P2 | Xương Lỗi |
| 12 | `/assets/new` | `frontend/src/views/asset/AssetCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Lỗi A11y |
| 13 | `/assets/labels/print` | `frontend/src/views/asset/AssetLabelPrintView.vue` | Khác | E | P1 | Tải Xương Rỗng Lỗi |
| 14 | `/assets/:id` | `frontend/src/views/asset/AssetDetailView.vue` | Chi tiết | C | P1 | Xương Rỗng A11y |
| 15 | `/assets/:id/edit` | `frontend/src/views/asset/AssetEditView.vue` | Biểu mẫu | D | P1 | Xương Lỗi A11y |
| 16 | `/suppliers` | `frontend/src/views/purchase/SupplierListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 17 | `/suppliers/new` | `frontend/src/views/purchase/SupplierFormView.vue` | Biểu mẫu | D | P1 | Xương Lỗi A11y |
| 18 | `/suppliers/:id` | `frontend/src/views/purchase/SupplierDetailView.vue` | Chi tiết | C | P2 | Xương Lỗi |
| 19 | `/suppliers/:id/edit` | `frontend/src/views/purchase/SupplierFormView.vue` | Biểu mẫu | D | P1 | Xương Lỗi A11y |
| 20 | `/device-models` | `frontend/src/views/asset/DeviceModelListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 21 | `/device-models/new` | `frontend/src/views/asset/DeviceModelFormView.vue` | Biểu mẫu | D | P1 | Xương Lỗi A11y |
| 22 | `/device-models/:id` | `frontend/src/views/asset/DeviceModelFormView.vue` | Biểu mẫu | D | P1 | Xương Lỗi A11y |
| 23 | `/sla-policies` | `frontend/src/views/master-data/SlaPolicyListView.vue` | Danh sách | B | P1 | Lỗi RWD A11y |
| 24 | `/reference-data` | `frontend/src/views/master-data/ReferenceDataView.vue` | Khác | E | P1 | Xương Lỗi A11y |
| 25 | `/commissioning` | `frontend/src/views/commissioning/CommissioningListView.vue` | Danh sách | B | P2 | RWD A11y |
| 26 | `/commissioning/new` | `frontend/src/views/commissioning/CommissioningCreateView.vue` | Biểu mẫu | D | P1 | Xương Rỗng Lỗi |
| 27 | `/commissioning/:id` | `frontend/src/views/commissioning/CommissioningDetailView.vue` | Chi tiết | C | P2 | Rỗng A11y |
| 28 | `/commissioning/:id/nc` | `frontend/src/views/commissioning/CommissioningNCView.vue` | Khác | E | P1 | Rỗng Lỗi |
| 29 | `/commissioning/:id/timeline` | `frontend/src/views/commissioning/CommissioningTimelineView.vue` | Khác | E | P2 | Rỗng |
| 30 | `/documents` | `frontend/src/views/document/DocumentManagement.vue` | Khác | E | P2 | Lỗi A11y |
| 31 | `/documents/new` | `frontend/src/views/document/DocumentCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Rỗng Lỗi |
| 32 | `/documents/view/:name` | `frontend/src/views/document/DocumentDetailView.vue` | Chi tiết | C | P2 | A11y |
| 33 | `/documents/requests` | `frontend/src/views/document/DocumentRequestListView.vue` | Danh sách | B | P1 | Lỗi RWD A11y |
| 34 | `/pm/dashboard` | `frontend/src/views/pm/PMDashboardView.vue` | Bảng điều khiển | E | P1 | Rỗng Lỗi |
| 35 | `/pm/calendar` | `frontend/src/views/pm/PMCalendarView.vue` | Bảng điều khiển | A | P0 | Tải Xương Rỗng Lỗi RWD |
| 36 | `/pm/work-orders` | `frontend/src/views/pm/PMWorkOrderListView.vue` | Danh sách | B | P2 | RWD A11y |
| 37 | `/pm/work-orders/new` | `frontend/src/views/pm/PMWorkOrderCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Lỗi A11y |
| 38 | `/pm/work-orders/:id` | `frontend/src/views/pm/PMWorkOrderDetailView.vue` | Chi tiết | C | P2 | — |
| 39 | `/pm/schedules` | `frontend/src/views/pm/PmScheduleListView.vue` | Danh sách | B | P2 | RWD A11y |
| 40 | `/pm/templates` | `frontend/src/views/pm/PmTemplateListView.vue` | Danh sách | B | P1 | Lỗi RWD A11y |
| 41 | `/cm/dashboard` | `frontend/src/views/cm/CMDashboardView.vue` | Bảng điều khiển | E | P1 | Rỗng Lỗi RWD |
| 42 | `/cm/create` | `frontend/src/views/cm/CMCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Lỗi A11y |
| 43 | `/cm/work-orders` | `frontend/src/views/cm/CMWorkOrderListView.vue` | Danh sách | B | P2 | RWD A11y |
| 44 | `/cm/work-orders/:id` | `frontend/src/views/cm/CMWorkOrderDetailView.vue` | Chi tiết | C | P2 | — |
| 45 | `/cm/work-orders/:id/diagnose` | `frontend/src/views/cm/CMDiagnoseView.vue` | Khác | A | P0 | Tải Xương Rỗng Lỗi A11y |
| 46 | `/cm/work-orders/:id/parts` | `frontend/src/views/cm/CMPartsView.vue` | Khác | A | P0 | Tải Xương Rỗng Lỗi A11y |
| 47 | `/cm/work-orders/:id/checklist` | `frontend/src/views/cm/CMChecklistView.vue` | Khác | E | P1 | Tải Xương Lỗi A11y |
| 48 | `/cm/firmware` | `frontend/src/views/document/FirmwareCrListView.vue` | Danh sách | B | P1 | Lỗi RWD A11y |
| 49 | `/cm/firmware/:id` | `frontend/src/views/document/FirmwareCrDetailView.vue` | Chi tiết | C | P1 | Xương Rỗng Lỗi |
| 50 | `/cm/mttr` | `frontend/src/views/cm/CMMttrView.vue` | Khác | E | P1 | Rỗng Lỗi A11y |
| 51 | `/calibration/dashboard` | `frontend/src/views/calibration/CalibrationDashboard.vue` | Khác | E | P2 | Xương Lỗi |
| 52 | `/calibration` | `frontend/src/views/calibration/CalibrationListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 53 | `/calibration/new` | `frontend/src/views/calibration/CalibrationCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Lỗi A11y |
| 54 | `/calibration/schedules` | `frontend/src/views/calibration/CalibrationScheduleListView.vue` | Danh sách | B | P1 | Lỗi RWD A11y |
| 55 | `/calibration/:id` | `frontend/src/views/calibration/CalibrationDetailView.vue` | Chi tiết | C | P1 | Xương RWD A11y |
| 56 | `/incidents/dashboard` | `frontend/src/views/incident/IMM12DashboardView.vue` | Bảng điều khiển | E | P1 | Tải Xương Rỗng |
| 57 | `/incidents/list` | `frontend/src/views/incident/IncidentListView.vue` | Danh sách | B | P2 | Lỗi |
| 58 | `/incidents/new` | `frontend/src/views/incident/IncidentCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Lỗi |
| 59 | `/incidents/:id` | `frontend/src/views/incident/IncidentDetailView.vue` | Chi tiết | C | P2 | Xương VI |
| 60 | `/rca` | `frontend/src/views/incident/RCAListView.vue` | Danh sách | B | P2 | Lỗi |
| 61 | `/rca/:id` | `frontend/src/views/incident/RCADetailView.vue` | Chi tiết | A | P0 | Xương Rỗng Lỗi RWD VI |
| 62 | `/capas` | `frontend/src/views/incident/CAPAListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 63 | `/capas/:id` | `frontend/src/views/incident/CAPADetailView.vue` | Chi tiết | C | P2 | A11y |
| 64 | `/audit-trail` | `frontend/src/views/audit/AuditTrailListView.vue` | Danh sách | B | P2 | A11y |
| 65 | `/compliance/rules` | `frontend/src/views/compliance/ComplianceRuleListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 66 | `/compliance/rules/:id` | `frontend/src/views/compliance/ComplianceRuleDetailView.vue` | Chi tiết | C | P2 | A11y |
| 67 | `/compliance/findings` | `frontend/src/views/compliance/FindingListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 68 | `/compliance/findings/:id` | `frontend/src/views/compliance/FindingDetailView.vue` | Chi tiết | C | P2 | Lỗi A11y |
| 69 | `/compliance/audits` | `frontend/src/views/compliance/InternalAuditListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 70 | `/compliance/audits/:id` | `frontend/src/views/compliance/InternalAuditDetailView.vue` | Chi tiết | C | P2 | Rỗng A11y |
| 71 | `/compliance/scorecard` | `frontend/src/views/compliance/ScorecardView.vue` | Khác | E | P2 | Lỗi A11y |
| 72 | `/compliance/mr` | `frontend/src/views/compliance/ManagementReviewListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 73 | `/compliance/mr/:id` | `frontend/src/views/compliance/ManagementReviewDetailView.vue` | Chi tiết | C | P2 | RWD A11y |
| 74 | `/compliance/heatmap` | `frontend/src/views/compliance/ComplianceHeatmapView.vue` | Bảng điều khiển | E | P2 | Lỗi A11y |
| 75 | `/asset-transfers` | `frontend/src/views/asset/AssetTransferListView.vue` | Danh sách | B | P2 | Xương Lỗi |
| 76 | `/asset-transfers/new` | `frontend/src/views/asset/AssetTransferCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Rỗng Lỗi |
| 77 | `/asset-transfers/:id` | `frontend/src/views/asset/AssetTransferDetailView.vue` | Chi tiết | C | P2 | Xương Lỗi |
| 78 | `/decommissions` | `frontend/src/views/eol/DecommissionListView.vue` | Danh sách | B | P2 | — |
| 79 | `/decommissions/:id` | `frontend/src/views/eol/DecommissionDetailView.vue` | Chi tiết | C | P2 | — |
| 80 | `/service-contracts` | `frontend/src/views/purchase/ServiceContractListView.vue` | Danh sách | B | P2 | A11y |
| 81 | `/service-contracts/new` | `frontend/src/views/purchase/ServiceContractCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Lỗi |
| 82 | `/service-contracts/:id` | `frontend/src/views/purchase/ServiceContractDetailView.vue` | Chi tiết | C | P1 | Xương Lỗi RWD A11y |
| 83 | `/depreciation` | `frontend/src/views/asset/DepreciationView.vue` | Khác | E | P1 | Tải Rỗng Lỗi |
| 84 | `/inventory` | `frontend/src/views/inventory/InventoryDashboardView.vue` | Bảng điều khiển | E | P2 | Lỗi |
| 85 | `/warehouses` | `frontend/src/views/inventory/WarehouseListView.vue` | Danh sách | B | P2 | Lỗi |
| 86 | `/warehouses/:name` | `frontend/src/views/inventory/WarehouseDetailView.vue` | Chi tiết | C | P1 | Xương Rỗng Lỗi |
| 87 | `/spare-parts` | `frontend/src/views/inventory/SparePartListView.vue` | Danh sách | B | P2 | Lỗi |
| 88 | `/spare-parts/:name` | `frontend/src/views/inventory/SparePartDetailView.vue` | Chi tiết | C | P2 | Xương Lỗi |
| 89 | `/stock` | `frontend/src/views/inventory/StockLevelView.vue` | Khác | E | P2 | Xương Lỗi |
| 90 | `/stock-movements` | `frontend/src/views/inventory/StockMovementListView.vue` | Danh sách | B | P2 | Lỗi A11y |
| 91 | `/stock-movements/new` | `frontend/src/views/inventory/StockMovementCreateView.vue` | Biểu mẫu | A | P0 | Tải Xương Rỗng Lỗi RWD |
| 92 | `/stock-movements/:name/edit` | `frontend/src/views/inventory/StockMovementEditView.vue` | Biểu mẫu | A | P0 | Xương Rỗng Lỗi RWD A11y |
| 93 | `/stock-movements/:name` | `frontend/src/views/inventory/StockMovementDetailView.vue` | Chi tiết | C | P1 | Xương Rỗng Lỗi |
| 94 | `/inventory/uom` | `frontend/src/views/inventory/UomConversionView.vue` | Khác | A | P0 | Tải Xương Lỗi RWD A11y |
| 95 | `/inventory/forecasts` | `frontend/src/views/inventory/SpareForecastView.vue` | Khác | E | P2 | Tải Xương |
| 96 | `/inventory/watchlist` | `frontend/src/views/inventory/WatchlistView.vue` | Khác | E | P1 | Tải Xương Lỗi A11y |
| 97 | `/inventory/cycle-counts` | `frontend/src/views/inventory/CycleCountListView.vue` | Danh sách | B | P2 | — |
| 98 | `/inventory/cycle-counts/new` | `frontend/src/views/inventory/CycleCountCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Lỗi |
| 99 | `/inventory/cycle-counts/:name` | `frontend/src/views/inventory/CycleCountDetailView.vue` | Chi tiết | C | P2 | VI |
| 100 | `/approvals/pending` | `frontend/src/views/audit/PendingApprovalsView.vue` | Khác | E | P2 | Xương |
| 101 | `/purchases` | `frontend/src/views/purchase/PurchaseListView.vue` | Danh sách | B | P2 | RWD |
| 102 | `/purchases/new` | `frontend/src/views/purchase/PurchaseCreateView.vue` | Biểu mẫu | D | P1 | Tải Xương Lỗi RWD |
| 103 | `/purchases/:name/edit` | `frontend/src/views/purchase/PurchaseEditView.vue` | Biểu mẫu | D | P1 | Xương Lỗi RWD |
| 104 | `/purchases/:name` | `frontend/src/views/purchase/PurchaseDetailView.vue` | Chi tiết | C | P2 | Xương Lỗi |
| 105 | `/admin/roles` | `frontend/src/views/admin/RoleAdminView.vue` | Khác | A | P0 | Xương Rỗng Lỗi RWD A11y |
| 106 | `/user-profiles` | `frontend/src/views/auth/UserProfileListView.vue` | Danh sách | B | P2 | — |
| 107 | `/user-profiles/new` | `frontend/src/views/auth/UserProfileFormView.vue` | Biểu mẫu | D | P2 | Xương Lỗi |
| 108 | `/user-profiles/:user` | `frontend/src/views/auth/UserProfileFormView.vue` | Biểu mẫu | D | P2 | Xương Lỗi |
| 109 | `/account/change-password` | `frontend/src/views/auth/ChangePasswordView.vue` | Khác | E | P1 | Tải Xương Lỗi A11y |
| 110 | `/needs-requests` | `frontend/src/views/needs/NeedsRequestListView.vue` | Danh sách | B | P2 | A11y |
| 111 | `/needs-requests/new` | `frontend/src/views/needs/NeedsRequestCreateView.vue` | Biểu mẫu | A | P0 | Tải Xương Lỗi RWD A11y |
| 112 | `/needs-requests/:id` | `frontend/src/views/needs/NeedsRequestDetailView.vue` | Chi tiết | C | P2 | RWD A11y |
| 113 | `/procurement-plans` | `frontend/src/views/needs/ProcurementPlanListView.vue` | Danh sách | B | P2 | RWD |
| 114 | `/procurement-plans/:id` | `frontend/src/views/needs/ProcurementPlanDetailView.vue` | Chi tiết | C | P1 | Xương Lỗi RWD |
| 115 | `/tech-specs` | `frontend/src/views/tech-specs/TechSpecListView.vue` | Danh sách | B | P1 | Xương Lỗi A11y |
| 116 | `/tech-specs/new` | `frontend/src/views/tech-specs/TechSpecCreateView.vue` | Biểu mẫu | A | P0 | Tải Xương Lỗi RWD A11y |
| 117 | `/tech-specs/:id` | `frontend/src/views/tech-specs/TechSpecDetailView.vue` | Chi tiết | C | P1 | Xương Lỗi RWD A11y |
| 118 | `/vendor-evaluations` | `frontend/src/views/procurement/VendorEvalListView.vue` | Danh sách | B | P1 | Xương Lỗi A11y |
| 119 | `/vendor-evaluations/:id` | `frontend/src/views/procurement/VendorEvalDetailView.vue` | Chi tiết | C | P1 | Xương Lỗi RWD A11y |
| 120 | `/approved-vendors` | `frontend/src/views/procurement/AvlListView.vue` | Danh sách | B | P1 | Xương Lỗi A11y |
| 121 | `/procurement-decisions` | `frontend/src/views/procurement/DecisionListView.vue` | Danh sách | B | P2 | Xương Lỗi |
| 122 | `/procurement-decisions/:id` | `frontend/src/views/procurement/DecisionDetailView.vue` | Chi tiết | C | P1 | Xương Lỗi A11y |
| 123 | `/vendor-profiles` | `frontend/src/views/procurement/VendorProfileListView.vue` | Danh sách | B | P2 | — |
| 124 | `/vendor-profiles/:id` | `frontend/src/views/procurement/VendorProfileDetailView.vue` | Chi tiết | A | P0 | Xương Rỗng Lỗi RWD A11y |
| 125 | `/imm06/programs` | `frontend/src/views/training/ProgramListView.vue` | Danh sách | B | P2 | A11y |
| 126 | `/imm06/programs/new` | `frontend/src/views/training/ProgramDetailView.vue` | Chi tiết | C | P2 | Xương A11y |
| 127 | `/imm06/programs/:name` | `frontend/src/views/training/ProgramDetailView.vue` | Chi tiết | C | P2 | Xương A11y |
| 128 | `/imm06/sessions` | `frontend/src/views/training/SessionListView.vue` | Danh sách | B | P2 | A11y |
| 129 | `/imm06/sessions/new` | `frontend/src/views/training/SessionDetailView.vue` | Chi tiết | C | P2 | Xương A11y |
| 130 | `/imm06/sessions/:name` | `frontend/src/views/training/SessionDetailView.vue` | Chi tiết | C | P2 | Xương A11y |
| 131 | `/imm06/dashboard` | `frontend/src/views/training/TrainingDashboardView.vue` | Bảng điều khiển | E | P2 | Rỗng |
| 132 | `/imm06/competencies` | `frontend/src/views/training/CompetencyListView.vue` | Danh sách | B | P2 | A11y |
| 133 | `/imm06/competencies/:name` | `frontend/src/views/training/CompetencyDetailView.vue` | Chi tiết | C | P2 | Xương A11y |
| 134 | `/debug/asset-dashboard` | `frontend/src/components/commissioning/AssetDashboard.vue` | Khác | E | P1 | Tải Xương Rỗng |
| 135 | `/:pathMatch(.*)*` | `frontend/src/views/system/NotFoundView.vue` | Khác | E | P2 | — |

**Tổng: 135 route có view — Danh sách 40 · Chi tiết 34 · Biểu mẫu 23 · Bảng điều khiển 8 · Khác 30. Đợt A 11 · B 40 · C 32 · D 19 · E 33.**

---

## §12. Guard parity — `frontend/src/router/uiFixPlanParity.test.ts` (MỚI)

Cùng khuôn với `uiAuditDocParity.test.ts` (đã chạy được từ vòng 1): đọc **bảng route thật** (`routes` từ `src/router/index.ts`) + bảng `00 §3.1` + bảng §11 của tài liệu này.

| Mã | Bất biến | Vì sao cần |
|---|---|---|
| **INV-UX5PLAN-1** | Mọi route có view trong `00 §3.1` (file ≠ `— *(redirect)*`) xuất hiện **đúng 1 lần** ở §11 ⇒ **0 route mồ côi** | Phương án "sửa toàn bộ" mà bỏ sót 1 màn thì không còn là toàn bộ |
| **INV-UX5PLAN-2** | §11 **không** có dòng thừa (route đã xoá phải rời bảng) và số dòng == 135 | Bảng mục theo thời gian |
| **INV-UX5PLAN-3** | Cột *Nhóm* ∈ {Danh sách, Chi tiết, Biểu mẫu, Bảng điều khiển, Khác}; cột *Đợt* ∈ {A,B,C,D,E}; cột *Đau* ∈ {P0,P1,P2} | Chống ô rỗng / giá trị lạ |
| **INV-UX5PLAN-4** | `Đợt == 'A'` **⟺** `Đau == 'P0'` (kiểm 2 chiều) | Luật §9.3 phải là luật, không phải mô tả |
| **INV-UX5PLAN-5** | Cột *View file* của mỗi route **khớp đúng** ô view file của route đó ở `00 §3.1` (135/135). **KHÔNG** cross-check cột *Đau* — 2 bảng lệch 14 ô có chủ đích (ADR-UX-10), assert bằng nhau sẽ đỏ oan | 2 bảng phải cùng trỏ 1 file, nhưng thước đo mức đau chỉ có **một chủ**: bộ dò |
| **INV-UX5PLAN-6** | Cột *View file* trỏ file **có thật** trên đĩa | Đường dẫn chết |
| **INV-UX5PLAN-7** | Đúng **5** mục `### 10.1`…`### 10.5`, tên nhóm trong `«…»` **trùng khít** tập giá trị cột *Nhóm*, mỗi mục có đủ 3 dòng mở đầu `- **Ước lượng**` · `- **Thứ tự ưu tiên**` · `- **DoD**`. (`### 10.6` nằm **ngoài** phép kiểm — là hạng mục không thuộc route.) | A12 đòi "mỗi nhóm có ước lượng + thứ tự ưu tiên + DoD đo được" |
| **INV-UX5PLAN-8** | Dòng "Tổng: 135 route…" khớp số dòng đếm được và khớp phân bố nhóm/đợt | Chống sửa bảng quên sửa tổng |

Khuôn parse dùng lại nguyên `cellsOf()` / `section()` của `uiAuditDocParity.test.ts` — **không** viết bộ parse thứ hai.

---

## §13. Lộ trình — thứ tự thi hành

| Thứ tự | Đợt | Nội dung | Route | Ước lượng | Điều kiện tiên quyết |
|---|---|---|---|---|---|
| 0 | — | **Vòng 5 (đang chạy)**: hợp đồng hộp thoại SSoT + capstone | 0 | 1 vòng | — |
| 1 | **A** | 11 route P0 + `NotificationModal` dùng `useFocusTrap` | 11 | ~4 vòng | Vòng 5 xong |
| 2 | **B** | Nhóm *Danh sách* — adoption `ListPageShell` (AC-UX-047) | 40 | ~10 vòng | khuôn đã có |
| 3 | **C** | Nhóm *Chi tiết* — adoption `DetailPageShell` + `DetailTabBar` (AC-UX-048/052/053) | 32 | ~8 vòng | khuôn đã có; **AC-UX-049 chờ BE emit `can_edit`** |
| 4 | **D** | Nhóm *Biểu mẫu* — dựng `FormField` + `IconButton` (AC-UX-039) rồi áp | 19 | ~6 vòng | 1 vòng dựng primitive trước |
| 5 | **E** | *Bảng điều khiển* + *Khác* + dọn nốt overlay/`confirm()` | 33 | ~11 vòng | — |
| | | **Tổng** | **135** | **~39 vòng** | |

**Cổng chung mọi đợt (DoD tối thiểu, không thương lượng):**
1. `npx vitest run` — **0 file đỏ**; số file test **≥** baseline đầu đợt (chấm DELTA).
2. `npm run typecheck` sạch.
3. `uiAuditDocParity` + `uiFixPlanParity` xanh — bảng `00 §3.1` **và** §11 cập nhật cùng lượt với mã.
4. Bộ dò chạy TRƯỚC/SAU mỗi lô: **0 ô ✅ lật thành ❌** (chống "sửa chỗ này hỏng chỗ kia").
5. `git status --short -- '*.py'` **rỗng** trừ khi đợt đó có hạng mục BE đã ratify (vd AC-UX-049).
6. Chuỗi hiển thị mới: **tiếng Việt đầy đủ** (LL-FE-53).

---

## §14. Danh mục file được phép chạm — vòng 5

**Được sửa / tạo mới (7 đường dẫn):**
```
frontend/src/composables/useFocusTrap.ts                       (MỚI)
frontend/src/composables/useFocusTrap.test.ts                  (MỚI)
frontend/src/components/common/BaseModal.vue                   (SỬA — §3.2)
frontend/src/components/common/BaseModalDialog.test.ts         (MỚI)
frontend/src/components/common/modalOverlayHygiene.test.ts     (MỚI)
frontend/src/components/common/CommandPalette.vue              (SỬA — §4, chỉ gỡ mã fork)
frontend/src/router/uiFixPlanParity.test.ts                    (MỚI)
```

**Doc (BA đã land):**
```
docs/ui-ux/04_PHUONG_AN_SUA_TOAN_BO.md                         (MỚI — tài liệu này)
docs/ui-ux/00_AUDIT_HIEN_TRANG.md                              (SỬA — §6 sổ, §9 ADR-UX-08/09/10, §10 ghim, mục Tài liệu liên quan)
```

**CẤM chạm ở vòng 5:** mọi file dưới `frontend/src/views/` · `frontend/src/stores/` · `frontend/src/api/` · `frontend/src/components/ui/` · `assetcore/**/*.py` · `BaseModalResponsive.test.ts` · `CommandPalette.test.ts`.

---

## §15. Truy vết Acceptance A1–A13 ⇄ spec ⇄ lệnh đo

| AC | Spec | Bất biến | Lệnh chấm |
|---|---|---|---|
| **A1** | §3.2 D3/D7/D8 | INV-UX5-1/2/3 | TC-UX5-20/21/22 |
| **A2** | §3.1 + §3.4 | INV-UX5-8 | `git diff --stat` trên 20 đường dẫn (§7.4) |
| **A3** | §2.4 + §3.2 D4 | INV-UX5-4 | TC-UX5-23/24, TC-UX5-09 |
| **A4** | §2.2 + §2.4 | INV-UX5-5/6 | TC-UX5-25/26/27, TC-UX5-03..06 |
| **A5** | §2.4 `deactivate` | INV-UX5-7 | TC-UX5-28, TC-UX5-07 |
| **A6** | §4 + §5.4 | INV-UX5-11 | `vitest run CommandPalette.test.ts` (7/7) + TC-UX5-32/33 |
| **A7** | §3.1 | — | `vitest run BaseModalResponsive.test.ts` (4/4) |
| **A8** | §5.2 + §5.3 | INV-UX5-9/10 | TC-UX5-30/31 |
| **A9** | §7.4 khối A9 | — | mutation 2 chiều, ghi lại output cả 2 lần |
| **A10** | §1.3 | — | `find src -name "*.test.ts" \| wc -l` ⇒ **312** (308 + 4) · `vitest run` 0 đỏ |
| **A11** | §0 Never | — | `git status --short -- '*.py'` rỗng |
| **A12** | §9–§13 | INV-UX5PLAN-1..8 | `vitest run src/router/uiFixPlanParity.test.ts` |
| **A13** | §0 Always | — | Chuỗi mới duy nhất trong vòng: **không có** (BaseModal chỉ thêm thuộc tính ARIA; `aria-label="Đóng"` đã là tiếng Việt). Guard `uiPrimitiveHygiene` không đổi. |

---

## §16. Rủi ro & việc để lại

| # | Rủi ro | Giảm thiểu |
|---|---|---|
| R1 | Auto-focus của `BaseModal` làm đỏ test cũ đang mount view có modal (36 điểm dùng) | Chạy **toàn** suite trước khi khai xong; test đỏ vì assert focus ⇒ sửa test; đỏ vì lý do khác ⇒ hoàn nguyên + báo BA (§8.10) |
| R2 | `document`-level ESC listener chồng nhau khi nhiều modal | Ngăn xếp topmost (§2.3) + TC-UX5-10/13 |
| R3 | Bộ lọc `isVisible` rộng hơn `offsetParent` ⇒ palette có thêm tabbable ở trình duyệt thật | Đã ghi ở §4 là **đổi có chủ đích**; 7 TC cũ không chạm Tab |
| R4 | Guard overlay bỏ sót overlay khai bằng CSS scoped | Ghi rõ ở §5.5; mở rộng ⇒ `[ROADMAP Đợt E]` |
| R5 | Ước lượng §13 bị đọc thành cam kết tiến độ | Đã gắn nhãn ở §9.4; đơn giá suy từ vòng 3–4, đo lại sau mỗi đợt |
| R6 | Bảng §11 và `00 §3.1` trôi khỏi nhau khi thêm route | INV-UX5PLAN-1/2/5 đỏ ngay |

**Để lại (không thuộc vòng 5):**
- **AC-UX-049** — gỡ 5 hardcode `workflow_state === 'Draft'` ở `ProcurementPlanDetailView`: **hard-dependency vào BE** (`get_procurement_plan` phải emit `can_edit`). Sửa FE trước = tạo dead-control (LL-FE-47).
- **AC-UX-039** — `FormField` / `IconButton` / `ClickableRow` / `PageTitle`: điều kiện tiên quyết của đợt D.
- **AC-UX-040** — bẫy deep-merge `neutral` của Tailwind (52 lần dùng ở 8 file ngoài `ui/`).
- **`confirm()` trần** — **42** call-site / **28** file (đo lại 2026-08-04; số cũ «44/31» đếm thiếu strip-comment). Thay bằng `await useNotify().confirm()` theo lô (§10.6) — lô 1 có hợp đồng riêng ở [`06_CONFIRM_DIALOG_SSOT.md`](./06_CONFIRM_DIALOG_SSOT.md), sổ **AC-UX-064/065/066**.
- Mở rộng guard overlay sang `<style>` scoped (§5.5).

---

## §17. Quyết định kiến trúc

Ba ADR của vòng 5 nằm ở **sổ ADR chung** `00_AUDIT_HIEN_TRANG.md §9` (giữ 1 nơi duy nhất, đúng tiền lệ ADR-UX-01…07):

- **ADR-UX-08** — `BaseModal` là **tier-1** `components/common/`, **KHÔNG** thành primitive #9; hợp đồng hộp thoại cài tại SSoT ⇒ 19 file tiêu thụ 0 dòng sửa; id tiêu đề sinh bằng bộ đếm **module** chứ không `useId()`.
- **ADR-UX-09** — `useFocusTrap` là **nguồn duy nhất** của Tab-wrap + return-focus; điều phối phím bằng `handleTabKey()` do component gọi (**không** listener `keydown` toàn cục cho Tab); `Escape` có **đúng 1 chủ sở hữu**/hộp thoại; ngăn xếp topmost; cấm dùng `offsetParent` để lọc hiển thị.
- **ADR-UX-10** — **bộ dò `ui-audit-inventory.mjs` là SSoT cho DELTA**; bảng tay `00 §3.1` đóng băng làm ảnh chụp vòng 1 ⇒ **đóng AC-UX-031**.

---

## §18. Tiến độ đợt C — nhóm «Chi tiết» (cập nhật 2026-08-04, vòng 10)

> Mục này **chỉ ghi số đo được từ đĩa**. Bảng §10.2 (nhóm «Chi tiết» — 34 route) và bảng §11 (135 route)
> **KHÔNG đổi**: chúng là bản đồ phân hoạch, không phải bảng tiến độ (`uiFixPlanParity` đang khoá cả hai).

### 18.1 Adoption `DetailPageShell` — họ `*DetailView.vue`

| Mốc | Vòng | Phép đo (`grep -rl "from '@/components/common/DetailPageShell.vue'" --include='*DetailView.vue' src/views`) | Kết quả |
|---|---|---|---|
| Dựng khuôn + 3 màn đầu | 4 | 3 / 32 | ĐÃ ĐÓNG |
| **Lô 1** — 8 màn ([`03 §12`](./03_DETAIL_PAGE_SHELL.md)) | 9 | 11 / 32 | ĐÃ ĐÓNG (2026-08-03) |
| **Lô 2 — 21 màn CÒN LẠI** ([`03 §13`](./03_DETAIL_PAGE_SHELL.md)) | **10** | **32 / 32**, non-adopter **0** | **ĐÃ ĐÓNG (2026-08-04)** |

Sau lô 2, nợ adoption lớp chi tiết bị **đóng băng ở 0** bằng guard `AC-UX-071` — cùng cơ chế CHỈ-GIẢM hai
chiều đã đóng lớp danh sách ở 40/40 (`AC-UX-070`). Đây là lần đầu **cả hai** họ khuôn (`ListPageShell` +
`DetailPageShell`) hết nợ adoption cùng lúc.

**Nghiệm thu lô 2 — số ĐO LẠI TỪ ĐĨA sau khi FE land (2026-08-04):**

| Đại lượng | Lệnh (chạy tại `frontend/`) | Trước lô 2 | Sau lô 2 |
|---|---|---|---|
| Adopter `DetailPageShell` | `grep -rl "from '@/components/common/DetailPageShell.vue'" --include='*DetailView.vue' src/views \| wc -l` | 11 / 32 | **32 / 32** |
| Non-adopter (`NON_ADOPTER_BUDGET`) | guard `views/detailShellAdoption.test.ts` | 21 | **0** (sổ RỖNG) |
| `useDetailAccess` | `grep -rl useDetailAccess --include='*DetailView.vue' src/views \| wc -l` | 3 | **21** |
| Gọi trực tiếp `loadErrorKind(` | `grep -rln "loadErrorKind(" --include='*DetailView.vue' src/views \| wc -l` | 14 | **11** (= đúng sổ legacy) |
| Import trực tiếp `DetailTabBar` ở `*DetailView` | `grep -rl "import DetailTabBar" --include='*DetailView.vue' src/views \| wc -l` | 7 | **0** (hoisting, `ADR-UX-25`) |
| Màn chi tiết 0-lối-nạp-lại (token `NO-DET`) | vòng lặp `grep -qE 'DetailLoadError\|@retry\|DetailPageShell'` | 12 | **0** |
| Ô ❌ cột *Lỗi+Thử lại* (token `NO-CON`) | `node scripts/ui-audit-inventory.mjs --summary` | 57 | **50** (bộ dò lật 7 ô) |
| Suite FE | `npx vitest run` | 377 file / 3731 test | **400 file / 3993 test — 0 đỏ** |
| Kiểu | `npx vue-tsc --noEmit` | 0 lỗi | **0 lỗi** |

Delta file test = **+23** đúng bằng dự báo (21 file `*DetailStates.test.ts` + 2 guard). 21 file trạng thái
dùng chung khung `src/test/detailStatesHarness.ts` — **một** bộ sub-case (a)…(f) + (g) cho màn có tab, thay
vì 21 bản chép tay mà bản thứ 22 sẽ quên đúng sub-case (d) «0 nút chết».

### 18.2 Ba số hiệu MỚI cấp ở vòng 10 (sổ trên đĩa trước đó max = **070**)

| Mã | Nội dung | Nơi đặc tả |
|---|---|---|
| **AC-UX-071** | Guard `views/detailShellAdoption.test.ts` — ngân sách adoption khuôn CHI TIẾT, `TOTAL_DETAIL_VIEWS = 32`, CHỈ-GIẢM hai chiều, `NON_ADOPTER_BUDGET` rỗng cuối vòng | [`03 §13.7.1`](./03_DETAIL_PAGE_SHELL.md) |
| **AC-UX-072** | Guard `views/detailAccessAdoption.test.ts` — SSoT lỗi nạp `useDetailAccess`; `LEGACY_LOCAL_KIND_BUDGET` đóng băng **11** file, chỉ được xoá dòng | [`03 §13.7.2`](./03_DETAIL_PAGE_SHELL.md) |
| **AC-UX-073** | Chống **2 thanh tab**: quyết định hoisting `:tabs` + `active-tab` lên shell cho 7 màn — `ADR-UX-25` | [`03 §13.4.2`, `§13.11`](./03_DETAIL_PAGE_SHELL.md) |

`AC-UX-053` (hợp đồng `useDetailAccess` ⇄ shell) **đóng phần quyết định** bằng `ADR-UX-27`: giữ **3 prop rời**
ở shell, nguồn bắt buộc là composable ở phía view.

### 18.3 Hai đính chính BA (số trong prompt không đo được từ đĩa)

1. **`useDetailAccess` 3 → ~~24~~ 21.** 3 màn đang dùng composable (`pm` · `cm` · `incident`) **nằm trong**
   21 màn của lô ⇒ trần đo được là 21, không phải 3 + 21. 11 màn legacy bị chính acceptance A2 đóng băng.
2. **Baseline suite = 377 file / 3731 test — 0 đỏ** (đo `npx vitest run` sau bước BA, 2026-08-04 16:59),
   không phải 340/3352. Kỳ vọng cuối vòng: **400** file (+21 trạng thái, +2 guard), vẫn 0 đỏ —
   **thực đo sau khi FE land: đúng 400 file / 3993 test, 0 đỏ.**

### 18.4 Việc để lại sau lô 2 (KHÔNG thuộc vòng 10)

- **11 màn legacy** còn `loadErrorKind` cục bộ — di trú sang `useDetailAccess` theo lô riêng; sổ CHỈ-GIẢM của
  `AC-UX-072` là thước đo.
- **AC-UX-052 lô 2** — 7 nút-tab tự chế còn lại ở 6 file **ngoài** họ `*DetailView` (`TechSpec` ·
  `VendorEval` · `UomConversion` · `ReferenceData` · `CommissioningForm` · `AssetDashboard`).
- **AC-UX-049** — 5 hardcode `workflow_state === 'Draft'` ở `ProcurementPlanDetailView`: vẫn chặn bởi
  hard-dependency BE (`get_procurement_plan` phải emit `can_edit`). Bọc shell **không** gỡ được nợ này.
- **AC-UX-055/056** — di trú overlay tự vẽ: **12/21** màn của lô nằm trong allowlist đóng băng, cố ý không đụng.
