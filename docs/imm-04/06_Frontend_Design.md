# 06 — Thiết kế Frontend (Frontend Design / UI-UX Guide)

| Mục | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phạm vi | Per-module |
| Owner | FE Lead + Designer |
| Module accent | `violet-600` (installation / commissioning) |

---

## 1. Sitemap / Route map

> Source of truth: `frontend/src/router/index.ts` (Section 3 — IMM-04 Commissioning)

| Route | Route name | Component thực tế | Mô tả |
|---|---|---|---|
| `/commissioning` | `CommissioningList` | `views/commissioning/CommissioningListView.vue` | Danh sách phiếu nghiệm thu |
| `/commissioning/new` | `CommissioningCreate` | `views/commissioning/CommissioningCreateView.vue` | Tạo phiếu mới |
| `/commissioning/:id` | `CommissioningDetail` | `views/commissioning/CommissioningDetailView.vue` | Chi tiết phiếu |
| `/commissioning/:id/nc` | `CommissioningNC` | `views/commissioning/CommissioningNCView.vue` | Quản lý Non Conformance |
| `/commissioning/:id/timeline` | `CommissioningTimeline` | `views/commissioning/CommissioningTimelineView.vue` | Lịch sử vòng đời |

**Không có:** route riêng cho dashboard (`/imm-04/dashboard`), checklist, handover, hay documents tab — các chức năng này được tích hợp vào `CommissioningDetailView` hoặc chưa implement route riêng.

> **Quyết định implement (2026-05-29):** KPI dashboard KHÔNG tách route riêng `/imm-04/dashboard`. 5 KPI (`get_dashboard_stats`) được render trực tiếp dưới dạng **KPI strip trên đầu list page `/commissioning`** (`CommissioningListView`), tái dùng `WorkOrderKpiStrip` + `KpiCard` — đồng pattern với IMM-08/09. Mỗi KPI clickable → quick-filter danh sách ngay tại chỗ. Chi tiết KPI→API field + click action xem §3.1.

---

## 2. Sidebar nav module

```ts
"imm-04": {
  title: "IMM-04 · Lắp đặt & Nghiệm thu",
  accent: "violet-600",
  items: [
    { icon: "chart-bar",     label: "Tổng quan",           to: "/imm-04/dashboard" },
    { icon: "clipboard-list",label: "Danh sách phiếu",     to: "/imm-04" },
    { icon: "plus-circle",   label: "Tạo phiếu mới",       to: "/imm-04/new" },
    { icon: "clock",         label: "Phiếu quá hạn SLA",   to: "/imm-04?filter=overdue" },
    { icon: "shield-exclaim",label: "Clinical Hold",        to: "/imm-04?filter=clinical_hold" },
  ],
}
```

---

## 3. Thiết kế giao diện

### 3.a. UI Mockup (pre-build)

**Mockup 1 — Dashboard (`/imm-04/dashboard`):**
```
┌──────────────────────────────────────────────────────────────────────┐
│ IMM-04 — Lắp đặt & Nghiệm thu Thiết bị              [+ Tạo phiếu]  │
│ ──────────────────────────────────────────────────────────────────── │
│ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌─────────┐│
│ │ Đang mở   │ │ Clinical  │ │ NC mở     │ │ Release   │ │ Quá hạn ││
│ │   12      │ │ Hold  2   │ │  3        │ │ tháng này │ │   1     ││
│ │           │ │           │ │           │ │    8      │ │         ││
│ └───────────┘ └───────────┘ └───────────┘ └───────────┘ └─────────┘│
│                                                                       │
│ ┌─── Theo trạng thái ───┐  ┌─── 5 phiếu gần đây ─────────────────┐ │
│ │ Identification:  5    │  │ ACC-26-04-001 Identification 18/04   │ │
│ │ Initial Insp:    4    │  │ ACC-26-04-002 Clinical Hold  17/04   │ │
│ │ Clinical Hold:   2    │  │ ...                                   │ │
│ │ Non Conformance: 1    │  └───────────────────────────────────────┘ │
│ └───────────────────────┘                                             │
└──────────────────────────────────────────────────────────────────────┘
```

**Mockup 2 — List view (`/imm-04`):**
```
┌──────────────────────────────────────────────────────────────────────┐
│ Danh sách Phiếu Nghiệm thu                       [+ Tạo phiếu mới] │
│ ──────────────────────────────────────────────────────────────────── │
│ [Trạng thái ▼]  [Thiết bị ▼]  [Nhà cung cấp ▼]  [🔍 Tìm kiếm...]  │
│                                                                       │
│ ┌──────────────┬──────────────┬──────────────┬──────────────────────┐│
│ │ Mã phiếu    │ Thiết bị     │ Trạng thái   │ Ngày nhận / SLA      ││
│ ├──────────────┼──────────────┼──────────────┼──────────────────────┤│
│ │ ACC-26-04-001│ Máy X-Ray   │ 🟣 Nhận diện │ 18/04 — còn 12 ngày ││
│ │ ACC-26-04-002│ Monitor ICU │ 🔴 Tạm giữ LS│ 17/04 — ⚠️ 33 ngày  ││
│ └──────────────┴──────────────┴──────────────┴──────────────────────┘│
│  ◀ 1 2 3 ▶   Hiển thị 1-20/47                                         │
└──────────────────────────────────────────────────────────────────────┘
```

**Mockup 3 — Detail view (`/imm-04/:id`):**
```
┌──────────────────────────────────────────────────────────────────────┐
│ ← Quay lại      ACC-26-04-00001 — Máy X-Ray Philips                 │
│                                   [🟣 Đang nhận diện]  [Nút action]  │
│ ──────────────────────────────────────────────────────────────────── │
│  [Thông tin] [Hồ sơ (3)] [Đo kiểm] [NC (1)] [Lịch sử] [Bàn giao]   │
│                                                                       │
│  Số phiếu:  ACC-26-04-00001    PO:         PO-2026-00023             │
│  Thiết bị:  Máy X-Ray Philips  Nhà CC:     Philips Healthcare VN     │
│  Khoa:      Khoa CĐHA          Rủi ro:     ● C [Nguy cơ cao]        │
│  Ngày nhận: 18/04/2026         SN NCC:     PHI-SN98765               │
│  Mã nội bộ: BV-CDHA-2026-0001  [In mã QR]                            │
│                                                                       │
│  ⚠️ Thiết bị phân loại C — yêu cầu QA sign-off trước Clinical Release│
└──────────────────────────────────────────────────────────────────────┘
```

**Mockup 4 — Form tạo phiếu mới (`/imm-04/new`):**
```
┌──────────────────────────────────────────────────────────────────────┐
│ Tạo Phiếu Nghiệm thu Mới                         [Hủy] [Lưu Draft] │
│ ──────────────────────────────────────────────────────────────────── │
│ Đơn Mua Hàng*: [🔍 Tìm PO...        ▼]                              │
│   → Sau khi chọn PO, tự động điền: Thiết bị, Nhà cung cấp          │
│                                                                       │
│ Thiết bị*:     [Auto-fill từ PO    ▼]  Phân loại rủi ro: [C ●]     │
│ Nhà cung cấp*: [Auto-fill từ PO    ▼]  Thiết bị bức xạ:  ☑         │
│ Khoa lắp đặt*: [🔍 Khoa CĐHA       ▼]                               │
│ Ngày lắp (dự kiến)*: [📅 20/04/2026  ]                               │
│                                                                       │
│  ⚠️ Thiết bị phân loại C/D/Radiation cần có Giấy phép trước Release  │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.b. UI Screenshot (post-build)

Lưu ảnh tại `docs/imm-04/screenshots/`:
- `01_dashboard.png` — Dashboard KPI
- `02_list.png` — Danh sách phiếu
- `03_detail_identification.png` — Chi tiết state Identification
- `04_checklist.png` — Trang đo kiểm baseline
- `05_clinical_hold_alert.png` — Alert Clinical Hold

### 3.c. Trang chi tiết theo archetype

#### 3.1. KPI strip (trên đầu list page `/commissioning`)

> Bám `docs/res/design/design-frontend.md §3.1` và `docs/fe/04-commissioning/commissioning-list.html`. Render qua `WorkOrderKpiStrip` + `KpiCard` (pattern IMM-08/09), KHÔNG route riêng.

**KPI cards (display summary — đồng pattern IMM-08/09; thẻ clickable → quick-filter list):**
| KPI (nhãn hiển thị VI) | API field | Màu | Click → filter |
|---|---|---|---|
| Phiếu đang mở | `kpis.pending_count` | primary | clear (`filterState=''`) |
| Tạm giữ lâm sàng | `kpis.hold_count` | warning | `filterState='Clinical Hold'` — hiển thị qua i18n (§ bảng map), KHÔNG để raw English |
| NC mở | `kpis.open_nc_count` | danger | `filterState='Non Conformance'` |
| Bàn giao tháng này | `kpis.released_this_month` | success | `filterState='Clinical Release'` — hiển thị tiếng Việt theo § i18n |
<!-- BR-04-11: card count đếm theo commissioning_date ∈ tháng (BE đổi anchor modified→commissioning_date). FE ZERO shape-change — xem ghi chú "Vòng 16" dưới đây. -->

| **Quá hạn SLA** | `kpis.overdue_sla` | **warning** | **`overdue:1`** (virtual filter — BR-04-10), KHÔNG còn display-only |

> **Đính chính i18n (2026-06-02, factory vòng 9):** nhãn KPI strip PHẢI tiếng Việt theo quy tắc i18n ở § "State value tiếng Anh map qua i18n → tiếng Việt trên UI" và wireframe ("Tạm giữ LS"). Bản trước để raw `Clinical Hold` / `Release tháng này` là rò rỉ tiếng Anh, mâu thuẫn chính bảng i18n của module → đã thống nhất về VI. `filterState` vẫn dùng workflow_state gốc tiếng Anh (`Clinical Hold` / `Clinical Release`) làm khoá lọc.

> **Vòng 32 — "Quá hạn SLA" click-to-drill (đóng backlog cũ):** thẻ chuyển từ display-only (color neutral) sang **clickable** mang `overdue:1`:
> - Nhãn GIỮ tiếng Việt `'Quá hạn SLA'` (KHÔNG leak raw EN). Màu đổi `neutral → warning` để báo hiệu actionable.
> - `commissioningKpiItems()` (`commissioningKpi.ts`) thêm cho thẻ này một marker drill `overdue: true` (KHÔNG dùng `filterState` vì đây là virtual filter, không phải workflow_state). Các thẻ khác giữ nguyên `filterState` như cũ.
> - `WorkOrderKpiStrip`/`KpiCard` cần affordance click (emit/`@click`) — hiện display-only. FE dev: thêm optional click contract **không phá** call-site IMM-08/09 (item không có target → vẫn render tĩnh).
> - `CommissioningListView`: khi click thẻ overdue → set cờ `filters.overdue = true`, gọi `applyFilters` (đẩy `overdue:1` vào payload `buildFilters`), hiển thị **chip "Quá hạn"** + nút **xóa chip** (xóa cờ overdue, refresh). Click thẻ state khác → giữ hành vi `quickFilter('workflow_state', …)` cũ.
> - `CommissioningFilters` thêm `overdue?: boolean`. `buildFilters` chỉ đính `overdue: 1` khi cờ bật.
> - INVARIANT FE↔BE: số trên thẻ `overdue_sla` = số dòng list sau khi áp `overdue:1` (cùng SoT BE).
>
> Mapping kpis→strip items: hàm thuần `commissioningKpiItems()` (`views/commissioning/commissioningKpi.ts`, có vitest `commissioningKpi.test.ts` — cập nhật K4 case: overdue giờ mang drill marker, KHÔNG còn display-only).

> **Vòng 16 — "Bàn giao tháng này" re-anchor (BR-04-11) — FE ZERO shape-change:** BE đổi `released_this_month` từ count theo `modified` sang count theo `commissioning_date ∈ [đầu tháng, hôm nay]`. `get_dashboard_stats()` GIỮ NGUYÊN shape: `kpis.released_this_month` vẫn type `number`, nhãn "Bàn giao tháng này" bất biến, `filterState='Clinical Release'` bất biến. **FE KHÔNG đổi component/store/type** — chỉ giá trị số trả về chính xác hơn (phiếu Released tháng-trước bị edit tháng này không còn thổi phồng card).
> - ⚠️ **Nuance drill (không phải bug, ghi rõ):** card đếm phiếu Clinical Release có `commissioning_date` trong THÁNG, nhưng click drill hiện lọc `filterState='Clinical Release'` = TẤT CẢ phiếu Clinical Release (không giới hạn tháng) → số drill ≥ số card. Đây là hành vi hiện hữu, KHÔNG nằm trong scope task này. INVARIANT BE-side (card == count cùng cửa sổ tháng) được verify ở tầng service/test (07 §commissioningKpi), KHÔNG qua FE drill. Nếu sau này muốn drill khớp tuyệt đối card → thêm virtual filter tháng (giống `overdue:1`) — `[ROADMAP]`, ngoài scope vòng 16.
> - Test FE: NEW `commissioningKpi.test.ts` case — strip render `released_this_month` đúng số + nhãn VI "Bàn giao tháng này" + màu success (verbatim từ `commissioningKpiItems()`), KHÔNG leak EN. vue-tsc prod 0.

**API gọi:** `get_dashboard_stats` (store `fetchDashboardStats`) — fetch song song với `fetchList` trong `onMounted`.
**State:** strip ẩn khi chưa có dữ liệu (`v-if="items.length"`). KPI fetch **non-blocking**: dùng `dashboardError` riêng, KHÔNG đụng `error`/`loading` của list (KPI lỗi không che list skeleton/banner).

#### 3.2. List (`/imm-04`)

**Filter bar:**
| Filter | Type | Default |
|---|---|---|
| Trạng thái | MultiSelect | Tất cả |
| Thiết bị | LinkSearch `Item` | — |
| Nhà cung cấp | LinkSearch `Supplier` | — |
| Tìm kiếm | text | — |
| Quá hạn SLA | virtual flag (set qua click KPI card) | off |

> **Chip "Quá hạn" (vòng 32):** khi cờ `overdue` bật (click thẻ KPI "Quá hạn SLA"), filter bar hiển thị active chip nhãn **"Quá hạn"** với nút ✕ xóa. Xóa chip = `filters.overdue = false` + `applyFilters`. Chip này nằm cùng hàng active-chips với các chip khác (`workflow_state`, `vendor_serial_no`...). Combinable với filter khác (không clobber).

**Cột bảng:**
| Cột | Render |
|---|---|
| Mã phiếu | Link đến detail |
| Thiết bị | `master_item` tên tự nhiên + mã nhỏ |
| Trạng thái | `<StatusBadge>` màu per-state |
| Ngày nhận | date + SLA countdown nếu >30 ngày |
| NCC | vendor name |

**Action:** Click row → navigate detail | Nút `+ Tạo phiếu mới`

#### 3.3. Detail (`/imm-04/:id`)

**Header:** tên thiết bị (lớn) + mã phiếu (nhỏ, mono) + `<StatusBadge>` + `<ActionBar>`

**Tabs:** Thông tin · Hồ sơ · Đo kiểm · NC · Lịch sử · Bàn giao

**Tab Thông tin:** Form editable theo state (chỉ edit được ở state ≤ Identification)

**Tab Đo kiểm:** Inline table checklist — kết quả Pass/Fail/N/A per row. Nút "Nộp kết quả" (enable khi 100% rows có result).

##### 3.3.a — Fail-path đo kiểm cơ sở (BR-04-04e/f · BR-04-13 · BR-04-14 — xem `04_Backend_Design.md §5.5`)

**Nộp bảng kiểm khả dụng ở 2 state:** `Initial Inspection` **và** `Re Inspection` (BR-04-14). FE **không** được ẩn tab/nút ở `Re Inspection` — đó chính là màn đo lại.

**`submit_baseline_checklist` nay là success cả khi KHÔNG ĐẠT.** Response 5-key `{name, overall_result: "Pass"|"Fail", tests_recorded, failed_parameters[], clinical_hold_required}`.
⚠️ **Cấm suy ra "đạt" từ `success === true`** — phải phân nhánh theo `overall_result`:

| `overall_result` | Banner | CTA gợi ý |
|---|---|---|
| `"Pass"` | success — "Đã ghi nhận {tests_recorded} phép đo. Kết quả: **Đạt**." | mở nút phê duyệt phát hành theo `allowed_transitions[]` |
| `"Fail"` | **warning (KHÔNG phải error)** — "Đã ghi nhận {tests_recorded} phép đo. Kết quả: **Không đạt** — thông số chưa đạt: {failed_parameters}." | nổi bật nút **“Báo cáo lỗi baseline”** (đưa phiếu sang Tái kiểm) |

**Bắt buộc trước khi cho bấm “Nộp kết quả”** (chặn EC-04-13 — hook save-time VR-03a vẫn `frappe.throw` ⇒ 417 thô):
1. **Mọi** dòng phải có `test_result` (Pass/Fail/N/A) — nút disable + tooltip khi còn dòng trống.
2. Dòng `Fail` **bắt buộc** `fail_note` non-rỗng — inline field error dưới đúng ô.

**Gate CTA phát hành lâm sàng (GATE-8 — server-driven, KHÔNG hardcode `status === …`):** nút dẫn tới `Clinical Release` (`Phê duyệt phát hành` · `Phê duyệt sau tái kiểm` · `Gỡ giữ lâm sàng`) **disable + tooltip** khi còn dòng `test_result ∉ {Pass, N/A}`. Nếu vẫn gọi, BE trả envelope `message_code === "IMM04-GATE-G03-BASELINE"` (HTTP-200, `http_status: 422` trong body) → hiện `title`/`error`/`action_hint` từ envelope + highlight các dòng trong `context.failed`. **KHÔNG** để rơi về toast `SYS-500`.

> ⚠️ Điều kiện tiên quyết FE: `IMM04-GATE-G03-BASELINE` phải có trong `frontend/src/i18n/messages.ts` — file **AUTO-GENERATED**, chỉ cập nhật bằng `python scripts/gen_fe_messages.py` (**cấm sửa tay**), rồi `npm run build`/redeploy.

**Tab Lịch sử:** Timeline `<AssetLifecycleTimeline>` — read-only, immutable.

**API gọi:** `get_form_context` — cache detail key `['imm04', 'detail', name]`

#### 3.4. Form tạo mới (`/imm-04/new`)

**Sections:** Đơn Mua Hàng → Thông tin Thiết bị → Khoa & Thời gian → Lưu

**State:** Loading spinner khi submit. Disable nút khi form có lỗi.

---

## 4. Component custom của module

| Component | Mục đích | Props chính |
|---|---|---|
| `StatusBadge.vue` | Hiển thị trạng thái phiếu với màu | `status: CommissioningStatus, size?: 'sm'\|'md'\|'lg'` |
| `ActionBar.vue` | Nút hành động theo state + role | `status, userRole[], hasOpenNc, allDocsReceived, allChecklistPass` |
| `BarcodeScanner.vue` | Scan QR/barcode camera hoặc USB HID | `mode: 'camera'\|'usb-hid', expectedFormat?` |
| `RiskClassBadge.vue` | Badge màu đỏ nếu C/D/Radiation | `riskClass: string` |
| `AssetLifecycleTimeline.vue` | Timeline lifecycle events immutable | `events: AssetLifecycleEvent[]` |
| `ClinicalHoldAlert.vue` | Alert Clinical Hold với danh sách doc thiếu | `riskClass, qaOfficer, missingLicenses[]` |
| `BaselineChecklistTable.vue` | Table đo kiểm inline editable | `items: CommissioningChecklist[], readonly: boolean` |
| `commissioning/QRLabel.vue` | Preview + in nhãn QR của phiếu nghiệm thu | `name: string` |

Đặt trong `frontend/src/components/imm04/`. Component dùng ≥ 2 module → promote ra `components/common/`.

### 4.1 — `QRLabel.vue` mã hoá deep-link asset (dedup vòng 13 / ADR-001 §D6.1)

> Hợp nhất nhãn QR commissioning về **1 đường deep-link** với QR cấp asset. Quét điện thoại trên phiếu đã release → mở thẳng màn `AssetScanInfo` (A6) thay vì ra chuỗi text thô.

| # | Quy tắc FE | Chi tiết |
|---|---|---|
| 1 | Nguồn mã hoá ẢNH QR | `QRCode.toDataURL(value)` với `value = res.qr_url` khi `res.qr_url` không rỗng (deep-link `/a/<token>`); **fallback** `res.qr_value` (tag `internal_tag_qr`) CHỈ khi `qr_url` rỗng (phiếu chưa mint asset). KHÔNG bao giờ mã hoá tag tuần tự khi đã có deep-link. |
| 2 | Type `QrLabelData` | `+qr_url?: string \| null`; **−`scan_url`** (BE bỏ field). `qr_value` GIỮ (fallback + nhãn cũ + scanner-wedge). |
| 3 | Nhãn hiển thị | Các field `label.*` GIỮ nguyên (kể cả `internal_qr` read-only hiển thị tham chiếu nội bộ). Chỉ ĐỔI nội dung mã hoá VÀO ảnh QR. |
| 4 | Edge token-less | `qr_url=null` → encode `qr_value` (như cũ) → nhãn vẫn in được, không lỗi, không màn trắng. |
| 5 | Tương thích ngược | `internal_tag_qr` vẫn hiển thị + dùng cho scanner-wedge (`BarcodeScanner.vue` / `get_barcode_lookup`) — KHÔNG xoá khỏi UI.

### 4.2 — Thẻ "Trạng thái Hồ sơ" (dữ liệu IMM-05, CR-75)

> Thẻ nằm trong `CommissioningForm.vue` (state + fetch ở `CommissioningDetailView.vue`), nhưng **hợp đồng dữ liệu thuộc IMM-05**. Spec chuẩn (tông màu, nhãn tiếng Việt, khối "Hết hạn", `hidden_count`, `required_total === 0`): [imm-05 / 06 §4.4](../imm-05/06_Frontend_Design.md); shape response: [imm-05 / 05 §2.7](../imm-05/05_API_Specification.md).

| # | Quy tắc FE | Chi tiết |
|---|---|---|
| 1 | Gate bằng **số**, không bằng chuỗi | `imm05IsCompliant` đọc `data.is_compliant === 1` — **KHÔNG** so `document_status === 'Compliant'`. Trước CR-75 BE trả `Complete` ⇒ so chuỗi luôn sai ⇒ hồ sơ đủ vẫn hiện đỏ. |
| 2 | 3 tông, hết dead-branch | vàng khi `is_compliant === 1 && document_status === 'Expiring_Soon'`; xanh khi `is_compliant === 1`; đỏ khi `is_compliant === 0`. |
| 3 | % thật | thanh tiến độ + nhãn `completeness_pct` (`required_satisfied/required_total`), KHÔNG còn hằng 0. |
| 4 | Nhãn tiếng Việt | ánh xạ 5 enum → nhãn VI (LL-FE-53); KHÔNG in raw enum ra DOM. |
| 5 | Hai khối vi phạm tách nhau | "Thiếu hồ sơ bắt buộc" (`missing_required`) ≠ "Hết hạn" (`expired_required`) — hai hành động khác nhau (bổ sung mới ≠ gia hạn). |
| 6 | `imm05-is-compliant` → `WorkflowActions.vue` | giữ nguyên prop; chỉ nguồn tính đổi (khoá số). |

---

### 4.3 — Thẻ «Điều kiện bàn giao» G01–G06 nói ĐÚNG cổng thật (CR-76 · BR-04-15/16)

> Component: `frontend/src/components/commissioning/ApprovalPanel.vue` (khối A) · fetch ở `CommissioningDetailView.vue:134-141` (`getGateStatus`) · type ở `frontend/src/api/imm04.ts:350-360`.
> Hợp đồng dữ liệu: [05 — API Specification](./05_API_Specification.md) §24 · thiết kế BE: [04 — Backend Design](./04_Backend_Design.md) §5.6.

**Nguyên tắc số 1 — thẻ mô tả CỔNG, không mô tả THÀNH TÍCH.** `gXX = true` nghĩa là *"cổng này không chặn phiếu"*. Mọi câu chữ khẳng định mạnh hơn thế (vd "Tất cả hồ sơ bắt buộc đã được xác nhận") là **nói dối người duyệt** khi thực tế đang là **giải trình thiếu hồ sơ**.

| # | Quy tắc FE | Chi tiết |
|---|---|---|
| 1 | **Type +1 khoá additive** | `interface GateStatus` thêm `g01_waived: boolean`; `defaultGateStatus` thêm `g01_waived: false`. 6 khoá cũ **không đổi tên/kiểu**. |
| 2 | **G01 có 3 trạng thái hiển thị, không phải 2** | (a) `g01_docs && !g01_waived` → ✅ xanh, *"Đủ hồ sơ bắt buộc"*; (b) `g01_docs && g01_waived` → ⚠️ **vàng**, *"Đạt — có giải trình thiếu hồ sơ"* + tooltip in nội dung `documents_incomplete_note` (đọc từ `doc`, đã có trong `get_form_context`); (c) `!g01_docs` → ❌ đỏ, *"Thiếu hồ sơ bắt buộc"*. **CẤM** dùng lại mô tả cũ *"Tất cả hồ sơ bắt buộc đã được xác nhận"* cho ca (b). |
| 3 | **G02 ghi rõ tính tham khảo** | Nhãn giữ *"Cơ sở hạ tầng"*, mô tả đổi thành *"Ghi nhận tham khảo — không chặn phát hành"*; icon dùng tông **trung tính** (xám) khi `false`, **KHÔNG** đỏ. `allGatesPassed` **KHÔNG** tính G02 (nó không phải cổng chặn) — nếu tính, nút CTA bị khoá bởi một cờ mà server không hề kiểm. |
| 4 | **G03 nhãn đúng ngữ nghĩa** | *"An toàn điện"* → **"Đo kiểm cơ sở (baseline)"**; mô tả *"Đã có phép đo và 100% dòng Đạt / Không áp dụng"*. Nhãn cũ chỉ mô tả **một** nhóm phép đo trong khi cổng xét **toàn bộ** bảng kiểm. |
| 5 | **G05 nói rõ chỉ NC "Đang mở" mới chặn** | mô tả *"Không còn phiếu không phù hợp đang mở (NC đang xử lý/đã xử lý không chặn)"*. |
| 6 | **Nhánh 403/404 KHÔNG làm trắng màn** | `getGateStatus` trả envelope lỗi trên **HTTP-200** ⇒ `catch` phải phân biệt: `code === 'FORBIDDEN'` → thẻ hiển thị trạng thái *"Bạn không có quyền xem điều kiện bàn giao của phiếu này."* (khối thẻ thu gọn, các phần khác của trang **vẫn render**); `code === 'NOT_FOUND'` → *"Không tìm thấy phiếu."*. **TUYỆT ĐỐI KHÔNG** `logout`/redirect `/login` (đó là dispatcher-403, khác loại — xem 05 §24.3). Hiện `loadGateStatus` nuốt lỗi về `defaultGateStatus` ⇒ **6 cổng đỏ giả** cho người thiếu quyền: phải thay bằng cờ `gateError` riêng. |
| 7 | **Ngôn ngữ (LL-FE-53)** | 100% tiếng Việt đầy đủ trong nhãn/mô tả/tooltip: *"phiếu không phù hợp"* (không viết tắt NC), *"đo kiểm cơ sở"*, *"người phê duyệt Ban Giám đốc"*. Giữ nguyên `G01…G06` (mã cổng, không phải từ viết tắt tiếng Anh). |
| 8 | **Không tự suy diễn ngược** | Cấm mọi logic FE kiểu `g01_docs === true ⇒ hiển thị "hồ sơ đầy đủ"`; nguồn duy nhất cho câu chữ là bảng ở quy tắc 2. |

**Test FE bắt buộc** (`ApprovalPanel.gate.test.ts`): (a) `g01_docs=true,g01_waived=true` ⇒ DOM chứa *"có giải trình"* và **KHÔNG** chứa *"Tất cả hồ sơ bắt buộc đã được xác nhận"*; (b) `g01_docs=true,g01_waived=false` ⇒ nhãn đủ-hồ-sơ; (c) `g02_facility=false` ⇒ `allGatesPassed` vẫn có thể `true`; (d) nhánh `gateError='FORBIDDEN'` ⇒ render thông báo tiếng Việt, panel không unmount.

---

## 5. Pinia store

> Source of truth: `frontend/src/stores/imm04.ts`

**File thực tế:** `frontend/src/stores/imm04.ts` (renamed từ `commissioning.ts` để align convention `immXX.ts`).

Store được export bằng `useCommissioningStore` (giữ tên symbol để giảm churn — xem các views: `CommissioningListView.vue`, `CommissioningCreateView.vue`, `CommissioningDetailView.vue`, components `CommissioningForm.vue`, `AssetDashboard.vue`).

Store dùng Composition API pattern (`defineStore('commissioning', () => {...})`).

**API calls:** Import từ `@/api/imm04` — tất cả function theo naming convention camelCase: `getFormContext`, `listCommissioning`, `transitionState`, `saveCommissioning`, `createCommissioning`, v.v.

---

## 6. Vue Query keys

```ts
// frontend/src/api/imm04.ts
export const imm04Keys = {
  dashboard: ['imm04', 'dashboard'] as const,
  list: (filters: ListFilters) => ['imm04', 'list', filters] as const,
  detail: (name: string) => ['imm04', 'detail', name] as const,
  snCheck: (sn: string) => ['imm04', 'sn-check', sn] as const,
}
```

**Invalidate sau mutation:**
```ts
// Sau submit_commissioning:
queryClient.invalidateQueries({ queryKey: ['imm04', 'list'] })
queryClient.invalidateQueries({ queryKey: ['imm04', 'detail', name] })
queryClient.invalidateQueries({ queryKey: ['imm04', 'dashboard'] })
```

---

## 6b. API call pattern — useApi().run()

```ts
// CommissioningDetailPage.vue
import { useApi } from '@/composables/useApi'
import { submitCommissioning } from '@/api/imm04'

const api = useApi()
const formErrors = reactive<Record<string, string>>({})

async function onSubmitCommissioning() {
  const result = await api.run(
    () => submitCommissioning({ name: props.id }),
    {
      successMessage: 'Phiếu đã Submit. Tài sản đã được tạo.',
      onFieldError: (fields) => Object.assign(formErrors, fields),
    }
  )
  if (result) {
    // result = response.data (đã unwrap envelope)
    router.push(`/assets/${result.final_asset}`)
  }
}
```

---

## 6c. TypeScript types

```
frontend/src/types/
├── common.ts          # Paginated<T>, ApiResponse<T>, ApiError
├── imm04.ts           # CommissioningStatus, AssetCommissioning, CommissioningChecklist, ...
└── inventory.ts       # Asset cross-module
```

Type mirror BE DTO 1-1: `CommissioningStatus` values khớp `workflow_state` trong DB.

---

## 7. Quy tắc ngôn ngữ FE

### 7.a. Nguyên tắc cứng
- 100% tiếng Việt mọi label, button, message, toast, error inline
- Mã phiếu (ACC-...) hiển thị nhỏ bên dưới tên tự nhiên, font-mono, `text-xs text-slate-500`
- State value tiếng Anh (`Clinical Release`) map qua i18n → tiếng Việt trên UI

### 7.b. Entity display pattern

```
┌────────────────────────────────────────┐
│ Máy X-quang Philips DigitalDiagnost    │ ← tên tự nhiên (font-semibold)
│ ACC-26-04-00001 · ITM-XRAY-001         │ ← mã (text-xs text-slate-500 font-mono)
└────────────────────────────────────────┘
```

### 7.c. Bảng từ ngữ chuẩn hóa

| Khái niệm | Tiếng Việt | Tránh từ |
|---|---|---|
| Asset Commissioning | Phiếu Nghiệm thu | Commissioning, Commission |
| Clinical Release | Phát hành lâm sàng | Release, Published |
| Clinical Hold | Tạm giữ lâm sàng | Hold, Suspended |
| Non Conformance | Không phù hợp | NC, Lỗi |
| Baseline test | Đo kiểm an toàn điện | Test, Kiểm tra |
| DOA | Hỏng ngay khi nhận | Dead-on-Arrival |
| Board approver | Người phê duyệt BGĐ | Approver |
| Biên bản bàn giao | Biên bản bàn giao | Handover document |

---

## 7d. Linked / Cascade fields

### 7d.a. Quan hệ phụ thuộc
- `po_reference` → auto-fill `vendor`, `master_item`, `risk_class`
- `master_item` → auto-fill `risk_class`, `is_radiation_device`
- `risk_class ∈ {C, D, Radiation}` → hiện field `qa_officer`, row License trong documents
- `is_radiation_device=1` → hiện field `radiation_license_no`

### 7d.b. Hành vi chuẩn
- Field cha thay đổi → field con reset + reload options
- Khi `po_reference` rỗng → `master_item` disabled + placeholder "Chọn PO trước"

### 7d.c. Pattern code

```ts
// CommissioningFormPage.vue
const poReference = ref<string | null>(null)
const masterItem = ref<string | null>(null)
const riskClass = ref<string | null>(null)

watch(poReference, async (newPo) => {
  masterItem.value = null
  riskClass.value = null
  if (!newPo) return
  const details = await getPoDetails({ po_name: newPo })
  if (details) {
    vendor.value = details.supplier
    // pre-fill item nếu chỉ có 1
    if (details.items.length === 1) masterItem.value = details.items[0].item_code
  }
})

watch(masterItem, async (item) => {
  if (!item) return
  const itemDoc = await fetchItemDetails(item)
  riskClass.value = itemDoc?.custom_risk_class ?? null
  isRadiation.value = itemDoc?.custom_is_radiation ?? false
})
```

---

## 7e. Input tight

### 7e.a. Ưu tiên picker
| Loại input | Dùng |
|---|---|
| Ngày | `<DateInput>` mask `dd/mm/yyyy` |
| PO, Item, Supplier | `<LinkSearch>` autocomplete |
| Risk class | `<RadioChip>` A / B / C / D / Radiation |
| Kết quả đo kiểm | `<RadioChip>` Pass / Fail / N/A |
| Số đo (mA, Ω…) | number input + unit SmartSelect |

### 7e.b. Validation realtime
- Serial Number: `check_sn_unique` on-blur, debounce 300ms
- Required fields: inline error khi blur
- Nút "Nộp kết quả đo kiểm" disabled khi còn row chưa có result

### 7e.c. Confirm modal
- Submit phiếu (Clinical Release → docstatus=1): confirm modal với checkbox "Tôi xác nhận hành động này"
- Cancel phiếu: confirm modal với tóm tắt hành động
- Return To Vendor: confirm modal danger (đỏ)

---

## 8. Empty / Error / Loading copy

| Tình huống | Copy |
|---|---|
| Danh sách phiếu rỗng | "Chưa có phiếu nào. Tạo phiếu đầu tiên từ PO." |
| Không có quyền xem | "Bạn không có quyền xem trang này. Liên hệ CMMS Admin." |
| Đang tải | Skeleton 5 dòng bảng |
| Lỗi server | "Có lỗi xảy ra. Vui lòng thử lại hoặc liên hệ hỗ trợ." |
| Submit thành công | "Phiếu đã Submit. Tài sản [asset_id] đã được tạo." |
| Concurrent error | "Phiếu vừa được cập nhật bởi người dùng khác. Tải lại để xem thay đổi mới nhất." |
| Clinical Hold alert | "Thiết bị [risk_class] phải có giấy phép BYT trước khi đưa vào lâm sàng (NĐ142/2020)." |
| Baseline có Fail — **kết quả nộp** (warning, KHÔNG error) | "Đã ghi nhận [tests_recorded] phép đo. Kết quả: **Không đạt** — thông số chưa đạt: [failed_parameters]. Chuyển phiếu sang Tái kiểm để đo lại." |
| Baseline chưa đạt — **chặn phát hành lâm sàng** (`IMM04-GATE-G03-BASELINE`) | Lấy `title` + `error` + `action_hint` **từ envelope** (registry i18n), KHÔNG hardcode chuỗi ở FE. Highlight các dòng trong `context.failed`. |
| Bảng kiểm còn dòng chưa chọn kết quả | "Còn [n] dòng chưa chọn kết quả Đạt/Không đạt/Không áp dụng." — disable nút "Nộp kết quả" |
| Dòng Không đạt thiếu ghi chú | "Dòng '[parameter]' Không đạt — bắt buộc ghi nguyên nhân." — field error dưới ô Ghi chú lỗi |
| Thẻ điều kiện bàn giao — **không đủ quyền** (`FORBIDDEN`, CR-76) | "Bạn không có quyền xem điều kiện bàn giao của phiếu này." — chỉ thu gọn **khối thẻ**, phần còn lại của trang vẫn hiển thị; **KHÔNG** đăng xuất, **KHÔNG** màn trắng |
| Thẻ điều kiện bàn giao — **phiếu không tồn tại** (`NOT_FOUND`) | "Không tìm thấy phiếu. Có thể phiếu đã bị xoá." |
| G01 đạt **nhờ giải trình** (`g01_waived=true`) | Nhãn "Đạt — có giải trình thiếu hồ sơ" + tooltip "Lý do: [documents_incomplete_note]" — tông **vàng** (cảnh báo), KHÔNG xanh |

---

## 9. Accessibility checklist module

- `<ActionBar>` buttons có `aria-label` đầy đủ tiếng Việt
- `<StatusBadge>` có `role="status"` + `aria-label="Trạng thái: {tên tiếng Việt}"`
- `<BarcodeScanner>` có `aria-live="polite"` cho kết quả scan
- Form fields có `<label>` liên kết `for` + `id`
- Clinical Hold alert: `role="alert"` để screen reader đọc ngay
- Keyboard navigation: Tab order hợp lý (PO → Item → NCC → Khoa → Ngày)
- Color contrast WCAG AA: Risk class badge đỏ đảm bảo contrast ≥ 4.5:1

---

## 9b. §G04-3STATE — Thẻ cổng G04 đọc CẶP `(g04_applicable, g04_radiation)` (AC-CR-85)

> **Nguồn:** BR-04-17 (`02 §IV.2`) · hợp đồng `05 §24.6` · BE `04 §5.7`. **Component:** `frontend/src/components/commissioning/ApprovalPanel.vue`.

### 9b.1. Lỗi hiện tại (verify @source 2026-07-27)

```ts
// ApprovalPanel.vue:122-125 — SAI: suy từ NGUỒN THỨ HAI
function isGateNa(gate: Gate): boolean {
  return gate.na && !props.doc.is_radiation_device
}
```

Thẻ G04 hiện N/A-hoá bằng `props.doc.is_radiation_device` — một trường **không nằm trong hợp đồng thẻ cổng** và (trước AC-CR-85) **đang bị server ghi sai** cho mọi phiếu Class C/D. Đây đúng class-of-bug *display ⇔ enforcement parity*: thẻ phải là **tấm gương** của validator, không phải bản diễn giải thứ hai.

### 9b.2. Hợp đồng FE sau AC-CR-85

| # | Yêu cầu |
|---|---|
| F1 | `GateStatus` (`frontend/src/api/imm04.ts:365-374`) **+ `g04_applicable?: boolean`** — khai **optional** (giống `g01_waived`) vì BE có thể còn stale |
| F2 | `isGateNa(g04)` đọc `props.gateStatus.g04_applicable` khi khoá **có mặt**: `return gate.na && props.gateStatus.g04_applicable === false` |
| F3 | **Fallback khi khoá VẮNG** (BE stale): mirror predicate server bằng **cả hai** vế — `!(doc.is_radiation_device || doc.risk_class === 'Radiation')`. ⚠️ **KHÔNG** dùng lại đúng một vế cũ: bỏ vế `risk_class === 'Radiation'` sẽ N/A-hoá một cổng mà server **vẫn chặn** ⇒ người duyệt thấy "Không áp dụng" rồi bấm phát hành và bị chặn câm |
| F4 | Thẻ **KHÔNG vỡ** khi khoá vắng: không `undefined` rò ra UI, không mất chip, không mất mô tả |
| F5 | 3 nhãn theo `05 §24.6.3`: «Không áp dụng» (chip xám) / «Đã có giấy phép» / «Chưa có giấy phép — cổng đang chặn phát hành» |
| F6 | Ô **BẤT KHẢ** `{applicable:false, radiation:false}`: hiển thị cảnh báo dữ liệu bất nhất (không im lặng, không tự đoán) |
| F7 | Mọi chỗ khác đang đọc `is_radiation_device` **giữ nguyên** — chúng trả lời câu hỏi KHÁC và **sẽ tự đúng lên** sau khi BE gỡ ghi đè: `showQaOfficer` (`ApprovalPanel.vue:91-93`) và `isHighRisk` (`CommissioningForm.vue:290-293`) gác theo **nhóm nguy cơ** (Class C/D/Radiation) — đúng ngữ nghĩa; `showRadiationWarning` (`CommissioningForm.vue:281-286`) + dòng đỏ "Bắt buộc cho thiết bị bức xạ" (`:626`) + ô tick hiển thị (`:655`) nói về **bức xạ**, hiện đang hiện oan trên Class C/D và sẽ hết oan |

### 9b.3. Copy tiếng Việt (đầy đủ, không viết tắt EN — LL-FE-53)

| Trạng thái | Chip | Mô tả |
|---|---|---|
| Không áp dụng | «Không áp dụng» | «Thiết bị không phát bức xạ nên cổng này không áp dụng. Không cần Giấy phép của Cục An toàn Bức xạ Hạt nhân.» |
| Đã có giấy phép | *(không chip)* | «Đã đính kèm Giấy phép của Cục An toàn Bức xạ Hạt nhân.» |
| Chưa có giấy phép | *(chip chặn)* | «Thiết bị phát bức xạ nhưng chưa đính kèm giấy phép — cổng này đang chặn phát hành.» |
| Bất nhất (BẤT KHẢ) | «Dữ liệu bất nhất» | «Máy chủ trả trạng thái cổng bức xạ không hợp lệ. Vui lòng tải lại trang; nếu vẫn còn, báo quản trị viên.» |

### 9b.4. Test FE (RENDER thật, không chỉ unit computed)

| TC | Kịch bản | Kỳ vọng |
|---|---|---|
| FE-G04-1 | `g04_applicable=false`, `g04_radiation=true` | render **«Không áp dụng»**; **không** xuất hiện chuỗi «Đạt»/«Đã có giấy phép» |
| FE-G04-2 | `g04_applicable=true`, `g04_radiation=true` | render «Đã có giấy phép» |
| FE-G04-3 | `g04_applicable=true`, `g04_radiation=false` | render «…đang chặn phát hành» |
| FE-G04-4 | Khoá **vắng** + `doc.is_radiation_device=0`, `risk_class='C'` | fallback ⇒ «Không áp dụng»; thẻ không vỡ |
| FE-G04-5 | Khoá **vắng** + `doc.is_radiation_device=0`, `risk_class='Radiation'` | fallback ⇒ **KHÔNG** N/A-hoá (server vẫn chặn) — chống đúng bẫy F3 |
| FE-G04-6 | `g04_applicable=false`, `g04_radiation=false` | hiện cảnh báo bất nhất, **không** hiện «Đạt» |
| FE-G04-7 | Anti-regression | `ApprovalPanel.vue` **không** còn `!props.doc.is_radiation_device` trong `isGateNa` |

---

## 10. Print spec

Trang cần in: **Biên bản Bàn giao** (sau khi phiếu ở Clinical Release).

- Generate server-side qua Frappe Print Format `Biên bản Bàn giao`
- ⚠️ TODO: Print Format chưa được config — `generate_handover_pdf` trả URL nhưng PDF có thể fail
- Layout: 1 cột, A4, ẩn navigation chrome
- Nội dung: thông tin phiếu, SN, QR, danh sách hồ sơ, kết quả đo kiểm, chữ ký BGĐ

---

## 11. §SCOPED-EMPTY — `/commissioning?asset=<mã>` trả 0 dòng: empty-state **CÓ NGỮ CẢNH** (AC-CR-98 · A9)

> Quyết định BE: [`../imm-00/ADR-IMM00-LIST-SCOPE.md §10`](../imm-00/ADR-IMM00-LIST-SCOPE.md) · hợp đồng drill: [`../imm-00/05_API_Specification.md §III.24.9`](../imm-00/05_API_Specification.md) (INV-CONN-26/27).

### 11.1 Vì sao (lỗi hiện tại — verify @source 2026-07-30)

Sau khi BE áp row-scope (AC-CR-98), một persona **hợp lệ** bấm «Xem tất cả» từ tab «Bản ghi liên quan» của thiết bị X có thể tới `/commissioning?asset=X` và nhận **0 dòng** (phiếu của X nằm ngoài phạm vi của họ, hoặc chỉ có phiếu `docstatus=2`). `CommissioningListView.vue` hiện chỉ có **1 empty-state chung** — "Không tìm thấy phiếu nào phù hợp." (`:269` mobile · `:354` desktop) + nút "Xóa bộ lọc để xem tất cả" **chỉ hiện khi `activeFilterCount > 0`**. Người dùng vừa đến từ một thiết bị cụ thể sẽ đọc câu đó là **"hệ thống không có phiếu nào"** → **màn trống chết**: không biết mình đang bị lọc theo thiết bị, không biết mã thiết bị nào, không có lối ra.

### 11.2 Hợp đồng FE (2 nhánh, KHÔNG gộp)

| Điều kiện | Render | testid |
|---|---|---|
| `store.list.length === 0` **∧** `route.query.asset` có giá trị | Empty-state **CÓ NGỮ CẢNH** (11.3) | **`list-empty-scoped`** |
| `store.list.length === 0` **∧** KHÔNG có `route.query.asset` | Empty-state **chung** hiện tại — **0 hồi quy**, giữ nguyên copy + nguyên điều kiện `activeFilterCount > 0` của nút "Xóa tất cả" | (như hiện tại) |

- Nguồn chân lý của nhánh là **`route.query.asset`** (khoá URL), KHÔNG phải `filters.value.final_asset` — hai thứ có thể lệch một nhịp khi người dùng vừa gỡ chip (`dropAssetQuery` `:82-90`). Khi 2 giá trị lệch, `route.query.asset` thắng.
- **Không** đổi/di chuyển empty-state chung; thêm nhánh **trước** nó (`v-if` scoped → `v-else` chung), ở **cả hai** khối: mobile card list (`:269`) và desktop table (`:348` `colspan="9"`).
- Nhánh scoped **không** phụ thuộc `activeFilterCount` — deep-link là bộ lọc **do hệ thống đặt**, người dùng không tự bấm nên không được yêu cầu họ suy ra.

### 11.3 Copy tiếng Việt (đầy đủ, KHÔNG viết tắt EN — LL-FE-53)

| Phần tử | Copy | Ghi chú |
|---|---|---|
| Tiêu đề | **"Thiết bị này chưa có phiếu nghiệm thu nào."** | KHÔNG in chữ `final_asset`/`asset` ra giao diện |
| Dòng ngữ cảnh | **"Đang lọc theo thiết bị: `<mã thiết bị>`"** | mã lấy từ `route.query.asset`, in `font-mono`; **KHÔNG** bịa tên thiết bị (BE list chưa enrich tên cho khoá lọc — xem `:58-61`) |
| Gợi ý | **"Có thể phiếu thuộc phạm vi khác hoặc đã bị hủy."** | phản ánh đúng 2 nguyên nhân THẬT: row-scope (§10.2) + `docstatus != 2` tự tiêm (INV-CONN-26) — KHÔNG hứa "sẽ thấy nếu thử lại" |
| Hành động chính | nút **"Xóa bộ lọc thiết bị"** | gọi đúng đường đã có: `dropAssetQuery()` (`:82-90`, `router.replace` bỏ khoá `asset`) — **KHÔNG** viết `router.push` mới, **KHÔNG** reset các filter khác |
| Hành động phụ | link **"Mở thiết bị `<mã>`"** → `/assets/<mã>` | dùng SSoT `detailRouteForDoctype`, KHÔNG literal đường dẫn |

**CẤM:** ❌ "Không tìm thấy phiếu nào phù hợp." cho nhánh scoped (mất ngữ cảnh) · ❌ nút "Xóa tất cả" thay cho "Xóa bộ lọc thiết bị" (hai hành động khác nhau: một xoá **mọi** filter, một chỉ xoá khoá thiết bị) · ❌ suy "0 dòng ⇒ không có quyền" và render 403 (0 dòng **không** phải lỗi — §10.6).

### 11.4 Test FE (RENDER thật, KHÔNG chỉ computed) — file MỚI `frontend/src/views/commissioning/commissioningScopedEmpty.test.ts`

| TC | Phát biểu chấm được |
|---|---|
| **TC-FE-COMM-SE-01** | mount với `route.query.asset='AC-ASSET-X'` + store trả `items: []` ⇒ **tồn tại** `[data-testid="list-empty-scoped"]` ∧ text chứa `AC-ASSET-X` |
| **TC-FE-COMM-SE-02** | cùng ca ⇒ có nút nhãn **đúng chữ** "Xóa bộ lọc thiết bị"; click ⇒ `router.replace` được gọi với query **không còn** khoá `asset` ∧ các khoá query khác **giữ nguyên** |
| **TC-FE-COMM-SE-03** | 0 dòng mà **không** có `route.query.asset` ⇒ **KHÔNG** có `list-empty-scoped`, empty-state chung vẫn render (0 hồi quy) |
| **TC-FE-COMM-SE-04** | `items` không rỗng + có `route.query.asset` ⇒ **KHÔNG** có `list-empty-scoped` (bảng vẫn render đủ dòng) |
| **TC-FE-COMM-SE-05** | text của nhánh scoped **không** chứa chuỗi `final_asset` (LL-FE-53 — cấm rò tên field ra giao diện) |
| **TC-FE-COMM-SE-06** | render ở **cả hai** breakpoint (khối mobile card + khối desktop table) — assert testid xuất hiện đúng **1** lần theo `v-if` breakpoint, không nhân đôi câu chữ |

### 11.5 §TỔNG-LÀ-SERVER — nguồn con số TỔNG là `store.pagination.total`, KHÔNG `items.length` (AC-CR-112)

> Quyết định BE + nghi thức chấm: [`../imm-00/ADR-IMM00-LIST-SCOPE.md §11`](../imm-00/ADR-IMM00-LIST-SCOPE.md) (`INV-COMM-SCOPE-5` · mutation **M4**) · TC BE đối ứng: [`07 §IX.2`](./07_Testing_QA.md).

**Vì sao thêm mục này (lỗ chứng minh, verify @source 2026-07-30):** màn danh sách in TỔNG ở **3 chỗ** — tiêu đề `:199` (`Tổng ${store.pagination.total} phiếu`) + dải thông tin mobile `:305` + desktop `:342` (`Hiển thị {{ store.list.length }} / {{ store.pagination.total }}`). Toàn bộ 6 TC ở §11.4 dùng store giả mà `pagination.total` **được suy ra từ `rows.length`** ⇒ `total` và `items.length` **luôn bằng nhau trong test** ⇒ nếu ai đó đổi nguồn TỔNG sang `store.list.length` (một "đơn giản hoá" rất dễ xảy ra khi refactor), **0 test nào ĐỎ**, mà hậu quả trên UI là: người dùng ở trang 1/8 đọc «Tổng 20 phiếu» thay vì «Tổng 156 phiếu» ⇒ mất luôn ý nghĩa của bất biến `count == rows` mà BE vừa trả giá để dựng.

**Hợp đồng FE (bất biến, KHÔNG đổi mã prod nếu đang đúng):**

| Điều | Quy định |
|---|---|
| Nguồn TỔNG | **`store.pagination.total`** (BE trả trong `pagination`) tại **cả 3** chỗ `:199` · `:305` · `:342`. **CẤM** `store.list.length`, **CẤM** cộng dồn trang ở FE |
| Nguồn SỐ ĐANG HIỂN THỊ | `store.list.length` (số dòng của **trang hiện tại**) — hai con số **khác nhau là bình thường**, không được "làm cho giống nhau" |
| Empty-state theo ngữ cảnh | giữ `data-testid="list-empty-scoped"` (`:269`) + điều kiện `assetScope !== '' ∧ store.list.length === 0` (`isScopedEmpty`) — **không** thay bằng `pagination.total === 0` (total là số của **predicate**, list là số của **trang**) |
| Cờ `overdue` | drill từ thẻ KPI «Quá hạn SLA» gửi `overdue: true` (`cleanFilters()`), AND với các filter khác ở BE (BR-04-10) — **không** tự dựng predicate ngày ở FE |

**Sửa BẮT BUỘC ở test double (không phải ở mã prod):** store giả trong `commissioningScopedEmpty.test.ts` phải cho `total` **độc lập** với `rows.length` (thêm `const total = ref<number|null>(null)` → `get pagination() { return { …, total: total.value ?? rows.value.length } }`). Giữ nguyên hành vi cũ khi `total` chưa set ⇒ **0 hồi quy** cho 6 TC đang xanh.

| TC | Phát biểu chấm được |
|---|---|
| **TC-FE-COMM-SE-07** | `rows` = 2 dòng ∧ `pagination.total` = **156** ⇒ tiêu đề chứa **"Tổng 156 phiếu"** ∧ dải thông tin chứa **"2"** và **"156"** (đúng thứ tự «Hiển thị 2 / 156»). **Mutation M4** (`:199` → `store.list.length`) ⇒ TC này **ĐỎ** |
| **TC-FE-COMM-SE-08** | deep-link drill quá hạn: `route.query = { asset: 'AC-ASSET-X', filter: 'overdue' }` + `rows = []` ⇒ (a) `list-empty-scoped` **có mặt** ∧ text chứa `AC-ASSET-X`; (b) chip «Quá hạn» **có mặt** (nhãn VI, không rò chữ `overdue`); (c) bấm «Xóa bộ lọc thiết bị» ⇒ `fetchList` được gọi với đối số **còn** `overdue: true` và **không còn** khoá thiết bị ⇒ chứng minh hai bộ lọc **AND**, xoá một cái không xoá cái kia |

**CẤM:** ❌ assert bằng snapshot toàn trang (đổi 1 lớp CSS là ĐỎ giả) · ❌ dùng `pagination.total` để quyết định empty-state · ❌ in chữ `overdue`/`final_asset` ra giao diện (LL-FE-53) · ❌ nới assert để cho xanh; ĐỎ ⇒ sửa **root cause** ở mã prod kèm TC tái hiện viết **trước**.

---

## DoD — File 06 hoàn chỉnh

- [x] Sitemap đủ mọi route module
- [x] UI Mockup ≥ 4 màn hình chính
- [x] Sidebar nav config
- [x] Mỗi archetype có table columns / form section / state mapping
- [x] Component custom liệt kê với props
- [x] Type definitions mirror BE (file 05 §1.5)
- [x] State phân lớp: server data → Vue Query, UI state → Pinia
- [x] Vue Query keys + invalidate rule
- [x] Quy tắc ngôn ngữ FE: 100% tiếng Việt + entity display pattern
- [x] Bảng từ ngữ chuẩn hóa
- [x] Cascade fields: po_reference → item → risk_class
- [x] Input tight: picker + validation realtime + confirm modal
- [x] Empty / Error / Loading copy đủ
- [x] Accessibility checklist module
- [x] Print spec
