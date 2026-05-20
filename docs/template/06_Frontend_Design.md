# 06 — Thiết kế Frontend (Frontend Design / UI-UX Guide)

| Mục | Giá trị |
|---|---|
| Module | IMM-`<XX>` |
| Phạm vi | Per-module |
| Owner | FE Lead + Designer |
| Module accent | `<orange-600 / emerald-600 / cyan-600 …>` (xem `docs/res/design-frontend.md §7`) |

> **Mục đích**: Mô tả màn hình module — sitemap, archetype, components dùng, state, copy tiếng Việt. KHÔNG re-define design system — bám `docs/res/design-frontend.md`. Chỉ ghi đặc trưng module.

---

## 1. Sitemap / Route map
**Viết gì**: Bảng `Route · Tên trang · Archetype (Hub/Dashboard/List/Detail/Form/Wizard) · Role · Component chính`. URL convention semantic kebab-case plural.

## 2. Sidebar nav module
**Viết gì**: Snippet đăng ký vào `MODULE_NAV` của `AppSidebar.vue` — title, accent color, items theo workflow user thường dùng.

```ts
"imm-<XX>": {
  title: "IMM-<XX> · <Tên module>",
  accent: "orange-600",
  items: [
    { icon: "chart",  label: "Tổng quan",     to: "/<module>/dashboard" },
    { icon: "wrench", label: "Lệnh <…>",      to: "/<module>/<entities>" },
    { icon: "clock",  label: "Sắp đến SLA",   to: "/<module>/<entities>?filter=sla_warning" },
  ],
}
```

## 3. Thiết kế giao diện — 2 cấp

Phân biệt 2 loại UI artefact (KHÔNG gộp):

### 3.a. UI Mockup (pre-build)
**Viết gì**: Wireframe / mockup **trước khi build code**, dùng để align với BA + designer + stakeholder. Tool: Figma / draw.io / ASCII low-fi. Mỗi archetype màn hình có 1 mockup chuẩn — tối thiểu cover:
- Mockup hub / dashboard chính (entry point)
- Mockup list view (1 tiêu biểu, áp dụng cho mọi list khác)
- Mockup detail view
- Mockup form (create / edit)
- Mockup các state đặc biệt (empty / error / loading)
- Mockup riêng cho role đặc thù nếu có (vd Vendor portal khác user thường — chỉ thêm khi UX khác biệt)

Lưu link Figma trong frontmatter HOẶC export PNG vào `docs/imm-XX/mockups/<screen>.png`.

### 3.b. UI Screenshot (post-build)
**Viết gì**: **Sau khi build xong**, chụp UI thực tế với data sample. Mỗi chức năng chính 1 ảnh + caption ngắn. Dùng cho:
- Báo cáo final (file 11)
- User Guide (file 09 §I)
- Release Notes (file 09 §II)
- Demo cho stakeholder

Pattern: lưu ảnh `docs/imm-XX/screenshots/<feature>.png` + caption "Hình N.X: Giao diện `<chức năng>`". Đánh số liên tục để tự sinh danh mục hình vẽ (file 11).

## 3.c. Trang chi tiết theo archetype
**Viết gì**: Mỗi archetype dùng (Dashboard/List/Detail/Form/Wizard) → 1 sub-section. Template:

```markdown
### 3.X. <Archetype> (`<route>`)

> Bám `docs/res/design-frontend.md §3.X`.

**Filter bar / Tabs / KPI / Form section**:
| Filter / Cột / Field | Type | Default / Render |
|---|---|---|
| ... | ... | ... |

**Search placeholder**: <copy chính xác — xem §3.c.i>
**Searchable fields**: <`name`, `<biz_field_1>`, …> (khớp `pop_search()` BE — file 05 §3.1)

**Action buttons**: <action chính theo workflow state>

**API gọi**: <endpoint + cache TTL>

**State**:
- Loading: <skeleton 5 row / spinner button>
- Empty: <copy + CTA>
- Error: <pattern>
```

### 3.c.i. Search placeholder — TRUTH-IN-UI (BẮT BUỘC)

**Sự cố tham chiếu (2026-05-20)**: `/needs-requests` ô tìm kiếm ghi
"Tìm theo mã, model, khoa..." nhưng BE chỉ search trên `name` +
`device_model_ref` — user gõ tên khoa thì không ra kết quả → mất niềm tin.

**Hợp đồng**:

- Placeholder phải **liệt kê đúng** các field mà BE (hoặc client-side
  filter) thực sự tìm. CẤM ghi field không tìm được, CẤM bỏ sót field
  tìm được.
- Khi mở rộng / thu hẹp `searchable_fields` BE → **đồng thời** cập nhật
  placeholder. Hai nguồn này là **mirror**, không phải copy độc lập.
- Diễn đạt theo nghiệp vụ, không theo schema: dùng "mã phiếu" thay vì
  `name`, "mã model" thay vì `device_model_ref`. Nhưng phải phân biệt
  "mã model" (search trên link ID) vs "tên model" (search trên model_name)
  — tránh hứa hẹn sai.
- **"Tên ..." = phải dùng `link_search`** (file 05 §3.1.a): nếu placeholder
  hứa "tên model / tên NCC / tên thiết bị" thì BE phải khai báo
  `link_search={"<link_field>": ("<Linked DocType>", "<display_field>")}`
  để resolve display name → link ID. Direct LIKE trên link ID (vd
  `device_model_ref`) CHỈ tìm theo mã, không theo tên.
- Pattern copy: `"Tìm theo <A>, <B> hoặc <C>..."` (≤ 3 nhãn). Nếu list
  dài hơn 3 → rút gọn nhưng KHÔNG bịa thêm.

**Ví dụ đúng (Wave 2 sau fix 2026-05-20)**:

| View | BE `searchable_fields` + `link_search` | Placeholder |
|---|---|---|
| `NeedsRequestListView` | `["name"]` + link_search `device_model_ref → IMM Device Model.model_name` | "Tìm theo mã phiếu hoặc tên model..." |
| `ProcurementPlanListView` | `["name", "plan_period"]` | "Tìm theo mã kế hoạch hoặc kỳ kế hoạch..." |
| `TechSpecListView` | `["name", "version"]` + link_search `device_model_ref → IMM Device Model.model_name` | "Tìm theo mã hồ sơ, tên model hoặc phiên bản..." |
| `AvlListView` | `["name"]` + link_search `supplier → AC Supplier.supplier_name` | "Tìm theo mã AVL hoặc tên nhà cung cấp..." |
| `DecisionListView` | `["name", "spec_ref"]` + link_search `winner_supplier → AC Supplier.supplier_name` | "Tìm theo mã quyết định, mã hồ sơ hoặc tên NCC..." |

**Reminder hệ quả**: khi placeholder dùng từ "**tên**" cho 1 entity nào đó
mà entity đó ở doctype khác (vd "tên model" — model_name sống trên
`IMM Device Model`, không trên parent) → BE **bắt buộc** dùng
`link_search` (file 05 §3.1.a). Direct LIKE trên link ID chỉ match mã,
không match tên — sẽ giống sự cố "khoa" trên `/needs-requests` 2026-05-20.

**Review checklist** (PR review BẮT BUỘC tick):
- [ ] Mở BE list endpoint, đối chiếu `pop_search(_, [...])` hoặc
      `or_filters=[...]` với placeholder.
- [ ] Mọi label trong placeholder có ≥ 1 field BE tương ứng.
- [ ] Mọi field BE searchable đáng kể được phản ánh trong placeholder.

### 3.c.ii. Auto-search debounce — KHÔNG bắt user bấm nút

Mọi list view dùng `ListFilterBar` đều **tự động** apply search sau khi user
ngừng gõ. Đây là hành vi mặc định của component (`searchDebounceMs: 350`
trong `components/common/ListFilterBar.vue`) — view tiêu thụ KHÔNG cần wire
debounce riêng.

**Hợp đồng**:

- Khi user gõ vào ô search và dừng `searchDebounceMs` ms → component emit
  `apply` (cùng event với nhấn nút Tìm). View phải gắn `@apply="<handler
  reload list>"`.
- Nhấn nút "Tìm" hoặc Enter → flush debounce + emit `apply` ngay lập tức.
- Khi parent set `search=''` programmatically (reset filter) → debounce
  KHÔNG fire (vì bind `:value` + `@input`, không phải `v-model`). Parent
  tự gọi handler reload trong `resetFilters()`.
- Filter SELECT (workflow_state, category, …) phát `@change="applyFilters"`
  → instant apply, không cần debounce (event rời rạc).

**CẤM**:

- Tự viết `useDebounceFn` / `setTimeout` cho ô search trong list view
  (đã có sẵn — sẽ double-fire). Tham chiếu: `SparePartListView` cũ đã
  bị remove `watch(q, debouncedSearch)` trong cleanup 2026-05-20.
- Đặt `searchDebounceMs={0}` trừ khi list quá nặng (>2s/lần load) và
  cần đợi user xác nhận.
- Thêm nút "Tìm" thứ 2 ngoài bar — luôn dùng nút sẵn trong `ListFilterBar`.

**Mức delay đề xuất**:

| Tình huống | `searchDebounceMs` |
|---|---|
| Mặc định (mọi list ≤ 100k rows) | `350` (không cần truyền — đã là default) |
| List rất nhẹ (cached / dưới 1k row) | `200` (nhanh hơn 1 chút) |
| List rất nặng / endpoint > 1s | `600`–`800` (giảm số lần fire) |
| Tắt auto-search (button-only) | `0` |

## 4. Component custom của module
**Viết gì**: Bảng `Component · Mục đích · Props`. Đặt trong `frontend/src/components/<module>/`. Component dùng ≥ 2 module → promote ra `components/common/`.

## 5. Pinia store
**Viết gì**: File `stores/imm<XX>.ts`. State + Action + Persist policy (chỉ persist filter, không persist data record).

## 6. Vue Query keys
**Viết gì**: Snippet keys + invalidate rule sau mutation.

```ts
const keys = {
  dashboard: ['imm<XX>', 'dashboard'],
  list: (filters: F) => ['imm<XX>', 'list', filters],
  detail: (name: string) => ['imm<XX>', 'detail', name],
}
```

## 6b. API call pattern — useApi().run()

**Viết gì**: Mọi mutation gọi qua `useApi().run(fn, opts)` để có toast + loading + field error mapping tự động:

```ts
import { useApi } from '@/composables/useApi'
import { createRepair } from '@/api/imm<XX>'

const api = useApi()
const formErrors = reactive<Record<string, string>>({})

async function onSubmit() {
  formErrors = {}
  const result = await api.run(
    () => createRepair({ asset_ref: form.asset, priority: form.priority }),
    {
      successMessage: 'Đã tạo lệnh sửa chữa',
      onFieldError: (fields) => Object.assign(formErrors, fields),
    }
  )
  if (result) {
    // Happy path — result là response.data (đã unwrap envelope)
    router.push(`/cm/repairs/${result.name}`)
  }
  // Error path: useApi đã show toast + populate fields, không cần xử lý thêm
}
```

**Quy ước**:
- `result` trả về dữ liệu đã unwrap (`response.data` từ envelope `{success, data}`).
- `result` = `null` khi error → flow KHÔNG vào happy path.
- `onFieldError` map field-level error → form state cho inline display.
- Toast tự động phân loại theo `ApiError.isBusinessError` / `isSystemError` (xem 05 §1.4).
- `silentError: true` khi muốn tự handle error UI (vd modal confirm).

## 6c. TypeScript types — folder structure

`frontend/src/types/` đã có sẵn — KHÔNG inline type trong component:

```
frontend/src/types/
├── common.ts       # Paginated<T>, ApiResponse<T>, ApiError shared
├── auth.ts         # User, Session, Role
├── imm00.ts        # Master / cross-cutting
├── imm0X.ts        # Per-module types
└── inventory.ts    # Cross-module entities
```

Khi thêm module: tạo `imm<XX>.ts` mới, KHÔNG inline trong view. Type phải mirror BE DTO 1-1.

## 7. Quy tắc ngôn ngữ FE (BẮT BUỘC — bám 01 §IV.1.c)

### 7.a. Nguyên tắc cứng
- **100% tiếng Việt** mọi label, button, message, toast, error inline, placeholder, tooltip.
- **KHÔNG dùng mã code / ID làm tên hiển thị**. Mọi entity hiển thị bằng tên tự nhiên.
- **Mã code** (UDI, serial, mã WO, mã IR) khi cần show → **đặt nhỏ phía dưới** tên tự nhiên, font-mono, `text-xs text-slate-500`.
- Technical token (mã ErrorCode, workflow state value tiếng Anh) KHÔNG hiển thị cho end-user — map qua i18n.

### 7.b. Pattern hiển thị thực thể (Entity display pattern)

```
┌────────────────────────────────────┐
│ Máy theo dõi bệnh nhân — BS Nội    │ ← H3 tự nhiên (text-base/lg, font-semibold)
│ AC-MON-0042 · S/N: PHILIPS-MX450    │ ← Mã code phụ (text-xs text-slate-500 font-mono)
└────────────────────────────────────┘
```

Áp dụng ở mọi nơi entity xuất hiện: list cell, detail header, dropdown option, link card.

### 7.c. Bảng từ ngữ chuẩn hóa
**Viết gì**: Bảng `Khái niệm · Tiếng Việt · Tránh từ`. Chốt từ ngữ cho mọi state + action chính. i18n key namespace `imm<XX>.<screen>.<element>`. KHÔNG để 2 dev viết "Lệnh" / "Phiếu" cho cùng 1 thứ.

## 7d. Linked / Cascade fields (BẮT BUỘC khi có quan hệ phụ thuộc)

### 7d.a. Khi nào cần cascade
Khi field B chỉ valid khi field A có giá trị xác định. Ví dụ:
- Khoa / phòng → Tủ thiết bị thuộc khoa → Asset thuộc tủ
- Nguồn (`source_type`) → Mã nguồn (`source_name`) — Dynamic Link
- Loại thiết bị → Model → Serial cụ thể
- Vendor → Service contract còn hiệu lực

### 7d.b. Hành vi chuẩn
- Field cha đổi → field con **reset value + reload options** (KHÔNG giữ value cũ — invalid).
- Field con dùng `<LinkSearch>` với prop `filters` phụ thuộc field cha.
- Khi field cha rỗng → field con disabled + placeholder "Chọn `<field cha>` trước".
- Validate cuối: BE re-check parent-child consistency (FE convenience, BE truth).

### 7d.c. Pattern code

```ts
// frontend/src/views/<module>/<Form>.vue
const department = ref<string | null>(null);
const cabinet = ref<string | null>(null);
const asset = ref<string | null>(null);

// Reset cascade khi cha đổi
watch(department, () => {
  cabinet.value = null;
  asset.value = null;
});
watch(cabinet, () => {
  asset.value = null;
});

// LinkSearch options phụ thuộc cha
const cabinetFilters = computed(() => ({
  department: department.value,
}));
```

```vue
<LinkSearch v-model="department" doctype="AC Department" />
<LinkSearch v-model="cabinet"
            doctype="AC Cabinet"
            :filters="cabinetFilters"
            :disabled="!department"
            placeholder="Chọn khoa trước" />
<LinkSearch v-model="asset"
            doctype="AC Asset"
            :filters="{ cabinet }"
            :disabled="!cabinet" />
```

## 7e. Input tight — chống nhập sai (BẮT BUỘC)

### 7e.a. Ưu tiên picker thay free-text
Domain hữu hạn → KHÔNG cho free-text:

| Loại input | Dùng |
|---|---|
| Date | `<DateInput>` mask `dd/mm/yyyy` (KHÔNG `<input type="text">`) |
| Datetime | `<DateTimeInput>` mask `dd/mm/yyyy hh:mm` |
| Number + đơn vị | number + `<SmartSelect>` unit (KHÔNG free-text `35°C`) |
| Enum | `<RadioChip>` (≤ 4 option) hoặc `<SmartSelect>` (≥ 5) |
| Reference DocType | `<LinkSearch>` autocomplete (KHÔNG copy-paste mã) |
| Boolean | Toggle / Checkbox (KHÔNG select Yes/No) |
| Range | Slider hoặc 2 input (min, max) (KHÔNG free-text) |

### 7e.b. Validation realtime
- Inline error xuất hiện **ngay khi user blur khỏi field** invalid (không chờ submit).
- Button submit **disabled** khi form còn lỗi → user KHÔNG thử submit + nhận error sau.
- Required marker `*` đỏ sau label.
- Error message dưới field: `text-rose-600 text-xs mt-1` — cụ thể, không generic ("Field này bắt buộc" ❌ → "Vui lòng chọn thiết bị" ✓).

### 7e.c. Mask + format input
- Serial / mã thiết bị có pattern → mask + uppercase tự động.
- Số điện thoại → mask `0xxx xxx xxx`.
- Số có phân tách nghìn → format khi blur (vd `1500000` → `1 500 000`).
- Datetime VN → mask + accept paste cả `06/05/2026` lẫn `2026-05-06`.

### 7e.d. Confirm modal cho hành động không undo
- Submit final / Approve / Decommission / Cancel sau Submit → `<BaseModal>` confirm với:
  - Tóm tắt hành động (1-2 câu)
  - Checkbox "Tôi xác nhận hành động này"
  - Button danger (đỏ) ở primary, ghost ở Cancel

## 8. Empty / Error / Loading copy
**Viết gì**: Bảng `Tình huống · Copy`. Cover: empty list (no data), empty filter, empty permission, loading skeleton, server error, submit success, concurrent error.

## 9. Accessibility checklist module
**Viết gì**: Module-specific items (action button có aria-label, SLA countdown aria-live, form label, status badge role). Bám `design-frontend.md §10`.

## 10. Print spec (nếu có)
**Viết gì**: Trang nào cần in (WO closed report, certificate…). Hide chrome, layout 1 cột. Generate server-side qua Frappe print format (KHÔNG FE — sai font VN).

---

## DoD — File 06 hoàn chỉnh

- [ ] Sitemap đủ mọi route module
- [ ] **UI Mockup (pre-build)** ≥ 4 mockup chính
- [ ] **UI Screenshot (post-build)** ≥ 5 ảnh thực tế cho báo cáo / user guide
- [ ] Mỗi route có archetype + component chính
- [ ] Sidebar nav config đầy đủ
- [ ] Mỗi archetype dùng có table columns / form section / state mapping
- [ ] Component custom liệt kê
- [ ] **Type definitions** (mirror BE — file 05 §1.4) đầy đủ trong `frontend/src/types/imm<XX>.ts`
- [ ] **State quản lý đúng phân lớp**: server data → TanStack Vue Query · UI state → Pinia store
- [ ] Vue Query keys chuẩn hóa + invalidate đúng sau mutation
- [ ] **Quy tắc ngôn ngữ FE (§7)**: 100% tiếng Việt + KHÔNG dùng mã code làm tên hiển thị + entity display pattern
- [ ] Copy tiếng Việt chốt cho state + action chính (bảng từ ngữ §7.c)
- [ ] **Linked / Cascade fields (§7d)**: mọi field phụ thuộc đều cascade reset + reload
- [ ] **Input tight (§7e)**: picker thay free-text + validation realtime + button disabled khi invalid + confirm modal cho action không undo
- [ ] **Search placeholder (§3.c.i)**: list view có search box phải khớp 1-1 với `searchable_fields` BE (file 05 §3.1) — không hứa field không tìm được, không bỏ sót field tìm được
- [ ] **Auto-search debounce (§3.c.ii)**: list view dùng `ListFilterBar` mặc định (350ms debounce) — KHÔNG tự viết `useDebounceFn` / `setTimeout` cho ô search; mọi consumer phải có `@apply="<reload handler>"`
- [ ] Empty / Error / Loading copy đủ
- [ ] Error response từ BE map đúng tier (toast / modal / inline) — bám 05 §1.3
- [ ] Accessibility checklist module
- [ ] Reviewed bởi FE Lead + Designer + BA
