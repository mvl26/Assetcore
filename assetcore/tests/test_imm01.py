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


class TestPlanDetailAllowedTransitions(unittest.TestCase):
    """IMM-01 GATE-8 / LL-FE-51 — `get_procurement_plan` phải emit
    ``allowed_transitions`` (server-driven CTA gating).

    FE (ProcurementPlanDetailView) chỉ render nút Phê duyệt/Kích hoạt/Đóng khi
    action nằm trong list này ⇒ triệt tiêu kịch bản "nút hiện rồi bấm mới báo
    Bạn không có quyền" (khiếu nại QTV duyệt kế hoạch).

    Contract (naming với FE): payload['allowed_transitions'] = list[str] action
    ĐÃ DEDUPE, tính bằng ``frappe.model.workflow.get_transitions`` trên IMM
    Procurement Plan (tự lọc theo state hiện tại + role của user gọi). Action
    khớp EXACT workflow.json (IMM-01 Plan Workflow), vd: 'Phê duyệt kế hoạch'.
    """

    DT = "IMM Procurement Plan"
    APPROVE_ACTION = "Phê duyệt kế hoạch"

    @classmethod
    def setUpClass(cls):
        import frappe
        frappe.set_user("Administrator")

    def tearDown(self):
        import frappe
        frappe.set_user("Administrator")

    def _make_draft_plan(self, year, period="Q1"):
        # Kế hoạch RỖNG ở Draft (bậc thang transition đầu) — đủ để đo allowed_transitions.
        import frappe
        doc = frappe.new_doc(self.DT)
        doc.plan_year = year
        doc.plan_period = period
        doc.budget_envelope = 1_000_000
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        self.addCleanup(self._purge_plan, doc.name)
        self.assertEqual(doc.workflow_state, "Draft")  # sanity: workflow default state
        return doc.name

    def _purge_plan(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self.DT, name):
            frappe.delete_doc(self.DT, name, force=True, ignore_permissions=True)
        frappe.db.commit()

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
        frappe.clear_cache(user=email)  # tránh stale role-cache nếu user tồn dư từ run trước
        self.addCleanup(self._purge_user, email)
        return email

    def _purge_user(self, email):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _allowed_as(self, user, name):
        """allowed_transitions của payload get_procurement_plan khi gọi bởi ``user``."""
        import frappe
        from assetcore.api import imm01 as api
        frappe.set_user(user)
        try:
            payload = api._get_procurement_plan(name)
        finally:
            frappe.set_user("Administrator")
        self.assertIn("allowed_transitions", payload,
                      "payload PHẢI có field allowed_transitions (server-driven CTA)")
        self.assertIsInstance(payload["allowed_transitions"], list)
        return payload["allowed_transitions"]

    def test_get_plan_payload_includes_allowed_transitions(self):
        """Draft plan + user có vai trò TRANSITION 'Procurement Manager' (kèm 'Needs
        Manager' để có quyền ĐỌC — mirror persona thật 'Trưởng phòng VT-TTBYT' =
        Needs Manager + Procurement Manager + Commissioning Manager) →
        allowed_transitions CHỨA 'Phê duyệt kế hoạch'."""
        name = self._make_draft_plan(2089)
        usr = self._ensure_user(
            "pp_at_procmgr@test.local", ["Needs Manager", "Procurement Manager"])
        allowed = self._allowed_as(usr, name)
        self.assertIn(self.APPROVE_ACTION, allowed)
        # Dedupe: workflow.json có nhiều row (Procurement/Super Admin/System Manager)
        # cho cùng action ở Draft → action chỉ xuất hiện MỘT lần.
        self.assertEqual(allowed.count(self.APPROVE_ACTION), 1)

    def test_plan_transition_excluded_for_unentitled_role(self):
        """Draft plan + user CHỈ base role 'AssetCore System User' (không manager,
        không quyền transition) → 'Phê duyệt kế hoạch' KHÔNG có trong
        allowed_transitions. Base role KHÔNG có quyền đọc plan ⇒ helper degrade
        graceful về [] — payload KHÔNG vỡ (không 403/500)."""
        name = self._make_draft_plan(2088)
        usr = self._ensure_user("pp_at_base@test.local", ["AssetCore System User"])
        allowed = self._allowed_as(usr, name)
        self.assertNotIn(self.APPROVE_ACTION, allowed)

    def test_plan_transition_excluded_for_reader_without_transition_role(self):
        """Kiểm soát — gate theo TRANSITION, KHÔNG theo status literal: user CÓ
        quyền đọc plan (Needs User) nhưng KHÔNG có vai trò transition ở Draft →
        allowed_transitions = [] ⇒ 'Phê duyệt kế hoạch' KHÔNG có. Chứng minh
        inclusion do vai trò TRANSITION quyết định (không do read / không do
        workflow_state == 'Draft')."""
        name = self._make_draft_plan(2087)
        usr = self._ensure_user("pp_at_reader@test.local", ["Needs User"])
        allowed = self._allowed_as(usr, name)
        self.assertNotIn(self.APPROVE_ACTION, allowed)

    def test_plan_transition_allows_super_admin(self):
        """Regression khoá đúng khiếu nại gốc: QTV (AssetCore Super Admin) trên
        Draft plan → 'Phê duyệt kế hoạch' CÓ trong allowed_transitions (khớp
        admin-override đã khai ở fixtures/workflow.json)."""
        name = self._make_draft_plan(2086)
        usr = self._ensure_user(
            "pp_at_superadmin@test.local", ["AssetCore Super Admin"])
        allowed = self._allowed_as(usr, name)
        self.assertIn(self.APPROVE_ACTION, allowed)


# ─────────────────────────────────────────────────────────────────────────────
# Escalation phiếu nhu cầu quá hạn (BR-01-11 / ADR-IMM-01-01 / framework E7)
# TDD: viết TRƯỚC implement (CLAUDE.md §17). Spec: docs/imm-01/02_Analysis_Design.md
# BR-01-11 + ADR-IMM-01-01; recipient qua SSoT notify_roles.NEEDS_STALE_ESCALATION.
# ─────────────────────────────────────────────────────────────────────────────
class TestNeedsOverdueEscalation(unittest.TestCase):
    """`check_pending_request_overdue()` → `notify_needs_overdue()`: NR ở
    Submitted/Reviewing (docstatus=0) treo > 30 ngày kể từ `request_date` → sinh
    escalation **digest** in-app (Notification Log) + email tới MỌI user giữ role
    trong SSoT `notify_roles.NEEDS_STALE_ESCALATION` (= "Needs Manager"). Idempotent
    1 digest/người/ngày; 0 phiếu → 0 thông báo; 0 recipient → log cảnh báo KHÔNG raise.
    """

    NR = "IMM Needs Request"
    # Đồng bộ CHÍNH XÁC với notifications._NEEDS_STALE_MARKER (dedup Frappe-first).
    _MARKER = "phiếu nhu cầu quá hạn xử lý"
    _NM_USER = "stale_nm@test.local"
    _DEPT = "_TEST-STALE-DEPT"

    @classmethod
    def setUpClass(cls):
        import frappe
        frappe.set_user("Administrator")
        # User chuyên dụng giữ role thật "Needs Manager" → recipient deterministic
        # (không phụ thuộc Notification Settings của user site thật).
        if not frappe.db.exists("User", cls._NM_USER):
            frappe.get_doc({
                "doctype": "User", "email": cls._NM_USER,
                "first_name": "Stale NeedsMgr",
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
        u = frappe.get_doc("User", cls._NM_USER)
        if "Needs Manager" not in {r.role for r in u.get("roles", [])}:
            u.append("roles", {"role": "Needs Manager"})
            u.save(ignore_permissions=True)
        frappe.db.commit()
        from assetcore.services.shared import rbac as _rbac
        if hasattr(_rbac, "invalidate_capabilities"):
            _rbac.invalidate_capabilities(cls._NM_USER)

    @classmethod
    def tearDownClass(cls):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists("User", cls._NM_USER):
            frappe.delete_doc("User", cls._NM_USER, force=True, ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        import frappe
        frappe.set_user("Administrator")
        # Reset dedup 1/ngày: xoá mọi digest marker HÔM NAY (real scheduler không
        # chạy trong test) → mỗi test bắt đầu sạch, tránh dedup chéo giữa test.
        self._purge_marker_logs()

    def tearDown(self):
        import frappe
        frappe.set_user("Administrator")
        self._purge_marker_logs()

    def _purge_marker_logs(self):
        import frappe
        frappe.db.delete("Notification Log", {"subject": ("like", f"%{self._MARKER}%")})
        frappe.db.commit()

    def _marker_log_count(self):
        import frappe
        return frappe.db.count(
            "Notification Log", {"subject": ("like", f"%{self._MARKER}%")})

    def _make_overdue_nr(self, *, days_old, state="Submitted", dept=None):
        """NR Draft tối thiểu; ép `request_date` lùi `days_old` ngày + `workflow_state`
        qua db.set_value (bypass validate/workflow) để khớp đúng bộ lọc scheduler."""
        import frappe
        from frappe.utils import add_days
        nr = frappe.new_doc(self.NR)
        nr.request_date = today()
        nr.request_type = "New"
        nr.requesting_department = dept or self._DEPT
        nr.device_category = "_TEST-STALE-CAT"
        nr.quantity = 1
        nr.target_year = getdate(today()).year + 1
        nr.clinical_justification = "Test NR escalation quá hạn — đủ ký tự mô tả."
        nr.flags.ignore_links = True
        nr.insert(ignore_permissions=True)
        frappe.db.set_value(self.NR, nr.name, {
            "request_date": add_days(today(), -days_old),
            "workflow_state": state,
        }, update_modified=False)
        frappe.db.commit()
        self.addCleanup(self._purge_nr, nr.name)
        return nr.name

    def _purge_nr(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self.NR, name):
            frappe.delete_doc(self.NR, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    # ── TC1: NR quá hạn → sinh Notification Log + email tới Needs Manager ──────
    def test_stale_needs_creates_notification(self):
        import frappe
        from unittest.mock import patch
        from assetcore.services import imm01 as svc
        from assetcore.services import notifications as ntf

        nr = self._make_overdue_nr(days_old=40, state="Submitted")

        sent = {"recipients": []}

        def fake_sendmail(**kwargs):
            sent["recipients"].extend(kwargs.get("recipients") or [])

        with patch.object(ntf, "_safe_sendmail", side_effect=fake_sendmail), \
             patch.object(ntf, "_user_wants_email", return_value=True):
            svc.check_pending_request_overdue()

        logs = frappe.get_all(
            "Notification Log",
            filters={"subject": ("like", f"%{self._MARKER}%")},
            fields=["name", "for_user", "email_content", "type"],
        )
        self.assertGreaterEqual(len(logs), 1, "phải sinh ≥1 Notification Log escalation")
        self.assertTrue(all(l.type == "Alert" for l in logs), "digest type=Alert")
        recips = {l.for_user for l in logs}
        self.assertIn(self._NM_USER, recips,
                      "recipient phải gồm user giữ role Needs Manager (SSoT)")
        # message digest liệt kê mã phiếu + phòng ban (audit/traceability)
        body = next((l.email_content for l in logs if l.for_user == self._NM_USER), "")
        self.assertIn(nr, body, "digest phải liệt kê mã phiếu quá hạn")
        self.assertIn(self._DEPT, body, "digest phải breakdown theo phòng ban")
        # Email path: gửi tới recipient Needs Manager (nạp Email Queue qua sendmail)
        self.assertIn(self._NM_USER, set(sent["recipients"]),
                      "email escalation phải gửi tới recipient Needs Manager")

    # ── TC2: KHÔNG NR quá hạn → 0 thông báo, 0 email (early-return sạch) ───────
    def test_no_stale_no_notification(self):
        import frappe
        from unittest.mock import patch
        from assetcore.services import imm01 as svc
        from assetcore.services import notifications as ntf

        fresh = self._make_overdue_nr(days_old=5, state="Submitted")

        # (a) NR mới (<30 ngày) KHÔNG lọt vào rows scheduler truyền cho notify.
        captured = {"rows": None}
        with patch.object(ntf, "notify_needs_overdue",
                          side_effect=lambda rows: captured.__setitem__("rows", rows)):
            svc.check_pending_request_overdue()
        names = {r.get("name") for r in (captured["rows"] or [])}
        self.assertNotIn(fresh, names, "NR mới (<30 ngày) KHÔNG được escalation")

        # (b) early-return: 0 phiếu → 0 email, 0 Notification Log.
        before = self._marker_log_count()
        with patch.object(ntf, "_safe_sendmail") as m:
            ntf.notify_needs_overdue([])
        m.assert_not_called()
        self.assertEqual(self._marker_log_count(), before,
                         "0 phiếu quá hạn → KHÔNG sinh notification")

    # ── TC3: guard anti-RBAC-dead-gate — recipient resolve ≥1 user thật ───────
    def test_recipients_resolve_nonempty_guard(self):
        import frappe
        from assetcore.services import notifications as ntf
        from assetcore.services.shared import notify_roles

        self.assertTrue(notify_roles.NEEDS_STALE_ESCALATION,
                        "NEEDS_STALE_ESCALATION không được rỗng")
        for role in notify_roles.NEEDS_STALE_ESCALATION:
            self.assertTrue(frappe.db.exists("Role", role),
                            f"role '{role}' phải tồn tại (chống dead-gate)")
            self.assertIn(role, notify_roles.ALL_NOTIFY_ROLES,
                          f"'{role}' phải nằm trong ALL_NOTIFY_ROLES (guard test phủ)")
        recips = ntf._needs_stale_recipients()
        self.assertGreaterEqual(len(recips), 1,
                                "phải resolve ≥1 user thật giữ role escalation")
        self.assertNotIn("Administrator", recips, "Administrator phải bị loại")

    # ── TC4: idempotent — chạy 2 lần cùng ngày KHÔNG nhân đôi digest ──────────
    def test_idempotent_same_day_no_duplicate(self):
        from assetcore.services import imm01 as svc
        self._make_overdue_nr(days_old=45, state="Reviewing")
        svc.check_pending_request_overdue()
        after1 = self._marker_log_count()
        svc.check_pending_request_overdue()
        after2 = self._marker_log_count()
        self.assertGreaterEqual(after1, 1, "lần chạy 1 phải sinh ≥1 digest")
        self.assertEqual(after1, after2,
                         "chạy lại cùng ngày cùng tập NR KHÔNG được nhân đôi digest")

    # ── TC5: 0 recipient → KHÔNG raise, 0 notification, có log cảnh báo ───────
    def test_zero_recipients_no_crash(self):
        import frappe
        from unittest.mock import patch
        from assetcore.services import notifications as ntf

        warnings: list[str] = []

        class _SpyLogger:
            def warning(self, msg, *a, **k):
                warnings.append(str(msg))

            def info(self, *a, **k):
                pass

            def error(self, *a, **k):
                pass

        rows = [{"name": "NR-TEST-0001", "requesting_department": self._DEPT,
                 "request_date": "2026-01-01"}]
        before = self._marker_log_count()
        with patch.object(ntf, "get_users_with_role", return_value=[]), \
             patch.object(frappe, "logger", return_value=_SpyLogger()), \
             patch.object(ntf, "_safe_sendmail") as m:
            try:
                ntf.notify_needs_overdue(rows)
            except Exception as exc:  # noqa: BLE001
                self.fail(f"notify_needs_overdue KHÔNG được raise khi 0 recipient: {exc}")
        m.assert_not_called()
        self.assertEqual(self._marker_log_count(), before,
                         "0 recipient → KHÔNG sinh notification")
        self.assertTrue(
            any(("recipient" in w.lower()) or ("người nhận" in w.lower())
                or ("escalation" in w.lower()) for w in warnings),
            "phải ghi log cảnh báo khi 0 recipient (fail-loud, an toàn)")


class TestNeedsListOverdueEnrichment(unittest.TestCase):
    """TC-01-LIST-OVERDUE: `_enrich_needs_overdue` gắn age_days + is_overdue theo
    server-clock (SSoT overdue) — FE chỉ render, KHÔNG so ngày ở client.

    is_overdue = state ∈ {Submitted, Reviewing} và tuổi > 30 ngày (khớp KPI
    `backlog_over_30d` + scheduler `check_pending_request_overdue`).
    """

    def test_enrich_sets_age_and_overdue_flag(self):
        from frappe.utils import add_days
        from assetcore.api.imm01 import _enrich_needs_overdue

        items = [
            {"name": "NR-A", "workflow_state": "Submitted", "request_date": add_days(today(), -40)},
            {"name": "NR-B", "workflow_state": "Reviewing", "request_date": add_days(today(), -10)},
            {"name": "NR-C", "workflow_state": "Approved",  "request_date": add_days(today(), -99)},
            {"name": "NR-D", "workflow_state": "Submitted", "request_date": None},
        ]
        _enrich_needs_overdue(items)

        by = {it["name"]: it for it in items}
        # NR-A: Submitted, 40 ngày > 30 → overdue
        self.assertEqual(by["NR-A"]["age_days"], 40)
        self.assertTrue(by["NR-A"]["is_overdue"])
        # NR-B: Reviewing nhưng mới 10 ngày → không overdue
        self.assertEqual(by["NR-B"]["age_days"], 10)
        self.assertFalse(by["NR-B"]["is_overdue"])
        # NR-C: 99 ngày nhưng state Approved (không thuộc tập overdue) → không overdue
        self.assertFalse(by["NR-C"]["is_overdue"])
        # NR-D: thiếu request_date → age None, không overdue (không vỡ)
        self.assertIsNone(by["NR-D"]["age_days"])
        self.assertFalse(by["NR-D"]["is_overdue"])


# ─────────────────────────────────────────────────────────────────────────────
# GATE-8 / LL-FE-51 — server-driven CTA cho phiếu đề xuất (Needs Request):
# get_needs_request emit allowed_transitions + approve/reject enforce transition-role.
# Đóng dead-gate: FE cũ gate isBoardApprover (Dept Head/Ops Manager) desync khỏi
# role transition thật 'Phê duyệt'/'Bác đề xuất' (Procurement Manager / AssetCore
# Super Admin / System Manager theo fixtures/workflow.json).
# TDD: viết TRƯỚC implement (CLAUDE.md §17).
# ─────────────────────────────────────────────────────────────────────────────
class TestNeedsRequestAllowedTransitions(unittest.TestCase):
    """`get_needs_request` PHẢI emit `allowed_transitions` (list[str] action ĐÃ
    DEDUPE) — FE (NeedsRequestDetailView) gate nút Phê duyệt/Bác đề xuất theo list
    này, KHÔNG theo isBoardApprover role-list hay workflow_state literal.

    Persona duyệt = Needs Manager (đọc NR) + Procurement Manager (role transition
    'Phê duyệt'/'Bác đề xuất') — mirror 'Trưởng phòng VT-TTBYT'. KHÔNG có Dept
    Head/Ops Manager/System Manager.
    """

    NR = "IMM Needs Request"
    APPROVE = "Phê duyệt"
    REJECT = "Bác đề xuất"

    @classmethod
    def setUpClass(cls):
        import frappe
        frappe.set_user("Administrator")

    def tearDown(self):
        import frappe
        frappe.set_user("Administrator")

    def _make_pending_nr(self, year):
        """NR ở 'Pending Approval' (docstatus=0). ignore_links → bỏ qua AC
        Department/Category (helper allowed_transitions read-only, không submit)."""
        import frappe
        nr = frappe.new_doc(self.NR)
        nr.request_date = frappe.utils.today()
        nr.request_type = "New"
        nr.requesting_department = "_TEST-NRCTA-DEPT"
        nr.device_category = "_TEST-NRCTA-CAT"
        nr.quantity = 1
        nr.target_year = year
        nr.funding_source = "NSNN"
        nr.clinical_justification = "Test NR cho allowed_transitions — đủ ký tự."
        nr.flags.ignore_links = True
        nr.insert(ignore_permissions=True)
        frappe.db.set_value(self.NR, nr.name, "workflow_state", "Pending Approval",
                            update_modified=False)
        frappe.db.commit()
        self.addCleanup(self._purge_nr, nr.name)
        return nr.name

    def _purge_nr(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self.NR, name):
            frappe.db.set_value(self.NR, name, "docstatus", 0)
            frappe.delete_doc(self.NR, name, force=True, ignore_permissions=True)
        frappe.db.commit()

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
        frappe.clear_cache(user=email)
        from assetcore.services.shared import rbac as _rbac
        if hasattr(_rbac, "invalidate_capabilities"):
            _rbac.invalidate_capabilities(email)
        self.addCleanup(self._purge_user, email)
        return email

    def _purge_user(self, email):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _allowed_as(self, user, name):
        import frappe
        from assetcore.api import imm01 as api
        frappe.set_user(user)
        try:
            payload = api._get_needs_request(name)
        finally:
            frappe.set_user("Administrator")
        self.assertIn("allowed_transitions", payload,
                      "payload PHẢI có field allowed_transitions (server-driven CTA)")
        self.assertIsInstance(payload["allowed_transitions"], list)
        return payload["allowed_transitions"]

    def test_procurement_manager_sees_approve_and_reject(self):
        name = self._make_pending_nr(2090)
        usr = self._ensure_user(
            "nrcta_procmgr@test.local", ["Needs Manager", "Procurement Manager"])
        allowed = self._allowed_as(usr, name)
        self.assertIn(self.APPROVE, allowed)
        self.assertIn(self.REJECT, allowed)
        # Dedupe: workflow.json có nhiều row (Procurement/Super Admin/System Manager)
        # cho cùng action ở Pending Approval → action chỉ xuất hiện MỘT lần.
        self.assertEqual(allowed.count(self.APPROVE), 1)
        self.assertEqual(allowed.count(self.REJECT), 1)

    def test_reader_without_transition_role_excluded(self):
        """Gate theo TRANSITION, KHÔNG theo status literal: Needs Manager đọc được
        NR ở Pending Approval nhưng KHÔNG có role transition 'Phê duyệt' →
        allowed_transitions KHÔNG chứa 'Phê duyệt'/'Bác đề xuất' (hết false-permissive)."""
        name = self._make_pending_nr(2089)
        usr = self._ensure_user("nrcta_needsmgr@test.local", ["Needs Manager"])
        allowed = self._allowed_as(usr, name)
        self.assertNotIn(self.APPROVE, allowed)
        self.assertNotIn(self.REJECT, allowed)

    def test_super_admin_sees_approve(self):
        """Regression admin-override: QTV (AssetCore Super Admin) → 'Phê duyệt' CÓ
        trong allowed_transitions (workflow.json khai Super Admin cho transition)."""
        name = self._make_pending_nr(2088)
        usr = self._ensure_user(
            "nrcta_superadmin@test.local", ["AssetCore Super Admin"])
        allowed = self._allowed_as(usr, name)
        self.assertIn(self.APPROVE, allowed)


class TestNeedsRequestApproveRejectRbac(unittest.TestCase):
    """`approve_needs_request` / `reject_needs_request` PHẢI từ chối FORBIDDEN(403)
    user KHÔNG nằm trong allowed roles của transition (đóng lỗ set workflow_state
    trực tiếp bỏ qua kiểm role). Procurement Manager approve được (regression xanh).
    """

    NR = "IMM Needs Request"

    @classmethod
    def setUpClass(cls):
        import frappe
        frappe.set_user("Administrator")
        # Dept + Category THẬT để NR submit được (approve → doc.submit() re-validate
        # link). autoname series → capture name thật.
        dept = frappe.new_doc("AC Department")
        dept.department_name = "_Test NR-RBAC Dept"
        dept.insert(ignore_permissions=True)
        cls._dept = dept.name
        cat = frappe.new_doc("AC Asset Category")
        cat.category_name = "_Test NR-RBAC Cat"
        cat.insert(ignore_permissions=True)
        cls._cat = cat.name
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        import frappe
        frappe.set_user("Administrator")
        for dt, nm in (("AC Department", getattr(cls, "_dept", None)),
                       ("AC Asset Category", getattr(cls, "_cat", None))):
            if nm and frappe.db.exists(dt, nm):
                frappe.delete_doc(dt, nm, force=True, ignore_permissions=True)
        frappe.db.commit()

    def tearDown(self):
        import frappe
        frappe.set_user("Administrator")

    def _make_pending_nr(self, year):
        """NR ở 'Pending Approval' (docstatus=0) với dept/cat THẬT (link hợp lệ) +
        funding_source (gate G05 trước submit)."""
        import frappe
        nr = frappe.new_doc(self.NR)
        nr.request_date = frappe.utils.today()
        nr.request_type = "New"
        nr.requesting_department = self._dept
        nr.device_category = self._cat
        nr.quantity = 1
        nr.target_year = year
        nr.funding_source = "NSNN"
        nr.clinical_justification = "Test NR RBAC approve/reject — đủ ký tự mô tả."
        nr.insert(ignore_permissions=True)
        frappe.db.set_value(self.NR, nr.name, "workflow_state", "Pending Approval",
                            update_modified=False)
        frappe.db.commit()
        self.addCleanup(self._purge_nr, nr.name)
        return nr.name

    def _purge_nr(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self.NR, name):
            frappe.db.set_value(self.NR, name, "docstatus", 0)
            frappe.delete_doc(self.NR, name, force=True, ignore_permissions=True)
        frappe.db.commit()

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
        frappe.clear_cache(user=email)
        from assetcore.services.shared import rbac as _rbac
        if hasattr(_rbac, "invalidate_capabilities"):
            _rbac.invalidate_capabilities(email)
        self.addCleanup(self._purge_user, email)
        return email

    def _purge_user(self, email):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def test_approve_wrong_role_forbidden(self):
        """Needs Manager (đọc được NR, KHÔNG có role transition 'Phê duyệt') →
        approve raise FORBIDDEN(403); workflow_state + docstatus KHÔNG đổi
        (guard TRƯỚC mutate)."""
        import frappe
        from assetcore.api import imm01 as api
        name = self._make_pending_nr(2085)
        usr = self._ensure_user("nrrbac_needsmgr@test.local", ["Needs Manager"])
        frappe.set_user(usr)
        try:
            with self.assertRaises(ServiceError) as cm:
                api._approve_needs_request(name, "boss@test.local", "ok")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        self.assertNotIn("<strong>", (cm.exception.message or "").lower())
        self.assertEqual(
            frappe.db.get_value(self.NR, name, "workflow_state"), "Pending Approval")
        self.assertEqual(frappe.db.get_value(self.NR, name, "docstatus"), 0)

    def test_reject_wrong_role_forbidden(self):
        """Đối xứng: Needs Manager reject NR Pending Approval → FORBIDDEN(403),
        workflow_state KHÔNG đổi."""
        import frappe
        from assetcore.api import imm01 as api
        name = self._make_pending_nr(2084)
        usr = self._ensure_user("nrrbac_needsmgr@test.local", ["Needs Manager"])
        frappe.set_user(usr)
        try:
            with self.assertRaises(ServiceError) as cm:
                api._reject_needs_request(name, "Không đủ điều kiện")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        self.assertEqual(
            frappe.db.get_value(self.NR, name, "workflow_state"), "Pending Approval")
        self.assertEqual(frappe.db.get_value(self.NR, name, "docstatus"), 0)

    def test_procurement_manager_approves_end_to_end(self):
        """Regression xanh: Needs Manager + Procurement Manager → approve chạy
        end-to-end: workflow_state='Approved', docstatus=1, write_audit_trail được
        gọi với event 'Approval Note'."""
        import frappe
        from assetcore.api import imm01 as api
        from assetcore.services import imm01 as svc
        name = self._make_pending_nr(2083)
        usr = self._ensure_user(
            "nrrbac_procmgr@test.local", ["Needs Manager", "Procurement Manager"])

        events: list[str] = []
        orig = svc.write_audit_trail

        def _spy(doc, event_type, *a, **k):
            events.append(event_type)
            return orig(doc, event_type, *a, **k)

        svc.write_audit_trail = _spy
        frappe.set_user(usr)
        try:
            # board_approver là Link→User: dùng chính user duyệt (tồn tại) để vượt
            # link-validation lúc doc.submit().
            res = api._approve_needs_request(name, usr, "Đồng ý phê duyệt")
        finally:
            frappe.set_user("Administrator")
            svc.write_audit_trail = orig

        self.assertEqual(res["workflow_state"], "Approved")
        self.assertEqual(frappe.db.get_value(self.NR, name, "workflow_state"), "Approved")
        self.assertEqual(frappe.db.get_value(self.NR, name, "docstatus"), 1)
        self.assertIn("Approval Note", events,
                      "write_audit_trail phải được gọi với event 'Approval Note'")


# ─────────────────────────────────────────────────────────────────────────────
# CR-WF-01-SURFACE-GUARD — invariant guard cho 2 surface CTA của IMM-01
# (silent-CTA-loss). Mirror R29 IMM-04 cho module lifecycle-ENTRY (Needs 34
# transition + Plan 10 transition, 2 surface — KHÁC IMM-04 chỉ 1 surface).
#
# Lỗ đóng: rename / deactivate / duplicate active Workflow → get_transitions trả []
# → bare `except Exception: return []` @_nr/_plan_allowed_transition_actions nuốt
# CÂM → mất TOÀN BỘ nút duyệt đề xuất/kế hoạch mà KHÔNG test nào bắt. 3 tầng bất
# biến, module-local:
#   • INV-A (resolution): document_type → ĐÚNG-1 active Workflow đúng tên (fixtures).
#   • INV-B (live-wiring): user CÓ role transition trên Draft → surface NON-EMPTY
#     và == tập action get_transitions (chống permanent []).
#   • INV-C (degrade): user thiếu quyền / get_transitions raise → [] GRACEFUL,
#     KHÔNG raise, payload không vỡ (phân định empty-do-thiếu-quyền vs empty-do-vỡ).
#
# Cross-ref (KHÔNG re-assert ở đây): Super-Admin-mọi-transition-edge đã khoá TOÀN
# CỤC ở test_workflow_admin_override.py (5 class: TestWorkflowAdminOverride +
# TestBackfillScope + TestRevertForeign[Live] + TestSourceWorkflowFiles). Guard này
# CHỈ khoá resolution + live-wiring + degrade của 2 surface IMM-01.
#
# [AUTO] 0 runtime .py change (chỉ +test) → 0 gunicorn --preload reload / 0 migrate.
# ─────────────────────────────────────────────────────────────────────────────
class TestNeedsPlanWorkflowSurfaceInvariant(unittest.TestCase):
    """Guard 2 surface CTA IMM-01 (`_nr_allowed_transition_actions` @api/imm01.py:187
    + `_plan_allowed_transition_actions` @:476) chống mất-câm-nút-duyệt khi
    workflow bị rename/deactivate/duplicate. Live-wiring = surface phải BẰNG tập
    action `frappe.model.workflow.get_transitions` (không permanent []).
    """

    _DT_NR = "IMM Needs Request"
    _DT_PP = "IMM Procurement Plan"
    _EXPECTED_NR_WF = "IMM-01 Needs Workflow"
    _EXPECTED_PP_WF = "IMM-01 Plan Workflow"
    # Action Draft grounded fixtures/workflow.json (Draft có đúng 1 action/workflow).
    _NR_DRAFT_ACTION = "Gửi đề xuất"
    _PP_DRAFT_ACTION = "Phê duyệt kế hoạch"

    @classmethod
    def setUpClass(cls):
        import frappe
        frappe.set_user("Administrator")

    def tearDown(self):
        import frappe
        frappe.set_user("Administrator")

    # ── fixtures ──────────────────────────────────────────────────────────────
    def _make_draft_nr(self, year):
        """NR ở 'Draft' (docstatus=0). ignore_links → bỏ qua AC Department/Category
        (guard read-only, không submit). workflow_state ép 'Draft' → deterministic."""
        import frappe
        nr = frappe.new_doc(self._DT_NR)
        nr.request_date = frappe.utils.today()
        nr.request_type = "New"
        nr.requesting_department = "_TEST-INVSURF-DEPT"
        nr.device_category = "_TEST-INVSURF-CAT"
        nr.quantity = 1
        nr.target_year = year
        nr.funding_source = "NSNN"
        nr.clinical_justification = "Guard INV-SURFACE cho NR — đủ ký tự minh chứng."
        nr.flags.ignore_links = True
        nr.insert(ignore_permissions=True)
        frappe.db.set_value(self._DT_NR, nr.name, "workflow_state", "Draft",
                            update_modified=False)
        frappe.db.commit()
        self.addCleanup(self._purge_nr, nr.name)
        return nr.name

    def _purge_nr(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self._DT_NR, name):
            frappe.db.set_value(self._DT_NR, name, "docstatus", 0)
            frappe.delete_doc(self._DT_NR, name, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _make_draft_plan(self, year, period="Q1"):
        """Kế hoạch RỖNG ở 'Draft' (bậc thang transition đầu) — đủ để đo surface."""
        import frappe
        doc = frappe.new_doc(self._DT_PP)
        doc.plan_year = year
        doc.plan_period = period
        doc.budget_envelope = 1_000_000
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        self.addCleanup(self._purge_plan, doc.name)
        self.assertEqual(doc.workflow_state, "Draft")  # sanity: default workflow state
        return doc.name

    def _purge_plan(self, name):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists(self._DT_PP, name):
            frappe.delete_doc(self._DT_PP, name, force=True, ignore_permissions=True)
        frappe.db.commit()

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
        frappe.clear_cache(user=email)  # tránh stale role-cache nếu user tồn dư
        from assetcore.services.shared import rbac as _rbac
        if hasattr(_rbac, "invalidate_capabilities"):
            _rbac.invalidate_capabilities(email)
        self.addCleanup(self._purge_user, email)
        return email

    def _purge_user(self, email):
        import frappe
        frappe.set_user("Administrator")
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()

    def _surface_and_raw(self, kind, name, user):
        """Tính (surface, raw) DƯỚI CÙNG session ``user``:
          surface = _{nr|plan}_allowed_transition_actions(doc) (dedupe)
          raw     = action từ frappe.model.workflow.get_transitions(doc) (dedupe)
        So == raw = bằng chứng live-wiring (surface KHÔNG hardcode / permanent [])."""
        import frappe
        from assetcore.api import imm01 as api
        from frappe.model.workflow import get_transitions
        dt = self._DT_NR if kind == "nr" else self._DT_PP
        surface_fn = (api._nr_allowed_transition_actions if kind == "nr"
                      else api._plan_allowed_transition_actions)
        frappe.set_user(user)
        try:
            doc = frappe.get_doc(dt, name)
            surface = list(surface_fn(doc))
            raw: list[str] = []
            for t in (get_transitions(doc) or []):
                a = t.get("action")
                if a and a not in raw:
                    raw.append(a)
        finally:
            frappe.set_user("Administrator")
        return surface, raw

    # ── INV-01-SURFACE-A: workflow-resolution (đúng-1-active-named) ────────────
    def test_inv_surface_a1_needs_resolves_single_active_named_workflow(self):
        """TC-01-SURF-A1: document_type 'IMM Needs Request' → ĐÚNG 1 active Workflow
        tên 'IMM-01 Needs Workflow' (grounded fixtures/workflow.json). RED nếu
        rename / deactivate / duplicate active workflow."""
        import frappe
        names = frappe.get_all(
            "Workflow",
            filters={"document_type": self._DT_NR, "is_active": 1},
            pluck="name",
        )
        self.assertEqual(
            len(names), 1,
            f"INV-A1: document_type {self._DT_NR!r} PHẢI resolve ĐÚNG 1 active "
            f"Workflow (rename/deactivate/duplicate = mất câm CTA); thấy: {names}")
        self.assertEqual(
            names[0], self._EXPECTED_NR_WF,
            f"INV-A1: active Workflow phải tên {self._EXPECTED_NR_WF!r} "
            f"(grounded fixtures/workflow.json); thấy: {names[0]!r}")

    def test_inv_surface_a2_plan_resolves_single_active_named_workflow(self):
        """TC-01-SURF-A2: document_type 'IMM Procurement Plan' → ĐÚNG 1 active
        Workflow tên 'IMM-01 Plan Workflow' (grounded fixtures)."""
        import frappe
        names = frappe.get_all(
            "Workflow",
            filters={"document_type": self._DT_PP, "is_active": 1},
            pluck="name",
        )
        self.assertEqual(
            len(names), 1,
            f"INV-A2: document_type {self._DT_PP!r} PHẢI resolve ĐÚNG 1 active "
            f"Workflow; thấy: {names}")
        self.assertEqual(
            names[0], self._EXPECTED_PP_WF,
            f"INV-A2: active Workflow phải tên {self._EXPECTED_PP_WF!r}; "
            f"thấy: {names[0]!r}")

    # ── INV-01-SURFACE-B: live-wiring (NON-EMPTY == get_transitions) ───────────
    def test_inv_surface_b1_needs_live_wired_nonempty_equals_get_transitions(self):
        """TC-01-SURF-B1: Draft NR + user CÓ role transition ('Needs Manager' —
        đọc NR + có action Draft 'Gửi đề xuất') → _nr_allowed_transition_actions
        NON-EMPTY và == {action từ get_transitions} (dedupe). Chống permanent []."""
        name = self._make_draft_nr(2091)
        usr = self._ensure_user("inv_nr_wire@test.local", ["Needs Manager"])
        surface, raw = self._surface_and_raw("nr", name, usr)
        self.assertTrue(
            surface,
            "INV-B1: user CÓ role transition PHẢI có ≥1 action (permanent [] = "
            "workflow vỡ / bare-except nuốt câm)")
        self.assertEqual(
            set(surface), set(raw),
            "INV-B1: surface PHẢI == tập action get_transitions (live-wired)")
        self.assertEqual(
            len(surface), len(set(surface)),
            "INV-B1: surface dedupe theo action (không trùng)")
        self.assertIn(
            self._NR_DRAFT_ACTION, surface,
            f"INV-B1: Draft NR + Needs Manager PHẢI thấy {self._NR_DRAFT_ACTION!r} "
            f"(grounded fixtures/workflow.json)")

    def test_inv_surface_b2_plan_live_wired_nonempty_equals_get_transitions(self):
        """TC-01-SURF-B2: Draft Plan + user role transition ('Procurement Manager'
        cho action + 'Needs Manager' cho quyền ĐỌC) → _plan_allowed_transition_actions
        NON-EMPTY == get_transitions actions. Dùng _DT_PP — KHÔNG lẫn _DT_NR."""
        name = self._make_draft_plan(2092)
        usr = self._ensure_user(
            "inv_pp_wire@test.local", ["Needs Manager", "Procurement Manager"])
        surface, raw = self._surface_and_raw("plan", name, usr)
        self.assertTrue(
            surface,
            "INV-B2: user CÓ role transition PHẢI có ≥1 action (permanent [] = vỡ)")
        self.assertEqual(
            set(surface), set(raw),
            "INV-B2: surface PHẢI == tập action get_transitions (live-wired)")
        self.assertEqual(
            len(surface), len(set(surface)),
            "INV-B2: surface dedupe theo action (không trùng)")
        self.assertIn(
            self._PP_DRAFT_ACTION, surface,
            f"INV-B2: Draft Plan + Procurement Manager PHẢI thấy "
            f"{self._PP_DRAFT_ACTION!r} (grounded fixtures/workflow.json)")

    # ── INV-01-SURFACE-C: degrade graceful (phân định empty-do-thiếu-quyền) ────
    def test_inv_surface_c1_needs_base_role_returns_empty_graceful(self):
        """TC-01-SURF-C1: user CHỈ base role 'AssetCore System User' (không role
        transition) → _nr_allowed_transition_actions trả [] GRACEFUL — KHÔNG raise,
        payload KHÔNG vỡ. Đây là empty-do-thiếu-quyền (CHẤP NHẬN), phân biệt với
        empty-do-workflow-vỡ (INV-A/INV-B bắt = bug)."""
        import frappe
        from assetcore.api import imm01 as api
        name = self._make_draft_nr(2093)
        usr = self._ensure_user("inv_nr_base@test.local", ["AssetCore System User"])
        frappe.set_user(usr)
        try:
            doc = frappe.get_doc(self._DT_NR, name)
            result = api._nr_allowed_transition_actions(doc)  # KHÔNG raise
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(
            result, [],
            "INV-C1: base-role → [] graceful (không raise / không 403-500 vỡ payload)")

    def test_inv_surface_c2_get_transitions_raise_returns_empty_graceful(self):
        """TC-01-SURF-C2: monkeypatch frappe.model.workflow.get_transitions → raise
        → CẢ _nr/_plan surface trả [] (bare-except path chứng minh graceful).

        ⚠️ HARD-STOP observability backlog (KHÔNG áp vòng này): bare
        `except Exception: return []` @_nr/_plan_allowed_transition_actions NUỐT lỗi
        CÂM. Nên thay bằng frappe.log_error(...) TRƯỚC khi degrade = runtime .py
        change → cần gunicorn --preload reload (USER), ship RIÊNG. Guard này khoá
        hành vi graceful hiện tại; khi thêm log_error surface VẪN trả [] nên test
        vẫn GREEN (chỉ +side-effect log)."""
        from unittest import mock
        from types import SimpleNamespace
        from assetcore.api import imm01 as api
        dummy = SimpleNamespace()  # get_transitions bị patch raise trước khi chạm doc
        with mock.patch("frappe.model.workflow.get_transitions",
                        side_effect=Exception("boom-workflow-broken")):
            self.assertEqual(
                api._nr_allowed_transition_actions(dummy), [],
                "INV-C2: get_transitions raise → _nr surface [] (bare-except graceful)")
            self.assertEqual(
                api._plan_allowed_transition_actions(dummy), [],
                "INV-C2: get_transitions raise → _plan surface [] (bare-except graceful)")
