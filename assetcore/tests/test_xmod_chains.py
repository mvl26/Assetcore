# Copyright (c) 2026, AssetCore Team
"""Cross-module chain tests — Next Round Test Plan: RC-03, RC-04, RC-07, NEG-11.

RC-03: Incident → RCA Completed → CAPA auto-created with linked_incident.
RC-04: Incident workflow auto-advances RCA Required → Closed after RCA submit.
RC-07: AC Asset.after_insert with is_calibration_required=1 → Calibration Schedule.
NEG-11: Cannot close High-severity Incident without RCA Completed.
"""
from __future__ import annotations

import unittest
from contextlib import suppress

import frappe
from frappe.utils import nowdate, add_days


_CAT_NAME = "_TestCatXmod"


def _ensure_cat() -> str:
    existing = frappe.db.get_value(
        "AC Asset Category", {"category_name": _CAT_NAME}, "name"
    )
    if existing:
        return existing
    return frappe.get_doc(
        {"doctype": "AC Asset Category", "category_name": _CAT_NAME}
    ).insert(ignore_permissions=True).name


def _make_asset(suffix: str, *, is_cal_required: int = 0,
                cal_interval: int = 0) -> "frappe.Document":
    import time
    cat = _ensure_cat()
    prev = getattr(frappe.flags, "in_install", False)
    frappe.flags.in_install = "frappe"  # bypass workflow gate (matches test_imm11)
    tag = suffix.lstrip("-") or "001"
    sn = f"SN-XMOD-{tag}-{int(time.time() * 1000) % 100000}"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset Xmod{suffix}-{tag}",
            "asset_category": cat,
            "manufacturer_sn": sn,
            "lifecycle_status": "Active",
            "is_calibration_required": is_cal_required,
            "calibration_interval_days": cal_interval if is_cal_required else 0,
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _cleanup_asset(asset_name: str) -> None:
    """Remove asset and all dependent rows (cal schedules, incidents, capa, rca).

    Delegates to the shared ``purge_asset`` (raw-SQL audit/lifecycle purge +
    cancel-children) — a plain delete_doc silently fails under the WR-03 / audit
    on_trash guards and leaks the asset.
    """
    from assetcore.tests._asset_cleanup import purge_asset
    try:
        purge_asset(asset_name)
    except Exception:
        pass


def tearDownModule():  # noqa: N802
    """Safety net: purge any cross-module chain fixtures that survived a class's
    teardown gap (the recurring _Test chain incident / _Test RCA Model leak)."""
    from assetcore.tests._asset_cleanup import (
        purge_assets_by_name_prefix,
        purge_category_by_name,
    )
    frappe.set_user("Administrator")
    # Standalone incidents not bound to a purged asset.
    for inc in frappe.db.sql_list(
        "SELECT name FROM `tabIncident Report` WHERE description LIKE %s",
        ("\\_Test%",),
    ):
        with suppress(Exception):
            # Cancel + delete any linked CAPA/RCA first, then the incident.
            for dt, fld in (("IMM CAPA Record", "linked_incident"),
                            ("IMM RCA Record", "incident")):
                if frappe.db.has_column(dt, fld):
                    for ch in frappe.db.sql_list(
                        f"SELECT name FROM `tab{dt}` WHERE `{fld}`=%s", (inc,)
                    ):
                        with suppress(Exception):
                            frappe.delete_doc(dt, ch, force=True, ignore_permissions=True)
            frappe.delete_doc("Incident Report", inc, force=True, ignore_permissions=True)
    purge_assets_by_name_prefix("_Test Asset Xmod")
    purge_category_by_name(_CAT_NAME, "_Test RCA Cat")
    for mdl in frappe.db.sql_list(
        "SELECT name FROM `tabIMM Device Model` WHERE model_name=%s", ("_Test RCA Model",)
    ):
        with suppress(Exception):
            frappe.delete_doc("IMM Device Model", mdl, force=True, ignore_permissions=True)
    frappe.db.commit()


class TestRC07_AutoCalibrationSchedule(unittest.TestCase):
    """RC-07: AC Asset.after_insert with is_calibration_required=1 → Schedule auto-created."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.assets: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for a in cls.assets:
            _cleanup_asset(a)
        cat = frappe.db.get_value("AC Asset Category",
                                   {"category_name": _CAT_NAME}, "name")
        if cat:
            try:
                frappe.delete_doc("AC Asset Category", cat, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass

    def test_no_cal_required_no_schedule(self):
        asset = _make_asset("-nocal", is_cal_required=0)
        self.assets.append(asset.name)
        rows = frappe.get_all("IMM Calibration Schedule",
                               filters={"asset": asset.name})
        self.assertEqual(len(rows), 0,
                         "Asset không tick calibration → KHÔNG được tạo schedule")

    def test_cal_required_creates_schedule(self):
        asset = _make_asset("-yescal", is_cal_required=1, cal_interval=180)
        self.assets.append(asset.name)
        rows = frappe.get_all(
            "IMM Calibration Schedule",
            filters={"asset": asset.name, "is_active": 1},
            fields=["name", "interval_days", "next_due_date"],
        )
        self.assertEqual(len(rows), 1,
                         f"Đúng 1 schedule được tạo cho asset {asset.name}")
        self.assertEqual(rows[0]["interval_days"], 180)
        self.assertIsNotNone(rows[0]["next_due_date"])

    def test_idempotent_second_insert_skipped(self):
        # Tạo asset có schedule, rồi gọi hook lần 2 → KHÔNG duplicate
        asset = _make_asset("-idem", is_cal_required=1, cal_interval=365)
        self.assets.append(asset.name)
        from assetcore.services.imm11 import create_calibration_schedule_from_asset
        result = create_calibration_schedule_from_asset(asset)
        self.assertIsNone(result, "Lần 2 phải skip (idempotent guard)")
        rows = frappe.get_all("IMM Calibration Schedule",
                               filters={"asset": asset.name, "is_active": 1})
        self.assertEqual(len(rows), 1)


class TestRC03_04_RcaCompletedChain(unittest.TestCase):
    """RC-03: CAPA auto từ RCA Completed.
    RC-04: Incident workflow auto-advances RCA Required → Closed.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-chain")

    @classmethod
    def tearDownClass(cls):
        _cleanup_asset(cls.asset.name)
        cat = frappe.db.get_value("AC Asset Category",
                                   {"category_name": _CAT_NAME}, "name")
        if cat:
            try:
                frappe.delete_doc("AC Asset Category", cat, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass

    def test_full_chain_incident_rca_capa_close(self):
        from assetcore.services.imm12 import (
            report_incident, acknowledge_incident, start_work, resolve_incident,
            submit_rca, create_rca,
        )
        # 1. Report High incident — auto-creates RCA via resolve hook later
        incident = report_incident(
            asset=self.asset.name,
            incident_type="Malfunction",
            severity="High",
            description="_Test chain incident",
        )
        ir_name = incident["name"]

        # 2. Acknowledge → start_work → resolve (resolve auto-creates RCA cho High)
        acknowledge_incident(ir_name)
        start_work(ir_name)
        resolved = resolve_incident(
            ir_name,
            resolution_notes="Tạm thời thay phụ tùng A để mở chain",
        )
        self.assertIsNotNone(resolved.get("rca_created"),
                              "Auto-RCA phải được tạo cho High severity sau resolve")
        rca_name = resolved["rca_created"]

        # 3. Manually advance incident workflow Resolved → RCA Required
        # (matches real flow where Compliance Manager applies "Yêu cầu RCA")
        frappe.db.set_value("Incident Report", ir_name, {
            "status": "RCA Required",
            "workflow_state": "RCA Required",
        })
        frappe.db.commit()

        # 4. Submit RCA → triggers on_rca_completed chain
        # RCA auto-create dùng method 5-Why; cần điền 5 steps đủ
        five_steps = [
            {"why_number": i, "why_question": f"Why {i}?",
             "why_answer": f"Vì lý do {i}"}
            for i in range(1, 6)
        ]
        result = submit_rca(
            rca_name,
            root_cause="Nguyên nhân gốc test chain",
            corrective_action="Thay phụ tùng B vĩnh viễn",
            preventive_action="Tăng tần suất PM",
            five_why_steps=five_steps,
        )

        # RC-03 assertion: CAPA exists, linked to incident
        self.assertIsNotNone(result.get("linked_capa"),
                              "RC-03: CAPA phải được tạo sau submit_rca")
        capa_name = result["linked_capa"]
        self.assertTrue(frappe.db.exists("IMM CAPA Record", capa_name))

        capa = frappe.db.get_value(
            "IMM CAPA Record", capa_name,
            ["linked_incident", "source_type", "source_ref"],
            as_dict=True,
        )
        self.assertEqual(capa.linked_incident, ir_name,
                          "RC-03: CAPA.linked_incident phải trỏ về Incident")
        self.assertEqual(capa.source_type, "Incident Report")
        self.assertEqual(capa.source_ref, ir_name)

        # Reverse link
        ir_after = frappe.db.get_value(
            "Incident Report", ir_name,
            ["linked_capa", "workflow_state", "status"],
            as_dict=True,
        )
        self.assertEqual(ir_after.linked_capa, capa_name,
                          "RC-03: Incident.linked_capa phải trỏ về CAPA")

        # RC-04 assertion: incident workflow đẩy về Closed
        self.assertEqual(ir_after.status, "Closed",
                          f"RC-04: Incident phải Closed sau RCA submit, "
                          f"hiện đang '{ir_after.status}'")

    def test_idempotent_rca_resubmit_no_duplicate_capa(self):
        from assetcore.services.imm16 import create_capa_from_incident
        # Create an incident + capa first time
        incident = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": self.asset.name,
            "incident_type": "Malfunction",
            "severity": "High",
            "description": "_Test idempotent",
            "reported_by": "Administrator",
            "reported_at": frappe.utils.now_datetime(),
            "status": "Open",
        }).insert(ignore_permissions=True)

        r1 = create_capa_from_incident(incident.name)
        r2 = create_capa_from_incident(incident.name)
        self.assertEqual(r1["capa_name"], r2["capa_name"],
                          "Idempotent: cùng incident → cùng CAPA name")
        self.assertTrue(r2["reused"], "Lần 2 phải reused")


class TestNEG11_CloseGateForHighIncident(unittest.TestCase):
    """NEG-11: High-severity Incident cannot be closed without RCA Completed."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-neg11")

    @classmethod
    def tearDownClass(cls):
        _cleanup_asset(cls.asset.name)
        cat = frappe.db.get_value("AC Asset Category",
                                   {"category_name": _CAT_NAME}, "name")
        if cat:
            try:
                frappe.delete_doc("AC Asset Category", cat, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass

    def _bypass_workflow(self, doc, target_state: str) -> None:
        """Bypass workflow gate (we test the *validator*, not the workflow engine)."""
        doc.status = target_state
        doc.workflow_state = target_state

    def test_cannot_close_high_without_rca(self):
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            ir = frappe.get_doc({
                "doctype": "Incident Report",
                "asset": self.asset.name,
                "incident_type": "Malfunction",
                "severity": "High",
                "description": "_Test NEG-11 - no RCA",
                "reported_by": "Administrator",
                "reported_at": frappe.utils.now_datetime(),
                "status": "Open",
                "requires_rca": 1,
            }).insert(ignore_permissions=True)
            self._bypass_workflow(ir, "Closed")
            with self.assertRaises(frappe.ValidationError):
                ir.save(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev

    def test_can_close_high_with_completed_rca(self):
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            ir = frappe.get_doc({
                "doctype": "Incident Report",
                "asset": self.asset.name,
                "incident_type": "Malfunction",
                "severity": "High",
                "description": "_Test NEG-11 - with RCA",
                "reported_by": "Administrator",
                "reported_at": frappe.utils.now_datetime(),
                "status": "Open",
                "requires_rca": 1,
            }).insert(ignore_permissions=True)
            rca = frappe.get_doc({
                "doctype": "IMM RCA Record",
                "incident_report": ir.name,
                "asset": self.asset.name,
                "rca_method": "Fishbone",  # avoid strict 5-Why validation
                "trigger_type": "Major Incident",
                "status": "Completed",
                "assigned_to": "Administrator",
                "due_date": add_days(nowdate(), 7),
                "root_cause": "Test root cause",
                "corrective_action_summary": "Test corrective",
                "completed_date": nowdate(),
                "completed_by": "Administrator",
            }).insert(ignore_permissions=True)
            ir.rca_record = rca.name
            self._bypass_workflow(ir, "Closed")
            try:
                ir.save(ignore_permissions=True)
            except frappe.ValidationError as e:
                self.fail(f"NEG-11: Close should pass with RCA Completed, got: {e}")
        finally:
            frappe.flags.in_install = prev

    def test_low_severity_close_not_gated(self):
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            ir = frappe.get_doc({
                "doctype": "Incident Report",
                "asset": self.asset.name,
                "incident_type": "Malfunction",
                "severity": "Low",
                "description": "_Test low",
                "reported_by": "Administrator",
                "reported_at": frappe.utils.now_datetime(),
                "status": "Open",
            }).insert(ignore_permissions=True)
            self._bypass_workflow(ir, "Closed")
            ir.save(ignore_permissions=True)  # should NOT raise
        finally:
            frappe.flags.in_install = prev
