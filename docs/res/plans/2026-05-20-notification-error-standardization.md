# Chuẩn hoá Notification & Error Framework (AssetCore)

> **Status (2026-05-25):** Phase 0–2 hoàn thành. Phase 3–6 còn lại. Xem block "Implementation status (2026-05-25)" ở cuối file.
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thống nhất toàn bộ thông báo (lỗi nghiệp vụ, lỗi hệ thống, thành công, warning, info) trên BE + FE qua **một nguồn chân lý duy nhất** — code-first registry với typed `NotificationCode` (giai đoạn 1), sẵn sàng migrate sang doctype-driven (giai đoạn 2 — không nằm trong plan này). Loại bỏ 197+ `frappe.throw()` bare, 14+ `frappe.msgprint()`, và hàng trăm chuỗi toast hardcode rải khắp FE.

**Non-Goals (giai đoạn 1):**
- KHÔNG tạo `Error Registry` doctype (deferred — chỉ làm khi BA cần edit live).
- KHÔNG inject qua `frappe.boot` (AssetCore FE là SPA tách rời).
- KHÔNG đổi UX model (giữ toast non-blocking, không chuyển sang `msgprint` dialog).
- KHÔNG đa ngôn ngữ động (chỉ chuẩn cấu trúc; i18n full nằm ở giai đoạn 3).

**Architecture:**

```
┌───────────────────────────────────────────────────────────────┐
│   SOURCE OF TRUTH — Python dict + TypeScript const (generated) │
│   assetcore/utils/messages.py   ⇄   frontend/src/locales/messages.ts │
└───────────────────────────────────────────────────────────────┘
        ↓ raise/lookup                       ↓ lookup/render
┌──────────────────────────┐       ┌──────────────────────────────┐
│  BE  ServiceError(code,  │ HTTP  │  FE  ApiError + notify.show()│
│       ctx={...})         │ ────► │  axios interceptor → toast/  │
│  → utils/response._err() │ code+ │  modal theo `severity`       │
│  → controllers: validate │ ctx   │  Vue errorHandler hook       │
│    /hooks dùng `nthrow()`│       │                              │
└──────────────────────────┘       └──────────────────────────────┘
```

- BE raise `ServiceError(code=MSG.XXX, context={...})`. Helper `_err()` format `message_template.format(**context)` từ registry.
- API response envelope mở rộng: `{success, error, code, context, action_hint, severity, fields}`.
- FE axios interceptor parse `code + context` → tạo `ApiError` với template đã render → component gọi `notify.fromError(e)` hoặc `notify.show(code, ctx)`.
- Notification UX phân nhánh theo `severity`: `error/warning` → toast đỏ/vàng; `success/info` → toast xanh/xám; `critical` → modal blocking (vd: lỗi compliance gate, mất dữ liệu).

**Tech Stack:** Frappe v15 (Python 3.11), MariaDB, Vue 3 + TypeScript + Pinia, axios, TailwindCSS.

**Reference:**
- Framework gốc (Miyano): [docs/res/frameworks/miyano-error-framework.md](../frameworks/miyano-error-framework.md)
- Phân tích gap: phiên hội thoại 2026-05-20 (lưu trong memory `notification_framework_analysis`).
- BE hiện tại: `assetcore/utils/response.py`, `assetcore/utils/helpers.py`, `assetcore/services/shared/errors.py`, `assetcore/services/shared/constants.py`.
- FE hiện tại: `frontend/src/api/errors.ts`, `frontend/src/api/axios.ts`, `frontend/src/composables/useToast.ts`, `frontend/src/App.vue`.

---

## File Structure

### Backend (sửa)

- `assetcore/utils/response.py` — mở rộng `_err()` thêm `context`, `action_hint`, `severity`; bổ sung `lookup_message(code, ctx)`.
- `assetcore/utils/helpers.py` — **DEPRECATE** `_err/_ok`; re-export từ `response.py` để giữ backwards-compat; xoá sau Phase 4.
- `assetcore/services/shared/errors.py` — `ServiceError.__init__` thêm `context: dict | None = None`; thêm factory `notify_throw(code, **ctx)`.
- `assetcore/services/shared/constants.py` — xoá `ErrorCode` (duplicate); re-export từ `response.py`.
- `assetcore/services/shared/__init__.py` — expose `ServiceError`, `nthrow`, `MSG`.
- 197 file BE có `frappe.throw()` bare — migrate sang `nthrow(MSG.XXX, **ctx)` (Phase 4).
- 14 file BE có `frappe.msgprint()` bare — migrate sang `nmsg(MSG.XXX, **ctx)` hoặc xoá (Phase 4).

### Backend (tạo mới)

- `assetcore/utils/messages.py` — **NEW** central message registry (Python). Class `MSG` chứa hằng số mã lỗi; dict `MESSAGES` chứa `{code: {title, template, action_hint, severity, http_status}}`.
- `assetcore/utils/notify.py` — **NEW** helpers `nthrow()` (raise ServiceError + lookup), `nmsg()` (msgprint chuẩn — chỉ dùng trong Frappe Desk legacy), `format_message(code, ctx)`.
- `assetcore/tests/test_notification_framework.py` — **NEW** unit test: lookup, template render, context missing, fallback `SYS-500`, envelope shape.
- `scripts/gen_fe_messages.py` — **NEW** generator: parse `utils/messages.py` → emit `frontend/src/locales/messages.ts`.

### Frontend (sửa)

- `frontend/src/api/errors.ts` — `ApiError` thêm `messageCode?: string`, `context?: Record<string, unknown>`, `actionHint?: string`, `severity?: Severity`, `title?: string`.
- `frontend/src/api/axios.ts` — response interceptor: nếu response có `code + context` → resolve qua `messages.ts` registry, hydrate `ApiError`.
- `frontend/src/composables/useToast.ts` — mở rộng `show(opts: { code?, ctx?, title?, message?, severity, actionHint?, duration? })`; giữ legacy `success/error/warning/info(msg)`; thêm `fromError(e: ApiError)`.
- `frontend/src/App.vue` — Vue `errorHandler` + `unhandledrejection` chuyển sang `notify.fromError(e)`; modal fallback khi `severity === 'critical'`.
- Tất cả views có `toast.success('...')` / `toast.error('...')` hardcode — migrate sang `notify.show({ code: MSG.XXX, ctx })` (Phase 5).

### Frontend (tạo mới)

- `frontend/src/locales/messages.ts` — **GENERATED** từ `scripts/gen_fe_messages.py`; KHÔNG chỉnh tay.
- `frontend/src/locales/messages.types.ts` — **NEW** type definitions: `Severity`, `MessageEntry`, `MessageCode`.
- `frontend/src/composables/useNotify.ts` — **NEW** `useNotify()` wrapper: `show(code, ctx)`, `fromError(e)`, `confirm(code, ctx)`; phân nhánh toast/modal theo severity.
- `frontend/src/components/common/NotificationModal.vue` — **NEW** blocking dialog cho `severity: critical`.
- `frontend/src/__tests__/useNotify.spec.ts` — **NEW** unit test render template, fromError mapping, severity routing.

### Docs (sync)

- `docs/res/frameworks/miyano-error-framework.md` — thêm note "AssetCore adaptation — see plans/2026-05-20".
- `CLAUDE.md` §15 (Code Style) — thêm rule: "Không gọi `frappe.throw` / `frappe.msgprint` / `toast.error('literal')` — dùng `nthrow(MSG.XXX)` hoặc `notify.show({code})`".
- `docs/imm-00/04_Backend_Design.md` (và tương đương các module) — sync code pattern mới.

---

## Phase 0 — Hợp nhất duplicate (prerequisite) [DONE 2026-05-25]

### Task 0.1: Hợp nhất `_err/_ok` helpers  [DONE]

**Files:**
- Modify: `assetcore/utils/helpers.py`
- Modify: `assetcore/utils/response.py`

- [ ] **Step 1**: Xác nhận `response.py:_err()` là canonical (đã có HTTP mapping, fields, extra).
- [ ] **Step 2**: Trong `helpers.py`, xoá `_err`/`_ok` cũ, thay bằng `from assetcore.utils.response import _err, _ok  # re-export`.
- [ ] **Step 3**: Chạy `grep -rn "from assetcore.utils.helpers import.*_err" assetcore/` → confirm tất cả import vẫn resolved.
- [ ] **Step 4**: `bench --site assetcore.local migrate && bench --site assetcore.local run-tests --app assetcore` → green.

### Task 0.2: Hợp nhất `ErrorCode` enum  [DONE]

**Files:**
- Modify: `assetcore/services/shared/constants.py`
- Modify: `assetcore/utils/response.py`

- [ ] **Step 1**: Liệt kê toàn bộ code trong 2 enum, đối chiếu trùng (`NOT_FOUND`, `FORBIDDEN`, `UNAUTHORIZED`, `VALIDATION`, `CONFLICT`, `INTERNAL`) và khác (`BAD_STATE`, `DUPLICATE`, `INVALID_PARAMS`, `RATE_LIMITED`, `COMPLIANCE_BLOCKED` chỉ ở `constants.py`; `BUSINESS_RULE = "BUSINESS_RULE_VIOLATION"` ở `response.py` vs `BUSINESS_RULE = "BUSINESS_RULE"` ở `constants.py`).
- [ ] **Step 2**: **Quyết định**: dùng giá trị `constants.py` (ngắn hơn, khớp services). Sửa `response.py:ErrorCode.BUSINESS_RULE = "BUSINESS_RULE"`.
- [ ] **Step 3**: Move full enum vào `response.py` (single source); `constants.py` chỉ `from assetcore.utils.response import ErrorCode  # re-export`.
- [ ] **Step 4**: Sync FE `frontend/src/api/errors.ts:ErrorCode` để khớp values mới (đổi `BUSINESS_RULE_VIOLATION` → `BUSINESS_RULE`, bổ sung `BAD_STATE`, `DUPLICATE`, `INVALID_PARAMS`, `RATE_LIMITED`, `COMPLIANCE_BLOCKED`).
- [ ] **Step 5**: Run tests + grep call sites của `ErrorCode.BUSINESS_RULE_VIOLATION` (cả Python lẫn TS) — đảm bảo không còn.

---

## Phase 1 — Central Message Registry (BE) [DONE 2026-05-25]

### Task 1.1: Tạo `utils/messages.py`  [DONE]

**Files:**
- Create: `assetcore/utils/messages.py`

- [ ] **Step 1**: Viết failing test trước (`tests/test_notification_framework.py::test_lookup_message_returns_template`).
- [ ] **Step 2**: Implement skeleton:

```python
# assetcore/utils/messages.py
from __future__ import annotations
from typing import TypedDict, Literal

Severity = Literal["error", "warning", "info", "success", "critical"]

class MessageEntry(TypedDict):
    title: str
    template: str
    action_hint: str
    severity: Severity
    http_status: int

class MSG:
    """Hằng số mã thông báo — naming: SYS-/AUTH-/VAL-/BIZ-/IMM<NN>-/UI-."""
    # System
    SYS_500 = "SYS-500"
    SYS_NETWORK = "SYS-NETWORK"
    # Auth
    AUTH_UNAUTHORIZED = "AUTH-401"
    AUTH_FORBIDDEN = "AUTH-403"
    AUTH_SESSION_EXPIRED = "AUTH-SESSION-EXPIRED"
    # Validation
    VAL_REQUIRED = "VAL-REQUIRED"
    VAL_INVALID_FORMAT = "VAL-FORMAT"
    # Business (module-prefixed)
    IMM04_NOT_FOUND = "IMM04-NOT-FOUND"
    IMM04_BAD_STATE = "IMM04-BAD-STATE"
    # ... (sẽ điền dần ở Phase 4)

MESSAGES: dict[str, MessageEntry] = {
    MSG.SYS_500: {
        "title": "Lỗi hệ thống",
        "template": "Đã xảy ra sự cố không lường trước. Dữ liệu của bạn chưa bị mất.",
        "action_hint": "Vui lòng tải lại trang (F5). Nếu lỗi tiếp diễn, liên hệ IT.",
        "severity": "error",
        "http_status": 500,
    },
    MSG.VAL_REQUIRED: {
        "title": "Thiếu thông tin bắt buộc",
        "template": "Trường {field} chưa được điền.",
        "action_hint": "Vui lòng điền đầy đủ trước khi lưu.",
        "severity": "warning",
        "http_status": 422,
    },
    # ...
}

def lookup_message(code: str, context: dict | None = None) -> MessageEntry:
    entry = MESSAGES.get(code)
    if not entry:
        # Fallback an toàn — không lộ code lạ ra user
        return MESSAGES[MSG.SYS_500]
    return entry

def format_message(code: str, context: dict | None = None) -> tuple[str, str, MessageEntry]:
    entry = lookup_message(code, context)
    ctx = context or {}
    try:
        message = entry["template"].format(**ctx)
    except KeyError as e:
        import frappe
        frappe.log_error(f"messages: missing key {e} for {code}", "notification_framework")
        message = entry["template"]
    return entry["title"], message, entry
```

- [ ] **Step 3**: Run test → green.

### Task 1.2: Mở rộng `ServiceError` + tạo `nthrow()`  [DONE]

**Files:**
- Modify: `assetcore/services/shared/errors.py`
- Create: `assetcore/utils/notify.py`

- [ ] **Step 1**: Viết failing test `test_nthrow_raises_service_error_with_resolved_message`.
- [ ] **Step 2**: Sửa `ServiceError.__init__` thêm `context: dict | None = None`, `message_code: str | None = None`:

```python
class ServiceError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        http_status: int = 400,
        context: dict | None = None,
        message_code: str | None = None,
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.context = context or {}
        self.message_code = message_code  # MSG.XXX lookup key
        super().__init__(f"[{code}] {message}")
```

- [ ] **Step 3**: Tạo `utils/notify.py`:

```python
from assetcore.utils.messages import MSG, format_message, lookup_message
from assetcore.services.shared.errors import ServiceError
from assetcore.utils.response import ErrorCode

def nthrow(message_code: str, **context) -> None:
    """Raise ServiceError chuẩn từ message registry."""
    title, message, entry = format_message(message_code, context)
    # Map severity → ErrorCode
    code_map = {
        500: ErrorCode.INTERNAL_ERROR,
        422: ErrorCode.BUSINESS_RULE,
        409: ErrorCode.CONFLICT,
        404: ErrorCode.NOT_FOUND,
        403: ErrorCode.FORBIDDEN,
        401: ErrorCode.UNAUTHORIZED,
        400: ErrorCode.VALIDATION_ERROR,
    }
    error_code = code_map.get(entry["http_status"], ErrorCode.VALIDATION_ERROR)
    raise ServiceError(
        code=error_code,
        message=message,
        http_status=entry["http_status"],
        context=context,
        message_code=message_code,
    )
```

- [ ] **Step 4**: Run test → green.

### Task 1.3: Mở rộng `_err()` envelope  [DONE]

**Files:**
- Modify: `assetcore/utils/response.py`
- Modify: `assetcore/api/imm04.py` (sample, để verify shape)

- [ ] **Step 1**: Viết failing test `test_err_envelope_includes_context_and_action_hint`.
- [ ] **Step 2**: Sửa `_err()` thêm params `context`, `action_hint`, `severity`, `message_code`, `title`:

```python
def _err(
    msg: str,
    code: Any = 400,
    fields: dict | None = None,
    http_status: int | None = None,
    extra: dict | None = None,
    *,
    message_code: str | None = None,
    context: dict | None = None,
    action_hint: str | None = None,
    severity: str | None = None,
    title: str | None = None,
) -> dict:
    # ... existing logic ...
    payload: dict = {
        "success": False,
        "error": msg,
        "code": error_code,
        "http_status": http,
    }
    if message_code: payload["message_code"] = message_code
    if context: payload["context"] = context
    if action_hint: payload["action_hint"] = action_hint
    if severity: payload["severity"] = severity
    if title: payload["title"] = title
    if fields: payload["fields"] = fields
    if extra: payload.update(extra)
    return payload
```

- [ ] **Step 3**: Trong `api/imm04.py:_handle()`, khi bắt `ServiceError`, đọc thêm `e.message_code`, `e.context` và truyền vào `_err()`:

```python
except ServiceError as e:
    if e.message_code:
        from assetcore.utils.messages import lookup_message
        entry = lookup_message(e.message_code)
        return _err(
            e.message, e.code,
            message_code=e.message_code,
            context=e.context,
            action_hint=entry.get("action_hint"),
            severity=entry.get("severity"),
            title=entry.get("title"),
        )
    return _err(e.message, e.code)
```

- [ ] **Step 4**: Refactor `_handle()` thành shared helper `assetcore/utils/api_handler.py:handle()` (hiện đang duplicate ở mọi `api/immXX.py`).
- [ ] **Step 5**: Run test → green.

### Task 1.4: FE message generator  [DONE]

**Files:**
- Create: `scripts/gen_fe_messages.py`
- Create: `frontend/src/locales/messages.ts` (generated)
- Create: `frontend/src/locales/messages.types.ts`

- [ ] **Step 1**: Viết generator parse `utils/messages.py` qua AST (không import — tránh phụ thuộc Frappe), emit `messages.ts`.
- [ ] **Step 2**: Output shape:

```typescript
// AUTO-GENERATED from assetcore/utils/messages.py — DO NOT EDIT
import type { MessageEntry, MessageCode } from './messages.types'

export const MSG = {
  SYS_500: 'SYS-500',
  VAL_REQUIRED: 'VAL-REQUIRED',
  // ...
} as const

export const MESSAGES: Record<MessageCode, MessageEntry> = {
  'SYS-500': { title: '...', template: '...', action_hint: '...', severity: 'error', http_status: 500 },
  // ...
}
```

- [ ] **Step 3**: Thêm hook vào `package.json`: `"gen:messages": "python ../scripts/gen_fe_messages.py"`.
- [ ] **Step 4**: Thêm CI check: chạy generator, `git diff --exit-code frontend/src/locales/messages.ts` → fail nếu out-of-sync.
- [ ] **Step 5**: Document quy trình: "Thêm mã mới → sửa `utils/messages.py` → `npm run gen:messages` → commit cả 2 file".

---

## Phase 2 — Frontend Notification System [DONE 2026-05-25]

### Task 2.1: Mở rộng `ApiError`  [DONE]

**Files:**
- Modify: `frontend/src/api/errors.ts`

- [ ] **Step 1**: Viết failing test `useNotify.spec.ts::ApiError carries messageCode and context`.
- [ ] **Step 2**: Thêm fields:

```typescript
export class ApiError extends Error {
  readonly code: ErrorCodeType
  readonly httpStatus: number
  readonly fields?: Record<string, string>
  readonly extra?: Record<string, unknown>
  readonly messageCode?: string
  readonly context?: Record<string, unknown>
  readonly actionHint?: string
  readonly severity?: Severity
  readonly title?: string

  constructor(message: string, opts: {
    code?: ErrorCodeType
    httpStatus?: number
    fields?: Record<string, string>
    extra?: Record<string, unknown>
    messageCode?: string
    context?: Record<string, unknown>
    actionHint?: string
    severity?: Severity
    title?: string
  } = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = opts.code ?? ErrorCode.UNKNOWN
    this.httpStatus = opts.httpStatus ?? 0
    // ... assign rest
  }
}
```

- [ ] **Step 3**: Backwards-compat: giữ alternate constructor `new ApiError(msg, code, status, fields, extra)` qua overload.
- [ ] **Step 4**: Run test → green.

### Task 2.2: Axios interceptor — hydrate ApiError từ registry  [DONE]

**Files:**
- Modify: `frontend/src/api/axios.ts`

- [ ] **Step 1**: Viết failing test: response 422 với `{code, message_code, context}` → ApiError có `messageCode`, `context`, `actionHint` populated từ MESSAGES registry.
- [ ] **Step 2**: Trong response interceptor, thêm helper `hydrateFromRegistry(data)`:

```typescript
import { MESSAGES, MSG } from '@/i18n/messages'

function hydrateFromRegistry(data: any, fallbackMsg: string, fallbackCode: ErrorCodeType, status: number): ApiError {
  const messageCode = data?.message_code as string | undefined
  const context = data?.context as Record<string, unknown> | undefined
  const entry = messageCode ? MESSAGES[messageCode as keyof typeof MESSAGES] : undefined

  if (entry) {
    const rendered = entry.template.replace(/\{(\w+)\}/g, (_, k) => String(context?.[k] ?? `[${k}]`))
    return new ApiError(rendered, {
      code: fallbackCode, httpStatus: status,
      messageCode, context,
      actionHint: entry.action_hint,
      severity: entry.severity,
      title: entry.title,
      fields: data?.fields, extra: data,
    })
  }
  return new ApiError(fallbackMsg, { code: fallbackCode, httpStatus: status, fields: data?.fields })
}
```

- [ ] **Step 3**: Thay tất cả `throw new ApiError(msg, code, status, ...)` trong interceptor bằng `throw hydrateFromRegistry(data, msg, code, status)`.
- [ ] **Step 4**: Run test → green.

### Task 2.3: Tạo `useNotify` composable  [DONE]

**Files:**
- Create: `frontend/src/composables/useNotify.ts`
- Modify: `frontend/src/composables/useToast.ts` (thêm severity field vào Toast type)

- [ ] **Step 1**: Viết failing test cho 4 use case: `show(code, ctx)`, `fromError(apiError)`, `confirm(code, ctx)`, fallback khi code không tồn tại.
- [ ] **Step 2**: Implement:

```typescript
// useNotify.ts
import { ApiError } from '@/api/errors'
import { MESSAGES, MSG } from '@/i18n/messages'
import { useToast } from './useToast'
import { useModal } from './useModal'  // tạo mới nếu chưa có

export function useNotify() {
  const toast = useToast()
  const modal = useModal()

  function render(code: string, ctx: Record<string, unknown> = {}) {
    const entry = MESSAGES[code as keyof typeof MESSAGES] ?? MESSAGES[MSG.SYS_500]
    const message = entry.template.replace(/\{(\w+)\}/g, (_, k) => String(ctx[k] ?? `[${k}]`))
    return { ...entry, message }
  }

  function show(opts: { code: string; ctx?: Record<string, unknown>; duration?: number }) {
    const { title, message, action_hint, severity } = render(opts.code, opts.ctx)
    const body = action_hint ? `${message}\n${action_hint}` : message

    if (severity === 'critical') {
      modal.alert({ title, body })
      return
    }
    toast.show(body, severity ?? 'info', opts.duration)
  }

  function fromError(e: unknown) {
    if (e instanceof ApiError && e.messageCode) {
      return show({ code: e.messageCode, ctx: e.context })
    }
    const msg = e instanceof Error ? e.message : String(e)
    toast.error(msg)
  }

  return { show, fromError, confirm: modal.confirm }
}
```

- [ ] **Step 3**: Cập nhật `useToast.Toast` type: thêm `severity` để match.
- [ ] **Step 4**: Run test → green.

### Task 2.4: Wire global handlers  [DONE]

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/main.ts`

- [ ] **Step 1**: Thay `toast.error(msg)` trong `App.vue` `errorHandler` + `unhandledrejection` bằng `notify.fromError(err)`.
- [ ] **Step 2**: Cùng pattern cho `main.ts:app.config.errorHandler`.
- [ ] **Step 3**: Test smoke: throw `ApiError` trong component → toast hiển thị đúng template + action_hint.

### Task 2.5: Modal cho critical severity  [DONE]

**Files:**
- Create: `frontend/src/components/common/NotificationModal.vue`
- Create: `frontend/src/composables/useModal.ts`

- [ ] **Step 1**: Viết failing test: `modal.alert({title, body})` mount component, click "Đóng" unmount.
- [ ] **Step 2**: Implement modal đơn giản (TailwindCSS, backdrop, ESC để đóng).
- [ ] **Step 3**: Cung cấp `alert(opts)` và `confirm(opts) → Promise<boolean>`.
- [ ] **Step 4**: Run test → green.

---

## Phase 3 — Seed initial messages

### Task 3.1: Inventory + seed

**Files:**
- Modify: `assetcore/utils/messages.py`

- [ ] **Step 1**: Grep `frappe.throw(_("...")` + `frappe.throw("...")` qua toàn repo BE; dedupe theo nội dung. Ước tính ~60-80 unique messages.
- [ ] **Step 2**: Grep `toast.success('...')`, `toast.error('...')`, `toast.warning('...')` qua `frontend/src/`. Ước tính ~150-200 unique messages.
- [ ] **Step 3**: Phân loại theo prefix module: `IMM00-`, `IMM01-`, ..., `IMM16-`, `SYS-`, `AUTH-`, `VAL-`, `UI-`, `IMPORT-`, `INVENTORY-`, `PURCHASE-`.
- [ ] **Step 4**: Áp dụng quy chuẩn ngôn ngữ §5 Miyano framework (chủ thể + hậu quả + action_hint). Editor BA review.
- [ ] **Step 5**: Điền vào `MESSAGES` dict; rerun `gen_fe_messages.py`.
- [ ] **Step 6**: Run test `test_all_messages_have_required_fields` (title không empty, template không empty, severity hợp lệ, http_status hợp lệ).

---

## Phase 4 — Migrate BE bare calls

> **Cách làm**: chia theo module IMM-XX, mỗi module 1 PR riêng để dễ review. Pattern tham chiếu trong từng task.

### Task 4.1: Migrate `services/imm04.py`

**Files:**
- Modify: `assetcore/services/imm04.py` (10 bare `frappe.throw`)
- Modify: `assetcore/api/imm04.py` (verify `_handle` đọc `message_code`)

- [ ] **Step 1**: Mỗi `frappe.throw(_("..."))` → `nthrow(MSG.IMMXX_YYY, **ctx)`. Nếu chưa có code → thêm vào `messages.py` trước.
- [ ] **Step 2**: Service tests: assert exception type `ServiceError` thay vì `frappe.ValidationError`.
- [ ] **Step 3**: Run test module → green; smoke API → response có `message_code` + `context`.

### Task 4.2-4.13: Lặp lại cho từng module

- [ ] `services/imm00.py` (12), `imm06.py` (9), `imm09.py` (10), `imm16.py` (11), `imm08.py` (5), `imm12.py`, `imm15.py`, `imm01.py`, `imm02.py`, `imm03.py`, `imm05.py`, `imm11.py`.
- [ ] `services/purchase.py` (5), `services/inventory.py`.

### Task 4.14: Migrate doctype controllers

**Files:**
- Modify: `assetcore/assetcore/doctype/asset_document/asset_document.py` (13)
- Modify: `assetcore/assetcore/doctype/asset_commissioning/asset_commissioning.py` (13)
- Modify: `assetcore/assetcore/doctype/imm_asset_calibration/imm_asset_calibration.py` (13)
- Modify: `assetcore/assetcore/doctype/ac_stock_movement/ac_stock_movement.py` (8)
- Modify: `assetcore/assetcore/doctype/ac_spare_part/ac_spare_part.py` (7)
- Modify: `assetcore/assetcore/doctype/imm_rca_record/imm_rca_record.py` (6)
- Modify: `assetcore/assetcore/doctype/ac_asset/ac_asset.py` (6)
- Modify: `assetcore/assetcore/doctype/ac_asset_category/ac_asset_category.py` (5)
- ... (xem `grep -rE "frappe\.throw\(" assetcore/assetcore/doctype/`)

- [ ] **Step 1**: Trong `validate()` / `on_submit()` hooks, dùng `nthrow()` thay `frappe.throw()`. Frappe sẽ propagate `ServiceError` thành 500 nếu không bắt → wrap doctype hooks bằng `ServiceError → frappe.throw` adapter:

```python
# utils/notify.py
def nthrow_in_hook(message_code, **ctx):
    """Cho doctype hook — convert thành frappe.ValidationError để Frappe handle."""
    title, message, entry = format_message(message_code, ctx)
    import frappe
    frappe.throw(msg=message, title=title, exc=frappe.ValidationError)
```

- [ ] **Step 2**: Hoặc nâng cấp: viết Frappe exception subclass mang `message_code`, axios interceptor parse từ `_server_messages`.
- [ ] **Step 3**: Run doctype tests → green.

### Task 4.15: Xoá `frappe.msgprint()` bare

**Files:** 14 file scattered (tìm bằng `grep -rn "frappe\.msgprint" assetcore/`).

- [ ] **Step 1**: Phân loại: success message → chuyển sang trả về `_ok({notify: MSG.XXX, context})` cho FE; warning info → giữ nếu chỉ chạy trong Frappe Desk legacy.
- [ ] **Step 2**: FE đọc `response.notify` trong `useApi`, gọi `notify.show()` tự động.

---

## Phase 5 — Migrate FE hardcoded toast

### Task 5.1: Migrate views — module-by-module

**Files:** ~30-50 view files có `toast.success/error/warning(...)`.

- [ ] **Step 1**: Module IMM-04: `views/commissioning/*.vue` — replace `toast.success('Đã gửi...')` → `notify.show({ code: MSG.IMM04_SENT, ctx: {...} })`.
- [ ] **Step 2**: Lặp lại cho IMM-05, 06, 08, 09, 11, 12, 15, 16, 00, 01, 02, 03.
- [ ] **Step 3**: Catch block: `catch (e) { notify.fromError(e) }` thay vì parse tay.
- [ ] **Step 4**: Lint rule (ESLint custom): warn khi gặp `toast.error('literal')` hoặc `toast.success('literal')` → khuyến nghị dùng `notify.show`.

### Task 5.2: Migrate stores

**Files:** `frontend/src/stores/*.ts`.

- [ ] **Step 1**: Stores hiện đang set `error.value = e.message` — chuyển sang lưu `lastError: ApiError` để view có thể `notify.fromError(store.lastError)`.

---

## Phase 6 — Deprecation + Cleanup

### Task 6.1: Xoá legacy

**Files:**
- `assetcore/utils/helpers.py` — xoá `_err/_ok` (đã re-export ở Phase 0; sau Phase 4 không còn ai gọi trực tiếp).
- `assetcore/services/shared/constants.py` — xoá `ErrorCode` class (đã re-export).

- [ ] **Step 1**: Grep `from assetcore.utils.helpers import _err` → phải = 0.
- [ ] **Step 2**: Grep `from assetcore.services.shared.constants import ErrorCode` → phải = 0.
- [ ] **Step 3**: Xoá block code, run full test suite.

### Task 6.2: Cập nhật CLAUDE.md + docs

**Files:**
- `CLAUDE.md` §15 (Code Style)
- `docs/imm-00/04_Backend_Design.md` và tương đương

- [ ] **Step 1**: Thêm rule vào CLAUDE.md:

```markdown
### Notification & Error
- **Bắt buộc**: BE dùng `nthrow(MSG.XXX, **ctx)`; KHÔNG dùng `frappe.throw()` bare.
- **Bắt buộc**: FE dùng `notify.show({code: MSG.XXX, ctx})` hoặc `notify.fromError(e)`; KHÔNG dùng `toast.error('literal string')`.
- Thêm mã mới: sửa `utils/messages.py` → `npm run gen:messages` → commit cả 2 file.
- Quy chuẩn ngôn ngữ: §5 docs/res/frameworks/miyano-error-framework.md.
```

- [ ] **Step 2**: Update sample pattern trong mỗi `docs/imm-XX/04_Backend_Design.md`.

### Task 6.3: Lint guard (CI)

**Files:**
- `.eslintrc` / `eslint.config.js`
- `pyproject.toml` (ruff custom rule hoặc grep-based pre-commit)

- [ ] **Step 1**: ESLint custom rule `no-hardcoded-toast`: pattern `toast\.(success|error|warning|info)\(['"`]` → error.
- [ ] **Step 2**: Pre-commit grep guard: `git diff --cached --name-only | xargs grep -nE "frappe\.throw\(['\"]" && exit 1`.
- [ ] **Step 3**: Whitelist legitimate uses (vd: `utils/notify.py:nthrow_in_hook` được phép gọi `frappe.throw`).

---

## Rollout & Verification

### Strategy

- **Phase 0-2**: 1 PR — foundation (helper hợp nhất + registry + composable). KHÔNG migrate gì.
- **Phase 3**: 1 PR — seed messages (BA review nội dung trước khi merge).
- **Phase 4**: N PR — mỗi module 1 PR, có thể parallel.
- **Phase 5**: M PR — mỗi module FE 1 PR.
- **Phase 6**: 1 PR cuối — cleanup + lint guard.

### Verification per phase

| Phase | Verification |
|---|---|
| 0 | Existing test suite green; grep duplicate helper = 0 |
| 1 | New `test_notification_framework.py` green; sample API response có envelope mở rộng |
| 2 | Unit test `useNotify.spec.ts` green; manual smoke: throw `ApiError` → toast hiện đúng template |
| 3 | Test `test_all_messages_have_required_fields` green; BA approval comment trên PR |
| 4 | Per-module `bench --site assetcore.local run-tests --app assetcore --module assetcore.tests.test_immXX` green; Playwright smoke per module |
| 5 | Manual UAT per module; visual regression trên `notify` toast (không spam, severity đúng màu) |
| 6 | Lint guard fail nếu intentionally add `frappe.throw('literal')` trong PR mới |

### Rollback

- Mỗi PR self-contained; rollback bằng `git revert`.
- Phase 4-5 chia nhỏ → blast radius mỗi module độc lập.
- Phase 0 (hợp nhất helper) là rủi ro cao nhất → cần full test suite + 1 ngày soak trên staging.

---

## Open Questions

1. **Doctype hook bypass**: `frappe.throw` trong doctype `validate()` không đi qua `_handle` — chấp nhận adapter `nthrow_in_hook` (Phase 4.14 step 1) hay tạo Frappe exception subclass (step 2)? **Đề xuất**: adapter trước (đơn giản); subclass khi cần phong phú hơn.
2. **i18n**: Khi nào move sang `vue-i18n` thật (giai đoạn 3)? Hiện `messages.ts` đã là dict — chỉ cần wrap thêm 1 lớp `t(code, ctx)` đọc theo locale. Plan này KHÔNG cover.
3. **`Error Registry` doctype**: BA có cần edit live không? Nếu **có** trong 6 tháng tới → kế hoạch giai đoạn 2 (doctype + Redis cache + import từ `messages.py` initial). Nếu **không** → cứ giữ code-first.
4. **Success notifications từ BE**: response `_ok({data, notify: {code, ctx}})` có phù hợp pattern hiện tại không, hay BE chỉ trả data và FE tự quyết notify? **Đề xuất**: hybrid — BE chỉ trả `notify` khi muốn ép message (vd: "Đã gửi email tới 5 NCC"); còn lại FE tự gọi `notify.show({code: MSG.IMM04_SAVE_SUCCESS})` sau khi API thành công.

---

## Estimated effort

| Phase | Effort | Người |
|---|---|---|
| 0 | 0.5 ngày | 1 BE |
| 1 | 2 ngày | 1 BE |
| 2 | 2 ngày | 1 FE |
| 3 | 2-3 ngày | 1 BA + 1 BE |
| 4 | 5-7 ngày | 2 BE parallel |
| 5 | 5-7 ngày | 2 FE parallel |
| 6 | 1 ngày | 1 BE + 1 FE |
| **Tổng** | **~18-23 ngày** | 2-3 dev |

---

## Implementation status (2026-05-25)

### ✅ Done — Phase 0–2 (foundation + FE wiring + demo)

| Phase | File(s) | Note |
|---|---|---|
| 0.1 | `assetcore/utils/helpers.py` | `_err/_ok` re-export from `response.py`. `_parse_json` + email helpers giữ tại helpers.py |
| 0.2 | `assetcore/utils/response.py`, `assetcore/services/shared/constants.py`, `frontend/src/api/errors.ts`, `frontend/src/api/README.md` | `ErrorCode` hợp nhất vào `response.py`, BUSINESS_RULE đổi value `"BUSINESS_RULE_VIOLATION"` → `"BUSINESS_RULE"`, FE sync |
| 1.1 | `assetcore/utils/messages.py` | 32 entries seed (SYS / AUTH / VAL / BIZ / UI / IMM04 / IMM09). MSG class + MESSAGES dict + lookup_message + format_message |
| 1.2 | `assetcore/services/shared/errors.py`, `assetcore/utils/notify.py` | ServiceError thêm `context`+`message_code` (backwards-compat); `nthrow(MSG.XXX, **ctx)`, `nthrow_in_hook(MSG.XXX, **ctx)` cho DocType hook, `render()` cho composer |
| 1.3 | `assetcore/utils/response.py` | `_err()` thêm kwargs `message_code`, `context`, `action_hint`, `severity`, `title` |
| 1.3b | `assetcore/utils/api_handler.py` | NEW shared `handle()` + `parse_json()`. Existing per-api `_handle()` chưa migrate (incremental Phase 4). IMM-04 `_handle` đã hydrate message_code làm reference impl |
| 1.4 | `scripts/gen_fe_messages.py`, `frontend/src/locales/messages.ts`, `frontend/src/locales/messages.types.ts`, `frontend/package.json` | AST-parse generator (không cần Frappe runtime). `npm run gen:messages` |
| 2.1 | `frontend/src/api/errors.ts` | ApiError thêm `messageCode/context/actionHint/severity/title`. Backwards-compat constructor overload |
| 2.2 | `frontend/src/api/helpers.ts`, `frontend/src/api/axios.ts` | unwrap() trong helpers hydrate ApiError từ MESSAGES; axios interceptor 417/422 `makeBusinessRuleError()` resolve registry |
| 2.3 | `frontend/src/composables/useNotify.ts`, `frontend/src/composables/useToast.ts`, `frontend/src/components/common/ToastContainer.vue` | useNotify.show/fromError/fromOk/confirm; toast type thêm title+actionHint render |
| 2.4 | `frontend/src/App.vue` | onErrorCaptured + unhandledrejection → notify.fromError |
| 2.5 | `frontend/src/composables/useModal.ts`, `frontend/src/components/common/NotificationModal.vue` | Singleton modal queue, alert/confirm. Mount trong App.vue. Critical severity tự route sang modal |
| 1-demo | `assetcore/services/imm04.py`, `assetcore/api/imm04.py` | `get_form_context()` migrate sang `nthrow(MSG.IMM04_NOT_FOUND, name=...)`. `_handle()` IMM-04 hydrate envelope đầy đủ |

### Test evidence

```
bench --site miyano run-tests --module assetcore.tests.test_notification_framework
→ Ran 14 tests in 0.158s. OK (0 fail).

bench --site miyano run-tests --module assetcore.tests.test_imm04
→ Ran 31 tests in 0.175s. OK (0 fail) — no regression sau khi migrate get_form_context.

cd frontend && npm run typecheck
→ 0 errors.

cd frontend && npm run lint
→ 0 errors (lint warnings là pre-existing cosmetic).
```

### 🚧 Còn lại

| Phase | Task | Hiện trạng |
|---|---|---|
| 3 | Seed full message catalog từ 197+ `frappe.throw` + 150+ `toast.*` literals | Pending — cần BA review nội dung |
| 4 | Migrate per-module BE bare calls (`services/imm04..imm16.py` + doctypes) | Chỉ IMM-04 `get_form_context` đã migrate làm reference |
| 5 | Migrate FE hardcoded toast → notify.show | Pending — cần đi từng view |
| 6 | Deprecation cleanup + CLAUDE.md guard + ESLint lint rule | Pending |

### Notes for next pickup

- `nthrow_in_hook` đã sẵn sàng cho DocType validate/on_submit migration — set `frappe.local.response["message_code"]` để axios `makeBusinessRuleError()` hydrate envelope khi 417 throw.
- `frontend/src/locales/messages.ts` là GENERATED. Mọi thay đổi message bắt buộc đi qua `assetcore/utils/messages.py` + `npm run gen:messages`. Add CI check `git diff --exit-code` để chống drift.
- Phase 4-5 hoàn toàn incremental — mỗi module migrate trong PR riêng, không cần coordinate.
