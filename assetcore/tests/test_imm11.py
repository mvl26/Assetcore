"""IMM-11 Calibration — test suite.

Run: bench --site miyano run-tests --module assetcore.tests.test_imm11
"""
from __future__ import annotations

import unittest

import frappe
from frappe.utils import nowdate, add_days

from assetcore.services.imm11 import create_calibration, cancel_calibration
from assetcore.services.shared import CalibrationResult, ErrorCode, ServiceError


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
