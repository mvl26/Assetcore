# Copyright (c) 2026, AssetCore Team
"""IMM-00 Setup Validation — Smoke Test Checklist (S-01..S-13).

Source: docs/imm-00/07_Testing_QA.md §II.1.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.imm00.test_imm00_smoke
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import nowdate

from assetcore.tests._helpers._asset_cleanup import purge_asset
from frappe.tests.utils import FrappeTestCase


_UID = str(int(time.time()) % 100000)


def _insert_asset_bypass_workflow(data: dict):
    """Insert AC Asset bypassing workflow guard (BR-00-02) for fixtures."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def setUpModule():
    frappe.set_user("Administrator")


# ─── S-01 ────────────────────────────────────────────────────────────────────

class TestS01_CreateAssetCategory(FrappeTestCase):
    """S-01: Tạo 1 AC Asset Category → Record được lưu, `name = category_code`."""

    def test_category_name_equals_code(self):
        code = f"_TestSmokeCat-{_UID}"
        cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": code,
            "category_name": f"Thiết bị Hô hấp & Hồi sức (smoke) {_UID}",
        }).insert(ignore_permissions=True)
        try:
            self.assertEqual(cat.name, code)
            self.assertTrue(frappe.db.exists("AC Asset Category", code))
        finally:
            frappe.delete_doc("AC Asset Category", cat.name, force=True, ignore_permissions=True)


# ─── S-02 ────────────────────────────────────────────────────────────────────

class TestS02_CreateDepartmentAutoname(FrappeTestCase):
    """S-02: Tạo 1 AC Department (không nhập code) → autoname `AC-DEPT-####`."""

    def test_department_autoname_pattern(self):
        dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": f"_TestSmoke ICU {_UID}",
        }).insert(ignore_permissions=True)
        try:
            self.assertTrue(dept.name.startswith("AC-DEPT-"),
                            f"Expected AC-DEPT- prefix, got: {dept.name}")
            # department_code should be synced with name
            self.assertEqual(dept.department_code, dept.name)
        finally:
            frappe.delete_doc("AC Department", dept.name, force=True, ignore_permissions=True)


# ─── S-03 ────────────────────────────────────────────────────────────────────

class TestS03_CreateLocationTree(FrappeTestCase):
    """S-03: Tạo 1 AC Location (tree node) → lft/rgt được set qua nested-set."""

    def test_location_lft_rgt_populated(self):
        loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": f"_TestSmoke Room {_UID}",
            "clinical_area_type": "ICU",
        }).insert(ignore_permissions=True)
        try:
            self.assertTrue(loc.name.startswith("AC-LOC-"))
            # Re-read from DB — Frappe rebuilds tree on insert.
            row = frappe.db.get_value(
                "AC Location", loc.name, ["lft", "rgt"], as_dict=True
            )
            self.assertIsNotNone(row.lft, "lft chưa được nested-set populate")
            self.assertIsNotNone(row.rgt, "rgt chưa được nested-set populate")
            self.assertGreater(row.rgt, row.lft, "rgt phải > lft")
        finally:
            frappe.delete_doc("AC Location", loc.name, force=True, ignore_permissions=True)


# ─── S-04 ────────────────────────────────────────────────────────────────────

class TestS04_DeviceModelClassMappingRisk(FrappeTestCase):
    """S-04: Tạo IMM Device Model Class II → risk_classification = Medium (BR-00-01)."""

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestSmokeCatS04-{_UID}",
            "category_name": f"Thiết bị Chẩn đoán Hình ảnh (smoke S-04) {_UID}",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)

    def test_class_ii_maps_to_medium(self):
        model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": f"_TestSmoke Mindray DC-70 {_UID}",
            "manufacturer": "Mindray (smoke)",
            "medical_device_class": "Class II",
            "asset_category": self._cat.name,
            "is_radiation_device": 0,
        }).insert(ignore_permissions=True)
        try:
            self.assertEqual(model.risk_classification, "Medium",
                             "BR-00-01: Class II → Medium")
        finally:
            frappe.delete_doc("IMM Device Model", model.name, force=True, ignore_permissions=True)


# ─── S-05 ────────────────────────────────────────────────────────────────────

class TestS05_DeviceModelFetchPayload(FrappeTestCase):
    """S-05: AC Asset link với Device Model → BE API trả về fields FE cần auto-fill.

    Per 04_Backend_Design.md §125: auto-fill là FE concern (Vue
    `watch(form.device_model)`). BE smoke chỉ verify endpoint trả đủ field cho FE.
    """

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestSmokeCatS05-{_UID}",
            "category_name": f"Thiết bị Hô hấp (smoke S-05) {_UID}",
        }).insert(ignore_permissions=True)
        cls._model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": f"_TestSmoke Dräger Evita V500 {_UID}",
            "manufacturer": "Dräger (smoke)",
            "medical_device_class": "Class III",
            "asset_category": cls._cat.name,
            "is_pm_required": 1,
            "pm_interval_days": 180,
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("IMM Device Model", cls._model.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)

    def test_get_device_model_returns_autofill_fields(self):
        from assetcore.api.imm00 import get_device_model
        resp = get_device_model(self._model.name)
        self.assertTrue(resp.get("success"), f"Endpoint failed: {resp}")
        data = resp["data"]
        # Critical fields the FE copies into the Asset form.
        self.assertEqual(data["medical_device_class"], "Class III")
        self.assertIn(data["risk_classification"], {"High", "Critical"})
        self.assertEqual(data["pm_interval_days"], 180)


# ─── S-06 / S-07 / S-12 (share asset fixture) ────────────────────────────────

class TestAssetLifecycleSmoke(FrappeTestCase):
    """S-06: Submit AC Asset → lifecycle_status=Commissioned + 1 ALE.
    S-07: Transition Active → Under Repair → 1 ALE repair_opened + 1 Audit Trail.
    S-12: verify_audit_chain → {valid: true, count: N}.
    """

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestSmokeCatS06-{_UID}",
            "category_name": f"Thiết bị Phẫu thuật (smoke S-06) {_UID}",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        # Raw SQL for tables guarded by `on_trash` (ISO 13485 immutability + ALE
        # immutability). force=True does NOT bypass custom on_trash — only raw
        # DELETE works for fixture purge.
        assets = frappe.get_all("AC Asset", filters={"asset_category": cls._cat.name}, pluck="name")
        for a in assets:
            if frappe.db.table_exists("AC Asset Downtime Log"):
                frappe.db.sql(
                    "DELETE FROM `tabAC Asset Downtime Log` WHERE asset=%s", (a,)
                )
            purge_asset(a)
        frappe.db.commit()
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_asset(self, tag: str):
        return _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"_TestSmoke EPIQ7 {tag}-{_UID}",
            "asset_category": self._cat.name,
            "manufacturer_sn": f"_TestSmokeSN-{tag}-{_UID}",
            "medical_device_class": "Class II",
            "risk_classification": "High",
            "purchase_date": "2024-03-15",
            "gross_purchase_amount": 950_000_000,
            "warranty_expiry_date": "2027-03-15",
            "in_service_date": "2024-03-20",
            "commissioning_date": "2024-03-20",
            "byt_reg_no": f"BYT-TB-2024-{tag}-{_UID}",
            "is_pm_required": 1,
            "pm_interval_days": 180,
            "lifecycle_status": "Commissioned",
        })

    # S-06
    def test_s06_asset_commissioned_creates_lifecycle_event(self):
        from assetcore.services.imm00 import transition_asset_status

        asset = self._make_asset("s06")
        # Asset inserted với Commissioned. ALE chưa có do bypass workflow.
        # Smoke: re-transition Commissioned → Active để tạo ALE đầu tiên.
        transition_asset_status(
            asset.name, "Active", actor="Administrator",
            reason="Hoàn tất nghiệm thu, đưa vào sử dụng (smoke S-06)",
        )
        frappe.db.commit()
        ales = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        self.assertGreaterEqual(ales, 1, "S-06: phải có ít nhất 1 Asset Lifecycle Event")

    # S-07
    def test_s07_active_to_under_repair_creates_event_and_audit(self):
        from assetcore.services.imm00 import transition_asset_status

        asset = self._make_asset("s07")
        transition_asset_status(asset.name, "Active", actor="Administrator")
        frappe.db.commit()
        ale_before = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        audit_before = frappe.db.count("IMM Audit Trail", {"asset": asset.name})

        transition_asset_status(
            asset.name, "Under Repair", actor="Administrator",
            reason="Thiết bị báo lỗi áp lực — chuyển vào sửa chữa (smoke S-07)",
        )
        frappe.db.commit()

        ale_after = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        audit_after = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        self.assertEqual(ale_after - ale_before, 1, "S-07: phải tạo đúng 1 ALE repair_opened")
        self.assertGreaterEqual(audit_after - audit_before, 1, "S-07: phải tạo Audit Trail entry")

        # Verify event_type
        last_event = frappe.db.get_value(
            "Asset Lifecycle Event",
            {"asset": asset.name, "to_status": "Under Repair"},
            "event_type",
        )
        self.assertEqual(last_event, "repair_opened")

    # S-12
    def test_s12_verify_audit_chain_valid(self):
        from assetcore.services.imm00 import transition_asset_status, verify_audit_chain

        asset = self._make_asset("s12")
        transition_asset_status(asset.name, "Active", actor="Administrator")
        transition_asset_status(asset.name, "Under Repair", actor="Administrator")
        transition_asset_status(asset.name, "Active", actor="Administrator")
        frappe.db.commit()

        result = verify_audit_chain(asset.name)
        self.assertTrue(result.get("valid"),
                        f"S-12: audit chain phải hợp lệ, got: {result}")
        self.assertGreaterEqual(result.get("count", 0), 3,
                                f"S-12: ít nhất 3 audit entries, got: {result}")


# ─── S-08 / S-09 (CAPA lifecycle) ────────────────────────────────────────────

class TestCAPASmoke(FrappeTestCase):
    """S-08: CAPA thiếu root_cause + submit → ValidationError (BR-00-08).
    S-09: CAPA đủ field + close → status=Closed, docstatus=1.
    """

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestSmokeCatCAPA-{_UID}",
            "category_name": f"Thiết bị Theo dõi (smoke CAPA) {_UID}",
        }).insert(ignore_permissions=True)
        cls._asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"_TestSmoke Mindray T9 CAPA-{_UID}",
            "asset_category": cls._cat.name,
            "manufacturer_sn": f"_TestSmokeSN-CAPA-{_UID}",
            "medical_device_class": "Class II",
            "risk_classification": "High",
            "purchase_date": "2024-01-15",
            "gross_purchase_amount": 300_000_000,
            "warranty_expiry_date": "2027-01-15",
            "in_service_date": "2024-01-25",
            "byt_reg_no": f"BYT-TB-2024-CAPA-{_UID}",
            "is_pm_required": 1,
            "pm_interval_days": 90,
            "lifecycle_status": "Active",
        })

    @classmethod
    def tearDownClass(cls):
        # Cancel + delete CAPAs first (otherwise asset on_trash blocks)
        capas = frappe.get_all("IMM CAPA Record",
                                filters={"asset": cls._asset.name}, pluck="name")
        for c in capas:
            doc = frappe.get_doc("IMM CAPA Record", c)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("IMM CAPA Record", c, force=True, ignore_permissions=True,
                              delete_permanently=True)
        purge_asset(cls._asset.name)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    # S-08
    def test_s08_submit_capa_without_root_cause_fails(self):
        from assetcore.services.imm00 import create_capa

        capa_name = create_capa(
            asset=self._asset.name,
            source_type="Non-Conformance",
            source_ref="",
            severity="Minor",
            description="Smoke S-08 — thiếu root_cause sẽ chặn submit",
            responsible="Administrator",
            due_days=14,
        )
        try:
            doc = frappe.get_doc("IMM CAPA Record", capa_name)
            with self.assertRaises(frappe.ValidationError,
                                   msg="S-08: submit không root_cause phải raise BR-00-08"):
                doc.submit()
        finally:
            doc = frappe.get_doc("IMM CAPA Record", capa_name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("IMM CAPA Record", capa_name, force=True,
                              ignore_permissions=True, delete_permanently=True)

    # S-09
    def test_s09_close_capa_with_full_fields(self):
        from assetcore.services.imm00 import create_capa, close_capa

        capa_name = create_capa(
            asset=self._asset.name,
            source_type="Non-Conformance",
            source_ref="",
            severity="Minor",
            description="Smoke S-09 — full lifecycle close",
            responsible="Administrator",
            due_days=14,
        )
        try:
            close_capa(
                capa_name=capa_name,
                root_cause="Cảm biến SpO2 lỏng đầu nối do rung chuyển khi di chuyển máy",
                corrective_action="Siết và cố định cáp; kiểm tra lại bằng thiết bị mô phỏng",
                preventive_action="Bổ sung kiểm tra đầu nối vào checklist trước mỗi ca trực",
                effectiveness_check="Effective",
            )
            frappe.db.commit()
            doc = frappe.get_doc("IMM CAPA Record", capa_name)
            self.assertEqual(doc.status, "Closed")
            self.assertEqual(doc.docstatus, 1)
        finally:
            doc = frappe.get_doc("IMM CAPA Record", capa_name)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc("IMM CAPA Record", capa_name, force=True,
                              ignore_permissions=True, delete_permanently=True)


# ─── S-10 ────────────────────────────────────────────────────────────────────

class TestS10_CriticalIncidentNotBlocked(FrappeTestCase):
    """S-10: Tạo Incident severity Critical + patient_affected=1 → warning (không block).

    Per `incident_report.py:_warn_byt_critical` → msgprint indicator orange.
    Save phải thành công (BR-INC-01 chỉ hard-block ở `before_submit`).
    """

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestSmokeCatS10-{_UID}",
            "category_name": f"Thiết bị Cấp cứu (smoke S-10) {_UID}",
        }).insert(ignore_permissions=True)
        cls._asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"_TestSmoke Canon CXDI S10-{_UID}",
            "asset_category": cls._cat.name,
            "manufacturer_sn": f"_TestSmokeSN-S10-{_UID}",
            "medical_device_class": "Class II",
            "risk_classification": "High",
            "purchase_date": "2023-05-12",
            "gross_purchase_amount": 980_000_000,
            "warranty_expiry_date": "2026-05-12",
            "in_service_date": "2023-05-18",
            "byt_reg_no": f"BYT-TB-2023-S10-{_UID}",
            "is_pm_required": 1,
            "pm_interval_days": 182,
            "lifecycle_status": "Active",
        })

    @classmethod
    def tearDownClass(cls):
        irs = frappe.get_all("Incident Report",
                              filters={"asset": cls._asset.name}, pluck="name")
        for ir in irs:
            d = frappe.get_doc("Incident Report", ir)
            if d.docstatus == 1:
                d.cancel()
            frappe.delete_doc("Incident Report", ir, force=True, ignore_permissions=True,
                              delete_permanently=True)
        purge_asset(cls._asset.name)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_s10_critical_with_patient_impact_saves_ok(self):
        ir = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": self._asset.name,
            "severity": "Critical",
            "incident_datetime": nowdate(),
            "description": "Máy X-quang Canon CXDI báo lỗi artifact dạng sọc sau di chuyển; "
                           "ảnh hưởng kết quả chụp 2 ca cấp cứu (smoke S-10).",
            "patient_affected": 1,
            "patient_impact_description": (
                "2 bệnh nhân phải chụp lại; không gây tổn hại trực tiếp nhưng kéo dài "
                "thời gian chẩn đoán ~25 phút mỗi ca."
            ),
        }).insert(ignore_permissions=True)
        try:
            self.assertTrue(ir.name.startswith("IR-"),
                            f"S-10: incident phải có naming IR-, got: {ir.name}")
            self.assertEqual(ir.docstatus, 0, "S-10: save không được auto-submit")
        finally:
            frappe.delete_doc("Incident Report", ir.name, force=True, ignore_permissions=True)


# ─── S-11 ────────────────────────────────────────────────────────────────────

class TestS11_CheckCapaOverdueScheduler(FrappeTestCase):
    """S-11: Chạy `check_capa_overdue` manual → không raise."""

    def test_check_capa_overdue_runs_without_error(self):
        from assetcore.services.imm00 import check_capa_overdue
        # Smoke: must not raise. Email backend trong test env = no-op.
        try:
            check_capa_overdue()
        except Exception as exc:  # pragma: no cover — smoke assertion
            self.fail(f"S-11: check_capa_overdue raised {type(exc).__name__}: {exc}")


# ─── S-13 ────────────────────────────────────────────────────────────────────

class TestS13_TechnicianScopeFilter(FrappeTestCase):
    """S-13: Technician không phải reporter/responsible → list count = 0 (permission_query).

    Per `permissions.incident_report_query` — technician roles chỉ thấy IR có
    `reported_by = current_user`. Tạo IR bởi Administrator → tech user query = 0.

    Dùng `Corrective User`: vừa có IR read DocPerm, vừa nằm trong
    `_TECHNICIAN_ROLES` (sau fix 2026-05-28) nên bị scope.
    """

    TECH_EMAIL = f"_test_tech_s13_{_UID}@nd1.hospital.vn"

    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestSmokeCatS13-{_UID}",
            "category_name": f"Thiết bị Hồi sức (smoke S-13) {_UID}",
        }).insert(ignore_permissions=True)
        cls._asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"_TestSmoke Asset S13-{_UID}",
            "asset_category": cls._cat.name,
            "manufacturer_sn": f"_TestSmokeSN-S13-{_UID}",
            "medical_device_class": "Class II",
            "risk_classification": "Medium",
            "purchase_date": "2024-02-10",
            "gross_purchase_amount": 250_000_000,
            "warranty_expiry_date": "2027-02-10",
            "in_service_date": "2024-02-15",
            "byt_reg_no": f"BYT-TB-2024-S13-{_UID}",
            "lifecycle_status": "Active",
        })
        # Admin tạo IR (reported_by = Administrator)
        cls._ir = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": cls._asset.name,
            "severity": "Medium",
            "incident_datetime": nowdate(),
            "description": "IR do admin báo cáo — tech khác không được thấy (smoke S-13)",
            "reported_by": "Administrator",
            "patient_affected": 0,
        }).insert(ignore_permissions=True)
        # Test user: System User với role 'PM User' (nằm trong _TECHNICIAN_ROLES)
        if not frappe.db.exists("User", cls.TECH_EMAIL):
            u = frappe.new_doc("User")
            u.email = cls.TECH_EMAIL
            u.first_name = "Smoke"
            u.last_name = "TechS13"
            u.user_type = "System User"
            u.enabled = 1
            u.send_welcome_email = 0
            u.append("roles", {"role": "Corrective User"})
            u.flags.ignore_permissions = True
            u.insert()
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if cls._ir and frappe.db.exists("Incident Report", cls._ir.name):
            frappe.delete_doc("Incident Report", cls._ir.name, force=True,
                              ignore_permissions=True)
        purge_asset(cls._asset.name)
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        if frappe.db.exists("User", cls.TECH_EMAIL):
            frappe.delete_doc("User", cls.TECH_EMAIL, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_s13_tech_user_sees_zero_others_incidents(self):
        frappe.set_user(self.TECH_EMAIL)
        try:
            rows = frappe.get_list(
                "Incident Report",
                filters={"name": self._ir.name},
                fields=["name"],
            )
            self.assertEqual(
                len(rows), 0,
                f"S-13: tech '{self.TECH_EMAIL}' không phải reporter, "
                f"phải bị permission_query lọc khỏi IR '{self._ir.name}'. "
                f"Got: {rows}"
            )
        finally:
            frappe.set_user("Administrator")
