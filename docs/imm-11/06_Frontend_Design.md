# 06 — Thiết kế Frontend (Frontend Design / UI-UX Guide)

| Mục | Giá trị |
|---|---|
| Module | IMM-11 — Hiệu chuẩn (Calibration) |
| Phạm vi | Per-module |
| Owner | FE Lead + Designer |
| Module accent | `cyan-600` |
| Cập nhật | 2026-05-18 |
| Trạng thái | ✅ Live — Vue components đã build |

---

## 1. Sitemap / Route map

Routes and component names are based on **actual Vue files** in `frontend/src/views/calibration/`.

> Path prefix thực tế là `/calibration/...` (xem `frontend/src/router/index.ts`). Module key `imm11` được map qua regex `/^\/calibration/` → `imm11` để chuyển sidebar.

| Route (actual) | Tên trang | Archetype | Role | Vue Component (actual filename) |
|---|---|---|---|---|
| `/calibration/dashboard` | Bảng điều khiển | Dashboard | All | `views/calibration/CalibrationDashboard.vue` |
| `/calibration` | Danh sách phiếu | List | All | `views/calibration/CalibrationListView.vue` |
| `/calibration/new` | Tạo phiếu mới | Form | Workshop Lead, Technician | `views/calibration/CalibrationCreateView.vue` |
| `/calibration/schedules` | Lịch hiệu chuẩn | List | Workshop Lead | `views/calibration/CalibrationScheduleListView.vue` |
| `/calibration/:id` | Chi tiết phiếu | Detail | All | `views/calibration/CalibrationDetailView.vue` |

> CAPA list/detail (CAPAListView/CAPADetailView) thuộc folder `views/incident/` và phục vụ IMM-12; IMM-11 hiển thị CAPA dạng panel/inline trong `CalibrationDetailView` (không có route CAPA riêng cho IMM-11).

---

## 2. Sidebar nav module

```ts
// frontend/src/constants/modules.ts — entry imm11
{
  id: 'imm11', code: 'IMM-11',
  label: 'Hiệu năng & Hiệu chuẩn',
  description: 'Inspection, calibration, certificate, fail/out-of-tolerance',
  icon: 'gauge',
  to: '/calibration/dashboard',
  roles: TECH_ROLES,
}
```

---

## 3. Thiết kế giao diện

### 3.a. UI Mockup (pre-build) ⚠️ Mockup only

#### Mockup 1: CalibrationDashboard

```
┌──────────────────────────────────────────────────────────────────┐
│  IMM-11 — Bảng điều khiển Hiệu chuẩn          Tháng 04/2026 [▼] │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│ Compliance   │ OOT Rate     │ CAPA Open    │ Avg Days Sent→Cert  │
│ Rate         │              │              │                     │
│  87.5%       │   4.2%       │     3        │    12 ngày          │
│  ████████▒   │   ▒          │  [!]         │  ←────────────→    │
├──────────────┴──────────────┴──────────────┴─────────────────────┤
│  Thiết bị đến hạn trong 30 ngày                  [Xem tất cả →] │
│  🔴 Overdue (2)                                                   │
│  • Máy thở Drager V500 [ACC-001] — Quá hạn 15 ngày [Tạo CAL]   │
│  🟡 Due Soon (5)                                                  │
│  • Máy đo SpO2 Masimo  [ACC-005] — Còn 7 ngày    [Tạo CAL]     │
├──────────────────────────────────────────────────────────────────┤
│  CAPA Đang Mở                                  [Xem tất cả →]   │
│  • CAPA-2026-00015 — ACC-008 — Lookback Pending  [QA Review]    │
└──────────────────────────────────────────────────────────────────┘
```

#### Mockup 2: CalibrationList

```
┌──────────────────────────────────────────────────────────────────┐
│  PHIẾU HIỆU CHUẨN                            [+ Tạo phiếu mới]  │
│  Trạng thái [Tất cả ▼] · Loại [Tất cả ▼] · Thiết bị [...] 🔍   │
│  ──────────────────────────────────────────────────────────────  │
│  Mã phiếu      Thiết bị             Loại      Trạng thái  Hạn   │
│  ──────────────────────────────────────────────────────────────  │
│  CAL-2026-001  Sysmex XN-1000       External  📅 Đã lên lịch    │
│  CAL-2026-002  Máy thở Drager       External  🚚 Tại Lab  20/04 │
│  CAL-2026-003  ECG Nihon Kohden     In-House  ⚙️ Đang đo  —     │
│  CAL-2026-004  Monitor BP Mindray   External  ✅ Đạt      24/04 │
│  ──────────────────────────────────────────────────────────────  │
│  Hiển thị 1–20 / 145                          [Trước 1 2 Sau]   │
└──────────────────────────────────────────────────────────────────┘
```

#### Mockup 3: CalibrationForm (create/edit)

```
┌──────────────────────────────────────────────────────────────────┐
│ [← Quay lại]  Phiếu Hiệu chuẩn  CAL-2026-00001  [📅 Đã lên lịch]│
│                                                [Lưu]  [Submit]  │
├──────────────────────────────────────────────────────────────────┤
│ SECTION 1: Thông tin chung                                       │
│  Thiết bị *          [Sysmex XN-1000 🔍]  Model: IMM-MDL-001    │
│  Loại hiệu chuẩn *   ( ) External  (•) In-House                 │
│  KTV thực hiện *     [Nguyễn Văn A 🔍]                           │
│  Ngày đến hạn        [2026-05-01] (read-only)                    │
├──────────────────────────────────────────────────────────────────┤
│ SECTION 2: Lab (chỉ hiện khi External)                           │
│  Tổ chức kiểm định * [Trung tâm Đo lường 3 🔍]                   │
│  Số công nhận ISO *  [VLAS-T-028]                                │
│  Ngày gửi            [2026-04-20] 📅                             │
│  Ngày cấp chứng chỉ *[2026-04-24] 📅                             │
│  Upload Certificate * [📄 Drag & Drop PDF]                       │
├──────────────────────────────────────────────────────────────────┤
│ SECTION 3: Kết quả đo lường                                      │
│  Tham số   ĐV    Danh định  Tol(+) Tol(-) Đo được    Kết quả   │
│  WBC Count 10³/µ 7.5        ±3%    ±3%    [7.6]      ✅ Đạt    │
│  HGB       g/dL  14.0       ±3%    ±3%    [14.8]     ❌ Không đạt│
│  [+ Thêm tham số]                 Kết quả tổng: ❌ KHÔNG ĐẠT     │
└──────────────────────────────────────────────────────────────────┘
```

#### Mockup 4: Submit Confirmation (Fail path)

```
┌──────────────────────────────────────────────────────────────────┐
│  ⚠️  CẢNH BÁO — Kết quả KHÔNG ĐẠT                               │
│                                                                  │
│  1/3 tham số NGOÀI DUNG SAI: HGB (đo 14.8, danh định 14.0 ±3%) │
│                                                                  │
│  Khi Submit:                                                     │
│  • Thiết bị → "Ngưng sử dụng"                                   │
│  • CAPA Record được tạo tự động                                  │
│  • Lookback assessment cho 3 thiết bị cùng model                │
│  • Thông báo gửi QA Officer và Trưởng phòng                     │
│                                                                  │
│  ☐ Tôi xác nhận hành động này                                   │
│                        [Hủy bỏ]  [Xác nhận Submit →]           │
└──────────────────────────────────────────────────────────────────┘
```

---

### 3.c. Trang chi tiết theo archetype

#### 3.1. Dashboard (`/calibration/`)

| Filter / KPI | Type | Default |
|---|---|---|
| Kỳ báo cáo | DateRange | Tháng hiện tại |
| Compliance Rate | KPI card | % với progress bar |
| OOT Rate | KPI card | % (danger nếu > 5%) |
| CAPA Open | KPI card | Count với warning icon |
| Thiết bị quá hạn | List | Sort by days_overdue DESC |

**API gọi:** `get_calibration_dashboard` + `get_due_calibrations` — cache TTL 5 phút.

**State:**
- Loading: Skeleton 4 KPI card + skeleton list
- Empty: "Chưa có dữ liệu hiệu chuẩn — bắt đầu bằng cách tạo phiếu đầu tiên"

#### 3.2. List (`/calibration/list`)

| Filter | Type | Default |
|---|---|---|
| Trạng thái | MultiSelect | Tất cả |
| Loại | Select | Tất cả |
| Thiết bị | LinkSearch | — |
| Khoảng thời gian | DateRange | 30 ngày |

**Columns:** Mã phiếu · Thiết bị (tên + mã) · Loại · Trạng thái badge · KTV · Hạn · Kết quả

#### 3.3. Detail (`/calibration/:id`) — Workflow stepper + action buttons (SINGLE SOURCE cho FE)

State machine BE thật (khớp `imm_11_calibration_workflow.json`). 8 state:
`Scheduled / In Progress / Sent to Lab / Certificate Received / Passed / Failed / Conditionally Passed / Cancelled`. KHÔNG có state "Submitted" (mockup HTML cũ sai — bỏ).

Hai luồng: **In-House** (`Scheduled → In Progress → Passed/Failed/Conditionally Passed`) và **External/Lab** (`Scheduled → Sent to Lab → Certificate Received → Passed/Failed/Conditionally Passed` qua phê duyệt).

| Status hiện tại | Nút hiển thị (label VN) | Action API | Transition | Role allowed |
|---|---|---|---|---|
| Scheduled | "Bắt đầu hiệu chuẩn" | `submit_calibration`/update | Scheduled → In Progress | Calibration User |
| Scheduled | "Gửi phòng hiệu chuẩn" | `send_to_lab` | Scheduled → Sent to Lab | Calibration User |
| Scheduled | "Hủy lịch" | `cancel_calibration` | Scheduled → Cancelled | System Manager |
| In Progress | "Đạt" | `submit_calibration(result=Passed)` | In Progress → Passed | Calibration User |
| In Progress | "Không đạt → sinh CAPA" | `submit_calibration(result=Failed)` | In Progress → Failed | Calibration User |
| In Progress | "Đạt có điều kiện" | `submit_calibration(result=Conditionally Passed)` | In Progress → Conditionally Passed | Calibration User |
| In Progress | "Hủy hiệu chuẩn" | `cancel_calibration` | In Progress → Cancelled | System Manager |
| Sent to Lab | "Nhận chứng chỉ" | `receive_certificate` | Sent to Lab → Certificate Received | Calibration User |
| Certificate Received | "Phê duyệt đạt / không đạt / có điều kiện" | (workflow approve) | Certificate Received → Passed/Failed/Conditionally Passed | System Manager |
| Failed | "CAPA hoàn tất → chuyển có điều kiện" | (workflow) | Failed → Conditionally Passed | Compliance Manager / System Manager |

> BR-11-02: `Failed` → tự sinh CM Work Order (IMM-09) + lookback. Nút "Không đạt" phải cảnh báo trước khi commit.

---

## 4. Component custom của module

| Component | Mục đích | Props |
|---|---|---|
| `MeasurementTable` | Nhập kết quả đo với tolerance indicator realtime | `measurements, readonly, showTolerance` |
| `CertificateUploader` | PDF upload + preview inline | `modelValue, acceptTypes, maxSizeMB` |
| `LookbackPanel` | Hiển thị assets cùng model khi Fail + action Cleared/Action Required | `capaName, lookbackAssets` |
| `CalibrationStatusBadge` | Badge màu trạng thái CAL | `status: CalibrationStatus` |
| `ComplianceKPICard` | Card KPI compliance rate, OOT rate | `title, value, target, unit` |
| `CalibrationTimeline` | Timeline lịch sử cal của 1 asset | `assetName` |

---

## 5. Pinia store

**File:** `frontend/src/stores/imm11.ts` ✅ LIVE

**Actual state (useImm11Store):**
- `calibrations: AssetCalibration[]`
- `pagination: { total, page, page_size, total_pages }`
- `loading: boolean`
- `error: string | null`
- `schedules: CalibrationSchedule[]`
- `schedulesLoading: boolean`
- `kpis: CalibrationKpis | null`
- `kpisLoading: boolean`
- `dueItems: DueCalibrationItem[]`

**Actual actions:** `fetchList(params)`, `fetchSchedules(filters)`, `fetchKpis(year?, month?)`, `fetchDue()`

**Persist policy:** No persistence (no `persist` option set).

---

## 6. API client

**File:** `frontend/src/api/imm11.ts` ✅ LIVE

Base URL: `/api/method/assetcore.api.imm11`

**Exported functions (actual):**
- `listCalibrationSchedules(filters, page, pageSize)` → `{data: CalibrationSchedule[], pagination}`
- `getCalibrationSchedule(name)`
- `createCalibrationSchedule(payload)`
- `updateCalibrationSchedule(name, data)`
- `deleteCalibrationSchedule(name)`
- `listCalibrations(filters, page, pageSize)` → `{data: AssetCalibration[], pagination}`
- `getCalibration(name)` → `AssetCalibration`
- `createCalibration(payload)`
- `updateCalibration(name, data)`
- `submitCalibration(name)` → `{name, status, overall_result, next_calibration_date}`
- `getCalibrationKpis(year?, month?)` → `CalibrationKpis`
- `getAssetCalibrationHistory(asset, limit)` → `{asset, history}`
- `sendToLab(name, payload)` → `{name, status, sent_date}`
- `receiveCertificate(name, payload)` → `{name, status, certificate_number}`
- `cancelCalibration(name, reason)` → `{name, status}`
- `getDueCalibrations(days, limit)` → `{items: DueCalibrationItem[], threshold_days}`

## 6b. API call pattern

```ts
import { submitCalibration } from '@/api/imm11'

async function onSubmit() {
  const result = await submitCalibration(calName.value)
  if (result.overall_result === 'Failed') {
    // CAPA chi tiết thuộc IMM-12; chuyển sang route đó
    router.push(`/capa/${result.capa_created}`)
  } else {
    router.push(`/calibration/${result.name}`)
  }
}
```

---

## 7. Quy tắc ngôn ngữ FE

### 7.a. Nguyên tắc cứng
- 100% tiếng Việt mọi label, button, message, toast, placeholder, tooltip
- Mã phiếu (CAL-YYYY-NNNNN) hiển thị nhỏ phía dưới, font-mono, `text-xs text-slate-500`
- Trạng thái tiếng Anh (Passed, Failed) map qua i18n → hiển thị tiếng Việt

### 7.b. Pattern hiển thị thực thể
```
Sysmex XN-1000 Huyết học tự động              ← H3, font-semibold
AC-ASSET-2026-00101 · S/N: SYSMEX-XN-001      ← text-xs text-slate-500 font-mono
```

### 7.c. Bảng từ ngữ chuẩn hóa

| Khái niệm | Tiếng Việt | Tránh từ |
|---|---|---|
| IMM Asset Calibration | Phiếu hiệu chuẩn | Calibration record, Lệnh, Phiếu kiểm |
| Passed | Đạt | Pass, OK |
| Failed | Không đạt | Fail, Hỏng |
| Conditionally Passed | Đạt có điều kiện | — |
| Sent to Lab | Đang tại lab | Gửi đi |
| Certificate Received | Đã nhận chứng chỉ | Cert arrived |
| Out of Tolerance | Ngoài dung sai | OOT, Lỗi |
| Lookback Assessment | Đánh giá hồi cứu | Lookback |

### 7d. Cascade fields

Field `device_model` auto-populate từ `asset`. Field `lab_supplier` reset khi `calibration_type` đổi.

```ts
watch(() => form.asset, async (newAsset) => {
  if (newAsset) {
    const assetData = await fetchAssetInfo(newAsset)
    form.device_model = assetData.device_model
    form.next_calibration_date = assetData.next_calibration_date
  }
})
watch(() => form.calibration_type, () => {
  form.lab_supplier = null
  form.certificate_file = null
})
```

---

## 8. Empty / Error / Loading copy

| Tình huống | Copy |
|---|---|
| Danh sách rỗng | "Chưa có phiếu hiệu chuẩn — hãy tạo phiếu đầu tiên" |
| Filter không có kết quả | "Không có phiếu nào khớp với bộ lọc" |
| Không có quyền | "Bạn không có quyền xem dữ liệu này" |
| Loading | Skeleton 5 hàng table |
| Server error | Toast đỏ "Có lỗi xảy ra — vui lòng thử lại" + nút Thử lại |
| Submit thành công (Pass) | Toast xanh "Phiếu hiệu chuẩn đã Submit — kết quả: Đạt" |
| Submit thành công (Fail) | Toast cam "Thiết bị Không Đạt — CAPA đã được tạo tự động" |

---

## 9. Accessibility checklist module

- [ ] `MeasurementTable` row Fail có `role="alert"` + aria-label mô tả tham số lỗi
- [ ] Submit button disabled khi form chưa hợp lệ + `aria-disabled="true"`
- [ ] `CalibrationStatusBadge` có `aria-label="Trạng thái: Đạt"` (không chỉ dùng màu)
- [ ] Modal "Xác nhận Submit Fail" có focus trap + Escape đóng modal
- [ ] PDF iframe có `title="Calibration Certificate"` cho screen reader

---

## DoD — File 06 hoàn chỉnh

- [x] Sitemap — actual Vue files: CalibrationDashboard.vue · CalibrationListView.vue · CalibrationCreateView.vue · CalibrationDetailView.vue · CalibrationScheduleListView.vue · CAPAListView.vue · CAPADetailView.vue
- [x] UI Mockup ≥ 4 mockup chính (Dashboard, List, Form, Confirm Dialog)
- [x] Sidebar nav config
- [x] Archetype dashboard + list + form có specs
- [x] Component custom liệt kê (6 components)
- [x] ✅ Pinia store — `stores/imm11.ts` (useImm11Store) implemented
- [x] ✅ API client — `api/imm11.ts` với 16 exported functions
- [x] Quy tắc ngôn ngữ FE + bảng từ ngữ chuẩn hóa
- [x] Cascade fields khai báo
- [x] Empty / Error / Loading copy
- [x] Accessibility checklist
- [ ] UI Screenshot post-build
- [ ] Reviewed bởi FE Lead + Designer + BA
