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
from frappe.tests.utils import FrappeTestCase


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


class TestParseWeighting(FrappeTestCase):

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


class TestParseJsonField(FrappeTestCase):

    def test_none_returns_empty_dict(self):
        self.assertEqual(_parse_json_field(None), {})

    def test_dict_passthrough(self):
        d = {"k": 1}
        self.assertEqual(_parse_json_field(d), d)

    def test_valid_json_string(self):
        self.assertEqual(_parse_json_field('{"a": 2}'), {"a": 2})

    def test_invalid_json_returns_empty(self):
        self.assertEqual(_parse_json_field("not-json"), {})


class TestComputeEvalScores(FrappeTestCase):

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


class TestResolveRecommendation(FrappeTestCase):
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


class TestGateG04Method(FrappeTestCase):

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


class TestMethodRules(FrappeTestCase):
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


class TestActualDeliveryDefault(FrappeTestCase):
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


class TestReceiptAgainstPO(FrappeTestCase):
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

class TestAvlLiveSoT(FrappeTestCase):
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


class TestEvalTieAuditEvent(FrappeTestCase):
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

class TestDecisionCardDrillParity(FrappeTestCase):
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


# ──────────────────────────────────────────────────────────────────────────────
# IMM-03 — Server-driven CTA (GATE-8 / LL-FE-51): get_decision emit
#   `allowed_transitions = _DECISION_VALID_TRANSITIONS.get(workflow_state, [])`.
#
# BUG gốc (client-map DESYNC): FE DecisionDetailView giữ hằng TRANSITIONS_BY_STATE
# THIẾU hẳn nhánh 'Pending Approval' → nút 'Huỷ Decision' KHÔNG bao giờ render ⇒
# QTV / Procurement Manager KHÔNG huỷ được Decision dù fixture cấp quyền transition.
# Fix: BE là SoT — get_decision emit tập ACTION hợp lệ; FE chỉ render theo tập này.
#
# KHÁC IMM-05 (map next_state): map ACTION (nhãn transition) vì FE POST action sang
# transition_decision_workflow / award_decision / record_contract. allowed_transitions
# CHỈ là hint hiển thị (⊆ guard-permitted) — guard role trên apply_workflow vẫn là
# chốt enforcement thật, KHÔNG nới lỏng ở đây.
# ──────────────────────────────────────────────────────────────────────────────

class TestDecisionAllowedTransitions(FrappeTestCase):
    """get_decision(name).allowed_transitions == _DECISION_VALID_TRANSITIONS map
    cho MỖI workflow_state + invariant khớp fixture 'IMM-03 Decision Workflow'."""

    _pds: list[str]

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._pds = []
        cls.names: dict[str, str] = {}
        # 1 Decision cho mỗi state cần assert (insert ở Draft rồi ép state — workflow
        # validation chặn nhảy thẳng Draft→X; predicate get_decision chỉ đọc field).
        for state in (
            "Draft", "Method Selected", "Negotiation", "Award Recommended",
            "Pending Approval", "Awarded", "Contract Signed", "PO Issued", "Cancelled",
        ):
            cls.names[state] = cls._mk_pd(state)
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

    @classmethod
    def _mk_pd(cls, state: str) -> str:
        pd = frappe.get_doc({"doctype": "IMM Procurement Decision",
                             "workflow_state": "Draft"})
        pd.flags.ignore_mandatory = True
        pd.insert(ignore_permissions=True)
        frappe.db.set_value("IMM Procurement Decision", pd.name,
                            "workflow_state", state, update_modified=False)
        cls._pds.append(pd.name)
        return pd.name

    # ── TC-03-CTA-01: emit đúng tập ACTION cho mỗi state ─────────────────────────
    def test_get_decision_emits_allowed_transitions(self):
        from assetcore.api.imm03 import get_decision
        res = get_decision(self.names["Pending Approval"])["data"]
        self.assertIn("allowed_transitions", res,
                      "get_decision PHẢI emit key 'allowed_transitions' (server-driven CTA).")
        self.assertEqual(set(res["allowed_transitions"]),
                         {"Phê duyệt trúng thầu", "Huỷ Decision"})
        self.assertEqual(
            set(get_decision(self.names["Awarded"])["data"]["allowed_transitions"]),
            {"Ký HĐ"})
        self.assertEqual(
            set(get_decision(self.names["Draft"])["data"]["allowed_transitions"]),
            {"Chọn phương án"})
        # Trạng thái cuối → [] tường minh.
        self.assertEqual(
            get_decision(self.names["PO Issued"])["data"]["allowed_transitions"], [])
        self.assertEqual(
            get_decision(self.names["Cancelled"])["data"]["allowed_transitions"], [])

    # ── TC-03-CTA-02: invariant chống drift — map == fixture (mirror IMM-05) ──────
    def test_decision_allowed_transitions_matches_workflow_fixture(self):
        """INVARIANT: map BE == {state: set(action)} của fixture 'IMM-03 Decision
        Workflow'. Ai thêm/sửa transition mà quên map → test đỏ."""
        from pathlib import Path
        from assetcore.services.imm03 import _DECISION_VALID_TRANSITIONS
        wf_path = Path(frappe.get_app_path("assetcore")) / "fixtures" / "workflow.json"
        fixtures = json.loads(wf_path.read_text(encoding="utf-8"))
        wf = next(
            (w for w in fixtures if w.get("name") == "IMM-03 Decision Workflow"), None)
        self.assertIsNotNone(wf, "fixture 'IMM-03 Decision Workflow' KHÔNG tồn tại.")
        # Codomain gồm MỌI state (kể cả terminal không transition ra → set() rỗng).
        codomain: dict[str, set] = {s["state"]: set() for s in wf["states"]}
        for t in wf["transitions"]:
            codomain.setdefault(t["state"], set()).add(t["action"])
        self.assertEqual(
            set(_DECISION_VALID_TRANSITIONS.keys()), set(codomain.keys()),
            "Key-set map BE PHẢI == states[] fixture (thừa/thiếu state → drift).")
        for state, wf_actions in codomain.items():
            self.assertEqual(
                set(_DECISION_VALID_TRANSITIONS[state]), wf_actions,
                f"DRIFT '{state}': map {sorted(_DECISION_VALID_TRANSITIONS[state])} "
                f"!= fixture {sorted(wf_actions)}")

    # ── TC-03-CTA-03: regression đúng bug — Pending Approval lộ 'Huỷ Decision' ────
    def test_pending_approval_exposes_cancel_transition(self):
        """Đúng nhánh trước đây client-map bỏ sót: ở Pending Approval, 'Huỷ Decision'
        PHẢI có trong allowed_transitions (FE khôi phục nút Huỷ)."""
        from assetcore.api.imm03 import get_decision
        allowed = get_decision(self.names["Pending Approval"])["data"]["allowed_transitions"]
        self.assertIn("Huỷ Decision", allowed,
                      "'Huỷ Decision' PHẢI có ở Pending Approval — QTV/Procurement "
                      "Manager huỷ được (bug client-map DESYNC).")


# ──────────────────────────────────────────────────────────────────────────────
# IMM-03 — Server-driven CTA (GATE-8 / LL-FE-51) PARITY cho Vendor Evaluation:
#   get_evaluation emit `allowed_transitions = _EVAL_VALID_TRANSITIONS.get(state, [])`
#   (song song get_decision / _DECISION_VALID_TRANSITIONS).
#
# BUG gốc (client-map DESYNC): VendorEvalDetailView giữ hằng client TRANSITIONS_BY_STATE
# → QTV/Commissioning Manager thấy/bấm action không đúng quyền hoặc lệch khi workflow
# đổi. Fix: BE là SoT — get_evaluation emit tập ACTION hợp lệ; FE chỉ render theo tập
# này. allowed_transitions CHỈ là hint hiển thị (⊆ guard-permitted) — guard role trên
# apply_workflow (transition_eval_workflow) vẫn là chốt enforcement thật.
# ──────────────────────────────────────────────────────────────────────────────

class TestEvalAllowedTransitions(FrappeTestCase):
    """get_evaluation(name).allowed_transitions == _EVAL_VALID_TRANSITIONS map cho
    MỖI workflow_state + invariant khớp fixture 'IMM-03 Vendor Eval Workflow'."""

    _ves: list[str]

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._ves = []
        cls.names: dict[str, str] = {}
        # 1 Evaluation cho mỗi state cần assert (insert ở Draft rồi ép state —
        # workflow validation chặn nhảy thẳng; predicate get_evaluation chỉ đọc field).
        for state in ("Draft", "Open RFQ", "Quotation Received", "Evaluated", "Cancelled"):
            cls.names[state] = cls._mk_ve(state)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        for name in cls._ves:
            try:
                frappe.db.set_value(_DT_VE, name, "docstatus", 0,
                                    update_modified=False)
                frappe.delete_doc(_DT_VE, name, force=1, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @classmethod
    def _mk_ve(cls, state: str) -> str:
        ve = frappe.get_doc({"doctype": _DT_VE, "workflow_state": "Draft"})
        ve.flags.ignore_mandatory = True
        ve.insert(ignore_permissions=True)
        frappe.db.set_value(_DT_VE, ve.name, "workflow_state", state,
                            update_modified=False)
        cls._ves.append(ve.name)
        return ve.name

    # ── TC-03-EVAL-CTA-01: emit đúng tập ACTION cho mỗi state ─────────────────────
    def test_get_evaluation_emits_allowed_transitions(self):
        from assetcore.api.imm03 import get_evaluation
        res = get_evaluation(self.names["Quotation Received"])["data"]
        self.assertIn("allowed_transitions", res,
                      "get_evaluation PHẢI emit key 'allowed_transitions' (server-driven CTA).")
        self.assertEqual(res["allowed_transitions"],
                         ["Hoàn tất chấm điểm", "Huỷ Eval"])
        self.assertEqual(
            get_evaluation(self.names["Draft"])["data"]["allowed_transitions"],
            ["Mở RFQ"])
        self.assertEqual(
            set(get_evaluation(self.names["Open RFQ"])["data"]["allowed_transitions"]),
            {"Nhận báo giá xong", "Huỷ Eval"})
        # Trạng thái cuối → [] tường minh (không nút transition).
        self.assertEqual(
            get_evaluation(self.names["Evaluated"])["data"]["allowed_transitions"], [])
        self.assertEqual(
            get_evaluation(self.names["Cancelled"])["data"]["allowed_transitions"], [])

    # ── TC-03-EVAL-CTA-02: invariant chống drift — map == fixture (parity Decision) ─
    def test_eval_allowed_transitions_matches_workflow_fixture(self):
        """INVARIANT: map BE == {state: set(action)} của fixture 'IMM-03 Vendor Eval
        Workflow'. Ai thêm/sửa transition mà quên map → test đỏ (equality, chống
        thiếu/thừa desync)."""
        from pathlib import Path
        from assetcore.services.imm03 import _EVAL_VALID_TRANSITIONS
        wf_path = Path(frappe.get_app_path("assetcore")) / "fixtures" / "workflow.json"
        fixtures = json.loads(wf_path.read_text(encoding="utf-8"))
        wf = next(
            (w for w in fixtures if w.get("name") == "IMM-03 Vendor Eval Workflow"), None)
        self.assertIsNotNone(wf, "fixture 'IMM-03 Vendor Eval Workflow' KHÔNG tồn tại.")
        # Codomain gồm MỌI state (kể cả terminal không transition ra → set() rỗng).
        codomain: dict[str, set] = {s["state"]: set() for s in wf["states"]}
        for t in wf["transitions"]:
            codomain.setdefault(t["state"], set()).add(t["action"])
        self.assertEqual(
            set(_EVAL_VALID_TRANSITIONS.keys()), set(codomain.keys()),
            "Key-set map BE PHẢI == states[] fixture (thừa/thiếu state → drift).")
        for state, wf_actions in codomain.items():
            self.assertEqual(
                set(_EVAL_VALID_TRANSITIONS[state]), wf_actions,
                f"DRIFT '{state}': map {sorted(_EVAL_VALID_TRANSITIONS[state])} "
                f"!= fixture {sorted(wf_actions)}")


# ──────────────────────────────────────────────────────────────────────────────
# IMM-03 — Server-driven CTA (GATE-8 / LL-FE-51) cho AVL Entry (workflow 3/3):
#   get_avl/list_avl emit `allowed_transitions` = svc.avl_allowed_transitions(
#   workflow_state, user_roles) — LỌC theo role caller (⊆ tập được phép). SoT =
#   `_AVL_VALID_TRANSITIONS` (RICHER: (action, next_state, allowed_roles)).
#
# BUG gốc: get_avl passthrough as_dict() thô (không emit allowed_transitions) +
# AvlListView hardcode `workflow_state==='Draft'|'Approved'|'Conditional'` → nút
# 'Phục hồi Approved' (Conditional/Suspended→Approved) BE+fixture cho phép nhưng
# FE giấu = dead-functionality. Fix: BE là SoT — FE gate theo tập này.
# ──────────────────────────────────────────────────────────────────────────────

_DT_AVL = "IMM AVL Entry"


class TestAvlAllowedTransitions(FrappeTestCase):
    """get_avl/list_avl emit allowed_transitions đúng theo workflow_state + invariant
    map == fixture 'IMM-03 AVL Workflow' (parity Decision/Eval)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._avls: list[str] = []
        cls._suppliers: list[str] = []
        cls._cats: list[str] = []
        cls.supplier = cls._mk_supplier()
        cls.cat = cls._mk_cat()
        cls.names: dict[str, str] = {}
        for state in ("Draft", "Approved", "Conditional", "Suspended", "Expired"):
            cls.names[state] = cls._mk_avl(state)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._avls:
            try:
                frappe.db.set_value(_DT_AVL, name, "docstatus", 0, update_modified=False)
                frappe.delete_doc(_DT_AVL, name, force=1, ignore_permissions=True)
            except Exception:
                pass
        for c in cls._cats:
            try:
                frappe.delete_doc("AC Asset Category", c, force=1, ignore_permissions=True)
            except Exception:
                pass
        for s in cls._suppliers:
            try:
                frappe.delete_doc("AC Supplier", s, force=1, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    @classmethod
    def _mk_supplier(cls) -> str:
        d = frappe.get_doc({"doctype": "AC Supplier",
                            "supplier_name": f"_T-AVLCTA-SUP-{frappe.generate_hash(length=6)}"})
        d.flags.ignore_mandatory = True
        d.insert(ignore_permissions=True)
        cls._suppliers.append(d.name)
        return d.name

    @classmethod
    def _mk_cat(cls) -> str:
        c = frappe.get_doc({"doctype": "AC Asset Category",
                            "category_name": f"_T-AVLCTA-CAT-{frappe.generate_hash(length=6)}",
                            "category_code": f"AC{frappe.generate_hash(length=4)}"})
        c.flags.ignore_mandatory = True
        c.insert(ignore_permissions=True)
        cls._cats.append(c.name)
        return c.name

    @classmethod
    def _mk_avl(cls, state: str) -> str:
        from frappe.utils import today
        avl = frappe.get_doc({"doctype": _DT_AVL, "supplier": cls.supplier,
                              "device_category": cls.cat, "validity_years": 2,
                              "valid_from": today()})
        avl.flags.ignore_mandatory = True
        avl.insert(ignore_permissions=True)
        cls._avls.append(avl.name)
        if state != "Draft":
            avl.submit()  # docstatus 1 (workflow_state vẫn Draft → activate_avl skip)
        frappe.db.set_value(_DT_AVL, avl.name, "workflow_state", state,
                            update_modified=False)
        return avl.name

    # ── TC-03-AVL-CTA-01: invariant map == fixture EXACT (state,action,next,roles) ──
    def test_avl_allowed_transitions_matches_workflow_fixture(self):
        """INVARIANT chống desync: (state, action, next_state, roles) của
        _AVL_VALID_TRANSITIONS == fixture 'IMM-03 AVL Workflow' (equality)."""
        from pathlib import Path
        from assetcore.services.imm03 import _AVL_VALID_TRANSITIONS
        wf_path = Path(frappe.get_app_path("assetcore")) / "fixtures" / "workflow.json"
        fixtures = json.loads(wf_path.read_text(encoding="utf-8"))
        wf = next((w for w in fixtures if w.get("name") == "IMM-03 AVL Workflow"), None)
        self.assertIsNotNone(wf, "fixture 'IMM-03 AVL Workflow' KHÔNG tồn tại.")
        # (state, action, next_state) — dedupe rows role-nhân-bản của fixture.
        fixture_edges = {(t["state"], t["action"], t["next_state"]) for t in wf["transitions"]}
        map_edges = {(state, action, next_state)
                     for state, rows in _AVL_VALID_TRANSITIONS.items()
                     for action, next_state, _roles in rows}
        self.assertEqual(
            map_edges, fixture_edges,
            "DRIFT _AVL_VALID_TRANSITIONS(edges) != fixture 'IMM-03 AVL Workflow'")
        # Key-set == states[] (kể cả terminal Expired → [] nhưng CÓ key).
        self.assertEqual(set(_AVL_VALID_TRANSITIONS.keys()),
                         {s["state"] for s in wf["states"]})
        # Role parity: allowed_roles mỗi edge == union 'allowed' fixture cho edge đó.
        fixture_roles: dict[tuple, set] = {}
        for t in wf["transitions"]:
            fixture_roles.setdefault(
                (t["state"], t["action"], t["next_state"]), set()).add(t["allowed"])
        for state, rows in _AVL_VALID_TRANSITIONS.items():
            for action, next_state, roles in rows:
                self.assertEqual(
                    set(roles), fixture_roles[(state, action, next_state)],
                    f"ROLE DRIFT {state}/{action}: map {sorted(roles)} != "
                    f"fixture {sorted(fixture_roles[(state, action, next_state)])}")

    # ── TC-03-AVL-CTA-02: get_avl emit đúng tập ACTION cho mỗi state (Admin=full) ──
    def test_get_avl_emits_allowed_transitions(self):
        from assetcore.api.imm03 import get_avl
        self.assertEqual(
            get_avl(self.names["Draft"])["data"]["allowed_transitions"],
            ["Phê duyệt AVL", "Cấp Conditional"])
        self.assertEqual(
            get_avl(self.names["Approved"])["data"]["allowed_transitions"],
            ["Hạ xuống Conditional", "Đình chỉ"])
        self.assertEqual(
            get_avl(self.names["Conditional"])["data"]["allowed_transitions"],
            ["Phục hồi Approved", "Đình chỉ"])
        self.assertEqual(
            get_avl(self.names["Suspended"])["data"]["allowed_transitions"],
            ["Phục hồi Approved"])
        # Trạng thái cuối → [] tường minh (0 nút).
        self.assertEqual(
            get_avl(self.names["Expired"])["data"]["allowed_transitions"], [])

    # ── TC-03-AVL-CTA-03: list_avl emit allowed_transitions MỖI row ───────────────
    def test_list_avl_emits_allowed_transitions_per_row(self):
        from assetcore.api.imm03 import list_avl
        res = list_avl(json.dumps({"supplier": self.supplier}))["data"]
        by_state = {it["workflow_state"]: it.get("allowed_transitions")
                    for it in res["items"]}
        self.assertEqual(by_state.get("Draft"), ["Phê duyệt AVL", "Cấp Conditional"])
        self.assertEqual(by_state.get("Approved"), ["Hạ xuống Conditional", "Đình chỉ"])
        self.assertEqual(by_state.get("Suspended"), ["Phục hồi Approved"])
        self.assertEqual(by_state.get("Expired"), [])
        # MỖI row PHẢI carry key (không sót row nào).
        for it in res["items"]:
            self.assertIn("allowed_transitions", it)

    # ── TC-03-AVL-CTA-04: Suspended lộ 'Phục hồi Approved' (đóng dead-functionality) ─
    def test_suspended_exposes_restore_transition(self):
        from assetcore.api.imm03 import get_avl
        allowed = get_avl(self.names["Suspended"])["data"]["allowed_transitions"]
        self.assertIn("Phục hồi Approved", allowed,
                      "'Phục hồi Approved' PHẢI có ở Suspended (BE+fixture cho phép, "
                      "trước đây FE giấu vì chỉ gate Draft → dead-functionality).")

    # ── TC-03-AVL-CTA-05: role filter — user thiếu role → allowed_transitions rỗng ─
    def test_allowed_transitions_filtered_by_role(self):
        """SSoT derive LỌC theo role: user không có Procurement/Spec/Admin role →
        [] (degrade an toàn, FE 0 nút, không dead-control 403)."""
        from assetcore.services.imm03 import avl_allowed_transitions
        low = {"AssetCore System User", "All"}
        self.assertEqual(avl_allowed_transitions("Draft", low), [])
        self.assertEqual(avl_allowed_transitions("Approved", low), [])
        # Đủ role (Spec Manager) → thấy đúng action mình được phép.
        spec = {"Spec Manager"}
        self.assertEqual(avl_allowed_transitions("Approved", spec),
                         ["Hạ xuống Conditional", "Đình chỉ"])
        # Procurement Manager KHÔNG có 'Cấp Conditional' (Spec-only) ở Draft.
        proc = {"Procurement Manager"}
        self.assertEqual(avl_allowed_transitions("Draft", proc), ["Phê duyệt AVL"])


class TestAvlTransitionEnforcement(FrappeTestCase):
    """approve_avl/suspend_avl: SoT-gated + role-enforced (LL-BE-62), approver derive
    session (chống spoof). Đóng root-cause 'không duyệt được dù đủ quyền'."""

    _LOW_USER = "_t_avl_lowrole@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._avls: list[str] = []
        cls._suppliers: list[str] = []
        cls._cats: list[str] = []
        # Low-role user (chỉ base role, KHÔNG có role transition nào của AVL).
        if not frappe.db.exists("User", cls._LOW_USER):
            u = frappe.get_doc({
                "doctype": "User", "email": cls._LOW_USER,
                "first_name": "AVL LowRole", "send_welcome_email": 0,
                "roles": [{"role": "AssetCore System User"}],
            })
            u.flags.ignore_permissions = True
            u.insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._avls:
            frappe.db.sql("DELETE FROM `tabIMM Audit Trail` "
                          "WHERE ref_doctype=%s AND ref_name=%s", (_DT_AVL, name))
            try:
                frappe.db.set_value(_DT_AVL, name, "docstatus", 0, update_modified=False)
                frappe.delete_doc(_DT_AVL, name, force=1, ignore_permissions=True)
            except Exception:
                pass
        for c in cls._cats:
            try:
                frappe.delete_doc("AC Asset Category", c, force=1, ignore_permissions=True)
            except Exception:
                pass
        for s in cls._suppliers:
            try:
                frappe.delete_doc("AC Supplier", s, force=1, ignore_permissions=True)
            except Exception:
                pass
        try:
            frappe.delete_doc("User", cls._LOW_USER, force=1, ignore_permissions=True)
        except Exception:
            pass
        frappe.db.commit()

    # ── fixtures ────────────────────────────────────────────────────────────────

    def _supplier(self) -> str:
        d = frappe.get_doc({"doctype": "AC Supplier",
                            "supplier_name": f"_T-AVLENF-SUP-{frappe.generate_hash(length=6)}"})
        d.flags.ignore_mandatory = True
        d.insert(ignore_permissions=True)
        type(self)._suppliers.append(d.name)
        return d.name

    def _cat(self) -> str:
        c = frappe.get_doc({"doctype": "AC Asset Category",
                            "category_name": f"_T-AVLENF-CAT-{frappe.generate_hash(length=6)}",
                            "category_code": f"AE{frappe.generate_hash(length=4)}"})
        c.flags.ignore_mandatory = True
        c.insert(ignore_permissions=True)
        type(self)._cats.append(c.name)
        return c.name

    def _mk_draft_avl(self, supplier=None, cat=None) -> str:
        from frappe.utils import today
        avl = frappe.get_doc({"doctype": _DT_AVL,
                              "supplier": supplier or self._supplier(),
                              "device_category": cat or self._cat(),
                              "validity_years": 2, "valid_from": today()})
        avl.flags.ignore_mandatory = True
        avl.insert(ignore_permissions=True)  # docstatus 0, workflow_state Draft
        type(self)._avls.append(avl.name)
        return avl.name

    def _mk_approved_avl(self):
        """Trả (name, supplier) — AVL Approved (docstatus 1) + supplier synced."""
        from frappe.utils import add_days, today
        sup = self._supplier()
        name = self._mk_draft_avl(supplier=sup, cat=self._cat())
        avl = frappe.get_doc(_DT_AVL, name)
        avl.submit()
        frappe.db.set_value(_DT_AVL, name,
                            {"workflow_state": "Approved",
                             "valid_to": add_days(today(), 365)},
                            update_modified=False)
        from assetcore.services.imm03 import _sync_supplier_avl_status
        _sync_supplier_avl_status(sup)
        return name, sup

    # ── TC-03-AVL-ENF-01: approver spoof bị ignore (derive session) ───────────────
    def test_approve_ignores_client_approver_spoof(self):
        from assetcore.api.imm03 import _approve_avl
        name = self._mk_draft_avl()
        _approve_avl(name)
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "approver"),
                         frappe.session.user)
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"),
                         "Approved")

    def test_approve_whitelist_swallows_legacy_approver_kwarg(self):
        """Whitelist approve_avl(name, approver='hacker@x.vn') → **_ignore nuốt
        (back-compat OpenAPI/mobile); avl.approver == session, KHÔNG spoof."""
        from assetcore.api.imm03 import approve_avl
        name = self._mk_draft_avl()
        res = approve_avl(name, approver="hacker@x.vn")  # legacy kwarg
        self.assertTrue(res["success"])
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "approver"),
                         frappe.session.user)
        self.assertNotEqual(frappe.db.get_value(_DT_AVL, name, "approver"),
                            "hacker@x.vn")

    # ── TC-03-AVL-ENF-02: approve Draft→Approved thành công (đủ quyền) ────────────
    def test_approve_from_draft_success(self):
        from assetcore.api.imm03 import _approve_avl
        name = self._mk_draft_avl()
        res = _approve_avl(name)
        self.assertEqual(res["workflow_state"], "Approved")
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"),
                         "Approved")

    # ── TC-03-AVL-ENF-03: suspend từ Draft KHÔNG có trong SoT → reject BAD_STATE ──
    def test_suspend_from_draft_rejected(self):
        from assetcore.api.imm03 import _suspend_avl
        name = self._mk_draft_avl()
        with self.assertRaises(ServiceError) as cm:
            _suspend_avl(name, "Lý do đình chỉ")
        self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE)
        # KHÔNG bị đổi state (ad-hoc branch cũ cho phép mọi state đã bị siết).
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Draft")

    # ── TC-03-AVL-ENF-04: suspend Approved→Suspended OK + _sync gọi ───────────────
    def test_suspend_from_approved_success_syncs_supplier(self):
        from assetcore.api.imm03 import _suspend_avl
        name, sup = self._mk_approved_avl()
        # supplier có AVL active → imm_avl_status Approved trước khi đình chỉ
        if frappe.db.has_column("AC Supplier", "imm_avl_status"):
            self.assertEqual(
                frappe.db.get_value("AC Supplier", sup, "imm_avl_status"), "Approved")
        res = _suspend_avl(name, "Phát hiện vi phạm ISO 13485")
        self.assertEqual(res["workflow_state"], "Suspended")
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Suspended")
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "suspension_reason"),
                         "Phát hiện vi phạm ISO 13485")
        # _sync gọi → AVL active DUY NHẤT bị đình chỉ → supplier về Expired.
        if frappe.db.has_column("AC Supplier", "imm_avl_status"):
            self.assertEqual(
                frappe.db.get_value("AC Supplier", sup, "imm_avl_status"), "Expired")

    # ── TC-03-AVL-ENF-05: restore Suspended→Approved qua 'Phục hồi Approved' ──────
    def test_restore_from_suspended_success(self):
        from assetcore.api.imm03 import _approve_avl, _suspend_avl
        name, _sup = self._mk_approved_avl()
        _suspend_avl(name, "tạm dừng do audit")
        res = _approve_avl(name)  # Suspended → Approved
        self.assertEqual(res["workflow_state"], "Approved")
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Approved")

    # ── TC-03-AVL-ENF-06: user thiếu role → approve/suspend raise FORBIDDEN ───────
    def test_approve_low_role_rejected(self):
        from assetcore.api.imm03 import _approve_avl
        name = self._mk_draft_avl()
        frappe.set_user(self._LOW_USER)
        try:
            with self.assertRaises(ServiceError) as cm:
                _approve_avl(name)
            self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        finally:
            frappe.set_user("Administrator")
        # Guard fail-fast → state KHÔNG đổi (vẫn Draft).
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Draft")

    def test_suspend_low_role_rejected(self):
        from assetcore.api.imm03 import _suspend_avl
        name, _sup = self._mk_approved_avl()
        frappe.set_user(self._LOW_USER)
        try:
            with self.assertRaises(ServiceError) as cm:
                _suspend_avl(name, "lý do bất kỳ")
            self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Approved")

    # ── TC-03-AVL-ENF-07: approve từ Expired (ngoài SoT) → BAD_STATE ──────────────
    def test_approve_from_expired_rejected(self):
        from assetcore.api.imm03 import _approve_avl
        name, _sup = self._mk_approved_avl()
        frappe.db.set_value(_DT_AVL, name, "workflow_state", "Expired",
                            update_modified=False)
        with self.assertRaises(ServiceError) as cm:
            _approve_avl(name)
        self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE)


# ─────────────────────────────────────────────────────────────────────────────
# CR-WF-03-AVL-COND — set_avl_conditional (đóng "hidden-CTA-câm")
#
# 2 nhãn action Conditional ĐÃ ở SoT `_AVL_VALID_TRANSITIONS` + fixture 'IMM-03
# AVL Workflow' + phát qua `allowed_transitions` (list_avl/get_avl) NHƯNG chưa có
# endpoint → FE render nút → click 404 câm. Endpoint mới `set_avl_conditional`:
#   Draft    → Conditional  (action 'Cấp Conditional',      submit doc 0→1, mirror _approve_avl nhánh Draft)
#   Approved → Conditional  (action 'Hạ xuống Conditional', db.set_value submitted, mirror _suspend_avl)
# reuse field `condition_notes` (Long Text SẴN CÓ) — KHÔNG migrate.
# ─────────────────────────────────────────────────────────────────────────────
class TestAvlConditional(FrappeTestCase):
    """set_avl_conditional: Draft→Conditional (submit) + Approved→Conditional
    (db.set_value) — SoT-gated + role-enforced (LL-BE-62), condition_notes bắt buộc
    (parity suspension_reason), _sync_supplier + 1 audit 'State Change'."""

    _LOW_USER = "_t_avlcond_lowrole@example.com"
    _SPEC_USER = "_t_avlcond_specmgr@example.com"

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls._avls: list[str] = []
        cls._suppliers: list[str] = []
        cls._cats: list[str] = []
        # Low-role user (chỉ base role, KHÔNG có role transition nào của AVL) → FORBIDDEN.
        if not frappe.db.exists("User", cls._LOW_USER):
            u = frappe.get_doc({
                "doctype": "User", "email": cls._LOW_USER,
                "first_name": "AVLCond LowRole", "send_welcome_email": 0,
                "roles": [{"role": "AssetCore System User"}],
            })
            u.flags.ignore_permissions = True
            u.insert(ignore_permissions=True)
        # Spec Manager user — AC2: Spec Manager thực hiện được CẢ 2 nhánh Conditional.
        if not frappe.db.exists("User", cls._SPEC_USER):
            u = frappe.get_doc({
                "doctype": "User", "email": cls._SPEC_USER,
                "first_name": "AVLCond SpecMgr", "send_welcome_email": 0,
                "roles": [{"role": "AssetCore System User"}, {"role": "Spec Manager"}],
            })
            u.flags.ignore_permissions = True
            u.insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        for name in cls._avls:
            frappe.db.sql("DELETE FROM `tabIMM Audit Trail` "
                          "WHERE ref_doctype=%s AND ref_name=%s", (_DT_AVL, name))
            try:
                frappe.db.set_value(_DT_AVL, name, "docstatus", 0, update_modified=False)
                frappe.delete_doc(_DT_AVL, name, force=1, ignore_permissions=True)
            except Exception:
                pass
        for c in cls._cats:
            try:
                frappe.delete_doc("AC Asset Category", c, force=1, ignore_permissions=True)
            except Exception:
                pass
        for s in cls._suppliers:
            try:
                frappe.delete_doc("AC Supplier", s, force=1, ignore_permissions=True)
            except Exception:
                pass
        for user in (cls._LOW_USER, cls._SPEC_USER):
            try:
                frappe.delete_doc("User", user, force=1, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()

    # ── fixtures (mirror TestAvlTransitionEnforcement) ────────────────────────────
    def _supplier(self) -> str:
        d = frappe.get_doc({"doctype": "AC Supplier",
                            "supplier_name": f"_T-AVLCOND-SUP-{frappe.generate_hash(length=6)}"})
        d.flags.ignore_mandatory = True
        d.insert(ignore_permissions=True)
        type(self)._suppliers.append(d.name)
        return d.name

    def _cat(self) -> str:
        c = frappe.get_doc({"doctype": "AC Asset Category",
                            "category_name": f"_T-AVLCOND-CAT-{frappe.generate_hash(length=6)}",
                            "category_code": f"AC{frappe.generate_hash(length=4)}"})
        c.flags.ignore_mandatory = True
        c.insert(ignore_permissions=True)
        type(self)._cats.append(c.name)
        return c.name

    def _mk_draft_avl(self, supplier=None, cat=None) -> str:
        from frappe.utils import today
        avl = frappe.get_doc({"doctype": _DT_AVL,
                              "supplier": supplier or self._supplier(),
                              "device_category": cat or self._cat(),
                              "validity_years": 2, "valid_from": today()})
        avl.flags.ignore_mandatory = True
        avl.insert(ignore_permissions=True)  # docstatus 0, workflow_state Draft
        type(self)._avls.append(avl.name)
        return avl.name

    def _mk_approved_avl(self):
        """Trả (name, supplier) — AVL Approved (docstatus 1) + supplier synced."""
        from frappe.utils import add_days, today
        sup = self._supplier()
        name = self._mk_draft_avl(supplier=sup, cat=self._cat())
        avl = frappe.get_doc(_DT_AVL, name)
        avl.submit()
        frappe.db.set_value(_DT_AVL, name,
                            {"workflow_state": "Approved",
                             "valid_to": add_days(today(), 365)},
                            update_modified=False)
        _sync_supplier_avl_status(sup)
        return name, sup

    def _count_state_change_audit(self, name: str) -> int:
        return frappe.db.count("IMM Audit Trail",
                               {"ref_doctype": _DT_AVL, "ref_name": name,
                                "event_type": "State Change"})

    # ── BE-TC1: Draft + Spec role + notes → Conditional docstatus=1 + notes lưu ────
    def test_grant_conditional_from_draft(self):
        from assetcore.api.imm03 import _set_avl_conditional
        name = self._mk_draft_avl()
        res = _set_avl_conditional(name, "Chỉ đạt 2/3 tiêu chí")
        self.assertEqual(res["workflow_state"], "Conditional")
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Conditional")
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "docstatus"), 1)  # submit 0→1
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "condition_notes"),
                         "Chỉ đạt 2/3 tiêu chí")

    # ── BE-TC2: Approved (submitted) → Conditional qua db.set_value, docstatus giữ 1 ─
    def test_downgrade_conditional_from_approved(self):
        from assetcore.api.imm03 import _set_avl_conditional
        name, _sup = self._mk_approved_avl()
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "docstatus"), 1)
        res = _set_avl_conditional(name, "Vi phạm nhẹ điều khoản giao hàng")
        self.assertEqual(res["workflow_state"], "Conditional")
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Conditional")
        # KHÔNG re-submit — docstatus vẫn 1 (không nhảy 2 hay reset 0).
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "docstatus"), 1)
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "condition_notes"),
                         "Vi phạm nhẹ điều khoản giao hàng")

    # ── BE-TC3: condition_notes rỗng/whitespace → VALIDATION ──────────────────────
    def test_empty_condition_notes_rejected(self):
        from assetcore.api.imm03 import _set_avl_conditional
        name = self._mk_draft_avl()
        for bad in ("", "   ", "\n\t "):
            with self.assertRaises(ServiceError) as cm:
                _set_avl_conditional(name, bad)
            self.assertEqual(cm.exception.code, ErrorCode.VALIDATION)
        # Không side-effect: vẫn Draft (docstatus 0).
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Draft")

    # ── BE-TC4: state ∈ {Conditional, Suspended, Expired} → BAD_STATE (reject cạnh) ─
    def test_out_of_sot_states_rejected(self):
        from assetcore.api.imm03 import _set_avl_conditional
        for bad_state in ("Conditional", "Suspended", "Expired"):
            name, _sup = self._mk_approved_avl()
            frappe.db.set_value(_DT_AVL, name, "workflow_state", bad_state,
                                update_modified=False)
            with self.assertRaises(ServiceError) as cm:
                _set_avl_conditional(name, "lý do hợp lệ")
            self.assertEqual(cm.exception.code, ErrorCode.BAD_STATE,
                             f"state {bad_state} phải BAD_STATE")
            # Không đổi state.
            self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), bad_state)

    # ── BE-TC5: user thiếu role → FORBIDDEN (fail-fast, KHÔNG PermissionError) ─────
    def test_low_role_rejected(self):
        from assetcore.api.imm03 import _set_avl_conditional
        name = self._mk_draft_avl()
        frappe.set_user(self._LOW_USER)
        try:
            with self.assertRaises(ServiceError) as cm:
                _set_avl_conditional(name, "lý do hợp lệ")
            self.assertEqual(cm.exception.code, ErrorCode.FORBIDDEN)
        finally:
            frappe.set_user("Administrator")
        # Guard fail-fast → state KHÔNG đổi.
        self.assertEqual(frappe.db.get_value(_DT_AVL, name, "workflow_state"), "Draft")

    # ── AC2: Spec Manager thực hiện được CẢ 2 nhánh ───────────────────────────────
    def test_spec_manager_can_do_both_branches(self):
        from assetcore.api.imm03 import _set_avl_conditional
        # Nhánh Draft
        d_name = self._mk_draft_avl()
        # Nhánh Approved
        a_name, _sup = self._mk_approved_avl()
        frappe.set_user(self._SPEC_USER)
        try:
            r1 = _set_avl_conditional(d_name, "Điều kiện: bổ sung ISO 13485 trong 90 ngày")
            r2 = _set_avl_conditional(a_name, "Hạ do phát hiện chậm giao 2 lô")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(r1["workflow_state"], "Conditional")
        self.assertEqual(r2["workflow_state"], "Conditional")
        self.assertEqual(frappe.db.get_value(_DT_AVL, d_name, "docstatus"), 1)
        self.assertEqual(frappe.db.get_value(_DT_AVL, a_name, "docstatus"), 1)

    # ── BE-TC6: downgrade Approved→Conditional → _sync supplier + 1 audit 'State Change' ─
    def test_downgrade_syncs_supplier_and_audits(self):
        from assetcore.api.imm03 import _set_avl_conditional
        name, sup = self._mk_approved_avl()
        if frappe.db.has_column("AC Supplier", "imm_avl_status"):
            self.assertEqual(
                frappe.db.get_value("AC Supplier", sup, "imm_avl_status"), "Approved")
        before = self._count_state_change_audit(name)
        _set_avl_conditional(name, "Hạ do audit ISO phát hiện điểm không phù hợp minor")
        # _sync gọi → AVL active DUY NHẤT giờ Conditional → supplier về Conditional.
        if frappe.db.has_column("AC Supplier", "imm_avl_status"):
            self.assertEqual(
                frappe.db.get_value("AC Supplier", sup, "imm_avl_status"), "Conditional")
        # ĐÚNG 1 dòng IMM Audit Trail 'State Change' mới.
        after = self._count_state_change_audit(name)
        self.assertEqual(after - before, 1)

    def test_audit_summary_localized(self):
        """change_summary = 'AVL — {action}: {from_vi} → Có điều kiện' (localize enum)."""
        from assetcore.api.imm03 import _set_avl_conditional
        name = self._mk_draft_avl()
        _set_avl_conditional(name, "Đạt điều kiện tối thiểu")
        summary = frappe.db.get_value(
            "IMM Audit Trail",
            {"ref_doctype": _DT_AVL, "ref_name": name, "event_type": "State Change"},
            "change_summary")
        self.assertEqual(summary, "AVL — Cấp Conditional: Nháp → Có điều kiện")

    # ── BE-TC7 (INVARIANT): mọi action phát ra ⊆ endpoint @whitelist implemented ───
    def test_avl_every_emitted_action_has_endpoint(self):
        """MỌI action-label trong codomain _AVL_VALID_TRANSITIONS map tới 1 endpoint
        @whitelist IMPLEMENTED (đóng câm, đo được). RED trước khi land
        set_avl_conditional ('Cấp Conditional' + 'Hạ xuống Conditional' unmapped)."""
        import assetcore.api.imm03 as api
        from assetcore.services.imm03 import _AVL_VALID_TRANSITIONS
        # Bảng action-label → tên endpoint @whitelist chịu trách nhiệm phát action đó.
        action_endpoint = {
            "Phê duyệt AVL":        "approve_avl",
            "Phục hồi Approved":    "approve_avl",
            "Cấp Conditional":      "set_avl_conditional",
            "Hạ xuống Conditional": "set_avl_conditional",
            "Đình chỉ":             "suspend_avl",
        }
        # codomain = tập action-label có trong SoT (mọi state).
        emitted = {action
                   for rows in _AVL_VALID_TRANSITIONS.values()
                   for action, _next, _roles in rows}
        # (1) mọi action phát ra PHẢI có trong bảng map (thêm action mới mà quên → đỏ).
        unmapped = emitted - set(action_endpoint)
        self.assertFalse(unmapped, f"Action chưa map tới endpoint: {unmapped}")
        # (2) mỗi endpoint map tới PHẢI là callable @whitelist IMPLEMENTED.
        for action in emitted:
            fn = getattr(api, action_endpoint[action], None)
            self.assertTrue(callable(fn),
                            f"Endpoint cho '{action}' chưa implement: "
                            f"{action_endpoint[action]}")
            self.assertIn(fn, frappe.whitelisted,
                          f"Endpoint '{action_endpoint[action]}' cho '{action}' "
                          f"chưa @frappe.whitelist")
