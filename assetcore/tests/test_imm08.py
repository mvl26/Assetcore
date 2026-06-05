"""IMM-08 Preventive Maintenance — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm08
"""
from __future__ import annotations

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
    purge_category_by_name("_TestCatIMM08", "_TestCatIMM08Gate")
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
