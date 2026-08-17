# assetcore/tests/imm00/test_imm00_byt_expiry_sot.py
# Copyright (c) 2026, AssetCore Team
"""TDD — BR-00-17 (NĐ98): Số ĐK lưu hành BYT sắp/đã hết hạn — SoT predicate.

Phủ:
  - byt_expiry_filter() shape + null-guard + no-op (TestBytExpiryFilterSoT).
  - INVARIANT count==drill: get_overview().assets.byt_* == total list_assets
    (TestBytExpiryCountEqualsDrill) — boundary today / today+30 / today+31 / today-1 / NULL.
  - list_assets(byt_status, department) AND không clobber (TestListAssetsBytStatusNoClobber).
"""
from __future__ import annotations

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days

from assetcore.api.imm00 import list_assets
from assetcore.api.dashboard import get_overview
from assetcore.services.imm00 import byt_expiry_filter, BYT_EXPIRY_SOON_DAYS
from assetcore.tests._helpers._asset_cleanup import purge_asset


class TestBytExpiryFilterSoT(FrappeTestCase):
    """Shape + null-guard + no-op của byt_expiry_filter()."""

    def test_expiring_shape_with_named_const(self):
        ref = today()
        f = byt_expiry_filter("expiring", ref)
        assert f == {"byt_reg_expiry": ["between", [ref, add_days(ref, BYT_EXPIRY_SOON_DAYS)]]}, f
        # named const, KHÔNG literal 30 trong giá trị
        assert BYT_EXPIRY_SOON_DAYS == 30

    def test_expired_shape_strict_with_null_guard(self):
        ref = today()
        f = byt_expiry_filter("expired", ref)
        spec = f["byt_reg_expiry"]
        assert spec[0] == "between", spec
        lo, hi = spec[1]
        # cận trên = ref-1 (inclusive) ⟺ expiry < ref (strict <)
        assert hi == add_days(ref, -1), hi
        # cận dưới = DATE floor → NULL/'' bị loại tường minh (null-guard)
        assert lo == "1000-01-01", lo

    def test_garbage_bucket_is_noop(self):
        assert byt_expiry_filter("garbage") == {}
        assert byt_expiry_filter("") == {}
        assert byt_expiry_filter("EXPIRING") == {}  # case-sensitive → no-op

    def test_null_records_excluded_both_buckets(self):
        # 'between' với 2 mốc ngày thật KHÔNG khớp NULL/'' (SQL NULL-comparison →
        # NULL → loại). Cả 2 bucket đều dùng 'between' → NULL không bao giờ đếm.
        for bucket in ("expiring", "expired"):
            spec = byt_expiry_filter(bucket, today())["byt_reg_expiry"]
            assert spec[0] == "between", bucket

    def test_list_assets_has_byt_status_param(self):
        sig = inspect.signature(list_assets)
        assert "byt_status" in sig.parameters, "list_assets() thiếu param byt_status."


class _BytSeedMixin:
    """Seed asset với byt_reg_expiry tại các biên test."""

    _CAT = "TEST-CAT-BYT-SOT"
    _assets: list[str] = []
    _cat_name: str | None = None

    @classmethod
    def _seed(cls):
        cls._assets = []
        # AC Asset Category autoname=CAT-#### → lookup by category_code, NOT name
        # (LL-TEST-9). Track real doc-name for teardown so the category never leaks.
        cls._cat_name = frappe.db.get_value(
            "AC Asset Category", {"category_code": cls._CAT}, "name"
        )
        if not cls._cat_name:
            doc = frappe.get_doc({
                "doctype": "AC Asset Category",
                "category_name": "_Test BYT SoT",
                "category_code": cls._CAT,
            }).insert(ignore_permissions=True)
            cls._cat_name = doc.name
        ref = today()
        # (suffix, expiry) — biên xung quanh window.
        plan = [
            ("today", ref),                       # expiring (biên dưới)
            ("plus30", add_days(ref, BYT_EXPIRY_SOON_DAYS)),   # expiring (biên trên)
            ("plus31", add_days(ref, BYT_EXPIRY_SOON_DAYS + 1)),  # OUT cả 2
            ("minus1", add_days(ref, -1)),        # expired
            ("null", None),                       # OUT cả 2 (chưa khai báo ĐK)
        ]
        for suffix, expiry in plan:
            # NON-reserved asset_name (KHÔNG prefix '_'): data-hygiene SSoT ẩn '_…'
            # khỏi list_assets; fixture cần XUẤT HIỆN trong drill ⇒ tên thường.
            name = f"ZZTEST-BYT-{suffix}"
            # NHẬN NUÔI bản rò của lượt trước thay vì `continue`: bỏ qua nghĩa là
            # fixture cũ (hạn đã lùi vào quá khứ) ở lại DB, không được đăng ký để
            # dọn, và test tự sập theo NGÀY — đúng sự cố 2026-08-14 (asset rò từ
            # 2026-07-22 khiến 'ZZTEST-BYT-today' rơi sang rổ 'đã hết hạn').
            stale = frappe.db.get_value("AC Asset", {"asset_name": name}, "name")
            if stale:
                frappe.db.set_value("AC Asset", stale, "byt_reg_expiry", expiry,
                                    update_modified=False)
                cls._assets.append(stale)
                continue
            # lifecycle_status để mặc định (Draft) — byt filter độc lập với lifecycle;
            # ép Active vi phạm workflow guard, không cần cho test này.
            doc = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": name,
                "asset_category": cls._cat_name,
            })
            if expiry is not None:
                doc.byt_reg_expiry = expiry
            doc.insert(ignore_permissions=True)
            cls._assets.append(doc.name)

    @classmethod
    def _teardown(cls):
        # purge_asset, KHÔNG delete_doc bọc `except: pass`: WR-03 (on_trash) chặn xoá
        # cứng khi asset đã có Sự kiện vòng đời ⇒ except nuốt lỗi ⇒ rò 5 asset MỖI
        # lượt chạy mà test vẫn xanh (đo 2026-08-14).
        for n in cls._assets:
            purge_asset(n)
        # Purge the self-seeded category too (by resolved doc-name) so it never
        # leaks into prod-like category lists.
        if cls._cat_name and frappe.db.exists("AC Asset Category", cls._cat_name):
            try:
                frappe.delete_doc("AC Asset Category", cls._cat_name,
                                  force=True, ignore_permissions=True)
            except Exception:
                pass
        frappe.db.commit()


class TestBytExpiryCountEqualsDrill(_BytSeedMixin, FrappeTestCase):
    """INVARIANT count==drill: KPI count == total list_assets cùng bucket."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed()

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        super().tearDownClass()

    def _drill_total(self, bucket: str) -> int:
        return list_assets(byt_status=bucket, page_size=500)["data"]["pagination"]["total"]

    def test_expiring_count_equals_drill(self):
        kpi = get_overview()["data"]["assets"]["byt_expiring_30d"]
        drill = self._drill_total("expiring")
        assert kpi == drill, f"expiring KPI={kpi} != drill={drill}"

    def test_expired_count_equals_drill(self):
        kpi = get_overview()["data"]["assets"]["byt_expired"]
        drill = self._drill_total("expired")
        assert kpi == drill, f"expired KPI={kpi} != drill={drill}"

    def test_seeded_boundaries_present(self):
        # Seed của test phải nằm trong drill tương ứng (sanity — không bị lọc nhầm).
        exp_names = {
            r["asset_name"] for r in list_assets(byt_status="expiring", page_size=500)["data"]["items"]
        }
        assert "ZZTEST-BYT-today" in exp_names
        assert "ZZTEST-BYT-plus30" in exp_names
        assert "ZZTEST-BYT-plus31" not in exp_names
        assert "ZZTEST-BYT-null" not in exp_names
        expd_names = {
            r["asset_name"] for r in list_assets(byt_status="expired", page_size=500)["data"]["items"]
        }
        assert "ZZTEST-BYT-minus1" in expd_names
        assert "ZZTEST-BYT-null" not in expd_names


class TestListAssetsBytStatusNoClobber(_BytSeedMixin, FrappeTestCase):
    """byt_status AND department không clobber + bucket rác = no-op."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._seed()

    @classmethod
    def tearDownClass(cls):
        cls._teardown()
        super().tearDownClass()

    def test_byt_status_and_category_both_applied(self):
        # Cùng category seeded + bucket expiring → chỉ asset thoả CẢ 2 ràng buộc.
        items = list_assets(byt_status="expiring", asset_category=self._CAT, page_size=500)["data"]["items"]
        for it in items:
            assert it["asset_category"] == self._CAT
        names = {it["asset_name"] for it in items}
        assert "ZZTEST-BYT-today" in names           # thoả cả 2
        assert "ZZTEST-BYT-plus31" not in names       # đúng category nhưng OUT bucket

    def test_garbage_byt_status_is_noop(self):
        # bucket rác → byt filter bỏ qua; list trả như không có byt_status.
        with_garbage = list_assets(byt_status="garbage", asset_category=self._CAT, page_size=500)["data"]["pagination"]["total"]
        without = list_assets(asset_category=self._CAT, page_size=500)["data"]["pagination"]["total"]
        assert with_garbage == without, f"garbage no-op fail: {with_garbage} != {without}"
