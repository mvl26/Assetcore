# Notification Contract — chuẩn thông báo BE → FE (BẮT BUỘC mọi module)

> Nguồn gốc: Sprint chuẩn hoá thông báo 2026-05-29 (IMM-04/05/08/09/11/12).
> **RED đã quan sát:** trước sprint, MỌI module raise `frappe.throw(_(...))` / `ServiceError(ErrorCode.X, "tiếng Việt")` thô → leak message tiếng Anh/kỹ thuật ra UI, FE không có pipeline thông báo thống nhất, thao tác thành công không phản hồi. Rule này tồn tại để module MỚI không tái tạo lỗi đó.
>
> **Quy tắc vàng:** user tương tác → BE raise/return → envelope chuẩn (có `message_code` + `severity`) → FE hydrate từ registry → 1 component popup/toast duy nhất. KHÔNG có nhánh nào bỏ qua chuỗi này.

---

## 0. Iron Law

```
KHÔNG hardcode câu chữ hiển thị cho user trong service/controller/view.
Mọi message đi qua MSG.<CODE> trong registry duy nhất: assetcore/utils/messages.py
```

- Service KHÔNG gọi `frappe.throw(_("..."))` trực tiếp.
- Service KHÔNG `raise ServiceError(ErrorCode.X, "câu tiếng Việt literal")`.
- View Vue KHÔNG `toast.error("chuỗi literal")` cho lỗi nghiệp vụ.
- Vi phạm "letter" = vi phạm "spirit": message đúng tiếng Việt nhưng không qua `MSG` vẫn là vi phạm (không versioned, BA không sửa được 1 chỗ, không có `severity`/`action_hint` nhất quán).

---

## 1. Kiến trúc chuỗi (đọc 1 lần, nhớ mãi)

```
service raise nthrow(MSG.X, **ctx)        ── ServiceError(message_code, http_status, context)
        │
  api: return handle(svc.fn, ...)         ── utils/api_handler.handle → _service_error_to_envelope
        │                                     hydrate {message, code, http_status, message_code,
        │                                     context, action_hint, severity, title} từ registry
        ▼
  DocType hook raise nthrow_in_hook(MSG.X) ── frappe.ValidationError (HTTP 417) +
        │                                     frappe.local.response["message_code"/"context"]
        ▼
  FE axios/helpers → ApiError (messageCode, context, severity, title, actionHint)
        │
  store catch → _captureError(e) → lastApiError
        │
  view: success → notify.show({code, ctx}) ; fail → notify.fromError(store.lastApiError)
        ▼
  useNotify → severity routing: success/info/warning/error → toast ; critical → modal
```

---

## 2. BE — registry (`assetcore/utils/messages.py`)

Mỗi mã = 1 const trong `class MSG` + 1 entry trong `MESSAGES`:

```python
class MSG:
    IMM09_SLA_EXPIRED = "IMM09-SLA-EXPIRED"          # snake attr → kebab string

MESSAGES = {
    MSG.IMM09_SLA_EXPIRED: {
        "title": "Đã quá hạn SLA",                    # ngắn, danh từ
        "template": "Lệnh sửa chữa {name} đã vượt thời hạn SLA.",  # {var} = context key
        "action_hint": "Liên hệ quản lý để gia hạn hoặc ưu tiên xử lý.",
        "severity": "warning",   # error|warning|info|success|critical
        "http_status": 422,      # quyết định ErrorCode bucket qua _HTTP_TO_BUCKET
    },
}
```

Quy chuẩn nội dung (miyano-error-framework §5): **Chủ thể + Hậu quả + Hành động** (hành động ở `action_hint`). Không từ kỹ thuật ("ValidationError", "Failed", stack trace). Không đổ lỗi user.

Naming `<MODULE>-<KIND>[-<SUBKIND>]`: `SYS-*`, `AUTH-*`, `VAL-*`, `BIZ-*`, `UI-*`, `IMM<NN>-*`, domain (`IMPORT-*`…).

**Sau khi thêm/sửa mã → BẮT BUỘC regen FE i18n:**
```bash
python scripts/gen_fe_messages.py   # parse messages.py → frontend/src/locales/messages.ts
```
Commit CẢ `messages.py` + `messages.ts` cùng lúc. Quên regen = FE render `[var]` / fallback SYS-500.

`http_status` → ErrorCode bucket (xem `notify._HTTP_TO_BUCKET`): 400→INVALID_PARAMS, 401→UNAUTHORIZED, 403→FORBIDDEN, 404→NOT_FOUND, 409→CONFLICT, 422→BUSINESS_RULE, 429→RATE_LIMITED, 500→INTERNAL.

---

## 3. BE — service layer raise (`services/immXX.py`)

```python
from assetcore.utils.notify import nthrow
from assetcore.utils.messages import MSG

def submit_result(*, name: str) -> dict:
    doc = repo.get(name)
    if not doc:
        nthrow(MSG.IMM11_NOT_FOUND, name=name)        # 404 bucket tự suy
    if doc.status != "In Progress":
        nthrow(MSG.IMM11_BAD_STATE, name=name, status=doc.status)
    ...
```

- `nthrow(MSG.X, **ctx)`: `ctx` vừa render vào template, vừa propagate xuống FE qua `context` (để FE i18n hoá lại). Đặt tên ctx khớp `{var}` trong template.
- `error_code=` override bucket chỉ khi mapping HTTP→bucket mặc định không khớp UX (hiếm).

---

## 4. BE — DocType hook raise (`doctype/<x>/<x>.py`)

Hook (`validate`/`on_submit`/`before_insert`…) chạy NGOÀI api layer → `ServiceError` sẽ thành HTTP 500. Dùng adapter:

```python
from assetcore.utils.notify import nthrow_in_hook
from assetcore.utils.messages import MSG

def validate(self):
    if not self.attachments:
        nthrow_in_hook(MSG.IMM05_FILE_REQUIRED)        # → frappe.ValidationError (417)
```

`nthrow_in_hook` tự gắn `message_code`/`context` vào `frappe.local.response` → FE vẫn hydrate được.

---

## 5. BE — API layer (`api/immXX.py`)

```python
from assetcore.utils.api_handler import handle, parse_json

@frappe.whitelist()
def list_things(filters: str = "", page: int = 1, page_size: int = 20):
    return handle(svc.list_things, parse_json(filters, default={}), page=int(page), page_size=int(page_size))

@frappe.whitelist(methods=["POST"])
def do_action(name: str, payload: str = ""):
    return handle(svc.do_action, name, payload=parse_json(payload, default={}))
```

- Dùng `handle`/`parse_json` SHARED từ `utils/api_handler` — **KHÔNG** copy/định nghĩa `_handle`/`_parse_json`/`_err` cục bộ (anti-pattern cũ, nay deprecated).
- GET param optional kiểu JSON → default `str = ""` (KHÔNG `"{}"` bắt buộc) để tránh HTTP 417 khi client bỏ trống (LL-BE-1).
- `handle` chỉ bắt `ServiceError`; system exception bubble lên Frappe global handler (log + 500 đúng cách).

---

## 6. FE — store (`stores/immXX.ts`)

```ts
import { ApiError, toApiError } from '@/api/errors'

const lastApiError = ref<ApiError | null>(null)

/** Ghi nhận lỗi: vừa set banner string (legacy) vừa giữ ApiError đã hydrate (notify). */
function _captureError(e: unknown): void {
  const err = toApiError(e)
  lastApiError.value = err
  error.value = err.message
}

async function doAction(payload): Promise<Result | null> {
  try { return await apiDoAction(payload) }
  catch (e: unknown) { _captureError(e); return null }   // trả null khi fail
}

return { /* ...state */ lastApiError, _captureError, doAction }
```

Mọi mutating action `catch (e) { _captureError(e); return null }`. Read action cũng `_captureError` (banner inline). KHÔNG nuốt lỗi (`catch {}`) trừ side-effect non-blocking (vd refetch audit tab).

---

## 7. FE — view (`views/.../XDetailView.vue`)

```ts
import { useNotify } from '@/composables/useNotify'
import { MSG } from '@/i18n/messages'
const notify = useNotify()

async function onSubmit() {
  const ok = await store.submit(props.id)
  if (ok) notify.show({ code: MSG.IMM11_SUBMIT_SUCCESS, ctx: { name: props.id } })
  else    notify.fromError(store.lastApiError)
}
```

- Success → `notify.show({ code: MSG.*, ctx })`. Generic CRUD dùng `MSG.UI_SAVE_SUCCESS`/`UI_DELETE_SUCCESS` với `ctx.entity`.
- Fail → `notify.fromError(store.lastApiError)` (KHÔNG `toast.error(string)`).
- FE-only pre-check (vd thiếu file trước khi gửi) → cũng `notify.show({ code: MSG.* })`, KHÔNG `toast.warning("literal")`.
- Flow form nặng (field-error) có thể dùng `useApi().run(fn, { successMessage, onFieldError })` thay cho store pattern — vẫn route qua `notify.fromError` mặc định.

---

## 8. DONE checklist — module MỚI (BẮT BUỘC tick đủ trước khi gọi "xong")

- [ ] Mọi `frappe.throw(_(...))` / `ServiceError(ErrorCode.X, "literal")` trong service đã thành `nthrow(MSG.*)`. Verify: `grep -nE "frappe\.throw|ServiceError\(ErrorCode" services/immXX.py` → 0 (trừ re-raise có message_code).
- [ ] Mọi raise trong DocType hook = `nthrow_in_hook(MSG.*)`.
- [ ] `api/immXX.py` import `handle, parse_json` từ `utils/api_handler`; KHÔNG còn `_handle`/`_parse_json` cục bộ.
- [ ] GET optional JSON param default `str = ""`.
- [ ] Đã thêm `MSG.IMMxx_*` + MESSAGES entry; chạy `scripts/gen_fe_messages.py`; commit kèm `messages.ts`.
- [ ] Store có `lastApiError` + `_captureError`; mọi action catch → `_captureError`.
- [ ] Mọi view success → `notify.show(MSG.*)`, fail → `notify.fromError(store.lastApiError)`; 0 `toast.*("literal")` cho nghiệp vụ.
- [ ] `docs/imm-XX/05_API_Specification.md` có §11 Notification Contract (envelope + bảng mã + severity rule).
- [ ] Test: 1 case assert envelope mang `message_code` + `severity` đúng (xem `test_imm11.py::TestImm11NotificationContract`).
- [ ] FE: `npx vue-tsc --noEmit` 0 lỗi; `npx vitest run` xanh.

---

## 9. Bẫy đã sụp (KHÔNG lặp lại)

| # | Bẫy | Hậu quả | Cách đúng |
|---|-----|---------|-----------|
| N-1 | Wrapper bắt `frappe.ValidationError` rồi bọc `ServiceError(VALIDATION, str(e))` | rớt `message_code`/`severity` → FE không hydrate title/action_hint | Trong wrapper re-`nthrow(MSG.IMMxx_*)` để registry hydrate đầy đủ |
| N-2 | Sửa BE giữa phiên rồi eval FE ngay → `AttributeError: MSG has no attribute X` | gunicorn worker chạy **bytecode cũ**, KHÔNG phải lỗi code | `bench --site miyano restart` hoặc `kill -HUP <gunicorn worker>` TRƯỚC khi Playwright/FE eval (LL-TEST-12) |
| N-3 | Thêm mã vào `messages.py` nhưng quên `gen_fe_messages.py` | FE render `[var]` hoặc fallback SYS-500 | Luôn regen + commit `messages.ts` cùng commit |
| N-4 | GET optional param default `"{}"` | HTTP 417 khi client bỏ trống | default `str = ""`, `parse_json(..., default={})` |
| N-5 | `toast.warning("literal")` cho FE-only pre-check | thoát contract, không versioned | `notify.show({ code: MSG.* })` |
| N-6 | `catch {}` nuốt lỗi trong store action | user không nhận thông báo lỗi | `_captureError(e)` rồi `return null` |

---

## 10. Live examples (copy từ đây)

- BE service raise: `assetcore/services/imm11.py`, `imm12.py`
- BE hook raise: `assetcore/assetcore/doctype/imm_asset_calibration/imm_asset_calibration.py`
- BE api shared handle: `assetcore/api/imm09.py`, `imm11.py`
- Registry: `assetcore/utils/messages.py` · Adapter: `assetcore/utils/notify.py` · Handler: `assetcore/utils/api_handler.py`
- FE store: `frontend/src/stores/imm11.ts` · view: `frontend/src/views/calibration/CalibrationDetailView.vue`
- FE pipeline: `composables/useNotify.ts`, `useApi.ts` · registry: `i18n/messages.ts`
- Test contract: `assetcore/tests/test_imm11.py::TestImm11NotificationContract`, `test_notification_framework.py`
