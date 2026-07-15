# Copyright (c) 2026, AssetCore Team
# IMM-15 Cycle Count — Detail endpoint + lifecycle test suite (TDD).
#
# Covers the BE contract consumed by frontend/src/views/inventory:
#   - svc.get_cycle_count(name)          → header + items + allowed_transitions
#   - api.get_cycle_count(name)          → 404 envelope on not-found (NOT 500)
#   - create → submit → post lifecycle   → variance + adjustment_ref + capa
#
# Reuses the shared fixtures (warehouse / spare part / seeded stock=20) from
# TestImm15Base so we do not duplicate master-data seeding.
from __future__ import annotations

from contextlib import suppress

import frappe

from assetcore.api import imm15 as api15
from assetcore.services import imm15 as svc
from assetcore.services.shared import ErrorCode, ServiceError
from assetcore.tests.test_imm15 import TestImm15Base

_VERIFIER = "cyclecount-verifier@assetcore.test"


class TestCycleCountDetailAndLifecycle(TestImm15Base):
    """TC-15-CYC: get_cycle_count + Planned→Counting→Reviewed→Posted lifecycle."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        # Second real user for VR-15-11 segregation (verifier != counted_by).
        if not frappe.db.exists("User", _VERIFIER):
            with suppress(Exception):
                u = frappe.get_doc({
                    "doctype": "User",
                    "email": _VERIFIER,
                    "first_name": "Cycle",
                    "last_name": "Verifier",
                    "enabled": 1,
                    "send_welcome_email": 0,
                })
                u.flags.ignore_permissions = True
                u.insert(ignore_permissions=True)
        frappe.db.commit()

    def setUp(self):
        frappe.set_user("Administrator")
        # Deterministic per-test state: posting an adjustment mutates the shared
        # stock fixture (service commits, no rollback) → reset to the seed snapshot
        # so system_qty / variance are reproducible regardless of test order.
        frappe.db.set_value(
            "AC Spare Part Stock",
            {"spare_part": self.part, "warehouse": self.warehouse},
            {"qty_on_hand": 20, "available_qty": 20, "reserved_qty": 0},
        )
        self._purge_open_capa_for_part()

    def _purge_open_capa_for_part(self):
        """Cleanup: drop CAPAs seeded by this suite (source_type marker).

        Keeps the CAPA table from accumulating across runs; the per-line capa_ref
        assertion is deterministic regardless, so this is hygiene only.
        """
        with suppress(Exception):
            for capa in frappe.get_all(
                "IMM CAPA Record",
                filters={"source_type": "Cycle Count Variance"},
                fields=["name", "docstatus"],
            ):
                with suppress(Exception):
                    if capa.docstatus == 1:
                        cd = frappe.get_doc("IMM CAPA Record", capa.name)
                        cd.cancel()
                    frappe.delete_doc("IMM CAPA Record", capa.name, force=True,
                                      ignore_permissions=True)
        frappe.db.commit()

    # ── get_cycle_count: header + items + allowed_transitions ────────────────

    def test_get_cycle_count_returns_items_and_allowed_transitions(self):
        res = svc.create_cycle_count(
            warehouse=self.warehouse,
            items=[{"spare_part": self.part}],
            count_type="Cycle",
        )
        name = res["name"]

        data = svc.get_cycle_count(name)

        # Header contract
        self.assertEqual(data["name"], name)
        self.assertEqual(data["warehouse"], self.warehouse)
        self.assertEqual(data["status"], "Planned")
        self.assertIn("warehouse_name", data)
        self.assertIn("verified_by_name", data)
        self.assertIn("adjustment_ref", data)
        # Items carry the system_qty snapshot (=20 seeded) + resolved part_name
        self.assertTrue(data["items"], "items must not be empty")
        line = data["items"][0]
        self.assertEqual(line["spare_part"], self.part)
        self.assertEqual(float(line["system_qty"]), 20.0)
        self.assertIn("part_name", line)
        self.assertNotEqual(line["part_name"], "")
        # allowed_transitions: Planned + inventory.write cap → ['Submit']
        self.assertIn("Submit", data["allowed_transitions"])
        self.assertNotIn("Post", data["allowed_transitions"])

    def test_get_cycle_count_allowed_transitions_track_status(self):
        res = svc.create_cycle_count(
            warehouse=self.warehouse,
            items=[{"spare_part": self.part}],
            count_type="Cycle",
        )
        name = res["name"]
        # Reviewed (Administrator, cap inventory.submit) → ['Recount', 'Post']
        # (CR-WF-15-CC: Recount CTA surfaced Reviewed→Counting; Recount đặt TRƯỚC Post —
        # xem test_imm15.TestCycleCountAllowedTransitions.test_recount_surfaced_for_reviewed).
        svc.submit_cycle_count(name, [{"spare_part": self.part, "counted_qty": 20}])
        data = svc.get_cycle_count(name)
        self.assertEqual(data["status"], "Reviewed")
        self.assertEqual(data["allowed_transitions"], ["Recount", "Post"])
        # Posted → no action tokens
        svc.post_cycle_count(name, verified_by=_VERIFIER)
        data = svc.get_cycle_count(name)
        self.assertEqual(data["status"], "Posted")
        self.assertEqual(data["allowed_transitions"], [])

    # ── not-found → 404 envelope (NOT 500) ───────────────────────────────────

    def test_get_cycle_count_not_found_404(self):
        # Service raises typed NOT_FOUND
        with self.assertRaises(ServiceError) as ctx:
            svc.get_cycle_count("CYC-9999-NON-EXISTENT")
        self.assertEqual(ctx.exception.code, ErrorCode.NOT_FOUND)
        # API layer maps it to a 404 envelope — never a 500 / raw traceback
        env = api15.get_cycle_count("CYC-9999-NON-EXISTENT")
        self.assertFalse(env["success"])
        self.assertEqual(env["code"], "NOT_FOUND")
        self.assertEqual(env["http_status"], 404)
        self.assertNotIn("traceback", env)

    # ── full lifecycle: create → submit → post ───────────────────────────────

    def test_cycle_count_lifecycle_planned_to_posted(self):
        # create → Planned, system_qty snapshot = 20
        created = svc.create_cycle_count(
            warehouse=self.warehouse,
            items=[{"spare_part": self.part}],
            count_type="Cycle",
        )
        name = created["name"]
        self.assertEqual(created["workflow_state"], "Planned")

        # submit with a real variance (+10 found extra) → Reviewed
        submitted = svc.submit_cycle_count(
            name,
            [{"spare_part": self.part, "counted_qty": 30,
              "root_cause": "Found_Extra"}],
        )
        self.assertEqual(submitted["workflow_state"], "Reviewed")
        self.assertEqual(submitted["variance_count"], 1)

        doc = frappe.get_doc("IMM Stock Cycle Count", name)
        self.assertEqual(float(doc.items[0].variance_qty), 10.0)
        self.assertEqual(doc.items[0].root_cause, "Found_Extra")
        self.assertTrue(doc.items[0].capa_required)

        # post (verifier != counted_by) → Posted + adjustment_ref + capa
        posted = svc.post_cycle_count(name, verified_by=_VERIFIER)
        self.assertEqual(posted["workflow_state"], "Posted")
        self.assertTrue(posted["adjustment_ref"],
                        "post must set adjustment_ref (stock movement)")
        self.assertEqual(posted["capa_created"], 1)

        # adjustment record exists + is an actual submitted stock movement
        self.assertTrue(frappe.db.exists("AC Stock Movement",
                                         posted["adjustment_ref"]))
        # get_cycle_count exposes adjustment_ref alias for the FE banner
        detail = svc.get_cycle_count(name)
        self.assertEqual(detail["adjustment_ref"], posted["adjustment_ref"])
        self.assertEqual(detail["capa_created"], 1)
        # CAPA seeded with the correct schema (source_type option) + linked back
        # on the varianced child row for §5 traceability.
        capa_ref = frappe.db.get_value("IMM Cycle Count Item",
                                       doc.items[0].name, "capa_ref")
        self.assertTrue(capa_ref, "varianced line must link its seeded CAPA")
        self.assertEqual(
            frappe.db.get_value("IMM CAPA Record", capa_ref, "source_type"),
            "Cycle Count Variance")

    def test_submit_no_variance_posts_clean(self):
        created = svc.create_cycle_count(
            warehouse=self.warehouse,
            items=[{"spare_part": self.part}],
            count_type="Spot",
        )
        name = created["name"]
        # counted == system → zero variance
        submitted = svc.submit_cycle_count(
            name, [{"spare_part": self.part, "counted_qty": 20}])
        self.assertEqual(submitted["variance_count"], 0)
        posted = svc.post_cycle_count(name, verified_by=_VERIFIER)
        self.assertEqual(posted["workflow_state"], "Posted")
        self.assertEqual(posted["capa_created"], 0)

    def test_submit_is_idempotent_bad_state_after_reviewed(self):
        created = svc.create_cycle_count(
            warehouse=self.warehouse,
            items=[{"spare_part": self.part}],
            count_type="Cycle",
        )
        name = created["name"]
        svc.submit_cycle_count(name, [{"spare_part": self.part, "counted_qty": 20}])
        # Re-submitting a Reviewed count must be rejected (BAD_STATE), not silently redo
        with self.assertRaises(ServiceError) as ctx:
            svc.submit_cycle_count(name, [{"spare_part": self.part, "counted_qty": 5}])
        self.assertEqual(ctx.exception.code, ErrorCode.BAD_STATE)

    @classmethod
    def tearDownClass(cls):
        # Drop cycle counts + adjustment movements + CAPA created by this suite,
        # then delegate shared-fixture teardown to the base class.
        frappe.set_user("Administrator")
        with suppress(Exception):
            for capa in frappe.get_all(
                "IMM CAPA Record",
                filters={"source_type": "Cycle Count Variance"},
                fields=["name", "docstatus"],
            ):
                with suppress(Exception):
                    if capa.docstatus == 1:
                        frappe.get_doc("IMM CAPA Record", capa.name).cancel()
                    frappe.delete_doc("IMM CAPA Record", capa.name, force=True,
                                      ignore_permissions=True)
        with suppress(Exception):
            if frappe.db.exists("User", _VERIFIER):
                frappe.delete_doc("User", _VERIFIER, force=True,
                                  ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()
