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
API Layer  (assetcore/api/imm04.py — 33 endpoints)
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
| `lifecycle_events` | Table Asset Lifecycle Event | — | — | VR-06: immutable ⚠️ field in field_order but missing from JSON fields array — add definition manually |
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

> Lưu ý: workflow_state values dùng **space** (không phải underscore) — xác nhận từ `imm_04_workflow.json`, `services/imm04.py` constants, và `types/imm04.ts` (`WorkflowState` enum). Tech debt naming đã được resolve.

| workflow_state value | Style | docstatus | Gate |
|---|---|---|---|
| `Draft` | Success | 0 | — |
| `Pending Doc Verify` | Warning | 0 | G01 |
| `To Be Installed` | Success | 0 | G02 |
| `Installing` | Success | 0 | — |
| `Identification` | Success | 0 | VR-01 |
| `Initial Inspection` | Success | 0 | G03 |
| `Non Conformance` | Warning | 0 | — |
| `Clinical Hold` | Warning | 0 | G04 |
| `Re Inspection` | Success | 0 | — |
| `Clinical Release` | Success | 1 | G05+G06+GW-2 (terminal) |
| `Return To Vendor` | Danger | 1 | terminal negative |

Service code constants: `_STATE_CLINICAL_RELEASE = "Clinical Release"`, `_STATE_INITIAL_INSPECTION = "Initial Inspection"`, `_STATE_RE_INSPECTION = "Re Inspection"`, `_TERMINAL_STATES = {"Clinical Release", "Return To Vendor"}` — đồng bộ giá trị space giữa service layer, workflow config, và FE types.

**Transitions (rút gọn từ codebase `imm_04_workflow.json`):**

| From → To | Ghi chú |
|---|---|
| `Draft` → `Pending Doc Verify` | Gửi kiểm tra tài liệu |
| `Pending Doc Verify` → `To Be Installed` | Xác nhận đủ tài liệu |
| `Pending Doc Verify` → `Draft` | Yêu cầu bổ sung |
| `To Be Installed` → `Installing` | Bắt đầu lắp đặt |
| `To Be Installed` → `Non Conformance` | Báo cáo sự cố trước lắp đặt |
| `Installing` → `Identification` | Lắp đặt hoàn thành |
| `Installing` → `Non Conformance` | Báo cáo DOA |
| `Identification` → `Initial Inspection` | Bắt đầu kiểm tra |
| `Initial Inspection` → `Clinical Release` | Phê duyệt phát hành |
| `Initial Inspection` → `Clinical Hold` | Giữ lâm sàng |
| `Clinical Hold` → `Clinical Release` | Gỡ giữ lâm sàng |
| `Non Conformance` → `Return To Vendor` | Trả lại NCC |

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
        # Yêu cầu state = Clinical Release
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
| `check_commissioning_overdue()` | — | None | Email Workshop Head phiếu >30 ngày (scheduler daily — ⚠️ CHƯA đăng ký trong hooks.py) |
| `submit_for_approval(commissioning, approver, stage, remarks)` | string + params | dict | Gửi phê duyệt nội bộ (Wave-2 approval flow) |
| `approve_pending(commissioning, decision, remarks)` | string + params | dict | Duyệt/từ chối phiếu đang chờ |
| `list_my_pending_approvals()` | — | list | Danh sách phiếu chờ duyệt của user hiện tại |
| `create_commissioning_from_purchase(purchase_name, device_idx)` | string + int | dict | Tạo phiếu từ PO |
| `get_commissioning_origin(asset_name)` | string | dict | Truy ngược asset → commissioning |
| `get_form_context(name)` | string | dict | Full context cho form view (FE) |
| `search_link(doctype, query, page_length)` | string | list | Frappe link search helper |
| `get_users_by_role(role, search, limit)` | string | list | Danh sách user theo Role |
| `get_gate_status(name)` | string | dict | Trạng thái G01–G06 cho 1 phiếu |
| `retry_mint_asset(name)` | string | dict | Tạo lại AC Asset nếu on_submit bị lỗi |
| `get_lifecycle_timeline(name)` | string | list | Timeline lifecycle events (FE) |

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

| Job | Tần suất | Trạng thái đăng ký | Mục đích |
|---|---|---|---|
| `assetcore.services.imm04.check_commissioning_overdue` | daily | *(Defined nhưng CHƯA đăng ký trong `hooks.py:scheduler_events`)* | Email Workshop Head phiếu mở >30 ngày |
| `assetcore.tasks.check_clinical_hold_aging` | daily | *(Not yet implemented — module không có `assetcore/tasks.py`)* | Email QA Officer phiếu Clinical Hold quá N ngày |
| `assetcore.tasks.check_commissioning_sla` | daily | *(Not yet implemented)* | SLA vi phạm |

> Ground truth `assetcore/hooks.py` (2026-05-14): chưa có entry IMM-04 nào trong `scheduler_events`. Để kích hoạt `check_commissioning_overdue`, cần thêm thủ công:

```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm04.check_commissioning_overdue",
        # 2 job clinical_hold_aging / commissioning_sla — backlog, chưa cài
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

**doc_events trong hooks.py (Wave-2 ground truth):**

```python
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_from_commissioning",
            "assetcore.services.imm11.create_calibration_schedule_from_commissioning",
            "assetcore.services.imm16.eval_imm04_realtime",
        ],
    },
}
```

> `before_insert` / `validate` cho Asset Commissioning KHÔNG đi qua `doc_events` mà gắn trực tiếp trong controller `assetcore/assetcore/doctype/asset_commissioning/asset_commissioning.py` (`def before_insert(self): imm04_svc.initialize_commissioning(self)` + `def validate(self): imm04_svc.validate_commissioning(self)`). Đây là pattern chuẩn AssetCore (controller delegates to service).

**Fixtures liên quan IMM-04** (trong `assetcore/fixtures/workflow.json` + `assetcore/fixtures/role_profile.json`): `IMM-04 Workflow` + Workflow States (`Pending Doc Verify`, `To Be Installed`, `Installing`, `Identification`, `Initial Inspection`, `Non Conformance`, `Clinical Hold`, `Re Inspection`, `Clinical Release`, `Return To Vendor`).

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
