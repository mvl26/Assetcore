# API & Error Handling Convention

Pipeline thống nhất: **BE envelope → Axios interceptor → ApiError → useApi → Toast / fieldErrors**.

## 1. Backend (Python)

Mọi handler whitelist dùng `_ok` / `_err` từ `assetcore/utils/response.py`.

```python
from assetcore.utils.response import _ok, _err, ErrorCode
from assetcore.utils.api_endpoint import api_endpoint

@frappe.whitelist()
@api_endpoint  # tự catch DoesNotExistError / PermissionError / ValidationError → _err code chuẩn
def update_pm_schedule(name: str):
    if not frappe.db.exists("PM Schedule", name):
        return _err(_("Lịch PM không tồn tại"), ErrorCode.NOT_FOUND)
    if not data.get("asset_ref"):
        return _err(_("Vui lòng chọn thiết bị"),
                    ErrorCode.VALIDATION_ERROR,
                    fields={"asset_ref": "Bắt buộc"})
    # ...
    return _ok({"name": doc.name})
```

**Envelope chuẩn:**

```json
// success
{"success": true, "data": {...}}

// error
{"success": false, "error": "<message tiếng Việt>",
 "code": "BUSINESS_RULE_VIOLATION", "http_status": 422,
 "fields": {"asset_ref": "Bắt buộc"}}
```

## 2. Error codes

| Code | HTTP | Nghĩa | UX gợi ý |
|---|---|---|---|
| `VALIDATION_ERROR` | 400 | Input không hợp lệ (kèm `fields`) | toast warning + highlight field |
| `UNAUTHORIZED` | 401 | Chưa login / session hết | redirect /login (axios tự xử lý) |
| `FORBIDDEN` | 403 | Thiếu role | toast warning, không redirect |
| `NOT_FOUND` | 404 | Bản ghi không tồn tại | toast error, route 404 page nếu là detail view |
| `CONFLICT` | 409 | Trùng lặp / state conflict | toast warning |
| `BUSINESS_RULE_VIOLATION` | 422 | Vi phạm nghiệp vụ (workflow, locked, ...) | toast warning, giữ form |
| `INTERNAL_ERROR` | 500 | Lỗi server | toast error, có thể "Tải lại" |
| `NETWORK_ERROR` | 0 | Mất kết nối | toast error |

## 3. Frontend

### Pattern khuyến nghị (mọi view)

```ts
import { useApi } from '@/composables/useApi'

const apiCall = useApi()
const fieldErrors = ref<Record<string, string>>({})

async function save() {
  const ok = await apiCall.run(
    () => createPmSchedule(form.value),
    {
      successMessage: 'Đã tạo lịch PM',
      onFieldError: (fields) => { fieldErrors.value = fields },
    },
  )
  if (ok) await load()
}
```

`useApi.run`:
- Tự bật toast: `success` (xanh), business (vàng), system (đỏ).
- 401/403 đã được axios redirect — không spam toast.
- Trả `null` khi lỗi → caller chỉ cần `if (result) { ... }`.
- `lastError` cho phép lấy chi tiết: `apiCall.lastError.value?.code`.

### Field-level errors trong form

```vue
<SmartSelect v-model="form.asset_ref" :has-error="!!fieldErrors.asset_ref" />
<p v-if="fieldErrors.asset_ref" class="text-xs text-red-600">{{ fieldErrors.asset_ref }}</p>
```

### Khi nào tự `try/catch`?

Chỉ khi cần override default UX (vd: silent error, fallback inline):

```ts
import { ApiError, ErrorCode } from '@/api/errors'

try {
  await getAsset(name)
} catch (e) {
  if (e instanceof ApiError && e.code === ErrorCode.NOT_FOUND) {
    router.push({ name: 'NotFound' })
  } else {
    throw e // để App.vue unhandledrejection toast
  }
}
```

## 4. Loading & Blank-page protection

| Tình huống | Cơ chế |
|---|---|
| Đang load list | `<SkeletonLoader v-for="i in 5" />` thay placeholder text |
| Load fail | block "⚠️ + Thử lại" + toast |
| List rỗng | empty state với CTA (`+ Thêm`, `Xóa bộ lọc`) |
| Render component throw | `RouteErrorBoundary` (App.vue) — không blank page |
| URL không match route | `:pathMatch(.*)*` → `NotFoundView` |
| Promise unhandled | `window.unhandledrejection` (App.vue) → toast |

## 5. Migrate legacy code

- `alert(err.message)` → `toast.error(...)` hoặc dùng `useApi`.
- `err.value = ...` inline → giữ cho lỗi validate client-side; lỗi từ BE để `useApi` xử lý.
- `catch (e) { console.error(e) }` silent → throw lại hoặc dùng `useApi`.
