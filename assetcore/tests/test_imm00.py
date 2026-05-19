# Copyright (c) 2026, AssetCore Team
"""IMM-00 foundation test suite.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm00
"""
import unittest
import frappe
from frappe.utils import nowdate, add_days


def setUpModule():
    """Seed master records required by AC Asset link validation."""
    frappe.set_user("Administrator")
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(ignore_permissions=True)
        frappe.db.commit()


def tearDownModule():
    """Remove UOM seed record created in setUpModule."""
    if frappe.db.exists("AC UOM", "Cái"):
        frappe.delete_doc("AC UOM", "Cái", force=True, ignore_permissions=True)
        frappe.db.commit()


class TestACAssetCategory(unittest.TestCase):
    def setUp(self):
        self.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Hô hấp & Hồi sức (ICU)",
            "description": "Máy thở, máy hút đờm, máy CPAP/BiPAP sử dụng tại khoa ICU và phòng mổ",
            "default_pm_required": 1,
            "default_pm_interval_days": 90,
            "default_calibration_required": 1,
            "default_calibration_interval_days": 365,
            "default_depreciation_method": "Straight Line",
            "total_depreciation_months": 120,
            "depreciation_frequency": "Yearly",
            "default_residual_value_pct": 5.0,
            "is_active": 1,
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Asset Category", self.cat.name, force=True, ignore_permissions=True)

    def test_category_created(self):
        self.assertTrue(frappe.db.exists("AC Asset Category", self.cat.name))

    def test_category_fields(self):
        doc = frappe.get_doc("AC Asset Category", self.cat.name)
        self.assertEqual(doc.default_pm_interval_days, 90)
        self.assertEqual(doc.default_calibration_interval_days, 365)


class TestACDepartment(unittest.TestCase):
    def setUp(self):
        self.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Hồi sức tích cực (ICU)",
            "department_code": "ICU",
            "phone": "028-3855-4269",
            "email": "icu@nd1.hospital.vn",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Department", self.dept.name, force=True, ignore_permissions=True)

    def test_department_created(self):
        self.assertTrue(frappe.db.exists("AC Department", self.dept.name))

    def test_naming_series(self):
        # AC Department is a tree DocType — Frappe uses department_name as primary key
        self.assertEqual(self.dept.name, self.dept.department_name)


class TestACLocation(unittest.TestCase):
    def setUp(self):
        self.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "Phòng ICU 3 — Tầng 3, Nhà A",
            "location_type": "Room",
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Location", self.loc.name, force=True, ignore_permissions=True)

    def test_location_created(self):
        self.assertTrue(frappe.db.exists("AC Location", self.loc.name))

    def test_naming_series(self):
        self.assertTrue(self.loc.name.startswith("AC-LOC-"))


class TestACSupplier(unittest.TestCase):
    def setUp(self):
        self.sup = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": "Công ty TNHH Dräger Medical Vietnam",
            "supplier_group": "Manufacturer",
            "vendor_type": "Manufacturer",
            "country": "Vietnam",
            "tax_id": "0312345678",
            "address": "10 Nguyễn Đình Chiểu, Phường Đa Kao, Quận 1, TPHCM",
            "phone": "028-3824-5566",
            "email_id": "nv.phong@drager.com.vn",
            "local_representative": "Nguyễn Văn Phong",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Supplier", self.sup.name, force=True, ignore_permissions=True)

    def test_supplier_created(self):
        self.assertTrue(frappe.db.exists("AC Supplier", self.sup.name))

    def test_naming_series(self):
        self.assertTrue(self.sup.name.startswith("AC-SUP-"))


class TestIMMDeviceModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Chẩn đoán Hình ảnh",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)

    def setUp(self):
        self.model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": "Máy thở Dräger Evita V500",
            "manufacturer": "Dräger Medical GmbH",
            "medical_device_class": "Class III",
            "risk_classification": "Critical",
            "asset_category": self._cat.name,
            "country_of_origin": "Germany",
            "expected_lifespan_years": 10,
            "gmdn_code": "56987",
            "gmdn_term": "Ventilator, continuous, for use with adults/children",
            "registration_required": 1,
            "is_pm_required": 1,
            "pm_interval_days": 182,
            "pm_alert_days": 14,
            "is_calibration_required": 1,
            "calibration_interval_days": 365,
            "calibration_alert_days": 30,
            "default_calibration_type": "External",
            "power_supply": "220V/50Hz",
            "weight_kg": 25.5,
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("IMM Device Model", self.model.name, force=True, ignore_permissions=True)

    def test_model_created(self):
        self.assertTrue(frappe.db.exists("IMM Device Model", self.model.name))


class TestIMSLAPolicy(unittest.TestCase):
    def test_sla_policies_loaded(self):
        """Fixture SLA policies must exist after bench migrate."""
        count = frappe.db.count("IMM SLA Policy", {"is_active": 1})
        self.assertGreaterEqual(count, 5, "Expected at least 5 active SLA policies from fixtures")

    def test_resolve_default_policy(self):
        from assetcore.services.imm00 import get_sla_policy
        policy = get_sla_policy("P1", "Critical")
        self.assertIsNotNone(policy)
        self.assertEqual(policy.get("response_time_minutes"), 15)

    def test_resolve_fallback_to_default(self):
        from assetcore.services.imm00 import get_sla_policy
        # Non-existent combo → fallback to is_default for that priority
        policy = get_sla_policy("P3", "Critical")
        self.assertIsNotNone(policy)


class TestACAsset(unittest.TestCase):
    """Full asset lifecycle: create → transition → validate."""

    @classmethod
    def setUpClass(cls):
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Máy thở & Hỗ trợ hô hấp",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)

        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Hồi sức tích cực (ICU)",
        }).insert(ignore_permissions=True)

        cls.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "Phòng ICU 3 — Tầng 3, Nhà A",
            "location_type": "Room",
        }).insert(ignore_permissions=True)

        cls.sup = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": "Công ty TNHH Dräger Medical Vietnam",
            "supplier_group": "Manufacturer",
            "vendor_type": "Manufacturer",
            "country": "Vietnam",
            "tax_id": "0312345678",
            "address": "10 Nguyễn Đình Chiểu, Phường Đa Kao, Quận 1, TPHCM",
            "phone": "028-3824-5566",
            "email_id": "nv.phong@drager.com.vn",
            "local_representative": "Nguyễn Văn Phong",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        for dt, name in [
            ("AC Asset Category", cls.cat.name),
            ("AC Department", cls.dept.name),
            ("AC Location", cls.loc.name),
            ("AC Supplier", cls.sup.name),
        ]:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)

    def _make_asset(self, suffix=""):
        # Use in_install bypass to insert with a non-initial lifecycle_status
        # (AC Asset Lifecycle workflow blocks direct "Draft" → "Commissioned").
        tag = suffix.lstrip("-") or "0001"
        return _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Dräger Evita V500 — ICU{suffix}",
            "asset_category": self.cat.name,
            "department": self.dept.name,
            "location": self.loc.name,
            "supplier": self.sup.name,
            "purchase_date": "2023-03-15",
            "gross_purchase_amount": 850_000_000,
            "warranty_expiry_date": "2026-03-15",
            "in_service_date": "2023-03-20",
            "commissioning_date": "2023-03-20",
            "manufacturer_sn": f"EVT-2023-{tag}",
            "medical_device_class": "Class III",
            "risk_classification": "Critical",
            "gmdn_code": "56987",
            "byt_reg_no": "BYT-TB-2022-00891",
            "byt_reg_expiry": "2027-12-31",
            "lifecycle_status": "Commissioned",
            "is_pm_required": 1,
            "pm_interval_days": 182,
            "is_calibration_required": 1,
            "calibration_interval_days": 365,
            "useful_life_years": 10,
            "depreciation_method": "Straight Line",
            "total_depreciation_months": 120,
            "residual_value": 42_500_000,
        })

    def test_asset_created_with_naming_series(self):
        asset = self._make_asset("-create")
        try:
            self.assertTrue(asset.name.startswith("AC-ASSET-"))
            self.assertEqual(asset.lifecycle_status, "Commissioned")
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)

    def test_transition_status_commissioned_to_active(self):
        from assetcore.services.imm00 import transition_asset_status
        asset = self._make_asset("-trans")
        try:
            transition_asset_status(asset.name, "Active", actor="Administrator", reason="Thiết bị đã hoàn thành nghiệm thu và sẵn sàng đưa vào vận hành lâm sàng")
            frappe.db.commit()
            asset.reload()
            self.assertEqual(asset.lifecycle_status, "Active")
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)

    def test_transition_creates_lifecycle_event(self):
        from assetcore.services.imm00 import transition_asset_status
        asset = self._make_asset("-event")
        try:
            before = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
            transition_asset_status(asset.name, "Active", actor="Administrator")
            frappe.db.commit()
            after = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
            self.assertGreater(after, before)
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)

    def test_cannot_operate_decommissioned_asset(self):
        from assetcore.services.imm00 import transition_asset_status, validate_asset_for_operations
        asset = self._make_asset("-decom")
        try:
            transition_asset_status(asset.name, "Decommissioned", actor="Administrator", reason="Thiết bị hết niên hạn sử dụng theo quy định BYT; đã lập biên bản thanh lý")
            frappe.db.commit()
            with self.assertRaises(frappe.ValidationError):
                validate_asset_for_operations(asset.name)
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)

    def test_decommission_suspends_pm_schedule(self):
        from assetcore.services.imm00 import transition_asset_status
        asset = self._make_asset("-pm")
        try:
            transition_asset_status(asset.name, "Decommissioned", actor="Administrator")
            frappe.db.commit()
            asset.reload()
            self.assertEqual(asset.is_pm_required, 0)
        finally:
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)


def _insert_asset_bypass_workflow(data: dict):
    """Insert AC Asset bypassing workflow validation (for test fixtures)."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


class TestIMMCAPARecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clean up leftovers from prior failed runs.
        for a in frappe.get_all("AC Asset", filters={"asset_name": "Monitor Mindray BeneView T9 — ICU"},
                                fields=["name"]):
            frappe.delete_doc("AC Asset", a.name, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset Category", "Thiết bị Theo dõi Bệnh nhân"):
            frappe.delete_doc("AC Asset Category", "Thiết bị Theo dõi Bệnh nhân",
                              force=True, ignore_permissions=True)
        frappe.db.commit()

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Theo dõi Bệnh nhân",
        }).insert(ignore_permissions=True)
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": "Monitor Mindray BeneView T9 — ICU",
            "asset_category": cls.cat.name,
            "manufacturer_sn": "MBT9-2024-CAPA01",
            "medical_device_class": "Class II",
            "risk_classification": "High",
            "purchase_date": "2024-01-20",
            "gross_purchase_amount": 320_000_000,
            "warranty_expiry_date": "2027-01-20",
            "in_service_date": "2024-01-25",
            "byt_reg_no": "BYT-TB-2023-01122",
            "is_pm_required": 1,
            "pm_interval_days": 90,
            "lifecycle_status": "Active",
        })

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name, force=True, ignore_permissions=True)

    def test_create_capa(self):
        from assetcore.services.imm00 import create_capa
        name = create_capa(
            asset=self.asset.name,
            source_type="Non-Conformance",
            source_ref="",
            severity="Minor",
            description="Van PEEP bị mòn do vượt chu kỳ thay thế khuyến nghị (>18 tháng). Hành động: thay van mới theo BOM Dräger. Phòng ngừa: cập nhật lịch bảo dưỡng Q6.",
            responsible="Administrator",
            due_days=30,
        )
        frappe.db.commit()
        self.assertTrue(frappe.db.exists("IMM CAPA Record", name))
        frappe.delete_doc("IMM CAPA Record", name, force=True, ignore_permissions=True)

    def test_close_capa(self):
        from assetcore.services.imm00 import create_capa, close_capa
        name = create_capa(
            asset=self.asset.name,
            source_type="Non-Conformance",
            source_ref="",
            severity="Minor",
            description="Cảm biến SpO2 lỏng tiếp điểm, kết quả đo nhiễu. Đã kiểm tra và siết lại đầu nối; hiệu chuẩn lại theo QP-CAL-07.",
            responsible="Administrator",
            due_days=7,
        )
        frappe.db.commit()
        close_capa(
            capa_name=name,
            root_cause="Lỏng đầu nối cảm biến do rung động khi di chuyển thiết bị giữa các phòng",
            corrective_action="Siết lại và dán cố định cáp cảm biến; ghi nhận vào hồ sơ thiết bị",
            preventive_action="Bổ sung checklist kiểm tra đầu nối trước mỗi ca vận hành",
            effectiveness_check="Effective",
        )
        frappe.db.commit()
        doc = frappe.get_doc("IMM CAPA Record", name)
        self.assertEqual(doc.status, "Closed")
        doc.cancel()
        frappe.delete_doc("IMM CAPA Record", name, force=True, ignore_permissions=True)


class TestIMMauditTrail(unittest.TestCase):
    """Audit trail immutability and hash chain."""

    @classmethod
    def setUpClass(cls):
        # Clean up leftovers from prior failed runs.
        for a in frappe.get_all("AC Asset", filters={"asset_name": "Máy siêu âm Philips EPIQ 7 — CĐHA"},
                                fields=["name"]):
            frappe.delete_doc("AC Asset", a.name, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset Category", "Thiết bị Phẫu thuật"):
            frappe.delete_doc("AC Asset Category", "Thiết bị Phẫu thuật",
                              force=True, ignore_permissions=True)
        frappe.db.commit()

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Phẫu thuật",
        }).insert(ignore_permissions=True)
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": "Máy siêu âm Philips EPIQ 7 — CĐHA",
            "asset_category": cls.cat.name,
            "manufacturer_sn": "EPQ7-2022-AUDIT01",
            "medical_device_class": "Class II",
            "risk_classification": "High",
            "purchase_date": "2022-08-10",
            "gross_purchase_amount": 1_250_000_000,
            "warranty_expiry_date": "2025-08-10",
            "in_service_date": "2022-08-20",
            "byt_reg_no": "BYT-TB-2021-00445",
            "byt_reg_expiry": "2026-12-31",
            "gmdn_code": "33587",
            "useful_life_years": 10,
            "depreciation_method": "Straight Line",
            "total_depreciation_months": 120,
            "residual_value": 62_500_000,
            "is_pm_required": 1,
            "pm_interval_days": 365,
            "is_calibration_required": 1,
            "calibration_interval_days": 365,
            "lifecycle_status": "Commissioned",
        })

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name, force=True, ignore_permissions=True)

    def test_audit_trail_created_on_transition(self):
        from assetcore.services.imm00 import transition_asset_status
        before = frappe.db.count("IMM Audit Trail", {"asset": self.asset.name})
        transition_asset_status(self.asset.name, "Active", actor="Administrator", reason="Thiết bị được nghiệm thu và đưa vào sử dụng chính thức tại Khoa CĐHA")
        frappe.db.commit()
        after = frappe.db.count("IMM Audit Trail", {"asset": self.asset.name})
        self.assertGreater(after, before)

    def test_audit_trail_cannot_be_deleted(self):
        entries = frappe.get_list("IMM Audit Trail", filters={"asset": self.asset.name}, fields=["name"])
        if not entries:
            self.skipTest("No audit trail entries to test deletion block")
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("IMM Audit Trail", entries[0]["name"], ignore_permissions=True)

    def test_verify_chain_valid(self):
        from assetcore.services.imm00 import verify_audit_chain
        result = verify_audit_chain(self.asset.name)
        self.assertTrue(result.get("valid"), f"Chain invalid: {result}")


class TestIncidentReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clean up any leftover fixtures from a prior failed run.
        for asset in frappe.get_all("AC Asset", filters={"asset_name": "Máy X-quang Canon CXDI-Elite — Khoa CĐHA"},
                                    fields=["name"]):
            frappe.delete_doc("AC Asset", asset.name, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset Category", "Thiết bị Cấp cứu & Tái hồi"):
            frappe.delete_doc("AC Asset Category", "Thiết bị Cấp cứu & Tái hồi",
                              force=True, ignore_permissions=True)
        frappe.db.commit()

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Cấp cứu & Tái hồi",
        }).insert(ignore_permissions=True)
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": "Máy X-quang Canon CXDI-Elite — Khoa CĐHA",
            "asset_category": cls.cat.name,
            "manufacturer_sn": "CXD-2023-IR01",
            "medical_device_class": "Class II",
            "risk_classification": "High",
            "purchase_date": "2023-05-12",
            "gross_purchase_amount": 980_000_000,
            "warranty_expiry_date": "2026-05-12",
            "in_service_date": "2023-05-18",
            "byt_reg_no": "BYT-TB-2022-00678",
            "byt_reg_expiry": "2027-06-30",
            "gmdn_code": "40939",
            "useful_life_years": 10,
            "depreciation_method": "Straight Line",
            "total_depreciation_months": 120,
            "residual_value": 49_000_000,
            "is_pm_required": 1,
            "pm_interval_days": 182,
            "is_calibration_required": 1,
            "calibration_interval_days": 365,
            "lifecycle_status": "Active",
        })

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset", cls.asset.name, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name, force=True, ignore_permissions=True)

    def test_create_incident(self):
        ir = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": self.asset.name,
            "severity": "Medium",
            "incident_title": "Máy X-quang hiển thị artifact dạng sọc ngang sau khi di chuyển thiết bị",
            "incident_datetime": nowdate(),
            "description": "Thiết bị báo lỗi artifact dạng sọc ngang ảnh hưởng chất lượng chẩn đoán. Sự cố xảy ra sau khi di chuyển máy từ phòng CĐHA-1 sang CĐHA-2 lúc 08:30 ngày vận hành.",
            "patient_affected": 0,
        }).insert(ignore_permissions=True)
        self.assertTrue(ir.name.startswith("IR-"))
        frappe.delete_doc("Incident Report", ir.name, force=True, ignore_permissions=True)

    def test_patient_impact_required_when_patient_affected(self):
        doc = frappe.new_doc("Incident Report")
        doc.update({
            "asset": self.asset.name,
            "severity": "Critical",
            "incident_title": "Máy thở báo lỗi E-001 — áp lực đường thở tăng bất thường",
            "incident_datetime": nowdate(),
            "description": "Máy thở Dräger Evita V500 tại ICU giường số 5 báo lỗi E-001 lúc 02:15, bệnh nhân thở thụ động, áp lực đường thở tăng vượt ngưỡng cảnh báo. Đã chuyển sang máy dự phòng và tạm dừng sử dụng thiết bị.",
            "patient_affected": 1,
            "patient_impact": "",  # missing — should fail
        })
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)


class TestUserRoleManagement(unittest.TestCase):
    """Regression: update_user_info phải persist imm_roles vào tabHas Role.

    Bug history: `_sync_imm_roles` từng dùng `user_doc.add_roles(*roles)` —
    method này gọi `self.save()` mà không set `flags.ignore_permissions = True`,
    nên Frappe DocPerm check fail SILENT và rollback role changes (FE thấy 200
    OK + toast thành công nhưng DB không thay đổi). Fix: chỉ mutate child
    table trong memory, để `_save_user` save 1 lần với ignore_permissions.
    """

    TEST_EMAIL = "ky.thuat.vien.test@nd1.hospital.vn"

    @classmethod
    def setUpClass(cls):
        # Tạo test user (system user)
        if not frappe.db.exists("User", cls.TEST_EMAIL):
            u = frappe.new_doc("User")
            u.email = cls.TEST_EMAIL
            u.first_name = "Role"
            u.last_name = "Test"
            u.user_type = "System User"
            u.enabled = 1
            u.send_welcome_email = 0
            u.append("roles", {"role": "IMM Technician"})
            u.flags.ignore_permissions = True
            u.insert()
        # Đảm bảo session là admin để qua _assert_admin
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        if frappe.db.exists("User", cls.TEST_EMAIL):
            frappe.delete_doc("User", cls.TEST_EMAIL, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _db_roles(self) -> list[str]:
        return sorted(
            r.role for r in frappe.db.sql(
                "SELECT role FROM `tabHas Role` WHERE parent=%s AND role LIKE 'IMM%%'",
                (self.TEST_EMAIL,), as_dict=True
            )
        )

    def test_update_user_roles_persists_to_has_role_table(self):
        """Gán roles mới qua update_user_info → DB phải có đúng các role đó."""
        import json
        from assetcore.api.user import update_user_info

        frappe.local.form_dict = frappe._dict({
            "user": self.TEST_EMAIL,
            "imm_roles": json.dumps([
                {"role": "IMM Workshop Lead"},
                {"role": "IMM QA Officer"},
            ]),
        })
        result = update_user_info()
        frappe.db.commit()

        self.assertTrue(result.get("success"), f"update_user_info failed: {result}")
        self.assertEqual(self._db_roles(), ["IMM QA Officer", "IMM Workshop Lead"])

    def test_update_user_roles_clears_old_roles(self):
        """Gán roles mới phải XÓA các IMM role cũ không nằm trong payload."""
        import json
        from assetcore.api.user import update_user_info

        # Seed: 3 roles
        frappe.local.form_dict = frappe._dict({
            "user": self.TEST_EMAIL,
            "imm_roles": json.dumps([
                {"role": "IMM Technician"},
                {"role": "IMM Storekeeper"},
                {"role": "IMM Document Officer"},
            ]),
        })
        update_user_info()
        frappe.db.commit()
        self.assertEqual(
            self._db_roles(),
            ["IMM Document Officer", "IMM Storekeeper", "IMM Technician"],
        )

        # Replace: chỉ giữ 1
        frappe.local.form_dict = frappe._dict({
            "user": self.TEST_EMAIL,
            "imm_roles": json.dumps([{"role": "IMM Clinical User"}]),
        })
        update_user_info()
        frappe.db.commit()
        self.assertEqual(self._db_roles(), ["IMM Clinical User"])

    def test_non_admin_cannot_set_roles(self):
        """Non-admin user phải bị reject 403 khi gọi update_user_info."""
        import json
        from assetcore.api.user import update_user_info

        # Tạo non-admin user
        guest_email = "nhan.vien.guest.test@nd1.hospital.vn"
        if not frappe.db.exists("User", guest_email):
            u = frappe.new_doc("User")
            u.email = guest_email
            u.first_name = "Guest"
            u.user_type = "System User"
            u.enabled = 1
            u.send_welcome_email = 0
            u.append("roles", {"role": "IMM Clinical User"})  # non-admin role
            u.flags.ignore_permissions = True
            u.insert()
            frappe.db.commit()

        try:
            frappe.set_user(guest_email)
            frappe.local.form_dict = frappe._dict({
                "user": self.TEST_EMAIL,
                "imm_roles": json.dumps([{"role": "IMM System Admin"}]),
            })
            result = update_user_info()
            self.assertFalse(result.get("success"))
            self.assertEqual(result.get("http_status"), 403)
        finally:
            frappe.set_user("Administrator")
            frappe.delete_doc("User", guest_email, force=True, ignore_permissions=True)
            frappe.db.commit()


def run_all():
    """Convenience runner for bench console."""
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
