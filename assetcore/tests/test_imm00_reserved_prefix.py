# assetcore/tests/test_imm00_reserved_prefix.py
# Copyright (c) 2026, AssetCore Team
"""TDD — IMM-00 hardening: loại asset rác test/security-audit khỏi list_assets + KPI.

Acceptance (data-hygiene, SSoT NOT-LIKE escape-safe):
  - list_assets() KHÔNG trả bất kỳ row nào có asset_name bắt đầu bằng '_' HOẶC
    name bắt đầu bằng 'SI-' (ESCAPE-safe NOT LIKE, escape '\\_' cho underscore-wildcard).
  - Count tổng áp CÙNG predicate ở cả 3 nguồn: non-search frappe.db.count,
    search raw-SQL count, dashboard get_overview().assets.total
    → INVARIANT total == len(items) khi cùng filter (parity IMM-06/12).
  - Predicate là 1 SSoT DUY NHẤT (reserved_asset_conditions/reserved_asset_count_sql
    trong services/imm00) — KHÔNG lặp literal '_%'/'SI-%' ở nhiều nơi (grep-guard).
  - 0 false-positive: asset tên thường (Máy thở, TS-..., AC-ASSET-..., Model_X có
    '_' ở GIỮA) VẪN xuất hiện đầy đủ — chỉ prefix '_' đầu hoặc 'SI-' đầu mới loại.
  - param-safe (no SQLi); kết hợp byt_status/department filter vẫn đúng (no clobber).
"""
from __future__ import annotations

import re
from unittest.mock import patch

import frappe
from frappe.utils import today
from frappe.tests.utils import FrappeTestCase

from assetcore.api.imm00 import (
    list_assets,
    list_assets_depreciation,
    get_depreciation_stats,
)
from assetcore.api.dashboard import get_overview
from assetcore.services.imm00 import (
    _RESERVED_NAME_PREFIX,
    _RESERVED_NAME_SI_PREFIX,
    reserved_prefix_filter,
    reserved_prefix_sql,
    reserved_asset_names,
)
from assetcore.tests._asset_cleanup import purge_asset
from assetcore.tests._helpers.paths import APP_ROOT


def _insert_asset(data: dict):
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


class _SeedMixin:
    """Seed các asset rác (reserved-prefix) + asset hợp lệ (kể cả '_' ở GIỮA tên)."""

    @classmethod
    def _purge_tag(cls, tag: str):
        """Idempotent pre-clean: gỡ leftover fixture cùng tag (run trước bị abort/
        deadlock dưới chạy song song → để rớt category PK '_TestRSV-<tag>' chặn
        re-insert). Chỉ đụng đúng data tag của test này (KHÔNG phải prod purge)."""
        cat = frappe.db.get_value(
            "AC Asset Category", {"category_code": f"_TestRSV-{tag}"}, "name"
        )
        if cat:
            for a in frappe.get_all("AC Asset", filters={"asset_category": cat}, pluck="name"):
                purge_asset(a)
            frappe.delete_doc("AC Asset Category", cat, force=True, ignore_permissions=True)
        if frappe.db.exists("AC Asset", f"SI-RSV-{tag}"):
            purge_asset(f"SI-RSV-{tag}")
        frappe.db.commit()

    @classmethod
    def _seed(cls, tag: str):
        cls._purge_tag(tag)
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestRSV-{tag}",
            "category_name": f"_TestRSV cat {tag}",
        }).insert(ignore_permissions=True)
        cls._names: dict[str, str] = {}
        # (key, asset_name, expect_kept)
        spec = [
            # --- reserved (phải BỊ loại) ---
            ("smoke",   f"_TestSmoke {tag}",        False),  # asset_name prefix '_'
            ("probe",   f"_Probe {tag}",            False),  # asset_name prefix '_'
            # --- hợp lệ (phải GIỮ) — tên thường ---
            ("vent",    f"Máy thở {tag}",           True),
            ("usg",     f"TS-2025-USG {tag}",       True),
            ("midus",   f"Model_X {tag}",           True),   # '_' ở GIỮA → KHÔNG loại
            ("notsi",   f"NOT-SI-thing {tag}",      True),   # 'SI-' ở GIỮA → KHÔNG loại
        ]
        for key, aname, _kept in spec:
            d = {
                "doctype": "AC Asset",
                "asset_name": aname,
                "asset_category": cls._cat.name,
                "manufacturer_sn": f"_RSVSN-{tag}-{key}",
                "lifecycle_status": "Active",
            }
            cls._names[key] = _insert_asset(d).name
        # Một asset có name (ID) bắt đầu 'SI-' — security-audit fixture. AC Asset
        # autoname không cho ép name tuỳ ý qua insert thường → set name trực tiếp.
        si = _insert_asset({
            "doctype": "AC Asset",
            "asset_name": f"SI audit asset {tag}",   # asset_name thường (KHÔNG prefix '_')
            "asset_category": cls._cat.name,
            "manufacturer_sn": f"_RSVSN-{tag}-si",
            "lifecycle_status": "Active",
        })
        from frappe.model.rename_doc import rename_doc
        new_si = f"SI-RSV-{tag}"
        rename_doc("AC Asset", si.name, new_si, force=True,
                   ignore_permissions=True, show_alert=False, validate=False)
        cls._names["si"] = new_si
        frappe.db.commit()

    @classmethod
    def _teardown(cls):
        for n in getattr(cls, "_names", {}).values():
            purge_asset(n)
        if getattr(cls, "_cat", None):
            frappe.delete_doc("AC Asset Category", cls._cat.name, force=True,
                              ignore_permissions=True)
        frappe.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 1. SSoT predicate shape — pure helpers (1 nơi định nghĩa literal)
# ─────────────────────────────────────────────────────────────────────────────
class TestReservedPredicateSoT(FrappeTestCase):
    def test_prefix_constants_are_underscore_and_si(self):
        self.assertEqual(_RESERVED_NAME_PREFIX, "_")
        self.assertEqual(_RESERVED_NAME_SI_PREFIX, "SI-")

    def test_filter_is_name_not_in_resolved_set(self):
        # ORM filter dùng 'not in' (đồng nhất db.count & get_list — KHÔNG dính bug
        # double-escape của 'not like'). Rỗng-DB → {} no-op.
        f = reserved_prefix_filter()
        if f:  # site test luôn có reserved fixtures → non-empty
            self.assertEqual(set(f.keys()), {"name"})
            op, vals = f["name"]
            self.assertEqual(op, "not in")
            self.assertIsInstance(vals, list)
            # tập == reserved_asset_names() (cùng predicate gốc)
            self.assertEqual(set(vals), set(reserved_asset_names()))

    def test_reserved_asset_names_excludes_mid_underscore(self):
        # 0 false-positive: 'Model_X' ('_' ở GIỮA) KHÔNG nằm trong tập rác.
        names = reserved_asset_names()
        for n in names:
            an = frappe.db.get_value("AC Asset", n, "asset_name") or ""
            # mỗi tên rác hoặc asset_name prefix '_' HOẶC name prefix 'SI-'
            self.assertTrue(an.startswith("_") or n.startswith("SI-"),
                            f"{n} ({an}) bị gắn reserved nhầm")

    def test_count_sql_returns_clause_and_params(self):
        clause, params = reserved_prefix_sql()
        low = clause.lower()
        self.assertIn("not like", low)
        self.assertIn("escape", low)            # ESCAPE-safe tường minh trong raw-SQL
        self.assertIn("asset_name", low)
        self.assertIn("name", low)
        # params parametrized (no inline interpolation → no SQLi)
        self.assertEqual(params, [r"\_%", "SI-%"])

    def test_count_sql_alias_prefixes_columns(self):
        clause, _ = reserved_prefix_sql(alias="a.")
        self.assertIn("a.asset_name", clause)
        self.assertIn("a.name", clause)


# ─────────────────────────────────────────────────────────────────────────────
# 2. RED-first: leak prove → list_assets KHÔNG trả reserved-prefix row
# ─────────────────────────────────────────────────────────────────────────────
class TestListAssetsExcludesReserved(_SeedMixin, FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed("exc")

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        super().tearDownClass()

    def _all_names(self, **kw):
        items = list_assets(page_size=500, **kw)["data"]["items"]
        return {i["name"] for i in items}

    def test_reserved_name_prefix_excluded(self):
        names = self._all_names()
        self.assertNotIn(self._names["smoke"], names)
        self.assertNotIn(self._names["probe"], names)

    def test_reserved_id_prefix_excluded(self):
        names = self._all_names()
        self.assertNotIn(self._names["si"], names)

    def test_legitimate_assets_kept(self):
        names = self._all_names()
        # 0 false-positive — tên thường + '_'/'SI-' ở GIỮA VẪN xuất hiện
        for key in ("vent", "usg", "midus", "notsi"):
            self.assertIn(self._names[key], names,
                          f"asset hợp lệ '{key}' bị ẩn nhầm (false-positive)")

    def test_search_path_also_excludes_reserved(self):
        # search nhắm trúng cả reserved + hợp lệ (cùng tag) → vẫn KHÔNG lộ reserved.
        names = self._all_names(search="exc")
        self.assertNotIn(self._names["smoke"], names)
        self.assertNotIn(self._names["probe"], names)
        self.assertNotIn(self._names["si"], names)
        self.assertIn(self._names["vent"], names)


# ─────────────────────────────────────────────────────────────────────────────
# 3. INVARIANT total == len(items) cho CẢ search & non-search path
# ─────────────────────────────────────────────────────────────────────────────
class TestCountEqualsListInvariant(_SeedMixin, FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed("inv")

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        super().tearDownClass()

    def test_nonsearch_total_equals_len_items(self):
        # page_size đủ lớn để 1 trang chứa toàn bộ tập đã lọc của site test
        res = list_assets(page_size=2000)["data"]
        self.assertEqual(res["pagination"]["total"], len(res["items"]),
                         "non-search: total (count) != len(items) — count bỏ sót predicate")

    def test_search_total_equals_len_items(self):
        res = list_assets(search="inv", page_size=2000)["data"]
        self.assertEqual(res["pagination"]["total"], len(res["items"]),
                         "search: raw-SQL count != len(items) — count chưa loại reserved")


# ─────────────────────────────────────────────────────────────────────────────
# 4. KPI parity: dashboard get_overview().assets.total KHÔNG đếm reserved
# ─────────────────────────────────────────────────────────────────────────────
class TestOverviewTotalExcludesReserved(_SeedMixin, FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed("kpi")

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        super().tearDownClass()

    def test_overview_total_equals_list_total(self):
        # KPI card total == drill list total (cùng predicate ⇒ parity)
        ov_total = get_overview()["data"]["assets"]["total"]
        list_total = list_assets(page_size=2000)["data"]["pagination"]["total"]
        self.assertEqual(ov_total, list_total,
                         "KPI total != list total — predicate lệch giữa dashboard & list")

    def test_overview_total_excludes_seeded_reserved(self):
        # Đếm thủ công reserved seeded; overview total + reserved <= raw count.
        ov_total = get_overview()["data"]["assets"]["total"]
        raw_total = frappe.db.count("AC Asset")
        reserved_seeded = 3  # smoke, probe, si
        self.assertLessEqual(ov_total, raw_total - reserved_seeded)


# ─────────────────────────────────────────────────────────────────────────────
# 5. No-clobber: reserved-exclusion AND byt_status/department vẫn đúng + param-safe
# ─────────────────────────────────────────────────────────────────────────────
class TestNoClobberAndParamSafe(_SeedMixin, FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed("ncl")
        # Idempotent pre-clean dept leftover (run trước abort/deadlock dưới chạy
        # song song để rớt PK '_TRSVNCL' chặn re-insert).
        _leftover_dept = frappe.db.get_value(
            "AC Department", {"department_code": "_TRSVNCL"}, "name"
        )
        if _leftover_dept:
            frappe.delete_doc("AC Department", _leftover_dept, force=True,
                              ignore_permissions=True)
            frappe.db.commit()
        cls._dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_TestRSV dept ncl",
            "department_code": "_TRSVNCL",
        }).insert(ignore_permissions=True)
        # Gắn 1 hợp lệ + 1 reserved vào CÙNG department.
        frappe.db.set_value("AC Asset", cls._names["vent"], "department", cls._dept.name)
        frappe.db.set_value("AC Asset", cls._names["smoke"], "department", cls._dept.name)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        if getattr(cls, "_dept", None):
            frappe.delete_doc("AC Department", cls._dept.name, force=True,
                              ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def test_department_filter_and_reserved_exclusion(self):
        # department=dept → chứa 'vent' (hợp lệ) NHƯNG loại 'smoke' (reserved) dù cùng dept.
        items = list_assets(department=self._dept.name, page_size=500)["data"]["items"]
        names = {i["name"] for i in items}
        self.assertIn(self._names["vent"], names)
        self.assertNotIn(self._names["smoke"], names)

    def test_search_param_is_sqli_safe(self):
        # Payload SQLi không được phá query (parametrized) → trả 0 row, KHÔNG throw.
        res = list_assets(search="x' OR '1'='1", page_size=50)["data"]
        self.assertIn("items", res)
        self.assertEqual(res["pagination"]["total"], len(res["items"]))


# ─────────────────────────────────────────────────────────────────────────────
# 6. Grep-guard: literal '_%' / 'SI-%' chỉ định nghĩa 1 nơi (SSoT)
# ─────────────────────────────────────────────────────────────────────────────
class TestNoDuplicateReservedLiteral(FrappeTestCase):
    """Predicate literal '\\_%' và 'SI-%' chỉ được phép trong services/imm00.py."""

    def test_reserved_literal_single_source(self):
        import os
        import re
        base = APP_ROOT
        # bắt literal SI-% hoặc \_% trong .py (ngoài tests, ngoài SoT body)
        pat = re.compile(r"""['"](SI-%|\\_%)['"]""")
        offenders = []
        for root, _dirs, files in os.walk(base):
            if "/tests" in root:
                continue
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(root, fn)
                with open(path, encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        if pat.search(line):
                            if fn == "imm00.py" and "services" in root:
                                continue  # SoT body duy nhất được phép
                            offenders.append(f"{path}:{lineno}: {line.strip()}")
        self.assertEqual(offenders, [],
                         "Literal reserved-prefix lặp ngoài SSoT:\n" + "\n".join(offenders))


# ─────────────────────────────────────────────────────────────────────────────
# 7. RC-LIST-VENDORCLOBBER (Vòng 26 B) — vendor-scope (AUTH-01) KHÔNG bị
#    reserved-exclusion clobber. FR-00-84 / BR-00-35 mục 6 / 07 §III.6.h-VENDORCLOBBER.
# ─────────────────────────────────────────────────────────────────────────────
_VENDOR_USER = "_test_vendor_clobber@example.com"
_VENDOR_USER_EMPTY = "_test_vendor_empty@example.com"


def _ensure_test_user(email: str):
    """Idempotent: tạo User test (disabled, no welcome mail) để làm assigned_to."""
    if frappe.db.exists("User", email):
        return email
    frappe.get_doc({
        "doctype": "User",
        "email": email,
        "first_name": "VendorScope",
        "send_welcome_email": 0,
        "enabled": 1,
    }).insert(ignore_permissions=True)
    return email


class _VendorSeedMixin:
    """Seed 3 nhóm asset THẬT + gắn vendor qua Asset Repair assigned_to.

    Asset Repair (WO-CM) đọc bởi _resolve_vendor_assigned_assets (UNION với PM WO);
    chọn Asset Repair vì ít Link bắt buộc hơn (chỉ asset_ref).

    Nhóm:
      assigned   — asset thường, gắn vendor qua Asset Repair assigned_to → PHẢI hiện.
      assigned_r — asset reserved ('_…'), gắn vendor → loại bởi reserved-exclusion.
      outside    — asset thường, KHÔNG gắn vendor → ẩn (vendor isolation).

    LƯU Ý (entanglement 2 tầng scope): patch ``frappe.get_roles`` → Vendor Engineer
    kích HOẠT CẢ ``apply_vendor_scope`` (theo assigned_to, application-layer) LẪN
    ``permission_query_conditions`` ``ac_asset_query`` (theo responsible_technician,
    Frappe-layer) vì ``scope.frappe`` chính là module ``frappe`` toàn cục. Để asset
    assigned hiện qua ``list_assets`` (đi qua get_list có perm-hook), seed cũng đặt
    ``responsible_technician`` = session-user (test-runner) trên các asset assigned →
    qua được CẢ HAI tầng. Đây vẫn cô lập đúng điểm fix (compose name-safe trong
    ``list_assets``): nếu clobber, assigned biến mất / outside lọt / INVARIANT vỡ.
    """

    @classmethod
    def _vendor_seed(cls, tag: str):
        _ensure_test_user(_VENDOR_USER)
        _ensure_test_user(_VENDOR_USER_EMPTY)
        # idempotent pre-clean
        leftover_cat = frappe.db.get_value(
            "AC Asset Category", {"category_code": f"_TestVS-{tag}"}, "name"
        )
        if leftover_cat:
            for a in frappe.get_all("AC Asset", filters={"asset_category": leftover_cat}, pluck="name"):
                for rp in frappe.get_all("Asset Repair", filters={"asset_ref": a}, pluck="name"):
                    frappe.delete_doc("Asset Repair", rp, force=True, ignore_permissions=True)
                purge_asset(a)
            frappe.delete_doc("AC Asset Category", leftover_cat, force=True, ignore_permissions=True)
            frappe.db.commit()

        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestVS-{tag}",
            "category_name": f"_TestVS cat {tag}",
        }).insert(ignore_permissions=True)
        cls._names = {}
        cls._reps = []
        # session-user của test-runner: ac_asset_query (perm-hook) scope theo
        # responsible_technician = user này khi role bị mock thành Vendor Engineer.
        session_user = frappe.session.user
        spec = [
            ("assigned",   f"Máy thở VS {tag}",   True),   # assigned, thường  → hiện
            ("assigned_r", f"_TestVendorScope {tag}", True),  # assigned, reserved → ẩn
            ("outside",    f"Máy chụp VS {tag}",   False),  # KHÔNG assigned    → ẩn
        ]
        for key, aname, _assign in spec:
            data = {
                "doctype": "AC Asset",
                "asset_name": aname,
                "asset_category": cls._cat.name,
                "manufacturer_sn": f"_VSSN-{tag}-{key}",
                "lifecycle_status": "Active",
            }
            if _assign:
                # qua được tầng perm-hook (responsible_technician) song song với
                # tầng apply_vendor_scope (assigned_to qua Asset Repair).
                data["responsible_technician"] = session_user
            a = _insert_asset(data)
            cls._names[key] = a.name
            if _assign:
                rp = frappe.get_doc({
                    "doctype": "Asset Repair",
                    "asset_ref": a.name,
                    "assigned_to": _VENDOR_USER,
                    "failure_description": f"_VS test repair {tag}",
                    "repair_type": "Corrective",
                    "priority": "Normal",
                }).insert(ignore_permissions=True)
                cls._reps.append(rp.name)
        frappe.db.commit()

    @classmethod
    def _vendor_teardown(cls):
        for rp in getattr(cls, "_reps", []):
            if frappe.db.exists("Asset Repair", rp):
                frappe.delete_doc("Asset Repair", rp, force=True, ignore_permissions=True)
        for n in getattr(cls, "_names", {}).values():
            purge_asset(n)
        if getattr(cls, "_cat", None):
            frappe.delete_doc("AC Asset Category", cls._cat.name, force=True, ignore_permissions=True)
        frappe.db.commit()


def _mock_vendor_roles(*_a, **_k):
    """frappe.get_roles stub → Vendor Engineer (KHÔNG bypass-role)."""
    return ["Vendor Engineer"]


class TestListAssetsVendorScopeReserved(_VendorSeedMixin, FrappeTestCase):
    """RED-first: trên code clobber, vendor thấy asset ngoài-scope (ĐỎ). Sau fix
    (filter-list form) — vendor CHỈ thấy assigned ∖ reserved."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._vendor_seed("vsr")

    @classmethod
    def tearDownClass(cls):
        cls._vendor_teardown()
        super().tearDownClass()

    def _vendor_list(self, assigned, **kw):
        """Gọi list_assets dưới góc nhìn Vendor Engineer mà KHÔNG đụng Frappe DocPerm.

        Patch CHỈ trong module ``scope`` (nơi apply_vendor_scope sống):
          • ``scope.frappe.get_roles`` → Vendor Engineer (không bypass) ⟹
            apply_vendor_scope chèn ``name in <assigned>``.
          • ``scope._resolve_vendor_assigned_assets`` → tập ``assigned`` seed sẵn.
        ``frappe.session.user`` GIỮ là test-runner (full DocPerm) ⟹ get_list/db.count
        KHÔNG bị PermissionError + permission_query_conditions (ac_asset_query) thấy
        senior role → "" (no extra filter). Cô lập đúng logic apply_vendor_scope +
        compose_reserved_into (điểm fix RC-LIST-VENDORCLOBBER)."""
        import assetcore.services.shared.scope as scope
        with patch.object(scope.frappe, "get_roles", _mock_vendor_roles), \
             patch.object(scope, "_resolve_vendor_assigned_assets", lambda u: list(assigned)):
            return list_assets(page_size=2000, **kw)["data"]

    def test_vendor_sees_only_assigned_minus_reserved(self):
        # Vendor được giao [assigned-thật, assigned-reserved]; outside KHÔNG giao.
        assigned = [self._names["assigned"], self._names["assigned_r"]]
        data = self._vendor_list(assigned)
        names = {i["name"] for i in data["items"]}
        # result ⊆ assigned ∧ result ∩ reserved = ∅
        self.assertIn(self._names["assigned"], names,
                      "assigned-thật phải hiện (AUTH-01 restore)")
        self.assertNotIn(self._names["assigned_r"], names,
                         "assigned-reserved phải bị reserved-exclusion loại")
        self.assertNotIn(self._names["outside"], names,
                         "asset ngoài-scope KHÔNG được lộ (vendor isolation — RED trên clobber)")
        # result ⊆ (assigned ∖ reserved) = {assigned-thật}
        self.assertTrue(names <= {self._names["assigned"]},
                        f"result phải ⊆ (assigned ∖ reserved); got {names}")

    def test_vendor_invariant_total_equals_len(self):
        assigned = [self._names["assigned"], self._names["assigned_r"]]
        data = self._vendor_list(assigned)
        self.assertEqual(data["pagination"]["total"], len(data["items"]),
                         "vendor non-search: total (count) != len(items)")

    def test_vendor_invariant_total_equals_len_search(self):
        # search khớp cả assigned-thật ('VS vsr') lẫn outside ('VS vsr') → vẫn AND scope.
        assigned = [self._names["assigned"], self._names["assigned_r"]]
        data = self._vendor_list(assigned, search="VS vsr")
        names = {i["name"] for i in data["items"]}
        self.assertEqual(data["pagination"]["total"], len(data["items"]),
                         "vendor search: raw-count != len(items)")
        self.assertNotIn(self._names["outside"], names,
                         "search KHÔNG được vượt rào scope")
        self.assertNotIn(self._names["assigned_r"], names)

    def test_vendor_empty_scope_returns_zero(self):
        # Vendor chưa được giao asset nào → resolver trả [] → sentinel __none__ AND
        # reserved-exclusion → tập rỗng (KHÔNG fallback toàn bộ asset).
        import assetcore.services.shared.scope as scope
        with patch.object(scope.frappe, "get_roles", _mock_vendor_roles), \
             patch.object(scope, "_resolve_vendor_assigned_assets", lambda u: []):
            data = list_assets(page_size=2000)["data"]
        self.assertEqual(data["items"], [], "empty-scope phải trả 0 row")
        self.assertEqual(data["pagination"]["total"], 0,
                         "empty-scope total phải == 0 (KHÔNG fallback toàn bộ)")

    def test_admin_invariant_unchanged(self):
        # KHÔNG mock → Administrator (bypass scope). Baseline GIỮ.
        data = list_assets(page_size=2000)["data"]
        names = {i["name"] for i in data["items"]}
        self.assertEqual(data["pagination"]["total"], len(data["items"]),
                         "admin: total != len(items) (regression)")
        self.assertIn(self._names["assigned"], names)
        self.assertIn(self._names["outside"], names, "admin thấy mọi asset thường")
        self.assertNotIn(self._names["assigned_r"], names, "reserved vẫn loại cho admin")

    def test_depreciation_endpoints_no_regress(self):
        # 2 endpoint depreciation KHÔNG vendor-scope; base filter không có key name.
        # reserved vẫn bị loại + count==list giữ (chứng minh filters.update an toàn ở đây).
        dep = list_assets_depreciation(page_size=2000)["data"]
        names = {i["name"] for i in dep["items"]}
        self.assertNotIn(self._names["assigned_r"], names,
                         "depreciation list vẫn loại reserved")
        self.assertEqual(dep["pagination"]["total"], len(dep["items"]),
                         "depreciation INVARIANT count==list")
        stats = get_depreciation_stats()["data"]
        self.assertIn("total_gross", stats)

    def test_helpers_not_renamed(self):
        # 3 helper SSoT GIỮ NGUYÊN tên (0 rename) + helper merge name-safe import được.
        from assetcore.services.imm00 import (
            reserved_prefix_sql as _s,
            reserved_prefix_filter as _f,
            reserved_asset_names as _n,
            compose_reserved_into as _merge,
        )
        f = _f()
        self.assertTrue(f == {} or set(f.keys()) == {"name"})
        self.assertTrue(callable(_merge))

    def test_resolver_reads_asset_ref_column(self):
        """Root-cause guard: _resolve_vendor_assigned_assets đọc đúng cột asset_ref
        (KHÔNG phải 'asset' — cột không tồn tại → 1054 nuốt → [] → vendor mất scope).
        Seed gắn assigned + assigned_r vào _VENDOR_USER qua Asset Repair.assigned_to."""
        from assetcore.services.shared.scope import _resolve_vendor_assigned_assets
        resolved = set(_resolve_vendor_assigned_assets(_VENDOR_USER))
        self.assertIn(self._names["assigned"], resolved,
                      "resolver phải đọc được asset gắn qua Asset Repair.asset_ref")
        self.assertIn(self._names["assigned_r"], resolved)
        self.assertNotIn(self._names["outside"], resolved,
                         "asset KHÔNG gắn vendor KHÔNG được resolve")


class TestComposeReservedIntoUnit(FrappeTestCase):
    """Unit test helper SSoT merge name-safe (compose_reserved_into)."""

    def test_no_name_key_dict_preserved(self):
        # input KHÔNG có name → output filter-list = các field cũ + name not in reserved.
        from assetcore.services.imm00 import compose_reserved_into, reserved_asset_names
        out = compose_reserved_into({"lifecycle_status": "Active"})
        # filter-list form: mọi điều kiện gốc giữ, thêm name not-in reserved (nếu có reserved).
        self.assertIsInstance(out, list)
        # lifecycle_status condition phải còn
        ls = [c for c in out if c[1] == "lifecycle_status"]
        self.assertEqual(len(ls), 1)
        self.assertEqual(ls[0][3], "Active")
        reserved = reserved_asset_names()
        name_excl = [c for c in out if c[1] == "name" and c[2] == "not in"]
        if reserved:
            self.assertEqual(len(name_excl), 1)
            self.assertEqual(set(name_excl[0][3]), set(reserved))
        else:
            self.assertEqual(name_excl, [])

    def test_vendor_name_in_kept_alongside_not_in(self):
        # input có name=['in', X] (vendor-scope) → output GIỮ name in X RIÊNG +
        # thêm name not in reserved RIÊNG (2 điều kiện name ANDed, KHÔNG clobber).
        from assetcore.services.imm00 import compose_reserved_into, reserved_asset_names
        out = compose_reserved_into({"name": ["in", ["AC-X", "AC-Y"]]})
        name_in = [c for c in out if c[1] == "name" and c[2] == "in"]
        name_not_in = [c for c in out if c[1] == "name" and c[2] == "not in"]
        self.assertEqual(len(name_in), 1, "name in <assigned> phải còn nguyên (no clobber)")
        self.assertEqual(set(name_in[0][3]), {"AC-X", "AC-Y"})
        if reserved_asset_names():
            self.assertEqual(len(name_not_in), 1,
                             "name not in <reserved> phải đứng RIÊNG (ANDed)")

    def test_empty_name_in_preserved(self):
        # name=['in', []] → giữ rỗng (KHÔNG fallback). Empty set ANDed reserved = rỗng.
        from assetcore.services.imm00 import compose_reserved_into
        out = compose_reserved_into({"name": ["in", []]})
        name_in = [c for c in out if c[1] == "name" and c[2] == "in"]
        self.assertEqual(len(name_in), 1)
        self.assertEqual(name_in[0][3], [])

    def test_db_count_get_list_parity_under_compose(self):
        # INVARIANT: frappe.db.count(filter-list) == len(get_list(filter-list)) +
        # count_with_or cùng số → predicate đồng nhất ở mọi engine.
        from assetcore.services.imm00 import compose_reserved_into
        from assetcore.services.shared.filters import count_with_or
        sample = frappe.get_all("AC Asset", fields=["name"], limit_page_length=3)
        if len(sample) < 2:
            self.skipTest("not enough AC Asset rows")
        assigned = [r["name"] for r in sample]
        flist = compose_reserved_into({"name": ["in", assigned]})
        c = frappe.db.count("AC Asset", filters=flist)
        gl = frappe.get_list("AC Asset", filters=flist, fields=["name"],
                             ignore_permissions=True, limit_page_length=0)
        cwo = count_with_or("AC Asset", flist, None)
        self.assertEqual(c, len(gl))
        self.assertEqual(cwo, len(gl))


class TestNoRawFiltersUpdateNameClobber(FrappeTestCase):
    """Meta grep-guard: trong api/imm00.py, sau apply_vendor_scope(...) cho AC Asset
    (field-map='name') KHÔNG được dùng filters.update(reserved_prefix_filter())
    trực tiếp — phải đi qua helper merge name-safe (compose_reserved_into). Chống
    tái phát RC-LIST-VENDORCLOBBER khi thêm endpoint asset-list mới."""

    def test_no_dict_update_after_vendor_scope_for_asset(self):
        path = frappe.get_app_path("assetcore", "api", "imm00.py")
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
        offenders = []
        last_vendor_scope_asset = None
        for i, line in enumerate(lines):
            if "apply_vendor_scope(" in line and "_DT_ASSET" in line:
                last_vendor_scope_asset = i
            if "filters.update(reserved_prefix_filter())" in line:
                # chỉ vi phạm nếu đứng SAU một apply_vendor_scope(..., _DT_ASSET) gần đó
                # trong CÙNG hàm (heuristic: trong 40 dòng sau scope, chưa gặp 'def ').
                if last_vendor_scope_asset is not None:
                    between = "".join(lines[last_vendor_scope_asset:i])
                    if "\ndef " not in between and "\n@frappe.whitelist" not in between:
                        offenders.append(f"{path}:{i+1}: {line.strip()}")
        self.assertEqual(offenders, [],
                         "filters.update(reserved_prefix_filter()) đứng SAU apply_vendor_scope"
                         "(AC Asset) → clobber name. Dùng compose_reserved_into:\n"
                         + "\n".join(offenders))
