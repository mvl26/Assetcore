# Copyright (c) 2026, AssetCore Team
"""IMM-01 test suite — scoring & priority formula.

Run: bench --site miyano run-tests --app assetcore --module assetcore.tests.test_imm01

Covers BR-01-04 (G02): weighted priority score formula and priority class
classification per `docs/imm-01/02_Analysis_Design.md`.
"""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from assetcore.services.imm01 import (
    DEFAULT_PRIORITY_WEIGHTS,
    _classify_priority,
    _compute_priority_score,
    _validate_device_target,
    _validate_gate_g01,
    _validate_gate_g02,
    _validate_gate_g03,
    _validate_gate_g05,
    _vr04_target_year,
    _vr05_score_consistency,
)
from assetcore.services.shared import ErrorCode, ServiceError
from frappe.utils import getdate, today


def _make_doc(scoring_rows: list[dict]) -> SimpleNamespace:
    """Tạo doc giả tối thiểu — không cần DB để test thuần công thức."""
    rows = [SimpleNamespace(**r) for r in scoring_rows]
    return SimpleNamespace(
        scoring_rows=rows,
        weighted_score=None,
        priority_class=None,
    )


class TestPriorityClassification(unittest.TestCase):
    """`_classify_priority(score)` ranges per BR-01-04."""

    def test_p1_threshold(self):
        self.assertEqual(_classify_priority(4.0), "P1")
        self.assertEqual(_classify_priority(4.5), "P1")
        self.assertEqual(_classify_priority(5.0), "P1")

    def test_p2_threshold(self):
        self.assertEqual(_classify_priority(3.0), "P2")
        self.assertEqual(_classify_priority(3.99), "P2")

    def test_p3_threshold(self):
        self.assertEqual(_classify_priority(2.0), "P3")
        self.assertEqual(_classify_priority(2.99), "P3")

    def test_p4_threshold(self):
        self.assertEqual(_classify_priority(0.5), "P4")
        self.assertEqual(_classify_priority(1.99), "P4")

    def test_zero_or_negative(self):
        self.assertIsNone(_classify_priority(0.0))
        self.assertIsNone(_classify_priority(-1.0))


class TestComputePriorityScore(unittest.TestCase):
    """`_compute_priority_score(doc)` — weighted sum theo DEFAULT_PRIORITY_WEIGHTS.

    Trọng số mặc định:
      clinical_impact=0.25, risk=0.20, utilization_gap=0.15,
      replacement_signal=0.15, compliance_gap=0.15, budget_fit=0.10
    """

    def test_all_max_yields_5(self):
        doc = _make_doc([
            {"criterion": k, "score": 5, "weight_pct": None, "weighted": None}
            for k in DEFAULT_PRIORITY_WEIGHTS
        ])
        _compute_priority_score(doc)
        self.assertEqual(doc.weighted_score, 5.0)
        self.assertEqual(doc.priority_class, "P1")

    def test_all_zero_yields_zero(self):
        doc = _make_doc([
            {"criterion": k, "score": 0, "weight_pct": None, "weighted": None}
            for k in DEFAULT_PRIORITY_WEIGHTS
        ])
        _compute_priority_score(doc)
        self.assertEqual(doc.weighted_score, 0.0)
        self.assertIsNone(doc.priority_class)

    def test_brd_example_from_us_01_010(self):
        """US-01-010: clinical=5 risk=5 util_gap=4 replacement=5 compliance=3 budget_fit=3
        → expected: 5*.25 + 5*.20 + 4*.15 + 5*.15 + 3*.15 + 3*.10 = 4.35
        (doc viết 4.30 là approximation; code spec là 4.35).
        """
        doc = _make_doc([
            {"criterion": "clinical_impact",    "score": 5, "weight_pct": None, "weighted": None},
            {"criterion": "risk",               "score": 5, "weight_pct": None, "weighted": None},
            {"criterion": "utilization_gap",    "score": 4, "weight_pct": None, "weighted": None},
            {"criterion": "replacement_signal", "score": 5, "weight_pct": None, "weighted": None},
            {"criterion": "compliance_gap",     "score": 3, "weight_pct": None, "weighted": None},
            {"criterion": "budget_fit",         "score": 3, "weight_pct": None, "weighted": None},
        ])
        _compute_priority_score(doc)
        self.assertAlmostEqual(doc.weighted_score, 4.35, places=4)
        self.assertEqual(doc.priority_class, "P1")

    def test_row_weight_pct_and_weighted_populated(self):
        doc = _make_doc([
            {"criterion": "clinical_impact", "score": 4, "weight_pct": None, "weighted": None},
        ])
        _compute_priority_score(doc)
        row = doc.scoring_rows[0]
        self.assertEqual(row.weight_pct, 25.0)
        self.assertAlmostEqual(row.weighted, 1.0, places=4)

    def test_unknown_criterion_has_zero_weight(self):
        doc = _make_doc([
            {"criterion": "unknown_xyz", "score": 5, "weight_pct": None, "weighted": None},
        ])
        _compute_priority_score(doc)
        self.assertEqual(doc.weighted_score, 0.0)

    def test_empty_rows_yields_zero(self):
        doc = _make_doc([])
        _compute_priority_score(doc)
        self.assertEqual(doc.weighted_score, 0.0)
        self.assertIsNone(doc.priority_class)

    def test_weights_sum_to_one(self):
        """Sanity check: trọng số mặc định cộng dồn = 1.0."""
        self.assertAlmostEqual(sum(DEFAULT_PRIORITY_WEIGHTS.values()), 1.0, places=4)


class TestValidateDeviceTarget(unittest.TestCase):
    """Slide 10 — device_category bắt buộc, device_model_ref tùy chọn."""

    def test_category_only_ok(self):
        """Chỉ có category → hợp lệ (model là tùy chọn)."""
        doc = SimpleNamespace(device_category="CAT-XRAY", device_model_ref=None)
        _validate_device_target(doc)  # must not raise
        self.assertEqual(doc.device_category, "CAT-XRAY")

    def test_nothing_set_rejects(self):
        """Không category, không model → reject với lỗi VN rõ ràng."""
        doc = SimpleNamespace(device_category=None, device_model_ref=None)
        with self.assertRaises(ServiceError) as ctx:
            _validate_device_target(doc)
        self.assertIn("Nhóm thiết bị", str(ctx.exception.message))


class TestTargetYear(unittest.TestCase):
    """`_vr04_target_year(doc)` — VR-01-04: target_year ≥ năm hiện tại."""

    def setUp(self):
        self.current_year = getdate(today()).year

    def test_current_year_passes(self):
        _vr04_target_year(SimpleNamespace(target_year=self.current_year))  # no raise

    def test_future_year_passes(self):
        _vr04_target_year(SimpleNamespace(target_year=self.current_year + 1))

    def test_past_year_rejects(self):
        with self.assertRaises(ServiceError) as ctx:
            _vr04_target_year(SimpleNamespace(target_year=self.current_year - 1))
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("VR-01-04", str(ctx.exception.message))

    def test_none_rejects(self):
        with self.assertRaises(ServiceError) as ctx:
            _vr04_target_year(SimpleNamespace(target_year=None))
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)


class TestScoreConsistency(unittest.TestCase):
    """`_vr05_score_consistency(doc)` — sai số > 0.01 → VALIDATION."""

    def test_empty_rows_ok(self):
        _vr05_score_consistency(SimpleNamespace(scoring_rows=[], weighted_score=None))

    def test_within_tolerance_passes(self):
        rows = [SimpleNamespace(weighted=1.0), SimpleNamespace(weighted=2.0)]
        _vr05_score_consistency(SimpleNamespace(scoring_rows=rows, weighted_score=3.005))

    def test_exceeds_tolerance_rejects(self):
        rows = [SimpleNamespace(weighted=1.0), SimpleNamespace(weighted=2.0)]
        with self.assertRaises(ServiceError) as ctx:
            _vr05_score_consistency(SimpleNamespace(scoring_rows=rows, weighted_score=3.5))
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("VR-01-05", str(ctx.exception.message))

    def test_none_weighted_treated_as_zero(self):
        rows = [SimpleNamespace(weighted=None), SimpleNamespace(weighted=None)]
        _vr05_score_consistency(SimpleNamespace(scoring_rows=rows, weighted_score=None))


_LONG_JUSTIFICATION = "a" * 250


class TestGateG01(unittest.TestCase):
    """`_validate_gate_g01(doc)` — clinical_justification ≥ 200 + utilization_pct_12m
    bắt buộc khi Replacement/Upgrade."""

    def test_new_with_long_justification_passes(self):
        _validate_gate_g01(SimpleNamespace(
            clinical_justification=_LONG_JUSTIFICATION,
            request_type="New",
            utilization_pct_12m=None,
        ))

    def test_short_justification_rejects(self):
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g01(SimpleNamespace(
                clinical_justification="quá ngắn",
                request_type="New",
                utilization_pct_12m=None,
            ))
        self.assertEqual(ctx.exception.code, ErrorCode.VALIDATION)
        self.assertIn("VR-01-03", str(ctx.exception.message))

    def test_replacement_without_utilization_rejects(self):
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g01(SimpleNamespace(
                clinical_justification=_LONG_JUSTIFICATION,
                request_type="Replacement",
                utilization_pct_12m=None,
            ))
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("utilization_pct_12m", str(ctx.exception.message))

    def test_replacement_with_zero_utilization_passes(self):
        """utilization_pct_12m=0 (đo được, value = 0) phải pass — chỉ None mới reject."""
        _validate_gate_g01(SimpleNamespace(
            clinical_justification=_LONG_JUSTIFICATION,
            request_type="Replacement",
            utilization_pct_12m=0,
        ))

    def test_upgrade_with_utilization_passes(self):
        _validate_gate_g01(SimpleNamespace(
            clinical_justification=_LONG_JUSTIFICATION,
            request_type="Upgrade",
            utilization_pct_12m=85.5,
        ))


class TestGateG02(unittest.TestCase):
    """`_validate_gate_g02(doc)` — phải có đủ 6 tiêu chí scoring."""

    def _doc(self, criteria: list[str]):
        return SimpleNamespace(
            scoring_rows=[SimpleNamespace(criterion=c) for c in criteria],
        )

    def test_all_six_passes(self):
        _validate_gate_g02(self._doc(list(DEFAULT_PRIORITY_WEIGHTS.keys())))

    def test_five_of_six_rejects(self):
        partial = list(DEFAULT_PRIORITY_WEIGHTS.keys())[:5]
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g02(self._doc(partial))
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("G02", str(ctx.exception.message))

    def test_empty_rejects(self):
        with self.assertRaises(ServiceError):
            _validate_gate_g02(self._doc([]))


class TestGateG03(unittest.TestCase):
    """`_validate_gate_g03(doc)` — total_capex > 0 + đủ OPEX 5 năm (year_offset 1..5)."""

    def _doc(self, capex, opex_years):
        lines = []
        for y in opex_years:
            lines.append(SimpleNamespace(budget_section="OPEX", year_offset=y))
        return SimpleNamespace(total_capex=capex, budget_lines=lines)

    def test_happy_full_opex_passes(self):
        _validate_gate_g03(self._doc(100_000.0, [1, 2, 3, 4, 5]))

    def test_zero_capex_rejects(self):
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g03(self._doc(0, [1, 2, 3, 4, 5]))
        self.assertIn("CAPEX", str(ctx.exception.message))

    def test_missing_one_opex_year_rejects(self):
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g03(self._doc(50_000.0, [1, 2, 3, 5]))  # thiếu year 4
        self.assertIn("OPEX 5 năm", str(ctx.exception.message))
        self.assertIn("4", str(ctx.exception.message))

    def test_no_opex_rejects(self):
        with self.assertRaises(ServiceError):
            _validate_gate_g03(self._doc(50_000.0, []))


class TestGateG05(unittest.TestCase):
    """`_validate_gate_g05(doc)` — funding_source + board_approver bắt buộc trước Submit."""

    def test_both_set_passes(self):
        _validate_gate_g05(SimpleNamespace(funding_source="NSNN", board_approver="vp@hospital.vn"))

    def test_missing_funding_rejects(self):
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g05(SimpleNamespace(funding_source=None, board_approver="vp@hospital.vn"))
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertIn("funding_source", str(ctx.exception.message))

    def test_missing_approver_rejects(self):
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g05(SimpleNamespace(funding_source="NSNN", board_approver=None))
        self.assertIn("board_approver", str(ctx.exception.message))

    def test_both_missing_lists_both(self):
        with self.assertRaises(ServiceError) as ctx:
            _validate_gate_g05(SimpleNamespace(funding_source=None, board_approver=""))
        msg = str(ctx.exception.message)
        self.assertIn("funding_source", msg)
        self.assertIn("board_approver", msg)


class TestCreateProcurementPlanGate(unittest.TestCase):
    """LL-BE-24: `create_procurement_plan` PHẢI gate `needs.create` ở BE,
    không tin FE hide. Verify gate được gọi đúng capability + short-circuit
    creation khi thiếu quyền (envelope FORBIDDEN), không tạo doc."""

    def test_capability_maps_to_needs_create(self):
        """Capability string FE/BE khớp + resolve đúng DocType+ptype."""
        from assetcore.services.shared import rbac
        self.assertIn("needs.create", rbac.CAPABILITY_MAP)
        self.assertEqual(
            rbac.CAPABILITY_MAP["needs.create"], ("IMM Needs Request", "create")
        )

    def test_create_calls_rbac_require_before_insert(self):
        """Gate phải invoke rbac.require('needs.create') TRƯỚC khi tạo doc;
        thiếu quyền → PermissionError (Frappe → HTTP 403), KHÔNG có doc nào
        được tạo. Theo convention imm05 (AUTH-02): gate nằm ngoài _handle,
        PermissionError propagate cho framework."""
        import frappe
        from assetcore.api import imm01 as api
        from assetcore.services.shared import rbac

        called: dict = {}
        orig_require = rbac.require

        def fake_require(cap, doc=None):
            called["cap"] = cap
            raise frappe.PermissionError("blocked for test")

        before = frappe.db.count("IMM Procurement Plan")
        rbac.require = fake_require
        try:
            with self.assertRaises(frappe.PermissionError):
                api.create_procurement_plan(2098, "Q2", 0)
        finally:
            rbac.require = orig_require

        # Gate invoked với đúng capability
        self.assertEqual(called.get("cap"), "needs.create")
        # Gate raise TRƯỚC insert → tổng số plan không đổi (không tạo doc rác)
        self.assertEqual(
            frappe.db.count("IMM Procurement Plan"), before,
            "Gate phải short-circuit TRƯỚC khi insert — không được tạo doc",
        )


class TestApprovePlanGuard(unittest.TestCase):
    """Bug PP-26-00010: duyệt kế hoạch mua sắm RỖNG (0 đề xuất) ném raw Frappe
    'Workflow State transition not allowed from <strong>Draft</strong> to
    <strong>Approved</strong>'.

    Luồng đúng: đề xuất (Needs Request) duyệt trước → đưa vào kế hoạch → mới
    phê duyệt kế hoạch. Yêu cầu BE-guard slice:
      (1) chặn duyệt kế hoạch RỖNG bằng thông báo VI sạch (VALIDATION) —
          fail-fast TRƯỚC khi đổi workflow_state (kế hoạch giữ Draft);
      (2) người dùng KHÔNG đủ vai trò duyệt (không phải Procurement/
          Commissioning Manager) → thông báo VI sạch (FORBIDDEN);
    cả 2 KHÔNG để raw HTML '<strong>' / 'transition not allowed' của Frappe lọt ra.
    """

    DT = "IMM Procurement Plan"

    @classmethod
    def setUpClass(cls):
        import frappe
        frappe.set_user("Administrator")

    def tearDown(self):
        import frappe
        frappe.set_user("Administrator")

    def _make_plan(self, year, period="Q1", budget=1_000_000):
        # Dựng kế hoạch RỖNG trực tiếp (bypass API). Sau khi create_procurement_plan
        # bắt buộc ≥1 đề xuất, không thể tạo plan rỗng qua API — nhưng approve-guard
        # vẫn phải phòng thủ với plan rỗng (legacy / đã gỡ hết đề xuất), nên fixture
        # dựng thẳng doc để test đúng nhánh đó.
        import frappe
        doc = frappe.new_doc(self.DT)
        doc.plan_year = year
        doc.plan_period = period
        doc.budget_envelope = float(budget)
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        self.addCleanup(self._purge_plan, doc.name)
        return doc.name

    def _purge_plan(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self.DT, name):
            frappe.delete_doc(self.DT, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_nr(self, year):
        """NR Draft tối thiểu (ignore_links → bỏ qua AC Department/Category) chỉ
        để plan_items.needs_request có link HỢP LỆ (vượt link-validation lúc
        _approve_plan save)."""
        import frappe
        nr = frappe.new_doc("IMM Needs Request")
        nr.request_date = frappe.utils.today()
        nr.request_type = "New"
        nr.requesting_department = "_TEST-PP-DEPT"
        nr.device_category = "_TEST-PP-CAT"
        nr.quantity = 1
        nr.target_year = year
        nr.clinical_justification = "Test NR cho approve-plan guard — đủ ký tự."
        nr.flags.ignore_links = True
        nr.insert(ignore_permissions=True)
        frappe.db.commit()
        self.addCleanup(
            lambda: frappe.delete_doc(
                "IMM Needs Request", nr.name, force=True, ignore_permissions=True))
        return nr.name

    def _ensure_user(self, email, roles):
        import frappe
        if not frappe.db.exists("User", email):
            frappe.get_doc({
                "doctype": "User", "email": email,
                "first_name": email.split("@")[0],
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        doc = frappe.get_doc("User", email)
        existing = {r.role for r in doc.get("roles", [])}
        for r in roles:
            if r not in existing:
                doc.append("roles", {"role": r})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        from assetcore.services.shared import rbac as _rbac
        if hasattr(_rbac, "invalidate_capabilities"):
            _rbac.invalidate_capabilities(email)
        return email

    def test_approve_empty_plan_blocked_clean_validation(self):
        import frappe
        from assetcore.api import imm01 as api
        name = self._make_plan(2097)
        with self.assertRaises(ServiceError) as cm:
            api._approve_plan(name)
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)
        msg = (cm.exception.message or "").lower()
        self.assertNotIn("<strong>", msg)
        self.assertNotIn("transition not allowed", msg)
        # Fail-fast: kế hoạch KHÔNG bị duyệt rỗng — vẫn Draft.
        self.assertEqual(frappe.db.get_value(self.DT, name, "workflow_state"), "Draft")

    def test_approve_nonempty_plan_wrong_role_clean_forbidden(self):
        import frappe
        from assetcore.api import imm01 as api
        name = self._make_plan(2096)
        nr = self._make_nr(2096)
        # Thêm 1 đề xuất → vượt guard rỗng. State giữ Draft (Draft→Draft, không
        # transition) nên Administrator save OK; link needs_request HỢP LỆ (NR thật).
        plan = frappe.get_doc(self.DT, name)
        plan.append("plan_items", {"needs_request": nr, "allocated_budget": 100})
        plan.save(ignore_permissions=True)
        frappe.db.commit()
        # User đọc/sửa được plan (Needs Manager) nhưng KHÔNG có vai trò duyệt
        # (Procurement/Commissioning Manager) → Frappe ném WorkflowPermissionError.
        usr = self._ensure_user("pp_needsmgr@test.local", ["Needs Manager"])
        frappe.set_user(usr)
        try:
            with self.assertRaises(ServiceError) as cm:
                api._approve_plan(name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        self.assertNotIn("<strong>", (cm.exception.message or "").lower())
        self.assertEqual(frappe.db.get_value(self.DT, name, "workflow_state"), "Draft")

    def test_activate_wrong_role_clean_forbidden(self):
        """Kích hoạt (Approved→Active) bởi user KHÔNG có vai trò duyệt (Needs
        Manager) → ServiceError(FORBIDDEN) SẠCH, KHÔNG raw WorkflowPermissionError."""
        import frappe
        from assetcore.api import imm01 as api
        name = self._make_plan(2092)
        frappe.db.set_value(self.DT, name, "workflow_state", "Approved")
        frappe.db.commit()
        usr = self._ensure_user("pp_needsuser@test.local", ["Needs User"])
        frappe.set_user(usr)
        try:
            with self.assertRaises(ServiceError) as cm:
                api._activate_plan(name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        self.assertNotIn("<strong>", (cm.exception.message or "").lower())

    def test_close_wrong_role_clean_forbidden(self):
        """Đóng (Active→Closed) bởi user KHÔNG có vai trò (Commissioning Manager)
        → ServiceError(FORBIDDEN) SẠCH, KHÔNG raw WorkflowPermissionError."""
        import frappe
        from assetcore.api import imm01 as api
        name = self._make_plan(2091)
        frappe.db.set_value(self.DT, name, "workflow_state", "Active")
        frappe.db.commit()
        usr = self._ensure_user("pp_needsuser@test.local", ["Needs User"])
        frappe.set_user(usr)
        try:
            with self.assertRaises(ServiceError) as cm:
                api._close_plan(name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        self.assertNotIn("<strong>", (cm.exception.message or "").lower())


class TestCreatePlanRequiresProposals(unittest.TestCase):
    """Proposal-first (QĐ USER): create_procurement_plan PHẢI có ≥1 đề xuất
    (Needs Request đã Approved) và tạo kèm dòng trong MỘT thao tác — không bao
    giờ tồn tại kế hoạch RỖNG. NR chưa Approved → chặn (BUSINESS_RULE). Luồng
    đúng = đề xuất duyệt trước → chọn đề xuất rồi tạo kế hoạch."""

    DT = "IMM Procurement Plan"
    NR = "IMM Needs Request"

    @classmethod
    def setUpClass(cls):
        import frappe
        frappe.set_user("Administrator")

    def _make_nr(self, year, *, approved: bool):
        import frappe
        nr = frappe.new_doc(self.NR)
        nr.request_date = frappe.utils.today()
        nr.request_type = "New"
        nr.requesting_department = "_TEST-PP-DEPT"
        nr.device_category = "_TEST-PP-CAT"
        nr.quantity = 1
        nr.target_year = year
        nr.clinical_justification = "Test NR cho create-plan — đủ ký tự mô tả."
        nr.flags.ignore_links = True
        nr.insert(ignore_permissions=True)
        if approved:
            # Đánh dấu Approved cho fixture (bypass workflow) — append-rule chỉ đọc
            # docstatus + workflow_state qua get_doc.
            frappe.db.set_value(self.NR, nr.name, {"docstatus": 1,
                                                   "workflow_state": "Approved"})
        frappe.db.commit()
        self.addCleanup(self._purge_nr, nr.name)
        return nr.name

    def _purge_nr(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self.NR, name):
            # docstatus=1 (fixture Approved) không xoá trực tiếp được → hạ về 0.
            frappe.db.set_value(self.NR, name, "docstatus", 0)
            frappe.delete_doc(self.NR, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _purge_plan(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self.DT, name):
            frappe.delete_doc(self.DT, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_create_without_proposals_blocked_validation(self):
        import frappe
        from assetcore.api import imm01 as api
        before = frappe.db.count(self.DT)
        with self.assertRaises(ServiceError) as cm:
            api._create_procurement_plan(2095, "Q1", 1_000_000, "[]")
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)
        self.assertNotIn("<strong>", (cm.exception.message or "").lower())
        self.assertEqual(frappe.db.count(self.DT), before,
                         "Không được tạo kế hoạch RỖNG (no đề xuất)")

    def test_create_with_unapproved_nr_blocked_business_rule(self):
        import frappe
        import json
        from assetcore.api import imm01 as api
        nr = self._make_nr(2094, approved=False)
        before = frappe.db.count(self.DT)
        with self.assertRaises(ServiceError) as cm:
            api._create_procurement_plan(2094, "Q1", 1_000_000, json.dumps([nr]))
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)
        self.assertEqual(frappe.db.count(self.DT), before,
                         "NR chưa Approved → không tạo plan")

    def test_create_with_approved_nr_builds_plan_with_line(self):
        import frappe
        import json
        from assetcore.api import imm01 as api
        nr = self._make_nr(2093, approved=True)
        res = api._create_procurement_plan(2093, "Q1", 1_000_000, json.dumps([nr]))
        self.addCleanup(self._purge_plan, res["name"])
        plan = frappe.get_doc(self.DT, res["name"])
        self.assertEqual(len(plan.plan_items), 1, "Plan phải được tạo KÈM 1 dòng đề xuất")
        self.assertEqual(plan.plan_items[0].needs_request, nr)
        self.assertEqual(plan.workflow_state, "Draft")
