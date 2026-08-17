# Copyright (c) 2026, AssetCore Team
"""AC-CR-106 — vendor-scope là PHÉP GIAO, KHÔNG phải PHÉP GÁN.

Class-of-bug (đo trên đĩa 2026-07-30, ``services/shared/scope.py:174`` bản cũ):

    filters[field] = ["in", assigned]        # GÁN — xoá sạch ý định của caller

Hệ quả kép, cả hai đều CÂM (không lỗi, không log, test cũ vẫn xanh):

  1. **Leo phạm vi so với caller** — Vendor Engineer deep-link ĐÚNG MỘT thiết bị
     (``?asset=A9`` → ``filters={"asset_ref": "A9"}``) nhận về **MỌI** phiếu của **MỌI**
     thiết bị họ được giao. Không phải lỗ IDOR (vẫn trong phạm vi được giao) nhưng là
     **rò dữ liệu so với yêu cầu** + người dùng tin rằng đang xem 1 thiết bị.
  2. **Vỡ bất biến count == drill** cho đúng persona đó: ô «…» trên màn chi tiết thiết
     bị đếm theo 1 thiết bị, còn màn drill trả toàn bộ ⇒ 2 con số không bao giờ khớp.

Hợp đồng sau fix (``_intersect_in``): shape ĐẦU VÀO nhận cả 3 dạng (vô hướng ·
``["in", [...]]`` · ``["=", x]``, cộng ``None``/khuyết/list literal), shape ĐẦU RA
LUÔN ``["in", <list>]`` ⇒ ``services/imm11.py::_extract_asset_in_scope`` (đã vá
run-4 cho shape vô hướng) và ``_normalize_list_filters`` KHÔNG cần đổi. Giao rỗng ⇒
``["in", ["__none__"]]`` (0 dòng — KHÔNG phải "toàn bộ thiết bị của tôi").

Run:
  bench --site miyano run-tests --app assetcore \
        --module assetcore.tests.integration.test_vendor_scope_intersect
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.services.shared.scope import (
    _VENDOR_SCOPE_FIELD_MAP,
    _intersect_in,
    apply_vendor_scope,
)

_SENTINEL = "__none__"
_ASSIGNED = ["A1", "A2"]

_VENDOR_EMAIL = "acr106_vendor@example.invalid"

#: DocType row-scoped dùng cho TC-VSCOPE-16 (có `permission_query_conditions` thật:
#: `asset_commissioning_query`, `hooks.py:444`) — cần dữ liệu THẬT nên không mock được.
_COMM_DT = "Asset Commissioning"


class TestIntersectInHelper(unittest.TestCase):
    """``_intersect_in`` là hàm THUẦN (0 truy vấn) — 3 shape + rỗng-an-toàn."""

    def test_tc_be_cr106_1_scalar_shape(self) -> None:
        """TC-BE-CR106-1 (bẫy run-4 «filter bị nuốt câm»): vô hướng ``'A1'``."""
        self.assertEqual(_intersect_in("A1", _ASSIGNED), ["in", ["A1"]])

    def test_tc_be_cr106_2_in_list_shape(self) -> None:
        """TC-BE-CR106-2: ``['in', ['A1','A9']]`` ⇒ A9 (ngoài phạm vi) bị LOẠI."""
        self.assertEqual(_intersect_in(["in", ["A1", "A9"]], _ASSIGNED), ["in", ["A1"]])

    def test_tc_be_cr106_3_eq_shape(self) -> None:
        """TC-BE-CR106-3: ``['=', 'A2']``."""
        self.assertEqual(_intersect_in(["=", "A2"], _ASSIGNED), ["in", ["A2"]])

    def test_tc_be_cr106_4a_out_of_scope_is_empty_not_everything(self) -> None:
        """TC-BE-CR106-4 (chống leo phạm vi): 'A9' KHÔNG được giao ⇒ sentinel, KHÔNG assigned."""
        got = _intersect_in("A9", _ASSIGNED)
        self.assertEqual(got, ["in", [_SENTINEL]])
        self.assertNotEqual(
            got, ["in", _ASSIGNED],
            "GÁN thay vì GIAO: caller xin 1 thiết bị ngoài phạm vi mà nhận về TOÀN BỘ "
            "thiết bị được giao (leo phạm vi so với ý định caller + vỡ count == drill)",
        )

    def test_tc_be_cr106_5_no_caller_filter_is_byte_identical(self) -> None:
        """TC-BE-CR106-5 (0 hồi quy): khuyết/None/rỗng ⇒ y hệt hành vi cũ."""
        for existing in (None, "", "   "):
            with self.subTest(existing=existing):
                self.assertEqual(_intersect_in(existing, _ASSIGNED), ["in", _ASSIGNED])

    def test_plain_list_literal_is_treated_as_in_set(self) -> None:
        """List literal KHÔNG có op (``['A1','A2']``) = tập IN (mirror ``normalize_filters``)."""
        self.assertEqual(_intersect_in(["A1", "A2", "A9"], _ASSIGNED), ["in", ["A1", "A2"]])

    def test_tuple_in_shape_accepted(self) -> None:
        """Service layer nội bộ dùng tuple ``('in', [...])`` — cùng nghĩa với list."""
        self.assertEqual(_intersect_in(("in", ["A2"]), _ASSIGNED), ["in", ["A2"]])

    def test_negative_ops_subtract_from_assigned(self) -> None:
        """``not in`` / ``!=`` GIAO được: assigned ∖ {loại trừ}."""
        self.assertEqual(_intersect_in(["not in", ["A1"]], _ASSIGNED), ["in", ["A2"]])
        self.assertEqual(_intersect_in(["!=", "A2"], _ASSIGNED), ["in", ["A1"]])
        # Loại trừ hết ⇒ rỗng-an-toàn (KHÔNG fallback về assigned).
        self.assertEqual(
            _intersect_in(["not in", ["A1", "A2"]], _ASSIGNED), ["in", [_SENTINEL]]
        )

    def test_unintersectable_op_fails_closed(self) -> None:
        """Op không giao được tĩnh (``like``/``between``/so sánh) ⇒ FAIL-CLOSED.

        Chọn 0 dòng thay vì "toàn bộ thiết bị của tôi": phạm vi vendor là RANH GIỚI
        AN NINH, còn màn trống là lỗi hiển thị hữu hình (FE có empty-state có ngữ cảnh).
        """
        for existing in (["like", "%A%"], ["between", ["A1", "A2"]], [">", "A1"]):
            with self.subTest(existing=existing):
                self.assertEqual(_intersect_in(existing, _ASSIGNED), ["in", [_SENTINEL]])

    def test_output_shape_is_always_in_list(self) -> None:
        """INVARIANT shape ĐẦU RA: luôn ``['in', list]`` — hạ nguồn không phải đoán."""
        for existing in (None, "A1", ["in", ["A1"]], ["=", "A1"], ["A1"], ["like", "%x%"]):
            with self.subTest(existing=existing):
                got = _intersect_in(existing, _ASSIGNED)
                self.assertIsInstance(got, list)
                self.assertEqual(len(got), 2)
                self.assertEqual(got[0], "in")
                self.assertIsInstance(got[1], list)
                self.assertTrue(got[1], "IN-list RỖNG khiến Frappe match-all ⇒ rò dữ liệu")

    def test_tc_be_cr106_6_downstream_imm11_parity(self) -> None:
        """TC-BE-CR106-6 — hạ nguồn IMM-11 phân giải ĐÚNG tập từ shape đầu ra.

        Bảo vệ fix run-4 (``_extract_asset_in_scope`` nhận shape vô hướng) khỏi bị vô
        hiệu: cả 2 đường lịch/phiếu hiệu chuẩn đọc CÙNG shape mà ``_intersect_in`` phát.
        """
        from assetcore.services.imm11 import (  # noqa: PLC0415 - khuôn cục bộ
            _extract_asset_in_scope,
            _normalize_list_filters,
        )

        scoped = _intersect_in("A1", _ASSIGNED)
        # Đường list_calibration_schedules → _normalize_schedule_filters → helper này.
        self.assertEqual(
            _extract_asset_in_scope(scoped), ["A1"],
            "_extract_asset_in_scope nuốt shape ['in', [...]] ⇒ lọc thiết bị BIẾN MẤT "
            "câm và endpoint trả TOÀN BỘ lịch hiệu chuẩn (bug run-4 tái sinh)",
        )
        # Đường list_calibration_records → _normalize_list_filters: giữ VERBATIM.
        self.assertEqual(_normalize_list_filters({"asset": scoped}), {"asset": scoped})


class TestApplyVendorScopeIntersects(FrappeTestCase):
    """``apply_vendor_scope`` GIAO trên CẢ 6 doctype của field-map, cả 2 shape filters."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        if frappe.db.exists("User", _VENDOR_EMAIL):
            frappe.delete_doc("User", _VENDOR_EMAIL, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": _VENDOR_EMAIL, "first_name": "ACR106 Vendor",
            "send_welcome_email": 0, "enabled": 1,
        }).insert(ignore_permissions=True)
        u.add_roles("AssetCore System User", "Vendor Engineer")
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", _VENDOR_EMAIL):
            frappe.delete_doc("User", _VENDOR_EMAIL, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        frappe.set_user("Administrator")

    def _scoped(self, filters, doctype: str):
        """``apply_vendor_scope`` với tập được-giao CỐ ĐỊNH (patch resolver — 0 truy vấn WO).

        Patch ở CHÍNH module ``scope`` (nơi hàm được nhìn thấy) — không patch nơi khác.
        """
        with patch(
            "assetcore.services.shared.scope._resolve_vendor_assigned_assets",
            return_value=list(_ASSIGNED),
        ):
            return apply_vendor_scope(filters, doctype, user=_VENDOR_EMAIL)

    def test_tc_be_cr106_8_all_six_doctypes_intersect(self) -> None:
        """TC-BE-CR106-8 — parametrize 6 doctype: mỗi field-map đều GIAO, không GÁN."""
        self.assertEqual(
            len(_VENDOR_SCOPE_FIELD_MAP), 6,
            "field-map đổi số phần tử ⇒ TC parametrize rot âm thầm (cập nhật CÙNG vòng)",
        )
        for doctype, field in sorted(_VENDOR_SCOPE_FIELD_MAP.items()):
            with self.subTest(doctype=doctype, field=field):
                # trong phạm vi → giữ ĐÚNG cái caller xin
                self.assertEqual(
                    self._scoped({field: "A1"}, doctype)[field], ["in", ["A1"]],
                    f"{doctype}.{field}: caller xin A1 mà kết quả khác ⇒ GÁN chứ không GIAO",
                )
                # ngoài phạm vi → 0 dòng, KHÔNG "toàn bộ thiết bị của tôi"
                self.assertEqual(
                    self._scoped({field: "A9"}, doctype)[field], ["in", [_SENTINEL]],
                )
                # không có filter caller → y hệt hôm nay (0 hồi quy)
                self.assertEqual(
                    self._scoped({}, doctype)[field], ["in", _ASSIGNED],
                )

    def test_ac_asset_name_key_of_list_assets_is_not_clobbered(self) -> None:
        """``api/imm00.py:413`` — AC Asset map sang field ``name`` (khoá NHẠY: PK).

        ``list_assets`` build filters rồi gọi ``apply_vendor_scope(filters, "AC Asset")``;
        nếu caller đã có ``name`` (deep-link 1 thiết bị) thì GÁN sẽ xoá nó.
        """
        self.assertEqual(_VENDOR_SCOPE_FIELD_MAP["AC Asset"], "name")
        out = self._scoped({"lifecycle_status": "Active", "name": "A2"}, "AC Asset")
        self.assertEqual(out["name"], ["in", ["A2"]])
        self.assertEqual(out["lifecycle_status"], "Active", "filter cột khác không được đụng")

    def test_caller_dict_is_not_mutated(self) -> None:
        """Hàm trả bản COPY — caller (api/imm00 dùng lại ``filters``) không bị đổi ngầm."""
        src = {"asset_ref": "A1"}
        out = self._scoped(src, "PM Work Order")
        self.assertEqual(src, {"asset_ref": "A1"})
        self.assertIsNot(out, src)

    def test_tc_be_cr106_7_list_form_ands_scope_condition(self) -> None:
        """TC-BE-CR106-7 (nhánh list filters) — semantics ĐÃ RATIFY §10.4 (cuối bảng).

        BA **đính chính** cách đọc của acceptance A7: hai điều kiện CÙNG field trong
        filter-list form được Frappe ANDed trong SQL, và ``field = 'A9' AND field IN
        ('A1','A2')`` **chính là** phép giao (⇒ 0 dòng) — KHÔNG phải "2 điều kiện xung
        đột". Tiền lệ đã verify: ``services/imm00.py::compose_reserved_into`` ghép
        ``name in assigned`` AND ``name not in reserved``. Vì vậy nhánh này **GIỮ NGUYÊN**
        cách ghép (0 hồi quy) và assert ở đây khoá đúng điều đó.
        """
        out = self._scoped([["Asset Repair", "asset_ref", "=", "A9"]], "Asset Repair")
        self.assertIsInstance(out, list)
        self.assertEqual(
            out,
            [["Asset Repair", "asset_ref", "=", "A9"],
             ["Asset Repair", "asset_ref", "in", _ASSIGNED]],
            "nhánh list-form phải GIỮ điều kiện caller và THÊM điều kiện scope (AND = "
            "giao); mất một trong hai vế = rò dữ liệu hoặc mất bộ lọc",
        )

    def test_list_form_keeps_other_columns(self) -> None:
        """Cột khác giữ nguyên thứ tự; scope thêm ĐÚNG 1 điều kiện."""
        src = [["Asset Repair", "status", "=", "Open"]]
        out = self._scoped(src, "Asset Repair")
        self.assertEqual(out[0], ["Asset Repair", "status", "=", "Open"])
        self.assertEqual(out[-1], ["Asset Repair", "asset_ref", "in", _ASSIGNED])
        self.assertEqual(len(out), 2)
        self.assertEqual(src, [["Asset Repair", "status", "=", "Open"]],
                         "list caller bị mutate tại chỗ (phải trả bản COPY)")

    def test_ac_cr_109_list_branch_unreachable_from_all_five_call_sites(self) -> None:
        """Điều kiện HOÃN ``AC-CR-109`` (§10.4 ghi chú ⚠️) — nhánh list-form **chưa** tới
        được từ 5 call site prod, nên bug nhãn-alias (``Calibration Schedule`` KHÔNG phải
        DocType thật) chưa thể phát tác.

        Nếu một vòng sau có call site truyền **list** vào ``apply_vendor_scope`` thì test
        này ĐỎ ⇒ buộc land map alias→DocType thật TRƯỚC khi nhánh đó sống. Không có nó,
        điều kiện hoãn là lời nói (không đỏ được).
        """
        import ast  # noqa: PLC0415 - khuôn cục bộ
        import inspect  # noqa: PLC0415
        import pathlib as _p  # noqa: PLC0415

        from assetcore.api import imm00, imm08, imm09, imm11  # noqa: PLC0415

        call_sites = 0
        for mod in (imm00, imm08, imm09, imm11):
            src = _p.Path(inspect.getsourcefile(mod)).read_text(encoding="utf-8")
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and ast.unparse(node.func).endswith("apply_vendor_scope")):
                    continue
                call_sites += 1
                first = ast.unparse(node.args[0]) if node.args else ""
                # Mọi call site truyền tên biến đã đi qua `parse_json(...)` (dict) —
                # KHÔNG literal list, KHÔNG biến dựng bằng list-comprehension.
                self.assertFalse(
                    first.startswith("["),
                    f"{mod.__name__}: apply_vendor_scope nhận LIST literal ⇒ nhánh "
                    f"list-form SỐNG ⇒ phải land AC-CR-109 (map alias→DocType thật) "
                    f"trong CÙNG vòng: {first[:60]}",
                )
        self.assertEqual(
            call_sites, 5,
            f"Số call site `apply_vendor_scope` đổi ({call_sites} ≠ 5) ⇒ bảng §10.4/§10.1 "
            f"RC-10.2 rot: cập nhật doc + test trong CÙNG vòng",
        )

    def test_non_vendor_and_bypass_roles_still_passthrough(self) -> None:
        """0 hồi quy trên nhánh KHÔNG phải vendor: filters trả về NGUYÊN VẸN."""
        f = {"asset_ref": "A9"}
        self.assertEqual(apply_vendor_scope(f, "PM Work Order", user="Administrator"), f)
        self.assertEqual(apply_vendor_scope(f, "Some Random Doctype", user=_VENDOR_EMAIL), f)


class TestCountWithOrListFormRowScope(FrappeTestCase):
    """TC-VSCOPE-16 — ``count_with_or`` áp row-scope cho CẢ filters dạng **LIST**.

    Docstring của ``count_with_or`` (``services/shared/filters.py:236-247``) KHẲNG ĐỊNH
    nó nhận list-form ``[[doctype, field, op, val], …]`` và vẫn là MỘT predicate với
    ``frappe.get_list``. Trước vòng này lời khẳng định đó **không có test nào** — mọi TC
    count==rows đều dùng dict. Nhánh list-form là nhánh SỐNG duy nhất trên prod
    (``imm04.list_commissioning`` với ``overdue=1``, ``imm04.py:1100-1105``), nên nếu
    ``get_list`` xử lý list-form khác dict (vd bỏ điều kiện trùng cột) thì header "Tổng N"
    lại nói dối mà không ai biết.

    Chứng minh ở đây, dữ liệu THẬT, 2 persona:
      * row-scoped (``Vendor Engineer`` + ``Commissioning User``) ⇒ ``count_with_or`` ==
        ``len(get_list(cùng filters))`` và **NHỎ HƠN** engine thô (row-scope có tác dụng);
      * ``AssetCore Super Admin`` (senior ⇒ ``asset_commissioning_query`` trả ``""``) ⇒
        ``count_with_or`` == engine thô (không siết oan).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        sfx = frappe.generate_hash(length=6)
        cls.sfx = sfx
        cls.cat_name = f"_VScope16 Category {sfx}"
        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": cls.cat_name,
            "default_pm_interval_days": 90,
        }).insert(ignore_permissions=True).name

        cls.vendor = cls._user(f"vscope16_vendor_{sfx}@example.invalid", "VScope NCC",
                               "AssetCore System User", "Commissioning User",
                               "Vendor Engineer")
        cls.admin = cls._user(f"vscope16_admin_{sfx}@example.invalid", "VScope QTV",
                              "AssetCore System User", "AssetCore Super Admin")
        cls.users = [cls.vendor, cls.admin]

        prev = frappe.flags.in_install
        frappe.flags.in_install = "frappe"
        try:
            cls.asset = frappe.get_doc({
                "doctype": "AC Asset",
                "asset_name": f"_VScope16 Asset {sfx}",
                "asset_category": cls.cat,
                "manufacturer_sn": f"VS16-SN-{sfx}",
                "lifecycle_status": "Active",
            }).insert(ignore_permissions=True).name
        finally:
            frappe.flags.in_install = prev

        # 2 phiếu của vendor + 1 của Administrator ⇒ row-scope phải cắt còn 2.
        cls.mine = [cls._comm(owner=cls.vendor), cls._comm(owner=cls.vendor)]
        cls.foreign = cls._comm(owner="Administrator")
        cls.comms = [*cls.mine, cls.foreign]

        # Shape MIRROR nhánh prod: `final_asset` + `docstatus` + **hai** ràng buộc trên
        # CÙNG cột `workflow_state` (chính lý do tồn tại của list-form: dict sẽ clobber).
        cls.LIST_FILTERS = [
            [_COMM_DT, "final_asset", "=", cls.asset],
            [_COMM_DT, "docstatus", "!=", 2],
            [_COMM_DT, "workflow_state", "not in", ["Clinical Release", "Return To Vendor"]],
            [_COMM_DT, "workflow_state", "!=", "Draft"],
        ]
        frappe.db.commit()

    @classmethod
    def _user(cls, email: str, first_name: str, *roles: str) -> str:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": email, "first_name": first_name,
            "send_welcome_email": 0, "enabled": 1,
        }).insert(ignore_permissions=True)
        u.add_roles(*roles)
        return u.name

    @classmethod
    def _comm(cls, *, owner: str) -> str:
        frappe.set_user(owner)
        try:
            doc = frappe.get_doc({
                "doctype": _COMM_DT, "workflow_state": "Draft",
            }).insert(ignore_permissions=True, ignore_mandatory=True, ignore_links=True)
        finally:
            frappe.set_user("Administrator")
        doc.db_set("workflow_state", "To Be Installed", update_modified=False)
        doc.db_set("final_asset", cls.asset, update_modified=False)
        return doc.name

    @classmethod
    def tearDownClass(cls):
        from assetcore.tests._helpers._asset_cleanup import (  # noqa: PLC0415
            purge_asset, purge_category_by_name)

        frappe.set_user("Administrator")
        for name in getattr(cls, "comms", []):
            if frappe.db.exists(_COMM_DT, name):
                frappe.delete_doc(_COMM_DT, name, force=True, ignore_permissions=True)
        purge_asset(getattr(cls, "asset", None))
        purge_category_by_name(getattr(cls, "cat_name", ""))
        for email in getattr(cls, "users", []):
            if frappe.db.exists("User", email):
                frappe.delete_doc("User", email, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        frappe.set_user("Administrator")

    def _as(self, user: str, fn):
        frappe.set_user(user)
        try:
            return fn()
        finally:
            frappe.set_user("Administrator")

    def test_tc_vscope_16_count_with_or_list_form_applies_row_scope(self) -> None:
        """TC-VSCOPE-16 — count == rows trên filters LIST-FORM, cho CẢ 2 persona."""
        from assetcore.services.shared.filters import (  # noqa: PLC0415
            count_ignore_permissions, count_with_or)

        f = self.LIST_FILTERS

        # Engine THÔ (get_all — bỏ permission_query_conditions) = oracle "tổng bảng".
        raw = count_ignore_permissions(_COMM_DT, f, None)
        self.assertEqual(
            raw, 3,
            f"fixture rot: engine thô phải thấy 3 phiếu của thiết bị này, thấy {raw} "
            f"⇒ mọi so sánh dưới đây thành vacuous",
        )

        # ── persona ROW-SCOPED ────────────────────────────────────────────────
        vendor_count = self._as(self.vendor, lambda: count_with_or(_COMM_DT, f, None))
        vendor_rows = self._as(self.vendor, lambda: [
            r["name"] for r in frappe.get_list(
                _COMM_DT, filters=f, fields=["name"], limit_page_length=0)
        ])
        self.assertEqual(
            vendor_count, len(vendor_rows),
            f"count_with_or={vendor_count} != len(get_list)={len(vendor_rows)} trên "
            f"filters DẠNG LIST ⇒ docstring filters.py:236-247 SAI cho dạng list: đường "
            f"đếm và đường đọc không còn cùng predicate (header 'Tổng N' nói dối)",
        )
        self.assertEqual(
            set(vendor_rows), set(self.mine),
            "row-scope phải cắt đúng 2 phiếu do vendor sở hữu (owner) — "
            "`asset_commissioning_query`, hooks.py:444",
        )
        self.assertLess(
            vendor_count, raw,
            f"count_with_or({vendor_count}) == engine thô({raw}) cho persona row-scoped "
            f"⇒ `permission_query_conditions` KHÔNG được áp trên nhánh list-form "
            f"(đây chính là §1: 'Tổng 3' mà drill được 2)",
        )

        # ── persona READ-ALL (senior) ────────────────────────────────────────
        admin_count = self._as(self.admin, lambda: count_with_or(_COMM_DT, f, None))
        admin_rows = self._as(self.admin, lambda: frappe.get_list(
            _COMM_DT, filters=f, fields=["name"], limit_page_length=0))
        self.assertEqual(admin_count, len(admin_rows))
        self.assertEqual(
            admin_count, raw,
            f"AssetCore Super Admin là senior (`asset_commissioning_query` trả '') nên "
            f"count_with_or phải == tổng bảng cho filters đó ({raw}), nhận {admin_count} "
            f"⇒ đang siết OAN persona read-all trên nhánh list-form",
        )

    def test_tc_vscope_16b_list_form_conditions_are_not_dropped(self) -> None:
        """Điều kiện trong list-form phải THỰC SỰ áp — không bị nuốt câm.

        Nếu ``get_list`` bỏ qua list-form (vd shape sai bị ``except`` nuốt) thì count sẽ
        là tổng-bảng-không-lọc và **cả** hai assert của TC trên vẫn có thể xanh cùng-sai.
        Bơm 1 điều kiện KHÔNG THỂ khớp ⇒ đòi 0.
        """
        from assetcore.services.shared.filters import count_with_or  # noqa: PLC0415

        impossible = [*self.LIST_FILTERS,
                      [_COMM_DT, "workflow_state", "=", f"__nope_{self.sfx}__"]]
        for user in (self.vendor, self.admin):
            with self.subTest(user=user):
                self.assertEqual(
                    self._as(user, lambda: count_with_or(_COMM_DT, impossible, None)), 0,
                    "điều kiện list-form bị NUỐT: count vẫn > 0 với ràng buộc không thể "
                    "khớp ⇒ mọi con số count_with_or trên nhánh này vô nghĩa",
                )


if __name__ == "__main__":
    unittest.main()
