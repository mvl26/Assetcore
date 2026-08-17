"""TC-OAS-01..OPID + ENV-ADD — OpenAPI 3.1 CORE generator (D1+D2+D3).

Bám ADR-IMM00-OPENAPI §D1/D2/D3 (Phase A2). Test viết TRƯỚC implement (TDD RED→GREEN).

CORE round (A2) phủ:
  - D1 introspect: 22 module-file → mọi fn whitelisted (membership trong
    `frappe.whitelisted`, loại re-export bằng `__module__`) → path/operationId.
  - D2 path/method/param/security: path `/api/method/assetcore.api.<mod>.<fn>`;
    method từ `frappe.allowed_http_methods_for_whitelisted_func` (KHÔNG ast/grep);
    param required = không-default; type-map type-hint; security từ
    `frappe.guest_methods`.
  - D3 envelope components: `SuccessEnvelope` + `ErrorEnvelope` sinh TỪ
    `utils/response.py` (ErrorCode + _HTTP_FOR_CODE) — KHÔNG hardcode danh sách 2.

D5 round (A5) phủ THÊM (TC-OAS-06/07 + DOCTYPE-MAP + COVERAGE):
  - D5 form_dict body-bridge: POST `create_*` đọc form_dict (no signature-param) CÓ entry
    trong `openapi_overrides.FORM_DICT_DOCTYPE_MAP` → requestBody object NON-EMPTY sinh từ
    `frappe.get_meta(DocType)`. Đếm động qua registry — KHÔNG hardcode magic number.
  - registry `openapi_overrides.py` import-được THUẦN (no DB ở module-level).
  - fail-safe: form_dict create_* CHƯA map → giữ D4 (requestBody=None) + coverage guard.

OUT OF SCOPE round này (backlog): D6 enrich, D7 serve endpoint + Swagger UI,
D8 x-assetcore-stats. → TC-OAS-08/10/11/12.

Run: bench --site miyano run-tests --module assetcore.tests.guards.test_oas_generator
"""
from __future__ import annotations

import importlib
import inspect
import re
import unittest
from pathlib import Path
from unittest import mock

import frappe

import assetcore.api as _api_pkg
from assetcore.api import openapi
from assetcore.api import openapi_overrides
from assetcore.utils.response import ErrorCode, _HTTP_FOR_CODE

# Đếm động `^@frappe.whitelist` qua mọi api/*.py (KHÔNG hardcode 485).
_WL_RE = re.compile(r"^@frappe\.whitelist")


def _grep_whitelist_count() -> int:
    """Số decorator `^@frappe.whitelist` trong api/*.py (trừ __init__) — acceptance SSoT."""
    api_dir = Path(_api_pkg.__path__[0])
    n = 0
    for py in sorted(api_dir.glob("*.py")):
        if py.name == "__init__.py":
            continue
        for line in py.read_text(encoding="utf-8").splitlines():
            if _WL_RE.match(line):
                n += 1
    return n


def _error_code_values() -> set[str]:
    """Tập value hằng UPPER_CASE str của ErrorCode — đọc TRỰC TIẾP utils/response.py."""
    return {
        v
        for k, v in vars(ErrorCode).items()
        if not k.startswith("_") and isinstance(v, str)
    }


# ── D4 body-bridge introspection (đếm ĐỘNG — KHÔNG hardcode 219/31/235) ───────
def _named_params(fn) -> list:
    """Param đặt tên (bỏ *args/**kwargs) — y như `openapi._request_body_for`/`_parameters_for`."""
    sig = inspect.signature(fn)
    return [
        p
        for p in sig.parameters.values()
        if p.kind
        not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    ]


def _introspect_endpoints() -> list[dict]:
    """Re-introspect MỌI endpoint whitelisted → [{mod, fn_name, verb, named, has_param}].

    Dùng CHÍNH helper của generator (`_iter_api_modules`/`_http_method_for`/
    `_whitelisted_functions_in`) → derive độc lập với spec để cross-check (đếm
    động, KHÔNG hardcode magic). Import HẾT module trước rồi mới snapshot name_set.
    """
    mods = openapi._iter_api_modules()
    name_set = openapi._whitelisted_name_set()
    out: list[dict] = []
    for mod in mods:
        mod_short = openapi._module_short(mod)
        for fn_name, fn in openapi._whitelisted_functions_in(mod, name_set):
            named = _named_params(fn)
            out.append(
                {
                    "mod": mod_short,
                    "fn_name": fn_name,
                    "fn": fn,
                    "verb": openapi._http_method_for(fn),
                    "named": named,
                    "has_param": len(named) > 0,
                }
            )
    return out


class TestOasCoreGenerator(unittest.TestCase):
    """Generator CORE — 1 lần build spec, share cho mọi assertion."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    # ── TC-OAS-01 ────────────────────────────────────────────────────────────
    def test_oas_01_generate_no_exception_and_path_count(self):
        spec = self.spec
        self.assertEqual(spec["openapi"], "3.1.0")
        expected = _grep_whitelist_count()
        self.assertGreater(expected, 50, "Sanity: grep phải bắt được hàng trăm whitelist.")
        self.assertEqual(
            len(spec["paths"]),
            expected,
            f"len(paths)={len(spec['paths'])} != grep ^@frappe.whitelist={expected}",
        )

    def test_oas_01_info_block(self):
        info = self.spec["info"]
        self.assertEqual(info["title"], "AssetCore API")
        self.assertTrue(info.get("version"), "info.version phải có giá trị.")
        self.assertIn("Auto-generated", info.get("description", ""))

    # ── TC-OAS-02 (ErrorCode enum SSoT) ──────────────────────────────────────
    def test_oas_02_error_code_enum_from_response_module(self):
        enum = set(
            self.spec["components"]["schemas"]["ErrorEnvelope"]["properties"]["code"][
                "enum"
            ]
        )
        self.assertEqual(
            enum,
            _error_code_values(),
            "code.enum phải == set(ErrorCode values) đọc từ utils/response.py.",
        )

    # ── TC-OAS-03 (http_status enum SSoT) ────────────────────────────────────
    def test_oas_03_http_status_enum_from_http_for_code(self):
        enum = set(
            self.spec["components"]["schemas"]["ErrorEnvelope"]["properties"][
                "http_status"
            ]["enum"]
        )
        self.assertEqual(
            enum,
            set(_HTTP_FOR_CODE.values()),
            "http_status.enum phải == set(_HTTP_FOR_CODE.values()).",
        )

    # ── TC-OAS-ENV (envelope shape khớp response.py:_ok/_err) ─────────────────
    def test_oas_env_success_envelope_shape(self):
        s = self.spec["components"]["schemas"]["SuccessEnvelope"]
        self.assertEqual(s["type"], "object")
        self.assertEqual(set(s["required"]), {"success", "data"})
        self.assertEqual(s["properties"]["success"]["enum"], [True])
        # data: {} (payload tuỳ endpoint — không ràng buộc shape ở core round).
        self.assertIn("data", s["properties"])

    def test_oas_env_error_envelope_required_and_optional_fields(self):
        e = self.spec["components"]["schemas"]["ErrorEnvelope"]
        self.assertEqual(set(e["required"]), {"success", "error", "code", "http_status"})
        self.assertEqual(e["properties"]["success"]["enum"], [False])
        props = e["properties"]
        # Required block.
        for f in ("success", "error", "code", "http_status"):
            self.assertIn(f, props, f"ErrorEnvelope thiếu field bắt buộc {f}.")
        # Optional notification-framework block (response.py:142-151).
        for f in (
            "fields",
            "message_code",
            "context",
            "action_hint",
            "severity",
            "title",
        ):
            self.assertIn(f, props, f"ErrorEnvelope thiếu optional field {f}.")
        self.assertEqual(
            set(props["severity"]["enum"]),
            {"error", "warning", "info", "success", "critical"},
        )

    def test_oas_security_scheme_cookie_session(self):
        schemes = self.spec["components"]["securitySchemes"]
        self.assertEqual(
            schemes["cookieSession"],
            {"type": "apiKey", "in": "cookie", "name": "sid"},
        )

    # ── TC-OAS-04 (method từ registry, KHÔNG từ tên hàm) ──────────────────────
    def _op(self, mod: str, fn: str, verb: str) -> dict:
        path = f"/api/method/assetcore.api.{mod}.{fn}"
        self.assertIn(path, self.spec["paths"], f"Thiếu path {path}.")
        item = self.spec["paths"][path]
        self.assertIn(verb, item, f"{path} thiếu verb {verb} (có: {list(item)}).")
        return item[verb]

    def test_oas_04_get_endpoints_sample(self):
        # ≥10 GET endpoint thật (bare @frappe.whitelist() — allowed list có GET).
        get_samples = [
            ("imm00", "get_asset"),
            ("imm00", "list_assets"),
            ("imm00", "get_asset_category"),
            ("imm00", "get_asset_kpi"),
            ("imm00", "get_asset_timeline"),
            ("imm12", "get_asset_incident_history"),
            ("imm00", "get_asset_label_data"),
            ("imm00", "list_assets_depreciation"),
            ("layout", "get_user_context"),
            ("layout", "ping_session"),
            ("imm00", "get_asset_downtime_metrics"),
        ]
        for mod, fn in get_samples:
            path = f"/api/method/assetcore.api.{mod}.{fn}"
            self.assertIn(path, self.spec["paths"], f"Thiếu path {path}.")
            self.assertIn(
                "get",
                self.spec["paths"][path],
                f"{path} phải là GET (có: {list(self.spec['paths'][path])}).",
            )

    def test_oas_04_post_endpoints_sample(self):
        # ≥10 POST endpoint thật (@frappe.whitelist(methods=["POST"])).
        post_samples = [
            ("imm00", "create_asset"),
            ("imm00", "create_asset_category"),
            ("imm12", "report_incident"),
            ("auth", "register_user"),
            ("auth", "check_account_status"),
            ("auth", "account_state"),
        ]
        for mod, fn in post_samples:
            path = f"/api/method/assetcore.api.{mod}.{fn}"
            self.assertIn(path, self.spec["paths"], f"Thiếu path {path}.")
            self.assertIn(
                "post",
                self.spec["paths"][path],
                f"{path} phải là POST (có: {list(self.spec['paths'][path])}).",
            )

    def test_oas_04_verb_derived_from_registry_not_name(self):
        """Verb đọc từ `allowed_http_methods_for_whitelisted_func`, KHÔNG suy từ tên.

        Bằng chứng: `get_user_context` allow_guest GET dù không bắt đầu 'get_'
        và `report_incident` bắt đầu 'report_' (không có 'post' trong tên) mà là POST.
        So path-verb với registry trực tiếp cho TỪNG sample.
        """
        import assetcore.api.imm12 as m12
        import assetcore.api.imm00 as m00

        reg = frappe.allowed_http_methods_for_whitelisted_func
        cases = [
            (m00.get_asset, "imm00", "get_asset", "get"),
            (m00.create_asset, "imm00", "create_asset", "post"),
            (m12.report_incident, "imm12", "report_incident", "post"),
        ]
        for fn, mod, name, verb in cases:
            allowed = reg.get(fn) or []
            derived = "post" if ("GET" not in allowed and "POST" in allowed) else "get"
            self.assertEqual(
                derived,
                verb,
                f"Registry-derived verb cho {name} = {derived}, expect {verb} "
                f"(allowed={allowed}).",
            )
            self.assertIn(verb, self.spec["paths"][f"/api/method/assetcore.api.{mod}.{name}"])

    def test_oas_04_method_distribution_both_present(self):
        """Toàn spec có cả GET và POST (sample ≥10 mỗi loại bằng đếm tổng)."""
        n_get = n_post = 0
        for item in self.spec["paths"].values():
            if "get" in item:
                n_get += 1
            if "post" in item:
                n_post += 1
        self.assertGreaterEqual(n_get, 10, "Phải có ≥10 GET endpoint.")
        self.assertGreaterEqual(n_post, 10, "Phải có ≥10 POST endpoint.")
        # Mỗi endpoint chính xác 1 verb (core round không multi-verb).
        for path, item in self.spec["paths"].items():
            verbs = [v for v in ("get", "post", "put", "delete") if v in item]
            self.assertEqual(len(verbs), 1, f"{path} phải có đúng 1 verb, có {verbs}.")

    # ── TC-OAS-05 (required + type map) ──────────────────────────────────────
    def test_oas_05_required_and_type_map_list_assets(self):
        op = self._op("imm00", "list_assets", "get")
        params = {p["name"]: p for p in op.get("parameters", [])}
        # page/page_size có default → required:false; type integer.
        self.assertIn("page", params)
        self.assertFalse(params["page"]["required"])
        self.assertEqual(params["page"]["schema"]["type"], "integer")
        self.assertFalse(params["page_size"]["required"])
        # lifecycle_status có default → required:false; type string.
        self.assertFalse(params["lifecycle_status"]["required"])
        self.assertEqual(params["lifecycle_status"]["schema"]["type"], "string")

    def test_oas_05_required_param_no_default(self):
        # get_asset(name: str) — name không default → required:true.
        op = self._op("imm00", "get_asset", "get")
        params = {p["name"]: p for p in op.get("parameters", [])}
        self.assertIn("name", params)
        self.assertTrue(params["name"]["required"], "name (không default) → required:true.")
        self.assertEqual(params["name"]["schema"]["type"], "string")

    def test_oas_05_type_map_int_float_string(self):
        """Type-map đọc cả annotation thật (imm00, no future-import) và chuỗi PEP563.

        list_assets (GET) GIỮ query parameters (regression A2). report_incident (POST)
        sau D4 body-bridge → type-map nằm trong requestBody.schema.properties (KHÔNG
        còn `parameters`); required ↔ mảng schema.required.
        """
        # imm00 = real type objects — GET giữ query parameters.
        op = self._op("imm00", "list_assets", "get")
        params = {p["name"]: p for p in op["parameters"]}
        self.assertEqual(params["page"]["schema"]["type"], "integer")  # int
        # imm12 = PEP563 string annotations — POST body-bridge (D4).
        op12 = self._op("imm12", "report_incident", "post")
        self.assertNotIn("parameters", op12, "POST có body → KHÔNG key parameters.")
        schema12 = op12["requestBody"]["content"]["application/json"]["schema"]
        props = schema12["properties"]
        req = set(schema12.get("required", []))
        # asset: 'str' (string) required; workaround_applied: 'int' (integer) default.
        self.assertEqual(props["asset"]["type"], "string")
        self.assertIn("asset", req)
        self.assertEqual(props["workaround_applied"]["type"], "integer")
        self.assertNotIn("workaround_applied", req)

    # ── TC-OAS-SEC (security) ────────────────────────────────────────────────
    def test_oas_sec_guest_endpoints_empty_security(self):
        guest = [
            ("auth", "register_user"),
            ("auth", "check_account_status"),
            ("auth", "account_state"),
            ("layout", "get_user_context"),
            ("layout", "ping_session"),
        ]
        for mod, fn in guest:
            path = f"/api/method/assetcore.api.{mod}.{fn}"
            item = self.spec["paths"][path]
            verb = next(iter(item))
            self.assertEqual(
                item[verb]["security"],
                [],
                f"{path} là allow_guest → security phải [] (rỗng).",
            )

    def test_oas_sec_normal_endpoint_cookie_session(self):
        op = self._op("imm00", "get_asset", "get")
        self.assertEqual(op["security"], [{"cookieSession": []}])

    # ── TC-OAS-OPID (operationId duy nhất + format) ──────────────────────────
    def test_oas_opid_unique_and_format(self):
        op_ids = []
        fmt = re.compile(r"^assetcore\.api\.[a-z0-9_]+\.[A-Za-z0-9_]+$")
        for path, item in self.spec["paths"].items():
            for verb, op in item.items():
                oid = op["operationId"]
                op_ids.append(oid)
                self.assertRegex(oid, fmt, f"operationId sai format: {oid}")
                self.assertEqual(
                    oid,
                    path.replace("/api/method/", ""),
                    "operationId phải == 'assetcore.api.<mod>.<fn>' (== path tail).",
                )
        self.assertEqual(
            len(set(op_ids)), len(op_ids), "operationId phải DUY NHẤT (không trùng)."
        )


class TestOasBodyBridgeD4(unittest.TestCase):
    """TC-OAS-13..16 — D4 body-bridge: POST có signature-param → requestBody (KHÔNG query).

    Bám ADR-IMM00-OPENAPI §D4. POST với param-chữ-ký → `requestBody`
    application/json object schema (properties + required no-default); GET giữ
    nguyên `parameters` (in=query); POST form_dict/no-arg → KHÔNG sinh requestBody.
    Đếm ĐỘNG bằng re-introspect (`_introspect_endpoints`) — KHÔNG hardcode 219/31/235.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()
        cls.endpoints = _introspect_endpoints()

    def _op(self, mod: str, fn: str, verb: str) -> dict:
        path = f"/api/method/assetcore.api.{mod}.{fn}"
        self.assertIn(path, self.spec["paths"], f"Thiếu path {path}.")
        item = self.spec["paths"][path]
        self.assertIn(verb, item, f"{path} thiếu verb {verb} (có: {list(item)}).")
        return item[verb]

    # ── TC-OAS-13 ────────────────────────────────────────────────────────────
    def test_oas_13_post_with_param_uses_request_body_not_parameters(self):
        """Mọi op verb=post CÓ signature-param → requestBody object non-empty, KHÔNG parameters.

        Đếm động (introspect lại sig) — assert == số POST-with-param thực tế.
        """
        post_with_param = [
            e for e in self.endpoints if e["verb"] == "post" and e["has_param"]
        ]
        # Sanity: phải có hàng trăm POST-with-param (≈219), KHÔNG hardcode.
        self.assertGreater(
            len(post_with_param),
            100,
            "Sanity: phải có hàng trăm POST-with-param (body-bridge target).",
        )
        checked = 0
        for e in post_with_param:
            op = self._op(e["mod"], e["fn_name"], "post")
            self.assertIn(
                "requestBody",
                op,
                f"{e['mod']}.{e['fn_name']} (POST có param) THIẾU requestBody.",
            )
            self.assertNotIn(
                "parameters",
                op,
                f"{e['mod']}.{e['fn_name']} (POST có body) KHÔNG được còn 'parameters'.",
            )
            rb = op["requestBody"]
            self.assertTrue(rb.get("required"), "requestBody.required phải True.")
            schema = rb["content"]["application/json"]["schema"]
            self.assertEqual(schema["type"], "object", "requestBody.schema.type=='object'.")
            self.assertTrue(
                schema.get("properties"),
                f"{e['fn_name']} requestBody.schema.properties phải non-empty.",
            )
            checked += 1
        # Mọi POST-with-param đều có requestBody (checked == số introspect).
        self.assertEqual(
            checked,
            len(post_with_param),
            "Số POST-with-param có requestBody phải == số introspect động.",
        )

    def test_oas_13_required_array_matches_no_default_params(self):
        """requestBody.required == ĐÚNG các param không-default (sorted), 1-prop/param."""
        post_with_param = [
            e for e in self.endpoints if e["verb"] == "post" and e["has_param"]
        ]
        for e in post_with_param:
            op = self._op(e["mod"], e["fn_name"], "post")
            schema = op["requestBody"]["content"]["application/json"]["schema"]
            # 1 property / named param.
            self.assertEqual(
                set(schema["properties"].keys()),
                {p.name for p in e["named"]},
                f"{e['fn_name']} properties phải khớp đúng tập param đặt tên.",
            )
            expected_required = sorted(
                p.name
                for p in e["named"]
                if p.default is inspect.Parameter.empty
            )
            self.assertEqual(
                sorted(schema.get("required", [])),
                expected_required,
                f"{e['fn_name']} required phải == param không-default (sorted).",
            )

    # ── TC-OAS-14 (report_incident) ──────────────────────────────────────────
    def test_oas_14_report_incident_request_body(self):
        op = self._op("imm12", "report_incident", "post")
        self.assertIn("requestBody", op)
        self.assertNotIn("parameters", op)
        schema = op["requestBody"]["content"]["application/json"]["schema"]
        self.assertEqual(schema["type"], "object")
        props = schema["properties"]
        # Đủ 12 param.
        for key in (
            "asset",
            "incident_type",
            "severity",
            "description",
            "fault_code",
            "workaround_applied",
            "clinical_impact",
            "patient_affected",
            "patient_impact_description",
            "immediate_action",
            "linked_repair_wo",
            "source",
        ):
            self.assertIn(key, props, f"report_incident requestBody thiếu prop {key}.")
        # Type-map: workaround_applied/patient_affected → integer; còn lại string.
        self.assertEqual(props["workaround_applied"]["type"], "integer")
        self.assertEqual(props["patient_affected"]["type"], "integer")
        for key in ("asset", "incident_type", "severity", "description", "source"):
            self.assertEqual(props[key]["type"], "string", f"{key} phải type string.")
        # required == 4 param không-default (sorted).
        self.assertEqual(
            sorted(schema["required"]),
            sorted(["asset", "incident_type", "severity", "description"]),
        )

    # ── TC-OAS-15 (GET regression — giữ query, không requestBody) ─────────────
    def test_oas_15_get_endpoints_keep_query_params(self):
        for mod, fn in (
            ("imm00", "list_assets"),
            ("imm00", "get_asset"),
            ("imm12", "get_asset_incident_history"),
        ):
            op = self._op(mod, fn, "get")
            self.assertIn("parameters", op, f"GET {fn} phải GIỮ 'parameters'.")
            self.assertNotIn(
                "requestBody", op, f"GET {fn} KHÔNG được sinh requestBody."
            )
            for p in op["parameters"]:
                self.assertEqual(p["in"], "query", f"GET {fn} param phải in=query.")

    def test_oas_15_list_assets_type_map_unchanged(self):
        """list_assets giữ y A2: page integer (default→required:false), lifecycle_status string."""
        op = self._op("imm00", "list_assets", "get")
        params = {p["name"]: p for p in op["parameters"]}
        self.assertEqual(params["page"]["schema"]["type"], "integer")
        self.assertFalse(params["page"]["required"])
        self.assertEqual(params["page_size"]["schema"]["type"], "integer")
        self.assertEqual(params["lifecycle_status"]["schema"]["type"], "string")
        # get_asset(name) — required:true, type string (A2 hình dạng cũ).
        opg = self._op("imm00", "get_asset", "get")
        pg = {p["name"]: p for p in opg["parameters"]}
        self.assertTrue(pg["name"]["required"])
        self.assertEqual(pg["name"]["schema"]["type"], "string")

    # ── TC-OAS-16 (POST form_dict/no-arg: D5 mapped→body, unmapped→fail-safe None) ──
    def test_oas_16_post_no_param_body_follows_d5_registry(self):
        """POST form_dict no-arg: CÓ entry registry → requestBody (D5); CHƯA map → None.

        D4 trước: mọi form_dict create_* → KHÔNG body. D5 nay: mapped (create_asset/
        create_supplier/create_asset_category…) sinh body từ DocType meta; chỉ unmapped
        (vd user.create_system_user core) giữ fail-safe None. Đếm động qua registry —
        KHÔNG hardcode. Invariant tách theo entry registry, KHÔNG còn 'mọi no-param→None'.
        """
        from assetcore.api import openapi_overrides as _ovr

        # 3 sample đã map → PHẢI có requestBody (D5).
        for mod, fn in (
            ("imm00", "create_asset"),
            ("imm00", "create_supplier"),
            ("imm00", "create_asset_category"),
        ):
            self.assertIn(
                f"{mod}.{fn}",
                _ovr.FORM_DICT_DOCTYPE_MAP,
                f"{mod}.{fn} phải có entry registry (sample D5).",
            )
            op = self._op(mod, fn, "post")
            self.assertIn(
                "requestBody",
                op,
                f"{fn} (mapped form_dict) PHẢI có requestBody round D5.",
            )
        # Đếm động: mọi POST-no-param theo registry — mapped→body, unmapped→None.
        post_no_param = [
            e for e in self.endpoints if e["verb"] == "post" and not e["has_param"]
        ]
        self.assertGreater(
            len(post_no_param), 0, "Sanity: phải có ≥1 POST form_dict no-arg (≈21)."
        )
        for e in post_no_param:
            op = self._op(e["mod"], e["fn_name"], "post")
            op_tail = f"{e['mod']}.{e['fn_name']}"
            if op_tail in _ovr.FORM_DICT_DOCTYPE_MAP:
                self.assertIn(
                    "requestBody",
                    op,
                    f"{op_tail} (mapped) PHẢI có requestBody (D5).",
                )
            else:
                self.assertNotIn(
                    "requestBody",
                    op,
                    f"{op_tail} (unmapped form_dict) KHÔNG được có requestBody (fail-safe).",
                )

    # ── Regression: tổng phân bố verb/body không vỡ A2 ───────────────────────
    def test_oas_d4_distribution_invariants(self):
        """len(paths)==introspect total; POST-with-body + POST-no-body + GET == total."""
        n_total = len(self.endpoints)
        self.assertEqual(
            len(self.spec["paths"]),
            n_total,
            "len(paths) phải == số endpoint introspect động (regression TC-OAS-01).",
        )
        post_with = sum(
            1 for e in self.endpoints if e["verb"] == "post" and e["has_param"]
        )
        post_no = sum(
            1 for e in self.endpoints if e["verb"] == "post" and not e["has_param"]
        )
        n_get = sum(1 for e in self.endpoints if e["verb"] == "get")
        self.assertEqual(
            post_with + post_no + n_get,
            n_total,
            "Tổng POST-with-param + POST-no-param + GET phải == total.",
        )
        # Mọi GET KHÔNG có requestBody (toàn spec).
        for path, item in self.spec["paths"].items():
            if "get" in item:
                self.assertNotIn(
                    "requestBody",
                    item["get"],
                    f"GET {path} KHÔNG được có requestBody.",
                )


# ── D5 form_dict body-bridge introspection (đếm ĐỘNG qua registry) ─────────────
def _form_dict_post_creates() -> list[dict]:
    """Mọi POST create_* đọc form_dict (no signature-param) introspect-được.

    → [{op_tail, mod, fn_name}]. op_tail = '<module>.<fn>' (key registry). Đếm động —
    KHÔNG hardcode 21. Dùng làm domain cho TC-OAS-06 (mapped) + COVERAGE (unmapped).
    """
    out: list[dict] = []
    for e in _introspect_endpoints():
        if (
            e["verb"] == "post"
            and not e["has_param"]
            and e["fn_name"].startswith("create_")
        ):
            out.append(
                {
                    "op_tail": f"{e['mod']}.{e['fn_name']}",
                    "mod": e["mod"],
                    "fn_name": e["fn_name"],
                }
            )
    return out


class TestOasDoctypeMapRegistry(unittest.TestCase):
    """TC-OAS-DOCTYPE-MAP — registry `openapi_overrides` import-được THUẦN (no DB module-level)."""

    def test_registry_imports_without_db_at_module_level(self):
        """Import KHÔNG exception kể cả khi `frappe.get_meta` raise (no DB ở module-level).

        Bằng chứng module-level không gọi meta: monkeypatch get_meta→raise rồi reload module
        → import VẪN pass (chỉ generate_spec mới chạm meta).
        """
        with mock.patch.object(
            frappe, "get_meta", side_effect=RuntimeError("DB touched at import!")
        ):
            mod = importlib.reload(openapi_overrides)
        self.assertTrue(
            mod.FORM_DICT_DOCTYPE_MAP, "FORM_DICT_DOCTYPE_MAP phải non-empty sau import."
        )
        self.assertIsInstance(mod.FORM_DICT_DOCTYPE_MAP, dict)

    def test_registry_values_are_real_doctypes(self):
        """Mọi value trong FORM_DICT_DOCTYPE_MAP là DocType tồn tại (skip-if-not-migrated)."""
        for op_tail, dt in openapi_overrides.FORM_DICT_DOCTYPE_MAP.items():
            if not frappe.db.exists("DocType", dt):
                self.skipTest(f"DocType {dt!r} chưa migrate (entry {op_tail}).")
            self.assertTrue(
                frappe.db.exists("DocType", dt),
                f"{op_tail} → {dt!r} KHÔNG phải DocType hợp lệ.",
            )

    def test_registry_keys_are_form_dict_post_creates(self):
        """Mọi key registry PHẢI là POST create_* form_dict introspect-được (no orphan map)."""
        introspected = {e["op_tail"] for e in _form_dict_post_creates()}
        for op_tail in openapi_overrides.FORM_DICT_DOCTYPE_MAP:
            self.assertIn(
                op_tail,
                introspected,
                f"Registry key {op_tail!r} KHÔNG khớp POST create_* form_dict nào "
                "(orphan map — sửa registry hoặc endpoint).",
            )

    def test_registry_is_pure_no_module_side_effect(self):
        """Registry KHÔNG gọi DB ở mức module: re-import với get_meta+db.exists raise vẫn pass."""
        with mock.patch.object(
            frappe, "get_meta", side_effect=AssertionError("no meta at import")
        ), mock.patch.object(
            frappe.db, "exists", side_effect=AssertionError("no db at import")
        ):
            mod = importlib.reload(openapi_overrides)
        self.assertIsInstance(mod.FRAPPE_FIELDTYPE_JSON_MAP, dict)


class TestOasD5FormDictBodyBridge(unittest.TestCase):
    """TC-OAS-06 — form_dict create_* CÓ entry registry → requestBody object NON-EMPTY."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()
        cls.form_creates = _form_dict_post_creates()

    def _op(self, op_tail: str) -> dict:
        mod, fn = op_tail.split(".", 1)
        path = f"/api/method/assetcore.api.{mod}.{fn}"
        self.assertIn(path, self.spec["paths"], f"Thiếu path {path}.")
        item = self.spec["paths"][path]
        self.assertIn("post", item, f"{path} thiếu verb post (có: {list(item)}).")
        return item["post"]

    def test_oas_06_mapped_form_dict_creates_have_non_empty_body(self):
        """Mọi op-tail ∈ FORM_DICT_DOCTYPE_MAP ∩ introspected POST → requestBody non-empty.

        Đếm số endpoint-có-body-bridge ĐỘNG qua registry; assert == |map ∩ introspected|
        (KHÔNG hardcode). Mỗi requestBody = object schema, properties NON-EMPTY, KHÔNG rỗng.
        """
        introspected = {e["op_tail"] for e in self.form_creates}
        mapped_and_introspected = sorted(
            t for t in openapi_overrides.FORM_DICT_DOCTYPE_MAP if t in introspected
        )
        self.assertGreater(
            len(mapped_and_introspected),
            10,
            "Sanity: phải có >10 form_dict create_* được map (registry hiện ~20).",
        )
        bridged = 0
        for op_tail in mapped_and_introspected:
            dt = openapi_overrides.FORM_DICT_DOCTYPE_MAP[op_tail]
            if not frappe.db.exists("DocType", dt):
                self.skipTest(f"DocType {dt!r} chưa migrate.")
            op = self._op(op_tail)
            self.assertIn(
                "requestBody",
                op,
                f"{op_tail} (mapped form_dict) PHẢI có requestBody (D5).",
            )
            self.assertNotIn(
                "parameters", op, f"{op_tail} có body → KHÔNG còn 'parameters'."
            )
            rb = op["requestBody"]
            self.assertTrue(rb.get("required"), f"{op_tail} requestBody.required phải True.")
            schema = rb["content"]["application/json"]["schema"]
            self.assertEqual(
                schema["type"], "object", f"{op_tail} schema.type phải 'object'."
            )
            self.assertTrue(
                schema.get("properties"),
                f"{op_tail} requestBody.schema.properties phải NON-EMPTY (không rỗng D4).",
            )
            bridged += 1
        self.assertEqual(
            bridged,
            len(mapped_and_introspected),
            "Số endpoint áp body-bridge ĐỘNG phải == |map ∩ introspected POST form_dict|.",
        )

    def test_oas_06_mutation_remove_one_entry_drops_count_by_one(self):
        """Mutation: xoá 1 entry registry → số endpoint-có-body-bridge giảm ĐÚNG 1 (test có răng)."""
        introspected = {e["op_tail"] for e in self.form_creates}

        def _count_bridged(spec) -> int:
            n = 0
            for op_tail in openapi_overrides.FORM_DICT_DOCTYPE_MAP:
                if op_tail not in introspected:
                    continue
                mod, fn = op_tail.split(".", 1)
                op = spec["paths"].get(f"/api/method/assetcore.api.{mod}.{fn}", {}).get(
                    "post", {}
                )
                if "requestBody" in op:
                    n += 1
            return n

        baseline = _count_bridged(self.spec)
        victim = "imm00.create_asset"
        self.assertIn(victim, openapi_overrides.FORM_DICT_DOCTYPE_MAP)
        saved = dict(openapi_overrides.FORM_DICT_DOCTYPE_MAP)
        try:
            del openapi_overrides.FORM_DICT_DOCTYPE_MAP[victim]
            mutated = openapi.generate_spec()
            after = _count_bridged(mutated)
            # victim KHÔNG còn body (fail-safe D4).
            v_op = mutated["paths"][
                "/api/method/assetcore.api.imm00.create_asset"
            ]["post"]
            self.assertNotIn(
                "requestBody",
                v_op,
                "Xoá entry registry → endpoint quay về D4 (KHÔNG requestBody).",
            )
            self.assertEqual(
                after,
                baseline - 1,
                "Xoá 1 entry → số endpoint-có-body-bridge giảm đúng 1.",
            )
        finally:
            openapi_overrides.FORM_DICT_DOCTYPE_MAP.clear()
            openapi_overrides.FORM_DICT_DOCTYPE_MAP.update(saved)


class TestOasD5CreateAssetSchema(unittest.TestCase):
    """TC-OAS-07 — create_asset.requestBody.required == SSoT (no autoset) + properties shape."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def _create_asset_schema(self) -> dict:
        op = self.spec["paths"]["/api/method/assetcore.api.imm00.create_asset"]["post"]
        self.assertIn("requestBody", op, "create_asset PHẢI có requestBody (D5).")
        return op["requestBody"]["content"]["application/json"]["schema"]

    def test_oas_07_create_asset_required_is_ssot_no_autoset(self):
        """required == sorted(['asset_category','asset_name']) — KHÔNG naming_series/status/lifecycle."""
        if not frappe.db.exists("DocType", "AC Asset"):
            self.skipTest("AC Asset chưa migrate.")
        schema = self._create_asset_schema()
        self.assertEqual(
            sorted(schema.get("required", [])),
            sorted(["asset_category", "asset_name"]),
            "create_asset.required phải == SSoT _ASSET_REQD_LABELS_VI.",
        )
        for autoset in ("naming_series", "status", "lifecycle_status"):
            self.assertNotIn(
                autoset,
                schema.get("required", []),
                f"required KHÔNG được chứa API-autoset field {autoset!r}.",
            )

    def test_oas_07_required_matches_imm00_ssot_directly(self):
        """Cross-ref: required khớp ĐÚNG keys của imm00._ASSET_REQD_LABELS_VI (SSoT thật)."""
        if not frappe.db.exists("DocType", "AC Asset"):
            self.skipTest("AC Asset chưa migrate.")
        from assetcore.api.imm00 import _ASSET_REQD_LABELS_VI

        schema = self._create_asset_schema()
        self.assertEqual(
            sorted(schema.get("required", [])),
            sorted(_ASSET_REQD_LABELS_VI.keys()),
            "create_asset.required phải == keys(_ASSET_REQD_LABELS_VI) (SSoT).",
        )

    def test_oas_07_required_props_present_as_string(self):
        """asset_name + asset_category có trong properties với type string."""
        if not frappe.db.exists("DocType", "AC Asset"):
            self.skipTest("AC Asset chưa migrate.")
        props = self._create_asset_schema()["properties"]
        for f in ("asset_name", "asset_category"):
            self.assertIn(f, props, f"properties thiếu {f}.")
            self.assertEqual(props[f]["type"], "string", f"{f} phải type string.")

    def test_oas_07_optional_field_in_properties_not_required(self):
        """≥1 field optional (location/supplier) vào properties NHƯNG KHÔNG vào required."""
        if not frappe.db.exists("DocType", "AC Asset"):
            self.skipTest("AC Asset chưa migrate.")
        schema = self._create_asset_schema()
        props = schema["properties"]
        required = set(schema.get("required", []))
        optional_present = [f for f in ("location", "supplier") if f in props]
        self.assertTrue(
            optional_present,
            "Phải có ≥1 optional Link field (location/supplier) trong properties.",
        )
        for f in optional_present:
            self.assertNotIn(
                f, required, f"Optional field {f!r} KHÔNG được vào required."
            )

    def test_oas_07_hidden_field_excluded(self):
        """Field hidden (qr_token) KHÔNG vào properties."""
        if not frappe.db.exists("DocType", "AC Asset"):
            self.skipTest("AC Asset chưa migrate.")
        props = self._create_asset_schema()["properties"]
        self.assertNotIn("qr_token", props, "Field hidden qr_token KHÔNG được vào body.")

    def test_oas_07_create_supplier_required_minimum(self):
        """create_supplier.required tối thiểu gồm supplier_name+supplier_group+vendor_type (trừ naming_series)."""
        if not frappe.db.exists("DocType", "AC Supplier"):
            self.skipTest("AC Supplier chưa migrate.")
        op = self.spec["paths"][
            "/api/method/assetcore.api.imm00.create_supplier"
        ]["post"]
        self.assertIn("requestBody", op, "create_supplier PHẢI có requestBody (D5).")
        schema = op["requestBody"]["content"]["application/json"]["schema"]
        required = set(schema.get("required", []))
        for f in ("supplier_name", "supplier_group", "vendor_type"):
            self.assertIn(f, required, f"create_supplier.required thiếu {f}.")
        self.assertNotIn(
            "naming_series", required, "naming_series KHÔNG vào required (autoset)."
        )


class TestOasD5Coverage(unittest.TestCase):
    """TC-OAS-COVERAGE — liệt kê form_dict create_* CHƯA map; assert fail-safe (KHÔNG body sai)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()
        cls.form_creates = _form_dict_post_creates()

    def test_coverage_unmapped_creates_are_fail_safe(self):
        """form_dict create_* KHÔNG có entry registry → requestBody KHÔNG sinh (None) — fail-safe.

        KHÔNG fail cứng nếu coverage <100%, NHƯNG fail nếu unmapped SINH body sai. In danh
        sách unmapped để theo dõi coverage.
        """
        mapped = set(openapi_overrides.FORM_DICT_DOCTYPE_MAP)
        unmapped = sorted(
            e["op_tail"] for e in self.form_creates if e["op_tail"] not in mapped
        )
        # Theo dõi coverage (in ra, KHÔNG fail cứng).
        total = len(self.form_creates)
        covered = total - len(unmapped)
        print(
            f"\n[OAS-COVERAGE] form_dict create_* mapped {covered}/{total}; "
            f"unmapped={unmapped}"
        )
        # FAIL-SAFE invariant: mọi unmapped PHẢI KHÔNG có requestBody (giữ D4).
        for op_tail in unmapped:
            mod, fn = op_tail.split(".", 1)
            op = self.spec["paths"][
                f"/api/method/assetcore.api.{mod}.{fn}"
            ]["post"]
            self.assertNotIn(
                "requestBody",
                op,
                f"unmapped {op_tail} KHÔNG được sinh requestBody (fail-safe D4).",
            )


class TestOasEnvAdd(unittest.TestCase):
    """TC-OAS-ENV-ADD — chống hardcode enum: thêm 1 ErrorCode → code.enum tăng đúng 1."""

    def test_env_add_extra_error_code_grows_enum_by_one(self):
        baseline = set(
            openapi.generate_spec()["components"]["schemas"]["ErrorEnvelope"][
                "properties"
            ]["code"]["enum"]
        )
        sentinel = "ZZ_FAKE_OAS_TEST_CODE"
        self.assertNotIn(sentinel, baseline)
        setattr(ErrorCode, sentinel, sentinel)
        try:
            after = set(
                openapi.generate_spec()["components"]["schemas"]["ErrorEnvelope"][
                    "properties"
                ]["code"]["enum"]
            )
        finally:
            delattr(ErrorCode, sentinel)
        self.assertEqual(
            after - baseline,
            {sentinel},
            "Thêm 1 ErrorCode → enum phải tăng đúng 1 (generator đọc động, KHÔNG hardcode).",
        )


# ── D6 enrich (Phase A6) — helpers + invariants ────────────────────────────────
# DẪN XUẤT ĐỘNG từ SSoT `openapi_overrides.D6_MODULES` (no magic-tuple drift). D6-IMM09-
# ENRICH: tập module enrich tăng {00,04,12} → {00,04,09,12} khi imm09 vào D6_MODULES —
# test bám SSoT nên KHÔNG cần sửa danh sách tay mỗi lần mở rộng module enrich.
_D6_MODULES = set(openapi_overrides.D6_MODULES)

# Regex cap-token kiểu 'corrective.create' / 'calibration.create' (leak quyền nội bộ).
# CHỈ áp cho ERROR message (E4) — KHÔNG áp request-example field-enum (E2).
_CAP_TOKEN_RE = re.compile(r"[a-z]+\.[a-z]+")
# Từ EN trạng thái cấm trong error message (E4).
_EN_STATUS_RE = re.compile(
    r"\b(Active|Out of Service|Under Maintenance|Decommissioned)\b"
)
# Raw định-danh-chéo cấm trong error message (E4): qr_token literal / email / serial.
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _d6_enriched_ops(spec) -> list[dict]:
    """Mọi operation thuộc imm00/04/12 có entry OPERATION_META → [{op_tail, verb, op}]."""
    out: list[dict] = []
    for op_tail in openapi_overrides.OPERATION_META:
        mod = op_tail.split(".", 1)[0]
        if mod not in _D6_MODULES:
            continue
        path = f"/api/method/assetcore.api.{op_tail}"
        item = spec["paths"].get(path)
        if not item:
            continue
        for verb, op in item.items():
            out.append({"op_tail": op_tail, "verb": verb, "op": op})
    return out


class TestOasD6Enrich(unittest.TestCase):
    """TC-OAS-D6-01..06 — enrich imm00/04/12 DẪN XUẤT từ OPERATION_META (registry).

    Bám ADR-IMM00-OPENAPI §D6 (E0-E6). KHÔNG đụng test D5 (`test_oas_06_*`/`test_oas_07_*`).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def _op(self, op_tail: str, verb: str) -> dict:
        path = f"/api/method/assetcore.api.{op_tail}"
        self.assertIn(path, self.spec["paths"], f"Thiếu path {path}.")
        item = self.spec["paths"][path]
        self.assertIn(verb, item, f"{path} thiếu verb {verb} (có: {list(item)}).")
        return item[verb]

    # ── TC-OAS-D6-01 — mọi op imm00/04/12 có summary>0 + description>0 ─────────
    def test_oas_06e_all_three_modules_have_summary_description(self):
        """MỌI op thuộc imm00/04/12 có len(summary)>0 và len(description)>0.

        Đếm động qua _introspect_endpoints lọc mod ∈ {imm00,imm04,imm12}; module khác
        KHÔNG ép enrich (giữ default docstring).
        """
        targets = [
            e for e in _introspect_endpoints() if e["mod"] in _D6_MODULES
        ]
        self.assertGreater(
            len(targets), 50, "Sanity: imm00/04/12 phải có hàng chục endpoint."
        )
        offenders: list[str] = []
        for e in targets:
            op = self._op(f"{e['mod']}.{e['fn_name']}", e["verb"])
            if not op.get("summary"):
                offenders.append(f"{e['mod']}.{e['fn_name']} (summary rỗng)")
            if not op.get("description"):
                offenders.append(f"{e['mod']}.{e['fn_name']} (description rỗng)")
            # KHÔNG còn lấy default = operationId.
            self.assertNotEqual(
                op.get("summary"),
                op["operationId"],
                f"{e['mod']}.{e['fn_name']} summary KHÔNG được == operationId.",
            )
        self.assertEqual(
            offenders,
            [],
            "Op imm00/04/12 còn summary/description rỗng:\n  " + "\n  ".join(offenders),
        )

    def test_oas_06e_other_module_not_force_enriched(self):
        """Module ngoài 3 trọng yếu KHÔNG bị ép enrich (không có entry → giữ default)."""
        # auth/layout không nằm trong OPERATION_META → KHÔNG có examples nhúng.
        for op_tail, verb in (("auth.register_user", "post"), ("layout.ping_session", "get")):
            self.assertNotIn(
                op_tail,
                openapi_overrides.OPERATION_META,
                f"{op_tail} KHÔNG được nằm trong OPERATION_META (chỉ enrich 3 module).",
            )

    # ── TC-OAS-D6-02 — mutation: enrich là DẪN XUẤT từ registry (test có răng) ──
    def test_oas_06e_mutation_add_entry_reflects_remove_reverts(self):
        """Thêm 1 entry OPERATION_META → spec op đó đổi summary/description; xoá → default."""
        victim = "imm12.get_chronic_failures"  # op không-enrich sẵn (GET, default docstring).
        self.assertNotIn(
            victim,
            openapi_overrides.OPERATION_META,
            "Chọn victim CHƯA enrich để chứng minh +entry có hiệu lực.",
        )
        default_op = self.spec["paths"][
            f"/api/method/assetcore.api.{victim}"
        ]["get"]
        default_summary = default_op.get("summary")
        sentinel_summary = "ZZ_SENTINEL_D6_SUMMARY"
        sentinel_desc = "ZZ_SENTINEL_D6_DESC mô tả nghiệp vụ enrich."
        saved = dict(openapi_overrides.OPERATION_META)
        try:
            openapi_overrides.OPERATION_META[victim] = {
                "summary": sentinel_summary,
                "description": sentinel_desc,
            }
            mutated = openapi.generate_spec()
            m_op = mutated["paths"][f"/api/method/assetcore.api.{victim}"]["get"]
            self.assertEqual(m_op["summary"], sentinel_summary, "+entry → summary đổi ngay.")
            self.assertEqual(m_op["description"], sentinel_desc, "+entry → description đổi ngay.")
        finally:
            openapi_overrides.OPERATION_META.clear()
            openapi_overrides.OPERATION_META.update(saved)
        reverted = openapi.generate_spec()["paths"][
            f"/api/method/assetcore.api.{victim}"
        ]["get"]
        self.assertEqual(
            reverted.get("summary"),
            default_summary,
            "Xoá entry → op quay về default (fail-safe, KHÔNG hardcode).",
        )

    # ── TC-OAS-D6-03 — request example khớp schema (POST) ─────────────────────
    def test_oas_06e_request_example_matches_schema(self):
        """Mỗi POST enriched: set(example.keys()) ⊆ properties + schema.required ⊆ example."""
        enriched_posts = [
            d for d in _d6_enriched_ops(self.spec) if d["verb"] == "post"
        ]
        self.assertGreater(len(enriched_posts), 0, "Sanity: phải có POST enriched.")
        for d in enriched_posts:
            op = d["op"]
            meta = openapi_overrides.OPERATION_META[d["op_tail"]]
            if "request" not in meta.get("examples", {}):
                continue  # POST không khai request example (vẫn hợp lệ nếu có summary/desc).
            self.assertIn(
                "requestBody", op, f"{d['op_tail']} (POST enriched) PHẢI có requestBody."
            )
            content = op["requestBody"]["content"]["application/json"]
            self.assertIn(
                "example", content, f"{d['op_tail']} requestBody thiếu example."
            )
            example = content["example"]
            schema = content["schema"]
            props = set(schema.get("properties", {}).keys())
            self.assertTrue(
                set(example.keys()) <= props,
                f"{d['op_tail']} example keys {set(example.keys())} ⊄ properties {props}.",
            )
            for req in schema.get("required", []):
                self.assertIn(
                    req,
                    example,
                    f"{d['op_tail']} schema.required '{req}' THIẾU trong example.",
                )

    def test_oas_06e_report_incident_example_shape(self):
        """report_incident example có asset/description/incident_type/severity (E2 canonical)."""
        self.assertIn("imm12.report_incident", openapi_overrides.OPERATION_META)
        op = self._op("imm12.report_incident", "post")
        example = op["requestBody"]["content"]["application/json"]["example"]
        for k in ("asset", "description", "incident_type", "severity"):
            self.assertIn(k, example, f"report_incident example thiếu '{k}'.")

    # ── TC-OAS-D6-04 — response 200 = SuccessEnvelope SSoT + example ──────────
    def test_oas_06e_response_200_success_envelope_with_example(self):
        """Mỗi op enriched: responses['200'] ref SuccessEnvelope + example success:true + data."""
        for d in _d6_enriched_ops(self.spec):
            op = d["op"]
            resp = op["responses"]["200"]
            content = resp["content"]["application/json"]
            self.assertEqual(
                content["schema"]["$ref"],
                "#/components/schemas/SuccessEnvelope",
                f"{d['op_tail']} response 200 PHẢI vẫn ref SuccessEnvelope (KHÔNG khai lại shape).",
            )
            self.assertIn("examples", content, f"{d['op_tail']} response 200 thiếu examples.")
            value = content["examples"]["success"]["value"]
            self.assertIs(value["success"], True, f"{d['op_tail']} example.success phải True.")
            self.assertIn("data", value, f"{d['op_tail']} example success thiếu 'data'.")

    def test_oas_06e_success_envelope_shape_unchanged(self):
        """SSoT SuccessEnvelope KHÔNG bị enrich đổi shape (vẫn data:{} generic)."""
        s = self.spec["components"]["schemas"]["SuccessEnvelope"]
        self.assertEqual(set(s["required"]), {"success", "data"})
        self.assertEqual(s["properties"]["data"], {}, "data vẫn generic {} (KHÔNG schema thứ 2).")

    # ── TC-OAS-D6-05 — error-responses VI + ∈ ErrorCode ──────────────────────
    def test_oas_06e_error_responses_codes_in_errorcode_enum(self):
        """Mỗi op enriched khai mã lỗi: code ∈ ErrorCode + status-key == _HTTP_FOR_CODE[code]."""
        valid_codes = _error_code_values()
        for d in _d6_enriched_ops(self.spec):
            op = d["op"]
            meta = openapi_overrides.OPERATION_META[d["op_tail"]]
            errors = meta.get("examples", {}).get("errors", {})
            if not errors:
                continue
            for code in errors:
                self.assertIn(
                    code,
                    valid_codes,
                    f"{d['op_tail']} error code '{code}' KHÔNG ∈ ErrorCode SSoT.",
                )
                status_key = str(_HTTP_FOR_CODE[code])
                self.assertIn(
                    status_key,
                    op["responses"],
                    f"{d['op_tail']} thiếu response key '{status_key}' cho code {code}.",
                )
                resp = op["responses"][status_key]
                self.assertEqual(
                    resp["content"]["application/json"]["schema"]["$ref"],
                    "#/components/schemas/ErrorEnvelope",
                    f"{d['op_tail']} response {status_key} PHẢI ref ErrorEnvelope.",
                )
                ex = resp["content"]["application/json"]["example"]
                self.assertIs(ex["success"], False)
                self.assertEqual(ex["code"], code)
                self.assertEqual(ex["http_status"], _HTTP_FOR_CODE[code])

    def test_oas_06e_error_messages_vi_clean_no_leak(self):
        """Mọi error example message của 3 module: no cap-token, no EN-status, no email/serial."""
        offenders: list[str] = []
        for d in _d6_enriched_ops(self.spec):
            meta = openapi_overrides.OPERATION_META[d["op_tail"]]
            errors = meta.get("examples", {}).get("errors", {})
            for code, msg in errors.items():
                if _CAP_TOKEN_RE.search(msg):
                    offenders.append(f"{d['op_tail']}/{code}: cap-token leak → {msg!r}")
                if _EN_STATUS_RE.search(msg):
                    offenders.append(f"{d['op_tail']}/{code}: EN-status leak → {msg!r}")
                if _EMAIL_RE.search(msg):
                    offenders.append(f"{d['op_tail']}/{code}: email/định-danh leak → {msg!r}")
                if "qr_token" in msg:
                    offenders.append(f"{d['op_tail']}/{code}: raw qr_token leak → {msg!r}")
        self.assertEqual(
            offenders,
            [],
            "Error message D6 leak (cap-token/EN-status/email/qr_token):\n  "
            + "\n  ".join(offenders),
        )

    # ── TC-OAS-D6-06 — registry import THUẦN (no DB module-level) ─────────────
    def test_oas_06e_operation_meta_imports_pure_no_db(self):
        """monkeypatch frappe.get_meta raise → import OPERATION_META vẫn pass (giữ D5)."""
        with mock.patch.object(
            frappe, "get_meta", side_effect=RuntimeError("DB touched at import!")
        ):
            mod = importlib.reload(openapi_overrides)
        self.assertTrue(
            mod.OPERATION_META, "OPERATION_META phải non-empty sau import THUẦN."
        )
        self.assertIsInstance(mod.OPERATION_META, dict)

    def test_oas_06e_operation_meta_keys_are_real_endpoints(self):
        """Mọi key OPERATION_META là endpoint introspect-được của module ∈ D6_MODULES (no orphan)."""
        introspected = {f"{e['mod']}.{e['fn_name']}" for e in _introspect_endpoints()}
        for op_tail in openapi_overrides.OPERATION_META:
            self.assertIn(
                op_tail.split(".", 1)[0],
                _D6_MODULES,
                f"OPERATION_META key {op_tail!r} ngoài tập module enrich D6_MODULES.",
            )
            self.assertIn(
                op_tail,
                introspected,
                f"OPERATION_META key {op_tail!r} KHÔNG khớp endpoint introspect-được (orphan).",
            )

