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
)
from assetcore.services.shared import ServiceError


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
