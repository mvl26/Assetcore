"""Unit tests for IMM-03 — Vendor Eval & Procurement Decision service layer."""
from __future__ import annotations
import unittest
from types import SimpleNamespace

from assetcore.services.imm03 import (
    _parse_weighting,
    _parse_json_field,
    _compute_eval_scores,
    _validate_gate_g04_method,
    ENVELOPE_HARD_LIMIT_PCT,
    _METHOD_RULES,
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
        return SimpleNamespace(candidates=candidates, criteria=criteria,
                               weighting_scheme=weighting, recommended_candidate=None)

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
