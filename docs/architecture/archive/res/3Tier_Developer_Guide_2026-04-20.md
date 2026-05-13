# AssetCore — 3-Tier Developer Guide

**Ngày:** 2026-04-20
**Đối tượng:** Developer tiếp tục refactor IMM-00/04/05/08/09 + module mới.
**Tham chiếu:** `docs/res/Architecture_3Tier_Refactor_2026-04-20.md`

Đã có pilot hoàn chỉnh cho **IMM-11 Calibration** và **Auth**. Tài liệu này là checklist + pattern để áp dụng cho các module còn lại.

---

## 1. Nguyên tắc vàng

1. **Một import, một tầng.** File ở tầng cao hơn được import từ tầng thấp hơn — KHÔNG ngược lại.
   - `api/*` import từ `services/*` ✅
   - `services/*` import từ `repositories/*` ✅
   - `services/*` import từ `services/shared/*` ✅
   - `repositories/*` chỉ import `frappe` và `base` ✅
   - `api/*` KHÔNG bao giờ import `frappe.db` / `frappe.get_doc` ❌
   - `services/*` KHÔNG bao giờ return JSON envelope ❌

2. **Không hardcode string.** Mọi role, status, error code phải đến từ `services.shared.constants`.

3. **Raise thay vì return.** Service raise `ServiceError(code, msg)`. API layer bắt và convert thành `_err`.

4. **Transaction ở service.** Controller gọi service; service gọi `frappe.db.commit()` tại ranh giới use case.

---

## 2. Template chuẩn cho 1 module

### 2.1 `services/shared/constants.py` — thêm enum nếu cần

```python
class PMStatus:
    DRAFT = "Draft"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    ACTIVE_STATUSES = (SCHEDULED, IN_PROGRESS)
```

### 2.2 `repositories/<module>_repo.py`

```python
from .base import BaseRepository

class PMScheduleRepo(BaseRepository):
    DOCTYPE = "PM Schedule"

class PMWorkOrderRepo(BaseRepository):
    DOCTYPE = "PM Work Order"
```

Đã có sẵn 8 file repo cho các DocType chính — [repositories/](../../assetcore/repositories/).

### 2.3 `services/<module>.py` — Tier 2

```python
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.repositories.pm_repo import PMWorkOrderRepo
from assetcore.repositories.asset_repo import AssetRepo

def get_work_order(name: str) -> dict:
    doc = PMWorkOrderRepo.get(name)
    if not doc:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy WO '{name}'")
    return doc.as_dict()

def create_work_order(*, asset: str, scheduled_date: str, ...) -> dict:
    if not AssetRepo.exists(asset):
        raise ServiceError(ErrorCode.NOT_FOUND, "Thiết bị không tồn tại")
    doc = PMWorkOrderRepo.create({...})
    return {"name": doc.name, "status": doc.status}

def list_work_orders(filters: dict, *, page=1, page_size=20) -> dict:
    rows, pg = PMWorkOrderRepo.list(
        filters=filters, fields=[...],
        order_by="scheduled_date desc",
        page=page, page_size=page_size,
    )
    return {"data": rows, "pagination": pg}
```

### 2.4 `api/<module>.py` — Tier 1

```python
from assetcore.services import pm_service as svc  # hoặc services.imm08 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.utils.helpers import _err, _ok

def _handle(fn, *args, **kwargs):
    try:
        return _ok(fn(*args, **kwargs))
    except ServiceError as e:
        return _err(e.message, e.code)

@frappe.whitelist()
def get_pm_work_order(name: str) -> dict:
    return _handle(svc.get_work_order, name)

@frappe.whitelist()
def create_pm_work_order(asset: str, scheduled_date: str, ...) -> dict:
    return _handle(svc.create_work_order,
                   asset=asset, scheduled_date=scheduled_date, ...)
```

---

## 3. Checklist refactor 1 module

- [ ] Audit file `api/<module>.py` hiện tại — liệt kê tất cả `@frappe.whitelist()` endpoint.
- [ ] Liệt kê mọi `frappe.db.*` / `frappe.get_doc` / `frappe.new_doc` / hardcoded role/status.
- [ ] Kiểm `services/<module>.py` đã có chưa; nếu không có → tạo.
- [ ] Di chuyển tất cả logic ORM từ API sang service.
- [ ] Replace raw literals bằng enum trong `services.shared.constants`.
- [ ] Replace role check bằng `require_role()` / `has_any_role()`.
- [ ] Service dùng repository thay vì `frappe.db.*`.
- [ ] Raise `ServiceError` với `ErrorCode.*` + message tiếng Việt.
- [ ] API endpoint bọc gọn bằng `_handle()` helper.
- [ ] Chạy regression test module đó (UAT script hiện có hoặc bench execute).
- [ ] Cập nhật FE `src/api/<module>.ts` nếu response shape đổi (hiếm khi).

---

## 4. Ví dụ đầy đủ — IMM-11 (đã refactor, dùng làm reference)

- Constants: [services/shared/constants.py](../../assetcore/services/shared/constants.py)
- Repositories: [repositories/calibration_repo.py](../../assetcore/repositories/calibration_repo.py)
- Service: [services/imm11.py](../../assetcore/services/imm11.py)
- API: [api/imm11.py](../../assetcore/api/imm11.py)

Thay đổi đo lường được:
- `frappe.db.*` calls trong `api/imm11.py`: **15 → 0**
- Raw status literals trong service: **12 → 0** (dùng enum)
- Lines trong `api/imm11.py`: **~270 → 153** (-43%)
- Duplicate pagination block: **2 → 0** (dùng `paginate` trong repo)

---

## 5. Frontend pattern

### 5.1 Role constants — dùng `@/constants/roles`

```ts
// router/index.ts
import { ROLES_CREATE, ROLES_APPROVE } from '@/constants/roles'

{ path: '/pm/new', meta: { requiredRoles: ROLES_CREATE } }

// component
import { Roles } from '@/constants/roles'
<button v-permission="Roles.OPS_MANAGER">Duyệt</button>
```

### 5.2 API client — dùng helper `frappeGet/frappePost`

```ts
// src/api/pm.ts
import { frappeGet, frappePost } from './helpers'

const BASE = '/api/method/assetcore.api.imm08'

export function listPMWorkOrders(filters = {}, page = 1, page_size = 20) {
  return frappeGet(`${BASE}.list_pm_work_orders`, { filters: JSON.stringify(filters), page, page_size })
}
```

### 5.3 Error handling — envelope đã unwrap

`frappeGet/Post` tự unwrap `{success: false, error, code}` → throw Error. Component chỉ cần:
```ts
try {
  const data = await listPMWorkOrders()
} catch (e: unknown) {
  err.value = (e as Error).message
}
```

---

## 6. Thứ tự refactor khuyến nghị

| Thứ tự | Module | Lý do | Ước tính |
|---|---|---|---|
| ✅ 1 | IMM-11 | Nhỏ, vừa build xong (pilot) | Xong |
| ✅ 2 | Auth | Nhỏ, độc lập | Xong |
| 3 | IMM-05 Documents | `services/imm05.py` thiếu hẳn, logic nằm trong API | 2-3 ngày |
| 4 | IMM-09 Repair | Cross-module với IMM-11 | 3-4 ngày |
| 5 | IMM-08 PM | Integration với IMM-04 | 3-4 ngày |
| 6 | IMM-04 Commissioning | Lớn nhất, workflow 11 states | 1 tuần |
| 7 | IMM-00 Foundation | Chạm nhiều controller, refactor cuối | 1 tuần |

---

## 7. Điểm cần để ý khi refactor

### 7.1 Controller DocType (`assetcore/doctype/<dt>/<dt>.py`)

- `validate()`: giữ check trường nội tại (required, format).
- `on_submit()` / `on_update()`: gọi service, không tạo doc khác trực tiếp.
- Nếu cần `frappe.throw(_("..."))` — chấp nhận (Frappe pattern); nhưng **nếu message là business rule** thì convert sang `ServiceError` và raise từ service.

### 7.2 Scheduler jobs

Scheduler trong `hooks.py::scheduler_events` gọi trực tiếp function trong `services/<module>.py`. Giữ pattern này — service function signature: không arg hoặc arg đơn giản, return số/None.

### 7.3 Hook doc_events

Các hook (`Asset Commissioning.on_submit`) gọi `services.imm11.create_calibration_schedule_from_commissioning` — giữ pattern này.

### 7.4 Transaction boundary

- Repository **không** gọi `frappe.db.commit()`.
- Service gọi `frappe.db.commit()` **tại ranh giới use case** (sau khi hoàn thành 1 action nghiệp vụ atomic).
- API không gọi `commit()`.

### 7.5 `ignore_permissions`

- Repository mặc định `ignore_permissions=True` (assumption: service đã check role qua `require_role`).
- Nếu endpoint trả dữ liệu read-only cho user thường → gọi repo với `ignore_permissions=False`.

---

## 8. Test pattern

### 8.1 Unit test cho service (mock repository)

```python
def test_create_schedule_validates_asset_exists(mocker):
    mocker.patch.object(AssetRepo, "exists", return_value=False)
    with pytest.raises(ServiceError) as exc:
        imm11.create_schedule(asset="FAKE", ...)
    assert exc.value.code == ErrorCode.NOT_FOUND
```

### 8.2 Integration test cho API (dùng bench)

```bash
bench --site miyano execute assetcore.api.imm11.list_calibration_schedules
bench --site miyano execute assetcore.api.imm11.get_calibration --kwargs '{"name":"CAL-2026-00001"}'
```

---

## 9. Ownership & Review

- Mỗi module refactor bằng 1 PR riêng.
- Checklist review:
  - [ ] `grep "frappe.db.get\|frappe.db.set\|frappe.get_doc\|frappe.new_doc" api/<module>.py` = 0 match.
  - [ ] Tất cả role strings dùng `Roles.*` constant.
  - [ ] Service raise `ServiceError` với `ErrorCode.*`.
  - [ ] UAT script module đó pass.
  - [ ] Diff TypeScript + FE không bị vỡ (`npx vue-tsc --noEmit`).

---

## 10. Khi có vấn đề

- Refactor làm vỡ endpoint → rollback PR, tìm root cause, chia nhỏ.
- ImportError circular giữa services: chuyển import xuống trong function (lazy).
- Test fail do mock: verify repo class method signature khớp với BaseRepository API.
- Performance regression: check N+1 (repo `list` trả tuple `(rows, pg)`, tránh call `list` trong loop).
