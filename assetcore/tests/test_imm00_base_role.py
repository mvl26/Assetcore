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

    def test_grants_despite_stale_link_field(self):
        """User có link field cũ trỏ record đã bị xoá (vd ``ac_department`` = phòng ban
        không còn tồn tại) → VẪN cấp base role, KHÔNG được abort bằng LinkValidationError.

        Regression: patch 009 từng chặn cả ``bench migrate`` với 'Could not find Khoa /
        Phòng (AssetCore): HSCC' vì ``doc.save()`` re-validate MỌI link trên User — kể cả
        field patch không đụng tới. Patch chỉ APPEND base role nên phải bỏ qua link cũ.
        """
        u = self._insert("stalelink", ["Repair User"])
        bogus = f"_ZZ_NOEXIST_{_UID}"
        self.assertFalse(frappe.db.exists("AC Department", bogus))
        # Ghi thẳng DB (bypass validation) để mô phỏng link cũ đã hỏng trên site thật.
        frappe.db.set_value("User", u, "ac_department", bogus, update_modified=False)
        frappe.db.commit()
        self.assertEqual(self._grant([u]), 1)
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
        # AC-CR-80: `data` là OBJECT {items,total,truncated,limit} — KHÔNG mảng trần.
        return {it["name"] for it in res["data"]["items"]}

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

    # ─────────────────────────────────────────────────────────────────────────
    # AC-CR-80 — picker "người nhận việc" nói ĐÚNG SỰ THẬT (TC-00-ASSIGN-01..12)
    #
    # Spec: docs/imm-00/05_API_Specification.md §III.23 · code-shape 04 §V.6 ·
    # ADR-IMM00-TRUNCATION-SSOT §7 (ADR-IMM00-ASSIGN-01..04 / INV-ASSIGN-1..8).
    # Vấn đề gốc: `return _ok(capable[:limit])` CẮT IM LẶNG ⇒ picker khẳng định
    # "không tìm thấy KTV" trong khi thật ra chỉ là bị cắt ở `limit`.
    #
    # Cách ly dữ liệu thật: mỗi TC có "ô" tìm kiếm riêng `_test_lau_<UID><letter>`
    # (UID đứng TRƯỚC letter ⇒ ô của TC này không bao giờ khớp user của TC khác,
    # kể cả fixture rơi lại từ lần chạy bị kill giữa chừng).
    # ─────────────────────────────────────────────────────────────────────────

    def _scope(self, letter: str) -> str:
        """Chuỗi `search` khoá đúng tập user do TC này seed."""
        return f"_test_lau_{_UID}{letter}"

    def _scoped(self, letter: str, idx: int, roles: list[str]) -> str:
        """Seed 1 user trong ô tìm kiếm của TC (`letter`), thứ tự hiển thị theo `idx`."""
        return self._insert(f"{_UID}{letter}{idx}", roles)

    def _data(self, context: str, search: str, limit: int) -> dict:
        """Gọi endpoint → trả `data` (đã assert envelope success)."""
        from assetcore.api.user import list_assignable_users
        res = list_assignable_users(context=context, search=search, limit=limit)
        self.assertTrue(res.get("success"), res)
        return res["data"]

    # ── TC-00-ASSIGN-01 — shape mới ──────────────────────────────────────────
    def test_assign_01_data_is_object_with_four_keys(self):
        """`data` là OBJECT có ĐỦ 4 khoá {items,total,truncated,limit} — KHÔNG mảng trần."""
        self._scoped("a", 1, [BASE_ROLE, "Repair User"])
        data = self._data("repair", self._scope("a"), 20)
        self.assertIsInstance(data, dict, "AC-CR-80: `data` PHẢI là object, KHÔNG mảng trần.")
        self.assertEqual(set(data), {"items", "total", "truncated", "limit"})

    # ── TC-00-ASSIGN-02 — INV-ASSIGN-1: len(items) <= limit ──────────────────
    def test_assign_02_items_never_exceed_limit(self):
        """3 người hợp lệ, `limit=2` ⇒ ĐÚNG 2 dòng (trần cứng được tôn trọng)."""
        for i in (1, 2, 3):
            self._scoped("b", i, [BASE_ROLE, "Repair User"])
        data = self._data("repair", self._scope("b"), 2)
        self.assertEqual(len(data["items"]), 2)
        self.assertLessEqual(len(data["items"]), data["limit"])

    # ── TC-00-ASSIGN-03 — INV-ASSIGN-3 (CÓ cắt) ──────────────────────────────
    def test_assign_03_truncated_flag_and_total_when_cut(self):
        """`limit=2` trên tập 3 ⇒ `truncated==1` ∧ `total==3` (nói ĐÚNG phần bị giấu)."""
        for i in (1, 2, 3):
            self._scoped("c", i, [BASE_ROLE, "Repair User"])
        data = self._data("repair", self._scope("c"), 2)
        self.assertEqual(data["truncated"], 1, "Bị cắt mà `truncated=0` ⇒ picker nói dối.")
        self.assertEqual(data["total"], 3, "`total` = tổng người ĐƯỢC PHÉP, TRƯỚC khi cắt.")
        self.assertGreater(data["total"], data["limit"])

    # ── TC-00-ASSIGN-04 — INV-ASSIGN-3 (KHÔNG cắt, zero-cost) ────────────────
    def test_assign_04_not_truncated_when_under_limit(self):
        """2 người, `limit=100` ⇒ `truncated==0` ∧ `total==len(items)==2` (0 dải cảnh báo)."""
        for i in (1, 2):
            self._scoped("d", i, [BASE_ROLE, "Repair User"])
        data = self._data("repair", self._scope("d"), 100)
        self.assertEqual(data["truncated"], 0)
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["total"], len(data["items"]))

    # ── TC-00-ASSIGN-05 — INV-ASSIGN-4: kiểu int, KHÔNG bool (parity CR-01) ──
    def test_assign_05_truncation_meta_is_int_not_bool(self):
        """`truncated` là int 0|1 — bool trần làm crash codegen Dart/Kotlin (CR-01).

        KHÔNG chấm bằng `assertEqual(truncated, 0)` một mình: `False == 0` là True
        ⇒ test mù. Phải chấm `isinstance(..., bool) is False`.
        """
        for i in (1, 2, 3):
            self._scoped("e", i, [BASE_ROLE, "Repair User"])
        for limit, expect_trunc in ((2, 1), (100, 0)):
            data = self._data("repair", self._scope("e"), limit)
            self.assertIs(isinstance(data["truncated"], bool), False,
                          "`truncated` KHÔNG được là bool (parity CR-01).")
            self.assertIn(data["truncated"], (0, 1))
            self.assertEqual(data["truncated"], expect_trunc)
            for key in ("total", "limit"):
                self.assertIs(type(data[key]), int, f"`{key}` PHẢI là int.")
                self.assertGreaterEqual(data[key], 0)

    # ── TC-00-ASSIGN-06 — INV-ASSIGN-7: clamp 1..100 + echo limit ĐÃ clamp ───
    def test_assign_06_limit_clamped_and_echoed(self):
        """`limit=0` ⇒ hiệu lực 1; `limit=500` ⇒ hiệu lực 100; `data.limit` = trần ĐÃ CLAMP.

        Echo tham số thô sẽ khiến client tự suy `truncated` sai (INV-TRUNC-LIMIT / D5).
        """
        for i in (1, 2, 3):
            self._scoped("f", i, [BASE_ROLE, "Repair User"])
        low = self._data("repair", self._scope("f"), 0)
        self.assertEqual(low["limit"], 1, "`limit=0` PHẢI clamp lên 1.")
        self.assertEqual(len(low["items"]), 1)
        self.assertEqual(low["truncated"], 1, "`truncated` tính theo limit ĐÃ clamp (1), không phải 0.")
        self.assertEqual(low["total"], 3)

        high = self._data("repair", self._scope("f"), 500)
        self.assertEqual(high["limit"], 100, "`limit=500` PHẢI clamp xuống 100.")
        self.assertEqual(high["truncated"], 0)
        self.assertEqual(high["total"], 3)

    # ── TC-00-ASSIGN-07 — INV-ASSIGN-2: total đếm SAU lọc năng lực ───────────
    def test_assign_07_total_counted_after_capability_filter(self):
        """2 người capable + 3 người base-role KHÔNG capable ⇒ `total==2` (KHÔNG 5).

        Đây là ca bắt đúng lỗi dùng `count_ac_users()` (COUNT DB TRƯỚC lọc năng lực)
        làm `count_fn` — sẽ thổi `total` lên 5 ⇒ dải cảnh báo nói dối.
        """
        for i in (1, 2):
            self._scoped("g", i, [BASE_ROLE, "Repair User"])
        for i in (3, 4, 5):
            self._scoped("g", i, [BASE_ROLE, "Document User"])
        data = self._data("repair", self._scope("g"), 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["total"], 2,
                         "`total` PHẢI đếm SAU lọc năng lực (2 capable), KHÔNG phải 5 base-role.")
        self.assertEqual(data["truncated"], 1)

    # ── TC-00-ASSIGN-08 — INV-ASSIGN-5: parity XUÔI (0 dead-pick) ────────────
    def test_assign_08_every_item_passes_enforcement_predicate(self):
        """∀ u ∈ items(`context='repair'`) ⇒ `imm09._is_repair_capable(u)` True, ở MỌI limit.

        Picker là TẤM GƯƠNG của validator: không ai trong danh sách bị BE từ chối.
        """
        from assetcore.services.imm09 import _is_repair_capable

        for i in (1, 2, 3):
            self._scoped("h", i, [BASE_ROLE, "Repair User"])
        self._scoped("h", 4, [BASE_ROLE, "AssetCore Auditor"])
        for limit in (2, 20, 100):
            data = self._data("repair", self._scope("h"), limit)
            self.assertTrue(data["items"], f"limit={limit} trả rỗng — fixture/search sai?")
            for item in data["items"]:
                self.assertTrue(
                    _is_repair_capable(item["name"]),
                    f"DEAD-PICK: `{item['name']}` hiện trong picker nhưng validator từ chối "
                    f"(limit={limit}).")

    # ── TC-00-ASSIGN-09 — INV-ASSIGN-6: parity NGHỊCH ───────────────────────
    def test_assign_09_filtered_out_user_is_rejected_by_validator(self):
        """User base-role read-only (Auditor) KHÔNG bao giờ ∈ items; validator raise 422.

        Chiều nghịch chứng minh picker không phải "một diễn giải thứ hai" của quyền.
        """
        from assetcore.services.shared.errors import ServiceError
        from assetcore.services.imm09 import _assert_valid_technician

        capable = self._scoped("i", 1, [BASE_ROLE, "Repair User"])
        auditor = self._scoped("i", 2, [BASE_ROLE, "AssetCore Auditor"])
        for limit in (1, 20, 100):
            data = self._data("repair", self._scope("i"), limit)
            self.assertNotIn(auditor, {it["name"] for it in data["items"]},
                             f"User read-only lọt vào picker ở limit={limit}.")
        with self.assertRaises(ServiceError) as ctx:
            _assert_valid_technician(auditor)
        self.assertEqual(ctx.exception.code, "VALIDATION_ERROR")
        self.assertEqual(ctx.exception.http_status, 422)
        self.assertEqual(ctx.exception.message_code, "IMM09-INVALID-TECHNICIAN")
        # Chiều thuận: người CÓ trong danh sách thì validator KHÔNG raise.
        _assert_valid_technician(capable)

    # ── TC-00-ASSIGN-10 — INV-ASSIGN-8: 400 IN-ENVELOPE trên HTTP-200 ───────
    def test_assign_10_invalid_context_returns_400_in_envelope(self):
        """`context` lạ ⇒ HTTP-200 kèm {success:false, VALIDATION_ERROR, http_status:400}.

        KHÔNG raise (raise ⇒ 417/500 status-line ⇒ client route nhầm sang re-auth/LOGOUT).
        """
        from assetcore.api.user import list_assignable_users
        res = list_assignable_users(context="bogus_ctx")
        self.assertIs(res.get("success"), False)
        self.assertEqual(res.get("code"), "VALIDATION_ERROR")
        self.assertEqual(res.get("http_status"), 400)
        self.assertIn("Ngữ cảnh phân công không hợp lệ", res.get("error") or "",
                      "Thông điệp PHẢI tiếng Việt (§III.23.3).")

    # ── TC-00-ASSIGN-11 — INV-ASSIGN-8: 0 leak DocType/SQL ──────────────────
    def test_assign_11_invalid_context_leaks_no_doctype_or_sql(self):
        """Envelope lỗi KHÔNG chứa tên DocType allowlist / `tab` / `select` (bề mặt phân quyền)."""
        from assetcore.api.user import _ASSIGNABLE_CONTEXTS, list_assignable_users
        blob = json.dumps(list_assignable_users(context="bogus_ctx"), ensure_ascii=False).lower()
        for doctype, _ptype in _ASSIGNABLE_CONTEXTS.values():
            self.assertNotIn(doctype.lower(), blob,
                             f"Message lộ DocType `{doctype}` — đó là bề mặt phân quyền.")
        for token in ("tab", "select", "from `"):
            self.assertNotIn(token, blob, f"Message lộ dấu vết SQL (`{token}`).")

    # ── TC-00-ASSIGN-12 — context 'user' giữ nguyên 2 chế độ ────────────────
    def test_assign_12_user_context_keeps_envelope_and_skips_capability(self):
        """`context='user'`: KHÔNG lọc năng lực NHƯNG vẫn đủ 4 khoá + invariant truncation."""
        doc_user = self._scoped("j", 1, [BASE_ROLE, "Document User"])
        self._scoped("j", 2, [BASE_ROLE, "Repair User"])
        data = self._data("user", self._scope("j"), 100)
        self.assertEqual(set(data), {"items", "total", "truncated", "limit"})
        self.assertIn(doc_user, {it["name"] for it in data["items"]},
                      "`context='user'` KHÔNG được lọc năng lực.")
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["truncated"], 0)
        cut = self._data("user", self._scope("j"), 1)
        self.assertEqual(len(cut["items"]), 1)
        self.assertEqual(cut["total"], 2)
        self.assertEqual(cut["truncated"], 1)

    # ── Guard SSoT: hằng public cho OAS-parity (cr80_b) ─────────────────────
    def test_assign_context_keys_is_single_source_of_truth(self):
        """`ASSIGNABLE_CONTEXT_KEYS` = {_ANY_USER_CONTEXT} ∪ keys(_ASSIGNABLE_CONTEXTS).

        Guard OAS (`test_mobile_oas::cr80_b`) import hằng THẬT thay vì chép enum tay —
        hằng này PHẢI là nguồn DUY NHẤT, kể cả cho nhánh validate `context` trong handler.
        """
        from assetcore.api import user as user_api

        self.assertEqual(set(user_api.ASSIGNABLE_CONTEXT_KEYS),
                         {user_api._ANY_USER_CONTEXT} | set(user_api._ASSIGNABLE_CONTEXTS))
        self.assertEqual(len(user_api.ASSIGNABLE_CONTEXT_KEYS),
                         len(set(user_api.ASSIGNABLE_CONTEXT_KEYS)),
                         "Hằng có giá trị TRÙNG.")
        # Mọi khoá công bố PHẢI được handler chấp nhận (không có giá trị "chết").
        for ctx in user_api.ASSIGNABLE_CONTEXT_KEYS:
            res = user_api.list_assignable_users(context=ctx, search=self._scope("z"), limit=1)
            self.assertTrue(res.get("success"), f"Ngữ cảnh công bố `{ctx}` lại bị từ chối: {res}")
