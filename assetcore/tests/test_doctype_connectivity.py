# Copyright (c) 2026, AssetCore Team
"""STATIC guard — ĐỒ THỊ LIÊN KẾT (dashboard connections) của hub doctype.

BỐI CẢNH (SPEC_core_refinement_frappe_native §2): khảo sát 2026-07-22 cho thấy **0/110**
doctype AssetCore khai đồ thị liên kết ⇒ mở 1 tài sản KHÔNG thấy phiếu PM / sửa chữa /
hiệu chuẩn / sự cố / hồ sơ nào. Dữ liệu CÓ quan hệ trong DB, nhưng không nơi nào khai
báo quan hệ đó cho tầng hiển thị ⇒ cả Desk lẫn Vue đều phải code tay từng màn.

INVARIANT (SoT): mỗi doctype trong ``HUB_DOCTYPES`` PHẢI có
``<snake>_dashboard.py::get_data()`` (đúng tên hàm Frappe v15 —
``frappe/model/meta.py::get_dashboard_data`` nạp module suffix ``_dashboard`` rồi gọi
``get_data``), và MỌI doctype liệt kê trong ``transactions[].items`` PHẢI **phân giải
được về một field thật**:

  - **inbound** (mặc định): doctype đó có Link field tên
    ``non_standard_fieldnames[dt]`` (hoặc ``fieldname``) với ``options == hub``;
  - **outbound**: ``internal_links[dt]`` dạng chuỗi = tên Link field TRÊN CHÍNH hub, trỏ
    ``options == dt`` (frappe/desk/notifications.py::get_internal_links nhánh ``str``);
  - **qua child table**: ``internal_links[dt]`` dạng list ``[table_fieldname,
    link_fieldname]`` — hub có Table field ``table_fieldname``, doctype con của nó có Link
    field ``link_fieldname`` trỏ ``options == dt`` (nhánh ``list``).

VÌ SAO PHẢI LÀ STATIC GUARD: ``Meta.get_dashboard_data`` bọc ``load_doctype_module``
trong ``except ImportError: pass`` ⇒ file dashboard lỗi cú pháp/sai tên hàm **KHÔNG báo
lỗi**, chỉ âm thầm mất tab Connections. Tương tự, một item trỏ tới field không tồn tại
chỉ cho ra badge count 0 — trông y hệt "chưa có dữ liệu". Cả hai đều là lỗi CÂM, phải bắt
bằng test chứ không thể bắt bằng mắt.

Oracle ĐỘC LẬP, file-driven: đọc thẳng ``assetcore/assetcore/doctype/*/*.json`` +
import module dashboard TƯỜNG MINH (KHÔNG nuốt ImportError), KHÔNG query live DB.

TRẠNG THÁI HIỆN TẠI: ĐỎ có chủ đích (RED-first, T02 của PLAN_core_refinement_tasks.md).
Guard chuyển GREEN dần khi T04/T07/T09 khai đủ 12 dashboard. ``TestHubDeskAffordances``
(SC-7) cũng ĐỎ tới khi T21 bổ sung ``title_field``/``search_fields``/``in_global_search``.

Run:
  bench --site miyano run-tests --app assetcore \
      --module assetcore.tests.test_doctype_connectivity
"""
from __future__ import annotations

import copy
import importlib
import json
import os
import unittest

import frappe

# ---------------------------------------------------------------------------
# SSoT — 12 hub doctype đợt 1 (SPEC §3 P1). Thêm hub ⇒ sửa DUY NHẤT chỗ này.
# ---------------------------------------------------------------------------
HUB_DOCTYPES: list[str] = [
    "AC Asset",
    "PM Work Order",
    "Asset Repair",
    "IMM Asset Calibration",
    "Incident Report",
    "Asset Commissioning",
    "Asset Document",
    "Asset Transfer",
    "AC Supplier",
    "IMM Device Model",
    "AC Spare Part",
    "IMM CAPA Record",
]

_APP = "assetcore"


# ---------------------------------------------------------------------------
# Loaders (oracle độc lập — đọc file, KHÔNG chạm live DB)
# ---------------------------------------------------------------------------
def _snake(doctype: str) -> str:
    return doctype.lower().replace(" ", "_").replace("-", "_")


def _doctype_json_path(doctype: str) -> str:
    s = _snake(doctype)
    return frappe.get_app_path(_APP, _APP, "doctype", s, s + ".json")


_META_CACHE: dict[str, dict] = {}


def _doctype_json(doctype: str) -> dict | None:
    """Schema JSON của doctype trong app assetcore; None nếu không thuộc app này."""
    if doctype in _META_CACHE:
        return _META_CACHE[doctype] or None
    path = _doctype_json_path(doctype)
    data: dict = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    _META_CACHE[doctype] = data
    return data or None


def _doctype_exists(doctype: str) -> bool:
    """True nếu doctype tồn tại — JSON-first, fallback DB (doctype của app khác)."""
    if _doctype_json(doctype):
        return True
    return bool(frappe.db.exists("DocType", doctype))


def _fields(doctype: str) -> list[dict]:
    j = _doctype_json(doctype)
    if j:
        return j.get("fields", []) or []
    try:
        return [f.as_dict() for f in frappe.get_meta(doctype).fields]
    except Exception:
        return []


def _field(doctype: str, fieldname: str) -> dict | None:
    for f in _fields(doctype):
        if f.get("fieldname") == fieldname:
            return f
    return None


def _child_doctype_of(doctype: str, table_fieldname: str) -> str:
    f = _field(doctype, table_fieldname) or {}
    if f.get("fieldtype") in ("Table", "Table MultiSelect"):
        return f.get("options") or ""
    return ""


def _load_dashboard_data(hub: str) -> dict | None:
    """get_data() của ``<snake>_dashboard.py``; None nếu CHƯA có file.

    KHÔNG nuốt lỗi như ``Meta.get_dashboard_data``: file tồn tại mà lỗi import / thiếu
    ``get_data`` ⇒ ném lên để test ĐỎ đúng nguyên nhân, thay vì mất tab Connections câm.
    """
    s = _snake(hub)
    path = frappe.get_app_path(_APP, _APP, "doctype", s, s + "_dashboard.py")
    if not os.path.exists(path):
        return None
    module = importlib.import_module(f"{_APP}.{_APP}.doctype.{s}.{s}_dashboard")
    importlib.reload(module)
    if not hasattr(module, "get_data"):
        raise AssertionError(
            f"{s}_dashboard.py TỒN TẠI nhưng KHÔNG có hàm get_data() — Frappe "
            f"(frappe/model/meta.py) chỉ gọi đúng tên `get_data`, sai tên ⇒ mất tab "
            f"Connections KHÔNG BÁO LỖI."
        )
    return dict(module.get_data())


# ---------------------------------------------------------------------------
# Oracle + guard — dùng chung giữa static test và guard-bites
# ---------------------------------------------------------------------------
def _connectivity_violations(hub: str, data: dict) -> list[str]:
    """Danh sách vi phạm invariant đồ thị liên kết của 1 hub (rỗng = hợp lệ)."""
    problems: list[str] = []
    transactions = data.get("transactions") or []
    if not transactions:
        return [f"{hub}: get_data() không có nhóm `transactions` nào"]

    default_fieldname = data.get("fieldname")
    non_standard = data.get("non_standard_fieldnames") or {}
    internal = data.get("internal_links") or {}

    seen: dict[str, str] = {}
    for group in transactions:
        label = (group.get("label") or "").strip()
        items = group.get("items") or []
        if not label:
            problems.append(f"{hub}: có nhóm thiếu `label` (người dùng sẽ thấy tiêu đề rỗng)")
        if not items:
            problems.append(f"{hub}: nhóm '{label}' rỗng `items`")

        for dt in items:
            if dt in seen:
                problems.append(
                    f"{hub}: '{dt}' xuất hiện ở CẢ nhóm '{seen[dt]}' và '{label}' (trùng)"
                )
                continue
            seen[dt] = label

            if not _doctype_exists(dt):
                problems.append(f"{hub}/{label}: doctype '{dt}' KHÔNG tồn tại")
                continue

            link = internal.get(dt)
            if isinstance(link, str):
                # outbound — Link field trên CHÍNH hub
                f = _field(hub, link)
                if not f or f.get("fieldtype") != "Link" or f.get("options") != dt:
                    problems.append(
                        f"{hub}/{label}: internal_links['{dt}']='{link}' nhưng {hub} "
                        f"KHÔNG có Link field '{link}' trỏ '{dt}'"
                    )
            elif isinstance(link, (list, tuple)):
                # qua child table — [table_fieldname, link_fieldname]
                if len(link) != 2:
                    problems.append(
                        f"{hub}/{label}: internal_links['{dt}'] dạng list phải đúng 2 phần "
                        f"tử [table_fieldname, link_fieldname], đang là {link!r}"
                    )
                    continue
                table_fieldname, link_fieldname = link
                child = _child_doctype_of(hub, table_fieldname)
                if not child:
                    problems.append(
                        f"{hub}/{label}: '{table_fieldname}' không phải Table field của {hub}"
                    )
                    continue
                cf = _field(child, link_fieldname)
                if not cf or cf.get("fieldtype") != "Link" or cf.get("options") != dt:
                    problems.append(
                        f"{hub}/{label}: child '{child}' KHÔNG có Link field "
                        f"'{link_fieldname}' trỏ '{dt}'"
                    )
            else:
                # inbound — Link field trên doctype con trỏ NGƯỢC về hub
                fieldname = non_standard.get(dt, default_fieldname)
                if not fieldname:
                    problems.append(
                        f"{hub}/{label}: '{dt}' không có `fieldname` mặc định lẫn "
                        f"`non_standard_fieldnames` ⇒ Desk lọc bằng None, count luôn 0"
                    )
                    continue
                f = _field(dt, fieldname)
                if not f or f.get("fieldtype") != "Link" or f.get("options") != hub:
                    problems.append(
                        f"{hub}/{label}: '{dt}.{fieldname}' KHÔNG phải Link trỏ '{hub}' "
                        f"⇒ liên kết CÂM (badge 0, trông như 'chưa có dữ liệu')"
                    )
    return problems


def _assert_connectivity(hub: str, data: dict) -> None:
    """GUARD: raise AssertionError nếu đồ thị liên kết của hub không phân giải được."""
    problems = _connectivity_violations(hub, data)
    if problems:
        raise AssertionError(
            f"{len(problems)} vi phạm đồ thị liên kết:\n  - " + "\n  - ".join(problems)
        )


# ---------------------------------------------------------------------------
# TC-CONN-1 — mọi hub PHẢI có dashboard (RED tới khi T04/T07/T09 xong)
# ---------------------------------------------------------------------------
class TestHubDashboardsExist(unittest.TestCase):
    """12 hub doctype phải khai đồ thị liên kết trong ``<snake>_dashboard.py``."""

    def test_every_hub_declares_a_dashboard(self) -> None:
        missing = [hub for hub in HUB_DOCTYPES if _load_dashboard_data(hub) is None]
        self.assertEqual(
            missing,
            [],
            f"{len(missing)}/{len(HUB_DOCTYPES)} hub doctype CHƯA có "
            f"<snake>_dashboard.py::get_data() ⇒ mở record không thấy bản ghi liên quan "
            f"nào (cả Desk lẫn API /connections): {missing}",
        )


# ---------------------------------------------------------------------------
# TC-CONN-2 — đồ thị đã khai phải phân giải được về field THẬT
# ---------------------------------------------------------------------------
class TestHubConnectionGraphResolvable(unittest.TestCase):
    """Với hub ĐÃ có dashboard: mọi item phải phân giải về field thật (chống liên kết câm)."""

    def test_declared_graphs_resolve_to_real_fields(self) -> None:
        problems: list[str] = []
        checked = 0
        for hub in HUB_DOCTYPES:
            data = _load_dashboard_data(hub)
            if data is None:
                continue  # thiếu file → TC-CONN-1 lo, không báo trùng
            checked += 1
            problems.extend(_connectivity_violations(hub, data))
        self.assertEqual(
            problems,
            [],
            f"Đồ thị liên kết của {checked} hub đã khai có vi phạm:\n  - "
            + "\n  - ".join(problems),
        )


# ---------------------------------------------------------------------------
# TC-CONN-3 — guard-bites (RED-proof: chứng minh guard THẬT cắn)
# ---------------------------------------------------------------------------
class TestConnectivityGuardBites(unittest.TestCase):
    """Bơm 3 loại lỗi CÂM vào bản in-memory ⇒ guard phải raise từng loại."""

    _VALID = {
        "fieldname": "asset",
        "transactions": [{"label": "Vòng đời", "items": ["Asset Lifecycle Event"]}],
    }

    def test_valid_graph_does_not_raise(self) -> None:
        # Sanity: đồ thị hợp lệ KHÔNG raise ⇒ mọi RED dưới đây là do MUTATION.
        _assert_connectivity("AC Asset", copy.deepcopy(self._VALID))

    def test_guard_bites_on_nonexistent_doctype(self) -> None:
        bad = copy.deepcopy(self._VALID)
        bad["transactions"][0]["items"] = ["Doctype Không Tồn Tại"]
        with self.assertRaises(AssertionError):
            _assert_connectivity("AC Asset", bad)

    def test_guard_bites_on_wrong_link_fieldname(self) -> None:
        # 'Asset Lifecycle Event' trỏ AC Asset qua field 'asset', KHÔNG phải 'asset_ref'.
        bad = copy.deepcopy(self._VALID)
        bad["fieldname"] = "asset_ref"
        with self.assertRaises(AssertionError):
            _assert_connectivity("AC Asset", bad)

    def test_guard_bites_on_bogus_internal_link(self) -> None:
        bad = copy.deepcopy(self._VALID)
        bad["internal_links"] = {"Asset Lifecycle Event": "khong_co_field_nay"}
        with self.assertRaises(AssertionError):
            _assert_connectivity("AC Asset", bad)

    def test_guard_bites_on_empty_transactions(self) -> None:
        with self.assertRaises(AssertionError):
            _assert_connectivity("AC Asset", {"fieldname": "asset", "transactions": []})


# ---------------------------------------------------------------------------
# TC-CONN-4 — SC-7 desk affordances (RED tới khi T21 xong)
# ---------------------------------------------------------------------------
class TestHubDeskAffordances(unittest.TestCase):
    """Hub phải tra cứu được: có tiêu đề người đọc được + tìm thấy trong ô tìm kiếm."""

    #: Fieldtype không mang giá trị — Frappe TỪ CHỐI nếu lọt vào `search_fields`
    #: (``DocType.check_search_fields`` → ``no_value_fields``).
    _NO_VALUE_FIELDTYPES = frozenset({
        "Section Break", "Column Break", "Tab Break", "HTML", "Table", "Table MultiSelect",
        "Button", "Image", "Fold", "Heading",
    })

    def test_every_hub_has_title_and_search_metadata(self) -> None:
        problems: list[str] = []
        for hub in HUB_DOCTYPES:
            j = _doctype_json(hub)
            if not j:
                problems.append(f"{hub}: không tìm thấy schema JSON trong app")
                continue
            if not j.get("title_field"):
                problems.append(f"{hub}: thiếu `title_field` ⇒ list view hiện mã thay vì tên")
            if not (j.get("search_fields") or "").strip():
                problems.append(f"{hub}: thiếu `search_fields`")
            if not any(f.get("in_global_search") for f in j.get("fields", [])):
                problems.append(f"{hub}: 0 field `in_global_search` ⇒ ô tìm kiếm Desk không ra")
        self.assertEqual(
            problems,
            [],
            f"{len(problems)} vi phạm khả-năng-tra-cứu (SC-7):\n  - " + "\n  - ".join(problems),
        )

    def test_metadata_would_survive_a_bench_migrate(self) -> None:
        """`title_field`/`search_fields` phải qua được đúng 2 luật Frappe kiểm lúc migrate.

        Metadata DocType chỉ vào CSDL khi ``bench migrate`` chạy — mà migrate là việc của
        người vận hành, không phải của test. Nếu một field bị gõ sai hoặc là loại không
        mang giá trị, ``DocType.check_title_field`` / ``check_search_fields`` sẽ ném lỗi
        và **abort cả lần migrate**. Kiểm ngay tại đây để lỗi lộ ra ở CI, không lộ ra
        giữa lúc nâng cấp site khách.
        """
        problems: list[str] = []
        for hub in HUB_DOCTYPES:
            j = _doctype_json(hub)
            if not j:
                continue
            fields = {f.get("fieldname"): f for f in j.get("fields", [])}

            title = j.get("title_field")
            if title and title not in fields:
                problems.append(
                    f"{hub}: title_field '{title}' không phải fieldname ⇒ migrate abort "
                    f"(InvalidFieldNameError)"
                )

            for raw in (j.get("search_fields") or "").split(","):
                fieldname = raw.strip()
                if not fieldname:
                    continue
                field = fields.get(fieldname)
                if not field:
                    problems.append(
                        f"{hub}: search_fields chứa '{fieldname}' không tồn tại ⇒ migrate abort"
                    )
                elif field.get("fieldtype") in self._NO_VALUE_FIELDTYPES:
                    problems.append(
                        f"{hub}: search_fields chứa '{fieldname}' kiểu "
                        f"{field.get('fieldtype')} (không mang giá trị) ⇒ migrate abort"
                    )
        self.assertEqual(
            problems, [],
            f"{len(problems)} metadata sẽ làm hỏng `bench migrate`:\n  - " + "\n  - ".join(problems),
        )
