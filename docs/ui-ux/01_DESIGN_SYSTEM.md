# Design System nền — Token ngữ nghĩa + 7 primitive (Core Doc VÒNG 2)

| Mục             | Giá trị                                                                                                                                                                                  |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Phạm vi         | `frontend/src/components/ui/` · `frontend/tailwind.config.js` · `frontend/src/assets/styles/main.css` · `frontend/src/design/` — **cross-cutting, KHÔNG thuộc IMM-XX** |
| Loại tài liệu | Core Doc cross-cutting (design system) — spec thi hành cho FE dev vòng 2                                                                                                                |
| Owner            | BA (đặc tả) · FE dev (thi hành) · QA (chấm A1–A11)                                                                                                                                 |
| Trạng thái     | **Chốt để code** — spec-before-code gate ĐẠT                                                                                                                                   |
| Ngày đo        | 2026-07-31 (mọi số trong tài liệu này đo TỪ ĐĨA hôm nay)                                                                                                                         |
| Nhánh           | `feature/hieuc/core-refinement` @ `3a6a391`                                                                                                                                            |
| Tài liệu mẹ   | [`00_AUDIT_HIEN_TRANG.md`](./00_AUDIT_HIEN_TRANG.md) — §7.2 (nợ design-system) · §9 **ADR-UX-04** (quyết định) · §6 sổ `AC-UX-032…040`                                |

> **Vì sao có tài liệu này:** vòng 1 chỉ ĐO. §7.2 của tài liệu mẹ kết luận nợ gốc là **không có tầng 0**:
> 0 token màu ngữ nghĩa và 0 primitive dùng chung ⇒ mỗi màn tự chế màu + tự chế khung rỗng/lỗi.
> Sửa nợ hiển thị ở 135 route khi chưa có tầng 0 = nhân bản nợ. Vòng 2 **chỉ dựng tầng 0**, chưa áp vào route.

---

## §0. Phạm vi & Boundaries

**Always (bắt buộc mọi thay đổi vòng 2):**

- **0 đổi giao diện hiển thị.** Mọi token mới phải cho ra **đúng mã màu đang chạy** ở bậc 500; mọi primitive phải **bọc class `@layer` sẵn có** trong `main.css`.
- Mỗi primitive có **1 file test co-located** cùng tên, mount THẬT bằng `@vue/test-utils`.
- Chữ hiển thị **tiếng Việt đầy đủ** (`LL-FE-53`); mặc định copy khai trong `withDefaults`, không rải chuỗi rời rạc.
- Mọi token Tailwind mới phải có CSS var đối ứng **cùng lượt sửa** (guard parity 2 chiều chặn).

**Ask first (hỏi BA/PM trước khi làm):**

- Thêm **bậc màu** ngoài `{50, 500, 700}` hoặc thêm **họ màu** ngoài 5 họ đã chốt.
- Thêm primitive thứ 8 vào `components/ui/`.
- Đổi bất kỳ mã hex nào ở bậc **500** (⇒ đổi màu hiển thị toàn hệ).

**Never (tuyệt đối không, vòng 2):**

- **KHÔNG** sửa `frontend/src/views/**` (trừ 1 ngoại lệ test-drift ở §7), `src/stores/**`, `src/api/**`, bất kỳ `.py` nào.
- **KHÔNG** refactor `components/common/DetailLoadError.vue` (mang ngữ nghĩa CR-74 `notfound`/`forbidden`/`unknown` — ngoài phạm vi).
- **KHÔNG** đụng 49 view đang dùng `SkeletonLoader` (adoption làm **bên trong** `SkeletonLoader.vue`).
- **KHÔNG** thêm thư viện UI ngoài (kế thừa Never của tài liệu mẹ §0).
- **KHÔNG** fork lại CSS đã có trong `@layer components` (vd viết lại `.btn` bằng utility rời) — xem luật no-fork §3.0.
- **KHÔNG** dùng class palette thô (`emerald-*`, `slate-*`, `red-*`…) trong `components/ui/*.vue`.

---

## §1. Hiện trạng đo từ đĩa — 2026-07-31

| Số đo                                                                         | Giá trị                                                                                                                                                       | Cách đo                                                                                                                               |
| ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Token ngữ nghĩa trong`tailwind.config.js`                                   | **0** (chỉ có `brand`, `ink`)                                                                                                                       | `node -e "import('./tailwind.config.js').then(m=>console.log(Object.keys(m.default.theme.extend.colors)))"` → `[ 'brand', 'ink' ]` |
| Biến màu trong`main.css :root`                                              | **9** — `primary`, `primary-dim`, `success`, `warning`, `danger`, `neutral`, + 3 surface/text nhóm khác; **THIẾU `--color-info`** | đọc`main.css:6-31`                                                                                                                  |
| `components/ui/`                                                              | **không tồn tại**                                                                                                                                      | `ls frontend/src/components/ui` → `No such file or directory`                                                                      |
| Hardcode palette trong`views/` (5 họ `emerald\|amber\|rose\|red\|green`)       | **1690**                                                                                                                                                  | `grep -roE "(emerald\|amber\|rose\|red\|green)-[0-9]{2,3}" src/views --include=*.vue \| wc -l`                                             |
| Hardcode palette trong`views/` (10 họ, gồm `slate\|gray\|blue\|indigo\|teal`) | **6119**                                                                                                                                                  | cùng lệnh, mở rộng nhóm                                                                                                            |
| Hardcode palette trong`components/` (10 họ)                                  | **1118**                                                                                                                                                  | như trên, đổi thư mục                                                                                                             |
| View dùng`SkeletonLoader`                                                    | **49**                                                                                                                                                    | `grep -rl SkeletonLoader src --include=*.vue \| wc -l`                                                                                 |
| File test FE                                                                    | **290** (1 đỏ: `personaDashboards.test.ts`)                                                                                                           | `find src -name "*.test.ts" -o -name "*.spec.ts" \| wc -l`                                                                             |
| File`.vue` chứa chuỗi `Thử lại`                                         | **45**                                                                                                                                                    | `grep -rn "Thử lại" src --include=*.vue \| wc -l`                                                                                    |
| `@vue/test-utils`                                                             | `^2.4.11` (devDependency, đã có)                                                                                                                           | `package.json`                                                                                                                        |
| Vitest                                                                          | `^4.1.8`, `environment: jsdom`, `include: src/**/*.{test,spec}.ts`                                                                                        | `vitest.config.ts`                                                                                                                    |

**2 sự kiện đã kiểm chứng bằng thực nghiệm (không suy đoán):**

1. `tailwind.config.js` **import được từ vitest** — đã chạy thử file test tạm `src/design/__probe.test.ts` với
   `await import('../../tailwind.config.js')` → `Test Files 1 passed (1)` (đã xoá file tạm). ⇒ guard parity đọc **object thật**, không regex file nguồn.
2. 53 file test view **stub** `SkeletonLoader` (`{ SkeletonLoader: true }`) và **0 test nào assert `.skeleton`**
   (`grep -rn "\.skeleton" src --include=*.test.ts` → rỗng) ⇒ đổi *bên trong* `SkeletonLoader.vue` là an toàn.

---

## §2. Token màu ngữ nghĩa — SSoT 2 chiều

### 2.1 Bảng token (SSoT — 5 họ × 3 bậc = 15 token)

Quy ước: **bậc 500 = màu nền tảng đang chạy** (khoá cứng, bằng đúng biến `--color-*` cũ) ⇒ **0 đổi màu hiển thị**.
Bậc 50 = nền nhạt (badge/alert), bậc 700 = chữ đậm trên nền nhạt.

| Họ         | Bậc 50     | Bậc 500 (KHOÁ)      | Bậc 700    | Nguồn bậc 500                                                                                         | Ngữ nghĩa                         |
| ----------- | ----------- | --------------------- | ----------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `success` | `#ecfdf5` | **`#059669`** | `#047857` | `--color-success` (`main.css:17`)                                                                   | đạt / hoàn tất / trong ngưỡng |
| `warning` | `#fffbeb` | **`#d97706`** | `#b45309` | `--color-warning` (`main.css:18`)                                                                   | sắp đến hạn / cần chú ý      |
| `danger`  | `#fef2f2` | **`#dc2626`** | `#b91c1c` | `--color-danger` (`main.css:19`)                                                                    | quá hạn / lỗi / chặn            |
| `info`    | `#eff6ff` | **`#2563eb`** | `#1d4ed8` | **MỚI** — bằng `brand.600` (`tailwind.config.js`) đang dùng cho `.alert-info` họ blue | thông tin trung tính              |
| `neutral` | `#f8fafc` | **`#64748b`** | `#334155` | `--color-neutral` (`main.css:20`)                                                                   | không áp dụng / chưa có / phụ |

**Kiểm chứng “0 đổi màu”:** 3 bậc 500 của `success`/`warning`/`danger` và của `neutral` **trùng byte-per-byte** với 4 biến CSS đang chạy.
`neutral-500 #64748b` ≡ `slate-500`, `neutral-700 #334155` ≡ `slate-700`, `neutral-50 #f8fafc` ≡ `slate-50`
⇒ primitive thay `text-slate-700` bằng `text-neutral-700` cho **cùng pixel**, đồng thời hết vướng A6(a).

### 2.2 `frontend/tailwind.config.js` — hình dạng patch

Thêm **5 khoá** vào `theme.extend.colors`, **giữ nguyên** `brand` và `ink` (guard có test regression):

```js
colors: {
  brand: { /* GIỮ NGUYÊN */ },
  ink:   { /* GIỮ NGUYÊN */ },
  success: { 50: '#ecfdf5', 500: '#059669', 700: '#047857' },
  warning: { 50: '#fffbeb', 500: '#d97706', 700: '#b45309' },
  danger:  { 50: '#fef2f2', 500: '#dc2626', 700: '#b91c1c' },
  info:    { 50: '#eff6ff', 500: '#2563eb', 700: '#1d4ed8' },
  neutral: { 50: '#f8fafc', 500: '#64748b', 700: '#334155' },
},
```

**Ràng buộc chữ thường:** hex viết **lowercase 6 ký tự** (`^#[0-9a-f]{6}$`) — guard so sánh chuỗi, không chuẩn hoá hoa/thường.

### 2.3 `frontend/src/assets/styles/main.css` — hình dạng patch

Trong `:root` (khối `main.css:6-31`), **giữ nguyên toàn bộ biến cũ**, thêm:

```css
  /* Brand */
  --color-primary:     #2563eb;
  --color-primary-dim: #dbeafe;
  --color-success:     #059669;
  --color-warning:     #d97706;
  --color-danger:      #dc2626;
  --color-info:        #2563eb;   /* MỚI — A3: :root trước đây thiếu 'info' dù .alert-info đã dùng họ blue */
  --color-neutral:     #64748b;

  /* Token ngữ nghĩa — đối ứng 1-1 với theme.extend.colors (guard: src/design/tokens.parity.test.ts) */
  --ac-color-success-50:  #ecfdf5;
  --ac-color-success-500: #059669;
  --ac-color-success-700: #047857;
  --ac-color-warning-50:  #fffbeb;
  --ac-color-warning-500: #d97706;
  --ac-color-warning-700: #b45309;
  --ac-color-danger-50:   #fef2f2;
  --ac-color-danger-500:  #dc2626;
  --ac-color-danger-700:  #b91c1c;
  --ac-color-info-50:     #eff6ff;
  --ac-color-info-500:    #2563eb;
  --ac-color-info-700:    #1d4ed8;
  --ac-color-neutral-50:  #f8fafc;
  --ac-color-neutral-500: #64748b;
  --ac-color-neutral-700: #334155;
```

**Không** viết lại giá trị `@layer components` hiện có bằng `var(--ac-color-*)` trong vòng 2 — đó là bước di trú (vòng 3+),
làm chung lượt này sẽ trộn 2 rủi ro (đổi màu thật + refactor) và phá bất biến “0 đổi giao diện”.

### 2.4 Guard parity 2 chiều — `frontend/src/design/tokens.parity.test.ts` (A4)

| Mã                          | Bất biến                                                                                                                                                    | Cách chứng                                                             |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| **INV-DS-1**           | 5 họ`success/warning/danger/info/neutral` có mặt trong `theme.extend.colors`, mỗi họ có **đúng** tập bậc `{50,500,700}`                 | `Object.keys`                                                          |
| **INV-DS-2** (xuôi)   | ∀ token`<họ>.<bậc>` trong config ⇒ tồn tại `--ac-color-<họ>-<bậc>` trong `:root` với **hex giống hệt**                                 | đọc`main.css`, regex `--ac-color-([a-z]+)-(\d+):\s*(#[0-9a-f]{6})` |
| **INV-DS-3** (ngược) | ∀`--ac-color-*` trong `main.css` ⇒ có token tương ứng trong config (**0 var mồ côi**)                                                       | so 2 tập khoá, cả 2 chiều`toEqual([])`                             |
| **INV-DS-4**           | Pin 0-đổi-màu:`--ac-color-success-500 === --color-success`, tương tự `warning`/`danger`/`neutral`; và `--color-info === --ac-color-info-500` | đối chiếu trong cùng khối`:root`                                  |
| **INV-DS-5**           | Mọi hex khớp`^#[0-9a-f]{6}$`; 5 hex ở bậc 500 **đôi một khác nhau** (chống copy-paste nhầm họ)                                             | `new Set(...).size === 5`                                              |
| **INV-DS-6**           | Regression:`brand[600] === '#2563eb'` và `ink[900] === '#0d1117'` (vòng 2 không được đụng 2 họ cũ)                                              | đọc config                                                             |

Cách nạp config trong test (**đã kiểm chứng chạy được**, §1):

```ts
const cfg = (await import('../../tailwind.config.js')).default as {
  theme: { extend: { colors: Record<string, Record<string, string>> } }
}
```

Đường dẫn `main.css` lấy tương đối từ `import.meta.url` (khuôn giống `uiAuditDocParity.test.ts:26-29`), **không** hardcode đường dẫn tuyệt đối.

### 2.5 Bẫy đã biết — deep-merge palette Tailwind (BẮT BUỘC đọc trước khi code)

`theme.extend.colors.neutral = {50,500,700}` **KHÔNG thay** bảng màu `neutral` mặc định của Tailwind mà **trộn** vào:
`neutral-100/200/…/900` mặc định (xám ấm) vẫn dùng được và **lệch tông** với 3 bậc slate ta vừa khai.
⇒ Luật: trong `components/ui/*.vue` chỉ được dùng **đúng 3 bậc đã khai** của 5 họ ngữ nghĩa.
Khoá bằng bất biến bổ sung **INV-UI-4** (§6). Ghi sổ **AC-UX-040** để vòng 3 quyết định có khai đủ thang hay không.

---

## §3. Bảy primitive — hợp đồng API

### 3.0 Luật chung (áp cho cả 7)

1. **No-fork:** primitive **bọc** class `@layer components` sẵn có trong `main.css`; cấm chép lại chuỗi utility của class đó.
   Bảng bọc: `Button→.btn-*` · `Card→.card/.card-sm/.card-interactive` · `DataTable→.table-wrapper/.table-header/.table-cell` ·
   `Skeleton→.skeleton` · `EmptyState`/`ErrorState`→`.card` + `Button`. `Badge` **chưa có class @layer** ⇒ được phép khai utility,
   nhưng **phải** dùng token ngữ nghĩa (`bg-<họ>-50 text-<họ>-700`) và **giữ đúng 3 lớp kích thước của `StatusBadge.vue:15-21`**.
2. **Dumb component:** 0 gọi API, 0 `store`, 0 `useRouter`, 0 `localStorage`. Chỉ props/slots/emits.
3. **Class động phải là map tĩnh** — Tailwind JIT quét chuỗi literal; `` `bg-${tone}-50` `` sẽ **bị purge**.
   Bắt buộc khai `Record<Tone, string>` với chuỗi class viết đủ.
4. **`data-testid` đặt tên `ui-*`**, khai ngay trên root: `ui-button`, `ui-badge`, `ui-card`, `ui-datatable`, `ui-empty`, `ui-error`, `ui-skeleton`.
5. **Copy VI** khai trong `withDefaults`; danh sách chuỗi mặc định là SSoT ở §6 (guard đối chiếu).
6. **Fallthrough attrs bật mặc định** (1 root element) ⇒ caller truyền `class`/`style`/`aria-label` được merge — **không** khai `inheritAttrs: false`.
7. **Barrel** `index.ts` export cả 7 theo tên PascalCase.

### 3.1 `Button.vue`

| Prop         | Kiểu                                                | Mặc định     | Ghi chú                                                                                                |
| ------------ | ---------------------------------------------------- | --------------- | ------------------------------------------------------------------------------------------------------- |
| `variant`  | `'primary'\|'secondary'\|'danger'\|'success'\|'ghost'` | `'secondary'` | map tĩnh →`.btn-primary` / `.btn-secondary` / `.btn-danger` / `.btn-success` / `.btn-ghost` |
| `size`     | `'sm'\|'md'`                                        | `'md'`        | `sm` → thêm `text-sm px-3 py-1.5`; `md` → không thêm gì                                     |
| `type`     | `'button'\|'submit'`                                | `'button'`    | tránh submit ngoài ý muốn trong`<form>`                                                           |
| `disabled` | `boolean`                                          | `false`       |                                                                                                         |
| `loading`  | `boolean`                                          | `false`       | ⇒`disabled` thật + `aria-busy="true"`                                                             |

- Root: `<button :type :class="[variantClass, sizeClass]" :disabled="disabled || loading" :aria-busy="loading || undefined" data-testid="ui-button">`
- Slot: `default` (nhãn). Không có prop `label` — nhãn luôn do caller truyền ⇒ 0 chuỗi EN lọt vào primitive.
- Emits: không khai; `@click` đi theo fallthrough (trình duyệt tự chặn khi `disabled`).
- **Test tối thiểu (4):** ① 5 variant → đúng class `.btn-*`; ② `disabled`/`loading` → có attr `disabled` + `aria-busy`; ③ slot render + click phát ra khi enabled; ④ click **không** phát khi `disabled`.

### 3.2 `Badge.vue`

| Prop     | Kiểu                                             | Mặc định   |
| -------- | ------------------------------------------------- | ------------- |
| `tone` | `'success'\|'warning'\|'danger'\|'info'\|'neutral'` | `'neutral'` |
| `size` | `'xs'\|'sm'\|'md'`                                | `'sm'`      |

- `toneClass` (map tĩnh): `success → 'bg-success-50 text-success-700'`, tương tự 4 họ còn lại.
- `sizeClass` **sao đúng** `StatusBadge.vue:15-21`: `xs → 'px-1.5 py-0.5 text-[10px]'` · `sm → 'px-2.5 py-0.5 text-[11px]'` · `md → 'px-3 py-1 text-xs'`.
- Root: `<span class="inline-flex items-center font-medium rounded-full leading-none whitespace-nowrap" :class="[toneClass, sizeClass]" data-testid="ui-badge">` + slot `default`.
- **KHÔNG** đụng `StatusBadge.vue` vòng này (nó ánh xạ enum → nhãn VI qua `utils/formatters.ts`; hợp nhất là việc vòng 3, ghi sổ `AC-UX-038`).
- **Test tối thiểu (3):** ① 5 tone → đúng cặp class; ② mặc định `neutral` + `sm`; ③ slot text render.

### 3.3 `Card.vue`

| Prop            | Kiểu         | Mặc định   | Ghi chú                                                     |
| --------------- | ------------- | ------------- | ------------------------------------------------------------ |
| `padding`     | `'sm'\|'md'` | `'md'`      | `sm → .card-sm`, `md → .card`                          |
| `interactive` | `boolean`   | `false`     | ⇒`.card-interactive` (đã bao `.card`)                 |
| `title`       | `string`    | `undefined` | có thì render`<h3 class="text-base font-semibold mb-3">` |

- Slots: `default`, `title` (ưu tiên hơn prop), `actions` (góc phải hàng tiêu đề).
- Root: `<div :class="rootClass" data-testid="ui-card">`.
- **Test tối thiểu (4):** ① `padding` map đúng class; ② `interactive` → `.card-interactive`; ③ prop `title` render trong `h3`; ④ slot `title` thắng prop.

### 3.4 `DataTable.vue`

| Prop           | Kiểu                                                        | Mặc định               | Ghi chú                                                          |
| -------------- | ------------------------------------------------------------ | ------------------------- | ----------------------------------------------------------------- |
| `columns`    | `{ key: string; label: string; align?: 'left'\|'right' }[]` | — (bắt buộc)           | `label` là chữ VI do caller truyền                           |
| `rows`       | `Record<string, unknown>[]`                                | `[]`                    |                                                                   |
| `rowKey`     | `string`                                                   | `'name'`                | khoá`:key`                                                     |
| `loading`    | `boolean`                                                  | `false`                 | ⇒ tbody render 3 dòng`Skeleton`                               |
| `clickable`  | `boolean`                                                  | `false`                 | ⇒`<tr role="button" tabindex="0">` + `@keydown.enter/.space` |
| `emptyLabel` | `string`                                                   | `'Chưa có dữ liệu'` |                                                                   |
| `caption`    | `string`                                                   | `undefined`             | ⇒`<caption class="sr-only">` (a11y)                            |

- Root **bắt buộc** `.table-wrapper` (đã có `overflow-x-auto` + `overscroll-behavior-x: contain`) ⇒ trả nợ nhóm hazard bảng-tràn của tài liệu mẹ §7.1.
- `<th class="table-header">`, `<td class="table-cell">`. Slot theo cột: `#cell-<key>="{ row, value }"`; mặc định in `value` thô.
- Slot `empty` (mặc định `emptyLabel`), slot `loading` (mặc định 3 dòng `Skeleton`).
- Emits: `row-click` (payload = `row`) — **chỉ** khi `clickable`.
- **Test tối thiểu (5):** ① render đủ `<th>` theo `columns`; ② render đúng số `<tr>` theo `rows`; ③ slot `cell-<key>` ghi đè ô; ④ `rows=[]` → hiện `emptyLabel` với `colspan = columns.length`; ⑤ `clickable` + click dòng → emit `row-click` đúng payload (và **không** emit khi `clickable=false`).

### 3.5 `EmptyState.vue`

| Prop            | Kiểu      | Mặc định                             |
| --------------- | ---------- | --------------------------------------- |
| `title`       | `string` | — (bắt buộc, caller truyền chữ VI) |
| `hint`        | `string` | `undefined`                           |
| `actionLabel` | `string` | `undefined`                           |

- Root: `<div class="card p-8 text-center space-y-2" role="status" data-testid="ui-empty">`.
- `title` → `<p class="text-base font-medium text-neutral-700">`; `hint` → `<p class="text-sm text-neutral-500">`.
- `actionLabel` có ⇒ render `<Button variant="secondary" data-testid="ui-empty-action">` phát `action`.
- Slot `default` (nội dung phụ), slot `action` (ghi đè nút).
- **Test tối thiểu (4):** ① `title` render; ② không `hint` ⇒ 0 phần tử hint; ③ có `actionLabel` ⇒ nút hiện, click → emit `action`; ④ không `actionLabel` ⇒ 0 nút.

### 3.6 `ErrorState.vue`

| Prop           | Kiểu       | Mặc định                                          |
| -------------- | ----------- | ---------------------------------------------------- |
| `message`    | `string`  | `'Không tải được dữ liệu.'`                 |
| `hint`       | `string`  | `'Vui lòng thử lại hoặc tải lại trang.'`     |
| `retryable`  | `boolean` | `true`                                             |
| `retryLabel` | `string`  | **`'Thử lại'`** (khoá bởi A8 — xem §5) |

- Root: `<div class="card p-8 text-center space-y-3" role="alert" data-testid="ui-error">`.
- Nút thử lại: `<Button variant="ghost" data-testid="ui-error-retry">{{ retryLabel }}</Button>` → emit `retry`; ẩn khi `retryable=false`.
- Slot `action` cho nút phụ (vd “về danh sách”) — nhãn do caller truyền.
- **Không** mang ngữ nghĩa `notfound`/`forbidden` (đó là `DetailLoadError.vue`, giữ nguyên).
- **Test tối thiểu (4):** ① message/hint mặc định VI render; ② `message` truyền vào thắng mặc định; ③ click nút → emit `retry`; ④ `retryable=false` ⇒ 0 nút thử lại.

### 3.7 `Skeleton.vue`

- **Không props.** Root: `<div class="skeleton" aria-hidden="true" data-testid="ui-skeleton">` — 1 khối shimmer nguyên tử.
- Kích thước/bo góc do **caller truyền qua fallthrough** (`class="h-3.5 w-24 rounded"`, `:style="{ width: '70%' }"`) ⇒ khi thay thế trong `SkeletonLoader.vue` không đổi một pixel.
- `aria-hidden="true"`: khối trang trí, wrapper cha đã mang `aria-busy`/`aria-label` (`SkeletonLoader.vue:25,41,56,65`).
- **Test tối thiểu (4):** ① root có class `skeleton`; ② class caller được merge (`h-3.5 w-24`); ③ `style` caller được merge; ④ có `aria-hidden="true"` + `data-testid="ui-skeleton"`.

### 3.8 `index.ts` (barrel)

```ts
export { default as Badge } from './Badge.vue'
export { default as Button } from './Button.vue'
export { default as Card } from './Card.vue'
export { default as DataTable } from './DataTable.vue'
export { default as EmptyState } from './EmptyState.vue'
export { default as ErrorState } from './ErrorState.vue'
export { default as Skeleton } from './Skeleton.vue'
```

Guard vệ sinh đối chiếu: số dòng `export { default as X }` **== 7 == số file `.vue`**, tên trùng khít tên file.

---

## §4. Adoption LIVE — `SkeletonLoader` render QUA `ui/Skeleton` (A7)

**Vì sao bắt buộc:** primitive không được dùng ở đâu = shelf-ware. `SkeletonLoader.vue` là điểm áp dụng **duy nhất** an toàn của vòng 2
(49 view dùng nó, 53 file test **stub** nó, 0 test assert `.skeleton`).

**Cách làm:** thay **mọi** `<div class="skeleton …" />` bên trong `SkeletonLoader.vue` bằng `<Skeleton class="…" :style="…" />`.
Giữ nguyên: cấu trúc wrapper, số phần tử, thứ tự, mọi class kích thước, `aria-busy`, `aria-label`, `stagger-*`, `animation` inline.

**Bất biến KHÔNG-ĐỔI-GIAO-DIỆN — số phần tử `.skeleton` đếm từ mã hiện tại** (`SkeletonLoader.vue`, `rows` mặc định = 5):

| `variant`   | Cấu tạo (dòng mã hiện tại)                         | Số`.skeleton`      |
| ------------- | -------------------------------------------------------- | --------------------- |
| `kpi-cards` | 4 thẻ × 4 khối (`:16,:17,:19,:20`)                  | **16**          |
| `table`     | `rows` dòng × 6 khối (`:31-:36`)                  | **30** (rows=5) |
| `form`      | 6 nhóm × 2 (`:44,:45`) + `:48` + `:50` + `:51` | **15**          |
| `card`      | `:57` + `:58` + `rows` dòng (`:60`)             | **7** (rows=5)  |
| `list`      | `rows` × 4 khối (`:71,:73,:74,:76`)                | **20** (rows=5) |

**File test:** `frontend/src/components/common/SkeletonLoader.test.ts` (co-located, KHÔNG đặt trong `ui/` — xem §9 A5).

**Test tối thiểu (7):**
① với **cả 5** `variant`: `wrapper.findAllComponents(Skeleton).length > 0` (5 case);
② `variant='table'`, `rows=5` ⇒ `wrapper.findAll('.skeleton').length === 30`;
③ 4 variant còn lại khớp bảng trên (16 / 15 / 7 / 20) — chấm cùng 1 case dạng bảng.

**Cấm:** đổi API props của `SkeletonLoader` (`variant`, `rows`), đổi giá trị mặc định, đụng bất kỳ file nào trong 49 view.

---

## §5. Copy parity “Thử lại” (A8)

**Luật:** nhãn nút thử lại của `ui/ErrorState.vue` **bằng đúng** nhãn của `components/common/DetailLoadError.vue:71` = `Thử lại`
(hiện có ở **45** file `.vue` — đây là chuỗi de-facto của hệ thống, không được sáng tác biến thể “Tải lại”/“Thử lần nữa”).

**Cách guard (đặt trong `uiPrimitiveHygiene.test.ts` hoặc `ErrorState.test.ts` — chọn 1, khai rõ trong mã):**

1. Mount `ErrorState` → `wrapper.get('[data-testid="ui-error-retry"]').text().trim()` → chuỗi A.
2. Đọc `components/common/DetailLoadError.vue` bằng `readFileSync`, trích nhãn nút retry bằng regex bám `@click="emit('retry')"`
   rồi lấy text node kế tiếp (hoặc regex `/emit\('retry'\)"[^>]*>\s*([^<]+?)\s*</`) → chuỗi B.
3. `expect(A).toBe(B)` **và** `expect(A).toBe('Thử lại')` (chốt 2 đầu, tránh cả hai cùng trôi).

**Cấm tuyệt đối:** sửa/refactor `DetailLoadError.vue` (giữ ngữ nghĩa CR-74 `notfound`/`forbidden`/`unknown`).
Việc gộp `DetailLoadError` vào `ErrorState` **không** thuộc vòng 2 (ghi sổ `AC-UX-038`).

---

## §6. Guard vệ sinh primitive — `frontend/src/components/ui/uiPrimitiveHygiene.test.ts` (A6)

| Mã                                                                  | Bất biến                                                                                                                                     | Cách chứng                                                                                                               |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **INV-UI-1** (a)                                               | **0** hit `/(emerald\|amber\|rose\|red\|green\|slate\|gray\|blue\|indigo\|teal)-[0-9]{2,3}/` trong mọi `ui/*.vue`                            | đọc file,`match` toàn văn, in ra file+chuỗi vi phạm                                                                |
| **INV-UI-2** (b)                                               | Đúng**7** file `ui/*.vue`; mỗi file có **đúng 1** `ui/<Name>.test.ts` cùng tên; `index.ts` export đúng 7 tên đó | `readdirSync`                                                                                                            |
| **INV-UI-3** (c)                                               | Mọi**text node hiển thị** trong `<template>` của `ui/*.vue` thuộc allowlist VI §6.1; và **0** hit token EN cấm         | bóc`<template>`, xoá `{{…}}`, xoá comment, lấy text giữa `>` và `<`                                         |
| **INV-UI-4** (bổ sung, **không thay 3 bất biến A6**) | Mọi class dạng`<tiền tố>-<họ ngữ nghĩa>-<bậc>` trong `ui/*.vue` có bậc ∈ `{50,500,700}` (bẫy deep-merge §2.5)               | regex`\b(?:text\|bg\|border\|ring\|from\|via\|to\|divide\|placeholder\|accent)-(success\|warning\|danger\|info\|neutral)-(\d{2,3})\b` |

### 6.1 Allowlist chuỗi hiển thị VI (SSoT vòng 2)

Chỉ 2 chuỗi được phép nằm **cứng trong template**; phần còn lại đến từ props/slot do caller truyền:

| Chuỗi        | Nơi dùng                                                                               |
| ------------- | ---------------------------------------------------------------------------------------- |
| `Thử lại` | `ErrorState.vue` (nếu render trực tiếp thay vì qua prop)                           |
| *(rỗng)*   | mọi copy khác khai ở`withDefaults` trong `<script setup>`, không phải text node |

Chuỗi mặc định khai trong `<script setup>` (`'Chưa có dữ liệu'`, `'Không tải được dữ liệu.'`, `'Vui lòng thử lại hoặc tải lại trang.'`, `'Thử lại'`)
được INV-UI-3 kiểm bằng **danh sách EN cấm** thay vì allowlist (vì nằm ngoài template).

### 6.2 Danh sách token EN cấm (case-sensitive, quét toàn file trừ comment)

`Retry` · `Loading` · `No data` · `Error` · `Cancel` · `Save` · `Close` · `Submit` · `Search` · `Add` · `Edit` · `Delete` · `Confirm` · `Success` · `Warning` · `Failed`

> Viết thường (`success`, `warning`, `info`, `danger`, `neutral`) là **tên token/prop**, hợp lệ — vì vậy regex phải **phân biệt hoa thường**.

---

## §7. Test-drift `AC-UX-023` (A9) — ngoại lệ DUY NHẤT được chạm dưới `views/`

- File: `frontend/src/views/dashboard/personas/personaDashboards.test.ts:59`.
- Hiện: `expect(w.html()).toContain('Trưởng phòng VT-TTBYT')` — commit `44cbff9` đã rút tên persona khỏi tiêu đề
  (`OpsmgrDashboardView.vue:78` nay là `title="Bảng điều khiển"`), trong khi `PageHeader` **bị stub** ở test ⇒ chuỗi không còn xuất hiện.
- **Cách sửa BẮT BUỘC (bám ý định của TC `D-FE-1: current=opsmgr → render OpsmgrDashboardView`, miễn nhiễm đổi copy):**

```ts
import OpsmgrDashboardView from './OpsmgrDashboardView.vue'
// …
expect(w.findComponent(OpsmgrDashboardView).exists()).toBe(true)
```

  (`DashboardView.vue:10-36` import **tĩnh** 8 view persona ⇒ `findComponent` chạy được, không cần `flushPromises` bổ sung.)

- **KHÔNG** sửa `OpsmgrDashboardView.vue` để chuỗi cũ quay lại (sẽ đảo ngược `44cbff9`).
- **KHÔNG** đụng TC `D-FE-2` (`StoreDashboardView.vue:34` vẫn còn tên persona trong `title` ⇒ đang xanh thật).

---

## §8. Danh mục file được phép chạm — vòng 2 (A10)

**Được thêm mới (9 file):**

```
frontend/src/components/ui/Button.vue        + Button.test.ts
frontend/src/components/ui/Badge.vue         + Badge.test.ts
frontend/src/components/ui/Card.vue          + Card.test.ts
frontend/src/components/ui/DataTable.vue     + DataTable.test.ts
frontend/src/components/ui/EmptyState.vue    + EmptyState.test.ts
frontend/src/components/ui/ErrorState.vue    + ErrorState.test.ts
frontend/src/components/ui/Skeleton.vue      + Skeleton.test.ts
frontend/src/components/ui/index.ts
frontend/src/components/ui/uiPrimitiveHygiene.test.ts
frontend/src/design/tokens.parity.test.ts
frontend/src/components/common/SkeletonLoader.test.ts
```

**Được sửa (4 file):**

```
frontend/tailwind.config.js                                  (§2.2 — chỉ thêm 5 khoá màu)
frontend/src/assets/styles/main.css                          (§2.3 — chỉ thêm biến trong :root)
frontend/src/components/common/SkeletonLoader.vue            (§4 — thay div.skeleton bằng <Skeleton>)
frontend/src/views/dashboard/personas/personaDashboards.test.ts (§7 — ngoại lệ DUY NHẤT dưới views/)
```

**Doc (BA đã land trước khi code):** `docs/ui-ux/01_DESIGN_SYSTEM.md` (file này) · `docs/ui-ux/00_AUDIT_HIEN_TRANG.md` (§6 sổ, §7.2 ghi chú, §9 ADR-UX-04, §10 ghim).

**Ngoài danh mục trên: 0 file.** `git status --short` phải cho **0** `.py`, **0** `src/views/**/*.vue`, **0** `src/stores/**`, **0** `src/api/**`.

---

## §9. Truy vết Acceptance A1–A11 ⇄ spec ⇄ lệnh đo

| AC  | Mục spec                   | Lệnh / cách chấm                                                                                                                                                                                                |
| --- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| A1  | §3                         | `ls frontend/src/components/ui/*.vue \| wc -l` → **7**; có `index.ts`                                                                                                                                   |
| A2  | §2.1, §2.2                | `node -e "import('./tailwind.config.js').then(m=>{const c=m.default.theme.extend.colors;for(const k of ['success','warning','danger','info','neutral'])console.log(k,Object.keys(c[k]))})"` → 5 khoá × 3 bậc |
| A3  | §2.3                       | `grep -c "^\s*--ac-color-" frontend/src/assets/styles/main.css` → **15**; `grep -n -- "--color-info" …` → có; hex bậc 500 trùng 4 biến cũ                                                        |
| A4  | §2.4                       | `npx vitest run src/design/tokens.parity.test.ts` → đọc `Tests N passed` bằng mắt (spec ra **6** case)                                                                                              |
| A5  | §3.1–3.7                  | `npx vitest run src/components/ui --exclude '**/uiPrimitiveHygiene.test.ts'` → `Test Files 7 passed (7)`, tổng case **28 ≥ 21**                                                                       |
| A6  | §6                         | `npx vitest run src/components/ui/uiPrimitiveHygiene.test.ts` → xanh (4 bất biến; 3 bất biến A6 + 1 bổ sung)                                                                                               |
| A7  | §4                         | `npx vitest run src/components/common/SkeletonLoader.test.ts` → xanh; `git status --short frontend/src/views` → rỗng                                                                                        |
| A8  | §5                         | assert 2 đầu chuỗi (`ErrorState` render ⇄ `DetailLoadError.vue` trên đĩa)                                                                                                                               |
| A9  | §7                         | `npx vitest run` → 0 file đỏ; **delta kỳ vọng `+10` file test** (290 → **300**) — xem lưu ý dưới                                                                                        |
| A10 | §8                         | `git status --short` — allowlist §8                                                                                                                                                                            |
| A11 | 00_AUDIT §6/§7.2/§9/§10 | `npx vitest run src/router/uiAuditDocParity.test.ts` → `Tests 15 passed (15)`                                                                                                                                 |

> **Lưu ý A5 (mâu thuẫn đề bài đã giải):** `uiPrimitiveHygiene.test.ts` nằm **trong** `ui/` (A6 chốt đường dẫn), nên
> `npx vitest run src/components/ui` **trần** sẽ in `Test Files 8 passed (8)` — **đúng, không phải lỗi**. Lệnh chấm A5 dùng
> `--exclude '**/uiPrimitiveHygiene.test.ts'` (flag có thật trong vitest 4: `--exclude <glob>`), hoặc liệt kê 7 đường dẫn tường minh.

> **Lưu ý A9 (chấm DELTA, không chấm số tuyệt đối):** baseline đo hôm nay là **290** file test (§1), không phải 289 —
> 289 là số **passed**, 1 file đỏ. Vòng 2 thêm 7 (primitive) + 1 (parity) + 1 (hygiene) + 1 (adoption `SkeletonLoader.test.ts`) = **+10** ⇒ **300 file, 0 đỏ**.

---

## §10. Rủi ro & việc để lại vòng 3

| # | Rủi ro / nợ                                                                           | Xử lý                                                                                                                        |
| - | --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 1 | Primitive chưa được view nào dùng (trừ`Skeleton`) ⇒ nguy cơ shelf-ware       | Vòng 3 áp`DataTable`/`EmptyState`/`ErrorState` cho nhóm hazard bảng-tràn (17 route, mẹ §7.1) — sổ `AC-UX-038` |
| 2 | `StatusBadge.vue` và `Badge.vue` cùng tồn tại (2 nguồn kích thước badge)    | Vòng 3:`StatusBadge` bọc `Badge`, giữ ánh xạ enum→VI ở `utils/formatters.ts`                                      |
| 3 | `FormField` / `IconButton` / `ClickableRow` / `PageTitle` (mẹ §7.2) chưa có | Vòng 3 — sổ`AC-UX-039`                                                                                                    |
| 4 | Bậc màu chưa khai của`neutral` (deep-merge Tailwind) vẫn dùng được           | INV-UI-4 chặn trong`ui/`; toàn FE chờ vòng 3 — sổ `AC-UX-040`                                                        |
| 5 | `@layer components` vẫn hardcode `slate/emerald/red…`                             | Di trú sang`var(--ac-color-*)` là **vòng 3+**, làm riêng để giữ bất biến “0 đổi màu” của vòng 2       |
| 6 | 1690/6119 hardcode trong`views/` chưa giảm                                          | Chỉ giảm khi adoption chạy (vòng 3–5); vòng 2**không** hứa giảm số này                                        |

---

## §11. Sai lệch thi hành so với §3 (FE dev ghi lại — 2026-07-31, sau khi code)

Hợp đồng API §3 do BA soạn; danh sách test-case chấm (TC-UX2-04…14) yêu cầu **rộng hơn** ở 6 điểm.
Mã đã cài là **tập cha** của cả hai — mọi bất biến §3 vẫn đúng. Ghi ở đây để doc ⇄ code không lệch:

| # | §3 nói                                       | Mã đã cài                                                                                                      | Vì sao                                                                                                                    |
| - | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| 1 | `Button` không có `iconOnly`             | thêm`iconOnly` + `ariaLabel`, thiếu nhãn ⇒ `console.warn` đúng 1 lần lúc mount                       | TC-UX2-06 — bắt nợ a11y`AC-UX-002` ngay tại gốc thay vì đi vá 87 màn                                            |
| 2 | `Button` chỉ khai `aria-busy`             | thêm`aria-disabled="true"` + chặn `emit('click')` khi disabled/loading                                       | TC-UX2-05 —`disabled` thuần HTML không phát tín hiệu cho một số trình đọc màn hình                          |
| 3 | `Badge` 5 tone                               | 6 tone (thêm`brand` = `bg-brand-50 text-brand-700`)                                                           | TC-UX2-07 đòi 6 tập class khác nhau;`brand` là họ token có sẵn, không phải palette thô                        |
| 4 | `Card` root `<div>`                        | root`<section>`, có tiêu đề ⇒ `aria-labelledby` trỏ `useId()`                                          | TC-UX2-08 —`<section>` vô danh vẫn là `generic` nên không đổi ngữ nghĩa khi không có tiêu đề            |
| 5 | `EmptyState.title` bắt buộc; prop `hint` | `title` mặc định `'Chưa có dữ liệu'`; prop `description` (giữ `hint` làm bí danh)                | TC-UX2-11 — mặc định an toàn, caller quên truyền vẫn không ra khung câm                                          |
| 6 | `Skeleton` không props                      | props`lines`/`width`/`height`/`rounded`; **`lines` mặc định 1 ⇒ vẫn là 1 khối nguyên tử** | TC-UX2-14 đòi`lines=3`; giữ chế độ atom nên bất biến đếm của `SkeletonLoader` (30/16/15/7/20) không đổi |
| 7 | `DataTable` slot `empty`/`loading`       | thêm prop`error` + slot `error` (dựng `ErrorState`, phát `retry`)                                       | Task FE T5d — 83/135 màn đang thiếu lối thử lại                                                                     |

**Rủi ro MỚI phát hiện khi biên dịch thật (chưa xử lý — thuộc `AC-UX-040`):**
khai `colors.neutral.{50,500,700}` **đè** đúng 3 bậc đó của bảng `neutral` mặc định Tailwind ⇒ **52 lần dùng
`*-neutral-{50,500,700}` có sẵn ở 8 file NGOÀI `components/ui/`** đổi tông xám ấm → xám lạnh:
`neutral-50 #fafafa → #f8fafc` · `neutral-500 #737373 → #64748b` · `neutral-700 #404040 → #334155`.
Nặng nhất: `views/needs/NeedsRequestDetailView.vue` (36 lần). Vòng 2 **không được sửa `views/`** (§8) nên đây là
việc của vòng 3: hoặc đổi 52 chỗ đó sang token đúng ngữ nghĩa, hoặc BA ratify việc đồng bộ về tông slate.
