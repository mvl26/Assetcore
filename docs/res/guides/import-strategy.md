# AssetCore — Chiến lược Import Dữ liệu Hàng loạt

> Phiên bản: 2026-05-18  
> Phạm vi: AC Asset, AC Supplier, IMM Device Model, Service Contract, SLA Policy, AC Department, AC Location, AC Asset Category, AC Spare Part, AC Warehouse, Frappe User

---

## 1. Frappe đã có gì sẵn?

Frappe v15 cung cấp **Data Import** — một tính năng built-in hoàn chỉnh:

| Thành phần | Mô tả |
|---|---|
| `frappe/core/doctype/data_import/` | DocType ghi nhận mỗi lần import |
| `importer.py` (1 283 dòng) | Engine parse CSV/XLSX, map cột, validate, insert/update |
| `exporter.py` | Sinh template CSV từ schema DocType |
| Background job | `enqueue_import()` → chạy async, không block UI |
| WebSocket | Broadcast tiến trình realtime đến client |
| Data Import Log | Ghi kết quả từng dòng (thành công / lỗi + message) |

**Luồng mặc định:**

```
User → Frappe /data-import UI
  → Chọn DocType + upload file
  → Preview & map cột
  → "Start Import" → enqueue background job
  → Real-time progress bar (WebSocket)
  → Xem log lỗi từng dòng
```

**Những gì Frappe validate được:**

- Kiểm tra Link field tồn tại (`frappe.db.exists(doctype, value)`)
- Kiểm tra giá trị Select field hợp lệ
- Parse Date / Datetime (tự đoán format)
- Child table qua header `child_fieldname.column` hoặc `Label (Table Label)`
- Auto-submit sau import nếu bật `submit_after_import`

---

## 2. Những gì Frappe KHÔNG làm được (với AssetCore)

Đây là lý do không thể dùng Frappe Data Import thuần túy cho AssetCore:

### 2.1 Bỏ qua Workflow & Service Layer

Frappe import gọi thẳng `doc.insert()` / `doc.save()` → **bypass hoàn toàn**:

- `before_insert()`, `validate()`, `on_submit()` controller hooks
- Workflow state machine (`Draft → Commissioned → Active`)
- Service layer AssetCore (`svc_transition_asset_status`, `svc_create_pm_schedule`, ...)

**Hậu quả cụ thể:**

| DocType | Vấn đề |
|---|---|
| AC Asset (`is_submittable=1`) | Import xong tài sản ở `Draft`, không đi qua commissioning workflow |
| AC Asset | Không trigger sinh PM Schedule tự động khi `is_pm_required=1` |
| AC Asset | `lifecycle_status` có thể set thẳng `"Active"` mà không qua `"Commissioned"` |
| Service Contract | Không validate `contract_end > contract_start` (logic domain) |
| SLA Policy | Không kiểm tra escalation user có role HTM phù hợp không |

### 2.2 Không transactional

Batch import không rollback: nếu dòng 47 lỗi sau khi 46 dòng đã `INSERT`, **46 dòng đó không bị xóa**. Dữ liệu có thể ở trạng thái nửa vời.

### 2.3 Không có import hooks

Frappe không expose `before_import()` / `after_import()` để inject logic domain. Không thể thêm validation riêng của AssetCore vào engine Frappe.

### 2.4 UX/UI không phù hợp

Frappe Data Import UI nằm ở **Setup → Data Import** (admin page) — không nằm trong luồng nghiệp vụ AssetCore. User không biết DocType tên gì (`AC Asset` hay `Asset`?), phải map cột thủ công, không có hướng dẫn domain.

---

## 3. Quyết định kiến trúc: Hybrid Approach

> **Dùng Frappe Data Import làm engine, bọc bằng custom UI và validation layer của AssetCore.**

Không build import engine từ đầu — lãng phí. Không dùng Frappe Import UI thuần — thiếu context domain.

**Phân chia trách nhiệm:**

```
┌─────────────────────────────────────────────────────────────┐
│                   AssetCore Import UI (Vue 3)               │
│  - Wizard 4 bước: Chọn loại → Upload → Preview → Xác nhận  │
│  - Template download tích hợp                               │
│  - Hiển thị lỗi bằng tiếng Việt, đúng nghiệp vụ            │
└───────────────────┬─────────────────────────────────────────┘
                    │ POST /api/method/assetcore.api.import.*
┌───────────────────▼─────────────────────────────────────────┐
│               AssetCore Import API Layer (Python)            │
│  - Nhận file, gọi Pre-validation (domain rules)             │
│  - Gọi Frappe Importer engine                               │
│  - Post-processing: sinh PM Schedule, gán SLA, ...          │
│  - Trả về kết quả có context domain                         │
└───────────────────┬─────────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────────┐
│           Frappe Data Import Engine (built-in)               │
│  - Parse file, map cột, validate Link/Select                │
│  - insert() / save() vào DB                                 │
│  - Logging vào Data Import Log                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Luồng Import Chi tiết

### 4.1 Luồng tổng quát (4 bước)

```
Bước 1 — Chọn loại dữ liệu
  User chọn: Tài sản / NCC / Model / Hợp đồng / SLA / ...
  → Download template Excel tương ứng

Bước 2 — Upload file
  Kéo thả hoặc browse file .xlsx / .csv
  → Gọi POST /api/import/preview
  → FE hiển thị preview 10 dòng đầu + cảnh báo cột thiếu

Bước 3 — Kiểm tra & xác nhận
  Bảng lỗi pre-validation (tiếng Việt):
    - "Dòng 5: Khoa phòng 'Khoa XYZ' không tồn tại"
    - "Dòng 12: asset_category bắt buộc nhưng để trống"
  User xem báo cáo, tải file lỗi (highlight dòng lỗi)
  Nút "Bắt đầu Import" chỉ enable khi 0 lỗi critical

Bước 4 — Import & kết quả
  Background job (Frappe RQ) → progress bar realtime
  Kết quả: X thành công / Y lỗi / Z bỏ qua
  Download báo cáo kết quả .xlsx (mỗi dòng có cột Status + Ghi chú lỗi)
```

### 4.2 Pre-validation (trước khi gọi Frappe engine)

Mỗi DocType có validator riêng trong `assetcore/services/import_validators.py`:

| DocType | Rules domain cần check |
|---|---|
| AC Asset | `asset_category` tồn tại + active; nếu `is_pm_required=1` → `pm_interval_days` bắt buộc; `lifecycle_status` chỉ cho phép `Draft` hoặc `Commissioned` khi import |
| IMM Device Model | `asset_category` tồn tại; `gmdn_code` format (5-6 chữ số nếu có); nếu `is_calibration_required=1` → `calibration_interval_days` bắt buộc |
| AC Supplier | `email_id` format hợp lệ; nếu `supplier_group=Calibration Lab` → `iso_17025_cert` khuyến nghị |
| Service Contract | `contract_end >= contract_start`; `supplier` tồn tại + active |
| SLA Policy | `resolution_time_hours > response_time_minutes / 60` |
| AC Asset Category | `category_name` unique (chưa tồn tại); GMDN code unique |
| Frappe User | Email format; email chưa tồn tại; `role_profile_name` tồn tại |

### 4.3 Post-processing (sau khi Frappe insert xong)

Chỉ áp dụng cho AC Asset và một số DocType có side-effect:

```python
# assetcore/services/import_postprocess.py

def post_process_assets(import_job_name: str) -> None:
    """
    Sau khi import AC Asset thành công:
    1. Sinh PM Schedule nếu is_pm_required=1 và next_pm_date chưa set
    2. Tạo Lifecycle Event "imported" cho mỗi asset
    3. Assign SLA Policy mặc định nếu chưa có
    """
```

---

## 5. Phân tích từng DocType: Dùng gì?

| DocType | Frappe engine đủ? | Cần wrapper? | Lý do |
|---|---|---|---|
| **AC Asset Category** | ✅ Đủ | ❌ Không | Data đơn giản, không có side-effect |
| **AC Department** | ✅ Đủ | ❌ Không | Tree structure: Frappe xử lý được nếu dùng `parent_department` |
| **AC Location** | ✅ Đủ | ❌ Không | Tương tự Department |
| **AC Supplier** | ✅ Đủ | ⚠️ Nhẹ | Validate ISO cert format; email unique |
| **IMM Device Model** | ✅ Đủ | ⚠️ Nhẹ | Cross-field validation (PM + interval) |
| **Service Contract** | ✅ Đủ | ⚠️ Nhẹ | `contract_end >= contract_start` |
| **IMM SLA Policy** | ✅ Đủ | ⚠️ Nhẹ | Escalation user role check |
| **AC Spare Part** | ✅ Đủ | ❌ Không | Đơn giản |
| **AC Warehouse** | ✅ Đủ | ❌ Không | Đơn giản |
| **Frappe User** | ✅ Đủ | ⚠️ Nhẹ | Role Profile must exist; send welcome email |
| **AC Asset** | ⚠️ Một phần | ✅ **Bắt buộc** | Post-processing PM Schedule, Lifecycle Event, workflow state |

---

## 6. Thiết kế UI

### 6.1 Vị trí trong sidebar

```
Quản trị hệ thống
  └── Import dữ liệu          ← route: /system/import
```

Hoặc có shortcut ở từng module:

```
Tài sản (IMM-00)
  └── [nút "Import tài sản"] → mở modal import AC Asset
```

### 6.2 Component structure (Vue 3)

```
frontend/src/views/system/import/
├── ImportWizardView.vue          # Wizard container (4 bước)
├── components/
│   ├── ImportTypeSelector.vue    # Bước 1: chọn loại data
│   ├── ImportFileUpload.vue      # Bước 2: upload file
│   ├── ImportPreviewTable.vue    # Bước 3: preview + lỗi
│   └── ImportResultSummary.vue   # Bước 4: kết quả
├── composables/
│   └── useImport.ts              # API calls, state management
└── types/
    └── import.ts                 # ImportJob, ImportRow, ImportError types
```

### 6.3 Màn hình Preview (Bước 3)

```
┌─────────────────────────────────────────────────────────────┐
│  📋 Preview: 120 dòng / 3 lỗi cần sửa                      │
│                                                             │
│  [Lỗi] ▼                                                   │
│  ┌──────┬──────────────────────────────────────────────┐   │
│  │ Dòng │ Vấn đề                                        │   │
│  ├──────┼──────────────────────────────────────────────┤   │
│  │  5   │ asset_category "Máy phẫu thuật" không tồn tại │   │
│  │ 12   │ pm_interval_days bắt buộc khi is_pm_required=1│   │
│  │ 67   │ warranty_expiry_date: sai định dạng ngày       │   │
│  └──────┴──────────────────────────────────────────────┘   │
│                                                             │
│  [Tải file lỗi .xlsx]        [Sửa & upload lại]            │
│                                                             │
│  Preview 10 dòng đầu:                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ # │ Tên tài sản         │ Danh mục    │ Vị trí    │ │   │
│  │ 1 │ Máy siêu âm P301    │ Siêu âm     │ P301      │ │   │
│  │ 2 │ Máy thở ICU-03      │ Máy thở     │ ICU       │ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│              [Hủy]  [Bắt đầu Import ▶]                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Thiết kế API Backend

### 7.1 Endpoints

```python
# assetcore/api/import_data.py

@frappe.whitelist(methods=["POST"])
def preview(doctype: str, file_url: str) -> dict:
    """
    Parse file, chạy pre-validation, trả về:
    - total_rows, preview_rows (10 dòng đầu)
    - errors: [{row, field, message}]
    - warnings: [{row, field, message}]
    """

@frappe.whitelist(methods=["POST"])
def start(doctype: str, file_url: str, import_type: str = "Insert") -> dict:
    """
    Tạo Frappe Data Import record → enqueue background job
    Trả về: { job_id, data_import_name }
    """

@frappe.whitelist()
def status(job_id: str) -> dict:
    """
    Trả về tiến trình: { progress, total, success, failed, status }
    """

@frappe.whitelist()
def result(data_import_name: str) -> dict:
    """
    Trả về kết quả chi tiết + URL file báo cáo
    """

@frappe.whitelist()
def download_template(doctype: str) -> Response:
    """
    Trả về file Excel template tương ứng từ import_templates/
    """
```

### 7.2 Pre-validation flow

```python
# assetcore/services/import_validators.py

VALIDATORS: dict[str, type[BaseImportValidator]] = {
    "AC Asset":            AssetImportValidator,
    "IMM Device Model":    DeviceModelImportValidator,
    "AC Supplier":         SupplierImportValidator,
    "Service Contract":    ContractImportValidator,
    "IMM SLA Policy":      SLAPolicyImportValidator,
    "AC Asset Category":   CategoryImportValidator,
    # Các DocType đơn giản không cần validator riêng → dùng BaseImportValidator
}

class BaseImportValidator:
    def validate_row(self, row: dict, row_idx: int) -> list[ImportError]: ...
    def validate_all(self, rows: list[dict]) -> list[ImportError]: ...

class AssetImportValidator(BaseImportValidator):
    def validate_row(self, row, row_idx):
        errors = []
        if row.get("is_pm_required") == "1" and not row.get("pm_interval_days"):
            errors.append(ImportError(row_idx, "pm_interval_days",
                "Bắt buộc khi 'Cần bảo trì định kỳ' = 1"))
        if row.get("lifecycle_status") not in ("", "Draft", "Commissioned"):
            errors.append(ImportError(row_idx, "lifecycle_status",
                "Import chỉ cho phép Draft hoặc Commissioned"))
        return errors
```

---

## 8. Thứ tự Import (dependency order)

Phải import theo thứ tự để tránh lỗi Link field:

```
Bước 1 (không phụ thuộc):
  AC Asset Category
  AC Department
  AC Location
  Frappe User

Bước 2 (phụ thuộc Bước 1):
  AC Supplier         (cần: User cho technician)
  IMM Device Model    (cần: AC Asset Category)
  AC Warehouse        (cần: AC Location, AC Department)

Bước 3 (phụ thuộc Bước 2):
  Service Contract    (cần: AC Supplier)
  IMM SLA Policy      (cần: User cho escalation)
  AC Spare Part       (cần: AC Supplier)

Bước 4 (cuối cùng):
  AC Asset            (cần: tất cả trên)
```

UI nên hiển thị dependency rõ ràng khi user chọn loại import sai thứ tự.

---

## 8bis. Hợp đồng "điền TÊN, báo đúng chỗ, bỏ qua được" (chốt 2026-08-11)

Phản hồi người dùng: *"có vài trường phải điền bằng mã (mã khoa phòng, mã model…)"* —
mã hệ thống là chi tiết cài đặt, người nhập liệu bệnh viện không có cách nào tra.
Ba cam kết dưới đây áp cho MỌI loại dữ liệu hỗ trợ nhập/xuất:

**1. Cột tham chiếu luôn dùng TÊN, cả 2 chiều.**
SSoT: `utils/import_helpers.LINK_DISPLAY_BY_DOCTYPE` (`api/import_data._RESOLVABLE_LINKS_BY_DOCTYPE`
chỉ là alias). Một map, ba hướng dùng:

| Hướng | Hàm | Hệ quả nếu quên |
|---|---|---|
| Nhập: tên → mã trước khi lưu | `_resolve_links` | Frappe báo "Could not find …" giữa chừng |
| Nhập: chấp nhận cả tên lẫn mã khi kiểm tra | `_link_lookup_set` | Từ chối đúng giá trị template dạy điền |
| Xuất: mã → tên khi ghi Excel | `resolve_links_to_display` | File xuất ra toàn mã, không nhập lại được |

Ngoại lệ duy nhất: Link trỏ `User` — khoá chính là email, chính là giá trị hiển thị.
Cột `name` ("Mã hệ thống") vẫn xuất để hỗ trợ kỹ thuật đối chiếu.

**2. Báo lỗi chỉ đúng hàng và đúng cột, bằng tiếng Việt.**
Parser loại dòng trống ⇒ "dòng thứ N" KHÔNG bằng hàng Excel `N+5`. `_rows_to_dicts`
ghi số hàng gốc vào `__source_row__`; `enrich_issues()` bồi `source_row` + `label`
(nhãn VI) vào mọi lỗi trả ra: xem trước · lỗi khi nhập · dòng bỏ qua · báo cáo lỗi
`.xlsx` (cột đầu = "Hàng trong file"). Giao diện hiện **"Hàng 12 · Danh mục tài sản"**,
không hiện `row: 7` hay `asset_category`.

**3. Sai/trùng vài dòng không chặn cả file.**
Chế độ 'Bỏ qua dòng lỗi/trùng' (opt-in, mặc định vẫn là dừng lại) áp cho MỌI loại dữ
liệu — kể cả `User` (đường upsert riêng nhận `invalid_idx` + `skipped_rows`). Dữ liệu
trùng đã có trong hệ thống hoặc trùng trong file đều là lỗi chặn ⇒ bỏ qua được.
Với dữ liệu cây, bỏ qua cha thì bỏ qua luôn con (`_cascade_skip_for_tree`) để không
sinh node mồ côi. Sau khi nhập xong tải báo cáo lỗi về sửa rồi nhập lại phần còn thiếu.

Guard: `assetcore/tests/test_import_display_names.py` (17 TC) + `frontend/src/api/importRowLabels.test.ts` (4 TC).

### 8bis.1 Dữ liệu có BẢNG CON — mẫu bảng kiểm bảo trì (bổ sung 2026-08-11)

`PM Checklist Template` (cha) + `PM Checklist Item` (bảng con) là loại dữ liệu đầu
tiên không phẳng. Quyết định:

- **Một sheet phẳng, mỗi hàng = 1 hạng mục kiểm tra.** 5 cột đầu (tên mẫu · danh
  mục · loại bảo trì · phiên bản · ngày hiệu lực) lặp lại y hệt ở mọi hàng cùng
  mẫu. Không dùng 2 sheet cha/con: người nhập liệu phải tự khớp khoá bằng tay.
- **Gộp theo khoá định danh (Danh mục + Loại bảo trì)** — đúng
  `autoname: PMCT-{asset_category}-{pm_type}`, nên **không có cột mã mẫu**. Khoá
  được chuẩn hoá trước khi gộp (tên→mã, nhãn VI→giá trị lưu) và gộp theo khoá chứ
  không theo hàng liền nhau.
- **Cột của mẫu lấy theo hàng đầu nhóm**; hàng sau khai lệch chỉ cảnh báo — chặn
  thì file thật (người ta copy/paste tay) không bao giờ nhập nổi.
- **Mẫu đã tồn tại** ⇒ lỗi gắn vào mọi hàng của mẫu đó, nên 'bỏ qua dòng lỗi/trùng'
  loại đúng mẫu trùng mà các mẫu khác trong file vẫn vào. Import KHÔNG ghi đè mẫu
  cũ — sửa mẫu là việc của màn hình `/pm/templates`.
- **Tạo bản ghi qua service layer** (`services.imm08.create_template`), không
  `new_doc().insert()` trần: đánh số hạng mục (`ITEM-001…`) và quy tắc nghiệp vụ
  nằm ở đó.
- **`success` đếm theo DÒNG**, thêm `groups_created` cho số mẫu — giao diện hiện cả
  hai ("3 hạng mục nhập thành công · Đã tạo 2 mẫu bảng kiểm").
- **Cột Select cũng hỏi bằng tiếng Việt** (SSoT `ENUM_DISPLAY_BY_DOCTYPE`): template
  và export in "Hàng quý" / "Số đo"; import nhận cả nhãn VI lẫn giá trị gốc rồi đổi
  về giá trị gốc. Enum của DocType KHÔNG đổi.

Guard: `assetcore/tests/test_import_pm_checklist_template.py` (11 TC) +
`frontend/src/views/pm/pmTemplateImportWiring.test.ts` (5 TC).

### 8bis.2 Cột Select hỏi bằng tiếng Việt — áp CẢ LOẠT (đồng bộ 2026-08-11)

Việt hoá enum cho riêng mẫu bảng kiểm rồi để 7 mẫu còn lại hỏi "Semi-Annual" /
"Straight Line" **khó dùng hơn thuần tiếng Anh**: người dùng không đoán được cột
nào theo luật nào. Đã áp đồng loạt cho mọi cột Select xuất hiện trong file mẫu
hoặc file xuất:

| Loại dữ liệu | Cột |
|---|---|
| Danh mục tài sản | phương pháp khấu hao · tần suất khấu hao |
| Vị trí | loại khu vực lâm sàng · mức kiểm soát nhiễm khuẩn |
| Nhà cung cấp | nhóm nhà cung cấp · loại nhà cung cấp |
| Model thiết bị | phân loại thiết bị · loại hiệu chuẩn |
| Hợp đồng dịch vụ | loại hợp đồng |
| Người dùng | trạng thái duyệt |
| Tài sản | trạng thái vòng đời · trạng thái · phương pháp/tần suất khấu hao |
| Phụ tùng | loại phụ tùng |
| Chính sách SLA | mức ưu tiên · phân loại rủi ro |
| Mẫu bảng kiểm | loại bảo trì · cách ghi nhận kết quả |

Cơ chế: SSoT `ENUM_DISPLAY_BY_DOCTYPE` + `enum_display` / `enum_accepted` /
`enum_to_stored`. Template và file xuất in **nhãn tiếng Việt**; khi nhập, hệ thống
nhận **cả nhãn tiếng Việt lẫn giá trị gốc** rồi đổi về giá trị gốc trước khi lưu
(`_restore_enum_values`). **Enum trong cơ sở dữ liệu KHÔNG đổi** — chỉ lớp
nhập/xuất dịch qua lại. Validator dùng chung `BaseImportValidator._check_enum`,
câu báo lỗi liệt kê nhãn tiếng Việt.

Nhãn phải trùng nhãn trên màn hình, nên các map nhãn còn nằm rải trong `.vue` đã
được gom về `frontend/src/constants/labels.ts` (`CLINICAL_AREA_TYPE_LABEL`,
`INFECTION_CONTROL_LEVEL_LABEL`, `SPARE_PART_CATEGORY_LABEL`, `VENDOR_TYPE_LABEL`).

Guard `assetcore/tests/test_import_enum_labels.py` (7 TC / 4 tầng: phủ kín ·
không khoá rác · parity với SSoT của giao diện · dropdown trong file `.xlsx` thật)
— thêm một cột Select mới mà quên nhãn là đỏ ngay.

---

## 9. Quyết định cuối cùng

| Câu hỏi | Quyết định |
|---|---|
| Dùng Frappe built-in hay tự build? | **Hybrid**: Frappe engine + AssetCore wrapper |
| Dùng Frappe Data Import UI (/data-import)? | **Không** — quá thô, không có context domain |
| Build UI riêng? | **Có** — ImportWizardView trong AssetCore FE |
| Cần build import engine riêng? | **Không** — reuse Frappe Importer class |
| Import bypass workflow có OK không? | **Có cho data tham chiếu** (Category, Supplier, Model...); **Không cho AC Asset** — cần post-processing |
| Xử lý thứ tự import? | **FE guide** + **BE validate dependency** trước khi import |

---

## 10. Việc cần làm (implementation order)

```
[ ] BE: assetcore/api/import_data.py (preview, start, status, result, download_template)
[ ] BE: assetcore/services/import_validators.py (validators per DocType)
[ ] BE: assetcore/services/import_postprocess.py (post-processing AC Asset)
[ ] FE: router entry /system/import
[ ] FE: ImportWizardView.vue + 4 sub-components
[ ] FE: composables/useImport.ts
[ ] FE: sidebar entry "Import dữ liệu"
[ ] TEST: unit test validators + integration test end-to-end 10-row import
```
