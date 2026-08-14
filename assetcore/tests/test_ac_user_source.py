# Copyright (c) 2026, AssetCore Team
"""IMM-00 — SSoT nguồn "user AssetCore" cho MỌI trang / form / báo cáo.

Yêu cầu (2026-07-22): số người dùng trên `/dashboard` lệch với `/user-profiles`
vì mỗi surface tự query thẳng `tabUser`. Định danh DUY NHẤT của "user AssetCore"
= giữ base role ``AssetCore System User`` (memory: user-source-base-role-pattern,
spec `docs/res/rbac/user-scope-filter-analysis.md` §11.A).

Test này khoá 3 lớp:
  1. Resolver `services/shared/ac_users.py` — hành vi nền (base role, loại
     Administrator/Guest, lọc theo role / trạng thái duyệt).
  2. INVARIANT count == drill — mọi KPI người-dùng trên dashboard phải bằng
     ĐÚNG số dòng mà `/user-profiles` hiển thị khi bấm drill (ADR §4b).
  3. Guard tĩnh — không surface nào được đếm/liệt kê `User` thô ngoài resolver.

Run:
    bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.test_ac_user_source
"""
from __future__ import annotations

import ast
import time
import unittest
from pathlib import Path

import frappe

from assetcore.setup.role_profile_catalog import BASE_ROLE
from assetcore.tests._helpers.paths import APP_ROOT

_UID = str(int(time.time()) % 1000000)


def setUpModule():
    frappe.set_user("Administrator")


def _mk_user(suffix: str, roles: list[str], *, enabled: int = 1,
             approval: str | None = None) -> str:
    """Insert thẳng 1 User với bộ roles cho trước (không qua create_system_user)."""
    email = f"_test_acusers_{suffix}_{_UID}@example.com"
    doc = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": f"AcUsers {suffix}",
        "enabled": enabled,
        "user_type": "System User",
        "roles": [{"role": r} for r in roles],
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
    if approval and frappe.db.has_column("User", "imm_approval_status"):
        frappe.db.set_value("User", email, "imm_approval_status", approval,
                            update_modified=False)
    frappe.db.commit()
    return email


class _UserFixtureCase(unittest.TestCase):
    """Base case: tự dọn user tạo trong test (không rò fixture — LL-TEST)."""

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

    def _user(self, *args, **kwargs) -> str:
        email = _mk_user(*args, **kwargs)
        self._emails.append(email)
        return email


class TestAcUserResolver(_UserFixtureCase):
    """Resolver = định nghĩa DUY NHẤT của "user AssetCore"."""

    def test_only_base_role_holders(self):
        """User giữ base role → thuộc tập; user Frappe thường → KHÔNG."""
        from assetcore.services.shared.ac_users import ac_user_names

        member = self._user("member", [BASE_ROLE])
        outsider = self._user("outsider", [])

        names = ac_user_names()
        self.assertIn(member, names)
        self.assertNotIn(outsider, names,
                         "User không có base role vẫn lọt vào tập user AssetCore")

    def test_excludes_infra_accounts(self):
        """Administrator / Guest là tài khoản hạ tầng — không phải user AssetCore."""
        from assetcore.services.shared.ac_users import ac_user_names

        names = ac_user_names()
        self.assertNotIn("Administrator", names)
        self.assertNotIn("Guest", names)

    def test_role_filter_intersects_base_role(self):
        """Lọc theo role phụ = GIAO với tập base-role, không thay thế."""
        from assetcore.services.shared.ac_users import ac_user_names

        vendor_member = self._user("vendor_in", [BASE_ROLE, "Vendor Engineer"])
        vendor_only = self._user("vendor_out", ["Vendor Engineer"])

        names = ac_user_names(role="Vendor Engineer")
        self.assertIn(vendor_member, names)
        self.assertNotIn(vendor_only, names,
                         "User có role nghiệp vụ nhưng KHÔNG có base role vẫn lọt")

    def test_count_matches_names(self):
        """`count_ac_users` và `ac_user_names` luôn cùng một tập (count == rows)."""
        from assetcore.services.shared.ac_users import ac_user_names, count_ac_users

        self._user("count", [BASE_ROLE])
        self.assertEqual(count_ac_users(), len(ac_user_names()))

    def test_enabled_filter(self):
        """`extra_filters` áp thêm trên tập base-role (vd chỉ user đang hoạt động)."""
        from assetcore.services.shared.ac_users import count_ac_users

        self._user("on", [BASE_ROLE], enabled=1)
        self._user("off", [BASE_ROLE], enabled=0)

        total = count_ac_users()
        active = count_ac_users({"enabled": 1})
        disabled = count_ac_users({"enabled": 0})
        self.assertEqual(total, active + disabled)
        self.assertGreaterEqual(disabled, 1)

    def test_approved_only_excludes_pending(self):
        """Picker chỉ được gợi ý user đã duyệt (BA §0.1.1)."""
        if not frappe.db.has_column("User", "imm_approval_status"):
            self.skipTest("custom field imm_approval_status chưa migrate")
        from assetcore.services.shared.ac_users import ac_user_names

        pending = self._user("pending", [BASE_ROLE], approval="Pending")
        approved = self._user("approved", [BASE_ROLE], approval="Approved")

        names = ac_user_names(approved_only=True)
        self.assertIn(approved, names)
        self.assertNotIn(pending, names)
        self.assertIn(pending, ac_user_names(),
                      "Tập admin (/user-profiles) vẫn phải thấy user chờ duyệt")


class TestDashboardCountMatchesDrill(_UserFixtureCase):
    """INVARIANT count == drill: KPI dashboard == số dòng /user-profiles."""

    def _kpi(self, key: str):
        from assetcore.api.dashboard import _build_admin, get_overview

        data = _build_admin(get_overview())
        for k in data["kpis"]:
            if k["key"] == key:
                return k
        self.fail(f"KPI '{key}' không tồn tại trên dashboard admin")

    def _list_total(self, **params) -> int:
        from assetcore.api.user import list_users

        res = list_users(page=1, page_size=100, **params)
        return int(res["data"]["pagination"]["total"])

    def test_total_users_matches_user_profiles(self):
        """"Tổng người dùng" == tổng dòng /user-profiles (không lọc)."""
        self._user("dash_on", [BASE_ROLE], enabled=1)
        self._user("dash_off", [BASE_ROLE], enabled=0)
        self._user("dash_outsider", [])

        self.assertEqual(self._kpi("total_users")["value"], self._list_total())

    def test_pending_users_matches_drill(self):
        """"Chờ phê duyệt" == /user-profiles?approval_status=Pending."""
        if not frappe.db.has_column("User", "imm_approval_status"):
            self.skipTest("custom field imm_approval_status chưa migrate")
        self._user("dash_pending", [BASE_ROLE], approval="Pending")

        kpi = self._kpi("pending_users")
        self.assertEqual(kpi["value"], self._list_total(approval_status="Pending"))
        self.assertGreaterEqual(kpi["value"], 1,
                                "KPI chờ duyệt luôn 0 — field custom sai tên?")

    def test_vendor_engineers_matches_drill(self):
        """"Vendor Engineer" == /user-profiles?role=Vendor Engineer."""
        self._user("dash_vendor", [BASE_ROLE, "Vendor Engineer"])

        self.assertEqual(self._kpi("vendor_engineers")["value"],
                         self._list_total(role="Vendor Engineer"))

    def test_users_pending_section_is_ac_scope(self):
        """Mục "user chờ duyệt" chỉ chứa user AssetCore (không phải user app khác)."""
        from assetcore.api.dashboard import _build_admin, get_overview
        from assetcore.services.shared.ac_users import ac_user_names

        outsider = self._user("sect_outsider", [], enabled=0)
        rows = _build_admin(get_overview())["sections"]["users_pending"]

        names = ac_user_names()
        self.assertNotIn(outsider, [r["name"] for r in rows])
        for r in rows:
            self.assertIn(r["name"], names)


class TestNotificationCoverageScope(unittest.TestCase):
    """KPI độ phủ thông báo lấy mẫu số cùng nguồn user AssetCore."""

    def test_total_users_is_ac_scope(self):
        from assetcore.repositories.notification_repo import count_email_opt_out
        from assetcore.services.shared.ac_users import count_ac_users

        self.assertEqual(
            int(count_email_opt_out()["total_users"]),
            count_ac_users({"enabled": 1}),
        )


class TestLegacyLeakSurfacesRemoved(unittest.TestCase):
    """2 lối lấy user cũ (rò toàn bộ Frappe user) đã bị gỡ."""

    def test_list_frappe_users_endpoint_removed(self):
        import assetcore.api.user as user_api

        self.assertFalse(
            hasattr(user_api, "list_frappe_users"),
            "list_frappe_users vẫn còn — endpoint trả toàn bộ Frappe user",
        )

    def test_search_link_rejects_user_doctype(self):
        from assetcore.services.imm04 import _ALLOWED_SEARCH_DOCTYPES

        self.assertNotIn(
            "User", _ALLOWED_SEARCH_DOCTYPES,
            "search_link vẫn cho tìm doctype User → xổ toàn bộ user site",
        )


class TestNoRawUserQueryGuard(unittest.TestCase):
    """Guard TĨNH — chặn tái phát: cấm đếm/liệt kê `User` thô ngoài resolver.

    Hợp lệ (KHÔNG bị bắt):
      * ``frappe.db.get_value("User", name, ...)`` — đọc 1 bản ghi theo id.
      * ``frappe.get_all("User", filters={"name": ["in", ids]})`` — enrich tên
        hiển thị từ danh sách id ĐÃ có (không phải nguồn liệt kê user).

    Vi phạm: mọi ``get_all/get_list/count("User", ...)`` KHÔNG khoá theo ``name``
    → đó là một "nguồn liệt kê user" mới, phải đi qua
    ``services/shared/ac_users``.
    """

    _APP = Path(APP_ROOT)
    _SCAN_DIRS = ("api", "services", "repositories")
    # Ngoại lệ có lý do:
    #   * resolver — nơi DUY NHẤT được phép query gốc;
    #   * import_validators — check trùng email khi import PHẢI quét toàn bộ
    #     `tabUser` (email đã bị user app khác chiếm vẫn không tạo được User).
    _ALLOWLIST = {
        "services/shared/ac_users.py",
        "services/import_validators.py",
    }
    _LIST_CALLS = {"get_all", "get_list", "count"}

    @staticmethod
    def _first_arg_is_user(call: ast.Call) -> bool:
        if not call.args:
            return False
        a = call.args[0]
        return isinstance(a, ast.Constant) and a.value == "User"

    @staticmethod
    def _keyed_by_name(call: ast.Call) -> bool:
        """True khi filters khoá theo `name` (enrich theo id — không phải nguồn liệt kê)."""
        nodes = [kw.value for kw in call.keywords if kw.arg == "filters"]
        nodes += list(call.args[1:2])
        for node in nodes:
            if isinstance(node, ast.Dict):
                for k in node.keys:
                    if isinstance(k, ast.Constant) and k.value == "name":
                        return True
        return False

    def test_no_raw_user_listing_outside_resolver(self):
        offenders: list[str] = []
        for sub in self._SCAN_DIRS:
            for path in sorted((self._APP / sub).rglob("*.py")):
                rel = path.relative_to(self._APP).as_posix()
                if rel in self._ALLOWLIST:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    fn = node.func
                    if not isinstance(fn, ast.Attribute) or fn.attr not in self._LIST_CALLS:
                        continue
                    if not self._first_arg_is_user(node):
                        continue
                    if self._keyed_by_name(node):
                        continue
                    offenders.append(f"{rel}:{node.lineno}")
        self.assertEqual(
            offenders, [],
            "Query `User` thô (không khoá theo name) ngoài resolver — dùng "
            "assetcore.services.shared.ac_users thay thế: " + ", ".join(offenders),
        )
