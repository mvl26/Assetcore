"""Unit tests for IMM-02 — Tech Spec & Market Analysis service layer."""
from __future__ import annotations
import unittest
from types import SimpleNamespace

from assetcore.services.imm02 import (
    _rollup_infra_status,
    _rollup_requirement_counts,
    _validate_gate_g01,
    _validate_gate_g04,
    _compute_candidate_score,
    _parse_weighting,
    validate_lock_in_assessment,
    MIN_MANDATORY_REQUIREMENTS,
    LOCK_IN_THRESHOLD_DEFAULT,
    INFRA_DOMAINS_REQUIRED,
)
from assetcore.services.shared import ErrorCode, ServiceError


def _make_req(parameter: str, is_mandatory: bool, test_method: str = "visual") -> SimpleNamespace:
    return SimpleNamespace(parameter=parameter, is_mandatory=is_mandatory,
                           test_method=test_method, idx=1, seq=None)


def _make_infra_item(domain: str, status: str) -> SimpleNamespace:
    return SimpleNamespace(domain=domain, compatibility_status=status)


def _make_lock_in_item(dimension: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(dimension=dimension, score=score, weight_pct=None, weighted=None)


def _make_ts_doc(**kwargs) -> SimpleNamespace:
    defaults = dict(
        name="_Test-TS-001",
        requirements=[],
        infra_compat=[],
        workflow_state="Draft",
        total_mandatory=0,
        total_optional=0,
        lock_in_score=None,
        lock_in_risk_ref=None,
        mitigation_plan=None,
        mitigation_evidence=None,
        benchmark_ref=None,
        candidate_count=None,
        threshold_used=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestRollupInfraStatus(unittest.TestCase):

    def test_empty_returns_blank(self):
        doc = _make_ts_doc()
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "")

    def test_all_compatible(self):
        doc = _make_ts_doc(infra_compat=[
            _make_infra_item("Electrical", "Compatible"),
            _make_infra_item("Network/IT", "N/A"),
        ])
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "All Compatible")

    def test_need_upgrade_gives_partial(self):
        doc = _make_ts_doc(infra_compat=[
            _make_infra_item("Electrical", "Compatible"),
            _make_infra_item("Network/IT", "Need Upgrade"),
        ])
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "Partial")

    def test_need_major_upgrade_wins(self):
        doc = _make_ts_doc(infra_compat=[
            _make_infra_item("Electrical", "Compatible"),
            _make_infra_item("Network/IT", "Need Major Upgrade"),
        ])
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "Need Major Upgrade")

    def test_no_statuses_returns_blank(self):
        doc = _make_ts_doc(infra_compat=[
            _make_infra_item("Electrical", ""),
        ])
        _rollup_infra_status(doc)
        self.assertEqual(doc.infra_status_overall, "")


class TestRollupRequirementCounts(unittest.TestCase):

    def test_counts_mandatory_optional(self):
        doc = _make_ts_doc(requirements=[
            _make_req("R1", True),
            _make_req("R2", True),
            _make_req("R3", False),
        ])
        _rollup_requirement_counts(doc)
        self.assertEqual(doc.total_mandatory, 2)
        self.assertEqual(doc.total_optional, 1)

    def test_sets_seq_on_each_row(self):
        reqs = [_make_req(f"R{i}", True) for i in range(3)]
        doc = _make_ts_doc(requirements=reqs)
        _rollup_requirement_counts(doc)
        for i, r in enumerate(reqs, 1):
            self.assertEqual(r.seq, i)


class TestGateG01(unittest.TestCase):

    def _make_mandatory_reqs(self, count: int, with_method: bool = True) -> list:
        return [_make_req(f"P{i}", True, "visual" if with_method else "") for i in range(count)]

    def test_below_minimum_raises(self):
        doc = _make_ts_doc(requirements=self._make_mandatory_reqs(MIN_MANDATORY_REQUIREMENTS - 1))
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g01(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)

    def test_exactly_minimum_passes(self):
        doc = _make_ts_doc(requirements=self._make_mandatory_reqs(MIN_MANDATORY_REQUIREMENTS))
        _validate_gate_g01(doc)  # must not raise

    def test_missing_test_method_raises(self):
        doc = _make_ts_doc(requirements=self._make_mandatory_reqs(MIN_MANDATORY_REQUIREMENTS, with_method=False))
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g01(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)


class TestGateG04(unittest.TestCase):

    def test_below_threshold_passes(self):
        doc = _make_ts_doc(lock_in_score=2.0)
        _validate_gate_g04(doc)  # must not raise

    def test_above_threshold_no_plan_raises(self):
        doc = _make_ts_doc(lock_in_score=LOCK_IN_THRESHOLD_DEFAULT + 0.1, mitigation_plan=None)
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g04(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)

    def test_above_threshold_with_plan_but_no_evidence_raises(self):
        doc = _make_ts_doc(
            lock_in_score=LOCK_IN_THRESHOLD_DEFAULT + 0.1,
            mitigation_plan="Switching to open protocol",
            mitigation_evidence=None,
        )
        with self.assertRaises(ServiceError) as cm:
            _validate_gate_g04(doc)
        self.assertEqual(cm.exception.code, ErrorCode.BUSINESS_RULE)

    def test_above_threshold_with_plan_and_evidence_passes(self):
        doc = _make_ts_doc(
            lock_in_score=LOCK_IN_THRESHOLD_DEFAULT + 0.1,
            mitigation_plan="Switching to open protocol",
            mitigation_evidence="evidence.pdf",
        )
        _validate_gate_g04(doc)  # must not raise


class TestComputeCandidateScore(unittest.TestCase):

    def test_returns_float_in_range(self):
        cand = SimpleNamespace(spec_match_pct=80, support_tier="Tier1")
        weights = {"spec": 40, "price": 30, "support": 20, "brand": 10}
        score = _compute_candidate_score(cand, weights)
        self.assertIsInstance(score, float)
        self.assertGreater(score, 0)
        self.assertLessEqual(score, 5.0)

    def test_higher_spec_match_gives_higher_score(self):
        weights = {"spec": 40, "price": 30, "support": 20, "brand": 10}
        low = _compute_candidate_score(SimpleNamespace(spec_match_pct=40, support_tier="Tier1"), weights)
        high = _compute_candidate_score(SimpleNamespace(spec_match_pct=90, support_tier="Tier1"), weights)
        self.assertGreater(high, low)

    def test_tier1_better_than_tier3(self):
        weights = {"spec": 40, "price": 30, "support": 20, "brand": 10}
        t1 = _compute_candidate_score(SimpleNamespace(spec_match_pct=80, support_tier="Tier1"), weights)
        t3 = _compute_candidate_score(SimpleNamespace(spec_match_pct=80, support_tier="Tier3"), weights)
        self.assertGreater(t1, t3)


class TestParseWeighting(unittest.TestCase):

    def test_none_returns_defaults(self):
        result = _parse_weighting(None)
        self.assertIn("spec", result)
        self.assertIn("price", result)

    def test_dict_passthrough(self):
        d = {"spec": 50, "price": 50}
        self.assertEqual(_parse_weighting(d), d)

    def test_json_string_parsed(self):
        result = _parse_weighting('{"spec": 60, "price": 40}')
        self.assertEqual(result["spec"], 60)

    def test_invalid_json_returns_defaults(self):
        result = _parse_weighting("not-json")
        self.assertIn("spec", result)


class TestValidateLockInAssessment(unittest.TestCase):

    def test_computes_weighted_score(self):
        items = [
            _make_lock_in_item("Protocol Standard", 3.0),
            _make_lock_in_item("Consumable Source", 2.0),
        ]
        doc = SimpleNamespace(items=items, lock_in_score=None,
                              threshold_used=None, spec_ref=None,
                              mitigation_plan=None, mitigation_evidence=None)
        validate_lock_in_assessment(doc)
        # Protocol Standard: 3.0 * 0.30 = 0.90; Consumable Source: 2.0 * 0.20 = 0.40 → 1.30
        self.assertAlmostEqual(doc.lock_in_score, 1.30, places=3)

    def test_sets_default_threshold(self):
        doc = SimpleNamespace(items=[], lock_in_score=None, threshold_used=None,
                              spec_ref=None, mitigation_plan=None, mitigation_evidence=None)
        validate_lock_in_assessment(doc)
        self.assertEqual(doc.threshold_used, LOCK_IN_THRESHOLD_DEFAULT)

    def test_unknown_dimension_ignored(self):
        items = [_make_lock_in_item("Unknown Dim", 5.0)]
        doc = SimpleNamespace(items=items, lock_in_score=None, threshold_used=None,
                              spec_ref=None, mitigation_plan=None, mitigation_evidence=None)
        validate_lock_in_assessment(doc)
        self.assertEqual(doc.lock_in_score, 0.0)
