---
name: assetcore-tester
description: Write or run tests for AssetCore — unit tests for services, integration tests for DocType lifecycle hooks, workflow smoke tests, and UAT scripts. Use this whenever the user says "viết test", "TDD", "kiểm thử", "test case cho IMM-XX", "fixture", "mock", "test fails", "run tests", "bench run-tests", or wants to verify behavior before deployment. Strongly use this skill before considering any backend feature complete — CLAUDE.md §17 mandates TDD.
---

# AssetCore Test Writer

Frappe ships its own test runner on top of `unittest`. Tests run in a real DB transaction that's rolled back at the end. Follow this guide so tests are deterministic, fast, and isolated.

## Project layout

```
assetcore/tests/
├── __init__.py
├── test_imm00.py        # foundation DocTypes (Category, Dept, Location, Supplier)
├── test_workflows.py    # workflow smoke tests (states + transitions + docstatus)
└── test_immXX.py        # one file per module (Wave 1: imm04/05/08/09/11/12; not all exist yet)

assetcore/uat_test.py    # ad-hoc UAT helper used standalone
assetcore/scripts/uat/
└── uat_immXX.py         # end-to-end scenarios for human-led UAT (per module)
```

**State of test coverage (May 2026):** only `test_imm00.py` and `test_workflows.py` are committed. New module work should add `test_immXX.py` per CLAUDE.md §17 (TDD). The pattern below is what those new files should look like.

## Running tests

```bash
# All tests in the app
bench --site <site> run-tests --app assetcore

# One module
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm09

# One class or method
bench --site <site> run-tests --app assetcore --module assetcore.tests.test_imm09 --test TestRepairCreation

# Skip ERPNext schema checks (much faster)
bench --site <site> run-tests --app assetcore --skip-test-records
```

## Standard test file template

```python
# assetcore/tests/test_immXX.py
"""IMM-XX module tests.

Run: bench --site <site> run-tests --app assetcore --module assetcore.tests.test_immXX
"""
from __future__ import annotations
import unittest
import frappe
from frappe.utils import now_datetime


class TestRepairCreation(unittest.TestCase):
    """BR-09-01: WO must have either incident_report or source_pm_wo."""

    @classmethod
    def setUpClass(cls):
        # Build long-lived fixtures here (asset, category, location)
        cls.asset = _make_asset()

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)

    def setUp(self):
        # Per-test resources
        frappe.set_user("Administrator")

    def tearDown(self):
        # Clean up records this test may have created
        for wo in frappe.get_all("Asset Repair", filters={"asset_ref": self.asset.name}):
            frappe.delete_doc("Asset Repair", wo.name, force=True, ignore_permissions=True)

    def test_create_without_source_fails(self):
        from frappe.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            frappe.get_doc({
                "doctype": "Asset Repair",
                "asset_ref": self.asset.name,
                "repair_type": "Corrective",
                "priority": "Normal",
                "failure_description": "...",
            }).insert(ignore_permissions=True)

    def test_create_with_incident_succeeds(self):
        ir = _make_incident(self.asset.name)
        wo = frappe.get_doc({
            "doctype": "Asset Repair",
            "asset_ref": self.asset.name,
            "repair_type": "Corrective",
            "priority": "Normal",
            "failure_description": "blah",
            "incident_report": ir.name,
        }).insert(ignore_permissions=True)
        self.assertEqual(wo.status, "Open")
        self.assertIsNotNone(wo.open_datetime)


# ── helpers ────────────────────────────────────────────────────────────────
def _make_asset() -> "frappe.Document":
    return frappe.get_doc({
        "doctype": "AC Asset",
        "asset_name": "_Test Asset IMM09",
        "asset_category": "_Test Category",
        "serial_no": f"TEST-{frappe.utils.random_string(8)}",
    }).insert(ignore_permissions=True)


def _make_incident(asset_ref: str) -> "frappe.Document":
    return frappe.get_doc({
        "doctype": "Incident Report",
        "asset_ref": asset_ref,
        "description": "test incident",
    }).insert(ignore_permissions=True)
```

## Conventions

- **Test class** = behavior being tested (`TestRepairCreation`, `TestSlaCalculation`).
- **Test method** = `test_<scenario>_<expected_outcome>` (`test_create_without_source_fails`).
- **Use `setUpClass` for fixtures shared across tests**, `setUp` for per-test state. Tests run in random order — never rely on order.
- **Always `ignore_permissions=True`** when inserting test data. Tests bypass RBAC; permission tests use `frappe.set_user(...)` explicitly.
- **Prefix test record names with `_Test`** so cleanup hooks find them and they don't leak into desk views.
- **Assert against the service layer when possible** — service tests are 10× faster than DocType tests because they skip Document hooks.
- **Don't mock the database.** Frappe wraps each test in a savepoint; rollback is automatic. Mocks lie about migrations and constraint behavior.

## Service-layer tests (preferred — fast)

```python
from assetcore.services.imm09 import (
    get_sla_target, RepairStatus, validate_repair_source,
)
from assetcore.services.shared import ErrorCode, ServiceError

class TestSlaMatrix(unittest.TestCase):
    def test_class3_emergency_is_4h(self):
        self.assertEqual(get_sla_target("Class III", "Emergency"), 4.0)

    def test_unknown_combo_uses_default(self):
        self.assertEqual(get_sla_target("Class IX", "Whenever"), 480.0)


class TestServiceErrorContract(unittest.TestCase):
    def test_close_already_closed_raises_bad_state(self):
        # arrange: a completed WO
        wo = _make_completed_wo()
        from assetcore.services.imm09 import close_work_order
        with self.assertRaises(ServiceError) as cm:
            close_work_order(wo.name, repair_summary="x", root_cause_category="y", dept_head_name="z")
        self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE)
```

These don't need DB access for pure-function tests, and only need a savepoint for service tests — they should be the majority. Always assert on `e.code` (machine-readable) rather than `e.message` (Vietnamese, may be reworded for UX).

## Permission tests (use `frappe.set_user`)

```python
def test_technician_cannot_close_wo(self):
    frappe.set_user("technician_user@test.com")
    try:
        with self.assertRaises(frappe.PermissionError):
            close_work_order(self.wo.name, ...)
    finally:
        frappe.set_user("Administrator")
```

Always reset to Administrator in `finally` — leaking user state breaks subsequent tests.

## Workflow smoke tests

`tests/test_workflows.py` validates every workflow's state/transition counts, docstatus rules, and role existence. This is a deploy gate — it must pass before any release.

When you add a new workflow:

1. Count the states and transitions in the workflow JSON (exact count, not an estimate).
2. Add an entry to `EXPECTED_WORKFLOWS` with the verified counts:
   ```python
   "IMM-XX Foo Workflow": {"doctype": "Foo DocType", "min_states": 7, "min_transitions": 9},
   ```
3. Run the smoke test immediately: `bench --site <site> run-tests --module assetcore.tests.test_workflows`

**Also check:** when a new workflow is added, verify `hooks.py` fixtures has entries in ALL THREE lists: `Workflow`, `Workflow State`, `Workflow Action Master`. A workflow missing from fixtures will import on dev (where JSON files are live-loaded) but fail on a fresh site — the test won't catch this gap.

Don't write your own workflow tests — extend the shared one.

## UAT scripts

For human-led acceptance testing, write a script that runs an end-to-end scenario without any test framework:

```python
# assetcore/scripts/uat/uat_imm09.py
"""Run: bench --site <site> execute assetcore.scripts.uat.uat_imm09.run"""
import frappe
from frappe.utils import now_datetime

def run() -> None:
    print("UAT IMM-09: full repair flow")
    # 1. Create incident
    # 2. Open WO from incident
    # 3. Assign technician
    # 4. Submit diagnosis
    # 5. Request parts → consume → close
    print("✅ All steps passed")
    frappe.db.commit()  # required for `bench execute`
```

UAT scripts must `frappe.db.commit()` at the end (web requests auto-commit; CLI doesn't).

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Test passes alone, fails in suite | Leaked user / shared fixture | Reset `frappe.set_user("Administrator")`; use `setUpClass` for shared, `setUp` for per-test |
| `DoesNotExistError` for clean-looking fixture | Missing parent record (Category, Department) | Build the dependency chain in `setUpClass` |
| `LinkValidationError` | Link target not inserted yet | Insert parents before children; use `ignore_permissions=True` |
| Random ordering breaks tests | Tests assume order | Don't rely on order; build self-contained fixtures |
| `bench run-tests` is slow | Builds ERPNext test records every time | Add `--skip-test-records` for iteration |
| Workflow tests fail after JSON edit | Forgot to `bench migrate` | Run migrate; workflows are reloaded from JSON |

## Coverage targets

Prioritize:
1. **Validators** in `services/immXX.py` — every BR-XX-NN should have a passing + failing test.
2. **Service entrypoints** that change state — assert the resulting status, lifecycle event written, audit trail row.
3. **Permission gates** — at least one positive + one negative role test per mutating endpoint.
4. **Status transitions** — ensure invalid transitions raise `BAD_STATE`.

Skip:
- Trivial getters (no logic).
- Frappe framework internals.
- DocType property accessors that just read fields.

## Before claiming a feature is done

- [ ] All new tests pass: `bench --site <site> run-tests --app assetcore --module assetcore.tests.test_immXX`
- [ ] Workflow smoke test still passes: `... --module assetcore.tests.test_workflows`
- [ ] If a new workflow was added: `EXPECTED_WORKFLOWS` updated AND all 3 fixture lists in `hooks.py` updated
- [ ] No bare `except: pass` introduced in new code
- [ ] Manual UAT script (if applicable) ran clean

## Where to look for live examples

- `assetcore/tests/test_imm00.py` — DocType-level pattern (setUp/tearDown, naming series)
- `assetcore/tests/test_workflows.py` — parameterized smoke testing
- `assetcore/scripts/uat/uat_imm09.py` — end-to-end scenario

---

## Cross-skill conventions

Read [`/.claude/skills/CONVENTIONS.md`](../CONVENTIONS.md) for project-wide rules. Especially relevant to this skill:

- §6. Test Standards — service unit + workflow smoke + API integration + permission gate per module
- §7. Doc sync — adding ErrorCode requires test asserting it raises

### Module-specific gotchas
- Test coverage gap: IMM-04, 05, 06, 08, 09, 11, 12 have no dedicated `test_imm<XX>.py` file — only `test_workflows.py` smoke
- Wave 2 modules (IMM-01, 02, 03, 06) need test scaffolds before further changes
- Tests run via `bench --site assetcore.local run-tests --app assetcore`
- Use `frappe.set_user("Administrator")` in setUp; restore via tearDown to avoid permission test bleed
