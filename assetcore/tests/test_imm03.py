"""Unit tests for IMM-03 — Vendor Eval & Procurement Decision service layer."""
from __future__ import annotations
import json
import unittest
from types import SimpleNamespace

import frappe

from assetcore.services.imm03 import (
    _parse_weighting,
    _parse_json_field,
    _compute_eval_scores,
    _resolve_recommendation,
    _validate_gate_g04_method,
    set_actual_delivery_on_received,
    validate_receipt_against_po,
    ENVELOPE_HARD_LIMIT_PCT,
    _METHOD_RULES,
    _avl_is_live,
    _is_supplier_in_avl,
    _vr05_winner_avl_required,
    _sync_supplier_avl_status,
    check_avl_expiry,
    _DT_VE,
)
from assetcore.services.shared import ErrorCode, ServiceError


def _make_candidate(supplier: str, scores: dict | None = None,
                    weighted_score: float = 0.0) -> SimpleNamespace:
    return SimpleNamespace(supplier=supplier, scores=scores,
                           weighted_score=weighted_score, in_avl=0)


def _make_criterion(criterion: str, group: str, weight_pct: float) -> SimpleNamespace:
    return SimpleNamespace(criterion=criterion, group=group, weight_pct=weight_pct)


def _make_pd_doc(**kwargs) -> SimpleNamespace:
    defaults = dict(
        name="_Test-PD-001",
        workflow_state="Draft",
        procurement_method=None,
        awarded_price=None,
        method_legal_basis=None,
        winner_supplier=None,
        spec_ref=None,
        plan_ref=None,
        plan_line=None,
        envelope_check_pct=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestParseWeighting(unittest.TestCase):

    def test_none_returns_defaults(self):
        result = _parse_weighting(None)
        self.assertIn("Technical", result)
        self.assertIn("Commercial", result)

    def test_dict_passthrough(self):
        d = {"Technical": 40, "Commercial": 30, "Financial": 30}
        self.assertEqual(_parse_weighting(d), d)

    def test_valid_json_parsed(self):
        result = _parse_weighting('{"Technical": 50, "Support": 50}')
        self.assertEqual(result["Technical"], 50)

    def test_invalid_json_returns_defaults(self):
        result = _parse_weighting("{bad}")
        self.assertIn("Technical", result)


class TestParseJsonField(unittest.TestCase):

    def test_none_returns_empty_dict(self):
        self.assertEqual(_parse_json_field(None), {})

    def test_dict_passthrough(self):
        d = {"k": 1}
        self.assertEqual(_parse_json_field(d), d)

    def test_valid_json_string(self):
        self.assertEqual(_parse_json_field('{"a": 2}'), {"a": 2})

    def test_invalid_json_returns_empty(self):
        self.assertEqual(_parse_json_field("not-json"), {})


class TestComputeEvalScores(unittest.TestCase):

    def _make_eval_doc(self, candidates, criteria, weighting=None) -> SimpleNamespace:
        # name/has_top_tie/tied_candidates mirror DocType fields (INV-VE-TIE §IV.7)
        return SimpleNamespace(name="_Test-VE-001", candidates=candidates,
                               criteria=criteria, weighting_scheme=weighting,
                               recommended_candidate=None, spec_ref=None,
                               has_top_tie=0, tied_candidates="")

    def test_higher_score_candidate_wins(self):
        criteria = [
            _make_criterion("Tech Score", "Technical", 100.0),
        ]
        cands = [
            _make_candidate("SUP-A", scores={"Tech Score": 0.9}),
            _make_candidate("SUP-B", scores={"Tech Score": 0.5}),
        ]
        weighting = {"Technical": 100}
        doc = self._make_eval_doc(cands, criteria, weighting)
        _compute_eval_scores(doc)
        self.assertEqual(doc.recommended_candidate, "SUP-A")

    def test_unknown_criterion_ignored(self):
        criteria = [_make_criterion("Known", "Technical", 100.0)]
        cands = [_make_candidate("SUP-A", scores={"Unknown": 0.9, "Known": 0.8})]
        doc = self._make_eval_doc(cands, criteria, {"Technical": 100})
        _compute_eval_scores(doc)
        # Should not raise; unknown criterion contributes 0
        self.assertGreater(cands[0].weighted_score, 0)

    def test_empty_candidates_no_recommended(self):
        doc = self._make_eval_doc([], [])
        _compute_eval_scores(doc)
        self.assertIsNone(doc.recommended_candidate)

    # ── INV-VE-TIE §IV.7 — cổng tie-break (KHÔNG auto-award khi đỉnh HÒA) ──────

    def _tech100(self):
        return [_make_criterion("Tech Score", "Technical", 100.0)], {"Technical": 100}

    def test_single_top_score_recommends_that_candidate(self):
        """1 candidate điểm cao nhất DUY NHẤT → recommended = supplier đó,
        has_top_tie falsy, tied_candidates rỗng (giữ higher-wins)."""
        criteria, weighting = self._tech100()
        cands = [
            _make_candidate("SUP-A", scores={"Tech Score": 0.9}),
            _make_candidate("SUP-B", scores={"Tech Score": 0.5}),
        ]
        doc = self._make_eval_doc(cands, criteria, weighting)
        _compute_eval_scores(doc)
        self.assertEqual(doc.recommended_candidate, "SUP-A")
        self.assertFalse(doc.has_top_tie)
        self.assertIn(doc.tied_candidates, (None, ""))

    def test_top_tie_suppresses_recommendation(self):
        """2 candidate cùng weighted_score đỉnh (>0) → recommended None,
        has_top_tie truthy, tied_candidates chứa cả 2 supplier (sorted), KHÔNG raise."""
        criteria, weighting = self._tech100()
        cands = [
            _make_candidate("SUP-B", scores={"Tech Score": 0.8}),
            _make_candidate("SUP-A", scores={"Tech Score": 0.8}),
        ]
        doc = self._make_eval_doc(cands, criteria, weighting)
        _compute_eval_scores(doc)  # must NOT raise
        self.assertIsNone(doc.recommended_candidate)
        self.assertTrue(doc.has_top_tie)
        self.assertEqual(doc.tied_candidates, "SUP-A,SUP-B")  # sorted asc

    def test_three_way_partial_tie_only_top_counts(self):
        """3 candidate: 2 hòa đỉnh + 1 thấp hơn → recommended None,
        tied = 2 supplier đỉnh (candidate thấp KHÔNG vào tied)."""
        criteria, weighting = self._tech100()
        cands = [
            _make_candidate("SUP-C", scores={"Tech Score": 0.9}),
            _make_candidate("SUP-A", scores={"Tech Score": 0.9}),
            _make_candidate("SUP-B", scores={"Tech Score": 0.4}),  # lower
        ]
        doc = self._make_eval_doc(cands, criteria, weighting)
        _compute_eval_scores(doc)
        self.assertIsNone(doc.recommended_candidate)
        self.assertTrue(doc.has_top_tie)
        self.assertEqual(doc.tied_candidates, "SUP-A,SUP-C")
        self.assertNotIn("SUP-B", doc.tied_candidates)

    def test_near_equal_within_epsilon_is_tie(self):
        """Chênh ≤ 1e-9 sau round(4) → tie (suppress). Cùng round value = tie."""
        criteria, weighting = self._tech100()
        # round(·×5,4) collapses 0.80000 and 0.800004 → both 4.0 (Δ=0) ⇒ tie
        cands = [
            _make_candidate("SUP-A", scores={"Tech Score": 0.80000}),
            _make_candidate("SUP-B", scores={"Tech Score": 0.800004}),
        ]
        doc = self._make_eval_doc(cands, criteria, weighting)
        _compute_eval_scores(doc)
        self.assertEqual(cands[0].weighted_score, cands[1].weighted_score)
        self.assertIsNone(doc.recommended_candidate)
        self.assertTrue(doc.has_top_tie)

    def test_above_epsilon_is_not_tie(self):
        """Chênh > epsilon (rõ ràng) → KHÔNG tie; chọn cao hơn."""
        criteria, weighting = self._tech100()
        cands = [
            _make_candidate("SUP-A", scores={"Tech Score": 0.9}),
            _make_candidate("SUP-B", scores={"Tech Score": 0.89}),
        ]
        doc = self._make_eval_doc(cands, criteria, weighting)
        _compute_eval_scores(doc)
        self.assertGreater(cands[0].weighted_score, cands[1].weighted_score)
        self.assertEqual(doc.recommended_candidate, "SUP-A")
        self.assertFalse(doc.has_top_tie)

    def test_all_zero_scores_no_recommendation_no_tie(self):
        """Mọi weighted_score ≤ 0 → recommended None, has_top_tie falsy (giữ zero)."""
        criteria, weighting = self._tech100()
        cands = [
            _make_candidate("SUP-A", scores={"Tech Score": 0.0}),
            _make_candidate("SUP-B", scores={"Tech Score": 0.0}),
        ]
        doc = self._make_eval_doc(cands, criteria, weighting)
        _compute_eval_scores(doc)
        self.assertIsNone(doc.recommended_candidate)
        self.assertFalse(doc.has_top_tie)
        self.assertIn(doc.tied_candidates, (None, ""))

    def test_non_tie_ordering_stable_deterministic(self):
        """Cùng input gọi 2 lần (đảo thứ tự child) → thứ hạng & recommended y hệt
        (KHÔNG phụ thuộc thứ tự child ngẫu nhiên)."""
        criteria, weighting = self._tech100()
        order1 = [
            _make_candidate("SUP-A", scores={"Tech Score": 0.9}),
            _make_candidate("SUP-B", scores={"Tech Score": 0.5}),
            _make_candidate("SUP-C", scores={"Tech Score": 0.7}),
        ]
        order2 = [
            _make_candidate("SUP-C", scores={"Tech Score": 0.7}),
            _make_candidate("SUP-B", scores={"Tech Score": 0.5}),
            _make_candidate("SUP-A", scores={"Tech Score": 0.9}),
        ]
        d1 = self._make_eval_doc(order1, criteria, weighting)
        d2 = self._make_eval_doc(order2, criteria, weighting)
        _compute_eval_scores(d1)
        _compute_eval_scores(d2)
        self.assertEqual(d1.recommended_candidate, d2.recommended_candidate)
        self.assertEqual(d1.recommended_candidate, "SUP-A")
        self.assertFalse(d1.has_top_tie)
        self.assertFalse(d2.has_top_tie)


class TestResolveRecommendation(unittest.TestCase):
    """Pure helper _resolve_recommendation(candidates) -> (recommended, tied) —
    KHÔNG cần Frappe DB (INV-VE-TIE §IV.7)."""

    def test_single_winner(self):
        cands = [_make_candidate("SUP-A", weighted_score=4.5),
                 _make_candidate("SUP-B", weighted_score=3.0)]
        rec, tied = _resolve_recommendation(cands)
        self.assertEqual(rec, "SUP-A")
        self.assertEqual(tied, [])

    def test_two_way_tie_returns_sorted_list_no_winner(self):
        cands = [_make_candidate("SUP-B", weighted_score=4.5),
                 _make_candidate("SUP-A", weighted_score=4.5)]
        rec, tied = _resolve_recommendation(cands)
        self.assertIsNone(rec)
        self.assertEqual(tied, ["SUP-A", "SUP-B"])  # sorted asc

    def test_zero_top_no_winner_no_tie(self):
        cands = [_make_candidate("SUP-A", weighted_score=0.0),
                 _make_candidate("SUP-B", weighted_score=0.0)]
        rec, tied = _resolve_recommendation(cands)
        self.assertIsNone(rec)
        self.assertEqual(tied, [])

    def test_empty_no_winner_no_tie(self):
        rec, tied = _resolve_recommendation([])
        self.assertIsNone(rec)
        self.assertEqual(tied, [])

    def test_partial_tie_excludes_lower(self):
        cands = [_make_candidate("SUP-C", weighted_score=4.9),
                 _make_candidate("SUP-A", weighted_score=4.9),
                 _make_candidate("SUP-B", weighted_score=2.0)]
        rec, tied = _resolve_recommendation(cands)
        self.assertIsNone(rec)
        self.assertEqual(tied, ["SUP-A", "SUP-C"])

    def test_epsilon_equal_is_tie(self):
        cands = [_make_candidate("SUP-A", weighted_score=4.0),
                 _make_candidate("SUP-B", weighted_score=4.0 + 5e-10)]
        rec, tied = _resolve_recommendation(cands)
        self.assertIsNone(rec)
        self.assertEqual(tied, ["SUP-A", "SUP-B"])


class TestGateG04Method(unittest.TestCase):

    def test_draft_state_skips_check(self):
        doc = _make_pd_doc(
            workflow_state="Draft",
            procurement_method="Chỉ định thầu",
            awarded_price=100_000_000,
        )
        _validate_gate_g04_method(doc)  # must not raise

    def test_chi_dinh_thau_exceeds_limit_raises(self):
        doc = _make_pd_doc(
            workflow_state="Pending Approval",
            procurement_method="Chỉ định thầu",
            awarded_price=60_000_000,  # > 50M limit
        )
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g04_method(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)

    def test_chi_dinh_thau_within_limit_but_no_legal_basis_raises(self):
        doc = _make_pd_doc(
            workflow_state="Pending Approval",
            procurement_method="Chỉ định thầu",
            awarded_price=30_000_000,  # within limit
            method_legal_basis="",
        )
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g04_method(doc)
        self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)

    def test_chao_hang_within_limit_and_legal_basis_passes(self):
        doc = _make_pd_doc(
            workflow_state="Pending Approval",
            procurement_method="Chào hàng cạnh tranh",
            awarded_price=500_000_000,  # < 1B limit
            method_legal_basis="Nghị định 63",
        )
        _validate_gate_g04_method(doc)  # must not raise

    def test_unknown_method_skips(self):
        doc = _make_pd_doc(
            workflow_state="Pending Approval",
            procurement_method="Method không tồn tại",
            awarded_price=999_999_999,
        )
        _validate_gate_g04_method(doc)  # must not raise

    def test_no_method_skips(self):
        doc = _make_pd_doc(workflow_state="Pending Approval", procurement_method=None)
        _validate_gate_g04_method(doc)  # must not raise


class TestMethodRules(unittest.TestCase):
    """Verify _METHOD_RULES constants are internally consistent."""

    def test_chi_dinh_thau_limit_is_50m(self):
        max_val, min_q = _METHOD_RULES["Chỉ định thầu"]
        self.assertEqual(max_val, 50_000_000)
        self.assertEqual(min_q, 1)

    def test_chao_hang_canh_tranh_limit_is_1b(self):
        max_val, min_q = _METHOD_RULES["Chào hàng cạnh tranh"]
        self.assertEqual(max_val, 1_000_000_000)
        self.assertEqual(min_q, 3)

    def test_dau_thau_rong_rai_has_no_price_cap(self):
        max_val, min_q = _METHOD_RULES["Đấu thầu rộng rãi"]
        self.assertIsNone(max_val)
        self.assertEqual(min_q, 3)


class TestActualDeliveryDefault(unittest.TestCase):
    """Slide 14b — actual_delivery_date mặc định = hôm nay khi Received."""

    def test_received_empty_defaults_today(self):
        from frappe.utils import today
        doc = SimpleNamespace(status="Received", actual_delivery_date=None)
        set_actual_delivery_on_received(doc)
        self.assertEqual(doc.actual_delivery_date, today())

    def test_received_with_value_unchanged(self):
        doc = SimpleNamespace(status="Received", actual_delivery_date="2026-01-01")
        set_actual_delivery_on_received(doc)
        self.assertEqual(doc.actual_delivery_date, "2026-01-01")

    def test_non_received_skipped(self):
        doc = SimpleNamespace(status="Submitted", actual_delivery_date=None)
        set_actual_delivery_on_received(doc)
        self.assertIsNone(doc.actual_delivery_date)


class TestReceiptAgainstPO(unittest.TestCase):
    """Slide 18 — hàng nhận phải khớp PO line; + Slide 09 PO→Decision→Plan."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        existing = frappe.get_all("AC Supplier", limit=1, pluck="name")
        if existing:
            sup = existing[0]
        else:
            d = frappe.get_doc({
                "doctype": "AC Supplier", "supplier_name": "_T-IMM03-SUP",
            })
            d.insert(ignore_permissions=True)
            sup = d.name
        cls.supplier = sup
        model = frappe.get_all("IMM Device Model", limit=1, pluck="name")
        cls.model = model[0] if model else None
        po = frappe.new_doc("AC Purchase")
        po.supplier = sup
        if cls.model:
            po.append("devices", {"device_model": cls.model, "qty": 1, "unit_price": 1000})
        else:
            spares = frappe.get_all("AC Spare Part", limit=1, pluck="name")
            cls.spare = spares[0] if spares else None
            if cls.spare:
                po.append("items", {"spare_part": cls.spare, "qty": 1, "unit_cost": 100})
        po.insert(ignore_permissions=True)
        cls.po = po.name

    def test_po_code_set_after_insert(self):
        po_code = frappe.db.get_value("AC Purchase", self.po, "po_code")
        self.assertEqual(po_code, self.po)

    def test_match_passes(self):
        if self.model:
            validate_receipt_against_po(self.po, [{"device_model": self.model}])
        elif getattr(self, "spare", None):
            validate_receipt_against_po(self.po, [{"spare_part": self.spare}])
        else:
            self.skipTest("no model/spare master to test match")

    def test_mismatch_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            validate_receipt_against_po(self.po, [{"device_model": "_NONEXISTENT"}])
        self.assertEqual(ctx.exception.code, ErrorCode.BUSINESS_RULE)

    def test_unknown_po_raises(self):
        with self.assertRaises(ServiceError) as ctx:
            validate_receipt_against_po("_NOPE", [{"device_model": "X"}])
        self.assertEqual(ctx.exception.code, ErrorCode.NOT_FOUND)

    def test_traceability_po_to_decision_to_plan(self):
        """PO → Decision → Plan chain navigable khi qua mint flow."""
        # Verify field tồn tại để traverse: po.procurement_decision_ref
        meta = frappe.get_meta("AC Purchase")
        self.assertIsNotNone(meta.get_field("procurement_decision_ref"))
        pd_meta = frappe.get_meta("IMM Procurement Decision")
        self.assertIsNotNone(pd_meta.get_field("plan_ref"))
        ve_meta = frappe.get_meta("IMM Vendor Evaluation")
        self.assertIsNotNone(ve_meta.get_field("plan_ref"))


# ── INV-AVL-LIVE — SoT predicate 'AVL còn hiệu lực' (02 §IV.6, vòng 22) ─────────
#
# Predicate SoT canonical:
#   LIVE ⇔ docstatus=1 ∧ workflow_state ∈ {Approved,Conditional}
#                      ∧ (valid_to IS NULL OR valid_to >= CURDATE())
# >= inclusive (biên hôm-nay LIVE) bù khít check_avl_expiry dùng < (no off-by-one).
# TDD VIẾT TRƯỚC — RED-prove trên code cũ (cũ thiếu valid_to ở
# _is_supplier_in_avl/_vr05/dashboard → ca hết-hạn PASS sai).

class TestAvlLiveSoT(unittest.TestCase):
    """INV-AVL-LIVE-1..6 — hợp nhất cổng eligibility AVL về 1 SoT live."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._avls: list[str] = []
        cls._suppliers: list[str] = []
        cls._cats: list[str] = []
        cls._specs: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for name in cls._avls:
            try:
                frappe.db.set_value("IMM AVL Entry", name, "docstatus", 0,
                                    update_modified=False)
                frappe.delete_doc("IMM AVL Entry", name, force=1,
                                  ignore_permissions=True)
            except Exception:
                pass
        for name in cls._specs:
            try:
                frappe.delete_doc("IMM Tech Spec", name, force=1,
                                  ignore_permissions=True)
            except Exception:
                pass
        for name in cls._cats:
            try:
                frappe.delete_doc("AC Asset Category", name, force=1,
                                  ignore_permissions=True)
            except Exception:
                pass
        for name in cls._suppliers:
            try:
                frappe.delete_doc("AC Supplier", name, force=1,
                                  ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    # ── fixtures ───────────────────────────────────────────────────────────────

    def _new_supplier(self) -> str:
        doc = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": f"_T-AVL-SUP-{frappe.generate_hash(length=6)}",
        })
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        type(self)._suppliers.append(doc.name)
        return doc.name

    def _new_category(self) -> str:
        cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"_T-AVL-CAT-{frappe.generate_hash(length=6)}",
            "category_code": f"AV{frappe.generate_hash(length=4)}",
        })
        cat.flags.ignore_mandatory = True
        cat.insert(ignore_permissions=True)
        type(self)._cats.append(cat.name)
        return cat.name

    def _new_avl(self, supplier: str, category: str, *,
                 workflow_state: str = "Approved", valid_to=None) -> str:
        """Insert + submit AVL, rồi force workflow_state/valid_to chính xác qua
        db.set_value (valid_to read_only + auto-compute trong validate_avl; ca
        cần ngày tùy ý/NULL → set trực tiếp như production check_avl_expiry)."""
        from frappe.utils import today as _today
        avl = frappe.get_doc({
            "doctype": "IMM AVL Entry",
            "supplier": supplier,
            "device_category": category,
            "validity_years": 2,
            "valid_from": _today(),
        })
        avl.flags.ignore_mandatory = True
        avl.insert(ignore_permissions=True)
        avl.submit()  # docstatus=1
        type(self)._avls.append(avl.name)
        frappe.db.set_value("IMM AVL Entry", avl.name,
                            {"workflow_state": workflow_state, "valid_to": valid_to},
                            update_modified=False)
        return avl.name

    def _new_spec(self, category: str) -> str:
        spec = frappe.get_doc({
            "doctype": "IMM Tech Spec",
            "device_category": category,
        })
        spec.flags.ignore_mandatory = True
        spec.insert(ignore_permissions=True)
        type(self)._specs.append(spec.name)
        return spec.name

    def _pd(self, winner: str, spec_ref: str) -> SimpleNamespace:
        return _make_pd_doc(winner_supplier=winner, spec_ref=spec_ref,
                            workflow_state="Pending Approval")

    @staticmethod
    def _yesterday():
        from frappe.utils import add_days, today
        return add_days(today(), -1)

    @staticmethod
    def _tomorrow():
        from frappe.utils import add_days, today
        return add_days(today(), 1)

    # ── TC-03-AVL-LIVE-01 / INV-AVL-LIVE-1 (BUG CHÍNH, RED-prove) ───────────────

    def test_01_vr05_blocks_expired_stale_approved_winner(self):
        """Winner có AVL Approved nhưng valid_to=hôm-qua (chưa flip Expired) →
        _vr05_winner_avl_required RAISE BUSINESS_RULE. Code cũ: PASS sai (RED)."""
        sup, cat = self._new_supplier(), self._new_category()
        self._new_avl(sup, cat, workflow_state="Approved", valid_to=self._yesterday())
        spec = self._new_spec(cat)
        with self.assertRaises(ServiceError) as cm:
            _vr05_winner_avl_required(self._pd(sup, spec))
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)

    # ── TC-03-AVL-LIVE-02 / INV-AVL-LIVE-5 (happy submit PASS) ──────────────────

    def test_02_vr05_passes_future_valid_to(self):
        """valid_to=ngày-mai → _vr05 KHÔNG raise (eligible). Happy-path bảo toàn."""
        sup, cat = self._new_supplier(), self._new_category()
        self._new_avl(sup, cat, workflow_state="Approved", valid_to=self._tomorrow())
        spec = self._new_spec(cat)
        _vr05_winner_avl_required(self._pd(sup, spec))  # must not raise

    # ── TC-03-AVL-LIVE-03 / INV-AVL-LIVE-4 (biên hôm nay, no off-by-one) ────────

    def test_03_boundary_today_eligible_and_not_expired(self):
        """valid_to == hôm nay → ELIGIBLE (>= inclusive): _is_supplier_in_avl=1,
        _vr05 PASS; check_avl_expiry (dùng <) KHÔNG flip Expired hôm nay."""
        from frappe.utils import today
        sup, cat = self._new_supplier(), self._new_category()
        avl = self._new_avl(sup, cat, workflow_state="Approved", valid_to=today())
        spec = self._new_spec(cat)
        self.assertEqual(_is_supplier_in_avl(sup, cat), 1)
        _vr05_winner_avl_required(self._pd(sup, spec))  # must not raise
        # scheduler dùng < CURDATE() → KHÔNG expire biên hôm nay
        check_avl_expiry()
        self.assertEqual(
            frappe.db.get_value("IMM AVL Entry", avl, "workflow_state"), "Approved")

    # ── TC-03-AVL-LIVE-04 / INV-AVL-LIVE-2 (valid_to NULL — vô thời hạn) ────────

    def test_04_null_valid_to_eligible(self):
        """valid_to IS NULL → eligible=1 + _vr05 PASS (AVL vô thời hạn)."""
        sup, cat = self._new_supplier(), self._new_category()
        self._new_avl(sup, cat, workflow_state="Approved", valid_to=None)
        spec = self._new_spec(cat)
        self.assertEqual(_is_supplier_in_avl(sup, cat), 1)
        _vr05_winner_avl_required(self._pd(sup, spec))  # must not raise

    # ── TC-03-AVL-LIVE-05 / INV-AVL-LIVE-2 (_is_supplier_in_avl trực tiếp) ──────

    def test_05_is_supplier_in_avl_direct(self):
        """Expired-stale-Approved → 0; live → 1; category mismatch → 0."""
        sup, cat = self._new_supplier(), self._new_category()
        other_cat = self._new_category()
        # hết hạn (workflow_state vẫn Approved) → 0  [RED trên code cũ]
        a_exp = self._new_avl(sup, cat, workflow_state="Approved",
                              valid_to=self._yesterday())
        self.assertEqual(_is_supplier_in_avl(sup, cat), 0)
        # category mismatch → 0
        self.assertEqual(_is_supplier_in_avl(sup, other_cat), 0)
        # nâng valid_to lên tương lai → 1
        frappe.db.set_value("IMM AVL Entry", a_exp, "valid_to", self._tomorrow(),
                            update_modified=False)
        self.assertEqual(_is_supplier_in_avl(sup, cat), 1)
        # category None (bỏ filter device_category) → 1
        self.assertEqual(_is_supplier_in_avl(sup, None), 1)

    # ── TC-03-AVL-LIVE-06 / INV-AVL-LIVE-3 (parity SoT) ────────────────────────

    def test_06_parity_with_sync_predicate(self):
        """Dataset hỗn hợp: tập eligible qua _avl_is_live == tập 'active' của
        reference predicate _sync (cùng mệnh đề). KHÔNG lệch predicate."""
        cat = self._new_category()
        s_future = self._new_supplier()
        s_expired = self._new_supplier()
        s_null = self._new_supplier()
        self._new_avl(s_future, cat, workflow_state="Approved",
                      valid_to=self._tomorrow())
        self._new_avl(s_expired, cat, workflow_state="Approved",
                      valid_to=self._yesterday())  # stale-Approved
        self._new_avl(s_null, cat, workflow_state="Conditional", valid_to=None)
        suppliers = [s_future, s_expired, s_null]
        gate_set = {s for s in suppliers if _avl_is_live(s, cat) == 1}
        # reference predicate = _sync mệnh đề (line 347-348) đo trực tiếp trên DB
        ref_set = set(frappe.db.sql_list(
            """SELECT DISTINCT supplier FROM `tabIMM AVL Entry`
               WHERE supplier IN %(sups)s AND docstatus = 1
                 AND workflow_state IN ('Approved','Conditional')
                 AND (valid_to IS NULL OR valid_to >= CURDATE())""",
            {"sups": suppliers},
        ))
        self.assertEqual(gate_set, ref_set)
        self.assertEqual(gate_set, {s_future, s_null})  # s_expired loại

    # ── TC-03-AVL-LIVE-07 / INV-AVL-LIVE-6 (no N+1) ────────────────────────────

    def test_07_no_n_plus_1(self):
        """Số query của _vr05 với 1 vs nhiều AVL của winner == hằng số (1 truy
        vấn predicate). KHÔNG tăng theo số AVL."""
        sup, cat = self._new_supplier(), self._new_category()
        self._new_avl(sup, cat, workflow_state="Approved", valid_to=self._tomorrow())
        spec = self._new_spec(cat)
        import frappe.database.database as _db_mod

        def _count_calls():
            calls = {"n": 0}
            orig = _db_mod.Database.sql

            def _wrapped(self, *a, **k):
                calls["n"] += 1
                return orig(self, *a, **k)
            return calls, orig, _wrapped

        # 1 AVL
        calls1, orig, wrapped = _count_calls()
        _db_mod.Database.sql = wrapped
        try:
            _vr05_winner_avl_required(self._pd(sup, spec))
        finally:
            _db_mod.Database.sql = orig
        # thêm nhiều AVL nữa cho cùng winner
        for _ in range(4):
            self._new_avl(sup, cat, workflow_state="Approved",
                          valid_to=self._tomorrow())
        calls2, orig, wrapped = _count_calls()
        _db_mod.Database.sql = wrapped
        try:
            _vr05_winner_avl_required(self._pd(sup, spec))
        finally:
            _db_mod.Database.sql = orig
        self.assertEqual(calls1["n"], calls2["n"],
                         "query count phải BẰNG NHAU bất kể số AVL (no N+1)")

    # ── TC-03-AVL-LIVE-08 (Expired đã flip vẫn bị loại — 2 lớp phòng vệ) ───────

    def test_08_already_flipped_expired_rejected(self):
        """AVL workflow_state='Expired' (scheduler đã flip) → eligible=0 + _vr05
        RAISE (phòng vệ cả flag valid_to lẫn workflow_state)."""
        sup, cat = self._new_supplier(), self._new_category()
        # valid_to tương lai NHƯNG state Expired → vẫn loại (state không in tập)
        self._new_avl(sup, cat, workflow_state="Expired", valid_to=self._tomorrow())
        spec = self._new_spec(cat)
        self.assertEqual(_is_supplier_in_avl(sup, cat), 0)
        with self.assertRaises(ServiceError) as cm:
            _vr05_winner_avl_required(self._pd(sup, spec))
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)


class TestEvalTieAuditEvent(unittest.TestCase):
    """INV-VE-TIE §IV.7 — tie tại đỉnh phải surface + audit 'eval_tie_unresolved'.

    Integration nhẹ: dựng VE thật (2 candidate hòa đỉnh) → validate set has_top_tie
    → on_submit_evaluation ghi ĐÚNG 1 IMM Audit Trail (event_type='System') chứa
    'eval_tie_unresolved'; idempotent (gọi 2 lần KHÔNG nhân đôi)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._suppliers: list[str] = []
        cls._cats: list[str] = []
        cls._specs: list[str] = []
        cls._ves: list[str] = []

    @classmethod
    def tearDownClass(cls):
        # Audit Trail có on_trash guard (ISO) → raw SQL cho fixture rác
        for ve in cls._ves:
            frappe.db.sql(
                "DELETE FROM `tabIMM Audit Trail` "
                "WHERE ref_doctype=%s AND ref_name=%s",
                (_DT_VE, ve),
            )
            try:
                frappe.db.set_value(_DT_VE, ve, "docstatus", 0, update_modified=False)
                frappe.delete_doc(_DT_VE, ve, force=1, ignore_permissions=True)
            except Exception:
                pass
        for spec in cls._specs:
            try:
                frappe.delete_doc("IMM Tech Spec", spec, force=1, ignore_permissions=True)
            except Exception:
                pass
        for cat in cls._cats:
            try:
                frappe.delete_doc("AC Asset Category", cat, force=1, ignore_permissions=True)
            except Exception:
                pass
        for sup in cls._suppliers:
            try:
                frappe.delete_doc("AC Supplier", sup, force=1, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    def _supplier(self) -> str:
        doc = frappe.get_doc({
            "doctype": "AC Supplier",
            "supplier_name": f"_T-TIE-SUP-{frappe.generate_hash(length=6)}",
        })
        doc.flags.ignore_mandatory = True
        doc.insert(ignore_permissions=True)
        type(self)._suppliers.append(doc.name)
        return doc.name

    def _spec(self) -> str:
        cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": f"_T-TIE-CAT-{frappe.generate_hash(length=6)}",
            "category_code": f"TI{frappe.generate_hash(length=4)}",
        })
        cat.flags.ignore_mandatory = True
        cat.insert(ignore_permissions=True)
        type(self)._cats.append(cat.name)
        spec = frappe.get_doc({
            "doctype": "IMM Tech Spec",
            "device_category": cat.name,
        })
        spec.flags.ignore_mandatory = True
        spec.insert(ignore_permissions=True)
        type(self)._specs.append(spec.name)
        return spec.name

    def _make_tied_ve(self, sup_a: str, sup_b: str, spec: str):
        """VE Draft với 2 candidate hòa đỉnh (cùng Tech Score)."""
        from frappe.utils import today as _today
        ve = frappe.get_doc({
            "doctype": _DT_VE,
            "spec_ref": spec,
            "draft_date": _today(),
            "weighting_scheme": json.dumps({"Technical": 100}),
            "criteria": [
                {"group": "Technical", "criterion": "Tech Score", "weight_pct": 100},
            ],
            "candidates": [
                {"supplier": sup_a, "scores": json.dumps({"Tech Score": 0.8})},
                {"supplier": sup_b, "scores": json.dumps({"Tech Score": 0.8})},
            ],
        })
        ve.flags.ignore_mandatory = True
        ve.insert(ignore_permissions=True)
        type(self)._ves.append(ve.name)
        return ve

    def _audit_rows(self, ve_name: str):
        return frappe.get_all(
            "IMM Audit Trail",
            filters={"ref_doctype": _DT_VE, "ref_name": ve_name,
                     "event_type": "System"},
            fields=["name", "change_summary"],
        )

    def test_tie_writes_audit_event(self):
        """Tie đỉnh → validate set has_top_tie=1 + tied_candidates;
        on_submit_evaluation ghi 1 audit 'eval_tie_unresolved' với tied suppliers."""
        sup_a, sup_b = self._supplier(), self._supplier()
        spec = self._spec()
        ve = self._make_tied_ve(sup_a, sup_b, spec)
        # validate đã chạy ở insert() → compute scores + flag tie
        ve.reload()
        self.assertTrue(ve.has_top_tie, "validate phải set has_top_tie cho đỉnh hòa")
        self.assertIsNone(ve.recommended_candidate)
        self.assertEqual(ve.tied_candidates, ",".join(sorted([sup_a, sup_b])))
        # Submit-time audit
        from assetcore.services.imm03 import on_submit_evaluation
        on_submit_evaluation(ve)
        rows = self._audit_rows(ve.name)
        tie_rows = [r for r in rows if "eval_tie_unresolved" in (r.change_summary or "")]
        self.assertEqual(len(tie_rows), 1, "đúng 1 audit eval_tie_unresolved")
        summary = tie_rows[0].change_summary
        self.assertIn(sup_a, summary)
        self.assertIn(sup_b, summary)

    def test_tie_audit_idempotent(self):
        """Gọi on_submit_evaluation 2 lần (amend/resubmit) → vẫn 1 audit row."""
        sup_a, sup_b = self._supplier(), self._supplier()
        spec = self._spec()
        ve = self._make_tied_ve(sup_a, sup_b, spec)
        ve.reload()
        from assetcore.services.imm03 import on_submit_evaluation
        on_submit_evaluation(ve)
        on_submit_evaluation(ve)  # re-trigger
        tie_rows = [r for r in self._audit_rows(ve.name)
                    if "eval_tie_unresolved" in (r.change_summary or "")]
        self.assertEqual(len(tie_rows), 1, "idempotent — không nhân đôi audit")

    def test_no_tie_writes_no_audit(self):
        """KHÔNG hòa (1 winner duy nhất) → has_top_tie=0 + KHÔNG audit eval_tie."""
        sup_a, sup_b = self._supplier(), self._supplier()
        spec = self._spec()
        from frappe.utils import today as _today
        ve = frappe.get_doc({
            "doctype": _DT_VE,
            "spec_ref": spec,
            "draft_date": _today(),
            "weighting_scheme": json.dumps({"Technical": 100}),
            "criteria": [
                {"group": "Technical", "criterion": "Tech Score", "weight_pct": 100},
            ],
            "candidates": [
                {"supplier": sup_a, "scores": json.dumps({"Tech Score": 0.9})},
                {"supplier": sup_b, "scores": json.dumps({"Tech Score": 0.5})},
            ],
        })
        ve.flags.ignore_mandatory = True
        ve.insert(ignore_permissions=True)
        type(self)._ves.append(ve.name)
        ve.reload()
        self.assertFalse(ve.has_top_tie)
        self.assertEqual(ve.recommended_candidate, sup_a)
        from assetcore.services.imm03 import on_submit_evaluation
        on_submit_evaluation(ve)
        tie_rows = [r for r in self._audit_rows(ve.name)
                    if "eval_tie_unresolved" in (r.change_summary or "")]
        self.assertEqual(len(tie_rows), 0)


# ──────────────────────────────────────────────────────────────────────────────
# INV-DEC-DRILL (02 §IV.8 / 04 §V.b / 07 §III.2.z) — GUARD card==drill parity.
#
#   KPI tile "Quyết định mua sắm" drill: click tile state S → list lọc
#   workflow_state=S. INVARIANT: SỐ DÒNG list (total) == số trên tile
#   (kpis.decision_states[S]) cho 3 state Awarded / Pending Approval / PO Issued.
#
#   Root của card!=drill: 2 nhánh lệch predicate docstatus.
#     - KPI  : raw SQL  `WHERE docstatus<2 GROUP BY workflow_state`  (loại cancelled)
#     - drill: get_list/db.count — Frappe v15 KHÔNG tự áp docstatus<2 → đếm CẢ
#              cancelled (docstatus=2) còn mang workflow_state cũ ⇒ total > tile.
#   Fix: _list_decisions bơm docstatus<2 mặc định → 2 nhánh đồng nhất predicate.
#
#   TDD: lớp này RED trên code lệch docstatus (revert dòng bơm docstatus<2 →
#   TC-PARITY-03 FAIL: drill[Awarded].total = N+1 ≠ KPI = N), GREEN sau fix.
# ──────────────────────────────────────────────────────────────────────────────

class TestDecisionCardDrillParity(unittest.TestCase):
    """TC-03-PARITY-01..04 — kpis.decision_states[S] == list_decisions({S}).total."""

    _STATES = ("Awarded", "Pending Approval", "PO Issued")
    _PER_STATE = 3  # N decision docstatus<2 (mix submitted+draft) mỗi state

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._pds: list[str] = []
        # Đếm baseline (data thật còn tồn) để parity-check trên DELTA, không phụ
        # thuộc số tuyệt đối trong DB chung (tránh flaky với fixture-leak module khác).
        cls._baseline_kpi = cls._kpi_states()
        cls._baseline_total = {s: cls._drill_total(s) for s in cls._STATES}
        # Seed: N docstatus<2 cho mỗi state (2 submitted docstatus=1 + 1 draft
        # docstatus=0) ⇒ chứng minh TC-PARITY-04 (draft ĐẾM ở cả 2 nhánh).
        for s in cls._STATES:
            cls._mk_pd(s, mode="submit")
            cls._mk_pd(s, mode="submit")
            cls._mk_pd(s, mode="draft")
        # Seed 1 cancelled (docstatus=2) ở Awarded — chứng minh TC-PARITY-03
        # (KHÔNG được đếm ở CẢ KPI lẫn drill).
        cls._cancelled_name = cls._mk_pd("Awarded", mode="cancel")
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for name in cls._pds:
            try:
                frappe.db.set_value("IMM Procurement Decision", name, "docstatus",
                                    0, update_modified=False)
                frappe.delete_doc("IMM Procurement Decision", name, force=1,
                                  ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    # ── fixtures ────────────────────────────────────────────────────────────────

    @classmethod
    def _mk_pd(cls, state: str, *, mode: str) -> str:
        """Insert IMM Procurement Decision và ép workflow_state + docstatus.

        mode: 'draft' (docstatus=0) | 'submit' (docstatus=1) | 'cancel'
        (docstatus=2). docstatus + workflow_state ép THẲNG qua db.set_value.

        Lý do KHÔNG dùng pd.submit()/pd.cancel(): controller before_submit chạy
        gate G05 (yêu cầu funding_source/board_approver/contract_doc) — ngoài
        scope test parity. KPI raw-SQL `WHERE docstatus<2` và drill get_list/db.count
        CHỈ đọc 2 cột docstatus + workflow_state, nên set 2 cột là đủ & chính xác
        tái hiện điều kiện card==drill (predicate-level test, không phải flow test).
        """
        # Insert ở Draft (workflow validation chặn nhảy thẳng Draft→Awarded).
        pd = frappe.get_doc({"doctype": "IMM Procurement Decision",
                             "workflow_state": "Draft"})
        pd.flags.ignore_mandatory = True
        pd.insert(ignore_permissions=True)
        docstatus = {"draft": 0, "submit": 1, "cancel": 2}[mode]
        frappe.db.set_value(
            "IMM Procurement Decision", pd.name,
            {"workflow_state": state, "docstatus": docstatus},
            update_modified=False)
        cls._pds.append(pd.name)
        return pd.name

    @staticmethod
    def _kpi_states() -> dict:
        from assetcore.api.imm03 import _dashboard_kpis
        return dict(_dashboard_kpis()["decision_states"])

    @staticmethod
    def _drill_total(state: str, *, extra: dict | None = None) -> int:
        from assetcore.api.imm03 import _list_decisions
        f = {"workflow_state": state}
        if extra:
            f.update(extra)
        return _list_decisions(json.dumps(f), 1, 20)["total"]

    # ── tests ─────────────────────────────────────────────────────────────────

    def test_parity_01_awarded(self):
        """TC-03-PARITY-01: KPI[Awarded] == drill(Awarded).total (DELTA-stable)."""
        kpi = self._kpi_states().get("Awarded", 0)
        total = self._drill_total("Awarded")
        self.assertEqual(kpi, total,
                         "INV-DEC-DRILL GÃY (Awarded): tile != list total")
        # DELTA seeded = 2 submit + 1 draft = 3 (cancelled KHÔNG tính).
        self.assertEqual(kpi - self._baseline_kpi.get("Awarded", 0), self._PER_STATE)

    def test_parity_02_pending_and_po(self):
        """TC-03-PARITY-02: parity cho 'Pending Approval' và 'PO Issued'."""
        for s in ("Pending Approval", "PO Issued"):
            with self.subTest(state=s):
                kpi = self._kpi_states().get(s, 0)
                total = self._drill_total(s)
                self.assertEqual(kpi, total,
                                 f"INV-DEC-DRILL GÃY ({s}): tile != list total")
                self.assertEqual(kpi - self._baseline_kpi.get(s, 0),
                                 self._PER_STATE)

    def test_parity_03_cancelled_excluded_both_branches(self):
        """TC-03-PARITY-03: docstatus=2 (cancelled) KHÔNG xuất hiện ở CẢ 2 nhánh."""
        # KPI[Awarded] DELTA = 3 (chỉ docstatus<2), KHÔNG +1 vì cancelled.
        kpi_delta = self._kpi_states().get("Awarded", 0) - \
            self._baseline_kpi.get("Awarded", 0)
        self.assertEqual(kpi_delta, self._PER_STATE,
                         "Cancelled bị KPI đếm nhầm (docstatus<2 không loại=2)")
        # Drill DELTA = 3 (chống lệch docstatus: drill KHÔNG đếm cancelled).
        drill_delta = self._drill_total("Awarded") - \
            self._baseline_total["Awarded"]
        self.assertEqual(drill_delta, self._PER_STATE,
                         "Cancelled lọt vào drill → card!=drill (root bug)")
        # Cancelled record CÓ tồn tại trong DB với state Awarded (sanity: chứng
        # minh bài test có sức ép — nếu predicate sai sẽ đếm thêm nó).
        self.assertEqual(
            frappe.db.get_value("IMM Procurement Decision",
                                self._cancelled_name, "docstatus"), 2)
        # Override docstatus=2 → drill PHẢI thấy đúng cancelled (predicate
        # mặc định không che data audit khi caller chủ động yêu cầu).
        canc_total = self._drill_total("Awarded", extra={"docstatus": 2})
        self.assertGreaterEqual(canc_total, 1,
                                "Override docstatus=2 phải truy được cancelled")

    def test_parity_04_draft_counted_both_branches(self):
        """TC-03-PARITY-04: docstatus=0 (draft) ĐẾM ở CẢ 2 nhánh (docstatus<2)."""
        # Seed có 1 draft mỗi state. Nếu predicate là docstatus=1 (lệch) thì
        # draft bị loại ở 1 nhánh → KPI != drill. Parity 01/02 đã phủ; bổ sung
        # khẳng định draft hiện diện: drill Awarded chứa ÍT NHẤT 1 record draft.
        from assetcore.api.imm03 import _list_decisions
        res = _list_decisions(json.dumps({"workflow_state": "Awarded"}), 1, 100)
        names = {it["name"] for it in res["items"]}
        draft_names = [
            n for n in self._pds
            if frappe.db.get_value("IMM Procurement Decision", n, "docstatus") == 0
            and frappe.db.get_value("IMM Procurement Decision", n,
                                    "workflow_state") == "Awarded"
        ]
        self.assertTrue(draft_names, "fixture: phải có ÍT NHẤT 1 draft Awarded")
        for dn in draft_names:
            self.assertIn(dn, names,
                          "Draft (docstatus=0) bị drill loại → lệch docstatus<2")
        # Và KPI cũng đếm draft (parity 01 đã đảm bảo == drill, ở đây tái khẳng định).
        self.assertEqual(self._kpi_states().get("Awarded", 0), res["total"])

    def test_parity_05_cross_state_isolation(self):
        """TC-03-PARITY-05: cross-state isolation — count của 1 state KHÔNG bị
        trộn record của state khác (ngữ nghĩa kế thừa từ bộ absolute-count cũ,
        viết lại DELTA-stable để chống flaky trên DB miyano chung).

        Đo KPI[Awarded] trước, seed thêm record NHIỄU ở 'Pending Approval', đo lại:
        KPI[Awarded] PHẢI bất biến (record state khác KHÔNG lọt vào count Awarded);
        đồng thời KPI[Pending Approval] PHẢI tăng đúng số seeded — chứng minh
        predicate group-by-state cô lập đúng, KHÔNG gộp nhầm cross-state."""
        awarded_before = self._kpi_states().get("Awarded", 0)
        awarded_drill_before = self._drill_total("Awarded")
        pending_before = self._kpi_states().get("Pending Approval", 0)
        pending_drill_before = self._drill_total("Pending Approval")

        # Seed 2 record NHIỄU ở state khác (Pending Approval): 1 submit + 1 draft.
        noise = [self._mk_pd("Pending Approval", mode="submit"),
                 self._mk_pd("Pending Approval", mode="draft")]
        frappe.db.commit()

        # Awarded KHÔNG bị trộn record Pending Approval (cả KPI lẫn drill bất biến).
        self.assertEqual(self._kpi_states().get("Awarded", 0), awarded_before,
                         "Record Pending Approval LỌT vào count Awarded (KPI trộn state)")
        self.assertEqual(self._drill_total("Awarded"), awarded_drill_before,
                         "Record Pending Approval LỌT vào drill Awarded (drill trộn state)")
        # Pending Approval tăng đúng 2 (predicate đếm đúng state vừa seed) — cả 2 nhánh.
        self.assertEqual(self._kpi_states().get("Pending Approval", 0),
                         pending_before + len(noise),
                         "KPI Pending Approval không tăng đúng số record vừa seed")
        self.assertEqual(self._drill_total("Pending Approval"),
                         pending_drill_before + len(noise),
                         "Drill Pending Approval không tăng đúng số record vừa seed")
        # Bất biến card==drill vẫn giữ cho CẢ 2 state (cô lập không phá parity).
        for st in ("Awarded", "Pending Approval"):
            with self.subTest(state=st):
                self.assertEqual(self._kpi_states().get(st, 0),
                                 self._drill_total(st),
                                 f"INV-DEC-DRILL GÃY ({st}) sau seed cross-state")
