"""TC-OAS-D7-01..06 — Serve OpenAPI spec endpoint (session-gated + cached) + Swagger UI page.

Bám ADR-IMM00-OPENAPI §D7 (Phase A7). Test viết TRƯỚC implement (TDD RED→GREEN).

D7 phủ:
  - SERVE: `@frappe.whitelist(methods=['GET']) def spec() -> dict` trong api/openapi.py.
    · Session user thường → trả RAW OpenAPI 3.1 dict (KHÔNG bọc SuccessEnvelope).
    · Guest → frappe.PermissionError (KHÔNG allow_guest, KHÔNG lộ 485-endpoint — F6).
  - CACHE: `_cached_spec()` đọc `frappe.cache().get_value(_spec_cache_key())`; miss →
    `generate_spec()` rồi set; hit → trả thẳng (KHÔNG re-introspect). Key versioned theo
    `CAP_SET_VERSION` + `_app_version()` → tự bust khi thêm cap / bump version.
  - VERB-GATE: spec endpoint GET-only (allowed_http_methods == ['GET']); operationId/path
    KHÔNG phá quy ước D2 (path-tail unique).

KHÔNG ghi đè class/fn D1-D6 — dùng TÊN MỚI `TestOasD7Serve`. Suite test_oas_generator (49) +
test_oas_signatures (11) KHÔNG regression (TC-OAS-D7-06).

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_serve
"""
from __future__ import annotations

import unittest
from unittest import mock

import frappe

from assetcore.api import openapi
from assetcore.tests._helpers.paths import APP_ROOT


class TestOasD7Serve(unittest.TestCase):
    """D7 serve + cache — TÊN MỚI, KHÔNG đụng class D1-D6."""

    def setUp(self):
        frappe.set_user("Administrator")
        # Cache phải sạch trước mỗi test cache-sensitive (D7-03/01).
        frappe.cache().delete_value(openapi._spec_cache_key())

    def tearDown(self):
        frappe.set_user("Administrator")
        try:
            frappe.cache().delete_value(openapi._spec_cache_key())
        except Exception:
            pass

    # ── TC-OAS-D7-01 — session user thường → RAW spec dict, KHÔNG envelope ─────
    def test_oas_d7_01_logged_in_returns_raw_spec(self):
        spec = openapi.spec()
        self.assertIsInstance(spec, dict)
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("paths", spec)
        self.assertTrue(spec["paths"], "paths phải non-empty.")
        # RAW — KHÔNG bọc SuccessEnvelope.
        self.assertNotIn("success", spec, "spec phải RAW, KHÔNG có key 'success'.")
        self.assertNotIn("data", spec, "spec phải RAW, KHÔNG có key 'data' (envelope).")
        # len(paths) == generate_spec()['paths'] (cùng introspect surface).
        self.assertEqual(
            len(spec["paths"]),
            len(openapi.generate_spec()["paths"]),
            "len(paths) phải == generate_spec()['paths'].",
        )

    # ── TC-OAS-D7-02 — Guest → PermissionError, KHÔNG leak paths ──────────────
    def test_oas_d7_02_guest_raises_permission_error(self):
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                openapi.spec()
        finally:
            frappe.set_user("Administrator")

    def test_oas_d7_02_guest_no_surface_leak(self):
        """Guest KHÔNG nhận được dict có 'paths' (no 485-endpoint leak — F6)."""
        frappe.set_user("Guest")
        try:
            result = None
            try:
                result = openapi.spec()
            except frappe.PermissionError:
                pass
            # Dù bằng cơ chế gì, Guest KHÔNG được nhận spec có paths.
            if isinstance(result, dict):
                self.assertNotIn("paths", result, "Guest KHÔNG được thấy paths.")
        finally:
            frappe.set_user("Administrator")

    # ── TC-OAS-D7-03 — cache HIT: gọi 2 lần → generate_spec called == 1 ───────
    def test_oas_d7_03_cache_hit_no_reintrospect(self):
        frappe.cache().delete_value(openapi._spec_cache_key())
        real_generate = openapi.generate_spec
        calls = {"n": 0}

        def counting_generate():
            calls["n"] += 1
            return real_generate()

        with mock.patch.object(openapi, "generate_spec", counting_generate):
            first = openapi.spec()
            self.assertEqual(calls["n"], 1, "Lần 1 phải gọi generate_spec đúng 1 lần.")
            second = openapi.spec()
            self.assertEqual(
                calls["n"], 1, "Lần 2 phải HIT cache, KHÔNG re-introspect (vẫn ==1)."
            )
        self.assertIsInstance(first, dict)
        self.assertIsInstance(second, dict)
        self.assertEqual(first, second, "2 lần gọi phải trả dict bằng nhau.")

    # ── TC-OAS-D7-04 — cache key bust khi CAP_SET_VERSION / app_version đổi ────
    def test_oas_d7_04_cache_key_busts_on_cap_set_version(self):
        baseline = openapi._spec_cache_key()
        with mock.patch(
            "assetcore.services.shared.rbac.CAP_SET_VERSION", "vZZZ.deadbeef0000"
        ):
            mutated = openapi._spec_cache_key()
        self.assertNotEqual(
            baseline, mutated, "Key phải ĐỔI khi CAP_SET_VERSION đổi (chống stale)."
        )

    def test_oas_d7_04_cache_key_busts_on_app_version(self):
        baseline = openapi._spec_cache_key()
        with mock.patch.object(openapi, "_app_version", lambda: "99.99.99"):
            mutated = openapi._spec_cache_key()
        self.assertNotEqual(
            baseline, mutated, "Key phải ĐỔI khi _app_version() đổi (chống stale)."
        )

    def test_oas_d7_04_cache_key_format_prefix(self):
        key = openapi._spec_cache_key()
        self.assertTrue(
            key.startswith("ac_openapi_spec_v"),
            f"Key phải prefix 'ac_openapi_spec_v' (giống ac_caps pattern), got {key!r}.",
        )

    # ── TC-OAS-D7-05 — verb-gate: spec endpoint GET-only, opId/path không phá D2 ──
    def test_oas_d7_05_spec_endpoint_is_get_only(self):
        allowed = frappe.allowed_http_methods_for_whitelisted_func.get(openapi.spec)
        self.assertIsNotNone(
            allowed, "openapi.spec phải đã @frappe.whitelist (có trong registry)."
        )
        self.assertEqual(
            sorted(allowed), ["GET"], f"spec phải GET-only, got {allowed!r}."
        )

    def test_oas_d7_05_spec_in_generated_spec_path_tail_unique(self):
        """spec endpoint tự xuất hiện trong generate_spec() và path-tail unique (D2)."""
        generated = openapi.generate_spec()
        spec_path = "/api/method/assetcore.api.openapi.spec"
        self.assertIn(
            spec_path,
            generated["paths"],
            "Endpoint spec phải tự introspect-được trong generate_spec().",
        )
        # GET-only → verb 'get' trong operation map.
        self.assertIn("get", generated["paths"][spec_path])
        # operationId == path-tail; unique trong toàn spec.
        op_ids = [
            op.get("operationId")
            for item in generated["paths"].values()
            for op in item.values()
        ]
        self.assertEqual(
            len(op_ids), len(set(op_ids)), "operationId phải DUY NHẤT (D2)."
        )


class TestOasD18SwaggerAssets(unittest.TestCase):
    """TC-OAS-D18 — Swagger UI asset-resolvable + dev-preview fallback (ADR-IMM00-OPENAPI §D18).

    BỆNH: www/api-docs.html ref /assets/assetcore/swagger-ui/* → 404 ở werkzeug dev :8000 (KHÔNG
    serve /assets/, chỉ nginx prod). FIX: (1) file local TỒN TẠI trên đĩa (public/swagger-ui/ →
    /assets/ qua symlink prod → asset-path resolvable ở prod); (2) api-docs.html có loader
    local-first + CDN-fallback (CHỈ khi local 404) → dev-preview KHÔNG vỡ trang. Prod air-gapped:
    local LUÔN resolve → KHÔNG chạm CDN.
    """

    import pathlib as _pathlib
    _APP_ROOT = _pathlib.Path(APP_ROOT)
    _SWAGGER_DIR = _APP_ROOT / "public" / "swagger-ui"
    _HTML = _APP_ROOT / "www" / "api-docs.html"
    _REQUIRED_ASSETS = (
        "swagger-ui.css",
        "swagger-ui-bundle.js",
        "swagger-ui-standalone-preset.js",
    )

    def test_oas_d18_01_local_assets_present_on_disk(self):
        """3 asset Swagger UI TỒN TẠI trên đĩa (public/swagger-ui/) — prod /assets/ symlink resolve.
        Đây là điều kiện asset-path /assets/assetcore/swagger-ui/* resolvable ở prod (air-gapped)."""
        self.assertTrue(self._SWAGGER_DIR.is_dir(), f"Thiếu thư mục {self._SWAGGER_DIR}")
        for asset in self._REQUIRED_ASSETS:
            p = self._SWAGGER_DIR / asset
            self.assertTrue(p.is_file(), f"Thiếu asset Swagger UI local (prod air-gapped cần): {p}")
            self.assertGreater(p.stat().st_size, 0, f"Asset rỗng: {p}")

    def test_oas_d18_02_html_refs_local_first(self):
        """api-docs.html VẪN ref local /assets/assetcore/swagger-ui/* TRƯỚC (prod air-gapped ưu tiên
        self-host — KHÔNG ép phụ thuộc CDN). 3 asset path local có mặt trong HTML."""
        html = self._HTML.read_text(encoding="utf-8")
        for asset in self._REQUIRED_ASSETS:
            self.assertIn(
                f"/assets/assetcore/swagger-ui/{asset}", html,
                f"api-docs.html PHẢI ref local /assets/assetcore/swagger-ui/{asset} (prod self-host).",
            )

    def test_oas_d18_03_html_has_dev_preview_cdn_fallback(self):
        """api-docs.html có dev-preview fallback CDN (CHỈ khi local 404 — onerror) + crossorigin.
        Đảm bảo dev werkzeug :8000 (KHÔNG serve /assets/) KHÔNG vỡ trang trắng."""
        html = self._HTML.read_text(encoding="utf-8")
        # Loader có nhánh onerror → fallback CDN swagger-ui-dist (dev-only).
        self.assertIn("onerror", html, "api-docs.html PHẢI có onerror fallback (local 404 → CDN dev-preview).")
        self.assertIn(
            "swagger-ui-dist@", html,
            "api-docs.html PHẢI có CDN fallback swagger-ui-dist@<version> (dev-preview khi local 404).",
        )
        self.assertIn(
            "crossOrigin", html,
            "Script CDN fallback PHẢI set crossOrigin='anonymous' (điều kiện SRI + CORS).",
        )
        # acSwaggerReady gate: bootstrap CHỜ loader xong (local-first/CDN-fallback).
        self.assertIn(
            "acSwaggerReady", html,
            "api-docs.html PHẢI gate bootstrap qua acSwaggerReady (chờ bundle sẵn sàng).",
        )

    def test_oas_d18_04_html_unwraps_frappe_message_envelope(self):
        """§F-C1 regression — api-docs.html PHẢI unwrap envelope Frappe {message:} trước khi
        feed Swagger UI. openapi.spec() là @frappe.whitelist → dispatcher BỌC return value vào
        {"message": <spec>}; nếu loader feed `url:` thẳng, Swagger đọc top-level KHÔNG thấy
        'openapi:' → "Unable to render this definition" (render trắng, 0 opblock). FIX = fetch tự
        + đọc `.message` + feed `spec:` object. Test khoá: KHÔNG còn `url:` trỏ thẳng spec endpoint
        + CÓ unwrap `.message` + feed `spec:`."""
        html = self._HTML.read_text(encoding="utf-8")
        # Phải fetch spec rồi feed `spec:` object (KHÔNG `url:` để Swagger tự fetch raw envelope).
        self.assertIn(
            "spec:", html,
            "api-docs.html PHẢI feed `spec:` (object đã unwrap), KHÔNG `url:` (Swagger fetch raw envelope).",
        )
        self.assertIn(
            ".message", html,
            "api-docs.html PHẢI unwrap `.message` (envelope Frappe {message:<spec>}) trước khi render.",
        )
        self.assertNotIn(
            'url: "/api/method/assetcore.api.openapi.spec"', html,
            "api-docs.html KHÔNG được feed `url:` thẳng vào SwaggerUIBundle — Swagger sẽ render "
            "envelope {message:} thay vì spec → 'Unable to render this definition' (F-C1).",
        )
        # Vẫn fetch đúng endpoint spec session-gated (cùng origin, cookie sid).
        self.assertIn(
            "/api/method/assetcore.api.openapi.spec", html,
            "api-docs.html VẪN fetch endpoint spec session-gated (qua fetch, KHÔNG qua url:).",
        )


if __name__ == "__main__":
    unittest.main()
