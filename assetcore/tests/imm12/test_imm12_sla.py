# Copyright (c) 2026, AssetCore Team
"""IMM-12 SLA breach tracking (BR-12-08) — test suite (R23, TDD).

Run: bench --site miyano run-tests --module assetcore.tests.imm12.test_imm12_sla

BR-12-08 (docs/imm-12/02_Analysis_Design.md):
  - report_incident() resolve IMM SLA Policy theo severity -> set sla_policy,
    response_due_at = reported_at + response_time_minutes,
    resolution_due_at = reported_at + resolution_time_hours.
  - acknowledge_incident() set response_breached nếu ack trễ.
  - resolve_incident() set resolution_breached nếu resolve trễ.
  - check_incident_sla_breach() (scheduler) đánh dấu breach cho incident chưa
    đóng đã quá hạn + ghi audit-trail.
  - KHÔNG hardcode giờ — đọc từ IMM SLA Policy. severity->priority:
    Critical->P1, High->P2, Medium->P3, Low->P4.
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import add_to_date, now_datetime

from assetcore.services.imm12 import (
    report_incident,
    acknowledge_incident,
    resolve_incident,
    check_incident_sla_breach,
)
from assetcore.tests._helpers._asset_cleanup import purge_asset
from assetcore.tests.imm12.test_imm12 import _make_asset
from frappe.tests.utils import FrappeTestCase

_RUN = str(int(time.time() * 1000))[-7:]


class TestIncidentSLA(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-sla")
        # KHÔNG tạo/mutate policy — dùng seeded P1 default (fixture migrate).
        # Critical -> P1. Đọc giá trị THẬT để assert policy-relative (không hardcode).
        from assetcore.services.imm00 import get_sla_policy
        cls.policy_doc = get_sla_policy("P1")
        assert cls.policy_doc, "Seeded P1 default SLA Policy phải tồn tại sau migrate"
        cls.policy = cls.policy_doc["name"]
        cls.resp_min = int(cls.policy_doc["response_time_minutes"])
        cls.res_hr = int(cls.policy_doc["resolution_time_hours"])
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(cls.asset.name)
        frappe.db.commit()

    def _report_critical(self) -> str:
        r = report_incident(
            asset=self.asset.name, incident_type="Failure", severity="Critical",
            description="SLA test", clinical_impact="bệnh nhân bị ảnh hưởng",
        )
        return r["name"]

    def test_tc_sla_01_report_sets_due_times_from_policy(self):
        """report_incident resolve policy + set due-time KHÔNG hardcode."""
        name = self._report_critical()
        doc = frappe.get_doc("Incident Report", name)
        self.assertEqual(doc.sla_policy, self.policy)
        self.assertIsNotNone(doc.response_due_at)
        self.assertIsNotNone(doc.resolution_due_at)
        # due-time = reported_at + (giá trị TỪ policy, không hardcode).
        expected_resp = add_to_date(doc.reported_at, minutes=self.resp_min)
        self.assertEqual(
            frappe.utils.get_datetime(doc.response_due_at), expected_resp,
        )
        expected_res = add_to_date(doc.reported_at, hours=self.res_hr)
        self.assertEqual(
            frappe.utils.get_datetime(doc.resolution_due_at), expected_res,
        )

    def test_tc_sla_02_no_breach_when_acked_on_time(self):
        """Ack ngay -> response_breached=0."""
        name = self._report_critical()
        acknowledge_incident(name, notes="ack ngay")
        doc = frappe.get_doc("Incident Report", name)
        self.assertEqual(int(doc.response_breached or 0), 0)

    def test_tc_sla_03_response_breach_when_ack_late(self):
        """Backdate response_due về quá khứ -> ack -> response_breached=1."""
        name = self._report_critical()
        frappe.db.set_value(
            "Incident Report", name, "response_due_at",
            add_to_date(now_datetime(), minutes=-5), update_modified=False,
        )
        acknowledge_incident(name, notes="ack trễ")
        doc = frappe.get_doc("Incident Report", name)
        self.assertEqual(int(doc.response_breached or 0), 1)

    def test_tc_sla_04_resolution_breach_when_resolve_late(self):
        """Backdate resolution_due -> resolve -> resolution_breached=1."""
        name = self._report_critical()
        acknowledge_incident(name, notes="ack")
        from assetcore.services.imm12 import start_work
        start_work(name)
        frappe.db.set_value(
            "Incident Report", name, "resolution_due_at",
            add_to_date(now_datetime(), hours=-1), update_modified=False,
        )
        resolve_incident(name, resolution_notes="đã xử lý xong")
        doc = frappe.get_doc("Incident Report", name)
        self.assertEqual(int(doc.resolution_breached or 0), 1)

    def test_tc_sla_05_scheduler_flags_overdue_open_incident(self):
        """Incident còn Open, resolution_due đã qua -> scheduler đánh breach + audit."""
        name = self._report_critical()
        frappe.db.set_value(
            "Incident Report", name, "resolution_due_at",
            add_to_date(now_datetime(), hours=-2), update_modified=False,
        )
        frappe.db.commit()
        check_incident_sla_breach()
        doc = frappe.get_doc("Incident Report", name)
        self.assertEqual(int(doc.resolution_breached or 0), 1)


if __name__ == "__main__":
    unittest.main()
