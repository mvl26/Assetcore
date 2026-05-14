# IMM-00 — UI/UX Guide (Foundation Layer)

| Thuộc tính | Giá trị |
|---|---|
| Module | IMM-00 Foundation |
| Tài liệu | UI/UX Guide |
| Phiên bản | 3.0.0 |
| Ngày cập nhật | 2026-04-18 |
| Trạng thái | **DRAFT** — chờ triển khai theo kiến trúc FE mới (Vue 3 + Frappe UI) |
| Tác giả | AssetCore Team |

---

## 0. Tổng quan

Tài liệu này đặc tả hệ thống UI/UX cho lớp nền IMM-00 của AssetCore. FE được xây trên **Vue 3 + TypeScript + Frappe UI**, **không dùng ERPNext Desk UI**. Toàn bộ 13 DocType của IMM-00 được render qua các màn hình tùy biến, bám sát nghiệp vụ HTM (Health Technology Management).

Người dùng mục tiêu:

- **IMM Technician** (KTV hiện trường — tablet / phone)
- **IMM Department Head / Operations Manager** (quản lý — desktop)
- **IMM QA Officer** (kiểm soát chất lượng — desktop, tra Audit Trail)
- **IMM System Admin** (cấu hình)

Khác biệt chính với v2:

- Bỏ hoàn toàn Asset Profile → dùng trực tiếp `AC Asset` với HTM fields first-class.
- Bỏ UI dạng Desk Form của ERPNext → viết lại Vue 3 shell.
- Prefix `AC-` / `IMM-` phản ánh trên mọi navigation label.

---

## 1. Nguyên tắc UX

| # | Nguyên tắc | Mô tả |
|---|---|---|
| 1.1 | Tiếng Việt mặc định | Mọi label, button, toast, error message dùng tiếng Việt. Fallback tiếng Anh qua i18n. |
| 1.2 | Mobile-responsive | KTV thao tác trên tablet / phone tại hiện trường. Breakpoint: `sm 640 / md 768 / lg 1024 / xl 1280`. |
| 1.3 | Offline-tolerant | Form ghi log PM và Incident hỗ trợ offline queue (IndexedDB) + auto-sync khi online. |
| 1.4 | Accessibility | WCAG 2.1 AA tối thiểu: contrast ≥ 4.5:1, focus ring rõ ràng, ARIA label, keyboard navigable. |
| 1.5 | Ít click | Thao tác phổ biến (log PM, tra asset bằng QR) ≤ 3 click. |
| 1.6 | An toàn mặc định | Destructive action (decommission, close CAPA) luôn có confirm modal. |
| 1.7 | Phản hồi tức thì | Optimistic UI cho action ngắn; loading skeleton cho list; toast tức thì. |
| 1.8 | Traceability hiển thị | Mọi màn detail đều có tab Audit Trail / Lifecycle. Người dùng luôn thấy ai — khi nào — làm gì. |
| 1.9 | Consistency | Cùng pattern cho List / Detail / Form / Tree xuyên suốt 13 DocType. |
| 1.10 | Đơn giản trước, mở rộng sau | Không overload field trên màn chính; advanced filter ẩn trong drawer. |

---

## 2. Design System

### 2.1 Color palette

| Token | Hex | Dùng cho |
|---|---|---|
| `--color-primary-500` | `#0E6FFF` | CTA chính, link, selected state |
| `--color-primary-600` | `#0957D1` | Hover primary |
| `--color-primary-50` | `#E8F1FF` | Background nhẹ, chip |
| `--color-success-500` | `#16A34A` | Thành công, Active, Calibrated |
| `--color-warning-500` | `#F59E0B` | Cảnh báo, PM đến hạn, ISO 17025 thiếu |
| `--color-danger-500` | `#DC2626` | Lỗi, Overdue, Out of Service, Critical |
| `--color-info-500` | `#0891B2` | Thông tin trung tính |
| `--color-neutral-900` | `#0F172A` | Text chính |
| `--color-neutral-600` | `#475569` | Text phụ |
| `--color-neutral-300` | `#CBD5E1` | Border |
| `--color-neutral-100` | `#F1F5F9` | Background section |
| `--color-neutral-0`   | `#FFFFFF` | Canvas |

Semantic trạng thái `AC Asset.lifecycle_status`:

| Trạng thái | Màu | Chip style |
|---|---|---|
| Planned | neutral-600 | outline |
| Commissioning | info-500 | soft |
| Active | success-500 | solid |
| Under Repair | warning-500 | soft |
| Out of Service | danger-500 | soft |
| Decommissioned | neutral-900 | outline dashed |

### 2.2 Typography

Font chính: **Inter** (fallback: Roboto, system-ui).

| Token | Size / Line-height | Dùng cho |
|---|---|---|
| `text-xs` | 12 / 16 | caption, helper text |
| `text-sm` | 14 / 20 | body phụ, label form |
| `text-base` | 16 / 24 | body chính |
| `text-lg` | 20 / 28 | heading section |
| `text-xl` | 24 / 32 | heading page |
| `text-2xl` | 30 / 38 | KPI number (dashboard) |

Weight: 400 regular, 500 medium (label), 600 semibold (heading), 700 bold (KPI).

### 2.3 Spacing scale

`4 / 8 / 12 / 16 / 24 / 32 / 48 / 64` px — dùng qua token `space-1…space-12`.

Gap grid: 16 (mobile) — 24 (desktop).

### 2.4 Component library

Dựa trên `frappe/frappe-ui` + mở rộng nội bộ `@assetcore/ui`.

| Component | Biến thể | Ghi chú |
|---|---|---|
| Button | primary / secondary / ghost / danger / icon | Có loading + disabled state |
| Input | text / number / textarea / password | Kèm label + helper + error slot |
| Select | single / multi / async search | Async gọi `/api/method/…` |
| DatePicker | single / range | Hỗ trợ locale vi |
| Table | sortable / selectable / sticky header | Virtual scroll ≥ 500 rows |
| Modal | default / confirm / fullscreen | ESC đóng, focus trap |
| Toast | success / warning / danger / info | 3s auto-dismiss (success); persistent (error) |
| Tabs | line / card | Deep-link qua query string `?tab=` |
| Tree | expandable, lazy-load | Dùng cho AC Location / AC Department |
| FileUpload | drag-drop, multi | Gắn Frappe File |
| Drawer | right / bottom | Dùng cho filter nâng cao, quick edit |
| Chip | status / severity / risk_class | Preset semantic color |
| Breadcrumb | auto từ route | Hỗ trợ truncation |
| Skeleton | list row / card / form | Dùng thay spinner |
| Timeline | vertical | Lifecycle Event, Audit Trail |

### 2.5 Icon set

**Lucide** (mặc định) + **Heroicons** (fallback cho icon đặc biệt). Size: 16 / 20 / 24.

---

## 3. App Shell

### 3.1 Layout tổng

```
┌───────────────────────────────────────────────────────────────────────┐
│ Topbar  [Logo AssetCore] [Search ⌘K]  ... [🔔 3] [👤 anh.doan ▾]     │
├──────────┬────────────────────────────────────────────────────────────┤
│          │ Breadcrumb: Trang chủ / Thiết bị / AC-ASSET-2026-00042     │
│ Sidebar  ├────────────────────────────────────────────────────────────┤
│          │                                                            │
│ • Dash   │              Main content area                             │
│ • Thiết  │              (list / detail / form)                        │
│   bị     │                                                            │
│ • NCC    │                                                            │
│ • Vị trí │                                                            │
│ • Khoa   │                                                            │
│ • Master │                                                            │
│ • Sự cố  │                                                            │
│ • CAPA   │                                                            │
│ • Audit  │                                                            │
│          │                                                            │
└──────────┴────────────────────────────────────────────────────────────┘
```

### 3.2 Sidebar — 8 nhóm điều hướng

| # | Nhãn | Icon | Route | Quyền tối thiểu |
|---|---|---|---|---|
| 1 | Dashboard | `layout-dashboard` | `/` | mọi IMM role |
| 2 | Thiết bị (AC Asset) | `package` | `/assets` | IMM Technician+ |
| 3 | Nhà cung cấp (AC Supplier) | `truck` | `/suppliers` | Storekeeper+ |
| 4 | Vị trí (AC Location) | `map-pin` | `/locations` | Ops Manager+ |
| 5 | Khoa / Department | `building-2` | `/departments` | Ops Manager+ |
| 6 | Master Data | `database` | `/master-data` | Workshop Lead+ |
| | — IMM Device Model | | `/master-data/device-models` | |
| | — AC Asset Category | | `/master-data/categories` | |
| | — IMM SLA Policy | | `/master-data/sla` | |
| 7 | Sự cố (Incident Report) | `alert-triangle` | `/incidents` | IMM Technician+ |
| 8 | CAPA | `shield-check` | `/capa` | QA Officer, Workshop Lead |
| 9 | Audit Trail | `file-lock` | `/audit-trail` | QA Officer, System Admin |

Menu ẩn item không có quyền (không grey-out). Collapse / expand sidebar toggle; trạng thái lưu trong `localStorage`.

### 3.3 Topbar

```
┌───────────────────────────────────────────────────────────────────────┐
│  [AC] AssetCore  │ 🔍 Tìm mã/UDI/tên thiết bị…  ⌘K │ 🔔⁽³⁾ │ 👤 ▾    │
└───────────────────────────────────────────────────────────────────────┘
```

- **Search (⌘K / Ctrl+K)**: global search, debounce 300ms, gọi `/api/method/assetcore.api.imm00.global_search`.
- **Notifications**: danh sách cảnh báo scheduler (CAPA overdue, contract expiry, BYT reg expiry).
- **User menu**: thông tin, role chip, Đăng xuất.

### 3.4 Auth guard

| Trạng thái | Hành vi |
|---|---|
| Chưa đăng nhập | Redirect `/login` (Frappe session cookie) |
| Đã đăng nhập, đủ role | Render route |
| Đã đăng nhập, thiếu role | Render `Forbidden403View` với CTA "Yêu cầu quyền" |
| API 401 | Xoá Pinia auth store, redirect `/login` |
| API 403 | Toast danger "Không có quyền thực hiện hành động này" |
| API 500 | `ErrorBoundary` với retry + error ID |

### 3.5 Breadcrumb

Auto sinh từ `route.meta.breadcrumb`. Max 4 cấp, cắt giữa ("…") nếu dài. Click mọi cấp trừ cấp cuối.

### 3.6 Trạng thái chung — Loading / Empty / Error

| State | Layout | Ghi chú |
|---|---|---|
| Loading | Skeleton row × 8 (list) / skeleton card (dashboard) | Không spinner |
| Empty | Icon + mô tả + CTA tạo mới | Ví dụ: "Chưa có AC Asset — [Tạo thiết bị mới]" |
| Error | Icon cảnh báo + error code + button Thử lại | Gửi lỗi lên Sentry |

---

## 4. Layout patterns

### 4.1 List view

```
┌─────────────────────────────────────────────────────────────────────┐
│ Tiêu đề danh sách                   [ + Tạo mới ]  [ Xuất Excel ▾ ] │
├───────────────┬─────────────────────────────────────────────────────┤
│ Filter sidebar│  Bulk: [ Gán kỹ thuật viên ] [ Đổi trạng thái ]     │
│               ├─────────────────────────────────────────────────────┤
│ Status    ▾   │  □  Mã            Tên        Khoa    Status   Next │
│ Lifecycle ▾   │  □  AC-ASSET-001  Máy MRI    CĐHA    Active   05/05│
│ Dept      ▾   │  □  AC-ASSET-002  Máy XN     XN      UnderRep 12/05│
│ Risk      ▾   │  …                                                 │
│ Next PM   📅  │                                                     │
│               │         [ ‹ 1 2 3 … 12 › ]       Hiển thị 20 / trang│
└───────────────┴─────────────────────────────────────────────────────┘
```

- Filter sidebar bên trái (desktop) / drawer (mobile).
- Table bên phải: sticky header, sortable column, multi-select.
- Pagination: server-side (`page`, `page_size`). Default `page_size=20`.
- Bulk action bar xuất hiện khi chọn ≥ 1 row.
- Export CSV / Excel qua API `/api/method/...export`.

### 4.2 Detail view

```
┌─────────────────────────────────────────────────────────────────────┐
│ ← AC-ASSET-2026-00042   [Active ●]           [ Sửa ]  [ Thao tác ▾ ]│
├─────────────────────────────────────────────────────────────────────┤
│ [Tổng quan] [Vòng đời] [PM & Cal] [Tài liệu] [Incident & CAPA] [Audit]│
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   Nội dung theo tab                                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

- Header: back button + mã + chip status + action cluster phải.
- Tabs deep-linkable: `?tab=lifecycle`.
- Action menu ▾: Decommission, Transfer, In QR, Xuất lý lịch.

### 4.3 Form view

```
┌─────────────────────────────────────────────────────────────────────┐
│ Tạo mới AC Asset                                                    │
├─────────────────────────────────────────────────────────────────────┤
│ §1 Định danh (UDI / GMDN / BYT)                                     │
│    [Mã UDI* ...................]  [GMDN ..........]                 │
│    [Số đăng ký BYT ...........]  [Hạn đăng ký  📅 ]                 │
│                                                                     │
│ §2 Phân loại                                                        │
│    [Device Model* ▾]  → (auto) class / risk / pm_interval           │
│                                                                     │
│ §3 Vị trí & Trách nhiệm                                             │
│ §4 Lịch bảo trì                                                     │
│ §5 Ghi chú                                                          │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ [ Huỷ ]                                [ Lưu nháp ] [ Lưu & Gửi duyệt ]│
└─────────────────────────────────────────────────────────────────────┘
```

- Sticky action bar ở đáy (mobile) / đỉnh (desktop khi scroll).
- Section break dùng heading `text-lg` + divider.
- Field required có dấu `*` đỏ.

### 4.4 Print-friendly view

Route `/print/:doctype/:name` với CSS `@media print`. Ẩn sidebar / topbar. Font size 11pt, màu chuyển grayscale. Dùng cho lý lịch thiết bị, CAPA form, Incident form.

---

## 5. Screen specs

Phần này đặc tả 13 màn chính của IMM-00.

### 5.1 Dashboard

Route: `/`

```
┌─────────────────────────────────────────────────────────────────────┐
│ Xin chào, anh.doan                                   18/04/2026     │
├─────────────────────────────────────────────────────────────────────┤
│ [Tổng AC Asset]  [PM đến hạn 7d]  [PM đến hạn 30d]  [CAPA Overdue] │
│      1,284             12               48                3         │
│ [Incident Open]  [Contract sắp hết]  [BYT reg sắp hết]              │
│      5                  7 (90d)            4 (90d)                  │
├─────────────────────────────────────────────────────────────────────┤
│ Biểu đồ: Asset theo lifecycle_status (donut)                        │
│ Biểu đồ: PM compliance theo tháng (line)                            │
├─────────────────────────────────────────────────────────────────────┤
│ Hoạt động gần đây (Lifecycle Event) — 10 dòng                       │
└─────────────────────────────────────────────────────────────────────┘
```

- KPI card click → filter list tương ứng (vd click "CAPA Overdue" → `/capa?status=Overdue`).
- Theo role ưu tiên khác nhau (xem §7).

### 5.2 AC Asset — List

Route: `/assets`

| Cột | Mô tả | Sort |
|---|---|---|
| `asset_code` | Mã AC-ASSET-… | ✓ |
| `asset_name` | Tên thiết bị | ✓ |
| `device_model` | Mã model | ✓ |
| `department` | Khoa | ✓ |
| `lifecycle_status` | Chip màu | ✓ |
| `next_pm_date` | Ngày PM kế tiếp | ✓ |
| `risk_class` | Chip Low/Med/High/Critical | ✓ |

Filter: `status`, `lifecycle_status`, `department`, `risk_class`, `next_pm_date` (range).

Bulk actions: Gán KTV, In QR hàng loạt, Xuất Excel.

Tìm kiếm nhanh: theo `asset_code`, `asset_name`, `udi`.

### 5.3 AC Asset — Detail

Route: `/assets/:name`

6 tab:

| Tab | Nội dung chính |
|---|---|
| 1. Info HTM | asset_code, UDI, GMDN, BYT reg, device_model, class, risk, custodian, location |
| 2. Vòng đời | Timeline Asset Lifecycle Event (xem §5.12) |
| 3. PM & Calibration | next_pm_date, pm_interval_days, next_calibration_date, lịch sử PM / Cal |
| 4. Tài liệu | Upload IQ/OQ/PQ, manual, biên bản — Frappe File |
| 5. Incident & CAPA | Danh sách Incident + CAPA liên quan, CTA tạo mới |
| 6. Audit Trail | Log immutable theo asset, button "Verify chain" |

Header action menu:

- **Tác nghiệp**: Đổi trạng thái (modal chọn transition hợp lệ), Transfer khoa, Decommission.
- **Tiện ích**: In QR, Xuất lý lịch (PDF).

### 5.4 AC Asset — Form (Create / Edit)

Route: `/assets/new`, `/assets/:name/edit`

Section:

| § | Label | Field |
|---|---|---|
| 1 | Định danh | `asset_code` (auto), `asset_name*`, `udi`, `gmdn_code`, `byt_reg_no`, `byt_reg_expiry` |
| 2 | Phân loại | `device_model*`, `asset_category` (auto từ model), `device_class` (readonly), `risk_class` (readonly) |
| 3 | Vị trí & Trách nhiệm | `department*`, `location`, `responsible_technician` |
| 4 | Lịch bảo trì | `pm_interval_days` (auto), `next_pm_date`, `next_calibration_date` |
| 5 | Ghi chú | `notes`, `attachments` |

Hành vi auto-fill khi chọn `device_model`:

```
on change device_model:
  GET /api/method/assetcore.api.imm00.get_device_model_defaults?model=...
  → apply: device_class, risk_class, pm_interval_days, asset_category
```

BR hiển thị:

- `BR-00-01` (class vs risk): toast warning nếu user sửa ngược chuẩn.
- `BR-00-06` (ISO 17025): không áp dụng ở đây (áp dụng ở Supplier).

### 5.5 AC Supplier — List + Form

Route: `/suppliers`, `/suppliers/new`, `/suppliers/:name`.

List columns: `supplier_code`, `supplier_name`, `vendor_type` (chip), `iso_17025_cert` (badge ✓ / ✗), `contract_end`, `status`.

Form section:

| § | Field |
|---|---|
| Cơ bản | supplier_code, supplier_name*, vendor_type* (Manufacturer / Distributor / Service Provider / Calibration Lab) |
| Pháp lý | tax_code, business_license, iso_17025_cert |
| Hợp đồng | contract_start, contract_end, contract_ref (file) |
| KTV uỷ quyền (child) | AC Authorized Technician inline table |

Banner cảnh báo (soft, amber) — khi `vendor_type = Calibration Lab` và thiếu `iso_17025_cert`:

```
⚠  Nhà cung cấp dạng Calibration Lab cần khai báo ISO/IEC 17025.
   Hiện tại đang thiếu chứng chỉ — không khuyến nghị sử dụng cho hiệu chuẩn.
```

### 5.6 AC Location — Tree view

Route: `/locations`

```
┌──────────────────────────┬──────────────────────────────────────────┐
│  Toà A                   │  Chi tiết vị trí                         │
│   └ Tầng 2               │  Mã: AC-LOC-2026-0042                    │
│     └ CĐHA        [sel]  │  Tên: Phòng CĐHA                         │
│       └ Phòng MRI        │  Loại khu vực: Diagnostic Imaging        │
│     └ Phòng CT           │  Infection control: Standard             │
│   └ Tầng 3               │  [Thiết bị tại đây: 12]                  │
│  Toà B                   │  [ Sửa ]  [ + Thêm vị trí con ]          │
└──────────────────────────┴──────────────────────────────────────────┘
```

- Tree bên trái (lazy load), detail panel bên phải.
- Drag-drop để đổi parent (chỉ System Admin + Ops Manager).
- Click "Thiết bị tại đây" → `/assets?location=AC-LOC-…`.

### 5.7 AC Department — Tree view

Cùng pattern §5.6, hiển thị trường: `department_code`, `department_name`, `parent_department`, `head_user`. Click "Thiết bị thuộc khoa" → `/assets?department=…`.

### 5.8 IMM Device Model — List + Form

Route: `/master-data/device-models`

List: `model_code`, `model_name`, `manufacturer`, `device_class`, `risk_class`, `pm_interval_days`.

Form section:

| § | Field |
|---|---|
| Định danh | model_code, model_name*, manufacturer*, gmdn_code |
| Phân loại | device_class (I/II/III)*, risk_class (auto BR-00-01), life_years |
| Bảo trì khuyến nghị | pm_interval_days*, calibration_interval_days |
| Phụ tùng | child table IMM Device Spare Part (part_no, name, supplier, qty) inline |
| Tài liệu | manual, IFU, datasheet (File) |

BR-00-01 enforce qua Select chain: chọn `device_class` → `risk_class` default theo bảng, có thể override nhưng phải xác nhận.

### 5.9 IMM SLA Policy — Matrix

Route: `/master-data/sla`

Hiển thị dạng ma trận 2 chiều `priority × risk_class`:

```
           │  Low      Medium     High       Critical
───────────┼────────────────────────────────────────────
  P1       │ 30/4h    15/2h      10/1h       5/30m
  P2       │ 60/8h    30/4h      20/2h      10/1h
  P3       │ 240/24h  120/12h    60/8h      30/4h
  P4       │ 480/72h  240/48h   120/24h     60/12h

  (Response minutes / Resolution time)
```

- Cell clickable → modal edit `response_time_minutes`, `resolution_time_hours`.
- BR-00-07: response < resolution × 60 → inline error đỏ trong modal.
- Row `is_default` highlight nền `primary-50`.

### 5.10 IMM Audit Trail — Log

Route: `/audit-trail`

**Read-only**. Không có nút Create / Edit / Delete (enforce cả trên perm BE + UI).

Filter: `asset`, `event_type`, `user`, `date_range`, `module`.

```
┌─────────────────────────────────────────────────────────────────────┐
│ Bộ lọc          │  [ Verify chain integrity 🔒 ]                    │
├──────────────────────────────────────────────────────────────────── │
│ Time     │ Module │ Event       │ Asset        │ User    │ Hash ✓  │
│ 10:42:11 │ IMM-08 │ pm_done     │ AC-ASSET-042 │ ktv01   │ a3f2…   │
│ 09:15:03 │ IMM-04 │ commissioned│ AC-ASSET-042 │ dhead01 │ 91bc…   │
└─────────────────────────────────────────────────────────────────────┘
```

Nút **Verify chain integrity** gọi `/api/method/assetcore.api.imm00.verify_audit_chain`:

- Spinner loading.
- Kết quả: modal hiển thị:
  - ✅ "Chain toàn vẹn — N entries, from HASH_0 to HASH_N"
  - ❌ "Phát hiện break tại entry #K, hash_prev không khớp" (kèm link tới entry).

Row click → drawer phải hiển thị raw payload JSON.

### 5.11 IMM CAPA — List + Form

Route: `/capa`, `/capa/new`, `/capa/:name`

List: `capa_code`, `title`, `severity` (chip), `status` (workflow bar), `due_date` (warn nếu < 7d), `assigned_to`.

Workflow status bar (top of form):

```
[ Open ] ──▶ [ Root Cause ] ──▶ [ Corrective ] ──▶ [ Verification ] ──▶ [ Closed ]
   ●            ●                  ○                ○                     ○
```

Section form:

| § | Field |
|---|---|
| Cơ bản | capa_code, title*, source (Incident / PM / Audit), severity* |
| Trách nhiệm | assigned_to*, due_date*, department |
| Phân tích | root_cause*, affected_assets (multi) |
| Hành động | corrective_action*, preventive_action, verification_plan |
| Đóng | verification_result, closed_by, closed_at |

Warning banner: nếu `due_date < today` → đỏ "CAPA quá hạn (BR-00-09)".

Close CAPA: confirm modal liệt kê checklist BR-00-08 (corrective + root_cause bắt buộc).

### 5.12 Asset Lifecycle Event — Timeline

Embedded trong AC Asset Detail tab "Vòng đời". Route chuyên biệt: `/assets/:name/lifecycle`.

Vertical timeline, màu theo `event_type`:

```
 │
 ●  2026-04-15 10:42   pm_completed       ktv01      (success)
 │     → Source: WO-PM-2026-0128
 │
 ●  2026-03-20 09:00   repair_opened      ktv02      (warning)
 │     → Source: IR-2026-0042
 │
 ●  2026-02-01 14:30   commissioned       dhead01    (info)
 │     → Source: ACC-2026-0015
 │
 ●  2026-01-20 08:00   planned            admin      (neutral)
```

- Click event → drawer phải show payload + link tới source record.
- Filter: event_type (multi), date range.

### 5.13 Incident Report — Wizard 3 bước

Route: `/incidents/new` (wizard), `/incidents`, `/incidents/:name`.

```
 Bước 1 / 3         Bước 2 / 3         Bước 3 / 3
 Thông tin cơ bản → Mức độ & Bệnh nhân → Hành động tức thời
 ─────────         ───────────         ───────────────────
```

**Bước 1 — Thông tin cơ bản**

| Field | Note |
|---|---|
| asset* | Select async, show asset chip |
| occurred_at* | DateTime picker |
| reported_by | Auto = session.user |
| short_description* | Textarea 200 char |

**Bước 2 — Mức độ & Bệnh nhân**

| Field | Note |
|---|---|
| severity* | Minor / Major / Critical |
| patient_affected | boolean |
| patient_injury_level | conditional (nếu patient_affected) |
| witnesses | Table (name, role) |

Khi `severity = Critical` AND `patient_affected = true`:

```
┌───────────────────────────────────────────────────────────────────┐
│ 🛑  BÁO CÁO BỘ Y TẾ BẮT BUỘC theo NĐ98/2021                       │
│     Hồ sơ phải được gửi trong 24h kể từ thời điểm xảy ra sự cố.   │
│     Hệ thống sẽ tự tạo CAPA và gán QA Officer sau khi Submit.     │
└───────────────────────────────────────────────────────────────────┘
```

**Bước 3 — Hành động tức thời**

| Field | Note |
|---|---|
| immediate_action* | textarea |
| asset_status_after | Select (Active / Out of Service / Under Repair) |
| create_capa | checkbox (auto-checked nếu Critical) |
| attachments | File upload |

Nút Submit → tạo Incident + (tuỳ chọn) CAPA + Lifecycle Event `failure_reported`.

---

## 6. Interaction patterns

### 6.1 Auto-save draft

Form dài (AC Asset, CAPA, Incident Wizard) auto-save vào `localStorage` mỗi 10s. Khi mở lại:

```
┌────────────────────────────────────────────────────────────┐
│ Phát hiện bản nháp lưu lúc 09:41 hôm nay.                  │
│   [ Khôi phục bản nháp ]    [ Bỏ qua ]                     │
└────────────────────────────────────────────────────────────┘
```

Key naming: `draft:<doctype>:<user>:<name|new>`. Xoá khi submit thành công.

### 6.2 Optimistic UI

Actions ngắn (toggle flag, gán KTV, bookmark) update UI ngay, rollback + toast nếu API lỗi.

### 6.3 Inline validation

- Validate on blur cho field cơ bản.
- Validate on submit cho BR (gọi BE).
- Lỗi BR hiển thị banner đỏ đầu form:

```
┌────────────────────────────────────────────────────────────┐
│ ❌  Có 2 lỗi cần sửa:                                      │
│    • BR-00-01: risk_class không phù hợp device_class       │
│    • BR-00-07: response_time phải nhỏ hơn resolution × 60  │
└────────────────────────────────────────────────────────────┘
```

### 6.4 Confirmation modal cho destructive

Triggers: Decommission asset, Close CAPA, Xoá Supplier, Ngừng Device Model.

Modal pattern:

```
┌────────────────────────────────────────────────────────────┐
│ Xác nhận ngừng sử dụng AC-ASSET-2026-00042                 │
├────────────────────────────────────────────────────────────┤
│ Thao tác này sẽ:                                           │
│   • Đổi lifecycle_status → Decommissioned                  │
│   • Huỷ toàn bộ PM/Calibration schedule còn pending        │
│   • Ghi 1 Asset Lifecycle Event bất biến                   │
│                                                            │
│ Nhập mã thiết bị để xác nhận: [___________________]        │
├────────────────────────────────────────────────────────────┤
│              [ Huỷ ]       [ Xác nhận ngừng ] (red)        │
└────────────────────────────────────────────────────────────┘
```

### 6.5 Keyboard shortcuts

| Phím | Hành động |
|---|---|
| `Ctrl+S` / `⌘+S` | Lưu form hiện tại |
| `Ctrl+K` / `⌘+K` | Mở global search |
| `Esc` | Đóng modal / drawer |
| `?` | Hiển thị cheat-sheet shortcut |
| `G` then `A` | Go to Assets |
| `G` then `D` | Go to Dashboard |

### 6.6 QR scan

Nút "Quét QR" trên topbar (mobile) + AC Asset list:

- Sử dụng `getUserMedia` + thư viện `@zxing/browser`.
- Parse QR payload (format: `AC-ASSET-YYYY-#####` hoặc full UDI).
- Điều hướng tới `/assets/:name` nếu tìm thấy, ngược lại toast "Không tìm thấy thiết bị".

---

## 7. Role-based UI

| Role | Sidebar | Dashboard ưu tiên | Action khả dụng |
|---|---|---|---|
| IMM Technician | Dashboard, Thiết bị, Sự cố | "PM của tôi", "Sự cố đang xử lý" | Quick Log PM, Tạo Incident |
| IMM QA Officer | Full + Audit Trail, CAPA | "CAPA Overdue", "Audit exceptions" | Verify chain, Close CAPA |
| IMM Department Head | Full (trừ Master Data edit) | "CAPA Overdue", "Contract 90d", "BYT reg 90d" | Approve transfer, Sign-off decommission |
| IMM Operations Manager | Full | "Asset utilization", "PM compliance" | Bulk assign KTV |
| IMM System Admin | Full + Settings | "System health" | Edit fixtures, Manage roles |

Enforce bằng 2 lớp:

1. **FE**: Pinia `authStore.hasRole()` — ẩn menu / disable button.
2. **BE**: Frappe Permission (`has_permission`) + custom `permission.py` — chặn data truy cập.

IMM Technician chỉ thấy AC Asset có `responsible_technician = session.user` (enforce BE). Trên UI, list cho "Chỉ thiết bị của tôi" là filter mặc định bật.

Form PM của IMM Technician có thêm khối **Quick Log**:

```
┌────────────────────────────────────────────────────────────┐
│  Ghi PM nhanh — AC-ASSET-2026-00042                        │
│  ┌──────────────┬─────────────────────────────────────┐   │
│  │ Checklist ✓  │  □ Kiểm tra nguồn   □ Vệ sinh       │   │
│  │              │  □ Hiệu chuẩn nội   □ Chạy test     │   │
│  ├──────────────┼─────────────────────────────────────┤   │
│  │ Kết quả      │ ( ) Pass  ( ) Pass w/ note  ( ) Fail │   │
│  │ Ghi chú      │ [______________________________]    │   │
│  │ Ảnh          │ [📷 Chụp]  [📎 Đính kèm]            │   │
│  └──────────────┴─────────────────────────────────────┘   │
│        [ Huỷ ]            [ Hoàn tất PM ]  (success)       │
└────────────────────────────────────────────────────────────┘
```

---

## 8. States & Feedback

### 8.1 Loading

- List / table: **skeleton rows** (8 dòng, shimmer animation).
- Card / KPI: skeleton block.
- Button action: spinner thay icon; disable button.
- **Không** dùng full-page spinner trừ route guard đầu tiên.

### 8.2 Empty state

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│               [ 📦 icon ]                                  │
│                                                            │
│       Chưa có AC Asset nào trong hệ thống.                 │
│       Tạo thiết bị đầu tiên để bắt đầu quản lý HTM.        │
│                                                            │
│                 [ + Tạo AC Asset ]                         │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

CTA nhất quán cho mọi list rỗng.

### 8.3 Error state

```
┌────────────────────────────────────────────────────────────┐
│   ⚠  Không thể tải dữ liệu                                │
│                                                            │
│   Mã lỗi: ERR-IMM00-5003                                   │
│   Chi tiết: Connection timeout                             │
│                                                            │
│        [ Thử lại ]   [ Gửi báo cáo lỗi ]                  │
└────────────────────────────────────────────────────────────┘
```

- Error ID hiển thị để support đối chiếu log.

### 8.4 Toast

| Loại | Màu | Thời lượng | Vị trí |
|---|---|---|---|
| success | green | 3s | top-right |
| info | blue | 3s | top-right |
| warning | amber | 5s | top-right |
| danger | red | persistent (có X close) | top-right |

Tối đa 3 toast đồng thời; FIFO nếu vượt.

---

## 9. Form validation UX

### 9.1 Pattern cơ bản

| Thành phần | Style |
|---|---|
| Required | Dấu `*` đỏ ngay sau label |
| Inline error | Text đỏ 12px, icon ⚠ dưới field |
| Success | Border xanh, icon ✓ phải field |
| Disabled | Nền neutral-100, tooltip lý do khi hover |

### 9.2 Business Rule display

BR-level error: banner đỏ đầu form, liệt kê mã BR (`BR-00-xx`), link tới docs BR.

BR-level warning (soft): banner amber, cho phép submit. Ví dụ BR-00-06 ISO 17025 thiếu.

### 9.3 Field disabled với lý do

```
[  next_pm_date  📅  (disabled)  ]   ⓘ
                                     ▲
                          ┌────────────────────────┐
                          │ Thiết bị đang Under    │
                          │ Repair — không thể đặt │
                          │ lịch PM.                │
                          └────────────────────────┘
```

### 9.4 Async validation

Vd `asset_code` unique check: debounce 400ms, spinner nhỏ phải field, sau đó ✓ hoặc ✗.

### 9.5 Server error mapping

BE trả về `_err(msg, code)` → FE:

- `code` bắt đầu `FIELD_*` → gán vào field tương ứng (inline).
- `code` bắt đầu `BR_*` → banner BR.
- `code` khác → toast danger.

---

## 10. Tech stack FE

### 10.1 Core

| Công nghệ | Version mục tiêu | Ghi chú |
|---|---|---|
| Vue | 3.4+ (Composition API) | script setup, `<script setup lang="ts">` |
| TypeScript | 5.3+ strict | `"strict": true`, `"noImplicitAny": true` |
| Frappe UI | `frappe/frappe-ui` latest | Button, Dialog, FormControl, ListView… |
| Vite | 5+ | Dev server, build |
| PNPM | 8+ | Workspace monorepo |

### 10.2 State & Routing

| Thư viện | Role |
|---|---|
| Pinia | Global state: `authStore`, `uiStore`, `notifStore` |
| Vue Router 4 | File-based routing (unplugin-vue-router) |
| VueUse | Hook tiện ích (`useLocalStorage`, `useEventListener`) |

### 10.3 API layer

- Axios wrapper `/src/api/client.ts`:
  - Base URL: `/api/method/`
  - Interceptor: `X-Frappe-CSRF-Token`, cookie session.
  - Response parse `{ message: {...} }` → trả `data` / throw `ApiError`.
- Endpoints: `assetcore.api.imm00.*`:
  - `get_asset`, `list_assets`, `create_asset`, `update_asset`
  - `transition_asset_status`
  - `verify_audit_chain`
  - `get_device_model_defaults`
  - `global_search`
  - `list_capa`, `close_capa`
  - `list_incidents`, `create_incident`

### 10.4 Form

| Thư viện | Role |
|---|---|
| vee-validate 4 | Form state, validate on blur / submit |
| zod | Schema validation TS-first |
| @vueuse/integrations | date, clipboard |

Pattern:

```ts
const schema = z.object({
  asset_name: z.string().min(1, 'Bắt buộc'),
  device_model: z.string().min(1, 'Chọn Device Model'),
  udi: z.string().regex(/^[\dA-Z\-]{8,}$/, 'UDI không hợp lệ').optional()
})
```

### 10.5 i18n

`vue-i18n@9`:

- Locale mặc định: `vi`.
- Fallback: `en`.
- Key namespace theo screen: `assets.list.title`, `capa.form.severity`.
- File: `/src/locales/vi.json`, `/src/locales/en.json`.

### 10.6 Cấu trúc thư mục FE

```
frontend/
├─ src/
│  ├─ api/            axios client + endpoint groups
│  ├─ components/     shared UI (Button, Chip, Timeline, …)
│  ├─ composables/    useAuth, usePagination, useOffline
│  ├─ layouts/        AppShell, AuthLayout, PrintLayout
│  ├─ locales/        vi.json, en.json
│  ├─ pages/          file-based routes
│  │  ├─ index.vue            (Dashboard)
│  │  ├─ assets/
│  │  ├─ suppliers/
│  │  ├─ locations/
│  │  ├─ departments/
│  │  ├─ master-data/
│  │  ├─ incidents/
│  │  ├─ capa/
│  │  └─ audit-trail/
│  ├─ stores/         authStore, uiStore, notifStore
│  ├─ utils/          formatDate, qrScan, offlineQueue
│  └─ main.ts
├─ index.html
├─ vite.config.ts
├─ tsconfig.json
└─ package.json
```

### 10.7 Build & deploy

- Build: `pnpm build` → output `dist/` → mount tại `/assets/assetcore/frontend`.
- Dev: `pnpm dev` proxy `/api` → bench `http://localhost:8000`.
- Offline queue: `navigator.serviceWorker` + IndexedDB, scope `/assets/assetcore/frontend/`.

---

## 11. Accessibility checklist

| # | Yêu cầu | Kiểm tra |
|---|---|---|
| A11Y-1 | Contrast AA | axe-core CI |
| A11Y-2 | Keyboard navigable | Tab qua mọi interactive element |
| A11Y-3 | Focus visible | Ring 2px primary-500 |
| A11Y-4 | ARIA labels | Icon-only button bắt buộc `aria-label` |
| A11Y-5 | Form error `aria-describedby` | link input → error id |
| A11Y-6 | Modal focus trap | ESC đóng, focus trả về trigger |
| A11Y-7 | Table row semantic | `<th scope="col">` |
| A11Y-8 | Language attr | `<html lang="vi">` |

---

## 12. Responsive breakpoint matrix

| Màn | Mobile (<640) | Tablet (640-1024) | Desktop (>1024) |
|---|---|---|---|
| Dashboard | KPI 1 cột | 2 cột | 4 cột |
| List | Card list (thay table) | Table cơ bản | Table + filter sidebar |
| Detail | Tab dọc (accordion) | Tab ngang | Tab ngang |
| Form | 1 cột | 2 cột | 2 cột + sticky action |
| Tree | Drawer full-screen | 50/50 | 30/70 |
| Incident Wizard | Step full screen | Step + progress bar | Step + progress + sidebar tóm tắt |

---

## 13. Liên quan tài liệu khác

| Tài liệu | Nội dung |
|---|---|
| `IMM-00_Module_Overview.md` | Kiến trúc tổng, 13 DocType |
| `IMM-00_Technical_Design.md` | Data dictionary, DocType JSON |
| `IMM-00_Functional_Specs.md` | Use case, workflow |
| `IMM-00_API_Interface.md` | Endpoint `/api/method/assetcore.api.imm00.*` |
| `IMM-00_Setup_Guide.md` | Cài đặt, fixtures, permission |

---

## 14. Changelog

| Version | Ngày | Thay đổi |
|---|---|---|
| 1.0.0 | 2025-12-10 | Bản đầu, ERPNext Desk UI |
| 2.0.0 | 2026-02-05 | Đã có Asset Profile, Vue 3 PoC |
| **3.0.0** | **2026-04-18** | **Reset theo kiến trúc 13 DocType (AC/IMM prefix), bỏ Profile, chuẩn hoá Frappe UI, thêm wizard Incident 3 bước, role-based UI chi tiết, offline queue, WCAG 2.1 AA** |
