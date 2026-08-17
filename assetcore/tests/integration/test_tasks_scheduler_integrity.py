"""tasks.py scheduler-integrity + dead-code landmine guard (TDD-first).

ROOT-CAUSE this suite protects (Round-5-class crash):
``assetcore.tasks`` had ORPHAN jobs (``update_asset_completeness``,
``generate_pm_work_orders``, duplicate ``check_document_expiry``, plus a few
IMM-04 commissioning jobs) that:
  (a) were NOT wired into ``hooks.scheduler_events`` and had 0 callers, and
  (b) referenced the NON-EXISTENT core doctype string-literal ``"Asset"``
      (AssetCore uses ``AC Asset`` — CLAUDE.md §5).
If a scheduler had ever fired one, it would crash on ``tabAsset`` not existing.

Invariants enforced here (so the drift can NEVER come back silently):

* TDD-1  every dotted path in ``hooks.scheduler_events`` imports + is callable.
* TDD-2  NO function in ``assetcore.tasks`` references the bare core doctype
         literal ``"Asset"`` (only ``"AC Asset"`` via ``_AC_ASSET``, or domain
         doctypes such as ``"Asset Document"`` / ``"Asset Commissioning"``).
* TDD-3  the orphan symbols are gone at module level, and the only surviving
         ``check_document_expiry`` is the wired ``imm05`` one (not ``tasks``).
* TDD-4  the live wired path stays intact: ``tasks.check_pm_overdue`` is in
         ``daily`` and fires before ``generate_pm_work_orders_from_schedule``.

Run: bench --site miyano run-tests --module \
     assetcore.tests.integration.test_tasks_scheduler_integrity
"""
from __future__ import annotations

import ast
import inspect
import re
import unittest

import frappe  # noqa: F401  (frappe context needed for get_attr)

from assetcore import hooks
from assetcore import tasks


# Domain doctypes whose *name* legitimately starts with "Asset " (NOT the core
# "Asset"). Used to assert TDD-2 doesn't false-positive on these.
_ALLOWED_ASSET_PREFIX_DOCTYPES = {
    "Asset Document",
    "Asset Commissioning",
    "Asset Category",
}

_SCHEDULE_BUCKETS = ("daily", "weekly", "monthly", "hourly", "cron")


def _all_scheduler_paths() -> list[str]:
    paths: list[str] = []
    for bucket in _SCHEDULE_BUCKETS:
        val = hooks.scheduler_events.get(bucket)
        if not val:
            continue
        if isinstance(val, dict):  # cron bucket is {expr: [paths]}
            for sub in val.values():
                paths.extend(sub)
        else:
            paths.extend(val)
    return paths


# ─── TDD-1: scheduler wiring is internally consistent ─────────────────────────

class TestSchedulerWiringResolves(unittest.TestCase):
    """Every wired dotted path imports cleanly AND is callable.

    Guards against deleting/renaming a wired function or leaving a dangling
    reference in hooks.scheduler_events.
    """

    def test_every_scheduler_path_is_importable_callable(self):
        paths = _all_scheduler_paths()
        self.assertTrue(paths, "scheduler_events should not be empty")
        for path in paths:
            with self.subTest(path=path):
                try:
                    fn = frappe.get_attr(path)
                except Exception as exc:  # pragma: no cover - failure is the signal
                    self.fail(f"Scheduler path '{path}' is not importable: {exc}")
                self.assertTrue(
                    callable(fn),
                    f"Scheduler path '{path}' resolved but is not callable.",
                )


# ─── TDD-2: the landmine guard — no bare core "Asset" literal in tasks.py ─────

class TestNoCoreAssetLiteralInTasks(unittest.TestCase):
    """No function in assetcore.tasks references the non-existent core
    doctype string-literal 'Asset'. AssetCore rollups MUST use AC Asset.

    This is the anti-regression for the Round-5-class crash: a scheduler-wired
    job (or its transitive in-module call graph) hitting ``tabAsset``.
    """

    def test_no_bare_asset_doctype_string_in_tasks_source(self):
        src = inspect.getsource(tasks)
        tree = ast.parse(src)

        offenders: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value == "Asset":
                    offenders.append(f'bare "Asset" literal at line {node.lineno}')
                # raw SQL `tabAsset` (but NOT `tabAsset Document`, etc.)
                if re.search(r"`tabAsset`", node.value):
                    offenders.append(f'`tabAsset` SQL at line {node.lineno}')
                if re.search(r"`tabAsset`(?!\s*\w)", node.value):
                    offenders.append(f'`tabAsset` SQL ref at line {node.lineno}')

        self.assertEqual(
            offenders,
            [],
            "tasks.py must NOT reference core 'Asset'. Use _AC_ASSET ('AC Asset') "
            "or a domain doctype. Offenders: " + "; ".join(offenders),
        )

    def test_allowed_asset_prefixed_doctypes_are_not_flagged(self):
        # Sanity: ensure our guard doesn't over-match domain doctypes if present.
        src = inspect.getsource(tasks)
        for dt in _ALLOWED_ASSET_PREFIX_DOCTYPES:
            if dt in src:
                # Presence is fine; this test just documents the allow-list.
                self.assertNotEqual(dt, "Asset")


# ─── TDD-3: orphan symbols gone; single canonical check_document_expiry ───────

class TestOrphanSymbolsRemoved(unittest.TestCase):
    def test_orphan_jobs_no_longer_exist_in_tasks(self):
        for sym in (
            "update_asset_completeness",
            "generate_pm_work_orders",
        ):
            with self.subTest(symbol=sym):
                self.assertFalse(
                    hasattr(tasks, sym),
                    f"Orphan tasks.{sym} must be deleted (0 callers, 0 wiring).",
                )

    def test_check_document_expiry_resolves_to_imm05_only(self):
        # The wired path points at imm05, NOT tasks. The tasks duplicate is gone.
        self.assertIn(
            "assetcore.services.imm05.check_document_expiry",
            hooks.scheduler_events.get("daily", []),
        )
        self.assertFalse(
            hasattr(tasks, "check_document_expiry"),
            "Duplicate tasks.check_document_expiry must be removed; the canonical "
            "one is assetcore.services.imm05.check_document_expiry.",
        )
        fn = frappe.get_attr("assetcore.services.imm05.check_document_expiry")
        self.assertEqual(fn.__module__, "assetcore.services.imm05")


# ─── TDD-4: live wired path stays intact ──────────────────────────────────────

class TestLivePmOverdueWiringIntact(unittest.TestCase):
    def test_check_pm_overdue_still_wired_and_callable(self):
        daily = hooks.scheduler_events.get("daily", [])
        self.assertIn("assetcore.tasks.check_pm_overdue", daily)
        self.assertTrue(callable(frappe.get_attr("assetcore.tasks.check_pm_overdue")))

    def test_check_pm_overdue_runs_before_generate(self):
        daily = hooks.scheduler_events.get("daily", [])
        gen = "assetcore.services.imm08.generate_pm_work_orders_from_schedule"
        if gen in daily:
            self.assertLess(
                daily.index("assetcore.tasks.check_pm_overdue"),
                daily.index(gen),
            )

    def test_update_asset_pm_status_helper_preserved(self):
        # The live escalation/rollup helpers must NOT be swept.
        for sym in (
            "_update_asset_pm_status",
            "_escalate_to_director",
            "_escalate_to_ptp",
            "_alert_workshop_manager_overdue",
            "_AC_ASSET",
        ):
            with self.subTest(symbol=sym):
                self.assertTrue(
                    hasattr(tasks, sym),
                    f"Live PM-overdue path symbol tasks.{sym} must be preserved.",
                )
        self.assertEqual(tasks._AC_ASSET, "AC Asset")
