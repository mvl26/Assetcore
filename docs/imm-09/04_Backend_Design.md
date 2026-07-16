# 04 — Thiết kế Backend — IMM-09 Sửa chữa (Corrective Maintenance)

| Mục | Giá trị |
|---|---|
| Module | IMM-09 — Corrective Maintenance / Repair |
| Phạm vi | Per-module |
| Owner | Tech Lead / BE Lead |
| Liên kết | [02 Analysis & Design](./02_Analysis_Design.md) · [03 Diagrams](./03_Diagrams.md) · [05 API](./05_API_Specification.md) |
| Cập nhật | 2026-05-14 |

---

## 1. Tổng quan kiến trúc

IMM-09 bám kiến trúc **3-tier strict**: API → Service → DocType/ORM. Logic nghiệp vụ tập trung trong `services/imm09.py`. Controller `asset_repair.py` chỉ delegate sang service. API layer (`api/imm09.py`) là thin wrapper dùng `_handle / _ok / _err`.

```
Browser/Client
    │ HTTP (token/sid)
    ▼
api/imm09.py          ← 12 endpoints, thin wrapper
    │
    ▼
services/imm09.py     ← 13+ business functions, SLA, MTTR, lifecycle events
    │
    ▼
asset_repair.py       ← controller hooks (delegate sang service)
    │
    ▼
Frappe ORM + MariaDB  ← 4 DocTypes
```

> **Quy ước ngôn ngữ:** Code/fieldname tiếng Anh · Field label tiếng Việt · Error message tiếng Việt qua `frappe._()` · DTO mirror FE TypeScript types trong `frontend/src/types/imm09.ts`

---

## 2. Domain Model — DocType

### 2.1 Asset Repair

- **Naming:** `WO-CM-.YYYY.-.#####`
- **Submittable:** Yes — immutable sau docstatus=1
- **Track changes:** Yes

| Trường | Type | Required | Notes |
|---|---|---|---|
| `asset_ref` | Link → Asset | ✓ | search_index, in_list_view |
| `incident_report` | Link Incident Report | BR-09-01 | OR source_pm_wo |
| `source_pm_wo` | Link PM Work Order | BR-09-01 | OR incident_report |
| `repair_type` | Select | ✓ | Corrective/Emergency/Warranty Repair |
| `priority` | Select | ✓ | Normal/Urgent/Emergency, default Normal |
| `status` | Select | ✓ | 9 states, default Open |
| `open_datetime` | Datetime | — | auto=now() before_insert |
| `assigned_datetime` | Datetime | — | auto khi assign |
| `completion_datetime` | Datetime | — | auto on_submit |
| `sla_target_hours` | Float | — | auto từ get_sla_target() |
| `mttr_hours` | Float | — | auto = `repair_elapsed_hours(doc, completion_datetime)` = `(completion−open) − parts_hold_hours` (clock-stop, **BR-09-10**). Khi `parts_hold_hours==0` ⇒ `(completion−open)/3600` cũ. |
| `sla_breached` | Check | — | auto = `is_sla_breached(repair_elapsed_hours(doc, completion), sla_target)` (boundary `>=`, BR-09-07; **NGUỒN elapsed = clock-stop SoT BR-09-10**); monotonic — completion KHÔNG reset 1→0 |
| `parts_hold_hours` | Float | — | **MỚI (BR-09-10)** default 0; tổng cộng dồn (giờ) mọi khoảng WO nằm Pending Parts. MONOTONIC tăng (INV-CM-HOLD-3). KHÔNG `in_list_view`. read_only. |
| `parts_hold_started` | Datetime | — | **MỚI (BR-09-10)** null khi không hold; STAMP khi VÀO Pending Parts, RESET null khi RA / khi đóng WO lúc đang hold (INV-CM-HOLD-2). non-null ⟺ status==Pending Parts. read_only. |
| `is_repeat_failure` | Check | — | auto before_insert |
| `assigned_to` | Link User | — | KTV thực hiện |
| `diagnosis_notes` | Text | — | — |
| `root_cause_category` | Select | — | 6 options |
| `repair_summary` | Text | (close) | reqd khi Completed |
| `spare_parts_used` | Table | — | child |
| `total_parts_cost` | Currency | — | auto Σ |
| `repair_checklist` | Table | (close) | child; 100% Pass (BR-09-04) |
| `firmware_updated` | Check | — | trigger BR-09-03 |
| `firmware_change_request` | Link FCR | BR-09-03 | reqd khi firmware_updated=1 |
| `dept_head_name` | Data | (close) | reqd khi Completed |
| `cannot_repair_reason` | Text | (cannot) | reqd khi Cannot Repair |

**Permissions:**

| Role | R | W | Create | Submit | Cancel | Delete |
|---|---|---|---|---|---|---|
| Workshop Manager | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| CMMS Admin | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| HTM Technician | ✓ | ✓ (own) | ✗ | ✗ | ✗ | ✗ |
| Kho vật tư | ✓ | ✓ (parts only) | ✗ | ✗ | ✗ | ✗ |
| Trưởng khoa | ✓ | ✓ (dept_head_name) | ✗ | ✗ | ✗ | ✗ |
| PTP Khối 2 | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

**Permission Query (HTM Technician):** `permission.py` → filter `assigned_to = session.user`

### 2.2 Firmware Change Request

- **Naming:** `FCR-.YYYY.-.#####`
- **Submittable:** Yes

| Trường | Type | Required | Notes |
|---|---|---|---|
| `asset` | Link Asset | ✓ | — |
| `repair_wo` | Link Asset Repair | ✓ | — |
| `version_before` | Data | ✓ | — |
| `version_after` | Data | ✓ | — |
| `change_notes` | Text | ✓ | — |
| `status` | Select | ✓ | Draft/Pending Approval/Approved/Applied/Rollback Required/Rolled Back — **state machine `_FCR_VALID_TRANSITIONS`** (§3.1-bis), đổi CHỈ qua endpoint transition |
| `approved_by` | Link User | (Approve) | set bởi `approve_firmware_cr` (read-only qua CRUD) |
| `approved_datetime` / `applied_datetime` | Datetime | — | read-only, set bởi transition (approve/deploy) |
| `rollback_reason` | Text | (Rollback) | reqd khi hoàn tác (`validate()` FCR + guard service) |

> **⚠️ Fieldname thực (grounded `firmware_change_request.json`):** `asset_ref` (KHÔNG `asset`), `asset_repair_wo` (KHÔNG `repair_wo`), `source_reference` (Data). Bảng trên là tên rút gọn tài liệu — dùng fieldname thực khi code. State machine + capability + audit trail: xem **§3.1-bis** + BR-09-18/19/20.

---

## 3. Workflow (State Machine)

State machine enforce **qua controller + API guard** — không dùng Frappe Workflow record (optional cho wave 2).

**States:**

| State | Style | docstatus | allow_edit role |
|---|---|---|---|
| Open | Warning | 0 | Workshop Manager |
| Assigned | Primary | 0 | Workshop Manager |
| Diagnosing | Primary | 0 | KTV HTM |
| Pending Parts | Warning | 0 | KTV / Kho |
| In Repair | Danger | 0 | KTV HTM |
| Pending Inspection | Primary | 0 | KTV HTM |
| Completed | Success | 1 | — (submitted) |
| Cannot Repair | Danger | 0 | Workshop Manager |
| Cancelled | Secondary | 2 | — (cancelled) |

**Key transitions (API-driven):**

| From | To | Trigger | Actor | Validation |
|---|---|---|---|---|
| (insert) | Open | `create_work_order` | Workshop Manager | BR-09-01 (source) + BR-09-05 (no active WO) |
| Open | Assigned | `assign_technician` | Workshop Manager | — |
| Assigned | Diagnosing | `submit_diagnosis` | KTV HTM | — |
| Diagnosing | Pending Parts | `submit_diagnosis(needs_parts=1)` | KTV HTM | **BR-09-10 ENTER hold:** `enter_parts_hold(doc)` → stamp `parts_hold_started = now()` (INV-CM-HOLD-2); ALE `parts_hold_started` |
| Diagnosing | In Repair | `submit_diagnosis(needs_parts=0)` | KTV HTM | — |
| Pending Parts | In Repair | `request_spare_parts` hoặc `start_repair` | KTV HTM / Kho | **BR-09-10 EXIT hold:** `exit_parts_hold(doc, until=now())` → `parts_hold_hours += (now − parts_hold_started)`, reset `parts_hold_started=null` (INV-CM-HOLD-2/3); ALE `parts_hold_resumed` |
| Any active | In Repair | `start_repair` | KTV HTM | allowed from Assigned/Diagnosing/Pending Parts; nếu from Pending Parts → EXIT hold (như trên) |
| In Repair | Pending Inspection | `close_work_order(cannot_repair=0)` | KTV HTM | Điền repair_summary + dept_head_name |
| **Pending Inspection** | **Completed** | **`confirm_inspection`** | **Dept Head / QA Officer** | `CAN_APPROVE_DEP` role; WO submit → `complete_repair()` (chốt hold cuối nếu `parts_hold_started` còn non-null, INV-CM-HOLD-5) |
| Any active | Cannot Repair | `close_work_order(cannot_repair=1)` | KTV / Workshop Manager | cannot_repair_reason required; nếu đang Pending Parts → EXIT hold tới now() TRƯỚC khi đóng (INV-CM-HOLD-5) |

**Controller hooks:**

```python
# assetcore/assetcore/doctype/asset_repair/asset_repair.py
class AssetRepair(Document):
    def before_insert(self):
        from assetcore.services.imm09 import (
            validate_repair_source, validate_asset_not_under_repair, check_repeat_failure,
        )
        validate_repair_source(self)                          # BR-09-01
        validate_asset_not_under_repair(self.asset_ref)       # BR-09-05
        self.is_repeat_failure = check_repeat_failure(self.asset_ref)  # BR-09-06 (returns bool)
        self.open_datetime = now_datetime()                   # audit timestamp

    def on_insert(self):
        from assetcore.services import imm09 as svc
        svc.set_asset_under_repair(self.asset_ref, self.name)  # BR-09-05

    def validate(self):
        from assetcore.services import imm09 as svc
        svc._compute_parts_cost(self)  # total_parts_cost

    def before_submit(self):
        from assetcore.services import imm09 as svc
        svc.validate_spare_parts_stock_entries(self)   # BR-09-02
        svc.validate_firmware_change_request(self)     # BR-09-03
        svc.validate_repair_checklist_complete(self)   # BR-09-04

    def on_submit(self):
        from assetcore.services import imm09 as svc
        svc.complete_repair(self)  # MTTR, sla_breached, asset restore guarded (BR-09-09), ALE
```

### 3.1 Server-driven CTA — `allowed_transitions[]` (SSoT, mirror Incident R3 / PM R21)

`get_work_order` (màn repair-detail mobile/web) emit thêm key `allowed_transitions: list[str]` = **các trạng-thái-kế hợp lệ** từ `status` hiện tại. Client render nút workflow trên màn detail **theo SERVER** — KHÔNG hardcode `status → button` phía client (anti-pattern *dead-gate / RBAC-drift*: khi workflow đổi mà FE quên đồng bộ → nút sai/cụt).

Đây là thành viên **THỨ BA** có `allowed_transitions[]` (sau `IncidentDetail` — imm12.py:778, R3; `PmWorkOrderDetail` — imm08.py:651, R21), đóng **NỬA Repair** của ASYMMETRY R3. (Nửa Calibration — `imm_11_calibration_workflow.json` state-machine riêng — round riêng sau, cùng pattern.)

**SSoT = map tập trung `_REPAIR_VALID_TRANSITIONS` (`services/imm09.py`)**, keyed bằng `RepairStatus.*` constants (KHÔNG literal), codomain GROUNDED **edge-by-edge** `imm_09_repair_workflow.json` (9 state / 15 transition):

```python
_REPAIR_VALID_TRANSITIONS: dict[str, list[str]] = {
    RepairStatus.OPEN:               [RepairStatus.ASSIGNED, RepairStatus.CANCELLED],
    RepairStatus.ASSIGNED:           [RepairStatus.DIAGNOSING, RepairStatus.CANCELLED],
    RepairStatus.DIAGNOSING:         [RepairStatus.IN_REPAIR, RepairStatus.PENDING_PARTS, RepairStatus.CANCELLED],
    RepairStatus.PENDING_PARTS:      [RepairStatus.IN_REPAIR, RepairStatus.CANCELLED],
    RepairStatus.IN_REPAIR:          [RepairStatus.PENDING_INSPECTION, RepairStatus.CANNOT_REPAIR, RepairStatus.CANCELLED],
    RepairStatus.PENDING_INSPECTION: [RepairStatus.COMPLETED, RepairStatus.IN_REPAIR, RepairStatus.CANCELLED],
    RepairStatus.COMPLETED:          [],   # terminal (doc_status=1)
    RepairStatus.CANNOT_REPAIR:      [],   # terminal (doc_status=1)
    RepairStatus.CANCELLED:          [],   # terminal
}
```

Emit (mirror imm12.py:778 / imm08.py:651) — **0 đổi signature handler** `getRepairWorkOrder` (vẫn `handle(svc.get_work_order, name)`); field mới chảy qua envelope tự động:

```python
# services/imm09.py::get_work_order — ngay trước `return data`
data["allowed_transitions"] = _REPAIR_VALID_TRANSITIONS.get(doc.status, [])
```

**Boundaries (Always / Never):**

| | |
|---|---|
| **Always** | Keyed bằng `RepairStatus.*` constants. Codomain == `imm_09_repair_workflow.json` edge-by-edge (guard SSoT-divergence). Terminal `Completed`/`Cannot Repair`/`Cancelled` → `[]`. Emit qua `_REPAIR_VALID_TRANSITIONS.get(doc.status, [])` (default `[]` an toàn cho status lạ). |
| **Never** | KHÔNG literal status trong map. KHÔNG enum-bound cứng ở schema YAML (né drift). KHÔNG đưa `allowed_transitions` vào `required`. KHÔNG để FE hardcode `status → button` (server-drive). KHÔNG đổi signature handler / không gọi workflow-engine để derive (map thuần). |

**ADR-IMM09-CTA — server-driven `allowed_transitions[]` cho repair-detail**

- **Context:** màn repair-detail cần biết nút workflow nào được phép từ `status` hiện tại. Nếu FE tự suy (`status → button`) thì mỗi lần workflow đổi phải sửa 2 nơi (BE + FE) → drift, nút cụt/sai, lỗi RBAC dead-gate. Incident (R3) và PM (R21) đã giải bằng map server-driven; Repair còn thiếu ⇒ ASYMMETRY.
- **Decision:** thêm map tập trung `_REPAIR_VALID_TRANSITIONS` (SSoT, grounded workflow JSON edge-by-edge), emit `allowed_transitions[]` trong `get_work_order`. Schema YAML khai `array<string>` **KHÔNG enum-bound** + **NOT-required** (mirror IncidentDetail/PmWorkOrderDetail), `additionalProperties:true` giữ nguyên.
- **Consequences:** FE render CTA hoàn toàn theo server (1 nguồn sự thật); thêm/bớt transition chỉ sửa workflow JSON + map (guard test bắt drift ngay). Field optional → client cũ bỏ qua an toàn (backward-compatible). Không enum-bound ⇒ thêm state mới không phá contract.
- **Alternatives (rejected):** (a) FE hardcode `status→button` — drift 2 nơi, dead-gate; (b) schema enum-bound `items.enum=[...9 state]` — drift mỗi lần đổi workflow, phá codegen; (c) derive qua Frappe workflow-engine runtime — nặng + phụ thuộc Workflow record (IMM-09 không dùng Workflow record, enforce qua controller/guard).

### 3.1-bis Firmware Change Request — state machine SERVER-controlled (`_FCR_VALID_TRANSITIONS`) (Vòng 10, BR-09-18/19/20)

**Thành viên THỨ HAI của IMM-09 có `allowed_transitions[]`** (sau `_REPAIR_VALID_TRANSITIONS`) — nhưng cho **DocType `Firmware Change Request`** (KHÔNG phải Asset Repair). FCR **không có Frappe Workflow JSON** → `status` field là SSoT state machine, enforce hoàn toàn qua service guard (ADR-IMM09-FCR-01).

**Enum constants + map (`services/imm09.py` — mirror `RepairStatus`/`_REPAIR_VALID_TRANSITIONS`):**

```python
class FirmwareStatus:
    DRAFT             = "Draft"
    PENDING_APPROVAL  = "Pending Approval"
    APPROVED          = "Approved"
    APPLIED           = "Applied"
    ROLLBACK_REQUIRED = "Rollback Required"   # RESERVED (2-phase tương lai) — không trong map
    ROLLED_BACK       = "Rolled Back"

# SoT — codomain ⊆ FirmwareStatus (keyed bằng constants, KHÔNG literal). Guard test
# chốt codomain ⊆ enum status của DocType (chống typo/drift).
_FCR_VALID_TRANSITIONS: dict[str, list[str]] = {
    FirmwareStatus.DRAFT:            [FirmwareStatus.PENDING_APPROVAL],
    FirmwareStatus.PENDING_APPROVAL: [FirmwareStatus.APPROVED],
    FirmwareStatus.APPROVED:         [FirmwareStatus.APPLIED],
    FirmwareStatus.APPLIED:          [FirmwareStatus.ROLLED_BACK],
    FirmwareStatus.ROLLED_BACK:      [],
}

# Cạnh yêu cầu quyền phê duyệt (đối xứng: duyệt + hoàn tác = quyết định manager)
_FCR_APPROVAL_EDGES = {FirmwareStatus.APPROVED, FirmwareStatus.ROLLED_BACK}
```

**Capability-per-edge (gate CAPABILITY, KHÔNG role-name):**

| Cạnh | Endpoint | Capability | Side-effect | Lifecycle Event |
|---|---|---|---|---|
| `Draft → Pending Approval` | `submit_firmware_cr` | `repair.write` | — | — |
| `Pending Approval → Approved` | `approve_firmware_cr` | **`firmware.approve`** | set `approved_by=session.user`, `approved_datetime=now()` | `firmware_cr_approved` |
| `Approved → Applied` | `deploy_firmware_cr` | `repair.write` | set `applied_datetime=now()` | `firmware_deployed` |
| `Applied → Rolled Back` | `rollback_firmware_cr(reason)` | **`firmware.approve`** | reqd `rollback_reason` (throw VN nếu rỗng) | `firmware_rolled_back` |

**Capability mới — `rbac.py` CAPABILITY_MAP.update():**

```python
# Vòng 10: Duyệt/Hoàn tác FCR gate theo DocPerm submit của CHÍNH Firmware Change
# Request → Repair Manager + AssetCore Super Admin (submit=1) TRUE, Repair User
# (submit=0) FALSE. Capability-based (chống RBAC dead-gate) — đổi quyền = sửa
# DocPerm ở /app, KHÔNG deploy. Thêm cap → CAP_SET_VERSION đổi → FE auto-invalidate
# persisted-caps stale + after_migrate invalidate_capabilities().
"firmware.approve": ("Firmware Change Request", "submit"),
```

**Guard helper (service):**

```python
def _assert_valid_fcr_transition(current: str, target: str) -> None:
    if target not in _FCR_VALID_TRANSITIONS.get(current, []):
        raise ServiceError(ErrorCode.BAD_STATE,
            _("Không thể chuyển yêu cầu đổi firmware từ '{0}' sang '{1}'").format(current, target))

def _assert_can_approve_fcr() -> None:
    # In-handler cap-check → ServiceError(FORBIDDEN) → HTTP-200 Error envelope (KHÔNG
    # rbac.require → PermissionError/4xx). FE render inline VN, không re-auth redirect.
    if not rbac.can("firmware.approve"):
        raise ServiceError(ErrorCode.FORBIDDEN,
            _("Bạn không có quyền phê duyệt yêu cầu đổi firmware"), http_status=403)

def firmware_allowed_transitions(status: str) -> tuple[list[str], bool]:
    """Server-derive cho get_firmware_cr: raw list LỌC theo capability caller + can_approve."""
    raw = _FCR_VALID_TRANSITIONS.get(status, [])
    can_approve = rbac.can("firmware.approve")
    can_write   = rbac.can("repair.write")
    allowed = [t for t in raw
               if (t in _FCR_APPROVAL_EDGES and can_approve)
               or (t not in _FCR_APPROVAL_EDGES and can_write)]
    return allowed, can_approve
```

**Transition body (chung — `firmware_transition`), CANONICAL lifecycle event (fail-loud):**

```python
def firmware_transition(name, target, *, event_type, extra_fields=None, notes=""):
    doc = frappe.get_doc(_DT_FIRMWARE_CR, name)   # NOT_FOUND nếu thiếu (guard trước)
    if target in _FCR_APPROVAL_EDGES:
        _assert_can_approve_fcr()
    else:
        _assert_can_write_fcr()                    # repair.write
    _assert_valid_fcr_transition(doc.status, target)
    from_status = doc.status
    for k, v in (extra_fields or {}).items():
        doc.set(k, v)
    frappe.db.savepoint("fcr_transition")          # SCOPED rollback (robust job/test)
    doc.db_set(updates)                            # mutate FIELD status + extra_fields
    # HARD-REQ audit NĐ98 — canonical create_lifecycle_event TRỰC TIẾP (KHÔNG wrapper
    # _log_lifecycle_event vì nó try/except-swallow). Event throw → rollback TỚI
    # savepoint (undo db_set) + re-raise ⇒ status KHÔNG đổi câm (KHÔNG full-rollback,
    # né phá savepoint-isolation test / cuốn write khác trong request).
    try:
        _create_lifecycle_event(
            asset=doc.asset_ref, event_type=event_type, actor=frappe.session.user,
            from_status=from_status, to_status=target,
            root_doctype=_DT_FIRMWARE_CR, root_record=name, notes=notes)
    except Exception:
        frappe.db.rollback(save_point="fcr_transition")
        raise
    frappe.db.commit()
    return {"name": name, "status": target}
```

**`update_firmware_cr` (generic) — STRIP controlled fields (`api/imm00.py`):**

```python
_FCR_CONTROLLED_FIELDS = {"status", "approved_by", "approved_datetime",
                          "applied_datetime", "rollback_reason"}

@frappe.whitelist(methods=["POST"])
def update_firmware_cr(name: str):
    data = frappe.local.form_dict
    for f in _FCR_CONTROLLED_FIELDS:              # status KHÔNG đổi qua CRUD chung
        data.pop(f, None)
    return _generic_update(_DT_FIRMWARE_CR, name)  # _generic_update đã bỏ cmd/name/doctype
```

**`get_firmware_cr` — enrich `allowed_transitions` + `can_approve` (`api/imm00.py`, lazy-import):**

```python
from assetcore.services import imm09 as _svc09     # lazy trong hàm (né circular)
allowed, can_approve = _svc09.firmware_allowed_transitions(doc["status"])
doc["allowed_transitions"] = allowed
doc["can_approve"] = bool(can_approve)   # BOOLEAN (FE web so === true), KHÔNG int 1/0
```

> **Endpoint thực (BUILT — khớp FE `imm00.ts::transitionFirmwareCr`):** 1 dispatcher
> `transition_firmware_cr(name, action, reason)` ở `api/imm00.py` (action ∈
> {submit, approve, deploy, rollback}), delegate `services/imm09.py::transition_firmware_cr`
> → map action→target→`firmware_transition`. Gộp 1 endpoint action-based thay vì 4
> endpoint riêng (One-Version + khớp FE đã build). Xem §05 §3.15.

**Boundaries (Always / Never):**

| | |
|---|---|
| **Always** | `status` field = SSoT workflow (mutate qua `db_set`/`set_value`). Keyed bằng `FirmwareStatus.*`. Gate `firmware.approve` bằng CAPABILITY. 1 ALE canonical/transition trong CÙNG transaction (fail-loud). `allowed_transitions` LỌC theo cap + `can_approve`. `update_firmware_cr` STRIP `_FCR_CONTROLLED_FIELDS`. |
| **Never** | KHÔNG hardcode role-name (`role=='Repair Manager'`). KHÔNG dùng wrapper swallow `_log_lifecycle_event` cho audit firmware. KHÔNG `raise → HTTP-4xx` cho lỗi transition (dùng in-handler HTTP-200 Error envelope; dispatcher-403 chỉ guest). KHÔNG couple transition với `docstatus`/`doc.submit()` (dùng field `status`). KHÔNG đổi status FCR qua `update_firmware_cr`/`_generic_update`. KHÔNG thêm enum `event_type`/`status` mà quên `reload-doctype`. |

**ADR-IMM09-FCR-01 — FCR `status` field = SSoT state machine (KHÔNG Frappe Workflow, KHÔNG generic CRUD)**

- **Status:** Accepted · **Date:** 2026-07-10
- **Context:** FCR (`is_submittable=1`) trước đây đổi status bằng `update_firmware_cr` (generic `_generic_update`, `ignore_permissions=True`) + FE hardcode `fcr.status==='X'` gate nút ⇒ Repair User tự Approve, nhảy-cóc, KHÔNG audit (vi phạm CLAUDE.md §5/§10, NĐ98 change-control). Không có `_FCR_VALID_TRANSITIONS` (Repair đã có `_REPAIR_VALID_TRANSITIONS` — ASYMMETRY).
- **Decision:** thêm map SSoT `_FCR_VALID_TRANSITIONS` + endpoint transition riêng mỗi cạnh (submit/approve/deploy/rollback). `status` field là SSoT workflow (mutate `db_set`), KHÔNG dùng Frappe Workflow record (FCR chưa có workflow JSON), KHÔNG couple với `docstatus` submit. `on_submit` gate (status==Approved) giữ nguyên như hàng rào phụ.
- **Alternatives (rejected):** (a) tạo Frappe Workflow JSON `imm_09_firmware_workflow.json` — nặng, thêm 1 state-machine engine cho 5 state đơn giản, lệch pattern Repair (cũng field-based); (b) couple transition với `docstatus` (approve = submit) — `on_submit` chỉ 1 transition, không phủ Deploy/Rollback trên doc đã submit (field submitted immutable trừ `db_set`); (c) giữ generic CRUD + chỉ thêm permission check — vẫn cho nhảy-cóc, không audit.
- **Consequences:** contract nhất quán với Repair; thêm cạnh chỉ sửa map + 1 endpoint. Cần `reload-doctype` khi thêm event enum. `db_set` bỏ qua `validate()` FCR ⇒ side-effect (`rollback_reason` reqd) tự-enforce trong service TRƯỚC `db_set`.

**ADR-IMM09-FCR-02 — capability `firmware.approve` = (`Firmware Change Request`, `submit`), KHÔNG role-name**

- **Status:** Accepted · **Date:** 2026-07-10
- **Context:** "Duyệt FCR = Repair Manager HOẶC Super Admin". Nếu gate bằng `if 'Repair Manager' in roles` → RBAC dead-gate (đổi role/thêm role duyệt phải sửa code; đối xứng root-cause workflow-admin-override "đủ quyền vẫn không duyệt được").
- **Decision:** bind capability `firmware.approve → ("Firmware Change Request", "submit")`. DocPerm FCR đã có submit=1 cho Repair Manager + AssetCore Super Admin, submit=0 cho Repair User ⇒ `rbac.can("firmware.approve")` resolve ĐÚNG requirement mà KHÔNG hardcode role. Đổi ai được duyệt = sửa DocPerm ở /app.
- **Alternatives (rejected):** (a) hardcode role-name — dead-gate; (b) reuse `repair.submit` (= Asset Repair submit) — sai đối tượng quyền (submit Asset Repair ≠ submit FCR, DocPerm khác nhau); (c) tạo domain `Firmware` riêng — thừa (FCR đã thuộc domain Repair, chỉ cần 1 cap đặc thù submit).
- **Consequences:** thêm 1 cap → CAP_SET_VERSION đổi → FE auto-invalidate persisted-caps + `after_migrate invalidate_capabilities()`. Symmetry 401/403 mobile tự cân nếu surface (path vào business-paths).

**ADR-IMM09-FCR-03 — lỗi transition (cap/invalid-edge/reason) = in-handler HTTP-200 Error envelope; dispatcher-403 chỉ guest**

- **Status:** Accepted · **Date:** 2026-07-10
- **Context:** DONE-gate spec-contract (LL-BE-42..49): lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope (KHÔNG raise→4xx). Repair User bấm Duyệt cần thấy thông điệp VN inline (KHÔNG 403-redirect/re-auth, KHÔNG 500).
- **Decision:** cap-check + valid-transition + reason-check nằm TRONG service, raise `ServiceError(FORBIDDEN/BAD_STATE/VALIDATION)` → `handle()` chuyển thành HTTP-200 Error envelope (route-by-VALUE `body.success=false`). KHÔNG dùng `rbac.require` (raise PermissionError→4xx) cho các action này. **2 loại 403 phân biệt:** dispatcher-403 = guest/no-token gõ POST @whitelist (trước handler, re-auth); "thiếu quyền" của user đã đăng nhập = business error → HTTP-200 Error envelope (show-msg), KHÔNG 403-line.
- **Alternatives (rejected):** (a) `rbac.require` before `handle` → HTTP-403 — FE khó phân biệt với dispatcher-403 guest, dễ trigger re-auth flow sai; (b) trả 500 khi thiếu quyền — leak/UX tệ; (c) silent no-op — vi phạm "KHÔNG silent".
- **Consequences:** test assert `body.success==False` + message VN (KHÔNG expect exception/4xx). Consumer web+mobile cùng route-by-value. Mirror pattern attach_*_photo (imm08/09/12) in-handler cap-403.

### 3.2 Mobile-BE contract — `assignTechnician` (DISPATCH: Open → Assigned)

Endpoint `assign_technician` đã có sẵn ở BE (`api/imm09.py:58`, whitelisted POST) và web SPA (§3.4 file 05). Round này bồi **path tương ứng vào contract mobile** `docs/mobile/openapi/assetcore-mobile.openapi.yaml` để app field-tech lấp **HỐ create→start**: chuỗi `createRepairWorkOrder → [THIẾU giao việc] → startRepair` chưa có endpoint giao WO cho KTV hiện trường. `assignTechnician` là **action lifecycle DISPATCH** đầu chuỗi vận hành repair (`Open → Assigned`).

**Grounding @source (verify-before-claim):**

| Mục | Giá trị | Evidence |
|---|---|---|
| Handler | `assign_technician(name, technician, priority="")` | `api/imm09.py:58` |
| Cap-gate | `rbac.require("repair.write")` | `api/imm09.py:59` |
| Service return | `{name, status=RepairStatus.ASSIGNED, assigned_to=technician}` (3-key) | `services/imm09.py:848` |
| Status gate | chỉ khi `status == "Open"` → nếu khác raise `IMM09_BAD_STATE` | `services/imm09.py:842` |

**Khác mọi C8-ACTION đã làm — đây là điểm thiết kế cần ADR:**

- **Response 3-key** `{name, status, assigned_to}` ⇒ **KHÔNG reuse** `RepairActionEnvelope`/`RepairActionResponse` (2-key `{name,status}` của `start_repair`). Service trả thêm `assigned_to` (echo technician đã gán) ⇒ schema RIÊNG (precedent: `CloseWorkOrderEnvelope` 4-key, `ResolveIncidentEnvelope` 3-key — C3-split field-disjoint).
- **requestBody 2-required** `[name, technician]` + 1 optional `priority` ⇒ KHÁC mọi C8-ACTION đơn-`{name}` trước đó (startRepair/acknowledgeIncident). `technician` (positional `api/imm09.py:58`) chính là **đích tiêu thụ của `listUsers`** (R23 picker KTV).

**Boundaries (Always / Never):**

| | |
|---|---|
| **Always** | `AssignTechnicianResponse` props EXACT `{name,status,assigned_to}` (grounded `services/imm09.py:848`), `additionalProperties:false`, `required=[name,status,assigned_to]`. `status` enum = RepairStatus-canonical 9-state (mô tả literal `Assigned`). requestBody `required=[name,technician]` (cả 2 positional no-default), `priority` optional `default ''`. 200 = `oneOf [AssignTechnicianEnvelope, Error]` route-by-VALUE `body.success` (closed-schema, 0 discriminator). Path vào `_MVP_BUSINESS_PATHS` ⇒ 401/403 symmetry tự cân (test so SET). |
| **Never** | KHÔNG reuse `RepairActionEnvelope` (2-key ≠ 3-key). KHÔNG đưa `priority` vào `required`. KHÔNG thêm `name` vào body-exclude (name **BẮT BUỘC** — positional thứ nhất). KHÔNG dùng discriminator (`success` boolean illegal §5c). KHÔNG status-line key 404/409/422 (lỗi nghiệp vụ in-handler arrive HTTP-200 + Error body). KHÔNG sửa `api/imm09.py`/`services/imm09.py` (PURE-YAML round). |

**ADR-IMM09-ASSIGN — mobile contract `assignTechnician` (response RIÊNG 3-key, KHÔNG reuse 2-key envelope)**

- **Status:** Accepted · **Date:** 2026-06-16
- **Context:** chuỗi vận hành repair trên mobile field-tech có HỐ `create → [?] → start`: thiếu endpoint giao WO cho KTV. BE `assign_technician` đã sẵn (whitelisted POST `api/imm09.py:58`) nhưng chưa có path mobile-contract. Service trả 3-key (thêm `assigned_to` so với `start_repair` 2-key) ⇒ không thể tái dùng `RepairActionEnvelope`. requestBody cũng khác mọi action đơn-`{name}` (cần `technician` positional + `priority` optional).
- **Decision:** thêm ĐÚNG 1 path `POST /api/method/assetcore.api.imm09.assign_technician` opId `assignTechnician`; schema RIÊNG `AssignTechnicianRequest` (required `[name,technician]` + optional `priority`, `additionalProperties:false`) + `AssignTechnicianEnvelope`(`success:true`, `data=AssignTechnicianResponse {name,status,assigned_to}`); 200 = `oneOf [AssignTechnicianEnvelope, Error]` route-by-VALUE `body.success` (closed-schema, 0 discriminator — pattern C8-ACTION). 403 SINGLE-SHAPE dispatcher-403 (in-handler cap-403 `repair.write` đã phủ bởi nhánh Error 200-oneOf — mirror startRepair/acknowledgeIncident). PURE-YAML + guard test, KHÔNG đụng `.py`.
- **Consequences:** mobile lấp được hố create→start; `listUsers` (R23) có đích tiêu thụ rõ (`technician` field). Path/opId 33→34. Codegen sinh client `assignTechnician(name,technician,priority?)` typed. `assigned_to` echo cho client cập nhật UI ngay không cần re-fetch.
- **Alternatives (rejected):** (a) reuse `RepairActionEnvelope` 2-key — DROP `assigned_to`, client phải re-fetch để biết ai được gán → thừa round-trip + lệch source; (b) đưa `priority` vào required — chặn client không muốn override priority (signature có default `''`); (c) gộp `assignTechnician` vào `startRepair` — sai lifecycle (DISPATCH ≠ START, 2 transition khác nhau `Open→Assigned` vs `Assigned/...→In Repair`).

### 3.3 Dispatch-validation gate — `assign_technician` (R25: chặn mis-dispatch / dữ liệu rác)

**Vấn đề gốc (R24 USER-eval CRITICAL):** `services/imm09.py:840` set `doc.assigned_to = technician` rồi `doc.flags.ignore_links = True` (`:846`) → bỏ qua referential-integrity của Frappe (Link field `assigned_to` → DocType `User`). Hệ quả: email bịa `khong-ton-tai@nope.invalid` vẫn POST 200 `success:true status=Assigned` — WO bị giao vào **hư vô**, KTV không bao giờ nhận việc, SLA chạy oan, audit-trail sai. `listUsers` picker (R23) ở FE lane là *tiện ích* (UX), KHÔNG phải **validation-boundary** — client tự gõ / app khác / replay request đều bypass được. Boundary đúng = **server-side gate** trước khi save.

**Hậu quả nếu data sai (5-câu-hỏi domain):** mis-dispatch là lỗi vận hành nghiêm trọng — thiết bị y tế hỏng không được sửa đúng người, vi phạm traceability (CLAUDE.md §5 "mọi nghiệp vụ phải có record" + audit-trail đúng actor). Lifecycle event `repair_assigned` ghi `assigned_to` rác → toàn chuỗi downstream (diagnosis/start/complete) treo.

**Grounding @source (verify-before-claim):**

| Mục | Giá trị | Evidence |
|---|---|---|
| Set không kiểm | `doc.assigned_to = technician` (0 validation) | `services/imm09.py:840` |
| Bypass FK | `doc.flags.ignore_links = True` | `services/imm09.py:846` |
| Cap-gate (đã có) | `rbac.require("repair.write")` (dispatcher quyền **người gọi**, KHÔNG validate **người được gán**) | `api/imm09.py:59` |
| Repair-capability binding | `repair.*` → DocPerm trên DocType `Asset Repair` (KHÔNG hardcode role-name) | `services/shared/rbac.py:37,71,91` |
| Repair domain roles (SSoT catalog) | `Repair Manager` / `Repair User` (Domain), + Super Admin bao trùm | `services/shared/constants.py:25-35` |

**Định nghĩa "technician hợp lệ" (3 điều kiện AND — gate TRƯỚC khi save):**

1. **Tồn tại:** `frappe.db.exists("User", technician)` truthy. (User là DocType; `technician` = `User.name` = email.)
2. **Enabled:** `User.enabled == 1`. (User bị khoá KHÔNG được giao việc.)
3. **Repair-capable:** user có quyền ghi trên DocType `Asset Repair` — kiểm bằng **capability**, KHÔNG so tên role (chống anti-pattern *RBAC dead-gate*, memory `factory_rounds_1_25`). Implement: `rbac.can("repair.write", user=technician)` hoặc tương đương `frappe.has_permission("Asset Repair", "write", user=technician)`. Cap `repair.write` đã bind `(Asset Repair, "write")` ở `rbac.py:91` ⇒ bất kỳ user có DocPerm write trên Asset Repair (Repair Manager/User + Super Admin) đều pass; user chỉ có vai khác (vd Auditor) → fail. **Boundary so khớp:** capability dùng để gate = đúng cap mà **người được gán** sẽ cần để thao tác (diagnose/start/complete repair) → đảm bảo người nhận việc thực sự thao tác được.

> **⚠️ Implementation note (BE):**
> - `rbac.can(cap)` mặc định resolve theo `frappe.session.user`. Để kiểm **target user**, BE phải gọi `frappe.has_permission("Asset Repair", "write", user=technician)` (truyền `user=`), KHÔNG dùng `rbac.can` (không nhận `user=`). Đặt helper `_is_repair_capable(technician)` trong `services/imm09.py` để giữ 1 SoT. KHÔNG bỏ cache-by-session làm sai kết quả.
> - `error_code=ErrorCode.VALIDATION_ERROR` cần import: `services/imm09.py` HIỆN CHƯA import `ErrorCode` → BE thêm `from assetcore.utils.response import ErrorCode` (đầu file, cạnh import `nthrow`). `MSG.IMM09_INVALID_TECHNICIAN` đã có constant + registry entry (`utils/messages.py`, http_status=422) — KHÔNG cần thêm.
> - Sau khi thêm MSG mới, chạy `python scripts/gen_fe_messages.py` để regen `frontend/src/i18n/messages.ts` (quy trình `utils/messages.py` docstring §"Quy trình thêm mã mới"). Đây là FE-message generator, KHÔNG đụng mobile contract.

**Vị trí gate trong `assign_technician` (services/imm09.py:833-848):** chèn SAU `RBAC.require` + status-gate (`status == OPEN`), TRƯỚC `doc.assigned_to = technician`. Thứ tự: not-found WO (`IMM09_NOT_FOUND`) → bad-state (`IMM09_BAD_STATE`) → **invalid-technician (`IMM09_INVALID_TECHNICIAN`)** → set + save. Khi gate fail: `nthrow(...)` raise TRƯỚC mọi mutation ⇒ `doc` KHÔNG save, `assigned_to` KHÔNG đổi, `status` GIỮ `Open` (invariant: fail-fast, no partial write).

**Error contract (DONE-gate spec-contract — Error-on-HTTP-200, KHÔNG raise→4xx):**

```text
nthrow(MSG.IMM09_INVALID_TECHNICIAN,
       error_code=ErrorCode.VALIDATION_ERROR,   # override bucket
       technician=technician)
```

→ envelope (in-handler, qua `handle()`, HTTP-200 status-line): `{success:false, error:<render template>, code:'VALIDATION_ERROR', http_status:422}`.

- `http_status:422` ← registry entry `MSG.IMM09_INVALID_TECHNICIAN["http_status"]=422` (`nthrow` lấy `entry["http_status"]` trực tiếp, `utils/notify.py:84`).
- `code:'VALIDATION_ERROR'` ← **override bắt buộc** `error_code=ErrorCode.VALIDATION_ERROR` (`utils/notify.py:80,82`). KHÔNG override → `_bucket_for` default map `422 → BUSINESS_RULE` (`utils/notify.py:24,53`) ⇒ sẽ ra `code='BUSINESS_RULE'` (SAI acceptance). Xem ADR-IMM09-VALIDATE-TECH lý do chọn cặp `VALIDATION_ERROR×422`.
- Cả `code='VALIDATION_ERROR'` (yaml `Error.code` enum line 565) và `http_status=422` (yaml `Error.http_status` enum line 597) ĐỀU ∈ bounded-enum đã chốt (R11) ⇒ valid against `#/components/schemas/Error`, **KHÔNG schema mới**. Nhánh Error này đã được phủ bởi `200 = oneOf [AssignTechnicianEnvelope, Error]` (§3.2, yaml line 5347-5349) — đây là **lý do KHÔNG đụng contract path/schema** round này (chỉ bồi mô tả Error-case prose).

**Boundaries (Always / Never):**

| | |
|---|---|
| **Always** | Gate 3-điều-kiện AND chạy SERVER-SIDE trước mọi mutation. Kiểm repair-capability bằng `frappe.has_permission("Asset Repair","write",user=technician)` (capability, KHÔNG so tên role). Fail → `nthrow(MSG.IMM09_INVALID_TECHNICIAN, error_code=ErrorCode.VALIDATION_ERROR, technician=...)` ⇒ `code='VALIDATION_ERROR'` + `http_status=422`, `assigned_to` GIỮ nguyên, `status` GIỮ `Open`. Happy-path (technician hợp lệ) KHÔNG đổi hành vi R24 (regression-safe). |
| **Never** | KHÔNG hardcode list role-name `["Repair Manager","Repair User",...]` để check (RBAC dead-gate — role đổi tên/thêm vai → gate fail âm thầm). KHÔNG raise→HTTP-4xx (lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope). KHÔNG dùng `code='VALIDATION'` (422 nhưng acceptance chốt `VALIDATION_ERROR`) hay `code='BUSINESS_RULE'` (default 422 nếu quên override). KHÔNG thêm schema mới vào yaml (nhánh Error đã có). KHÔNG bỏ `error_code` override (ra BUSINESS_RULE sai). KHÔNG validate ở FE-only (picker R23 ≠ boundary). KHÔNG xoá `ignore_links=True` (giữ — nhiều Link khác trong doc; gate phủ đúng `assigned_to`). |

**ADR-IMM09-VALIDATE-TECH — server-side technician-validation gate (capability-based, Error code `VALIDATION_ERROR`×422)**

- **Status:** Accepted · **Date:** 2026-06-16
- **Context:** `assign_technician` set `assigned_to` + `ignore_links=True` không kiểm input ⇒ email bịa POST 200 success, mis-dispatch vào hư vô (R24 USER-eval CRITICAL). 24 vòng mobile-BE trước CHỈ shape contract/read-path/action-passthrough — chưa vòng nào thêm **server-side input-validation gate** chống ghi dữ liệu rác. `ignore_links=True` cố ý bypass FK Frappe (perf + nhiều Link), KHÔNG thể chỉ tháo cờ. Acceptance chốt envelope `code:'VALIDATION_ERROR' + http_status:422` — nhưng SSoT `response.py:_HTTP_FOR_CODE[VALIDATION_ERROR]=400` và `notify.py:_HTTP_TO_BUCKET[422]=BUSINESS_RULE` ⇒ cặp `VALIDATION_ERROR×422` KHÔNG phải default-pairing của 1 trong 2 map.
- **Decision:** (1) Thêm gate 3-điều-kiện AND (tồn-tại + enabled + repair-capable) trong `services/imm09.py:assign_technician`, TRƯỚC set/save, raise `nthrow(MSG.IMM09_INVALID_TECHNICIAN, error_code=ErrorCode.VALIDATION_ERROR, technician=...)`. (2) Kiểm repair-capability bằng **capability/DocPerm** (`has_permission("Asset Repair","write",user=technician)`), KHÔNG so tên role. (3) Envelope dùng registry `http_status=422` (input không hợp lệ — field-level, NĐ98/audit: "đúng người mới thao tác") + **override** `error_code=VALIDATION_ERROR` (acceptance + UX: FE route nhánh validation, không phải nhánh business-rule/state). Cả 2 ∈ bounded-enum R11 ⇒ valid `Error` schema, KHÔNG schema mới.
- **Alternatives (rejected):** (a) **tháo `ignore_links=True`** để Frappe tự validate FK — vỡ các Link khác trong doc (asset_ref, incident_report...) + raise `LinkValidationError`→HTTP-417/500 (KHÔNG Error-on-200), lệch contract; (b) **hardcode role-name list** kiểm `technician` có role ∈ {"Repair Manager","Repair User"} — anti-pattern RBAC dead-gate (đổi tên role/thêm vai → gate fail âm thầm, memory `factory_rounds_1_25` P1); (c) **`code='BUSINESS_RULE'`** (default khi quên override, http 422) — đúng http nhưng FE phân nhánh UX sai (đây là input-validation, không phải vi phạm workflow-state); (d) **`code='VALIDATION'`** (422 "tự nhiên" theo `_HTTP_FOR_CODE`) — đúng http + đúng họ nhưng acceptance chốt `VALIDATION_ERROR`; (e) **validate FE-only qua `listUsers` picker** (R23) — picker là UX tiện, client tự gõ / app khác / replay bypass → KHÔNG phải boundary.
- **Consequences:** mis-dispatch bị chặn tại boundary đúng (server). `listUsers` picker (R23) trở thành *first-line UX* khớp gate (cùng tập user enabled + repair-capable) — FE lane sẽ filter `role`/`is_active` để picker chỉ hiện user pass gate ⇒ user hợp lệ không bao giờ chạm Error. Thêm 1 MSG (`IMM09_INVALID_TECHNICIAN`) + 1 helper `_is_repair_capable`. KHÔNG đổi contract yaml schema/path (nhánh Error đã có). Cặp `VALIDATION_ERROR×422` là **ngoại lệ có chủ đích** so default-map → ghi rõ ADR để 6 tháng sau không "sửa cho khớp _HTTP_FOR_CODE". Regression-safe: happy-path R24 (technician hợp lệ) KHÔNG đổi.

---

### 3.4 Referential-integrity gate — `create_work_order` 2 optional Link FK (R26: chặn ghi FK rác)

**Vấn đề gốc (R26):** `services/imm09.py:805-822` build `frappe.get_doc({...})` với `incident_report` + `source_pm_wo` lấy nguyên giá trị caller truyền, rồi `doc.flags.ignore_links = True` (`:821`) → `doc.insert(ignore_permissions=True)` (`:822`). `ignore_links=True` bỏ qua referential-integrity của Frappe cho MỌI Link field trong doc — gồm 2 optional Link `incident_report` (→ DocType `Incident Report`) và `source_pm_wo` (→ DocType `PM Work Order`). Hệ quả: caller truyền non-empty bịa (`incident_report='INC-khong-ton-tai'`) vẫn POST 200 `success:true status=Open` — WO được tạo với FK trỏ vào **record không tồn tại**, phá traceability nguồn-gốc (WO không truy được về Incident/PM thực). Đối xứng hệt R25 `assign_technician`/`assigned_to`: cùng cờ `ignore_links=True`, cùng họ "Link rác qua bypass FK".

**Phân biệt với R25 (boundary scope):** R25 phủ `assigned_to` (User-FK). R26 phủ 2 FK nguồn-gốc `incident_report` + `source_pm_wo`. `asset_ref` (Link → Asset) ĐÃ được validate sẵn `services/imm09.py:790-791` (`IMM09_ASSET_NOT_FOUND`, http 404) — **NGOÀI scope R26, KHÔNG đụng**. R26 chỉ thêm gate cho 2 FK optional CHƯA validate.

**Hậu quả nếu data sai (5-câu-hỏi domain):** WO sửa chữa (CM) ở stage *Maintenance* (WHO HTM) phải truy được về sự kiện kích hoạt — Incident Report (lỗi vận hành) hoặc PM Work Order (phát hiện khi bảo trì định kỳ). FK rác phá audit-trail nguồn (CLAUDE.md §5 "mọi nghiệp vụ phải có record" + §10 lifecycle event `root_record`). Báo cáo CAPA/RCA (IMM-12) downstream truy ngược `incident_report` rác → treo. NĐ98/audit: chuỗi nguyên-nhân→hành-động phải nối được record thật.

**Grounding @source (verify-before-claim):**

| Mục | Giá trị | Evidence |
|---|---|---|
| Set FK không kiểm | `"incident_report": incident_report, "source_pm_wo": source_pm_wo` (0 validation) | `services/imm09.py:814-815` |
| Bypass FK | `doc.flags.ignore_links = True` | `services/imm09.py:821` |
| Insert | `doc.insert(ignore_permissions=True)` | `services/imm09.py:822` |
| `asset_ref` đã validate (ngoài scope) | `if not asset_data: nthrow(MSG.IMM09_ASSET_NOT_FOUND, ...)` | `services/imm09.py:790-791` |
| Open-WO guard (đứng trước gate mới) | `if open_wo: nthrow(MSG.IMM09_ASSET_HAS_OPEN_WO, ...)` | `services/imm09.py:797-798` |
| FK target DocType | `incident_report` → `Incident Report`; `source_pm_wo` → `PM Work Order` | `asset_repair.json:104-115` (Link, reqd=None) |
| Standalone hợp lệ (slide 24b) | cả 2 FK rỗng `""` → tạo WO standalone, KHÔNG validate | doc §I.5 / `services/imm09.py:575` |

**Định nghĩa "FK hợp lệ" (per-FK, validate chỉ khi non-empty — fail-fast):**

1. **incident_report:** nếu `incident_report` non-empty (truthy) → BẮT BUỘC `frappe.db.exists("Incident Report", incident_report)` truthy; fail → `nthrow(MSG.IMM09_INCIDENT_REPORT_NOT_FOUND, error_code=ErrorCode.VALIDATION_ERROR, incident_report=incident_report)`.
2. **source_pm_wo:** nếu `source_pm_wo` non-empty (truthy) → BẮT BUỘC `frappe.db.exists("PM Work Order", source_pm_wo)` truthy; fail → `nthrow(MSG.IMM09_SOURCE_PM_WO_NOT_FOUND, error_code=ErrorCode.VALIDATION_ERROR, source_pm_wo=source_pm_wo)`.
3. **Empty = skip (standalone, slide 24b):** `incident_report=''` AND `source_pm_wo=''` → KHÔNG validate, KHÔNG raise → happy-path standalone GIỮ nguyên (R-pre regression-safe). Đây là lý do dùng `if incident_report:` / `if source_pm_wo:` (chỉ gate non-empty), KHÔNG gate vô điều kiện.

> **⚠️ Implementation note (BE):**
> - Helper gợi ý: `_assert_valid_create_fks(incident_report, source_pm_wo)` trong `services/imm09.py` (1 SoT cho gate), hoặc inline 2 `if`-block. Dùng `frappe.db.exists(doctype, name)` (rẻ, index `name`), KHÔNG `get_doc` (load thừa).
> - `ErrorCode` đã được import sẵn `services/imm09.py:26` (R25 đã thêm) — KHÔNG cần thêm import.
> - 2 MSG mới `IMM09_INCIDENT_REPORT_NOT_FOUND` + `IMM09_SOURCE_PM_WO_NOT_FOUND` đã có constant + registry entry (`utils/messages.py`, http_status=422) — sau khi BE/test xong, chạy `python scripts/gen_fe_messages.py` regen `frontend/src/i18n/messages.ts`.

**Vị trí gate trong `create_work_order` (services/imm09.py:787-822):** chèn SAU `asset_ref`-validate (`:790-791`, `IMM09_ASSET_NOT_FOUND`) + open-WO-guard (`:793-798`, `IMM09_ASSET_HAS_OPEN_WO`), TRƯỚC `frappe.get_doc({...})` (`:805`). Thứ tự: rbac → asset-not-found → open-WO → **incident_report∄ (`IMM09_INCIDENT_REPORT_NOT_FOUND`) → source_pm_wo∄ (`IMM09_SOURCE_PM_WO_NOT_FOUND`)** → get_doc/insert. Khi gate fail: `nthrow(...)` raise TRƯỚC `get_doc`/`insert`/`transition_asset_status`/`commit` ⇒ doc KHÔNG insert, KHÔNG partial-write, KHÔNG commit (invariant `frappe.db.exists("Asset Repair", {asset_ref})` không thêm WO mới). `asset_ref`-validate đứng trước gate này GIỮ nguyên (ngoài scope).

**Error contract (DONE-gate spec-contract — Error-on-HTTP-200, KHÔNG raise→4xx):**

```text
nthrow(MSG.IMM09_INCIDENT_REPORT_NOT_FOUND,
       error_code=ErrorCode.VALIDATION_ERROR,   # override bucket
       incident_report=incident_report)
# (source_pm_wo tương tự với MSG.IMM09_SOURCE_PM_WO_NOT_FOUND + source_pm_wo=...)
```

→ envelope (in-handler, qua `handle()`, HTTP-200 status-line): `{success:false, error:<render template>, code:'VALIDATION_ERROR', http_status:422}`.

- `http_status:422` ← registry entry `["http_status"]=422` cho cả 2 MSG.
- `code:'VALIDATION_ERROR'` ← **override bắt buộc** `error_code=ErrorCode.VALIDATION_ERROR`. KHÔNG override → default-map `422 → BUSINESS_RULE` ⇒ `code='BUSINESS_RULE'` (SAI acceptance). Cùng cặp `VALIDATION_ERROR×422` của R25 — xem ADR-IMM09-CREATE-FK.
- Cả `code='VALIDATION_ERROR'` (yaml `Error.code` enum) và `http_status=422` (yaml `Error.http_status` enum) ĐỀU ∈ bounded-enum đã chốt (R11) ⇒ valid against `#/components/schemas/Error`, **KHÔNG schema mới**. Nhánh Error này đã được phủ bởi `200 = oneOf [CreateRepairWorkOrderCreatedEnvelope, Error]` (yaml line 5789-5791) — đây là **lý do KHÔNG đụng contract path/schema** round này (chỉ bồi mô tả Error-case prose vào 200.description, §05/yaml).

**Boundaries (Always / Never):**

| | |
|---|---|
| **Always** | Validate per-FK CHỈ khi non-empty (`if incident_report:` / `if source_pm_wo:`) bằng `frappe.db.exists(<target DocType>, <value>)`, SERVER-SIDE, TRƯỚC `get_doc`/`insert`. Thứ tự: sau asset_ref-validate + open-WO-guard, TRƯỚC get_doc. Fail → `nthrow(MSG.IMM09_INCIDENT_REPORT_NOT_FOUND` / `IMM09_SOURCE_PM_WO_NOT_FOUND, error_code=ErrorCode.VALIDATION_ERROR, ...)` ⇒ `code='VALIDATION_ERROR'` + `http_status=422`, doc KHÔNG insert, KHÔNG commit (no partial-write). Cả 2 FK rỗng (standalone slide 24b) → PASS, tạo WO `status=Open` như cũ (regression-safe R-pre). 2 FK tồn-tại thật → PASS, ghi đúng giá trị. |
| **Never** | KHÔNG validate vô điều kiện (FK rỗng PHẢI pass — standalone hợp lệ; gate rỗng = regress happy-path). KHÔNG raise→HTTP-4xx (lỗi nghiệp vụ = in-handler HTTP-200 + Error envelope). KHÔNG dùng `code='VALIDATION'` hay `code='BUSINESS_RULE'`. KHÔNG thêm schema mới vào yaml (nhánh Error đã có). KHÔNG bỏ `error_code` override. KHÔNG xoá `ignore_links=True` (giữ — nhiều Link khác; gate phủ đúng 2 FK). KHÔNG đụng `asset_ref`-validate (`IMM09_ASSET_NOT_FOUND`, đã có — ngoài scope). KHÔNG đổi path/opId count contract (giữ 34/34). |

**ADR-IMM09-CREATE-FK — referential-integrity gate cho 2 optional Link FK trong `create_work_order` (capability-agnostic, Error code `VALIDATION_ERROR`×422)**

- **Status:** Accepted · **Date:** 2026-06-16
- **Context:** `create_work_order` build doc với `incident_report` + `source_pm_wo` từ caller rồi `ignore_links=True` + insert — không kiểm 2 FK optional. Caller truyền non-empty bịa ⇒ WO tạo với FK trỏ record-không-tồn-tại, phá traceability nguồn-gốc (R26). Đối xứng R25 (`assigned_to`) nhưng phủ 2 FK nguồn (Incident Report / PM Work Order). `ignore_links=True` cố ý bypass FK Frappe (nhiều Link trong doc + perf) — KHÔNG thể chỉ tháo cờ. Slide 24b chốt standalone hợp lệ (cả 2 FK rỗng) ⇒ gate PHẢI conditional (chỉ non-empty), KHÔNG vô điều kiện. `asset_ref` đã validate sẵn (`IMM09_ASSET_NOT_FOUND` http-404) — ngoài scope.
- **Decision:** (1) Thêm per-FK existence gate (chỉ khi non-empty) trong `create_work_order`, SAU asset_ref-validate + open-WO-guard, TRƯỚC `get_doc`/insert — `frappe.db.exists("Incident Report", incident_report)` / `frappe.db.exists("PM Work Order", source_pm_wo)`. (2) Fail → `nthrow(<MSG>, error_code=ErrorCode.VALIDATION_ERROR, <fk>=...)`. (3) Envelope dùng registry `http_status=422` (input không hợp lệ — field-level) + **override** `error_code=VALIDATION_ERROR` (đồng nhất R25, FE route nhánh validation). Cả 2 ∈ bounded-enum R11 ⇒ valid `Error`, KHÔNG schema mới.
- **Alternatives (rejected):** (a) **tháo `ignore_links=True`** để Frappe tự validate FK — vỡ các Link khác (asset_ref...) + raise `LinkValidationError`→HTTP-417/500 (KHÔNG Error-on-200), lệch contract; (b) **validate vô điều kiện** (kể cả FK rỗng) — regress standalone slide 24b (`''` không phải record → exists=False → raise oan), vỡ happy-path; (c) **`code='BUSINESS_RULE'`** (default 422 nếu quên override) — đúng http nhưng FE phân nhánh UX sai (đây input-validation); (d) **`code='VALIDATION'`** (422 tự nhiên) — acceptance + đồng nhất R25 chốt `VALIDATION_ERROR`; (e) **dùng `IMM09_ASSET_NOT_FOUND` chung cho cả 3 FK** — message mơ hồ (user không biết FK nào sai), và `asset_ref` http-404 ≠ 422 của 2 FK optional → 2 MSG riêng rõ ràng hơn; (f) **validate FE-only qua picker** (Incident/PM dropdown) — picker là UX, client tự gõ / app khác / replay bypass → KHÔNG phải boundary.
- **Consequences:** FK rác bị chặn tại boundary đúng (server). Thêm 2 MSG (`IMM09_INCIDENT_REPORT_NOT_FOUND` + `IMM09_SOURCE_PM_WO_NOT_FOUND`) + gate inline/helper. KHÔNG đổi contract yaml schema/path (nhánh Error đã có, 34/34 giữ). Cặp `VALIDATION_ERROR×422` đồng nhất ADR-IMM09-VALIDATE-TECH (R25) — ngoại lệ chủ đích vs default-map, ghi ADR để không "sửa cho khớp _HTTP_FOR_CODE". Regression-safe: standalone (slide 24b) + happy-path 2-FK-tồn-tại KHÔNG đổi. Pattern này nên nhân ra mọi service dùng `ignore_links=True` với Link optional CHƯA validate (xem §3.3 R25 cho `assigned_to`).

---

### 3.5 Mobile-BE contract — repair spare-parts sub-flow (`searchSpareParts` GET + `requestSpareParts` POST)

Bồi **2 path** vào contract mobile `docs/mobile/openapi/assetcore-mobile.openapi.yaml` để app field-tech lấp **sub-flow vật-tư** trên màn repair-detail: KTV đang sửa WO (`Pending Parts`/`In Repair`) cần (1) **tìm vật tư** (`searchSpareParts`, picker) rồi (2) **gắn phiếu xuất kho** vào dòng vật tư (`requestSpareParts`). Cặp này nối tiếp `submitDiagnosis(needs_parts=1)` (§8.11-bis, → `Pending Parts`) → spare-parts → `startRepair`/`closeWorkOrder`. Acceptance: YAML path/opId 40→42 (`searchSpareParts` + `requestSpareParts` UNIQUE camelCase), `info.version` GIỮ `0.1.0-skeleton`, 0 dangling `$ref`.

**Grounding @source (verify-before-claim):**

| Mục | Giá trị | Evidence |
|---|---|---|
| Handler search | `search_spare_parts(query="", limit="10")` — bare `@frappe.whitelist()` (GET), **KHÔNG `rbac.require`** | `api/imm09.py:123-125` |
| Service search return | `list[dict]` RAW (cap SQL `LIMIT`); query `<2` ký tự → `[]` | `services/imm09.py:1223-1248` |
| Search item shape | EXACT 10-key `{item_code, item_name, manufacturer_part_no, qty, uom, unit_cost, total_cost, stock_entry_ref, notes, idx}` | `services/imm09.py:1237-1246` |
| Handler request | `request_spare_parts(name, parts="[]")` — **`@frappe.whitelist(methods=["POST"])` SẴN @source** (HEAD-committed, KHÔNG cần flip) | `api/imm09.py:77-81` |
| Request cap | api-level `rbac.require("repair.write")` (`:79`) + service-level `rbac.require("repair.create")` (`:973`) | `api/imm09.py:79`, `services/imm09.py:973` |
| Service request return | EXACT 4-key `{name, status, updated, allocation}` (`allocation` str\|None — Gate-2 IMM-15) | `services/imm09.py:1018-1019` |
| Request 404 | WO∄ → `nthrow(MSG.IMM09_NOT_FOUND)` (in-handler 404 trên HTTP-200) | `services/imm09.py:976` |

**Self-Correction (2 điểm — bug thiết kế gốc, sửa Core Doc TRƯỚC):**

1. **`requestSpareParts` KHÔNG reuse `RepairActionResponse` 2-key.** Contract-doc §8.11 (`docs/mobile/04-api-contract.md`) forward-reserve `RepairActionResponse {name,status}` để "tái dùng cho `assign_technician`/`submit_diagnosis`/`request_spare_parts`". Đúng cho `submit_diagnosis` (2-key) nhưng **SAI cho `request_spare_parts`**: service THẬT trả **4-key** `{name,status,updated,allocation}` (`services/imm09.py:1018-1019`). ⇒ Phải sinh schema RIÊNG `RequestSparePartsResponse` (C3-split field-disjoint — precedent `ResolveIncidentResponse` 3-key thêm `rca_created`). `assign_technician` cũng đã RIÊNG 3-key (§3.2). Forward-reservation chỉ đúng cho action 2-key thuần.
2. **Premise "flip bare→`methods=['POST']`" đã STALE.** Acceptance ghi flip `request_spare_parts` bare→POST, nhưng `git show HEAD:assetcore/api/imm09.py` cho thấy decorator **đã là `@frappe.whitelist(methods=["POST"])`** (committed vòng trước). ⇒ `requestSpareParts` là **CLEAN POST** (mirror `closeIncident` §8.16), KHÔNG verb-divergence, KHÔNG vào `_PARITY_VERB_ALLOWLIST` (giữ `set()` rỗng). BE step PURE-YAML cho **cả 2** endpoint (search bare GET untouched; request đã POST-only untouched) — `git diff api/imm09.py` cho 2 hàm này = empty.

**Boundaries (Always / Never):**

| | |
|---|---|
| **Always** | `searchSpareParts` GET, `data` = **array `<SearchSparePartItem>` RAW** (KHÔNG `{...,items}`/pagination — `_ok(list)` `api/imm09.py:125`), item `additionalProperties:false` EXACT 10-key `required[item_code]`. Slot `{200,401}` — KHÔNG 403 (api-level no `rbac.require`). `requestSpareParts` POST, `data` = `RequestSparePartsResponse` `additionalProperties:false` 4-key `required[name,status]`; `status` enum RepairStatus 9-state; `updated` integer; `allocation` `type:string nullable:true`. requestBody `oneOf[application/json, x-www-form-urlencoded]` (Frappe `form_dict`) `required[name,parts]`, `parts` item props `{item_code, stock_entry_ref?, spare_part?, qty?}`. Cả 2: 200 = `oneOf[<Envelope>, Error]` route-by-VALUE `body.success` (0 discriminator, closed). |
| **Never** | KHÔNG reuse `RepairActionResponse` cho `requestSpareParts` (4-key ≠ 2-key — Self-Correction #1). KHÔNG thêm pagination cho `searchSpareParts` (svc trả list trần). KHÔNG khai 403 cho `searchSpareParts` (no api-level cap-gate). KHÔNG bịa status-line key 404 (WO∄ arrive HTTP-200 + Error, route `body.http_status`). KHÔNG dùng discriminator (`success` boolean illegal §5c). KHÔNG flip/đụng `api/imm09.py` (request đã POST-only; search bare GET — PURE-YAML). KHÔNG thêm entry `_PARITY_VERB_ALLOWLIST` (request CLEAN POST). KHÔNG đổi `info.version` (giữ `0.1.0-skeleton`). |

**ADR-IMM09-SPARE-SEARCH — `searchSpareParts` GET RAW-list, no-pagination, slot `{200,401}` no-403**

- **Status:** Accepted · **Date:** 2026-06-27
- **Context:** màn repair-detail mobile cần picker tìm vật-tư trước khi gắn phiếu xuất kho. BE `search_spare_parts` đã sẵn (bare `@frappe.whitelist()` GET `api/imm09.py:123`), trả `list[dict]` RAW cap bởi SQL `LIMIT` (KHÔNG paginate `services/imm09.py:1223-1248`), KHÔNG `rbac.require` ở api-level (read-only picker — quyền đọc đủ).
- **Decision:** thêm 1 path `GET …search_spare_parts` opId `searchSpareParts`; `data` = array `<SearchSparePartItem>` RAW (envelope `SearchSparePartsEnvelope` closed `required[success,data]`, `data` là list trần KHÔNG `{...,items}`); item EXACT 10-key `required[item_code]`. 200 = `oneOf[SearchSparePartsEnvelope, Error]` route-by-VALUE. Slot `{200,401}` — **KHÔNG 403** (no api-level cap-gate). `[]` rỗng hợp lệ (query<2 / no-match — KHÔNG 404).
- **Alternatives (rejected):** (a) bọc data trong `{query, items}` như `getAssetIncidentHistory {asset,items}` — svc THẬT trả list trần, thêm wrapper = lệch source + drift codegen; (b) thêm pagination `{page,page_size,total}` — svc không paginate (chỉ `limit` cap), bịa total → sai; (c) khai slot 403 — handler KHÔNG `rbac.require` ⇒ không có in-handler cap-403, khai 403 = phantom (mirror `getUserContext` §8.19 no-403); (d) đưa vào `_MVP_BUSINESS_PATHS` (ép 401∧403 symmetry) — vỡ vì no-403 (giống `getUserContext`).
- **Consequences:** mobile có picker vật-tư typed; client đọc list trần cap bởi `limit`. Path/opId 40→41. `searchSpareParts` ∉ `_MVP_BUSINESS_PATHS` (read-only no-cap-gate path) — typed-200 oneOf phủ bởi guard riêng. 0 đụng `.py` (PURE-YAML).

**ADR-IMM09-REQUEST-PARTS — `requestSpareParts` POST, `RequestSparePartsResponse` RIÊNG 4-key (KHÔNG reuse 2-key), CLEAN POST**

- **Status:** Accepted · **Date:** 2026-06-27
- **Context:** sau khi tìm vật-tư, KTV gắn `stock_entry_ref` vào dòng `spare_parts_used` của WO. BE `request_spare_parts` đã sẵn **POST-only @source** (`@frappe.whitelist(methods=["POST"])` `api/imm09.py:77`, HEAD-committed). Service trả **4-key** `{name,status,updated,allocation}` (`services/imm09.py:1018-1019`) — `updated` (số row gắn được) + `allocation` (name `IMM Spare Allocation` Gate-2 IMM-15, str\|None). KHÁC giả định forward-reservation §8.11 (reuse `RepairActionResponse` 2-key cho `request_spare_parts`).
- **Decision:** thêm 1 path `POST …request_spare_parts` opId `requestSpareParts`; schema RIÊNG `RequestSparePartsRequest` (`required[name,parts]`, `parts` item `{item_code, stock_entry_ref?, spare_part?, qty?}`, content `oneOf[json, x-www-form]`) + `RequestSparePartsEnvelope`(`data=RequestSparePartsResponse {name,status,updated,allocation}` closed `required[name,status]`, `allocation` nullable). 200 = `oneOf[RequestSparePartsEnvelope, Error]` route-by-VALUE. Slot `{200,401,403}`; 403 SINGLE-SHAPE dispatcher-403 (in-handler cap-403 `repair.write`+`repair.create` phủ bởi nhánh Error). `IMM09_NOT_FOUND` (404) arrive HTTP-200 + Error.
- **Alternatives (rejected):** (a) **reuse `RepairActionResponse` 2-key** — DROP `updated`+`allocation`, client mất tín hiệu "đã gắn mấy dòng" + "allocation Gate-2 nào tạo" → thừa re-fetch + lệch source (Self-Correction #1); (b) **flip decorator bare→POST round này** — đã POST-only @source (Self-Correction #2), flip = no-op + vi phạm PURE-YAML; (c) **vào `_PARITY_VERB_ALLOWLIST`** — chỉ dành cho bare-`@whitelist` write-action chờ fix (submit_pm_result/submit_calibration §8.14/§8.15); `request_spare_parts` đã CLEAN POST ⇒ KHÔNG cần allowlist (giữ `set()` rỗng); (d) **khai status-line 404** — lỗi nghiệp vụ in-handler arrive HTTP-200 + Error (route `body.http_status`), KHÔNG status-line.
- **Consequences:** mobile đóng sub-flow vật-tư; `searchSpareParts` (picker) có đích tiêu thụ. Path/opId 41→42. `requestSpareParts` ∈ `_MVP_BUSINESS_PATHS` (cap-gated write-action) ⇒ 401∧403 symmetry tự cân. Codegen sinh `requestSpareParts(name,parts)` typed + `RequestSparePartsResponse` đọc `updated`/`allocation`. CLEAN POST — KHÔNG verb-divergence (mirror `closeIncident` §8.16), 0 ADR-fix-backlog. 0 đụng `.py` (PURE-YAML — request đã POST-only). Sau USER reload gunicorn `--preload` → LIVE reject GET(405) cho `request_spare_parts`; trước reload stale worker còn nhận GET — KHÔNG curl-verify LIVE (LL-DEPLOY-07).

### 3.6 Mobile-BE contract — `listRepairWorkOrders` self-scope `mine` (A2-symmetry CUỐI: tab "Phiếu CM của tôi" MVP-5b)

**Vấn đề gốc (A2 known-gap — contract nói dối):** OpenAPI `listRepairWorkOrders` (summary `[MVP-5b] Phiếu CM của tôi`) description CLAIM **"Scope theo user"**, NHƯNG `list_repair_work_orders(filters, page, page_size)` (`api/imm09.py:21`) **KHÔNG có cơ chế** scope `assigned_to` — chỉ `parse_json(filters)` + `apply_vendor_scope("Asset Repair")` rồi `handle(svc.list_work_orders, …)`. ⇒ tab "Phiếu CM của tôi" trả **mọi** CM WO mà quyền đọc cho phép (với senior/QA `asset_repair_query` trả `""` → thấy hết, kể cả WO gán người khác), KHÔNG self-scope. Đối-xứng hệt R38 PM (ADR-MOBILE-016) — đây là **mắt-xích CUỐI** đóng đối-xứng A2 self-scope cho 3 list-read MyWorkOrdersView (Incident `reported_by` ADR-015 / PM `assigned_to` ADR-016 / **CM `assigned_to` ADR-017**).

**5-câu-hỏi domain:** (stage HTM) Operation/Maintenance — corrective; (NĐ98) traceability nghiệp vụ sửa-chữa gắn đúng KTV; (stakeholder) KTV field-tech mobile + senior/QA web; (lifecycle event) repair_assigned đã ghi `assigned_to` (`services/imm09.py:449`); (hậu quả nếu data sai) tab hiển thị WO người khác → KTV nhầm việc, nhưng **không leak quyền** vì read-gating GIỮ DocPerm — `mine` chỉ là filter hiển thị.

| Khía cạnh | Quyết định | Evidence |
|---|---|---|
| Param | `mine: int = 0` (`0\|1`), inject @api SAU `apply_vendor_scope("Asset Repair")`, TRƯỚC `handle(svc.list_work_orders)` | `api/imm09.py:21,29-30` (mirror `api/imm08.py:28,33-34`) |
| Injection | `if int(mine or 0): f["assigned_to"] = frappe.session.user` | mirror `list_pm_work_orders` |
| count==rows | `count_with_or` + `get_all` CÙNG `filters` dict (đã có `assigned_to`) + CÙNG `permission_query_conditions` | `repositories/base.py:65-71`, `permissions.py:115 asset_repair_query` |
| Backward-compat | `mine=0`/absent ⇒ `filters` BYTE-IDENTICAL baseline (web-FE `RepairWorkOrderListView` KHÔNG đổi) | — |
| Contract | OpenAPI REUSE `components/parameters/WorkOrderMine` (R38) — **0 component mới**; param-set `{WorkOrderFilters,Page,PageSize}`→+`WorkOrderMine`=4; path-count GIỮ 46 | `docs/mobile/openapi/assetcore-mobile.openapi.yaml` |

**Boundaries:**

| | |
|---|---|
| **Always** | `mine` ANDed với mọi key trong `filters` JSON-blob (kể cả virtual `open` → `open_repair_filter`, `sla_breached`). Inject `assigned_to=session.user` @api SAU `apply_vendor_scope`. count==rows giữ (cùng filters dict). `mine=0`/absent = baseline byte-identical. REUSE `WorkOrderMine` (KHÔNG component mới). |
| **Never** | KHÔNG tạo component `RepairWorkOrderMine` (shape trùng `WorkOrderMine`). KHÔNG thêm endpoint `list_my_repair_work_orders` (+path). KHÔNG auto-scope qua `permission_query_conditions` (vỡ view senior/QA cần thấy tất cả). KHÔNG seed @service (CM filters JSON-blob @api như PM). KHÔNG coi `mine` là security-boundary (read-gating vẫn DocPerm `repair.read`+`asset_repair_query`). KHÔNG đụng `services/imm09.py`/`repositories/`. |

**ADR-IMM09-LISTMINE — `listRepairWorkOrders` self-scope qua param opt-in `mine` (REUSE `WorkOrderMine`, inject @api SAU `apply_vendor_scope`)**

- **Status:** Accepted · **Date:** 2026-06-29 · đối-xứng ADR-MOBILE-016 (PM) — xem mobile `docs/mobile/ADR-MOBILE-017.md`.
- **Context:** `list_repair_work_orders` claim "Scope theo user" nhưng không có cơ chế `assigned_to` (claim suông). Tab "Phiếu CM của tôi" (MVP-5b) cần self-scope. `WorkOrderMine` đã tồn tại từ R38 (PM) — cùng field `assigned_to`, cùng int 0|1. CM filters là JSON-blob `parse_json` @api (như PM, KHÁC imm12 discrete param).
- **Decision:** REUSE `WorkOrderMine` + `$ref` vào `listRepairWorkOrders.parameters` + sửa description; `api/imm09.py` thêm `mine: int = 0` + `if int(mine or 0): f["assigned_to"]=frappe.session.user` SAU `apply_vendor_scope`. KHÔNG đụng service/repo.
- **Alternatives (rejected):** (a) endpoint riêng — +path, nhân đôi enrich/SLA-derive; (b) component `RepairWorkOrderMine` mới — shape trùng `WorkOrderMine`, vỡ "0 component mới"; (c) `permission_query_conditions` auto-scope — vỡ view senior/QA (`asset_repair_query` trả `""` để thấy tất cả); (d) seed @service — CM filters parse @api, inject @api blast-radius nhỏ hơn.
- **Consequences:** contract trung thực; `mine=0` backward-compat đo được; count==rows giữ; path-count 46 + 0 component mới ⇒ `generate_spec` get=232/post=256/total=488 UNCHANGED (`test_oas_d12/d15/d17` re-verify, KHÔNG re-baseline). Đóng TRỌN đối-xứng A2 (Incident/PM/CM). `mine` = filter ứng-dụng KHÔNG-phải-security-boundary.

---

## 4. Service Layer

File: `assetcore/services/imm09.py`

### Public functions

| Function | Input | Output | Side effect |
|---|---|---|---|
| `validate_repair_source(doc)` | Document | None | raise ServiceError BR-09-01 |
| `validate_asset_not_under_repair(asset_ref)` | str | None | raise ServiceError BR-09-05 duplicate |
| `check_repeat_failure(doc)` | Document | None | set `doc.is_repeat_failure` |
| `set_asset_under_repair(asset_ref, wo_name)` | str, str | None | Asset status → Under Repair; ALE repair_opened |
| `validate_spare_parts_stock_entries(doc)` | Document | None | raise ServiceError BR-09-02 |
| `validate_firmware_change_request(doc)` | Document | None | raise ServiceError BR-09-03 |
| `validate_repair_checklist_complete(doc)` | Document | None | raise ServiceError BR-09-04 |
| `get_sla_target(risk_class, priority)` | str, str | float | **BẤT BIẾN** (BR-09-10 không đụng) — vẫn tra `_SLA_MATRIX`. |
| `is_sla_breached(elapsed_hours, sla_target)` | float, float | bool | **SoT predicate (BR-09-07) — BẤT BIẾN** (biên `>=`, không đổi): `elapsed_hours >= sla_target`. Hàm DUY NHẤT quyết định breach — gọi từ cả `complete_repair` LẪN `check_repair_sla_breach`. BR-09-10 chỉ đổi NGUỒN `elapsed_hours` (clock-stop), KHÔNG đổi hàm này. Cấm so sánh breach inline ở nơi khác. |
| `repair_elapsed_hours(doc, until)` | Document\|dict, datetime | float | **MỚI — SoT clock-stop elapsed (BR-09-10), INV-CM-HOLD-1.** `= max(0, ((until − open_datetime) − parts_hold_effective)/3600)` với `parts_hold_effective = parts_hold_hours_seconds + (until − parts_hold_started nếu parts_hold_started non-null)`. Pure, no DB write. Điểm DUY NHẤT phái sinh elapsed cho breach+MTTR — `complete_repair`, `check_repair_sla_breach`, `_row_is_live_overdue` ĐỀU gọi hàm này. Cấm tính `(until−open)` thô để quyết breach/MTTR ở nơi khác. |
| `enter_parts_hold(doc)` | Document | None | **MỚI (BR-09-10):** stamp `doc.parts_hold_started = now_datetime()` (idempotent: nếu đã non-null thì giữ nguyên, không re-stamp); ALE `parts_hold_started`. Gọi từ `submit_diagnosis(needs_parts=1)`. |
| `exit_parts_hold(doc, until=None)` | Document, datetime\|None | None | **MỚI (BR-09-10):** nếu `parts_hold_started` non-null → `parts_hold_hours += max(0, (until or now()) − parts_hold_started)`/3600 (biên Δ==0 ⇒ +0, INV-CM-HOLD-3), reset `parts_hold_started=null`; ALE `parts_hold_resumed`. Idempotent: nếu đã null → no-op. Gọi từ `start_repair`/`request_spare_parts` (khi rời Pending Parts) + `complete_repair`/cannot_repair (chốt cuối, until=completion). |
| `is_repair_open(status)` | str\|None | bool | **SoT predicate (BR-09-08)**: open ⟺ `status NOT IN REPAIR_TERMINAL_STATES`; None/rỗng → open. Hàm DUY NHẤT định nghĩa "đang mở". |
| `open_repair_filter(extra=None)` | dict\|None | dict | Trả `{'status': ['not in', sorted(REPAIR_TERMINAL_STATES)], **extra}` (sorted → deterministic, khớp drill SQL byte-for-byte) — filter dùng chung cho mọi `_count`/`get_all`/drill SQL. |
| `sla_breach_live_filter(extra=None)` | dict\|None | dict | **SoT live (BR-09-07 LIVE)**: nhánh "open & vượt hạn & cờ chưa stamp" = `open_repair_filter()` ∧ `{'sla_breached': 0}` ∧ `{'open_datetime': ['<', <cutoff_for_each_sla_bucket>]}`. Vì `sla_target_hours` khác nhau theo (risk_class, priority) → predicate **per-row** (xem `_row_is_live_overdue`); filter này dùng để **thu hẹp candidate** (chỉ WO open & cờ=0), rồi lọc chính xác in-Python. Terminal loại tự nhiên (INV-CM-SLA-4). |
| `cm_sla_breach_count()` | — | int | **SoT live count (BR-09-07 LIVE)**: `count(sla_breached=1)` + `count(candidate open & cờ=0 thoả `_row_is_live_overdue`)`. 2 nhánh exclusive (cờ=1 vs cờ=0) → no double-count, **idempotent vs scheduler** (INV-CM-SLA-2). Wired vào `api/dashboard.py` `cm_sla_breached` thay `_count({sla_breached:1})`. |
| `_row_is_live_overdue(row, now)` | dict, datetime | bool | Per-row derive: `row.sla_breached==0` ∧ `is_repair_open(row.status)` ∧ `is_sla_breached(repair_elapsed_hours(row, now), row.sla_target_hours)`. **BR-09-10:** elapsed dùng SoT clock-stop `repair_elapsed_hours` (trừ `parts_hold_hours` + open-leg đang chạy nếu row.status==Pending Parts) thay `(now−open)` thô ⇒ WO ở Pending Parts KHÔNG live-overdue oan. KHÔNG query thêm — `row` PHẢI có `parts_hold_hours`/`parts_hold_started` trong `fields=[...]`. |
| `_enrich_sla_breach(rows)` | list | None | Gắn `is_sla_breached = bool(row.sla_breached) or _row_is_live_overdue(row, now)` cho mỗi row (in-Python, no extra query). Gọi trong `list_work_orders` → drill có live-truth (INV-CM-SLA-5). |
| `confirm_inspection(name)` | str | dict `{name, status, mttr_hours, sla_breached}` | Pending Inspection → Completed; submit doc → `complete_repair()`; requires `CAN_APPROVE_DEP` role; auto-trigger IMM-12 chronic detect nếu root_cause chứa từ khóa lặp lại |
| `complete_repair(doc)` | Document | None | mttr, sla_breached, **state-machine-guarded asset restore (BR-09-09)**, ALE. **BR-09-10:** TRƯỚC khi tính elapsed → `exit_parts_hold(doc, until=completion_datetime)` chốt open-leg hold cuối (INV-CM-HOLD-5); `mttr_hours = repair_elapsed_hours(doc, completion_datetime)`; `sla_breached = is_sla_breached(repair_elapsed_hours(...), sla_target) OR doc.sla_breached`. Asset→Active CHỈ khi `prev_status == 'Under Repair'`; nếu đang `Out of Service` (hold governance khác) → giữ OoS; nếu `Decommissioned` (terminal) → bỏ qua restore. NEVER raise từ nhánh restore (INV-09-RESTORE-1). |
| `check_repair_sla_breach()` | — | None | **BR-09-10:** elapsed = `repair_elapsed_hours(wo, now())` (clock-stop, trừ hold đang chạy nếu Pending Parts) thay `(now−open)` thô; set sla_breached qua `is_sla_breached`; publish realtime. INV-CM-HOLD-6 (card==scheduler==stamp). |
| `check_repair_overdue()` | — | None | email Workshop Manager |
| `update_asset_mttr_avg()` | — | None | **BẤT BIẾN** (BR-09-10 không đụng): roll-up AVG(`mttr_hours`) 12 tháng. Vì `mttr_hours` đã là clock-stop tại nguồn (`complete_repair`), avg tự động phản ánh đúng — KHÔNG sửa hàm này. |
| `_is_repair_capable(technician)` | str | bool | **MỚI (R25, BR-09-DISPATCH):** SoT 1-chỗ cho "user được phép nhận giao việc sửa chữa". `= frappe.has_permission("Asset Repair", "write", user=technician)` (capability/DocPerm, KHÔNG so tên role — chống RBAC dead-gate). KHÔNG dùng `rbac.can` (resolve theo session, không nhận `user=`). |
| `assign_technician(name, *, technician, priority='')` | str, str, str | dict `{name, status, assigned_to}` | **SỬA (R25, BR-09-DISPATCH):** thêm dispatch-validation gate TRƯỚC set/save (sau status-gate Open). Gate 3-AND: `frappe.db.exists("User", technician)` ∧ `User.enabled==1` ∧ `_is_repair_capable(technician)`. Fail bất kỳ điều kiện → `nthrow(MSG.IMM09_INVALID_TECHNICIAN, error_code=ErrorCode.VALIDATION_ERROR, technician=technician)` (envelope `code='VALIDATION_ERROR'` + `http_status=422`) — raise TRƯỚC mutation ⇒ `assigned_to` GIỮ nguyên, `status` GIỮ Open (fail-fast, no partial write). Happy-path KHÔNG đổi (regression-safe R24). Xem ADR-IMM09-VALIDATE-TECH (§3.3). |
| `create_work_order(*, asset_ref, repair_type, priority, failure_description, incident_report='', source_pm_wo='', fault_image='')` | str × N | dict `{name, status, sla_target_hours}` | **SỬA (R26, BR-09-CREATE-FK):** thêm referential-integrity gate cho 2 optional Link FK, SAU `asset_ref`-validate (`IMM09_ASSET_NOT_FOUND`) + open-WO-guard (`IMM09_ASSET_HAS_OPEN_WO`), TRƯỚC `get_doc`/insert. Per-FK, CHỈ khi non-empty: `incident_report` truthy → `frappe.db.exists("Incident Report", incident_report)` (fail → `nthrow(MSG.IMM09_INCIDENT_REPORT_NOT_FOUND, error_code=ErrorCode.VALIDATION_ERROR, incident_report=...)`); `source_pm_wo` truthy → `frappe.db.exists("PM Work Order", source_pm_wo)` (fail → `nthrow(MSG.IMM09_SOURCE_PM_WO_NOT_FOUND, error_code=ErrorCode.VALIDATION_ERROR, source_pm_wo=...)`). Envelope `code='VALIDATION_ERROR'` + `http_status=422`. Raise TRƯỚC `get_doc`/insert/commit ⇒ doc KHÔNG insert, no partial-write. Cả 2 FK rỗng (standalone slide 24b) → PASS như cũ (regression-safe R-pre). `asset_ref`-validate GIỮ nguyên (ngoài scope). Xem ADR-IMM09-CREATE-FK (§3.4). |

| `attach_repair_checklist_photo(work_order_name, checklist_item_idx, filedata=None, filename="", content_type="")` | str, int, bytes?, str, str | dict `{file_url, file_name, checklist_item_idx}` | **MỚI (Vòng 3, BR-09-15/16, mobile CR-15/G6)** — đính ảnh bằng chứng per-mục checklist sửa chữa (NĐ98 Class C/D). Thứ tự reject TRƯỚC `File.insert`: `exists(WO)`→NOT_FOUND · permission (assignee/`repair.write`)→FORBIDDEN · `checklist_item_idx`→child-row `idx` VALIDATION · file present/content-type/size/max-count(=1) VALIDATION. Success: `File.insert(is_private=1, attached_to_doctype='Asset Repair', attached_to_name=WO, content=filedata, decode=False)` → `frappe.db.set_value("Repair Checklist", row.name, "photo", file_url, update_modified=False)` (**KHÔNG `doc.save()`** trên Asset Repair — anti-pattern #10, tránh re-validate BR-09-04/docstatus) → `create_lifecycle_event('repair_checklist_photo_attached')` **TRỰC TIẾP** (KHÔNG qua wrapper `_log_lifecycle_event` swallow — hard-req, event throw→rollback) → `commit`. §05 §3.10 + ADR-IMM09-PHOTO-01/02. Đối xứng `imm08.attach_pm_checklist_photo` / `imm12.attach_incident_photo`. |
| `_find_repair_checklist_row(wo, checklist_item_idx)` | Document, int | Repair Checklist row \| None | None — resolve mục checklist theo **Frappe child `idx`** (1-based) trong `wo.repair_checklist` (Repair Checklist KHÔNG có field STT domain như PM Checklist Result — xem ADR-IMM09-PHOTO-01). `return next((r for r in wo.repair_checklist if int(r.idx)==idx), None)`. None → nhánh reject VALIDATION (KHÔNG N+1: dùng list con đã load). |
| `_repair_checklist_item_photos(row)` | Repair Checklist row | `list[{file_url}]` | None — **SoT DUY NHẤT** ảnh/mục checklist (BR-09-16): đọc `row.photo` (`Attach` đơn trị). `return [{"file_url": row.photo}] if row.photo else []`. CÙNG nguồn mà `get_work_order` hiển thị (`repair_checklist[].photo`) VỪA đếm max-count ⇒ invariant **count==rows** (mirror `_pm_checklist_photos` imm08 / `_scene_photos` imm12). |
| `_assert_can_attach_repair_photo(wo)` | Document | None | None — BR-09-15 permission: KTV được giao (`wo.assigned_to == session.user`) HOẶC `frappe.has_permission("Asset Repair", "write", doc=wo, user=session.user)` (áp CẢ role-DocPerm write LẪN row-level hook `ac_asset_repair_query`/vendor-scope ⇒ tái dùng IDOR-guard). Thiếu cả 2 → `raise ServiceError(ErrorCode.FORBIDDEN, _MSG_REPAIR_PHOTO_FORBIDDEN, http_status=403)`. Mirror `_assert_can_attach_pm_photo` (imm08). |

### Firmware Change Request — transition service (BR-09-18/19/20, Vòng 10)

| Function | Input | Output | Side effect |
|---|---|---|---|
| `firmware_allowed_transitions(status)` | str | `(list[str], bool)` | **MỚI** — server-derive cho `get_firmware_cr`: raw `_FCR_VALID_TRANSITIONS.get(status,[])` LỌC theo capability caller (`firmware.approve` cho cạnh ∈ `_FCR_APPROVAL_EDGES`, `repair.write` cho cạnh còn lại) + trả `can_approve = rbac.can("firmware.approve")`. Pure, no write. |
| `_assert_valid_fcr_transition(current, target)` | str, str | None | **MỚI** — `target ∉ _FCR_VALID_TRANSITIONS.get(current,[])` → `raise ServiceError(BAD_STATE, "Không thể chuyển yêu cầu đổi firmware từ '{current}' sang '{target}'")`. |
| `_assert_can_approve_fcr()` | — | None | **MỚI** — `not rbac.can("firmware.approve")` → `raise ServiceError(FORBIDDEN, "Bạn không có quyền phê duyệt yêu cầu đổi firmware", http_status=403)`. In-handler → HTTP-200 Error envelope (KHÔNG rbac.require/4xx). |
| `firmware_transition(name, target, *, event_type, extra_fields=None, notes="")` | str, str, str, dict?, str | dict `{name, status}` | **MỚI** — thân chung: guard NOT_FOUND → cap-check (approve-edge → `_assert_can_approve_fcr`, else `repair.write`) → `_assert_valid_fcr_transition` → set `extra_fields` → `db_set("status", target)` → **canonical `create_lifecycle_event` TRỰC TIẾP** (hard-req, event throw → rollback status) → commit. |
| `approve_firmware_cr(name)` | str | dict `{name, status}` | **MỚI** — `Pending Approval → Approved`; cap `firmware.approve`; `extra_fields={approved_by: session.user, approved_datetime: now}`; event `firmware_cr_approved`. |
| `deploy_firmware_cr(name)` | str | dict `{name, status}` | **MỚI** — `Approved → Applied`; cap `repair.write`; `extra_fields={applied_datetime: now}`; event `firmware_deployed`. |
| `rollback_firmware_cr(name, *, rollback_reason)` | str, str | dict `{name, status}` | **MỚI** — `Applied → Rolled Back`; cap `firmware.approve`; `rollback_reason` rỗng → `raise ServiceError(VALIDATION, ...)` TRƯỚC transition; `extra_fields={rollback_reason}`; event `firmware_rolled_back`. |
| `submit_firmware_cr(name)` | str | dict `{name, status}` | **MỚI** — `Draft → Pending Approval`; cap `repair.write`; KHÔNG ALE (bước nội bộ). |

> **Lifecycle events MỚI (add option enum `Asset Lifecycle Event.event_type` → deploy `reload-doctype`, HARD-STOP USER):** `firmware_cr_approved`, `firmware_deployed`, `firmware_rolled_back`. Đối xứng cách thêm `repair_checklist_photo_attached` (§6 Audit). Test seed event qua `create_lifecycle_event` (KHÔNG chặn bởi enum chưa reload trên worker cũ).

### Constants đính ảnh bằng chứng (BR-09-15/16, mirror imm08/imm12)

```python
_DT_REPAIR_WO = "Asset Repair"
_DT_REPAIR_CHECKLIST_ROW = "Repair Checklist"
_DT_FILE = "File"
_REPAIR_PHOTO_CONTENT_TYPES = ("image/jpeg", "image/jpg", "image/png")
_EVENT_REPAIR_CHECKLIST_PHOTO_ATTACHED = "repair_checklist_photo_attached"
MAX_REPAIR_CHECKLIST_PHOTOS = 1              # per mục — SoT = row.photo (Attach đơn trị), mirror imm08 code
MAX_REPAIR_CHECKLIST_PHOTO_BYTES = 10 * 1024 * 1024   # 10 MB (parity mobile + imm12)

# Field-level VALIDATION messages (VN, Decision-B fields.file — KHÔNG leak raw cap/stack)
_MSG_REPAIR_PHOTO_MISSING     = "Thiếu tệp ảnh"
_MSG_REPAIR_PHOTO_NOT_IMAGE   = "Tệp phải là ảnh JPG hoặc PNG"
_MSG_REPAIR_PHOTO_TOO_LARGE   = "Ảnh vượt quá dung lượng cho phép (tối đa 10 MB)"
_MSG_REPAIR_PHOTO_MAX         = "Mỗi mục checklist chỉ đính 1 ảnh"
_MSG_REPAIR_PHOTO_FORBIDDEN   = "Không có quyền đính ảnh cho lệnh sửa chữa này"
_MSG_REPAIR_PHOTO_IDX_NOT_FOUND = "Không tìm thấy mục checklist trong lệnh sửa chữa này"
```

> **Field liên quan (ĐÃ tồn tại — KHÔNG migration schema):** `repair_checklist.photo` (`Attach`, permlevel=0) child của `Asset Repair.repair_checklist` (xác nhận `assetcore/assetcore/doctype/repair_checklist/repair_checklist.json`). Vòng này chỉ **ghi** vào field sẵn có + **thêm 1 option enum** `repair_checklist_photo_attached` vào `asset_lifecycle_event.json` (xem §6 Audit + ADR-IMM09-PHOTO-02). **Read-side `get_repair_work_order` KHÔNG đổi** — `get_work_order` dùng `doc.as_dict()` đã serialize `repair_checklist[].photo`.

### SLA Matrix

```python
def get_sla_target(risk_class: str, priority: str) -> float:
    """Tra ma trận SLA target (giờ) theo risk_class x priority."""
    sla_matrix = {
        ("Class III", "Emergency"): 4.0,
        ("Class III", "Urgent"):    24.0,
        ("Class III", "Normal"):    120.0,
        ("Class II",  "Emergency"): 8.0,
        ("Class II",  "Urgent"):    48.0,
        ("Class II",  "Normal"):    72.0,
        ("Class I",   "Emergency"): 24.0,
        ("Class I",   "Urgent"):    72.0,
        ("Class I",   "Normal"):    480.0,
    }
    return sla_matrix.get((risk_class, priority), 480.0)
```

### Clock-stop elapsed — Single Source of Truth (BR-09-10, Self-Correction)

**Vấn đề thiết kế gốc:** CẢ 3 consumer (`complete_repair` lúc đóng, scheduler `check_repair_sla_breach`, card `_row_is_live_overdue`) tính elapsed = wall-clock thuần `(now/completion − open_datetime)`, KHÔNG trừ thời gian WO nằm `Pending Parts` (kho hết hàng — blocker cung ứng/vendor lead-time NGOÀI tầm đội sửa). ⇒ inflate MTTR + **false SLA breach** (phạt oan đội sửa; méo KPI đáp ứng NĐ98 Article 56).

**Quyết định:** thêm helper SoT DUY NHẤT `repair_elapsed_hours` phái sinh elapsed-trừ-hold. CẢ 3 consumer gọi hàm này rồi truyền vào `is_sla_breached` (BR-09-07, biên `>=`, **BẤT BIẾN**). 2 field mới `parts_hold_hours` (cộng dồn) + `parts_hold_started` (mốc open-leg đang chạy).

```python
def repair_elapsed_hours(doc, until) -> float:
    """SoT DUY NHẤT (BR-09-10, INV-CM-HOLD-1): elapsed-trừ-hold (giờ).

    elapsed = (until − open_datetime) − tổng-thời-gian-Pending-Parts
    tổng-hold = parts_hold_hours (đã cộng dồn các khoảng ĐÃ ĐÓNG)
              + (until − parts_hold_started) nếu parts_hold_started còn non-null
                (open-leg ĐANG hold — WO hiện ở Pending Parts).

    Pure, no DB write. `doc` có thể là Document hoặc dict (row từ get_all) —
    đọc open_datetime / parts_hold_hours / parts_hold_started qua getattr/get.
    `parts_hold_hours==0 ∧ parts_hold_started==null` ⇒ trả đúng (until−open)/3600
    cũ (INV-CM-HOLD-4, no-regression).
    """
    open_dt = get_datetime(_field(doc, "open_datetime"))
    until_dt = get_datetime(until)
    wall_seconds = time_diff_in_seconds(until_dt, open_dt)
    hold_seconds = (_field(doc, "parts_hold_hours") or 0.0) * 3600.0
    started = _field(doc, "parts_hold_started")
    if started:                                  # open-leg đang hold
        hold_seconds += max(0.0, time_diff_in_seconds(until_dt, get_datetime(started)))
    return round(max(0.0, wall_seconds - hold_seconds) / 3600.0, 2)
```

**Stamp / accumulate (đối xứng enter ↔ exit, ⚠️ ORDERING):**

```python
def enter_parts_hold(doc) -> None:               # VÀO Pending Parts
    if doc.parts_hold_started:                   # idempotent — không re-stamp
        return
    doc.parts_hold_started = now_datetime()
    _log_lifecycle_event(asset=doc.asset_ref, event_type="parts_hold_started", ...)

def exit_parts_hold(doc, until=None) -> None:    # RA Pending Parts / chốt cuối
    if not doc.parts_hold_started:               # idempotent — không hold đang mở
        return
    until_dt = get_datetime(until) if until else now_datetime()
    delta_h = max(0.0, time_diff_in_seconds(            # biên Δ==0 ⇒ +0 (INV-CM-HOLD-3)
        until_dt, get_datetime(doc.parts_hold_started))) / 3600.0
    doc.parts_hold_hours = (doc.parts_hold_hours or 0.0) + round(delta_h, 4)
    doc.parts_hold_started = None                # reset (INV-CM-HOLD-2)
    _log_lifecycle_event(asset=doc.asset_ref, event_type="parts_hold_resumed", ...)
```

> **⚠️ ORDERING bắt buộc (INV-CM-HOLD-5):** trong `complete_repair` — gọi `exit_parts_hold(doc, until=completion_datetime)` để chốt open-leg cuối **TRƯỚC** khi `mttr_hours = repair_elapsed_hours(doc, completion_datetime)`. Nếu tính elapsed trước khi chốt, khoảng hold cuối bị bỏ sót. Sau chốt, `parts_hold_started` đã null ⇒ `repair_elapsed_hours` chỉ trừ `parts_hold_hours` (đã gồm khoảng cuối) — không double-count.

**Wiring (BE phải làm cùng commit):**
- `submit_diagnosis(needs_parts=1)` → `enter_parts_hold(doc)` trước `RepairRepo.save`.
- `start_repair` / `request_spare_parts` khi `doc.status == PENDING_PARTS` → `exit_parts_hold(doc)` trước khi đổi status sang In Repair.
- `complete_repair` → `exit_parts_hold(doc, until=completion_datetime)` rồi `mttr_hours = repair_elapsed_hours(doc, completion_datetime)`.
- `close_work_order(cannot_repair=1)` khi đang Pending Parts → `exit_parts_hold(doc, until=now())` trước khi đóng (audit khoảng hold cuối, dù WO không tính MTTR).
- `check_repair_sla_breach` / `_row_is_live_overdue`: `fields=[...]` PHẢI thêm `parts_hold_hours`, `parts_hold_started`; elapsed = `repair_elapsed_hours(row, now())`.
- **Grep-guard (zero-tolerance):** sau patch, 0 idiom `time_diff_in_seconds(now/completion, open) ... breach/mttr` thô ở 3 consumer — mọi elapsed cho breach/MTTR đi qua `repair_elapsed_hours`.

### SLA breach predicate — Single Source of Truth (BR-09-07)

`sla_breached` được quyết định bởi **một hàm thuần (pure) DUY NHẤT**. Mục tiêu: completion (`complete_repair`) và scheduler (`check_repair_sla_breach`) KHÔNG BAO GIỜ bất đồng về cùng một cặp `(elapsed_hours, sla_target)`. **BR-09-10:** `elapsed_hours` truyền vào hàm này LUÔN là output của `repair_elapsed_hours` (clock-stop) — KHÔNG phải wall-clock thô.

```python
def is_sla_breached(elapsed_hours: float, sla_target: float) -> bool:
    """SoT cho cờ vi phạm SLA của Asset Repair (BR-09-07).

    Quy ước BIÊN: elapsed BẰNG ĐÚNG target ⇒ ĐÃ vi phạm (`>=`).
    Lý do: target là hạn chót — chạm hạn là đã hết thời gian cho phép, nhất
    quán với hợp đồng SLA và với scheduler (vốn dùng `>=`). Đây là hàm DUY
    NHẤT được phép quyết định breach; cấm viết `mttr > target` / `>= sla`
    rải rác.
    """
    if elapsed_hours is None or sla_target is None:
        return False
    return float(elapsed_hours) >= float(sla_target)
```

**Quy tắc monotonic (latch):** một khi scheduler đã set `sla_breached=1` cho WO đang chạy, completion **KHÔNG được lật về 0**. `complete_repair` set cờ theo OR với giá trị hiện tại:

```python
doc.sla_breached = 1 if (is_sla_breached(doc.mttr_hours, doc.sla_target_hours)
                         or doc.sla_breached) else 0
```

Nhờ vậy: WO có MTTR == target (vd 72 == 72) → scheduler đánh breach=1 → completion giữ nguyên 1 (không flip-flop). MTTR < target và chưa từng breach → 0. MTTR > target → 1.

### KPI/drill 'SLA vi phạm' — LIVE SoT count (BR-09-07 LIVE, Self-Correction)

**Vấn đề thiết kế gốc (Self-Correction):** `api/dashboard.py` đặt `cm_sla_breached = _count("Asset Repair", {"sla_breached": 1})` — chỉ đếm **cờ đã stamp**. Cờ `sla_breached` chỉ set bởi `complete_repair()` (lúc đóng) hoặc scheduler hourly `check_repair_sla_breach()`. ⇒ WO **đang mở** vừa vượt hạn 1–59' nhưng scheduler chưa quét tới có `sla_breached=0` → **KHÔNG đếm** trên card đến đầu giờ kế = **undercount cửa-sổ-trễ-scheduler**. Đồng dạng lỗi đã sửa ở IMM-12 BR-12-09 (incident SLA live SoT).

**Quyết định:** card `cm_sla_breached` + drill đếm theo **live SoT predicate**, KHÔNG chỉ cờ stale. `cm_sla_breach_count()` = hợp 2 nhánh **loại trừ nhau**:

```python
def _row_is_live_overdue(row: dict, now) -> bool:
    """WO đang mở, cờ chưa stamp, nhưng (now - open_datetime) đã ≥ sla_target_hours."""
    if row.get("sla_breached"):                         # nhánh (1) lo cờ=1
        return False
    if not is_repair_open(row.get("status")):           # terminal loại tự nhiên (INV-CM-SLA-4)
        return False
    elapsed_h = time_diff_in_seconds(now, get_datetime(row["open_datetime"])) / 3600.0
    target = row.get("sla_target_hours") or get_sla_target(
        row.get("risk_class") or RiskClass.I, row.get("priority") or "Normal")
    return is_sla_breached(elapsed_h, target)           # SoT predicate (biên >=)

def cm_sla_breach_count() -> int:
    """SoT live count cho card 'SLA vi phạm'. 2 nhánh exclusive → idempotent vs scheduler."""
    flagged = RepairRepo.count({"sla_breached": 1})                       # (1) cờ lịch sử monotonic
    now = now_datetime()
    candidates = RepairRepo.list(                                          # (2) open & cờ=0
        filters=open_repair_filter({"sla_breached": 0}),
        fields=["name", "status", "open_datetime", "sla_target_hours",
                "risk_class", "priority"],
    )[0]
    live_open = sum(1 for r in candidates if _row_is_live_overdue(r, now))
    return flagged + live_open                                            # exclusive ⇒ no double-count

def _enrich_sla_breach(rows: list) -> None:
    """Per-row live-truth cho drill list (INV-CM-SLA-5). In-Python, no extra query."""
    now = now_datetime()
    for r in rows:
        r["is_sla_breached"] = bool(r.get("sla_breached")) or _row_is_live_overdue(r, now)
```

**Wiring:**
- `api/dashboard.py`: `cm_sla_breached = svc.cm_sla_breach_count()` (thay `_count({sla_breached:1})`). Grep-guard: 0 idiom `{"sla_breached": 1}` cho KPI tile.
- `list_work_orders()`: thêm `sla_target_hours` vào `fields=[...]`, gọi `_enrich_sla_breach(rows)` sau `_enrich_rows(rows)` ⇒ drill có `is_sla_breached` live.
- Filter drill `sla_breached=1`: `list_work_orders` trả tập theo enrich — FE đọc `is_sla_breached ?? sla_breached` (xem 06 §FE). Nếu BE cần lọc-server tập breach, dùng `cm_sla_breach_count` predicate (open∪flag) — KHÔNG lọc thô `{sla_breached:1}` (sẽ rớt live-overdue).

**Idempotent vs scheduler (INV-CM-SLA-2):** WO live-overdue đếm ở nhánh (2). Khi scheduler chạy → cờ thành 1 → WO chuyển sang nhánh (1), rời nhánh (2) (vì `sla_breached=0` không còn match). Tổng KHÔNG đổi. 2 nhánh phân hoạch theo cờ (1 vs 0) ⇒ KHÔNG bao giờ chồng.

### Open / terminal-state predicate — Single Source of Truth (BR-09-08)

**Vấn đề thiết kế gốc (Self-Correction, vòng 19):** khái niệm "Asset Repair đang mở" trước đây được tính lặp lại bằng các literal status inline, KHÔNG đồng nhất giữa các consumer:

| Consumer | Vị trí cũ | Filter cũ | Lỗi |
|---|---|---|---|
| KPI thẻ `cm_open` | `api/dashboard.py:87` | `NOT IN [Completed, Closed, Cancelled]` | Đếm cả `Cannot Repair` là mở (sai); có phantom `Closed` |
| Drill-down list | `api/dashboard.py:386` | `NOT IN [Completed, Closed, Cancelled, Cannot Repair]` | Loại `Cannot Repair`; có phantom `Closed` |
| Technician `my_cm` | `api/dashboard.py:562` | `NOT IN [Completed, Closed, Cancelled]` | Đếm `Cannot Repair`; phantom `Closed` |
| Technician `cm_urgent` | `api/dashboard.py:569` | `NOT IN [Completed, Closed, Cancelled]` | Đếm `Cannot Repair`; phantom `Closed` |
| SLA engine | `services/notifications.py:813` `_REPAIR_TERMINAL_STATUS` | `frozenset{Completed, Cannot Repair, Cancelled}` | Đúng tập, nhưng là frozenset **độc lập** (2 SoT song song) |

Hậu quả: số trên thẻ "CM đang mở" **≠** số dòng list khi click drill-down (card đếm `Cannot Repair`, list không) → mất niềm tin dashboard. `Closed` là **literal ma** — KHÔNG có trong DocType enum (chỉ có `Open|Assigned|Diagnosing|Pending Parts|In Repair|Pending Inspection|Completed|Cannot Repair|Cancelled`).

**Quyết định (Core Doc là quyết định cuối):** "Asset Repair đang mở" được định nghĩa bởi **một predicate thuần DUY NHẤT** trong `services/imm09.py`. Mọi consumer (KPI thẻ, persona KTV, drill-down SQL, SLA engine) PHẢI dùng chung tập terminal này.

```python
# assetcore/services/imm09.py
REPAIR_TERMINAL_STATES: frozenset[str] = frozenset({
    RepairStatus.COMPLETED,      # "Completed"
    RepairStatus.CANNOT_REPAIR,  # "Cannot Repair" — TERMINAL, KHÔNG phải đang mở
    RepairStatus.CANCELLED,      # "Cancelled"
})
# KHÔNG còn 'Closed' — literal ma, KHÔNG có trong Asset Repair.status enum.

def is_repair_open(status: str | None) -> bool:
    """SoT: một Asset Repair là 'đang mở' ⟺ status KHÔNG thuộc terminal set.
    None / rỗng (WO mới chưa set status) → coi là đang mở (an toàn — chưa đóng).
    """
    if not status:
        return True
    return status not in REPAIR_TERMINAL_STATES

def open_repair_filter(extra: dict | None = None) -> dict:
    """Trả filter Frappe cho 'Asset Repair đang mở' — dùng chung cho mọi
    _count / get_all / frappe.db filter. Merge thêm điều kiện qua `extra`.
    `sorted()` để filter shape DETERMINISTIC + khớp drill SQL byte-for-byte.
    """
    return {"status": ["not in", sorted(REPAIR_TERMINAL_STATES)], **(extra or {})}
```

**INVARIANT card == drill (BR-09-08):** `cm_open` (KPI thẻ) và drill-down repair SQL PHẢI đếm CÙNG tập WO. Số trên thẻ "CM đang mở" == số dòng list khi user click. Acceptance đo được: với 1 Asset Repair ở status `Cannot Repair` → KHÔNG tính vào `cm_open` VÀ KHÔNG xuất hiện trong `repair_rows`.

**`Cannot Repair` = TERMINAL ở MỌI consumer:** KPI `cm_open`, persona KTV `my_cm` + `cm_urgent`, drill SQL — tất cả loại `Cannot Repair` (khớp SLA engine: đồng hồ SLA dừng khi WO không còn cứu được). Đây là quy ước domain: thiết bị không sửa được → chuyển `Out of Service` (xem `_mark_cannot_repair`), KHÔNG còn là việc-đang-làm của KTV.

**Một SoT, không hai frozenset:** `notifications.py::_REPAIR_TERMINAL_STATUS` PHẢI trỏ về `imm09.REPAIR_TERMINAL_STATES` (alias import), KHÔNG định nghĩa frozenset song song. Quan hệ với `RepairStatus.CANNOT_START` (cùng 3 phần tử): `CANNOT_START` mô tả "không thể bắt đầu sửa từ trạng thái này" (validate khi tạo/assign); `REPAIR_TERMINAL_STATES` mô tả "đã đóng — không còn đang mở" (đếm/filter). Cùng giá trị, khác ngữ nghĩa — giữ tách tên để đọc rõ intent; có thể để `CANNOT_START = tuple(REPAIR_TERMINAL_STATES)` nếu muốn 1 nguồn literal.

**Grep guard (zero-tolerance):** sau fix, `api/dashboard.py` KHÔNG còn literal inline `['Completed','Closed','Cancelled']` hoặc `['Completed','Closed','Cancelled','Cannot Repair']` cho Asset Repair; literal `'Closed'` bị xoá khỏi MỌI Asset Repair status filter.

### State-machine-guarded asset restore (BR-09-09, Self-Correction)

**Vấn đề thiết kế gốc:** `complete_repair` (`services/imm09.py`) gọi `transition_asset_status(to_status=AssetStatus.ACTIVE)` **VÔ ĐIỀU KIỆN**, giả định asset luôn ở `Under Repair` khi WO đóng. Thực tế `lifecycle_status` của AC Asset do **nhiều process** quản:
- IMM-11 calibration-fail → `Out of Service` + CAPA (IMM-16);
- IMM-12 incident → `Out of Service`;
- IMM-13/14 decommission → `Decommissioned` (terminal).

Một thiết bị có thể đang mở 1 CM **đồng thời** bị 1 governance hold khác đẩy sang `Out of Service`/`Decommissioned`. Khi CM đóng, transition vô-điều-kiện phục vụ sai ≥2 ngữ cảnh lifecycle → **2 hậu quả an toàn**:

1. **Override governance hold (NĐ98):** asset đang `Out of Service` do calib-fail/CAPA bị ép về `Active` → thiết bị **out-of-tolerance tự lọt lại lâm sàng** (vi phạm an toàn NĐ98). Việc đóng phiếu CM (sửa phần cứng) KHÔNG đồng nghĩa giải toả hold hiệu chuẩn/CAPA — hold đó phải được giải riêng.
2. **Vỡ on_submit (terminal):** asset đã `Decommissioned` → `_VALID_ASSET_TRANSITIONS['Decommissioned'] == set()` (terminal) → ép `Active` raise `InvalidAssetTransition` → `on_submit` của controller VỠ → **WO un-closeable** (treo vĩnh viễn).

**FIX — đọc `prev_status` TRƯỚC, 3 nhánh (KHÔNG override, KHÔNG raise):**

| `prev_status` | Hành động | Lý do |
|---|---|---|
| `Under Repair` | `transition_asset_status(→ Active)` | Restore hợp lệ — đây là ngữ cảnh đúng của CM. |
| `Out of Service` (hoặc bất kỳ prev khác `Under Repair`/`Decommissioned`) | GIỮ nguyên; ghi ALE `repair_completed` (from=to) + note "WO đóng nhưng asset giữ `<prev>` do hold khác — cần giải toả riêng" | An toàn NĐ98: không override governance hold. |
| `Decommissioned` | Bỏ qua restore (terminal); ghi ALE `repair_completed` (from=to) + note "asset đã thanh lý" | Không raise → WO vẫn đóng được. |

**INVARIANT INV-09-RESTORE-1 (đo được):** sau `complete_repair`, `lifecycle_status` mới ∈ { `Active` **CHỈ KHI** `prev_status == 'Under Repair'`; `prev_status` giữ nguyên với MỌI prev khác } — và nhánh restore **KHÔNG BAO GIỜ raise**. WO luôn đóng được (status=`Completed`, docstatus=1) bất kể lifecycle_status của asset.

**Bất biến phụ:**
- **Lifecycle Event LUÔN ghi** (cả 3 nhánh) — audit trail đầy đủ, không nuốt record (CLAUDE.md §5).
- **Grep guard (zero-tolerance):** trong `complete_repair` KHÔNG còn `transition_asset_status(..., to_status=AssetStatus.ACTIVE)` không-điều-kiện — call này PHẢI nằm trong nhánh `if prev_status == AssetStatus.UNDER_REPAIR`.
- **No-regression:** path MTTR (`mttr_hours`), SLA (`sla_breached` OR-latch BR-09-07), `RepairRepo.set_values` (status/mttr/sla), và hook `create_post_repair_calibration` (BR-11 recalibration) GIỮ NGUYÊN 100%. Chỉ thay đổi DUY NHẤT khối transition_asset_status.

### Error handling pattern

```python
from assetcore.services.shared.constants import ErrorCode
from assetcore.services.shared.errors import ServiceError

def validate_repair_source(doc) -> None:
    """BR-09-01: WO phải có ít nhất 1 nguồn."""
    if not doc.incident_report and not doc.source_pm_wo:
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            frappe._("Phải có nguồn sửa chữa: Incident Report hoặc PM Work Order gốc")
        )

def validate_spare_parts_stock_entries(doc) -> None:
    """BR-09-02: mọi spare part phải có stock_entry_ref tồn tại."""
    for row in doc.spare_parts_used:
        if not row.stock_entry_ref:
            raise ServiceError(
                ErrorCode.VALIDATION,
                frappe._(f"Vật tư '{row.item_code}' (dòng {row.idx}) thiếu phiếu xuất kho")
            )
        if not frappe.db.exists("Stock Entry", row.stock_entry_ref):
            raise ServiceError(
                ErrorCode.VALIDATION,
                frappe._(f"Phiếu xuất kho '{row.stock_entry_ref}' không tồn tại trong hệ thống")
            )

def complete_repair(doc) -> None:
    """on_submit: tính MTTR, SLA breach, restore Asset (guarded), sinh ALE."""
    close_dt = now_datetime()
    doc.completion_datetime = close_dt
    diff_seconds = time_diff_in_seconds(close_dt, doc.open_datetime)
    doc.mttr_hours = round(diff_seconds / 3600.0, 2)
    # BR-09-07: SoT predicate (boundary >=) + monotonic — không reset 1→0 nếu
    # scheduler đã đánh breach lúc WO còn đang chạy. KHÔNG đổi (giữ 100%).
    doc.sla_breached = 1 if (is_sla_breached(doc.mttr_hours, doc.sla_target_hours)
                             or doc.sla_breached) else 0
    doc.status = RepairStatus.COMPLETED
    # … (RepairRepo.set_values status/mttr/sla giữ nguyên) …

    # ─── BR-09-09: restore Asset CÓ ĐIỀU KIỆN theo state machine ──────────────
    # ROOT CAUSE (Self-Correction): bản trước gọi transition_asset_status(
    #   to_status=ACTIVE) VÔ ĐIỀU KIỆN, giả định asset luôn ở Under Repair.
    #   Thực tế lifecycle_status do NHIỀU process quản (calib-fail→OoS+CAPA,
    #   incident, decommission) → 1 transition phục vụ sai ≥2 ngữ cảnh.
    # FIX: đọc prev_status TRƯỚC; chỉ Active khi đang Under Repair; mọi nhánh
    #   GHI 1 Lifecycle Event 'repair_completed' (audit đầy đủ, CLAUDE.md §5);
    #   nhánh restore KHÔNG BAO GIỜ raise (INV-09-RESTORE-1) → on_submit không vỡ.
    prev_status = frappe.db.get_value("AC Asset", doc.asset_ref, "lifecycle_status") or ""
    note = f"MTTR: {doc.mttr_hours}h | SLA: {'Breached' if doc.sla_breached else 'OK'}"

    if prev_status == AssetStatus.UNDER_REPAIR:
        # Nhánh A — restore bình thường: WO đóng đưa thiết bị về vận hành.
        transition_asset_status(
            asset_name=doc.asset_ref, to_status=AssetStatus.ACTIVE,
            actor=frappe.session.user,
            root_doctype=RepairRepo.DOCTYPE, root_record=doc.name,
            reason=note,
        )  # transition_asset_status TỰ ghi ALE 'activated' (from=Under Repair)
    elif prev_status == AssetStatus.DECOMMISSIONED:
        # Nhánh C — terminal: ép Active sẽ raise InvalidAssetTransition (set rỗng)
        # → on_submit VỠ, WO un-closeable. Bỏ qua restore; vẫn ghi ALE để audit.
        _log_lifecycle_event(
            asset=doc.asset_ref, event_type="repair_completed",
            from_status=prev_status, to_status=prev_status, root_record=doc.name,
            notes=f"{note} — asset đã thanh lý (Decommissioned), bỏ qua restore.",
        )
    else:
        # Nhánh B — hold governance khác (Out of Service do calib-fail/CAPA/
        # incident, hoặc bất kỳ prev khác Under Repair). KHÔNG ép Active: thiết bị
        # out-of-tolerance KHÔNG được tự lọt lại lâm sàng (NĐ98 — an toàn).
        _log_lifecycle_event(
            asset=doc.asset_ref, event_type="repair_completed",
            from_status=prev_status, to_status=prev_status, root_record=doc.name,
            notes=f"{note} — WO đóng nhưng asset giữ '{prev_status}' do hold khác; "
                  f"cần giải toả riêng.",
        )
```

> **CHỈ thay đổi DUY NHẤT khối transition.** Path MTTR/`sla_breached`/`RepairRepo.set_values`
> /`status=Completed` và hook `create_post_repair_calibration` GIỮ NGUYÊN 100%.

### Repeat failure detection

```python
def check_repeat_failure(doc) -> None:
    """BR-09-06: kiểm tra WO Completed trong 30 ngày."""
    cutoff = add_days(nowdate(), -30)
    exists = frappe.db.exists("Asset Repair", {
        "asset_ref": doc.asset_ref,
        "status": "Completed",
        "completion_datetime": (">=", cutoff),
        "docstatus": 1,
    })
    doc.is_repeat_failure = 1 if exists else 0
```

---

## 4b. Repository Layer

Module IMM-09 sử dụng Frappe ORM trực tiếp trong service (wave-1). Các DB access chính:

```python
# List WOs với filter
rows = frappe.get_all(
    "Asset Repair",
    filters=filters,
    fields=["name", "asset_ref", "priority", "status", "mttr_hours", "sla_breached"],
    limit_start=offset,
    limit_page_length=page_size,
    order_by="open_datetime desc"
)
total = frappe.db.count("Asset Repair", filters=filters)

# Get detail với enrichment
doc = frappe.get_doc("Asset Repair", name)
asset_info = frappe.get_value("Asset", doc.asset_ref,
    ["asset_name", "status", "custom_risk_class", "custom_mttr_avg_hours"],
    as_dict=True)
```

---

## 5. API Layer

File: `assetcore/api/imm09.py`

```python
import frappe
from assetcore.utils.helpers import _handle, _ok, _err, _parse_json
from assetcore.services import imm09 as service

@frappe.whitelist(methods=["POST"])
def create_repair_work_order(
    asset_ref: str,
    repair_type: str,
    priority: str,
    failure_description: str = "",
    incident_report: str = "",
    source_pm_wo: str = ""
) -> dict:
    return _handle(service.create_repair_work_order,
                   asset_ref, repair_type, priority,
                   failure_description, incident_report, source_pm_wo)

@frappe.whitelist()
def list_repair_work_orders(filters: str = "{}", page: int = 1, page_size: int = 20) -> dict:
    parsed = _parse_json(filters, field_name="filters", default={})
    return _handle(service.list_repair_work_orders, parsed, int(page), int(page_size))

@frappe.whitelist(methods=["POST"])
def close_work_order(
    name: str,
    repair_summary: str = "",
    root_cause_category: str = "",
    dept_head_name: str = "",
    checklist_results: str = "[]",
    spare_parts: str = "[]",
    firmware_updated: int = 0,
    firmware_change_request: str = "",
    cannot_repair: int = 0,
    cannot_repair_reason: str = ""
) -> dict:
    results = _parse_json(checklist_results, "checklist_results", [])
    parts = _parse_json(spare_parts, "spare_parts", [])
    return _handle(service.close_work_order,
                   name, repair_summary, root_cause_category, dept_head_name,
                   results, parts, bool(firmware_updated), firmware_change_request,
                   bool(cannot_repair), cannot_repair_reason)
```

**Helper `_handle`:**

```python
def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "IMM-09 API Error")
        return _err("Lỗi hệ thống. Vui lòng thử lại.", "INTERNAL")
```

---

**ADR-IMM09-CLOSE-PARITY — `close_work_order` 2 nhánh return CÙNG key-set (superset 5-khoá gồm `asset_status`); OAS khai `asset_status` bịt `additionalProperties:false` (CR-13b, mobile Trục B)**

- **Status**: Accepted
- **Date**: 2026-07-10
- **Context**: `close_work_order` có 2 nhánh return khác key-set: happy (`services/imm09.py:1575`) trả `{name, status, mttr_hours, sla_breached}`; `_mark_cannot_repair` (`services/imm09.py:1634`) trả `{name, status, asset_status}`. (1) Hai nhánh **lệch key-set** → client mobile phải deserialize 2 shape khác nhau cho cùng 1 endpoint (dễ vỡ codegen Dart/Kotlin strict). (2) Nhánh cannot_repair emit `asset_status` **KHÔNG khai** trong OAS `CloseWorkOrderResponse` (schema đóng 4-khoá `{name,status,mttr_hours,sla_breached}`, `test_mobile_oas.py:_CLOSE_WORK_ORDER_DATA_KEYS`) ⇒ **vi phạm `additionalProperties:false`** của contract mobile — codegen/validator reject field lạ.
- **Decision**: chuẩn hoá **cùng key-set superset đúng 5 khoá** `{name, status, mttr_hours, sla_breached, asset_status}` cho CẢ 2 nhánh — INVARIANT `set(keys happy) == set(keys cannot_repair)`. Happy thêm `asset_status` = LIVE `lifecycle_status` (thường `Under Repair`); cannot_repair thêm `mttr_hours` + `sla_breached` (= `doc.*`, thường `null` — KHÔNG tính MTTR). `asset_status` đọc **SSoT LIVE** qua `frappe.db.get_value("AC Asset", doc.asset_ref, "lifecycle_status")` / `AssetRepo.get_value` (**KHÔNG hardcode** — cùng nguồn `complete_repair` `:732`; `lifecycle_status` do nhiều process quản, BR-09-09). OAS `CloseWorkOrderResponse` **khai thêm** property `asset_status` (`type:string`, `nullable:true`); `mttr_hours`/`sla_breached` giữ nullable; `required=[name,status]`. Đồng bộ hằng test `_CLOSE_WORK_ORDER_DATA_KEYS` (+`asset_status`) + example `api/openapi_overrides.py` `imm09.close_work_order` (`:955-975`).
- **Alternatives**:
  - *(A) Giữ 2 shape khác nhau, chỉ khai `asset_status` nullable*: bịt được vi phạm `additionalProperties` nhưng client vẫn phải xử lý key-set biến thiên → drift, không có INVARIANT test bảo vệ. Loại.
  - *(B) Bỏ `asset_status` khỏi cannot_repair cho khớp 4-khoá cũ*: mất thông tin trạng thái asset (client cần biết thiết bị đã Out of Service để cập nhật UI) → giảm giá trị nghiệp vụ. Loại.
  - *(C) Hardcode `asset_status="Under Repair"` cho happy*: sai SSoT — `lifecycle_status` có thể đã bị process khác đổi (calib-fail/decommission). Loại (mâu thuẫn BR-09-09).
- **Consequences**: contract mobile ổn định (1 shape, INVARIANT test giữ). BE thêm 1 field-read live per branch (khuyến nghị tail dùng chung dựng đủ 5 khoá, chỉ `status` khác — chống drift). Regression-safe: `name/status/mttr_hours/sla_breached` GIỮ nguyên giá trị; happy vẫn → Pending Inspection, cannot_repair vẫn → Out of Service. **KHÔNG đụng** `confirm_inspection`/`ConfirmInspectionResponse` (4-key, `status.enum=[Completed]`, C3-split RIÊNG). Suite `mobile_oas` + `oas_d*` phải XANH sau `api:gen dev`; `test_imm09` (159) + toàn bộ test đóng/cannot_repair/pending_inspection/confirm_inspection GIỮ XANH. Chi tiết field-by-field + example: `05 §3.8 "Response contract — parity shape"`.

---

## 6. Audit Trail

| Trigger | Event type | Actor | Payload |
|---|---|---|---|
| create_repair_work_order | `repair_opened` | Workshop Manager / System | asset, wo, priority, sla_target |
| submit_diagnosis | `diagnosis_submitted` | KTV HTM | diagnosis_notes, needs_parts, root_cause |
| **enter_parts_hold (vào Pending Parts)** | **`parts_hold_started`** | **KTV HTM** | **wo, parts_hold_started (mốc), lý do (kho hết hàng) — BR-09-10** |
| **exit_parts_hold (ra Pending Parts / chốt cuối)** | **`parts_hold_resumed`** | **KTV HTM / Kho** | **wo, khoảng hold vừa cộng (giờ), parts_hold_hours tích lũy — BR-09-10** |
| complete_repair (on_submit) | `repair_completed` | KTV HTM | mttr_hours (clock-stop), parts_hold_hours, sla_breached, prev_status→new_status |
| close_work_order(cannot_repair=1) | `cannot_repair` | KTV / Workshop Manager | cannot_repair_reason |
| **attach_repair_checklist_photo (BR-09-16)** | **`repair_checklist_photo_attached`** | **KTV / assignee** | `asset=wo.asset_ref`, `root_doctype='Asset Repair'`, `root_record=WO`, `notes="Đính ảnh mục #<idx>: <filename>"` — **HARD-REQ** (commit CÙNG File.insert + set_value; event throw→rollback; KHÔNG swallow) |

Tất cả ALE insert qua `_create_lifecycle_event(...)` trong `services/imm09.py`. Wrap trong `try/except` — ALE failure KHÔNG block main operation.

> **⚠️ NGOẠI LỆ hard-req (BR-09-16):** sự kiện `repair_checklist_photo_attached` là **bản ghi bằng chứng NĐ98**, KHÔNG được mất im lặng ⇒ **KHÔNG** dùng wrapper `_log_lifecycle_event` (try/except-**swallow**) như các ALE khác. Gọi `create_lifecycle_event(...)` (canonical, `utils/lifecycle.py`) **TRỰC TIẾP** trong transaction, TRƯỚC `frappe.db.commit()`. Nếu event throw → File.insert + `set_value` rollback (chưa commit) ⇒ không orphan File, không silent. Đối xứng imm12 `incident_photo_attached` (`services/imm12.py:911`) / imm08 `pm_checklist_photo_attached` (`services/imm08.py:887`). Vì asset KHÔNG đổi trạng thái khi đính ảnh → `from_status == to_status == asset.lifecycle_status` hiện tại.

> **⚡ Enum change (deploy — HARD-STOP USER, KHÔNG chặn test):** thêm option **`repair_checklist_photo_attached`** vào Select `event_type` của `Asset Lifecycle Event` (`assetcore/assetcore/doctype/asset_lifecycle_event/asset_lifecycle_event.json`) — nối tiếp `incident_photo_attached` (Vòng 1) + `pm_checklist_photo_attached` (Vòng 2). Ghi `event_type` ngoài Select sẽ bị nuốt/throw → BẮT BUỘC mở enum trước khi LIVE. Deploy: `bench --site miyano reload-doctype "Asset Lifecycle Event"` + `clear-cache`. Test seed event qua `create_lifecycle_event` (không phụ thuộc reload live). Xem **ADR-IMM09-PHOTO-02** (`05 §3.10`).

**`repair_completed` LUÔN được ghi đúng 1 ALE — cả 3 nhánh restore (BR-09-09):**

| Nhánh | `prev_status` | Asset sau khi đóng | from → to (ALE) | Ghi chú audit |
|---|---|---|---|---|
| A — restore | `Under Repair` | `Active` | Under Repair → Active | Restore bình thường (ALE `activated` do `transition_asset_status` sinh + `repair_completed` business) |
| B — hold | `Out of Service` (hoặc prev khác) | giữ nguyên `prev_status` | prev → prev (no-op) | "WO đóng nhưng asset giữ `<prev>` do hold khác; cần giải toả riêng" |
| C — terminal | `Decommissioned` | giữ `Decommissioned` | Decommissioned → Decommissioned | "asset đã thanh lý, bỏ qua restore" |

KHÔNG nhánh nào nuốt record (CLAUDE.md §5 "mọi nghiệp vụ phải có record"). Nhánh B/C dùng `_log_lifecycle_event` (from=to) thay vì `transition_asset_status` (vốn early-return khi prev==to và sẽ raise nếu cố ép Active từ terminal).

---

## 7. Background jobs / Scheduler

```python
# assetcore/hooks.py — kế hoạch (xem ghi chú dưới)
scheduler_events = {
    "hourly": ["assetcore.services.imm09.check_repair_sla_breach"],
    "daily":  ["assetcore.services.imm09.check_repair_overdue"],
    "monthly": ["assetcore.services.imm09.update_asset_mttr_avg"],
}
```

| Job | Tần suất | Mục đích | Trạng thái wire `hooks.py` |
|---|---|---|---|
| `check_repair_sla_breach` | Hourly | Mark `sla_breached=1` khi `is_sla_breached(elapsed, target)` (SoT predicate, boundary `>=`); publish realtime `cm_sla_breached` đến Kỹ thuật viên. Chỉ set khi đang 0 (idempotent). | ⚠ chưa wire (function tồn tại trong `services/imm09.py`) |
| `check_repair_overdue` | Daily 07:00 | Email Workshop Manager khi WO > 7 ngày chưa đóng | ⚠ chưa wire (function tồn tại trong `services/imm09.py:239`) |
| `update_asset_mttr_avg` | Monthly day 01 06:00 | Cập nhật `Asset.custom_mttr_avg_hours` (avg 12 WO gần nhất) | ⚠ chưa wire (function tồn tại trong `services/imm09.py:263`) |

> **Code-to-doc gap (2026-05-14):** 3 function trên đã hiện diện trong service nhưng **chưa được đăng ký** trong `assetcore/hooks.py::scheduler_events`. Cần thêm trong patch Wave 2 release.

---

## 8. Integration

**Module nội bộ:**
- IMM-08 → IMM-09: `services/imm08.py::_create_cm_wo_from_failure` (line 154) auto-insert `Asset Repair` với `source_pm_wo` khi PM `report_major_failure` hoặc Fail-Major.
- IMM-12 → IMM-09: User tạo WO từ Incident Report (`incident_report` field trong `create_work_order`).
- IMM-09 → IMM-11: Sau Completed, nếu `Device Model.requires_calibration=True` → trigger calibration WO (manual rule hiện tại).
- IMM-09 → IMM-12 CAPA: `is_repeat_failure=1` → FE gợi ý tạo CAPA.
- **IMM-09 ↔ IMM-15 (Pattern B lazy-import)**: `services/imm09.py::request_spare_parts` (line ~500) lazy-import `assetcore.services.imm15.create_allocation` và mở allocation Requested truy về kho. Lỗi không throw — chỉ log `frappe.log_error` để giữ flow chính chạy.
- **IMM-09 ↔ IMM-16 (Pattern C compliance gate)**: `Asset Repair.validate` gọi `assetcore.services.imm16.gate_wo_submit(doc, method=None)` — signature `(doc, method=None)` chứ KHÔNG phải `(asset_ref, wo_type="CM")`. Trên `on_submit` gọi `imm16.eval_imm08_09_realtime` để cập nhật scorecard. Cả hai wired trong `hooks.py::doc_events["Asset Repair"]`.

**Bên ngoài:**
- ERPNext Stock: validate `stock_entry_ref` tồn tại
- Frappe Email Queue: overdue daily notification
- Frappe Realtime (`frappe.publish_realtime`): SLA breach push đến KTV

---

## 9. Migration & Patch

| Patch | Path | Mục đích |
|---|---|---|
| v1 → v2 | `patches/v2_0/migrate_asset_repair.py` | Migrate từ ERPNext Asset Repair → DocType native (BACKLOG) |
| Working hours MTTR | `patches/v2_1/imm09_mttr_working_hours.py` | Chuyển sang `get_working_hours_between` |
| Backfill repeat failure | `patches/v2_0/backfill_is_repeat_failure.py` | DRAFT |

**ERPNext compat shims** (controller hiện có):
- `completion_date` property ↔ `completion_datetime`
- `company` fallback ↔ `frappe.defaults.get_global_default("company")`

---

## 10. Non-functional

**Concurrency:** Frappe `doc.modified` optimistic lock — 20 active WO đồng thời không conflict.

**Caching:** KPI report: Redis key `imm09:kpis:{year}-{month}` TTL 10 phút (recommended, chưa implement).

**Logging:**
```python
frappe.logger("imm09").info(f"Repair WO {wo_name} completed MTTR={mttr:.1f}h SLA={'BREACH' if breach else 'OK'}")
frappe.logger("imm09").warning(f"SLA breached: {wo_name} asset={asset_ref}")
```

**Known issue:** `ignore_permissions=True` và `doc.flags.ignore_links=True` dùng trong service để tránh break trong môi trường test. Production cần review và bật đầy đủ permission check.

---

## DoD — File 04 hoàn chỉnh

- [x] Quy ước ngôn ngữ BE: code tiếng Anh + error message tiếng Việt
- [x] 4 DocType nêu đầy đủ trường + naming + permissions
- [x] Quan hệ liên DocType ERD
- [x] State machine 9 states + transitions
- [x] Controller hooks delegate sang service
- [x] Mọi error raise qua `ServiceError(ErrorCode.X, "msg tiếng Việt")`
- [x] API layer dùng `_handle / _ok / _err`
- [x] SLA matrix documented
- [x] Audit trail (ALE) liệt kê đủ trigger
- [x] 3 background job đăng ký rõ
- [x] Integration nội bộ + ERPNext + realtime
- [x] Patch path cho migration
- [x] Known issues documented
