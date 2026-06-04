# Copyright (c) 2026, AssetCore Team
"""IMM-00 foundation test suite.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm00
"""
import unittest
import frappe
from frappe.utils import nowdate, add_days, flt

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
        "asset_name": "_Test DeprBookZero",
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


def run_all():
    """Convenience runner for bench console."""
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
