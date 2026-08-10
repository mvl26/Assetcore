# 06 — Diệt `confirm()` trần: một SSoT hộp thoại xác nhận (`NotificationModal` → `BaseModal`)

| Mục | Giá trị |
|---|---|
| Module | **IMM-00** (nền FE dùng chung) — hưởng lợi: IMM-03/05/07/08/10/15 |
| Sổ backlog | **AC-UX-064** (hợp nhất SSoT render + ESC, P0) · **AC-UX-065** (quy ước gọi + di trú lô 1, P1) · **AC-UX-066** (guard ngân sách CHỈ-GIẢM, P1) |
| Kế thừa | **AC-UX-058** (mở sổ vòng 5) — tài liệu này là hợp đồng thi hành của nó |
| SSoT chạm | `frontend/src/components/common/NotificationModal.vue` · `frontend/src/components/common/BaseModal.vue` · `frontend/src/composables/useNotify.ts` |
| Trạng thái | **Spec ĐÃ CHỐT — sẵn sàng cho [FE]** (BA đóng Bước 2, vòng 1 / run-7) |
| Cập nhật | 2026-08-04 |

## Tài liệu liên quan
- [`00_AUDIT_HIEN_TRANG.md §6`](./00_AUDIT_HIEN_TRANG.md) — sổ backlog AC-UX (nay **66** mục)
- [`04_PHUONG_AN_SUA_TOAN_BO.md §3`](./04_PHUONG_AN_SUA_TOAN_BO.md) — hợp đồng a11y `BaseModal` (vòng 5). Tài liệu **06** kế thừa nguyên **§3.1 bất biến 0-churn** và chỉ THÊM.
- [`04 §5.2/§5.3`](./04_PHUONG_AN_SUA_TOAN_BO.md) — allowlist overlay tự vẽ (**30 → 29** sau vòng này) và file lai (**4**, không đổi).
- [`05_MODAL_INLINE_ERROR.md`](./05_MODAL_INLINE_ERROR.md) — lỗi CHẶN hiện inline (ADR-UX-13/14/15). Vòng này **không** đụng vùng lỗi inline.
- Core Doc module: [`docs/imm-00/06_Frontend_Design.md`](../imm-00/06_Frontend_Design.md)

---

## §0. Phạm vi & Boundaries

**Always (luôn áp dụng):**
- Mọi hộp thoại **xác nhận** của người dùng đi qua **một chuỗi SSoT duy nhất**: view → `useNotify().confirm()` → `useModal().confirm()` → hàng đợi → `NotificationModal` → `BaseModal` (ADR-UX-16).
- `NotificationModal` **render qua `BaseModal`** — không tự vẽ overlay, không tự cài a11y, không tự nghe phím.
- Một hộp thoại có **đúng 1 chủ sở hữu phím `Escape`** (kế thừa ADR-UX-09).
- 100% chuỗi hiển thị là **tiếng Việt** (LL-FE-53); nút mặc định «Xác nhận» / «Huỷ».
- Hành động **phá huỷ / không hoàn tác** (xoá, huỷ đơn, huỷ phiếu, sinh lại lịch) ⇒ `tone: 'error'` ⇒ `BaseModal` nhận `danger`.

**Ask first (hỏi BA trước khi làm):**
- Thay đổi bất kỳ prop / emit / testid / class **đã có** của `BaseModal` (vi phạm bất biến 0-churn `04 §3.1` — xem §3.4).
- Thay đổi **hợp đồng đối ngoại** của `useModal()` (`alert` / `confirm` / `dismiss` / `queue`, `tone`, `confirmText` / `cancelText`).
- Di trú thêm file ngoài **7 file lô 1** ở §5 (mỗi lô phải có số hiệu và bảng riêng).
- Gỡ overlay tự vẽ của 5 file lô 1 đang nằm trong allowlist `04 §5.2` — đó là **AC-UX-055**, KHÔNG phải vòng này.

**Never (tuyệt đối không):**
- Không gọi `confirm(...)` / `window.confirm(...)` / `globalThis.confirm(...)` trần trong bất kỳ `.vue` nào — kể cả “tạm thời để test cho nhanh”.
- Không gọi `useModal()` **trực tiếp từ view** (đó là tầng hàng đợi, không phải API của view — ADR-UX-16).
- Không để `NotificationModal` giữ `addEventListener('keydown', …)` sau vòng này (ESC kép — §4).
- Không thêm dòng vào allowlist `ALLOWLIST_SELF_DRAWN` hay bản đồ ngân sách `bareConfirmBudget` (cả hai **CHỈ-GIẢM**).
- Không đổi **nghĩa** câu xác nhận đang có; không sinh chuỗi tiếng Anh mới.
- Không dùng `vi.stubGlobal('confirm', …)` trong test mới.

---

## §1. Baseline đo từ đĩa 2026-08-04 — **đè lên mọi số cũ**

### 1.1 Công thức đúng (bắt buộc STRIP COMMENT)

```bash
# Bước 1 — quét thô (đây là công thức cũ ở 04 §10.6, KHÔNG đủ):
grep -rn "[^.a-zA-Z_]confirm(" frontend/src/views frontend/src/components --include=*.vue
#   ⇒ 47 match / 31 file

# Bước 2 — BỎ dòng chú thích trước khi đếm (HTML `<!-- -->`, block `/* */`, dòng `//`).
#   Cài đặt tham chiếu: hàm stripComments() của
#   frontend/src/components/common/modalOverlayHygiene.test.ts:23
```

| Số đo | Giá trị đúng (2026-08-04) |
|---|---|
| Match thô | **47** / **31** file |
| Dòng là **chú thích** | **5** |
| **Call-site THẬT** | **42** |
| **File THẬT** | **28** |

**5 dòng chú thích** (không phải nợ, đừng “sửa”):
`views/needs/ProcurementPlanDetailView.vue:38` · `:129` · `:257` · `views/calibration/CalibrationDetailView.vue:898` · `components/common/NotificationModal.vue:2`.

### 1.2 BA Self-Correction — ba con số đang lưu hành đều SAI

| Nguồn | Ghi | Đúng | Nguyên nhân |
|---|---|---|---|
| `04 §1.2` (dòng 71) · `04 §10.6` (677) · `04 §16` (935) · `00 §6` (563) | **44 / 31** | **42 / 28** | Đếm thô, **không** strip comment; và số đo đã cũ |
| Prompt vòng 6 (run-6) | **49 / 33** | **42 / 28** | Đếm thô trên cây bẩn |
| Prompt vòng 1 (run-7) | 42 / **29** | 42 / **28** | Call-site đúng; **số file lệch 1** — 3 file (`ProcurementPlanDetailView`, `CalibrationDetailView`, `NotificationModal`) chỉ có chú thích ⇒ 31 − 3 = **28** |

> **Luật rút ra (ghi vào sổ):** mọi con số nợ trong doc phải kèm **công thức tái lập được**, và công thức nào đếm mã nguồn thì **phải strip comment**. Số không kèm lệnh = số sẽ rot.

### 1.3 Bản đồ per-file (mẫu số chấm DELTA)

| # | File (`frontend/`) | Call-site | Lô |
|---|---|---|---|
| 1 | `src/views/purchase/PurchaseDetailView.vue` | 5 | **1** |
| 2 | `src/views/inventory/UomConversionView.vue` | 4 | **1** |
| 3 | `src/views/asset/AssetTransferDetailView.vue` | 3 | **1** |
| 4 | `src/views/inventory/StockMovementDetailView.vue` | 3 | **1** |
| 5 | `src/components/asset/AssetDepreciationSchedule.vue` | 2 | **1** |
| 6 | `src/views/document/DocumentDetailView.vue` | 2 | **1** |
| 7 | `src/views/pm/PmTemplateListView.vue` | 2 | **1** |
| 8–28 | 21 file còn lại, **1 call-site mỗi file** (liệt kê ở §6.3) | 21 | 2+ |
| | **Tổng** | **42 / 28 file** | |

**Đích sau vòng này: 21 call-site / 21 file** (giảm **21** = **50,0%** nợ, đóng 7 file nặng nhất).

---

## §2. Kiến trúc SSoT — 4 tầng, mỗi tầng đúng 1 việc

```
  View (.vue)                 ← CHỈ tầng này được gọi
       │  await notify.confirm({ title, body, tone?, confirmText?, cancelText? }) : Promise<boolean>
       ▼
  composables/useNotify.ts    ← Façade: render mã thông điệp (MSG), gán mặc định
       │  modal.confirm({...})
       ▼
  composables/useModal.ts     ← Hàng đợi (FIFO) + resolve promise. KHÔNG render.
       │  queue: Ref<ModalRequest[]>
       ▼
  components/common/NotificationModal.vue   ← Render item[0] của hàng đợi
       │  <BaseModal>
       ▼
  components/common/BaseModal.vue           ← Overlay + a11y + bẫy focus + ESC (SSoT)
```

**Hiện trạng lệch (đo 2026-08-04):**
- `useNotify.ts:127-144` **đã** uỷ nhiệm cho `modal.confirm` — chuỗi trên đã đúng từ tầng 2 xuống 3.
- `NotificationModal.vue` **tự vẽ** overlay (`:48` `fixed inset-0 … z-[10000]`) và **tự nghe** ESC (`:39`) ⇒ tầng 4 rẽ nhánh khỏi `BaseModal`, không hưởng bẫy focus / trả focus / `aria-labelledby` theo instance.
- View tiêu thụ: **7 call-site** dùng đúng `notify.confirm` (`procurement/DecisionDetailView` ×2 · `procurement/AvlListView` · `procurement/VendorEvalDetailView` · `eol/DecommissionDetailView` · `document/FirmwareCrDetailView` ×2); **0** view gọi `useModal()` trực tiếp.

⇒ Quy ước gọi của view **đã tồn tại và đã có test**; vòng này chỉ **lan rộng** nó và **hàn** tầng 4.

---

## §3. Delta chính xác trên `NotificationModal.vue` (AC-UX-064)

### 3.1 Bất biến — hợp đồng đối ngoại `useModal()` GIỮ NGUYÊN TUYỆT ĐỐI

`alert` · `confirm` · `dismiss` · `queue` · `ModalKind` · `ModalRequest` (mọi field, kể cả `tone`, `confirmText`, `cancelText`, `actionHint`) **không đổi 1 ký tự**.
`frontend/src/composables/useModal.ts` phải có **0 dòng thay đổi** trong vòng này (`git diff --stat` = rỗng cho file đó).

### 3.2 Ánh xạ trạng thái → prop `BaseModal`

| `ModalRequest` | → `BaseModal` | Ghi chú |
|---|---|---|
| `current.title` | `:title` | `BaseModal` tự render `<h2 :id>` + `aria-labelledby` |
| `current.tone ∈ {critical, error}` | `:danger="true"` | tiêu đề đỏ + viền đỏ |
| `current.tone ∈ {warning, info}` | `:danger="false"` | |
| — | `size="md"` | tương đương `max-w-md` hiện tại |
| `current.body` / `actionHint` | slot mặc định | giữ `whitespace-pre-line` (chuỗi có `\n`) |
| `current.kind` / `confirmText` / `cancelText` | slot `#footer` | §3.3 |
| — | `:error` / `:errorTitle` | **KHÔNG dùng** — hộp thoại xác nhận chưa có lỗi chặn |

**Bắt buộc:** `<BaseModal v-if="current" …>`. `BaseModal` **không** có `v-if` nội tại — mount là render overlay. Thiếu `v-if` ⇒ nền mờ phủ toàn app vĩnh viễn.

### 3.3 Nút và thứ tự DOM ở `#footer`

Footer của `BaseModal` là `flex-col-reverse … sm:flex-row sm:justify-end` ⇒ **DOM order = phụ trước, chính sau** (mobile lật ngược để nút chính nằm trên).

```
#footer:
  1) <button v-if="current.kind === 'confirm'" @click="onCancel">  {{ current.cancelText }}   ← phụ
  2) <button @click="onConfirm">
       {{ current.kind === 'confirm' ? current.confirmText : 'Đã hiểu' }}                     ← chính
```
- `kind === 'alert'` ⇒ **1 nút** «Đã hiểu», `onConfirm` → `dismiss(id, true)` → `resolve()` (alert resolve void).
- Giữ nguyên quy tắc màu: `danger` ⇒ nút chính đỏ; ngược lại xanh.

### 3.4 Ba đường đóng hộp thoại — đều là **huỷ**

`BaseModal` phát `close` từ **3** nguồn: `Escape` (qua `useFocusTrap`), click nền (`@click.self`), nút **✕** ở đầu bài.
⇒ `<BaseModal @close="onCancel">`. Cả 3 đều `dismiss(id, false)` — đúng ngữ nghĩa cũ (ESC/backdrop = huỷ).

> **Thay đổi hữu hình duy nhất:** xuất hiện thêm nút **✕** (`BaseModal` luôn render, không có prop tắt). **Chấp nhận** — hành vi của nó trùng khít backdrop/ESC vốn đã có. **KHÔNG** thêm prop `hideClose` vào `BaseModal` để né (vi phạm bất biến 0-churn §3.1 và làm 19 file tiêu thụ phải cân nhắc thêm 1 prop).

### 3.5 Tầng xếp chồng (`z-index`) — delta THÊM duy nhất trên `BaseModal`

**Vấn đề:** `NotificationModal` hiện ở `z-[10000]`, `BaseModal` ở `z-50`. Sau khi hợp nhất, hộp thoại **chặn hệ thống** (lỗi `critical`, xác nhận phá huỷ) tụt xuống cùng tầng với hộp thoại nghiệp vụ của màn ⇒ thứ tự vẽ chỉ còn phụ thuộc thứ tự `Teleport` chèn vào `body`.

**Quyết định (ADR-UX-17):** thêm **1 prop tuỳ chọn** `layer` cho `BaseModal`, mặc định giữ nguyên `z-50`:

```ts
layer?: 'default' | 'system'   // mặc định 'default'
```
| `layer` | class overlay |
|---|---|
| `'default'` (mặc định) | `z-50` — **19 file tiêu thụ: 0 dòng đổi, class y hệt hôm nay** |
| `'system'` | `z-[10000]` — chỉ `NotificationModal` truyền |

**Bẫy Tailwind JIT:** hai chuỗi `'z-50'` và `'z-[10000]'` phải là **literal** trong `BaseModal.vue` (ternary trong `:class` hoặc map hằng ở `<script>`). Ghép chuỗi động (`` `z-[${n}]` ``) ⇒ JIT không sinh class ⇒ overlay mất z-index câm.

Đây là **THÊM tuỳ chọn**, cùng khuôn với `error`/`errorTitle` của AC-UX-062 ⇒ không vi phạm §3.1.

### 3.6 Kết quả grep bắt buộc sau vòng

```bash
cd frontend
grep -c 'fixed inset-0'            src/components/common/NotificationModal.vue   # = 0
grep -c "addEventListener('keydown'" src/components/common/NotificationModal.vue # = 0
grep -c 'BaseModal'                src/components/common/NotificationModal.vue   # ≥ 2 (import + thẻ)
git diff --stat -- src/composables/useModal.ts                                   # rỗng
```

---

## §4. Bẫy P1 — ESC kép **KHÔNG** phải “resolve 2 lần”, mà là **nuốt hộp thoại kế tiếp**

### 4.1 Đính chính (BA Self-Correction so với đề mục vòng)

Đề mục ghi: *“hiện tại 2 listener = dismiss 2 lần ⇒ `resolve` gọi 2 lần”*. **Sai** — đọc `useModal.ts:70-76`:

```ts
function dismiss(id: number, ok: boolean) {
  const idx = queue.value.findIndex(m => m.id === id)
  if (idx < 0) return          // ← lần gọi thứ 2 với CÙNG id thoát ở đây
  …
  req.resolve(ok)
}
```
`dismiss` **bình phương-bất biến theo `id`** ⇒ với hàng đợi 1 phần tử, `resolve` vẫn chỉ chạy **1 lần**. Một test viết theo mô tả sai sẽ **XANH GIẢ** và không chứng minh được gì.

### 4.2 Lỗi THẬT (P1, tái lập được)

Hai listener cùng sống: `useFocusTrap` gắn trên `document` (`useFocusTrap.ts:121`), `NotificationModal` gắn trên `globalThis` (`:39`). `keydown` nổi bọt `document` → `window` ⇒ **cả hai chạy trong cùng một lần nhấn**, `useFocusTrap` trước (nó `preventDefault()` nhưng **không** `stopPropagation()`).

`current = computed(() => queue.value[0])`, và `splice` thông báo phụ thuộc **đồng bộ** ⇒ giữa hai handler, `current` **đã trỏ sang phần tử kế tiếp**.

| Nhịp | Handler | `current` đọc được | Hệ quả |
|---|---|---|---|
| 1 | `useFocusTrap` → `emit('close')` → `onCancel` | **A** | `dismiss(A,false)` — A resolve `false` ✔ |
| 2 | `NotificationModal.onKey` → `onCancel` | **B** | `dismiss(B,false)` — **B resolve `false` dù CHƯA từng hiển thị** ✘ |

⇒ **Một lần nhấn ESC huỷ hai xác nhận.** Với hàng đợi ≥2 (lỗi `critical` dồn, hoặc user bấm nhanh 2 hành động) người dùng mất một quyết định mà không hề thấy nó.

### 4.3 Cách sửa + ca kiểm thử bắt buộc

Sửa: **xoá** `onKey` + cặp `onMounted`/`onBeforeUnmount` ở `NotificationModal.vue:35-40`. `Escape` để `BaseModal`→`useFocusTrap` sở hữu (ADR-UX-09: đúng 1 chủ sở hữu).

| TC | Dựng | Hành động | Khẳng định |
|---|---|---|---|
| **TC-UX6-01** | 1 `confirm` trong hàng đợi | nhấn `Escape` **1 lần** | promise resolve `false` **đúng 1 lần**; `queue.length === 0` |
| **TC-UX6-02** | **2** `confirm` (A rồi B) | nhấn `Escape` **1 lần** | A resolve `false`; **B CHƯA resolve**; `queue.length === 1`; hộp thoại vẫn hiển thị tiêu đề của **B** |
| **TC-UX6-03** | 1 `confirm` | click **nền** | resolve `false`, đúng 1 lần |
| **TC-UX6-04** | 1 `confirm` | click **✕** | resolve `false`, đúng 1 lần |
| **TC-UX6-05** | 1 `confirm` | click nút chính | resolve `true`, đúng 1 lần |
| **TC-UX6-06** | 1 `alert` | nhấn `Escape` | resolve (void) đúng 1 lần; **không** có nút «Huỷ» trong footer |
| **TC-UX6-07** | 1 `confirm` `tone:'error'` | mount | `modal-card` mang dấu hiệu `danger` (tiêu đề đỏ); overlay có `z-[10000]` |

> **TC-UX6-02 là ca chứng minh.** Revert bản sửa ⇒ TC-UX6-02 phải ĐỎ. Nếu revert mà vẫn xanh thì test chưa chứng minh gì (đo lại).

---

## §5. Di trú lô 1 — 7 file / 21 call-site (danh sách ĐÓNG BĂNG, AC-UX-065)

### 5.1 Khuôn thay thế

```ts
// TRƯỚC
if (!confirm('…')) return

// SAU  (hàm bao đã là `async` ở cả 21 vị trí — đã kiểm tra)
const notify = useNotify()          // đặt ở <script setup>, KHÔNG trong hàm
…
const ok = await notify.confirm({ title: '…', body: '…', tone: '…', confirmText: '…' })
if (!ok) return
```

**Delta bắt buộc trên `useNotify.ts`** — `ConfirmOpts` (`:31-40`) hiện **thiếu `tone`** nên không diễn đạt được hành động phá huỷ. Thêm **1 field tuỳ chọn** và chuyển tiếp nguyên vẹn:

```ts
interface ConfirmOpts {
  …
  tone?: 'error' | 'warning' | 'info' | 'critical'   // THÊM
}
// và ở modal.confirm({...}) : tone: opts.tone      // THÊM 1 dòng
```
Không truyền ⇒ `useModal` giữ mặc định `'warning'` ⇒ **7 call-site `notify.confirm` đang có: 0 dòng đổi, 0 đổi hành vi.**

### 5.2 Bảng copy — nguyên văn, **[FE] không tự nghĩ chữ**

`tone: 'error'` = phá huỷ / không hoàn tác (⇒ `danger`). `tone: 'warning'` = mặc định.
Nút mặc định «Xác nhận» / «Huỷ» — chỉ ghi `confirmText` khi cần động từ rõ hơn.

**1) `src/views/purchase/PurchaseDetailView.vue` (5)**

| Dòng | `title` | `body` | `tone` | `confirmText` |
|---|---|---|---|---|
| 80 | Tạo phiếu tiếp nhận | Tạo phiếu tiếp nhận cho thiết bị này? | `warning` | Tạo phiếu |
| 92 | Duyệt đơn hàng | Xác nhận duyệt đơn hàng này? | `warning` | Duyệt |
| 100 | Xác nhận nhận hàng | Xác nhận đã nhận đủ hàng? | `warning` | Đã nhận đủ |
| 108 | Huỷ đơn hàng | Xác nhận huỷ đơn hàng này? | **`error`** | Huỷ đơn |
| 116 | Xoá đơn nháp | Xoá đơn nháp này? Hành động không thể hoàn tác. | **`error`** | Xoá |

**2) `src/views/inventory/UomConversionView.vue` (4)**

| Dòng | `title` | `body` | `tone` | `confirmText` |
|---|---|---|---|---|
| 56 | Xoá đơn vị tính | Xoá đơn vị "{name}"?\nNếu đang được dùng sẽ chỉ ngừng sử dụng. | **`error`** | Xoá |
| 64 | Tạo danh mục chuẩn | Tạo danh mục đơn vị tính chuẩn y tế Việt Nam (bỏ qua các đơn vị đã có)? | `warning` | Tạo danh mục |
| 112 | Gán đơn vị tính mặc định | Gán "{uom}" cho {n} phụ tùng thiếu đơn vị tính? | `warning` | Gán |
| 152 | Xoá quy đổi | Xoá quy đổi "{uom}"? | **`error`** | Xoá |

> `:152` là biểu thức **ngắn mạch**: `if (!convPart.value || !confirm(…)) return`. Tách làm 2 câu lệnh — kiểm `convPart` **trước**, chỉ mở hộp thoại khi đã có phụ tùng.
> `:64` — «UOM» dịch thành «đơn vị tính» theo LL-FE-53 (nghĩa giữ nguyên).

**3) `src/views/asset/AssetTransferDetailView.vue` (3)**

| Dòng | `title` | `body` | `tone` | `confirmText` |
|---|---|---|---|---|
| 130 | Phê duyệt luân chuyển | Phê duyệt phiếu luân chuyển này? Vị trí thiết bị sẽ được cập nhật ngay. | `warning` | Phê duyệt |
| 153 | Xác nhận tiếp nhận | Xác nhận đã tiếp nhận thiết bị tại vị trí mới? | `warning` | Đã tiếp nhận |
| 165 | Huỷ phiếu luân chuyển | Huỷ phiếu "{name}"? | **`error`** | Huỷ phiếu |

**4) `src/views/inventory/StockMovementDetailView.vue` (3)**

| Dòng | `title` | `body` | `tone` | `confirmText` |
|---|---|---|---|---|
| 42 | Duyệt phiếu kho | Xác nhận duyệt phiếu này? Tồn kho sẽ được cập nhật. | `warning` | Duyệt |
| 55 | Xoá phiếu nháp | Xoá phiếu nháp này? Hành động không thể hoàn tác. | **`error`** | Xoá |
| 69 | Huỷ phiếu kho | Xác nhận huỷ phiếu? Tồn kho sẽ được hoàn nguyên. | **`error`** | Huỷ phiếu |

**5) `src/components/asset/AssetDepreciationSchedule.vue` (2)**

| Dòng | `title` | `body` | `tone` | `confirmText` |
|---|---|---|---|---|
| 35 | Sinh lại lịch khấu hao | Xoá lịch hiện tại và sinh lại từ đầu? | **`error`** | Sinh lại |
| 48 | Chạy khấu hao đến hạn | Chạy ngay các kỳ khấu hao đến hạn? (chỉ Quản trị hệ thống được phép) | `warning` | Chạy ngay |

> `:48` — «System Manager» dịch thành «Quản trị hệ thống» (LL-FE-53).

**6) `src/views/document/DocumentDetailView.vue` (2)**

| Dòng | `title` | `body` | `tone` | `confirmText` |
|---|---|---|---|---|
| 192 | Lưu trữ tài liệu | Lưu trữ tài liệu này theo NĐ98 (lưu trữ 10 năm, không thể xoá). Tiếp tục? | **`error`** | Lưu trữ |
| 211 | Phê duyệt tài liệu | Phê duyệt tài liệu này sẽ tự động lưu trữ phiên bản cũ. Tiếp tục? | `warning` | Phê duyệt |

**7) `src/views/pm/PmTemplateListView.vue` (2)**

| Dòng | `title` | `body` | `tone` | `confirmText` |
|---|---|---|---|---|
| 163 | Xoá mẫu bảo trì | Xoá mẫu bảo trì "{name}"? | **`error`** | Xoá |
| 175 | Áp mẫu cho danh mục | Tạo lịch bảo trì định kỳ cho mọi thiết bị thuộc danh mục "{cat}" theo mẫu "{tpl}"?\n\nThiết bị đã có lịch cùng loại bảo trì định kỳ sẽ được giữ nguyên. | `warning` | Áp dụng |

> `:163`/`:175` — «template» dịch thành «mẫu bảo trì» (LL-FE-53); biến `msg` ghép sẵn ở `:172-174` chuyển thẳng vào `body`.

### 5.3 Bất biến của lô 1

- **7 file → đúng 0** call-site `confirm(` trần sau vòng.
- **Không** gỡ overlay tự vẽ của 5 file lô 1 đang ở `ALLOWLIST_SELF_DRAWN` (`AssetTransferDetailView` · `DocumentDetailView` · `PmTemplateListView` · `PurchaseDetailView` · `UomConversionView`) ⇒ allowlist `04 §5.2` chỉ giảm **đúng 1 dòng** (`NotificationModal.vue`), **30 → 29**.
- Không đụng luồng gọi API, không đổi tên hàm, không đổi `data-testid` đang có.

---

## §6. Guard ngân sách CHỈ-GIẢM — `frontend/src/components/common/bareConfirmBudget.test.ts` (MỚI, AC-UX-066)

### 6.1 Vì sao cần

Allowlist theo **tên file** (khuôn `modalOverlayHygiene`) không chặn được hồi quy trong file **đã có tên trong danh sách**: `PurchaseDetailView` từ 5 → 0 rồi lặng lẽ về 3 vẫn “hợp lệ”. ⇒ ngân sách phải theo **cặp (file, số lần)**.

### 6.2 Thuật toán

1. Liệt kê `.vue` dưới `src/views` + `src/components`.
2. `stripComments()` — **dùng lại nguyên hàm** ở `modalOverlayHygiene.test.ts:23` (HTML `<!-- -->`, block `/* */`, dòng `//`). Không viết bản thứ hai.
3. Đếm khớp `/[^.a-zA-Z_]confirm\(/g` **và** `/\b(?:window|globalThis)\.confirm\(/g` (chặn né guard bằng `window.confirm`).
4. So với bản đồ `BUDGET: Record<string, number>`.

### 6.3 Bản đồ ĐÓNG BĂNG sau lô 1 — **21 file × 1 = 21**

```
src/views/asset/AssetDetailView.vue                     1
src/views/asset/AssetTransferListView.vue               1
src/views/asset/DeviceModelFormView.vue                 1
src/views/asset/DeviceModelListView.vue                 1
src/views/compliance/ComplianceRuleListView.vue         1
src/views/compliance/ScorecardView.vue                  1
src/views/document/DocumentManagement.vue               1
src/views/document/DocumentRequestListView.vue          1
src/views/document/FirmwareCrListView.vue               1
src/views/incident/IncidentDetailView.vue               1
src/views/inventory/SparePartDetailView.vue             1
src/views/inventory/WarehouseDetailView.vue             1
src/views/inventory/WarehouseListView.vue               1
src/views/master-data/ReferenceDataView.vue             1
src/views/master-data/SlaPolicyListView.vue             1
src/views/pm/PMWorkOrderDetailView.vue                  1
src/views/pm/PmScheduleListView.vue                     1
src/views/purchase/ServiceContractDetailView.vue        1
src/views/purchase/SupplierDetailView.vue               1
src/views/purchase/SupplierFormView.vue                 1
src/views/purchase/SupplierListView.vue                 1
```

### 6.4 Bất biến (INV-UXCONF-*)

| Mã | Khẳng định | ĐỎ khi |
|---|---|---|
| **INV-UXCONF-1** | tổng ngân sách == **21** và tổng đo được ≤ 21 | thêm call-site bất kỳ |
| **INV-UXCONF-2** | 0 file đo được **ngoài** bản đồ | file mới mọc `confirm(` (tên file hiện trong thông báo) |
| **INV-UXCONF-3** | mỗi file: đo được ≤ hạn mức của nó | hồi quy trong file đã biết |
| **INV-UXCONF-4** | **CHỈ-GIẢM**: file có hạn mức mà đo được **thấp hơn** ⇒ ĐỎ kèm câu *“đã giảm — hãy hạ hạn mức xuống N (hoặc xoá dòng nếu N=0)”* | quên hạ sổ sau khi di trú |
| **INV-UXCONF-5** | 7 file lô 1 **không** xuất hiện trong bản đồ | ai đó thêm lại |

> INV-UXCONF-4 là điều làm guard này khác allowlist thường: nó **ép doc đi theo đĩa** thay vì cho phép trần treo lơ lửng.

---

## §7. Viết lại 4 test đang stub `confirm` (bắt buộc — chống ĐỎ và chống XANH GIẢ)

### 7.1 Đính chính lệnh nghiệm thu

Đề mục yêu cầu `grep -c 'window.confirm' <4 file>` = 0. **Lệnh này vô nghĩa** — đo từ đĩa hôm nay:

| File | `window.confirm` | `stubGlobal('confirm'` |
|---|---|---|
| `src/components/asset/AssetDepreciationSchedule.test.ts` | 0 | **0** |
| `src/views/asset/assetTransferDetailCtaGate.test.ts` | 1 *(trong **chú thích**)* | **1** |
| `src/views/asset/assetTransferDetailEditGate.test.ts` | 0 | **1** |
| `src/views/purchase/purchaseCtaGate.test.ts` | 1 *(trong **chú thích**)* | **1** |

Stub thật viết là `vi.stubGlobal('confirm', vi.fn(() => true))` — chuỗi `window.confirm` chỉ nằm trong lời chú thích. Lệnh đúng:

```bash
grep -c "stubGlobal('confirm'" <file>    # phải = 0 ở cả 4 file
```

`AssetDepreciationSchedule.test.ts` **không hề stub** ⇒ 2 nút của nó hiện chạy vào `confirm()` thật của jsdom (trả `undefined` ⇒ falsy ⇒ **thoát sớm**). Nghĩa là đường thành công của `regenerate()` / `runNow()` **chưa từng được kiểm thử** — không phải “test sẽ đỏ”, mà là **lỗ phủ**. Vòng này phải **thêm** ca cho nhánh xác nhận.

### 7.2 Khuôn harness (dùng chung cho cả 4 file)

Đã có tiền lệ chạy tốt trong repo — `views/modalBlockingErrorAdoption.test.ts:39-42` (mock `useModal`) và `views/eol/decommissionDetailCtaGate.test.ts:128` (spy `notify.confirm`). Dùng lại, **không sáng tác khuôn thứ ba**:

```ts
const notifyConfirm = vi.fn().mockResolvedValue(true)   // mặc định: người dùng bấm Xác nhận
vi.mock('@/composables/useNotify', () => ({
  useNotify: () => ({ confirm: notifyConfirm, show: vi.fn(), fromError: vi.fn(), fromOk: vi.fn() }),
}))
```

**Mỗi file phải có ít nhất 2 ca mới:**
1. **Xác nhận** — `notifyConfirm` resolve `true` ⇒ API **được** gọi đúng 1 lần; `notifyConfirm` được gọi đúng 1 lần.
2. **Huỷ** — resolve `false` ⇒ API **KHÔNG** được gọi (`expect(apiSpy).not.toHaveBeenCalled()`).

Ca “Huỷ” là ca chống XANH GIẢ: nếu [FE] lỡ bỏ `if (!ok) return`, chỉ ca này bắt được.

### 7.3 `await` — bẫy đã biết

`confirm()` trần **đồng bộ**; `notify.confirm()` trả **Promise**. Sau khi đổi, mọi test click nút phải `await flushPromises()` (thường **2 nhịp**: 1 cho promise xác nhận, 1 cho lời gọi API) trước khi khẳng định. Thiếu `await` ⇒ test đỏ tưởng do mã, thực ra do nhịp.

---

## §8. Bẫy đã biết — ĐỌC TRƯỚC KHI CODE

| # | Bẫy | Hệ quả nếu quên |
|---|---|---|
| 1 | `BaseModal` **không** có `v-if` nội tại | thiếu `v-if="current"` ⇒ nền mờ phủ toàn app vĩnh viễn |
| 2 | `dismiss` bình phương-bất biến theo `id` | test “resolve 2 lần” **xanh giả**; ca thật là hàng đợi 2 phần tử (§4.2) |
| 3 | Tailwind JIT không sinh class ghép động | `z-[10000]` biến mất câm ⇒ hộp thoại hệ thống nằm dưới hộp thoại nghiệp vụ |
| 4 | `modalOverlayHygiene.test.ts` chốt `toHaveLength(30)` ở **:126** và `toBe(30)` ở **:127**, `toBeLessThanOrEqual(30)` ở **:141** | xoá dòng allowlist mà quên hạ **3** chỗ số ⇒ guard đỏ |
| 5 | `uiAuditDocParity.test.ts:35` `ROUND_VALUES` — trước bước BA chỉ nhận `{2,3,4,5,6}` | ghi «vòng 7» cho mục mới ⇒ guard **ĐỎ**. **Đã nới thành `{2,…,7}` ở bước BA**; mở vòng 8 phải nới tiếp |
| 6 | `uiAuditDocParity.test.ts:220` đối chiếu dòng «**Tổng: N mục**» | thêm 3 mục mà quên sửa 63 → 66 ⇒ guard đỏ (**đã sửa ở bước BA**) |
| 7 | Sổ AC-UX phải **liên tục từ 001** | cấp số nhảy cóc ⇒ guard đỏ |
| 8 | `useNotify` là façade — view **không** import `useModal` | thêm 1 lối gọi thứ hai = fork SSoT (ADR-UX-16) |
| 9 | `whitespace-pre-line` cho `body` | chuỗi có `\n` (`UomConversionView:56`, `PmTemplateListView:175`) dồn thành một dòng |
| 10 | `notify.confirm` là **async** | quên `await` ⇒ `if (!ok)` nhận Promise (luôn truthy) ⇒ **hành động phá huỷ chạy dù người dùng bấm Huỷ** |

---

## §9. Việc phải làm trên tài liệu & guard (doc-layer)

| Tệp | Delta |
|---|---|
| `docs/ui-ux/00_AUDIT_HIEN_TRANG.md:563` | sửa AC-UX-058: **44/31 → 42/28** + ghi công thức strip-comment |
| `docs/ui-ux/00_AUDIT_HIEN_TRANG.md §6` | **thêm** AC-UX-064/065/066; sửa «Tổng: **63** mục … AC-UX-**063**» → «**66** … AC-UX-**066**» |
| `docs/ui-ux/00_AUDIT_HIEN_TRANG.md §9` | **thêm** ADR-UX-16/17/18 |
| `docs/ui-ux/04_…md:71` (§1.2) | **44/31 → 42/28** + công thức; sửa dòng «hạ tầng chết» (nay `useNotify` đã tiêu thụ) |
| `docs/ui-ux/04_…md:677` (§10.6) | **44 lần / 31 file → 42 / 28**; đích ghi rõ lô 1 = 21; `NotificationModal` chuyển sang **ĐANG LÀM (vòng 7)** |
| `docs/ui-ux/04_…md:935` (§16) | «44 lần `confirm()` trần» → **42**, trỏ sang tài liệu `06` |
| `frontend/src/router/uiAuditDocParity.test.ts:34` | `ROUND_VALUES` thêm `'7'` |
| `frontend/src/components/common/modalOverlayHygiene.test.ts` | allowlist **30 → 29** (xoá đúng dòng `NotificationModal.vue`) + hạ 3 chỗ số ở `:126`/`:127`/`:141` |

---

## §10. DoD — nghiệm thu vòng (đo từ đĩa, không đọc mô tả)

```bash
cd frontend
# 1) SSoT hợp nhất
grep -c 'fixed inset-0'              src/components/common/NotificationModal.vue   # 0
grep -c "addEventListener('keydown'" src/components/common/NotificationModal.vue   # 0
git diff --stat -- src/composables/useModal.ts                                     # rỗng

# 2) Nợ confirm — công thức CÓ strip comment (§1.1)
node -e "…"    # 21 call-site / 21 file
for f in PurchaseDetailView UomConversionView StockMovementDetailView \
         AssetTransferDetailView PmTemplateListView DocumentDetailView; do
  grep -rn "[^.a-zA-Z_]confirm(" src --include="$f.vue"; done          # rỗng
grep -n "[^.a-zA-Z_]confirm(" src/components/asset/AssetDepreciationSchedule.vue  # rỗng

# 3) Test cũ
for f in src/components/asset/AssetDepreciationSchedule.test.ts \
         src/views/asset/assetTransferDetailCtaGate.test.ts \
         src/views/asset/assetTransferDetailEditGate.test.ts \
         src/views/purchase/purchaseCtaGate.test.ts; do
  grep -c "stubGlobal('confirm'" $f; done                              # 0 0 0 0

# 4) Sổ số hiệu
grep -rhoE "AC-UX-[0-9]{3}" ../docs/ src/ | sort -u | tail -1          # AC-UX-066

# 5) Rác
git status --porcelain | grep __qa_scratch                             # rỗng
git status --porcelain -- '*.py'                                       # rỗng
```

| Hạng mục | Đích |
|---|---|
| `npx vitest run` | **0 file đỏ**, đọc số bằng mắt |
| DELTA số file test | ≥ **+2** so với baseline đĩa **340** (`find frontend/src -name '*.test.ts' \| wc -l`) |
| DELTA số TC | ≥ **+25** |
| 4 guard `uiAuditDocParity` · `uiFixPlanParity` · `modalOverlayHygiene` · `uiPrimitiveHygiene` | **XANH** |
| `npm run typecheck` | XANH |
| Bàn giao BE | **không có** — 0 tệp `.py`, không `bench migrate`, không restart worker |

> **Baseline trong prompt luôn có thể stale** ⇒ chấm **DELTA**, đo lại từ đĩa. Không dừng vì lệch số tuyệt đối.

---

## §11. Chấm bù run-6 — ghi sổ, **CẤM re-spec**

Ba đề mục run-6 **đã land**; adoption thực tế **nhỏ hơn** con số trong handoff. Ghi lại để khỏi đếm lại, phần thiếu là **ADOPTION** (đã có số **AC-UX-047/048** + vòng 6), **không cấp số mới**:

| Đề mục | Handoff ghi | Đo từ đĩa 2026-08-04 |
|---|---|---|
| `ListPageShell` | 19 view | **16** view |
| `DetailPageShell` | 22 view | **11** view |
| `ModalInlineError.vue` | — | **tồn tại**, đã nối vào `BaseModal` (`error`/`errorTitle`) + `sanitizeBusinessMessage` (`frontend/src/api/axios.ts:187`); mới **2** view tiêu thụ (`CalibrationScheduleListView` · `ReferenceDataView`) |

---

## §12. Quyết định kiến trúc

### ADR-UX-16: View gọi `useNotify().confirm()`, **không** gọi `useModal()` trực tiếp
- **Status**: Accepted — 2026-08-04
- **Context**: `04 §1.2` mô tả `useModal` là “hạ tầng đã có nhưng **chết** (0 view tiêu thụ)”, và đề mục vòng này gọi `useModal.ts` là SSoT. Đo lại từ đĩa: `useNotify.ts:127-144` **đã** uỷ nhiệm `confirm` cho `modal.confirm`, và **7 call-site** ở 5 view đã dùng `notify.confirm` (có test: `decommissionDetailCtaGate.test.ts:128`). Hạ tầng **không chết** — nó được dùng **qua façade**. Nếu lô 1 gọi thẳng `useModal()`, repo sẽ có **hai** lối mở cùng một hộp thoại.
- **Decision**: **`useNotify()` là API duy nhất của view.** `useModal` là tầng **hàng đợi**, chỉ `useNotify` và `NotificationModal` được nhập. `ConfirmOpts` thêm `tone?` tuỳ chọn để diễn đạt hành động phá huỷ.
- **Consequences**: (+) một lối gọi, một chỗ gắn mã thông điệp `MSG`, test có sẵn khuôn spy; (+) sau này đổi tầng render không đụng view; (−) thêm một tầng gián tiếp khi đọc mã; (−) `useNotify` phình dần ⇒ chốt: chỉ nhận thêm field **chuyển tiếp thẳng**, không thêm logic.
- **Alternatives**: (a) view gọi `useModal()` trực tiếp như đề mục ghi — **loại**: fork lối gọi, mất `MSG`, mâu thuẫn 7 call-site đang chạy; (b) bỏ `useNotify.confirm`, dồn về `useModal` — **loại**: phải sửa 5 view + test đang xanh, đổi hợp đồng đã ổn định để chiều một câu chữ trong đề mục.

### ADR-UX-17: `BaseModal` thêm prop tuỳ chọn `layer` — hộp thoại **hệ thống** nằm trên hộp thoại **nghiệp vụ**
- **Status**: Accepted — 2026-08-04 · mở rộng **ADR-UX-08** (không thay thế)
- **Context**: `NotificationModal` đang ở `z-[10000]`, `BaseModal` ở `z-50`. Hợp nhất mà không xử lý ⇒ thứ tự vẽ chỉ còn phụ thuộc thứ tự `Teleport` chèn `body`. Ca thường gặp (lỗi `critical` bật **sau** khi hộp thoại nghiệp vụ đã mở) tình cờ đúng; ca ngược lại (hộp thoại nghiệp vụ mở **sau** một cảnh báo đang chờ) **che mất** cảnh báo chặn.
- **Decision**: thêm `layer?: 'default' | 'system'`, mặc định `'default'` ⇒ `z-50` **y hệt hôm nay**; `'system'` ⇒ `z-[10000]`, chỉ `NotificationModal` truyền. Hai chuỗi class là **literal** (bẫy JIT).
- **Consequences**: (+) 19 file tiêu thụ **0 dòng đổi**, hành vi bit-đối-bit như cũ; (+) thứ tự xếp chồng thành **hợp đồng khai báo**, không còn là hệ quả tình cờ của thứ tự mount; (−) `BaseModal` có thêm 1 prop — chấp nhận, cùng khuôn `error`/`errorTitle` (AC-UX-062).
- **Alternatives**: (a) dựa vào thứ tự `Teleport` — **loại**: đúng do may, hỏng câm, không test được bằng mắt; (b) `NotificationModal` bọc thêm một lớp `div` z-index — **loại**: `Teleport` nằm **bên trong** `BaseModal`, lớp bọc không bao được overlay; (c) nâng `BaseModal` lên `z-[10000]` cho tất cả — **loại**: đổi hành vi của cả 19 file tiêu thụ để phục vụ 1 ca.

### ADR-UX-18: Ngân sách nợ đo theo **cặp (file, số lần)** và **CHỈ-GIẢM hai chiều**
- **Status**: Accepted — 2026-08-04 · mở rộng khuôn allowlist của **AC-UX-055**
- **Context**: allowlist theo tên file chặn được *file mới*, nhưng mù với hồi quy **bên trong** file đã có tên. Với 42 call-site rải 28 file và kế hoạch di trú nhiều lô, cái mù đó chính là đường nợ quay lại. Thêm nữa, run-5/run-6 cho thấy trần treo lơ lửng thì **doc trôi khỏi đĩa** (44/31 sống sót qua 2 vòng dù đĩa đã khác).
- **Decision**: guard giữ **bản đồ số** per-file; ĐỎ khi tổng tăng · file lạ xuất hiện · một file vượt hạn mức; **và** ĐỎ khi một file đo được **thấp hơn** hạn mức (buộc hạ sổ). Số đo luôn tính **sau khi strip comment**, dùng lại đúng hàm `stripComments` đang có.
- **Consequences**: (+) tiến độ di trú luôn khớp đĩa, không cần đo lại từ đầu mỗi lô; (+) người sửa được nhắc ngay phải cập nhật sổ; (−) mỗi lô phải chạm tệp guard — chấp nhận, đó chính là điểm ghi nhận tiến độ.
- **Alternatives**: (a) chỉ chốt **tổng** — **loại**: cho phép xê dịch giữa các file, che hồi quy; (b) chỉ chốt danh sách tên file — **loại**: đúng cái mù đang cần chữa; (c) không guard, tin vào review — **loại**: đã thất bại 2 vòng liền (44/31).

---

## §13. Nợ để lại (KHÔNG thuộc vòng này)

- **AC-UX-058 lô 2+** — 21 call-site còn lại / 21 file (bản đồ §6.3). Chia lô theo module, mỗi lô hạ bản đồ ngân sách.
- **AC-UX-055/056** — gỡ overlay tự vẽ của 5 file lô 1 (allowlist 29 → 24) + 4 file lai.
- `views/pm/PMWorkOrderDetailView.vue:186` — `confirm()` trần được dùng để **điều hướng** (mở phiếu sửa chữa vừa tạo), không phải xác nhận hành động ⇒ cần mẫu «hộp thoại có lối đi tiếp», không dùng khuôn §5.1. Xử lý ở lô riêng.
- Mở rộng `bareConfirmBudget` sang `alert(` / `prompt(` trần — `[ROADMAP]`.
