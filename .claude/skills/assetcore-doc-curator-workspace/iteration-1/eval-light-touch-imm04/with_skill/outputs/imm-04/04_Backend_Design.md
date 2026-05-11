# 04 — Thiết kế Backend (Backend Design)

| Mục | Giá trị |
|---|---|
| Module | IMM-04 — Lắp đặt, Định danh & Kiểm tra Ban đầu |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | 02 Analysis & Design · 03 Diagrams · 05 API |

> **Mục đích**: Hợp đồng giữa Tech Lead và BE Dev — implementation chi tiết: DocType, workflow, hooks, service, scheduler, audit, integration, patches.

---

## 1. Tổng quan kiến trúc

Bám 3-tier strict: **API → Service → DocType → ORM**.

```
HTTP Request
      │
      ▼
API Layer  (assetcore/api/imm04.py — 17 endpoints)
      │   _ok / _err envelope; permission check; payload parse
      ▼
Service Layer  (assetcore/services/imm04.py)
      │   business rules, gates, lifecycle event logging
      ▼
Controller  (assetcore/doctype/asset_commissioning/asset_commissioning.py)
      │   before_insert / before_save / validate / on_submit / on_cancel
      ▼
Frappe ORM → MariaDB
      │
      ▼
Side Effects:
  • AC Asset insert (create_ac_asset — trong services/imm04.py)
  • Document transfer sang IMM-05 (_transfer_commissioning_documents_to_asset)
  • Depreciation schedule (services/depreciation.generate_schedule)
  • Realtime publish (imm04_asset_released)
  • Lifecycle Event row (immutable VR-06)
```

> **Quy ước ngôn ngữ BE:**
> - Code (function, class, variable): **tiếng Anh** snake_case / PascalCase
> - DocType **fieldname**: tiếng Anh (`vendor_serial_no`, `board_approver`)
> - DocType **field label** (Frappe form): **tiếng Việt** (`Số serial NCC`, `Người phê duyệt BGĐ`)
> - **Enum value**: tiếng Anh (`Clinical Release`); label tiếng Việt qua i18n
> - Naming series: tiếng Anh + số (`ACC-.YY.-.MM.-.#####`)
> - DTO mirror FE TypeScript types 1-1 — sai lệch = bug

---

## 2. Domain Model — DocType

### 2.1 `Asset Commissioning`

**Autoname:** `ACC-.YY.-.MM.-.#####` | **is_submittable:** 1 | **track_changes:** 1 | **track_views:** 1

**Workflow:** `IMM-04 Workflow` (state field: `workflow_state`)

| Trường | Type | Required | Default | Validation |
|---|---|---|---|---|
| `workflow_state` | Link Workflow State | — | Draft | read_only |
| `po_reference` | Link AC Purchase | YES | — | PO exists + not Cancelled |
| `master_item` | Link IMM Device Model | YES | — | device model exists |
| `vendor` | Link AC Supplier | YES | — | exists |
| `clinical_dept` | Link AC Department | YES | — | exists |
| `expected_installation_date` | Date | YES | — | ≥ today |
| `reception_date` | Date | — | today() auto-set | ≤ today |
| `installation_date` | Datetime | — | auto khi Installing | read_only |
| `vendor_serial_no` | Data | YES (Identification) | — | UNIQUE (VR-01) |
| `internal_tag_qr` | Data | — | auto-sinh BV-DEPT-YYYY-SEQ | read_only |
| `is_radiation_device` | Check | — | 0 | read_only, fetch_from item |
| `risk_class` | Select A/B/C/D/Radiation | — | — | VR-05 warning khi đổi |
| `board_approver` | Link User | YES (before Submit) | — | G06 |
| `qa_license_doc` | Attach | COND | — | reqd nếu radiation (VR-07) |
| `final_asset` | Link AC Asset | — | — | set by create_ac_asset() on submit |
| `baseline_tests` | Table Commissioning Checklist | YES | — | G03: 100% Pass/N/A |
| `commissioning_documents` | Table Commissioning Document Record | — | — | G01: mandatory Received/Waived |
| `lifecycle_events` | Table Asset Lifecycle Event | — | — | VR-06: immutable |
| `docstatus` | Int | — | 0 | 0=Draft, 1=Submitted, 2=Cancelled |

**Naming series:** `ACC-.YY.-.MM.-.#####` (YY=năm 2 số, MM=tháng 2 số)

**Permissions sơ bộ:**

| Role | Create | Read | Write | Submit | Cancel | Amend |
|---|---|---|---|---|---|---|
| HTM Technician | ✓ | ✓ | ✓ | — | — | — |
| Biomed Engineer | — | ✓ | ✓ | — | — | — |
| Workshop Head | — | ✓ | — | ✓ | ✓ | ✓ |
| VP Block2 | — | ✓ | — | ✓ | ✓ | — |
| QA Risk Team | — | ✓ | ✓ | — | — | — |

**Indexes DB:**
- `po_reference` — search_index
- `vendor_serial_no` — search_index (khuyến nghị thêm UNIQUE)
- `workflow_state` — in_standard_filter
- Composite (khuyến nghị): `(workflow_state, docstatus, reception_date)`

---

## 3. Workflow

**File fixture:** `assetcore/assetcore/workflow/imm_04_workflow.json`
**Workflow name:** `IMM-04 Workflow`
**workflow_state_field:** `workflow_state`

**States — tên chính xác trong workflow_state field:**

> Cảnh báo: workflow_state values dùng underscore khi stored trong DB và trong TypeScript types (xác nhận từ `types/imm04.ts`). Một số label display có thể khác.

| workflow_state value | Style | docstatus | Gate |
|---|---|---|---|
| `Draft` | Success | 0 | — |
| `Pending_Doc_Verify` | Warning | 0 | G01 |
| `To_Be_Installed` | Success | 0 | G02 |
| `Installing` | Success | 0 | — |
| `Identification` | Success | 0 | VR-01 |
| `Initial_Inspection` | Success | 0 | G03 |
| `Non_Conformance` | Warning | 0 | — |
| `Clinical_Hold` | Warning | 0 | G04 |
| `Re_Inspection` | Success | 0 | — |
| `Pending_Release` | Warning | 0 | — |
| `Clinical_Release` | Success | 1 | G05+G06+GW-2 (terminal) |
| `Return_To_Vendor` | Danger | 1 | terminal negative |
| `DOA_Incident` | Danger | 0 | — |

Service code constants: `_STATE_CLINICAL_RELEASE = "Clinical Release"`, `_STATE_INITIAL_INSPECTION = "Initial Inspection"`, `_STATE_RE_INSPECTION = "Re Inspection"`, `_TERMINAL_STATES = {"Clinical Release", "Return To Vendor"}` — đây là giá trị so sánh trong service layer (space), cần đồng bộ với workflow config thực tế.

**TODO (Sprint 7):** Chuẩn hóa naming `Clinical Release` vs `Clinical_Release` — đây là tech debt đã ghi nhận trong README.md.

**Transitions (rút gọn từ codebase):**

| From → To | Ghi chú |
|---|---|
| `Draft` → `Pending_Doc_Verify` | Gửi kiểm tra tài liệu |
| `Pending_Doc_Verify` → `To_Be_Installed` | Xác nhận đủ tài liệu |
| `Pending_Doc_Verify` → `Draft` | Yêu cầu bổ sung |
| `To_Be_Installed` → `Installing` | Bắt đầu lắp đặt |
| `Installing` → `Identification` | Lắp đặt hoàn thành |
| `Installing` → `Non_Conformance` | Báo cáo DOA |
| `Identification` → `Initial_Inspection` | Bắt đầu kiểm tra |
| `Initial_Inspection` → `Clinical_Release` | Phê duyệt phát hành |
| `Initial_Inspection` → `Clinical_Hold` | Giữ lâm sàng |
| `Clinical_Hold` → `Clinical_Release` | Gỡ giữ lâm sàng |
| `Non_Conformance` → `Return_To_Vendor` | Trả lại NCC |

**Lifecycle hooks (controller chỉ delegate):**

```python
# assetcore/assetcore/doctype/asset_commissioning/asset_commissioning.py
class AssetCommissioning(Document):
    def validate(self):
        from assetcore.services.imm04 import validate_commissioning
        validate_commissioning(self)

    def before_insert(self):
        from assetcore.services.imm04 import initialize_commissioning
        initialize_commissioning(self)

    def before_save(self):
        # Set installation_date khi vào Installing; sinh internal_tag_qr khi vào Identification
        from assetcore.services.imm04 import before_save_commissioning
        before_save_commissioning(self)

    def on_submit(self):
        # Yêu cầu state = Clinical_Release
        self.create_ac_asset()
        self.create_initial_document_set()
        from assetcore.services.imm04 import log_lifecycle_event
        log_lifecycle_event(self, "Release", self.workflow_state, "Clinical Release", "")
        self.fire_release_event()

    def on_cancel(self):
        from assetcore.services.imm04 import handle_commissioning_cancel
        handle_commissioning_cancel(self)
```

---

## 4. Service Layer

**File:** `assetcore/services/imm04.py`

**Public functions:**

| Function | Input | Output | Side effect |
|---|---|---|---|
| `initialize_commissioning(doc)` | Document | None | Set reception_date, fetch risk_class, populate mandatory docs |
| `validate_commissioning(doc)` | Document | None | Chạy VR-01 → VR-07 + Gate checks |
| `validate_gate_g01(doc)` | Document | None | Raise ServiceError nếu mandatory docs không đủ |
| `validate_gate_g03(doc)` | Document | None | Raise nếu có baseline Fail |
| `validate_gate_g05_g06(doc)` | Document | None | Raise nếu Open NC tồn tại hoặc thiếu board_approver |
| `check_auto_clinical_hold(doc)` | Document | bool | Trả True nếu risk_class ∈ {C,D,Radiation} |
| `log_lifecycle_event(doc, event_type, from_s, to_s, remarks)` | Document + strings | None | Append lifecycle event row |
| `handle_commissioning_cancel(doc)` | Document | None | Block cancel nếu final_asset tồn tại |
| `check_commissioning_overdue()` | — | None | Email Workshop Head phiếu >30 ngày |

**Validators (private):**
- `_vr01_unique_serial_number(doc)` — UNIQUE check cross-table
- `_vr05_risk_class_change_warning(doc)` — msgprint (không block)
- `_vr06_immutable_lifecycle_events(doc)` — block edit existing rows
- `_validate_document_expiry(doc)` — throw nếu expired; warn nếu <30 ngày
- `validate_backdate(doc)` — installation_date ≥ PO transaction_date

**Error handling:**

```python
# assetcore/services/imm04.py
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def validate_gate_g01(doc) -> None:
    """Validate Gate G01: all mandatory documents must be Received or Waived."""
    missing = [
        row.doc_type
        for row in doc.commissioning_documents
        if row.is_mandatory and row.status not in ("Received", "Waived")
    ]
    if missing:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"VR-02 (Gate G01): Chưa đủ tài liệu bắt buộc. Còn thiếu: {', '.join(missing)}"
        )

def _vr01_unique_serial_number(doc) -> None:
    """VR-01: vendor_serial_no must be unique across Asset + Commissioning."""
    if not doc.vendor_serial_no:
        return
    existing = frappe.db.get_value(
        "Asset Commissioning",
        {"vendor_serial_no": doc.vendor_serial_no, "name": ("!=", doc.name), "docstatus": ("!=", 2)},
        "name"
    )
    if existing:
        raise ServiceError(
            ErrorCode.VALIDATION,
            f"VR-01: Serial Number '{doc.vendor_serial_no}' đã được đăng ký cho phiếu {existing}."
        )
```

---

## 4b. Repository Layer

**Pattern:** Wrap `frappe.get_all` / `frappe.get_doc` trong class hoặc module functions riêng — service không gọi ORM raw trực tiếp.

```python
# assetcore/repositories/imm04_repo.py (hoặc inline trong services/imm04.py)

class CommissioningRepo:
    @staticmethod
    def get(name: str):
        if not frappe.db.exists("Asset Commissioning", name):
            return None
        return frappe.get_doc("Asset Commissioning", name)

    @staticmethod
    def list_open(filters: dict, page: int = 1, page_size: int = 20):
        base_filters = {"docstatus": ("!=", 2), **filters}
        offset = (page - 1) * page_size
        rows = frappe.get_all(
            "Asset Commissioning",
            filters=base_filters,
            fields=["name", "workflow_state", "vendor", "master_item", "modified"],
            limit=page_size,
            start=offset,
            order_by="modified desc"
        )
        total = frappe.db.count("Asset Commissioning", filters=base_filters)
        return rows, total

    @staticmethod
    def get_open_nc_count(commissioning_name: str) -> int:
        return frappe.db.count(
            "Asset QA Non Conformance",
            {"ref_commissioning": commissioning_name, "resolution_status": "Open"}
        )
```

**Methods cần có:**
- `get(name)` — lấy 1 phiếu theo name
- `list_open(filters, page, page_size)` — list phiếu + pagination
- `get_open_nc_count(commissioning_name)` — đếm NC chưa đóng (G05)
- `check_sn_exists(vendor_serial_no, exclude_name)` — VR-01

---

## 5. API Layer

**File:** `assetcore/api/imm04.py`

**Pattern thin wrapper + _handle/_ok/_err:**

```python
# assetcore/api/imm04.py
from assetcore.utils.helpers import _ok, _err, _handle, _parse_json
import assetcore.services.imm04 as service

@frappe.whitelist(methods=["POST"])
def create_commissioning(data: str = "{}") -> dict:
    payload = _parse_json(data, field_name="data", default={})
    return _handle(service.create_commissioning_from_api, payload)

@frappe.whitelist()
def list_commissioning(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_commissioning, parsed, int(page), int(page_size))

@frappe.whitelist(methods=["POST"])
def submit_commissioning(name: str) -> dict:
    return _handle(service.submit_commissioning, name)

@frappe.whitelist(methods=["POST"])
def assign_identification(name: str, vendor_serial_no: str,
                          internal_tag_qr: str = "", custom_moh_code: str = "") -> dict:
    return _handle(service.assign_identification, name, vendor_serial_no, internal_tag_qr, custom_moh_code)
```

**Helper `_handle`:**

```python
def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception as e:
        frappe.log_error(title="IMM-04 API Error", message=str(e))
        return _err("Lỗi hệ thống. Vui lòng thử lại.", ErrorCode.INTERNAL)
```

> **Quy chuẩn cứng:**
> - Mọi endpoint vào API Catalog (file 05 §0)
> - Response success: `_ok(data)` → `{"success": true, "data": ...}`
> - Response error: `_err(msg_vi, code)` → `{"success": false, "error": ..., "code": ...}`
> - Service raise `ServiceError(ErrorCode.X, "msg tiếng Việt")`
> - `@frappe.whitelist(methods=["POST"])` cho mọi mutation
> - Input JSON parse qua `_parse_json()` — throw `ServiceError(INVALID_PARAMS)` nếu malformed

---

## 6. Audit Trail

| Trigger | Entry type | Actor | Payload lưu |
|---|---|---|---|
| `create_commissioning` | `commissioning_created` | session.user | from=None, to=Draft |
| Transition state | `state_transition` | session.user | from=prev_state, to=new_state, action |
| `assign_identification` | `identification` | session.user | vendor_serial_no, internal_tag_qr |
| `submit_baseline_checklist` | `baseline_test` | session.user | overall_result |
| `approve_clinical_release` → Submit | `release` | session.user | final_asset, commissioning_date |
| NC created | `non_conformance` | session.user | nc_name, nc_type |
| NC closed | `nc_closed` | session.user | nc_name, resolution_note |
| `on_cancel` | `cancel` | session.user | reason |

**Hash chain:** Sử dụng `Asset Lifecycle Event` child table với field `ip_address`. VR-06 enforce immutability bằng cách so sánh snapshot trong `validate()`. Không có SHA-256 hash chain tại thời điểm v2 — planned cho v3.

**Verify:** Xem `lifecycle_events` child table trực tiếp. API `get_form_context` trả đầy đủ `lifecycle_events[]`.

---

## 7. Background jobs / Scheduler

| Job | Tần suất | Hook trong hooks.py | Mục đích |
|---|---|---|---|
| `assetcore.services.imm04.check_commissioning_overdue` | daily | `scheduler_events["daily"]` | Email Workshop Head phiếu mở >30 ngày |
| `assetcore.tasks.check_clinical_hold_aging` | daily | `scheduler_events["daily"]` | Email QA Officer phiếu Clinical Hold quá N ngày |
| `assetcore.tasks.check_commissioning_sla` | daily | `scheduler_events["daily"]` | SLA vi phạm |

**Đăng ký trong `hooks.py`:**

```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm04.check_commissioning_overdue",
        "assetcore.tasks.check_clinical_hold_aging",
        "assetcore.tasks.check_commissioning_sla",
    ],
}
```

**Logic `check_commissioning_overdue`:**

```python
def check_commissioning_overdue() -> None:
    """Daily: email Workshop Head for open commissioning > 30 days."""
    threshold = frappe.utils.add_days(frappe.utils.today(), -30)
    overdue = frappe.get_all(
        "Asset Commissioning",
        filters={
            "docstatus": 0,
            "workflow_state": ("not in", ["Clinical Release", "Return To Vendor"]),
            "reception_date": ("<", threshold),
        },
        fields=["name", "master_item", "workflow_state", "reception_date"],
    )
    if overdue:
        # send email to Workshop Head role users
        _notify_workshop_head_overdue(overdue)
```

---

## 8. Integration

**Module nội bộ:**

| Module | Chiều | Cơ chế |
|---|---|---|
| IMM-03 (Purchase Order) | IN | `po_reference` Link; `get_po_details()` auto-fill |
| IMM-05 (Asset Document) | OUT | `create_initial_document_set()` khi on_submit |
| IMM-04 ← IMM-05 | IN | GW-2 gate: query Asset Document Active cho asset |
| IMM-08 (PM Schedule) | OUT (TODO) | `fire_release_event()` publish `imm04_asset_released` — IMM-08 chưa subscribe |
| IMM-12 / QMS | OUT | `Asset QA Non Conformance.transfer_to_capa` flag |

**doc_events trong hooks.py:**

```python
doc_events = {
    "Asset Commissioning": {
        "before_insert": "assetcore.services.imm04.initialize_commissioning",
    },
}

fixtures = [
    {"dt": "Workflow", "filters": [["name", "in", ["IMM-04 Workflow"]]]},
    {"dt": "Required Document Type"},
    {"dt": "Custom Field", "filters": [["dt", "in", ["Asset"]]]},
]
```

---

## 9. Migration & Patch

**Patch path:** `assetcore/patches/v2/001_imm04_initial_setup.py`

**Đăng ký trong `patches.txt`:**
```
assetcore.patches.v2.001_imm04_initial_setup
```

**Migration steps:**
1. `bench --site <site> migrate` — apply DocType JSON
2. Import workflow fixture: `imm_04_workflow.json`
3. Seed `Required Document Type`: CO, CQ, Manual, Warranty, License, Radiation License
4. Import Custom Fields trên `Asset`: `custom_vendor_serial`, `custom_internal_qr`, `custom_comm_ref`
5. Tạo Role nếu chưa có: HTM Technician, Biomed Engineer, Vendor Engineer, QA Officer, Workshop Head, VP Block2

---

## 10. Non-functional

**Concurrency:**
- `vendor_serial_no` unique: app-layer check (VR-01) + khuyến nghị DB UNIQUE index (tech-debt)
- `create_ac_asset()`: dùng `db_set` commit ngay; cần wrap savepoint để rollback nếu IMM-05 import fail

**Caching:**
- `get_dashboard_stats()`: không cache hiện tại; recommend Redis cache TTL 5 phút
- `get_po_details()`: không cache; PO data ít thay đổi → TTL 1 phút acceptable

**Logging:**
- INFO: mọi lifecycle event created
- WARNING: VR-05 risk_class change, overdue phiếu
- ERROR: `create_ac_asset` fail, `create_initial_document_set` exception

**Idempotency:**
- `generate_qr_label()`: idempotent — nếu `internal_tag_qr` đã có, trả giá trị hiện tại
- `create_initial_document_set()`: graceful skip nếu document đã tồn tại (`source_commissioning` check)

---

## DoD — File 04 hoàn chỉnh

- [x] Quy ước ngôn ngữ BE: code tiếng Anh + field label tiếng Việt
- [x] DocType đầy đủ trường + naming + permissions sơ bộ
- [x] Workflow 11 states + transition matrix
- [x] Service layer public functions liệt kê + error handling pattern
- [x] Repository layer methods liệt kê
- [x] API layer thin wrapper với `_handle/_ok/_err`
- [x] Mọi error raise qua `ServiceError(ErrorCode.X, msg tiếng Việt)`
- [x] Audit trail trigger liệt kê
- [x] Scheduler jobs đăng ký
- [x] Integration nội bộ + ngoại bộ
- [x] Migration steps
- [x] Non-functional: concurrency, caching, logging, idempotency
