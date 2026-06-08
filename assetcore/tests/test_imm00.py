# Copyright (c) 2026, AssetCore Team
"""IMM-00 foundation test suite.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm00
"""
import re
import unittest
import frappe
from frappe.utils import nowdate, add_days, flt, getdate

# IMM-14 GATE (BR-14-W2-01): asset chỉ vào Decommissioned qua closure flow.
from assetcore.tests._asset_cleanup import decommission_via_closure


# Track whether this module created the "Cái" UOM so tearDownModule never
# deletes a pre-existing (real, shared) UOM that other records depend on.
_uom_created = False


def setUpModule():
    """Seed master records required by AC Asset link validation."""
    global _uom_created
    frappe.set_user("Administrator")
    if not frappe.db.exists("AC UOM", "Cái"):
        frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(ignore_permissions=True)
        frappe.db.commit()
        _uom_created = True


def tearDownModule():
    """Remove the UOM seed only if setUpModule created it (else it is shared real data)."""
    if _uom_created and frappe.db.exists("AC UOM", "Cái"):
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
        # Use a _Test-prefixed department_code so the fixture never collides
        # with real seeded departments (e.g. the production "ICU" dept used by
        # asset TS-2025-VEN-001). AC Department uses department_code as the PK.
        self.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_Test Khoa Hồi sức tích cực (ICU)",
            "department_code": "_TEST-ICU",
            "phone": "028-3855-4269",
            "email": "icu@nd1.hospital.vn",
            "is_active": 1,
        }).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.delete_doc("AC Department", self.dept.name, force=True, ignore_permissions=True)

    def test_department_created(self):
        self.assertTrue(frappe.db.exists("AC Department", self.dept.name))

    def test_naming_series(self):
        # AC Department uses department_code as the primary key (name) when the
        # user supplies one (see ACDepartment.autoname).
        self.assertEqual(self.dept.name, self.dept.department_code)


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
            _purge_asset(asset.name)

    def test_transition_status_commissioned_to_active(self):
        from assetcore.services.imm00 import transition_asset_status
        asset = self._make_asset("-trans")
        try:
            transition_asset_status(asset.name, "Active", actor="Administrator", reason="Thiết bị đã hoàn thành nghiệm thu và sẵn sàng đưa vào vận hành lâm sàng")
            frappe.db.commit()
            asset.reload()
            self.assertEqual(asset.lifecycle_status, "Active")
        finally:
            _purge_asset(asset.name)

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
            _purge_asset(asset.name)

    def test_cannot_operate_decommissioned_asset(self):
        from assetcore.services.imm00 import validate_asset_for_operations
        asset = self._make_asset("-decom")
        try:
            decommission_via_closure(asset.name)
            with self.assertRaises(frappe.ValidationError):
                validate_asset_for_operations(asset.name)
        finally:
            _purge_asset(asset.name)

    def test_decommission_suspends_pm_schedule(self):
        asset = self._make_asset("-pm")
        try:
            decommission_via_closure(asset.name)
            asset.reload()
            self.assertEqual(asset.is_pm_required, 0)
        finally:
            _purge_asset(asset.name)


def _insert_asset_bypass_workflow(data: dict):
    """Insert AC Asset bypassing workflow validation (for test fixtures)."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _purge_asset(asset_name: str) -> None:
    """Force-delete an AC Asset for fixture cleanup (LL-TEST-17).

    ``AC Asset.on_trash`` (WR-03) blocks hard-delete while audit / lifecycle /
    operational records exist, and ``force=True`` does NOT bypass a custom
    ``on_trash``. ``IMM Audit Trail`` and ``Asset Lifecycle Event`` additionally
    throw in their own ``on_trash`` (ISO 13485:7.5.9 / append-only), so they must
    be purged via raw SQL. Operational dependents have no guard → ORM delete.
    """
    if not frappe.db.exists("AC Asset", asset_name):
        return
    # 1) Append-only records — raw SQL (ORM delete always throws, even force=True)
    frappe.db.sql(
        "DELETE FROM `tabIMM Audit Trail` "
        "WHERE asset=%s OR (ref_doctype='AC Asset' AND ref_name=%s)",
        (asset_name, asset_name),
    )
    frappe.db.sql("DELETE FROM `tabAsset Lifecycle Event` WHERE asset=%s", (asset_name,))
    # 2) Operational dependents — ORM (cancel submitted docs first)
    for dt, fld in [
        ("PM Work Order", "asset_ref"),
        ("CM Work Order", "asset_ref"),
        ("IMM Calibration Schedule", "asset"),
        ("IMM Calibration Order", "asset_ref"),
        ("Incident Report", "asset"),
        ("Asset Document", "asset_ref"),
        ("Asset Transfer", "asset"),
        ("AC Asset Downtime Log", "asset"),
    ]:
        if not frappe.db.table_exists(dt) or not frappe.db.has_column(dt, fld):
            continue
        for child in frappe.get_all(dt, filters={fld: asset_name}, pluck="name"):
            doc = frappe.get_doc(dt, child)
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc(dt, child, force=True, ignore_permissions=True,
                              delete_permanently=True)
    frappe.db.commit()
    # 3) Asset now deletes cleanly
    frappe.delete_doc("AC Asset", asset_name, force=True, ignore_permissions=True)


def _purge_category(category_name: str) -> None:
    """Delete a leftover AC Asset Category by its business field (LL-TEST-9).

    ``AC Asset Category`` is autonamed (``CAT-####``) so ``frappe.db.exists(dt,
    category_name)`` never matches — the stale row survives and the unique
    ``category_name`` index then blocks re-insert. Look up by the field instead.
    """
    name = frappe.db.get_value("AC Asset Category", {"category_name": category_name}, "name")
    if name:
        frappe.delete_doc("AC Asset Category", name, force=True, ignore_permissions=True)
        frappe.db.commit()


class TestIMMCAPARecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clean up leftovers from prior failed runs.
        for a in frappe.get_all("AC Asset", filters={"asset_name": "Monitor Mindray BeneView T9 — ICU"},
                                fields=["name"]):
            _purge_asset(a.name)
        _purge_category("Thiết bị Theo dõi Bệnh nhân")
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
        _purge_asset(cls.asset.name)
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

    # ── BR-00-26 — CAPA effectiveness gate (round 12, RC-CAPA-EFF) ────────────
    # SoT predicate assert_capa_effectiveness_gate: cả close_capa (legacy) lẫn
    # capa_record_validate (status=='Closed') gọi CÙNG cổng. effectiveness_check
    # null/rỗng → FIN-007 (VR-06); != 'Effective' → FIN-007 (VR-07).

    def _new_open_capa(self, sn_suffix: str) -> str:
        from assetcore.services.imm00 import create_capa
        name = create_capa(
            asset=self.asset.name,
            source_type="Non-Conformance",
            source_ref="",
            severity="Minor",
            description=(
                "Bơm tiêm điện báo lỗi lưu lượng ngắt quãng khi truyền tốc độ thấp; "
                "cần phân tích nguyên nhân và khắc phục theo QP-CM-03 — case " + sn_suffix
            ),
            responsible="Administrator",
            due_days=7,
        )
        frappe.db.commit()
        return name

    def _purge_capa(self, name: str) -> None:
        doc = frappe.get_doc("IMM CAPA Record", name)
        if doc.docstatus == 1:
            doc.cancel()
        frappe.delete_doc("IMM CAPA Record", name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_close_capa_blocks_when_effectiveness_none(self):
        """AC-1 / TC-CAPA-GATE-01: close_capa(effectiveness_check=None) → FIN-007 (VR-06).

        CAPA KHÔNG đổi sang Closed, KHÔNG submit (docstatus vẫn 0)."""
        from assetcore.services.imm00 import close_capa
        from assetcore.services.shared import ServiceError, ErrorCode
        name = self._new_open_capa("none")
        try:
            with self.assertRaises(ServiceError) as ctx:
                close_capa(
                    capa_name=name,
                    root_cause="Bo mạch cảm biến áp suất nhiễu do ẩm",
                    corrective_action="Thay cụm cảm biến + hiệu chuẩn lại",
                    preventive_action="Bổ sung kiểm tra độ ẩm buồng đặt máy",
                    effectiveness_check=None,
                )
            self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
            self.assertEqual(ctx.exception.message_code, "FIN-007")
            self.assertIn("VR-06", ctx.exception.message)
            doc = frappe.get_doc("IMM CAPA Record", name)
            self.assertNotEqual(doc.status, "Closed")
            self.assertEqual(doc.docstatus, 0)
        finally:
            self._purge_capa(name)

    def test_close_capa_blocks_when_not_effective(self):
        """AC-2 / TC-CAPA-GATE-02: close_capa('Not Effective') → FIN-007 (VR-07)."""
        from assetcore.services.imm00 import close_capa
        from assetcore.services.shared import ServiceError, ErrorCode
        name = self._new_open_capa("noteff")
        try:
            with self.assertRaises(ServiceError) as ctx:
                close_capa(
                    capa_name=name,
                    root_cause="Bo mạch cảm biến áp suất nhiễu do ẩm",
                    corrective_action="Thay cụm cảm biến + hiệu chuẩn lại",
                    preventive_action="Bổ sung kiểm tra độ ẩm buồng đặt máy",
                    effectiveness_check="Not Effective",
                )
            self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
            self.assertEqual(ctx.exception.message_code, "FIN-007")
            self.assertIn("VR-07", ctx.exception.message)
            doc = frappe.get_doc("IMM CAPA Record", name)
            self.assertNotEqual(doc.status, "Closed")
            self.assertEqual(doc.docstatus, 0)
        finally:
            self._purge_capa(name)

    def test_close_capa_blocks_when_partially_effective(self):
        """AC-2 / TC-CAPA-GATE-02b: close_capa('Partially Effective') → FIN-007 (VR-07)."""
        from assetcore.services.imm00 import close_capa
        from assetcore.services.shared import ServiceError
        name = self._new_open_capa("parteff")
        try:
            with self.assertRaises(ServiceError) as ctx:
                close_capa(
                    capa_name=name,
                    root_cause="Bo mạch cảm biến áp suất nhiễu do ẩm",
                    corrective_action="Thay cụm cảm biến + hiệu chuẩn lại",
                    preventive_action="Bổ sung kiểm tra độ ẩm buồng đặt máy",
                    effectiveness_check="Partially Effective",
                )
            self.assertEqual(ctx.exception.message_code, "FIN-007")
            doc = frappe.get_doc("IMM CAPA Record", name)
            self.assertNotEqual(doc.status, "Closed")
            self.assertEqual(doc.docstatus, 0)
        finally:
            self._purge_capa(name)

    def test_close_capa_audit_on_effective(self):
        """AC-3 / TC-CAPA-GATE-03: happy path 'Effective' → Closed+submitted + Audit Trail.

        change_summary có effectiveness (Vietnamese). KHÔNG regress test_close_capa."""
        from assetcore.services.imm00 import close_capa
        name = self._new_open_capa("eff")
        try:
            before = frappe.db.count(
                "IMM Audit Trail", {"ref_name": name, "event_type": "CAPA"})
            close_capa(
                capa_name=name,
                root_cause="Bo mạch cảm biến áp suất nhiễu do ẩm",
                corrective_action="Thay cụm cảm biến + hiệu chuẩn lại",
                preventive_action="Bổ sung kiểm tra độ ẩm buồng đặt máy",
                effectiveness_check="Effective",
            )
            frappe.db.commit()
            doc = frappe.get_doc("IMM CAPA Record", name)
            self.assertEqual(doc.status, "Closed")
            self.assertTrue(doc.closed_date)
            self.assertEqual(doc.docstatus, 1)
            after = frappe.db.count(
                "IMM Audit Trail", {"ref_name": name, "event_type": "CAPA"})
            self.assertGreater(after, before)
        finally:
            self._purge_capa(name)

    def test_capa_validate_fires_gate_regardless_workflow_state(self):
        """AC-4 / TC-CAPA-GATE-04: validate path fires gate khi status=='Closed' BẤT KỂ
        workflow_state. effectiveness rỗng → VR-06; 'Not Effective' → VR-07."""
        name = self._new_open_capa("validate")
        try:
            doc = frappe.get_doc("IMM CAPA Record", name)
            doc.root_cause = "Bo mạch cảm biến áp suất nhiễu do ẩm"
            doc.corrective_action = "Thay cụm cảm biến + hiệu chuẩn lại"
            doc.preventive_action = "Bổ sung kiểm tra độ ẩm buồng đặt máy"
            doc.workflow_state = "Verification"   # KHÁC 'Closed' — bỏ điều kiện kép
            doc.status = "Closed"
            doc.effectiveness_check = None
            with self.assertRaises(frappe.exceptions.ValidationError):
                doc.save(ignore_permissions=True)
            # 'Not Effective' cũng phải bị chặn ở validate (VR-07 mới)
            doc2 = frappe.get_doc("IMM CAPA Record", name)
            doc2.root_cause = "Bo mạch cảm biến áp suất nhiễu do ẩm"
            doc2.corrective_action = "Thay cụm cảm biến + hiệu chuẩn lại"
            doc2.preventive_action = "Bổ sung kiểm tra độ ẩm buồng đặt máy"
            doc2.workflow_state = "Verification"
            doc2.status = "Closed"
            doc2.effectiveness_check = "Not Effective"
            with self.assertRaises(frappe.exceptions.ValidationError):
                doc2.save(ignore_permissions=True)
        finally:
            self._purge_capa(name)

    def test_capa_effectiveness_gate_single_sot(self):
        """AC-1/AC-5 / TC-CAPA-GATE-05: SoT predicate — cùng từ chối 'Not Effective'
        và cùng chấp nhận 'Effective'. Predicate thuần, no DB write, idempotent."""
        from assetcore.services.imm00 import assert_capa_effectiveness_gate
        from assetcore.services.shared import ServiceError

        class _Stub:
            def __init__(self, ec):
                self.effectiveness_check = ec

        for bad in (None, "", "Not Effective", "Partially Effective"):
            with self.assertRaises(ServiceError) as ctx:
                assert_capa_effectiveness_gate(_Stub(bad))
            self.assertEqual(ctx.exception.message_code, "FIN-007")
        # Effective → no raise (returns None)
        self.assertIsNone(assert_capa_effectiveness_gate(_Stub("Effective")))

    def test_capa_open_count_unchanged_after_gate(self):
        """AC-5 / TC-CAPA-GATE-06: CAPA chưa-Effective vẫn vào _open_capa_filter count.
        Gate KHÔNG đổi membership 'mở' → KPI capa_open bất biến."""
        from assetcore.services.imm00 import _open_capa_filter, close_capa
        from assetcore.services.shared import ServiceError
        name = self._new_open_capa("count")
        try:
            filt = {"asset": self.asset.name, **_open_capa_filter()}
            before = frappe.db.count("IMM CAPA Record", filt)
            # Cố đóng nhưng chưa effective → bị chặn, không đổi membership.
            with self.assertRaises(ServiceError):
                close_capa(
                    capa_name=name,
                    root_cause="Bo mạch cảm biến áp suất nhiễu do ẩm",
                    corrective_action="Thay cụm cảm biến + hiệu chuẩn lại",
                    preventive_action="Bổ sung kiểm tra độ ẩm buồng đặt máy",
                    effectiveness_check=None,
                )
            after = frappe.db.count("IMM CAPA Record", filt)
            self.assertEqual(before, after)
            # CAPA bị chặn vẫn đếm 'mở' (status NOT IN Closed).
            self.assertGreaterEqual(after, 1)
        finally:
            self._purge_capa(name)


class TestIMMauditTrail(unittest.TestCase):
    """Audit trail immutability and hash chain."""

    @classmethod
    def setUpClass(cls):
        # Clean up leftovers from prior failed runs.
        for a in frappe.get_all("AC Asset", filters={"asset_name": "Máy siêu âm Philips EPIQ 7 — CĐHA"},
                                fields=["name"]):
            _purge_asset(a.name)
        _purge_category("Thiết bị Phẫu thuật")
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
        _purge_asset(cls.asset.name)
        frappe.delete_doc("AC Asset Category", cls.cat.name, force=True, ignore_permissions=True)

    def test_audit_trail_created_on_transition(self):
        from assetcore.services.imm00 import transition_asset_status
        before = frappe.db.count("IMM Audit Trail", {"asset": self.asset.name})
        transition_asset_status(self.asset.name, "Active", actor="Administrator", reason="Thiết bị được nghiệm thu và đưa vào sử dụng chính thức tại Khoa CĐHA")
        frappe.db.commit()
        after = frappe.db.count("IMM Audit Trail", {"asset": self.asset.name})
        self.assertGreater(after, before)

    def test_audit_trail_cannot_be_deleted(self):
        # SEC-02 / BR-00-03: seed a deterministic entry rather than relying on
        # test-method ordering (this test sorts before any transition test, so
        # the asset would otherwise have zero entries and the assertion skip).
        from assetcore.services.imm00 import log_audit_event
        entry = log_audit_event(
            asset=self.asset.name,
            event_type="State Change",
            actor="Administrator",
            from_status="Commissioned",
            to_status="Active",
            change_summary="Ghi nhận sự kiện kiểm thử tính bất biến của audit trail",
        )
        frappe.db.commit()
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc("IMM Audit Trail", entry, ignore_permissions=True)

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
            _purge_asset(asset.name)
        _purge_category("Thiết bị Cấp cứu & Tái hồi")
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
        _purge_asset(cls.asset.name)
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
            u.append("roles", {"role": "PM User"})
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
        """Trả về các AssetCore role gán cho user (lọc theo Roles.ALL)."""
        from assetcore.services.shared.constants import Roles
        rows = frappe.db.sql(
            "SELECT role FROM `tabHas Role` WHERE parent=%s",
            (self.TEST_EMAIL,), as_dict=True,
        )
        allowed = set(Roles.ALL)
        return sorted(r.role for r in rows if r.role in allowed)

    def test_update_user_roles_persists_to_has_role_table(self):
        """Gán roles mới qua update_user_info → DB phải có đúng các role đó."""
        import json
        from assetcore.api.user import update_user_info

        frappe.local.form_dict = frappe._dict({
            "user": self.TEST_EMAIL,
            "imm_roles": json.dumps([
                {"role": "PM Manager"},
                {"role": "Compliance Manager"},
            ]),
        })
        result = update_user_info()
        frappe.db.commit()

        self.assertTrue(result.get("success"), f"update_user_info failed: {result}")
        self.assertEqual(self._db_roles(), ["Compliance Manager", "PM Manager"])

    def test_update_user_roles_clears_old_roles(self):
        """Gán roles mới phải XÓA các IMM role cũ không nằm trong payload."""
        import json
        from assetcore.api.user import update_user_info

        # Seed: 3 roles
        frappe.local.form_dict = frappe._dict({
            "user": self.TEST_EMAIL,
            "imm_roles": json.dumps([
                {"role": "PM User"},
                {"role": "Inventory Manager"},
                {"role": "Document Manager"},
            ]),
        })
        update_user_info()
        frappe.db.commit()
        self.assertEqual(
            self._db_roles(),
            ["Document Manager", "Inventory Manager", "PM User"],
        )

        # Replace: chỉ giữ 1
        frappe.local.form_dict = frappe._dict({
            "user": self.TEST_EMAIL,
            "imm_roles": json.dumps([{"role": "Corrective User"}]),
        })
        update_user_info()
        frappe.db.commit()
        self.assertEqual(self._db_roles(), ["Corrective User"])

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
            u.append("roles", {"role": "Corrective User"})  # non-admin role
            u.flags.ignore_permissions = True
            u.insert()
            frappe.db.commit()

        try:
            frappe.set_user(guest_email)
            frappe.local.form_dict = frappe._dict({
                "user": self.TEST_EMAIL,
                "imm_roles": json.dumps([{"role": "AssetCore Super Admin"}]),
            })
            result = update_user_info()
            self.assertFalse(result.get("success"))
            self.assertEqual(result.get("http_status"), 403)
        finally:
            frappe.set_user("Administrator")
            frappe.delete_doc("User", guest_email, force=True, ignore_permissions=True)
            frappe.db.commit()


class TestFKDeleteIntegrity(unittest.TestCase):
    """NEG-12 / NEG-13: chặn xóa Model / Location đang được Asset tham chiếu.

    Ref: docs/res/reports/AssetCore_Test_Plan_NextRound_1_Analysis.md §5
    """

    @classmethod
    def setUpClass(cls):
        # Cleanup leftovers
        for nm in frappe.get_all(
            "AC Asset",
            filters={"asset_name": ["like", "FK-INTEG-%"]},
            fields=["name"],
        ):
            _purge_asset(nm.name)
        # IMM Device Model is autonamed (IMM-MDL-####) — look up leaked fixtures
        # by model_name, not name (LL-TEST-9). Must run after assets are purged.
        for m in frappe.get_all("IMM Device Model",
                                filters={"model_name": ["like", "FK-Integ Model %"]},
                                pluck="name"):
            frappe.delete_doc("IMM Device Model", m, force=True, ignore_permissions=True)
        _purge_category("FK-Integrity-Cat")
        frappe.db.commit()

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "FK-Integrity-Cat",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        # Force cleanup any stray asset/model/location created in tests
        for nm in frappe.get_all(
            "AC Asset",
            filters={"asset_name": ["like", "FK-INTEG-%"]},
            fields=["name"],
        ):
            _purge_asset(nm.name)
        frappe.delete_doc(
            "AC Asset Category", cls.cat.name, force=True, ignore_permissions=True
        )
        frappe.db.commit()

    def _make_model(self, suffix: str):
        return frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": f"FK-Integ Model {suffix}",
            "manufacturer": "FK Integ Mfg",
            "medical_device_class": "Class II",
            "asset_category": self.cat.name,
        }).insert(ignore_permissions=True)

    def _make_location(self, suffix: str):
        return frappe.get_doc({
            "doctype": "AC Location",
            "location_name": f"FK-Integ Loc {suffix}",
            "location_type": "Room",
        }).insert(ignore_permissions=True)

    def _make_asset_with(self, *, suffix: str, model: str | None = None,
                         location: str | None = None):
        data = {
            "doctype": "AC Asset",
            "asset_name": f"FK-INTEG-{suffix}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"FK-INTEG-SN-{suffix}",
            "medical_device_class": "Class II",
            "risk_classification": "Medium",
            "purchase_date": "2024-01-01",
            "gross_purchase_amount": 100_000_000,
            "warranty_expiry_date": "2027-01-01",
            "in_service_date": "2024-01-05",
            "byt_reg_no": "BYT-FK-2024-0001",
            "lifecycle_status": "Active",
        }
        if model:
            data["device_model"] = model
        if location:
            data["location"] = location
        return _insert_asset_bypass_workflow(data)

    # NEG-12 — Device Model

    def test_delete_model_blocked_when_asset_references_it(self):
        model = self._make_model("DEL-BLOCK")
        asset = self._make_asset_with(suffix="MODEL-DEL", model=model.name)
        try:
            with self.assertRaises(frappe.LinkExistsError) as ctx:
                frappe.delete_doc(
                    "IMM Device Model", model.name, ignore_permissions=True
                )
            msg = str(ctx.exception)
            self.assertIn("FK-INTEG-MODEL-DEL", msg)
            self.assertIn("Không thể xóa", msg)
        finally:
            _purge_asset(asset.name)
            frappe.delete_doc(
                "IMM Device Model", model.name, force=True, ignore_permissions=True
            )

    def test_delete_model_allowed_when_no_dependent_assets(self):
        model = self._make_model("DEL-OK")
        # No asset references → delete should succeed.
        frappe.delete_doc(
            "IMM Device Model", model.name, ignore_permissions=True
        )
        self.assertFalse(frappe.db.exists("IMM Device Model", model.name))

    # NEG-13 — Location

    def test_delete_location_blocked_when_asset_assigned(self):
        loc = self._make_location("DEL-BLOCK")
        asset = self._make_asset_with(suffix="LOC-DEL", location=loc.name)
        try:
            with self.assertRaises(frappe.LinkExistsError) as ctx:
                frappe.delete_doc(
                    "AC Location", loc.name, ignore_permissions=True
                )
            msg = str(ctx.exception)
            self.assertIn("FK-INTEG-LOC-DEL", msg)
            self.assertIn("Không thể xóa", msg)
        finally:
            _purge_asset(asset.name)
            frappe.delete_doc(
                "AC Location", loc.name, force=True, ignore_permissions=True
            )

    def test_delete_location_allowed_when_no_assets(self):
        loc = self._make_location("DEL-OK")
        frappe.delete_doc("AC Location", loc.name, ignore_permissions=True)
        self.assertFalse(frappe.db.exists("AC Location", loc.name))


# ─────────────────────────────────────────────────────────────────────────────
# ROOT-CAUSE: AC Asset before_insert inherits depreciation rules from Category
# ─────────────────────────────────────────────────────────────────────────────

_CAT_INH = "_TestCatBeforeInsertInh"
_CAT_INH_NORULE = "_TestCatBeforeInsertNoRule"


def _ensure_inh_category(name: str, *, months: int, residual_pct: float) -> str:
    """Idempotent AC Asset Category for before_insert inheritance tests.

    AC Asset Category autoname=CAT-#### ⇒ lookup/cleanup by category_name field.
    """
    existing = frappe.db.get_value(
        "AC Asset Category", {"category_name": name}, "name")
    if existing:
        frappe.db.set_value("AC Asset Category", existing, {
            "default_depreciation_method": "Straight Line",
            "total_depreciation_months": months,
            "depreciation_frequency": "Monthly",
            "default_residual_value_pct": residual_pct,
        }, update_modified=False)
        # Bust the in-process value cache so the SoT's frappe.db.get_value reads
        # the freshly-updated months (set_value on a leaked row can leave a stale
        # (doctype,name,field) value cache → before_insert inherit sees months=0).
        frappe.clear_document_cache("AC Asset Category", existing)
        return existing
    return frappe.get_doc({
        "doctype": "AC Asset Category",
        "category_name": name,
        "default_depreciation_method": "Straight Line",
        "total_depreciation_months": months,
        "depreciation_frequency": "Monthly",
        "default_residual_value_pct": residual_pct,
        "is_active": 1,
    }).insert(ignore_permissions=True).name


def _purge_inh_category(name: str) -> None:
    cat = frappe.db.get_value("AC Asset Category", {"category_name": name}, "name")
    if cat:
        try:
            frappe.delete_doc("AC Asset Category", cat, force=True,
                              ignore_permissions=True)
        except Exception:
            pass


class TestAssetBeforeInsertInheritsDepreciation(unittest.TestCase):
    """[TDD] Insert AC Asset (real insert) gross>0 + asset_category WITH rule,
    NOT passing months/residual → after insert
    doc.total_depreciation_months == Category.total_depreciation_months ∧
    residual_value == round(gross*pct/100, 2).

    RED proof: temporarily remove the call in before_insert → months stays 0.
    """

    @classmethod
    def setUpClass(cls):
        cls.cat = _ensure_inh_category(_CAT_INH, months=60, residual_pct=10.0)
        cls.cat_norule = _ensure_inh_category(_CAT_INH_NORULE, months=0,
                                             residual_pct=0.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_inh_category(_CAT_INH)
        _purge_inh_category(_CAT_INH_NORULE)
        frappe.db.commit()

    def setUp(self):
        self._assets = []
        frappe.set_user("Administrator")

    def tearDown(self):
        for a in self._assets:
            _purge_asset(a)
        frappe.db.commit()

    def _insert(self, **kw):
        data = {
            "doctype": "AC Asset",
            "asset_name": "_Test BeforeInsertInh",
            "gross_purchase_amount": 100_000_000.0,
            "lifecycle_status": "Active",
        }
        data.update(kw)
        doc = _insert_asset_bypass_workflow(data)
        self._assets.append(doc.name)
        return doc

    def test_inherits_months_and_residual_on_insert(self):
        doc = self._insert(asset_category=self.cat)
        self.assertEqual(int(doc.total_depreciation_months), 60)
        self.assertAlmostEqual(
            float(doc.residual_value),
            round(100_000_000.0 * 10.0 / 100, 2),
            delta=0.01,
        )

    def test_category_no_rule_keeps_months_zero_no_raise(self):
        """Category months=0 → before_insert must NOT fabricate, NOT raise."""
        doc = self._insert(asset_category=self.cat_norule)
        self.assertEqual(int(doc.total_depreciation_months or 0), 0)

    def test_user_months_not_clobbered_on_insert(self):
        """User-entered months=24 preserved (no double-apply / clobber)."""
        doc = self._insert(asset_category=self.cat,
                           total_depreciation_months=24)
        self.assertEqual(int(doc.total_depreciation_months), 24)


class TestRegenerateNoFalse422AfterInherit(unittest.TestCase):
    """[TDD] User-reported bug: asset with gross>0 + Category rule, created
    WITHOUT months → regenerate_depreciation_schedule must NOT return a false
    422 'Thiếu: Số tháng khấu hao'; it must generate a schedule (periods>0).

    And: Category ALSO missing rule → regenerate STILL 422 (correct config error).
    """

    @classmethod
    def setUpClass(cls):
        cls.cat = _ensure_inh_category(_CAT_INH, months=60, residual_pct=10.0)
        cls.cat_norule = _ensure_inh_category(_CAT_INH_NORULE, months=0,
                                             residual_pct=0.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_inh_category(_CAT_INH)
        _purge_inh_category(_CAT_INH_NORULE)
        frappe.db.commit()

    def setUp(self):
        self._assets = []
        frappe.set_user("Administrator")

    def tearDown(self):
        for a in self._assets:
            _purge_asset(a)
        frappe.db.commit()

    def _insert(self, **kw):
        data = {
            "doctype": "AC Asset",
            "asset_name": "_Test RegenAfterInh",
            "gross_purchase_amount": 100_000_000.0,
            "lifecycle_status": "Active",
        }
        data.update(kw)
        doc = _insert_asset_bypass_workflow(data)
        self._assets.append(doc.name)
        return doc

    def test_regenerate_no_false_422_after_inherit(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        doc = self._insert(asset_category=self.cat)
        # months inherited at insert ⇒ regenerate must succeed.
        resp = regenerate_depreciation_schedule(doc.name, force=1)
        self.assertTrue(resp.get("success"),
                        f"expected success, got: {resp}")
        data = resp.get("data") or {}
        self.assertGreater(int(data.get("periods") or 0), 0,
                           "schedule must have periods>0")

    def test_regenerate_still_422_when_category_also_missing(self):
        from assetcore.api.imm00 import regenerate_depreciation_schedule
        doc = self._insert(asset_category=self.cat_norule)
        resp = regenerate_depreciation_schedule(doc.name, force=1)
        self.assertFalse(resp.get("success"),
                         "config truly missing → must NOT silently succeed")
        self.assertEqual(resp.get("http_status"), 422)
        self.assertIn("total_depreciation_months", resp.get("error") or "")


# ─────────────────────────────────────────────────────────────────────────────
# RC-05 (Round-4): bulk_regenerate_schedule_by_category audit + RBAC.
# TDD (CLAUDE.md §17) — written BEFORE the audit wiring.
# ─────────────────────────────────────────────────────────────────────────────

class TestBulkRegenAudit(unittest.TestCase):
    """[TDD RC-05] after a bulk that inherits >=1 asset, there is a per-asset
    Asset Lifecycle Event 'depreciation_rules_inherited' + exactly one IMM Audit
    Trail 'System'. Audit is best-effort: a no-op bulk (Category already synced)
    must NOT create garbage events."""

    @classmethod
    def setUpClass(cls):
        cls.cat = _ensure_inh_category(_CAT_INH, months=60, residual_pct=10.0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_inh_category(_CAT_INH)
        frappe.db.commit()

    def setUp(self):
        self._assets = []
        frappe.set_user("Administrator")

    def tearDown(self):
        for a in self._assets:
            _purge_asset(a)
        frappe.db.commit()

    def _bare_asset(self, suffix: str) -> str:
        """gross>0, no rule on the asset, pointing at the rule Category."""
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"_Test BulkAudit {suffix}",
            "gross_purchase_amount": 80_000_000.0,
            "asset_category": self.cat,
            "lifecycle_status": "Active",
        })
        self._assets.append(doc.name)
        return doc.name

    def test_inherit_emits_lifecycle_and_audit(self):
        from assetcore.api.imm00 import bulk_regenerate_schedule_by_category
        asset = self._bare_asset("Inh")
        # Asset created via before_insert ALREADY inherits months at insert, so to
        # exercise the bulk inherit branch we reset it to a missing-rule state.
        frappe.db.set_value("AC Asset", asset, {
            "total_depreciation_months": 0,
            "residual_value": 0,
            "depreciation_method": "",
        }, update_modified=False)
        frappe.db.commit()

        resp = bulk_regenerate_schedule_by_category(self.cat)
        self.assertTrue(resp.get("success"), resp)
        data = resp.get("data") or {}
        self.assertGreaterEqual(data.get("inherited", 0), 1, "must inherit asset")

        ale = frappe.db.count("Asset Lifecycle Event", {
            "asset": asset, "event_type": "depreciation_rules_inherited"})
        self.assertGreaterEqual(
            ale, 1,
            "bulk inherit must record a 'depreciation_rules_inherited' ALE")
        # exactly one IMM Audit Trail 'System' entry referencing the Category.
        aud = frappe.db.count("IMM Audit Trail", {
            "event_type": "System", "ref_name": self.cat})
        self.assertGreaterEqual(aud, 1, "bulk must record an IMM Audit Trail 'System'")

    def test_audit_failure_does_not_break_payload(self):
        """Best-effort: if the audit helper raises, the bulk still returns a
        normal payload (audit must never block the response — CLAUDE.md §5)."""
        from assetcore.api import imm00 as api_mod
        from assetcore.services import depreciation as depr_mod
        asset = self._bare_asset("BestEffort")
        frappe.db.set_value("AC Asset", asset, {
            "total_depreciation_months": 0, "residual_value": 0,
            "depreciation_method": "",
        }, update_modified=False)
        frappe.db.commit()

        # Patch the audit helper wherever it lives (service or api) to blow up.
        target_name = "_log_bulk_regen_audit"
        target_mod = depr_mod if hasattr(depr_mod, target_name) else api_mod
        original = getattr(target_mod, target_name, None)
        self.assertIsNotNone(
            original, f"{target_name} must exist on service or api module")

        def _boom(*a, **k):
            raise RuntimeError("audit exploded")

        setattr(target_mod, target_name, _boom)
        try:
            resp = bulk = api_mod.bulk_regenerate_schedule_by_category(self.cat)
        finally:
            setattr(target_mod, target_name, original)
        self.assertTrue(resp.get("success"), f"audit failure broke payload: {resp}")
        data = resp.get("data") or {}
        for key in ("inherited", "regenerated", "skipped_no_rule"):
            self.assertIn(key, data, f"payload missing key {key}")
        _ = bulk


class TestBulkRegenRBAC(unittest.TestCase):
    """[TDD RC-05] non-admin → 403 (PermissionError) via _assert_system_admin."""

    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_non_admin_blocked(self):
        from assetcore.api.imm00 import bulk_regenerate_schedule_by_category
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                bulk_regenerate_schedule_by_category("any-category")
        finally:
            frappe.set_user("Administrator")


# ─────────────────────────────────────────────────────────────────────────────
# BR-05-13 (falsy-zero fix): effective_book_value SoT — depreciation stats must
# count an asset with current_book_value=0.0 (gross>0, residual=0, configured) as
# fully_depreciated, and must NOT add a phantom `gross` into total_book.
# TDD (CLAUDE.md §17) — written BEFORE wiring `effective_book_value` into the
# 3 BE call-sites of api/imm00.py.
#
# RED-EXPERIMENT (ghi lại, KHÔNG commit): tạm revert effective_book_value về
# ``float(current_book_value or gross)`` ⇒
#   - test_fully_depreciated_counts_book_zero_asset FAIL (delta 0, book→gross>residual)
#   - test_total_book_no_phantom_gross         FAIL (delta == gross, over-count)
# restore SoT → GREEN.
# ─────────────────────────────────────────────────────────────────────────────

_CAT_BOOKZERO = "_TestCatDeprBookZero"


def _book_zero_asset() -> str:
    """Asset đã KH HẾT về 0.0 hợp lệ: gross>0, residual=0, configured (method +
    months>0), current_book_value=0.0, accumulated=gross.

    Dùng category KHÔNG có rule (months=0) ⇒ before_insert KHÔNG kế thừa/clobber;
    ta set thẳng các field KH sau insert (raw set_value, không qua workflow) để
    có đúng trạng thái 'configured + book=0.0'."""
    cat = _ensure_inh_category(_CAT_BOOKZERO, months=0, residual_pct=0.0)
    doc = _insert_asset_bypass_workflow({
        "doctype": "AC Asset",
        # NON-reserved asset_name (KHÔNG prefix '_'): data-hygiene SSoT ẩn '_…'/'SI-…'
        # khỏi list_assets_depreciation + get_depreciation_stats; fixture cần XUẤT
        # HIỆN trong drill ⇒ dùng tên thường. (test_imm00_reserved_prefix bảo vệ ẩn.)
        "asset_name": "ZZTest DeprBookZero",
        "gross_purchase_amount": 120_000_000.0,
        "asset_category": cat,
        "lifecycle_status": "Active",
    })
    frappe.db.set_value("AC Asset", doc.name, {
        "depreciation_method": "Straight Line",
        "total_depreciation_months": 12,
        "depreciation_frequency": "Monthly",
        "residual_value": 0.0,
        "accumulated_depreciation": 120_000_000.0,
        "current_book_value": 0.0,
    }, update_modified=False)
    frappe.db.commit()
    return doc.name


class TestDeprStatsBookZero(unittest.TestCase):
    """BR-05-13: get_depreciation_stats over an asset with book=0.0 (đã KH hết).

    Delta-based: so sánh stats TRƯỚC vs SAU khi thêm 1 asset book=0.0 để cô lập
    đóng góp của riêng nó (DB miyano có data khác đang sống)."""

    def setUp(self):
        frappe.set_user("Administrator")
        from assetcore.api.imm00 import get_depreciation_stats
        self._stats = get_depreciation_stats
        self._before = self._stats()["data"]
        self._asset = _book_zero_asset()

    def tearDown(self):
        _purge_asset(self._asset)
        _purge_inh_category(_CAT_BOOKZERO)
        frappe.db.commit()
        frappe.set_user("Administrator")

    def test_fully_depreciated_counts_book_zero_asset(self):
        """fully_depreciated tăng đúng +1 cho asset gross>0,residual=0,book=0.0.

        RED trước fix: 0 (book→gross>residual+1 ⇒ bị loại khỏi tập)."""
        after = self._stats()["data"]
        delta = after["fully_depreciated"] - self._before["fully_depreciated"]
        self.assertEqual(
            delta, 1,
            "asset book=0.0 (residual=0, configured) PHẢI được đếm "
            "fully_depreciated +1 — falsy-zero `or gross` đã nuốt book=0.0.",
        )

    def test_total_book_no_phantom_gross(self):
        """total_book_value KHÔNG cộng phantom gross cho asset book=0.0.

        Delta total_book do asset này == 0 (book thật), KHÔNG == 120tr (gross).
        RED trước fix: delta == gross (over-count)."""
        after = self._stats()["data"]
        delta = after["total_book_value"] - self._before["total_book_value"]
        self.assertEqual(
            delta, 0,
            "total_book_value over-count: cộng phantom gross cho asset book=0.0 "
            f"(delta={delta}, kỳ vọng 0, KHÔNG 120000000).",
        )


class TestDeprDrillInvariant(unittest.TestCase):
    """INV-DEP-5 giữ nguyên (count==drill) khi tập có asset book=0.0.

    get_depreciation_stats().fully_depreciated == de-dup len của
    list_assets_depreciation(depreciation_filter='fully_depreciated') mọi trang.
    Cả hai cùng dùng SoT mới ⇒ cùng-đúng (trước: cùng-sai-cùng-kiểu)."""

    def setUp(self):
        frappe.set_user("Administrator")
        self._asset = _book_zero_asset()

    def tearDown(self):
        _purge_asset(self._asset)
        _purge_inh_category(_CAT_BOOKZERO)
        frappe.db.commit()
        frappe.set_user("Administrator")

    def _drill_count(self) -> int:
        from assetcore.api.imm00 import list_assets_depreciation
        seen: set[str] = set()
        page = 1
        while True:
            resp = list_assets_depreciation(
                page=page, page_size=200,
                depreciation_filter="fully_depreciated")["data"]
            items = resp.get("items") or []
            for it in items:
                seen.add(it["name"])
            total = (resp.get("pagination") or {}).get("total", 0)
            if page * 200 >= total or not items:
                break
            page += 1
        return len(seen)

    def test_count_equals_drill_with_book_zero(self):
        from assetcore.api.imm00 import list_assets_depreciation
        stats_count = self._stats_fully()
        drill_count = self._drill_count()
        self.assertEqual(
            stats_count, drill_count,
            "INV-DEP-5 vỡ: stats.fully_depreciated != de-dup drill len "
            f"({stats_count} != {drill_count}).",
        )
        # asset book=0.0 PHẢI nằm trong tập drill (chứng minh không-loại-oan).
        self.assertIn(self._asset, self._drill_names(list_assets_depreciation))

    def _stats_fully(self) -> int:
        from assetcore.api.imm00 import get_depreciation_stats
        return get_depreciation_stats()["data"]["fully_depreciated"]

    def _drill_names(self, list_fn) -> set:
        names: set[str] = set()
        page = 1
        while True:
            resp = list_fn(page=page, page_size=200,
                           depreciation_filter="fully_depreciated")["data"]
            items = resp.get("items") or []
            for it in items:
                names.add(it["name"])
            total = (resp.get("pagination") or {}).get("total", 0)
            if page * 200 >= total or not items:
                break
            page += 1
        return names


# ════════════════════════════════════════════════════════════════════════════
# Decommission → Cancel pending depreciation (kill phantom Pending backlog)
# ════════════════════════════════════════════════════════════════════════════
# BUG: thanh lý asset mid-life KHÔNG hủy các kỳ AC Asset Depreciation Schedule
# status='Pending' còn lại → pending_periods > 0 vĩnh viễn + run_due_depreciation
# bỏ qua Decommissioned (line 416) nên kỳ Pending treo "phantom overdue" mãi mãi.
# FIX: transition → Decommissioned phải gọi _cancel_pending_depreciation(asset)
# (Pending → Cancelled, SoT duy nhất) + sinh 1 lifecycle event 'depreciation_stopped'
# + 1 IMM Audit Trail. Executed bất biến. Idempotent. Best-effort audit.
_DEC_FAR_FUTURE = "2099-12-31"

_DEC_DT_SCHED = "AC Asset Depreciation Schedule"


class TestDecommissionCancelsDepreciation(unittest.TestCase):
    """TDD cho services/imm00.transition_asset_status decommission hook."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def setUp(self):
        self._assets: list[str] = []

    def tearDown(self):
        for a in self._assets:
            try:
                _purge_asset(a)
            except Exception:
                pass
        frappe.db.commit()

    # ── fixture ──────────────────────────────────────────────────────────────
    def _make_asset(self, suffix: str, *, lifecycle: str = "Active") -> str:
        """Asset gross=120tr, residual=0, 12 kỳ Monthly, mid-life (start xa quá khứ).

        depreciation_start_date 2024-01-01 + 12 kỳ monthly ⇒ MỌI kỳ scheduled_date
        <= today (2026) → nếu chạy executor đều overdue. Nhưng test giữ tất cả ở
        Pending để chứng minh hook hủy đúng số kỳ Pending.
        """
        if not frappe.db.exists("AC UOM", "Cái"):
            frappe.get_doc({"doctype": "AC UOM", "uom_name": "Cái"}).insert(
                ignore_permissions=True)
        doc = frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Decom Depr {suffix}",
            "gross_purchase_amount": 120_000_000,
            "residual_value": 0,
            "depreciation_method": "Straight Line",
            "total_depreciation_months": 12,
            "depreciation_frequency": "Monthly",
            "depreciation_start_date": "2024-01-01",
            "in_service_date": "2024-01-01",
            "lifecycle_status": lifecycle,
        })
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_links = True
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        self._assets.append(doc.name)
        return doc.name

    def _gen(self, asset: str) -> int:
        from assetcore.services import depreciation as depr_svc
        depr_svc.generate_schedule(asset, force=True)
        frappe.db.commit()
        return self._count_status(asset, "Pending")

    def _count_status(self, asset: str, status: str) -> int:
        return frappe.db.count(_DEC_DT_SCHED, {
            "parent": asset, "parenttype": "AC Asset", "status": status})

    def _pending_periods(self, asset: str) -> int:
        from assetcore.api.imm00 import get_depreciation_schedule
        return get_depreciation_schedule(asset)["data"]["summary"]["pending_periods"]

    def _decommission(self, asset: str):
        # IMM-14 GATE: đi qua closure flow (create + approve) thay vì gọi
        # transition_asset_status trực tiếp — side-effect (cancel depreciation +
        # lifecycle event 'depreciation_stopped' + audit) vẫn do transition lo.
        decommission_via_closure(asset, reason="Thanh lý hết niên hạn theo quy định.")
        frappe.db.commit()

    # ── TC-01 (BUG CHÍNH) ─────────────────────────────────────────────────────
    def test_tc01_decommission_cancels_all_pending(self):
        asset = self._make_asset("tc01")
        n = self._gen(asset)
        self.assertGreater(n, 0, "fixture phải có kỳ Pending")
        self.assertGreater(self._pending_periods(asset), 0)

        self._decommission(asset)

        self.assertEqual(self._count_status(asset, "Pending"), 0,
                         "tất cả kỳ Pending phải → Cancelled")
        self.assertEqual(self._count_status(asset, "Cancelled"), n)
        self.assertEqual(self._pending_periods(asset), 0,
                         "get_depreciation_schedule.pending_periods phải = 0")

    # ── TC-02: Executed bất biến ──────────────────────────────────────────────
    def test_tc02_executed_rows_untouched(self):
        from assetcore.services import depreciation as depr_svc
        asset = self._make_asset("tc02")
        self._gen(asset)
        # Chạy executor để 1 vài kỳ thành Executed (asset Active).
        depr_svc.run_due_depreciation(as_of="2024-04-30", asset=asset)
        frappe.db.commit()
        executed_before = self._count_status(asset, "Executed")
        self.assertGreater(executed_before, 0, "phải có kỳ Executed trước decommission")
        acc_before = flt(frappe.db.get_value("AC Asset", asset, "accumulated_depreciation"))
        book_before = flt(frappe.db.get_value("AC Asset", asset, "current_book_value"))

        self._decommission(asset)

        self.assertEqual(self._count_status(asset, "Executed"), executed_before,
                         "kỳ Executed KHÔNG được đổi status")
        self.assertEqual(
            flt(frappe.db.get_value("AC Asset", asset, "accumulated_depreciation")),
            acc_before, "accumulated_depreciation bất biến")
        self.assertEqual(
            flt(frappe.db.get_value("AC Asset", asset, "current_book_value")),
            book_before, "current_book_value bất biến")

    # ── TC-03: idempotent ─────────────────────────────────────────────────────
    def test_tc03_idempotent_no_dup_cancel_or_event(self):
        from assetcore.services.imm00 import _cancel_pending_depreciation
        asset = self._make_asset("tc03")
        self._gen(asset)
        self._decommission(asset)
        events_after_1 = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset, "event_type": "depreciation_stopped"})
        self.assertEqual(events_after_1, 1)

        # Re-run helper directly: không còn Pending → trả 0, không Cancelled mới.
        cancelled_2 = _cancel_pending_depreciation(asset)
        frappe.db.commit()
        self.assertEqual(cancelled_2, 0, "lần 2 không hủy thêm kỳ nào")

        # Transition lại (prev==to Decommissioned → early-return) không sinh event 2.
        from assetcore.services.imm00 import transition_asset_status
        transition_asset_status(asset, "Decommissioned", actor="Administrator")
        frappe.db.commit()
        events_after_2 = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset, "event_type": "depreciation_stopped"})
        self.assertEqual(events_after_2, 1, "không sinh event depreciation_stopped thứ 2")

    # ── TC-04: audit + event đúng 1; không sinh thừa khi 0 kỳ ──────────────────
    def test_tc04_audit_event_created_with_notes(self):
        asset = self._make_asset("tc04")
        n = self._gen(asset)
        self._decommission(asset)

        events = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": asset, "event_type": "depreciation_stopped"},
            fields=["name", "notes", "root_doctype"])
        self.assertEqual(len(events), 1, "đúng 1 Asset Lifecycle Event depreciation_stopped")
        self.assertEqual(events[0]["root_doctype"], "AC Asset")
        self.assertIn(str(n), events[0]["notes"] or "",
                      "notes phải nêu số kỳ hủy")
        # IMM Audit Trail có bản ghi cho asset (decommission ghi State Change).
        self.assertGreaterEqual(
            frappe.db.count("IMM Audit Trail", {"asset": asset}), 1)

    def test_tc04b_no_event_when_zero_pending(self):
        # Asset KHÔNG có schedule (0 kỳ Pending) → decommission KHÔNG sinh event thừa.
        asset = self._make_asset("tc04b")
        self.assertEqual(self._count_status(asset, "Pending"), 0)
        self._decommission(asset)
        self.assertEqual(
            frappe.db.count("Asset Lifecycle Event",
                            {"asset": asset, "event_type": "depreciation_stopped"}),
            0, "0 kỳ Pending → KHÔNG sinh event depreciation_stopped")

    # ── TC-05: executor no-phantom sau decommission ──────────────────────────
    def test_tc05_executor_no_phantom_after_decommission(self):
        from assetcore.services import depreciation as depr_svc
        asset = self._make_asset("tc05")
        self._gen(asset)
        self._decommission(asset)
        res = depr_svc.run_due_depreciation(as_of=_DEC_FAR_FUTURE, asset=asset)
        self.assertEqual(res["executed_rows"], 0,
                         "Decommissioned asset KHÔNG được execute kỳ nào nữa")

    # ── TC-06: best-effort — audit lỗi KHÔNG vỡ transition ────────────────────
    def test_tc06_audit_failure_does_not_break_transition(self):
        import assetcore.services.imm00 as svc
        asset = self._make_asset("tc06")
        n = self._gen(asset)

        orig = svc.create_lifecycle_event

        def _boom(*a, **k):
            # chỉ raise cho event depreciation_stopped (giữ event decommissioned chạy)
            if k.get("event_type") == "depreciation_stopped":
                raise RuntimeError("simulated audit failure")
            return orig(*a, **k)

        svc.create_lifecycle_event = _boom
        try:
            self._decommission(asset)
        finally:
            svc.create_lifecycle_event = orig

        # Transition vẫn hoàn tất: status set + rows vẫn Cancelled.
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            "Decommissioned")
        self.assertEqual(self._count_status(asset, "Cancelled"), n,
                         "rows vẫn phải Cancelled dù audit lỗi")
        self.assertEqual(self._count_status(asset, "Pending"), 0)

    # ── TC-07: AST/grep guard — 1 SoT duy nhất ────────────────────────────────
    def test_tc07_single_source_of_truth_no_inline_cancel(self):
        import inspect
        import re
        import assetcore.services.imm00 as svc

        src = inspect.getsource(svc)
        # Mọi set status='Cancelled' của depreciation phải đi qua helper.
        # Đếm số literal "Cancelled" gắn với schedule UPDATE/set_value ngoài helper.
        helper_src = inspect.getsource(svc._cancel_pending_depreciation)
        self.assertIn("Cancelled", helper_src,
                      "helper phải set status='Cancelled'")
        self.assertIn(_DEC_DT_SCHED, helper_src,
                      "helper phải target AC Asset Depreciation Schedule")

        # Ngoài helper: KHÔNG có inline set_value(... 'AC Asset Depreciation
        # Schedule' ... 'Cancelled').
        outside = src.replace(helper_src, "")
        offending = re.findall(
            r"AC Asset Depreciation Schedule[\s\S]{0,200}?Cancelled", outside)
        self.assertEqual(
            offending, [],
            "depreciation Cancelled-on-decommission chỉ qua _cancel_pending_depreciation")


# ──────────────────────────────────────────────────────────────────────────
# A1 — QR cấp tài sản: field qr_token + sinh idempotent (3-tier) + before_insert
# + lifecycle/audit + enum delta + backfill patch (ADR-001, IMM-00 §II.1.8/§II.6)
# ──────────────────────────────────────────────────────────────────────────


class TestAssetQRToken(unittest.TestCase):
    """A1 — token QR enumeration-safe, idempotent, lifecycle/audit best-effort."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Chẩn đoán hình ảnh (QR)",
            "description": "Category cho test QR token",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        self._created: list[str] = []

    def tearDown(self):
        # Durable cleanup: rollback aborted-tx trước, rồi purge + commit DỨT KHOÁT
        # (chống leak khi 1 test sau commit gom luôn insert của test trước).
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy QR Test {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"QR-SN-{uniq}",
            "asset_code": f"QR-ASSET-{uniq}",
            "lifecycle_status": "Commissioned",
        })
        self._created.append(doc.name)
        return doc

    # ── Schema ───────────────────────────────────────────────────────────────
    def test_event_type_enum_has_qr_options(self):
        """RED trước khi sync JSON: event_type chứa qr_generated + label_printed."""
        meta = frappe.get_meta("Asset Lifecycle Event")
        opts = (meta.get_field("event_type").options or "").split("\n")
        self.assertIn("qr_generated", opts)
        self.assertIn("label_printed", opts)

    # ── Idempotent — insert ───────────────────────────────────────────────────
    def test_qr_token_generated_on_insert(self):
        asset = self._make_asset("gen")
        try:
            self.assertTrue(asset.qr_token,
                            "qr_token phải != rỗng sau insert")
            self.assertIsNotNone(asset.qr_token)
        finally:
            _purge_asset(asset.name)

    def test_qr_token_enumeration_safe(self):
        a1 = self._make_asset("enum1")
        a2 = self._make_asset("enum2")
        try:
            t1, t2 = a1.qr_token, a2.qr_token
            self.assertNotEqual(t1, t2, "2 asset → 2 token khác nhau")
            for asset, t in ((a1, t1), (a2, t2)):
                self.assertGreaterEqual(len(t), 20, "token URL-safe >= 20 ký tự")
                self.assertRegex(t, r"^[A-Za-z0-9_-]+$",
                                 "token chỉ ký tự URL-safe [A-Za-z0-9_-]")
                self.assertNotIn(asset.name, t, "token KHÔNG chứa name")
                self.assertNotIn(asset.asset_code, t,
                                 "token KHÔNG chứa asset_code")
        finally:
            _purge_asset(a1.name)
            _purge_asset(a2.name)

    def test_qr_token_idempotent_on_update(self):
        asset = self._make_asset("upd")
        try:
            tok = asset.qr_token
            asset.asset_name = "Máy QR Test upd — đổi tên"
            asset.save(ignore_permissions=True)
            asset.reload()
            self.assertEqual(asset.qr_token, tok,
                             "qr_token KHÔNG đổi khi update field khác")
        finally:
            _purge_asset(asset.name)

    # ── Service tier ──────────────────────────────────────────────────────────
    def test_ensure_asset_qr_token_no_op_when_present(self):
        from assetcore.services.imm00 import ensure_asset_qr_token
        asset = self._make_asset("noop")
        try:
            before = frappe.db.count("Asset Lifecycle Event",
                                     {"asset": asset.name,
                                      "event_type": "qr_generated"})
            t1 = ensure_asset_qr_token(asset)
            t2 = ensure_asset_qr_token(asset)
            self.assertEqual(t1, t2, "2 lần gọi trả cùng token")
            self.assertEqual(t1, asset.qr_token)
            after = frappe.db.count("Asset Lifecycle Event",
                                    {"asset": asset.name,
                                     "event_type": "qr_generated"})
            self.assertEqual(after, before,
                             "đã có token → KHÔNG emit qr_generated thêm")
        finally:
            _purge_asset(asset.name)

    def test_generate_qr_token_pure(self):
        from assetcore.services.imm00 import generate_qr_token
        t1, t2 = generate_qr_token(), generate_qr_token()
        self.assertNotEqual(t1, t2)
        for t in (t1, t2):
            self.assertGreaterEqual(len(t), 20)
            self.assertRegex(t, r"^[A-Za-z0-9_-]+$")

    # ── Lifecycle + audit ─────────────────────────────────────────────────────
    def test_qr_generated_lifecycle_and_audit_emitted(self):
        asset = self._make_asset("emit")
        try:
            ale = frappe.db.count("Asset Lifecycle Event",
                                  {"asset": asset.name,
                                   "event_type": "qr_generated"})
            self.assertEqual(ale, 1,
                             "đúng 1 Asset Lifecycle Event qr_generated")
            row = frappe.get_all(
                "Asset Lifecycle Event",
                filters={"asset": asset.name, "event_type": "qr_generated"},
                fields=["root_doctype", "root_record"], limit=1)[0]
            self.assertEqual(row["root_doctype"], "AC Asset")
            self.assertEqual(row["root_record"], asset.name)
            aud = frappe.db.count(
                "IMM Audit Trail",
                {"asset": asset.name, "event_type": "System",
                 "ref_doctype": "AC Asset", "ref_name": asset.name})
            self.assertGreaterEqual(aud, 1, "có IMM Audit Trail tương ứng")
        finally:
            _purge_asset(asset.name)

    def test_audit_failure_does_not_break_insert(self):
        """monkeypatch log_audit_event raise → insert vẫn OK + token vẫn set."""
        from assetcore.services import imm00 as svc
        orig = svc.log_audit_event

        def _boom(*a, **k):
            raise RuntimeError("audit down")

        svc.log_audit_event = _boom
        asset = None
        try:
            asset = self._make_asset("auditfail")
            self.assertTrue(asset.qr_token,
                            "qr_token vẫn set dù audit lỗi (best-effort)")
            self.assertTrue(frappe.db.exists("AC Asset", asset.name))
        finally:
            svc.log_audit_event = orig
            if asset:
                _purge_asset(asset.name)

    # ── DB unique constraint ──────────────────────────────────────────────────
    def test_qr_token_unique_constraint(self):
        a1 = self._make_asset("uniq1")
        a2 = self._make_asset("uniq2")
        try:
            dup = a1.qr_token
            with self.assertRaises(Exception):
                frappe.db.sql(
                    "UPDATE `tabAC Asset` SET qr_token=%s WHERE name=%s",
                    (dup, a2.name))
                frappe.db.commit()
        finally:
            # SQL lỗi UNIQUE để transaction ở trạng thái abort → rollback TRƯỚC,
            # rồi purge (a1/a2 đã commit lúc insert? insert() KHÔNG commit → có
            # thể đã mất sau rollback; _purge_asset guard bằng exists).
            frappe.db.rollback()
            _purge_asset(a1.name)
            _purge_asset(a2.name)
            frappe.db.commit()

    # ── Backfill patch ────────────────────────────────────────────────────────
    def test_backfill_patch_idempotent(self):
        import importlib
        patch = importlib.import_module(
            "assetcore.patches.v3_2.008_backfill_asset_qr_token")
        asset = self._make_asset("backfill")
        try:
            # Giả legacy: xóa token (raw SQL, không qua validate)
            frappe.db.sql(
                "UPDATE `tabAC Asset` SET qr_token=NULL WHERE name=%s",
                (asset.name,))
            frappe.db.commit()
            patch.execute()
            tok = frappe.db.get_value("AC Asset", asset.name, "qr_token")
            self.assertTrue(tok, "patch sinh token cho asset legacy")
            patch.execute()  # re-run = no-op
            tok2 = frappe.db.get_value("AC Asset", asset.name, "qr_token")
            self.assertEqual(tok, tok2, "re-run patch KHÔNG đổi token")
        finally:
            _purge_asset(asset.name)


# ──────────────────────────────────────────────────────────────────────────
# B (Vòng 17) — SSoT collision-safe qr_token generation (BR-00-31 / FR-00-76..79)
# 1 helper DUY NHẤT generate_unique_qr_token(exclude) — pre-write check
# frappe.db.exists + bounded retry _MAX_QR_TOKEN_RETRY + cạn→frappe.ValidationError
# (KHÔNG IntegrityError thô). 4 đường ghi (before_insert/ensure/regenerate/backfill)
# DELEGATE cùng helper. RED viết trước impl (CLAUDE.md §17).
# ──────────────────────────────────────────────────────────────────────────


class TestGenerateUniqueQrToken(unittest.TestCase):
    """B — helper SSoT generate_unique_qr_token: retry collision, exclude, exhaust."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Chẩn đoán hình ảnh (QR-COLL)",
            "description": "Category cho test QR collision-safe",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        self._created: list[str] = []

    def tearDown(self):
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy QR Coll {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"QRC-SN-{uniq}",
            "asset_code": f"QRC-ASSET-{uniq}",
            "lifecycle_status": "Commissioned",
        })
        self._created.append(doc.name)
        return doc

    # ── helper API ────────────────────────────────────────────────────────────
    def test_generate_unique_qr_token_retries_on_collision(self):
        """RED: lần 1 trả token đã tồn tại trên 1 AC Asset → retry → lần 2 trả mới.

        gen được gọi đúng 2 lần; helper trả token lần 2 (unique). KHÔNG ghi DB.
        """
        from assetcore.services import imm00 as svc
        asset = self._make_asset("retry")
        existing = asset.qr_token
        seq = iter([existing, "FRESH-UNIQUE-TOKEN-COLL-1"])
        calls = {"n": 0}

        def _fake():
            calls["n"] += 1
            return next(seq)

        orig = svc.generate_qr_token
        svc.generate_qr_token = _fake
        try:
            tok = svc.generate_unique_qr_token()
            self.assertEqual(tok, "FRESH-UNIQUE-TOKEN-COLL-1",
                             "trả token lần 2 (unique), bỏ token va chạm lần 1")
            self.assertEqual(calls["n"], 2, "gọi generate_qr_token đúng 2 lần")
            # Pure: helper KHÔNG đụng asset.qr_token trên DB.
            self.assertEqual(
                frappe.db.get_value("AC Asset", asset.name, "qr_token"), existing,
                "helper thuần token-gen — KHÔNG ghi DB")
        finally:
            svc.generate_qr_token = orig

    def test_generate_unique_qr_token_no_collision_single_call(self):
        """RED: token đầu unique → trả ngay, gọi generate_qr_token đúng 1 lần."""
        from assetcore.services import imm00 as svc
        calls = {"n": 0}

        def _fake():
            calls["n"] += 1
            return "UNIQUE-NO-COLL-TOKEN-XYZ"

        orig = svc.generate_qr_token
        svc.generate_qr_token = _fake
        try:
            tok = svc.generate_unique_qr_token()
            self.assertEqual(tok, "UNIQUE-NO-COLL-TOKEN-XYZ")
            self.assertEqual(calls["n"], 1, "no wasted retry khi token đầu unique")
        finally:
            svc.generate_qr_token = orig

    def test_generate_unique_qr_token_exhausts_retry_raises(self):
        """RED: gen luôn trả token trùng → raise frappe.ValidationError.

        KHÔNG IntegrityError thô, KHÔNG loop vô hạn; số lần gọi == _MAX_QR_TOKEN_RETRY.
        """
        from assetcore.services import imm00 as svc
        asset = self._make_asset("exhaust")
        existing = asset.qr_token
        calls = {"n": 0}

        def _fake():
            calls["n"] += 1
            return existing  # luôn trùng

        orig = svc.generate_qr_token
        svc.generate_qr_token = _fake
        try:
            with self.assertRaises(frappe.ValidationError):
                svc.generate_unique_qr_token()
            self.assertEqual(calls["n"], svc._MAX_QR_TOKEN_RETRY,
                             "gọi đúng _MAX_QR_TOKEN_RETRY lần rồi raise (bounded)")
        finally:
            svc.generate_qr_token = orig

    def test_generate_unique_qr_token_respects_exclude(self):
        """RED: exclude=old → token trả về != old kể cả khi DB chưa có old."""
        from assetcore.services import imm00 as svc
        seq = iter(["OLD-ROTATE-TOKEN", "NEW-ROTATE-TOKEN"])
        calls = {"n": 0}

        def _fake():
            calls["n"] += 1
            return next(seq)

        orig = svc.generate_qr_token
        svc.generate_qr_token = _fake
        try:
            tok = svc.generate_unique_qr_token(exclude="OLD-ROTATE-TOKEN")
            self.assertEqual(tok, "NEW-ROTATE-TOKEN",
                             "exclude bỏ token cũ dù DB chưa có nó")
            self.assertNotEqual(tok, "OLD-ROTATE-TOKEN")
            self.assertEqual(calls["n"], 2)
        finally:
            svc.generate_qr_token = orig

    # ── 4 đường ghi DELEGATE ────────────────────────────────────────────────
    def test_before_insert_token_unique_after_collision(self):
        """RED: gen va chạm lần đầu → AC Asset mới hoàn tất, token unique, KHÔNG IntegrityError."""
        from assetcore.services import imm00 as svc
        seed = self._make_asset("biseed")
        clash = seed.qr_token
        seq = iter([clash, "BI-FRESH-UNIQUE-TOKEN"])

        def _fake():
            return next(seq)

        orig = svc.generate_qr_token
        svc.generate_qr_token = _fake
        try:
            new = self._make_asset("bicollide")
            self.assertEqual(new.qr_token, "BI-FRESH-UNIQUE-TOKEN",
                             "before_insert nhận token unique sau va chạm")
            self.assertTrue(frappe.db.exists("AC Asset", new.name),
                            "INSERT KHÔNG bị abort bởi IntegrityError")
        finally:
            svc.generate_qr_token = orig

    def test_ensure_asset_qr_token_collision_safe(self):
        """RED: token-less + collision lần đầu → ensure trả token unique.

        Regression idempotency: đã-có-token → no-op, KHÔNG gọi helper, KHÔNG emit lần 2.
        """
        from assetcore.services import imm00 as svc
        seed = self._make_asset("enseed")
        clash = seed.qr_token
        target = self._make_asset("ennull")
        # Giả token-less (raw SQL, không qua validate).
        frappe.db.sql("UPDATE `tabAC Asset` SET qr_token=NULL WHERE name=%s",
                      (target.name,))
        frappe.db.commit()

        seq = iter([clash, "EN-FRESH-UNIQUE-TOKEN"])

        def _fake():
            return next(seq)

        orig_gen = svc.generate_qr_token
        svc.generate_qr_token = _fake
        try:
            tok = svc.ensure_asset_qr_token(target.name)
            self.assertEqual(tok, "EN-FRESH-UNIQUE-TOKEN",
                             "ensure delegate helper → token unique sau va chạm")
        finally:
            svc.generate_qr_token = orig_gen

        # Idempotency: đã có token → KHÔNG gọi helper, KHÔNG emit lần 2.
        before_emit = frappe.db.count("Asset Lifecycle Event",
                                      {"asset": target.name,
                                       "event_type": "qr_generated"})
        called = {"helper": False}
        orig_helper = svc.generate_unique_qr_token

        def _spy(*a, **k):
            called["helper"] = True
            return orig_helper(*a, **k)

        svc.generate_unique_qr_token = _spy
        try:
            again = svc.ensure_asset_qr_token(target.name)
        finally:
            svc.generate_unique_qr_token = orig_helper
        self.assertEqual(again, tok, "idempotent: trả cùng token")
        self.assertFalse(called["helper"],
                         "đã có token → KHÔNG gọi generate_unique_qr_token")
        after_emit = frappe.db.count("Asset Lifecycle Event",
                                     {"asset": target.name,
                                      "event_type": "qr_generated"})
        self.assertEqual(after_emit, before_emit,
                         "đã có token → KHÔNG emit qr_generated lần 2")

    def test_regenerate_collision_with_other_asset(self):
        """RED: token mới trùng token asset KHÁC ở lần đầu → retry → unique != cũ.

        emit qr_regenerated đúng 1 lần.
        """
        from assetcore.services import imm00 as svc
        other = self._make_asset("rgother")
        target = self._make_asset("rgtarget")
        old = target.qr_token
        other_tok = other.qr_token
        # lần 1 trả token của asset khác (đã tồn tại) → helper retry; lần 2 unique.
        seq = iter([other_tok, "RG-FRESH-UNIQUE-TOKEN"])

        def _fake():
            return next(seq)

        orig = svc.generate_qr_token
        svc.generate_qr_token = _fake
        try:
            new = svc.regenerate_asset_qr_token(target.name)
            self.assertEqual(new, "RG-FRESH-UNIQUE-TOKEN")
            self.assertNotEqual(new, old, "rotate đổi token cũ")
            self.assertNotEqual(new, other_tok, "rotate KHÔNG đụng token asset khác")
            self.assertFalse(
                frappe.db.exists("AC Asset",
                                 {"qr_token": new, "name": ["!=", target.name]}),
                "token cuối unique trong toàn bảng")
            self.assertEqual(
                frappe.db.get_value("AC Asset", target.name, "qr_token"), new)
        finally:
            svc.generate_qr_token = orig
        emit = frappe.db.count("Asset Lifecycle Event",
                               {"asset": target.name,
                                "event_type": "qr_regenerated"})
        self.assertEqual(emit, 1, "emit qr_regenerated đúng 1 lần")

    def test_backfill_patch_delegates_unique_helper(self):
        """RED: patch 008 sau collision lần đầu → backfill token unique; idempotent."""
        import importlib
        from assetcore.services import imm00 as svc
        patch = importlib.import_module(
            "assetcore.patches.v3_2.008_backfill_asset_qr_token")
        seed = self._make_asset("bfseed")
        clash = seed.qr_token
        legacy = self._make_asset("bflegacy")
        frappe.db.sql("UPDATE `tabAC Asset` SET qr_token=NULL WHERE name=%s",
                      (legacy.name,))
        frappe.db.commit()

        seq = iter([clash, "BF-FRESH-UNIQUE-TOKEN"])

        def _fake():
            return next(seq)

        orig = svc.generate_qr_token
        svc.generate_qr_token = _fake
        try:
            patch.execute()
        finally:
            svc.generate_qr_token = orig
        tok = frappe.db.get_value("AC Asset", legacy.name, "qr_token")
        self.assertEqual(tok, "BF-FRESH-UNIQUE-TOKEN",
                         "backfill sinh token unique cho asset legacy qua helper")
        # Idempotent: re-run = no-op (0 asset trống).
        patch.execute()
        tok2 = frappe.db.get_value("AC Asset", legacy.name, "qr_token")
        self.assertEqual(tok, tok2, "re-run patch KHÔNG đổi token")


# ──────────────────────────────────────────────────────────────────────────
# A2 — Deep-link resolve qr_token → asset (ADR-001 D2/D4)
# RBAC enablement (asset.* cap), endpoint resolve_qr_token: 200/404/403/IDOR,
# cap-set version regression guard (chống quên bust FE cache — lesson IMM-14).
# ──────────────────────────────────────────────────────────────────────────


class TestAssetCapabilityEnablement(unittest.TestCase):
    """A2 — domain Asset thêm vào _DOMAIN_PRIMARY → auto-sinh asset.* cap.

    Chống RBAC dead-gate (lesson r1-25): gate bằng cap KHÔNG tồn tại = chặn âm
    thầm. asset.read PHẢI tồn tại + resolve qua DocPerm AC Asset (KHÔNG hardcode
    role-name).
    """

    def test_asset_read_capability_exists(self):
        """CAPABILITY_MAP chứa asset.read sau khi A2 thêm domain Asset."""
        from assetcore.services.shared.rbac import CAPABILITY_MAP
        self.assertIn("asset.read", CAPABILITY_MAP,
                      "asset.read phải tồn tại sau khi thêm 'Asset' vào "
                      "_DOMAIN_PRIMARY (chống RBAC dead-gate)")

    def test_asset_six_capabilities_generated(self):
        """6 cap CRUD asset.* auto-sinh + bind đúng ('AC Asset', ptype)."""
        from assetcore.services.shared.rbac import CAPABILITY_MAP
        for pt in ("read", "write", "create", "delete", "submit", "cancel"):
            cap = f"asset.{pt}"
            self.assertIn(cap, CAPABILITY_MAP, f"{cap} phải auto-sinh")
            self.assertEqual(CAPABILITY_MAP[cap], ("AC Asset", pt),
                             f"{cap} phải bind ('AC Asset', '{pt}')")

    def test_can_asset_read_resolves_via_docperm(self):
        """can('asset.read') → frappe.has_permission('AC Asset','read').

        Admin có DocPerm read → True; Guest không → False. KHÔNG hardcode role.
        """
        from assetcore.services.shared import rbac
        frappe.set_user("Administrator")
        try:
            self.assertTrue(rbac.can("asset.read"),
                            "Administrator có DocPerm read AC Asset → True")
        finally:
            frappe.set_user("Administrator")
        frappe.set_user("Guest")
        try:
            self.assertFalse(rbac.can("asset.read"),
                             "Guest không có DocPerm read AC Asset → False")
        finally:
            frappe.set_user("Administrator")

    def test_cap_set_version_changed_after_asset_domain(self):
        """Regression guard: thêm 6 cap asset.* → CAP_SET_VERSION ĐỔI giá trị cũ.

        Buộc FE auth.ts::CAP_SET_VERSION phải bump khớp → isCapCacheStale tự bỏ
        persisted-caps stale (rỗng asset.*) → gate không chết âm thầm (lesson
        IMM-14). Giá trị cũ trước A2 = 'v89.2df4c16c2bbd' (89 cap).
        """
        from assetcore.services.shared.rbac import CAP_SET_VERSION, CAPABILITY_MAP
        self.assertNotEqual(CAP_SET_VERSION, "v89.2df4c16c2bbd",
                            "CAP_SET_VERSION phải đổi sau khi thêm 6 cap asset.* "
                            "(quên bump = FE giữ cap-set rỗng asset.*)")
        self.assertTrue(CAP_SET_VERSION.startswith("v95."),
                        f"95 cap sau A2 → version prefix 'v95.' (hiện {CAP_SET_VERSION})")
        self.assertEqual(len(CAPABILITY_MAP), 95,
                         "89 + 6 cap asset.* = 95")


class TestResolveQrToken(unittest.TestCase):
    """A2 — endpoint resolve_qr_token: 200/404/403/IDOR, leak-safe, no-audit."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Resolve QR (A2)",
            "description": "Category cho test resolve_qr_token",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy Resolve {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"RS-SN-{uniq}",
            "asset_code": f"RS-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    # ── 200 — token hợp lệ trả payload tối thiểu ────────────────────────────
    def test_resolve_valid_token_returns_payload(self):
        from assetcore.api.imm00 import resolve_qr_token
        asset = self._make_asset("ok")
        resp = resolve_qr_token(token=asset.qr_token)
        self.assertTrue(resp["success"], "token hợp lệ → success")
        data = resp["data"]
        self.assertEqual(data["name"], asset.name)
        self.assertEqual(data["asset_code"], asset.asset_code)
        self.assertEqual(data["lifecycle_status"], "Active")
        # field hiển thị tối thiểu phải có mặt trong payload (kể cả rỗng).
        self.assertIn("device_model_name", data)
        self.assertIn("location_name", data)

    # ── 404 — token không tồn tại (KHÔNG raise, KHÔNG 500, leak-safe) ────────
    def test_resolve_unknown_token_returns_404(self):
        from assetcore.api.imm00 import resolve_qr_token
        resp = resolve_qr_token(token="khong-ton-tai-zzzzzzzzzzzzzzzzz")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 404,
                         "token sai → 404, KHÔNG 500")

    def test_resolve_empty_token_returns_404_no_full_scan(self):
        """token rỗng ("") hoặc param vắng → 404 (guard), KHÔNG full-scan.

        P1 hotfix: signature là ``token: str = ""`` (KHÔNG ``str | None``) để layer
        coercion @whitelist nhận str → KHÔNG 417 (xem TestQrWhitelistHttpLayer).
        Real-GET KHÔNG bao giờ gửi ``None`` (param vắng → default ``""``); guard
        ``isinstance(token, str)`` ở service vẫn ép rỗng → None → 404 leak-safe.
        """
        from assetcore.api.imm00 import resolve_qr_token
        # token="" (rỗng) + param hoàn toàn vắng (dùng default "") — 2 đường real-GET.
        for resp in (resolve_qr_token(token=""), resolve_qr_token()):
            self.assertFalse(resp["success"], "token rỗng → KHÔNG success")
            self.assertIn(resp["http_status"], (400, 404),
                          "token rỗng → 400/404, KHÔNG trả asset, KHÔNG 417")

    # ── 403 — user KHÔNG có asset.read ──────────────────────────────────────
    def test_resolve_without_capability_raises_permission(self):
        """Guest (không DocPerm read AC Asset) → PermissionError (403)."""
        from assetcore.api.imm00 import resolve_qr_token
        asset = self._make_asset("noperm")
        token = asset.qr_token
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                resolve_qr_token(token=token)
        finally:
            frappe.set_user("Administrator")

    # ── 403 — IDOR / vendor isolation ───────────────────────────────────────
    def test_resolve_vendor_out_of_scope_forbidden_no_leak(self):
        """Vendor Engineer resolve token asset NGOÀI scope → 403, KHÔNG leak.

        Tái dùng assert_vendor_can_access (KHÔNG re-implement). Vendor không được
        giao PM/CM trên asset → ServiceError(FORBIDDEN) → envelope 403, không có
        payload asset.
        """
        from assetcore.api.imm00 import resolve_qr_token
        asset = self._make_asset("idor")
        token = asset.qr_token
        vendor_email = "vendor_a2_idor@example.com"
        if frappe.db.exists("User", vendor_email):
            frappe.delete_doc("User", vendor_email, force=True,
                              ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": vendor_email,
            "first_name": "Vendor A2 IDOR", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        # Vendor Engineer (scope-restrict) + Repair User (grants asset.read
        # DocPerm) → user QUA gate require('asset.read') NHƯNG bị chặn ở IDOR
        # assert_vendor_can_access (asset ngoài WO được giao) → đúng đường test.
        u.add_roles("Vendor Engineer", "Repair User")
        frappe.db.commit()
        frappe.set_user(vendor_email)
        try:
            resp = resolve_qr_token(token=token)
            self.assertFalse(resp["success"], "vendor ngoài scope → KHÔNG success")
            self.assertEqual(resp["http_status"], 403,
                             "vendor ngoài scope → 403 (IDOR guard)")
            self.assertNotIn("asset_code", resp.get("data") or {},
                             "KHÔNG leak payload asset ngoài scope")
        finally:
            frappe.set_user("Administrator")
            if frappe.db.exists("User", vendor_email):
                frappe.delete_doc("User", vendor_email,
                                  force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── No-audit on resolve (ADR D4) ────────────────────────────────────────
    def test_resolve_does_not_write_audit(self):
        """Read-only lookup → KHÔNG ghi audit/lifecycle (chống spam chain)."""
        from assetcore.api.imm00 import resolve_qr_token
        asset = self._make_asset("noaudit")
        before = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        before_ale = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        resolve_qr_token(token=asset.qr_token)
        self.assertEqual(
            frappe.db.count("IMM Audit Trail", {"asset": asset.name}), before,
            "resolve KHÔNG ghi IMM Audit Trail")
        self.assertEqual(
            frappe.db.count("Asset Lifecycle Event", {"asset": asset.name}),
            before_ale, "resolve KHÔNG ghi Asset Lifecycle Event")

    # ── Index — lookup KHÔNG full-scan ──────────────────────────────────────
    def test_qr_token_field_is_indexed(self):
        """qr_token có index (unique hoặc search_index) → resolve O(log n)."""
        idx = frappe.db.sql(
            "SHOW INDEX FROM `tabAC Asset` WHERE Column_name='qr_token'",
            as_dict=True)
        self.assertTrue(idx, "qr_token PHẢI có DB index (chống full-scan resolve)")


# ──────────────────────────────────────────────────────────────────────────
# A6 — Màn THÔNG TIN thiết bị mobile-first khi quét QR (deep-link landing)
# Endpoint get_asset_scan_info(token|name): payload mobile cốt lõi (định danh +
# model + vị trí + lifecycle_status canonical + bảo trì gần nhất + next_pm_date),
# RBAC asset.read (403) + IDOR vendor-scope (403) + 404 leak-safe + KHÔNG ghi
# audit/lifecycle (read-only, đồng nhất A2). KHÔNG leak field nhạy cảm. RED trước.
# ──────────────────────────────────────────────────────────────────────────


class TestAssetScanInfo(unittest.TestCase):
    """A6 — endpoint get_asset_scan_info: 200 shape / 404 / 403 gate / 403 IDOR /
    no-audit / recent_maintenance gần nhất. RED viết TRƯỚC impl."""

    # Field nghiệp vụ NHẠY CẢM tuyệt đối KHÔNG được lọt vào payload màn quét.
    _SENSITIVE_KEYS = {
        "gross_purchase_amount", "purchase_cost", "accumulated_depreciation",
        "depreciation_method", "depreciation_schedule", "current_hash",
        "previous_hash", "supplier",
    }
    _CORE_KEYS = {
        "name", "asset_code", "asset_name", "device_model_name",
        "location_name", "lifecycle_status", "recent_maintenance",
        "next_pm_date",
    }

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Scan Info (A6)",
            "description": "Category cho test get_asset_scan_info",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix="", **extra):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy Scan {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"SI-SN-{uniq}",
            "asset_code": f"SI-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _add_ale(self, asset_name, event_type, timestamp):
        """Append 1 Asset Lifecycle Event với timestamp xác định (test fixture).

        ``create_lifecycle_event`` luôn stamp ``now_datetime()`` → để kiểm "lấy
        sự kiện gần nhất" cần timestamp khác nhau; set NGAY trong insert dict
        (field mandatory). KHÔNG đổi canonical helper chỉ vì test."""
        frappe.get_doc({
            "doctype": "Asset Lifecycle Event",
            "asset": asset_name, "event_type": event_type,
            "timestamp": timestamp,
            "actor": "Administrator", "from_status": "", "to_status": "",
            "root_doctype": "AC Asset", "root_record": asset_name,
            "notes": f"test ALE {event_type}",
        }).insert(ignore_permissions=True)

    # ── 200 — token hợp lệ trả payload mobile cốt lõi, KHÔNG leak nhạy cảm ────
    def test_scan_info_valid_token_returns_core_payload(self):
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("ok", next_pm_date=add_days(nowdate(), 30))
        resp = get_asset_scan_info(token=asset.qr_token)
        self.assertTrue(resp["success"], "token hợp lệ → success")
        data = resp["data"]
        self.assertEqual(data["name"], asset.name)
        self.assertEqual(data["asset_code"], asset.asset_code)
        self.assertEqual(data["asset_name"], asset.asset_name)
        self.assertEqual(data["lifecycle_status"], "Active",
                         "BE trả mã canonical (FE dịch qua SSoT), KHÔNG nhãn VI thô")
        for k in self._CORE_KEYS:
            self.assertIn(k, data, f"payload mobile cốt lõi PHẢI có '{k}'")
        self.assertIn("device_model_name", data)
        self.assertIn("location_name", data)

    def test_scan_info_does_not_leak_sensitive_fields(self):
        """KHÔNG trả giá mua / khấu hao / audit chain / supplier code nội bộ."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("nosens", gross_purchase_amount=999000000)
        data = get_asset_scan_info(token=asset.qr_token)["data"]
        leaked = self._SENSITIVE_KEYS & set(data.keys())
        self.assertFalse(leaked, f"payload màn quét KHÔNG được chứa field nhạy cảm: {leaked}")

    # ── resolve theo name (deep-link /assets/:id/info) ──────────────────────
    def test_scan_info_by_name_returns_payload(self):
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("byname")
        resp = get_asset_scan_info(name=asset.name)
        self.assertTrue(resp["success"], "resolve theo name → success")
        self.assertEqual(resp["data"]["name"], asset.name)

    # ── 404 — token/name sai / không tồn tại / rỗng → leak-safe, KHÔNG 500 ───
    def test_scan_info_unknown_token_returns_404(self):
        from assetcore.api.imm00 import get_asset_scan_info
        resp = get_asset_scan_info(token="khong-ton-tai-zzzzzzzzzzzzzzzzz")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 404, "token sai → 404, KHÔNG 500")

    def test_scan_info_empty_returns_404_no_full_scan(self):
        """token/name rỗng (hoặc param vắng) → 404 leak-safe, KHÔNG full-scan, KHÔNG 417."""
        from assetcore.api.imm00 import get_asset_scan_info
        for resp in (get_asset_scan_info(token=""), get_asset_scan_info(),
                     get_asset_scan_info(name="")):
            self.assertFalse(resp["success"], "rỗng → KHÔNG success")
            self.assertIn(resp["http_status"], (400, 404),
                          "rỗng → 400/404, KHÔNG 500/417")

    def test_scan_info_unknown_name_returns_404(self):
        """name không tồn tại trả CÙNG 404 như token sai (KHÔNG phân biệt)."""
        from assetcore.api.imm00 import get_asset_scan_info
        resp = get_asset_scan_info(name="AC-ASSET-KHONG-TON-TAI-9999")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 404)

    # ── 403 — user KHÔNG có asset.read ──────────────────────────────────────
    def test_scan_info_without_capability_raises_permission(self):
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("noperm")
        token = asset.qr_token
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                get_asset_scan_info(token=token)
        finally:
            frappe.set_user("Administrator")

    # ── 403 — IDOR / vendor isolation (tái dùng assert_vendor_can_access) ────
    def test_scan_info_vendor_out_of_scope_forbidden_no_leak(self):
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("idor")
        token = asset.qr_token
        vendor_email = "vendor_a6_idor@example.com"
        if frappe.db.exists("User", vendor_email):
            frappe.delete_doc("User", vendor_email, force=True,
                              ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": vendor_email,
            "first_name": "Vendor A6 IDOR", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        u.add_roles("Vendor Engineer", "Repair User")
        frappe.db.commit()
        frappe.set_user(vendor_email)
        try:
            resp = get_asset_scan_info(token=token)
            self.assertFalse(resp["success"], "vendor ngoài scope → KHÔNG success")
            self.assertEqual(resp["http_status"], 403, "vendor ngoài scope → 403 IDOR")
            self.assertNotIn("asset_code", resp.get("data") or {},
                             "KHÔNG leak payload asset ngoài scope")
        finally:
            frappe.set_user("Administrator")
            if frappe.db.exists("User", vendor_email):
                frappe.delete_doc("User", vendor_email,
                                  force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── No-side-effect — read-only KHÔNG ghi audit/lifecycle (đồng nhất A2) ──
    def test_scan_info_no_side_effect(self):
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("noaudit")
        # tạo sẵn 1 ALE để asset có lịch sử (đếm phải bằng nhau trước/sau gọi).
        self._add_ale(asset.name, "pm_completed", add_days(nowdate(), -5))
        before_audit = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        before_ale = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        get_asset_scan_info(token=asset.qr_token)
        self.assertEqual(frappe.db.count("IMM Audit Trail", {"asset": asset.name}),
                         before_audit, "scan info KHÔNG ghi IMM Audit Trail")
        self.assertEqual(frappe.db.count("Asset Lifecycle Event", {"asset": asset.name}),
                         before_ale, "scan info KHÔNG ghi Asset Lifecycle Event")

    # ── recent_maintenance — lấy ĐÚNG sự kiện gần nhất (ORDER BY timestamp DESC) ─
    def test_scan_info_recent_maintenance_picks_latest(self):
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("recent")
        self._add_ale(asset.name, "pm_completed", add_days(nowdate(), -30))
        self._add_ale(asset.name, "pm_completed", add_days(nowdate(), -3))
        data = get_asset_scan_info(token=asset.qr_token)["data"]
        rm = data["recent_maintenance"]
        self.assertIsNotNone(rm, "asset có ALE bảo trì → recent_maintenance KHÔNG null")
        self.assertEqual(rm["event_type"], "pm_completed")
        self.assertEqual(str(getdate(rm["date"])), str(getdate(add_days(nowdate(), -3))),
                         "recent_maintenance phải là sự kiện MỚI NHẤT (DESC LIMIT 1)")

    def test_scan_info_recent_maintenance_null_when_none(self):
        """Asset chưa có sự kiện bảo trì → recent_maintenance null/empty, KHÔNG lỗi."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("nomaint")
        data = get_asset_scan_info(token=asset.qr_token)["data"]
        self.assertIn("recent_maintenance", data)
        self.assertFalse(data["recent_maintenance"],
                         "không có bảo trì → recent_maintenance falsy (null/empty)")


# ──────────────────────────────────────────────────────────────────────────
# A6 hardening — cờ pm_overdue (PM quá hạn) trên màn THÔNG TIN khi quét QR.
# SSoT overdue ở BE (server-side, timezone-safe): True ⟺ next_pm_date không rỗng
# ∧ getdate(next_pm_date) < getdate(nowdate()) ∧ lifecycle_status KHÔNG thuộc tập
# ngừng-vĩnh-viễn (Decommissioned). Mọi nhánh khác → False. KHÔNG endpoint/field
# nhạy cảm mới; payload giữ 8 field cũ + đúng 1 field pm_overdue. RED viết TRƯỚC.
# ──────────────────────────────────────────────────────────────────────────


class TestAssetScanInfoPmOverdue(unittest.TestCase):
    """A6 hardening — derive pm_overdue server-side. FE CHỈ render cờ (KHÔNG so
    ngày client → chống lệch timezone). RED viết TRƯỚC impl."""

    # 8 field hiện có của payload scan-info (regression: KHÔNG thêm/bớt ngoài
    # đúng 1 field pm_overdue mới).
    _EXISTING_KEYS = {
        "name", "asset_code", "asset_name", "device_model_name",
        "location_name", "lifecycle_status", "recent_maintenance",
        "next_pm_date",
    }
    _SENSITIVE_KEYS = {
        "gross_purchase_amount", "purchase_cost", "accumulated_depreciation",
        "depreciation_method", "depreciation_schedule", "current_hash",
        "previous_hash", "supplier",
    }

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị PM Overdue (A6)",
            "description": "Category cho test pm_overdue scan-info",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix="", status="Active", **extra):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy PMOverdue {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"PMO-SN-{uniq}",
            "asset_code": f"PMO-ASSET-{uniq}",
            "lifecycle_status": status,
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _scan(self, asset):
        from assetcore.api.imm00 import get_asset_scan_info
        return get_asset_scan_info(token=asset.qr_token)["data"]

    # ── True ⟺ next_pm_date quá khứ ∧ status đang dùng ──────────────────────
    def test_scan_info_pm_overdue_true_when_next_pm_in_past(self):
        asset = self._make_asset("past", next_pm_date=add_days(nowdate(), -1))
        data = self._scan(asset)
        self.assertIn("pm_overdue", data, "payload PHẢI có field pm_overdue")
        self.assertIs(data["pm_overdue"], True,
                      "next_pm_date < hôm nay ∧ status đang dùng → pm_overdue=True")

    # ── False — next_pm_date tương lai ──────────────────────────────────────
    def test_scan_info_pm_overdue_false_when_next_pm_future(self):
        asset = self._make_asset("future", next_pm_date=add_days(nowdate(), 7))
        self.assertIs(self._scan(asset)["pm_overdue"], False,
                      "next_pm_date > hôm nay → KHÔNG quá hạn")

    # ── False — boundary: next_pm_date == hôm nay (chưa quá hạn) ─────────────
    def test_scan_info_pm_overdue_false_when_next_pm_today(self):
        asset = self._make_asset("today", next_pm_date=nowdate())
        self.assertIs(self._scan(asset)["pm_overdue"], False,
                      "next_pm_date == hôm nay → CHƯA quá hạn (so sánh strict <)")

    # ── False — next_pm_date NULL (chưa lên lịch) KHÔNG raise ────────────────
    def test_scan_info_pm_overdue_false_when_next_pm_null(self):
        asset = self._make_asset("null")  # KHÔNG set next_pm_date
        data = self._scan(asset)
        self.assertIsNone(data["next_pm_date"], "fixture: next_pm_date rỗng")
        self.assertIs(data["pm_overdue"], False,
                      "next_pm_date NULL → False, KHÔNG raise")

    # ── False — status ngừng-dùng-vĩnh-viễn (BLOCKED_FOR_WO) dù ngày quá khứ ──
    def test_scan_info_pm_overdue_false_when_status_retired(self):
        """next_pm_date quá khứ NHƯNG status ∈ BLOCKED_FOR_WO → False (BR-00-36).

        'retired/decommissioned/ngừng-vĩnh-viễn' = AssetStatus.BLOCKED_FOR_WO =
        ('Out of Service', 'Decommissioned'). Kiểm CẢ HAI mã canonical (KHÔNG chỉ
        Decommissioned — Out of Service cũng ngừng dùng, KHÔNG cờ quá hạn)."""
        from assetcore.services.shared.constants import AssetStatus
        for i, status in enumerate(AssetStatus.BLOCKED_FOR_WO):
            with self.subTest(status=status):
                asset = self._make_asset(f"blk{i}", status=status,
                                         next_pm_date=add_days(nowdate(), -30))
                self.assertIs(self._scan(asset)["pm_overdue"], False,
                              f"status '{status}' ∈ BLOCKED_FOR_WO → KHÔNG cờ quá hạn dù ngày quá khứ")

    # ── True — status downtime KHÔNG-vĩnh-viễn (Under Repair) vẫn cờ ──────────
    def test_scan_info_pm_overdue_true_when_under_repair_past_due(self):
        """Chỉ Out of Service + Decommissioned bị loại — Under Repair vẫn tính cờ."""
        asset = self._make_asset("repair", status="Under Repair",
                                 next_pm_date=add_days(nowdate(), -7))
        self.assertIs(self._scan(asset)["pm_overdue"], True,
                      "Under Repair ∉ BLOCKED_FOR_WO → quá hạn vẫn cờ True")

    # ── White-box — mốc so là nowdate() server (timezone-safe), KHÔNG client ──
    def test_pm_overdue_uses_server_nowdate_not_client(self):
        from assetcore.services.imm00 import _is_pm_overdue
        self.assertIs(_is_pm_overdue(add_days(nowdate(), -1), "Active"), True)
        self.assertIs(_is_pm_overdue(add_days(nowdate(), 1), "Active"), False)
        self.assertIs(_is_pm_overdue(nowdate(), "Active"), False,
                      "đúng nowdate() server → False (strict <)")

    # ── Guard rỗng GIỮ NGUYÊN → None (KHÔNG raise vì thêm pm_overdue) ─────────
    def test_pm_overdue_guard_empty_asset_returns_none(self):
        from assetcore.services.imm00 import build_asset_scan_info
        self.assertIsNone(build_asset_scan_info(""),
                          "asset_name rỗng → None (guard giữ nguyên)")
        self.assertIsNone(build_asset_scan_info(None),
                          "asset_name None → None (KHÔNG raise)")

    # ── Regression — giữ ĐÚNG 8 field cũ + pm_overdue + 2 field hiệu chuẩn ────
    # FR-00-86: payload bổ sung next_calibration_date + calibration_overdue (Vòng
    # 28 B) — KHÔNG mất/đổi field cũ. Whitelist mở rộng đúng 2 key calibration.
    _CALIBRATION_KEYS = {"next_calibration_date", "calibration_overdue"}

    def test_scan_info_payload_keeps_8_existing_fields_plus_pm_overdue(self):
        asset = self._make_asset("shape", next_pm_date=add_days(nowdate(), -1))
        data = self._scan(asset)
        for k in self._EXISTING_KEYS:
            self.assertIn(k, data, f"payload PHẢI giữ field cũ '{k}'")
        self.assertEqual(
            set(data.keys()),
            self._EXISTING_KEYS | {"pm_overdue"} | self._CALIBRATION_KEYS,
            "payload = 8 field cũ + pm_overdue + 2 field hiệu chuẩn (KHÔNG dư)",
        )
        leaked = self._SENSITIVE_KEYS & set(data.keys())
        self.assertFalse(leaked, f"KHÔNG leak field nhạy cảm: {leaked}")

    # ── No-side-effect — derive pm_overdue KHÔNG ghi audit/lifecycle ─────────
    def test_scan_info_no_side_effect_with_pm_overdue(self):
        asset = self._make_asset("noeffect", next_pm_date=add_days(nowdate(), -2))
        before_audit = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        before_ale = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        data = self._scan(asset)
        self.assertIs(data["pm_overdue"], True)  # đảm bảo nhánh derive được chạy
        self.assertEqual(frappe.db.count("IMM Audit Trail", {"asset": asset.name}),
                         before_audit, "derive pm_overdue KHÔNG ghi IMM Audit Trail")
        self.assertEqual(frappe.db.count("Asset Lifecycle Event", {"asset": asset.name}),
                         before_ale, "derive pm_overdue KHÔNG ghi Asset Lifecycle Event")


class TestAssetScanInfoCalibrationOverdue(unittest.TestCase):
    """A6 hardening (FR-00-86 / BR-00-37, Vòng 28 B) — derive calibration_overdue
    server-side. Chiều HIỆU CHUẨN song song với pm_overdue: FE CHỈ render cờ
    (KHÔNG so ngày client → chống lệch timezone). RED viết TRƯỚC impl.

    next_calibration_date là field AC Asset đã có (ac_asset.json:453, Date
    read_only) — ZERO schema delta. KHÔNG mock getdate/nowdate; set ngày THẬT
    quanh nowdate() để đo đúng biên strict ``<``."""

    # 9 field hiện có của payload scan-info SAU khi đã thêm pm_overdue (regression:
    # 9 field GIỮ NGUYÊN tên + giá trị khi thêm 2 field hiệu chuẩn).
    _EXISTING_KEYS = {
        "name", "asset_code", "asset_name", "device_model_name",
        "location_name", "lifecycle_status", "recent_maintenance",
        "next_pm_date", "pm_overdue",
    }

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Cal Overdue (A6)",
            "description": "Category cho test calibration_overdue scan-info",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix="", status="Active", **extra):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy CalOverdue {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"CALO-SN-{uniq}",
            "asset_code": f"CALO-ASSET-{uniq}",
            "lifecycle_status": status,
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _scan(self, asset):
        from assetcore.api.imm00 import get_asset_scan_info
        return get_asset_scan_info(token=asset.qr_token)["data"]

    # ── Field-whitelist delta — 2 key MỚI + 9 field FR-00-85 GIỮ NGUYÊN ──────
    def test_payload_has_calibration_fields_9_fields_intact(self):
        asset = self._make_asset("shape",
                                 next_calibration_date=add_days(nowdate(), -1))
        data = self._scan(asset)
        # 2 key calibration mới có mặt + đúng kiểu.
        self.assertIn("next_calibration_date", data,
                      "payload PHẢI có field next_calibration_date")
        self.assertIn("calibration_overdue", data,
                      "payload PHẢI có field calibration_overdue")
        self.assertIsInstance(data["calibration_overdue"], bool,
                              "calibration_overdue PHẢI là bool")
        self.assertIsInstance(data["next_calibration_date"], (str, type(None)),
                              "next_calibration_date PHẢI là str|None")
        # 9 field FR-00-85 GIỮ NGUYÊN tên.
        for k in self._EXISTING_KEYS:
            self.assertIn(k, data, f"payload PHẢI giữ field cũ '{k}'")
        self.assertEqual(
            set(data.keys()),
            self._EXISTING_KEYS | {"next_calibration_date", "calibration_overdue"},
            "payload = 9 field cũ + đúng 2 field hiệu chuẩn (KHÔNG dư/thiếu)",
        )

    # ── True ⟺ next_calibration_date quá khứ ∧ status đang dùng ──────────────
    def test_calibration_overdue_true_when_past_date_active(self):
        asset = self._make_asset("past", status="Active",
                                 next_calibration_date=add_days(nowdate(), -1))
        data = self._scan(asset)
        self.assertIs(data["calibration_overdue"], True,
                      "next_calibration_date < hôm nay ∧ status đang dùng → True")

    # ── False — next_calibration_date NULL/rỗng (chưa lên lịch) KHÔNG raise ───
    def test_calibration_overdue_false_when_next_cal_null(self):
        asset = self._make_asset("null")  # KHÔNG set next_calibration_date
        data = self._scan(asset)
        self.assertIsNone(data["next_calibration_date"],
                          "fixture: next_calibration_date rỗng → None")
        self.assertIs(data["calibration_overdue"], False,
                      "next_calibration_date NULL → False, KHÔNG raise")

    # ── False — boundary: next_calibration_date == hôm nay (STRICT <) ─────────
    def test_calibration_overdue_false_when_today(self):
        asset = self._make_asset("today", next_calibration_date=nowdate())
        self.assertIs(self._scan(asset)["calibration_overdue"], False,
                      "next_calibration_date == hôm nay → CHƯA quá hạn (strict <)")

    # ── False — boundary: next_calibration_date tương lai ────────────────────
    def test_calibration_overdue_false_when_future(self):
        asset = self._make_asset("future",
                                 next_calibration_date=add_days(nowdate(), 1))
        self.assertIs(self._scan(asset)["calibration_overdue"], False,
                      "next_calibration_date > hôm nay → KHÔNG quá hạn")

    # ── False — status ngừng-dùng-vĩnh-viễn (BLOCKED_FOR_WO) dù ngày quá khứ ──
    def test_calibration_overdue_false_when_out_of_service(self):
        asset = self._make_asset("oos", status="Out of Service",
                                 next_calibration_date=add_days(nowdate(), -30))
        self.assertIs(self._scan(asset)["calibration_overdue"], False,
                      "Out of Service ∈ BLOCKED_FOR_WO → KHÔNG cờ dù ngày quá khứ")

    def test_calibration_overdue_false_when_decommissioned(self):
        asset = self._make_asset("dec", status="Decommissioned",
                                 next_calibration_date=add_days(nowdate(), -30))
        self.assertIs(self._scan(asset)["calibration_overdue"], False,
                      "Decommissioned ∈ BLOCKED_FOR_WO → KHÔNG cờ dù ngày quá khứ")

    # ── White-box — mốc so là nowdate() server (timezone-safe), STRICT < ──────
    def test_calibration_overdue_uses_server_nowdate_strict(self):
        from assetcore.services.imm00 import _is_calibration_overdue
        self.assertIs(_is_calibration_overdue(add_days(nowdate(), -1), "Active"), True)
        self.assertIs(_is_calibration_overdue(add_days(nowdate(), 1), "Active"), False)
        self.assertIs(_is_calibration_overdue(nowdate(), "Active"), False,
                      "đúng nowdate() server → False (strict <)")
        self.assertIs(_is_calibration_overdue(None, "Active"), False,
                      "ngày None → False (KHÔNG raise)")

    # ── No-side-effect — derive calibration_overdue KHÔNG ghi audit/lifecycle ─
    def test_calibration_overdue_no_side_effect(self):
        asset = self._make_asset("noeffect",
                                 next_calibration_date=add_days(nowdate(), -2))
        before_audit = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        before_ale = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        data = self._scan(asset)
        self.assertIs(data["calibration_overdue"], True)  # nhánh derive được chạy
        self.assertEqual(frappe.db.count("IMM Audit Trail", {"asset": asset.name}),
                         before_audit, "derive calibration_overdue KHÔNG ghi audit")
        self.assertEqual(frappe.db.count("Asset Lifecycle Event", {"asset": asset.name}),
                         before_ale, "derive calibration_overdue KHÔNG ghi lifecycle")


# ──────────────────────────────────────────────────────────────────────────
# A3 — Dữ liệu in nhãn QR + sự kiện in (ADR-001 D3)
# get_asset_label_data (1) + get_asset_label_data_batch (batch, KHÔNG N+1) +
# mark_label_printed (POST emit label_printed + audit). RED viết TRƯỚC impl.
# ──────────────────────────────────────────────────────────────────────────


class TestAssetLabelData(unittest.TestCase):
    """A3 — endpoint dữ liệu in nhãn + sự kiện in (get/batch/mark)."""

    _LABEL_KEYS = {
        "name", "asset_code", "device_model_name", "location_name",
        "lifecycle_status", "qr_url",
    }
    _QR_URL_RE = r"^https?://.+/a/[A-Za-z0-9_-]{20,}$"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị In nhãn (A3)",
            "description": "Category cho test get_asset_label_data",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix="", with_token=True):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy Nhãn {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"LB-SN-{uniq}",
            "asset_code": f"LB-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        if not with_token:
            frappe.db.set_value("AC Asset", doc.name, "qr_token", None,
                                update_modified=False)
            doc.reload()
        return doc

    def _count_label_events(self, asset_name):
        return frappe.db.count("Asset Lifecycle Event",
                               {"asset": asset_name, "event_type": "label_printed"})

    def _count_audit(self, asset_name):
        return frappe.db.count("IMM Audit Trail", {"asset": asset_name})

    # ── payload shape — 6 key + qr_url tuyệt đối ────────────────────────────
    def test_get_asset_label_data_payload_shape(self):
        from assetcore.api.imm00 import get_asset_label_data
        asset = self._make_asset("shape")
        resp = get_asset_label_data(asset=asset.name)
        self.assertTrue(resp["success"], "asset hợp lệ → success")
        data = resp["data"]
        self.assertEqual(set(data.keys()), self._LABEL_KEYS,
                         "payload nhãn PHẢI đúng 6 key (không thiếu/thừa)")
        self.assertEqual(data["name"], asset.name)
        self.assertEqual(data["asset_code"], asset.asset_code)
        self.assertEqual(data["lifecycle_status"], "Active")
        self.assertRegex(data["qr_url"], self._QR_URL_RE,
                         "qr_url phải là URL tuyệt đối /a/<token>")
        self.assertIn("/a/", data["qr_url"])
        self.assertIn(asset.qr_token, data["qr_url"],
                      "qr_url phải chứa đúng token của asset")

    # ── token-less asset → ensure token → qr_url KHÔNG rỗng (BR-00-28) ───────
    def test_get_asset_label_data_ensures_token(self):
        from assetcore.api.imm00 import get_asset_label_data
        asset = self._make_asset("ensure", with_token=False)
        self.assertFalsy = self.assertFalse
        self.assertFalse(
            frappe.db.get_value("AC Asset", asset.name, "qr_token"),
            "tiền đề: asset chưa có qr_token")
        resp = get_asset_label_data(asset=asset.name)
        self.assertTrue(resp["success"])
        data = resp["data"]
        self.assertTrue(data["qr_url"], "qr_url KHÔNG rỗng (BR-00-28)")
        self.assertRegex(data["qr_url"], self._QR_URL_RE)
        self.assertNotRegex(data["qr_url"], r"/a/$",
                            "qr_url KHÔNG được kết thúc '/a/' (token rỗng)")
        # ensure đã ghi token vào DB
        self.assertTrue(frappe.db.get_value("AC Asset", asset.name, "qr_token"),
                        "ensure_asset_qr_token sinh token idempotent")

    # ── GET read-only về sự kiện in: KHÔNG emit label_printed/audit ──────────
    def test_get_asset_label_data_is_readonly_no_emit(self):
        from assetcore.api.imm00 import get_asset_label_data
        asset = self._make_asset("readonly")
        before_label = self._count_label_events(asset.name)
        before_audit = self._count_audit(asset.name)
        get_asset_label_data(asset=asset.name)
        get_asset_label_data(asset=asset.name)  # gọi nhiều lần preview
        self.assertEqual(self._count_label_events(asset.name), before_label,
                         "GET KHÔNG emit label_printed (read-only về print event)")
        self.assertEqual(self._count_audit(asset.name), before_audit,
                         "GET KHÔNG ghi IMM Audit Trail (preview ≠ in)")

    # ── batch: thứ tự = input, KHÔNG N+1, missing → entry lỗi giữ index ──────
    def test_get_asset_label_data_batch_order_and_no_n_plus_1(self):
        from assetcore.api.imm00 import get_asset_label_data_batch
        a1 = self._make_asset("b1")
        a2 = self._make_asset("b2")
        a3 = self._make_asset("b3")
        names = [a1.name, a2.name, a3.name]
        resp = get_asset_label_data_batch(assets=names)
        self.assertTrue(resp["success"])
        data = resp["data"]
        self.assertEqual(len(data), 3, "batch trả đúng số lượng input")
        # thứ tự khớp input
        self.assertEqual([d["name"] for d in data], names,
                         "output theo ĐÚNG thứ tự input")
        for d in data:
            self.assertEqual(set(d.keys()), self._LABEL_KEYS)
            self.assertRegex(d["qr_url"], self._QR_URL_RE)

    def test_get_asset_label_data_batch_missing_keeps_index(self):
        from assetcore.api.imm00 import get_asset_label_data_batch
        a1 = self._make_asset("m1")
        a2 = self._make_asset("m2")
        # asset giữa KHÔNG tồn tại → entry lỗi tại đúng index (KHÔNG drop)
        names = [a1.name, "AC-ASSET-NONEXISTENT-XYZ", a2.name]
        resp = get_asset_label_data_batch(assets=names)
        self.assertTrue(resp["success"])
        data = resp["data"]
        self.assertEqual(len(data), 3, "missing KHÔNG bị drop → giữ index")
        self.assertEqual(data[0]["name"], a1.name)
        self.assertNotIn("error", data[0])
        self.assertEqual(data[1]["name"], "AC-ASSET-NONEXISTENT-XYZ")
        self.assertEqual(data[1].get("error"), "AC-E001",
                         "missing → entry lỗi rõ ràng AC-E001")
        self.assertNotIn("asset_code", data[1],
                         "entry lỗi KHÔNG leak field khác")
        self.assertEqual(data[2]["name"], a2.name)
        self.assertNotIn("error", data[2])

    def test_get_asset_label_data_batch_no_n_plus_1_query_count(self):
        """Batch lookup gộp: số query KHÔNG tỉ lệ với số asset (chống N+1)."""
        from assetcore.api.imm00 import get_asset_label_data_batch
        assets3 = [self._make_asset(f"q3-{i}").name for i in range(3)]
        assets6 = [self._make_asset(f"q6-{i}").name for i in range(6)]

        def _count_queries(names):
            calls = {"n": 0}
            orig = frappe.db.sql

            def _wrap(*a, **k):
                calls["n"] += 1
                return orig(*a, **k)

            frappe.db.sql = _wrap
            try:
                get_asset_label_data_batch(assets=names)
            finally:
                frappe.db.sql = orig
            return calls["n"]

        q3 = _count_queries(assets3)
        q6 = _count_queries(assets6)
        # N+1 → q6 ≈ 2*q3. Gộp → q6 ≈ q3 (chênh nhỏ). Cho biên rộng: q6 < q3 + 6.
        self.assertLess(q6, q3 + len(assets6),
                        f"batch KHÔNG N+1: q3={q3} q6={q6} (gộp, KHÔNG loop/asset)")

    def test_get_asset_label_data_batch_empty_returns_empty(self):
        from assetcore.api.imm00 import get_asset_label_data_batch
        resp = get_asset_label_data_batch(assets=[])
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"], [], "input rỗng → data rỗng (200)")

    # ── mark_label_printed: 1 event + 1 audit / asset / lần in ──────────────
    def test_mark_label_printed_emits_one_event_per_asset(self):
        from assetcore.api.imm00 import mark_label_printed
        a1 = self._make_asset("mk1")
        a2 = self._make_asset("mk2")
        before1 = self._count_label_events(a1.name)
        before2 = self._count_label_events(a2.name)
        audit_b1 = self._count_audit(a1.name)
        audit_b2 = self._count_audit(a2.name)
        resp = mark_label_printed(assets=[a1.name, a2.name])
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"]["event_count"], 2)
        self.assertEqual(resp["data"]["printed"], [a1.name, a2.name])
        # đúng 1 event / asset
        self.assertEqual(self._count_label_events(a1.name), before1 + 1)
        self.assertEqual(self._count_label_events(a2.name), before2 + 1)
        # đúng 1 audit / asset
        self.assertEqual(self._count_audit(a1.name), audit_b1 + 1)
        self.assertEqual(self._count_audit(a2.name), audit_b2 + 1)
        # root_doctype/root_record khớp
        ev = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": a1.name, "event_type": "label_printed"},
            fields=["root_doctype", "root_record"], limit=1)
        self.assertEqual(ev[0]["root_doctype"], "AC Asset")
        self.assertEqual(ev[0]["root_record"], a1.name)

    def test_mark_label_printed_idempotent_count(self):
        """Gọi N lần in → N event/asset (mỗi lần in = 1 event, đúng nghiệp vụ)."""
        from assetcore.api.imm00 import mark_label_printed
        a1 = self._make_asset("idem")
        before = self._count_label_events(a1.name)
        mark_label_printed(assets=[a1.name])
        mark_label_printed(assets=[a1.name])
        self.assertEqual(self._count_label_events(a1.name), before + 2,
                         "2 lần in = 2 event label_printed (KHÔNG dedup)")

    def test_mark_label_printed_all_or_nothing_missing_asset(self):
        """≥1 asset không tồn tại → 404, KHÔNG ghi event nào (all-or-nothing)."""
        from assetcore.api.imm00 import mark_label_printed
        a1 = self._make_asset("aon")
        before = self._count_label_events(a1.name)
        resp = mark_label_printed(assets=[a1.name, "AC-ASSET-NONEXISTENT-XYZ"])
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 404)
        self.assertEqual(self._count_label_events(a1.name), before,
                         "KHÔNG ghi event nào khi 1 asset không tồn tại")

    # ── RBAC: cả 3 endpoint gate (no-cap Guest → 403; vòng B siết asset.write) ─
    def test_label_endpoints_require_asset_read(self):
        """Guest (KHÔNG có cap nào) → 403 cho cả 3 endpoint in nhãn.

        Vòng B siết gate asset.read→asset.write; Guest KHÔNG có read LẪN write nên
        vẫn 403 (giữ test này). Phân-tách read-only-user vs write-user đo riêng ở
        TestLabelWriteCapability (user THẬT có/không asset.write).
        """
        from assetcore.api.imm00 import (
            get_asset_label_data, get_asset_label_data_batch, mark_label_printed,
        )
        asset = self._make_asset("gate")
        name = asset.name
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                get_asset_label_data(asset=name)
            with self.assertRaises(frappe.PermissionError):
                get_asset_label_data_batch(assets=[name])
            with self.assertRaises(frappe.PermissionError):
                mark_label_printed(assets=[name])
        finally:
            frappe.set_user("Administrator")

    # ── 404 leak-safe — asset không tồn tại ─────────────────────────────────
    def test_label_data_404_leak_safe(self):
        from assetcore.api.imm00 import get_asset_label_data
        resp = get_asset_label_data(asset="AC-ASSET-NONEXISTENT-XYZ")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 404, "không tồn tại → 404, KHÔNG 500")
        # leak-safe: KHÔNG trả field nội bộ
        self.assertNotIn("asset_code", resp.get("data") or {})

    # ── IDOR — vendor ngoài scope → 403 (mirror A2) ─────────────────────────
    def test_label_idor_vendor_scope(self):
        """Vendor CÓ asset.write nhưng asset NGOÀI scope → 403 IDOR.

        Vòng B siết gate read→write: user vendor phải CÓ asset.write để qua gate
        WRITE rồi mới đập IDOR (assert_vendor_can_access). Chỉ "AssetCore Super
        Admin" có write DocPerm sẵn (và là bypass-IDOR) → cấp write tạm cho role
        Vendor Engineer (Custom DocPerm, KHÔNG cap mới), gỡ ở finally. Siết RBAC
        KHÔNG nới IDOR.
        """
        from frappe.permissions import add_permission, update_permission_property
        from assetcore.api.imm00 import get_asset_label_data, mark_label_printed
        from assetcore.services.shared import rbac
        asset = self._make_asset("idor")
        name = asset.name
        role = "Vendor Engineer"
        vendor_email = "vendor_a3_idor@example.com"
        if frappe.db.exists("User", vendor_email):
            frappe.delete_doc("User", vendor_email, force=True,
                              ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": vendor_email,
            "first_name": "Vendor A3 IDOR", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        # Vendor Engineer (scope-restrict, KHÔNG bypass-IDOR) + Repair User.
        u.add_roles("Vendor Engineer", "Repair User")
        # Cấp write tạm cho Vendor Engineer trên AC Asset → user qua gate WRITE
        # NHƯNG bị chặn ở IDOR (asset ngoài WO được giao). DATA, KHÔNG cap mới.
        add_permission("AC Asset", role, 0)
        update_permission_property("AC Asset", role, 0, "write", 1)
        frappe.clear_cache()
        frappe.db.commit()
        frappe.set_user(vendor_email)
        try:
            resp = get_asset_label_data(asset=name)
            self.assertFalse(resp["success"], "vendor ngoài scope → KHÔNG success")
            self.assertEqual(resp["http_status"], 403,
                             "get_asset_label_data IDOR → 403 (siết RBAC KHÔNG nới IDOR)")
            self.assertNotIn("asset_code", resp.get("data") or {},
                             "KHÔNG leak payload asset ngoài scope")
            resp2 = mark_label_printed(assets=[name])
            self.assertFalse(resp2["success"])
            self.assertEqual(resp2["http_status"], 403,
                             "mark_label_printed IDOR → 403 (siết RBAC KHÔNG nới IDOR)")
        finally:
            frappe.set_user("Administrator")
            cp = frappe.db.get_value(
                "Custom DocPerm",
                {"parent": "AC Asset", "role": role, "permlevel": 0}, "name")
            if cp:
                frappe.delete_doc("Custom DocPerm", cp, force=True,
                                  ignore_permissions=True)
            frappe.clear_cache()
            rbac.invalidate_capabilities(vendor_email)
            if frappe.db.exists("User", vendor_email):
                frappe.delete_doc("User", vendor_email,
                                  force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── Vòng B (BR-00-33) — CAP batch-size: DoS payload guard (413) ──────────
    # SSoT: services.imm00._MAX_LABEL_BATCH (KHÔNG literal lặp ở api layer).
    # Cap-check chạy SAU rbac.require('asset.write'), TRƯỚC vòng exists/IDOR +
    # service → len>cap = 413 (bucket RIÊNG), KHÔNG build payload / ghi event.
    def _cap(self):
        from assetcore.services import imm00 as _svc
        return _svc._MAX_LABEL_BATCH

    def test_batch_read_at_limit_ok(self):
        """len(names)==_MAX_LABEL_BATCH → KHÔNG 413, trả list đúng (mix valid + AC-E001)."""
        from assetcore.api.imm00 import get_asset_label_data_batch
        cap = self._cap()
        a1 = self._make_asset("cap-ok-1")
        a2 = self._make_asset("cap-ok-2")
        # Đệm tên KHÔNG tồn tại tới ĐÚNG cap → entry AC-E001 (KHÔNG cần 200 asset thật).
        fakes = [f"AC-ASSET-CAP-MISS-{i:04d}" for i in range(cap - 2)]
        names = [a1.name, *fakes, a2.name]
        self.assertEqual(len(names), cap, "tiền đề: len == cap (biên dưới đúng)")
        resp = get_asset_label_data_batch(assets=names)
        self.assertTrue(resp["success"], "len==cap → KHÔNG 413 (biên PASS)")
        data = resp["data"]
        self.assertEqual(len(data), cap, "trả đủ N entry giữ index")
        self.assertEqual(data[0]["name"], a1.name)
        self.assertNotIn("error", data[0], "asset thật → payload đầy đủ")
        self.assertEqual(data[-1]["name"], a2.name)
        self.assertNotIn("error", data[-1])
        self.assertEqual(data[1].get("error"), "AC-E001", "tên giả → AC-E001 giữ index")

    def test_batch_read_over_limit_413(self):
        """len==_MAX_LABEL_BATCH+1 → 413, message VI cố định, KHÔNG build payload/leak name."""
        from assetcore.api.imm00 import get_asset_label_data_batch
        from assetcore.services.imm00 import _ERR_BATCH_TOO_LARGE
        a1 = self._make_asset("cap-over")
        # 1 asset thật + đệm giả → vượt cap đúng 1. Cap chặn TRƯỚC exists → tên giả vô hại.
        names = [a1.name] + [f"AC-ASSET-OVER-{i:04d}" for i in range(self._cap())]
        self.assertEqual(len(names), self._cap() + 1, "tiền đề: len == cap+1")
        resp = get_asset_label_data_batch(assets=names)
        self.assertFalse(resp["success"], "len>cap → KHÔNG success")
        self.assertEqual(resp["http_status"], 413,
                         "vượt cap → 413 (bucket RIÊNG, KHÔNG 404/403/429)")
        self.assertEqual(resp["error"], _ERR_BATCH_TOO_LARGE,
                         "message VI cố định nêu giới hạn")
        # KHÔNG build payload + KHÔNG leak asset name nào.
        self.assertIsNone(resp.get("data"), "413 → KHÔNG trả data payload")
        self.assertNotIn(a1.name, resp["error"], "KHÔNG leak asset name trong message")

    def test_mark_at_limit_ok(self):
        """mark_label_printed len==_MAX_LABEL_BATCH (all valid) → N event+audit, KHÔNG 413."""
        from assetcore.api.imm00 import mark_label_printed
        cap = self._cap()
        names = [self._make_asset(f"mcap-{i}").name for i in range(cap)]
        self.assertEqual(len(names), cap, "tiền đề: len == cap")
        # audit baseline TRƯỚC mark (asset insert sinh sẵn audit tạo) → đo DELTA.
        audit_before_first = self._count_audit(names[0])
        resp = mark_label_printed(assets=names)
        self.assertTrue(resp["success"], "len==cap → KHÔNG 413 (biên PASS)")
        self.assertEqual(resp["data"]["event_count"], cap, "ghi đúng N event")
        self.assertEqual(len(resp["data"]["printed"]), cap)
        # spot-check: mỗi asset có đúng 1 label_printed + đúng 1 audit MỚI / lần in.
        self.assertEqual(self._count_label_events(names[0]), 1)
        self.assertEqual(self._count_audit(names[0]), audit_before_first + 1,
                         "đúng 1 IMM Audit Trail MỚI / asset / lần in")
        self.assertEqual(self._count_label_events(names[-1]), 1)

    def test_mark_over_limit_413_no_side_effect(self):
        """len==cap+1 → 413 + 0 ALE + 0 audit mới (chặn TRƯỚC mọi write)."""
        from assetcore.api.imm00 import mark_label_printed
        from assetcore.services.imm00 import _ERR_BATCH_TOO_LARGE
        a1 = self._make_asset("mover")
        before_label = self._count_label_events(a1.name)
        before_audit = self._count_audit(a1.name)
        total_ale_before = frappe.db.count(
            "Asset Lifecycle Event", {"event_type": "label_printed"})
        names = [a1.name] + [f"AC-ASSET-MOVER-{i:04d}" for i in range(self._cap())]
        self.assertEqual(len(names), self._cap() + 1, "tiền đề: len == cap+1")
        resp = mark_label_printed(assets=names)
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 413, "vượt cap → 413 (KHÔNG 404/403)")
        self.assertEqual(resp["error"], _ERR_BATCH_TOO_LARGE)
        # KHÔNG side-effect: count TRƯỚC == SAU (chặn TRƯỚC validate/write).
        self.assertEqual(self._count_label_events(a1.name), before_label,
                         "413 → KHÔNG ghi label_printed")
        self.assertEqual(self._count_audit(a1.name), before_audit,
                         "413 → KHÔNG ghi IMM Audit Trail")
        self.assertEqual(
            frappe.db.count("Asset Lifecycle Event", {"event_type": "label_printed"}),
            total_ale_before, "413 → tổng ALE label_printed KHÔNG tăng")

    def test_cap_after_rbac(self):
        """User KHÔNG asset.write gửi list quá cap → 403 (rbac TRƯỚC cap), KHÔNG lộ 413."""
        from assetcore.api.imm00 import get_asset_label_data_batch, mark_label_printed
        a1 = self._make_asset("caprbac")
        names = [a1.name] + [f"AC-ASSET-RBAC-{i:04d}" for i in range(self._cap())]
        self.assertEqual(len(names), self._cap() + 1, "tiền đề: list quá cap")
        frappe.set_user("Guest")  # KHÔNG có asset.write
        try:
            with self.assertRaises(frappe.PermissionError):
                get_asset_label_data_batch(assets=names)
            with self.assertRaises(frappe.PermissionError):
                mark_label_printed(assets=names)
        finally:
            frappe.set_user("Administrator")

    def test_batch_empty_and_one_unchanged(self):
        """len==0/None → empty list KHÔNG 413 KHÔNG side-effect; len==1 → bình thường."""
        from assetcore.api.imm00 import get_asset_label_data_batch, mark_label_printed
        # empty + None → [] (200), KHÔNG 413.
        for empty in ([], None):
            r = get_asset_label_data_batch(assets=empty)
            self.assertTrue(r["success"], "empty/None → success (KHÔNG 413)")
            self.assertEqual(r["data"], [])
        a1 = self._make_asset("one")
        before = self._count_label_events(a1.name)
        # mark empty → KHÔNG side-effect, KHÔNG 413.
        rm = mark_label_printed(assets=[])
        self.assertTrue(rm["success"])
        self.assertEqual(rm["data"]["event_count"], 0)
        self.assertEqual(self._count_label_events(a1.name), before)
        # len==1 → bình thường (regression).
        r1 = get_asset_label_data_batch(assets=[a1.name])
        self.assertTrue(r1["success"])
        self.assertEqual(len(r1["data"]), 1)
        rm1 = mark_label_printed(assets=[a1.name])
        self.assertTrue(rm1["success"])
        self.assertEqual(rm1["data"]["event_count"], 1)

    def test_cap_is_single_ssot(self):
        """_MAX_LABEL_BATCH định nghĩa 1 lần ở service; api import dùng lại; 0 literal 200 lặp."""
        import re
        import inspect
        from assetcore.services import imm00 as _svc
        from assetcore.api import imm00 as _api
        # service định nghĩa đúng 1 lần.
        svc_src = inspect.getsource(_svc)
        self.assertEqual(len(re.findall(r"^_MAX_LABEL_BATCH\s*=", svc_src, re.M)), 1,
                         "_MAX_LABEL_BATCH định nghĩa ĐÚNG 1 lần ở service")
        # api KHÔNG redefine hằng + KHÔNG hardcode literal 200 trong 2 endpoint.
        api_src = inspect.getsource(_api)
        self.assertEqual(len(re.findall(r"^_MAX_LABEL_BATCH\s*=", api_src, re.M)), 0,
                         "api KHÔNG redefine _MAX_LABEL_BATCH (SSoT 1 nơi)")
        self.assertNotRegex(api_src, r"len\(names\)\s*>\s*200",
                            "api KHÔNG hardcode literal 200 (phải tham chiếu hằng SSoT)")
        # api tham chiếu hằng từ service.
        self.assertIn("_MAX_LABEL_BATCH", api_src,
                      "api tham chiếu _MAX_LABEL_BATCH (dùng lại hằng service)")


# ──────────────────────────────────────────────────────────────────────────
# A3 / Vòng B — SIẾT RBAC in nhãn QR: asset.read → asset.write (ADR-001 D4)
#
# Least-privilege: 3 endpoint GHI/side-effect (get_asset_label_data,
# get_asset_label_data_batch, mark_label_printed) gate `asset.write` thay vì
# `asset.read`. User chỉ-đọc (asset.read NHƯNG KHÔNG asset.write) → 403; user
# có asset.write → 200. KHÔNG cap mới (CAP_SET_VERSION GIỮ v95.3388ee5629c1).
#
# KHÔNG test false-green (luật skill): test tạo user THẬT + cấp/không-cấp DocPerm
# `write` trên AC Asset (qua Role), frappe.set_user(...), rồi gọi endpoint qua
# layer require("asset.write") → can → frappe.has_permission("AC Asset","write").
# KHÔNG monkeypatch rbac.require / frappe.has_permission.
#
# DocPerm thực tế (site miyano): chỉ "AssetCore Super Admin" có write=1 trên AC
# Asset; mọi role "* User" có read=1/write=0 → dùng "Commissioning User" làm
# user chỉ-đọc, "AssetCore Super Admin" làm user write. IDOR test cần user CÓ
# write NHƯNG vendor-scope (Vendor Engineer, KHÔNG bypass) → cấp write tạm cho
# role Vendor Engineer qua Custom DocPerm trong setUp, gỡ ở tearDown.
# ──────────────────────────────────────────────────────────────────────────


class TestLabelWriteCapability(unittest.TestCase):
    """Vòng B — 3 endpoint in nhãn gate asset.write (least-privilege).

    Phân tách read (đọc) vs write (in/ghi label_printed): user chỉ-đọc bị 403,
    user write 200. Read-only QR endpoint (resolve_qr_token/get_asset_scan_info/
    get_asset) GIỮ asset.read. IDOR (assert_vendor_can_access) KHÔNG bị nới.
    """

    _LABEL_KEYS = {
        "name", "asset_code", "device_model_name", "location_name",
        "lifecycle_status", "qr_url",
    }
    # Role chỉ-đọc trên AC Asset (read=1, write=0) — least-privilege user.
    _READONLY_ROLE = "Commissioning User"
    # Role có write=1 trên AC Asset (DocPerm thật) — user write hợp lệ.
    _WRITE_ROLE = "AssetCore Super Admin"
    _READONLY_USER = "be_b_label_readonly@example.com"
    _WRITE_USER = "be_b_label_write@example.com"
    _IDOR_USER = "be_b_label_idor_write@example.com"

    _CATEGORY_NAME = "Thiết bị RBAC In nhãn (B)"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        # Idempotent setup: purge orphan category leaked by an aborted prior run
        # (UNIQUE category_name) before insert — self-healing, không phụ thuộc DB sạch.
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test siết RBAC in nhãn QR",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        cls._readonly = cls._ensure_user(cls._READONLY_USER, [cls._READONLY_ROLE])
        cls._writer = cls._ensure_user(cls._WRITE_USER, [cls._WRITE_ROLE])
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for email in (cls._READONLY_USER, cls._WRITE_USER, cls._IDOR_USER):
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True,
                                  ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email, roles):
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": email,
            "first_name": email.split("@")[0], "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        u.add_roles(*roles)
        return u

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy RBAC Nhãn {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"RW-SN-{uniq}",
            "asset_code": f"RW-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def _count_label_events(self, asset_name):
        return frappe.db.count("Asset Lifecycle Event",
                               {"asset": asset_name, "event_type": "label_printed"})

    def _count_audit(self, asset_name):
        return frappe.db.count("IMM Audit Trail", {"asset": asset_name})

    # ── 403 — user chỉ-đọc (asset.read, NO asset.write) bị chặn ──────────────
    def test_label_data_read_only_user_403(self):
        """get_asset_label_data: user asset.read (KHÔNG write) → PermissionError."""
        from assetcore.api.imm00 import get_asset_label_data
        asset = self._make_asset("ro1")
        frappe.set_user(self._READONLY_USER)
        try:
            # tiền đề: user CÓ asset.read NHƯNG KHÔNG asset.write (least-privilege)
            from assetcore.services.shared import rbac
            self.assertTrue(rbac.can("asset.read"),
                            "tiền đề: user có asset.read")
            self.assertFalse(rbac.can("asset.write"),
                             "tiền đề: user KHÔNG có asset.write")
            with self.assertRaises(frappe.PermissionError):
                get_asset_label_data(asset=asset.name)
        finally:
            frappe.set_user("Administrator")

    def test_label_batch_read_only_user_403(self):
        """get_asset_label_data_batch: user chỉ-đọc → PermissionError (403)."""
        from assetcore.api.imm00 import get_asset_label_data_batch
        asset = self._make_asset("ro2")
        frappe.set_user(self._READONLY_USER)
        try:
            with self.assertRaises(frappe.PermissionError):
                get_asset_label_data_batch(assets=[asset.name])
        finally:
            frappe.set_user("Administrator")

    def test_mark_printed_read_only_user_403(self):
        """mark_label_printed: user chỉ-đọc → 403 VÀ KHÔNG sinh event/audit.

        Gate WRITE chạy ĐẦU TIÊN → chặn TRƯỚC mọi side-effect (no label_printed,
        no IMM Audit Trail) — least-privilege + no-side-effect khi bị chặn.
        """
        from assetcore.api.imm00 import mark_label_printed
        asset = self._make_asset("ro3")
        before_label = self._count_label_events(asset.name)
        before_audit = self._count_audit(asset.name)
        frappe.set_user(self._READONLY_USER)
        try:
            with self.assertRaises(frappe.PermissionError):
                mark_label_printed(assets=[asset.name])
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(self._count_label_events(asset.name), before_label,
                         "user chỉ-đọc bị chặn → KHÔNG sinh label_printed")
        self.assertEqual(self._count_audit(asset.name), before_audit,
                         "user chỉ-đọc bị chặn → KHÔNG ghi IMM Audit Trail")

    # ── 200 — user có asset.write qua được gate ──────────────────────────────
    def test_label_data_write_user_200(self):
        """get_asset_label_data: user asset.write → 200 + payload đủ 6 key."""
        from assetcore.api.imm00 import get_asset_label_data
        asset = self._make_asset("w1")
        frappe.set_user(self._WRITE_USER)
        try:
            resp = get_asset_label_data(asset=asset.name)
            self.assertTrue(resp["success"], "user write → success")
            self.assertEqual(set(resp["data"].keys()), self._LABEL_KEYS,
                             "payload nhãn đúng 6 key")
        finally:
            frappe.set_user("Administrator")

    def test_mark_printed_write_user_200(self):
        """mark_label_printed: user asset.write → 200 + 1 label_printed + 1 audit."""
        from assetcore.api.imm00 import mark_label_printed
        asset = self._make_asset("w2")
        before_label = self._count_label_events(asset.name)
        before_audit = self._count_audit(asset.name)
        frappe.set_user(self._WRITE_USER)
        try:
            resp = mark_label_printed(assets=[asset.name])
            self.assertTrue(resp["success"], "user write → success")
            self.assertEqual(resp["data"]["event_count"], 1)
            self.assertEqual(resp["data"]["printed"], [asset.name])
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(self._count_label_events(asset.name), before_label + 1,
                         "user write → ĐÚNG 1 label_printed / asset")
        self.assertEqual(self._count_audit(asset.name), before_audit + 1,
                         "user write → ĐÚNG 1 IMM Audit Trail / asset")

    # ── Regression — read-only QR endpoint GIỮ asset.read (KHÔNG siết nhầm) ───
    def test_readonly_qr_endpoints_keep_asset_read(self):
        """resolve_qr_token + get_asset_scan_info + get_asset: user chỉ-đọc 200.

        Siết RBAC CHỈ áp cho nhóm in nhãn — 3 endpoint read-only KHÔNG bị siết:
        user có asset.read (KHÔNG write) vẫn quét QR / xem info / get_asset OK.
        """
        from assetcore.api.imm00 import (
            resolve_qr_token, get_asset_scan_info, get_asset,
        )
        asset = self._make_asset("rd")
        token = asset.qr_token
        frappe.set_user(self._READONLY_USER)
        try:
            r1 = resolve_qr_token(token=token)
            self.assertTrue(r1["success"],
                            "resolve_qr_token GIỮ asset.read (user chỉ-đọc 200)")
            r2 = get_asset_scan_info(token=token)
            self.assertTrue(r2["success"],
                            "get_asset_scan_info GIỮ asset.read (user chỉ-đọc 200)")
            r3 = get_asset(name=asset.name)
            self.assertTrue(r3["success"],
                            "get_asset GIỮ asset.read (user chỉ-đọc 200)")
        finally:
            frappe.set_user("Administrator")

    # ── IDOR — user CÓ write nhưng vendor ngoài scope → 403 (KHÔNG nới IDOR) ──
    def test_label_idor_unchanged_after_write_gate(self):
        """user asset.write + Vendor Engineer ngoài scope → 403 IDOR.

        Siết gate read→write KHÔNG được nới IDOR: assert_vendor_can_access vẫn
        chặn user CÓ write nhưng asset NGOÀI WO được giao. Cấp write tạm cho
        role Vendor Engineer (Custom DocPerm) để user qua gate WRITE rồi đập IDOR.
        """
        from frappe.permissions import add_permission, update_permission_property
        from assetcore.api.imm00 import get_asset_label_data, mark_label_printed
        from assetcore.services.shared import rbac
        asset = self._make_asset("idorw")
        name = asset.name
        role = "Vendor Engineer"
        u = self._ensure_user(self._IDOR_USER, ["Vendor Engineer", "Repair User"])
        # Cấp write tạm cho Vendor Engineer trên AC Asset (data, KHÔNG cap mới).
        add_permission("AC Asset", role, 0)
        update_permission_property("AC Asset", role, 0, "write", 1)
        frappe.clear_cache()
        frappe.db.commit()
        try:
            frappe.set_user(self._IDOR_USER)
            # tiền đề: user CÓ asset.write (qua gate WRITE) NHƯNG vendor-scope.
            self.assertTrue(rbac.can("asset.write"),
                            "tiền đề: user IDOR có asset.write (qua gate)")
            resp = get_asset_label_data(asset=name)
            self.assertFalse(resp["success"], "vendor ngoài scope → KHÔNG success")
            self.assertEqual(resp["http_status"], 403,
                             "get_asset_label_data IDOR → 403 (KHÔNG nới IDOR)")
            self.assertNotIn("asset_code", resp.get("data") or {},
                             "KHÔNG leak payload asset ngoài scope")
            resp2 = mark_label_printed(assets=[name])
            self.assertFalse(resp2["success"])
            self.assertEqual(resp2["http_status"], 403,
                             "mark_label_printed IDOR → 403 (KHÔNG nới IDOR)")
        finally:
            frappe.set_user("Administrator")
            cp = frappe.db.get_value(
                "Custom DocPerm",
                {"parent": "AC Asset", "role": role, "permlevel": 0}, "name")
            if cp:
                frappe.delete_doc("Custom DocPerm", cp, force=True,
                                  ignore_permissions=True)
            frappe.clear_cache()
            rbac.invalidate_capabilities(self._IDOR_USER)
            if frappe.db.exists("User", self._IDOR_USER):
                frappe.delete_doc("User", self._IDOR_USER, force=True,
                                  ignore_permissions=True)
            frappe.db.commit()

    # ── No-churn guard — cap-set version KHÔNG đổi (KHÔNG thêm cap) ───────────
    def test_cap_set_version_unchanged(self):
        """Siết read→write dùng cap CÓ SẴN → CAP_SET_VERSION GIỮ v95.3388ee5629c1.

        White-box no-churn: asset.write ∈ CAPABILITY_MAP; KHÔNG có asset.print_label
        (cap mới đã BỎ khỏi roadmap) → FE auth.ts::CAP_SET_VERSION KHÔNG cần bump.
        """
        from assetcore.services.shared.rbac import CAP_SET_VERSION, CAPABILITY_MAP
        self.assertEqual(CAP_SET_VERSION, "v95.3388ee5629c1",
                         "siết read→write KHÔNG thêm cap → version GIỮ NGUYÊN "
                         "(KHÔNG churn FE auth.ts CAP_SET_VERSION)")
        self.assertIn("asset.write", CAPABILITY_MAP,
                      "asset.write phải có sẵn (qua _DOMAIN_PRIMARY['Asset'])")
        self.assertEqual(CAPABILITY_MAP["asset.write"], ("AC Asset", "write"),
                         "asset.write bind ('AC Asset','write')")
        self.assertNotIn("asset.print_label", CAPABILITY_MAP,
                         "KHÔNG thêm cap mới asset.print_label (đã BỎ khỏi roadmap)")


# ──────────────────────────────────────────────────────────────────────────
# P1 HOTFIX — HTTP-LAYER (whitelist coercion) cho QR GET endpoints
#
# RC (eval LIVE 2026-06-04): GET /api/method/...resolve_qr_token?token=<thật>
# trả 417 EXPECTATION FAILED vì signature `token: str | None = None`. Frappe
# áp `validate_argument_types(fn, apply_condition=in_request_or_test)` (frappe/
# __init__.py:849) — coercion CHỈ chạy khi có request-context HOẶC in_test.
# 91 test cũ gọi service/python TRỰC TIẾP (không qua coercion) → false-green,
# KHÔNG bắt 417. Test class này dispatch QUA layer coercion thật (mô phỏng
# request-context giống handler.execute_cmd → frappe.call(method, **form_dict)).
#
# Bất biến chống-417 (version-independent): param @whitelist GET QR KHÔNG được
# mang annotation kiểu Union chứa None (`str | None`) — kiểu này KÍCH HOẠT
# coercion pydantic (typing_validations.py:122 chỉ SKIP khi annotation là
# str/ForwardRef). Đổi `str | None = None` → `str = ""` (giống get_asset @183
# chạy OK) → coercion nhận str, KHÔNG reject. Guard `isinstance(...,str)` ở
# service giữ nguyên xử lý rỗng. Test RED trên `str|None`, GREEN sau fix.
# ──────────────────────────────────────────────────────────────────────────


class TestQrWhitelistHttpLayer(unittest.TestCase):
    """A2/A3 P1 — QR GET endpoints đi xuyên HTTP whitelist dispatch (coercion).

    Dispatch qua ``_http_call`` = mô phỏng đúng đường handler.execute_cmd:
    coercion ``transform_parameter_types`` được áp (như request thật) → bắt
    được 417 mà gọi service trực tiếp KHÔNG chạm tới.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị QR HTTP (P1)",
            "description": "Category cho test HTTP-layer QR",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        # Vòng 12 B: _http_call dùng IP/cmd cố định → dọn rate-limit counter
        # giữa các test để KHÔNG cộng dồn chạm trần 30/60s (false 429).
        try:
            frappe.cache.delete_keys("rl:")
        except Exception:
            pass
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy HTTP {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"HT-SN-{uniq}",
            "asset_code": f"HT-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def _http_call(self, fn, **params):
        """Gọi endpoint @whitelist QUA layer coercion (giống request HTTP thật).

        Đặt ``frappe.local.request`` truthy → ``in_request_or_test()`` True →
        ``validate_argument_types`` áp ``transform_parameter_types`` (đúng layer
        sinh 417). Trả (status_or_envelope, exception). Nếu coercion/endpoint
        raise (vd FrappeTypeError 417 hoặc PermissionError 403) → trả exception.
        """
        class _Req:
            method = "GET"
            host = "miyano"
            # get_url()/get_request_header dùng request.headers.get(...) khi build
            # qr_url tuyệt đối — stub dict rỗng đủ để KHÔNG raise (không có proxy).
            headers: dict = {}
        had_req = getattr(frappe.local, "request", None)
        had_ip = getattr(frappe.local, "request_ip", None)
        had_cmd = frappe.form_dict.get("cmd")
        frappe.local.request = _Req()
        # Vòng 12 B: resolve_qr_token có @rate_limit(ip_based=True) → khi
        # frappe.request truthy, limiter cần request_ip + cmd để dựng identity,
        # nếu thiếu → throw("Either key or IP flag is required."). Request HTTP
        # THẬT luôn có ip → set ở đây để helper mô phỏng đúng (KHÔNG trip 429:
        # mỗi test gọi ≤ vài lần, dưới trần 30/60s).
        frappe.local.request_ip = "127.0.0.1"
        frappe.form_dict.cmd = f"assetcore.api.imm00.{getattr(fn, '__name__', 'x')}"
        try:
            try:
                env = fn(**params)
                return env, None
            except Exception as e:  # noqa: BLE001 — cần phân loại http_status_code
                return None, e
        finally:
            frappe.local.request = had_req
            frappe.local.request_ip = had_ip
            if had_cmd is None:
                frappe.form_dict.pop("cmd", None)
            else:
                frappe.form_dict.cmd = had_cmd

    # ── 200 — resolve_qr_token QUA HTTP với token thật ──────────────────────
    def test_resolve_qr_token_http_returns_200(self):
        """RED trên `str|None=None` (417 coercion ở môi trường prod), GREEN sau
        đổi `str=""`: token thật QUA HTTP → 200 + payload 6-field tối thiểu."""
        from assetcore.api.imm00 import resolve_qr_token
        asset = self._make_asset("ok")
        env, exc = self._http_call(resolve_qr_token, token=asset.qr_token)
        self.assertIsNone(
            exc,
            f"resolve_qr_token QUA HTTP KHÔNG được raise (417/coercion): {exc!r}")
        self.assertTrue(env["success"], "token thật QUA HTTP → success")
        data = env["data"]
        for k in ("name", "asset_code", "lifecycle_status",
                  "device_model_name", "location_name"):
            self.assertIn(k, data, f"payload thiếu field tối thiểu '{k}'")
        self.assertEqual(data["name"], asset.name)

    def test_resolve_qr_token_http_bad_token_404(self):
        """token sai QUA HTTP → 404 leak-safe, KHÔNG 417/500."""
        from assetcore.api.imm00 import resolve_qr_token
        env, exc = self._http_call(
            resolve_qr_token, token="khong-ton-tai-zzzzzzzzzzzzzzz")
        self.assertIsNone(exc, f"KHÔNG raise (417/500): {exc!r}")
        self.assertFalse(env["success"])
        self.assertEqual(env["http_status"], 404,
                         "token sai QUA HTTP → 404 (KHÔNG 417/500)")
        self.assertNotIn("asset_code", env.get("data") or {},
                         "404 KHÔNG leak field")

    def test_resolve_qr_token_http_empty_token_404(self):
        """token rỗng/thiếu param QUA HTTP → 404 (guard isinstance giữ nguyên),
        KHÔNG 417 do coercion."""
        from assetcore.api.imm00 import resolve_qr_token
        # (a) token="" rỗng
        env, exc = self._http_call(resolve_qr_token, token="")
        self.assertIsNone(exc, f"token='' KHÔNG raise: {exc!r}")
        self.assertFalse(env["success"])
        self.assertIn(env["http_status"], (400, 404),
                      "token rỗng → 400/404, KHÔNG 417")
        # (b) param hoàn toàn vắng (FE/handler không gửi token) → default kick-in
        env2, exc2 = self._http_call(resolve_qr_token)
        self.assertIsNone(exc2, f"thiếu param KHÔNG raise (417): {exc2!r}")
        self.assertFalse(env2["success"])
        self.assertIn(env2["http_status"], (400, 404))

    def test_get_asset_label_data_http_returns_200(self):
        """get_asset_label_data QUA HTTP với asset thật → 200 (CÙNG defect đã vá,
        A4-safe). RED trên `str|None=None`."""
        from assetcore.api.imm00 import get_asset_label_data
        asset = self._make_asset("label")
        env, exc = self._http_call(get_asset_label_data, asset=asset.name)
        self.assertIsNone(
            exc, f"get_asset_label_data QUA HTTP KHÔNG được raise: {exc!r}")
        self.assertTrue(env["success"], "asset thật QUA HTTP → success")
        self.assertIn("qr_url", env["data"])
        self.assertIn("/a/", env["data"]["qr_url"])

    def test_resolve_qr_token_http_forbidden_403(self):
        """user KHÔNG có asset.read QUA HTTP → PermissionError (403) — gate còn
        nguyên sau khi đổi signature (KHÔNG bị coercion nuốt thành 417)."""
        from assetcore.api.imm00 import resolve_qr_token
        asset = self._make_asset("noperm")
        token = asset.qr_token
        frappe.set_user("Guest")
        try:
            env, exc = self._http_call(resolve_qr_token, token=token)
            self.assertIsNotNone(
                exc, "Guest (thiếu asset.read) PHẢI raise (403), KHÔNG trả 200")
            self.assertIsInstance(
                exc, frappe.PermissionError,
                f"thiếu cap → PermissionError(403), KHÔNG {type(exc).__name__}")
        finally:
            frappe.set_user("Administrator")

    # ── Bất biến chống-417 (version-independent regression guard) ────────────
    def test_qr_get_params_not_none_union_annotation(self):
        """RC GUARD: param @whitelist GET QR KHÔNG mang annotation Union-chứa-None
        (`str | None`) — kiểu này kích hoạt coercion pydantic → 417 ở môi trường
        prod. Đổi sang `str` (default ``""``) → coercion nhận str, KHÔNG reject.

        RED trên signature cũ (`token: str | None`), GREEN sau fix (`token: str`).
        Độc lập phiên bản frappe/pydantic — chốt RC ngay ở chữ ký.
        """
        import inspect
        import types as _types
        from assetcore.api import imm00 as _api

        def _is_none_union(ann) -> bool:
            # UnionType (str | None) hoặc typing.Optional/Union[..., None]
            import typing
            if isinstance(ann, _types.UnionType):
                return type(None) in ann.__args__
            if typing.get_origin(ann) is typing.Union:
                return type(None) in typing.get_args(ann)
            return False

        for fn_name, param in (("resolve_qr_token", "token"),
                               ("get_asset_label_data", "asset")):
            raw = inspect.unwrap(getattr(_api, fn_name))
            ann = raw.__annotations__.get(param, inspect._empty)
            self.assertFalse(
                _is_none_union(ann),
                f"{fn_name}({param}) annotation '{ann}' là Union-chứa-None → "
                f"coercion pydantic kích hoạt → 417 prod. Đổi sang `str` (default '').")


# ──────────────────────────────────────────────────────────────────────────
# B (hardening) — Regenerate (rotate) QR token cấp AC Asset
# Endpoint regenerate_asset_qr_token(asset): gate asset.write (403 read-only) →
# token MỚI != cũ (enumeration-safe, overwrite, update_modified=False) → token
# CŨ KHÔNG còn resolve → 1 ALE 'qr_regenerated' + 1 IMM Audit Trail (KHÔNG log
# token thô) → IDOR-safe (assert_vendor_can_access) → 404 leak-safe. RED viết TRƯỚC.
# ──────────────────────────────────────────────────────────────────────────


class TestRegenerateQrToken(unittest.TestCase):
    """B — rotate qr_token: vô hiệu hoá token bị lộ + cấp token mới (RED-first)."""

    # Role chỉ-đọc trên AC Asset (read=1, write=0) — least-privilege user.
    _READONLY_ROLE = "Commissioning User"
    # Role có write=1 trên AC Asset (DocPerm thật) — user write hợp lệ.
    _WRITE_ROLE = "AssetCore Super Admin"
    _READONLY_USER = "be_b_regen_readonly@example.com"
    _WRITE_USER = "be_b_regen_write@example.com"
    _IDOR_USER = "be_b_regen_idor@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Rotate QR (B)",
            "description": "Category cho test regenerate_asset_qr_token",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        cls._readonly = cls._ensure_user(cls._READONLY_USER, [cls._READONLY_ROLE])
        cls._writer = cls._ensure_user(cls._WRITE_USER, [cls._WRITE_ROLE])
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for email in (cls._READONLY_USER, cls._WRITE_USER, cls._IDOR_USER):
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True,
                                  ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    @staticmethod
    def _ensure_user(email, roles):
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": email,
            "first_name": email.split("@")[0], "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        u.add_roles(*roles)
        return u

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy Rotate {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"RG-SN-{uniq}",
            "asset_code": f"RG-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    # ── Schema — enum mới 'qr_regenerated' ──────────────────────────────────
    def test_event_type_enum_has_qr_regenerated(self):
        """RED trước khi sync JSON: event_type chứa qr_regenerated (sau label_printed)."""
        meta = frappe.get_meta("Asset Lifecycle Event")
        opts = (meta.get_field("event_type").options or "").split("\n")
        self.assertIn("qr_regenerated", opts,
                      "enum event_type PHẢI có 'qr_regenerated' (enum +1, không destructive)")

    # ── 200 — user asset.write → token mới != cũ, qr_url chứa token mới ──────
    def test_regenerate_write_user_200_new_token(self):
        from assetcore.api.imm00 import regenerate_asset_qr_token
        asset = self._make_asset("ok")
        old = asset.qr_token
        self.assertTrue(old, "tiền đề: asset đã có qr_token")
        frappe.set_user(self._WRITE_USER)
        try:
            resp = regenerate_asset_qr_token(asset=asset.name)
            self.assertTrue(resp["success"], "user asset.write → success")
            data = resp["data"]
            self.assertEqual(data["name"], asset.name)
            # No-raw-token (ADR-001 §D4 rule 9): envelope KHÔNG surface token thô
            # → token MỚI parse từ qr_url (/a/<new>), KHÔNG đọc data['qr_token'].
            self.assertNotIn("qr_token", data,
                             "envelope KHÔNG còn field qr_token thô (no-raw-token)")
            m = re.search(r"/a/([^/?#]+)", data["qr_url"])
            self.assertIsNotNone(m, "qr_url phải có dạng /a/<token>")
            new = m.group(1)
            self.assertTrue(new, "token mới != rỗng")
            self.assertNotEqual(new, old, "token MỚI phải KHÁC token cũ (rotate)")
            # qr_url phản ánh token MỚI (nhãn/print deep-link mới).
            self.assertIn(f"/a/{new}", data["qr_url"],
                          "qr_url phải chứa token MỚI")
            self.assertNotIn(old, data["qr_url"], "qr_url KHÔNG còn token cũ")
            # DB GHI ĐÈ qr_token (overwrite, KHÔNG idempotent) — verify rotate ở DB.
            self.assertEqual(
                frappe.db.get_value("AC Asset", asset.name, "qr_token"), new,
                "DB qr_token đã overwrite token mới")
        finally:
            frappe.set_user("Administrator")

    # ── contract-lock — envelope CHỈ {name, qr_url}, KHÔNG token thô ─────────
    def test_regenerate_response_no_raw_token(self):
        """ADR-001 §D4 rule 9: data == {name, qr_url} CHÍNH XÁC (chống tái-leak)."""
        from assetcore.api.imm00 import regenerate_asset_qr_token
        asset = self._make_asset("noleak")
        resp = regenerate_asset_qr_token(asset=asset.name)
        self.assertTrue(resp["success"])
        data = resp["data"]
        self.assertNotIn("qr_token", data,
                         "envelope KHÔNG được chứa qr_token thô (no-raw-token)")
        self.assertEqual(
            set(data.keys()), {"name", "qr_url"},
            "data CHỈ gồm name + qr_url (khoá envelope ADR D4 rule 9)")

    # ── 403 — user chỉ asset.read (Guest/nurse) KHÔNG rotate được ────────────
    def test_regenerate_guest_forbidden(self):
        """Guest (không DocPerm write) → PermissionError (403), KHÔNG rotate."""
        from assetcore.api.imm00 import regenerate_asset_qr_token
        asset = self._make_asset("guest")
        old = asset.qr_token
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                regenerate_asset_qr_token(asset=asset.name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset.name, "qr_token"), old,
            "Guest bị chặn → qr_token KHÔNG đổi")

    def test_regenerate_read_only_user_403(self):
        """User asset.read NHƯNG KHÔNG asset.write → PermissionError, KHÔNG rotate."""
        from assetcore.api.imm00 import regenerate_asset_qr_token
        from assetcore.services.shared import rbac
        asset = self._make_asset("ro")
        old = asset.qr_token
        frappe.set_user(self._READONLY_USER)
        try:
            self.assertTrue(rbac.can("asset.read"), "tiền đề: có asset.read")
            self.assertFalse(rbac.can("asset.write"),
                             "tiền đề: KHÔNG có asset.write")
            with self.assertRaises(frappe.PermissionError):
                regenerate_asset_qr_token(asset=asset.name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset.name, "qr_token"), old,
            "user chỉ-đọc bị chặn → qr_token KHÔNG đổi (no side-effect)")

    # ── Token CŨ KHÔNG còn resolve; token MỚI resolve đúng asset ────────────
    def test_old_token_unresolvable_new_token_resolves(self):
        from assetcore.api.imm00 import regenerate_asset_qr_token
        from assetcore.services.imm00 import resolve_qr_token as svc_resolve
        asset = self._make_asset("rot")
        old = asset.qr_token
        # rotate (Admin = asset.write). Envelope no-raw-token → token MỚI đọc từ DB.
        regenerate_asset_qr_token(asset=asset.name)
        new = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        self.assertNotEqual(new, old)
        # token CŨ → None (vô hiệu hoá nhãn đã in/lộ).
        self.assertIsNone(svc_resolve(old),
                          "token CŨ sau rotate KHÔNG còn resolve → None")
        # token MỚI → asset đúng.
        payload = svc_resolve(new)
        self.assertIsNotNone(payload, "token MỚI resolve được")
        self.assertEqual(payload["name"], asset.name,
                         "token MỚI resolve đúng asset")

    # ── Mỗi rotate ghi đúng 1 ALE 'qr_regenerated' + 1 IMM Audit Trail ──────
    def test_regenerate_emits_one_ale_and_audit_no_raw_token(self):
        from assetcore.api.imm00 import regenerate_asset_qr_token
        asset = self._make_asset("emit")
        old = asset.qr_token
        before_ale = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": "qr_regenerated"})
        before_audit = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        regenerate_asset_qr_token(asset=asset.name)
        new = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        after_ale = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": "qr_regenerated"})
        after_audit = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        self.assertEqual(after_ale - before_ale, 1,
                         "đúng 1 Asset Lifecycle Event qr_regenerated / rotate")
        self.assertEqual(after_audit - before_audit, 1,
                         "đúng 1 IMM Audit Trail / rotate")
        # change_summary KHÔNG log token thô (cũ hoặc mới) — leak-safe audit.
        rows = frappe.get_all(
            "IMM Audit Trail", filters={"asset": asset.name},
            fields=["change_summary"], order_by="creation desc", limit=1)
        summary = (rows[0]["change_summary"] or "") if rows else ""
        self.assertNotIn(old, summary, "audit KHÔNG chứa token CŨ thô")
        self.assertNotIn(new, summary, "audit KHÔNG chứa token MỚI thô")
        # ALE notes cũng KHÔNG log token thô.
        ale = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": asset.name, "event_type": "qr_regenerated"},
            fields=["notes"], order_by="creation desc", limit=1)
        notes = (ale[0]["notes"] or "") if ale else ""
        self.assertNotIn(old, notes, "ALE notes KHÔNG chứa token CŨ thô")
        self.assertNotIn(new, notes, "ALE notes KHÔNG chứa token MỚI thô")

    # ── 403 IDOR — vendor rotate asset ngoài scope → chặn, leak-safe ────────
    def test_regenerate_vendor_out_of_scope_forbidden_no_leak(self):
        """user CÓ asset.write + Vendor Engineer ngoài scope → 403 IDOR, KHÔNG rotate."""
        from frappe.permissions import add_permission, update_permission_property
        from assetcore.api.imm00 import regenerate_asset_qr_token
        from assetcore.services.shared import rbac
        asset = self._make_asset("idor")
        old = asset.qr_token
        role = "Vendor Engineer"
        u = self._ensure_user(self._IDOR_USER, ["Vendor Engineer", "Repair User"])
        # Cấp write tạm cho Vendor Engineer trên AC Asset (data, KHÔNG cap mới)
        # → user QUA gate WRITE rồi đập IDOR (assert_vendor_can_access).
        add_permission("AC Asset", role, 0)
        update_permission_property("AC Asset", role, 0, "write", 1)
        frappe.clear_cache()
        frappe.db.commit()
        try:
            frappe.set_user(self._IDOR_USER)
            self.assertTrue(rbac.can("asset.write"),
                            "tiền đề: user IDOR có asset.write (qua gate)")
            resp = regenerate_asset_qr_token(asset=asset.name)
            self.assertFalse(resp["success"], "vendor ngoài scope → KHÔNG success")
            self.assertEqual(resp["http_status"], 403,
                             "vendor ngoài scope → 403 (IDOR guard)")
            self.assertNotIn("qr_token", resp.get("data") or {},
                             "KHÔNG leak token mới cho asset ngoài scope")
        finally:
            frappe.set_user("Administrator")
            cp = frappe.db.get_value(
                "Custom DocPerm",
                {"parent": "AC Asset", "role": role, "permlevel": 0}, "name")
            if cp:
                frappe.delete_doc("Custom DocPerm", cp, force=True,
                                  ignore_permissions=True)
            frappe.clear_cache()
            rbac.invalidate_capabilities(self._IDOR_USER)
            if frappe.db.exists("User", self._IDOR_USER):
                frappe.delete_doc("User", self._IDOR_USER, force=True,
                                  ignore_permissions=True)
            frappe.db.commit()
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset.name, "qr_token"), old,
            "vendor ngoài scope bị chặn → qr_token KHÔNG đổi")

    # ── 404 — asset không tồn tại / param rỗng → leak-safe đồng nhất ────────
    def test_regenerate_unknown_asset_404(self):
        from assetcore.api.imm00 import regenerate_asset_qr_token
        resp = regenerate_asset_qr_token(asset="KHONG-TON-TAI-zzzz")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 404,
                         "asset không tồn tại → 404, KHÔNG 500")
        self.assertNotIn("qr_token", resp.get("data") or {})

    def test_regenerate_empty_param_404(self):
        from assetcore.api.imm00 import regenerate_asset_qr_token
        for resp in (regenerate_asset_qr_token(asset=""),
                     regenerate_asset_qr_token()):
            self.assertFalse(resp["success"], "param rỗng → KHÔNG success")
            self.assertIn(resp["http_status"], (400, 404),
                          "param rỗng → 400/404 leak-safe, KHÔNG 500/417")

    # ── 2 lần liên tiếp → 2 token KHÁC NHAU (KHÁC ensure idempotent) + 2 ALE ─
    def test_regenerate_twice_yields_two_distinct_tokens_two_events(self):
        from assetcore.api.imm00 import regenerate_asset_qr_token
        asset = self._make_asset("twice")
        t0 = asset.qr_token
        before = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": "qr_regenerated"})
        # Envelope no-raw-token → token sau mỗi rotate đọc từ DB (SoT).
        regenerate_asset_qr_token(asset=asset.name)
        t1 = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        regenerate_asset_qr_token(asset=asset.name)
        t2 = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        self.assertNotEqual(t1, t0, "lần 1 != token gốc")
        self.assertNotEqual(t2, t1, "lần 2 != lần 1 (KHÁC ensure idempotent)")
        self.assertNotEqual(t2, t0, "lần 2 != token gốc")
        after = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": "qr_regenerated"})
        self.assertEqual(after - before, 2,
                         "2 lần rotate → 2 ALE qr_regenerated")

    # ── token mới enumeration-safe (độ dài/charset URL-safe, != định danh) ──
    def test_new_token_enumeration_safe(self):
        from assetcore.api.imm00 import regenerate_asset_qr_token
        asset = self._make_asset("enum")
        # Envelope no-raw-token → token MỚI đọc từ DB (SoT) để kiểm tra charset.
        regenerate_asset_qr_token(asset=asset.name)
        new = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        self.assertGreaterEqual(len(new), 20, "token URL-safe >= 20 ký tự")
        self.assertRegex(new, r"^[A-Za-z0-9_-]+$",
                         "token chỉ ký tự URL-safe [A-Za-z0-9_-]")
        self.assertNotIn(asset.name, new, "token KHÔNG chứa name")
        self.assertNotIn(asset.asset_code, new, "token KHÔNG chứa asset_code")
        self.assertNotIn(asset.manufacturer_sn, new,
                         "token KHÔNG chứa manufacturer_sn")

    # ── update_modified=False — rotate KHÔNG bump modified của asset ────────
    def test_regenerate_does_not_bump_modified(self):
        from assetcore.api.imm00 import regenerate_asset_qr_token
        asset = self._make_asset("mod")
        before = frappe.db.get_value("AC Asset", asset.name, "modified")
        regenerate_asset_qr_token(asset=asset.name)
        after = frappe.db.get_value("AC Asset", asset.name, "modified")
        self.assertEqual(before, after,
                         "rotate qr_token dùng update_modified=False (KHÔNG bump)")

    # ── No-churn guard — CAP_SET_VERSION KHÔNG đổi (KHÔNG thêm cap) ─────────
    def test_cap_set_version_unchanged(self):
        """rotate dùng asset.write CÓ SẴN → CAP_SET_VERSION GIỮ v95.3388ee5629c1."""
        from assetcore.services.shared.rbac import CAP_SET_VERSION, CAPABILITY_MAP
        self.assertEqual(CAP_SET_VERSION, "v95.3388ee5629c1",
                         "rotate KHÔNG thêm cap → version GIỮ NGUYÊN (no FE churn)")
        self.assertIn("asset.write", CAPABILITY_MAP,
                      "asset.write có sẵn (qua _DOMAIN_PRIMARY['Asset'])")


# ──────────────────────────────────────────────────────────────────────────
# Vòng 12 B (hardening/security) — Rate-limit 2 endpoint QR deep-link resolve
# (BR-00-29). @rate_limit(limit=AC_QR_RESOLVE_RATE_LIMIT=30, seconds=60,
# ip_based=True) áp lên resolve_qr_token + get_asset_scan_info (2 entry-point
# camera điện thoại /a/<token> & /scan/:token). 429 chạy TRƯỚC rbac.require,
# no-leak parity 404/403. KHÔNG áp lên nhóm GHI nhãn. RED viết TRƯỚC.
#
# Hạ tầng test (BẮT BUỘC — sai → false-green): frappe.rate_limiter.rate_limit có
# `if not frappe.request: return fn(...)` → gọi hàm TRỰC TIẾP KHÔNG trip limiter.
# Để chạm 429 phải mô phỏng HTTP context: set frappe.local.request truthy +
# frappe.local.request_ip + frappe.form_dict.cmd (cache key dùng cmd). Mỗi test
# dùng IP/cmd DUY NHẤT + dọn cache `rl:*` ở teardown → KHÔNG rò trần sang test
# khác. Xem 07_Testing_QA.md §III.6.c, 05_API_Specification.md §I.7a.
# ──────────────────────────────────────────────────────────────────────────


class TestQrResolveRateLimit(unittest.TestCase):
    """Vòng 12 B — @rate_limit trên 2 endpoint QR deep-link resolve (RED-first)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị RateLimit QR (Vòng 12 B)",
            "description": "Category cho test rate-limit QR resolve",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []
        # IP duy nhất mỗi test → bucket riêng, không kế thừa counter test trước.
        import uuid
        self._ip = f"10.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}." \
                   f"{uuid.uuid4().int % 250 + 1}"

    def tearDown(self):
        frappe.set_user("Administrator")
        # Dọn MỌI cache key rate-limit do test sinh ra (tránh rò trần).
        try:
            frappe.cache.delete_keys("rl:")
        except Exception:
            pass
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy RateLimit {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"RL-SN-{uniq}",
            "asset_code": f"RL-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def _http_call(self, fn, cmd, **params):
        """Gọi endpoint @rate_limit QUA HTTP context (limiter ĐƯỢC kích hoạt).

        Mô phỏng đúng điều kiện ``rate_limit`` wrapper cần: ``frappe.local.request``
        truthy, ``frappe.local.request_ip`` (ip_based), và ``frappe.form_dict.cmd``
        (cache key ``rl:{cmd}:{ip}``). Trả (envelope, exception).
        """
        class _Req:
            method = "GET"
            host = "miyano"
            headers: dict = {}
        had_req = getattr(frappe.local, "request", None)
        had_ip = getattr(frappe.local, "request_ip", None)
        had_cmd = frappe.form_dict.get("cmd")
        frappe.local.request = _Req()
        frappe.local.request_ip = self._ip
        frappe.form_dict.cmd = cmd
        try:
            try:
                return fn(**params), None
            except Exception as e:  # noqa: BLE001 — phân loại http_status_code
                return None, e
        finally:
            frappe.local.request = had_req
            frappe.local.request_ip = had_ip
            if had_cmd is None:
                frappe.form_dict.pop("cmd", None)
            else:
                frappe.form_dict.cmd = had_cmd

    def _drain(self, fn, cmd, n, **params):
        """Dội ``n`` call hợp lệ (≤ trần) — trả exception cuối cùng (None nếu OK)."""
        last_exc = None
        for _ in range(n):
            _, last_exc = self._http_call(fn, cmd, **params)
        return last_exc

    # ── Hằng tồn tại, đúng giá trị BA chốt (KHÔNG literal rải rác) ───────────
    def test_rate_limit_constant_value(self):
        from assetcore.api.imm00 import AC_QR_RESOLVE_RATE_LIMIT
        self.assertEqual(AC_QR_RESOLVE_RATE_LIMIT, 30,
                         "ngưỡng BA chốt = 30 req/60s/IP/endpoint (BR-00-29)")

    # ── resolve_qr_token: call N+1 trong window → 429, KHÔNG trả payload ─────
    def test_resolve_rate_limited_after_threshold(self):
        from assetcore.api.imm00 import (
            resolve_qr_token, AC_QR_RESOLVE_RATE_LIMIT as N)
        asset = self._make_asset("over")
        cmd = "assetcore.api.imm00.resolve_qr_token"
        # N call đầu trong window: hợp lệ (KHÔNG raise).
        first_exc = self._drain(resolve_qr_token, cmd, N, token=asset.qr_token)
        self.assertIsNone(first_exc,
                          f"{N} call đầu trong window KHÔNG được throttle: {first_exc!r}")
        # call N+1 → 429.
        env, exc = self._http_call(resolve_qr_token, cmd, token=asset.qr_token)
        self.assertIsNotNone(exc, f"call thứ {N+1} PHẢI raise 429 (vượt trần)")
        # Frappe @rate_limit raise frappe.RateLimitExceededError (precedent
        # auth.py:67). http_status_code == 429 là invariant load-bearing (no-leak
        # parity 404/403); cũng chấp nhận TooManyRequestsError nếu Frappe đổi.
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            f"vượt trần → 429 (RateLimitExceededError), KHÔNG {type(exc).__name__}")
        self.assertEqual(getattr(exc, "http_status_code", None), 429,
                         "exception map HTTP 429")
        # No-leak: KHÔNG trả envelope/payload asset khi bị throttle.
        self.assertIsNone(env, "429 KHÔNG trả envelope (no payload built)")
        msg = str(getattr(exc, "message", "") or "") + str(exc)
        for leak in (asset.name, asset.asset_code, asset.manufacturer_sn):
            self.assertNotIn(leak, msg,
                             "429 message KHÔNG leak name/asset_code/serial")

    # ── resolve_qr_token: ≤N call vẫn 200/404/403 đúng baseline ─────────────
    def test_resolve_within_limit_still_ok(self):
        from assetcore.api.imm00 import (
            resolve_qr_token, AC_QR_RESOLVE_RATE_LIMIT as N)
        asset = self._make_asset("under")
        cmd = "assetcore.api.imm00.resolve_qr_token"
        # (a) token hợp lệ ≤N → 200 + payload.
        env, exc = self._http_call(resolve_qr_token, cmd, token=asset.qr_token)
        self.assertIsNone(exc, f"call đầu KHÔNG throttle: {exc!r}")
        self.assertTrue(env["success"], "token hợp lệ trong trần → 200")
        self.assertEqual(env["data"]["name"], asset.name)
        # (b) token sai ≤N → 404 (KHÔNG raise 429).
        env2, exc2 = self._http_call(
            resolve_qr_token, cmd, token="khong-ton-tai-zzzzzzzzzzzzz")
        self.assertIsNone(exc2, "token sai trong trần → KHÔNG 429")
        self.assertEqual(env2["http_status"], 404, "token sai → 404 baseline")
        # (c) no asset.read (Guest) trong trần → 403 (RBAC vẫn chạy sau RL).
        frappe.set_user("Guest")
        try:
            _, exc3 = self._http_call(
                resolve_qr_token, cmd, token=asset.qr_token)
            self.assertIsInstance(
                exc3, frappe.PermissionError,
                "≤N + thiếu asset.read → 403 (RBAC), KHÔNG 429")
        finally:
            frappe.set_user("Administrator")

    # ── get_asset_scan_info: call N+1 → 429 no-leak (asset name/lifecycle) ───
    def test_scan_info_rate_limited_after_threshold(self):
        from assetcore.api.imm00 import (
            get_asset_scan_info, AC_QR_RESOLVE_RATE_LIMIT as N)
        asset = self._make_asset("scanover")
        cmd = "assetcore.api.imm00.get_asset_scan_info"
        first_exc = self._drain(get_asset_scan_info, cmd, N, token=asset.qr_token)
        self.assertIsNone(first_exc,
                          f"{N} call đầu KHÔNG throttle: {first_exc!r}")
        env, exc = self._http_call(get_asset_scan_info, cmd, token=asset.qr_token)
        self.assertIsNotNone(exc, f"call thứ {N+1} PHẢI raise 429")
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            f"vượt trần → 429, KHÔNG {type(exc).__name__}")
        self.assertEqual(getattr(exc, "http_status_code", None), 429)
        self.assertIsNone(env, "429 KHÔNG trả envelope")
        msg = str(getattr(exc, "message", "") or "") + str(exc)
        for leak in (asset.name, asset.asset_code, asset.asset_name):
            self.assertNotIn(leak, msg,
                             "429 KHÔNG leak asset name/lifecycle")

    # ── get_asset_scan_info: ≤N call vẫn trả payload core-shape (A6) ─────────
    def test_scan_info_within_limit_unaffected(self):
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("scanunder")
        cmd = "assetcore.api.imm00.get_asset_scan_info"
        env, exc = self._http_call(get_asset_scan_info, cmd, token=asset.qr_token)
        self.assertIsNone(exc, f"call đầu KHÔNG throttle: {exc!r}")
        self.assertTrue(env["success"], "token hợp lệ trong trần → 200")
        data = env["data"]
        self.assertEqual(data["name"], asset.name)
        # core-shape A6: định danh + lifecycle (mã canonical) phải có mặt.
        for k in ("name", "asset_code", "lifecycle_status"):
            self.assertIn(k, data, f"payload A6 thiếu field core '{k}'")

    # ── 2 endpoint = 2 bucket RIÊNG (cache key gồm cmd) ─────────────────────
    def test_resolve_and_scan_info_separate_buckets(self):
        """Dội resolve tới sát/quá trần KHÔNG được làm get_asset_scan_info bị 429
        ở call đầu (bucket riêng theo cmd) — chống chặn nhầm cross-endpoint."""
        from assetcore.api.imm00 import (
            resolve_qr_token, get_asset_scan_info, AC_QR_RESOLVE_RATE_LIMIT as N)
        asset = self._make_asset("twobucket")
        # vắt kiệt bucket resolve (N+1 → 429 ở resolve).
        self._drain(resolve_qr_token,
                    "assetcore.api.imm00.resolve_qr_token", N + 1,
                    token=asset.qr_token)
        # scan_info bucket RIÊNG → call đầu vẫn 200 (KHÔNG kế thừa counter resolve).
        env, exc = self._http_call(
            get_asset_scan_info,
            "assetcore.api.imm00.get_asset_scan_info",
            token=asset.qr_token)
        self.assertIsNone(exc, f"scan_info bucket riêng → call đầu KHÔNG 429: {exc!r}")
        self.assertTrue(env["success"])

    # ── 404 (token sai) VẪN bị đếm vào trần — chống enumeration ─────────────
    def test_404_calls_count_toward_limit(self):
        from assetcore.api.imm00 import (
            resolve_qr_token, AC_QR_RESOLVE_RATE_LIMIT as N)
        cmd = "assetcore.api.imm00.resolve_qr_token"
        bad = "khong-ton-tai-bruteforce-zzzz"
        # N call token-SAI (đều 404, KHÔNG raise) — counter vẫn tăng TRƯỚC thân hàm.
        for i in range(N):
            env, exc = self._http_call(resolve_qr_token, cmd, token=bad)
            self.assertIsNone(exc, f"404 call #{i+1} KHÔNG raise (counter tăng)")
            self.assertEqual(env["http_status"], 404)
        # call N+1 token-sai → 429 (brute-forcer dội 404 vẫn bị bóp).
        _, exc = self._http_call(resolve_qr_token, cmd, token=bad)
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            "dò token-sai (404) VẪN bị tính → call N+1 → 429 (chống enumeration)")

    # ── Bypass test/CLI có chủ đích — gọi TRỰC TIẾP (no frappe.request) ─────
    def test_no_request_context_bypasses_limit(self):
        """Gọi resolve_qr_token TRỰC TIẾP >N lần (KHÔNG set frappe.local.request)
        → KHÔNG 429 (wrapper `if not frappe.request: return fn`). Đảm bảo suite cũ
        A2/A6 (gọi trực tiếp) KHÔNG regress."""
        from assetcore.api.imm00 import (
            resolve_qr_token, AC_QR_RESOLVE_RATE_LIMIT as N)
        asset = self._make_asset("bypass")
        had_req = getattr(frappe.local, "request", None)
        frappe.local.request = None
        try:
            for _ in range(N + 5):
                resp = resolve_qr_token(token=asset.qr_token)
                self.assertTrue(resp["success"],
                                "gọi trực tiếp (no request) → KHÔNG bao giờ 429")
        finally:
            frappe.local.request = had_req

    # ── GUARD: nhóm GHI in-nhãn KHÔNG bị rate-limit (chống over-scope) ─────
    def test_write_endpoints_not_rate_limited(self):
        """get_asset_label_data[_batch] / mark_label_printed dội >N lần với user
        asset.write → vẫn 200, KHÔNG 429. Chống chặn nhầm in-nhãn-hàng-loạt
        (least-surprise, ADR-001 D4). LƯU Ý (Vòng 27 B / BR-00-38): rotate
        ``regenerate_asset_qr_token`` ĐÃ TÁCH RA — NAY CÓ @rate_limit (hằng/bucket
        RIÊNG, ngưỡng THẤP hơn) → KHÔNG còn trong danh sách 'không throttle'."""
        import inspect
        from assetcore.api.imm00 import (
            get_asset_label_data_batch, AC_QR_RESOLVE_RATE_LIMIT as N)

        # (a) Tĩnh: 3 endpoint in-nhãn KHÔNG mang decorator rate_limit (rotate ĐÃ
        #     tách — có @rate_limit RIÊNG, kiểm ở TestQrRegenerateRateLimit).
        from assetcore.api import imm00 as _api
        for fn_name in ("get_asset_label_data", "get_asset_label_data_batch",
                        "mark_label_printed"):
            src = inspect.getsource(getattr(_api, fn_name))
            self.assertNotIn(
                "@rate_limit", src,
                f"{fn_name} KHÔNG được mang @rate_limit (in-nhãn low-volume admin)")
        # rotate NAY CÓ @rate_limit (Vòng 27 B) — chứng minh quyết định đã đảo.
        regen_src = inspect.getsource(getattr(_api, "regenerate_asset_qr_token"))
        self.assertIn(
            "@rate_limit", regen_src,
            "regenerate_asset_qr_token PHẢI mang @rate_limit (Vòng 27 B / BR-00-38)")
        self.assertIn(
            "AC_QR_REGEN_RATE_LIMIT", regen_src,
            "rotate dùng hằng RIÊNG AC_QR_REGEN_RATE_LIMIT (KHÔNG chung resolve)")

        # (b) Hành vi: dội >N call get_asset_label_data_batch QUA HTTP với admin
        #     (asset.write) → KHÔNG 429 (mỗi call 200, list rỗng-ok).
        asset = self._make_asset("nolimit")
        cmd = "assetcore.api.imm00.get_asset_label_data_batch"
        for i in range(N + 3):
            env, exc = self._http_call(
                get_asset_label_data_batch, cmd, assets=[asset.name])
            self.assertNotIsInstance(
                exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
                f"get_asset_label_data_batch call #{i+1} KHÔNG được 429")
            self.assertIsNone(exc, f"call #{i+1} KHÔNG raise: {exc!r}")
            self.assertTrue(env["success"])

    # ── Regression — CAP_SET_VERSION KHÔNG đổi (rate-limit KHÔNG thêm cap) ──
    def test_cap_set_version_unchanged(self):
        from assetcore.services.shared.rbac import CAP_SET_VERSION
        self.assertEqual(
            CAP_SET_VERSION, "v95.3388ee5629c1",
            "thêm @rate_limit (decorator) KHÔNG đổi CAPABILITY_MAP → "
            "CAP_SET_VERSION GIỮ v95.3388ee5629c1 (no FE auth.ts churn)")


# ──────────────────────────────────────────────────────────────────────────
# Vòng 27 B (BR-00-38) — Rate-limit endpoint GHI rotate `regenerate_asset_qr_token`.
# @rate_limit(limit=AC_QR_REGEN_RATE_LIMIT=10, seconds=60, ip_based=True) bọc NGOÀI
# thân hàm → 429 (RateLimitExceededError) TRƯỚC rbac.require("asset.write") ⇒ KHÔNG
# side-effect (0 token mới, 0 ALE qr_regenerated, 0 audit), no-leak. Hằng + bucket
# RIÊNG (KHÔNG chung resolve=30; cache key gồm cmd → counter tách biệt). Đóng bất
# đối xứng read-throttled (BR-00-29) / write-rotate-unthrottled (Self-Correction
# đảo quyết định Vòng 12 vốn loại rotate khỏi throttle). Hạ tầng test = mô phỏng
# HTTP context (frappe.local.request truthy + request_ip per-test-uniq + form_dict.cmd)
# + dọn cache `rl:*` ở teardown. Spec: 04 §II.1.8d / 02 BR-00-38 / 07 §III.6.d-ROTATERL.
# ──────────────────────────────────────────────────────────────────────────


class TestQrRegenerateRateLimit(unittest.TestCase):
    """Vòng 27 B — @rate_limit trên endpoint GHI rotate (RED-first, bucket RIÊNG)."""

    _CMD = "assetcore.api.imm00.regenerate_asset_qr_token"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị RotateRL QR (Vòng 27 B)",
            "description": "Category cho test rate-limit QR rotate",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        cls._READONLY_USER = "be_v27_regenrl_readonly@example.com"
        # User chỉ-đọc (read=1, write=0) — chứng minh RL chặn TRƯỚC rbac.require.
        if frappe.db.exists("User", cls._READONLY_USER):
            frappe.delete_doc("User", cls._READONLY_USER, force=True,
                              ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": cls._READONLY_USER,
            "first_name": "regenrl-ro", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        u.add_roles("Commissioning User")  # read=1, write=0 trên AC Asset
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", cls._READONLY_USER):
            frappe.delete_doc("User", cls._READONLY_USER, force=True,
                              ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []
        import uuid
        self._ip = f"10.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}." \
                   f"{uuid.uuid4().int % 250 + 1}"

    def tearDown(self):
        frappe.set_user("Administrator")
        try:
            frappe.cache.delete_keys("rl:")
        except Exception:
            pass
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy RotateRL {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"RGRL-SN-{uniq}",
            "asset_code": f"RGRL-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def _http_call(self, fn, cmd, **params):
        """Gọi endpoint @rate_limit QUA HTTP context (limiter ĐƯỢC kích hoạt).

        Mô phỏng đúng điều kiện ``rate_limit`` wrapper cần: ``frappe.local.request``
        truthy, ``frappe.local.request_ip`` (ip_based), ``frappe.form_dict.cmd``
        (cache key ``rl:{cmd}:{ip}``). Trả (envelope, exception).
        """
        class _Req:
            method = "POST"
            host = "miyano"
            headers: dict = {}
        had_req = getattr(frappe.local, "request", None)
        had_ip = getattr(frappe.local, "request_ip", None)
        had_cmd = frappe.form_dict.get("cmd")
        frappe.local.request = _Req()
        frappe.local.request_ip = self._ip
        frappe.form_dict.cmd = cmd
        try:
            try:
                return fn(**params), None
            except Exception as e:  # noqa: BLE001 — phân loại http_status_code
                return None, e
        finally:
            frappe.local.request = had_req
            frappe.local.request_ip = had_ip
            if had_cmd is None:
                frappe.form_dict.pop("cmd", None)
            else:
                frappe.form_dict.cmd = had_cmd

    def _drain(self, fn, cmd, n, **params):
        """Dội ``n`` call hợp lệ (≤ trần) — trả exception cuối cùng (None nếu OK)."""
        last_exc = None
        for _ in range(n):
            _, last_exc = self._http_call(fn, cmd, **params)
        return last_exc

    # ── Hằng RIÊNG tồn tại, đúng ngưỡng BA chốt (KHÔNG dùng chung resolve) ───
    def test_regen_constant_value(self):
        from assetcore.api.imm00 import AC_QR_REGEN_RATE_LIMIT
        self.assertEqual(
            AC_QR_REGEN_RATE_LIMIT, 10,
            "ngưỡng BA chốt rotate = 10 req/60s/IP (BR-00-38, THẤP hơn resolve)")

    def test_regen_constant_distinct_from_resolve(self):
        from assetcore.api.imm00 import (
            AC_QR_REGEN_RATE_LIMIT, AC_QR_RESOLVE_RATE_LIMIT)
        self.assertNotEqual(
            AC_QR_REGEN_RATE_LIMIT, AC_QR_RESOLVE_RATE_LIMIT,
            "hằng rotate RIÊNG — KHÔNG tái dùng AC_QR_RESOLVE_RATE_LIMIT")
        self.assertLess(
            AC_QR_REGEN_RATE_LIMIT, AC_QR_RESOLVE_RATE_LIMIT,
            "rotate hiếm hơn quét → ngưỡng THẤP hơn resolve (BR-00-38)")

    # ── Boundary ≤N → 200 {name, qr_url} no-raw-token (regression B-2) ──────
    def test_regen_under_limit_ok(self):
        from assetcore.api.imm00 import (
            regenerate_asset_qr_token, AC_QR_REGEN_RATE_LIMIT as N)
        asset = self._make_asset("under")
        cmd = self._CMD
        for i in range(N):
            env, exc = self._http_call(
                regenerate_asset_qr_token, cmd, asset=asset.name)
            self.assertIsNone(exc, f"call #{i+1} (≤N) KHÔNG throttle: {exc!r}")
            self.assertTrue(env["success"], f"call #{i+1} ≤N → 200")
            data = env["data"]
            self.assertEqual(set(data.keys()), {"name", "qr_url"},
                             "envelope CHỈ {name, qr_url} (no-raw-token, B-2)")
            self.assertNotIn("qr_token", data,
                             "≤N rotate KHÔNG surface token thô (regression B-2)")
            self.assertIn("/a/", data["qr_url"])

    # ── Boundary >N → 429, KHÔNG trả {name, qr_url} ─────────────────────────
    def test_regen_over_limit_429(self):
        from assetcore.api.imm00 import (
            regenerate_asset_qr_token, AC_QR_REGEN_RATE_LIMIT as N)
        asset = self._make_asset("over")
        cmd = self._CMD
        first_exc = self._drain(regenerate_asset_qr_token, cmd, N, asset=asset.name)
        self.assertIsNone(first_exc,
                          f"{N} call đầu trong window KHÔNG throttle: {first_exc!r}")
        env, exc = self._http_call(regenerate_asset_qr_token, cmd, asset=asset.name)
        self.assertIsNotNone(exc, f"call thứ {N+1} PHẢI raise 429 (vượt trần)")
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            f"vượt trần → 429 (RateLimitExceededError), KHÔNG {type(exc).__name__}")
        self.assertEqual(getattr(exc, "http_status_code", None), 429,
                         "exception map HTTP 429")
        self.assertIsNone(env, "429 KHÔNG trả {name, qr_url} (no payload built)")

    # ── 429 → KHÔNG side-effect (token KHÔNG đổi, 0 ALE, 0 audit) ───────────
    def test_regen_429_no_side_effect(self):
        from assetcore.api.imm00 import (
            regenerate_asset_qr_token, AC_QR_REGEN_RATE_LIMIT as N)
        asset = self._make_asset("noside")
        cmd = self._CMD
        # Vắt kiệt trần (N call hợp lệ — mỗi call rotate đổi token; đo SAU N).
        self._drain(regenerate_asset_qr_token, cmd, N, asset=asset.name)
        token_before = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        ale_before = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": "qr_regenerated"})
        audit_before = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        # call N+1 → 429 (chặn TRƯỚC thân hàm ⇒ KHÔNG chạm service).
        env, exc = self._http_call(regenerate_asset_qr_token, cmd, asset=asset.name)
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            "call vượt trần PHẢI 429")
        self.assertIsNone(env, "429 KHÔNG trả envelope")
        token_after = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        ale_after = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": "qr_regenerated"})
        audit_after = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        self.assertEqual(token_after, token_before,
                         "429 → qr_token KHÔNG đổi (KHÔNG overwrite)")
        self.assertEqual(ale_after, ale_before,
                         "429 → 0 ALE qr_regenerated MỚI (no side-effect)")
        self.assertEqual(audit_after, audit_before,
                         "429 → 0 IMM Audit Trail MỚI (no side-effect)")

    # ── 429 no-leak (message KHÔNG chứa name/asset_code/token cũ) ───────────
    def test_regen_429_no_leak(self):
        from assetcore.api.imm00 import (
            regenerate_asset_qr_token, AC_QR_REGEN_RATE_LIMIT as N)
        asset = self._make_asset("noleak")
        old_token = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        cmd = self._CMD
        self._drain(regenerate_asset_qr_token, cmd, N, asset=asset.name)
        _, exc = self._http_call(regenerate_asset_qr_token, cmd, asset=asset.name)
        self.assertIsNotNone(exc, "call vượt trần PHẢI raise 429")
        msg = str(getattr(exc, "message", "") or "") + str(exc)
        for leak in (asset.name, asset.asset_code, old_token):
            self.assertNotIn(leak, msg,
                             "429 message KHÔNG leak name/asset_code/qr_token")

    # ── Bucket RIÊNG — hammer rotate KHÔNG bóp resolve (cmd-key tách) ───────
    def test_regen_separate_bucket_from_resolve(self):
        from assetcore.api.imm00 import (
            regenerate_asset_qr_token, resolve_qr_token,
            AC_QR_REGEN_RATE_LIMIT as N)
        asset = self._make_asset("twobucket")
        # vắt kiệt bucket rotate (N+1 → 429 ở rotate).
        self._drain(regenerate_asset_qr_token, self._CMD, N + 1, asset=asset.name)
        # resolve bucket RIÊNG (cmd khác) → call đầu vẫn 200 (KHÔNG kế thừa counter).
        token = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        env, exc = self._http_call(
            resolve_qr_token, "assetcore.api.imm00.resolve_qr_token", token=token)
        self.assertIsNone(
            exc, f"resolve bucket riêng → call đầu KHÔNG 429: {exc!r}")
        self.assertTrue(env["success"], "resolve vẫn 200 trong cùng cửa sổ")
        self.assertEqual(env["data"]["name"], asset.name)

    # ── Thứ tự gate — RL (429) chạy TRƯỚC rbac.require (403) ────────────────
    def test_regen_429_runs_before_rbac(self):
        """User KHÔNG asset.write (chỉ read), dội >N → call vượt trần → 429
        (KHÔNG 403). Decorator @rate_limit bọc NGOÀI thân → counter+throw TRƯỚC
        khi thân chạy rbac.require("asset.write"). Đồng nhất precedent resolve."""
        from assetcore.api.imm00 import (
            regenerate_asset_qr_token, AC_QR_REGEN_RATE_LIMIT as N)
        from assetcore.services.shared import rbac
        asset = self._make_asset("order")
        cmd = self._CMD
        frappe.set_user(self._READONLY_USER)
        try:
            self.assertFalse(rbac.can("asset.write"),
                             "tiền đề: user chỉ-đọc KHÔNG có asset.write")
            # ≤N: user chỉ-đọc → PermissionError (403) — RBAC chạy SAU RL khi chưa trần.
            _, exc_under = self._http_call(
                regenerate_asset_qr_token, cmd, asset=asset.name)
            self.assertIsInstance(
                exc_under, frappe.PermissionError,
                "≤N + thiếu asset.write → 403 (RBAC sau RL khi chưa trần)")
            # Dội cho vượt trần (counter tăng kể cả khi thân raise 403).
            for _ in range(N):
                self._http_call(regenerate_asset_qr_token, cmd, asset=asset.name)
            # call vượt trần → 429 (RL chặn TRƯỚC rbac.require, KHÔNG 403).
            _, exc_over = self._http_call(
                regenerate_asset_qr_token, cmd, asset=asset.name)
            self.assertIsInstance(
                exc_over,
                (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
                f"vượt trần → 429 TRƯỚC PermissionError, KHÔNG {type(exc_over).__name__}")
        finally:
            frappe.set_user("Administrator")

    # ── Bypass test/CLI — gọi TRỰC TIẾP (no frappe.request) → KHÔNG 429 ─────
    def test_regen_no_request_context_bypasses(self):
        """Gọi regenerate_asset_qr_token TRỰC TIẾP >N lần (KHÔNG set
        frappe.local.request) → KHÔNG 429 (wrapper `if not frappe.request: return
        fn`). Đảm bảo TestRegenerateQrToken cũ (gọi trực tiếp) KHÔNG regress."""
        from assetcore.api.imm00 import (
            regenerate_asset_qr_token, AC_QR_REGEN_RATE_LIMIT as N)
        asset = self._make_asset("bypass")
        had_req = getattr(frappe.local, "request", None)
        frappe.local.request = None
        try:
            for _ in range(N + 5):
                resp = regenerate_asset_qr_token(asset=asset.name)
                self.assertTrue(resp["success"],
                                "gọi trực tiếp (no request) → KHÔNG bao giờ 429")
        finally:
            frappe.local.request = had_req

    # ── Regression — CAP_SET_VERSION KHÔNG đổi (decorator KHÔNG thêm cap) ───
    def test_regen_cap_set_version_unchanged(self):
        from assetcore.services.shared.rbac import CAP_SET_VERSION
        self.assertEqual(
            CAP_SET_VERSION, "v95.3388ee5629c1",
            "thêm @rate_limit lên rotate KHÔNG đổi CAPABILITY_MAP → "
            "CAP_SET_VERSION GIỮ v95.3388ee5629c1")


# ─── B (hardening) — base-URL công khai cấu hình được cho deep-link QR ─────────
# RC: `_build_qr_url` resolve host nội bộ `http://miyano/a/<token>` → camera điện
# thoại KHÔNG mở được (P2 blocker eval Vòng 4/9/10). Đóng kín bằng site_config key
# MỚI `assetcore_qr_base_url` (vd https://htm.benhvien.vn). KHÔNG hardcode, KHÔNG
# cap/field/DocType mới. Consumer DÙNG CHUNG `_build_qr_url` (1 SSoT).
class TestQrBaseUrl(unittest.TestCase):
    """B — `_build_qr_url` ưu tiên base-URL công khai cấu hình được (config → get_url)."""

    _EVAL_TOKEN = "AanTF-3HT9K3dFyWyaZLNw"  # token thật từ eval (regression mangle)
    _CONF_KEY = "assetcore_qr_base_url"

    def setUp(self):
        frappe.set_user("Administrator")
        # Lưu giá trị conf gốc để khôi phục — KHÔNG để rò sang test khác.
        self._orig_conf = frappe.conf.get(self._CONF_KEY)

    def tearDown(self):
        # Khôi phục đúng trạng thái conf ban đầu (None → pop, có → set lại).
        if self._orig_conf is None:
            frappe.conf.pop(self._CONF_KEY, None)
        else:
            frappe.conf[self._CONF_KEY] = self._orig_conf
        frappe.set_user("Administrator")

    def _set_conf(self, value):
        if value is None:
            frappe.conf.pop(self._CONF_KEY, None)
        else:
            frappe.conf[self._CONF_KEY] = value

    # (1) conf set host công khai → URL dùng base công khai.
    def test_build_url_uses_public_base_when_conf_set(self):
        from assetcore.services.imm00 import _build_qr_url
        self._set_conf("https://htm.bv.vn")
        self.assertEqual(_build_qr_url("TOK"), "https://htm.bv.vn/a/TOK")

    # (2) base có trailing slash → vẫn đúng 1 dấu '/a/' (strip dấu '/' thừa cuối).
    def test_build_url_strips_trailing_slash(self):
        from assetcore.services.imm00 import _build_qr_url
        self._set_conf("https://htm.bv.vn/")
        self.assertEqual(_build_qr_url("TOK"), "https://htm.bv.vn/a/TOK")
        self.assertNotIn("//a/", _build_qr_url("TOK"))

    # (3) conf vắng/rỗng → fallback frappe.utils.get_url('/a/TOK') (hành vi cũ).
    def test_build_url_fallback_when_conf_absent(self):
        from unittest import mock
        from assetcore.services import imm00 as svc
        self._set_conf(None)
        with mock.patch.object(svc.frappe.utils, "get_url",
                               return_value="http://miyano/a/TOK") as m:
            out = svc._build_qr_url("TOK")
        m.assert_called_once_with("/a/TOK")
        self.assertEqual(out, "http://miyano/a/TOK")

    def test_build_url_fallback_when_conf_empty(self):
        from assetcore.services.imm00 import _build_qr_url, _qr_base_url
        self._set_conf("")
        self.assertIsNone(_qr_base_url(), "conf rỗng → _qr_base_url None")
        out = _build_qr_url("TOK")
        self.assertTrue(out.endswith("/a/TOK"))
        self.assertRegex(out, r"^https?://")

    # (4) conf không-scheme → fallback + KHÔNG raise (log cảnh báo, không gãy in tem).
    def test_build_url_rejects_missing_scheme(self):
        from assetcore.services.imm00 import _build_qr_url, _qr_base_url
        self._set_conf("htm.bv.vn")
        self.assertIsNone(_qr_base_url(), "thiếu scheme → reject → None")
        out = _build_qr_url("TOK")  # KHÔNG raise (fallback get_url)
        self.assertTrue(out.endswith("/a/TOK"))
        self.assertRegex(out, r"^https?://", "fallback get_url vẫn có scheme")

    # (5) conf có path/query/fragment → reject (KHÔNG để base-URL lồng /a/...).
    def test_build_url_rejects_path_in_base(self):
        from assetcore.services.imm00 import _qr_base_url, _build_qr_url
        for bad in ("https://x.vn/app", "https://x.vn/?q=1", "https://x.vn/#a",
                    "https://x.vn/a/INJECT", "https://x vn"):
            self._set_conf(bad)
            self.assertIsNone(_qr_base_url(),
                              f"base sai '{bad}' → reject (None)")
            self.assertTrue(_build_qr_url("TOK").endswith("/a/TOK"),
                            f"base sai '{bad}' → fallback get_url, KHÔNG raise")

    # (6) token thật eval KHÔNG bị URL-mangle (token y nguyên trong URL).
    def test_eval_token_not_mangled(self):
        from assetcore.services.imm00 import _build_qr_url
        self._set_conf("https://htm.bv.vn")
        out = _build_qr_url(self._EVAL_TOKEN)
        self.assertEqual(out, f"https://htm.bv.vn/a/{self._EVAL_TOKEN}")
        self.assertIn(self._EVAL_TOKEN, out, "token urlsafe nối thẳng, không mangle")

    # ── consumer SSoT: label single / batch dùng chung base công khai ──────────
    def _make_asset(self):
        import uuid
        uniq = uuid.uuid4().hex[:8]
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"QR Base Asset {uniq}",
            "asset_category": self._cat,
            "asset_code": f"QRB-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "QR Base URL Category (B)",
        }).insert(ignore_permissions=True).name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        _purge_category("QR Base URL Category (B)")
        frappe.db.commit()

    def _setup_assets_state(self):
        self._created: list[str] = []

    # (7) build_asset_label_data['qr_url'] dùng base công khai khi conf set.
    def test_label_single_uses_public_base(self):
        from assetcore.services.imm00 import build_asset_label_data
        self._setup_assets_state()
        try:
            self._set_conf("https://htm.bv.vn")
            asset = self._make_asset()
            token = frappe.db.get_value("AC Asset", asset.name, "qr_token")
            data = build_asset_label_data(asset.name)
            self.assertEqual(data["qr_url"], f"https://htm.bv.vn/a/{token}")
        finally:
            for n in self._created:
                _purge_asset(n)
            frappe.db.commit()

    # (8) build_asset_label_data_batch mỗi item qr_url cùng base công khai.
    def test_label_batch_uses_public_base(self):
        from assetcore.services.imm00 import build_asset_label_data_batch
        self._setup_assets_state()
        try:
            self._set_conf("https://htm.bv.vn")
            a = self._make_asset()
            b = self._make_asset()
            ta = frappe.db.get_value("AC Asset", a.name, "qr_token")
            tb = frappe.db.get_value("AC Asset", b.name, "qr_token")
            out = build_asset_label_data_batch([a.name, b.name])
            self.assertEqual(out[0]["qr_url"], f"https://htm.bv.vn/a/{ta}")
            self.assertEqual(out[1]["qr_url"], f"https://htm.bv.vn/a/{tb}")
        finally:
            for n in self._created:
                _purge_asset(n)
            frappe.db.commit()

    # (9) regression: cap-set version vẫn v95.3388ee5629c1 (KHÔNG cap change).
    def test_cap_set_version_unchanged(self):
        from assetcore.services.shared.rbac import CAP_SET_VERSION
        self.assertEqual(
            CAP_SET_VERSION, "v95.3388ee5629c1",
            "base-URL deep-link là logic dựng URL — KHÔNG thêm cap/field/DocType")


# ──────────────────────────────────────────────────────────────────────────
# B (hardening / enumeration-safety) — no-raw-token parity trên MỌI đường ĐỌC
# AC Asset. ADR-001 §D4 rule 9: token thô (qr_token) KHÔNG BAO GIỜ rời BE qua
# endpoint đọc asset. Root cause: get_asset trả frappe.get_doc(...).as_dict() →
# leak field qr_token (hidden/read_only nhưng VẪN nằm trong as_dict). Fix: 1
# helper SSoT _strip_qr_token(doc) pop key trước _ok(). Parity: get_asset,
# get_asset_timeline, get_asset_kpi, list_assets đều KHÔNG có qr_token/token.
# Deep-link vẫn dùng qua qr_url (build_asset_label_data server-side, A3/A4).
# Test-case RED viết TRƯỚC fix (test_get_asset_no_raw_qr_token fail vì as_dict
# leak). KHÔNG cap/field/DocType/enum mới → CAP_SET_VERSION GIỮ v95.3388ee5629c1.
# ──────────────────────────────────────────────────────────────────────────
class TestGetAssetNoRawQrToken(unittest.TestCase):
    """B — no-raw-token parity MỌI đường đọc AC Asset (ADR-001 D4 rule 9)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị No-Raw-Token (B)",
            "description": "Category cho test no-raw-token get_asset",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        cls.model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": "NRT Dräger Evita V500",
            "manufacturer": "Dräger Medical",
            "medical_device_class": "Class II",
            "asset_category": cls.cat.name,
        }).insert(ignore_permissions=True)
        cls.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "NRT Phòng ICU — Tầng 3",
            "location_type": "Room",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Location", cls.loc.name,
                          force=True, ignore_permissions=True)
        frappe.delete_doc("IMM Device Model", cls.model.name,
                          force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        # device_model + location set → enrich _name fields có mặt (test
        # payload-intact xác minh strip KHÔNG làm mất field enrich).
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy NoRawToken {uniq}",
            "asset_category": self.cat.name,
            "device_model": self.model.name,
            "location": self.loc.name,
            "manufacturer_sn": f"NRT-SN-{uniq}",
            "asset_code": f"NRT-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    # ── RED-first — get_asset KHÔNG leak qr_token thô ───────────────────────
    def test_get_asset_no_raw_qr_token(self):
        """[RED] asset CÓ qr_token thật → 'qr_token' not in data['data'].

        Trước fix: get_asset trả frappe.get_doc(...).as_dict() → key qr_token
        lọt nguyên văn (dù hidden/read_only). Sau fix: _strip_qr_token pop key.
        """
        from assetcore.api.imm00 import get_asset
        asset = self._make_asset("raw")
        self.assertTrue(
            frappe.db.get_value("AC Asset", asset.name, "qr_token"),
            "tiền đề: asset thật sự CÓ qr_token (before_insert sinh idempotent)")
        resp = get_asset(name=asset.name)
        self.assertTrue(resp["success"], "asset tồn tại → success")
        data = resp["data"]
        self.assertNotIn("qr_token", data,
                         "get_asset KHÔNG được trả qr_token thô (ADR D4 rule 9)")
        # parity với resolve/regenerate: token không xuất hiện dưới key 'token' nào
        self.assertNotIn("token", data,
                         "KHÔNG có key 'token' thô trong payload đọc asset")

    # ── payload intact — strip ĐÚNG 1 key, KHÔNG strip nhầm field cốt lõi ────
    def test_get_asset_payload_intact(self):
        """Field cốt lõi VẪN có mặt sau strip → AssetDetail render đủ data."""
        from assetcore.api.imm00 import get_asset
        asset = self._make_asset("intact")
        resp = get_asset(name=asset.name)
        data = resp["data"]
        for fld in ("name", "asset_code", "lifecycle_status",
                    "category_name", "device_model_name", "location_name"):
            self.assertIn(fld, data,
                          f"strip KHÔNG được làm mất field cốt lõi '{fld}'")
        self.assertEqual(data["name"], asset.name)
        self.assertEqual(data["asset_code"], asset.asset_code)
        self.assertEqual(data["lifecycle_status"], "Active")
        self.assertEqual(data["category_name"], "Thiết bị No-Raw-Token (B)")

    # ── timeline — đường đọc-asset thứ 2 cũng no-raw-token ───────────────────
    def test_get_asset_timeline_no_qr_token(self):
        """get_asset_timeline đọc Asset Lifecycle Event (fields tường minh) →
        KHÔNG echo qr_token/token. Items lifecycle event cũng không leak."""
        from assetcore.api.imm00 import get_asset_timeline
        asset = self._make_asset("tl")
        resp = get_asset_timeline(name=asset.name)
        self.assertTrue(resp["success"])
        data = resp["data"]
        self.assertNotIn("qr_token", data, "timeline payload KHÔNG có qr_token")
        for it in data.get("items", []):
            self.assertNotIn("qr_token", it,
                             "lifecycle event item KHÔNG có qr_token")
            self.assertNotIn("token", it,
                             "lifecycle event item KHÔNG có key 'token' thô")

    # ── kpi — đường đọc-asset thứ 3 cũng no-raw-token ───────────────────────
    def test_get_asset_kpi_no_qr_token(self):
        """get_asset_kpi trả dict KPI tường minh (compute on-the-fly) → KHÔNG
        echo qr_token (đọc doc nhưng chỉ surface field KPI/lifecycle)."""
        from assetcore.api.imm00 import get_asset_kpi
        asset = self._make_asset("kpi")
        resp = get_asset_kpi(name=asset.name)
        self.assertTrue(resp["success"])
        data = resp["data"]
        self.assertNotIn("qr_token", data, "kpi payload KHÔNG có qr_token")
        self.assertNotIn("token", data, "kpi payload KHÔNG có key 'token' thô")
        # parity: KPI vẫn surface field cốt lõi (regression — strip không làm vỡ)
        self.assertIn("lifecycle_status", data)
        self.assertIn("uptime_pct", data)

    # ── list — regression lock parity ───────────────────────────────────────
    def test_list_assets_no_qr_token(self):
        """list_assets fields=[...] tường minh → items KHÔNG select qr_token."""
        from assetcore.api.imm00 import list_assets
        asset = self._make_asset("list")
        resp = list_assets(page=1, page_size=100)
        self.assertTrue(resp["success"])
        items = resp["data"]["items"]
        # asset vừa tạo phải nằm trong list (Active, Admin scope)
        names = [it.get("name") for it in items]
        self.assertIn(asset.name, names, "asset vừa tạo phải có trong list")
        for it in items:
            self.assertNotIn("qr_token", it,
                             "list_assets item KHÔNG được chứa qr_token")
            self.assertNotIn("token", it,
                             "list_assets item KHÔNG được chứa key 'token' thô")

    # ── grep/AST guard — mọi get_doc(_DT_ASSET...).as_dict() đường return đều
    #    qua _strip_qr_token (chống thêm endpoint asset-read mới leak) ─────────
    def test_no_asset_read_endpoint_leaks_qr_token(self):
        """AST guard: trong api/imm00.py, mọi biểu thức
        frappe.get_doc(_DT_ASSET, ...).as_dict() mà giá trị được TRẢ VỀ (return
        _ok(...) hoặc gán biến rồi return) PHẢI đi qua _strip_qr_token.

        Heuristic an toàn-bảo-thủ: với mỗi hàm có chứa
        get_doc(_DT_ASSET,...).as_dict(), nếu hàm ĐÓ có return _ok(<doc>) thì
        thân hàm PHẢI gọi _strip_qr_token. get_supplier/get_device_model... đọc
        DocType khác (KHÔNG _DT_ASSET) → không bị ràng buộc (chỉ AC Asset có
        field qr_token). Chống regress khi thêm endpoint asset-read mới.
        """
        import ast
        import inspect
        import assetcore.api.imm00 as mod

        src = inspect.getsource(mod)
        tree = ast.parse(src)

        def _calls_as_dict_on_asset(fn_node) -> bool:
            for node in ast.walk(fn_node):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "as_dict"):
                    # node.func.value là kết quả frappe.get_doc(...)
                    inner = node.func.value
                    if (isinstance(inner, ast.Call)
                            and isinstance(inner.func, ast.Attribute)
                            and inner.func.attr == "get_doc"
                            and inner.args):
                        first = inner.args[0]
                        # _DT_ASSET (Name) hoặc literal "AC Asset"
                        if isinstance(first, ast.Name) and first.id == "_DT_ASSET":
                            return True
                        if isinstance(first, ast.Constant) and first.value == "AC Asset":
                            return True
            return False

        def _calls_strip(fn_node) -> bool:
            for node in ast.walk(fn_node):
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Name)
                        and node.func.id == "_strip_qr_token"):
                    return True
                if (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "_strip_qr_token"):
                    return True
            return False

        offenders = []
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef):
                if _calls_as_dict_on_asset(fn) and not _calls_strip(fn):
                    offenders.append(fn.name)

        self.assertEqual(
            offenders, [],
            "Endpoint(s) đọc AC Asset qua as_dict() mà KHÔNG strip qr_token "
            f"(thêm _strip_qr_token trước return): {offenders}")

    # ── helper SSoT tồn tại + None-safe ─────────────────────────────────────
    def test_strip_qr_token_helper_none_safe(self):
        """_strip_qr_token là 1 helper SSoT: pop 'qr_token', None-safe, in-place."""
        from assetcore.api.imm00 import _strip_qr_token
        # None → None (không raise)
        self.assertIsNone(_strip_qr_token(None))
        # dict có qr_token → pop, giữ field khác
        d = {"name": "X", "qr_token": "secret", "asset_code": "A1"}
        out = _strip_qr_token(d)
        self.assertNotIn("qr_token", out)
        self.assertEqual(out["name"], "X")
        self.assertEqual(out["asset_code"], "A1")
        # dict không có qr_token → no-op (không raise)
        d2 = {"name": "Y"}
        self.assertEqual(_strip_qr_token(d2), {"name": "Y"})

    # ── IDOR + 404 preserved — no-regress RBAC sau khi thêm strip ────────────
    def test_get_asset_404_no_leak_preserved(self):
        """name không tồn tại → 404 leak-safe (KHÔNG 500, KHÔNG payload)."""
        from assetcore.api.imm00 import get_asset
        resp = get_asset(name="AC-ASSET-DOES-NOT-EXIST-0000")
        self.assertFalse(resp["success"], "asset không tồn tại → KHÔNG success")
        self.assertEqual(resp["http_status"], 404, "name không tồn tại → 404")
        self.assertNotIn("asset_code", resp.get("data") or {},
                         "404 KHÔNG leak payload")

    def test_get_asset_idor_vendor_out_of_scope_preserved(self):
        """Vendor ngoài scope → 403 IDOR (assert_vendor_can_access GIỮ NGUYÊN).

        Vendor Engineer (scope-restrict) + Repair User (DocPerm asset.read) →
        QUA gate read NHƯNG bị chặn ở IDOR vì asset ngoài WO được giao.
        """
        from assetcore.api.imm00 import get_asset
        asset = self._make_asset("idor")
        vendor_email = "vendor_getasset_idor@example.com"
        if frappe.db.exists("User", vendor_email):
            frappe.delete_doc("User", vendor_email, force=True,
                              ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": vendor_email,
            "first_name": "Vendor GetAsset IDOR", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        u.add_roles("Vendor Engineer", "Repair User")
        frappe.db.commit()
        frappe.set_user(vendor_email)
        try:
            resp = get_asset(name=asset.name)
            self.assertFalse(resp["success"], "vendor ngoài scope → KHÔNG success")
            self.assertEqual(resp["http_status"], 403,
                             "vendor ngoài scope → 403 (IDOR guard giữ nguyên)")
            self.assertNotIn("asset_code", resp.get("data") or {},
                             "KHÔNG leak payload asset ngoài scope")
            self.assertNotIn("qr_token", resp.get("data") or {},
                             "403 cũng KHÔNG leak qr_token")
        finally:
            frappe.set_user("Administrator")
            if frappe.db.exists("User", vendor_email):
                frappe.delete_doc("User", vendor_email,
                                  force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── no-churn guard — CAP_SET_VERSION KHÔNG đổi (KHÔNG thêm cap) ──────────
    def test_cap_set_version_unchanged(self):
        """strip qr_token = logic API-response — KHÔNG cap/field/DocType/enum."""
        from assetcore.services.shared.rbac import CAP_SET_VERSION
        self.assertEqual(
            CAP_SET_VERSION, "v97.c30c69b8974d",
            "no-raw-token strip KHÔNG thêm cap; giá trị hiện hành v97.c30c69b8974d (sau D6)")


class TestGetAssetIdentityPayload(unittest.TestCase):
    """[V1-E] BE guard — get_asset PHẢI trả CẢ 2 key định danh: asset_code
    ('Mã tài sản' = PK) VÀ manufacturer_sn ('Số serial NSX' = field nghiệp vụ).

    CONTEXT (ADR-IMM00-ASSETCODE §D1/D4): màn AssetDetailView (FE) hiển thị 2 hàng
    TÁCH BẠCH 'Mã tài sản' (asset_code, fallback name) và 'Số serial NSX'
    (manufacturer_sn). FE chỉ render — KHÔNG derive. ⇒ Contract đọc-asset PHẢI luôn
    surface 2 key NÀY, nếu không UI rớt trường định danh (regression im lặng).

    Guard = KEY-PRESENCE (không phụ thuộc GIÁ TRỊ): chống regress nếu ai đó sửa
    fields-list / _strip_qr_token / as_dict làm rớt 1 trong 2 key. get_asset trả full
    doc via _strip_qr_token(frappe.get_doc(...).as_dict()) (api/imm00.py L294) ⇒ kỳ
    vọng GREEN ngay (no-op BE — chỉ khoá contract). Đỏ ⇒ root-cause bổ sung key.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Định danh (V1-E)",
            "description": "Category cho test identity-payload get_asset",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, *, with_serial=True):
        import uuid
        uniq = uuid.uuid4().hex[:8]
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy Định danh {uniq}",
            "asset_category": self.cat.name,
            "asset_code": f"IDP-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        if with_serial:
            data["manufacturer_sn"] = f"IDP-SN-{uniq}"
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def test_get_asset_payload_has_identity_keys(self):
        """KEY-PRESENCE: payload chứa CẢ 'asset_code' VÀ 'manufacturer_sn'."""
        from assetcore.api.imm00 import get_asset
        asset = self._make_asset(with_serial=True)
        resp = get_asset(name=asset.name)
        self.assertTrue(resp["success"], "asset tồn tại → success")
        data = resp["data"]
        self.assertIn("asset_code", data,
                      "get_asset PHẢI trả key 'asset_code' (Mã tài sản — ADR D4)")
        self.assertIn("manufacturer_sn", data,
                      "get_asset PHẢI trả key 'manufacturer_sn' (Số serial NSX — ADR D4)")
        # value-parity (định danh không bị clobber/đổi qua tầng API)
        self.assertEqual(data["asset_code"], asset.asset_code)
        self.assertEqual(data["manufacturer_sn"], asset.manufacturer_sn)

    def test_identity_keys_present_even_when_serial_empty(self):
        """Key-presence ĐỘC LẬP giá trị: serial rỗng → key VẪN có mặt (value rỗng),
        KHÔNG bị as_dict bỏ key ⇒ FE luôn render hàng 'Số serial NSX' (fallback '—')."""
        from assetcore.api.imm00 import get_asset
        asset = self._make_asset(with_serial=False)
        data = get_asset(name=asset.name)["data"]
        self.assertIn("asset_code", data)
        self.assertIn("manufacturer_sn", data,
                      "key 'manufacturer_sn' PHẢI có mặt kể cả khi giá trị rỗng")
        # asset_code == name (invariant D5) → fallback FE an toàn
        self.assertEqual(data["asset_code"], asset.name)


_AC_ASSET_NAME_RE = re.compile(r"^AC-ASSET-\d{4}-\d{5}$")


class TestACAssetCodeNaming(unittest.TestCase):
    """QA-1..5 — định danh tài sản: autoname 2 nhánh + asset_code DB-unique/immutable
    + manufacturer_sn app-unique/mutable.

    Phủ ĐỦ acceptance V1-GATE asset-code (ADR-IMM00-ASSETCODE D1–D5):
      - QA-1 autoname 2 nhánh (trống→series ^AC-ASSET-\\d{4}-\\d{5}$ & asset_code==name;
        nhập 'TS-LAB-001'→name=='TS-LAB-001' & asset_code=='TS-LAB-001').
      - QA-2 asset_code DB-unique + IMMUTABLE sau tạo (đổi rồi save → throw).
      - QA-3 manufacturer_sn app-unique nhưng MUTABLE (đổi sang giá trị mới → OK).
      - QA-4 KHÔNG default-theo-serial (manufacturer_sn có, asset_code trống →
        auto-gen series, KHÔNG copy serial).
      - QA-5 invariant asset_code==name cho CẢ 2 nhánh tạo.
      - Pattern reject (khoảng trắng / ký tự lạ) + whitespace trim.

    Tự dọn fixture qua addCleanup(_purge_asset) ⇒ chạy lặp 2 lần vẫn GREEN, no leak,
    no real-data collision (mọi mã test mang prefix run-token duy nhất).
    """

    @classmethod
    def setUpClass(cls):
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị chẩn đoán hình ảnh — Định danh test",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        _purge_category("Thiết bị chẩn đoán hình ảnh — Định danh test")

    def setUp(self):
        # Run-token duy nhất / phương thức test → mọi asset_code & serial test
        # KHÔNG đụng data thật và KHÔNG đụng nhau khi chạy lặp.
        self._tok = frappe.generate_hash(length=6).upper()

    def _new_asset(self, **overrides):
        """Tạo AC Asset tối thiểu qua đường chuẩn (KHÔNG bypass autoname/validate).

        addCleanup ⇒ tự purge dù test pass/fail. lifecycle_status để mặc định
        (Draft) — autoname/validate chạy đầy đủ như production create flow.
        """
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Asset định danh {self._tok}",
            "asset_category": self.cat.name,
        }
        data.update(overrides)
        doc = frappe.get_doc(data).insert(ignore_permissions=True)
        self.addCleanup(_purge_asset, doc.name)
        return doc

    # ── QA-1 (a) autoname blank → series ──────────────────────────────────────
    def test_autoname_blank_generates_series(self):
        asset = self._new_asset()  # KHÔNG truyền asset_code
        self.assertRegex(
            asset.name, _AC_ASSET_NAME_RE,
            "asset_code trống → name phải khớp ^AC-ASSET-\\d{4}-\\d{5}$",
        )
        self.assertEqual(asset.asset_code, asset.name,
                         "QA-1a: asset_code phải == name sau auto-gen")

    # ── QA-1 (b) autoname supplied → name == code ─────────────────────────────
    def test_autoname_supplied_used_as_name(self):
        code = f"TS-LAB-{self._tok}"
        asset = self._new_asset(asset_code=code)
        self.assertEqual(asset.name, code, "QA-1b: name phải == asset_code đã nhập")
        self.assertEqual(asset.asset_code, code,
                         "QA-1b: asset_code giữ nguyên giá trị nhập")

    # ── QA-2 asset_code DB-unique (collision) ─────────────────────────────────
    def test_asset_code_db_unique_collision_throws(self):
        code = f"TS-DUP-{self._tok}"
        self._new_asset(asset_code=code)
        with self.assertRaises((frappe.DuplicateEntryError, frappe.ValidationError)):
            self._new_asset(asset_code=code)

    # ── QA-2 asset_code IMMUTABLE sau tạo ─────────────────────────────────────
    def test_asset_code_immutable_after_create(self):
        asset = self._new_asset(asset_code=f"TS-IMM-{self._tok}")
        asset.asset_code = f"TS-IMM2-{self._tok}"
        with self.assertRaises(frappe.ValidationError) as ctx:
            asset.save(ignore_permissions=True)
        self.assertIn("không thể thay đổi", str(ctx.exception),
                      "throw phải nói rõ asset_code immutable")

    # ── QA-3 manufacturer_sn app-unique (collision) ──────────────────────────
    def test_manufacturer_sn_app_unique_collision_throws(self):
        serial = f"SN-DUP-{self._tok}"
        asset_a = self._new_asset(manufacturer_sn=serial)
        with self.assertRaises(frappe.ValidationError) as ctx:
            self._new_asset(manufacturer_sn=serial)
        msg = str(ctx.exception)
        # ADR-IMM00-ASSETCODE D4: nhãn VI 'Số serial NSX', KHÔNG lead-EN 'Serial number'.
        self.assertIn("Số serial NSX", msg,
                      "throw phải dùng nhãn VI 'Số serial NSX' (ADR D4) — parity import_validators")
        self.assertNotIn("Serial number", msg,
                         "KHÔNG còn lead-EN 'Serial number' trong message dup-serial")
        # No-leak định danh chéo: KHÔNG nhúng asset_code/name (PK) của tài sản KHÁC.
        self.assertNotIn(asset_a.name, msg,
                         "message KHÔNG được lộ PK (name/asset_code) của asset thứ nhất")
        # Serial chính chủ (giá trị user vừa nhập) vẫn hiện để người dùng nhận biết.
        self.assertIn(serial, msg,
                      "message phải chứa chính giá trị serial người dùng vừa nhập")

    # ── QA-3 manufacturer_sn MUTABLE (đổi sang giá trị mới → OK) ──────────────
    def test_manufacturer_sn_mutable_ok(self):
        asset = self._new_asset(manufacturer_sn=f"SN-OLD-{self._tok}")
        new_serial = f"SN-NEW-{self._tok}"
        asset.manufacturer_sn = new_serial
        asset.save(ignore_permissions=True)  # KHÔNG throw
        asset.reload()
        self.assertEqual(asset.manufacturer_sn, new_serial,
                         "QA-3: manufacturer_sn mutable — đổi giá trị mới phải lưu được")

    # ── QA-4 KHÔNG default-theo-serial ───────────────────────────────────────
    def test_blank_code_not_defaulted_from_serial(self):
        serial = f"SN-XYZ-{self._tok}"
        asset = self._new_asset(manufacturer_sn=serial)  # asset_code TRỐNG
        self.assertRegex(
            asset.asset_code, _AC_ASSET_NAME_RE,
            "QA-4: asset_code trống → auto-gen series, KHÔNG copy serial",
        )
        self.assertNotEqual(asset.asset_code, serial,
                            "QA-4: asset_code KHÔNG được lấy từ manufacturer_sn")
        self.assertEqual(asset.asset_code, asset.name)

    # ── QA-5 invariant asset_code == name cho CẢ 2 nhánh ─────────────────────
    def test_invariant_asset_code_equals_name_both_branches(self):
        blank = self._new_asset()
        self.assertEqual(blank.asset_code, blank.name,
                         "QA-5 nhánh trống: asset_code == name")
        supplied = self._new_asset(asset_code=f"TS-INV-{self._tok}")
        self.assertEqual(supplied.asset_code, supplied.name,
                         "QA-5 nhánh nhập: asset_code == name")

    # ── Pattern reject (khoảng trắng / ký tự lạ) ─────────────────────────────
    def test_asset_code_pattern_reject(self):
        for bad in (f"TS {self._tok}", f"TS#{self._tok}"):
            with self.subTest(bad=bad):
                with self.assertRaises(frappe.ValidationError) as ctx:
                    self._new_asset(asset_code=bad)
                self.assertIn("Mã tài sản chỉ được chứa", str(ctx.exception))

    # ── Whitespace trim ──────────────────────────────────────────────────────
    def test_asset_code_whitespace_trimmed(self):
        code = f"TS-WS-{self._tok}"
        asset = self._new_asset(asset_code=f"  {code}  ")
        self.assertEqual(asset.name, code,
                         "asset_code có khoảng trắng đầu/cuối → trim trước khi làm name")
        self.assertEqual(asset.asset_code, code)


class TestCreateAssetEndpoint(unittest.TestCase):
    """V1-B — api.imm00.create_asset (endpoint-level, đường HTTP create thực).

    Phủ 2 P1 (eval 2026-06-08):
      - B1: dup asset_code trên INSERT → 422 + VI 'đã tồn tại', KHÔNG 409 raw
        'DuplicateEntryError'/'Duplicate entry'/key 'PRIMARY'. Friendly check fire
        TRƯỚC khi chạm DB PRIMARY. Lần 2 fail → KHÔNG để row rác.
      - B2: thiếu Danh mục (asset_category) → 422 + nhãn VI 'Danh mục', KHÔNG lộ
        dev-string '[AC Asset' / 'asset_category' raw / 'MandatoryError'.
    + regression: blank code auto-gen series; explicit code verbatim; immutable
      vẫn chặn ở nhánh update.

    setUp dùng run-token duy nhất ⇒ chạy lặp GREEN, no real-data collision; mọi
    asset tạo qua endpoint được addCleanup(_purge_asset).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Danh mục test create_asset endpoint",
        }).insert(ignore_permissions=True)

    @classmethod
    def tearDownClass(cls):
        _purge_category("Danh mục test create_asset endpoint")

    def setUp(self):
        frappe.set_user("Administrator")
        self._tok = frappe.generate_hash(length=6).upper()
        self._saved_form_dict = getattr(frappe.local, "form_dict", None)

    def tearDown(self):
        frappe.local.form_dict = self._saved_form_dict or frappe._dict()

    def _call_create(self, **fields) -> dict:
        """Gọi create_asset như HTTP layer: nạp form_dict rồi invoke endpoint."""
        from assetcore.api.imm00 import create_asset
        payload = {"cmd": "assetcore.api.imm00.create_asset"}
        payload.update(fields)
        frappe.local.form_dict = frappe._dict(payload)
        resp = create_asset()
        if resp.get("success") and resp.get("data", {}).get("name"):
            self.addCleanup(_purge_asset, resp["data"]["name"])
        return resp

    @staticmethod
    def _blob(resp: dict) -> str:
        """Toàn bộ message + envelope → chuỗi để assert no-raw-leak."""
        return str(resp)

    # ── B1: dup asset_code trên INSERT → VI 422, KHÔNG raw 409 ────────────────
    def test_create_asset_dup_asset_code_on_insert_returns_vi_422(self):
        code = f"TS-LAB-{self._tok}"
        first = self._call_create(asset_name=f"Asset A {self._tok}",
                                   asset_category=self.cat.name, asset_code=code)
        self.assertTrue(first.get("success"), f"lần 1 phải tạo OK: {first}")

        second = self._call_create(asset_name=f"Asset B {self._tok}",
                                    asset_category=self.cat.name, asset_code=code)
        self.assertFalse(second.get("success"), "lần 2 (trùng code) phải fail")
        self.assertEqual(second.get("http_status"), 422,
                         f"dup asset_code phải trả 422, nhận: {second}")
        self.assertIn("đã tồn tại", second.get("error", ""),
                      "message phải là VI thân thiện 'đã tồn tại'")
        blob = self._blob(second)
        for leak in ("DuplicateEntry", "Duplicate entry", "PRIMARY", "MandatoryError"):
            self.assertNotIn(leak, blob, f"KHÔNG được lộ raw dev-string '{leak}'")

    def test_create_asset_dup_asset_code_no_orphan_row(self):
        code = f"TS-ORP-{self._tok}"
        self._call_create(asset_name=f"Asset orp {self._tok}",
                          asset_category=self.cat.name, asset_code=code)
        self._call_create(asset_name=f"Asset orp2 {self._tok}",
                          asset_category=self.cat.name, asset_code=code)
        self.assertEqual(
            frappe.db.count("AC Asset", {"asset_code": code}), 1,
            "lần 2 fail KHÔNG được tạo row rác — vẫn đúng 1 asset mang code này",
        )

    # ── B2: thiếu Danh mục → VI 422, KHÔNG lộ dev-string ──────────────────────
    def test_create_asset_missing_category_returns_vi_422(self):
        resp = self._call_create(asset_name=f"Asset no-cat {self._tok}")
        self.assertFalse(resp.get("success"), "thiếu category phải fail")
        self.assertEqual(resp.get("http_status"), 422,
                         f"thiếu category phải 422, nhận: {resp}")
        self.assertIn("Danh mục", resp.get("error", ""),
                      "message phải chứa nhãn VI 'Danh mục'")
        blob = self._blob(resp)
        for leak in ("[AC Asset", "MandatoryError", "AC-ASSET-2026"):
            self.assertNotIn(leak, blob, f"KHÔNG lộ dev-string '{leak}'")
        # 'asset_code'/'asset_category' raw fieldname KHÔNG được nằm trong message VI
        self.assertNotIn("asset_category", resp.get("error", ""),
                         "message VI KHÔNG được chứa raw fieldname")

    def test_create_asset_missing_name_returns_vi_422(self):
        resp = self._call_create(asset_category=self.cat.name)
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 422)
        self.assertIn("Tên tài sản", resp.get("error", ""),
                      "thiếu asset_name → nhãn VI 'Tên tài sản'")
        self.assertNotIn("MandatoryError", self._blob(resp))

    # ── Regression: auto-gen + verbatim + immutable ───────────────────────────
    def test_create_asset_blank_code_autogen_unchanged(self):
        resp = self._call_create(asset_name=f"Asset autogen {self._tok}",
                                  asset_category=self.cat.name)  # asset_code TRỐNG
        self.assertTrue(resp.get("success"), f"auto-gen phải OK: {resp}")
        name = resp["data"]["name"]
        self.assertRegex(name, _AC_ASSET_NAME_RE,
                         "asset_code trống → name khớp ^AC-ASSET-\\d{4}-\\d{5}$")
        self.assertEqual(frappe.db.get_value("AC Asset", name, "asset_code"), name,
                         "asset_code == name sau auto-gen")

    def test_create_asset_explicit_code_verbatim(self):
        code = f"TS-NEW-{self._tok}"
        resp = self._call_create(asset_name=f"Asset verbatim {self._tok}",
                                  asset_category=self.cat.name, asset_code=code)
        self.assertTrue(resp.get("success"), f"explicit code phải OK: {resp}")
        self.assertEqual(resp["data"]["name"], code,
                         "asset_code hợp lệ → dùng verbatim làm name")

    def test_validate_unique_asset_code_update_immutable_still_blocks(self):
        code = f"TS-UPD-{self._tok}"
        resp = self._call_create(asset_name=f"Asset upd {self._tok}",
                                  asset_category=self.cat.name, asset_code=code)
        self.assertTrue(resp.get("success"))
        doc = frappe.get_doc("AC Asset", resp["data"]["name"])
        doc.asset_code = f"TS-UPD2-{self._tok}"
        with self.assertRaises(frappe.ValidationError) as ctx:
            doc.save(ignore_permissions=True)
        self.assertIn("không thể thay đổi", str(ctx.exception),
                      "đổi asset_code trên doc đã tồn tại vẫn throw VI immutable")


def run_all():
    """Convenience runner for bench console."""
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
