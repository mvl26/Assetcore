"""TC-D1-01..07 + TC-D1-DB — Schema + DocPerm guard cho DocType `AC Mobile Device Token`.

EPIC-D / D1 (`docs/mobile/06-push-fcm.md §2.1-2.4` · `docs/mobile/completion/EPIC-D-push-fcm.md §5.1`).

Hai nhóm test:

A. SCHEMA + DOCPERM (TC-D1-01..07) — đọc `frappe.get_meta` runtime (read-only), KHÔNG đụng bảng DB.
   `frappe.get_meta` KHÔNG có JSON-fallback cho app-doctype chưa migrate (meta.py:134
   load_doctype_from_file chỉ phủ core/in-create) ⇒ DocType chỉ readable SAU
   `bench --site miyano migrate` (HARD-STOP USER). Khi CHƯA migrate → setUpClass SKIP
   sạch (RED-pending-migrate, KHÔNG ERROR che lỗi thật), đồng pattern nhóm B.
     - TC-D1-01: đúng 7 field nghiệp vụ với đúng fieldtype.
     - TC-D1-02: autoname == 'hash'.
     - TC-D1-03: fcm_token unique==1 + reqd==1.
     - TC-D1-04: platform Select options == ['android','ios'], reqd==1.
     - TC-D1-05: enabled Check default '1', reqd==1.
     - TC-D1-06: track_changes == 1 (audit modify NĐ98 §6.3).
     - TC-D1-07: DocPerm — System Manager read; field-tech base role create/read/write/delete.

B. DB-DEPENDENT (TC-D1-DB) — RED-pending-migrate. Insert đụng bảng `tabAC Mobile Device Token`
   + UNIQUE index `fcm_token` chỉ tồn tại SAU `bench --site miyano migrate` (HARD-STOP USER).
   ⇒ test này ĐỎ tới khi USER chạy migrate; KHÔNG chữa vô hạn (ghi open_issues).

Run: bench --site miyano run-tests --module assetcore.tests.test_mobile_device_token
"""
from __future__ import annotations

import unittest

import frappe

DOCTYPE = "AC Mobile Device Token"

# 7 field nghiệp vụ theo 06 §2.1 (fieldname -> fieldtype kỳ vọng).
_EXPECTED_FIELDS: dict[str, str] = {
    "user": "Link",
    "fcm_token": "Data",
    "platform": "Select",
    "device_label": "Data",
    "app_version": "Data",
    "last_seen": "Datetime",
    "enabled": "Check",
}

# Role nền của persona field-tech (Role Profile "Kỹ thuật viên" base role,
# personas-mvp §1.2 / role_profile_catalog.py:32). DocPerm role-level ở D1;
# row-level self-scope (user==session.user) thực thi ở D7 hook.
_FIELD_TECH_ROLE = "AssetCore System User"
_ADMIN_ROLE = "System Manager"


class TestMobileDeviceTokenSchema(unittest.TestCase):
    """Nhóm A — schema + DocPerm. Read-only meta; KHÔNG ghi DB."""

    @classmethod
    def setUpClass(cls) -> None:
        # frappe.get_meta KHÔNG đọc JSON cho app-doctype chưa migrate (DoesNotExistError).
        # Chưa migrate (HARD-STOP USER) → SKIP sạch thay vì ERROR (RED-pending-migrate).
        if not frappe.db.exists("DocType", DOCTYPE):
            raise unittest.SkipTest(
                f"DocType {DOCTYPE} chưa đăng ký trong site — cần "
                "`bench --site miyano migrate` (HARD-STOP USER). "
                "TC-D1-01..07 = RED-pending-migrate (SKIP, KHÔNG ERROR)."
            )
        cls.meta = frappe.get_meta(DOCTYPE)

    def _field(self, fieldname: str):
        return self.meta.get_field(fieldname)

    # TC-D1-01 ---------------------------------------------------------------
    def test_d1_01_field_count_and_types(self) -> None:
        """ĐÚNG 7 field nghiệp vụ — KHÔNG bịa thêm (06 §2.1)."""
        business_fields = [
            f for f in self.meta.fields
            if f.fieldtype not in ("Section Break", "Column Break", "Tab Break", "HTML")
        ]
        names = sorted(f.fieldname for f in business_fields)
        self.assertEqual(
            names,
            sorted(_EXPECTED_FIELDS.keys()),
            f"AC Mobile Device Token phải có ĐÚNG 7 field {sorted(_EXPECTED_FIELDS)}, "
            f"thực tế {names}",
        )
        for fieldname, expected_type in _EXPECTED_FIELDS.items():
            f = self._field(fieldname)
            self.assertIsNotNone(f, f"Field {fieldname} không tồn tại")
            self.assertEqual(
                f.fieldtype, expected_type,
                f"{fieldname} phải là {expected_type}, thực tế {f.fieldtype}",
            )

    # TC-D1-02 ---------------------------------------------------------------
    def test_d1_02_autoname_hash(self) -> None:
        """autoname == 'hash' (token KHÔNG làm PK — 06 §2.2)."""
        self.assertEqual(self.meta.autoname, "hash")

    # TC-D1-03 ---------------------------------------------------------------
    def test_d1_03_fcm_token_unique_reqd(self) -> None:
        """fcm_token UNIQUE + reqd (dedup 06 §2.4)."""
        f = self._field("fcm_token")
        self.assertEqual(int(f.unique or 0), 1, "fcm_token phải unique==1")
        self.assertEqual(int(f.reqd or 0), 1, "fcm_token phải reqd==1")

    # TC-D1-04 ---------------------------------------------------------------
    def test_d1_04_platform_select(self) -> None:
        """platform Select options == android/ios, reqd==1."""
        f = self._field("platform")
        opts = [o for o in (f.options or "").split("\n") if o]
        self.assertEqual(opts, ["android", "ios"])
        self.assertEqual(int(f.reqd or 0), 1, "platform phải reqd==1")

    # TC-D1-05 ---------------------------------------------------------------
    def test_d1_05_enabled_default(self) -> None:
        """enabled Check default '1', reqd==1 (06 §2.1)."""
        f = self._field("enabled")
        self.assertEqual(f.fieldtype, "Check")
        self.assertEqual(str(f.default), "1", "enabled default phải '1'")
        self.assertEqual(int(f.reqd or 0), 1, "enabled phải reqd==1")

    # TC-D1-06 ---------------------------------------------------------------
    def test_d1_06_track_changes(self) -> None:
        """track_changes == 1 (audit modify NĐ98 §6.3)."""
        self.assertEqual(int(self.meta.track_changes or 0), 1)

    # TC-D1-07 ---------------------------------------------------------------
    def test_d1_07_docperm_roles(self) -> None:
        """System Manager read-all + field-tech base role create/read/write/delete.

        Self-scope (user==session.user) là D7 hook — KHÔNG test ở D1.
        """
        perms = {p.role: p for p in self.meta.permissions}
        self.assertIn(_ADMIN_ROLE, perms, "Thiếu DocPerm System Manager (admin read-all)")
        self.assertEqual(int(perms[_ADMIN_ROLE].read or 0), 1, "System Manager phải có read")

        self.assertIn(
            _FIELD_TECH_ROLE, perms,
            f"Thiếu DocPerm {_FIELD_TECH_ROLE} (field-tech self-service)",
        )
        ft = perms[_FIELD_TECH_ROLE]
        for op in ("read", "write", "create", "delete"):
            self.assertEqual(
                int(getattr(ft, op) or 0), 1,
                f"{_FIELD_TECH_ROLE} phải có {op} (self-service token của mình)",
            )


class TestMobileDeviceTokenDB(unittest.TestCase):
    """Nhóm B — TC-D1-DB. RED-pending-migrate: cần bảng + UNIQUE index DB.

    Chỉ XANH sau `bench --site miyano migrate` (HARD-STOP USER). Ghi open_issues
    nếu đỏ — KHÔNG chữa vô hạn.
    """

    def setUp(self) -> None:
        if not frappe.db.table_exists("AC Mobile Device Token"):
            self.skipTest(
                "tabAC Mobile Device Token chưa tồn tại — cần `bench --site miyano migrate` "
                "(HARD-STOP USER). TC-D1-DB = RED-pending-migrate."
            )
        self._created: list[str] = []

    def tearDown(self) -> None:
        for name in getattr(self, "_created", []):
            frappe.delete_doc("AC Mobile Device Token", name, force=True, ignore_permissions=True)
        frappe.db.rollback()

    def _new(self, fcm_token: str, user: str = "Administrator"):
        doc = frappe.get_doc({
            "doctype": "AC Mobile Device Token",
            "user": user,
            "fcm_token": fcm_token,
            "platform": "android",
            "enabled": 1,
        })
        doc.insert(ignore_permissions=True)
        self._created.append(doc.name)
        return doc

    def test_d1_db_name_is_hash(self) -> None:
        """autoname=hash → name là hash (KHÔNG phải fcm_token)."""
        doc = self._new("tok-hash-1")
        self.assertNotEqual(doc.name, doc.fcm_token)
        self.assertTrue(doc.name and len(doc.name) >= 10, "name phải là hash dài")

    def test_d1_db_fcm_token_unique(self) -> None:
        """2 record CÙNG fcm_token → UniqueValidationError (06 §2.4 dedup DB)."""
        from frappe.exceptions import UniqueValidationError, ValidationError

        self._new("tok-dup")
        with self.assertRaises((UniqueValidationError, ValidationError)):
            self._new("tok-dup")


# ════════════════════════════════════════════════════════════════════════════
# D2 — Service mobile_device_token (3-tier): register / unregister / invalidate
#   Spec: docs/mobile/completion/EPIC-D-push-fcm.md §D2/§6.2/§6.3
#         docs/mobile/06-push-fcm.md §2.3-2.5/§5.3
#
#   Nhóm LOGIC (TC-D2-03 spoof signature · TC-D2-07 audit-call · TC-D2-08 guard)
#   = XANH KHÔNG cần migrate (mock session + mock ORM/audit, KHÔNG đụng bảng).
#   Nhóm DB (TC-D2-01/02/04/05/06 UPSERT-dedup) = RED-pending-migrate:
#   SKIP sạch khi `tabAC Mobile Device Token` chưa tồn tại (HARD-STOP USER
#   `bench migrate`) — KHÔNG ERROR che lỗi thật (anti-false-green LL-BE-42..49).
# ════════════════════════════════════════════════════════════════════════════

from unittest import mock  # noqa: E402

from assetcore.services import mobile_device_token as svc  # noqa: E402

_SESSION_USER = "Administrator"          # session giả-lập (chủ token hợp lệ)
_VICTIM_USER = "victim@example.com"       # nạn nhân spoof — KHÔNG được làm chủ token


class TestMobileDeviceTokenServiceLogic(unittest.TestCase):
    """Nhóm LOGIC D2 — XANH KHÔNG cần migrate (mock session + ORM + audit).

    Chỉ kiểm tra hợp đồng signature (ÉP user=session, swallow kwargs lạ) và
    audit-call — KHÔNG ghi bảng `tabAC Mobile Device Token`.
    """

    # TC-D2-03 ÉP user=session chống spoof (signature) -----------------------
    def test_d2_03_register_signature_rejects_no_user_param(self) -> None:
        """Signature `register_device_token` KHÔNG khai báo tham số `user`.

        Hợp đồng chống spoof §6.2: client KHÔNG được chọn chủ token. `user` phải
        bị ÉP = `frappe.session.user` trong thân hàm, KHÔNG nằm trong signature.
        """
        import inspect

        sig = inspect.signature(svc.register_device_token)
        self.assertNotIn(
            "user", sig.parameters,
            "register_device_token KHÔNG được nhận tham số `user` (chống spoof §6.2)",
        )
        # fcm_token + platform là keyword-only reqd (không positional ambiguous).
        self.assertEqual(
            sig.parameters["fcm_token"].kind, inspect.Parameter.KEYWORD_ONLY,
            "fcm_token phải keyword-only (gọi rõ ràng, không positional)",
        )

    def test_d2_03_register_forces_session_user_drops_spoof_kwarg(self) -> None:
        """Truyền `user='victim'` (kwargs lạ) → record.user == session.user (NOT victim).

        Mock ORM: chặn DB hoàn toàn, bắt dict ghi xuống. Token chưa tồn tại →
        nhánh new_doc; field `user` PHẢI = session.user dù caller cố nhồi victim.
        """
        captured: dict = {}

        class _FakeDoc:
            def __init__(self, data):
                captured.update(data)
                self.__dict__.update(data)
                self.name = "FAKE-HASH-1"

            def insert(self, *a, **k):
                return self

            def save(self, *a, **k):
                return self

        with mock.patch.object(svc.frappe, "session") as msess, \
                mock.patch.object(svc, "now_datetime", return_value="2026-06-12 00:00:00"), \
                mock.patch.object(svc.frappe.db, "get_value", return_value=None), \
                mock.patch.object(svc.frappe, "get_doc", side_effect=lambda d: _FakeDoc(d)), \
                mock.patch.object(svc, "_audit"):
            msess.user = _SESSION_USER
            # Caller cố spoof: nhồi user=victim qua kwargs lạ.
            svc.register_device_token(
                fcm_token="T1", platform="android",
                **{"user": _VICTIM_USER},  # kwargs lạ — PHẢI bị drop
            )

        self.assertEqual(
            captured.get("user"), _SESSION_USER,
            "record.user PHẢI = session.user, KHÔNG = victim (spoof bị chặn §6.2)",
        )
        self.assertNotEqual(captured.get("user"), _VICTIM_USER)

    # TC-D2-07 audit register/unregister ------------------------------------
    def test_d2_07_register_calls_audit(self) -> None:
        """register sinh audit NĐ98 (svc00.log_audit_event gọi đúng 1 lần)."""
        class _FakeDoc:
            def __init__(self, data):
                self.__dict__.update(data)
                self.name = "FAKE-HASH-2"

            def insert(self, *a, **k):
                return self

            def save(self, *a, **k):
                return self

        with mock.patch.object(svc.frappe, "session") as msess, \
                mock.patch.object(svc, "now_datetime", return_value="2026-06-12 00:00:00"), \
                mock.patch.object(svc.frappe.db, "get_value", return_value=None), \
                mock.patch.object(svc.frappe, "get_doc", side_effect=lambda d: _FakeDoc(d)), \
                mock.patch.object(svc.svc00, "log_audit_event") as maudit:
            msess.user = _SESSION_USER
            svc.register_device_token(fcm_token="T1", platform="android")

        self.assertTrue(maudit.called, "register PHẢI gọi log_audit_event (NĐ98 §6.3)")
        kw = maudit.call_args.kwargs
        self.assertEqual(kw.get("actor"), _SESSION_USER, "audit actor = session.user")
        self.assertEqual(kw.get("ref_doctype"), svc.DOCTYPE)
        self.assertIn(
            "register", (kw.get("change_summary") or "").lower(),
            "audit change_summary phải nêu hành động register",
        )

    def test_d2_07_unregister_calls_audit_when_record_exists(self) -> None:
        """unregister token tồn tại → set enabled=0 + sinh audit (record GIỮ)."""
        with mock.patch.object(svc.frappe, "session") as msess, \
                mock.patch.object(svc.frappe.db, "get_value", return_value="FAKE-HASH-3"), \
                mock.patch.object(svc.frappe.db, "set_value") as mset, \
                mock.patch.object(svc.svc00, "log_audit_event") as maudit:
            msess.user = _SESSION_USER
            svc.unregister_device_token("T1")

        # enabled=0 set qua db.set_value (KHÔNG delete record — §2.5).
        self.assertTrue(mset.called, "unregister phải set_value(enabled=0), KHÔNG xoá record")
        args = mset.call_args
        self.assertEqual(args.args[0], svc.DOCTYPE)
        self.assertTrue(maudit.called, "unregister PHẢI gọi log_audit_event (NĐ98 §6.3)")

    def test_d2_07_unregister_absent_is_noop_no_audit(self) -> None:
        """unregister token∄ = no-op KHÔNG raise, KHÔNG audit (idempotent)."""
        with mock.patch.object(svc.frappe, "session") as msess, \
                mock.patch.object(svc.frappe.db, "get_value", return_value=None), \
                mock.patch.object(svc.frappe.db, "set_value") as mset, \
                mock.patch.object(svc.svc00, "log_audit_event") as maudit:
            msess.user = _SESSION_USER
            # KHÔNG raise.
            svc.unregister_device_token("T-not-exist")
        self.assertFalse(mset.called)
        self.assertFalse(maudit.called)

    # TC-D2-06 invalidate idempotent (logic) --------------------------------
    def test_d2_06_invalidate_absent_is_noop_no_raise(self) -> None:
        """invalidate_token token∄ = no-op KHÔNG raise (total-function, sender D5)."""
        with mock.patch.object(svc.frappe.db, "get_value", return_value=None), \
                mock.patch.object(svc.frappe.db, "set_value") as mset:
            # gọi 2 lần — idempotent.
            svc.invalidate_token("T-not-exist")
            svc.invalidate_token("T-not-exist")
        self.assertFalse(mset.called, "invalidate token∄ KHÔNG được đụng DB")

    def test_d2_06_invalidate_existing_sets_enabled_zero(self) -> None:
        """invalidate_token token tồn tại → set enabled=0 (entry-point D5 on-401)."""
        with mock.patch.object(svc.frappe.db, "get_value", return_value="FAKE-HASH-4"), \
                mock.patch.object(svc.frappe.db, "set_value") as mset:
            svc.invalidate_token("T1")
        self.assertTrue(mset.called)
        self.assertEqual(mset.call_args.args[0], svc.DOCTYPE)


class TestMobileDeviceTokenServiceDB(unittest.TestCase):
    """Nhóm DB D2 — TC-D2-01/02/04/05. RED-pending-migrate.

    UPSERT-dedup THẬT đụng bảng `tabAC Mobile Device Token` + UNIQUE index —
    chỉ XANH SAU `bench --site miyano migrate` (HARD-STOP USER). Khi chưa migrate
    → SKIP sạch (KHÔNG ERROR che lỗi). Ghi open_issues nếu đỏ — KHÔNG chữa vô hạn.
    """

    def setUp(self) -> None:
        if not frappe.db.table_exists("AC Mobile Device Token"):
            self.skipTest(
                "tabAC Mobile Device Token chưa tồn tại — cần "
                "`bench --site miyano migrate` (HARD-STOP USER). "
                "TC-D2-01/02/04/05 = RED-pending-migrate."
            )
        self._created: list[str] = []
        frappe.set_user("Administrator")

    def tearDown(self) -> None:
        for name in getattr(self, "_created", []):
            try:
                frappe.delete_doc(
                    "AC Mobile Device Token", name, force=True, ignore_permissions=True
                )
            except Exception:
                pass
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _track(self, name: str) -> str:
        self._created.append(name)
        return name

    def _count(self, fcm_token: str) -> int:
        return frappe.db.count("AC Mobile Device Token", {"fcm_token": fcm_token})

    # TC-D2-01 register tạo mới ---------------------------------------------
    def test_d2_01_register_creates_new(self) -> None:
        name = self._track(svc.register_device_token(fcm_token="D2T1", platform="android"))
        self.assertEqual(self._count("D2T1"), 1, "register lần đầu → đúng 1 record")
        doc = frappe.get_doc("AC Mobile Device Token", name)
        self.assertEqual(doc.user, frappe.session.user, "user == session.user")
        self.assertEqual(int(doc.enabled), 1, "enabled=1 sau register")
        self.assertTrue(doc.last_seen, "last_seen được set")

    # TC-D2-02 UPSERT-dedup giữ 1 record ------------------------------------
    def test_d2_02_upsert_dedup_keeps_single_record(self) -> None:
        n1 = self._track(svc.register_device_token(
            fcm_token="D2T2", platform="android", device_label="phone-A"))
        n2 = svc.register_device_token(
            fcm_token="D2T2", platform="ios", device_label="phone-B", app_version="1.2.3")
        self.assertEqual(n1, n2, "UPSERT trả CÙNG name (KHÔNG tạo record mới)")
        self.assertEqual(self._count("D2T2"), 1, "1 fcm_token ⇒ tối đa 1 record")
        doc = frappe.get_doc("AC Mobile Device Token", n1)
        self.assertEqual(doc.device_label, "phone-B", "field cập nhật theo lần 2")
        self.assertEqual(doc.platform, "ios")
        self.assertEqual(doc.app_version, "1.2.3")

    # TC-D2-04 re-bind đổi chủ ----------------------------------------------
    def test_d2_04_rebind_changes_owner_no_duplicate(self) -> None:
        # user-A đăng ký T trước (insert thẳng để giả lập chủ cũ).
        seed = frappe.get_doc({
            "doctype": "AC Mobile Device Token",
            "user": "Administrator",
            "fcm_token": "D2T4",
            "platform": "android",
            "enabled": 1,
        })
        # giả lập chủ cũ = user khác Administrator nếu tồn tại; nếu không, dùng Guest.
        other = "Guest"
        seed.user = other
        seed.insert(ignore_permissions=True)
        self._track(seed.name)

        # user-B (session = Administrator) register CÙNG token → re-bind.
        frappe.set_user("Administrator")
        n = svc.register_device_token(fcm_token="D2T4", platform="ios")
        self.assertEqual(n, seed.name, "re-bind = CÙNG record (KHÔNG record thứ 2)")
        self.assertEqual(self._count("D2T4"), 1, "KHÔNG nhân đôi")
        doc = frappe.get_doc("AC Mobile Device Token", seed.name)
        self.assertEqual(doc.user, "Administrator", "record chuyển chủ về session.user")

    # TC-D2-05 unregister giữ record ----------------------------------------
    def test_d2_05_unregister_keeps_record_enabled_zero(self) -> None:
        name = self._track(svc.register_device_token(fcm_token="D2T5", platform="android"))
        svc.unregister_device_token("D2T5")
        self.assertEqual(self._count("D2T5"), 1, "record CÒN tồn tại (KHÔNG xoá — §2.5)")
        doc = frappe.get_doc("AC Mobile Device Token", name)
        self.assertEqual(int(doc.enabled), 0, "enabled==0 sau unregister")

    # TC-D2-06 invalidate idempotent (DB) -----------------------------------
    def test_d2_06_invalidate_db_idempotent(self) -> None:
        name = self._track(svc.register_device_token(fcm_token="D2T6", platform="android"))
        svc.invalidate_token("D2T6")
        doc = frappe.get_doc("AC Mobile Device Token", name)
        self.assertEqual(int(doc.enabled), 0, "invalidate → enabled=0")
        # gọi lại + token∄ → no-op KHÔNG raise.
        svc.invalidate_token("D2T6")
        svc.invalidate_token("D2T6-nonexistent")
        self.assertEqual(self._count("D2T6"), 1, "vẫn 1 record, KHÔNG vỡ")


# ════════════════════════════════════════════════════════════════════════════
# D5 — Sender utils/fcm.py (FCM HTTP v1) — TC-D5-01..06
#   Spec: docs/mobile/completion/EPIC-D-push-fcm.md §D5 / §5.3 (payload shape) /
#         §6.2 (no creds-leak) / §6.4 (fail-safe) · 06-push-fcm.md §4.1 / §5.2.
#
#   100% mock (KHÔNG creds, KHÔNG HTTP thật, KHÔNG bảng DB) ⇒ XANH KHÔNG cần
#   migrate / D3 creds. Mock 3 seam: frappe.conf (creds-from-conf) +
#   _fetch_access_token (bỏ qua OAuth thật) + _post_message (giả lập FCM transport)
#   + invalidate_token (đếm call). Send-THẬT tới device = RED-pending-creds (D3
#   HARD-STOP USER) → open_issues, KHÔNG cố chữa ở mock-test.
# ════════════════════════════════════════════════════════════════════════════

import json  # noqa: E402
import logging  # noqa: E402

from assetcore.utils import fcm  # noqa: E402

# Service-account giả-lập (KHÔNG private_key thật) — đủ field để _load_credentials
# pass guard (private_key + client_email). RSA-sign bị mock qua _fetch_access_token.
_FAKE_SA_PRIVATE_KEY = "-----BEGIN PRIVATE KEY-----\nFAKE_SECRET_DO_NOT_LOG\n-----END PRIVATE KEY-----"
_FAKE_SA_INFO = {
    "type": "service_account",
    "project_id": "assetcore-fcm-test",
    "private_key": _FAKE_SA_PRIVATE_KEY,
    "client_email": "fcm@assetcore-fcm-test.iam.gserviceaccount.com",
}
_CONF_PROJECT_ID = "assetcore-fcm-test"
_DEAD_TOKEN = "DEAD-TOK-123456"


class _FakeConf(dict):
    """Giả-lập frappe.conf — `.get(key)` đọc site_config (creds-from-conf §5.2).

    `__getattr__` trả None cho key thiếu (đồng frappe `_dict`) để KHÔNG vỡ
    internals của Frappe đọc attr `frappe.conf.allow_tests` khi log_error/SQL chạy.
    """

    def __getattr__(self, key):  # pragma: no cover - delegate-only
        return self.get(key)


class TestMobileFcmSender(unittest.TestCase):
    """Nhóm D5 — sender FCM HTTP v1. 100% mock, XANH KHÔNG cần creds/migrate."""

    def _patch_conf(self, *, project_id=_CONF_PROJECT_ID, sa_path="/fake/sa.json"):
        """Patch frappe.conf + _load_credentials đọc-từ-conf (KHÔNG hardcode)."""
        conf = _FakeConf()
        if project_id is not None:
            conf["fcm_project_id"] = project_id
        if sa_path is not None:
            conf["fcm_service_account_path"] = sa_path
        return mock.patch.object(fcm.frappe, "conf", conf)

    # TC-D5-01 build message shape §5.3 -------------------------------------
    def test_d5_01_build_message_shape(self) -> None:
        """message.token == fcm_token; title/body strip-HTML + body≤1000;
        data{doctype,name,event,deeplink}; android.priority set (§5.3)."""
        long_body = "<b>x</b>" + ("a" * 2000)
        data = {
            "doctype": "Incident Report",
            "name": "INC-2026-0042",
            "event": "incident_created",
            "deeplink": "assetcore://incident/INC-2026-0042",
        }
        msg = fcm._build_message("TOK-1", "<i>Sự cố mới</i>", long_body, data)["message"]

        self.assertEqual(msg["token"], "TOK-1", "message.token == fcm_token")
        # strip-HTML title/body.
        self.assertEqual(msg["notification"]["title"], "Sự cố mới")
        self.assertNotIn("<", msg["notification"]["body"], "body phải strip-HTML")
        self.assertLessEqual(
            len(msg["notification"]["body"]), 1000, "body cắt ≤1000 ký tự (§5.3)"
        )
        # data routing keys present (§5.3).
        for k in ("doctype", "name", "event", "deeplink"):
            self.assertIn(k, msg["data"], f"data thiếu routing key {k}")
        self.assertEqual(msg["data"]["doctype"], "Incident Report")
        self.assertEqual(msg["data"]["deeplink"], "assetcore://incident/INC-2026-0042")
        # data map<string,string> — mọi value là str (FCM HTTP v1 yêu cầu).
        for v in msg["data"].values():
            self.assertIsInstance(v, str, "FCM data value PHẢI là string")
        # android.priority set.
        self.assertIn(msg["android"]["priority"], ("high", "normal"))

    def test_d5_01_build_message_priority_override(self) -> None:
        """`_priority` trong data hạ android.priority='normal' (PM-due §5.3)."""
        msg = fcm._build_message(
            "TOK-2", "t", "b", {"event": "calibration_due", "_priority": "normal"}
        )["message"]
        self.assertEqual(msg["android"]["priority"], "normal")
        self.assertNotIn("_priority", msg["data"], "key nội bộ _priority KHÔNG vào data")

    # TC-D5-02 invalidate-on-401/UNREGISTERED/404 — đúng 1 lần -----------------
    def test_d5_02_invalidate_on_401(self) -> None:
        """FCM 401 → invalidate_token(token) gọi ĐÚNG 1 lần (call_count==1)."""
        self._assert_invalidate_called_once(status=401, body='{"error":{"status":"UNAUTHENTICATED"}}')

    def test_d5_02_invalidate_on_unregistered(self) -> None:
        """FCM 404 UNREGISTERED → invalidate đúng 1 lần."""
        body = '{"error":{"status":"NOT_FOUND","details":[{"errorCode":"UNREGISTERED"}]}}'
        self._assert_invalidate_called_once(status=404, body=body)

    def test_d5_02_invalidate_on_token_not_registered_marker(self) -> None:
        """body chứa `registration-token-not-registered` → invalidate đúng 1 lần."""
        body = '{"error":{"message":"messaging/registration-token-not-registered"}}'
        # status 200-line không xảy ra với token-dead; dùng 404 thực tế.
        self._assert_invalidate_called_once(status=404, body=body)

    def _assert_invalidate_called_once(self, *, status: int, body: str) -> None:
        with self._patch_conf(), \
                mock.patch.object(fcm, "_load_credentials",
                                  return_value=(_FAKE_SA_INFO, _CONF_PROJECT_ID)), \
                mock.patch.object(fcm, "_fetch_access_token", return_value="FAKE-ACCESS"), \
                mock.patch.object(fcm, "_post_message", return_value=(status, body)), \
                mock.patch("assetcore.services.mobile_device_token.invalidate_token") as minval:
            result = fcm.send_fcm_message(
                _DEAD_TOKEN, "t", "b",
                {"doctype": "Incident Report", "name": "INC-1"},
            )
        self.assertEqual(
            minval.call_count, 1,
            f"invalidate_token PHẢI gọi đúng 1 lần khi FCM trả {status}",
        )
        self.assertEqual(minval.call_args.args[0], _DEAD_TOKEN, "invalidate đúng token chết")
        self.assertFalse(result, "send trả False khi token chết (đã invalidate)")

    def test_d5_02_no_invalidate_on_success(self) -> None:
        """FCM 200 → KHÔNG invalidate (token sống); return True."""
        with self._patch_conf(), \
                mock.patch.object(fcm, "_load_credentials",
                                  return_value=(_FAKE_SA_INFO, _CONF_PROJECT_ID)), \
                mock.patch.object(fcm, "_fetch_access_token", return_value="FAKE-ACCESS"), \
                mock.patch.object(fcm, "_post_message",
                                  return_value=(200, '{"name":"projects/x/messages/1"}')), \
                mock.patch("assetcore.services.mobile_device_token.invalidate_token") as minval:
            result = fcm.send_fcm_message("LIVE-TOK", "t", "b", {})
        self.assertFalse(minval.called, "token sống KHÔNG được invalidate")
        self.assertTrue(result, "FCM 2xx → return True")

    # TC-D5-03 creds-from-conf (KHÔNG hardcode) ------------------------------
    def test_d5_03_creds_read_from_conf_not_hardcoded(self) -> None:
        """_load_credentials đọc fcm_service_account_path + fcm_project_id TỪ conf."""
        captured_path = {}

        def _fake_open(path, *a, **k):
            captured_path["p"] = path
            import io
            return io.StringIO(json.dumps(_FAKE_SA_INFO))

        with self._patch_conf(project_id="proj-from-conf", sa_path="/conf/driven/sa.json"), \
                mock.patch("builtins.open", side_effect=_fake_open):
            creds = fcm._load_credentials()
        self.assertIsNotNone(creds, "đủ creds-từ-conf → load OK")
        sa_info, project_id = creds
        self.assertEqual(project_id, "proj-from-conf",
                         "project_id PHẢI lấy từ conf (KHÔNG hardcode)")
        self.assertEqual(captured_path.get("p"), "/conf/driven/sa.json",
                         "đọc SA file theo path từ conf (KHÔNG hardcode)")

    def test_d5_03_project_id_from_conf_reflected_in_url(self) -> None:
        """project_id sai/khác trong conf → URL messages:send phản ánh conf."""
        captured = {}

        def _fake_post(project_id, message, access_token):
            captured["url"] = fcm._FCM_SEND_URL.format(project_id=project_id)
            captured["project_id"] = project_id
            return 200, "{}"

        with self._patch_conf(project_id="weird-proj-999"), \
                mock.patch.object(fcm, "_load_credentials",
                                  return_value=(_FAKE_SA_INFO, "weird-proj-999")), \
                mock.patch.object(fcm, "_fetch_access_token", return_value="FAKE-ACCESS"), \
                mock.patch.object(fcm, "_post_message", side_effect=_fake_post):
            fcm.send_fcm_message("TOK", "t", "b", {})
        self.assertEqual(captured.get("project_id"), "weird-proj-999")
        self.assertIn("weird-proj-999", captured.get("url", ""),
                      "URL phản ánh project_id từ conf")

    # TC-D5-04 no-leak creds in log -----------------------------------------
    def test_d5_04_no_creds_leak_in_log(self) -> None:
        """Lỗi gửi → log KHÔNG chứa private_key/access_token bí mật (§6.2)."""
        logged = []

        def _capture_log_error(message, title=None):
            logged.append(str(message))
            if title:
                logged.append(str(title))

        # Buộc nhánh lỗi (post raise) để kích log_error — assert KHÔNG leak.
        with self._patch_conf(), \
                mock.patch.object(fcm, "_load_credentials",
                                  return_value=(_FAKE_SA_INFO, _CONF_PROJECT_ID)), \
                mock.patch.object(fcm, "_fetch_access_token", return_value="SECRET-ACCESS-TOKEN-XYZ"), \
                mock.patch.object(fcm, "_post_message", return_value=(500, "internal")), \
                mock.patch.object(fcm.frappe, "log_error", side_effect=_capture_log_error):
            fcm.send_fcm_message("TOK", "t", "b", {})

        blob = "\n".join(logged)
        self.assertNotIn("FAKE_SECRET_DO_NOT_LOG", blob, "private_key KHÔNG được vào log")
        self.assertNotIn(_FAKE_SA_PRIVATE_KEY, blob, "private_key KHÔNG được vào log")
        self.assertNotIn("SECRET-ACCESS-TOKEN-XYZ", blob, "access_token KHÔNG được vào log")

    def test_d5_04_creds_unreadable_logs_no_secret(self) -> None:
        """SA file lỗi đọc → log nhãn config KHÔNG kèm private_key."""
        logged = []
        with self._patch_conf(sa_path="/nonexistent/sa.json"), \
                mock.patch("builtins.open", side_effect=OSError("boom")), \
                mock.patch.object(fcm.frappe, "log_error",
                                  side_effect=lambda m, t=None: logged.append(str(m))):
            creds = fcm._load_credentials()
        self.assertIsNone(creds, "SA file lỗi → None (no-op fail-safe)")
        self.assertNotIn("FAKE_SECRET_DO_NOT_LOG", "\n".join(logged))

    # TC-D5-05 missing-creds → no-op KHÔNG raise -----------------------------
    def test_d5_05_missing_creds_is_noop_no_raise(self) -> None:
        """conf thiếu fcm_* → send no-op return None KHÔNG raise (fail-safe §6.4)."""
        with self._patch_conf(project_id=None, sa_path=None):
            # KHÔNG raise — caller D6 KHÔNG vỡ.
            result = fcm.send_fcm_message("TOK", "t", "b", {})
        self.assertIsNone(result, "thiếu creds → no-op None (KHÔNG raise)")

    def test_d5_05_missing_project_id_only_is_noop(self) -> None:
        """Có path nhưng thiếu fcm_project_id → no-op None (đủ-2-creds mới chạy)."""
        with self._patch_conf(project_id=None, sa_path="/some/sa.json"):
            result = fcm.send_fcm_message("TOK", "t", "b", {})
        self.assertIsNone(result)

    def test_d5_05_empty_token_is_noop(self) -> None:
        """token rỗng → no-op None (KHÔNG load creds, KHÔNG HTTP)."""
        with mock.patch.object(fcm, "_load_credentials") as mload:
            result = fcm.send_fcm_message("", "t", "b", {})
        self.assertIsNone(result)
        self.assertFalse(mload.called, "token rỗng → KHÔNG cả load creds")

    # TC-D5-06 stdlib-guard — KHÔNG kéo firebase_admin/requests/google.* --------
    def test_d5_06_stdlib_only_imports(self) -> None:
        """import assetcore.utils.fcm KHÔNG kéo firebase_admin/requests/google.*."""
        import importlib
        import sys

        forbidden = ("firebase_admin", "requests", "google.auth", "googleapiclient")
        # Module đã import ở đầu file — verify nó KHÔNG kéo lib bị cấm vào sys.modules
        # qua chính nó. (cryptography/urllib/json/base64/time = cho phép.)
        importlib.reload(fcm)
        # Quét source-level import names của module (AST) — chắc chắn KHÔNG khai báo.
        import ast

        with open(fcm.__file__, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imported.add(n.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        for bad in ("firebase_admin", "requests", "googleapiclient"):
            self.assertNotIn(
                bad, imported,
                f"utils/fcm.py KHÔNG được import {bad} (STDLIB-only guard)",
            )
        # `google` (google.auth) cũng cấm ở top-level import.
        self.assertNotIn("google", imported, "KHÔNG import google.* (lib chưa cài)")
        # sanity: ít nhất stdlib urllib + frappe có mặt (sender thực sự dùng).
        self.assertIn("urllib", imported)
        self.assertIn("frappe", imported)
        _ = (logging, sys, forbidden)  # giữ import dùng (lint)


# ════════════════════════════════════════════════════════════════════════════
# D6 — Kênh #3 push (FCM) trong `_dispatch` (1 điểm fan-out) + rate-limit register
#   Spec: docs/mobile/completion/EPIC-D-push-fcm.md §D6 / §5.3 (payload) /
#         §5.4-§5.5 (event+deeplink route) / §1.3 (fail-safe) · 06-push-fcm.md §5.3.
#
#   Nhóm AUTO (TC-D6-01..05/07/08) = XANH KHÔNG cần migrate/creds: mock
#   send_fcm_message + mock frappe.get_all (token lookup) + mock kênh 1/2.
#   Nhóm DB (TC-D6-06 DoD E3 fan-out token THẬT) = RED-pending-migrate: cần bảng
#   `tabAC Mobile Device Token` (HARD-STOP USER `bench migrate`) → SKIP sạch.
#
#   Chống false-green (LL-TEST-21): assert side-effect THẬT (send_fcm_message
#   call_args token/payload), KHÔNG chỉ "return không raise".
# ════════════════════════════════════════════════════════════════════════════

from assetcore.services import notifications as notif  # noqa: E402


class _DocStub:
    """Doc rời rạc tối thiểu cho `_dispatch` (doctype/name để route + payload)."""

    def __init__(self, doctype: str = "Incident Report", name: str = "INC-2026-0042"):
        self.doctype = doctype
        self.name = name


def _fake_token_get_all(rows_by_user: dict[str, list[str]]):
    """side_effect cho frappe.get_all: trả token enabled=1 theo user; pass-through khác.

    CHỈ chặn truy vấn 'AC Mobile Device Token' (pluck fcm_token). Mọi get_all khác
    (nếu có) trả [] an toàn — test này KHÔNG kích nhánh get_all nào khác.
    """

    def _impl(doctype, *args, **kwargs):
        if doctype == "AC Mobile Device Token":
            user = (kwargs.get("filters") or {}).get("user")
            return list(rows_by_user.get(user, []))
        return []

    return _impl


class TestMobilePushDispatch(unittest.TestCase):
    """Nhóm AUTO D6 — kênh #3 push trong `_dispatch`. Mock-FCM, XANH KHÔNG cần migrate."""

    def _run_dispatch(self, *, users, doc, tokens_by_user, fcm_side_effect=None,
                      wants_email=True):
        """Chạy `_dispatch` với kênh 1/2/token-lookup/FCM bị mock.

        Trả (mock_enqueue, mock_sendmail, mock_send_fcm) để assert side-effect.
        """
        with mock.patch.object(notif, "enqueue_create_notification") as menq, \
                mock.patch.object(notif, "_safe_sendmail") as msend, \
                mock.patch.object(notif, "_user_wants_email", return_value=wants_email), \
                mock.patch.object(notif.frappe, "get_all",
                                  side_effect=_fake_token_get_all(tokens_by_user)), \
                mock.patch("assetcore.utils.fcm.send_fcm_message",
                           side_effect=fcm_side_effect) as mfcm:
            notif._dispatch(users, "<b>Sự cố mới</b>", "<i>Vui lòng xử lý</i>", doc)
        return menq, msend, mfcm

    # TC-D6-01 fan-out CHỈ token enabled=1 ----------------------------------
    def test_d6_01_dispatch_pushes_only_enabled_tokens(self) -> None:
        """User có token enabled=1 → send_fcm_message gọi ĐÚNG token đó.

        (get_all đã filter enabled=1 ở repo-layer; assert token enabled=1 nhận,
        token enabled=0 KHÔNG trong kết quả get_all ⇒ KHÔNG được gọi.)
        """
        _menq, _msend, mfcm = self._run_dispatch(
            users=["ktv-a@x.com"],
            doc=_DocStub(),
            tokens_by_user={"ktv-a@x.com": ["TOK-ENABLED"]},  # enabled=0 KHÔNG có trong list
        )
        self.assertEqual(mfcm.call_count, 1, "đúng 1 push cho 1 token enabled=1")
        self.assertEqual(mfcm.call_args.args[0], "TOK-ENABLED",
                         "push gửi tới token enabled=1")

    def test_d6_01_disabled_only_user_gets_no_push(self) -> None:
        """User CHỈ có token enabled=0 (get_all trả []) → 0 lần gọi send_fcm_message."""
        _menq, _msend, mfcm = self._run_dispatch(
            users=["ktv-b@x.com"],
            doc=_DocStub(),
            tokens_by_user={"ktv-b@x.com": []},  # enabled=1 filter → rỗng
        )
        self.assertEqual(mfcm.call_count, 0, "token enabled=0 → KHÔNG push")

    # TC-D6-02 fail-safe: FCM raise → kênh 1+2 VẪN chạy ----------------------
    def test_d6_02_fcm_raise_does_not_break_inapp_email(self) -> None:
        """send_fcm_message raise Exception → `_dispatch` KHÔNG raise; kênh 1+2 VẪN gọi."""
        menq, msend, mfcm = self._run_dispatch(
            users=["ktv-a@x.com"],
            doc=_DocStub(),
            tokens_by_user={"ktv-a@x.com": ["TOK-1"]},
            fcm_side_effect=RuntimeError("FCM transport boom"),
        )
        # Kênh 1 in-app VẪN gọi (trước push trong thân _dispatch).
        self.assertTrue(menq.called, "kênh 1 in-app PHẢI gọi dù FCM raise")
        # Kênh 2 email VẪN gọi (wants_email=True).
        self.assertTrue(msend.called, "kênh 2 email PHẢI gọi dù FCM raise")
        # FCM đã được thử (raise bị nuốt fail-safe — KHÔNG vỡ _dispatch).
        self.assertTrue(mfcm.called, "push được thử trước khi raise bị nuốt")

    # TC-D6-03 payload shape §5.3/§5.5 --------------------------------------
    def test_d6_03_payload_shape(self) -> None:
        """title/body strip-HTML + body≤1000; data{doctype,name,event,deeplink} (§5.3)."""
        long_msg = "<b>x</b>" + ("a" * 2000)
        with mock.patch.object(notif, "enqueue_create_notification"), \
                mock.patch.object(notif, "_safe_sendmail"), \
                mock.patch.object(notif, "_user_wants_email", return_value=False), \
                mock.patch.object(notif.frappe, "get_all",
                                  side_effect=_fake_token_get_all({"u@x.com": ["TOK-1"]})), \
                mock.patch("assetcore.utils.fcm.send_fcm_message") as mfcm:
            notif._dispatch(["u@x.com"], "<i>Sự cố mới</i>", long_msg,
                            _DocStub("Incident Report", "INC-2026-0042"))

        self.assertEqual(mfcm.call_count, 1)
        kw = mfcm.call_args.kwargs
        # title/body strip-HTML.
        self.assertEqual(kw["title"], "Sự cố mới", "title = strip_html(subject)")
        self.assertNotIn("<", kw["body"], "body phải strip-HTML")
        self.assertLessEqual(len(kw["body"]), 1000, "body cắt ≤1000 (§5.3)")
        # data routing keys.
        data = kw["data"]
        self.assertEqual(data["doctype"], "Incident Report", "data.doctype == doc.doctype")
        self.assertEqual(data["name"], "INC-2026-0042", "data.name == doc.name")
        self.assertEqual(data["event"], "incident_created", "E3 event (§5.5)")
        self.assertEqual(data["deeplink"], "assetcore://incident/INC-2026-0042",
                         "E3 deeplink (§5.4)")

    def test_d6_03_route_table_maps_per_doctype(self) -> None:
        """_push_event_route map đúng theo doctype (§5.5) + fallback an toàn."""
        self.assertEqual(
            notif._push_event_route(_DocStub("Incident Report", "INC-1")),
            ("incident_created", "assetcore://incident/INC-1", "high"))
        self.assertEqual(
            notif._push_event_route(_DocStub("Asset Repair", "WO-CM-1")),
            ("repair_assigned", "assetcore://wo/cm/WO-CM-1", "high"))
        self.assertEqual(
            notif._push_event_route(_DocStub("PM Work Order", "WO-PM-1")),
            ("pm_assignment", "assetcore://wo/pm/WO-PM-1", "normal"))
        self.assertEqual(
            notif._push_event_route(_DocStub("AC Asset", "AC-1")),
            ("calibration_due", "assetcore://asset/AC-1", "normal"))
        # Fallback: doctype lạ → notification, KHÔNG deeplink.
        ev, dl, pr = notif._push_event_route(_DocStub("Some Other DocType", "X-1"))
        self.assertEqual(ev, "notification")
        self.assertEqual(dl, "", "doctype lạ → bỏ deeplink")
        # name rỗng → fallback (kể cả doctype khớp).
        ev2, dl2, _ = notif._push_event_route(_DocStub("Incident Report", ""))
        self.assertEqual(ev2, "notification")
        self.assertEqual(dl2, "")

    def test_d6_03_fallback_doctype_omits_deeplink_key(self) -> None:
        """doctype lạ → data KHÔNG có key 'deeplink' (APK mở inbox)."""
        with mock.patch.object(notif, "enqueue_create_notification"), \
                mock.patch.object(notif, "_safe_sendmail"), \
                mock.patch.object(notif, "_user_wants_email", return_value=False), \
                mock.patch.object(notif.frappe, "get_all",
                                  side_effect=_fake_token_get_all({"u@x.com": ["TOK-1"]})), \
                mock.patch("assetcore.utils.fcm.send_fcm_message") as mfcm:
            notif._dispatch(["u@x.com"], "Sub", "Msg",
                            _DocStub("Mystery DocType", "M-1"))
        data = mfcm.call_args.kwargs["data"]
        self.assertEqual(data["event"], "notification")
        self.assertNotIn("deeplink", data, "fallback KHÔNG có deeplink key")

    # TC-D6-04 no-token recipient → 0 push, kênh 1+2 vẫn gửi -----------------
    def test_d6_04_no_token_recipient_skips_push_keeps_channels(self) -> None:
        """Recipient KHÔNG có token enabled=1 → 0 push; in-app + email VẪN gửi."""
        menq, msend, mfcm = self._run_dispatch(
            users=["no-token@x.com"],
            doc=_DocStub(),
            tokens_by_user={},  # user không có token nào
        )
        self.assertEqual(mfcm.call_count, 0, "không token → 0 push")
        self.assertTrue(menq.called, "in-app VẪN gửi")
        self.assertTrue(msend.called, "email VẪN gửi")

    # TC-D6-05 creds-absent → send_fcm_message None no-op, _dispatch sạch -----
    def test_d6_05_creds_absent_noop_dispatch_clean(self) -> None:
        """send_fcm_message trả None (creds thiếu D3) → push no-op, _dispatch KHÔNG raise."""
        menq, msend, mfcm = self._run_dispatch(
            users=["ktv-a@x.com"],
            doc=_DocStub(),
            tokens_by_user={"ktv-a@x.com": ["TOK-1"]},
            fcm_side_effect=lambda *a, **k: None,  # creds-absent → None
        )
        self.assertEqual(mfcm.call_count, 1, "vẫn thử gọi (sender tự no-op None)")
        self.assertTrue(menq.called, "in-app VẪN gửi khi creds thiếu")
        self.assertTrue(msend.called, "email VẪN gửi khi creds thiếu")

    # TC-D6-07 multi-token same user → push mỗi device 1 lần -----------------
    def test_d6_07_multi_token_same_user(self) -> None:
        """User có 2 token enabled=1 → send_fcm_message gọi 2 lần (mỗi device 1 message)."""
        _menq, _msend, mfcm = self._run_dispatch(
            users=["ktv-a@x.com"],
            doc=_DocStub(),
            tokens_by_user={"ktv-a@x.com": ["TOK-D1", "TOK-D2"]},
        )
        self.assertEqual(mfcm.call_count, 2, "2 device enabled=1 → 2 push")
        sent_tokens = {c.args[0] for c in mfcm.call_args_list}
        self.assertEqual(sent_tokens, {"TOK-D1", "TOK-D2"}, "mỗi token nhận đúng 1 lần")

    def test_d6_07_multi_user_dedup_fanout(self) -> None:
        """2 recipient, mỗi người 1 token → 2 push tới đúng từng token."""
        _menq, _msend, mfcm = self._run_dispatch(
            users=["a@x.com", "b@x.com"],
            doc=_DocStub(),
            tokens_by_user={"a@x.com": ["TOK-A"], "b@x.com": ["TOK-B"]},
        )
        self.assertEqual(mfcm.call_count, 2)
        self.assertEqual({c.args[0] for c in mfcm.call_args_list}, {"TOK-A", "TOK-B"})


class TestMobileRegisterRateLimit(unittest.TestCase):
    """TC-D6-08 — @rate_limit chống spam đăng ký register_device_token (06 §5.3/§5.5)."""

    def test_d6_08_register_handler_has_rate_limit(self) -> None:
        """register_device_token: rate-limit ĐÃ wired + dispatcher VẪN resolve được.

        Bịt false-green LL-TEST-26: chỉ check "có @rate_limit" KHÔNG đủ — order sai
        (rate_limit NGOÀI whitelist) ⇒ is_whitelisted FAIL ⇒ MỌI POST 403 dù decorator
        có mặt. Assert HIỆN-VẬT THẬT: dispatcher path get_attr → is_whitelisted PASS
        (KHÔNG raise PermissionError) + hàm là wrapper rate_limit (__wrapped__).
        """
        import frappe

        from assetcore.api.mobile.v1 import device_token as dt

        # Hằng ngưỡng phải tồn tại + dương (wiring same-commit).
        self.assertTrue(hasattr(dt, "_REGISTER_RATE_LIMIT"))
        self.assertGreater(dt._REGISTER_RATE_LIMIT, 0)
        fn = dt.register_device_token
        self.assertTrue(callable(fn))
        # rate_limit dùng @wraps → wrapper có __wrapped__ trỏ handler gốc.
        self.assertTrue(hasattr(fn, "__wrapped__"), "register phải qua @rate_limit (wrapper)")
        # GATE THẬT dispatcher (handler.py): get_attr → is_whitelisted. Order sai sẽ
        # raise PermissionError ở đây (chính là regression test_mob_oas_22j bắt được).
        frappe.local.request = frappe._dict({"method": "POST"})
        resolved = frappe.get_attr("assetcore.api.mobile.v1.register_device_token")
        try:
            frappe.is_whitelisted(resolved)
        except Exception as exc:  # noqa: BLE001
            self.fail(
                f"register_device_token resolve nhưng is_whitelisted BLOCK ({type(exc).__name__}) "
                f"→ @rate_limit đặt SAI thứ tự (phải TRONG @frappe.whitelist)."
            )

    def test_d6_08_register_source_has_decorator(self) -> None:
        """Source-level guard: @frappe.whitelist NGOÀI, @rate_limit TRONG (pattern imm00:427).

        Đọc AST: decorator list của register_device_token gồm 'rate_limit' và
        'whitelist', và whitelist đứng TRƯỚC rate_limit (ngoài cùng).

        VÌ SAO whitelist phải NGOÀI: @frappe.whitelist đăng ký vào registry theo OBJECT
        hàm nó bọc. Nếu @rate_limit bọc NGOÀI → registry giữ hàm-trần (inner) nhưng attr
        module = wrapper rate_limit ⇒ dispatcher get_attr() trả wrapper ⇒ is_whitelisted
        FAIL ⇒ MỌI POST 403 "not whitelisted" (regression D6, bắt bởi test_mob_oas_22j).
        @rate_limit ở TRONG vẫn raise 429 TRƯỚC thân handler (chống spam giữ nguyên).
        """
        import ast
        import inspect

        from assetcore.api.mobile.v1 import device_token as dt

        src = inspect.getsource(dt)
        tree = ast.parse(src)
        reg = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "register_device_token"
        )
        names = []
        for d in reg.decorator_list:
            # @rate_limit(...) → Call(func=Name/Attribute); @whitelist(...) tương tự.
            node = d.func if isinstance(d, ast.Call) else d
            if isinstance(node, ast.Attribute):
                names.append(node.attr)
            elif isinstance(node, ast.Name):
                names.append(node.id)
        self.assertIn("rate_limit", names, "register phải có @rate_limit")
        self.assertIn("whitelist", names, "register giữ @frappe.whitelist")
        self.assertLess(
            names.index("whitelist"), names.index("rate_limit"),
            "@frappe.whitelist phải NGOÀI @rate_limit (is_whitelisted resolve wrapper; "
            "rate_limit ở trong vẫn 429 trước handler) — pattern imm00.py:427",
        )

    def test_d6_08_unregister_not_throttled(self) -> None:
        """unregister_device_token KHÔNG có @rate_limit (opt-out luôn cho phép)."""
        import ast
        import inspect

        from assetcore.api.mobile.v1 import device_token as dt

        tree = ast.parse(inspect.getsource(dt))
        unreg = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "unregister_device_token"
        )
        names = []
        for d in unreg.decorator_list:
            node = d.func if isinstance(d, ast.Call) else d
            if isinstance(node, ast.Attribute):
                names.append(node.attr)
            elif isinstance(node, ast.Name):
                names.append(node.id)
        self.assertNotIn("rate_limit", names, "unregister KHÔNG throttle (§5.5)")


class TestMobilePushDispatchDB(unittest.TestCase):
    """TC-D6-06 (DoD E3) — fan-out token THẬT. RED-pending-migrate.

    Cần bảng `tabAC Mobile Device Token` (HARD-STOP USER `bench migrate`). Tạo
    Incident Report assigned_to=KTV-A (token enabled=1) → after_insert E3 (:562) →
    `_dispatch` mock-FCM push tới KTV-A đúng 1 lần; KTV-B (token enabled=1 nhưng
    KHÔNG được giao) → 0 push. Khi chưa migrate → SKIP sạch (ghi open_issues).
    """

    def setUp(self) -> None:
        if not frappe.db.table_exists("AC Mobile Device Token"):
            self.skipTest(
                "tabAC Mobile Device Token chưa tồn tại — cần "
                "`bench --site miyano migrate` (HARD-STOP USER). "
                "TC-D6-06 DoD E3 fan-out = RED-pending-migrate."
            )
        self._created: list[tuple[str, str]] = []
        frappe.set_user("Administrator")

    def tearDown(self) -> None:
        for dt_name, name in reversed(getattr(self, "_created", [])):
            try:
                frappe.delete_doc(dt_name, name, force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def test_d6_06_dod_e3_fanout_only_assigned_recipient(self) -> None:
        """E3 push CHỈ tới token của recipient được giao (KTV-A), KTV-B 0 push.

        Side-effect THẬT qua bảng device-token; FCM mock để đếm push (chống
        false-green LL-TEST-21). RED-pending-migrate tới khi USER migrate.
        """
        ktv_a, ktv_b = "ktv-a@example.com", "ktv-b@example.com"
        if not frappe.db.exists("User", ktv_a) or not frappe.db.exists("User", ktv_b):
            self.skipTest(
                f"User test {ktv_a}/{ktv_b} chưa tồn tại trên site — "
                "RED-pending fixture (HARD-STOP USER). TC-D6-06 SKIP."
            )
        for u in (ktv_a, ktv_b):
            tok = frappe.get_doc({
                "doctype": "AC Mobile Device Token",
                "user": u, "fcm_token": f"DOD-{u}", "platform": "android", "enabled": 1,
            })
            tok.insert(ignore_permissions=True)
            self._created.append(("AC Mobile Device Token", tok.name))

        sent: list[str] = []
        with mock.patch("assetcore.utils.fcm.send_fcm_message",
                        side_effect=lambda token, **k: sent.append(token)):
            notif._dispatch([ktv_a], "Sự cố mới", "Xử lý",
                            _DocStub("Incident Report", "INC-DOD-1"))

        self.assertIn(f"DOD-{ktv_a}", sent, "KTV-A (được giao) nhận push")
        self.assertNotIn(f"DOD-{ktv_b}", sent, "KTV-B (KHÔNG giao) KHÔNG nhận push")
        self.assertEqual(len(sent), 1, "đúng 1 push (1 recipient, 1 token enabled=1)")


# ════════════════════════════════════════════════════════════════════════════
# D7 — RBAC row-level self-scope (IDOR negative) cho `AC Mobile Device Token`
#   Spec: docs/mobile/completion/EPIC-D-push-fcm.md §6.1 (self-scope bearer-gated)
#         · permissions.py:268/285 · hooks.py:395/404 (wired)
#
#   GAP THẬT (Vòng 20): grep chỉ thấy COMMENT, 0 TestCase exercise 2 hàm
#   `ac_mobile_device_token_query` + `ac_mobile_device_token_has_permission`.
#   Nhóm LOGIC (TC-D7-01..05) = XANH KHÔNG cần migrate: introspect 2 hàm thuần
#   (mock `_user_roles` để bơm vai — KHÔNG đụng bảng tabAC Mobile Device Token,
#   KHÔNG cần user DB thật). Nhóm DB (TC-D7-09 IDOR get_list THẬT) =
#   RED-pending-migrate → SKIP sạch (HARD-STOP USER `bench migrate`).
#
#   KHÔNG sửa impl: permissions.py:268/285 + hooks.py:395/404 ĐÃ khớp spec §6.1
#   (re-verify @source Vòng 20) — D7 CHỈ thêm test (anti-false-green LL-TEST-21:
#   2 hàm permission TRƯỚC giờ 0 TestCase ⇒ self-scope chưa từng bị exercise).
# ════════════════════════════════════════════════════════════════════════════

from assetcore import permissions as perms  # noqa: E402

# Vai field-tech "thường" (KTV nội bộ) — KHÔNG senior, KHÔNG Auditor. Bất kỳ role
# nào ngoài _SENIOR_ROLES/_AUDITOR_ROLE đều rơi nhánh self-scope (06 §6.1). Dùng
# base role Role Profile "Kỹ thuật viên" cho sát thực tế (KHÔNG ảnh hưởng logic:
# nhánh self-scope chỉ cần "không senior, không auditor").
_FIELD_TECH_ROLES = {"AssetCore System User", "PM User"}
_SENIOR_SAMPLE = {"PM Manager"}              # 1 module-manager (∈ _SENIOR_ROLES)
_SYS_MGR_ROLES = {"System Manager"}          # core admin (∈ _SENIOR_ROLES)
_AUDITOR_ROLES = {"AssetCore Auditor"}       # read-all NĐ98 (read ptypes only)

_USER_A = "ktv-a@example.com"                 # chủ token (victim của IDOR)
_USER_B = "ktv-b@example.com"                 # kẻ enumerate (field-tech thường)


class TestMobileDeviceTokenSelfScope(unittest.TestCase):
    """Nhóm LOGIC D7 — self-scope query + has_permission IDOR. XANH KHÔNG cần migrate.

    Mock `permissions._user_roles` để bơm vai (KHÔNG cần user DB / migrate). 2 hàm
    `ac_mobile_device_token_query` + `ac_mobile_device_token_has_permission` được
    exercise lần đầu (GAP Vòng 20: trước đó 0 TestCase).
    """

    def _patch_roles(self, roles: set[str]):
        """Bơm tập role cho user bất kỳ (cả _user_roles(user) lẫn _user_roles(None))."""
        return mock.patch.object(perms, "_user_roles", return_value=set(roles))

    # TC-D7-01 self-scope query field-tech ----------------------------------
    def test_d7_01_query_field_tech_self_scope(self) -> None:
        """field-tech thường → điều kiện CHỈ chứa user CỦA MÌNH (KHÔNG '' read-all).

        ⇒ list-scope (permission_query_conditions) chỉ trả token user-B; get_list
        dưới user-B KHÔNG kéo token user-A (chống IDOR enumerate list-level).
        """
        with self._patch_roles(_FIELD_TECH_ROLES):
            cond = perms.ac_mobile_device_token_query(_USER_B)
        self.assertNotEqual(cond, "", "field-tech KHÔNG được read-all ('')")
        self.assertIn(
            f"user = '{_USER_B}'", cond,
            "điều kiện phải khoá user == session.user (self-scope §6.1)",
        )
        # KHÔNG được lộ user khác trong điều kiện (IDOR list-level).
        self.assertNotIn(_USER_A, cond, "self-scope KHÔNG được chứa user khác")
        # Escape-safe: bám đúng field `user` của bảng device-token.
        self.assertIn("`tabAC Mobile Device Token`.user", cond)

    def test_d7_01_query_escape_safe_no_sqli(self) -> None:
        """user chứa quote → _esc (frappe.db.escape) trung hoà, KHÔNG mở SQLi."""
        evil = "x' OR '1'='1"
        with self._patch_roles(_FIELD_TECH_ROLES):
            cond = perms.ac_mobile_device_token_query(evil)
        # _esc nhân đôi quote ⇒ KHÔNG có chuỗi `OR '1'='1` thoát ra ngoài literal.
        self.assertNotIn("OR '1'='1'", cond, "escape phải trung hoà payload SQLi")
        self.assertIn("user = '", cond, "vẫn là điều kiện self-scope hợp lệ")

    # TC-D7-02 self-scope query senior/SysMgr/Auditor → '' read-all ----------
    def test_d7_02_query_senior_read_all(self) -> None:
        """module-manager (senior) → '' (read-all ops/chẩn đoán §6.1)."""
        with self._patch_roles(_SENIOR_SAMPLE):
            self.assertEqual(perms.ac_mobile_device_token_query(_USER_B), "")

    def test_d7_02_query_system_manager_read_all(self) -> None:
        """System Manager (core admin) → '' read-all."""
        with self._patch_roles(_SYS_MGR_ROLES):
            self.assertEqual(perms.ac_mobile_device_token_query(_USER_B), "")

    def test_d7_02_query_auditor_read_all(self) -> None:
        """Auditor → '' read-all (NĐ98 audit trail)."""
        with self._patch_roles(_AUDITOR_ROLES):
            self.assertEqual(perms.ac_mobile_device_token_query(_USER_B), "")

    # TC-D7-03 has_permission IDOR negative ----------------------------------
    def test_d7_03_has_perm_cross_user_read_false(self) -> None:
        """doc(user=A), user=B (field-tech) đọc → False (chặn IDOR enumerate)."""
        doc = {"user": _USER_A}
        with self._patch_roles(_FIELD_TECH_ROLES):
            self.assertFalse(
                perms.ac_mobile_device_token_has_permission(doc, "read", _USER_B),
                "field-tech KHÔNG được đọc token user khác (IDOR)",
            )

    def test_d7_03_has_perm_cross_user_write_delete_false(self) -> None:
        """doc(user=A), user=B → write/delete cũng False (chặn sửa/xoá device người khác)."""
        doc = {"user": _USER_A}
        with self._patch_roles(_FIELD_TECH_ROLES):
            for ptype in ("write", "delete", "create", "submit", "cancel"):
                self.assertFalse(
                    perms.ac_mobile_device_token_has_permission(doc, ptype, _USER_B),
                    f"field-tech KHÔNG được {ptype} token user khác (IDOR)",
                )

    # TC-D7-04 has_permission owner positive ---------------------------------
    def test_d7_04_has_perm_owner_dict_true(self) -> None:
        """doc dạng dict {'user':A}, user=A → True (Frappe truyền dict thường gặp)."""
        doc = {"user": _USER_A}
        with self._patch_roles(_FIELD_TECH_ROLES):
            for ptype in ("read", "write", "delete"):
                self.assertTrue(
                    perms.ac_mobile_device_token_has_permission(doc, ptype, _USER_A),
                    f"chủ token PHẢI được {ptype} token CỦA MÌNH",
                )

    def test_d7_04_has_perm_owner_document_obj_true(self) -> None:
        """doc dạng object (.user attr, KHÔNG .get) — chủ token → True.

        `ac_mobile_device_token_has_permission` đọc `doc.get('user')` nếu có `.get`,
        ngược lại `getattr(doc,'user')` → phải hỗ trợ cả Document lẫn dict.
        """
        class _Obj:
            user = _USER_A

        with self._patch_roles(_FIELD_TECH_ROLES):
            self.assertTrue(
                perms.ac_mobile_device_token_has_permission(_Obj(), "read", _USER_A),
                "object có .user (Document) — chủ token đọc được",
            )

    # TC-D7-05 senior True mọi ptype; Auditor chỉ read ptypes ----------------
    def test_d7_05_has_perm_senior_true_all_ptypes(self) -> None:
        """Senior (ops) → True MỌI ptype kể cả token user khác (chẩn đoán §6.1)."""
        doc = {"user": _USER_A}
        with self._patch_roles(_SENIOR_SAMPLE):
            for ptype in ("read", "write", "delete", "create"):
                self.assertTrue(
                    perms.ac_mobile_device_token_has_permission(doc, ptype, _USER_B),
                    f"senior PHẢI có {ptype} (ops/chẩn đoán)",
                )

    def test_d7_05_has_perm_system_manager_true_all_ptypes(self) -> None:
        """System Manager → True mọi ptype (core admin)."""
        doc = {"user": _USER_A}
        with self._patch_roles(_SYS_MGR_ROLES):
            for ptype in ("read", "write", "delete"):
                self.assertTrue(
                    perms.ac_mobile_device_token_has_permission(doc, ptype, _USER_B)
                )

    def test_d7_05_has_perm_auditor_read_only(self) -> None:
        """Auditor → True CHỈ read/print/email/export; write/delete → False (read-only NĐ98)."""
        doc = {"user": _USER_A}
        with self._patch_roles(_AUDITOR_ROLES):
            for ptype in ("read", "print", "email", "export"):
                self.assertTrue(
                    perms.ac_mobile_device_token_has_permission(doc, ptype, _USER_B),
                    f"Auditor PHẢI có {ptype} (read-only audit)",
                )
            for ptype in ("write", "delete", "create", "submit", "cancel"):
                self.assertFalse(
                    perms.ac_mobile_device_token_has_permission(doc, ptype, _USER_B),
                    f"Auditor KHÔNG được {ptype} (read-only NĐ98)",
                )

    def test_d7_05_wiring_query_and_has_perm_registered(self) -> None:
        """Same-commit wiring: hooks.py trỏ ĐÚNG 2 hàm self-scope (§6.1)."""
        from assetcore import hooks

        self.assertEqual(
            hooks.permission_query_conditions.get("AC Mobile Device Token"),
            "assetcore.permissions.ac_mobile_device_token_query",
            "permission_query_conditions phải wire ac_mobile_device_token_query",
        )
        self.assertEqual(
            hooks.has_permission.get("AC Mobile Device Token"),
            "assetcore.permissions.ac_mobile_device_token_has_permission",
            "has_permission phải wire ac_mobile_device_token_has_permission",
        )


# ════════════════════════════════════════════════════════════════════════════
# D7 — DoD E3 qua hook-chain THẬT (checklist D-A3): Incident Report after_insert
#   → notify_incident_created (hooks.py:270 → notifications.py:609) → kênh #3
#   mock-FCM push ĐÚNG 1 lần tới recipient được giao (KTV-A).
#
#   Bổ trợ test_d6_06 (DB) hiện chỉ gọi `_dispatch` trực tiếp với _DocStub:
#   ĐÂY đi qua ĐIỂM VÀO THẬT của hook chain (notify_incident_created), kích đúng
#   _push_event_route(Incident Report) → event=incident_created + deeplink.
#   Side-effect THẬT (send_fcm_message call_args), KHÔNG chỉ return (LL-TEST-21).
#   Anti-spam (LL-TEST-18): chạy 2× → KHÔNG nhân đôi push trong MỖI dispatch.
#
#   100% mock (session/get_all/FCM/kênh 1+2) ⇒ XANH KHÔNG cần migrate/creds.
# ════════════════════════════════════════════════════════════════════════════


class _IncidentDocStub:
    """Incident Report tối thiểu cho notify_incident_created (E3 entry-point).

    Hỗ trợ `.get(field)` (Frappe Document API) + `.doctype/.name/.docstatus` +
    field nghiệp vụ (assigned_to/reported_by/severity/asset). KHÔNG đụng DB.
    """

    def __init__(self, *, name="INC-2026-0042", assigned_to=None, reported_by=None,
                 severity="Major", asset="AC-0001", docstatus=0):
        self.doctype = "Incident Report"
        self.name = name
        self.docstatus = docstatus
        self.assigned_to = assigned_to
        self.reported_by = reported_by
        self.severity = severity
        self.asset = asset

    def get(self, field, default=None):
        return getattr(self, field, default)


class TestMobileDeviceTokenDoDE3HookChain(unittest.TestCase):
    """TC-D7-06/07 — DoD E3 push qua notify_incident_created (entry-point THẬT).

    Mock-FCM + mock token lookup (get_all) + mock kênh 1/2. XANH KHÔNG cần migrate.
    Actor (session.user) = người khác recipient để resolve_recipients GIỮ assignee.
    """

    _ACTOR = "dispatcher@example.com"   # session.user — KHÁC KTV-A (giữ assignee)

    def _run_e3(self, doc, tokens_by_user, *, fcm_side_effect=None):
        """Chạy notify_incident_created với 4 seam mock; trả (mfcm, menq, msend)."""
        with mock.patch.object(notif.frappe, "session") as msess, \
                mock.patch.object(notif, "enqueue_create_notification") as menq, \
                mock.patch.object(notif, "_safe_sendmail") as msend, \
                mock.patch.object(notif, "_user_wants_email", return_value=False), \
                mock.patch.object(notif.frappe, "get_all",
                                  side_effect=_fake_token_get_all(tokens_by_user)), \
                mock.patch("assetcore.utils.fcm.send_fcm_message",
                           side_effect=fcm_side_effect) as mfcm:
            msess.user = self._ACTOR
            notif.notify_incident_created(doc)
        return mfcm, menq, msend

    # TC-D7-06 DoD E3 hook-chain: push ĐÚNG 1 lần tới KTV-A; KTV-B 0 push ------
    def test_d7_06_e3_hookchain_pushes_only_assigned(self) -> None:
        """Incident assigned_to=KTV-A token enabled=1 → mock FCM push ĐÚNG 1 lần KTV-A.

        KTV-B (KHÔNG được giao, dù có token) → 0 push. Đi qua entry-point THẬT
        notify_incident_created (KHÔNG gọi _dispatch trực tiếp) — side-effect THẬT.
        """
        doc = _IncidentDocStub(assigned_to=_USER_A)
        mfcm, menq, msend = self._run_e3(
            doc,
            tokens_by_user={_USER_A: ["TOK-A"], _USER_B: ["TOK-B"]},
        )
        self.assertEqual(mfcm.call_count, 1, "đúng 1 push (1 recipient được giao)")
        self.assertEqual(mfcm.call_args.args[0], "TOK-A", "push tới token KTV-A (được giao)")
        sent_tokens = {c.args[0] for c in mfcm.call_args_list}
        self.assertNotIn("TOK-B", sent_tokens, "KTV-B KHÔNG được giao → 0 push")
        # Kênh 1 in-app VẪN gửi (E3 đi đủ chain).
        self.assertTrue(menq.called, "kênh 1 in-app VẪN chạy trong E3 chain")

    def test_d7_06_e3_payload_event_is_incident_created(self) -> None:
        """E3 qua entry-point THẬT → data.event=incident_created + deeplink incident (§5.4/§5.5)."""
        doc = _IncidentDocStub(name="INC-E3-1", assigned_to=_USER_A)
        mfcm, _menq, _msend = self._run_e3(doc, tokens_by_user={_USER_A: ["TOK-A"]})
        self.assertEqual(mfcm.call_count, 1)
        data = mfcm.call_args.kwargs["data"]
        self.assertEqual(data["event"], "incident_created", "route Incident → incident_created")
        self.assertEqual(data["deeplink"], "assetcore://incident/INC-E3-1", "deeplink E3 (§5.4)")
        self.assertEqual(data["doctype"], "Incident Report")
        self.assertEqual(data["name"], "INC-E3-1")

    def test_d7_06_e3_unassigned_self_confirm_to_reporter(self) -> None:
        """Chưa phân công ai → self-confirm tới reported_by (token reporter nhận push)."""
        # actor = reporter (self-confirm GIỮ actor); resolve_recipients include_self.
        reporter = self._ACTOR
        doc = _IncidentDocStub(assigned_to=None, reported_by=reporter)
        mfcm, _menq, _msend = self._run_e3(doc, tokens_by_user={reporter: ["TOK-R"]})
        self.assertEqual(mfcm.call_count, 1, "self-confirm → push 1 lần tới reporter")
        self.assertEqual(mfcm.call_args.args[0], "TOK-R")

    # TC-D7-07 anti-spam: chạy 2× KHÔNG nhân đôi (LL-TEST-18) -----------------
    def test_d7_07_e3_anti_spam_no_double_per_dispatch(self) -> None:
        """Chạy E3 2× → MỖI lần push ĐÚNG 1/token (KHÔNG nhân đôi trong 1 dispatch).

        notify_incident_created/`_dispatch` stateless per-call: mỗi invocation
        fan-out đúng 1 push/token/recipient (dedupe :377 dict.fromkeys). 2 lần gọi
        ⇒ 2 push TỔNG (1 mỗi lần) — KHÔNG phải 4 (KHÔNG tích luỹ/nhân đôi nội bộ).
        """
        doc = _IncidentDocStub(assigned_to=_USER_A)
        per_call_counts = []
        for _ in range(2):
            mfcm, _menq, _msend = self._run_e3(doc, tokens_by_user={_USER_A: ["TOK-A"]})
            per_call_counts.append(mfcm.call_count)
        self.assertEqual(
            per_call_counts, [1, 1],
            "MỖI dispatch push ĐÚNG 1/token (KHÔNG nhân đôi nội bộ — LL-TEST-18)",
        )

    def test_d7_07_e3_duplicate_recipient_dedup_single_push(self) -> None:
        """assignee trùng reporter (cùng user) → dedupe :377 → 1 push (KHÔNG 2)."""
        # assigned_to set → nhánh cross-assign; chỉ 1 recipient KTV-A dù trùng reporter.
        doc = _IncidentDocStub(assigned_to=_USER_A, reported_by=_USER_A)
        mfcm, _menq, _msend = self._run_e3(doc, tokens_by_user={_USER_A: ["TOK-A"]})
        self.assertEqual(mfcm.call_count, 1, "recipient trùng → dedupe → 1 push")

    def test_d7_07_e3_cancelled_incident_no_push(self) -> None:
        """Incident docstatus=2 (cancel) → notify skip → 0 push (an toàn)."""
        doc = _IncidentDocStub(assigned_to=_USER_A, docstatus=2)
        mfcm, menq, _msend = self._run_e3(doc, tokens_by_user={_USER_A: ["TOK-A"]})
        self.assertEqual(mfcm.call_count, 0, "incident cancel → KHÔNG push")
        self.assertFalse(menq.called, "incident cancel → KHÔNG cả in-app")


class TestMobileDeviceTokenSelfScopeDB(unittest.TestCase):
    """TC-D7-09 — IDOR get_list THẬT trên bảng. RED-pending-migrate.

    Cần bảng `tabAC Mobile Device Token` + permission_query_conditions áp runtime
    (HARD-STOP USER `bench migrate`). user-B `get_list` KHÔNG thấy token user-A.
    Khi chưa migrate → SKIP sạch (ghi open_issues, KHÔNG chữa vô hạn).
    """

    def setUp(self) -> None:
        if not frappe.db.table_exists("AC Mobile Device Token"):
            self.skipTest(
                "tabAC Mobile Device Token chưa tồn tại — cần "
                "`bench --site miyano migrate` (HARD-STOP USER). "
                "TC-D7-09 IDOR get_list THẬT = RED-pending-migrate."
            )
        self._created: list[str] = []
        frappe.set_user("Administrator")

    def tearDown(self) -> None:
        for name in getattr(self, "_created", []):
            try:
                frappe.delete_doc(
                    "AC Mobile Device Token", name, force=True, ignore_permissions=True
                )
            except Exception:
                pass
        frappe.db.rollback()
        frappe.set_user("Administrator")

    def _seed(self, user: str, token: str) -> str:
        doc = frappe.get_doc({
            "doctype": "AC Mobile Device Token",
            "user": user, "fcm_token": token, "platform": "android", "enabled": 1,
        })
        doc.insert(ignore_permissions=True)
        self._created.append(doc.name)
        return doc.name

    def test_d7_09_idor_get_list_excludes_other_user_token(self) -> None:
        """user-B (field-tech thường) get_list KHÔNG thấy token user-A (IDOR list-level)."""
        if not frappe.db.exists("User", _USER_A) or not frappe.db.exists("User", _USER_B):
            self.skipTest(
                f"User test {_USER_A}/{_USER_B} chưa tồn tại trên site — "
                "RED-pending fixture (HARD-STOP USER). TC-D7-09 SKIP."
            )
        a_tok = self._seed(_USER_A, "IDOR-A")
        self._seed(_USER_B, "IDOR-B")
        try:
            frappe.set_user(_USER_B)
            names = {
                r["name"] for r in frappe.get_list(
                    "AC Mobile Device Token", fields=["name", "user"], limit_page_length=0
                )
            }
        finally:
            frappe.set_user("Administrator")
        self.assertNotIn(
            a_tok, names, "user-B get_list KHÔNG được thấy token user-A (self-scope §6.1)"
        )
