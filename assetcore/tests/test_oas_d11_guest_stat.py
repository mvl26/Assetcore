"""TC-OAS-D11-01..05 — STATS-GUEST-SSOT: guest_count DẪN XUẤT từ rendered paths.

Bám Acceptance Phase A D11. Test viết TRƯỚC fix (TDD RED→GREEN).

Root cause: `x-assetcore-stats.guest_count` cũ = `len(_guest_name_set())` (đọc
`frappe.guest_methods` — GLOBAL registry volatile, gồm guest-method của MỌI app +
re-import → trả 2/5/10 tuỳ worker-boot context). Drift 10-vs-5 vs bề mặt guest THẬT
mà spec phơi ra (5 operation có security==[]).

Fix: guest_count đếm ĐỘNG từ chính `paths` dict — số operation có `security == []`
(cùng nguồn total_endpoints/get_count/post_count/enriched_count). KHÔNG gọi
`frappe.guest_methods` trong `_assetcore_stats`. `_guest_name_set()` GIỮ là SSoT cho
quyết định is_guest PER-OP trong `_build_operation` (không đổi) — chỉ STAT đổi nguồn.

Bề mặt guest THẬT (5): auth.register_user / auth.check_account_status /
auth.account_state + layout.get_user_context / layout.ping_session.

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_d11_guest_stat
"""
from __future__ import annotations

import unittest

import frappe  # noqa: F401 — môi trường Frappe

from assetcore.api import openapi
from assetcore.api import openapi_overrides as _ovr


# Bề mặt guest documented (5 op-tail) — tập kỳ vọng TUYỆT ĐỐI (không nhiều/ít hơn).
_EXPECTED_GUEST_TAILS = {
    "auth.register_user",
    "auth.check_account_status",
    "auth.account_state",
    "layout.get_user_context",
    "layout.ping_session",
}

_PREFIX = "/api/method/assetcore.api."


def _rendered_guest_ops(spec: dict) -> list[dict]:
    """Mọi operation trong spec['paths'] có security == [] (bề mặt guest THẬT spec phơi)."""
    return [
        op
        for item in spec["paths"].values()
        for op in item.values()
        if op.get("security") == []
    ]


def _guest_path_tails(spec: dict) -> set[str]:
    """Tập op-tail '<mod>.<fn>' của các operation security==[] (rút từ operationId)."""
    tails: set[str] = set()
    for item in spec["paths"].values():
        for op in item.values():
            if op.get("security") == []:
                op_id = op["operationId"]
                tails.add(op_id.replace("assetcore.api.", "", 1))
    return tails


class TestOasD11GuestStat(unittest.TestCase):
    """guest_count = số operation security==[] trong rendered paths (KHÔNG đọc global)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    # ── TC-OAS-D11-01 (RED-first) ────────────────────────────────────────────
    def test_d11_01_guest_count_equals_rendered_security_empty_ops(self):
        """guest_count == len([op trong paths có security==[]]) — nguồn = rendered paths."""
        rendered = _rendered_guest_ops(self.spec)
        self.assertEqual(
            self.spec["x-assetcore-stats"]["guest_count"],
            len(rendered),
            "guest_count PHẢI == số operation security==[] trong spec['paths'] "
            "(bề mặt guest THẬT), KHÔNG == len(frappe.guest_methods) global volatile.",
        )

    # ── TC-OAS-D11-02 (exact surface) ────────────────────────────────────────
    def test_d11_02_guest_surface_is_exactly_the_five_documented_tails(self):
        """Tập op-tail guest == đúng 5 tail documented; guest_count == len(tập đó)."""
        tails = _guest_path_tails(self.spec)
        self.assertEqual(
            tails,
            _EXPECTED_GUEST_TAILS,
            "Bề mặt guest (security==[]) PHẢI == đúng 5 endpoint documented "
            "(không thừa, không thiếu).",
        )
        self.assertEqual(
            self.spec["x-assetcore-stats"]["guest_count"],
            len(tails),
            "guest_count PHẢI == len(tập guest-tail) — KHÔNG hardcode 5.",
        )

    # ── TC-OAS-D11-03 (invariant) ────────────────────────────────────────────
    def test_d11_03_guest_count_invariants(self):
        """0 < guest_count <= total_endpoints; guest_count < get+post; đếm OP không path-item."""
        stats = self.spec["x-assetcore-stats"]
        gc = stats["guest_count"]
        total = stats["total_endpoints"]
        self.assertGreater(gc, 0, "Phải có ≥1 guest endpoint.")
        self.assertLessEqual(gc, total, "guest_count PHẢI <= total_endpoints.")
        self.assertLess(
            gc,
            stats["get_count"] + stats["post_count"],
            "guest_count PHẢI < get_count+post_count (guest là tập con của tổng op).",
        )
        # Đếm theo OPERATION (security==[]), KHÔNG theo path-item: nếu 1 path có 2 verb
        # đều guest thì đếm 2. Xác minh count == Σ operation, không == Σ path-item.
        op_count = sum(
            1
            for item in self.spec["paths"].values()
            for op in item.values()
            if op.get("security") == []
        )
        path_item_count = sum(
            1
            for item in self.spec["paths"].values()
            if any(op.get("security") == [] for op in item.values())
        )
        self.assertEqual(gc, op_count, "guest_count đếm theo OPERATION.")
        # Hiện 5 guest op nằm trên 5 path-item khác nhau → 2 con số trùng, nhưng công
        # thức PHẢI đếm operation (op_count), không path_item_count.
        self.assertEqual(op_count, path_item_count, "Hiện không path nào multi-verb guest.")

    # ── TC-OAS-D11-04 (no-global-dependency / mutation guard) ────────────────
    def test_d11_04_guest_count_independent_of_global_registry(self):
        """Monkeypatch frappe.guest_methods (to/rỗng) → _assetcore_stats(paths) KHÔNG đổi.

        Chứng minh guest_count KHÔNG còn đọc global registry — chỉ dùng paths dict.
        """
        paths = self.spec["paths"]
        baseline = openapi._assetcore_stats(paths)["guest_count"]

        saved = frappe.guest_methods
        try:
            # Fake set LỚN HƠN (giả lập 10-context) — nếu stat còn đọc global, gc sẽ đổi.
            class _Fake:
                __module__ = "fake.mod"
                __qualname__ = "fake_guest"

            frappe.guest_methods = [_Fake() for _ in range(10)]
            after_big = openapi._assetcore_stats(paths)["guest_count"]
            self.assertEqual(
                after_big,
                baseline,
                "guest_count PHẢI bất biến khi guest_methods phình to "
                "(không đọc global registry).",
            )
            # Fake set RỖNG — nếu còn đọc global, gc sẽ về 0.
            frappe.guest_methods = []
            after_empty = openapi._assetcore_stats(paths)["guest_count"]
            self.assertEqual(
                after_empty,
                baseline,
                "guest_count PHẢI bất biến khi guest_methods rỗng "
                "(không đọc global registry).",
            )
        finally:
            frappe.guest_methods = saved

    def test_d11_04b_guest_count_deterministic_across_regenerate(self):
        """Lặp generate_spec() nhiều lần → guest_count ổn định (không phụ thuộc boot ctx)."""
        runs = [openapi.generate_spec()["x-assetcore-stats"]["guest_count"] for _ in range(3)]
        self.assertEqual(len(set(runs)), 1, f"guest_count phải ổn định, nhận {runs}.")

    # ── TC-OAS-D11-05 (regression on sibling stats) ──────────────────────────
    def test_d11_05_sibling_stats_unchanged(self):
        """total/get/post/enriched/json_param/version — KHÔNG đổi (chỉ guest_count đổi nguồn)."""
        from assetcore.services.shared import rbac

        stats = self.spec["x-assetcore-stats"]
        paths = self.spec["paths"]
        self.assertEqual(
            stats["total_endpoints"], len(paths), "total_endpoints == len(paths)."
        )
        self.assertEqual(
            stats["get_count"] + stats["post_count"],
            stats["total_endpoints"],
            "get+post == total.",
        )
        # D6-IMM09-ENRICH: enriched_count derive ĐỘNG (KHÔNG magic 161) — đếm op có
        # enrich_meta_for != None qua chính helper SSoT (bất biến khi mở rộng D6_MODULES).
        expected_enriched = sum(
            1
            for p in paths
            if _ovr.enrich_meta_for(p.replace("/api/method/assetcore.api.", "", 1)) is not None
        )
        self.assertEqual(
            stats["enriched_count"], expected_enriched,
            "enriched_count == số op enrich_meta_for!=None (đếm động, KHÔNG magic).",
        )
        self.assertEqual(
            stats["json_param_count"],
            openapi._total_json_string_params(),
            "json_param_count == đếm động.",
        )
        self.assertEqual(stats["cap_set_version"], rbac.CAP_SET_VERSION)
        self.assertEqual(stats["generated_app_version"], openapi._app_version())
