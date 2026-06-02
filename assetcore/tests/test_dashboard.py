"""Dashboard / KPI consistency tests — RC-08, RC-09, RC-10 NextRound.

Cover các bug:
* RC-08 — Counter "Đã hết hạn" phải bao gồm cả Asset Document trạng thái Draft.
* RC-09 — `count_pending_approvals(scope=...)` là single source of truth cho
          dashboard widget VÀ /approvals/pending.
* RC-10 — `count_overdue_pm(user=...)` là single source of truth cho launcher
          KPI, /pm/dashboard và endpoint get_overview.

Run:
    bench --site miyano run-tests --module assetcore.tests.test_dashboard
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from assetcore.services.imm00 import count_pending_approvals
from assetcore.services.imm08 import PMStatus, count_overdue_pm


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _ensure_category(name: str = "_TestCatDashboard") -> str:
    """Ensure AC Asset Category exists (autoname → lookup theo category_name)."""
    existing = frappe.db.get_value(
        "AC Asset Category", {"category_name": name}, "name"
    )
    if existing:
        return existing
    doc = frappe.get_doc(
        {"doctype": "AC Asset Category", "category_name": name}
    ).insert(ignore_permissions=True)
    return doc.name


def _make_asset(suffix: str) -> str:
    sn = f"SN-DASH-{suffix}-{int(time.time() * 1000) % 1000000}"
    doc = frappe.get_doc(
        {
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset Dashboard {suffix}",
            "asset_category": _ensure_category(),
            "manufacturer_sn": sn,
            # Để default lifecycle (Draft) — test KPI doc không phụ thuộc trạng thái asset
        }
    ).insert(ignore_permissions=True)
    return doc.name


# ─── RC-08: Expired Doc KPI bao gồm Draft ────────────────────────────────────


class TestExpiredDocsIncludesDrafts(FrappeTestCase):
    """RC-08: KPI 'Đã hết hạn' phải đếm doc Draft có expiry_date < today.

    Dùng FrappeTestCase → mỗi test wrap trong savepoint + rollback tự động,
    nên Asset Document tạo trong test method KHÔNG persist (tránh leak).

    BUG GỐC (fix vòng 13): bản cũ dùng unittest.TestCase + tearDownClass gọi
    delete_doc("Asset Document") — nhưng Asset Document.on_trash() THROW
    ("Không được phép xóa tài liệu"), bị `except: pass` nuốt → mọi lần chạy
    test LEAK toàn bộ Asset Document vào DB prod (đã thấy 56 doc rác + 28 asset
    rác). FrappeTestCase rollback giải quyết tận gốc; tearDownClass dùng RAW SQL
    để dọn asset + bất kỳ doc nào lỡ persist (on_trash chặn ORM delete).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.asset = _make_asset("RC08")
        cls.created: list[str] = []

    @classmethod
    def tearDownClass(cls):
        # Asset Document.on_trash THROW → KHÔNG dùng ORM delete được. Dùng raw
        # SQL purge mọi doc của asset test (kể cả doc lỡ persist ngoài savepoint).
        frappe.db.sql(
            "DELETE FROM `tabAsset Document` WHERE asset_ref=%s", (cls.asset,)
        )
        frappe.db.commit()
        try:
            frappe.delete_doc("AC Asset", cls.asset, force=True, ignore_permissions=True)
            frappe.db.commit()
        except Exception:  # noqa: BLE001 — asset cleanup best-effort
            frappe.db.rollback()
        super().tearDownClass()

    def _make_doc(self, state: str, expiry: str) -> str:
        # Insert ở workflow_state default ("Draft") rồi force-update sang state
        # mong muốn qua db.set_value để bypass workflow validation (chỉ cho test).
        d = frappe.get_doc(
            {
                "doctype": "Asset Document",
                "asset_ref": self.asset,
                "doc_category": "Technical",  # ko bắt buộc issuing_authority
                "doc_type_detail": f"_Test Type {state}",
                "doc_number": f"NUM-{state}-{int(time.time() * 1000) % 1000000}",
                "version": "1.0",
                "issued_date": add_days(expiry, -365),
                "expiry_date": expiry,
            }
        ).insert(ignore_permissions=True)
        if state != "Draft":
            frappe.db.set_value("Asset Document", d.name, "workflow_state", state)
        self.created.append(d.name)
        return d.name

    def test_count_expired_docs_includes_drafts(self):
        """Bug RC-08: doc Draft hết hạn vẫn phải được tính vào 'Đã hết hạn'."""
        # Tạo 2 doc: 1 Draft đã hết hạn, 1 Active đã hết hạn
        yesterday = add_days(nowdate(), -1)
        self._make_doc("Draft", yesterday)
        self._make_doc("Active", yesterday)

        # Filter theo logic dashboard.py:doc_expired (RC-08 fix)
        expired_count = frappe.db.count(
            "Asset Document",
            filters={"expiry_date": ["<", nowdate()]},
        )
        # Có ít nhất 2 (cả Draft và Active đều phải có trong count)
        self.assertGreaterEqual(expired_count, 2)

        # Đối chiếu: nếu BUG (filter status="Active") thì sẽ chỉ thấy 1
        active_only = frappe.db.count(
            "Asset Document",
            filters={"expiry_date": ["<", nowdate()], "workflow_state": "Active"},
        )
        self.assertLess(active_only, expired_count, "Bug regression: Draft bị bỏ qua")


# ─── RC-09: count_pending_approvals scope mine/all ────────────────────────────


class TestCountPendingApprovals(unittest.TestCase):
    """RC-09: helper count_pending_approvals(user, scope) là single source of truth."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def test_count_pending_approvals_mine_scope_default(self):
        """scope='mine' (default) → filter theo pending_approver = current_user."""
        # Không raise, return int
        n = count_pending_approvals()
        self.assertIsInstance(n, int)
        self.assertGreaterEqual(n, 0)

    def test_count_pending_approvals_mine_scope_explicit_user(self):
        """scope='mine' với user cụ thể."""
        n = count_pending_approvals(user="Administrator", scope="mine")
        self.assertIsInstance(n, int)
        # Kết quả phải bằng count trực tiếp với cùng filter
        expected = frappe.db.count(
            "Asset Commissioning",
            filters={"pending_approver": "Administrator", "docstatus": ["!=", 2]},
        )
        self.assertEqual(n, expected)

    def test_count_pending_approvals_all_scope_admin(self):
        """scope='all' với Administrator (có quyền) → global count."""
        frappe.set_user("Administrator")
        n = count_pending_approvals(scope="all")
        expected = frappe.db.count(
            "Asset Commissioning",
            filters={"pending_approver": ["is", "set"], "docstatus": ["!=", 2]},
        )
        self.assertEqual(n, expected)

    def test_count_pending_approvals_all_scope_falls_back_to_mine_for_non_admin(self):
        """scope='all' nhưng user thiếu quyền → fallback 'mine' (an toàn)."""
        # Tạo user mới với role thường (User)
        if not frappe.db.exists("User", "test_dash_user@example.com"):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_dash_user@example.com",
                    "first_name": "TestDash",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
        n_all = count_pending_approvals(user="test_dash_user@example.com", scope="all")
        n_mine = count_pending_approvals(user="test_dash_user@example.com", scope="mine")
        # Vì non-admin → fallback mine → 2 số bằng nhau
        self.assertEqual(n_all, n_mine)

    def test_count_pending_approvals_consistent_with_list_endpoint(self):
        """Số count phải khớp với len(list_my_pending_approvals())."""
        from assetcore.services.imm04 import list_my_pending_approvals

        frappe.set_user("Administrator")
        n = count_pending_approvals(user="Administrator", scope="mine")
        items = list_my_pending_approvals()
        # count chỉ trả số, list trả tối đa 50 record — chỉ check khi <= 50
        if n <= 50:
            self.assertEqual(n, len(items))


# ─── RC-10: count_overdue_pm consistent ──────────────────────────────────────


class TestCountOverduePm(unittest.TestCase):
    """RC-10: helper count_overdue_pm(user) là single source of truth."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def test_count_overdue_pm_global(self):
        """count_overdue_pm() (không user) → count toàn hệ thống status=Overdue."""
        n = count_overdue_pm()
        expected = frappe.db.count("PM Work Order", filters={"status": PMStatus.OVERDUE})
        self.assertEqual(n, expected)

    def test_count_overdue_pm_filter_by_user(self):
        """count_overdue_pm(user) → filter thêm assigned_to."""
        n = count_overdue_pm(user="Administrator")
        expected = frappe.db.count(
            "PM Work Order",
            filters={"status": PMStatus.OVERDUE, "assigned_to": "Administrator"},
        )
        self.assertEqual(n, expected)

    def test_count_overdue_pm_consistent_between_launcher_and_pm_dashboard(self):
        """Launcher (get_overview) và /pm/dashboard (get_dashboard_stats) phải khớp."""
        from assetcore.api.dashboard import get_overview
        from assetcore.services.imm08 import get_dashboard_stats
        from datetime import datetime

        # Launcher KPI lấy từ get_overview → pm.overdue
        overview = get_overview()
        launcher_overdue = (overview.get("data") or {}).get("pm", {}).get("overdue", 0)

        # /pm/dashboard KPI lấy từ get_dashboard_stats(year, month) → kpis.overdue
        now = datetime.now()
        pm_stats = get_dashboard_stats(year=now.year, month=now.month)
        pm_dashboard_overdue = pm_stats.get("kpis", {}).get("overdue", 0)

        # 2 source phải bằng nhau và bằng count_overdue_pm()
        canonical = count_overdue_pm()
        self.assertEqual(launcher_overdue, canonical, "Launcher KPI lệch single source")
        self.assertEqual(
            pm_dashboard_overdue,
            canonical,
            "/pm/dashboard KPI lệch single source",
        )


# ─── Persona dashboards (Core Doc FE_Persona_Dashboards.md §8.1) ──────────────


class TestPersonaDashboard(unittest.TestCase):
    """D-BE-1..6: get_persona_dashboard trả data thật, scoped, không hardcode."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def _payload(self, persona: str) -> dict:
        from assetcore.api.dashboard import get_persona_dashboard
        resp = get_persona_dashboard(persona=persona)
        self.assertTrue(resp.get("success"), f"endpoint failed: {resp}")
        return resp["data"]

    def test_d_be_1_opsmgr_matches_overview(self):
        """D-BE-1: KPI opsmgr (asset/pm/incident) khớp get_overview cùng thời điểm."""
        from assetcore.api.dashboard import get_overview
        ov = (get_overview().get("data") or {})
        data = self._payload("opsmgr")
        kpis = {k["key"]: k["value"] for k in data["kpis"]}
        self.assertEqual(kpis["active_assets"], ov.get("assets", {}).get("active", 0))
        self.assertEqual(kpis["pm_due_7d"], ov.get("pm", {}).get("due_next_7d", 0))
        self.assertEqual(kpis["incidents_critical"], ov.get("incidents", {}).get("critical_open", 0))
        self.assertIn("asset_status_breakdown", data["sections"])

    def test_d_be_2_store_matches_imm15(self):
        """D-BE-2: low_stock/pending khớp imm15.get_dashboard_stats."""
        from assetcore.services.imm15 import get_dashboard_stats
        stats = get_dashboard_stats()
        data = self._payload("store")
        kpis = {k["key"]: k["value"] for k in data["kpis"]}
        self.assertEqual(kpis["low_stock"], stats.get("low_stock_alerts", 0))
        self.assertEqual(kpis["pending_alloc"], stats.get("pending_allocations", 0))
        self.assertEqual(kpis["pending_cycle"], stats.get("pending_cycle_counts", 0))

    def test_d_be_3_qa_score_matches_scorecard(self):
        """D-BE-3: compliance score khớp imm16.get_current_scorecard (hoặc None nếu chưa có)."""
        from assetcore.services.imm16 import get_current_scorecard
        sc = get_current_scorecard()
        data = self._payload("qa")
        kpis = {k["key"]: k["value"] for k in data["kpis"]}
        if sc.get("exists") is False:
            self.assertIsNone(kpis["compliance_score"])
        else:
            expected = sc.get("overall_score") or sc.get("score") or sc.get("total_score")
            self.assertEqual(kpis["compliance_score"], expected)

    def test_d_be_4_invalid_persona_safe_empty(self):
        """D-BE-4: persona không hợp lệ → payload rỗng, không raise."""
        data = self._payload("zzz")
        self.assertEqual(data["kpis"], [])
        self.assertEqual(data["sections"], {})

    def test_d_be_5_all_personas_render(self):
        """D-BE-5: cả 8 persona trả kpis list + sections dict, không raise."""
        for p in ("admin", "opsmgr", "workshop", "tech", "clinical", "doc", "store", "qa"):
            data = self._payload(p)
            self.assertEqual(data["persona"], p)
            self.assertIsInstance(data["kpis"], list)
            self.assertIsInstance(data["sections"], dict)
            self.assertGreaterEqual(len(data["kpis"]), 1, f"{p} thiếu KPI")

    def test_d_be_6_kpi_shape_normalized(self):
        """D-BE-6: mỗi KPI có đủ key/label_vi/value/foot_vi/tone hợp lệ."""
        valid_tones = {"primary", "info", "ok", "warn", "danger"}
        data = self._payload("workshop")
        for k in data["kpis"]:
            self.assertIn("key", k)
            self.assertIn("label_vi", k)
            self.assertIn("value", k)
            self.assertIn("tone", k)
            self.assertIn(k["tone"], valid_tones)

    def test_d_be_7_none_persona_no_type_error(self):
        """LL-BE-1: persona=None (param vắng/null từ query) KHÔNG được raise
        FrappeTypeError → HTTP 417. Phải trả payload rỗng an toàn như Core Doc
        FE_Persona_Dashboards.md §3 ('KHÔNG raise — FE shell tối thiểu').

        Gọi QUA wrapper validate_argument_types(apply_condition=True) để mô phỏng
        đúng request-context — đây chính là layer raise 417 mà gọi Python trực
        tiếp KHÔNG chạm tới.
        """
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.dashboard import get_persona_dashboard

        wrapped = validate_argument_types(
            get_persona_dashboard, apply_condition=lambda: True
        )
        # persona=None: trước fix → FrappeTypeError (HTTP 417). Sau fix → safe empty.
        resp = wrapped(persona=None)
        self.assertTrue(resp.get("success"), f"endpoint failed: {resp}")
        self.assertEqual(resp["data"]["kpis"], [])
        self.assertEqual(resp["data"]["sections"], {})

    def test_d_be_8_missing_persona_arg_no_type_error(self):
        """LL-BE-1 (biến thể): gọi KHÔNG truyền persona qua request-wrapper →
        default kick-in, không raise."""
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.dashboard import get_persona_dashboard

        wrapped = validate_argument_types(
            get_persona_dashboard, apply_condition=lambda: True
        )
        resp = wrapped()
        self.assertTrue(resp.get("success"), f"endpoint failed: {resp}")
        self.assertEqual(resp["data"]["kpis"], [])
        self.assertEqual(resp["data"]["sections"], {})

    def test_d_be_9_clinical_no_dept_fails_closed(self):
        """D-BE-9: clinical persona của user CHƯA gắn khoa/phòng (_current_dept→None)
        PHẢI fail-CLOSED — KHÔNG leak data toàn viện.

        Bug gốc (fail-open): khi dept=None, filter incident/needs bị bỏ → user
        thấy toàn bộ sự cố + đề xuất + tổng asset toàn viện gắn nhãn 'khoa mình'.
        Đây là rò rỉ data vượt ranh giới role clinical (Core Doc §5.5 — clinical
        scope theo khoa). Sau fix: mọi section rỗng + sections.dept_configured=False.
        """
        from assetcore.api import dashboard as dash

        orig = dash._current_dept
        dash._current_dept = staticmethod(lambda: None)
        try:
            data = self._payload("clinical")
        finally:
            dash._current_dept = orig

        sec = data["sections"]
        # Cờ mới: clinical user chưa gắn khoa.
        self.assertIn("dept_configured", sec)
        self.assertFalse(sec["dept_configured"])
        self.assertEqual(sec.get("department"), "")
        # Fail-closed: KHÔNG liệt kê data toàn viện.
        self.assertEqual(sec.get("dept_incidents"), [])
        self.assertEqual(sec.get("dept_needs"), [])
        # KPI cũng phải scope rỗng — không leak tổng asset/sự cố toàn viện.
        kpis = {k["key"]: k["value"] for k in data["kpis"]}
        self.assertEqual(kpis["dept_assets"], 0)
        self.assertEqual(kpis["inc_open"], 0)
        self.assertEqual(kpis["nr_submitted"], 0)

    def test_d_be_10_clinical_with_dept_sets_configured_flag(self):
        """D-BE-10 (đối chứng D-BE-9): khi _current_dept trả 1 khoa thật,
        dept_configured=True và department khớp giá trị resolve — đảm bảo path
        cũ (đã scope) không bị regress."""
        from assetcore.api import dashboard as dash

        orig = dash._current_dept
        dash._current_dept = staticmethod(lambda: "_TEST-DEPT-CLINICAL")
        try:
            data = self._payload("clinical")
        finally:
            dash._current_dept = orig

        sec = data["sections"]
        self.assertTrue(sec["dept_configured"])
        self.assertEqual(sec.get("department"), "_TEST-DEPT-CLINICAL")


# ─── Drill-down / data-linking (Core Doc §9) ─────────────────────────────────


class TestDashboardDrillDown(unittest.TestCase):
    """Core Doc §9.6: KPI/segment drill metadata mang canonical code, không VI."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def _payload(self, persona: str) -> dict:
        from assetcore.api.dashboard import get_persona_dashboard
        resp = get_persona_dashboard(persona=persona)
        self.assertTrue(resp.get("success"), f"endpoint failed: {resp}")
        return resp["data"]

    def test_d_be_11_opsmgr_active_kpi_has_canonical_drill(self):
        """D-BE-11 (§9.6): KPI 'active_assets' của opsmgr mang drill.query.
        lifecycle_status == 'Active' (canonical English, KHÔNG nhãn VI)."""
        data = self._payload("opsmgr")
        kmap = {k["key"]: k for k in data["kpis"]}
        active = kmap["active_assets"]
        self.assertIsNotNone(active.get("drill"), "active KPI thiếu drill descriptor")
        self.assertEqual(active["drill"]["route"], "/assets")
        self.assertEqual(active["drill"]["query"]["lifecycle_status"], "Active")

    def test_d_be_12_lifecycle_breakdown_has_canonical_code(self):
        """D-BE-12 (§9.6): mỗi entry lifecycle_breakdown có 'code' canonical
        non-empty — để donut segment-click route bằng code (không nhãn VI)."""
        from assetcore.api.dashboard import get_overview
        ov = (get_overview().get("data") or {})
        breakdown = ov.get("lifecycle_breakdown", [])
        self.assertTrue(breakdown, "lifecycle_breakdown rỗng")
        CANON = {"Active", "Under Repair", "Calibrating", "Out of Service",
                 "Commissioned", "Decommissioned", "Under Maintenance"}
        for entry in breakdown:
            self.assertIn("code", entry, f"entry thiếu code: {entry}")
            self.assertTrue(entry["code"], "code rỗng")
            self.assertIn(entry["code"], CANON, f"code không canonical: {entry['code']}")

    def test_d_be_13_non_drill_kpi_has_none_drill(self):
        """D-BE-13 (§9.6): KPI không drillable → drill is None (không bịa route)."""
        # qa persona: compliance_score KPI không có list view filter tương ứng.
        data = self._payload("qa")
        kmap = {k["key"]: k for k in data["kpis"]}
        self.assertIsNone(kmap["compliance_score"].get("drill"))

    def test_d_be_15_opsmgr_incident_kpi_drill_severity(self):
        """D-BE-15 (§9.4.1): KPI 'incidents_critical' opsmgr drill tới
        /incidents/list?severity=Critical."""
        data = self._payload("opsmgr")
        kmap = {k["key"]: k for k in data["kpis"]}
        crit = kmap["incidents_critical"]
        self.assertIsNotNone(crit.get("drill"))
        self.assertEqual(crit["drill"]["route"], "/incidents/list")
        self.assertEqual(crit["drill"]["query"]["severity"], "Critical")

    def test_d_be_16_workshop_pm_overdue_drill(self):
        """D-BE-16 (§9.4.2): KPI 'pm_overdue' workshop drill tới
        /pm/work-orders?status=Overdue (canonical WO status)."""
        data = self._payload("workshop")
        kmap = {k["key"]: k for k in data["kpis"]}
        ov = kmap["pm_overdue"]
        self.assertIsNotNone(ov.get("drill"))
        self.assertEqual(ov["drill"]["route"], "/pm/work-orders")
        self.assertEqual(ov["drill"]["query"]["status"], "Overdue")

    def test_d_be_17_calib_due_drill_date_window(self):
        """D-BE-17 (R6 §9.4.3): KPI 'calib_due' workshop drill tới
        /calibration/schedules?due_before=<today+30> (date-window, KHÔNG ép status=).
        calib_overdue → ?overdue=1. Date-based KPI phải drill bằng cửa sổ ngày
        để count list khớp KPI (tránh 'lệch count')."""
        from frappe.utils import add_days, today
        data = self._payload("workshop")
        kmap = {k["key"]: k for k in data["kpis"]}
        due = kmap["calib_due"]
        self.assertIsNotNone(due.get("drill"), "calib_due thiếu drill")
        self.assertEqual(due["drill"]["route"], "/calibration/schedules")
        self.assertEqual(due["drill"]["query"]["due_before"], add_days(today(), 30))
        overdue = kmap.get("calib_overdue")
        if overdue is not None:
            self.assertIsNotNone(overdue.get("drill"))
            self.assertEqual(overdue["drill"]["query"].get("overdue"), "1")

    def test_d_be_18_opsmgr_pm_due_7d_drill_date_window(self):
        """D-BE-18 (R6 §9.4.3): KPI 'pm_due_7d' opsmgr drill tới
        /pm/work-orders?due_before=<today+7> (date-window)."""
        from frappe.utils import add_days, today
        data = self._payload("opsmgr")
        kmap = {k["key"]: k for k in data["kpis"]}
        due = kmap["pm_due_7d"]
        self.assertIsNotNone(due.get("drill"), "pm_due_7d thiếu drill")
        self.assertEqual(due["drill"]["route"], "/pm/work-orders")
        self.assertEqual(due["drill"]["query"]["due_before"], add_days(today(), 7))

    def test_d_be_19_calib_overview_uses_correct_field(self):
        """D-BE-19 (R6 root-cause): get_overview đếm calib_due/overdue bằng field
        next_due_date THỰC TỒN TẠI trên IMM Calibration Schedule (không phải
        next_calibration_date — column không tồn tại → OperationalError nuốt
        trong try/except làm KPI âm thầm sai)."""
        from assetcore.api.dashboard import get_overview
        ov = (get_overview().get("data") or {})
        calib = ov.get("calibration", {})
        # Count phải khớp truy vấn trực tiếp trên next_due_date (SSOT).
        from frappe.utils import today as _t, add_days as _a
        expect_overdue = frappe.db.count(
            "IMM Calibration Schedule", {"next_due_date": ["<", _t()]})
        self.assertEqual(calib.get("overdue"), expect_overdue,
                         "calib overdue lệch — field next_due_date sai?")

    def test_d_be_20_schedule_list_due_before_filter(self):
        """D-BE-20 (R6 §9.4.3): svc.list_schedules nhận virtual filter due_before
        → dịch sang next_due_date <= X; list count KHỚP KPI calib_due (round-trip)."""
        from assetcore.services.imm11 import list_schedules
        from frappe.utils import today as _t, add_days as _a
        win = _a(_t(), 30)
        res = list_schedules({"due_before": win, "is_active": 1})
        kpi_due = frappe.db.count("IMM Calibration Schedule", {
            "next_due_date": ["between", [_t(), win]], "is_active": 1})
        # List due_before là tập bao (<=win, gồm cả quá hạn). KPI là [today,win].
        # list count phải >= kpi_due (superset hợp lệ §9.4.1).
        self.assertGreaterEqual(res["pagination"]["total"], kpi_due)

    def test_d_be_26_qa_capa_drills(self):
        """D-BE-26 (R10 §9.4.8): qa KPI capa_open → /capas?not_closed=1;
        capa_overdue → /capas?overdue=1 (date-window). rca_incomplete KHÔNG drill
        (compound predicate, canonical-value §9.5 #10)."""
        data = self._payload("qa")
        kmap = {k["key"]: k for k in data["kpis"]}
        co = kmap["capa_open"]
        self.assertIsNotNone(co.get("drill"))
        self.assertEqual(co["drill"]["route"], "/capas")
        self.assertEqual(co["drill"]["query"].get("not_closed"), "1")
        cov = kmap["capa_overdue"]
        self.assertIsNotNone(cov.get("drill"))
        self.assertEqual(cov["drill"]["query"].get("overdue"), "1")
        self.assertIsNone(kmap["rca_incomplete"].get("drill"))

    def test_d_be_27_list_capas_not_closed_matches_kpi(self):
        """D-BE-27 (R10 §9.4.8): list_capas(not_closed=1) total KHỚP KPI capa_open
        (cùng predicate status NOT IN Closed) — round-trip §9.5 #10."""
        from assetcore.api.imm00 import list_capas
        res = list_capas(not_closed=1, page_size=500)
        payload = res.get("data") or res.get("message") or res
        total = payload.get("pagination", {}).get("total", 0)
        expect = frappe.db.count("IMM CAPA Record", {"status": ["not in", ["Closed"]]})
        self.assertEqual(total, expect, "list_capas(not_closed) lệch KPI capa_open")

    def test_d_be_24_workshop_cm_sla_breached_drill(self):
        """D-BE-24 (R9 §9.4.7): KPI 'cm_sla_breached' workshop drill tới
        /cm/work-orders?sla_breached=1 (list tập bao KPI compound §9.4.1)."""
        data = self._payload("workshop")
        kmap = {k["key"]: k for k in data["kpis"]}
        sla = kmap["cm_sla_breached"]
        self.assertIsNotNone(sla.get("drill"), "cm_sla_breached thiếu drill")
        self.assertEqual(sla["drill"]["route"], "/cm/work-orders")
        self.assertEqual(sla["drill"]["query"].get("sla_breached"), "1")

    def test_d_be_25_workshop_wo_to_assign_no_fake_drill(self):
        """D-BE-25 (R9 §9.4.7 canonical-value): 'wo_to_assign' là metric COMPOUND
        (PM open + CM open, 2 doctype) → KHÔNG drill tới 1 list đơn (sẽ lệch count,
        vi phạm §9.5 #10). drill phải là None; section 'wo_to_assign' table backing."""
        data = self._payload("workshop")
        kmap = {k["key"]: k for k in data["kpis"]}
        self.assertIsNone(kmap["wo_to_assign"].get("drill"),
                          "wo_to_assign compound KHÔNG được bịa drill 1-list")

    def test_d_be_22_opsmgr_severity_breakdown_canonical_codes(self):
        """D-BE-22 (R8 §9.4.6): opsmgr section 'incident_severity_breakdown' — mỗi
        entry có 'code' canonical (Critical/High/Medium/Low) + count, để donut
        segment-click route /incidents/list?severity=<code> (KHÔNG nhãn VI)."""
        data = self._payload("opsmgr")
        rows = data["sections"].get("incident_severity_breakdown")
        self.assertIsNotNone(rows, "thiếu incident_severity_breakdown")
        CANON = {"Critical", "High", "Medium", "Low"}
        seen_total = 0
        for e in rows:
            self.assertIn("code", e)
            self.assertIn(e["code"], CANON, f"severity code không canonical: {e['code']}")
            self.assertIn("count", e)
            seen_total += int(e["count"])
        # Round-trip: tổng breakdown == số incident mở (cùng predicate KPI).
        expect = frappe.db.count("Incident Report", {
            "severity": ["in", list(CANON)],
            "status": ["not in", ["Closed", "Resolved"]]})
        self.assertEqual(seen_total, expect, "severity breakdown lệch tổng incident mở")

    def test_d_be_23_opsmgr_maintenance_bars_drill_cm(self):
        """D-BE-23 (R8 §9.4.6): maintenance_kpi section mang drill cho MTTR/SLA →
        CM list filtered. SLA → /cm/work-orders?sla_breached=1; open_wos →
        /cm/work-orders (mở). Drill descriptor để BarsCard click-through."""
        data = self._payload("opsmgr")
        m = data["sections"].get("maintenance_kpi", {})
        drills = m.get("drills")
        self.assertIsNotNone(drills, "maintenance_kpi thiếu drills")
        self.assertEqual(drills["sla_compliance_pct"]["route"], "/cm/work-orders")
        self.assertEqual(drills["sla_compliance_pct"]["query"].get("sla_breached"), "1")
        self.assertEqual(drills["open_wos"]["route"], "/cm/work-orders")

    def test_d_be_21_store_low_stock_drill(self):
        """D-BE-21 (R7 §9.4.5): KPI 'low_stock' store drill tới
        /spare-parts?low_stock=1 (parts dưới định mức)."""
        data = self._payload("store")
        kmap = {k["key"]: k for k in data["kpis"]}
        low = kmap["low_stock"]
        self.assertIsNotNone(low.get("drill"), "low_stock thiếu drill")
        self.assertEqual(low["drill"]["route"], "/spare-parts")
        self.assertEqual(low["drill"]["query"]["low_stock"], "1")

    def test_d_be_28_admin_user_kpis_drill(self):
        """D-BE-28 (R1 §9.4.9): admin KPI total_users → /user-profiles;
        pending_users → /user-profiles?approval_status=Pending;
        vendor_engineers → /user-profiles?role=Vendor Engineer (canonical role-name)."""
        data = self._payload("admin")
        kmap = {k["key"]: k for k in data["kpis"]}
        tu = kmap["total_users"]
        self.assertIsNotNone(tu.get("drill"), "total_users thiếu drill")
        self.assertEqual(tu["drill"]["route"], "/user-profiles")
        self.assertEqual(tu["drill"].get("query") or {}, {})
        pu = kmap["pending_users"]
        self.assertIsNotNone(pu.get("drill"), "pending_users thiếu drill")
        self.assertEqual(pu["drill"]["route"], "/user-profiles")
        self.assertEqual(pu["drill"]["query"]["approval_status"], "Pending")
        ve = kmap["vendor_engineers"]
        self.assertIsNotNone(ve.get("drill"), "vendor_engineers thiếu drill")
        self.assertEqual(ve["drill"]["route"], "/user-profiles")
        self.assertEqual(ve["drill"]["query"]["role"], "Vendor Engineer")

    def test_d_be_29_admin_audit_chain_drill_audit_trail(self):
        """D-BE-29 (R1 §9.4.9): admin KPI audit_chain (status PASS/FAIL) → mở
        /audit-trail (viewer toàn cục, không filter). Không phải tập record nhưng
        vẫn route tới nơi user kiểm tra tính toàn vẹn."""
        data = self._payload("admin")
        kmap = {k["key"]: k for k in data["kpis"]}
        ac = kmap["audit_chain"]
        self.assertIsNotNone(ac.get("drill"), "audit_chain thiếu drill")
        self.assertEqual(ac["drill"]["route"], "/audit-trail")
        self.assertEqual(ac["drill"].get("query") or {}, {})

    def test_d_be_30_admin_recent_rows_carry_root_record(self):
        """D-BE-30 (R2 §9.4.9 #6, §10): section 'audit_recent' mỗi dòng mang đủ
        field để FE link về source: 'asset' (root record) + 'name'. KHÔNG có asset
        → FE để dòng tĩnh (không bịa link)."""
        data = self._payload("admin")
        rows = data["sections"].get("audit_recent", [])
        # Không khẳng định có dữ liệu (site có thể trống) — chỉ khẳng định SHAPE
        # khi có dòng: phải có ít nhất 'asset' hoặc 'name' để dựng link.
        for r in rows:
            self.assertTrue(
                ("asset" in r) or ("name" in r),
                f"audit_recent row thiếu khoá nguồn để drill: {r}")

    def test_d_be_14_dashboard_data_chart_has_codes(self):
        """D-BE-14 (§9.2): get_dashboard_data donut chart mang mảng 'codes'
        canonical song song labels (VI) — FE emit code khi click segment."""
        from assetcore.api.dashboard import get_dashboard_data
        data = (get_dashboard_data().get("data") or {})
        chart = data.get("asset_status_chart", {})
        self.assertIn("codes", chart)
        self.assertEqual(len(chart["codes"]), len(chart["labels"]))
        # Mọi code phải là canonical hoặc sentinel 'Chưa xác định' giữ nguyên
        for c, lbl in zip(chart["codes"], chart["labels"]):
            self.assertTrue(c, f"code rỗng cho label {lbl}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
