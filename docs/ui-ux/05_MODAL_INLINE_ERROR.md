# 05 — Lỗi CHẶN hành động hiện INLINE trong hộp thoại + làm sạch câu lỗi tại `axios`

| Mục | Giá trị |
|---|---|
| Module | **IMM-00** (nền FE dùng chung) — hưởng lợi: IMM-01/03/05/07/10/11/12/16 |
| Sổ backlog | **AC-UX-062** (lỗi inline, P0) · **AC-UX-063** (làm sạch câu lỗi, P1) |
| SSoT chạm | `frontend/src/components/common/BaseModal.vue` · `frontend/src/api/axios.ts` |
| Trạng thái | **Spec ĐÃ CHỐT — sẵn sàng cho [FE]** (BA đóng Bước 2, vòng 3 / run-6) |
| Cập nhật | 2026-08-03 |

## Tài liệu liên quan
- [`00_AUDIT_HIEN_TRANG.md §6`](./00_AUDIT_HIEN_TRANG.md) — sổ backlog AC-UX (nay 63 mục)
- [`04_PHUONG_AN_SUA_TOAN_BO.md §3`](./04_PHUONG_AN_SUA_TOAN_BO.md) — hợp đồng `BaseModal` vòng 5 (a11y dialog + bẫy focus). Tài liệu **05** kế thừa nguyên **§3.1 bất biến 0-churn** và chỉ THÊM.
- [`04 §5.2/§5.3`](./04_PHUONG_AN_SUA_TOAN_BO.md) — allowlist overlay tự vẽ (**30**) và file lai (**4**). Hai file trong lô 1 dưới đây thuộc nhóm **lai** ⇒ đọc §5 trước khi code.
- Core Doc module: [`docs/imm-00/06_Frontend_Design.md §II.6`](../imm-00/06_Frontend_Design.md)

---

## §0. Phạm vi & Boundaries

**Always (luôn áp dụng):**
- Lỗi **CHẶN hành động** (thao tác bị máy chủ từ chối) phải hiện **trong chính hộp thoại** đang mở, `role="alert"`, **không tự tắt**, và hộp thoại **KHÔNG đóng**.
- Toast chỉ dành cho thông báo **không chặn** (thành công, cảnh báo nền, thông tin).
- Hợp đồng cài ở **SSoT** (`BaseModal.vue`), không rải theo màn.
- Mọi chuỗi lỗi tới từ máy chủ đi qua **một cửa** làm sạch trước khi tới `ApiError.message`.

**Ask first (hỏi BA trước khi làm):**
- Thay đổi bất kỳ prop/emit/testid/class **đã có** của `BaseModal` (vi phạm §2.2).
- Di trú overlay tự vẽ sang `BaseModal` (đó là **AC-UX-055/056**, không phải vòng này).
- Mở rộng bộ dấu hiệu kỹ thuật của sanitizer ngoài §7.3.

**Never (tuyệt đối không):**
- Không đặt `setTimeout`/`duration`/tự-ẩn cho vùng lỗi inline (kể cả “để đỡ rối”).
- Không đóng hộp thoại ở nhánh lỗi (`show*Modal = false` trong `catch` = **cấm**).
- Không để lỗi chặn đi ra bằng toast **song song** với vùng inline (2 kênh = người dùng đọc 1, bỏ 1).
- Không để hộp thoại thứ hai (`useModal.alert`) bật chồng lên hộp thoại đang mở.
- Không echo traceback/SQL/tên file `.py` ra giao diện — kể cả “chỉ khi 417”.

---

## §1. Hiện trạng đo từ đĩa (2026-08-03 — mẫu số chấm DELTA)

Lệnh tái lập (chạy trong `frontend/src`):

```bash
grep -rl "BaseModal" --include=*.vue .            # 19 file tiêu thụ
grep -c 'role="alert"'            <file>          # theo từng file
grep -c 'data-testid="modal-error"' <file>
grep -c setTimeout ../components/common/BaseModal.vue   # 0
find src -name "*.test.ts" | wc -l                # 335
```

| Số đo | Giá trị 2026-08-03 |
|---|---|
| File `.vue` tiêu thụ `BaseModal` | **19** |
| Trong đó có **0** vùng lỗi inline (0 `role="alert"` **và** 0 `data-testid="modal-error"`) | **15** (danh sách §6.2) |
| File có `role="alert"` (đều là vùng **ngoài** hộp thoại) | 4 — `AssetDetailView` (3) · `AssetLabelPrintView` (2) · `CAPADetailView` (1) · `RCADetailView` (8) |
| File có `data-testid="modal-error"` | **0 / 19** |
| `BaseModal.vue` có `setTimeout` | **0** (phải giữ **0**) |
| File test FE | **335** |
| Toast tự tắt | `composables/useToast.ts:33` (`duration = 4000`) → `:45` `setTimeout(...)` xoá toast |

**Hệ quả đo được:** với 15/19 file, lý do một thao tác bị từ chối **chỉ đến bằng toast biến mất sau 4 giây**, trong khi hộp thoại vẫn mở — người dùng nhìn lại hộp thoại thì không còn dấu vết vì sao hỏng.

### 1.1 Bốn kiểu đường-lỗi sai đang tồn tại (bằng chứng `file:line`)

| Kiểu | Bằng chứng | Vì sao hỏng |
|---|---|---|
| **K1 — toast tự tắt là kênh DUY NHẤT** | `views/inventory/CycleCountDetailView.vue:99` (`doPost`), `:121` (`doRecount`) — `api.run(...)` không `silentError` ⇒ `useApi.ts:70 notify.fromError` | Hộp thoại còn mở, lỗi bay mất sau 4s |
| **K2 — lỗi ghi vào biến hiển thị NGOÀI hộp thoại** | `views/auth/UserProfileFormView.vue:231` (`confirmReject`) ghi `error.value` — banner của **trang**, trong khi `BaseModal` (`:632`) đang phủ lên trên | Người dùng trong hộp thoại **không bao giờ thấy** lý do |
| **K3 — có chữ lỗi trong overlay nhưng KHÔNG có ngữ nghĩa alert + BỊ nhân đôi ra toast** | `views/calibration/CalibrationScheduleListView.vue:444` (`<div v-if="err" class="alert-error">`) + `:196/:201 toast.error` + `:216 notify.fromError` | Trình đọc màn hình không được báo; cùng 1 lỗi ra 2 kênh |
| **K4 — chữ lỗi là `e.message` THÔ của máy chủ** | `views/master-data/ReferenceDataView.vue:175` (`err.value = e instanceof Error ? e.message : 'Lỗi lưu'`) render ở `:503` | 417/422 không có `message_code` ⇒ đổ nguyên văn chuỗi kỹ thuật ra giao diện |

### 1.2 Hai cửa đang trả chữ THÔ của máy chủ cho giao diện

| Cửa | Vị trí | Ghi chú |
|---|---|---|
| **Cửa A** — 417/422 fallback | `api/axios.ts:277` (`makeBusinessRuleError` nhánh không có `message_code`) → ném ở `:310` | Nhánh **có** `message_code` (`:262-276`) đã render từ registry VI ⇒ **KHÔNG đụng** |
| **Cửa B** — 400 | `api/axios.ts:181-184` (`handle400`) | Gọi cùng một hàm `parseServerMessages` |

**Cả hai cửa đều đi qua `parseServerMessages` (`axios.ts:136-146`)** ⇒ đó là **một cửa duy nhất** để cài sanitizer (A7).

**Đã sạch từ trước, không đụng:** `handle500` (`:228-236`, đã chặn echo `exc` từ Finding C 2026-07-09) · `handle429` (`:244-247`) · `handle403` (`:204-226`) · nhánh `message_code` (`:262-276`).

---

## §2. Hợp đồng SSoT — `BaseModal.vue` + `ModalInlineError.vue`

### 2.1 `frontend/src/components/common/ModalInlineError.vue` (MỚI — tier-1, thuần trình bày)

Lý do tồn tại: **markup vùng lỗi phải có đúng 1 nguồn**. `BaseModal` dùng nó; hai overlay **lai** của lô 1 (§5) cũng dùng **chính nó** — nếu copy markup sang overlay thì lần sửa sau phải sửa 3 nơi (đúng lỗi `CommandPalette` fork focus-trap đã trả giá ở vòng 5).

- **Vị trí:** `components/common/` (tier-1). **KHÔNG** phải primitive `components/ui/` thứ 9 — nó phụ thuộc ngữ cảnh hộp thoại, không phải khối dựng hình chung (cùng lý lẽ ADR-UX-06 với `DetailPageShell`).
- **Props:** `message: string` · `title?: string` (mặc định `'Không thực hiện được thao tác'`).
- **Render (bắt buộc, y nguyên các thuộc tính):**

```html
<div
  data-testid="modal-error"
  role="alert"
  aria-live="assertive"
  class="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2"
>
  <p class="text-sm font-semibold text-red-800">{{ title }}</p>
  <p data-testid="modal-error-message" class="text-sm text-red-700 whitespace-pre-line">{{ message }}</p>
</div>
```

- **Cấm:** `setTimeout` · `v-show` theo thời gian · nút “×” tự đóng vùng lỗi (vùng lỗi biến mất **chỉ khi** người dùng thử lại hoặc đóng hộp thoại).

### 2.2 Delta chính xác trên `BaseModal.vue` (hiện 118 dòng)

| # | Vị trí | Delta |
|---|---|---|
| E1 | `<script setup>` `defineProps` (`:9-13`) | **THÊM** `error?: string \| null` và `errorTitle?: string`. Ba prop cũ (`title`/`size`/`danger`) **giữ nguyên chữ ký** |
| E2 | `<script setup>` | `import ModalInlineError from './ModalInlineError.vue'` |
| E3 | thân bài (`:102`) | Ngay **ĐẦU** `data-testid="modal-body"`, TRƯỚC `<slot />`: `<ModalInlineError v-if="error" :message="error" :title="errorTitle" />` |
| E4 | — | **KHÔNG** đổi `:class`, không đổi thứ tự header/body/footer, không thêm emit, không thêm `setTimeout` |

Ràng buộc đo được: `grep -c setTimeout frontend/src/components/common/BaseModal.vue` **== 0** sau khi sửa.

Quy ước “rỗng”: `v-if="error"` xử lý cả `null`, `undefined` và `''` ⇒ chuỗi rỗng **không** render khung đỏ trống.

### 2.3 Bất biến 0-churn (kế thừa `04 §3.1` — điều kiện tồn tại của vòng)

Thay đổi **CHỈ THÊM**. Giữ tuyệt đối: prop `title`/`size`/`danger` · emit `close` · testid `modal-card`/`modal-close`/`modal-body`/`modal-footer` · **toàn bộ chuỗi class**.

**Đo:** bốn tệp test đã có phải **XANH với 0 dòng sửa** —
`BaseModal.dialog.test.ts` (16 TC) · `BaseModal.a11y.test.ts` (9 TC) · `BaseModal.responsive.test.ts` · `modalOverlayHygiene.guard.test.ts` (10 TC).

> ⚠️ **KHÔNG đo bằng `git diff --stat`** — 3/4 tệp này **chưa được theo dõi bởi git** (untracked từ run-5: chỉ `BaseModal.responsive.test.ts` nằm trong `git ls-files`) ⇒ `git diff --stat` **luôn rỗng** dù có sửa hay không: đó là **xanh giả**. Đo bằng **md5 chốt trước khi code** (đo 2026-08-03):
>
> ```
> 0d6b524feec436918f0f1c5cb81de94c  BaseModal.a11y.test.ts
> 8b6df68666ab43963364738fa0a4939c  BaseModal.dialog.test.ts
> 2a13a65b72d49daf73d511cc922bbe16  BaseModal.responsive.test.ts
> 27e6f21226af2ccdf9090edd6f9564d3  modalOverlayHygiene.guard.test.ts
> ```
>
> Lệnh chấm: `md5sum frontend/src/components/common/BaseModal*.test.ts frontend/src/guards/modalOverlayHygiene.guard.test.ts` — **4/4 khớp**.

Nếu buộc phải sửa 1 trong 4 ⇒ **thiết kế sai, quay lại SSoT** (không sửa test cho vừa mã).

---

## §3. Không xếp chồng hộp thoại (A3)

Bối cảnh: `useApi.run` khi lỗi và **không** `silentError` sẽ gọi `notify.fromError` (`useApi.ts:58-71`); `fromError` với severity `critical` mở **hộp thoại thứ hai** qua `useModal.alert` (`useNotify.ts:65-73` và `:93-101`), do `NotificationModal.vue` render.

**Luật:** ở mọi thao tác trong hộp thoại,
1. gọi `api.run(..., { silentError: true })` — chặn cả toast lẫn `modal.alert`;
2. **hoặc** (nhánh không dùng `useApi`, xem §5) tự `catch` và **gỡ** mọi `toast.*` / `notify.fromError` trên đường lỗi đó;
3. gán chuỗi lỗi vào biến `error` bind vào hộp thoại đang mở.

**Đo (test render):** sau khi thao tác thất bại, `wrapper.findAll('[data-testid="modal-card"]').length === 1` **và** `wrapper.find('[data-testid="modal-error"]').exists() === true`.

Lưu ý: `silentError: true` vẫn ghi `lastError` (`useApi.ts:52`) và vẫn gọi `onFieldError` (`:54-56`) ⇒ lỗi field-level giữ nguyên hành vi cũ.

---

## §4. Xoá lỗi cũ (bắt buộc — chống “lỗi ma”)

Vùng lỗi **không tự tắt** ⇒ phải xoá tường minh, nếu không lần mở sau sẽ thấy lỗi của lần trước:

| Thời điểm | Hành động |
|---|---|
| Mở hộp thoại (`show*Modal = true`) | `error = ''` |
| Ngay đầu mỗi lần thử lại (dòng đầu của handler) | `error = ''` |
| Đóng hộp thoại (`@close`) | `error = ''` |
| **Thất bại** | `error = <câu lỗi>` — **và KHÔNG** set `show*Modal = false` |
| Thành công | đóng hộp thoại như cũ |

---

## §5. Adoption lô 1 — 5 file / **8** hộp thoại hành động (danh sách ĐÓNG BĂNG)

Hai đường cài đặt, chọn theo **khuôn hộp thoại thật của từng chỗ** (đo từ đĩa, không suy đoán):

- **Đường A — hộp thoại là `BaseModal`:** bind `:error="…"` (dùng hợp đồng §2.2).
- **Đường B — overlay tự vẽ (file *lai*, xem `04 §5.3`):** render `<ModalInlineError :message="err" />` ngay đầu thân overlay, thay cho `<div v-if="err">` hiện tại. **KHÔNG** di trú overlay sang `BaseModal` trong vòng này (đó là AC-UX-056).

| # | File · hộp thoại | Handler | Khuôn | Delta bắt buộc |
|---|---|---|---|---|
| L1 | `views/inventory/CycleCountDetailView.vue` — “Ghi nhận điều chỉnh tồn” (`:316`, `showPostModal`) | `doPost` `:97` (`api.run` `:99`) | A | `silentError: true` + `:error="postError"` + xoá lỗi ở `:221` (nút mở) và đầu handler |
| L2 | `views/inventory/CycleCountDetailView.vue` — “Sửa đếm lại” (`:336`, `showRecountModal`) | `doRecount` `:117` (`api.run` `:121`) | A | như L1 với `recountError` |
| L3 | `views/needs/NeedsRequestDetailView.vue` — “Phê duyệt đề xuất nhu cầu” (`:768`, `showApproveModal`) | `doApprove` `:222` (`api.run` `:224`) | A | `silentError: true` + `:error="approveError"` |
| L4 | `views/needs/NeedsRequestDetailView.vue` — “Bác đề xuất” (`:793`, `showRejectModal`) | `doReject` `:237` (`api.run` `:239`) | A | `silentError: true` + `:error="rejectError"` |
| L5 | `views/needs/NeedsRequestDetailView.vue` — “Đưa vào kế hoạch mua sắm” (`:818`, `showRollModal`) | `doRollIntoPlan` `:279` (`api.run` `:283`) | A | `silentError: true` + `:error="rollError"` |
| L6 | `views/calibration/CalibrationScheduleListView.vue` — form tạo/sửa lịch (overlay `:441`, `showForm`) | `save` `:192` | **B** | Thay `:444` bằng `<ModalInlineError :message="err" />`; **gỡ** `toast.error` `:196`, `:201` và `notify.fromError` `:216` (giữ `store._captureError` + `err.value = store.error`) |
| L7 | `views/master-data/ReferenceDataView.vue` — form tạo/sửa dữ liệu nền (overlay `:500`, `showForm`) | `save` `:160` | **B** | Thay `:503` bằng `<ModalInlineError :message="err" />`; `catch` `:175` dùng `toApiError(e).message` thay `e.message` (chuỗi đã qua sanitizer §7) |
| L8 | `views/auth/UserProfileFormView.vue` — “Từ chối tài khoản” (`BaseModal` `:632`, `showRejectModal`) | `confirmReject` `:217` | A | Thêm `rejectModalError`; `catch` `:230-232` ghi vào **biến mới** (KHÔNG vào `error.value` của trang) + `:error="rejectModalError"`; xoá ở `openRejectModal` `:207-211` |

**Ràng buộc chung cho cả 8:** nhánh lỗi **tuyệt đối không** set `show*Modal = false` / `showForm = false`.

> ⚠️ Ba đính chính so với bản đề mục đóng băng — xem §9 (BA Self-Correction). Tóm tắt: (a) `CalibrationScheduleListView` và `ReferenceDataView` **không** dùng `BaseModal` cho form tạo/sửa (overlay tự vẽ) ⇒ đường B; (b) `UserProfileFormView` **không** có hộp thoại “lưu” — hộp thoại chặn thật là “Từ chối tài khoản”; (c) hai file đường B không dùng `useApi` ⇒ điều kiện `silentError: true` được thay bằng “gỡ kênh toast trên đường lỗi đó”.

---

## §6. Guard CHỈ-GIẢM — `frontend/src/guards/modalInlineErrorAdoption.guard.test.ts` (MỚI)

Cùng khuôn CHỈ-GIẢM với `modalOverlayHygiene.guard.test.ts` — **KHÔNG viết bộ đếm thứ hai**, tái dùng cách quét file của guard đó.

### 6.1 Vị ngữ “file này ĐÃ có vùng lỗi chặn inline”

`HAS_INLINE_ERROR(file)` = đúng **ít nhất một** điều:
1. chứa literal `data-testid="modal-error"`; **hoặc**
2. chứa `<ModalInlineError` (đường B, và cả `BaseModal.vue` nếu quét tới); **hoặc**
3. có **ít nhất một** thẻ mở `<BaseModal …>` (regex `/<BaseModal\b[\s\S]*?>/g`) chứa `:error=` hoặc `v-bind:error=`.

Điều 3 phải soi **trong thẻ mở**, không grep cả file — `:error=` của một component khác không được tính là đã đạt.

### 6.2 Allowlist ĐÓNG BĂNG (15 — đo 2026-08-03)

```
views/asset/DepreciationView.vue
views/auth/UserProfileFormView.vue                  ← lô 1 (L8)
views/calibration/CalibrationScheduleListView.vue   ← lô 1 (L6)
views/compliance/ComplianceRuleDetailView.vue
views/compliance/ComplianceRuleListView.vue
views/compliance/FindingDetailView.vue
views/compliance/InternalAuditDetailView.vue
views/compliance/InternalAuditListView.vue
views/compliance/ManagementReviewDetailView.vue
views/compliance/ManagementReviewListView.vue
views/document/FirmwareCrDetailView.vue
views/inventory/CycleCountDetailView.vue            ← lô 1 (L1,L2)
views/master-data/ReferenceDataView.vue             ← lô 1 (L7)
views/needs/NeedsRequestDetailView.vue              ← lô 1 (L3,L4,L5)
views/procurement/AvlListView.vue
```

### 6.3 Bất biến (INV-UXMODERR-*)

| Mã | Bất biến |
|---|---|
| INV-UXMODERR-1 | Tập «file tiêu thụ `BaseModal` mà `HAS_INLINE_ERROR` sai» là **tập con** của allowlist ⇒ file mới không được sinh nợ mới |
| INV-UXMODERR-2 | Kích thước tập đó **== 10** sau lô 1 (từ **15**). Guard ĐỎ nếu > 10 (tăng nợ) **và** ĐỎ nếu < 10 mà allowlist chưa cập nhật (số ĐÓNG BĂNG phải đi cùng doc) |
| INV-UXMODERR-3 | Mọi mục trong allowlist phải **tồn tại trên đĩa** và **thật sự** tiêu thụ `BaseModal` (chống allowlist mục ma) |
| INV-UXMODERR-4 | `grep -c setTimeout` trên `BaseModal.vue` **== 0** và trên `ModalInlineError.vue` **== 0** |
| INV-UXMODERR-5 | 8 hộp thoại lô 1: **0** lần `show*Modal = false` / `showForm = false` xuất hiện trong khối `catch` của handler tương ứng |

Sau lô 1, 10 file còn nợ: `DepreciationView` · `ComplianceRuleDetailView` · `ComplianceRuleListView` · `FindingDetailView` · `InternalAuditDetailView` · `InternalAuditListView` · `ManagementReviewDetailView` · `ManagementReviewListView` · `FirmwareCrDetailView` · `AvlListView` (⇒ lô 2, chưa cấp số vòng này).

---

## §7. Hợp đồng làm sạch câu lỗi — `frontend/src/api/axios.ts`

### 7.1 Chữ ký & vị trí

```ts
/** Làm sạch chuỗi lỗi máy chủ trước khi tới giao diện. Export để test khoá trực tiếp. */
export function sanitizeBusinessMessage(raw: string): string
```

Đặt **trên** `parseServerMessages`. `parseServerMessages` (`:136-146`) giữ nguyên logic bóc `_server_messages`, chỉ **bọc kết quả**:

```ts
function parseServerMessages(data: FrappeErrorData): string {
  return sanitizeBusinessMessage(rawServerMessage(data))   // rawServerMessage = thân hàm cũ, không đổi
}
```

⇒ **một cửa** phủ CẢ HAI: `handle400` (`:182`) và `makeBusinessRuleError` nhánh fallback (`:277`, ném ở `:310`).
Nhánh có `message_code` (`:262-276`) **không đi qua** hàm này ⇒ bản render từ registry VI giữ **nguyên văn** (khoá bằng TC-SAN-10).

### 7.2 Thuật toán 3 bước

1. **Chuẩn hoá:** `raw` rỗng/chỉ khoảng trắng → trả câu VI trung tính.
2. **Gỡ thẻ trình bày lành tính:** xoá cặp thẻ `br|b|strong|i|em|u|p|span|div|ul|ol|li|small` (mở/đóng, `<br>`/`<br />` → một khoảng trắng), rồi `trim`. *Chỉ gỡ thẻ, KHÔNG đổi chữ.*
3. **Dò dấu hiệu kỹ thuật** trên chuỗi sau bước 2: khớp **bất kỳ** dấu hiệu nào → trả **đúng một** câu VI trung tính; sau bước 2 mà chuỗi rỗng → cũng trả câu đó. Ngược lại → trả chuỗi bước 2 **nguyên văn**.

**Câu VI trung tính (hằng số duy nhất, copy đúng từng ký tự):**

> `Không thực hiện được thao tác do quy tắc nghiệp vụ. Vui lòng kiểm tra lại dữ liệu hoặc liên hệ quản trị hệ thống.`

### 7.3 Bộ dấu hiệu kỹ thuật (tối thiểu — đúng bộ này, không thêm bớt khi chưa hỏi BA)

| Nhóm | Mẫu |
|---|---|
| Traceback Python | `Traceback` · `File "` · `line <số>, in ` |
| Kiểu/đối tượng Python | `<class '` · `<module` · `<function` · `<built-in` |
| Import | `cannot import name` |
| SQL | `SELECT … FROM` · `INSERT INTO` · `UPDATE … SET` · `DELETE FROM` · tên bảng Frappe `tab<ChữHoa>` |
| Driver / lỗi DB | `pymysql` · `OperationalError` · `ProgrammingError` · `IntegrityError` |
| Ngoại lệ Frappe | `frappe.exceptions` |
| Tệp nguồn | đuôi `.py` |
| Thẻ còn sót | bất kỳ `<…>` **còn lại sau bước 2** (vd `<a href='/app/...'>` của Frappe) |

SQL dò theo **cặp từ khoá** (`SELECT`…`FROM`, `UPDATE`…`SET`, `INSERT INTO`, `DELETE FROM`), không dò một từ đơn — tránh nuốt oan câu VI có chữ “update”. Xem bẫy §8-B3.

### 7.4 Chỉ log khi DEV (A8)

```ts
if (import.meta.env.DEV) {
  console.debug('[axios] sanitizeBusinessMessage: chuỗi thô bị thay', raw)
}
```

- Chỉ log **khi có thay thế** (không log câu VI sạch đi qua).
- DEV = false ⇒ logger **không được gọi** và chuỗi thô **không xuất hiện** trong `ApiError.message`.
- DEV = true ⇒ logger được gọi **đúng 1 lần** cho mỗi lần thay.

### 7.5 Bảng ca kiểm thử bắt buộc (`api/sanitizeBusinessMessage.test.ts` — MỚI)

| TC | Đầu vào | Kỳ vọng |
|---|---|---|
| TC-SAN-01 | `Traceback (most recent call last): File "/home/.../imm12.py", line 88, in advance` | câu VI trung tính |
| TC-SAN-02 | `pymysql.err.OperationalError: (1054, "Unknown column 'x'")` | câu VI trung tính |
| TC-SAN-03 | `SELECT name FROM \`tabAC Asset\` WHERE ...` | câu VI trung tính |
| TC-SAN-04 | `cannot import name 'foo' from 'assetcore.services.imm11'` | câu VI trung tính |
| TC-SAN-05 | `<class 'frappe.exceptions.ValidationError'>` | câu VI trung tính |
| TC-SAN-06 | `Cannot delete because linked with <a href='/app/imm-capa/CAPA-1'>CAPA-1</a>` | câu VI trung tính (thẻ `<a …>` còn sót) |
| TC-SAN-07 | `Không thể xoá vì còn phiếu bảo trì đang mở.` | **nguyên văn** |
| TC-SAN-08 | `Không thể xoá vì còn <b>2</b> phiếu bảo trì đang mở.` | `Không thể xoá vì còn 2 phiếu bảo trì đang mở.` (chỉ gỡ thẻ) |
| TC-SAN-09 | `''` / `'   '` | câu VI trung tính |
| TC-SAN-10 | 417 kèm `message_code` hợp lệ | message **giữ nguyên bản render** từ registry (không đi qua sanitizer) |
| TC-SAN-11 | 400 với `_server_messages` chứa traceback | `ApiError.message` == câu VI trung tính, `code` vẫn `VALIDATION_ERROR`, `httpStatus` 400 |
| TC-SAN-12 | DEV=false, đầu vào TC-SAN-01 | `console.debug` **0 lần**; chuỗi thô không nằm trong `ApiError.message` |
| TC-SAN-13 | DEV=true, đầu vào TC-SAN-01 | `console.debug` **đúng 1 lần** |
| TC-SAN-14 | Câu VI sạch (TC-SAN-07), DEV=true | `console.debug` **0 lần** |

---

## §8. Bẫy đã biết — ĐỌC TRƯỚC KHI CODE

- **B1 — hai kênh cùng lúc.** Bind `:error` mà quên `silentError: true` ⇒ vừa có vùng inline vừa có toast (và có thể thêm `modal.alert` khi severity `critical`) ⇒ vi phạm §3. Kiểm bằng `findAll('[data-testid="modal-card"]').length === 1`.
- **B2 — “lỗi ma” ở lần mở sau.** Không xoá `error` khi mở lại ⇒ hộp thoại vừa mở đã đỏ. Xem §4.
- **B3 — sanitizer nuốt oan.** Dò một từ SQL đơn lẻ (`UPDATE`) sẽ giết câu VI hợp lệ. Dò theo cặp từ khoá (§7.3).
- **B4 — gỡ thẻ quá tay.** Nếu thay cả nội dung khi gặp `<b>` thì message VI có in đậm (BE có dùng `<b>`/`<br>` ở một số chỗ) bị nuốt sạch ⇒ bước 2 **chỉ gỡ thẻ**, giữ chữ.
- **B5 — đụng nhánh `message_code`.** Nhánh này đã là VI đã render; đưa nó qua sanitizer là rủi ro thuần tuý, không lợi ích.
- **B6 — sửa test cho vừa mã.** 4 tệp test ở §2.3 phải xanh **không sửa dòng nào**; sửa chúng = tự phá bất biến 0-churn.
- **B7 — overlay lai.** `CalibrationScheduleListView` và `ReferenceDataView` nằm trong `ALLOWLIST_HYBRID` của `modalOverlayHygiene.guard.test.ts` (`04 §5.3`, đóng băng ở **4**). Thêm `<ModalInlineError>` **không** làm chúng rời allowlist đó (vẫn còn overlay tự vẽ) ⇒ guard cũ vẫn xanh; đừng “tiện tay” di trú.
- **B8 — `import.meta.env.DEV` trong vitest.** Mặc định `DEV === true` khi chạy vitest ⇒ TC-SAN-12 phải `vi.stubEnv('DEV', false)` (hoặc tương đương) rồi `vi.unstubAllEnvs()` ở `afterEach`, nếu không sẽ xanh giả.

---

## §9. BA Self-Correction — 5 đính chính so với đề mục đóng băng vòng 3

Ghi lại để [QA] chấm theo bản **này**, không chấm theo câu chữ cũ (Core Doc là quyết định cuối).

| # | Đề mục nói | Đĩa nói (bằng chứng) | Quyết định BA |
|---|---|---|---|
| SC-1 | Lô 1 gồm `CalibrationScheduleListView` (tạo/sửa lịch) và `ReferenceDataView` (lưu), mỗi cái `api.run(..., {silentError:true})` + bind `:error` | Cả hai hộp thoại đó là **overlay tự vẽ** (`CalibrationScheduleListView.vue:441` · `ReferenceDataView.vue:500`), không phải `BaseModal`; `save()` **không dùng `useApi`** (`:192` và `:160`) | Giữ nguyên 2 file trong lô 1 nhưng đi **đường B** (§5): dùng `ModalInlineError` + gỡ kênh toast. **Không** di trú overlay (thuộc AC-UX-056) |
| SC-2 | `UserProfileFormView.vue` (lưu) | `saveEdit` `:236` / `saveNew` `:257` là **biểu mẫu của trang**, không có hộp thoại. Hộp thoại `BaseModal` duy nhất là “Từ chối tài khoản” `:632`, lỗi của nó ghi vào banner **trang** (`:231`) nằm dưới lớp phủ | Đổi mục tiêu sang `confirmReject` `:217` (L8). Giữ nguyên số file lô 1 = **5**, số hộp thoại = **8** (≥7 như yêu cầu) |
| SC-3 | Đo adoption bằng `grep -c 'modal-error' ≥ 1` trên 5 file | Thiết kế SSoT (A1) cố ý **không** rải markup: file đường A chỉ có `:error="…"`, literal `modal-error` nằm ở `ModalInlineError.vue` ⇒ phép đo cũ **luôn = 0**, mâu thuẫn chính A1 | Phép đo chuẩn là **vị ngữ §6.1** (3 dạng) do guard `modalInlineErrorAdoption.guard.test.ts` thực thi + test render mỗi hộp thoại. Grep literal bị **thay thế**, không phải bị bỏ |
| SC-4 | Dấu hiệu kỹ thuật: `SELECT `/`INSERT `/`UPDATE `/`DELETE FROM` và thẻ HTML `<…>` (khớp là thay cả câu) | Câu VI hợp lệ có thể chứa chữ “update” và BE có dùng `<b>`/`<br>` khi định dạng | Dò SQL theo **cặp** từ khoá; thẻ trình bày lành tính bị **gỡ** (giữ chữ), chỉ thẻ **còn sót** mới là dấu hiệu (§7.2–7.3). Tinh chỉnh độ chính xác, giữ nguyên ý định |
| SC-5 | Bất biến 0-churn đo bằng `git diff --stat` trên 4 tệp test **== rỗng** | 3/4 tệp đó **untracked** (`git ls-files` chỉ trả `BaseModal.responsive.test.ts`) ⇒ phép đo **luôn rỗng**, kể cả khi tệp bị sửa nát — **xanh giả** | Đo bằng **md5 chốt** (§2.3). Ý định (cấm sửa test cho vừa mã) giữ nguyên, chỉ đổi dụng cụ đo |

---

## §10. Quyết định kiến trúc

### ADR-UX-13: Lỗi CHẶN đi kênh **inline trong hộp thoại**, toast chỉ cho lỗi KHÔNG chặn
- **Status**: Accepted — 2026-08-03
- **Context**: `useToast.ts:33/:45` tự xoá thông báo sau 4000ms. Với 15/19 file tiêu thụ `BaseModal`, đó là kênh **duy nhất** báo vì sao thao tác bị từ chối, trong khi hộp thoại vẫn mở ⇒ người dùng quay lại hộp thoại và không còn thông tin nào.
- **Decision**: Lỗi làm **thất bại thao tác đang thực hiện** phải hiện trong chính hộp thoại (`role="alert"`, `aria-live="assertive"`, không hẹn giờ), hộp thoại **không đóng**. Toast giữ vai trò thông báo không chặn.
- **Alternatives**: (a) tăng `duration` cho toast lỗi — vẫn biến mất, vẫn nằm ngoài ngữ cảnh, và tạo tham số phải chỉnh mãi; (b) `useModal.alert` chồng lên — hai lớp hộp thoại, người dùng mất ngữ cảnh biểu mẫu vừa nhập (và va §3).
- **Consequences**: Mỗi hộp thoại hành động phải có một biến `error` + kỷ luật xoá (§4). Đổi lại, sửa 1 nơi (`BaseModal`) là 19 màn thừa hưởng.

### ADR-UX-14: Markup vùng lỗi tách thành `ModalInlineError.vue` (tier-1), KHÔNG nhúng thẳng vào `BaseModal`
- **Status**: Accepted — 2026-08-03
- **Context**: Hai hộp thoại của lô 1 là overlay **tự vẽ** (`04 §5.3`, allowlist lai = 4) và chưa được phép di trú. Nếu markup chỉ nằm trong `BaseModal`, hai chỗ đó buộc phải **copy** — đúng vết xe `CommandPalette` fork focus-trap (AC-UX-057).
- **Decision**: Một component trình bày dùng chung; `BaseModal` tiêu thụ nó qua prop `error`, overlay lai tiêu thụ trực tiếp.
- **Alternatives**: (a) nhúng markup trong `BaseModal` + copy sang overlay — 3 bản markup; (b) ép di trú overlay ngay vòng này — phình phạm vi, đụng allowlist `modalOverlayHygiene`, rủi ro hồi quy cao.
- **Consequences**: Thêm 1 file tier-1. Guard §6.1 phải chấp nhận **cả hai** cách tiêu thụ (đó là lý do vị ngữ có 3 dạng).

### ADR-UX-15: Làm sạch câu lỗi tại **một cửa** `parseServerMessages`, không tại nơi hiển thị
- **Status**: Accepted — 2026-08-03
- **Context**: Chuỗi thô của máy chủ đi ra giao diện qua 2 cửa (`handle400` `:182`, `makeBusinessRuleError` fallback `:277`); nếu lọc ở từng view thì mỗi view sót một kiểu, và view mới sinh sau sẽ không có lọc.
- **Decision**: Bọc `parseServerMessages` — cửa chung của cả 2 nhánh. Nhánh `message_code` (đã render VI) **không** đi qua.
- **Alternatives**: (a) lọc ở `useApi`/`useNotify` — muộn hơn, và `ApiError.message` (đọc trực tiếp ở nhiều view, vd `ReferenceDataView.vue:175`) vẫn bẩn; (b) lọc ở BE — đúng về lâu dài nhưng vòng này **không được đụng `.py`**, và FE vẫn cần phòng thủ trước Frappe core.
- **Consequences**: Một điểm duy nhất phải test kỹ (bảng §7.5). Ba cửa khác (`404` `:302`, `409` `:306`, nhánh mặc định `:318`) **vẫn** đọc `data.message` thô ⇒ ghi thành nợ §11, **không** mở rộng trong vòng này để giữ bất biến TC-SAN-10.

---

## §11. Nợ để lại (chưa cấp số — cấp ở vòng sau)

1. **Lô 2 adoption**: 10 file còn lại ở §6.3 (mỗi file kèm test render trạng thái lỗi).
2. **Ba cửa chưa lọc trong `axios.ts`**: 404 (`:302`), 409 (`:306`), nhánh mặc định (`:318`) đọc `data?.message` thô — cùng họ với AC-UX-063, đóng khi lô 2 chạy.
3. **`useToast` không phân biệt lỗi chặn / không chặn** — sau khi lô 2 xong, cân nhắc chặn hẳn `toast.error` cho lỗi phát sinh khi có hộp thoại đang mở (guard, không phải quy ước miệng).
4. **AC-UX-055/056** — di trú 30 overlay tự vẽ + 4 file lai sang `BaseModal`; khi đó đường B của §5 tự tiêu biến.
