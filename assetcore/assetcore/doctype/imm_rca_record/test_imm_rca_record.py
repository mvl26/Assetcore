# Copyright (c) 2026, AssetCore Team
"""Test cho IMM RCA Record controller — validate + on_submit hooks.

Run: bench --site miyano run-tests --app assetcore --module assetcore.assetcore.doctype.imm_rca_record.test_imm_rca_record
"""
from __future__ import annotations

import unittest
import frappe
from frappe.utils import add_days, today


def _ensure_test_asset() -> str:
    """Tạo asset test (idempotent) — trả về tên."""
    asset_label = "_Test RCA Asset"
    existing = frappe.db.get_value("AC Asset", {"asset_name": asset_label}, "name")
    if existing:
        return existing

    # Category (name = category_name nếu autoname=field)
    if not frappe.db.exists("AC Asset Category", "_Test RCA Cat"):
        frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "_Test RCA Cat",
        }).insert(ignore_permissions=True)

    # Device Model — name auto-generated, lookup by model_name+manufacturer
    model = frappe.db.get_value(
        "IMM Device Model",
        {"model_name": "_Test RCA Model", "manufacturer": "_Test Mfg"},
        "name",
    )
    if not model:
        model_doc = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": "_Test RCA Model",
            "manufacturer": "_Test Mfg",
            "asset_category": "_Test RCA Cat",
        }).insert(ignore_permissions=True)
        model = model_doc.name

    doc = frappe.get_doc({
        "doctype": "AC Asset",
        "asset_name": asset_label,
        "device_model": model,
        "asset_category": "_Test RCA Cat",
    }).insert(ignore_permissions=True)
    return doc.name


def _ensure_test_incident(asset_name: str) -> str:
    inc = frappe.get_doc({
        "doctype": "Incident Report",
        "asset": asset_name,
        "incident_type": "Failure",
        "severity": "High",
        "description": "_Test incident for RCA",
        "reported_at": frappe.utils.now_datetime(),
        "requires_rca": 1,
    }).insert(ignore_permissions=True)
    return inc.name


class TestIMMRCARecordValidate(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.asset_name = _ensure_test_asset()

    def setUp(self) -> None:
        self.incident = _ensure_test_incident(self.asset_name)
        self._created_rca: list[str] = []

    def tearDown(self) -> None:
        for n in self._created_rca:
            try:
                frappe.delete_doc("IMM RCA Record", n, force=True, ignore_permissions=True)
            except Exception:
                pass
        try:
            frappe.delete_doc("Incident Report", self.incident, force=True, ignore_permissions=True)
        except Exception:
            pass

    def _new_rca(self, **overrides) -> dict:
        base = {
            "doctype": "IMM RCA Record",
            "incident_report": self.incident,
            "asset": self.asset_name,
            "trigger_type": "Major Incident",
            "rca_method": "5-Why",
            "status": "RCA Required",
            "due_date": add_days(today(), 7),
        }
        base.update(overrides)
        return base

    # ── Assignment validation ──

    def test_in_progress_requires_assignment(self):
        doc = frappe.get_doc(self._new_rca(status="RCA In Progress"))
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    # ── 5-Why method validation ──

    def test_5why_method_requires_5_steps_when_in_progress(self):
        doc = frappe.get_doc(self._new_rca(
            status="RCA In Progress",
            assigned_to="Administrator",
            five_why_steps=[
                {"why_number": 1, "why_question": "Q1", "why_answer": "A1"},
            ],
        ))
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_5why_complete_path(self):
        steps = [
            {"why_number": i + 1, "why_question": f"Q{i+1}", "why_answer": f"A{i+1}"}
            for i in range(5)
        ]
        doc = frappe.get_doc(self._new_rca(
            status="RCA In Progress",
            assigned_to="Administrator",
            five_why_steps=steps,
        )).insert(ignore_permissions=True)
        self._created_rca.append(doc.name)
        # root_cause được auto-fill từ last why_answer trong before_save
        self.assertEqual(doc.root_cause, "A5")

    # ── Completion requirements ──

    def test_completed_requires_root_cause(self):
        doc = frappe.get_doc(self._new_rca(
            status="Completed",
            assigned_to="Administrator",
            corrective_action_summary="Replace component",
        ))
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_completed_requires_capa_or_action(self):
        doc = frappe.get_doc(self._new_rca(
            status="Completed",
            assigned_to="Administrator",
            root_cause="Sensor failed",
        ))
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_completed_happy_path_marks_incident(self):
        steps = [
            {"why_number": i + 1, "why_question": f"Q{i+1}", "why_answer": f"A{i+1}"}
            for i in range(5)
        ]
        doc = frappe.get_doc(self._new_rca(
            status="Completed",
            assigned_to="Administrator",
            root_cause="Sensor failed",
            corrective_action_summary="Replace sensor + retrain operator",
            five_why_steps=steps,
        )).insert(ignore_permissions=True)
        self._created_rca.append(doc.name)
        # completed_date auto-fill
        self.assertEqual(str(doc.completed_date), today())
        # on_submit chỉ chạy khi submit() — gọi rồi check
        doc.submit()
        # Verify incident.requires_rca cleared
        self.assertEqual(
            frappe.db.get_value("Incident Report", self.incident, "requires_rca"),
            0,
            "Sau khi RCA submit, Incident.requires_rca phải về 0",
        )
