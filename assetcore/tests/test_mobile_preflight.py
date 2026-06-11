"""TC-MOB-PRE-01..09 — Drift-guard + behaviour cho Phase-B pre-flight verifier (B0-PREFLIGHT).

Hai nhóm test:

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

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_preflight
"""
from __future__ import annotations

import unittest

import frappe

from assetcore.api.mobile import preflight

OAUTH_CLIENT = "OAuth Client"

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
