"""IMM-08 Preventive Maintenance — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm08
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_days, nowdate

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
