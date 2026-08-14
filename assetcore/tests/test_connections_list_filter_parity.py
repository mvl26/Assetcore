# Copyright (c) 2026, AssetCore Team
"""TC-BE-CONN-14/15 — hợp đồng «FE gửi ``?asset=`` thì BE PHẢI lọc» (AC-CR-95).

Bối cảnh (AC-CR-91 → AC-CR-94 → AC-CR-95): nút «Xem tất cả» trong tab «Bản ghi liên
quan» deep-link sang màn danh sách đích kèm bộ lọc theo thiết bị cha. Deep-link chỉ có
giá trị khi **CẢ HAI ĐẦU** cùng làm việc:

  * đầu FE — màn đích đọc ``route.query.asset`` rồi dịch sang khoá BE
    (``frontend/src/api/connections.ts`` ``DOCTYPE_LIST_TARGET`` + view tương ứng);
  * đầu BE — endpoint/list-service THẬT SỰ nhận khoá đó và biến nó thành điều kiện WHERE.

Vòng AC-CR-95 thăng hạng 4 doctype khỏi ``LIST_TARGET_NO_FILTER``:

  | DocType                 | màn FE          | khoá FE gửi | khoá BE lọc thật |
  |-------------------------|-----------------|-------------|------------------|
  | Asset Commissioning     | /commissioning  | ``asset``   | ``final_asset``  |
  | Asset Decommission      | /decommissions  | ``asset``   | ``asset``        |
  | IMM CAPA Record         | /capas          | ``asset``   | ``asset``        |
  | Firmware Change Request | /cm/firmware    | ``asset``   | ``asset_ref``    |

Đây là guard **TĨNH** (introspect signature / hằng whitelist / AST / schema JSON) — KHÔNG
fixture, KHÔNG ghi DB, KHÔNG phụ thuộc dữ liệu site. Nó đóng đúng một lớp bug: ai đó gỡ
tham số ``asset`` khỏi endpoint, gỡ khoá khỏi whitelist ``filters``, hoặc đổi tên Link
field ⇒ BE lặng lẽ **bỏ qua** bộ lọc và trả danh sách **TOÀN VIỆN** trên màn mà người
dùng vừa bấm từ một thiết bị cụ thể (không lỗi, không cảnh báo — đúng lớp bug
"Tổng 1430 / bảng của tôi" mà ``ADR-IMM00-LIST-SCOPE §4b`` gọi tên).

Mỗi assert kèm message chỉ RÕ màn FE sẽ vỡ, để người phá guard biết ngay hệ quả.

Vế FE của cùng hợp đồng do ``frontend/src/guards/connectionsListParity.guard.test.ts`` giữ
(phân hoạch ``DOCTYPE_LIST_TARGET`` ∪ ``LIST_TARGET_NO_FILTER`` == ``DOCTYPE_ROUTE``,
allowlist CHỈ-GIẢM + ``sourceKeys`` là Link → AC Asset thật).

Spec: ``docs/imm-00/05_API_Specification.md §III.24`` · ADR
``docs/imm-00/ADR-IMM00-CONNECTIONS-TREE.md`` (D-CR5-4..7 / INV-CONN-18..22) ·
``docs/imm-00/07_Testing_QA.md §XVIII``.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_connections_list_filter_parity
"""
from __future__ import annotations

import ast
import inspect
import json
import os
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

import assetcore.api.imm00 as api_imm00
import assetcore.services.imm04 as svc_imm04
import assetcore.services.imm14 as svc_imm14
from assetcore.services.connections import deep_link_keys

#: Bảng thăng hạng AC-CR-95 — (DocType, khoá neo BE, slug JSON, màn FE vỡ nếu guard đỏ).
#:
#: "khoá neo BE" = fieldname Link → AC Asset mà đồ thị liên quan phát ra trong
#: ``deep_link_filters`` VÀ là khoá FE khai ở ``DOCTYPE_LIST_TARGET.sourceKeys``.
_PROMOTED: tuple[tuple[str, str, str, str], ...] = (
    ("Asset Commissioning", "final_asset", "asset_commissioning", "/commissioning"),
    ("Asset Decommission", "asset", "asset_decommission", "/decommissions"),
    ("IMM CAPA Record", "asset", "imm_capa_record", "/capas"),
    ("Firmware Change Request", "asset_ref", "firmware_change_request", "/cm/firmware"),
)

#: ``apps/assetcore/assetcore/assetcore/doctype`` — module app LỒNG một cấp, nên KHÔNG
#: suy từ ``__file__`` của package ``tests`` (sai một cấp); dùng helper canonical.
_DOCTYPE_DIR = frappe.get_app_path("assetcore", "assetcore", "doctype")

_ANCHOR_DOCTYPE = "AC Asset"


# ─────────────────────────────────────────────────────────────────────────────
# Predicate THUẦN — tách khỏi assert để chứng minh guard SỐNG (mutation test bên
# dưới nạp đầu vào đã-đột-biến mà KHÔNG cần sửa một dòng file prod nào).
# ─────────────────────────────────────────────────────────────────────────────
def _accepts_param(fn, param: str) -> bool:
    """Hàm ``fn`` có nhận tham số tên ``param``?"""
    return param in inspect.signature(fn).parameters


def _contains_key(container, key: str) -> bool:
    """Khoá ``key`` có nằm trong tập/whitelist ``container``?"""
    return key in container


def _anchor_in_deep_link_keys(anchor: str, keyset) -> bool:
    """Khoá neo FE khai có thuộc tập khoá deep-link BE phát ra?"""
    return anchor in keyset


def _link_fields_to(doctype_json: dict, target: str) -> set[str]:
    """Tập fieldname Link trỏ tới ``target`` trong schema DocType (đọc từ đĩa)."""
    return {
        f["fieldname"]
        for f in doctype_json.get("fields") or []
        if f.get("fieldtype") == "Link" and f.get("options") == target
    }


def _fn_ast(module, fn_name: str) -> ast.FunctionDef:
    """AST của một hàm trong module (đọc source THẬT trên đĩa, không suy đoán)."""
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            return node
    raise AssertionError(f"Không tìm thấy hàm '{fn_name}' trong {module.__name__}")


def _maps_param_to_filter_key(module, fn_name: str, param: str, filter_key: str) -> bool:
    """Trong ``fn_name`` có phép gán ``<dict>["<filter_key>"] = <param>``?

    Đây là bước DỊCH khoá mà FE phụ thuộc: FE gửi ``?asset=`` nhưng cột DB tên khác
    (``asset_ref``). Mất dòng gán này ⇒ tham số vào nhưng KHÔNG thành điều kiện WHERE.
    """
    for node in ast.walk(_fn_ast(module, fn_name)):
        if not isinstance(node, ast.Assign):
            continue
        if not (
            isinstance(node.value, ast.Name) and node.value.id == param
        ):
            continue
        for tgt in node.targets:
            if (
                isinstance(tgt, ast.Subscript)
                and isinstance(tgt.slice, ast.Constant)
                and tgt.slice.value == filter_key
            ):
                return True
    return False


def _has_condition_on_field(module, fn_name: str, field: str, param: str) -> bool:
    """Trong ``fn_name`` có literal điều kiện list mang cả ``"<field>"`` và biến ``param``?

    Khớp dạng list-of-conditions của Frappe: ``[_DT, "asset", "=", asset]``.
    """
    for node in ast.walk(_fn_ast(module, fn_name)):
        if not isinstance(node, ast.List):
            continue
        has_field = any(
            isinstance(e, ast.Constant) and e.value == field for e in node.elts
        )
        has_param = any(isinstance(e, ast.Name) and e.id == param for e in node.elts)
        if has_field and has_param:
            return True
    return False


def _consumes_constant(module, fn_name: str, const_name: str) -> bool:
    """Hằng whitelist có được ĐỌC trong hàm (chống hằng chết = whitelist trang trí)?"""
    return any(
        isinstance(n, ast.Name) and n.id == const_name
        for n in ast.walk(_fn_ast(module, fn_name))
    )


class TestConnectionsListFilterParity(FrappeTestCase):
    """Guard tĩnh: 4 màn đích của «Xem tất cả» thật sự lọc được theo thiết bị."""

    # ── TC-BE-CONN-14 — BE nhận khoá asset (BE-1) ────────────────────────────
    def test_tc_be_conn_14a_list_capas_accepts_asset(self) -> None:
        """``api.imm00.list_capas`` còn tham số ``asset``."""
        self.assertTrue(
            _accepts_param(api_imm00.list_capas, "asset"),
            "MÀN FE VỠ: /capas — «Xem tất cả» (IMM CAPA Record) deep-link "
            "?asset=<mã> nhưng list_capas không còn nhận tham số 'asset' ⇒ danh "
            "sách CAPA trả TOÀN VIỆN thay vì của đúng thiết bị (câm, không lỗi). "
            "Khôi phục tham số hoặc hạ IMM CAPA Record về LIST_TARGET_NO_FILTER "
            "(frontend/src/api/connections.ts) trong CÙNG commit.",
        )

    def test_tc_be_conn_14b_list_firmware_crs_accepts_asset(self) -> None:
        """``api.imm00.list_firmware_crs`` còn tham số ``asset``."""
        self.assertTrue(
            _accepts_param(api_imm00.list_firmware_crs, "asset"),
            "MÀN FE VỠ: /cm/firmware — «Xem tất cả» (Firmware Change Request) "
            "deep-link ?asset=<mã> nhưng list_firmware_crs không còn nhận tham số "
            "'asset' ⇒ danh sách yêu cầu đổi firmware trả TOÀN VIỆN. Khôi phục tham "
            "số hoặc hạ doctype về LIST_TARGET_NO_FILTER trong CÙNG commit.",
        )

    def test_tc_be_conn_14c_decom_filter_keys_contains_asset(self) -> None:
        """``services.imm14._DECOM_FILTER_KEYS`` còn khoá ``asset``."""
        self.assertTrue(
            _contains_key(svc_imm14._DECOM_FILTER_KEYS, "asset"),
            "MÀN FE VỠ: /decommissions — «Xem tất cả» (Asset Decommission) gửi "
            "filters={'asset': <mã>} nhưng 'asset' đã rơi khỏi whitelist "
            "_DECOM_FILTER_KEYS ⇒ _normalize_decom_filters LOẠI khoá này (whitelist "
            "im lặng) và trả danh sách giải nhiệm TOÀN VIỆN. "
            f"Whitelist hiện tại: {tuple(svc_imm14._DECOM_FILTER_KEYS)!r}.",
        )

    def test_tc_be_conn_14d_commissioning_allows_final_asset(self) -> None:
        """``services.imm04._ALLOWED_FILTER_KEYS`` còn khoá ``final_asset``."""
        self.assertTrue(
            _contains_key(svc_imm04._ALLOWED_FILTER_KEYS, "final_asset"),
            "MÀN FE VỠ: /commissioning — «Xem tất cả» (Asset Commissioning) dịch "
            "?asset=<mã> sang filters={'final_asset': <mã>} nhưng 'final_asset' đã "
            "rơi khỏi _ALLOWED_FILTER_KEYS ⇒ list_commissioning LOẠI khoá này và trả "
            "hồ sơ nghiệm thu TOÀN VIỆN.",
        )

    # ── TC-BE-CONN-14 (bis) — tham số/whitelist phải BIẾN THÀNH điều kiện ────
    def test_tc_be_conn_14e_list_firmware_crs_maps_asset_to_asset_ref(self) -> None:
        """``asset`` được DỊCH sang cột ``asset_ref`` (không chỉ nằm trong signature)."""
        self.assertTrue(
            _maps_param_to_filter_key(
                api_imm00, "list_firmware_crs", "asset", "asset_ref"
            ),
            "MÀN FE VỠ: /cm/firmware — list_firmware_crs vẫn nhận 'asset' nhưng KHÔNG "
            "còn phép gán f['asset_ref'] = asset ⇒ tham số bị NUỐT: HTTP 200, danh "
            "sách TOÀN VIỆN. Có-mặt-tham-số ≠ có-lọc; cột thật của Firmware Change "
            "Request là 'asset_ref' (Link → AC Asset).",
        )

    def test_tc_be_conn_14f_list_capas_conditions_on_asset_field(self) -> None:
        """``list_capas`` build điều kiện list ``[_DT_CAPA, "asset", "=", asset]``."""
        self.assertTrue(
            _has_condition_on_field(api_imm00, "list_capas", "asset", "asset"),
            "MÀN FE VỠ: /capas — list_capas nhận 'asset' nhưng không còn append điều "
            "kiện trên cột 'asset' ⇒ tham số bị nuốt, trả toàn bộ CAPA. Giữ dạng "
            "list-of-conditions (BR-00-16 conjoin) để 'asset' AND với status/overdue.",
        )

    def test_tc_be_conn_14g_filter_whitelists_are_consumed(self) -> None:
        """Hai hằng whitelist được ĐỌC trong hàm list (không phải hằng chết)."""
        self.assertTrue(
            _consumes_constant(svc_imm14, "_normalize_decom_filters", "_DECOM_FILTER_KEYS"),
            "MÀN FE VỠ: /decommissions — _DECOM_FILTER_KEYS thành hằng CHẾT: "
            "_normalize_decom_filters không còn đọc nó ⇒ whitelist chỉ còn trang trí "
            "(khoá 'asset' có thể bị loại hoặc mọi khoá lạ lọt qua).",
        )
        self.assertTrue(
            _consumes_constant(svc_imm04, "list_commissioning", "_ALLOWED_FILTER_KEYS"),
            "MÀN FE VỠ: /commissioning — _ALLOWED_FILTER_KEYS thành hằng CHẾT: "
            "list_commissioning không còn đọc nó ⇒ 'final_asset' không được lọc "
            "(hoặc khoá tuỳ ý lọt xuống SQL).",
        )

    # ── TC-BE-CONN-15 — khoá neo có THẬT trong đồ thị + trong schema (BE-2) ──
    def test_tc_be_conn_15a_anchor_key_in_deep_link_keys(self) -> None:
        """Khoá FE khai ở ``sourceKeys`` phải nằm trong ``deep_link_keys(doctype)``.

        Chống ca "nút hiện nhưng ``listTarget()`` luôn ``null``": FE chỉ dịch được
        ``deep_link_filters`` → ``?asset=`` khi BE THỰC SỰ phát ra khoá neo đó.
        """
        for doctype, anchor, _slug, route in _PROMOTED:
            with self.subTest(doctype=doctype):
                keys = deep_link_keys(doctype)
                self.assertTrue(
                    _anchor_in_deep_link_keys(anchor, keys),
                    f"MÀN FE VỠ: {route} — FE khai sourceKeys=['{anchor}'] cho "
                    f"'{doctype}' nhưng deep_link_keys('{doctype}') = "
                    f"{sorted(keys)!r} KHÔNG chứa khoá đó ⇒ get_connections không bao "
                    f"giờ phát khoá neo, listTarget() luôn null, nút «Xem tất cả» biến "
                    f"mất (state chết). Sửa non_standard_fieldnames trong "
                    f"ac_asset_dashboard.py HOẶC sửa sourceKeys ở "
                    f"frontend/src/api/connections.ts — CÙNG commit.",
                )

    def test_tc_be_conn_15b_anchor_key_is_real_link_to_ac_asset(self) -> None:
        """Khoá neo là Link → AC Asset THẬT trong schema DocType (đọc JSON trên đĩa).

        Song song với guard FE ``connectionsListParity.guard.test.ts`` — đổi tên Link field
        mà quên hai bảng dịch ⇒ deep-link trỏ vào cột không tồn tại.
        """
        for doctype, anchor, slug, route in _PROMOTED:
            with self.subTest(doctype=doctype):
                path = os.path.join(_DOCTYPE_DIR, slug, f"{slug}.json")
                self.assertTrue(os.path.isfile(path), f"Thiếu schema: {path}")
                with open(path, encoding="utf-8") as fh:
                    schema = json.load(fh)
                self.assertEqual(
                    schema.get("name"),
                    doctype,
                    f"Slug '{slug}' không phải schema của '{doctype}'.",
                )
                links = _link_fields_to(schema, _ANCHOR_DOCTYPE)
                self.assertIn(
                    anchor,
                    links,
                    f"MÀN FE VỠ: {route} — '{anchor}' KHÔNG phải Link → "
                    f"{_ANCHOR_DOCTYPE} trong {slug}.json (Link thật: "
                    f"{sorted(links)!r}) ⇒ lọc theo khoá này sinh SQL sai cột hoặc "
                    f"danh sách RỖNG vĩnh viễn.",
                )

    def test_tc_be_conn_15c_anchor_keys_cover_all_four_promoted(self) -> None:
        """Bảng ``_PROMOTED`` phủ ĐÚNG 4 doctype AC-CR-95 (chống co bảng cho dễ xanh)."""
        self.assertEqual(
            {row[0] for row in _PROMOTED},
            {
                "Asset Commissioning",
                "Asset Decommission",
                "IMM CAPA Record",
                "Firmware Change Request",
            },
            "AC-CR-95 thăng hạng ĐÚNG 4 doctype; bảng _PROMOTED bị sửa ⇒ guard mất "
            "răng. Doctype rời DOCTYPE_LIST_TARGET (FE) thì XOÁ khỏi đây trong CÙNG "
            "commit, kèm lý do — allowlist FE là CHỈ-GIẢM.",
        )

    # ── Mutation self-check — chứng minh guard SỐNG, không phải template xanh ─
    def test_tc_be_conn_15d_guard_predicates_detect_mutation(self) -> None:
        """Mọi predicate ở trên PHẢI báo sai khi nạp đầu vào đã đột biến.

        Chạy mutation ngay trong test (mock/đầu vào giả) — KHÔNG sửa file prod, nên
        vòng này giữ nguyên kỷ luật "0 thay đổi .py nghiệp vụ" mà vẫn có bằng chứng
        guard không phải assert hằng-đúng.
        """
        # 1. signature thiếu tham số
        def _no_asset(page: int = 1, page_size: int = 20):  # pragma: no cover
            return None

        self.assertFalse(_accepts_param(_no_asset, "asset"))
        self.assertTrue(_accepts_param(api_imm00.list_capas, "asset"))

        # 2. whitelist bị co lại (patch hằng — không đụng đĩa)
        with mock.patch.object(
            svc_imm14, "_DECOM_FILTER_KEYS", ("workflow_state", "disposal_method")
        ):
            self.assertFalse(_contains_key(svc_imm14._DECOM_FILTER_KEYS, "asset"))
        self.assertTrue(_contains_key(svc_imm14._DECOM_FILTER_KEYS, "asset"))

        with mock.patch.object(
            svc_imm04, "_ALLOWED_FILTER_KEYS", frozenset({"workflow_state"})
        ):
            self.assertFalse(
                _contains_key(svc_imm04._ALLOWED_FILTER_KEYS, "final_asset")
            )
        self.assertTrue(_contains_key(svc_imm04._ALLOWED_FILTER_KEYS, "final_asset"))

        # 3. khoá neo ngoại lai (ca A3: ô đến từ hub KHÁC)
        self.assertFalse(
            _anchor_in_deep_link_keys("asset_repair_wo", frozenset({"asset_ref", "name"}))
        )

        # 4. schema không có Link tới AC Asset dưới tên bị đổi
        self.assertEqual(
            _link_fields_to(
                {
                    "fields": [
                        {"fieldname": "vendor", "fieldtype": "Link", "options": "AC Supplier"},
                        {"fieldname": "final_asset", "fieldtype": "Data"},
                    ]
                },
                _ANCHOR_DOCTYPE,
            ),
            set(),
        )

        # 5. AST: hàm nhận tham số nhưng KHÔNG dịch sang khoá lọc ⇒ predicate False
        self.assertFalse(
            _maps_param_to_filter_key(api_imm00, "list_capas", "asset", "asset_ref"),
            "list_capas lọc bằng list-of-conditions, không phải f['asset_ref'] — "
            "predicate _maps_param_to_filter_key phải trả False ở đây, nếu True thì "
            "nó đang khớp quá rộng (guard giả).",
        )
