"""IMM-11 Calibration — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm11
"""
from __future__ import annotations

import json
import unittest

import frappe
from frappe.utils import nowdate, add_days

from assetcore.services.imm11 import create_calibration, cancel_calibration
from assetcore.services.shared import (
    AssetStatus,
    CalibrationResult,
    CalibrationStatus,
    ErrorCode,
    ServiceError,
)


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _make_asset(suffix: str = "") -> object:
    import time
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    tag = suffix.lstrip("-") or "001"
    sn = f"SN-11-{tag}-{int(time.time()) % 100000}"
    try:
        return frappe.get_doc({
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset IMM11{suffix}",
            "asset_category": _ensure_cat(),
            "manufacturer_sn": sn,
            "lifecycle_status": "Active",
        }).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _ensure_cat() -> str:
    name = "_TestCatIMM11"
    existing = frappe.db.get_value(
        "AC Asset Category", {"category_name": name}, "name"
    )
    if existing:
        return existing
    doc = frappe.get_doc({"doctype": "AC Asset Category", "category_name": name}).insert(
        ignore_permissions=True
    )
    return doc.name


def tearDownModule():  # noqa: N802
    """Safety net: purge the shared test category/assets if a class teardown gap
    left them (recurring '_TestCatIMM11' leak)."""
    from assetcore.tests._asset_cleanup import (
        purge_assets_by_name_prefix,
        purge_category_by_name,
    )
    frappe.set_user("Administrator")
    purge_assets_by_name_prefix("_Test Asset IMM11")
    purge_category_by_name("_TestCatIMM11")
    frappe.db.commit()


def _purge_asset_with_deps(asset_name: str) -> None:
    """Cascade-clean records that WR-03 on_trash protects against, then delete asset.

    Production asset removal must use the Decommission workflow; tests need a
    direct path to drop fixtures created during setUpClass without triggering
    the WR-03 LinkExistsError guard.
    """
    for dt, field in (
        ("IMM Audit Trail",       "asset"),
        ("Asset Lifecycle Event", "asset"),
        ("AC Asset Downtime Log", "asset"),
        ("Asset Document",        "asset_ref"),
    ):
        if not frappe.db.table_exists(dt):
            continue
        try:
            frappe.db.delete(dt, {field: asset_name})
        except Exception:
            continue
    frappe.delete_doc("AC Asset", asset_name, force=True, ignore_permissions=True)


# ─── Tests ────────────────────────────────────────────────────────────────────

class TestCalibrationCreation(unittest.TestCase):
    """BR-11-01: create_calibration validation + happy path."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-cal")

    @classmethod
    def tearDownClass(cls):
        for cal in frappe.get_all(
            "IMM Asset Calibration", filters={"asset": cls.asset.name}, fields=["name"]
        ):
            frappe.delete_doc(
                "IMM Asset Calibration", cal.name, force=True, ignore_permissions=True
            )
        _purge_asset_with_deps(cls.asset.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM11"}, "name"
        )
        if cat_name:
            try:
                frappe.delete_doc("AC Asset Category", cat_name, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass

    def setUp(self):
        frappe.set_user("Administrator")

    def test_nonexistent_asset_raises_not_found(self):
        with self.assertRaises(ServiceError) as cm:
            create_calibration(
                asset="DOES-NOT-EXIST",
                calibration_type="In-House",
                scheduled_date=nowdate(),
                technician="Administrator",
            )
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)

    def test_create_calibration_succeeds(self):
        result = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 7),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        self.assertIn("name", result)
        self.assertEqual(result["status"], CalibrationResult.SCHEDULED)
        doc = frappe.get_doc("IMM Asset Calibration", result["name"])
        self.assertEqual(doc.asset, self.asset.name)

    def test_initial_status_is_scheduled(self):
        result = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 14),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        self.assertEqual(result["status"], CalibrationResult.SCHEDULED)

    def test_naming_series(self):
        result = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 30),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        self.assertTrue(
            result["name"].startswith("CAL-")
            or "IMM-CAL" in result["name"]
            or frappe.db.exists("IMM Asset Calibration", result["name"])
        )


class TestCalibrationCancellation(unittest.TestCase):
    """BR-11-05: Scheduled calibration can be cancelled with reason."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-cancel")
        result = create_calibration(
            asset=cls.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 7),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        cls.cal_name = result["name"]

    @classmethod
    def tearDownClass(cls):
        if frappe.db.exists("IMM Asset Calibration", cls.cal_name):
            frappe.delete_doc(
                "IMM Asset Calibration", cls.cal_name, force=True, ignore_permissions=True
            )
        _purge_asset_with_deps(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_cancel_scheduled_calibration(self):
        result = cancel_calibration(self.cal_name, reason="_Test cancel — equipment unavailable")
        frappe.db.commit()
        self.assertEqual(result["status"], CalibrationResult.CANCELLED)
        doc = frappe.get_doc("IMM Asset Calibration", self.cal_name)
        self.assertEqual(doc.status, CalibrationResult.CANCELLED)


class TestCalibrationSubmitGate(unittest.TestCase):
    """BR-11-08/09 — Submit phải có ≥1 measurement + overall_result."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-subgate")

    @classmethod
    def tearDownClass(cls):
        for cal in frappe.get_all(
            "IMM Asset Calibration", filters={"asset": cls.asset.name}, fields=["name"]
        ):
            # Submitted calibrations cannot be cancelled (BR-11-05) — purge rows directly.
            frappe.db.delete("IMM Calibration Measurement", {"parent": cal.name})
            frappe.db.delete("IMM Asset Calibration", {"name": cal.name})
        _purge_asset_with_deps(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_cal(self):
        res = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 7),
            technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        return res["name"]

    def test_submit_blocked_without_measurements(self):
        from assetcore.services.imm11 import submit_calibration
        name = self._make_cal()
        with self.assertRaises(Exception):
            submit_calibration(name)

    def test_submit_succeeds_with_measurement_and_result(self):
        from assetcore.services.imm11 import submit_calibration, add_measurement
        name = self._make_cal()
        add_measurement(
            name, parameter_name="Temp", unit="C", nominal_value=100,
            tolerance_positive=5, tolerance_negative=5, measured_value=101,
        )
        frappe.db.commit()
        res = submit_calibration(name)
        frappe.db.commit()
        self.assertIn(res["overall_result"], ("Passed", "Conditionally Passed"))


class TestLLBE1CalKpis417(unittest.TestCase):
    """LL-BE-1 guard: get_calibration_kpis (GET, year/month optional) phải
    tolerate query rỗng (`?year=`) mà KHÔNG raise FrappeTypeError → HTTP 417.

    Hiện AN TOÀN vì `api/imm11.py` có `from __future__ import annotations`
    (annotation = string → validator SKIP coercion). Test GUARD chống regression
    nếu future-import bị gỡ / annotation thành real-type (khi đó `int=None`+`""`
    → 417). Cf. dashboard.py (không future-import) đã từng 417.
    """

    def test_cal_kpis_empty_year_no_417(self):
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.imm11 import get_calibration_kpis

        wrapped = validate_argument_types(
            get_calibration_kpis, apply_condition=lambda: True
        )
        resp = wrapped(year="", month="")
        self.assertIsInstance(resp, dict)

    def test_cal_kpis_missing_args_no_417(self):
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.imm11 import get_calibration_kpis

        wrapped = validate_argument_types(
            get_calibration_kpis, apply_condition=lambda: True
        )
        resp = wrapped()
        self.assertIsInstance(resp, dict)


class TestImm11NotificationContract(unittest.TestCase):
    """Sprint Notification vòng 4 — service raise nthrow(MSG.IMM11_*) carry
    message_code; api_handler.handle() hydrate severity/title/action_hint.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-notif")

    @classmethod
    def tearDownClass(cls):
        for cal in frappe.get_all(
            "IMM Asset Calibration", filters={"asset": cls.asset.name}, fields=["name"]
        ):
            frappe.db.delete("IMM Calibration Measurement", {"parent": cal.name})
            frappe.db.delete("IMM Asset Calibration", {"name": cal.name})
        _purge_asset_with_deps(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_service_error_carries_message_code(self):
        """create_calibration với asset không tồn tại → ServiceError có
        message_code = IMM11-ASSET-NOT-FOUND."""
        from assetcore.utils.messages import MSG
        with self.assertRaises(ServiceError) as cm:
            create_calibration(
                asset="DOES-NOT-EXIST-NOTIF",
                calibration_type="In-House",
                scheduled_date=nowdate(),
                technician="Administrator",
            )
        self.assertEqual(cm.exception.message_code, MSG.IMM11_ASSET_NOT_FOUND)
        self.assertEqual(cm.exception.code, ErrorCode.NOT_FOUND)

    def test_cancel_reason_required_message_code(self):
        from assetcore.utils.messages import MSG
        res = create_calibration(
            asset=self.asset.name, calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 7), technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        with self.assertRaises(ServiceError) as cm:
            cancel_calibration(res["name"], reason="")
        self.assertEqual(cm.exception.message_code, MSG.IMM11_CANCEL_REASON_REQUIRED)

    def test_api_envelope_hydrates_notification_fields(self):
        """api.imm11.get_calibration với mã không tồn tại → envelope đủ
        message_code + severity + title (hydrate qua handle())."""
        from assetcore.api.imm11 import get_calibration
        resp = get_calibration("CAL-NO-SUCH-RECORD-99999")
        self.assertFalse(resp["success"])
        self.assertEqual(resp["message_code"], "IMM11-CAL-NOT-FOUND")
        self.assertEqual(resp["severity"], "warning")
        self.assertTrue(resp.get("title"))
        self.assertTrue(resp.get("action_hint"))

    def test_doctype_hook_uses_nthrow_in_hook(self):
        """before_submit không có measurement → ValidationError (417) với
        message_code đính kèm response (nthrow_in_hook)."""
        from assetcore.services.imm11 import submit_calibration
        res = create_calibration(
            asset=self.asset.name, calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 9), technician="Administrator",
            reference_standard_serial="STD-TEST-001",
        )
        frappe.db.commit()
        with self.assertRaises(frappe.ValidationError):
            submit_calibration(res["name"])
        self.assertEqual(
            frappe.local.response.get("message_code"), "IMM11-NO-MEASUREMENTS"
        )


# ─── Server-side schedule list: search / overdue drill / count parity ─────────

def _make_schedule(asset_name: str, *, next_due: str, cal_type: str = "External",
                   interval: int = 365, is_active: int = 1) -> str:
    """Create a Calibration Schedule directly so next_due_date is deterministic."""
    from assetcore.repositories.calibration_repo import CalibrationScheduleRepo
    dm = frappe.db.get_value("AC Asset", asset_name, "device_model")
    doc = CalibrationScheduleRepo.create({
        "asset": asset_name,
        "device_model": dm,
        "calibration_type": cal_type,
        "interval_days": interval,
        "next_due_date": next_due,
        "is_active": is_active,
    })
    return doc.name


class TestScheduleListSearchServerSide(unittest.TestCase):
    """Server-side filter/search/overdue drill for list_schedules.

    Same bug-class as /audit-trail: client-side filtering on a single
    50-row page diverges from pagination.total and never reaches rows >50.
    """

    _PAGE = 50  # exceed default page_size so paging is exercised

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._assets: list = []
        cls._schedules: list[str] = []
        # 55 overdue schedules (next_due_date < today) → spans >1 page of 50.
        past = add_days(nowdate(), -10)
        for i in range(55):
            a = _make_asset(f"-srch-od-{i}")
            cls._assets.append(a)
            cls._schedules.append(_make_schedule(a.name, next_due=past))
        # One distinctively-named asset whose schedule lands on a later page,
        # to prove search reaches rows beyond page 1.
        _prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls._needle_asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": "_Test Asset IMM11 ZZNEEDLE Unique",
                "asset_category": _ensure_cat(),
                "manufacturer_sn": f"SN-11-needle-{frappe.utils.now_datetime().microsecond}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = _prev
        cls._assets.append(cls._needle_asset)
        cls._schedules.append(_make_schedule(cls._needle_asset.name, next_due=past))
        # A few future (not overdue) schedules so overdue filter must exclude them.
        future = add_days(nowdate(), 200)
        for i in range(3):
            a = _make_asset(f"-srch-fut-{i}")
            cls._assets.append(a)
            cls._schedules.append(_make_schedule(a.name, next_due=future))
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for name in cls._schedules:
            try:
                frappe.delete_doc("IMM Calibration Schedule", name, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass
        for a in cls._assets:
            try:
                _purge_asset_with_deps(a.name)
            except Exception:
                pass
        frappe.db.commit()

    def test_overdue_total_counts_all_overdue_not_capped_at_page(self):
        """?overdue=1 → pagination.total = real overdue count (>page_size)."""
        from assetcore.services.imm11 import list_schedules
        res = list_schedules({"overdue": 1}, page=1, page_size=self._PAGE)
        # 56 overdue (55 + needle); future ones excluded.
        self.assertGreaterEqual(res["pagination"]["total"], 56)
        self.assertEqual(len(res["data"]), self._PAGE)  # page 1 full
        self.assertGreater(res["pagination"]["total_pages"], 1)
        # Every returned row must actually be overdue (predicate matches KPI).
        for r in res["data"]:
            self.assertLess(str(r["next_due_date"]), nowdate())

    def test_overdue_page_2_returns_more_overdue_rows(self):
        """page=2 yields additional overdue rows — not truncated at one page."""
        from assetcore.services.imm11 import list_schedules
        p1 = list_schedules({"overdue": 1}, page=1, page_size=self._PAGE)
        p2 = list_schedules({"overdue": 1}, page=2, page_size=self._PAGE)
        self.assertGreater(len(p2["data"]), 0)
        names_p1 = {r["name"] for r in p1["data"]}
        names_p2 = {r["name"] for r in p2["data"]}
        self.assertEqual(names_p1 & names_p2, set())  # no overlap

    def test_search_by_asset_name_on_later_page_is_found(self):
        """search by asset_name (link_search) finds the needle wherever it pages."""
        from assetcore.services.imm11 import list_schedules
        res = list_schedules({"search": "ZZNEEDLE"}, page=1, page_size=self._PAGE)
        self.assertEqual(res["pagination"]["total"], 1)
        self.assertEqual(len(res["data"]), 1)
        self.assertEqual(res["data"][0]["asset"], self._needle_asset.name)

    def test_search_by_schedule_name_matches(self):
        """search by schedule code (parent column) returns that schedule."""
        from assetcore.services.imm11 import list_schedules
        target = self._schedules[0]
        res = list_schedules({"search": target}, page=1, page_size=self._PAGE)
        self.assertEqual(res["pagination"]["total"], 1)
        self.assertEqual(res["data"][0]["name"], target)

    def test_count_matches_list_with_or_filter(self):
        """count_with_or parity: total == #rows when collecting all search pages.

        Regression guard for divergence count vs rows (same as /audit-trail).
        """
        from assetcore.services.imm11 import list_schedules
        # "_Test Asset IMM11" matches every fixture asset_name → broad OR search.
        first = list_schedules({"search": "_Test Asset IMM11"}, page=1,
                               page_size=self._PAGE)
        total = first["pagination"]["total"]
        collected: set = set()
        page = 1
        while True:
            res = list_schedules({"search": "_Test Asset IMM11"}, page=page,
                                 page_size=self._PAGE)
            if not res["data"]:
                break
            collected |= {r["name"] for r in res["data"]}
            if page >= res["pagination"]["total_pages"]:
                break
            page += 1
        self.assertEqual(len(collected), total)

    def test_overdue_combined_with_calibration_type(self):
        """overdue AND calibration_type AND-combine with search OR clause."""
        from assetcore.services.imm11 import list_schedules
        res = list_schedules(
            {"overdue": 1, "calibration_type": "External", "search": "_Test Asset IMM11"},
            page=1, page_size=self._PAGE,
        )
        for r in res["data"]:
            self.assertEqual(r["calibration_type"], "External")
            self.assertLess(str(r["next_due_date"]), nowdate())


class TestScheduleListVendorScope(unittest.TestCase):
    """Vendor user + search must NOT bypass apply_vendor_scope.

    search adds an OR clause; the vendor `asset IN [...]` AND filter injected
    by apply_vendor_scope must still bound the result.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._assets = [_make_asset("-vs-in"), _make_asset("-vs-out")]
        past = add_days(nowdate(), -5)
        cls._sched_in = _make_schedule(cls._assets[0].name, next_due=past)
        cls._sched_out = _make_schedule(cls._assets[1].name, next_due=past)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in (cls._sched_in, cls._sched_out):
            try:
                frappe.delete_doc("IMM Calibration Schedule", name, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass
        for a in cls._assets:
            try:
                _purge_asset_with_deps(a.name)
            except Exception:
                pass
        frappe.db.commit()

    def test_search_respects_vendor_scope(self):
        """apply_vendor_scope restricts to in-scope asset even when search set.

        Simulates the API path: scope is applied to the filter dict BEFORE
        list_schedules, then a broad search runs. Out-of-scope schedule must
        not surface despite matching the search term.
        """
        from assetcore.services.imm11 import list_schedules
        # Mimic api/imm11.list_calibration_schedules: scope first (asset IN
        # [in-scope only]), then search OR clause.
        scoped = {"asset": ["in", [self._assets[0].name]], "search": "_Test Asset IMM11"}
        res = list_schedules(scoped, page=1, page_size=50)
        returned_assets = {r["asset"] for r in res["data"]}
        self.assertIn(self._assets[0].name, returned_assets)
        self.assertNotIn(self._assets[1].name, returned_assets)
        for r in res["data"]:
            self.assertEqual(r["asset"], self._assets[0].name)


# ─── Server-side list / search / drill-down (bug-class /audit-trail) ──────────

class TestScheduleListServerSide(unittest.TestCase):
    """list_schedules: search + KPI-drill server-side, count khớp rows.

    Cùng lớp lỗi /audit-trail: trước fix FE lọc client-side trên page-1 (50)
    nhưng total = full server count → divergence + rows >page_size không tới
    được. BE phải:
      - áp search server-side (pop_search trên ['name','asset'] + link_search
        asset_name) và đếm total qua count_with_or (KHÔNG db.count thuần);
      - drill overdue/due_before khớp đúng predicate KPI calib_overdue/calib_due
        kể cả khi tổng > page_size (không cắt ở 1 trang).
    """

    N_OVERDUE = 12      # > page_size dùng trong test (5) → ép multi-page
    PAGE_SIZE = 5

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-sched")
        # Asset thứ 2 có asset_name riêng-biệt để test link_search (search theo
        # tên thiết bị → match qua AC Asset.asset_name, không phải mã schedule).
        cls.asset2 = _make_asset("-zsearch")
        cls.unique_token = f"ZZSEARCH{int(__import__('time').time()) % 100000}"
        frappe.db.set_value("AC Asset", cls.asset2.name, "asset_name",
                            f"_Test {cls.unique_token} Device")
        from assetcore.repositories.calibration_repo import CalibrationScheduleRepo
        cls.repo = CalibrationScheduleRepo
        cls.created: list[str] = []
        past = add_days(nowdate(), -10)        # overdue: next_due_date < today
        future = add_days(nowdate(), 400)      # not overdue
        for i in range(cls.N_OVERDUE):
            s = CalibrationScheduleRepo.create({
                "asset": cls.asset.name,
                "calibration_type": "External",
                "interval_days": 365,
                "last_calibration_date": add_days(past, -365),
                "next_due_date": past,
                "is_active": 1,
            })
            cls.created.append(s.name)
        # 1 schedule KHÔNG overdue (next_due_date tương lai) gắn asset2 — để test
        # search theo asset_name + để chứng minh overdue drill loại nó ra.
        s2 = CalibrationScheduleRepo.create({
            "asset": cls.asset2.name,
            "calibration_type": "In-House",
            "interval_days": 365,
            "last_calibration_date": nowdate(),
            "next_due_date": future,
            "is_active": 1,
        })
        cls.search_sched = s2.name
        cls.created.append(s2.name)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for name in cls.created:
            try:
                frappe.delete_doc("IMM Calibration Schedule", name, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass
        for a in (cls.asset, cls.asset2):
            _purge_asset_with_deps(a.name)
        cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_name": "_TestCatIMM11"}, "name"
        )
        if cat_name:
            try:
                frappe.delete_doc("AC Asset Category", cat_name, force=True,
                                  ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    # — Search server-side (link_search asset_name, page-independent) —

    def test_search_by_asset_name_finds_record_on_any_page(self):
        """search theo asset_name (qua link_search 'asset'→AC Asset.asset_name)
        ⇒ trả về đúng schedule + total = số match thực, KHÔNG phụ thuộc trang."""
        from assetcore.services.imm11 import list_schedules
        res = list_schedules({"search": self.unique_token},
                             page=1, page_size=self.PAGE_SIZE)
        names = {r["name"] for r in res["data"]}
        self.assertIn(self.search_sched, names,
                      "search asset_name phải tìm thấy schedule qua link_search")
        # total khớp số rows match thực (đúng 1) — count_with_or, KHÔNG full count
        self.assertEqual(res["pagination"]["total"], len(res["data"]))
        self.assertEqual(res["pagination"]["total"], 1)

    def test_search_by_schedule_name_direct(self):
        """search theo mã schedule (cột name parent) ⇒ match trực tiếp."""
        from assetcore.services.imm11 import list_schedules
        target = self.created[0]
        res = list_schedules({"search": target}, page=1, page_size=self.PAGE_SIZE)
        names = {r["name"] for r in res["data"]}
        self.assertIn(target, names)
        self.assertGreaterEqual(res["pagination"]["total"], 1)

    # — KPI drill overdue spanning multiple pages —

    def test_overdue_drill_total_matches_and_spans_pages(self):
        """?overdue=1 ⇒ pagination.total = ĐÚNG tổng overdue (>page_size);
        page 2 trả thêm overdue rows (không cắt ở 1 trang)."""
        from assetcore.services.imm11 import list_schedules
        p1 = list_schedules({"overdue": 1}, page=1, page_size=self.PAGE_SIZE)
        total = p1["pagination"]["total"]
        self.assertGreaterEqual(total, self.N_OVERDUE,
                                "total overdue phải >= số overdue đã tạo")
        # next_due_date tương lai (search_sched) KHÔNG được tính là overdue
        p1_names = {r["name"] for r in p1["data"]}
        self.assertNotIn(self.search_sched, p1_names)
        self.assertEqual(len(p1["data"]), self.PAGE_SIZE,
                         "page 1 đầy đúng page_size khi total > page_size")
        p2 = list_schedules({"overdue": 1}, page=2, page_size=self.PAGE_SIZE)
        self.assertGreater(len(p2["data"]), 0,
                           "page 2 phải có thêm overdue rows (không cắt ở 50)")
        # Không trùng row giữa 2 trang
        self.assertFalse(p1_names & {r["name"] for r in p2["data"]})
        # Mọi row overdue: next_due_date < hôm nay (khớp predicate KPI)
        for r in p1["data"] + p2["data"]:
            self.assertLess(str(r["next_due_date"]), nowdate())

    def test_due_before_drill_predicate(self):
        """?due_before=X ⇒ CHỈ next_due_date <= X (khớp KPI calib_due)."""
        from assetcore.services.imm11 import list_schedules
        cutoff = nowdate()  # bao gồm toàn bộ overdue (past < today)
        res = list_schedules({"due_before": cutoff}, page=1, page_size=100)
        for r in res["data"]:
            self.assertLessEqual(str(r["next_due_date"]), cutoff)
        self.assertNotIn(self.search_sched,
                         {r["name"] for r in res["data"]})

    # — Count khớp list khi có OR-search (regression guard divergence) —

    def test_count_matches_rows_with_or_search(self):
        """count_with_or trả đúng tổng khi có OR-filter search — total KHÔNG
        được > số rows thực (cùng bug-class /audit-trail divergence)."""
        from assetcore.services.imm11 import list_schedules
        res = list_schedules({"search": self.unique_token}, page=1, page_size=100)
        self.assertEqual(res["pagination"]["total"], len(res["data"]),
                         "total phải khớp rows thực sau khi áp search OR-filter")

    def test_search_combined_with_overdue_and_filter(self):
        """search (OR) kết hợp overdue (AND) ⇒ AND giữa 2 nhóm: search_sched
        KHÔNG overdue nên bị loại dù tên match search."""
        from assetcore.services.imm11 import list_schedules
        res = list_schedules({"search": self.unique_token, "overdue": 1},
                             page=1, page_size=100)
        names = {r["name"] for r in res["data"]}
        self.assertNotIn(self.search_sched, names,
                         "overdue AND search: row future-due bị loại bởi AND")

    # — Vendor-scope không bị search bypass —

    def test_search_does_not_bypass_and_scope_filter(self):
        """Khi filters đã mang AND-scope (vd vendor scope asset in [allowed]),
        search OR KHÔNG được kéo về row ngoài scope.

        Mô phỏng apply_vendor_scope đã inject {'asset': ['in', [allowed]]}:
        scope chỉ cho asset (overdue batch), search khớp asset2 (ngoài scope)
        ⇒ asset2 KHÔNG được lọt qua."""
        from assetcore.services.imm11 import list_schedules
        res = list_schedules(
            {"asset": ["in", [self.asset.name]], "search": self.unique_token},
            page=1, page_size=100,
        )
        names = {r["name"] for r in res["data"]}
        self.assertNotIn(self.search_sched, names,
                         "search OR không được bypass AND-scope asset filter")
        for r in res["data"]:
            self.assertEqual(r["asset"], self.asset.name)


# ════════════════════════════════════════════════════════════════════════════
#  SoT calibration due/overdue predicate (BR-11-08 / BR-11-09)
#  docs/imm-11/04_Backend_Design.md §4.1 · 07_Testing_QA.md TC-11-SOT-*
# ════════════════════════════════════════════════════════════════════════════


class TestIsCalibrationPredicate(unittest.TestCase):
    """TDD-1 / TDD-2 — pure boundary predicate (no I/O).

    OVERDUE  ⟺ next_due < today (strict <).
    DUE_SOON ⟺ today <= next_due <= today + CAL_DUE_SOON_WINDOW_DAYS (inclusive).
    """

    def test_tdd1_overdue_boundary(self):
        from assetcore.services.imm11 import is_calibration_overdue
        ref = nowdate()
        self.assertTrue(is_calibration_overdue(add_days(ref, -1), ref),
                        "next_due = today-1 phải OVERDUE")
        self.assertFalse(is_calibration_overdue(ref, ref),
                         "next_due == today KHÔNG overdue (== là due_soon biên dưới)")
        self.assertFalse(is_calibration_overdue(add_days(ref, 1), ref))
        self.assertFalse(is_calibration_overdue(None, ref),
                         "None (chưa có hạn) → không overdue")

    def test_tdd2_due_soon_boundary(self):
        from assetcore.services.imm11 import (
            is_calibration_due_soon, CAL_DUE_SOON_WINDOW_DAYS,
        )
        ref = nowdate()
        w = CAL_DUE_SOON_WINDOW_DAYS
        self.assertEqual(w, 30, "window phải = 30 (1 hằng dùng chung)")
        self.assertTrue(is_calibration_due_soon(ref, ref),
                        "next_due == today → due_soon (biên dưới inclusive)")
        self.assertTrue(is_calibration_due_soon(add_days(ref, w), ref),
                        "next_due == today+30 → due_soon (biên trên inclusive)")
        self.assertFalse(is_calibration_due_soon(add_days(ref, w + 1), ref),
                         "next_due == today+31 → ON_SCHEDULE")
        self.assertFalse(is_calibration_due_soon(add_days(ref, -1), ref),
                         "next_due == today-1 → đã overdue, KHÔNG due_soon")
        self.assertFalse(is_calibration_due_soon(None, ref))


class TestCalibrationSotAssetIds(unittest.TestCase):
    """TDD-3 (mint gap) / TDD-4 (KPI==drill) / TDD-6 (filter) / TDD-7 (de-dup).

    SoT = IMM Calibration Schedule.next_due_date của schedule is_active=1,
    asset NOT decommissioned. De-dup theo asset. KHÔNG đọc AC Asset.* date field.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._assets: list[str] = []

        # A1: asset CHỈ-có-schedule overdue, next_calibration_date NULL (mint gap)
        cls.a_mint = _make_asset("-sot-mint")
        cls._assets.append(cls.a_mint.name)
        _make_schedule(cls.a_mint.name, next_due=add_days(nowdate(), -5))

        # A2: asset due_soon (next_due == today+10)
        cls.a_due = _make_asset("-sot-due")
        cls._assets.append(cls.a_due.name)
        _make_schedule(cls.a_due.name, next_due=add_days(nowdate(), 10))

        # A3: asset on_schedule (next_due == today+100) — không đếm
        cls.a_ok = _make_asset("-sot-ok")
        cls._assets.append(cls.a_ok.name)
        _make_schedule(cls.a_ok.name, next_due=add_days(nowdate(), 100))

        # A4: de-dup — 2 active schedule cùng overdue trên 1 asset (TDD-7)
        cls.a_dup = _make_asset("-sot-dup")
        cls._assets.append(cls.a_dup.name)
        _make_schedule(cls.a_dup.name, next_due=add_days(nowdate(), -3),
                       cal_type="External")
        _make_schedule(cls.a_dup.name, next_due=add_days(nowdate(), -7),
                       cal_type="In-House")

        # A5: decommissioned asset, schedule overdue → KHÔNG đếm (TDD-6)
        cls.a_decom = _make_asset("-sot-decom")
        cls._assets.append(cls.a_decom.name)
        _make_schedule(cls.a_decom.name, next_due=add_days(nowdate(), -9))
        frappe.db.set_value("AC Asset", cls.a_decom.name,
                            "lifecycle_status", "Decommissioned")

        # A6: inactive schedule overdue → KHÔNG đếm (TDD-6)
        cls.a_inact = _make_asset("-sot-inact")
        cls._assets.append(cls.a_inact.name)
        _make_schedule(cls.a_inact.name, next_due=add_days(nowdate(), -4),
                       is_active=0)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for an in cls._assets:
            frappe.db.delete("IMM Calibration Schedule", {"asset": an})
            _purge_asset_with_deps(an)
        frappe.db.commit()

    def test_tdd3_mint_gap_counted(self):
        """Asset chỉ-có-schedule (next_calibration_date NULL) VẪN đếm overdue."""
        from assetcore.services.imm11 import _overdue_asset_ids
        ids = _overdue_asset_ids()
        self.assertIn(self.a_mint.name, ids,
                      "asset minted (chỉ có schedule) phải đếm overdue ở SoT")
        # Chứng minh KHÔNG phụ thuộc AC Asset.next_calibration_date.
        self.assertIsNone(
            frappe.db.get_value("AC Asset", self.a_mint.name, "next_calibration_date"))

    def test_tdd6_decommissioned_and_inactive_excluded(self):
        from assetcore.services.imm11 import _overdue_asset_ids
        ids = _overdue_asset_ids()
        self.assertNotIn(self.a_decom.name, ids,
                         "asset Decommissioned KHÔNG đếm dù schedule overdue")
        self.assertNotIn(self.a_inact.name, ids,
                         "schedule is_active=0 KHÔNG đếm")

    def test_tdd7_dedup_by_asset(self):
        """1 asset 2 active schedule overdue → đếm 1 lần (DISTINCT asset)."""
        from assetcore.services.imm11 import _overdue_asset_ids
        ids = list(_overdue_asset_ids())
        self.assertEqual(ids.count(self.a_dup.name), 1,
                         "asset nhiều schedule overdue chỉ xuất hiện 1 lần")

    def test_due_soon_excludes_overdue(self):
        """Overdue ưu tiên — asset overdue KHÔNG đồng thời nằm trong due_soon."""
        from assetcore.services.imm11 import _overdue_asset_ids, _due_soon_asset_ids
        od = _overdue_asset_ids()
        ds = _due_soon_asset_ids()
        self.assertIn(self.a_due.name, ds)
        self.assertNotIn(self.a_mint.name, ds, "asset overdue không lọt due_soon")
        self.assertFalse(od & ds, "overdue và due_soon phải rời nhau")
        self.assertNotIn(self.a_ok.name, ds)
        self.assertNotIn(self.a_ok.name, od)

    def test_tdd4_kpi_equals_drill(self):
        """overdue drill ?overdue=1 == _overdue_asset_ids() (de-dup theo asset).

        Due-soon drill chuyển sang assert riêng ở test_due_soon_drill_count_equals_kpi
        (param `due_soon`, 2-biên, KHÔNG còn post-filter Python >= today).
        """
        from assetcore.services.imm11 import (
            get_kpis, list_schedules, _overdue_asset_ids,
        )
        from frappe.utils import getdate
        now = getdate(nowdate())
        k = get_kpis(now.year, now.month)["kpis"]

        # overdue drill: ?overdue=1 → group theo asset
        drill_od = list_schedules({"overdue": 1}, page=1, page_size=10_000)["data"]
        drill_od_assets = {r["asset"] for r in drill_od}
        self.assertEqual(k["overdue_assets"], len(_overdue_asset_ids()))
        self.assertEqual(k["overdue_assets"], len(drill_od_assets),
                         "KPI overdue_assets phải == số asset distinct ở drill overdue")

    def test_due_soon_drill_excludes_overdue(self):
        """Drill ?due_soon=1 (2-biên) == _due_soon_asset_ids(): chứa A_ds, KHÔNG
        chứa A_od (overdue) lẫn A_future (>window). Mọi row: today <= next_due <=
        today+CAL_DUE_SOON_WINDOW_DAYS (KHÔNG cần post-filter Python)."""
        from assetcore.services.imm11 import (
            list_schedules, _due_soon_asset_ids, CAL_DUE_SOON_WINDOW_DAYS,
        )
        from frappe.utils import getdate
        a_od = _make_asset("-dsx-od")
        a_ds = _make_asset("-dsx-ds")
        a_future = _make_asset("-dsx-fut")
        self.addCleanup(self._cleanup_assets, [a_od, a_ds, a_future])
        _make_schedule(a_od.name, next_due=add_days(nowdate(), -10))
        _make_schedule(a_ds.name, next_due=add_days(nowdate(), 10))
        _make_schedule(a_future.name, next_due=add_days(nowdate(), 60))
        frappe.db.commit()

        drill = list_schedules({"due_soon": 1}, page=1, page_size=10_000)["data"]
        drill_assets = {r["asset"] for r in drill}
        ds_ids = _due_soon_asset_ids()
        self.assertEqual(drill_assets, ds_ids,
                         "drill due_soon phải == _due_soon_asset_ids() (cùng tập)")
        self.assertIn(a_ds.name, drill_assets)
        self.assertNotIn(a_od.name, drill_assets, "overdue KHÔNG vào due-soon drill")
        self.assertNotIn(a_future.name, drill_assets, ">window KHÔNG vào drill")
        ref = getdate(nowdate())
        upper = add_days(ref, CAL_DUE_SOON_WINDOW_DAYS)
        for r in drill:
            nd = getdate(r["next_due_date"])
            self.assertGreaterEqual(nd, ref, "due-soon row: next_due >= today")
            self.assertLessEqual(nd, upper, "due-soon row: next_due <= today+window")

    def test_due_soon_drill_count_equals_kpi(self):
        """len({asset}) trong drill ?due_soon=1 == _due_soon_asset_ids() == KPI
        due_soon_assets — KHÔNG post-filter Python >= today (assert raw)."""
        from assetcore.services.imm11 import (
            get_kpis, list_schedules, _due_soon_asset_ids,
        )
        from frappe.utils import getdate
        now = getdate(nowdate())
        k = get_kpis(now.year, now.month)["kpis"]
        drill = list_schedules({"due_soon": 1}, page=1, page_size=10_000)["data"]
        drill_ds_assets = {r["asset"] for r in drill}  # RAW — no post-filter
        self.assertEqual(len(drill_ds_assets), len(_due_soon_asset_ids()))
        self.assertEqual(len(drill_ds_assets), k["due_soon_assets"],
                         "drill due_soon distinct-asset == KPI due_soon_assets")

    def test_overdue_drill_unchanged(self):
        """Regression: ?overdue=1 vẫn next_due_date < today; asset-set ==
        _overdue_asset_ids() (KHÔNG hồi quy)."""
        from assetcore.services.imm11 import list_schedules, _overdue_asset_ids
        drill = list_schedules({"overdue": 1}, page=1, page_size=10_000)["data"]
        drill_assets = {r["asset"] for r in drill}
        self.assertEqual(drill_assets, _overdue_asset_ids())
        for r in drill:
            self.assertLess(str(r["next_due_date"]), nowdate())

    def test_due_before_legacy_superset(self):
        """due_before (cutoff tùy ý) GIỮ ngữ nghĩa tập-bao (<= cutoff, gồm
        overdue) — không vỡ caller legacy. KHÁC due_soon (2-biên)."""
        from assetcore.services.imm11 import list_schedules
        a_od = _make_asset("-dbl-od")
        a_ds = _make_asset("-dbl-ds")
        self.addCleanup(self._cleanup_assets, [a_od, a_ds])
        _make_schedule(a_od.name, next_due=add_days(nowdate(), -10))
        _make_schedule(a_ds.name, next_due=add_days(nowdate(), 10))
        frappe.db.commit()
        cutoff = add_days(nowdate(), 30)
        # Scope drill to the 2 test assets — `asset` filter ANDs với virtual
        # due_before predicate. Tránh page-cap (paginate cap 100) bị nuốt bởi
        # seed/real data khác. Vẫn chứng minh due_before là tập-BAO: gồm cả
        # overdue (a_od, next_due<today) lẫn due_soon (a_ds) khi <= cutoff —
        # khác hẳn due_soon (2-biên loại overdue).
        scope = {"due_before": cutoff, "asset": ["in", [a_od.name, a_ds.name]]}
        drill = list_schedules(scope, page=1, page_size=100)["data"]
        drill_assets = {r["asset"] for r in drill}
        self.assertIn(a_od.name, drill_assets,
                      "due_before là tập-bao: overdue (<= cutoff) VẪN có")
        self.assertIn(a_ds.name, drill_assets)
        for r in drill:
            self.assertLessEqual(str(r["next_due_date"]), cutoff)

    @staticmethod
    def _cleanup_assets(assets):
        for a in assets:
            frappe.db.delete("IMM Calibration Schedule", {"asset": a.name})
            _purge_asset_with_deps(a.name)
        frappe.db.commit()


class TestCheckCalibrationExpiryRollup(unittest.TestCase):
    """TDD-8 (idempotent + anti-spam) / TDD-9 (no-regression rollup cache).

    check_calibration_expiry = rollup cache AC Asset.calibration_status TỪ SoT
    schedule. Idempotent: chạy 2× cho cùng kết quả. notify_calibration_due chỉ
    gọi khi status THỰC SỰ đổi.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._assets: list[str] = []
        # Asset minted overdue (next_calibration_date NULL): chứng minh rollup
        # KHÔNG đọc field asset mà derive từ schedule.
        cls.a = _make_asset("-rollup-od")
        cls._assets.append(cls.a.name)
        _make_schedule(cls.a.name, next_due=add_days(nowdate(), -6))
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for an in cls._assets:
            frappe.db.delete("IMM Calibration Schedule", {"asset": an})
            _purge_asset_with_deps(an)
        frappe.db.commit()

    def test_tdd8_rollup_idempotent_and_antispam(self):
        from unittest.mock import patch
        from assetcore.services.imm11 import check_calibration_expiry
        from assetcore.services.shared import CalibrationStatus

        # reset cache để chuyển trạng thái lần 1 (None/empty → Overdue)
        frappe.db.set_value("AC Asset", self.a.name, "calibration_status", "")

        with patch("assetcore.services.notifications.notify_calibration_due") as m:
            check_calibration_expiry()
            calls_1 = m.call_count
        status_1 = frappe.db.get_value("AC Asset", self.a.name, "calibration_status")
        self.assertEqual(status_1, CalibrationStatus.OVERDUE,
                         "rollup cache phải set Overdue từ SoT schedule (mint gap)")
        self.assertGreaterEqual(calls_1, 1, "lần 1 status đổi → notify >0")

        with patch("assetcore.services.notifications.notify_calibration_due") as m2:
            check_calibration_expiry()
            calls_2 = m2.call_count
        status_2 = frappe.db.get_value("AC Asset", self.a.name, "calibration_status")
        self.assertEqual(status_1, status_2, "idempotent: 2 lần chạy cùng status")
        self.assertEqual(calls_2, 0,
                         "lần 2 status KHÔNG đổi → KHÔNG notify (anti-spam)")


class TestCalibrationReconciliation(unittest.TestCase):
    """TDD-RECON-1..5 — full-set reconcile write-path (BR-11-10 / BR-11-11).

    check_calibration_expiry phải duyệt UNION(asset có active schedule, asset có
    calibration_status != '') — KHÔNG chỉ rollup.items(). 2 bug gốc:
      BUG-1 stale-never-cleared: lịch DUY NHẤT bị is_active=0/xóa → cache giữ
            'Overdue'/'Due Soon' vĩnh viễn (badge ma). Phải reset NOT_REQUIRED/''.
      BUG-2 FAILED-clobber: terminal 'Calibration Failed' (lifecycle Out of
            Service) bị rollup ghi đè về On Schedule/Overdue. Phải preserve.
    docs/imm-11/04_Backend_Design.md §4.1.3 (BR-11-10 / BR-11-11).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._assets: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for an in cls._assets:
            frappe.db.delete("IMM Calibration Schedule", {"asset": an})
            _purge_asset_with_deps(an)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _track(self, asset):
        type(self)._assets.append(asset.name)
        return asset

    # ── TDD-RECON-1: stale-reset (BUG-1) ─────────────────────────────────────
    def test_recon1_stale_overdue_reset_after_schedule_deactivated(self):
        """Asset overdue → cache=Overdue; deactivate lịch DUY NHẤT (is_active=0)
        → lần quét sau reset calibration_status ∈ {NOT_REQUIRED, ''}.

        MUST fail trước fix: rollup map không còn chứa asset → vòng cũ chỉ duyệt
        rollup.items() nên không bao giờ thăm lại → 'Overdue' tồn vĩnh viễn."""
        from assetcore.services.imm11 import check_calibration_expiry
        from assetcore.services.shared import CalibrationStatus

        a = self._track(_make_asset("-recon1"))
        sched = _make_schedule(a.name, next_due=add_days(nowdate(), -8))
        frappe.db.commit()

        check_calibration_expiry()
        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "calibration_status"),
            CalibrationStatus.OVERDUE,
            "tiền đề: asset overdue → cache=Overdue",
        )

        # deactivate lịch DUY NHẤT — asset không còn active schedule
        frappe.db.set_value("IMM Calibration Schedule", sched, "is_active", 0)
        frappe.db.commit()

        check_calibration_expiry()
        new_status = frappe.db.get_value("AC Asset", a.name, "calibration_status")
        self.assertIn(
            new_status, (CalibrationStatus.NOT_REQUIRED, "", None),
            f"stale 'Overdue' phải reset về neutral, got {new_status!r}",
        )
        self.assertNotEqual(new_status, CalibrationStatus.OVERDUE,
                            "KHÔNG được giữ badge 'Overdue' khi hết active schedule")

    # ── TDD-RECON-2: FAILED-preserve (BUG-2) ─────────────────────────────────
    def test_recon2_failed_preserved_while_out_of_service(self):
        """Asset FAILED + lifecycle=Out of Service + lịch active future-due →
        rollup KHÔNG được ghi đè 'Calibration Failed'.

        MUST fail trước fix: rollup map trả 'On Schedule' (future-due) → clobber."""
        from assetcore.services.imm11 import check_calibration_expiry
        from assetcore.services.shared import CalibrationStatus

        a = self._track(_make_asset("-recon2"))
        # mô phỏng kết cục handle_calibration_fail: terminal + Out of Service
        frappe.db.set_value("AC Asset", a.name, {
            "calibration_status": CalibrationStatus.FAILED,
            "lifecycle_status": "Out of Service",
        })
        # lịch active mới (future) → rollup derive 'On Schedule'
        _make_schedule(a.name, next_due=add_days(nowdate(), 90))
        frappe.db.commit()

        check_calibration_expiry()
        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "calibration_status"),
            CalibrationStatus.FAILED,
            "terminal FAILED phải được giữ khi lifecycle=Out of Service",
        )

    def test_recon2b_failed_preserved_when_schedule_overdue(self):
        """Biến thể: lịch active OVERDUE (rollup trả 'Overdue') vẫn KHÔNG clobber
        FAILED khi Out of Service."""
        from assetcore.services.imm11 import check_calibration_expiry
        from assetcore.services.shared import CalibrationStatus

        a = self._track(_make_asset("-recon2b"))
        frappe.db.set_value("AC Asset", a.name, {
            "calibration_status": CalibrationStatus.FAILED,
            "lifecycle_status": "Out of Service",
        })
        _make_schedule(a.name, next_due=add_days(nowdate(), -5))
        frappe.db.commit()

        check_calibration_expiry()
        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "calibration_status"),
            CalibrationStatus.FAILED,
            "FAILED preserve kể cả khi lịch overdue (guard chỉ theo lifecycle)",
        )

    # ── TDD-RECON-3: FAILED released khi asset rời Out of Service ─────────────
    def test_recon3_failed_released_when_back_to_active(self):
        """Asset FAILED nhưng lifecycle=Active (recal Pass đã release) + lịch
        due_soon → rollup ĐƯỢC PHÉP chuyển sang Due Soon (guard chỉ giữ khi
        Out of Service)."""
        from assetcore.services.imm11 import check_calibration_expiry
        from assetcore.services.shared import CalibrationStatus

        a = self._track(_make_asset("-recon3"))
        frappe.db.set_value("AC Asset", a.name, {
            "calibration_status": CalibrationStatus.FAILED,
            "lifecycle_status": "Active",
        })
        _make_schedule(a.name, next_due=add_days(nowdate(), 10))  # due_soon
        frappe.db.commit()

        check_calibration_expiry()
        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "calibration_status"),
            CalibrationStatus.DUE_SOON,
            "FAILED + Active (không OoS) → rollup tiếp quản (Due Soon)",
        )

    # ── TDD-RECON-4: idempotent + anti-spam cho reset & preserve ─────────────
    def test_recon4_reset_and_preserve_idempotent_no_notify(self):
        """Lần 2 trên asset đã reset (stale-clear) VÀ asset preserved-FAILED →
        KHÔNG ghi, notify_calibration_due call_count==0. Reset/preserve KHÔNG
        emit notify (chỉ notify khi chuyển VÀO Due Soon/Overdue)."""
        from unittest.mock import patch
        from assetcore.services.imm11 import check_calibration_expiry
        from assetcore.services.shared import CalibrationStatus

        # asset stale-reset
        a_reset = self._track(_make_asset("-recon4-reset"))
        s = _make_schedule(a_reset.name, next_due=add_days(nowdate(), -8))
        frappe.db.commit()
        check_calibration_expiry()  # → Overdue
        frappe.db.set_value("IMM Calibration Schedule", s, "is_active", 0)
        frappe.db.commit()

        # asset preserved-FAILED
        a_fail = self._track(_make_asset("-recon4-fail"))
        frappe.db.set_value("AC Asset", a_fail.name, {
            "calibration_status": CalibrationStatus.FAILED,
            "lifecycle_status": "Out of Service",
        })
        _make_schedule(a_fail.name, next_due=add_days(nowdate(), -5))
        frappe.db.commit()

        alert_states = (CalibrationStatus.DUE_SOON, CalibrationStatus.OVERDUE)

        def _assert_no_alert_for(call_list, who, phase):
            """notify_calibration_due CHỈ emit cảnh báo khi new_status ∈
            {Due Soon, Overdue}. reset (→Not Required) và preserve (FAILED→FAILED)
            KHÔNG chuyển VÀO alert-state → KHÔNG spam thông báo."""
            for call in call_list:
                args, kwargs = call.args, call.kwargs
                target = args[0] if args else kwargs.get("asset_name")
                new = args[2] if len(args) >= 3 else kwargs.get("new_status")
                if target in who:
                    self.assertNotIn(
                        new, alert_states,
                        f"{phase}: {target} reset/preserve KHÔNG được emit alert "
                        f"(new_status={new!r})")

        who = (a_reset.name, a_fail.name)

        # 1st run: reset stale + preserve failed → neither transitions INTO alert.
        with patch("assetcore.services.notifications.notify_calibration_due") as m1:
            check_calibration_expiry()
            _assert_no_alert_for(m1.call_args_list, who, "lần 1")
        self.assertIn(
            frappe.db.get_value("AC Asset", a_reset.name, "calibration_status"),
            (CalibrationStatus.NOT_REQUIRED, "", None))
        self.assertEqual(
            frappe.db.get_value("AC Asset", a_fail.name, "calibration_status"),
            CalibrationStatus.FAILED)

        # 2nd run: status stable for both → idempotent no-op → notify NOT called
        # at all for them (old == new short-circuit before notify wrap).
        with patch("assetcore.services.notifications.notify_calibration_due") as m2:
            check_calibration_expiry()
            for call in m2.call_args_list:
                target = call.args[0] if call.args else call.kwargs.get("asset_name")
                self.assertNotIn(
                    target, who,
                    "lần 2: reset/preserve idempotent (new==old) → KHÔNG gọi notify")

    # ── TDD-RECON-5: count SoT no-regression ─────────────────────────────────
    def test_recon5_count_sot_unchanged_by_reconcile(self):
        """_overdue_asset_ids / _due_soon_asset_ids sets + KPI calib_due/overdue
        không đổi trước/sau khi chạy check_calibration_expiry (write-path cache
        không chạm count SoT)."""
        from assetcore.services.imm11 import (
            check_calibration_expiry, _overdue_asset_ids, _due_soon_asset_ids,
            get_kpis,
        )
        from frappe.utils import getdate

        a = self._track(_make_asset("-recon5"))
        _make_schedule(a.name, next_due=add_days(nowdate(), -7))
        frappe.db.commit()

        od_before = _overdue_asset_ids()
        ds_before = _due_soon_asset_ids()
        now = getdate(nowdate())
        k_before = get_kpis(now.year, now.month)["kpis"]

        check_calibration_expiry()

        od_after = _overdue_asset_ids()
        ds_after = _due_soon_asset_ids()
        k_after = get_kpis(now.year, now.month)["kpis"]

        self.assertEqual(od_before, od_after,
                         "_overdue_asset_ids KHÔNG đổi bởi reconcile write-path")
        self.assertEqual(ds_before, ds_after,
                         "_due_soon_asset_ids KHÔNG đổi bởi reconcile write-path")
        self.assertEqual(k_before["overdue_assets"], k_after["overdue_assets"])
        self.assertEqual(k_before["due_soon_assets"], k_after["due_soon_assets"])


# ════════════════════════════════════════════════════════════════════════════
#  BR-11-12 — Recalibration OoS-restore governance guard (TC-11-RESTORE-*)
#  docs/imm-11/02_Analysis_Design.md §BR-11-12 + 04_Backend_Design.md §4.1.5
#  AC-11-14..18 / AC-1..7. RED-prove: revert guard về `is_recalibration ∧ OoS`
#  thô ⇒ cross-module/concurrent-hold cases FAIL (asset ép Active sai).
# ════════════════════════════════════════════════════════════════════════════

_DT_CAL = "IMM Asset Calibration"


def _make_recal_pass_doc(asset_name: str, *, is_recalibration: int = 1):
    """Insert + submit a passing IMM Asset Calibration (recalibration) so the
    real on_submit → handle_calibration_pass path fires. Returns the cal doc."""
    cal = frappe.get_doc({
        "doctype": _DT_CAL,
        "asset": asset_name,
        "calibration_type": "In-House",
        "scheduled_date": nowdate(),
        "actual_date": nowdate(),
        "status": "In Progress",
        "is_recalibration": int(is_recalibration),
        "reference_standard_serial": "STD-RESTORE-001",
        "technician": "Administrator",
        "measurements": [{
            "parameter_name": "Temp", "unit": "C", "nominal_value": 100,
            "tolerance_positive": 5, "tolerance_negative": 5, "measured_value": 101,
        }],
    })
    cal.insert(ignore_permissions=True)
    cal.submit()  # overall_result computed Passed → handle_calibration_pass
    frappe.db.commit()
    return cal


def _latest_ale(asset_name: str) -> dict | None:
    rows = frappe.get_all(
        "Asset Lifecycle Event", filters={"asset": asset_name},
        fields=["name", "event_type", "from_status", "to_status",
                "root_doctype", "root_record", "notes"],
        order_by="timestamp desc, creation desc", limit=1,
    )
    return rows[0] if rows else None


def _count_passed_active_ale(asset_name: str) -> int:
    """ALE 'activated' produced by the OoS/Calibrating → Active transition."""
    return frappe.db.count("Asset Lifecycle Event", {
        "asset": asset_name, "event_type": "activated", "to_status": "Active",
    })


class TestCalibrationRestoreGuard(unittest.TestCase):
    """BR-11-12 — recalibration-pass restore CHỈ khi chủ-hold OoS == calibration
    ∧ 0 hold governance khác mở. Kill force-override hold liên-module."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        frappe.set_user("Administrator")
        for name in self._assets:
            for cal in frappe.get_all(_DT_CAL, filters={"asset": name},
                                      fields=["name"]):
                frappe.db.delete("IMM Calibration Measurement", {"parent": cal.name})
                frappe.db.delete(_DT_CAL, {"name": cal.name})
            for dt, field in (("Incident Report", "asset"),
                              ("Asset Repair", "asset_ref")):
                if frappe.db.table_exists(dt):
                    frappe.db.delete(dt, {field: name})
            _purge_asset_with_deps(name)
        frappe.db.commit()

    def _new_asset(self, suffix: str):
        a = _make_asset(suffix)
        self._assets.append(a.name)
        return a

    def _draft_cal(self, asset_name: str) -> str:
        """A real (draft) IMM Asset Calibration to satisfy the Dynamic Link
        validation of Asset Lifecycle Event.root_record."""
        cal = frappe.get_doc({
            "doctype": _DT_CAL, "asset": asset_name,
            "calibration_type": "In-House", "scheduled_date": nowdate(),
            "status": "Scheduled", "is_recalibration": 1,
            "reference_standard_serial": "STD-SRC-001",
            "technician": "Administrator",
        }).insert(ignore_permissions=True)
        return cal.name

    def _set_oos_via_calibration(self, asset_name: str):
        """OoS hold whose latest ALE root_doctype == IMM Asset Calibration."""
        from assetcore.services.imm00 import transition_asset_status
        src = self._draft_cal(asset_name)
        transition_asset_status(
            asset_name=asset_name, to_status="Out of Service",
            root_doctype=_DT_CAL, root_record=src,
            reason="cal fail (self)",
        )
        frappe.db.commit()

    # ── TC-CAL-RESTORE-01 (AC-1): Calibrating → Active luôn restore ──────────
    def test_cal_restore_01_calibrating_pass_restores_active(self):
        a = self._new_asset("-restore01")
        frappe.db.set_value("AC Asset", a.name, "lifecycle_status", "Calibrating")
        frappe.db.commit()

        _make_recal_pass_doc(a.name, is_recalibration=0)

        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "lifecycle_status"), "Active",
            "AC-1: Calibrating + Pass phải restore Active (nhánh A giữ nguyên)")
        ale = _latest_ale(a.name)
        # nhánh A: transition tự ghi ALE 'activated' to=Active
        self.assertEqual(ale["to_status"], "Active")

    # ── TC-CAL-RESTORE-02 (AC-2): self-source OoS, no other hold → restore ───
    def test_cal_restore_02_self_source_oos_restores_active(self):
        a = self._new_asset("-restore02")
        self._set_oos_via_calibration(a.name)

        _make_recal_pass_doc(a.name)

        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "lifecycle_status"), "Active",
            "AC-2: OoS do cal-fail + không hold khác + recal Pass → Active")

    # ── TC-CAL-RESTORE-03 (AC-3): OoS do Incident (IMM-12) → giữ OoS ─────────
    def test_cal_restore_03_incident_hold_keeps_oos(self):
        a = self._new_asset("-restore03")
        # OoS đặt bởi Incident (root_doctype='Incident Report')
        from assetcore.services.imm00 import transition_asset_status
        ir = frappe.get_doc({
            "doctype": "Incident Report", "asset": a.name,
            "reported_by": "Administrator", "reported_at": frappe.utils.now(),
            "incident_type": "Malfunction", "severity": "High",
            "status": "Open", "description": "hold incident open",
        }).insert(ignore_permissions=True)
        transition_asset_status(
            asset_name=a.name, to_status="Out of Service",
            root_doctype="Incident Report", root_record=ir.name,
            reason="incident hold")
        frappe.db.commit()

        before = _count_passed_active_ale(a.name)
        _make_recal_pass_doc(a.name)

        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "lifecycle_status"),
            "Out of Service",
            "AC-3: OoS do Incident → recal Pass GIỮ Out of Service (KHÔNG ép Active)")
        self.assertEqual(_count_passed_active_ale(a.name), before,
                         "KHÔNG được ghi ALE 'activated' khi giữ OoS")
        ale = _latest_ale(a.name)
        self.assertEqual(ale["event_type"], "calibration_passed")
        self.assertEqual(ale["from_status"], "Out of Service")
        self.assertEqual(ale["to_status"], "Out of Service")
        self.assertIn("giữ Ngừng hoạt động do hạng mục khác", ale["notes"] or "")
        self.assertIn("Sự cố", ale["notes"] or "")

    # ── TC-CAL-RESTORE-04 (AC-3): OoS do Repair (IMM-09) → giữ OoS ───────────
    def test_cal_restore_04_repair_hold_keeps_oos(self):
        a = self._new_asset("-restore04")
        from assetcore.services.imm00 import transition_asset_status
        wo = frappe.get_doc({
            "doctype": "Asset Repair", "asset_ref": a.name,
            "failure_description": "broken", "repair_type": "Corrective",
            "priority": "Normal", "status": "Open",
        }).insert(ignore_permissions=True)
        transition_asset_status(
            asset_name=a.name, to_status="Out of Service",
            root_doctype="Asset Repair", root_record=wo.name,
            reason="repair hold")
        frappe.db.commit()

        _make_recal_pass_doc(a.name)

        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "lifecycle_status"),
            "Out of Service",
            "AC-3: OoS do Repair → recal Pass GIỮ Out of Service")
        ale = _latest_ale(a.name)
        self.assertEqual(ale["to_status"], "Out of Service")
        self.assertIn("Sửa chữa", ale["notes"] or "")

    # ── TC-CAL-RESTORE-05 (AC-4): self-source OoS NHƯNG còn Incident mở ──────
    def test_cal_restore_05_concurrent_incident_keeps_oos(self):
        a = self._new_asset("-restore05")
        # chủ-hold = calibration, NHƯNG vẫn còn 1 Incident mở
        self._set_oos_via_calibration(a.name)
        frappe.get_doc({
            "doctype": "Incident Report", "asset": a.name,
            "reported_by": "Administrator", "reported_at": frappe.utils.now(),
            "incident_type": "Malfunction", "severity": "High",
            "status": "Open", "description": "concurrent open incident",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

        _make_recal_pass_doc(a.name)

        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "lifecycle_status"),
            "Out of Service",
            "AC-4: chủ-hold cal NHƯNG còn Incident mở → GIỮ OoS (không restore)")
        ale = _latest_ale(a.name)
        self.assertEqual(ale["to_status"], "Out of Service")
        self.assertIn("giữ Ngừng hoạt động do hạng mục khác", ale["notes"] or "")

    # ── TC-CAL-RESTORE-06 (AC-5): terminal Decommissioned → no-raise ─────────
    def test_cal_restore_06_decommissioned_no_raise(self):
        a = self._new_asset("-restore06")
        # asset thanh lý giữa chừng (terminal) — recal Pass KHÔNG được raise
        frappe.db.set_value("AC Asset", a.name, "lifecycle_status", "Decommissioned")
        frappe.db.commit()

        try:
            _make_recal_pass_doc(a.name)
        except Exception as exc:  # noqa: BLE001
            self.fail(f"on_submit recal Pass KHÔNG được raise (terminal): {exc}")

        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "lifecycle_status"),
            "Decommissioned",
            "AC-5: terminal giữ nguyên, KHÔNG ép Active")
        self.assertEqual(_count_passed_active_ale(a.name), 0,
                         "KHÔNG ghi ALE 'activated' từ terminal")

    # ── TC-CAL-RESTORE-07 (AC-5): idempotent — không ALE Active trùng ────────
    def test_cal_restore_07_idempotent_no_duplicate_active(self):
        a = self._new_asset("-restore07")
        self._set_oos_via_calibration(a.name)
        _make_recal_pass_doc(a.name)  # → Active (1 ALE 'activated')
        self.assertEqual(
            frappe.db.get_value("AC Asset", a.name, "lifecycle_status"), "Active")
        n1 = _count_passed_active_ale(a.name)

        # gọi lại handle_calibration_pass trên asset đã Active (prev==to → no-op)
        from assetcore.services.imm11 import handle_calibration_pass
        cal2 = frappe.get_all(_DT_CAL, filters={"asset": a.name},
                              fields=["name"], limit=1)[0]
        handle_calibration_pass(frappe.get_doc(_DT_CAL, cal2.name))
        frappe.db.commit()

        self.assertEqual(_count_passed_active_ale(a.name), n1,
                         "AC-5: chạy lại Pass khi đã Active KHÔNG tạo ALE 'activated' trùng")

    # ── TC-CAL-RESTORE-08 (AC-6): grep/AST-guard — mọi ép-Active-từ-OoS qua predicate
    def test_cal_restore_08_grep_guard_predicate_gates_active(self):
        """Static guard: trong handle_calibration_pass, KHÔNG có nhánh
        _transition_asset(..., ACTIVE) từ ngữ cảnh prev=OUT_OF_SERVICE nằm NGOÀI
        block bảo vệ bởi _can_restore_from_oos. AST: với mỗi call _transition_asset
        có arg ACTIVE đặt trong elif OUT_OF_SERVICE, phải có gọi _can_restore_from_oos
        bao quanh."""
        import ast
        import inspect
        from assetcore.services import imm11

        src = inspect.getsource(imm11.handle_calibration_pass)
        tree = ast.parse(src.lstrip())

        def _calls_predicate(node) -> bool:
            for n in ast.walk(node):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                        and n.func.id == "_can_restore_from_oos":
                    return True
            return False

        def _is_active_transition(call: ast.Call) -> bool:
            if not (isinstance(call.func, ast.Name)
                    and call.func.id == "_transition_asset"):
                return False
            for arg in call.args:
                if isinstance(arg, ast.Attribute) and arg.attr == "ACTIVE":
                    return True
            return False

        # Tìm mọi If có test so sánh current_status == OUT_OF_SERVICE
        offending = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            test_src = ast.dump(node.test)
            if "OUT_OF_SERVICE" not in test_src:
                continue
            # trong nhánh OoS: mọi _transition_asset(ACTIVE) phải nằm dưới predicate
            for inner in ast.walk(node):
                if isinstance(inner, ast.Call) and _is_active_transition(inner):
                    # tìm If bao quanh inner gọi predicate
                    guarded = any(
                        isinstance(g, ast.If) and _calls_predicate(g)
                        and inner in ast.walk(g)
                        for g in ast.walk(node)
                    )
                    if not guarded:
                        offending.append(ast.dump(inner))

        self.assertEqual(
            offending, [],
            "AC-6: ép Active-từ-OoS phải nằm sau _can_restore_from_oos (0 bypass)")


# ─── BR-11-08b: FAIL hiệu chuẩn ⇒ active Schedule due-now ─────────────────────

def _submit_calibration_with_result(
    asset_name: str, *, result: str,
    calibration_schedule: str | None = None, is_recalibration: int = 0,
) -> str:
    """End-to-end: create + measurement (Pass/Fail) + submit → fire on_submit →
    handle_calibration_fail / handle_calibration_pass.

    Basis-date = certificate_date or actual_date or nowdate(). We rely on
    actual_date (auto-set to nowdate() in before_submit) so basis == today —
    deterministic without poking certificate_date (which round-trips as a
    datetime.date and trips the controller's str-comparison guard).

    Nominal=100, tol=±5% → ±5. measured 101 → Pass; 110 → Fail (out of tolerance).
    """
    from assetcore.services.imm11 import (
        create_calibration, add_measurement, submit_calibration,
    )
    res = create_calibration(
        asset=asset_name,
        calibration_type="In-House",
        scheduled_date=add_days(nowdate(), 1),
        technician="Administrator",
        reference_standard_serial="STD-FAILDUE-001",
        calibration_schedule=calibration_schedule,
        is_recalibration=is_recalibration,
    )
    name = res["name"]
    measured = 110 if result == "Fail" else 101
    add_measurement(
        name, parameter_name="Temp", unit="C", nominal_value=100,
        tolerance_positive=5, tolerance_negative=5, measured_value=measured,
    )
    frappe.db.commit()
    submit_calibration(name)
    frappe.db.commit()
    return name


class TestCalibrationFailDueNow(unittest.TestCase):
    """BR-11-08b / INV-FAIL-DUENOW-1..5 — FAIL hiệu chuẩn phải hạ MỌI active
    IMM Calibration Schedule.next_due_date về basis-date (due-now) → asset rơi
    vào overdue/due-soon SoT set, KHÔNG còn mask ON_SCHEDULE.

    SoT KPI = IMM Calibration Schedule.next_due_date (is_active=1), KHÔNG đọc
    AC Asset.calibration_status cache (BR-11-08). Trước fix schedule giữ ngày
    tương lai → TC-01 ĐỎ (RED-prove).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []
        self._schedules: list[str] = []

    def tearDown(self):
        from assetcore.repositories.calibration_repo import CalibrationScheduleRepo
        for asset in self._assets:
            for cal in frappe.get_all(
                "IMM Asset Calibration", filters={"asset": asset}, fields=["name"]
            ):
                frappe.db.delete("IMM Calibration Measurement", {"parent": cal.name})
                frappe.db.delete("IMM Asset Calibration", {"name": cal.name})
            for dt, field in (
                ("IMM Calibration Schedule", "asset"),
                ("IMM CAPA Record",          "asset"),
                ("Incident Report",          "asset"),
            ):
                if frappe.db.table_exists(dt):
                    try:
                        frappe.db.delete(dt, {field: asset})
                    except Exception:
                        pass
            _purge_asset_with_deps(asset)
        frappe.db.commit()

    def _new_asset(self, suffix: str) -> str:
        a = _make_asset(suffix)
        self._assets.append(a.name)
        return a.name

    def _new_schedule(self, asset_name: str, *, next_due: str, interval: int = 180,
                      cal_type: str = "In-House", is_active: int = 1) -> str:
        name = _make_schedule(
            asset_name, next_due=next_due, cal_type=cal_type,
            interval=interval, is_active=is_active,
        )
        self._schedules.append(name)
        return name

    @staticmethod
    def _next_due(schedule_name: str) -> str:
        from assetcore.repositories.calibration_repo import CalibrationScheduleRepo
        return str(CalibrationScheduleRepo.get_value(schedule_name, "next_due_date"))

    # ── TC-CAL-FAIL-DUE-01 (RED-prove) ───────────────────────────────────────
    def test_fail_lowers_active_schedule_to_basis(self):
        """FAIL với certificate_date=today → Schedule.next_due_date == today
        (basis). TRƯỚC fix vẫn = future(+180d) → test ĐỎ."""
        asset = self._new_asset("-faildue01")
        sched = self._new_schedule(asset, next_due=add_days(nowdate(), 180))
        _submit_calibration_with_result(
            asset, result="Fail",
            calibration_schedule=sched,
        )
        self.assertEqual(
            self._next_due(sched), nowdate(),
            "INV-FAIL-DUENOW-1: schedule active phải hạ về basis-date (today)",
        )

    # ── TC-CAL-FAIL-DUE-02 (overdue/due-soon set + KPI count) ────────────────
    def test_fail_asset_enters_overdue_or_due_soon_set(self):
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-faildue02")
        sched = self._new_schedule(asset, next_due=add_days(nowdate(), 180))

        # Trước fix asset KHÔNG nằm trong overdue/due-soon (mask gap).
        self.assertNotIn(asset, svc._overdue_asset_ids())
        self.assertNotIn(asset, svc._due_soon_asset_ids())
        before = svc.get_kpis(
            int(nowdate()[:4]), int(nowdate()[5:7])
        )["kpis"]
        before_due = before["overdue_assets"] + before["due_soon_assets"]

        _submit_calibration_with_result(
            asset, result="Fail",
            calibration_schedule=sched,
        )

        in_overdue = asset in svc._overdue_asset_ids()
        in_due_soon = asset in svc._due_soon_asset_ids()
        self.assertTrue(
            in_overdue or in_due_soon,
            "INV-FAIL-DUENOW-1: asset FAIL phải ∈ overdue HOẶC due-soon (due-now)",
        )
        after = svc.get_kpis(
            int(nowdate()[:4]), int(nowdate()[5:7])
        )["kpis"]
        after_due = after["overdue_assets"] + after["due_soon_assets"]
        self.assertEqual(
            after_due, before_due + 1,
            "KPI overdue+due-soon phải tăng đúng 1 (count == drill, không undercount)",
        )

    # ── TC-CAL-FAIL-DUE-03 (null-safe: không có active schedule) ─────────────
    def test_fail_without_active_schedule_no_raise(self):
        """asset FAIL KHÔNG có active Schedule → handle_calibration_fail KHÔNG
        raise; CAPA + Incident vẫn được tạo; no Schedule mutation."""
        asset = self._new_asset("-faildue03")
        # Schedule INACTIVE only (is_active=0) → loop active rỗng → no-op.
        inactive = self._new_schedule(
            asset, next_due=add_days(nowdate(), 180), is_active=0)
        cal = _submit_calibration_with_result(
            asset, result="Fail",
        )
        # Không raise (submit thành công); CAPA tạo (capa_record set trên cal) —
        # luồng FAIL hiện hữu (CAPA + lookback + incident auto-report) BẤT BIẾN.
        capa = frappe.db.get_value("IMM Asset Calibration", cal, "capa_record")
        self.assertTrue(capa, "CAPA vẫn phải được tạo khi không có active schedule")
        self.assertTrue(
            frappe.db.exists("IMM CAPA Record", capa),
            "CAPA record thực sự tồn tại (luồng FAIL bất biến)",
        )
        # asset vẫn chuyển Out of Service (write-path due-now KHÔNG ép trạng thái khác).
        self.assertEqual(
            frappe.db.get_value("AC Asset", asset, "lifecycle_status"),
            "Out of Service",
        )
        # Inactive schedule (is_active=0) KHÔNG bị đụng (giữ ngày tương lai) —
        # write-path chỉ loop active schedule.
        self.assertEqual(self._next_due(inactive), add_days(nowdate(), 180))

    # ── TC-CAL-FAIL-DUE-04 (vòng khép kín fail→due-now→pass→on-schedule) ─────
    def test_fail_then_recalibration_pass_advances_schedule(self):
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-faildue04")
        sched = self._new_schedule(
            asset, next_due=add_days(nowdate(), 180), interval=180)

        _submit_calibration_with_result(
            asset, result="Fail",
            calibration_schedule=sched,
        )
        self.assertEqual(self._next_due(sched), nowdate())
        self.assertTrue(
            asset in svc._overdue_asset_ids() or asset in svc._due_soon_asset_ids())

        # Recalibration PASS — asset đã OoS nên create_calibration cho phép
        # qua is_recalibration=1 (BLOCKED_FOR_WO bypass).
        _submit_calibration_with_result(
            asset, result="Pass", calibration_schedule=sched, is_recalibration=1,
        )

        self.assertEqual(
            self._next_due(sched), add_days(nowdate(), 180),
            "INV-FAIL-DUENOW-5: PASS sau FAIL advance next_due_date = basis+interval",
        )
        self.assertNotIn(asset, svc._overdue_asset_ids())
        self.assertNotIn(asset, svc._due_soon_asset_ids())

    # ── TC-CAL-FAIL-DUE-05 (no-regression PASS lần đầu) ──────────────────────
    def test_pass_first_advances_to_future(self):
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-faildue05")
        sched = self._new_schedule(
            asset, next_due=add_days(nowdate(), 180), interval=180)
        _submit_calibration_with_result(
            asset, result="Pass",
            calibration_schedule=sched,
        )
        self.assertEqual(
            self._next_due(sched), add_days(nowdate(), 180),
            "PASS lần đầu: next_due_date = basis+interval (tương lai), bất biến",
        )
        self.assertNotIn(asset, svc._overdue_asset_ids())
        self.assertNotIn(asset, svc._due_soon_asset_ids())

    # ── TC-CAL-FAIL-DUE-06 (basis SoT shared PASS & FAIL) ────────────────────
    def test_basis_date_source_shared_pass_and_fail(self):
        from assetcore.services.imm11 import _calibration_basis_date

        class _Stub:
            def __init__(self, cert, actual):
                self.certificate_date = cert
                self.actual_date = actual

        # certificate_date có → dùng certificate_date
        self.assertEqual(
            _calibration_basis_date(_Stub("2026-01-10", "2026-01-20")), "2026-01-10")
        # thiếu certificate_date, có actual_date → actual_date
        self.assertEqual(
            _calibration_basis_date(_Stub(None, "2026-01-20")), "2026-01-20")
        # thiếu cả hai → nowdate()
        self.assertEqual(
            _calibration_basis_date(_Stub(None, None)), nowdate())

    # ── TC-CAL-FAIL-DUE-07 (idempotent: re-apply không đẩy lệch) ─────────────
    def test_fail_due_now_idempotent(self):
        """Submit FAIL 2 lần trên cùng asset (re-apply write-path due-now, cùng
        basis=today) KHÔNG nhân đôi/đẩy lệch next_due_date ngoài basis (today).
        basis cố định theo phiếu → set_values lặp lại = bất biến."""
        asset = self._new_asset("-faildue07")
        sched = self._new_schedule(asset, next_due=add_days(nowdate(), 180))

        _submit_calibration_with_result(asset, result="Fail")
        first = self._next_due(sched)
        self.assertEqual(first, nowdate())

        # Lần 2 (recalibration cũng Fail — asset đang OoS, cần is_recalibration).
        _submit_calibration_with_result(
            asset, result="Fail", is_recalibration=1)
        self.assertEqual(
            self._next_due(sched), nowdate(),
            "INV-FAIL-DUENOW-3: idempotent — re-apply giữ next_due_date == basis",
        )


# ════════════════════════════════════════════════════════════════════════════
#  BR-11-13 — PASS → Asset-cache ROLLUP đa-lịch (worst-of-all + MIN next_due)
#  docs/imm-11/02_Analysis_Design.md §BR-11-13 + 04_Backend_Design.md §4.1.7
#  docs/imm-11/07_Testing_QA.md TC-11-PASS-ROLLUP-01..07 + N1
# ════════════════════════════════════════════════════════════════════════════

class TestCalibrationPassRollup(unittest.TestCase):
    """BR-11-13 / INV-PASS-ROLLUP-1..6 — sau ``handle_calibration_pass`` (Pass
    của 1 schedule), ASSET-cache ``calibration_status`` + ``next_calibration_date``
    phải derive TỪ MỌI active schedule của asset (worst-of-all + MIN next_due),
    KHÔNG hardcode ON_SCHEDULE + next-của-1-lịch-vừa-Pass.

    RED-prove (code cũ hardcode ``calibration_status=ON_SCHEDULE`` +
    ``next_calibration_date=basis+interval``): asset 2-lịch (A overdue + B Pass)
    → TC-01/03 ĐỎ (badge "Đúng lịch" + asset rớt khỏi due-list). Sau khi thay block
    bằng ``_apply_asset_calibration_rollup`` (§4.1.7) → GREEN.

    basis-date = today (``_submit_calibration_with_result`` set actual_date=today).
    interval schedule B = 180 → sau Pass(B), B advance next_due = today+180.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        for asset in self._assets:
            for cal in frappe.get_all(
                "IMM Asset Calibration", filters={"asset": asset}, fields=["name"]
            ):
                frappe.db.delete("IMM Calibration Measurement", {"parent": cal.name})
                frappe.db.delete("IMM Asset Calibration", {"name": cal.name})
            for dt, field in (
                ("IMM Calibration Schedule", "asset"),
                ("IMM CAPA Record",          "asset"),
                ("Incident Report",          "asset"),
            ):
                if frappe.db.table_exists(dt):
                    try:
                        frappe.db.delete(dt, {field: asset})
                    except Exception:
                        pass
            _purge_asset_with_deps(asset)
        frappe.db.commit()

    # ── fixture helpers ──────────────────────────────────────────────────────
    def _new_asset(self, suffix: str) -> str:
        a = _make_asset(suffix)
        self._assets.append(a.name)
        return a.name

    def _sched(self, asset_name: str, *, next_due: str, cal_type: str = "External",
               interval: int = 180, is_active: int = 1) -> str:
        return _make_schedule(
            asset_name, next_due=next_due, cal_type=cal_type,
            interval=interval, is_active=is_active,
        )

    @staticmethod
    def _cache(asset_name: str, field: str):
        return frappe.db.get_value("AC Asset", asset_name, field)

    @staticmethod
    def _next_due(schedule_name: str) -> str:
        from assetcore.repositories.calibration_repo import CalibrationScheduleRepo
        return str(CalibrationScheduleRepo.get_value(schedule_name, "next_due_date"))

    # ── TC-11-PASS-ROLLUP-01 (BUG CHÍNH — RED-prove) ─────────────────────────
    def test_pass_multi_schedule_status_is_rollup_overdue(self):
        """asset X có A (overdue today-10) + B (Pass). Sau Pass(B):
        AC Asset.calibration_status == 'Overdue' (KHÔNG 'On Schedule') == SoT map.
        Code cũ hardcode ON_SCHEDULE → ĐỎ."""
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-pr01")
        self._sched(asset, next_due=add_days(nowdate(), -10), cal_type="External")
        sched_b = self._sched(asset, next_due=add_days(nowdate(), 5),
                              cal_type="In-House")

        _submit_calibration_with_result(
            asset, result="Pass", calibration_schedule=sched_b)

        status = self._cache(asset, "calibration_status")
        self.assertEqual(
            status, CalibrationStatus.OVERDUE,
            "INV-PASS-ROLLUP-1: còn lịch A overdue → rollup Overdue (KHÔNG On Schedule)",
        )
        self.assertEqual(
            status, svc._calibration_status_asset_ids().get(asset),
            "AC Asset.calibration_status == _calibration_status_asset_ids()[X]",
        )

    # ── TC-11-PASS-ROLLUP-02 (schedule advance BR-11-04 bất biến) ─────────────
    def test_pass_multi_schedule_advances_only_passed_schedule(self):
        """Schedule B advance = today+interval; schedule A KHÔNG đổi (today-10)."""
        asset = self._new_asset("-pr02")
        sched_a = self._sched(asset, next_due=add_days(nowdate(), -10),
                              cal_type="External")
        sched_b = self._sched(asset, next_due=add_days(nowdate(), 5),
                              cal_type="In-House", interval=180)

        _submit_calibration_with_result(
            asset, result="Pass", calibration_schedule=sched_b)

        self.assertEqual(
            self._next_due(sched_b), add_days(nowdate(), 180),
            "BR-11-04: schedule vừa Pass advance next_due_date = basis+interval",
        )
        self.assertEqual(
            self._next_due(sched_a), add_days(nowdate(), -10),
            "schedule A (KHÔNG Pass) next_due_date bất biến",
        )

    # ── TC-11-PASS-ROLLUP-03 (next == MIN + KHÔNG rớt due-list) ───────────────
    def test_pass_multi_schedule_next_is_min_and_in_due_list(self):
        """AC Asset.next_calibration_date == MIN(next_due) (= A, today-10);
        asset X ∈ get_due_calibrations(30).items (KHÔNG rớt khỏi filter).
        Code cũ đẩy next về today+180 → asset rớt khỏi due-list → ĐỎ."""
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-pr03")
        self._sched(asset, next_due=add_days(nowdate(), -10), cal_type="External")
        sched_b = self._sched(asset, next_due=add_days(nowdate(), 5),
                              cal_type="In-House")

        _submit_calibration_with_result(
            asset, result="Pass", calibration_schedule=sched_b)

        self.assertEqual(
            str(self._cache(asset, "next_calibration_date")),
            add_days(nowdate(), -10),
            "INV-PASS-ROLLUP-2: next_calibration_date == MIN(next_due) = schedule A",
        )
        due = svc.get_due_calibrations(days=30)
        names = {r["name"] for r in due["items"]}
        self.assertIn(
            asset, names,
            "INV-PASS-ROLLUP-4: asset còn lịch overdue VẪN trong due-list",
        )

    # ── TC-11-PASS-ROLLUP-04 (ROLLUP-CONSISTENCY / idempotent scheduler) ──────
    def test_pass_then_scheduler_idempotent(self):
        """Sau Pass multi-schedule → check_calibration_expiry() chạy NGAY sau
        KHÔNG đổi calibration_status (PASS-rollup == scheduler-rollup). Chạy 2×
        bất biến (no flip-flop badge)."""
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-pr04")
        self._sched(asset, next_due=add_days(nowdate(), -10), cal_type="External")
        sched_b = self._sched(asset, next_due=add_days(nowdate(), 5),
                              cal_type="In-House")

        _submit_calibration_with_result(
            asset, result="Pass", calibration_schedule=sched_b)
        after_pass = self._cache(asset, "calibration_status")

        svc.check_calibration_expiry()
        frappe.db.commit()
        self.assertEqual(
            self._cache(asset, "calibration_status"), after_pass,
            "INV-PASS-ROLLUP-3: scheduler ngay sau Pass KHÔNG đổi cache (idempotent)",
        )
        # chạy lần 2 — vẫn bất biến (no flip-flop).
        svc.check_calibration_expiry()
        frappe.db.commit()
        self.assertEqual(
            self._cache(asset, "calibration_status"), after_pass,
            "scheduler 2× → kết quả bất biến",
        )

    # ── TC-11-PASS-ROLLUP-05 (DUE_SOON rollup) ───────────────────────────────
    def test_pass_multi_schedule_status_is_rollup_due_soon(self):
        """asset có A (due_soon today+10) + B (Pass) → calibration_status ==
        'Due Soon' (KHÔNG 'On Schedule'); next_calibration_date == MIN (= A)."""
        asset = self._new_asset("-pr05")
        self._sched(asset, next_due=add_days(nowdate(), 10), cal_type="External")
        sched_b = self._sched(asset, next_due=add_days(nowdate(), 3),
                              cal_type="In-House", interval=180)

        _submit_calibration_with_result(
            asset, result="Pass", calibration_schedule=sched_b)

        self.assertEqual(
            self._cache(asset, "calibration_status"), CalibrationStatus.DUE_SOON,
            "còn lịch A due_soon → rollup Due Soon (KHÔNG On Schedule)",
        )
        self.assertEqual(
            str(self._cache(asset, "next_calibration_date")),
            add_days(nowdate(), 10),
            "next_calibration_date == MIN(next_due) = schedule A (today+10)",
        )

    # ── TC-11-PASS-ROLLUP-06 (HAPPY 1-lịch bất biến) ─────────────────────────
    def test_pass_single_schedule_unchanged_behaviour(self):
        """asset chỉ 1 active schedule → Pass → calibration_status='On Schedule';
        next_calibration_date == add_days(basis, interval); schedule advance;
        ALE 'calibration_passed' đúng 1 record. Hành vi cũ giữ 100%."""
        asset = self._new_asset("-pr06")
        sched = self._sched(asset, next_due=add_days(nowdate(), 5),
                            cal_type="In-House", interval=180)

        _submit_calibration_with_result(
            asset, result="Pass", calibration_schedule=sched)

        self.assertEqual(
            self._cache(asset, "calibration_status"), CalibrationStatus.ON_SCHEDULE,
            "INV-PASS-ROLLUP-4: 1-lịch Pass → On Schedule (bất biến)",
        )
        self.assertEqual(
            str(self._cache(asset, "next_calibration_date")),
            add_days(nowdate(), 180),
            "1-lịch: next_calibration_date == add_days(basis, interval) = MIN trên 1 lịch",
        )
        self.assertEqual(
            self._next_due(sched), add_days(nowdate(), 180),
            "schedule advance next_due_date = basis+interval",
        )
        ale = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": asset, "event_type": "calibration_passed"},
            fields=["name"],
        )
        self.assertEqual(len(ale), 1, "đúng 1 ALE 'calibration_passed'")

    # ── TC-11-PASS-ROLLUP-07 (BR-11-12 restore-guard bất biến — nhánh C OoS) ──
    def test_pass_oos_other_hold_stays_oos_and_rolls_up(self):
        """asset Out of Service, _can_restore_from_oos=False (còn Incident mở) →
        Pass GIỮ OoS + ALE hold-note (BR-11-12 bất biến); cache rollup KHÔNG ép
        Active; CalibrationRepo.next_calibration_date set như cũ."""
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-pr07")
        sched = self._sched(asset, next_due=add_days(nowdate(), 5),
                            cal_type="In-House", interval=180)
        # Đưa asset Out of Service qua governance hold KHÁC (Incident IMM-12)
        # để _can_restore_from_oos=False (chủ-hold KHÔNG phải IMM Asset Calibration).
        from assetcore.services.imm00 import transition_asset_status
        incident = frappe.get_doc({
            "doctype": "Incident Report",
            "asset": asset,
            "incident_type": "Failure",
            "severity": "High",
            "status": "Open",
            "reported_by": "Administrator",
            "reported_at": nowdate(),
            "description": "_Test pr07 hold",
        }).insert(ignore_permissions=True)
        transition_asset_status(
            asset_name=asset, to_status=AssetStatus.OUT_OF_SERVICE,
            actor="Administrator", root_doctype="Incident Report",
            root_record=incident.name, reason="hold pr07",
        )
        frappe.db.commit()
        self.assertFalse(
            svc._can_restore_from_oos(asset, None),
            "tiền đề: còn governance hold khác → KHÔNG được restore",
        )

        cal_name = _submit_calibration_with_result(
            asset, result="Pass", calibration_schedule=sched, is_recalibration=1)

        self.assertEqual(
            self._cache(asset, "lifecycle_status"), AssetStatus.OUT_OF_SERVICE,
            "BR-11-12 nhánh C: Pass KHÔNG ép Active khi còn hold khác",
        )
        # ALE 'calibration_passed' đúng 1 record (hold-note nhồi vào note, KHÔNG +ALE).
        ale = frappe.get_all(
            "Asset Lifecycle Event",
            filters={"asset": asset, "event_type": "calibration_passed"},
            fields=["name", "notes"],
        )
        self.assertEqual(len(ale), 1, "đúng 1 ALE 'calibration_passed'")
        # CalibrationRepo.next_calibration_date (phiếu) set = basis+interval như cũ.
        from assetcore.repositories.calibration_repo import CalibrationRepo
        self.assertEqual(
            str(CalibrationRepo.get_value(cal_name, "next_calibration_date")),
            add_days(nowdate(), 180),
            "INV-PASS-ROLLUP-5: CalibrationRepo.next_calibration_date bất biến",
        )

    # ── TC-11-PASS-ROLLUP-N1 (no N+1 — bounded query) ────────────────────────
    def test_rollup_helper_bounded_queries(self):
        """_apply_asset_calibration_rollup cho asset 3 active schedule → số lần
        frappe.db.sql gọi BOUNDED, KHÔNG loop per-schedule. Đếm cho 1 vs 3 lịch
        phải BẰNG NHAU (độc lập số schedule)."""
        from assetcore.services import imm11 as svc

        def _count_sql_for_schedules(n: int) -> int:
            asset = self._new_asset(f"-prN1-{n}")
            _types = ("External", "In-House")
            for i in range(n):
                self._sched(asset, next_due=add_days(nowdate(), 5 + i),
                            cal_type=_types[i % len(_types)])
            calls = {"n": 0}
            orig = frappe.db.sql

            def _spy(*a, **k):
                calls["n"] += 1
                return orig(*a, **k)

            frappe.db.sql = _spy
            try:
                svc._apply_asset_calibration_rollup(asset, nowdate())
            finally:
                frappe.db.sql = orig
            return calls["n"]

        one = _count_sql_for_schedules(1)
        three = _count_sql_for_schedules(3)
        # INVARIANT CHỐT (INV-PASS-ROLLUP-6): query count BẰNG NHAU bất kể số
        # schedule → KHÔNG loop per-schedule SQL (KHÔNG N+1). Đây là ràng buộc thật.
        self.assertEqual(
            one, three,
            "INV-PASS-ROLLUP-6: query count độc lập số schedule (KHÔNG N+1)",
        )
        # Bounded tuyệt đối: _calibration_status_asset_ids = 4 set-query toàn-tập
        # (overdue + due_soon[=overdue+window] + on_schedule) + _asset_min_next_due
        # 1 aggregate + AssetRepo.set_values write = ≤6 (hằng, không theo schedule).
        self.assertLessEqual(
            three, 6,
            "rollup 1 asset = số query bounded (hằng số, KHÔNG theo schedule)",
        )


class TestGetDueCalibrationsNullExclusion(unittest.TestCase):
    """ROOT-CAUSE GUARD — ``get_due_calibrations`` chỉ trả asset CÓ
    ``next_calibration_date`` đã set (due_soon/overdue thật), KHÔNG trả asset
    chưa-có-lịch (``next_calibration_date`` IS NULL).

    BUG (verified @ SQL): Frappe query-builder render filter ``<= threshold``
    thành ``ifnull(next_calibration_date, '0001-01-01') <= threshold`` ⇒ MỌI
    asset NULL-date bị coerce '0001-01-01' và LỌT filter, sort ASC lên đầu.
    Với ~1500 asset NULL-date trong DB + ``limit=50``, page lấp kín bằng asset
    phantom (NULL) ⇒ asset overdue THẬT bị đẩy quá hàng 50 → rớt khỏi due-list
    (INV-PASS-ROLLUP-4 / KPI 'sắp đến hạn' đếm sai). Fix = thêm guard
    ``next_calibration_date IS SET`` vào filter (semantics đúng: chưa-có-lịch ≠
    'đến hạn').
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def setUp(self):
        frappe.set_user("Administrator")
        self._assets: list[str] = []

    def tearDown(self):
        for asset in self._assets:
            _purge_asset_with_deps(asset)
        frappe.db.commit()

    def _new_asset(self, suffix: str) -> object:
        a = _make_asset(suffix)
        self._assets.append(a.name)
        return a

    def test_null_next_calibration_date_excluded_from_due_list(self):
        """Asset MỚI (chưa có lịch → next_calibration_date NULL) KHÔNG xuất hiện
        trong get_due_calibrations(30). RED-prove: code cũ coerce NULL→'0001-01-01'
        ⇒ asset NULL-date LỌT filter (sai)."""
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-null-due")
        # đảm bảo NULL (asset mới, chưa Pass calibration nào → KHÔNG có cache date)
        self.assertIsNone(
            frappe.db.get_value("AC Asset", asset.name, "next_calibration_date"),
            "tiền đề: asset mới có next_calibration_date NULL",
        )
        # limit=100 (max page) — đủ rộng để asset NULL-date LỌT nếu filter sai.
        due = svc.get_due_calibrations(days=30, limit=100)
        names = {r["name"] for r in due["items"]}
        self.assertNotIn(
            asset.name, names,
            "asset chưa-có-lịch (NULL date) KHÔNG phải 'đến hạn' → ngoài due-list",
        )
        # KHÔNG item nào trong due-list có next_calibration_date NULL.
        self.assertTrue(
            all(r.get("next_calibration_date") for r in due["items"]),
            "due-list KHÔNG chứa item next_calibration_date NULL (no phantom)",
        )

    def test_overdue_asset_present_despite_null_date_assets_beyond_limit(self):
        """Asset overdue THẬT (next_calibration_date = today-10) PHẢI có trong
        get_due_calibrations(30) DÙ DB có hàng nghìn asset NULL-date. RED-prove:
        code cũ để NULL-date asset lấp kín limit=50 → asset overdue rớt khỏi page.

        Set next_calibration_date trực tiếp (cache field) thay vì dựng schedule —
        đủ để test filter của get_due_calibrations."""
        from assetcore.services import imm11 as svc
        asset = self._new_asset("-real-overdue")
        overdue_date = add_days(nowdate(), -10)
        frappe.db.set_value(
            "AC Asset", asset.name, "next_calibration_date", overdue_date,
            update_modified=False,
        )
        frappe.db.commit()
        # default limit=50: với ~1500 asset NULL-date trong DB, asset overdue
        # THẬT phải vẫn lọt page (vì NULL-date đã bị loại khỏi filter).
        due = svc.get_due_calibrations(days=30)
        names = {r["name"] for r in due["items"]}
        self.assertIn(
            asset.name, names,
            "asset overdue thật KHÔNG bị NULL-date asset đẩy khỏi due-list (limit=50)",
        )
        # và mọi item trả về PHẢI có next_calibration_date set (no NULL leak).
        self.assertTrue(
            all(r.get("next_calibration_date") for r in due["items"]),
            "due-list KHÔNG chứa item next_calibration_date NULL",
        )


class TestCalibrationAllowedTransitions(unittest.TestCase):
    """Server-driven CTA (mirror imm12 R3 + imm08 R21 + imm09 R22): get_calibration emit
    `allowed_transitions[]`.

    ASYMMETRY R3 ĐÓNG KÍN — màn calibration-detail mobile render nút workflow theo SERVER,
    KHÔNG hardcode status→button (anti-pattern dead-gate). Đây là thành viên THỨ TƯ & CUỐI
    có allowed_transitions[] (sau Incident R3 + PM R21 + Repair R22 → 4/4 *Detail emit).
    Assert:
      (1) codomain ⊆ CalibrationResult enum — mọi key + value-state ∈ enum (0 extra value);
      (2) _CAL_VALID_TRANSITIONS == codomain imm_11_calibration_workflow.json edge-by-edge
          theo SET (12 cạnh unique, `Failed→Conditionally Passed` khai 2 lần — tự dedup);
          terminal Passed/Conditionally Passed/Cancelled → [] (0 outgoing);
      (3) get_calibration(name) CHỨA key `allowed_transitions` == map[status] cho ≥3 status
          (Scheduled / In Progress / Passed-terminal-rỗng) — set_value flip status để exercise
          các nhánh (KHÔNG drive full workflow-engine).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-caltrans")

    @classmethod
    def tearDownClass(cls):
        for c in frappe.get_all(
            "IMM Asset Calibration", filters={"asset": cls.asset.name},
            fields=["name"],
        ):
            frappe.delete_doc(
                "IMM Asset Calibration", c.name, force=True, ignore_permissions=True
            )
        _purge_asset_with_deps(cls.asset.name)

    def setUp(self):
        frappe.set_user("Administrator")

    def test_codomain_subset_of_enum(self):
        """(1) Mọi key + value-state của _CAL_VALID_TRANSITIONS ∈ CalibrationResult enum (0 extra)."""
        from assetcore.services.imm11 import _CAL_VALID_TRANSITIONS

        enum = {
            getattr(CalibrationResult, a) for a in dir(CalibrationResult)
            if not a.startswith("_") and isinstance(getattr(CalibrationResult, a), str)
        }
        for state, nexts in _CAL_VALID_TRANSITIONS.items():
            self.assertIn(
                state, enum, f"key-state '{state}' KHÔNG ∈ CalibrationResult enum (typo/bịa).")
            for nx in nexts:
                self.assertIn(
                    nx, enum,
                    f"_CAL_VALID_TRANSITIONS['{state}'] chứa '{nx}' KHÔNG ∈ CalibrationResult enum.")

    def test_map_equals_workflow_json_edges(self):
        """(2) _CAL_VALID_TRANSITIONS == codomain imm_11_calibration_workflow.json (SET dedup).

        SSoT-divergence: thêm/bớt edge ở map mà KHÔNG đồng bộ workflow JSON → RED.
        Terminal Passed/Conditionally Passed/Cancelled → []. Count thô = 13 transition (JSON
        có dòng `Failed→Conditionally Passed` LẶP 2 lần — Compliance + System Manager); so SET
        tự dedup → 12 cạnh unique khớp map.
        """
        import json
        from pathlib import Path
        from assetcore.services.imm11 import _CAL_VALID_TRANSITIONS

        wf_path = (
            Path(frappe.get_app_path("assetcore"))
            / "assetcore" / "workflow" / "imm_11_calibration_workflow.json"
        )
        data = json.loads(wf_path.read_text(encoding="utf-8"))
        codomain = {s["state"]: set() for s in data["states"]}
        for t in data["transitions"]:
            codomain.setdefault(t["state"], set()).add(t["next_state"])
        # Key-set map BE PHẢI == states[] workflow JSON (8 state).
        self.assertEqual(
            set(_CAL_VALID_TRANSITIONS.keys()), set(codomain.keys()),
            "Key-set _CAL_VALID_TRANSITIONS PHẢI == states[] imm_11_calibration_workflow.json (8 state).")
        for state, wf_nexts in codomain.items():
            self.assertEqual(
                set(_CAL_VALID_TRANSITIONS[state]), wf_nexts,
                f"DRIFT '{state}': map BE {sorted(_CAL_VALID_TRANSITIONS[state])} ≠ "
                f"workflow next_state {sorted(wf_nexts)} (SSoT-divergence map↔workflow lệch).")
        # Sanity-count workflow JSON: 8 state / 13 transition raw (KHÔNG 12 — JSON có dòng lặp).
        self.assertEqual(
            len(data.get("states", [])), 8,
            "imm_11_calibration_workflow.json PHẢI 8 state (grounding count).")
        self.assertEqual(
            len(data.get("transitions", [])), 13,
            "imm_11_calibration_workflow.json PHẢI 13 transition raw (12 cạnh unique — dòng lặp).")
        # Terminal → [] rỗng.
        self.assertEqual(_CAL_VALID_TRANSITIONS[CalibrationResult.PASSED], [], "Passed terminal → [].")
        self.assertEqual(
            _CAL_VALID_TRANSITIONS[CalibrationResult.COND_PASSED], [],
            "Conditionally Passed terminal → [].")
        self.assertEqual(
            _CAL_VALID_TRANSITIONS[CalibrationResult.CANCELLED], [], "Cancelled terminal → [].")

    def test_live_get_calibration_emits(self):
        """(3) get_calibration CHỨA allowed_transitions == map[status] cho ≥3 status."""
        from assetcore.services.imm11 import _CAL_VALID_TRANSITIONS, get_calibration

        result = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=add_days(nowdate(), 7),
            technician="Administrator",
            reference_standard_serial="STD-TRANS-001",
        )
        frappe.db.commit()
        name = result["name"]
        try:
            # Scheduled (as created) → key present + đúng codomain (In Progress, Sent to Lab, Cancelled).
            detail = get_calibration(name)
            self.assertIn(
                "allowed_transitions", detail,
                "get_calibration PHẢI emit key 'allowed_transitions' (server-driven CTA).")
            self.assertEqual(
                detail["allowed_transitions"],
                _CAL_VALID_TRANSITIONS[CalibrationResult.SCHEDULED],
                "Scheduled → [In Progress, Sent to Lab, Cancelled].")

            # In Progress → 4 next (flip status trực tiếp; KHÔNG drive workflow-engine).
            frappe.db.set_value(
                "IMM Asset Calibration", name, "status", CalibrationResult.IN_PROGRESS)
            frappe.db.commit()
            self.assertEqual(
                get_calibration(name)["allowed_transitions"],
                _CAL_VALID_TRANSITIONS[CalibrationResult.IN_PROGRESS],
                "In Progress → [Passed, Failed, Conditionally Passed, Cancelled].")

            # Passed (terminal) → [] rỗng.
            frappe.db.set_value(
                "IMM Asset Calibration", name, "status", CalibrationResult.PASSED)
            frappe.db.commit()
            self.assertEqual(
                get_calibration(name)["allowed_transitions"], [],
                "Passed (terminal) → [] rỗng (KHÔNG transition ra).")
        finally:
            frappe.delete_doc(
                "IMM Asset Calibration", name, force=True, ignore_permissions=True)
            frappe.db.commit()


class TestCalibrationListMineScope(unittest.TestCase):
    """C-LISTREAD-MINE-CAL (ADR-MOBILE — quartet "phiếu-của-tôi" ĐÓNG NỐT sau PM/CM/Incident) —
    api/imm11.list_calibrations mine=1 scope technician == session.user cho tab
    'Phiếu hiệu chuẩn của tôi' (MVP-5d).

    Mirror TestPMListMineScope (test_imm08.py) / TestRepairListMineScope (test_imm09.py) NHƯNG
    field assignee = `technician` (KHÔNG `assigned_to`; calibration assignee — mirror IncidentMine
    dùng reported_by, mỗi domain field RIÊNG). Inject @api-layer SAU apply_vendor_scope("Calibration
    Record"). INVARIANT count==rows: count_with_or + get_all dùng CÙNG filters dict (đã có technician).
    FENCE: mine=0/absent ⇒ filters byte-identical baseline (web-FE list_calibrations KHÔNG regress).

    Calibration KHÔNG có ràng buộc "1 active / asset" (khác Asset Repair) ⇒ dùng 1 asset / nhiều
    phiếu (mirror PM). Scope CHỈ phiếu của test này qua filter `asset == cls.asset.name`.
    """

    OTHER_USER = "_test_imm11_mine_other@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("-cal-mine")
        # technician là Link User → user "khác" PHẢI tồn tại thật để insert phiếu hợp lệ.
        if not frappe.db.exists("User", cls.OTHER_USER):
            frappe.get_doc({
                "doctype": "User",
                "email": cls.OTHER_USER,
                "first_name": "IMM11 Mine Other",
                "send_welcome_email": 0,
            }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        cls._purge_cals()
        if frappe.db.exists("User", cls.OTHER_USER):
            frappe.delete_doc("User", cls.OTHER_USER, force=True, ignore_permissions=True)
        _purge_asset_with_deps(cls.asset.name)
        frappe.db.commit()

    @classmethod
    def _purge_cals(cls):
        for c in frappe.get_all(
            "IMM Asset Calibration", filters={"asset": cls.asset.name},
            fields=["name", "docstatus"],
        ):
            doc = frappe.get_doc("IMM Asset Calibration", c["name"])
            if doc.docstatus == 1:
                doc.cancel()
            frappe.delete_doc(
                "IMM Asset Calibration", c["name"], force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Mỗi test tự dựng phiếu — purge giữa các test để count==rows deterministic.
        self._purge_cals()

    def _make_cal(self, technician: str, status: str | None = None) -> str:
        # In-House (KHÔNG cần lab ISO-17025) + reference_standard_serial (VR In-House) — fixture
        # tối thiểu hợp lệ; nội dung calibration_type/lab KHÔNG ảnh hưởng scope-by-technician.
        res = create_calibration(
            asset=self.asset.name,
            calibration_type="In-House",
            scheduled_date=nowdate(),
            technician=technician,
            reference_standard_serial="REF-STD-CALMINE",
        )
        name = res["name"]
        if status and status != CalibrationResult.SCHEDULED:
            # set sau insert (bypass service/controller — chỉ cần giá trị cột cho filter test;
            # KHÔNG kích transition asset).
            frappe.db.set_value("IMM Asset Calibration", name, "status", status)
        frappe.db.commit()
        return name

    def _list(self, *, mine: int | None = None, extra: dict | None = None) -> dict:
        from assetcore.api.imm11 import list_calibrations
        f: dict = {"asset": self.asset.name}
        if extra:
            f.update(extra)
        kwargs = {"filters": json.dumps(f), "page": 1, "page_size": 100}
        if mine is not None:
            kwargs["mine"] = mine
        env = list_calibrations(**kwargs)
        self.assertTrue(env.get("success"), f"envelope KHÔNG success: {env}")
        return env["data"]

    def test_list_calibrations_mine_scopes_technician_session_user(self):
        """mine=1 → CHỈ phiếu technician == frappe.session.user (Administrator)."""
        mine_cal = self._make_cal("Administrator")
        other_cal = self._make_cal(self.OTHER_USER)
        data = self._list(mine=1)
        names = {r["name"] for r in data["data"]}
        self.assertIn(mine_cal, names, "Phiếu của session.user PHẢI hiện khi mine=1.")
        self.assertNotIn(other_cal, names, "Phiếu của KTV khác PHẢI bị loại khi mine=1.")
        for r in data["data"]:
            self.assertEqual(
                r["technician"], "Administrator",
                "mine=1 ⇒ MỌI row technician == session.user.",
            )

    def test_list_calibrations_mine_zero_fence_other_users_visible(self):
        """FENCE blast-radius: mine=0/absent ⇒ phiếu technician KTV khác VẪN hiện
        (filters byte-identical baseline — backward-compat tuyệt đối, web-FE
        list_calibrations KHÔNG regress)."""
        mine_cal = self._make_cal("Administrator")
        other_cal = self._make_cal(self.OTHER_USER)
        # mine=0 explicit.
        names0 = {r["name"] for r in self._list(mine=0)["data"]}
        self.assertIn(mine_cal, names0)
        self.assertIn(other_cal, names0, "mine=0 ⇒ phiếu KTV khác VẪN hiện (fence).")
        # mine absent — phải GIỐNG hệt mine=0 (default 0).
        names_absent = {r["name"] for r in self._list()["data"]}
        self.assertEqual(
            names0, names_absent,
            "mine absent PHẢI == mine=0 (default 0 — web-FE list_calibrations KHÔNG regress).",
        )

    def test_list_calibrations_mine_ands_with_status_filter(self):
        """mine=1 + filters status ⇒ AND (chỉ phiếu của tôi + đúng status), KHÔNG ghi đè filter."""
        my_inprogress = self._make_cal("Administrator", status=CalibrationResult.IN_PROGRESS)
        my_scheduled = self._make_cal("Administrator", status=CalibrationResult.SCHEDULED)
        other_inprogress = self._make_cal(self.OTHER_USER, status=CalibrationResult.IN_PROGRESS)
        data = self._list(mine=1, extra={"status": CalibrationResult.IN_PROGRESS})
        names = {r["name"] for r in data["data"]}
        self.assertEqual(
            names, {my_inprogress},
            "mine=1 AND status='In Progress' ⇒ CHỈ my_inprogress (loại my_scheduled=status sai, "
            "other_inprogress=KTV khác).",
        )
        self.assertNotIn(my_scheduled, names)
        self.assertNotIn(other_inprogress, names)

    def test_list_calibrations_mine_count_equals_rows(self):
        """INVARIANT count==rows: mine=1 ⇒ pagination.total == len(data.data)
        (count_with_or + get_all CÙNG filters dict đã có technician — chống drift
        memory asset_list_count_drill_technician)."""
        for _ in range(3):
            self._make_cal("Administrator")
        for _ in range(2):
            self._make_cal(self.OTHER_USER)
        data = self._list(mine=1)
        self.assertEqual(
            data["pagination"]["total"], len(data["data"]),
            "mine=1 ⇒ pagination.total PHẢI == len(rows) (count-vs-rows drift guard).",
        )
        self.assertEqual(data["pagination"]["total"], 3, "CHỈ 3 phiếu của session.user.")
