"""IMM-08 Preventive Maintenance — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.imm08.test_imm08
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import frappe
from frappe.utils import add_days, getdate, nowdate

from assetcore.services.imm08 import (
    create_adhoc_work_order,
    create_schedule,
    create_template,
    set_schedule_status,
)
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.services.imm08 import PMScheduleStatus
from assetcore.tests._helpers._asset_cleanup import purge_asset
from frappe.tests.utils import FrappeTestCase


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _ensure_cat(name: str = "_TestCatIMM08") -> str:
    existing = frappe.db.get_value("AC Asset Category", {"category_name": name}, "name")
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(
        ignore_permissions=True
    )
    return doc.name


def tearDownModule():  # noqa: N802
    """Safety net: purge the shared test categories/assets if a class teardown
    gap left them (recurring '_TestCatIMM08' leak)."""
    from assetcore.tests._helpers._asset_cleanup import (
        purge_assets_by_name_prefix,
        purge_category_by_name,
    )
    frappe.set_user("Administrator")
    purge_assets_by_name_prefix("_Test Asset IMM08")
    purge_category_by_name("_TestCatIMM08", "_TestCatIMM08Gate", "_TestCatIMM08Photo")
    frappe.db.commit()


def _make_asset(suffix: str = "") -> object:
    import time
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    tag = suffix.lstrip("-") or "001"
    sn = f"SN-08-{tag}-{int(time.time()) % 100000}"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM08{suffix}",
            "asset_category": _ensure_cat(),
            "manufacturer_sn": sn,
            "lifecycle_status": "Active",
            "is_pm_required": 1,
            "pm_interval_days": 90,
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _make_template(cat: str, pm_type: str = "Quarterly") -> dict:
    # PM Checklist Template autoname là deterministic (PMCT-{cat}-{pm_type}) và
    # dùng chung 1 category cho cả module → reuse nếu đã tồn tại (kể cả orphan
    # leak từ run trước có asset-number bị recycle) để tránh DuplicateEntryError.
    det = f"PMCT-{cat}-{pm_type}"
    if frappe.db.exists("PM Checklist Template", det):
        return {"name": det}
    return create_template({
        "template_name": f"_Test Template {pm_type}",
        "asset_category": cat,
        "pm_type": pm_type,
        "checklist_items": [
            {"description": "_Test check item 1", "measurement_type": "Pass/Fail", "is_critical": 1},
            {"description": "_Test check item 2", "measurement_type": "Pass/Fail"},
        ],
    })


def _make_schedule(asset_ref: str, template_name: str) -> dict:
    # PM Schedule autoname deterministic (PMS-{asset}-{pm_type}). AC Asset series
    # có thể recycle số sau khi xoá → schedule cũ còn sót (orphan leak) gây
    # DuplicateEntryError. Purge schedule+WO cũ theo tên deterministic trước khi tạo.
    det = f"PMS-{asset_ref}-Quarterly"
    if frappe.db.exists("PM Schedule", det):
        for wo in frappe.get_all(
            "PM Work Order", filters={"pm_schedule": det}, pluck="name"
        ):
            frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", det, force=True, ignore_permissions=True)
    return create_schedule({
        "asset_ref": asset_ref,
        "pm_type": "Quarterly",
        "pm_interval_days": 90,
        "checklist_template": template_name,
        "status": "Active",
    })


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestPMChecklistTemplate(FrappeTestCase):
    """BR-08-T1: Template creation + validation."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()

    @classmethod
    def tearDownClass(cls):
        for t in frappe.get_all(
            "PM Checklist Template",
            filters={"template_name": ("like", "_Test Template%")},
            fields=["name"],
        ):
            frappe.delete_doc("PM Checklist Template", t.name, force=True, ignore_permissions=True)
        cat_name = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM08"}, "name")
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_missing_required_fields_raises_validation(self):
        with self.assertRaises(ServiceError) as cm:
            create_template({"pm_type": "Preventive"})
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)

    def test_create_template_succeeds(self):
        result = _make_template(self.cat)
        self.assertIn("name", result)
        self.assertEqual(result["items_count"], 2)

    def test_template_naming_series(self):
        result = _make_template(self.cat, pm_type="Annual")
        doc = frappe.get_doc("PM Checklist Template", result["name"])
        self.assertTrue(frappe.db.exists("PM Checklist Template", result["name"]))
        self.assertEqual(doc.pm_type, "Annual")


class TestPMSchedule(FrappeTestCase):
    """BR-08-S1: Schedule creation + status transitions."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-sched")
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        cls.sched = _make_schedule(cls.asset.name, cls.template_name)

    @classmethod
    def tearDownClass(cls):
        for s in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Schedule", s.name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")
        set_schedule_status(self.sched["name"], "Active")

    def test_missing_required_raises_validation(self):
        with self.assertRaises(ServiceError) as cm:
            create_schedule({"asset_ref": self.asset.name})
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)

    def test_create_schedule_succeeds(self):
        self.assertIn("name", self.sched)
        self.assertEqual(self.sched["status"], "Active")

    def test_set_schedule_paused(self):
        result = set_schedule_status(self.sched["name"], "Paused")
        self.assertEqual(result["status"], "Paused")

    def test_invalid_status_raises_validation(self):
        with self.assertRaises(ServiceError) as cm:
            set_schedule_status(self.sched["name"], "InvalidStatus")
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)


class TestPMWorkOrder(FrappeTestCase):
    """BR-08-W1: Adhoc PM WO creation."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-wo")
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_missing_required_raises_validation(self):
        with self.assertRaises(ServiceError) as cm:
            create_adhoc_work_order({"asset_ref": self.asset.name})
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)

    def test_nonexistent_schedule_raises_not_found(self):
        with self.assertRaises(ServiceError) as cm:
            create_adhoc_work_order({
                "asset_ref": self.asset.name,
                "pm_schedule": "DOES-NOT-EXIST",
                "due_date": add_days(nowdate(), 7),
            })
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)
        # Notification contract — service raise qua nthrow → có message_code.
        self.assertEqual(cm.exception.message_code, "IMM08-SCHEDULE-NOT-FOUND")

    def test_asset_mismatch_raises_validation(self):
        other_asset = _make_asset("-other")
        try:
            with self.assertRaises(ServiceError) as cm:
                create_adhoc_work_order({
                    "asset_ref": other_asset.name,
                    "pm_schedule": self.schedule_name,
                    "due_date": add_days(nowdate(), 7),
                })
            self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)
        finally:
            purge_asset(other_asset.name)

    def test_create_pm_work_order_succeeds(self):
        result = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        self.assertIn("name", result)
        self.assertEqual(result["status"], "Open")
        self.assertGreaterEqual(result["checklist_items_count"], 0)

    def test_paused_schedule_blocks_wo_creation(self):
        set_schedule_status(self.schedule_name, "Paused")
        try:
            with self.assertRaises(ServiceError) as cm:
                create_adhoc_work_order({
                    "asset_ref": self.asset.name,
                    "pm_schedule": self.schedule_name,
                    "due_date": add_days(nowdate(), 7),
                })
            self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE)
        finally:
            set_schedule_status(self.schedule_name, "Active")

    def test_br0806_high_risk_wo_no_attribute_error(self):
        """BR-08-06 regression: PM WO cho thiết bị Critical KHÔNG được raise
        AttributeError trên `doc.attachments` (Attach Multiple chưa init).

        Phải raise ValidationError có ý nghĩa (yêu cầu photo evidence) — KHÔNG
        phải AttributeError. Bug gốc: `if ... and not doc.attachments` crash khi
        attachments chưa từng set; fix dùng `doc.get("attachments")`.
        """
        from frappe.exceptions import ValidationError

        crit_asset = _make_asset("-crit")
        frappe.db.set_value(
            "AC Asset", crit_asset.name, "risk_classification", "Critical"
        )
        # PM Schedule có naming deterministic PMS-{asset}-Quarterly. Nếu một
        # lần chạy trước để sót (asset name có thể tái dùng) → xoá trước khi tạo.
        det_name = f"PMS-{crit_asset.name}-Quarterly"
        if frappe.db.exists("PM Schedule", det_name):
            for wo in frappe.get_all(
                "PM Work Order", filters={"pm_schedule": det_name}, pluck="name"
            ):
                frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
            frappe.delete_doc("PM Schedule", det_name, force=True, ignore_permissions=True)
        crit_sched = _make_schedule(crit_asset.name, self.template_name)
        try:
            # Không gắn attachments → BR-08-06 phải chặn bằng ValidationError,
            # KHÔNG phải AttributeError. assertRaises(ValidationError) sẽ FAIL
            # nếu raise AttributeError (loại exception khác) → bắt đúng regression.
            try:
                create_adhoc_work_order({
                    "asset_ref": crit_asset.name,
                    "pm_schedule": crit_sched["name"],
                    "due_date": add_days(nowdate(), 7),
                })
            except AttributeError as e:  # noqa: F841
                self.fail(f"BR-08-06 regression: raised AttributeError {e}")
            except (ValidationError, ServiceError):
                pass  # đúng kỳ vọng — gate photo evidence hoạt động
        finally:
            for wo in frappe.get_all(
                "PM Work Order", filters={"asset_ref": crit_asset.name}, pluck="name"
            ):
                frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
            frappe.delete_doc("PM Schedule", crit_sched["name"], force=True, ignore_permissions=True)
            purge_asset(crit_asset.name)

    # ── slide 22 / write-path supervisor persistence (TDD) ──────────────────
    def test_adhoc_persists_supervisor_to_db(self):
        """TDD-RED-1: create_adhoc_work_order(supervisor='Administrator') PHẢI
        persist xuống DB. Đọc LẠI từ DB (frappe.get_doc), không in-memory.
        FAIL trước fix (write-path drop supervisor) → PROVE bug."""
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "supervisor": "Administrator",
        })
        frappe.db.commit()
        try:
            reloaded = frappe.get_doc("PM Work Order", res["name"])
            self.assertEqual(reloaded.supervisor, "Administrator")
        finally:
            frappe.delete_doc("PM Work Order", res["name"], force=True, ignore_permissions=True)

    def test_adhoc_persists_assigned_to_and_supervisor_with_audit_stamp(self):
        """TDD-2: cả assigned_to + supervisor persist; assigned_by audit-stamp
        == session.user (semantics field khác KHÔNG đổi)."""
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
            "supervisor": "Administrator",
        })
        frappe.db.commit()
        try:
            reloaded = frappe.get_doc("PM Work Order", res["name"])
            self.assertEqual(reloaded.assigned_to, "Administrator")
            self.assertEqual(reloaded.supervisor, "Administrator")
            self.assertEqual(reloaded.assigned_by, frappe.session.user)
        finally:
            frappe.delete_doc("PM Work Order", res["name"], force=True, ignore_permissions=True)

    def test_adhoc_without_supervisor_backward_compat(self):
        """TDD-3: payload cũ KHÔNG có supervisor → tạo WO bình thường, supervisor
        falsy, KHÔNG raise. assigned_by KHÔNG bị stamp khi không có assigned_to."""
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
        })
        frappe.db.commit()
        try:
            reloaded = frappe.get_doc("PM Work Order", res["name"])
            self.assertFalse(reloaded.supervisor)
            self.assertFalse(reloaded.assigned_by)
        finally:
            frappe.delete_doc("PM Work Order", res["name"], force=True, ignore_permissions=True)

    def test_adhoc_supervisor_round_trips_through_read_path(self):
        """TDD-4 (end-to-end write→read): sau create với supervisor →
        get_work_order(name)['supervisor']=='Administrator' VÀ supervisor_name != ''.
        Đóng vòng write→read mà test_list_and_detail_expose_supervisor BỎ SÓT
        (vì nó insert trực tiếp, bypass write-path)."""
        from assetcore.services.imm08 import get_work_order
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "supervisor": "Administrator",
        })
        frappe.db.commit()
        try:
            detail = get_work_order(res["name"])
            self.assertEqual(detail["supervisor"], "Administrator")
            self.assertNotEqual(detail["supervisor_name"], "")
        finally:
            frappe.delete_doc("PM Work Order", res["name"], force=True, ignore_permissions=True)


class TestPMAllowedTransitions(FrappeTestCase):
    """Server-driven CTA (mirror imm12 R3): get_work_order emit `allowed_transitions[]`.

    ASYMMETRY ĐÓNG — màn PM-detail mobile render nút workflow theo server, KHÔNG hardcode
    status→button (anti-pattern dead-gate). Assert:
      (1) map _PM_VALID_TRANSITIONS GROUNDED imm_08_pm_workflow.json (codomain ⊆ PMStatus enum);
      (2) get_work_order(name) CHỨA key `allowed_transitions` == _PM_VALID_TRANSITIONS[status]
          cho ≥3 status (Open / In Progress / Completed-terminal-rỗng) — set_values flip status
          để exercise các nhánh (KHÔNG drive full workflow-engine).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-trans")
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_map_codomain_subset_pmstatus_grounded(self):
        """(1) Mọi key + value-state ∈ PMStatus enum + khớp workflow JSON codomain (chống typo/drift)."""
        import json
        from pathlib import Path
        from assetcore.services.imm08 import PMStatus, _PM_VALID_TRANSITIONS

        enum = {
            getattr(PMStatus, a) for a in dir(PMStatus)
            if not a.startswith("_") and isinstance(getattr(PMStatus, a), str)
        }
        for state, nexts in _PM_VALID_TRANSITIONS.items():
            self.assertIn(state, enum, f"key-state '{state}' KHÔNG ∈ PMStatus enum.")
            for nx in nexts:
                self.assertIn(nx, enum, f"next '{nx}' (từ '{state}') KHÔNG ∈ PMStatus enum.")
        # SSoT-divergence: map == codomain imm_08_pm_workflow.json (7 state / 13 transition).
        wf_path = (
            Path(frappe.get_app_path("assetcore"))
            / "assetcore" / "workflow" / "imm_08_pm_workflow.json"
        )
        data = json.loads(wf_path.read_text(encoding="utf-8"))
        codomain = {s["state"]: set() for s in data["states"]}
        for t in data["transitions"]:
            codomain.setdefault(t["state"], set()).add(t["next_state"])
        self.assertEqual(
            set(_PM_VALID_TRANSITIONS.keys()), set(codomain.keys()),
            "Key-set map BE PHẢI == states[] workflow JSON.")
        for state, wf_nexts in codomain.items():
            self.assertEqual(
                set(_PM_VALID_TRANSITIONS[state]), wf_nexts,
                f"DRIFT '{state}': map {sorted(_PM_VALID_TRANSITIONS[state])} ≠ workflow {sorted(wf_nexts)}.")

    def test_get_work_order_emits_allowed_transitions_per_status(self):
        """(2) get_work_order CHỨA allowed_transitions == map[status] cho ≥3 status."""
        from assetcore.services.imm08 import (
            PMStatus, _PM_VALID_TRANSITIONS, get_work_order,
        )
        from assetcore.repositories.pm_repo import PMWorkOrderRepo

        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        name = res["name"]
        try:
            from assetcore.services.imm08 import RESCHEDULE_CTA_STATES
            # Open (as created) → key present + workflow-mirror ∪ reschedule-CTA-overlay
            # (CR-45b ADR-IMM08-RESCHED-CTA): map[Open] + Pending–Device Busy (CTA «Dời lịch»).
            detail = get_work_order(name)
            self.assertIn(
                "allowed_transitions", detail,
                "get_work_order PHẢI emit key 'allowed_transitions' (server-driven CTA).")
            self.assertEqual(
                detail["allowed_transitions"],
                _PM_VALID_TRANSITIONS[PMStatus.OPEN] + [PMStatus.PENDING_BUSY],
                "Open → map ∪ overlay [In Progress, Overdue, Cancelled, Pending–Device Busy] (CR-45b).")
            self.assertIn(PMStatus.OPEN, RESCHEDULE_CTA_STATES,
                          "Open ∈ RESCHEDULE_CTA_STATES (overlay áp CTA «Dời lịch»).")

            # In Progress → 4 next (∉ RESCHEDULE_CTA_STATES ⇒ overlay no-op; Pending SẴN từ workflow).
            PMWorkOrderRepo.set_values(name, {"status": PMStatus.IN_PROGRESS})
            frappe.db.commit()
            self.assertEqual(
                get_work_order(name)["allowed_transitions"],
                _PM_VALID_TRANSITIONS[PMStatus.IN_PROGRESS],
                "In Progress → [Completed, Halted–Major Failure, Pending–Device Busy, Cancelled].")

            # Completed (terminal) → [] rỗng.
            PMWorkOrderRepo.set_values(name, {"status": PMStatus.COMPLETED})
            frappe.db.commit()
            self.assertEqual(
                get_work_order(name)["allowed_transitions"], [],
                "Completed (terminal) → [] rỗng (KHÔNG transition ra).")
        finally:
            frappe.delete_doc("PM Work Order", name, force=True, ignore_permissions=True)


class TestPMBackfillAndSupervisor(FrappeTestCase):
    """Slide 08c — backfill PM Schedule cho asset có next_pm_date; slide 22 — supervisor."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-bf")
        # checklist template khớp category để create_pm_schedule_from_asset thành công
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]

    @classmethod
    def tearDownClass(cls):
        for sc in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Schedule", sc.name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")
        for sc in frappe.get_all(
            "PM Schedule", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Schedule", sc.name, force=True, ignore_permissions=True)

    def test_backfill_creates_schedule_for_due_asset(self):
        from assetcore.services.imm08 import backfill_pm_schedules_for_due_assets

        frappe.db.set_value(
            "AC Asset", self.asset.name, "next_pm_date", add_days(nowdate(), -1)
        )
        frappe.db.commit()

        result = backfill_pm_schedules_for_due_assets()
        self.assertGreaterEqual(result["created"], 1)
        self.assertTrue(
            frappe.db.exists(
                "PM Schedule", {"asset_ref": self.asset.name, "status": "Active"}
            )
        )

    def test_backfill_skips_asset_with_active_schedule(self):
        from assetcore.services.imm08 import (
            backfill_pm_schedules_for_due_assets,
            create_pm_schedule_from_asset,
        )

        frappe.db.set_value(
            "AC Asset", self.asset.name, "next_pm_date", add_days(nowdate(), -1)
        )
        frappe.db.commit()
        asset_doc = frappe.get_doc("AC Asset", self.asset.name)
        create_pm_schedule_from_asset(asset_doc)
        frappe.db.commit()

        before = frappe.db.count("PM Schedule", {"asset_ref": self.asset.name})
        backfill_pm_schedules_for_due_assets()
        after = frappe.db.count("PM Schedule", {"asset_ref": self.asset.name})
        self.assertEqual(before, after)

    def test_list_and_detail_expose_supervisor(self):
        from assetcore.services.imm08 import get_work_order, list_work_orders

        wo = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": self.asset.name,
            "pm_schedule": None,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "Open",
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
            "supervisor": "Administrator",
        })
        # pm_schedule reqd — tạo lịch tạm
        from assetcore.services.imm08 import create_pm_schedule_from_asset
        frappe.db.set_value(
            "AC Asset", self.asset.name, "next_pm_date", add_days(nowdate(), -1)
        )
        sched_name = create_pm_schedule_from_asset(
            frappe.get_doc("AC Asset", self.asset.name)
        )
        wo.pm_schedule = sched_name
        wo.insert(ignore_permissions=True)
        frappe.db.commit()
        try:
            detail = get_work_order(wo.name)
            self.assertEqual(detail["supervisor"], "Administrator")
            self.assertIn("supervisor_name", detail)
            self.assertIn("completion_date", detail)
            self.assertIn("assigned_to", detail)

            listed = list_work_orders({"asset_ref": self.asset.name})
            match = next(r for r in listed["data"] if r["name"] == wo.name)
            self.assertEqual(match["supervisor"], "Administrator")
            self.assertIn("supervisor_name", match)
            self.assertIn("completion_date", match)
        finally:
            frappe.delete_doc(
                "PM Work Order", wo.name, force=True, ignore_permissions=True
            )


class TestPMListMineScope(FrappeTestCase):
    """C-LISTREAD-MINE-PM (ADR-MOBILE-016) — api/imm08.list_pm_work_orders mine=1 scope
    assigned_to == session.user cho tab 'Phiếu PM của tôi' (MyWorkOrdersView, MVP-5a).

    Đối-xứng IncidentMine (báo hỏng của tôi). Inject @api-layer SAU apply_vendor_scope.
    INVARIANT: count==rows giữ vì count_with_or + get_all dùng CÙNG filters dict (đã có
    assigned_to). FENCE: mine=0/absent ⇒ filters byte-identical baseline (WO user khác VẪN hiện).
    """

    OTHER_USER = "_test_imm08_mine_other@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Mine")
        cls.asset = _make_asset("-mine")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        cls.schedule_name = _make_schedule(cls.asset.name, cls.template_name)["name"]
        # assigned_to là Link User → user "khác" PHẢI tồn tại thật để insert WO hợp lệ.
        if not frappe.db.exists("User", cls.OTHER_USER):
            frappe.get_doc({
                "doctype": "User",
                "email": cls.OTHER_USER,
                "first_name": "IMM08 Mine Other",
                "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        for sc in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Schedule", sc.name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        if frappe.db.exists("User", cls.OTHER_USER):
            frappe.delete_doc("User", cls.OTHER_USER, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Mỗi test tự dựng WO — purge giữa các test để count==rows deterministic.
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_wo(self, assigned_to: str, status: str | None = None) -> str:
        wo = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "Open",
            "due_date": add_days(nowdate(), 7),
            "assigned_to": assigned_to,
        })
        wo.insert(ignore_permissions=True)
        if status and status != "Open":
            # set sau insert (bypass controller) — chỉ cần giá trị cột cho filter test.
            frappe.db.set_value("PM Work Order", wo.name, "status", status)
        frappe.db.commit()
        return wo.name

    def _list(self, *, mine: int | None = None, extra: dict | None = None) -> dict:
        from assetcore.api.imm08 import list_pm_work_orders
        f = {"asset_ref": self.asset.name}
        if extra:
            f.update(extra)
        kwargs = {"filters": json.dumps(f), "page": 1, "page_size": 100}
        if mine is not None:
            kwargs["mine"] = mine
        env = list_pm_work_orders(**kwargs)
        self.assertTrue(env.get("success"), f"envelope KHÔNG success: {env}")
        return env["data"]

    def test_list_pm_mine_scopes_assigned_to_session_user(self):
        """mine=1 → CHỈ PM WO assigned_to == frappe.session.user (Administrator)."""
        mine_wo = self._make_wo("Administrator")
        other_wo = self._make_wo(self.OTHER_USER)
        data = self._list(mine=1)
        names = {r["name"] for r in data["data"]}
        self.assertIn(mine_wo, names, "WO của session.user PHẢI hiện khi mine=1.")
        self.assertNotIn(other_wo, names, "WO của user khác PHẢI bị loại khi mine=1.")
        for r in data["data"]:
            self.assertEqual(
                r["assigned_to"], "Administrator",
                "mine=1 ⇒ MỌI row assigned_to == session.user.",
            )

    def test_list_pm_mine_zero_fence_other_users_visible(self):
        """FENCE blast-radius: mine=0/absent ⇒ WO assigned user khác VẪN hiện
        (filters byte-identical baseline — backward-compat tuyệt đối)."""
        mine_wo = self._make_wo("Administrator")
        other_wo = self._make_wo(self.OTHER_USER)
        # mine=0 explicit.
        names0 = {r["name"] for r in self._list(mine=0)["data"]}
        self.assertIn(mine_wo, names0)
        self.assertIn(other_wo, names0, "mine=0 ⇒ WO user khác VẪN hiện (fence).")
        # mine absent — phải GIỐNG hệt mine=0 (default 0).
        names_absent = {r["name"] for r in self._list()["data"]}
        self.assertEqual(
            names0, names_absent,
            "mine absent PHẢI == mine=0 (default 0 — web-FE PMWorkOrderListView KHÔNG regress).",
        )

    def test_list_pm_mine_ands_with_status_filter(self):
        """mine=1 + filters status ⇒ AND (chỉ WO của tôi + đúng status)."""
        my_open = self._make_wo("Administrator", status="Open")
        my_overdue = self._make_wo("Administrator", status="Overdue")
        other_open = self._make_wo(self.OTHER_USER, status="Open")
        data = self._list(mine=1, extra={"status": "Open"})
        names = {r["name"] for r in data["data"]}
        self.assertEqual(
            names, {my_open},
            "mine=1 AND status=Open ⇒ CHỈ my_open (loại my_overdue=status sai, other_open=user khác).",
        )
        self.assertNotIn(my_overdue, names)
        self.assertNotIn(other_open, names)

    def test_list_pm_mine_count_equals_rows(self):
        """INVARIANT count==rows: mine=1 ⇒ pagination.total == len(data.data)
        (count_with_or + get_all CÙNG filters dict đã có assigned_to)."""
        for _ in range(3):
            self._make_wo("Administrator")
        for _ in range(2):
            self._make_wo(self.OTHER_USER)
        data = self._list(mine=1)
        self.assertEqual(
            data["pagination"]["total"], len(data["data"]),
            "mine=1 ⇒ pagination.total PHẢI == len(rows) (count-vs-rows drift guard).",
        )
        self.assertEqual(data["pagination"]["total"], 3, "CHỈ 3 WO của session.user.")


# ─── CR-62d: get_pm_calendar mine=1 scope server-resolve (Lịch PM tháng) ──────

class TestPMCalendarMineScope(FrappeTestCase):
    """CR-62d (mobile Spec 62 "Lịch PM tháng") — api/imm08.get_pm_calendar mine=1 scope
    events[] + summary về assigned_to == session.user. Email do SERVER giải (client KHÔNG
    truyền email) → toggle "Chỉ việc của tôi" hết phải tự-suy email KTV client-side.

    Mirror imm09.py:37 / imm11.py:84 (mine THẮNG technician). FENCE: mine=0/absent ⇒
    response BYTE-IDENTICAL baseline (2 WO đều hiện) — param additive default 0, 0 regression
    web-FE PMDashboard/Calendar. CR-62b: events[].is_late kiểu int 0/1 (KHÔNG bool).
    """

    OTHER_USER = "_test_imm08_cal_other@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Cal")
        cls.asset = _make_asset("-cal")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        cls.schedule_name = _make_schedule(cls.asset.name, cls.template_name)["name"]
        if not frappe.db.exists("User", cls.OTHER_USER):
            frappe.get_doc({
                "doctype": "User",
                "email": cls.OTHER_USER,
                "first_name": "IMM08 Calendar Other",
                "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
        # Ngày due CỐ ĐỊNH trong tháng đang xét (15) → luôn thuộc [start,end] window,
        # KHÔNG spill sang tháng kế (add_days near month-end race).
        today = getdate(nowdate())
        cls.year = today.year
        cls.month = today.month
        cls.due_date = f"{cls.year:04d}-{cls.month:02d}-15"
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        for sc in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Schedule", sc.name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        if frappe.db.exists("User", cls.OTHER_USER):
            frappe.delete_doc("User", cls.OTHER_USER, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_wo(self, assigned_to: str) -> str:
        wo = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "Open",
            "due_date": self.due_date,
            "assigned_to": assigned_to,
        })
        wo.insert(ignore_permissions=True)
        frappe.db.commit()
        return wo.name

    def _calendar(self, *, mine=None, technician=None) -> dict:
        from assetcore.api.imm08 import get_pm_calendar
        kwargs = {
            "year": self.year, "month": self.month,
            "asset_ref": self.asset.name,
        }
        if technician is not None:
            kwargs["technician"] = technician
        if mine is not None:
            kwargs["mine"] = mine
        env = get_pm_calendar(**kwargs)
        self.assertTrue(env.get("success"), f"envelope KHÔNG success: {env}")
        return env["data"]

    def test_get_pm_calendar_mine_scopes_to_session_user(self):
        """mine=1 → events CHỈ chứa WO assigned_to == session.user; summary tính đúng
        trên tập đã lọc (total==1)."""
        mine_wo = self._make_wo("Administrator")
        other_wo = self._make_wo(self.OTHER_USER)
        data = self._calendar(mine=1)
        names = {e["name"] for e in data["events"]}
        self.assertIn(mine_wo, names, "WO của session.user PHẢI hiện khi mine=1.")
        self.assertNotIn(other_wo, names, "WO của user khác PHẢI bị loại khi mine=1.")
        for e in data["events"]:
            self.assertEqual(
                e["assigned_to"], "Administrator",
                "mine=1 ⇒ MỌI event assigned_to == session.user.",
            )
        self.assertEqual(data["summary"]["total"], 1,
                         "summary.total PHẢI tính trên tập ĐÃ LỌC (chỉ 1 WO của session.user).")

    def test_get_pm_calendar_mine_zero_is_baseline(self):
        """mine=0 và mine absent ⇒ 2 response identical VÀ chứa CẢ 2 WO (additive,
        0 regression web-FE)."""
        mine_wo = self._make_wo("Administrator")
        other_wo = self._make_wo(self.OTHER_USER)
        data0 = self._calendar(mine=0)
        data_absent = self._calendar()
        self.assertEqual(data0, data_absent,
                         "mine=0 PHẢI == mine absent (default 0 — byte-identical baseline).")
        names0 = {e["name"] for e in data0["events"]}
        self.assertIn(mine_wo, names0, "baseline chứa WO session.user.")
        self.assertIn(other_wo, names0, "baseline chứa WO user khác (fence — KHÔNG lọc).")
        self.assertEqual(data0["summary"]["total"], 2, "baseline summary.total == 2 (cả 2 WO).")

    def test_get_pm_calendar_mine_overrides_technician(self):
        """mine=1 + technician=<email khác> → vẫn scope về session.user (technician
        truyền bị override — mine THẮNG, khớp imm09.py:37 / imm11.py:84)."""
        mine_wo = self._make_wo("Administrator")
        other_wo = self._make_wo(self.OTHER_USER)
        data = self._calendar(mine=1, technician=self.OTHER_USER)
        names = {e["name"] for e in data["events"]}
        self.assertEqual(
            names, {mine_wo},
            "mine=1 THẮNG technician=<other> ⇒ CHỈ WO session.user (technician bị override).",
        )
        self.assertNotIn(other_wo, names)
        self.assertEqual(data["summary"]["total"], 1)

    def test_get_pm_calendar_is_late_is_int(self):
        """CR-62b: events[].is_late kiểu int 0/1 (assertIsInstance int, KHÔNG bool —
        Check field né strict-deser mobile Dart/Kotlin)."""
        self._make_wo("Administrator")
        data = self._calendar(mine=1)
        self.assertTrue(data["events"], "PHẢI có ≥1 event để soi is_late.")
        for e in data["events"]:
            self.assertIn("is_late", e, "event PHẢI khai is_late.")
            self.assertIsInstance(e["is_late"], int, "is_late PHẢI là int.")
            self.assertNotIsInstance(
                e["is_late"], bool,
                "is_late PHẢI int THUẦN (0/1), KHÔNG bool (bool ⊂ int nhưng codegen crash).",
            )
            self.assertIn(e["is_late"], (0, 1), "is_late ∈ {0,1}.")


# ─── CR-18: free-text search server-side cho list PM Work Order ────────────────

class TestPMListSearch(FrappeTestCase):
    """CR-18 — api/imm08.list_pm_work_orders(search=...) OR-LIKE trên (name = mã
    phiếu / asset_ref = mã thiết bị / asset_name = tên thiết bị) qua pop_search +
    count_with_or.

    Acceptance: search khớp TOÀN tập mọi trang (KHÔNG phụ thuộc rows client tải);
    count==rows GIỮ; AND với mine + filters; wildcard %/_ escape-literal; search
    rỗng/absent ⇒ baseline byte-identical. Đối xứng test_imm09 TestRepairListSearch.
    """

    OTHER_USER = "_test_imm08_search_other@example.com"

    @classmethod
    def setUpClass(cls):
        import time
        frappe.set_user("Administrator")
        cls.token = f"ZZPMSRCH{int(time.time()) % 100000}"
        cls.cat = _ensure_cat("_TestCatIMM08Search")
        # Asset A: asset_name chứa token DUY NHẤT → search token khớp qua link_search.
        cls.asset_a = _make_asset(f"-{cls.token}A")
        cls.asset_a.asset_category = cls.cat
        cls.asset_a.save(ignore_permissions=True)
        # Asset B (decoy): asset_name KHÔNG chứa token → search token KHÔNG khớp.
        cls.asset_b = _make_asset("-DECOYB")
        cls.asset_b.asset_category = cls.cat
        cls.asset_b.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        cls.sched_a = _make_schedule(cls.asset_a.name, cls.template_name)["name"]
        cls.sched_b = _make_schedule(cls.asset_b.name, cls.template_name)["name"]
        if not frappe.db.exists("User", cls.OTHER_USER):
            frappe.get_doc({
                "doctype": "User", "email": cls.OTHER_USER,
                "first_name": "IMM08 Search Other", "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for a in (cls.asset_a, cls.asset_b):
            for wo in frappe.get_all("PM Work Order", filters={"asset_ref": a.name}, pluck="name"):
                frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
            for sc in frappe.get_all("PM Schedule", filters={"asset_ref": a.name}, pluck="name"):
                frappe.delete_doc("PM Schedule", sc, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Checklist Template", cls.template_name, force=True, ignore_permissions=True)
        purge_asset(cls.asset_a.name)
        purge_asset(cls.asset_b.name)
        if frappe.db.exists("User", cls.OTHER_USER):
            frappe.delete_doc("User", cls.OTHER_USER, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        for a in (self.asset_a, self.asset_b):
            for wo in frappe.get_all("PM Work Order", filters={"asset_ref": a.name}, pluck="name"):
                frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_wo(self, asset_ref: str, schedule: str, assigned_to: str = "Administrator") -> str:
        wo = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": asset_ref,
            "pm_schedule": schedule,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "Open",
            "due_date": add_days(nowdate(), 7),
            "assigned_to": assigned_to,
        })
        wo.insert(ignore_permissions=True)
        frappe.db.commit()
        return wo.name

    def _list(self, *, search=None, mine=None, page=1, page_size=100, extra=None) -> dict:
        from assetcore.api.imm08 import list_pm_work_orders
        f = dict(extra or {})
        kwargs = {"filters": json.dumps(f), "page": page, "page_size": page_size}
        if search is not None:
            kwargs["search"] = search
        if mine is not None:
            kwargs["mine"] = mine
        env = list_pm_work_orders(**kwargs)
        self.assertTrue(env.get("success"), f"envelope KHÔNG success: {env}")
        return env["data"]

    def _all_names(self, **kw) -> set:
        return {r["name"] for r in self._list(**kw)["data"]}

    def test_list_pm_search_matches_wo_name(self):
        """2 phiếu khác name, search substring name của 1 phiếu → CHỈ phiếu khớp."""
        wo1 = self._make_wo(self.asset_a.name, self.sched_a)
        wo2 = self._make_wo(self.asset_a.name, self.sched_a)
        self.assertNotEqual(wo1, wo2)
        # tail 5 ký tự của wo1.name — phân biệt wo1 vs wo2 (naming series liên tiếp).
        term = wo1[-5:]
        data = self._list(search=term)
        names = {r["name"] for r in data["data"]}
        self.assertIn(wo1, names, "phiếu có name chứa term PHẢI khớp.")
        self.assertNotIn(wo2, names, "phiếu name KHÁC KHÔNG được lọt.")
        self.assertEqual(data["pagination"]["total"], 1, "count==rows: chỉ 1 khớp.")

    def test_list_pm_search_matches_asset_code_or_name(self):
        """search khớp asset_name (token) → trả phiếu của asset đó kể cả ở 'trang
        sau' (page_size nhỏ) — server phủ TOÀN tập, KHÔNG chỉ rows đã tải."""
        wo_a = self._make_wo(self.asset_a.name, self.sched_a)   # asset_name chứa token
        # decoy: nhiều WO asset_b (KHÔNG chứa token) đẩy wo_a về 'trang sau' nếu unpaged.
        for _ in range(3):
            self._make_wo(self.asset_b.name, self.sched_b)
        # search theo asset_name token, page_size=1 → wo_a vẫn tìm được (server-side).
        found = set()
        page, total_pages = 1, 1
        while page <= total_pages:
            data = self._list(search=self.token, page=page, page_size=1)
            found |= {r["name"] for r in data["data"]}
            total_pages = data["pagination"]["total_pages"]
            page += 1
        self.assertEqual(found, {wo_a}, "search asset_name token → CHỈ phiếu asset A (mọi trang).")
        # search theo asset_code (asset_ref = mã thiết bị) cũng khớp.
        by_code = self._all_names(search=self.asset_a.name)
        self.assertIn(wo_a, by_code, "search asset_code (asset_ref) PHẢI khớp phiếu asset A.")

    def test_list_pm_search_count_equals_rows(self):
        """search + page_size=1 nhiều trang → Σ(rows mọi trang)==pagination.total
        ==số khớp thực (bất biến count==rows)."""
        made = {self._make_wo(self.asset_a.name, self.sched_a) for _ in range(3)}
        # decoy asset_b KHÔNG khớp token.
        self._make_wo(self.asset_b.name, self.sched_b)
        collected, totals = set(), set()
        page, total_pages = 1, 1
        while page <= total_pages:
            data = self._list(search=self.token, page=page, page_size=1)
            collected |= {r["name"] for r in data["data"]}
            totals.add(data["pagination"]["total"])
            total_pages = data["pagination"]["total_pages"]
            page += 1
        self.assertEqual(collected, made, "Σ rows mọi trang == tập khớp thực.")
        self.assertEqual(totals, {3}, "pagination.total ổn định == 3 khớp (count==rows).")

    def test_list_pm_search_and_mine_scope(self):
        """search + mine=1 → CHỈ phiếu assigned_to==session.user VÀ khớp; phiếu
        người khác (khớp search) KHÔNG lọt (không nới quyền)."""
        mine_wo = self._make_wo(self.asset_a.name, self.sched_a, "Administrator")
        other_wo = self._make_wo(self.asset_a.name, self.sched_a, self.OTHER_USER)
        names = self._all_names(search=self.token, mine=1)
        self.assertIn(mine_wo, names, "phiếu của tôi + khớp search PHẢI hiện.")
        self.assertNotIn(other_wo, names, "phiếu người khác (dù khớp search) KHÔNG lọt khi mine=1.")

    def test_list_pm_search_empty_is_baseline(self):
        """search='' → kết quả == list KHÔNG search (byte-identical, no regression)."""
        self._make_wo(self.asset_a.name, self.sched_a)
        self._make_wo(self.asset_b.name, self.sched_b)
        base = self._all_names()
        empty = self._all_names(search="")
        blank = self._all_names(search="   ")
        self.assertEqual(empty, base, "search='' PHẢI == baseline không search.")
        self.assertEqual(blank, base, "search khoảng-trắng PHẢI == baseline (strip rỗng).")

    def test_list_pm_search_wildcard_escaped(self):
        """search chứa '%'/'_' → khớp LITERAL, KHÔNG match toàn bảng (escape)."""
        wo = self._make_wo(self.asset_a.name, self.sched_a)   # name/asset không có %/_
        # Nếu KHÔNG escape: '%' → LIKE '%%%' match-all ⇒ wo lọt. Escape ⇒ literal '%'
        # KHÔNG có trong field ⇒ wo KHÔNG lọt.
        self.assertNotIn(wo, self._all_names(search="%"),
                         "search='%' escaped literal ⇒ KHÔNG match toàn bảng.")
        self.assertNotIn(wo, self._all_names(search="_"),
                         "search='_' escaped literal ⇒ KHÔNG match mọi row 1-ký-tự.")
        # sanity: token thật vẫn khớp (escape KHÔNG phá match hợp lệ).
        self.assertIn(wo, self._all_names(search=self.token),
                      "token hợp lệ vẫn khớp sau khi thêm escape.")


# ─── BE-TC-OVD1..7: filter LIVE `overdue_live` cho list PM Work Order ──────────

class TestListPmOverdueLiveFilter(FrappeTestCase):
    """Chip mobile 'Quá hạn' PM — `list_work_orders({"overdue_live":1})` lọc theo
    predicate LIVE `is_overdue` = (status==Overdue, cron ĐÃ stamp) OR
    is_pm_overdue(status, due_date, today) (due_date<hôm nay ∧ status ∈
    OVERDUE_SOURCE_STATES). CÙNG predicate badge row `_enrich_pm_overdue`.

    GATE: INVARIANT membership filter == badge. Nếu lọc theo cột STORED
    status==Overdue đơn thuần (cron nightly stamp trễ) → WO due_date<today mà
    status vẫn Open MISS filter nhưng badge HIỆN → mismatch phá niềm tin KTV.
    Test chứng minh LIVE ≠ stored status. Mirror imm09 TestListSlaBreachedLiveFilter.

    ĐIỂM KHÁC imm09: fetch UNCLAMPED (loop-paginate `_fetch_all_pm_rows`) ⇒
    BE-TC-OVD5 chứng minh >100 phiếu quá hạn KHÔNG bị cap 100 (imm09 R2 clamp bug).

    DELTA-style; mọi WO fixture trên 1 asset riêng, setUp purge → count deterministic.
    """

    OVD_USER = "_test_imm08_ovd_scope@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Ovd")
        cls.asset = _make_asset("-ovd")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        cls.schedule_name = _make_schedule(cls.asset.name, cls.template_name)["name"]
        if not frappe.db.exists("User", cls.OVD_USER):
            frappe.get_doc({
                "doctype": "User",
                "email": cls.OVD_USER,
                "first_name": "IMM08 Overdue Scope",
                "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        for sc in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Schedule", sc.name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        if frappe.db.exists("User", cls.OVD_USER):
            frappe.delete_doc("User", cls.OVD_USER, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Mỗi test tự dựng WO — purge giữa các test để count==rows deterministic.
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _mk_wo(self, *, tag: str, status: str, due_offset_days: int,
               is_late: int = 0, commit: bool = True) -> str:
        """PM WO fixture: insert Open/tương-lai (hợp lệ controller) rồi db.set_value
        status + due_date + is_late SAU insert (bypass controller — chỉ cần giá trị
        cột cho predicate/filter). Mirror TestPMListMineScope._make_wo."""
        wo = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "Open",
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        wo.insert(ignore_permissions=True)
        frappe.db.set_value("PM Work Order", wo.name, {
            "status": status,
            "due_date": add_days(nowdate(), due_offset_days),
            "is_late": is_late,
        })
        if commit:
            frappe.db.commit()
        return wo.name

    def _list_live(self, extra: dict | None = None, page: int = 1,
                   page_size: int = 100) -> dict:
        from assetcore.services.imm08 import list_work_orders
        f = {"overdue_live": 1, "asset_ref": self.asset.name}
        if extra:
            f.update(extra)
        return list_work_orders(f, page=page, page_size=page_size)

    # ── BE-TC-OVD1: filter chỉ chứa row is_overdue==True (LIVE) ───────────────
    def test_ovd1_filter_contains_only_live_overdue(self):
        # open in-hạn (due tương lai, cờ status Open) → KHÔNG
        ok = self._mk_wo(tag="OVD1-ok", status="Open", due_offset_days=10)
        # open live-overdue (due hôm qua, status vẫn Open) → CÓ
        live = self._mk_wo(tag="OVD1-live", status="Open", due_offset_days=-1)
        # Overdue cron-stamped → CÓ
        stamp = self._mk_wo(tag="OVD1-stamp", status="Overdue", due_offset_days=-3)
        res = self._list_live()
        names = {r["name"] for r in res["data"]}
        self.assertTrue(res["data"], "filter phải trả ≥1 row")
        self.assertTrue(all(r.get("is_overdue") for r in res["data"]),
                        "MỌI row trong list overdue_live PHẢI is_overdue==True")
        self.assertIn(live, names, "open live-overdue (status Open, due<today) PHẢI có")
        self.assertIn(stamp, names, "status==Overdue (cron-stamped) PHẢI có")
        self.assertNotIn(ok, names, "open in-hạn (due tương lai) KHÔNG được trong filter")

    # ── BE-TC-OVD2 (GATE anti-cron-miss): status STORED=Open vẫn xuất hiện ────
    def test_ovd2_anti_cron_miss_open_status_still_listed(self):
        # open WO due_date=hôm qua NHƯNG status vẫn Open (cron nightly CHƯA stamp).
        name = self._mk_wo(tag="OVD2", status="Open", due_offset_days=-1)
        self.assertEqual(
            frappe.db.get_value("PM Work Order", name, "status"), "Open",
            "tiền đề: cột STORED status PHẢI còn 'Open' (cron chưa flip → Overdue)")
        names = {r["name"] for r in self._list_live()["data"]}
        self.assertIn(name, names,
                      "GATE anti-cron-miss: WO due<today status STORED=Open PHẢI xuất "
                      "hiện trong filter LIVE (predicate LIVE ≠ cột stored status — nếu "
                      "MISS = badge/filter mismatch phá niềm tin KTV)")

    # ── BE-TC-OVD3 (monotonic superset): status==Overdue VẪN trong list ───────
    def test_ovd3_monotonic_superset_stamped_kept(self):
        # status==Overdue nhưng due_date TƯƠNG LAI (is_pm_overdue=False vì Overdue
        # ∉ OVERDUE_SOURCE_STATES) → chỉ nhánh OR status==Overdue giữ nó → chứng
        # minh superset monotonic (KHÔNG mất phiếu chip cũ cron-stamped).
        name = self._mk_wo(tag="OVD3", status="Overdue", due_offset_days=5)
        from assetcore.services.imm08 import is_pm_overdue
        self.assertFalse(
            is_pm_overdue("Overdue", add_days(nowdate(), 5)),
            "tiền đề: is_pm_overdue False cho status=Overdue (∉ source states) — "
            "membership dựa DUY NHẤT vào nhánh OR status==Overdue")
        names = {r["name"] for r in self._list_live()["data"]}
        self.assertIn(name, names,
                      "monotonic: WO status==Overdue (cron-stamped) VẪN trong filter "
                      "(OR superset — không mất phiếu chip cũ)")

    # ── BE-TC-OVD4 (is_late KHÔNG rò): Completed-late KHÔNG trong overdue ──────
    def test_ovd4_is_late_completed_not_listed(self):
        # Completed-late: is_late=1, due=hôm qua, status Completed. is_pm_overdue
        # False (Completed ∉ source states) + status != Overdue → is_overdue False.
        name = self._mk_wo(tag="OVD4", status="Completed", due_offset_days=-5, is_late=1)
        self.assertEqual(
            frappe.db.get_value("PM Work Order", name, "is_late"), 1,
            "tiền đề: is_late=1 (WO hoàn thành TRỄ)")
        names = {r["name"] for r in self._list_live()["data"]}
        self.assertNotIn(name, names,
                         "is_late (hoàn thành trễ) ≠ is_overdue (chưa xong quá hạn) — "
                         "Completed-late KHÔNG được rò vào filter overdue_live")

    # ── BE-TC-OVD5 (GATE scale): UNCLAMPED — >100 phiếu quá hạn đếm ĐỦ ─────────
    def test_ovd5_unclamped_pagination_over_100(self):
        from assetcore.services.imm08 import list_work_orders
        # 105 open-quá-hạn (due=hôm qua, status Open) → filter LIVE giữ CẢ 105.
        # Nếu fetch bị clamp-100 (imm09 R2 bug) → total=100, MẤT 5 phiếu.
        N = 105
        created = set()
        for i in range(N):
            created.add(self._mk_wo(tag=f"OVD5-{i}", status="Open",
                                    due_offset_days=-3, commit=False))
        frappe.db.commit()
        scope = {"asset_ref": self.asset.name}
        p1 = list_work_orders({"overdue_live": 1, **scope}, page=1, page_size=100)
        self.assertEqual(
            p1["pagination"]["total"], N,
            "UNCLAMPED GATE: pagination.total PHẢI = N (105) — KHÔNG cap 100 "
            "(imm09 R2 fetch page_size khổng lồ bị clamp-100 im lặng)")
        self.assertEqual(len(p1["data"]), 100, "page 1 đầy đúng page_size clamp=100")
        self.assertEqual(p1["pagination"]["total_pages"], 2, "ceil(105/100)=2")
        self.assertTrue(all(r.get("is_overdue") for r in p1["data"]),
                        "mọi row page 1 phải is_overdue==True")
        p2 = list_work_orders({"overdue_live": 1, **scope}, page=2, page_size=100)
        self.assertEqual(len(p2["data"]), 5, "page 2 phần dư = 105-100 = 5")
        self.assertEqual(p2["pagination"]["total"], N)
        n1 = {r["name"] for r in p1["data"]}
        n2 = {r["name"] for r in p2["data"]}
        self.assertFalse(n1 & n2, "page 1 và page 2 KHÔNG trùng row")
        self.assertEqual(n1 | n2, created,
                         "union 2 trang == toàn tập 105 phiếu tạo (không mất/không trùng)")

    # ── BE-TC-OVD6: baseline byte-identical (absent/falsy KHÔNG lọc) ──────────
    def test_ovd6_baseline_byte_identical(self):
        from assetcore.services.imm08 import list_work_orders

        def _sig(res):
            return ([r["name"] for r in res["data"]], res["pagination"])

        # Dựng WO hỗn hợp để baseline có nội dung (In Progress due tương lai — KHÔNG
        # overdue) → chứng minh path baseline KHÔNG bị overdue-filter.
        self._mk_wo(tag="OVD6-inprog", status="In Progress", due_offset_days=8)
        # falsy virtual key (0) POP sạch ⇒ path baseline y hệt absent (không đẩy cột
        # ma `overdue_live` vào get_all, không lọc overdue). So khớp names + pagination.
        base_absent = list_work_orders({}, page=1, page_size=50)
        base_zero = list_work_orders({"overdue_live": 0}, page=1, page_size=50)
        self.assertEqual(_sig(base_absent), _sig(base_zero),
                         "overdue_live=0 (falsy) POP sạch ⇒ baseline byte-identical "
                         "với absent (không lọc, không cột ma)")
        # status filter baseline vẫn hoạt động + KHÔNG bị overdue-filter (chứa WO
        # In Progress KHÔNG-overdue). Scope asset để fixture chắc chắn trong tập.
        scope = {"asset_ref": self.asset.name}
        base_status = list_work_orders({"status": "In Progress", **scope},
                                       page=1, page_size=100)
        self.assertTrue(
            all(r.get("status") == "In Progress" for r in base_status["data"]),
            "baseline status filter chỉ trả In Progress")
        self.assertTrue(base_status["data"],
                        "In Progress WO (KHÔNG overdue) PHẢI có ở baseline status filter "
                        "(baseline KHÔNG bị overdue-filter)")

    # ── BE-TC-OVD7 (invariant): filter total == Σ badge is_overdue baseline ────
    def test_ovd7_invariant_filter_total_equals_badge(self):
        from assetcore.services.imm08 import list_work_orders
        scope = {"asset_ref": self.asset.name}
        self._mk_wo(tag="OVD7-live", status="Open", due_offset_days=-1)   # live overdue
        self._mk_wo(tag="OVD7-stamp", status="Overdue", due_offset_days=5)  # stamped
        self._mk_wo(tag="OVD7-ok", status="Open", due_offset_days=10)     # in-hạn
        self._mk_wo(tag="OVD7-done", status="Completed",
                    due_offset_days=-10, is_late=1)                        # late-done
        full = list_work_orders({**scope}, page=1, page_size=100)
        badge_count = sum(1 for r in full["data"] if r.get("is_overdue"))
        live = list_work_orders({"overdue_live": 1, **scope}, page=1, page_size=100)
        self.assertEqual(
            live["pagination"]["total"], badge_count,
            "INVARIANT: membership filter total == Σ badge is_overdue trên baseline "
            "(badge == membership mọi path)")
        self.assertEqual(badge_count, 2,
                         "CHỈ OVD7-live (live-overdue) + OVD7-stamp (status=Overdue) = 2")


# ─── CR-37: cờ LIVE `is_overdue` trên WO DETAIL (parity list↔detail) ──────────

class TestPmDetailOverdueLiveFlag(FrappeTestCase):
    """CR-37 (mobile, cận an-toàn người bệnh) — `get_work_order(name)` PHẢI phơi cờ
    LIVE `is_overdue` (Python bool) BÊN CẠNH cờ STORED `is_late`, DÙNG CHUNG predicate
    `_enrich_pm_overdue` với list-item.

    GATE chính (phân kỳ LIVE vs STORED): PM WO có due_date < nowdate(), status Open
    (KHÔNG phải Overdue — cron nightly chưa stamp), completion_date rỗng, is_late=0
    (chưa hoàn thành trễ) → `is_overdue == True` TRONG KHI `is_late == False`. Nếu
    detail đọc cột STORED status==Overdue (trễ 1 nhịp scheduler) → badge 'Quá hạn' ẩn
    dù WO đã quá hạn LIVE = mismatch phá niềm tin KTV. RED trước fix (KeyError), GREEN sau.

    INVARIANT parity list↔detail: cờ LIVE trên detail == cờ LIVE trên list-item cùng
    record (≥1 quá-hạn + ≥1 trong-hạn; trong-hạn ⇒ False cả 2).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08OvdDetail")
        cls.asset = _make_asset("-ovddet")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        cls.schedule_name = _make_schedule(cls.asset.name, cls.template_name)["name"]
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        for sc in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Schedule", sc.name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _mk_wo(self, *, status: str, due_offset_days: int, is_late: int = 0,
               completion_date=None) -> str:
        """PM WO fixture: insert hợp lệ (Open/tương-lai) rồi db.set_value status +
        due_date + is_late + completion_date SAU insert (bypass controller — chỉ cần
        giá trị cột cho predicate). Mirror TestListPmOverdueLiveFilter._mk_wo."""
        wo = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "Open",
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        wo.insert(ignore_permissions=True)
        frappe.db.set_value("PM Work Order", wo.name, {
            "status": status,
            "due_date": add_days(nowdate(), due_offset_days),
            "is_late": is_late,
            "completion_date": completion_date,
        })
        frappe.db.commit()
        return wo.name

    def test_detail_is_overdue_live_diverges_from_is_late_stored(self):
        """[CR-37 RED-first] due<today, status Open, completion rỗng, is_late=0 →
        detail['is_overdue'] is True VÀ detail['is_late'] is False (LIVE ≠ STORED)."""
        from assetcore.services.imm08 import get_work_order
        name = self._mk_wo(status="Open", due_offset_days=-3, is_late=0,
                           completion_date=None)
        # tiền đề: cột STORED chưa phản ánh quá hạn (cron chưa stamp; chưa trễ-hoàn-thành).
        self.assertEqual(
            frappe.db.get_value("PM Work Order", name, "status"), "Open",
            "tiền đề: status STORED = Open (cron chưa flip → Overdue)")
        self.assertEqual(
            frappe.db.get_value("PM Work Order", name, "is_late"), 0,
            "tiền đề: is_late = 0 (chưa hoàn thành trễ)")
        detail = get_work_order(name)
        self.assertIn("is_overdue", detail,
                      "get_work_order PHẢI emit khoá 'is_overdue' (cờ LIVE, CR-37)")
        self.assertIs(detail["is_overdue"], True,
                      "is_overdue LIVE PHẢI True (due<today ∧ status ∈ source states)")
        self.assertIs(detail["is_late"], False,
                      "is_late STORED PHẢI False — chứng minh phân kỳ LIVE vs STORED "
                      "(is_late GIỮ NGUYÊN, KHÔNG bị is_overdue ghi đè)")

    def test_detail_is_overdue_false_when_in_window(self):
        """WO due tương lai, status Open → is_overdue False (không phantom-overdue)."""
        from assetcore.services.imm08 import get_work_order
        name = self._mk_wo(status="Open", due_offset_days=7)
        self.assertIs(get_work_order(name)["is_overdue"], False,
                      "WO trong-hạn (due tương lai) PHẢI is_overdue False")

    def test_parity_detail_matches_list_item(self):
        """[CR-37 INV parity] cờ LIVE detail == cờ LIVE list-item CÙNG record —
        ≥1 quá-hạn (True cả 2) + ≥1 trong-hạn (False cả 2)."""
        from assetcore.services.imm08 import get_work_order, list_work_orders
        overdue = self._mk_wo(status="Open", due_offset_days=-2)
        in_window = self._mk_wo(status="Open", due_offset_days=10)
        listing = list_work_orders({"asset_ref": self.asset.name}, page=1, page_size=100)
        by_name = {r["name"]: r for r in listing["data"]}
        for name, expected in ((overdue, True), (in_window, False)):
            self.assertIn(name, by_name, f"WO {name} PHẢI có trong list")
            det = get_work_order(name)["is_overdue"]
            lst = by_name[name].get("is_overdue")
            self.assertIs(det, expected,
                          f"detail is_overdue cho {name} PHẢI {expected}")
            self.assertEqual(
                det, lst,
                f"PARITY: detail is_overdue ({det}) == list-item is_overdue ({lst}) "
                f"CÙNG record {name} (CÙNG predicate _enrich_pm_overdue)")


class TestPMCompletionGate(FrappeTestCase):
    """BR-08-08/09/10 — gate hoàn thành PM (checklist rated + labor>0 + tem)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Gate")
        cls.asset = _make_asset("-gate")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value("AC Asset Category", {"category_name": "_TestCatIMM08Gate"}, "name")
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_wo(self):
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        return res["name"]

    def _rated_results(self, wo_name):
        wo = frappe.get_doc("PM Work Order", wo_name)
        return [
            {"idx": r.idx, "result": "Pass", "measured_value": None, "notes": ""}
            for r in (wo.checklist_results or [])
        ]

    def test_complete_blocked_when_checklist_unrated(self):
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        wo = frappe.get_doc("PM Work Order", wo_name)
        if not wo.checklist_results:
            self.skipTest("template không có checklist item")
        with self.assertRaises(ServiceError):
            submit_result(
                wo_name, checklist_results=[], overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30,
            )

    def test_complete_blocked_when_labor_zero(self):
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        with self.assertRaises(ServiceError):
            submit_result(
                wo_name, checklist_results=self._rated_results(wo_name),
                overall_result="Pass", pm_sticker_attached=1, duration_minutes=0,
            )

    def test_complete_blocked_when_sticker_missing(self):
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        with self.assertRaises(ServiceError):
            submit_result(
                wo_name, checklist_results=self._rated_results(wo_name),
                overall_result="Pass", pm_sticker_attached=0, duration_minutes=30,
            )

    def test_complete_succeeds_when_all_satisfied(self):
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        res = submit_result(
            wo_name, checklist_results=self._rated_results(wo_name),
            overall_result="Pass", pm_sticker_attached=1, duration_minutes=45,
        )
        frappe.db.commit()
        self.assertEqual(res["new_status"], "Completed")

    # ── BR-08-08 empty-checklist gate: regressions (AC3/AC4/AC5/AC6 seeded path) ──

    def test_ac3_green_rated_checklist_creates_one_task_log_and_advances_next_pm(self):
        """AC3: WO có ≥1 checklist item ĐÃ rated + duration>0 + sticker=1 → Completed,
        ĐÚNG 1 PM Task Log tạo, AC Asset.next_pm_date advance (đọc DB thực)."""
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        wo = frappe.get_doc("PM Work Order", wo_name)
        self.assertTrue(wo.checklist_results, "seeded template PHẢI có checklist item")
        logs0 = frappe.db.count("PM Task Log", {"pm_work_order": wo_name})
        next_before = frappe.db.get_value("AC Asset", self.asset.name, "next_pm_date")
        res = submit_result(
            wo_name, checklist_results=self._rated_results(wo_name),
            overall_result="Pass", pm_sticker_attached=1, duration_minutes=45,
        )
        frappe.db.commit()
        self.assertEqual(res["new_status"], "Completed")
        self.assertEqual(
            frappe.db.count("PM Task Log", {"pm_work_order": wo_name}), logs0 + 1,
            "AC3: ĐÚNG 1 PM Task Log mới cho WO green",
        )
        next_after = frappe.db.get_value("AC Asset", self.asset.name, "next_pm_date")
        self.assertTrue(next_after, "AC3: next_pm_date PHẢI được set sau khi hoàn thành")
        self.assertEqual(
            str(next_after), res["next_pm_date"],
            "AC3: AC Asset.next_pm_date persist == payload next_pm_date (1 SoT)",
        )
        self.assertNotEqual(
            str(next_after), str(next_before),
            "AC3: next_pm_date advance so với trước submit",
        )

    def test_ac4_unrated_checklist_fires_incomplete_not_swallowed_by_empty_gate(self):
        """AC4: WO có ≥1 checklist item nhưng result rỗng → gate BR-08-08 CŨ
        (CHECKLIST_INCOMPLETE) fire — KHÔNG bị empty-gate mới nuốt."""
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        wo = frappe.get_doc("PM Work Order", wo_name)
        self.assertTrue(wo.checklist_results, "seeded template PHẢI có checklist item")
        with self.assertRaises(ServiceError) as cm:
            submit_result(
                wo_name, checklist_results=[], overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30,
            )
        msg = cm.exception.message or ""
        self.assertIn(
            "chưa điền", msg,
            f"AC4: PHẢI là gate CHECKLIST_INCOMPLETE (item chưa điền), got: {msg!r}",
        )
        self.assertNotIn(
            "chưa có mục nào", msg,
            "AC4: KHÔNG được là empty-gate — WO có mục, chỉ chưa điền kết quả",
        )
        wo2 = frappe.get_doc("PM Work Order", wo_name)
        self.assertNotEqual(wo2.status, "Completed")
        self.assertEqual(wo2.docstatus, 0)

    def test_ac5_zero_duration_fires_duration_gate_order_preserved(self):
        """AC5-regression (BR-08-09): checklist hợp lệ + duration=0 → DURATION_REQUIRED —
        empty-gate mới KHÔNG đổi thứ tự gate."""
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        with self.assertRaises(ServiceError) as cm:
            submit_result(
                wo_name, checklist_results=self._rated_results(wo_name),
                overall_result="Pass", pm_sticker_attached=1, duration_minutes=0,
            )
        msg = cm.exception.message or ""
        self.assertIn(
            "Thời gian thực hiện", msg,
            f"AC5: PHẢI là gate DURATION_REQUIRED, got: {msg!r}",
        )

    def test_ac6_phantom_idx_not_silently_dropped(self):
        """AC6/BE-3: payload mang idx KHÔNG tồn tại trong child → raise IDX_UNKNOWN,
        KHÔNG âm thầm thành công; row idx thật KHÔNG đổi; WO GIỮ trạng thái."""
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        wo = frappe.get_doc("PM Work Order", wo_name)
        self.assertTrue(wo.checklist_results, "seeded template PHẢI có checklist item")
        real_idx = [r.idx for r in wo.checklist_results]
        self.assertNotIn(99, real_idx, "precondition: child KHÔNG có idx 99")
        with self.assertRaises(ServiceError) as cm:
            submit_result(
                wo_name, checklist_results=[{"idx": 99, "result": "Pass"}],
                overall_result="Pass", pm_sticker_attached=1, duration_minutes=30,
            )
        self.assertEqual(cm.exception.message_code, "IMM08-CHECKLIST-IDX-UNKNOWN")
        wo2 = frappe.get_doc("PM Work Order", wo_name)
        self.assertNotEqual(wo2.status, "Completed", "AC6: KHÔNG được hoàn thành giả")
        self.assertEqual(wo2.docstatus, 0)
        for r in wo2.checklist_results:
            self.assertFalse(r.result, "AC6: row thật KHÔNG bị mutate bởi payload phantom")

    def test_ac6b_mixed_valid_plus_phantom_idx_blocks_silent_success(self):
        """AC6 (case nguy hiểm): payload gồm idx hợp lệ ĐÃ rated + 1 idx phantom →
        KHÔNG được complete giả (drop câm idx phantom rồi báo thành công)."""
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        rows = self._rated_results(wo_name)  # tất cả idx hợp lệ, đã rated
        self.assertTrue(rows, "seeded template PHẢI có checklist item")
        payload = rows + [{"idx": 99, "result": "Pass"}]
        with self.assertRaises(ServiceError) as cm:
            submit_result(
                wo_name, checklist_results=payload, overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30,
            )
        self.assertEqual(cm.exception.message_code, "IMM08-CHECKLIST-IDX-UNKNOWN")
        wo2 = frappe.get_doc("PM Work Order", wo_name)
        self.assertNotEqual(
            wo2.status, "Completed",
            "AC6b: idx phantom bị drop câm + báo thành công = anti-pattern, PHẢI chặn",
        )
        self.assertEqual(wo2.docstatus, 0)


class TestPMEmptyChecklistGate(FrappeTestCase):
    """BR-08-08 (fix chính) — chặn nghiệm-thu-giả khi bảng kiểm RỖNG.

    Root-cause: vòng ``for item in doc.checklist_results`` là VACUOUS trên list rỗng
    → bỏ qua toàn bộ kiểm tra → WO template-less (0 checklist row) hoàn thành GIẢ
    (Completed + PM Task Log KHÔNG có bằng chứng công việc). Reproduce path: PM
    Checklist Template có 0 item (thiếu bảng kiểm mẫu) → schedule → create_adhoc_work_order
    → WO có checklist_results == []. Gate SSoT đặt ở validate_work_order (mọi path
    save status=Completed đều qua đây)."""

    @classmethod
    def setUpClass(cls):
        from assetcore.services.imm08 import create_schedule, create_template
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Empty")
        cls.asset = _make_asset("-empty")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        # Template RỖNG (0 checklist item) — reproduce "thiếu bảng kiểm mẫu".
        tmpl = create_template({
            "template_name": "_Test Empty Template",
            "asset_category": cls.cat,
            "pm_type": "Quarterly",
            "checklist_items": [],
        })
        cls.template_name = tmpl["name"]
        sched = create_schedule({
            "asset_ref": cls.asset.name,
            "pm_type": "Quarterly",
            "pm_interval_days": 90,
            "checklist_template": cls.template_name,
            "status": "Active",
        })
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM08Empty"}, "name"
        )
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_empty_wo(self):
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        return res["name"]

    def test_be4_template_less_path_yields_zero_checklist_rows(self):
        """BE-4: xác nhận đường tạo WO template-less thực sự cho 0 checklist row —
        reproduce path cho AC1/AC2."""
        wo_name = self._make_empty_wo()
        wo = frappe.get_doc("PM Work Order", wo_name)
        self.assertEqual(
            len(wo.checklist_results or []), 0,
            "reproduce: WO tạo từ template rỗng PHẢI có checklist_results == []",
        )

    def test_ac1_submit_on_empty_checklist_raises_and_stays_open(self):
        """AC1 (RED→GREEN): submit_result trên WO checklist rỗng → raise ServiceError
        (VALIDATION, message VI 'bảng kiểm chưa có mục nào'); WO GIỮ trạng thái
        (≠ Completed), docstatus vẫn 0."""
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_empty_wo()
        status_before = frappe.db.get_value("PM Work Order", wo_name, "status")
        with self.assertRaises(ServiceError) as cm:
            submit_result(
                wo_name, checklist_results=[], overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=45,
            )
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)
        msg = cm.exception.message or ""
        self.assertIn(
            "bảng kiểm chưa có mục nào", msg,
            f"AC1: message VI PHẢI nêu bảng kiểm rỗng, got: {msg!r}",
        )
        wo = frappe.get_doc("PM Work Order", wo_name)
        self.assertNotEqual(wo.status, "Completed", "AC1: WO KHÔNG được Completed giả")
        self.assertEqual(wo.status, status_before, "AC1: status GIỮ nguyên")
        self.assertEqual(wo.docstatus, 0, "AC1: docstatus vẫn 0 (chưa submit)")

    def test_ac2_no_persist_side_effects_after_blocked_submit(self):
        """AC2 (persist-thật, đọc DB thực): sau AC1 — KHÔNG tạo PM Task Log mới,
        AC Asset.next_pm_date & last_pm_date KHÔNG đổi (KHÔNG tin return payload)."""
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_empty_wo()
        logs_before = frappe.db.count("PM Task Log", {"pm_work_order": wo_name})
        next_before = frappe.db.get_value("AC Asset", self.asset.name, "next_pm_date")
        last_before = frappe.db.get_value("AC Asset", self.asset.name, "last_pm_date")
        with self.assertRaises(ServiceError):
            submit_result(
                wo_name, checklist_results=[], overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=45,
            )
        frappe.db.rollback()
        self.assertEqual(
            frappe.db.count("PM Task Log", {"pm_work_order": wo_name}), logs_before,
            "AC2: KHÔNG tạo PM Task Log mới khi submit bị chặn",
        )
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "next_pm_date"), next_before,
            "AC2: AC Asset.next_pm_date KHÔNG đổi (đọc DB thực)",
        )
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "last_pm_date"), last_before,
            "AC2: AC Asset.last_pm_date KHÔNG đổi (đọc DB thực)",
        )


class TestPMSubmitResultIdempotency(FrappeTestCase):
    """CR-24-PM — idempotency `client_request_id` cho submit_result (mobile write-outbox
    re-drain). Mở rộng CR-24 (imm12 report_incident) sang submit_pm_result NHƯNG store =
    frappe.cache() thay DocField (KHÔNG field mới ⇒ KHÔNG bench migrate).

    Khoá truthy → side-effect áp ĐÚNG 1 lần (WO Completed 1 lần, completion_date +
    next_pm_date KHÔNG drift, CM WO KHÔNG double); replay trả CÙNG payload verbatim,
    KHÔNG raise. Rỗng ⇒ legacy path y nguyên (0 dedup, NULL-semantics). Key scoped
    (wo_name, client_request_id) ⇒ 2 WO / 2 key độc lập.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Idem")
        cls.asset = _make_asset("-idem")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        # Idempotency cache là Redis-backed (TTL 24h) — dọn để test hermetic giữa run.
        frappe.cache().delete_keys("pm_submit_result::*")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM08Idem"}, "name"
        )
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    # ── fixture helpers ────────────────────────────────────────────────────────
    def _make_wo(self):
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        return res["name"]

    def _rated_results(self, wo_name):
        wo = frappe.get_doc("PM Work Order", wo_name)
        return [
            {"idx": r.idx, "result": "Pass", "measured_value": None, "notes": ""}
            for r in (wo.checklist_results or [])
        ]

    def _results_one_fail_minor(self, wo_name):
        rows = self._rated_results(wo_name)
        self.assertTrue(rows, "template PHẢI có checklist item để test escalation")
        # Flip dòng cuối (item non-critical) → Fail–Minor: has_minor → 1 CM WO Medium,
        # WO GIỮ status Completed (elif branch KHÔNG halt) — @services/imm08.py:406-407.
        rows[-1]["result"] = "Fail–Minor"
        return rows

    def _cm_count(self, wo_name):
        return frappe.db.count(
            "PM Work Order", {"source_pm_wo": wo_name, "wo_type": "Corrective"}
        )

    def _completion_date(self, wo_name):
        return frappe.db.get_value("PM Work Order", wo_name, "completion_date")

    def _task_log_count(self, wo_name):
        return frappe.db.count("PM Task Log", {"pm_work_order": wo_name})

    # ── acceptance tests ───────────────────────────────────────────────────────
    def test_submit_pm_result_idempotent_replay_same_key(self):
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        # Baseline delta (PM Task Log = immutable audit, KHÔNG purge + naming-series có thể
        # recycle tên WO ⇒ đếm tuyệt-đối = môi-trường; invariant THẬT = replay tạo 0 log mới).
        logs0 = self._task_log_count(wo)
        p1 = submit_result(
            wo, checklist_results=self._rated_results(wo), overall_result="Pass",
            pm_sticker_attached=1, duration_minutes=30, client_request_id="k1",
        )
        frappe.db.commit()
        cd1 = self._completion_date(wo)
        self.assertEqual(self._task_log_count(wo), logs0 + 1, "call 1 tạo ĐÚNG 1 PM Task Log")
        p2 = submit_result(
            wo, checklist_results=self._rated_results(wo), overall_result="Pass",
            pm_sticker_attached=1, duration_minutes=30, client_request_id="k1",
        )
        self.assertEqual(p2, p1, "replay cùng key PHẢI trả payload verbatim")
        self.assertEqual(p2["new_status"], "Completed")
        self.assertEqual(self._completion_date(wo), cd1, "completion_date KHÔNG drift lần 2")
        self.assertEqual(p2["next_pm_date"], p1["next_pm_date"], "next_pm_date persist 1 lần")
        self.assertEqual(self._task_log_count(wo), logs0 + 1, "replay KHÔNG tạo PM Task Log mới")

    def test_submit_pm_result_idempotent_no_duplicate_cm_wo(self):
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        p1 = submit_result(
            wo, checklist_results=self._results_one_fail_minor(wo), overall_result="Fail",
            pm_sticker_attached=1, duration_minutes=30, client_request_id="k1",
        )
        frappe.db.commit()
        self.assertEqual(self._cm_count(wo), 1, "lần 1 escalate ĐÚNG 1 CM WO")
        self.assertIsNotNone(p1["cm_wo_created"], "payload PHẢI echo CM WO name")
        p2 = submit_result(
            wo, checklist_results=self._results_one_fail_minor(wo), overall_result="Fail",
            pm_sticker_attached=1, duration_minutes=30, client_request_id="k1",
        )
        self.assertEqual(self._cm_count(wo), 1, "lần 2 KHÔNG tạo CM WO trùng")
        self.assertEqual(p2["cm_wo_created"], p1["cm_wo_created"], "cm_wo_created cùng name")
        self.assertEqual(p2, p1, "replay payload verbatim (kể cả nhánh escalate)")

    def test_submit_pm_result_legacy_no_key_unchanged(self):
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        p1 = submit_result(
            wo, checklist_results=self._rated_results(wo), overall_result="Pass",
            pm_sticker_attached=1, duration_minutes=30,
        )
        frappe.db.commit()
        self.assertEqual(p1["new_status"], "Completed")
        # KHÔNG key ⇒ 0 dedup ⇒ gọi lại raise ALREADY_SUBMITTED (hành vi legacy nguyên vẹn).
        with self.assertRaises(ServiceError) as cm:
            submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30,
            )
        self.assertEqual(cm.exception.message_code, "IMM08-ALREADY-SUBMITTED")

    def test_submit_pm_result_distinct_keys_isolated(self):
        from assetcore.services.imm08 import submit_result
        wo_a = self._make_wo()
        wo_b = self._make_wo()
        pa = submit_result(
            wo_a, checklist_results=self._rated_results(wo_a), overall_result="Pass",
            pm_sticker_attached=1, duration_minutes=30, client_request_id="kSame",
        )
        pb = submit_result(
            wo_b, checklist_results=self._rated_results(wo_b), overall_result="Pass",
            pm_sticker_attached=1, duration_minutes=30, client_request_id="kSame",
        )
        frappe.db.commit()
        self.assertNotEqual(pa["name"], pb["name"], "2 WO khác nhau")
        # CÙNG client_request_id nhưng key scoped theo wo_name ⇒ KHÔNG nhiễm chéo:
        # replay từng cái trả ĐÚNG payload của chính nó.
        ra = submit_result(
            wo_a, checklist_results=self._rated_results(wo_a), overall_result="Pass",
            pm_sticker_attached=1, duration_minutes=30, client_request_id="kSame",
        )
        rb = submit_result(
            wo_b, checklist_results=self._rated_results(wo_b), overall_result="Pass",
            pm_sticker_attached=1, duration_minutes=30, client_request_id="kSame",
        )
        self.assertEqual(ra, pa, "replay wo_a trả payload wo_a (KHÔNG payload wo_b)")
        self.assertEqual(rb, pb, "replay wo_b trả payload wo_b")
        self.assertEqual(ra["name"], wo_a)
        self.assertEqual(rb["name"], wo_b)

    def test_submit_pm_result_race_same_key_single_effect(self):
        from assetcore.services import imm08
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        key = "krace"
        # Winner A: submit đầy đủ + set cache.
        p1 = submit_result(
            wo, checklist_results=self._rated_results(wo), overall_result="Pass",
            pm_sticker_attached=1, duration_minutes=30, client_request_id=key,
        )
        frappe.db.commit()
        cd1 = self._completion_date(wo)
        logs1 = self._task_log_count(wo)
        # Loser B đã qua pre-check TRƯỚC khi A cache (race window): ép cache-get MISS
        # đúng lần đầu → chạm nhánh docstatus==1 + winner-reread (re-read cache thật,
        # trả idempotent thay vì raise 'already completed'). Patch seam nội-bộ
        # (_pm_submit_cache_get) — KHÔNG đụng frappe.cache() dùng chung bởi rbac.
        real_get = imm08._pm_submit_cache_get
        state = {"first": True}

        def _miss_first(cache_key):
            if state["first"]:
                state["first"] = False
                return None
            return real_get(cache_key)

        with patch.object(imm08, "_pm_submit_cache_get", side_effect=_miss_first):
            p2 = submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30, client_request_id=key,
            )
        self.assertEqual(p2, p1, "winner-reread PHẢI trả cùng payload, KHÔNG raise")
        self.assertEqual(self._completion_date(wo), cd1, "side-effect chỉ áp 1 lần")
        self.assertEqual(self._task_log_count(wo), logs1, "KHÔNG double PM Task Log")

    def test_submit_pm_result_invariants_intact(self):
        # Bất biến API layer: signature KHÔNG có `user` (anti-spoof), client_request_id
        # optional default str='' (KHÔNG None), POST-only @source, rbac.require('pm.submit').
        import inspect
        from assetcore.api.imm08 import submit_pm_result

        sig = inspect.signature(submit_pm_result)
        self.assertNotIn("user", sig.parameters, "anti-spoof: signature KHÔNG nhận `user`")
        self.assertIn("client_request_id", sig.parameters, "PHẢI có param idempotency")
        self.assertEqual(
            sig.parameters["client_request_id"].default, "",
            "optional PHẢI default str='' (NULL-semantics, KHÔNG None → tránh 417)",
        )
        # POST-ONLY-ENFORCED-AT-SOURCE (registry introspect, gate THẬT dispatcher).
        allowed = set(
            frappe.allowed_http_methods_for_whitelisted_func.get(submit_pm_result) or []
        )
        self.assertEqual(allowed, {"POST"}, f"submit_pm_result PHẢI POST-only, got {allowed}")
        # rbac.require('pm.submit'): Guest thiếu cap → PermissionError (chặn TRƯỚC handle).
        try:
            frappe.set_user("Guest")
            with self.assertRaises(frappe.PermissionError):
                submit_pm_result(name="PM-WO-GUARD-NOPE")
        finally:
            frappe.set_user("Administrator")

    # ── CR-24 §2.1 header-parity (HANDOFF): honor X-Idempotency-Key / Idempotency-Key ──
    @staticmethod
    def _hdr_factory(mapping):
        def _hdr(key, default=None):
            return mapping.get(key, default or "")
        return _hdr

    def test_submit_result_header_only_replay(self):
        """RED-first: header X-Idempotency-Key GIỐNG nhau, body client_request_id rỗng →
        lần 2 REPLAY envelope lần 1 VERBATIM (WO Completed đúng 1 lần, next_pm_date KHÔNG
        drift, KHÔNG double CM escalation). Hiện ĐỎ trước fix (cache key chỉ dùng body
        param → lần 2 rơi ALREADY_SUBMITTED)."""
        from unittest import mock
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        key = "hdr-only-k1"
        logs0 = self._task_log_count(wo)
        with mock.patch("frappe.get_request_header",
                        side_effect=self._hdr_factory({"X-Idempotency-Key": key})):
            p1 = submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="",
            )
            frappe.db.commit()
            cd1 = self._completion_date(wo)
            self.assertEqual(self._task_log_count(wo), logs0 + 1, "call 1 tạo ĐÚNG 1 PM Task Log")
            p2 = submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="",
            )
        self.assertEqual(p2, p1, "header-only replay PHẢI trả payload verbatim")
        self.assertEqual(p2["new_status"], "Completed")
        self.assertEqual(self._completion_date(wo), cd1, "completion_date KHÔNG drift lần 2")
        self.assertEqual(self._task_log_count(wo), logs0 + 1, "replay KHÔNG tạo PM Task Log mới")

    def test_submit_result_header_only_no_double_cm_wo(self):
        from unittest import mock
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        key = "hdr-only-cm"
        with mock.patch("frappe.get_request_header",
                        side_effect=self._hdr_factory({"X-Idempotency-Key": key})):
            p1 = submit_result(
                wo, checklist_results=self._results_one_fail_minor(wo), overall_result="Fail",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="",
            )
            frappe.db.commit()
            self.assertEqual(self._cm_count(wo), 1, "lần 1 escalate ĐÚNG 1 CM WO")
            p2 = submit_result(
                wo, checklist_results=self._results_one_fail_minor(wo), overall_result="Fail",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="",
            )
        self.assertEqual(self._cm_count(wo), 1, "header-only replay KHÔNG tạo CM WO thứ 2")
        self.assertEqual(p2, p1, "replay payload verbatim (nhánh escalate)")

    def test_submit_result_body_wins_over_header(self):
        """body='B' + header='H' ⇒ dedup theo body 'B' (cache keyed 'B', KHÔNG 'H')."""
        from unittest import mock
        from assetcore.services import imm08 as _svc
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        with mock.patch("frappe.get_request_header",
                        side_effect=self._hdr_factory({"X-Idempotency-Key": "H"})):
            p1 = submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="B",
            )
            frappe.db.commit()
            p2 = submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="B",
            )
        self.assertEqual(p2, p1, "body 'B' THẮNG header → replay theo 'B' HIT verbatim")
        self.assertIsNotNone(
            _svc._pm_submit_cache_get(_svc._pm_submit_cache_key(wo, "B")),
            "cache PHẢI keyed theo body 'B' (body wins over header)")
        self.assertIsNone(
            _svc._pm_submit_cache_get(_svc._pm_submit_cache_key(wo, "H")),
            "cache KHÔNG được keyed theo header 'H' khi body present")

    def test_submit_result_alias_idempotency_key_replay(self):
        """alias 'Idempotency-Key' (KHÔNG tiền tố X-) cũng honor cho dedup."""
        from unittest import mock
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        with mock.patch("frappe.get_request_header",
                        side_effect=self._hdr_factory({"Idempotency-Key": "alias-k"})):
            p1 = submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="",
            )
            frappe.db.commit()
            p2 = submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="",
            )
        self.assertEqual(p2, p1, "alias Idempotency-Key (no X-) cũng replay verbatim")
        self.assertEqual(p2["new_status"], "Completed")

    def test_submit_result_no_key_no_header_legacy_already_submitted(self):
        """cả body param LẪN header vắng ⇒ NO-OP dedup: lần 2 raise ALREADY_SUBMITTED
        (legacy path byte-identical)."""
        from unittest import mock
        from assetcore.services.imm08 import submit_result
        wo = self._make_wo()
        with mock.patch("frappe.get_request_header", side_effect=self._hdr_factory({})):
            p1 = submit_result(
                wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                pm_sticker_attached=1, duration_minutes=30, client_request_id="",
            )
            frappe.db.commit()
            self.assertEqual(p1["new_status"], "Completed")
            with self.assertRaises(ServiceError) as cm:
                submit_result(
                    wo, checklist_results=self._rated_results(wo), overall_result="Pass",
                    pm_sticker_attached=1, duration_minutes=30, client_request_id="",
                )
        self.assertEqual(cm.exception.message_code, "IMM08-ALREADY-SUBMITTED")


class TestLLBE1PMStats417(FrappeTestCase):
    """LL-BE-1 guard: get_pm_dashboard_stats (GET, year/month optional) phải
    tolerate query rỗng (`?year=`) mà KHÔNG raise FrappeTypeError → HTTP 417.

    Hiện AN TOÀN vì `api/imm08.py` có `from __future__ import annotations`
    (annotation = string → validator SKIP coercion). Test GUARD chống regression
    nếu future-import bị gỡ / annotation thành real-type (khi đó `int=None`+`""`
    → 417). Cf. dashboard.py (không future-import) đã từng 417.
    """

    def test_pm_stats_empty_year_no_417(self):
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.imm08 import get_pm_dashboard_stats

        wrapped = validate_argument_types(
            get_pm_dashboard_stats, apply_condition=lambda: True
        )
        resp = wrapped(year="", month="")
        self.assertIsInstance(resp, dict)

    def test_pm_stats_missing_args_no_417(self):
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.imm08 import get_pm_dashboard_stats

        wrapped = validate_argument_types(
            get_pm_dashboard_stats, apply_condition=lambda: True
        )
        resp = wrapped()
        self.assertIsInstance(resp, dict)


class TestNotificationContract(FrappeTestCase):
    """Sprint Notification vòng 3 — IMM-08 raise qua nthrow/nthrow_in_hook.

    Bất biến (docs/imm-08 §11): mọi business error có message_code; API envelope
    hydrate severity/title/action_hint qua api_handler.handle().
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Notify")
        cls.asset = _make_asset("-notify")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM08Notify"}, "name"
        )
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_wo(self):
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        return res["name"]

    # ── service-layer nthrow → message_code ───────────────────────────────────

    def test_get_work_order_not_found_has_message_code(self):
        from assetcore.services.imm08 import get_work_order
        with self.assertRaises(ServiceError) as cm:
            get_work_order("PM-WO-DOES-NOT-EXIST")
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)
        self.assertEqual(cm.exception.message_code, "IMM08-WO-NOT-FOUND")

    def test_template_not_found_has_message_code(self):
        from assetcore.services.imm08 import get_template
        with self.assertRaises(ServiceError) as cm:
            get_template("TMPL-DOES-NOT-EXIST")
        self.assertEqual(cm.exception.message_code, "IMM08-TEMPLATE-NOT-FOUND")

    def test_assign_bad_state_has_message_code(self):
        from assetcore.services.imm08 import assign_technician
        wo_name = self._make_wo()
        # assign lần 1: Open → In Progress; assign lần 2 → BAD_STATE (không OPEN/OVERDUE)
        assign_technician(wo_name, technician="Administrator")
        frappe.db.commit()
        with self.assertRaises(ServiceError) as cm:
            assign_technician(wo_name, technician="Administrator")
        # bucket .code suy từ http_status 409 (CONFLICT); contract dựa message_code.
        self.assertEqual(cm.exception.message_code, "IMM08-BAD-STATE")

    def test_assign_open_wo_transitions_in_progress_and_audits_under_maintenance(self):
        """R35 PM-DISPATCH BE-unit (assignPmTechnician): assign Open WO → status In Progress +
        assigned_to set + asset → Under Maintenance + SINH Lifecycle Event audit (BR-08 traceability).

        Verify side-effect THẬT (KHÔNG chỉ return): WO persisted In Progress, asset.lifecycle_status
        = Under Maintenance, ≥1 row Asset Lifecycle Event to_status='Under Maintenance' (audit trail
        trục CLAUDE.md §10). Đây là transition mà contract assignPmTechnician phơi cho mobile."""
        from assetcore.services.imm08 import assign_technician, PMStatus
        from assetcore.services.shared import AssetStatus
        wo_name = self._make_wo()
        # Shared cls.asset có thể bị test khác để lại 'Under Maintenance' ⇒ transition_asset_status
        # no-op (prev==to → KHÔNG sinh event). Reset về Active (test-setup, bypass event) để verify
        # transition + audit của CHÍNH assign này.
        frappe.db.set_value("AC Asset", self.asset.name, "lifecycle_status", AssetStatus.ACTIVE)
        frappe.db.commit()
        before = frappe.db.count("Asset Lifecycle Event", {"asset": self.asset.name})
        res = assign_technician(wo_name, technician="Administrator")
        frappe.db.commit()
        # return shape = closed 3-key {name,status,assigned_to} (grounded services/imm08.py:679).
        self.assertEqual(set(res.keys()), {"name", "status", "assigned_to"})
        self.assertEqual(res["name"], wo_name)
        self.assertEqual(res["status"], PMStatus.IN_PROGRESS)
        self.assertEqual(res["assigned_to"], "Administrator")
        # WO persisted: status In Progress + assigned_to set.
        wo = frappe.get_doc("PM Work Order", wo_name)
        self.assertEqual(wo.status, PMStatus.IN_PROGRESS)
        self.assertEqual(wo.assigned_to, "Administrator")
        self.assertEqual(wo.assigned_by, frappe.session.user)
        # asset → Under Maintenance (transition_asset_status @services/imm08.py:678).
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "lifecycle_status"),
            AssetStatus.UNDER_MAINTENANCE,
        )
        # SINH Lifecycle Event audit — side-effect THẬT (chống false-green).
        after = frappe.db.count("Asset Lifecycle Event", {"asset": self.asset.name})
        self.assertGreater(after, before, "assign PHẢI sinh ≥1 Lifecycle Event audit (BR-08 traceability).")
        evt = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": self.asset.name, "to_status": AssetStatus.UNDER_MAINTENANCE},
            fields=["name", "root_record"], order_by="creation desc", limit=1,
        )
        self.assertTrue(evt, "PHẢI có Lifecycle Event to_status='Under Maintenance' cho asset sau assign.")
        self.assertEqual(evt[0]["root_record"], wo_name, "Lifecycle Event PHẢI trỏ root_record = PM WO (traceability).")

    def test_assign_missing_wo_has_message_code(self):
        """R35 PM-DISPATCH BE-unit: assign WO không tồn tại → IMM08_WO_NOT_FOUND (404 bucket)."""
        from assetcore.services.imm08 import assign_technician
        with self.assertRaises(ServiceError) as cm:
            assign_technician("PM-WO-DOES-NOT-EXIST", technician="Administrator")
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)
        self.assertEqual(cm.exception.message_code, "IMM08-WO-NOT-FOUND")

    def test_report_major_failure_api_handler_returns_4key_envelope(self):
        """R36 PM→CM ESCALATION BE-unit (reportMajorFailure SIGNATURE-FIX): gọi API HANDLER
        api.imm08.report_major_failure → 200 success envelope, data closed 4-key
        {pm_wo,new_status,cm_wo_created,asset_status} (services/imm08.py:792-797).

        RED-before: handler cũ parse + truyền `failed_item_indexes=` vào service
        report_major_failure(pm_wo_name, *, failure_description) — signature KHÔNG nhận ⇒ TypeError;
        handle() KHÔNG bắt non-ServiceError (api_handler.py:43-46) ⇒ bubble → HTTP-500 mỗi call.
        GREEN-after DROP field: trả envelope đúng. Gọi HANDLER (KHÔNG service) để bắt bug tầng-API
        — service-only test KHÔNG phơi mismatch. Verify side-effect THẬT: PM WO Halted + asset OOS
        + CM WO khẩn (Asset Repair source_pm_wo) tồn tại."""
        from assetcore.api.imm08 import report_major_failure as api_report_major_failure
        from assetcore.services.imm08 import PMStatus
        from assetcore.services.shared import AssetStatus
        wo_name = self._make_wo()
        cm_wo = None
        try:
            res = api_report_major_failure(
                pm_wo_name=wo_name,
                failure_description="Compressor không khởi động — điện áp 0V",
            )
            frappe.db.commit()
            # success envelope (handle wrap _ok) — KHÔNG TypeError/500 (signature-fix).
            self.assertTrue(res.get("success"), f"PHẢI success envelope (signature-fix), got {res}.")
            data = res.get("data") or {}
            self.assertEqual(
                set(data.keys()), {"pm_wo", "new_status", "cm_wo_created", "asset_status"},
                f"data PHẢI closed 4-key (services/imm08.py:792-797), got {sorted(data.keys())}.",
            )
            self.assertEqual(data["pm_wo"], wo_name)
            self.assertEqual(data["new_status"], PMStatus.HALTED_MAJOR)
            self.assertEqual(data["asset_status"], AssetStatus.OUT_OF_SERVICE)
            cm_wo = data["cm_wo_created"]
            self.assertTrue(cm_wo, "cm_wo_created PHẢI có (CM WO khẩn tạo).")
            # side-effect THẬT (chống false-green): PM WO Halted + asset OOS + CM WO (Asset Repair) tồn tại.
            self.assertEqual(frappe.db.get_value("PM Work Order", wo_name, "status"), PMStatus.HALTED_MAJOR)
            self.assertEqual(
                frappe.db.get_value("AC Asset", self.asset.name, "lifecycle_status"),
                AssetStatus.OUT_OF_SERVICE,
            )
            self.assertTrue(frappe.db.exists("Asset Repair", cm_wo), "CM WO (Asset Repair) PHẢI tồn tại.")
            self.assertEqual(frappe.db.get_value("Asset Repair", cm_wo, "source_pm_wo"), wo_name)
        finally:
            # cleanup CM WO + Incident sinh ra (chống leak; asset/PM-WO do tearDownClass purge).
            if cm_wo and frappe.db.exists("Asset Repair", cm_wo):
                for inc in frappe.get_all("Incident Report", filters={"linked_repair_wo": cm_wo}, pluck="name"):
                    frappe.delete_doc("Incident Report", inc, force=True, ignore_permissions=True)
                d = frappe.get_doc("Asset Repair", cm_wo)
                if d.docstatus == 1:
                    d.cancel()
                frappe.delete_doc("Asset Repair", cm_wo, force=True, ignore_permissions=True)
            frappe.db.commit()

    def test_report_major_failure_missing_wo_404_envelope(self):
        """R36 BE-unit: handler report_major_failure WO∄ → Error envelope success=False code NOT_FOUND
        http_status 404 (handle bắt ServiceError từ nthrow IMM08_WO_NOT_FOUND @services/imm08.py:747).
        Khẳng định 404 đến qua HTTP-200 + Error body (KHÔNG raise) — khớp slot {200,401,403} contract."""
        from assetcore.api.imm08 import report_major_failure as api_report_major_failure
        res = api_report_major_failure(
            pm_wo_name="PM-WO-DOES-NOT-EXIST",
            failure_description="x",
        )
        self.assertFalse(res.get("success"), f"WO∄ PHẢI Error envelope, got {res}.")
        self.assertEqual(res.get("code"), "NOT_FOUND")
        self.assertEqual(res.get("http_status"), 404)
        self.assertEqual(res.get("message_code"), "IMM08-WO-NOT-FOUND")

    def test_reschedule_api_handler_happy_4key_envelope_restores_active(self):
        """R37 PM-RESCHEDULE BE-unit (reschedulePm happy-path): gọi API HANDLER api.imm08.reschedule_pm →
        200 success envelope, data closed 4-key {name,old_date,new_date,status} (services/imm08.py:823),
        status = PMStatus.PENDING_BUSY ('Pending–Device Busy' en-dash U+2013), VÀ asset khôi phục Active khi
        WO đang In Progress (was_in_progress → _transition_asset Active @services/imm08.py:821-822).

        Gọi HANDLER (KHÔNG service-only) để bắt bug tầng-API (signature parity name/new_date/reason). Verify
        side-effect THẬT (chống false-green): WO persisted Pending–Device Busy + due_date đổi + asset Active."""
        from assetcore.api.imm08 import reschedule_pm as api_reschedule_pm
        from assetcore.services.imm08 import assign_technician, PMStatus
        from assetcore.services.shared import AssetStatus
        # Shared cls.asset có thể bị test khác (report_major_failure) để lại 'Out of Service' ⇒ create_adhoc
        # _work_order reject BR-00-05. Reset về Active (test-setup, bypass event) để self-contained.
        frappe.db.set_value("AC Asset", self.asset.name, "lifecycle_status", AssetStatus.ACTIVE)
        frappe.db.commit()
        wo_name = self._make_wo()
        # Đưa WO về In Progress (Open→In Progress + asset→Under Maintenance) để verify nhánh restore-Active.
        assign_technician(wo_name, technician="Administrator")
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "lifecycle_status"),
            AssetStatus.UNDER_MAINTENANCE,
            "PRECONDITION: assign PHẢI đặt asset → Under Maintenance trước khi reschedule.",
        )
        old_due = str(frappe.db.get_value("PM Work Order", wo_name, "due_date"))
        new_due = str(add_days(nowdate(), 14))
        res = api_reschedule_pm(
            name=wo_name,
            new_date=new_due,
            reason="Thiết bị đang dùng cho ca cấp cứu, dời sang tuần sau",
        )
        frappe.db.commit()
        # success envelope (handle wrap _ok).
        self.assertTrue(res.get("success"), f"PHẢI success envelope, got {res}.")
        data = res.get("data") or {}
        self.assertEqual(
            set(data.keys()), {"name", "old_date", "new_date", "status"},
            f"data PHẢI closed 4-key {{name,old_date,new_date,status}} (services/imm08.py:823), got {sorted(data.keys())}.",
        )
        self.assertEqual(data["name"], wo_name)
        self.assertEqual(data["old_date"], old_due)
        self.assertEqual(data["new_date"], new_due)
        self.assertEqual(data["status"], PMStatus.PENDING_BUSY)
        # BYTE-MATCH en-dash U+2013 (KHÔNG hyphen-minus U+002D) — copy byte-khớp PMStatus.PENDING_BUSY :50.
        non_ascii = [c for c in data["status"] if ord(c) > 0x7F]
        self.assertEqual(
            [hex(ord(c)) for c in non_ascii], ["0x2013"],
            f"status PHẢI chứa en-dash U+2013 DUY NHẤT (PMStatus.PENDING_BUSY :50), got {[hex(ord(c)) for c in non_ascii]}.",
        )
        # side-effect THẬT: WO Pending–Device Busy + due_date đổi + asset khôi phục Active.
        self.assertEqual(frappe.db.get_value("PM Work Order", wo_name, "status"), PMStatus.PENDING_BUSY)
        self.assertEqual(str(frappe.db.get_value("PM Work Order", wo_name, "due_date")), new_due)
        self.assertEqual(
            frappe.db.get_value("AC Asset", self.asset.name, "lifecycle_status"),
            AssetStatus.ACTIVE,
            "asset PHẢI khôi phục 'Active' khi WO đang In Progress lúc hoãn (services/imm08.py:821-822).",
        )

    def test_reschedule_reason_too_short_validation_422_envelope(self):
        """R37 PM-RESCHEDULE BE-unit: reason < 5 ký tự → ServiceError VALIDATION (guard
        len(reason.strip()) < 5 @services/imm08.py:808) → Error envelope success=False code VALIDATION.
        Guard chạy TRƯỚC khi lookup WO → KHÔNG cần WO hợp lệ. Lỗi đến qua HTTP-200 + Error body (KHÔNG raise)."""
        from assetcore.api.imm08 import reschedule_pm as api_reschedule_pm
        from assetcore.services.shared import ErrorCode
        res = api_reschedule_pm(name="PM-WO-ANY", new_date=str(add_days(nowdate(), 7)), reason="x")
        self.assertFalse(res.get("success"), f"reason<5 PHẢI Error envelope, got {res}.")
        self.assertEqual(res.get("code"), ErrorCode.VALIDATION, "code PHẢI VALIDATION (guard reason<5 @services/imm08.py:808).")
        # http_status @source = 422: reschedule dùng helper validation() (errors.py:62 http_status=422)
        #   @services/imm08.py:809; handle() → _err(http_status=e.http_status)=422 (api_handler.py:69).
        #   RECONCILED (ADR-MOBILE-014 + spec §0.1.3): BE=422 theo canonical SSoT _HTTP_FOR_CODE
        #   [ErrorCode.VALIDATION]=422 (utils/response.py:61, 'input không hợp lệ field-level') — KHÁC
        #   VALIDATION_ERROR→400 (parse error :62). DRIFT 400-vs-422 ĐÃ ĐÓNG. Atomic blast-radius=1 endpoint:
        #   default ServiceError.__init__ GIỮ 400 (errors.py:36) — xem test_other_validation_endpoint_stays_400.
        self.assertEqual(
            res.get("http_status"), 422,
            "reason<5 → VALIDATION http_status @source = 422 (validation() helper errors.py:62, canonical "
            "_HTTP_FOR_CODE[VALIDATION]=422 utils/response.py:61). RECONCILED vs spec §0.1.3/ADR-MOBILE-014.",
        )

    def test_other_validation_endpoint_stays_400(self):
        """R37b ATOMIC-FENCE: chứng minh fix reschedule (validation()=422) CHỈ chạm nhánh reason<5 —
        KHÔNG đổi default ServiceError.__init__ (errors.py:36). create_adhoc_work_order thiếu trường bắt
        buộc raise ServiceError(ErrorCode.VALIDATION, ...) TRỰC TIẾP (services/imm08.py:830) → giữ default
        http_status=400. Blast-radius = 1 endpoint (reschedule), các VALIDATION raise trực tiếp khác GIỮ 400."""
        from assetcore.services.imm08 import create_adhoc_work_order as svc_create_adhoc
        from assetcore.services.shared import ErrorCode
        with self.assertRaises(ServiceError) as cm:
            svc_create_adhoc({"asset_ref": self.asset.name})  # thiếu pm_schedule + due_date
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)
        self.assertEqual(
            cm.exception.http_status, 400,
            "create_adhoc VALIDATION raise trực tiếp PHẢI GIỮ default 400 (ServiceError.__init__ errors.py:36 "
            "KHÔNG đổi) — chứng minh fix reschedule→422 blast-radius=1 endpoint.",
        )

    def test_reschedule_missing_wo_404_envelope(self):
        """R37 PM-RESCHEDULE BE-unit: WO∄ (reason hợp lệ ≥5 để qua guard) → Error envelope success=False
        code NOT_FOUND http_status 404 (nthrow IMM08_WO_NOT_FOUND @services/imm08.py:813). 404 đến qua
        HTTP-200 + Error body — khớp slot {200,401,403} contract."""
        from assetcore.api.imm08 import reschedule_pm as api_reschedule_pm
        from assetcore.services.shared import ErrorCode
        res = api_reschedule_pm(
            name="PM-WO-DOES-NOT-EXIST",
            new_date=str(add_days(nowdate(), 7)),
            reason="Thiết bị đang dùng cho ca mổ",
        )
        self.assertFalse(res.get("success"), f"WO∄ PHẢI Error envelope, got {res}.")
        self.assertEqual(res.get("code"), ErrorCode.NOT_FOUND)
        self.assertEqual(res.get("http_status"), 404)
        self.assertEqual(res.get("message_code"), "IMM08-WO-NOT-FOUND")

    def test_already_submitted_has_message_code(self):
        from assetcore.services.imm08 import submit_result
        wo_name = self._make_wo()
        results = [
            {"idx": r.idx, "result": "Pass"}
            for r in frappe.get_doc("PM Work Order", wo_name).checklist_results or []
        ]
        submit_result(wo_name, checklist_results=results, overall_result="Pass",
                      pm_sticker_attached=1, duration_minutes=30)
        frappe.db.commit()
        with self.assertRaises(ServiceError) as cm:
            submit_result(wo_name, checklist_results=results, overall_result="Pass",
                          pm_sticker_attached=1, duration_minutes=30)
        self.assertEqual(cm.exception.message_code, "IMM08-ALREADY-SUBMITTED")

    # ── API envelope hydration ─────────────────────────────────────────────────

    def test_api_envelope_hydrates_notification_fields(self):
        from assetcore.api.imm08 import get_pm_work_order
        resp = get_pm_work_order("PM-WO-DOES-NOT-EXIST")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["message_code"], "IMM08-WO-NOT-FOUND")
        self.assertEqual(resp["severity"], "warning")
        self.assertTrue(resp["title"])
        self.assertTrue(resp["action_hint"])


# ─── BR-08-11: PM Overdue predicate SoT + cron wiring ─────────────────────────

class TestPMOverdueSchedulerWiring(FrappeTestCase):
    """Root-cause guard (BR-08-11): cron check_pm_overdue PHẢI đăng ký trong
    hooks.py::scheduler_events['daily'] — nếu unwire, status Overdue không bao
    giờ được set ở prod (KPI 'Quá hạn' luôn 0)."""

    def test_check_pm_overdue_registered_in_scheduler(self):
        from assetcore import hooks
        self.assertIn(
            "assetcore.tasks.check_pm_overdue",
            hooks.scheduler_events["daily"],
            "check_pm_overdue phải nằm trong scheduler_events['daily'] "
            "(root-cause: cron không đăng ký → Overdue không bao giờ set)",
        )


class TestIsPmOverduePredicate(FrappeTestCase):
    """BR-08-11: predicate SoT is_pm_overdue dùng chung cho cron / counter / drill."""

    def test_is_pm_overdue_boundary(self):
        from assetcore.services.imm08 import is_pm_overdue
        today = nowdate()
        # due_date < today → quá hạn
        self.assertTrue(is_pm_overdue("Open", add_days(today, -1), today))
        # due_date == today → CHƯA quá hạn (boundary chốt)
        self.assertFalse(is_pm_overdue("Open", today, today))
        # due_date > today → chưa quá hạn
        self.assertFalse(is_pm_overdue("Open", add_days(today, 1), today))
        # status terminal (Completed) → không quá hạn dù due_date < today
        self.assertFalse(is_pm_overdue("Completed", add_days(today, -5), today))
        # due_date None → không quá hạn
        self.assertFalse(is_pm_overdue("Open", None, today))

    def test_is_pm_overdue_pending_busy(self):
        """Regression: cron cũ chỉ bắt Open/In Progress, bỏ sót Pending–Device Busy."""
        from assetcore.services.imm08 import is_pm_overdue
        today = nowdate()
        self.assertTrue(
            is_pm_overdue("Pending–Device Busy", add_days(today, -1), today),
            "WO hoãn (Pending–Device Busy) due_date<today PHẢI là quá hạn",
        )

    def test_is_pm_overdue_excludes_terminal_states(self):
        from assetcore.services.imm08 import is_pm_overdue
        today = nowdate()
        past = add_days(today, -5)
        for st in ("Completed", "Cancelled", "Halted–Major Failure", "Overdue"):
            self.assertFalse(
                is_pm_overdue(st, past, today),
                f"status '{st}' không được coi là nguồn quá hạn",
            )


class TestPMOverdueCronAndCounter(FrappeTestCase):
    """BR-08-11: cron flip → counter == drill-down, idempotent, loại terminal."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-ovd")
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")
        # Sạch WO trước mỗi test để counter đo đúng phạm vi asset fixture.
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_overdue_wo(self, status="Open", days_back=3):
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), -days_back),
            "assigned_to": "Administrator",
        })
        if status != "Open":
            frappe.db.set_value("PM Work Order", res["name"], "status", status)
        frappe.db.commit()
        return res["name"]

    def _count_for_asset(self, status):
        from assetcore.repositories.pm_repo import PMWorkOrderRepo
        return PMWorkOrderRepo.count({"asset_ref": self.asset.name, "status": status})

    def test_cron_sets_overdue_then_counter_matches(self):
        from assetcore.tasks import check_pm_overdue
        from assetcore.services.imm08 import count_overdue_pm
        wo_name = self._make_overdue_wo(status="Open", days_back=3)
        before = count_overdue_pm()
        check_pm_overdue()
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("PM Work Order", wo_name, "status"), "Overdue"
        )
        self.assertEqual(count_overdue_pm(), before + 1)
        self.assertEqual(self._count_for_asset("Overdue"), 1)

    def test_kpi_equals_drilldown(self):
        """KPI count_overdue_pm == số rows mà drill-down ?overdue=1 trả về."""
        from assetcore.tasks import check_pm_overdue
        from assetcore.services.imm08 import count_overdue_pm, list_work_orders, _normalize_filters
        self._make_overdue_wo(status="Open", days_back=2)
        self._make_overdue_wo(status="Pending–Device Busy", days_back=5)
        check_pm_overdue()
        frappe.db.commit()
        kpi = count_overdue_pm()
        # _normalize_filters({'overdue':'1'}) → status=Overdue (cùng nguồn)
        self.assertEqual(_normalize_filters({"overdue": "1"}), {"status": "Overdue"})
        listed = list_work_orders({"overdue": "1"}, page=1, page_size=500)
        self.assertEqual(kpi, listed["pagination"]["total"],
                         "KPI count phải == drill-down ?overdue=1 list total")

    def test_cron_catches_pending_busy(self):
        """Regression: WO Pending–Device Busy quá hạn PHẢI bị flip Overdue."""
        from assetcore.tasks import check_pm_overdue
        wo_name = self._make_overdue_wo(status="Pending–Device Busy", days_back=4)
        check_pm_overdue()
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("PM Work Order", wo_name, "status"), "Overdue"
        )

    def test_cron_boundary_due_today_not_flipped(self):
        """due_date == today CHƯA quá hạn → KHÔNG flip."""
        from assetcore.tasks import check_pm_overdue
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": nowdate(),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        check_pm_overdue()
        frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("PM Work Order", res["name"], "status"), "Open"
        )

    def test_cron_idempotent_and_excludes_terminal(self):
        """Chạy 2 lần không tăng count; Completed/Cancelled past-due KHÔNG bị flip."""
        from assetcore.tasks import check_pm_overdue
        from assetcore.services.imm08 import count_overdue_pm
        self._make_overdue_wo(status="Open", days_back=3)
        # WO terminal quá hạn — không được flip.
        comp = self._make_overdue_wo(status="Completed", days_back=10)
        canc = self._make_overdue_wo(status="Cancelled", days_back=10)
        check_pm_overdue()
        frappe.db.commit()
        first = count_overdue_pm()
        check_pm_overdue()
        frappe.db.commit()
        second = count_overdue_pm()
        self.assertEqual(first, second, "cron phải idempotent — count không tăng lần 2")
        self.assertEqual(
            frappe.db.get_value("PM Work Order", comp, "status"), "Completed"
        )
        self.assertEqual(
            frappe.db.get_value("PM Work Order", canc, "status"), "Cancelled"
        )


class TestPMDueSoonFilterSoT(FrappeTestCase):
    """BR-08-12: SoT cửa-sổ due-soon `due_soon_filter` — pure builder + boundary.

    Card == drill: KPI `pm_due_7d` và drill `?due_before=today+7` dùng CHUNG
    `due_soon_filter`. WO quá hạn (`due_date < today`) NẰM NGOÀI due-soon →
    thuộc tập overdue (BR-08-11) → hai tập disjoint.
    """

    def test_tc_08_due_01_filter_shape_and_window(self):
        """TC-08-DUE-01: due_soon_filter sinh due_date BETWEEN [ref, window_end]
        (cận dưới = ref_date, cận trên = window_end) + status NOT IN [Completed,
        Cancelled]. Hằng PM_DUE_SOON_WINDOW_DAYS == 7."""
        from assetcore.services.imm08 import (
            PM_DUE_SOON_WINDOW_DAYS,
            PMStatus,
            due_soon_filter,
        )
        self.assertEqual(PM_DUE_SOON_WINDOW_DAYS, 7)
        today = nowdate()
        win = add_days(today, 7)
        f = due_soon_filter(win, ref_date=today)
        self.assertEqual(f["due_date"], ["between", [today, win]],
                         "cận dưới PHẢI = ref_date (today), KHÔNG còn '<=' window_end")
        self.assertEqual(f["status"], ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]])

    def test_tc_08_due_01_default_ref_is_today(self):
        """ref_date mặc định = nowdate() (cận dưới = hôm nay)."""
        from assetcore.services.imm08 import due_soon_filter
        win = add_days(nowdate(), 7)
        f = due_soon_filter(win)
        self.assertEqual(f["due_date"][1][0], nowdate(),
                         "ref_date mặc định PHẢI = today (cận dưới)")
        self.assertEqual(f["due_date"][1][1], win)


class TestPMDueSoonBoundaryAndDisjoint(FrappeTestCase):
    """TC-08-DUE-01 boundary (membership thật trên DB) + TC-08-DUE-02/03."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-ds")
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_wo(self, *, days_offset: int, status: str = "Open"):
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), days_offset),
            "assigned_to": "Administrator",
        })
        if status != "Open":
            frappe.db.set_value("PM Work Order", res["name"], "status", status)
        frappe.db.commit()
        return res["name"]

    def _due_soon_count(self):
        from assetcore.services.imm08 import due_soon_filter
        win = add_days(nowdate(), 7)
        f = dict(due_soon_filter(win))
        f["asset_ref"] = self.asset.name
        return frappe.db.count("PM Work Order", f)

    def test_tc_08_due_01_boundary_membership(self):
        """TC-08-DUE-01: due_date==today → IN; today+7 → IN; today+8 → OUT;
        today-1 → OUT (overdue, not due-soon); Completed/Cancelled trong cửa sổ → OUT."""
        self._make_wo(days_offset=0)            # today → IN
        self._make_wo(days_offset=7)            # today+7 → IN
        self._make_wo(days_offset=8)            # today+8 → OUT
        self._make_wo(days_offset=-1)           # today-1 → OUT (overdue)
        self._make_wo(days_offset=3, status="Completed")   # OUT
        self._make_wo(days_offset=3, status="Cancelled")   # OUT
        self.assertEqual(self._due_soon_count(), 2,
                         "chỉ today + today+7 nằm trong cửa sổ due-soon")

    def test_tc_08_due_02_normalize_filters_window(self):
        """TC-08-DUE-02: _normalize_filters(due_before=today+7) sinh due_date
        == ['between', [today, today+7]] (cận dưới today) + status NOT IN
        [Completed, Cancelled] — KHÔNG còn ['<=', today+7]."""
        from assetcore.services.imm08 import _normalize_filters, PMStatus
        today = nowdate()
        win = add_days(today, 7)
        out = _normalize_filters({"due_before": win})
        self.assertEqual(out["due_date"], ["between", [today, win]],
                         "_normalize_filters PHẢI sinh cửa sổ có cận dưới today")
        self.assertEqual(out["status"], ["not in", [PMStatus.COMPLETED, PMStatus.CANCELLED]])
        self.assertNotIn("<=", str(out["due_date"]),
                         "KHÔNG còn dịch '<=' window_end (cận-dưới-thiếu)")

    def test_tc_08_due_03_disjoint_overdue_vs_due_soon(self):
        """TC-08-DUE-03: 1 WO quá hạn (due_date=today-3, Overdue) + 1 WO due-soon
        (due_date=today+2, Open) → due_soon đếm 1; count_overdue_pm đếm 1 (chỉ asset);
        2 tập KHÔNG giao nhau."""
        from assetcore.services.imm08 import count_overdue_pm
        self._make_wo(days_offset=-3, status="Overdue")   # overdue
        self._make_wo(days_offset=2)                       # due-soon
        self.assertEqual(self._due_soon_count(), 1,
                         "due-soon chỉ chứa WO due_date>=today (loại WO quá hạn)")
        self.assertEqual(count_overdue_pm("Administrator"), 1,
                         "overdue counter chỉ chứa WO status==Overdue (disjoint)")


# ─── BR-08-03: SoT compute_next_pm_date (anchor=completion, default=90) ───────

class TestComputeNextPmDateSoT(FrappeTestCase):
    """BR-08-03 — TC-PM-NEXT-01: helper SoT `compute_next_pm_date` (pure).

    INVARIANT: anchor LUÔN `completion_date` (KHÔNG nowdate); interval hiệu lực =
    `pm_interval_days` nếu > 0 else `PM_DEFAULT_INTERVAL_DAYS = 90`. Mọi write-site
    gọi CHUNG helper → bằng nhau byte-for-byte.
    """

    def test_const_default_interval_is_90(self):
        from assetcore.services.imm08 import PM_DEFAULT_INTERVAL_DAYS
        self.assertEqual(PM_DEFAULT_INTERVAL_DAYS, 90)

    def test_explicit_interval(self):
        from assetcore.services.imm08 import compute_next_pm_date
        # 2026-03-01 + 90 = 2026-05-30
        self.assertEqual(compute_next_pm_date("2026-03-01", 90), "2026-05-30")

    def test_zero_interval_falls_back_to_90(self):
        from assetcore.services.imm08 import compute_next_pm_date
        self.assertEqual(
            compute_next_pm_date("2026-03-01", 0),
            str(add_days(getdate("2026-03-01"), 90)),
            "interval 0 PHẢI fallback PM_DEFAULT_INTERVAL_DAYS (+90), KHÔNG +0",
        )

    def test_none_interval_falls_back_to_90(self):
        from assetcore.services.imm08 import compute_next_pm_date
        self.assertEqual(
            compute_next_pm_date("2026-03-01", None),
            str(add_days(getdate("2026-03-01"), 90)),
            "interval None PHẢI fallback +90",
        )

    def test_negative_interval_falls_back_to_90(self):
        from assetcore.services.imm08 import compute_next_pm_date
        self.assertEqual(
            compute_next_pm_date("2026-03-01", -5),
            str(add_days(getdate("2026-03-01"), 90)),
            "interval âm KHÔNG hợp lệ → fallback +90 (interval > 0 mới dùng)",
        )

    def test_boundary_end_of_month(self):
        from assetcore.services.imm08 import compute_next_pm_date
        # 2026-01-31 + 30 ngày → đúng add_days (rollover sang tháng 3)
        self.assertEqual(
            compute_next_pm_date("2026-01-31", 30),
            str(add_days(getdate("2026-01-31"), 30)),
        )

    def test_returns_str(self):
        from assetcore.services.imm08 import compute_next_pm_date
        out = compute_next_pm_date("2026-03-01", 90)
        self.assertIsInstance(out, str)


class TestNextPmDateParityAndAnchor(FrappeTestCase):
    """BR-08-03 — TC-PM-NEXT-02/03/04/05: anchor=completion, default=90, parity.

    Sau 1 submit WO: submit_result.next_pm_date == PM Schedule.next_due_date
    (persist) == AC Asset.next_pm_date == PM Task Log.next_pm_date (byte-for-byte,
    1 SoT). + grep-guard không-inline-literal.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Next")
        cls.asset = _make_asset("-next")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        for log in frappe.get_all(
            "PM Task Log", filters={"asset_ref": cls.asset.name}, pluck="name"
        ):
            frappe.delete_doc("PM Task Log", log, force=True, ignore_permissions=True)
        for sch in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, pluck="name"
        ):
            frappe.delete_doc("PM Schedule", sch, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM08Next"}, "name"
        )
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        # Reset PM Schedule sạch cho mỗi test (interval khác nhau giữa các test).
        for sch in frappe.get_all(
            "PM Schedule", filters={"asset_ref": self.asset.name}, pluck="name"
        ):
            for wo in frappe.get_all(
                "PM Work Order", filters={"pm_schedule": sch}, pluck="name"
            ):
                d = frappe.get_doc("PM Work Order", wo)
                if d.docstatus == 1:
                    d.cancel()
                frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
            frappe.delete_doc("PM Schedule", sch, force=True, ignore_permissions=True)

    def _make_schedule_interval(self, interval):
        """Tạo PM Schedule với pm_interval_days tùy ý (kể cả 0/None để test default).

        `create_schedule` yêu cầu pm_interval_days truthy (required field) → tạo
        bằng 90 rồi ép thẳng pm_interval_days=0/None ở DB để mô phỏng dữ liệu
        rỗng/0 (test default-90 SoT).
        """
        sched = create_schedule({
            "asset_ref": self.asset.name,
            "pm_type": "Quarterly",
            "pm_interval_days": interval if interval else 90,
            "checklist_template": self.template_name,
            "status": "Active",
        })
        if not interval:  # 0 hoặc None — ép raw để bypass required validation
            frappe.db.set_value(
                "PM Schedule", sched["name"], "pm_interval_days", interval,
                update_modified=False,
            )
            frappe.db.commit()
        return sched["name"]

    def _make_wo(self, sched_name):
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": sched_name,
            "due_date": add_days(nowdate(), -10),  # due trong quá khứ
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        return res["name"]

    def _rated(self, wo_name):
        wo = frappe.get_doc("PM Work Order", wo_name)
        return [
            {"idx": r.idx, "result": "Pass", "measured_value": None, "notes": ""}
            for r in (wo.checklist_results or [])
        ]

    def _submit(self, wo_name):
        from assetcore.services.imm08 import submit_result
        res = submit_result(
            wo_name, checklist_results=self._rated(wo_name),
            overall_result="Pass", pm_sticker_attached=1, duration_minutes=30,
        )
        frappe.db.commit()
        return res

    # ── TC-PM-NEXT-04: cross-path parity (1 SoT, byte-for-byte) ──────────────
    def test_next_pm_cross_path_parity(self):
        """4 nơi (API return / PM Schedule / AC Asset / PM Task Log) bằng nhau."""
        sched_name = self._make_schedule_interval(90)
        wo_name = self._make_wo(sched_name)
        res = self._submit(wo_name)

        wo = frappe.get_doc("PM Work Order", wo_name)
        from assetcore.services.imm08 import compute_next_pm_date
        expected = compute_next_pm_date(wo.completion_date, 90)

        sched_next = str(frappe.db.get_value("PM Schedule", sched_name, "next_due_date"))
        asset_next = str(frappe.db.get_value("AC Asset", self.asset.name, "next_pm_date"))
        log_next = str(frappe.db.get_value(
            "PM Task Log", {"pm_work_order": wo_name}, "next_pm_date"
        ))

        self.assertEqual(res["next_pm_date"], expected)
        self.assertEqual(sched_next, expected, "PM Schedule.next_due_date phải == SoT")
        self.assertEqual(asset_next, expected, "AC Asset.next_pm_date phải == SoT")
        self.assertEqual(log_next, expected, "PM Task Log.next_pm_date phải == SoT")
        # 4-way equality byte-for-byte
        self.assertEqual(
            {res["next_pm_date"], sched_next, asset_next, log_next}, {expected},
            "Cả 4 write-site PHẢI bằng nhau byte-for-byte (1 SoT)",
        )

    # ── TC-PM-NEXT-02: anchor == completion_date, KHÔNG nowdate ──────────────
    def test_submit_anchor_is_completion_not_independent_nowdate(self):
        """submit_result.next_pm_date neo theo wo.completion_date (mốc hoàn thành
        WO mà handle_work_order_submit đã set), KHÔNG gọi nowdate() độc lập.

        Bằng chứng: giá trị return == compute_next_pm_date(wo.completion_date, …)
        == PM Schedule.next_due_date (đã persist từ chính completion_date đó).
        Nếu submit_result còn add_days(nowdate(), …) mà PM Schedule dùng
        completion_date → hai nguồn lệch khi completion != nowdate.
        """
        sched_name = self._make_schedule_interval(90)
        wo_name = self._make_wo(sched_name)
        res = self._submit(wo_name)

        wo = frappe.get_doc("PM Work Order", wo_name)
        from assetcore.services.imm08 import compute_next_pm_date
        self.assertEqual(
            res["next_pm_date"],
            compute_next_pm_date(wo.completion_date, 90),
            "next_pm_date PHẢI neo theo completion_date (anchor SoT)",
        )
        # parity với DB-persisted (nguồn dùng completion_date) — chống anchor-drift
        sched_next = str(frappe.db.get_value("PM Schedule", sched_name, "next_due_date"))
        self.assertEqual(
            res["next_pm_date"], sched_next,
            "API return PHẢI == PM Schedule.next_due_date (cùng anchor completion_date)",
        )

    def test_backdated_completion_anchor_writers(self):
        """TC-PM-NEXT-02 backdate: với completion_date lùi 5 ngày, các writer
        (update_pm_schedule_after_completion + AC Asset + PM Task Log) PHẢI tính
        từ completion_date, KHÔNG từ nowdate(). Test trực tiếp writer layer vì
        controller on_submit ép completion=nowdate ở luồng submit_result.
        """
        from assetcore.services.imm08 import (
            compute_next_pm_date,
            update_pm_schedule_after_completion,
        )
        backdated = add_days(nowdate(), -5)
        sched_name = self._make_schedule_interval(90)

        update_pm_schedule_after_completion(sched_name, backdated)
        sched_next = str(frappe.db.get_value("PM Schedule", sched_name, "next_due_date"))
        self.assertEqual(
            sched_next, compute_next_pm_date(backdated, 90),
            "next_due_date PHẢI = completion_date(-5) + 90, KHÔNG today + 90",
        )
        self.assertNotEqual(
            sched_next, add_days(nowdate(), 90),
            "anchor PHẢI là completion_date backdated, KHÔNG nowdate (RED nếu còn nowdate)",
        )

    # ── TC-PM-NEXT-03: default interval 90 đồng nhất khi rỗng/0 ───────────────
    def test_default_interval_uniform_when_zero(self):
        """pm_interval_days = 0 → next_pm_date == completion + 90 ở CẢ 3 nơi
        (PM Schedule / AC Asset / API). KHÔNG +0 ⇒ asset KHÔNG bị PM-overdue giả.
        """
        sched_name = self._make_schedule_interval(0)
        # xác nhận schedule thật sự rỗng/0 (không bị default ngầm)
        self.assertIn(
            frappe.db.get_value("PM Schedule", sched_name, "pm_interval_days"),
            (0, None),
        )
        wo_name = self._make_wo(sched_name)
        res = self._submit(wo_name)

        wo = frappe.get_doc("PM Work Order", wo_name)
        expected_plus90 = str(add_days(getdate(wo.completion_date), 90))

        asset_next = str(frappe.db.get_value("AC Asset", self.asset.name, "next_pm_date"))
        sched_next = str(frappe.db.get_value("PM Schedule", sched_name, "next_due_date"))

        self.assertEqual(res["next_pm_date"], expected_plus90,
                         "interval 0 → API +90 (KHÔNG +0 = completion_date)")
        self.assertEqual(asset_next, expected_plus90,
                         "interval 0 → AC Asset.next_pm_date +90 (KHÔNG còn `or 0`)")
        self.assertEqual(sched_next, expected_plus90)
        self.assertNotEqual(
            asset_next, str(getdate(wo.completion_date)),
            "asset.next_pm_date KHÔNG được == completion_date (PM-overdue giả)",
        )
        # 3 nơi bằng nhau
        self.assertEqual({res["next_pm_date"], asset_next, sched_next}, {expected_plus90})

    # ── TC-PM-NEXT-05: no-inline-literal guard (grep thân hàm) ────────────────
    def test_no_inline_nowdate_anchor_or_literal_90(self):
        """Grep thân submit_result + handle_work_order_submit +
        update_pm_schedule_after_completion: 0 nowdate-anchored next-date,
        0 literal 90 NGOÀI hằng PM_DEFAULT_INTERVAL_DAYS / compute_next_pm_date.
        """
        import inspect
        import re
        from assetcore.services import imm08

        for fn in (imm08.submit_result, imm08.handle_work_order_submit,
                   imm08.update_pm_schedule_after_completion):
            src = inspect.getsource(fn)
            # KHÔNG add_days(nowdate(), …) — anchor nowdate bị cấm cho ngày PM kế tiếp
            self.assertNotRegex(
                src, r"add_days\(\s*_?nowdate\(\)",
                f"{fn.__name__}: còn add_days(nowdate(), …) — anchor SAI",
            )
            # KHÔNG add_days(...completion_date..., interval) inline (phải qua SoT)
            self.assertNotRegex(
                src, r"_?add_days\([^)]*completion_date[^)]*,\s*\w*interval",
                f"{fn.__name__}: còn inline add_days(completion_date, interval) — phải qua compute_next_pm_date",
            )
            # KHÔNG literal `or 0` / `or 90` quanh interval ở call-site
            self.assertNotRegex(
                src, r"pm_interval_days\s+or\s+\d+",
                f"{fn.__name__}: còn `pm_interval_days or N` — default phải nằm trong compute_next_pm_date",
            )
            self.assertNotIn(
                "or 90", src,
                f"{fn.__name__}: còn `or 90` — literal default phải qua PM_DEFAULT_INTERVAL_DAYS",
            )

        # compute_next_pm_date là nơi DUY NHẤT chứa default 90 (qua hằng).
        src_helper = inspect.getsource(imm08.compute_next_pm_date)
        self.assertIn("PM_DEFAULT_INTERVAL_DAYS", src_helper)


class TestPMDashboardKpiScope(FrappeTestCase):
    """INV-PM-KPI-1..6 — KPI dashboard PM phải ĐỒNG NHẤT PHẠM VI.

    Tách 'Quá hạn trong tháng' (overdue_in_month — subset của total_scheduled,
    đối-soát được) khỏi 'Quá hạn (toàn hệ thống)' (overdue — count_overdue_pm()
    global, RC-10, khớp launcher + drill ?overdue=1).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Kpi")
        cls.asset = _make_asset("-kpi")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]
        # Tháng "xem" cố định trong quá khứ để KHÔNG đụng WO của môi trường/round
        # khác (tách phạm vi). Mọi WO seed đều due trong tháng này.
        cls.view_year = 2025
        cls.view_month = 3   # 2025-03
        cls.prev_year = 2025
        cls.prev_month = 2   # 2025-02 (tháng trước, dùng cho counter-example)

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        for sch in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, pluck="name"
        ):
            frappe.delete_doc("PM Schedule", sch, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM08Kpi"}, "name"
        )
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        # Sạch WO trước mỗi test để stats đo đúng phạm vi seed. KHÔNG commit ở đây
        # (cùng connection vẫn thấy xoá) — tránh lock contention/deadlock khi nhiều
        # test class commit song song trong cùng module run.
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)

    def _seed_wo(self, *, due_date, status, is_late=0, completion_date=None):
        """Tạo 1 PM Work Order với due_date/status/is_late/completion_date cụ thể.

        create_adhoc_work_order set status='Open'; ép thẳng các field còn lại ở DB
        để mô phỏng đầy đủ trạng thái (Completed on-time/late, Overdue) mà
        get_dashboard_stats đọc trực tiếp từ repo (KHÔNG qua controller).

        KHÔNG commit per-seed: get_dashboard_stats/count_overdue_pm chạy cùng
        connection → thấy write chưa commit; bỏ commit để giảm deadlock + giữ
        isolation cho test-runner rollback (LL — fixture commit gây leak/deadlock).
        """
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": due_date,
            "assigned_to": "Administrator",
        })
        updates = {"status": status, "is_late": is_late}
        if completion_date is not None:
            updates["completion_date"] = completion_date
        for f, v in updates.items():
            frappe.db.set_value("PM Work Order", res["name"], f, v, update_modified=False)
        return res["name"]

    def _stats(self):
        from assetcore.services.imm08 import get_dashboard_stats
        return get_dashboard_stats(year=self.view_year, month=self.view_month)["kpis"]

    # ── TC-PM-KPI-01: INV-PM-KPI-1 đối-soát strip tháng ──────────────────────
    def test_month_strip_reconciles(self):
        """3 WO trong tháng (1 on-time, 1 late, 1 Overdue): total==3,
        completed_on_time==1, overdue_in_month==1, pending_in_month==0; và
        total >= completed_on_time + overdue_in_month + pending_in_month.
        """
        self._seed_wo(due_date="2025-03-05", status="Completed", is_late=0,
                      completion_date="2025-03-04")
        self._seed_wo(due_date="2025-03-10", status="Completed", is_late=1,
                      completion_date="2025-03-20")
        self._seed_wo(due_date="2025-03-15", status="Overdue", is_late=0)

        k = self._stats()
        self.assertEqual(k["total_scheduled"], 3)
        self.assertEqual(k["completed_on_time"], 1)
        self.assertEqual(k["overdue_in_month"], 1)
        self.assertEqual(k["pending_in_month"], 0)
        self.assertGreaterEqual(
            k["total_scheduled"],
            k["completed_on_time"] + k["overdue_in_month"] + k["pending_in_month"],
            "strip tháng PHẢI hòa hợp số học (INV-PM-KPI-1)",
        )

    # ── TC-PM-KPI-02: BUG CHÍNH (RED-prove) — overdue global vs in-month ──────
    def test_counterexample_overdue_global_vs_in_month(self):
        """5 WO Overdue due THÁNG TRƯỚC (2025-02) + 0 WO due tháng xem (2025-03):
        overdue(global) tăng +5, overdue_in_month==0, total_scheduled==0.
        Nếu FE đọc 'overdue' (global) như số tháng → 5>0=total → mâu thuẫn không
        đối-soát. GREEN khi tách overdue_in_month==0.

        overdue (global) assert theo DELTA (count_overdue_pm KHÔNG lọc tháng →
        có thể chứa Overdue WO thật/của test khác) — in-month assert tuyệt đối vì
        cửa-sổ 2025-03 biệt lập, không test/khách-thể nào khác đụng.
        """
        from assetcore.services.imm08 import count_overdue_pm
        before_global = count_overdue_pm()
        for i in range(5):
            self._seed_wo(due_date=f"2025-02-{10 + i:02d}", status="Overdue")

        k = self._stats()
        self.assertEqual(k["total_scheduled"], 0,
                         "0 WO due trong tháng xem (2025-03)")
        self.assertEqual(k["overdue_in_month"], 0,
                         "0 Overdue ∧ due ∈ tháng xem → overdue_in_month==0")
        self.assertEqual(k["overdue"] - before_global, 5,
                         "overdue (global) phải +5 WO Overdue mới (toàn thời gian)")
        self.assertEqual(k["overdue"], count_overdue_pm(),
                         "kpis.overdue == count_overdue_pm() global (RC-10)")
        # KHÔNG bao giờ overdue_in_month > total_scheduled (INV-PM-KPI-1)
        self.assertLessEqual(k["overdue_in_month"], k["total_scheduled"])

    # ── TC-PM-KPI-03: INV-PM-KPI-3 compliance None khi total==0 ───────────────
    def test_compliance_none_when_no_scheduled(self):
        """total_scheduled==0 → compliance_rate_pct == None (KHÔNG 0.0/100.0
        gây hiểu nhầm 'không tuân thủ')."""
        # 5 Overdue tháng trước, 0 WO tháng xem → total tháng = 0
        for i in range(5):
            self._seed_wo(due_date=f"2025-02-{10 + i:02d}", status="Overdue")
        k = self._stats()
        self.assertEqual(k["total_scheduled"], 0)
        self.assertIsNone(k["compliance_rate_pct"],
                          "total==0 → compliance None, KHÔNG 0.0")

    def test_compliance_value_when_has_data(self):
        """Có WO trong tháng → compliance là số (KHÔNG None). 2 on-time / 4 tổng
        → 50.0."""
        self._seed_wo(due_date="2025-03-02", status="Completed", is_late=0,
                      completion_date="2025-03-01")
        self._seed_wo(due_date="2025-03-03", status="Completed", is_late=0,
                      completion_date="2025-03-02")
        self._seed_wo(due_date="2025-03-04", status="Completed", is_late=1,
                      completion_date="2025-03-12")
        self._seed_wo(due_date="2025-03-05", status="Overdue")
        k = self._stats()
        self.assertEqual(k["total_scheduled"], 4)
        self.assertEqual(k["compliance_rate_pct"], 50.0)

    # ── TC-PM-KPI-04: INV-PM-KPI-2 no-regression RC-10 (global overdue) ───────
    def test_overdue_global_equals_counter_and_drill(self):
        """field 'overdue' == count_overdue_pm() global, khớp drill
        _normalize_filters(overdue=1) list total; đổi tháng xem KHÔNG đổi value.
        """
        from assetcore.services.imm08 import (
            count_overdue_pm, list_work_orders, _normalize_filters, get_dashboard_stats,
        )
        # Seed Overdue rải nhiều tháng — global đếm hết, không phân biệt tháng.
        self._seed_wo(due_date="2025-02-05", status="Overdue")
        self._seed_wo(due_date="2025-03-05", status="Overdue")
        self._seed_wo(due_date="2025-01-05", status="Overdue")

        counter = count_overdue_pm()
        self.assertEqual(_normalize_filters({"overdue": "1"}), {"status": "Overdue"})
        listed = list_work_orders({"overdue": "1"}, page=1, page_size=500)

        k_mar = get_dashboard_stats(year=2025, month=3)["kpis"]
        k_feb = get_dashboard_stats(year=2025, month=2)["kpis"]
        self.assertEqual(k_mar["overdue"], counter,
                         "'overdue' (global) == count_overdue_pm()")
        self.assertEqual(k_mar["overdue"], listed["pagination"]["total"],
                         "'overdue' == drill ?overdue=1 list total (RC-10)")
        self.assertEqual(k_mar["overdue"], k_feb["overdue"],
                         "đổi tháng xem KHÔNG đổi 'overdue' (global invariant)")
        # in-month thì PHẢI đổi theo tháng (mỗi tháng 1 Overdue ở seed này)
        self.assertEqual(k_mar["overdue_in_month"], 1)
        self.assertEqual(k_feb["overdue_in_month"], 1)

    # ── TC-PM-KPI-05: no-regression trend + avg_days_late ─────────────────────
    def test_trend_and_avg_days_late_invariant(self):
        """trend_6months có đủ 6 phần tử + key bất biến; avg_days_late tính từ
        completed-late (4 ngày). overdue_in_month KHÔNG nhiễu các field cũ.
        """
        from assetcore.services.imm08 import get_dashboard_stats
        self._seed_wo(due_date="2025-03-10", status="Completed", is_late=1,
                      completion_date="2025-03-14")  # trễ 4 ngày
        res = get_dashboard_stats(year=2025, month=3)
        k = res["kpis"]
        self.assertEqual(k["avg_days_late"], 4.0)
        self.assertEqual(len(res["trend_6months"]), 6)
        for t in res["trend_6months"]:
            self.assertEqual(set(t.keys()), {"month", "total", "on_time", "rate"})
        # Shape kpis có đủ cả field cũ + 2 field mới (no breaking).
        self.assertTrue(
            {"compliance_rate_pct", "total_scheduled", "completed_on_time",
             "overdue", "overdue_in_month", "pending_in_month", "avg_days_late"}
            <= set(k.keys())
        )

    def test_pending_in_month_counts_unfinished(self):
        """pending_in_month = WO trong tháng chưa Completed & chưa Overdue
        (Open/In Progress). 1 Open + 1 Completed-ontime → pending==1, total==2."""
        self._seed_wo(due_date="2025-03-20", status="Open")
        self._seed_wo(due_date="2025-03-02", status="Completed", is_late=0,
                      completion_date="2025-03-01")
        k = self._stats()
        self.assertEqual(k["total_scheduled"], 2)
        self.assertEqual(k["pending_in_month"], 1)
        self.assertEqual(k["completed_on_time"], 1)
        self.assertEqual(k["overdue_in_month"], 0)
        self.assertEqual(
            k["total_scheduled"],
            k["completed_on_time"] + k["overdue_in_month"] + k["pending_in_month"],
        )


class TestPmComplianceExcludeCancelled(FrappeTestCase):
    """BR-08-14 / INV-PM-KPI-6 — WO 'Cancelled' (hủy chủ động, hết nghĩa vụ) bị
    LOẠI khỏi MẪU tuân thủ (total_scheduled) + bucket pending/overdue/completed.

    ROOT CAUSE (cũ): get_dashboard_stats đặt total = len(wos) (MỌI status) →
    Cancelled (a) phình mẫu compliance kéo tụt giả; (b) rơi vào pending phantom.
    Fix: population THÁNG = scheduled = [w for w in wos if status != Cancelled].
    'Halted–Major Failure' GIỮ counted (kết cục non-compliant thật) — chỉ
    Cancelled bị loại.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08Canc")
        cls.asset = _make_asset("-canc")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        sched = _make_schedule(cls.asset.name, cls.template_name)
        cls.schedule_name = sched["name"]
        cls.view_year = 2025
        cls.view_month = 3   # 2025-03 (biệt lập, quá khứ)

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)
        for sch in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, pluck="name"
        ):
            frappe.delete_doc("PM Schedule", sch, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True
        )
        purge_asset(cls.asset.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM08Canc"}, "name"
        )
        if cat_name:
            frappe.delete_doc("AC Asset Category", cat_name, force=True, ignore_permissions=True)

    def setUp(self):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, fields=["name"]
        ):
            d = frappe.get_doc("PM Work Order", wo.name)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("PM Work Order", wo.name, force=True, ignore_permissions=True)

    def _seed_wo(self, *, due_date, status, is_late=0, completion_date=None):
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": due_date,
            "assigned_to": "Administrator",
        })
        updates = {"status": status, "is_late": is_late}
        if completion_date is not None:
            updates["completion_date"] = completion_date
        for f, v in updates.items():
            frappe.db.set_value("PM Work Order", res["name"], f, v, update_modified=False)
        return res["name"]

    def _stats(self):
        from assetcore.services.imm08 import get_dashboard_stats
        return get_dashboard_stats(year=self.view_year, month=self.view_month)["kpis"]

    # ── TC-08-CANC-01 (RED-prove) — Cancelled loại khỏi mẫu compliance ───────
    def test_tc_08_canc_01_cancelled_excluded_from_compliance_sample(self):
        """Tháng {1 Completed on-time, 1 Completed late, 1 Overdue, 1 Cancelled}:
        total_scheduled==3 (KHÔNG 4); compliance = round(1/3*100,1)=33.3
        (cũ SAI: 1/4=25.0). RED trên code cũ → GREEN sau fix.
        """
        self._seed_wo(due_date="2025-03-05", status="Completed", is_late=0,
                      completion_date="2025-03-04")
        self._seed_wo(due_date="2025-03-10", status="Completed", is_late=1,
                      completion_date="2025-03-20")
        self._seed_wo(due_date="2025-03-15", status="Overdue", is_late=0)
        self._seed_wo(due_date="2025-03-18", status="Cancelled", is_late=0)

        k = self._stats()
        self.assertEqual(k["total_scheduled"], 3,
                         "Cancelled KHÔNG vào total_scheduled (cũ: 4)")
        self.assertEqual(k["compliance_rate_pct"], 33.3,
                         "mẫu loại Cancelled → 1/3=33.3 (cũ SAI 1/4=25.0)")
        self.assertEqual(k["completed_on_time"], 1)
        self.assertEqual(k["overdue_in_month"], 1)

    # ── TC-08-CANC-02 — Cancelled KHÔNG vào pending_in_month ─────────────────
    def test_tc_08_canc_02_cancelled_not_in_pending(self):
        """Cùng fixture: pending_in_month==0 (cũ: 1 phantom 'chưa xong')."""
        self._seed_wo(due_date="2025-03-05", status="Completed", is_late=0,
                      completion_date="2025-03-04")
        self._seed_wo(due_date="2025-03-10", status="Completed", is_late=1,
                      completion_date="2025-03-20")
        self._seed_wo(due_date="2025-03-15", status="Overdue", is_late=0)
        self._seed_wo(due_date="2025-03-18", status="Cancelled", is_late=0)

        k = self._stats()
        self.assertEqual(k["pending_in_month"], 0,
                         "Cancelled KHÔNG rơi vào pending (cũ: 1 phantom)")

    # ── TC-08-CANC-03 — tháng chỉ-Cancelled → total==0, compliance None ──────
    def test_tc_08_canc_03_cancelled_only_month(self):
        """2 Cancelled, 0 khác → total_scheduled==0 ⇒ compliance_rate_pct is None
        ('—' ở FE, KHÔNG 0.0 hiểu nhầm 'không tuân thủ'); pending==0; overdue==0.
        """
        self._seed_wo(due_date="2025-03-05", status="Cancelled", is_late=0)
        self._seed_wo(due_date="2025-03-12", status="Cancelled", is_late=0)

        k = self._stats()
        self.assertEqual(k["total_scheduled"], 0)
        self.assertIsNone(k["compliance_rate_pct"],
                          "total==0 → None (KHÔNG 0.0)")
        self.assertEqual(k["pending_in_month"], 0)
        self.assertEqual(k["overdue_in_month"], 0)

    # ── TC-08-CANC-04 (no-regression đối chứng) — tháng KHÔNG Cancelled ──────
    def test_tc_08_canc_04_no_cancelled_invariant(self):
        """{1 on-time, 1 late, 1 Overdue} (KHÔNG Cancelled): total_scheduled==3,
        compliance==33.3, pending==0, overdue_in_month==1 — Cancelled-free path
        BẤT BIẾN như trước fix.
        """
        self._seed_wo(due_date="2025-03-05", status="Completed", is_late=0,
                      completion_date="2025-03-04")
        self._seed_wo(due_date="2025-03-10", status="Completed", is_late=1,
                      completion_date="2025-03-20")
        self._seed_wo(due_date="2025-03-15", status="Overdue", is_late=0)

        k = self._stats()
        self.assertEqual(k["total_scheduled"], 3)
        self.assertEqual(k["compliance_rate_pct"], 33.3)
        self.assertEqual(k["pending_in_month"], 0)
        self.assertEqual(k["overdue_in_month"], 1)

    # ── TC-08-CANC-05 (đối-soát số học INV-PM-KPI-1) ─────────────────────────
    def test_tc_08_canc_05_arithmetic_invariant_with_cancelled(self):
        """Mọi fixture (kể cả có Cancelled): total_scheduled >= completed_on_time
        + overdue_in_month + pending_in_month, và KHÔNG Cancelled nào lọt bucket.
        """
        self._seed_wo(due_date="2025-03-05", status="Completed", is_late=0,
                      completion_date="2025-03-04")
        self._seed_wo(due_date="2025-03-08", status="Open")           # pending
        self._seed_wo(due_date="2025-03-15", status="Overdue", is_late=0)
        self._seed_wo(due_date="2025-03-18", status="Cancelled", is_late=0)
        self._seed_wo(due_date="2025-03-22", status="Cancelled", is_late=0)

        k = self._stats()
        self.assertEqual(k["total_scheduled"], 3,
                         "2 Cancelled bị loại khỏi mẫu (5 WO → 3 scheduled)")
        self.assertGreaterEqual(
            k["total_scheduled"],
            k["completed_on_time"] + k["overdue_in_month"] + k["pending_in_month"],
            "INV-PM-KPI-1 hòa hợp số học vẫn đúng sau khi đổi mẫu",
        )
        # Đối-soát đầy đủ: 1 on-time + 1 overdue + 1 pending == 3 (KHÔNG Cancelled)
        self.assertEqual(
            k["completed_on_time"] + k["overdue_in_month"] + k["pending_in_month"],
            3,
        )

    # ── TC-08-CANC-06 (trend SoT) — trend dùng CÙNG predicate loại-Cancelled ──
    def test_tc_08_canc_06_trend_excludes_cancelled(self):
        """Tháng-trend (2025-01) có Cancelled → trend rate dùng mẫu loại-Cancelled
        (t = số WO không-Cancelled). Seed 2025-01: {1 Completed on-time, 1
        Cancelled} → t==1, on_time==1, rate==100.0 (KHÔNG 1/2=50.0 nếu kéo bởi
        Cancelled). CÙNG SoT predicate với tile compliance tháng hiện tại.
        """
        from assetcore.services.imm08 import get_dashboard_stats
        # 2025-01 nằm trong cửa-sổ trend 6 tháng của view 2025-03.
        self._seed_wo(due_date="2025-01-10", status="Completed", is_late=0,
                      completion_date="2025-01-09")
        self._seed_wo(due_date="2025-01-20", status="Cancelled", is_late=0)

        res = get_dashboard_stats(year=2025, month=3)
        jan = next(t for t in res["trend_6months"] if t["month"] == "2025-01")
        self.assertEqual(jan["total"], 1,
                         "trend total loại Cancelled (t = không-Cancelled)")
        self.assertEqual(jan["on_time"], 1)
        self.assertEqual(jan["rate"], 100.0,
                         "rate = c_on/t = 1/1 = 100.0 (KHÔNG 1/2=50.0)")

    def test_tc_08_canc_06b_trend_cancelled_only_rate_zero(self):
        """Tháng-trend chỉ-Cancelled → t==0 → rate==0.0 (giữ default cũ, KHÔNG
        ZeroDivision). Đối chứng: trend không phình bởi Cancelled."""
        from assetcore.services.imm08 import get_dashboard_stats
        self._seed_wo(due_date="2025-02-10", status="Cancelled", is_late=0)
        self._seed_wo(due_date="2025-02-14", status="Cancelled", is_late=0)

        res = get_dashboard_stats(year=2025, month=3)
        feb = next(t for t in res["trend_6months"] if t["month"] == "2025-02")
        self.assertEqual(feb["total"], 0, "2 Cancelled → t==0 (loại hết)")
        self.assertEqual(feb["rate"], 0.0, "t==0 → rate 0.0 (KHÔNG ZeroDivision)")

    # ── TC-08-CANC-07 (Halted GIỮ counted — ranh giới) ──────────────────────
    def test_tc_08_canc_07_halted_stays_counted(self):
        """WO 'Halted–Major Failure' trong tháng VẪN trong total_scheduled (KHÔNG
        bị loại như Cancelled) → khẳng định CHỈ Cancelled bị loại; Halted là kết
        cục PM non-compliant thật. {1 Completed on-time, 1 Halted, 1 Cancelled}:
        total_scheduled==2 (Halted IN, Cancelled OUT).
        """
        self._seed_wo(due_date="2025-03-05", status="Completed", is_late=0,
                      completion_date="2025-03-04")
        self._seed_wo(due_date="2025-03-10", status="Halted–Major Failure",
                      is_late=0)
        self._seed_wo(due_date="2025-03-15", status="Cancelled", is_late=0)

        k = self._stats()
        self.assertEqual(k["total_scheduled"], 2,
                         "Halted GIỮ counted, chỉ Cancelled bị loại (3 WO → 2)")
        # Halted không Completed/Overdue → rơi vào pending (chưa-xong-non-compliant)
        self.assertEqual(k["completed_on_time"], 1)
        self.assertEqual(k["pending_in_month"], 1,
                         "Halted nằm trong pending bucket (KHÔNG Cancelled)")
        # compliance = 1 on-time / 2 scheduled = 50.0
        self.assertEqual(k["compliance_rate_pct"], 50.0)


# ─── BR-08-14: attach_pm_checklist_photo — bằng chứng ảnh/mục checklist PM (NĐ98) ──
# Mobile CR-14/G6. Đính ảnh cho MỘT mục checklist → File private (attached_to 'PM Work
# Order'/WO, is_private=1) + đúng 1 Asset Lifecycle Event 'pm_checklist_photo_attached'
# + set row.photo=file_url (read-back parity get_work_order). Mọi nhánh reject TRƯỚC
# File.insert (NOT_FOUND/FORBIDDEN/VALIDATION) → 0 File. Đối xứng attach_incident_photo
# (imm12) — KHÁC module/doctype. max ảnh/mục = 1 (row.photo Attach ĐƠN, count==nguồn).


def _jpg_bytes() -> bytes:
    """Bytes JPEG THẬT (PIL). Frappe File.before_insert strip EXIF ⇒ PIL phải nhận
    diện được ảnh (fake magic-byte → UnidentifiedImageError)."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (30, 120, 200)).save(buf, format="JPEG")
    return buf.getvalue()


def _truncated_jpg_bytes() -> bytes:
    """Ảnh JPEG THẬT bị CẮT CỤT thân (magic header hợp lệ, dữ liệu scan đứt) — mô
    phỏng KTV chụp hiện trường wifi/4G chập chờn. PIL.open nhận diện JPEG nhưng
    .save() ném OSError('Truncated File Read'). Filename .jpg ⇒ strip_exif chạy."""
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (30, 120, 200)).save(buf, format="JPEG")
    full = buf.getvalue()
    return full[: len(full) // 2]


def _garbage_jpg_bytes() -> bytes:
    """Magic-byte JPEG hợp lệ nhưng thân RÁC → PIL.UnidentifiedImageError."""
    return b"\xff\xd8\xff" + b"\x00" * 64


class TestPMChecklistPhotoAttach(FrappeTestCase):
    """BR-08-14 (mobile CR-14/G6): đính ảnh bằng chứng theo TỪNG mục checklist PM.

    - success → đúng 1 File private (attached_to 'PM Work Order'/WO, is_private=1) +
      set row.photo=file_url (read-back get_work_order) + đúng 1 lifecycle
      'pm_checklist_photo_attached' (actor=session.user, asset của WO, hard-req).
    - permission assignee OR pm.write: outsider (Auditor read-only, không assignee)
      → FORBIDDEN, 0 File; assignee dù thiếu write vẫn đính được.
    - validation: idx-không-tồn-tại / thiếu-file / content-type≠ảnh / size>cap / ảnh
      thứ 2 cùng mục → VALIDATION fields.file, 0 File (reject KHÔNG tạo File).
    - rollback hard-req: emit event throw → File.insert rollback (no orphan).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # Category/template/asset DEDICATED (_TestCatIMM08Photo) — KHÔNG shared
        # _TestCatIMM08. R-9: fixture KHÔNG pollute shared state; nếu dùng shared cat,
        # setUpClass commit PMCT-_TestCatIMM08-Quarterly → hỏng test_create_template_
        # succeeds (chạy sau, _make_template thấy đã tồn tại → thiếu items_count).
        cls.cat = _ensure_cat("_TestCatIMM08Photo")
        cls.asset = cls._make_asset_in_cat("-photo", cls.cat)
        tpl = _make_template(cls.cat)
        cls.template_name = tpl["name"]
        sched = _make_schedule(cls.asset.name, tpl["name"])
        cls.schedule_name = sched["name"]
        # assignee: Auditor (read-only, KHÔNG pm.write) → được set assigned_to ⇒ đính
        # qua NHÁNH assignee. outsider: Auditor (read-only) KHÔNG assignee → FORBIDDEN.
        cls.assignee = cls._ensure_user("_test_pm_photo_assignee@assetcore.test",
                                        ["AssetCore Auditor"])
        cls.outsider = cls._ensure_user("_test_pm_photo_outsider@assetcore.test",
                                        ["AssetCore Auditor"])
        cls._wos: list[str] = []

    @staticmethod
    def _make_asset_in_cat(suffix: str, cat: str) -> object:
        import time
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        sn = f"SN-08P-{suffix.lstrip('-')}-{int(time.time()) % 100000}"
        try:
            return frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": f"_Test Asset IMM08{suffix}",
                "asset_category": cat,
                "manufacturer_sn": sn,
                "lifecycle_status": "Active",
                "is_pm_required": 1,
                "pm_interval_days": 90,
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in cls._wos:
            try:
                for f in frappe.get_all(
                    "File", filters={"attached_to_doctype": "PM Work Order",
                                     "attached_to_name": wo}, pluck="name"):
                    frappe.delete_doc("File", f, force=True, ignore_permissions=True)
            except Exception:
                pass
            try:
                frappe.delete_doc("PM Work Order", wo, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        try:
            frappe.delete_doc("PM Schedule", cls.schedule_name, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        purge_asset(cls.asset.name)
        try:
            frappe.delete_doc("PM Checklist Template", cls.template_name, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        try:
            frappe.delete_doc("AC Asset Category", cls.cat, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        for u in (cls.assignee, cls.outsider):
            try:
                frappe.delete_doc("User", u, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email: str, roles: list[str]) -> str:
        if not frappe.db.exists("User", email):
            doc = frappe.get_doc({
                "doctype": "User", "email": email, "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        else:
            doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        return email

    def setUp(self):
        frappe.set_user("Administrator")

    def _new_wo(self, assigned_to: str = "Administrator") -> str:
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": assigned_to,
        })
        frappe.db.commit()
        self._wos.append(res["name"])
        # checklist template có 2 mục ⇒ checklist_item_idx 1..2 tồn tại
        self.assertGreaterEqual(res["checklist_items_count"], 1,
                                "WO fixture PHẢI có ≥1 mục checklist")
        return res["name"]

    def _file_count(self, wo: str) -> int:
        return frappe.db.count("File", {
            "attached_to_doctype": "PM Work Order",
            "attached_to_name": wo, "is_private": 1})

    def _row_photo(self, wo: str, idx: int):
        from assetcore.services.imm08 import get_work_order
        for r in get_work_order(wo)["checklist_results"]:
            if int(r["checklist_item_idx"]) == int(idx):
                return r["photo"]
        return None

    # ── TC-PM-PHOTO-01 Happy + read-back parity ─────────────────────────────────
    def test_happy_attach_creates_private_file_and_readback_parity(self):
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo()
        res = attach_pm_checklist_photo(wo, 1, filedata=_jpg_bytes(),
                                        filename="pm_item1.jpg", content_type="image/jpeg")
        self.assertTrue(res.get("file_url"), "phải trả file_url != ''")
        self.assertEqual(res.get("file_name"), "pm_item1.jpg")
        self.assertEqual(res.get("checklist_item_idx"), 1)
        files = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "PM Work Order", "attached_to_name": wo},
            fields=["name", "is_private", "attached_to_doctype", "attached_to_name"])
        self.assertEqual(len(files), 1, "đúng 1 File được tạo")
        self.assertEqual(files[0]["is_private"], 1, "File PHẢI private (NĐ98)")
        self.assertEqual(files[0]["attached_to_doctype"], "PM Work Order")
        self.assertEqual(files[0]["attached_to_name"], wo)
        # read-back parity: get_work_order.checklist_results[idx].photo == file_url
        self.assertEqual(self._row_photo(wo, 1), res["file_url"],
                         "row.photo == file_url vừa trả (read-back parity)")

    # ── TC-PM-PHOTO-02 Lifecycle: đúng 1 event ──────────────────────────────────
    def test_success_emits_exactly_one_lifecycle_event(self):
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo()
        attach_pm_checklist_photo(wo, 2, filedata=_jpg_bytes(),
                                  filename="pm_item2.png", content_type="image/png")
        evts = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"event_type": "pm_checklist_photo_attached", "root_record": wo},
            fields=["name", "actor", "asset", "root_doctype"])
        self.assertEqual(len(evts), 1, "đúng 1 lifecycle event/lần success")
        self.assertEqual(evts[0]["actor"], "Administrator", "actor = session.user")
        self.assertEqual(evts[0]["asset"], self.asset.name, "asset của WO")
        self.assertEqual(evts[0]["root_doctype"], "PM Work Order")

    # ── TC-PM-PHOTO-03 Rollback hard-req: event throw → no orphan File ───────────
    def test_rollback_on_event_failure_no_orphan_file(self):
        from assetcore.services import imm00 as svc00
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo()
        before = self._file_count(wo)
        orig = svc00.create_lifecycle_event

        def _boom(**kw):
            raise RuntimeError("boom-lifecycle-event")

        svc00.create_lifecycle_event = _boom
        try:
            with self.assertRaises(Exception):
                attach_pm_checklist_photo(wo, 1, filedata=_jpg_bytes(),
                                          filename="rb.jpg", content_type="image/jpeg")
        finally:
            svc00.create_lifecycle_event = orig
        frappe.db.rollback()
        self.assertEqual(self._file_count(wo), before,
                         "event throw → File.insert rollback (KHÔNG orphan)")
        self.assertIsNone(self._row_photo(wo, 1),
                          "row.photo KHÔNG bị set khi event throw (rollback)")

    # ── TC-PM-PHOTO-04 Reject non-image → VALIDATION, no File ───────────────────
    def test_reject_non_image_content_type_validation_no_file(self):
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo()
        with self.assertRaises(ServiceError) as ctx:
            attach_pm_checklist_photo(wo, 1, filedata=b"%PDF-1.4 fake",
                                      filename="doc.pdf", content_type="application/pdf")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields, "VALIDATION phải có fields.file")
        self.assertEqual(self._file_count(wo), 0, "nhánh VALIDATION KHÔNG tạo File")

    # ── TC-PM-PHOTO-05 Reject oversize → VALIDATION, no File ────────────────────
    def test_reject_oversize_photo_validation_no_file(self):
        from assetcore.services.imm08 import (attach_pm_checklist_photo,
                                              MAX_PM_CHECKLIST_PHOTO_BYTES)
        wo = self._new_wo()
        big = b"\x00" * (MAX_PM_CHECKLIST_PHOTO_BYTES + 1)
        with self.assertRaises(ServiceError) as ctx:
            attach_pm_checklist_photo(wo, 1, filedata=big, filename="big.jpg",
                                      content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields)
        self.assertEqual(self._file_count(wo), 0)

    # ── TC-PM-PHOTO-06 Reject idx không tồn tại → VALIDATION, no File ────────────
    def test_reject_nonexistent_checklist_idx_validation_no_file(self):
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo()
        with self.assertRaises(ServiceError) as ctx:
            attach_pm_checklist_photo(wo, 999, filedata=_jpg_bytes(),
                                      filename="x.jpg", content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertEqual(self._file_count(wo), 0, "idx sai → reject TRƯỚC File.insert")

    # ── TC-PM-PHOTO-07 Reject WO không tồn tại → NOT_FOUND, no File ─────────────
    def test_reject_nonexistent_wo_not_found(self):
        from assetcore.services.imm08 import attach_pm_checklist_photo
        with self.assertRaises(ServiceError) as ctx:
            attach_pm_checklist_photo("WO-PM-DOES-NOT-EXIST-0000", 1,
                                      filedata=_jpg_bytes(), filename="x.jpg",
                                      content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.NOT_FOUND)

    # ── TC-PM-PHOTO-08 ảnh HỎNG / ĐỨT TRUYỀN → VALIDATION, no 500, no orphan ─────
    def test_reject_corrupt_or_truncated_image_validation_no_file(self):
        """Finding B (ROOT CAUSE): content-type hợp lệ nhưng bytes KHÔNG giải mã (ảnh
        cắt-cụt/rác). File.before_insert → strip_exif → PIL ném UnidentifiedImageError
        / OSError('Truncated File Read'). PHẢI thành VALIDATION Decision-B (fields.file,
        thông điệp VN), KHÔNG 500, KHÔNG orphan File, KHÔNG set row.photo, KHÔNG
        lifecycle event."""
        from assetcore.services.imm08 import attach_pm_checklist_photo
        for label, data in (("truncated-OSError", _truncated_jpg_bytes()),
                            ("garbage-Unidentified", _garbage_jpg_bytes())):
            with self.subTest(kind=label):
                wo = self._new_wo()
                with self.assertRaises(ServiceError) as ctx:
                    attach_pm_checklist_photo(wo, 1, filedata=data,
                                              filename="pm_bad.jpg",
                                              content_type="image/jpeg")
                self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION,
                                 f"[{label}] ảnh hỏng → VALIDATION, KHÔNG 500")
                self.assertIn("file", ctx.exception.fields,
                              f"[{label}] Decision-B phải có fields.file")
                self.assertIn("bị lỗi hoặc không đọc được",
                              ctx.exception.fields["file"],
                              f"[{label}] thông điệp VN chụp/chọn lại")
                self.assertEqual(self._file_count(wo), 0,
                                 f"[{label}] KHÔNG tạo File orphan")
                self.assertIsNone(self._row_photo(wo, 1),
                                  f"[{label}] row.photo KHÔNG bị set khi ảnh hỏng")
                self.assertEqual(frappe.db.count("Asset Lifecycle Event", {
                    "event_type": "pm_checklist_photo_attached", "root_record": wo}), 0,
                    f"[{label}] KHÔNG sinh lifecycle event khi ảnh hỏng")

    # ── TC-PM-PHOTO-08 Permission: outsider FORBIDDEN; assignee/pm.write → 200 ───
    def test_outsider_not_assignee_no_write_forbidden_no_file(self):
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo(assigned_to=self.assignee)  # assigned_to != outsider
        frappe.set_user(self.outsider)
        try:
            with self.assertRaises(ServiceError) as ctx:
                attach_pm_checklist_photo(wo, 1, filedata=_jpg_bytes(),
                                          filename="x.jpg", content_type="image/jpeg")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(ctx.exception.code, ErrorCode.FORBIDDEN)
        self.assertEqual(self._file_count(wo), 0, "nhánh FORBIDDEN KHÔNG tạo File")

    def test_assignee_without_write_can_attach(self):
        """BR-08-14: KTV được giao luôn đính được ảnh phiếu của mình dù thiếu write."""
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo(assigned_to=self.assignee)
        frappe.set_user(self.assignee)
        try:
            res = attach_pm_checklist_photo(wo, 1, filedata=_jpg_bytes(),
                                            filename="a.jpg", content_type="image/jpeg")
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(res.get("file_url"))
        self.assertEqual(self._file_count(wo), 1)

    # ── TC-PM-PHOTO-09 Max-count: ảnh thứ 2 cùng mục → VALIDATION, count==nguồn ──
    def test_reject_second_photo_same_item_max_count(self):
        from assetcore.services.imm08 import (attach_pm_checklist_photo,
                                              MAX_PM_CHECKLIST_PHOTOS)
        wo = self._new_wo()
        for _ in range(MAX_PM_CHECKLIST_PHOTOS):
            attach_pm_checklist_photo(wo, 1, filedata=_jpg_bytes(),
                                      filename="m.jpg", content_type="image/jpeg")
        files_after_max = self._file_count(wo)
        with self.assertRaises(ServiceError) as ctx:
            attach_pm_checklist_photo(wo, 1, filedata=_jpg_bytes(),
                                      filename="over.jpg", content_type="image/jpeg")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields)
        self.assertEqual(self._file_count(wo), files_after_max,
                         "ảnh vượt max bị chặn → File count giữ nguyên (no drift)")
        # count==nguồn-liệt-kê: row.photo (nguồn hiển thị) == đúng số ảnh max
        self.assertIsNotNone(self._row_photo(wo, 1),
                             "row.photo giữ đúng ảnh đã đính (count==nguồn)")

    def test_max_count_is_per_item_not_shared(self):
        """Mỗi mục checklist độc lập: đính mục 1 KHÔNG chặn mục 2 (per-item).

        (file_url có thể trùng giữa 2 mục do Frappe dedup NỘI DUNG ảnh giống nhau —
        KHÔNG assert file_url khác; điểm mấu chốt = mục 2 KHÔNG bị max của mục 1 chặn
        + read-back row.photo đúng cho từng mục.)"""
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo()
        r1 = attach_pm_checklist_photo(wo, 1, filedata=_jpg_bytes(),
                                       filename="i1.jpg", content_type="image/jpeg")
        r2 = attach_pm_checklist_photo(wo, 2, filedata=_jpg_bytes(),
                                       filename="i2.jpg", content_type="image/jpeg")
        self.assertTrue(r1.get("file_url"))
        self.assertTrue(r2.get("file_url"), "mục 2 đính được (KHÔNG bị max mục 1 chặn)")
        self.assertEqual(self._row_photo(wo, 1), r1["file_url"])
        self.assertEqual(self._row_photo(wo, 2), r2["file_url"])

    # ── TC-PM-PHOTO-10 No-file → VALIDATION (reject TRƯỚC File.insert) ───────────
    def test_reject_missing_file_validation(self):
        from assetcore.services.imm08 import attach_pm_checklist_photo
        wo = self._new_wo()
        with self.assertRaises(ServiceError) as ctx:
            attach_pm_checklist_photo(wo, 1, filedata=None, filename="",
                                      content_type="")
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("file", ctx.exception.fields)
        self.assertEqual(self._file_count(wo), 0)

    # ── API tier — Decision-B envelope + multipart parity ───────────────────────
    def _fake_request(self, filedata: bytes, filename: str, content_type: str,
                      idx: str = "1"):
        import io

        from werkzeug.datastructures import FileStorage
        fs = FileStorage(stream=io.BytesIO(filedata), filename=filename,
                         content_type=content_type)

        class _Req:
            files = {"file": fs}
            host = None  # File.get_url() đọc request.host — None → fallback site conf

        return _Req()

    def test_api_attach_returns_decision_b_ok(self):
        from assetcore.api.imm08 import attach_pm_checklist_photo as api_attach
        wo = self._new_wo()
        orig = getattr(frappe.local, "request", None)
        frappe.local.request = self._fake_request(_jpg_bytes(), "api.jpg", "image/jpeg")
        try:
            res = api_attach(work_order_name=wo, checklist_item_idx="1")
        finally:
            frappe.local.request = orig
        self.assertTrue(res.get("success"), f"phải success, nhận: {res}")
        self.assertIn("file_url", res["data"])
        self.assertEqual(res["data"]["file_name"], "api.jpg")
        self.assertEqual(res["data"]["checklist_item_idx"], 1)

    def test_api_attach_non_image_returns_validation_fields(self):
        from assetcore.api.imm08 import attach_pm_checklist_photo as api_attach
        wo = self._new_wo()
        orig = getattr(frappe.local, "request", None)
        frappe.local.request = self._fake_request(b"%PDF fake", "n.pdf", "application/pdf")
        try:
            res = api_attach(work_order_name=wo, checklist_item_idx="1")
        finally:
            frappe.local.request = orig
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("code"), ErrorCode.VALIDATION)
        self.assertIn("file", res.get("fields", {}))
        self.assertEqual(self._file_count(wo), 0)


# ─── BR-08-14-IDEMP: attach_pm_checklist_photo idempotency (CR-24 §4 photo-level) ──


class TestPMChecklistPhotoIdempotency(FrappeTestCase):
    """CR-24 §4 photo-level closure · mirror ADR-IMM12-10: idempotency `client_request_id`
    đóng cửa sổ re-drain outbox tạo File TRÙNG cho MỘT mục checklist PM.

    Re-drain PHA-2 re-POST cùng ảnh (response rớt mạng SAU khi server đã tạo File) → File
    TRÙNG + lifecycle `pm_checklist_photo_attached` TRÙNG (bẩn evidence-trail NĐ98). Dedupe
    theo composite scoped key `{wo}::{idx}::{key}` trên Custom Field `File.ac_client_request_id`
    (unique NULL-store):
      - replay cùng (wo, idx, key) → 1 File + 1 lifecycle; response#2 == #1 (byte-đối-byte),
        THẮNG max-count (pre-check TRƯỚC validation ladder — replay dù mục đã đủ MAX=1 ảnh).
      - empty/thiếu key → at-least-once CŨ (mỗi call 1 insert THẬT, field NULL; KHÔNG dedupe).
      - scope namespace record+mục: cùng key KHÁC idx / KHÁC wo → composite KHÁC → 2 File
        (KHÔNG collision chéo — chống nuốt ảnh mục/phiếu khác).

    LƯU Ý domain: max ảnh/mục = 1 (BR-08-14, row.photo Attach ĐƠN) ⇒ 2 ảnh KHÁC nhau CÙNG
    (wo, idx) là BẤT KHẢ (call thứ 2 bị max-count reject) — idx đưa vào scoped key CHÍNH để
    N ảnh của N mục/phiếu KHÔNG bị nuốt (test scope-by-idx + scope-by-wo dưới đây).

    Precondition: Custom Field `File.ac_client_request_id` (fixtures/file_custom_fields.json).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08PhotoIdemp")
        cls.asset = TestPMChecklistPhotoAttach._make_asset_in_cat("-photoidemp", cls.cat)
        tpl = _make_template(cls.cat)
        cls.template_name = tpl["name"]
        sched = _make_schedule(cls.asset.name, tpl["name"])
        cls.schedule_name = sched["name"]
        cls._wos: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in cls._wos:
            try:
                for f in frappe.get_all(
                    "File", filters={"attached_to_doctype": "PM Work Order",
                                     "attached_to_name": wo}, pluck="name"):
                    frappe.delete_doc("File", f, force=True, ignore_permissions=True)
            except Exception:
                pass
            try:
                frappe.delete_doc("PM Work Order", wo, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        try:
            frappe.delete_doc("PM Schedule", cls.schedule_name, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        purge_asset(cls.asset.name)
        try:
            frappe.delete_doc("PM Checklist Template", cls.template_name, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        try:
            frappe.delete_doc("AC Asset Category", cls.cat, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    _seq = 0

    def _new_wo(self) -> str:
        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        })
        frappe.db.commit()
        self._wos.append(res["name"])
        self.assertGreaterEqual(res["checklist_items_count"], 2,
                                "WO fixture PHẢI có ≥2 mục checklist (scope-by-idx test)")
        return res["name"]

    def _key(self, tag: str) -> str:
        import time
        return f"pmk-{tag}-{int(time.time() * 1000)}"

    @classmethod
    def _unique_jpg_bytes(cls) -> bytes:
        """JPEG THẬT KHÁC nhau mỗi call (đổi màu) — tránh Frappe reuse file_url khi trùng
        content_hash (2 File riêng nhưng URL chung → assert URL-khác false-fail)."""
        import io

        from PIL import Image
        cls._seq += 1
        buf = io.BytesIO()
        Image.new("RGB", (8, 8),
                  (cls._seq % 256, (cls._seq * 7) % 256, 40)).save(buf, format="JPEG")
        return buf.getvalue()

    def _attach(self, wo: str, idx: int, key: str = "", filename: str = "pm.jpg") -> dict:
        from assetcore.services.imm08 import attach_pm_checklist_photo
        return attach_pm_checklist_photo(
            wo, idx, filedata=self._unique_jpg_bytes(),
            filename=filename, content_type="image/jpeg", client_request_id=key)

    def _file_count(self, wo: str) -> int:
        return frappe.db.count("File", {
            "attached_to_doctype": "PM Work Order",
            "attached_to_name": wo, "is_private": 1})

    def _event_count(self, wo: str) -> int:
        return frappe.db.count("Asset Lifecycle Event", {
            "event_type": "pm_checklist_photo_attached", "root_record": wo})

    # ── replay same key → 1 File + 1 lifecycle + response byte-đối-byte (RED-first) ──
    def test_replay_same_key_single_file_event_same_response(self):
        wo = self._new_wo()
        key = self._key("replay")
        res1 = self._attach(wo, 1, key=key)
        res2 = self._attach(wo, 1, key=key)
        self.assertEqual(
            frappe.db.count("File", {"ac_client_request_id": f"{wo}::1::{key}"}), 1,
            "CÙNG (wo, idx, key) → CHỈ 1 ROW File mang scoped key")
        self.assertEqual(self._file_count(wo), 1, "replay KHÔNG được insert File thứ 2")
        self.assertEqual(self._event_count(wo), 1,
                         "replay KHÔNG được emit lifecycle lần 2 (NĐ98)")
        self.assertEqual(res2, res1,
                         "response replay PHẢI == lần 1 (file_url/file_name/idx byte-đối-byte)")
        self.assertEqual(set(res2.keys()), {"file_url", "file_name", "checklist_item_idx"},
                         f"shape EXACT 3-key KHÔNG đổi (OAS closed), nhận: {res2}")

    # ── empty key → 2 File riêng (at-least-once CŨ), NULL key — dùng 2 mục (max=1/mục) ──
    def test_empty_key_backward_compat_two_files_null_key(self):
        wo = self._new_wo()
        self._attach(wo, 1, key="", filename="nk1.jpg")
        self._attach(wo, 2, key="", filename="nk2.jpg")
        self.assertEqual(self._file_count(wo), 2,
                         "KHÔNG key → mỗi call = 1 File THẬT (hành vi cũ nguyên vẹn)")
        keys = frappe.get_all(
            "File", filters={"attached_to_doctype": "PM Work Order",
                             "attached_to_name": wo, "is_private": 1},
            pluck="ac_client_request_id")
        self.assertTrue(all(not k for k in keys),
                        f"File không-khoá PHẢI lưu NULL/empty, nhận: {keys}")

    # ── scope-by-idx: cùng key KHÁC mục → 2 File (idx ∈ scoped key, KHÔNG nuốt ảnh mục khác) ──
    def test_same_key_different_idx_two_files(self):
        wo = self._new_wo()
        key = self._key("byidx")
        r1 = self._attach(wo, 1, key=key, filename="i1.jpg")
        r2 = self._attach(wo, 2, key=key, filename="i2.jpg")
        self.assertNotEqual(r1["file_url"], r2["file_url"],
                            "cùng key KHÁC idx → 2 File riêng (scoped key {wo}::{idx}::{key} khác)")
        self.assertEqual(self._file_count(wo), 2, "2 mục KHÁC → đúng 2 File")
        self.assertEqual(self._event_count(wo), 2, "2 File thật → đúng 2 lifecycle")

    # ── scope-by-record: cùng key KHÁC WO → 2 File (KHÔNG collision chéo phiếu) ──
    def test_same_key_different_wo_no_cross_dedupe(self):
        wo_a = self._new_wo()
        wo_b = self._new_wo()
        key = self._key("bywo")
        res_a = self._attach(wo_a, 1, key=key, filename="a.jpg")
        res_b = self._attach(wo_b, 1, key=key, filename="b.jpg")
        self.assertNotEqual(res_a["file_url"], res_b["file_url"],
                            "cùng key KHÁC WO → 2 File riêng (composite khác)")
        self.assertEqual(self._file_count(wo_a), 1)
        self.assertEqual(self._file_count(wo_b), 1)
        self.assertEqual(self._event_count(wo_a), 1)
        self.assertEqual(self._event_count(wo_b), 1)


# ─── F8 "Nhắc việc" — get_due_pm_schedules (mobile CR-28b) ─────────────────────
class TestDuePmSchedules(FrappeTestCase):
    """ROOT-CAUSE GUARD — ``get_due_pm_schedules`` (mobile F8 "Nhắc việc") ĐỐI XỨNG
    ``get_due_calibrations`` (imm11) NHƯNG KHÁC NGUỒN: dùng ``PM Schedule.next_due_date``
    (KHÔNG AC Asset.next_calibration_date). CHỈ trả lịch ``status == 'Active'`` CÓ
    ``next_due_date`` set, ≤ ngưỡng; rows-key ``items`` + ``threshold_days`` (KHÔNG
    pagination); ``days_left`` signed server-derived.

    NULL-coerce guard (mirror imm11): filter ``[next_due_date, is, set]`` BẮT BUỘC —
    RED-prove bỏ nó ⇒ Frappe query-builder coerce NULL→'0001-01-01' ⇒ lịch chưa-có-
    ngày LỌT filter, sort ASC lên top, lấp kín limit → đẩy lịch quá-hạn thật khỏi list.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.template_name = _make_template(cls.cat)["name"]

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        for asset in self._assets:
            for s in frappe.get_all(
                "PM Schedule", filters={"asset_ref": asset}, pluck="name"
            ):
                for wo in frappe.get_all(
                    "PM Work Order", filters={"pm_schedule": s}, pluck="name"
                ):
                    frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
                frappe.delete_doc("PM Schedule", s, force=True, ignore_permissions=True)
            purge_asset(asset)
        frappe.db.commit()

    def _new_schedule(self, suffix: str, *, next_due_date, status: str = "Active",
                      pm_type: str = "Quarterly", last_pm_date=None) -> str:
        """Tạo asset + PM Schedule với next_due_date/status CHÍNH XÁC.

        before_save auto-điền next_due_date ⇒ dùng interval xa (3650) để né auto-WO
        window, RỒI ép next_due_date/status/last_pm_date qua db.set_value (bypass
        controller — mirror imm11 test set next_calibration_date trực tiếp). NULL =
        set_value(None) → lịch chưa-có-ngày (KHÔNG lọt filter is-set)."""
        asset = _make_asset(suffix)
        self._assets.append(asset.name)
        det = f"PMS-{asset.name}-{pm_type}"
        if frappe.db.exists("PM Schedule", det):
            frappe.delete_doc("PM Schedule", det, force=True, ignore_permissions=True)
        sched = frappe.get_doc({
            "doctype": "PM Schedule",
            "asset_ref": asset.name,
            "pm_type": pm_type,
            "pm_interval_days": 3650,
            "checklist_template": self.template_name,
            "status": "Active",
        }).insert(ignore_permissions=True)
        frappe.db.set_value("PM Schedule", sched.name, {
            "next_due_date": next_due_date,
            "last_pm_date": last_pm_date,
            "status": status,
        }, update_modified=False)
        frappe.db.commit()
        return sched.name

    def test_due_pm_01_soon_in_window_present_days_left_positive(self):
        """TC-DUE-PM-01: Active, next_due_date=today+5 → có trong items, days_left==5."""
        from assetcore.services.imm08 import get_due_pm_schedules
        name = self._new_schedule("-due-soon", next_due_date=add_days(nowdate(), 5))
        due = get_due_pm_schedules(days=30, limit=100)
        row = next((r for r in due["items"] if r["name"] == name), None)
        self.assertIsNotNone(row, "lịch Active due trong window PHẢI ∈ items")
        self.assertEqual(row["days_left"], 5, "days_left signed = date_diff(next_due_date, today)")

    def test_due_pm_02_overdue_present_days_left_negative_signed(self):
        """TC-DUE-PM-02: Active, next_due_date=today-3 (quá hạn) → items, days_left==-3."""
        from assetcore.services.imm08 import get_due_pm_schedules
        name = self._new_schedule("-overdue", next_due_date=add_days(nowdate(), -3))
        due = get_due_pm_schedules(days=30, limit=100)
        row = next((r for r in due["items"] if r["name"] == name), None)
        self.assertIsNotNone(row, "lịch quá hạn PHẢI ∈ items")
        self.assertEqual(row["days_left"], -3, "quá hạn ⇒ days_left ÂM (signed)")

    def test_due_pm_03_beyond_window_excluded(self):
        """TC-DUE-PM-03: Active, next_due_date=today+40 với days=30 → KHÔNG có."""
        from assetcore.services.imm08 import get_due_pm_schedules
        name = self._new_schedule("-far", next_due_date=add_days(nowdate(), 40))
        due = get_due_pm_schedules(days=30, limit=100)
        names = {r["name"] for r in due["items"]}
        self.assertNotIn(name, names, "ngoài due-window (40 > 30 ngày) ⇒ KHÔNG lọt")

    def test_due_pm_04_null_next_due_date_excluded(self):
        """TC-DUE-PM-04: next_due_date NULL → KHÔNG lọt (NULL-coerce guard).

        RED-prove: bỏ filter `is set` ⇒ NULL bị Frappe ép '0001-01-01' <= threshold
        ⇒ lịch chưa-có-ngày LỌT top."""
        from assetcore.services.imm08 import get_due_pm_schedules
        name = self._new_schedule("-null", next_due_date=None)
        self.assertIsNone(
            frappe.db.get_value("PM Schedule", name, "next_due_date"),
            "tiền đề: lịch chưa có next_due_date (NULL)",
        )
        due = get_due_pm_schedules(days=30, limit=100)
        names = {r["name"] for r in due["items"]}
        self.assertNotIn(name, names, "lịch chưa-có-ngày (NULL) KHÔNG phải 'đến hạn'")
        self.assertTrue(
            all(r.get("next_due_date") for r in due["items"]),
            "due-list KHÔNG chứa item next_due_date NULL (no phantom)",
        )

    def test_due_pm_05_paused_suspended_excluded_even_if_due(self):
        """TC-DUE-PM-05: status Paused và Suspended dù đến hạn → LOẠI (chỉ Active)."""
        from assetcore.services.imm08 import get_due_pm_schedules
        paused = self._new_schedule("-paused", next_due_date=add_days(nowdate(), 2),
                                    status="Paused")
        suspended = self._new_schedule("-susp", next_due_date=add_days(nowdate(), 2),
                                       status="Suspended")
        due = get_due_pm_schedules(days=30, limit=100)
        names = {r["name"] for r in due["items"]}
        self.assertNotIn(paused, names, "Paused KHÔNG lọt (chỉ Active)")
        self.assertNotIn(suspended, names, "Suspended KHÔNG lọt (chỉ Active)")

    def test_due_pm_06_limit_cut_and_order_asc_worst_first(self):
        """TC-DUE-PM-06: nhiều row đến hạn + limit=N → cắt đúng N, quá-hạn-nặng-nhất
        (next_due_date nhỏ nhất) lên đầu (order asc)."""
        from assetcore.services.imm08 import get_due_pm_schedules
        worst = self._new_schedule("-w-neg10", next_due_date=add_days(nowdate(), -10))
        mid = self._new_schedule("-w-neg2", next_due_date=add_days(nowdate(), -2))
        soon = self._new_schedule("-w-pos3", next_due_date=add_days(nowdate(), 3))
        mine = {worst, mid, soon}
        due = get_due_pm_schedules(days=30, limit=2)
        self.assertEqual(len(due["items"]), 2, "limit=2 ⇒ cắt đúng 2 row")
        # order asc: mọi cặp liền kề next_due_date không giảm.
        dates = [r["next_due_date"] for r in due["items"]]
        self.assertEqual(dates, sorted(dates), "order_by next_due_date asc")
        # với đủ rộng, quá-hạn-nặng-nhất (worst) đứng trước mid trước soon.
        full = get_due_pm_schedules(days=30, limit=100)
        ordered_mine = [r["name"] for r in full["items"] if r["name"] in mine]
        self.assertEqual(ordered_mine, [worst, mid, soon],
                         "asc: quá-hạn-nặng-nhất (next_due_date nhỏ nhất) lên đầu")

    def test_due_pm_07_shape_and_row_fields(self):
        """TC-DUE-PM-07: shape == {'items':[...],'threshold_days':30}; mỗi row đủ 11
        field gồm asset_name enriched + days_left + [CR-45] next_wo_ref/next_wo_status."""
        from assetcore.services.imm08 import get_due_pm_schedules
        name = self._new_schedule("-shape", next_due_date=add_days(nowdate(), 7))
        due = get_due_pm_schedules(days=30, limit=100)
        self.assertEqual(
            set(due.keys()), {"items", "threshold_days", "total", "truncated"},
            "shape ĐÚNG 4 key {items, threshold_days, total, truncated} (CR-46 "
            "additive; KHÔNG pagination)")
        self.assertEqual(due["threshold_days"], 30, "threshold_days echo param days")
        row = next((r for r in due["items"] if r["name"] == name), None)
        self.assertIsNotNone(row)
        expected_fields = {
            "name", "asset_ref", "asset_name", "pm_type", "status",
            "next_due_date", "last_pm_date", "responsible_technician", "days_left",
            "next_wo_ref", "next_wo_status",
        }
        self.assertEqual(set(row.keys()), expected_fields,
                         f"row PHẢI ĐÚNG 11 field (9 cũ + CR-45 next_wo_ref/next_wo_status): "
                         f"thừa={set(row.keys()) - expected_fields} "
                         f"thiếu={expected_fields - set(row.keys())}")
        self.assertEqual(row["asset_name"], "_Test Asset IMM08-shape",
                         "asset_name enriched từ AC Asset.asset_name")
        self.assertEqual(row["days_left"], 7, "days_left server-derived signed")

    def test_due_pm_schedules_total_and_truncated(self):
        """T7 (CR-46 hợp đồng TRUNG THỰC khi cắt): ``total`` = COUNT thật trên ĐÚNG
        filter-set TRƯỚC khi cắt; ``truncated`` = int 0/1 = (len(items) ≥ limit ∧
        total > limit). Seed 2 lịch due → limit=1 ⇒ 1 item, total==2, truncated==1;
        limit=100 ⇒ truncated==0, total==len(items); items/threshold_days GIỮ.

        Isolation: 2 lịch trên 2 asset RIÊNG với next_due_date lệch nhau; count DÙNG
        CÙNG filter (status=Active ∧ next_due_date is-set ∧ ≤ threshold) nên robust
        với data dev khác — assert theo QUAN HỆ (total == COUNT DB, ≥ 2) chứ không
        cứng ==2 khi site có lịch due khác."""
        from assetcore.services.imm08 import get_due_pm_schedules
        a = self._new_schedule("-t7-a", next_due_date=add_days(nowdate(), -2))
        b = self._new_schedule("-t7-b", next_due_date=add_days(nowdate(), 3))
        mine = {a, b}

        # limit=1 → cắt xuống 1 item nhưng total = COUNT thật (≥2), truncated=1.
        cut = get_due_pm_schedules(days=30, limit=1)
        self.assertEqual(len(cut["items"]), 1, "limit=1 ⇒ ĐÚNG 1 item")
        self.assertIsInstance(cut["total"], int)
        self.assertFalse(isinstance(cut["total"], bool), "total là int, KHÔNG bool")
        self.assertGreaterEqual(cut["total"], 2, "total ≥ 2 (≥ 2 lịch seed due)")
        self.assertEqual(cut["truncated"], 1, "len(items)≥limit ∧ total>limit ⇒ truncated=1")
        self.assertNotIsInstance(cut["truncated"], bool, "truncated int 0/1 (KHÔNG bool)")
        self.assertIn("items", cut)
        self.assertEqual(cut["threshold_days"], 30, "threshold_days GIỮ")

        # limit=100 → không cắt: truncated=0, total==len(items); 2 lịch seed đều hiện.
        full = get_due_pm_schedules(days=30, limit=100)
        self.assertEqual(full["truncated"], 0, "đủ chỗ ⇒ truncated=0")
        self.assertEqual(full["total"], len(full["items"]),
                         "không cắt ⇒ total == len(items)")
        got = {r["name"] for r in full["items"]}
        self.assertTrue(mine <= got, "cả 2 lịch seed due PHẢI hiện khi limit rộng")


class TestPMNextWoAndRescheduleGuard(FrappeTestCase):
    """CR-45 (mobile Spec 52 — F8 «Nhắc việc» → phiếu). Đóng luồng «Dời lịch PM»:

    (b) ``get_due_pm_schedules`` enrich ``next_wo_ref``/``next_wo_status`` (PK + status của
        phiếu PM Work Order MỞ gần hạn nhất của lịch, null nếu 0 phiếu mở) — 1-BATCH, no N+1.
    (c) ``allowed_transitions`` (get_work_order) cho Open/Overdue CHỨA 'Pending–Device Busy'
        (khớp hành vi ``reschedule`` ĐÃ CÓ → mobile render CTA «Dời lịch»).
    guard ``reschedule`` chặn phiếu terminal (Completed/Cancelled) → 422 VALIDATION, KHÔNG
        ghi đè ``due_date`` (vá lỗ ghi im lặng lên phiếu đã đóng).

    OPEN_STATUSES enrich = {Open, Overdue, In Progress, Pending–Device Busy}.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.template_name = _make_template(cls.cat)["name"]

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        for asset in self._assets:
            for s in frappe.get_all(
                "PM Schedule", filters={"asset_ref": asset}, pluck="name"
            ):
                for wo in frappe.get_all(
                    "PM Work Order", filters={"pm_schedule": s}, pluck="name"
                ):
                    frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
                frappe.delete_doc("PM Schedule", s, force=True, ignore_permissions=True)
            purge_asset(asset)
        frappe.db.commit()

    def _new_schedule(self, suffix: str, *, next_due_date) -> tuple[str, str]:
        """asset + PM Schedule Active với next_due_date ép chính xác (interval 3650 để
        né auto-WO window, mirror TestDuePmSchedules._new_schedule)."""
        asset = _make_asset(suffix)
        self._assets.append(asset.name)
        det = f"PMS-{asset.name}-Quarterly"
        if frappe.db.exists("PM Schedule", det):
            frappe.delete_doc("PM Schedule", det, force=True, ignore_permissions=True)
        sched = frappe.get_doc({
            "doctype": "PM Schedule",
            "asset_ref": asset.name,
            "pm_type": "Quarterly",
            "pm_interval_days": 3650,
            "checklist_template": self.template_name,
            "status": "Active",
        }).insert(ignore_permissions=True)
        frappe.db.set_value("PM Schedule", sched.name,
                            {"next_due_date": next_due_date}, update_modified=False)
        frappe.db.commit()
        return asset.name, sched.name

    def _make_wo(self, asset: str, sched: str, *, status: str, scheduled_date,
                 due_date=None) -> str:
        """Tạo phiếu Open (create_adhoc) rồi ép status+scheduled_date qua set_value
        (bypass validate() gate hoàn-thành cho status terminal — mirror _make_overdue_wo)."""
        res = create_adhoc_work_order({
            "asset_ref": asset,
            "pm_schedule": sched,
            "due_date": str(due_date or scheduled_date),
            "assigned_to": "Administrator",
        })
        name = res["name"]
        frappe.db.set_value("PM Work Order", name,
                            {"status": status, "scheduled_date": scheduled_date},
                            update_modified=False)
        frappe.db.commit()
        return name

    # ── AC1/AC2 — next_wo_ref/next_wo_status enrich ────────────────────────────

    def test_t1_next_wo_ref_overdue_happy(self):
        """T1 (AC1/AC2 happy): lịch có 1 phiếu Overdue → next_wo_ref==WO, status=='Overdue'."""
        from assetcore.services.imm08 import get_due_pm_schedules
        asset, sched = self._new_schedule("-nwo-t1", next_due_date=add_days(nowdate(), 5))
        wo = self._make_wo(asset, sched, status="Overdue",
                           scheduled_date=add_days(nowdate(), 3))
        due = get_due_pm_schedules(days=30, limit=100)
        row = next((r for r in due["items"] if r["name"] == sched), None)
        self.assertIsNotNone(row, "lịch due PHẢI ∈ items")
        self.assertEqual(row["next_wo_ref"], wo, "next_wo_ref = PK phiếu mở của lịch")
        self.assertEqual(row["next_wo_status"], "Overdue", "next_wo_status khớp phiếu")

    def test_t2_completed_cancelled_or_zero_wo_null(self):
        """T2 (AC2 null): lịch chỉ có phiếu Completed/Cancelled HOẶC 0 phiếu → cả 2 = None."""
        from assetcore.services.imm08 import get_due_pm_schedules
        a1, s1 = self._new_schedule("-nwo-t2a", next_due_date=add_days(nowdate(), 5))
        self._make_wo(a1, s1, status="Completed", scheduled_date=add_days(nowdate(), 3))
        a2, s2 = self._new_schedule("-nwo-t2b", next_due_date=add_days(nowdate(), 6))
        self._make_wo(a2, s2, status="Cancelled", scheduled_date=add_days(nowdate(), 3))
        a3, s3 = self._new_schedule("-nwo-t2c", next_due_date=add_days(nowdate(), 7))  # 0 phiếu
        due = get_due_pm_schedules(days=30, limit=100)
        for sched in (s1, s2, s3):
            row = next((r for r in due["items"] if r["name"] == sched), None)
            self.assertIsNotNone(row, f"{sched} PHẢI ∈ items")
            self.assertIsNone(row["next_wo_ref"],
                              f"{sched}: 0 phiếu MỞ ⇒ next_wo_ref None (không đoán bừa)")
            self.assertIsNone(row["next_wo_status"], f"{sched}: next_wo_status None")

    def test_t3_order_nearest_and_single_batch_query(self):
        """T3 (AC2 order + no-N+1): 2 phiếu mở (Open xa + Overdue gần) → next_wo_ref =
        phiếu scheduled_date gần nhất (asc); enrich WO CHỈ 1 query (đếm qua spy)."""
        from assetcore.services.imm08 import get_due_pm_schedules
        asset, sched = self._new_schedule("-nwo-t3", next_due_date=add_days(nowdate(), 5))
        self._make_wo(asset, sched, status="Open", scheduled_date=add_days(nowdate(), 20))
        near = self._make_wo(asset, sched, status="Overdue",
                             scheduled_date=add_days(nowdate(), 2))
        orig_get_all = frappe.get_all
        wo_calls = {"n": 0}

        def _spy(doctype, *a, **k):
            if doctype == "PM Work Order":
                wo_calls["n"] += 1
            return orig_get_all(doctype, *a, **k)

        with patch.object(frappe, "get_all", side_effect=_spy):
            due = get_due_pm_schedules(days=30, limit=100)
        row = next((r for r in due["items"] if r["name"] == sched), None)
        self.assertIsNotNone(row)
        self.assertEqual(row["next_wo_ref"], near,
                         "phiếu scheduled_date gần hạn nhất (asc) = next_wo_ref")
        self.assertEqual(row["next_wo_status"], "Overdue")
        self.assertEqual(wo_calls["n"], 1,
                         "enrich next_wo PHẢI 1 batch query PM Work Order (no N+1)")

    def test_t7_contract_shape_every_item_has_next_wo_keys(self):
        """T7 (AC1 contract-shape): keys == {items, threshold_days, total, truncated};
        MỌI item có key next_wo_ref + next_wo_status (kể cả null) — chặn drift shape."""
        from assetcore.services.imm08 import get_due_pm_schedules
        asset, sched = self._new_schedule("-nwo-t7", next_due_date=add_days(nowdate(), 5))
        self._make_wo(asset, sched, status="Open", scheduled_date=add_days(nowdate(), 3))
        due = get_due_pm_schedules(days=30, limit=100)
        self.assertEqual(set(due.keys()),
                         {"items", "threshold_days", "total", "truncated"})
        for r in due["items"]:
            self.assertIn("next_wo_ref", r,
                          "MỌI item PHẢI có key next_wo_ref (kể cả null)")
            self.assertIn("next_wo_status", r,
                          "MỌI item PHẢI có key next_wo_status (kể cả null)")

    # ── AC3 — allowed_transitions Open/Overdue chứa Pending–Device Busy ────────

    def test_t4_allowed_transitions_open_overdue_contain_pending_busy(self):
        """T4 (AC3): get_work_order Open/Overdue → allowed_transitions chứa 'Pending–Device
        Busy' (CTA «Dời lịch» khớp hành vi reschedule)."""
        from assetcore.services.imm08 import get_work_order, PMStatus
        asset, sched = self._new_schedule("-nwo-t4", next_due_date=add_days(nowdate(), 5))
        wo = self._make_wo(asset, sched, status=PMStatus.OPEN,
                           scheduled_date=add_days(nowdate(), 3))
        self.assertIn(PMStatus.PENDING_BUSY, get_work_order(wo)["allowed_transitions"],
                      "Open → allowed_transitions PHẢI chứa Pending–Device Busy")
        frappe.db.set_value("PM Work Order", wo, "status", PMStatus.OVERDUE,
                            update_modified=False)
        frappe.db.commit()
        self.assertIn(PMStatus.PENDING_BUSY, get_work_order(wo)["allowed_transitions"],
                      "Overdue → allowed_transitions PHẢI chứa Pending–Device Busy")

    # ── AC4 — reschedule terminal guard + regression ──────────────────────────

    def test_t5_reschedule_terminal_guard_422_due_date_preserved(self):
        """T5 (AC4 guard): reschedule phiếu Completed/Cancelled → 422 VALIDATION;
        due_date KHÔNG bị ghi đè (vá lỗ ghi im lặng lên phiếu terminal)."""
        from assetcore.services.imm08 import reschedule, PMStatus
        from assetcore.services.shared import ErrorCode
        reason = "Thiết bị đang dùng cho ca cấp cứu, dời lịch sang tuần sau"
        new_date = str(add_days(nowdate(), 14))
        for terminal in (PMStatus.COMPLETED, PMStatus.CANCELLED):
            due_before = str(add_days(nowdate(), 3))
            asset, sched = self._new_schedule(
                f"-nwo-t5{terminal[:3].lower()}", next_due_date=add_days(nowdate(), 5))
            wo = self._make_wo(asset, sched, status=terminal,
                               scheduled_date=due_before, due_date=due_before)
            with self.assertRaises(ServiceError) as cm:
                reschedule(wo, new_date=new_date, reason=reason)
            self.assertEqual(cm.exception.code, ErrorCode.VALIDATION,
                             f"{terminal}: guard PHẢI raise VALIDATION")
            self.assertEqual(cm.exception.http_status, 422, f"{terminal}: http 422")
            self.assertEqual(
                str(frappe.db.get_value("PM Work Order", wo, "due_date")), due_before,
                f"{terminal}: due_date KHÔNG bị ghi đè (guard TRƯỚC mutate)")
            self.assertEqual(
                frappe.db.get_value("PM Work Order", wo, "status"), terminal,
                f"{terminal}: status GIỮ terminal (KHÔNG flip Pending–Device Busy)")

    def test_t6_reschedule_open_overdue_success_regression(self):
        """T6 (AC4 regression): reschedule phiếu Open/Overdue (reason hợp lệ) → thành công,
        status → 'Pending–Device Busy', due_date = new_date (giữ hành vi cũ ca hợp lệ)."""
        from assetcore.services.imm08 import reschedule, PMStatus
        reason = "Thiết bị bận ca mổ, dời lịch bảo trì sang tuần sau"
        for start in (PMStatus.OPEN, PMStatus.OVERDUE):
            asset, sched = self._new_schedule(
                f"-nwo-t6{start[:3].lower()}", next_due_date=add_days(nowdate(), 5))
            wo = self._make_wo(asset, sched, status=start,
                               scheduled_date=add_days(nowdate(), 3))
            new_date = str(add_days(nowdate(), 21))
            res = reschedule(wo, new_date=new_date, reason=reason)
            frappe.db.commit()
            self.assertEqual(res["status"], PMStatus.PENDING_BUSY,
                             f"{start}: reschedule hợp lệ → Pending–Device Busy")
            self.assertEqual(
                frappe.db.get_value("PM Work Order", wo, "status"),
                PMStatus.PENDING_BUSY, f"{start}: status persisted Pending–Device Busy")
            self.assertEqual(
                str(frappe.db.get_value("PM Work Order", wo, "due_date")), new_date,
                f"{start}: due_date = new_date")


class TestPMDashboardPeriodEcho(FrappeTestCase):
    """CR-36 (Mobile-BE Dashboard KPI / IMM-07) — get_pm_dashboard_stats phải ECHO
    kỳ báo-cáo `period: {year, month}` = ĐÚNG kỳ service tính (server-resolve, KHÔNG
    đồng-hồ client). Đối-xứng imm11.get_kpis (đã có period) + imm09.get_kpis.

    Bất biến:
      - period = kỳ service THẬT tính (year/month keyword của get_dashboard_stats).
      - api-tier no-param → period echo {getdate(nowdate()).year, .month} (resolve
        tại wrapper api/imm08.py — KHÔNG client-clock).
      - kpis + trend_6months GIỮ NGUYÊN (chỉ THÊM period, KHÔNG đổi/xoá field cũ).
    """

    def setUp(self):
        frappe.set_user("Administrator")

    def test_service_period_echoes_explicit_year_month(self):
        """get_dashboard_stats(year=2026, month=7) → period == {'year':2026,'month':7}."""
        from assetcore.services.imm08 import get_dashboard_stats
        res = get_dashboard_stats(year=2026, month=7)
        self.assertEqual(res["period"], {"year": 2026, "month": 7},
                         "period PHẢI echo ĐÚNG kỳ service tính (year=2026, month=7).")

    def test_service_period_no_regression_kpis_trend(self):
        """THÊM period KHÔNG mất field cũ — kpis + trend_6months vẫn present."""
        from assetcore.services.imm08 import get_dashboard_stats
        res = get_dashboard_stats(year=2026, month=7)
        self.assertIn("kpis", res, "kpis PHẢI vẫn present (no-regression).")
        self.assertIn("trend_6months", res, "trend_6months PHẢI vẫn present (no-regression).")
        self.assertIsInstance(res["trend_6months"], list, "trend_6months vẫn là list.")
        # kpis giữ nguyên 7-key VERBATIM (INV-PM-KPI) — period KHÔNG chui vào kpis.
        self.assertNotIn("period", res["kpis"],
                         "period PHẢI ở TOP-LEVEL, KHÔNG lẫn vào kpis.")

    def test_api_tier_default_period_echoes_server_resolved_today(self):
        """api-tier get_pm_dashboard_stats() KHÔNG param → period = server-resolve
        {getdate(nowdate()).year, .month} (chứng minh echo kỳ server, KHÔNG client-clock)."""
        from assetcore.api.imm08 import get_pm_dashboard_stats
        today = getdate(nowdate())
        resp = get_pm_dashboard_stats()
        self.assertTrue(resp.get("success"), f"phải success envelope, nhận: {resp}")
        self.assertEqual(resp["data"]["period"], {"year": today.year, "month": today.month},
                         "period no-param PHẢI echo kỳ server-resolve today (api/imm08.py:169).")


# ─── CR-69 · Hợp đồng TRUNG THỰC khi cắt — lịch sử PM của thiết bị ────────────

class TestAssetPmHistoryTruncation(FrappeTestCase):
    """TC-BE-08-HIST-01/02/03 (CR-69): ``get_asset_history`` PHẢI công bố
    ``total`` + ``truncated`` thay vì cắt IM LẶNG theo ``limit``.

    Vì sao nghiệp vụ: màn hồ-sơ-vận-hành thiết bị dùng chính danh sách này để
    quyết định "sửa tiếp hay đề nghị thanh lý" (WHO HTM Decommission / hồ sơ
    NĐ98). Thấy 10 lần bảo trì ≠ biết máy đã bảo trì 34 lần.

    Bất biến kiểm được:
      * ``truncated == 1`` ⟺ (``len(history) >= limit`` ∧ ``total > limit``)
      * ``truncated == 0`` ⇒ ``total == len(history)``
      * vừa khít trần (``total == limit``) ⇒ ``truncated == 0`` (KHÔNG báo cắt oan)
      * ``total``/``truncated`` LUÔN là ``int`` Python (parity CR-01 — chống
        int-vs-bool crash khi codegen Dart/Kotlin)
    """

    _assets: list[str] = []

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._assets = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for a in cls._assets:
            # PM Task Log KHÔNG nằm trong _ASSET_DEPENDENTS (immutable audit) →
            # xoá tường minh TRƯỚC purge_asset, nếu không fixture rò lại DB.
            for log in frappe.get_all("PM Task Log", filters={"asset_ref": a},
                                      pluck="name"):
                frappe.delete_doc("PM Task Log", log, force=True,
                                  ignore_permissions=True)
            purge_asset(a)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _seed(self, n: int, tag: str) -> str:
        """Tạo asset mới + ``n`` PM Task Log gắn asset đó. Trả asset_ref."""
        asset = _make_asset(f"-hist{tag}")
        type(self)._assets.append(asset.name)
        for i in range(n):
            doc = frappe.get_doc({
                "doctype": "PM Task Log",
                "asset_ref": asset.name,
                # pm_work_order reqd (Link PM Work Order) — fixture KHÔNG dựng cả
                # chuỗi Template→Schedule→WO vì test chỉ đo semantics đếm/cắt;
                # ignore_links bỏ validate link (giống fixture backdate IMM-09).
                "pm_work_order": f"PM-WO-CR69-{tag}-{i:03d}",
                "pm_type": "Quarterly",
                "completion_date": add_days(nowdate(), -i),
                "overall_result": "Pass",
                "summary": f"_Test CR-69 PM log {i}",
            })
            doc.flags.ignore_links = True
            doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return asset.name

    # ── TC-BE-08-HIST-01: quá trần → total thật + truncated=1 ────────────────
    def test_tc_be_08_hist_01_over_limit_exposes_real_total(self):
        from assetcore.services.imm08 import get_asset_history
        asset = self._seed(12, "01")
        res = get_asset_history(asset, limit=10)
        self.assertEqual(len(res["history"]), 10,
                         "limit=10 ⇒ CHỈ 10 dòng trả về (trần giữ nguyên).")
        self.assertEqual(res["total"], 12,
                         "total = COUNT DB thật trên {asset_ref} TRƯỚC khi cắt (12), "
                         "KHÔNG phải số dòng đã cắt.")
        self.assertEqual(res["truncated"], 1,
                         "12 > 10 ∧ chạm trần ⇒ truncated=1 (danh sách BỊ cắt).")
        # ADDITIVE — 2 khoá cũ GIỮ NGUYÊN (0 breaking, Hyrum's Law).
        self.assertEqual(res["asset_ref"], asset, "asset_ref echo GIỮ NGUYÊN.")
        self.assertIsInstance(res["history"], list, "history[] GIỮ NGUYÊN.")

    # ── TC-BE-08-HIST-02: dưới trần → truncated=0 ∧ total == len(rows) ───────
    def test_tc_be_08_hist_02_under_limit_no_truncation(self):
        from assetcore.services.imm08 import get_asset_history
        asset = self._seed(3, "02")
        res = get_asset_history(asset, limit=10)
        self.assertEqual(res["total"], 3, "3 log ⇒ total=3.")
        self.assertEqual(res["truncated"], 0, "3 < 10 ⇒ KHÔNG cắt.")
        self.assertEqual(res["total"], len(res["history"]),
                         "Bất biến: truncated==0 ⇒ total == len(history).")

    # ── TC-BE-08-HIST-03 (biên): vừa khít trần ⇒ KHÔNG báo cắt oan ───────────
    def test_tc_be_08_hist_03_exactly_at_limit_not_truncated(self):
        from assetcore.services.imm08 import get_asset_history
        asset = self._seed(10, "03")
        res = get_asset_history(asset, limit=10)
        self.assertEqual(len(res["history"]), 10, "10 log, limit=10 ⇒ 10 dòng.")
        self.assertEqual(res["total"], 10, "total=10 (COUNT thật).")
        self.assertEqual(res["truncated"], 0,
                         "total == limit ⇒ vừa khít trần, KHÔNG báo cắt oan "
                         "(len(rows)>=limit CHƯA đủ, phải total>limit).")

    # ── Type-parity CR-01: int thuần, KHÔNG bool/None ────────────────────────
    def test_tc_be_08_hist_04_int_parity_not_bool(self):
        from assetcore.services.imm08 import get_asset_history
        asset = self._seed(1, "04")
        res = get_asset_history(asset, limit=10)
        self.assertIs(type(res["truncated"]), int,
                      "truncated PHẢI là int THUẦN (bool là subclass của int → "
                      "codegen Dart/Kotlin crash int-vs-bool).")
        self.assertIs(type(res["total"]), int, "total PHẢI là int thuần.")
        self.assertIn(res["truncated"], (0, 1), "truncated ∈ {0,1}.")

    # ── INV-PMH-6 (bẫy clamp D5): limit > trần hệ thống ─────────────────────
    def test_tc_be_08_hist_06_limit_above_cap_still_truthful(self):
        """`limit=500` ⇒ rows bị `paginate` clamp về 100; nếu so `len(rows)` với
        `limit` THÔ (500) thì 100 < 500 ⇒ kết luận "không cắt" và total=100 —
        ĐÚNG lời nói dối CR-69 sinh ra để xoá. Trần THỰC ÁP = `pg["page_size"]`.
        """
        from assetcore.services.imm08 import get_asset_history
        asset = self._seed(105, "06")
        res = get_asset_history(asset, limit=500)
        self.assertEqual(len(res["history"]), 100,
                         "trần hệ thống _MAX_PAGE_SIZE=100 vẫn áp cho rows.")
        self.assertEqual(res["total"], 105,
                         "total = COUNT thật (105), KHÔNG phải số dòng đã clamp.")
        self.assertEqual(res["truncated"], 1,
                         "105 > 100 (trần THỰC ÁP) ⇒ PHẢI khai báo bị cắt.")

    # ── INV-PMH-7 (parity `limit=0` giữa 3 tab cùng màn hồ-sơ-thiết-bị) ─────
    def test_tc_be_08_hist_07_limit_zero_falls_back_to_endpoint_default_10(self):
        """`limit=0` ⇒ default **10 của endpoint**, KHÔNG 20 của `paginate`.

        Trước fix: `page_size=int(limit)` → `paginate(..., 0)` → `clamp_page_size(0,
        20)` = 20 ⇒ cùng `limit=0` mà tab PM trả 20 dòng còn tab Sự cố (imm12)
        trả 10 — lệch ngữ nghĩa giữa 3 tab cùng một màn (client mobile dùng chung
        1 tham số). Sau fix: cả 3 dùng `clamp_page_size(limit, 10)`.
        """
        from assetcore.services.imm08 import get_asset_history
        asset = self._seed(12, "07")
        res = get_asset_history(asset, limit=0)
        self.assertEqual(len(res["history"]), 10,
                         "limit=0 ⇒ default 10 CỦA ENDPOINT (KHÔNG 20 của paginate).")
        self.assertEqual(res["total"], 12, "total = COUNT thật (12).")
        self.assertEqual(res["truncated"], 1, "12 > 10 ⇒ khai báo bị cắt.")


# ─────────────────────────────────────────────────────────────────────────────
# AC-CR-77 — `get_pm_work_order` += `available_actions[]` server-driven 4 CTA
# Hợp đồng: docs/imm-08/05 §13 · code-shape: docs/imm-08/04 §4.3 · TC: 07 §IX.
# ─────────────────────────────────────────────────────────────────────────────

_CTA_USER_FULL = "pmcta_full@example.invalid"      # PM User → pm.write/submit/reschedule
_CTA_USER_NOCAP = "pmcta_nocap@example.invalid"    # Auditor → read-only, 0 cap PM

# Mã trạng thái THÔ (tiếng Anh) — reason KHÔNG được chứa bất kỳ chuỗi nào ở đây
# (INV-PMCTA-2: nội suy status vào reason = rò EN ra UI).
_EN_STATUS_TOKENS = (
    "In Progress", "Halted", "Pending", "Completed", "Cancelled", "Overdue", "Open",
)


def _ensure_cta_user(email: str, first_name: str, *roles: str) -> str:
    """Persona test sạch (xoá + tạo lại) — BẮT BUỘC set_user, chạy Administrator = xanh giả."""
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    u = frappe.get_doc({
        "doctype": "User", "email": email, "first_name": first_name,
        "send_welcome_email": 0, "enabled": 1,
    }).insert(ignore_permissions=True)
    if roles:
        u.add_roles(*roles)
    return u.name


class TestPmAvailableActions(FrappeTestCase):
    """AC-CR-77 — 4 CTA server-driven: hết "nút chết" + hết CTA ma `Cancelled`.

    `enabled = transition_allowed ∩ has_cap ∩ business_gate`; `reason` VI 3 bậc
    (transition > capability > business). Bảng chân trị oracle = `05 §13.5`.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-cta")
        cls.template_name = _make_template(cls.cat)["name"]
        cls.schedule_name = _make_schedule(cls.asset.name, cls.template_name)["name"]
        cls.user_full = _ensure_cta_user(
            _CTA_USER_FULL, "PMCTA Full", "PM User", "AssetCore System User")
        cls.user_nocap = _ensure_cta_user(
            _CTA_USER_NOCAP, "PMCTA NoCap", "AssetCore Auditor", "AssetCore System User")
        # WO chính: assigned_to = USER_FULL (row-scope PM User) + bảng kiểm ≥1 mục
        # (từ template 2 mục) ⇒ cô lập tầng `transition` trong bảng chân trị.
        cls.wo_name = create_adhoc_work_order({
            "asset_ref": cls.asset.name,
            "pm_schedule": cls.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": cls.user_full,
        })["name"]
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, pluck="name"
        ):
            frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Schedule", cls.schedule_name, force=True, ignore_permissions=True)
        frappe.delete_doc(
            "PM Checklist Template", cls.template_name, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        for email in (_CTA_USER_FULL, _CTA_USER_NOCAP):
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _wo_doc(self):
        from assetcore.repositories.pm_repo import PMWorkOrderRepo
        return PMWorkOrderRepo.get(self.wo_name)

    def _actions_for_status(self, status: str, *, user: str, doc=None) -> dict:
        """Map key→action của builder cho 1 status (doc IN-MEMORY, KHÔNG ghi DB)."""
        from assetcore.services.imm08 import _build_pm_available_actions
        wo = doc if doc is not None else self._wo_doc()
        wo.status = status
        frappe.set_user(user)
        try:
            return {a["key"]: a for a in _build_pm_available_actions(wo)}
        finally:
            frappe.set_user("Administrator")

    @staticmethod
    def _all_statuses() -> list:
        from assetcore.services.imm08 import _PM_VALID_TRANSITIONS
        return list(_PM_VALID_TRANSITIONS) + ["", "BOGUS"]

    # ── TC-PMCTA-01 (A1 shape/order) ─────────────────────────────────────────
    def test_pmcta_01_shape_order_route(self):
        """`get_work_order` trả `available_actions`: ĐÚNG 4, thứ tự cố định, 5 khoá, route=""."""
        from assetcore.services.imm08 import get_work_order
        frappe.set_user(self.user_full)
        try:
            detail = get_work_order(self.wo_name)
        finally:
            frappe.set_user("Administrator")
        self.assertIn("available_actions", detail,
                      "get_work_order PHẢI emit `available_actions` (server-driven CTA).")
        actions = detail["available_actions"]
        self.assertEqual(len(actions), 4, "LUÔN đủ 4 CTA kể cả khi enabled=false.")
        self.assertEqual(
            [a["key"] for a in actions],
            ["start_work", "submit_result", "reschedule", "report_major_failure"],
            "Thứ tự CỐ ĐỊNH = thứ tự render FE.")
        for a in actions:
            self.assertEqual(
                set(a), {"key", "label", "route", "enabled", "reason"},
                f"Shape phần tử PHẢI == AvailableAction (5 khoá), thấy {sorted(a)}.")
            self.assertEqual(a["route"], "", "CTA nằm TRONG màn ⇒ route rỗng.")
            self.assertIsInstance(a["enabled"], bool, "enabled PHẢI là bool.")
            self.assertTrue(a["label"].strip(), "label VI KHÔNG được rỗng.")

    # ── TC-PMCTA-02 (bảng chân trị 9×4) ──────────────────────────────────────
    def test_pmcta_02_truth_table_9_rows(self):
        """Bảng chân trị `05 §13.5` — 9 hàng × 4 cột (enabled ∧ bậc reason)."""
        from assetcore.services.imm08 import (
            PMStatus, _PM_ACTION_REASON_TRANSITION,
        )
        T, X = True, False
        expected = {
            PMStatus.OPEN: (T, X, T, X),
            PMStatus.OVERDUE: (T, X, T, X),
            PMStatus.IN_PROGRESS: (X, T, T, T),
            PMStatus.PENDING_BUSY: (X, X, T, X),
            PMStatus.HALTED_MAJOR: (X, X, T, X),
            PMStatus.COMPLETED: (X, X, X, X),
            PMStatus.CANCELLED: (X, X, X, X),
            "": (X, X, X, X),
            "BOGUS": (X, X, X, X),
        }
        keys = ["start_work", "submit_result", "reschedule", "report_major_failure"]
        for status, row in expected.items():
            acts = self._actions_for_status(status, user=self.user_full)
            for key, want in zip(keys, row):
                got = acts[key]
                self.assertEqual(
                    got["enabled"], want,
                    f"[{status or '<rỗng>'}] {key}: enabled={got['enabled']} ≠ {want}.")
                if not want:
                    # ô ❌ ở bảng gốc đều là bậc TRANSITION (cap đủ, assigned_to set,
                    # bảng kiểm ≥1 mục) ⇒ so CẢ reason (chống false-green chỉ so enabled).
                    self.assertEqual(
                        got["reason"], _PM_ACTION_REASON_TRANSITION,
                        f"[{status or '<rỗng>'}] {key}: phải là reason bậc TRANSITION.")

    # ── TC-PMCTA-03 (INV-PMCTA-1 bất biến D9) ────────────────────────────────
    def test_pmcta_03_invariant_reason_iff_disabled(self):
        """`enabled False ⟺ reason != ""` với MỌI status × {có cap, không cap}."""
        for user in (self.user_full, self.user_nocap):
            for status in self._all_statuses():
                for key, a in self._actions_for_status(status, user=user).items():
                    if a["enabled"]:
                        self.assertEqual(
                            a["reason"], "",
                            f"[{user}|{status or '<rỗng>'}] {key}: enabled ⇒ reason rỗng.")
                    else:
                        self.assertNotEqual(
                            a["reason"].strip(), "",
                            f"[{user}|{status or '<rỗng>'}] {key}: disabled PHẢI có lý do.")

    # ── TC-PMCTA-04 (INV-PMCTA-2 VI 100%) ────────────────────────────────────
    def test_pmcta_04_reason_vietnamese_no_en_leak(self):
        """Mọi reason ∈ 4 hằng VI; 0 mã trạng thái EN rò ra UI."""
        from assetcore.services.imm08 import (
            _PM_ACTION_REASON_CAPABILITY, _PM_ACTION_REASON_CHECKLIST_EMPTY,
            _PM_ACTION_REASON_NO_TECHNICIAN, _PM_ACTION_REASON_TRANSITION,
        )
        allowed = {
            "", _PM_ACTION_REASON_TRANSITION, _PM_ACTION_REASON_CAPABILITY,
            _PM_ACTION_REASON_NO_TECHNICIAN, _PM_ACTION_REASON_CHECKLIST_EMPTY,
        }
        for user in (self.user_full, self.user_nocap):
            for status in self._all_statuses():
                for key, a in self._actions_for_status(status, user=user).items():
                    self.assertIn(
                        a["reason"], allowed,
                        f"[{status or '<rỗng>'}] {key}: reason ngoài 4 hằng VI.")
                    for token in _EN_STATUS_TOKENS:
                        self.assertNotIn(
                            token, a["reason"],
                            f"[{status or '<rỗng>'}] {key}: rò mã trạng thái EN '{token}'.")

    # ── TC-PMCTA-05 (INV-PMCTA-4 key ↔ endpoint THẬT, 0 CTA ma) ──────────────
    def test_pmcta_05_every_key_maps_to_whitelisted_endpoint(self):
        """Mỗi key resolve ĐỘNG ra callable whitelisted; `Cancelled` KHÔNG là action."""
        import assetcore.api.imm08 as api08
        from assetcore.services.imm08 import PMStatus, _PM_ACTION_SPECS

        for spec in _PM_ACTION_SPECS:
            fn = getattr(api08, spec["endpoint"], None)
            self.assertTrue(
                callable(fn),
                f"CTA '{spec['key']}' trỏ endpoint '{spec['endpoint']}' KHÔNG tồn tại.")
            self.assertIn(
                fn, frappe.whitelisted,
                f"Endpoint '{spec['endpoint']}' của CTA '{spec['key']}' chưa @whitelist.")
        keys = {s["key"] for s in _PM_ACTION_SPECS}
        self.assertNotIn("cancel", keys, "CTA 'cancel' KHÔNG có endpoint ⇒ không được advertise.")
        self.assertNotIn(
            PMStatus.CANCELLED, {s["target"] for s in _PM_ACTION_SPECS},
            "'Cancelled' là đích hợp lệ trong transition map NHƯNG 0 endpoint ⇒ 0 action.")
        # Đích của mọi CTA phải là state THẬT (không bịa ngoài enum).
        enum = {
            getattr(PMStatus, a) for a in dir(PMStatus)
            if not a.startswith("_") and isinstance(getattr(PMStatus, a), str)
        }
        for spec in _PM_ACTION_SPECS:
            self.assertIn(spec["target"], enum, f"target '{spec['target']}' ∉ PMStatus enum.")

    # ── TC-PMCTA-06 (INV-PMCTA-5 cap parity advertise ↔ enforce, đọc AST) ────
    def test_pmcta_06_cap_parity_with_endpoint_ast(self):
        """`spec.cap` == literal `rbac.require("…")` trong api/imm08.py (AST, KHÔNG chép tay)."""
        import ast
        import inspect

        import assetcore.api.imm08 as api08
        from assetcore.services.imm08 import _PM_ACTION_SPECS

        tree = ast.parse(inspect.getsource(api08))
        caps_by_fn: dict[str, list[str]] = {}
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            found = []
            for call in ast.walk(node):
                if (isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == "require"
                        and isinstance(call.func.value, ast.Name)
                        and call.func.value.id == "rbac"
                        and call.args
                        and isinstance(call.args[0], ast.Constant)):
                    found.append(call.args[0].value)
            caps_by_fn[node.name] = found

        for spec in _PM_ACTION_SPECS:
            self.assertEqual(
                caps_by_fn.get(spec["endpoint"]), [spec["cap"]],
                f"CTA '{spec['key']}': cap advertise '{spec['cap']}' ≠ rbac.require của "
                f"'{spec['endpoint']}' ({caps_by_fn.get(spec['endpoint'])}) — gate nói dối.")

    # ── TC-PMCTA-07 (bậc capability) ─────────────────────────────────────────
    def test_pmcta_07_nocap_persona_gets_capability_reason(self):
        """Persona 0 cap PM, phiếu Open ⇒ disabled bậc CAPABILITY (không phải transition)."""
        from assetcore.services.imm08 import (
            PMStatus, _PM_ACTION_REASON_CAPABILITY,
        )
        acts = self._actions_for_status(PMStatus.OPEN, user=self.user_nocap)
        for key in ("start_work", "reschedule"):
            self.assertFalse(acts[key]["enabled"], f"{key}: thiếu cap ⇒ disabled.")
            self.assertEqual(
                acts[key]["reason"], _PM_ACTION_REASON_CAPABILITY,
                f"{key}: transition OK nhưng thiếu cap ⇒ reason bậc CAPABILITY.")

    # ── TC-PMCTA-08 / 09 (A5 display ⇔ enforcement · bảng kiểm rỗng) ─────────
    def test_pmcta_08_checklist_empty_business_gate(self):
        """`In Progress` + 0 mục bảng kiểm ⇒ submit_result disabled; thêm 1 mục ⇒ enabled."""
        from assetcore.services.imm08 import (
            PMStatus, _PM_ACTION_REASON_CHECKLIST_EMPTY,
        )
        wo = self._wo_doc()
        wo.checklist_results = []
        acts = self._actions_for_status(PMStatus.IN_PROGRESS, user=self.user_full, doc=wo)
        self.assertFalse(acts["submit_result"]["enabled"],
                         "0 mục bảng kiểm ⇒ KHÔNG nghiệm thu được (BR-08-19).")
        self.assertEqual(acts["submit_result"]["reason"], _PM_ACTION_REASON_CHECKLIST_EMPTY)
        wo.append("checklist_results", {
            "checklist_item_idx": 1, "description": "_Test mục bảng kiểm",
            "measurement_type": "Pass/Fail",
        })
        acts2 = self._actions_for_status(PMStatus.IN_PROGRESS, user=self.user_full, doc=wo)
        self.assertTrue(acts2["submit_result"]["enabled"], "≥1 mục ⇒ nghiệm thu được.")
        self.assertEqual(acts2["submit_result"]["reason"], "")

    def test_pmcta_09_advertise_equals_enforcement_checklist_empty(self):
        """CÙNG điều kiện: thẻ nói disabled ⟺ validator chặn `IMM08-CHECKLIST-EMPTY`."""
        from assetcore.services.imm08 import PMStatus
        from assetcore.repositories.pm_repo import PMWorkOrderRepo

        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": self.user_full,
        })
        name = res["name"]
        frappe.db.commit()
        try:
            wo = PMWorkOrderRepo.get(name)
            wo.set("checklist_results", [])
            wo.save(ignore_permissions=True)
            frappe.db.commit()

            wo = PMWorkOrderRepo.get(name)
            acts = self._actions_for_status(PMStatus.IN_PROGRESS, user=self.user_full, doc=wo)
            self.assertFalse(acts["submit_result"]["enabled"],
                             "ADVERTISE: thẻ phải nói KHÔNG nghiệm thu được.")

            # ENFORCE: gọi THẬT đường ghi mà CTA `submit_result` trỏ tới ⇒ chứng
            # minh thẻ nói ĐÚNG điều validator chặn (message = SSoT registry
            # MSG.IMM08_CHECKLIST_EMPTY, KHÔNG literal chép tay).
            from assetcore.services.imm08 import submit_result
            from assetcore.utils.messages import MESSAGES, MSG
            with self.assertRaises(ServiceError) as cm:
                submit_result(name, checklist_results=[], overall_result="Pass",
                              pm_sticker_attached=1, duration_minutes=45)
            self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)
            self.assertIn(
                MESSAGES[MSG.IMM08_CHECKLIST_EMPTY]["template"].split(":")[0],
                cm.exception.message or "",
                "ENFORCE: validator PHẢI chặn bằng MSG.IMM08_CHECKLIST_EMPTY.")
        finally:
            frappe.db.rollback()
            frappe.set_user("Administrator")
            frappe.delete_doc("PM Work Order", name, force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── TC-PMCTA-10 (business-gate no-technician) ────────────────────────────
    def test_pmcta_10_no_technician_business_gate(self):
        """Phiếu Open chưa phân công KTV ⇒ start_work disabled + reason no-technician."""
        from assetcore.services.imm08 import (
            PMStatus, _PM_ACTION_REASON_NO_TECHNICIAN,
        )
        wo = self._wo_doc()
        wo.assigned_to = None
        acts = self._actions_for_status(PMStatus.OPEN, user=self.user_full, doc=wo)
        self.assertFalse(acts["start_work"]["enabled"], "Chưa có KTV ⇒ không dispatch được.")
        self.assertEqual(acts["start_work"]["reason"], _PM_ACTION_REASON_NO_TECHNICIAN)
        wo.assigned_to = self.user_full
        acts2 = self._actions_for_status(PMStatus.OPEN, user=self.user_full, doc=wo)
        self.assertTrue(acts2["start_work"]["enabled"])
        self.assertEqual(acts2["start_work"]["reason"], "")

    # ── TC-PMCTA-11 (INV-PMCTA-8 reschedule display == enforcement) ──────────
    def test_pmcta_11_reschedule_display_equals_enforcement(self):
        """7 status: `reschedule.enabled` ⟺ `reschedule()` KHÔNG raise guard terminal."""
        from assetcore.services.imm08 import (
            _PM_VALID_TRANSITIONS, reschedule,
        )
        from assetcore.repositories.pm_repo import PMWorkOrderRepo
        from assetcore.services.shared import ServiceError

        res = create_adhoc_work_order({
            "asset_ref": self.asset.name,
            "pm_schedule": self.schedule_name,
            "due_date": add_days(nowdate(), 7),
            "assigned_to": self.user_full,
        })
        name = res["name"]
        frappe.db.commit()
        try:
            for status in _PM_VALID_TRANSITIONS:
                PMWorkOrderRepo.set_values(name, {"status": status})
                frappe.db.commit()
                wo = PMWorkOrderRepo.get(name)
                advertised = self._actions_for_status(
                    status, user=self.user_full, doc=wo)["reschedule"]["enabled"]
                blocked = False
                try:
                    reschedule(name, new_date=add_days(nowdate(), 14),
                               reason="Máy đang bận điều trị người bệnh")
                except ServiceError:
                    blocked = True
                self.assertEqual(
                    advertised, not blocked,
                    f"[{status}] advertise={advertised} nhưng enforcement "
                    f"{'CHẶN' if blocked else 'CHO PHÉP'} — display ≠ enforcement.")
        finally:
            frappe.set_user("Administrator")
            frappe.delete_doc("PM Work Order", name, force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── TC-PMCTA-12 (ADR-IMM08-CTA-02 hằng) ──────────────────────────────────
    def test_pmcta_12_reschedule_action_states_constant(self):
        """`RESCHEDULE_ACTION_STATES` = map − terminal, ⊇ `RESCHEDULE_CTA_STATES` (CR-45b)."""
        from assetcore.services.imm08 import (
            PMStatus, RESCHEDULE_ACTION_STATES, RESCHEDULE_CTA_STATES,
            _PM_VALID_TRANSITIONS,
        )
        self.assertEqual(
            set(RESCHEDULE_ACTION_STATES),
            set(_PM_VALID_TRANSITIONS) - {PMStatus.COMPLETED, PMStatus.CANCELLED},
            "Dẫn xuất TỪ SSoT map (thêm state vào map ⇒ tự vào đây).")
        self.assertTrue(
            set(RESCHEDULE_CTA_STATES) <= set(RESCHEDULE_ACTION_STATES),
            "Neo với CR-45b: overlay CTA ⊆ tập status «Hoãn lịch» có nghĩa.")

    # ── TC-PMCTA-13 (A6 back-compat) ─────────────────────────────────────────
    def test_pmcta_13_allowed_transitions_unchanged_superset_payload(self):
        """`allowed_transitions` byte-identical baseline; payload chỉ THÊM 1 khoá."""
        from assetcore.services.imm08 import PMStatus, get_work_order
        from assetcore.repositories.pm_repo import PMWorkOrderRepo

        baseline = {
            PMStatus.OPEN: [PMStatus.IN_PROGRESS, PMStatus.OVERDUE, PMStatus.CANCELLED,
                            PMStatus.PENDING_BUSY],
            PMStatus.OVERDUE: [PMStatus.IN_PROGRESS, PMStatus.CANCELLED,
                               PMStatus.PENDING_BUSY],
            PMStatus.IN_PROGRESS: [PMStatus.COMPLETED, PMStatus.HALTED_MAJOR,
                                   PMStatus.PENDING_BUSY, PMStatus.CANCELLED],
            PMStatus.PENDING_BUSY: [PMStatus.IN_PROGRESS, PMStatus.CANCELLED],
            PMStatus.HALTED_MAJOR: [PMStatus.IN_PROGRESS, PMStatus.CANCELLED],
            PMStatus.COMPLETED: [],
            PMStatus.CANCELLED: [],
        }
        legacy_keys = {
            "name", "asset_ref", "asset_name", "asset_category", "risk_class", "pm_type",
            "wo_type", "status", "due_date", "scheduled_date", "completion_date",
            "assigned_to", "assigned_to_name", "supervisor", "supervisor_name",
            "overall_result", "technician_notes", "pm_sticker_attached", "is_late",
            "is_overdue", "duration_minutes", "source_pm_wo", "allowed_transitions",
            "checklist_results",
        }
        for status, want in baseline.items():
            PMWorkOrderRepo.set_values(self.wo_name, {"status": status})
            frappe.db.commit()
            frappe.set_user(self.user_full)
            try:
                detail = get_work_order(self.wo_name)
            finally:
                frappe.set_user("Administrator")
            self.assertEqual(
                detail["allowed_transitions"], want,
                f"[{status}] allowed_transitions PHẢI giữ nguyên 100% (giá trị + thứ tự).")
            self.assertEqual(
                set(detail), legacy_keys | {"available_actions"},
                f"[{status}] payload chỉ được THÊM `available_actions` (superset).")
        PMWorkOrderRepo.set_values(self.wo_name, {"status": PMStatus.OPEN})
        frappe.db.commit()

    # ── TC-PMCTA-14 (INV-PMCTA-10 READ-ONLY) ─────────────────────────────────
    def test_pmcta_14_get_work_order_is_read_only(self):
        """3 lần đọc ⇒ 0 audit trail / 0 lifecycle event mới, `modified` bất biến."""
        from assetcore.services.imm08 import get_work_order

        before_audit = frappe.db.count("IMM Audit Trail")
        before_evt = frappe.db.count("Asset Lifecycle Event")
        before_mod = frappe.db.get_value("PM Work Order", self.wo_name, "modified")
        frappe.set_user(self.user_full)
        try:
            for _ in range(3):
                get_work_order(self.wo_name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.count("IMM Audit Trail"), before_audit,
                         "get_work_order KHÔNG được ghi audit trail.")
        self.assertEqual(frappe.db.count("Asset Lifecycle Event"), before_evt,
                         "get_work_order KHÔNG được sinh lifecycle event.")
        self.assertEqual(
            frappe.db.get_value("PM Work Order", self.wo_name, "modified"), before_mod,
            "get_work_order KHÔNG được save/modify phiếu.")


# ─── AC-CR-79: whitelist khoá `filters` cho list_pm_work_orders (07 §X.2) ─────

class TestPmFilterKeyWhitelist(FrappeTestCase):
    """AC-CR-79 — khoá `filters` ngoài `_ALLOWED_FILTER_KEYS` ⇒ **400 IN-ENVELOPE**.

    RED-before (probe LIVE 2026-07-27, `bench --site miyano console`):
    `imm08.list_work_orders({"khong_ton_tai_abc":"x"})` RAISE
    `OperationalError (1054, "Unknown column 'tabPM Work Order.khong_ton_tai_abc' in 'WHERE'")`
    → `utils/api_handler.handle` CỐ Ý không bắt Exception chung (`:44-49`) ⇒ thoát ra
    **HTTP-500 KHÔNG có `body.success`** + **lộ tên bảng/cột SQL**.

    Boundaries khoá bằng test: **Always** envelope `success:false` + `INVALID_PARAMS` +
    `http_status=400` + `message_code=VAL-INVALID-FILTER-KEY` · message VI nêu khoá sai +
    tập hợp lệ · whitelist là SSoT DUY NHẤT (mọi TC **import THẲNG** hằng, KHÔNG chép tay) ·
    khoá `apply_vendor_scope` bơm ∈ whitelist (tính TỪ `_VENDOR_SCOPE_FIELD_MAP`).
    **Never** raise → HTTP-4xx/5xx · echo tên bảng/cột SQL · đổi ngữ nghĩa 4 khoá ảo ·
    đổi rows/pagination của khoá hợp lệ (INV-FKEY-1).

    Hợp đồng: `docs/imm-08/05_API_Specification.md §14` · TC: `docs/imm-08/07 §X.2`.
    """

    # Chuỗi TUYỆT ĐỐI KHÔNG được xuất hiện trong envelope (AC1 assert phủ định).
    LEAK_TOKENS = ("Unknown column", "tabPM Work Order", "tabAsset Repair",
                   "OperationalError", "SELECT")

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat("_TestCatIMM08FKey")
        cls.asset = _make_asset("-fkey")
        cls.asset.asset_category = cls.cat
        cls.asset.save(ignore_permissions=True)
        tmpl = _make_template(cls.cat)
        cls.template_name = tmpl["name"]
        cls.schedule_name = _make_schedule(cls.asset.name, cls.template_name)["name"]
        cls.wo_name = cls._make_wo()
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for wo in frappe.get_all("PM Work Order", filters={"asset_ref": cls.asset.name},
                                 pluck="name"):
            frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
        for sc in frappe.get_all("PM Schedule", filters={"asset_ref": cls.asset.name},
                                 pluck="name"):
            frappe.delete_doc("PM Schedule", sc, force=True, ignore_permissions=True)
        frappe.delete_doc("PM Checklist Template", cls.template_name, force=True,
                          ignore_permissions=True)
        purge_asset(cls.asset.name)
        frappe.db.commit()

    @classmethod
    def _make_wo(cls) -> str:
        wo = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": cls.asset.name,
            "pm_schedule": cls.schedule_name,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "Open",
            "due_date": add_days(nowdate(), 7),
            "assigned_to": "Administrator",
        }).insert(ignore_permissions=True)
        return wo.name

    def setUp(self):
        frappe.set_user("Administrator")

    # ── helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _allowed() -> frozenset:
        """Whitelist ĐỌC THẲNG từ service (SSoT) — KHÔNG chép tay (AC2)."""
        from assetcore.services.imm08 import _ALLOWED_FILTER_KEYS
        return _ALLOWED_FILTER_KEYS

    def _probe_values(self) -> dict:
        """Giá trị hợp lệ theo fieldtype cho TỪNG khoá whitelist (TC-PMFK-04).

        `set(...) == _ALLOWED_FILTER_KEYS` được assert riêng ⇒ thêm khoá ở BE mà
        quên probe ⇒ ĐỎ (không im lặng bỏ qua).
        """
        return {
            # cột THẬT trên `PM Work Order`
            "name": self.wo_name,
            "status": "Open",
            "asset_ref": self.asset.name,
            "assigned_to": "Administrator",
            "supervisor": "Administrator",
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "due_date": add_days(nowdate(), 7),
            "completion_date": nowdate(),
            "overall_result": "Pass",
            "is_late": 0,
            "source_pm_wo": self.wo_name,
            # khoá ẢO
            "overdue": "1",
            "due_before": add_days(nowdate(), 7),
            "overdue_live": "1",
            "search": "_ZZ_NO_MATCH_TOKEN_",
        }

    def _call(self, filters, **kw) -> dict:
        from assetcore.api.imm08 import list_pm_work_orders
        payload = filters if isinstance(filters, str) else json.dumps(filters)
        return list_pm_work_orders(filters=payload, page=1, page_size=100, **kw)

    # ── TC-PMFK-01 — khoá lạ = lỗi TYPED, KHÔNG raise ────────────────────────
    def test_pmfk_01_unknown_key_returns_typed_envelope_not_500(self):
        """Khoá lạ ⇒ HTTP-200 + envelope INVALID_PARAMS/400/VAL-INVALID-FILTER-KEY."""
        try:
            env = self._call({"khong_ton_tai_abc": "x"})
        except Exception as exc:  # noqa: BLE001 — chính là hồi quy cần chặn
            self.fail(
                f"Khoá lạ PHẢI trả envelope, KHÔNG raise ({type(exc).__name__}: {exc}). "
                "`api_handler.handle` không bắt Exception chung ⇒ raise = HTTP-500 thô.")
        self.assertIs(env.get("success"), False, f"PHẢI success=False. env={env}")
        # Envelope FLAT (`utils/response._err` — OAS `Error` closed-schema:
        # {success, error:<string>, code, http_status, message_code, …}).
        self.assertEqual(env.get("code"), "INVALID_PARAMS",
                         "bucket PHẢI tái dùng INVALID_PARAMS (ADR-IMM08-FILTERKEY-02).")
        self.assertEqual(env.get("http_status"), 400, "lỗi INPUT ⇒ 400, KHÔNG 5xx.")
        self.assertEqual(env.get("message_code"), "VAL-INVALID-FILTER-KEY",
                         "message_code PHẢI phân biệt với malformed-JSON VAL-INVALID-PARAMS.")
        self.assertIsInstance(env.get("error"), str,
                              "`error` là CHUỖI (Hyrum: đổi shape = breaking mọi client).")

    # ── TC-PMFK-02 — message nêu khoá sai + tập khoá hợp lệ ──────────────────
    def test_pmfk_02_message_names_bad_key_and_allowed_set(self):
        """Message TIẾNG VIỆT nêu tên khoá sai + liệt kê khoá hợp lệ (AC1)."""
        env = self._call({"khong_ton_tai_abc": "x"})
        msg = env.get("error") or ""
        self.assertIn("khong_ton_tai_abc", msg,
                      "Message PHẢI nêu ĐÍCH DANH khoá sai (người dùng mới sửa được).")
        for good in ("asset_ref", "status", "search"):
            self.assertIn(good, msg, f"Message PHẢI liệt kê khoá hợp lệ `{good}`.")

    # ── TC-PMFK-03 — assert PHỦ ĐỊNH: 0 rò rỉ schema/SQL ─────────────────────
    def test_pmfk_03_envelope_leaks_no_sql_schema(self):
        """Envelope KHÔNG chứa tên bảng/cột SQL hay dấu vết OperationalError."""
        env = self._call({"khong_ton_tai_abc": "x"})
        blob = json.dumps(env, ensure_ascii=False)
        for token in self.LEAK_TOKENS:
            self.assertNotIn(token, blob,
                             f"RÒ RỈ SCHEMA: envelope chứa `{token}`. Lỗi INPUT không "
                             f"được phơi cấu trúc CSDL ra client.")

    # ── TC-PMFK-04 — AC2(a): MỌI khoá whitelist đều được honor ───────────────
    def test_pmfk_04_every_allowed_key_is_honored(self):
        """Lặp TỪNG khoá ∈ `_ALLOWED_FILTER_KEYS` (import THẬT) ⇒ success:true."""
        allowed = self._allowed()
        self.assertGreaterEqual(len(allowed), 16,
                                "Whitelist < 16 khoá ⇒ TC này vacuous-pass. Đọc `05 §14.3`.")
        probes = self._probe_values()
        self.assertEqual(
            set(probes), set(allowed),
            "DRIFT probe↔whitelist: thêm/đổi khoá ở BE mà quên bảng probe ⇒ khoá đó "
            "KHÔNG bao giờ được kiểm honor. "
            f"thiếu={sorted(set(allowed) - set(probes))} thừa={sorted(set(probes) - set(allowed))}")
        for key, value in sorted(probes.items()):
            with self.subTest(key=key):
                env = self._call({key: value})
                self.assertIs(env.get("success"), True,
                              f"Khoá whitelist `{key}` bị chặn oan: {env.get('error')}")

    # ── TC-PMFK-05 — AC4: vendor-scope KHÔNG bị 400 oan ──────────────────────
    def test_pmfk_05_vendor_scope_injected_key_is_whitelisted(self):
        """Khoá `apply_vendor_scope` bơm ∈ whitelist — tính TỪ `_VENDOR_SCOPE_FIELD_MAP`."""
        from assetcore.services.shared.scope import _VENDOR_SCOPE_FIELD_MAP
        injected = _VENDOR_SCOPE_FIELD_MAP["PM Work Order"]
        self.assertIn(
            injected, self._allowed(),
            f"Vendor Engineer sẽ nhận 400 OAN: `apply_vendor_scope` bơm khoá `{injected}` "
            "nhưng khoá đó KHÔNG ∈ whitelist. Sửa whitelist — KHÔNG sửa map để test xanh.")

    # ── TC-PMFK-06 — INV-FKEY-4: filters rỗng/absent KHÔNG lỗi ───────────────
    def test_pmfk_06_empty_and_absent_filters_are_ok(self):
        """`'{}'` và `filters` absent ⇒ success (whitelist chỉ chặn khoá LẠ)."""
        from assetcore.api.imm08 import list_pm_work_orders
        env_empty = self._call({})
        self.assertIs(env_empty.get("success"), True, f"filters='{{}}' phải OK: {env_empty}")
        env_absent = list_pm_work_orders(page=1, page_size=100)
        self.assertIs(env_absent.get("success"), True, f"filters absent phải OK: {env_absent}")
        self.assertEqual(
            env_absent["data"]["pagination"]["total"],
            env_empty["data"]["pagination"]["total"],
            "filters absent PHẢI == filters '{}' (default '{}' — 0 regression).")

    # ── TC-PMFK-07 — INV-FKEY-5: malformed JSON giữ mã cũ ────────────────────
    def test_pmfk_07_malformed_json_stays_distinguishable(self):
        """JSON hỏng vẫn đi đường `parse_json` CŨ và PHÂN BIỆT được với khoá-lạ.

        ⚠ Hành vi THẬT (đo 2026-07-27): `api_handler.parse_json` raise ServiceError
        **legacy KHÔNG có `message_code`** ⇒ envelope chỉ có `code=INVALID_PARAMS`.
        Bất biến load-bearing là **phân biệt được 2 cách hỏng của CÙNG tham số
        `filters`**, KHÔNG phải một chuỗi `message_code` cụ thể. (`05 §14.6`
        INV-FKEY-5 ghi "VAL-INVALID-PARAMS" — sai với `parse_json` hiện hành;
        đã ghi open-issue cho BA.) KHÔNG bồi `message_code` vào `parse_json` ở vòng
        này: helper đó dùng chung MỌI endpoint ⇒ thêm khoá envelope = blast-radius
        toàn app (Hyrum), phải có CR riêng.
        """
        env = self._call('{khong-phai-json')
        self.assertIs(env.get("success"), False)
        self.assertEqual(env.get("code"), "INVALID_PARAMS")
        self.assertEqual(env.get("http_status"), 400)
        self.assertNotEqual(
            env.get("message_code"), "VAL-INVALID-FILTER-KEY",
            "malformed JSON KHÔNG được AC-CR-79 nuốt — 2 lỗi khác nhau phải phân biệt được.")
        self.assertIn("JSON", env.get("error") or "",
                      "Message phải nói rõ tham số không phải JSON hợp lệ.")

    # ── TC-PMFK-08 — AC3: 0 regression trên 8 khoá đang dùng thật ────────────
    def test_pmfk_08_no_regression_on_real_world_filters(self):
        """8 combo baseline: rows + `pagination` Y HỆT path CHƯA-validate.

        So sánh trong CÙNG lần chạy giữa entrypoint công khai (ĐÃ cắm validate) và
        `_list_work_orders` (path CŨ, KHÔNG validate) ⇒ nếu validate lỡ pop/sửa dict
        thì lệch lộ ra ngay (INV-FKEY-1). KHÔNG so "có > 0 dòng" (vacuous).
        """
        from assetcore.services.imm08 import _list_work_orders
        combos = [
            {"status": "Open"},
            {"asset_ref": self.asset.name},
            {"assigned_to": "Administrator"},
            {"due_date": add_days(nowdate(), 7)},
            {"due_before": add_days(nowdate(), 30)},
            {"overdue": "1"},
            {"overdue_live": "1"},
            {"search": self.wo_name},
            {"status": "Open", "asset_ref": self.asset.name},
        ]
        for combo in combos:
            with self.subTest(combo=combo):
                baseline = _list_work_orders(dict(combo), page=1, page_size=100)
                env = self._call(combo)
                self.assertIs(env.get("success"), True, f"{combo} → {env.get('error')}")
                self.assertEqual(env["data"]["pagination"], baseline["pagination"],
                                 f"pagination LỆCH baseline cho {combo}.")
                self.assertEqual([r["name"] for r in env["data"]["data"]],
                                 [r["name"] for r in baseline["data"]],
                                 f"rows LỆCH baseline cho {combo}.")

    # ── TC-PMFK-09 — INV-ROWSCOPE giữ nguyên (persona KTV, KHÔNG Administrator) ──
    def test_pmfk_09_rowscope_invariant_holds_for_technician(self):
        """`pagination.total == len(data)` dưới persona row-scoped + filter hợp lệ."""
        ktv = "_test_imm08_fkey_ktv@example.invalid"
        if not frappe.db.exists("User", ktv):
            u = frappe.get_doc({
                "doctype": "User", "email": ktv, "first_name": "IMM08 FKey KTV",
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
            u.add_roles("PM User")
        frappe.db.set_value("PM Work Order", self.wo_name, "assigned_to", ktv,
                            update_modified=False)
        frappe.db.commit()
        try:
            frappe.set_user(ktv)
            env = self._call({"status": "Open"})
            self.assertIs(env.get("success"), True, f"KTV bị chặn: {env.get('error')}")
            data = env["data"]
            self.assertEqual(
                data["pagination"]["total"], len(data["data"]),
                "INV-ROWSCOPE vỡ: count và rows dùng predicate KHÁC nhau.")
        finally:
            frappe.set_user("Administrator")
            frappe.db.set_value("PM Work Order", self.wo_name, "assigned_to",
                                "Administrator", update_modified=False)
            frappe.delete_doc("User", ktv, force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── TC-PMFK-10 — ADR-…-03: khoảng ngày = toán tử trên `due_date` ─────────
    def test_pmfk_10_date_range_uses_operator_on_due_date(self):
        """`{"due_date": ["between", [today, +30d]]}` hợp lệ và TRÚNG phiếu fixture."""
        env = self._call({"due_date": ["between", [nowdate(), add_days(nowdate(), 30)]]})
        self.assertIs(env.get("success"), True, f"between bị chặn: {env.get('error')}")
        names = {r["name"] for r in env["data"]["data"]}
        self.assertIn(self.wo_name, names,
                      "Phiếu fixture (due_date = +7d) PHẢI nằm trong cửa-sổ [today, +30d].")

    # ── TC-PMFK-11 — Self-Correction: khoá FE tự bịa bị chặn TYPED ───────────
    def test_pmfk_11_fe_invented_due_date_from_is_rejected_typed(self):
        """`due_date_from` (FE tự bịa, `PMWorkOrderListView.vue:72`) ⇒ 400, KHÔNG 1054."""
        env = self._call({"due_date_from": "2026-01-01", "due_date_to": "2026-12-31"})
        self.assertIs(env.get("success"), False,
                      "`due_date_from`/`due_date_to` CHƯA TỪNG tồn tại ở BE ⇒ phải bị chặn.")
        self.assertEqual(env.get("message_code"), "VAL-INVALID-FILTER-KEY")
        self.assertIn("due_date_from", env.get("error") or "")
        self.assertNotIn("Unknown column", json.dumps(env, ensure_ascii=False))

    # ── TC-PMFK-13 — web-FE PM thật KHÔNG bịa khoá nào (đọc TỪ hiện vật .vue) ──
    def test_pmfk_13_web_fe_filter_keys_are_all_whitelisted(self):
        """Mọi khoá `buildFilters()` của `PMWorkOrderListView.vue` ∈ whitelist.

        [QA] Bổ sung ĐỐI XỨNG với TC-CMFK-11 (`test_imm09.py`). Nghịch lý trước vòng
        này: guard đọc-hiện-vật CHỈ tồn tại ở IMM-09 — module KHÔNG có bug — trong khi
        bug THẬT (`due_date_from`/`due_date_to` → `Unknown column` → HTTP-500) nằm ở
        IMM-08. TC-PMFK-11 chỉ ghim ĐÚNG 2 chuỗi đã biết ⇒ điều khiển lọc PM MỚI thêm
        sau này (hoặc đổi tên khoá) tái sinh cùng class-of-bug mà suite KHÔNG thấy.
        Đọc TỪ HIỆN VẬT (parse .vue) ⇒ FE thêm `f.<khoá>` mới mà quên whitelist ⇒ ĐỎ.
        """
        import pathlib
        import re
        vue = (pathlib.Path(frappe.get_app_path("assetcore")).parent
               / "frontend" / "src" / "views" / "pm" / "PMWorkOrderListView.vue")
        self.assertTrue(vue.exists(), f"Không thấy hiện vật FE: {vue}")
        src = vue.read_text(encoding="utf-8")
        body = re.search(r"function buildFilters\(\)[^{]*\{(.*?)\n\}", src, re.S)
        self.assertIsNotNone(body, "Không parse được `buildFilters()` — cập regex/hiện vật.")
        keys = set(re.findall(r"\bf\.(\w+)\s*=", body.group(1)))
        self.assertGreaterEqual(len(keys), 5,
                                f"Parse được {len(keys)} khoá (<5) ⇒ TC vacuous. keys={keys}")
        missing = sorted(keys - set(self._allowed()))
        self.assertEqual(
            missing, [],
            f"Web-FE PM gửi khoá KHÔNG ∈ whitelist: {missing} ⇒ màn danh sách sẽ báo lỗi "
            "lọc (trước AC-CR-79 là HTTP-500 lộ `tabPM Work Order`). Hoặc bồi khoá vào "
            "whitelist (kèm consumer + TC), hoặc sửa FE dùng cột THẬT + toán tử Frappe.")
        # Gửi CÙNG LÚC mọi khoá FE dựng được (trừ 2 khoá ảo loại trừ nhau overdue /
        # due_before — FE cũng không bao giờ gửi kèm) ⇒ 0 khoá nào bị chặn oan.
        probes = self._probe_values()
        combo = {k: probes[k] for k in sorted(keys) if k != "overdue"}
        env = self._call(combo)
        self.assertIs(env.get("success"), True,
                      f"Khoá web-FE PM gửi CÙNG LÚC bị chặn ({sorted(combo)}): {env.get('error')}")

    # ── TC-PMFK-14 — `filters` KHÔNG phải object ⇒ vẫn 400 IN-ENVELOPE ───────
    def test_pmfk_14_non_object_filters_stay_in_envelope(self):
        """`filters` là MẢNG/số ⇒ envelope 400, KHÔNG raise (HTTP-500 không envelope).

        [QA] Đo LIVE 2026-07-27 trước fix: `filters='[["asset_ref","=","X"]]'` (dạng
        filter CANONICAL của Frappe, client mobile rất dễ gửi) ⇒
        `TypeError: unhashable type: 'list'` NGAY TẠI `assert_allowed_filter_keys`
        (`set(f)`); `filters='123'` ⇒ `TypeError: 'int' object is not iterable`. Cả hai
        thoát khỏi `api_handler.handle` (cố ý không bắt Exception chung) ⇒ **HTTP-500
        KHÔNG có `body.success`** = ĐÚNG class-of-bug mà AC-CR-79 hứa đóng, chỉ khác
        đường vào. Client mobile route theo `body.success` nên vẫn hỏng như cũ.
        """
        for raw in ('[["asset_ref","=","X"]]', '[["asset_ref","X"]]', "123", '"abc"'):
            with self.subTest(filters=raw):
                try:
                    env = self._call(raw)
                except Exception as exc:  # noqa: BLE001 — chính là hồi quy cần chặn
                    self.fail(
                        f"`filters={raw}` PHẢI trả envelope, KHÔNG raise "
                        f"({type(exc).__name__}: {exc}). `handle` không bắt Exception "
                        "chung ⇒ raise = HTTP-500 thô, mất `body.success`.")
                self.assertIsInstance(env, dict)
                self.assertIs(env.get("success"), False, f"env={env}")
                self.assertEqual(env.get("http_status"), 400,
                                 "Lỗi INPUT ⇒ 400 trong BODY, KHÔNG 5xx.")
                self.assertEqual(env.get("code"), "INVALID_PARAMS")
                blob = json.dumps(env, ensure_ascii=False)
                for token in self.LEAK_TOKENS:
                    self.assertNotIn(token, blob, f"RÒ RỈ SCHEMA với filters={raw}")

    # ── TC-PMFK-12 — nhiều khoá lạ + khoá ký tự bẩn ─────────────────────────
    def test_pmfk_12_multiple_and_dirty_keys_sanitized_and_sorted(self):
        """3 khoá lạ + 1 khoá bẩn ⇒ liệt kê SORTED, khoá bẩn KHÔNG phản chiếu nguyên văn."""
        env = self._call({"zzz_bad": 1, "aaa_bad": 2, "mmm_bad": 3, "a b'; DROP--": 4})
        self.assertIs(env.get("success"), False)
        msg = env.get("error") or ""
        pos = [msg.find(k) for k in ("aaa_bad", "mmm_bad", "zzz_bad")]
        self.assertTrue(all(p >= 0 for p in pos), f"Thiếu khoá lạ trong message: {msg}")
        self.assertEqual(pos, sorted(pos), "Danh sách khoá PHẢI sorted (message deterministic).")
        self.assertNotIn("DROP--", msg,
                         "Khoá ký tự bẩn KHÔNG được phản chiếu nguyên văn (reflected-content).")
        blob = json.dumps(env, ensure_ascii=False)
        for token in self.LEAK_TOKENS:
            self.assertNotIn(token, blob)
