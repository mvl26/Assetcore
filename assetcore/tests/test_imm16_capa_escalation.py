# Copyright (c) 2026, AssetCore Team
# IMM-16 ∩ IMM-00 — CAPA overdue escalation gate (RC-CAPA-ESC, BA Vòng 13).
#
# Core Doc: docs/imm-16/04_Backend_Design.md §VI.2 (INV-CAPA-ESC-1..4 + BVA).
# Bugs fixed (RED-proven below):
#   RC-ESC-1 TIER       — if/elif → Critical never reaches Level-2 (manager).
#   RC-ESC-2 FIELD-SoT  — _escalate_capa read raw imm_risk_level (default Medium)
#                         while real severity lives in `severity` → no escalate.
#   RC-ESC-3 IDEMPOTENCY — daily cron re-sends already-sent tiers (no record).
#   RC-ESC-4 N+1        — check_capa_due selects `severity` (unused) +
#                         _escalate_capa does its own db.get_value(imm_risk_level).
#
# Test data isolation: per-test rollback (tearDown) + module-level purge net.
from __future__ import annotations

import unittest
from contextlib import suppress
from unittest.mock import patch

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services import imm16 as svc

# Marker baked into every CAPA seeded here → reliable purge (autonamed PK).
_ESC_MARK = "ESC-TEST-CAPA-MARK"


def _purge_escalation_capas() -> None:
    frappe.set_user("Administrator")
    for nm in frappe.db.sql_list(
        "SELECT name FROM `tabIMM CAPA Record` WHERE description = %s", (_ESC_MARK,)
    ):
        with suppress(Exception):
            frappe.delete_doc("IMM CAPA Record", nm, force=True,
                              ignore_permissions=True, ignore_on_trash=True)
    frappe.db.commit()


def tearDownModule():  # noqa: N802
    _purge_escalation_capas()


class TestCapaEscalation(unittest.TestCase):
    """BR-16-02 / INV-CAPA-ESC-1..4 — _escalate_capa + check_capa_due."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[str] = []

    def tearDown(self):
        for nm in self._created:
            with suppress(Exception):
                frappe.delete_doc("IMM CAPA Record", nm, force=True,
                                  ignore_permissions=True, ignore_on_trash=True)
        frappe.db.rollback()
        # Belt-and-suspenders: service uses db.set_value (no commit) so rollback
        # clears escalation_level mutations; explicit delete covers committed rows.
        _purge_escalation_capas()

    # ── seed helper ──────────────────────────────────────────────────────────
    def _seed_capa(self, *, severity: str = "", imm_risk_level: str = "",
                   overdue_days: int = 0, status: str = "Open",
                   escalation_level: int = 0) -> str:
        """Insert a CAPA bypassing workflow/mandatory so we can pin any state.

        due_date = today - overdue_days (overdue_days>0 ⇒ past-due ⇒ overdue set).
        """
        due = add_days(nowdate(), -overdue_days)
        doc = frappe.get_doc({
            "doctype": "IMM CAPA Record",
            "description": _ESC_MARK,
            "severity": severity or None,
            "imm_risk_level": imm_risk_level or None,
            "status": status,
            "responsible": "compliance.user@test.local",
            "due_date": due,
            "opened_date": add_days(nowdate(), -(overdue_days + 5)),
            "escalation_level": escalation_level,
        })
        doc.flags.ignore_links = True
        doc.flags.ignore_mandatory = True
        doc.flags.ignore_validate = True
        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            doc.insert(ignore_permissions=True)
        finally:
            frappe.flags.in_install = prev
        # escalation_level may be reset by controller default → force the seed value.
        if escalation_level:
            frappe.db.set_value("IMM CAPA Record", doc.name, "escalation_level",
                                escalation_level, update_modified=False)
        if status not in ("Open",):
            frappe.db.set_value("IMM CAPA Record", doc.name, "status", status,
                                update_modified=False)
        self._created.append(doc.name)
        return doc.name

    def _run_due_capturing_levels(self):
        """Run check_capa_due, capturing every _send_capa_escalation(level=) call
        and _safe_sendmail invocations. Returns (levels:list[int], sendmail_count)."""
        levels: list[int] = []
        sendmail_calls: list = []

        real_send = svc._send_capa_escalation

        def _spy_send(capa, level):
            levels.append(level)
            # do NOT actually send mail in the spy path
            sendmail_calls.append((capa.get("name"), level))

        with patch.object(svc, "_send_capa_escalation", side_effect=_spy_send):
            svc.check_capa_due()
        return levels, sendmail_calls

    def _levels_for(self, name: str, levels: list, calls: list) -> list[int]:
        return [lvl for nm, lvl in calls if nm == name]

    # ── TC-CAPA-ESC-01 (BUG-1 TIER) ──────────────────────────────────────────
    def test_esc01_critical_3d_reaches_level2(self):
        """RC-ESC-1: Critical overdue=3d → _send_capa_escalation(level=2) ≥1.
        RED with if/elif: only level=1 ever fires for Critical."""
        name = self._seed_capa(imm_risk_level="Critical", severity="Critical",
                               overdue_days=3)
        levels, calls = self._run_due_capturing_levels()
        mine = self._levels_for(name, levels, calls)
        self.assertIn(2, mine, "Critical ≥3d phải kích hoạt Level-2 (lên manager)")
        self.assertIn(1, mine, "Critical ≥3d lần đầu cũng kích hoạt Level-1")

    # ── TC-CAPA-ESC-02 (BVA tier) ────────────────────────────────────────────
    def test_esc02_bva_tier_boundaries(self):
        n1 = self._seed_capa(imm_risk_level="Critical", overdue_days=1)
        n2 = self._seed_capa(imm_risk_level="Critical", overdue_days=2)
        n3 = self._seed_capa(imm_risk_level="Critical", overdue_days=3)
        levels, calls = self._run_due_capturing_levels()
        self.assertEqual(sorted(self._levels_for(n1, levels, calls)), [1],
                         "Critical =1d → chỉ Level-1")
        self.assertEqual(sorted(self._levels_for(n2, levels, calls)), [1],
                         "Critical =2d → vẫn chỉ Level-1 (chưa Level-2)")
        self.assertEqual(sorted(self._levels_for(n3, levels, calls)), [1, 2],
                         "Critical =3d → Level-1 + Level-2")

    # ── TC-CAPA-ESC-03 (BUG-2 FIELD-SoT) ─────────────────────────────────────
    def test_esc03_severity_sot_overrides_default_risk(self):
        """RC-ESC-2: severity='Critical' but imm_risk_level='Medium' → escalate.
        RED: old code reads imm_risk_level='Medium' → 0 escalate."""
        name = self._seed_capa(severity="Critical", imm_risk_level="Medium",
                               overdue_days=1)
        levels, calls = self._run_due_capturing_levels()
        mine = self._levels_for(name, levels, calls)
        self.assertIn(1, mine,
                      "severity=Critical (SoT) phải escalate Level-1 dù imm_risk_level=Medium")

    def test_esc03b_severity_critical_empty_risk_3d_level2(self):
        """severity=Critical, imm_risk_level EMPTY, 3d → Level-1+Level-2."""
        name = self._seed_capa(severity="Critical", imm_risk_level="",
                               overdue_days=3)
        levels, calls = self._run_due_capturing_levels()
        self.assertEqual(sorted(self._levels_for(name, levels, calls)), [1, 2])

    # ── TC-CAPA-ESC-04 (BUG-3 IDEMPOTENCY) ───────────────────────────────────
    def test_esc04_idempotent_second_run_no_resend(self):
        """RC-ESC-3: 2× check_capa_due same day on Critical 3d → run-2 sends 0.
        escalation_level == 2 after both runs."""
        name = self._seed_capa(imm_risk_level="Critical", severity="Critical",
                               overdue_days=3)

        sendmail_count = {"n": 0}

        def _count_sendmail(**kwargs):
            sendmail_count["n"] += 1

        with patch("assetcore.utils.helpers._safe_sendmail",
                   side_effect=_count_sendmail):
            svc.check_capa_due()
            after_run1 = sendmail_count["n"]
            lvl_after1 = frappe.db.get_value("IMM CAPA Record", name,
                                             "escalation_level")
            svc.check_capa_due()
            after_run2 = sendmail_count["n"]
            lvl_after2 = frappe.db.get_value("IMM CAPA Record", name,
                                             "escalation_level")

        self.assertGreaterEqual(after_run1, 1, "run-1 phải gửi ≥1 email")
        self.assertEqual(after_run2, after_run1,
                         "run-2 cùng ngày KHÔNG được gửi thêm email (idempotent)")
        self.assertEqual(int(lvl_after1 or 0), 2, "escalation_level=2 sau run-1")
        self.assertEqual(int(lvl_after2 or 0), 2, "escalation_level=2 sau run-2")

    # ── TC-CAPA-ESC-05 (EP non-escalate) ─────────────────────────────────────
    def test_esc05_non_escalate_partitions(self):
        med = self._seed_capa(imm_risk_level="Medium", overdue_days=10)
        low = self._seed_capa(imm_risk_level="Low", overdue_days=10)
        high2 = self._seed_capa(imm_risk_level="High", overdue_days=2)
        high3 = self._seed_capa(imm_risk_level="High", overdue_days=3)
        levels, calls = self._run_due_capturing_levels()
        self.assertEqual(self._levels_for(med, levels, calls), [],
                         "Medium → KHÔNG escalate")
        self.assertEqual(self._levels_for(low, levels, calls), [],
                         "Low → KHÔNG escalate")
        self.assertEqual(self._levels_for(high2, levels, calls), [],
                         "High =2d → no escalate")
        high3_lvls = self._levels_for(high3, levels, calls)
        # Spec §VI.2.4 BVA-HIGH: High ≥3d → Level-2 kích hoạt (manager reached).
        # Reference impl range(already+1, target+1) → target=2, already=0 ⇒ [1,2]:
        # cả thông báo responsible (L1) + manager (L2) đều gửi lần đầu. Bất biến
        # CỐT LÕI = Level-2 PHẢI có (chưa từng có ở =2d) → manager được leo thang.
        self.assertIn(2, high3_lvls,
                      "High =3d → phải kích hoạt Level-2 (lên manager)")
        self.assertEqual(sorted(high3_lvls), [1, 2],
                         "High ≥3d lần đầu: range(1,3) gửi cả L1+L2 (đúng reference impl)")

    # ── TC-CAPA-ESC-06 (BUG-4 N+1) ───────────────────────────────────────────
    def test_esc06_no_db_get_value_imm_risk_level_in_loop(self):
        """RC-ESC-4: _escalate_capa reads severity/imm_risk_level/escalation_level
        from the selected row — 0 db.get_value('imm_risk_level') per CAPA."""
        self._seed_capa(imm_risk_level="Critical", severity="Critical",
                        overdue_days=3)

        bad_calls: list = []
        real_get_value = frappe.db.get_value

        def _spy_get_value(doctype, *args, **kwargs):
            # signature: get_value(doctype, filters, fieldname, ...)
            field = args[1] if len(args) > 1 else kwargs.get("fieldname")
            if doctype == "IMM CAPA Record" and (
                field == "imm_risk_level"
                or (isinstance(field, (list, tuple)) and "imm_risk_level" in field)
            ):
                bad_calls.append((doctype, field))
            return real_get_value(doctype, *args, **kwargs)

        with patch.object(frappe.db, "get_value", side_effect=_spy_get_value):
            with patch.object(svc, "_send_capa_escalation"):
                svc.check_capa_due()

        self.assertEqual(bad_calls, [],
                         "KHÔNG được db.get_value('imm_risk_level') trong vòng escalate (N+1)")

    def test_esc06b_severity_not_in_dead_select(self):
        """AST guard: check_capa_due select must include the SoT fields
        (imm_risk_level + escalation_level) — not just dead `severity`."""
        import inspect
        src = inspect.getsource(svc.check_capa_due)
        self.assertIn("imm_risk_level", src,
                      "check_capa_due phải select imm_risk_level (SoT)")
        self.assertIn("escalation_level", src,
                      "check_capa_due phải select escalation_level (idempotency)")

    # ── TC-CAPA-ESC-07 (AUDIT) ───────────────────────────────────────────────
    def test_esc07_audit_record_emitted(self):
        """≥1 IMM Audit Trail event_type='CAPA' per escalation tier."""
        name = self._seed_capa(imm_risk_level="Critical", severity="Critical",
                               overdue_days=3)
        before = frappe.db.count("IMM Audit Trail",
                                 {"ref_doctype": "IMM CAPA Record", "ref_name": name,
                                  "event_type": "CAPA"})
        with patch("assetcore.utils.helpers._safe_sendmail"):
            svc.check_capa_due()
        after = frappe.db.count("IMM Audit Trail",
                                {"ref_doctype": "IMM CAPA Record", "ref_name": name,
                                 "event_type": "CAPA"})
        self.assertGreaterEqual(after - before, 1,
                                "escalate Critical 3d phải sinh ≥1 audit CAPA event")

    def test_esc07b_audit_failure_does_not_break_cron(self):
        """audit-fail (log_audit_event raise) KHÔNG vỡ check_capa_due."""
        name = self._seed_capa(imm_risk_level="Critical", severity="Critical",
                               overdue_days=3)
        sent = {"n": 0}

        def _boom(*a, **k):
            raise RuntimeError("audit chain down")

        def _count(**k):
            sent["n"] += 1

        # imm16 binds log_audit_event into its own namespace → patch svc.<name>.
        with patch.object(svc, "log_audit_event", side_effect=_boom):
            with patch("assetcore.utils.helpers._safe_sendmail", side_effect=_count):
                # must NOT raise
                svc.check_capa_due()
        self.assertGreaterEqual(sent["n"], 1,
                                "email vẫn gửi dù audit fail (best-effort audit)")
        self.assertEqual(int(frappe.db.get_value("IMM CAPA Record", name,
                                                 "escalation_level") or 0), 2,
                         "escalation_level vẫn được cập nhật dù audit fail")

    # ── TC-CAPA-ESC-08 (REGRESSION terminal) ─────────────────────────────────
    def test_esc08_closed_capa_not_escalated(self):
        """Closed CAPA (terminal) due=today-10 NOT in _overdue_capa_filter → 0 escalate."""
        name = self._seed_capa(imm_risk_level="Critical", severity="Critical",
                               overdue_days=10, status="Closed")
        levels, calls = self._run_due_capturing_levels()
        self.assertEqual(self._levels_for(name, levels, calls), [],
                         "CAPA Closed (terminal) KHÔNG được escalate (SoT overdue bất biến)")


if __name__ == "__main__":
    unittest.main()
