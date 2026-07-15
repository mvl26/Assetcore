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
        import uuid
        # category_name có DB-unique constraint → uuid-suffix để setUpClass
        # idempotent: 1 lần crash/SIGKILL (commit dưới) KHÔNG poison DB vĩnh viễn
        # cho lần chạy sau (leaked record cũ KHÔNG còn đụng tên). name (CAT-####)
        # mới là ref thật cho model/asset — literal này KHÔNG bị assert ở đâu.
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"Thiết bị Chẩn đoán Hình ảnh {uuid.uuid4().hex[:8]}",
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
        import uuid
        # category_name (DB-unique) uuid-suffix — idempotent với leak từ run bị
        # SIGKILL (parity fix _make_asset). dept/loc/supplier KHÔNG unique → leak vô hại.
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"Máy thở & Hỗ trợ hô hấp {uuid.uuid4().hex[:8]}",
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
        import uuid
        # manufacturer_sn qua app-level validate "serial đã tồn tại" (KHÔNG DB-unique)
        # → uuid-suffix để asset leaked từ run bị SIGKILL (finally _purge_asset không
        # chạy) KHÔNG chặn lần sau. Parity mọi _make_asset khác trong file (đã uuid).
        tag = f"{suffix.lstrip('-') or '0001'}-{uuid.uuid4().hex[:8]}"
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


class TestCreateTransferRequiredFields(unittest.TestCase):
    """Asset Transfer requiredness contract: to_department mandatory, to_location optional.

    Business rule (phiếu điều chuyển): "Phòng ban mới" (to_department) là bắt buộc,
    "Vị trí mới" (to_location) có thể nhập hoặc không.
    """

    @classmethod
    def setUpClass(cls):
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Bơm tiêm điện (Transfer-Req test)",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)
        cls.dept_from = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Nội (Transfer-Req nguồn)",
        }).insert(ignore_permissions=True)
        cls.dept_to = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Ngoại (Transfer-Req đích)",
        }).insert(ignore_permissions=True)
        cls.loc_from = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "Phòng 101 (Transfer-Req nguồn)",
            "location_type": "Room",
        }).insert(ignore_permissions=True)
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": "Terumo TE-SS830 (Transfer-Req)",
            "asset_category": cls.cat.name,
            "department": cls.dept_from.name,
            "location": cls.loc_from.name,
            "lifecycle_status": "Commissioned",
        })

    @classmethod
    def tearDownClass(cls):
        _purge_asset(cls.asset.name)
        for dt, name in [
            ("AC Location", cls.loc_from.name),
            ("AC Department", cls.dept_from.name),
            ("AC Department", cls.dept_to.name),
            ("AC Asset Category", cls.cat.name),
        ]:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)

    def _base_payload(self):
        return {
            "asset": self.asset.name,
            "transfer_type": "Internal",
            "reason": "Điều chuyển phục vụ nhu cầu khoa",
        }

    def test_to_department_is_required(self):
        from assetcore.services.imm00 import create_transfer_request
        payload = self._base_payload()
        payload["to_location"] = self.loc_from.name  # location present, department omitted
        with self.assertRaises(frappe.ValidationError) as ctx:
            create_transfer_request(payload)
        self.assertIn("to_department", str(ctx.exception))

    def test_to_location_is_optional(self):
        from assetcore.services.imm00 import create_transfer_request
        payload = self._base_payload()
        payload["to_department"] = self.dept_to.name  # department present, location omitted
        result = create_transfer_request(payload)
        try:
            self.assertTrue(frappe.db.exists("Asset Transfer", result["name"]))
            doc = frappe.get_doc("Asset Transfer", result["name"])
            self.assertEqual(doc.to_department, self.dept_to.name)
            self.assertFalse(doc.to_location)
        finally:
            frappe.delete_doc("Asset Transfer", result["name"],
                              force=True, ignore_permissions=True)


class _SqlSpy:
    """Context manager đếm số lần ``frappe.db.sql`` chạm 1 bảng cụ thể.

    Dùng để chứng minh enrich N+1-free: số IN-query trên ``tabAC Location`` /
    ``tabAC Department`` / ``tabUser`` phải là HẰNG SỐ theo số phiếu (batch),
    KHÔNG tăng theo số row (per-row get_value).
    """

    def __init__(self):
        self.queries: list = []

    def __enter__(self):
        self._orig = frappe.db.sql

        def _spy(query, *args, **kwargs):
            self.queries.append(str(query))
            return self._orig(query, *args, **kwargs)

        frappe.db.sql = _spy
        return self

    def __exit__(self, *exc):
        frappe.db.sql = self._orig
        return False

    def count_table(self, table: str) -> int:
        return sum(1 for q in self.queries if f"`{table}`" in q)


class TestTransferEnrichNames(unittest.TestCase):
    """Vòng 16 (FR-00-TRF-01) — denorm tên Khoa/Vị trí/Người giữ cho phiếu Điều chuyển.

    ``list_transfers`` / ``get_transfer`` / ``get_transfer_full`` THÊM đúng 6 khóa
    ``*_name`` (from/to × location/department/custodian) + giữ ``asset_name``,
    coalesce ``''`` (NEVER None / NEVER raw Link-id), N+1-free (batch IN-query).
    Xem docs/imm-00 §III.12-NAMES / §II.1.13-TRANSFERENRICH / ADR-IMM00-TRANSFER-ENRICH.
    """

    RAW_LINK_RE = re.compile(r"^(AC-DEPT-|AC-LOC-|ER-\d|.+@)")

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Máy thở (Transfer-Enrich test)",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)
        cls.loc_a = frappe.get_doc({
            "doctype": "AC Location", "location_type": "Room",
            "location_name": "Phòng Mổ số 1 (Enrich nguồn)",
        }).insert(ignore_permissions=True)
        cls.loc_b = frappe.get_doc({
            "doctype": "AC Location", "location_type": "Room",
            "location_name": "Phòng Hồi sức A (Enrich đích)",
        }).insert(ignore_permissions=True)
        cls.dept_a = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Ngoại Tổng hợp (Enrich nguồn)",
        }).insert(ignore_permissions=True)
        cls.dept_b = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Hồi sức tích cực ICU (Enrich đích)",
        }).insert(ignore_permissions=True)
        cls.user_a = cls._mk_user("transfer.enrich.nguon@example.com", "Trần Thị", "Nguồn")
        cls.user_b = cls._mk_user("transfer.enrich.dich@example.com", "Lê Văn", "Đích")
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": "Dräger Evita V500 (Transfer-Enrich)",
            "asset_category": cls.cat.name,
            "department": cls.dept_a.name,
            "location": cls.loc_a.name,
            "lifecycle_status": "Commissioned",
        })
        # Transfer A: from=locA/deptA/userA → to=locB/deptB/userB
        cls.t_a = cls._mk_transfer(
            from_location=cls.loc_a.name, from_department=cls.dept_a.name,
            from_custodian=cls.user_a.name,
            to_location=cls.loc_b.name, to_department=cls.dept_b.name,
            to_custodian=cls.user_b.name,
        )
        # Transfer B: HOÁN ĐỔI nguồn/đích so với A → chứng minh KHÔNG cross-map
        cls.t_b = cls._mk_transfer(
            from_location=cls.loc_b.name, from_department=cls.dept_b.name,
            from_custodian=cls.user_b.name,
            to_location=cls.loc_a.name, to_department=cls.dept_a.name,
            to_custodian=cls.user_a.name,
        )
        # Transfer C: "bàn giao khởi tạo" — from_department + from_custodian + to_custodian RỖNG
        cls.t_c = cls._mk_transfer(
            from_location=cls.loc_a.name, from_department="", from_custodian="",
            to_location=cls.loc_b.name, to_department=cls.dept_b.name,
            to_custodian="",
        )
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in (cls.t_a, cls.t_b, cls.t_c):
            if frappe.db.exists("Asset Transfer", name):
                frappe.delete_doc("Asset Transfer", name, force=True, ignore_permissions=True)
        _purge_asset(cls.asset.name)
        for dt, name in [
            ("User", cls.user_a.name), ("User", cls.user_b.name),
            ("AC Location", cls.loc_a.name), ("AC Location", cls.loc_b.name),
            ("AC Department", cls.dept_a.name), ("AC Department", cls.dept_b.name),
            ("AC Asset Category", cls.cat.name),
        ]:
            if frappe.db.exists(dt, name):
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def _mk_user(cls, email, first, last):
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.new_doc("User")
        u.email = email
        u.first_name = first
        u.last_name = last
        u.user_type = "System User"
        u.enabled = 1
        u.send_welcome_email = 0
        u.flags.ignore_permissions = True
        u.insert()
        return u

    @classmethod
    def _mk_transfer(cls, **fields) -> str:
        doc = frappe.get_doc({
            "doctype": "Asset Transfer",
            "asset": cls.asset.name,
            "transfer_type": "Internal",
            "transfer_date": nowdate(),
            "reason": "Điều chuyển phục vụ nhu cầu khoa (enrich test)",
            **fields,
        })
        doc.insert(ignore_permissions=True)
        return doc.name

    def _list_items(self):
        from assetcore.api.imm00 import list_transfers
        env = list_transfers(asset=self.asset.name, page_size=50)
        self.assertTrue(env["success"])
        return env["data"]

    def _item_by_name(self, items, name):
        for it in items:
            if it["name"] == name:
                return it
        self.fail(f"Transfer {name} không có trong list")

    _SIX_KEYS = (
        "from_location_name", "to_location_name",
        "from_department_name", "to_department_name",
        "from_custodian_name", "to_custodian_name",
    )

    def _assert_no_raw_link(self, item):
        for k in self._SIX_KEYS:
            val = item.get(k)
            self.assertIsInstance(val, str, f"{k} phải là str, gặp {type(val)}")
            self.assertFalse(
                self.RAW_LINK_RE.match(val),
                f"{k} rò raw Link-id: {val!r}")

    # ── TC-1: list_transfers enrich đủ 6 _name khớp source ───────────────────
    def test_list_transfers_enriches_from_to_names(self):
        data = self._list_items()
        item = self._item_by_name(data["items"], self.t_a)
        # asset_name GIỮ nguyên
        self.assertEqual(item["asset_name"], self.asset.asset_name)
        # 6 _name khớp source doctype
        self.assertEqual(item["from_location_name"],
                         frappe.db.get_value("AC Location", self.loc_a.name, "location_name"))
        self.assertEqual(item["to_location_name"],
                         frappe.db.get_value("AC Location", self.loc_b.name, "location_name"))
        self.assertEqual(item["from_department_name"],
                         frappe.db.get_value("AC Department", self.dept_a.name, "department_name"))
        self.assertEqual(item["to_department_name"],
                         frappe.db.get_value("AC Department", self.dept_b.name, "department_name"))
        self.assertEqual(item["from_custodian_name"],
                         frappe.db.get_value("User", self.user_a.name, "full_name"))
        self.assertEqual(item["to_custodian_name"],
                         frappe.db.get_value("User", self.user_b.name, "full_name"))
        self._assert_no_raw_link(item)

    # ── TC-2: Link rỗng → '' NGHIÊM NGẶT (KHÔNG None, KHÔNG raw id) ───────────
    def test_list_transfers_blank_link_coalesces_empty_string(self):
        data = self._list_items()
        item = self._item_by_name(data["items"], self.t_c)
        # from_department + from_custodian + to_custodian RỖNG → '' str
        self.assertEqual(item["from_department_name"], "")
        self.assertEqual(item["from_custodian_name"], "")
        self.assertEqual(item["to_custodian_name"], "")
        self.assertIsNotNone(item["from_department_name"])  # KHÔNG None
        # khóa RỖNG vẫn present (đủ 6 khóa mọi item)
        for k in self._SIX_KEYS:
            self.assertIn(k, item, f"item thiếu khóa {k}")
        # nhánh có giá trị vẫn đúng
        self.assertEqual(item["from_location_name"],
                         frappe.db.get_value("AC Location", self.loc_a.name, "location_name"))
        self.assertEqual(item["to_department_name"],
                         frappe.db.get_value("AC Department", self.dept_b.name, "department_name"))
        self._assert_no_raw_link(item)

    # ── TC-3: get_transfer + get_transfer_full enrich đồng shape ─────────────
    def test_get_transfer_detail_enriches_names(self):
        from assetcore.api.imm00 import get_transfer, get_transfer_full
        for fn in (get_transfer, get_transfer_full):
            with self.subTest(endpoint=fn.__name__):
                env = fn(self.t_a)
                self.assertTrue(env["success"])
                doc = env["data"]
                self.assertEqual(doc["asset_name"], self.asset.asset_name)
                self.assertEqual(doc["from_location_name"],
                                 frappe.db.get_value("AC Location", self.loc_a.name, "location_name"))
                self.assertEqual(doc["to_custodian_name"],
                                 frappe.db.get_value("User", self.user_b.name, "full_name"))
                for k in self._SIX_KEYS:
                    self.assertIn(k, doc)
                self._assert_no_raw_link(doc)
                # nhánh Link rỗng → '' (parity list)
                env_c = fn(self.t_c)
                doc_c = env_c["data"]
                self.assertEqual(doc_c["from_department_name"], "")
                self.assertEqual(doc_c["from_custodian_name"], "")
                self._assert_no_raw_link(doc_c)

    # ── TC-4: N+1 guard — nhiều row map ĐÚNG _name của chính nó ──────────────
    def test_list_transfers_multiple_rows_map_correct(self):
        data = self._list_items()
        a = self._item_by_name(data["items"], self.t_a)
        b = self._item_by_name(data["items"], self.t_b)
        # A và B HOÁN ĐỔI nguồn/đích → nếu enrich cross-map, giá trị sẽ nhầm
        self.assertEqual(a["from_location_name"],
                         frappe.db.get_value("AC Location", self.loc_a.name, "location_name"))
        self.assertEqual(b["from_location_name"],
                         frappe.db.get_value("AC Location", self.loc_b.name, "location_name"))
        self.assertEqual(a["from_custodian_name"],
                         frappe.db.get_value("User", self.user_a.name, "full_name"))
        self.assertEqual(b["from_custodian_name"],
                         frappe.db.get_value("User", self.user_b.name, "full_name"))
        self.assertNotEqual(a["from_location_name"], b["from_location_name"])
        # batch IN-query: số query/bảng là HẰNG theo số row (KHÔNG per-row)
        from assetcore.api.imm00 import list_transfers
        with _SqlSpy() as spy:
            list_transfers(asset=self.asset.name, page_size=50)
        # from+to cùng bảng = 2 IN-query/bảng, ĐỘC LẬP số phiếu (3 row ở đây)
        self.assertLessEqual(spy.count_table("tabAC Location"), 2)
        self.assertLessEqual(spy.count_table("tabAC Department"), 2)
        self.assertLessEqual(spy.count_table("tabUser"), 2)

    # ── TC-5: pagination.total == len(items) bất biến ────────────────────────
    def test_list_transfers_pagination_total_unchanged(self):
        data = self._list_items()
        self.assertEqual(data["pagination"]["total"], len(data["items"]))
        self.assertEqual(data["pagination"]["total"], 3)

    # ── TC-6: filter transfer_type PHẢI áp dụng (bug: FE gửi transfer_type
    # nhưng signature cũ thiếu param → Frappe get_newargs nuốt câm → filter chết).
    # 3 fixture đều Internal ⇒ lọc 'Loan' phải trả 0; lọc 'Internal' trả đủ 3.
    def test_list_transfers_filter_by_transfer_type(self):
        from assetcore.api.imm00 import list_transfers
        env_loan = list_transfers(asset=self.asset.name, transfer_type="Loan", page_size=50)
        self.assertTrue(env_loan["success"])
        self.assertEqual(env_loan["data"]["pagination"]["total"], 0,
                         "Lọc transfer_type='Loan' phải loại hết 3 phiếu Internal")
        self.assertEqual(len(env_loan["data"]["items"]), 0)
        env_internal = list_transfers(asset=self.asset.name, transfer_type="Internal", page_size=50)
        self.assertEqual(env_internal["data"]["pagination"]["total"], 3,
                         "Lọc transfer_type='Internal' phải trả đủ 3 phiếu")
        for it in env_internal["data"]["items"]:
            self.assertEqual(it["transfer_type"], "Internal")


# ─────────────────────────────────────────────────────────────────────────────
# CR-WF-00-TRANSFER-AUTHZ — server-driven CTA authorization cho Phiếu luân chuyển.
# (1) Gate confirm_receipt bằng rbac.require(commissioning.write) — trước đây THIẾU
#     (mọi user login xác nhận tiếp nhận Approved→Received, kể cả base) trái với
#     approve/reject vốn gate commissioning.submit.
# (2) get_transfer_full emit can_approve/can_receive (int 0/1) dẫn xuất CÙNG SoT
#     (transfer_cta_flags) mà mutating enforce ⇒ FE gate nút = quyền thật (bỏ dead-btn).
# receive_cap = commissioning.write (least-privilege): Commissioning User write=1/
# submit=0 nhận nhưng KHÔNG duyệt; Commissioning Manager có cả hai; base AssetCore
# System User fail-closed cả hai (không có DocPerm Asset Commissioning).
# ADR-IMM00-TRANSFER-AUTHZ. TDD RED-first.
# ─────────────────────────────────────────────────────────────────────────────
class TestTransferReceiveAuthzAndFlags(unittest.TestCase):
    _STATUS_PENDING  = "Pending Approval"
    _STATUS_APPROVED = "Approved"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Máy X-quang (Transfer-Authz test)",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)
        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Chẩn đoán hình ảnh (Authz đích)",
        }).insert(ignore_permissions=True)
        cls.loc = frappe.get_doc({
            "doctype": "AC Location", "location_type": "Room",
            "location_name": "Phòng CĐHA số 2 (Authz đích)",
        }).insert(ignore_permissions=True)
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": "Philips EPIQ 7 (Transfer-Authz)",
            "asset_category": cls.cat.name,
            "department": cls.dept.name,
            "location": cls.loc.name,
            "lifecycle_status": "Commissioned",
        })
        cls._users: list[str] = []
        cls._transfers: list[str] = []
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._transfers:
            if frappe.db.exists("Asset Transfer", name):
                frappe.delete_doc("Asset Transfer", name, force=True, ignore_permissions=True)
        _purge_asset(cls.asset.name)
        for email in cls._users:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        for dt, nm in [("AC Location", cls.loc.name),
                       ("AC Department", cls.dept.name),
                       ("AC Asset Category", cls.cat.name)]:
            if frappe.db.exists(dt, nm):
                frappe.delete_doc(dt, nm, force=True, ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def _mk_user(cls, email: str, roles: list[str]) -> str:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": email,
            "first_name": email.split("@")[0], "send_welcome_email": 0,
            "user_type": "System User",
        }).insert(ignore_permissions=True)
        for r in roles:
            u.append("roles", {"role": r})
        u.flags.ignore_permissions = True
        u.save()
        from assetcore.services.shared import rbac as _rbac
        _rbac.invalidate_capabilities(email)
        cls._users.append(email)
        frappe.db.commit()
        return email

    def _mk_transfer(self, status: str) -> str:
        """Insert 1 Asset Transfer rồi ép status (field read_only/no_copy) qua DB."""
        doc = frappe.get_doc({
            "doctype": "Asset Transfer",
            "asset": self.asset.name,
            "transfer_type": "Internal",
            "transfer_date": nowdate(),
            "to_location": self.loc.name,
            "to_department": self.dept.name,
            "reason": "Điều chuyển phục vụ nhu cầu khoa (authz test)",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("Asset Transfer", doc.name, "status", status)
        frappe.db.commit()
        self._transfers.append(doc.name)
        return doc.name

    # ── TC-1 [RED-first]: base user (thiếu receive-cap) confirm_receipt Approved → 403
    def test_confirm_receipt_requires_capability(self):
        """Base AssetCore System User (không commissioning.write) xác nhận tiếp nhận
        phiếu 'Approved' → frappe.PermissionError (403). Trước fix confirm_receipt
        KHÔNG gate ⇒ THÀNH CÔNG (false-pass) → assertRaises ĐỎ; sau fix rbac.require
        ném PermissionError → XANH. Gate chạy TRƯỚC status-check (mirror approve)."""
        from assetcore.services.imm00 import confirm_receipt
        t = self._mk_transfer(self._STATUS_APPROVED)
        base = self._mk_user("_test_imm00_trf_base_recv@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(base)
            with self.assertRaises(frappe.PermissionError):
                confirm_receipt(t)
        finally:
            frappe.set_user("Administrator")
        # Fail-closed: phiếu KHÔNG bị đổi trạng thái bởi user thiếu quyền.
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "status"),
                         self._STATUS_APPROVED)

    # ── TC-2: user CÓ receive-cap (Commissioning User) → Received + side-effect thật
    def test_confirm_receipt_authorized_succeeds(self):
        """Commissioning User (write=1/submit=0 ⇒ commissioning.write) confirm_receipt
        phiếu 'Approved' → status='Received', received_by=session.user, audit
        event_type='Transfer' + lifecycle 'transferred' emitted (giữ hành vi hiện có).
        Assert SIDE-EFFECT THẬT (LL-TEST-18) — không chỉ return."""
        from assetcore.services.imm00 import confirm_receipt
        t = self._mk_transfer(self._STATUS_APPROVED)
        user = self._mk_user("_test_imm00_trf_recv_ok@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        try:
            frappe.set_user(user)
            out = confirm_receipt(t, handover_notes="Thiết bị nguyên vẹn, đã kiểm tra khởi động")
            self.assertEqual(out["status"], "Received")
            self.assertEqual(out["received_by"], user)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "status"), "Received")
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "received_by"), user)
        self.assertTrue(frappe.db.exists("IMM Audit Trail", {
            "ref_doctype": "Asset Transfer", "ref_name": t, "event_type": "Transfer"}),
            "Thiếu audit event_type='Transfer' cho phiếu tiếp nhận")
        self.assertTrue(frappe.db.exists("Asset Lifecycle Event", {
            "root_record": t, "event_type": "transferred"}),
            "Thiếu lifecycle event 'transferred'")

    # ── TC-3: get_transfer_full emit can_approve/can_receive theo cap × status
    def test_get_transfer_full_emits_capability_flags(self):
        """Commissioning Manager (submit=1 + write=1). Pending → can_approve=1,
        can_receive=0 (status-gate). Approved → can_receive=1, can_approve=0."""
        from assetcore.api.imm00 import get_transfer_full
        t_pending  = self._mk_transfer(self._STATUS_PENDING)
        t_approved = self._mk_transfer(self._STATUS_APPROVED)
        mgr = self._mk_user("_test_imm00_trf_mgr@assetcore.test",
                            ["AssetCore System User", "Commissioning Manager"])
        try:
            frappe.set_user(mgr)
            env_p = get_transfer_full(t_pending)
            self.assertTrue(env_p["success"])
            self.assertEqual(env_p["data"]["can_approve"], 1)
            self.assertEqual(env_p["data"]["can_receive"], 0)
            env_a = get_transfer_full(t_approved)
            self.assertTrue(env_a["success"])
            self.assertEqual(env_a["data"]["can_receive"], 1)
            self.assertEqual(env_a["data"]["can_approve"], 0)
        finally:
            frappe.set_user("Administrator")

    # ── TC-4: base user → can_approve==0 && can_receive==0 ở MỌI status (fail-closed)
    def test_transfer_flags_false_for_base_user(self):
        from assetcore.api.imm00 import get_transfer_full
        statuses = (self._STATUS_PENDING, self._STATUS_APPROVED, "Received", "Rejected")
        transfers = {st: self._mk_transfer(st) for st in statuses}
        base = self._mk_user("_test_imm00_trf_base_flags@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(base)
            for st, t in transfers.items():
                env = get_transfer_full(t)
                self.assertTrue(env["success"])
                self.assertEqual(env["data"]["can_approve"], 0,
                                 f"can_approve phải 0 (fail-closed) ở status {st}")
                self.assertEqual(env["data"]["can_receive"], 0,
                                 f"can_receive phải 0 (fail-closed) ở status {st}")
        finally:
            frappe.set_user("Administrator")

    # ── TC-5 [regression]: approve/reject VẪN require cap (gate hiện có @2665/2696)
    def test_approve_reject_still_require_cap(self):
        from assetcore.services.imm00 import (
            approve_transfer_request, reject_transfer_request,
        )
        t1 = self._mk_transfer(self._STATUS_PENDING)
        t2 = self._mk_transfer(self._STATUS_PENDING)
        base = self._mk_user("_test_imm00_trf_base_apprej@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(base)
            with self.assertRaises(frappe.PermissionError):
                approve_transfer_request(t1)
            with self.assertRaises(frappe.PermissionError):
                reject_transfer_request(t2, "Lý do từ chối hợp lệ cho kiểm thử")
        finally:
            frappe.set_user("Administrator")

    # ── TC-6 [RED-first LOCK — QUA mobile handler]: CR-WF-00-TRANSFER-AUTHZ contract-sync.
    #    Base AssetCore System User (thiếu commissioning.write) gọi API HANDLER
    #    `api.imm00.receive_transfer` (KHÔNG service confirm_receipt trực tiếp như TC-1) trên phiếu
    #    'Approved' → frappe.PermissionError PROPAGATE NGUYÊN qua handler → HTTP-403 status-line THẬT
    #    (cap-403 REACHABLE). Handler CHỈ `except frappe.exceptions.ValidationError` @api/imm00.py:2645-2648
    #    ⇒ PermissionError của rbac.require(commissioning.write) @services/imm00.py:2768 KHÔNG bị
    #    nuốt/convert thành `_err(str(e), 422)` (200-Error). assertRaises PermissionError = bằng chứng
    #    propagate: nếu handler trả `_err(..,422)` thay vì raise ⇒ KHÔNG có exception ⇒ test ĐỎ.
    #    GUARD chống drift: ai đó nới `except Exception`/`except PermissionError → _err(422)` ⇒ RED.
    #    (RED-first gốc: trước CR-WF-00-TRANSFER-AUTHZ confirm_receipt KHÔNG gate ⇒ handler trả _ok ⇒ ĐỎ.)
    def test_receive_transfer_mobile_propagates_cap_403(self):
        from assetcore.api.imm00 import receive_transfer
        t = self._mk_transfer(self._STATUS_APPROVED)
        base = self._mk_user("_test_imm00_trf_mob_base@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(base)
            with self.assertRaises(frappe.PermissionError):
                receive_transfer(t)
        finally:
            frappe.set_user("Administrator")
        # Fail-closed: handler KHÔNG rơi vào _ok path ⇒ trạng thái phiếu KHÔNG đổi.
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "status"),
                         self._STATUS_APPROVED)

    # ── TC-7 [happy-path — QUA mobile handler]: Commissioning User (write=1/submit=0 ⇒ CÓ
    #    commissioning.write) gọi HANDLER `api.imm00.receive_transfer` phiếu 'Approved' → `_ok`
    #    envelope {success:True, data:{name,status='Received',received_by}} (cap-đủ VẪN đi qua
    #    handler bình thường, KHÔNG bị gate chặn nhầm). Chứng minh gate least-privilege
    #    commissioning.write đúng cho bên nhận (KHÔNG cần commissioning.submit).
    def test_receive_transfer_mobile_authorized_returns_ok_envelope(self):
        from assetcore.api.imm00 import receive_transfer
        t = self._mk_transfer(self._STATUS_APPROVED)
        user = self._mk_user("_test_imm00_trf_mob_ok@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        try:
            frappe.set_user(user)
            env = receive_transfer(t, handover_notes="Bàn giao đủ phụ kiện, khởi động OK")
        finally:
            frappe.set_user("Administrator")
        self.assertIs(env["success"], True)
        self.assertEqual(set(env["data"].keys()), {"name", "status", "received_by"},
                         "Envelope data PHẢI EXACT 3-key {name,status,received_by} (services/imm00.py:2708).")
        self.assertEqual(env["data"]["name"], t)
        self.assertEqual(env["data"]["status"], "Received")
        self.assertEqual(env["data"]["received_by"], user)
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "status"), "Received")


# ─────────────────────────────────────────────────────────────────────────────
# CR-WF-00-CANCEL-AUTHZ (ADR-IMM00-CANCEL-AUTHZ) — Vòng 41. Đóng backlog cancel-authz
# tách khỏi TRANSFER-AUTHZ. Trước fix `cancel_transfer_request`:
#   (1) THIẾU rbac.require → mọi user login (kể cả base) hủy được phiếu Pending/Rejected.
#   (2) THIẾU log_audit_event → hủy KHÔNG để lại dấu vết (vi phạm CLAUDE.md §5 + NĐ98).
# cancel_cap = commissioning.write (parity confirm_receipt, least-privilege): Commissioning
# User write=1 hủy được; base AssetCore System User fail-closed. Gate SAU exists TRƯỚC
# status-check (mirror EXACT confirm_receipt) — base hủy phiếu sai status vẫn 403, không
# rò trạng thái. get_transfer_full emit thêm can_cancel (int 0/1). TDD RED-first.
# ─────────────────────────────────────────────────────────────────────────────
class TestTransferCancelAuthzAndAudit(unittest.TestCase):
    _STATUS_PENDING   = "Pending Approval"
    _STATUS_APPROVED  = "Approved"
    _STATUS_REJECTED  = "Rejected"
    _STATUS_RECEIVED  = "Received"
    _STATUS_CANCELLED = "Cancelled"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Máy siêu âm (Cancel-Authz test)",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)
        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Sản (Cancel-Authz đích)",
        }).insert(ignore_permissions=True)
        cls.loc = frappe.get_doc({
            "doctype": "AC Location", "location_type": "Room",
            "location_name": "Phòng Siêu âm số 1 (Cancel-Authz)",
        }).insert(ignore_permissions=True)
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": "GE Voluson E10 (Cancel-Authz)",
            "asset_category": cls.cat.name,
            "department": cls.dept.name,
            "location": cls.loc.name,
            "lifecycle_status": "Commissioned",
        })
        cls._users: list[str] = []
        cls._transfers: list[str] = []
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._transfers:
            if frappe.db.exists("Asset Transfer", name):
                frappe.delete_doc("Asset Transfer", name, force=True, ignore_permissions=True)
        _purge_asset(cls.asset.name)
        for email in cls._users:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        for dt, nm in [("AC Location", cls.loc.name),
                       ("AC Department", cls.dept.name),
                       ("AC Asset Category", cls.cat.name)]:
            if frappe.db.exists(dt, nm):
                frappe.delete_doc(dt, nm, force=True, ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def _mk_user(cls, email: str, roles: list[str]) -> str:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": email,
            "first_name": email.split("@")[0], "send_welcome_email": 0,
            "user_type": "System User",
        }).insert(ignore_permissions=True)
        for r in roles:
            u.append("roles", {"role": r})
        u.flags.ignore_permissions = True
        u.save()
        from assetcore.services.shared import rbac as _rbac
        _rbac.invalidate_capabilities(email)
        cls._users.append(email)
        frappe.db.commit()
        return email

    def _mk_transfer(self, status: str) -> str:
        """Insert 1 Asset Transfer (Draft) rồi ép status qua DB (read_only/no_copy).

        Bypass ``create_transfer_request`` ⇒ KHÔNG sinh audit 'Yêu cầu luân chuyển'
        ⇒ số audit-row của phiếu = 0 trước khi hủy (RED-first can đo được 0→1)."""
        doc = frappe.get_doc({
            "doctype": "Asset Transfer",
            "asset": self.asset.name,
            "transfer_type": "Internal",
            "transfer_date": nowdate(),
            "to_location": self.loc.name,
            "to_department": self.dept.name,
            "reason": "Điều chuyển phục vụ nhu cầu khoa (cancel-authz test)",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("Asset Transfer", doc.name, "status", status)
        frappe.db.commit()
        self._transfers.append(doc.name)
        return doc.name

    def _count_transfer_audit(self, name: str) -> int:
        return frappe.db.count("IMM Audit Trail", {
            "ref_doctype": "Asset Transfer", "ref_name": name, "event_type": "Transfer"})

    # ── TC-1 [RED-first]: base user (thiếu cancel-cap) hủy Pending → 403, status giữ nguyên
    def test_cancel_requires_capability(self):
        """Base AssetCore System User (không commissioning.write) hủy phiếu 'Pending
        Approval' → frappe.PermissionError. Trước fix cancel KHÔNG gate ⇒ THÀNH CÔNG
        (status→Cancelled, false-pass) → assertRaises ĐỎ; sau fix rbac.require ném
        PermissionError → XANH. Fail-closed: phiếu KHÔNG bị đổi trạng thái."""
        from assetcore.services.imm00 import cancel_transfer_request
        t = self._mk_transfer(self._STATUS_PENDING)
        base = self._mk_user("_test_imm00_trf_cancel_base@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(base)
            with self.assertRaises(frappe.PermissionError):
                cancel_transfer_request(t)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "status"),
                         self._STATUS_PENDING)

    # ── TC-2: user CÓ cancel-cap (Commissioning User) hủy Pending & Rejected → Cancelled
    def test_cancel_authorized_succeeds(self):
        """Commissioning User (write=1) hủy phiếu 'Pending Approval' → {status:'Cancelled'};
        và hủy phiếu 'Rejected' → {status:'Cancelled'}. Assert side-effect thật (DB)."""
        from assetcore.services.imm00 import cancel_transfer_request
        t_pending  = self._mk_transfer(self._STATUS_PENDING)
        t_rejected = self._mk_transfer(self._STATUS_REJECTED)
        user = self._mk_user("_test_imm00_trf_cancel_ok@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        try:
            frappe.set_user(user)
            out_p = cancel_transfer_request(t_pending)
            self.assertEqual(out_p, {"name": t_pending, "status": self._STATUS_CANCELLED})
            out_r = cancel_transfer_request(t_rejected)
            self.assertEqual(out_r, {"name": t_rejected, "status": self._STATUS_CANCELLED})
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value("Asset Transfer", t_pending, "status"),
                         self._STATUS_CANCELLED)
        self.assertEqual(frappe.db.get_value("Asset Transfer", t_rejected, "status"),
                         self._STATUS_CANCELLED)

    # ── TC-3 [RED-first 0→1]: mỗi lần hủy sinh ĐÚNG 1 audit Transfer (change_summary 'Hủy')
    def test_cancel_writes_one_audit_row(self):
        """Sau hủy: đúng 1 IMM Audit Trail (event_type='Transfer', change_summary chứa
        'Hủy'). Trước fix cancel KHÔNG log_audit_event ⇒ 0 dòng → assertEqual(...,1) ĐỎ."""
        from assetcore.services.imm00 import cancel_transfer_request
        t = self._mk_transfer(self._STATUS_PENDING)
        self.assertEqual(self._count_transfer_audit(t), 0)  # RED baseline: chưa có audit
        user = self._mk_user("_test_imm00_trf_cancel_audit@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        try:
            frappe.set_user(user)
            cancel_transfer_request(t)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(self._count_transfer_audit(t), 1,
                         "Hủy phiếu phải sinh ĐÚNG 1 audit Transfer")
        summary = frappe.db.get_value("IMM Audit Trail", {
            "ref_doctype": "Asset Transfer", "ref_name": t, "event_type": "Transfer"},
            "change_summary") or ""
        self.assertIn("Hủy", summary)

    # ── TC-4: gate ordering — existence TRƯỚC rbac; rbac TRƯỚC status (không rò trạng thái)
    def test_cancel_gate_ordering(self):
        """(a) base user hủy phiếu KHÔNG tồn tại → raise chứa 'không tồn tại' (existence
        -check chạy TRƯỚC rbac). (b) base user hủy phiếu 'Approved' (SAI status) →
        PermissionError (rbac chạy TRƯỚC status-check) — KHÔNG leak 'trạng thái'."""
        from assetcore.services.imm00 import cancel_transfer_request
        t_approved = self._mk_transfer(self._STATUS_APPROVED)
        base = self._mk_user("_test_imm00_trf_cancel_order@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(base)
            # (a) existence-check trước rbac → not-found, KHÔNG PermissionError
            with self.assertRaises(frappe.exceptions.ValidationError) as ctx:
                cancel_transfer_request("AT-DOES-NOT-EXIST-99999")
            self.assertNotIsInstance(ctx.exception, frappe.PermissionError)
            self.assertIn("không tồn tại", str(ctx.exception))
            # (b) rbac trước status-check → PermissionError (không rò 'trạng thái')
            with self.assertRaises(frappe.PermissionError) as ctx2:
                cancel_transfer_request(t_approved)
            self.assertNotIn("trạng thái", str(ctx2.exception))
        finally:
            frappe.set_user("Administrator")
        # Fail-closed: phiếu Approved KHÔNG bị đổi trạng thái.
        self.assertEqual(frappe.db.get_value("Asset Transfer", t_approved, "status"),
                         self._STATUS_APPROVED)

    # ── TC-5: transfer_cta_flags(status) → can_cancel matrix (cap × status)
    def test_transfer_cta_flags_can_cancel_matrix(self):
        """cap + Pending→1, cap + Rejected→1, cap + Approved→0, cap + Received→0;
        base user (no cap) → 0 ở MỌI status (fail-closed)."""
        from assetcore.services.imm00 import transfer_cta_flags
        user = self._mk_user("_test_imm00_trf_flags_cancel@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        base = self._mk_user("_test_imm00_trf_flags_cancel_base@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(user)
            self.assertEqual(transfer_cta_flags(self._STATUS_PENDING)["can_cancel"], 1)
            self.assertEqual(transfer_cta_flags(self._STATUS_REJECTED)["can_cancel"], 1)
            self.assertEqual(transfer_cta_flags(self._STATUS_APPROVED)["can_cancel"], 0)
            self.assertEqual(transfer_cta_flags(self._STATUS_RECEIVED)["can_cancel"], 0)
            frappe.set_user(base)
            for st in (self._STATUS_PENDING, self._STATUS_REJECTED,
                       self._STATUS_APPROVED, self._STATUS_RECEIVED):
                self.assertEqual(transfer_cta_flags(st)["can_cancel"], 0,
                                 f"base user phải can_cancel=0 ở status {st}")
        finally:
            frappe.set_user("Administrator")

    # ── TC-6: get_transfer_full echo can_cancel khớp transfer_cta_flags(status)
    def test_get_transfer_full_emits_can_cancel(self):
        """get_transfer_full response chứa key 'can_cancel' và khớp
        transfer_cta_flags(status). Base user (no cap) → 0 ở mọi status."""
        from assetcore.api.imm00 import get_transfer_full
        from assetcore.services.imm00 import transfer_cta_flags
        t_pending  = self._mk_transfer(self._STATUS_PENDING)
        t_rejected = self._mk_transfer(self._STATUS_REJECTED)
        user = self._mk_user("_test_imm00_trf_full_cancel@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        base = self._mk_user("_test_imm00_trf_full_cancel_base@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(user)
            env_p = get_transfer_full(t_pending)
            self.assertTrue(env_p["success"])
            self.assertIn("can_cancel", env_p["data"])
            self.assertEqual(env_p["data"]["can_cancel"],
                             transfer_cta_flags(self._STATUS_PENDING)["can_cancel"])
            self.assertEqual(env_p["data"]["can_cancel"], 1)
            env_r = get_transfer_full(t_rejected)
            self.assertEqual(env_r["data"]["can_cancel"], 1)
            frappe.set_user(base)
            env_pb = get_transfer_full(t_pending)
            self.assertEqual(env_pb["data"]["can_cancel"], 0)
        finally:
            frappe.set_user("Administrator")


# ─────────────────────────────────────────────────────────────────────────────
# CR-WF-00-EDIT-AUTHZ (ADR-IMM00-EDIT-AUTHZ) — Vòng 42. Đóng nốt bộ-tứ transfer-authz
# (approve/receive/cancel/EDIT). Trước fix `api.imm00.update_transfer`:
#   THIẾU rbac.require → mọi user login (kể cả Inventory User có inventory.read/write
#   nhưng KHÔNG commissioning.write) sửa được đích/khoa/người nhận/ngày/lý do/ghi chú
#   của phiếu 'Pending Approval' (missing-authorization write = custody-hole).
#   `_generic_update` dùng doc.save(ignore_permissions=True) ⇒ không có hàng rào quyền
#   nào ⇒ handler trả _ok/200 (false-pass).
# edit_cap = commissioning.write (parity _TRANSFER_RECEIVE_CAP/_TRANSFER_CANCEL_CAP,
# least-privilege): Commissioning User (write=1/submit=0) sửa được; Inventory User → 403
# fail-closed. Ordering chốt bởi BA: tồn tại (404) → rbac.require (403) → status Pending
# (422). update_transfer KHÔNG try/except ⇒ PermissionError propagate tự nhiên → HTTP-403;
# status-gate 422 GIỮ NGUYÊN (KHÔNG bị rbac che thành 403). get_transfer_full emit thêm
# can_edit (int 0/1) — SoT parity với transfer_cta_flags. TDD RED-first.
# ─────────────────────────────────────────────────────────────────────────────
class TestTransferEditAuthzAndFlags(unittest.TestCase):
    _STATUS_PENDING   = "Pending Approval"
    _STATUS_APPROVED  = "Approved"
    _STATUS_REJECTED  = "Rejected"
    _STATUS_RECEIVED  = "Received"
    _STATUS_CANCELLED = "Cancelled"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Máy nội soi (Edit-Authz test)",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)
        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "Khoa Nội soi (Edit-Authz đích)",
        }).insert(ignore_permissions=True)
        cls.loc = frappe.get_doc({
            "doctype": "AC Location", "location_type": "Room",
            "location_name": "Phòng Nội soi số 1 (Edit-Authz)",
        }).insert(ignore_permissions=True)
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": "Olympus CV-190 (Edit-Authz)",
            "asset_category": cls.cat.name,
            "department": cls.dept.name,
            "location": cls.loc.name,
            "lifecycle_status": "Commissioned",
        })
        cls._users: list[str] = []
        cls._transfers: list[str] = []
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._transfers:
            if frappe.db.exists("Asset Transfer", name):
                frappe.delete_doc("Asset Transfer", name, force=True, ignore_permissions=True)
        _purge_asset(cls.asset.name)
        for email in cls._users:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        for dt, nm in [("AC Location", cls.loc.name),
                       ("AC Department", cls.dept.name),
                       ("AC Asset Category", cls.cat.name)]:
            if frappe.db.exists(dt, nm):
                frappe.delete_doc(dt, nm, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        # update_transfer đọc frappe.local.form_dict → lưu/khôi phục để không rò rỉ
        # payload sang test khác chạy trong cùng process.
        self._saved_form_dict = getattr(frappe.local, "form_dict", None)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.local.form_dict = self._saved_form_dict or frappe._dict()

    @classmethod
    def _mk_user(cls, email: str, roles: list[str]) -> str:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": email,
            "first_name": email.split("@")[0], "send_welcome_email": 0,
            "user_type": "System User",
        }).insert(ignore_permissions=True)
        for r in roles:
            u.append("roles", {"role": r})
        u.flags.ignore_permissions = True
        u.save()
        from assetcore.services.shared import rbac as _rbac
        _rbac.invalidate_capabilities(email)
        cls._users.append(email)
        frappe.db.commit()
        return email

    def _mk_transfer(self, status: str, reason: str | None = None) -> str:
        """Insert 1 Asset Transfer rồi ép status (field read_only/no_copy) qua DB."""
        doc = frappe.get_doc({
            "doctype": "Asset Transfer",
            "asset": self.asset.name,
            "transfer_type": "Internal",
            "transfer_date": nowdate(),
            "to_location": self.loc.name,
            "to_department": self.dept.name,
            "reason": reason or "Điều chuyển phục vụ nhu cầu khoa (edit-authz test)",
        })
        doc.insert(ignore_permissions=True)
        frappe.db.set_value("Asset Transfer", doc.name, "status", status)
        frappe.db.commit()
        self._transfers.append(doc.name)
        return doc.name

    # ── TC-1 [RED-first]: Inventory User (inventory.read/write, KHÔNG commissioning.write)
    #    gọi HANDLER api.imm00.update_transfer trên phiếu Pending → frappe.PermissionError.
    #    Trước fix update_transfer KHÔNG gate ⇒ _generic_update(ignore_permissions) trả
    #    _ok/200 (custody-hole, false-pass) → assertRaises ĐỎ; sau fix rbac.require ném
    #    PermissionError → XANH. Gọi ENDPOINT (không service) để lock contract HTTP-403.
    def test_update_transfer_denied_for_non_commissioning_user(self):
        from assetcore.api.imm00 import update_transfer
        t = self._mk_transfer(self._STATUS_PENDING, reason="Lý do gốc trước khi thử sửa")
        inv = self._mk_user("_test_imm00_trf_edit_inv@assetcore.test",
                            ["AssetCore System User", "Inventory User"])
        try:
            frappe.set_user(inv)
            frappe.local.form_dict = frappe._dict({
                "reason": "KTV kho cố sửa lý do (không được phép)",
            })
            with self.assertRaises(frappe.PermissionError):
                update_transfer(t)
        finally:
            frappe.set_user("Administrator")
        # Fail-closed: phiếu KHÔNG bị đổi bởi user thiếu quyền.
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "reason"),
                         "Lý do gốc trước khi thử sửa")

    # ── TC-2: Commissioning User (write=1/submit=0) update phiếu Pending → success,
    #    re-fetch xác nhận field THẬT được cập nhật (side-effect thật, LL-TEST-18).
    def test_update_transfer_authorized_succeeds(self):
        from assetcore.api.imm00 import update_transfer
        t = self._mk_transfer(self._STATUS_PENDING, reason="Lý do ban đầu (authorized)")
        user = self._mk_user("_test_imm00_trf_edit_ok@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        new_reason = "Điều chỉnh: chuyển sang khoa Nội soi theo yêu cầu mới"
        try:
            frappe.set_user(user)
            frappe.local.form_dict = frappe._dict({"reason": new_reason})
            env = update_transfer(t)
        finally:
            frappe.set_user("Administrator")
        self.assertIs(env["success"], True, f"update_transfer phải success: {env}")
        self.assertEqual(env["data"]["name"], t)
        # Re-fetch xác nhận field THẬT đổi trong DB.
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "reason"), new_reason)

    # ── TC-3: status-gate 422 GIỮ NGUYÊN — Commissioning User update phiếu Approved →
    #    _err 422 (KHÔNG bị rbac che thành 403). Phân định 403(quyền) vs 422(trạng thái):
    #    user CÓ cap ⇒ rbac.require pass ⇒ đến status-check ⇒ envelope http_status=422.
    def test_update_transfer_status_gate_preserved(self):
        from assetcore.api.imm00 import update_transfer
        user = self._mk_user("_test_imm00_trf_edit_gate@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        try:
            frappe.set_user(user)
            for st in (self._STATUS_APPROVED, self._STATUS_RECEIVED, self._STATUS_CANCELLED):
                t = self._mk_transfer(st, reason=f"Không được sửa ở status {st}")
                frappe.local.form_dict = frappe._dict({"reason": "cố sửa sai trạng thái"})
                env = update_transfer(t)
                self.assertIs(env["success"], False,
                              f"update phiếu {st} phải fail (status-gate)")
                self.assertEqual(env["http_status"], 422,
                                 f"phiếu {st} phải 422 (status-gate), KHÔNG 403: {env}")
                # Fail-closed: reason KHÔNG bị đổi.
                self.assertEqual(frappe.db.get_value("Asset Transfer", t, "reason"),
                                 f"Không được sửa ở status {st}")
        finally:
            frappe.set_user("Administrator")

    # ── TC-4: transfer_cta_flags(status) → can_edit matrix (cap × status)
    def test_transfer_cta_flags_can_edit_matrix(self):
        """cap + Pending→1; cap + Approved/Received/Rejected→0 (status-gate);
        base/Inventory user (no commissioning.write) → 0 ở MỌI status (fail-closed)."""
        from assetcore.services.imm00 import transfer_cta_flags
        user = self._mk_user("_test_imm00_trf_flags_edit@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        inv = self._mk_user("_test_imm00_trf_flags_edit_inv@assetcore.test",
                            ["AssetCore System User", "Inventory User"])
        try:
            frappe.set_user(user)
            self.assertEqual(transfer_cta_flags(self._STATUS_PENDING)["can_edit"], 1)
            self.assertEqual(transfer_cta_flags(self._STATUS_APPROVED)["can_edit"], 0)
            self.assertEqual(transfer_cta_flags(self._STATUS_RECEIVED)["can_edit"], 0)
            self.assertEqual(transfer_cta_flags(self._STATUS_REJECTED)["can_edit"], 0)
            frappe.set_user(inv)
            for st in (self._STATUS_PENDING, self._STATUS_APPROVED,
                       self._STATUS_RECEIVED, self._STATUS_REJECTED):
                self.assertEqual(transfer_cta_flags(st)["can_edit"], 0,
                                 f"non-commissioning user phải can_edit=0 ở status {st}")
        finally:
            frappe.set_user("Administrator")

    # ── TC-5: get_transfer_full echo can_edit khớp transfer_cta_flags(status)
    def test_get_transfer_full_emits_can_edit(self):
        """get_transfer_full response.data chứa key 'can_edit' đúng theo cap × status
        (parity can_approve/can_receive/can_cancel). Pending+cap→1; Approved+cap→0;
        base user → 0 ở mọi status."""
        from assetcore.api.imm00 import get_transfer_full
        from assetcore.services.imm00 import transfer_cta_flags
        t_pending  = self._mk_transfer(self._STATUS_PENDING)
        t_approved = self._mk_transfer(self._STATUS_APPROVED)
        user = self._mk_user("_test_imm00_trf_full_edit@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        base = self._mk_user("_test_imm00_trf_full_edit_base@assetcore.test",
                             ["AssetCore System User"])
        try:
            frappe.set_user(user)
            env_p = get_transfer_full(t_pending)
            self.assertTrue(env_p["success"])
            self.assertIn("can_edit", env_p["data"])
            self.assertEqual(env_p["data"]["can_edit"],
                             transfer_cta_flags(self._STATUS_PENDING)["can_edit"])
            self.assertEqual(env_p["data"]["can_edit"], 1)
            env_a = get_transfer_full(t_approved)
            self.assertEqual(env_a["data"]["can_edit"], 0)  # status-gate
            frappe.set_user(base)
            env_pb = get_transfer_full(t_pending)
            self.assertEqual(env_pb["data"]["can_edit"], 0)  # fail-closed
        finally:
            frappe.set_user("Administrator")

    # ── TC-6 [INVARIANT]: can_edit=1 cho session ⇒ update_transfer KHÔNG raise
    #    PermissionError cùng session (button-affordance ⇔ action parity, mirror
    #    parity đã có cho can_cancel/can_receive).
    def test_can_edit_implies_update_permitted(self):
        from assetcore.api.imm00 import update_transfer
        from assetcore.services.imm00 import transfer_cta_flags
        t = self._mk_transfer(self._STATUS_PENDING, reason="Trạng thái đầu (invariant)")
        user = self._mk_user("_test_imm00_trf_edit_inv_parity@assetcore.test",
                             ["AssetCore System User", "Commissioning User"])
        try:
            frappe.set_user(user)
            # Tiền đề: cờ can_edit=1 cho phiếu Pending dưới session này.
            self.assertEqual(transfer_cta_flags(self._STATUS_PENDING)["can_edit"], 1)
            frappe.local.form_dict = frappe._dict({"reason": "Sửa hợp lệ theo cờ can_edit"})
            try:
                env = update_transfer(t)
            except frappe.PermissionError:
                self.fail("can_edit=1 nhưng update_transfer raise PermissionError "
                          "(vi phạm button-affordance ⇔ action parity)")
        finally:
            frappe.set_user("Administrator")
        self.assertIs(env["success"], True)
        self.assertEqual(frappe.db.get_value("Asset Transfer", t, "reason"),
                         "Sửa hợp lệ theo cờ can_edit")


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
        # Base role `AssetCore System User` là invariant bắt buộc — luôn có mặt
        # bên cạnh các role payload (không gỡ qua UI). Xem _ensure_base_role.
        self.assertEqual(
            self._db_roles(),
            ["AssetCore System User", "Compliance Manager", "PM Manager"],
        )

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
        # Base role `AssetCore System User` luôn được giữ (invariant) cùng 3 role seed.
        self.assertEqual(
            self._db_roles(),
            ["AssetCore System User", "Document Manager", "Inventory Manager", "PM User"],
        )

        # Replace: chỉ giữ 1 domain role — các role cũ bị xóa, nhưng base role giữ nguyên.
        frappe.local.form_dict = frappe._dict({
            "user": self.TEST_EMAIL,
            "imm_roles": json.dumps([{"role": "Corrective User"}]),
        })
        update_user_info()
        frappe.db.commit()
        self.assertEqual(self._db_roles(), ["AssetCore System User", "Corrective User"])

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
        # 0 kỳ Pending → decommission KHÔNG sinh event thừa.
        # L-07: asset cấu hình nay tự sinh lịch ở after_insert ⇒ xoá schedule vừa
        # sinh để dựng đúng trạng thái "không còn kỳ Pending" (mô phỏng asset đã
        # khấu hao hết / lịch đã đóng) trước khi decommission.
        asset = self._make_asset("tc04b")
        frappe.db.delete(_DEC_DT_SCHED, {"parent": asset, "parenttype": "AC Asset"})
        frappe.db.commit()
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
# BE-D4 (ADR-IMM00-QR-SCAN-ACTION §D4) — QR-gen COVERAGE proof across MỌI đường
# tạo asset + read-only baseline + idempotent backfill reproof.
#
# 🎯 "QR sinh ở đâu?" — 1 NGUỒN DUY NHẤT: model-layer
#     ``ac_asset.py::before_insert`` → ``_ensure_qr_token`` (ac_asset.py:50,63,65).
#   Mọi đường tạo asset gọi ``doc.insert()`` ⇒ Frappe lifecycle fire before_insert
#   ⇒ token tự sinh. KHÔNG có code QR riêng cho form / import / registration.
#     (1) form   : api/imm00.py::create_asset → frappe.get_doc(...).insert()
#     (2) import : api/import_data.py:348-350 new_doc().update().insert()
#                  (đường import e2e: test_import_asset_identity.TestQrGenCoverageImport)
#     (3) regist.: services/imm04.py::create_ac_asset → asset.insert() (:598)
#                  + belt-and-suspenders ensure_asset_qr_token (imm04.py:1010-1011)
#
# RED-guard: nếu before_insert/_ensure_qr_token bị gỡ (patch no-op) → cả 3 đường
# ra token rỗng → root-cause neo vào model hook (KHÔNG rải logic QR ở từng caller).
# ──────────────────────────────────────────────────────────────────────────


class TestQrGenCoverageD4(unittest.TestCase):
    """BE-D4: chứng minh qr_token != rỗng SAU mỗi đường tạo + baseline + backfill."""

    _URLSAFE = re.compile(r"^[A-Za-z0-9_-]+$")

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Danh mục test QR coverage D4",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_category("Danh mục test QR coverage D4")
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._tok = frappe.generate_hash(length=6).upper()
        self._saved_form_dict = getattr(frappe.local, "form_dict", None)

    def tearDown(self):
        frappe.local.form_dict = self._saved_form_dict or frappe._dict()

    # ── (1) FORM path — qua endpoint create_asset thật ──────────────────────
    def test_qr_token_generated_on_form_create(self):
        """create_asset (đường HTTP form) → asset.qr_token != rỗng.

        Bổ sung so với test_qr_token_generated_on_insert (dùng
        _insert_asset_bypass_workflow): test này đi qua ENDPOINT create_asset —
        đúng path FE gọi.
        """
        from assetcore.api.imm00 import create_asset

        code = f"TS-QRFORM-{self._tok}"
        frappe.local.form_dict = frappe._dict({
            "cmd": "assetcore.api.imm00.create_asset",
            "asset_name": f"Máy QR form {self._tok}",
            "asset_category": self.cat.name,
            "asset_code": code,
        })
        resp = create_asset()
        self.assertTrue(resp.get("success"), f"create_asset phải OK: {resp}")
        name = resp["data"]["name"]
        self.addCleanup(_purge_asset, name)

        token = frappe.db.get_value("AC Asset", name, "qr_token")
        self.assertTrue(token, "qr_token != rỗng sau form-create endpoint")
        self.assertGreaterEqual(len(token), 20)
        self.assertRegex(token, self._URLSAFE)

    # ── (3) REGISTRATION path — create_ac_asset (commissioning) ─────────────
    def test_qr_token_generated_on_registration(self):
        """IMM-04/05 commissioning tạo final_asset qua create_ac_asset →
        final_asset.qr_token != rỗng (assert tại điểm tạo doctype .insert()).

        Đây là đường registration THẬT: services/imm04.py::create_ac_asset gọi
        ``asset.insert()`` (:598) ⇒ before_insert sinh token.
        """
        from assetcore.services.imm04 import create_ac_asset

        # Insert ở Draft để skip Gate G01 (commissioning docs) — create_ac_asset
        # CHỈ đọc field của doc (asset_description/vendor_serial_no/final_asset),
        # KHÔNG re-validate workflow_state của phiếu → đường mint asset đúng.
        comm = frappe.get_doc({
            "doctype": "Asset Commissioning",
            "workflow_state": "Draft",
            "asset_description": f"Máy thở Dräger Evita V500 (reg {self._tok})",
            "vendor_serial_no": f"SN-REG-{self._tok}",
        }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        self.addCleanup(
            lambda: frappe.db.exists("Asset Commissioning", comm.name)
            and frappe.delete_doc("Asset Commissioning", comm.name,
                                  force=True, ignore_permissions=True))
        frappe.db.commit()

        asset_name = create_ac_asset(comm)
        self.addCleanup(_purge_asset, asset_name)
        self.assertTrue(asset_name, "create_ac_asset phải mint AC Asset")

        token = frappe.db.get_value("AC Asset", asset_name, "qr_token")
        self.assertTrue(token,
                        "final_asset.qr_token != rỗng sau registration "
                        "(before_insert qua asset.insert())")
        self.assertGreaterEqual(len(token), 20)
        self.assertRegex(token, self._URLSAFE)

    # ── RED-guard — before_insert là NGUỒN DUY NHẤT ─────────────────────────
    def test_qr_token_before_insert_is_sole_source(self):
        """Nếu _ensure_qr_token bị no-op (gỡ hook) → form + import đều ra token
        rỗng ⇒ chứng minh root-cause neo vào model hook, KHÔNG có code QR riêng
        ở caller. (Patch _ensure_qr_token thành no-op, assert insert ra token rỗng.)
        """
        from unittest.mock import patch as _mock_patch
        from assetcore.assetcore.doctype.ac_asset.ac_asset import ACAsset

        # FORM path với hook bị gỡ → token rỗng
        with _mock_patch.object(ACAsset, "_ensure_qr_token", lambda self: None):
            doc = _insert_asset_bypass_workflow({
                "doctype": "AC Asset",
                "asset_name": f"Máy no-hook form {self._tok}",
                "asset_category": self.cat.name,
                "asset_code": f"TS-NOHOOK-FORM-{self._tok}",
                "lifecycle_status": "Draft",
            })
            self.addCleanup(_purge_asset, doc.name)
            self.assertFalse(
                frappe.db.get_value("AC Asset", doc.name, "qr_token"),
                "gỡ _ensure_qr_token → form-create KHÔNG còn sinh token "
                "(token KHÔNG sinh ở caller — sole source là before_insert)")

        # IMPORT path (new_doc().update().insert()) với hook bị gỡ → token rỗng
        with _mock_patch.object(ACAsset, "_ensure_qr_token", lambda self: None):
            d2 = frappe.new_doc("AC Asset")
            d2.update({
                "asset_name": f"Máy no-hook import {self._tok}",
                "asset_category": self.cat.name,
                "asset_code": f"TS-NOHOOK-IMP-{self._tok}",
                "lifecycle_status": "Draft",
            })
            d2.insert(ignore_permissions=True)
            self.addCleanup(_purge_asset, d2.name)
            self.assertFalse(
                frappe.db.get_value("AC Asset", d2.name, "qr_token"),
                "gỡ _ensure_qr_token → import-insert KHÔNG còn sinh token")

        # Sanity: KHÔNG patch → token sinh lại bình thường (hook là nguồn DUY NHẤT)
        d3 = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy có-hook {self._tok}",
            "asset_category": self.cat.name,
            "asset_code": f"TS-HOOK-OK-{self._tok}",
            "lifecycle_status": "Draft",
        })
        self.addCleanup(_purge_asset, d3.name)
        self.assertTrue(
            frappe.db.get_value("AC Asset", d3.name, "qr_token"),
            "không patch → before_insert sinh token (sole source hoạt động)")

    # ── BE-D4-b — read-only baseline count (KHÔNG mutate) ───────────────────
    def test_backfill_baseline_count_readonly(self):
        """COUNT(*) AC Asset WHERE qr_token IN ('', NULL) đo được + KHÔNG mutate:
        count trước == count sau khi chỉ-đọc.
        """
        def _missing_count() -> int:
            return frappe.db.count("AC Asset", {"qr_token": ["in", ["", None]]})

        before = _missing_count()
        # Chỉ đọc lại — KHÔNG ghi gì. Phải bằng nhau (đo không có side-effect).
        after = _missing_count()
        self.assertEqual(before, after,
                         "đo baseline phải read-only — count không đổi")
        self.assertGreaterEqual(before, 0)

    # ── BE-D4-c reproof — backfill idempotent 2 lần + KHÔNG emit lần 2 ──────
    def test_backfill_idempotent_twice(self):
        """Asset legacy giả-lập token rỗng → ensure_asset_qr_token lần 1 sinh
        token, lần 2 trả CÙNG token, qr_generated event KHÔNG tăng lần 2.
        """
        from assetcore.services.imm00 import ensure_asset_qr_token

        asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy legacy {self._tok}",
            "asset_category": self.cat.name,
            "asset_code": f"TS-LEGACY-{self._tok}",
            "lifecycle_status": "Draft",
        })
        self.addCleanup(_purge_asset, asset.name)
        # Giả legacy: xoá token (raw SQL — không qua validate/before hooks)
        frappe.db.sql("UPDATE `tabAC Asset` SET qr_token=NULL WHERE name=%s",
                      (asset.name,))
        frappe.db.commit()

        t1 = ensure_asset_qr_token(asset.name)
        self.assertTrue(t1, "lần 1: sinh token cho asset legacy")
        events_after_1 = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": "qr_generated"})

        t2 = ensure_asset_qr_token(asset.name)
        self.assertEqual(t1, t2, "lần 2: backfill idempotent — CÙNG token")
        events_after_2 = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": "qr_generated"})
        self.assertEqual(
            events_after_1, events_after_2,
            "đã có token → KHÔNG emit qr_generated lần 2 (idempotent)")


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
        self.assertTrue(CAP_SET_VERSION.startswith("v104."),
                        f"104 cap (89 + 6 asset.* + 2 D6 print/rotate + 1 firmware.approve "
                        f"+ 6 purchase.* IMM-03 Vòng 19) → "
                        f"version prefix 'v104.' (hiện {CAP_SET_VERSION})")
        self.assertEqual(len(CAPABILITY_MAP), 104,
                         "89 + 6 cap asset.* + 2 cap D6 (asset.print/asset.qr.rotate) "
                         "+ 1 firmware.approve (IMM-09 Vòng 10) "
                         "+ 6 purchase.* (IMM-03 Vòng 19) = 104")


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
# A2/A6 — Chuẩn hoá whitespace qr_token ở SSoT resolve (FR-00-90/91, BR-00-40,
# ADR-IMM00-QR-SCAN-ACTION §D8). Token tem nhiệt / deep-link camera có thể kèm
# khoảng trắng đầu/cuối hoặc trailing newline (artifact encode QR) → phải
# resolve ĐÚNG (KHÔNG false-404). Chuẩn hoá = strip 2 đầu DUY NHẤT trong service
# SSoT `resolve_qr_token` (TRƯỚC guard rỗng + query) → `get_asset_scan_info`
# nhánh token kế thừa qua `_svc_resolve_qr_token` (KHÔNG fork). Token toàn
# whitespace → sau strip rỗng → guard return None KHÔNG query (chống full-scan,
# đo query-count=0). RED viết TRƯỚC fix.
# ──────────────────────────────────────────────────────────────────────────


class TestResolveQrTokenWhitespace(unittest.TestCase):
    """Chuẩn hoá whitespace qr_token ở SSoT resolve (BE-1..BE-5). RED trước fix.

    Strip CHỈ 2 đầu (leading/trailing) — KHÔNG strip giữa (token urlsafe
    [A-Za-z0-9_-] không bao giờ chứa space giữa; space giữa = token hỏng thật →
    404). KHÔNG lowercase/transform (token case-sensitive). Sau strip rỗng →
    None leak-safe KHÔNG query (chống full-scan)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Resolve QR Whitespace",
            "description": "Category cho test chuẩn hoá whitespace qr_token",
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
            "asset_name": f"Máy WS {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"WS-SN-{uniq}",
            "asset_code": f"WS-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def _count_asset_token_queries(self):
        """Context-manager đếm số lần `frappe.db.get_value` tra theo filter
        ``{"qr_token": ...}`` trên AC Asset (= lần lookup token thực sự chạm DB).

        Path rỗng-sau-strip PHẢI = 0 (guard return None TRƯỚC query → chống
        full-scan). Wrap thẳng module service (resolve_qr_token gọi
        ``frappe.db.get_value`` trực tiếp) → đếm chính xác lần lookup token."""
        import contextlib
        counter = {"n": 0}
        orig = frappe.db.get_value

        def _wrapped(doctype, filters=None, *args, **kwargs):
            if doctype == "AC Asset" and isinstance(filters, dict) \
                    and "qr_token" in filters:
                counter["n"] += 1
            return orig(doctype, filters, *args, **kwargs)

        @contextlib.contextmanager
        def _ctx():
            frappe.db.get_value = _wrapped
            try:
                yield counter
            finally:
                frappe.db.get_value = orig
        return _ctx()

    # ── TC-RESOLVE-WS-1 — token kèm khoảng trắng đầu/cuối → resolve ĐÚNG ──────
    def test_resolve_token_with_surrounding_whitespace_resolves(self):
        """SERVICE resolve_qr_token(' '+tok+' ') → payload['name']==asset.name
        (RED trước fix: false-404 do whitespace chưa strip)."""
        from assetcore.services.imm00 import resolve_qr_token
        asset = self._make_asset("ws1")
        payload = resolve_qr_token(f"  {asset.qr_token}  ")
        self.assertIsNotNone(payload, "token + whitespace 2 đầu PHẢI resolve (KHÔNG false-404)")
        self.assertEqual(payload["name"], asset.name)
        self.assertEqual(payload["asset_code"], asset.asset_code)

    # ── TC-RESOLVE-WS-2 — trailing newline (artifact tem nhiệt) → resolve ────
    def test_resolve_token_with_trailing_newline_resolves(self):
        """resolve_qr_token(tok+'\\n') (artifact encode QR tem nhiệt) → đúng asset."""
        from assetcore.services.imm00 import resolve_qr_token
        asset = self._make_asset("ws2")
        payload = resolve_qr_token(f"{asset.qr_token}\n")
        self.assertIsNotNone(payload, "trailing newline PHẢI strip → resolve đúng")
        self.assertEqual(payload["name"], asset.name)
        # Cả tab + CRLF (biến thể artifact encode khác) cũng strip đúng.
        payload2 = resolve_qr_token(f"\t{asset.qr_token}\r\n")
        self.assertIsNotNone(payload2)
        self.assertEqual(payload2["name"], asset.name)

    # ── TC-RESOLVE-WS-3 — token TOÀN whitespace → None, query-count=0 ────────
    def test_resolve_whitespace_only_token_returns_none_no_query(self):
        """resolve_qr_token('   ')/'\\t'/'\\n' (toàn whitespace) → None; sau strip
        thành '' → guard return None KHÔNG query (query-count trên AC Asset = 0,
        chống full-scan — đối xử y hệt token rỗng)."""
        from assetcore.services.imm00 import resolve_qr_token
        for ws in ("   ", "\t", "\n", " \t\r\n "):
            with self._count_asset_token_queries() as c:
                payload = resolve_qr_token(ws)
            self.assertIsNone(payload, f"token toàn whitespace {ws!r} → None leak-safe")
            self.assertEqual(c["n"], 0,
                             f"token {ws!r} sau strip rỗng → KHÔNG query (chống full-scan)")

    # ── TC-RESOLVE-WS-4 — whitespace + token sai → None leak-safe (no 500) ───
    def test_resolve_whitespace_plus_unknown_token_returns_none(self):
        """resolve_qr_token(' khong-ton-tai ') → None (sau strip vẫn không khớp
        asset nào) — KHÔNG raise/500, leak-safe (KHÔNG phân biệt sai-định-dạng vs
        không-tồn-tại)."""
        from assetcore.services.imm00 import resolve_qr_token
        payload = resolve_qr_token("  khong-ton-tai-zzzzzzzzzzzz  ")
        self.assertIsNone(payload, "whitespace + token sai → None leak-safe (KHÔNG 500)")

    # ── BE-4 — endpoint API kế thừa chuẩn hoá service (KHÔNG strip ở API tier) ─
    def test_endpoint_resolve_token_with_whitespace_returns_200(self):
        """api.resolve_qr_token(' '+tok+' ') → 200 + payload đúng (server tự đúng
        ĐỘC LẬP, KHÔNG phụ thuộc FE trim — truy về source, CLAUDE.md §5/§20)."""
        from assetcore.api.imm00 import resolve_qr_token
        asset = self._make_asset("ep")
        resp = resolve_qr_token(token=f"  {asset.qr_token}\n")
        self.assertTrue(resp["success"], "endpoint: token+whitespace → 200")
        self.assertEqual(resp["data"]["name"], asset.name)

    def test_endpoint_resolve_whitespace_only_returns_404(self):
        """api.resolve_qr_token('   ') → 404 leak-safe (sau strip rỗng → None)."""
        from assetcore.api.imm00 import resolve_qr_token, _ERR_ASSET_NOT_FOUND
        resp = resolve_qr_token(token="   ")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 404,
                         "token toàn whitespace → 404 leak-safe (KHÔNG 500/417)")
        self.assertEqual(resp["error"], frappe._(_ERR_ASSET_NOT_FOUND),
                         "message == _ERR_ASSET_NOT_FOUND (KHÔNG leak)")

    # ── TC-SCANINFO-WS-1 — scan-info parity: token+whitespace → đúng asset ───
    def test_scan_info_token_with_whitespace_parity(self):
        """get_asset_scan_info(token=' '+tok+' ') → payload màn scan-info ĐÚNG
        asset (parity HOÀN TOÀN với resolve — chứng minh dùng CHUNG SSoT
        `_svc_resolve_qr_token`, KHÔNG nhánh chuẩn-hoá riêng)."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("siws")
        # Token y hệt resolve nhưng kèm whitespace 2 đầu + trailing newline.
        resp = get_asset_scan_info(token=f"  {asset.qr_token}\n")
        self.assertTrue(resp["success"], "scan-info: token+whitespace → 200 (parity resolve)")
        self.assertEqual(resp["data"]["name"], asset.name,
                         "scan-info kế thừa strip qua _svc_resolve_qr_token (cùng SSoT)")
        self.assertEqual(resp["data"]["asset_code"], asset.asset_code)

    # ── TC-SCANINFO-WS-2 — ws-only → 404 no-scan; name KHÔNG bị strip phá ────
    def test_scan_info_whitespace_only_token_404_and_name_branch_intact(self):
        """get_asset_scan_info(token='  ') → 404 leak-safe, KHÔNG full-scan
        (query-count token=0). Nhánh name (asset id NỘI BỘ, KHÔNG phải QR) resolve
        bình thường — KHÔNG bị chuẩn-hoá token phá."""
        from assetcore.api.imm00 import get_asset_scan_info, _ERR_ASSET_NOT_FOUND
        asset = self._make_asset("sinm")
        # token toàn whitespace → 404 + KHÔNG query token (guard rỗng sau strip).
        with self._count_asset_token_queries() as c:
            resp = get_asset_scan_info(token="  ")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["http_status"], 404,
                         "ws-only token → 404 leak-safe (KHÔNG 500/417)")
        self.assertEqual(resp["error"], frappe._(_ERR_ASSET_NOT_FOUND))
        self.assertEqual(c["n"], 0,
                         "ws-only token sau strip rỗng → KHÔNG query (chống full-scan)")
        # name nội bộ (KHÔNG strip) resolve bình thường → 200 đúng asset.
        resp_name = get_asset_scan_info(name=asset.name)
        self.assertTrue(resp_name["success"], "nhánh name resolve bình thường")
        self.assertEqual(resp_name["data"]["name"], asset.name)


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
        "location_name", "department_name", "lifecycle_status",
        "recent_maintenance", "next_pm_date",
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
        # CR-19: khoa/phòng fixture — denorm AC Asset.department → department_name
        # trên màn quét. _Test-prefix + department_code riêng để KHÔNG đụng dept
        # seeded thật (AC Department dùng department_code làm PK).
        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_Test Khoa Chẩn đoán hình ảnh (CR-19)",
            "department_code": "_TEST-SCAN-DEPT",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Department", cls.dept.name,
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

    # ── Vòng 37 (D5 — NĐ98): manufacturer_sn = Số serial NSX trong payload scan ──
    # KTV xác nhận ĐÚNG thiết bị vật lý trước khi báo hỏng/tạo WO. Đọc field thật
    # AC Asset.manufacturer_sn trong CÙNG get_value (KHÔNG round-trip), coalesce ''
    # parity asset_code/asset_name. Test SERVICE build_asset_scan_info trực tiếp.
    def test_scan_info_includes_manufacturer_sn(self):
        """build_asset_scan_info trả payload['manufacturer_sn'] == giá trị field thật."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("sn", manufacturer_sn="QR-SN-XXX")
        payload = build_asset_scan_info(asset.name)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["manufacturer_sn"], "QR-SN-XXX",
                         "Số serial NSX (D5) phải đúng nguyên văn field thật")
        self.assertIsInstance(payload["manufacturer_sn"], str,
                              "manufacturer_sn LUÔN là str (coalesce, KHÔNG None)")

    def test_scan_info_manufacturer_sn_empty_coalesces_to_str(self):
        """SN None/'' (không set) → payload['manufacturer_sn'] == '' (KHÔNG None/KeyError).

        Parity coalesce asset_code/asset_name (D5). Cả 2 nhánh rỗng (None và '')
        đều phải coalesce về str rỗng — KHÔNG để None lọt payload (no-leak raw)."""
        from assetcore.services.imm00 import build_asset_scan_info
        for tag, empty in (("none", None), ("blank", "")):
            asset = self._make_asset(f"snempty-{tag}", manufacturer_sn=empty)
            payload = build_asset_scan_info(asset.name)
            self.assertIsNotNone(payload)
            self.assertIn("manufacturer_sn", payload, "KHÔNG KeyError khi SN rỗng")
            self.assertEqual(payload["manufacturer_sn"], "",
                             f"SN={tag}({empty!r}) → '' (str rỗng, KHÔNG None)")
            self.assertIsInstance(payload["manufacturer_sn"], str)

    def test_scan_info_manufacturer_sn_no_sensitive_leak_and_no_regress(self):
        """manufacturer_sn KHÔNG kéo theo field nhạy cảm mới + asset rỗng-name → None.

        manufacturer_sn là định danh truy xuất hợp lệ (D5 — NĐ98), KHÔNG phải
        giá/khấu hao/docname. Thêm key này KHÔNG được nở field nhạy cảm; guard
        asset rỗng-name vẫn trả None (no-regress)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("snnoleak", manufacturer_sn="SN-NOLEAK-1",
                                 gross_purchase_amount=123000000)
        payload = build_asset_scan_info(asset.name)
        leaked = self._SENSITIVE_KEYS & set(payload.keys())
        self.assertFalse(leaked, f"payload KHÔNG được chứa field nhạy cảm: {leaked}")
        # no-regress guard: rỗng-name → None (KHÔNG query toàn bảng)
        self.assertIsNone(build_asset_scan_info(""))
        self.assertIsNone(build_asset_scan_info(None))

    # ── Vòng 38 (risk_classification — phân loại rủi ro Low/Medium/High/Critical) ──
    # Enum EN của AC Asset (read-only, fetch_from device_model). BE GIỮ raw enum làm
    # SSoT contract (KHÔNG dịch — FE map sang VI). Đọc field thật trong CÙNG get_value
    # (KHÔNG round-trip), coalesce '' parity manufacturer_sn/asset_code (Vòng 37).
    # KHÔNG nhầm với risk_class (A/B/C/D — WHO/NĐ98 letter class).
    def test_scan_info_includes_risk_classification(self):
        """build_asset_scan_info trả payload['risk_classification'] == raw enum (KHÔNG dịch)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("risk", risk_classification="Critical")
        payload = build_asset_scan_info(asset.name)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["risk_classification"], "Critical",
                         "risk_classification phải đúng RAW enum field thật (BE KHÔNG dịch sang VI)")
        self.assertIsInstance(payload["risk_classification"], str,
                              "risk_classification LUÔN là str (coalesce, KHÔNG None)")

    def test_scan_info_risk_classification_empty_coalesces_to_str(self):
        """risk_classification None/'' (không set) → '' (KHÔNG None/KeyError).

        Parity coalesce manufacturer_sn/asset_code (Vòng 37). Cả 2 nhánh rỗng
        (None và '') đều coalesce về str rỗng — KHÔNG để None lọt payload."""
        from assetcore.services.imm00 import build_asset_scan_info
        for tag, empty in (("none", None), ("blank", "")):
            asset = self._make_asset(f"riskempty-{tag}", risk_classification=empty)
            payload = build_asset_scan_info(asset.name)
            self.assertIsNotNone(payload)
            self.assertIn("risk_classification", payload,
                          "KHÔNG KeyError khi risk_classification rỗng (key luôn hiện diện)")
            self.assertEqual(payload["risk_classification"], "",
                             f"risk_classification={tag}({empty!r}) → '' (str rỗng, KHÔNG None)")
            self.assertIsInstance(payload["risk_classification"], str)

    def test_scan_info_risk_classification_no_sensitive_leak_and_no_regress(self):
        """risk_classification KHÔNG kéo theo field nhạy cảm mới + asset rỗng-name → None.

        risk_classification là phân loại rủi ro public (read-only enum), KHÔNG phải
        giá/khấu hao/docname. Thêm key này KHÔNG được nở field nhạy cảm; guard asset
        rỗng-name vẫn trả None (no-regress). Parity manufacturer_sn (Vòng 37)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("risknoleak", risk_classification="High",
                                 gross_purchase_amount=123000000)
        payload = build_asset_scan_info(asset.name)
        leaked = self._SENSITIVE_KEYS & set(payload.keys())
        self.assertFalse(leaked, f"payload KHÔNG được chứa field nhạy cảm: {leaked}")
        # no-regress guard: rỗng-name → None (KHÔNG query toàn bảng)
        self.assertIsNone(build_asset_scan_info(""))
        self.assertIsNone(build_asset_scan_info(None))

    # ── CR-19 (department_name — Khoa/phòng màn quét QR) ────────────────────
    # Denorm AC Asset.department → AC Department.department_name (parity
    # location_name Vòng 46). KTV hiện trường cần biết thiết bị thuộc khoa/phòng
    # nào (KHÔNG chỉ vị trí lắp đặt) để đối chiếu trước khi báo sự cố/mở WO. Đọc
    # trong CÙNG get_value ('department' thêm vào field list — KHÔNG round-trip
    # thừa), enrich qua _str_or_blank parity location_name. Asset thiếu khoa →
    # '' (KHÔNG None, KHÔNG mã raw). Test SERVICE build_asset_scan_info trực tiếp.
    def test_get_asset_scan_info_includes_department_name(self):
        """asset có department → payload['department_name'] == nhãn khoa (AC Department.department_name)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("dept", department=self.dept.name)
        payload = build_asset_scan_info(asset.name)
        self.assertIsNotNone(payload)
        self.assertIn("department_name", payload,
                      "payload màn quét PHẢI có 'department_name' (CR-19)")
        self.assertEqual(payload["department_name"], self.dept.department_name,
                         "department_name = nhãn khoa (denorm AC Department.department_name), KHÔNG mã raw")
        self.assertIsInstance(payload["department_name"], str,
                              "department_name LUÔN là str (coalesce, KHÔNG None)")

    def test_get_asset_scan_info_department_blank_when_missing(self):
        """asset KHÔNG có department → payload['department_name'] == '' (KHÔNG None/KeyError/mã raw).

        Parity coalesce location_name (Vòng 46): unassigned → skip query (KHÔNG N+1),
        _str_or_blank('') → ''. KHÔNG để None lọt payload (no-leak raw)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("nodept")  # KHÔNG set department
        payload = build_asset_scan_info(asset.name)
        self.assertIsNotNone(payload)
        self.assertIn("department_name", payload,
                      "KHÔNG KeyError khi asset thiếu khoa (key luôn hiện diện)")
        self.assertEqual(payload["department_name"], "",
                         "asset thiếu khoa → '' (str rỗng, KHÔNG None, KHÔNG mã raw)")
        self.assertIsInstance(payload["department_name"], str)

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

    # ── parity helper (Vòng 16): 3 trường ngày scan-info (next_pm_date /
    #    next_calibration_date / recent_maintenance.date) PHẢI cùng shape str
    #    'YYYY-MM-DD' (10 ký tự, KHÔNG phần giờ). Ép CÙNG 1 assertion-helper cho cả
    #    3 → KHOÁ parity contract: nếu recent_maintenance.date lệch shape (datetime
    #    thô có ':') helper RED GIỐNG HỆT khi next_pm_date lệch.
    _YMD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def _assert_ymd_date_field(self, value, field):
        self.assertIsInstance(value, str, f"{field} phải là str (str|None contract)")
        self.assertEqual(len(value), 10, f"{field} phải đúng 10 ký tự 'YYYY-MM-DD'")
        self.assertNotIn(":", value, f"{field} KHÔNG được kèm phần giờ 'HH:MM:SS'")
        self.assertRegex(value, self._YMD_RE,
                         f"{field} phải khớp regex ^\\d{{4}}-\\d{{2}}-\\d{{2}}$")

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
        # Vòng 16 — assert TRỰC TIẾP str 'YYYY-MM-DD' (KHÔNG bọc getdate() che lệch
        # shape): date đã chuẩn hoá str|None qua _date_str_or_none, DESC LIMIT 1
        # KHÔNG đổi → vẫn là sự kiện MỚI NHẤT (−3 ngày).
        self.assertEqual(rm["date"], str(getdate(add_days(nowdate(), -3))),
                         "recent_maintenance phải là sự kiện MỚI NHẤT (DESC LIMIT 1)")

    def test_scan_info_recent_maintenance_date_is_ymd_str(self):
        """date của recent_maintenance = chuỗi 'YYYY-MM-DD' (10 ký tự, KHÔNG phần
        giờ) — KHÔNG còn datetime thô. ALE timestamp CÓ phần giờ 14:32:05."""
        from assetcore.api.imm00 import get_asset_scan_info
        from frappe.utils import now_datetime
        asset = self._make_asset("ymd")
        ts = add_days(now_datetime(), -3).replace(hour=14, minute=32, second=5)
        self._add_ale(asset.name, "pm_completed", ts)
        rm = get_asset_scan_info(token=asset.qr_token)["data"]["recent_maintenance"]
        self.assertIsNotNone(rm, "có ALE bảo trì → recent_maintenance KHÔNG null")
        self.assertIsInstance(rm["date"], str, "date phải là str (str|None contract)")
        self.assertEqual(len(rm["date"]), 10, "date phải đúng 10 ký tự (KHÔNG kèm giờ)")
        self.assertNotIn(":", rm["date"], "date KHÔNG chứa phần giờ 'HH:MM:SS'")
        self.assertEqual(rm["date"], str(getdate(ts)),
                         "date = ngày (getdate) của timestamp record mới nhất")
        # Anti-false-green: date KHÁC giá trị datetime thô có giờ → CHỨNG MINH phần
        # giờ ĐÃ bị cắt. Nếu impl quên normalize, str(ts) còn 'HH:MM:SS' → RED.
        self.assertNotEqual(rm["date"], str(ts),
                            "date KHÔNG được là datetime thô (phần giờ phải bị cắt)")

    def test_scan_info_recent_maintenance_date_parity_with_pm_dates(self):
        """3 trường ngày scan-info cùng shape str 'YYYY-MM-DD' — ép CÙNG assertion-
        helper với next_pm_date/next_calibration_date để KHOÁ parity (FR-00-86)."""
        from assetcore.api.imm00 import get_asset_scan_info
        from frappe.utils import now_datetime
        asset = self._make_asset(
            "parity",
            next_pm_date=add_days(nowdate(), 30),
            next_calibration_date=add_days(nowdate(), 45),
        )
        ts = add_days(now_datetime(), -3).replace(hour=9, minute=7, second=41)
        self._add_ale(asset.name, "pm_completed", ts)
        data = get_asset_scan_info(token=asset.qr_token)["data"]
        # CÙNG 1 assertion-helper cho cả 3 → recent_maintenance.date lệch shape
        # (datetime thô có ':') sẽ RED y hệt khi next_pm_date lệch.
        self._assert_ymd_date_field(data["next_pm_date"], "next_pm_date")
        self._assert_ymd_date_field(data["next_calibration_date"], "next_calibration_date")
        self._assert_ymd_date_field(
            data["recent_maintenance"]["date"], "recent_maintenance.date")

    def test_scan_info_recent_maintenance_null_when_none(self):
        """Asset chưa có sự kiện bảo trì → recent_maintenance null/empty, KHÔNG lỗi."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("nomaint")
        data = get_asset_scan_info(token=asset.qr_token)["data"]
        self.assertIn("recent_maintenance", data)
        self.assertFalse(data["recent_maintenance"],
                         "không có bảo trì → recent_maintenance falsy (null/empty)")

    # ── Vòng 16 (FR-00-86 parity) — recent_maintenance.date = str|None 'YYYY-MM-DD' ─
    # Đóng parity contract ngày: 3 field date trên màn scan-info (next_pm_date,
    # next_calibration_date, recent_maintenance.date) CÙNG dạng str|None qua SSoT
    # _date_str_or_none — KHÔNG còn 1 field lệch shape (datetime thô kèm giờ).
    _YMD_RE = r"^\d{4}-\d{2}-\d{2}$"

    def test_scan_info_recent_maintenance_date_is_ymd_str(self):
        """date PHẢI là str 'YYYY-MM-DD' (10 ký tự, KHÔNG phần giờ 'HH:MM:SS') —
        KHÔNG còn datetime thô (timestamp Datetime của Asset Lifecycle Event)."""
        from assetcore.api.imm00 import get_asset_scan_info
        from frappe.utils import now_datetime, get_datetime
        asset = self._make_asset("rmdatestr")
        # timestamp CÓ phần GIỜ rõ ràng (14:32:05) để chứng minh giờ bị cắt.
        ts_raw = get_datetime(add_days(now_datetime(), -3)).replace(
            hour=14, minute=32, second=5, microsecond=0)
        self._add_ale(asset.name, "pm_completed", ts_raw)
        rm = get_asset_scan_info(token=asset.qr_token)["data"]["recent_maintenance"]
        self.assertIsNotNone(rm, "asset có ALE bảo trì → recent_maintenance KHÔNG null")
        self.assertIsInstance(rm["date"], str,
                              "date PHẢI là str (KHÔNG datetime thô)")
        self.assertEqual(len(rm["date"]), 10,
                         "date = 10 ký tự 'YYYY-MM-DD' (KHÔNG kèm phần giờ)")
        self.assertNotIn(":", rm["date"],
                         "date KHÔNG chứa ':' (no time component)")
        self.assertEqual(rm["date"], str(getdate(ts_raw)),
                         "date == str(getdate(<ts>)) — ngày của record mới nhất")

    def test_scan_info_recent_maintenance_date_parity_with_pm_dates(self):
        """CÙNG payload: recent_maintenance.date, next_pm_date, next_calibration_date
        đều khớp regex ^\\d{4}-\\d{2}-\\d{2}$ (CÙNG dạng str 'YYYY-MM-DD' qua SSoT
        _date_str_or_none). Ép CÙNG 1 assertion-helper với 2 field kia → khoá parity."""
        from assetcore.api.imm00 import get_asset_scan_info
        from frappe.utils import now_datetime
        past = add_days(nowdate(), -1)
        asset = self._make_asset("rmparity", next_pm_date=past,
                                 next_calibration_date=past)
        self._add_ale(asset.name, "pm_completed", add_days(now_datetime(), -3))
        data = get_asset_scan_info(token=asset.qr_token)["data"]

        def _assert_ymd(field_name, value):
            self.assertIsInstance(value, str,
                                  f"{field_name} PHẢI là str (parity str|None)")
            self.assertRegex(value, self._YMD_RE,
                             f"{field_name} PHẢI khớp 'YYYY-MM-DD' (FR-00-86 parity)")

        _assert_ymd("next_pm_date", data["next_pm_date"])
        _assert_ymd("next_calibration_date", data["next_calibration_date"])
        _assert_ymd("recent_maintenance.date", data["recent_maintenance"]["date"])

    def test_scan_info_recent_maintenance_none_when_no_event(self):
        """Asset KHÔNG có ALE bảo trì → recent_maintenance is None (giữ nhánh falsy
        — chuẩn hoá date KHÔNG regress nhánh không-có-sự-kiện)."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("rmnone")
        data = get_asset_scan_info(token=asset.qr_token)["data"]
        self.assertIsNone(data["recent_maintenance"],
                          "không có ALE bảo trì → recent_maintenance is None")

    def test_scan_info_recent_maintenance_date_strips_time_anti_false_green(self):
        """Anti-false-green: date != giá trị datetime thô có giờ → CHỨNG MINH phần
        giờ ĐÃ bị cắt. Nếu impl quên normalize (trả ev['timestamp'] thô), RED."""
        from assetcore.api.imm00 import get_asset_scan_info
        from frappe.utils import now_datetime, get_datetime
        asset = self._make_asset("rmstrip")
        ts_raw = get_datetime(add_days(now_datetime(), -3)).replace(
            hour=9, minute=7, second=41, microsecond=0)
        self._add_ale(asset.name, "pm_completed", ts_raw)
        rm = get_asset_scan_info(token=asset.qr_token)["data"]["recent_maintenance"]
        self.assertNotEqual(rm["date"], ts_raw,
                            "date KHÔNG còn là datetime thô (phần giờ bị cắt)")
        self.assertNotEqual(str(rm["date"]), str(ts_raw),
                            "str(date) != str(datetime thô) — đã strip 'HH:MM:SS'")
        self.assertEqual(rm["date"], str(getdate(ts_raw)))

    # ── Vòng 44 (FR-00 — parity type event_type) — event_type LUÔN str ───────
    # Đóng parity contract TYPE cho recent_maintenance.event_type: parity với
    # date (str|None qua _date_str_or_none) và với ''-coalesce
    # manufacturer_sn/asset_code/risk_classification trong build_asset_scan_info.
    # ALE column event_type nullable / legacy / drift → row có event_type=None/''
    # → SSoT service _recent_maintenance_event COALESCE về '' (str), KHÔNG None,
    # KHÔNG raw object. Khử rò None ra mobile-BE/non-Vue consumer + đúng FE type
    # RecentMaintenance.event_type: string (imm00.ts:110). RED viết TRƯỚC impl.
    def test_scan_info_recent_maintenance_event_type_coalesced_when_null(self):
        """SSoT _recent_maintenance_event: row ALE bảo trì có event_type=None
        (nullable col / legacy / drift) → recent_maintenance KHÔNG null, event_type
        coalesce về '' (str), KHÔNG None, KHÔNG raw object. Parity ''-coalesce với
        manufacturer_sn/asset_code/risk_classification + parity str FE type.

        Filter ``event_type ('in', _MAINTENANCE_EVENT_TYPES)`` KHÔNG đổi → để mô
        phỏng drift mà row VẪN lọt LIMIT 1, patch ``frappe.get_all`` của service
        trả đúng 1 row {event_type: None, timestamp}. Đây là defensive contract:
        dù query trả None ở cột event_type, dict-build coalesce '' (never-None)."""
        from unittest.mock import patch
        from assetcore.services import imm00 as svc
        ts = add_days(nowdate(), -3)
        with patch.object(svc.frappe, "get_all",
                          return_value=[{"event_type": None, "timestamp": ts}]):
            rm = svc._recent_maintenance_event("ASSET-DRIFT")
        self.assertIsNotNone(rm, "có row ALE bảo trì → recent_maintenance KHÔNG null")
        self.assertIsInstance(rm["event_type"], str,
                              "event_type PHẢI là str (never-None contract)")
        self.assertEqual(rm["event_type"], "",
                         "event_type=None drift → coalesce '' (KHÔNG None, KHÔNG raw)")
        # parity: date vẫn str|None qua _date_str_or_none (KHÔNG regress)
        self.assertEqual(rm["date"], str(getdate(ts)),
                         "date GIỮ str 'YYYY-MM-DD' (parity contract KHÔNG đổi)")

    def test_scan_info_recent_maintenance_event_type_is_str_type(self):
        """Anti-false-green: khoá invariant 'event_type KHÔNG bao giờ None khi
        recent_maintenance != null' ở CẢ happy-path lẫn null/empty-path. Coalesce
        'or' KHÔNG được nuốt giá trị thật (pm_completed nguyên văn)."""
        from unittest.mock import patch
        from assetcore.api.imm00 import get_asset_scan_info
        from assetcore.services import imm00 as svc
        # happy-path (E2E qua API): giá trị thật → str nguyên văn, KHÔNG bị nuốt
        asset_ok = self._make_asset("rmevtstr_ok")
        self._add_ale(asset_ok.name, "pm_completed", add_days(nowdate(), -2))
        rm_ok = get_asset_scan_info(
            token=asset_ok.qr_token)["data"]["recent_maintenance"]
        self.assertIsNotNone(rm_ok)
        self.assertIsInstance(rm_ok["event_type"], str,
                              "happy-path event_type PHẢI là str")
        self.assertEqual(rm_ok["event_type"], "pm_completed",
                         "happy-path GIỮ NGUYÊN VĂN (coalesce KHÔNG nuốt giá trị thật)")
        # null-path & empty-path (unit, drift) → '' str (vẫn str, KHÔNG None)
        ts = add_days(nowdate(), -2)
        for drift_value in (None, ""):
            with patch.object(
                    svc.frappe, "get_all",
                    return_value=[{"event_type": drift_value, "timestamp": ts}]):
                rm_drift = svc._recent_maintenance_event("ASSET-DRIFT")
            self.assertIsInstance(rm_drift["event_type"], str,
                                  f"drift {drift_value!r} → event_type PHẢI là str")
            self.assertEqual(rm_drift["event_type"], "",
                             f"drift {drift_value!r} → coalesce '' (never-None)")


# ──────────────────────────────────────────────────────────────────────────
# Vòng 48 — trạng thái BẢO HÀNH ở payload scan-info (IMM-00 scan-action).
# 2 KEY MỚI trong build_asset_scan_info:
#   (a) warranty_expiry_date: str|None 'YYYY-MM-DD' qua _date_str_or_none HIỆN CÓ
#       (parity next_pm_date/next_calibration_date — rỗng/None → None).
#   (b) warranty_expired: bool derive SERVER-SIDE qua helper MỚI
#       _is_warranty_expired(warranty_expiry_date) — STRICT < theo NGÀY server
#       (no client-clock; hôm-nay CHƯA hết hạn).
# KHÁC _is_pm_overdue/_is_calibration_overdue: KHÔNG nhận/áp lifecycle_status,
# KHÔNG có *_EXEMPT — bảo hành là sự kiện HỢP ĐỒNG độc lập lifecycle (thiết bị
# Out-of-Service/Decommissioned VẪN có thể còn/hết bảo hành). RED viết TRƯỚC impl.
# ──────────────────────────────────────────────────────────────────────────


class TestWarrantyExpiredHelper(unittest.TestCase):
    """Unit helper _is_warranty_expired(value) -> bool (read-only, no side-effect).

    True ⟺ value KHÔNG rỗng ∧ getdate(value) < getdate(nowdate()) (STRICT <).
    NULL/rỗng/None/hôm-nay/tương-lai → False. KHÔNG quan tâm lifecycle_status
    (no-exempt — KHÁC pm/cal overdue). BE-WAR-1..5."""

    def test_be_war_1_past_date_is_expired(self):
        """BE-WAR-1: ngày quá khứ → True."""
        from assetcore.services.imm00 import _is_warranty_expired
        self.assertTrue(_is_warranty_expired("2020-01-01"),
                        "warranty quá khứ → hết bảo hành (True)")

    def test_be_war_2_today_is_not_expired_strict(self):
        """BE-WAR-2: hôm nay → False (STRICT <, hôm-nay CHƯA hết hạn)."""
        from assetcore.services.imm00 import _is_warranty_expired
        self.assertFalse(_is_warranty_expired(nowdate()),
                         "hôm nay CHƯA quá hạn (STRICT < theo NGÀY server)")

    def test_be_war_3_future_date_is_not_expired(self):
        """BE-WAR-3: tương lai → False."""
        from assetcore.services.imm00 import _is_warranty_expired
        self.assertFalse(_is_warranty_expired(add_days(nowdate(), 30)),
                         "warranty tương lai → còn bảo hành (False)")

    def test_be_war_4_none_and_empty_are_not_expired(self):
        """BE-WAR-4: None / '' → False (không có thông tin ≠ hết hạn)."""
        from assetcore.services.imm00 import _is_warranty_expired
        self.assertFalse(_is_warranty_expired(None), "None → False")
        self.assertFalse(_is_warranty_expired(""), "'' → False")

    def test_be_war_5_no_exempt_independent_of_lifecycle(self):
        """BE-WAR-5 (no-exempt, KHÁC pm/cal overdue): helper KHÔNG nhận
        lifecycle_status → thiết bị Out-of-Service/Decommissioned với warranty
        quá khứ VẪN True (bảo hành độc lập lifecycle).

        Khoá invariant ở MỨC SIGNATURE: helper chỉ nhận 1 đối số (value), KHÔNG
        có tham số lifecycle_status như _is_pm_overdue/_is_calibration_overdue —
        chứng minh KHÔNG thể exempt theo trạng thái thiết bị."""
        import inspect
        from assetcore.services.imm00 import (
            _is_warranty_expired, _is_pm_overdue, _is_calibration_overdue,
        )
        past = "2020-01-01"
        # Dù gọi với asset đang ngừng dùng (lifecycle_status không liên quan),
        # warranty quá khứ vẫn True. _is_pm_overdue CÙNG ngày + status ngừng dùng
        # → False (exempt) → đối chứng chứng minh 2 cờ KHÁC bản chất.
        self.assertTrue(_is_warranty_expired(past),
                        "warranty quá khứ → True bất kể lifecycle (no-exempt)")
        self.assertFalse(_is_pm_overdue(past, "Out of Service"),
                         "đối chứng: PM overdue EXEMPT khi Out of Service")
        self.assertFalse(_is_calibration_overdue(past, "Decommissioned"),
                         "đối chứng: Calibration overdue EXEMPT khi Decommissioned")
        # SIGNATURE guard: _is_warranty_expired KHÔNG có param lifecycle_status.
        sig = inspect.signature(_is_warranty_expired)
        self.assertEqual(
            list(sig.parameters), ["value"],
            "_is_warranty_expired chỉ nhận (value) — KHÔNG lifecycle_status "
            "(no-exempt, độc lập lifecycle, KHÁC pm/cal overdue)")
        self.assertIn(
            "lifecycle_status", inspect.signature(_is_pm_overdue).parameters,
            "đối chứng: _is_pm_overdue CÓ lifecycle_status (exempt-aware)")


# ──────────────────────────────────────────────────────────────────────────
# Vòng 50 — CRASH-SAFE getdate ở 4 hàm xử-lý-ngày của build_asset_scan_info.
# warranty_expiry_date / next_pm_date / next_calibration_date dị-dạng (legacy
# import lỏng / canonical drift) KHÔNG còn ném HTTP-500 traceback-leak ở
# endpoint quét QR — degrade graceful về False / None. getdate('not-a-date')
# / getdate('2020-13-45') / getdate('2020-99-99') ném frappe.exceptions.
# ValidationError (KHÔNG phải ValueError — Exception trực tiếp), nên catch
# PHẢI liệt kê (frappe.exceptions.ValidationError, ValueError, TypeError) —
# KHÔNG `except Exception:` trần (che lỗi nghiệp vụ khác). 1 record xấu KHÔNG
# kéo sập cả màn quét QR. Parity FE formatIsoDateLabel ISO-strict (Vòng 18-19).
# RED viết TRƯỚC impl. BE-WAR-EDGE-1..6.
# ──────────────────────────────────────────────────────────────────────────
class TestScanInfoDateHelpersCrashSafe(unittest.TestCase):
    """Unit: 4 hàm xử-lý-ngày của build_asset_scan_info crash-safe trên chuỗi
    dị-dạng (legacy/drift). _is_warranty_expired / _is_pm_overdue /
    _is_calibration_overdue('not-a-date'|'2020-13-45'|'2020-99-99') → False
    (KHÔNG raise); _date_str_or_none(dị-dạng) → None (KHÔNG raise, KHÔNG leak
    verbatim). No-regress: giá trị HỢP LỆ (date-obj / ISO / None / '') giữ
    NGUYÊN hành vi cũ. Source-guard: catch HẸP, KHÔNG `except Exception:` trần.
    BE-WAR-EDGE-1..3, EDGE-5, EDGE-6."""

    # Chuỗi dị-dạng đại diện: phi-parse hoàn toàn + out-of-range (tháng/ngày).
    # Cả 3 đều khiến getdate() ném frappe.exceptions.ValidationError (đã verify).
    _MALFORMED = ("not-a-date", "2020-13-45", "2020-99-99", "garbage")

    # ── BE-WAR-EDGE-1: _is_warranty_expired(dị-dạng) → False (no raise) ───────
    def test_be_war_edge_1_warranty_malformed_returns_false_no_raise(self):
        """BE-WAR-EDGE-1: _is_warranty_expired('not-a-date') /
        _is_warranty_expired('2020-13-45') → False (KHÔNG raise
        frappe.exceptions.ValidationError). Chuỗi phi-parse = 'không xác định
        ≠ hết hạn' — no-false-alarm."""
        from assetcore.services.imm00 import _is_warranty_expired
        for bad in self._MALFORMED:
            with self.subTest(value=bad):
                try:
                    result = _is_warranty_expired(bad)
                except Exception as exc:  # noqa: BLE001 — test phải FAIL nếu raise
                    self.fail(f"_is_warranty_expired({bad!r}) KHÔNG được raise, "
                              f"đã raise {type(exc).__name__}: {exc}")
                self.assertIs(result, False,
                              f"_is_warranty_expired({bad!r}) → False (dị-dạng = "
                              "không xác định ≠ hết hạn)")

    # ── BE-WAR-EDGE-2: 2 overdue helper(dị-dạng) → False (no raise) ──────────
    def test_be_war_edge_2_overdue_malformed_returns_false_no_raise(self):
        """BE-WAR-EDGE-2: _is_pm_overdue('garbage', None) và
        _is_calibration_overdue('2020-99-99', None) → False (KHÔNG raise) —
        parity warranty. Date dị-dạng KHÔNG bịa cờ quá hạn."""
        from assetcore.services.imm00 import (
            _is_pm_overdue, _is_calibration_overdue,
        )
        for helper in (_is_pm_overdue, _is_calibration_overdue):
            for bad in self._MALFORMED:
                with self.subTest(helper=helper.__name__, value=bad):
                    try:
                        result = helper(bad, None)
                    except Exception as exc:  # noqa: BLE001
                        self.fail(f"{helper.__name__}({bad!r}, None) KHÔNG được "
                                  f"raise, đã raise {type(exc).__name__}: {exc}")
                    self.assertIs(result, False,
                                  f"{helper.__name__}({bad!r}, None) → False "
                                  "(dị-dạng KHÔNG bịa cờ quá hạn)")

    # ── BE-WAR-EDGE-3: _date_str_or_none(dị-dạng) → None (no raise) ──────────
    def test_be_war_edge_3_date_str_malformed_returns_none_no_raise(self):
        """BE-WAR-EDGE-3: _date_str_or_none('not-a-date') /
        _date_str_or_none('2020-13-45') → None (KHÔNG raise, KHÔNG leak
        verbatim, KHÔNG mis-parse câm). Parity FE formatIsoDateLabel ISO-strict
        (Vòng 18-19) — nay đối xứng ở BE."""
        from assetcore.services.imm00 import _date_str_or_none
        for bad in self._MALFORMED:
            with self.subTest(value=bad):
                try:
                    result = _date_str_or_none(bad)
                except Exception as exc:  # noqa: BLE001
                    self.fail(f"_date_str_or_none({bad!r}) KHÔNG được raise, "
                              f"đã raise {type(exc).__name__}: {exc}")
                self.assertIsNone(result,
                                  f"_date_str_or_none({bad!r}) → None (KHÔNG leak "
                                  "verbatim, KHÔNG crash)")

    # ── BE-WAR-EDGE-5: no-regress giá trị HỢP LỆ giữ NGUYÊN hành vi cũ ───────
    def test_be_war_edge_5_valid_values_no_regress(self):
        """BE-WAR-EDGE-5 (no-regress): mọi giá trị HỢP LỆ (datetime.date object,
        chuỗi ISO 'YYYY-MM-DD', None, '') GIỮ NGUYÊN hành vi cũ.
        past→True/today→False/future→False/None→False/''→False;
        _date_str_or_none(date-obj)→'YYYY-MM-DD'. Guard KHÔNG nuốt path hợp lệ."""
        from datetime import date
        from assetcore.services.imm00 import (
            _is_warranty_expired, _is_pm_overdue, _is_calibration_overdue,
            _date_str_or_none,
        )
        # _is_warranty_expired — biên strict < theo NGÀY server.
        self.assertIs(_is_warranty_expired("2020-01-01"), True, "ISO quá khứ → True")
        self.assertIs(_is_warranty_expired(nowdate()), False, "hôm nay → False (strict)")
        self.assertIs(_is_warranty_expired(add_days(nowdate(), 30)), False,
                      "tương lai → False")
        self.assertIs(_is_warranty_expired(None), False, "None → False")
        self.assertIs(_is_warranty_expired(""), False, "'' → False")
        # date OBJECT (như DB trả) — KHÔNG bị guard nuốt nhầm.
        self.assertIs(_is_warranty_expired(date(2020, 1, 1)), True,
                      "date-obj quá khứ → True (no-regress)")
        # 2 overdue helper — date-obj + ISO hợp lệ vẫn derive đúng.
        self.assertIs(_is_pm_overdue(add_days(nowdate(), -1), "Active"), True)
        self.assertIs(_is_pm_overdue(date(2020, 1, 1), "Active"), True,
                      "date-obj quá khứ → True (no-regress)")
        self.assertIs(_is_pm_overdue(None, "Active"), False)
        self.assertIs(_is_calibration_overdue(add_days(nowdate(), 1), "Active"), False)
        self.assertIs(_is_calibration_overdue(date(2020, 1, 1), "Active"), True,
                      "date-obj quá khứ → True (no-regress)")
        # _date_str_or_none — date-obj → 'YYYY-MM-DD'; ISO str round-trip; rỗng → None.
        self.assertEqual(_date_str_or_none(date(2027, 5, 1)), "2027-05-01",
                         "date-obj → 'YYYY-MM-DD' (no-regress)")
        self.assertEqual(_date_str_or_none("2027-05-01"), "2027-05-01",
                         "ISO str round-trip (no-regress)")
        self.assertIsNone(_date_str_or_none(None), "None → None")
        self.assertIsNone(_date_str_or_none(""), "'' → None")

    # ── BE-WAR-EDGE-6: source-guard catch HẸP, KHÔNG `except Exception:` trần ─
    def test_be_war_edge_6_catch_is_narrow_not_bare_except(self):
        """BE-WAR-EDGE-6 (no-mask-real-bug): guard CHỈ nuốt lỗi parse-date —
        source 4 hàm (+ helper SSoT nếu có) PHẢI catch đúng
        (frappe.exceptions.ValidationError / ValueError / TypeError), KHÔNG
        `except Exception:` trần / `except:` trần (che lỗi nghiệp vụ khác).

        ValidationError KHÔNG phải subclass ValueError (Exception trực tiếp) →
        BẮT BUỘC liệt kê tường minh; `except (ValueError, TypeError):` đơn lẻ
        sẽ KHÔNG bắt → vẫn HTTP-500. Guard này khoá invariant đó."""
        import inspect
        from assetcore.services import imm00 as svc
        from assetcore.services.imm00 import (
            _is_warranty_expired, _is_pm_overdue, _is_calibration_overdue,
            _date_str_or_none,
        )
        # Gom nguồn 4 hàm + (nếu có) helper SSoT _safe_getdate — bất kỳ try/except
        # nuốt getdate PHẢI nằm trong tập source này.
        srcs = [inspect.getsource(f) for f in (
            _is_warranty_expired, _is_pm_overdue,
            _is_calibration_overdue, _date_str_or_none,
        )]
        if hasattr(svc, "_safe_getdate"):
            srcs.append(inspect.getsource(svc._safe_getdate))
        blob = "\n".join(srcs)

        def _strip_to_code(text: str) -> str:
            # Bóc docstring/string-literal + comment để CHỈ còn CODE thực thi —
            # tránh false-match khi docstring NHẮC chữ 'except Exception:' (như
            # các comment giải thích vì sao KHÔNG dùng catch-all). AST-based:
            # an toàn hơn regex naïve, không tự nhầm chính mình.
            import ast
            stripped_lines = []
            for line in text.splitlines():
                stripped_lines.append(line.split("#", 1)[0])
            no_comment = "\n".join(stripped_lines)
            # Loại mọi string literal (gồm docstring) qua AST: parse từng hàm.
            try:
                tree = ast.parse(no_comment)
            except SyntaxError:
                # getsource có thể trả nhiều def liền — bọc vào module vẫn parse
                # được; nếu vẫn fail thì fallback dùng no_comment thô.
                return no_comment
            string_spans = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                        for ln in range(node.lineno, (node.end_lineno or node.lineno) + 1):
                            string_spans.add(ln)
            kept = []
            for i, line in enumerate(no_comment.splitlines(), start=1):
                if i in string_spans:
                    continue
                kept.append(line)
            return "\n".join(kept)

        code = _strip_to_code(blob)
        # Phải có guard parse-date (try + getdate trong vùng có except).
        self.assertIn("getdate", code, "4 hàm vẫn dùng getdate (mốc ngày server)")
        self.assertIn("except", code,
                      "PHẢI có except bọc getdate (degrade thay vì 500)")
        # KHÔNG `except Exception:` trần / `except:` trần (catch-all che lỗi khác).
        self.assertNotRegex(
            code, r"except\s+Exception\s*[:\(]",
            "KHÔNG `except Exception:` trần — catch-all che lỗi nghiệp vụ khác "
            "(no-mask-real-bug). Phải liệt kê parse-date error cụ thể.")
        self.assertNotRegex(
            code, r"except\s*:",
            "KHÔNG `except:` trần (bắt cả BaseException — nuốt KeyboardInterrupt)")
        # Catch PHẢI liệt kê ValidationError (vì NOT subclass ValueError) +
        # ValueError + TypeError. Chấp nhận frappe.exceptions.ValidationError
        # hoặc alias ValidationError.
        self.assertRegex(
            code, r"ValidationError",
            "catch PHẢI liệt kê ValidationError (getdate ném "
            "frappe.exceptions.ValidationError — NOT subclass ValueError → "
            "`except (ValueError, TypeError)` đơn lẻ KHÔNG bắt được)")
        self.assertIn("ValueError", code,
                      "catch nên liệt kê ValueError (dateutil out-of-range)")
        self.assertIn("TypeError", code,
                      "catch nên liệt kê TypeError (kiểu lạ không parse được)")


class TestWarrantyInScanInfo(unittest.TestCase):
    """Integration build_asset_scan_info: 2 key warranty mới đúng kiểu/format +
    13 key cũ no-regress + KHÔNG leak field tài chính. BE-WAR-6..8."""

    _OLD_KEYS = {
        "name", "asset_code", "asset_name", "manufacturer_sn",
        "risk_classification", "lifecycle_status", "device_model_name",
        "location_name", "department_name", "next_pm_date", "next_calibration_date",
        "recent_maintenance", "pm_overdue", "calibration_overdue",
        "available_actions",
    }
    _NEW_KEYS = {"warranty_expiry_date", "warranty_expired"}
    _SENSITIVE_KEYS = {
        "gross_purchase_amount", "purchase_cost", "accumulated_depreciation",
        "depreciation_method", "depreciation_schedule", "warranty_period",
    }

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Warranty (V48)",
            "description": "Category cho test warranty scan-info",
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
            "asset_name": f"Máy Warranty {uniq}",
            "asset_category": self.cat.name,
            "asset_code": f"WAR-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def test_be_war_6_future_warranty_iso_str_not_expired(self):
        """BE-WAR-6: warranty_expiry_date=date(2027,5,1) → payload
        ['warranty_expiry_date']=='2027-05-01' (str ISO, KHÔNG date object/giờ)
        + ['warranty_expired']==False (tương lai)."""
        from datetime import date
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("future", warranty_expiry_date=date(2027, 5, 1))
        payload = build_asset_scan_info(asset.name)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["warranty_expiry_date"], "2027-05-01",
                         "warranty_expiry_date = str ISO 'YYYY-MM-DD'")
        self.assertIsInstance(payload["warranty_expiry_date"], str,
                              "warranty_expiry_date PHẢI là str (KHÔNG date object)")
        self.assertNotIn(":", payload["warranty_expiry_date"],
                         "KHÔNG kèm phần giờ 'HH:MM:SS'")
        self.assertIs(payload["warranty_expired"], False,
                      "2027 > hôm nay → còn bảo hành (False)")

    def test_be_war_6b_past_warranty_expired_true(self):
        """warranty quá khứ trong payload thật → warranty_expired is True."""
        from datetime import date
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("past", warranty_expiry_date=date(2020, 1, 1))
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["warranty_expiry_date"], "2020-01-01")
        self.assertIs(payload["warranty_expired"], True,
                      "2020 < hôm nay → hết bảo hành (True)")

    def test_be_war_7_empty_warranty_none_and_false(self):
        """BE-WAR-7: asset warranty rỗng → warranty_expiry_date is None +
        warranty_expired is False (không có thông tin ≠ hết hạn)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("empty")  # KHÔNG set warranty_expiry_date
        payload = build_asset_scan_info(asset.name)
        self.assertIsNone(payload["warranty_expiry_date"],
                          "warranty rỗng → None (parity next_pm_date)")
        self.assertIs(payload["warranty_expired"], False,
                      "warranty rỗng → KHÔNG hết hạn (False, no-false-alarm)")

    def test_be_war_8_old_keys_no_regress_and_no_financial_leak(self):
        """BE-WAR-8: payload GIỮ đủ 13 key cũ (no-regress) + đúng 2 key mới +
        KHÔNG leak field tài chính/bảo hành nhạy cảm khác."""
        from datetime import date
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset(
            "noregress",
            next_pm_date=add_days(nowdate(), 30),
            next_calibration_date=add_days(nowdate(), 45),
            warranty_expiry_date=date(2027, 5, 1),
            gross_purchase_amount=999000000,
        )
        payload = build_asset_scan_info(asset.name)
        keys = set(payload.keys())
        missing = self._OLD_KEYS - keys
        self.assertFalse(missing, f"key cũ PHẢI giữ nguyên, thiếu: {missing}")
        for k in self._NEW_KEYS:
            self.assertIn(k, keys, f"key warranty mới PHẢI có: '{k}'")
        leaked = self._SENSITIVE_KEYS & keys
        self.assertFalse(leaked,
                         f"KHÔNG leak field tài chính/nhạy cảm: {leaked}")
        # Đúng 17 key total (15 cũ gồm name + department_name CR-19 + 2 warranty)
        # — KHÔNG thừa key lạ. _OLD_KEYS đã gồm 'name' → 15 + 2 = 17.
        self.assertEqual(keys, self._OLD_KEYS | self._NEW_KEYS,
                         "payload = đúng 15 key cũ (gồm name + department_name) + "
                         "2 key warranty, KHÔNG thừa/thiếu")


class TestScanInfoMalformedDateResilience(unittest.TestCase):
    """BE-WAR-EDGE-4 (integration, assert-chính) — build_asset_scan_info trên 1
    AC Asset có warranty_expiry_date / next_pm_date / next_calibration_date là
    CHUỖI DỊ-DẠNG (legacy/drift/import bẩn) KHÔNG ném exception. Trả payload đầy
    đủ với cờ tương ứng=False / field ngày=None; 13 field còn lại GIỮ NGUYÊN
    (degrade gracefully — 1 record xấu KHÔNG kéo sập cả payload, KHÔNG HTTP-500
    traceback-leak ở endpoint quét QR).

    Date-column DB chặn set garbage thật → MOCK frappe.db.get_value trả row có
    value bẩn (mô phỏng drift/legacy) trên 1 asset thật → assert resilience ở
    BIÊN build_asset_scan_info là đủ. RED viết TRƯỚC impl."""

    _ALL_KEYS = {
        "name", "asset_code", "asset_name", "manufacturer_sn",
        "risk_classification", "lifecycle_status", "device_model_name",
        "location_name", "next_pm_date", "next_calibration_date",
        "recent_maintenance", "pm_overdue", "calibration_overdue",
        "available_actions", "warranty_expiry_date", "warranty_expired",
    }

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Malformed-Date (V50)",
            "description": "Category cho test crash-safe getdate scan-info",
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

    def _make_asset(self):
        import uuid
        uniq = uuid.uuid4().hex[:8]
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy Malformed {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"MAL-SN-{uniq}",
            "asset_code": f"MAL-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def _patched_get_value(self, real_get_value, asset_name, dirty):
        """Wrap frappe.db.get_value: với CHÍNH asset đang test + cột scan-info,
        trả row có warranty_expiry_date BẨN (drift). Mọi call khác → real
        (device_model_name/location_name/recent_maintenance vẫn chạy thật)."""
        def _side_effect(*args, **kwargs):
            row = real_get_value(*args, **kwargs)
            # Chỉ can thiệp row scan-info của ĐÚNG asset (as_dict, có key warranty).
            if (isinstance(row, dict)
                    and row.get("name") == asset_name
                    and "warranty_expiry_date" in row):
                row = dict(row)
                row["warranty_expiry_date"] = dirty
            return row
        return _side_effect

    def test_be_war_edge_4_malformed_warranty_degrades_no_raise(self):
        """BE-WAR-EDGE-4 (assert-chính): warranty_expiry_date='not-a-date'
        (mô phỏng drift) → build_asset_scan_info KHÔNG raise; warranty_expired
        is False, warranty_expiry_date is None, 13 field còn lại present."""
        from unittest import mock
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset()
        real_gv = frappe.db.get_value
        side = self._patched_get_value(real_gv, asset.name, "not-a-date")
        with mock.patch.object(frappe.db, "get_value", side_effect=side):
            try:
                payload = build_asset_scan_info(asset.name)
            except Exception as exc:  # noqa: BLE001
                self.fail("build_asset_scan_info KHÔNG được raise trên "
                          "warranty_expiry_date dị-dạng (legacy/drift) — phải "
                          f"degrade graceful. Đã raise {type(exc).__name__}: {exc}")
        self.assertIsNotNone(payload, "payload KHÔNG None (asset tồn tại)")
        self.assertIs(payload["warranty_expired"], False,
                      "warranty dị-dạng → warranty_expired=False (no-false-alarm)")
        self.assertIsNone(payload["warranty_expiry_date"],
                          "warranty dị-dạng → warranty_expiry_date=None (KHÔNG "
                          "leak verbatim 'not-a-date')")
        # 13 field còn lại present (degrade gracefully — KHÔNG sập cả payload).
        present = set(payload.keys())
        missing = self._ALL_KEYS - present
        self.assertFalse(missing, f"payload đầy đủ — thiếu field: {missing}")
        # KHÔNG leak chuỗi bẩn verbatim ở field bảo hành.
        self.assertNotEqual(payload["warranty_expiry_date"], "not-a-date")

    def test_be_war_edge_4b_malformed_pm_and_cal_degrade_no_raise(self):
        """BE-WAR-EDGE-4b (parity 3 field ngày): next_pm_date='2020-13-45' +
        next_calibration_date='2020-99-99' dị-dạng → KHÔNG raise; pm_overdue=
        False, calibration_overdue=False, 2 field ngày=None; payload đầy đủ."""
        from unittest import mock
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset()
        real_gv = frappe.db.get_value

        def _side_effect(*args, **kwargs):
            row = real_gv(*args, **kwargs)
            if (isinstance(row, dict)
                    and row.get("name") == asset.name
                    and "next_pm_date" in row):
                row = dict(row)
                row["next_pm_date"] = "2020-13-45"
                row["next_calibration_date"] = "2020-99-99"
            return row

        with mock.patch.object(frappe.db, "get_value", side_effect=_side_effect):
            try:
                payload = build_asset_scan_info(asset.name)
            except Exception as exc:  # noqa: BLE001
                self.fail("build_asset_scan_info KHÔNG được raise trên next_pm_date"
                          f"/next_calibration_date dị-dạng. Raise {type(exc).__name__}: {exc}")
        self.assertIsNotNone(payload)
        self.assertIs(payload["pm_overdue"], False,
                      "next_pm_date dị-dạng → pm_overdue=False (KHÔNG bịa cờ)")
        self.assertIs(payload["calibration_overdue"], False,
                      "next_calibration_date dị-dạng → calibration_overdue=False")
        self.assertIsNone(payload["next_pm_date"], "dị-dạng → None")
        self.assertIsNone(payload["next_calibration_date"], "dị-dạng → None")
        missing = self._ALL_KEYS - set(payload.keys())
        self.assertFalse(missing, f"payload đầy đủ — thiếu field: {missing}")

    def test_be_war_edge_4c_valid_warranty_still_works_under_mock(self):
        """No-regress control: dưới CÙNG cơ chế mock nhưng inject value HỢP LỆ
        (date thật quá khứ) → warranty_expired=True + warranty_expiry_date ISO.
        Chứng minh guard KHÔNG nuốt path hợp lệ (đối chứng EDGE-4)."""
        from datetime import date
        from unittest import mock
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset()
        real_gv = frappe.db.get_value
        side = self._patched_get_value(real_gv, asset.name, date(2020, 1, 1))
        with mock.patch.object(frappe.db, "get_value", side_effect=side):
            payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["warranty_expiry_date"], "2020-01-01",
                         "value hợp lệ vẫn → ISO str (guard KHÔNG nuốt nhầm)")
        self.assertIs(payload["warranty_expired"], True,
                      "value hợp lệ quá khứ vẫn → True (no-regress dưới mock)")


# ──────────────────────────────────────────────────────────────────────────
# Vòng 45 — chuẩn hoá whitespace-only của 4 trường định danh chuỗi
# (asset_code/asset_name/manufacturer_sn/risk_classification) ở SSoT payload
# scan-info + nhãn QR. '   '/'\n'/'\t' (canonical drift / legacy / mobile-BE
# copy-paste) coalesce về '' tại BE — khử rò junk-whitespace ra mobile-BE /
# non-Vue consumer mà FE `.trim()` đang ÂM THẦM gánh. 1 SSoT helper
# `_str_or_blank(value)`: blank/whitespace-only/None → '', else value.strip()
# — parity với `_date_str_or_none` (str, never None) + chuẩn hoá qr_token /
# preset (Vòng 6/31/32: strip 2 đầu, KHÔNG nuốt nội dung giữa-chuỗi).
# No-regress: asset bình thường trả y hệt; event_type (Vòng 44) + 3 trường
# ngày (str|None Vòng 11/16) KHÔNG đổi shape. RED viết TRƯỚC impl.
# ──────────────────────────────────────────────────────────────────────────


class TestAssetIdentityWhitespaceStrip(unittest.TestCase):
    """Vòng 45 — `_str_or_blank` chuẩn hoá 4 trường định danh chuỗi trong
    build_asset_scan_info + build_asset_label_data[_batch]: whitespace-only/
    None → '' (str); giá trị thật kèm whitespace 2 đầu → strip (KHÔNG nuốt
    nội dung). RED viết TRƯỚC impl."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị WS-Strip (V45)",
            "description": "Category cho test whitespace-strip định danh",
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
        # Vòng 46 — track IMM Device Model / AC Location fixtures để purge SAU
        # khi asset đã xoá (FK Link AC Asset → 2 doctype này).
        self._models: list[str] = []
        self._locations: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        # Purge model/location SAU asset (FK an toàn) — Vòng 46.
        for m in self._models:
            frappe.delete_doc("IMM Device Model", m,
                              force=True, ignore_permissions=True)
        for loc in self._locations:
            frappe.delete_doc("AC Location", loc,
                              force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_asset(self, suffix="", **extra):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy WS {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"WSS-SN-{uniq}",
            "asset_code": f"WSS-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _set_raw(self, name, **vals):
        """Ghi giá trị THÔ (whitespace-junk) vào DB bỏ qua validate đường form —
        mô phỏng canonical drift / legacy / import lỏng để kiểm chuẩn hoá BE."""
        frappe.db.set_value("AC Asset", name, vals, update_modified=False)

    # ── TC-SI-WS-1 — manufacturer_sn='   ' → '' (str, KHÔNG '   ') ───────────
    def test_si_ws_1_manufacturer_sn_whitespace_only_blank(self):
        """build_asset_scan_info: manufacturer_sn='   ' → payload '' (str)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("si1")
        self._set_raw(asset.name, manufacturer_sn="   ")
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["manufacturer_sn"], "",
                         "manufacturer_sn whitespace-only → '' (khử junk)")
        self.assertIsInstance(payload["manufacturer_sn"], str,
                              "type vẫn str (KHÔNG None)")
        self.assertNotEqual(payload["manufacturer_sn"], "   ",
                            "KHÔNG rò '   ' ra non-Vue consumer")

    # ── TC-SI-WS-2 — risk_classification='\t\n' → '' ; 'High' giữ nguyên ─────
    def test_si_ws_2_risk_classification_whitespace_blank_and_clean_kept(self):
        """risk_classification='\\t\\n' → '' (parity); 'High' (sạch) giữ nguyên."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("si2")
        self._set_raw(asset.name, risk_classification="\t\n")
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["risk_classification"], "",
                         "risk_classification whitespace-only → '' (parity)")
        self.assertNotIn("\t", payload["risk_classification"])
        self.assertNotIn("\n", payload["risk_classification"])
        self.assertIsInstance(payload["risk_classification"], str)
        # giá trị sạch → giữ nguyên (KHÔNG over-normalize)
        clean = self._make_asset("si2c", risk_classification="High")
        p2 = build_asset_scan_info(clean.name)
        self.assertEqual(p2["risk_classification"], "High",
                         "giá trị sạch 'High' giữ nguyên (KHÔNG dịch/đổi)")

    # ── TC-SI-WS-3 — ' SN-123 ' → 'SN-123' (strip 2 đầu, KHÔNG nuốt nội dung) ─
    def test_si_ws_3_canonical_with_surrounding_ws_stripped_not_eaten(self):
        """manufacturer_sn=' SN-123 ' → 'SN-123' (strip 2 đầu, GIỮ nội dung)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("si3")
        self._set_raw(asset.name, manufacturer_sn=" SN-123 ")
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["manufacturer_sn"], "SN-123",
                         "strip 2 đầu, KHÔNG nuốt nội dung (parity qr_token/preset)")

    # ── TC-SI-WS-4 — asset_name='\n' + asset_code='  ' → cả hai '' ───────────
    def test_si_ws_4_name_code_whitespace_blank_plus_no_regress(self):
        """asset_name='\\n' + asset_code='  ' → cả hai '' ; asset bình thường
        → no-regress (giá trị y hệt)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("si4")
        self._set_raw(asset.name, asset_name="\n", asset_code="  ")
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["asset_name"], "",
                         "asset_name whitespace-only → '' (h1 không nhận junk)")
        self.assertEqual(payload["asset_code"], "",
                         "asset_code whitespace-only → '' (định danh không junk)")
        self.assertIsInstance(payload["asset_name"], str)
        self.assertIsInstance(payload["asset_code"], str)
        # no-regress: asset có giá trị thật → trả y hệt
        normal = self._make_asset("si4n", risk_classification="Medium")
        np = build_asset_scan_info(normal.name)
        self.assertEqual(np["asset_code"], normal.asset_code)
        self.assertEqual(np["asset_name"], normal.asset_name)
        self.assertEqual(np["manufacturer_sn"], normal.manufacturer_sn)
        self.assertEqual(np["risk_classification"], "Medium")

    # ── TC-SI-WS-NOREGRESS — event_type (V44) + 3 trường ngày shape KHÔNG đổi ─
    def test_si_ws_noregress_event_type_and_date_shape_unchanged(self):
        """Thêm helper KHÔNG đổi shape: event_type (str) + next_pm_date /
        next_calibration_date / recent_maintenance.date (str|None) giữ nguyên."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset(
            "sinr",
            next_pm_date=add_days(nowdate(), 30),
            next_calibration_date=add_days(nowdate(), 60),
        )
        frappe.get_doc({
            "doctype": "Asset Lifecycle Event",
            "asset": asset.name, "event_type": "pm_completed",
            "timestamp": add_days(nowdate(), -5),
            "actor": "Administrator", "from_status": "", "to_status": "",
            "root_doctype": "AC Asset", "root_record": asset.name,
            "notes": "test ALE noregress",
        }).insert(ignore_permissions=True)
        payload = build_asset_scan_info(asset.name)
        # 3 trường ngày: str (có giá trị) — shape str|None KHÔNG đổi
        self.assertIsInstance(payload["next_pm_date"], str)
        self.assertEqual(len(payload["next_pm_date"]), 10)
        self.assertIsInstance(payload["next_calibration_date"], str)
        rm = payload["recent_maintenance"]
        self.assertIsNotNone(rm)
        self.assertIsInstance(rm["event_type"], str, "event_type V44 vẫn str")
        self.assertEqual(rm["event_type"], "pm_completed")
        self.assertIsInstance(rm["date"], str)
        self.assertEqual(len(rm["date"]), 10, "date 'YYYY-MM-DD' shape giữ nguyên")
        # asset chưa có sự kiện bảo trì → recent_maintenance None (shape KHÔNG đổi)
        empty = self._make_asset("sinr2")
        self.assertIsNone(build_asset_scan_info(empty.name)["recent_maintenance"])

    # ── lifecycle_status GIỮ RAW (KHÔNG áp _str_or_blank — FE dịch nhãn) ──────
    def test_si_ws_lifecycle_status_kept_raw(self):
        """lifecycle_status KHÔNG bị _str_or_blank đụng — giữ canonical raw để
        FE dịch (parity quyết định Vòng 38 risk_classification raw enum)."""
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("silc")
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["lifecycle_status"], "Active",
                         "lifecycle_status giữ mã canonical raw (FE dịch)")

    # ── TC-LBL-WS-1 — build_asset_label_data: manufacturer_sn='   ' → '' ─────
    def test_lbl_ws_1_label_data_manufacturer_sn_whitespace_blank(self):
        """build_asset_label_data: manufacturer_sn='   ' → '' (parity scan-info)."""
        from assetcore.services.imm00 import build_asset_label_data
        asset = self._make_asset("lbl1")
        self._set_raw(asset.name, manufacturer_sn="   ", asset_name="\t ",
                      asset_code=" \n ")
        data = build_asset_label_data(asset.name)
        self.assertEqual(data["manufacturer_sn"], "",
                         "manufacturer_sn whitespace-only → '' (parity nhãn)")
        self.assertEqual(data["asset_name"], "",
                         "asset_name whitespace-only → '' (parity nhãn)")
        self.assertEqual(data["asset_code"], "",
                         "asset_code whitespace-only → '' (parity nhãn)")
        for k in ("manufacturer_sn", "asset_name", "asset_code"):
            self.assertIsInstance(data[k], str)
        # qr_url KHÔNG đụng (đã strip tầng render riêng) — vẫn URL hợp lệ
        self.assertIn("/a/", data["qr_url"])

    # ── TC-LBL-WS-2 — batch: item hợp lệ strip ; item lỗi GIỮ {name, error} ──
    def test_lbl_ws_2_batch_valid_strips_error_item_unchanged(self):
        """build_asset_label_data_batch: 1 asset manufacturer_sn=' \\t ' + 1 name
        không tồn tại → item1 manufacturer_sn=='' ; item2 GIỮ {name, error:
        'AC-E001'} (KHÔNG nở key)."""
        from assetcore.services.imm00 import build_asset_label_data_batch
        a1 = self._make_asset("lblb1")
        self._set_raw(a1.name, manufacturer_sn=" \t ")
        missing = "AC-ASSET-NONEXISTENT-WS45"
        out = build_asset_label_data_batch([a1.name, missing])
        self.assertEqual(len(out), 2, "giữ index, KHÔNG drop")
        self.assertEqual(out[0]["name"], a1.name)
        self.assertEqual(out[0]["manufacturer_sn"], "",
                         "item hợp lệ: manufacturer_sn whitespace-only → ''")
        self.assertIsInstance(out[0]["manufacturer_sn"], str)
        # item lỗi GIỮ NGUYÊN {name, error} — KHÔNG nở key
        self.assertEqual(out[1]["name"], missing)
        self.assertEqual(out[1].get("error"), "AC-E001")
        self.assertEqual(set(out[1].keys()), {"name", "error"},
                         "item lỗi đúng {name, error} (KHÔNG nở key sau helper)")

    # ── canonical kèm whitespace 2 đầu trên nhãn → strip, KHÔNG nuốt ─────────
    def test_lbl_ws_canonical_surrounding_ws_stripped(self):
        """build_asset_label_data: asset_code=' WSS-X ' → 'WSS-X' (strip 2 đầu)."""
        from assetcore.services.imm00 import build_asset_label_data
        asset = self._make_asset("lblc")
        self._set_raw(asset.name, asset_code=" WSS-X ")
        data = build_asset_label_data(asset.name)
        self.assertEqual(data["asset_code"], "WSS-X",
                         "strip 2 đầu, KHÔNG nuốt nội dung (parity scan-info)")

    # ──────────────────────────────────────────────────────────────────────
    # Vòng 46 — mở rộng parity _str_or_blank sang 2 NHÃN QUAN HỆ
    # device_model_name (← IMM Device Model.model_name) +
    # location_name (← AC Location.location_name). 2 field này resolve qua
    # get_value/IN-map → trước Vòng 46 dùng `(... if ... else '') or ''` raw →
    # whitespace-only ('   ' / '\n' / '\t') lọt nguyên ra mobile-BE/non-Vue +
    # tem in. Bọc qua _str_or_blank (parity 4 trường định danh Vòng 45):
    # whitespace-only/None → '' đã strip 2 đầu; KHÔNG transform giữa-chuỗi.
    # KHÔNG round-trip DB thêm (chỉ bọc kết quả get_value/map sẵn có). RED
    # viết TRƯỚC fix (hiện `or ''` chỉ coalesce None→'', để '   ' lọt).
    # ──────────────────────────────────────────────────────────────────────

    def _make_model_raw(self, suffix: str, raw_model_name: str):
        """IMM Device Model với model_name THÔ (whitespace-junk) — insert tên
        hợp lệ rồi set_value bỏ qua validate (mô phỏng canonical drift/legacy/
        import lỏng để kiểm chuẩn hoá BE). Trả docname."""
        m = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": f"WS46 Model {suffix}",
            "manufacturer": "WS46 Mfg",
            "medical_device_class": "Class II",
            "asset_category": self.cat.name,
        }).insert(ignore_permissions=True)
        frappe.db.set_value("IMM Device Model", m.name,
                            "model_name", raw_model_name, update_modified=False)
        self._models.append(m.name)
        return m.name

    def _make_location_raw(self, suffix: str, raw_location_name: str):
        """AC Location với location_name THÔ (whitespace-junk) — insert tên hợp
        lệ rồi set_value bỏ qua validate. Trả docname."""
        loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": f"WS46 Loc {suffix}",
            "location_type": "Room",
        }).insert(ignore_permissions=True)
        frappe.db.set_value("AC Location", loc.name,
                            "location_name", raw_location_name, update_modified=False)
        self._locations.append(loc.name)
        return loc.name

    # ── TC-WS-MODEL-1 (RED) — model_name='   ' → device_model_name=='' ───────
    def test_ws_model_1_device_model_name_whitespace_only_blank(self):
        """build_asset_scan_info: asset gắn IMM Device Model model_name='   '
        (whitespace-only) → device_model_name=='' (hiện trả '   ')."""
        from assetcore.services.imm00 import build_asset_scan_info
        model = self._make_model_raw("m1", "   ")
        asset = self._make_asset("wsm1", device_model=model)
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["device_model_name"], "",
                         "model_name whitespace-only → '' (khử junk ra mobile-BE)")
        self.assertIsInstance(payload["device_model_name"], str)
        self.assertNotEqual(payload["device_model_name"], "   ",
                            "KHÔNG rò '   ' ra non-Vue consumer/tem")

    # ── TC-WS-LOC-1 (RED) — location_name='\t' → location_name=='' ───────────
    def test_ws_loc_1_location_name_whitespace_only_blank(self):
        """build_asset_scan_info: asset gắn AC Location location_name='\\t'
        (whitespace-only) → location_name=='' (parity model)."""
        from assetcore.services.imm00 import build_asset_scan_info
        loc = self._make_location_raw("l1", "\t")
        asset = self._make_asset("wsl1", location=loc)
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["location_name"], "",
                         "location_name whitespace-only → '' (khử junk)")
        self.assertIsInstance(payload["location_name"], str)
        self.assertNotIn("\t", payload["location_name"])

    # ── TC-WS-MODEL-2 — '  Evita V500  ' → 'Evita V500' (strip 2 đầu, GIỮ giữa)
    def test_ws_model_2_surrounding_ws_stripped_inner_kept(self):
        """model_name='  Evita V500  ' → device_model_name=='Evita V500' (strip
        2 đầu). 'ICU - Tầng 3' chứng minh khoảng-trắng-GIỮA giữ nguyên."""
        from assetcore.services.imm00 import build_asset_scan_info
        model = self._make_model_raw("m2", "  Evita V500  ")
        asset = self._make_asset("wsm2", device_model=model)
        payload = build_asset_scan_info(asset.name)
        self.assertEqual(payload["device_model_name"], "Evita V500",
                         "strip 2 đầu, KHÔNG nuốt nội dung (parity Vòng 45)")
        # location: khoảng-trắng-GIỮA giữ nguyên (KHÔNG over-normalize)
        loc = self._make_location_raw("l2", "  ICU - Tầng 3  ")
        a2 = self._make_asset("wsl2", location=loc)
        p2 = build_asset_scan_info(a2.name)
        self.assertEqual(p2["location_name"], "ICU - Tầng 3",
                         "strip 2 đầu GIỮ khoảng-trắng-giữa 'ICU - Tầng 3'")

    # ── TC-WS-LABEL-1 — build_asset_label_data model_name='\n' → '' ──────────
    def test_ws_label_1_label_data_relation_names_strip(self):
        """build_asset_label_data: model_name='\\n' → device_model_name=='' ;
        location_name='   ' → location_name=='' (parity scan-info, mở rộng 2
        field quan hệ)."""
        from assetcore.services.imm00 import build_asset_label_data
        model = self._make_model_raw("lbl1", "\n")
        loc = self._make_location_raw("lbl1", "   ")
        asset = self._make_asset("wslbl1", device_model=model, location=loc)
        data = build_asset_label_data(asset.name)
        self.assertEqual(data["device_model_name"], "",
                         "model_name whitespace-only → '' trên tem")
        self.assertEqual(data["location_name"], "",
                         "location_name whitespace-only → '' trên tem")
        for k in ("device_model_name", "location_name"):
            self.assertIsInstance(data[k], str)
        self.assertIn("/a/", data["qr_url"])

    # ── TC-WS-BATCH-1 — batch: item hợp lệ strip ; item lỗi GIỮ {name, error} ─
    def test_ws_batch_1_relation_names_strip_error_item_unchanged(self):
        """build_asset_label_data_batch: item hợp lệ location_name='   ' → ''
        ; item lỗi GIỮ NGUYÊN {name, error: 'AC-E001'} (no-regress key)."""
        from assetcore.services.imm00 import build_asset_label_data_batch
        model = self._make_model_raw("b1", "  Dräger V500  ")
        loc = self._make_location_raw("b1", "   ")
        a1 = self._make_asset("wsbatch1", device_model=model, location=loc)
        missing = "AC-ASSET-NONEXISTENT-WS46"
        out = build_asset_label_data_batch([a1.name, missing])
        self.assertEqual(len(out), 2, "giữ index, KHÔNG drop")
        self.assertEqual(out[0]["name"], a1.name)
        self.assertEqual(out[0]["location_name"], "",
                         "item hợp lệ: location_name whitespace-only → ''")
        self.assertEqual(out[0]["device_model_name"], "Dräger V500",
                         "model_name strip 2 đầu (GIỮ khoảng-trắng-giữa)")
        for k in ("device_model_name", "location_name"):
            self.assertIsInstance(out[0][k], str)
        # item lỗi GIỮ NGUYÊN {name, error} — KHÔNG nở key
        self.assertEqual(out[1]["name"], missing)
        self.assertEqual(out[1].get("error"), "AC-E001")
        self.assertEqual(set(out[1].keys()), {"name", "error"},
                         "item lỗi đúng {name, error} (KHÔNG nở key sau helper)")

    # ── TC-NOREG-1 — gán hợp lệ → giữ nguyên văn cả 3 builder ; unassigned → ''
    def test_ws_noreg_valid_relation_kept_unassigned_blank_all_builders(self):
        """model/location gán hợp lệ ('Dräger V500'/'ICU') → giữ nguyên văn cả
        3 builder ; device_model/location rỗng (unassigned) → '' (skip query,
        no-regress)."""
        from assetcore.services.imm00 import (
            build_asset_scan_info, build_asset_label_data,
            build_asset_label_data_batch,
        )
        model = self._make_model_raw("nr", "Dräger V500")
        loc = self._make_location_raw("nr", "ICU")
        asset = self._make_asset("wsnr", device_model=model, location=loc)
        # 3 builder: giữ nguyên văn
        si = build_asset_scan_info(asset.name)
        self.assertEqual(si["device_model_name"], "Dräger V500")
        self.assertEqual(si["location_name"], "ICU")
        lbl = build_asset_label_data(asset.name)
        self.assertEqual(lbl["device_model_name"], "Dräger V500")
        self.assertEqual(lbl["location_name"], "ICU")
        batch = build_asset_label_data_batch([asset.name])
        self.assertEqual(batch[0]["device_model_name"], "Dräger V500")
        self.assertEqual(batch[0]["location_name"], "ICU")
        # unassigned (device_model/location rỗng) → '' (skip query, no-regress)
        bare = self._make_asset("wsbare")
        sib = build_asset_scan_info(bare.name)
        self.assertEqual(sib["device_model_name"], "",
                         "unassigned device_model → '' (skip query no N+1)")
        self.assertEqual(sib["location_name"], "",
                         "unassigned location → '' (skip query)")
        lblb = build_asset_label_data(bare.name)
        self.assertEqual(lblb["device_model_name"], "")
        self.assertEqual(lblb["location_name"], "")
        batchb = build_asset_label_data_batch([bare.name])
        self.assertEqual(batchb[0]["device_model_name"], "")
        self.assertEqual(batchb[0]["location_name"], "")

    # ── _str_or_blank SSoT helper — contract unit-level ─────────────────────
    def test_str_or_blank_helper_contract(self):
        """_str_or_blank: blank/whitespace-only/None/non-str → '' ; else strip()."""
        from assetcore.services.imm00 import _str_or_blank
        self.assertEqual(_str_or_blank(None), "")
        self.assertEqual(_str_or_blank(""), "")
        self.assertEqual(_str_or_blank("   "), "")
        self.assertEqual(_str_or_blank("\t\n "), "")
        self.assertEqual(_str_or_blank(" SN-123 "), "SN-123")
        self.assertEqual(_str_or_blank("High"), "High")
        # non-str (canonical drift / int leak) → '' (str, never None/raw)
        self.assertEqual(_str_or_blank(123), "")
        for v in (None, "", "   ", 123, " x "):
            self.assertIsInstance(_str_or_blank(v), str,
                                  "LUÔN str (parity _date_str_or_none never-None)")


# ──────────────────────────────────────────────────────────────────────────
# A6 / Vòng 31 — chuẩn hoá whitespace tham số `name` ở get_asset_scan_info.
# Parity với nhánh token (Vòng 6 — `_svc_resolve_qr_token` đã `.strip()` SSoT):
# nhánh `name` (api/imm00.py: `elif name and frappe.db.exists(_DT_ASSET, name)`)
# phải `.strip()` 2 đầu TRƯỚC `frappe.db.exists`. asset hợp lệ kèm leading/
# trailing whitespace/newline (deep-link /assets/:id/info, copy-paste, mobile-BE)
# → mở ĐÚNG hồ sơ (200) thay vì 404 GIẢ. CHỈ strip 2 đầu (KHÔNG lowercase/
# transform giữa-chuỗi — KHÔNG over-normalize, parity quy tắc token). Contract
# bất biến: shape payload + 3 lớp bảo mật (RBAC 403 / 404 no-leak / IDOR 403) +
# no-raw-token + read-only no-audit GIỮ NGUYÊN. RED viết TRƯỚC fix.
# ──────────────────────────────────────────────────────────────────────────


class TestAssetScanInfoNameStrip(unittest.TestCase):
    """Vòng 31 — get_asset_scan_info(name=...) strip whitespace 2 đầu TRƯỚC
    exists → parity nhánh token. RED viết TRƯỚC impl."""

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
            "category_name": "Thiết bị Scan NameStrip (V31)",
            "description": "Category cho test name-strip get_asset_scan_info",
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
            "asset_name": f"Máy NameStrip {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"NS-SN-{uniq}",
            "asset_code": f"NS-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    # ── TC-SCAN-NAME-STRIP-01 — name kèm space 2 đầu → 200 payload ĐÚNG ───────
    def test_name_with_leading_trailing_space_returns_200(self):
        """name='  <NAME>  ' → HTTP 200, payload['name']==<NAME>, payload đầy đủ.
        [RED trước fix = 404 vì exists() so chuỗi THÔ kèm khoảng trắng]."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("space", next_pm_date=add_days(nowdate(), 30))
        resp = get_asset_scan_info(name=f"  {asset.name}  ")
        self.assertTrue(resp["success"],
                        "name hợp lệ kèm space 2 đầu → 200 (parity nhánh token)")
        data = resp["data"]
        self.assertEqual(data["name"], asset.name,
                         "payload['name'] = name asset SẠCH (không kèm whitespace)")
        self.assertEqual(data["asset_code"], asset.asset_code)
        for k in self._CORE_KEYS:
            self.assertIn(k, data, f"payload scan-info PHẢI có '{k}'")

    # ── TC-SCAN-NAME-STRIP-02 — newline/tab 2 đầu → 200 (mọi whitespace) ──────
    def test_name_with_newline_tab_returns_200(self):
        """name='<NAME>\\n\\t' → 200. strip() bắt MỌI whitespace 2 đầu (newline/
        tab), KHÔNG chỉ space (mobile-BE/copy-paste hay kèm '\\n')."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("nlt")
        resp = get_asset_scan_info(name=f"\n\t{asset.name}\n\t")
        self.assertTrue(resp["success"],
                        "name kèm newline/tab 2 đầu → 200 (strip mọi whitespace)")
        self.assertEqual(resp["data"]["name"], asset.name)

    # ── TC-SCAN-NAME-STRIP-03 — toàn whitespace → 404 leak-safe, no full-scan ─
    def test_name_all_whitespace_returns_404_no_full_scan(self):
        """name='   ' (toàn whitespace) → sau strip = rỗng → 404 _ERR_ASSET_NOT_
        FOUND leak-safe, KHÔNG query toàn bảng, KHÔNG 500/traceback."""
        from assetcore.api.imm00 import get_asset_scan_info, _ERR_ASSET_NOT_FOUND
        # tạo sẵn 1 asset để bảo đảm bảng KHÔNG rỗng — nếu impl full-scan/lỏng
        # guard, asset này có thể bị resolve nhầm → assertFalse sẽ bắt được.
        self._make_asset("guard")
        resp = get_asset_scan_info(name="   ")
        self.assertFalse(resp["success"], "toàn whitespace → KHÔNG success")
        self.assertEqual(resp["http_status"], 404,
                         "toàn whitespace → 404, KHÔNG 500/traceback")
        self.assertEqual(resp["error"], _ERR_ASSET_NOT_FOUND,
                         "404 leak-safe — KHÔNG phân biệt 'sai định dạng' vs 'không có'")
        self.assertFalse((resp.get("data") or {}).get("asset_code"),
                         "KHÔNG resolve nhầm asset nào (KHÔNG full-scan)")

    # ── TC-SCAN-NAME-STRIP-04 — whitespace GIỮA = hỏng thật → 404 ─────────────
    def test_name_inner_whitespace_returns_404(self):
        """name='A 042' (space GIỮA) sau strip 2 đầu VẪN không khớp asset thật →
        404. CHỈ strip leading/trailing, KHÔNG lowercase/transform giữa-chuỗi
        (parity quy tắc token Vòng 6 — KHÔNG over-normalize)."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("inner")
        # chèn 1 space vào GIỮA name thật → KHÔNG còn là id hợp lệ.
        mangled = asset.name[:3] + " " + asset.name[3:]
        resp = get_asset_scan_info(name=mangled)
        self.assertFalse(resp["success"],
                         "space GIỮA = id hỏng thật → KHÔNG success")
        self.assertEqual(resp["http_status"], 404,
                         "space GIỮA → 404 (KHÔNG transform giữa-chuỗi)")

    # ── TC-SCAN-NAME-STRIP-05 (no-regress) — name SẠCH → 200 payload bất biến ─
    def test_name_clean_returns_200_payload_unchanged(self):
        """name='<NAME>' sạch (không whitespace) → 200 payload bất biến — shape
        + field guard KHÔNG hồi quy sau khi thêm strip()."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("clean", next_pm_date=add_days(nowdate(), 15))
        resp = get_asset_scan_info(name=asset.name)
        self.assertTrue(resp["success"], "name sạch → 200 (no-regress)")
        data = resp["data"]
        self.assertEqual(data["name"], asset.name)
        self.assertEqual(data["asset_code"], asset.asset_code)
        self.assertEqual(data["lifecycle_status"], "Active",
                         "BE trả mã canonical (FE dịch SSoT) — KHÔNG nhãn VI thô")
        for k in self._CORE_KEYS:
            self.assertIn(k, data, f"payload scan-info PHẢI có '{k}'")

    # ── TC-SCAN-NAME-STRIP-06 (token no-fork) — token kèm space → 200 ─────────
    def test_token_with_whitespace_no_fork_still_200(self):
        """token='  <token>  ' → 200. Nhánh token strip ở SERVICE (Vòng 6) KHÔNG
        bị đụng/double-strip bởi fix nhánh name — parity giữ, KHÔNG lệch."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("tokfork")
        resp = get_asset_scan_info(token=f"  {asset.qr_token}\n")
        self.assertTrue(resp["success"],
                        "token kèm whitespace → 200 (service strip Vòng 6 nguyên vẹn)")
        self.assertEqual(resp["data"]["name"], asset.name)

    # ── TC-SCAN-NAME-STRIP-07 (IDOR parity) — vendor ngoài scope + name space →403
    def test_vendor_out_of_scope_with_whitespace_name_forbidden(self):
        """vendor ngoài scope, name kèm whitespace → 403. assert_vendor_can_access
        VẪN chặn SAU strip+exists (resolve được asset → IDOR guard chạy), KHÔNG
        leak payload. Strip KHÔNG bypass lớp bảo mật."""
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("idorns")
        asset_name = asset.name
        vendor_email = "vendor_v31_namestrip_idor@example.com"
        if frappe.db.exists("User", vendor_email):
            frappe.delete_doc("User", vendor_email, force=True,
                              ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": vendor_email,
            "first_name": "Vendor V31 NameStrip IDOR", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        u.add_roles("Vendor Engineer", "Repair User")
        frappe.db.commit()
        frappe.set_user(vendor_email)
        try:
            resp = get_asset_scan_info(name=f"  {asset_name}  ")
            self.assertFalse(resp["success"],
                             "vendor ngoài scope (dù name kèm whitespace) → KHÔNG success")
            self.assertEqual(resp["http_status"], 403,
                             "vendor ngoài scope → 403 IDOR (SAU strip+exists)")
            self.assertNotIn("asset_code", resp.get("data") or {},
                             "KHÔNG leak payload asset ngoài scope")
        finally:
            frappe.set_user("Administrator")
            if frappe.db.exists("User", vendor_email):
                frappe.delete_doc("User", vendor_email,
                                  force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── TC-SCAN-NAME-STRIP-08 (revert-proof LL-TEST-26) — strip thật sự cần ───
    def test_strip_is_load_bearing_revert_proof(self):
        """Revert-proof: chứng minh strip() là LOAD-BEARING. Mô phỏng nhánh name
        KHÔNG strip (`name THÔ` + exists) → asset hợp lệ kèm whitespace KHÔNG
        khớp (RED giả lập); CÓ strip → khớp. Nếu ai gỡ .strip() ở impl, TC-01/02
        sẽ ĐỎ — test này khoá ý nghĩa cụ thể của strip 2 đầu."""
        from assetcore.api.imm00 import _DT_ASSET
        asset = self._make_asset("revert")
        raw = f"  {asset.name}  "
        # KHÔNG strip → exists THÔ thất bại (đây là hành vi 404-giả đã sửa).
        self.assertFalse(frappe.db.exists(_DT_ASSET, raw),
                         "name THÔ kèm whitespace KHÔNG khớp exists → 404 giả nếu quên strip")
        # CÓ strip → exists khớp (đây là hành vi đúng sau fix).
        self.assertTrue(frappe.db.exists(_DT_ASSET, raw.strip()),
                        "name SAU strip 2 đầu khớp exists → resolve đúng asset")


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

    # Field hiện có của payload scan-info (regression: KHÔNG thêm/bớt ngoài
    # đúng 1 field pm_overdue mới). Vòng 37 (D5 — NĐ98): + manufacturer_sn
    # (Số serial NSX, định danh truy xuất) vào whitelist field cốt lõi. Vòng 38:
    # + risk_classification (phân loại rủi ro enum, read-only) vào whitelist —
    # parity manufacturer_sn (raw enum SSoT, FE dịch VI).
    _EXISTING_KEYS = {
        "name", "asset_code", "asset_name", "manufacturer_sn", "risk_classification",
        "device_model_name", "location_name", "department_name", "lifecycle_status",
        "recent_maintenance", "next_pm_date",
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

    # ── Vòng 11 — next_pm_date là str|None ('YYYY-MM-DD'/None), parity với ────
    # next_calibration_date (FR-00-86 / 07 §III.6.f-PMDATESTR). Mirror chính xác
    # test_payload_has_calibration_fields_9_fields_intact (chiều hiệu chuẩn).
    def test_scan_info_next_pm_date_is_str_or_none(self):
        from frappe.utils import getdate
        past = add_days(nowdate(), -1)
        asset = self._make_asset("pmdatestr", next_pm_date=past)
        data = self._scan(asset)
        self.assertIsInstance(
            data["next_pm_date"], str,
            "next_pm_date PHẢI là str (KHÔNG còn datetime.date object thô)")
        self.assertEqual(
            data["next_pm_date"], getdate(past).strftime("%Y-%m-%d"),
            "next_pm_date == getdate(...).strftime('%Y-%m-%d') ('YYYY-MM-DD')")

    def test_scan_info_next_pm_date_none_when_null(self):
        asset = self._make_asset("pmdatenull")  # KHÔNG set next_pm_date
        data = self._scan(asset)
        self.assertIsNone(
            data["next_pm_date"],
            "next_pm_date rỗng/NULL → None (KHÔNG raise, KHÔNG '')")

    def test_scan_info_next_pm_date_type_parity_with_calibration(self):
        """Vòng 11 — CHỐT đối xứng: trong CÙNG 1 payload cả next_pm_date lẫn
        next_calibration_date đều là (str | None) qua _date_str_or_none (KHÔNG
        còn date object thô ở 1 nhánh). Khoá no-asymmetry (FR-00-86)."""
        asset = self._make_asset(
            "pmcalparity",
            next_pm_date=add_days(nowdate(), -1),
            next_calibration_date=add_days(nowdate(), -1),
        )
        data = self._scan(asset)
        self.assertIsInstance(
            data["next_pm_date"], (str, type(None)),
            "next_pm_date PHẢI là str|None (parity với next_calibration_date)")
        self.assertIsInstance(
            data["next_calibration_date"], (str, type(None)),
            "next_calibration_date PHẢI là str|None (đối xứng next_pm_date)")

    def test_scan_info_pm_overdue_unaffected_by_str_normalize(self):
        """INVARIANT: cờ pm_overdue derive từ RAW row TRƯỚC normalize string —
        KHÔNG hồi quy khi next_pm_date đổi sang str|None (Vòng 11)."""
        from frappe.utils import getdate
        past = add_days(nowdate(), -1)
        asset = self._make_asset("pmdateinv", next_pm_date=past)
        data = self._scan(asset)
        self.assertIs(data["pm_overdue"], True,
                      "past+active → pm_overdue=True (derive từ raw, KHÔNG đổi)")
        self.assertIsInstance(data["next_pm_date"], str)
        self.assertEqual(data["next_pm_date"],
                         getdate(past).strftime("%Y-%m-%d"))

    def test_scan_info_payload_shape_unchanged_after_pmdate_str(self):
        """Field-whitelist KHÔNG đổi — chỉ đổi KIỂU value next_pm_date, KHÔNG
        thêm/bớt key (9 FR-00-85 + 2 calibration + available_actions)."""
        asset = self._make_asset("pmdateshape", next_pm_date=add_days(nowdate(), -1))
        data = self._scan(asset)
        self.assertEqual(
            set(data.keys()),
            self._EXISTING_KEYS | {"pm_overdue"} | self._CALIBRATION_KEYS
            | self._WARRANTY_KEYS | {"available_actions"},
            "shape ổn định: KHÔNG thêm/bớt key khi next_pm_date thành str|None")

    # ── Regression — giữ ĐÚNG 8 field cũ + pm_overdue + 2 field hiệu chuẩn ────
    # FR-00-86: payload bổ sung next_calibration_date + calibration_overdue (Vòng
    # 28 B) — KHÔNG mất/đổi field cũ. Whitelist mở rộng đúng 2 key calibration.
    _CALIBRATION_KEYS = {"next_calibration_date", "calibration_overdue"}
    # Vòng 48 — payload bổ sung đúng 2 key warranty (trạng thái BẢO HÀNH).
    _WARRANTY_KEYS = {"warranty_expiry_date", "warranty_expired"}

    def test_scan_info_payload_keeps_8_existing_fields_plus_pm_overdue(self):
        asset = self._make_asset("shape", next_pm_date=add_days(nowdate(), -1))
        data = self._scan(asset)
        for k in self._EXISTING_KEYS:
            self.assertIn(k, data, f"payload PHẢI giữ field cũ '{k}'")
        self.assertEqual(
            set(data.keys()),
            self._EXISTING_KEYS | {"pm_overdue"} | self._CALIBRATION_KEYS
            | self._WARRANTY_KEYS | {"available_actions"},
            "payload = 8 field cũ + pm_overdue + 2 field hiệu chuẩn + "
            "2 field bảo hành + available_actions (R1 §D2 — KHÔNG dư field khác)",
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


# ──────────────────────────────────────────────────────────────────────────
# Vòng 48 (A6 — TRẠNG THÁI BẢO HÀNH): build_asset_scan_info bổ sung 2 KEY MỚI
# warranty_expiry_date (str|None 'YYYY-MM-DD' qua _date_str_or_none, parity
# next_pm_date/next_calibration_date) + warranty_expired (bool, derive SERVER-
# SIDE qua helper MỚI _is_warranty_expired). KTV biết "còn/hết bảo hành" TRƯỚC
# khi báo hỏng/tạo CM (affordance chi phí sửa chữa). KHÁC pm/cal overdue:
# _is_warranty_expired ĐỘC LẬP lifecycle_status (bảo hành = sự kiện HỢP ĐỒNG —
# Out-of-Service/Decommissioned VẪN có thể còn/hết bảo hành → KHÔNG exempt).
# Đọc field thật AC Asset.warranty_expiry_date trong CÙNG get_value (KHÔNG N+1).
# RED viết TRƯỚC impl.
# ──────────────────────────────────────────────────────────────────────────


class TestAssetScanInfoWarranty(unittest.TestCase):
    """A6 (Vòng 48) — trạng thái BẢO HÀNH màn quét QR: warranty_expiry_date +
    warranty_expired. Cờ derive THUẦN từ ngày server (no client-clock). Helper
    _is_warranty_expired ĐỘC LẬP lifecycle (khác pm/cal overdue). RED trước impl."""

    # KEY CŨ của payload — no-regress khi thêm đúng 2 key warranty mới. CR-19:
    # += department_name (denorm AC Asset.department, parity location_name).
    _LEGACY_KEYS = {
        "name", "asset_code", "asset_name", "manufacturer_sn", "risk_classification",
        "lifecycle_status", "device_model_name", "location_name", "department_name",
        "next_pm_date", "next_calibration_date", "recent_maintenance",
        "pm_overdue", "calibration_overdue", "available_actions",
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
            "category_name": "Thiết bị Bảo hành (A6 V48)",
            "description": "Category cho test warranty scan-info",
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
            "asset_name": f"Máy Warranty {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"WAR-SN-{uniq}",
            "asset_code": f"WAR-ASSET-{uniq}",
            "lifecycle_status": status,
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _scan(self, asset):
        from assetcore.api.imm00 import get_asset_scan_info
        return get_asset_scan_info(token=asset.qr_token)["data"]

    # ── BE-WAR-1: quá khứ → True ─────────────────────────────────────────────
    def test_is_warranty_expired_past_true(self):
        from assetcore.services.imm00 import _is_warranty_expired
        self.assertIs(_is_warranty_expired("2020-01-01"), True,
                      "ngày bảo hành quá khứ → hết bảo hành (True)")
        self.assertIs(_is_warranty_expired(add_days(nowdate(), -1)), True,
                      "hôm qua < hôm nay (strict <) → True")

    # ── BE-WAR-2: hôm nay → False (strict <, hôm nay CHƯA hết hạn) ────────────
    def test_is_warranty_expired_today_false_strict(self):
        from assetcore.services.imm00 import _is_warranty_expired
        self.assertIs(_is_warranty_expired(nowdate()), False,
                      "hôm nay == hạn → CHƯA hết bảo hành (strict <, KHÔNG <=)")

    # ── BE-WAR-3: tương lai → False ──────────────────────────────────────────
    def test_is_warranty_expired_future_false(self):
        from assetcore.services.imm00 import _is_warranty_expired
        self.assertIs(_is_warranty_expired(add_days(nowdate(), 30)), False,
                      "hạn tương lai → còn bảo hành (False)")

    # ── BE-WAR-4: None / '' → False (KHÔNG raise) ────────────────────────────
    def test_is_warranty_expired_none_and_blank_false(self):
        from assetcore.services.imm00 import _is_warranty_expired
        self.assertIs(_is_warranty_expired(None), False, "None → False")
        self.assertIs(_is_warranty_expired(""), False, "'' → False")

    # ── BE-WAR-5: NO-EXEMPT — độc lập lifecycle (KHÁC pm/cal overdue) ─────────
    def test_is_warranty_expired_independent_of_lifecycle(self):
        """_is_warranty_expired KHÔNG nhận/áp lifecycle_status. Thiết bị
        Out of Service / Decommissioned với warranty quá khứ → VẪN True
        (bảo hành = sự kiện HỢP ĐỒNG độc lập lifecycle, KHÔNG có *_EXEMPT
        như _is_pm_overdue/_is_calibration_overdue)."""
        from assetcore.services.imm00 import _is_warranty_expired
        from assetcore.services.shared.constants import AssetStatus
        past = add_days(nowdate(), -30)
        # helper KHÔNG nhận status → True bất kể trạng thái:
        self.assertIs(_is_warranty_expired(past), True)
        # và qua payload đầy đủ: asset BLOCKED_FOR_WO + warranty quá khứ → warranty_expired True
        for i, status in enumerate(AssetStatus.BLOCKED_FOR_WO):
            with self.subTest(status=status):
                asset = self._make_asset(f"blk{i}", status=status,
                                         warranty_expiry_date=past)
                data = self._scan(asset)
                self.assertIs(data["warranty_expired"], True,
                              f"status '{status}' (ngừng dùng) NHƯNG warranty quá khứ "
                              "→ warranty_expired=True (KHÔNG exempt như pm/cal overdue)")
                # đối chứng: cùng asset, pm_overdue thì BỊ exempt (False) — chứng minh KHÁC
                self.assertIs(data["pm_overdue"], False,
                              "đối chứng: pm_overdue exempt khi BLOCKED_FOR_WO (≠ warranty)")

    # ── BE-WAR-6: payload field thật → str ISO + warranty_expired bool ────────
    def test_scan_info_warranty_future_str_iso_and_not_expired(self):
        from frappe.utils import getdate
        asset = self._make_asset("future", warranty_expiry_date="2027-05-01")
        data = self._scan(asset)
        self.assertIn("warranty_expiry_date", data, "payload PHẢI có warranty_expiry_date")
        self.assertIsInstance(data["warranty_expiry_date"], str,
                              "warranty_expiry_date là str ISO (KHÔNG date object/giờ)")
        self.assertEqual(data["warranty_expiry_date"], "2027-05-01",
                         "warranty_expiry_date == 'YYYY-MM-DD' (KHÔNG datetime thô)")
        # parity _date_str_or_none: không leak phần giờ
        self.assertEqual(data["warranty_expiry_date"],
                         getdate("2027-05-01").strftime("%Y-%m-%d"))
        self.assertIs(data["warranty_expired"], False,
                      "2027 (tương lai) → còn bảo hành (False)")

    # ── BE-WAR-7: warranty rỗng → None + warranty_expired False ──────────────
    def test_scan_info_warranty_empty_none_and_not_expired(self):
        asset = self._make_asset("empty")  # KHÔNG set warranty_expiry_date
        data = self._scan(asset)
        self.assertIn("warranty_expiry_date", data, "key luôn hiện diện (KHÔNG KeyError)")
        self.assertIsNone(data["warranty_expiry_date"],
                          "warranty rỗng/NULL → None (parity next_pm_date)")
        self.assertIs(data["warranty_expired"], False,
                      "warranty NULL → warranty_expired=False (KHÔNG raise)")

    # ── BE-WAR-8: 13 key cũ no-regress + đúng 2 key mới + no-leak ─────────────
    def test_scan_info_warranty_keys_no_regress_no_sensitive_leak(self):
        asset = self._make_asset("noregress", warranty_expiry_date="2020-01-01",
                                 gross_purchase_amount=123_000_000)
        data = self._scan(asset)
        # key cũ GIỮ NGUYÊN
        missing = self._LEGACY_KEYS - set(data.keys())
        self.assertFalse(missing, f"key cũ PHẢI giữ nguyên, thiếu: {missing}")
        # đúng 2 key warranty mới
        self.assertIn("warranty_expiry_date", data)
        self.assertIn("warranty_expired", data)
        # payload = key cũ + 2 mới (KHÔNG dư field khác)
        self.assertEqual(
            set(data.keys()), self._LEGACY_KEYS | {"warranty_expiry_date", "warranty_expired"},
            "payload = key cũ + đúng 2 key warranty mới (KHÔNG dư/thiếu)")
        # KHÔNG leak field tài chính/nhạy cảm
        leaked = self._SENSITIVE_KEYS & set(data.keys())
        self.assertFalse(leaked, f"KHÔNG leak field nhạy cảm: {leaked}")
        # quá khứ → warranty_expired True (nhánh derive được chạy)
        self.assertIs(data["warranty_expired"], True)

    # ── No-side-effect — derive warranty KHÔNG ghi audit/lifecycle (A2) ───────
    def test_scan_info_warranty_no_side_effect(self):
        asset = self._make_asset("noeffect", warranty_expiry_date="2020-01-01")
        before_audit = frappe.db.count("IMM Audit Trail", {"asset": asset.name})
        before_ale = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        data = self._scan(asset)
        self.assertIs(data["warranty_expired"], True)
        self.assertEqual(frappe.db.count("IMM Audit Trail", {"asset": asset.name}),
                         before_audit, "derive warranty KHÔNG ghi IMM Audit Trail")
        self.assertEqual(frappe.db.count("Asset Lifecycle Event", {"asset": asset.name}),
                         before_ale, "derive warranty KHÔNG ghi Asset Lifecycle Event")


class TestAssetScanInfoCalibrationOverdue(unittest.TestCase):
    """A6 hardening (FR-00-86 / BR-00-37, Vòng 28 B) — derive calibration_overdue
    server-side. Chiều HIỆU CHUẨN song song với pm_overdue: FE CHỈ render cờ
    (KHÔNG so ngày client → chống lệch timezone). RED viết TRƯỚC impl.

    next_calibration_date là field AC Asset đã có (ac_asset.json:453, Date
    read_only) — ZERO schema delta. KHÔNG mock getdate/nowdate; set ngày THẬT
    quanh nowdate() để đo đúng biên strict ``<``."""

    # Field hiện có của payload scan-info SAU khi đã thêm pm_overdue (regression:
    # GIỮ NGUYÊN tên + giá trị khi thêm 2 field hiệu chuẩn). Vòng 37 (D5 — NĐ98):
    # + manufacturer_sn (Số serial NSX, định danh truy xuất) vào whitelist. Vòng 38:
    # + risk_classification (phân loại rủi ro enum, read-only) — parity manufacturer_sn.
    _EXISTING_KEYS = {
        "name", "asset_code", "asset_name", "manufacturer_sn", "risk_classification",
        "device_model_name", "location_name", "department_name", "lifecycle_status",
        "recent_maintenance", "next_pm_date", "pm_overdue",
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
            self._EXISTING_KEYS | {"next_calibration_date", "calibration_overdue"}
            | {"warranty_expiry_date", "warranty_expired"}
            | {"available_actions"},
            "payload = 9 field cũ + 2 field hiệu chuẩn + 2 field bảo hành + "
            "available_actions (R1 §D2 — KHÔNG dư/thiếu field khác)",
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
# R1 QR-SCAN-ACTION (ADR-IMM00-QR-SCAN-ACTION §D2) — màn quét QR emit
# available_actions = capability ∩ lifecycle derive SERVER-SIDE qua 1 predicate
# SSoT (_scan_action_specs + _lifecycle_allows). 4 action map 1-1 cap (D1):
# report_failure→corrective.create, request_pm→pm.create, request_cm→repair.create,
# request_calibration→calibration.create. Bảng lifecycle×action (D2):
# Active/Commissioned/Under Maintenance/Under Repair/Calibrating → 4 enabled;
# Out of Service → CHỈ report_failure+request_cm; Decommissioned → 0; Draft → 0.
# reason ưu tiên lifecycle > capability. Payload read-only cũ (11 key) GIỮ NGUYÊN.
# no-raw-token parity GIỮ. RED viết TRƯỚC impl.
# ──────────────────────────────────────────────────────────────────────────
class TestScanInfoAvailableActions(unittest.TestCase):
    """R1 §D2 — available_actions = has_cap ∩ lifecycle_allows (SSoT 1 predicate).

    Administrator có MỌI DocPerm ⇒ rbac.can(*) True cho cả 4 cap → dùng để đo
    nhánh lifecycle thuần (không nhiễu capability). Test thiếu-cap monkeypatch
    rbac.can (module attribute service tham chiếu) để ép 1 cap False. KHÔNG mock
    getdate/nowdate. RED viết TRƯỚC impl."""

    _ACTION_KEYS = {"report_failure", "request_pm", "request_cm",
                    "request_calibration"}
    _ROUTES = {"IncidentCreate", "PMWorkOrderCreate", "CMCreate",
               "CalibrationCreate"}
    _SHAPE_KEYS = {"key", "label", "route", "enabled", "reason"}
    # 11 key read-only cũ (contract A6) — regression guard không đổi.
    _EXISTING_PAYLOAD_KEYS = {
        "name", "asset_code", "asset_name", "lifecycle_status",
        "device_model_name", "location_name", "next_pm_date",
        "next_calibration_date", "recent_maintenance", "pm_overdue",
        "calibration_overdue",
    }
    _REASON_DECOM = "Thiết bị đã thanh lý"
    _REASON_OOS = ("Thiết bị đang ngừng hoạt động — chỉ cho phép báo hỏng / "
                   "yêu cầu sửa chữa")
    _REASON_DRAFT = "Thiết bị chưa đưa vào vận hành"
    _REASON_NO_CAP = "Bạn không có quyền thực hiện thao tác này"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Scan Actions (R1)",
            "description": "Category cho test available_actions scan-info",
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
            "asset_name": f"Máy ScanAction {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"SA-SN-{uniq}",
            "asset_code": f"SA-ASSET-{uniq}",
            "lifecycle_status": status,
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _actions(self, asset):
        from assetcore.services.imm00 import build_asset_scan_info
        payload = build_asset_scan_info(asset.name)
        self.assertIn("available_actions", payload,
                      "payload PHẢI có key available_actions")
        return {a["key"]: a for a in payload["available_actions"]}

    # ── Active + đủ 4 cap → 4 enabled, reason rỗng ──────────────────────────
    def test_active_full_cap_4_enabled(self):
        from assetcore.services.imm00 import _scan_action_specs
        asset = self._make_asset("active", status="Active")
        actions = self._actions(asset)
        self.assertEqual(set(actions), self._ACTION_KEYS,
                         "đủ 4 action key canonical")
        specs = {s["key"]: s for s in _scan_action_specs()}
        for key, a in actions.items():
            self.assertIs(a["enabled"], True,
                          f"Active + đủ cap → {key} enabled=True")
            self.assertEqual(a["reason"], "",
                             f"enabled=True → reason rỗng ({key})")
            self.assertEqual(a["label"], specs[key]["label"],
                             f"label khớp _scan_action_specs ({key})")
            self.assertEqual(a["route"], specs[key]["route"],
                             f"route khớp _scan_action_specs ({key})")

    def test_commissioned_full_cap_4_enabled(self):
        asset = self._make_asset("commi", status="Commissioned")
        for key, a in self._actions(asset).items():
            self.assertIs(a["enabled"], True, f"Commissioned → {key} enabled")
            self.assertEqual(a["reason"], "")

    # ── Decommissioned → 4 disabled, reason 'đã thanh lý' ───────────────────
    def test_decommissioned_all_disabled(self):
        asset = self._make_asset("decom", status="Decommissioned")
        for key, a in self._actions(asset).items():
            self.assertIs(a["enabled"], False,
                          f"Decommissioned → {key} enabled=False")
            self.assertEqual(a["reason"], self._REASON_DECOM,
                             f"Decommissioned reason ({key})")

    # ── Out of Service → CHỈ report_failure + request_cm enabled ────────────
    def test_out_of_service_only_report_and_cm(self):
        asset = self._make_asset("oos", status="Out of Service")
        actions = self._actions(asset)
        self.assertIs(actions["report_failure"]["enabled"], True,
                      "OoS → report_failure enabled")
        self.assertEqual(actions["report_failure"]["reason"], "")
        self.assertIs(actions["request_cm"]["enabled"], True,
                      "OoS → request_cm enabled")
        self.assertEqual(actions["request_cm"]["reason"], "")
        for key in ("request_pm", "request_calibration"):
            self.assertIs(actions[key]["enabled"], False,
                          f"OoS → {key} disabled")
            self.assertEqual(actions[key]["reason"], self._REASON_OOS,
                             f"OoS disabled reason ({key})")

    # ── Draft → 4 disabled 'chưa đưa vào vận hành' ──────────────────────────
    def test_draft_all_disabled(self):
        asset = self._make_asset("draft", status="Draft")
        for key, a in self._actions(asset).items():
            self.assertIs(a["enabled"], False, f"Draft → {key} disabled")
            self.assertEqual(a["reason"], self._REASON_DRAFT,
                             f"Draft reason ({key})")

    # ── Status rỗng/lạ + đủ cap → 4 disabled reason _LIFECYCLE_REASON_UNKNOWN ──
    # (D9 R1 §IV.18 — bịt lỗ hổng nút disabled-không-lý-do khi lifecycle_status
    # rỗng ''/mã LẠ ngoài enum AssetStatus + user CÓ capability.) RED trước fix:
    # code hiện tại trả reason="" khi has_cap=True (rơi cuối _lifecycle_reason).
    def test_unknown_status_disabled_has_nonempty_reason(self):
        from assetcore.services.imm00 import _LIFECYCLE_REASON_UNKNOWN
        for status in ("", "ZzUnknown"):
            asset = self._make_asset("unk", status="Active")
            frappe.db.set_value("AC Asset", asset.name, "lifecycle_status",
                                status, update_modified=False)
            actions = self._actions(asset)
            self.assertEqual(set(actions), self._ACTION_KEYS,
                             f"đủ 4 action key (status={status!r})")
            for key, a in actions.items():
                self.assertIs(a["enabled"], False,
                              f"status rỗng/lạ → {key} disabled (status={status!r})")
                self.assertNotEqual(a["reason"], "",
                                    f"disabled ⟹ reason KHÔNG rỗng ({key}, {status!r})")
                self.assertEqual(a["reason"], _LIFECYCLE_REASON_UNKNOWN,
                                 f"status rỗng/lạ + đủ cap → reason hằng UNKNOWN "
                                 f"({key}, status={status!r})")

    # ── Bất biến: status rỗng/lạ → mọi action disabled PHẢI kèm reason != '' ──
    def test_unknown_status_invariant_no_disabled_empty_reason(self):
        for status in ("", "GARBAGE"):
            asset = self._make_asset("inv", status="Active")
            frappe.db.set_value("AC Asset", asset.name, "lifecycle_status",
                                status, update_modified=False)
            for key, a in self._actions(asset).items():
                if a["enabled"] is False:
                    self.assertNotEqual(
                        a["reason"], "",
                        f"(not enabled) ⟹ reason != '' ({key}, status={status!r})")

    # ── Bất biến TỔNG QUÁT: ∀ status × {có/thiếu cap} disabled ⟹ reason != '' ─
    # + chống hồi quy: 5 status đã biết reason KHÔNG đổi (byte-for-byte).
    def test_available_actions_invariant_all_status_disabled_nonempty(self):
        from assetcore.services import imm00 as svc
        from assetcore.services.imm00 import _LIFECYCLE_REASON_UNKNOWN
        known_reason = {
            "Decommissioned": self._REASON_DECOM,
            "Draft": self._REASON_DRAFT,
        }
        statuses = ["", "GARBAGE", "Active", "Commissioned",
                    "Decommissioned", "Out of Service", "Draft"]
        orig_can = svc.rbac.can

        def _no_cap(cap, doc=None):
            return False

        for status in statuses:
            for has_cap in (True, False):
                asset = self._make_asset("allinv", status="Active")
                frappe.db.set_value("AC Asset", asset.name, "lifecycle_status",
                                    status, update_modified=False)
                if not has_cap:
                    svc.rbac.can = _no_cap
                try:
                    actions = self._actions(asset)
                finally:
                    svc.rbac.can = orig_can
                for key, a in actions.items():
                    if a["enabled"] is False:
                        self.assertNotEqual(
                            a["reason"], "",
                            f"(not enabled) ⟹ reason != '' "
                            f"(status={status!r}, has_cap={has_cap}, {key})")
                # Chống hồi quy 5 status đã biết khi ĐỦ cap — reason byte-for-byte.
                if has_cap and status in known_reason:
                    for key, a in actions.items():
                        self.assertEqual(
                            a["reason"], known_reason[status],
                            f"reason {status} KHÔNG đổi ({key})")
                if has_cap and status == "Out of Service":
                    for key in ("request_pm", "request_calibration"):
                        self.assertEqual(actions[key]["reason"], self._REASON_OOS,
                                         f"OoS disabled reason KHÔNG đổi ({key})")
                # Status rỗng/lạ + đủ cap → reason hằng UNKNOWN (không lẫn cũ).
                if has_cap and status in ("", "GARBAGE"):
                    for key, a in actions.items():
                        self.assertEqual(a["reason"], _LIFECYCLE_REASON_UNKNOWN,
                                         f"rỗng/lạ + đủ cap → UNKNOWN ({key})")

    def test_under_maintenance_full_cap_4_enabled(self):
        asset = self._make_asset("um", status="Under Maintenance")
        for key, a in self._actions(asset).items():
            self.assertIs(a["enabled"], True, f"Under Maintenance → {key} enabled")
            self.assertEqual(a["reason"], "")

    def test_calibrating_full_cap_4_enabled(self):
        asset = self._make_asset("calng", status="Calibrating")
        for key, a in self._actions(asset).items():
            self.assertIs(a["enabled"], True, f"Calibrating → {key} enabled")
            self.assertEqual(a["reason"], "")

    # ── Thiếu cap (Active) → action thiếu cap disabled reason quyền ─────────
    def test_missing_capability_disabled_with_reason(self):
        """Active nhưng user THIẾU pm.create (mock rbac.can) → request_pm disabled
        reason quyền; các action có cap vẫn enabled."""
        from assetcore.services import imm00 as svc
        asset = self._make_asset("nocap", status="Active")
        orig_can = svc.rbac.can

        def _fake_can(cap, doc=None):
            if cap == "pm.create":
                return False
            return orig_can(cap, doc=doc)

        svc.rbac.can = _fake_can
        try:
            actions = self._actions(asset)
        finally:
            svc.rbac.can = orig_can
        self.assertIs(actions["request_pm"]["enabled"], False,
                      "thiếu pm.create → request_pm disabled")
        self.assertEqual(actions["request_pm"]["reason"], self._REASON_NO_CAP,
                         "reason thiếu cap")
        for key in ("report_failure", "request_cm", "request_calibration"):
            self.assertIs(actions[key]["enabled"], True,
                          f"{key} có cap + Active → enabled")
            self.assertEqual(actions[key]["reason"], "")

    # ── Lifecycle > capability: Decommissioned + thiếu cap → reason lifecycle ─
    def test_lifecycle_reason_priority_over_capability(self):
        from assetcore.services import imm00 as svc
        asset = self._make_asset("prio", status="Decommissioned")

        def _fake_can(cap, doc=None):
            return False  # thiếu TẤT CẢ cap

        orig_can = svc.rbac.can
        svc.rbac.can = _fake_can
        try:
            actions = self._actions(asset)
        finally:
            svc.rbac.can = orig_can
        for key, a in actions.items():
            self.assertIs(a["enabled"], False, f"{key} disabled")
            self.assertEqual(a["reason"], self._REASON_DECOM,
                             f"ưu tiên lifecycle 'đã thanh lý' KHÔNG reason quyền ({key})")

    # ── Shape & keys chính xác ──────────────────────────────────────────────
    def test_action_shape_and_keys(self):
        asset = self._make_asset("shape", status="Active")
        from assetcore.services.imm00 import build_asset_scan_info
        actions = build_asset_scan_info(asset.name)["available_actions"]
        self.assertEqual(len(actions), 4, "đúng 4 phần tử")
        keys_seen = set()
        for a in actions:
            self.assertEqual(set(a.keys()), self._SHAPE_KEYS,
                             f"shape CHÍNH XÁC {self._SHAPE_KEYS}, không thừa: {a}")
            self.assertIsInstance(a["key"], str)
            self.assertIsInstance(a["label"], str)
            self.assertIsInstance(a["route"], str)
            self.assertIsInstance(a["enabled"], bool)
            self.assertIsInstance(a["reason"], str)
            self.assertIn(a["route"], self._ROUTES, "route ∈ tập route-name D1")
            keys_seen.add(a["key"])
        self.assertEqual(keys_seen, self._ACTION_KEYS,
                         "set key = 4 action canonical")

    def test_capability_map_per_action_d1(self):
        """Mỗi spec map ĐÚNG capability D1 = <domain>.create."""
        from assetcore.services.imm00 import _scan_action_specs
        cap_by_key = {s["key"]: s["capability"] for s in _scan_action_specs()}
        self.assertEqual(cap_by_key, {
            "report_failure": "corrective.create",
            "request_pm": "pm.create",
            "request_cm": "repair.create",
            "request_calibration": "calibration.create",
        })

    def test_spec_routes_are_exactly_the_four_fe_allowlist_names(self):
        """Vòng 20 anti-drift: mọi _SCAN_ACTION_SPECS['route'] ∈ tập 4 route-name
        cố định mà FE allow-list (SCAN_ACTION_ROUTES) PHẢI mirror.

        Đây là SSoT-level guard (đọc thẳng _scan_action_specs, KHÔNG qua runtime
        payload/asset/capability): nếu BE tự thêm route mới (route thứ-5 hoặc đổi
        tên) mà FE chưa kịp đồng bộ allow-list → màn quét QR render nút disabled
        câm (route lạ → _ROUTE_UNAVAILABLE). Test ĐỎ buộc đồng bộ 2 đầu BE↔FE
        trong cùng đổi. KHÔNG đụng api/imm00.py runtime (read-only assert)."""
        from assetcore.services.imm00 import _scan_action_specs
        spec_routes = {s["route"] for s in _scan_action_specs()}
        # bao đúng-bằng: không thiếu (4 CTA chuẩn) + không thừa (route lạ chưa map FE).
        self.assertEqual(spec_routes, self._ROUTES,
                         "route SSoT BE PHẢI == đúng 4 route-name FE allow-list "
                         "mirror (IncidentCreate/PMWorkOrderCreate/CMCreate/"
                         "CalibrationCreate); lệch → đồng bộ FE SCAN_ACTION_ROUTES")

    # ── Regression — 11 key read-only cũ GIỮ NGUYÊN ─────────────────────────
    def test_existing_payload_unchanged(self):
        from assetcore.services.imm00 import build_asset_scan_info
        asset = self._make_asset("regress", status="Active",
                                 next_pm_date=add_days(nowdate(), 30),
                                 next_calibration_date=add_days(nowdate(), 30))
        payload = build_asset_scan_info(asset.name)
        missing = self._EXISTING_PAYLOAD_KEYS - set(payload.keys())
        self.assertFalse(missing, f"payload cũ MẤT key: {missing}")
        self.assertEqual(payload["name"], asset.name)
        self.assertEqual(payload["asset_code"], asset.asset_code)
        self.assertEqual(payload["asset_name"], asset.asset_name)
        self.assertEqual(payload["lifecycle_status"], "Active")
        self.assertIs(payload["pm_overdue"], False)
        self.assertIs(payload["calibration_overdue"], False)

    # ── no-raw-token parity — available_actions KHÔNG chứa qr_token ─────────
    def test_no_raw_token_parity(self):
        from assetcore.api.imm00 import get_asset_scan_info
        asset = self._make_asset("notoken", status="Active")
        data = get_asset_scan_info(token=asset.qr_token)["data"]
        self.assertNotIn("qr_token", data, "payload tổng KHÔNG leak qr_token")
        for a in data["available_actions"]:
            for v in a.values():
                self.assertNotIn("qr_token", str(v),
                                 "available_actions item KHÔNG chứa qr_token")
        # grep toàn payload JSON = 0 occurrence 'qr_token'
        import json as _json
        self.assertNotIn("qr_token", _json.dumps(data, default=str),
                         "grep qr_token trong payload available_actions = 0")

    # ── Status rỗng/lạ → 4 disabled an toàn, KHÔNG KeyError ─────────────────
    def test_unknown_status_safe_default(self):
        from assetcore.services.imm00 import (
            _lifecycle_allows, build_asset_scan_info,
        )
        # White-box: status lạ/rỗng → _lifecycle_allows trả False (KHÔNG KeyError).
        for key in self._ACTION_KEYS:
            self.assertIs(_lifecycle_allows("", key), False,
                          f"status rỗng → {key} không cho phép")
            self.assertIs(_lifecycle_allows("Trạng-thái-lạ", key), False,
                          f"status lạ → {key} không cho phép")
        # Black-box qua payload: status rỗng → 4 disabled, KHÔNG crash.
        asset = self._make_asset("unkstat", status="Active")
        frappe.db.set_value("AC Asset", asset.name, "lifecycle_status", "",
                            update_modified=False)
        payload = build_asset_scan_info(asset.name)
        actions = {a["key"]: a for a in payload["available_actions"]}
        self.assertEqual(set(actions), self._ACTION_KEYS)
        for a in actions.values():
            self.assertIs(a["enabled"], False,
                          "status rỗng → mọi action disabled (safe default)")
            self.assertIsInstance(a["reason"], str)
            # D9: disabled ⟹ reason KHÔNG rỗng (Administrator = đủ cap → UNKNOWN).
            self.assertNotEqual(a["reason"], "",
                                "status rỗng disabled PHẢI kèm reason VI != ''")

    # ── SSoT: Out of Service đọc constants, KHÔNG literal rải rác ───────────
    def test_no_inline_literal_status_check_in_derive(self):
        """grep literal-status-check quanh derive available_actions = 0.

        Thân build_asset_scan_info KHÔNG được inline `if status == 'Out of
        Service'` (hoặc 'Decommissioned'/'Draft'/'Active'); toàn bộ rẽ-nhánh
        lifecycle dồn vào _lifecycle_allows/_lifecycle_reason (SSoT predicate)."""
        import inspect
        from assetcore.services.imm00 import build_asset_scan_info
        src = inspect.getsource(build_asset_scan_info)
        for literal in ("'Out of Service'", '"Out of Service"',
                        "'Decommissioned'", '"Decommissioned"',
                        "'Draft'", '"Draft"'):
            self.assertNotIn(literal, src,
                             f"build_asset_scan_info KHÔNG inline literal {literal} "
                             "(dùng _lifecycle_allows SSoT)")


# ──────────────────────────────────────────────────────────────────────────
# SSoT overdue (PM + hiệu chuẩn) cho màn ADMIN-DETAIL (get_asset) — Vòng 3 QR.
# get_asset(name) (api/imm00.py:244) phải trả 2 cờ bool pm_overdue +
# calibration_overdue derive bằng CHÍNH _is_pm_overdue/_is_calibration_overdue
# (KHÔNG re-implement so ngày) → 2 màn (quét-QR ↔ admin-detail) CÙNG 1 SSoT
# server-flag. Parity no-raw-token GIỮ NGUYÊN (payload KHÔNG leak qr_token qua
# _strip_qr_token). RED viết TRƯỚC impl.
# ──────────────────────────────────────────────────────────────────────────
class TestGetAssetOverdueFlags(unittest.TestCase):
    """get_asset(name) emit pm_overdue + calibration_overdue server-flag (SSoT).

    Đồng bộ với màn quét-QR (build_asset_scan_info) — derive cùng deriver
    tz-safe + exempt BLOCKED_FOR_WO. FE admin-detail CHỈ render cờ, KHÔNG so
    ngày client. KHÔNG mock getdate/nowdate; set ngày THẬT quanh nowdate()."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị get_asset Overdue",
            "description": "Category cho test get_asset overdue flags",
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
            "asset_name": f"Máy GAOverdue {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"GAO-SN-{uniq}",
            "asset_code": f"GAO-ASSET-{uniq}",
            "lifecycle_status": status,
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _get(self, asset):
        from assetcore.api.imm00 import get_asset
        return get_asset(asset.name)["data"]

    # ── Nhánh 1: quá khứ + Active → cờ True ───────────────────────────────────
    def test_get_asset_emits_pm_overdue_true(self):
        asset = self._make_asset("pm-true", status="Active",
                                 next_pm_date=add_days(nowdate(), -1))
        data = self._get(asset)
        self.assertIn("pm_overdue", data, "payload get_asset PHẢI có pm_overdue")
        self.assertIs(data["pm_overdue"], True,
                      "next_pm_date hôm-qua ∧ Active → pm_overdue=True")

    def test_get_asset_emits_calibration_overdue_true(self):
        asset = self._make_asset("cal-true", status="Active",
                                 next_calibration_date=add_days(nowdate(), -1))
        data = self._get(asset)
        self.assertIn("calibration_overdue", data,
                      "payload get_asset PHẢI có calibration_overdue")
        self.assertIs(data["calibration_overdue"], True,
                      "next_calibration_date quá khứ ∧ Active → True")

    # ── Nhánh 2: tương lai → cả 2 cờ False ────────────────────────────────────
    def test_get_asset_overdue_false_when_future(self):
        asset = self._make_asset("future", status="Active",
                                 next_pm_date=add_days(nowdate(), 7),
                                 next_calibration_date=add_days(nowdate(), 7))
        data = self._get(asset)
        self.assertIs(data["pm_overdue"], False, "PM tương lai → False")
        self.assertIs(data["calibration_overdue"], False,
                      "hiệu chuẩn tương lai → False")

    # ── Nhánh 3: NULL → cả 2 cờ False (no KeyError) ───────────────────────────
    def test_get_asset_overdue_false_when_null(self):
        asset = self._make_asset("null", status="Active")  # KHÔNG set ngày nào
        data = self._get(asset)
        self.assertIn("pm_overdue", data)
        self.assertIn("calibration_overdue", data)
        self.assertIs(data["pm_overdue"], False, "next_pm_date None → False")
        self.assertIs(data["calibration_overdue"], False,
                      "next_calibration_date None → False")

    # ── Nhánh 4: status BLOCKED_FOR_WO + ngày quá khứ → exempt (False) ─────────
    def test_get_asset_overdue_exempt_out_of_service(self):
        asset = self._make_asset("oos", status="Out of Service",
                                 next_pm_date=add_days(nowdate(), -30),
                                 next_calibration_date=add_days(nowdate(), -30))
        data = self._get(asset)
        self.assertIs(data["calibration_overdue"], False,
                      "Out of Service ∈ BLOCKED_FOR_WO → calibration_overdue False")
        self.assertIs(data["pm_overdue"], False,
                      "Out of Service ∈ BLOCKED_FOR_WO → pm_overdue False")

    # ── Parity no-raw-token GIỮ NGUYÊN sau khi thêm 2 cờ ─────────────────────
    def test_get_asset_still_strips_qr_token(self):
        asset = self._make_asset("strip", status="Active",
                                 next_pm_date=add_days(nowdate(), -1))
        data = self._get(asset)
        self.assertTrue(asset.qr_token, "fixture: asset có qr_token")
        self.assertNotIn("qr_token", data,
                         "payload get_asset KHÔNG leak qr_token (đi qua _strip_qr_token)")
        # 2 cờ vẫn có mặt (đảm bảo thêm cờ KHÔNG vô tình undo strip).
        self.assertIn("pm_overdue", data)
        self.assertIn("calibration_overdue", data)


# ──────────────────────────────────────────────────────────────────────────
# Vòng 34 / scan-action — capability-gate cho get_asset (parity sibling read).
# get_asset (api/imm00.py:438) phải gọi rbac.require("asset.read") làm CÂU LỆNH
# ĐẦU TIÊN thân hàm — đối xứng tuyệt đối với get_asset_scan_info:616 +
# resolve_qr_token:575. RC: frappe.get_doc().as_dict() trên whitelist method
# KHÔNG tự enforce DocPerm read → user thiếu read AC Asset vẫn đọc trọn doc qua
# endpoint QR-detail (lỗ hổng). Gate năng-lực chạy TRƯỚC frappe.db.exists →
# no existence-oracle (thiếu cap → 403 KHÔNG 404). RED viết TRƯỚC impl.
# ──────────────────────────────────────────────────────────────────────────
class TestGetAssetRequiresAssetReadCapability(unittest.TestCase):
    """get_asset gate rbac.require('asset.read') ĐẦU TIÊN (parity scan_info).

    Guest KHÔNG có DocPerm read AC Asset (xem TestAssetCapabilityEnablement::
    test_can_asset_read_resolves_via_docperm) → rbac.can('asset.read')==False →
    rbac.require ném frappe.PermissionError (403). Gate chạy TRƯỚC exists →
    no existence-oracle. Admin có asset.read → hành vi hợp-lệ KHÔNG hồi quy.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị get_asset CapGate",
            "description": "Category cho test get_asset capability-gate (V34)",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        # Location seed hermetic → guard enrich location_name (KHÔNG phụ thuộc
        # real-data có thể bị xoá). asset.location=cls.loc.name → branch enrich chạy.
        cls.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "CapGate Phòng test (V34)",
            "location_type": "Room",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("AC Location", cls.loc.name,
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

    def _make_asset(self, suffix="", **extra):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy CapGate {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"CG-SN-{uniq}",
            "asset_code": f"CG-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    # ── 403 — user KHÔNG có asset.read → PermissionError (KHÔNG _ok(doc)) ──────
    def test_get_asset_requires_asset_read_capability(self):
        """Guest (không DocPerm read AC Asset) get_asset(name hợp lệ) → 403.

        Trước fix: doc rò trọn vẹn qua as_dict(). Sau fix: rbac.require chặn
        TRƯỚC frappe.get_doc → frappe.PermissionError (HTTP 403), KHÔNG trả _ok.
        """
        from assetcore.api.imm00 import get_asset
        from assetcore.services.shared import rbac
        asset = self._make_asset("noperm")
        frappe.set_user("Guest")
        try:
            self.assertFalse(rbac.can("asset.read"),
                             "tiền đề: Guest KHÔNG có asset.read (DocPerm read=0)")
            with self.assertRaises(frappe.PermissionError):
                get_asset(name=asset.name)
        finally:
            frappe.set_user("Administrator")

    # ── 403 TRƯỚC exists — no existence-oracle (gate chạy trước 404) ──────────
    def test_get_asset_capability_gate_before_existence(self):
        """User thiếu asset.read gọi get_asset(name không tồn tại) → 403 KHÔNG 404.

        Gate năng-lực chạy TRƯỚC frappe.db.exists → user thiếu cap KHÔNG dò được
        tài sản tồn tại hay không (no existence-oracle) — parity thứ tự với
        resolve_qr_token/get_asset_scan_info.
        """
        from assetcore.api.imm00 import get_asset
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                # name KHÔNG tồn tại — nếu gate chạy SAU exists sẽ trả 404
                # (ServiceError/_err) thay vì PermissionError → fail test này.
                get_asset(name="AC-ASSET-DOES-NOT-EXIST-0000")
        finally:
            frappe.set_user("Administrator")

    # ── 200 — user CÓ asset.read (Administrator) → enrich + cờ, KHÔNG raise ────
    def test_get_asset_allows_user_with_asset_read(self):
        """Administrator (có DocPerm read AC Asset) → _ok với enrich + 2 cờ bool.

        Guard chống hồi quy hành vi hợp-lệ: gate KHÔNG chặn user CÓ cap; payload
        vẫn enrich category_name/location_name + pm_overdue/calibration_overdue.
        """
        from assetcore.api.imm00 import get_asset
        from assetcore.services.shared import rbac
        # location set → branch enrich location_name chạy (guard hồi quy enrich).
        asset = self._make_asset("ok", location=self.loc.name)
        # Administrator (setUp) có asset.read — KHÔNG ném.
        self.assertTrue(rbac.can("asset.read"),
                        "tiền đề: Administrator có asset.read")
        resp = get_asset(name=asset.name)
        self.assertTrue(resp["success"], "user có asset.read → success (KHÔNG 403)")
        data = resp["data"]
        self.assertEqual(data["name"], asset.name)
        self.assertIn("category_name", data,
                      "payload PHẢI enrich category_name (KHÔNG hồi quy)")
        self.assertEqual(data["category_name"], self.cat.category_name,
                         "category_name enrich đúng giá trị")
        self.assertIn("location_name", data,
                      "payload PHẢI enrich location_name (KHÔNG hồi quy)")
        self.assertEqual(data["location_name"], self.loc.location_name,
                         "location_name enrich đúng giá trị")
        self.assertIsInstance(data["pm_overdue"], bool,
                              "pm_overdue PHẢI là bool server-flag")
        self.assertIsInstance(data["calibration_overdue"], bool,
                              "calibration_overdue PHẢI là bool server-flag")

    # ── Parity — cùng user thiếu read → get_asset & scan_info ĐỀU 403 ─────────
    def test_get_asset_gate_parity_with_scan_info(self):
        """Đóng asymmetry: Guest → cả get_asset & get_asset_scan_info đều 403.

        Trước fix: get_asset_scan_info chặn (rbac.require), get_asset CHO QUA →
        đọc trọn doc. Sau fix: cả hai cùng PermissionError (đối xứng tuyệt đối).
        """
        from assetcore.api.imm00 import get_asset, get_asset_scan_info
        asset = self._make_asset("parity")
        name = asset.name
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                get_asset_scan_info(name=name)
            with self.assertRaises(frappe.PermissionError):
                get_asset(name=name)
        finally:
            frappe.set_user("Administrator")

    # ── No-raw-token GIỮ NGUYÊN (gate KHÔNG vô tình bỏ _strip_qr_token) ───────
    def test_get_asset_strip_qr_token_unchanged(self):
        """User có asset.read → payload KHÔNG chứa key qr_token (ADR-001 §D4).

        Đảm bảo thêm gate KHÔNG vô tình undo _strip_qr_token (no-raw-token parity).
        """
        from assetcore.api.imm00 import get_asset
        asset = self._make_asset("strip")
        self.assertTrue(asset.qr_token, "fixture: asset có qr_token")
        data = get_asset(name=asset.name)["data"]
        self.assertNotIn("qr_token", data,
                         "payload get_asset KHÔNG leak qr_token (giữ _strip_qr_token)")


# ──────────────────────────────────────────────────────────────────────────
# V35 — get_asset_action_meta: cap-gate rbac.require('asset.read') ĐẦU TIÊN
# (TRƯỚC frappe.db.exists) → no existence-oracle, parity get_asset/scan_info/
# resolve_qr_token. Endpoint meta NẠC cho 3 màn QR scan-action (CM/Hiệu chuẩn/
# PM). RED viết TRƯỚC khi đảo thứ tự gate→exists trong impl.
# ──────────────────────────────────────────────────────────────────────────


class TestGetAssetActionMetaRequiresAssetReadCapability(unittest.TestCase):
    """get_asset_action_meta gate rbac.require('asset.read') ĐẦU TIÊN.

    Mirror tuyệt đối bộ test get_asset (Vòng 34): Guest KHÔNG có DocPerm read
    AC Asset → rbac.can('asset.read')==False → rbac.require ném
    frappe.PermissionError (403). Gate chạy TRƯỚC frappe.db.exists →
    no existence-oracle (user thiếu cap KHÔNG dò được tài sản tồn tại qua
    endpoint meta nạc). Administrator có asset.read → hành vi hợp-lệ
    (đúng 6 key allowlist + enrich) KHÔNG hồi quy. rbac/has_permission KHÔNG
    monkeypatch — dùng user thật (Guest vs Administrator) + DocPerm thật.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị action_meta CapGate",
            "description": "Category cho test get_asset_action_meta cap-gate (V35)",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        # device_model + location seed hermetic → branch enrich
        # device_model_name/location_name chạy (guard hồi quy enrich).
        cls.model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": "AMG Dräger Evita V500 (V35)",
            "manufacturer": "Dräger Medical",
            "medical_device_class": "Class II",
            "asset_category": cls.cat.name,
        }).insert(ignore_permissions=True)
        cls.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "AMG CapGate Phòng test (V35)",
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

    def _make_asset(self, suffix="", **extra):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy AMGCapGate {uniq}",
            "asset_category": self.cat.name,
            "device_model": self.model.name,
            "location": self.loc.name,
            "manufacturer_sn": f"AMG-SN-{uniq}",
            "asset_code": f"AMG-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    # ── 403 — Guest thiếu asset.read gọi name TỒN TẠI → PermissionError ───────
    def test_action_meta_requires_asset_read_capability(self):
        """Guest (không DocPerm read) get_asset_action_meta(name TỒN TẠI) → 403.

        Trước fix: 6 key meta rò qua get_doc().has_permission CHẠY SAU exists.
        Sau fix: rbac.require chặn ĐẦU TIÊN → frappe.PermissionError (HTTP 403),
        KHÔNG trả _ok meta.
        """
        from assetcore.api.imm00 import get_asset_action_meta
        from assetcore.services.shared import rbac
        asset = self._make_asset("noperm")
        frappe.set_user("Guest")
        try:
            self.assertFalse(rbac.can("asset.read"),
                             "tiền đề: Guest KHÔNG có asset.read (DocPerm read=0)")
            with self.assertRaises(frappe.PermissionError):
                get_asset_action_meta(name=asset.name)
        finally:
            frappe.set_user("Administrator")

    # ── 403 TRƯỚC exists — no existence-oracle (gate chạy trước 404) ──────────
    def test_action_meta_capability_gate_before_existence(self):
        """Guest gọi name KHÔNG tồn tại → 403 KHÔNG _err(404) (no existence-oracle).

        Test phân biệt existence-oracle (mirror
        test_get_asset_capability_gate_before_existence): TRƯỚC fix exists chạy
        trước → trả _err(404); SAU fix rbac.require ĐẦU TIÊN → PermissionError.
        """
        from assetcore.api.imm00 import get_asset_action_meta
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                # name KHÔNG tồn tại — nếu gate chạy SAU exists sẽ trả _err(404)
                # thay vì PermissionError → fail test này.
                get_asset_action_meta(name="AC-ASSET-DOES-NOT-EXIST-0000")
        finally:
            frappe.set_user("Administrator")

    # ── 200 — Administrator (có asset.read) → đúng 6 key + enrich, KHÔNG hồi quy ─
    def test_action_meta_allows_user_with_asset_read(self):
        """Administrator (có DocPerm read) → _ok đúng 6 key allowlist + enrich.

        Guard chống hồi quy hành vi hợp-lệ: gate KHÔNG chặn user CÓ cap; payload
        đúng set(_ASSET_ACTION_META_KEYS) + device_model_name/location_name enrich.
        """
        from assetcore.api.imm00 import (
            get_asset_action_meta, _ASSET_ACTION_META_KEYS,
        )
        from assetcore.services.shared import rbac
        asset = self._make_asset("ok")
        self.assertTrue(rbac.can("asset.read"),
                        "tiền đề: Administrator có asset.read")
        resp = get_asset_action_meta(name=asset.name)
        self.assertTrue(resp["success"],
                        "user có asset.read → success (KHÔNG 403)")
        data = resp["data"]
        self.assertEqual(set(data.keys()), set(_ASSET_ACTION_META_KEYS),
                         "payload PHẢI đúng 6 key allowlist (KHÔNG hồi quy)")
        self.assertEqual(data["name"], asset.name)
        self.assertEqual(data["device_model_name"], self.model.model_name,
                         "device_model_name enrich đúng giá trị")
        self.assertEqual(data["location_name"], self.loc.location_name,
                         "location_name enrich đúng giá trị")

    # ── No-overfetch — KHÔNG rò field tài chính/qr_token (guard regress) ──────
    def test_action_meta_no_overfetch_financial(self):
        """payload data KHÔNG chứa key tài chính/nhạy cảm/qr_token.

        Guard chống regress over-fetch song song gate mới (cap-gate KHÔNG được
        kéo theo nới allowlist).
        """
        from assetcore.api.imm00 import get_asset_action_meta
        asset = self._make_asset("nofin")
        data = get_asset_action_meta(name=asset.name)["data"]
        for fld in ("gross_purchase_amount", "accumulated_depreciation",
                    "current_book_value", "purchase_cost", "salvage_value",
                    "qr_token"):
            self.assertNotIn(fld, data,
                             f"payload meta KHÔNG được leak field nhạy cảm {fld}")

    # ── name rỗng với user CÓ quyền → vẫn _err(404) leak-safe (gate KHÔNG vỡ) ──
    def test_action_meta_empty_name_still_404_for_privileged(self):
        """Administrator → get_asset_action_meta(name='') → _err 404 leak-safe.

        Gate cap KHÔNG làm vỡ nhánh 404 hợp-lệ cho user CÓ quyền (Admin qua
        rbac.require → vào nhánh exists → name rỗng → _err(404)).
        """
        from assetcore.api.imm00 import get_asset_action_meta
        resp = get_asset_action_meta(name="")
        self.assertFalse(resp["success"], "name rỗng → success False")
        self.assertEqual(resp["http_status"], 404,
                         "name rỗng (user có quyền) → 404 leak-safe (KHÔNG 403/500)")


# ──────────────────────────────────────────────────────────────────────────
# CR-WF-00-TRANSITION-AUTHZ (Trục A — missing-authorization write) — endpoint
# transition_status ĐỔI lifecycle_status AC Asset gọi service perm-free
# transition_asset_status. TRƯỚC fix: MỌI user login POST được endpoint tự đổi
# trạng thái thiết bị. Fix = MIRROR 3-lớp bảo mật get_asset:
#   0. rbac.require("asset.write")  → 403 TRƯỚC exists (no existence-oracle)
#   1. exists                       → 404 leak-safe
#   2. assert_vendor_can_access     → 403 IDOR (Vendor Engineer ngoài scope)
# Gate CHỈ ở tầng ENDPOINT — service transition_asset_status GIỮ NGUYÊN perm-free
# (đường WO-driven: KTV không có asset.write vẫn chuyển trạng thái khi complete WO).
# Chỉ "AssetCore Super Admin" có write DocPerm AC Asset; Administrator bypass mọi
# permission (happy-path). rbac/has_permission KHÔNG monkeypatch — user THẬT +
# DocPerm THẬT. RED viết TRƯỚC impl (mirror get_asset cap-gate Vòng 34).
# ──────────────────────────────────────────────────────────────────────────
class TestTransitionStatusRequiresAssetWrite(unittest.TestCase):
    """transition_status gate rbac.require('asset.write') + IDOR (MIRROR get_asset).

    Đóng lỗ CR-WF-00-TRANSITION-AUTHZ: endpoint đổi lifecycle_status AC Asset
    thiếu authz → MỌI user login đổi được trạng thái thiết bị. Fix mirror 3-lớp
    get_asset (rbac.require ĐẦU TIÊN → no existence-oracle → IDOR vendor).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị transition AuthZ",
            "description": "Category cho test transition_status authz (CR-WF-00-TRANSITION-AUTHZ)",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        # User base-role THẬT (AssetCore System User read=1, write=0 trên AC Asset
        # + PM User) = "user login bất kỳ": có read, KHÔNG có asset.write. Chính là
        # actor lỗ hổng trước fix (POST đổi trạng thái được). KHÔNG Guest (Guest quá
        # yếu — không chứng minh "user login hợp lệ vẫn bị chặn WRITE").
        cls.base_user = "trans_authz_base@example.com"
        if frappe.db.exists("User", cls.base_user):
            frappe.delete_doc("User", cls.base_user, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": cls.base_user,
            "first_name": "Trans AuthZ Base", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        u.add_roles("AssetCore System User", "PM User")
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", cls.base_user):
            frappe.delete_doc("User", cls.base_user, force=True, ignore_permissions=True)
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
            "asset_name": f"Máy TransAuthZ {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"TA-SN-{uniq}",
            "asset_code": f"TA-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(extra)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    # ── T1 (AC1) — 403 khi thiếu asset.write; lifecycle_status KHÔNG đổi ───────
    def test_transition_status_denies_without_asset_write(self):
        """Base-role user (read=1, write=0) POST transition_status → 403.

        Trước fix: transition_asset_status chạy → lifecycle_status đổi. Sau fix:
        rbac.require('asset.write') chặn ĐẦU TIÊN → frappe.PermissionError (403);
        lifecycle_status trong DB KHÔNG đổi (assert trước/sau bằng db.get_value).
        """
        from assetcore.api.imm00 import transition_status
        from assetcore.services.shared import rbac
        asset = self._make_asset("noperm")
        before = frappe.db.get_value("AC Asset", asset.name, "lifecycle_status")
        self.assertEqual(before, "Active", "tiền đề: asset khởi tạo ở Active")
        frappe.set_user(self.base_user)
        try:
            self.assertFalse(rbac.can("asset.write"),
                             "tiền đề: base-role user KHÔNG có asset.write (DocPerm write=0)")
            with self.assertRaises(frappe.PermissionError):
                transition_status(name=asset.name, to_status="Under Maintenance",
                                  reason="Đưa vào bảo trì định kỳ")
        finally:
            frappe.set_user("Administrator")
        after = frappe.db.get_value("AC Asset", asset.name, "lifecycle_status")
        self.assertEqual(after, before,
                         "denied → lifecycle_status KHÔNG đổi (vẫn Active)")

    # ── T4 (AC3) — 403 TRƯỚC exists: no existence-oracle ─────────────────────
    def test_transition_status_no_existence_oracle(self):
        """User thiếu asset.write + name KHÔNG tồn tại → 403 (KHÔNG 404).

        Chứng minh rbac.require chạy TRƯỚC frappe.db.exists (parity thứ-tự-lớp
        get_asset): nếu gate chạy SAU exists sẽ trả _err(404) thay vì
        PermissionError → user dò được tài sản tồn tại hay không (existence-oracle).
        """
        from assetcore.api.imm00 import transition_status
        frappe.set_user(self.base_user)
        try:
            with self.assertRaises(frappe.PermissionError):
                transition_status(name="AC-ASSET-DOES-NOT-EXIST-0000",
                                  to_status="Under Maintenance", reason="probe")
        finally:
            frappe.set_user("Administrator")

    # ── T2 (AC2) — IDOR: Vendor Engineer CÓ asset.write, asset ngoài scope → 403 ─
    def test_transition_status_denies_vendor_out_of_scope(self):
        """Vendor Engineer CÓ asset.write nhưng asset NGOÀI scope → 403 IDOR.

        Mirror get_asset AUTH-10 (+ test_label_idor_vendor_scope). Chỉ 'AssetCore
        Super Admin' có write DocPerm sẵn (và là bypass-IDOR) → cấp write TẠM cho
        role 'Vendor Engineer' qua Custom DocPerm (DATA, KHÔNG cap mới), gỡ ở
        finally. User QUA gate WRITE rồi mới đập IDOR (assert_vendor_can_access:
        asset ngoài WO được giao). Siết RBAC KHÔNG nới IDOR. lifecycle_status
        KHÔNG đổi.
        """
        from frappe.permissions import add_permission, update_permission_property
        from assetcore.api.imm00 import transition_status
        from assetcore.services.shared import rbac
        asset = self._make_asset("idor")
        name = asset.name
        before = frappe.db.get_value("AC Asset", name, "lifecycle_status")
        role = "Vendor Engineer"
        vendor_email = "vendor_trans_authz_idor@example.com"
        if frappe.db.exists("User", vendor_email):
            frappe.delete_doc("User", vendor_email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": vendor_email,
            "first_name": "Vendor Trans AuthZ IDOR", "send_welcome_email": 0,
        }).insert(ignore_permissions=True)
        # Vendor Engineer (scope-restrict, KHÔNG bypass-IDOR) + Repair User.
        u.add_roles("Vendor Engineer", "Repair User")
        # Cấp write TẠM cho Vendor Engineer trên AC Asset → user qua gate WRITE
        # NHƯNG bị chặn ở IDOR (asset ngoài WO được giao). DATA, KHÔNG cap mới.
        add_permission("AC Asset", role, 0)
        update_permission_property("AC Asset", role, 0, "write", 1)
        frappe.clear_cache()
        frappe.db.commit()
        frappe.set_user(vendor_email)
        try:
            self.assertTrue(rbac.can("asset.write"),
                            "tiền đề: Vendor Engineer (Custom DocPerm write=1) CÓ asset.write")
            resp = transition_status(name=name, to_status="Under Maintenance",
                                     reason="Vendor thử đổi trạng thái asset ngoài scope")
            self.assertFalse(resp["success"], "vendor ngoài scope → KHÔNG success")
            self.assertEqual(resp["http_status"], 403,
                             "vendor ngoài scope → 403 (IDOR guard, mirror get_asset AUTH-10)")
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
        after = frappe.db.get_value("AC Asset", name, "lifecycle_status")
        self.assertEqual(after, before,
                         "vendor denied → lifecycle_status KHÔNG đổi (vẫn Active)")

    # ── T3 (AC4) — happy-path: holder asset.write + in-scope → _ok + audit ────
    def test_transition_status_allows_asset_write_holder(self):
        """Administrator (asset.write via bypass) + transition hợp state-machine
        (Active→Under Maintenance) → _ok {name, lifecycle_status}; đúng 1 Asset
        Lifecycle Event + 1 IMM Audit Trail 'State Change' row sinh (KHÔNG hồi quy).
        """
        from assetcore.api.imm00 import transition_status
        from assetcore.services.shared import rbac
        asset = self._make_asset("ok")
        self.assertTrue(rbac.can("asset.write"),
                        "tiền đề: Administrator có asset.write (bypass superuser)")
        ale_before = frappe.db.count("Asset Lifecycle Event", {"asset": asset.name})
        at_before = frappe.db.count(
            "IMM Audit Trail", {"asset": asset.name, "event_type": "State Change"})
        resp = transition_status(name=asset.name, to_status="Under Maintenance",
                                 reason="Đưa thiết bị vào bảo trì định kỳ theo lịch PM")
        self.assertTrue(resp["success"], "holder asset.write in-scope → success")
        self.assertEqual(resp["data"]["name"], asset.name)
        self.assertEqual(resp["data"]["lifecycle_status"], "Under Maintenance")
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset.name, "lifecycle_status"),
            "Under Maintenance", "lifecycle_status thực đổi trong DB")
        self.assertEqual(
            frappe.db.count("Asset Lifecycle Event", {"asset": asset.name}) - ale_before, 1,
            "transition hợp lệ → sinh đúng 1 Asset Lifecycle Event")
        self.assertEqual(
            frappe.db.count(
                "IMM Audit Trail",
                {"asset": asset.name, "event_type": "State Change"}) - at_before, 1,
            "transition hợp lệ → sinh đúng 1 IMM Audit Trail 'State Change'")

    # ── T5 (AC5) — zero blast-radius: SERVICE perm-free (đường WO-driven) ─────
    def test_service_transition_asset_status_no_perm_gate(self):
        """Gọi TRỰC TIẾP service transition_asset_status với user KHÔNG có
        asset.write vẫn success — khẳng định gate CHỈ ở ENDPOINT.

        Đường WO-driven (test_imm08/09: KTV complete WO → asset Under Maintenance/
        Active/Completed) gọi service programmatic; KTV không có asset.write DocPerm.
        Nếu gate rớt xuống service → toàn bộ WO-complete vỡ. Guard này khoá contract
        service perm-free.
        """
        from assetcore.services.imm00 import transition_asset_status
        from assetcore.services.shared import rbac
        asset = self._make_asset("svc")
        frappe.set_user(self.base_user)
        try:
            self.assertFalse(rbac.can("asset.write"),
                             "tiền đề: base-role user KHÔNG có asset.write")
            transition_asset_status(
                asset.name, "Under Maintenance", actor=self.base_user,
                reason="WO-driven: KTV chuyển trạng thái khi bắt đầu bảo trì")
            frappe.db.commit()
            self.assertEqual(
                frappe.db.get_value("AC Asset", asset.name, "lifecycle_status"),
                "Under Maintenance",
                "service perm-free → transition thành công dù user thiếu asset.write "
                "(đường WO-complete KTV KHÔNG bị chặn)")
        finally:
            frappe.set_user("Administrator")


# ──────────────────────────────────────────────────────────────────────────
# A3 — Dữ liệu in nhãn QR + sự kiện in (ADR-001 D3)
# get_asset_label_data (1) + get_asset_label_data_batch (batch, KHÔNG N+1) +
# mark_label_printed (POST emit label_printed + audit). RED viết TRƯỚC impl.
# ──────────────────────────────────────────────────────────────────────────


class TestAssetLabelData(unittest.TestCase):
    """A3 — endpoint dữ liệu in nhãn + sự kiện in (get/batch/mark)."""

    # ADR-IMM00-QR-SCAN-ACTION D5: nhãn QR tách bạch Mã tài sản (asset_code) ↔
    # Số serial NSX (manufacturer_sn) + Tên tài sản (asset_name) ⇒ 8 key.
    _LABEL_KEYS = {
        "name", "asset_code", "asset_name", "manufacturer_sn",
        "device_model_name", "location_name", "lifecycle_status", "qr_url",
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
                         "payload nhãn PHẢI đúng 8 key (không thiếu/thừa)")
        self.assertGreaterEqual(set(data.keys()), self._LABEL_KEYS)
        self.assertEqual(data["name"], asset.name)
        self.assertEqual(data["asset_code"], asset.asset_code)
        # D5: Số serial NSX + Tên tài sản tách bạch khỏi Mã tài sản.
        self.assertEqual(data["manufacturer_sn"], asset.manufacturer_sn,
                         "manufacturer_sn (Số serial NSX) == giá trị asset")
        self.assertEqual(data["asset_name"], asset.asset_name,
                         "asset_name (Tên tài sản) == giá trị asset")
        self.assertNotEqual(data["asset_code"], data["manufacturer_sn"],
                            "Mã tài sản ≠ Số serial NSX (KHÔNG trộn 2 khái niệm)")
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
        by_name = {a.name: a for a in (a1, a2, a3)}
        for d in data:
            self.assertEqual(set(d.keys()), self._LABEL_KEYS)
            self.assertRegex(d["qr_url"], self._QR_URL_RE)
            # D5: mỗi item HỢP LỆ chứa manufacturer_sn + asset_name đúng value.
            src = by_name[d["name"]]
            self.assertEqual(d["manufacturer_sn"], src.manufacturer_sn)
            self.assertEqual(d["asset_name"], src.asset_name)

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
        # entry lỗi GIỮ NGUYÊN {name, error} — KHÔNG nở key mới.
        self.assertEqual(set(data[1].keys()), {"name", "error"},
                         "entry lỗi đúng {name, error} (D5 KHÔNG đổi nhánh lỗi)")
        self.assertNotIn("manufacturer_sn", data[1])
        self.assertNotIn("asset_name", data[1])
        self.assertEqual(data[2]["name"], a2.name)
        self.assertNotIn("error", data[2])
        # item hợp lệ 2 bên chứa 2 key mới đúng value.
        self.assertEqual(data[0]["manufacturer_sn"], a1.manufacturer_sn)
        self.assertEqual(data[0]["asset_name"], a1.asset_name)
        self.assertEqual(data[2]["manufacturer_sn"], a2.manufacturer_sn)
        self.assertEqual(data[2]["asset_name"], a2.asset_name)

    # ── D5: manufacturer_sn / asset_name rỗng-None → '' (KHÔNG None) ─────────
    def test_get_asset_label_data_empty_serial_name_coerced_to_blank(self):
        from assetcore.api.imm00 import get_asset_label_data
        asset = self._make_asset("blank")
        # set manufacturer_sn + asset_name về None ở DB (bỏ qua validate đường form)
        frappe.db.set_value("AC Asset", asset.name,
                            {"manufacturer_sn": None}, update_modified=False)
        frappe.db.set_value("AC Asset", asset.name,
                            {"asset_name": None}, update_modified=False)
        resp = get_asset_label_data(asset=asset.name)
        self.assertTrue(resp["success"])
        data = resp["data"]
        self.assertEqual(data["manufacturer_sn"], "",
                         "manufacturer_sn None → '' (KHÔNG None, không vỡ render)")
        self.assertEqual(data["asset_name"], "",
                         "asset_name None → '' (KHÔNG None)")
        self.assertIsNotNone(data["manufacturer_sn"])
        self.assertIsNotNone(data["asset_name"])

    def test_get_asset_label_data_batch_empty_serial_name_coerced_to_blank(self):
        from assetcore.api.imm00 import get_asset_label_data_batch
        asset = self._make_asset("bblank")
        frappe.db.set_value("AC Asset", asset.name,
                            {"manufacturer_sn": None, "asset_name": None},
                            update_modified=False)
        resp = get_asset_label_data_batch(assets=[asset.name])
        self.assertTrue(resp["success"])
        d = resp["data"][0]
        self.assertEqual(d["manufacturer_sn"], "")
        self.assertEqual(d["asset_name"], "")

    # ── D5 no-extra-query guard: 2 key mới = cột thêm vào get_value/get_all
    #    SẴN CÓ, KHÔNG thêm query nào (2 asset cùng device_model) ───────────
    def test_get_asset_label_data_batch_new_cols_no_extra_query(self):
        from assetcore.api.imm00 import get_asset_label_data_batch
        # 2 asset cùng device_model (None ở đây) → batch vẫn gộp; thêm 2 cột
        # vào fields get_all KHÔNG được sinh query mới.
        a1 = self._make_asset("nc1")
        a2 = self._make_asset("nc2")
        names = [a1.name, a2.name]

        def _count_queries():
            calls = {"n": 0}
            orig = frappe.db.sql

            def _wrap(*a, **k):
                calls["n"] += 1
                return orig(*a, **k)

            frappe.db.sql = _wrap
            try:
                resp = get_asset_label_data_batch(assets=names)
            finally:
                frappe.db.sql = orig
            return calls["n"], resp

        n, resp = _count_queries()
        data = resp["data"]
        # 2 key mới có value đúng (cột mở rộng đã trả về row).
        self.assertEqual(data[0]["manufacturer_sn"], a1.manufacturer_sn)
        self.assertEqual(data[0]["asset_name"], a1.asset_name)
        # Cận trên query rộng nhưng chống N+1: 2 asset KHÔNG kéo query/asset.
        self.assertLess(n, len(names) + 6,
                        f"thêm 2 cột KHÔNG tăng query/asset (n={n})")

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
# ADR-IMM00-QR-SCAN-ACTION D6 (Accepted→EXECUTED, phương án B) — TÁCH cap in/rotate
#
# RECONCILE (2026-06-08): trước đây 3 endpoint nhãn + rotate gate `asset.write`,
# mà write=1 CHỈ Super Admin có → KTV/QL vật tư KHÔNG in/rotate được (self-
# correction P2). Phương án B TÁCH cap riêng:
#   - get_asset_label_data / _batch / mark_label_printed → gate `asset.print`
#     →(AC Asset,"print"). DocPerm print=1 sẵn cho ~MỌI role vận hành ⇒ in được
#     NGAY (KHÔNG đổi DocPerm). User KHÔNG có print → 403.
#   - regenerate_asset_qr_token → gate `asset.qr.rotate`→(AC Asset,"write").
#     Rotate = GHI ⇒ bind "write" (chỉ Super Admin/role được cấp write). print
#     KHÔNG đủ để rotate.
# Thêm 2 cap ⇒ CAP_SET_VERSION ĐỔI v95.3388ee5629c1 → v104.e46d05d9a66d.
#
# KHÔNG test false-green (luật skill): test tạo user THẬT + cấp/không-cấp DocPerm
# `print`/`write` trên AC Asset (qua Role/Custom DocPerm), frappe.set_user(...),
# rồi gọi endpoint qua layer require(...) → can → frappe.has_permission("AC Asset",
# permtype). KHÔNG monkeypatch rbac.require / frappe.has_permission.
#
# DocPerm thực tế (site miyano, verified 2026-06-08): MỌI role có print=1 trên AC
# Asset; chỉ "AssetCore Super Admin" có write=1. ⇒ "Commissioning User"
# (read=1,write=0,print=1) = user CÓ print NHƯNG KHÔNG write → in 200, rotate 403.
# "AssetCore Super Admin" (write=1,print=1) → in 200 + rotate 200. User KHÔNG
# print → gỡ print qua Custom DocPerm tạm (hoặc Guest no-cap). IDOR test cần user
# CÓ print NHƯNG vendor-scope (Vendor Engineer) → cấp print tạm, gỡ ở tearDown.
# ──────────────────────────────────────────────────────────────────────────


class TestLabelWriteCapability(unittest.TestCase):
    """D6 phương án B — in nhãn gate asset.print, rotate gate asset.qr.rotate.

    Phân tách quyền IN (`asset.print`, persona vận hành có) vs quyền ROTATE
    (`asset.qr.rotate`=write, chỉ Super Admin/được cấp). Read-only QR endpoint
    (resolve_qr_token/get_asset_scan_info/get_asset) GIỮ asset.read. IDOR
    (assert_vendor_can_access) KHÔNG bị nới.
    """

    # D5 (ADR-IMM00-QR-SCAN-ACTION): nhãn QR + asset_name + manufacturer_sn ⇒ 8 key.
    _LABEL_KEYS = {
        "name", "asset_code", "asset_name", "manufacturer_sn",
        "device_model_name", "location_name", "lifecycle_status", "qr_url",
    }
    # Role có print=1 NHƯNG write=0 trên AC Asset → user CÓ asset.print NHƯNG
    # KHÔNG asset.qr.rotate (persona vận hành: KTV/QL vật tư mặc định).
    _PRINT_ONLY_ROLE = "Commissioning User"
    # Role có write=1 (⇒ asset.qr.rotate) + print=1 trên AC Asset (DocPerm thật).
    _WRITE_ROLE = "AssetCore Super Admin"
    _PRINT_USER = "be_b_label_printonly@example.com"
    _WRITE_USER = "be_b_label_write@example.com"
    _IDOR_USER = "be_b_label_idor_print@example.com"
    _NOPRINT_USER = "be_b_label_noprint@example.com"

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
            "description": "Category cho test RBAC in/rotate nhãn QR (D6)",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        # User CÓ print (write=0) — persona vận hành: in 200, rotate 403.
        cls._printer = cls._ensure_user(cls._PRINT_USER, [cls._PRINT_ONLY_ROLE])
        # User write=1 (⇒ asset.qr.rotate) + print=1 — Super Admin: in + rotate 200.
        cls._writer = cls._ensure_user(cls._WRITE_USER, [cls._WRITE_ROLE])
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for email in (cls._PRINT_USER, cls._WRITE_USER,
                      cls._IDOR_USER, cls._NOPRINT_USER):
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

    # ── D6 phương án B — user CÓ print (write=0) → 200 (KHÔNG còn 403) ────────
    def test_label_data_print_user_200(self):
        """get_asset_label_data: user CÓ asset.print NHƯNG KHÔNG write → 200.

        D6 RECONCILE: gate đổi asset.write→asset.print. Persona vận hành (KTV/QL
        vật tư, DocPerm print=1 write=0) BÂY GIỜ in được (sửa self-correction P2).
        """
        from assetcore.api.imm00 import get_asset_label_data
        from assetcore.services.shared import rbac
        asset = self._make_asset("pr1")
        frappe.set_user(self._PRINT_USER)
        try:
            # tiền đề ĐO ĐƯỢC: user CÓ asset.print NHƯNG KHÔNG asset.write/rotate.
            self.assertTrue(rbac.can("asset.print"),
                            "tiền đề: user có asset.print (DocPerm print=1)")
            self.assertFalse(rbac.can("asset.write"),
                             "tiền đề: user KHÔNG có asset.write")
            self.assertFalse(rbac.can("asset.qr.rotate"),
                             "tiền đề: user KHÔNG có asset.qr.rotate (write=0)")
            resp = get_asset_label_data(asset=asset.name)
            self.assertTrue(resp["success"],
                            "user print (không write) → 200 (KHÔNG 403)")
            self.assertEqual(set(resp["data"].keys()), self._LABEL_KEYS,
                             "payload nhãn đúng 8 key")
        finally:
            frappe.set_user("Administrator")

    def test_label_batch_print_user_200(self):
        """get_asset_label_data_batch: user CÓ print (write=0) → 200."""
        from assetcore.api.imm00 import get_asset_label_data_batch
        asset = self._make_asset("pr2")
        frappe.set_user(self._PRINT_USER)
        try:
            resp = get_asset_label_data_batch(assets=[asset.name])
            self.assertTrue(resp["success"], "user print → 200 (KHÔNG 403)")
        finally:
            frappe.set_user("Administrator")

    def test_mark_printed_print_user_200(self):
        """mark_label_printed: user CÓ print (write=0) → 200 + 1 event + 1 audit."""
        from assetcore.api.imm00 import mark_label_printed
        asset = self._make_asset("pr3")
        before_label = self._count_label_events(asset.name)
        before_audit = self._count_audit(asset.name)
        frappe.set_user(self._PRINT_USER)
        try:
            resp = mark_label_printed(assets=[asset.name])
            self.assertTrue(resp["success"], "user print → 200 (KHÔNG 403)")
            self.assertEqual(resp["data"]["event_count"], 1)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(self._count_label_events(asset.name), before_label + 1,
                         "user print → ĐÚNG 1 label_printed / asset")
        self.assertEqual(self._count_audit(asset.name), before_audit + 1,
                         "user print → ĐÚNG 1 IMM Audit Trail / asset")

    # ── 403 — user KHÔNG có print (Guest no-cap) bị chặn + no side-effect ─────
    def test_label_data_no_print_user_403(self):
        """get_asset_label_data: user KHÔNG có asset.print (Guest) → 403 VI sạch."""
        from assetcore.api.imm00 import get_asset_label_data
        from assetcore.services.shared import rbac
        asset = self._make_asset("np1")
        frappe.set_user("Guest")
        try:
            self.assertFalse(rbac.can("asset.print"),
                             "tiền đề: Guest KHÔNG có asset.print")
            with self.assertRaises(frappe.PermissionError):
                get_asset_label_data(asset=asset.name)
        finally:
            frappe.set_user("Administrator")

    def test_mark_printed_no_print_user_403_no_side_effect(self):
        """mark_label_printed: user KHÔNG print → 403 + KHÔNG sinh event/audit.

        Gate print chạy ĐẦU TIÊN → chặn TRƯỚC mọi side-effect (no label_printed,
        no IMM Audit Trail) — least-privilege + no-side-effect khi bị chặn.
        """
        from assetcore.api.imm00 import mark_label_printed
        asset = self._make_asset("np2")
        before_label = self._count_label_events(asset.name)
        before_audit = self._count_audit(asset.name)
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                mark_label_printed(assets=[asset.name])
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(self._count_label_events(asset.name), before_label,
                         "user không-print bị chặn → KHÔNG sinh label_printed")
        self.assertEqual(self._count_audit(asset.name), before_audit,
                         "user không-print bị chặn → KHÔNG ghi IMM Audit Trail")

    # ── 200 — user có asset.write (Super Admin) qua được gate print ───────────
    def test_label_data_write_user_200(self):
        """get_asset_label_data: Super Admin (print=1+write=1) → 200 + 8 key."""
        from assetcore.api.imm00 import get_asset_label_data
        asset = self._make_asset("w1")
        frappe.set_user(self._WRITE_USER)
        try:
            resp = get_asset_label_data(asset=asset.name)
            self.assertTrue(resp["success"], "user write → success")
            self.assertEqual(set(resp["data"].keys()), self._LABEL_KEYS,
                             "payload nhãn đúng 8 key")
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
        frappe.set_user(self._PRINT_USER)
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

    # ── IDOR — user CÓ print nhưng vendor ngoài scope → 403 (KHÔNG nới IDOR) ──
    def test_label_idor_unchanged_after_print_gate(self):
        """user asset.print + Vendor Engineer ngoài scope → 403 IDOR.

        Đổi gate write→print KHÔNG được nới IDOR: assert_vendor_can_access vẫn
        chặn user CÓ print nhưng asset NGOÀI WO được giao. Vendor Engineer đã có
        print=1 (DocPerm chuẩn) → qua gate PRINT mà KHÔNG cần grant tạm; IDOR
        đập SAU gate. (D6 phương án B — print mở rộng persona NHƯNG IDOR bất biến.)
        """
        from assetcore.api.imm00 import get_asset_label_data, mark_label_printed
        from assetcore.services.shared import rbac
        asset = self._make_asset("idorp")
        name = asset.name
        u = self._ensure_user(self._IDOR_USER, ["Vendor Engineer", "Repair User"])
        frappe.clear_cache()
        frappe.db.commit()
        try:
            frappe.set_user(self._IDOR_USER)
            # tiền đề: user CÓ asset.print (qua gate PRINT) NHƯNG vendor-scope.
            self.assertTrue(rbac.can("asset.print"),
                            "tiền đề: user IDOR có asset.print (qua gate)")
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
            frappe.clear_cache()
            rbac.invalidate_capabilities(self._IDOR_USER)
            if frappe.db.exists("User", self._IDOR_USER):
                frappe.delete_doc("User", self._IDOR_USER, force=True,
                                  ignore_permissions=True)
            frappe.db.commit()

    # ── Version guard — thêm 2 cap (D6) → CAP_SET_VERSION ĐỔI + cap mới có ─────
    def test_cap_set_version_changed_after_split_caps(self):
        """D6 phương án B: thêm asset.print + asset.qr.rotate → version ĐỔI.

        White-box: CAP_SET_VERSION KHÔNG còn v95.3388ee5629c1 (giá trị cũ) → đổi
        v104.e46d05d9a66d (98 cap). FE auth.ts::CAP_SET_VERSION PHẢI bump khớp →
        isCapCacheStale tự bỏ persisted-caps cũ. 2 cap mới bind đúng permtype.
        KHÔNG còn asset.print_label (tên cũ trong roadmap đã đổi đúng theo ADR).
        """
        from assetcore.services.shared.rbac import CAP_SET_VERSION, CAPABILITY_MAP
        self.assertNotEqual(CAP_SET_VERSION, "v95.3388ee5629c1",
                            "thêm 2 cap (D6) → CAP_SET_VERSION PHẢI đổi giá trị cũ")
        self.assertEqual(CAP_SET_VERSION, "v104.e46d05d9a66d",
                         "98 cap (D6 + firmware.approve IMM-09 Vòng 10) → version "
                         "v104.e46d05d9a66d (khớp FE auth.ts CAP_SET_VERSION)")
        self.assertIn("asset.print", CAPABILITY_MAP,
                      "asset.print (D6 phương án B) phải có trong CAPABILITY_MAP")
        self.assertEqual(CAPABILITY_MAP["asset.print"], ("AC Asset", "print"),
                         "asset.print bind ('AC Asset','print') — DocPerm print")
        self.assertIn("asset.qr.rotate", CAPABILITY_MAP,
                      "asset.qr.rotate (D6 phương án B) phải có trong CAPABILITY_MAP")
        self.assertEqual(CAPABILITY_MAP["asset.qr.rotate"], ("AC Asset", "write"),
                         "asset.qr.rotate bind ('AC Asset','write') — rotate=GHI")
        self.assertIn("asset.write", CAPABILITY_MAP,
                      "asset.write GIỮ (qua _DOMAIN_PRIMARY['Asset'])")
        self.assertNotIn("asset.print_label", CAPABILITY_MAP,
                         "tên cũ asset.print_label KHÔNG dùng (ADR chốt asset.print)")


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

    # ── 417-GUARD — print_asset_labels_pdf QUA HTTP (JSON-string + list) ─────
    def test_print_labels_pdf_http_no_417_json_string(self):
        """ADR-LABEL-PDF §D1 — endpoint sinh PDF QUA HTTP coercion KHÔNG 417.

        Real HTTP: ``assets`` đến dưới dạng JSON-string (frappe.form_dict).
        param ``assets`` (KHÔNG annotation — đồng nhất get_asset_label_data_batch)
        → coercion KHÔNG reject (KHÁC `str` annotation vốn reject native list ở
        test-context). Trả PDF qua frappe.local.response (KHÔNG raise FrappeTypeError).
        """
        import json
        from assetcore.api.imm00 import print_asset_labels_pdf
        asset = self._make_asset("pdfhttp")
        frappe.local.response = frappe._dict()
        env, exc = self._http_call(
            print_asset_labels_pdf, assets=json.dumps([asset.name]),
            preset="tem-60x100")
        self.assertIsNone(
            exc, f"print_asset_labels_pdf QUA HTTP KHÔNG được raise (417): {exc!r}")
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "QUA HTTP JSON-string → set response PDF (KHÔNG 417)")
        self.assertTrue(bytes(frappe.local.response.get("filecontent"))
                        .startswith(b"%PDF-"))

    def test_print_labels_pdf_param_not_none_union_annotation(self):
        """RC GUARD: print_asset_labels_pdf KHÔNG mang annotation Union-chứa-None
        (chống 417 prod) — đồng nhất guard QR GET. ``assets`` bare (no-coercion)."""
        import inspect
        import types as _types
        from assetcore.api import imm00 as _api

        def _is_none_union(ann) -> bool:
            import typing
            if isinstance(ann, _types.UnionType):
                return type(None) in ann.__args__
            if typing.get_origin(ann) is typing.Union:
                return type(None) in typing.get_args(ann)
            return False

        raw = inspect.unwrap(_api.print_asset_labels_pdf)
        for param in ("assets", "preset"):
            ann = raw.__annotations__.get(param, inspect._empty)
            self.assertFalse(
                _is_none_union(ann),
                f"print_asset_labels_pdf({param}) annotation '{ann}' Union-chứa-None "
                f"→ coercion 417 prod.")


# ──────────────────────────────────────────────────────────────────────────
# B (hardening) — Regenerate (rotate) QR token cấp AC Asset
# Endpoint regenerate_asset_qr_token(asset): gate asset.qr.rotate →(AC Asset,
# "write") (D6 phương án B — tách cap rotate; 403 khi user chỉ print/read) →
# token MỚI != cũ (enumeration-safe, overwrite, update_modified=False) → token
# CŨ KHÔNG còn resolve → 1 ALE 'qr_regenerated' + 1 IMM Audit Trail (KHÔNG log
# token thô) → IDOR-safe (assert_vendor_can_access) → 404 leak-safe. RED viết TRƯỚC.
# ──────────────────────────────────────────────────────────────────────────


class TestRegenerateQrToken(unittest.TestCase):
    """D6/B — rotate qr_token gate asset.qr.rotate (=write): print KHÔNG đủ."""

    # Role print=1 write=0 → CÓ asset.print NHƯNG KHÔNG asset.qr.rotate.
    _READONLY_ROLE = "Commissioning User"
    # Role có write=1 (⇒ asset.qr.rotate) trên AC Asset (DocPerm thật).
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

    def test_regenerate_print_only_user_403(self):
        """User CÓ asset.print NHƯNG KHÔNG asset.qr.rotate → 403, KHÔNG rotate.

        D6 phương án B: rotate gate asset.qr.rotate(=write). Persona vận hành CÓ
        print (in nhãn được) NHƯNG KHÔNG rotate được — least-privilege chính xác.
        """
        from assetcore.api.imm00 import regenerate_asset_qr_token
        from assetcore.services.shared import rbac
        asset = self._make_asset("ro")
        old = asset.qr_token
        frappe.set_user(self._READONLY_USER)
        try:
            self.assertTrue(rbac.can("asset.print"),
                            "tiền đề: user CÓ asset.print (in nhãn được)")
            self.assertFalse(rbac.can("asset.qr.rotate"),
                             "tiền đề: user KHÔNG có asset.qr.rotate (write=0)")
            with self.assertRaises(frappe.PermissionError):
                regenerate_asset_qr_token(asset=asset.name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset.name, "qr_token"), old,
            "user chỉ-print bị chặn → qr_token KHÔNG đổi (no side-effect)")

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
        """user CÓ asset.qr.rotate + Vendor Engineer ngoài scope → 403 IDOR."""
        from frappe.permissions import add_permission, update_permission_property
        from assetcore.api.imm00 import regenerate_asset_qr_token
        from assetcore.services.shared import rbac
        asset = self._make_asset("idor")
        old = asset.qr_token
        role = "Vendor Engineer"
        u = self._ensure_user(self._IDOR_USER, ["Vendor Engineer", "Repair User"])
        # Cấp write tạm cho Vendor Engineer trên AC Asset (data) → asset.qr.rotate
        # (bind write) resolve TRUE → user QUA gate ROTATE rồi đập IDOR
        # (assert_vendor_can_access). KHÔNG hardcode role, cấp qua DocPerm.
        add_permission("AC Asset", role, 0)
        update_permission_property("AC Asset", role, 0, "write", 1)
        frappe.clear_cache()
        frappe.db.commit()
        try:
            frappe.set_user(self._IDOR_USER)
            self.assertTrue(rbac.can("asset.qr.rotate"),
                            "tiền đề: user IDOR có asset.qr.rotate (qua gate)")
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

    # ── Version guard — rotate cap tách riêng (D6) → version ĐỔI ────────────
    def test_rotate_cap_in_map_and_version_changed(self):
        """D6: rotate gate asset.qr.rotate→(AC Asset,write); CAP_SET_VERSION ĐỔI."""
        from assetcore.services.shared.rbac import CAP_SET_VERSION, CAPABILITY_MAP
        self.assertEqual(CAP_SET_VERSION, "v104.e46d05d9a66d",
                         "thêm asset.print + asset.qr.rotate → version v104.e46d05d9a66d")
        self.assertEqual(CAPABILITY_MAP.get("asset.qr.rotate"), ("AC Asset", "write"),
                         "asset.qr.rotate bind ('AC Asset','write') — rotate=GHI")


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

    # ── GUARD: TOÀN BỘ họ endpoint nhãn QR NAY throttled (Vòng 36 — đóng lỗ cuối) ──
    # ⚠️ ĐẢO Vòng 36 (BR-00-51 / FR-00-102 / 05 §I.7c): danh sách miễn rate-limit ĐÃ
    # CẠN — get_asset_label_data (single) là endpoint nhãn DUY NHẤT còn hở trước Vòng
    # 36 NAY MANG @rate_limit (hằng+bucket RIÊNG). Lý do throttle dù read-mostly:
    # mint side-effect — token-less asset → ensure_asset_qr_token (idempotent) emit
    # qr_generated (ALE+audit) ⇒ hammer = write-amplification. Hành vi >N→429 kiểm ở
    # TestLabelDataRateLimit. mark/batch (Vòng 14) + rotate (Vòng 27 B) + pdf + 2
    # resolve cũng throttled. Static decorator-presence guard — chống tái-gỡ âm thầm.
    def test_all_label_endpoints_throttled(self):
        """TOÀN BỘ họ endpoint nhãn QR (single + batch + mark + rotate) MANG
        @rate_limit (hằng/bucket RIÊNG). Static decorator-presence guard."""
        import inspect
        from assetcore.api import imm00 as _api

        # (a) single NAY MANG @rate_limit + hằng RIÊNG (Vòng 36 — đóng lỗ cuối).
        single_src = inspect.getsource(getattr(_api, "get_asset_label_data"))
        self.assertIn(
            "@rate_limit", single_src,
            "get_asset_label_data (single) PHẢI mang @rate_limit (Vòng 36 / BR-00-51)")
        self.assertIn(
            "AC_LABEL_DATA_RATE_LIMIT", single_src,
            "single dùng hằng RIÊNG AC_LABEL_DATA_RATE_LIMIT (KHÔNG chung batch/pdf)")

        # (b) mark + batch NAY MANG @rate_limit + hằng RIÊNG (Vòng 14 — đảo).
        mark_src = inspect.getsource(getattr(_api, "mark_label_printed"))
        self.assertIn("@rate_limit", mark_src,
                      "mark_label_printed PHẢI mang @rate_limit (Vòng 14 / BR-00-45)")
        self.assertIn("AC_LABEL_MARK_RATE_LIMIT", mark_src,
                      "mark dùng hằng RIÊNG AC_LABEL_MARK_RATE_LIMIT")
        batch_src = inspect.getsource(getattr(_api, "get_asset_label_data_batch"))
        self.assertIn("@rate_limit", batch_src,
                      "get_asset_label_data_batch PHẢI mang @rate_limit (BR-00-46)")
        self.assertIn("AC_LABEL_BATCH_RATE_LIMIT", batch_src,
                      "batch dùng hằng RIÊNG AC_LABEL_BATCH_RATE_LIMIT")

        # (c) rotate NAY CÓ @rate_limit (Vòng 27 B) — chứng minh quyết định đã đảo.
        regen_src = inspect.getsource(getattr(_api, "regenerate_asset_qr_token"))
        self.assertIn(
            "@rate_limit", regen_src,
            "regenerate_asset_qr_token PHẢI mang @rate_limit (Vòng 27 B / BR-00-38)")
        self.assertIn(
            "AC_QR_REGEN_RATE_LIMIT", regen_src,
            "rotate dùng hằng RIÊNG AC_QR_REGEN_RATE_LIMIT (KHÔNG chung resolve)")

    # ── Regression — CAP_SET_VERSION KHÔNG đổi (rate-limit KHÔNG thêm cap) ──
    def test_cap_set_version_unchanged(self):
        from assetcore.services.shared.rbac import CAP_SET_VERSION
        self.assertEqual(
            CAP_SET_VERSION, "v104.e46d05d9a66d",
            "@rate_limit (decorator) KHÔNG đổi CAPABILITY_MAP; giá trị hiện hành "
            "v104.e46d05d9a66d (sau D6 tách asset.print/asset.qr.rotate)")


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
            CAP_SET_VERSION, "v104.e46d05d9a66d",
            "@rate_limit lên rotate KHÔNG đổi CAPABILITY_MAP; giá trị hiện hành "
            "v104.e46d05d9a66d (sau D6 tách asset.print/asset.qr.rotate)")


# ──────────────────────────────────────────────────────────────────────────
# Vòng 14 (BR-00-45/46 / FR-00-96/97 — Self-Correction, mirror rotate) — Rate-limit
# 2 endpoint nhãn còn hở: mark_label_printed (POST — GHI write-audit-amplification
# 2×N record/call = N ALE `label_printed` + N IMM Audit Trail) +
# get_asset_label_data_batch (GET — đọc N asset/call). @rate_limit bucket+hằng RIÊNG
# (cache key gồm cmd → counter TÁCH BIỆT resolve(30)/scan(30)/regen(10)/pdf(20)).
# 429 NGOÀI/TRƯỚC rbac.require("asset.print") ⇒ mark vượt → 0 ALE + 0 audit (no
# side-effect); batch vượt → 0 byte payload. no-leak parity 404/403.
#   AC_LABEL_MARK_RATE_LIMIT  = 10  (≤ AC_QR_REGEN_RATE_LIMIT — cùng họ write-amplify)
#   AC_LABEL_BATCH_RATE_LIMIT = 20  (read-only → CAO hơn mark, song song pdf=20)
# Hạ tầng test = mô phỏng HTTP context (frappe.local.request truthy + request_ip
# per-test-uniq + form_dict.cmd) + dọn `rl:*` ở teardown. CLI/test bypass:
# `if not frappe.request: return fn` → suite cũ GREEN. Spec: 05 §I.7c / 02 BR-00-45/46
# / 04 §II.1.8e-LABELRL / 07 §III.6.i-LABELRL / ADR-IMM00-LABEL-PDF §D18. RED-first.
# ──────────────────────────────────────────────────────────────────────────


class TestLabelMarkBatchRateLimit(unittest.TestCase):
    """Vòng 14 — @rate_limit trên mark_label_printed + get_asset_label_data_batch.

    RED-first: trước khi gắn decorator, dội >10 mark / >20 batch KHÔNG raise 429.
    Tái dùng pattern _http_call/_drain/IP-uniq/teardown `rl:` (mirror rotate).
    """

    _CMD_MARK = "assetcore.api.imm00.mark_label_printed"
    _CMD_BATCH = "assetcore.api.imm00.get_asset_label_data_batch"
    _ALE_LABEL = "label_printed"  # Asset Lifecycle Event.event_type

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị LabelRL QR (Vòng 14)",
            "description": "Category cho test rate-limit nhãn mark/batch",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        # order test dùng Guest (KHÔNG asset.print) để chứng minh RL chặn TRƯỚC
        # rbac.require — role vận hành ĐỀU có DocPerm print=1 (ADR D6) nên KHÔNG
        # dùng được. KHÔNG cần seed user riêng.
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
        import uuid
        self._ip = f"10.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}." \
                   f"{uuid.uuid4().int % 250 + 1}"

    def tearDown(self):
        frappe.set_user("Administrator")
        # Dọn MỌI cache key rate-limit do test sinh ra (tránh rò trần sang test khác).
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
            "asset_name": f"Máy LabelRL {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"LBRL-SN-{uniq}",
            "asset_code": f"LBRL-ASSET-{uniq}",
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

    def _count_side_effects(self, asset_name):
        """COUNT (ALE label_printed, IMM Audit Trail) của asset — đo trước+sau 429."""
        ale = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset_name, "event_type": self._ALE_LABEL})
        audit = frappe.db.count("IMM Audit Trail", {"asset": asset_name})
        return ale, audit

    # ── Hằng RIÊNG tồn tại + đúng ngưỡng BA chốt (constant-value guard) ──────
    def test_label_mark_constant_value(self):
        from assetcore.api.imm00 import AC_LABEL_MARK_RATE_LIMIT
        self.assertEqual(
            AC_LABEL_MARK_RATE_LIMIT, 10,
            "ngưỡng BA chốt mark = 10 req/60s/IP (BR-00-45, write-audit-amplification)")

    def test_label_batch_constant_value(self):
        from assetcore.api.imm00 import AC_LABEL_BATCH_RATE_LIMIT
        self.assertEqual(
            AC_LABEL_BATCH_RATE_LIMIT, 20,
            "ngưỡng BA chốt batch = 20 req/60s/IP (BR-00-46, read-only)")

    def test_label_mark_le_regen(self):
        from assetcore.api.imm00 import (
            AC_LABEL_MARK_RATE_LIMIT, AC_QR_REGEN_RATE_LIMIT)
        self.assertLessEqual(
            AC_LABEL_MARK_RATE_LIMIT, AC_QR_REGEN_RATE_LIMIT,
            "mark cùng họ write-amplify như rotate → ngưỡng ≤ regen (BR-00-45)")

    def test_label_batch_gt_mark(self):
        from assetcore.api.imm00 import (
            AC_LABEL_BATCH_RATE_LIMIT, AC_LABEL_MARK_RATE_LIMIT)
        self.assertGreater(
            AC_LABEL_BATCH_RATE_LIMIT, AC_LABEL_MARK_RATE_LIMIT,
            "batch read-only → ngưỡng CAO hơn mark write-amplify (BR-00-46)")

    def test_label_consts_distinct(self):
        """2 hằng nhãn RIÊNG — KHÔNG tái dùng resolve/regen (giá-trị batch trùng
        pdf=20 nhưng TÊN độc lập — tách biệt ngữ nghĩa)."""
        from assetcore.api.imm00 import (
            AC_LABEL_MARK_RATE_LIMIT, AC_LABEL_BATCH_RATE_LIMIT,
            AC_QR_RESOLVE_RATE_LIMIT)
        self.assertNotEqual(
            AC_LABEL_MARK_RATE_LIMIT, AC_QR_RESOLVE_RATE_LIMIT,
            "mark KHÔNG tái dùng ngưỡng resolve")
        self.assertNotEqual(
            AC_LABEL_BATCH_RATE_LIMIT, AC_QR_RESOLVE_RATE_LIMIT,
            "batch KHÔNG tái dùng ngưỡng resolve")

    # ── Decorator-presence guard (chống tái-gỡ âm thầm) ─────────────────────
    def test_label_decorator_presence(self):
        import inspect
        from assetcore.api import imm00 as _api
        mark_src = inspect.getsource(getattr(_api, "mark_label_printed"))
        self.assertIn("@rate_limit", mark_src,
                      "mark_label_printed PHẢI mang @rate_limit (BR-00-45)")
        self.assertIn("AC_LABEL_MARK_RATE_LIMIT", mark_src,
                      "mark dùng hằng RIÊNG AC_LABEL_MARK_RATE_LIMIT")
        batch_src = inspect.getsource(getattr(_api, "get_asset_label_data_batch"))
        self.assertIn("@rate_limit", batch_src,
                      "get_asset_label_data_batch PHẢI mang @rate_limit (BR-00-46)")
        self.assertIn("AC_LABEL_BATCH_RATE_LIMIT", batch_src,
                      "batch dùng hằng RIÊNG AC_LABEL_BATCH_RATE_LIMIT")

    # ── mark: ≤N call → 200 + ghi 2×N record/call (happy-path bất biến) ─────
    def test_mark_under_limit_ok(self):
        from assetcore.api.imm00 import (
            mark_label_printed, AC_LABEL_MARK_RATE_LIMIT as N)
        asset = self._make_asset("markunder")
        cmd = self._CMD_MARK
        for i in range(N):
            env, exc = self._http_call(
                mark_label_printed, cmd, assets=[asset.name])
            self.assertIsNone(exc, f"mark call #{i+1} (≤N) KHÔNG throttle: {exc!r}")
            self.assertTrue(env["success"], f"mark call #{i+1} ≤N → 200")

    # ── mark: call N+1 → 429, KHÔNG trả envelope ────────────────────────────
    def test_mark_over_limit_429(self):
        from assetcore.api.imm00 import (
            mark_label_printed, AC_LABEL_MARK_RATE_LIMIT as N)
        asset = self._make_asset("markover")
        cmd = self._CMD_MARK
        first_exc = self._drain(mark_label_printed, cmd, N, assets=[asset.name])
        self.assertIsNone(first_exc,
                          f"{N} call mark đầu trong window KHÔNG throttle: {first_exc!r}")
        env, exc = self._http_call(mark_label_printed, cmd, assets=[asset.name])
        self.assertIsNotNone(exc, f"mark call thứ {N+1} PHẢI raise 429 (vượt trần)")
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            f"vượt trần → 429 (RateLimitExceededError), KHÔNG {type(exc).__name__}")
        self.assertEqual(getattr(exc, "http_status_code", None), 429,
                         "exception map HTTP 429")
        self.assertIsNone(env, "429 KHÔNG trả envelope (no payload built)")

    # ── mark: 429 → 0 ALE label_printed + 0 IMM Audit Trail MỚI (CỐT LÕI) ───
    def test_mark_429_no_side_effect(self):
        from assetcore.api.imm00 import (
            mark_label_printed, AC_LABEL_MARK_RATE_LIMIT as N)
        asset = self._make_asset("noside")
        cmd = self._CMD_MARK
        # Vắt kiệt trần (N call hợp lệ — mỗi call ghi 2 record; đo SAU N).
        self._drain(mark_label_printed, cmd, N, assets=[asset.name])
        ale_before, audit_before = self._count_side_effects(asset.name)
        # call N+1 → 429 (chặn TRƯỚC thân hàm ⇒ KHÔNG chạm _svc_mark_label_printed).
        env, exc = self._http_call(mark_label_printed, cmd, assets=[asset.name])
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            "call mark vượt trần PHẢI 429")
        self.assertIsNone(env, "429 KHÔNG trả envelope")
        ale_after, audit_after = self._count_side_effects(asset.name)
        self.assertEqual(ale_after, ale_before,
                         "429 → 0 ALE label_printed MỚI (no side-effect)")
        self.assertEqual(audit_after, audit_before,
                         "429 → 0 IMM Audit Trail MỚI (no side-effect)")

    # ── mark: 429 no-leak (KHÔNG name/asset_code/số-record) ─────────────────
    def test_mark_429_no_leak(self):
        from assetcore.api.imm00 import (
            mark_label_printed, AC_LABEL_MARK_RATE_LIMIT as N)
        asset = self._make_asset("noleak")
        cmd = self._CMD_MARK
        self._drain(mark_label_printed, cmd, N, assets=[asset.name])
        _, exc = self._http_call(mark_label_printed, cmd, assets=[asset.name])
        self.assertIsNotNone(exc, "call mark vượt trần PHẢI raise 429")
        msg = str(getattr(exc, "message", "") or "") + str(exc)
        for leak in (asset.name, asset.asset_code, asset.manufacturer_sn):
            self.assertNotIn(leak, msg,
                             "429 message KHÔNG leak name/asset_code/serial")

    # ── mark: 429 chạy TRƯỚC rbac.require("asset.print") ────────────────────
    def test_mark_429_runs_before_rbac(self):
        """User KHÔNG asset.print (Guest), dội >N → call vượt trần → 429
        (KHÔNG 403). Decorator @rate_limit bọc NGOÀI thân → counter+throw TRƯỚC
        rbac.require("asset.print"). Đồng nhất precedent resolve/rotate.

        Dùng Guest (KHÔNG print) — `Commissioning User`/role vận hành ĐỀU có
        DocPerm print=1 (ADR D6: asset.print mở cho ~mọi role) nên KHÔNG dùng
        để chứng minh thiếu-print được."""
        from assetcore.api.imm00 import (
            mark_label_printed, AC_LABEL_MARK_RATE_LIMIT as N)
        from assetcore.services.shared import rbac
        asset = self._make_asset("order")
        cmd = self._CMD_MARK
        frappe.set_user("Guest")
        try:
            self.assertFalse(rbac.can("asset.print"),
                             "tiền đề: Guest KHÔNG có asset.print")
            # ≤N: user chỉ-đọc → PermissionError (403) — RBAC chạy SAU RL khi chưa trần.
            _, exc_under = self._http_call(
                mark_label_printed, cmd, assets=[asset.name])
            self.assertIsInstance(
                exc_under, frappe.PermissionError,
                "≤N + thiếu asset.print → 403 (RBAC sau RL khi chưa trần)")
            # Dội cho vượt trần (counter tăng kể cả khi thân raise 403).
            for _ in range(N):
                self._http_call(mark_label_printed, cmd, assets=[asset.name])
            _, exc_over = self._http_call(
                mark_label_printed, cmd, assets=[asset.name])
            self.assertIsInstance(
                exc_over,
                (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
                f"vượt trần → 429 TRƯỚC PermissionError, KHÔNG {type(exc_over).__name__}")
        finally:
            frappe.set_user("Administrator")

    # ── batch: ≤N call → 200 payload N-item (happy-path bất biến) ───────────
    def test_batch_under_limit_ok(self):
        from assetcore.api.imm00 import (
            get_asset_label_data_batch, AC_LABEL_BATCH_RATE_LIMIT as N)
        asset = self._make_asset("batchunder")
        cmd = self._CMD_BATCH
        for i in range(N):
            env, exc = self._http_call(
                get_asset_label_data_batch, cmd, assets=[asset.name])
            self.assertIsNone(exc, f"batch call #{i+1} (≤N) KHÔNG throttle: {exc!r}")
            self.assertTrue(env["success"], f"batch call #{i+1} ≤N → 200")

    # ── batch: call N+1 → 429, 0 byte payload build ─────────────────────────
    def test_batch_over_limit_429(self):
        from assetcore.api.imm00 import (
            get_asset_label_data_batch, AC_LABEL_BATCH_RATE_LIMIT as N)
        asset = self._make_asset("batchover")
        cmd = self._CMD_BATCH
        first_exc = self._drain(
            get_asset_label_data_batch, cmd, N, assets=[asset.name])
        self.assertIsNone(first_exc,
                          f"{N} call batch đầu KHÔNG throttle: {first_exc!r}")
        env, exc = self._http_call(
            get_asset_label_data_batch, cmd, assets=[asset.name])
        self.assertIsNotNone(exc, f"batch call thứ {N+1} PHẢI raise 429")
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            f"vượt trần → 429, KHÔNG {type(exc).__name__}")
        self.assertEqual(getattr(exc, "http_status_code", None), 429)
        self.assertIsNone(env, "429 KHÔNG trả payload (build_asset_label_data_batch KHÔNG chạy)")

    # ── mark / batch = 2 bucket RIÊNG (cache key gồm cmd) ───────────────────
    def test_mark_batch_separate_bucket(self):
        """Vắt kiệt bucket mark (chạm trần) KHÔNG làm batch bị 429 ở call đầu
        (bucket riêng theo cmd) — chống chặn nhầm cross-endpoint."""
        from assetcore.api.imm00 import (
            mark_label_printed, get_asset_label_data_batch,
            AC_LABEL_MARK_RATE_LIMIT as NM)
        asset = self._make_asset("twobucket")
        # vắt kiệt bucket mark (N+1 → 429 ở mark).
        self._drain(mark_label_printed, self._CMD_MARK, NM + 1, assets=[asset.name])
        # batch bucket RIÊNG → call đầu vẫn 200 (KHÔNG kế thừa counter mark).
        env, exc = self._http_call(
            get_asset_label_data_batch, self._CMD_BATCH, assets=[asset.name])
        self.assertIsNone(exc, f"batch bucket riêng → call đầu KHÔNG 429: {exc!r}")
        self.assertTrue(env["success"], "batch vẫn 200 trong cùng cửa sổ")

    # ── Bypass test/CLI có chủ đích — gọi TRỰC TIẾP (no frappe.request) ─────
    def test_label_no_request_context_bypasses(self):
        """Gọi mark/batch TRỰC TIẾP >N lần (KHÔNG set frappe.local.request) →
        KHÔNG 429 (wrapper `if not frappe.request: return fn`). Đảm bảo suite cũ
        (TestMarkLabelPrinted/batch — gọi trực tiếp) KHÔNG regress."""
        from assetcore.api.imm00 import (
            mark_label_printed, get_asset_label_data_batch,
            AC_LABEL_MARK_RATE_LIMIT as NM, AC_LABEL_BATCH_RATE_LIMIT as NB)
        asset = self._make_asset("bypass")
        had_req = getattr(frappe.local, "request", None)
        frappe.local.request = None
        try:
            for _ in range(NM + 5):
                resp = mark_label_printed(assets=[asset.name])
                self.assertTrue(resp["success"],
                                "mark trực tiếp (no request) → KHÔNG bao giờ 429")
            for _ in range(NB + 5):
                resp = get_asset_label_data_batch(assets=[asset.name])
                self.assertTrue(resp["success"],
                                "batch trực tiếp (no request) → KHÔNG bao giờ 429")
        finally:
            frappe.local.request = had_req

    # ── Regression — CAP_SET_VERSION KHÔNG đổi (decorator KHÔNG thêm cap) ───
    def test_cap_set_version_unchanged(self):
        from assetcore.services.shared.rbac import CAP_SET_VERSION
        self.assertEqual(
            CAP_SET_VERSION, "v104.e46d05d9a66d",
            "@rate_limit lên mark/batch KHÔNG đổi CAPABILITY_MAP; giá trị hiện "
            "hành v104.e46d05d9a66d (sau D6 tách asset.print/asset.qr.rotate)")


# ──────────────────────────────────────────────────────────────────────────
# Vòng 36 (BR-00-51 / FR-00-102 — đóng lỗ hổng CUỐI họ endpoint nhãn QR) — Rate-limit
# endpoint ĐỌC SINGLE `get_asset_label_data` (preview nhãn 1 asset). @rate_limit(
# limit=AC_LABEL_DATA_RATE_LIMIT=20, seconds=60, ip_based=True) bọc NGOÀI thân hàm →
# 429 (RateLimitExceededError) TRƯỚC rbac.require("asset.print") ⇒ vượt ngưỡng = 0
# byte payload build + 0 mint-token side-effect (ensure_asset_qr_token KHÔNG chạy →
# 0 qr_generated ALE/audit). Hằng + bucket RIÊNG (KHÔNG chung batch=20/pdf=20; cache
# key gồm cmd → counter TÁCH BIỆT). Lý do throttle dù read-mostly: token-less asset →
# ensure_asset_qr_token (idempotent) GHI token + emit qr_generated → hammer KHÔNG giới
# hạn = write-amplification mint-token (bơm phồng audit-chain NĐ98). Thứ tự gate sau
# decorator GIỮ NGUYÊN: 429 → 403(rbac asset.print) → 404(asset rỗng/∄ leak-safe) →
# 403(IDOR assert_vendor_can_access) → 200(_ok build_asset_label_data). Hạ tầng test =
# mô phỏng HTTP context (frappe.local.request truthy + request_ip per-test-uniq +
# form_dict.cmd) + dọn `rl:*` ở teardown. Spec: 05 §I.7c / 02 BR-00-51 / 07. RED-first.
# ──────────────────────────────────────────────────────────────────────────


class TestLabelDataRateLimit(unittest.TestCase):
    """Vòng 36 — @rate_limit trên get_asset_label_data (single, bucket+hằng RIÊNG).

    RED-first: trước khi gắn decorator, dội >20 single KHÔNG raise 429.
    Tái dùng pattern _http_call/_drain/IP-uniq/teardown `rl:` (mirror batch).
    """

    _CMD_SINGLE = "assetcore.api.imm00.get_asset_label_data"
    _CMD_BATCH = "assetcore.api.imm00.get_asset_label_data_batch"
    _ALE_QR_GEN = "qr_generated"  # Asset Lifecycle Event.event_type (mint side-effect)

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị LabelDataRL QR (Vòng 36)",
            "description": "Category cho test rate-limit single get_asset_label_data",
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
        import uuid
        self._ip = f"10.{uuid.uuid4().int % 250 + 1}.{uuid.uuid4().int % 250 + 1}." \
                   f"{uuid.uuid4().int % 250 + 1}"

    def tearDown(self):
        frappe.set_user("Administrator")
        # Dọn MỌI cache key rate-limit do test sinh ra (tránh rò trần sang test khác).
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
            "asset_name": f"Máy LabelDataRL {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"LDRL-SN-{uniq}",
            "asset_code": f"LDRL-ASSET-{uniq}",
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

    # ── Hằng RIÊNG tồn tại + đúng ngưỡng BA chốt (constant-value guard) ──────
    def test_label_data_rate_limit_constant_value(self):
        from assetcore.api.imm00 import AC_LABEL_DATA_RATE_LIMIT
        self.assertEqual(
            AC_LABEL_DATA_RATE_LIMIT, 20,
            "ngưỡng BA chốt single = 20 req/60s/IP (BR-00-51, read-mostly preview)")

    def test_label_data_const_distinct_identifier(self):
        """AC_LABEL_DATA_RATE_LIMIT là ĐỊNH-DANH RIÊNG — KHÔNG alias batch/pdf/mark/
        resolve/regen (giá-trị trùng batch=pdf=20 nhưng TÊN độc lập — tách ngữ-nghĩa).
        Chứng minh tách-định-danh: source decorator dùng đúng tên hằng single, KHÔNG
        tham chiếu hằng khác."""
        import inspect
        from assetcore.api import imm00 as _api
        # (a) hằng tồn tại & = 20.
        self.assertTrue(hasattr(_api, "AC_LABEL_DATA_RATE_LIMIT"),
                        "AC_LABEL_DATA_RATE_LIMIT PHẢI được khai báo RIÊNG")
        self.assertEqual(_api.AC_LABEL_DATA_RATE_LIMIT, 20)
        # (b) decorator single dùng ĐÚNG hằng single, KHÔNG tái dùng định-danh khác.
        single_src = inspect.getsource(getattr(_api, "get_asset_label_data"))
        self.assertIn("AC_LABEL_DATA_RATE_LIMIT", single_src,
                      "decorator single PHẢI dùng AC_LABEL_DATA_RATE_LIMIT")
        for other in ("AC_LABEL_BATCH_RATE_LIMIT", "AC_LABEL_MARK_RATE_LIMIT",
                      "AC_LABEL_PDF_RATE_LIMIT", "AC_QR_RESOLVE_RATE_LIMIT",
                      "AC_QR_REGEN_RATE_LIMIT"):
            self.assertNotIn(
                f"limit={other}", single_src,
                f"single KHÔNG tái dùng định-danh hằng khác ({other})")

    # ── Decorator-presence guard (chống tái-gỡ âm thầm) ─────────────────────
    def test_get_asset_label_data_has_rate_limit_decorator(self):
        """introspect: get_asset_label_data có wrapper rate_limit (parity batch/mark)."""
        import inspect
        from assetcore.api import imm00 as _api
        single_src = inspect.getsource(getattr(_api, "get_asset_label_data"))
        self.assertIn("@rate_limit", single_src,
                      "get_asset_label_data PHẢI mang @rate_limit (Vòng 36 / BR-00-51)")
        self.assertIn("AC_LABEL_DATA_RATE_LIMIT", single_src,
                      "single dùng hằng RIÊNG AC_LABEL_DATA_RATE_LIMIT")
        # decorator đặt GIỮA @frappe.whitelist() và def (bọc NGOÀI thân → 429 TRƯỚC rbac).
        wl_pos = single_src.find("@frappe.whitelist()")
        rl_pos = single_src.find("@rate_limit")
        def_pos = single_src.find("def get_asset_label_data")
        self.assertTrue(
            0 <= wl_pos < rl_pos < def_pos,
            "@rate_limit PHẢI nằm GIỮA @frappe.whitelist() và def (bọc ngoài thân)")
        # wrapper thực sự bọc handler (introspect __wrapped__ — closure rate_limit).
        self.assertIsNot(
            inspect.unwrap(getattr(_api, "get_asset_label_data")),
            getattr(_api, "get_asset_label_data"),
            "handler PHẢI bị wrap (rate_limit closure) — __wrapped__ tồn tại")

    # ── single: ≤N call → 200 + mint idempotent CHẠY (token-less → qr_url≠rỗng) ──
    def test_label_data_under_limit_ok(self):
        """user CÓ asset.print + asset token-less → 200, qr_url≠rỗng (mint idempotent
        VẪN chạy dưới ngưỡng); request đầu KHÔNG bị 429."""
        from assetcore.api.imm00 import (
            get_asset_label_data, AC_LABEL_DATA_RATE_LIMIT as N)
        asset = self._make_asset("under")
        # Token-less: xoá qr_token để ép nhánh mint (ensure_asset_qr_token) chạy.
        frappe.db.set_value("AC Asset", asset.name,
                            {"qr_token": None}, update_modified=False)
        cmd = self._CMD_SINGLE
        # request đầu — KHÔNG 429, mint side-effect chạy → token sinh ra.
        env, exc = self._http_call(get_asset_label_data, cmd, asset=asset.name)
        self.assertIsNone(exc, f"request đầu (≤N) KHÔNG throttle: {exc!r}")
        self.assertTrue(env["success"], "asset token-less ≤N → 200")
        self.assertIn("qr_url", env["data"])
        self.assertTrue(env["data"]["qr_url"], "qr_url KHÔNG rỗng (mint idempotent)")
        self.assertIn("/a/", env["data"]["qr_url"],
                      "qr_url chứa deep-link /a/<token> (mint đã sinh token)")
        # token đã GHI vào DB (mint side-effect chạy dưới ngưỡng).
        self.assertTrue(
            frappe.db.get_value("AC Asset", asset.name, "qr_token"),
            "ensure_asset_qr_token đã mint token cho asset token-less (dưới ngưỡng)")
        # các call còn lại trong window (≤N) cũng KHÔNG 429.
        for i in range(N - 1):
            env_i, exc_i = self._http_call(get_asset_label_data, cmd, asset=asset.name)
            self.assertIsNone(exc_i, f"single call #{i+2} (≤N) KHÔNG throttle: {exc_i!r}")
            self.assertTrue(env_i["success"], f"single call #{i+2} ≤N → 200")

    # ── single: call N+1 → 429, 0 byte payload + 0 mint side-effect ─────────
    def test_label_data_over_limit_429_no_side_effect(self):
        from assetcore.api.imm00 import (
            get_asset_label_data, AC_LABEL_DATA_RATE_LIMIT as N)
        asset = self._make_asset("over")
        # token-less để chứng minh 429 → KHÔNG mint (0 qr_generated MỚI).
        frappe.db.set_value("AC Asset", asset.name,
                            {"qr_token": None}, update_modified=False)
        cmd = self._CMD_SINGLE
        first_exc = self._drain(get_asset_label_data, cmd, N, asset=asset.name)
        self.assertIsNone(first_exc,
                          f"{N} call single đầu KHÔNG throttle: {first_exc!r}")
        # Đo qr_generated TRƯỚC call vượt trần (mint đã xảy ra ở call đầu — idempotent).
        qrgen_before = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": self._ALE_QR_GEN})
        env, exc = self._http_call(get_asset_label_data, cmd, asset=asset.name)
        self.assertIsNotNone(exc, f"single call thứ {N+1} PHẢI raise 429 (vượt trần)")
        self.assertIsInstance(
            exc, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            f"vượt trần → 429, KHÔNG {type(exc).__name__}")
        self.assertEqual(getattr(exc, "http_status_code", None), 429)
        self.assertIsNone(env, "429 KHÔNG trả payload (build_asset_label_data KHÔNG chạy)")
        qrgen_after = frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset.name, "event_type": self._ALE_QR_GEN})
        self.assertEqual(qrgen_after, qrgen_before,
                         "429 → 0 qr_generated MỚI (mint-token side-effect KHÔNG chạy)")

    # ── single / batch = 2 bucket RIÊNG (cache key gồm cmd) ─────────────────
    def test_label_data_bucket_isolated_from_batch(self):
        """Vắt kiệt bucket single (chạm trần >N → 429 ở single) KHÔNG đẩy counter
        batch lên 429 ở call đầu (bucket riêng theo cmd) — chống chặn nhầm cross-
        endpoint (1 endpoint vượt ngưỡng KHÔNG khoá endpoint khác)."""
        from assetcore.api.imm00 import (
            get_asset_label_data, get_asset_label_data_batch,
            AC_LABEL_DATA_RATE_LIMIT as NS)
        asset = self._make_asset("isobucket")
        # vắt kiệt bucket single (N+2 → vượt trần ở single).
        self._drain(get_asset_label_data, self._CMD_SINGLE, NS + 2, asset=asset.name)
        # batch bucket RIÊNG → call đầu vẫn 200 (KHÔNG kế thừa counter single).
        env, exc = self._http_call(
            get_asset_label_data_batch, self._CMD_BATCH, assets=[asset.name])
        self.assertIsNone(exc, f"batch bucket riêng → call đầu KHÔNG 429: {exc!r}")
        self.assertTrue(env["success"], "batch vẫn 200 trong cùng cửa sổ (counter tách)")

    # ── single → batch KHÔNG bị throttle (single hammer KHÔNG khoá batch) ───
    def test_label_data_over_limit_does_not_lock_batch(self):
        """Sau khi single đã 429, batch (cmd khác) vẫn phục vụ N call đầu — kiểm
        bất biến tách-bucket bền hơn 1 call."""
        from assetcore.api.imm00 import (
            get_asset_label_data, get_asset_label_data_batch,
            AC_LABEL_DATA_RATE_LIMIT as NS)
        asset = self._make_asset("nolock")
        self._drain(get_asset_label_data, self._CMD_SINGLE, NS + 2, asset=asset.name)
        # single bây giờ đã vượt trần.
        _, exc_s = self._http_call(get_asset_label_data, self._CMD_SINGLE, asset=asset.name)
        self.assertIsInstance(
            exc_s, (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
            "tiền đề: single đã vượt trần (429)")
        # batch vẫn phục vụ vài call đầu (≤ trần batch=20) KHÔNG 429.
        for i in range(3):
            env_b, exc_b = self._http_call(
                get_asset_label_data_batch, self._CMD_BATCH, assets=[asset.name])
            self.assertIsNone(exc_b, f"batch call #{i+1} KHÔNG bị khoá bởi single: {exc_b!r}")
            self.assertTrue(env_b["success"])

    # ── Gate-order giữ nguyên dưới ngưỡng: 403(rbac)/404/403(IDOR) ──────────
    def test_label_data_gate_order_unchanged_no_print_403(self):
        """thiếu asset.print (Guest) DƯỚI ngưỡng → 403 (KHÔNG 200, KHÔNG 429).
        Decorator KHÔNG nuốt RBAC khi chưa trần — gate-order GIỮ NGUYÊN."""
        from assetcore.api.imm00 import get_asset_label_data
        from assetcore.services.shared import rbac
        asset = self._make_asset("noprint")
        cmd = self._CMD_SINGLE
        frappe.set_user("Guest")
        try:
            self.assertFalse(rbac.can("asset.print"),
                             "tiền đề: Guest KHÔNG có asset.print")
            _, exc = self._http_call(get_asset_label_data, cmd, asset=asset.name)
            self.assertIsInstance(
                exc, frappe.PermissionError,
                f"≤N + thiếu asset.print → 403, KHÔNG {type(exc).__name__}")
        finally:
            frappe.set_user("Administrator")

    def test_label_data_gate_order_unchanged_missing_404(self):
        """asset rỗng/∄ DƯỚI ngưỡng → 404 leak-safe (KHÔNG 200, KHÔNG 500)."""
        from assetcore.api.imm00 import get_asset_label_data
        cmd = self._CMD_SINGLE
        # (a) asset ∄
        env, exc = self._http_call(
            get_asset_label_data, cmd, asset="AC-ASSET-NONEXISTENT-LDRL-ZZZ")
        self.assertIsNone(exc, f"asset ∄ KHÔNG raise (404 leak-safe): {exc!r}")
        self.assertFalse(env["success"])
        self.assertEqual(env["http_status"], 404, "asset ∄ → 404")
        # (b) asset rỗng
        env2, exc2 = self._http_call(get_asset_label_data, cmd, asset="")
        self.assertIsNone(exc2, f"asset rỗng KHÔNG raise: {exc2!r}")
        self.assertFalse(env2["success"])
        self.assertEqual(env2["http_status"], 404, "asset rỗng → 404")

    # ── single: 429 chạy TRƯỚC rbac.require("asset.print") ──────────────────
    def test_label_data_429_runs_before_rbac(self):
        """User KHÔNG asset.print (Guest), dội >N → call vượt trần → 429 (KHÔNG
        403). Decorator @rate_limit bọc NGOÀI thân → counter+throw TRƯỚC
        rbac.require("asset.print"). Đồng nhất precedent batch/mark/rotate."""
        from assetcore.api.imm00 import (
            get_asset_label_data, AC_LABEL_DATA_RATE_LIMIT as N)
        from assetcore.services.shared import rbac
        asset = self._make_asset("order")
        cmd = self._CMD_SINGLE
        frappe.set_user("Guest")
        try:
            self.assertFalse(rbac.can("asset.print"),
                             "tiền đề: Guest KHÔNG có asset.print")
            # ≤N: thiếu print → 403 (RBAC sau RL khi chưa trần).
            _, exc_under = self._http_call(get_asset_label_data, cmd, asset=asset.name)
            self.assertIsInstance(
                exc_under, frappe.PermissionError,
                "≤N + thiếu asset.print → 403 (RBAC sau RL khi chưa trần)")
            # Dội cho vượt trần (counter tăng kể cả khi thân raise 403).
            for _ in range(N):
                self._http_call(get_asset_label_data, cmd, asset=asset.name)
            _, exc_over = self._http_call(get_asset_label_data, cmd, asset=asset.name)
            self.assertIsInstance(
                exc_over,
                (frappe.RateLimitExceededError, frappe.TooManyRequestsError),
                f"vượt trần → 429 TRƯỚC PermissionError, KHÔNG {type(exc_over).__name__}")
        finally:
            frappe.set_user("Administrator")

    # ── single: 429 no-leak (KHÔNG name/asset_code/serial) ──────────────────
    def test_label_data_429_no_leak(self):
        from assetcore.api.imm00 import (
            get_asset_label_data, AC_LABEL_DATA_RATE_LIMIT as N)
        asset = self._make_asset("noleak")
        cmd = self._CMD_SINGLE
        self._drain(get_asset_label_data, cmd, N, asset=asset.name)
        _, exc = self._http_call(get_asset_label_data, cmd, asset=asset.name)
        self.assertIsNotNone(exc, "call single vượt trần PHẢI raise 429")
        msg = str(getattr(exc, "message", "") or "") + str(exc)
        for leak in (asset.name, asset.asset_code, asset.manufacturer_sn):
            self.assertNotIn(leak, msg,
                             "429 message KHÔNG leak name/asset_code/serial")

    # ── Bypass test/CLI có chủ đích — gọi TRỰC TIẾP (no frappe.request) ─────
    def test_label_data_no_request_context_bypasses(self):
        """Gọi single TRỰC TIẾP >N lần (KHÔNG set frappe.local.request) → KHÔNG 429
        (wrapper `if not frappe.request: return fn`). Đảm bảo suite cũ
        (TestGetAssetLabelData — gọi trực tiếp) KHÔNG regress."""
        from assetcore.api.imm00 import (
            get_asset_label_data, AC_LABEL_DATA_RATE_LIMIT as N)
        asset = self._make_asset("bypass")
        had_req = getattr(frappe.local, "request", None)
        frappe.local.request = None
        try:
            for _ in range(N + 5):
                resp = get_asset_label_data(asset=asset.name)
                self.assertTrue(resp["success"],
                                "single trực tiếp (no request) → KHÔNG bao giờ 429")
        finally:
            frappe.local.request = had_req

    # ── Regression — CAP_SET_VERSION KHÔNG đổi (decorator KHÔNG thêm cap) ───
    def test_cap_set_version_unchanged(self):
        from assetcore.services.shared.rbac import CAP_SET_VERSION
        self.assertEqual(
            CAP_SET_VERSION, "v104.e46d05d9a66d",
            "@rate_limit lên single KHÔNG đổi CAPABILITY_MAP; giá trị hiện hành "
            "v104.e46d05d9a66d (sau D6 tách asset.print/asset.qr.rotate)")


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

    # (9) regression: cap-set version hiện hành v104.e46d05d9a66d (sau D6).
    def test_cap_set_version_unchanged(self):
        from assetcore.services.shared.rbac import CAP_SET_VERSION
        self.assertEqual(
            CAP_SET_VERSION, "v104.e46d05d9a66d",
            "base-URL deep-link là logic dựng URL — KHÔNG thêm cap (D6 mới đổi version)")


# ──────────────────────────────────────────────────────────────────────────
# B (hardening / enumeration-safety) — no-raw-token parity trên MỌI đường ĐỌC
# AC Asset. ADR-001 §D4 rule 9: token thô (qr_token) KHÔNG BAO GIỜ rời BE qua
# endpoint đọc asset. Root cause: get_asset trả frappe.get_doc(...).as_dict() →
# leak field qr_token (hidden/read_only nhưng VẪN nằm trong as_dict). Fix: 1
# helper SSoT _strip_qr_token(doc) pop key trước _ok(). Parity: get_asset,
# get_asset_timeline, get_asset_kpi, list_assets đều KHÔNG có qr_token/token.
# Deep-link vẫn dùng qua qr_url (build_asset_label_data server-side, A3/A4).
# Test-case RED viết TRƯỚC fix (test_get_asset_no_raw_qr_token fail vì as_dict
# leak). KHÔNG cap/field/DocType/enum mới ở vòng này (CAP_SET_VERSION hiện hành
# v104.e46d05d9a66d — D6 tách asset.print/asset.qr.rotate mới đổi version).
# ──────────────────────────────────────────────────────────────────────────
class TestGetAssetNoRawQrToken(unittest.TestCase):
    """B — no-raw-token parity MỌI đường đọc AC Asset (ADR-001 D4 rule 9)."""

    @classmethod
    def setUpClass(cls):
        import uuid
        frappe.set_user("Administrator")
        # category_name có DB-unique constraint + commit dưới → uuid-suffix để
        # idempotent (leak từ run bị SIGKILL KHÔNG poison lần sau). model_name/
        # location_name KHÔNG unique nên leak vô hại; ref qua .name (autoname).
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"Thiết bị No-Raw-Token (B) {uuid.uuid4().hex[:8]}",
            "description": "Category cho test no-raw-token get_asset",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        # model_name/location_name KHÔNG DB-unique NHƯNG có app-level validate
        # ((model_name,manufacturer) & location) → uuid-suffix để leak từ run bị
        # SIGKILL (parity category) KHÔNG poison lần sau. Ref qua .name (autoname).
        _u = uuid.uuid4().hex[:8]
        cls.model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": f"NRT Dräger Evita V500 {_u}",
            "manufacturer": "Dräger Medical",
            "medical_device_class": "Class II",
            "asset_category": cls.cat.name,
        }).insert(ignore_permissions=True)
        cls.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": f"NRT Phòng ICU — Tầng 3 {_u}",
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
        self.assertEqual(data["category_name"], self.cat.category_name)

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
            CAP_SET_VERSION, "v104.e46d05d9a66d",
            "no-raw-token strip KHÔNG thêm cap; giá trị hiện hành v104.e46d05d9a66d (sau D6)")


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


# ──────────────────────────────────────────────────────────────────────────
# ADR-IMM00-LABEL-PDF (V1) — pipeline sinh PDF nhãn QR đúng khổ tem 60×100mm.
# TDD RED viết TRƯỚC impl. 11 case map D1–D8:
#  (1) service render → bytes %PDF-; (2) options dict 60×100mm+margin0+portrait;
#  (3) N asset → N trang (HTML N block + N-1 page-break); (4) QR encode qr_url,
#  HTML KHÔNG chứa qr_token thô; (5) cap-403 no-print → KHÔNG PDF/DB;
#  (6) IDOR vendor ngoài scope → 403 toàn call; (7) >200 → 413 SAU rbac no-leak;
#  (8) list rỗng → 422; (9) asset∄ trong batch → ô lỗi an toàn KHÔNG vỡ;
#  (10) render KHÔNG ghi label_printed; (11) preset lạ → 422 + field thiếu OK.
# ──────────────────────────────────────────────────────────────────────────


class TestLabelPdfPipeline(unittest.TestCase):
    """V1 — endpoint+service sinh PDF nhãn QR khổ tem nhiệt 60×100mm (ADR-LABEL-PDF)."""

    _CATEGORY_NAME = "Thiết bị PDF Nhãn (LABEL-PDF V1)"
    # Role có print=1 (DocPerm) NHƯNG vendor-scope → qua gate PRINT, đập IDOR sau.
    _IDOR_USER = "be_labelpdf_idor@example.com"
    # Role KHÔNG có print=1 trên AC Asset → thiếu cap asset.print → 403.
    _NOPRINT_USER = "be_labelpdf_noprint@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test pipeline PDF nhãn QR",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for email in (cls._IDOR_USER, cls._NOPRINT_USER):
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True,
                                  ignore_permissions=True)
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

    def _make_asset(self, suffix="", **overrides):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy PDF Nhãn {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"PDF-SN-{uniq}",
            "asset_code": f"PDF-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(overrides)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _count_label_events(self, asset_name):
        return frappe.db.count("Asset Lifecycle Event",
                               {"asset": asset_name, "event_type": "label_printed"})

    # ── (1) D1 — service render trả bytes bắt đầu magic %PDF- ────────────────
    def test_render_returns_pdf_magic_header(self):
        from assetcore.services.imm00 import render_asset_labels_pdf
        asset = self._make_asset("pdf1")
        pdf = render_asset_labels_pdf([asset.name], "tem-60x100")
        self.assertIsInstance(pdf, (bytes, bytearray),
                              "render_asset_labels_pdf trả bytes")
        self.assertTrue(bytes(pdf).startswith(b"%PDF-"),
                        "PDF bytes PHẢI bắt đầu magic header %PDF-")

    def test_endpoint_returns_pdf_via_response(self):
        """D1 — endpoint set frappe.local.response PDF (KHÔNG _ok JSON dict)."""
        from assetcore.api.imm00 import print_asset_labels_pdf
        import base64
        asset = self._make_asset("ep1")
        frappe.local.response = frappe._dict()
        ret = print_asset_labels_pdf(assets=[asset.name], preset="tem-60x100")
        # thành công → KHÔNG trả JSON envelope (return None / không success-dict)
        self.assertFalse(isinstance(ret, dict) and ret.get("success") is True,
                         "thành công KHÔNG trả JSON success-dict (trả PDF qua response)")
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "response.type = 'pdf' (Frappe set application/pdf)")
        content = frappe.local.response.get("filecontent")
        self.assertTrue(bytes(content).startswith(b"%PDF-"),
                        "response.filecontent là PDF bytes magic %PDF-")
        # parity với 'base64 decode bắt đầu %PDF-' (FE có thể base64 từ filecontent)
        self.assertTrue(base64.b64decode(base64.b64encode(bytes(content)))
                        .startswith(b"%PDF-"))

    # ── (2) D5 — options dict đúng khổ tem 60×100mm + margin0 + portrait ─────
    def test_pdf_options_page_size_60x100(self):
        from assetcore.services.imm00 import _label_pdf_options
        opt = _label_pdf_options("tem-60x100")
        self.assertEqual(opt.get("page-width"), "60mm", "page-width 60mm")
        self.assertEqual(opt.get("page-height"), "100mm", "page-height 100mm")
        for m in ("margin-top", "margin-right", "margin-bottom", "margin-left"):
            self.assertEqual(opt.get(m), "0mm",
                             f"{m} = '0mm' (chuỗi truthy chống default 15mm)")
        self.assertEqual(opt.get("orientation"), "Portrait", "khổ DỌC")
        # F6 trap: margin KHÔNG được là 0/'' (falsy → default 15mm)
        self.assertNotIn(0, [opt.get(m) for m in
                             ("margin-top", "margin-right", "margin-bottom", "margin-left")])

    # ── (3) D2 — N asset → N trang: HTML N block + N-1 page-break ────────────
    def test_one_page_per_asset(self):
        from assetcore.services.imm00 import (
            _label_html, build_asset_label_data_batch)
        names = [self._make_asset(f"pg{i}").name for i in range(3)]
        items = build_asset_label_data_batch(names)
        html = _label_html(items, "tem-60x100")
        # đếm block = số div mang class 'label' (prefix khớp cả 'label' & 'label brk')
        self.assertEqual(html.count('<div class="label'), 3,
                         "3 asset → 3 block .label (mỗi asset 1 trang)")
        # break = số block mang class 'brk' = N-1 (block cuối KHÔNG break)
        self.assertEqual(html.count('class="label brk"'), 2,
                         "3 block → 2 page-break (block cuối KHÔNG break, KHÔNG trang trắng)")

    def test_one_page_per_asset_single(self):
        from assetcore.services.imm00 import (
            _label_html, build_asset_label_data_batch)
        names = [self._make_asset("single").name]
        html = _label_html(build_asset_label_data_batch(names), "tem-60x100")
        self.assertEqual(html.count('<div class="label'), 1)
        self.assertEqual(html.count('class="label brk"'), 0,
                         "1 asset → 0 break applied (1 trang)")

    # ── (3-bis) §D16 — ĐẾM TRANG PDF THẬT (pypdf) chống BUG-LABEL-1 ──────────
    def test_pdf_real_page_count_no_blank_overflow(self):
        """RED-guard BUG-LABEL-1 (blank-overflow): đếm TRANG PDF THẬT bằng pypdf,
        KHÔNG chỉ đếm HTML block. .label height==page-height làm wkhtmltopdf đẻ
        trang TRẮNG đuôi (1 asset → 2 trang PDF) — test_one_page_per_asset cũ chỉ
        đếm HTML block nên FALSE-GREEN. Fix = .label height = height_mm−1mm
        (content < page). Test này khoá invariant 'N asset = N trang PDF THẬT'."""
        import io
        from pypdf import PdfReader
        from assetcore.services.imm00 import render_asset_labels_pdf
        a1 = self._make_asset("rpc1")
        pdf1 = render_asset_labels_pdf([a1.name], "tem-60x100")
        pages1 = len(PdfReader(io.BytesIO(bytes(pdf1))).pages)
        self.assertEqual(pages1, 1,
                         f"1 asset PHẢI = 1 trang PDF THẬT (KHÔNG blank-overflow); got {pages1}")
        names = [self._make_asset(f"rpc{i}").name for i in range(2, 5)]
        pdf3 = render_asset_labels_pdf(names, "tem-60x100")
        pages3 = len(PdfReader(io.BytesIO(bytes(pdf3))).pages)
        self.assertEqual(pages3, 3,
                         f"3 asset PHẢI = 3 trang PDF THẬT (KHÔNG xen trang trắng); got {pages3}")

    # ── (3-ter) §D16 — 3 preset PDF đều 1 trang/asset + ĐÚNG kích thước khổ ──
    def test_all_presets_one_real_page_and_correct_mediabox(self):
        """F1-FIX: 3 preset PDF (60×100/70×40/50×30) đều render-được, mỗi asset =
        1 trang PDF THẬT (KHÔNG blank), và MediaBox = ĐÚNG khổ mm (chống xoay/lệch
        khổ). 1mm = 2.8346pt."""
        import io
        from pypdf import PdfReader
        from assetcore.services.imm00 import render_asset_labels_pdf, _LABEL_PRESETS
        MM_TO_PT = 2.834645669
        a = self._make_asset("multi")
        for preset, spec in _LABEL_PRESETS.items():
            pdf = render_asset_labels_pdf([a.name], preset)
            self.assertTrue(bytes(pdf).startswith(b"%PDF-"),
                            f"preset {preset} → PDF magic %PDF-")
            reader = PdfReader(io.BytesIO(bytes(pdf)))
            self.assertEqual(len(reader.pages), 1,
                             f"preset {preset}: 1 asset = 1 trang THẬT (KHÔNG blank)")
            box = reader.pages[0].mediabox
            self.assertAlmostEqual(
                float(box.width), spec["width_mm"] * MM_TO_PT, delta=3,
                msg=f"{preset} MediaBox width ≈ {spec['width_mm']}mm (KHÔNG xoay)")
            self.assertAlmostEqual(
                float(box.height), spec["height_mm"] * MM_TO_PT, delta=3,
                msg=f"{preset} MediaBox height ≈ {spec['height_mm']}mm (KHÔNG xoay)")

    def test_pdf_options_dimensions_per_preset(self):
        """§D16 — _label_pdf_options trả ĐÚNG page-width/height cho cả 3 preset."""
        from assetcore.services.imm00 import _label_pdf_options
        cases = {"tem-60x100": ("60mm", "100mm"),
                 "tem-70x40": ("70mm", "40mm"),
                 "tem-50x30": ("50mm", "30mm")}
        for preset, (w, h) in cases.items():
            opt = _label_pdf_options(preset)
            self.assertEqual(opt.get("page-width"), w, f"{preset} page-width {w}")
            self.assertEqual(opt.get("page-height"), h, f"{preset} page-height {h}")
            for m in ("margin-top", "margin-right", "margin-bottom", "margin-left"):
                self.assertEqual(opt.get(m), "0mm", f"{preset} {m}=0mm")

    # ── (4) D4 — QR encode qr_url (deep-link), HTML KHÔNG chứa qr_token thô ──
    def test_qr_encodes_qr_url_not_raw_token(self):
        from assetcore.services.imm00 import (
            _label_html, build_asset_label_data_batch)
        asset = self._make_asset("qr1")
        raw_token = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        self.assertTrue(raw_token, "tiền đề: asset có qr_token")
        items = build_asset_label_data_batch([asset.name])
        qr_url = items[0]["qr_url"]
        html = _label_html(items, "tem-60x100")
        self.assertIn(qr_url, html,
                      "HTML chứa qr_url (deep-link /a/<token>) — encode đúng nguồn")
        self.assertIn("/a/", qr_url, "qr_url là deep-link /a/<token>")
        self.assertIn(raw_token, qr_url,
                      "tiền đề: token là path-segment của qr_url deep-link /a/<token>")
        # No-raw-token parity: token CHỈ được phép xuất hiện NHƯ path-segment của
        # qr_url deep-link (enumeration-safe), KHÔNG bao giờ dưới dạng raw-token
        # độc lập / URL desk. Strip MỌI lần xuất hiện qr_url → token KHÔNG còn ở đâu.
        html_wo_url = html.replace(qr_url, "")
        self.assertNotIn(raw_token, html_wo_url,
                         "qr_token THÔ KHÔNG xuất hiện ngoài qr_url (no-raw-token parity)")
        # token thô KHÔNG được nằm dưới dạng URL desk
        self.assertNotIn("/app/", html, "KHÔNG URL desk /app/ trên tem")
        # SVG QR inline có mặt (server-side render)
        self.assertIn("<svg", html, "QR SVG inline nhúng thẳng HTML")

    # ── (5) D6 — user thiếu asset.print → 403, KHÔNG PDF, KHÔNG đụng DB ──────
    def test_cap_403_no_pdf_no_db(self):
        from assetcore.api.imm00 import print_asset_labels_pdf
        from assetcore.services.shared import rbac
        asset = self._make_asset("cap1")
        u = self._ensure_user(self._NOPRINT_USER, ["Guest"])
        frappe.clear_cache()
        frappe.db.commit()
        before = self._count_label_events(asset.name)
        frappe.local.response = frappe._dict()
        try:
            frappe.set_user(self._NOPRINT_USER)
            self.assertFalse(rbac.can("asset.print"),
                             "tiền đề: user KHÔNG có asset.print")
            with self.assertRaises(frappe.PermissionError):
                print_asset_labels_pdf(assets=[asset.name], preset="tem-60x100")
        finally:
            frappe.set_user("Administrator")
            frappe.clear_cache()
            rbac.invalidate_capabilities(self._NOPRINT_USER)
        self.assertNotEqual(frappe.local.response.get("type"), "pdf",
                            "thiếu cap → KHÔNG set response PDF")
        self.assertEqual(self._count_label_events(asset.name), before,
                         "thiếu cap → KHÔNG đụng DB (0 label_printed)")

    # ── (6) D6 — IDOR vendor ngoài scope → 403 toàn call, KHÔNG PDF ─────────
    def test_idor_vendor_403_whole_call(self):
        from assetcore.api.imm00 import print_asset_labels_pdf
        from assetcore.services.shared import rbac
        asset = self._make_asset("idor1")
        u = self._ensure_user(self._IDOR_USER, ["Vendor Engineer", "Repair User"])
        frappe.clear_cache()
        frappe.db.commit()
        frappe.local.response = frappe._dict()
        try:
            frappe.set_user(self._IDOR_USER)
            self.assertTrue(rbac.can("asset.print"),
                            "tiền đề: user IDOR CÓ asset.print (qua gate)")
            resp = print_asset_labels_pdf(assets=[asset.name], preset="tem-60x100")
            self.assertIsInstance(resp, dict, "IDOR → Error envelope (KHÔNG PDF)")
            self.assertFalse(resp.get("success"), "vendor ngoài scope → KHÔNG success")
            self.assertEqual(resp.get("http_status"), 403,
                             "IDOR → 403 TOÀN call (no partial PDF)")
            self.assertNotEqual(frappe.local.response.get("type"), "pdf",
                                "IDOR → KHÔNG set response PDF")
        finally:
            frappe.set_user("Administrator")
            frappe.clear_cache()
            rbac.invalidate_capabilities(self._IDOR_USER)

    # ── (7) D6 — batch > 200 → 413 SAU rbac, message KHÔNG leak asset name ──
    def test_batch_over_cap_413(self):
        from assetcore.api.imm00 import print_asset_labels_pdf
        from assetcore.services.imm00 import _MAX_LABEL_BATCH
        asset = self._make_asset("over1")
        # >200 names: 1 thật + 200 fake (Admin qua rbac → tới batch-cap check).
        names = [asset.name] + [f"FAKE-{i}" for i in range(_MAX_LABEL_BATCH)]
        self.assertGreater(len(names), _MAX_LABEL_BATCH)
        frappe.local.response = frappe._dict()
        resp = print_asset_labels_pdf(assets=names, preset="tem-60x100")
        self.assertIsInstance(resp, dict, "vượt cap → Error envelope")
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 413, "vượt batch cap → 413 bucket riêng")
        self.assertNotIn(asset.name, resp.get("error", ""),
                         "message 413 KHÔNG leak asset name")
        self.assertNotEqual(frappe.local.response.get("type"), "pdf",
                            "vượt cap → KHÔNG sinh PDF")

    # ── (8) D7 — list rỗng → 422, KHÔNG PDF ────────────────────────────────
    def test_empty_list_422(self):
        from assetcore.api.imm00 import print_asset_labels_pdf
        frappe.local.response = frappe._dict()
        resp = print_asset_labels_pdf(assets=[], preset="tem-60x100")
        self.assertIsInstance(resp, dict, "list rỗng → Error envelope")
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 422, "list rỗng → 422 (BA chốt D7)")
        self.assertNotEqual(frappe.local.response.get("type"), "pdf")

    # ── (9) D7 — asset∄ trong batch → ô lỗi an toàn trong PDF, KHÔNG vỡ ─────
    def test_nonexistent_asset_renders_error_cell_no_crash(self):
        from assetcore.services.imm00 import (
            render_asset_labels_pdf, _label_html, build_asset_label_data_batch)
        asset = self._make_asset("mix1")
        names = [asset.name, "KHONG-TON-TAI-XYZ"]
        items = build_asset_label_data_batch(names)
        # batch trả ô lỗi AC-E001 cho name∄ (no drop) — pipeline KHÔNG raise.
        html = _label_html(items, "tem-60x100")
        self.assertEqual(html.count('<div class="label'), 2,
                         "mix valid+invalid → 2 block (asset∄ vẫn 1 trang)")
        pdf = render_asset_labels_pdf(names, "tem-60x100")
        self.assertTrue(bytes(pdf).startswith(b"%PDF-"),
                        "asset∄ trong batch → PDF vẫn render (KHÔNG vỡ, KHÔNG 500)")
        # leak-safe: chỉ echo name client đã gửi
        self.assertIn("KHONG-TON-TAI-XYZ", html)

    def test_endpoint_mix_valid_invalid_returns_pdf(self):
        """D7 — endpoint (Admin) mix valid+invalid → PDF (KHÔNG 404 all-or-nothing)."""
        from assetcore.api.imm00 import print_asset_labels_pdf
        asset = self._make_asset("mix2")
        frappe.local.response = frappe._dict()
        ret = print_asset_labels_pdf(
            assets=[asset.name, "KHONG-TON-TAI-ABC"], preset="tem-60x100")
        self.assertFalse(isinstance(ret, dict) and ret.get("success") is False,
                         "asset∄ KHÔNG làm vỡ thành Error envelope (ô lỗi trong PDF)")
        self.assertEqual(frappe.local.response.get("type"), "pdf")
        self.assertTrue(bytes(frappe.local.response.get("filecontent"))
                        .startswith(b"%PDF-"))

    # ── (10) D8 — render PDF KHÔNG ghi label_printed (audit-on-cancel guard) ─
    def test_render_pdf_does_not_emit_label_printed(self):
        from assetcore.api.imm00 import print_asset_labels_pdf
        asset = self._make_asset("audit1")
        before = self._count_label_events(asset.name)
        frappe.local.response = frappe._dict()
        print_asset_labels_pdf(assets=[asset.name], preset="tem-60x100")
        self.assertEqual(self._count_label_events(asset.name), before,
                         "render PDF = preview ≠ in → KHÔNG ghi label_printed (D8)")

    # ── (11) preset lạ → 422 ; asset thiếu field → PDF vẫn render ───────────
    def test_invalid_preset_422(self):
        from assetcore.api.imm00 import print_asset_labels_pdf
        asset = self._make_asset("preset1")
        frappe.local.response = frappe._dict()
        resp = print_asset_labels_pdf(assets=[asset.name], preset="khong-co-preset")
        self.assertIsInstance(resp, dict)
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 422, "preset lạ → 422")

    # ── (11-bis) Vòng 32 §D6 — preset hợp lệ BỌC whitespace/newline → STRIP 2 đầu
    #            TRƯỚC gate whitelist → render ĐÚNG khổ (parity token Vòng 6 / name
    #            Vòng 31). KHÔNG _err(422) giả. Đo PDF THẬT bằng pypdf (MediaBox).
    _MM_TO_PT = 2.834645669

    def test_print_labels_pdf_preset_whitespace_wrapped_renders_correct_size(self):
        """AC-1: preset=' tem-60x100 ' (leading/trailing space) → strip 2 đầu TRƯỚC
        gate whitelist → response.type=='pdf', 1 trang PDF THẬT, MediaBox 60×100mm
        (pypdf, point-tolerance như test_all_presets_…). KHÔNG _err(422) giả."""
        import io
        from pypdf import PdfReader
        from assetcore.api.imm00 import print_asset_labels_pdf
        asset = self._make_asset("wswrap")
        frappe.local.response = frappe._dict()
        ret = print_asset_labels_pdf(assets=[asset.name], preset=" tem-60x100 ")
        # KHÔNG rơi nhánh _err(422) — preset hợp lệ kèm whitespace vẫn render
        self.assertFalse(
            isinstance(ret, dict) and ret.get("success") is False,
            "preset hợp lệ kèm whitespace KHÔNG được _err(422) (strip TRƯỚC gate)")
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "render PDF (KHÔNG 422 giả)")
        content = frappe.local.response.get("filecontent")
        self.assertTrue(bytes(content).startswith(b"%PDF-"), "PDF magic %PDF-")
        reader = PdfReader(io.BytesIO(bytes(content)))
        self.assertEqual(len(reader.pages), 1, "1 asset = 1 trang PDF THẬT")
        box = reader.pages[0].mediabox
        self.assertAlmostEqual(float(box.width), 60 * self._MM_TO_PT, delta=3,
                               msg="MediaBox width ≈ 60mm (đúng khổ tem-60x100)")
        self.assertAlmostEqual(float(box.height), 100 * self._MM_TO_PT, delta=3,
                               msg="MediaBox height ≈ 100mm (đúng khổ tem-60x100)")

    def test_print_labels_pdf_preset_newline_tab_all_three_presets(self):
        """AC-2: áp cho CẢ 3 preset whitelist — tab/newline bọc 2 đầu vẫn render
        đúng khổ tương ứng (pypdf MediaBox). Parity 3 preset."""
        import io
        from pypdf import PdfReader
        from assetcore.api.imm00 import print_asset_labels_pdf
        cases = {
            " tem-60x100 ": (60, 100),
            "\ttem-70x40\n": (70, 40),
            " tem-50x30 ": (50, 30),
        }
        for raw, (w_mm, h_mm) in cases.items():
            asset = self._make_asset(f"ws3-{w_mm}x{h_mm}")
            frappe.local.response = frappe._dict()
            ret = print_asset_labels_pdf(assets=[asset.name], preset=raw)
            self.assertFalse(
                isinstance(ret, dict) and ret.get("success") is False,
                f"preset {raw!r} (đã-strip hợp lệ) KHÔNG được _err(422)")
            self.assertEqual(frappe.local.response.get("type"), "pdf",
                             f"preset {raw!r} → render PDF")
            content = frappe.local.response.get("filecontent")
            reader = PdfReader(io.BytesIO(bytes(content)))
            self.assertEqual(len(reader.pages), 1, f"{raw!r}: 1 trang THẬT")
            box = reader.pages[0].mediabox
            self.assertAlmostEqual(
                float(box.width), w_mm * self._MM_TO_PT, delta=3,
                msg=f"{raw!r} MediaBox width ≈ {w_mm}mm")
            self.assertAlmostEqual(
                float(box.height), h_mm * self._MM_TO_PT, delta=3,
                msg=f"{raw!r} MediaBox height ≈ {h_mm}mm")

    def test_print_labels_pdf_preset_internal_space_still_422(self):
        """AC-3 (no-over-normalize): CHỈ strip 2 đầu — KHÔNG lowercase/transform
        GIỮA chuỗi. 'tem 60x100' (space GIỮA), 'tem-99x99' (lạ), 'TEM-60X100'
        (case khác) → KHÔNG ∈ whitelist → GIỮ _err 422 + 'Khổ tem không hợp lệ.'.
        Whitelist KHÔNG bị nới."""
        from assetcore.api.imm00 import print_asset_labels_pdf, _ERR_LABEL_PRESET
        asset = self._make_asset("internal")
        for bad in ("tem 60x100", "tem-99x99", "TEM-60X100"):
            frappe.local.response = frappe._dict()
            resp = print_asset_labels_pdf(assets=[asset.name], preset=bad)
            self.assertIsInstance(resp, dict, f"{bad!r}: Error envelope dict")
            self.assertFalse(resp.get("success"), f"{bad!r}: success=false")
            self.assertEqual(resp.get("http_status"), 422,
                             f"{bad!r}: preset lạ/space-giữa/case → 422")
            self.assertEqual(resp.get("error"), _ERR_LABEL_PRESET,
                             f"{bad!r}: message == 'Khổ tem không hợp lệ.'")
            self.assertNotEqual(frappe.local.response.get("type"), "pdf",
                                f"{bad!r}: KHÔNG render PDF")

    def test_print_labels_pdf_preset_blank_after_strip_falls_to_resolver(self):
        """AC-4 (parity empty-path): preset rỗng-sau-strip ('   '/'\\n') → coi như
        not preset → rơi nhánh _resolve_label_preset() (site_config → DEFAULT
        'tem-60x100'), KHÔNG 422, KHÔNG raise. Mock frappe.conf KHÔNG set key →
        DEFAULT_LABEL_PRESET → render khổ 60×100mm."""
        import io
        from unittest.mock import patch
        from pypdf import PdfReader
        from assetcore.api import imm00 as _api
        from assetcore.services import imm00 as _svc
        for blank in ("   ", "\n", "\t  \n"):
            asset = self._make_asset("blankstrip")
            frappe.local.response = frappe._dict()
            # site_config KHÔNG set assetcore_label_preset → resolver → DEFAULT
            with patch.object(_svc.frappe, "conf", _svc.frappe._dict()):
                ret = _api.print_asset_labels_pdf(assets=[asset.name], preset=blank)
            self.assertFalse(
                isinstance(ret, dict) and ret.get("success") is False,
                f"preset {blank!r} (rỗng-sau-strip) → resolver, KHÔNG 422")
            self.assertEqual(frappe.local.response.get("type"), "pdf",
                             f"{blank!r}: render PDF khổ DEFAULT")
            content = frappe.local.response.get("filecontent")
            reader = PdfReader(io.BytesIO(bytes(content)))
            self.assertEqual(len(reader.pages), 1, f"{blank!r}: 1 trang THẬT")
            box = reader.pages[0].mediabox
            self.assertAlmostEqual(
                float(box.width), 60 * self._MM_TO_PT, delta=3,
                msg=f"{blank!r} → DEFAULT khổ 60mm")
            self.assertAlmostEqual(
                float(box.height), 100 * self._MM_TO_PT, delta=3,
                msg=f"{blank!r} → DEFAULT khổ 100mm")

    def test_print_labels_pdf_preset_nonstr_safe(self):
        """AC-4 (parity): preset non-str (0/None qua coercion) → isinstance guard →
        '' → nhánh resolver, KHÔNG raise/500, render DEFAULT 60×100mm."""
        import io
        from unittest.mock import patch
        from pypdf import PdfReader
        from assetcore.api import imm00 as _api
        from assetcore.services import imm00 as _svc
        for nonstr in (0, None):
            asset = self._make_asset("nonstr")
            frappe.local.response = frappe._dict()
            raised = None
            try:
                with patch.object(_svc.frappe, "conf", _svc.frappe._dict()):
                    ret = _api.print_asset_labels_pdf(
                        assets=[asset.name], preset=nonstr)
            except Exception as e:  # noqa: BLE001 — chứng minh KHÔNG raise
                raised = e
                ret = None
            self.assertIsNone(raised,
                              f"preset={nonstr!r} non-str KHÔNG raise (got {raised!r})")
            self.assertFalse(
                isinstance(ret, dict) and ret.get("success") is False,
                f"preset={nonstr!r} → resolver, KHÔNG 422/500")
            self.assertEqual(frappe.local.response.get("type"), "pdf",
                             f"preset={nonstr!r} → render PDF DEFAULT")
            content = frappe.local.response.get("filecontent")
            reader = PdfReader(io.BytesIO(bytes(content)))
            box = reader.pages[0].mediabox
            self.assertAlmostEqual(float(box.width), 60 * self._MM_TO_PT, delta=3)
            self.assertAlmostEqual(float(box.height), 100 * self._MM_TO_PT, delta=3)

    # ── (12) §D16 hardening — render lỗi runtime → _err VI sạch, KHÔNG 500/traceback
    def test_render_failure_returns_vi_error_no_traceback(self):
        """pdfkit/wkhtmltopdf raise runtime → endpoint trả Error envelope VI
        (HTTP-200, http_status 500) KHÔNG raise/leak traceback (DONE-gate). Chống
        lỗi 'Không thể tạo PDF nhãn' biến thành 500-traceback ở môi trường live."""
        from unittest.mock import patch
        from assetcore.api import imm00 as _api
        asset = self._make_asset("renderfail")
        frappe.local.response = frappe._dict()
        with patch.object(_api, "_svc_render_asset_labels_pdf",
                          side_effect=OSError("wkhtmltopdf exploded")):
            resp = _api.print_asset_labels_pdf(
                assets=[asset.name], preset="tem-60x100")
        self.assertIsInstance(resp, dict, "render lỗi → Error envelope dict, KHÔNG raise")
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 500, "render lỗi → 500 trong envelope")
        self.assertIn("PDF", resp.get("error", ""), "message VI nhắc PDF")
        self.assertNotIn("Traceback", str(resp), "KHÔNG leak traceback ra client")
        self.assertNotEqual(frappe.local.response.get("type"), "pdf",
                            "render lỗi → KHÔNG set response.type=pdf")
        self.assertNotEqual(frappe.local.response.get("type"), "pdf")

    def test_missing_field_renders_blank_no_crash(self):
        from assetcore.services.imm00 import (
            render_asset_labels_pdf, build_asset_label_data_batch, _label_html)
        # asset KHÔNG có manufacturer_sn / device_model → field '' fallback.
        asset = self._make_asset("nofield", manufacturer_sn="")
        items = build_asset_label_data_batch([asset.name])
        self.assertEqual(items[0]["manufacturer_sn"], "",
                         "field rỗng coerced về '' (no None)")
        html = _label_html(items, "tem-60x100")
        self.assertIn('class="label"', html, "block vẫn render dù thiếu field")
        pdf = render_asset_labels_pdf([asset.name], "tem-60x100")
        self.assertTrue(bytes(pdf).startswith(b"%PDF-"),
                        "thiếu field → PDF magic %PDF còn đúng (KHÔNG vỡ)")

    # ── D3 — nhãn render đủ 5 field LABEL SPEC D5 (no EN status-leak) ───────
    def test_label_html_contains_5_fields_and_vi_labels(self):
        from assetcore.services.imm00 import (
            _label_html, build_asset_label_data_batch, _lifecycle_vi)
        import uuid
        mfr = f"NSX Test PDF {uuid.uuid4().hex[:8]}"
        # self-healing: purge orphan model leaked bởi aborted prior run (UNIQUE
        # model_name+manufacturer) — KHÔNG phụ thuộc DB sạch.
        _orphan = frappe.db.get_value(
            "IMM Device Model", {"model_name": "Model Nhãn PDF Test"}, "name")
        if _orphan:
            for _a in frappe.get_all(
                    "AC Asset", filters={"device_model": _orphan}, pluck="name"):
                _purge_asset(_a)
            frappe.delete_doc("IMM Device Model", _orphan, force=True,
                              ignore_permissions=True)
        model = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": "Model Nhãn PDF Test",
            "manufacturer": mfr,
            "asset_category": self.cat.name,
        }).insert(ignore_permissions=True)
        try:
            asset = self._make_asset("d5", device_model=model.name,
                                     lifecycle_status="Under Maintenance")
            items = build_asset_label_data_batch([asset.name])
            html = _label_html(items, "tem-60x100")
            # 5 nhãn-VI cố định (QR là field 1, không nhãn chữ) — V3 thêm 'Trạng thái'
            for vi in ("Model", "Số serial NSX", "Tên tài sản", "Mã tài sản",
                       "Trạng thái"):
                self.assertIn(vi, html, f"thiếu nhãn VI '{vi}' (LABEL SPEC D5/D3)")
            # giá trị 5 field có mặt
            self.assertIn(items[0]["asset_code"], html)
            self.assertIn(items[0]["asset_name"], html)
            self.assertIn(items[0]["manufacturer_sn"], html)
            self.assertIn("Model Nhãn PDF Test", html)
            # V3 §D3: field thứ 5 lifecycle_status dịch VI render TRÊN tem (bắt buộc)
            self.assertEqual(_lifecycle_vi("Under Maintenance"), "Đang bảo trì",
                             "lifecycle_status dịch VI (SSoT labels.ts)")
            self.assertIn("Đang bảo trì", html,
                          "V3 §D3: giá trị VI lifecycle_status render trên tem")
            self.assertNotIn("Under Maintenance", html,
                             "mã EN status thô KHÔNG lọt tem (no EN-leak)")
        finally:
            # purge asset TRƯỚC khi xoá model (model.on_trash chặn xoá khi còn
            # asset tham chiếu — LinkExistsError). asset đã trong self._created
            # nhưng tearDown chạy SAU finally → purge tường minh ở đây.
            for n in list(self._created):
                _purge_asset(n)
                self._created.remove(n)
            frappe.delete_doc("IMM Device Model", model.name,
                              force=True, ignore_permissions=True)


class TestLabelPdfEmptyQrUrlSafeCell(unittest.TestCase):
    """Vòng 30 — empty/whitespace ``qr_url`` ở tem PDF in → Ô-LỖI AN TOÀN
    (parity AC-E001 + FE ``AssetQrLabel.vue:73``), chặn junk-QR rỗng dán lên thiết bị.

    BUG (drift / contract-violation BR-00-28): nhánh non-error của ``_label_block``
    gọi ``_qr_svg_inline(qr_url)`` NGAY mà KHÔNG guard ``qr_url`` rỗng/whitespace.
    ``pyqrcode.create('')``/``create('   ')`` KHÔNG raise — nó encode 1 QR RÁC vô
    nghĩa + nhúng ``data-qr-url=""`` rỗng. Tem khách quét = junk-QR. ``build_asset_
    label_data(_batch)`` luôn build qr_url qua ``_build_qr_url`` (KHÔNG bao giờ rỗng),
    NHƯNG drift/manual-inject/contract-violation có thể đưa item ``{qr_url:''}``
    (non-error) vào render-tier → cần guard PHÒNG-THỦ ở chính ``_label_block``.

    FIX (render-tier, chỉ ``_label_block``): SAU nhánh ``error`` thêm guard
    ``_qr = (item.get('qr_url') or '').strip(); if not _qr: return <ô-lỗi-an-toàn>``
    dùng CÙNG shape/class ``label-error`` nhánh AC-E001 (KHÔNG <svg> QR, KHÔNG
    ``data-qr-url`` rỗng) với nhãn VI SSoT 'Không tạo được mã QR'. Chỉ khi qua guard
    mới gọi ``_qr_svg_inline``. Invariant N→N trang GIỮ NGUYÊN (1 asset xấu KHÔNG
    giết batch). Đo ở TẦNG PDF THẬT bằng pypdf (KHÔNG đếm HTML block).
    """

    _CATEGORY_NAME = "Thiết bị PDF Nhãn QrRỗng (LABEL-PDF QREMPTY)"
    _ERR_QR_VI = "Không tạo được mã QR"   # SSoT nhãn-lỗi qr_url rỗng (parity FE :124)
    _ERR_ASSET_VI = "Không tìm thấy tài sản"  # nhánh AC-E001 (KHÁC nhánh qr rỗng)

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test ô-lỗi-an-toàn qr_url rỗng tầng PDF",
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

    def _make_asset(self, suffix="", **overrides):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy PDF QrRỗng {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"QREMPTY-SN-{uniq}",
            "asset_code": f"QREMPTY-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(overrides)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    @staticmethod
    def _render_pdf_from_items(items, preset):
        """Render PDF THẬT từ items HAND-CRAFTED (mirror render_asset_labels_pdf
        NHƯNG bỏ qua build_asset_label_data_batch → cho phép inject item dị thường
        {qr_url:''} mà pipeline-build hợp lệ KHÔNG bao giờ tạo). KHÔNG đụng prod."""
        import pdfkit
        from assetcore.services.imm00 import _label_html, _label_pdf_options
        html = _label_html(items, preset)
        options = _label_pdf_options(preset)
        pdf = pdfkit.from_string(html, False, options=options)
        return pdf if isinstance(pdf, (bytes, bytearray)) else bytes(pdf)

    @staticmethod
    def _page_text(pdf_bytes):
        """Trả (reader, text_chuẩn-hoá). pypdf extract_text chèn \\t/\\n GIỮA glyph
        (ngắt từ tuỳ layout) → gộp MỌI khoảng-trắng về 1 space để assert chuỗi VI
        liền mạch ('Không tạo được mã QR') KHÔNG false-fail vì tách-từ của pypdf."""
        import io
        import re
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(bytes(pdf_bytes)))
        raw = "".join(p.extract_text() or "" for p in reader.pages)
        return reader, re.sub(r"\s+", " ", raw)

    # ── TC1 — no-regress baseline: item hợp lệ → 1 trang + QR <svg> + data-qr-url ─
    def test_tc1_valid_item_renders_qr_svg_one_page(self):
        from assetcore.services.imm00 import (
            render_asset_labels_pdf, _label_html, build_asset_label_data_batch)
        asset = self._make_asset("tc1")
        items = build_asset_label_data_batch([asset.name])
        qr_url = items[0]["qr_url"]
        self.assertTrue(qr_url and qr_url.strip(), "tiền đề: qr_url hợp lệ KHÔNG rỗng")
        html = _label_html(items, "tem-60x100")
        self.assertIn("<svg", html, "item hợp lệ → QR SVG render")
        self.assertIn(f'data-qr-url="{qr_url}"', html,
                      "item hợp lệ → data-qr-url = qr_url đúng (auditable)")
        import io
        from pypdf import PdfReader
        pdf = render_asset_labels_pdf([asset.name], "tem-60x100")
        self.assertEqual(len(PdfReader(io.BytesIO(bytes(pdf))).pages), 1,
                         "1 asset hợp lệ = 1 trang PDF THẬT")

    # ── TC2 (assert-chính) — non-error {qr_url:''} → ô-lỗi-an-toàn, 0 QR, 0 raise ─
    def test_tc2_empty_qr_url_renders_safe_error_cell_no_qr(self):
        from assetcore.services.imm00 import _label_block, _label_html
        item = {"name": "DRIFT-EMPTY-001", "asset_code": "DRIFT-EMPTY-001",
                "asset_name": "X", "qr_url": ""}
        # service-tier: KHÔNG raise, KHÔNG <svg>, KHÔNG data-qr-url rỗng.
        block = _label_block(item, "tem-60x100", is_last=True)
        self.assertNotIn("<svg", block,
                         "qr_url rỗng → KHÔNG encode QR (no junk-QR)")
        self.assertNotIn('data-qr-url=""', block,
                         "qr_url rỗng → KHÔNG nhúng data-qr-url rỗng")
        self.assertNotIn("data-qr-url", block,
                         "ô-lỗi-an-toàn KHÔNG mang data-qr-url")
        self.assertIn("label-error", block,
                      "tái dùng shape/class label-error nhánh AC-E001")
        self.assertIn(self._ERR_QR_VI, block,
                      "ô-lỗi mang nhãn VI 'Không tạo được mã QR' (no EN-leak)")
        # PDF THẬT: 1 trang, KHÔNG <svg> QR cho ô đó, text trang chứa nhãn-lỗi VI.
        pdf = self._render_pdf_from_items([item], "tem-60x100")
        reader, text = self._page_text(pdf)
        self.assertEqual(len(reader.pages), 1,
                         "1 item (qr rỗng) = 1 trang PDF THẬT (no blank-overflow)")
        self.assertNotIn(b"<svg", bytes(pdf),
                         "PDF bytes KHÔNG chứa <svg> QR cho ô qr_url rỗng")
        self.assertIn(self._ERR_QR_VI, text,
                      "trang PDF chứa text VI 'Không tạo được mã QR'")

    # ── TC3 — whitespace qr_url → .strip() rỗng → CÙNG ô-lỗi-an-toàn TC2 ────────
    def test_tc3_whitespace_qr_url_same_safe_error_cell(self):
        from assetcore.services.imm00 import _label_block
        item = {"name": "DRIFT-WS-001", "asset_code": "DRIFT-WS-001",
                "qr_url": "   "}
        block = _label_block(item, "tem-60x100", is_last=True)
        self.assertNotIn("<svg", block,
                         "qr_url whitespace → KHÔNG encode whitespace thành QR")
        self.assertNotIn("data-qr-url", block,
                         "whitespace → ô-lỗi-an-toàn KHÔNG data-qr-url")
        self.assertIn("label-error", block)
        self.assertIn(self._ERR_QR_VI, block,
                      "whitespace .strip() rỗng → CÙNG nhãn-lỗi VI TC2")

    # ── TC4 — invariant N→N + mix: [ok, qr-rỗng, AC-E001, ok] → 4 trang, 2 nhánh lỗi
    def test_tc4_mixed_batch_n_to_n_distinct_error_branches(self):
        from assetcore.services.imm00 import build_asset_label_data
        a1 = self._make_asset("tc4a")
        a2 = self._make_asset("tc4b")
        ok1 = build_asset_label_data(a1.name)
        ok2 = build_asset_label_data(a2.name)
        empty_item = {"name": "DRIFT-EMPTY-MIX", "asset_code": "DRIFT-EMPTY-MIX",
                      "qr_url": ""}
        err_item = {"name": "KHONG-TON-TAI-MIX", "error": "AC-E001"}
        items = [ok1, empty_item, err_item, ok2]
        pdf = self._render_pdf_from_items(items, "tem-60x100")
        reader, text = self._page_text(pdf)
        self.assertEqual(len(reader.pages), 4,
                         "[ok, qr-rỗng, error, ok] → 4 trang (1 xấu KHÔNG giết batch)")
        # 2 nhánh lỗi KHÁC NHAU, KHÔNG nhầm.
        self.assertIn(self._ERR_QR_VI, text,
                      "asset qr-rỗng = nhánh 'Không tạo được mã QR'")
        self.assertIn(self._ERR_ASSET_VI, text,
                      "asset∄ = nhánh AC-E001 'Không tìm thấy tài sản'")
        # 2 asset ok VẪN có QR (ít nhất 2 <svg> trong HTML nguồn).
        from assetcore.services.imm00 import _label_html
        html = _label_html(items, "tem-60x100")
        self.assertGreaterEqual(html.count("<svg"), 2,
                                "2 asset ok VẪN render QR (chỉ 1 ô rỗng + 1 ô error mất QR)")

    # ── TC5 — MediaBox mỗi preset đúng khổ mm KỂ CẢ khi có ô-lỗi-qr ─────────────
    def test_tc5_mediabox_correct_per_preset_with_empty_qr_cell(self):
        from assetcore.services.imm00 import _LABEL_PRESETS
        MM_TO_PT = 2.834645669
        empty_item = {"name": "DRIFT-EMPTY-MB", "asset_code": "DRIFT-EMPTY-MB",
                      "qr_url": ""}
        for preset, spec in _LABEL_PRESETS.items():
            pdf = self._render_pdf_from_items([empty_item], preset)
            reader, _ = self._page_text(pdf)
            self.assertEqual(len(reader.pages), 1,
                             f"{preset}: ô-lỗi-qr = 1 trang (khổ KHÔNG lệch vì nhánh lỗi)")
            box = reader.pages[0].mediabox
            self.assertAlmostEqual(
                float(box.width), spec["width_mm"] * MM_TO_PT, delta=3,
                msg=f"{preset} MediaBox width ≈ {spec['width_mm']}mm (ô-lỗi KHÔNG lệch khổ)")
            self.assertAlmostEqual(
                float(box.height), spec["height_mm"] * MM_TO_PT, delta=3,
                msg=f"{preset} MediaBox height ≈ {spec['height_mm']}mm (ô-lỗi KHÔNG lệch khổ)")

    # ── TC6 (no-junk-encode guard) — qr_url rỗng → _label_block KHÔNG gọi pyqrcode
    def test_tc6_no_qr_encode_called_when_qr_url_empty(self):
        from unittest.mock import patch
        from assetcore.services import imm00 as _svc
        empty_item = {"name": "DRIFT-EMPTY-SPY", "asset_code": "DRIFT-EMPTY-SPY",
                      "qr_url": ""}
        ws_item = {"name": "DRIFT-WS-SPY", "asset_code": "DRIFT-WS-SPY",
                   "qr_url": "  \t  "}
        with patch.object(_svc, "_qr_svg_inline",
                          side_effect=AssertionError(
                              "_qr_svg_inline KHÔNG được gọi khi qr_url rỗng/whitespace")
                          ) as spy:
            _svc._label_block(empty_item, "tem-60x100", is_last=True)
            _svc._label_block(ws_item, "tem-70x40", is_last=True)
            spy.assert_not_called()


class TestLabelPdfNoRawTokenAtPdfLevel(unittest.TestCase):
    """No-raw-token parity ở TẦNG PDF THẬT (pypdf) — REGRESSION GUARD (ADR §D4).

    `test_qr_encodes_qr_url_not_raw_token` (TestLabelPdfPipeline) CHỈ assert ở
    HTML source: token thô KHÔNG xuất hiện ngoài qr_url. Đó là false-green gap với
    constraint 'QR encode qr_url KHÔNG raw token — parity MỌI đường', vì tem khách
    cầm/quét là **PDF in THẬT**, không phải HTML. Class này đóng gap đó: render
    PDF THẬT bằng ``render_asset_labels_pdf`` rồi assert (a) ``token.encode() not
    in bytes(pdf)`` (bytes thô) VÀ (b) ``token not in extract_text`` (pypdf), trên
    MỌI preset + CẢ batch + nhánh ô-lỗi (AC-E001 echo name).

    INVARIANT: raw ``qr_token`` (đọc từ DB) — và full ``qr_url`` / deep-link prefix
    ``/a/`` — chỉ tồn tại trong QR VECTOR (camera-scan), KHÔNG enumerate được dưới
    dạng plain-text từ file PDF. FUNCTIONAL GIỮ NGUYÊN: QR vẫn encode đúng qr_url
    deep-link (verify ở tầng HTML/SVG — KHÔNG hồi quy khả năng quét).

    KHÔNG sửa logic production: probe live đã chứng minh output hiện tại sạch
    (token 22 ký tự KHÔNG có trong pdf_bytes/extract_text; ``/a/`` KHÔNG trong
    text). Đây là REGRESSION GUARD — nếu cố tình inject raw token plaintext vào
    output (vd bỏ ``_strip``/đổi ``data-qr-url`` thành text hiển thị) → TC-1/2/3/5
    PHẢI FAIL (TC-PDF-NORAW-6 RED-first proof, chạy thủ công khi review).

    Đếm trang dùng ``PdfReader(...).pages`` (chống false-green BUG-LABEL-1 —
    KHÔNG đếm HTML block).
    """

    _CATEGORY_NAME = "Thiết bị PDF Nhãn NoRaw (LABEL-PDF NORAW)"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test no-raw-token tầng PDF thật",
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

    def _make_asset(self, suffix="", **overrides):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy NoRaw {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"NORAW-SN-{uniq}",
            "asset_code": f"NORAW-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(overrides)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    @staticmethod
    def _pdf_text(pdf_bytes) -> str:
        """Text trích xuất bằng pypdf (analog quét file PDF nhãn đã in)."""
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(bytes(pdf_bytes)))
        return "".join(p.extract_text() or "" for p in reader.pages)

    def _raw_token(self, asset_name) -> str:
        token = frappe.db.get_value("AC Asset", asset_name, "qr_token")
        self.assertTrue(token, "tiền đề: asset có qr_token trong DB")
        return token

    # ── TC-PDF-NORAW-1 — mọi preset: token thô KHÔNG ở bytes/text PDF ────────
    def test_no_raw_token_in_pdf_bytes_and_text_all_presets(self):
        """TC-PDF-NORAW-1: với MỖI preset trong _LABEL_PRESETS, render 1 asset có
        qr_token → assert `token.encode() not in bytes(pdf)` VÀ `token not in
        extract_text`. RED-guard: inject token plaintext vào block → FAIL."""
        from assetcore.services.imm00 import (
            render_asset_labels_pdf, _LABEL_PRESETS)
        a = self._make_asset("p1")
        token = self._raw_token(a.name)
        for preset in _LABEL_PRESETS:
            pdf = bytes(render_asset_labels_pdf([a.name], preset))
            self.assertTrue(pdf.startswith(b"%PDF-"),
                            f"preset {preset} → PDF magic %PDF-")
            self.assertNotIn(
                token.encode(), pdf,
                f"[{preset}] raw qr_token KHÔNG ở BYTES thô PDF (no-raw-token)")
            text = self._pdf_text(pdf)
            self.assertNotIn(
                token, text,
                f"[{preset}] raw qr_token KHÔNG ở TEXT trích pypdf (chỉ ở QR vector)")

    # ── TC-PDF-NORAW-2 — batch: KHÔNG token nào leak + N→N trang THẬT ────────
    def test_no_raw_token_in_batch_pdf_and_page_count(self):
        """TC-PDF-NORAW-2: render lô 3 asset (token khác nhau) → assert KHÔNG
        token nào trong bytes/text của PDF lô; số trang == 3 (PdfReader.pages —
        đồng thời chốt N→N trang, chống false-green BUG-LABEL-1)."""
        import io
        from pypdf import PdfReader
        from assetcore.services.imm00 import render_asset_labels_pdf
        assets = [self._make_asset(f"b{i}") for i in range(3)]
        names = [a.name for a in assets]
        tokens = [self._raw_token(n) for n in names]
        self.assertEqual(len(set(tokens)), 3, "tiền đề: 3 token PHẢI khác nhau")
        for preset in ("tem-60x100", "tem-70x40", "tem-50x30"):
            pdf = bytes(render_asset_labels_pdf(names, preset))
            text = self._pdf_text(pdf)
            for n, token in zip(names, tokens):
                self.assertNotIn(
                    token.encode(), pdf,
                    f"[{preset}] token của {n} KHÔNG ở bytes lô")
                self.assertNotIn(
                    token, text,
                    f"[{preset}] token của {n} KHÔNG ở text lô")
        # chốt N→N trang trên preset mặc định (PdfReader.pages — KHÔNG đếm block)
        pdf = bytes(render_asset_labels_pdf(names, "tem-60x100"))
        pages = len(PdfReader(io.BytesIO(pdf)).pages)
        self.assertEqual(pages, 3,
                         f"3 asset = 3 trang PDF THẬT (no blank-overflow); got {pages}")

    # ── TC-PDF-NORAW-3 — deep-link (/a/ + full qr_url) KHÔNG ở TEXT PDF ──────
    def test_deep_link_not_in_extracted_text(self):
        """TC-PDF-NORAW-3: assert `/a/` và full qr_url của asset KHÔNG xuất hiện
        trong extracted_text (deep-link chỉ ở QR vector, không plain-text) — token
        CHỈ camera-scan được, KHÔNG enumerate từ file PDF."""
        from assetcore.services.imm00 import (
            render_asset_labels_pdf, build_asset_label_data_batch, _LABEL_PRESETS)
        a = self._make_asset("dl1")
        qr_url = build_asset_label_data_batch([a.name])[0]["qr_url"]
        self.assertIn("/a/", qr_url, "tiền đề: qr_url là deep-link /a/<token>")
        for preset in _LABEL_PRESETS:
            text = self._pdf_text(render_asset_labels_pdf([a.name], preset))
            self.assertNotIn(
                qr_url, text,
                f"[{preset}] full qr_url KHÔNG ở text PDF (chỉ trong QR vector)")
            self.assertNotIn(
                "/a/", text,
                f"[{preset}] deep-link prefix '/a/' KHÔNG ở text PDF")

    # ── TC-PDF-NORAW-4 — FUNCTIONAL GIỮ: HTML/SVG vẫn encode qr_url + /a/ ────
    def test_functional_qr_url_preserved_in_html_svg(self):
        """TC-PDF-NORAW-4: cùng asset, assert `_label_html([item],preset)` VẪN
        chứa qr_url + '/a/' + QR SVG (encode đúng nguồn) — chứng minh KHÔNG hồi
        quy khả năng quét, chỉ siết leak TEXT ở tầng PDF."""
        from assetcore.services.imm00 import (
            _label_html, build_asset_label_data_batch)
        a = self._make_asset("fn1")
        items = build_asset_label_data_batch([a.name])
        qr_url = items[0]["qr_url"]
        html = _label_html(items, "tem-60x100")
        self.assertIn(qr_url, html,
                      "HTML VẪN chứa qr_url (encode đúng nguồn — không hồi quy quét)")
        self.assertIn("/a/", html, "HTML chứa deep-link prefix /a/")
        self.assertIn("<svg", html, "QR SVG inline nhúng thẳng HTML (server-side)")

    # ── TC-PDF-NORAW-5 — mix valid + name∄ (AC-E001 echo): KHÔNG leak token ──
    def test_error_cell_mix_no_token_leak(self):
        """TC-PDF-NORAW-5: lô gồm 1 asset hợp lệ + 1 name∄ (AC-E001 echo) → PDF ra
        (mix valid/invalid) + assert token của asset hợp lệ KHÔNG leak bytes/text;
        ô lỗi KHÔNG chứa token/`/a/` (echo name client gửi, KHÔNG QR)."""
        import io
        from pypdf import PdfReader
        from assetcore.services.imm00 import (
            render_asset_labels_pdf, build_asset_label_data_batch)
        a = self._make_asset("mix1")
        token = self._raw_token(a.name)
        missing = "NORAW-ASSET-DOES-NOT-EXIST-9999"
        names = [a.name, missing]
        # tiền đề: batch trả ô lỗi AC-E001 đúng index cho name∄ (KHÔNG drop)
        batch = build_asset_label_data_batch(names)
        self.assertEqual(batch[1].get("error"), "AC-E001",
                         "tiền đề: name∄ → {error:'AC-E001'} (echo name)")
        for preset in ("tem-60x100", "tem-70x40", "tem-50x30"):
            pdf = bytes(render_asset_labels_pdf(names, preset))
            self.assertTrue(pdf.startswith(b"%PDF-"),
                            f"[{preset}] mix valid/invalid VẪN ra PDF (KHÔNG vỡ)")
            text = self._pdf_text(pdf)
            self.assertNotIn(
                token.encode(), pdf,
                f"[{preset}] token asset hợp lệ KHÔNG leak bytes (ô lỗi cùng lô)")
            self.assertNotIn(
                token, text,
                f"[{preset}] token asset hợp lệ KHÔNG leak text (ô lỗi cùng lô)")
            self.assertNotIn(
                "/a/", text,
                f"[{preset}] ô lỗi KHÔNG QR/deep-link; valid-cell deep-link chỉ ở vector")
        # mix = 2 trang THẬT (valid + error-cell đều 1 trang — giữ N→N trang)
        pdf = bytes(render_asset_labels_pdf(names, "tem-60x100"))
        pages = len(PdfReader(io.BytesIO(pdf)).pages)
        self.assertEqual(pages, 2,
                         f"mix valid+error = 2 trang PDF THẬT; got {pages}")


class TestLabelPdfStatusViPresenceAware(unittest.TestCase):
    """Vòng 41 — dòng "Trạng thái" trên TEM IN PDF: bịt '—' CÂM + presence-aware.

    BUG (parity Vòng 22 scan-view): asset có ``lifecycle_status`` RỖNG ('') hoặc
    MÃ LẠ/DRIFT/LEGACY ngoài 8 mã canonical → ``_lifecycle_vi`` cũ trả '' →
    ``_label_block`` rớt vào ``{val or "—"}`` → in '—' CÂM (presence-blind: KHÔNG
    phân biệt "không có data" với render lỗi). Fix = ``_lifecycle_vi`` rỗng/lạ →
    'Chưa rõ' (nhãn VI an toàn, no-EN-leak). Verify ở TẦNG PDF THẬT bằng
    ``pypdf.PdfReader.extract_text()`` (KHÔNG đếm HTML block — chống false-green).

    INVARIANT giữ nguyên: N asset = N trang (PdfReader.pages == N) + MediaBox =
    đúng khổ mm của preset; dòng Trạng thái đổi KHÔNG làm tràn trang. 8 mã
    canonical GIỮ nhãn VI cũ (no-regress). empty vs unknown CÙNG render 'Chưa rõ'
    (an-toàn-thống-nhất). KHÔNG còn bất kỳ status nào in '—' câm trên dòng status.

    KHÔNG đụng QR encode/qr_url/token/rotate/resolve/scan-action — chỉ tầng render
    nhãn dòng status.
    """

    _CATEGORY_NAME = "Thiết bị PDF Status VI (LABEL-PDF V41)"
    _UNKNOWN_VI = "Chưa rõ"
    # Mã canonical → nhãn VI cũ (no-regress) — SSoT _LIFECYCLE_VI services/imm00.
    _CANONICAL_VI = {
        "Active": "Đang hoạt động",
        "Out of Service": "Ngừng sử dụng",
        "Decommissioned": "Đã thanh lý",
        "Commissioned": "Đã đưa vào sử dụng",
        "Under Maintenance": "Đang bảo trì",
    }

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test status VI presence-aware trên tem PDF",
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

    def _make_asset(self, suffix="", *, status="Active"):
        """Insert asset rồi GHI THẲNG DB lifecycle_status (bypass Select-validate).

        ``lifecycle_status`` là Select reqd với 8 option canonical → KHÔNG thể
        insert '' hay mã drift qua DocType. Insert 'Active' (hợp lệ) rồi
        ``frappe.db.set_value`` ghi raw '' / 'RANDOM_DRIFT_XYZ' để mô phỏng
        rỗng/drift trong DB — render đọc raw qua build_asset_label_data_batch.
        """
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy Status VI {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"SVI-SN-{uniq}",
            "asset_code": f"SVI-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        if status != "Active":
            # Ghi raw value (kể cả '' / mã drift) — bypass Select option validate.
            frappe.db.set_value("AC Asset", doc.name, "lifecycle_status", status,
                                update_modified=False)
            frappe.db.commit()
        return doc

    @staticmethod
    def _norm(text: str) -> str:
        """Chuẩn-hoá whitespace text trích pypdf → 1 dấu cách.

        pypdf chèn '\\t'/'\\n' GIỮA glyph khi label hẹp (60mm) wrap chữ ('Chưa rõ'
        → 'Chưa\\trõ'). Substring-match thô sẽ false-fail. Gom MỌI whitespace
        (space/tab/newline) thành 1 space để so khớp NHÃN HIỂN THỊ THẬT, KHÔNG so
        layout-wrap. KHÔNG ảnh hưởng no-leak (raw code không có whitespace nội bộ).
        """
        import re
        return re.sub(r"\s+", " ", text or "")

    @classmethod
    def _page_text(cls, pdf_bytes, idx=0) -> str:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(bytes(pdf_bytes)))
        return cls._norm(reader.pages[idx].extract_text() or "")

    @classmethod
    def _status_segment(cls, pdf_bytes, idx=0) -> str:
        """Chỉ đoạn SAU 'Trạng thái:' trên trang — để check '—' đúng dòng status.

        'Model: —' (model rỗng) hợp lệ có '—' ở trang → KHÔNG được tính là lỗi
        dòng status. Cô lập đoạn từ nhãn 'Trạng thái' đến hết trang."""
        text = cls._page_text(pdf_bytes, idx)
        marker = "Trạng thái:"
        i = text.find(marker)
        return text[i + len(marker):] if i >= 0 else ""

    @classmethod
    def _all_text(cls, pdf_bytes) -> str:
        import io
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(bytes(pdf_bytes)))
        return cls._norm("".join(p.extract_text() or "" for p in reader.pages))

    @staticmethod
    def _num_pages(pdf_bytes) -> int:
        import io
        from pypdf import PdfReader
        return len(PdfReader(io.BytesIO(bytes(pdf_bytes))).pages)

    # ── (1) lifecycle_status RỖNG ('') → 'Chưa rõ', KHÔNG '—' câm ────────────
    def test_empty_status_renders_chua_ro_not_em_dash(self):
        """Asset lifecycle_status='' (rỗng) → extract_text trang chứa 'Chưa rõ',
        KHÔNG có '—' ở dòng status; MediaBox 60×100; pages==1."""
        from assetcore.services.imm00 import render_asset_labels_pdf, _LABEL_PRESETS
        MM_TO_PT = 2.834645669
        a = self._make_asset("empty", status="")
        pdf = render_asset_labels_pdf([a.name], "tem-60x100")
        self.assertEqual(self._num_pages(pdf), 1, "1 asset = 1 trang PDF THẬT")
        text = self._page_text(pdf, 0)
        self.assertIn(self._UNKNOWN_VI, text,
                      "status rỗng → nhãn an toàn 'Chưa rõ' trên tem (presence-aware)")
        self.assertNotIn("—", self._status_segment(pdf, 0),
                         "status rỗng KHÔNG còn in '—' CÂM trên dòng status")
        # MediaBox đúng khổ preset (no-regress khổ tem 60×100).
        import io
        from pypdf import PdfReader
        box = PdfReader(io.BytesIO(bytes(pdf))).pages[0].mediabox
        spec = _LABEL_PRESETS["tem-60x100"]
        self.assertAlmostEqual(float(box.width), spec["width_mm"] * MM_TO_PT, delta=3)
        self.assertAlmostEqual(float(box.height), spec["height_mm"] * MM_TO_PT, delta=3)

    # ── (2) MÃ LẠ/DRIFT → 'Chưa rõ', TUYỆT ĐỐI KHÔNG leak raw code ───────────
    def test_drift_status_renders_chua_ro_no_raw_en_leak(self):
        """Asset lifecycle_status='RANDOM_DRIFT_XYZ' → extract_text chứa 'Chưa rõ'
        và TUYỆT ĐỐI KHÔNG chứa 'RANDOM_DRIFT_XYZ' (no-raw-EN-leak trên tem)."""
        from assetcore.services.imm00 import render_asset_labels_pdf
        drift = "RANDOM_DRIFT_XYZ"
        a = self._make_asset("drift", status=drift)
        pdf = render_asset_labels_pdf([a.name], "tem-60x100")
        text = self._page_text(pdf, 0)
        self.assertIn(self._UNKNOWN_VI, text,
                      "mã lạ → 'Chưa rõ' (an toàn, presence-aware)")
        self.assertNotIn(drift, text,
                         "mã drift TUYỆT ĐỐI KHÔNG leak raw EN ra extract_text tem")
        # bytes thô PDF cũng KHÔNG được chứa raw code (defense-in-depth).
        self.assertNotIn(drift.encode(), bytes(pdf),
                         "mã drift KHÔNG ở BYTES thô PDF (no-raw-EN-leak)")

    def test_drift_case_wrong_and_legacy_codes_all_chua_ro(self):
        """Mã sai-case ('active') + legacy ('Retired') ngoài 8 canonical → 'Chưa
        rõ', KHÔNG leak chính mã đó (parity empty vs unknown CÙNG nhãn)."""
        from assetcore.services.imm00 import render_asset_labels_pdf
        # suffix dùng INDEX (KHÔNG nhúng `bad` vào asset_code/name → tránh false
        # leak-fail khi `bad` là token thường như 'active').
        for i, bad in enumerate(("active", "Retired", "RANDOM_DRIFT")):
            a = self._make_asset(f"bad{i}", status=bad)
            pdf = render_asset_labels_pdf([a.name], "tem-60x100")
            text = self._page_text(pdf, 0)
            seg = self._status_segment(pdf, 0)
            self.assertIn(self._UNKNOWN_VI, text, f"'{bad}' → 'Chưa rõ'")
            self.assertNotIn(bad, seg, f"'{bad}' KHÔNG leak raw ra dòng status")
            self.assertNotIn("—", seg, f"'{bad}' KHÔNG in '—' câm dòng status")

    # ── (3) 8 mã canonical GIỮ nhãn VI cũ (no-regress) ──────────────────────
    def test_canonical_codes_keep_vi_label_no_regress(self):
        """Active→'Đang hoạt động'; Out of Service→'Ngừng sử dụng';
        Decommissioned→'Đã thanh lý'… (extract_text)."""
        from assetcore.services.imm00 import render_asset_labels_pdf
        # suffix INDEX (KHÔNG nhúng `code` vào asset_code → tránh false leak-fail).
        for i, (code, vi) in enumerate(self._CANONICAL_VI.items()):
            a = self._make_asset(f"canon{i}", status=code)
            pdf = render_asset_labels_pdf([a.name], "tem-60x100")
            text = self._page_text(pdf, 0)
            seg = self._status_segment(pdf, 0)
            self.assertIn(vi, text, f"'{code}' → nhãn VI '{vi}' (no-regress)")
            self.assertNotIn(self._UNKNOWN_VI, text,
                             f"'{code}' hợp lệ KHÔNG bị rớt thành 'Chưa rõ'")
            self.assertNotIn(code, seg, f"'{code}' raw KHÔNG leak EN ra dòng status")

    # ── (4) batch N=3 mixed (hợp lệ + rỗng + drift) → N→N + nhãn đúng từng trang ─
    def test_batch_mixed_status_pages_and_per_page_labels(self):
        """Batch N=3 (Active + '' + drift): PdfReader.pages==3 (giữ N→N), mỗi trang
        status đúng nhãn tương ứng, KHÔNG trang nào in '—' ở dòng status."""
        from assetcore.services.imm00 import render_asset_labels_pdf
        a_ok = self._make_asset("mix-ok", status="Active")
        a_empty = self._make_asset("mix-empty", status="")
        a_drift = self._make_asset("mix-drift", status="WEIRD_DRIFT_999")
        names = [a_ok.name, a_empty.name, a_drift.name]
        pdf = render_asset_labels_pdf(names, "tem-60x100")
        self.assertEqual(self._num_pages(pdf), 3,
                         "3 asset = 3 trang PDF THẬT (invariant N→N giữ)")
        t0 = self._page_text(pdf, 0)
        t1 = self._page_text(pdf, 1)
        t2 = self._page_text(pdf, 2)
        self.assertIn("Đang hoạt động", t0, "trang 0 (Active) → nhãn VI canonical")
        self.assertIn(self._UNKNOWN_VI, t1, "trang 1 (rỗng) → 'Chưa rõ'")
        self.assertIn(self._UNKNOWN_VI, t2, "trang 2 (drift) → 'Chưa rõ'")
        self.assertNotIn("WEIRD_DRIFT_999", t2, "drift KHÔNG leak raw ra tem")
        # '—' check CÔ LẬP đoạn dòng status mỗi trang (Model rỗng có '—' hợp lệ).
        for i in range(3):
            self.assertNotIn("—", self._status_segment(pdf, i),
                             f"trang {i} KHÔNG in '—' câm dòng status")

    # ── (5) parity preset BẤT KỲ có 'status' trong fields (KHÔNG chỉ 60×100) ──
    def test_empty_status_chua_ro_on_every_preset_with_status_field(self):
        """Mọi preset có field 'status' (60×100 + bất kỳ preset nào fields chứa
        'status') → asset rỗng render 'Chưa rõ', KHÔNG '—'; pages==1; khổ đúng."""
        from assetcore.services.imm00 import render_asset_labels_pdf, _LABEL_PRESETS
        MM_TO_PT = 2.834645669
        a = self._make_asset("preset-empty", status="")
        presets_with_status = [
            k for k, v in _LABEL_PRESETS.items() if "status" in v.get("fields", [])
        ]
        self.assertIn("tem-60x100", presets_with_status,
                      "tiền đề: 60×100 có field 'status'")
        for preset in presets_with_status:
            pdf = render_asset_labels_pdf([a.name], preset)
            self.assertEqual(self._num_pages(pdf), 1,
                             f"[{preset}] 1 asset = 1 trang THẬT")
            text = self._page_text(pdf, 0)
            self.assertIn(self._UNKNOWN_VI, text,
                          f"[{preset}] status rỗng → 'Chưa rõ'")
            self.assertNotIn("—", self._status_segment(pdf, 0),
                             f"[{preset}] KHÔNG '—' câm dòng status")
            import io
            from pypdf import PdfReader
            box = PdfReader(io.BytesIO(bytes(pdf))).pages[0].mediabox
            spec = _LABEL_PRESETS[preset]
            self.assertAlmostEqual(float(box.width), spec["width_mm"] * MM_TO_PT,
                                   delta=3, msg=f"[{preset}] MediaBox width đúng khổ")
            self.assertAlmostEqual(float(box.height), spec["height_mm"] * MM_TO_PT,
                                   delta=3, msg=f"[{preset}] MediaBox height đúng khổ")

    # ── (6) UNIT — _lifecycle_vi SSoT (no-EN-leak, presence-aware) ──────────
    def test_unit_lifecycle_vi_ssot(self):
        """_lifecycle_vi('')=='Chưa rõ', _lifecycle_vi('NopeCode')=='Chưa rõ',
        _lifecycle_vi('Active')=='Đang hoạt động' (SSoT, no-EN-leak)."""
        from assetcore.services.imm00 import _lifecycle_vi
        self.assertEqual(_lifecycle_vi(""), self._UNKNOWN_VI,
                         "rỗng → 'Chưa rõ' (KHÔNG '')")
        self.assertEqual(_lifecycle_vi("NopeCode"), self._UNKNOWN_VI,
                         "mã lạ → 'Chưa rõ' (KHÔNG raw code)")
        self.assertEqual(_lifecycle_vi(None), self._UNKNOWN_VI,
                         "None → 'Chưa rõ' (guard rỗng)")
        self.assertEqual(_lifecycle_vi("Active"), "Đang hoạt động",
                         "Active → nhãn VI canonical (no-regress)")
        self.assertEqual(_lifecycle_vi("Out of Service"), "Ngừng sử dụng")
        self.assertEqual(_lifecycle_vi("Decommissioned"), "Đã thanh lý")
        # no-EN-leak: KHÔNG mã lạ nào trả về chính nó.
        for bad in ("Retired", "RANDOM_DRIFT", "active", "PENDING_X"):
            self.assertEqual(_lifecycle_vi(bad), self._UNKNOWN_VI,
                             f"'{bad}' → 'Chưa rõ' (no-EN-leak SSoT)")
            self.assertNotEqual(_lifecycle_vi(bad), bad)


class TestLabelPresetResolverV3(unittest.TestCase):
    """V3 POLISH (ADR-LABEL-PDF §D14): resolver site_config `assetcore_label_preset`.

    Hợp-lệ-hoá 1 chỗ (mirror `_qr_base_url`): conf hợp-lệ → preset đó; conf
    vắng/rỗng/sai-kiểu/không-whitelist → fallback `DEFAULT_LABEL_PRESET` + warn
    log ĐÚNG 1 lần, KHÔNG raise. explicit client preset > site_config > code-default;
    preset client lạ → 422 GIỮ NGUYÊN (resolver KHÔNG nới whitelist).
    """

    _CATEGORY_NAME = "Thiết bị Preset Resolver (LABEL-PDF V3)"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test resolver preset V3",
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
        # cô lập state config + cờ warn module-level giữa các test (KHÔNG để rò).
        from assetcore.services import imm00 as _svc
        self._conf_had = _svc._LABEL_PRESET_CONF_KEY in frappe.conf
        self._conf_prev = frappe.conf.get(_svc._LABEL_PRESET_CONF_KEY)
        _svc._label_preset_warned = False

    def tearDown(self):
        frappe.set_user("Administrator")
        from assetcore.services import imm00 as _svc
        # khôi phục conf về trạng thái trước test (KHÔNG rò sang test khác).
        if self._conf_had:
            frappe.conf[_svc._LABEL_PRESET_CONF_KEY] = self._conf_prev
        else:
            frappe.conf.pop(_svc._LABEL_PRESET_CONF_KEY, None)
        _svc._label_preset_warned = False
        frappe.db.rollback()
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _set_conf(self, value):
        from assetcore.services import imm00 as _svc
        frappe.conf[_svc._LABEL_PRESET_CONF_KEY] = value

    def _clear_conf(self):
        from assetcore.services import imm00 as _svc
        frappe.conf.pop(_svc._LABEL_PRESET_CONF_KEY, None)

    def _make_asset(self, suffix="", **overrides):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy Preset {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"PRESET-SN-{uniq}",
            "asset_code": f"PRESET-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(overrides)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    # ── [BE TDD] resolver hợp lệ: conf ∈ whitelist → trả conf ────────────────
    def test_resolve_preset_valid_conf(self):
        from assetcore.services.imm00 import _resolve_label_preset
        self._set_conf("tem-60x100")
        self.assertEqual(_resolve_label_preset(), "tem-60x100",
                         "conf hợp lệ ∈ _LABEL_PRESETS → trả đúng conf")

    def test_resolve_preset_valid_conf_endpoint_no_preset_pdf(self):
        """conf hợp lệ + endpoint KHÔNG truyền preset → PDF (response.type=pdf)."""
        from assetcore.api.imm00 import print_asset_labels_pdf
        self._set_conf("tem-60x100")
        asset = self._make_asset("rconf1")
        frappe.local.response = frappe._dict()
        print_asset_labels_pdf(assets=[asset.name])
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "conf hợp lệ + no-preset → PDF khổ conf")
        self.assertTrue(bytes(frappe.local.response.get("filecontent"))
                        .startswith(b"%PDF-"))

    # ── [BE TDD] resolver fallback: vắng / '' / 123 / không-whitelist ────────
    def test_resolve_preset_missing_or_invalid_falls_back(self):
        from assetcore.services.imm00 import (
            _resolve_label_preset, DEFAULT_LABEL_PRESET)
        from assetcore.services import imm00 as _svc
        # (a) conf VẮNG → DEFAULT, KHÔNG warn (vắng là hợp lệ).
        self._clear_conf()
        _svc._label_preset_warned = False
        self.assertEqual(_resolve_label_preset(), DEFAULT_LABEL_PRESET)
        self.assertFalse(_svc._label_preset_warned,
                         "conf vắng → KHÔNG warn (vắng là hợp lệ)")
        # (b) conf '' rỗng → DEFAULT (rỗng coi như vắng — falsy, KHÔNG warn).
        self._set_conf("")
        _svc._label_preset_warned = False
        self.assertEqual(_resolve_label_preset(), DEFAULT_LABEL_PRESET)
        # (c) conf 123 (sai kiểu) → DEFAULT, KHÔNG raise.
        self._set_conf(123)
        _svc._label_preset_warned = False
        self.assertEqual(_resolve_label_preset(), DEFAULT_LABEL_PRESET,
                         "conf sai kiểu → DEFAULT (KHÔNG raise)")
        # (d) conf 'khong-whitelist' → DEFAULT + warn.
        self._set_conf("khong-whitelist")
        _svc._label_preset_warned = False
        self.assertEqual(_resolve_label_preset(), DEFAULT_LABEL_PRESET,
                         "conf không-whitelist → fallback DEFAULT")

    def test_resolve_preset_warns_exactly_once(self):
        """conf sai-whitelist → warn ĐÚNG 1 lần (gọi 2× → log 1×)."""
        from assetcore.services.imm00 import _resolve_label_preset
        from assetcore.services import imm00 as _svc
        from unittest.mock import patch
        self._set_conf("rac-config-sai")
        _svc._label_preset_warned = False
        with patch.object(frappe, "logger") as mock_logger:
            warn = mock_logger.return_value.warning
            _resolve_label_preset()
            _resolve_label_preset()
            self.assertEqual(warn.call_count, 1,
                             "config sai → warning ĐÚNG 1 lần (cờ module-level)")
        self.assertTrue(_svc._label_preset_warned, "cờ warn set True sau lần đầu")

    def test_resolve_preset_invalid_conf_renders_pdf_no_raise(self):
        """conf=123 / 'rác' + endpoint no-preset → render PDF OK, KHÔNG 500."""
        from assetcore.api.imm00 import print_asset_labels_pdf
        asset = self._make_asset("rbad1")
        for bad in (123, "rac-khong-whitelist"):
            self._set_conf(bad)
            from assetcore.services import imm00 as _svc
            _svc._label_preset_warned = False
            frappe.local.response = frappe._dict()
            ret = print_asset_labels_pdf(assets=[asset.name])
            self.assertFalse(isinstance(ret, dict) and ret.get("success") is False,
                             f"conf={bad!r} → KHÔNG Error envelope (fallback 60×100)")
            self.assertEqual(frappe.local.response.get("type"), "pdf",
                             f"conf={bad!r} → PDF vẫn ra (fallback, KHÔNG 500)")
            self.assertTrue(bytes(frappe.local.response.get("filecontent"))
                            .startswith(b"%PDF-"))

    # ── [BE TDD] explicit client preset THẮNG config + lạ → 422 GIỮ NGUYÊN ───
    def test_endpoint_explicit_preset_wins_over_conf(self):
        from assetcore.api.imm00 import print_asset_labels_pdf
        from assetcore.services.imm00 import _resolve_label_preset
        # conf set 1 preset hợp lệ; client truyền tường minh preset hợp lệ →
        # client THẮNG (resolver chỉ áp khi caller bỏ trống). Hiện whitelist chỉ
        # có 1 preset PDF → dùng cùng giá trị nhưng chứng minh nhánh explicit
        # KHÔNG đi qua resolver (resolver trả conf, explicit bỏ qua resolver).
        self._set_conf("tem-60x100")
        self.assertEqual(_resolve_label_preset(), "tem-60x100")
        asset = self._make_asset("exp1")
        frappe.local.response = frappe._dict()
        print_asset_labels_pdf(assets=[asset.name], preset="tem-60x100")
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "client truyền preset hợp lệ → PDF (explicit thắng)")
        # client truyền preset LẠ → 422 GIỮ NGUYÊN (resolver KHÔNG nới whitelist)
        frappe.local.response = frappe._dict()
        resp = print_asset_labels_pdf(assets=[asset.name], preset="xyz-lung-tung")
        self.assertIsInstance(resp, dict, "preset lạ tường minh → Error envelope")
        self.assertFalse(resp.get("success"))
        self.assertEqual(resp.get("http_status"), 422,
                         "preset client lạ → 422 GIỮ NGUYÊN (KHÔNG nới whitelist)")
        self.assertNotEqual(frappe.local.response.get("type"), "pdf")

    # ── [BE TDD] no-preset dùng conf default; conf vắng → 60×100 fallback ────
    def test_endpoint_no_preset_uses_conf_default(self):
        from assetcore.api.imm00 import print_asset_labels_pdf
        asset = self._make_asset("nopre1")
        # (a) conf set → PDF đúng preset conf.
        self._set_conf("tem-60x100")
        frappe.local.response = frappe._dict()
        print_asset_labels_pdf(assets=[asset.name])
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "no-preset + conf set → PDF preset conf")
        # (b) conf VẮNG → PDF fallback 60×100 (DEFAULT_LABEL_PRESET).
        self._clear_conf()
        frappe.local.response = frappe._dict()
        print_asset_labels_pdf(assets=[asset.name])
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "no-preset + conf vắng → PDF fallback 60×100mm")
        self.assertTrue(bytes(frappe.local.response.get("filecontent"))
                        .startswith(b"%PDF-"))


class TestLabelStatusViV3(unittest.TestCase):
    """V3 POLISH (ADR-LABEL-PDF §D3/§D13): field thứ 5 lifecycle_status dịch VI.

    Nhãn 'Trạng thái:' + giá trị VI; mã EN canonical KHÔNG lọt tem (grep=0);
    Block lỗi (asset∄) KHÔNG có status.

    VÒNG 41 (label-pdf em-dash câm fix): mã lạ/rỗng KHÔNG còn '—' câm mà → nhãn
    SSoT VI 'Chưa rõ' (presence-aware, no-EN-leak). Assertion cũ (_lifecycle_vi
    rỗng/lạ == '') ĐÃ THAY bằng == 'Chưa rõ' bên dưới. Bộ assert pypdf đầy đủ ở
    TestLabelStatusViUnknownVi41.
    """

    _CATEGORY_NAME = "Thiết bị Status VI (LABEL-PDF V3)"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test status VI V3",
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

    def _make_asset(self, suffix="", **overrides):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy Status {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"STAT-SN-{uniq}",
            "asset_code": f"STAT-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(overrides)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    # ── [BE TDD] HTML render status VI + nhãn 'Trạng thái' + no EN-leak ──────
    def test_label_html_renders_lifecycle_status_vi(self):
        from assetcore.services.imm00 import (
            _label_html, build_asset_label_data_batch)
        # (a) Under Maintenance → 'Đang bảo trì'; EN canonical KHÔNG lọt tem.
        a = self._make_asset("um1", lifecycle_status="Under Maintenance")
        html = _label_html(build_asset_label_data_batch([a.name]), "tem-60x100")
        self.assertIn("Trạng thái", html, "nhãn-VI cố định 'Trạng thái' có mặt")
        self.assertIn("Đang bảo trì", html, "giá trị VI dịch đúng")
        self.assertNotIn("Under Maintenance", html,
                         "mã EN canonical thô KHÔNG lọt tem (no EN-leak)")
        # (b) Active → 'Đang hoạt động'; 'Active' EN KHÔNG lọt tem.
        b = self._make_asset("act1", lifecycle_status="Active")
        html2 = _label_html(build_asset_label_data_batch([b.name]), "tem-60x100")
        self.assertIn("Đang hoạt động", html2, "Active → 'Đang hoạt động'")
        # 'Active' chỉ kiểm trong ngữ cảnh status — đảm bảo mã EN status không lọt.
        # (HTML có thể chứa 'active' trong CSS? KHÔNG — CSS chỉ class .status. Assert thô.)
        self.assertNotIn("Active", html2,
                         "mã EN 'Active' thô KHÔNG lọt tem (no EN-leak)")

    # ── [BE TDD] status mã lạ/rỗng → 'Chưa rõ' (Vòng 41 — no em-dash câm) ─────
    def test_label_status_unknown_no_crash(self):
        from assetcore.services.imm00 import (
            _label_html, build_asset_label_data_batch,
            render_asset_labels_pdf, _lifecycle_vi)
        # (a) status rỗng → _lifecycle_vi('') == 'Chưa rõ' → render 'Chưa rõ',
        # KHÔNG 'None', KHÔNG '—' câm. lifecycle_status mandatory → insert hợp lệ
        # rồi set rỗng qua DB (mô phỏng data cũ/migration thiếu status).
        a = self._make_asset("empty1")
        frappe.db.set_value("AC Asset", a.name, "lifecycle_status", "",
                            update_modified=False)
        items = build_asset_label_data_batch([a.name])
        html = _label_html(items, "tem-60x100")
        self.assertIn("Trạng thái", html, "dòng status vẫn render khi rỗng")
        self.assertIn("Chưa rõ", html, "status rỗng → nhãn VI 'Chưa rõ' (no em-dash câm)")
        self.assertNotIn("None", html, "KHÔNG render chuỗi 'None'")
        self.assertEqual(_lifecycle_vi(""), "Chưa rõ",
                         "_lifecycle_vi('') == 'Chưa rõ' (Vòng 41 SSoT)")
        self.assertEqual(_lifecycle_vi("FooBarLa"), "Chưa rõ",
                         "mã lạ → 'Chưa rõ' (KHÔNG leak, KHÔNG None, KHÔNG '—')")
        # PDF magic %PDF còn đúng (KHÔNG crash khi status rỗng).
        pdf = render_asset_labels_pdf([a.name], "tem-60x100")
        self.assertTrue(bytes(pdf).startswith(b"%PDF-"),
                        "status rỗng → PDF magic %PDF còn đúng (KHÔNG raise)")

    def test_error_block_has_no_status_line(self):
        """Block lỗi (asset∄) KHÔNG thêm dòng status (chỉ echo name + not-found)."""
        from assetcore.services.imm00 import (
            _label_html, build_asset_label_data_batch)
        a = self._make_asset("mixstat")
        items = build_asset_label_data_batch([a.name, "KHONG-TON-TAI-STAT"])
        html = _label_html(items, "tem-60x100")
        # đúng 1 dòng status (cho asset hợp lệ), KHÔNG cho block lỗi.
        self.assertEqual(html.count('class="line status"'), 1,
                         "chỉ block hợp lệ có dòng status (block lỗi KHÔNG)")


# ── VÒNG 41 — TEM IN PDF: dòng 'Trạng thái' status rỗng/lạ → 'Chưa rõ' (no em-dash
#    câm), no-EN-leak — verify ở TẦNG PDF THẬT (pypdf extract_text), KHÔNG đếm HTML.
#    Parity FE AssetQrLabel.vue (translateStatus-safe → 'Chưa rõ'). Đo extract_text
#    (analog quét tem khách in) — chống false-green của assert HTML-source thuần.
class TestLabelStatusViUnknownVi41(unittest.TestCase):
    """VÒNG 41: bịt em-dash-câm + presence-aware nhãn VI cho dòng 'Trạng thái' trên
    TEM IN PDF. status rỗng/lạ/drift → 'Chưa rõ' (SSoT VI, KHÔNG '—', KHÔNG leak mã
    EN thô). 8 mã canonical GIỮ nhãn cũ (no-regress). Bất biến PDF (N→N trang +
    MediaBox khổ mm) GIỮ. Đo bằng PdfReader.extract_text() (KHÔNG HTML block).
    """

    _CATEGORY_NAME = "Thiết bị Status Vi41 (LABEL-PDF V41)"
    _MM_TO_PT = 2.834645669

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test status VI Vòng 41",
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

    def _make_asset(self, suffix="", **overrides):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        data = {
            "doctype": "AC Asset",
            "asset_name": f"Máy V41 {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"V41-SN-{uniq}",
            "asset_code": f"V41-ASSET-{uniq}",
            "lifecycle_status": "Active",
        }
        data.update(overrides)
        doc = _insert_asset_bypass_workflow(data)
        self._created.append(doc.name)
        return doc

    def _set_status_raw(self, name: str, status: str) -> None:
        # lifecycle_status mandatory → insert hợp lệ rồi set rỗng/drift qua DB
        # (mô phỏng data cũ/migration/drift ngoài 8 mã canonical).
        frappe.db.set_value("AC Asset", name, "lifecycle_status", status,
                            update_modified=False)

    def _pdf_text_pages(self, names):
        """Trả (reader, [text_chuẩn-hoá per-page]). pypdf extract_text chèn \\t/\\n
        GIỮA glyph → bỏ whitespace để so chuỗi VI liền mạch ('Chưa rõ') KHÔNG
        false-fail vì tách-từ. Đây là TẦNG PDF THẬT (analog quét tem in)."""
        import io
        from pypdf import PdfReader
        from assetcore.services.imm00 import render_asset_labels_pdf
        pdf = render_asset_labels_pdf(names, "tem-60x100")
        reader = PdfReader(io.BytesIO(bytes(pdf)))
        norm = ["".join(p.extract_text().split()) for p in reader.pages]
        return reader, norm

    @staticmethod
    def _status_segment(page_text: str) -> str:
        """Trích GIÁ TRỊ dòng 'Trạng thái' từ text trang (đã chuẩn-hoá). Layout
        tem-60x100 (fields=[code,name,model,sn,status]) → 'status' là field CUỐI →
        giá trị = phần sau marker 'Trạngthái:'. Cho phép SCOPE assert '—' câm CHỈ ở
        dòng status — GIỮ '—' cho field khác (code/name/model/sn) out-of-scope V41
        (vd model rỗng vẫn '—' hợp lệ). Marker = nhãn VI cố định (no em-dash)."""
        marker = "Trạngthái:"
        idx = page_text.find(marker)
        return page_text[idx + len(marker):] if idx >= 0 else ""

    # ── unit SSoT — _lifecycle_vi (no-EN-leak, presence-aware) ──────────────
    def test_unit_lifecycle_vi_ssot(self):
        from assetcore.services.imm00 import _lifecycle_vi, _LIFECYCLE_VI_UNKNOWN
        self.assertEqual(_LIFECYCLE_VI_UNKNOWN, "Chưa rõ",
                         "hằng SSoT VI cho mã rỗng/lạ == 'Chưa rõ'")
        self.assertEqual(_lifecycle_vi(""), "Chưa rõ", "rỗng → 'Chưa rõ'")
        self.assertEqual(_lifecycle_vi("NopeCode"), "Chưa rõ", "mã lạ → 'Chưa rõ'")
        self.assertEqual(_lifecycle_vi("Active"), "Đang hoạt động",
                         "mã canonical GIỮ nhãn cũ (no-regress)")
        # no-EN-leak: mã lạ KHÔNG bao giờ trả raw code.
        self.assertNotIn("NopeCode", _lifecycle_vi("NopeCode"))
        # presence-aware: KHÔNG bao giờ trả chuỗi rỗng (luôn truthy → no '—' câm).
        for s in ("", "NopeCode", "RANDOM_DRIFT", "active"):
            self.assertTrue(_lifecycle_vi(s), f"_lifecycle_vi({s!r}) phải truthy")

    # ── PDF THẬT — status rỗng ('') → extract_text chứa 'Chưa rõ', KHÔNG '—' ──
    def test_pdf_empty_status_shows_chua_ro_no_emdash(self):
        a = self._make_asset("empty")
        self._set_status_raw(a.name, "")
        reader, pages = self._pdf_text_pages([a.name])
        self.assertEqual(len(reader.pages), 1, "1 asset = 1 trang PDF THẬT")
        seg = self._status_segment(pages[0])
        self.assertTrue(seg.startswith("Chưarõ"),
                        "status rỗng → dòng 'Trạng thái' = 'Chưa rõ' (extract_text)")
        # KHÔNG '—' câm Ở DÒNG STATUS (scope status-segment — GIỮ '—' cho field khác
        # như model rỗng, out-of-scope V41). Em-dash U+2014 KHÔNG ở giá trị status.
        self.assertNotIn("—", seg,
                         "KHÔNG còn '—' câm Ở DÒNG STATUS khi status rỗng")
        # MediaBox đúng khổ 60×100mm (no-regress khổ tem).
        box = reader.pages[0].mediabox
        self.assertAlmostEqual(float(box.width), 60 * self._MM_TO_PT, delta=3)
        self.assertAlmostEqual(float(box.height), 100 * self._MM_TO_PT, delta=3)

    # ── PDF THẬT — mã DRIFT/lạ → 'Chưa rõ' + TUYỆT ĐỐI KHÔNG leak raw code ────
    def test_pdf_drift_status_no_raw_en_leak(self):
        a = self._make_asset("drift")
        self._set_status_raw(a.name, "RANDOM_DRIFT_XYZ")
        reader, pages = self._pdf_text_pages([a.name])
        self.assertEqual(len(reader.pages), 1)
        self.assertIn("Chưarõ", pages[0], "mã lạ → 'Chưa rõ' trên tem in")
        # No-raw-EN-leak ở TẦNG PDF THẬT: chuỗi drift KHÔNG xuất hiện ở extract_text.
        joined = "".join(pages)
        self.assertNotIn("RANDOM_DRIFT_XYZ", joined,
                         "mã lạ KHÔNG leak raw code ra tem (extract_text)")
        self.assertNotIn("RANDOM", joined, "không leak phần mã drift")
        self.assertNotIn("—", self._status_segment(pages[0]),
                         "KHÔNG '—' câm Ở DÒNG STATUS cho mã lạ")

    # ── PDF THẬT — 8 mã canonical GIỮ nhãn VI cũ (no-regress) ────────────────
    def test_pdf_canonical_status_no_regress(self):
        cases = {
            "Active": "Đanghoạtđộng",
            "Out of Service": "Ngừngsửdụng",
            "Decommissioned": "Đãthanhlý",
        }
        for raw, vi in cases.items():
            # suffix sạch (asset_code chỉ chấp chữ/số/._-/) — bỏ space của mã có
            # khoảng trắng ('Out of Service') → KHÔNG vi phạm regex asset_code.
            safe = "".join(c for c in raw if c.isalnum())[:8]
            a = self._make_asset(f"canon-{safe}")
            self._set_status_raw(a.name, raw)
            reader, pages = self._pdf_text_pages([a.name])
            seg = self._status_segment(pages[0])
            self.assertTrue(seg.startswith(vi),
                            f"{raw} → dòng 'Trạng thái' = '{vi}' (no-regress)")
            # mã EN canonical KHÔNG leak Ở DÒNG STATUS (scope status-segment —
            # asset_code/suffix có thể chứa mã, out-of-scope; chỉ status line tính).
            self.assertNotIn(raw.replace(" ", ""), seg,
                             f"mã EN '{raw}' KHÔNG leak ra DÒNG STATUS")
            self.assertNotIn("Chưarõ", seg,
                             f"{raw} là mã hợp lệ → DÒNG STATUS KHÔNG 'Chưa rõ'")

    # ── PDF THẬT — batch N=3 mixed (hợp lệ + rỗng + drift): N→N trang giữ ─────
    def test_pdf_batch_mixed_status_invariant_n_pages(self):
        ok = self._make_asset("mix-ok", lifecycle_status="Active")
        empty = self._make_asset("mix-empty")
        self._set_status_raw(empty.name, "")
        drift = self._make_asset("mix-drift")
        self._set_status_raw(drift.name, "WeirdDrift")
        reader, pages = self._pdf_text_pages([ok.name, empty.name, drift.name])
        # invariant N→N: PdfReader.pages == 3 (KHÔNG đếm HTML block).
        self.assertEqual(len(reader.pages), 3,
                         "3 asset mixed → 3 trang PDF THẬT (invariant N→N giữ)")
        joined = "".join(pages)
        # mỗi nhãn render đúng: 1 'Đang hoạt động' (ok) + 2 'Chưa rõ' (empty+drift).
        self.assertIn("Đanghoạtđộng", joined, "asset hợp lệ → nhãn VI canonical")
        self.assertEqual(joined.count("Chưarõ"), 2,
                         "đúng 2 nhãn 'Chưa rõ' (rỗng + drift), KHÔNG nhiều/ít hơn")
        # KHÔNG trang nào in '—' Ở DÒNG STATUS (scope status-segment — '—' field
        # khác như model rỗng là out-of-scope V41).
        for i, txt in enumerate(pages):
            self.assertNotIn("—", self._status_segment(txt),
                             f"trang {i} KHÔNG '—' câm Ở DÒNG STATUS")
        self.assertNotIn("WeirdDrift", joined, "drift KHÔNG leak raw code")


class TestImm00Imm04QrNoConflictV3(unittest.TestCase):
    """V3 POLISH (ADR-LABEL-PDF §D15): IMM-00 label PDF ↔ IMM-04 commissioning.

    CÙNG token `/a/<token>` qua `ensure_asset_qr_token`+`_build_qr_url`; in PDF
    IMM-00 KHÔNG rotate token IMM-04 dùng (no side-effect chéo).
    """

    _CATEGORY_NAME = "Thiết bị No-Conflict QR (LABEL-PDF V3)"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test no-conflict QR V3",
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
            "asset_name": f"Máy NoConflict {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"NC-SN-{uniq}",
            "asset_code": f"NC-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def test_imm00_qr_url_is_deep_link_a_token(self):
        """IMM-00 build_asset_label_data → qr_url = /a/<token> (CÙNG SSoT)."""
        from assetcore.services.imm00 import (
            build_asset_label_data, ensure_asset_qr_token, _build_qr_url)
        asset = self._make_asset("dl1")
        token = ensure_asset_qr_token(asset.name)
        expected = _build_qr_url(token)
        data = build_asset_label_data(asset.name)
        self.assertEqual(data["qr_url"], expected,
                         "IMM-00 qr_url == _build_qr_url(ensure_asset_qr_token) — CÙNG SSoT")
        self.assertIn("/a/", data["qr_url"], "deep-link /a/<token>")
        self.assertIn(token, data["qr_url"], "token là path-segment qr_url")

    def test_print_pdf_does_not_rotate_token(self):
        """in PDF IMM-00 KHÔNG rotate qr_token (token trước == sau — no side-effect)."""
        from assetcore.api.imm00 import print_asset_labels_pdf
        from assetcore.services.imm00 import ensure_asset_qr_token
        asset = self._make_asset("norot1")
        token_before = ensure_asset_qr_token(asset.name)
        frappe.db.commit()
        frappe.local.response = frappe._dict()
        print_asset_labels_pdf(assets=[asset.name])
        self.assertEqual(frappe.local.response.get("type"), "pdf")
        token_after = frappe.db.get_value("AC Asset", asset.name, "qr_token")
        self.assertEqual(token_before, token_after,
                         "in PDF KHÔNG rotate token (no side-effect chéo IMM-04)")

    def test_imm00_imm04_same_helper_same_token(self):
        """IMM-00 build_asset_label_data['qr_url'] dùng CÙNG helper như IMM-04.

        IMM-04 generate_qr_label lazy-import ensure_asset_qr_token+_build_qr_url
        từ IMM-00 (services/imm04.py:1010-1012). Chứng minh CÙNG token: gọi cả 2
        helper trên cùng asset → CÙNG /a/<token> (ensure idempotent — không rotate).
        """
        from assetcore.services.imm00 import (
            build_asset_label_data, ensure_asset_qr_token, _build_qr_url)
        asset = self._make_asset("conv1")
        # đường IMM-00 (asset label)
        imm00_url = build_asset_label_data(asset.name)["qr_url"]
        # đường IMM-04 reuse (CÙNG helper, mô phỏng generate_qr_label sau release)
        imm04_token = ensure_asset_qr_token(asset.name)
        imm04_url = _build_qr_url(imm04_token)
        self.assertEqual(imm00_url, imm04_url,
                         "IMM-00 ↔ IMM-04 CÙNG /a/<token> (ensure idempotent, no rotate)")


# ──────────────────────────────────────────────────────────────────────────
# Vòng 5 — LIST-SCOPE: page_size upper-cap (ADR-IMM00-LIST-SCOPE)
# ──────────────────────────────────────────────────────────────────────────
# BUG (factory round 5): 11 list-endpoint imm00 parse `page_size = int(page_size)`
# rồi truyền THẲNG `limit_page_length=page_size` vào frappe.get_list KHÔNG cap.
# `paginate()` CHỈ clamp metadata [1,100] (utils/pagination.py:8) → metadata
# divergent với limit query thật → invariant `len(items) <= pagination.page_size`
# VỠ + truy vấn vô giới hạn (DoS/perf). Sibling imm01/02/03/04 đã cap.
#
# FIX (SSoT, BA chốt ADR-IMM00-LIST-SCOPE): tái dùng clamp đã-có của paginate() —
# DÙNG `pag["page_size"]` (đã min(max(x,1),100)) làm limit_page_length. KHÔNG rải
# literal 100 ở 11 handler. RED viết TRƯỚC fix.
#
# TC-PAGESZ-01..07. Frappe-first, logic-level (bench run-tests fresh-import) —
# KHÔNG cần USER reload gunicorn (STALE-WORKER gate AC5).
# ──────────────────────────────────────────────────────────────────────────
class TestListScopePageSizeCap(unittest.TestCase):
    """Vòng 5 — page_size cap 100 cho MỌI list-endpoint imm00 (parity imm01/02/03)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Page-Size-Cap (V5)",
            "description": "Category cho test list-scope page_size cap",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        cls.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": "PSC Phòng Kiểm thử — Tầng 5",
            "location_type": "Room",
        }).insert(ignore_permissions=True)
        # 1 asset thật → đủ cho list_assets + các endpoint cần `asset`/`name`
        # (get_asset_timeline, list_lifecycle_events) có arg hợp lệ.
        import uuid
        uniq = uuid.uuid4().hex[:8]
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy PageSizeCap {uniq}",
            "asset_category": cls.cat.name,
            "location": cls.loc.name,
            "manufacturer_sn": f"PSC-SN-{uniq}",
            "asset_code": f"PSC-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        _purge_asset(cls.asset.name)
        frappe.delete_doc("AC Location", cls.loc.name,
                          force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _spy_get_list_limits(self, fn, **kwargs):
        """Gọi `fn(**kwargs)` trong khi SPY mọi `limit_page_length` thực sự truyền
        vào frappe.get_list. Trả (resp, [limit_page_length...]).

        Deterministic-RED: chứng minh limit query đã-cap KHÔNG phụ thuộc DB có
        >100 row hay không (test DB fresh-import có thể ít row → len(items)<=100
        đúng-trivially; spy bắt ĐÚNG giá trị limit_page_length truyền xuống SQL)."""
        import frappe as _frappe
        captured: list = []
        orig = _frappe.get_list

        def _spy(*a, **kw):
            if "limit_page_length" in kw:
                captured.append(kw["limit_page_length"])
            return orig(*a, **kw)

        _frappe.get_list = _spy
        try:
            resp = fn(**kwargs)
        finally:
            _frappe.get_list = orig
        return resp, captured

    # 11 list-endpoint imm00 (đề mục AC2) → (callable, kwargs cố-định-arg-bắt-buộc).
    # Endpoint cần `asset`/`name` được cấp asset thật; còn lại arg-optional.
    def _endpoints(self):
        from assetcore.api import imm00 as api
        return [
            ("list_assets",            api.list_assets,            {}),
            ("get_asset_timeline",     api.get_asset_timeline,     {"name": self.asset.name}),
            ("list_lifecycle_events",  api.list_lifecycle_events,  {"asset": self.asset.name}),
            ("list_suppliers",         api.list_suppliers,         {}),
            ("list_device_models",     api.list_device_models,     {}),
            ("list_audit_trail",       api.list_audit_trail,       {}),
            ("list_capas",             api.list_capas,             {}),
            ("list_overdue_capas",     api.list_overdue_capas,     {}),
            ("list_incidents",         api.list_incidents,         {}),
            ("list_transfers",         api.list_transfers,         {}),
            ("list_service_contracts", api.list_service_contracts, {}),
        ]

    # ── TC-PAGESZ-01 (RED trước fix) — list_assets page_size khổng lồ ───────
    def test_pagesz_01_list_assets_huge_page_size_capped(self):
        """`list_assets(page_size=100000)` → len(items) <= 100 VÀ
        pagination.page_size == 100 (metadata == limit thực, hết divergence).

        RED trước fix: limit_page_length=page_size thô → items vượt 100 (nếu DB
        đủ row) + pagination.page_size==100 ⇒ len(items) > pagination.page_size.
        """
        from assetcore.api.imm00 import list_assets
        resp, limits = self._spy_get_list_limits(list_assets, page=1, page_size=100000)
        self.assertTrue(resp["success"])
        data = resp["data"]
        self.assertEqual(data["pagination"]["page_size"], 100,
                         "page_size metadata phải clamp về 100")
        # DETERMINISTIC-RED: limit_page_length thực truyền vào SQL <= 100
        # (trước fix = 100000 thô → FAIL bất kể DB ít/nhiều row).
        self.assertTrue(limits, "list_assets phải gọi frappe.get_list (spy bắt được)")
        for lim in limits:
            self.assertLessEqual(lim, 100,
                                 f"limit_page_length truyền vào SQL={lim} > 100 "
                                 "(query vô giới hạn — DoS/perf, invariant VỠ)")
        self.assertLessEqual(len(data["items"]), 100,
                             "items KHÔNG được vượt 100 (limit query đã cap)")
        # Invariant cốt lõi: len(items) <= pagination.page_size (hết divergence).
        self.assertLessEqual(len(data["items"]), data["pagination"]["page_size"],
                             "len(items) <= pagination.page_size (invariant VỠ trước fix)")

    # ── TC-PAGESZ-02 — biên dưới page_size<=0/âm clamp >=1 ─────────────────
    def test_pagesz_02_list_assets_zero_and_negative_clamped(self):
        """page_size=0 và =-5 → clamp >=1, KHÔNG trả 0 row do limit=0."""
        from assetcore.api.imm00 import list_assets
        for bad in (0, -5):
            resp = list_assets(page=1, page_size=bad)
            self.assertTrue(resp["success"], f"page_size={bad} vẫn success")
            pag = resp["data"]["pagination"]
            self.assertGreaterEqual(pag["page_size"], 1,
                                    f"page_size={bad} → clamp >=1 (KHÔNG 0/âm)")
            # có ít nhất 1 asset (fixture) ⇒ limit>=1 → trả >=1 row (KHÔNG 0 do limit=0)
            self.assertGreaterEqual(len(resp["data"]["items"]), 1,
                                    f"page_size={bad}: limit>=1 → KHÔNG trả 0 row sai")

    # ── TC-PAGESZ-03 — page_size hợp lệ giữ NGUYÊN (no regress trang nhỏ) ───
    def test_pagesz_03_list_assets_valid_page_size_preserved(self):
        """page_size=50 (<=100) → giữ nguyên 50, KHÔNG regress trang nhỏ."""
        from assetcore.api.imm00 import list_assets
        resp = list_assets(page=1, page_size=50)
        self.assertTrue(resp["success"])
        pag = resp["data"]["pagination"]
        self.assertEqual(pag["page_size"], 50, "page_size hợp lệ giữ nguyên 50")
        self.assertLessEqual(len(resp["data"]["items"]), 50,
                             "items <= 50 (limit đúng trang nhỏ)")

    # ── TC-PAGESZ-04 (parity loop) — MỌI endpoint clamp về 100 ─────────────
    def test_pagesz_04_all_endpoints_cap_page_size(self):
        """11 list-endpoint imm00: page_size=99999 →
        pagination.page_size==100 VÀ len(items)<=100 (data-driven)."""
        for fn_name, fn, kwargs in self._endpoints():
            with self.subTest(endpoint=fn_name):
                resp, limits = self._spy_get_list_limits(
                    fn, page=1, page_size=99999, **kwargs)
                self.assertTrue(resp["success"],
                                f"{fn_name} page_size=99999 vẫn success")
                pag = resp["data"]["pagination"]
                self.assertEqual(pag["page_size"], 100,
                                 f"{fn_name}: page_size metadata clamp về 100")
                # DETERMINISTIC-RED: limit_page_length thực <= 100 (trước fix=99999).
                self.assertTrue(limits,
                                f"{fn_name} phải gọi frappe.get_list (spy bắt được)")
                for lim in limits:
                    self.assertLessEqual(lim, 100,
                                         f"{fn_name}: limit_page_length={lim} > 100 "
                                         "(query vô giới hạn)")
                self.assertLessEqual(len(resp["data"]["items"]), 100,
                                     f"{fn_name}: items KHÔNG vượt 100 (limit cap)")
                self.assertLessEqual(len(resp["data"]["items"]), pag["page_size"],
                                     f"{fn_name}: len(items) <= pagination.page_size")

    # ── TC-PAGESZ-05 (invariant count==drill) — list_assets total bất biến ─
    def test_pagesz_05_list_assets_total_invariant_under_cap(self):
        """page_size lớn KHÔNG phá count: pagination.total == count_with_or
        (permission-aware) — fix CHỈ clamp limit, KHÔNG đụng filters/vendor-scope."""
        from assetcore.api.imm00 import list_assets, _DT_ASSET
        from assetcore.services.shared.filters import count_with_or
        from assetcore.services.shared.scope import apply_vendor_scope
        # Tái dựng predicate Y HỆT list_assets (Admin scope: reserved-exclusion qua
        # compose_reserved_into) để so total. import lazy để khớp SSoT handler.
        from assetcore.api.imm00 import compose_reserved_into
        filters = apply_vendor_scope({}, _DT_ASSET)
        filters = compose_reserved_into(filters, _DT_ASSET)
        expected_total = count_with_or(_DT_ASSET, filters, None)
        resp = list_assets(page=1, page_size=100000)
        self.assertTrue(resp["success"])
        self.assertEqual(resp["data"]["pagination"]["total"], expected_total,
                         "page_size lớn KHÔNG được đổi total (count==drill giữ)")

    # ── TC-PAGESZ-06 (SSoT no-literal) — cap định nghĩa 1 nơi ──────────────
    def test_pagesz_06_no_scattered_raw_page_size_limit(self):
        """grep source imm00.py — KHÔNG còn anti-pattern
        `limit_page_length=page_size` (giá trị thô chưa-cap). MỌI list-endpoint
        phải dùng giá trị đã-clamp (pag['page_size']) ⇒ cap định nghĩa ĐÚNG 1 nơi
        (utils/pagination.paginate). Chống copy-paste literal 100 rải 11 lần."""
        import inspect
        from assetcore.api import imm00 as api
        src = inspect.getsource(api)
        # anti-pattern thô: limit_page_length nhận thẳng `page_size` (chưa clamp)
        raw_hits = re.findall(r"limit_page_length\s*=\s*page_size\b", src)
        self.assertEqual(len(raw_hits), 0,
                         "KHÔNG endpoint nào được dùng limit_page_length=page_size "
                         "thô (chưa cap) — phải dùng pag['page_size'] đã clamp")
        # SSoT: clamp [1,100] CHỈ ở paginate (1 literal 100), KHÔNG rải ở imm00 handler
        cap_literals = re.findall(r"min\(\s*(?:int\()?page_size[^)]*,\s*100\s*\)", src)
        self.assertEqual(len(cap_literals), 0,
                         "KHÔNG được inline min(page_size,100) ở imm00.py — cap là "
                         "SSoT tại utils/pagination.paginate (không literal lặp)")

    # ── TC-PAGESZ-07 (regression no-leak) — list_assets vẫn không leak token ─
    def test_pagesz_07_list_assets_no_qr_token_under_cap(self):
        """Fix KHÔNG thêm field select → page_size lớn vẫn KHÔNG leak qr_token."""
        from assetcore.api.imm00 import list_assets
        resp = list_assets(page=1, page_size=100000)
        self.assertTrue(resp["success"])
        for it in resp["data"]["items"]:
            self.assertNotIn("qr_token", it,
                             "list_assets item KHÔNG chứa qr_token (no-leak giữ)")
            self.assertNotIn("token", it,
                             "list_assets item KHÔNG chứa key 'token' thô")


# ══════════════════════════════════════════════════════════════════════════
# IMM-00 / label-pdf — COERCE an toàn tham số `assets` ở 3 endpoint nhãn QR
# (Vòng 10). RED-first: trước fix, `frappe.parse_json(assets)` TRẦN raise
# JSONDecodeError/TypeError → HTTP-500/traceback-leak HOẶC duyệt KÝ TỰ
# (scalar-string → len()/iter trên char). Sau fix: 1 SSoT helper
# `_coerce_asset_names` → luôn list[str] hợp lệ; malformed → [] → empty-path
# (PDF/batch→422, mark→404/empty no-side-effect). KHÔNG 500, KHÔNG leak.
# Ref LL-BE-42 (no-500/no-traceback) · anti-pattern #16/#17 (count==rows /
# in-handler HTTP-200 Error).
# ══════════════════════════════════════════════════════════════════════════
class TestLabelAssetsCoerce(unittest.TestCase):
    """Coerce SSoT cho `assets` ở 3 endpoint nhãn QR — malformed KHÔNG còn 500/leak."""

    _CATEGORY_NAME = "Thiết bị Coerce Nhãn (LABEL-COERCE V10)"
    _NOPRINT_USER = "be_labelcoerce_noprint@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test coerce assets nhãn QR",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", cls._NOPRINT_USER):
            frappe.delete_doc("User", cls._NOPRINT_USER, force=True,
                              ignore_permissions=True)
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

    def _make_asset(self, suffix=""):
        import uuid
        uniq = f"{suffix or '0001'}-{uuid.uuid4().hex[:8]}"
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy Coerce Nhãn {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"COE-SN-{uniq}",
            "asset_code": f"COE-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def _count_label_events(self, asset_name):
        return frappe.db.count("Asset Lifecycle Event",
                               {"asset": asset_name, "event_type": "label_printed"})

    def _reset_response(self):
        frappe.local.response = frappe._dict()

    # Malformed-string inputs gây JSONDecodeError khi parse_json TRẦN (RED).
    _BARE_STRINGS = ["AC-2026-00001", "", "   ", "not-json"]

    @staticmethod
    def _assert_clean_err(tc, resp, http, label=""):
        """Error envelope HTTP-200 VI sạch: success=false + đúng http_status +
        KHÔNG leak traceback/JSONDecodeError trong message."""
        tc.assertIsInstance(resp, dict, f"{label}: phải trả Error envelope (dict)")
        tc.assertFalse(resp.get("success"), f"{label}: success=false")
        tc.assertEqual(resp.get("http_status"), http,
                       f"{label}: http_status={http}")
        msg = resp.get("error", "") or ""
        tc.assertNotIn("Traceback", msg, f"{label}: KHÔNG leak Traceback")
        tc.assertNotIn("JSONDecodeError", msg, f"{label}: KHÔNG leak JSONDecodeError")
        tc.assertNotIn("Expecting value", msg, f"{label}: KHÔNG leak JSON parse text")
        tc.assertNotIn("line 1 column", msg, f"{label}: KHÔNG leak JSON position")

    # ── TC-COERCE-1 (RED-first) — bare code string → 422 empty, KHÔNG 500 ────
    def test_coerce_1_pdf_bare_code_string_422_no_jsondecode(self):
        """print_asset_labels_pdf(assets='AC-2026-00001') (mã thô, KHÔNG ngoặc) →
        _err VALIDATION + _ERR_LABEL_EMPTY + http 422; KHÔNG raise JSONDecodeError,
        KHÔNG traceback. RED trước fix (parse_json trần raise → 500)."""
        from assetcore.api.imm00 import print_asset_labels_pdf, _ERR_LABEL_EMPTY
        self._reset_response()
        raised = None
        try:
            resp = print_asset_labels_pdf(assets="AC-2026-00001", preset="tem-60x100")
        except Exception as e:  # noqa: BLE001 — chứng minh KHÔNG raise sau fix
            raised = e
            resp = None
        self.assertIsNone(raised,
                          f"bare-code string KHÔNG được raise (got {raised!r})")
        self._assert_clean_err(self, resp, 422, "PDF bare-code")
        self.assertEqual(resp.get("error"), _ERR_LABEL_EMPTY,
                         "bare-code coerce→[] → _ERR_LABEL_EMPTY (nhánh empty 422 sẵn có)")
        # `code` = bucket map từ HTTP 422 qua _HTTP_TO_CODE (giữ nguyên envelope sẵn
        # có: _err(_ERR_LABEL_EMPTY, 422) → 'BUSINESS_RULE'). KHÔNG over-specify —
        # chốt là http_status 422 + message VI sạch + KHÔNG leak.
        self.assertIn(resp.get("code"), ("BUSINESS_RULE", "VALIDATION"),
                      "422 → bucket lỗi nghiệp vụ (KHÔNG INTERNAL/500)")
        self.assertNotEqual(frappe.local.response.get("type"), "pdf",
                            "malformed → KHÔNG sinh PDF")

    # ── TC-COERCE-2 — 4 input rỗng/space/garbage trên CẢ 3 endpoint ─────────
    def test_coerce_2_all_three_endpoints_empty_space_garbage(self):
        from assetcore.api.imm00 import (
            print_asset_labels_pdf, get_asset_label_data_batch, mark_label_printed,
            _ERR_LABEL_EMPTY)
        for bad in self._BARE_STRINGS:
            # PDF → 422 empty, KHÔNG 500
            self._reset_response()
            resp = print_asset_labels_pdf(assets=bad, preset="tem-60x100")
            self._assert_clean_err(self, resp, 422, f"PDF {bad!r}")
            self.assertEqual(resp.get("error"), _ERR_LABEL_EMPTY)
            self.assertNotEqual(frappe.local.response.get("type"), "pdf")
            # batch (read-only) → batch RỖNG hợp lệ (_ok success), KHÔNG 500
            resp = get_asset_label_data_batch(assets=bad)
            self.assertIsInstance(resp, dict, f"batch {bad!r}: dict")
            self.assertTrue(resp.get("success"),
                            f"batch {bad!r}: malformed→[] → batch rỗng hợp lệ (no-500)")
            self.assertEqual(resp.get("data"), [],
                             f"batch {bad!r}: data rỗng (0 entry)")
            # mark → 404/empty no-side-effect (KHÔNG ghi ALE/audit)
            a = self._make_asset("mk")
            before_ale = frappe.db.count("Asset Lifecycle Event",
                                         {"event_type": "label_printed"})
            before_audit = frappe.db.count("IMM Audit Trail")
            resp = mark_label_printed(assets=bad)
            self.assertIsInstance(resp, dict, f"mark {bad!r}: dict")
            # mark malformed→[] → 404/empty no-side-effect: chấp nhận 404 HOẶC
            # empty-success (result rỗng) — INVARIANT binding là KHÔNG ghi gì +
            # KHÔNG 500/leak. KHÔNG over-specify success flag.
            self.assertNotEqual(resp.get("http_status"), 500,
                                f"mark {bad!r}: KHÔNG HTTP-500")
            self.assertNotIn("Traceback", resp.get("error", "") or "", f"mark {bad!r}")
            self.assertNotIn("JSONDecodeError", resp.get("error", "") or "", f"mark {bad!r}")
            self.assertNotIn("Expecting value", resp.get("error", "") or "", f"mark {bad!r}")
            self.assertEqual(
                frappe.db.count("Asset Lifecycle Event",
                                {"event_type": "label_printed"}), before_ale,
                f"mark {bad!r}: KHÔNG tạo ALE label_printed")
            self.assertEqual(frappe.db.count("IMM Audit Trail"), before_audit,
                             f"mark {bad!r}: KHÔNG tạo IMM Audit Trail")

    # ── TC-COERCE-3 — JSON-scalar-string KHÔNG duyệt từng KÝ TỰ ──────────────
    def test_coerce_3_json_scalar_string_no_char_walk(self):
        """assets='"AC-1"' (JSON-scalar-string) → coerce→[] (KHÔNG biến str thành
        list ký tự). Spy frappe.db.exists: KHÔNG được gọi với 'A'/'C'/'-'/'1'.
        PDF → 422 empty, KHÔNG render 4 ô lỗi."""
        from unittest.mock import patch
        import assetcore.api.imm00 as api
        from assetcore.api.imm00 import _ERR_LABEL_EMPTY
        self._reset_response()
        seen_args = []
        real_exists = api.frappe.db.exists

        def spy_exists(*a, **k):
            seen_args.append((a, k))
            return real_exists(*a, **k)

        with patch.object(api.frappe.db, "exists", side_effect=spy_exists):
            resp = api.print_asset_labels_pdf(assets='"AC-1"', preset="tem-60x100")
        # KHÔNG có call exists nào với 1-ký-tự lẻ (char-walk dấu hiệu)
        single_chars = {"A", "C", "-", "1"}
        for a, k in seen_args:
            for val in list(a) + list(k.values()):
                self.assertNotIn(
                    val, single_chars,
                    f"frappe.db.exists bị gọi với ký tự lẻ {val!r} (char-walk!)")
        self._assert_clean_err(self, resp, 422, "PDF scalar-string")
        self.assertEqual(resp.get("error"), _ERR_LABEL_EMPTY,
                         "scalar-string coerce→[] → _ERR_LABEL_EMPTY (KHÔNG ô lỗi)")
        self.assertNotEqual(frappe.local.response.get("type"), "pdf")

    # ── TC-COERCE-4 — JSON-number / JSON-object → no-TypeError, _err 422 ─────
    def test_coerce_4_json_number_and_object_no_typeerror(self):
        from assetcore.api.imm00 import (
            print_asset_labels_pdf, get_asset_label_data_batch, mark_label_printed,
            _ERR_LABEL_EMPTY)
        for bad in ("123", '{"a":1}'):
            self._reset_response()
            resp = print_asset_labels_pdf(assets=bad, preset="tem-60x100")
            self._assert_clean_err(self, resp, 422, f"PDF {bad!r}")
            self.assertEqual(resp.get("error"), _ERR_LABEL_EMPTY)
            self.assertNotEqual(frappe.local.response.get("type"), "pdf")
            # batch read-only → batch rỗng hợp lệ, no-500/no-TypeError
            resp = get_asset_label_data_batch(assets=bad)
            self.assertTrue(resp.get("success"), f"batch {bad!r}: no-TypeError")
            self.assertEqual(resp.get("data"), [], f"batch {bad!r}: data rỗng")
            # mark → 404/empty no-side-effect (KHÔNG 500/TypeError/leak)
            resp = mark_label_printed(assets=bad)
            self.assertIsInstance(resp, dict, f"mark {bad!r}: dict")
            self.assertNotEqual(resp.get("http_status"), 500,
                                f"mark {bad!r}: KHÔNG HTTP-500/TypeError")
            self.assertNotIn("Traceback", resp.get("error", "") or "", f"mark {bad!r}")

    # ── TC-COERCE-5 (HAPPY no-regression) — list thật & JSON-array-string ────
    def test_coerce_5_happy_list_and_json_array_string_parity(self):
        """assets=['AC-A','AC-B'] và assets='["AC-A","AC-B"]' → hành vi GIỮ NGUYÊN:
        PDF ra %PDF + đúng số trang (pypdf); batch 2 entry đúng thứ tự; mark ghi N
        event. Byte-for-byte parity với baseline."""
        import io
        import json
        from pypdf import PdfReader
        from assetcore.api.imm00 import (
            print_asset_labels_pdf, get_asset_label_data_batch, mark_label_printed)
        a1 = self._make_asset("hpyA")
        a2 = self._make_asset("hpyB")
        list_input = [a1.name, a2.name]
        json_input = json.dumps([a1.name, a2.name])

        for label, inp in (("list", list_input), ("json-str", json_input)):
            # PDF: %PDF + 2 trang THẬT
            self._reset_response()
            print_asset_labels_pdf(assets=inp, preset="tem-60x100")
            self.assertEqual(frappe.local.response.get("type"), "pdf",
                             f"{label}: happy path → PDF")
            content = bytes(frappe.local.response.get("filecontent"))
            self.assertTrue(content.startswith(b"%PDF-"), f"{label}: magic %PDF-")
            self.assertEqual(len(PdfReader(io.BytesIO(content)).pages), 2,
                             f"{label}: 2 asset → 2 trang PDF THẬT (pypdf)")
            # batch: 2 entry ĐÚNG thứ tự
            resp = get_asset_label_data_batch(assets=inp)
            self.assertTrue(resp.get("success"), f"{label}: batch success")
            data = resp.get("data")
            self.assertEqual(len(data), 2, f"{label}: 2 entry")
            self.assertEqual(data[0].get("name"), a1.name,
                             f"{label}: thứ tự[0]==a1")
            self.assertEqual(data[1].get("name"), a2.name,
                             f"{label}: thứ tự[1]==a2")

        # mark: ghi đúng N event (2 asset) cho cả 2 dạng input
        for label, inp in (("list", list_input), ("json-str", json_input)):
            b1 = self._count_label_events(a1.name)
            b2 = self._count_label_events(a2.name)
            resp = mark_label_printed(assets=inp)
            self.assertTrue(resp.get("success"), f"{label}: mark success")
            self.assertEqual(self._count_label_events(a1.name), b1 + 1,
                             f"{label}: a1 +1 event")
            self.assertEqual(self._count_label_events(a2.name), b2 + 1,
                             f"{label}: a2 +1 event")

    # ── TC-COERCE-6 — list lẫn non-str/empty: chỉ str hợp lệ lọt IDOR/render ─
    def test_coerce_6_list_filters_non_str_and_empty(self):
        """assets=[1,'AC-A',None,''] → CHỈ 'AC-A' lọt vào exists. Spy
        frappe.db.exists KHÔNG được gọi với 1/None/'' (chỉ 'AC-A')."""
        from unittest.mock import patch
        import assetcore.api.imm00 as api
        a = self._make_asset("flt")
        self._reset_response()
        seen = []
        real_exists = api.frappe.db.exists

        def spy_exists(dt, name, *a2, **k):
            seen.append(name)
            return real_exists(dt, name, *a2, **k)

        with patch.object(api.frappe.db, "exists", side_effect=spy_exists):
            api.print_asset_labels_pdf(
                assets=[1, a.name, None, ""], preset="tem-60x100")
        # exists chỉ thấy 'AC-A' (asset thật); KHÔNG thấy 1/None/'' lọt qua filter
        self.assertIn(a.name, seen, "asset hợp lệ phải qua exists")
        for bad in (1, None, ""):
            self.assertNotIn(bad, seen,
                             f"phần tử non-str/empty {bad!r} KHÔNG được đẩy vào exists")
        # render thành công (1 asset hợp lệ) → PDF
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "1 phần tử hợp lệ → vẫn render PDF")

    # ── TC-COERCE-7 (gate-order) — thiếu cap + bare-code → 403 TRƯỚC coerce ──
    def test_coerce_7_rbac_runs_before_coerce(self):
        """user KHÔNG có cap asset.print + assets='AC-bad' → vẫn PermissionError
        (403) TRƯỚC coerce/empty (rbac.require chạy đầu) — coerce KHÔNG nuốt 403
        thành 422, KHÔNG rò giới hạn cho khách chưa-auth."""
        from assetcore.api.imm00 import print_asset_labels_pdf
        from assetcore.services.shared import rbac
        u = self._ensure_user(self._NOPRINT_USER, ["Guest"])
        frappe.clear_cache()
        frappe.db.commit()
        self._reset_response()
        try:
            frappe.set_user(self._NOPRINT_USER)
            self.assertFalse(rbac.can("asset.print"),
                             "tiền đề: user KHÔNG có asset.print")
            with self.assertRaises(frappe.PermissionError):
                print_asset_labels_pdf(assets="AC-bad", preset="tem-60x100")
        finally:
            frappe.set_user("Administrator")
            frappe.clear_cache()
            rbac.invalidate_capabilities(self._NOPRINT_USER)
        self.assertNotEqual(frappe.local.response.get("type"), "pdf",
                            "thiếu cap → KHÔNG render dù coerce")

    # ── TC-COERCE-8 (SSoT) — 1 helper, KHÔNG parse_json(assets) trần ─────────
    def test_coerce_8_single_ssot_helper_no_bare_parse_json(self):
        """grep api/imm00.py: KHÔNG còn `frappe.parse_json(assets)` trần; cả 3
        endpoint gọi `_coerce_asset_names`; helper định nghĩa ĐÚNG 1 lần."""
        import inspect
        from assetcore.api import imm00 as api
        src = inspect.getsource(api)
        # KHÔNG còn handler-pattern TRẦN cũ `frappe.parse_json(assets) if isinstance`
        # (ternary KHÔNG try/except — chính là dòng gây JSONDecodeError/500 trước fix).
        bare_handler = re.findall(
            r"frappe\.parse_json\(\s*assets\s*\)\s+if\s+isinstance", src)
        self.assertEqual(len(bare_handler), 0,
                         "KHÔNG được còn `frappe.parse_json(assets) if isinstance` "
                         "trần ở handler (phải qua _coerce_asset_names có try/except)")
        # CHỈ còn DUY NHẤT 1 `frappe.parse_json(assets)` — nằm TRONG _coerce_asset_names
        # (bọc try/except ValueError/TypeError → KHÔNG raise).
        all_parse = re.findall(r"frappe\.parse_json\(\s*assets\s*\)", src)
        self.assertEqual(len(all_parse), 1,
                         "frappe.parse_json(assets) chỉ xuất hiện 1 lần (trong helper "
                         "_coerce_asset_names bọc try/except), KHÔNG rải ở 3 handler")
        # helper định nghĩa đúng 1 lần
        self.assertEqual(len(re.findall(r"def _coerce_asset_names\(", src)), 1,
                         "_coerce_asset_names định nghĩa ĐÚNG 1 lần (SSoT)")
        # parse_json trong helper PHẢI bọc try/except (no-raise contract)
        helper_src = inspect.getsource(api._coerce_asset_names)
        self.assertIn("try:", helper_src, "helper bọc parse_json trong try/except")
        self.assertIn("except", helper_src, "helper bắt JSONDecodeError/TypeError → []")
        # 3 endpoint cùng tham chiếu helper
        self.assertGreaterEqual(
            len(re.findall(r"_coerce_asset_names\(\s*assets\s*\)", src)), 3,
            "cả 3 endpoint (batch/mark/pdf) phải gọi _coerce_asset_names(assets)")
        # helper callable + luôn trả list[str]
        from assetcore.api.imm00 import _coerce_asset_names
        for inp, expect in (
            (["AC-1", "AC-2"], ["AC-1", "AC-2"]),
            ('["AC-1"]', ["AC-1"]),
            ('"AC-1"', []),            # scalar-string → []
            ("AC-2026-00001", []),     # bare code → []
            ("", []), ("   ", []), ("not-json", []),
            ("123", []), ('{"a":1}', []),
            ([1, "AC-X", None, ""], ["AC-X"]),
            (None, []),
        ):
            out = _coerce_asset_names(inp)
            self.assertIsInstance(out, list, f"{inp!r}: trả list")
            self.assertTrue(all(isinstance(x, str) and x for x in out),
                            f"{inp!r}: mọi phần tử là str non-empty")
            self.assertEqual(out, expect, f"{inp!r} → {expect!r}")


# ══════════════════════════════════════════════════════════════════════════
# Vòng 15 — DEDUP within-call ở SSoT `_coerce_asset_names` (IMM-00 / label-pdf)
# RC: assets chứa name LẶP trong 1 call ([a1,a1,a1]) → mark ghi N× event/audit
# trùng (audit chain phình), PDF in N trang trùng, batch trả N entry trùng, cap
# đo TRÊN list-thô (vượt 200 dù <200 unique). Fix: dedup giữ-thứ-tự TRONG helper
# (within-call) → 1 chỗ áp cho cả 3 endpoint. BẤT BIẾN cross-call GIỮ NGUYÊN
# (2 call riêng [a1] → 2 event — dedup KHÔNG xuyên-call).
# Ref: anti-pattern khuếch-đại ghi-audit/PDF · pypdf đếm TRANG THẬT (LL-TEST-26).
# ══════════════════════════════════════════════════════════════════════════
class TestLabelAssetsDedup(unittest.TestCase):
    """Dedup within-call ở `_coerce_asset_names` — chặn khuếch đại audit/PDF/batch."""

    _CATEGORY_NAME = "Thiết bị Dedup Nhãn (LABEL-DEDUP V15)"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        _orphan = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if _orphan:
            frappe.delete_doc("AC Asset Category", _orphan, force=True,
                              ignore_permissions=True)
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls._CATEGORY_NAME,
            "description": "Category cho test dedup assets nhãn QR",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        # cleanup theo field category_name (autoname CAT-#### — LL-TEST-23)
        real = frappe.db.get_value(
            "AC Asset Category", {"category_name": cls._CATEGORY_NAME}, "name")
        if real:
            frappe.delete_doc("AC Asset Category", real,
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
            "asset_name": f"Máy Dedup Nhãn {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"DED-SN-{uniq}",
            "asset_code": f"DED-ASSET-{uniq}",
            "lifecycle_status": "Active",
        })
        self._created.append(doc.name)
        return doc

    def _count_label_events(self, asset_name):
        return frappe.db.count(
            "Asset Lifecycle Event",
            {"asset": asset_name, "event_type": "label_printed"})

    def _count_audit(self, asset_name):
        return frappe.db.count("IMM Audit Trail", {"asset": asset_name})

    def _reset_response(self):
        frappe.local.response = frappe._dict()

    # ── TC-DEDUP-1 — helper trả unique GIỮ thứ tự xuất hiện đầu ──────────────
    def test_dedup_1_helper_unique_preserves_first_seen_order(self):
        """_coerce_asset_names dedup TRONG-call, giữ thứ tự xuất hiện đầu, bỏ trùng sau."""
        from assetcore.api.imm00 import _coerce_asset_names
        # spec acceptance: ['AC-1','AC-1','AC-2','AC-1'] -> ['AC-1','AC-2']
        self.assertEqual(
            _coerce_asset_names(["AC-1", "AC-1", "AC-2", "AC-1"]),
            ["AC-1", "AC-2"],
            "giữ thứ tự xuất hiện đầu, bỏ mọi lần lặp sau")
        # multi-dup mixed thứ tự
        self.assertEqual(
            _coerce_asset_names(["AC-3", "AC-1", "AC-3", "AC-2", "AC-1", "AC-2"]),
            ["AC-3", "AC-1", "AC-2"],
            "dedup mixed giữ first-seen order")
        # JSON-array-string cũng dedup (qua cùng helper)
        self.assertEqual(
            _coerce_asset_names('["AC-1","AC-2","AC-1"]'),
            ["AC-1", "AC-2"],
            "JSON-array-string dedup qua cùng SSoT")
        # phần tử non-str/empty bị loại TRƯỚC khi dedup; không trùng → giữ nguyên
        self.assertEqual(
            _coerce_asset_names([1, "AC-X", None, "", "AC-X"]),
            ["AC-X"],
            "loại non-str/empty + dedup → 1 phần tử")
        # no-dup → không đổi (idempotent với list đã unique)
        self.assertEqual(
            _coerce_asset_names(["AC-A", "AC-B", "AC-C"]),
            ["AC-A", "AC-B", "AC-C"],
            "list đã unique → giữ nguyên")

    # ── TC-DEDUP-2 — mark([a1,a1,a1]) 1 call → ĐÚNG 1 event + 1 audit ────────
    def test_dedup_2_mark_label_printed_dups_one_call_one_event(self):
        """1 call mark_label_printed([a1,a1,a1]) → 1 ALE label_printed + 1 IMM Audit
        Trail cho a1 (event_count=1), KHÔNG 3 (chặn khuếch đại ghi-audit)."""
        from assetcore.api.imm00 import mark_label_printed
        a1 = self._make_asset("d2")
        ev_before = self._count_label_events(a1.name)
        au_before = self._count_audit(a1.name)
        resp = mark_label_printed(assets=[a1.name, a1.name, a1.name])
        self.assertTrue(resp["success"], "dup-in-call hợp lệ → success")
        self.assertEqual(resp["data"]["event_count"], 1,
                         "dedup within-call → event_count=1 (KHÔNG 3)")
        self.assertEqual(resp["data"]["printed"], [a1.name],
                         "printed = list đã dedup (1 phần tử)")
        self.assertEqual(self._count_label_events(a1.name), ev_before + 1,
                         "ĐÚNG 1 ALE label_printed (KHÔNG 3)")
        self.assertEqual(self._count_audit(a1.name), au_before + 1,
                         "ĐÚNG 1 IMM Audit Trail (KHÔNG 3)")

    # ── TC-DEDUP-3 — ANTI-REGRESS cross-call: 2 call riêng → 2 event ─────────
    def test_dedup_3_cross_call_still_two_events_no_false_green(self):
        """Dedup CHỈ trong-call: 2 call RIÊNG mark_label_printed([a1]) → 2 event
        (bất biến cross-call GIỮ NGUYÊN — KHÔNG xuyên-call dedup)."""
        from assetcore.api.imm00 import mark_label_printed
        a1 = self._make_asset("d3")
        ev_before = self._count_label_events(a1.name)
        au_before = self._count_audit(a1.name)
        mark_label_printed(assets=[a1.name])
        mark_label_printed(assets=[a1.name])
        self.assertEqual(self._count_label_events(a1.name), ev_before + 2,
                         "2 call riêng = 2 event (dedup KHÔNG xuyên-call)")
        self.assertEqual(self._count_audit(a1.name), au_before + 2,
                         "2 call riêng = 2 audit (cross-call invariant)")

    # ── TC-DEDUP-4 — PDF([a1,a1]) → 1 TRANG THẬT (pypdf) + MediaBox đúng khổ ─
    def test_dedup_4_pdf_dups_one_real_page(self):
        """print_asset_labels_pdf([a1,a1]) → PDF ĐÚNG 1 trang (pypdf PdfReader.pages
        ==1), MediaBox đúng khổ mm — KHÔNG 2 trang trùng (LL-TEST-26: đếm TRANG THẬT)."""
        import io
        from pypdf import PdfReader
        from assetcore.api.imm00 import print_asset_labels_pdf
        a1 = self._make_asset("d4")
        self._reset_response()
        print_asset_labels_pdf(assets=[a1.name, a1.name], preset="tem-60x100")
        self.assertEqual(frappe.local.response.get("type"), "pdf",
                         "dup hợp lệ → render PDF")
        content = bytes(frappe.local.response.get("filecontent"))
        self.assertTrue(content.startswith(b"%PDF-"), "magic %PDF-")
        reader = PdfReader(io.BytesIO(content))
        self.assertEqual(len(reader.pages), 1,
                         "[a1,a1] dedup → ĐÚNG 1 trang PDF THẬT (KHÔNG 2 trang trùng)")
        # MediaBox đúng khổ 60×100mm (1mm = 72/25.4 pt) — chống xoay/lệch
        mb = reader.pages[0].mediabox
        pt = 72.0 / 25.4
        self.assertAlmostEqual(float(mb.width), 60 * pt, delta=2,
                               msg="MediaBox width ≈ 60mm (KHÔNG xoay)")
        self.assertAlmostEqual(float(mb.height), 100 * pt, delta=2,
                               msg="MediaBox height ≈ 100mm (KHÔNG xoay)")

    # ── TC-DEDUP-5 — batch([a1,a1]) → 1 phần tử ─────────────────────────────
    def test_dedup_5_batch_dups_one_entry(self):
        """get_asset_label_data_batch([a1,a1]) → 1 phần tử (KHÔNG 2 entry trùng)."""
        from assetcore.api.imm00 import get_asset_label_data_batch
        a1 = self._make_asset("d5")
        resp = get_asset_label_data_batch(assets=[a1.name, a1.name])
        self.assertTrue(resp["success"], "dup hợp lệ → success")
        data = resp["data"]
        self.assertEqual(len(data), 1, "[a1,a1] dedup → 1 phần tử (KHÔNG 2)")
        self.assertEqual(data[0]["name"], a1.name, "phần tử duy nhất là a1")

    # ── TC-DEDUP-6 — cap đo TRÊN list đã dedup ──────────────────────────────
    def _cap(self):
        from assetcore.services import imm00 as _svc
        return _svc._MAX_LABEL_BATCH

    def test_dedup_6a_cap_measured_on_unique_201_unique_413(self):
        """201 unique name → 413 (cap đo trên list đã dedup, vẫn 413 khi >200 unique)."""
        from assetcore.api.imm00 import get_asset_label_data_batch
        from assetcore.services.imm00 import _ERR_BATCH_TOO_LARGE
        cap = self._cap()
        # cap+1 tên giả UNIQUE (cap chặn TRƯỚC exists → tên giả vô hại)
        names = [f"AC-ASSET-DED-UNIQ-{i:04d}" for i in range(cap + 1)]
        self.assertEqual(len(set(names)), cap + 1, "tiền đề: cap+1 unique")
        resp = get_asset_label_data_batch(assets=names)
        self.assertFalse(resp["success"], ">cap unique → KHÔNG success")
        self.assertEqual(resp["http_status"], 413,
                         ">200 unique → 413 (cap đo trên unique)")
        self.assertEqual(resp["error"], _ERR_BATCH_TOO_LARGE)

    def test_dedup_6b_cap_passes_when_dups_collapse_under_cap(self):
        """300 phần tử nhưng <200 UNIQUE → qua cap (KHÔNG 413) vì cap đo trên dedup.

        a1+a2 lặp 150 lần mỗi cái = 300 phần tử thô → dedup còn 2 unique → batch
        trả 2 entry, KHÔNG 413 (cap đo SAU dedup, KHÔNG trên list-thô)."""
        from assetcore.api.imm00 import get_asset_label_data_batch
        a1 = self._make_asset("d6b1")
        a2 = self._make_asset("d6b2")
        raw = ([a1.name, a2.name] * 150)  # 300 phần tử thô, 2 unique
        self.assertEqual(len(raw), 300, "tiền đề: 300 phần tử thô")
        self.assertLess(len(set(raw)), self._cap(), "tiền đề: <200 unique")
        resp = get_asset_label_data_batch(assets=raw)
        self.assertTrue(resp["success"],
                        "300 thô / 2 unique → qua cap (KHÔNG 413)")
        data = resp["data"]
        self.assertEqual(len(data), 2, "dedup → 2 entry (KHÔNG 300)")
        self.assertEqual([d["name"] for d in data], [a1.name, a2.name],
                         "giữ thứ tự first-seen sau dedup")

    # ── TC-DEDUP-7 — malformed assets → [] GIỮ (no-500/no-traceback, LL-BE-42) ─
    def test_dedup_7_malformed_still_empty_no_500(self):
        """Malformed input → [] giữ nguyên (dedup KHÔNG phá hợp đồng no-500 cũ)."""
        from assetcore.api.imm00 import _coerce_asset_names
        for bad in ("AC-2026-00001", "", "   ", "not-json", "123",
                    '{"a":1}', '"AC-1"', "true", None, 123, {"a": 1}, True):
            out = _coerce_asset_names(bad)
            self.assertEqual(out, [], f"{bad!r}: malformed → [] (no-500/no-traceback)")
            self.assertIsInstance(out, list, f"{bad!r}: luôn list")


# ══════════════════════════════════════════════════════════════════════════
# XII. INVARIANT — Reconcile lifecycle map ⇄ workflow ⇄ fixtures
#      (CR-WF-00-LIFECYCLE, Vòng 32). Spec: docs/imm-00/04_Backend_Design.md
#      §II.1.7-RECON + ADR-IMM00-LIFECYCLE-SM ; docs/imm-00/07_Testing_QA.md §XII.
#      Guard bất-biến chống drift SSoT `_VALID_ASSET_TRANSITIONS`
#      ⇄ ac_asset_lifecycle_workflow.json ⇄ fixtures/workflow.json.
# ══════════════════════════════════════════════════════════════════════════
from assetcore.services.shared import AssetStatus as _AssetStatus
from assetcore.services.imm00 import (
    _VALID_ASSET_TRANSITIONS as _LC_MAP,
    _LIFECYCLE_EXCEPTION_EDGES as _LC_EXC,
    _NEG09_BLOCK_DECOM_FROM as _LC_NEG09,
    is_valid_asset_transition as _lc_is_valid,
    transition_asset_status as _lc_transition,
    InvalidAssetTransition as _LcInvalidTransition,
    # CR-WF-00-LIFECYCLE-SURFACE — DRIVER duy nhất cấp allowed_transitions cho CẢ
    # get_asset emit LẪN reconcile test (single-SSoT, KHÔNG bản sao bảng transition).
    asset_allowed_transitions as _asset_allowed_transitions,
)

# 8 mã canonical AssetStatus (constants.py:88-95) — grounding count workflow states.
_CANONICAL_ASSET_STATES = {
    _AssetStatus.DRAFT, _AssetStatus.COMMISSIONED, _AssetStatus.ACTIVE,
    _AssetStatus.UNDER_MAINTENANCE, _AssetStatus.UNDER_REPAIR, _AssetStatus.CALIBRATING,
    _AssetStatus.OUT_OF_SERVICE, _AssetStatus.DECOMMISSIONED,
}
# 2 cạnh SURFACE Vòng 32 (cả 2 →Out of Service) — ADR-IMM00-LIFECYCLE-SM.
_SURFACED_OOS_EDGES = {
    (_AssetStatus.COMMISSIONED, _AssetStatus.OUT_OF_SERVICE),
    (_AssetStatus.UNDER_MAINTENANCE, _AssetStatus.OUT_OF_SERVICE),
}
_ADMIN_LIFECYCLE_ROLES = {"AssetCore Super Admin", "System Manager"}
# Nhãn action Desk hợp lệ (anti-drift) — 14 nhãn (12 cũ + reuse "Đưa ra khỏi sử dụng").
_LIFECYCLE_ACTION_LABELS = {
    "Commission", "Activate", "Bắt đầu bảo trì", "Hoàn thành bảo trì",
    "Bắt đầu sửa chữa", "Hoàn thành sửa chữa", "Không thể sửa chữa",
    "Bắt đầu hiệu chuẩn", "Hiệu chuẩn đạt", "Hiệu chuẩn không đạt",
    "Đưa ra khỏi sử dụng", "Khôi phục hoạt động", "Sửa chữa lại", "Thanh lý",
}


def _load_lifecycle_source_workflow() -> dict:
    """Parse ac_asset_lifecycle_workflow.json (SOURCE — path `_sync_workflows` import_doc)."""
    import json as _json
    path = frappe.get_app_path(
        "assetcore", "assetcore", "workflow", "ac_asset_lifecycle_workflow.json")
    with open(path, encoding="utf-8") as fh:
        return _json.load(fh)


def _load_lifecycle_fixture_workflow() -> dict:
    """Parse block 'AC Asset Lifecycle' trong fixtures/workflow.json (fresh-install parity)."""
    import json as _json
    path = frappe.get_app_path("assetcore", "fixtures", "workflow.json")
    with open(path, encoding="utf-8") as fh:
        data = _json.load(fh)
    for w in data:
        if w.get("doctype") == "Workflow" and w.get("name") == "AC Asset Lifecycle":
            return w
    raise AssertionError("Không tìm thấy 'AC Asset Lifecycle' trong fixtures/workflow.json")


def _wf_edge_pairs(wf: dict) -> set:
    """{(state, next_state)} distinct — bỏ role (đối soát cạnh state-machine)."""
    return {(t["state"], t["next_state"]) for t in wf.get("transitions", [])}


def _wf_edge_roles(wf: dict) -> dict:
    """{(state, next_state): set(allowed)} — coverage role per cạnh."""
    from collections import defaultdict
    roles = defaultdict(set)
    for t in wf.get("transitions", []):
        roles[(t["state"], t["next_state"])].add(t.get("allowed"))
    return roles


class TestLifecycleReconcileInvariant(unittest.TestCase):
    """Đối soát bất-biến map ⇄ workflow ⇄ fixtures + helper NEG-09 (pure/static, no-DB)."""

    # ── TC-00-WF-RECON-01 — INVARIANT chính (map ⇄ workflow edge-by-edge) ──────
    def test_asset_lifecycle_map_matches_workflow(self):
        wf = _load_lifecycle_source_workflow()
        wf_pairs = _wf_edge_pairs(wf)
        map_pairs = {(s, nxt) for s, nexts in _LC_MAP.items() for nxt in nexts}
        exc = set(_LC_EXC.keys())

        # (a) mọi cạnh map-không-surface PHẢI ∈ EXCEPTION_EDGES (0 drift câm).
        self.assertEqual(
            map_pairs - wf_pairs, exc,
            "DRIFT map⊋workflow chưa giải trình. "
            f"Cạnh thừa (drift): {sorted((map_pairs - wf_pairs) - exc)}; "
            f"Cạnh EXCEPTION thiếu surface bù: {sorted(exc - (map_pairs - wf_pairs))}",
        )
        # công thức acceptance edge-by-edge: ∀s set(map[s]) − exc_codom[s] == wf_codom[s]
        for s, nexts in _LC_MAP.items():
            exc_codom = {e[1] for e in exc if e[0] == s}
            wf_codom = {t["next_state"] for t in wf["transitions"] if t["state"] == s}
            self.assertEqual(
                set(nexts) - exc_codom, wf_codom,
                f"state '{s}': (map − EXCEPTION) ≠ workflow codomain")
            # SINGLE-SSoT (CR-WF-00-LIFECYCLE-SURFACE): helper CTA-surfaceable
            # ``asset_allowed_transitions`` là DRIVER get_asset emit. Đối soát TRỰC
            # TIẾP với workflow codomain TRỪ terminal Decommissioned — carve-out
            # IMM-14: "Thanh lý" (Active/Out of Service → Decommissioned) CÓ surface
            # trong workflow JSON NHƯNG KHÔNG là CTA dropdown chuyển-trạng-thái tự do
            # (thanh lý đi qua Asset Decommission closure). Chứng minh 0 drift giữa
            # BE-emitted CTA ⇄ workflow, đọc TỪ helper (không bản sao bảng nào).
            self.assertEqual(
                set(_asset_allowed_transitions(s)),
                wf_codom - {_AssetStatus.DECOMMISSIONED},
                f"state '{s}': helper CTA-surfaceable ≠ workflow codomain (non-terminal)")

        # (b) 0 cạnh workflow mồ côi — mọi CTA Desk ⊆ map.
        self.assertEqual(
            wf_pairs - map_pairs, set(),
            f"CTA Desk dẫn tới transition ∉ state-machine map: {sorted(wf_pairs - map_pairs)}")

        # (c) grounding count: 8 state workflow == 8 mã AssetStatus enum.
        self.assertEqual(len(wf["states"]), 8, "workflow phải có đúng 8 state")
        self.assertEqual({s["state"] for s in wf["states"]}, _CANONICAL_ASSET_STATES,
                         "state workflow lệch AssetStatus enum (typo/drift)")

        # (d) 2 cạnh SURFACE mỗi cạnh có ĐỦ cả 2 admin role.
        roles = _wf_edge_roles(wf)
        for e in _SURFACED_OOS_EDGES:
            self.assertTrue(
                _ADMIN_LIFECYCLE_ROLES <= roles.get(e, set()),
                f"cạnh SURFACE {e} thiếu role: {_ADMIN_LIFECYCLE_ROLES - roles.get(e, set())}")

        # (e) anti-drift nhãn action.
        actual = {t["action"] for t in wf["transitions"]}
        self.assertTrue(actual <= _LIFECYCLE_ACTION_LABELS,
                        f"nhãn action lạ: {sorted(actual - _LIFECYCLE_ACTION_LABELS)}")

    # ── EXCEPTION_EDGES rationale (0 cạnh câm không giải trình) ────────────────
    def test_lifecycle_exception_edges_have_rationale(self):
        self.assertTrue(_LC_EXC, "EXCEPTION_EDGES rỗng — phải khai tường minh")
        for edge, rationale in _LC_EXC.items():
            self.assertIn(rationale, {"NEG-09-superseded", "programmatic-only"},
                          f"{edge}: rationale '{rationale}' ∉ tập cho phép")
            self.assertTrue(str(rationale).strip(), f"{edge}: rationale rỗng")
            # bất-biến ngữ nghĩa: mọi cạnh EXCEPTION đều →Decommissioned.
            self.assertEqual(edge[1], _AssetStatus.DECOMMISSIONED,
                             f"{edge}: cạnh EXCEPTION phải →Decommissioned")
        self.assertEqual(len(_LC_EXC), 5, "phải đúng 5 cạnh EXCEPTION")
        self.assertEqual(sum(1 for v in _LC_EXC.values() if v == "programmatic-only"), 2)
        self.assertEqual(sum(1 for v in _LC_EXC.values() if v == "NEG-09-superseded"), 3)
        # 3 cạnh NEG-09-superseded == đúng 3 from-state của _NEG09_BLOCK_DECOM_FROM.
        neg09_edges = {e[0] for e, v in _LC_EXC.items() if v == "NEG-09-superseded"}
        self.assertEqual(neg09_edges, set(_LC_NEG09.keys()),
                         "NEG-09-superseded from-states lệch _NEG09_BLOCK_DECOM_FROM")

    # ── helper asset_allowed_transitions: bất-biến CTA-surfaceable (pure, no-DB) ──
    def test_asset_allowed_transitions_never_contains_decommissioned(self):
        """CR-WF-00-LIFECYCLE-SURFACE BẤT-BIẾN: ∀ status trong _VALID_ASSET_TRANSITIONS,
        Decommissioned KHÔNG bao giờ ∈ output helper — carve-out IMM-14 (thanh lý đi
        qua Asset Decommission closure, KHÔNG là CTA Desk tự do). Đối xứng
        _LIFECYCLE_EXCEPTION_EDGES + loại terminal. NB: 2 cạnh (Active/Out of Service
        → Decommissioned) CÓ surface trong workflow ('Thanh lý') nhưng KHÔNG là
        exception-edge ⇒ chỉ 'loại terminal' mới chặn được → RED nếu helper thiếu
        filter terminal."""
        for s in _LC_MAP:
            out = _asset_allowed_transitions(s)
            self.assertIsInstance(out, list, f"state '{s}': helper phải trả list")
            self.assertNotIn(
                _AssetStatus.DECOMMISSIONED, out,
                f"state '{s}': Decommissioned KHÔNG được surface làm CTA dropdown")
            self.assertEqual(out, sorted(out), f"state '{s}': helper phải sorted ổn định")
            # mọi phần tử ∈ codomain SSoT (KHÔNG bịa target ngoài map)
            self.assertTrue(set(out) <= set(_LC_MAP.get(s, set())),
                            f"state '{s}': helper phát target ∉ _VALID_ASSET_TRANSITIONS")

    def test_asset_allowed_transitions_active_subset_and_terminal_empty(self):
        """Active → đúng 4 CTA {Under Maintenance, Under Repair, Calibrating, Out of
        Service} (KHÔNG Decommissioned); terminal Decommissioned + status lạ → []."""
        self.assertEqual(
            _asset_allowed_transitions(_AssetStatus.ACTIVE),
            ["Calibrating", "Out of Service", "Under Maintenance", "Under Repair"])
        self.assertEqual(_asset_allowed_transitions(_AssetStatus.DECOMMISSIONED), [])
        self.assertEqual(_asset_allowed_transitions("Trạng thái không tồn tại"), [])

    # ── TC-00-WF-RECON-02 — lockstep source ⇄ fixtures (fresh-install parity) ──
    def test_lifecycle_workflow_source_matches_fixture(self):
        src, fix = _load_lifecycle_source_workflow(), _load_lifecycle_fixture_workflow()
        self.assertEqual(
            _wf_edge_pairs(src), _wf_edge_pairs(fix),
            "edge-set source ≠ fixtures — fresh-install `_sync_workflows` sẽ lệch Desk-workflow")
        sr, fr = _wf_edge_roles(src), _wf_edge_roles(fix)
        for e in _wf_edge_pairs(src):
            self.assertEqual(
                "AssetCore Super Admin" in sr[e], "AssetCore Super Admin" in fr[e],
                f"cạnh {e}: phủ role 'AssetCore Super Admin' source ≠ fixtures")
        for e in _SURFACED_OOS_EDGES:  # 2 cạnh mới hiện diện trong CẢ 2 file
            self.assertIn(e, _wf_edge_pairs(src), f"cạnh SURFACE {e} vắng ở source")
            self.assertIn(e, _wf_edge_pairs(fix), f"cạnh SURFACE {e} vắng ở fixtures")

    # ── grounding: 8 state == enum (dedicated, cả source + fixtures) ───────────
    def test_lifecycle_workflow_states_match_enum(self):
        for tag, wf in (("source", _load_lifecycle_source_workflow()),
                        ("fixture", _load_lifecycle_fixture_workflow())):
            self.assertEqual(len(wf["states"]), 8, f"{tag}: phải 8 state")
            self.assertEqual({s["state"] for s in wf["states"]}, _CANONICAL_ASSET_STATES,
                             f"{tag}: state lệch AssetStatus enum")

    # ── admin-override regression — mọi cạnh source chứa 'AssetCore Super Admin' ─
    def test_lifecycle_source_every_edge_allows_super_admin(self):
        roles = _wf_edge_roles(_load_lifecycle_source_workflow())
        no_admin = sorted(e for e in roles if "AssetCore Super Admin" not in roles[e])
        self.assertEqual(no_admin, [],
                         f"cạnh thiếu 'AssetCore Super Admin' (admin-override vỡ): {no_admin}")

    # ── TC-00-WF-RECON-03 — helper is_valid_asset_transition phản ánh NEG-09 ───
    def test_is_valid_asset_transition_reflects_neg09(self):
        D = _AssetStatus.DECOMMISSIONED
        # (a) 3 cạnh NEG-09 → helper False (KHỚP guard sẽ ném InvalidAssetTransition).
        for s in (_AssetStatus.UNDER_MAINTENANCE, _AssetStatus.UNDER_REPAIR,
                  _AssetStatus.CALIBRATING):
            self.assertFalse(_lc_is_valid(s, D),
                             f"helper phải False cho NEG-09 ({s}→Decommissioned)")
        # (b) 2 cạnh programmatic-only → helper True (chặn ở IMM-14 gate DB-layer).
        self.assertTrue(_lc_is_valid(_AssetStatus.DRAFT, D))
        self.assertTrue(_lc_is_valid(_AssetStatus.COMMISSIONED, D))
        # (c) regression →Under Repair KHÔNG đổi (imm09.py:1309 + test_imm09.py:431).
        UR = _AssetStatus.UNDER_REPAIR
        self.assertTrue(_lc_is_valid(_AssetStatus.ACTIVE, UR))
        self.assertTrue(_lc_is_valid(_AssetStatus.UNDER_MAINTENANCE, UR))
        self.assertTrue(_lc_is_valid(_AssetStatus.OUT_OF_SERVICE, UR))
        self.assertFalse(_lc_is_valid(_AssetStatus.DRAFT, UR))
        # no-op / empty from_status vẫn True (asset mới chưa vào lifecycle).
        self.assertTrue(_lc_is_valid("", D))
        self.assertTrue(_lc_is_valid(UR, UR))


class TestGetAssetAllowedTransitions(unittest.TestCase):
    """CR-WF-00-LIFECYCLE-SURFACE — get_asset emit ``allowed_transitions`` (server-
    driven CTA, capability-filtered ``asset.write``). Mirror precedent
    ``firmware_allowed_transitions`` (api/imm00.py:2806): FE gate dropdown chuyển-
    trạng-thái CHỈ theo field này, KHÔNG hardcode bảng transition client-side.

    Bất-biến kiểm bằng live-asset qua HTTP-shaped call ``get_asset(name)``:
      - caller CÓ ``asset.write`` (AssetCore Super Admin, non-admin) → subset == helper.
      - caller CHỈ-đọc (Commissioning User, read=1/write=0) → ``[]`` (RED-first: chưa
        capability-filter sẽ trả full subset).
      - Decommissioned KHÔNG bao giờ ∈ list (carve-out IMM-14); terminal → ``[]``.
    """

    _WRITE_USER = "be_lc_surface_write@example.com"        # AssetCore Super Admin (write=1)
    _READONLY_USER = "be_lc_surface_readonly@example.com"  # Commissioning User (read=1/write=0)

    @classmethod
    def setUpClass(cls):
        from assetcore.services.shared import rbac
        frappe.set_user("Administrator")
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "Thiết bị Lifecycle Surface (CR-WF-00)",
            "description": "Category test allowed_transitions surface",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        for email, first, role in (
            (cls._WRITE_USER, "lc-surface-write", "AssetCore Super Admin"),
            (cls._READONLY_USER, "lc-surface-ro", "Commissioning User"),
        ):
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            u = frappe.get_doc({
                "doctype": "User", "email": email,
                "first_name": first, "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
            u.add_roles(role)
            rbac.invalidate_capabilities(email)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        from assetcore.services.shared import rbac
        frappe.set_user("Administrator")
        for email in (cls._WRITE_USER, cls._READONLY_USER):
            rbac.invalidate_capabilities(email)
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.delete_doc("AC Asset Category", cls.cat.name,
                          force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for name in self._created:
            _purge_asset(name)
        frappe.db.commit()

    def _make_asset(self, *, lifecycle: str) -> str:
        import uuid
        uniq = uuid.uuid4().hex[:8]
        doc = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"Máy siêu âm Philips EPIQ 7 {uniq}",
            "asset_category": self.cat.name,
            "manufacturer_sn": f"LCS-SN-{uniq}",
            "asset_code": f"LCS-ASSET-{uniq}",
            "lifecycle_status": lifecycle,
        })
        self._created.append(doc.name)
        return doc.name

    def _allowed_as(self, user: str, asset: str) -> list:
        from assetcore.api.imm00 import get_asset
        frappe.set_user(user)
        try:
            env = get_asset(asset)
        finally:
            frappe.set_user("Administrator")
        self.assertTrue(env.get("success"), f"get_asset không success: {env}")
        self.assertIn("allowed_transitions", env["data"],
                      "get_asset PHẢI emit field 'allowed_transitions' (server-driven CTA)")
        return env["data"]["allowed_transitions"]

    # ── TC-1: write user, Active → subset == helper (KHÔNG Decommissioned) ──────
    def test_get_asset_emits_allowed_transitions_matches_ssot_subset(self):
        asset = self._make_asset(lifecycle="Active")
        out = self._allowed_as(self._WRITE_USER, asset)
        self.assertEqual(out, _asset_allowed_transitions("Active"),
                         "get_asset emit ≠ helper (single-SSoT vỡ)")
        self.assertEqual(
            out, ["Calibrating", "Out of Service", "Under Maintenance", "Under Repair"])
        self.assertNotIn("Decommissioned", out)

    # ── TC-2: read-only user → [] (RED-first nếu chưa capability-filter) ────────
    def test_get_asset_allowed_transitions_empty_for_readonly_user(self):
        asset = self._make_asset(lifecycle="Active")
        out = self._allowed_as(self._READONLY_USER, asset)
        self.assertEqual(out, [],
                         "caller thiếu asset.write PHẢI nhận allowed_transitions == []")

    # ── TC-3: terminal Decommissioned → [] (dù caller có asset.write) ───────────
    def test_get_asset_allowed_transitions_empty_terminal(self):
        asset = self._make_asset(lifecycle="Decommissioned")
        out = self._allowed_as(self._WRITE_USER, asset)
        self.assertEqual(out, [], "asset Decommissioned (terminal) → []")


class TestNeg09GuardRaisesLive(unittest.TestCase):
    """TC-00-WF-RECON-03b — guard `transition_asset_status` ném NEG-09 KHỚP helper.

    Live-asset: chứng minh cụ thể helper (False) ⇄ guard (raise) nhất quán cho 3
    cạnh →Decommissioned từ Under Maintenance/Under Repair/Calibrating.
    """

    @classmethod
    def setUpClass(cls):
        import uuid
        frappe.set_user("Administrator")
        sfx = uuid.uuid4().hex[:8]
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"NEG09 Hô hấp {sfx}",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)
        cls.dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": f"NEG09 ICU {sfx}",
        }).insert(ignore_permissions=True)
        cls.loc = frappe.get_doc({
            "doctype": "AC Location",
            "location_name": f"NEG09 Phòng {sfx}",
            "location_type": "Room",
        }).insert(ignore_permissions=True)
        cls.sup = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": f"NEG09 NCC {sfx}",
            "supplier_group": "Manufacturer",
            "vendor_type": "Manufacturer",
            "country": "Vietnam",
            "is_active": 1,
        }).insert(ignore_permissions=True)
        cls.asset = _insert_asset_bypass_workflow({
            "doctype": "AC Asset",
            "asset_name": f"NEG09 Máy thở {sfx}",
            "asset_category": cls.cat.name,
            "department": cls.dept.name,
            "location": cls.loc.name,
            "supplier": cls.sup.name,
            "purchase_date": "2023-03-15",
            "gross_purchase_amount": 850_000_000,
            "in_service_date": "2023-03-20",
            "commissioning_date": "2023-03-20",
            "manufacturer_sn": f"NEG09-{sfx}",
            "medical_device_class": "Class III",
            "risk_classification": "Critical",
            "lifecycle_status": "Active",
        })
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        # asset đang Active (KHÔNG Decommissioned) → _purge_asset xoá sạch được.
        _purge_asset(cls.asset.name)
        for dt, name in [
            ("AC Location", cls.loc.name), ("AC Supplier", cls.sup.name),
            ("AC Department", cls.dept.name), ("AC Asset Category", cls.cat.name),
        ]:
            if frappe.db.exists(dt, name):
                frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_guard_raises_neg09_for_maintenance_repair_calibration(self):
        D = _AssetStatus.DECOMMISSIONED
        try:
            for state in (_AssetStatus.UNDER_MAINTENANCE, _AssetStatus.UNDER_REPAIR,
                          _AssetStatus.CALIBRATING):
                frappe.db.set_value("AC Asset", self.asset.name, "lifecycle_status",
                                    state, update_modified=False)
                with self.assertRaises(_LcInvalidTransition) as ctx:
                    _lc_transition(self.asset.name, D, actor="Administrator")
                self.assertIn("NEG-09", str(ctx.exception),
                              f"{state}→Decommissioned phải ném InvalidAssetTransition NEG-09")
                # guard ⇄ helper nhất quán: cùng 1 cạnh helper trả False.
                self.assertFalse(_lc_is_valid(state, D),
                                 f"helper mâu thuẫn guard tại {state}→Decommissioned")
        finally:
            # đưa về Active để asset còn ở trạng thái xoá-được (teardown _purge_asset).
            frappe.db.set_value("AC Asset", self.asset.name, "lifecycle_status",
                                _AssetStatus.ACTIVE, update_modified=False)


def run_all():
    """Convenience runner for bench console."""
    suite = unittest.TestLoader().loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
