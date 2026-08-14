# assetcore/tests/test_imm00_byt_expiry.py
# Copyright (c) 2026, AssetCore Team
"""TDD — BR-00-17 (NĐ98): Số đăng ký lưu hành BYT sắp/đã hết hạn — SoT predicate.

Bám 100% Core Doc acceptance:
  - byt_expiry_filter(bucket) là Single Source of Truth (services/imm00) cho CẢ
    KPI count (dashboard get_overview) LẪN drill list (api/imm00 list_assets).
  - INVARIANT count==drill: get_overview().assets.byt_expiring_30d ==
    total(list_assets(byt_status='expiring')); byt_expired tương tự, byte-for-byte.
  - 'expiring' = [today, today+30]; 'expired' = < today; cả 2 LOẠI NULL/''.
  - list_assets(byt_status=...) HỢP NHẤT (AND) với mọi filter khác, KHÔNG clobber,
    GIỮ apply_vendor_scope. byt_status lạ → no-op (không throw).
"""
from __future__ import annotations

import frappe
from frappe.utils import today, add_days, nowdate
from frappe.tests.utils import FrappeTestCase

from assetcore.services.imm00 import byt_expiry_filter, BYT_EXPIRY_SOON_DAYS
from assetcore.api.imm00 import list_assets
from assetcore.api.dashboard import get_overview
from assetcore.tests._asset_cleanup import purge_asset
from assetcore.tests._helpers.paths import APP_ROOT


# ─────────────────────────────────────────────────────────────────────────────
# 1. SoT predicate shape — pure (không cần DB)
# ─────────────────────────────────────────────────────────────────────────────
class TestBytExpiryFilterSoT(FrappeTestCase):
    """byt_expiry_filter(bucket) trả filter dict đúng shape + NULL-guard + no-op."""

    def test_const_is_30_not_literal(self):
        self.assertEqual(BYT_EXPIRY_SOON_DAYS, 30)

    def test_expiring_shape_between_today_plus_30(self):
        ref = "2026-06-03"
        f = byt_expiry_filter("expiring", ref)
        self.assertIn("byt_reg_expiry", f)
        op, window = f["byt_reg_expiry"]
        self.assertEqual(op, "between")
        # cận trên = today + BYT_EXPIRY_SOON_DAYS (named const, không literal 30)
        self.assertEqual(window, [ref, add_days(ref, BYT_EXPIRY_SOON_DAYS)])

    def test_expiring_null_guard(self):
        # 'between [today, today+30]' loại NULL/'' (NULL fail; '' không nằm trong cửa sổ).
        f = byt_expiry_filter("expiring", "2026-06-03")
        op, window = f["byt_reg_expiry"]
        self.assertEqual(op, "between")
        # Cận dưới là 1 ngày hợp lệ (>=today) → '' / NULL không thể lọt.
        self.assertEqual(window[0], "2026-06-03")

    def test_expired_shape_strict_less_than_today(self):
        ref = "2026-06-03"
        f = byt_expiry_filter("expired", ref)
        op, window = f["byt_reg_expiry"]
        self.assertEqual(op, "between")
        # cận trên = ref-1 (inclusive) ⟺ expiry < ref (strict); expiry==today CHƯA hết hạn.
        self.assertEqual(window[1], add_days(ref, -1))

    def test_expired_null_guard_floor_excludes_null_and_empty(self):
        # cận dưới = MariaDB DATE min (sentinel) → NULL/'' bị loại TƯỜNG MINH.
        f = byt_expiry_filter("expired", "2026-06-03")
        op, window = f["byt_reg_expiry"]
        self.assertEqual(op, "between")
        # Floor phải là một mốc DATE rất nhỏ (không phải None / '').
        self.assertTrue(window[0] and window[0] < "2000-01-01")

    def test_garbage_bucket_is_noop_empty_dict(self):
        self.assertEqual(byt_expiry_filter("garbage"), {})
        self.assertEqual(byt_expiry_filter(""), {})
        self.assertEqual(byt_expiry_filter(None), {})  # type: ignore[arg-type]


# ─────────────────────────────────────────────────────────────────────────────
# Helper: seed assets có byt_reg_expiry tại các mốc biên
# ─────────────────────────────────────────────────────────────────────────────
def _insert_asset(data: dict):
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


class _BytSeedMixin:
    """Seed 5 asset tại các mốc biên BYT expiry trong 1 category cô lập."""

    @classmethod
    def _seed(cls, tag: str):
        cls._cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_code": f"_TestBYT-{tag}",
            "category_name": f"_TestBYT cat {tag}",
        }).insert(ignore_permissions=True)
        ref = today()
        cls._exp_today = add_days(ref, 0)      # biên TRONG 'expiring'
        cls._exp_p30 = add_days(ref, 30)       # biên TRONG 'expiring' (today+30)
        cls._exp_p31 = add_days(ref, 31)       # NGOÀI cả 2
        cls._exp_m1 = add_days(ref, -1)        # TRONG 'expired'
        cls._names = []
        spec = [
            ("today", cls._exp_today),
            ("p30", cls._exp_p30),
            ("p31", cls._exp_p31),
            ("m1", cls._exp_m1),
            ("null", None),                    # NULL → loại cả 2 bucket
        ]
        for sub, exp in spec:
            d = {
                "doctype": "AC Asset",
                # NON-reserved asset_name: data-hygiene SSoT ẩn '_…' khỏi list_assets;
                # fixture byt cần XUẤT HIỆN trong drill ⇒ tên thường (KHÔNG prefix '_').
                "asset_name": f"ZZTestBYT {tag}-{sub}",
                "asset_category": cls._cat.name,
                "manufacturer_sn": f"ZZTestBYTSN-{tag}-{sub}",
                "lifecycle_status": "Active",
            }
            if exp is not None:
                d["byt_reg_expiry"] = exp
            cls._names.append(_insert_asset(d).name)
        frappe.db.commit()

    @classmethod
    def _teardown(cls):
        for n in getattr(cls, "_names", []):
            purge_asset(n)
        if getattr(cls, "_cat", None):
            frappe.delete_doc("AC Asset Category", cls._cat.name, force=True,
                              ignore_permissions=True)
        frappe.db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# 2. INVARIANT count==drill (boundary) — get_overview KPI == list_assets total
# ─────────────────────────────────────────────────────────────────────────────
class TestBytExpiryCountEqualsDrill(_BytSeedMixin, FrappeTestCase):
    """get_overview().assets.byt_* == total(list_assets(byt_status=*)) byte-for-byte."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed("ce")

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        super().tearDownClass()

    def test_count_equals_drill_expiring(self):
        ov = get_overview()["data"]["assets"]
        drill = list_assets(byt_status="expiring", page_size=500)["data"]
        self.assertEqual(ov["byt_expiring_30d"], drill["pagination"]["total"])

    def test_count_equals_drill_expired(self):
        ov = get_overview()["data"]["assets"]
        drill = list_assets(byt_status="expired", page_size=500)["data"]
        self.assertEqual(ov["byt_expired"], drill["pagination"]["total"])

    def test_boundary_membership_expiring(self):
        # today & today+30 IN; today+31 OUT; today-1 OUT (đó là expired); NULL OUT.
        items = list_assets(byt_status="expiring", page_size=500)["data"]["items"]
        names = {i["name"] for i in items}
        self.assertIn(self._names[0], names)   # today
        self.assertIn(self._names[1], names)   # today+30
        self.assertNotIn(self._names[2], names)  # today+31
        self.assertNotIn(self._names[3], names)  # today-1
        self.assertNotIn(self._names[4], names)  # NULL

    def test_boundary_membership_expired(self):
        items = list_assets(byt_status="expired", page_size=500)["data"]["items"]
        names = {i["name"] for i in items}
        self.assertIn(self._names[3], names)     # today-1
        self.assertNotIn(self._names[0], names)  # today (chưa hết hạn — strict <)
        self.assertNotIn(self._names[4], names)  # NULL

    def test_null_excluded_from_both_buckets(self):
        exp = list_assets(byt_status="expiring", page_size=500)["data"]["items"]
        exd = list_assets(byt_status="expired", page_size=500)["data"]["items"]
        self.assertNotIn(self._names[4], {i["name"] for i in exp})
        self.assertNotIn(self._names[4], {i["name"] for i in exd})


# ─────────────────────────────────────────────────────────────────────────────
# 3. No-clobber: byt_status AND department; bucket lạ = no-op
# ─────────────────────────────────────────────────────────────────────────────
class TestListAssetsBytStatusNoClobber(_BytSeedMixin, FrappeTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed("nc")
        # Gắn 1 asset (today) vào 1 department cô lập để test AND-merge.
        cls._dept = frappe.get_doc({
            "doctype": "AC Department",
            "department_name": "_TestBYT dept nc",
            "department_code": "_TBYTNC",
        }).insert(ignore_permissions=True)
        frappe.db.set_value("AC Asset", cls._names[0], "department", cls._dept.name)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        if getattr(cls, "_dept", None):
            frappe.delete_doc("AC Department", cls._dept.name, force=True,
                              ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def test_byt_status_and_department_conjoined(self):
        # byt_status='expiring' AND department=dept → CHỈ asset 'today' (đã gắn dept).
        items = list_assets(byt_status="expiring", department=self._dept.name,
                            page_size=500)["data"]["items"]
        names = {i["name"] for i in items}
        self.assertEqual(names, {self._names[0]})

    def test_department_filter_not_clobbered_by_byt(self):
        # department-only: asset today thuộc dept; nhưng các asset BYT khác KHÔNG.
        items = list_assets(department=self._dept.name, page_size=500)["data"]["items"]
        names = {i["name"] for i in items}
        self.assertEqual(names, {self._names[0]})

    def test_garbage_byt_status_is_noop(self):
        # bucket lạ → KHÔNG throw, KHÔNG filter theo byt → trả như không truyền.
        base = list_assets(department=self._dept.name, page_size=500)["data"]["pagination"]["total"]
        same = list_assets(byt_status="garbage", department=self._dept.name,
                           page_size=500)["data"]["pagination"]["total"]
        self.assertEqual(base, same)


# ─────────────────────────────────────────────────────────────────────────────
# 4. RED-experiment guard (grep): 0 inline byt window literal NGOÀI thân SoT
# ─────────────────────────────────────────────────────────────────────────────
class TestNoInlineBytWindowLiteral(FrappeTestCase):
    """Grep-guard: chỉ byt_expiry_filter() body được phép có literal window."""

    def test_no_inline_byt_window_outside_sot(self):
        import os
        import re
        base = APP_ROOT
        # literal window patterns: 'byt_reg_expiry' theo sau bởi between/< (list spec)
        pat = re.compile(r"byt_reg_expiry[\"']\s*:\s*\[\s*[\"'](between|<)")
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
                            # Cho phép DUY NHẤT trong thân byt_expiry_filter (services/imm00.py).
                            if fn == "imm00.py" and "services" in root:
                                continue
                            offenders.append(f"{path}:{lineno}: {line.strip()}")
        self.assertEqual(offenders, [], "Inline byt window literal ngoài SoT:\n" + "\n".join(offenders))
