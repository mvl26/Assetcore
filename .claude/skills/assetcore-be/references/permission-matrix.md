# Permission matrix & role groups

Role names live in `assetcore/services/shared/constants.py:Roles`, re-exported via `assetcore.services.shared`. Wave 2 added 6 planning/procurement roles. **Never hardcode role strings.**

## All IMM roles (19)

```python
# Wave 1 — core HTM operations (13)
Roles.SYS_ADMIN        = "IMM System Admin"
Roles.OPS_MANAGER      = "IMM Operations Manager"
Roles.DEPT_HEAD        = "IMM Department Head"
Roles.DEPT_DEPUTY      = "IMM Deputy Department Head"
Roles.WORKSHOP         = "IMM Workshop Lead"
Roles.QA               = "IMM QA Officer"
Roles.BIOMED           = "IMM Biomed Technician"
Roles.TECHNICIAN       = "IMM Technician"
Roles.DOC_OFFICER      = "IMM Document Officer"
Roles.STOREKEEPER      = "IMM Storekeeper"
Roles.CLINICAL         = "IMM Clinical User"
Roles.AUDITOR          = "IMM Auditor"
Roles.VENDOR_ENGINEER  = "Vendor Engineer"

# Wave 2 — planning & procurement (6)
Roles.PLANNING         = "IMM Planning Officer"
Roles.FINANCE          = "IMM Finance Officer"
Roles.HTM_ENGINEER     = "IMM HTM Engineer"
Roles.PROCUREMENT      = "IMM Procurement Officer"
Roles.RISK             = "IMM Risk Officer"
Roles.BOARD_APPROVER   = "IMM Board Approver"
```

## Role groups (use these in `require_role`)

```python
Roles.ALL_IMM           # all 19 IMM roles
Roles.CAN_CREATE_WO     # SYS_ADMIN, OPS_MANAGER, WORKSHOP, BIOMED, TECHNICIAN
Roles.CAN_APPROVE       # SYS_ADMIN, OPS_MANAGER, DEPT_HEAD, QA
Roles.CAN_APPROVE_DEP   # + DEPT_DEPUTY
Roles.CAN_CANCEL        # SYS_ADMIN, OPS_MANAGER, DEPT_HEAD
Roles.CAN_MANAGE_DOCS   # SYS_ADMIN, DOC_OFFICER, QA
Roles.CAN_MANAGE_STOCK  # SYS_ADMIN, STOREKEEPER, OPS_MANAGER
Roles.CAN_ADMIN_USER    # SYS_ADMIN, OPS_MANAGER
```

The Wave 2 group names (`CAN_PLAN`, `CAN_APPROVE_BUDGET`, etc.) may exist by the time you're reading this — check the file.

## Two-layer enforcement

1. **Service layer** — `require_role(...)` at the start of every mutating function. This is the source of truth.
2. **DocPerm** — `setup_permissions.py` configures Frappe's row-level RBAC for desk users. The two must agree but don't replace each other; service checks defend against API misuse, DocPerm defends desk navigation.

```python
from assetcore.services.shared import Roles
from assetcore.services.shared.permissions import require_role

def assign_technician(name: str, *, technician: str, priority: str = ""):
    require_role(Roles.CAN_CREATE_WO, "Không đủ quyền giao việc")
    # ... rest of logic
```

## Convenience helpers (all in `services/shared/permissions.py`)

```python
has_role(role: str) -> bool
has_any_role(roles: Iterable[str]) -> bool
require_role(roles, message="Không đủ quyền thực hiện") -> None    # raises forbidden
is_admin() -> bool                  # alias for has_role(SYS_ADMIN)
require_admin() -> None
require_user_mgmt() -> None         # gates Roles.CAN_ADMIN_USER
```

## FE/BE role mirror

The frontend keeps an identical catalog at `frontend/src/constants/roles.ts` (`Roles`, `ALL_IMM_ROLES`, `ROLES_CREATE_WO`, `ROLES_APPROVE`, `ROLES_PM_MANAGE`, ...). Whenever you add a role or a group on BE, mirror it on FE. The two files must stay in sync — they're consumed by router guards and the `v-permission` directive.

## Owner-scoped access

For "creator can read own records" use `if_owner: 1` in DocPerm and check ownership in service when the action is creator-only:

```python
if not has_any_role(Roles.CAN_APPROVE) and frappe.session.user != doc.owner:
    raise forbidden("Chỉ người tạo hoặc người duyệt được xem")
```

## Vendor Engineer scope

`Roles.VENDOR_ENGINEER` is external — must NEVER access:
- `IMM Audit Trail`, `IMM CAPA Record`, `IMM Risk Register`, `IMM Internal Audit`
- Other vendors' work orders (filter by `assigned_vendor` matching the user's vendor company)
- Financial DocTypes (`AC Asset Depreciation Schedule`, `Budget Estimate Line`)

`hooks.py` wires `permission_query_conditions` for vendor-visible DocTypes. Service-layer code must additionally re-check.

When in doubt, deny.
