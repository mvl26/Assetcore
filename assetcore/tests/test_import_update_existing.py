# assetcore/tests/test_import_update_existing.py
# Copyright (c) 2026, AssetCore Team
"""TDD — NHẬP ĐỂ CẬP NHẬT bản ghi đã có (loại dữ liệu phẳng).

Bối cảnh (đo 2026-08-11): vòng "Xuất Excel → sửa → Nhập lại" chỉ chạy được cho
Người dùng (upsert theo email) và Mẫu bảng kiểm. 6 loại còn lại CHẶN cứng "đã tồn
tại" — muốn sửa 200 thiết bị phải mở từng bản ghi trên màn hình. Riêng Nhà cung
cấp còn tệ hơn: KHÔNG có validator + mã NCC là cột tuỳ chọn ⇒ nhập lại cùng file
lần hai đẻ ra bản ghi trùng, không lỗi, không cảnh báo.

Hợp đồng đã chốt với người dùng:
  - Cập nhật là OPT-IN (`update_existing`), mặc định TẮT.
  - Ô ĐỂ TRỐNG trong file ⇒ GIỮ NGUYÊN giá trị cũ (không xoá trắng).
  - Tài sản: cập nhật được thông tin mô tả, nhưng KHÓA mã tài sản / trạng thái
    vòng đời / serial — đổi qua import là đi vòng workflow và làm nhoè audit trail.
"""
from __future__ import annotations

import io

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.api.import_data import _do_import, _do_preview
from assetcore.services.shared import ServiceError
from assetcore.utils.import_helpers import (
    TEMPLATE_BANNER_PREFIX,
    UPDATE_KEY_BY_DOCTYPE,
    field_label,
    find_existing_by_key,
)

_SUP = "AC Supplier"
_CAT = "AC Asset Category"
_TAG = "_TESTUPD"


class _ImportFileMixin:
    _files: list[str] = []

    def _save_csv(self, doctype: str, fields: list[str], data_rows: list[list]) -> str:
        import csv

        from frappe.utils.file_manager import save_file

        buf = io.StringIO()
        w = csv.writer(buf)
        # Banner mang chuỗi ngẫu nhiên: Frappe dedupe File theo `content_hash` và
        # tái dùng đường dẫn cũ — file nội dung y hệt lần chạy trước (đã bị dọn
        # khỏi đĩa) làm `save_file` nổ FileNotFoundError. Parser bỏ hàng 1 nên
        # chuỗi này không ảnh hưởng dữ liệu.
        w.writerow([f"{TEMPLATE_BANNER_PREFIX}: test {frappe.generate_hash(length=10)} "
                    "| điền từ HÀNG 6"])
        w.writerow(fields)
        w.writerow([field_label(doctype, f) for f in fields])
        w.writerow(["mô tả"] * len(fields))
        w.writerow(["ví dụ"] * len(fields))
        for r in data_rows:
            w.writerow(r)

        fdoc = save_file(
            f"upd_{frappe.generate_hash(length=8)}.csv",
            buf.getvalue().encode("utf-8-sig"), "", "", is_private=1,
        )
        self.__class__._files.append(fdoc.name)
        frappe.db.commit()
        return fdoc.file_url

    @classmethod
    def _purge_files(cls):
        for f in cls._files:
            if frappe.db.exists("File", f):
                frappe.delete_doc("File", f, force=True, ignore_permissions=True)
        cls._files = []


class TestSupplierImportNoLongerDuplicates(_ImportFileMixin, FrappeTestCase):
    """Nhà cung cấp: nhập lại cùng file KHÔNG được đẻ bản ghi trùng."""

    _FIELDS = ["supplier_name", "supplier_code", "country", "phone", "address"]
    _NAME = f"{_TAG} NCC Trùng"

    def tearDown(self):
        for r in frappe.get_all(_SUP, filters={"supplier_name": ["like", f"{_TAG}%"]}):
            frappe.delete_doc(_SUP, r.name, force=True, ignore_permissions=True)
        frappe.db.commit()
        self._purge_files()
        super().tearDown()

    def _rows(self, **kw) -> list[list]:
        base = {"supplier_name": self._NAME, "country": "Việt Nam"}
        base.update(kw)
        return [[str(base.get(f, "")) for f in self._FIELDS]]

    def test_reimport_without_update_is_blocked_not_duplicated(self):
        first = self._save_csv(_SUP, self._FIELDS, self._rows())
        self.assertEqual(_do_import(_SUP, first)["success"], 1)

        second = self._save_csv(_SUP, self._FIELDS, self._rows(phone="0900000000"))
        with self.assertRaises(ServiceError):
            _do_import(_SUP, second)

        self.assertEqual(
            frappe.db.count(_SUP, {"supplier_name": self._NAME}), 1,
            "nhập lại lần hai KHÔNG được đẻ nhà cung cấp trùng tên",
        )

    def test_update_existing_writes_into_the_same_record(self):
        first = self._save_csv(_SUP, self._FIELDS, self._rows(phone="0911111111"))
        _do_import(_SUP, first)
        name = frappe.get_all(_SUP, filters={"supplier_name": self._NAME})[0].name

        second = self._save_csv(_SUP, self._FIELDS, self._rows(phone="0922222222"))
        res = _do_import(_SUP, second, update_existing=True)

        self.assertEqual(res["updated"], 1, res)
        self.assertEqual(res["success"], 1, res)
        self.assertEqual(frappe.db.count(_SUP, {"supplier_name": self._NAME}), 1)
        self.assertEqual(frappe.db.get_value(_SUP, name, "phone"), "0922222222")

    def test_blank_cell_keeps_the_old_value(self):
        """Ô để trống = 'tôi không quan tâm cột này', KHÔNG phải 'xoá đi'."""
        first = self._save_csv(
            _SUP, self._FIELDS, self._rows(phone="0911111111", address="Số 1 Hai Bà Trưng"))
        _do_import(_SUP, first)
        name = frappe.get_all(_SUP, filters={"supplier_name": self._NAME})[0].name

        # Lần hai chỉ điền điện thoại, bỏ trống địa chỉ.
        second = self._save_csv(_SUP, self._FIELDS, self._rows(phone="0933333333"))
        _do_import(_SUP, second, update_existing=True)

        doc = frappe.get_doc(_SUP, name)
        self.assertEqual(doc.phone, "0933333333", "ô có dữ liệu phải ghi đè")
        self.assertEqual(doc.address, "Số 1 Hai Bà Trưng",
                         "ô để trống KHÔNG được xoá trắng giá trị cũ")

    def test_supplier_code_wins_over_name_as_identity(self):
        """Có mã thì khoá theo mã ⇒ đổi được TÊN nhà cung cấp bằng import."""
        code = f"{_TAG}-001"
        first = self._save_csv(_SUP, self._FIELDS, self._rows(supplier_code=code))
        _do_import(_SUP, first)
        name = frappe.get_all(_SUP, filters={"supplier_code": code})[0].name

        renamed = f"{_TAG} NCC Đổi tên"
        second = self._save_csv(
            _SUP, self._FIELDS,
            [[renamed, code, "Việt Nam", "", ""]],
        )
        res = _do_import(_SUP, second, update_existing=True)

        self.assertEqual(res["updated"], 1, res)
        self.assertEqual(frappe.db.get_value(_SUP, name, "supplier_name"), renamed)
        self.assertEqual(frappe.db.count(_SUP, {"supplier_code": code}), 1)


class TestCategoryImportUpdate(_ImportFileMixin, FrappeTestCase):
    """Danh mục tài sản — đại diện cho các loại có validator sẵn."""

    _FIELDS = ["category_name", "description", "default_pm_interval_days"]
    _NAME = f"{_TAG} Danh mục"

    def tearDown(self):
        for r in frappe.get_all(_CAT, filters={"category_name": ["like", f"{_TAG}%"]}):
            frappe.delete_doc(_CAT, r.name, force=True, ignore_permissions=True)
        frappe.db.commit()
        self._purge_files()
        super().tearDown()

    def test_duplicate_error_becomes_update_warning(self):
        first = self._save_csv(_CAT, self._FIELDS, [[self._NAME, "Mô tả cũ", "180"]])
        _do_import(_CAT, first)

        second = self._save_csv(_CAT, self._FIELDS, [[self._NAME, "Mô tả mới", ""]])

        blocked = _do_preview(_CAT, second)
        self.assertTrue(blocked["errors"], "mặc định vẫn chặn")
        self.assertEqual(blocked["will_update"], 0)
        self.assertEqual(blocked["will_create"], 0,
                         "dòng trùng không được tính là sẽ tạo mới")

        allowed = _do_preview(_CAT, second, update_existing=True)
        self.assertEqual(allowed["errors"], [], "bật cập nhật thì hết lỗi chặn")
        self.assertEqual(allowed["will_update"], 1)
        self.assertTrue(any("cập nhật" in w["message"].lower()
                            for w in allowed["warnings"]), allowed["warnings"])

        res = _do_import(_CAT, second, update_existing=True)
        self.assertEqual(res["updated"], 1, res)
        name = frappe.get_all(_CAT, filters={"category_name": self._NAME})[0].name
        doc = frappe.get_doc(_CAT, name)
        self.assertEqual(doc.description, "Mô tả mới")
        self.assertEqual(doc.default_pm_interval_days, 180,
                         "ô để trống giữ nguyên chu kỳ cũ")

    def test_mixed_file_creates_new_and_updates_old_in_one_pass(self):
        first = self._save_csv(_CAT, self._FIELDS, [[self._NAME, "Cũ", ""]])
        _do_import(_CAT, first)

        second = self._save_csv(_CAT, self._FIELDS, [
            [self._NAME, "Đã sửa", ""],
            [f"{_TAG} Danh mục mới", "Tạo mới", ""],
        ])
        prev = _do_preview(_CAT, second, update_existing=True)
        self.assertEqual((prev["will_create"], prev["will_update"]), (1, 1), prev)

        res = _do_import(_CAT, second, update_existing=True)
        self.assertEqual((res["success"], res["updated"]), (2, 1), res)
        self.assertEqual(frappe.db.count(_CAT, {"category_name": ["like", f"{_TAG}%"]}), 2)


class TestAssetImportUpdateLocksSensitiveColumns(_ImportFileMixin, FrappeTestCase):
    """Tài sản: sửa được thông tin mô tả, KHÔNG sửa được thứ gắn với workflow."""

    _DOCTYPE = "AC Asset"
    _FIELDS = ["asset_code", "asset_name", "asset_category", "lifecycle_status", "notes"]
    # KHÔNG dùng tiền tố "_": validator chặn mã tài sản bắt đầu bằng ký tự dành
    # riêng cho fixture (`_RESERVED_NAME_PREFIX`).
    _CODE = "ZZ-TESTUPD-ASSET-01"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.cat = frappe.get_doc({
            "doctype": _CAT, "category_name": f"{_TAG} DM tài sản",
        }).insert(ignore_permissions=True)
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        # `AC Asset.on_trash` (WR-03) chặn xoá cứng khi còn audit trail / lịch sử
        # thiết bị, và `force=True` KHÔNG bỏ qua on_trash tuỳ biến — dùng helper
        # dùng chung thay vì tự chế (LL-TEST-17).
        from assetcore.tests._asset_cleanup import purge_asset, purge_category_by_name

        for r in frappe.get_all(cls._DOCTYPE, filters={"asset_code": cls._CODE}):
            purge_asset(r.name)
        purge_category_by_name(cls.cat.category_name)
        frappe.db.commit()
        cls._purge_files()
        super().tearDownClass()

    def _row(self, **kw) -> list[list]:
        base = {
            "asset_code": self._CODE,
            "asset_name": f"{_TAG} Máy thở",
            "asset_category": self.cat.category_name,
        }
        base.update(kw)
        return [[str(base.get(f, "")) for f in self._FIELDS]]

    def test_description_updates_but_lifecycle_status_stays_put(self):
        first = self._save_csv(self._DOCTYPE, self._FIELDS, self._row(notes="Ghi chú cũ"))
        self.assertEqual(_do_preview(self._DOCTYPE, first)["errors"], [],
                         "file dựng cho test phải sạch trước khi nói về cập nhật")
        self.assertEqual(_do_import(self._DOCTYPE, first)["success"], 1)
        name = frappe.get_all(self._DOCTYPE, filters={"asset_code": self._CODE})[0].name
        status_before = frappe.db.get_value(self._DOCTYPE, name, "lifecycle_status")

        second = self._save_csv(
            self._DOCTYPE, self._FIELDS,
            self._row(notes="Ghi chú mới", lifecycle_status="Đã thanh lý"),
        )

        prev = _do_preview(self._DOCTYPE, second, update_existing=True)
        self.assertTrue(
            any(w["field"] == "lifecycle_status" for w in prev["warnings"]),
            f"phải báo trước là trạng thái vòng đời KHÔNG đổi: {prev['warnings']}",
        )

        res = _do_import(self._DOCTYPE, second, update_existing=True)
        self.assertEqual(res["updated"], 1, res)

        doc = frappe.get_doc(self._DOCTYPE, name)
        self.assertEqual(doc.notes, "Ghi chú mới", "cột mô tả phải cập nhật được")
        self.assertEqual(
            doc.lifecycle_status, status_before,
            "trạng thái vòng đời phải giữ nguyên — đổi bằng file là đi vòng workflow",
        )
        self.assertEqual(frappe.db.count(self._DOCTYPE, {"asset_code": self._CODE}), 1)


class TestUpdateKeySsot(FrappeTestCase):
    """Khoá nhận dạng bản ghi phải khai một chỗ, phủ mọi loại nhập được."""

    #: Loại dữ liệu có đường cập nhật RIÊNG, không đi qua `UPDATE_KEY_BY_DOCTYPE`.
    #: `User` khoá theo email (chính là tên bản ghi) và upsert sẵn trong
    #: `_do_import_users` — thêm khoá ở map là khai hai lần, lệch lúc nào không hay.
    _OWN_UPSERT_PATH = {"User"}

    def test_every_importable_doctype_can_be_updated_somehow(self):
        """Nhập được thì phải sửa lại được — bằng một trong ba đường, không bỏ sót."""
        from assetcore.utils.import_helpers import (
            GROUPED_IMPORT_DOCTYPES,
            SUPPORTED_REF_DOCTYPES,
        )

        missing = [
            dt for dt in SUPPORTED_REF_DOCTYPES
            if dt not in GROUPED_IMPORT_DOCTYPES
            and dt not in UPDATE_KEY_BY_DOCTYPE
            and dt not in self._OWN_UPSERT_PATH
        ]
        self.assertEqual(
            missing, [],
            f"nhập được nhưng không sửa lại được bằng import: {missing}",
        )

    def test_every_update_key_field_exists_on_its_doctype(self):
        """Khoá gõ sai tên cột = im lặng không bao giờ khớp ⇒ luôn tạo bản mới."""
        for doctype, fields in UPDATE_KEY_BY_DOCTYPE.items():
            meta = frappe.get_meta(doctype)
            for field in fields:
                self.assertTrue(
                    meta.get_field(field),
                    f"{doctype}: không có cột '{field}'",
                )

    def test_validator_exists_for_every_importable_doctype(self):
        """Không validator = không phát hiện trùng = nhân đôi im lặng (lỗi NCC)."""
        from assetcore.services.import_validators import VALIDATOR_REGISTRY
        from assetcore.utils.import_helpers import SUPPORTED_REF_DOCTYPES

        missing = [dt for dt in SUPPORTED_REF_DOCTYPES if dt not in VALIDATOR_REGISTRY]
        self.assertEqual(missing, [], f"loại dữ liệu không ai kiểm: {missing}")

    def test_lookup_is_batched_not_one_query_per_row(self):
        """200 dòng không được bắn 200 truy vấn — file thật hàng trăm hàng."""
        rows = [{"category_name": f"{_TAG} không tồn tại {i}"} for i in range(200)]
        calls: list[str] = []
        original = frappe.get_all

        def counting_get_all(*args, **kwargs):
            calls.append(str(args[0]) if args else "")
            return original(*args, **kwargs)

        frappe.get_all = counting_get_all
        try:
            found = find_existing_by_key(_CAT, rows)
        finally:
            frappe.get_all = original

        self.assertEqual(found, {})
        self.assertLessEqual(len(calls), 2, f"phải gom truy vấn theo lô: {len(calls)}")
