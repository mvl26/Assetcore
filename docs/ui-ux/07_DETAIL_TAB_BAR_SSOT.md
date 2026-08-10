# 07 — Diệt thanh tab tự chế: một SSoT thanh tab (`DetailTabBar.vue`) + nhãn trạng thái MR

| Mục | Giá trị |
|---|---|
| Phạm vi | `frontend/src/components/common/DetailTabBar.vue` (SSoT) · 3 màn lô 1 · `frontend/src/utils/formatters.ts` (`STATUS_MAP`) |
| Sổ số hiệu | **AC-UX-067** (mở rộng SSoT) · **AC-UX-068** (di trú lô 1) · **AC-UX-069** (guard CHỈ-GIẢM) · **AC-UX-003 ĐÓNG** · **AC-UX-052 lô 1 ĐÓNG** |
| Trạng thái | Accepted — spec chốt, chờ [FE] hiện thực |
| Cập nhật | 2026-08-04 |
| Owner | BA + FE Lead |

## Tài liệu liên quan

- [`00_AUDIT_HIEN_TRANG.md`](./00_AUDIT_HIEN_TRANG.md) — bản đồ nợ + sổ backlog AC-UX (§6)
- [`03_DETAIL_PAGE_SHELL.md`](./03_DETAIL_PAGE_SHELL.md) — khuôn màn chi tiết; `DetailPageShell` nhận `tabs` + `activeTab` dạng **prop** và tự render `DetailTabBar` (ADR-UX-07)
- [`04_PHUONG_AN_SUA_TOAN_BO.md`](./04_PHUONG_AN_SUA_TOAN_BO.md) — phương án tổng; nhóm «Chi tiết» = §10.2, đợt C
- [`06_CONFIRM_DIALOG_SSOT.md`](./06_CONFIRM_DIALOG_SSOT.md) — khuôn tài liệu + khuôn guard CHỈ-GIẢM (ADR-UX-18) mà văn bản này dùng lại nguyên vẹn

---

## §0. Phạm vi & Boundaries

### 0.1 Always (luôn áp dụng trong vòng này)

- **A1** — `DetailTabBar.vue` là **nơi duy nhất** vẽ thanh tab trong toàn FE. Màn nào cần tab thì **tiêu thụ**, không tự vẽ.
- **A2** — Mở rộng SSoT theo lối **CHỈ-THÊM**: prop mới `badge` tuỳ chọn; **0 dòng** hợp đồng cũ bị đổi; `DetailTabBar.test.ts` hiện có phải XANH mà **không sửa một ký tự nào**.
- **A3** — Di trú **giữ nguyên hành vi từng màn** (nạp lười · điều hướng theo route · giữ state form). Vòng này là **đổi khuôn hiển thị**, không phải đổi luồng.
- **A4** — Mọi nhãn hiển thị viết **đầy đủ tiếng Việt** (LL-FE-53).
- **A5** — Nợ còn lại phải **đo được và khoá được**: mỗi thanh tab tự chế chưa di trú nằm trong bản đồ CHỈ-GIẢM, không phải trong một câu văn.

### 0.2 Never (tuyệt đối không)

- **N1** — **KHÔNG tạo lại** một component thanh tab thứ hai (`TabBar`, `TabsNav`, `PageTabs`…). Đây là **mở rộng** `DetailTabBar.vue`, không phải viết mới. Có sẵn = dùng lại.
- **N2** — **KHÔNG** đổi/xoá/nới bất kỳ lời hứa cũ của `DetailTabBar`: `role="tablist"` · `role="tab"` · `aria-selected` hai chiều · `type="button"` · `data-testid="tab-<key>"` · `overflow-x-auto` ở container · `shrink-0 whitespace-nowrap` ở nút · **controlled** (chỉ emit, không tự giữ state).
- **N3** — **KHÔNG** biến `CommissioningDetailView` từ tab-theo-route thành tab-state-cục-bộ (mất deep-link + mất nút Back của trình duyệt).
- **N4** — **KHÔNG** đổi `v-show` → `v-if` ở `NeedsRequestDetailView` (mất chữ đã gõ ở tab «Chấm điểm ưu tiên»/«Dự toán»).
- **N5** — **KHÔNG** đổi `v-if` → `v-show` ở panel «Bản ghi liên quan» của `AssetDetailView` (mất nạp lười — hợp đồng AC-CR-87/96, khoá bởi `relatedRecordsTabParity.test.ts`).
- **N6** — **KHÔNG** sửa file `.py`. Vòng này **0 dòng backend** ⇒ **không phát sinh nhu cầu restart `gunicorn --preload`**.
- **N7** — **KHÔNG** nới 5 guard đang xanh (xem §8.6). Ngoại lệ **duy nhất, đã dự liệu**: một token trong miền giá trị cột «Vòng» — §8.6.

---

## §1. Baseline đo từ đĩa 2026-08-04 — **đè lên mọi số cũ**

> Luật đã ghi trong `06 §1`: số trong đề mục và trong tài liệu **luôn có thể stale**; đo lại trước khi code, chấm theo **DELTA**.

### 1.1 Ba con số đang lưu hành đều SAI — BA Self-Correction

| Con số đang lưu hành | Nguồn | Sự thật đo 2026-08-04 |
|---|---|---|
| «**27/32** màn chi tiết còn thanh tab tự chế» | `00 §6` dòng AC-UX-052 · `00 §7` (ADR-UX-07) · `00 §8` · `03 §1.2` (bảng nợ nền, dòng «Dùng `DetailTabBar` — 5») · `03 §10` · `04 §10.2` | **SAI về bản chất.** 27 = *số màn chi tiết không import `DetailTabBar`*, nhưng **24 trong số đó không có tab nào cả** — không có nợ để trả. Số màn chi tiết **thật sự có thanh tab** = **8/32**; đã dùng SSoT = **5**; còn tự chế = **3**. |
| «Còn **ĐÚNG 3** thanh tab tự chế» (đề mục vòng) | đề mục PM 2026-08-04 | **SAI vì quét thiếu.** Đúng 3 **trong `views/*DetailView.vue`**. Quét đủ `src/views/` + `src/components/` ⇒ **9 file / 12 nút-tab tự chế** (§1.3). |
| «Sổ AC-UX max = 063» | đề mục vòng | **SAI.** Đĩa = **AC-UX-066** (`00 §6` dòng cuối: «Tổng: 66 mục»). Số mới cấp từ **AC-UX-067**. |

Thêm một đính chính về **lệnh nghiệm thu** (§10 dùng bản đã sửa):

```bash
# SAI — dính 2 dòng trong internalAuditDetailStates.test.ts (chuỗi trong ASSERT, không phải markup)
grep -rn 'role="tablist"' frontend/src/views/            # ⇒ 3 hit hôm nay, 2 hit sau vòng ⇒ KHÔNG BAO GIỜ về 0
# ĐÚNG — chỉ chấm markup
grep -rn 'role="tablist"' frontend/src/views/ --include=*.vue   # ⇒ 1 hit hôm nay → 0 hit sau vòng
```

### 1.2 Công thức đo «thanh tab tự chế» (bắt buộc dùng đúng công thức này)

Ba tín hiệu từng được cân nhắc và **bị loại**:

| Tín hiệu | Vì sao loại |
|---|---|
| `grep role="tablist"` | Bắt được **1/9** file — 8 thanh tab tự chế **không có** `role` nào (đó chính là lỗi a11y đang nói tới). Dò bằng triệu chứng vắng mặt là dò ngược. |
| `grep -L 'import DetailTabBar'` | Cho ra 27/32 — **đếm cả màn không có tab**. Đây là nguồn của con số sai đã sống 3 vòng. |
| `@click="tab = …"` | Bỏ sót `ReferenceDataView` (`@click="switchTab(t)"`), `AssetDetailView` (`@click="onTabChange(tab)"`) và **cả 3 nút** của `CommissioningDetailView` (`@click="router.push(…)"`). |

**Tín hiệu ĐƯỢC CHỌN** — *một `<button>` có ràng buộc `:class` đọc biến trạng thái tab*. Đây là dấu vân tay không thể thiếu của mọi thanh tab tự chế: nút phải tự tô đậm khi nó đang mở.

```js
const SELF_DRAWN_TAB_RE = /<button\b[^>]*?:class\s*=\s*"[^"]*\b(?:activeTab|tab)\s*===/g
```

- Quét **2 cây** `src/views` + `src/components` (thanh tab tự chế đã trốn được vào `components/` — §1.3).
- Đo trên nguồn **đã strip comment** (`src/test/stripComments.ts` — dùng chung với `bareConfirmBudget.test.ts`; chú thích mô tả thanh tab **không phải** thanh tab).
- Đơn vị đếm = **nút-tab khai báo trong nguồn**, không phải «bar». Một `v-for` = 1; ba nút viết tay = 3.

### 1.3 Bản đồ per-file — mẫu số chấm DELTA (đo 2026-08-04)

| # | File | Số nút-tab tự chế | `role="tablist"` | `role="tab"` | `aria-selected` | Kiểu tab | Lô |
|---|---|---|---|---|---|---|---|
| 1 | `views/asset/AssetDetailView.vue` | **1** (`v-for` 6 tab) | 1 | 1 | ✅ | state cục bộ + nạp lười | **1** |
| 2 | `views/commissioning/CommissioningDetailView.vue` | **3** (viết tay) | **0** | **0** | **0** | **theo route** | **1** |
| 3 | `views/needs/NeedsRequestDetailView.vue` | **1** (`v-for` 3 tab) | **0** | **0** | **0** | state cục bộ + `v-show` | **1** |
| 4 | `views/tech-specs/TechSpecDetailView.vue` | **1** (`v-for` 6 tab) | **0** | **0** | **0** | state cục bộ + `v-show` | 2 |
| 5 | `views/procurement/VendorEvalDetailView.vue` | **1** (`v-for` 3 tab) | **0** | **0** | **0** | state cục bộ + `v-show` | 2 |
| 6 | `views/inventory/UomConversionView.vue` | **1** (`v-for` 3 tab) | **0** | **0** | **0** | state cục bộ + `v-if` | 2 |
| 7 | `views/master-data/ReferenceDataView.vue` | **1** (`v-for` 3 tab) | **0** | **0** | **0** | state cục bộ + `v-if` | 2 |
| 8 | `components/commissioning/CommissioningForm.vue` | **1** (`v-for`) | **0** | **0** | **0** | state cục bộ + `v-show` | 2 |
| 9 | `components/commissioning/AssetDashboard.vue` | **2** (viết tay) | **0** | **0** | **0** | state cục bộ + `v-if` | 2 |

**Tổng đầu vòng: 9 file / 12 nút-tab tự chế. Lô 1 đóng 3 file / 5 nút ⇒ mục tiêu cuối vòng: 6 file / 7 nút.**

### 1.4 Phía ĐÃ dùng SSoT (không đụng — chỉ để biết mẫu số)

| File | Cách dùng |
|---|---|
| `views/calibration/CalibrationDetailView.vue:15` | `import DetailTabBar` trực tiếp |
| `views/cm/CMWorkOrderDetailView.vue:14` | `import DetailTabBar` trực tiếp |
| `views/incident/IncidentDetailView.vue:12` | `import DetailTabBar` trực tiếp |
| `views/pm/PMWorkOrderDetailView.vue:7` | `import DetailTabBar` trực tiếp |
| `views/compliance/InternalAuditDetailView.vue:208` | **gián tiếp** qua `DetailPageShell v-model:active-tab` — **ĐÃ ĐẠT, KHÔNG ĐỤNG** |

⇒ `grep -rln 'import DetailTabBar' frontend/src/views/ | wc -l` : **4 → 7** sau vòng (Internal Audit vẫn không import trực tiếp — **đúng thiết kế**, đừng «sửa» cho thành 8).

### 1.5 Nhãn trạng thái Soát xét lãnh đạo (AC-UX-003)

| Nguồn | Nội dung | Đo |
|---|---|---|
| Ground truth BE | `assetcore/hooks.py:97` + `assetcore/tests/test_imm16.py:2643` `_MR_VALID_STATES` | 4 state: `Draft` · `Held` · `Minutes Approved` · `Closed` |
| Nhãn VI đang có | `views/compliance/ManagementReviewListView.vue:42-47` `MR_STATUSES` | `Bản nháp` · `Đã họp` · `Biên bản đã duyệt` · `Đã đóng` — **chỉ dùng cho bộ lọc** |
| SSoT nhãn badge | `utils/formatters.ts:43` `STATUS_MAP` | có `Draft`/`Closed`; **thiếu** `Held` và `Minutes Approved` |
| Hệ quả | `ManagementReviewDetailView.vue:258` `<StatusBadge :state="mr.status" />` → `translateStatus()` → `STATUS_MAP[s] ?? s.replaceAll('_',' ')` | badge in **nguyên tiếng Anh** «Held» / «Minutes Approved» — vi phạm LL-FE-53 |

Kiểm va chạm tên enum (LL-BE-58 — *enum trùng tên ≠ trùng domain*): `grep -rn '"Held"' assetcore/` chỉ trả về ngữ cảnh Management Review (`hooks.py` · `fixtures/workflow.json` · `tests/test_imm16.py`). **Không có domain thứ hai dùng `Held`** ⇒ thêm vào `STATUS_MAP` toàn cục là an toàn.

---

## §2. Kiến trúc SSoT — 3 tầng, mỗi tầng đúng một việc

```
tầng 3 · MÀN         AssetDetail · CommissioningDetail · NeedsRequestDetail · 4 màn workflow
                     └─ khai TABS (key + nhãn VI + badge) và GIỮ state/route; quyết định panel nào mount
tầng 2 · KHUÔN       DetailPageShell.vue  (tuỳ chọn — nhận tabs/activeTab dạng prop, ADR-UX-07)
                     └─ chuyển tiếp xuống tầng 1, KHÔNG tự vẽ
tầng 1 · SSoT        DetailTabBar.vue     ← nơi DUY NHẤT có markup thanh tab
                     └─ a11y (role/aria-selected/type=button/focus ring) + cuộn ngang mobile + badge
```

Luật phân tầng:

- **Tầng 1 thuần hiển thị & controlled** — không giữ state, không biết route, không gọi API. Bấm ⇒ `emit('update:modelValue', key)`.
- **Tầng 3 là nguồn sự thật duy nhất của tab đang mở** — nhờ đó nạp lười (`AssetDetailView`) và điều hướng route (`CommissioningDetailView`) đều nằm ở nơi hiểu ngữ cảnh.
- **Không có tầng 4** — cấm màn tự vẽ lại nút tab «cho hợp phong cách». Phong cách sửa ở tầng 1, 9 màn hưởng.

---

## §3. Delta CHỈ-THÊM trên `DetailTabBar.vue` — **AC-UX-067**

### 3.1 Bất biến — hợp đồng cũ giữ nguyên 100%

Không được đổi, dù chỉ thứ tự thuộc tính:

```
<div role="tablist" class="… overflow-x-auto">
  <button type="button" role="tab" :aria-selected="…'true'|'false'" :data-testid="`tab-${key}`"
          class="shrink-0 whitespace-nowrap … focus-visible:ring-2 focus-visible:ring-blue-500">
```

`DetailTabBar.test.ts` (TC-CONNTAB-01..03) phải xanh **mà không sửa một ký tự nào**. Nếu phải sửa file test đó ⇒ delta đã **không còn** là CHỈ-THÊM ⇒ **dừng, báo BA**.

### 3.2 Delta duy nhất — trường `badge` tuỳ chọn

```ts
export interface DetailTab {
  /** Khoá tab — cũng là `data-testid` (`tab-<key>`). */
  key: string
  /** Nhãn hiển thị — LUÔN tiếng Việt đầy đủ (LL-FE-53). */
  label: string
  /**
   * Số/chữ đếm phụ hiện ngay trong nút tab (vd số phiếu không phù hợp còn mở).
   * KHÔNG render khi: undefined · null · '' · 0 · '0'  (khớp `v-if="store.openNcCount > 0"`).
   */
  badge?: string | number
}
```

### 3.3 Luật render badge (5 điều, khoá bằng test)

| # | Luật | Vì sao |
|---|---|---|
| B1 | Badge nằm **BÊN TRONG** `<button role="tab">` | Ngoài nút ⇒ vòng focus và vùng bấm lệch nhau; trình đọc màn hình đọc rời con số khỏi nhãn. |
| B2 | Badge **không** là `<button>`/`<a>`/không `tabindex` — chỉ `<span>` | Thêm một tab-stop giữa dải tab là hồi quy bàn phím. |
| B3 | Badge **không** đổi lớp `shrink-0 whitespace-nowrap` của nút, **không** phá `focus-visible:ring-2` | Hợp đồng cuộn ngang mobile (TC-RWD-07) và vòng focus giữ nguyên. |
| B4 | Rỗng ⇒ **không có phần tử badge trong DOM** (không phải `display:none`) | Test đếm phần tử; và trình đọc màn hình không đọc «0» vô nghĩa. |
| B5 | `data-testid="tab-badge-<key>"` | Test bấm/đọc badge đúng tab, không dò theo thứ tự. |

Tên có thể đọc được của nút sau khi thêm badge = `"<label> <badge>"` (vd «Không phù hợp 3») — **cố ý không `aria-hidden`**: con số là thông tin, không phải trang trí.

### 3.4 Ca kiểm thử bắt buộc (thêm vào cuối `DetailTabBar.test.ts`, **không sửa 3 describe cũ**)

| Mã | Nội dung |
|---|---|
| TC-CONNTAB-05 | `badge: 3` ⇒ có `[data-testid="tab-badge-nc"]`, text `'3'`, và phần tử đó **nằm trong** `[data-testid="tab-nc"]` |
| TC-CONNTAB-06 | `badge: 0` · `badge: '0'` · `badge: ''` · `badge: undefined` · thiếu hẳn trường ⇒ **0** phần tử badge (5 ca) |
| TC-CONNTAB-07 | Có badge ⇒ số `[role="tab"]` **không đổi**, mọi nút vẫn `type="button"`, `aria-selected` vẫn đúng 2 chiều |
| TC-CONNTAB-08 | Có badge ⇒ nút vẫn giữ `shrink-0` + `whitespace-nowrap`, container vẫn `overflow-x-auto` |
| TC-CONNTAB-09 | Trong nút tab **không có** phần tử `button`/`a`/`[tabindex]` lồng nhau (B2) |

---

## §4. Di trú lô 1 — 3 màn — **AC-UX-068**

### 4.0 Khuôn thay thế chung

```vue
<!-- script -->
import DetailTabBar, { type DetailTab } from '@/components/common/DetailTabBar.vue'
const TABS = computed<DetailTab[]>(() => [ … ])

<!-- template -->
<DetailTabBar :tabs="TABS" :model-value="activeTab" @update:model-value="onTabSelect" />
```

Dùng dạng `:model-value` + `@update:model-value` **tường minh** (không `v-model`) ở màn có tác dụng phụ khi đổi tab — để chỉ có **một** nơi ghi state và tác dụng phụ.

### 4.1 `views/asset/AssetDetailView.vue` — 6 tab, nạp lười

**Xoá**: khối `:698-712` (`<div role="tablist">` + `v-for` 6 nút).
**Thêm**: `<DetailTabBar :tabs="ASSET_TABS" :model-value="activeTab" @update:model-value="onTabChange" />` đúng chỗ cũ.

Khai tab (thay literal inline — đồng thời sửa **lỗi hoa/thường** ở nhãn `kpi`):

```ts
const ASSET_TAB_KEYS = ['info','depreciation','timeline','kpi','audit','related'] as const
type AssetTabKey = (typeof ASSET_TAB_KEYS)[number]
const ASSET_TAB_LABEL: Record<AssetTabKey, string> = {
  info: 'Thông tin', depreciation: 'Khấu hao', timeline: 'Lịch sử',
  kpi: 'Chỉ số hiệu suất',            // ⚠️ đĩa đang là 'chỉ số hiệu suất' (thường) — sửa về hoa đầu câu
  audit: 'Nhật ký truy vết', related: 'Bản ghi liên quan',
}
const ASSET_TABS: DetailTab[] = ASSET_TAB_KEYS.map((k) => ({ key: k, label: ASSET_TAB_LABEL[k] }))
function isAssetTabKey(v: string): v is AssetTabKey {
  return (ASSET_TAB_KEYS as readonly string[]).includes(v)
}
```

`onTabChange` đổi chữ ký sang `(tab: string)` + chặn đầu bằng `isAssetTabKey` — **KHÔNG dùng `as AssetTabKey`** (cast mù là nợ đã ghi sổ AC-CR-101).

**Bất biến KHÔNG ĐƯỢC VỠ:**

| # | Bất biến | Khoá bởi |
|---|---|---|
| A-1 | `activeTab` giữ **nguyên tên** và vẫn là `ref` | `relatedRecordsTabParity.test.ts` (d) assert `v-if="activeTab === 'related'"` |
| A-2 | Panel liên quan giữ `v-if` + `data-testid="tab-panel-related"` (`:1045`) | `relatedRecordsTabParity` (b)(c)(d) · `assetDetailRelatedTab.test.ts` |
| A-3 | `onTabChange` chạy **đúng 1 lần / 1 lần bấm**, giữ nguyên 3 nhánh nạp lười (`timeline`/`kpi`/`audit`) | `assetTimelineTotalLoadMore.test.ts:89,206,215` |
| A-4 | 6 testid `tab-info … tab-related` giữ nguyên chuỗi | `assetDetailRelatedTab.test.ts:128-161` |
| A-5 | Nhãn «Bản ghi liên quan» và «Nhật ký truy vết» còn nguyên trong nguồn | `assetDetailTabBarResponsive.test.ts` |
| A-6 | Không thêm `v-model` song song với `@update:model-value` | tránh ghi state 2 lần |

### 4.2 `views/commissioning/CommissioningDetailView.vue` — 3 tab, **theo route**, có badge

**Xoá**: khối `:437-467` (3 nút viết tay + 3 `<span>` gạch chân `absolute inset-x-0 bottom-0 h-0.5`).
**Thêm**:

```ts
const COMMISSIONING_TABS = computed<DetailTab[]>(() => [
  { key: 'detail',   label: 'Chi tiết phiếu' },
  { key: 'nc',       label: 'Không phù hợp', badge: store.openNcCount },  // 0 ⇒ không render (B4)
  { key: 'timeline', label: 'Lịch sử' },
])
const TAB_ROUTE: Record<string, string> = {
  detail:   `/commissioning/${props.id}`,
  nc:       `/commissioning/${props.id}/nc`,
  timeline: `/commissioning/${props.id}/timeline`,
}
function onTabSelect(key: string): void {
  const to = TAB_ROUTE[key]
  if (to) void router.push(to)
}
```

**Bất biến KHÔNG ĐƯỢC VỠ:**

| # | Bất biến |
|---|---|
| C-1 | `activeTab` **vẫn là `computed` đọc `route.name`** (`:93-97`) — **cấm** đổi sang `ref` (N3) |
| C-2 | Bấm tab vẫn `router.push` đúng 3 đường; deep-link và nút Back của trình duyệt còn nguyên |
| C-3 | Badge «Không phù hợp» hiện **iff** `store.openNcCount > 0` — hành vi y hệt `v-if` cũ |
| C-4 | Không sinh state tab cục bộ nào; không `watch` đồng bộ hai chiều |
| C-5 | Sau di trú, nguồn **không còn** chuỗi `absolute inset-x-0 bottom-0 h-0.5` (dấu vân tay của bản fork) |

**Delta thị giác được chấp nhận** (ADR-UX-20): gạch chân đổi từ `bg-brand-600` (span tự vẽ) sang `border-b-2 border-blue-600` của SSoT; chữ tab đang mở đổi `text-brand-600` → `text-blue-600`. Đây là **giá của việc có một khuôn duy nhất**; thống nhất tông màu là việc của token màu (AC-UX-032/040), **không** giải quyết bằng cách giữ fork.

### 4.3 `views/needs/NeedsRequestDetailView.vue` — 3 tab, giữ `v-show`

**Xoá**: khối `:415-429` (`<div class="border-b"><nav>` + `v-for`).
**Sửa khai báo**: `TABS` đang là `{ id, label, badge?: () => string }[]` — trường `badge` **hàm** này **chưa từng được render** (mã chết). Chuyển sang `DetailTab[]`:

```ts
const NEEDS_TABS: DetailTab[] = [
  { key: 'overview', label: 'Tổng quan' },
  { key: 'scoring',  label: 'Chấm điểm ưu tiên' },
  { key: 'budget',   label: 'Dự toán' },
]
```

`id` → `key`, bỏ `badge` hàm (không thay bằng `badge` mới — màn này không có số đếm nào để hiện). Vì `activeTab` ở đây **không có tác dụng phụ**, dùng `v-model="activeTab"` là hợp lệ.

**Bất biến KHÔNG ĐƯỢC VỠ:**

| # | Bất biến |
|---|---|
| N-1 | 3 panel giữ **`v-show`** (N4) — gõ dở ở «Chấm điểm ưu tiên»/«Dự toán» không được mất khi đổi tab |
| N-2 | `type TabId` + `activeTab` giữ nguyên tên/kiểu |
| N-3 | 3 nhãn VI giữ **nguyên văn**: «Tổng quan» · «Chấm điểm ưu tiên» · «Dự toán» |
| N-4 | Lớp `border-neutral-*` biến mất theo khối cũ — **không** kéo sang khuôn mới (liên quan bẫy deep-merge `colors.neutral`, AC-UX-040) |

### 4.4 Ca kiểm thử render bắt buộc cho lô 1

Mỗi màn ≥1 file test mount thật (khuôn `*DetailStates.test.ts` của `03 §12`):

| Mã | Màn | Nội dung |
|---|---|---|
| TC-UXTAB-01 | Asset | 6 `[role="tab"]`, nhãn đúng thứ tự; bấm «Lịch sử» ⇒ `onTabChange` gọi **1** lần, `[data-testid="tab-panel-related"]` **chưa** mount |
| TC-UXTAB-02 | Asset | bấm «Bản ghi liên quan» ⇒ panel mount, `aria-selected` của `tab-related`=`true` **và** `tab-info`=`false` |
| TC-UXTAB-03 | Commissioning | 3 `[role="tab"]`; bấm «Lịch sử» ⇒ `router.push` gọi với `/commissioning/<id>/timeline`, **0** state cục bộ đổi |
| TC-UXTAB-04 | Commissioning | `openNcCount = 3` ⇒ có `[data-testid="tab-badge-nc"]` = «3»; `openNcCount = 0` ⇒ **0** phần tử badge |
| TC-UXTAB-05 | Needs | đổi sang «Dự toán» rồi quay lại «Chấm điểm ưu tiên» ⇒ giá trị đã gõ **còn nguyên** (chứng minh `v-show`) |
| TC-UXTAB-06 | cả 3 | mỗi màn **đúng 1** `[role="tablist"]` và **0** `<button>` tab ngoài `DetailTabBar` |

---

## §5. Test cũ phải viết lại — **relocation, KHÔNG phải nới lỏng**

`frontend/src/views/asset/assetDetailTabBarResponsive.test.ts` (TC-RWD-07) là test **mức nguồn**: nó tìm chuỗi `'info', 'depreciation', 'timeline', 'kpi', 'audit', 'related'` rồi soi `<div>` đứng trước có `overflow-x-auto`, và soi khối `v-for="tab in ([…]` có `shrink-0`/`whitespace-nowrap`. Sau di trú, **markup đó không còn nằm trong `AssetDetailView.vue`** ⇒ test đỏ.

Chú thích trong chính file đó viết: *«TUYỆT ĐỐI KHÔNG nới lỏng assert overflow-x-auto/shrink-0»*. Cách xử lý **tôn trọng** câu đó:

| Không được làm | Phải làm |
|---|---|
| Xoá file · xoá 2 assert cuộn ngang · đổi thành `expect(true)` | **Dời** lời hứa về nơi markup thật sự sống |

Lời hứa `overflow-x-auto` + `shrink-0` + `whitespace-nowrap` **đã có sẵn** ở `DetailTabBar.test.ts` (TC-CONNTAB-03) — nên không có lời hứa nào bị mất. `assetDetailTabBarResponsive.test.ts` được viết lại thành **test tiêu thụ**:

| Assert mới | Ý nghĩa |
|---|---|
| Nguồn có `import DetailTabBar` **và** thẻ `<DetailTabBar` xuất hiện **đúng 1 lần** | Màn đã uỷ quyền cho SSoT |
| Nguồn **0** match `SELF_DRAWN_TAB_RE` (§1.2) và **0** `role="tablist"` | Không còn bản fork |
| 6 khoá tab + 6 nhãn VI (gồm «Nhật ký truy vết», «Bản ghi liên quan») còn nguyên trong nguồn | Không mất tab nào khi đổi khuôn |
| Mount thật: container tab có `overflow-x-auto`, mỗi nút có `shrink-0` | Hợp đồng RWD vẫn được chấm **trên màn thật**, nay bằng render thay vì regex |

Đổi tên `describe` giữ tiền tố `TC-RWD-07` để lịch sử truy được.

**Test KHÔNG được đụng** (phải xanh nguyên trạng): `relatedRecordsTabParity.test.ts` · `assetDetailRelatedTab.test.ts` · `assetTimelineTotalLoadMore.test.ts` · `cmDetailRelatedTab.test.ts` · `DetailTabBar.test.ts` (3 describe cũ) · `internalAuditDetailStates.test.ts`.

---

## §6. Guard CHỈ-GIẢM mới — `frontend/src/views/detailTabBarAdoption.test.ts` — **AC-UX-069**

### 6.1 Vì sao cần

Nợ thanh tab đã sống 3 vòng dưới dạng **một câu văn sai** («27/32»). Câu văn không đỏ được. Và bản thân lỗi *«mọc thêm một thanh tab tự chế»* rất rẻ để tái phạm: 8 dòng `<button>` là xong. Guard theo khuôn `bareConfirmBudget.test.ts` (ADR-UX-18).

### 6.2 Hai phần — vì một phép đo không đủ

**Phần A — bản đồ ngân sách CHỈ-GIẢM** (đo bằng `SELF_DRAWN_TAB_RE`, quét `src/views` + `src/components`, strip comment):

```ts
const TAB_BUDGET: Readonly<Record<string, number>> = {
  // Lô 1 — 3 file đích, đóng băng ở 0
  'views/asset/AssetDetailView.vue': 0,
  'views/commissioning/CommissioningDetailView.vue': 0,
  'views/needs/NeedsRequestDetailView.vue': 0,
  // Lô 2 — nợ đóng băng theo phép đo 2026-08-04 (§1.3), CHỈ-GIẢM
  'views/tech-specs/TechSpecDetailView.vue': 1,
  'views/procurement/VendorEvalDetailView.vue': 1,
  'views/inventory/UomConversionView.vue': 1,
  'views/master-data/ReferenceDataView.vue': 1,
  'components/commissioning/CommissioningForm.vue': 1,
  'components/commissioning/AssetDashboard.vue': 2,
}
```

Bốn assert (khuôn ADR-UX-18, **hai chiều**):

| # | Assert | Chặn được |
|---|---|---|
| (a) | Tổng đo được ≤ tổng bản đồ (**7**) | vay thêm nợ |
| (b) | File **ngoài** bản đồ có match ⇒ ĐỎ | né guard bằng cách đẻ file mới / trốn vào `components/` |
| (c) | File vượt hạn mức **riêng** ⇒ ĐỎ | «trả chỗ dễ, vay chỗ khó» |
| (d) | File đo **thấp hơn** hạn mức mà bản đồ chưa hạ ⇒ ĐỎ | trả nợ rồi quên hạ sổ ⇒ nợ được vay lại âm thầm |

**Phần B — danh sách bắt buộc dùng SSoT** (phép đo A **mù** với fork điều hướng-bằng-route như `CommissioningDetailView` trước đây: nút của nó là `router.push`, `:class` mới là thứ tố cáo — nên A bắt được, nhưng một fork tương lai có thể tô đậm bằng cách khác):

```ts
const MUST_USE_SSOT = [
  'views/asset/AssetDetailView.vue',
  'views/commissioning/CommissioningDetailView.vue',
  'views/needs/NeedsRequestDetailView.vue',
  'views/calibration/CalibrationDetailView.vue',
  'views/cm/CMWorkOrderDetailView.vue',
  'views/incident/IncidentDetailView.vue',
  'views/pm/PMWorkOrderDetailView.vue',
] as const
const FORK_FINGERPRINT: Readonly<Record<string, readonly string[]>> = {
  'views/commissioning/CommissioningDetailView.vue': ['absolute inset-x-0 bottom-0 h-0.5'],
}
```

| # | Assert |
|---|---|
| (e) | Mỗi file trong `MUST_USE_SSOT` có `import DetailTabBar` **và đúng 1** thẻ `<DetailTabBar` |
| (f) | Mỗi dấu vân tay trong `FORK_FINGERPRINT` **vắng mặt** khỏi file tương ứng |
| (g) | `role="tablist"` trong `src/views/**/*.vue` + `src/components/**/*.vue` = **0** (SSoT là file duy nhất được có, và nó nằm ở `components/common/DetailTabBar.vue` — loại trừ tường minh **đúng 1** đường dẫn) |
| (h) | `InternalAuditDetailView.vue` **không** import `DetailTabBar` trực tiếp mà đi qua `DetailPageShell` — chống «sửa cho đủ 8» làm hỏng ADR-UX-07 |

### 6.3 Bất biến

- **INV-UXTAB-1** — tổng nút-tab tự chế **CHỈ-GIẢM**, không bao giờ tăng.
- **INV-UXTAB-2** — bản đồ và đĩa khớp **hai chiều** (giảm phải hạ sổ).
- **INV-UXTAB-3** — mọi màn có tab đều đi qua SSoT; markup `role="tablist"` tồn tại **đúng 1 nơi** trong repo.
- **INV-UXTAB-4** — hợp đồng cũ của `DetailTabBar` bất biến: `DetailTabBar.test.ts` 3 describe đầu **0 dòng đổi** (chấm bằng `git diff --stat`).

---

## §7. Nhãn trạng thái Soát xét lãnh đạo — **AC-UX-003 ĐÓNG**

### 7.1 Delta trên `frontend/src/utils/formatters.ts`

Thêm vào `STATUS_MAP` một khối có chú thích domain (khuôn y hệt khối `Pending Verification` / `RCA Required` đã có):

```ts
  // ── IMM-16 Management Review status (SSoT nhãn badge) ──────────────
  // BE ground truth: hooks.py:97 + tests/test_imm16.py `_MR_VALID_STATES`
  //   = Draft / Held / Minutes Approved / Closed  (Draft & Closed đã có ở khối chung).
  // Thiếu 2 khoá này ⇒ StatusBadge in nguyên tiếng Anh ở /compliance/mr (LL-FE-53).
  // Nhãn phải TRÙNG TUYỆT ĐỐI MR_STATUSES của ManagementReviewListView (parity test).
  Held:                'Đã họp',
  'Minutes Approved':  'Biên bản đã duyệt',
  Minutes_Approved:    'Biên bản đã duyệt',
```

Biến thể gạch dưới `Minutes_Approved` là bắt buộc — Frappe trả raw ở vài đường (khuôn đã có cho `Pending_Verification` / `RCA_Required`).

### 7.2 Màu badge — quyết định tường minh, không để rơi vào mặc định

`getStatusColor` tra `STATUS_COLOR` riêng; thiếu khoá ⇒ rơi về `COLOR_GRAY`. Vòng đời MR là **Bản nháp → Đã họp → Biên bản đã duyệt → Đã đóng**, nên gán:

| State | Màu | Lý do |
|---|---|---|
| `Held` / — | `COLOR_BLUE` | đang xử lý (cùng tông `In Progress`/`Reviewing`) |
| `Minutes Approved` + `Minutes_Approved` | `COLOR_GREEN` | mốc đã duyệt (cùng tông `Approved`) |
| `Draft` · `Closed` | giữ nguyên `COLOR_GRAY` | đã có |

### 7.3 Guard parity 2 nguồn (gộp vào `detailTabBarAdoption.test.ts` hoặc file riêng `mrStatusLabelParity.test.ts`)

| Mã | Assert |
|---|---|
| TC-UXMR-01 | `translateStatus('Held') === 'Đã họp'` · `translateStatus('Minutes Approved') === 'Biên bản đã duyệt'` · `translateStatus('Minutes_Approved') === 'Biên bản đã duyệt'` |
| TC-UXMR-02 | **Parity 2 nguồn**: với cả 4 state `Draft/Held/Minutes Approved/Closed`, nhãn trong `MR_STATUSES` (`ManagementReviewListView.vue`) **===** `translateStatus(value)` |
| TC-UXMR-03 | 4 state ⇒ `translateStatus(s) !== s` (không rò raw EN) và không chứa ký tự `_` |
| TC-UXMR-04 | `getStatusColor(s)` ≠ chuỗi rỗng cho cả 4 state; `Held`/`Minutes Approved` **khác** `COLOR_GRAY` (chứng minh đã gán màu chủ ý, không rơi mặc định) |

TC-UXMR-02 là ô chốt: nó biến «nhãn phải trùng» từ lời dặn thành **luật**, nên lần sau đổi chữ ở một nguồn sẽ đỏ ngay.

---

## §8. Bẫy đã biết — **ĐỌC TRƯỚC KHI CODE**

### 8.1 `assetDetailTabBarResponsive.test.ts` sẽ đỏ ngay khi xoá markup — **đã lường trước**
Đây không phải hồi quy. Xử lý theo §5 (dời lời hứa), **không** xoá assert.

### 8.2 `relatedRecordsTabParity.test.ts` (d) đọc **chuỗi nguồn** `v-if="activeTab === 'related'"`
Đổi tên biến `activeTab` (vd thành `tab`) ⇒ đỏ **5 màn** cùng lúc. Giữ nguyên tên.

### 8.3 `v-model` + `@update:model-value` cùng lúc
Ở `AssetDetailView`, `v-model` sẽ ghi `activeTab` **trước** rồi handler ghi lần nữa — nạp lười vẫn đúng nhưng state bị ghi 2 lần và khó lần vết. Dùng **một** dạng (`:model-value` + handler).

### 8.4 Badge `0` là **số**, không phải chuỗi rỗng
`v-if="tab.badge"` ĐÚNG cho `0` và `''`, nhưng **SAI** cho `'0'` (chuỗi `'0'` là truthy). Dùng đúng điều kiện ở §3.2.

### 8.5 `CommissioningDetailView` — `activeTab` là `computed`
Truyền `computed` vào prop `modelValue` là bình thường; nhưng **cấm** `v-model` (computed không có setter ⇒ cảnh báo Vue / ghi hụt). Bắt buộc `:model-value` + handler đẩy route.

### 8.6 5 guard đang xanh — giữ nguyên, **một ngoại lệ đã dự liệu**

Không đụng: `router/uiFixPlanParity.test.ts` · `components/common/modalOverlayHygiene.test.ts` · `components/ui/uiPrimitiveHygiene.test.ts` · `components/common/bareConfirmBudget.test.ts` · phần lớn `router/uiAuditDocParity.test.ts`.

**Ngoại lệ duy nhất — bắt buộc, 1 token:**

```
frontend/src/router/uiAuditDocParity.test.ts:35
- const ROUND_VALUES = new Set(['2', '3', '4', '5', '6', '7'])
+ const ROUND_VALUES = new Set(['2', '3', '4', '5', '6', '7', '8'])
```

Đây **không phải nới guard**: `ROUND_VALUES` là **miền giá trị hợp lệ của cột «Vòng»**, và chính chú thích trong file viết *«nới thêm mỗi khi factory mở vòng mới»* (vòng 7 đã thêm `'7'` cho AC-UX-064/065/066). Không thêm `'8'` thì **không thể ghi sổ mục mới nào** — guard sẽ chặn chính việc nó tồn tại để phục vụ. Mọi assert khác của file giữ **nguyên xi**; đặc biệt assert *«đánh số liên tục từ 001»* và *«Tổng: N mục»* vẫn siết đúng như cũ.

### 8.7 Đếm test file: `.spec.ts` cũng tính
`find frontend/src -name '*.test.ts'` = 346, nhưng vitest gom cả `*.spec.ts` (**1** file) ⇒ **347**. Đừng «sửa» chênh lệch 1 file này.

### 8.8 Không đụng `.py`
`git status --porcelain -- '*.py'` phải **RỖNG** cuối vòng ⇒ **không** phát sinh nhu cầu restart `gunicorn --preload`, **không** `bench migrate`.

---

## §9. Việc doc-layer của vòng (BA đã làm)

| # | File | Delta |
|---|---|---|
| 1 | `docs/ui-ux/07_DETAIL_TAB_BAR_SSOT.md` | **MỚI** — văn bản này |
| 2 | `docs/ui-ux/00_AUDIT_HIEN_TRANG.md` §6 | sửa dòng **AC-UX-052** (bỏ «27/32», thay bằng số đo thật + phạm vi lô) · đánh dấu **AC-UX-003 ĐÓNG** · thêm **AC-UX-067/068/069** · dòng tổng `66 → 69` |
| 3 | `docs/ui-ux/00_AUDIT_HIEN_TRANG.md` §7 (ADR-UX-07) + §8 | sửa 2 chỗ còn ghi «27/32 màn» |
| 4 | `docs/ui-ux/04_PHUONG_AN_SUA_TOAN_BO.md` §10.2 | cập nhật trạng thái nhóm tab (thứ tự ưu tiên + tiến độ đợt C) |

Bốn chỗ trong `03_DETAIL_PAGE_SHELL.md` còn ghi số cũ (`§1.2` bảng nợ nền dòng «Dùng `DetailTabBar` — 5» · `§10` mục `AC-UX-052` · `§12` hai ghi chú «lô 1 truyền `tabs=[]`») là **ảnh chụp lịch sử của vòng 4** — giữ nguyên theo luật light-touch; con số đúng nay sống ở `00 §6` + văn bản này, và được **guard** chấm.

---

## §10. DoD — nghiệm thu vòng (đo từ đĩa, KHÔNG đọc mô tả)

```bash
cd frontend

# 1) SSoT là nơi duy nhất vẽ thanh tab
grep -rn 'role="tablist"' src/views src/components --include=*.vue    # ⇒ ĐÚNG 1 hit: components/common/DetailTabBar.vue
grep -rln 'import DetailTabBar' src/views/ | wc -l                    # ⇒ 7   (đầu vòng 4)

# 2) 3 file đích sạch fork
grep -c '<button' src/views/asset/AssetDetailView.vue                 # tab-bar cũ biến mất (đối chiếu §1.3)
grep -n 'absolute inset-x-0 bottom-0 h-0.5' src/views/commissioning/CommissioningDetailView.vue   # ⇒ 0 hit
node -e "…SELF_DRAWN_TAB_RE…"                                         # ⇒ 3 file đích = 0 match

# 3) Nợ tab còn lại — bản đồ CHỈ-GIẢM
npx vitest run src/views/detailTabBarAdoption.test.ts                 # ⇒ tổng 12 → 7, file 9 → 6

# 4) Nhãn MR
npx vitest run src/utils/formatters.test.ts                           # TC-UXMR-01..04 xanh

# 5) Hợp đồng cũ bất biến
git diff --stat -- src/components/common/DetailTabBar.test.ts         # 3 describe cũ: 0 dòng đổi (chỉ +TC-CONNTAB-05..09)

# 6) Suite + kiểu
npx vitest run                                                        # ⇒ ≥ 347 file / ≥ 3451 test, 0 ĐỎ, delta ≥ +4 file test
npx vue-tsc --noEmit                                                  # ⇒ 0 lỗi mới

# 7) Sổ số hiệu + backend + rác
grep -rhoE "AC-UX-[0-9]{3}" ../docs/ | sort -u | tail -1              # ⇒ AC-UX-069
grep -n "Tổng: 69 mục" ../docs/ui-ux/00_AUDIT_HIEN_TRANG.md           # ⇒ 1 hit
cd .. && git status --porcelain -- '*.py'                             # ⇒ RỖNG
bash .claude/scripts/tidy-eval-artifacts.sh                           # repo root 0 file scratch
```

**Ảnh render thật** (`.playwright/eval/`): `/assets/<id>` (6 tab + bấm «Lịch sử») · `/commissioning/<id>` (badge «Không phù hợp» > 0) · `/needs/<id>` · `/compliance/mr` + `/compliance/mr/<id>` (badge tiếng Việt, **0** chữ EN).

---

## §11. Quyết định kiến trúc

### ADR-UX-19: Thanh tab mở rộng bằng **trường tuỳ chọn trên `DetailTab`**, không bằng slot

- **Status**: Accepted — 2026-08-04
- **Context**: `CommissioningDetailView` cần một số đếm («Không phù hợp» × N) ngay trong nút tab. Ba đường: (1) slot `#tab-<key>` cho màn tự vẽ phần phụ; (2) prop mảng `badges` song song `tabs`; (3) trường `badge` trên chính `DetailTab`.
- **Decision**: chọn (3).
- **Alternatives**:
  - (1) **slot** — mở lại đúng cái cửa vừa đóng: màn lại tự vẽ nội dung trong nút ⇒ 9 màn 9 kiểu badge, và slot dễ bị nhét `<button>` vào (vỡ B2).
  - (2) **mảng song song** — hai nguồn phải khớp thứ tự; lệch một phần tử là badge dán nhầm tab, không test nào bắt được rẻ.
- **Consequences**: hợp đồng cũ **0 thay đổi** (trường tuỳ chọn); mọi màn tương lai muốn badge chỉ thêm 1 khoá dữ liệu; đổi lại, badge chỉ có thể là số/chuỗi ngắn — muốn chấm than/biểu tượng phải mở ADR mới, không lén thêm HTML.

### ADR-UX-20: Di trú thanh tab **chấp nhận delta thị giác**, không giữ fork vì màu

- **Status**: Accepted — 2026-08-04
- **Context**: `CommissioningDetailView` dùng `text-brand-600` + gạch chân `<span>` tự vẽ; SSoT dùng `text-blue-600` + `border-b-2`. Giữ nguyên hình thức cũ đồng nghĩa giữ fork.
- **Decision**: di trú, chấp nhận đổi tông; thống nhất màu là việc của lớp token (AC-UX-032/040) và sẽ chạm **một** file.
- **Alternatives**: thêm prop `variant="brand"` — đẻ nhánh phong cách ngay lúc vừa hợp nhất, đúng con đường đã sinh ra 9 bản fork.
- **Consequences**: một khác biệt màu tạm thời ở màn nghiệm thu; đổi lại mọi thay đổi phong cách tab về sau chỉ sửa 1 nơi.

### ADR-UX-21: Nợ thanh tab đo bằng **cặp (file, số nút-tab)**, quét cả `components/`

- **Status**: Accepted — 2026-08-04 (áp dụng lại ADR-UX-18)
- **Context**: Con số «27/32» sai vì đo bằng *vắng mặt của một import*; và 3 thanh tab tự chế đã **trốn được vào `src/components/`** nơi mọi bộ dò trước chỉ quét `src/views/`.
- **Decision**: đo bằng dấu vân tay **tích cực** (`<button>` có `:class` đọc biến tab), quét `views` + `components`, đóng băng theo cặp (file, số), CHỈ-GIẢM **hai chiều**; kèm danh sách «bắt buộc dùng SSoT» + dấu vân tay fork cho ca mà phép đo mù.
- **Alternatives**: một con số tổng (cho phép vay chỗ khó) · allowlist theo tên file (mù với hồi quy **bên trong** file đã có tên).
- **Consequences**: thêm 1 file guard; mọi vòng sau muốn thêm thanh tab tự chế phải **sửa mã**, không sửa được bản đồ để đi tiếp.

---

## §12. Nợ để lại — **KHÔNG thuộc vòng này**

| Mã | Nội dung | Ghi chú |
|---|---|---|
| **AC-UX-069 lô 2** | 6 file / 7 nút-tab tự chế còn lại: `TechSpecDetailView` · `VendorEvalDetailView` · `UomConversionView` · `ReferenceDataView` · `CommissioningForm` · `AssetDashboard` | đã đóng băng trong `TAB_BUDGET`; lô 2 mở ở vòng sau, mỗi file kèm test render |
| — | 2 file dùng lớp CSS `.tab`/`.tabs` (`TechSpecDetailView`, `VendorEvalDetailView`) — lớp này **không** khai trong `main.css` đã quét | cần khảo sát nguồn lớp trước khi di trú *(Cần khảo sát)* |
| — | Thống nhất tông màu tab `brand` ⇄ `blue` | thuộc AC-UX-032/040 (token màu), không giải bằng prop `variant` |
| — | `AssetDashboard.vue` 2 nút-tab viết tay trong `components/` | ứng viên tốt cho `DetailTabBar` nhưng nằm ngoài màn chi tiết ⇒ cần chốt phạm vi SSoT có phủ component nhúng không |
