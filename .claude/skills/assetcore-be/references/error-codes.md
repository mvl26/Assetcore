# ErrorCode reference (canonical)

Canonical class lives at `assetcore/services/shared/constants.py:213`, re-exported by `assetcore.services.shared`. Always import from there.

```python
from assetcore.services.shared import ErrorCode, ServiceError
```

## Real codes

| Constant | Value | HTTP | Use when |
|---|---|---|---|
| `ErrorCode.NOT_FOUND` | `"NOT_FOUND"` | 404 | Record doesn't exist |
| `ErrorCode.UNAUTHORIZED` | `"UNAUTHORIZED"` | 401 | No session / expired |
| `ErrorCode.FORBIDDEN` | `"FORBIDDEN"` | 403 | Authenticated but missing role |
| `ErrorCode.VALIDATION` | `"VALIDATION"` | 400 | Input shape wrong, required field missing, type mismatch |
| `ErrorCode.INVALID_PARAMS` | `"INVALID_PARAMS"` | 400 | JSON parse failed, illegal cast |
| `ErrorCode.BUSINESS_RULE` | `"BUSINESS_RULE"` | 422 | BR-XX-NN broken (SLA, mutual-exclusion, workflow gate) |
| `ErrorCode.BAD_STATE` | `"BAD_STATE"` | 409 | Object exists but in wrong state for this action |
| `ErrorCode.CONFLICT` | `"CONFLICT"` | 409 | Concurrent edit / duplicate active record |
| `ErrorCode.DUPLICATE` | `"DUPLICATE"` | 409 | Unique key violation |
| `ErrorCode.RATE_LIMITED` | `"RATE_LIMITED"` | 429 | Too many requests |
| `ErrorCode.INTERNAL` | `"INTERNAL"` | 500 | Unhandled exception bubbled up |

## ⚠ Do NOT use the legacy codes

There's a second `ErrorCode` class in `assetcore/utils/response.py` with values:
`VALIDATION_ERROR`, `BUSINESS_RULE_VIOLATION`, `UNAUTHORIZED`, `FORBIDDEN`, `NOT_FOUND`, `CONFLICT`, `INTERNAL_ERROR`.

These exist only to keep older `_err(msg, code=400)` int-based callers working. The `_err()` helper auto-translates HTTP int → legacy string via `_HTTP_TO_CODE`. New service code raises `ServiceError(ErrorCode.X, msg)` using the canonical class above; the API layer's `_handle()` passes `e.code` (canonical string) into `_err()`, which keeps it as-is (it only translates ints).

## Frontend mapping

`frontend/src/api/errors.ts` defines its own `ErrorCode` constant matching what FE needs. Both legacy and canonical strings are tolerated by `httpStatusToCode()` and `unwrap()`. New BE codes that aren't in FE's list fall through to `ErrorCode.UNKNOWN`. If you add a brand-new code on BE, also add it to FE's `errors.ts`.

## Decision rules

- Could the user fix the input and retry? → `VALIDATION` or `INVALID_PARAMS`.
- Did the user violate a business rule (SLA breach, missing approval)? → `BUSINESS_RULE`.
- Is the record in the wrong state for this action? → `BAD_STATE`.
- Concurrent / duplicate? → `CONFLICT` or `DUPLICATE`.
- Wrong identity? → `UNAUTHORIZED` (no session) or `FORBIDDEN` (wrong role).
- Did our code blow up? → `INTERNAL`.

## Factories (use these instead of raw constructor)

```python
from assetcore.services.shared.errors import (
    not_found, forbidden, unauthorized, validation, conflict, bad_state,
)

raise not_found("Work order không tồn tại")
raise forbidden("Chỉ Workshop Lead được đóng WO")
raise unauthorized()                  # default message
raise validation("priority không hợp lệ")
raise conflict("Đã có WO sửa chữa đang mở cho thiết bị này")
raise bad_state("WO đã đóng — không thể assign")
```

## Field-level errors (form validation)

`_err(msg, code, fields={...})` accepts a `fields` dict — FE renders inline next to inputs:

```python
return _err(
    "Dữ liệu không hợp lệ",
    ErrorCode.VALIDATION,
    fields={"asset_ref": "Bắt buộc", "priority": "Phải là Normal|Urgent|Emergency"},
)
```

For desk forms, use `frappe.throw(_("..."), as_list=True)` — Frappe shows it as a list in the form alert.
