# 04 — Thiết kế Backend (Backend Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-`<XX>` |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | 02 Analysis & Design · 03 Diagrams · 05 API |

> **Mục đích**: Hợp đồng giữa Tech Lead và BE Dev — implementation chi tiết: DocType, workflow, hooks, service, scheduler, audit, integration, patches. Code phải khớp doc này.

---

## 1. Tổng quan kiến trúc
**Viết gì**: Reference 01 §I. Bám 3-tier strict (API → Service → DocType). 1 sơ đồ ASCII đơn giản nếu cần highlight đặc thù module.

> **Quy ước ngôn ngữ BE (bám 01 §IV.1.b)**:
> - Code (function, class, variable, file): **tiếng Anh** snake_case / PascalCase
> - DocType **fieldname**: tiếng Anh (`asset`, `priority`, `sla_due_at`)
> - DocType **field label** (Frappe-native form đọc): **tiếng Việt** (`Thiết bị`, `Mức ưu tiên`)
> - **Enum value**: tiếng Anh (`Emergency`); label hiển thị tiếng Việt qua i18n (`Khẩn cấp`)
> - **Data text-content** (description, note, symptom): có thể tiếng Việt (user nhập)
> - Naming series: tiếng Anh + số (`WO-RP-.YYYY.-.#####`)
> - **DTO / TypedDict** mirror với FE TypeScript types (xem 05 §1.4) — sai lệch = bug

## 2. Domain Model — DocType
**Viết gì**: Cho mỗi DocType chính:
- Bảng field: `Trường · Type · Required · Default · Validation`
- Naming series (vd `WO-RP-.YYYY.-.#####`)
- Permissions matrix sơ bộ (chi tiết ở 07 §III Security)
- Child tables
- Quan hệ liên DocType
- Indexes DB

## 3. Workflow
**Viết gì**:
- File fixture path `assetcore/workflow/imm_<XX>_<entity>_workflow.json`
- Bảng States: `State · Style (Warning/Primary/Success/Danger) · docstatus · editable · allow_edit role`
- Bảng Transitions: `From · To · Action label · Allowed role · Condition`
- Lifecycle hooks DocType controller (chỉ delegate qua service)

```python
# assetcore/assetcore/doctype/asset_repair/asset_repair.py
class AssetRepair(Document):
    def validate(self):
        from assetcore.services.imm<XX> import validate_repair
        validate_repair(self)

    def before_save(self):
        from assetcore.services.imm<XX> import compute_sla
        compute_sla(self)

    def on_submit(self):
        from assetcore.services.imm<XX> import open_repair
        open_repair(self)
```

## 4. Service Layer
**Viết gì**: 4 mục con —
- **Public functions**: bảng `Function · Input · Output · Side effect`. Pattern: function-based, type hints đầy đủ, docstring tiếng Anh.
- **Validators** (private `_check_*` / `_validate_*`): liệt kê từng check.
- **State machine**: thường declare bằng class constants (vd `class RepairStatus: OPEN = "Open"; ASSIGNED = ...`) HOẶC dùng workflow JSON. Cả 2 đều OK — chọn đồng nhất per module.
- **Error handling**: raise `ServiceError(ErrorCode.X, "message tiếng Việt")` — KHÔNG raise raw `Exception` / `frappe.ValidationError`. ErrorCode list xem 05 §1.3.

```python
# Pattern thực tế
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def create_repair(asset_name: str, priority: str = "Normal") -> dict:
    """Create repair work order from asset."""
    asset = RepairRepo.get_asset(asset_name)
    if not asset:
        raise ServiceError(ErrorCode.NOT_FOUND, "Không tìm thấy thiết bị")
    if asset.status == "Decommissioned":
        raise ServiceError(ErrorCode.BAD_STATE, "Thiết bị đã ngưng sử dụng")
    # ... business logic
    return {"name": wo.name, "workflow_state": wo.workflow_state}
```

## 4b. Repository Layer (data access)
**Viết gì**: Pattern **đã established** trong AssetCore — không phải optional. File `assetcore/repositories/imm<XX>_repo.py` hoặc class trong service file. Wrap `frappe.get_all` / `frappe.get_doc` / `frappe.db.sql` — service không gọi trực tiếp Frappe ORM với raw filter.

```python
class RepairRepo:
    @staticmethod
    def get(name: str) -> Document | None:
        if not frappe.db.exists("AC Asset Repair", name):
            return None
        return frappe.get_doc("AC Asset Repair", name)

    @staticmethod
    def list(filters: dict, page: int = 1, page_size: int = 20) -> tuple[list, int]:
        offset = (page - 1) * page_size
        rows = frappe.get_all("AC Asset Repair", filters=filters, ...)
        total = frappe.db.count("AC Asset Repair", filters=filters)
        return rows, total

    @staticmethod
    def create(payload: dict) -> Document:
        doc = frappe.get_doc({"doctype": "AC Asset Repair", **payload})
        doc.insert()
        return doc
```

Liệt kê các method repo cần có cho module này.

## 5. API Layer (mức module)
**Viết gì**: File `assetcore/api/imm<XX>.py` + nguyên tắc thin wrapper (parse → service → format). Pattern thực tế dùng helper `_handle()` + `_ok()` / `_err()`:

```python
# assetcore/api/imm<XX>.py
@frappe.whitelist(methods=["POST"])
def create_repair(asset: str, priority: str = "Normal") -> dict:
    return _handle(service.create_repair, asset, priority)

@frappe.whitelist()
def list_repair_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20):
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_repairs, parsed, int(page), int(page_size))
```

Helper `_handle(fn, *args, **kwargs)`:

```python
def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
```

> **Quy chuẩn cứng (bám 01 §IV.2 + 05)**:
> - Mọi endpoint vào **API Catalog** module (file 05 §0)
> - Response success: envelope `_ok(data) → {"success": true, "data": ...}`
> - Response error: envelope `_err(msg, code) → {"success": false, "error": ..., "code": ...}` (xem 05 §1.2)
> - Service raise `ServiceError(ErrorCode.X, "msg tiếng Việt")` — handler tự convert
> - HTTP status luôn 200 — phân biệt success/error qua field `success`
> - `@frappe.whitelist(methods=["POST"])` cho mutation; mặc định cho read thuần
> - Input parse JSON qua `_parse_json()` — throw `ServiceError(INVALID_PARAMS)` nếu malformed
> - DTO mirror FE TypeScript type 1-1 (FE đã có `frontend/src/types/imm<XX>.ts`)

## 6. Audit Trail
**Viết gì**:
- Bảng `Trigger · Entry type · Actor · Payload`
- Hash chain spec: SHA-256 + canonical JSON + prev_hash
- Verify endpoint: `audit.verify_chain(doctype, name) -> (is_valid, broken_at)`

## 7. Background jobs / Scheduler
**Viết gì**: Bảng `Job · Tần suất · Hook · Mục đích`. Đăng ký trong `hooks.py:scheduler_events`.

## 8. Integration
**Viết gì**: 2 mục con —
- **Module nội bộ**: cross-module dependency (vd IMM-12 → IMM-09 qua Lifecycle Event)
- **Bên ngoài**: HIS / FHIR / Email / SMS (nếu có)

## 9. Migration & Patch
**Viết gì**:
- Patch path `assetcore/patches/v<X>/<NNN>_<slug>.py`
- Đăng ký `patches.txt`
- Fixtures cần export khi schema ổn định

## 10. Non-functional
**Viết gì**: Mục con cho:
- **Concurrency**: `for_update`, `modified` field check
- **Caching**: key + TTL + invalidate rule
- **Logging**: level (INFO/WARNING/ERROR) + target
- **Idempotency**: key + behavior

---

## DoD — File 04 hoàn chỉnh

- [ ] **Quy ước ngôn ngữ BE**: code tiếng Anh + field label tiếng Việt + DTO mirror FE
- [ ] DocType nêu đầy đủ trường + naming + permissions sơ bộ
- [ ] Quan hệ liên DocType vẽ rõ
- [ ] Workflow / state machine định nghĩa rõ (workflow JSON HOẶC class constants)
- [ ] Mọi mutation map về 1 service function (function-based + type hints)
- [ ] **Repository layer** liệt kê method (`get`, `list`, `create`, …) — không gọi `frappe.get_doc` rải rác trong service
- [ ] **Mọi error raise qua `ServiceError(ErrorCode.X, msg)`** — không raw string / Exception
- [ ] **API layer** dùng `_handle / _ok / _err` envelope — không inline try/except
- [ ] Audit trail entry liệt kê đủ trigger
- [ ] Index DB cho query nóng
- [ ] Background job đăng ký rõ
- [ ] Integration nội bộ + ngoại bộ liệt kê
- [ ] Patch path xác định cho mọi schema change
- [ ] Reviewed bởi BE Lead + (nếu chạm FE) FE Lead + DBA
