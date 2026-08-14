# 06 — Thiết kế Frontend — IMM-08 Bảo trì định kỳ (PM)

| Mục | Giá trị |
|---|---|
| Module | IMM-08 — Preventive Maintenance |
| Phạm vi | Per-module |
| Owner | FE Lead + Designer |
| Module accent | `emerald-600` |

---

## 1. Sitemap / Route map

| Route | Tên trang | Archetype | Role | Component chính |
|---|---|---|---|---|
| `/pm` | Redirect → Dashboard | — | — | — |
| `/pm/dashboard` | Dashboard Bảo trì PM | Dashboard | Workshop Head, VP Block2, CMMS Admin | `PMDashboardView.vue` |
| `/pm/calendar` | Lịch bảo trì PM | Calendar | Workshop Head, HTM Technician | `PMCalendarView.vue` |
| `/pm/work-orders` | Danh sách phiếu PM | List | All IMM roles | `PMWorkOrderListView.vue` |
| `/pm/work-orders/create` | Tạo phiếu PM thủ công | Form | Workshop Head, CMMS Admin | `PMWorkOrderCreateView.vue` |
| `/pm/work-orders/:id` | Chi tiết phiếu PM | Detail+Form | Workshop Head, Kỹ thuật viên (assigned) | `PMWorkOrderDetailView.vue` |
| `/pm/schedules` | Danh sách lịch PM | List | Workshop Head, CMMS Admin | `PmScheduleListView.vue` |
| `/pm/templates` | Checklist Template PM | List | Workshop Head, CMMS Admin | `PmTemplateListView.vue` |

> **Ghi chú:** `PmScheduleListView.vue` và `PmTemplateListView.vue` dùng API từ `@/api/imm00` (not `imm08`) — các endpoint Schedule/Template được expose qua `imm08` BE nhưng FE có thể dùng imm00 wrapper tùy routing.

---

## 2. Sidebar nav module

```ts
"imm-08": {
  title: "IMM-08 · Bảo trì định kỳ",
  accent: "emerald-600",
  items: [
    { icon: "layout-dashboard", label: "Dashboard PM",    to: "/pm/dashboard" },
    { icon: "calendar",         label: "Lịch bảo trì",   to: "/pm/calendar" },
    { icon: "clipboard-list",   label: "Phiếu bảo trì",  to: "/pm/work-orders" },
    { icon: "alert-triangle",   label: "Quá hạn",        to: "/pm/work-orders?filter=status:Overdue" },
  ],
}
```

---

## 3. Thiết kế giao diện

### 3.a. UI Mockup

**Mockup 1 — PM Dashboard:**

```
┌────────────────────────────────────────────────────────────────────┐
│  Dashboard Bảo trì PM                         [Tháng 4/2026 ▼]    │
│  ── STRIP THÁNG (Phạm vi: tháng 4/2026) ─────────────────────────  │
├────────────┬───────────┬───────────┬───────────┬───────────────────┤
│  87.5%     │    16     │    14     │     1     │   3.5 ngày        │
│ Compliance │ Tổng lịch │ Đúng hạn  │ Quá hạn   │ Trễ trung bình    │
│ (— nếu     │ (tháng)   │ (tháng)   │ trong     │ (tháng)           │
│  tổng=0)   │           │           │ tháng     │                   │
├────────────┴───────────┴───────────┴───────────┴───────────────────┤
│  ── KHỐI TOÀN HỆ THỐNG ─────────────────────────────────────────  │
│  [ 🔴 Quá hạn (toàn hệ thống): 5 ]   ← drill ?overdue=1            │
│     Toàn hệ thống · click để xem danh sách                        │
├────────────────────────────────────────────────────────────────────┤
│  TREND COMPLIANCE 6 THÁNG                                          │
│  100% ─────●───────●─────●                                        │
│   75%   ●        ●     ●                                          │
│        T11  T12   T1    T2   T3   T4                               │
├────────────────────────────────────────────────────────────────────┤
│  THIẾT BỊ QUÁ HẠN                                                  │
│  🔴 PM-WO-2026-00007  Monitor Philips  Quá hạn 8 ngày   [Xem]     │
│  🔴 PM-WO-2026-00012  Máy thở Drager   Quá hạn 3 ngày   [Xem]     │
└────────────────────────────────────────────────────────────────────┘
```

**Mockup 2 — PM Calendar:**

```
┌────────────────────────────────────────────────────────────────────┐
│  Lịch PM Tháng 4/2026                [◀]  [Tháng] [Tuần]  [▶]    │
│  Filter: [Kỹ thuật viên ▼] [Asset ▼]                               │
├───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────────┤
│  T2   │  T3   │  T4   │  T5   │  T6   │  T7   │  CN   │           │
│  14   │  15   │  16   │  17   │  18   │  19   │  20   │           │
│       │       │       │🟡PM-1 │       │🔴PM-7 │       │           │
│       │       │       │Máy thở│       │Monitor│       │           │
└───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────────┘
```

**Mockup 3 — PM Work Order List:**

```
┌────────────────────────────────────────────────────────────────────┐
│ Phiếu Bảo trì PM                           [+ Tạo PM thủ công]     │
│ Filter: [Trạng thái ▼] [Kỹ thuật viên ▼] [Asset...] [Từ] [Đến]    │
├──────────┬──────────────┬──────────┬──────────┬────────────┬───────┤
│ Mã WO    │ Thiết bị     │ Loại PM  │ Đến hạn  │ Kỹ thuật viên │ TT │
├──────────┼──────────────┼──────────┼──────────┼────────┼───────────┤
│ PM-00001 │ Máy thở DC   │ Quarterly│ 17/04    │ ktv1   │🔴 Quá hạn │
│ PM-00003 │ Monitor PH   │ Annual   │ 22/04    │ ktv2   │🟢 Hoàn thành│
└──────────┴──────────────┴──────────┴──────────┴────────┴───────────┘
                                          Trang 1/3   [← →]
```

**Mockup 4 — PM Work Order Detail (Checklist):**

```
┌────────────────────────────────────────────────────────────────────┐
│ ← PM-WO-2026-00001 — Máy thở Drager Evita V500    🟡 Đang thực hiện│
├────────────────────────────────────────────────────────────────────┤
│ THÔNG TIN CHUNG                                                    │
│ Thiết bị: AC-ASSET-2026-0003    │ Đến hạn: 17/04/2026             │
│ Kỹ thuật viên: ktv1@bv.vn       │ Loại PM: Quarterly              │
│ Khoa:     ICU                   │ Class:   III ⚠ Cần ảnh          │
├────────────────────────────────────────────────────────────────────┤
│ CHECKLIST  (4 / 10 đã điền)    ▓▓▓▓░░░░░░ 40%                     │
│                                                                    │
│ [1] Kiểm tra điện áp đầu vào (210–240V)         [CRITICAL]        │
│     ○ Pass  ● Fail-Minor  ○ Fail-Major  ○ N/A                     │
│     Giá trị đo: [225] V    Notes: [..rò rỉ van..] *bắt buộc       │
├────────────────────────────────────────────────────────────────────┤
│ KẾT QUẢ TỔNG THỂ                                                   │
│ Tóm tắt kỹ thuật viên: [..............................]            │
│ Đã gắn sticker PM: ☐   Thời gian: [__] phút                       │
├────────────────────────────────────────────────────────────────────┤
│  [Báo lỗi Major 🔴]  [Hoãn lịch]  [Lưu nháp]  [Hoàn thành ✓]    │
└────────────────────────────────────────────────────────────────────┘
```

### 3.b. UI Screenshot (post-build)

Screenshots thực tế lưu tại: `docs/imm-08/screenshots/` (thêm sau khi build xong).

### 3.c. Trang chi tiết theo archetype

#### 3.1. Dashboard (`/pm/dashboard`)

> Bám `design-frontend.md §3.Dashboard`.

**🆕 Vòng 10 (Self-Correction — BR-08-13). 2 khối phạm vi, mỗi tile có NHÃN PHẠM VI rõ ràng — KHÔNG để tile global đứng chung strip tháng không-đối-soát-được.**

**KHỐI THÁNG (strip — sub-label "Phạm vi: tháng {month}/{year}"):**

| Tile | Field (`kpis.*`) | Nhãn VI | Render rule |
|---|---|---|---|
| Compliance Rate | `compliance_rate_pct` | "Tỷ lệ tuân thủ" + "Phạm vi: tháng M/Y" | `null → '—'`/N/A (INV-PM-KPI-3); KHÔNG hiện `0%` khi null |
| Tổng lên lịch | `total_scheduled` | "Tổng lên lịch" + "Phạm vi: tháng M/Y" | số (BE đã loại WO `Cancelled` khỏi mẫu — INV-PM-KPI-6); FE render verbatim, KHÔNG tự cộng/trừ |
| Đúng hạn | `completed_on_time` | "Hoàn thành đúng hạn" + "Phạm vi: tháng M/Y" | số (xanh) |
| **Quá hạn trong tháng** | `overdue_in_month` | **"Quá hạn trong tháng"** + "Phạm vi: tháng M/Y" | số (đỏ); **KHÔNG dùng `kpis.overdue`** |
| Trễ trung bình | `avg_days_late` | "Trễ trung bình (ngày)" + "Phạm vi: tháng M/Y" | số |

**KHỐI TOÀN HỆ THỐNG (tile riêng, NGOÀI strip tháng):**

| Tile | Field | Nhãn VI | Hành vi |
|---|---|---|---|
| **Quá hạn (toàn hệ thống)** | `overdue` (`count_overdue_pm()`) | **"Quá hạn (toàn hệ thống)"** + sub "Toàn hệ thống" | click → drill `?overdue=1` (route `/pm/work-orders?overdue=1`) — INV-PM-KPI-2/6 không đổi |

> **INV-PM-KPI-4 (phản ví dụ FE):** khi `total_scheduled=0`, `overdue_in_month=0`, `overdue=5` → strip tháng hiện "Tổng lên lịch: 0 / Quá hạn trong tháng: 0 / Tuân thủ: —", tile global riêng hiện "Quá hạn (toàn hệ thống): 5". Người xem ĐỐI-SOÁT được: trong tháng không có gì, nhưng hệ thống còn 5 WO quá hạn tồn từ trước. KHÔNG còn "Quá hạn: 5" đứng cạnh "Tổng lịch: 0".
>
> **INV-PM-KPI-5 (đồng bộ cross-view):** strip KPI trên `PMWorkOrderListView.vue` dùng CÙNG endpoint `get_pm_dashboard_stats` → số tile khớp byte-for-byte với `PMDashboardView`. KHÔNG view nào tự re-compute từ list cục bộ. Không leak EN/raw status (dịch qua `formatters.translateStatus`).
>
> **INV-PM-KPI-6 (FE render mẫu loại-Cancelled — vòng 25):** strip `PMWorkOrderListView.vue` render **verbatim** các số BE trả:
> - tile "Tổng lên lịch" (a.k.a. "Tổng lịch tháng") = `kpis.total_scheduled` mới (đã loại Cancelled) — FE **KHÔNG** tự đếm list cục bộ, **KHÔNG** tự cộng/trừ `Cancelled`.
> - tile "Tỷ lệ tuân thủ" = `compliance_rate_pct`; `null → '—'` (KHÔNG `0%`/`0.0`) khi tháng chỉ-Cancelled (`total_scheduled==0`).
> - KHÔNG leak text EN (`'Cancelled'`/`'Completed'`/`'Overdue'`) — mọi status qua `formatters.translateStatus`. `vue-tsc` prod 0 lỗi.

**Action buttons:** Nút "Xuất báo cáo" (Workshop Head) — planned.

**State:**
- Loading: skeleton (5 tile strip tháng + 1 tile global) + chart placeholder
- Empty (`total_scheduled==0`): strip vẫn render (0/0/0/—) + tile global; chú thích "Không có PM nào đến hạn trong tháng này"
- Error: toast đỏ

#### 3.2. Calendar (`/pm/calendar`)

| Filter | Type | Default |
|---|---|---|
| Tháng/Năm | date picker | tháng hiện tại |
| Kỹ thuật viên | LinkSearch User | — |
| Asset | LinkSearch Asset | — |

**API:** `get_pm_calendar?year&month&technician?&asset_ref?`

**State:**
- Loading: skeleton grid
- Click event: open right drawer → lazy load `get_pm_work_order`

#### 3.3. List (`/pm/work-orders`)

| Cột | Type | Render |
|---|---|---|
| Mã WO | text/link | → `/pm/work-orders/{name}` |
| Thiết bị | text | asset_name |
| Loại PM | badge | pm_type |
| Đến hạn | date | dd/MM/yyyy |
| Kỹ thuật viên | text | assigned_to |
| Trạng thái | StatusChip | màu theo state |

**Filter bar:** Trạng thái · Kỹ thuật viên · Asset (free text) · Từ ngày – Đến ngày.

**Drill-down chips (từ KPI dashboard):**

| Chip key | Nguồn KPI | Nhãn (label) | Forward tới BE |
|---|---|---|---|
| `overdue` | `pm_overdue` (BR-08-11) | `Quá hạn` | `?overdue=1` |
| `dueBefore` | `pm_due_7d` (BR-08-12) | **`Đến hạn trong 7 ngày`** / `Đến hạn ≤ {date}, từ hôm nay` | `?due_before={date}` verbatim |

> 🆕 Vòng 23 (Self-Correction). Chip `dueBefore` đổi nhãn từ `Đến hạn trước {due_before}` → **`Đến hạn ≤ {date}, từ hôm nay`** (hoặc `Đến hạn trong 7 ngày` khi date == today+7). Lý do: nhãn cũ "trước {date}" khiến user hiểu nhầm danh sách GỒM cả WO quá hạn. Ngữ nghĩa thật là **cửa sổ due-soon `[hôm nay, {date}]`** — WO quá hạn nằm ở chip `Quá hạn` riêng (disjoint). FE **KHÔNG inline-compute membership** — vẫn forward `due_before` verbatim, BE `_normalize_filters` lo cận dưới `today` (gọi `due_soon_filter`). **Zero contract change ngoài label.** File: `frontend/src/views/pm/PMWorkOrderListView.vue` (`activeChips` computed, chip `dueBefore`).

> 🆕 **CR-18 (tìm kiếm free-text phía SERVER — BR-08-17):** ô "Tìm phiếu" nay refetch **SERVER** thay vì lọc client-side chỉ trang đã tải.
> - **Trước (search-trap):** `search` là ref client; `filteredWOs` computed lọc `store.workOrders` (CHỈ trang đang tải) theo `name`/`asset_name`/`asset_ref` `toLowerCase().includes` ⇒ phiếu ở trang 2+ KHÔNG hiện dù khớp. Subtitle "Tổng {total}" (server) lệch số dòng lọc (client) = trap.
> - **Sau:** `search` ref → **debounce 300ms** → `buildFilters()` KHÔNG chứa search; thay vào đó truyền `search` như tham số riêng cho `store.fetchWorkOrders(buildFilters(), 1, search.value.trim())` → `listPMWorkOrders(filters, page, pageSize, search)` (discrete query-param `search`). Mỗi lần đổi `search` → **reset `page=1`** + refetch. **GỠ** `filteredWOs` computed (render thẳng `store.workOrders`); GỠ mọi nơi dùng `filteredWOs.length`/`?? filteredWOs.length` (subtitle + "Hiển thị N" + empty-state) → dùng `store.pagination.total` / `store.workOrders.length`. **GIỮ** chip `search` (`activeChips` key `'search'`, xóa chip → clear `search` + refetch). Placeholder giữ "Tìm theo mã lệnh công việc, tên thiết bị...".
> - **Kết quả phủ MỌI trang:** BE OR-LIKE `name`/`asset_code`/`asset_name` toàn tập; FE KHÔNG lọc lại (transport-agnostic). File: `frontend/src/views/pm/PMWorkOrderListView.vue`, `frontend/src/api/imm08.ts` (`listPMWorkOrders` +`search`), `frontend/src/stores/imm08.ts` (`fetchWorkOrders` forward `search`).

#### 3.4. Detail — PM Work Order (`:id`)

**Left panel (60%):** Thông tin WO + Checklist items (one per row, radio Pass/Fail/N/A).
**Right panel (40%):** SLA countdown + Kỹ thuật viên info + action buttons.

**UX flow — đính ảnh bằng chứng theo mục checklist (BR-08-15/16, mobile CR-14/G6):**
- Mỗi hàng checklist có **1 control upload ảnh** (nút "📷 Ảnh bằng chứng"), gọi `POST attach_pm_checklist_photo` **multipart** với `work_order_name`, `checklist_item_idx` (STT hàng), `file`. Sau success (`{file_url, file_name, checklist_item_idx}`) → hiển thị **thumbnail** từ `checklist_results[idx].photo` (đã có sẵn trong `get_pm_work_order`), KHÔNG cần refetch toàn phiếu ngoài invalidate.
- **Client-side chỉ pre-hint** (đuôi jpg/png, ~10 MB) để UX nhanh; **server là enforcer cuối** — mọi lỗi (`VALIDATION`/`FORBIDDEN`/`NOT_FOUND`) surface Decision-B HTTP-200 → map qua Notification Contract, hiển thị dưới control (`fields.file` / `fields.checklist_item_idx`). KHÔNG so client-clock, KHÔNG tự suy quyền.
- **Gate hiển thị control:** chỉ KTV được giao (`assigned_to`) hoặc role có `pm.write` (mirror gate nút action theo `allowed_transitions`, KHÔNG hardcode); WO ở trạng thái đang thực hiện (Open/In Progress). Class C/D (`risk_class`) → badge "⚠ Cần ảnh" nhắc BR-08-06.
- **1 ảnh/mục — write-once** (server chặn ảnh thứ 2 → `"Mỗi mục checklist chỉ đính 1 ảnh"`, KHÔNG ghi đè; xem ADR-IMM08-PHOTO-03). `checklist_results[idx].photo` = ảnh đã đính làm thumbnail. Sau khi đính, control chuyển sang trạng thái "đã có ảnh" (KHÔNG cho chọn lại). Multi-photo/mục + đổi-ảnh-có-audit (`remove_pm_checklist_photo`) = `[ROADMAP]`.
- **Ảnh iPhone (HEIC/HEIF):** app mobile PHẢI transcode → JPEG trước upload (ADR-IMM08-PHOTO-04); web-FE chỉ pre-hint đuôi jpg/png. Chọn HEIC trên web → server reject `"Tệp phải là ảnh JPG hoặc PNG"` (hiển thị dưới control `fields.file`).

**UX flow — chặn nghiệm-thu-giả khi bảng kiểm RỖNG (BR-08-19, ADR-IMM08-CHECKLIST-EMPTY-01):**
- Khi WO có **0 mục checklist** (`checklist_results.length === 0` — WO tạo template-less / template 0 mục): banner amber "Chưa gắn bảng kiểm mẫu — không thể nghiệm thu" + **disable nút "Xác nhận hoàn thành"** (`canSubmit &&= checklist_results.length > 0`). Server VẪN là enforcer cuối: submit lọt → Decision-B HTTP-200 `message_code=IMM08-CHECKLIST-EMPTY` → toast VI đúng registry (KHÔNG tự chế message).
- **Phân biệt 2 mã** (KHÔNG trộn UX): `IMM08-CHECKLIST-EMPTY` (0 mục) → hint "gắn bảng kiểm mẫu" (lỗi cấu hình, KTV không tự sửa được → gợi báo Workshop Head); `IMM08-CHECKLIST-INCOMPLETE` (còn mục thiếu result) → hint "điền nốt các mục" + highlight dòng thiếu. `ChecklistProgress total===0` → render trạng thái rỗng riêng, KHÔNG hiện "0/0 hoàn tất" (đánh lừa đã xong).
- **KHÔNG success-giả:** chỉ báo "Đã hoàn thành" khi envelope `success===true`; mọi `VALIDATION` (EMPTY/IDX_UNKNOWN/INCOMPLETE) → giữ nút, hiện lỗi, KHÔNG điều hướng rời trang.

#### 3.4.a Server-driven CTA — render 4 nút vòng đời TỪ `available_actions[]` (AC-CR-77, GATE-8 / LL-FE-51) 🟡 SPEC (FE Bước-4)

> Hợp đồng BE: [`05 §13`](./05_API_Specification.md). Nguyên tắc: **FE chỉ render, KHÔNG tự suy** — nhãn, trạng thái disabled và tooltip đều do **server** quyết.

**Nguồn dữ liệu.** `get_pm_work_order` trả `available_actions`: mảng **đúng 4** phần tử, thứ tự cố định `[start_work, submit_result, reschedule, report_major_failure]`, shape `{key, label, route, enabled, reason}` (`route` luôn `""` — CTA nằm trong màn, KHÔNG deep-link).

**Type (`frontend/src/api/imm08.ts`)** — thêm, KHÔNG sửa type cũ:

```ts
/** 1 CTA server-driven màn chi tiết phiếu PM (AC-CR-77) — mirror BE
 *  `_build_pm_available_actions` (services/imm08.py). enabled/reason do SERVER
 *  tính (transition ∩ capability ∩ business gate); FE KHÔNG tự suy lại. */
export interface AvailableAction {
  key: string
  label: string
  route: string
  enabled: boolean
  reason: string
}
// trong interface PMWorkOrder — OPTIONAL để tương thích payload cũ (fallback đường cũ):
available_actions?: AvailableAction[]
```

**Quy tắc render (`PMWorkOrderDetailView.vue`):**

| Điều | Bắt buộc |
|---|---|
| Map action | `const actionMap = computed(() => Object.fromEntries((wo.value?.available_actions ?? []).map(a => [a.key, a])))` |
| **Bỏ nhân bản predicate** | 4 computed `canStart` / `canCompleteRender` / `canReschedule` / `canReportMajor` **KHÔNG** còn ghép `can('pm.*') && allowedTransitions.includes(...)` — đọc thẳng `actionMap[key]` |
| Nhãn nút | dùng `action.label` của server (**KHÔNG** hardcode chuỗi ở FE — hết drift nhãn BE↔FE) |
| Disabled | `:disabled="!action.enabled"` — nút **vẫn hiển thị**, KHÔNG ẩn (người dùng thấy được vì sao không bấm được) |
| Tooltip | `action.reason` (đã là tiếng Việt do BE trả) |
| Lớp 2 form (chỉ `submit_result`) | `disabled = !action.enabled || completionBlockReason !== ''`; tooltip = `action.reason || completionBlockReason`. **GIỮ** `completionBlockReason` cho 3 cổng form (mục chưa chấm / thời lượng / tem) — server không đánh giá được (ADR-IMM08-CTA-03) |
| **Fallback bắt buộc** | payload **thiếu** `available_actions` (client cũ / BE chưa reload) ⇒ rơi về **đúng logic hiện tại** (`can(...) && allowed_transitions.includes(...)`) — **KHÔNG nút nào biến mất** (A8) |
| `data-testid` | GIỮ NGUYÊN `cta-start` / `cta-complete` / `cta-reschedule` / `cta-major` (test cũ không gãy) |

**Đổi vị trí có chủ đích — «Hoãn lịch»:** hiện nút chỉ nằm **trong banner quá hạn** (`v-if="isOverdue"`), nên phiếu *Open*/*Đang thực hiện* chưa quá hạn **không thấy nút** dù server cho phép (lỗ D-3, `05 §13.1`). Sau AC-CR-77, «Hoãn lịch» render ở **cụm nút hành động** theo `available_actions.reschedule` (banner quá hạn giữ **shortcut** cũng đọc CÙNG action object — 1 nguồn, 2 chỗ hiển thị).

**Test render bắt buộc (`frontend/src/views/pm/pmWorkOrderServerDrivenCta.test.ts` — mới):**

| TC | Kỳ vọng |
|---|---|
| `FE-PMCTA-1` | payload có `available_actions` với `start_work.enabled=false` + `reason` ⇒ nút `cta-start` **hiện**, `disabled`, tooltip == `reason` (đọc từ DOM, **không** đọc từ store) |
| `FE-PMCTA-2` | `submit_result.enabled=true` nhưng `completionBlockReason` non-empty ⇒ vẫn `disabled` + tooltip = reason form (lớp 2 không bị nuốt) |
| `FE-PMCTA-3` | nhãn nút == `label` server (đổi `label` trong payload ⇒ DOM đổi theo) — chống hardcode |
| `FE-PMCTA-4` | payload **KHÔNG** có `available_actions` ⇒ 4 nút vẫn render theo đường cũ (0 nút biến mất) |
| `FE-PMCTA-5` | `available_actions` **không** chứa key `cancel` ⇒ màn hình **không** render nút hủy phiếu nào |

**Never (FE):** ❌ tự tính lại `enabled` từ `status`/`allowed_transitions` khi đã có `available_actions` · ❌ ẩn nút disabled (mất thông tin lý do) · ❌ hardcode nhãn/tooltip tiếng Anh · ❌ hiển thị mã trạng thái thô trong tooltip.

**Ghi nhận (KHÔNG thuộc AC-CR-77 — backlog `05 §13.10` B2):** nút "Tiếp tục bảo trì" (`cta-resume`) hiện chỉ gọi `store.fetchWorkOrder(props.id)` = **dead control** (không đổi trạng thái gì, vì chưa có endpoint resume). Xử lý ở vòng riêng sau khi ratify B1.

---

## 4. Component custom của module

| Component | Mục đích | Props |
|---|---|---|
| `PMStatusChip` | Badge màu theo PM WO status | `status: PMStatus` |
| `ChecklistProgress` | Thanh tiến trình X/N items có result | `filled: number, total: number` |
| `PMTimeline` | Timeline trạng thái WO | `history: TimelineEntry[]` |
| `SLACountdown` | Hiển thị ngày còn lại đến due_date | `dueDate: string, status: PMStatus` |
| `OverdueAlert` | Banner đỏ khi WO Overdue + ngày trễ | `daysOverdue: number` |
| Compliance pre-flight gate banner (inline trong `PMWorkOrderCreateView.vue`) | Cảnh báo SỚM khi asset có Critical CAPA mở (BR-16-09) — không đợi submit | reads `ComplianceGateResult` từ IMM-16 |

Đặt tại `frontend/src/components/pm/`.

### 4.bis Compliance pre-flight gate banner (cross-module IMM-16 → IMM-08)

> 🆕 Vòng 16. Wire dead FE client `imm16.ts::checkAssetComplianceStatus` vào `PMWorkOrderCreateView.vue` làm pre-flight gate banner. **Contract đầy đủ ở `docs/imm-16/06_Frontend_Design.md §II.8`** — phần này chỉ ghi placement IMM-08-specific.

- **Vị trí:** banner render NGAY SAU panel `assetMeta` (sau block `<div v-if="assetMeta" …grid…>`, line ~172-179 hiện tại), TRƯỚC các field PM Schedule.
- **Trigger fetch:** reuse `watch(() => form.value.asset_ref, loadAssetMeta)` — gọi `checkAssetComplianceStatus(form.value.asset_ref)` bên trong `loadAssetMeta` (cùng nhịp với `frappe.client.get_value`), bọc try-catch (lỗi/403 → `gateResult.value = null`, banner ẩn, KHÔNG blank trang).
- **State mới:** `gateResult = ref<ComplianceGateResult|null>(null)`; reset về `null` khi `asset_ref` rỗng.
- **Disable nút:** AND `gateResult.value?.blocked !== true` vào `canSubmit` computed (line 59-64 hiện tại) HOẶC giữ reactive-throw lúc submit nhưng banner đã cảnh báo trước.
- **i18n:** dịch `reason.status` qua `formatters.translateStatus` (SSoT). KHÔNG hardcode `'Overdue'`/`'Critical'` literal — `'Overdue'→'Quá hạn'`.
- **a11y:** `role="alert"` + `aria-live="assertive"` + severity `warning` (amber, KHÔNG đỏ — đây là cảnh báo gate, server vẫn là enforcer cuối qua `gate_wo_submit`).
- **Parity:** chỉ render `result.blocked`/`result.reasons[]` — KHÔNG inline-compute membership; cùng SoT với `gate_wo_submit`.

---

## 5. Pinia store

File: `frontend/src/stores/imm08.ts`

```ts
// State (actual — stores/imm08.ts)
workOrders: PMWorkOrder[]
currentWO: PMWorkOrder | null
calendarEvents: PMCalendarEvent[]
calendarSummary: { total: number; completed: number; overdue: number; pending: number }
dashboardStats: PMDashboardStats | null
pmHistory: any[]
pagination: { page: number; total: number; total_pages: number; page_size: number }
loading: boolean
error: string | null

// Computed (getters)
overdueWOs: PMWorkOrder[]          // filter status === 'Overdue'
openWOs: PMWorkOrder[]             // filter status === 'Open'
checklistComplete: boolean         // every checklist result !== null
hasMinorFailure: boolean           // any result === 'Fail–Minor'
hasMajorFailure: boolean           // any result === 'Fail–Major'

// Actions (tên chính xác trong code)
fetchWorkOrders(filters?, page?): Promise<void>
fetchWorkOrder(name: string): Promise<void>
updateChecklistResult(idx: number, updates: Partial<ChecklistResult>): void
doAssignTechnician(name, technician, scheduledDate?): Promise<boolean>
doSubmitResult(summary, stickerAttached, durationMin): Promise<{ success: boolean; cmWoCreated?: string | null }>
doReportMajorFailure(description: string): Promise<string | null>
fetchCalendar(year: number, month: number): Promise<void>
fetchDashboardStats(year?, month?): Promise<void>
doReschedule(name, newDate, reason): Promise<boolean>
fetchPMHistory(assetRef: string): Promise<void>
```

**Persist policy:** Chỉ persist `pagination.page_size` và filter state — KHÔNG persist data record.

---

## 6. Vue Query keys

```ts
const keys = {
  dashboard: (year: number, month: number) => ['imm08', 'dashboard', year, month],
  list: (filters: Record<string, any>) => ['imm08', 'list', filters],
  detail: (name: string) => ['imm08', 'detail', name],
  calendar: (year: number, month: number) => ['imm08', 'calendar', year, month],
  history: (assetRef: string) => ['imm08', 'history', assetRef],
}
```

**Invalidate sau mutation:**
- `submitResult` → invalidate `list`, `detail(name)`, `dashboard`
- `assignTech` → invalidate `list`, `detail(name)`, `calendar`
- `reschedulePM` → invalidate `list`, `detail(name)`, `calendar`

---

## 6b. API call pattern — useApi().run()

```ts
import { useApi } from '@/composables/useApi'
import { submitPmResult } from '@/api/imm08'
import { useQueryClient } from '@tanstack/vue-query'

const api = useApi()
const qc = useQueryClient()
const formErrors = reactive<Record<string, string>>({})

async function onSubmitResult() {
  formErrors.value = {}
  const result = await api.run(
    () => submitPmResult({ name: wo.name, checklist_results: results, overall_result }),
    {
      successMessage: 'Đã hoàn thành phiếu bảo trì',
      onFieldError: (fields) => Object.assign(formErrors, fields),
    }
  )
  if (result) {
    qc.invalidateQueries({ queryKey: ['imm08', 'list'] })
    router.push('/pm/work-orders')
  }
}
```

---

## 7. Quy tắc ngôn ngữ FE

### 7.a. Nguyên tắc cứng
- 100% tiếng Việt mọi label, button, toast, error, placeholder
- KHÔNG dùng mã WO làm tiêu đề chính — hiển thị tên thiết bị trước
- Mã WO đặt nhỏ phía dưới, font-mono, `text-xs text-slate-500`

### 7.b. Entity display pattern

```
┌──────────────────────────────────────────┐
│ Máy thở Drager Evita V500 — ICU Khối A   │  ← H3 tên tự nhiên
│ PM-WO-2026-00001 · Quarterly             │  ← Mã code phụ
└──────────────────────────────────────────┘
```

### 7.c. Bảng từ ngữ chuẩn hóa

| Khái niệm | Tiếng Việt | Tránh từ |
|---|---|---|
| PM Work Order | Phiếu bảo trì | "WO", "Order" |
| PM Status: Open | Chờ thực hiện | "Open" |
| PM Status: In Progress | Đang thực hiện | "In Progress" |
| PM Status: Overdue | Quá hạn | "Overdue" |
| PM Status: Completed | Hoàn thành | "Completed" |
| PM Status: Halted–Major Failure | Dừng — Lỗi nghiêm trọng | "Halted" |
| PM Status: Cancelled | Đã hủy | "Cancelled" |
| PM Status: Pending–Device Busy | Chờ — Thiết bị bận | "Pending Busy" |
| overall_result: Pass | Đạt | "Pass" |
| overall_result: Fail | Không đạt | "Fail" |
| result: Fail–Minor | Lỗi nhỏ | "Fail-Minor" |
| result: Fail–Major | Lỗi nghiêm trọng | "Fail-Major" |
| Submit PM | Hoàn thành / Nộp kết quả | "Submit" |
| KPI `overdue_in_month` | Quá hạn trong tháng | "overdue (month)" |
| KPI `overdue` (global) | Quá hạn (toàn hệ thống) | "overdue (global)" |
| KPI `compliance_rate_pct == null` | — (N/A) | "compliance n/a" |

### 7.c.bis Reconcile với mockup `docs/fe/08-pm/` (BE = source of truth)

> Mockup HTML trong `docs/fe/08-pm/` dùng nhãn marketing (**Scheduled, Assigned**)
> KHÔNG khớp `PMStatus` enum thật trong `services/imm08.py`. **BE thắng.**
> FE PHẢI map theo BE enum, KHÔNG copy nhãn mockup làm `value`.

| Mockup label | PMStatus thật (BE) | Nhãn VI render |
|---|---|---|
| "Scheduled" / "Đã phân công" | `Open` (+ `assigned_to` != null) | Chờ thực hiện / Đã phân công |
| "Assigned" | KHÔNG tồn tại state riêng → vẫn `Open` | — |
| "In Progress" / "Đang thực hiện" | `In Progress` | Đang thực hiện |
| "Overdue" | `Overdue` (hoặc `is_late=true`) | Quá hạn |
| "Completed" / "Hoàn tất" | `Completed` | Hoàn thành |
| "Pending Device Busy" | `Pending–Device Busy` | Chờ — Thiết bị bận |
| "Halted" / "Major Failure → CM" | `Halted–Major Failure` | Dừng — Lỗi nghiêm trọng |

**Workflow button → state matrix (PM Detail):** nút chỉ hiện khi state khớp.

| State hiện tại | Nút khả dụng | API |
|---|---|---|
| `Open` (chưa assign) | Phân công KTV | `assignTechnician` |
| `Open` (đã assign) / `In Progress` | Lưu tiến độ · Hoàn tất PM · Báo lỗi nghiêm trọng → CM · Tạm dừng (thiết bị bận) | `submitPMResult` / `reportMajorFailure` / `reschedulePM` |
| `Overdue` | giống `Open` + cảnh báo escalate | — |
| `Completed` / `Halted–Major Failure` / `Cancelled` | (terminal — không nút action) | — |

### 7d. Linked / Cascade fields

**Cascade PM Work Order Detail:**
- `asset_ref` chọn → auto-fill `asset_category`, `risk_class`, `serial_no`
- `pm_schedule` chọn → auto-fill `pm_type`, `checklist_template`, `due_date`

```ts
watch(assetRef, () => {
  pmSchedule.value = null
  // reload PM Schedules for this asset
})
```

---

## 7e. FilterKeyError — banner lỗi bộ lọc **KHÔNG thay thế bảng** (AC-CR-79, 2026-07-27) 🔴 SPEC

> Hợp đồng BE: [`05_API_Specification.md §14`](./05_API_Specification.md). Mục này là phần FE bắt buộc **cùng vòng**.

### 7e.1 Hai lỗi FE đo được (verify @source 2026-07-27)

| # | Chỗ | Vấn đề |
|---|---|---|
| **F1** | `views/pm/PMWorkOrderListView.vue:251` | `v-else-if="store.error"` nằm **cùng chuỗi `v-if`** với `<template v-else>` chứa bảng ⇒ **có lỗi là bảng biến mất**. Người dùng đang xem 20 phiếu, đổi 1 bộ lọc sai → **trắng nội dung**. Đây đúng cái AC6 cấm. |
| **F2** | `views/pm/PMWorkOrderListView.vue:72-73` | `f.due_date_from = [dateFrom.value]` / `f.due_date_to = [dateTo.value]` — **2 khoá KHÔNG tồn tại ở BE** ⇒ mọi lần lọc khoảng ngày là **HTTP-500 THẬT** (probe P3, `05 §14.1`). Bộ lọc này **chưa từng chạy**. |

### 7e.2 Sửa F2 — dùng toán tử Frappe trên `due_date` (khoá ĐÃ whitelist)

```ts
// AC-CR-79 / ADR-IMM08-FILTERKEY-03: BE KHÔNG có khoá `due_date_from`/`due_date_to`
//   (gửi đi = HTTP-500 `Unknown column 'tabPM Work Order.due_date_from'`). Khoảng
//   ngày đi bằng toán tử trên cột THẬT `due_date` — `_normalize_filters` cho lọt
//   nguyên dạng mọi `[<op>, <v>]` với op ∈ _OP_TOKENS (services/imm08.py:447).
if (dateFrom.value && dateTo.value) f.due_date = ['between', [dateFrom.value, dateTo.value]]
else if (dateFrom.value)           f.due_date = ['>=', dateFrom.value]
else if (dateTo.value)             f.due_date = ['<=', dateTo.value]
```

⚠️ Đặt **sau** nhánh `overdue`/`due_before` hiện có và **chỉ khi** 2 nhánh đó không chạy — `overdue` và
`due_before` cũng ghi `due_date`/`status` ở BE; 2 nguồn cùng ghi 1 cột = kết quả không đoán được.
Kiểu `buildFilters()` phải nới thành `Record<string, string | string[] | (string | string[])[]>`.

### 7e.3 Sửa F1 — banner **cộng thêm**, không thay thế

| Điều kiện | Hiển thị |
|---|---|
| `store.error` **và** `store.workOrders.length > 0` | **Banner** `alert-error` phía **TRÊN** bảng · bảng **giữ nguyên dữ liệu cũ** · nút "Thử lại" |
| `store.error` **và** `store.workOrders.length === 0` | Khối lỗi chiếm-chỗ như hiện tại (không có gì để giữ) |
| `store.loading` | Skeleton (không đổi) |

```
<div v-if="store.loading">…skeleton…</div>
<template v-else>
  <div v-if="store.error" class="alert-error" role="alert">…{{ store.error }}… [Thử lại]</div>
  <div v-if="store.error && store.workOrders.length" class="text-xs …">
    Dữ liệu bên dưới là kết quả của lần lọc gần nhất thành công.
  </div>
  <ErrorBlock v-if="store.error && !store.workOrders.length" />
  <template v-else>…bảng + mobile card…</template>
</template>
```

**Bắt buộc:**
- Dùng **message của BE** (`store.error` = `err.message`, `stores/imm08.ts:36-40`) — **KHÔNG** chuỗi tự chế,
  **KHÔNG** map lại theo `code` (message BE đã nêu khoá sai + tập khoá hợp lệ, tiếng Việt).
- **KHÔNG logout** — `error.http_status = 400`, không phải 401; interceptor không được đụng.
- **KHÔNG** thêm `workOrders.value = []` vào `catch` của `fetchWorkOrders` (`stores/imm08.ts:74-76` hiện
  **đúng** — chỉ `_captureError`). Đây là hành vi phải **bảo tồn**, không phải sửa.
- **0 lỗi console**.

### 7e.4 Test RENDER bắt buộc (không chỉ test store)

`frontend/src/views/pm/pmFilterKeyError.test.ts`:

| TC | Kịch bản | Assert |
|---|---|---|
| FE-PMFK-1 | mount với `workOrders` = 3 dòng, rồi `fetchWorkOrders` reject `ApiError(msg, 'INVALID_PARAMS', 400)` | **3 dòng vẫn render** trong DOM + banner chứa `msg` |
| FE-PMFK-2 | như trên | `router.push`/logout **không** được gọi; `console.error` spy = 0 |
| FE-PMFK-3 | `workOrders` rỗng + lỗi | khối lỗi hiện, **không** crash, có nút "Thử lại" |
| FE-PMFK-4 | `dateFrom`+`dateTo` → `buildFilters()` | trả `{ due_date: ['between', [from, to]] }`, **không** chứa `due_date_from`/`due_date_to` |
| FE-PMFK-5 | chỉ `dateFrom` | `{ due_date: ['>=', from] }` |

DoD FE: `vue-tsc --noEmit` **0 lỗi** · `vitest run` **xanh** · **KHÔNG** `npm run build` (ghi thẳng
`assetcore/public/frontend` + `emptyOutDir` = deploy live trong khi BE còn stale — LL-DEPLOY-09).

---

## 8. Empty / Error / Loading copy

| Tình huống | Copy |
|---|---|
| List empty (no filter) | "Không có phiếu bảo trì nào. Scheduler sẽ tạo tự động khi đến hạn." |
| List empty (with filter) | "Không tìm thấy kết quả với bộ lọc hiện tại." |
| Checklist 0 items | "Checklist chưa được tạo. Vui lòng kiểm tra PM Checklist Template." |
| Submit success | "Đã hoàn thành phiếu bảo trì PM-WO-XXXX" |
| Loading list | Skeleton 5 dòng bảng |
| Loading detail | Skeleton 2 cột |
| Server error | "Lỗi hệ thống. Vui lòng thử lại hoặc liên hệ Admin." |
| Concurrent error | "Phiếu bảo trì đã được cập nhật bởi người khác. Vui lòng tải lại." |

---

## 9. Accessibility checklist module

- [ ] Nút "Hoàn thành PM" có `aria-label="Hoàn thành và nộp kết quả phiếu bảo trì"`
- [ ] Radio buttons checklist có `aria-describedby` link sang error text khi Fail-* thiếu notes
- [ ] Status badge có `role="status"` + text
- [ ] SLA countdown có `aria-live="polite"` — không announce mỗi giây
- [ ] `<html lang="vi">`
- [ ] Tap target ≥ 48px trên mobile (checklist radio buttons)
- [ ] Focus ring 2px emerald trên tất cả button/input

---

## 10. Responsive matrix

| Màn | Mobile (<640) | Tablet (640–1024) | Desktop (>1024) |
|---|---|---|---|
| Dashboard | KPI 1 cột | 2–3 cột | 5 cột + chart full |
| Calendar | Day view list | Week view | Month grid |
| List | Card list | Table 5 cột | Table full + filter sidebar |
| Detail | Checklist one-per-screen, swipe | Single column | 2 cột (info + checklist) |

---

## DoD — File 06 hoàn chỉnh

- [x] Sitemap đủ 8 route (dashboard + calendar + list + create + detail + schedules + templates)
- [x] 4 UI Mockup ASCII chính
- [x] Mỗi route có archetype + component chính
- [x] Sidebar nav config đầy đủ
- [x] Component custom liệt kê với props
- [x] Type definitions TypeScript đầy đủ trong §5 store
- [x] Vue Query keys chuẩn hóa + invalidate rule
- [x] API call pattern useApi().run()
- [x] Quy tắc ngôn ngữ 100% tiếng Việt
- [x] Bảng từ ngữ chuẩn hóa
- [x] Cascade fields khai báo
- [x] Empty / Error / Loading copy đủ
- [x] Accessibility checklist module
- [x] Responsive matrix

---

## Khuôn trạng thái màn danh sách — `AC-UX-047` lô 3 (cross-cutting, 2026-08-04)

Màn danh sách của module này áp **khuôn dùng chung** `frontend/src/components/ui/ListPageShell.vue`
(4 trạng thái LOẠI TRỪ: đang tải / lỗi + «Thử lại» / rỗng + hướng dẫn / có dữ liệu). Đặc tả **KHÔNG** lặp
ở đây — SSoT là Core Doc UI/UX:

| Mục | Nơi chốt |
|---|---|
| Hợp đồng props/slots/`data-testid` | [`docs/ui-ux/02_LIST_PAGE_SHELL.md §3`](../ui-ux/02_LIST_PAGE_SHELL.md) |
| Sổ lô 3 + delta từng file + bảng copy tiếng Việt | [`§14.2` / `§14.4`](../ui-ux/02_LIST_PAGE_SHELL.md) |
| Bất biến `INV-UX3-24…29` + test `TC-UX3-40 / TC-UX3-41` | [`§14.5` / `§14.6`](../ui-ux/02_LIST_PAGE_SHELL.md) |
| Guard adoption CHỈ-GIẢM (`AC-UX-070`) | `frontend/src/guards/listShellAdoption.guard.test.ts` |

- **Route thuộc lô 3 của module này:** `/pm/work-orders` · `/pm/schedules`
- **File view:** `views/pm/PMWorkOrderListView.vue` · `views/pm/PmScheduleListView.vue`
- **Ràng buộc riêng phải giữ:** xem cột «Bẫy riêng theo màn» ở [`§14.4`](../ui-ux/02_LIST_PAGE_SHELL.md) —
  lỗi **lượt nạp danh sách** là nguồn DUY NHẤT của `:error-message`; lỗi biểu mẫu / cảnh báo bộ lọc /
  hành động ghi **không** được lật trạng thái danh sách (`ADR-UX-24`).
