# assetcore/tests/imm00/test_imm00_list_scope.py
# Copyright (c) 2026, AssetCore Team
"""IMM-00 — AC Asset list row-scope invariants (ADR-IMM00-LIST-SCOPE).

P1 (factory run2 [USER] eval 2026-06-08, persona KTV phamvanduc): /assets header
"Tổng 1430" + "1/72" nhưng bảng RỖNG → count != rows.

Root cause kép:
  (1) ac_asset_query scope KTV nội bộ về responsible_technician=<user> → KTV
      phụ trách 0 asset → 0 row.
  (2) count_with_or dùng frappe.get_all/db.count → KHÔNG áp permission_query_conditions
      → đếm TẤT CẢ; items dùng frappe.get_list → scoped ⟹ count != rows.

Quyết định nghiệp vụ (USER chốt 2026-06-08, ADR-IMM00-LIST-SCOPE §2):
  D1 — KTV NỘI BỘ (PM/Repair/Calibration/Corrective User) → READ-ALL.
  D2 — Vendor Engineer → VẪN scope (isolation BẤT BIẾN, CLAUDE.md §5/§19).
  D3 — INVARIANT pagination.total == len(items) cho MỌI persona.

Bất biến (ADR §5): INV-1..INV-7. INV-3 BẮT BUỘC chứng minh vendor KHÔNG bị nới
sau khi mở KTV read-all.

Run: bench --site miyano run-tests --app assetcore \
     --module assetcore.tests.imm00.test_imm00_list_scope
"""
from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.imm00 import list_assets, get_asset
from assetcore.permissions import ac_asset_query, ac_asset_has_permission
from assetcore.tests._helpers._asset_cleanup import purge_asset


_INTERNAL_TECH_EMAIL = "ktv_internal_listscope@example.com"
_VENDOR_EMAIL = "vendor_listscope@example.com"
_OTHER_TECH = "other_tech_listscope@example.com"


def _ensure_user(email: str, first_name: str, *roles: str) -> str:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)
    u = frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": first_name,
        "send_welcome_email": 0,
        "enabled": 1,
    }).insert(ignore_permissions=True)
    if roles:
        u.add_roles(*roles)
    return u.name


def _drop_user(email: str) -> None:
    if frappe.db.exists("User", email):
        frappe.delete_doc("User", email, force=True, ignore_permissions=True)


def _insert_asset(data: dict):
    """Insert AC Asset bypassing the lifecycle workflow (test fixture)."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


class TestAcAssetListScope(FrappeTestCase):
    """ADR-IMM00-LIST-SCOPE — internal read-all vs vendor isolation + count==rows."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": "ListScope Test Category",
            "category_code": "TEST-CAT-LISTSCOPE",
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)

        # Internal technician (NỘI BỘ) — uses ALL four *User roles → _TECHNICIAN_ROLES.
        cls.internal_user = _ensure_user(
            _INTERNAL_TECH_EMAIL, "KTV NoiBo",
            "PM User", "Repair User", "Calibration User", "Corrective User",
        )
        # Vendor Engineer (NGOÀI viện) — isolation persona. Pairs the manual
        # ``Vendor Engineer`` role with ``AssetCore System User`` (baseline desk
        # role that carries AC Asset DocPerm read but is NEITHER senior NOR an
        # internal ``_TECHNICIAN_ROLE``) → routes to the vendor-scope branch of
        # ac_asset_query (isolated), while having DocPerm read so frappe.get_list
        # does not hard-deny. This mirrors production provisioning
        # (setup_core_permissions: vendors get baseline desk read, isolation by
        # ac_asset_query). Adding a _TECHNICIAN_ROLE here would (per ADR §3.3)
        # promote the user to internal read-all — that combo is intentionally
        # NOT the isolation persona.
        cls.vendor_user = _ensure_user(
            _VENDOR_EMAIL, "Vendor Eng", "Vendor Engineer", "AssetCore System User",
        )
        # A second tech to own assets the internal/vendor user does NOT.
        cls.other_user = _ensure_user(_OTHER_TECH, "Other Tech", "Repair User")

        # 3 assets, each responsible_technician = someone OTHER than internal_user,
        # so the OLD scoped predicate would have returned 0 rows for internal_user.
        cls.asset_names: list[str] = []
        for i in range(3):
            doc = _insert_asset({
                "doctype": "AC Asset",
                "asset_name": f"ListScope Asset {i}",
                "asset_category": cls.cat.name,
                "lifecycle_status": "Commissioned",
                "responsible_technician": cls.other_user,
                "manufacturer_sn": f"LS-SN-{i}",
            })
            cls.asset_names.append(doc.name)

        # One asset assigned to the VENDOR via a PM Work Order (gives vendor scope).
        cls.vendor_asset = _insert_asset({
            "doctype": "AC Asset",
            "asset_name": "ListScope Vendor Asset",
            "asset_category": cls.cat.name,
            "lifecycle_status": "Commissioned",
            "responsible_technician": cls.vendor_user,
            "manufacturer_sn": "LS-SN-VENDOR",
        }).name
        cls.asset_names.append(cls.vendor_asset)

        # PM Work Order wiring: apply_vendor_scope resolves vendor's assets via
        # PM Work Order / Asset Repair where assigned_to=vendor. Create one so the
        # vendor has a non-empty scope (else INV-3 collapses to INV-4 empty-scope).
        cls.pm_wo = None
        if frappe.db.table_exists("PM Work Order") and frappe.db.has_column("PM Work Order", "asset_ref"):
            try:
                wo = frappe.get_doc({
                    "doctype": "PM Work Order",
                    "asset_ref": cls.vendor_asset,
                    "assigned_to": cls.vendor_user,
                }).insert(ignore_permissions=True)
                cls.pm_wo = wo.name
            except Exception:
                cls.pm_wo = None

        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if getattr(cls, "pm_wo", None) and frappe.db.exists("PM Work Order", cls.pm_wo):
            wo = frappe.get_doc("PM Work Order", cls.pm_wo)
            if wo.docstatus == 1:
                wo.cancel()
            frappe.delete_doc("PM Work Order", cls.pm_wo, force=True, ignore_permissions=True)
        for name in getattr(cls, "asset_names", []):
            purge_asset(name)
        if frappe.db.exists("AC Asset Category", cls.cat.name):
            frappe.delete_doc("AC Asset Category", cls.cat.name, force=True, ignore_permissions=True)
        for email in (_INTERNAL_TECH_EMAIL, _VENDOR_EMAIL, _OTHER_TECH):
            _drop_user(email)
        frappe.db.commit()
        super().tearDownClass()

    # ── helpers ──────────────────────────────────────────────────────────────
    def _list_all_names(self, **kw) -> tuple[int, list[str]]:
        """Return (pagination.total, [names across ALL pages]) for current user.

        INVARIANT count==rows is defined over the WHOLE result set (sum of every
        page), NOT a single page — paginate() caps page_size at 100 and
        Administrator/senior personas have >100 real assets in the DB, so we walk
        every page and assert total == len(all names collected).
        """
        first = list_assets(page=1, page_size=100, **kw)["data"]
        total = first["pagination"]["total"]
        names = [r["name"] for r in first["items"]]
        total_pages = first["pagination"].get("total_pages") or 0
        for p in range(2, total_pages + 1):
            page = list_assets(page=p, page_size=100, **kw)["data"]
            names.extend(r["name"] for r in page["items"])
        return total, names

    # ── INV-1: internal technician → read-all + count==rows ──────────────────
    def test_inv1_internal_technician_read_all_and_count_equals_rows(self):
        frappe.set_user(self.internal_user)
        try:
            total, names = self._list_all_names()
            # read-all: every seeded fixture (incl. ones owned by other_user) visible
            for a in self.asset_names:
                self.assertIn(a, names,
                              f"KTV nội bộ phải thấy asset {a} (read-all D1)")
            self.assertGreater(total, 0, "KTV nội bộ có data → items KHÔNG rỗng")
            self.assertEqual(total, len(names),
                             "INV-1/INV-6: total == len(items) cho KTV nội bộ")
        finally:
            frappe.set_user("Administrator")

    def test_inv1_query_predicate_internal_is_empty(self):
        """ac_asset_query for internal technician → '' (no WHERE injected)."""
        self.assertEqual(
            ac_asset_query(self.internal_user), "",
            "KTV nội bộ → predicate rỗng (read-all)",
        )

    # ── INV-2: internal technician → get_asset on any asset = 200 ────────────
    def test_inv2_internal_technician_get_any_asset_200(self):
        frappe.set_user(self.internal_user)
        try:
            # asset owned by other_user — old scoped has_permission would 403
            target = self.asset_names[0]
            resp = get_asset(target)
            self.assertTrue(resp.get("success"),
                            f"KTV nội bộ mở asset người khác phải 200: {resp}")
            self.assertEqual(resp["data"]["name"], target)
        finally:
            frappe.set_user("Administrator")

    def test_inv2_has_permission_internal_read_true(self):
        """ac_asset_has_permission read for internal tech on foreign asset → True."""
        doc = frappe.get_doc("AC Asset", self.asset_names[0])
        self.assertTrue(
            ac_asset_has_permission(doc, "read", self.internal_user),
            "KTV nội bộ read asset người khác → True (đồng bộ list read-all)",
        )

    # ── INV-3: vendor isolation HELD after internal read-all (BẮT BUỘC) ──────
    def test_inv3_vendor_isolated_after_internal_readall(self):
        frappe.set_user(self.vendor_user)
        try:
            total, names = self._list_all_names()
            # Vendor must NOT see assets owned by other_user (read-all leak guard).
            for a in self.asset_names[:3]:
                self.assertNotIn(
                    a, names,
                    f"VENDOR KHÔNG được thấy asset {a} của người khác "
                    "(isolation BẤT BIẾN sau khi mở KTV read-all)",
                )
            self.assertEqual(total, len(names),
                             "INV-3/INV-6: vendor total == len(items) (isolated)")
            # If vendor scope resolved an asset, it must be the vendor's own.
            for a in names:
                self.assertEqual(
                    a, self.vendor_asset,
                    "VENDOR chỉ thấy asset được giao (responsible_technician=mình "
                    "∩ assigned-via-WO)",
                )
        finally:
            frappe.set_user("Administrator")

    def test_inv3_query_predicate_vendor_still_scoped(self):
        """ac_asset_query for pure vendor → keeps responsible_technician scope."""
        cond = ac_asset_query(self.vendor_user)
        self.assertIn("responsible_technician", cond,
                      "VENDOR predicate phải GIỮ responsible_technician scope (D2)")
        self.assertIn(self.vendor_user, cond,
                      "VENDOR predicate phải gắn đúng user (escaped literal)")
        # escaping preserved (frappe.db.escape) — no raw injection slot
        self.assertNotIn("';", cond, "predicate vendor không lộ SQLi slot")

    def test_inv3_has_permission_vendor_foreign_denied(self):
        """Vendor read on a foreign asset → False (IDOR held)."""
        doc = frappe.get_doc("AC Asset", self.asset_names[0])
        self.assertFalse(
            ac_asset_has_permission(doc, "read", self.vendor_user),
            "VENDOR read asset người khác → False (isolation GIỮ)",
        )

    def test_inv3_has_permission_vendor_own_allowed(self):
        doc = frappe.get_doc("AC Asset", self.vendor_asset)
        self.assertTrue(
            ac_asset_has_permission(doc, "read", self.vendor_user),
            "VENDOR read asset của mình → True",
        )

    # ── INV-4: vendor empty-scope → 0 rows, no fallback ──────────────────────
    def test_inv4_vendor_empty_scope_zero_rows(self):
        empty_vendor = "vendor_empty_listscope@example.com"
        _ensure_user(empty_vendor, "Vendor Empty", "Vendor Engineer", "AssetCore System User")
        frappe.db.commit()
        frappe.set_user(empty_vendor)
        try:
            total, names = self._list_all_names()
            self.assertEqual(total, 0, "VENDOR scope rỗng → total == 0 (no fallback)")
            self.assertEqual(names, [], "VENDOR scope rỗng → 0 row")
        finally:
            frappe.set_user("Administrator")
            _drop_user(empty_vendor)
            frappe.db.commit()

    # ── INV-6: count==rows for senior + free-text search ─────────────────────
    def test_inv6_super_admin_read_all_count_equals_rows(self):
        frappe.set_user("Administrator")
        total, names = self._list_all_names()
        for a in self.asset_names:
            self.assertIn(a, names, "Administrator read-all phải thấy mọi fixture")
        self.assertEqual(total, len(names),
                         "INV-6: Administrator total == len(items)")

    def test_inv6_internal_technician_search_count_equals_rows(self):
        frappe.set_user(self.internal_user)
        try:
            # free-text search hits or_filters path in count_with_or
            total, names = self._list_all_names(search="ListScope")
            self.assertGreater(total, 0, "search có kết quả")
            self.assertEqual(
                total, len(names),
                "INV-6: free-text search → count == rows (permission-aware count path)",
            )
        finally:
            frappe.set_user("Administrator")

    def test_inv6_vendor_search_count_equals_rows(self):
        frappe.set_user(self.vendor_user)
        try:
            total, names = self._list_all_names(search="ListScope")
            self.assertEqual(
                total, len(names),
                "INV-6: vendor free-text search → count == rows (isolated, no leak)",
            )
            for a in names:
                self.assertEqual(a, self.vendor_asset,
                                 "vendor search KHÔNG leak asset người khác")
        finally:
            frappe.set_user("Administrator")

    # ── TC-SRCH-7 (FR-00-95 / BR-00-44): escape LIKE-metachar — INVARIANT
    #    count==rows giữ cho metachar-search ở MỌI persona. count_with_or +
    #    get_list dùng CÙNG or_filters đã-escape qua CÙNG động cơ DatabaseQuery
    #    ⟹ total == len(items). Kể cả khi escape biến '%'/'_' thành literal
    #    (0 match), bất biến count==rows KHÔNG được vỡ.
    def test_srch7_internal_technician_metachar_search_count_equals_rows(self):
        frappe.set_user(self.internal_user)
        try:
            for q in ("_", "%", "\\", "%%%%%%%%%%"):
                total, names = self._list_all_names(search=q)
                self.assertEqual(
                    total, len(names),
                    f"TC-SRCH-7 internal: metachar search={q!r} → count == rows",
                )
        finally:
            frappe.set_user("Administrator")

    def test_srch7_vendor_metachar_search_count_equals_rows(self):
        frappe.set_user(self.vendor_user)
        try:
            for q in ("_", "%", "\\", "%%%%%%%%%%"):
                total, names = self._list_all_names(search=q)
                self.assertEqual(
                    total, len(names),
                    f"TC-SRCH-7 vendor: metachar search={q!r} → count == rows (no leak)",
                )
                for a in names:
                    self.assertEqual(
                        a, self.vendor_asset,
                        f"TC-SRCH-7 vendor: metachar search={q!r} KHÔNG leak asset người khác",
                    )
        finally:
            frappe.set_user("Administrator")


class TestListAssetsPaginationCoercion(FrappeTestCase):
    """Vòng 33 — coerce an toàn page/page_size phi-số ở list_assets (line 300).

    @frappe.whitelist truyền page/page_size dưới dạng STRING từ form_dict. Giá trị
    phi-số ('abc', '10.5', '', None) TRƯỚC ĐÂY làm ``int(page)`` ném ValueError/
    TypeError → HTTP-500 traceback. Sau fix: ``_safe_page_int`` fall-back về default
    rồi vẫn đi qua clamp [1,100] của paginate() (SSoT round-5 KHÔNG đổi).

    KHÔNG seed fixture: chạy mặc định bằng Administrator (read-all) — chỉ cần bất
    biến envelope + clamp + invariant total==len(items), độc lập với data thật.

    Run: bench --site miyano run-tests --app assetcore \
         --module assetcore.tests.imm00.test_imm00_list_scope
    """

    # ── helper unit-test trực tiếp ───────────────────────────────────────────
    def test_safe_page_int_helper_units(self):
        from assetcore.api.imm00 import _safe_page_int
        # phi-số → default
        self.assertEqual(_safe_page_int("abc", 1), 1)
        self.assertEqual(_safe_page_int("10.5", 20), 20)
        self.assertEqual(_safe_page_int("", 20), 20)
        self.assertEqual(_safe_page_int(None, 20), 20)
        # số hợp lệ giữ nguyên
        self.assertEqual(_safe_page_int("7", 1), 7)
        # whitespace-wrap số hợp lệ vẫn parse (parity name/preset round 31/32)
        self.assertEqual(_safe_page_int("  4  ", 1), 4)
        # int truyền thẳng (call nội bộ) vẫn ổn
        self.assertEqual(_safe_page_int(3, 1), 3)

    def test_safe_page_int_does_not_swallow_other_errors(self):
        """KHÔNG nuốt lỗi ngoài (ValueError|TypeError) — object lạ str()-able vẫn
        đi qua int() và fall-back; nhưng helper KHÔNG được nuốt mọi Exception."""
        from assetcore.api.imm00 import _safe_page_int
        # list → str(['x']) = "['x']" → int() ném ValueError → default (TypeError/
        # ValueError được bắt). Đây là nhánh hợp lệ, KHÔNG raise.
        self.assertEqual(_safe_page_int(["x"], 9), 9)

    # ── endpoint: page phi-số → fall-back 1 ──────────────────────────────────
    def test_list_assets_page_non_numeric_falls_back_to_1(self):
        resp = list_assets(page="abc")
        data = resp["data"]
        self.assertIn("items", data)
        self.assertIn("pagination", data)
        self.assertEqual(data["pagination"]["page"], 1)

    # ── endpoint: page_size phi-số → fall-back default 20 ────────────────────
    def test_list_assets_page_size_float_string_falls_back_to_20(self):
        data = list_assets(page_size="10.5")["data"]
        self.assertEqual(data["pagination"]["page_size"], 20)

    def test_list_assets_page_size_alpha_and_empty_fall_back_to_20(self):
        for bad in ("abc", ""):
            data = list_assets(page_size=bad)["data"]
            self.assertEqual(
                data["pagination"]["page_size"], 20,
                f"page_size={bad!r} → fall-back default 20",
            )

    # ── endpoint: None (param vắng/null từ form_dict) → KHÔNG TypeError ──────
    def test_list_assets_none_params_default_without_typeerror(self):
        data = list_assets(page=None, page_size=None)["data"]
        self.assertEqual(data["pagination"]["page"], 1)
        self.assertEqual(data["pagination"]["page_size"], 20)

    # ── regression parity round-5: clamp [1,100] GIỮ ─────────────────────────
    def test_list_assets_page_size_over_cap_clamped_to_100(self):
        data = list_assets(page_size="9999")["data"]
        self.assertEqual(data["pagination"]["page_size"], 100)

    def test_list_assets_negative_page_clamped_to_1(self):
        data = list_assets(page="-5")["data"]
        self.assertEqual(data["pagination"]["page"], 1)

    # ── valid values giữ hành vi cũ ──────────────────────────────────────────
    def test_list_assets_valid_string_page_kept(self):
        data = list_assets(page="2", page_size="50")["data"]
        self.assertEqual(data["pagination"]["page"], 2)
        self.assertEqual(data["pagination"]["page_size"], 50)

    # ── whitespace-wrap số hợp lệ vẫn parse ──────────────────────────────────
    def test_list_assets_whitespace_wrapped_page_parsed(self):
        data = list_assets(page="  3  ")["data"]
        self.assertEqual(data["pagination"]["page"], 3)

    # ── INVARIANT total == cộng-dồn len(items) GIỮ (coercion KHÔNG đụng count) ─
    def test_list_assets_invariant_total_equals_cumulative_items(self):
        first = list_assets(page=1, page_size=5)["data"]
        total = first["pagination"]["total"]
        total_pages = first["pagination"].get("total_pages") or 0
        names = [r["name"] for r in first["items"]]
        for p in range(2, total_pages + 1):
            names.extend(r["name"] for r in list_assets(page=p, page_size=5)["data"]["items"])
        self.assertEqual(
            total, len(names),
            "INVARIANT: pagination.total == cộng-dồn len(items) (coercion KHÔNG đổi count/filter)",
        )
