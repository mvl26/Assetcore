# Copyright (c) 2026, AssetCore Team
"""Regression tests: free-text `search` filter on Wave-2 list endpoints.

Bug: FE list views put `search` into the same filter dict as column filters
(see NeedsRequestListView.vue:71). Older BE implementations passed the dict
straight to `frappe.get_list`, producing:

    OperationalError: (1054, "Unknown column 'tabIMM Needs Request.search'
    in 'WHERE'")

The fix routes `search` through `services.shared.filters.pop_search()` which
extracts the key and rewrites it as `or_filters` LIKE clauses across declared
searchable fields.

Run: bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.integration.test_list_search_filter
"""
from __future__ import annotations

import json
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.imm01 import list_needs_requests, list_procurement_plans
from assetcore.api.imm02 import list_tech_specs
from assetcore.api.imm03 import list_avl, list_decisions, list_evaluations
from assetcore.services.shared.filters import (
    count_with_or,
    pop_search,
)


class TestPopSearch(unittest.TestCase):
    """Pure-function tests — no DB needed."""

    def test_no_search_key_returns_dict_unchanged(self):
        f, or_f = pop_search({"workflow_state": "Draft"}, ["name"])
        self.assertEqual(f, {"workflow_state": "Draft"})
        self.assertIsNone(or_f)

    def test_none_input(self):
        f, or_f = pop_search(None, ["name"])
        self.assertEqual(f, {})
        self.assertIsNone(or_f)

    def test_empty_search_string_treated_as_no_search(self):
        f, or_f = pop_search({"search": "   "}, ["name", "model"])
        self.assertEqual(f, {})
        self.assertIsNone(or_f)

    def test_search_extracted_and_translated_to_or_filters(self):
        f, or_f = pop_search(
            {"workflow_state": "Draft", "search": "NR-2026"},
            ["name", "device_model_ref"],
        )
        self.assertEqual(f, {"workflow_state": "Draft"})
        self.assertEqual(or_f, [
            ["name", "like", "%NR-2026%"],
            ["device_model_ref", "like", "%NR-2026%"],
        ])

    def test_search_value_stripped(self):
        _f, or_f = pop_search({"search": "  hello  "}, ["name"])
        self.assertEqual(or_f, [["name", "like", "%hello%"]])

    def test_does_not_mutate_input(self):
        src = {"search": "x", "workflow_state": "Draft"}
        pop_search(src, ["name"])
        self.assertIn("search", src)  # caller's dict untouched


class TestPopSearchLinkResolution(FrappeTestCase):
    """`pop_search(link_search=...)` resolves display name → link IDs.

    Pattern: FE placeholder says "tên model" but parent stores only the
    Link ID (`device_model_ref`). Helper queries the linked DocType for
    `model_name LIKE %term%`, then OR-IN's the matched IDs.
    """

    _TAG = "ZZZ-pop-search-link-test-tag"  # unique substring in model_name

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Skip if `setUpClass` already populated names from a prior run.
        cls.alpha_name = cls._ensure_model(f"Alpha {cls._TAG}")
        cls.beta_name = cls._ensure_model(f"Beta {cls._TAG}")

    @staticmethod
    def _ensure_model(model_name: str) -> str:
        existing = frappe.db.get_value("IMM Device Model",
                                       {"model_name": model_name}, "name")
        if existing:
            return existing
        doc = frappe.get_doc({
            "doctype": "IMM Device Model",
            "model_name": model_name,
            "manufacturer": "TestCo",
        })
        # IMM Device Model has a long mandatory chain (asset_category, etc.)
        # but this test only needs the row to exist + model_name to be set.
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_validate = True
        doc.insert(ignore_permissions=True)
        return doc.name

    @staticmethod
    def _in_clause(or_filters) -> list | None:
        for c in or_filters or []:
            if isinstance(c, list) and len(c) == 3 and c[1] == "in":
                return c
        return None

    def test_link_search_returns_matching_link_ids(self):
        """search='Alpha <TAG>' → IN clause contains only the Alpha model."""
        _f, or_filters = pop_search(
            {"search": f"Alpha {self._TAG}"},
            ["name"],
            link_search={"device_model_ref": ("IMM Device Model", "model_name")},
        )
        clause = self._in_clause(or_filters)
        self.assertIsNotNone(clause, f"no IN clause in {or_filters}")
        link_field, _op, ids = clause
        self.assertEqual(link_field, "device_model_ref")
        self.assertIn(self.alpha_name, ids)
        self.assertNotIn(self.beta_name, ids)

    def test_link_search_with_no_matches_omits_in_clause(self):
        """search='no-such-model' → falls back to direct fields only."""
        _f, or_filters = pop_search(
            {"search": "ZZZ-this-term-matches-no-model-anywhere-ZZZ"},
            ["name"],
            link_search={"device_model_ref": ("IMM Device Model", "model_name")},
        )
        self.assertIsNone(self._in_clause(or_filters),
                          "no model match → no IN clause")
        self.assertEqual(or_filters, [
            ["name", "like", "%ZZZ-this-term-matches-no-model-anywhere-ZZZ%"],
        ])

    def test_link_search_also_matches_link_id(self):
        """search=<alpha_name> → IN clause contains the matched ID itself."""
        _f, or_filters = pop_search(
            {"search": self.alpha_name},
            ["name"],
            link_search={"device_model_ref": ("IMM Device Model", "model_name")},
        )
        clause = self._in_clause(or_filters)
        self.assertIsNotNone(clause)
        self.assertIn(self.alpha_name, clause[2])


class TestSearchOnWave2Lists(FrappeTestCase):
    """End-to-end regression: previously each of these raised SQL 1054."""

    def _payload(self, term: str) -> str:
        return json.dumps({"search": term})

    def test_list_needs_requests_with_search_does_not_raise(self):
        res = list_needs_requests(filters=self._payload("NR-DOES-NOT-EXIST"))
        self.assertTrue(res.get("success"), f"unexpected envelope: {res}")
        self.assertIn("items", res["data"])
        self.assertIn("total", res["data"])

    def test_list_procurement_plans_with_search_does_not_raise(self):
        res = list_procurement_plans(filters=self._payload("PP-DOES-NOT-EXIST"))
        self.assertTrue(res.get("success"), f"unexpected envelope: {res}")

    def test_list_tech_specs_with_search_does_not_raise(self):
        res = list_tech_specs(filters=self._payload("TS-DOES-NOT-EXIST"))
        self.assertTrue(res.get("success"), f"unexpected envelope: {res}")

    def test_list_evaluations_with_search_does_not_raise(self):
        res = list_evaluations(filters=self._payload("VE-DOES-NOT-EXIST"))
        self.assertTrue(res.get("success"), f"unexpected envelope: {res}")

    def test_list_avl_with_search_does_not_raise(self):
        res = list_avl(filters=self._payload("AVL-DOES-NOT-EXIST"))
        self.assertTrue(res.get("success"), f"unexpected envelope: {res}")

    def test_list_decisions_with_search_does_not_raise(self):
        res = list_decisions(filters=self._payload("PD-DOES-NOT-EXIST"))
        self.assertTrue(res.get("success"), f"unexpected envelope: {res}")

    def test_count_with_or_matches_get_list_length(self):
        """Pagination invariant: total must match the OR-clause result set."""
        term = "%"  # matches everything via LIKE
        or_filters = [["name", "like", term]]
        rows = frappe.get_all("IMM Needs Request", or_filters=or_filters,
                              fields=["name"], limit_page_length=0)
        self.assertEqual(
            count_with_or("IMM Needs Request", None, or_filters),
            len(rows),
        )
