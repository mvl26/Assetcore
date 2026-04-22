# AssetCore — Audit & Đề xuất Kiến trúc 3-Tầng

**Ngày:** 2026-04-20
**Phạm vi:** Rà soát mức độ tuân thủ tài liệu trong `docs/res/` và đề xuất refactor sang kiến trúc phân lớp 3 tầng (Presentation → Business → Data Access).

---

## 1. Kết quả Audit — Mức độ Tuân thủ Tài liệu

### 1.1 Theo Module

| Module | BE/DocType | API | FE | Mức tuân thủ | Gap chính |
|---|---|---|---|---|---|
| **IMM-00** (Foundation) | 17/17 DocType ✅ | Service layer đầy đủ | 21 views + store | **95%** | Depreciation: FE có, BE chưa auto-compute; `rollup_asset_kpi` thiếu MTBF/compliance_pct |
| **IMM-04** (Commissioning) | 5/5 + Workflow 11 states ✅ | 22 endpoints | 6 views | **90%** | Print Format biên bản bàn giao chưa có; hook IMM-04→IMM-08 chưa fire |
| **IMM-05** (Documents) | 3/3 + Workflow 6 states ✅ | 14 endpoints | 4 views | **95%** | Thiếu `services/imm05.py` (logic nằm trong API); dashboard KPI component FE thiếu |
| **IMM-08** (PM) | 6/6 ✅ | 9 endpoints (mỏng) | 6 views | **88%** | Listener IMM-04→IMM-08 chưa active |
| **IMM-09** (Repair) | 4/4 ✅ | 12 endpoints | 7 views | **88%** | Post-repair calibration trigger sang IMM-11 chưa đủ |
| **IMM-11** (Calibration) | 3/3 ✅ | Đầy đủ CRUD | 4 views | **95%** *(sau sprint 2026-04-19)* | Đã verified Pass/Fail flow + Scheduler |
| **IMM-12** (Incident/CAPA) | Có DocType trong IMM-00 | Chưa có `api/imm12.py` | — | **40%** | Module chính thức chưa tách; chỉ tái sử dụng Incident Report + CAPA của IMM-00 |
| **Auth / User** | AC User Profile + approval fields ✅ | `api/auth.py` (5 endpoints) | RegisterView, ProfileView, UnauthorizedView, `v-permission` | **95%** *(sau sprint 2026-04-20)* | Email verification phase 2 |

### 1.2 Theo tài liệu

| Tài liệu | Thực tế khớp | Ghi chú |
|---|---|---|
| `AssetCore_DocTypes_Audit_2026-04-19.md` (34 DocType) | 34/34 ✅ | 100% |
| `BE_Readiness_Audit_2026-04-18.md` | ~90% | Thiếu: centralized constants, permission layer, depreciation |
| `IMM-00_Entity_Coverage_Analysis.md` | ~95% | |
| `IMM-00_UAT_Gap_Analysis.md` | ~80% | Một số UAT scenarios chưa có test tự động |
| `Frontend_Router_Navigation_Map.md` | ~95% | Routes khớp; thêm mới `/register`, `/profile`, `/unauthorized` |
| `Module_Business_Flows_2026-04-19.md` | ~90% | Flow IMM-04→IMM-08 chưa end-to-end |
| `Auth_Account_Design_2026-04-20.md` | 95% ✅ | Vừa implement |
| `Wave1_Foundation_Readiness_2026-04-19.md` | ~88% | |

### 1.3 Gap hệ thống lớn nhất

1. **API layer gọi thẳng `frappe.db.*`** — ~342 lần trong `api/*.py` → logic nghiệp vụ rò rỉ lên presentation layer.
2. **Duplicate constants & helper** — `_ok/_err` định nghĩa local mỗi file, role strings hardcode ở nhiều nơi, `NOT_FOUND` literal 50+ lần.
3. **Permission check rải rác** — 40+ endpoint tự check role bằng hardcoded set.
4. **Controller DocType chứa business logic phức tạp** — `pm_work_order.py`, `asset_repair.py` gọi 4-6 service + tạo doc trực tiếp trong `on_submit`.
5. **Pagination + filter copy-paste** — 4 file API lặp logic `(page-1)*page_size` + `ceil(total/page_size)`.

---

## 2. Kiến trúc Hiện tại (As-is)

```
┌─────────────────────────────────────────────────────────────────┐
│  FE (Vue 3)                                                     │
│  - Views, Components, Stores                                    │
│  - API clients (src/api/*.ts) — thin HTTP wrappers              │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST (/api/method/...)
┌────────────────────────▼────────────────────────────────────────┐
│  BE (Frappe)                                                    │
│                                                                 │
│  ┌──────────────────┐   ┌──────────────────┐                   │
│  │  api/*.py        │◄──┤  controllers     │  ← lỗi: controller │
│  │  @whitelist      │   │  (doctype/*.py)  │     gọi service + │
│  │  • parse input   │   │  validate+hook   │     tạo doc trực  │
│  │  • Frappe ORM ◄──┼───┤  on_submit gọi   │     tiếp          │
│  │    TRỰC TIẾP (!) │   │  service + ORM   │                   │
│  │  • check role    │   └──────────────────┘                   │
│  │    hardcode      │            │                             │
│  └────────┬─────────┘            │                             │
│           │                      │                             │
│           ▼                      ▼                             │
│  ┌──────────────────────────────────────┐                      │
│  │  services/imm*.py  — PARTIAL         │                      │
│  │  • imm00 đủ                          │                      │
│  │  • imm04, imm05 mỏng                 │                      │
│  │  • imm08, imm09, imm11 đủ            │                      │
│  └────────────────┬─────────────────────┘                      │
│                   │                                            │
│                   ▼                                            │
│  ┌──────────────────────────────────────┐                      │
│  │  Frappe ORM (MariaDB)                │                      │
│  └──────────────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

**Triệu chứng:**
- API layer "béo" (fat controller) — vừa parse, vừa validate, vừa gọi ORM, vừa check quyền.
- Services mỏng hoặc thiếu — logic phân tán giữa API + Controller + ad-hoc trong hook.
- Không có lớp trừu tượng truy cập dữ liệu — test phải mock Frappe toàn bộ.
- Permission/Role/Constants rò rỉ khắp nơi.

---

## 3. Kiến trúc Đích (To-be) — 3-Tầng

```
┌──────────────────────────────────────────────────────────────────┐
│ TIER 1 — PRESENTATION                                            │
│ ┌────────────────────────┐    ┌─────────────────────────────┐   │
│ │ Frontend (Vue 3)       │    │ Backend: api/*.py           │   │
│ │ • views, components    │    │ @whitelist endpoints ONLY   │   │
│ │ • stores (Pinia)       │───►│ • parse/validate input      │   │
│ │ • API clients          │    │ • gọi service → nhận result │   │
│ │ • router guards        │    │ • format _ok/_err          │   │
│ │ • v-permission         │    │ • KHÔNG gọi ORM, KHÔNG      │   │
│ │                        │    │   check role hardcode       │   │
│ └────────────────────────┘    └──────────────┬──────────────┘   │
└───────────────────────────────────────────────┼──────────────────┘
                                                ▼
┌──────────────────────────────────────────────────────────────────┐
│ TIER 2 — BUSINESS / SERVICE                                      │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ services/<module>.py — thuần business logic                 │  │
│ │ • Luật nghiệp vụ (BR-xx-yy)                                 │  │
│ │ • Orchestration: transition_asset_status, create_capa, ...  │  │
│ │ • Cross-module: imm04.release → imm08.create_pm_schedule   │  │
│ │ • NHẬN arguments tường minh, TRẢ dict/domain object         │  │
│ └──────────────────────────┬──────────────────────────────────┘  │
│                            │                                     │
│ ┌──────────────────────────┴──────────────────────────────────┐  │
│ │ services/shared/ — cross-cutting                            │  │
│ │ • constants.py   — ROLES, STATUS, ERROR_CODES               │  │
│ │ • permissions.py — is_admin(), require_role(), role_sets    │  │
│ │ • lifecycle.py   — audit/event helpers (đã có một phần)     │  │
│ └──────────────────────────┬──────────────────────────────────┘  │
└────────────────────────────┼─────────────────────────────────────┘
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│ TIER 3 — DATA ACCESS (REPOSITORY)                                │
│ ┌─────────────────────────────────────────────────────────────┐  │
│ │ repositories/<doctype>_repo.py — wrap Frappe ORM             │  │
│ │ • get_by_name(name) -> Doc | None                            │  │
│ │ • list(filters, pagination) -> (rows, total)                 │  │
│ │ • create(data) / update(name, patch) / delete(name)          │  │
│ │ • count(filters) / exists(name)                              │  │
│ │ • Transaction boundary rõ ràng                               │  │
│ └──────────────────────────┬──────────────────────────────────┘  │
│                            ▼                                     │
│                  Frappe ORM / MariaDB                            │
└──────────────────────────────────────────────────────────────────┘
```

### 3.1 Cấu trúc thư mục đề xuất

```
assetcore/
├── api/                       # Tier 1 — presentation
│   ├── auth.py
│   ├── imm00.py
│   ├── imm04.py
│   └── ...                    # CHỈ: whitelist + parse + gọi service
│
├── services/                  # Tier 2 — business
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── constants.py       # IMM_ROLES, STATUSES, ERROR_CODES
│   │   ├── permissions.py     # require_role(), has_any_role(), role_sets
│   │   ├── pagination.py      # đã có ở utils/ — move vào đây
│   │   └── errors.py          # ServiceError class + error codes
│   ├── imm00.py
│   ├── imm04.py
│   ├── imm05.py               # (mới)
│   ├── imm08.py
│   ├── imm09.py
│   ├── imm11.py
│   └── auth_service.py        # (mới) — business của register/approve
│
├── repositories/              # Tier 3 — data access (MỚI)
│   ├── __init__.py
│   ├── base.py                # BaseRepository<T> generic
│   ├── asset_repo.py
│   ├── commissioning_repo.py
│   ├── document_repo.py
│   ├── pm_repo.py
│   ├── repair_repo.py
│   ├── calibration_repo.py
│   ├── user_profile_repo.py
│   └── audit_repo.py
│
├── utils/
│   ├── helpers.py             # _ok, _err — giữ (envelope response)
│   ├── email.py               # _safe_sendmail, _get_role_emails
│   └── response.py
│
└── assetcore/doctype/         # Tier (cross-cut) — controllers
    └── <doctype>/<doctype>.py # CHỈ: validate + on_submit → gọi service
```

### 3.2 Quy tắc phân lớp

**Tier 1 — `api/*.py` (Presentation):**
- ✅ `@frappe.whitelist()`, parse query/body, coerce types.
- ✅ Gọi `services.<module>.<function>(...)`.
- ✅ Trả `_ok(data)` / `_err(msg, code)`.
- ❌ KHÔNG `frappe.db.*`, `frappe.get_doc`, `frappe.new_doc`.
- ❌ KHÔNG hardcode role strings hoặc business rules.

**Tier 2 — `services/*.py` (Business):**
- ✅ Thuần Python + gọi repositories.
- ✅ Enforce BR-xx-yy, orchestration giữa module.
- ✅ Raise `ServiceError(code, msg)` cho lỗi nghiệp vụ.
- ❌ KHÔNG parse HTTP, KHÔNG return JSON envelope.
- ❌ KHÔNG gọi trực tiếp `frappe.db` (đi qua repo). Ngoại lệ: transaction control (`frappe.db.commit()`).

**Tier 3 — `repositories/*.py` (Data Access):**
- ✅ Wrap Frappe ORM với interface gọi gọn: `get_by_name`, `list(filters, page)`, `create`, `update`, `delete`, `exists`, `count`.
- ✅ Áp dụng pagination + order_by nhất quán.
- ❌ KHÔNG chứa business rules (ví dụ không check "is calibration failed").

**Controllers (`assetcore/doctype/<dt>.py`):**
- ✅ `validate()` — check trường nội tại của doc (required, format).
- ✅ `on_submit()`, `on_update()` → gọi service.
- ❌ KHÔNG tạo document khác bằng `frappe.new_doc` — delegate qua service.

---

## 4. Cross-cutting: Constants & Permissions

### 4.1 `services/shared/constants.py` (đề xuất)

```python
# Roles
class Roles:
    SYS_ADMIN   = "IMM System Admin"
    QA          = "IMM QA Officer"
    DEPT_HEAD   = "IMM Department Head"
    OPS_MANAGER = "IMM Operations Manager"
    WORKSHOP    = "IMM Workshop Lead"
    TECHNICIAN  = "IMM Technician"
    DOC_OFFICER = "IMM Document Officer"
    STOREKEEPER = "IMM Storekeeper"
    CLINICAL    = "IMM Clinical User"

    ALL_IMM = (SYS_ADMIN, QA, DEPT_HEAD, OPS_MANAGER, WORKSHOP,
               TECHNICIAN, DOC_OFFICER, STOREKEEPER, CLINICAL)

    CAN_CREATE_WO = (SYS_ADMIN, OPS_MANAGER, WORKSHOP, TECHNICIAN)
    CAN_APPROVE   = (SYS_ADMIN, QA, DEPT_HEAD, OPS_MANAGER)
    CAN_MANAGE_DOCS = (SYS_ADMIN, DOC_OFFICER, QA)

# Asset lifecycle status
class AssetStatus:
    DRAFT         = "Draft"
    COMMISSIONED  = "Commissioned"
    ACTIVE        = "Active"
    UNDER_REPAIR  = "Under Repair"
    CALIBRATING   = "Calibrating"
    OUT_OF_SERVICE = "Out of Service"
    DECOMMISSIONED = "Decommissioned"

# Calibration result
class CalibrationResult:
    PASSED        = "Passed"
    COND_PASSED   = "Conditionally Passed"
    FAILED        = "Failed"
    CANCELLED     = "Cancelled"

# Error codes
class ErrorCode:
    NOT_FOUND      = "NOT_FOUND"
    FORBIDDEN      = "FORBIDDEN"
    VALIDATION     = "VALIDATION"
    UNAUTHORIZED   = "UNAUTHORIZED"
    CONFLICT       = "CONFLICT"
    BAD_STATE      = "BAD_STATE"
```

### 4.2 `services/shared/permissions.py`

```python
import frappe
from .constants import Roles
from .errors import ServiceError, ErrorCode

def has_any_role(roles: tuple[str, ...]) -> bool:
    user_roles = set(frappe.get_roles())
    return bool(user_roles.intersection(roles))

def require_role(roles: tuple[str, ...]) -> None:
    if not has_any_role(roles):
        raise ServiceError(ErrorCode.FORBIDDEN, "Không đủ quyền thực hiện")
```

### 4.3 `services/shared/errors.py`

```python
class ServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")
```

`api/*.py` bắt `ServiceError`:
```python
try:
    result = services.imm11.submit_calibration(name)
    return _ok(result)
except ServiceError as e:
    return _err(e.message, e.code)
```

---

## 5. Base Repository Pattern

### `repositories/base.py`

```python
import frappe
from typing import Any
from assetcore.utils.pagination import paginate

class BaseRepository:
    """Generic CRUD wrapper around Frappe ORM."""

    DOCTYPE: str = ""

    @classmethod
    def get(cls, name: str):
        if not cls.exists(name):
            return None
        return frappe.get_doc(cls.DOCTYPE, name)

    @classmethod
    def exists(cls, name: str) -> bool:
        return bool(frappe.db.exists(cls.DOCTYPE, name))

    @classmethod
    def count(cls, filters: dict | None = None) -> int:
        return frappe.db.count(cls.DOCTYPE, filters or {})

    @classmethod
    def list(cls, filters: dict | None = None, fields: list[str] | None = None,
             page: int = 1, page_size: int = 20, order_by: str = "modified desc"):
        total = cls.count(filters)
        pg = paginate(total, page, page_size)
        rows = frappe.get_all(
            cls.DOCTYPE, filters=filters or {}, fields=fields or ["name"],
            order_by=order_by,
            limit_start=pg["offset"], limit_page_length=pg["page_size"],
        )
        return rows, pg

    @classmethod
    def create(cls, data: dict, ignore_permissions: bool = False):
        doc = frappe.get_doc({"doctype": cls.DOCTYPE, **data})
        doc.insert(ignore_permissions=ignore_permissions)
        return doc

    @classmethod
    def update(cls, name: str, patch: dict):
        frappe.db.set_value(cls.DOCTYPE, name, patch)

    @classmethod
    def delete(cls, name: str, ignore_permissions: bool = False):
        frappe.delete_doc(cls.DOCTYPE, name, ignore_permissions=ignore_permissions)
```

### Ví dụ `repositories/calibration_repo.py`

```python
from .base import BaseRepository

class CalibrationRepo(BaseRepository):
    DOCTYPE = "IMM Asset Calibration"

class CalibrationScheduleRepo(BaseRepository):
    DOCTYPE = "IMM Calibration Schedule"
```

---

## 6. Ví dụ Before/After — `api/imm11.py::get_calibration_schedule`

**Trước (hiện tại):**
```python
@frappe.whitelist()
def get_calibration_schedule(name: str) -> dict:
    if not frappe.db.exists(_DT_SCHED, name):
        return _err(f"{_NOT_FOUND} Schedule '{name}'", "NOT_FOUND")
    doc = frappe.get_doc(_DT_SCHED, name)
    return _ok(doc.as_dict())
```

**Sau:**
```python
# api/imm11.py (Tier 1 — chỉ HTTP + envelope)
@frappe.whitelist()
def get_calibration_schedule(name: str) -> dict:
    try:
        data = services.imm11.get_schedule(name)
        return _ok(data)
    except ServiceError as e:
        return _err(e.message, e.code)

# services/imm11.py (Tier 2 — business)
def get_schedule(name: str) -> dict:
    schedule = CalibrationScheduleRepo.get(name)
    if not schedule:
        raise ServiceError(ErrorCode.NOT_FOUND, f"Không tìm thấy Schedule '{name}'")
    return schedule.as_dict()
```

→ Trước: 4 dòng, logic ORM rò rỉ. Sau: tier 1 = 6 dòng thuần HTTP, tier 2 = 4 dòng thuần business, test độc lập được.

---

## 7. Kế hoạch Triển khai (Incremental, Low-Risk)

Refactor **theo module, không big-bang**. Giữ tất cả endpoint hiện tại hoạt động; chỉ thay đổi _nội bộ_.

### Phase 1 — Cross-cutting (1 sprint)
1. ✅ `services/shared/constants.py` — Roles, AssetStatus, CalibrationResult, ErrorCode.
2. ✅ `services/shared/errors.py` — `ServiceError`.
3. ✅ `services/shared/permissions.py` — `require_role`, `has_any_role`.
4. ✅ `repositories/base.py` + `repositories/<doctype>_repo.py` cho các DocType chính.
5. ✅ Unit test cho base repository.

### Phase 2 — Refactor theo module (1 module / sprint)
Thứ tự ưu tiên (theo rủi ro tăng dần):
1. **IMM-11** (nhỏ, vừa mới code) — pilot.
2. **IMM-05** (thiếu services layer rõ rệt).
3. **IMM-09** (nhiều logic cross-module).
4. **IMM-08** (integration với IMM-04).
5. **IMM-04** (lớn nhất, nhiều state machine).
6. **IMM-00** (foundation, refactor cuối cùng).

**Mỗi module:**
- Trích xuất logic ORM ra repository.
- Viết service function thay vì gọi `frappe.db.*` trong API.
- Thay hardcoded role sets bằng `Roles.CAN_APPROVE` từ constants.
- Đổi check role từ inline sang `require_role()`.
- Migrate error response từ literal `"Không tìm thấy"` sang `ErrorCode.NOT_FOUND`.
- Chạy lại UAT module đó trước khi qua module kế tiếp.

### Phase 3 — Controller detox (1 sprint)
- Review `pm_work_order.py`, `asset_repair.py`, `asset_commissioning.py`.
- Chuyển tạo doc từ `on_submit` sang service.
- Đảm bảo controller chỉ có `validate` + `on_submit/on_update` → service call.

### Phase 4 — Frontend alignment
- Audit `src/api/*.ts` — tất cả response đã handle qua `frappePost`/`frappeGet` helper.
- Centralize role strings vào `src/constants/roles.ts`; import từ đó thay vì hardcode.
- Directive `v-permission` đã có — audit views để dùng rộng.

### Phase 5 — Testing & Docs
- Viết unit test cho từng service (mock repository).
- Viết integration test cho từng API endpoint (mock service).
- Update tài liệu `docs/res/` với pattern mới.

---

## 8. Lợi ích Mong đợi

| Tiêu chí | Trước | Sau |
|---|---|---|
| Số lần `frappe.db.*` trong `api/` | ~342 | ~0 |
| Duplicate `_ok/_err` | 6 file | 1 nơi (`utils/helpers.py`) |
| Role strings hardcode | 40+ vị trí | 1 nơi (`Roles` class) |
| Test service không cần HTTP mock | Không | Được (chỉ mock repository) |
| Test API không cần DB | Không | Được (mock service) |
| Reuse logic cross-module | Copy-paste | Import service |
| Thay constant (ví dụ đổi "Active" → "Operational") | Sửa 6-8 file | Sửa 1 dòng |

---

## 9. Rủi ro & Giảm thiểu

| Rủi ro | Giảm thiểu |
|---|---|
| Refactor làm vỡ endpoint đang chạy | Incremental theo module + regression UAT mỗi bước |
| Repository layer thêm boilerplate | Base class generic + code gen cho DocType đơn giản |
| Transaction boundary khó kiểm soát | Service gọi `frappe.db.commit()` tại ranh giới use case; repo không tự commit |
| Backward compat cho `api/user_profile.py` + admin UI | Giữ nguyên; chỉ delegate vào service |
| Team không quen pattern | Pilot IMM-11, viết guideline + code review checklist |

---

## 10. Quyết định Cần Xác nhận

1. **Chấp nhận pattern 3-tier?** Nếu Ok, tôi bắt đầu Phase 1 (cross-cutting).
2. **Thứ tự refactor module?** Đề xuất: IMM-11 → IMM-05 → IMM-09 → IMM-08 → IMM-04 → IMM-00.
3. **Có kèm test suite?** Nếu yes, cài `pytest-mock` + `frappe-testing-tools` vào `requirements-dev.txt`.
4. **Thời gian?** Ước tính 6 sprint (12 tuần). Có thể song song 2 module nếu đủ nhân sự.

---

## 11. Tham chiếu

- CLAUDE.md §5, §15 — Architecture principles, Code style
- `docs/res/BE_Readiness_Audit_2026-04-18.md` — baseline
- `docs/res/AssetCore_DocTypes_Audit_2026-04-19.md` — DocType catalog
- [Martin Fowler — Patterns of Enterprise Application Architecture] — Repository + Service Layer
