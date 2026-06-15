"""TC-MOB-SEC-01..N — EPIC-G G4 security-gate verify guard (introspection-only).

Bốn invariant bảo mật (DoD EPIC-G G4 — `completion/EPIC-G-golive-hardening.md §4 G4`),
KIỂM bằng introspection STDLIB (`inspect` + `Path.read_text`) — KHÔNG HTTP, KHÔNG cloud,
KHÔNG sửa `api/*.py`/`services/*.py`/yaml-schema (owner constraint EPIC-G: test+doc-only):

GUARD-1 — no-traceback-leak (re-use preflight, read-only)
    `verify_oauth_client()` (`api/mobile/preflight.py`) chạy KHÔNG raise (count==0 thật @source)
    + report dict KHÔNG chứa key/value 'Traceback (most recent call last)' / 'exc'. Re-dùng
    preflight verifier (read-only gate) — chứng minh BE-helper an toàn KHÔNG leak stack ngay cả
    nhánh chưa-provision. Phản ánh hợp đồng `preflight.py:23` (KHÔNG leak traceback).

GUARD-2 — CI-guard placeholder (prod-build flag)
    Khi cờ prod-build BẬT → spec yaml KHÔNG còn `REPLACE-WITH-PUBLIC-HOST` (yaml:108) +
    version KHÔNG match `*-skeleton` (yaml:90). Hiện trạng DEV (cờ off) = control GREEN (placeholder
    được PHÉP tồn tại ở skeleton-Phase-A). RED-before: inject placeholder vào deepcopy + bật cờ →
    guard RED. Bảo vệ R6 (EPIC-G §8): placeholder/skeleton lọt prod build → client codegen trỏ host sai.

GUARD-3 — CORS no-wildcard literal (docset đặc tả prod)
    Docset đặc tả prod (08/10/ADR-004) KHÔNG có literal cấu-hình-KHUYẾN-NGHỊ `allow_cors: '*'`
    (dạng YAML key-config). Mọi nhắc tới wildcard CHỈ ở dạng NEGATED/cấm ('CẤM', 'KHÔNG'). RED-before:
    inject `allow_cors: '*'` literal (recommended-form) vào text → guard RED. Phản ánh T3 (`08 §1`) +
    R2 (EPIC-G §8): `allow_cors='*'` prod = mọi origin credential-echo.

GUARD-4 — status-line-vs-body invariant (§3.2)
    `_err(...)` (`utils/response.py`) body LUÔN chứa key `http_status` — CẢ nhánh int-code (response.py:127)
    LẪN nhánh chuỗi ErrorCode (response.py:131). Phản ánh `EPIC-G §3.2`: in-handler-4xx ARRIVE trên
    HTTP-200 → client phải route theo `body.http_status` (KHÔNG status-line). RED-before: stub `_err`
    bỏ `http_status` → guard RED.

GUARD-6 — no-token-leak drift-guard (G-A3, EPIC-G G4 sub-condition (c))
    Machine-check invariant "qr_token KHÔNG leak trong MVP read response" xuyên source + docset:
    (1) source-grounded @source `api/imm00.py`: `def _strip_qr_token(doc)` pop `qr_token` (KHÔNG
        line-tuyệt-đối — derive-from-source bằng `inspect.getsource`, anti stale-evidence); + `get_asset`
        body chứa `return _ok(_strip_qr_token(doc))`. Phản ánh ADR-001 §D4 rule 9 (no-raw-token).
    (2) docset prose invariant raw-text: `08 §5/T4` + `ACCEPTANCE-CHECKLIST GO-7/G4(c)` assert
        qr_token/token KHÔNG leak trong MVP read response (`getAsset`/`getAssetScanInfo`).
    (3) RED-before/GREEN-after string-mutate bản-sao (xoá `_strip_qr_token` call / xoá `pop('qr_token')`
        / flip prose phủ-định 'KHÔNG ... leak'→'leak') → guard RAISE; control THẬT sạch → GREEN.
    Đóng read-path analog của G4(a/b/d): client read MVP KHÔNG được surface khóa tra-cứu MỜ nội bộ.

Owner-constraint check (EPIC-G AUTO):
    test+doc introspection-only → `git diff --stat` api/services/*.py + yaml-schema = TRỐNG.
    STDLIB-only (KHÔNG cài lib mới): `inspect`, `re`, `unittest`, `copy`, `pathlib`.

Regression GIỮ GREEN sau guard này:
    `test_oas_d13_servers` (15 OK) · `test_oas_serve` (13 OK) · `test_mobile_preflight` (26 OK).

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_security_gate
"""
from __future__ import annotations

import copy
import inspect
import re
import unittest
from pathlib import Path

import frappe

from assetcore.api.mobile import preflight
from assetcore.utils import response as _resp

# ── Path SSoT (STDLIB Path — KHÔNG DB) ───────────────────────────────────────
# parents[2] = .../apps/assetcore (mirror test_mobile_docset._REPO_ROOT).
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOCS_MOBILE = _REPO_ROOT / "docs" / "mobile"
_YAML = _DOCS_MOBILE / "openapi" / "assetcore-mobile.openapi.yaml"

# Named doc Path SSoT (reuse cho GUARD-3 + GUARD-5 traceback-gate-doc — KHÔNG hardcode rời rạc).
_DOC_08 = _DOCS_MOBILE / "08-security-compliance.md"
_DOC_10 = _DOCS_MOBILE / "10-deploy-ops.md"
_ADR_004 = _DOCS_MOBILE / "ADR-MOBILE-004.md"
# Checklist go-live (GUARD-6 GO-7/G4(c) no-token-leak doc-invariant).
_ACCEPTANCE_CHECKLIST = _DOCS_MOBILE / "completion" / "ACCEPTANCE-CHECKLIST.md"
# EPIC-G completion doc (GUARD-9 §3.3 knob table + §8 R4 host_name invariant).
_EPIC_G = _DOCS_MOBILE / "completion" / "EPIC-G-golive-hardening.md"

# Docset đặc tả prod scan cho GUARD-3 (CORS no-wildcard).
_PROD_SPEC_DOCS = [
    _DOC_08,
    _DOC_10,
    _DOCS_MOBILE / "completion" / "EPIC-G-golive-hardening.md",
    _ADR_004,
]

# Marker leak traceback (frappe `is_traceback_allowed`/CPython traceback header).
_TRACEBACK_MARKERS = ("Traceback (most recent call last)",)
# Placeholder/skeleton CI-guard (R6).
_PLACEHOLDER_HOST = "REPLACE-WITH-PUBLIC-HOST"
_SKELETON_SUFFIX_RE = re.compile(r"-skeleton\b")
# CORS wildcard literal dạng KHUYẾN-NGHỊ (YAML key-config) — CẤM ở docset prod.
# Chỉ bắt dạng config-recommended `allow_cors: '*'` / `allow_cors: "*"` (key-colon-SPACE-quoted-star —
# YAML mapping THẬT luôn có >=1 space sau ':'). \s+ (one-or-more) loại trừ:
#   - prose Python-assignment `allow_cors='*'` (luôn trong câu 'CẤM ...') — KHÔNG có ':'.
#   - inline-code mô-tả-guard `allow_cors:'*'` (no-space, EPIC-G §4 G4 self-describe negated) — KHÔNG khuyến-nghị.
_CORS_WILDCARD_RECOMMEND_RE = re.compile(r"""allow_cors:[ \t]+['"]\*['"]""")

# SSoT số test* method trong module này (anti count-drift — analog F-C3 meta-guard).
# Cập nhật khi thêm/bớt CỐ Ý 1 test method; nếu lệch ⇒ TC-MOB-SEC-10 ĐỎ ⇒ buộc xác nhận
# số test đúng kỳ vọng (chống "âm thầm mất test" / dup name nuốt test).
# NOTE(G-A2): 16 base + 5 TC GUARD-5 TestSecGateTracebackGateDoc = 21.
# NOTE(G-A3): +7 TC GUARD-6 TestSecGateNoTokenLeak (no-token-leak G4(c)) = 28.
#   7 method test_sec_06_*: strip_qr_token_grounded_at_source · get_asset_returns_stripped ·
#   08_doc_no_token_leak_present · checklist_go7_g4c_present ·
#   red_before_inject_unstripped_response_is_red · red_before_flip_prose_negation_is_red ·
#   green_after_control_real_source_is_green.
# NOTE(G-A4): +0 (G-A4 = docset row-write GUARD-6 G4(c), KHÔNG thêm test method) — SSoT giữ 28.
# NOTE(G-A5): +8 TC GUARD-7 TestSecGateRateLimitHeaderDoc (429-header G4 sub-condition (d)) = 36.
#   8 method test_sec_07_*: rate_limit_apply_conf_gated_at_source ·
#   headers_emit_xratelimit_and_retry_after_at_source · 08_doc_d_invariant_present ·
#   10_doc_known_clause_present · red_before_remove_conf_gate_is_red ·
#   red_before_flip_known_clause_is_red · green_after_control_real_source_is_green ·
#   green_after_control_real_doc_is_green. Đóng LAST unguarded EPIC-G G4 invariant (d).
#   Meta-guard test_sec_10 đếm THẬT = 36 → SSoT=36.
# NOTE(G-A6): +8 TC GUARD-8 TestSecGateAuditActorNd98Doc (NĐ98 audit-actor §6 invariant) = 44.
#   8 method test_sec_gate_*: audit_actor_lifecycle_source_grounded ·
#   verify_audit_chain_integrity_source_grounded · bearer_set_user_frappe_auth_grounded ·
#   doc_08_section2_2_actor_invariant_present · doc_08_negation_no_service_account_present ·
#   doc_0851_gate_e_audit_actor_present · red_before_inject_removes_session_user_is_red ·
#   red_before_flip_service_account_negation_is_red. Đóng LAST unguarded EPIC-G §6 invariant
#   (bearer→set_user→log_audit_event(actor=session.user)→verify_audit_chain @source + doc 08 §2.2/§5.1(e)
#   + 10 §6.3 (verify-audit)). Meta-guard test_sec_10 đếm THẬT = 44 → SSoT=44.
# NOTE(G-A8): +8 TC GUARD-9 TestSecGateHostNameIssuerDoc (host_name/issuer go-live G4(f)) = 52.
#   8 method test_sec_09_*: get_url_host_name_grounded_at_source ·
#   get_url_fallback_internal_site_at_source · doc_10_section3_host_invariant_present ·
#   doc_10_section62_checklist_host_present · doc_08_gate_f_host_issuer_present ·
#   epicg_section33_section8_r4_host_invariant_present ·
#   red_before_remove_host_name_gate_at_source_is_red · red_before_flip_no_miyano_negation_is_red.
#   Đóng LAST unguarded KNOB-MATRIX invariant (knob #1 host_name = flow-2 QR deep-link + OIDC issuer;
#   4/5 trước có guard: CORS=GUARD-3, traceback=GUARD-5, rate-limit-header=GUARD-7, token-leak/audit=
#   GUARD-6/8). Source @source frappe/utils/data.py get_url (:1599) host_name (:1605) + fallback
#   protocol+site (:1631) + doc-invariant 08 §5.1(f) / 10 §3·§6.2·§6.3 / EPIC-G §3.3·§8 R4.
#   Meta-guard test_sec_10 đếm THẬT = 52 → SSoT=52.
_EXPECTED_SECURITY_GATE_TEST_COUNT = 52


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestSecGateNoTracebackLeak(unittest.TestCase):
    """GUARD-1 — `verify_oauth_client()` read-only KHÔNG raise + KHÔNG leak traceback."""

    def test_sec_01_verify_oauth_client_does_not_raise(self):
        """verify_oauth_client() (admin context) chạy KHÔNG raise — kể cả nhánh count==0.

        Re-use preflight verifier (read-only). KHÔNG ghi DB. Chứng minh BE-helper an toàn
        cho security-gate G4 — gọi được mà KHÔNG vỡ (no-raise nghiệp vụ, `preflight.py:23`).
        """
        # verify_oauth_client gọi frappe.only_for("System Manager"); test chạy as Administrator
        # (frappe test default) → qua gate. KHÔNG raise nghiệp vụ ở mọi nhánh.
        try:
            report = preflight.verify_oauth_client()
        except frappe.PermissionError:
            self.skipTest("Không ở context System Manager — bỏ qua (gate quyền, không phải leak).")
            return
        self.assertIsInstance(report, dict, "verify_oauth_client PHẢI trả dict report (no-raise).")
        self.assertIn("ready", report)
        self.assertIn("blockers", report)

    def test_sec_01_report_has_no_traceback_marker(self):
        """report dict KHÔNG chứa marker 'Traceback (most recent call last)' / key 'exc'
        ở BẤT KỲ key/value nào (serialize toàn report → grep marker)."""
        try:
            report = preflight.verify_oauth_client()
        except frappe.PermissionError:
            self.skipTest("Không ở context System Manager — bỏ qua.")
            return
        # Serialize toàn bộ report (JSON-safe) → grep marker leak.
        blob = frappe.as_json(report)
        for marker in _TRACEBACK_MARKERS:
            self.assertNotIn(
                marker, blob, f"report verify_oauth_client KHÔNG được leak '{marker}'."
            )
        # KHÔNG có key 'exc' (frappe traceback envelope key) ở top-level report.
        self.assertNotIn("exc", report, "report KHÔNG được có key 'exc' (traceback envelope).")

    def test_sec_01_red_before_detector_catches_injected_traceback(self):
        """RED-before/GREEN-after THẬT: bản-sao report inject marker 'Traceback...' → detector RAISE;
        report THẬT sạch → GREEN. Chứng minh guard bắt leak (chống false-green)."""
        try:
            real = preflight.verify_oauth_client()
        except frappe.PermissionError:
            self.skipTest("Không ở context System Manager — bỏ qua.")
            return

        def _detect_leak(report: dict) -> bool:
            blob = frappe.as_json(report)
            return any(m in blob for m in _TRACEBACK_MARKERS)

        # Control THẬT: sạch.
        self.assertFalse(_detect_leak(real), "Control report THẬT KHÔNG được có marker leak.")
        # RED-before: inject marker vào deepcopy (KHÔNG đụng report thật/DB).
        injected = copy.deepcopy(real)
        injected.setdefault("blockers", []).append("Traceback (most recent call last): boom")
        self.assertTrue(_detect_leak(injected), "Detector PHẢI bắt được traceback inject (anti-false-green).")


class TestSecGateCiPlaceholderGuard(unittest.TestCase):
    """GUARD-2 — CI-guard: placeholder host / skeleton-version KHÔNG lọt prod build."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.yaml_text = _read(_YAML)

    @staticmethod
    def _prod_build_violations(text: str, prod_build: bool) -> list[str]:
        """Trả danh sách vi-phạm CI-guard KHI cờ prod-build BẬT.

        prod_build=False (dev/skeleton Phase A) → [] (placeholder được PHÉP).
        prod_build=True → bắt `REPLACE-WITH-PUBLIC-HOST` + version `*-skeleton`.
        """
        if not prod_build:
            return []
        violations: list[str] = []
        if _PLACEHOLDER_HOST in text:
            violations.append(f"placeholder host '{_PLACEHOLDER_HOST}' lọt prod build")
        for line in text.splitlines():
            m = re.match(r"\s*version:\s*(\S+)", line)
            if m and _SKELETON_SUFFIX_RE.search(m.group(1)):
                violations.append(f"version skeleton '{m.group(1)}' lọt prod build")
        return violations

    def test_sec_02_control_dev_flag_off_is_green(self):
        """Control THẬT (dev, cờ prod-build OFF) → 0 vi-phạm (placeholder PHÉP ở skeleton-Phase-A)."""
        self.assertEqual(
            self._prod_build_violations(self.yaml_text, prod_build=False),
            [],
            "Cờ prod-build OFF: placeholder/skeleton được PHÉP (dev) → KHÔNG vi-phạm.",
        )

    def test_sec_02_red_before_inject_placeholder_prod_flag_on_is_red(self):
        """RED-before: deepcopy text + bật cờ prod-build → guard bắt CẢ placeholder host LẪN skeleton-version."""
        # Hiện trạng skeleton THẬT đã có sẵn placeholder + version skeleton (yaml:90/:108) →
        # bật cờ prod-build trên text THẬT đã đủ để RED (KHÔNG cần inject thêm).
        violations = self._prod_build_violations(self.yaml_text, prod_build=True)
        self.assertTrue(
            any(_PLACEHOLDER_HOST in v for v in violations),
            "Cờ prod-build ON: PHẢI bắt placeholder host (yaml:108).",
        )
        self.assertTrue(
            any("skeleton" in v for v in violations),
            "Cờ prod-build ON: PHẢI bắt version skeleton (yaml:90).",
        )

    def test_sec_02_green_after_cleaned_text_prod_flag_on_is_green(self):
        """GREEN-after: bản-sao text đã thay placeholder→host thật + version bỏ -skeleton → 0 vi-phạm
        (chứng minh guard CHỈ chặn placeholder, KHÔNG false-RED khi prod build sạch)."""
        cleaned = self.yaml_text.replace(_PLACEHOLDER_HOST, "api.benhvien-x.vn")
        cleaned = re.sub(r"(\n\s*version:\s*[^\s-]+)-skeleton\b", r"\1", cleaned)
        self.assertEqual(
            self._prod_build_violations(cleaned, prod_build=True),
            [],
            "Prod build SẠCH (host thật + version non-skeleton) → KHÔNG vi-phạm.",
        )

    def test_sec_02_yaml_skeleton_markers_exist_at_source(self):
        """Sanity drift-guard: yaml THẬT hiện CÓ placeholder + version skeleton (anchor cho guard).

        Nếu Phase B/G đã thay (host thật + version non-skeleton) → test này ĐỎ ⇒ buộc gỡ skeleton-anchor
        khỏi guard (doc đã go-live) — chống guard chạy vô-nghĩa sau khi placeholder biến mất.
        """
        self.assertIn(
            _PLACEHOLDER_HOST,
            self.yaml_text,
            "yaml skeleton-Phase-A PHẢI còn placeholder (anchor); nếu đã thay → cập nhật guard.",
        )
        version_line = next(
            (ln for ln in self.yaml_text.splitlines() if re.match(r"\s*version:", ln)), ""
        )
        self.assertRegex(version_line, r"-skeleton\b", "version yaml hiện PHẢI còn '-skeleton'.")


class TestSecGateCorsNoWildcardLiteral(unittest.TestCase):
    """GUARD-3 — docset đặc tả prod KHÔNG có literal khuyến-nghị `allow_cors: '*'`."""

    def test_sec_03_no_recommended_cors_wildcard_literal_in_prod_docs(self):
        """08/10/ADR-004/EPIC-G KHÔNG chứa literal config-KHUYẾN-NGHỊ `allow_cors: '*'`
        (YAML key-config). Mọi nhắc tới wildcard chỉ ở dạng NEGATED/cấm (prose 'CẤM ...')."""
        for path in _PROD_SPEC_DOCS:
            self.assertTrue(path.is_file(), f"Doc prod-spec thiếu: {path}")
            text = _read(path)
            hits = _CORS_WILDCARD_RECOMMEND_RE.findall(text)
            self.assertEqual(
                hits,
                [],
                f"{path.name} KHÔNG được có literal khuyến-nghị `allow_cors: '*'` "
                f"(YAML config-form). Wildcard chỉ được nhắc dạng NEGATED/cấm (T3/R2).",
            )

    def test_sec_03_red_before_inject_wildcard_literal_is_red(self):
        """RED-before/GREEN-after THẬT: text THẬT GREEN; inject `allow_cors: '*'` (recommended-form)
        vào bản-sao → detector RED. Chứng minh guard bắt wildcard-config (chống false-green)."""
        sample = _read(_PROD_SPEC_DOCS[0])  # 08-security-compliance.md
        # Control THẬT: KHÔNG có recommended-wildcard.
        self.assertEqual(
            _CORS_WILDCARD_RECOMMEND_RE.findall(sample), [], "Control text THẬT phải sạch wildcard-config."
        )
        # RED-before: inject dạng YAML config khuyến-nghị có-space (KHÔNG ghi file — chỉ in-memory).
        poisoned = sample + "\n```yaml\nallow_cors: '*'\n```\n"
        self.assertTrue(
            _CORS_WILDCARD_RECOMMEND_RE.search(poisoned),
            "Detector PHẢI bắt `allow_cors: '*'` config-form inject (anti-false-green).",
        )

    def test_sec_03_negated_wildcard_prose_is_allowed_green(self):
        """GREEN: prose NEGATED dạng Python-assignment `allow_cors='*'` (trong câu 'CẤM ...') KHÔNG bị
        regex bắt — guard CHỈ chặn config-form khuyến-nghị, KHÔNG chặn threat-model mô tả wildcard."""
        negated_samples = [
            "CẤM `allow_cors='*'` ở prod",
            'CẤM: `"allow_cors": "*"` ở prod',
            "Nếu set `allow_cors='*'` ở prod ⇒ MỌI origin gửi credential",
        ]
        for s in negated_samples:
            self.assertEqual(
                _CORS_WILDCARD_RECOMMEND_RE.findall(s),
                [],
                f"Prose NEGATED KHÔNG được bị flag (chỉ config-form bị chặn): {s!r}.",
            )


class TestSecGateErrHttpStatusInvariant(unittest.TestCase):
    """GUARD-4 — `_err(...)` body LUÔN có key `http_status` (status-line-vs-body §3.2)."""

    def test_sec_04_err_int_code_branch_has_http_status(self):
        """Nhánh int-code (legacy `_err(msg, 400)` — response.py:125-128) → body có `http_status`."""
        body = _resp._err("lỗi nghiệp vụ", 422)
        self.assertIn("http_status", body, "_err(int code) body PHẢI có key 'http_status' (§3.2).")
        self.assertEqual(body["http_status"], 422)
        self.assertFalse(body["success"], "Error envelope PHẢI success=False.")

    def test_sec_04_err_string_code_branch_has_http_status(self):
        """Nhánh chuỗi ErrorCode (`_err(msg, ErrorCode.X)` — response.py:129-131) → body có `http_status`
        map từ `_HTTP_FOR_CODE`."""
        body = _resp._err("thiếu quyền", _resp.ErrorCode.FORBIDDEN)
        self.assertIn("http_status", body, "_err(str ErrorCode) body PHẢI có key 'http_status' (§3.2).")
        self.assertEqual(body["http_status"], 403, "FORBIDDEN → http_status 403 (reflect in-handler-403).")
        self.assertEqual(body["code"], "FORBIDDEN")

    def test_sec_04_err_both_branches_invariant_across_error_codes(self):
        """Invariant TỔNG: MỌI ErrorCode (chuỗi) + 1 mẫu int → `_err` luôn emit `http_status` int."""
        for ec in (
            _resp.ErrorCode.VALIDATION,
            _resp.ErrorCode.BUSINESS_RULE,
            _resp.ErrorCode.UNAUTHORIZED,
            _resp.ErrorCode.FORBIDDEN,
            _resp.ErrorCode.NOT_FOUND,
            _resp.ErrorCode.CONFLICT,
            _resp.ErrorCode.RATE_LIMITED,
            _resp.ErrorCode.COMPLIANCE_BLOCKED,
            _resp.ErrorCode.INTERNAL,
        ):
            body = _resp._err("msg", ec)
            self.assertIn("http_status", body, f"_err({ec}) THIẾU http_status (§3.2 vỡ).")
            self.assertIsInstance(body["http_status"], int, f"http_status({ec}) phải là int.")
        # Mẫu int-branch.
        self.assertIn("http_status", _resp._err("x", 409))

    def test_sec_04_err_source_assigns_http_status_in_payload(self):
        """Source-introspection (anti-regression): `inspect.getsource(_err)` chứa gán
        `"http_status": http` trong payload — phản ánh §3.2 (in-handler-4xx arrive HTTP-200 → body-key).

        Nếu ai gỡ key khỏi payload (regress) → behaviour test trên + source-guard này cùng ĐỎ.
        """
        src = inspect.getsource(_resp._err)
        self.assertRegex(
            src,
            r'["\']http_status["\']\s*:\s*http',
            "_err source PHẢI gán '\"http_status\": http' vào payload (§3.2 status-line-vs-body).",
        )

    def test_sec_04_red_before_stub_err_without_http_status_is_red(self):
        """RED-before/GREEN-after THẬT: stub `_err` BỎ `http_status` → detector RED;
        `_err` THẬT → GREEN. Chứng minh guard bắt regress drop-key (chống false-green)."""

        def _stub_err_missing(msg, code=400):
            # Cố ý BỎ http_status — mô phỏng regress.
            return {"success": False, "error": msg, "code": code}

        def _has_http_status(fn) -> bool:
            return "http_status" in fn("x", 422)

        # GREEN: _err THẬT có http_status.
        self.assertTrue(_has_http_status(_resp._err), "Control _err THẬT phải có http_status.")
        # RED-before: stub thiếu → detector bắt.
        self.assertFalse(
            _has_http_status(_stub_err_missing),
            "Detector PHẢI bắt _err-stub thiếu http_status (anti-false-green).",
        )


class TestSecGateTracebackGateDoc(unittest.TestCase):
    """GUARD-5 — traceback-gate prose drift-guard (G-A2, EPIC-G G3 doc-part).

    Machine-check invariant cơ-chế bảo mật no-traceback-leak xuyên 3 doc đặc-tả prod:
        `08 §4(b)/§5` · `10 §6.2 item(6)` · `ADR-004 Consequences`.
    Invariant (đồng-bộ @source `frappe/utils/response.py:60-65`):
        gate THẬT = System Setting `allow_error_traceback` (default 1 = ON ⇒ prod LEAK,
        PHẢI tắt =0) — **KHÔNG phải** `developer_mode` / `site_config`.

    KIỂM raw-text STDLIB (`Path.read_text` + `re`) — derive-from-source, KHÔNG hardcode dòng.
    `test_sec_05_source_gate_grounded` neo invariant vào @source response.py (anti stale-evidence:
    nếu Frappe đổi cơ-chế → ĐỎ buộc cập-nhật doc). RED-before (`test_sec_05_red_before_...`) string-mutate
    bản-sao text (`System Setting`→`developer_mode` / xoá cụm phủ-định) → guard RAISE — chứng minh
    guard THẬT bắt drift (analog `test_sec_03_negated_wildcard_prose_is_allowed_green` + RED-before).
    Doc/test introspection-only → git diff api/services/*.py + yaml-schema = TRỐNG (owner constraint EPIC-G G4).
    """

    # Regex phủ-định 'KHÔNG phải developer_mode/site_config' — tolerant backtick/space/slash
    # (08/ADR dùng '`developer_mode` / `site_config`'; 10 dùng '`developer_mode`/`site_config`').
    _NEG_DEVMODE_RE = re.compile(
        r"KHÔNG phải\s*`?developer_mode`?\s*/\s*`?site_config`?", re.IGNORECASE
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.text_08 = _read(_DOC_08)
        cls.text_10 = _read(_DOC_10)
        cls.text_adr = _read(_ADR_004)

    @staticmethod
    def _section(text: str, start_marker: str, end_marker: str | None) -> str:
        """Cắt section [start_marker, end_marker) raw-text (derive-from-source, KHÔNG số dòng).

        start_marker PHẢI tồn tại (assert ở caller). end_marker=None ⇒ tới hết file.
        """
        i = text.find(start_marker)
        if i < 0:
            return ""
        j = text.find(end_marker, i + len(start_marker)) if end_marker else len(text)
        if j < 0:
            j = len(text)
        return text[i:j]

    # ── (1) 08-security §4(b)+§5 ────────────────────────────────────────────
    def test_sec_05_08_doc_present(self):
        """08 §4(b)+§5 chứa nguyên-văn invariant traceback-gate (raw-text, derive-from-source).

        Yêu-cầu: 'allow_error_traceback' + 'System Setting' + phủ-định-developer_mode/site_config
        + evidence 'response.py:60'. Quét trong khối §4→cuối §5 (KHÔNG quét toàn file → tránh
        false-green do cụm trùng ở chỗ khác).
        """
        # §4 + §5 = từ '## 4.' tới '## 6.' (hoặc cuối file nếu §6 vắng).
        sect = self._section(self.text_08, "## 4. Checklist Security Go-live", "## 6.")
        self.assertTrue(sect, "08: KHÔNG tìm thấy section §4 ('## 4. Checklist Security Go-live').")
        self.assertIn("allow_error_traceback", sect, "08 §4/§5 PHẢI chứa 'allow_error_traceback'.")
        self.assertIn("System Setting", sect, "08 §4/§5 PHẢI chứa 'System Setting' (gate=System Setting).")
        self.assertRegex(
            sect,
            self._NEG_DEVMODE_RE,
            "08 §4/§5 PHẢI có cụm phủ-định 'KHÔNG phải developer_mode / site_config'.",
        )
        self.assertIn("response.py:60", sect, "08 §4/§5 PHẢI neo evidence 'response.py:60' (@source).")

    # ── (2) 10-deploy §6.2 item (6) ─────────────────────────────────────────
    def test_sec_05_10_doc_present(self):
        """10 §6.2 item (6) chứa invariant: 'allow_error_traceback' + 'System Setting=0'
        + 'is_traceback_allowed' + phủ-định developer_mode/site_config (raw-text)."""
        sect = self._section(self.text_10, "### 6.2 Execute", "### 6.3")
        self.assertTrue(sect, "10: KHÔNG tìm thấy section §6.2 ('### 6.2 Execute').")
        # Khoanh hẹp về item (6) — dòng bắt đầu '**(6)**' tới item kế ('**(reload)**'/note).
        item6 = self._section(sect, "**(6)**", "**(reload)**")
        self.assertTrue(item6, "10 §6.2: KHÔNG tìm thấy item (6) ('**(6)**').")
        self.assertIn("allow_error_traceback", item6, "10 §6.2(6) PHẢI chứa 'allow_error_traceback'.")
        self.assertIn("System Setting=0", item6, "10 §6.2(6) PHẢI chứa 'System Setting=0' (tắt gate).")
        self.assertIn(
            "is_traceback_allowed", item6, "10 §6.2(6) PHẢI chứa 'is_traceback_allowed' (gate fn @source)."
        )
        self.assertRegex(
            item6,
            self._NEG_DEVMODE_RE,
            "10 §6.2(6) PHẢI có phủ-định 'KHÔNG phải developer_mode/site_config'.",
        )

    # ── (3) ADR-MOBILE-004 Consequences ─────────────────────────────────────
    def test_sec_05_adr004_doc_present(self):
        """ADR-004 ## Consequences chứa cùng invariant: 'System Setting' + phủ-định
        developer_mode/site_config + 'response.py:60-65' (raw-text)."""
        sect = self._section(self.text_adr, "## Consequences", None)
        self.assertTrue(sect, "ADR-004: KHÔNG tìm thấy section '## Consequences'.")
        self.assertIn("allow_error_traceback", sect, "ADR-004 Consequences PHẢI chứa 'allow_error_traceback'.")
        self.assertIn("System Setting", sect, "ADR-004 Consequences PHẢI chứa 'System Setting'.")
        self.assertRegex(
            sect,
            self._NEG_DEVMODE_RE,
            "ADR-004 Consequences PHẢI có phủ-định 'KHÔNG phải developer_mode / site_config'.",
        )
        self.assertIn(
            "response.py:60-65", sect, "ADR-004 Consequences PHẢI neo evidence 'response.py:60-65' (@source)."
        )

    # ── (4) ground-truth @source frappe/utils/response.py ───────────────────
    def test_sec_05_source_gate_grounded(self):
        """Anti stale-evidence: gate THẬT `is_traceback_allowed` (response.py:60) đọc
        `get_system_settings('allow_error_traceback')` (:63) TỒN TẠI @source.

        Nếu Frappe đổi cơ-chế (đổi tên fn / bỏ System Setting) → test ĐỎ ⇒ buộc cập-nhật doc
        (doc-claim phải đồng-bộ source THẬT, KHÔNG được stale). Introspect bằng `inspect.getsource`
        (KHÔNG hardcode số dòng — robust với drift cosmetic)."""
        from frappe.utils import response as _frappe_resp

        self.assertTrue(
            hasattr(_frappe_resp, "is_traceback_allowed"),
            "@source: frappe.utils.response.is_traceback_allowed PHẢI tồn tại (doc-claim grounded).",
        )
        src = inspect.getsource(_frappe_resp.is_traceback_allowed)
        self.assertRegex(
            src,
            r"get_system_settings\(\s*['\"]allow_error_traceback['\"]\s*\)",
            "@source: is_traceback_allowed PHẢI đọc get_system_settings('allow_error_traceback') "
            "(gate = System Setting, KHÔNG developer_mode/site_config — nếu Frappe đổi → cập-nhật doc).",
        )

    # ── (5) RED-before/GREEN-after — chứng minh guard THẬT bắt drift ─────────
    def test_sec_05_red_before_inject_developer_mode_is_red(self):
        """RED-before/GREEN-after THẬT: text THẬT GREEN; string-mutate bản-sao
        ('System Setting'→'developer_mode' HOẶC xoá cụm phủ-định) → guard RAISE.

        Chứng minh guard bắt drift THẬT (KHÔNG pass-suông). Detector tái-dựng đúng 3 assert
        cốt-lõi của (1) trên một string in-memory (KHÔNG ghi file/DB)."""

        def _passes_08_invariant(sect: str) -> bool:
            return (
                ("allow_error_traceback" in sect)
                and ("System Setting" in sect)
                and bool(self._NEG_DEVMODE_RE.search(sect))
                and ("response.py:60" in sect)
            )

        real_sect = self._section(self.text_08, "## 4. Checklist Security Go-live", "## 6.")
        # GREEN: text THẬT pass.
        self.assertTrue(_passes_08_invariant(real_sect), "Control: text 08 THẬT phải pass invariant.")

        # RED-before A: drift gate-name 'System Setting' → 'developer_mode'
        # (xoá MỌI 'System Setting' để mô-phỏng doc nói sai gate).
        drifted_gate = real_sect.replace("System Setting", "developer_mode")
        self.assertFalse(
            _passes_08_invariant(drifted_gate),
            "RED-before: doc drift gate→developer_mode PHẢI bị guard bắt (anti-false-green).",
        )

        # RED-before B: xoá cụm phủ-định 'KHÔNG phải developer_mode / site_config'.
        dropped_neg = self._NEG_DEVMODE_RE.sub("", real_sect)
        self.assertFalse(
            _passes_08_invariant(dropped_neg),
            "RED-before: xoá cụm phủ-định PHẢI bị guard bắt (anti-false-green).",
        )


class TestSecGateNoTokenLeak(unittest.TestCase):
    """GUARD-6 — no-token-leak drift-guard (G-A3, EPIC-G G4 sub-condition (c)).

    Machine-check invariant "qr_token KHÔNG leak trong MVP read response" — SOURCE-GROUNDED
    + DOC-INVARIANT + RED-before/GREEN-after, introspection-only (STDLIB raw-text + inspect):

        (1) `api/imm00.py` @source: `def _strip_qr_token(doc)` pop `qr_token` TỒN TẠI +
            `get_asset` body `return _ok(_strip_qr_token(doc))` (derive-from-source @symbol —
            KHÔNG hardcode số dòng tuyệt-đối; anti stale-evidence: imm00 đổi → ĐỎ buộc cập-nhật).
        (2) `08 §5/T4` + `ACCEPTANCE-CHECKLIST GO-7/G4(c)` chứa prose phủ-định qr_token/token
            KHÔNG leak trong MVP read response.
        (3) RED-before/GREEN-after string-mutate bản-sao (xoá `_strip_qr_token` call / xoá
            `pop('qr_token')` / flip prose phủ-định) → guard RAISE; control THẬT sạch → GREEN
            (anti false-green LL-TEST-21).

    Doc/test introspection-only → git diff api/services/*.py + yaml-schema = TRỐNG
    (owner constraint EPIC-G G4). KHÔNG sửa api/*.py, KHÔNG migrate/reload.
    """

    # Regex phủ-định prose 'qr_token/token KHÔNG ... leak' — tolerant backtick/từ-chèn giữa
    # 'KHÔNG' và 'leak' (08 dùng 'KHÔNG chứa key `qr_token`'/'KHÔNG có key `qr_token`';
    # checklist dùng 'token/QR ... KHÔNG leak'). Bắt cả 2 chiều: (token..KHÔNG..leak/chứa)
    # và (KHÔNG..leak/chứa..token) — đủ rộng để khớp prose THẬT, đủ hẹp để flip phủ-định → miss.
    _NEG_TOKEN_LEAK_RE = re.compile(
        r"(qr_token|token).{0,80}?KH[ÔO]NG.{0,40}?(leak|chứa)"
        r"|KH[ÔO]NG.{0,40}?(leak|chứa).{0,80}?(qr_token|token)",
        re.IGNORECASE | re.DOTALL,
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from assetcore.api import imm00 as _imm00

        cls.imm00 = _imm00
        cls.strip_src = inspect.getsource(_imm00._strip_qr_token)
        cls.get_asset_src = inspect.getsource(_imm00.get_asset)
        cls.text_08 = _read(_DOC_08)
        cls.text_checklist = _read(_ACCEPTANCE_CHECKLIST)

    # ── (1) source-grounded @api/imm00.py ───────────────────────────────────
    def test_sec_06_strip_qr_token_grounded_at_source(self):
        """@source api/imm00.py: `def _strip_qr_token(doc)` TỒN TẠI + body pop `qr_token`
        (derive-from-source bằng inspect — KHÔNG hardcode số dòng; anti stale-evidence).

        Nếu ai xoá helper / đổi pop sang field khác → ĐỎ buộc cập-nhật doc-claim (no-raw-token
        ADR-001 §D4 rule 9 phải đồng-bộ source THẬT)."""
        self.assertTrue(
            hasattr(self.imm00, "_strip_qr_token"),
            "@source: api/imm00.py PHẢI có def _strip_qr_token (SSoT no-raw-token).",
        )
        self.assertRegex(
            self.strip_src,
            r"def _strip_qr_token\(\s*doc\s*\)",
            "@source: signature PHẢI là def _strip_qr_token(doc).",
        )
        self.assertRegex(
            self.strip_src,
            r"""doc\.pop\(\s*['"]qr_token['"]\s*,\s*None\s*\)""",
            "@source: _strip_qr_token PHẢI pop('qr_token', None) (strip khóa MỜ nội bộ).",
        )

    def test_sec_06_get_asset_returns_stripped(self):
        """@source api/imm00.py: thân `get_asset` chứa `return _ok(_strip_qr_token(doc))`
        (read MVP đi qua SSoT strip TRƯỚC khi rời BE — anti stale-evidence)."""
        self.assertRegex(
            self.get_asset_src,
            r"return\s+_ok\(\s*_strip_qr_token\(\s*doc\s*\)\s*\)",
            "@source: get_asset PHẢI return _ok(_strip_qr_token(doc)) — read MVP strip qr_token.",
        )

    # ── (2) docset prose invariant raw-text ─────────────────────────────────
    def test_sec_06_08_doc_no_token_leak_present(self):
        """08 §5 (gate G4 row (c)) + T4 chứa prose phủ-định 'qr_token/token KHÔNG leak/chứa'
        trong MVP read response (raw-text, derive-from-source — KHÔNG số dòng).

        Quét khối §5 ('## 5. Security gate' → '## 6.'/cuối) để tránh false-green do cụm trùng."""
        sect = self._section_08_gate()
        self.assertTrue(sect, "08: KHÔNG tìm thấy section §5 ('## 5. Security gate').")
        self.assertIn(
            "no-token-leak", sect, "08 §5 PHẢI có gate '(c) no-token-leak' (G4 sub-condition)."
        )
        self.assertIn("qr_token", sect, "08 §5 PHẢI nhắc tên field 'qr_token' (read response).")
        self.assertIn(
            "_strip_qr_token", sect, "08 §5 PHẢI neo evidence cơ-chế '_strip_qr_token' (@source)."
        )
        self.assertRegex(
            sect,
            self._NEG_TOKEN_LEAK_RE,
            "08 §5 PHẢI có prose phủ-định 'qr_token/token KHÔNG leak/chứa' trong read response.",
        )

    def test_sec_06_checklist_go7_g4c_present(self):
        """ACCEPTANCE-CHECKLIST: GO-7 ('no token-leak') + G4(c)-machine-checked row chứa
        assert qr_token/token KHÔNG leak trong read response (raw-text)."""
        # GO-7 row — '| GO-7 | **Security: no token-leak** | ...'.
        go7 = self._section(self.text_checklist, "| GO-7 |", "\n| GO-8 |")
        self.assertTrue(go7, "Checklist: KHÔNG tìm thấy row GO-7.")
        self.assertIn(
            "no token-leak", go7, "GO-7 PHẢI khẳng định 'no token-leak'."
        )
        self.assertIn("_strip_qr_token", go7, "GO-7 PHẢI neo cơ-chế '_strip_qr_token'.")
        self.assertRegex(
            go7,
            self._NEG_TOKEN_LEAK_RE,
            "GO-7 PHẢI có prose phủ-định 'qr_token/token KHÔNG leak'.",
        )
        # G4(c) machine-checked tick — G-A3 đánh dấu trong row G-A4 (security-gate guard).
        ga4 = self._section(self.text_checklist, "| G-A4 |", "\n| G-U1 |")
        self.assertTrue(ga4, "Checklist: KHÔNG tìm thấy row G-A4 (security-gate guard).")
        self.assertIn(
            "G4(c)",
            ga4,
            "G-A4 PHẢI ghi 'G4(c)' machine-checked (G-A3 GUARD-6 no-token-leak).",
        )
        self.assertIn(
            "GUARD-6",
            ga4,
            "G-A4 PHẢI nhắc GUARD-6 (TestSecGateNoTokenLeak) đã machine-check G4(c).",
        )

    @classmethod
    def _section_08_gate(cls):
        return cls._section(cls.text_08, "## 5. Security gate", "## 6.")

    @staticmethod
    def _section(text: str, start_marker: str, end_marker: str | None) -> str:
        """Cắt section [start_marker, end_marker) raw-text (derive-from-source, KHÔNG số dòng)."""
        i = text.find(start_marker)
        if i < 0:
            return ""
        j = text.find(end_marker, i + len(start_marker)) if end_marker else len(text)
        if j < 0:
            j = len(text)
        return text[i:j]

    # ── (3) RED-before/GREEN-after — chứng minh guard THẬT bắt drift ─────────
    def test_sec_06_red_before_inject_unstripped_response_is_red(self):
        """RED-before/GREEN-after THẬT (source-side): control = get_asset_src THẬT pass;
        mutate bản-sao xoá `_strip_qr_token` call (→ `return _ok(doc)`) HOẶC xoá pop('qr_token')
        → detector RED. Chứng minh guard bắt regress unstripped read (anti false-green)."""

        def _source_passes(get_src: str, strip_src: str) -> bool:
            return bool(
                re.search(
                    r"return\s+_ok\(\s*_strip_qr_token\(\s*doc\s*\)\s*\)", get_src
                )
            ) and bool(
                re.search(
                    r"""doc\.pop\(\s*['"]qr_token['"]\s*,\s*None\s*\)""", strip_src
                )
            )

        # GREEN: source THẬT pass.
        self.assertTrue(
            _source_passes(self.get_asset_src, self.strip_src),
            "Control: source imm00 THẬT phải pass invariant strip.",
        )
        # RED-before A: get_asset bỏ strip call → return _ok(doc) thô.
        unstripped = self.get_asset_src.replace(
            "return _ok(_strip_qr_token(doc))", "return _ok(doc)"
        )
        self.assertFalse(
            _source_passes(unstripped, self.strip_src),
            "RED-before: get_asset bỏ _strip_qr_token call PHẢI bị guard bắt (anti-false-green).",
        )
        # RED-before B: _strip_qr_token bỏ pop('qr_token') → leak.
        no_pop = re.sub(
            r"""doc\.pop\(\s*['"]qr_token['"]\s*,\s*None\s*\)""",
            "pass  # popped removed",
            self.strip_src,
        )
        self.assertFalse(
            _source_passes(self.get_asset_src, no_pop),
            "RED-before: _strip_qr_token bỏ pop('qr_token') PHẢI bị guard bắt (anti-false-green).",
        )

    def test_sec_06_red_before_flip_prose_negation_is_red(self):
        """RED-before/GREEN-after THẬT (doc-side): control = §5 THẬT pass phủ-định;
        flip prose 'KHÔNG ... chứa/leak' → bỏ 'KHÔNG' (khẳng-định LEAK) → detector RED.
        Chứng minh guard bắt doc drift phủ-định (anti false-green)."""
        real_sect = self._section_08_gate()
        # GREEN: §5 THẬT có phủ-định.
        self.assertRegex(
            real_sect,
            self._NEG_TOKEN_LEAK_RE,
            "Control: 08 §5 THẬT phải có prose phủ-định token-leak.",
        )
        # RED-before: flip phủ-định — xoá MỌI 'KHÔNG' (gồm biến thể 'KHONG') trong section.
        flipped = re.sub(r"KH[ÔO]NG", "", real_sect, flags=re.IGNORECASE)
        self.assertNotRegex(
            flipped,
            self._NEG_TOKEN_LEAK_RE,
            "RED-before: flip prose 'KHÔNG ... leak'→'... leak' PHẢI bị guard bắt (anti-false-green).",
        )

    def test_sec_06_green_after_control_real_source_is_green(self):
        """GREEN-after: tổng-hợp control THẬT (source + 2 doc) đồng-thời pass — chứng minh
        guard KHÔNG false-RED trên trạng-thái THẬT sạch (đối-trọng 2 RED-before trên)."""
        # Source side.
        self.assertRegex(
            self.get_asset_src, r"return\s+_ok\(\s*_strip_qr_token\(\s*doc\s*\)\s*\)"
        )
        self.assertRegex(
            self.strip_src, r"""doc\.pop\(\s*['"]qr_token['"]\s*,\s*None\s*\)"""
        )
        # Doc side: 08 §5 + checklist GO-7 cùng có prose phủ-định.
        self.assertRegex(self._section_08_gate(), self._NEG_TOKEN_LEAK_RE)
        go7 = self._section(self.text_checklist, "| GO-7 |", "\n| GO-8 |")
        self.assertRegex(go7, self._NEG_TOKEN_LEAK_RE)


class TestSecGateRateLimitHeaderDoc(unittest.TestCase):
    """GUARD-7 — rate-limit 429-header drift-guard (G-A5, EPIC-G G4 sub-condition (d)).

    Đóng invariant CUỐI chưa-guard của EPIC-G G4: "(d) 429 có `Retry-After` / `X-RateLimit-*`".
    (a)/(b)/(c) đã có GUARD-1/3/6; (d) trước G-A5 CHỈ prose + [HARD-STOP USER] curl, KHÔNG
    drift-guard. Machine-check xuyên SOURCE-GROUNDED (frappe `rate_limiter`) + DOC-INVARIANT
    (08 §5(d) + 10 §6.2 note 2) + RED-before/GREEN-after, introspection-only (STDLIB raw-text
    + `inspect`):

        (1) `frappe.rate_limiter.apply` @source (rate_limiter.py:16-20 = conf-gate): body chứa
            `frappe.conf.rate_limit` + gán `frappe.local.rate_limiter` → chứng minh CƠ-CHẾ THẬT:
            rate_limiter CHỈ instantiate khi `conf.rate_limit` set (anti stale-evidence: nếu Frappe
            đổi cơ-chế → ĐỎ buộc cập-nhật doc-KNOWN-clause).
        (2) `frappe.rate_limiter.RateLimiter.headers` @source (rate_limiter.py:82-92): body emit 3
            khóa `X-RateLimit-Reset/Limit/Remaining` LUÔN + `Retry-After` CHỈ dưới nhánh
            `if self.rejected:` → khẳng-định header-shape mà doc (d) claim.
        (3) `08 §5 (d)` row chứa `Retry-After` + `X-RateLimit-*` + KNOWN-clause 'CHỈ phát khi
            `conf.rate_limit`/nginx `limit_req` set' + `10 §6.2 note 2` chứa cùng KNOWN (body-only
            no-header khi `conf.rate_limit` vắng) — derive-from-source raw-text, KHÔNG số dòng.
        (4) RED-before/GREEN-after string-mutate bản-sao: xoá `frappe.conf.rate_limit` khỏi
            source-snippet HOẶC flip KNOWN-clause prose ('CHỈ phát khi'→'luôn phát') → guard RAISE;
            control THẬT → GREEN (anti false-green LL-TEST-21).

    Doc/test introspection-only → git diff api/services/*.py + yaml-schema = TRỐNG
    (owner constraint EPIC-G G4). KHÔNG sửa api/*.py, KHÔNG sửa frappe core, KHÔNG migrate/reload.
    HARD-STOP carry (G-U5): curl 429 THẬT trên public host (header Retry-After/X-RateLimit-* present)
    cần USER set `conf.rate_limit`/nginx `limit_req` + reload — KHÔNG tự-động-hóa được local.
    """

    # KNOWN-clause prose (08 §5 (d) + 10 §6.2 note 2): header rate-limit CHỈ phát khi conf set.
    # Tolerant backtick/space (08 dùng '`conf.rate_limit`/nginx'; 10 dùng '`conf.rate_limit` (`site_config`)').
    _KNOWN_CLAUSE_RE = re.compile(
        r"CHỈ phát khi\s*`?conf\.rate_limit`?", re.IGNORECASE
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from frappe import rate_limiter as _rl

        cls.rl = _rl
        cls.apply_src = inspect.getsource(_rl.apply)
        cls.headers_src = inspect.getsource(_rl.RateLimiter.headers)
        cls.text_08 = _read(_DOC_08)
        cls.text_10 = _read(_DOC_10)

    @staticmethod
    def _section(text: str, start_marker: str, end_marker: str | None) -> str:
        """Cắt section [start_marker, end_marker) raw-text (derive-from-source, KHÔNG số dòng)."""
        i = text.find(start_marker)
        if i < 0:
            return ""
        j = text.find(end_marker, i + len(start_marker)) if end_marker else len(text)
        if j < 0:
            j = len(text)
        return text[i:j]

    # ── (1) source-grounded @frappe.rate_limiter.apply (conf-gate :16-20) ────
    def test_sec_07_rate_limit_apply_conf_gated_at_source(self):
        """@source frappe.rate_limiter.apply: body chứa `frappe.conf.rate_limit` + gán
        `frappe.local.rate_limiter` (rate_limiter.py:17-20 = conf-gate).

        Chứng minh CƠ-CHẾ THẬT: rate_limiter CHỈ instantiate khi conf.rate_limit set → doc-KNOWN
        'header CHỈ phát khi conf.rate_limit set' là GROUNDED. Anti stale-evidence: nếu Frappe đổi
        gate (bỏ conf.rate_limit / đổi thuộc-tính) → ĐỎ buộc cập-nhật doc (derive-from-source bằng
        inspect — KHÔNG hardcode số dòng)."""
        self.assertIn(
            "frappe.conf.rate_limit",
            self.apply_src,
            "@source: rate_limiter.apply PHẢI đọc 'frappe.conf.rate_limit' (conf-gate :17).",
        )
        self.assertIn(
            "frappe.local.rate_limiter",
            self.apply_src,
            "@source: rate_limiter.apply PHẢI gán 'frappe.local.rate_limiter' (instantiate :19-20).",
        )
        # Gán PHẢI nằm trong nhánh `if rate_limit:` (conf-gated, KHÔNG vô-điều-kiện).
        self.assertRegex(
            self.apply_src,
            r"if\s+rate_limit\s*:",
            "@source: instantiate PHẢI conf-gated dưới 'if rate_limit:' (KHÔNG vô-điều-kiện).",
        )

    # ── (2) source-grounded @RateLimiter.headers (header-shape :82-92) ───────
    def test_sec_07_headers_emit_xratelimit_and_retry_after_at_source(self):
        """@source frappe.rate_limiter.RateLimiter.headers: emit 3 khóa `X-RateLimit-*` LUÔN +
        `Retry-After` CHỈ dưới nhánh `if self.rejected:` (rate_limiter.py:82-92).

        Khẳng-định header-shape mà 08 §5(d) claim. Anti stale-evidence: nếu Frappe đổi tên header /
        bỏ Retry-After-on-reject → ĐỎ buộc cập-nhật doc (derive-from-source bằng inspect)."""
        for key in ("X-RateLimit-Reset", "X-RateLimit-Limit", "X-RateLimit-Remaining"):
            self.assertIn(
                key,
                self.headers_src,
                f"@source: RateLimiter.headers PHẢI emit khóa '{key}' (:85-87).",
            )
        self.assertIn(
            "Retry-After",
            self.headers_src,
            "@source: RateLimiter.headers PHẢI emit 'Retry-After' (:90).",
        )
        # Retry-After PHẢI nằm SAU `if self.rejected:` (CHỈ khi rejected — backoff hint).
        rejected_idx = self.headers_src.find("if self.rejected")
        retry_idx = self.headers_src.find("Retry-After")
        self.assertGreaterEqual(
            rejected_idx, 0, "@source: headers PHẢI có nhánh 'if self.rejected:' (gate Retry-After)."
        )
        self.assertGreater(
            retry_idx,
            rejected_idx,
            "@source: 'Retry-After' PHẢI nằm SAU 'if self.rejected:' (CHỈ phát khi reject — :89-90).",
        )

    # ── (3) docset prose invariant raw-text ─────────────────────────────────
    def test_sec_07_08_doc_d_invariant_present(self):
        """08 §5 (d) row chứa `Retry-After` + `X-RateLimit-*` + KNOWN-clause
        'CHỈ phát khi `conf.rate_limit`' (raw-text, derive-from-source — KHÔNG số dòng).

        Quét khối §5 ('## 5. Security gate' → '## 6.') để tránh false-green do cụm trùng chỗ khác."""
        sect = self._section(self.text_08, "## 5. Security gate", "## 6.")
        self.assertTrue(sect, "08: KHÔNG tìm thấy section §5 ('## 5. Security gate').")
        self.assertIn(
            "Retry-After", sect, "08 §5(d) PHẢI nhắc header 'Retry-After' (429 backoff hint)."
        )
        self.assertIn(
            "X-RateLimit-*", sect, "08 §5(d) PHẢI nhắc 'X-RateLimit-*' (header-set kèm 429)."
        )
        self.assertRegex(
            sect,
            self._KNOWN_CLAUSE_RE,
            "08 §5(d) PHẢI có KNOWN-clause 'CHỈ phát khi `conf.rate_limit`' (header conf-gated).",
        )

    def test_sec_07_10_doc_known_clause_present(self):
        """10 §6.2 note 2 chứa KNOWN-clause body-only-no-header khi conf.rate_limit vắng:
        'Retry-After'/'X-RateLimit-*' + 'CHỈ phát khi `conf.rate_limit`' + 'body-only no-header'
        (raw-text). Quét khối §6.2 ('### 6.2 Execute' → '### 6.3')."""
        sect = self._section(self.text_10, "### 6.2 Execute", "### 6.3")
        self.assertTrue(sect, "10: KHÔNG tìm thấy section §6.2 ('### 6.2 Execute').")
        # Khoanh hẹp về note 2 — dòng '> 2. **Rate-limit header (429):**' tới hết khối note.
        note2 = self._section(sect, "**Rate-limit header (429):**", "### 6.3")
        self.assertTrue(note2, "10 §6.2: KHÔNG tìm thấy note 2 ('**Rate-limit header (429):**').")
        self.assertIn("Retry-After", note2, "10 §6.2 note 2 PHẢI nhắc 'Retry-After'.")
        for key in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
            self.assertIn(key, note2, f"10 §6.2 note 2 PHẢI liệt-kê '{key}' (header-set 429).")
        self.assertRegex(
            note2,
            self._KNOWN_CLAUSE_RE,
            "10 §6.2 note 2 PHẢI có KNOWN-clause 'CHỈ phát khi `conf.rate_limit`'.",
        )
        self.assertIn(
            "body-only no-header",
            note2,
            "10 §6.2 note 2 PHẢI nói 'body-only no-header' (decorator-429 trần khi conf vắng).",
        )

    # ── (4) RED-before/GREEN-after — chứng minh guard THẬT bắt drift ─────────
    def test_sec_07_red_before_remove_conf_gate_is_red(self):
        """RED-before/GREEN-after THẬT (source-side): control = apply_src THẬT pass conf-gate;
        mutate bản-sao xoá token `frappe.conf.rate_limit` → detector RED. Chứng minh guard bắt
        regress (Frappe đổi/bỏ conf-gate) — anti false-green."""

        def _source_passes(apply_src: str) -> bool:
            return (
                "frappe.conf.rate_limit" in apply_src
                and "frappe.local.rate_limiter" in apply_src
            )

        # GREEN: source THẬT pass.
        self.assertTrue(
            _source_passes(self.apply_src), "Control: rate_limiter.apply THẬT phải pass conf-gate."
        )
        # RED-before: xoá conf-gate token khỏi bản-sao (KHÔNG đụng frappe core).
        no_conf_gate = self.apply_src.replace("frappe.conf.rate_limit", "RATE_LIMIT_ALWAYS_ON")
        self.assertFalse(
            _source_passes(no_conf_gate),
            "RED-before: xoá 'frappe.conf.rate_limit' PHẢI bị guard bắt (anti-false-green).",
        )

    def test_sec_07_red_before_flip_known_clause_is_red(self):
        """RED-before/GREEN-after THẬT (doc-side): control = §5 THẬT pass KNOWN-clause;
        flip prose 'CHỈ phát khi'→'luôn phát' (mất conf-gate caveat) → detector RED.
        Chứng minh guard bắt doc drift KNOWN-clause (anti false-green)."""
        real_sect = self._section(self.text_08, "## 5. Security gate", "## 6.")
        # GREEN: §5 THẬT có KNOWN-clause.
        self.assertRegex(
            real_sect,
            self._KNOWN_CLAUSE_RE,
            "Control: 08 §5 THẬT phải có KNOWN-clause 'CHỈ phát khi conf.rate_limit'.",
        )
        # RED-before: flip 'CHỈ phát khi'→'luôn phát' (xoá conf-gate caveat → doc nói SAI cơ-chế).
        flipped = real_sect.replace("CHỈ phát khi", "luôn phát")
        self.assertNotRegex(
            flipped,
            self._KNOWN_CLAUSE_RE,
            "RED-before: flip 'CHỉ phát khi'→'luôn phát' PHẢI bị guard bắt (anti-false-green).",
        )

    def test_sec_07_green_after_control_real_source_is_green(self):
        """GREEN-after (source-side): control THẬT (apply + headers @source) đồng-thời pass —
        đối-trọng RED-before source. apply conf-gated + headers emit X-RateLimit-* + Retry-After
        dưới if self.rejected."""
        self.assertIn("frappe.conf.rate_limit", self.apply_src)
        self.assertIn("frappe.local.rate_limiter", self.apply_src)
        for key in ("X-RateLimit-Reset", "X-RateLimit-Limit", "X-RateLimit-Remaining"):
            self.assertIn(key, self.headers_src)
        self.assertGreater(
            self.headers_src.find("Retry-After"),
            self.headers_src.find("if self.rejected"),
            "Control: Retry-After PHẢI nằm SAU if self.rejected (@source).",
        )

    def test_sec_07_green_after_control_real_doc_is_green(self):
        """GREEN-after (doc-side): control THẬT (08 §5(d) + 10 §6.2 note 2) đồng-thời pass KNOWN-clause
        — đối-trọng RED-before doc. Chứng minh guard KHÔNG false-RED trên trạng-thái THẬT sạch."""
        sect_08 = self._section(self.text_08, "## 5. Security gate", "## 6.")
        self.assertRegex(sect_08, self._KNOWN_CLAUSE_RE)
        self.assertIn("Retry-After", sect_08)
        self.assertIn("X-RateLimit-*", sect_08)
        sect_10 = self._section(self.text_10, "### 6.2 Execute", "### 6.3")
        note2 = self._section(sect_10, "**Rate-limit header (429):**", "### 6.3")
        self.assertRegex(note2, self._KNOWN_CLAUSE_RE)
        self.assertIn("body-only no-header", note2)


class TestSecGateAuditActorNd98Doc(unittest.TestCase):
    """GUARD-8 — NĐ98 audit-actor drift-guard (G-A6, EPIC-G §6 LAST unguarded invariant).

    Đóng invariant CUỐI chưa-guard của EPIC-G §6 / `08 §2.2`: chuỗi
    `bearer → set_user(token.user) → log_audit_event(actor=session.user) → verify_audit_chain`
    đảm bảo audit NĐ98 ghi **actor = KTV thật** (KHÔNG service-account/Administrator). (a)/(b)/(c)/(d)
    đã có GUARD-1/3/6/7; invariant audit-actor NĐ98 (GO-8 / `08 §4 (verify)` / §5.3 / `10 §6.3
    (verify-audit)`) trước G-A6 CHỈ prose + '[verify khi có token thật Phase D]', KHÔNG drift-guard.

    Machine-check xuyên SOURCE-GROUNDED + DOC-INVARIANT + RED-before/GREEN-after, introspection-only
    (STDLIB raw-text + `inspect`):

        (1) `assetcore/utils/lifecycle.py` @source: `def log_audit_event` TỒN TẠI + thân chứa
            `actor = actor or frappe.session.user` (lifecycle.py:44 — actor mặc-định = session.user;
            derive-from-source `inspect.getsource`, KHÔNG hardcode số dòng tuyệt-đối; anti
            stale-evidence: lifecycle đổi → ĐỎ buộc cập-nhật doc-claim NĐ98).
        (2) `def verify_audit_chain` @source: thân chứa integrity-compare
            `expected != ... hash_sha256` AND `prev_hash` mismatch (lifecycle.py:110-111) — khẳng-định
            hash-chain bất biến + liên tục mà `08 §2.2` claim.
        (3) `frappe/auth.py` @source raw-text: chứa nguyên-văn
            `frappe.set_user(frappe.db.get_value("OAuth Bearer Token", token, "user"))` (auth.py:667)
            = bearer → KTV-thật (anti stale-evidence: Frappe đổi cơ-chế → ĐỎ buộc cập-nhật doc).
        (4) `08 §2.2` evidence-table raw-text chứa `set_user(token.user)` + `log_audit_event` +
            `frappe.session.user` + phủ-định `KHÔNG service-account`/`KHÔNG Administrator` + evidence
            `auth.py:667` + `lifecycle.py`; `08 §5.1` có hàng gate `(e) audit-actor`; `10 §6.3
            (verify-audit)` giữ `verify_audit_chain` + actor = user thật.
        (5) RED-before/GREEN-after string-mutate bản-sao: xoá `actor = actor or frappe.session.user`
            khỏi source-snippet / flip phủ-định `KHÔNG service-account`→`service-account` / xoá
            set_user-bearer token → guard RAISE; control THẬT → GREEN (anti false-green LL-TEST-21).

    Doc/test introspection-only → git diff api/services/*.py + yaml-schema = TRỐNG
    (owner constraint EPIC-G G4). KHÔNG sửa api/*.py, KHÔNG sửa frappe core, KHÔNG migrate/reload.
    HARD-STOP carry (G-U?): chạy `verify_audit_chain(asset)` THẬT trên cloud SAU 1 action-từ-mobile
    bằng bearer token KTV thật → assert valid=True + audit row actor == KTV thật (cần B-U1..U4 OAuth
    Client + bearer live + G1 deploy + migrate + reload) = live-part còn lại của GO-8 / `08 §2 (verify)`.
    """

    # Phủ-định prose 'actor = KTV thật, KHÔNG service-account/Administrator' (08 §2).
    # Tolerant: 'KHÔNG service-account' (28/75/104) + 'KHÔNG Administrator/service-account' (84).
    _NEG_SERVICE_ACCOUNT_RE = re.compile(
        r"KH[ÔO]NG\s+(?:Administrator\s*/\s*)?service-account|"
        r"KH[ÔO]NG\s+Administrator",
        re.IGNORECASE,
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from assetcore.utils import lifecycle as _lc

        cls.lifecycle = _lc
        cls.log_audit_src = inspect.getsource(_lc.log_audit_event)
        cls.verify_chain_src = inspect.getsource(_lc.verify_audit_chain)
        # frappe/auth.py raw-text (bearer→set_user @:667) — read_text STDLIB, KHÔNG hardcode số dòng.
        import frappe as _frappe

        cls.auth_path = Path(_frappe.__file__).resolve().parent / "auth.py"
        cls.auth_text = _read(cls.auth_path)
        cls.text_08 = _read(_DOC_08)
        cls.text_10 = _read(_DOC_10)

    @staticmethod
    def _section(text: str, start_marker: str, end_marker: str | None) -> str:
        """Cắt section [start_marker, end_marker) raw-text (derive-from-source, KHÔNG số dòng)."""
        i = text.find(start_marker)
        if i < 0:
            return ""
        j = text.find(end_marker, i + len(start_marker)) if end_marker else len(text)
        if j < 0:
            j = len(text)
        return text[i:j]

    # ── (1) source-grounded @lifecycle.log_audit_event (actor=session.user :44) ──
    def test_sec_gate_audit_actor_lifecycle_source_grounded(self):
        """@source assetcore/utils/lifecycle.py: `def log_audit_event` TỒN TẠI + thân chứa
        `actor = actor or frappe.session.user` (lifecycle.py:44 — actor mặc-định = session.user).

        Chứng minh CƠ-CHẾ THẬT: audit ghi actor = `frappe.session.user` (= KTV thật sau bearer
        set_user, KHÔNG service-account). Anti stale-evidence: nếu ai bỏ default-actor /
        đổi sang hằng → ĐỎ buộc cập-nhật doc-claim NĐ98 (`08 §2.2`). Derive-from-source
        bằng inspect — KHÔNG hardcode số dòng tuyệt-đối."""
        self.assertTrue(
            hasattr(self.lifecycle, "log_audit_event"),
            "@source: utils/lifecycle.py PHẢI có def log_audit_event (SSoT audit NĐ98).",
        )
        self.assertRegex(
            self.log_audit_src,
            r"actor\s*=\s*actor\s+or\s+frappe\.session\.user",
            "@source: log_audit_event PHẢI gán 'actor = actor or frappe.session.user' "
            "(actor mặc-định = KTV thật, lifecycle.py:44 — nếu drift → cập-nhật doc NĐ98).",
        )

    # ── (2) source-grounded @lifecycle.verify_audit_chain (integrity :110-111) ──
    def test_sec_gate_verify_audit_chain_integrity_source_grounded(self):
        """@source assetcore/utils/lifecycle.py: `def verify_audit_chain` TỒN TẠI + thân chứa
        integrity-compare `expected != ... hash_sha256` AND `prev_hash` mismatch (lifecycle.py:110-111).

        Khẳng-định hash-chain bất biến + liên-tục (mỗi record neo `prev_hash`→`hash_sha256`; sửa/xoá
        giữa chuỗi ⇒ phát hiện) mà `08 §2.2` claim. Anti stale-evidence: đổi cơ-chế kiểm → ĐỎ."""
        self.assertTrue(
            hasattr(self.lifecycle, "verify_audit_chain"),
            "@source: utils/lifecycle.py PHẢI có def verify_audit_chain (kiểm tính bất biến chain).",
        )
        self.assertRegex(
            self.verify_chain_src,
            r"expected\s*!=\s*\S*\.?hash_sha256",
            "@source: verify_audit_chain PHẢI so-sánh 'expected != ...hash_sha256' (integrity bất biến).",
        )
        self.assertIn(
            "prev_hash",
            self.verify_chain_src,
            "@source: verify_audit_chain PHẢI kiểm 'prev_hash' mismatch (liên-tục, KHÔNG xoá khoảng giữa).",
        )

    # ── (3) source-grounded @frappe/auth.py (bearer→set_user :667) ────────────
    def test_sec_gate_bearer_set_user_frappe_auth_grounded(self):
        """@source frappe/auth.py raw-text: chứa nguyên-văn
        `frappe.set_user(frappe.db.get_value("OAuth Bearer Token", token, "user"))` (auth.py:667)
        = bearer → KTV-thật (`frappe.session.user` = chính KTV, KHÔNG Administrator/service-account).

        Anti stale-evidence: Frappe đổi cơ-chế set_user-from-bearer → ĐỎ buộc cập-nhật doc
        (`08 §2.1/§2.2` evidence `auth.py:667`). Read_text STDLIB — KHÔNG hardcode số dòng tuyệt-đối."""
        self.assertTrue(self.auth_path.is_file(), f"@source: frappe/auth.py thiếu: {self.auth_path}")
        self.assertRegex(
            self.auth_text,
            r'frappe\.set_user\(\s*frappe\.db\.get_value\(\s*["\']OAuth Bearer Token["\']\s*,\s*token\s*,\s*["\']user["\']\s*\)\s*\)',
            "@source: auth.py PHẢI chứa set_user(get_value('OAuth Bearer Token', token, 'user')) "
            "(bearer → KTV thật — nếu Frappe đổi → cập-nhật doc evidence auth.py:667).",
        )

    # ── (4) docset prose invariant raw-text ─────────────────────────────────
    def test_sec_gate_doc_08_section2_2_actor_invariant_present(self):
        """08 §2.2 evidence-table raw-text chứa `set_user(token.user)` + `log_audit_event` +
        `frappe.session.user` + evidence `auth.py:667` + `lifecycle.py` (derive-from-source).

        Quét khối §2 ('## 2. NĐ98' → '## 3.') để tránh false-green do cụm trùng chỗ khác."""
        sect = self._section(self.text_08, "## 2. NĐ98", "## 3.")
        self.assertTrue(sect, "08: KHÔNG tìm thấy section §2 ('## 2. NĐ98').")
        self.assertIn(
            "set_user(token.user)", sect, "08 §2.2 PHẢI có 'set_user(token.user)' (bearer→KTV thật)."
        )
        self.assertIn(
            "log_audit_event", sect, "08 §2.2 PHẢI nhắc 'log_audit_event' (ghi audit actor=session.user)."
        )
        self.assertIn(
            "frappe.session.user", sect, "08 §2.2 PHẢI nhắc 'frappe.session.user' (= actor audit ghi)."
        )
        self.assertIn("auth.py:667", sect, "08 §2.2 PHẢI neo evidence 'auth.py:667' (@source set_user).")
        self.assertIn("lifecycle.py", sect, "08 §2.2 PHẢI neo evidence 'lifecycle.py' (@source log_audit).")

    def test_sec_gate_doc_08_negation_no_service_account_present(self):
        """08 §2 chứa phủ-định 'actor = KTV thật, KHÔNG service-account / KHÔNG Administrator'
        (actor KHÔNG phải gateway/service chung) — raw-text trong khối §2 ('## 2.' → '## 3.')."""
        sect = self._section(self.text_08, "## 2. NĐ98", "## 3.")
        self.assertTrue(sect, "08: KHÔNG tìm thấy section §2 ('## 2. NĐ98').")
        self.assertRegex(
            sect,
            self._NEG_SERVICE_ACCOUNT_RE,
            "08 §2 PHẢI có phủ-định 'KHÔNG service-account'/'KHÔNG Administrator' (actor = KTV thật).",
        )

    def test_sec_gate_doc_0851_gate_e_audit_actor_present(self):
        """08 §5.1 có hàng gate `(e) audit-actor` (G4 invariant audit-actor NĐ98) +
        `10 §6.3` giữ `(verify-audit)` + `verify_audit_chain` + actor = user thật (raw-text)."""
        # 08 §5.1 — gate (e) audit-actor.
        sect_08 = self._section(self.text_08, "### 5.1", "### 5.2")
        self.assertTrue(sect_08, "08: KHÔNG tìm thấy section §5.1.")
        self.assertIn(
            "(e)", sect_08, "08 §5.1 PHẢI có hàng gate '(e)' (audit-actor — invariant §6 mới)."
        )
        self.assertIn(
            "audit-actor", sect_08, "08 §5.1 PHẢI có gate '(e) audit-actor' (NĐ98 actor=KTV thật)."
        )
        self.assertIn(
            "verify_audit_chain",
            sect_08,
            "08 §5.1 (e) PHẢI nhắc cơ-chế 'verify_audit_chain' (kiểm chain @source).",
        )
        # 10 §6.3 — (verify-audit) giữ verify_audit_chain + actor = user thật.
        sect_10 = self._section(self.text_10, "### 6.3", None)
        self.assertTrue(sect_10, "10: KHÔNG tìm thấy section §6.3.")
        self.assertIn(
            "(verify-audit)", sect_10, "10 §6.3 PHẢI giữ '(verify-audit)' (smoke post-verify audit)."
        )
        self.assertIn(
            "verify_audit_chain", sect_10, "10 §6.3 (verify-audit) PHẢI nhắc 'verify_audit_chain'."
        )
        self.assertRegex(
            sect_10,
            r"actor\s*=\s*user thật",
            "10 §6.3 (verify-audit) PHẢI khẳng-định 'actor = user thật' (NĐ98 đúng actor).",
        )

    # ── (5) RED-before/GREEN-after — chứng minh guard THẬT bắt drift ─────────
    def test_sec_gate_red_before_inject_removes_session_user_is_red(self):
        """RED-before/GREEN-after THẬT (source-side): control = log_audit_src + auth_text THẬT pass;
        mutate bản-sao xoá `actor = actor or frappe.session.user` HOẶC xoá set_user-bearer token
        → detector RED. Chứng minh guard bắt regress (drift cơ-chế actor) — anti false-green."""

        _bearer_re = re.compile(
            r'frappe\.set_user\(\s*frappe\.db\.get_value\(\s*["\']OAuth Bearer Token["\']\s*,\s*token\s*,\s*["\']user["\']\s*\)\s*\)'
        )

        def _source_passes(log_src: str, auth_txt: str) -> bool:
            return bool(
                re.search(r"actor\s*=\s*actor\s+or\s+frappe\.session\.user", log_src)
            ) and bool(_bearer_re.search(auth_txt))

        # GREEN: source THẬT pass.
        self.assertTrue(
            _source_passes(self.log_audit_src, self.auth_text),
            "Control: source lifecycle+auth THẬT phải pass invariant audit-actor.",
        )
        # RED-before A: log_audit_event bỏ default-actor → actor KHÔNG còn = session.user.
        no_session = self.log_audit_src.replace(
            "actor = actor or frappe.session.user", 'actor = actor or "service-account"'
        )
        self.assertFalse(
            _source_passes(no_session, self.auth_text),
            "RED-before: bỏ 'actor = actor or frappe.session.user' PHẢI bị guard bắt (anti-false-green).",
        )
        # RED-before B: auth.py bỏ set_user-bearer → bearer KHÔNG còn map KTV thật.
        no_bearer = _bearer_re.sub("pass  # set_user removed", self.auth_text)
        self.assertFalse(
            _source_passes(self.log_audit_src, no_bearer),
            "RED-before: xoá set_user-bearer token PHẢI bị guard bắt (anti-false-green).",
        )

    def test_sec_gate_red_before_flip_service_account_negation_is_red(self):
        """RED-before/GREEN-after THẬT (doc-side): control = §2 THẬT pass phủ-định;
        flip prose 'KHÔNG service-account'→'service-account' (mất phủ-định → doc nói SAI: actor
        có thể là service-account) → detector RED. Chứng minh guard bắt doc drift (anti false-green)."""
        real_sect = self._section(self.text_08, "## 2. NĐ98", "## 3.")
        # GREEN: §2 THẬT có phủ-định.
        self.assertRegex(
            real_sect,
            self._NEG_SERVICE_ACCOUNT_RE,
            "Control: 08 §2 THẬT phải có phủ-định 'KHÔNG service-account'.",
        )
        # RED-before: flip phủ-định — xoá MỌI 'KHÔNG' (gồm biến thể 'KHONG') trong section.
        flipped = re.sub(r"KH[ÔO]NG", "", real_sect, flags=re.IGNORECASE)
        self.assertNotRegex(
            flipped,
            self._NEG_SERVICE_ACCOUNT_RE,
            "RED-before: flip 'KHÔNG service-account'→'service-account' PHẢI bị guard bắt (anti-false-green).",
        )


class TestSecGateHostNameIssuerDoc(unittest.TestCase):
    """GUARD-9 — host_name/issuer go-live drift-guard (G-A8, EPIC-G §8 R4 / G4 (f)).

    Đóng invariant CUỐI chưa-guard của KNOB-MATRIX (5 knob): "knob #1 `host_name` set ⇒
    `get_url()` + OIDC `openid_configuration issuer == public host`, KHÔNG `http://miyano`
    nội bộ" (flow-2 QR deep-link + OIDC issuer reachability). 4/5 knob đã có guard:
    CORS-wildcard=GUARD-3, traceback=GUARD-5, rate-limit-header=GUARD-7, token-leak/audit=
    GUARD-6/8; host_name = LAST knob 0 guard-hit @source trước G-A8.

    Machine-check xuyên SOURCE-GROUNDED (`frappe/utils/data.py get_url`) + DOC-INVARIANT
    (08 §5.1(f) / 10 §3·§6.2·§6.3 / EPIC-G §3.3·§8 R4) + RED-before/GREEN-after,
    introspection-only (STDLIB raw-text + `inspect`):

        (1) `frappe.utils.data.get_url` @source: thân chứa
            `host_name = ...conf.host_name or ...conf.hostname` (data.py:1605 = host_name gate)
            + fallback `host_name = protocol + ...site` (data.py:1631 = `http://miyano` nội bộ khi
            host_name vắng). Chứng minh CƠ-CHẾ THẬT: get_url đọc conf.host_name; vắng ⇒ fallback
            protocol+site nội bộ. Anti stale-evidence: Frappe đổi gate (bỏ host_name / đổi fallback)
            → ĐỎ buộc cập-nhật doc (derive-from-source `inspect.getsource`, KHÔNG hardcode số dòng).
        (2) `08 §5.1 (f)` gate row + `10 §3` (knob + invariant note) + `10 §6.2` checklist item
            `(3c0)` + `10 §6.3 (verify-host)` + `EPIC-G §3.3` knob table + `EPIC-G §8 R4` — mỗi nơi
            chứa `host_name` + `get_url()`/`openid_configuration issuer == public host` + phủ-định
            `KHÔNG http://miyano` (raw-text derive-from-source, KHÔNG số dòng tuyệt-đối).
        (3) RED-before/GREEN-after string-mutate bản-sao: xoá `host_name = ...conf.host_name`
            khỏi source-snippet HOẶC flip prose phủ-định (`KHÔNG ...http://miyano`→bỏ `http://miyano`)
            → guard RAISE; control THẬT → GREEN (anti false-green LL-TEST-21).

    Doc/test introspection-only → git diff api/services/*.py + yaml-schema = TRỐNG
    (owner constraint EPIC-G G4). KHÔNG sửa api/*.py, KHÔNG sửa frappe core, KHÔNG migrate/reload.
    HARD-STOP carry (G-U2/G-U6): `get_url()` == public host + curl `openid_configuration issuer ==
    public host` THẬT trên cloud cần USER set `site_config.host_name` + reverse-proxy + reload —
    KHÔNG tự-động-hóa được local (host_name dev = ABSENT → fallback `http://miyano`).
    """

    # Phủ-định prose 'KHÔNG ... http://miyano' (08 §5.1(f) + 10 §3/§6.2/§6.3 + EPIC-G §8 R4).
    # Tolerant backtick/từ-chèn giữa 'KHÔNG' và 'http://miyano' (vd 'KHÔNG `http://miyano` nội bộ').
    _NEG_MIYANO_RE = re.compile(
        r"KH[ÔO]NG.{0,40}?`?http://miyano", re.IGNORECASE | re.DOTALL
    )
    # 'issuer == public host' tolerant '·' / backtick / khoảng-trắng (08/10/EPIC-G dùng
    # 'openid_configuration issuer == public host' và 'issuer == public host').
    _ISSUER_PUBLIC_RE = re.compile(r"issuer\s*==\s*public host", re.IGNORECASE)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from frappe.utils import data as _fdata

        cls.fdata = _fdata
        cls.get_url_src = inspect.getsource(_fdata.get_url)
        cls.text_08 = _read(_DOC_08)
        cls.text_10 = _read(_DOC_10)
        cls.text_epicg = _read(_EPIC_G)

    @staticmethod
    def _section(text: str, start_marker: str, end_marker: str | None) -> str:
        """Cắt section [start_marker, end_marker) raw-text (derive-from-source, KHÔNG số dòng)."""
        i = text.find(start_marker)
        if i < 0:
            return ""
        j = text.find(end_marker, i + len(start_marker)) if end_marker else len(text)
        if j < 0:
            j = len(text)
        return text[i:j]

    # ── (1) source-grounded @frappe.utils.data.get_url (host_name gate :1605/:1631) ──
    def test_sec_09_get_url_host_name_grounded_at_source(self):
        """@source frappe.utils.data.get_url: thân chứa
        `host_name = ...conf.host_name or ...conf.hostname` (data.py:1605 = host_name gate).

        Chứng minh CƠ-CHẾ THẬT: get_url đọc conf.host_name → doc-claim 'host_name gate get_url' là
        GROUNDED. Anti stale-evidence: nếu Frappe đổi gate (bỏ conf.host_name) → ĐỎ buộc cập-nhật
        doc (derive-from-source `inspect.getsource` — KHÔNG hardcode số dòng tuyệt-đối)."""
        self.assertTrue(
            hasattr(self.fdata, "get_url"),
            "@source: frappe.utils.data.get_url PHẢI tồn tại (host_name gate grounded).",
        )
        self.assertRegex(
            self.get_url_src,
            r"host_name\s*=\s*\S*conf\.host_name\s+or\s+\S*conf\.hostname",
            "@source: get_url PHẢI gán 'host_name = ...conf.host_name or ...conf.hostname' "
            "(data.py:1605 — gate host_name; nếu Frappe đổi → cập-nhật doc).",
        )

    def test_sec_09_get_url_fallback_internal_site_at_source(self):
        """@source frappe.utils.data.get_url: fallback `host_name = protocol + ...site`
        (data.py:1631 = host nội bộ khi conf.host_name vắng ⇒ `http://miyano`).

        Khẳng-định cơ-chế mà doc claim: host_name vắng ⇒ fallback protocol+site nội bộ. Anti
        stale-evidence: Frappe đổi fallback → ĐỎ buộc cập-nhật doc-claim."""
        self.assertRegex(
            self.get_url_src,
            r"host_name\s*=\s*protocol\s*\+\s*\S*site",
            "@source: get_url PHẢI có fallback 'host_name = protocol + ...site' "
            "(data.py:1631 — host nội bộ khi conf.host_name vắng ⇒ http://miyano).",
        )

    # ── (2) docset prose invariant raw-text ─────────────────────────────────
    def test_sec_09_doc_10_section3_host_invariant_present(self):
        """10 §3 (knob row + invariant note) chứa `host_name` + `get_url()` +
        `openid_configuration issuer == public host` + phủ-định 'KHÔNG `http://miyano`'
        (raw-text, derive-from-source — KHÔNG số dòng).

        Quét khối §3 ('## 3.' → '## 4.') để tránh false-green do cụm trùng chỗ khác."""
        sect = self._section(self.text_10, "## 3. §3", "## 4. §4")
        self.assertTrue(sect, "10: KHÔNG tìm thấy section §3 ('## 3. §3').")
        self.assertIn("host_name", sect, "10 §3 PHẢI nhắc knob 'host_name'.")
        self.assertIn("get_url()", sect, "10 §3 PHẢI nhắc cơ-chế 'get_url()' (@source data.py:1605).")
        self.assertRegex(
            sect,
            self._ISSUER_PUBLIC_RE,
            "10 §3 PHẢI khẳng-định 'openid_configuration issuer == public host'.",
        )
        self.assertRegex(
            sect,
            self._NEG_MIYANO_RE,
            "10 §3 PHẢI có phủ-định 'KHÔNG `http://miyano`' nội bộ (invariant host_name).",
        )

    def test_sec_09_doc_10_section62_checklist_host_present(self):
        """10 §6.2 checklist item `(3c0)` chứa `host_name` + `get_url()`/issuer + phủ-định
        'KHÔNG `http://miyano`' (raw-text). Quét khối §6.2 ('### 6.2 Execute' → '### 6.3')."""
        sect = self._section(self.text_10, "### 6.2 Execute", "### 6.3")
        self.assertTrue(sect, "10: KHÔNG tìm thấy section §6.2 ('### 6.2 Execute').")
        item = self._section(sect, "**(3c0)**", "**(3c)**")
        self.assertTrue(item, "10 §6.2: KHÔNG tìm thấy checklist item '(3c0)' (host_name).")
        self.assertIn("host_name", item, "10 §6.2 (3c0) PHẢI nhắc 'host_name'.")
        self.assertRegex(
            item,
            self._ISSUER_PUBLIC_RE,
            "10 §6.2 (3c0) PHẢI khẳng-định 'openid_configuration issuer == public host'.",
        )
        self.assertRegex(
            item,
            self._NEG_MIYANO_RE,
            "10 §6.2 (3c0) PHẢI có phủ-định 'KHÔNG `http://miyano`' nội bộ.",
        )

    def test_sec_09_doc_08_gate_f_host_issuer_present(self):
        """08 §5.1 có hàng gate `(f)` host_name/issuer go-live: `host_name` + `get_url()` +
        `openid_configuration issuer == public host` + phủ-định 'KHÔNG `http://miyano`'
        (raw-text). Quét khối §5.1 ('### 5.1' → '### 5.2')."""
        sect = self._section(self.text_08, "### 5.1", "### 5.2")
        self.assertTrue(sect, "08: KHÔNG tìm thấy section §5.1.")
        self.assertIn("(f)", sect, "08 §5.1 PHẢI có hàng gate '(f)' (host_name/issuer go-live).")
        self.assertIn(
            "host_name/issuer", sect, "08 §5.1 (f) PHẢI ghi gate 'host_name/issuer go-live'."
        )
        self.assertIn("get_url()", sect, "08 §5.1 (f) PHẢI nhắc 'get_url()' (@source data.py:1605).")
        self.assertRegex(
            sect,
            self._ISSUER_PUBLIC_RE,
            "08 §5.1 (f) PHẢI khẳng-định 'openid_configuration issuer == public host'.",
        )
        self.assertRegex(
            sect,
            self._NEG_MIYANO_RE,
            "08 §5.1 (f) PHẢI có phủ-định 'KHÔNG `http://miyano`' nội bộ.",
        )

    def test_sec_09_epicg_section33_section8_r4_host_invariant_present(self):
        """EPIC-G §3.3 (knob table host_name row) + §8 R4 chứa `host_name` + `get_url()` +
        phủ-định/đối-lập `http://miyano` nội bộ (raw-text). Neo cross-ref GUARD-9."""
        # §3.3 knob table — host_name row (khối '### 3.3' → '### 3.4'/'## 4.').
        sect_33 = self._section(self.text_epicg, "### 3.3", "## 4. Tasks")
        self.assertTrue(sect_33, "EPIC-G: KHÔNG tìm thấy section §3.3.")
        self.assertIn("host_name", sect_33, "EPIC-G §3.3 PHẢI có knob 'host_name'.")
        self.assertIn(
            "http://miyano", sect_33, "EPIC-G §3.3 PHẢI nhắc đối-lập nội bộ 'http://miyano'."
        )
        # §8 R4 row.
        sect_r4 = self._section(self.text_epicg, "| R4 |", "| R5 |")
        self.assertTrue(sect_r4, "EPIC-G: KHÔNG tìm thấy row §8 R4.")
        self.assertIn("host_name", sect_r4, "EPIC-G §8 R4 PHẢI nhắc 'host_name'.")
        self.assertIn("get_url()", sect_r4, "EPIC-G §8 R4 PHẢI nhắc 'get_url()'.")
        self.assertIn(
            "http://miyano", sect_r4, "EPIC-G §8 R4 PHẢI nhắc đối-lập nội bộ 'http://miyano'."
        )

    # ── (3) RED-before/GREEN-after — chứng minh guard THẬT bắt drift ─────────
    def test_sec_09_red_before_remove_host_name_gate_at_source_is_red(self):
        """RED-before/GREEN-after THẬT (source-side): control = get_url_src THẬT pass host_name gate;
        mutate bản-sao xoá `host_name = ...conf.host_name` → detector RED. Chứng minh guard bắt
        regress (Frappe đổi/bỏ host_name gate) — anti false-green."""

        _gate_re = re.compile(
            r"host_name\s*=\s*\S*conf\.host_name\s+or\s+\S*conf\.hostname"
        )

        def _source_passes(src: str) -> bool:
            return bool(_gate_re.search(src)) and bool(
                re.search(r"host_name\s*=\s*protocol\s*\+\s*\S*site", src)
            )

        # GREEN: source THẬT pass.
        self.assertTrue(
            _source_passes(self.get_url_src), "Control: get_url THẬT phải pass host_name gate."
        )
        # RED-before: xoá host_name gate-line khỏi bản-sao (KHÔNG đụng frappe core).
        no_gate = _gate_re.sub("host_name = HOST_HARDCODED", self.get_url_src)
        self.assertFalse(
            _source_passes(no_gate),
            "RED-before: xoá 'host_name = ...conf.host_name' PHẢI bị guard bắt (anti-false-green).",
        )

    def test_sec_09_red_before_flip_no_miyano_negation_is_red(self):
        """RED-before/GREEN-after THẬT (doc-side): control = 08 §5.1(f) THẬT pass phủ-định;
        flip prose 'KHÔNG `http://miyano`' → bỏ `http://miyano` (khẳng-định DÙNG internal host)
        → detector RED. Chứng minh guard bắt doc drift phủ-định (anti false-green)."""
        real_sect = self._section(self.text_08, "### 5.1", "### 5.2")
        # GREEN: §5.1 THẬT có phủ-định.
        self.assertRegex(
            real_sect,
            self._NEG_MIYANO_RE,
            "Control: 08 §5.1 THẬT phải có phủ-định 'KHÔNG `http://miyano`'.",
        )
        # RED-before: xoá MỌI 'http://miyano' khỏi section (mất anchor phủ-định).
        flipped = real_sect.replace("http://miyano", "<public-host>")
        self.assertNotRegex(
            flipped,
            self._NEG_MIYANO_RE,
            "RED-before: bỏ 'http://miyano' (mất phủ-định nội bộ) PHẢI bị guard bắt (anti-false-green).",
        )


class TestSecGateSelfCount(unittest.TestCase):
    """TC-MOB-SEC-10 — meta-guard self-verify (anti count-drift, analog F-C3).

    Introspect MỌI TestCase trong module này, đếm `test*` method, assert ==
    `_EXPECTED_SECURITY_GATE_TEST_COUNT`. Nếu ai thêm/xoá test (hoặc dup-name nuốt
    test âm thầm) mà KHÔNG cập nhật SSoT → ĐỎ ⇒ buộc xác nhận. Bản thân method này
    KHÔNG khớp prefix 'test_sec_' nên KHÔNG tự-đếm-trùng (vẫn là 1 test* → đã gộp vào SSoT).
    """

    def test_sec_10_module_test_count_matches_ssot(self):
        import sys

        module = sys.modules[__name__]
        count = 0
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, unittest.TestCase) and obj.__module__ == __name__:
                count += sum(1 for m in dir(obj) if m.startswith("test"))
        self.assertEqual(
            count,
            _EXPECTED_SECURITY_GATE_TEST_COUNT,
            f"Số test* ({count}) lệch SSoT ({_EXPECTED_SECURITY_GATE_TEST_COUNT}). "
            f"Nếu thêm/bớt test CÓ Ý → cập nhật _EXPECTED_SECURITY_GATE_TEST_COUNT.",
        )


if __name__ == "__main__":
    unittest.main()
