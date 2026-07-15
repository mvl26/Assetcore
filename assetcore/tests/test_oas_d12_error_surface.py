"""TC-OAS-D12-01..06 — BASELINE-ERR-SURFACE: typed 401/403 cho MỌI op authed.

Bám ADR-IMM00-OPENAPI §D12-BASELINE-ERR. Test viết TRƯỚC implement (TDD RED→GREEN).

Vấn đề: 325 op non-enriched chỉ có `default` (opaque ErrorEnvelope) — KHÔNG có
response status-coded 401/403, integrator/Swagger UI không biết op cần phiên/quyền gì.
161 op enriched (imm00/04/12) đã có status-coded error (curated D6) nhưng phần còn lại
trống.

Fix D12: với MỌI op AUTHED (security==[{cookieSession:[]}]) THÊM baseline response
`401`(UNAUTHORIZED) + `403`(FORBIDDEN) — schema $ref ErrorEnvelope, description VI DẪN
XUẤT từ SSoT (constants BE). MERGE bằng setdefault (key chưa tồn tại) → enrich D6 chạy
SAU vẫn override/bồi `examples` cho 161 op curated mà KHÔNG bị baseline đè. Op GUEST
(security==[]) KHÔNG có 401 (không cần phiên) — chỉ 200+default. Bất biến guest_count==5.

`x-assetcore-stats` thêm `error_responses_typed_count` = số op có ≥1 response status 4xx/5xx
(đếm động). total/get/post/guest/enriched/json_param/cap_set_version KHÔNG đổi.

Run: bench --site miyano run-tests --module assetcore.tests.test_oas_d12_error_surface
"""
from __future__ import annotations

import re
import unittest

import frappe  # noqa: F401 — môi trường Frappe

from assetcore.api import openapi
from assetcore.api import openapi_overrides as _ovr
from assetcore.utils.response import ErrorCode, _HTTP_FOR_CODE

# Bề mặt invariant baseline (D2/D11/D9/D6) — KHÔNG đổi sau D12.
# 2026-06-11 re-baseline 486→487 / get 236→237: working tree thêm endpoint thứ 487
# `imm00.print_asset_labels_pdf` (GET, whitelist mới từ IMM-00 print/rotate caps đã commit).
# 2026-06-12 re-baseline 487→488 / get 237→238: working tree thêm endpoint thứ 488
# `imm00.get_asset_action_meta` (GET, panel META NẠC cho 3 màn tạo WO — KHÔNG-parse-param,
# 6-key NẠC, RBAC/vendor-isolation intact; NĐ98 data-min). Delta = đúng 1 GET, POST giữ 250.
# 2026-06-27 VERB-PARITY CLOSURE re-baseline get 238→235 / post 250→253 (total GIỮ 488): 3 write-action
# bare @whitelist (submit_pm_result @imm08.py:54, create_calibration @imm11.py:89, submit_calibration
# @imm11.py:114) siết @frappe.whitelist(methods=["POST"]) ⇒ runtime _http_method_for GET→POST cho 3 ⇒
# get_count −3, post_count +3 (verb-flip observable trong x-assetcore-stats — Hyrum). 0 endpoint thêm/bớt.
# 2026-06-27 R34 ADD-MEASUREMENT re-baseline get 235→234 / post 253→254 (total GIỮ 488): write-action thứ-4
# bare @whitelist (add_measurement @imm11.py:120 — verb-parity gap R33 BỎ SÓT) siết
# @frappe.whitelist(methods=["POST"]) ⇒ runtime _http_method_for GET→POST cho 1 ⇒ get_count −1, post_count
# +1. RE-VERIFY @source (generate_spec SAU flip): get=234 post=254 (KHÔNG tin số học — đếm @source). 0 endpoint thêm/bớt.
# 2026-06-28 R35 PM-DISPATCH re-baseline get 234→233 / post 254→255 (total GIỮ 488): write-action thứ-5
# bare @whitelist (assign_technician @imm08.py:46 — verb-parity gap R33 BỎ SÓT, sibling add_measurement) siết
# @frappe.whitelist(methods=["POST"]) ⇒ runtime _http_method_for GET→POST cho 1 ⇒ get_count −1, post_count
# +1. RE-VERIFY @source (generate_spec SAU flip): get=233 post=255 (KHÔNG tin số học — đếm @source). 0 endpoint thêm/bớt.
# 2026-06-28 R36 PM→CM ESCALATION re-baseline get 233→232 / post 255→256 (total GIỮ 488): write-action thứ-6
# bare @whitelist (report_major_failure @imm08.py:74 — verb-parity gap còn sót + SIGNATURE-FIX DROP
# failed_item_indexes) siết @frappe.whitelist(methods=["POST"]) ⇒ runtime _http_method_for GET→POST cho 1 ⇒
# get_count −1, post_count +1. RE-VERIFY @source (generate_spec SAU flip): get=232 post=256 (KHÔNG tin số học — đếm @source). 0 endpoint thêm/bớt.
# 2026-07-01 RE-BASELINE-FIX total 488→492 / get 232→236 (POST 256 GIỮ): commit 979d736 là RE-BASELINE
# SÓT — commit-message ghi "path count 488→489" (thêm user.list_assignable_users, GET) và cập nhật
# D15/D17 phần verb-split NHƯNG _BASELINE_TOTAL/get + D10 path-count GIỮ 488 ⇒ D10/D12/D15/D17 RED âm
# thầm từ 979d736 (off-by-1, endpoint #489 chưa vào total). Nay HỢP NHẤT drift + 3 endpoint web GET mới
# working-tree: imm00.get_depreciation_by_category (KPI khấu hao gom theo danh mục), imm14.list_decommissions
# (list biên bản giải nhiệm, RBAC decommission.read), imm15.get_cycle_count (chi tiết phiếu kiểm kê chu kỳ).
# ⇒ total 489+3=492 / get 233+3=236 (cả 4 đều GET) / POST 256 GIỮ. RE-VERIFY @source generate_spec:
# total=492 get=236 post=256 guest=5 json_param=64. ⚠️ DESIGN-DEBT cho [BA]/lead: cùng 1 invariant
# (endpoint surface) hardcode magic-number ở ≥4 file (D10/D12/D15/D17) → sửa phải lockstep, 979d736 sót
# 1 file là RED âm thầm. Đề xuất: gom baseline về 1 SSoT module dùng chung (xem open-issues).
# 2026-07-09 CR-14/CR-15/CR-17 PHOTO-ATTACH: total 492→495 / post 256→259 (typed 492→495 == total): +3
#   multipart POST @whitelist đối xứng imm08.attach_pm_checklist_photo + imm09.attach_repair_checklist_photo
#   + imm12.attach_incident_photo (đính ảnh bằng chứng NĐ98). get/guest/json_param GIỮ. RE-VERIFY @source
#   generate_spec (QA vòng 3: baseline trước sót imm09 → 494 vs actual 495, đã sửa).
# 2026-07-10 RCA-CTA (GATE-8/BR-12-20/22): total 495→497 / post 259→261: +2 POST @whitelist
#   imm12.start_rca + imm12.cancel_rca (server-driven RCA transition). get/guest/json_param GIỮ
#   (params str, không parse_json). typed 497 == total. RE-VERIFY @source generate_spec.
# 2026-07-10 FCR-CTA (GATE-8/BR-09-20): total 497→498 / post 261→262: +1 POST @whitelist
#   imm00.transition_firmware_cr (server-driven Firmware CR transition). get/guest/json_param GIỮ
#   (params str, không parse_json). typed 498 == total. RE-VERIFY @source generate_spec.
# 2026-07-10 COMPETENCY-CTA (GATE-8/LL-FE-51): total 498→499 / get 236→237: +1 GET @whitelist
#   imm06.get_competency (server-driven competency allowed_transitions). post/guest/json_param GIỮ
#   (name str, không parse_json). typed 499 == total. RE-VERIFY @source generate_spec.
# 2026-07-11 CR-WF-12 INCIDENT-REOPEN (BR-12-23): total 499→500 / post 262→263: +1 POST @whitelist
#   imm12.reopen_incident (server-driven CTA "Mở lại điều tra", Resolved→In Progress; cap incident.close
#   parity close_incident). get/guest/json_param GIỮ (name/reason str, không parse_json). typed 500 ==
#   total. RE-VERIFY @source generate_spec.
# 2026-07-12 CR-WF-15-CC RECOUNT-CYCLE-COUNT (GATE-8/LL-FE-51): total 500→501 / post 263→264: +1 POST
#   @whitelist imm15.recount_cycle_count (server-driven CTA "Sửa đếm lại", Reviewed→Counting; cap
#   inventory.submit parity post_cycle_count). get/guest/json_param GIỮ (count_name/name/reason str,
#   không parse_json). typed 501 == total (authed op, baseline 401/403). RE-VERIFY @source generate_spec.
# 2026-07-14 ROOT-CAUSE FIX: baseline tuyệt đối GOM về SSoT `assetcore.tests.oas_baseline`
# (trước đây hardcode độc lập ở D10/D12/D15/D17 → lockstep-drift → silent RED; xem docstring
# SSoT + open-issue [BA]). Ledger đầy đủ (kể cả entry 501→505) nay ở SSoT. Alias `_BASELINE_*`
# GIỮ NGUYÊN mọi tham chiếu bên dưới — chỉ 1 nguồn số thay đổi.
# enriched_count derive ĐỘNG (D6-IMM09-ENRICH: KHÔNG magic 161) — D12 (error-surface) KHÔNG đụng enrich.
from assetcore.tests.oas_baseline import (  # noqa: E402
    BASELINE_GET as _BASELINE_GET,
    BASELINE_GUEST as _BASELINE_GUEST,
    BASELINE_JSON_PARAM as _BASELINE_JSON_PARAM,
    BASELINE_POST as _BASELINE_POST,
    BASELINE_TOTAL as _BASELINE_TOTAL,
)

_ERR_ENVELOPE_REF = "#/components/schemas/ErrorEnvelope"
_PREFIX = "/api/method/assetcore.api."

# Regex VI-clean guards (đồng bộ test_oas_generator._CAP_TOKEN_RE / _EN_STATUS_RE).
_CAP_TOKEN_RE = re.compile(r"[a-z]+\.[a-z]+")
_EN_STATUS_RE = re.compile(r"\b(Active|Out of Service|Under Maintenance|Decommissioned)\b")
# Op enriched mẫu (imm12/imm00) — phải GIỮ examples + status D6 sau merge baseline.
_ENRICHED_SAMPLES = {
    "imm12.report_incident": "post",
    "imm00.create_asset": "post",
}


def _is_authed(op: dict) -> bool:
    """True nếu op yêu cầu phiên: security == [{'cookieSession': []}] (D2)."""
    return op.get("security") == [{"cookieSession": []}]


def _is_guest(op: dict) -> bool:
    """True nếu op guest: security == [] (D2/D11)."""
    return op.get("security") == []


def _iter_ops(spec: dict):
    """Yield (path, verb, op) cho mọi operation trong spec['paths']."""
    for path, item in spec["paths"].items():
        for verb, op in item.items():
            yield path, verb, op


class TestOasD12ErrorSurface(unittest.TestCase):
    """Baseline 401/403 typed cho mọi authed op; guest KHÔNG có 401; merge giữ curated."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spec = openapi.generate_spec()

    def _op(self, op_tail: str, verb: str) -> dict:
        path = f"{_PREFIX}{op_tail}"
        self.assertIn(path, self.spec["paths"], f"Thiếu path {path}.")
        item = self.spec["paths"][path]
        self.assertIn(verb, item, f"{path} thiếu verb {verb} (có: {list(item)}).")
        return item[verb]

    # ── TC-OAS-D12-01 — mọi authed op có 401+403 ref ErrorEnvelope ────────────
    def test_d12_01_every_authed_op_has_401_403_ref_error_envelope(self):
        """MỌI op security==[{cookieSession:[]}] có responses['401'] và ['403'], cả 2
        schema $ref == ErrorEnvelope."""
        missing: list[str] = []
        authed_n = 0
        for _path, _verb, op in _iter_ops(self.spec):
            if not _is_authed(op):
                continue
            authed_n += 1
            r = op.get("responses", {})
            for code in ("401", "403"):
                if code not in r:
                    missing.append(f"{op['operationId']}: thiếu response {code}")
                    continue
                ref = (
                    r[code]
                    .get("content", {})
                    .get("application/json", {})
                    .get("schema", {})
                    .get("$ref")
                )
                if ref != _ERR_ENVELOPE_REF:
                    missing.append(
                        f"{op['operationId']}/{code}: $ref={ref!r} != {_ERR_ENVELOPE_REF}"
                    )
        self.assertEqual(missing, [], "Authed op thiếu 401/403 hoặc ref sai:\n  " + "\n  ".join(missing))
        # Sanity: phải có hàng trăm authed op (487 = baseline 492 − 5 guest).
        self.assertGreater(authed_n, 400, "Phải có >400 authed op.")

    def test_d12_01b_401_403_codes_match_ssot_http(self):
        """response 401 ↔ ErrorCode.UNAUTHORIZED; 403 ↔ ErrorCode.FORBIDDEN (SSoT _HTTP_FOR_CODE)."""
        self.assertEqual(_HTTP_FOR_CODE[ErrorCode.UNAUTHORIZED], 401, "SSoT: UNAUTHORIZED→401.")
        self.assertEqual(_HTTP_FOR_CODE[ErrorCode.FORBIDDEN], 403, "SSoT: FORBIDDEN→403.")
        # Lấy 1 op authed non-enriched bất kỳ → example code khớp.
        for _path, _verb, op in _iter_ops(self.spec):
            if not _is_authed(op):
                continue
            r = op["responses"]
            ex401 = r["401"]["content"]["application/json"].get("example")
            ex403 = r["403"]["content"]["application/json"].get("example")
            if ex401 is not None:
                self.assertEqual(ex401["code"], ErrorCode.UNAUTHORIZED)
                self.assertEqual(ex401["http_status"], 401)
            if ex403 is not None:
                self.assertEqual(ex403["code"], ErrorCode.FORBIDDEN)
                self.assertEqual(ex403["http_status"], 403)
            break

    # ── TC-OAS-D12-02 — guest op KHÔNG có 401; guest_count==5 ─────────────────
    def test_d12_02_guest_ops_have_no_401(self):
        """MỌI op guest (security==[]) KHÔNG có responses['401'] (không cần phiên)."""
        offenders: list[str] = []
        guest_n = 0
        for _path, _verb, op in _iter_ops(self.spec):
            if not _is_guest(op):
                continue
            guest_n += 1
            if "401" in op.get("responses", {}):
                offenders.append(op["operationId"])
        self.assertEqual(
            offenders, [], "Op guest KHÔNG được có 401 (không cần phiên):\n  " + "\n  ".join(offenders)
        )
        self.assertEqual(guest_n, _BASELINE_GUEST, "Bề mặt guest THẬT phải == 5 (D11 bất biến).")
        self.assertEqual(
            self.spec["x-assetcore-stats"]["guest_count"],
            _BASELINE_GUEST,
            "guest_count GIỮ 5 (D11 bất biến).",
        )

    def test_d12_02b_guest_ops_keep_200_and_default_only(self):
        """Guest op GIỮ 200 + default; KHÔNG thêm 401 (403 có thể có nếu enrich curated, nhưng
        guest hiện tại không thuộc 3 module enrich → chỉ 200+default)."""
        for _path, _verb, op in _iter_ops(self.spec):
            if not _is_guest(op):
                continue
            r = op.get("responses", {})
            self.assertIn("200", r, f"{op['operationId']}: guest phải giữ 200.")
            self.assertIn("default", r, f"{op['operationId']}: guest phải giữ default.")
            self.assertNotIn("401", r, f"{op['operationId']}: guest KHÔNG có 401.")

    # ── TC-OAS-D12-03 — VI-clean description ─────────────────────────────────
    def test_d12_03_baseline_401_403_descriptions_vi_clean(self):
        """description của 401/403 non-empty, tiếng Việt sạch — KHÔNG khớp EN-status,
        KHÔNG khớp cap-token regex `[a-z]+\\.[a-z]+`."""
        offenders: list[str] = []
        for _path, _verb, op in _iter_ops(self.spec):
            if not _is_authed(op):
                continue
            r = op["responses"]
            for code in ("401", "403"):
                desc = r[code].get("description", "")
                if not desc.strip():
                    offenders.append(f"{op['operationId']}/{code}: description rỗng")
                    continue
                if _EN_STATUS_RE.search(desc):
                    offenders.append(f"{op['operationId']}/{code}: EN-status leak → {desc!r}")
                if _CAP_TOKEN_RE.search(desc):
                    offenders.append(f"{op['operationId']}/{code}: cap-token leak → {desc!r}")
        self.assertEqual(offenders, [], "Description 401/403 không sạch:\n  " + "\n  ".join(offenders))

    def test_d12_03b_baseline_vi_descriptions_are_derived_from_ssot(self):
        """description baseline 401/403 lấy DẪN XUẤT từ constants BE (VI), non-hardcode-rời.

        Lấy 1 op authed non-enriched (không thuộc imm00/04/12) → so với helper SSoT.
        """
        baseline = openapi._baseline_error_responses(is_guest=False)
        self.assertIn("401", baseline)
        self.assertIn("403", baseline)
        desc401 = baseline["401"]["description"]
        desc403 = baseline["403"]["description"]
        # VI-clean + chứa từ khoá ngữ nghĩa SSoT (chưa đăng nhập / quyền).
        self.assertTrue(desc401.strip())
        self.assertTrue(desc403.strip())
        self.assertNotEqual(desc401, desc403, "401/403 description phải khác nhau.")
        self.assertFalse(_EN_STATUS_RE.search(desc401))
        self.assertFalse(_EN_STATUS_RE.search(desc403))
        self.assertFalse(_CAP_TOKEN_RE.search(desc401))
        self.assertFalse(_CAP_TOKEN_RE.search(desc403))
        # example code khớp ErrorCode SSoT.
        self.assertEqual(baseline["401"]["content"]["application/json"]["example"]["code"], ErrorCode.UNAUTHORIZED)
        self.assertEqual(baseline["403"]["content"]["application/json"]["example"]["code"], ErrorCode.FORBIDDEN)

    def test_d12_03c_baseline_guest_has_no_401(self):
        """`_baseline_error_responses(is_guest=True)` KHÔNG chứa 401, có 403."""
        baseline = openapi._baseline_error_responses(is_guest=True)
        self.assertNotIn("401", baseline, "Guest baseline KHÔNG có 401.")
        self.assertIn("403", baseline, "Guest baseline vẫn có 403 (forbidden có thể xảy ra).")

    # ── TC-OAS-D12-04 — enriched op GIỮ examples + status D6 ─────────────────
    def test_d12_04_enriched_ops_keep_examples_and_d6_status(self):
        """report_incident/create_asset GIỮ examples.errors + status codes D6 sau merge."""
        for op_tail, verb in _ENRICHED_SAMPLES.items():
            op = self._op(op_tail, verb)
            r = op["responses"]
            # 401/403 vẫn có (cả baseline lẫn curated đều phơi 2 mã này).
            self.assertIn("401", r, f"{op_tail}: phải có 401.")
            self.assertIn("403", r, f"{op_tail}: phải có 403.")
            # Curated phải THẮNG baseline → 403/401 có 'example' (curated thêm example),
            # và op có ÍT NHẤT 1 mã status D6 ngoài 401/403 (vd 422 VALIDATION).
            self.assertIn(
                "example",
                r["403"]["content"]["application/json"],
                f"{op_tail}/403: curated phải GIỮ example (merge không mất).",
            )
            extra_4xx = [c for c in r if re.fullmatch(r"[45]\d\d", c) and c not in ("401", "403")]
            self.assertGreater(
                len(extra_4xx),
                0,
                f"{op_tail}: phải GIỮ ≥1 status D6 ngoài 401/403 (vd 422) — merge không xoá curated.",
            )

    def test_d12_04b_report_incident_keeps_422_validation_example(self):
        """report_incident GIỮ 422 (VALIDATION) curated với example VI sau merge baseline."""
        op = self._op("imm12.report_incident", "post")
        r = op["responses"]
        http422 = str(_HTTP_FOR_CODE[ErrorCode.VALIDATION])
        self.assertIn(http422, r, "report_incident phải GIỮ 422 (VALIDATION) curated.")
        ex = r[http422]["content"]["application/json"].get("example")
        self.assertIsNotNone(ex, "422 curated phải GIỮ example.")
        self.assertEqual(ex["code"], ErrorCode.VALIDATION)
        # 403 curated giữ message VI cụ thể (không bị baseline đè).
        ex403 = r["403"]["content"]["application/json"].get("example")
        self.assertIsNotNone(ex403, "403 curated phải GIỮ example.")
        self.assertEqual(ex403["code"], ErrorCode.FORBIDDEN)

    # ── TC-OAS-D12-05 — stats.error_responses_typed_count + invariants ───────
    def test_d12_05_error_responses_typed_count_matches_dynamic(self):
        """error_responses_typed_count == đếm động op có ≥1 response status 4xx/5xx."""
        stats = self.spec["x-assetcore-stats"]
        self.assertIn("error_responses_typed_count", stats, "Thiếu khóa error_responses_typed_count.")
        expected = sum(
            1
            for _path, _verb, op in _iter_ops(self.spec)
            if any(re.fullmatch(r"[45]\d\d", str(c)) for c in op.get("responses", {}))
        )
        self.assertEqual(
            stats["error_responses_typed_count"],
            expected,
            "error_responses_typed_count PHẢI == đếm động op có ≥1 response 4xx/5xx.",
        )
        self.assertIsInstance(stats["error_responses_typed_count"], int)
        # Sau D12: MỌI op có ≥1 response 4xx — authed (500) có 401+403; guest (5) có 403
        # baseline (cấm-quyền vẫn xảy ra ở guest endpoint). ⟹ typed_count == total (SSoT).
        self.assertEqual(
            stats["error_responses_typed_count"],
            _BASELINE_TOTAL,
            "Mọi op (authed 401/403 + guest 403) có ≥1 status 4xx → typed_count == total (SSoT oas_baseline).",
        )

    def test_d12_05b_sibling_stats_unchanged(self):
        """total/get/post/guest/enriched/json_param/cap_set_version KHÔNG đổi so baseline."""
        from assetcore.services.shared import rbac

        stats = self.spec["x-assetcore-stats"]
        self.assertEqual(stats["total_endpoints"], _BASELINE_TOTAL, "total == SSoT oas_baseline.BASELINE_TOTAL (ledger @source).")
        self.assertEqual(stats["get_count"], _BASELINE_GET, "get == SSoT BASELINE_GET (4 CTA mới 501→505 đều POST → get GIỮ).")
        self.assertEqual(stats["post_count"], _BASELINE_POST, "post == SSoT BASELINE_POST (+4 POST CTA: suspend/restore_competency, request_rca, start_review).")
        self.assertEqual(stats["guest_count"], _BASELINE_GUEST, "guest GIỮ 5.")
        expected_enriched = sum(
            1
            for p in self.spec["paths"]
            if _ovr.enrich_meta_for(p.replace(_PREFIX, "", 1)) is not None
        )
        self.assertEqual(
            stats["enriched_count"], expected_enriched,
            "enriched_count == số op enrich đếm động (D12 không đụng enrich, KHÔNG magic).",
        )
        self.assertEqual(stats["json_param_count"], _BASELINE_JSON_PARAM, "json_param 64 (+imm14.list_decommissions.filters parse_json).")
        self.assertEqual(stats["cap_set_version"], rbac.CAP_SET_VERSION, "cap_set_version KHÔNG đổi.")

    # ── TC-OAS-D12-06 — 0 dangling $ref + openapi 3.1 + key-order ────────────
    def test_d12_06_no_dangling_ref_and_valid_openapi(self):
        """Walk toàn spec — mọi $ref resolve về component TỒN TẠI; openapi==3.1.0; JSON-serializable."""
        spec = self.spec
        self.assertEqual(spec["openapi"], "3.1.0")
        defined = set(spec["components"]["schemas"].keys()) | set(
            spec["components"].get("securitySchemes", {}).keys()
        )

        dangling: list[str] = []

        def _walk(node):
            if isinstance(node, dict):
                ref = node.get("$ref")
                if isinstance(ref, str):
                    # '#/components/schemas/X' hoặc '#/components/securitySchemes/X'
                    name = ref.rsplit("/", 1)[-1]
                    if name not in defined:
                        dangling.append(ref)
                for v in node.values():
                    _walk(v)
            elif isinstance(node, list):
                for v in node:
                    _walk(v)

        _walk(spec)
        self.assertEqual(dangling, [], f"0 dangling $ref required; thấy: {dangling}")
        self.assertIn("ErrorEnvelope", spec["components"]["schemas"], "ErrorEnvelope phải tồn tại.")

    def test_d12_06b_spec_json_serializable_and_key_order(self):
        """spec JSON-serializable; key-order info→components→paths→tags→x-assetcore-stats giữ."""
        import json

        s = frappe.as_json(self.spec)
        rt = json.loads(s)
        self.assertEqual(rt["openapi"], "3.1.0")
        keys = list(self.spec.keys())
        self.assertLess(keys.index("info"), keys.index("components"))
        self.assertLess(keys.index("components"), keys.index("paths"))
        self.assertLess(keys.index("paths"), keys.index("tags"))
        self.assertLess(keys.index("tags"), keys.index("x-assetcore-stats"))

    def test_d12_06c_status_code_keys_are_valid_http_strings(self):
        """Mọi status-code key 4xx/5xx là chuỗi HTTP hợp lệ (str(int) trong _HTTP_FOR_CODE.values())."""
        valid_http = {str(v) for v in _HTTP_FOR_CODE.values()}
        offenders: list[str] = []
        for _path, _verb, op in _iter_ops(self.spec):
            for code in op.get("responses", {}):
                if code in ("200", "default"):
                    continue
                if not re.fullmatch(r"[45]\d\d", code):
                    offenders.append(f"{op['operationId']}: key {code!r} không phải 4xx/5xx")
                    continue
                if code not in valid_http:
                    offenders.append(f"{op['operationId']}: status {code} ∉ _HTTP_FOR_CODE.values()")
        self.assertEqual(offenders, [], "Status-code key không hợp lệ:\n  " + "\n  ".join(offenders))
