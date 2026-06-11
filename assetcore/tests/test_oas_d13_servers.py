"""TC-OAS-D13-01..06 — D13 OpenAPI root `servers[]` dẫn xuất từ `frappe.utils.get_url()`.

Bám ADR-IMM00-OPENAPI §D13 (Phase A D13). Test viết TRƯỚC implement (TDD RED→GREEN).

D13 phủ:
  - root-level `servers`: list non-empty (>=1 entry), CHÈN ngay sau `info` và TRƯỚC
    `components` (thứ tự info→servers→components→paths→tags→x-assetcore-stats).
  - servers[0].url == `frappe.utils.get_url().rstrip('/')` (SSoT site base; BARE origin,
    KHÔNG kèm '/api/method/', KHÔNG trailing slash thừa). servers[0].description = chuỗi VI.
  - KHÔNG hardcode host/URL trong logic servers: chỉ gọi get_url() — grep source openapi.py
    vùng `_servers` KHÔNG có literal 'http://'/'https://'/tên site cố định.
  - Fail-safe: get_url() raise/rỗng → servers == [{'url':'/','description':<fallback>}];
    generate_spec() KHÔNG bao giờ exception; 485 endpoint vẫn sinh đủ.
  - x-assetcore-stats bất biến (servers không phải operation): total/get/post/guest/
    enriched/error_responses_typed/json_param KHÔNG đổi; enriched_count == derive ĐỘNG
    (đếm op enrich_meta_for!=None, KHÔNG magic) giữ nguyên; len(paths)==total_endpoints.

KHÔNG regression: test_oas_generator + test_oas_signatures + test_oas_serve +
test_oas_d8_metadata + d9/d10/d11/d12 GIỮ GREEN (servers thêm ở root, không đụng
path/operation/component/stat hiện có).

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_d13_servers
"""
from __future__ import annotations

import inspect
import re
import unittest
from unittest import mock

import frappe

from assetcore.api import openapi
from assetcore.api import openapi_overrides as _ovr


class TestOasD13Servers(unittest.TestCase):
    """TC-OAS-D13-01/02 — root servers[] dẫn xuất ĐỘNG từ get_url() (SSoT, no hardcode)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    # ── TC-OAS-D13-01 ────────────────────────────────────────────────────────
    def test_d13_01_servers_is_non_empty_list_with_url_and_description(self):
        """generate_spec()['servers'] là list len>=1; mỗi entry có 'url' (str non-empty)
        + 'description' (str non-empty)."""
        spec = self.spec
        self.assertIn("servers", spec, "Spec PHẢI có key 'servers' ở ROOT-LEVEL (D13).")
        servers = spec["servers"]
        self.assertIsInstance(servers, list, "servers phải là list.")
        self.assertGreaterEqual(len(servers), 1, "servers phải có >=1 entry (non-empty).")
        for entry in servers:
            self.assertIsInstance(entry, dict, "mỗi server entry phải là dict.")
            self.assertIn("url", entry, "server entry thiếu 'url'.")
            self.assertIn("description", entry, "server entry thiếu 'description'.")
            self.assertIsInstance(entry["url"], str, "server.url phải là str.")
            self.assertIsInstance(entry["description"], str, "server.description phải là str.")
            self.assertTrue(entry["url"], "server.url phải non-empty.")
            self.assertTrue(entry["description"], "server.description phải non-empty.")

    def test_d13_01_servers_key_order_after_info_before_components(self):
        """list(spec.keys()): 'servers' NGAY SAU 'info' và TRƯỚC 'components'.

        Thứ tự đầy đủ: info → servers → components → paths → tags → x-assetcore-stats.
        """
        keys = list(self.spec.keys())
        self.assertIn("servers", keys)
        # servers ngay sau info (index liền kề).
        self.assertEqual(
            keys.index("servers"),
            keys.index("info") + 1,
            "servers PHẢI nằm NGAY SAU info (index liền kề).",
        )
        # servers trước components.
        self.assertLess(
            keys.index("servers"),
            keys.index("components"),
            "servers PHẢI đứng TRƯỚC components.",
        )
        # Thứ tự tổng thể info<servers<components<paths<tags<x-assetcore-stats.
        order = ["info", "servers", "components", "paths", "tags", "x-assetcore-stats"]
        idxs = [keys.index(k) for k in order]
        self.assertEqual(idxs, sorted(idxs), f"Thứ tự key PHẢI là {order}; thực tế {keys}.")

    # ── TC-OAS-D13-02 ────────────────────────────────────────────────────────
    def test_d13_02_servers_url_matches_get_url_ssot(self):
        """servers[0]['url'] == frappe.utils.get_url().rstrip('/') (SSoT ĐỘNG, KHÔNG hardcode);
        url KHÔNG kết thúc '/api/method/' và KHÔNG có trailing slash thừa."""
        expected = frappe.utils.get_url().rstrip("/")
        url = self.spec["servers"][0]["url"]
        self.assertEqual(
            url,
            expected,
            "servers[0].url PHẢI == get_url().rstrip('/') (SSoT, không hardcode site).",
        )
        self.assertFalse(
            url.endswith("/api/method/"),
            "servers[0].url là BARE origin — KHÔNG kèm '/api/method/' (path-prefix đã ở từng path).",
        )
        # Trailing slash thừa: chỉ '/' đơn (fallback) được phép end '/'; bare origin thì KHÔNG.
        self.assertFalse(
            url.endswith("/") and url != "/",
            f"servers[0].url KHÔNG được có trailing slash thừa: {url!r}.",
        )

    def test_d13_02_servers_description_is_vietnamese(self):
        """servers[0].description là chuỗi VI mô tả (dẫn xuất động từ cấu hình Frappe)."""
        desc = self.spec["servers"][0]["description"]
        self.assertTrue(desc, "description phải non-empty.")
        # VI mô tả 'Site hiện tại — dẫn xuất động từ cấu hình Frappe'.
        self.assertIn("Site hiện tại", desc, "description PHẢI là chuỗi VI mô tả site hiện tại.")
        # KHÔNG leak EN-status / raw key tiếng Anh.
        self.assertNotRegex(desc, r"\b(Active|Pending|Server|Production)\b")


class TestOasD13ServersFailSafe(unittest.TestCase):
    """TC-OAS-D13-03 — fail-safe: get_url() raise/rỗng → fallback relative '/' (KHÔNG vỡ spec)."""

    def test_d13_03_get_url_raises_falls_back_to_relative_root(self):
        """monkeypatch frappe.utils.get_url raise → generate_spec() KHÔNG raise;
        servers == [{'url':'/','description':<fallback>}]; len(paths)==total_endpoints."""
        with mock.patch.object(
            frappe.utils, "get_url", side_effect=RuntimeError("no request context")
        ):
            spec = openapi.generate_spec()  # KHÔNG được raise.
        servers = spec["servers"]
        self.assertEqual(len(servers), 1, "Fail-safe → servers vẫn là list 1 entry.")
        self.assertEqual(servers[0]["url"], "/", "Fallback url PHẢI là relative '/'.")
        self.assertTrue(servers[0]["description"], "Fallback description phải non-empty.")
        # len(paths) vẫn == total_endpoints (servers fail KHÔNG ảnh hưởng 485 endpoint).
        self.assertEqual(
            len(spec["paths"]),
            spec["x-assetcore-stats"]["total_endpoints"],
            "Fail-safe servers KHÔNG được làm hụt endpoint.",
        )
        self.assertGreater(len(spec["paths"]), 50, "Sanity: vẫn sinh đủ hàng trăm endpoint.")

    def test_d13_03_get_url_returns_empty_falls_back_to_relative_root(self):
        """get_url() trả '' (ngữ cảnh không-request) → fallback relative '/' (KHÔNG bare empty)."""
        with mock.patch.object(frappe.utils, "get_url", return_value=""):
            spec = openapi.generate_spec()
        servers = spec["servers"]
        self.assertEqual(len(servers), 1)
        self.assertEqual(
            servers[0]["url"], "/", "get_url()=='' → fallback '/' (KHÔNG url rỗng vô nghĩa)."
        )

    def test_d13_03_get_url_returns_none_falls_back(self):
        """get_url() trả None (defensive) → fallback relative '/' (KHÔNG crash .rstrip)."""
        with mock.patch.object(frappe.utils, "get_url", return_value=None):
            spec = openapi.generate_spec()
        self.assertEqual(spec["servers"][0]["url"], "/")


class TestOasD13NoHardcode(unittest.TestCase):
    """TC-OAS-D13-04 — no-hardcode guard: source openapi.py vùng _servers chỉ reference get_url."""

    def test_d13_04_servers_helper_has_no_hardcoded_host_or_url(self):
        """Đọc source `_servers` helper → KHÔNG có literal 'http://'/'https://'/tên site cố định;
        CHỈ reference get_url (chống regression nhét host cứng)."""
        # Helper PHẢI tồn tại (đặt tên _servers — vùng logic build servers[]).
        self.assertTrue(
            hasattr(openapi, "_servers"),
            "openapi.py PHẢI có helper `_servers` (vùng build servers[] tách bạch để guard).",
        )
        src = inspect.getsource(openapi._servers)
        self.assertNotIn("http://", src, "Vùng _servers KHÔNG được có literal 'http://'.")
        self.assertNotIn("https://", src, "Vùng _servers KHÔNG được có literal 'https://'.")
        # Tên site cố định 'miyano' (dev) KHÔNG được hardcode.
        self.assertNotIn("miyano", src, "Vùng _servers KHÔNG được hardcode tên site 'miyano'.")
        # PHẢI reference get_url (nguồn SSoT).
        self.assertIn("get_url", src, "Vùng _servers PHẢI gọi get_url() (SSoT, không hardcode).")

    def test_d13_04_whole_module_no_literal_site_host(self):
        """Toàn module openapi.py KHÔNG có literal http(s):// hoặc tên site dev (anti-regression rộng)."""
        src = inspect.getsource(openapi)
        # Cho phép 'http_status' / 'allowed_http_methods' (KHÔNG phải URL literal). Bắt literal scheme.
        self.assertNotRegex(
            src,
            r"https?://[A-Za-z0-9]",
            "openapi.py KHÔNG được chứa URL literal scheme://host (chỉ get_url() SSoT).",
        )


class TestOasD13StatsInvariant(unittest.TestCase):
    """TC-OAS-D13-05 — x-assetcore-stats bất biến: servers không phải operation → không lệch số."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d13_05_stats_unchanged_total_equals_paths(self):
        """total_endpoints == len(paths); get+post == total (servers KHÔNG đụng số đếm op)."""
        stats = self.spec["x-assetcore-stats"]
        self.assertEqual(stats["total_endpoints"], len(self.spec["paths"]))
        self.assertEqual(stats["get_count"] + stats["post_count"], stats["total_endpoints"])

    def test_d13_05_enriched_count_unchanged(self):
        """enriched_count == derive ĐỘNG (servers thêm ở root, KHÔNG đụng op enrich).

        D6-IMM09-ENRICH: KHÔNG còn snapshot magic 161 (3-module) — đếm op enrich động qua
        helper SSoT (bất biến khi mở rộng D6_MODULES). Servers KHÔNG phải operation enrich.
        """
        expected = sum(
            1
            for p in self.spec["paths"]
            if _ovr.enrich_meta_for(p.replace("/api/method/assetcore.api.", "", 1)) is not None
        )
        self.assertEqual(
            self.spec["x-assetcore-stats"]["enriched_count"],
            expected,
            "enriched_count PHẢI == số op enrich đếm động (servers không phải op enrich).",
        )

    def test_d13_05_stats_keys_present_and_int(self):
        """Mọi khóa stats đếm vẫn là int (servers KHÔNG biến đổi shape stats)."""
        stats = self.spec["x-assetcore-stats"]
        for key in (
            "total_endpoints",
            "get_count",
            "post_count",
            "guest_count",
            "enriched_count",
            "error_responses_typed_count",
            "json_param_count",
        ):
            self.assertIn(key, stats, f"x-assetcore-stats thiếu khóa {key} (servers không xoá stat).")
            self.assertIsInstance(stats[key], int, f"{key} phải là int.")

    def test_d13_05_servers_not_counted_as_operation(self):
        """servers[] KHÔNG xuất hiện trong paths (không bị đếm như endpoint)."""
        # Mọi path key bắt đầu '/api/method/' — servers không tạo path giả.
        for path in self.spec["paths"]:
            self.assertTrue(path.startswith("/api/method/"), f"Path lạ (servers leak?): {path!r}.")


class TestOasD13Validity(unittest.TestCase):
    """TC-OAS-D13-06 (phần validity) — spec vẫn valid OpenAPI 3.1 với servers ở root."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d13_06_openapi_version_and_servers_schema_valid(self):
        """openapi==3.1.0; servers là array-of-objects {url[, description]} (field hợp lệ root 3.1)."""
        self.assertEqual(self.spec["openapi"], "3.1.0")
        servers = self.spec["servers"]
        self.assertIsInstance(servers, list)
        for e in servers:
            # OpenAPI Server Object: 'url' bắt buộc; 'description' optional (ở đây luôn có).
            self.assertIn("url", e)
            # Chỉ url + description (không field lạ phá validator).
            self.assertTrue(set(e.keys()) <= {"url", "description", "variables"})

    def test_d13_06_spec_serializes_json_with_servers(self):
        """spec serialize JSON OK với key servers (Swagger UI consume được)."""
        import json

        s = frappe.as_json(self.spec)
        round_trip = json.loads(s)
        self.assertIn("servers", round_trip)
        self.assertIsInstance(round_trip["servers"], list)
        self.assertEqual(round_trip["openapi"], "3.1.0")

