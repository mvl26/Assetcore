"""IMM-08 Preventive Maintenance — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm08
"""
from __future__ import annotations

import json
import unittest

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
from assetcore.tests._asset_cleanup import purge_asset


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
    from assetcore.tests._asset_cleanup import (
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

class TestPMChecklistTemplate(unittest.TestCase):
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


class TestPMSchedule(unittest.TestCase):
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


class TestPMWorkOrder(unittest.TestCase):
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


class TestPMAllowedTransitions(unittest.TestCase):
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
            # Open (as created) → key present + đúng codomain (3 next).
            detail = get_work_order(name)
            self.assertIn(
                "allowed_transitions", detail,
                "get_work_order PHẢI emit key 'allowed_transitions' (server-driven CTA).")
            self.assertEqual(
                detail["allowed_transitions"], _PM_VALID_TRANSITIONS[PMStatus.OPEN],
                "Open → [In Progress, Overdue, Cancelled].")

            # In Progress → 4 next (flip status trực tiếp; KHÔNG drive workflow-engine).
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


class TestPMBackfillAndSupervisor(unittest.TestCase):
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


class TestPMListMineScope(unittest.TestCase):
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


# ─── CR-18: free-text search server-side cho list PM Work Order ────────────────

class TestPMListSearch(unittest.TestCase):
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

class TestListPmOverdueLiveFilter(unittest.TestCase):
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


class TestPMCompletionGate(unittest.TestCase):
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


class TestLLBE1PMStats417(unittest.TestCase):
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


class TestNotificationContract(unittest.TestCase):
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

class TestPMOverdueSchedulerWiring(unittest.TestCase):
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


class TestIsPmOverduePredicate(unittest.TestCase):
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


class TestPMOverdueCronAndCounter(unittest.TestCase):
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


class TestPMDueSoonFilterSoT(unittest.TestCase):
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


class TestPMDueSoonBoundaryAndDisjoint(unittest.TestCase):
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

class TestComputeNextPmDateSoT(unittest.TestCase):
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


class TestNextPmDateParityAndAnchor(unittest.TestCase):
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


class TestPMDashboardKpiScope(unittest.TestCase):
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


class TestPmComplianceExcludeCancelled(unittest.TestCase):
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


class TestPMChecklistPhotoAttach(unittest.TestCase):
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


# ─── F8 "Nhắc việc" — get_due_pm_schedules (mobile CR-28b) ─────────────────────
class TestDuePmSchedules(unittest.TestCase):
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
        """TC-DUE-PM-07: shape == {'items':[...],'threshold_days':30}; mỗi row đủ 9
        field gồm asset_name enriched + days_left."""
        from assetcore.services.imm08 import get_due_pm_schedules
        name = self._new_schedule("-shape", next_due_date=add_days(nowdate(), 7))
        due = get_due_pm_schedules(days=30, limit=100)
        self.assertEqual(set(due.keys()), {"items", "threshold_days"},
                         "shape ĐÚNG 2 key {items, threshold_days} (KHÔNG pagination)")
        self.assertEqual(due["threshold_days"], 30, "threshold_days echo param days")
        row = next((r for r in due["items"] if r["name"] == name), None)
        self.assertIsNotNone(row)
        expected_fields = {
            "name", "asset_ref", "asset_name", "pm_type", "status",
            "next_due_date", "last_pm_date", "responsible_technician", "days_left",
        }
        self.assertEqual(set(row.keys()), expected_fields,
                         f"row PHẢI ĐÚNG 9 field: thừa={set(row.keys()) - expected_fields} "
                         f"thiếu={expected_fields - set(row.keys())}")
        self.assertEqual(row["asset_name"], "_Test Asset IMM08-shape",
                         "asset_name enriched từ AC Asset.asset_name")
        self.assertEqual(row["days_left"], 7, "days_left server-derived signed")
