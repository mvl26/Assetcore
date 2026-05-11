---
name: assetcore-integration-patterns
description: |
  Design cross-module integrations between IMM modules — gates (e.g., IMM-04→IMM-08 PM trigger), shared constants, event-driven hooks, dependency graph, and how IMM-16 compliance crosses all other modules. Use whenever the user asks "imm-XX gọi imm-yy", "module integration", "cross-module data", "dependency between IMM modules", "shared enum", "cross-module test", "event flow", "IMM-04 trigger PM", "compliance gate", "asset status propagation". Use BEFORE designing any feature that touches >1 IMM module.
---

# AssetCore Cross-Module Integration Patterns

IMM modules are **not** isolated — they form a graph of triggers, gates, and shared state. Most production bugs come from getting integration wrong (circular imports, status mismatches, CAPA deadlocks). Use this skill to design any feature that touches more than one IMM module.

## Purpose

Single-module work uses `assetcore-be-module` / `assetcore-fe-module`. Cross-module work has its own failure modes:

- Circular import between two services
- Status string drift between caller and callee
- Compliance gate (IMM-16) blocks an action the user expects to succeed
- Hook fires during cancel/amend and produces phantom events
- Module A calls into Module B at module load time, breaking startup

This skill centralizes the patterns that work and the anti-patterns that don't.

## When to invoke

Trigger phrases:
- "IMM-04 trigger PM in IMM-08"
- "imm-09 gọi imm-15 để trừ kho"
- "cross-module data flow"
- "dependency between IMM-12 and IMM-16"
- "shared enum / constant"
- "compliance gate blocks WO"
- "asset status propagation across modules"
- "circular import between services"
- "event flow IMM-04 → IMM-08 → IMM-11"

Use this skill **before** writing any code that imports a service from another IMM module.

## Module dependency graph

```
IMM-00 (Master / Foundation) ── shared services + lifecycle helpers for all
     │
     ├── IMM-01 (Needs) ──→ IMM-02 (Specs) ──→ IMM-03 (PO/Contract)
     │                                              │
     │                                              └─→ IMM-04 (Installation triggered by PO)
     │
     ├── IMM-04 (Installation) ──→ IMM-05 (Registration / Documentation)
     │       │
     │       ├──→ IMM-08 (PM Schedule auto-created on commissioning)
     │       └──→ IMM-11 (Calibration Schedule auto-created for Class B+)
     │
     ├── IMM-08 (PM) ──→ IMM-09 (PM finds defect → creates CM Repair)
     ├── IMM-09 (CM) ──→ IMM-15 (CM consumes spare parts)
     ├── IMM-11 (Cal) ──→ IMM-09 (Failed calibration → triggers CM)
     │
     ├── IMM-12 (Incident) ──→ IMM-09 (CM) + IMM-16 (CAPA)
     ├── IMM-06 (Training) ──→ IMM-04 (Clinical Release gate: trained operators only)
     │
     └── IMM-16 (Compliance) ─── gates ─→ IMM-08, IMM-09, IMM-04 (BR-16-09)
```

**Read top-to-bottom = lifecycle order.** Circular edges are forbidden — if you find one in your design, move the shared logic into IMM-00 or use an event.

## Pattern A — Event-driven hooks via `hooks.py`

The lowest-coupling pattern. Module A publishes an event by submitting a doc; Module B listens via `doc_events` in `hooks.py`.

```python
# hooks.py
doc_events = {
    "Asset Commissioning": {
        "on_submit": [
            "assetcore.services.imm08.create_pm_schedule_for_asset",
            "assetcore.services.imm11.create_calibration_schedule_if_needed",
            "assetcore.services.imm16.register_compliance_baseline",
        ]
    },
    "IMM PM Work Order": {
        "before_submit": "assetcore.services.imm15.reserve_spare_allocation",
        "on_cancel":     "assetcore.services.imm15.release_spare_allocation",
    },
}
```

**Rules:**
- Listener function is module-scoped (no leading underscore)
- Listener must handle `docstatus=2` (cancel/amend) — never assume submit-only
- Listener must be idempotent — Frappe may retry
- Cite the listener in the target module's `docs/imm-<YY>/04_workflow.md`

## Pattern B — Direct service-to-service call (lazy import)

When you need a synchronous return value, call the other service directly — but always lazy-import to avoid circulars.

```python
# services/imm04.py
def commission_asset(asset_name: str, operator_user: str) -> dict:
    # Lazy import — module-level import would risk circular dep
    from assetcore.services.imm06 import validate_user_authorized_for_asset

    if not validate_user_authorized_for_asset(operator_user, asset_name):
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            "Người vận hành chưa được đào tạo cho thiết bị này",
        )
    # ... continue commissioning
```

**Rules:**
- Always lazy-import inside the function body — never at module top
- Pass primary keys (string `name`), never live `Document` objects (they go stale across transactions)
- Callee must define a stable contract — document the function in its module's `docs/imm-<YY>/05_api.md`
- If the call mutates state, both sides must use shared `Status` constants (see Pattern E)

## Pattern C — Compliance gates (IMM-16 crosses everything)

IMM-16 is the only module that can **block** another module's action. It exposes gate functions called by other services before they commit.

```python
# services/imm09.py
def create_repair(asset_ref: str, **kwargs) -> dict:
    from assetcore.services.imm16 import gate_wo_submit
    gate_wo_submit(asset_ref, wo_type="CM")   # raises ServiceError if blocked
    # ... safe to proceed
```

```python
# services/imm16.py
def gate_wo_submit(asset_ref: str, *, wo_type: str) -> None:
    """BR-16-09: Open Critical CAPA blocks all WO creation for the asset."""
    if CAPARepo.exists({
        "asset_ref": asset_ref,
        "severity": "Critical",
        "status": ("in", ("Open", "In Progress")),
    }):
        raise ServiceError(
            ErrorCode.BUSINESS_RULE,
            "Tài sản có CAPA Critical đang mở — không thể tạo WO mới",
        )
```

**Rules:**
- Gate functions never return data — they raise or pass silently
- Gate functions live in IMM-16 (or IMM-05 for doc-expiry gates)
- Caller calls gate **before** any DB write
- Gate must be testable in isolation — write a unit test in `tests/test_imm16.py`

## Pattern D — Asset status propagation

`AC Asset.status` is shared state changed by many modules. Always go through the canonical helper in IMM-00.

```python
# Anywhere in any service
from assetcore.services.imm00 import transition_asset_status
from assetcore.services.shared import AssetStatus

transition_asset_status(
    asset_name,
    AssetStatus.OUT_OF_SERVICE,
    root_record=repair_doc.name,
)
```

`transition_asset_status`:
1. Validates the from→to transition is legal per the asset state machine
2. Updates `AC Asset.status`
3. Writes a SHA-256-chained row to `IMM Audit Trail`
4. Emits `Asset Lifecycle Event` for FE timelines

**Never** call `frappe.db.set_value("AC Asset", name, "status", ...)` directly — it bypasses validation and audit. This is a 🔴 critical violation in the audit checklist.

## Pattern E — Shared enums (single source of truth)

Always import enums from `assetcore.services.shared`. Never duplicate.

| Enum | Path | Purpose |
|---|---|---|
| `Roles` | `services/shared/constants.py:Roles` | All IMM role names (`WORKSHOP_LEAD`, `BIOMED_TECH`, ...) |
| `ErrorCode` | `services/shared/constants.py:ErrorCode` | Service error codes (`VALIDATION`, `BUSINESS_RULE`, `BAD_STATE`, ...) |
| `AssetStatus` | `services/shared/constants.py:AssetStatus` | Canonical asset states (`ACTIVE`, `IN_REPAIR`, `OUT_OF_SERVICE`, `RETIRED`) |
| `ApprovalStatus` | `services/shared/constants.py` | Cross-module approval states |
| `CalibrationStatus`, `CalibrationResult` | `services/shared/constants.py` | IMM-11 specific but shared with IMM-09 trigger logic |

**Module-local status (e.g., `RepairStatus`, `PMStatus`) stays inside its own service file** — modules must NOT import another module's `Status` class. If two modules need the same status, promote it to `services/shared/constants.py`.

## Cross-module testing

Integration tests live in `tests/test_integration_<scenario>.py` (or in the primary module's test file with a clear naming prefix `test_integration_*`).

```python
# tests/test_integration_imm04_to_imm08.py
def test_commissioning_creates_pm_schedule(self):
    asset = make_test_asset(class_="Medium")
    commissioning = make_commissioning(asset_ref=asset.name)
    commissioning.submit()

    # IMM-08 should have auto-created a PM schedule
    schedules = PMScheduleRepo.list({"asset_ref": asset.name})
    self.assertEqual(len(schedules["data"]), 1)
```

**Rules:**
- Use real DB writes (transactional rollback in `tearDown`); don't mock the integration boundary — that's the whole point
- Mock only external systems (FHIR, email, SMS)
- One test per integration edge in the dependency graph
- Run with `bench --site <site> run-tests --module assetcore.tests.test_integration_immXX_to_immYY`

## Common integration bugs

| Bug | Symptom | Fix |
|---|---|---|
| Circular import at module load | `ImportError: cannot import name X` on `bench start` | Lazy-import inside function body |
| Hook fires on cancel/amend | Phantom records, duplicate audit rows | Check `doc.docstatus == 1` and `not doc.flags.in_cancel` in listener |
| Status string drift | "Active" vs "ACTIVE" comparison fails silently | Use `AssetStatus.ACTIVE` constant on both sides |
| CAPA deadlock | New WO needed to close CAPA, but CAPA blocks WO | Add `wo_type="CAPA_REMEDIATION"` exception in `gate_wo_submit` |
| Stale Document object | Field changes don't persist | Pass primary keys, reload with `frappe.get_doc(...)` in callee |
| Listener swallows error | Submit succeeds but downstream effect missing | Never `except: pass` in listener — at minimum `frappe.log_error(...)` |
| Race on auto-creation | Two PM schedules created for same asset | Use `BaseRepository.exists(...)` guard before create |

## When NOT to integrate

Some pairs **should** stay decoupled. Resist the urge to wire them.

- **Reporting (IMM-17) reads denormalized snapshots** — never call live service functions from a report query. Use scheduled materialized views.
- **FHIR adapter is one-way** — outbound only; never let an FHIR import call into IMM-09 directly. Land it in a staging table, run a service job to ingest.
- **If a cross-module call would create a cycle** — use an event (Pattern A) instead of a direct call.

## Hooks.py audit checklist

Whenever you touch `hooks.py`:

- [ ] Every `doc_events` entry points to an existing function in the target service
- [ ] Every listener handles `docstatus` correctly (submit vs. cancel)
- [ ] Every `scheduler_events` function is module-scoped (no leading underscore)
- [ ] Every listener is documented in the target module's `docs/imm-<YY>/04_workflow.md`
- [ ] Listener is idempotent (or has its own dedup guard)
- [ ] Fixture exports section still includes any new workflow / role / custom field

Run `grep -n "assetcore.services" assetcore/hooks.py` and click through every reference.

## Don'ts

- ❌ Don't import another module's service at file top-level — always lazy
- ❌ Don't pass live `Document` objects between services — pass primary keys
- ❌ Don't fire audit log in both service AND controller hook for the same event — pick one (service is preferred)
- ❌ Don't duplicate a `Status` class across modules — promote to `services/shared/constants.py`
- ❌ Don't bypass `transition_asset_status` with `frappe.db.set_value` on `AC Asset.status`
- ❌ Don't add a circular edge to the dependency graph — re-architect via event or shared module

## References

- `assetcore/hooks.py` — central wiring point (doc_events, scheduler_events, fixtures)
- `assetcore/services/imm00.py` — `transition_asset_status`, lifecycle helpers, shared transitions
- `assetcore/services/shared/constants.py` — canonical enums (`Roles`, `ErrorCode`, `AssetStatus`, ...)
- `assetcore/services/shared/__init__.py` — re-exports — always import from here
- `assetcore/utils/lifecycle.py` — `log_audit_event` (SHA-256 chain)
- `../CONVENTIONS.md` §2 (Architecture Layers) and §3 (Shared Constants)
- `assetcore-be-module` — single-module BE structure
- `assetcore-module-audit` — verifies integration correctness as part of Pillar 4
