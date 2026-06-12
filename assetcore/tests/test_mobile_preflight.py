"""TC-MOB-PRE-01..26 — Drift-guard + behaviour cho Phase-B pre-flight verifier (B0-PREFLIGHT).

Sáu nhóm test:

A. DRIFT-GUARD (doc ↔ doctype @source) — bảo vệ prose field-spec `docs/mobile/03-auth-oauth2.md §4`
   KHỚP doctype `OAuth Client` THẬT của Frappe. Nếu Frappe đổi schema (đổi options Select,
   bỏ field, đổi reqd) → test ĐỎ ⇒ doc KHÔNG drift âm thầm. Đọc meta runtime (read-only).
     - TC-MOB-PRE-01: 10 fieldname B-1 TỒN TẠI trên meta OAuth Client.
     - TC-MOB-PRE-02: grant_type options == 'Authorization Code\\nImplicit' (verifier kỳ vọng
       'Authorization Code' là 1 lựa chọn hợp lệ).
     - TC-MOB-PRE-03: response_type options == 'Code\\nToken' (verifier kỳ vọng 'Code').
     - TC-MOB-PRE-04: app_name/scopes/default_redirect_uri reqd == 1 (doc §4 đánh ✅).
     - TC-MOB-PRE-05: allowed_roles fieldtype == 'Table MultiSelect', options == 'OAuth Client Role'.

B. VERIFIER BEHAVIOUR — `verify_oauth_client()` READ-ONLY + chịu count==0 + không raise nghiệp vụ.
     - TC-MOB-PRE-06: shape report đủ khoá (ready/client_count/checks/blockers/checked_client);
       mỗi check có field/expected/actual/pass.
     - TC-MOB-PRE-07: với client_count==0 (hiện trạng thật @source) → ready==False +
       blocker chứa 'Chưa có OAuth Client' + KHÔNG raise + checked_client is None.
     - TC-MOB-PRE-08: 7 điều kiện B-1 đều xuất hiện trong checks (client_count + 6 cấp-record)
       — kiểm bằng record giả lập (mock) ĐỦ field hợp lệ → ready==True, 0 blocker; rồi 1 field
       sai → ready==False + đúng blocker. (mock thuần in-memory, KHÔNG ghi DB.)
     - TC-MOB-PRE-09: verifier KHÔNG ghi DB — `frappe.db.count(OAuth Client)` bất biến trước/sau gọi.

C. DOC-VALUE PARITY (3-source value-constant drift-guard — F-B3, B1 acceptance #2 machine-check) —
   bảo vệ rằng **giá trị literal** của 4 hằng `preflight.EXPECTED_*` (+ `skip_authorization=0`)
   xuất hiện NGUYÊN-VĂN ở CẢ HAI doc nguồn: prose field-spec `03-auth-oauth2.md §4` (bảng field) VÀ
   runbook thực thi `10-deploy-ops.md §1` step1. Nhóm A chỉ chốt OPTIONS hợp lệ (constant ∈ options);
   nhóm C chốt VALUE prescribe == constant code, nên doc-text KHÔNG drift khỏi SSoT mã (preflight.py)
   và runbook KHỚP field-spec (B1 acceptance #2). STDLIB-only (Path.read_text), KHÔNG DB.
     - TC-MOB-PRE-10: 03 §4 chứa nguyên-văn EXPECTED_REDIRECT_URI + EXPECTED_SCOPES.
     - TC-MOB-PRE-11: 03 §4 chứa EXPECTED_GRANT_TYPE + EXPECTED_RESPONSE_TYPE (value 'Code') + skip_authorization value '0'.
     - TC-MOB-PRE-12: 10 §1 step1 chứa cùng 4 literal + skip_authorization=0 (runbook ↔ 03 §4 parity).
     - TC-MOB-PRE-13: RED-before/GREEN-after THẬT — bản-sao doc đổi 1 literal (HOẶC monkeypatch
       EXPECTED_SCOPES) → guard RED (assertion fail); giá-trị THẬT → GREEN. Chứng minh guard bắt drift
       (chống false-green). KHÔNG sửa file doc / preflight.py thật.

D. REPORT-SHAPE PARITY (doc↔code report-shape drift-guard — F-B4, B1/B4 acceptance #3 machine-check) —
   bảo vệ rằng **report-shape** verifier (12 §1.2 = 5 report-key của `verify_oauth_client()`) VÀ
   **7 check-field-name** (12 §1.3 = `client_count` ∪ 6 field cấp-record `_evaluate_client`) được mô tả
   ĐÚNG-VÀ-ĐỦ trong doc 12. Expected-set DERIVE TỪ `preflight.py` runtime (KHÔNG hardcode literal trong
   assert) → nếu preflight đổi/thêm/bớt field hoặc report-key mà 12 §1.2/§1.3 KHÔNG cập nhật → test ĐỎ.
   Cùng pattern STDLIB-only (Path.read_text + `_section`) như nhóm C; KHÔNG DB-write, KHÔNG lib mới.
     - TC-MOB-PRE-14: mọi 7 check-field-name (6 field từ `_evaluate_client(valid, allowed_roles_count=1)`
       ∪ `client_count`) xuất-hiện dạng `<field>` (backtick) trong region 12 §1.3 ('### 1.3' → '## 2.').
     - TC-MOB-PRE-15: mọi 5 report-key (ready/client_count/checks/blockers/checked_client từ output
       `verify_oauth_client()` nhánh count==0) xuất-hiện dạng `<key>` trong region 12 §1.2 ('### 1.2' → '### 1.3').
     - TC-MOB-PRE-16: blocker VI count==0 'Chưa có OAuth Client' (preflight.py:183) xuất-hiện nguyên-văn
       trong 12 (§1.2 JSON ví dụ HOẶC §3.2) — chống drift thông-điệp go/no-go operator-facing khỏi code.
     - TC-MOB-PRE-17: RED-before/GREEN-after THẬT — GREEN doc thật pass; RED-A bản-sao §1.3 xoá 1 field-name
       in-memory → guard RAISE; RED-B bản-sao §1.2 xoá 1 report-key in-memory → RAISE; khôi phục → GREEN
       (chống false-green, no side-effect). KHÔNG sửa file doc / preflight.py thật.

E. BLOCKER-VI REMEDIATION PARITY (doc↔code record-level blocker drift-guard — F-B5, B1/B4 acceptance #4
   machine-check) — bảo vệ rằng **bảng khắc phục operator-facing** 12 §3.3 (hợp đồng B4 dựa vào: 'đọc
   blockers VI → sửa record') liệt kê ĐỦ **CẢ 6** record-level blocker mà `_evaluate_client()` phát
   (grant_type/response_type/default_redirect_uri/scopes/skip_authorization/allowed_roles — preflight.py
   ~:91/99/115/124/132/139), KHÔNG chỉ 3 ví dụ tay-chép. Stem kỳ-vọng DERIVE TỪ runtime
   `_evaluate_client(<client cố-ý-sai>, allowed_roles_count=0)` (KHÔNG hardcode literal) → nếu preflight
   reword bất kỳ blocker nào mà §3.3 KHÔNG cập nhật → test ĐỎ (chống stale-remediation âm thầm). F-B4
   test_16 đã guard riêng blocker count==0 ('Chưa có OAuth Client'); F-B5 KHÔNG re-guard count==0.
   Cùng pattern STDLIB-only (Path.read_text + `_section`); KHÔNG DB-write, KHÔNG lib mới.
     - TC-MOB-PRE-18: `_evaluate_client(invalid, allowed_roles_count=0)` trả ĐÚNG 6 record-level blocker;
       derive 6 stem VI ổn-định từ runtime (cắt trước marker nội-suy ' — hiện[ default]:'), KHÔNG hardcode.
     - TC-MOB-PRE-19: region 12 §3.3 ('### 3.3' → '## 4.'/'---') chứa NGUYÊN-VĂN CẢ 6 stem derive (bảng
       khắc phục ĐỦ, không chỉ 3 ví dụ).
     - TC-MOB-PRE-20: §3.3 framing SSoT-derived — chứa sync-note + 6 tên field OAuth Client
       (grant_type/response_type/default_redirect_uri/scopes/skip_authorization/allowed_roles) + trỏ
       field-spec 03 §4 (mỗi dòng fix-action tham chiếu spec, KHÔNG prose lặp).
     - TC-MOB-PRE-21: RED-before/GREEN-after THẬT — GREEN doc thật pass; RED-A bản-sao §3.3 xoá 1 stem
       in-memory → guard RAISE; RED-B monkeypatch 1 blocker-string preflight (in-memory) sang stem VẮNG
       khỏi doc → guard RAISE (chứng minh derive-from-source bắt reword-drift, không false-green); khôi
       phục. KHÔNG sửa file doc / preflight.py thật.

F. STALE-LINE-REF RECONCILIATION (doc-region §3.4 EPIC-B-auth ↔ source — F-B7, analog F-C4
   `test_mob_oas_29c` @test_mobile_oas) — vùng `[SUPERSEDED]` §3.4 của
   `EPIC-B-auth-provisioning.md` (snapshot device-token 2026-06-11) từng tham-chiếu source bằng
   số-dòng TUYỆT-ĐỐI `test_mobile_oas.py:222`/`:108-109`/`:114-115`/`:641` cho `_STUB_PATHS`/
   path-map/operationId/names-frozen — đã CHẾT do line-drift (`_STUB_PATHS=set()` nay @:225,
   `test_mob_oas_06_device_token_names_frozen` nay @:850). Guard chốt §3.4 KHÔNG còn line-ref
   tuyệt-đối kiểu `test_mobile_oas.py:<digit>` (chỉ chấp dạng-SYMBOL), GIỮ nguyên nội-dung
   `[SUPERSEDED]` (audit-trail) — chỉ đổi CÁCH tham-chiếu. STDLIB-only (Path.read_text + re),
   KHÔNG DB, KHÔNG lib mới.
     - TC-MOB-PRE-23a: region §3.4 KHÔNG chứa pattern `test_mobile_oas.py:<digit>` (absolute-line)
       cho _STUB_PATHS/path-map/names-frozen — GREEN sau reconcile.
     - TC-MOB-PRE-23b: §3.4 chứa NGUYÊN-VĂN dạng-SYMBOL `_STUB_PATHS = set()` + `_DEVICE_TOKEN_FROZEN`
       + tên test `test_mob_oas_06_device_token_names_frozen` (ref bằng symbol/tên, KHÔNG số-dòng).
     - TC-MOB-PRE-23c (RED-before): inject bản-sao IN-MEMORY region có `test_mobile_oas.py:999` →
       guard PHẢI RAISE (chống false-green).
     - TC-MOB-PRE-23d (GREEN-after/control): region THẬT đã reconcile → guard pass, KHÔNG raise.

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_preflight
"""
from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import frappe

from assetcore.api.mobile import preflight

OAUTH_CLIENT = "OAuth Client"

# ── F-B6 (2026-06-12, EPIC-B) — META-GUARD count-self-verify SSoT (analog F-C3 @test_mobile_oas) ──
# SSoT con-số test-method của CHÍNH module này, định-nghĩa MỘT LẦN @đầu module. Meta-guard
# `TestMobilePreflightCountSelfVerify.test_22_count_matches_ssot` introspect MỌI `unittest.TestCase`
# định-nghĩa TRONG module + đếm method `test*` LOAD ĐƯỢC rồi assert == hằng này. Drift sau-này
# (thêm/bớt TC mà quên cập const) = RED NGAY — chống tái count-drift đúng kiểu 13->17->21 đã xảy ra.
# Đây là count-AFTER-add (gồm CHÍNH meta-guard TC-MOB-PRE-22). F-B7 (2026-06-12) +4 TC class
# `TestMobilePreflightDocLineRefReconciled` (TC-MOB-PRE-23a..d — stale-line-ref guard §3.4 EPIC-B-auth)
# ⇒ 22→26. Doc count-hiện-hành = giá-trị này.
_EXPECTED_PREFLIGHT_TEST_COUNT = 26

# 10 field B-1 theo prose 03 §4 (cột "Field (fieldname thật)").
_B1_FIELDS = [
    "app_name",
    "client_id",
    "client_secret",
    "scopes",
    "grant_type",
    "response_type",
    "redirect_uris",
    "default_redirect_uri",
    "allowed_roles",
    "skip_authorization",
]


class TestMobilePreflightDriftGuard(unittest.TestCase):
    """A. Drift-guard: prose 03 §4 ↔ doctype OAuth Client THẬT (read-only meta)."""

    @classmethod
    def setUpClass(cls):
        cls.meta = frappe.get_meta(OAUTH_CLIENT)

    def test_01_b1_fields_exist(self):
        missing = [fn for fn in _B1_FIELDS if self.meta.get_field(fn) is None]
        self.assertEqual(
            missing,
            [],
            f"Field B-1 KHÔNG còn trên doctype OAuth Client (Frappe đổi schema?): {missing}. "
            "Cập nhật docs/mobile/03-auth-oauth2.md §4 + preflight.py.",
        )

    def test_02_grant_type_options(self):
        df = self.meta.get_field("grant_type")
        self.assertEqual(df.fieldtype, "Select")
        self.assertEqual(
            df.options,
            "Authorization Code\nImplicit",
            "grant_type options drift — verifier kỳ vọng 'Authorization Code' là lựa chọn hợp lệ.",
        )
        # Hằng verifier nằm trong options.
        self.assertIn(preflight.EXPECTED_GRANT_TYPE, df.options.split("\n"))

    def test_03_response_type_options(self):
        df = self.meta.get_field("response_type")
        self.assertEqual(df.fieldtype, "Select")
        self.assertEqual(
            df.options,
            "Code\nToken",
            "response_type options drift — verifier kỳ vọng 'Code' là lựa chọn hợp lệ.",
        )
        self.assertIn(preflight.EXPECTED_RESPONSE_TYPE, df.options.split("\n"))

    def test_04_required_fields(self):
        for fn in ("app_name", "scopes", "default_redirect_uri"):
            df = self.meta.get_field(fn)
            self.assertEqual(
                int(df.reqd or 0), 1, f"Field '{fn}' phải reqd==1 (doc §4 đánh ✅) — drift schema."
            )

    def test_05_allowed_roles_child(self):
        df = self.meta.get_field("allowed_roles")
        self.assertEqual(df.fieldtype, "Table MultiSelect")
        self.assertEqual(
            df.options,
            "OAuth Client Role",
            "allowed_roles child-doctype drift — least-priv field-tech bám child 'OAuth Client Role'.",
        )


class TestMobilePreflightVerifier(unittest.TestCase):
    """B. Behaviour của verify_oauth_client() — chạy dưới quyền Administrator (System Manager)."""

    def setUp(self):
        # Test runner = Administrator (có System Manager) → qua frappe.only_for gate.
        frappe.set_user("Administrator")

    def _is_system_manager(self) -> bool:
        return "System Manager" in frappe.get_roles(frappe.session.user)

    def test_06_report_shape(self):
        if not self._is_system_manager():
            self.skipTest("Test user không có System Manager — bỏ qua kiểm shape.")
        report = preflight.verify_oauth_client()
        for key in ("ready", "client_count", "checks", "blockers", "checked_client"):
            self.assertIn(key, report, f"Report thiếu khoá '{key}'.")
        self.assertIsInstance(report["ready"], bool)
        self.assertIsInstance(report["client_count"], int)
        self.assertIsInstance(report["checks"], list)
        self.assertIsInstance(report["blockers"], list)
        for chk in report["checks"]:
            for k in ("field", "expected", "actual", "pass"):
                self.assertIn(k, chk, f"Check thiếu khoá '{k}': {chk}")
            self.assertIsInstance(chk["pass"], bool)

    def test_07_count_zero_no_raise(self):
        if frappe.db.count(OAUTH_CLIENT) != 0:
            self.skipTest("Site có OAuth Client record — không kiểm được nhánh count==0.")
        if not self._is_system_manager():
            self.skipTest("Test user không có System Manager.")
        # KHÔNG raise dù chưa provision.
        report = preflight.verify_oauth_client()
        self.assertFalse(report["ready"])
        self.assertEqual(report["client_count"], 0)
        self.assertIsNone(report["checked_client"])
        self.assertTrue(
            any("Chưa có OAuth Client" in b for b in report["blockers"]),
            f"Thiếu blocker VI 'Chưa có OAuth Client': {report['blockers']}",
        )
        # client_count check phải fail.
        cc = [c for c in report["checks"] if c["field"] == "client_count"]
        self.assertEqual(len(cc), 1)
        self.assertFalse(cc[0]["pass"])

    def test_08_evaluate_client_7_conditions(self):
        # Mock thuần in-memory cho 6 điều kiện cấp-record (B-1.2..7) — KHÔNG ghi DB.
        valid = {
            "grant_type": preflight.EXPECTED_GRANT_TYPE,
            "response_type": preflight.EXPECTED_RESPONSE_TYPE,
            "default_redirect_uri": preflight.EXPECTED_REDIRECT_URI,
            "redirect_uris": preflight.EXPECTED_REDIRECT_URI,
            "scopes": preflight.EXPECTED_SCOPES,
            "skip_authorization": 0,
        }
        checks, blockers = preflight._evaluate_client(valid, allowed_roles_count=1)
        fields = {c["field"] for c in checks}
        self.assertEqual(
            fields,
            {
                "grant_type",
                "response_type",
                "default_redirect_uri",
                "scopes",
                "skip_authorization",
                "allowed_roles",
            },
            "6 điều kiện cấp-record B-1.2..7 phải đủ mặt.",
        )
        self.assertTrue(all(c["pass"] for c in checks), f"Record hợp lệ phải pass hết: {checks}")
        self.assertEqual(blockers, [], "Record hợp lệ không được có blocker.")

        # Đổi 1 field sai → đúng 1 blocker tương ứng.
        bad = dict(valid)
        bad["grant_type"] = "Implicit"
        checks2, blockers2 = preflight._evaluate_client(bad, allowed_roles_count=1)
        gt = [c for c in checks2 if c["field"] == "grant_type"][0]
        self.assertFalse(gt["pass"])
        self.assertTrue(any("grant_type" in b for b in blockers2))

        # allowed_roles rỗng → fail least-priv.
        checks3, blockers3 = preflight._evaluate_client(valid, allowed_roles_count=0)
        ar = [c for c in checks3 if c["field"] == "allowed_roles"][0]
        self.assertFalse(ar["pass"])
        self.assertTrue(any("allowed_roles" in b for b in blockers3))

    def test_09_read_only_no_db_write(self):
        if not self._is_system_manager():
            self.skipTest("Test user không có System Manager.")
        before = frappe.db.count(OAUTH_CLIENT)
        preflight.verify_oauth_client()
        after = frappe.db.count(OAUTH_CLIENT)
        self.assertEqual(before, after, "verify_oauth_client() KHÔNG được thay đổi số record (read-only).")


# --- F-B3: 3-source value-constant drift-guard (preflight EXPECTED_* ↔ 03 §4 ↔ 10 §1) ---------------

_DOC_03 = "docs/mobile/03-auth-oauth2.md"  # field-spec (bảng §4)
_DOC_10 = "docs/mobile/10-deploy-ops.md"  # runbook thực thi (§1 step1)


def _app_doc_path(rel: str) -> Path:
    """Đường dẫn tuyệt đối tới doc trong app assetcore (STDLIB Path, KHÔNG hardcode /home)."""
    app_root = Path(frappe.get_app_path("assetcore")).parent  # .../apps/assetcore
    return app_root / rel


def _read_doc(rel: str) -> str:
    """Đọc raw-text doc qua STDLIB Path.read_text (KHÔNG DB, KHÔNG lib mới)."""
    return _app_doc_path(rel).read_text(encoding="utf-8")


def _section(text: str, start_marker: str, end_markers: tuple[str, ...]) -> str:
    """Cắt vùng raw-text từ dòng chứa ``start_marker`` tới dòng chứa marker kết tiếp.

    Section-scoped để guard chấm ĐÚNG vùng (§4 / §1 step1), tránh literal lọt do
    xuất hiện ở section khác. Trả phần thân (không gồm dòng start/end marker).
    """
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if start_marker in ln), None)
    assert start is not None, f"Không tìm thấy start-marker '{start_marker}' — doc đổi cấu trúc heading?"
    end = next(
        (j for j in range(start + 1, len(lines)) if any(m in lines[j] for m in end_markers)),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end])


def _assert_value_parity(testcase: unittest.TestCase, region_03: str, region_10: str) -> None:
    """Khẳng định MỖI literal value-constant xuất hiện nguyên-văn ở CẢ §4 (03) và §1 step1 (10).

    Literal lấy TỪ preflight.* (SSoT mã) — KHÔNG hardcode chuỗi trong assert ⇒ nếu đổi hằng
    code thì guard tự bám hằng mới (không false-pin). ``response_type='Code'`` chấm bằng form
    value-prescribe (``**`Code`**`` / ``response_type = Code``) chứ KHÔNG bare-substring 'Code'
    (vì 'Code' nằm trong 'Authorization Code'). ``skip_authorization=0`` chấm cả tên field + value '0'.
    """
    redirect = preflight.EXPECTED_REDIRECT_URI  # 'assetcore://oauth/callback'
    scopes = preflight.EXPECTED_SCOPES  # 'all openid'
    grant = preflight.EXPECTED_GRANT_TYPE  # 'Authorization Code'
    response = preflight.EXPECTED_RESPONSE_TYPE  # 'Code'

    # (1) redirect / scopes / grant_type — bare literal ĐỦ unique trong vùng.
    for label, lit in (("EXPECTED_REDIRECT_URI", redirect), ("EXPECTED_SCOPES", scopes), ("EXPECTED_GRANT_TYPE", grant)):
        testcase.assertIn(lit, region_03, f"{label} '{lit}' KHÔNG có nguyên-văn trong 03 §4 — doc drift khỏi preflight.py.")
        testcase.assertIn(lit, region_10, f"{label} '{lit}' KHÔNG có nguyên-văn trong 10 §1 step1 — runbook drift khỏi 03 §4.")

    # (2) response_type='Code' — value-prescribe form (KHÔNG bare 'Code' để khỏi trùng 'Authorization Code').
    resp_03 = f"**`{response}`**"  # 03 §4 bảng: | **`Code`** (default) |
    resp_10 = f"response_type = {response}"  # 10 §1 step1: response_type = Code
    testcase.assertIn(resp_03, region_03, f"EXPECTED_RESPONSE_TYPE value '{response}' KHÔNG prescribe nguyên-văn '{resp_03}' trong 03 §4.")
    testcase.assertIn(resp_10, region_10, f"EXPECTED_RESPONSE_TYPE value '{response}' KHÔNG prescribe nguyên-văn '{resp_10}' trong 10 §1 step1.")

    # (3) skip_authorization=0 — field name + value '0' phải có ở cả 2 vùng.
    for region, where in ((region_03, "03 §4"), (region_10, "10 §1 step1")):
        testcase.assertIn("skip_authorization", region, f"'skip_authorization' KHÔNG có trong {where}.")
        # value '0' prescribe: 03 dùng | `0` | ; 10 dùng skip_authorization = 0
        has_zero = "`0`" in region or "skip_authorization = 0" in region
        testcase.assertTrue(has_zero, f"value prescribe '0' cho skip_authorization KHÔNG có trong {where}.")


class TestMobilePreflightDocValueParity(unittest.TestCase):
    """C. Doc-value parity (F-B3): preflight.EXPECTED_* ↔ 03 §4 ↔ 10 §1 (STDLIB-only, no DB)."""

    @classmethod
    def setUpClass(cls):
        cls.text_03 = _read_doc(_DOC_03)
        cls.text_10 = _read_doc(_DOC_10)
        # §4 region (03): từ '## 4.' tới '## 5.'.
        cls.region_03_s4 = _section(cls.text_03, "## 4. Spec đăng ký OAuth Client", ("## 5.",))
        # §1 step1 region (10): từ heading '## 1.' tới marker 'Vì sao HARD-STOP' (kết step1 block §1).
        cls.region_10_s1 = _section(
            cls.text_10, "## 1. §1 — Bật OAuth2", ("> **Vì sao HARD-STOP", "## 2.")
        )

    def test_10_doc03_s4_redirect_and_scopes(self):
        # 03 §4 chứa nguyên-văn EXPECTED_REDIRECT_URI + EXPECTED_SCOPES.
        self.assertIn(
            preflight.EXPECTED_REDIRECT_URI,
            self.region_03_s4,
            "03 §4 thiếu nguyên-văn redirect 'assetcore://oauth/callback' (SSoT preflight.EXPECTED_REDIRECT_URI).",
        )
        self.assertIn(
            preflight.EXPECTED_SCOPES,
            self.region_03_s4,
            "03 §4 thiếu nguyên-văn scopes 'all openid' (SSoT preflight.EXPECTED_SCOPES).",
        )

    def test_11_doc03_s4_grant_response_skipauth(self):
        # 03 §4 chứa EXPECTED_GRANT_TYPE + EXPECTED_RESPONSE_TYPE (value 'Code') + skip_authorization '0'.
        self.assertIn(
            preflight.EXPECTED_GRANT_TYPE,
            self.region_03_s4,
            "03 §4 thiếu nguyên-văn grant_type 'Authorization Code'.",
        )
        self.assertIn(
            f"**`{preflight.EXPECTED_RESPONSE_TYPE}`**",
            self.region_03_s4,
            "03 §4 thiếu value prescribe response_type '**`Code`**' (phân biệt với 'Authorization Code').",
        )
        self.assertIn("skip_authorization", self.region_03_s4, "03 §4 thiếu field 'skip_authorization'.")
        self.assertIn("`0`", self.region_03_s4, "03 §4 thiếu value prescribe '`0`' cho skip_authorization.")

    def test_12_doc10_s1_runbook_parity(self):
        # 10 §1 step1 chứa cùng 4 literal + skip_authorization=0 (runbook ↔ 03 §4 = B1 acceptance #2 machine-check).
        _assert_value_parity(self, self.region_03_s4, self.region_10_s1)

    def test_13_red_before_green_after_drift_detection(self):
        # GREEN control: giá-trị THẬT → parity pass (KHÔNG raise).
        try:
            _assert_value_parity(self, self.region_03_s4, self.region_10_s1)
        except AssertionError as exc:  # pragma: no cover - chỉ chạy khi doc THẬT đã drift
            self.fail(f"Control GREEN thất bại — doc THẬT đã drift khỏi preflight.EXPECTED_*: {exc}")

        # RED-A: bản-sao IN-MEMORY của 03 §4 đổi redirect → guard PHẢI bắt (AssertionError).
        mutated_03 = self.region_03_s4.replace(preflight.EXPECTED_REDIRECT_URI, "myapp://cb")
        self.assertNotEqual(mutated_03, self.region_03_s4, "Bản-sao phải khác bản gốc (literal redirect tồn tại).")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt drift redirect — false-green!"):
            _assert_value_parity(self, mutated_03, self.region_10_s1)

        # RED-B: monkeypatch tạm EXPECTED_SCOPES sang giá-trị VẮNG MẶT trong doc (drift hằng) →
        #   doc THẬT không chứa hằng mới → guard RED. (Dùng 'profile email' — không xuất hiện ở 03 §4/10 §1;
        #   KHÔNG dùng 'all' vì 'all' là substring của 'all openid' vẫn match → false-green giả.)
        original_scopes = preflight.EXPECTED_SCOPES
        try:
            preflight.EXPECTED_SCOPES = "profile email"  # in-memory monkeypatch, KHÔNG ghi file preflight.py
            self.assertNotIn(
                preflight.EXPECTED_SCOPES,
                self.region_03_s4,
                "Tiền-đề RED-B sai: giá-trị drift phải VẮNG khỏi doc thật mới chứng minh được guard bắt drift.",
            )
            with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt drift EXPECTED_SCOPES — false-green!"):
                _assert_value_parity(self, self.region_03_s4, self.region_10_s1)
        finally:
            preflight.EXPECTED_SCOPES = original_scopes  # khôi phục — KHÔNG side-effect sang test khác.

        # Khôi phục xong → control THẬT lại GREEN (đảm bảo monkeypatch không rò rỉ).
        _assert_value_parity(self, self.region_03_s4, self.region_10_s1)


# --- F-B4: report-shape doc↔code drift-guard (preflight report-shape ↔ 12 §1.2/§1.3) ----------------

_DOC_12 = "docs/mobile/12-phase-b-preflight.md"  # cách đọc report + 7 check (§1.2/§1.3)

# Blocker VI count==0 — SSoT tại preflight.py:183. Guard chấm prefix nguyên-văn (chống drift thông-điệp
# operator-facing); KHÔNG hardcode toàn câu để khỏi pin dấu chấm/đuôi câu nếu code tinh chỉnh nhẹ.
_BLOCKER_NO_CLIENT_PREFIX = "Chưa có OAuth Client"


def _derive_check_fields() -> set[str]:
    """7 check-field-name DERIVE TỪ preflight.py (KHÔNG hardcode literal).

    = {'client_count'} ∪ set field từ ``_evaluate_client(valid_mock, allowed_roles_count=1)``.
    Mock thuần in-memory (KHÔNG ghi DB). Nếu preflight thêm/bớt field cấp-record → set này đổi
    ⇒ guard tự bám field-set mới (không false-pin).
    """
    valid = {
        "grant_type": preflight.EXPECTED_GRANT_TYPE,
        "response_type": preflight.EXPECTED_RESPONSE_TYPE,
        "default_redirect_uri": preflight.EXPECTED_REDIRECT_URI,
        "redirect_uris": preflight.EXPECTED_REDIRECT_URI,
        "scopes": preflight.EXPECTED_SCOPES,
        "skip_authorization": 0,
    }
    checks, _blockers = preflight._evaluate_client(valid, allowed_roles_count=1)
    fields = {c["field"] for c in checks}
    fields.add("client_count")  # B-1 #1 — thêm ở verify_oauth_client() cấp-count, không trong _evaluate_client.
    return fields


def _derive_report_keys() -> set[str]:
    """5 report-key DERIVE TỪ output ``verify_oauth_client()`` nhánh count==0 (KHÔNG hardcode literal).

    Khi runner = System Manager VÀ site có 0 OAuth Client (hiện trạng thật @source) → đọc keys
    trực tiếp từ report sống. Nếu site có client HOẶC không phải System Manager → fallback hằng tĩnh
    DẪN-XUẤT khớp report-shape đặc tả (docstring verify_oauth_client). Fallback vẫn là set "shape"
    chuẩn — nếu preflight đổi report-shape, nhánh sống (count==0) sẽ bắt; fallback chỉ giữ test chạy
    được trên runner có data, KHÔNG che drift cho nhánh sống.
    """
    if "System Manager" in frappe.get_roles(frappe.session.user) and frappe.db.count(OAUTH_CLIENT) == 0:
        report = preflight.verify_oauth_client()
        return set(report.keys())
    return {"ready", "client_count", "checks", "blockers", "checked_client"}


def _assert_fields_in_region(testcase: unittest.TestCase, names: set[str], region: str, where: str) -> None:
    """Khẳng định MỖI name xuất-hiện dạng backtick ``\\`<name>\\``` trong region (section-scoped)."""
    missing = sorted(n for n in names if f"`{n}`" not in region)
    testcase.assertEqual(
        missing,
        [],
        f"{where}: thiếu backtick `<name>` cho {missing} — doc 12 drift khỏi report-shape preflight.py. "
        f"Cập nhật {_DOC_12} {where} để khớp.",
    )


class TestMobilePreflightReportShapeDocGuard(unittest.TestCase):
    """D. Report-shape parity (F-B4): preflight report-shape ↔ 12 §1.2/§1.3 (STDLIB-only, no DB-write)."""

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")  # System Manager → đọc được report sống nhánh count==0.
        cls.text_12 = _read_doc(_DOC_12)
        # §1.2 region: từ '### 1.2' tới '### 1.3'.
        cls.region_12_s12 = _section(cls.text_12, "### 1.2 Cấu trúc report", ("### 1.3",))
        # §1.3 region: từ '### 1.3' tới '## 2.'.
        cls.region_12_s13 = _section(cls.text_12, "### 1.3 7 check", ("## 2.",))
        cls.check_fields = _derive_check_fields()
        cls.report_keys = _derive_report_keys()

    def test_14_check_fields_in_doc12_s13(self):
        # 7 check-field-name (derive từ _evaluate_client + client_count) đều `<field>` trong 12 §1.3.
        self.assertEqual(
            len(self.check_fields), 7, f"Phải đúng 7 check-field (6 record + client_count): {self.check_fields}"
        )
        _assert_fields_in_region(self, self.check_fields, self.region_12_s13, "§1.3")

    def test_15_report_keys_in_doc12_s12(self):
        # 5 report-key (derive từ verify_oauth_client count==0) đều `<key>` trong 12 §1.2.
        self.assertEqual(
            self.report_keys,
            {"ready", "client_count", "checks", "blockers", "checked_client"},
            f"Report-shape drift — verify_oauth_client() đổi key-set: {self.report_keys}",
        )
        _assert_fields_in_region(self, self.report_keys, self.region_12_s12, "§1.2")

    def test_16_blocker_vi_no_client_in_doc12(self):
        # Blocker VI count==0 (preflight.py:183) phải nguyên-văn trong 12 (§1.2 JSON ví dụ HOẶC §3.2).
        self.assertIn(
            _BLOCKER_NO_CLIENT_PREFIX,
            self.text_12,
            f"Doc 12 thiếu nguyên-văn blocker '{_BLOCKER_NO_CLIENT_PREFIX}' — drift thông-điệp "
            "go/no-go operator-facing khỏi preflight.py.",
        )

    def test_17_red_before_green_after_drift_detection(self):
        # GREEN control: doc THẬT → cả 2 guard pass (KHÔNG raise).
        try:
            _assert_fields_in_region(self, self.check_fields, self.region_12_s13, "§1.3")
            _assert_fields_in_region(self, self.report_keys, self.region_12_s12, "§1.2")
        except AssertionError as exc:  # pragma: no cover - chỉ chạy khi doc THẬT đã drift
            self.fail(f"Control GREEN thất bại — doc 12 THẬT đã drift khỏi report-shape preflight.py: {exc}")

        # RED-A: bản-sao IN-MEMORY §1.3 xoá 1 field-name (`allowed_roles`) → guard PHẢI bắt.
        field_to_drop = "allowed_roles"
        self.assertIn(field_to_drop, self.check_fields, "Tiền-đề RED-A: field-name phải có trong set derive.")
        mutated_s13 = self.region_12_s13.replace(f"`{field_to_drop}`", "`(removed)`")
        self.assertNotEqual(mutated_s13, self.region_12_s13, "Bản-sao §1.3 phải khác bản gốc (field tồn tại).")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt mất field-name §1.3 — false-green!"):
            _assert_fields_in_region(self, self.check_fields, mutated_s13, "§1.3")

        # RED-B: bản-sao IN-MEMORY §1.2 xoá 1 report-key (`checked_client`) → guard PHẢI bắt.
        key_to_drop = "checked_client"
        self.assertIn(key_to_drop, self.report_keys, "Tiền-đề RED-B: report-key phải có trong set derive.")
        mutated_s12 = self.region_12_s12.replace(f"`{key_to_drop}`", "`(removed)`")
        self.assertNotEqual(mutated_s12, self.region_12_s12, "Bản-sao §1.2 phải khác bản gốc (key tồn tại).")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt mất report-key §1.2 — false-green!"):
            _assert_fields_in_region(self, self.report_keys, mutated_s12, "§1.2")

        # Khôi phục: region gốc bất biến (replace trả bản mới, KHÔNG mutate cls) → control THẬT lại GREEN.
        _assert_fields_in_region(self, self.check_fields, self.region_12_s13, "§1.3")
        _assert_fields_in_region(self, self.report_keys, self.region_12_s12, "§1.2")


# --- F-B5: record-level blocker-VI remediation doc↔code drift-guard (preflight blockers ↔ 12 §3.3) ---

import re  # noqa: E402  — STDLIB-only; dùng cho stem-extraction (cắt phần nội-suy runtime).

# 6 tên field OAuth Client cấp-record mà §3.3 (bảng khắc phục) PHẢI phủ — bám field-spec 03 §4.
# Dùng để kiểm framing SSoT-derived (§3.3 nói rõ đụng field nào), KHÔNG để hardcode message stem.
_RECORD_BLOCKER_FIELDS = (
    "grant_type",
    "response_type",
    "default_redirect_uri",
    "scopes",
    "skip_authorization",
    "allowed_roles",
)

# Client cố-ý-sai MỌI field cấp-record → ép `_evaluate_client` phát ĐỦ 6 blocker (KHÔNG phụ thuộc DB).
_DELIBERATELY_INVALID_CLIENT = {
    "grant_type": "Implicit",  # ≠ Authorization Code
    "response_type": "Token",  # ≠ Code
    "default_redirect_uri": "myapp://cb",  # ≠ native scheme
    "redirect_uris": "",  # rỗng → default không ∈ list
    "scopes": "wrong",  # ≠ 'all openid'
    "skip_authorization": 1,  # ≠ 0
}


def _blocker_stem(blocker: str) -> str:
    """Stem VI ổn-định cho 1 record-level blocker: cắt phần nội-suy runtime ' — hiện[ default]:<value>'.

    Stem = mệnh đề dẫn TRƯỚC marker nội-suy (em-dash + 'hiện') nên VALUE-STABLE (không phụ thuộc giá
    trị 'hiện:' của record) nhưng REWORD-SENSITIVE (đổi câu mô tả ⇒ stem đổi ⇒ guard ĐỎ). Blocker
    KHÔNG có phần nội-suy (skip_authorization/allowed_roles) → lấy nguyên câu (bỏ dấu chấm/space cuối).

    Lưu ý: KHÔNG cắt nhầm cụm '(hiện màn ...)' của blocker skip_authorization vì pattern đòi
    ' — hiện' (em-dash + space + 'hiện'), còn cụm kia là '(hiện' (mở ngoặc), không khớp.
    """
    m = re.search(r"\s+—\s+hiện", blocker)
    stem = blocker[: m.start()] if m else blocker
    return stem.rstrip(" .")


def _derive_record_blocker_stems() -> list[str]:
    """6 stem VI DERIVE TỪ runtime `_evaluate_client(invalid, allowed_roles_count=0)` (KHÔNG hardcode).

    Mock thuần in-memory (KHÔNG ghi DB). Nếu preflight reword/thêm/bớt blocker cấp-record → list này
    đổi ⇒ guard tự bám thông-điệp mới (không false-pin literal trong test).
    """
    _checks, blockers = preflight._evaluate_client(_DELIBERATELY_INVALID_CLIENT, allowed_roles_count=0)
    return [_blocker_stem(b) for b in blockers]


def _assert_stems_in_region(testcase: unittest.TestCase, stems: list[str], region: str) -> None:
    """Khẳng định MỖI stem xuất-hiện NGUYÊN-VĂN trong region §3.3 (bảng khắc phục ĐỦ)."""
    missing = [s for s in stems if s not in region]
    testcase.assertEqual(
        missing,
        [],
        f"§3.3: thiếu stem blocker khắc phục cho {len(missing)} blocker — bảng khắc phục operator KHÔNG đủ "
        f"/ §3.3 drift khỏi message preflight.py. Thiếu: {missing}. Cập nhật {_DOC_12} §3.3.",
    )


class TestMobilePreflightBlockerViDocGuard(unittest.TestCase):
    """E. Blocker-VI remediation parity (F-B5): 6 record-level blocker ↔ 12 §3.3 (STDLIB-only, no DB-write).

    §3.3 là bảng khắc phục mà workflow B4-DoD dựa vào ('đọc blockers VI → sửa record'). Guard chốt §3.3
    phủ ĐỦ CẢ 6 record-level blocker (không chỉ 3 ví dụ tay-chép) + stem derive-from-source nên reword ở
    preflight.py mà §3.3 bỏ sót → test ĐỎ. KHÔNG đụng blocker count==0 (đã guard ở F-B4 test_16).
    """

    @classmethod
    def setUpClass(cls):
        frappe.set_user("Administrator")  # ổn định runner; _evaluate_client là pure-fn nên không cần quyền.
        cls.text_12 = _read_doc(_DOC_12)
        # §3.3 region: từ '### 3.3' tới marker kết tiếp ('## 4.' = section sau; '---' phân tách cuối §3).
        cls.region_12_s33 = _section(cls.text_12, "### 3.3", ("## 4.", "## Tham chiếu"))
        cls.stems = _derive_record_blocker_stems()

    def test_18_evaluate_client_emits_6_record_blockers(self):
        # client cố-ý-sai + allowed_roles_count=0 → ĐÚNG 6 record-level blocker (KHÔNG gồm count==0).
        _checks, blockers = preflight._evaluate_client(
            _DELIBERATELY_INVALID_CLIENT, allowed_roles_count=0
        )
        self.assertEqual(
            len(blockers),
            6,
            f"`_evaluate_client` phải phát đúng 6 record-level blocker (B-1.2..7): {blockers}",
        )
        # derive 6 stem ổn-định; mỗi stem non-empty + KHÔNG còn phần nội-suy ' — hiện'.
        self.assertEqual(len(self.stems), 6)
        for s in self.stems:
            self.assertTrue(s.strip(), "Stem rỗng — extraction sai.")
            self.assertNotIn(" — hiện", s, f"Stem còn dính phần nội-suy runtime: {s!r}")

    def test_19_all_6_stems_in_doc12_s33(self):
        # §3.3 (bảng khắc phục) chứa NGUYÊN-VĂN CẢ 6 stem derive → bảng ĐỦ, không chỉ 3 ví dụ.
        self.assertEqual(len(self.stems), 6, "Tiền-đề: phải derive đúng 6 stem record-level.")
        _assert_stems_in_region(self, self.stems, self.region_12_s33)

    def test_20_s33_framing_ssot_derived(self):
        # Framing SSoT-derived: §3.3 chứa 6 tên field OAuth Client + sync-note + trỏ field-spec 03 §4.
        region = self.region_12_s33
        missing_fields = [f for f in _RECORD_BLOCKER_FIELDS if f"`{f}`" not in region]
        self.assertEqual(
            missing_fields,
            [],
            f"§3.3 thiếu tham chiếu field `<name>` cho {missing_fields} — bảng khắc phục chưa map đủ "
            "6 field cấp-record (03 §4).",
        )
        # Trỏ field-spec nguồn (mỗi fix-action bám 03 §4, KHÔNG prose lặp bảng field).
        self.assertIn("03 §4", region, "§3.3 phải trỏ field-spec `03 §4` (fix-action bám spec, không lặp).")
        # Sync-note: nêu rõ bảng SSoT-derived từ blocker `verify_oauth_client()` (chống tay-chép trôi).
        self.assertTrue(
            "SSoT" in region and "verify_oauth_client" in region,
            "§3.3 thiếu sync-note nêu bảng SSoT-derived từ blocker `verify_oauth_client()` "
            "(framing chống doc trôi khỏi code).",
        )

    def test_21_red_before_green_after_drift_detection(self):
        # GREEN control: doc THẬT → cả 6 stem có mặt (KHÔNG raise).
        try:
            _assert_stems_in_region(self, self.stems, self.region_12_s33)
        except AssertionError as exc:  # pragma: no cover - chỉ chạy khi §3.3 THẬT đã thiếu/drift
            self.fail(f"Control GREEN thất bại — §3.3 THẬT đã thiếu stem hoặc drift khỏi preflight.py: {exc}")

        # RED-A: bản-sao IN-MEMORY §3.3 xoá 1 stem → guard PHẢI bắt (bảng thiếu blocker).
        stem_to_drop = self.stems[0]
        self.assertIn(stem_to_drop, self.region_12_s33, "Tiền-đề RED-A: stem phải có trong §3.3 thật.")
        mutated_s33 = self.region_12_s33.replace(stem_to_drop, "(đã xoá để test RED)")
        self.assertNotEqual(mutated_s33, self.region_12_s33, "Bản-sao §3.3 phải khác bản gốc (stem tồn tại).")
        with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt thiếu stem §3.3 — false-green!"):
            _assert_stems_in_region(self, self.stems, mutated_s33)

        # RED-B: monkeypatch tạm 1 blocker-string preflight (in-memory, KHÔNG ghi file) sang stem VẮNG
        #   khỏi doc → derive-from-source phải sinh stem mới VẮNG khỏi §3.3 → guard RED. Chứng minh guard
        #   bắt REWORD-DRIFT (không chỉ stem cũ), không false-green. Patch hàm `_evaluate_client` để trả
        #   blocker đã reword (giữ chữ ký + 6 phần tử) rồi khôi phục.
        original_eval = preflight._evaluate_client

        def _reworded_eval(client, allowed_roles_count):
            checks, blockers = original_eval(client, allowed_roles_count)
            if blockers:
                # reword blocker[0] sang câu VẮNG MẶT trong §3.3 (không có marker ' — hiện' để stem giữ nguyên).
                blockers = list(blockers)
                blockers[0] = "BLOCKER ĐÃ REWORD KHÔNG TỒN TẠI TRONG DOC §3.3 PHIÊN BẢN NÀY."
            return checks, blockers

        try:
            preflight._evaluate_client = _reworded_eval  # in-memory monkeypatch
            drifted_stems = _derive_record_blocker_stems()
            self.assertIn(
                "BLOCKER ĐÃ REWORD",
                drifted_stems[0],
                "Tiền-đề RED-B: stem reworded phải xuất hiện trong list derive (derive bám runtime).",
            )
            self.assertNotIn(
                drifted_stems[0],
                self.region_12_s33,
                "Tiền-đề RED-B sai: stem reworded phải VẮNG khỏi §3.3 thật mới chứng minh được guard bắt drift.",
            )
            with self.assertRaises(AssertionError, msg="Guard KHÔNG bắt reword-drift blocker — false-green!"):
                _assert_stems_in_region(self, drifted_stems, self.region_12_s33)
        finally:
            preflight._evaluate_client = original_eval  # khôi phục — KHÔNG side-effect sang test khác.

        # Khôi phục xong → control THẬT lại GREEN (đảm bảo monkeypatch không rò rỉ).
        _assert_stems_in_region(self, _derive_record_blocker_stems(), self.region_12_s33)


# --- F-B6: META-GUARD count-self-verify (chống tái count-drift 13->17->21; analog F-C3 @test_mobile_oas) ---


def _discover_preflight_test_methods() -> list[str]:
    """Introspect module hiện tại → liệt kê MỌI method `test*` của MỌI `unittest.TestCase`.

    STDLIB-only (inspect): duyệt class con TestCase ĐỊNH-NGHĨA TRONG module này (loại import-vào
    từ module khác), gom method bắt đầu 'test'. Đây là SỰ-THẬT runtime mà runner `bench run-tests`
    sẽ load — khớp 1:1 với `Ran N tests`. Trả list 'Class.method' (khử trùng-lặp kế-thừa: method
    chỉ tính ở class ĐỊNH-NGHĨA nó). KHÔNG DB, KHÔNG lib mới (chỉ inspect/unittest STDLIB).
    """
    module = __import__(__name__, fromlist=["*"])
    found: list[str] = []
    for _cls_name, cls in inspect.getmembers(module, inspect.isclass):
        if not issubclass(cls, unittest.TestCase) or cls is unittest.TestCase:
            continue
        if cls.__module__ != __name__:  # bỏ class import từ module khác
            continue
        for meth_name, _meth in inspect.getmembers(cls, inspect.isfunction):
            if not meth_name.startswith("test"):
                continue
            # chỉ tính method ĐỊNH-NGHĨA ở class này (không đếm lại bản kế-thừa)
            if meth_name in vars(cls):
                found.append(f"{cls.__name__}.{meth_name}")
    return found


class TestMobilePreflightCountSelfVerify(unittest.TestCase):
    """F-B6 META-GUARD — count test-method self-verify chống tái count-drift (analog F-C3 @test_mobile_oas).

    Assert số test-method LOAD ĐƯỢC của module == `_EXPECTED_PREFLIGHT_TEST_COUNT` (SSoT định-nghĩa
    MỘT LẦN @đầu module). Thêm/bớt TC mà quên cập const ⇒ RED NGAY ⇒ buộc doc + const đồng-bộ —
    chống tái đúng count-drift 13->17->21 vừa xảy ra. Count gồm CHÍNH TC này (count-after-add = 22
    @F-B6; F-B7 +4 TC `TestMobilePreflightDocLineRefReconciled` ⇒ SSoT nay = 26).
    RED-before/GREEN-after CHỨNG MINH ngay trong TC: tạm set SSoT lệch (999) → RED (`actual != 999`);
    khôi phục đúng (== const) → GREEN ⇒ guard THẬT bắt drift, KHÔNG pass-suông.
    """

    def test_22_count_matches_ssot(self):
        """Số test-method introspect được PHẢI == _EXPECTED_PREFLIGHT_TEST_COUNT (drift = RED).

        ĐÚNG 1 TC (meta-guard count-after-add 21->22 @F-B6). Sanity introspection (count>0 + tự-thấy
        chính meta-guard) gộp VÀO ĐÂY để KHÔNG nâng count thêm — chống introspection-rỗng giả-GREEN
        (filter sai → assertEqual(0,0) vẫn pass). SSoT const tự-cập theo lần thêm TC sau (F-B7 ⇒ 26).
        """
        discovered = _discover_preflight_test_methods()
        actual = len(discovered)
        # Sanity 1 — introspection KHÔNG rỗng/hỏng-filter (chống giả-GREEN do _discover trả []).
        self.assertGreater(actual, 0, "Introspection trả 0 test-method — filter hỏng.")
        # Sanity 2 — chính meta-guard NẰM TRONG tập discover (phạm-vi introspect đúng module).
        self.assertIn(
            "TestMobilePreflightCountSelfVerify.test_22_count_matches_ssot",
            set(discovered),
            "Meta-guard KHÔNG tự-thấy trong tập introspect → _discover_preflight_test_methods sai phạm-vi.",
        )

        # RED-before/GREEN-after PROVEN in-memory: SSoT lệch (999) → assertEqual PHẢI raise.
        with self.assertRaises(
            AssertionError, msg="Guard KHÔNG bắt count-drift (SSoT=999) — false-green!"
        ):
            self.assertEqual(actual, 999)
        # GREEN-after: SSoT THẬT == count introspect (drift = RED).
        self.assertEqual(
            actual,
            _EXPECTED_PREFLIGHT_TEST_COUNT,
            f"COUNT-DRIFT: introspect {actual} test-method NHƯNG _EXPECTED_PREFLIGHT_TEST_COUNT="
            f"{_EXPECTED_PREFLIGHT_TEST_COUNT}. Nếu CỐ Ý thêm/bớt TC → cập NHẬT const (đầu module) "
            f"+ đồng-bộ count trong docs/mobile/completion (ACCEPTANCE-CHECKLIST B-A1 + GO-2 + "
            f"EPIC-B-auth-provisioning B1 + roadmap §3.5/§3.6). Drift KHÔNG-chủ-ý = regress, sửa test. "
            f"discovered(head)={sorted(discovered)[:3]}",
        )


# --- F-B7: stale-line-ref reconciliation guard (§3.4 EPIC-B-auth ↔ source; analog F-C4 oas_29c) ------
#   Vùng `[SUPERSEDED]` §3.4 của `EPIC-B-auth-provisioning.md` (snapshot device-token 2026-06-11)
#   từng ref source bằng số-dòng TUYỆT-ĐỐI `test_mobile_oas.py:222`/`:108-109`/`:114-115`/`:641`
#   cho `_STUB_PATHS`/path-map/operationId/names-frozen — đã CHẾT do line-drift (`_STUB_PATHS=set()`
#   nay @:225; `test_mob_oas_06_device_token_names_frozen` nay @:850). Guard raw-text scan §3.4-region
#   chống tái-drift: (a) 0 line-ref tuyệt-đối `test_mobile_oas.py:<digit>`; (b) ref dạng-SYMBOL
#   (`_STUB_PATHS = set()` / `_DEVICE_TOKEN_FROZEN` / tên test `test_mob_oas_06_device_token_names_frozen`)
#   hiện-diện nguyên-văn; (c) RED-before inject `:999` → guard RAISE; (d) GREEN-after control region THẬT.
#   Nội-dung `[SUPERSEDED]` GIỮ nguyên (audit-trail) — chỉ đổi CÁCH tham-chiếu (symbol thay line).
#   SSoT: ../completion/EPIC-B-auth-provisioning.md §3.4 + ACCEPTANCE-CHECKLIST B-A1.
#   Pattern y hệt `test_mobile_oas.py::TestMobileRoadmapStateReconciled.test_mob_oas_29c` (F-C4).
#   STDLIB-only (Path.read_text + re), KHÔNG DB, KHÔNG yaml, KHÔNG lib mới.

_DOC_EPIC_B = "docs/mobile/completion/EPIC-B-auth-provisioning.md"  # §3.4 device-token snapshot

# Line-ref TUYỆT-ĐỐI vào test_mobile_oas.py (chết do line-drift) — KHÔNG được còn trong §3.4.
# Bắt cả `:222` (single) lẫn `:108-109` (range). KHÔNG anchor symbol cụ-thể ⇒ bắt mọi line-ref
# `test_mobile_oas.py:<digit>` trong vùng (path-map/operationId/names-frozen/_STUB_PATHS).
_ABS_LINE_REF_RX = re.compile(r"test_mobile_oas\.py:\d")

# Dạng-SYMBOL kỳ-vọng (ref bằng symbol/tên test, KHÔNG số-dòng) PHẢI hiện-diện nguyên-văn ở §3.4.
_EXPECTED_SYMBOL_REFS = (
    "_STUB_PATHS = set()",
    "_DEVICE_TOKEN_FROZEN",
    "test_mob_oas_06_device_token_names_frozen",
)


def _epic_b_s34_region() -> str:
    """Cắt vùng §3.4 raw-text của EPIC-B-auth-provisioning.md (từ '### 3.4' tới heading '## 4.').

    Section-scoped để guard chấm ĐÚNG vùng device-token snapshot — KHÔNG flag line-ref ở §4 Tasks
    (B3 vẫn ghi `:108-109`/`:641` như checklist file-edit, KHÔNG thuộc phạm-vi F-B7). Reuse `_section`
    (STDLIB-only). Marker kết = '## 4.' (heading section sau). KHÔNG dùng '---' làm end-marker vì
    dòng separator BẢNG markdown ('|---|---|') khớp '---' → cắt cụt region trước thân-bảng (mất L107
    `_DEVICE_TOKEN_FROZEN`/test-name). HR '---' cuối §3.4 nằm TRONG region (vô-hại — không chứa line-ref).
    """
    text = _read_doc(_DOC_EPIC_B)
    return _section(text, "### 3.4 Device-token", ("## 4.",))


def _scan_abs_line_refs(region: str) -> list[str]:
    """Trả list 'Lnn: <line>' cho MỌI dòng trong region chứa line-ref tuyệt-đối `test_mobile_oas.py:<digit>`.

    KHÔNG exempt dòng `[SUPERSEDED]`: task F-B7 yêu-cầu reconcile CẢ note `[SUPERSEDED]` (L101) —
    GIỮ nội-dung lịch-sử nhưng đổi line-ref→symbol. (Khác F-C4 oas_29a vốn exempt [SUPERSEDED]
    cho prose-state-anchor; ở đây chấm RIÊNG line-ref tuyệt-đối, là dạng-tham-chiếu phải reconcile.)
    """
    hits = []
    for ln, line in enumerate(region.splitlines(), start=1):
        if _ABS_LINE_REF_RX.search(line):
            hits.append(f"L{ln}: {line.strip()}")
    return hits


class TestMobilePreflightDocLineRefReconciled(unittest.TestCase):
    """F. Stale-line-ref reconciliation (F-B7): §3.4 EPIC-B-auth ↔ source (STDLIB-only, no DB).

    §3.4 = vùng `[SUPERSEDED]` snapshot device-token. Guard chốt vùng KHÔNG còn line-ref tuyệt-đối
    `test_mobile_oas.py:<digit>` (chết do drift) → chỉ chấp dạng-SYMBOL. Nội-dung `[SUPERSEDED]` GIỮ
    nguyên (audit-trail). Analog `test_mobile_oas.py::TestMobileRoadmapStateReconciled` (F-C4)."""

    @classmethod
    def setUpClass(cls):
        cls.region = _epic_b_s34_region()

    def test_23a_s34_no_absolute_line_ref(self):
        """(a) §3.4 KHÔNG còn line-ref tuyệt-đối `test_mobile_oas.py:<digit>` (chết do line-drift) —
        ref _STUB_PATHS/path-map/operationId/names-frozen PHẢI dùng dạng-SYMBOL. GREEN sau reconcile."""
        hits = _scan_abs_line_refs(self.region)
        self.assertEqual(
            hits,
            [],
            "§3.4 EPIC-B-auth còn line-ref TUYỆT-ĐỐI `test_mobile_oas.py:<NNN>` (chết do line-drift: "
            "`_STUB_PATHS=set()` nay @:225, names-frozen @:850). Reconcile sang dạng-SYMBOL "
            "(`_STUB_PATHS = set()` / `_DEVICE_TOKEN_FROZEN` / `test_mob_oas_06_device_token_names_frozen`) "
            "— GIỮ nội-dung [SUPERSEDED], chỉ đổi cách-tham-chiếu. Hits:\n  " + "\n  ".join(hits),
        )

    def test_23b_s34_symbol_form_present(self):
        """(b) §3.4 chứa NGUYÊN-VĂN dạng-SYMBOL `_STUB_PATHS = set()` + `_DEVICE_TOKEN_FROZEN` +
        tên test `test_mob_oas_06_device_token_names_frozen` (ref bằng symbol/tên, KHÔNG số-dòng)."""
        missing = [s for s in _EXPECTED_SYMBOL_REFS if s not in self.region]
        self.assertEqual(
            missing,
            [],
            f"§3.4 thiếu dạng-SYMBOL {missing} — sau reconcile phải ref source bằng symbol/tên test "
            "(re-verify @source theo SYMBOL, KHÔNG số-dòng-tuyệt-đối). Cập nhật "
            f"{_DOC_EPIC_B} §3.4.",
        )

    def test_23c_red_before_on_injected_abs_line_ref(self):
        """(c) RED-before — anti-false-green: inject bản-sao IN-MEMORY region có `test_mobile_oas.py:999`
        → detector PHẢI bắt (≥1 hit). Chứng minh guard 23a KHÔNG pass-suông. KHÔNG ghi file."""
        injected = self.region + "\n| OpenAPI STUB | guard `test_mobile_oas.py:999` names-frozen |\n"
        self.assertNotEqual(injected, self.region, "Bản-sao inject phải khác region gốc.")
        self.assertTrue(
            _scan_abs_line_refs(injected),
            "Detector stale-line-ref KHÔNG bắt dòng inject `test_mobile_oas.py:999` → guard giả "
            "(false-green). Detector PHẢI RED khi line-ref tuyệt-đối tái-xuất ở §3.4.",
        )

    def test_23d_green_after_control_region_clean(self):
        """(d) GREEN-after/control — region THẬT (đã reconcile) = SẠCH line-ref tuyệt-đối (đồng nhất
        23a GREEN) + có ĐỦ dạng-SYMBOL (đồng nhất 23b). Đảm bảo detector phân-biệt thật/inject."""
        self.assertEqual(
            _scan_abs_line_refs(self.region),
            [],
            "Control §3.4 THẬT phải SẠCH line-ref tuyệt-đối (đồng bộ 23a).",
        )
        self.assertTrue(
            all(s in self.region for s in _EXPECTED_SYMBOL_REFS),
            "Control §3.4 THẬT phải có ĐỦ dạng-SYMBOL (đồng bộ 23b).",
        )
