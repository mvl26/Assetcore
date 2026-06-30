# Copyright (c) 2026, AssetCore Team
"""IMM-00 Base role invariant — định danh "user AssetCore".

Yêu cầu (2026-06-29): user tạo từ UI AssetCore mặc định có base role
`AssetCore System User`; base role là BẮT BUỘC và KHÔNG sửa/gỡ được trên UI →
BE phải re-inject ở MỌI đường sửa role (create / set_user_roles /
update_user_roles / update_user_info). Có base role ⟺ là user AssetCore.

SSoT base role: assetcore.setup.role_profile_catalog.BASE_ROLE (= Roles.SYSTEM_USER).

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_imm00_base_role
"""
from __future__ import annotations

import json
import time
import unittest

import frappe

from assetcore.setup.role_profile_catalog import BASE_ROLE


_UID = str(int(time.time()) % 100000)


def setUpModule():
    frappe.set_user("Administrator")


class TestBaseRoleMandatory(unittest.TestCase):
    """Base role luôn được cấp khi tạo + không thể gỡ qua các endpoint sửa role."""

    def setUp(self):
        frappe.set_user("Administrator")
        self._emails: list[str] = []

    def tearDown(self):
        for email in self._emails:
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        frappe.local.form_dict = frappe._dict()
        frappe.set_user("Administrator")

    # ── helpers ──────────────────────────────────────────────────────────────
    def _track(self, email: str) -> str:
        self._emails.append(email)
        return email

    def _roles(self, email: str) -> set[str]:
        return {r.role for r in frappe.get_doc("User", email).roles}

    def _make_user(self, suffix: str, roles: list[str]) -> str:
        """Insert thẳng 1 User (không qua create_system_user) với bộ roles cho trước."""
        email = self._track(f"_test_baserole_{suffix}_{_UID}@example.com")
        doc = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": f"Base {suffix}",
            "enabled": 1,
            "user_type": "System User",
            "send_welcome_email": 0,
            "roles": [{"role": r} for r in roles],
        })
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        return email

    # ── create_system_user grants base role ───────────────────────────────────
    def test_create_grants_base_role_when_no_roles_selected(self):
        """Admin tạo user, không tick role nào → vẫn có base role."""
        from assetcore.api.user import create_system_user

        email = self._track(f"_test_baserole_create_none_{_UID}@example.com")
        frappe.local.form_dict = frappe._dict({
            "email": email, "first_name": "Create None", "imm_roles": "[]",
        })
        res = create_system_user()
        self.assertTrue(res.get("success"), res)
        self.assertIn(BASE_ROLE, self._roles(email))

    def test_create_grants_base_role_alongside_domain_roles(self):
        """Admin tick 'Repair User' → user có CẢ base role + Repair User."""
        from assetcore.api.user import create_system_user

        email = self._track(f"_test_baserole_create_dom_{_UID}@example.com")
        frappe.local.form_dict = frappe._dict({
            "email": email, "first_name": "Create Dom",
            "imm_roles": json.dumps([{"role": "Repair User"}]),
        })
        res = create_system_user()
        self.assertTrue(res.get("success"), res)
        roles = self._roles(email)
        self.assertIn(BASE_ROLE, roles)
        self.assertIn("Repair User", roles)

    # ── base role non-removable via set_user_roles ────────────────────────────
    def test_set_user_roles_keeps_base_when_replacing(self):
        """set_user_roles với bộ role KHÔNG có base → base vẫn còn."""
        from assetcore.api.user import set_user_roles

        email = self._make_user("set_replace", [BASE_ROLE, "Repair User"])
        res = set_user_roles(email, roles=json.dumps([{"role": "PM User"}]))
        self.assertTrue(res.get("success"), res)
        roles = self._roles(email)
        self.assertIn(BASE_ROLE, roles)
        self.assertIn("PM User", roles)

    def test_set_user_roles_keeps_base_when_clearing(self):
        """set_user_roles với danh sách rỗng → base role vẫn không bị gỡ."""
        from assetcore.api.user import set_user_roles

        email = self._make_user("set_clear", [BASE_ROLE, "Repair User"])
        res = set_user_roles(email, roles="[]")
        self.assertTrue(res.get("success"), res)
        self.assertIn(BASE_ROLE, self._roles(email))

    # ── base role non-removable via update_user_roles ─────────────────────────
    def test_update_user_roles_keeps_base(self):
        """update_user_roles (form_dict) với payload bỏ base → base vẫn còn."""
        from assetcore.api.user import update_user_roles

        email = self._make_user("update_roles", [BASE_ROLE, "Repair User"])
        frappe.local.form_dict = frappe._dict({
            "user": email, "roles": json.dumps([{"role": "PM User"}]),
        })
        res = update_user_roles()
        self.assertTrue(res.get("success"), res)
        self.assertIn(BASE_ROLE, self._roles(email))

    # ── base role non-removable via update_user_info ──────────────────────────
    def test_update_user_info_keeps_base(self):
        """update_user_info gửi imm_roles bỏ base → base vẫn còn."""
        from assetcore.api.user import update_user_info

        email = self._make_user("update_info", [BASE_ROLE, "Repair User"])
        frappe.local.form_dict = frappe._dict({
            "user": email, "imm_roles": json.dumps([{"role": "PM User"}]),
        })
        res = update_user_info()
        self.assertTrue(res.get("success"), res)
        self.assertIn(BASE_ROLE, self._roles(email))


class TestListUsersBaseRoleFilter(unittest.TestCase):
    """list_users CHỈ trả user có base role (= "user AssetCore")."""

    def setUp(self):
        frappe.set_user("Administrator")
        self._emails: list[str] = []

    def tearDown(self):
        for e in self._emails:
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=True, ignore_permissions=True)
        frappe.db.commit()
        frappe.set_user("Administrator")

    def _insert(self, suffix: str, roles: list[str]) -> str:
        email = self._emails.append(f"_test_lubr_{suffix}_{_UID}@example.com") or self._emails[-1]
        doc = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": f"LUBR {suffix}",
            "enabled": 1, "user_type": "System User", "send_welcome_email": 0,
            "roles": [{"role": r} for r in roles],
        })
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        return email

    def _list_names(self, search: str) -> set[str]:
        from assetcore.api.user import list_users
        res = list_users(search=search, page_size=100)
        self.assertTrue(res.get("success"), res)
        return {it["name"] for it in res["data"]["items"]}

    def test_base_role_holder_is_listed(self):
        """User có base role → xuất hiện trong list_users."""
        email = self._insert("withbase", [BASE_ROLE, "Repair User"])
        self.assertIn(email, self._list_names(email))

    def test_non_base_role_user_excluded(self):
        """System User KHÔNG có base role → KHÔNG xuất hiện (không phải user AssetCore)."""
        email = self._insert("nobase", ["PM User"])
        self.assertNotIn(email, self._list_names(email))


class TestBackfillBaseRole(unittest.TestCase):
    """Patch 009: cấp base role cho System User hiện có (trừ Admin/Guest), idempotent."""

    def setUp(self):
        frappe.set_user("Administrator")
        self._emails: list[str] = []

    def tearDown(self):
        for e in self._emails:
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=True, ignore_permissions=True)
        frappe.db.commit()
        frappe.set_user("Administrator")

    def _insert(self, suffix: str, roles: list[str]) -> str:
        email = self._emails.append(f"_test_bbf_{suffix}_{_UID}@example.com") or self._emails[-1]
        doc = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": f"BBF {suffix}",
            "enabled": 1, "user_type": "System User", "send_welcome_email": 0,
            "roles": [{"role": r} for r in roles],
        })
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        return email

    def _roles(self, email: str) -> set[str]:
        return {r.role for r in frappe.get_doc("User", email).roles}

    def _grant(self, names: list[str]) -> int:
        import importlib
        mod = importlib.import_module(
            "assetcore.patches.v3_2.009_backfill_base_role")
        n = mod.grant_base_role(names)
        frappe.db.commit()
        return n

    def test_grants_base_to_assetcore_users(self):
        u1 = self._insert("g1", ["Repair User"])
        u2 = self._insert("g2", ["PM User"])
        self.assertEqual(self._grant([u1, u2]), 2)
        self.assertIn(BASE_ROLE, self._roles(u1))
        self.assertIn(BASE_ROLE, self._roles(u2))

    def test_idempotent(self):
        u = self._insert("idem", ["Repair User"])
        self.assertEqual(self._grant([u]), 1)
        self.assertEqual(self._grant([u]), 0)
        self.assertIn(BASE_ROLE, self._roles(u))

    def test_skips_admin(self):
        u = self._insert("ctl", ["PM User"])
        before = self._roles("Administrator")
        self._grant(["Administrator", u])
        self.assertEqual(self._roles("Administrator"), before,
                         "grant_base_role KHÔNG được đổi role Administrator")
        self.assertIn(BASE_ROLE, self._roles(u))


class TestListAssignableUsers(unittest.TestCase):
    """list_assignable_users: picker user AssetCore ĐỦ NĂNG LỰC cho 1 ngữ cảnh.

    Q2: field phân công (vd KTV sửa chữa) CHỈ hiện user đủ năng lực — capability/
    DocPerm (mirror _is_repair_capable), KHÔNG role-name. Nguồn = base-role holder.
    """

    def setUp(self):
        frappe.set_user("Administrator")
        self._emails: list[str] = []

    def tearDown(self):
        for e in self._emails:
            if frappe.db.exists("User", e):
                frappe.delete_doc("User", e, force=True, ignore_permissions=True)
        frappe.db.commit()
        frappe.set_user("Administrator")

    def _insert(self, suffix: str, roles: list[str]) -> str:
        email = self._emails.append(f"_test_lau_{suffix}_{_UID}@example.com") or self._emails[-1]
        doc = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": f"LAU {suffix}",
            "enabled": 1, "user_type": "System User", "send_welcome_email": 0,
            "roles": [{"role": r} for r in roles],
        })
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        frappe.clear_cache(user=email)
        return email

    def _names(self, context: str, search: str = "") -> set[str]:
        from assetcore.api.user import list_assignable_users
        res = list_assignable_users(context=context, search=search, limit=100)
        self.assertTrue(res.get("success"), res)
        return {it["name"] for it in res["data"]}

    def test_repair_capable_base_user_listed(self):
        """User AssetCore có quyền repair (Repair User) → xuất hiện trong picker 'repair'."""
        email = self._insert("repcap", [BASE_ROLE, "Repair User"])
        self.assertIn(email, self._names("repair", search="_test_lau_repcap"))

    def test_non_capable_base_user_excluded(self):
        """User AssetCore KHÔNG có quyền repair (chỉ Document User) → KHÔNG trong picker."""
        email = self._insert("doconly", [BASE_ROLE, "Document User"])
        self.assertNotIn(email, self._names("repair", search="_test_lau_doconly"))

    def test_capable_but_non_base_user_excluded(self):
        """Có quyền repair nhưng THIẾU base role (không phải user AssetCore) → KHÔNG hiện."""
        email = self._insert("repnobase", ["Repair User"])
        self.assertNotIn(email, self._names("repair", search="_test_lau_repnobase"))

    def test_invalid_context_rejected(self):
        """Ngữ cảnh không hợp lệ → lỗi 400 (chống probe quyền doctype tùy ý)."""
        from assetcore.api.user import list_assignable_users
        res = list_assignable_users(context="bogus_ctx")
        self.assertFalse(res.get("success"), res)

    def test_pm_capable_base_user_listed(self):
        """Ngữ cảnh 'pm': user AssetCore có quyền PM (PM User) → xuất hiện."""
        email = self._insert("pmcap", [BASE_ROLE, "PM User"])
        self.assertIn(email, self._names("pm", search="_test_lau_pmcap"))

    def test_pm_excludes_non_pm_capable(self):
        """Ngữ cảnh 'pm': user chỉ có quyền repair (không PM) → KHÔNG xuất hiện."""
        email = self._insert("reponly", [BASE_ROLE, "Repair User"])
        self.assertNotIn(email, self._names("pm", search="_test_lau_reponly"))

    def test_user_context_returns_any_base_role_holder(self):
        """Ngữ cảnh 'user': BẤT KỲ user AssetCore (có base role) — KHÔNG lọc năng lực.
        User chỉ có Document User (không repair/pm) vẫn xuất hiện."""
        email = self._insert("anyuser", [BASE_ROLE, "Document User"])
        self.assertIn(email, self._names("user", search="_test_lau_anyuser"))

    def test_user_context_excludes_non_base(self):
        """Ngữ cảnh 'user': user THIẾU base role → vẫn KHÔNG xuất hiện (không phải user AssetCore)."""
        email = self._insert("anynobase", ["Document User"])
        self.assertNotIn(email, self._names("user", search="_test_lau_anynobase"))

    def test_calibration_context_includes_calibration_user(self):
        """Ngữ cảnh 'calibration': user có quyền hiệu chuẩn (Calibration User) → xuất hiện."""
        email = self._insert("calcap", [BASE_ROLE, "Calibration User"])
        self.assertIn(email, self._names("calibration", search="_test_lau_calcap"))
