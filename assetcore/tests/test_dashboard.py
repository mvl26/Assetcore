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


def tearDownModule():  # noqa: N802
    """Safety net: purge dashboard fixtures that survived a class teardown gap
    (recurring '_Test Asset Dashboard *' / '_TestCatDashboard' leak)."""
    from assetcore.tests._asset_cleanup import (
        purge_assets_by_name_prefix,
        purge_category_by_name,
    )
    frappe.set_user("Administrator")
    purge_assets_by_name_prefix("_Test Asset Dashboard")
    purge_category_by_name("_TestCatDashboard")
    frappe.db.commit()


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


class TestQaComplianceScorecardKpi(FrappeTestCase):
    """IMM-16: QA-persona 'Điểm tuân thủ' KPI đọc field CHÍNH TẮC `score_pct` của
    IMM Compliance Scorecard (SoT) — KHÔNG đọc overall_score/total_score (field
    của IMM-03 Supplier Scorecard + Internal Audit, vắng mặt ⇒ card luôn trống).

    FrappeTestCase → savepoint + rollback tự động: scorecard seed trong test KHÔNG
    persist vào DB prod (tránh leak SCR-* records).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

    def _payload(self, persona: str) -> dict:
        from assetcore.api.dashboard import get_persona_dashboard
        resp = get_persona_dashboard(persona=persona)
        self.assertTrue(resp.get("success"), f"endpoint failed: {resp}")
        return resp["data"]

    def _seed_current_scorecard(self, score_pct: float):
        """Seed 1 IMM Compliance Scorecard cho kỳ/scope hiện tại (mặc định
        get_current_scorecard → scope='Hospital'). Trả doc name.

        Đặt `name` tường minh duy nhất + flags.in_import: autoname doctype
        (`format:SCR-.YYYY.-.MM.-.#####`) dùng cú pháp dot-token `.YYYY.` nhưng
        _format_autoname của Frappe chỉ expand brace-token `{YYYY}` → token KHÔNG
        nở → mọi insert đụng cùng tên literal 'SCR-.YYYY.-.MM.-.#####' (DuplicateEntry).
        Bật frappe.flags.in_import để Frappe giữ `name` explicit (set_new_name không
        null name) → né collision; KHÔNG ảnh hưởng read theo period/scope của
        get_current_scorecard (lọc theo field, không theo name)."""
        from frappe.utils import getdate
        today = getdate(nowdate())
        uniq = f"SCR-TEST-{int(time.time() * 1000000) % 10**12}"
        prev_in_import = frappe.flags.in_import
        frappe.flags.in_import = True
        try:
            doc = frappe.get_doc({
                "doctype": "IMM Compliance Scorecard",
                "name": uniq,
                "period_year": today.year,
                "period_month": today.month,
                "scope": "Hospital",
                "score_pct": score_pct,
                "non_compliant_count": 0,
            }).insert(ignore_permissions=True)
        finally:
            frappe.flags.in_import = prev_in_import
        return doc.name

    def test_tdd_1_qa_score_reads_score_pct(self):
        """TDD-1: scorecard kỳ hiện tại score_pct=87.5 ⇒ compliance_score == 87.5
        (Float, KHÔNG None) và foot_vi='Mục tiêu ≥ 85' (KHÔNG 'Chưa có scorecard
        kỳ này'). RED trước fix (đọc overall_score → None)."""
        self._seed_current_scorecard(87.5)
        data = self._payload("qa")
        kmap = {k["key"]: k for k in data["kpis"]}
        card = kmap["compliance_score"]
        self.assertEqual(card["value"], 87.5)
        self.assertEqual(card["foot_vi"], "Mục tiêu ≥ 85")

    def test_tdd_2_no_scorecard_stays_none(self):
        """TDD-2: KHÔNG có scorecard kỳ hiện tại ⇒ value=None AND
        foot_vi='Chưa có scorecard kỳ này' (KHÔNG bịa 0.0)."""
        from frappe.utils import getdate
        from assetcore.services.imm16 import get_current_scorecard
        # Precondition deterministic: xoá mọi scorecard kỳ/scope hiện tại trong
        # savepoint của test (FrappeTestCase rollback → KHÔNG đụng DB prod). Né phụ
        # thuộc state live + leak savepoint giữa các test cùng class.
        today = getdate(nowdate())
        for r in frappe.get_all("IMM Compliance Scorecard",
                                filters={"period_year": today.year,
                                         "period_month": today.month,
                                         "scope": "Hospital"}, pluck="name"):
            frappe.delete_doc("IMM Compliance Scorecard", r,
                              force=True, ignore_permissions=True)
        self.assertIs(get_current_scorecard().get("exists"), False)
        data = self._payload("qa")
        kmap = {k["key"]: k for k in data["kpis"]}
        card = kmap["compliance_score"]
        self.assertIsNone(card["value"])
        self.assertEqual(card["foot_vi"], "Chưa có scorecard kỳ này")

    def test_tdd_3_score_binds_to_sot_field(self):
        """TDD-3: score trả về == get_current_scorecard()['score_pct'] cho scorecard
        đã seed → bind KPI vào field SoT; revert sang overall_score sẽ re-break."""
        from assetcore.services.imm16 import get_current_scorecard
        self._seed_current_scorecard(87.5)
        sc = get_current_scorecard()
        self.assertEqual(sc.get("exists"), None)  # doc.as_dict không set exists
        data = self._payload("qa")
        kmap = {k["key"]: k["value"] for k in data["kpis"]}
        self.assertEqual(kmap["compliance_score"], float(sc["score_pct"]))

    def test_tdd_4_score_is_float_or_none(self):
        """TDD-4 type guard: score trả về là float (hoặc None), KHÔNG str/Decimal —
        FE numeric formatting an toàn."""
        self._seed_current_scorecard(87.5)
        data = self._payload("qa")
        kmap = {k["key"]: k["value"] for k in data["kpis"]}
        val = kmap["compliance_score"]
        self.assertIsInstance(val, float)
        self.assertNotIsInstance(val, str)

    def test_tdd_5_grep_guard_no_phantom_field_read(self):
        """TDD-5 grep guard: khối _build_qa trong api/dashboard.py KHÔNG đọc
        overall_score/total_score against scorecard object (chống cross-module
        field-name drift tái diễn)."""
        import inspect
        from assetcore.api import dashboard as dash_mod
        # Bỏ comment line: guard nhắm vào CODE đọc field, không phải comment giải thích.
        code_lines = [ln for ln in inspect.getsource(dash_mod._build_qa).splitlines()
                      if not ln.lstrip().startswith("#")]
        code = "\n".join(code_lines)
        self.assertNotRegex(code, r"\boverall_score\b",
                            "phantom field overall_score đọc lại trong _build_qa")
        self.assertNotRegex(code, r"\btotal_score\b",
                            "phantom field total_score đọc lại trong _build_qa")
        # score_pct PHẢI có mặt trong code (khẳng định đọc đúng SoT field)
        self.assertRegex(code, r"\bscore_pct\b")


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
        """D-BE-3 (TDD-3 divergence guard): compliance_score == get_current_scorecard()
        ['score_pct'] khi có scorecard, None khi chưa có. Bind KPI vào field CHÍNH
        TẮC `score_pct` (SoT IMM-16) — nếu ai revert sang overall_score thì test này
        FAIL với 'score is None'."""
        from assetcore.services.imm16 import get_current_scorecard
        sc = get_current_scorecard()
        data = self._payload("qa")
        kpis = {k["key"]: k["value"] for k in data["kpis"]}
        if sc.get("exists") is False:
            self.assertIsNone(kpis["compliance_score"])
        else:
            raw = sc.get("score_pct")
            expected = float(raw) if raw is not None else None
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

    def test_d_be_7_empty_persona_no_type_error(self):
        """D-PRECOND OpenAPI (ADR-IMM00-OPENAPI #8): persona đổi `str|None` → `str=""`.

        Param VẮNG từ query → Frappe inject default `""` (KHÔNG `None`). Chuỗi rỗng
        `""` khớp `str` → validate_argument_types KHÔNG raise FrappeTypeError (HTTP 417)
        và endpoint trả payload rỗng an toàn (Core Doc FE_Persona_Dashboards.md §3
        'KHÔNG raise — FE shell tối thiểu'). `""` ≡ None-cũ về mặt hành vi
        (`(persona or "")` normalize giống hệt).

        Gọi QUA wrapper validate_argument_types(apply_condition=True) — đúng
        request-context (layer raise 417). `persona=""` mô phỏng param vắng thực tế
        trên HTTP (KHÔNG còn truyền literal None — không phải cách HTTP gửi query param).
        """
        from frappe.utils.typing_validations import validate_argument_types
        from assetcore.api.dashboard import get_persona_dashboard

        wrapped = validate_argument_types(
            get_persona_dashboard, apply_condition=lambda: True
        )
        # persona="" (default khi param vắng): khớp str → KHÔNG 417, safe empty.
        resp = wrapped(persona="")
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
        /incidents/list?severity=Critical&open=1. open=1 áp SoT open_incident_filter
        → card count == số dòng list (invariant count==drill, không lệch Cancelled)."""
        data = self._payload("opsmgr")
        kmap = {k["key"]: k for k in data["kpis"]}
        crit = kmap["incidents_critical"]
        self.assertIsNotNone(crit.get("drill"))
        self.assertEqual(crit["drill"]["route"], "/incidents/list")
        self.assertEqual(crit["drill"]["query"]["severity"], "Critical")
        # open=1 bắt buộc để open-set list khớp KPI count (card excludes Cancelled).
        self.assertEqual(crit["drill"]["query"].get("open"), "1")

    def test_d_be_16_workshop_pm_overdue_drill(self):
        """D-BE-16 (§9.4.2): KPI 'pm_overdue' workshop drill tới
        /pm/work-orders?status=Overdue (canonical WO status)."""
        data = self._payload("workshop")
        kmap = {k["key"]: k for k in data["kpis"]}
        ov = kmap["pm_overdue"]
        self.assertIsNotNone(ov.get("drill"))
        self.assertEqual(ov["drill"]["route"], "/pm/work-orders")
        self.assertEqual(ov["drill"]["query"]["status"], "Overdue")

    def test_calib_due_card_drill_param(self):
        """D-BE-17 (R6 §9.4.3 + BR-11-08): KPI 'calib_due' workshop drill tới
        /calibration/schedules?due_soon=1 (cờ cửa-sổ-2-biên SoT, KHÔNG còn
        due_before=cutoff-tập-bao, KHÔNG ép status=). calib_overdue → ?overdue=1.
        Card due-soon dùng param riêng (due_soon) để list tái lập CHÍNH XÁC tập
        KPI — overdue rows KHÔNG lẫn vào drill due-soon."""
        data = self._payload("workshop")
        kmap = {k["key"]: k for k in data["kpis"]}
        due = kmap["calib_due"]
        self.assertIsNotNone(due.get("drill"), "calib_due thiếu drill")
        self.assertEqual(due["drill"]["route"], "/calibration/schedules")
        self.assertEqual(due["drill"]["query"].get("due_soon"), "1",
                         "calib_due phải drill ?due_soon=1 (param mới, không due_before)")
        self.assertNotIn("due_before", due["drill"]["query"],
                         "due_before là cutoff-tập-bao — KHÔNG dùng cho card due-soon")
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

    def test_d_be_19_calib_overview_uses_sot(self):
        """D-BE-19 (R6 → SoT BR-11-08): get_overview calib_overdue/due dùng CÙNG
        SoT predicate với IMM-11 module — đếm IMM Calibration Schedule.next_due_date
        của schedule is_active=1, asset NOT decommissioned, de-dup theo asset.
        KHÔNG còn đếm thô next_due_date<today (bỏ filter → đếm dư schedule chết +
        asset thanh lý)."""
        from assetcore.api.dashboard import get_overview
        from assetcore.services.imm11 import _overdue_asset_ids, _due_soon_asset_ids
        ov = (get_overview().get("data") or {})
        calib = ov.get("calibration", {})
        self.assertEqual(calib.get("overdue"), len(_overdue_asset_ids()),
                         "dashboard calib_overdue phải == SoT _overdue_asset_ids")
        self.assertEqual(calib.get("due_30d"), len(_due_soon_asset_ids()),
                         "dashboard calib_due phải == SoT _due_soon_asset_ids")

    def test_calib_due_count_matches_due_soon_ids(self):
        """BR-11-08 identity (giữ sau refactor drill param): KPI calib_due
        (calibration.due_30d) == len(_due_soon_asset_ids()) — SoT predicate KHÔNG
        đổi, chỉ drill param đổi (due_before → due_soon)."""
        from assetcore.api.dashboard import get_overview
        from assetcore.services.imm11 import _due_soon_asset_ids
        ov = (get_overview().get("data") or {})
        calib = ov.get("calibration", {})
        self.assertEqual(calib.get("due_30d"), len(_due_soon_asset_ids()),
                         "calib_due phải == len(_due_soon_asset_ids()) (identity KPI↔SoT)")

    def test_d_be_19b_dashboard_equals_module(self):
        """TDD-5 (BR-11-08 parity): api/dashboard calib_overdue == imm11
        get_kpis.overdue_assets; calib_due == due_soon_assets (cùng SoT)."""
        from assetcore.api.dashboard import get_overview
        from assetcore.services.imm11 import get_kpis
        from frappe.utils import getdate, today as _t
        ov = (get_overview().get("data") or {})
        calib = ov.get("calibration", {})
        now = getdate(_t())
        k = get_kpis(now.year, now.month)["kpis"]
        self.assertEqual(calib.get("overdue"), k["overdue_assets"],
                         "dashboard overdue ≠ module overdue_assets — SoT lệch")
        self.assertEqual(calib.get("due_30d"), k["due_soon_assets"],
                         "dashboard due ≠ module due_soon_assets — SoT lệch")

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
        """D-BE-23 (R8 §9.4.6 + BR-09-08): maintenance_kpi section mang drill cho
        MTTR/SLA → CM list filtered. SLA → /cm/work-orders?sla_breached=1.

        open_wos: thẻ đếm SoT open-set (NOT IN terminal, GỒM Pending Inspection)
        → drill PHẢI dùng cờ ảo open=1 (BE dịch → open_repair_filter, CÙNG tập)
        chứ KHÔNG status='Open' đơn lẻ (1 state) — nếu không card != drill-list
        (QA Vòng 19 regression guard)."""
        data = self._payload("opsmgr")
        m = data["sections"].get("maintenance_kpi", {})
        drills = m.get("drills")
        self.assertIsNotNone(drills, "maintenance_kpi thiếu drills")
        self.assertEqual(drills["sla_compliance_pct"]["route"], "/cm/work-orders")
        self.assertEqual(drills["sla_compliance_pct"]["query"].get("sla_breached"), "1")
        # BR-09-08 INVARIANT: open_wos drill dùng open=1 SoT, KHÔNG status đơn lẻ.
        ow = drills["open_wos"]
        self.assertEqual(ow["route"], "/cm/work-orders")
        self.assertEqual(ow["query"].get("open"), "1",
                         "open_wos drill phải dùng cờ open=1 (SoT) → card == drill")
        self.assertNotIn("status", ow["query"],
                         "drill status='Open' đơn lẻ làm lệch card (6 state) vs drill (1)")

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


# ─── Incident "đang mở" SoT — dashboard KPI/donut == drill (exclude Cancelled) ──


class TestDashboardIncidentOpenSoT(unittest.TestCase):
    """api/dashboard.py incident predicate dùng SoT open_incident_filter (imm12).

    incidents_open / incidents_critical / severity_breakdown[*].count / persona
    inc_open / rca_incomplete KHÔNG đếm status=Cancelled là 'mở' (terminal).
    Donut count == drill rows (list_incidents(open=1, severity=sev).total).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("INC-SOT")
        frappe.db.set_value("AC Asset", cls.asset, "lifecycle_status", "Active")
        cls._incidents: list[str] = []

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for ir in cls._incidents:
            try:
                frappe.delete_doc("Incident Report", ir, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        frappe.db.sql(
            "DELETE FROM `tabIMM Audit Trail` WHERE asset=%s "
            "OR (ref_doctype='AC Asset' AND ref_name=%s)",
            (cls.asset, cls.asset),
        )
        frappe.db.commit()
        try:
            frappe.delete_doc("AC Asset", cls.asset, force=True, ignore_permissions=True)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_incident(self, severity: str, status: str, *, tag: str = "") -> str:
        from assetcore.services.imm12 import report_incident
        clinical = "Ảnh hưởng chẩn đoán" if severity == "Critical" else ""
        out = report_incident(
            asset=self.asset, incident_type="Malfunction", severity=severity,
            description=f"_Test dash SoT {severity} {status}", clinical_impact=clinical,
            fault_code=tag or None,
        )
        name = out["name"]
        self._incidents.append(name)
        if status != "Open":
            frappe.db.set_value("Incident Report", name, "status", status,
                                update_modified=False)
            frappe.db.commit()
        return name

    def _overview(self) -> dict:
        from assetcore.api.dashboard import get_overview
        return get_overview().get("data") or {}

    def test_incidents_open_kpi_excludes_cancelled(self):
        """1 Open Critical + 1 Cancelled Critical + 1 Resolved Critical →
        incidents_open count CHỈ tính Open (loại Cancelled & Resolved)."""
        from assetcore.services.imm12 import open_incident_filter
        tag = "DASH-EXC"
        self._make_incident("Critical", "Open", tag=tag)
        self._make_incident("Critical", "Cancelled", tag=tag)
        self._make_incident("Critical", "Resolved", tag=tag)

        # Scope theo asset + tag method để không phụ thuộc incident method khác.
        open_critical = frappe.db.count(
            "Incident Report",
            filters=open_incident_filter({"asset": self.asset, "severity": "Critical",
                                          "fault_code": tag}),
        )
        self.assertEqual(open_critical, 1,
                         "Chỉ Open là mở; Cancelled + Resolved bị loại")

        # Sanity: cùng SoT, scope tag có đúng 1 incident mở (severity bất kỳ).
        open_any = frappe.db.count(
            "Incident Report",
            filters=open_incident_filter({"asset": self.asset, "fault_code": tag}),
        )
        self.assertEqual(open_any, 1)

    def test_donut_count_equals_drill_rows(self):
        """Invariant count==drill: incident_severity_breakdown[Critical].count
        (predicate SoT) == list_incidents(open=1, severity=Critical).total cho
        cùng asset scope. Cancelled không tính ở cả hai phía."""
        from assetcore.services.imm12 import list_incidents, open_incident_filter
        self._make_incident("Critical", "In Progress")
        self._make_incident("Critical", "Cancelled")
        self._make_incident("High", "Open")

        # Invariant đúng với scope asset (donut predicate == drill list predicate).
        donut_critical = frappe.db.count(
            "Incident Report",
            filters=open_incident_filter({"asset": self.asset, "severity": "Critical"}),
        )
        drill = list_incidents(open=1, severity="Critical",
                               asset=self.asset, page_size=100)
        self.assertEqual(donut_critical, drill["pagination"]["total"],
                         "donut segment count phải == số dòng list sau drill")

    def test_dashboard_no_inline_negative_incident_list(self):
        """Guard chống tái phát SoT drift: api/dashboard.py KHÔNG còn negative-list
        ['Closed', 'Resolved'] inline cho incident; PHẢI import open_incident_filter."""
        import os
        import assetcore.api.dashboard as dash_mod
        src = open(dash_mod.__file__, encoding="utf-8").read()
        self.assertNotIn('["Closed", "Resolved"]', src,
                         "Còn negative-list incident inline → SoT drift")
        self.assertNotIn("['Closed', 'Resolved']", src)
        self.assertIn("open_incident_filter", src,
                      "api/dashboard.py phải dùng SoT open_incident_filter")
        # đảm bảo file path hợp lệ (dùng os để tránh lint unused)
        self.assertTrue(os.path.exists(dash_mod.__file__))


class TestDashboardRepairOpenSoT(unittest.TestCase):
    """BR-09-08: api/dashboard.py repair predicate dùng SoT open_repair_filter
    (imm09). INVARIANT card == drill: KPI thẻ cm_open (get_overview.cm.open) đếm
    CÙNG tập với drill-down active_repairs (get_dashboard_data). Cannot Repair =
    TERMINAL → KHÔNG tính vào cm_open VÀ KHÔNG xuất hiện trong repair_rows.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._assets: list[str] = []
        cls._repairs: list[str] = []
        # 3 asset riêng (1 open WO / asset — tránh duplicate-open guard BR-09).
        for tag in ("RPR-INREPAIR", "RPR-CANNOT", "RPR-DONE"):
            a = _make_asset(tag)
            frappe.db.set_value("AC Asset", a, "lifecycle_status", "Active")
            cls._assets.append(a)
        cls.asset_inrepair, cls.asset_cannot, cls.asset_done = cls._assets
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for r in cls._repairs:
            try:
                frappe.delete_doc("Asset Repair", r, force=True,
                                  ignore_permissions=True, delete_permanently=True)
            except Exception:
                pass
        for a in cls._assets:
            frappe.db.sql(
                "DELETE FROM `tabIMM Audit Trail` WHERE asset=%s "
                "OR (ref_doctype='AC Asset' AND ref_name=%s)", (a, a))
            try:
                frappe.delete_doc("AC Asset", a, force=True, ignore_permissions=True)
            except Exception:
                frappe.db.rollback()
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _seed_repair(self, asset: str, status: str) -> str:
        """Seed 1 Asset Repair với status cụ thể. Insert trực tiếp để đặt
        status terminal (tránh transition workflow đầy đủ trong test predicate)."""
        from assetcore.services.imm09 import create_work_order
        out = create_work_order(
            asset_ref=asset, repair_type="Corrective", priority="Normal",
            failure_description=f"_Test dash repair SoT {status} — enough chars",
        )
        name = out["name"]
        self.__class__._repairs.append(name)
        if status != "Open":
            frappe.db.set_value("Asset Repair", name, "status", status,
                                update_modified=False)
            frappe.db.commit()
        return name

    def test_card_equals_drill_excludes_cannot_repair(self):
        """TDD-3: 1 In Repair + 1 Cannot Repair + 1 Completed → cm_open == 1
        (chỉ In Repair) VÀ len(repair_rows scope asset)==1 VÀ Cannot Repair
        KHÔNG xuất hiện trong repair_rows. Trước fix RED: cm_open==2."""
        from assetcore.api.dashboard import get_dashboard_data, get_overview
        from assetcore.services.imm09 import open_repair_filter

        self._seed_repair(self.asset_inrepair, "In Repair")
        cannot = self._seed_repair(self.asset_cannot, "Cannot Repair")
        self._seed_repair(self.asset_done, "Completed")

        my_assets = set(self._assets)

        # Card side (KPI cm_open) — scope theo asset test qua SoT filter.
        card_count = frappe.db.count(
            "Asset Repair", open_repair_filter({"asset_ref": ["in", list(my_assets)]}))

        # Drill side (active_repairs) — scope rows về asset test.
        data = get_dashboard_data().get("data") or {}
        drill = [r for r in (data.get("active_repairs") or [])
                 if r.get("asset") in my_assets]

        self.assertEqual(card_count, 1, "Chỉ In Repair là mở (Cannot Repair + Completed loại)")
        self.assertEqual(len(drill), 1, "Drill list cũng chỉ 1 dòng — card == drill")
        drill_names = {r["name"] for r in drill}
        self.assertNotIn(cannot, drill_names,
                         "Cannot Repair = TERMINAL, KHÔNG được xuất hiện trong repair_rows")

        # Sanity: get_overview.cm.open phản ánh cùng SoT (global ≥ scoped card).
        overview = get_overview().get("data") or {}
        cm_open_global = (overview.get("cm") or {}).get("open")
        self.assertIsInstance(cm_open_global, int)

    def _fresh_asset_repair(self, tag: str, status: str) -> str:
        """Asset MỚI + 1 Asset Repair status cụ thể — tránh duplicate-open guard
        (1 open WO / asset) khi reuse asset class-scope đã có WO mở."""
        a = _make_asset(tag)
        frappe.db.set_value("AC Asset", a, "lifecycle_status", "Active")
        self.__class__._assets.append(a)
        frappe.db.commit()
        return self._seed_repair(a, status)

    def test_list_work_orders_open_flag_uses_sot(self):
        """QA Vòng 19: list_work_orders({'open':1}) áp SoT open_repair_filter —
        Pending Inspection (mở per-SoT) PHẢI có; Completed (terminal) PHẢI vắng.
        Đảm bảo drill open=1 trả CÙNG tập với thẻ open_wos (card == drill)."""
        from assetcore.services.imm09 import list_work_orders

        pi = self._fresh_asset_repair("OPEN-PI", "Pending Inspection")
        done = self._fresh_asset_repair("OPEN-DONE", "Completed")

        names = {r["name"] for r in list_work_orders({"open": 1}, page_size=2000)["data"]}
        self.assertIn(pi, names, "Pending Inspection mở per-SoT phải có trong open=1")
        self.assertNotIn(done, names, "Completed = terminal, phải vắng khỏi open=1")

    def test_list_work_orders_status_overrides_open(self):
        """QA Vòng 19: status đơn lẻ ƯU TIÊN hơn open=1 (mutually-exclusive).
        list_work_orders({'open':1,'status':'Completed'}) → CHỈ Completed."""
        from assetcore.services.imm09 import list_work_orders

        done = self._fresh_asset_repair("OVR-DONE", "Completed")
        rows = list_work_orders({"open": 1, "status": "Completed"}, page_size=2000)["data"]
        self.assertTrue(rows, "phải trả ít nhất WO Completed test")
        self.assertTrue(all(r["status"] == "Completed" for r in rows),
                        "status đơn lẻ phải override open-set")
        self.assertIn(done, {r["name"] for r in rows})

    def test_dashboard_no_inline_negative_repair_list(self):
        """TDD-6 grep guard: api/dashboard.py KHÔNG còn negative-list inline cho
        Asset Repair; PHẢI dùng SoT open_repair_filter / REPAIR_TERMINAL_STATES;
        literal ma 'Closed' bị xoá khỏi mọi repair status filter."""
        import re

        import assetcore.api.dashboard as dash_mod
        src = open(dash_mod.__file__, encoding="utf-8").read()
        # Strip comments để guard chỉ soi CODE thật (comment mô tả lịch sử OK).
        code = "\n".join(
            line.split("#", 1)[0] for line in src.splitlines()
        )

        # 0 inline negative-list cho repair (các biến thể quote/space).
        forbidden = [
            r"\[\s*['\"]Completed['\"]\s*,\s*['\"]Closed['\"]\s*,\s*['\"]Cancelled['\"]\s*\]",
            r"\[\s*['\"]Completed['\"]\s*,\s*['\"]Closed['\"]\s*,\s*['\"]Cancelled['\"]\s*,"
            r"\s*['\"]Cannot Repair['\"]\s*\]",
        ]
        for pat in forbidden:
            self.assertIsNone(re.search(pat, code),
                              f"Còn negative-list repair inline → SoT drift: {pat}")

        # 'Closed' literal KHÔNG còn trong code (DocType enum không có Closed cho repair).
        # Lưu ý: các doctype khác (CAPA/QA NC/Document Request) cũng dùng 'Closed'
        # → chỉ assert không tồn tại tổ-hợp repair-terminal có 'Closed' (đã cover trên).
        self.assertIn("open_repair_filter", code,
                      "api/dashboard.py phải dùng SoT open_repair_filter")
        self.assertIn("REPAIR_TERMINAL_STATES", code,
                      "drill SQL phải build từ SoT REPAIR_TERMINAL_STATES")


class TestPMDueSoonConvergence(unittest.TestCase):
    """BR-08-12: KPI pm_due_7d (api/dashboard.pm_due_next7) đếm CÙNG tập với
    drill `/pm/work-orders?due_before=today+7` (_normalize_filters). INVARIANT
    card == drill: WO quá hạn (due_date<today) KHÔNG lọt vào drill due-soon →
    thuộc pm_overdue. Hai tập disjoint. Thay cho comment hợp-thức-hoá superset cũ.
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._cat = _ensure_category()
        # PM Checklist Template (BẮT BUỘC cho PM Schedule).
        tmpl = frappe.get_doc({
            "doctype": "PM Checklist Template",
            "template_name": f"_Test DueSoon Tmpl {int(time.time()*1000)%1000000}",
            "asset_category": cls._cat,
            "pm_type": "Quarterly",
            "version": "1.0",
            "effective_date": nowdate(),
        }).insert(ignore_permissions=True)
        cls._template = tmpl.name
        cls._asset = _make_asset("DUESOON")
        frappe.db.set_value("AC Asset", cls._asset, "lifecycle_status", "Active")
        sched = frappe.get_doc({
            "doctype": "PM Schedule",
            "asset_ref": cls._asset,
            "pm_type": "Quarterly",
            "pm_interval_days": 90,
            "checklist_template": cls._template,
            "alert_days_before": 7,
            "status": "Active",
            "last_pm_date": nowdate(),
            "next_due_date": add_days(nowdate(), 90),
        }).insert(ignore_permissions=True)
        cls._schedule = sched.name
        cls._wos: list[str] = []
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for w in cls._wos:
            try:
                frappe.delete_doc("PM Work Order", w, force=True, ignore_permissions=True)
            except Exception:
                pass
        for w in frappe.get_all("PM Work Order", filters={"asset_ref": cls._asset},
                                fields=["name"]):
            try:
                frappe.delete_doc("PM Work Order", w.name, force=True, ignore_permissions=True)
            except Exception:
                pass
        try:
            frappe.delete_doc("PM Schedule", cls._schedule, force=True, ignore_permissions=True)
            frappe.delete_doc("PM Checklist Template", cls._template, force=True,
                              ignore_permissions=True)
        except Exception:
            pass
        frappe.db.sql("DELETE FROM `tabIMM Audit Trail` WHERE asset=%s", (cls._asset,))
        try:
            frappe.delete_doc("AC Asset", cls._asset, force=True, ignore_permissions=True)
        except Exception:
            frappe.db.rollback()
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")

    def _make_wo(self, *, days_offset: int, status: str = "Open") -> str:
        from assetcore.services.imm08 import create_adhoc_work_order
        out = create_adhoc_work_order({
            "asset_ref": self._asset,
            "pm_schedule": self._schedule,
            "due_date": add_days(nowdate(), days_offset),
            "assigned_to": "Administrator",
        })
        name = out["name"]
        self.__class__._wos.append(name)
        if status != "Open":
            frappe.db.set_value("PM Work Order", name, "status", status)
        frappe.db.commit()
        return name

    def test_d_be_18b_card_equals_drill_due_soon(self):
        """TC-08-DUE-04 (thay test cũ hợp-thức-hoá superset): KPI pm_due_next7 count
        == số dòng drill list (_normalize_filters(due_before=today+7)) — scope asset
        test. WO quá hạn (today-3, Overdue) KHÔNG xuất hiện trong drill list."""
        from assetcore.services.imm08 import (
            list_work_orders, _normalize_filters, due_soon_filter,
        )
        win = add_days(nowdate(), 7)

        due_today = self._make_wo(days_offset=0)            # IN
        due_win = self._make_wo(days_offset=7)              # IN
        self._make_wo(days_offset=8)                        # OUT (quá cận trên)
        overdue = self._make_wo(days_offset=-3, status="Overdue")   # OUT (overdue)
        self._make_wo(days_offset=3, status="Completed")   # OUT (terminal)

        # Card side: KPI pm_due_next7 đếm qua due_soon_filter, scope asset test.
        card_filter = dict(due_soon_filter(win))
        card_filter["asset_ref"] = self._asset
        card_count = frappe.db.count("PM Work Order", card_filter)

        # Drill side: _normalize_filters(due_before) + scope asset.
        drill = list_work_orders(
            {"due_before": win, "asset_ref": self._asset}, page=1, page_size=500)
        drill_names = {r["name"] for r in drill["data"]}

        self.assertEqual(card_count, 2, "chỉ today + today+7 trong cửa sổ due-soon")
        self.assertEqual(drill["pagination"]["total"], card_count,
                         "INVARIANT card == drill (byte-for-byte cùng tập)")
        self.assertIn(due_today, drill_names)
        self.assertIn(due_win, drill_names)
        self.assertNotIn(overdue, drill_names,
                         "WO quá hạn KHÔNG được lọt vào drill due-soon (thuộc pm_overdue)")
        # _normalize_filters sinh cửa sổ có cận dưới today (không còn '<=').
        norm = _normalize_filters({"due_before": win})
        self.assertEqual(norm["due_date"], ["between", [nowdate(), win]])

    def test_d_be_18c_overview_kpi_parity(self):
        """TC-08-DUE-05: kpis['pm_due_7d'] (overview) == pm.due_next_7d ==
        _count(due_soon_filter(today+7)) global, byte-for-byte cùng helper."""
        from assetcore.api.dashboard import get_overview
        from assetcore.services.imm08 import due_soon_filter
        win = add_days(nowdate(), 7)
        # Tạo 1 WO due-soon để parity khác 0 trên môi trường sạch.
        self._make_wo(days_offset=2)

        ov = (get_overview().get("data") or {})
        kpi = ov.get("pm", {}).get("due_next_7d")
        sot_count = frappe.db.count("PM Work Order", due_soon_filter(win))
        self.assertEqual(kpi, sot_count,
                         "pm_due_next7 PHẢI == _count(due_soon_filter(today+7)) (1 SoT)")

# ─── TC-DASH-PERM: Dashboard KPI count permission-aware (count == drill) ───────


class TestDashboardPermissionAwareCount(FrappeTestCase):
    """P1 (QA BE-PERF AUDIT 2026-06-10): dashboard KPI count BROKEN cho persona
    scoped (Vendor Engineer). Root-cause: api/dashboard.py:_count dùng
    ``frappe.db.count`` → KHÔNG áp ``permission_query_conditions`` hook, trong khi
    drill list (``count_with_or`` → ``frappe.get_list``) ÁP. ⟹ card "Tổng N" toàn
    viện nhưng drill chỉ ra subset persona → count != drill + lỗ leak aggregate.

    Fix (USER 2026-06-09): _count tách 2 nhánh —
      (a) doctype KHÔNG có hook → ``frappe.db.count`` (rẻ, đúng).
      (b) 5 doctype CÓ hook (AC Asset / PM Work Order / Incident Report /
          Asset Repair / Asset Commissioning) → đếm permission-aware qua
          ``frappe.get_list(limit_page_length=0)`` dưới ``frappe.session.user``
          (KHÔNG ``ignore_permissions``).

    INVARIANT (D3): get_overview() count == số dòng persona thấy khi drill list
    tương ứng, cho MỌI persona. Vendor < Admin; Vendor count == len(get_list
    cùng filter dưới session Vendor). Vendor isolation GIỮ NGUYÊN; internal
    technician + auditor = read-all KHÔNG đổi.

    Run: bench --site miyano run-tests --module assetcore.tests.test_dashboard
    """

    _VENDOR_EMAIL = "vendor_dashperm@example.com"
    _OTHER_EMAIL = "other_tech_dashperm@example.com"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        cls.cat = _ensure_category("_TestCatDashPerm")

        # Vendor Engineer (NGOÀI viện) — isolation persona. Vendor + baseline desk
        # role (AC Asset DocPerm read) → ac_asset_query routes to vendor-scope
        # branch (responsible_technician = vendor). Mirrors test_imm00_list_scope.
        cls.vendor_user = _ensure_dash_user(
            cls._VENDOR_EMAIL, "Vendor DashPerm",
            "Vendor Engineer", "AssetCore System User",
        )
        cls.other_user = _ensure_dash_user(
            cls._OTHER_EMAIL, "Other DashPerm", "Repair User",
        )

        # 1 asset của vendor (responsible_technician = vendor) + 1 của internal.
        # ⚠️ asset_name KHÔNG prefix '_' và name KHÔNG prefix 'SI-' → KHÔNG bị
        # reserved_prefix_filter loại (nếu loại, mọi count==0 → test vô nghĩa).
        # Dùng prefix 'ZDashPerm' (counted) để phân biệt với junk (_/SI- = reserved).
        cls.vendor_asset = _insert_dash_asset({
            "doctype": "AC Asset",
            "asset_name": "ZDashPerm Vendor Asset",
            "asset_category": cls.cat,
            "lifecycle_status": "Active",
            "responsible_technician": cls.vendor_user,
            "manufacturer_sn": f"DP-SN-V-{int(time.time()*1000)%1000000}",
        }).name
        cls.internal_asset = _insert_dash_asset({
            "doctype": "AC Asset",
            "asset_name": "ZDashPerm Internal Asset",
            "asset_category": cls.cat,
            "lifecycle_status": "Active",
            "responsible_technician": cls.other_user,
            "manufacturer_sn": f"DP-SN-I-{int(time.time()*1000)%1000000}",
        }).name
        cls._assets = [cls.vendor_asset, cls.internal_asset]
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        from assetcore.tests._asset_cleanup import purge_asset, purge_category_by_name
        frappe.set_user("Administrator")
        for a in getattr(cls, "_assets", []):
            try:
                purge_asset(a)
            except Exception:
                pass
        purge_category_by_name("_TestCatDashPerm")
        for email in (cls._VENDOR_EMAIL, cls._OTHER_EMAIL):
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def _overview(self) -> dict:
        from assetcore.api.dashboard import get_overview
        resp = get_overview()
        self.assertTrue(resp.get("success"), f"get_overview failed: {resp}")
        return resp["data"]

    # ── TC-DASH-PERM-01: count permission-aware (RED trước fix) ──────────────
    def test_tc_dash_perm_01_assets_total_scoped_by_persona(self):
        """Vendor session → assets.total == 1 (chỉ asset của vendor), KHÔNG 2.
        Admin session → assets.total >= 2 (read-all). Chứng minh count
        permission-aware (RED trước fix: vendor cũng thấy 2)."""
        frappe.set_user(self.vendor_user)
        try:
            vendor_total = self._overview()["assets"]["total"]
            # Vendor chỉ phụ trách vendor_asset → CHỈ thấy 1 asset (của mình).
            self.assertEqual(
                vendor_total, 1,
                "Vendor dashboard assets.total phải == 1 (asset của vendor) — "
                "KHÔNG đếm asset toàn viện (count permission-aware)",
            )
        finally:
            frappe.set_user("Administrator")

        admin_total = self._overview()["assets"]["total"]
        self.assertGreaterEqual(
            admin_total, 2,
            "Admin read-all phải thấy >= 2 asset (vendor + internal)",
        )
        self.assertLess(
            vendor_total, admin_total,
            "INVARIANT: Vendor count < Admin count (isolation giữ, no leak)",
        )

    # ── TC-DASH-PERM-02: INVARIANT count == drill (5 hooked doctypes) ────────
    def test_tc_dash_perm_02_count_equals_drill_under_vendor(self):
        """Dưới session Vendor: mỗi KPI count == số dòng drill (get_list cùng
        filter, permission-aware) cho cả 5 doctype CÓ hook. get_list dưới session
        Vendor áp CÙNG permission_query_conditions + DocPerm như drill → count ==
        drill. Persona thiếu DocPerm read trên doctype → get_list raise
        PermissionError → drill = 0 == KPI (count==drill==0, KHÔNG leak)."""
        from assetcore.services.imm00 import reserved_prefix_filter
        from assetcore.services.imm09 import open_repair_filter
        from assetcore.services.imm12 import open_incident_filter

        def _drill(doctype, filters):
            """Đếm permission-aware như _count nhánh (b) — catch PermissionError
            (persona không có DocPerm read) → 0 (== drill list rỗng)."""
            try:
                return len(frappe.get_list(
                    doctype, filters=filters, fields=["name"], limit_page_length=0))
            except Exception:
                return 0

        frappe.set_user(self.vendor_user)
        try:
            ov = self._overview()
            _rsv = reserved_prefix_filter()

            cases = [
                ("AC Asset", _rsv, ov["assets"]["total"]),
                ("PM Work Order",
                 {"status": ["not in", ["Completed", "Cancelled"]]},
                 ov["pm"]["open"]),
                ("Incident Report", open_incident_filter(), ov["incidents"]["open"]),
                ("Asset Repair", open_repair_filter(), ov["cm"]["open"]),
                ("Asset Commissioning",
                 {"workflow_state": ["not in", ["Clinical_Release", "Return_To_Vendor"]],
                  "docstatus": ["!=", 2]},
                 ov["commissioning"]["pending"]),
            ]
            for doctype, filters, kpi in cases:
                self.assertEqual(
                    kpi, _drill(doctype, filters),
                    f"{doctype}: KPI count != drill (vendor session)")
            # Sanity: AC Asset vendor scope = đúng 1 (asset của vendor) → count==1.
            self.assertEqual(ov["assets"]["total"], 1,
                             "vendor AC Asset count phải == 1 (chỉ asset của vendor)")
        finally:
            frappe.set_user("Administrator")

    # ── TC-DASH-PERM-03: non-hooked doctypes still use db.count ──────────────
    def test_tc_dash_perm_03_non_hooked_doctype_not_scoped(self):
        """Doctype KHÔNG có permission_query_conditions hook (User / Has Role /
        Asset Document / IMM CAPA Record / IMM Needs Request) VẪN dùng
        frappe.db.count → count Vendor == count Admin (KHÔNG bị scope nhầm).
        Verify nhánh (a) hoạt động qua admin-persona builder counts."""
        from assetcore.api.dashboard import _count
        from assetcore.permissions import (
            ac_asset_query, incident_report_query, asset_repair_query,
            pm_work_order_query, asset_commissioning_query,
        )
        # Đối với non-hooked doctype, _count == frappe.db.count dù session nào.
        for dt in ("User", "Has Role", "Asset Document", "IMM CAPA Record",
                   "IMM Needs Request"):
            frappe.set_user("Administrator")
            admin_c = _count(dt)
            frappe.set_user(self.vendor_user)
            try:
                vendor_c = _count(dt)
            finally:
                frappe.set_user("Administrator")
            db_c = frappe.db.count(dt)
            self.assertEqual(admin_c, db_c,
                             f"{dt}: non-hooked _count phải == frappe.db.count")
            self.assertEqual(vendor_c, db_c,
                             f"{dt}: non-hooked _count KHÔNG được scope theo persona")

    # ── TC-DASH-PERM-04: reserved-prefix loại rác qua path mới ───────────────
    def test_tc_dash_perm_04_reserved_prefix_excluded(self):
        """Seed asset rác _Test_X / SI-Y → get_overview().assets.total dưới Admin
        KHÔNG đếm chúng (predicate _rsv GIỮ qua path permission-aware mới)."""
        junk = []
        try:
            # reserved_asset_names predicate: asset_name LIKE '_%' OR name (PK)
            # LIKE 'SI-%'. AC Asset autoname (AC-ASSET-.YYYY.-.####) OVERRIDE explicit
            # `name` ngay cả khi flags.in_install → muốn PK 'SI-*' phải rename sau insert.
            uniq = int(time.time() * 1000) % 1000000
            # (a) reserved qua asset_name prefix '_'.
            d1 = _insert_dash_asset({
                "doctype": "AC Asset",
                "asset_name": "_TestDashPerm Junk Underscore",
                "asset_category": self.cat,
                "lifecycle_status": "Active",
                "manufacturer_sn": f"DP-JUNK-1-{uniq}",
            })
            junk.append(d1.name)
            # (b) reserved qua name (PK) prefix 'SI-' — rename PK sau insert.
            d2 = _insert_dash_asset({
                "doctype": "AC Asset",
                "asset_name": "DashPerm Junk SI Prefix",
                "asset_category": self.cat,
                "lifecycle_status": "Active",
                "manufacturer_sn": f"DP-JUNK-2-{uniq}",
            })
            si_name = f"SI-DASHPERM-{uniq}"
            from frappe.model.rename_doc import rename_doc as _rename_doc
            _rename_doc("AC Asset", d2.name, si_name,
                        force=True, ignore_permissions=True, validate=False)
            junk.append(si_name)
            frappe.db.commit()

            frappe.set_user("Administrator")
            ov = self._overview()
            # Asset rác KHÔNG được nằm trong drill (cùng predicate _rsv).
            from assetcore.services.imm00 import reserved_prefix_filter
            drill_names = {r["name"] for r in frappe.get_list(
                "AC Asset", filters=reserved_prefix_filter(),
                fields=["name"], limit_page_length=0)}
            for j in junk:
                self.assertNotIn(j, drill_names,
                                 f"asset rác {j} phải bị loại khỏi drill (_rsv)")
            self.assertEqual(ov["assets"]["total"], len(drill_names),
                             "assets.total == drill (_rsv giữ qua path mới)")
        finally:
            from assetcore.tests._asset_cleanup import purge_asset
            frappe.set_user("Administrator")
            for j in junk:
                try:
                    purge_asset(j)
                except Exception:
                    pass
            frappe.db.commit()

    # ── TC-DASH-PERM-05: internal tech + auditor = read-all == Admin ─────────
    def test_tc_dash_perm_05_internal_and_auditor_read_all(self):
        """Internal Technician + Auditor → assets.total == Admin (read-all,
        KHÔNG bị thu hẹp nhầm như Vendor). Xác nhận ac_asset_query trả '' cho 2
        persona này được tôn trọng trên path đếm KPI."""
        from assetcore.permissions import ac_asset_query
        internal = _ensure_dash_user(
            "ktv_internal_dashperm@example.com", "KTV DashPerm",
            "PM User", "Repair User", "Calibration User", "Corrective User",
        )
        auditor = _ensure_dash_user(
            "auditor_dashperm@example.com", "Auditor DashPerm", "AssetCore Auditor")
        frappe.db.commit()
        try:
            frappe.set_user("Administrator")
            admin_total = self._overview()["assets"]["total"]

            # Predicate phải rỗng (read-all) cho cả hai persona.
            self.assertEqual(ac_asset_query(internal), "",
                             "KTV nội bộ → predicate rỗng (read-all)")
            self.assertEqual(ac_asset_query(auditor), "",
                             "Auditor → predicate rỗng (read-all)")

            frappe.set_user(internal)
            internal_total = self._overview()["assets"]["total"]
            frappe.set_user(auditor)
            auditor_total = self._overview()["assets"]["total"]
            frappe.set_user("Administrator")

            self.assertEqual(internal_total, admin_total,
                             "Internal tech read-all → count == Admin")
            self.assertEqual(auditor_total, admin_total,
                             "Auditor read-all → count == Admin")
        finally:
            frappe.set_user("Administrator")
            for email in ("ktv_internal_dashperm@example.com",
                          "auditor_dashperm@example.com"):
                if frappe.db.exists("User", email):
                    frappe.delete_doc("User", email, force=True, ignore_permissions=True)
            frappe.db.commit()

    # ── Guard: _count branches on the hook-set (SSoT, no hardcode drift) ─────
    def test_tc_dash_perm_06_scoped_set_derived_from_hooks_py(self):
        """SSoT guard: _perm_scoped_doctypes() = giao(candidate dashboard, hook-set
        hooks.py). frappe.get_hooks trả MERGED set (gồm core Frappe doctype) nên ta
        assert (a) 5 AssetCore doctype CÓ mặt trong hook-set và (b)
        _perm_scoped_doctypes() == đúng 5 đó. Nếu ai gỡ hook 1 doctype trong
        hooks.py → assert fail → buộc đồng bộ (chống drift hardcode)."""
        expected = {"AC Asset", "PM Work Order", "Incident Report",
                    "Asset Repair", "Asset Commissioning"}
        hooked = set(frappe.get_hooks("permission_query_conditions").keys())
        # (a) cả 5 doctype AssetCore PHẢI có permission_query_conditions hook.
        self.assertTrue(
            expected <= hooked,
            f"hooks.py thiếu permission_query_conditions cho: {expected - hooked}",
        )
        # (b) helper SSoT giao đúng 5 (không nhiều hơn, không ít hơn).
        from assetcore.api import dashboard as dash_mod
        scoped = dash_mod._perm_scoped_doctypes()
        self.assertEqual(scoped, expected,
                         "_perm_scoped_doctypes() phải == 5 doctype hooked AssetCore (SSoT)")


def _ensure_dash_user(email: str, first_name: str, *roles: str) -> str:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    u = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "send_welcome_email": 0,
        "enabled": 1,
    }).insert(ignore_permissions=True)
    if roles:
        u.add_roles(*roles)
    return u.name


def _insert_dash_asset(data: dict):
    """Insert AC Asset bypassing the lifecycle workflow (test fixture)."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
