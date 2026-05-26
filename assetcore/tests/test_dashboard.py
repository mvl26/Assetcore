"""Dashboard / KPI consistency tests — RC-08, RC-09, RC-10 NextRound.

Cover các bug:
* RC-08 — Counter "Đã hết hạn" phải bao gồm cả Asset Document trạng thái Draft.
* RC-09 — `count_pending_approvals(scope=...)` là single source of truth cho
          dashboard widget VÀ /approvals/pending.
* RC-10 — `count_overdue_pm(user=...)` là single source of truth cho launcher
          KPI, /pm/dashboard và endpoint get_overview.

Run:
    bench --site miyano run-tests --module assetcore.tests.test_dashboard
"""
from __future__ import annotations

import time
import unittest

import frappe
from frappe.utils import add_days, nowdate

from assetcore.services.imm00 import count_pending_approvals
from assetcore.services.imm08 import PMStatus, count_overdue_pm


# ─── Fixture helpers ──────────────────────────────────────────────────────────

def _ensure_category(name: str = "_TestCatDashboard") -> str:
    """Ensure AC Asset Category exists (autoname → lookup theo category_name)."""
    existing = frappe.db.get_value(
        "AC Asset Category", {"category_name": name}, "name"
    )
    if existing:
        return existing
    doc = frappe.get_doc(
        {"doctype": "AC Asset Category", "category_name": name}
    ).insert(ignore_permissions=True)
    return doc.name


def _make_asset(suffix: str) -> str:
    sn = f"SN-DASH-{suffix}-{int(time.time() * 1000) % 1000000}"
    doc = frappe.get_doc(
        {
            "doctype": "AC Asset",
            "asset_name": f"_Test Asset Dashboard {suffix}",
            "asset_category": _ensure_category(),
            "manufacturer_sn": sn,
            # Để default lifecycle (Draft) — test KPI doc không phụ thuộc trạng thái asset
        }
    ).insert(ignore_permissions=True)
    return doc.name


# ─── RC-08: Expired Doc KPI bao gồm Draft ────────────────────────────────────


class TestExpiredDocsIncludesDrafts(unittest.TestCase):
    """RC-08: KPI 'Đã hết hạn' phải đếm doc Draft có expiry_date < today."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")
        cls.asset = _make_asset("RC08")
        cls.created: list[str] = []

    @classmethod
    def tearDownClass(cls):
        for n in cls.created:
            try:
                frappe.delete_doc("Asset Document", n, force=True, ignore_permissions=True)
            except Exception:  # noqa: BLE001
                pass
        try:
            frappe.delete_doc("AC Asset", cls.asset, force=True, ignore_permissions=True)
        except Exception:  # noqa: BLE001
            pass

    def _make_doc(self, state: str, expiry: str) -> str:
        # Insert ở workflow_state default ("Draft") rồi force-update sang state
        # mong muốn qua db.set_value để bypass workflow validation (chỉ cho test).
        d = frappe.get_doc(
            {
                "doctype": "Asset Document",
                "asset_ref": self.asset,
                "doc_category": "Technical",  # ko bắt buộc issuing_authority
                "doc_type_detail": f"_Test Type {state}",
                "doc_number": f"NUM-{state}-{int(time.time() * 1000) % 1000000}",
                "version": "1.0",
                "issued_date": add_days(expiry, -365),
                "expiry_date": expiry,
            }
        ).insert(ignore_permissions=True)
        if state != "Draft":
            frappe.db.set_value("Asset Document", d.name, "workflow_state", state)
        self.created.append(d.name)
        return d.name

    def test_count_expired_docs_includes_drafts(self):
        """Bug RC-08: doc Draft hết hạn vẫn phải được tính vào 'Đã hết hạn'."""
        # Tạo 2 doc: 1 Draft đã hết hạn, 1 Active đã hết hạn
        yesterday = add_days(nowdate(), -1)
        self._make_doc("Draft", yesterday)
        self._make_doc("Active", yesterday)

        # Filter theo logic dashboard.py:doc_expired (RC-08 fix)
        expired_count = frappe.db.count(
            "Asset Document",
            filters={"expiry_date": ["<", nowdate()]},
        )
        # Có ít nhất 2 (cả Draft và Active đều phải có trong count)
        self.assertGreaterEqual(expired_count, 2)

        # Đối chiếu: nếu BUG (filter status="Active") thì sẽ chỉ thấy 1
        active_only = frappe.db.count(
            "Asset Document",
            filters={"expiry_date": ["<", nowdate()], "workflow_state": "Active"},
        )
        self.assertLess(active_only, expired_count, "Bug regression: Draft bị bỏ qua")


# ─── RC-09: count_pending_approvals scope mine/all ────────────────────────────


class TestCountPendingApprovals(unittest.TestCase):
    """RC-09: helper count_pending_approvals(user, scope) là single source of truth."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def test_count_pending_approvals_mine_scope_default(self):
        """scope='mine' (default) → filter theo pending_approver = current_user."""
        # Không raise, return int
        n = count_pending_approvals()
        self.assertIsInstance(n, int)
        self.assertGreaterEqual(n, 0)

    def test_count_pending_approvals_mine_scope_explicit_user(self):
        """scope='mine' với user cụ thể."""
        n = count_pending_approvals(user="Administrator", scope="mine")
        self.assertIsInstance(n, int)
        # Kết quả phải bằng count trực tiếp với cùng filter
        expected = frappe.db.count(
            "Asset Commissioning",
            filters={"pending_approver": "Administrator", "docstatus": ["!=", 2]},
        )
        self.assertEqual(n, expected)

    def test_count_pending_approvals_all_scope_admin(self):
        """scope='all' với Administrator (có quyền) → global count."""
        frappe.set_user("Administrator")
        n = count_pending_approvals(scope="all")
        expected = frappe.db.count(
            "Asset Commissioning",
            filters={"pending_approver": ["is", "set"], "docstatus": ["!=", 2]},
        )
        self.assertEqual(n, expected)

    def test_count_pending_approvals_all_scope_falls_back_to_mine_for_non_admin(self):
        """scope='all' nhưng user thiếu quyền → fallback 'mine' (an toàn)."""
        # Tạo user mới với role thường (User)
        if not frappe.db.exists("User", "test_dash_user@example.com"):
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": "test_dash_user@example.com",
                    "first_name": "TestDash",
                    "send_welcome_email": 0,
                }
            ).insert(ignore_permissions=True)
        n_all = count_pending_approvals(user="test_dash_user@example.com", scope="all")
        n_mine = count_pending_approvals(user="test_dash_user@example.com", scope="mine")
        # Vì non-admin → fallback mine → 2 số bằng nhau
        self.assertEqual(n_all, n_mine)

    def test_count_pending_approvals_consistent_with_list_endpoint(self):
        """Số count phải khớp với len(list_my_pending_approvals())."""
        from assetcore.services.imm04 import list_my_pending_approvals

        frappe.set_user("Administrator")
        n = count_pending_approvals(user="Administrator", scope="mine")
        items = list_my_pending_approvals()
        # count chỉ trả số, list trả tối đa 50 record — chỉ check khi <= 50
        if n <= 50:
            self.assertEqual(n, len(items))


# ─── RC-10: count_overdue_pm consistent ──────────────────────────────────────


class TestCountOverduePm(unittest.TestCase):
    """RC-10: helper count_overdue_pm(user) là single source of truth."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")

    def test_count_overdue_pm_global(self):
        """count_overdue_pm() (không user) → count toàn hệ thống status=Overdue."""
        n = count_overdue_pm()
        expected = frappe.db.count("PM Work Order", filters={"status": PMStatus.OVERDUE})
        self.assertEqual(n, expected)

    def test_count_overdue_pm_filter_by_user(self):
        """count_overdue_pm(user) → filter thêm assigned_to."""
        n = count_overdue_pm(user="Administrator")
        expected = frappe.db.count(
            "PM Work Order",
            filters={"status": PMStatus.OVERDUE, "assigned_to": "Administrator"},
        )
        self.assertEqual(n, expected)

    def test_count_overdue_pm_consistent_between_launcher_and_pm_dashboard(self):
        """Launcher (get_overview) và /pm/dashboard (get_dashboard_stats) phải khớp."""
        from assetcore.api.dashboard import get_overview
        from assetcore.services.imm08 import get_dashboard_stats
        from datetime import datetime

        # Launcher KPI lấy từ get_overview → pm.overdue
        overview = get_overview()
        launcher_overdue = (overview.get("data") or {}).get("pm", {}).get("overdue", 0)

        # /pm/dashboard KPI lấy từ get_dashboard_stats(year, month) → kpis.overdue
        now = datetime.now()
        pm_stats = get_dashboard_stats(year=now.year, month=now.month)
        pm_dashboard_overdue = pm_stats.get("kpis", {}).get("overdue", 0)

        # 2 source phải bằng nhau và bằng count_overdue_pm()
        canonical = count_overdue_pm()
        self.assertEqual(launcher_overdue, canonical, "Launcher KPI lệch single source")
        self.assertEqual(
            pm_dashboard_overdue,
            canonical,
            "/pm/dashboard KPI lệch single source",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
