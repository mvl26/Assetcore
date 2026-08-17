# Copyright (c) 2026, AssetCore Team
"""Regression: IMM Audit Trail list endpoint — event_type filter + count parity.

Bug (2026-06-02, /audit-trail page): ``AuditTrailListView.vue`` sends
``event_type=CAPA`` but ``assetcore.api.imm00.list_audit_trail`` had no
``event_type`` parameter. Frappe's ``frappe.call`` strips unknown kwargs
(``get_newargs``), so the filter was silently ignored — "search by event"
returned every event type instead of just CAPA.

Secondary bug: when both ``asset`` and ``q`` were supplied the total count used
``or_filters`` only (ignoring the asset AND-filter), so pagination over-counted
(FE ``total`` larger than the rows actually returned).

Run: bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.imm00.test_imm00_audit_trail
"""
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.imm00 import list_audit_trail
from assetcore.services.imm00 import log_audit_event
from assetcore.tests.imm00.test_imm00 import (
    _insert_asset_bypass_workflow,
    _purge_asset,
    _purge_category,
)

_CAT = "Thiết bị Audit-Filter Test"
_ASSET_A = "Máy thử nghiệm lọc audit A — KTYS"
_ASSET_B = "Máy thử nghiệm lọc audit B — KTYS"


def _mk_asset(name: str, category: str, sn: str):
    return _insert_asset_bypass_workflow({
        "doctype": "AC Asset",
        "asset_name": name,
        "asset_category": category,
        "manufacturer_sn": sn,
        "medical_device_class": "Class II",
        "risk_classification": "Medium",
        "purchase_date": "2023-01-10",
        "lifecycle_status": "Active",
    })


class TestListAuditTrailFilters(FrappeTestCase):
    """`list_audit_trail` must honour the event_type filter and keep
    pagination total in parity with the returned rows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for nm in (_ASSET_A, _ASSET_B):
            for a in frappe.get_all("AC Asset", filters={"asset_name": nm}, pluck="name"):
                _purge_asset(a)
        _purge_category(_CAT)
        frappe.db.commit()

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": _CAT,
        }).insert(ignore_permissions=True)
        cls.asset = _mk_asset(_ASSET_A, cls.cat.name, "AUDIT-FILTER-A001")
        cls.asset_b = _mk_asset(_ASSET_B, cls.cat.name, "AUDIT-FILTER-B001")

        # Asset A: 3 entries of distinct event types.
        cls.e_capa = log_audit_event(
            asset=cls.asset.name, event_type="CAPA", actor="Administrator",
            change_summary="alpha capa effectiveness review",
        )
        cls.e_maint = log_audit_event(
            asset=cls.asset.name, event_type="Maintenance", actor="Administrator",
            change_summary="beta preventive maintenance done",
        )
        cls.e_state = log_audit_event(
            asset=cls.asset.name, event_type="State Change", actor="Administrator",
            from_status="Commissioned", to_status="Active",
            change_summary="gamma commissioned to active",
        )
        # Asset B: a foreign "alpha" entry — proves the count must respect the
        # asset AND-filter, not just the OR free-text clause.
        cls.e_foreign = log_audit_event(
            asset=cls.asset_b.name, event_type="CAPA", actor="Administrator",
            change_summary="alpha foreign asset entry",
        )
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        _purge_asset(cls.asset.name)
        _purge_asset(cls.asset_b.name)
        _purge_category(_CAT)
        frappe.db.commit()
        super().tearDownClass()

    def _query(self, **kw):
        res = list_audit_trail(asset=self.asset.name, **kw)
        self.assertTrue(res.get("success"), res)
        return res["data"]["items"], res["data"]["pagination"]

    # ── event_type filter ─────────────────────────────────────────────────────
    def test_filter_by_event_type_capa_returns_only_capa(self):
        items, pag = self._query(event_type="CAPA")
        self.assertEqual(len(items), 1, f"event_type=CAPA must return only CAPA rows: {items}")
        self.assertEqual(items[0]["event_type"], "CAPA")
        self.assertEqual(pag["total"], 1)

    def test_filter_by_event_type_maintenance(self):
        items, _ = self._query(event_type="Maintenance")
        self.assertEqual({i["event_type"] for i in items}, {"Maintenance"})

    def test_filter_by_event_type_no_match_returns_empty(self):
        items, pag = self._query(event_type="Calibration")
        self.assertEqual(items, [])
        self.assertEqual(pag["total"], 0)

    def test_no_event_type_returns_all_seeded(self):
        items, pag = self._query()
        self.assertGreaterEqual(pag["total"], 3)
        self.assertGreaterEqual(len(items), 3)

    # ── count / list parity ───────────────────────────────────────────────────
    def test_count_parity_with_asset_and_q(self):
        # q="alpha" lives in both asset A's CAPA row and asset B's foreign row,
        # but scoped to asset A only 1 row must be returned AND counted.
        items, pag = self._query(q="alpha")
        self.assertEqual(len(items), 1, items)
        self.assertEqual(
            pag["total"], len(items),
            "pagination total must match filtered item count (count/list parity)",
        )

    def test_event_type_and_q_combine_as_and(self):
        items, pag = self._query(event_type="Maintenance", q="alpha")
        self.assertEqual(items, [])
        self.assertEqual(pag["total"], 0)
