"""IMM-08 — PM Overdue Single-Source-of-Truth (SoT) tests.

TDD-first guard suite cho việc unify predicate "PM quá hạn":
* 1 SoT ``is_pm_overdue(status, due_date, today)`` dùng chung cho cron setter
  (``tasks.check_pm_overdue``), counter (``count_overdue_pm`` qua status=Overdue),
  và drill-down (``_normalize_filters(overdue=1)``).
* Root-cause guard: ``assetcore.tasks.check_pm_overdue`` PHẢI được đăng ký trong
  ``hooks.scheduler_events['daily']`` — nếu unwire (như trước fix) thì status
  Overdue không bao giờ được set ở prod ⇒ counter luôn 0.
* Boundary chốt: due_date < today = quá hạn; due_date == today CHƯA quá hạn.
* Tập status nguồn quá hạn = {Open, In Progress, Pending–Device Busy}
  (regression: cron cũ bỏ sót Pending–Device Busy).

Run: bench --site miyano run-tests --module assetcore.tests.test_imm08_pm_overdue
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm08 import (
    OVERDUE_SOURCE_STATES,
    PMStatus,
    count_overdue_pm,
    is_pm_overdue,
    list_work_orders,
    _normalize_filters,
)
from assetcore.tests.test_imm08 import (
    _ensure_cat,
    _make_asset,
    _make_schedule,
    _make_template,
)
from assetcore.tests._asset_cleanup import purge_asset


# ─── Root-cause guard: scheduler wiring ───────────────────────────────────────

class TestSchedulerWiring(unittest.TestCase):
    """Guard chống unwire tái phát — đây là ROOT CAUSE (status Overdue
    không bao giờ set ở prod vì cron không đăng ký)."""

    def test_check_pm_overdue_registered_in_scheduler(self):
        from assetcore import hooks
        daily = hooks.scheduler_events.get("daily", [])
        self.assertIn(
            "assetcore.tasks.check_pm_overdue",
            daily,
            "ROOT CAUSE: cron check_pm_overdue chưa đăng ký scheduler daily → "
            "status Overdue không bao giờ được set ở prod (counter luôn 0).",
        )

    def test_check_pm_overdue_runs_before_generate(self):
        """KPI phải phản ánh đúng trong ngày → setter chạy TRƯỚC generator."""
        from assetcore import hooks
        daily = hooks.scheduler_events.get("daily", [])
        if "assetcore.services.imm08.generate_pm_work_orders_from_schedule" in daily:
            self.assertLess(
                daily.index("assetcore.tasks.check_pm_overdue"),
                daily.index("assetcore.services.imm08.generate_pm_work_orders_from_schedule"),
                "check_pm_overdue phải đứng TRƯỚC generate_pm_work_orders_from_schedule.",
            )

    # NOTE: dead-code landmine guards (orphan tasks.py jobs trỏ core registry
    # doctype không tồn tại — TDD-1/2/3/4) sống ở suite chuyên biệt
    # ``assetcore.tests.test_tasks_scheduler_integrity`` (AST no-bare-literal +
    # orphan-removed + live-symbol-preserved). KHÔNG nhân bản ở đây để tránh 2
    # guard song song lệch nhau.


# ─── SoT predicate boundary ───────────────────────────────────────────────────

class TestIsPmOverduePredicate(unittest.TestCase):
    """is_pm_overdue là SINGLE SOURCE OF TRUTH cho điều kiện quá hạn."""

    def test_is_pm_overdue_boundary(self):
        today = nowdate()
        # due_date < today + status nguồn → quá hạn
        self.assertTrue(is_pm_overdue(PMStatus.OPEN, add_days(today, -1), today))
        # due_date == today → CHƯA quá hạn (boundary chốt)
        self.assertFalse(is_pm_overdue(PMStatus.OPEN, today, today))
        # due_date > today → chưa quá hạn
        self.assertFalse(is_pm_overdue(PMStatus.OPEN, add_days(today, 1), today))

    def test_is_pm_overdue_excludes_terminal(self):
        today = nowdate()
        past = add_days(today, -5)
        self.assertFalse(is_pm_overdue(PMStatus.COMPLETED, past, today))
        self.assertFalse(is_pm_overdue(PMStatus.CANCELLED, past, today))
        self.assertFalse(is_pm_overdue(PMStatus.HALTED_MAJOR, past, today))
        # đã Overdue rồi không phải nguồn (tránh double-flip)
        self.assertFalse(is_pm_overdue(PMStatus.OVERDUE, past, today))

    def test_is_pm_overdue_pending_busy(self):
        """Regression: cron cũ chỉ bắt Open/In Progress, bỏ sót Pending–Device Busy."""
        today = nowdate()
        self.assertTrue(
            is_pm_overdue(PMStatus.PENDING_BUSY, add_days(today, -1), today),
            "Pending–Device Busy quá hạn phải được bắt.",
        )

    def test_is_pm_overdue_in_progress(self):
        today = nowdate()
        self.assertTrue(is_pm_overdue(PMStatus.IN_PROGRESS, add_days(today, -2), today))

    def test_is_pm_overdue_null_due_date(self):
        today = nowdate()
        self.assertFalse(is_pm_overdue(PMStatus.OPEN, None, today))

    def test_overdue_source_states_membership(self):
        self.assertEqual(
            OVERDUE_SOURCE_STATES,
            {PMStatus.OPEN, PMStatus.IN_PROGRESS, PMStatus.PENDING_BUSY},
        )
        # Terminal / đã-Overdue KHÔNG nằm trong tập nguồn
        for s in (PMStatus.COMPLETED, PMStatus.CANCELLED,
                  PMStatus.HALTED_MAJOR, PMStatus.OVERDUE):
            self.assertNotIn(s, OVERDUE_SOURCE_STATES)


# ─── _normalize_filters derives from same SoT (no divergence) ─────────────────

class TestNormalizeFiltersContract(unittest.TestCase):
    """overdue=1 → status=Overdue (giữ contract FE) + boundary đồng nhất."""

    def test_overdue_filter_maps_to_status(self):
        out = _normalize_filters({"overdue": "1"})
        self.assertEqual(out.get("status"), PMStatus.OVERDUE)

    def test_overdue_zero_no_status_force(self):
        out = _normalize_filters({"overdue": "0"})
        self.assertNotIn("status", out)


# ─── Cron sets Overdue → counter & drill-down match ───────────────────────────

class TestCronSetsOverdueCounterMatches(unittest.TestCase):
    """Sau cron: count_overdue_pm() > 0 và == drill-down ?overdue=1.
    Trước fix: counter luôn 0 (cron không chạy)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = _ensure_cat()
        cls.asset = _make_asset("-ovd")
        # Template name là deterministic (PMCT-{cat}-Quarterly) → reuse nếu đã có
        # từ run trước/test khác, tránh DuplicateEntryError.
        det_tpl = f"PMCT-{cls.cat}-Quarterly"
        cls.tpl = det_tpl if frappe.db.exists("PM Checklist Template", det_tpl) \
            else _make_template(cls.cat)["name"]
        # PM Schedule autoname cũng deterministic (PMS-{asset}-Quarterly). Asset
        # series có thể recycle số sau khi xoá → schedule cũ còn sót gây collision.
        # Purge schedule+WO cũ theo tên deterministic trước khi tạo.
        det_sched = f"PMS-{cls.asset.name}-Quarterly"
        if frappe.db.exists("PM Schedule", det_sched):
            for wo in frappe.get_all(
                "PM Work Order", filters={"pm_schedule": det_sched}, pluck="name"
            ):
                frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
            frappe.delete_doc("PM Schedule", det_sched, force=True, ignore_permissions=True)
        cls.sched = _make_schedule(cls.asset.name, cls.tpl)["name"]

    @classmethod
    def tearDownClass(cls):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": cls.asset.name}, pluck="name"
        ):
            frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)
        for sc in frappe.get_all(
            "PM Schedule", filters={"asset_ref": cls.asset.name}, pluck="name"
        ):
            frappe.delete_doc("PM Schedule", sc, force=True, ignore_permissions=True)
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def _seed_wo(self, status: str, days_offset: int) -> str:
        # Insert luôn ở trạng thái Open (terminal status như Completed/Halted bị
        # validate_work_order chặn nếu thiếu duration/sticker/checklist — đó là
        # đường hợp lệ duy nhất qua submit). Sau đó set_value sang status đích,
        # mô phỏng đúng cách prod đạt terminal mà không trip validator.
        due = add_days(nowdate(), days_offset)
        wo = frappe.get_doc({
            "doctype": "PM Work Order",
            "asset_ref": self.asset.name,
            "pm_schedule": self.sched,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": PMStatus.OPEN,
            "due_date": due,
            "scheduled_date": due,
        }).insert(ignore_permissions=True)
        if status != PMStatus.OPEN:
            frappe.db.set_value("PM Work Order", wo.name, "status", status)
        return wo.name

    def _purge_wos(self):
        for wo in frappe.get_all(
            "PM Work Order", filters={"asset_ref": self.asset.name}, pluck="name"
        ):
            frappe.delete_doc("PM Work Order", wo, force=True, ignore_permissions=True)

    def setUp(self):
        self._purge_wos()

    def tearDown(self):
        self._purge_wos()

    def _drilldown_count(self) -> int:
        res = list_work_orders({"overdue": "1"}, page=1, page_size=500)
        return res["pagination"]["total"] if "pagination" in res else len(res.get("data", []))

    def test_cron_sets_overdue_then_counter_matches(self):
        from assetcore.tasks import check_pm_overdue
        name = self._seed_wo(PMStatus.OPEN, -3)

        before = count_overdue_pm()
        check_pm_overdue()
        after = count_overdue_pm()

        self.assertEqual(
            frappe.db.get_value("PM Work Order", name, "status"),
            PMStatus.OVERDUE,
            "Cron phải flip Open past-due → Overdue.",
        )
        self.assertGreater(after, before)
        self.assertGreaterEqual(after, 1)

    def test_kpi_equals_drilldown(self):
        """KPI (count_overdue_pm) == drill-down list (?overdue=1) — không divergence."""
        from assetcore.tasks import check_pm_overdue
        self._seed_wo(PMStatus.OPEN, -3)
        self._seed_wo(PMStatus.IN_PROGRESS, -10)
        self._seed_wo(PMStatus.PENDING_BUSY, -2)
        check_pm_overdue()

        self.assertEqual(count_overdue_pm(), self._drilldown_count())

    def test_cron_flips_pending_busy(self):
        """Regression: Pending–Device Busy past-due phải bị flip Overdue."""
        from assetcore.tasks import check_pm_overdue
        name = self._seed_wo(PMStatus.PENDING_BUSY, -4)
        check_pm_overdue()
        self.assertEqual(
            frappe.db.get_value("PM Work Order", name, "status"),
            PMStatus.OVERDUE,
        )

    def test_cron_idempotent_and_excludes_terminal(self):
        from assetcore.tasks import check_pm_overdue
        self._seed_wo(PMStatus.OPEN, -3)
        completed = self._seed_wo(PMStatus.COMPLETED, -5)
        cancelled = self._seed_wo(PMStatus.CANCELLED, -5)

        check_pm_overdue()
        n1 = count_overdue_pm()
        check_pm_overdue()
        n2 = count_overdue_pm()

        self.assertEqual(n1, n2, "Chạy cron 2 lần không được tăng count.")
        # Terminal past-due KHÔNG bị flip
        self.assertEqual(
            frappe.db.get_value("PM Work Order", completed, "status"), PMStatus.COMPLETED)
        self.assertEqual(
            frappe.db.get_value("PM Work Order", cancelled, "status"), PMStatus.CANCELLED)

    def test_cron_skips_due_today(self):
        """Boundary: due_date == today KHÔNG vào overdue."""
        from assetcore.tasks import check_pm_overdue
        name = self._seed_wo(PMStatus.OPEN, 0)
        check_pm_overdue()
        self.assertEqual(
            frappe.db.get_value("PM Work Order", name, "status"),
            PMStatus.OPEN,
            "due_date == today CHƯA quá hạn → không flip Overdue.",
        )
