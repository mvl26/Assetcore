# Backend (BE) — Import pipeline

Heavy reference cho phần Backend của import. Đọc khi viết/sửa `api/import_data.py`,
`services/import_validators.py`, `services/import_postprocess.py`, `utils/import_helpers.py`.

---

## 1.1 File structure

```
assetcore/
├── api/
│   └── import_data.py              ← Tier 1: 6 endpoints
├── services/
│   ├── import_validators.py        ← Tier 2: pre-validation per DocType
│   └── import_postprocess.py       ← Tier 2: post-processing (AC Asset)
└── utils/
    └── import_helpers.py           ← parse xlsx/csv, error report, folder mgmt, template map
```

## 1.2 ErrorCode — tên attribute đúng

```python
from assetcore.services.shared import ErrorCode

# ĐÚNG
ErrorCode.VALIDATION   # lỗi nghiệp vụ / input sai
ErrorCode.INTERNAL     # lỗi server không mong đợi

# SAI — không tồn tại, sẽ AttributeError tại runtime
ErrorCode.VALIDATION_ERROR   # ← KHÔNG dùng
ErrorCode.INTERNAL_ERROR     # ← KHÔNG dùng
```

`_handle` pattern chuẩn trong `import_data.py`:

```python
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.response import _err, _ok

def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except (ValueError, FileNotFoundError) as e:
        return _err(str(e), ErrorCode.VALIDATION)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Import API Error")
        return _err("Lỗi hệ thống — xem Error Log để biết chi tiết.", ErrorCode.INTERNAL)
```

## 1.3 API endpoints (`api/import_data.py`)

Các endpoint hiện có:

```python
@frappe.whitelist()
def init_import_folders(doctype: str) -> dict:
    """
    Tạo Frappe folder hierarchy TRƯỚC khi FE upload file.
    Phải gọi endpoint này trước, commit vào DB, rồi mới upload_file.
    Returns: {"folder": "Home/AssetCore Imports/<doctype>"}
    """
    from assetcore.utils.import_helpers import ensure_import_folder
    try:
        safe = doctype.replace(" ", "_")
        folder = ensure_import_folder(safe)
        ensure_import_folder("Error Reports")
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Init Import Folders")
        folder = "Home/Attachments"   # fallback an toàn
    return _ok({"folder": folder})

@frappe.whitelist(methods=["POST"])
def preview_ref_data(doctype: str, file_url: str) -> dict:
    """Parse + validate. KHÔNG insert."""
    return _handle(_do_preview, doctype, file_url)

@frappe.whitelist(methods=["POST"])
def import_ref_data(
    doctype: str,
    file_url: str,
    skip_invalid: bool = False,   # ← Phần 8: opt-in skip mode
) -> dict:
    """Validate + insert rows trực tiếp.
    - skip_invalid=False (mặc định): có lỗi pre-validate → ServiceError, abort toàn file.
    - skip_invalid=True: bỏ qua các dòng lỗi (và cascade child cho Tree DocType),
      vẫn insert phần hợp lệ. Trả {total, success, failed, skipped, errors, skipped_rows}.
    """
    return _handle(_do_import, doctype, file_url, skip_invalid)

@frappe.whitelist()
def export_ref_data(doctype: str):
    """Download current data as xlsx. Set response attachment."""

@frappe.whitelist()
def download_template(doctype: str):
    """Serve blank Excel template. Set response attachment."""

@frappe.whitelist(methods=["POST"])
def build_error_report(doctype: str, file_url: str) -> dict:
    """Parse + validate + build xlsx error report → trả file_url để FE download."""
    return _handle(_do_build_error_report, doctype, file_url)
```

**Response schema chuẩn:**

```python
# Thành công
{"success": True, "data": {...}}

# Preview response
{"success": True, "data": {
    "doctype": "AC Department",
    "total_rows": 12,
    "valid_rows": 11,
    "preview": [...],          # 10 dòng đầu
    "fieldnames": [...],       # tên field để FE render header
    "errors": [                # severity="error" → block import
        {"row": 5, "field": "email", "message": "Email không hợp lệ: abc@"}
    ],
    "warnings": [              # severity="warning" → không block
        {"row": 12, "field": "dept_head", "message": "Trưởng khoa chưa được gán"}
    ]
}}

# Import result — strict mode (skip_invalid=False)
{"success": True, "data": {
    "total": 12, "success": 11, "failed": 1, "skipped": 0,
    "errors": [{"row": 5, "field": "", "message": "Bản ghi đã tồn tại (trùng tên hoặc mã)."}],
    "skipped_rows": []
}}

# Import result — skip mode (skip_invalid=True), 5 dòng pre-validate lỗi + 2 dòng cascade
{"success": True, "data": {
    "total": 50, "success": 43, "failed": 0, "skipped": 7,
    "errors": [],
    "skipped_rows": [
        {"row": 4, "reason": "pre_validate", "field": "location_name",
         "message": "'Tên vị trí' là bắt buộc"},
        {"row": 11, "reason": "cascade_parent_skipped", "field": "parent_location",
         "message": "Cha 'Tầng 1 - Tòa A' đã bị bỏ qua → bỏ qua dòng này"}
    ]
}}
```

## 1.4 Pre-validation (`services/import_validators.py`)

**Registry pattern — bắt buộc:**

```python
from typing import TypedDict, Literal

class ImportError(TypedDict):
    row: int
    field: str
    message: str
    severity: Literal["error", "warning"]

class BaseImportValidator:
    doctype: str

    def validate_row(self, row: dict, row_idx: int) -> list[ImportError]:
        return []

    def validate_all(self, rows: list[dict]) -> list[ImportError]:
        errors: list[ImportError] = []
        for i, row in enumerate(rows, start=1):
            errors.extend(self.validate_row(row, i))
        return errors

VALIDATOR_REGISTRY: dict[str, type[BaseImportValidator]] = {
    "AC Asset":             AssetImportValidator,
    "IMM Device Model":     DeviceModelImportValidator,
    "AC Supplier":          SupplierImportValidator,
    "Service Contract":     ContractImportValidator,
    "IMM SLA Policy":       SLAPolicyImportValidator,
    "AC Asset Category":    CategoryImportValidator,
    "AC Department":        BaseImportValidator,
    "AC Location":          BaseImportValidator,
    "AC Spare Part":        BaseImportValidator,
    "AC Warehouse":         BaseImportValidator,
}

def get_validator(doctype: str) -> BaseImportValidator:
    cls = VALIDATOR_REGISTRY.get(doctype, BaseImportValidator)
    return cls()
```

**Rules tuyệt đối cho validators:**

- Validator KHÔNG insert/update DB — chỉ đọc (`frappe.db.exists`, `frappe.db.get_value`)
- Validator KHÔNG raise Exception — trả `list[ImportError]`, không raise
- `row` index là 1-based, khớp với dòng user nhìn trong Excel
- Message tiếng Việt, kèm giá trị cụ thể bị lỗi
- **LL-IMP-1** (BẮT BUỘC): Khi check 1 Link field — validator phải accept **CẢ HAI** dạng: system code (doc `name`) **và** display name (`category_name` / `supplier_name` / `model_name` / `location_name` / `department_name` …). Lý do: template Excel hướng dẫn user nhập display name (vd "Máy chẩn đoán hình ảnh" cho asset_category), `_RESOLVABLE_LINKS_BY_DOCTYPE` resolver đã accept cả 2 → validator chỉ accept code = reject input hợp lệ → wizard chặn user.

  **Helper bắt buộc dùng** (`assetcore/services/import_validators.py`):
  ```python
  def _link_lookup_set(doctype: str, display_field: str) -> set[str]:
      names = {r.name for r in frappe.get_all(doctype, fields=["name"])}
      if not display_field:
          return names
      displays = {str(r.get(display_field) or "")
                  for r in frappe.get_all(doctype, fields=[display_field])}
      displays.discard("")
      return names | displays
  ```

  **Dùng đúng**:
  ```python
  # ĐÚNG
  valid_categories = _link_lookup_set("AC Asset Category", "category_name")
  if cat and cat not in valid_categories:
      errors.append(self._err(row_idx, "asset_category", "..."))

  # SAI — reject display name
  valid_categories = {r.name for r in frappe.get_all("AC Asset Category", fields=["name"])}

  # SAI — frappe.db.exists chỉ check name, không check display
  if supplier and not frappe.db.exists("AC Supplier", supplier):
      ...
  ```

  **Ngoại lệ duy nhất**: User DocType (PK = email = display) — gọi `_link_lookup_set("User", "")`.

## 1.5 Helper utilities (`utils/import_helpers.py`)

### parse_upload_file — trả tuple, không phải list

```python
def parse_upload_file(file_url: str) -> tuple[list[str], list[dict]]:
    """
    Returns (fieldnames, rows).
    Template row layout:
        Row 1 — banner (skip)
        Row 2 — fieldnames  ← dùng làm column headers
        Row 3 — VN labels   (skip)
        Row 4 — description (skip)
        Row 5 — example     (skip)
        Row 6+ — data
    """

# ĐÚNG — unpack tuple
fieldnames, rows = parse_upload_file(file_url)

# SAI — parse_upload_file không trả list[dict]
rows = parse_upload_file(file_url)           # ← TypeError
_, rows = parse_upload_file(file_url)        # OK nếu fieldnames không cần
```

### save_file — dùng file_manager, không dùng frappe.get_doc

```python
# ĐÚNG — save error report
from frappe.utils.file_manager import save_file

folder = ensure_import_folder("Error Reports")
fname  = f"error_report_{doctype.replace(' ', '_').lower()}.xlsx"
file_doc = save_file(fname, xlsx_bytes, dt="", dn="", folder=folder, is_private=1)
return {"file_url": file_doc.file_url, "error_count": len(errors)}

# SAI — frappe.get_doc("File") trigger mandatory validation, raise:
#   "Fields `file_name` or `file_url` must be set for File"
frappe.get_doc({"doctype": "File", "content": xlsx_bytes, ...}).insert()  # ← KHÔNG
```

### Template file mapping — mỗi DocType một file riêng

```python
# ĐÚNG — 3 file riêng cho ref-data
_TEMPLATE_MAP: dict[str, str] = {
    "AC Asset Category": "01a_danh_muc_tai_san.xlsx",
    "AC Department":     "01b_khoa_phong.xlsx",
    "AC Location":       "01c_vi_tri.xlsx",
    "AC Supplier":       "02_imm00_ncc_model_hopdong_sla.xlsx",
    "IMM Device Model":  "02_imm00_ncc_model_hopdong_sla.xlsx",
    "Service Contract":  "02_imm00_ncc_model_hopdong_sla.xlsx",
    "IMM SLA Policy":    "02_imm00_ncc_model_hopdong_sla.xlsx",
    "AC Asset":          "03_danh_sach_tai_san.xlsx",
    "AC Spare Part":     "04_danh_sach_phu_tung.xlsx",
    "AC Warehouse":      "05_kho_hang.xlsx",
    "User":              "06_danh_sach_nguoi_dung.xlsx",
}

# SAI — không dùng 1 file chung cho nhiều DocType khác nhau
"AC Asset Category": "01_du_lieu_tham_chieu.xlsx",   # ← cũ, đã xóa
"AC Department":     "01_du_lieu_tham_chieu.xlsx",   # ← cũ, đã xóa
"AC Location":       "01_du_lieu_tham_chieu.xlsx",   # ← cũ, đã xóa
```

> Nếu update template map → phải chạy lại `docs/imports/generate_templates.py`
> để sinh lại các file xlsx trong `assetcore/public/import_templates/`.

## 1.6 Frappe folder management — PHẢI làm trước upload

Frappe's `upload_file` endpoint validate `folder` Link field trong DB trước khi nhận file.
**Nếu folder chưa tồn tại → upload fail với "Could not find Folder: ..."**

```python
# ĐÚNG — tạo folder với create_new_folder (tự handle ignore_if_duplicate)
from frappe.core.api.file import create_new_folder

_IMPORT_FOLDER_ROOT = "Home/AssetCore Imports"

def ensure_import_folder(sub: str = "") -> str:
    """
    Tạo folder hierarchy, commit ngay.
    Frappe folder name = path string, e.g. "Home/AssetCore Imports/AC_Department".
    frappe.db.commit() bắt buộc — request tiếp theo mới thấy folder.
    """
    _create_if_missing(create_new_folder, _IMPORT_FOLDER_ROOT, "Home")
    if not sub:
        frappe.db.commit()
        return _IMPORT_FOLDER_ROOT
    path = f"{_IMPORT_FOLDER_ROOT}/{sub}"
    _create_if_missing(create_new_folder, path, _IMPORT_FOLDER_ROOT)
    frappe.db.commit()
    return path

def _create_if_missing(create_fn, path: str, parent: str) -> None:
    if frappe.db.exists("File", path):
        return
    try:
        create_fn(path.rsplit("/", 1)[-1], parent)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Import Folder Creation")

# SAI — frappe.new_doc("File") không có ignore_if_duplicate → IntegrityError
frappe.get_doc({"doctype": "File", "file_name": "...", "is_folder": 1}).insert()  # ← KHÔNG
```

**Thứ tự bắt buộc trong FE:**

```
1. FE gọi initImportFolders(doctype)  → tạo folder + commit
2. FE nhận folder path từ response
3. FE upload file kèm folder path
```

Nếu bỏ bước 1 → upload fail vì folder chưa có trong DB.

## 1.7 Direct insert (`_do_import`)

Cho ref-data (không có side-effects), insert trực tiếp.

### Resolvable Link fields — bắt buộc cho mọi DocType có Link field hiển thị display name

User Excel template điền **display name** (ví dụ "Tòa nhà A - Khu Điều trị"), nhưng Frappe Link field expect **doc name** (system code `AC-LOC-2026-0001`). Phải có resolver từ display→code TRƯỚC insert.

Đặc biệt **Tree DocType** (`is_tree: 1`): `nsm_parent_field` (vd `parent_location`) là Link self-reference → bắt buộc resolve, nếu không Frappe core `nested_set.validate_parent_field` crash với:

> `frappe.exceptions.DoesNotExistError: Could not find Parent Location: Tòa nhà A - Khu Điều trị`

**Pattern bắt buộc** (LL-BE-26):

```python
_RESOLVABLE_LINKS_BY_DOCTYPE = {
    "AC Asset": {
        "asset_category": ("AC Asset Category", "category_name"),
        "device_model":   ("IMM Device Model", "model_name"),
        "location":       ("AC Location", "location_name"),
        "department":     ("AC Department", "department_name"),
        "supplier":       ("AC Supplier", "supplier_name"),
    },
    "AC Location": {
        # Tree DocType — parent self-reference PHẢI có entry
        "parent_location": ("AC Location", "location_name"),
    },
    "AC Warehouse": {
        "location":   ("AC Location", "location_name"),
        "department": ("AC Department", "department_name"),
    },
    # ... mọi DocType có Link field nhận display name từ template
}

for fld, (link_dt, display_field) in resolvable_links.items():
    val = clean.get(fld)
    if not val or frappe.db.exists(link_dt, val):
        continue   # đã là doc name (system code) → giữ nguyên
    resolved = frappe.db.get_value(link_dt, {display_field: val}, "name")
    if resolved:
        clean[fld] = resolved
    # else: để validator/Frappe core báo lỗi
```

**Yêu cầu thứ tự cho Tree DocType**: parent rows PHẢI nằm trước child rows trong file. `frappe.db.get_value` đọc DB state sau mỗi `doc.insert()` (Frappe write-through transaction) → resolve cross-row trong cùng batch hoạt động đúng.

**Validator bổ sung** (`LocationImportValidator.validate_all`): nếu phát hiện `parent_location` value xuất hiện ở row sau row đang xét → **warn** "Vị trí cha phải đặt trước con trong file". Không block (vì warn không phải error), nhưng user thấy được vấn đề.

### Bool fields & normalisation

```python
_BOOL_FIELDS = {
    "is_active", "is_group", "default_pm_required",
    "default_calibration_required", "has_radiation", "power_backup_available",
}

def _normalise_row(row: dict, bool_fields: set[str]) -> dict:
    """Convert string → Python types trước khi gán cho frappe.new_doc."""
    out: dict = {}
    for k, v in row.items():
        if v == "" or v is None:
            continue
        if k in bool_fields:
            out[k] = 1 if str(v) in ("1", "True", "true", "yes") else 0
        else:
            out[k] = v
    return out

def _friendly_frappe_error(msg: str) -> str:
    if "Duplicate entry" in msg:
        return "Bản ghi đã tồn tại (trùng tên hoặc mã)."
    if "cannot be null" in msg.lower() or "mandatory" in msg.lower():
        return "Thiếu trường bắt buộc."
    return msg[:200]
```

## 1.8 Skip-Invalid Mode (UX: tăng tolerance cho file có lỗi rải rác)

**Mục đích**: trước đây 1 dòng lỗi = abort cả file (line `if blocking: raise ServiceError(...)`). User import 500 dòng có 5 dòng lỗi phải sửa & upload lại từ đầu. Skip mode cho phép insert phần hợp lệ, báo cáo phần bỏ qua.

### Contract chuẩn

```python
def _do_import(doctype: str, file_url: str, skip_invalid: bool = False) -> dict:
    _, rows = parse_upload_file(file_url, doctype)
    if not rows:
        raise ServiceError(ErrorCode.VALIDATION, "File không có dòng dữ liệu.")

    validator = get_validator(doctype)
    issues = validator.validate_all(rows)
    blocking = [e for e in issues if e["severity"] == "error"]

    invalid_idx: set[int] = set()
    skipped_rows: list[dict] = []

    if blocking:
        if not skip_invalid:
            # Strict mode (mặc định, backward-compatible)
            raise ServiceError(
                ErrorCode.VALIDATION,
                f"File có {len(blocking)} lỗi bắt buộc phải sửa trước khi import. "
                "Dùng Preview để xem chi tiết hoặc bật 'Bỏ qua dòng lỗi'.",
            )
        # Skip mode: mark mọi row có blocking error
        for e in blocking:
            invalid_idx.add(e["row"])
            skipped_rows.append({
                "row": e["row"], "reason": "pre_validate",
                "field": e["field"], "message": e["message"],
            })

        # Cascade cho Tree DocType: nếu parent skip → child skip
        invalid_idx, cascade = _cascade_skip_for_tree(doctype, rows, invalid_idx)
        skipped_rows.extend(cascade)

        # Edge: 100% rows invalid → không có gì để insert
        if len(invalid_idx) >= len(rows):
            raise ServiceError(
                ErrorCode.VALIDATION,
                "Không có dòng hợp lệ nào để import — toàn bộ file lỗi.",
            )

    # ... loop insert, skip nếu i in invalid_idx
    results = {
        "total": len(rows), "success": 0, "failed": 0,
        "skipped": len(invalid_idx),
        "errors": [], "skipped_rows": skipped_rows,
    }
    for i, row in enumerate(rows, start=1):
        if i in invalid_idx:
            continue
        try:
            # ... existing insert logic
            results["success"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({...})
    frappe.db.commit()
    return results
```

### Cascade skip cho Tree DocType (`_cascade_skip_for_tree`)

```python
def _cascade_skip_for_tree(
    doctype: str, rows: list[dict], invalid_idx: set[int],
) -> tuple[set[int], list[dict]]:
    """
    Nếu DocType là Tree và row parent bị skip → các row child cũng skip.
    Tránh tạo orphan tree nodes hoặc fail với "Could not find Parent".
    """
    meta = frappe.get_meta(doctype)
    if not getattr(meta, "is_tree", 0):
        return invalid_idx, []

    parent_field = meta.nsm_parent_field  # vd "parent_location"
    cfg = _RESOLVABLE_LINKS_BY_DOCTYPE.get(doctype, {}).get(parent_field)
    if not cfg:
        return invalid_idx, []
    _, display_field = cfg   # vd "location_name"

    invalid_display_names: set[str] = {
        str(rows[i-1].get(display_field, "")).strip()
        for i in invalid_idx
        if str(rows[i-1].get(display_field, "")).strip()
    }

    extra_skip: list[dict] = []
    changed = True
    while changed:   # walk nhiều pass để bắt cascade nhiều cấp
        changed = False
        for i, row in enumerate(rows, start=1):
            if i in invalid_idx:
                continue
            parent_val = str(row.get(parent_field, "")).strip()
            if parent_val and parent_val in invalid_display_names:
                invalid_idx.add(i)
                extra_skip.append({
                    "row": i, "reason": "cascade_parent_skipped",
                    "field": parent_field,
                    "message": f"Cha '{parent_val}' đã bị bỏ qua → bỏ qua dòng này",
                })
                own_name = str(row.get(display_field, "")).strip()
                if own_name:
                    invalid_display_names.add(own_name)
                changed = True
    return invalid_idx, extra_skip
```

### Rules tuyệt đối

- **Default `skip_invalid=False`** — backward compatible. FE phải opt-in qua checkbox/radio.
- **Cascade cho Tree DocType là bắt buộc** — silent insert child với parent skip → orphan tree, fail insert sau hoặc tạo data sai cấp.
- **Không skip warning** — warning đã pass strict, không tính vào blocking.
- **Trả `skipped_rows` chi tiết** — FE render được danh sách + lý do (`pre_validate` / `cascade_parent_skipped`).
- **Edge case 100% invalid**: raise ServiceError, không gọi `commit()` rỗng.
- **Không hỗ trợ skip cho User import** — `_do_import_users` có logic riêng (upsert + role merge); skip riêng nếu cần phải refactor sau.

### Preview bổ sung — cascade_count cho Tree DocType

`preview_ref_data` response thêm field `cascade_count`:

```python
{"success": True, "data": {
    "doctype": "AC Location",
    "total_rows": 50,
    "valid_rows": 43,
    "errors": [...5 lỗi pre-validate...],
    "warnings": [...],
    "cascade_count": 2,   # ← số row sẽ bị cascade skip nếu chọn skip mode
}}
```

FE dùng `errors.length + cascade_count` để hiển thị "Sẽ bỏ qua 7 dòng (5 lỗi + 2 phụ thuộc)" TRƯỚC khi user confirm.

## 1.9 Frappe Data Import engine (cho AC Asset — tương lai)

```python
# Dùng khi DocType có side-effects, PM schedule, workflow
from frappe.core.doctype.data_import.data_import import DataImport

def start_import(doctype: str, file_url: str) -> dict:
    di = frappe.new_doc("Data Import")
    di.reference_doctype = doctype
    di.import_type = "Insert New Records"
    di.import_file = file_url
    di.submit_after_import = False   # CỨNG — AC Asset phải qua workflow commissioning
    di.insert(ignore_permissions=True)
    di.start_import()               # enqueue background job
    return {"data_import_name": di.name}
```

---

## Phần 3 — Anti-patterns BE (chi tiết, KHÔNG làm)

> Tóm tắt dạng table ở SKILL.md §Common Rationalizations. Chi tiết đầy đủ giữ ở đây.

1. **`ErrorCode.VALIDATION_ERROR` hoặc `INTERNAL_ERROR`** — không tồn tại, sẽ `AttributeError` tại runtime. Dùng `ErrorCode.VALIDATION` và `ErrorCode.INTERNAL`.

2. **`frappe.get_doc({"doctype": "File", "content": bytes})` để lưu file** — trigger mandatory validation, raise *"Fields `file_name` or `file_url` must be set for File"*. Dùng `frappe.utils.file_manager.save_file()`.

3. **`frappe.new_doc("File", is_folder=1).insert()` để tạo folder** — không có `ignore_if_duplicate`, crash khi folder đã tồn tại. Dùng `frappe.core.api.file.create_new_folder()`.

4. **Không gọi `frappe.db.commit()` sau khi tạo folder** — folder tạo xong nhưng chưa commit, request upload ngay sau sẽ fail vì DB transaction chưa visible. `commit()` là bắt buộc trong `ensure_import_folder`.

5. **Dùng `01_du_lieu_tham_chieu.xlsx` chung cho 3 ref-data DocType** — file này đã bị xóa. Mỗi DocType có file template riêng: `01a`, `01b`, `01c`.

6. **Validator raise Exception** — validator phải trả `list[ImportError]`, không raise. Raising crash preview, user thấy 500 thay vì danh sách lỗi.

7. **Post-processor không có try/except per record** — lỗi 1 record crash toàn bộ batch.

8. **`submit_after_import = True` khi dùng Frappe engine** — AC Asset phải qua workflow commissioning, không auto-submit.

9. **Validator query DB cho mỗi dòng không cache** — với 500 dòng cùng `asset_category`, cache trong dict trong `validate_all()` để tránh N+1 queries.

### Skip-Invalid Mode Anti-patterns (2026-05-28)

15. **Không resolve display→code cho `parent_location` (Tree DocType)** — Frappe core `nested_set.validate_parent_field` crash *"Could not find Parent Location: <display_name>"*. PHẢI thêm Tree DocType vào `_RESOLVABLE_LINKS_BY_DOCTYPE` với `nsm_parent_field` mapping. (LL-BE-26)

16. **Skip mode insert child khi parent đã skip (Tree DocType)** — tạo orphan tree node, gãy NestedSet (`lft/rgt`), hoặc crash insert vì parent doc name không có. PHẢI chạy `_cascade_skip_for_tree` để propagate skip xuống mọi cấp child.

17. **Default `skip_invalid=True` ở BE hoặc FE** — user import thiếu data mà không nhận ra. Skip mode PHẢI opt-in qua radio/checkbox FE; BE default `False` để backward-compatible với client cũ.

18. **Skip mode cho `User` import không refactor `_do_import_users`** — `_do_import_users` có upsert logic + role merge khác `_do_import`. Truyền `skip_invalid` qua mà không update hàm này → param bị ignore silent. Tách rõ trong API doc: User import chưa hỗ trợ skip mode.

19. **Không trả `skipped_rows` chi tiết** — FE chỉ thấy số `skipped: 7` nhưng không biết dòng nào, lý do gì → user phải tự dò file. PHẢI trả `[{row, reason, field, message}]` để FE render & user tải về sửa.

20. **Bỏ qua warning về thứ tự parent-child trong Tree file** — nếu user đặt child trước parent (vd dòng 4 = "Tầng 1", dòng 7 = "Tòa A"), `frappe.db.get_value` lookup parent fail vì parent chưa insert. Validator PHẢI thêm warning "Vị trí cha phải đặt trước con trong file" để user biết.

21. **(LL-IMP-1) Validator collect chỉ `r.name` để check Link field** — reject mọi display name user nhập. Template hướng dẫn "nhập tên danh mục" nhưng validator báo "Danh mục 'X' không tồn tại" vì X không phải code. PHẢI dùng `_link_lookup_set(doctype, display_field)` — accept cả 2 dạng:

    ```bash
    # Audit grep — tìm pattern sai trong validators
    grep -nE "for r in frappe\.get_all\([^,]+, fields=\[\"name\"\]\)" \
      assetcore/services/import_validators.py
    # Mỗi match → review xem có phải đang build "valid Link set" không.
    # Nếu có và display_field tồn tại → sửa sang _link_lookup_set().

    grep -nE "frappe\.db\.exists\(\"(AC|IMM|Service) [A-Z]" \
      assetcore/services/import_validators.py
    # Mỗi match → check xem field đó có display_field không.
    # Nếu có → dùng `value in _link_lookup_set(...)` thay vì frappe.db.exists.
    ```

22. **Template ví dụ dùng system code thay vì display name** — user copy example sẽ điền code, không match dữ liệu master họ vừa import. Template `example` PHẢI dùng display name (tên tiếng Việt) khớp với `_RESOLVABLE_LINKS_BY_DOCTYPE` resolver. Ngoại lệ: User email (vì email = PK = display).

---

## Cross-skill BE rules áp dụng (2026-05-27, mở rộng 2026-05-28)

Khi build import endpoint cho DocType có workflow + Link fields, BẮT BUỘC tuân thủ:

- **LL-BE-7** (workflow state via Draft + transition): insert luôn ở INITIAL state, transition sau insert. Xem `assetcore-be/SKILL.md`.
- **LL-BE-8** (resolve display→code): user fill template với category_name/model_name/etc. → resolver lookup → set PK code trước insert. Xem `assetcore-be/SKILL.md`.
- **LL-BE-26** (Tree DocType parent resolve, 2026-05-28): mọi Tree DocType (`is_tree: 1`) có `nsm_parent_field` PHẢI có entry trong `_RESOLVABLE_LINKS_BY_DOCTYPE` map `<parent_field> → (<self_doctype>, <display_field>)`. Thiếu = Frappe core crash `"Could not find Parent <Doctype>: <display>"`. Validator phải warn nếu parent xuất hiện sau child trong file (order dependency).
- **LL-IMP-1** (Validator accept-both, 2026-05-28): mọi validator check Link field PHẢI dùng `_link_lookup_set(doctype, display_field)` — chứa cả `name` và `display_field`. KHÔNG bao giờ check `value in {r.name for r in frappe.get_all(...)}` riêng lẻ, KHÔNG bao giờ `frappe.db.exists("AC Supplier", supplier)` mà không union display field. Lý do: template hướng dẫn user nhập display name, resolver accept cả 2, validator phải nhất quán nếu không sẽ reject input hợp lệ.

Pattern reference đầy đủ: `api/import_data.py:_do_import` (164-211) + `_transition_asset_lifecycle` (228-247) + `_cascade_skip_for_tree` (§1.8 spec).
