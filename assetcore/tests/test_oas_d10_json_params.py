"""TC-OAS-D10-01..07 — D10 JSON_PARAM_OVERRIDES: đánh dấu param JSON-string trong spec.

Bám ADR-IMM00-OPENAPI §D10. Test viết TRƯỚC implement (TDD RED→GREEN).

D10 phủ:
  - AST-discovery helper `openapi._json_string_params(fn) -> set[str]`: parse source-file
    của module bằng `ast` (cơ chế ADR §D2 — bất biến quote-style), tìm Call tới
    `parse_json`/`_parse_json`/`json.loads`/`frappe.parse_json` mà arg[0] là Name trùng
    tên 1 param đặt-tên của fn → trả tập tên param JSON-string. Cache theo module.
    DEFENSIVE: file/hàm không parse được → set() rỗng.
  - Wire vào `_parameters_for` (GET query-param) + `_request_body_for` (POST body property):
    param ∈ tập JSON-string → thêm `format:json` + `x-decoded-default-type` (dẫn xuất từ
    default literal: '{}'→object, '[]'→array, else 'object'/'string' theo parse_json default
    kwarg). KHÔNG đổi `type` (giữ 'string'). KHÔNG đụng D5 `_request_body_from_doctype`.
  - Registry `JSON_PARAM_OVERRIDES` (curated SSoT) keyed '<module>.<fn>.<param>' →
    {'x-decoded-schema': {...}}. ≥2 entry; MỌI key resolve về param JSON-string introspect-được
    (drift-guard: entry trỏ param không-tồn-tại → fail). Override đè x-decoded-default-type.
  - `x-assetcore-stats.json_param_count` = Σ param JSON-string introspect-được (đếm động).
  - Invariant: len(paths)==492 (đếm ĐỘNG @source generate_spec; 2026-07-01 rebase 488→492:
    hợp nhất off-by-1 sót của 979d736 + 3 web GET mới); enriched_count = derive ĐỘNG (no magic);
    root tags 23 canonical; openapi==3.1.0;
    format:json chỉ THÊM khoá (type vẫn 'string') — backward-compatible.

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_d10_json_params
"""
from __future__ import annotations

import unittest

import frappe

import assetcore.api.imm00 as m00
import assetcore.api.imm04 as m04
import assetcore.api.imm08 as m08
import assetcore.api.imm12 as m12
from assetcore.api import openapi
from assetcore.api import openapi_overrides as _ovr
from assetcore.tests.oas_baseline import BASELINE_TOTAL


def _flatten_json_string_params() -> set[str]:
    """Σ '<mod>.<fn>.<param>' qua MỌI endpoint whitelisted (đếm động — KHÔNG hardcode 109)."""
    mods = openapi._iter_api_modules()
    name_set = openapi._whitelisted_name_set()
    out: set[str] = set()
    for mod in mods:
        mod_short = openapi._module_short(mod)
        for fn_name, fn in openapi._whitelisted_functions_in(mod, name_set):
            for p in openapi._json_string_params(fn):
                out.add(f"{mod_short}.{fn_name}.{p}")
    return out


class TestOasD10AstDiscovery(unittest.TestCase):
    """TC-OAS-D10-01 — AST discovery: phát hiện đúng tập param JSON-string của 1 fn."""

    def test_d10_01_list_pm_work_orders_filters(self):
        """`_json_string_params(list_pm_work_orders)` == {'filters'} (parse_json(filters))."""
        self.assertEqual(
            openapi._json_string_params(m08.list_pm_work_orders), {"filters"}
        )

    def test_d10_01_create_commissioning_data(self):
        """`_json_string_params(create_commissioning)` == {'data'} (_parse_json(data))."""
        self.assertEqual(
            openapi._json_string_params(m04.create_commissioning), {"data"}
        )

    def test_d10_01_save_commissioning_fields(self):
        """`_json_string_params(save_commissioning)` == {'fields'} (_parse_json(fields))."""
        self.assertEqual(
            openapi._json_string_params(m04.save_commissioning), {"fields"}
        )

    def test_d10_01_non_parsing_fn_empty(self):
        """Hàm KHÔNG parse param nào (get_asset) → set() rỗng (fail-safe)."""
        self.assertEqual(openapi._json_string_params(m00.get_asset), set())

    def test_d10_01_report_incident_no_param_parse(self):
        """report_incident KHÔNG parse param nào của CHÍNH nó (parse_json ở fn khác) → set()."""
        self.assertEqual(openapi._json_string_params(m12.report_incident), set())

    def test_d10_01_search_link_json_loads_arg(self):
        """imm04.search_link dùng json.loads(filters) → {'filters'} (arg là Name=param)."""
        self.assertEqual(
            openapi._json_string_params(m04.search_link), {"filters"}
        )

    def test_d10_01_dynamic_count_not_hardcoded(self):
        """Tập param JSON-string introspect-được = đếm ĐỘNG (KHÔNG hardcode 109).

        ~109 grep call-site gồm: 14 dòng def/import + ~95 call-site thực, NHIỀU call-site
        nằm trong private delegate (`_list_xxx`) hoặc parse cùng 1 param nhiều lần. Đếm theo
        (whitelisted-fn, param) DUY NHẤT → vài chục cặp. Sanity: phải hàng chục (>40), KHÔNG
        hardcode con số chính xác (mutation thêm param mới → tự tăng).
        """
        params = _flatten_json_string_params()
        self.assertGreater(
            len(params), 40, "Sanity: phải có hàng chục param JSON-string introspect-được."
        )


class TestOasD10GetParamAnnotate(unittest.TestCase):
    """TC-OAS-D10-02 — GET query-param JSON-string có format:json + x-decoded-default-type."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def _op(self, mod: str, fn: str, verb: str) -> dict:
        path = f"/api/method/assetcore.api.{mod}.{fn}"
        self.assertIn(path, self.spec["paths"], f"Thiếu path {path}.")
        return self.spec["paths"][path][verb]

    def test_d10_02_filters_param_has_format_json(self):
        """query-param `filters` của list_pm_work_orders có format:json + default-type 'object'."""
        op = self._op("imm08", "list_pm_work_orders", "get")
        params = {p["name"]: p for p in op["parameters"]}
        self.assertIn("filters", params)
        schema = params["filters"]["schema"]
        self.assertEqual(schema["type"], "string", "type GIỮ 'string' (backward-compat).")
        self.assertEqual(schema["format"], "json", "filters phải có format:json.")
        # default '{}' → object.
        self.assertEqual(schema["x-decoded-default-type"], "object")

    def test_d10_02_scalar_params_no_format_json(self):
        """page/page_size (scalar int) KHÔNG có format:json."""
        op = self._op("imm08", "list_pm_work_orders", "get")
        params = {p["name"]: p for p in op["parameters"]}
        for scalar in ("page", "page_size"):
            self.assertIn(scalar, params)
            self.assertNotIn(
                "format",
                params[scalar]["schema"],
                f"{scalar} (scalar) KHÔNG được có format:json.",
            )
            self.assertNotIn("x-decoded-default-type", params[scalar]["schema"])


class TestOasD10PostBodyAnnotate(unittest.TestCase):
    """TC-OAS-D10-03 — POST requestBody property JSON-string có format:json."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def _post_props(self, mod: str, fn: str) -> dict:
        path = f"/api/method/assetcore.api.{mod}.{fn}"
        op = self.spec["paths"][path]["post"]
        return op["requestBody"]["content"]["application/json"]["schema"]["properties"]

    def test_d10_03_create_commissioning_data_format_json(self):
        """requestBody property `data` của create_commissioning có format:json."""
        props = self._post_props("imm04", "create_commissioning")
        self.assertIn("data", props)
        self.assertEqual(props["data"]["type"], "string", "type GIỮ 'string'.")
        self.assertEqual(props["data"]["format"], "json")
        # default '' → object (parse_json default kwarg convention).
        self.assertEqual(props["data"]["x-decoded-default-type"], "object")

    def test_d10_03_report_incident_scalar_props_no_format_json(self):
        """report_incident (param scalar thật, KHÔNG parse param) → KHÔNG prop có format:json."""
        props = self._post_props("imm12", "report_incident")
        for key, sub in props.items():
            self.assertNotIn(
                "format",
                sub,
                f"report_incident prop {key} (scalar) KHÔNG được có format:json.",
            )


class TestOasD10DefaultTypeDerive(unittest.TestCase):
    """TC-OAS-D10-04 — x-decoded-default-type dẫn xuất từ default literal."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d10_04_array_default_derives_array(self):
        """param default '[]' → x-decoded-default-type 'array' (vd imm09.request_spare_parts.parts)."""
        path = "/api/method/assetcore.api.imm09.request_spare_parts"
        op = self.spec["paths"][path]["post"]
        props = op["requestBody"]["content"]["application/json"]["schema"]["properties"]
        self.assertIn("parts", props)
        self.assertEqual(props["parts"]["format"], "json")
        self.assertEqual(props["parts"]["x-decoded-default-type"], "array")

    def test_d10_04_object_default_derives_object(self):
        """param default '{}' → 'object' (imm08.list_pm_work_orders.filters)."""
        path = "/api/method/assetcore.api.imm08.list_pm_work_orders"
        params = {
            p["name"]: p for p in self.spec["paths"][path]["get"]["parameters"]
        }
        self.assertEqual(params["filters"]["schema"]["x-decoded-default-type"], "object")

    def test_d10_04_empty_string_default_derives_object(self):
        """param default '' → 'object' (parse_json default kwarg: falsy→{} ⟹ object)."""
        path = "/api/method/assetcore.api.imm04.create_commissioning"
        op = self.spec["paths"][path]["post"]
        props = op["requestBody"]["content"]["application/json"]["schema"]["properties"]
        self.assertEqual(props["data"]["x-decoded-default-type"], "object")


class TestOasD10OverrideRegistry(unittest.TestCase):
    """TC-OAS-D10-05 — JSON_PARAM_OVERRIDES + drift-guard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d10_05_registry_has_min_two_entries(self):
        """len(JSON_PARAM_OVERRIDES) ≥ 2 + chứa 2 entry tối thiểu."""
        self.assertGreaterEqual(len(_ovr.JSON_PARAM_OVERRIDES), 2)
        self.assertIn("imm04.create_commissioning.data", _ovr.JSON_PARAM_OVERRIDES)
        self.assertIn("imm04.save_commissioning.fields", _ovr.JSON_PARAM_OVERRIDES)

    def test_d10_05_every_key_resolves_to_real_json_string_param(self):
        """Drift-guard: MỌI key '<mod>.<fn>.<param>' ∈ tập param JSON-string introspect-được."""
        introspected = _flatten_json_string_params()
        for key in _ovr.JSON_PARAM_OVERRIDES:
            self.assertIn(
                key,
                introspected,
                f"JSON_PARAM_OVERRIDES key {key!r} KHÔNG trỏ param JSON-string thực tế "
                "(drift — sửa registry hoặc endpoint).",
            )

    def test_d10_05_override_x_decoded_schema_in_spec(self):
        """create_commissioning.data trong spec có x-decoded-schema từ override (đè default-type)."""
        path = "/api/method/assetcore.api.imm04.create_commissioning"
        op = self.spec["paths"][path]["post"]
        props = op["requestBody"]["content"]["application/json"]["schema"]["properties"]
        self.assertIn("x-decoded-schema", props["data"], "data phải có x-decoded-schema.")
        self.assertIsInstance(props["data"]["x-decoded-schema"], dict)
        # Override KHÔNG xoá format:json (vẫn JSON-string).
        self.assertEqual(props["data"]["format"], "json")

    def test_d10_05_override_helper_returns_none_for_unmapped(self):
        """json_param_override_for cho param không-trong-registry → None (fail-safe)."""
        self.assertIsNone(
            _ovr.json_param_override_for("imm08.list_pm_work_orders", "filters")
        )
        self.assertIsNotNone(
            _ovr.json_param_override_for("imm04.create_commissioning", "data")
        )


class TestOasD10MutationGuard(unittest.TestCase):
    """TC-OAS-D10-06 — mutation-guard có răng: introspection tự khám phá param mới."""

    def test_d10_06_json_param_count_equals_dynamic_set(self):
        """x-assetcore-stats.json_param_count == len(tập introspect-được)."""
        spec = openapi.generate_spec()
        self.assertIn("json_param_count", spec["x-assetcore-stats"])
        self.assertEqual(
            spec["x-assetcore-stats"]["json_param_count"],
            len(_flatten_json_string_params()),
            "json_param_count PHẢI == số param JSON-string introspect động.",
        )

    def test_d10_06_ast_discovery_has_teeth(self):
        """Giả-lập fn thêm parse_json(param) → param xuất hiện trong tập JSON-string.

        Dùng 1 endpoint thật KHÔNG-parse (imm00.get_asset) so với 1 endpoint CÓ-parse
        (imm08.list_pm_work_orders): nếu AST-discovery bị vô hiệu (luôn trả set()), thì
        list_pm_work_orders.filters sẽ KHÔNG xuất hiện → test fail. Đây là 'răng' chống
        xoá AST-discovery.
        """
        self.assertEqual(openapi._json_string_params(m00.get_asset), set())
        self.assertIn("filters", openapi._json_string_params(m08.list_pm_work_orders))
        # Nếu ai đó stub _json_string_params → set() vĩnh viễn, json_param_count == 0.
        self.assertGreater(
            len(_flatten_json_string_params()),
            0,
            "AST-discovery bị vô hiệu → 0 param JSON-string (xoá discovery = test fail).",
        )


class TestOasD10InvariantRegression(unittest.TestCase):
    """TC-OAS-D10-07 — invariant D1-D9 GIỮ + format:json chỉ THÊM khoá."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def test_d10_07_path_count(self):
        """len(paths) == 492 (D1 intact). 2026-07-01 rebase 488→492: 979d736 sót off-by-1
        (endpoint #489 user.list_assignable_users — chỉ vào D15/D17, KHÔNG vào total/D10/D12)
        + 3 web GET mới (get_depreciation_by_category, list_decommissions, get_cycle_count).
        2026-07-09 CR-14/CR-15/CR-17 PHOTO-ATTACH 492→495: +3 multipart POST @whitelist đối xứng
        (imm08.attach_pm_checklist_photo + imm09.attach_repair_checklist_photo + imm12.attach_incident_photo).
        RE-VERIFY @source (QA vòng 3: baseline trước sót imm09 → 494 vs actual 495, đã sửa).
        2026-07-10 RCA-CTA 495→497: +2 POST @whitelist imm12.start_rca + imm12.cancel_rca
        (server-driven RCA transition — GATE-8/BR-12-20/22). RE-VERIFY @source generate_spec.
        2026-07-10 FCR-CTA 497→498: +1 POST @whitelist imm00.transition_firmware_cr
        (server-driven Firmware CR transition — GATE-8/BR-09-20). RE-VERIFY @source generate_spec.
        2026-07-10 COMPETENCY-CTA 498→499: +1 GET @whitelist imm06.get_competency
        (server-driven competency allowed_transitions — GATE-8/LL-FE-51). RE-VERIFY @source generate_spec.
        2026-07-11 CR-WF-12 INCIDENT-REOPEN 499→500: +1 POST @whitelist imm12.reopen_incident
        (server-driven CTA "Mở lại điều tra", Resolved→In Progress — BR-12-23). RE-VERIFY @source generate_spec.
        2026-07-12 CR-WF-15-CC RECOUNT 500→501: +1 POST @whitelist imm15.recount_cycle_count
        (server-driven CTA "Sửa đếm lại", Reviewed→Counting — GATE-8). RE-VERIFY @source generate_spec.
        2026-07-14 CONCURRENT-CTA 501→505: +4 POST @whitelist (imm06.suspend_competency +
        imm06.restore_competency + imm12.request_rca + imm16.start_review). Baseline tuyệt đối nay
        GOM về SSoT `assetcore.tests.oas_baseline.BASELINE_TOTAL` (ledger đầy đủ + open-issue [BA]).
        Số bỏ khỏi tên method (chống magic-number-in-name drift — DESIGN-DEBT [BA])."""
        self.assertEqual(len(self.spec["paths"]), BASELINE_TOTAL)

    def test_d10_07_enriched_count_dynamic(self):
        """enriched_count == derive ĐỘNG (D6 intact, KHÔNG magic 161 — nay 4 module enrich)."""
        expected = sum(
            1
            for p in self.spec["paths"]
            if _ovr.enrich_meta_for(p.replace("/api/method/assetcore.api.", "", 1)) is not None
        )
        self.assertEqual(self.spec["x-assetcore-stats"]["enriched_count"], expected)

    def test_d10_07_root_tags_23_canonical(self):
        """root tags == 23 canonical (D9 intact) — KHÔNG raw lowercase slug."""
        tags = self.spec["tags"]
        self.assertEqual(len(tags), 23, "23 root tag canonical (D9).")
        for t in tags:
            name = t["name"]
            self.assertFalse(
                name.islower() and name.startswith("imm"),
                f"Tag {name!r} là raw lowercase slug — D9 vỡ.",
            )

    def test_d10_07_openapi_version_31(self):
        self.assertEqual(self.spec["openapi"], "3.1.0")

    def test_d10_07_format_json_only_adds_keys_type_unchanged(self):
        """format:json chỉ THÊM khoá vào schema con — type vẫn 'string' (backward-compat).

        Quét MỌI schema con có format:json (GET param + POST property) → type == 'string'.
        """
        n_format = 0
        for item in self.spec["paths"].values():
            for op in item.values():
                # GET params.
                for p in op.get("parameters", []) or []:
                    sub = p["schema"]
                    if sub.get("format") == "json":
                        self.assertEqual(
                            sub["type"], "string", "format:json param type vẫn 'string'."
                        )
                        n_format += 1
                # POST body properties.
                body = op.get("requestBody")
                if body:
                    schema = body["content"]["application/json"]["schema"]
                    for sub in schema.get("properties", {}).values():
                        if sub.get("format") == "json":
                            self.assertEqual(
                                sub["type"], "string", "format:json prop type vẫn 'string'."
                            )
                            n_format += 1
        self.assertGreater(
            n_format, 0, "Phải có ≥1 schema con gắn format:json (D10 có hiệu lực)."
        )


if __name__ == "__main__":
    unittest.main()
