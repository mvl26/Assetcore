---
name: assetcore-be
description: >
  Phát triển backend AssetCore trên Frappe v15 — bao gồm 3-tier architecture (API → Service → Repository),
  DocType schema, Workflow state machine, controller hooks, validators, SLA, lifecycle events, KPI, và audit trail.
  Dùng khi user nói "viết BE", "thêm endpoint", "service IMM-xx", "controller", "validator nghiệp vụ",
  "tạo DocType mới", "thêm field", "thiết kế bảng", "child table", "tạo workflow", "thêm state",
  "approval flow", "transition cho IMM-XX", "docstatus", "workflow_state", "naming series",
  "audit trail", "lifecycle event", "build sequence cho module mới".
  Kích hoạt BẤT CỨ KHI NÀO user muốn thêm/sửa backend, data model, hoặc state machine.
---

# AssetCore Backend — Architecture, DocType & Workflow

## Overview

Skill này bao 3 lớp phát triển backend: **3-tier code** + **DocType schema** + **Workflow state machine**.
Mọi module IMM mới đều cần cả 3. Nguyên tắc cốt lõi: **API mỏng → Service giữ nghiệp vụ → Repository chạm DB**; mọi action đổi-state sinh audit; KHÔNG hardcode role/status.

## When to Use

- Thêm/sửa endpoint, service, validator nghiệp vụ, controller hook cho module IMM-XX.
- Tạo DocType mới / thêm field / child table / naming series / thiết kế bảng.
- Tạo hoặc sửa Workflow state machine (state, transition, approval flow, docstatus).
- Wire SLA, lifecycle event, audit trail, KPI, scheduler job.
- Build sequence cho module IMM mới (DocType → workflow → repo → service → api → test).
- **KHÔNG dùng khi**: chỉ đụng FE (→ `assetcore-fe`), chỉ viết/chạy test (→ `assetcore-test`),
  hoặc còn ở mức ý tưởng chưa chốt module (→ `assetcore-plan` / `assetcore-doc`).

## Process — build BE module IMM-XX theo 3-tier (DocType→repo→service→api→test)

Quy trình từng bước (spine — chi tiết ở mục dưới; giữ nguyên ranh giới §Kiến trúc 3-tier: API mỏng → Service nghiệp vụ → Repo chạm DB):
1. **Đọc Core Doc + Lessons Learned** — `docs/imm-XX/02+05`, chốt BR-XX-NN/tên endpoint; đọc LL-BE-1..63 trước khi viết → §Lessons Learned
2. **DocType schema** — folder + JSON template, naming series, status/timestamp `read_only+no_copy`, tra catalog tránh đoán tên → §DocType schema
3. **Workflow state machine + 3-list fixtures** — states/transitions, docstatus rule, update CẢ 3 list (Workflow + State + Action Master) cùng commit → §Workflow state machine
4. **Repository (Tier 3)** — `<Name>Repo(BaseRepository)`, DB chỉ qua repo, custom method khi cần raw SQL → §Tier 3 — Repository
5. **Service (Tier 2)** — Status class → validators → entrypoints; `require_role` đầu mutating, raise `nthrow(MSG.*)` → §Tier 2 — Service layer
6. **API (Tier 1) contract-first/Hyrum** — shared `handle`/`parse_json`, tên = spec, envelope chuẩn, boundary validate+cap → §Tier 1 — API layer
7. **Lifecycle & Audit trail** — mọi action đổi-state gọi `log_audit_event`/`transition_asset_status`, không insert trail trực tiếp → §Lifecycle & Audit trail (bắt buộc)
8. **Build sequence exact-path + fixtures** — đi lát mỏng dọc stack, export-fixtures + migrate, sync docs/`.ts`/openapi → §Build sequence module mới (exact file paths)
9. **Test TRƯỚC (TDD) + Verification** — `run-tests` xanh (paste output), `EXPECTED_WORKFLOWS` đếm từ JSON, đóng cổng → §Verification

---

## Kiến trúc 3-tier (bắt buộc)

```
┌─────────────────────────────────────────────────────────────┐
│  api/immXX.py     Tier 1 — thin HTTP wrapper (@whitelist)   │
│      ↓ calls                                                 │
│  services/immXX.py  Tier 2 — business rules, ServiceError   │
│      ↓ uses                                                  │
│  repositories/<name>_repo.py  Tier 3 — DB (BaseRepository)  │
│      ↓ persists                                              │
│  assetcore/doctype/<name>/  DocType + controller hooks       │
└─────────────────────────────────────────────────────────────┘
```

**Hard rules:**
- API: chỉ parse input + call service + format output. Không có business logic.
- Service: không touch HTTP/JSON/`@frappe.whitelist`. Raise `ServiceError`.
- Controller hooks: delegate 100% đến service functions. Không inline logic.
- Mọi state-changing action phải gọi `log_audit_event(...)` từ `assetcore.utils.lifecycle`.
- Shared constants từ `assetcore.services.shared` — không hardcode role/status strings.
- Không bao giờ `except: pass` — tối thiểu `frappe.log_error(...)`.

## Anti-patterns thực tế (từ Wave 1+2 cleanup — KHÔNG lặp lại)

1. **Shadow canonical function**: đừng bao giờ redefine `_create_lifecycle_event` hay `_log_audit` locally — luôn import từ `assetcore.utils.lifecycle`.
2. **Controller validate() thiếu wiring**: list TẤT CẢ service validators áp dụng; đảm bảo mỗi cái được gọi.
3. **Bypass audit chain**: không bao giờ insert `IMM Audit Trail` trực tiếp — dùng `log_audit_event(...)`.
4. **Flag-based selector không reset flag**: khi select records bằng boolean flag, phải reset flag sau khi xử lý.
5. **Controller import function không tồn tại**: trước khi commit, `grep -r "<fn>" services/` để verify.
6. **`doc_event` hook signature sai**: mọi function trong `hooks.py::doc_events` PHẢI có `(doc, method=None)`.
7. **Service function không wired vào `hooks.py::doc_events`**: gate/SLA function phải có cả service code + hooks entry trong cùng commit.
8. **API function name không khớp spec**: mở `docs/imm-XX/05_API_Specification.md` trước; copy tên chính xác.
9. **DocType field dùng trong service nhưng không có trong JSON**: sau khi viết service, grep `doc\.<field>` và verify từng field trong DocType JSON.
10. **`doc.save()` trên workflow-managed doc**: dùng `frappe.db.set_value(DOCTYPE, name, "workflow_state", state, update_modified=False)`.
11. **`_parse_json`/`_handle` định nghĩa lại per-file**: ĐÃ DEPRECATED. Dùng SHARED `from assetcore.utils.api_handler import handle, parse_json` — KHÔNG copy/viết lại block cục bộ. Xem [`references/notification-contract.md`](references/notification-contract.md) §5.
12. **Fixture wiring thiếu 1 trong 3 list**: mỗi workflow mới phải cập nhật CẢ 3 list trong `hooks.py` — Workflow + Workflow State + Workflow Action Master — trong cùng commit. Thiếu bất kỳ list nào → fresh-site fail.
13. **Event-driven feature hard-code state/role**: notification/escalation/SLA KHÔNG hard-code tập state hay giả định field role (`supervisor`…) tồn tại → silent no-op (feature chết, không lỗi, test giả định vẫn pass). Resolve động từ Workflow transitions + `has_column`. Xem LL-BE-30/31.
14. **Scheduler/background function không wire `scheduler_events`**: viết hàm scan/expiry/digest mà quên entry trong `hooks.py::scheduler_events` = dead code, chưa bao giờ chạy. Wire + `bench execute frappe.get_hooks` verify trong cùng commit. Xem LL-BE-32.
15. **"Chuông trống / không nhận thông báo" → vá engine ngay**: thường là DATA (actor tự gán cho chính mình → self-notify chặn đúng), KHÔNG phải bug. Chạy decision tree (count record → actor≠recipient? → test `_dispatch` → FE query đúng `api/layout` không) TRƯỚC khi đụng code. Xem LL-BE-34.
16. **List endpoint count≠rows / page_size không cap**: triệu chứng = persona row-scoped thấy `pagination.total` 1430 nhưng chỉ drill được ít row → nguyên nhân `frappe.db.count`/`get_all` BỎ `permission_query_conditions` còn rows áp query persona. RULE kiểm-được: (a) `pagination.total` qua `count_with_or`/`len(get_list(limit_page_length=0))` DƯỚI session user — KHÔNG `frappe.db.count`/`get_all`; (b) `page_size = max(1, min(int(page_size), 100))` cap 2 đầu MỌI list endpoint; (c) probe dưới persona row-scoped assert `total==len(items)`. Xem LL-BE-42/43/47; `api/imm15.py:62`, `api/inventory.py:36`.
17. **Error envelope leak raw exc / branch theo status-line / mutating thiếu cap-gate**: triệu chứng = client thấy traceback nội bộ, hoặc `{ref}` lộ record hiện hữu trên lỗi dup, hoặc @whitelist mutating gate bằng role-name không tồn tại (silent bypass). RULE kiểm-được: (a) catch-all `except Exception` → `log_error(get_traceback())` + message HẰNG, KHÔNG `_err(str(e))` (leak nội bộ); (b) lỗi nghiệp vụ 404/409/422 trả TRÊN HTTP-200 → client/test branch theo `envelope.http_status`/`code`, KHÔNG HTTP status-line; phân biệt dispatcher-403 (re-auth) vs in-handler cap-403 (show-message); (c) mọi mutating @whitelist có `rbac.require`/`has_any_role` capability-SSoT đầu body, KHÔNG gate role-name; (d) message dup-định-danh KHÔNG leak record hiện hữu. Xem LL-BE-44/45/46/49; `references/notification-contract.md`.

18. **Field "chọn người" lấy nguồn sai / không qua context allowlist**: triệu chứng = picker phân công/mô-tả-người kéo TOÀN BỘ Frappe user (FE `SmartSelect doctype="User"` hoặc endpoint trả `frappe.get_all("User")` thô) → lộ user ngoài hệ thống + user chọn người mà BE sẽ từ chối. RULE: mọi danh sách người PHẢI qua `api/user.py::list_assignable_users(context,...)` — nguồn = base-role holder ("user AssetCore" = giữ `AssetCore System User`, trừ Admin/Guest). `context="user"` = mọi holder (field mô-tả-người: giám sát/thủ kho/trưởng khoa/leo thang SLA); context capability trong `_ASSIGNABLE_CONTEXTS` = lọc thêm `frappe.has_permission(doctype, ptype)` (mirror `_is_repair_capable`, KHÔNG so role-name). Thêm field người mới = thêm 1 entry vào `_ASSIGNABLE_CONTEXTS` (allowlist nhận TÊN context, KHÔNG nhận doctype thô từ client → anti-probe), context lạ → 400. Xem memory `user-source-base-role-pattern`; skill `assetcore-fe` Display rules + GATE-7.

---

## Tier 1 — API layer

> 🔔 **Notification contract BẮT BUỘC** — đọc [`references/notification-contract.md`](references/notification-contract.md) TRƯỚC khi viết api/service/view. Mọi message qua `MSG.*` + envelope chuẩn (`message_code`+`severity`). KHÔNG raw `frappe.throw(_())` / `ServiceError(..., "literal")`.

### Pattern A (CANONICAL) — shared `handle` + `parse_json`
Service raise qua `nthrow(MSG.*)`; api chỉ wrap:
```python
from assetcore.utils.api_handler import handle, parse_json

@frappe.whitelist()
def list_things(filters: str = "", page: int = 1, page_size: int = 20):
    return handle(svc.list_things, parse_json(filters, default={}),
                  page=int(page), page_size=int(page_size))

@frappe.whitelist(methods=["POST"])
def do_action(name: str, payload: str = ""):
    return handle(svc.do_action, name, payload=parse_json(payload, default={}))
```
- KHÔNG định nghĩa `_handle`/`_parse_json`/`_err` cục bộ (deprecated).
- GET optional JSON param default `str = ""` (KHÔNG `"{}"`) → tránh HTTP 417 (LL-BE-1).
- `handle` auto-hydrate `action_hint`/`severity`/`title` từ registry khi ServiceError mang `message_code`.

### Pattern B — `@api_endpoint` decorator (khi service dùng `frappe.throw`)
```python
from assetcore.utils.api_endpoint import api_endpoint
from assetcore.utils.response import _ok

@frappe.whitelist()
@api_endpoint
def get_thing(name: str) -> dict:
    doc = frappe.get_doc("AC Asset", name)
    return _ok(doc.as_dict())
```

### Interface design — named principles (API là HỢP ĐỒNG)

> Whitelist signature + envelope field + naming = **hợp đồng với FE (`frontend/src/api/immXX.ts`) và mobile (`assetcore-mobile.openapi.yaml`)**. Áp dụng khi thiết kế/sửa BẤT KỲ @whitelist nào.

| Principle | Nghĩa cho AssetCore | Ví dụ Frappe |
|---|---|---|
| **Contract-first** | Khai shape (param + envelope `data`) khớp `05_API_Specification.md` + type FE/OpenAPI TRƯỚC khi viết service. Type FE/OpenAPI = spec, code follow. | Đổi `wo_name` → `repair_name` trong response = phải sync `.ts` + `.openapi.yaml` cùng commit. |
| **Hyrum's Law** | Mọi field/behavior observable (tên field, thứ tự list, text lỗi, default page_size) sẽ bị FE/mobile dựa vào → đổi = **breaking** dù spec không hứa. Đừng leak field nội bộ (`workflow_state` plumbing, `_internal_*`). | Rename `assigned_to`→`technician` lặng lẽ = vỡ FE binding + mobile codegen. Field thừa trong `as_dict()` cũng thành commitment. |
| **One-Version Rule** | KHÔNG fork `list_things_v2`/`do_action_old`. Extend bằng param/field optional, giữ 1 endpoint. Nhiều version = diamond-dep cho FE + mobile. | Thêm `include_history: bool = False` thay vì `get_repair_v2`. |
| **Error semantics ổn định** | Mã lỗi = `message_code` (`MSG.*`) + `code`/`http_status` HẰNG trong envelope — client branch theo mã, KHÔNG theo text/HTTP status-line (lỗi nghiệp vụ 404/409/422 đến TRÊN HTTP-200, xem anti-pattern #17). Đổi text OK, đổi mã = breaking. | `nthrow(MSG.IMMXX_NOT_FOUND)` → `code="NOT_FOUND"` ổn định; FE switch theo `error.message_code`. |
| **Boundary validation** | Validate + cast + `parse_json` ở ranh giới API/controller (input ngoài) TRƯỚC khi vào service; service tin type đã sạch, KHÔNG re-validate giữa các hàm nội bộ. | `page_size = max(1, min(int(page_size), 100))` + `parse_json(filters, default={})` ở Tier-1; service nhận dict đã chuẩn. |

**Conventions:**
- Mutating endpoints khai báo `methods=["POST"]`.
- Cast scalar params: `int(page)`, `bool(flag)`.
- JSON params dùng `parse_json(raw, default=...)` (shared, từ `utils/api_handler`).
- Envelope chuẩn: `{success, data}` hoặc `{success:false, error, code, http_status, message_code, severity, title, action_hint, context}` — notification fields auto-hydrate khi raise qua `nthrow(MSG.*)`.

---

## Tier 2 — Service layer

```python
# services/immXX.py
from assetcore.services.shared import AssetStatus, ErrorCode, ServiceError, Roles
from assetcore.services.shared.permissions import require_role
from assetcore.repositories.<name>_repo import <Name>Repo

class XStatus:
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

def validate_X_source(doc) -> None:
    """BR-XX-01: business rule. Gọi từ DocType hook → nthrow_in_hook."""
    if not doc.source_a and not doc.source_b:
        nthrow_in_hook(MSG.IMMXX_SOURCE_REQUIRED)

def create_thing(*, asset_ref: str, **kwargs) -> dict:
    require_role(Roles.CAN_CREATE_WO, "Không đủ quyền")
    if not repo.exists(asset_ref):
        nthrow(MSG.IMMXX_NOT_FOUND, asset=asset_ref)   # service entrypoint → nthrow
    doc = frappe.get_doc({"doctype": "<Name>", "asset_ref": asset_ref, **kwargs})
    doc.insert()
    return {"name": doc.name}
```

**Conventions (notification contract — xem [`references/notification-contract.md`](references/notification-contract.md)):**
- Business error trong service entrypoint → `nthrow(MSG.IMMXX_*, **ctx)` (`from assetcore.utils.notify import nthrow`).
- Raise trong DocType hook (validate/on_submit) → `nthrow_in_hook(MSG.IMMXX_*, **ctx)`.
- TUYỆT ĐỐI KHÔNG `frappe.throw(_("literal"))` / `ServiceError(ErrorCode.X, "literal")` — message luôn qua `MSG.*` trong registry.
- Không gọi `doc.save()` trên submitted doc — dùng `frappe.db.set_value`.
- Permission check ở **đầu** mọi mutating function.
- Status strings trong class cục bộ (`XStatus`) — không import cross-module.
- Real `ErrorCode`: `NOT_FOUND`, `FORBIDDEN`, `VALIDATION`, `BUSINESS_RULE`, `CONFLICT`, `BAD_STATE`, `DUPLICATE`, `INVALID_PARAMS`, `INTERNAL`.

---

## Tier 3 — Repository

```python
# repositories/<name>_repo.py
from .base import BaseRepository

class <Name>Repo(BaseRepository):
    DOCTYPE = "<DocType Name>"
```

`BaseRepository` cung cấp: `exists`, `get`, `get_value`, `count`, `list`, `find_one`, `create`, `update`, `delete`. Chỉ thêm custom method khi cần raw SQL. **Không** gọi `frappe.db.*` từ service — đi qua repo.

---

## DocType schema

> 🗺️ **Data model có 107 DocType — đọc [`references/doctype-catalog.md`](references/doctype-catalog.md) TRƯỚC khi thiết kế DocType mới / viết `Link` field / gọi `frappe.get_doc|get_all`.** Catalog cho **tên verbatim** + map domain để (1) KHÔNG đoán tên (`Department`≠`AC Department`, `Device Model`≠`IMM Device Model`) và (2) **tái dùng** DocType đã có thay vì tái phát minh (spare/stock/model). Đoán tên = bug LL-BE-10; tạo trùng domain = vi phạm CLAUDE.md §5/§19.

### Naming
| Prefix | Ý nghĩa | Ví dụ |
|---|---|---|
| `AC ` | Core entity (replaces ERPNext) | `AC Asset`, `AC Location` |
| `IMM ` | Governance / reference | `IMM SLA Policy`, `IMM Audit Trail` |
| (không) | Operational records | `Asset Repair`, `Incident Report` |

Folder = snake_case của tên: `AC Asset` → `assetcore/assetcore/doctype/ac_asset/`.

### Template JSON (required fields)
```json
{
  "name": "Asset Repair",
  "doctype": "DocType",
  "module": "AssetCore",
  "engine": "InnoDB",
  "is_submittable": 1,
  "track_changes": 1,
  "autoname": "format:WO-RP-{YYYY}-{####}",
  "title_field": "name",
  "search_fields": "asset_ref,assigned_to,status",
  "fields": [],
  "permissions": []
}
```

### Field patterns thường dùng
```json
// Link
{"fieldname":"asset_ref","fieldtype":"Link","options":"AC Asset","reqd":1,"in_list_view":1}

// Select (status — luôn read_only + no_copy)
{"fieldname":"status","fieldtype":"Select","options":"Open\nCompleted","read_only":1,"no_copy":1}

// Datetime (system-set — luôn read_only + no_copy)
{"fieldname":"open_datetime","fieldtype":"Datetime","read_only":1,"no_copy":1}

// Child table
{"fieldname":"spare_parts_used","fieldtype":"Table","options":"AC Spare Part Usage Row"}

// workflow_state (hidden plumbing)
{"fieldname":"workflow_state","fieldtype":"Link","options":"Workflow State","read_only":1,"hidden":1,"no_copy":1}
```

### DocType checklist
- [ ] `module: "AssetCore"` set
- [ ] `autoname` dùng prefix có ý nghĩa (`WO-PM-`, `CAL-`, `IR-`)
- [ ] `track_changes: 1`
- [ ] `is_submittable: 1` nếu có finalization step
- [ ] Status fields: `read_only: 1` + `no_copy: 1`
- [ ] Timestamp fields (open_datetime, close_datetime...): `read_only: 1` + `no_copy: 1`
- [ ] Audit trail DocType: `delete: 0` cho mọi role (kể cả SysAdmin)
- [ ] Link đến `AC Asset` nếu asset-related
- [ ] Permissions: SYS_ADMIN + ≥ 2 operational roles
- [ ] Controller hooks delegate 100% đến service layer

---

## Workflow state machine

### JSON structure
```json
{
  "name": "IMM-09 Repair Workflow",
  "workflow_name": "IMM-09 Repair Workflow",
  "document_type": "Asset Repair",
  "workflow_state_field": "workflow_state",
  "is_active": 1,
  "states": [
    {"state": "Open", "doc_status": "0", "allow_edit": "IMM Workshop Lead", "type": "Warning"}
  ],
  "transitions": [
    {"state": "Open", "action": "Phân công KTV", "next_state": "Assigned", "allowed": "IMM Workshop Lead"}
  ]
}
```

**docstatus rule**: `0→0`, `0→1`, `1→1`, `1→2` là valid. `0→2`, `1→0`, `2→*` là INVALID.

**Type convention**: `Success` = progress states | `Warning` = waiting | `Danger` = terminal-bad.

### Fixtures — PHẢI update 3 list cùng lúc
```python
# hooks.py — khi thêm workflow mới, cập nhật CẢ 3 list:
{"dt": "Workflow", "filters": [["name", "in": ["IMM-09 Repair Workflow", "<new>"]]]},
{"dt": "Workflow State", "filters": [["name", "in": [/* tất cả state names */]]]},
{"dt": "Workflow Action Master", "filters": [["name", "in": [/* tất cả action labels */]]]},
```
Thiếu bất kỳ list nào → fresh-site provisioning fail.

### Thêm vào EXPECTED_WORKFLOWS
```python
# tests/test_workflows.py
"IMM-XX Workflow": {"doctype": "<DocType>", "min_states": N, "min_transitions": M},
```
**Bắt buộc đếm từ JSON**, không đoán:
```bash
python -c "import json; d=json.load(open('workflow.json')); print(len(d['states']), len(d['transitions']))"
```

### Sync với service enum
State strings trong workflow phải khớp hoàn toàn với `XStatus` class trong `services/immXX.py` VÀ type union trong `frontend/src/api/immXX.ts`.

---

## Lifecycle & Audit trail (bắt buộc)

```python
from assetcore.utils.lifecycle import log_audit_event
from assetcore.services.imm00 import transition_asset_status
from assetcore.services.shared import AssetStatus

# Chỉ ghi audit (không đổi asset status):
log_audit_event(
    asset=asset_ref, event_type="repair_completed",
    ref_doctype="Asset Repair", ref_name=wo_name,
    from_status=RepairStatus.IN_REPAIR, to_status=RepairStatus.COMPLETED,
    change_summary="WO closed; checklist 100% Pass",
)

# Đổi asset status + ghi audit cùng lúc:
transition_asset_status(asset_ref, AssetStatus.ACTIVE, root_record=wo_name)
```

**Không bao giờ** insert `IMM Audit Trail` trực tiếp — hash chain sẽ hỏng.

---

## Build sequence module mới (exact file paths)

> 🧱 **Incremental — thin vertical slice**: thay vì build trọn module 1 lượt, đi LÁT MỎNG dọc stack `DocType → repo → service → api → test` cho MỘT entrypoint (vd `create_repair`), chạy `run-tests` xanh, **commit nhỏ**, rồi mới sang entrypoint kế. Mỗi lát để hệ ở trạng thái build-được + test-được. **Safe default**: tham số/feature mới mặc định conservative (`notify=False`, flag tắt qua `site_config`). **Rollback-friendly**: ưu tiên thay đổi additive (file/field mới dễ revert); DocType/field deprecate qua Frappe patch riêng — KHÔNG xoá+thay trong cùng commit.
>
> 📚 **Source-driven**: mọi quyết định Frappe/ERPNext v15 (hook signature, `frappe.qb`, naming series, child-table API, permission API) phải **cite tài liệu chính thức** — tra qua **context7 MCP** (`resolve-library-id` → `query-docs` cho frappe/erpnext) thay vì viết từ trí nhớ; nếu không tìm được nguồn xác minh → **flag `UNVERIFIED`** ở comment/PR, đừng để pattern lỗi thời thành template.

1. **Đọc docs**: `docs/imm-XX/02_Analysis_Design.md` + `05_API_Specification.md` — xác nhận BR-XX-NN và tên endpoint.

2. **DocType schema**: tạo folder + 4 files:
   ```
   assetcore/assetcore/doctype/<snake_name>/
   ├── __init__.py
   ├── <snake_name>.json    # template từ SKILL section DocType
   ├── <snake_name>.py      # controller — chỉ delegate đến service
   └── <snake_name>.js      # optional JS hooks
   ```

3. **Workflow JSON**:
   ```
   assetcore/assetcore/workflow/imm_XX_<domain>_workflow.json
   ```
   Tên file convention: `imm_09_repair_workflow.json`, `imm_08_pm_workflow.json`.

4. **Repository**:
   ```
   assetcore/repositories/<snake_name>_repo.py
   ```
   Import từ `assetcore/repositories/__init__.py` (add entry nếu chưa có).

5. **Service**:
   ```
   assetcore/services/immXX.py
   ```
   Sequence: local Status class → validators → entrypoints (mỗi entrypoint có `require_role` đầu).

6. **API layer**:
   ```
   assetcore/api/immXX.py
   ```
   `from assetcore.utils.api_handler import handle, parse_json` (shared — KHÔNG copy cục bộ). Tên function = spec. Service raise qua `nthrow(MSG.*)`; xem [`references/notification-contract.md`](references/notification-contract.md).

7. **Tests**:
   ```
   assetcore/tests/test_immXX.py
   ```
   Update `assetcore/tests/test_workflows.py::EXPECTED_WORKFLOWS`.

8. **hooks.py — 3 list update**:
   ```python
   # assetcore/hooks.py — fixtures list
   # Thêm workflow name + tất cả states + tất cả actions
   ```

9. **Export fixtures**:
   ```bash
   bench --site miyano export-fixtures --app assetcore
   bench --site miyano migrate
   bench --site miyano run-tests --module assetcore.tests.test_immXX
   bench --site miyano run-tests --module assetcore.tests.test_workflows
   ```

10. **Update docs**: `docs/imm-XX/04_Backend_Design.md` + `05_API_Specification.md` trong cùng commit với code.

---

## Live examples

- `assetcore/api/imm09.py` + `assetcore/services/imm09.py` — complete Pattern A reference (shared `handle` + `nthrow`)
- `assetcore/utils/{notify,api_handler,messages}.py` — notification contract entrypoints
- `assetcore/api/dashboard.py` — Pattern B (`@api_endpoint`)
- `assetcore/services/shared/constants.py` — `Roles`, `ErrorCode`, `AssetStatus`
- `assetcore/repositories/base.py` — `BaseRepository` contract
- `assetcore/utils/lifecycle.py` — `log_audit_event` (SHA-256 chain)
- `assetcore/assetcore/workflow/imm_09_repair_workflow.json` — workflow template
- `assetcore/assetcore/doctype/asset_repair/` — DocType reference
- [`references/doctype-catalog.md`](references/doctype-catalog.md) — bản đồ 107 DocType (tên verbatim + domain map) — đọc trước khi Link/thiết kế

---

## Lessons Learned — bug patterns production (BẮT BUỘC ĐỌC)

> ⚠️ quy tắc **LL-BE-1..63** (always-apply, KHÔNG optional) đã chuyển sang
> [`references/lessons-learned.md`](references/lessons-learned.md) — whitelist GET param,
> enrich Link field, DocType schema sync, workflow action labels, gate validators,
> audit trail localize, fixture-leak, null-guard dangling FK, slug-in-display,
> state reachability, event-driven resolve động (KHÔNG hard-code state/role),
> Workflow State style/type không persist runtime, scheduler_events wiring,
> verify field type/enum + sendmail reference…
>
> **DONE-gate bổ sung:**
> - Feature in **PDF khổ cố định** (tem/nhãn/vé) → `pdfkit`-direct (KHÔNG `get_pdf`) + test assert MediaBox = đúng khổ mm & pypdf page-count (LL-BE-55); bọc binary-call no-500 (LL-BE-56).
> - Logic theo **enum rủi ro** → cite `field+doctype` nguồn, KHÔNG lẫn `risk_classification` (Low/Med/High/Critical) ↔ `risk_class` (NĐ98 A/B/C/D / Class I/II/III) (LL-BE-58).
>
> **BẮT BUỘC: `Read references/lessons-learned.md` TRƯỚC KHI viết/sửa service · API · DocType · workflow.**
> Bỏ qua = tái phạm bug đã biết.

---

## Common Rationalizations

| Lý do hay viện để skip | Sự thật |
|---|---|
| "Service nhỏ, viết logic thẳng trong api/ cho nhanh" | Vi phạm 3-tier; logic trong API không test được ở service-layer + bị bypass khi gọi từ hook. Luôn API→Service. |
| "Đặt tên endpoint theo trí nhớ, sửa sau" | Lệch `05_API_Specification.md` → FE gọi sai (anti-pattern #8 / LL-BE-10). Copy tên verbatim từ spec TRƯỚC. |
| "Tạo DocType mới cho nhanh, kệ catalog" | 107 DocType đã tồn tại; tạo trùng domain vi phạm §5/§19, đoán tên = LL-BE-10. Đọc `references/doctype-catalog.md`. |
| "Thêm workflow chỉ cần khai Workflow fixture" | Thiếu 1/3 list (Workflow State / Action Master) → fresh-site fail (anti-pattern #12). Update CẢ 3 cùng commit. |
| "Notification/SLA hard-code tập state cho gọn" | Hard-code state/role = silent no-op, test giả vẫn xanh (anti-pattern #13, LL-BE-30/31). Resolve động từ transitions + `has_column`. |
| "Bug 'chuông trống' → vá engine ngay" | Thường là DATA (self-notify), không phải bug. Chạy decision tree LL-BE-34 TRƯỚC khi đụng code. |
| "`except Exception: pass` cho đỡ noise" | Nuốt lỗi = mù production. Tối thiểu `frappe.log_error(get_traceback())` + message HẰNG (anti-pattern #17 / LL-BE-44). |
| "Viết hàm scan/digest xong là nó chạy" | Quên `scheduler_events` = dead code (anti-pattern #14, LL-BE-32). Wire + `bench execute frappe.get_hooks` verify. |
| "Rename field response cho gọn, FE sửa sau" | Hyrum's Law — FE/mobile đã dựa vào tên cũ → đổi = breaking. Sync `.ts`+`.openapi.yaml` cùng commit hoặc giữ tên. |
| "Thêm `do_action_v2` cho chắc, khỏi đụng cái cũ" | Vi phạm One-Version Rule → diamond-dep cho FE+mobile. Extend bằng param optional, 1 endpoint. |
| "Hook Frappe này mình nhớ signature rồi" | Trí nhớ ≠ bằng chứng, v15 đổi API. Tra context7 MCP + cite; không rõ → flag UNVERIFIED. |

## Red Flags — STOP

- Business logic nằm trong `api/` hoặc inline trong controller hook (phải ở service).
- `_handle`/`_parse_json`/`_err` định nghĩa cục bộ (deprecated — dùng shared `utils/api_handler`).
- `frappe.throw(_("literal"))` / `ServiceError(..., "literal string")` — message phải qua `MSG.*`.
- `doc.save()` trên submitted/workflow-managed doc (dùng `frappe.db.set_value`).
- Insert `IMM Audit Trail` trực tiếp (phải qua `log_audit_event` — hash chain).
- Field dùng trong service nhưng không có trong DocType JSON; function import nhưng không tồn tại.
- Hard-code role/status string; gate mutating endpoint bằng role-name thay vì capability SSoT.
- `list`/`count` endpoint: `frappe.db.count`/`get_all` (bỏ permission query) hoặc `page_size` không cap (LL-BE-42/43).
- Thêm workflow mà chỉ update 1/3 fixture list; thêm scheduler fn mà quên `scheduler_events`.
- Đổi tên/kiểu field response hoặc fork endpoint `*_v2` mà không sync FE `.ts` + `assetcore-mobile.openapi.yaml` (Hyrum's Law / One-Version).
- Client branch theo HTTP status-line hay text lỗi thay vì `message_code`/`code` (error semantics không ổn định).
- Viết hook/`frappe.qb`/permission API Frappe v15 từ trí nhớ, không cite docs (context7) và không flag UNVERIFIED.

## Verification

Trước khi khai báo BE "xong" — phải có BẰNG CHỨNG (không "có vẻ đúng"):
- [ ] `bench --site miyano run-tests --module assetcore.tests.test_immXX` xanh (paste output).
- [ ] `test_workflows` xanh; `EXPECTED_WORKFLOWS` state/transition count đếm từ JSON, không đoán.
- [ ] `grep doc\.<field> services/` ↔ DocType JSON khớp từng field; `grep -r "<imported_fn>" services/` tồn tại.
- [ ] Mọi mutating fn có permission/capability check ở đầu; mọi action đổi-state gọi `log_audit_event`.
- [ ] api dùng shared `handle`/`parse_json`; GET optional JSON param default `str = ""` (tránh 417).
- [ ] Contract-first: param + envelope field khớp `05_API_Specification.md` + FE `.ts` + `assetcore-mobile.openapi.yaml`; thay đổi field là additive/optional (Hyrum's Law); không fork `*_v2` (One-Version); validate+cap+`parse_json` ở boundary.
- [ ] Slice nhỏ: từng entrypoint test xanh + commit riêng; param/feature mới safe-default; quyết định Frappe v15 đã cite (context7) hoặc flag UNVERIFIED.
- [ ] Workflow fixtures: cập nhật CẢ 3 list (Workflow + State + Action Master) trong cùng commit.
- [ ] Scheduler/event fn đã wire `hooks.py` (`scheduler_events`/`doc_events`) — verify `bench execute frappe.get_hooks`.
- [ ] Đã đọc `references/lessons-learned.md` (LL-BE-1..63) trước khi viết — không tái phạm.

---

## 🔗 Session context — bàn giao phiên (assetcore-session)

- **Trước khi xử lý/sửa BẤT KỲ việc gì:** chạy `.claude/scripts/session-log.sh show` (đọc STATE + file phiên mới nhất (curated; cần truy gốc chi tiết → đọc mục 🪞 Mirror của file phiên) — "đang dở ở đâu"; dữ liệu trong `.claude/contexts/` — gitignored; file phiên ở `sessions/<ngày>/`). Main session: hook tự nạp mỗi prompt + tự **mirror TOÀN BỘ lượt** (prompt+phản hồi+tool) vào file phiên qua hook `Stop`; subagent phải TỰ chạy lệnh này.
- **Sau MỖI việc đáng kể (đụng file/quyết định):** invoke **`assetcore-session`** checkpoint NGAY: `STATE.md`(ghi đè) + bồi **semantic** vào file phiên (`session-log.sh current` → path; **KHÔNG còn LOG.md**). Hook `Stop` đã mirror nguyên văn → bạn CHỈ cần tóm Làm/Quyết-định/Để-lại. KHÔNG đợi cuối phiên (ngắt giữa chừng = mất).
- **Ranh giới:** state-tạm-sẽ-hết → `.claude/contexts/` (STATE.md + sessions/<ngày>/); fact-bền-vững-dùng-lại → `memory/`. KHÔNG trộn.
