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

**Overdue-SLA SoT (BR-04-10):** `OVERDUE_DAYS = 30` là **module-constant** (KHÔNG inline literal 30 ở ≥2 nơi). Date-anchor chốt = `reception_date` (theo KPI-04-01). Một helper SoT duy nhất:

```python
OVERDUE_DAYS = 30  # SLA threshold — single source, no inline literal
_OVERDUE_ANCHOR = "reception_date"  # date-anchor chốt (Core Doc KPI-04-01 §I.5)

def overdue_commissioning_filter(today: str | None = None) -> dict:
    """SoT predicate cho 'phiếu quá hạn SLA' — dùng chung scheduler + KPI + list drill.

    Trả filter dict thuần (frappe.db filter syntax) để cả 3 call-site cùng một định nghĩa.
    """
    cutoff = add_days(today or nowdate(), -OVERDUE_DAYS)
    return {
        _OVERDUE_ANCHOR: ("<", cutoff),
        "workflow_state": ("not in", list(_TERMINAL_STATES)),
        "docstatus": ("!=", 2),
    }
```

> ⚠️ Self-Correction (vòng 32): `get_dashboard_stats().overdue_sla` trước đây dùng `expected_installation_date` + `docstatus != 2`, còn `check_commissioning_overdue` dùng `reception_date` + `docstatus = 0` → **divergence**. Hợp nhất về `overdue_commissioning_filter()` (anchor `reception_date`, `docstatus != 2`) cho cả 3 call-site. Lưu ý hệ quả: scheduler cũ chỉ alert Draft (`docstatus=0`); SoT mới gồm cả phiếu đã Submit chưa terminal (`docstatus != 2`) — đúng định nghĩa "phiếu chưa Clinical Release vẫn đang chạy SLA". `_send_overdue_alert` tính `days_open = date_diff(nowdate(), <reception_date>)` từ **cùng anchor**.

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
| `overdue_commissioning_filter(today=None)` | str?/None | dict | **SoT** predicate "quá hạn SLA" (BR-04-10): `{reception_date < today−OVERDUE_DAYS, workflow_state NOT IN _TERMINAL_STATES, docstatus != 2}`. Pure, no side effect — dùng chung 3 call-site |
| `check_commissioning_overdue()` | — | None | Email Workshop Head phiếu quá hạn — gọi `overdue_commissioning_filter()` (KHÔNG inline `reception_date<cutoff`); `_send_overdue_alert` tính `days_open` từ cùng anchor (scheduler daily — ⚠️ CHƯA đăng ký trong hooks.py) |
| `_stamp_commissioning_date(doc)` (private) | Document | None | **SoT** stamp Clinical-Release date (BR-04-11). **Idempotent:** `if not doc.commissioning_date: doc.commissioning_date = nowdate()` (set khi NULL, KHÔNG ghi đè). Gọi bởi cả 3 write-path SAU khi `doc.workflow_state == _STATE_CLINICAL_RELEASE` được xác lập. Pure đối với mọi field khác. KHÔNG @whitelist (chỉ internal). Mutate doc in-memory — caller chịu trách nhiệm persist (`doc.save`/`doc.submit` đã có sẵn trong từng write-path) |
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

### 5.1. Overdue-SLA drill — KPI ↔ list cùng SoT (BR-04-10)

Cả 3 call-site phải dùng `overdue_commissioning_filter()`; KHÔNG nhân bản predicate.

**`get_dashboard_stats().kpis.overdue_sla`** — count thuần từ helper:

```python
"overdue_sla": frappe.db.count(_DT, overdue_commissioning_filter()),  # KHÔNG inline filter
```

**`list_commissioning(filters, ...)` — tham số ảo `overdue=1`:**

```python
_ALLOWED_FILTER_KEYS = frozenset({...})          # raw column keys (KHÔNG chứa 'overdue')
_VIRTUAL_FILTER_KEYS = frozenset({"overdue"})     # virtual: AND thêm SoT, không phải column

def list_commissioning(filters: dict, page=1, page_size=20) -> dict:
    safe_filters = {k: v for k, v in filters.items() if k in _ALLOWED_FILTER_KEYS}
    if "docstatus" not in safe_filters:
        safe_filters["docstatus"] = ("!=", 2)
    # Virtual 'overdue=1' → AND thêm SoT predicate (KHÔNG clobber filter khác).
    # reception_date của SoT ghi đè mọi reception_date người dùng truyền (overdue thắng).
    if _is_truthy(filters.get("overdue")):
        safe_filters.update(overdue_commissioning_filter())
    ...
```

**Quy tắc:**
- `'overdue'` nằm trong tập key **được nhận** (whitelist ảo riêng) — KHÔNG lọt qua `_ALLOWED_FILTER_KEYS` như raw column (tránh `WHERE overdue = 1` → SQL error / luôn rỗng).
- `safe_filters.update(...)` chỉ thêm/ghi đè 3 khoá SoT (`reception_date`, `workflow_state`, `docstatus`); các filter khác (`master_item`, `clinical_dept`, `vendor_serial_no`...) **giữ nguyên** → drill kết hợp được.
- Chấp nhận `overdue ∈ {1, "1", true}` qua helper truthy; `0/""/absent` → bỏ qua.

**INVARIANT (kiểm thử trên data-live):**
`get_dashboard_stats().kpis.overdue_sla == list_commissioning({"overdue": 1}, page=1, page_size=N).pagination.total` — card count == drill rows, **byte-for-byte**. Cùng `nowdate()` trong một request nên cùng cutoff.

**KHÔNG đổi (trong scope BR-04-10):** `pending_count`, `hold_count`, `open_nc_count` giữ nguyên — chỉ `overdue_sla` đổi anchor (`expected_installation_date` → `reception_date`). `released_this_month` được re-anchor riêng trong §5.2 (BR-04-11).

### 5.2. "Bàn giao tháng này" — stamp + KPI re-anchor cùng SoT (BR-04-11)

**Bài toán (lỗi thiết kế gốc):** `get_dashboard_stats().kpis.released_this_month` đếm theo `modified >= first_day_of_month`. `modified` là timestamp Frappe tự cập nhật mỗi lần `.save()` → phiếu Released **tháng trước** mà bị edit (sửa note / upload doc / re-approve) **tháng này** lập tức bị kéo vào `released_this_month` → KPI throughput thổi phồng. Đồng thời phiếu chưa có cột thời điểm bàn giao thật: field `commissioning_date` (Date, read_only) tồn tại trên DocType nhưng **chưa write-path nào stamp** — `approve_clinical_release` chỉ đọc `doc.commissioning_date or nowdate()` ở return value (line ~1470), không persist.

**Fix — 2 vế, cùng anchor `commissioning_date`:**

**(a) Stamp tại 3 write-path** — gọi `_stamp_commissioning_date(doc)` SAU khi `workflow_state` đã thành `Clinical Release`, TRƯỚC `doc.save()`/`doc.submit()`:

```python
def _stamp_commissioning_date(doc) -> None:
    """SoT (BR-04-11): set commissioning_date = ngày vào Clinical Release.
    Idempotent — KHÔNG ghi đè giá trị đã có (re-submit/re-approve/edit giữ ngày gốc)."""
    if doc.workflow_state == _STATE_CLINICAL_RELEASE and not doc.commissioning_date:
        doc.commissioning_date = nowdate()
```

Wiring (chính xác, dùng symbol THẬT đã verify trong imm04.py):
- **`transition_state(name, action)`** — sau `frappe.model.workflow.apply_workflow(doc, action)` (line ~1074) và TRƯỚC `doc.save(...)` (line ~1076): chèn `_stamp_commissioning_date(doc)`. Khi action đưa phiếu vào Clinical Release, doc.save persist commissioning_date cùng lượt (cùng khối auto-mint `create_ac_asset` đã có).
- **`submit_commissioning(name)`** — phiếu PHẢI đã ở `Clinical Release` (guard line ~1121). Stamp TRƯỚC `doc.submit()` (line ~1148): `_stamp_commissioning_date(doc)` (submit persist). Bảo hiểm cho phiếu vào Clinical Release từ trước fix mà chưa stamp.
- **`approve_clinical_release(...)`** — phiếu đã ở Clinical Release (guard line ~1447). Stamp TRƯỚC `doc.save(ignore_permissions=True)` (line ~1464): `_stamp_commissioning_date(doc)`. Return value đổi `str(doc.commissioning_date or nowdate())` → `str(doc.commissioning_date)` (sau stamp luôn non-NULL).

> ⚠️ Idempotency: 3 path có thể nối tiếp nhau trên cùng phiếu (transition → approve → submit). Guard `not doc.commissioning_date` đảm bảo chỉ path ĐẦU TIÊN chạm Clinical Release ghi ngày; các path sau no-op → ngày bàn giao bất biến. KHÔNG `update_modified=False` cần thiết (stamp đi cùng save/submit hợp lệ của chính write-path).

**(b) KPI re-anchor** trong `get_dashboard_stats()` — đổi count `released_this_month` từ `modified` sang `commissioning_date` trong cửa sổ tháng:

```python
first_day = get_first_day(nowdate())
today = nowdate()
...
"released_this_month": frappe.db.count(_DT, {
    "workflow_state": _STATE_CLINICAL_RELEASE, "docstatus": 1,
    "commissioning_date": ("between", [str(first_day), str(today)]),
}),
```

> ⚠️ Dùng **MỘT** tuple `("between", [first_day, today])` cho cột `commissioning_date` — KHÔNG tách 2 predicate cùng key `commissioning_date` trong filter dict (dict key trùng bị overwrite, chỉ còn 1 bound). Pattern `["between", [...]]` đã proven trong codebase: `imm05.py:361/409`, `imm06.py:1461`. `frappe.db.count` truyền filters qua cùng query-builder với `get_all` → `between` hợp lệ.

- `("between", [first_day, today])` ⟺ `commissioning_date >= first_day AND <= today` (inclusive 2 đầu). `commissioning_date` NULL → `BETWEEN` loại tự nhiên (NULL không thỏa) → phiếu legacy NULL **không** crash, **không** lọt count (BR-04-11c).
- Cùng `nowdate()` trong một request → `first_day`/`today` ổn định cho cả card lẫn drill list.

**INVARIANT đo được (mirror §5.1, SoT-aligned):**
`released_this_month == count({workflow_state==Clinical Release, docstatus==1, commissioning_date ∈ [first_day, today]})` == số rows drill list `Clinical Release` lọc cùng cửa sổ tháng. Card == drill.

**KHÔNG đổi:** shape của `get_dashboard_stats()` (key `released_this_month` giữ nguyên type `int`/number); `states_breakdown`, `recent_list`, các KPI khác bất biến. KHÔNG schema migration (field đã có). Backfill phiếu Clinical Release legacy `commissioning_date` NULL = **optional, ngoài scope** (nếu cần: patch set `commissioning_date = modified` hoặc `creation` cho rows `workflow_state=Clinical Release AND commissioning_date IS NULL` — KHÔNG bắt buộc cho task này).

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
| `assetcore.services.imm04.check_commissioning_overdue` | daily | **ĐÃ đăng ký** trong `hooks.py:scheduler_events["daily"]` (2026-06-03) | Email Workshop Head phiếu quá hạn SLA (reception_date < today−OVERDUE_DAYS) |
| `assetcore.tasks.check_clinical_hold_aging` | daily | *(Not yet implemented — module không có `assetcore/tasks.py`)* | Email QA Officer phiếu Clinical Hold quá N ngày |
| `assetcore.tasks.check_commissioning_sla` | daily | *(Not yet implemented)* | SLA vi phạm |

> Ground truth `assetcore/hooks.py` (2026-06-03): `check_commissioning_overdue` đã được đăng ký trong `scheduler_events["daily"]` (cùng SoT `overdue_commissioning_filter()` với dashboard KPI + list drill). 2 job `clinical_hold_aging` / `commissioning_sla` vẫn backlog (chưa cài):

```python
scheduler_events = {
    "daily": [
        "assetcore.services.imm04.check_commissioning_overdue",  # ✅ registered 2026-06-03
        # 2 job clinical_hold_aging / commissioning_sla — backlog, chưa cài
    ],
}
```

**Logic `check_commissioning_overdue` (dùng SoT — BR-04-10):**

```python
def check_commissioning_overdue() -> None:
    """Daily: email Workshop Head for commissioning quá hạn SLA.

    Dùng SoT `overdue_commissioning_filter()` — KHÔNG inline `reception_date<cutoff`
    để scheduler-alert / KPI count / list drill luôn cùng định nghĩa.
    """
    overdue = frappe.get_all(
        "Asset Commissioning",
        filters=overdue_commissioning_filter(),
        fields=["name", "vendor", "workflow_state", "reception_date", "commissioned_by"],
    )
    for comm in overdue:
        # days_open tính từ CÙNG anchor đã chốt (reception_date)
        _send_overdue_alert(comm, date_diff(nowdate(), comm["reception_date"]))
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

## 8.1. QR cấp tài sản (Asset-level QR) — tương thích ngược với commissioning

> **Quyết định cuối:** [`./ADR-001-asset-qr.md`](./ADR-001-asset-qr.md). Tóm tắt tác động lên IMM-04 — schema/contract chi tiết ở [`../imm-00/04_Backend_Design.md`](../imm-00/04_Backend_Design.md) §II.1.8.

**Bối cảnh:** QR cấp tài sản (`AC Asset.qr_token` + deep-link `/a/<token>`) là cơ chế MỚI ở IMM-00 registry, **song song** với QR cấp commissioning đang có ở IMM-04 (`internal_tag_qr`).

| QR cũ (IMM-04 commissioning) | QR mới (IMM-00 asset) |
|---|---|
| Field `Asset Commissioning.internal_tag_qr` = `BV-{DEPT}-{YYYY}-{SEQ}` | Field `AC Asset.qr_token` = `secrets.token_urlsafe(16)` |
| Sinh ở `assign_identification` (`services/imm04.py:543`) | Sinh `before_insert` mọi asset (3-tier ở IMM-00) |
| Encode **chuỗi tag** (scanner-wedge gõ tay/đầu đọc) | Encode **URL** `/a/<token>` (camera điện thoại quét → màn info) |
| Đoán được (DEPT+YYYY+SEQ tuần tự) + doc-bound | Enumeration-safe + idempotent + sống ở cấp tài sản |

**Quy tắc tương thích ngược (ADR-001 D6):**
- **GIỮ NGUYÊN field** `internal_tag_qr` + `assign_identification` / `generate_internal_qr` / `get_barcode_lookup` (`services/imm04.py:543,1350,921`) — KHÔNG breaking change. Field vẫn read-only + scanner-wedge lookup theo `internal_tag_qr` vẫn chạy. Nhãn tag-string đã in vẫn quét được bằng đầu đọc.
- Vòng A (A1→A6) **KHÔNG đụng** logic QR của IMM-04. Hai cơ chế chạy song song trong giai đoạn chuyển tiếp.

#### 8.1.1 — Dedup `generate_qr_label` → deep-link asset (CHỐT vòng 13 / B-3 — ADR-001 §D6.1)

> **Quyết định cuối:** [`./ADR-001-asset-qr.md`](./ADR-001-asset-qr.md) §D6.1. Đây là **delta DUY NHẤT** vòng 13 trên IMM-04 — chỉ contract nhãn của `generate_qr_label`, KHÔNG field/cap/DocType/enum/patch mới.

**RC dedup:** trước vòng 13 có 2 đường QR quét-được trên 1 thiết bị → (1) `generate_qr_label` mã hoá `internal_tag_qr` tuần tự + `scan_url=/app/asset-commissioning/<name>` (desk); (2) deep-link asset `/a/<token>` enumeration-safe. Sau vòng 13: **CHỈ còn (2)**.

`generate_qr_label` ủy quyền (delegate) việc dựng deep-link sang helper QR cấp asset của IMM-00 — **KHÔNG copy-paste** logic sinh token/URL:

```python
# services/imm04.py::generate_qr_label — sau check permission + internal_tag_qr
# Ưu tiên gọi 1 entry point public (tránh import symbol private _build_qr_url cross-module):
from assetcore.services.imm00 import build_asset_label_data  # lazy import (Pattern B)

qr_url = None
if doc.final_asset:
    # build_asset_label_data nội bộ đã: ensure_asset_qr_token (idempotent — token-less → sinh
    # + emit qr_generated 1 lần) → _build_qr_url(token) (get_url("/a/{token}"), host từ site config).
    qr_url = build_asset_label_data(doc.final_asset)["qr_url"]
# (Tương đương: token = ensure_asset_qr_token(doc.final_asset); qr_url = _build_qr_url(token))

return {
    "qr_value": doc.internal_tag_qr,    # GIỮ — FE fallback khi qr_url rỗng + tương thích nhãn cũ
    "qr_url": qr_url,                   # MỚI: deep-link tuyệt đối /a/<token> hoặc None (phiếu chưa mint asset)
    "label": { ... },                   # GIỮ nguyên các field nhãn
    "docs_url": ...,                    # GIỮ nguyên (không trong scope)
    # scan_url: BỎ HẲN (desk-login) — thay bằng qr_url
}
```

| # | Quy tắc | Chi tiết |
|---|---|---|
| 1 | `qr_url` khi có `final_asset` | Chuỗi tuyệt đối `/a/<token>` qua `ensure_asset_qr_token(final_asset)` + `_build_qr_url`. 1 helper duy nhất (dedup THẬT). |
| 2 | Edge token-less | Phiếu CHƯA có `final_asset` → `qr_url=None`, KHÔNG gọi `ensure_asset_qr_token`, KHÔNG throw. Nhãn fallback `commissioning_id`. |
| 3 | `scan_url` desk → BỎ | Field `scan_url=/app/asset-commissioning/<name>` xoá khỏi contract; FE đọc `qr_url`. |
| 4 | `docs_url` | GIỮ nguyên — ngoài scope. |
| 5 | RBAC | GIỮ `has_permission("Asset Commissioning","read")`. `ensure_asset_qr_token` chỉ set token, KHÔNG nâng quyền. |
| 6 | Lifecycle | KHÔNG double-emit `qr_generated` (ensure idempotent). KHÔNG emit `label_printed` (đó là `mark_label_printed` POST). |

**Endpoint QR cấp asset (A2/A3 — CHỐT ownership ở IMM-00 registry, KHÔNG IMM-04):**

**Endpoint QR cấp asset (A2/A3 — CHỐT ownership ở IMM-00 registry, KHÔNG IMM-04):**
- **Ownership chốt:** endpoint QR asset-bound đặt ở **`api/imm00.py` + `services/imm00.py`** (cùng nhà `AC Asset.qr_token` + `ensure_asset_qr_token` + `resolve_qr_token`). IMM-04 chỉ tham chiếu chéo — KHÔNG host logic QR asset. Spec đầy đủ: [`../imm-00/04_Backend_Design.md`](../imm-00/04_Backend_Design.md) §II.1.8b + [`../imm-00/05_API_Specification.md`](../imm-00/05_API_Specification.md).
- `assetcore.api.imm00.get_asset_label_data(asset)` / `get_asset_label_data_batch(assets)` → trả payload nhãn (`name, asset_code, device_model_name, location_name, lifecycle_status, qr_url`); **READ-ONLY về sự kiện in** (KHÔNG emit `label_printed`). Khác `generate_qr_label` (commissioning-bound, `internal_tag_qr`) — endpoint mới asset-bound (`qr_url = /a/<token>`).
- `assetcore.api.imm00.mark_label_printed(assets)` (POST) → emit lifecycle `label_printed` + audit, 1 event / asset / lần in.
- `assetcore.api.imm00.resolve_qr_token(token)` (A2 — V3, **đã có**): IMM-00 ownership. RBAC `asset.read`. Xem ADR-001 D2/D4.
- **A3 KHÔNG đụng IMM-04** `generate_qr_label`/`internal_tag_qr`. **Dedup CHỐT ở vòng 13 (§8.1.1):** `generate_qr_label` thêm `qr_url=/a/<token>` (tái dùng `ensure_asset_qr_token`+`_build_qr_url`), bỏ `scan_url` desk — field `internal_tag_qr` vẫn GIỮ.

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
- `generate_qr_label()`: idempotent — `internal_tag_qr` đã có → trả giá trị hiện tại; `qr_url` (vòng 13) dựng qua `ensure_asset_qr_token` (idempotent — không sinh token thừa, không double-emit `qr_generated`)
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
