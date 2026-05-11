---
name: assetcore-be-module
description: Build or extend an AssetCore backend IMM module on Frappe v15 using the project's strict 3-tier architecture (API → Service → Repository) plus DocType controllers. Use this whenever the user asks to add an endpoint, business rule, validator, SLA logic, status transition, lifecycle event, KPI, or any backend feature for any IMM-XX module — even when they only say "add backend logic for repair", "viết API cho IMM-09", "thêm validator", "tạo work order endpoint", or "wire a service into the controller". Triggers on Vietnamese phrases like "viết BE", "thêm endpoint", "service IMM-xx", "controller", "validator nghiệp vụ".
---

# AssetCore Backend Module Builder

You are extending a Frappe v15 (Python) backend that follows a **mandatory 3-tier architecture**. The system manages medical equipment lifecycle (HTM) and every business action must produce an auditable record.

## Mental model — read this first

```
┌─────────────────────────────────────────────────────────────────┐
│  api/immXX.py    Tier 1 — thin HTTP wrappers (@frappe.whitelist)│
│      ↓ calls                                                    │
│  services/immXX.py  Tier 2 — business rules, raise ServiceError │
│      ↓ uses                                                     │
│  repositories/*_repo.py  Tier 3 — DB access (BaseRepository)    │
│      ↓ persists                                                 │
│  assetcore/doctype/<name>/  DocType + controller hooks          │
└─────────────────────────────────────────────────────────────────┘
```

**Hard rules:**
- API layer must NOT contain business logic. It only parses input, calls service, formats output.
- Service layer must NOT touch HTTP, JSON, or `frappe.whitelist`. It raises `ServiceError`.
- DocType controller hooks (`before_insert`, `validate`, etc.) delegate to service functions — never inline rules.
- Every state-changing action on an asset must call `log_audit_event(...)` from `assetcore.utils.lifecycle` (writes a SHA-256-chained `IMM Audit Trail` row). Don't hand-build audit rows. Don't define a local `_create_lifecycle_event` in a module — use the canonical one from `assetcore.utils.lifecycle`.
- Use the shared constants from `assetcore.services.shared` (Roles, ErrorCode, AssetStatus, ApprovalStatus, CalibrationStatus, CalibrationResult). Never hardcode role names or status strings.
- Never use bare `except: pass` or `except Exception: pass` — always at minimum `frappe.log_error(...)`. Silently swallowing exceptions hides data corruption.
- Note: there are **two** `ErrorCode` classes in the repo. Service layer uses the one re-exported by `assetcore.services.shared` (the canonical one — `VALIDATION`, `BUSINESS_RULE`, `BAD_STATE`, `INVALID_PARAMS`, `INTERNAL`, etc. — see `services/shared/constants.py:213`). The legacy one in `utils/response.py` (`VALIDATION_ERROR`, `BUSINESS_RULE_VIOLATION`, `INTERNAL_ERROR`) is kept only for backwards compatibility with older `_err()` callers. Always import from `assetcore.services.shared`.

## Directory layout (where files go)

```
assetcore/
├── api/immXX.py              # whitelist endpoints
├── services/immXX.py         # business logic
├── services/shared/          # constants, errors, permissions
├── repositories/<name>_repo.py
├── assetcore/doctype/<doctype>/<doctype>.py   # controller
├── assetcore/doctype/<doctype>/<doctype>.json # schema
├── assetcore/workflow/imm_XX_<flow>.json      # state machine
└── tests/test_immXX.py
```

## Tier 1 — API layer (two equivalent patterns)

The codebase has **two interchangeable patterns** for API handlers. Pick one per module and stay consistent within that module.

### Pattern A — explicit `_handle` wrapper (used by IMM-09)

```python
# api/immXX.py
from __future__ import annotations
import json
import frappe
from assetcore.services import immXX as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok


def _parse_json(raw, *, field_name: str, default=None):
    if not raw:
        return default if default is not None else {}
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError) as e:
        raise ServiceError(ErrorCode.INVALID_PARAMS,
                           f"{field_name} không phải JSON hợp lệ") from e


def _handle(fn, *args, **kwargs) -> dict:
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)


@frappe.whitelist()
def list_things(filters: str = "{}", page: int = 1, page_size: int = 20):
    try:
        f = _parse_json(filters, field_name="filters")
    except ServiceError as e:
        return _err(e.message, e.code)
    return _handle(svc.list_things, f, page=int(page), page_size=int(page_size))


@frappe.whitelist(methods=["POST"])
def do_action(name: str, payload: str = "{}"):
    return _handle(svc.do_action, name, _parse_json(payload, field_name="payload"))
```

### Pattern B — `@api_endpoint` decorator (when service uses `frappe.throw`)

`assetcore/utils/api_endpoint.py` provides a decorator that catches Frappe-native exceptions (`DoesNotExistError`, `PermissionError`, `DuplicateEntryError`, `LinkValidationError`, `ValidationError`) and maps each to the right `ErrorCode`. Use this when the service layer uses `frappe.throw` instead of raising `ServiceError`.

```python
from assetcore.utils.api_endpoint import api_endpoint
from assetcore.utils.response import _ok

@frappe.whitelist()
@api_endpoint
def get_thing(name: str) -> dict:
    doc = frappe.get_doc("AC Asset", name)        # DoesNotExistError → 404
    if doc.locked:
        frappe.throw("Tài sản đang bị khóa")       # ValidationError → 422 BUSINESS_RULE
    return _ok(doc.as_dict())
```

**Pick the pattern by service style:**
- Service raises `ServiceError(ErrorCode.X, msg)` → use Pattern A (`_handle`).
- Service uses `frappe.throw(_("..."))` and lets Frappe exceptions bubble → use Pattern B (`@api_endpoint`).
- Don't mix both decorators on the same handler.

**Common conventions:**
- All endpoints return the envelope `{success, data}` or `{success: false, error, code, http_status, fields?}`. Never let an exception reach the HTTP layer.
- Mutating endpoints SHOULD declare `methods=["POST"]` to keep CSRF posture tight. (Many existing endpoints don't yet — when you touch one, add the kwarg.)
- Cast scalar query params (`int(page)`, `bool(flag)`) — Frappe sends them as strings.
- Parse JSON-encoded list/dict params with `_parse_json` so failures surface as `INVALID_PARAMS`.
- Whitelist function paths follow the URL `/api/method/assetcore.api.<module>.<fn_name>`.

## Tier 2 — Service layer template

```python
# services/immXX.py
from __future__ import annotations
import frappe
from frappe.utils import now_datetime, nowdate
from frappe import _

from assetcore.repositories.<name>_repo import <Name>Repo
from assetcore.services.shared import (
    AssetStatus, ErrorCode, ServiceError, Roles,
)
from assetcore.services.shared.permissions import require_role


# Module-local enums — keep status strings here, not scattered.
class XStatus:
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    ACTIVE = (OPEN, IN_PROGRESS)


# ── Validators (called from controller hooks AND service entrypoints) ─────
def validate_X_source(doc) -> None:
    """BR-XX-01: business rule statement here."""
    if not doc.source_a and not doc.source_b:
        frappe.throw(_("Phải có ít nhất một nguồn."))


# ── Permission gates ──────────────────────────────────────────────────────
def _require_can_create():
    require_role(Roles.CAN_CREATE_WO, "Không đủ quyền tạo work order")


# ── Entrypoints called by api/ ────────────────────────────────────────────
def list_things(filters: dict, *, page: int, page_size: int):
    rows, pg = <Name>Repo.list(filters, page=page, page_size=page_size,
                               fields=["name", "status", "modified"])
    return {"data": rows, "pagination": pg}


def create_thing(*, asset_ref: str, **kwargs) -> dict:
    _require_can_create()
    if not <Name>Repo.exists({"asset_ref": asset_ref, "status": ("in", list(XStatus.ACTIVE))}):
        # all good
        pass
    else:
        raise ServiceError(ErrorCode.CONFLICT, "Đã có WO đang mở cho thiết bị này")

    doc = frappe.get_doc({"doctype": "<Name>", "asset_ref": asset_ref, **kwargs})
    doc.insert()
    return {"name": doc.name}
```

**Conventions:**
- Raise `ServiceError(ErrorCode.X, "vietnamese message")` for business errors. Use `frappe.throw(_("..."))` only inside DocType controller hooks (where Frappe converts it to a `ValidationError` the form layer understands).
- **`frappe.throw(_(f"..."))` is wrong** — f-strings inside `_()` are never translatable (the string extractor sees a runtime value). Always use `frappe.throw(_("... {}").format(value))`.
- **Never call `doc.save()` or `frappe.get_doc(...).save()` on a submitted document** (docstatus=1) — Frappe throws a re-submit guard. Use `frappe.db.set_value(DOCTYPE, name, field, value, update_modified=False)` for post-submit field updates.
- Use `frappe.logger("immXX").info(...)` for operational telemetry (KPI compute, schedule ticks). Reserve `frappe.log_error(...)` for actual errors — it creates records in the Error Log DocType visible to all desk users.
- Shared utilities (filter normalization, operator tokens) must go in `assetcore/services/shared/filters.py` — don't duplicate the same block across service files.
- Real `ErrorCode` constants (from `services/shared/constants.py`): `NOT_FOUND`, `FORBIDDEN`, `UNAUTHORIZED`, `VALIDATION`, `BUSINESS_RULE`, `CONFLICT`, `BAD_STATE`, `DUPLICATE`, `INVALID_PARAMS`, `RATE_LIMITED`, `INTERNAL`. Do NOT use `VALIDATION_ERROR`/`BUSINESS_RULE_VIOLATION`/`INTERNAL_ERROR` — those belong to the legacy `utils.response.ErrorCode` kept for backwards compat.
- Use the convenience factories in `services/shared/errors.py` when they fit: `not_found(msg)`, `forbidden(msg)`, `unauthorized(msg)`, `validation(msg)`, `conflict(msg)`, `bad_state(msg)`.
- Keep validators pure (`validate_*(doc)`) so controllers can reuse them.
- Permission checks at the **entry** of every mutating service function. Never trust the caller.
- Status strings live in a module-local class (`XStatus`). Don't import status from one module into another — duplicate if needed; modules must stay decoupled.
- For SLA / matrices use a dict at module top: `_SLA_MATRIX: dict[tuple[str, str], float] = {...}`.

## Tier 3 — Repository

```python
# repositories/<name>_repo.py
from .base import BaseRepository

class <Name>Repo(BaseRepository):
    DOCTYPE = "<DocType Name>"
```

`BaseRepository` already provides `exists`, `get`, `get_value`, `count`, `list`, `find_one`, `create`, `update`, `delete` with Frappe pagination. Only add custom methods if you need raw SQL or joins. **Never** call `frappe.db.*` from services — go through the repo.

## DocType controller hooks

```python
# assetcore/doctype/<name>/<name>.py
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class <Name>(Document):
    def before_insert(self) -> None:
        from assetcore.services.immXX import validate_X_source
        validate_X_source(self)
        self.open_datetime = now_datetime()

    def validate(self) -> None:
        from assetcore.services.immXX import validate_spare_parts_stock_entries
        validate_spare_parts_stock_entries(self)

    def on_submit(self) -> None:
        from assetcore.services.imm00 import write_lifecycle_event
        write_lifecycle_event(self.asset_ref, "X_completed", self.name)
```

**Conventions:**
- Lazy-import service functions inside hooks to avoid circular imports.
- Hook order: `before_insert → validate → on_insert → on_update → on_submit`.
- Add `@property` shims for ERPNext-expected fields (`completion_date`, `posting_date`, `company`) when ERPNext's stock/accounting hooks may touch the doc — see `asset_repair.py` for reference.

## Lifecycle / audit trail — MANDATORY for state changes

Every status transition on an asset writes a SHA-256-chained row in `IMM Audit Trail` (tamper-evident log). Use the helper at `assetcore/utils/lifecycle.py:log_audit_event` — never hand-build the record (the hash chain breaks if you do).

```python
from assetcore.utils.lifecycle import log_audit_event
from assetcore.services.imm00 import transition_asset_status
from assetcore.services.shared import AssetStatus

# Direct audit log
log_audit_event(
    asset=asset_ref,
    event_type="repair_completed",
    ref_doctype="Asset Repair", ref_name=wo_name,
    from_status=RepairStatus.IN_REPAIR, to_status=RepairStatus.COMPLETED,
    change_summary="WO closed; checklist 100% Pass",
)

# Or: combined helper that flips asset status AND writes the audit row
transition_asset_status(asset_ref, AssetStatus.ACTIVE, root_record=wo_name)
```

`log_audit_event` reads the previous row's `hash_sha256`, hashes `(asset, event_type, timestamp, actor, change_summary, prev_hash)`, and stores the new hash. Auditors verify chain integrity by re-hashing.

`Asset Lifecycle Event` (the simpler DocType) still exists for FE-facing timelines, but **`IMM Audit Trail` is the compliance source of truth**. When in doubt, write to audit trail.

## Wire endpoint into hooks if needed

Whitelisted methods are auto-discoverable at `/api/method/assetcore.api.immXX.fn_name`. Only edit `hooks.py` if you need fixtures, scheduled events, or doc events:

```python
# hooks.py
doc_events = {
    "<DocType Name>": {
        "before_save": "assetcore.services.immXX.before_save_handler",
    }
}
scheduler_events = {
    "hourly": ["assetcore.services.immXX.update_overdue_status"],
}
```

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| `CSRFTokenError` from FE POST | Endpoint not declared with `methods=["POST"]` | Add the kwarg |
| Service test passes but API returns 500 | Forgot `@frappe.whitelist()` | Decorate the public function |
| `ServiceError` reaches caller as 500 | Missing `_handle()` wrap | Wrap every call in `_handle` |
| Status string mismatch FE/BE | Hardcoded literal | Move to constant class, share via API response |
| Stale data after `frappe.db.set_value` | Forgot `frappe.db.commit()` in CLI scripts | Inside web requests Frappe commits; for `bench execute` you must commit explicitly |
| `ValidationError` on `doc.save()` after submit | Calling `.save()` on a submitted (docstatus=1) doc | Use `frappe.db.set_value(..., update_modified=False)` instead |
| Audit trail gap for pre-asset records | Service called `frappe.get_doc({...}).insert()` directly instead of `log_audit_event` | Route all audit writes through the canonical helper |
| Errors disappear silently | Bare `except: pass` or `except Exception: pass` in service/controller | At minimum `frappe.log_error(title, e)` inside the except |
| Recurring records in hourly job | Boolean flag field not reset after processing (e.g., `is_open = 0` forgotten) | Always reset the flag that was used to select the records |

## Where to look for live examples

- `assetcore/api/imm09.py` + `assetcore/services/imm09.py` — complete reference: list/create/assign/diagnose/start/close + SLA + validators (Pattern A)
- `assetcore/api/dashboard.py`, `assetcore/api/auth.py` — Pattern B (`@api_endpoint`)
- `assetcore/services/shared/constants.py` — `Roles`, `ErrorCode`, `AssetStatus`, `ApprovalStatus`, `CalibrationStatus`, `CalibrationResult`
- `assetcore/services/shared/__init__.py` — canonical re-exports (always import from here)
- `assetcore/services/shared/errors.py` — `ServiceError` + factories (`not_found`, `forbidden`, `validation`, `conflict`, `bad_state`)
- `assetcore/repositories/base.py` — `BaseRepository` contract (`exists`, `get`, `list`, `count`, `find_one`, `create`, `update`, `delete`)
- `assetcore/repositories/__init__.py` — canonical re-exports for all repos; import from here, not from the individual `_repo.py` files directly
- `assetcore/services/shared/filters.py` — `normalize_filters()` for query filter normalization (do not duplicate per-module)
- `assetcore/utils/response.py` — `_ok`, `_err`, legacy `ErrorCode` (do not use the legacy enum in new code)
- `assetcore/utils/api_endpoint.py` — `@api_endpoint` decorator
- `assetcore/utils/lifecycle.py` — `log_audit_event` (SHA-256 chain)
- `assetcore/utils/helpers.py` — `_get_role_emails`, `_safe_sendmail` (also re-exports `_ok`, `_err`)
- `assetcore/utils/pagination.py` — `paginate(total, page, page_size)` returns `{page, page_size, total, total_pages, offset}`

## Build sequence for a new IMM module

1. Confirm requirement (BR-XX-NN identifiers from `docs/imm-XX/`).
2. Design DocType schema → use `assetcore-doctype-designer` skill.
3. Design workflow → use `assetcore-workflow-builder` skill.
4. Write tests first (TDD per CLAUDE.md §17) → use `assetcore-tester` skill.
5. Implement repository (1 file, ~10 lines).
6. Implement service: constants, validators, entrypoints.
7. Implement DocType controller hooks (delegate to service).
8. Implement API layer (whitelist + `_handle`).
9. Run `bench --site <site> run-tests --module assetcore.tests.test_immXX`.
10. Update `assetcore/api/README.md` with new endpoint signatures.

---

## Cross-skill conventions

Read [`/.claude/skills/CONVENTIONS.md`](../CONVENTIONS.md) for project-wide rules. Especially relevant to this skill:

- §2. Architecture Layers — strict 3-tier; never call `frappe.db.set_value` from service (use repo)
- §3. Error Handling — use `ServiceError + ErrorCode` only; never throw ad-hoc strings
- §4. Audit & Lifecycle — every state transition MUST emit IMM Audit Trail
- §5. Permissions Layer 3 — centralize role guards in `services/shared/permissions.py`

### Module-specific gotchas
- `_normalize_filters` duplicated in imm08/09/11.py — import from `services.shared` instead
- `_parse_json` is duplicated in every API file — TODO: consolidate to `api.utils`
- Only `imm06` has explicit `_guard()` auth check; others rely on `@frappe.whitelist()` alone
- Many services bypass repositories — when refactoring a service, route reads through its repo
