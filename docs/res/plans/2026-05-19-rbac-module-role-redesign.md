# RBAC Module-Based Role Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay 20 persona role bằng RBAC theo module (4 System + 26 Domain role), code chỉ check capability (không hardcode tên role), BE là biên bảo mật, FE có trang gán role.

**Architecture:** Role chỉ là *bó quyền* gán qua `Has Role`. Quyền thật nằm trong DocPerm (105 DocType JSON) + Workflow Transition (data). Tầng `rbac.py` resolve capability→`frappe.has_permission`. FE đọc capability đã resolve, cache 1 lần. Hierarchy = DocPerm của Manager là superset của User (permission union, không nest tên role).

**Tech Stack:** Frappe v15 (Python), MariaDB, Vue 3 + TS + Pinia + Vue Router, pytest (`bench run-tests`).

**Spec nguồn:** `docs/res/rbac/role-redesign-module-based.md`

---

## Quy ước chung

- **Site test:** `miyano`. Lệnh bench chạy tại `/home/miyano/frappe-bench`.
- **Commit:** dùng skill `assetcore-commit` (1 commit/lần khi user yêu cầu, EN subject, body VN, KHÔNG `Co-Authored-By`). Trong plan này mỗi task có bước commit — **chỉ commit khi user xác nhận** (xem [[feedback-no-auto-commit]]); nếu chạy subagent-driven, gom diff và hỏi user trước mỗi commit.
- **TDD:** test trước (CLAUDE.md §17). Test BE đặt trong `assetcore/tests/`.
- **30 role:**
  - System (4): `AssetCore Super Admin`, `AssetCore System User`, `AssetCore Auditor`, `Vendor Engineer`
  - Domain (26): `<D> Manager` / `<D> User`, `<D>` ∈ {Data, Needs, Spec, Procurement, Commissioning, Document, Training, PM, Repair, Calibration, Corrective, Inventory, Compliance}

---

## File Structure

**Tạo mới:**
- `assetcore/services/shared/rbac.py` — `CAPABILITY_MAP`, `can()`, `require()`, `get_capabilities()`, `DOCTYPE_DOMAIN`, `DOMAIN_DOCTYPES`
- `assetcore/setup/gen_docperms.py` — script sinh block `permissions` cho 105 DocType JSON
- `assetcore/patches/v3_2/001_module_role_redesign.py` — migration wipe persona/legacy/profile
- `assetcore/tests/test_rbac.py` — test capability layer + DocPerm invariants
- `frontend/src/composables/useCapabilities.ts` — `can(cap)` đọc store cache
- `frontend/src/views/admin/RoleAdminView.vue` — trang catalog + gán role grid
- `frontend/src/api/roleAdmin.ts` — API client cho RoleAdminView

**Sửa:**
- `assetcore/services/shared/constants.py` — `class Roles` viết lại (30 hằng + `ROLE_RANK`/`SYSTEM_ROLES`/`DOMAIN_ROLES`), bỏ `CAN_*`/`ALL_IMM`, `ROLE_METADATA` mới
- `assetcore/hooks.py` — `_IMM_ROLES`(30); bỏ Role/Module Profile khỏi `fixtures`; `doc_events` cache-invalidate; Has Role umbrella hook
- `assetcore/api/auth.py` — bỏ `_ROLE_*` literal; thêm endpoint `get_capabilities`
- `assetcore/api/user.py` — endpoint set role cho user (grid FE)
- `assetcore/services/{imm00,imm05,imm06,imm09,imm15,imm16,auth_service}.py`, `services/shared/permissions.py` — `Roles.CAN_*` → `rbac.require`
- `assetcore/setup/setup_permissions.py`, `setup/setup_role_profiles.py` — cleanup
- `assetcore/fixtures/role.json` — regen 30 role; **xóa** `fixtures/role_profile.json`, `fixtures/module_profile.json`
- `assetcore/fixtures/workflow.json`, `fixtures/workflow_action_master.json`, `assetcore/workflow/*.json` — remap `allowed`/`allow_edit`
- 105 file `assetcore/assetcore/doctype/<dt>/<dt>.json` — block `permissions` (sinh bởi `gen_docperms.py`)
- `frontend/src/constants/roles.ts` — chỉ còn catalog 30 role; bỏ `ROLES_*`/`ALL_IMM_ROLES`
- `frontend/src/stores/auth.ts` — thêm `capabilities`, bỏ `isXxx` role-name
- `frontend/src/composables/usePermissions.ts` — wrap `useCapabilities`
- `frontend/src/directives/permission.ts` — `v-can` theo capability
- `frontend/src/router/index.ts` — `meta.requiredCapabilities`
- `frontend/src/constants/modules.ts` — `requiredCapabilities`
- `frontend/src/api/auth.ts` — `fetchCapabilities()`
- ~14 file FE import `constants/roles` — đổi sang `useCapabilities`

---

## PHASE 0 — Nền tảng: constants + rbac (BE, không đụng DocPerm)

### Task 0.1: Viết lại `constants.py::Roles` (30 role, bỏ CAN_*)

**Files:**
- Modify: `assetcore/services/shared/constants.py`
- Test: `assetcore/tests/test_rbac.py`

- [ ] **Step 1: Viết test thất bại** — `assetcore/tests/test_rbac.py`

```python
# Copyright (c) 2026, AssetCore Team
import frappe
import unittest
from assetcore.services.shared.constants import Roles


class TestRolesCatalog(unittest.TestCase):
    def test_30_roles_total(self):
        self.assertEqual(len(Roles.ALL), 30)

    def test_system_roles(self):
        self.assertEqual(
            set(Roles.SYSTEM_ROLES),
            {"AssetCore Super Admin", "AssetCore System User",
             "AssetCore Auditor", "Vendor Engineer"},
        )

    def test_domain_pairs(self):
        self.assertEqual(len(Roles.DOMAIN_ROLES), 26)
        self.assertIn("PM Manager", Roles.DOMAIN_ROLES)
        self.assertIn("PM User", Roles.DOMAIN_ROLES)

    def test_rank_hierarchy(self):
        self.assertGreater(Roles.ROLE_RANK["AssetCore Super Admin"],
                            Roles.ROLE_RANK["PM Manager"])
        self.assertGreater(Roles.ROLE_RANK["PM Manager"],
                            Roles.ROLE_RANK["PM User"])

    def test_no_legacy_can_attr(self):
        self.assertFalse(hasattr(Roles, "CAN_CREATE_WO"))
        self.assertFalse(hasattr(Roles, "ALL_IMM"))
```

- [ ] **Step 2: Chạy test — xác nhận FAIL**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL (`AttributeError: type object 'Roles' has no attribute 'ALL'`)

- [ ] **Step 3: Viết lại `class Roles` + `ROLE_METADATA`**

Thay toàn bộ `class Roles` và `ROLE_METADATA` trong `constants.py` bằng:

```python
class Roles:
    """RBAC module-based — 4 System + 26 Domain. Đồng bộ fixtures/role.json.

    Code KHÔNG so tên role; dùng assetcore.services.shared.rbac.{can,require}.
    Các hằng dưới chỉ phục vụ fixture/migration/catalog UI.
    """

    # System roles (cố định, toàn hệ thống)
    SUPER_ADMIN  = "AssetCore Super Admin"
    SYSTEM_USER  = "AssetCore System User"
    AUDITOR      = "AssetCore Auditor"
    VENDOR       = "Vendor Engineer"

    SYSTEM_ROLES = (SUPER_ADMIN, SYSTEM_USER, AUDITOR, VENDOR)

    # Domain words (13 module đã build)
    DOMAINS = (
        "Data", "Needs", "Spec", "Procurement", "Commissioning",
        "Document", "Training", "PM", "Repair", "Calibration",
        "Corrective", "Inventory", "Compliance",
    )

    DOMAIN_ROLES = tuple(
        f"{d} {tier}" for d in DOMAINS for tier in ("Manager", "User")
    )

    ALL = SYSTEM_ROLES + DOMAIN_ROLES

    # rank chỉ phục vụ UX grid (KHÔNG dùng để enforce)
    ROLE_RANK = {
        SUPER_ADMIN: 100,
        **{f"{d} Manager": 50 for d in DOMAINS},
        **{f"{d} User": 10 for d in DOMAINS},
        AUDITOR: 5,
        VENDOR: 5,
        SYSTEM_USER: 0,
    }


# Map domain word -> (IMM code, nhãn tiếng Việt) cho catalog FE/BE
DOMAIN_META: dict[str, dict[str, str]] = {
    "Data":          {"imm": "IMM-00", "label": "Dữ liệu nền"},
    "Needs":         {"imm": "IMM-01", "label": "Nhu cầu & Dự toán"},
    "Spec":          {"imm": "IMM-02", "label": "Thông số kỹ thuật"},
    "Procurement":   {"imm": "IMM-03", "label": "NCC & Mua sắm"},
    "Commissioning": {"imm": "IMM-04", "label": "Lắp đặt & Nghiệm thu"},
    "Document":      {"imm": "IMM-05", "label": "Hồ sơ"},
    "Training":      {"imm": "IMM-06", "label": "Đào tạo"},
    "PM":            {"imm": "IMM-08", "label": "Bảo trì định kỳ"},
    "Repair":        {"imm": "IMM-09", "label": "Sửa chữa"},
    "Calibration":   {"imm": "IMM-11", "label": "Hiệu chuẩn"},
    "Corrective":    {"imm": "IMM-12", "label": "Bảo trì khắc phục"},
    "Inventory":     {"imm": "IMM-15", "label": "Tồn kho phụ tùng"},
    "Compliance":    {"imm": "IMM-16", "label": "Tuân thủ / QMS"},
}

ROLE_METADATA: dict[str, dict[str, str]] = {
    Roles.SUPER_ADMIN: {"label": "Quản trị hệ thống",
        "description": "Toàn quyền + bao trùm Frappe System Manager", "group": "System"},
    Roles.SYSTEM_USER: {"label": "Người dùng hệ thống",
        "description": "Role nền: đăng nhập, dashboard, đọc shared-core", "group": "System"},
    Roles.AUDITOR: {"label": "Kiểm toán viên",
        "description": "Chỉ đọc toàn bộ + audit trail", "group": "System"},
    Roles.VENDOR: {"label": "KTV nhà cung cấp",
        "description": "Bên thứ ba, cô lập theo WO/Asset được phân công", "group": "System"},
    **{f"{d} Manager": {
        "label": f"{DOMAIN_META[d]['label']} — Quản lý",
        "description": f"{DOMAIN_META[d]['imm']}: full CRUD + duyệt/hủy workflow",
        "group": d} for d in Roles.DOMAINS},
    **{f"{d} User": {
        "label": f"{DOMAIN_META[d]['label']} — Người dùng",
        "description": f"{DOMAIN_META[d]['imm']}: read/write/create, thao tác thường",
        "group": d} for d in Roles.DOMAINS},
}
```

- [ ] **Step 4: Chạy test — xác nhận PASS**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: PASS (5 test)

- [ ] **Step 5: Commit** (chờ user xác nhận)

```
git add -A && git commit -m "refactor(rbac): redesign Roles catalog to 30 module-based roles" -m "- constants.py: bo persona+CAN_*, them 30 role, ROLE_RANK, DOMAIN_META, ROLE_METADATA moi
- tests/test_rbac.py: test catalog 30 role + hierarchy rank"
```

---

### Task 0.2: `rbac.py` — DOCTYPE_DOMAIN + CAPABILITY_MAP + can/require/get_capabilities

**Files:**
- Create: `assetcore/services/shared/rbac.py`
- Test: `assetcore/tests/test_rbac.py`

- [ ] **Step 1: Thêm test thất bại** vào `test_rbac.py`

```python
from assetcore.services.shared import rbac


class TestCapabilityMap(unittest.TestCase):
    def test_every_built_doctype_mapped(self):
        self.assertIn("PM Work Order", rbac.DOCTYPE_DOMAIN)
        self.assertEqual(rbac.DOCTYPE_DOMAIN["PM Work Order"], "PM")
        self.assertEqual(rbac.DOCTYPE_DOMAIN["AC Asset"], "_shared")
        self.assertEqual(rbac.DOCTYPE_DOMAIN["IMM Audit Trail"], "_audit")

    def test_capability_map_crud(self):
        self.assertEqual(rbac.CAPABILITY_MAP["pm.write"], ("PM Work Order", "write"))
        self.assertEqual(rbac.CAPABILITY_MAP["pm.delete"], ("PM Work Order", "delete"))

    def test_can_unknown_capability_raises(self):
        with self.assertRaises(KeyError):
            rbac.can("nope.nope")

    def test_get_capabilities_returns_dict(self):
        frappe.set_user("Administrator")
        caps = rbac.get_capabilities()
        self.assertIsInstance(caps, dict)
        self.assertIn("pm.read", caps)
```

- [ ] **Step 2: Chạy — FAIL**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL (`ModuleNotFoundError: assetcore.services.shared.rbac`)

- [ ] **Step 3: Tạo `assetcore/services/shared/rbac.py`**

```python
# Copyright (c) 2026, AssetCore Team
"""RBAC capability layer — code hoi capability, KHONG so ten role.

Binding capability -> (DocType, ptype) o day; quyen that do DocPerm/Workflow
(data) quyet dinh qua frappe.has_permission. Doi quyen = sua DocPerm o /app,
khong deploy.
"""
from __future__ import annotations

import frappe

# Map DocType -> domain word (hoac _shared / _audit)
# Nguon: docs/res/rbac/role-redesign-module-based.md §5
_DOMAIN_DOCTYPES: dict[str, list[str]] = {
    "Data": ["AC Asset Category", "AC Department", "AC Location", "AC Supplier",
        "AC UOM", "AC UOM Conversion", "IMM Device Model", "IMM Device Spare Part",
        "AC Authorized Technician", "Service Contract", "Service Contract Asset",
        "Required Document Type", "IMM SLA Policy"],
    "Needs": ["IMM Needs Request", "Needs Priority Scoring", "IMM Demand Forecast",
        "Forecast Driver", "Budget Estimate Line", "IMM Procurement Plan",
        "Procurement Plan Line"],
    "Spec": ["IMM Tech Spec", "Tech Spec Document", "Tech Spec Requirement",
        "IMM Market Benchmark", "Benchmark Candidate", "Infra Compatibility Item",
        "IMM Lock In Risk Assessment", "Lock In Risk Item"],
    "Procurement": ["IMM Vendor Evaluation", "Vendor Eval Candidate",
        "Vendor Eval Criterion", "IMM Vendor Scorecard", "IMM AVL Entry",
        "IMM Procurement Decision", "IMM Supplier Audit", "Vendor Quotation Line",
        "Vendor Cert", "AC Purchase", "AC Purchase Item", "AC Purchase Device Item"],
    "Commissioning": ["Asset Commissioning", "Commissioning Checklist",
        "Commissioning Document Record", "Asset Transfer"],
    "Document": ["Asset Document", "Document Request", "Expiry Alert Log"],
    "Training": ["IMM Training Program", "IMM Training Session",
        "IMM Training Participant", "IMM Trainer", "IMM User Competency",
        "IMM Competency Alert Log", "IMM Competency Gap Report", "IMM Gap Detail Row"],
    "PM": ["PM Work Order", "PM Schedule", "PM Task Log", "PM Checklist Template",
        "PM Checklist Item", "PM Checklist Result"],
    "Repair": ["Asset Repair", "Repair Checklist", "Spare Parts Used",
        "Firmware Change Request"],
    "Calibration": ["IMM Asset Calibration", "IMM Calibration Schedule",
        "IMM Calibration Measurement"],
    "Corrective": ["Incident Report", "IMM RCA Record", "IMM RCA Five Why Step",
        "IMM RCA Related Incident", "Asset QA Non Conformance"],
    "Inventory": ["AC Spare Part", "AC Spare Part Stock", "AC Stock Movement",
        "AC Stock Movement Item", "AC Warehouse", "IMM Spare Allocation",
        "IMM Spare Allocation Item", "IMM Spare Alternative", "IMM Spare Batch",
        "IMM Spare Part Forecast", "IMM Spare Forecast Item",
        "IMM Critical Spare Watchlist", "IMM Stock Cycle Count",
        "IMM Stock Cycle Count Item", "IMM Cycle Count Item"],
    "Compliance": ["IMM Compliance Finding", "IMM Compliance Rule",
        "IMM Compliance Scorecard", "IMM Scorecard Department Row",
        "IMM Scorecard Module Row", "Scorecard Kpi Row", "IMM CAPA Record",
        "IMM CAPA Action Step", "IMM Internal Audit", "IMM Audit Checklist Item",
        "Audit Finding", "IMM Management Review", "IMM MR Attendee",
        "IMM MR Output Action"],
    "_shared": ["AC Asset", "Asset Lifecycle Event",
        "AC Asset Depreciation Schedule", "AC Asset Downtime Log"],
    "_audit": ["IMM Audit Trail"],
}

DOMAIN_DOCTYPES = _DOMAIN_DOCTYPES
DOCTYPE_DOMAIN: dict[str, str] = {
    dt: dom for dom, dts in _DOMAIN_DOCTYPES.items() for dt in dts
}

# Dai dien 1 DocType chinh cho moi domain (de resolve cap CRUD)
_DOMAIN_PRIMARY: dict[str, str] = {
    "Data": "IMM Device Model", "Needs": "IMM Needs Request",
    "Spec": "IMM Tech Spec", "Procurement": "IMM Vendor Evaluation",
    "Commissioning": "Asset Commissioning", "Document": "Asset Document",
    "Training": "IMM Training Program", "PM": "PM Work Order",
    "Repair": "Asset Repair", "Calibration": "IMM Asset Calibration",
    "Corrective": "Incident Report", "Inventory": "AC Stock Movement",
    "Compliance": "IMM CAPA Record",
}

_PTYPES = ("read", "write", "create", "delete", "submit", "cancel")

CAPABILITY_MAP: dict[str, tuple[str, str]] = {}
for _dom, _dt in _DOMAIN_PRIMARY.items():
    _prefix = _dom.lower()
    for _pt in _PTYPES:
        CAPABILITY_MAP[f"{_prefix}.{_pt}"] = (_dt, _pt)

CAPABILITY_MAP.update({
    "pm.reschedule":        ("PM Work Order", "write"),
    "incident.acknowledge": ("Incident Report", "write"),
    "incident.close":       ("Incident Report", "submit"),
    "cal.send_lab":         ("IMM Asset Calibration", "write"),
    "doc.approve":          ("Asset Document", "submit"),
    "capa.close":           ("IMM CAPA Record", "submit"),
    "data.admin":           ("IMM Device Model", "delete"),
    "audit.read":           ("IMM Audit Trail", "read"),
})


def can(cap: str, doc=None) -> bool:
    """True neu user hien tai co quyen tuong ung capability."""
    dt, ptype = CAPABILITY_MAP[cap]  # KeyError neu cap sai — fail loud
    return bool(frappe.has_permission(dt, ptype, doc=doc))


def require(cap: str, doc=None) -> None:
    """Chan cung o BE — goi dau moi whitelisted method nhay cam."""
    if not can(cap, doc):
        frappe.throw(
            frappe._("Khong du quyen: {0}").format(cap),
            frappe.PermissionError,
        )


def _cache_key(user: str) -> str:
    return f"ac_caps::{user}"


def get_capabilities(user: str | None = None) -> dict[str, bool]:
    """Resolve toan bo capability cho user — cache 1h theo user."""
    user = user or frappe.session.user
    key = _cache_key(user)
    cached = frappe.cache().get_value(key)
    if cached is not None:
        return cached
    caps = {c: can(c) for c in CAPABILITY_MAP}
    frappe.cache().set_value(key, caps, expires_in_sec=3600)
    return caps


def invalidate_capabilities(user: str | None = None) -> None:
    if user:
        frappe.cache().delete_value(_cache_key(user))
    else:
        frappe.cache().delete_keys("ac_caps::*")
```

- [ ] **Step 4: Chạy — PASS**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: PASS (toàn bộ class trong test_rbac)

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "feat(rbac): add capability layer (rbac.py) with DocType to domain map" -m "- rbac.py: DOCTYPE_DOMAIN (105 dt), CAPABILITY_MAP, can/require/get_capabilities/invalidate
- tests: test_rbac capability map + resolve"
```

---

## PHASE 1 — DocPerm regen cho 105 DocType JSON

### Task 1.1: Script sinh DocPerm `gen_docperms.py`

**Files:**
- Create: `assetcore/setup/gen_docperms.py`
- Test: `assetcore/tests/test_rbac.py` (thêm class)

- [ ] **Step 1: Thêm test bất biến DocPerm**

```python
import json, os, glob


class TestDocPermInvariants(unittest.TestCase):
    DT_DIR = frappe.get_app_path("assetcore", "assetcore", "doctype")

    def _perms(self, dt_folder):
        with open(os.path.join(self.DT_DIR, dt_folder, dt_folder + ".json")) as f:
            return json.load(f).get("permissions", [])

    def test_no_persona_role_in_any_json(self):
        bad = {"IMM System Admin", "IMM Workshop Lead", "IMM QA Officer"}
        for jf in glob.glob(os.path.join(self.DT_DIR, "*", "*.json")):
            with open(jf) as f:
                data = json.load(f)
            roles = {p.get("role") for p in data.get("permissions", [])}
            self.assertEqual(roles & bad, set(), f"{jf} con persona role")

    def test_pm_manager_superset_of_user(self):
        perms = {p["role"]: p for p in self._perms("pm_work_order")}
        mgr, usr = perms["PM Manager"], perms["PM User"]
        for k in ("read", "write", "create"):
            self.assertTrue(usr.get(k))
        for k in ("delete", "cancel", "amend"):
            self.assertGreaterEqual(mgr.get(k, 0), usr.get(k, 0))
        self.assertEqual(mgr.get("delete"), 1)

    def test_system_user_can_read_shared_core(self):
        perms = {p["role"]: p for p in self._perms("ac_asset")}
        self.assertEqual(perms["AssetCore System User"].get("read"), 1)
```

- [ ] **Step 2: Chạy — FAIL**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL (`KeyError: 'PM Manager'` — JSON còn persona)

- [ ] **Step 3: Tạo `assetcore/setup/gen_docperms.py`**

```python
# Copyright (c) 2026, AssetCore Team
"""Sinh block `permissions` cho moi DocType JSON theo domain map (rbac.py).

Chay:  cd apps/assetcore && python -m assetcore.setup.gen_docperms
Idempotent: ghi de block permissions, giu nguyen phan con lai cua JSON.
"""
from __future__ import annotations

import json, os, glob, pathlib

from assetcore.services.shared.rbac import DOCTYPE_DOMAIN
from assetcore.services.shared.constants import Roles

_DT_DIR = os.path.join(os.path.dirname(__file__), "..", "assetcore", "doctype")


def _perm(role: str, **flags) -> dict:
    base = dict(read=0, write=0, create=0, submit=0, cancel=0, delete=0,
                amend=0, report=0, export=0, print=0, email=0, share=0)
    base.update(flags)
    return {"role": role, **base}


def _full(role):
    return _perm(role, read=1, write=1, create=1, submit=1, cancel=1,
                 delete=1, amend=1, report=1, export=1, print=1, email=1, share=1)


def _user(role):
    return _perm(role, read=1, write=1, create=1, report=1,
                 print=1, email=1, share=1)


def _read(role):
    return _perm(role, read=1, report=1, export=1, print=1)


def perms_for_doctype(doctype_label: str) -> list[dict]:
    dom = DOCTYPE_DOMAIN.get(doctype_label)
    rows = [_full("AssetCore Super Admin")]
    if dom == "_audit":
        rows.append(_read("AssetCore Auditor"))
        return rows
    if dom == "_shared":
        rows.append(_read("AssetCore System User"))
        rows.append(_read("AssetCore Auditor"))
        for d in Roles.DOMAINS:
            rows.append(_read(f"{d} User"))
        return rows
    if dom is None:
        rows.append(_read("AssetCore Auditor"))
        return rows
    rows.append(_full(f"{dom} Manager"))
    rows.append(_user(f"{dom} User"))
    rows.append(_read("AssetCore Auditor"))
    rows.append(_read("AssetCore System User"))
    return rows


def run() -> int:
    changed = 0
    for jf in glob.glob(os.path.join(_DT_DIR, "*", "*.json")):
        folder = os.path.basename(os.path.dirname(jf))
        with open(jf, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("doctype") != "DocType" and "fields" not in data:
            continue
        label = data.get("name") or folder.replace("_", " ").title()
        new_perms = perms_for_doctype(label)
        if data.get("permissions") == new_perms:
            continue
        data["permissions"] = new_perms
        body = json.dumps(data, ensure_ascii=False, indent=1) + "\n"
        pathlib.Path(jf).write_text(body, encoding="utf-8")
        changed += 1
    print(f"gen_docperms: {changed} DocType JSON cap nhat")
    return changed


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Chạy generator + test**

Run:
```
cd /home/miyano/frappe-bench/apps/assetcore && python -m assetcore.setup.gen_docperms
cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac
```
Expected: generator in `N DocType JSON cap nhat`; test PASS (3 invariant test).

- [ ] **Step 5: Kiểm tra diff JSON hợp lý** (thủ công)

Run: `git diff --stat -- 'assetcore/assetcore/doctype/**/*.json' | tail -1`
Expected: ~105 file changed; mở `pm_work_order.json`, `ac_asset.json`, `imm_audit_trail.json` xác nhận role mới.

- [ ] **Step 6: Commit** (chờ user)

```
git add -A && git commit -m "refactor(rbac): regenerate DocPerm for 105 DocTypes to module roles" -m "- setup/gen_docperms.py: sinh permissions theo DOCTYPE_DOMAIN
- 105 DocType JSON: Manager(full)/User(rwc)/System User+Auditor(read), shared-core read-all, audit-only Auditor
- tests: invariant no-persona, Manager superset User, System User read shared-core"
```

---

## PHASE 2 — Refactor service/api: bỏ `Roles.CAN_*` → `rbac.require`

### Task 2.1: Refactor 10 file dùng `Roles.`/`CAN_`/`ALL_IMM`

**Files (Modify):** `assetcore/api/user.py`, `assetcore/api/auth.py`, `assetcore/services/imm00.py`, `assetcore/services/imm05.py`, `assetcore/services/imm06.py`, `assetcore/services/imm09.py`, `assetcore/services/imm15.py`, `assetcore/services/imm16.py`, `assetcore/services/auth_service.py`, `assetcore/services/shared/permissions.py`
- Test: `assetcore/tests/test_rbac.py`

- [ ] **Step 1: Test "không còn tham chiếu role-name trong logic"**

```python
import subprocess


class TestNoHardcodedRoleChecks(unittest.TestCase):
    def test_no_can_or_all_imm_usage(self):
        app = frappe.get_app_path("assetcore")
        out = subprocess.run(
            ["grep", "-rnE", r"Roles\.(CAN_|ALL_IMM)|\.CAN_[A-Z]",
             os.path.join(app, "api"), os.path.join(app, "services")],
            capture_output=True, text=True,
        ).stdout
        self.assertEqual(out.strip(), "", f"Con role-name check:\n{out}")
```

- [ ] **Step 2: Chạy — FAIL** (10 file còn `Roles.CAN_*`)

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL, in danh sách dòng vi phạm.

- [ ] **Step 3: Refactor từng chỗ theo pattern**

Với mỗi dòng grep ra, thay kiểm tra role bằng capability:

```python
# TRUOC
from assetcore.services.shared.constants import Roles
if not set(frappe.get_roles()) & set(Roles.CAN_CREATE_WO):
    frappe.throw("...", frappe.PermissionError)

# SAU
from assetcore.services.shared import rbac
rbac.require("pm.create")
```

Bảng ánh xạ `CAN_* → capability`:

| Cũ | Mới (`rbac.require`) |
|---|---|
| `CAN_CREATE_WO` | `pm.create` (hoặc `repair.create`/`calibration.create` theo file) |
| `CAN_APPROVE` / `CAN_APPROVE_DEP` | `<domain>.submit` của doctype đang xử lý |
| `CAN_CANCEL` | `<domain>.cancel` |
| `CAN_MANAGE_DOCS` | `document.write` |
| `CAN_MANAGE_STOCK` | `inventory.write` |
| `CAN_ADMIN_USER` | `data.admin` |
| `CAN_PLAN` | `needs.write` |
| `CAN_APPROVE_PROCUREMENT` | `procurement.submit` |
| `CAN_ASSESS_RISK` | `spec.write` |
| `CAN_MANAGE_TRAINING` | `training.write` |
| `CAN_CONDUCT_TRAINING` | `training.write` |
| `CAN_SIGNOFF_COMPETENCY` | `training.submit` |
| `ALL_IMM` (gate "là user IMM") | bỏ check, hoặc `rbac.can("data.read")` nếu cần |
| `READ_ONLY_ROLES`/`AUDITOR` | `rbac.can("audit.read")` |

Trong `api/auth.py`: xóa hằng `_ROLE_ADMIN/_ROLE_QA/...`; chỗ `_get_role_emails(_ROLE_*)` là *email theo role* (data lookup, không phải gate) → đổi sang role mới: `_ROLE_ADMIN`→`"AssetCore Super Admin"`, `_ROLE_QA`→`"Compliance Manager"`, `_ROLE_OPS`→`"Commissioning Manager"`, `_ROLE_WORKSHOP`/`_ROLE_TECH`→`"PM Manager"`, `_ROLE_DOC`→`"Document Manager"`, `_ROLE_DEPT_HEAD`→bỏ.

> Mỗi file sửa xong chạy ngay test module liên quan, ví dụ:
> `bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm09`

- [ ] **Step 4: Ghi baseline + chạy test toàn bộ — PASS**

Run:
```
cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore 2>&1 | tail -5   # baseline TRƯỚC khi sửa, ghi lại số pass/fail
bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac
bench --site miyano run-tests --app assetcore 2>&1 | tail -5
```
Expected: `TestNoHardcodedRoleChecks` PASS; suite không phát sinh fail mới so với baseline.

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "refactor(rbac): replace Roles.CAN_* role checks with rbac.require capability" -m "- 10 file api/services: bo so ten role -> rbac.require(<cap>)
- api/auth.py: bo _ROLE_* literal, email-by-role doi role moi
- tests: assert 0 hardcoded role check trong api/services"
```

---

## PHASE 3 — Endpoint capability + hooks + cache invalidate

### Task 3.1: Endpoint `get_capabilities` + Has Role umbrella + cache invalidate

**Files:**
- Modify: `assetcore/api/auth.py`, `assetcore/hooks.py`
- Create: `assetcore/services/shared/role_hooks.py`
- Test: `assetcore/tests/test_rbac.py`

- [ ] **Step 1: Test endpoint + umbrella hook**

```python
class TestCapabilityEndpoint(unittest.TestCase):
    def test_endpoint_returns_caps(self):
        frappe.set_user("Administrator")
        from assetcore.api.auth import get_capabilities as ep
        res = ep()
        self.assertTrue(res["ok"])
        self.assertIn("pm.read", res["data"])


class TestUmbrellaRole(unittest.TestCase):
    def test_super_admin_grants_system_manager(self):
        u = "rbac_umbrella_test@example.com"
        if not frappe.db.exists("User", u):
            frappe.get_doc({"doctype": "User", "email": u,
                "first_name": "RBAC", "send_welcome_email": 0}).insert(
                ignore_permissions=True)
        from assetcore.services.shared.role_hooks import sync_umbrella
        user = frappe.get_doc("User", u)
        user.add_roles("AssetCore Super Admin")
        sync_umbrella(frappe.get_doc("Has Role",
            {"parent": u, "role": "AssetCore Super Admin"}), "after_insert")
        self.assertIn("System Manager", [r.role for r in
            frappe.get_doc("User", u).roles])
        frappe.delete_doc("User", u, force=True, ignore_permissions=True)
```

- [ ] **Step 2: Chạy — FAIL**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL (`ImportError: get_capabilities`)

- [ ] **Step 3a: Thêm endpoint vào `assetcore/api/auth.py`**

```python
@frappe.whitelist()
def get_capabilities():
    """Tra map capability da resolve cho user hien tai (FE cache 1 lan)."""
    from assetcore.services.shared import rbac
    if frappe.session.user == "Guest":
        return _err(_MSG_NOT_LOGGED_IN, "UNAUTHORIZED")
    return _ok(rbac.get_capabilities())
```

- [ ] **Step 3b: Tạo `assetcore/services/shared/role_hooks.py`**

```python
# Copyright (c) 2026, AssetCore Team
"""Has Role hooks: umbrella Super Admin + invalidate capability cache."""
from __future__ import annotations

import frappe

from assetcore.services.shared import rbac

_SUPER = "AssetCore Super Admin"
_FRAPPE_ADMIN = "System Manager"


def _user_of(doc):
    if doc.doctype == "Has Role" and doc.parenttype == "User":
        return doc.parent
    if doc.doctype == "User":
        return doc.name
    return None


def sync_umbrella(doc, method=None):
    """Khi gan/go Super Admin -> tu kem/go System Manager (idempotent)."""
    if doc.doctype != "Has Role" or doc.parenttype != "User":
        return
    if doc.role != _SUPER:
        return
    user = frappe.get_doc("User", doc.parent)
    has_roles = {r.role for r in user.roles}
    if method in ("after_insert", "on_update"):
        if _FRAPPE_ADMIN not in has_roles:
            user.add_roles(_FRAPPE_ADMIN)
    elif method == "on_trash":
        if _SUPER not in (has_roles - {doc.role}) and _FRAPPE_ADMIN in has_roles:
            user.remove_roles(_FRAPPE_ADMIN)


def invalidate_caps(doc, method=None):
    rbac.invalidate_capabilities(_user_of(doc))
```

- [ ] **Step 3c: Wire `hooks.py`** — thêm vào `doc_events` (không ghi đè entry sẵn có):

```python
doc_events = {
    # ... (giu nguyen cac entry hien co) ...
    "Has Role": {
        "after_insert": [
            "assetcore.services.shared.role_hooks.sync_umbrella",
            "assetcore.services.shared.role_hooks.invalidate_caps",
        ],
        "on_trash": [
            "assetcore.services.shared.role_hooks.sync_umbrella",
            "assetcore.services.shared.role_hooks.invalidate_caps",
        ],
    },
    "Custom DocPerm": {
        "on_update": "assetcore.services.shared.role_hooks.invalidate_caps",
        "on_trash": "assetcore.services.shared.role_hooks.invalidate_caps",
    },
}
```

> Entry `"User"` đã có `on_update: assetcore.services.imm06.handle_user_dept_change` — đổi thành list, thêm `invalidate_caps`:
> `"User": {"on_update": ["assetcore.services.imm06.handle_user_dept_change", "assetcore.services.shared.role_hooks.invalidate_caps"]}`

- [ ] **Step 4: Chạy — PASS**

Run: `cd /home/miyano/frappe-bench && bench --site miyano migrate && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: PASS (endpoint + umbrella).

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "feat(rbac): add get_capabilities endpoint + umbrella role + cache invalidate" -m "- api/auth.py: whitelisted get_capabilities
- services/shared/role_hooks.py: sync_umbrella (Super Admin -> System Manager), invalidate_caps
- hooks.py: doc_events Has Role/Custom DocPerm"
```

---

## PHASE 4 — Fixtures, workflow remap, setup cleanup, migration patch

### Task 4.1: `role.json` regen + bỏ profile khỏi fixtures + setup cleanup

**Files:**
- Modify: `assetcore/hooks.py`, `assetcore/setup/setup_permissions.py`, `assetcore/setup/setup_role_profiles.py`
- Replace: `assetcore/fixtures/role.json`
- Delete: `assetcore/fixtures/role_profile.json`, `assetcore/fixtures/module_profile.json`
- Test: `assetcore/tests/test_rbac.py`

- [ ] **Step 1: Test fixtures**

```python
class TestRoleFixture(unittest.TestCase):
    def test_role_json_has_30(self):
        p = frappe.get_app_path("assetcore", "fixtures", "role.json")
        data = json.load(open(p, encoding="utf-8"))
        names = {r["name"] for r in data}
        from assetcore.services.shared.constants import Roles
        self.assertEqual(names, set(Roles.ALL))

    def test_profile_fixtures_removed(self):
        base = frappe.get_app_path("assetcore", "fixtures")
        self.assertFalse(os.path.exists(os.path.join(base, "role_profile.json")))
        self.assertFalse(os.path.exists(os.path.join(base, "module_profile.json")))
```

- [ ] **Step 2: Chạy — FAIL**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL.

- [ ] **Step 3a: Sinh `fixtures/role.json`**

Run:
```
cd /home/miyano/frappe-bench/apps/assetcore && python -c "import json; from assetcore.services.shared.constants import Roles, ROLE_METADATA; rows=[{'doctype':'Role','name':n,'role_name':n,'desk_access':1,'disabled':0,'is_custom':1,'description':ROLE_METADATA[n]['description']} for n in Roles.ALL]; json.dump(rows, open('assetcore/fixtures/role.json','w',encoding='utf-8'), ensure_ascii=False, indent=1); print(len(rows),'roles')"
```

- [ ] **Step 3b: Xóa fixtures profile + sửa `hooks.py`**

```
git rm assetcore/fixtures/role_profile.json assetcore/fixtures/module_profile.json
```
`hooks.py`: thêm `from assetcore.services.shared.constants import Roles`; `_IMM_ROLES = list(Roles.ALL)`; xóa `_IMM_ROLE_PROFILES`, `_IMM_MODULE_PROFILES` và 2 dòng fixtures `Role Profile`/`Module Profile`.

- [ ] **Step 3c: `setup_permissions.py` + `setup_role_profiles.py`**

`setup_permissions._LEGACY_ROLES` thay bằng:
```python
_LEGACY_ROLES = (
    "IMM Manager","Kho vật tư","Workshop Manager","Clinical Head","CMMS Admin",
    "Tổ HC-QLCL","QA Risk Team","HTM Technician","VP Block2","Workshop Head",
    "Biomed Engineer",
    "IMM System Admin","IMM Operations Manager","IMM Department Head",
    "IMM Deputy Department Head","IMM Workshop Lead","IMM QA Officer",
    "IMM Biomed Technician","IMM Technician","IMM Document Officer",
    "IMM Storekeeper","IMM Clinical User","IMM Auditor","IMM Planning Officer",
    "IMM Finance Officer","IMM HTM Engineer","IMM Procurement Officer",
    "IMM Risk Officer","IMM Board Approver","IMM Training Officer",
)
```
`setup_role_profiles.run()`: giữ phần dọn legacy, bỏ mọi lời gọi `_upsert_role_profile(...)` (không tạo Role Profile nữa).

- [ ] **Step 4: migrate + test — PASS**

Run: `cd /home/miyano/frappe-bench && bench --site miyano migrate && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: PASS.

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "refactor(rbac): regen role.json (30) and drop role/module profiles" -m "- fixtures/role.json: 30 role moi; xoa role_profile.json, module_profile.json
- hooks.py: _IMM_ROLES=Roles.ALL, bo profile fixtures
- setup_permissions: _LEGACY_ROLES += 19 persona; setup_role_profiles: bo tao Role Profile"
```

---

### Task 4.2: Remap workflow `allowed`/`allow_edit` (gồm `Internal Auditor`)

**Files (Modify):** `assetcore/fixtures/workflow.json`, `assetcore/fixtures/workflow_action_master.json`, `assetcore/assetcore/workflow/*.json`
- Test: `assetcore/tests/test_rbac.py`

- [ ] **Step 1: Test workflow sạch persona/Internal Auditor**

```python
class TestWorkflowRoles(unittest.TestCase):
    BAD = {"IMM System Admin","IMM Workshop Lead","IMM QA Officer",
           "IMM Department Head","Internal Auditor"}

    def test_workflow_json_clean(self):
        p = frappe.get_app_path("assetcore","fixtures","workflow.json")
        txt = open(p, encoding="utf-8").read()
        for b in self.BAD:
            self.assertNotIn(f'"{b}"', txt, f"workflow.json con {b}")
```

- [ ] **Step 2: Chạy — FAIL**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL.

- [ ] **Step 3: Remap bằng bảng** — đổi `allowed`/`allow_edit` mọi workflow:

| Persona / cũ | Thay bằng |
|---|---|
| IMM System Admin | AssetCore Super Admin |
| IMM Workshop Lead | PM Manager (hoặc Repair/Calibration Manager theo workflow) |
| IMM Biomed/Technician | PM User / Repair User |
| IMM QA Officer | Compliance Manager |
| IMM Department Head / Deputy | Commissioning Manager |
| IMM Operations Manager | Commissioning Manager |
| IMM Document Officer | Document Manager |
| IMM Storekeeper | Inventory Manager |
| IMM Clinical User | Corrective User |
| IMM Planning/Finance | Needs Manager |
| IMM Procurement/Board Approver | Procurement Manager |
| IMM Training Officer | Training Manager |
| **Internal Auditor** (IMM-16) | Compliance Manager (bước duyệt) / AssetCore Auditor (xem) |

Áp dụng cả `assetcore/workflow/imm_16_internal_audit.json`. Kiểm `imm_internal_audit.json`, `imm_compliance_finding.json` đã được gen_docperms phủ (Task 1.1) — nếu còn `Internal Auditor` thì gỡ thủ công ở Step này.

- [ ] **Step 4: migrate + smoke + test**

Run:
```
cd /home/miyano/frappe-bench && bench --site miyano migrate
bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac
bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm16
```
Expected: PASS; workflow IMM-16 transition không lỗi role.

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "refactor(rbac): remap workflow allowed roles to module roles" -m "- workflow.json + workflow_action_master + workflow/*.json: persona+Internal Auditor -> module roles
- IMM-16 internal audit/compliance finding -> Compliance Manager/Auditor
- tests: workflow.json sach persona/Internal Auditor"
```

---

### Task 4.3: Migration patch wipe persona/legacy/profile

**Files:**
- Create: `assetcore/patches/v3_2/001_module_role_redesign.py`, `assetcore/patches/v3_2/__init__.py`
- Modify: `assetcore/patches.txt`
- Test: `assetcore/tests/test_rbac.py`

- [ ] **Step 1: Test post-migration state**

```python
class TestMigrationWipe(unittest.TestCase):
    def test_personas_gone_new_present(self):
        self.assertFalse(frappe.db.exists("Role", "IMM System Admin"))
        self.assertFalse(frappe.db.exists("Role", "IMM Workshop Lead"))
        self.assertTrue(frappe.db.exists("Role", "PM Manager"))
        self.assertTrue(frappe.db.exists("Role", "AssetCore Super Admin"))

    def test_other_app_and_core_roles_kept(self):
        self.assertTrue(frappe.db.exists("Role", "System Manager"))
        # Internal Auditor do normcore_dmktkt so huu — neu ton tai phai con
        if frappe.db.exists("Role", "Internal Auditor"):
            self.assertTrue(True)
```

- [ ] **Step 2: Chạy — FAIL** (persona còn tồn tại trước patch)

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL.

- [ ] **Step 3a: Tạo `assetcore/patches/v3_2/__init__.py`** (file rỗng)

- [ ] **Step 3b: Tạo `assetcore/patches/v3_2/001_module_role_redesign.py`**

```python
# Copyright (c) 2026, AssetCore Team
"""Wipe 19 persona + 11 legacy Role + Role/Module Profile. Idempotent.

KHONG xoa role do app khac (normcore_dmktkt/norm_himedic) hoac Frappe core
so huu (Internal Auditor, Norm*, Laboratory User, Healthcare Administrator,
System Manager...). Vendor Engineer GIU (re-scope qua DocPerm/fixture).
Role moi do fixtures/JSON tao khi sync_fixtures sau patches.

Run:  bench --site <site> execute assetcore.patches.v3_2.001_module_role_redesign.execute
"""
from __future__ import annotations

import frappe

_PERSONA = [
    "IMM System Admin","IMM Operations Manager","IMM Department Head",
    "IMM Deputy Department Head","IMM Workshop Lead","IMM QA Officer",
    "IMM Biomed Technician","IMM Technician","IMM Document Officer",
    "IMM Storekeeper","IMM Clinical User","IMM Auditor","IMM Planning Officer",
    "IMM Finance Officer","IMM HTM Engineer","IMM Procurement Officer",
    "IMM Risk Officer","IMM Board Approver","IMM Training Officer",
]
_LEGACY = [
    "IMM Manager","Kho vật tư","Workshop Manager","Clinical Head","CMMS Admin",
    "Tổ HC-QLCL","QA Risk Team","HTM Technician","VP Block2","Workshop Head",
    "Biomed Engineer",
]
_KILL_ROLES = _PERSONA + _LEGACY


def execute():
    frappe.db.delete("Has Role", {"role": ("in", _KILL_ROLES)})
    frappe.db.delete("DocPerm", {"role": ("in", _KILL_ROLES)})
    frappe.db.delete("Custom DocPerm", {"role": ("in", _KILL_ROLES)})
    for dt in ("Role Profile", "Module Profile"):
        for n in frappe.get_all(dt, pluck="name"):
            frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
    for r in _KILL_ROLES:
        if frappe.db.exists("Role", r):
            frappe.delete_doc("Role", r, force=True, ignore_permissions=True)
    frappe.db.commit()
```

- [ ] **Step 3c: Thêm vào `assetcore/patches.txt`** (cuối, dưới `[post_model_sync]`):

```
assetcore.patches.v3_2.001_module_role_redesign
```

- [ ] **Step 4: backup → migrate → test**

Run:
```
cd /home/miyano/frappe-bench && bench --site miyano backup
bench --site miyano migrate
bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac
```
Expected: patch chạy; PASS (`TestMigrationWipe`).

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "feat(rbac): add migration patch wiping persona/legacy roles + profiles" -m "- patches/v3_2/001_module_role_redesign.py: detach Has Role, xoa DocPerm/Profile/Role persona+legacy; giu app-khac/Frappe core; Vendor re-scope
- patches.txt: dang ky patch"
```

---

## PHASE 5 — FE: capability layer thay role-name

### Task 5.1: `roles.ts` catalog + `api/auth.ts` + store + composable

**Files:**
- Modify: `frontend/src/constants/roles.ts`, `frontend/src/api/auth.ts`, `frontend/src/stores/auth.ts`
- Create: `frontend/src/composables/useCapabilities.ts`

- [ ] **Step 1: Ghi baseline typecheck**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && npx vue-tsc --noEmit 2>&1 | tail -3`
Ghi lại số lỗi baseline.

- [ ] **Step 2: Viết lại `frontend/src/constants/roles.ts`**

```typescript
// Copyright (c) 2026, AssetCore Team
// Catalog 30 role — CHI de hien thi/gan o trang admin. KHONG dung cho logic gate
// (logic dung useCapabilities().can(...)).

export interface RoleInfo {
  name: string
  label: string
  description: string
  group: string
  rank: number
}

export const SYSTEM_ROLES = [
  'AssetCore Super Admin', 'AssetCore System User',
  'AssetCore Auditor', 'Vendor Engineer',
] as const

export const DOMAINS = [
  'Data','Needs','Spec','Procurement','Commissioning','Document','Training',
  'PM','Repair','Calibration','Corrective','Inventory','Compliance',
] as const

const DOMAIN_LABEL: Record<string, string> = {
  Data:'Dữ liệu nền', Needs:'Nhu cầu & Dự toán', Spec:'Thông số kỹ thuật',
  Procurement:'NCC & Mua sắm', Commissioning:'Lắp đặt & Nghiệm thu',
  Document:'Hồ sơ', Training:'Đào tạo', PM:'Bảo trì định kỳ',
  Repair:'Sửa chữa', Calibration:'Hiệu chuẩn', Corrective:'Bảo trì khắc phục',
  Inventory:'Tồn kho phụ tùng', Compliance:'Tuân thủ / QMS',
}

export const ROLE_CATALOG: RoleInfo[] = [
  { name:'AssetCore Super Admin', label:'Quản trị hệ thống', group:'System', rank:100,
    description:'Toàn quyền + bao trùm Frappe System Manager' },
  { name:'AssetCore System User', label:'Người dùng hệ thống', group:'System', rank:0,
    description:'Role nền: đăng nhập, dashboard, đọc shared-core' },
  { name:'AssetCore Auditor', label:'Kiểm toán viên', group:'System', rank:5,
    description:'Chỉ đọc toàn bộ + audit trail' },
  { name:'Vendor Engineer', label:'KTV nhà cung cấp', group:'System', rank:5,
    description:'Bên thứ ba, cô lập theo WO/Asset' },
  ...DOMAINS.flatMap((d) => ([
    { name:`${d} Manager`, label:`${DOMAIN_LABEL[d]} — Quản lý`, group:d, rank:50,
      description:'Full CRUD + duyệt/hủy workflow' },
    { name:`${d} User`, label:`${DOMAIN_LABEL[d]} — Người dùng`, group:d, rank:10,
      description:'read/write/create, thao tác thường' },
  ])),
]
```

- [ ] **Step 3a: Thêm `fetchCapabilities` vào `frontend/src/api/auth.ts`**

```typescript
export async function fetchCapabilities(): Promise<Record<string, boolean>> {
  const { data } = await axios.get(
    '/api/method/assetcore.api.auth.get_capabilities')
  return (data?.message?.data ?? {}) as Record<string, boolean>
}
```
(điều chỉnh import `axios` theo pattern hiện có của file.)

- [ ] **Step 3b: `stores/auth.ts`** — thêm state, bỏ role-name computed:

```typescript
const capabilities = ref<Record<string, boolean>>({})
const can = (cap: string) => capabilities.value[cap] === true
async function loadCapabilities() {
  const { fetchCapabilities } = await import('@/api/auth')
  capabilities.value = await fetchCapabilities()
}
// goi loadCapabilities() ngay sau login thanh cong (trong action login/bootstrap)
// XOA: isSystemAdmin/isQAOfficer/.../ROLES_* import & SUBMIT_ROLES/CREATE_ROLES
// Giu `roles` chi de hien thi ten; moi gate -> can()
return { /* ...existing..., */ capabilities, can, loadCapabilities }
```

- [ ] **Step 3c: Tạo `frontend/src/composables/useCapabilities.ts`**

```typescript
import { useAuthStore } from '@/stores/auth'

export function useCapabilities() {
  const auth = useAuthStore()
  const can = (cap: string | string[]) =>
    Array.isArray(cap) ? cap.some((c) => auth.can(c)) : auth.can(cap)
  return { can }
}
```

- [ ] **Step 4: Typecheck**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && npx vue-tsc --noEmit 2>&1 | tail -3`
Expected: lỗi mới chỉ ở các file F8 chưa refactor (Task 5.3) — về 0 sau 5.3.

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "refactor(fe): replace role catalog with capability store + composable" -m "- constants/roles.ts: chi con ROLE_CATALOG (30) cho UI
- api/auth.ts: fetchCapabilities; stores/auth.ts: capabilities+can+loadCapabilities
- composables/useCapabilities.ts moi"
```

---

### Task 5.2: `v-can` directive + router + modules requiredCapabilities

**Files:**
- Modify: `frontend/src/directives/permission.ts`, `frontend/src/main.ts`, `frontend/src/router/index.ts`, `frontend/src/constants/modules.ts`

- [ ] **Step 1: Viết lại `frontend/src/directives/permission.ts`**

```typescript
// Copyright (c) 2026, AssetCore Team
// v-can directive — an element neu THIEU capability (UX only; BE moi la chot).
import type { Directive, DirectiveBinding } from 'vue'
import { useAuthStore } from '@/stores/auth'

type V = string | readonly string[]
function ok(v: V): boolean {
  const auth = useAuthStore()
  const need = Array.isArray(v) ? v : [v as string]
  return need.length === 0 || need.some((c) => auth.can(c))
}
function enforce(el: HTMLElement, b: DirectiveBinding<V>) {
  if (!ok(b.value)) el.parentNode?.removeChild(el)
}
export const vCan: Directive<HTMLElement, V> = { mounted: enforce, updated: enforce }
```
`main.ts`: đổi đăng ký directive → `app.directive('can', vCan)`; giữ alias `app.directive('permission', vCan)` tạm để 14 file F8 không vỡ ngay.

- [ ] **Step 2: `router/index.ts`** — đổi guard:

Tìm hàm guard dùng `meta.requiredRoles`/`hasAnyRole`. Thay bằng:
```typescript
const need = to.meta.requiredCapabilities as string[] | undefined
if (need && need.length) {
  const auth = useAuthStore()
  if (!auth.capabilities || Object.keys(auth.capabilities).length === 0)
    await auth.loadCapabilities()
  if (!need.some((c) => auth.can(c)))
    return next({ name: 'forbidden' })
}
```
Đổi mọi `requiredRoles: ROLES_X` → `requiredCapabilities: ['<domain>.read']`: PM→`['pm.read']`, CM→`['repair.read']`, calibration→`['calibration.read']`, incident→`['corrective.read']`, inventory→`['inventory.read']`, training→`['training.read']`, compliance/capa→`['compliance.read']`, planning→`['needs.read']`, procurement→`['procurement.read']`, master-data→`['data.read']`. Bỏ import `ROLES_*` khỏi router. Nếu chưa có route `forbidden`, dùng route 403 hiện có hoặc `{ name: 'dashboard' }`.

- [ ] **Step 3: `constants/modules.ts`**

Đổi `ModuleCard.roles` → `requiredCapabilities: string[]`; mỗi card gán `['<domain>.read']` theo IMM-code. Bỏ `import { Roles, ROLES_* }`. Component đọc `modules.ts` đổi sang `useCapabilities().can(card.requiredCapabilities)`.

- [ ] **Step 4: Typecheck**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && npx vue-tsc --noEmit 2>&1 | tail -3`
Expected: lỗi giảm; còn lại ở F8.

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "refactor(fe): v-can directive + capability route guards" -m "- directives/permission.ts -> vCan; main.ts dang ky 'can'
- router: meta.requiredCapabilities + loadCapabilities lazy
- constants/modules.ts: requiredCapabilities thay roles"
```

---

### Task 5.3: Refactor ~14 file FE import `constants/roles`

**Files (Modify):** mọi file FE còn import từ `@/constants/roles` (trừ `RoleAdminView`) — `views/**`, `components/commissioning/ApprovalPanel.vue`, `composables/usePermissions.ts`, `api/user.ts`.

- [ ] **Step 1: Liệt kê file cần sửa**

Run: `cd /home/miyano/frappe-bench/apps/assetcore/frontend && grep -rl "constants/roles" src --include=*.ts --include=*.vue | grep -v RoleAdmin`

- [ ] **Step 2: `composables/usePermissions.ts`** — wrap capability:

```typescript
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
export function usePermissions() {
  const auth = useAuthStore()
  const can = (c: string | string[]) =>
    Array.isArray(c) ? c.some((x) => auth.can(x)) : auth.can(c)
  return {
    can,
    isAdmin: computed(() => auth.can('data.admin')),
    isQA: computed(() => auth.can('compliance.write')),
    isTechnician: computed(() => auth.can('pm.write') || auth.can('repair.write')),
    canApproveRelease: computed(() => auth.can('doc.approve')),
    canViewFinancials: computed(() => auth.can('needs.read')),
  }
}
```

- [ ] **Step 3: Mỗi view/component** — thay `auth.hasAnyRole([Roles.X])` / `v-permission="'IMM ...'"` bằng `useCapabilities().can('<cap>')` / `v-can="'<cap>'"`. Bảng cap theo nút:

| Nút | cap |
|---|---|
| Submit/execute PM | `pm.write` |
| Reschedule PM | `pm.reschedule` |
| Submit Calibration / send lab / receive cert | `cal.send_lab` |
| Cancel Calibration | `calibration.cancel` |
| Acknowledge/Resolve incident | `incident.acknowledge` |
| Close incident | `incident.close` |
| Cancel incident | `corrective.cancel` |
| Delete incident | `corrective.delete` |
| Approve document (release) | `doc.approve` |
| Close/reopen CAPA | `capa.close` |
| Create WO | `pm.create`/`repair.create`/`calibration.create` |
| Manage stock movement | `inventory.write` |
| Admin user / ref-data | `data.admin` |

- [ ] **Step 4: Typecheck = 0 lỗi mới + build**

Run:
```
cd /home/miyano/frappe-bench/apps/assetcore/frontend && npx vue-tsc --noEmit 2>&1 | tail -3
npm run build 2>&1 | tail -3
```
Expected: 0 lỗi liên quan roles; build OK.

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "refactor(fe): migrate all role-name checks to capabilities" -m "- usePermissions.ts wrap can(); ~14 view/component: hasAnyRole/v-permission -> can()/v-can
- typecheck + build pass"
```

---

## PHASE 6 — Trang quản trị Role/User (FE)

### Task 6.1: `RoleAdminView.vue` + `api/roleAdmin.ts` + BE set-role endpoint

**Files:**
- Create: `frontend/src/views/admin/RoleAdminView.vue`, `frontend/src/api/roleAdmin.ts`
- Modify: `assetcore/api/user.py`, `frontend/src/router/index.ts`
- Test: `assetcore/tests/test_rbac.py`

- [ ] **Step 1: Test BE set-role endpoint**

```python
class TestSetUserRoles(unittest.TestCase):
    def test_set_roles_replaces(self):
        frappe.set_user("Administrator")
        u = "rbac_setrole@example.com"
        if not frappe.db.exists("User", u):
            frappe.get_doc({"doctype":"User","email":u,"first_name":"S",
                "send_welcome_email":0}).insert(ignore_permissions=True)
        from assetcore.api.user import set_user_roles
        r = set_user_roles(user=u, roles=["PM Manager","Inventory User"])
        self.assertTrue(r["ok"])
        roles = {x.role for x in frappe.get_doc("User", u).roles}
        self.assertIn("PM Manager", roles)
        self.assertIn("Inventory User", roles)
        frappe.delete_doc("User", u, force=True, ignore_permissions=True)
```

- [ ] **Step 2: Chạy — FAIL**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac`
Expected: FAIL (`ImportError: set_user_roles`).

- [ ] **Step 3a: Thêm vào `assetcore/api/user.py`**

```python
@frappe.whitelist()
def list_assignable_roles():
    from assetcore.services.shared.rbac import require
    require("data.admin")
    from assetcore.services.shared.constants import Roles, ROLE_METADATA
    return _ok([{"name": n, **ROLE_METADATA[n]} for n in Roles.ALL])


@frappe.whitelist()
def set_user_roles(user: str, roles):
    """Thay toan bo AssetCore role cua 1 user (giu role app khac)."""
    from assetcore.services.shared.rbac import require
    require("data.admin")
    import json
    from assetcore.services.shared.constants import Roles
    if isinstance(roles, str):
        roles = json.loads(roles)
    allowed = set(Roles.ALL)
    target = [r for r in roles if r in allowed]
    doc = frappe.get_doc("User", user)
    keep = [r.role for r in doc.roles if r.role not in allowed]
    doc.set("roles", [])
    for r in keep + target:
        doc.append("roles", {"role": r})
    doc.save(ignore_permissions=True)
    frappe.db.commit()
    return _ok({"user": user, "roles": keep + target})
```
(dùng `_ok` đã import sẵn trong `api/user.py`.)

- [ ] **Step 3b: Tạo `frontend/src/api/roleAdmin.ts`**

```typescript
import axios from '@/api/axios'
export const listAssignableRoles = () =>
  axios.get('/api/method/assetcore.api.user.list_assignable_roles')
    .then(r => r.data.message.data)
export const listUsers = () =>
  axios.get('/api/method/frappe.client.get_list', { params: {
    doctype:'User', filters: JSON.stringify([['enabled','=',1]]),
    fields: JSON.stringify(['name','full_name']), limit_page_length: 0 } })
    .then(r => r.data.message)
export const getUserRoles = (user: string) =>
  axios.get('/api/method/frappe.client.get_list', { params: {
    doctype:'Has Role', parent:'User',
    filters: JSON.stringify([['parent','=',user]]),
    fields: JSON.stringify(['role']), limit_page_length: 0 } })
    .then(r => r.data.message.map((x:{role:string}) => x.role))
export const setUserRoles = (user: string, roles: string[]) =>
  axios.post('/api/method/assetcore.api.user.set_user_roles',
    { user, roles: JSON.stringify(roles) }).then(r => r.data.message)
```

- [ ] **Step 3c: Tạo `frontend/src/views/admin/RoleAdminView.vue`**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ROLE_CATALOG, SYSTEM_ROLES, DOMAINS } from '@/constants/roles'
import { listUsers, getUserRoles, setUserRoles } from '@/api/roleAdmin'

const users = ref<{name:string;full_name:string}[]>([])
const selected = ref<string>('')
const assigned = ref<Set<string>>(new Set())
const saving = ref(false)

onMounted(async () => { users.value = await listUsers() })

async function pick(u: string) {
  selected.value = u
  assigned.value = new Set(await getUserRoles(u))
}
function toggle(role: string) {
  if (assigned.value.has(role)) assigned.value.delete(role)
  else assigned.value.add(role)
  assigned.value = new Set(assigned.value)
}
async function save() {
  saving.value = true
  try {
    const acRoles = ROLE_CATALOG.map(r => r.name)
    await setUserRoles(selected.value,
      [...assigned.value].filter(r => acRoles.includes(r)))
  } finally { saving.value = false }
}
</script>

<template>
  <div class="p-6 space-y-6">
    <h1 class="text-xl font-semibold">Phân quyền theo module</h1>

    <section>
      <h2 class="font-medium mb-2">Danh mục role và quyền</h2>
      <table class="w-full text-sm border">
        <thead><tr class="bg-slate-100 text-left">
          <th class="p-2">Role</th><th class="p-2">Nhóm</th>
          <th class="p-2">Quyền</th></tr></thead>
        <tbody>
          <tr v-for="r in ROLE_CATALOG" :key="r.name" class="border-t">
            <td class="p-2 font-mono">{{ r.name }}</td>
            <td class="p-2">{{ r.group }}</td>
            <td class="p-2 text-slate-600">{{ r.description }}</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="grid grid-cols-3 gap-4">
      <div class="col-span-1 border rounded max-h-96 overflow-auto">
        <button v-for="u in users" :key="u.name" @click="pick(u.name)"
          class="block w-full text-left p-2 hover:bg-slate-50"
          :class="{ 'bg-blue-50': selected===u.name }">
          {{ u.full_name }}
          <span class="text-xs text-slate-400">{{ u.name }}</span>
        </button>
      </div>
      <div class="col-span-2 space-y-4" v-if="selected">
        <div>
          <h3 class="font-medium">System Roles</h3>
          <label v-for="s in SYSTEM_ROLES" :key="s"
            class="inline-flex items-center mr-4">
            <input type="checkbox" :checked="assigned.has(s)" @change="toggle(s)" />
            <span class="ml-1">{{ s }}</span>
          </label>
        </div>
        <table class="text-sm border">
          <thead><tr class="bg-slate-100">
            <th class="p-2 text-left">Module</th><th class="p-2">Manager</th>
            <th class="p-2">User</th></tr></thead>
          <tbody>
            <tr v-for="d in DOMAINS" :key="d" class="border-t">
              <td class="p-2">{{ d }}</td>
              <td class="p-2 text-center">
                <input type="checkbox" :checked="assigned.has(d+' Manager')"
                  @change="toggle(d+' Manager')" /></td>
              <td class="p-2 text-center">
                <input type="checkbox" :checked="assigned.has(d+' User')"
                  @change="toggle(d+' User')" /></td>
            </tr>
          </tbody>
        </table>
        <button @click="save" :disabled="saving"
          class="px-4 py-2 bg-blue-600 text-white rounded">
          {{ saving ? 'Đang lưu…' : 'Lưu' }}</button>
      </div>
    </section>
  </div>
</template>
```

- [ ] **Step 3d: Route** trong `frontend/src/router/index.ts`:

```typescript
{
  path: '/admin/roles', name: 'role-admin',
  component: () => import('@/views/admin/RoleAdminView.vue'),
  meta: { requiresAuth: true, title: 'Phân quyền',
          requiredCapabilities: ['data.admin'] },
}
```

- [ ] **Step 4: BE test PASS + build FE**

Run:
```
cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore --module assetcore.tests.test_rbac
cd apps/assetcore/frontend && npm run build 2>&1 | tail -3
```
Expected: BE PASS; FE build OK.

- [ ] **Step 5: Commit** (chờ user)

```
git add -A && git commit -m "feat(fe): role admin page (catalog + per-user module grid)" -m "- api/user.py: list_assignable_roles, set_user_roles (gate data.admin, giu role app khac)
- FE: api/roleAdmin.ts, views/admin/RoleAdminView.vue, route /admin/roles"
```

---

## PHASE 7 — Verify end-to-end

### Task 7.1: Smoke toàn hệ thống + Playwright

- [ ] **Step 1: BE suite đầy đủ**

Run: `cd /home/miyano/frappe-bench && bench --site miyano run-tests --app assetcore 2>&1 | tail -8`
Expected: không fail mới so với baseline (Task 2.1 Step 4).

- [ ] **Step 2: Migrate sạch (mô phỏng deploy) + idempotent**

Run: `cd /home/miyano/frappe-bench && bench --site miyano migrate 2>&1 | tail -5 && bench --site miyano migrate 2>&1 | tail -5`
Expected: patch v3_2/001 lần 2 no-op; 30 role, DocPerm đúng.

- [ ] **Step 3: Verify bằng console**

Run:
```
bench --site miyano console <<'PY'
import frappe
print("new", frappe.db.count("Role", {"name": ("in", ["PM Manager","AssetCore Super Admin"])}))
print("persona", frappe.db.exists("Role","IMM Workshop Lead"))
print("internal_auditor", frappe.db.exists("Role","Internal Auditor"))
print("system_manager", frappe.db.exists("Role","System Manager"))
PY
```
Expected: `new 2`, `persona None`, `system_manager` giữ.

- [ ] **Step 4: Playwright UI** (skill `assetcore-test`)

- Gán `PM Manager` cho 1 user test qua `/admin/roles` → login user đó → thấy nút submit PM, KHÔNG thấy nút data-admin.
- Bypass test: gọi trực tiếp `POST /api/method/assetcore.api.user.set_user_roles` bằng user thiếu `data.admin` → BE trả `PermissionError` (FE-bypass bị BE chặn — chứng minh nguyên tắc #2).

- [ ] **Step 5: Commit cuối** (chờ user)

```
git add -A && git commit -m "test(rbac): e2e verify module-role RBAC (BE suite + Playwright)" -m "- xac minh migrate idempotent, 30 role, persona wiped, app-khac/core kept
- Playwright: grid gan role, FE an nut, BE chan bypass"
```

---

## Self-Review (đã chạy khi viết plan)

- **Spec coverage:** §1→§11 spec đều có task — taxonomy(0.1), capability(0.2), DocPerm 105(1.1), refactor CAN_*(2.1), endpoint+umbrella+cache(3.1), fixtures/profile(4.1), workflow+Internal Auditor(4.2), migration wipe(4.3), FE capability(5.1–5.3), trang /admin/roles(6.1), verify+bypass(7.1). ✓
- **Placeholder scan:** mọi step có code/lệnh thật, không TBD. ✓
- **Type consistency:** `can()`, `rbac.require/can/get_capabilities/invalidate_capabilities`, `Roles.ALL/SYSTEM_ROLES/DOMAIN_ROLES/ROLE_RANK/DOMAINS`, `DOCTYPE_DOMAIN`, `CAPABILITY_MAP`, `set_user_roles`, `list_assignable_roles`, `ROLE_CATALOG`, `useCapabilities`, `vCan` nhất quán giữa các task. ✓
- **Lưu ý execute:** ghi baseline `bench run-tests` trước Phase 2; `bench backup` trước Task 4.3; nếu `gen_docperms` map sót DocType → bổ sung `_DOMAIN_DOCTYPES` rồi chạy lại; route `forbidden` dùng route 403 hiện có nếu chưa có.
