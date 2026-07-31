# Copyright (c) 2026, AssetCore Team
"""TC-CONN-T-01..28 — «Bản ghi liên quan» là CÂY DỮ LIỆU THẬT (AC-CR-87 · …94 · 92).

Spec: ``docs/imm-00/05_API_Specification.md §III.24`` · ADR + invariants:
``docs/imm-00/ADR-IMM00-CONNECTIONS-TREE.md`` (D1–D10 / INV-CONN-1..14 · **§17
D-CR92-1..9 / INV-CONN-29..34**) · code shape: ``docs/imm-00/04_Backend_Design.md
§V.7`` (§V.7.1 NGOẠI LỆ cổng I/O) · bộ TC: ``docs/imm-00/07_Testing_QA.md §XVIII``.

Bốn nhóm bất biến mà file này khoá (phần còn lại của hợp đồng CŨ do
``test_connections.py`` giữ — ở đó AC-CR-92 chỉ **DỜI** assert legacy sang khoá mới,
còn ``test_counts_run_under_session_user_not_administrator`` giữ **0 dòng sửa**):

  1. **Hợp đồng khoá** — mỗi ô đúng **9** khoá, so bằng **TẬP** (AC-CR-92 D-CR92-1);
     ``truncated`` và ``total_capped`` là ``int`` 0/1 chứ KHÔNG ``bool`` (parity CR-01:
     codegen Dart/Kotlin parse một khoá lúc ``true`` lúc ``1`` ⇒ crash).
  2. **Một predicate duy nhất** — preview và count derive từ CÙNG một ``frappe.get_list``
     dưới ``frappe.session.user``. Đây là chỗ tái sinh bug production *"Tổng 1430 /
     bảng RỖNG"* nếu ai đó tách thành hai truy vấn.
  3. **Không rò tiếng Anh, không rò field nhạy cảm** — nhãn DocType/trạng thái tiếng
     Việt là SSoT ở BE (LL-FE-53); preview chỉ lấy 3 field nghiệp vụ trung tính.
  4. **Không sinh nút chết** — ``can_create`` là GƯƠNG của quyền THẬT + cổng vòng đời,
     và luôn đi kèm ``create_route_hint`` (hai chiều).
  5. **Ô nói số nào thì drill ra đúng số đó** (AC-CR-94 · INV-CONN-18/19/20/22 —
     ``ADR-IMM00-CONNECTIONS-TREE.md §15`` · bộ TC ``07_Testing_QA.md §XVIII.9``):
     TC-CONN-T-25/26 gọi **THẬT** cả hai đầu (ô ↔ endpoint drill) trong CÙNG một
     ``frappe.session.user`` rồi so ``total`` với số dòng **và** kiểm mọi dòng thuộc
     đúng thiết bị cha. Hai con số bằng nhau vẫn có thể **cùng sai** (bộ lọc bị nuốt ở
     cả hai đầu ⇒ ``1430 == 1430``) nên vế "∀ dòng" là vế không được bỏ.

Run:
  bench --site miyano run-tests --app assetcore --module assetcore.tests.test_connections_tree
"""
from __future__ import annotations

import ast
import glob
import importlib
import inspect
import json
import os
import re
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from assetcore.api.connections import get_connections
from assetcore.services import connections as conn_service
from assetcore.services.shared import connection_meta as cmeta
from assetcore.tests._asset_cleanup import purge_asset, purge_category_by_name

_CAT_NAME = "ConnTree Test Category"
_CAT_CODE = "TEST-CAT-CONNTREE"
_LIMITED_EMAIL = "conn_tree_limited@example.com"
_TEMPLATE_NAME = "ConnTree PM Template"

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: Bộ khoá ĐÚNG-10 của MỖI ô (ADR §18 D-CR105-1 — AC-CR-105 thêm ``create_prefill``
#: vào bộ 9 khoá của AC-CR-92 §17 D-CR92-1). Oracle là **so sánh TẬP**: ``assertIn``
#: xanh cả khi 4 khoá legacy còn nguyên **và** xanh cả khi ai đó bồi thêm khoá thứ 11.
_ITEM_KEYS_V2 = {
    "doctype", "label_vi", "total", "truncated", "total_capped",
    "items", "deep_link_filters", "can_create", "create_route_hint",
    "create_prefill",
}
#: 4 khoá LEGACY đã gỡ (AC-CR-92). Khai tường minh để thông điệp đỏ chỉ thẳng vào
#: "khoá hồi sinh" thay vì chỉ báo "sai bộ khoá".
_LEGACY_ITEM_KEYS = {"label", "count", "capped", "filters"}
#: 5 khoá bắt buộc của MỖI dòng preview (ADR §D5).
_ROW_KEYS = {"name", "title", "status", "status_label", "date"}

#: Khoá **Link fieldname của BE** — CẤM tuyệt đối xuất hiện trong ``create_prefill``
#: (ADR §18 D-CR105-3). ``parents`` (schema BE) và ``query_keys`` (hợp đồng URL của FE)
#: là hai KHÔNG GIAN TÊN khác nhau; lẫn chúng đã trả giá hai lần (đính chính D8 §12.7 +
#: bug deep-link 13/16 ô §13.1) nên đây là assert TƯỜNG MINH, không phải tô điểm.
_FORBIDDEN_PREFILL_KEYS = frozenset({
    "asset_ref", "source_pm_wo", "incident_report", "final_asset", "critical_asset",
})

#: Bảng neo parity 3 điểm (INV-CONN4-3 · ADR §18 D-CR105-6): ``dt → (module API, hàm
#: tạo, DẠNG khai cap)``. Khai TRƯỚC để phép "derive" là tiền định chứ không phải quét
#: đoán; dạng ``const:<TÊN>`` dùng cho module gác bằng hằng ``_CAP_*`` + ``rbac.can``
#: (``api/imm12.py`` cố ý KHÔNG dùng ``rbac.require`` — require leak raw cap vào message).
_CAP_PARITY_ANCHORS: dict[str, tuple[str, str, str]] = {
    "PM Work Order":         ("assetcore.api.imm08", "create_pm_work_order", "require"),
    "Asset Repair":          ("assetcore.api.imm09", "create_repair_work_order", "require"),
    "IMM Asset Calibration": ("assetcore.api.imm11", "create_calibration", "require"),
    "Incident Report":       ("assetcore.api.imm12", "report_incident", "const:_CAP_REPORT"),
    "AC Purchase":           ("assetcore.api.purchase", "create_purchase", "require"),
}

#: Ba doctype CỐ Ý không khai token (ADR §12 D-CR4-2): route tạo của chúng gác cap trỏ
#: doctype KHÁC (``document.write`` / ``commissioning.create`` / ``data.create``) ⇒ khai
#: là **nói dối**, không phải bỏ sót. Khai thêm ⇒ t33 ĐỎ (buộc đọc ADR §12.9 trước).
_CREATE_CAPABILITY_ABSTENTIONS = frozenset({
    "Asset Document", "Asset Transfer", "Service Contract",
})

_FRONTEND_ROUTER = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "frontend", "src", "router", "index.ts",
)

#: Họ field CẤM đưa vào preview (LL-BE-57 — endpoint meta, không phải hồ sơ).
_FORBIDDEN_FIELD_TYPES = {"Currency", "Password", "Signature"}
_FORBIDDEN_FIELD_RE = re.compile(
    r"(amount|cost|price|salary|budget|phone|mobile|email|address|tax_id|bank)", re.I
)

_WORKFLOW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assetcore", "workflow"
)

#: Sáu lời gọi ĐỌC-THEO-TẬP bị cấm ở tầng service (ADR §17 D-CR92-6 điều kiện (a)).
#: Ranh giới của luật là "đọc theo TẬP", KHÔNG phải "mọi lần chạm ``frappe``":
#: ``frappe.get_doc`` / ``has_permission`` / ``get_meta`` / ``db.get_value`` / ``log_error``
#: / ``_`` / ``utils.getdate`` VẪN được phép — siết rộng hơn sẽ đẩy 4 lời gọi vô hại
#: xuống ``api/`` và làm mỏng service thành lớp trung chuyển (CLAUDE.md §15).
_ROW_READING_ORM = (
    "frappe.get_list", "frappe.get_all", "frappe.db.get_all",
    "frappe.db.get_list", "frappe.db.count", "frappe.db.sql",
)


def _insert_bypassing_workflow(data: dict):
    """Insert fixture bỏ qua workflow lifecycle (khuôn dùng chung với test_connections)."""
    prev = frappe.flags.in_install
    frappe.flags.in_install = "frappe"
    try:
        return frappe.get_doc(data).insert(ignore_permissions=True)
    finally:
        frappe.flags.in_install = prev


def _workflow_states_by_doctype() -> dict[str, set[str]]:
    """document_type → tập ``states[].state`` đọc từ ``assetcore/assetcore/workflow/*.json``.

    ``workflow_state`` là Link → ``Workflow State`` nên tập giá trị KHÔNG đọc được từ
    field JSON; nguồn sự thật là chính file workflow.
    """
    out: dict[str, set[str]] = {}
    for path in glob.glob(os.path.join(_WORKFLOW_DIR, "*.json")):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        dt = data.get("document_type")
        if not dt:
            continue
        out.setdefault(dt, set()).update(
            s.get("state") for s in data.get("states") or [] if s.get("state")
        )
    return out


def _api_create_capability(module_name: str, func_name: str, form: str) -> str:
    """Chuỗi capability gác **chính hàm tạo** của một module API — DERIVE, fail-CLOSED.

    Điểm 1 của parity 3 điểm (INV-CONN4-3). Đọc bằng AST chứ không bằng regex: chuỗi cap
    có thể xuất hiện trong comment/docstring của cả file, và điều cần chứng minh là nó
    nằm trong **đường thực thi** của đúng hàm đó.

    Hai dạng khai được hỗ trợ (ADR §18 D-CR105-6):
      * ``"require"`` — ``rbac.require("<cap>")`` trong thân hàm;
      * ``"const:_CAP_X"`` — hằng module-level ``_CAP_X = "<cap>"`` mà thân hàm **với
        tới được** (trực tiếp, hoặc qua đúng một helper cùng module như ``_can_report``).

    Không tìm thấy hàm / không tìm thấy cap / tìm thấy nhiều cap khác nhau ⇒ **raise**
    (test ĐỎ). Trả ``""`` rồi ``continue`` là guard xanh-giả — đúng lớp lỗi §XVIII.8.5.
    """
    mod = importlib.import_module(module_name)
    tree = ast.parse(inspect.getsource(mod))
    func = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == func_name),
        None,
    )
    if func is None:
        raise AssertionError(
            f"parity điểm 1: {module_name} KHÔNG có hàm {func_name}() — hàm bị đổi tên/dời "
            f"⇒ bảng neo _CAP_PARITY_ANCHORS phải cập nhật CÙNG VÒNG (fail-closed)"
        )

    if form == "require":
        # CHỈ lấy gate **vô điều kiện** — lời gọi ``rbac.require`` là câu lệnh trực tiếp
        # của thân hàm. Lý do: hàm tạo có thể còn gate PHỤ nằm trong nhánh ``if`` (vd
        # ``api/purchase.py::create_purchase`` gọi thêm ``rbac.require("purchase.submit")``
        # khi ``auto_submit``) — cap của nút tạo là cap gác **mọi** đường vào hàm, không
        # phải cap của một nhánh tuỳ chọn. Lấy cả nhánh ⇒ guard đỏ GIẢ; lấy "cái đầu
        # tiên bất kể vị trí" ⇒ guard phụ thuộc thứ tự dòng (mong manh).
        caps = sorted({
            stmt.value.args[0].value
            for stmt in func.body
            if isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Call)
            and ast.unparse(stmt.value.func) == "rbac.require"
            and stmt.value.args
            and isinstance(stmt.value.args[0], ast.Constant)
            and isinstance(stmt.value.args[0].value, str)
        })
        if len(caps) != 1:
            raise AssertionError(
                f"parity điểm 1: {module_name}::{func_name} có {len(caps)} gate "
                f"rbac.require VÔ ĐIỀU KIỆN với cap hằng ({caps}) — phải ĐÚNG 1 để so "
                f"được (gate nằm trong nhánh `if` KHÔNG tính: nó không gác mọi đường vào)"
            )
        return caps[0]

    const_name = form.split(":", 1)[1]
    values = sorted({
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        and any(isinstance(t, ast.Name) and t.id == const_name for t in node.targets)
    })
    if len(values) != 1:
        raise AssertionError(
            f"parity điểm 1: {module_name} không có ĐÚNG 1 hằng {const_name} = '<cap>' "
            f"ở mức module (thấy {values})"
        )

    def _uses_const(node) -> bool:
        return any(isinstance(n, ast.Name) and n.id == const_name for n in ast.walk(node))

    if not _uses_const(func):
        helpers = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        called = {
            ast.unparse(n.func) for n in ast.walk(func) if isinstance(n, ast.Call)
        }
        if not any(name in helpers and _uses_const(helpers[name]) for name in called):
            raise AssertionError(
                f"parity điểm 1: {module_name}::{func_name} KHÔNG với tới hằng "
                f"{const_name} (trực tiếp hay qua helper cùng module) ⇒ cap khai một chỗ "
                f"mà hàm gác bằng chỗ khác = gate nói dối"
            )
    return values[0]


def _route_required_capabilities(route_path: str) -> list[str]:
    """``meta.requiredCapabilities`` của một route trong ``frontend/src/router/index.ts``.

    Điểm 3 của parity 3 điểm. Đọc **giá trị khai trong router**, KHÔNG đọc
    ``router/routeAccess.ts``: file đó viết ``'doc' + 'ument.write'`` (nối chuỗi để né
    lint chặn ``document.write``) nên regex literal sẽ kết luận SAI — vế đó đã được đóng
    ở FE bằng cách IMPORT giá trị TS (``router/connectionsCreateParity.test.ts``).

    Fail-CLOSED: thiếu file / thiếu route / không parse được list literal ⇒ **raise**.
    """
    try:
        with open(_FRONTEND_ROUTER, encoding="utf-8") as fh:
            src = fh.read()
    except OSError as exc:
        raise AssertionError(f"parity điểm 3: không đọc được {_FRONTEND_ROUTER}: {exc}")

    anchor = re.search(rf"""path:\s*['"]{re.escape(route_path)}['"]\s*,""", src)
    if anchor is None:
        raise AssertionError(
            f"parity điểm 3: router/index.ts KHÔNG khai route '{route_path}' "
            f"(CREATE_CONTEXT trỏ route không tồn tại ⇒ nút chết)"
        )
    nxt = re.search(r"""path:\s*['"]""", src[anchor.end():])
    window = src[anchor.end(): anchor.end() + nxt.start()] if nxt else src[anchor.end():]

    caps_block = re.search(r"requiredCapabilities:\s*\[(.*?)\]", window, re.S)
    if caps_block is None:
        raise AssertionError(
            f"parity điểm 3: route '{route_path}' KHÔNG khai meta.requiredCapabilities "
            f"⇒ route-guard mở toang trong khi API vẫn gác ⇒ người dùng vào form rồi 403"
        )
    caps = re.findall(r"""['"]([^'"]+)['"]""", caps_block.group(1))
    if not caps:
        raise AssertionError(
            f"parity điểm 3: requiredCapabilities của '{route_path}' không parse được "
            f"thành list literal: {caps_block.group(1)!r}"
        )
    return caps


class TestConnectionsTree(FrappeTestCase):
    """Cây dữ liệu liên quan — preview thật, nhãn VI, đường tạo mới có quyền."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")

        cls.cat = frappe.get_doc({
            "doctype": "AC Asset Category",
            "category_name": _CAT_NAME,
            "category_code": _CAT_CODE,
            "default_pm_interval_days": 30,
        }).insert(ignore_permissions=True)

        cls.template = frappe.get_doc({
            "doctype": "PM Checklist Template",
            "template_name": _TEMPLATE_NAME,
            "asset_category": cls.cat.name,
            "pm_type": "Quarterly",
        }).insert(ignore_permissions=True).name

        # A6 = 6 phiếu bảo trì ⇒ chứng minh CẮT; A3 = 3 phiếu ⇒ chứng minh KHÔNG cắt;
        # A0 = 0 liên kết ⇒ chứng minh không lẫn dữ liệu giữa các bản ghi.
        cls.asset6 = cls._new_asset("ConnTree Asset 6", "CONNTREE-SN-6")
        cls.asset3 = cls._new_asset("ConnTree Asset 3", "CONNTREE-SN-3")
        cls.asset0 = cls._new_asset("ConnTree Asset 0", "CONNTREE-SN-0")

        cls.sched6 = cls._new_schedule(cls.asset6)
        cls.sched3 = cls._new_schedule(cls.asset3)
        cls.wo6 = [cls._new_pm_wo(cls.asset6, cls.sched6, i) for i in range(6)]
        cls.wo3 = [cls._new_pm_wo(cls.asset3, cls.sched3, i) for i in range(3)]

        # ── Fixture riêng cho TC-CONN-T-25/26 (bất biến count == drill) ──────────
        # Tách khỏi asset6/asset3 để 2 TC mới KHÔNG phụ thuộc số phiếu của TC khác
        # (thêm 1 WO ở đó là đổi kỳ vọng ở đây ⇒ ĐỎ giả).
        cls.asset_sched = cls._new_asset("ConnTree Asset Sched", "CONNTREE-SN-SCHED")
        # 3 lịch bảo trì: 2 Active + 1 Paused. ``autoname = format:PMS-{asset_ref}-{pm_type}``
        # ⇒ 3 ``pm_type`` PHẢI khác nhau, nếu không DuplicateEntryError.
        # ``pm_interval_days = 3650`` + KHÔNG ``last_pm_date`` ⇒ next_due = hôm nay+3650 ⇒
        # hook ``PMSchedule.on_update`` KHÔNG tự sinh PM Work Order (fixture mồ côi + lệch ô).
        cls.pm_scheds = [
            cls._new_schedule(cls.asset_sched, pm_type="Quarterly", status="Active"),
            cls._new_schedule(cls.asset_sched, pm_type="Semi-Annual", status="Active"),
            cls._new_schedule(cls.asset_sched, pm_type="Annual", status="Paused"),
        ]
        # 2 lịch hiệu chuẩn: 1 đang bật + 1 đã tắt. Bản ĐANG BẬT cố ý QUÁ HẠN để phép
        # kiểm "GIAO, không clobber" (INV-CONN-20) có tập giao KHÁC RỖNG — cả 2 dòng
        # đều tương lai thì `{asset, overdue}` trả 0 dòng ⇒ mệnh đề ⊆ đúng vì rỗng
        # (vacuous), đúng lớp assert mà D-CR94-8 cấm.
        cls.cal_active_overdue = cls._new_calibration_schedule(
            cls.asset_sched, calibration_type="External", is_active=1,
            next_due_date=add_days(nowdate(), -5),
        )
        cls.cal_inactive = cls._new_calibration_schedule(
            cls.asset_sched, calibration_type="In-House", is_active=0,
            next_due_date=add_days(nowdate(), 3650),
        )

        # ── Fixture riêng cho t31 (hub Incident Report — AC-CR-105) ──────────────
        # KHÔNG gắn sự cố vào asset0/asset6: asset0 là oracle "0 liên kết" của t20 và
        # asset6 là oracle số phiếu của t02. Serial có hậu tố BĂM: fixture tên cố định
        # tự chặn chính nó sau một lần crash không chạy teardown (LL-TEST).
        cls.asset_inc = cls._new_asset(
            "ConnTree Asset Incident", f"CONNTREE-SN-INC-{frappe.generate_hash(length=6)}"
        )
        cls.incident = _insert_bypassing_workflow({
            "doctype": "Incident Report",
            "asset": cls.asset_inc,
            "incident_type": "Malfunction",
            "severity": "Medium",
            "description": "<p>Sự cố fixture cho parity khoá prefill theo hub cha.</p>",
        }).name

        frappe.db.commit()

    @classmethod
    def _new_asset(cls, asset_name: str, serial: str) -> str:
        return _insert_bypassing_workflow({
            "doctype": "AC Asset",
            "asset_name": asset_name,
            "asset_category": cls.cat.name,
            "lifecycle_status": "Active",
            "manufacturer_sn": serial,
        }).name

    @classmethod
    def _new_schedule(cls, asset: str, *, pm_type: str = "Quarterly",
                      status: str = "Active") -> str:
        return frappe.get_doc({
            "doctype": "PM Schedule",
            "asset_ref": asset,
            "pm_type": pm_type,
            "pm_interval_days": 3650,
            "checklist_template": cls.template,
            "status": status,
        }).insert(ignore_permissions=True).name

    @classmethod
    def _new_calibration_schedule(cls, asset: str, *, calibration_type: str,
                                  is_active: int, next_due_date: str) -> str:
        """Lịch hiệu chuẩn — ``interval_days`` reqd; controller chỉ điền ``device_model``."""
        return frappe.get_doc({
            "doctype": "IMM Calibration Schedule",
            "asset": asset,
            "calibration_type": calibration_type,
            "interval_days": 365,
            "next_due_date": next_due_date,
            "is_active": is_active,
        }).insert(ignore_permissions=True).name

    @classmethod
    def _new_pm_wo(cls, asset: str, schedule: str, offset: int) -> str:
        return _insert_bypassing_workflow({
            "doctype": "PM Work Order",
            "asset_ref": asset,
            "pm_schedule": schedule,
            "pm_type": "Quarterly",
            "wo_type": "Preventive",
            "status": "In Progress" if offset == 0 else "Open",
            "due_date": add_days(nowdate(), 7 + offset),
        }).name

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        purge_asset(getattr(cls, "asset6", None))
        purge_asset(getattr(cls, "asset3", None))
        purge_asset(getattr(cls, "asset0", None))
        # purge_asset phủ CẢ 'PM Schedule' và 'IMM Calibration Schedule'
        # (tests/_asset_cleanup.py::_ASSET_DEPENDENTS) ⇒ 5 lịch của asset_sched đi theo.
        purge_asset(getattr(cls, "asset_sched", None))
        # 'Incident Report' có trong _ASSET_DEPENDENTS (tests/_asset_cleanup.py) ⇒ sự cố
        # fixture của t31 đi theo asset, KHÔNG cần teardown riêng.
        purge_asset(getattr(cls, "asset_inc", None))
        if getattr(cls, "template", None) and frappe.db.exists("PM Checklist Template", cls.template):
            frappe.delete_doc("PM Checklist Template", cls.template, force=True,
                              ignore_permissions=True)
        purge_category_by_name(_CAT_NAME)
        if frappe.db.exists("User", _LIMITED_EMAIL):
            frappe.delete_doc("User", _LIMITED_EMAIL, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        frappe.set_user("Administrator")

    # ── helpers ───────────────────────────────────────────────────────────────
    def _payload(self, doctype: str, name: str, **kwargs) -> dict:
        res = get_connections(doctype, name, **kwargs)
        self.assertTrue(res["success"], res)
        return res["data"]

    def _items(self, payload: dict) -> dict[str, dict]:
        return {it["doctype"]: it for g in payload["groups"] for it in g["items"]}

    def _all_items(self, payload: dict) -> list[dict]:
        return [it for g in payload["groups"] for it in g["items"]]

    def _ensure_limited_user(self) -> str:
        if not frappe.db.exists("User", _LIMITED_EMAIL):
            user = frappe.get_doc({
                "doctype": "User", "email": _LIMITED_EMAIL, "first_name": "Han Che Tree",
                "send_welcome_email": 0, "enabled": 1,
            }).insert(ignore_permissions=True)
            user.add_roles("AssetCore System User")
            frappe.db.commit()
        return _LIMITED_EMAIL

    # ── TC-CONN-T-01 — ĐÚNG 10 khoá, so bằng TẬP, trên MỌI hub đã seed ────────
    def test_t01_every_item_has_exactly_ten_keys_on_every_seeded_hub(self) -> None:
        """INV-CONN-29/30 + INV-CONN105-1 (AC-CR-92 §17 D-CR92-1/2 · AC-CR-105 §18
        D-CR105-1) — oracle là SO SÁNH TẬP.

        Vì sao KHÔNG ``assertIn``: nó chỉ chứng minh khoá **có mặt** ⇒ xanh cả khi 4
        khoá legacy (``label``/``count``/``capped``/``filters``) còn nguyên, **và** xanh
        cả khi ai đó bồi thêm khoá thứ 11 ("tạm để đây cho FE dùng").
        ``assertEqual(set(item), _ITEM_KEYS_V2)`` chứng minh HAI chiều trong một dòng:
        legacy đã VẮNG **và** không ai lén thêm.

        AC-CR-105 đổi **9 → 10** khoá (``create_prefill``): oracle bộ khoá PHẢI đổi
        CÙNG VÒNG với hợp đồng, nếu không khoá mới **không có ai canh** — đúng gốc drift
        D-CR92-7 (doc hứa ``create_prefill`` suốt 2 vòng trong khi đĩa 0 hit).

        Vì sao quét MỌI hub đã seed (không chỉ ``AC Asset``): cùng một hàm dựng ô chạy
        cho 12 hub, và nhánh ``internal_links`` (liên kết XUÔI) đi qua đoạn mã KHÁC với
        nhánh reverse-link ⇒ một nhánh bỏ sót vẫn phát được shape khác mà hub đơn không
        thấy.

        Hai cờ cắt là **int THUẦN**: ``bool`` là subclass của ``int`` nên
        ``assertIsInstance(v, int)`` KHÔNG bắt được ``True`` — phải ``type(v) is int``
        **và** ``not isinstance(v, bool)`` (CR-01: một khoá lúc ``true`` lúc ``1`` làm
        codegen Dart/Kotlin crash).
        """
        checked_hubs: list[str] = []
        checked_cells = 0
        for hub in sorted(conn_service.allowed_source_doctypes()):
            rows = frappe.get_all(hub, fields=["name"], limit_page_length=1)
            if not rows:
                continue
            checked_hubs.append(hub)
            for item in self._all_items(self._payload(hub, rows[0]["name"])):
                checked_cells += 1
                where = f"{hub} → {item.get('doctype')}"
                self.assertEqual(
                    set(item), _ITEM_KEYS_V2,
                    f"{where}: sai bộ khoá ô (thừa {sorted(set(item) - _ITEM_KEYS_V2)}, "
                    f"thiếu {sorted(_ITEM_KEYS_V2 - set(item))})",
                )
                self.assertEqual(
                    _LEGACY_ITEM_KEYS & set(item), set(),
                    f"{where}: khoá LEGACY hồi sinh sau AC-CR-92 — hai tên cho một đại "
                    f"lượng là nguồn lệch có hệ thống (ADR §17.1 #2)",
                )
                for flag in ("truncated", "total_capped"):
                    self.assertIs(type(item[flag]), int,
                                  f"{where}.{flag} phải là int THUẦN, đang là "
                                  f"{type(item[flag]).__name__}")
                    self.assertFalse(isinstance(item[flag], bool),
                                     f"{where}.{flag} là bool ⇒ crash codegen (CR-01)")
                    self.assertIn(item[flag], (0, 1), f"{where}.{flag} ngoài {{0,1}}")
                self.assertIsInstance(item["total"], int)
                self.assertIsInstance(item["can_create"], bool)
                self.assertIsInstance(item["create_route_hint"], str)
                self.assertIsInstance(item["create_prefill"], dict)
                self.assertIsInstance(item["label_vi"], str)

        # Chống xanh-giả: hub thiếu bản ghi thì bỏ qua là hợp lệ, TC rỗng thì không.
        self.assertLessEqual(
            {"AC Asset", "PM Work Order"}, set(checked_hubs),
            f"Hai hub CÓ fixture trong file này phải luôn được kiểm; mới kiểm: {checked_hubs}",
        )
        self.assertGreaterEqual(
            checked_cells, 20,
            f"Chỉ kiểm được {checked_cells} ô trên {len(checked_hubs)} hub — duyệt cây hỏng",
        )

    # ── TC-CONN-T-02 / T-03 — preview ↔ count CÙNG predicate ─────────────────
    def test_t02_six_work_orders_are_truncated_to_five(self) -> None:
        item = self._items(self._payload("AC Asset", self.asset6))["PM Work Order"]
        self.assertEqual(item["total"], 6)
        self.assertEqual(item["truncated"], 1)
        self.assertEqual(len(item["items"]), 5)
        # 6 < CAP ⇒ `total` là con số CHÍNH XÁC, không phải cận dưới (badge "6", không "6+").
        self.assertEqual(item["total_capped"], 0)

    def test_t03_three_work_orders_are_not_truncated(self) -> None:
        item = self._items(self._payload("AC Asset", self.asset3))["PM Work Order"]
        self.assertEqual(item["total"], 3)
        self.assertEqual(item["truncated"], 0)
        self.assertEqual(len(item["items"]), 3)

    # ── TC-CONN-T-04 — ZERO-COST + đúng 1 truy vấn/ô ─────────────────────────
    def test_t04_zero_cost_no_count_query_and_one_get_list_per_item(self) -> None:
        """Không COUNT phụ, và mỗi ô phát ĐÚNG 1 lời gọi đọc dòng.

        ``frappe.db.count`` bị thay bằng stub NÉM lỗi (nó bỏ qua
        ``permission_query_conditions`` ⇒ vừa sai số vừa rò dữ liệu). ``frappe.db.sql``
        được **bọc** (không ném — ``get_list`` chạy qua chính nó) để soi xem có câu
        COUNT nào lọt xuống DB hay không.

        AC-CR-105 (§18 D-CR105-9 · INV-CONN4-10) **bồi** thêm một vế — SIẾT chặt hơn,
        không nới: ``lifecycle_status`` của bản ghi cha được đọc **ĐÚNG 1 LẦN cho cả
        cây**. Cổng vòng đời chạy cho MỌI ô (19 ô trên hub ``AC Asset``) nên "đọc lại
        per-ô" là mutation rất dễ vô tình land khi ai đó land P4 per-doctype
        (``AC-CR-90(c)``) — và nó không có triệu chứng nào ngoài +19 truy vấn/lần mở tab.
        """
        seen_sql: list[str] = []
        real_sql = frappe.db.sql
        real_count = frappe.db.count
        real_get_list = frappe.get_list
        real_get_value = frappe.db.get_value
        calls: list[str] = []
        lifecycle_reads: list[tuple] = []

        def _spy_sql(query, *a, **kw):
            seen_sql.append(str(query))
            return real_sql(query, *a, **kw)

        def _boom_count(*a, **kw):  # pragma: no cover - chỉ chạy khi vi phạm
            raise AssertionError("frappe.db.count bị gọi ⇒ bỏ qua row-scope + COUNT thừa")

        def _spy_get_list(doctype, *a, **kw):
            calls.append(doctype)
            return real_get_list(doctype, *a, **kw)

        def _spy_get_value(*a, **kw):
            fieldname = a[2] if len(a) > 2 else kw.get("fieldname")
            if a[:1] == ("AC Asset",) and fieldname == "lifecycle_status":
                lifecycle_reads.append(a)
            return real_get_value(*a, **kw)

        frappe.db.sql = _spy_sql
        frappe.db.count = _boom_count
        frappe.get_list = _spy_get_list
        frappe.db.get_value = _spy_get_value
        try:
            payload = self._payload("AC Asset", self.asset3)
        finally:
            frappe.db.sql = real_sql
            frappe.db.count = real_count
            frappe.get_list = real_get_list
            frappe.db.get_value = real_get_value

        items = self._all_items(payload)
        self.assertEqual(
            len(calls), len(items),
            f"Phải đúng 1 lời gọi đọc dòng cho mỗi ô: {len(items)} ô nhưng {len(calls)} lời gọi",
        )
        offenders = [q for q in seen_sql if re.search(r"\bcount\s*\(", q, re.I)]
        self.assertEqual(offenders, [], f"Có truy vấn COUNT lọt xuống DB: {offenders[:2]}")
        self.assertEqual(
            len(lifecycle_reads), 1,
            f"`lifecycle_status` phải đọc ĐÚNG 1 lần cho cả cây ({len(items)} ô) — đang "
            f"{len(lifecycle_reads)} lần ⇒ cổng vòng đời đọc lại per-ô, phá ZERO-COST "
            f"(INV-CONN-6 / INV-CONN4-10)",
        )

    # ── TC-CONN-T-05 — AST guard trên CẢ HAI file ────────────────────────────
    def test_t05_no_unscoped_read_in_api_or_service(self) -> None:
        from assetcore.api import connections as api_mod

        for mod in (api_mod, conn_service):
            tree = ast.parse(inspect.getsource(mod))
            called: list[str] = []
            kwargs_used: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    called.append(ast.unparse(node.func))
                    kwargs_used.extend(kw.arg for kw in node.keywords if kw.arg)
            where = mod.__name__
            self.assertNotIn("frappe.db.count", called,
                             f"{where}: frappe.db.count BỎ QUA permission_query_conditions")
            self.assertNotIn("frappe.get_all", called,
                             f"{where}: get_all = get_list(ignore_permissions=True)")
            self.assertNotIn("ignore_permissions", kwargs_used,
                             f"{where}: không được truyền ignore_permissions")

        api_source = inspect.getsource(api_mod)
        self.assertIn("frappe.get_list(", api_source,
                      "Đọc dòng phải qua frappe.get_list (scoped) — giữ oracle của test_connections.py")

    # ── TC-CONN-T-06 — bất biến toàn cục trên MỌI hub ────────────────────────
    def test_t06_invariant_holds_for_every_hub(self) -> None:
        checked = 0
        for hub in sorted(conn_service.allowed_source_doctypes()):
            rows = frappe.get_all(hub, fields=["name"], limit_page_length=1)
            if not rows:
                continue
            payload = self._payload(hub, rows[0]["name"])
            for item in self._all_items(payload):
                self.assertEqual(
                    len(item["items"]), min(item["total"], cmeta.PREVIEW_LIMIT),
                    f"{hub} → {item['doctype']}: len(items) != min(total, PREVIEW_LIMIT)",
                )
                self.assertEqual(item["truncated"],
                                 1 if item["total"] > cmeta.PREVIEW_LIMIT else 0)
                # INV-CONN-32 — ô ``truncated=0 ∧ total_capped=1`` KHÔNG THỂ tồn tại:
                # chạm trần ⇒ total == CAP == 100 > preview_limit (≤ 10) ⇒ đã cắt.
                if item["total_capped"] == 1:
                    self.assertEqual(item["total"], conn_service.CONNECTION_COUNT_CAP,
                                     f"{hub} → {item['doctype']}: total_capped=1 mà total "
                                     f"!= trần ⇒ clamp đã bị gỡ")
                    self.assertEqual(item["truncated"], 1, f"{hub} → {item['doctype']}")
            checked += 1
        self.assertGreater(checked, 0, "Không hub nào có bản ghi để kiểm — fixture hỏng?")

    # ── TC-CONN-T-07 — dòng preview có dữ liệu THẬT ──────────────────────────
    def test_t07_preview_rows_are_real_and_never_null(self) -> None:
        payload = self._payload("AC Asset", self.asset6)
        seeded = set(self.wo6)
        seen_wo = set()
        for item in self._all_items(payload):
            for row in item["items"]:
                self.assertEqual(set(row), _ROW_KEYS, f"{item['doctype']}: sai bộ khoá dòng")
                for key, value in row.items():
                    self.assertIsNotNone(value, f"{item['doctype']}.{key} là None")
                    self.assertIsInstance(value, str, f"{item['doctype']}.{key} không phải str")
                self.assertNotEqual(row["title"], "", f"{item['doctype']}: title rỗng")
                if row["date"]:
                    self.assertRegex(row["date"], _DATE_RE)
            if item["doctype"] == "PM Work Order":
                seen_wo = {r["name"] for r in item["items"]}
        self.assertTrue(seen_wo <= seeded and seen_wo,
                        f"Dòng preview không khớp bản ghi seed: {seen_wo - seeded}")

    # ── TC-CONN-T-08 — nhãn trạng thái tiếng Việt ────────────────────────────
    def test_t08_status_label_is_vietnamese(self) -> None:
        self.assertEqual(cmeta.status_label("PM Work Order", "In Progress"), "Đang thực hiện")
        self.assertEqual(cmeta.status_label("PM Work Order", "MÃ-LẠ-KHÔNG-CÓ-THẬT"),
                         cmeta.STATUS_LABEL_UNKNOWN)
        self.assertEqual(cmeta.status_label("PM Work Order", ""), "")

        item = self._items(self._payload("AC Asset", self.asset6))["PM Work Order"]
        labels = {r["status_label"] for r in item["items"]}
        self.assertTrue(labels, "Không dòng nào có nhãn trạng thái")
        for label in labels:
            self.assertNotIn(label, {"Open", "In Progress", "Completed", "Cancelled"},
                             "Rò mã trạng thái tiếng Anh ra UI (LL-FE-53)")

    # ── TC-CONN-T-09 — parity bản dịch lifecycle (không đẻ bản thứ hai) ──────
    def test_t09_lifecycle_labels_mirror_imm00(self) -> None:
        from assetcore.services.imm00 import _LIFECYCLE_VI, _lifecycle_vi

        for code in _LIFECYCLE_VI:
            self.assertEqual(cmeta.status_label("AC Asset", code), _lifecycle_vi(code),
                             f"Bản dịch lifecycle lệch với services/imm00 ở mã {code}")

    # ── TC-CONN-T-10 — parity nhãn DocType (duyệt dashboard THẬT) ────────────
    def test_t10_every_dashboard_doctype_has_vietnamese_label(self) -> None:
        missing: list[str] = []
        untranslated: list[str] = []
        seen: set[str] = set()
        for hub, module in conn_service.iter_dashboard_modules():
            data = module.get_data() or {}
            for group in data.get("transactions") or []:
                for dt in group.get("items") or []:
                    seen.add(dt)
                    if dt not in cmeta.LABEL_VI:
                        missing.append(f"{hub} → {dt}")
                    elif cmeta.LABEL_VI[dt] == dt:
                        untranslated.append(dt)
        self.assertGreater(len(seen), 30, "Duyệt dashboard hỏng — quá ít doctype")
        self.assertEqual(missing, [], f"Doctype thiếu nhãn VI trong LABEL_VI: {missing}")
        self.assertEqual(untranslated, [], f"Nhãn VI vẫn là tên DocType thô: {untranslated}")

    # ── TC-CONN-T-11 — PREVIEW_FIELDS hợp lệ ─────────────────────────────────
    def test_t11_preview_fields_exist_permlevel_zero_and_safe(self) -> None:
        problems: list[str] = []
        for dt, spec in cmeta.PREVIEW_FIELDS.items():
            if not frappe.db.exists("DocType", dt):
                problems.append(f"{dt}: DocType không tồn tại")
                continue
            meta = frappe.get_meta(dt)
            for role, fieldname in (("title", spec.title), ("status", spec.status),
                                    ("date", spec.date)):
                if not fieldname:
                    continue
                df = meta.get_field(fieldname)
                if df is None:
                    problems.append(f"{dt}.{fieldname} ({role}) KHÔNG tồn tại")
                    continue
                if (df.permlevel or 0) != 0:
                    problems.append(f"{dt}.{fieldname} ({role}) permlevel={df.permlevel}")
                if df.fieldtype in _FORBIDDEN_FIELD_TYPES or _FORBIDDEN_FIELD_RE.search(fieldname):
                    problems.append(f"{dt}.{fieldname} ({role}) là field nhạy cảm/tài chính")
                if role == "date" and df.fieldtype not in ("Date", "Datetime"):
                    problems.append(f"{dt}.{fieldname} (date) fieldtype={df.fieldtype}")
                if role == "status" and df.fieldtype not in ("Select", "Link", "Data"):
                    problems.append(f"{dt}.{fieldname} (status) fieldtype={df.fieldtype}")
        self.assertEqual(problems, [], f"PREVIEW_FIELDS sai: {problems}")

    # ── TC-CONN-T-12 — phủ nhãn cho mọi giá trị enum trạng thái ──────────────
    def test_t12_every_status_enum_value_has_vietnamese_label(self) -> None:
        wf_states = _workflow_states_by_doctype()
        missing: list[str] = []
        for dt, spec in cmeta.PREVIEW_FIELDS.items():
            if not spec.status or not frappe.db.exists("DocType", dt):
                continue
            df = frappe.get_meta(dt).get_field(spec.status)
            if df is None:
                continue
            values: set[str] = set()
            if df.fieldtype == "Select":
                values = {v.strip() for v in (df.options or "").split("\n") if v.strip()}
            elif spec.status == "workflow_state":
                values = set(wf_states.get(dt) or set())
            if spec.status == "workflow_state":
                values |= set(wf_states.get(dt) or set())
            for value in sorted(values):
                if cmeta.status_label(dt, value) == cmeta.STATUS_LABEL_UNKNOWN:
                    missing.append(f"{dt}.{spec.status} = {value!r}")
        self.assertEqual(missing, [], f"Giá trị trạng thái chưa có nhãn VI: {missing}")

    # ── TC-CONN-T-13 — allowlist + message thống nhất ────────────────────────
    def test_t13_allowlist_and_uniform_not_found_message(self) -> None:
        garbage = get_connections("Xyz Không Tồn Tại", "ABC")
        self.assertFalse(garbage["success"])
        self.assertEqual(garbage["code"], "NOT_FOUND")

        missing_record = get_connections("AC Asset", "AC-ASSET-KHONG-CO-THAT")
        self.assertFalse(missing_record["success"])
        self.assertEqual(missing_record["code"], "NOT_FOUND")
        self.assertEqual(
            garbage["error"], missing_record["error"],
            "Message phải THỐNG NHẤT ⇒ không phân biệt 'doctype sai' với 'mã bản ghi sai'",
        )
        for res in (garbage, missing_record):
            self.assertNotIn("Xyz", res["error"])
            self.assertNotIn("KHONG-CO-THAT", res["error"])

        # Tồn tại nhưng ngoài allowlist (không có *_dashboard.py) ⇒ rỗng CÓ KIỂM SOÁT.
        outside = get_connections("AC Asset Category", self.cat.name)
        self.assertTrue(outside["success"], outside)
        self.assertEqual(outside["data"]["groups"], [])
        self.assertEqual(outside["data"]["total"], 0)
        self.assertNotIn("AC Asset Category", conn_service.allowed_source_doctypes())
        self.assertIn("AC Asset", conn_service.allowed_source_doctypes())

    # ── TC-CONN-T-14 — clamp preview_limit ───────────────────────────────────
    def test_t14_preview_limit_is_clamped(self) -> None:
        self.assertEqual(cmeta.clamp_preview_limit(0), 1)
        self.assertEqual(cmeta.clamp_preview_limit(-3), 1)
        self.assertEqual(cmeta.clamp_preview_limit(99), cmeta.PREVIEW_LIMIT_MAX)
        self.assertEqual(cmeta.clamp_preview_limit("abc"), cmeta.PREVIEW_LIMIT)
        self.assertEqual(cmeta.clamp_preview_limit(""), cmeta.PREVIEW_LIMIT)
        self.assertEqual(cmeta.clamp_preview_limit("3"), 3)

        item = self._items(self._payload("AC Asset", self.asset6, preview_limit=2))["PM Work Order"]
        self.assertEqual(len(item["items"]), 2)
        self.assertEqual(item["total"], 6)
        self.assertEqual(item["truncated"], 1)

        # Trần đã clamp (10) là số truyền vào truncation_meta ⇒ 6 dòng KHÔNG bị coi là cắt.
        item = self._items(self._payload("AC Asset", self.asset6, preview_limit=99))["PM Work Order"]
        self.assertEqual(len(item["items"]), 6)
        self.assertEqual(item["truncated"], 0)

        item = self._items(self._payload("AC Asset", self.asset6, preview_limit="abc"))["PM Work Order"]
        self.assertEqual(len(item["items"]), cmeta.PREVIEW_LIMIT)

    # ── TC-CONN-T-15 — deep_link_filters an toàn query-string ────────────────
    def test_t15_deep_link_filters_are_string_scalars(self) -> None:
        payload = self._payload("AC Asset", self.asset6)
        for item in self._all_items(payload):
            allowed = conn_service.deep_link_keys(item["doctype"])
            for key, value in item["deep_link_filters"].items():
                self.assertIn(key, allowed, f"{item['doctype']}: khoá {key} ngoài allowlist")
                self.assertIsInstance(value, str, f"{item['doctype']}.{key} không phải str")
            if item["total"] > 0:
                self.assertNotEqual(item["deep_link_filters"], {},
                                    f"{item['doctype']}: có dữ liệu nhưng KHÔNG có đường tới")
        self.assertEqual(
            self._items(payload)["PM Work Order"]["deep_link_filters"],
            {"asset_ref": self.asset6},
        )

    def test_t15b_internal_links_join_names_with_comma(self) -> None:
        payload = self._payload("PM Work Order", self.wo6[0])
        item = self._items(payload).get("AC Asset")
        self.assertIsNotNone(item, "Đồ thị PM Work Order phải có ô Thiết bị (internal_links)")
        self.assertEqual(item["deep_link_filters"], {"name": self.asset6})
        # AC-CR-92 gỡ khoá `filters` (dạng Frappe ``{"name": ["in", [...]]}`` không
        # serialize được thành query-string, D-CR92-5) ⇒ bộ lọc nội bộ chỉ còn quan sát
        # được qua KẾT QUẢ: đúng 1 dòng, và dòng đó là CHÍNH thiết bị cha của phiếu.
        self.assertEqual(item["total"], 1)
        self.assertEqual([r["name"] for r in item["items"]], [self.asset6])

    # ── TC-CONN-T-16..19 — can_create không sinh nút chết ────────────────────
    def test_t16_can_create_and_route_hint_are_two_way(self) -> None:
        for hub in sorted(conn_service.allowed_source_doctypes()):
            rows = frappe.get_all(hub, fields=["name"], limit_page_length=1)
            if not rows:
                continue
            for item in self._all_items(self._payload(hub, rows[0]["name"])):
                self.assertEqual(
                    item["can_create"], bool(item["create_route_hint"]),
                    f"{hub} → {item['doctype']}: can_create lệch create_route_hint",
                )
                if item["can_create"]:
                    self.assertIn(item["doctype"], cmeta.CREATE_CONTEXT)
                    self.assertTrue(frappe.has_permission(item["doctype"], ptype="create"))

    def test_t17_restricted_user_gets_no_create_affordance(self) -> None:
        email = self._ensure_limited_user()
        frappe.set_user(email)
        try:
            res = get_connections("AC Asset", self.asset6)
        finally:
            frappe.set_user("Administrator")
        if not res["success"]:
            self.assertEqual(res["code"], "FORBIDDEN")
            return
        for item in self._all_items(res["data"]):
            self.assertFalse(item["can_create"],
                             f"{item['doctype']}: quảng cáo nút tạo cho user không có quyền")
            self.assertEqual(item["create_route_hint"], "")

    def test_t18_forward_links_never_offer_create(self) -> None:
        # Ô 'AC Asset' trong đồ thị của PM Work Order là liên kết XUÔI (internal_links):
        # "tạo Thiết bị" từ màn phiếu bảo trì là vô nghĩa ⇒ luôn False dù có quyền tạo.
        self.assertTrue(frappe.has_permission("AC Asset", ptype="create"))
        item = self._items(self._payload("PM Work Order", self.wo6[0]))["AC Asset"]
        self.assertFalse(item["can_create"])
        self.assertEqual(item["create_route_hint"], "")

    def test_t19_lifecycle_gate_mirrors_validator(self) -> None:
        from assetcore.services.shared import AssetStatus

        self.assertIn("Decommissioned", AssetStatus.BLOCKED_FOR_WO)
        original = frappe.db.get_value("AC Asset", self.asset6, "lifecycle_status")
        # Fixture-only: đặt thẳng trạng thái để kiểm cổng hiển thị; nghiệp vụ THẬT đi qua
        # transition_asset_status (đường thanh lý IMM-14 có gate riêng).
        frappe.db.set_value("AC Asset", self.asset6, "lifecycle_status", "Decommissioned",
                            update_modified=False)
        frappe.db.commit()
        try:
            for item in self._all_items(self._payload("AC Asset", self.asset6)):
                self.assertFalse(
                    item["can_create"],
                    f"{item['doctype']}: quảng cáo tạo phiếu trên thiết bị đã thanh lý",
                )
        finally:
            frappe.db.set_value("AC Asset", self.asset6, "lifecycle_status", original,
                                update_modified=False)
            frappe.db.commit()

        item = self._items(self._payload("AC Asset", self.asset6))["PM Work Order"]
        self.assertTrue(item["can_create"])
        self.assertEqual(item["create_route_hint"], "/pm/work-orders/new")

    # ── TC-CONN-T-20 — nghĩa cấp PAYLOAD không đổi sau khi gỡ `count` ─────────
    def test_t20_payload_total_is_sum_of_cell_totals(self) -> None:
        """INV-CONN-31 (ADR §17 D-CR92-3) — ``payload["total"] == Σ item["total"]``.

        AC-CR-92 gỡ ``count`` ở cấp Ô nhưng **không** đổi hợp đồng cấp payload: đó vẫn
        là "tổng cộng dồn mọi ô", chỉ đổi *tên biến nguồn*. Luật cài đặt là cộng dồn
        ĐÚNG cái giá trị đã đặt vào ``item["total"]`` — hai biểu thức cùng nghĩa đặt
        cạnh nhau là hai cơ hội độc lập để nói dối (khuôn bug *"Tổng 1430 / bảng RỖNG"*).
        """
        payload = self._payload("AC Asset", self.asset6)
        items = self._all_items(payload)
        self.assertTrue(items, "Không ô nào được trả về cho tài sản có dữ liệu")
        self.assertEqual(payload["total"], sum(it["total"] for it in items),
                         "data.total (cấp payload) phải là TỔNG CỘNG DỒN total mọi ô")
        self.assertEqual(set(payload), {"doctype", "name", "groups", "total"},
                         "Bộ khoá cấp payload KHÔNG đổi ở AC-CR-92 (D-CR92-1 bảng)")
        for group in payload["groups"]:
            self.assertEqual(set(group), {"label", "label_vi", "items"},
                             "Nhóm giữ CẢ `label` lẫn `label_vi` (D-CR92-4) — nhãn nhóm "
                             "được khai bằng _('…') trong *_dashboard.py nên đã là VI")
        self.assertEqual(self._items(payload)["PM Work Order"]["deep_link_filters"],
                         {"asset_ref": self.asset6})
        # Tài sản không có liên kết nào ⇒ vẫn trả cây có kiểm soát, không lẫn dữ liệu.
        #
        # INV-CONN-22 / D-CR94-8 — assert này TRƯỚC ĐÂY vacuous: `empty.get("PM Work
        # Order", {}).get("count", 0) == 0` xanh **cả khi ô biến mất hoàn toàn** khỏi
        # payload (mutation "thôi liệt kê ô rỗng" sống sót). Hợp đồng (ADR §D1 +
        # `05 §III.24.3`) là ô rỗng VẪN có mặt: người dùng phải thấy "0 phiếu bảo trì"
        # chứ không phải một khoảng trắng không giải thích. Nên phải `assertIn` TRƯỚC,
        # rồi mới kiểm giá trị — và kiểm luôn `truncated` là int THUẦN + nhãn VI (một ô
        # rỗng vẫn phải nói được tên tiếng Việt của loại dữ liệu nó đại diện).
        empty = self._items(self._payload("AC Asset", self.asset0))
        self.assertIn(
            "PM Work Order", empty,
            "Ô rỗng PHẢI vẫn có mặt trong payload (ADR §D1) — ô biến mất là 'khoảng "
            "trắng không giải thích' trên UI, và biến chính assert này thành vacuous",
        )
        empty_cell = empty["PM Work Order"]
        self.assertEqual(empty_cell["total"], 0)
        self.assertEqual(empty_cell["items"], [])
        for flag in ("truncated", "total_capped"):
            self.assertIs(type(empty_cell[flag]), int,
                          f"{flag} của ô rỗng phải là int THUẦN (bool ⇒ crash codegen, CR-01)")
            self.assertFalse(isinstance(empty_cell[flag], bool))
            self.assertEqual(empty_cell[flag], 0)
        self.assertTrue(empty_cell["label_vi"], "Ô rỗng vẫn phải có nhãn tiếng Việt")
        self.assertNotEqual(empty_cell["label_vi"], "PM Work Order",
                            "label_vi còn là tên DocType thô ⇒ rò tiếng Anh ra UI (LL-FE-53)")

    # ── TC-CONN-T-21 — nhánh TRẦN (> CAP): 0 seed, tiêm ``list_fn`` giả ───────
    def test_t21_total_capped_is_int_flag_and_marks_lower_bound(self) -> None:
        """INV-CONN-30/31/32 — ``total`` DỪNG ở trần, ``total_capped`` báo **cận dưới**.

        Vì sao TC này tồn tại: fixture của file này tối đa **6** bản ghi mỗi ô ⇒ nhánh
        ``min(len(rows), CONNECTION_COUNT_CAP)`` KHÔNG BAO GIỜ chạy. Gỡ hẳn clamp đi thì
        các TC còn lại **vẫn xanh** (mutation sống sót) — nghĩa là con số duy nhất người
        dùng nhìn thấy ở ô "nhiều bản ghi" đang KHÔNG được test nào canh. Ở đây tiêm
        ``list_fn`` giả nên **0 bản ghi phải seed và 0 truy vấn đọc dòng** — chính vì cổng
        I/O được tiêm (xem docstring ``build_connections``) mà nhánh này test được rẻ.

        Ba mốc khoá luật D4 + D-CR92-2 (ADR §17):
          * 150 dòng (giả định cổng I/O bị nới) ⇒ ``total == 100`` ∧ ``total_capped == 1``
            ⇒ ``total`` là **cận dưới**, FE PHẢI render "100+" chứ không "100";
          * 101 dòng = trần THẬT của ``_row_scoped_rows`` (``CAP + 1``) ⇒ y hệt;
          * 100 dòng chẵn ⇒ ``total_capped == 0`` (predicate là ``len(rows) > CAP``, KHÔNG
            ``>=``) ⇒ "100" là con số CHÍNH XÁC. Lệch một dấu ``=`` ở đây là nói dối 1 bit.

        Kiểu là **int THUẦN**, không ``bool``: viết ``total_capped = len(rows) > CAP`` chạy
        đúng trên Python nhưng phát ``true``/``false`` xuống JSON ⇒ codegen mobile crash
        (CR-01). Vì ``bool`` là subclass của ``int``, oracle phải là ``type(v) is int``.
        """
        cap = conn_service.CONNECTION_COUNT_CAP

        def fake_rows(n: int):
            def _list_fn(linked_dt: str, filters: dict, fields: list[str]) -> list[dict]:
                return [
                    {f: (f"FAKE-{linked_dt}-{i}" if f == "name" else None) for f in fields}
                    for i in range(n)
                ]
            return _list_fn

        for n, expect_capped in ((150, 1), (cap + 1, 1), (cap, 0)):
            payload = conn_service.build_connections(
                "AC Asset", self.asset6, preview_limit=5, list_fn=fake_rows(n)
            )
            item = self._items(payload)["PM Work Order"]
            self.assertEqual(item["total"], cap,
                             f"{n} dòng ⇒ total PHẢI dừng ở trần {cap} (mất clamp = quét bảng "
                             f"lớn rồi in số thật ×19 ô); got {item['total']}")
            self.assertEqual(item["total_capped"], expect_capped,
                             f"{n} dòng ⇒ total_capped PHẢI {expect_capped} — predicate là "
                             "`len(rows) > CAP` (dùng >= sẽ biến 'đúng 100' thành '100+', "
                             "tức bịa thêm dữ liệu)")
            self.assertIs(type(item["total_capped"]), int,
                          "total_capped phải là int THUẦN — `len(rows) > CAP` trả bool ⇒ "
                          "JSON `true` ⇒ crash codegen Dart/Kotlin (CR-01)")
            self.assertFalse(isinstance(item["total_capped"], bool))
            self.assertEqual(item["truncated"], 1,
                             "items bị cắt còn 5 dòng ⇒ truncated PHẢI 1 (cắt IM LẶNG là class-of-bug "
                             "mà SSoT truncation_meta sinh ra để đóng)")
            self.assertEqual(len(item["items"]), 5,
                             "preview PHẢI đúng preview_limit dòng, KHÔNG phải toàn bộ rows")
            self.assertEqual(payload["total"], sum(it["total"] for it in self._all_items(payload)),
                             "data.total (cấp payload) vẫn là TỔNG CỘNG DỒN total mọi ô")

        # INV-CONN-32 — ô ``truncated=0 ∧ total_capped=1`` KHÔNG THỂ tồn tại, kể cả khi
        # người gọi nới preview_limit lên trần cho phép (10): 100 > 10 ⇒ vẫn cắt.
        payload = conn_service.build_connections(
            "AC Asset", self.asset6, preview_limit=cmeta.PREVIEW_LIMIT_MAX,
            list_fn=fake_rows(cap + 1),
        )
        item = self._items(payload)["PM Work Order"]
        self.assertEqual((item["total_capped"], item["truncated"]), (1, 1),
                         "total_capped=1 ⇒ truncated=1 (total==100 > preview_limit ≤ 10)")

    # ── TC-CONN-T-22 — thiếu DocPerm read ⇒ ẨN HẲN ô (không trả nhóm rỗng) ───
    def test_t22_missing_docperm_read_hides_the_cell_entirely(self) -> None:
        """Cổng ``frappe.has_permission(linked_dt, 'read')`` — gỡ cổng thì file này PHẢI ĐỎ.

        Mutation M5 (xoá 2 dòng gate trong ``build_connections``) hiện vẫn để file này
        21/21 xanh — chỉ ``test_connections.py`` (hợp đồng CŨ, không được sửa) bắt được.
        Rủi ro cụ thể: vòng 3 sẽ tỉa các khoá legacy trong file cũ; nếu TC canh cổng nằm
        NHỜ ở đó thì cổng phân quyền mất người canh đúng lúc code bị sửa nhiều nhất.

        Ẩn HẲN (không trả ô ``count: 0``) là hợp đồng: một ô rỗng "gây tò mò" vẫn bộc lộ
        rằng loại dữ liệu đó tồn tại và có liên quan tới hồ sơ này.
        """
        real_has_permission = frappe.has_permission

        def fake_has_permission(*args, **kwargs):
            doctype = args[0] if args else kwargs.get("doctype")
            ptype = kwargs.get("ptype", args[1] if len(args) > 1 else "read")
            if doctype == "PM Work Order" and ptype == "read":
                return False
            return real_has_permission(*args, **kwargs)

        baseline = self._items(self._payload("AC Asset", self.asset6))
        self.assertIn("PM Work Order", baseline,
                      "Control: khi CÓ quyền đọc, ô PHẢI có mặt — nếu không, phép kiểm dưới đây "
                      "pass suông vì lý do khác.")

        frappe.has_permission = fake_has_permission
        try:
            items = self._items(self._payload("AC Asset", self.asset6))
        finally:
            frappe.has_permission = real_has_permission

        self.assertNotIn(
            "PM Work Order", items,
            "Thiếu DocPerm read ⇒ ô PHẢI biến mất HẲN, KHÔNG trả ô count=0 (ô rỗng vẫn bộc lộ "
            "sự tồn tại của loại dữ liệu ngoài quyền — ADR §D1 luật 1).")
        self.assertTrue(
            set(items), "Các ô KHÁC phải còn nguyên — cổng này lọc theo TỪNG doctype, không "
                        "phải tắt cả khối (ẩn nhầm = màn chi tiết trống trơn).")
        for group in self._payload("AC Asset", self.asset6)["groups"]:
            self.assertTrue(group["items"], "Nhóm rỗng KHÔNG được trả về (chỉ append khi có ô).")

    # ── TC-CONN-T-23 / T-24 — deep-link phải LỌC ĐƯỢC THẬT (AC-CR-91) ─────────
    def _sample_record(self, hub: str) -> str:
        """Mã bản ghi để dựng cây cho một hub — ưu tiên fixture của CHÍNH file này.

        Hub không có fixture riêng thì mượn 1 bản ghi bất kỳ (chỉ 1 truy vấn ``name``,
        KHÔNG đọc dòng của các ô — phần đó do ``list_fn`` giả đảm nhiệm). Hub chưa có bản
        ghi nào trên site ⇒ ``""`` và người gọi bỏ qua; phép kiểm phủ-sóng ở cuối mỗi TC
        canh để việc "bỏ qua" không âm thầm biến cả TC thành rỗng.
        """
        seeded = {"AC Asset": self.asset6, "PM Work Order": self.wo6[0]}
        if hub in seeded:
            return seeded[hub]
        rows = frappe.get_all(hub, fields=["name"], limit_page_length=1)
        return rows[0]["name"] if rows else ""

    @staticmethod
    def _internal_link_doctypes(hub: str) -> set[str]:
        """Tập doctype nối bằng liên kết XUÔI trong đồ thị ĐANG CHẠY của hub.

        Đọc ``Meta.get_dashboard_data()`` — CÙNG nguồn ``build_connections`` đọc, nên phủ
        cả cạnh do child table ``links`` trong DB / hook ``override_doctype_dashboards``
        bơm vào (những cạnh mà guard file-driven ``test_doctype_connectivity.py`` không
        nhìn thấy vì nó chỉ đọc ``*_dashboard.py`` trên đĩa).
        """
        return set((dict(frappe.get_meta(hub).get_dashboard_data() or {})
                    .get("internal_links") or {}))

    @staticmethod
    def _fake_list_fn(rows_per_cell: int = 2):
        """Reader giả: mọi ô có dữ liệu, 0 truy vấn đọc dòng (giữ ZERO-COST INV-CONN-6).

        Bắt buộc phải giả: ô ``count == 0`` vẫn phát ``deep_link_filters``, nhưng ô có
        dữ liệu mới là ô FE dựng nút «Xem tất cả» — muốn kiểm đúng ca đó trên MỌI hub mà
        không seed hàng chục bản ghi thì tiêm cổng I/O (khuôn của TC-CONN-T-21).
        """
        def _list_fn(linked_dt: str, filters: dict, fields: list[str]) -> list[dict]:
            return [
                {f: (f"FAKE-{linked_dt}-{i}" if f == "name" else None) for f in fields}
                for i in range(rows_per_cell)
            ]
        return _list_fn

    def _tree_samples(self):
        """(hub, mã bản ghi cha, cây đã dựng, tập doctype liên kết XUÔI) cho MỌI hub."""
        for hub in sorted(conn_service.allowed_source_doctypes()):
            sample = self._sample_record(hub)
            if not sample:
                continue
            payload = conn_service.build_connections(
                hub, sample, preview_limit=cmeta.PREVIEW_LIMIT, list_fn=self._fake_list_fn()
            )
            yield hub, sample, payload, self._internal_link_doctypes(hub)

    def test_t23_deep_link_filters_carry_exactly_one_usable_key(self) -> None:
        """INV-CONN-16 — ô NGƯỢC: đúng 1 khoá ≠ ``name``; ô XUÔI: đúng khoá ``name``.

        Vì sao TC này tồn tại (ADR §13, AC-CR-91): FE dịch khoá fieldname của BE sang khoá
        query mà màn danh sách THẬT SỰ đọc (``listTarget``). Phép dịch đó nhận vào **một**
        khoá; 0 khoá ⇒ trả ``null`` ⇒ nút «Xem tất cả» **biến mất câm lặng**, 2 khoá ⇒
        không biết dịch khoá nào. Cả hai ca đều không TC nào canh trước vòng này:
        ``t15`` chỉ kiểm khoá thuộc allowlist và ``count > 0 ⇒ != {}`` trên MỘT hub.

        Ca hỏng cụ thể mà nó chặn: ``_safe_deep_link`` lọc theo allowlist
        ``_allowed_deep_link_keys()`` — đồ thị này derive từ ``Meta.get_dashboard_data()``
        nên phụ thuộc DB + hook của TỪNG site (INV-CONN-15). Allowlist dựng nhầm phạm vi
        (hoặc stale) sẽ **lọc sạch** khoá hợp lệ ⇒ ô có dữ liệu nhưng ``deep_link_filters
        == {}``. Đó chính là bug production người dùng báo, và nó im lặng tuyệt đối.

        Bồi thêm phần NGỮ NGHĨA (task BE-1) mà ID hình-dạng ở trên chưa nói: khoá đó phải
        là **Link field TỒN TẠI trên doctype đích với ``options`` == hub cha**. Khoá sai
        tên/sai đích không làm vỡ gì cả — nó chỉ khiến danh sách đích lọc ra **0 dòng**,
        trông y hệt "chưa có dữ liệu". Oracle là ``frappe.get_meta`` (schema ĐANG CHẠY),
        khác oracle file-JSON của ``test_doctype_connectivity.py`` nên bắt được cả cạnh do
        DB/hook bơm vào — thứ không nằm trong ``*_dashboard.py``.
        """
        problems: list[str] = []
        covered: list[str] = []
        checked_cells = 0

        for hub, sample, payload, internal in self._tree_samples():
            covered.append(hub)
            for item in self._all_items(payload):
                dt = item["doctype"]
                keys = sorted(item["deep_link_filters"])
                checked_cells += 1
                if dt in internal:
                    if keys != ["name"]:
                        problems.append(
                            f"{hub} → {dt}: ô liên kết XUÔI phải có ĐÚNG khoá ['name'], "
                            f"đang là {keys}"
                        )
                    continue
                if len(keys) != 1 or keys[0] == "name":
                    problems.append(
                        f"{hub} → {dt} (mã cha {sample}): ô liên kết NGƯỢC phải có ĐÚNG 1 "
                        f"khoá lọc ≠ 'name', đang là {keys} ⇒ FE không dịch được ⇒ nút "
                        f"«Xem tất cả» biến mất câm lặng"
                    )
                    continue
                key = keys[0]
                df = frappe.get_meta(dt).get_field(key)
                if df is None:
                    problems.append(
                        f"{hub} → {dt}: khoá '{key}' KHÔNG phải field của '{dt}' ⇒ danh "
                        f"sách đích lọc ra 0 dòng CÂM (trông như 'chưa có dữ liệu')"
                    )
                elif df.fieldtype != "Link" or df.options != hub:
                    problems.append(
                        f"{hub} → {dt}.{key}: fieldtype={df.fieldtype} options={df.options} "
                        f"— phải là Link trỏ '{hub}' thì lọc theo bản ghi cha mới ra dòng"
                    )

        self.assertEqual(problems, [], f"{len(problems)} khoá deep-link không lọc được: {problems}")
        # Chống xanh-giả: bỏ qua hub thiếu bản ghi là hợp lệ, nhưng TC rỗng thì không.
        self.assertLessEqual(
            {"AC Asset", "PM Work Order"}, set(covered),
            f"Hai hub CÓ fixture trong file này phải luôn được kiểm; mới kiểm: {covered}",
        )
        self.assertGreaterEqual(
            checked_cells, 20,
            f"Chỉ kiểm được {checked_cells} ô trên {len(covered)} hub — duyệt cây hỏng "
            f"(đồ thị 12 hub hiện có ~25 ô liên kết NGƯỢC + XUÔI trên riêng AC Asset)",
        )

    def test_t24_reverse_link_value_is_the_parent_record_id(self) -> None:
        """INV-CONN-17 — giá trị khoá deep-link của ô NGƯỢC == mã bản ghi CHA.

        Phép dịch của FE **giữ nguyên value** và chỉ đổi tên khoá. Value sai vì thế không
        cho ra "danh sách không lọc" (ca dở đã biết) mà cho ra **danh sách lọc NHẦM hồ
        sơ** — tệ hơn hẳn, vì nó trông như đã lọc đúng: người dùng đọc phiếu của thiết bị
        khác mà không có dấu hiệu nào. TC-CONN-T-23 canh KHOÁ, TC này canh GIÁ TRỊ; hỏng
        một trong hai đều dẫn tới cùng một màn hình sai.
        """
        problems: list[str] = []
        checked = 0
        for hub, sample, payload, internal in self._tree_samples():
            for item in self._all_items(payload):
                dt = item["doctype"]
                if dt in internal:
                    continue  # ô XUÔI mang mã bản ghi ĐÍCH — t15b đã khoá dạng chuỗi/dấu phẩy
                for key, value in item["deep_link_filters"].items():
                    checked += 1
                    if value != sample:
                        problems.append(
                            f"{hub} → {dt}: deep_link_filters['{key}'] = {value!r} nhưng mã "
                            f"bản ghi cha là {sample!r} ⇒ danh sách đích lọc NHẦM hồ sơ"
                        )
        self.assertEqual(problems, [], f"{len(problems)} deep-link trỏ sai bản ghi cha: {problems}")
        self.assertGreaterEqual(
            checked, 20,
            f"Chỉ kiểm được {checked} khoá — duyệt cây hỏng, TC đang xanh vì rỗng",
        )

    # ── TC-CONN-T-25 / T-26 — `count == drill` CROSS-ENDPOINT (AC-CR-94) ───────
    #
    # Vì sao 2 TC này KHÔNG mock: TC-CONN-T-23/24 chứng minh *khoá và giá trị* của
    # `deep_link_filters`, và test FE chứng minh *bảng dịch khoá*. Không cái nào chứng
    # minh mệnh đề mà người dùng thật sự đọc: **ô báo N thì màn danh sách đích ra đúng N
    # dòng của đúng thiết bị đó**. Mệnh đề đó chỉ đúng khi HAI endpoint độc lập nhìn thấy
    # CÙNG một tập bộ lọc — thứ duy nhất kiểm được bằng cách gọi thật cả hai đầu trong
    # cùng một `frappe.session.user` (D-CR94-2).
    #
    # Cả 'PM Schedule' và 'IMM Calibration Schedule' KHÔNG có
    # `permission_query_conditions` (hooks.py:439-447) ⇒ bất biến ở đây KHÔNG phụ thuộc
    # row-scope; ca DocPerm/vendor là backlog CÓ TÊN (ADR §15.8 — AC-CR-96 và
    # `_RAW_QUERY_UNGATED_BACKLOG`), CẤM biến 2 TC này thành TC an ninh.

    def test_t25_pm_schedule_cell_total_equals_drill_rows(self) -> None:
        """INV-CONN-18 — ô «Lịch bảo trì định kỳ» ↔ ``imm00.list_pm_schedules(asset=X)``.

        Vế "∀ dòng ``asset_ref == X``" là vế KHÔNG được bỏ: hai con số có thể bằng nhau
        mà cùng sai (bộ lọc bị nuốt ở CẢ HAI đầu ⇒ ``1430 == 1430``).

        Vế "có ≥ 1 dòng ``Paused``" khoá D-CR94-3: ô đếm MỌI lịch, nên drill **cấm** tự
        tiêm ``status='Active'``. Tiêm vào thì `total` 3 mà bảng 2 dòng — trông y hệt
        phân trang, và ẩn đúng câu trả lời cho *"vì sao thiết bị này không sinh phiếu
        bảo trì?"*.
        """
        from assetcore.api import imm00 as api_imm00  # noqa: PLC0415 - khuôn cục bộ của file

        cell = self._items(self._payload("AC Asset", self.asset_sched))["PM Schedule"]
        self.assertEqual(cell["total"], 3, "Ô phải đếm CẢ 3 lịch (2 Active + 1 Paused)")
        self.assertEqual(cell["total_capped"], 0, "3 < trần ⇒ total là con số CHÍNH XÁC")

        res = api_imm00.list_pm_schedules(asset=self.asset_sched, page_size=50)
        self.assertTrue(res["success"], res)
        rows = res["data"]["items"]  # envelope {success, data:{items, total, page, page_size}}
        self.assertEqual(
            len(rows), cell["total"],
            f"Ô báo {cell['total']} nhưng drill ra {len(rows)} dòng ⇒ hai đầu đang đọc "
            f"hai tập bộ lọc khác nhau (bất biến count == drill, ADR-IMM00-LIST-SCOPE §4b)",
        )
        self.assertEqual(
            res["data"]["total"], cell["total"],
            "pagination.total của drill cũng phải khớp ô — lệch ở đây là 'header nói 1430, "
            "bảng rỗng' phiên bản nhỏ",
        )
        foreign = [r["name"] for r in rows if r.get("asset_ref") != self.asset_sched]
        self.assertEqual(
            foreign, [],
            f"{len(foreign)} dòng KHÔNG thuộc thiết bị {self.asset_sched} ⇒ danh sách đích "
            f"lọc nhầm/không lọc: {foreign[:3]}",
        )
        self.assertIn(
            "Paused", {r.get("status") for r in rows},
            "Drill tự lọc mất lịch Paused ⇒ phá count == drill theo hướng khó thấy nhất "
            "(D-CR94-3) và ẩn nguyên nhân 'lịch bị tạm dừng'",
        )
        self.assertEqual({r["name"] for r in rows}, set(self.pm_scheds),
                         "Tập dòng drill phải ĐÚNG 3 lịch đã seed, không thừa không thiếu")

    def test_t26_calibration_schedule_cell_total_equals_drill_rows(self) -> None:
        """INV-CONN-19 + INV-CONN-20 — ô «Lịch hiệu chuẩn» ↔ ``imm11.list_calibration_schedules``.

        RED-before (bằng chứng chạy thật ghi ở ADR §15.1 #5): ``_normalize_schedule_filters``
        ``pop("asset")`` VÔ ĐIỀU KIỆN rồi chỉ tiêm lại khi ``_extract_asset_in_scope`` trả
        list; helper đó không nhận shape **vô hướng** ⇒ ``filters={"asset": X}`` **biến
        mất** và endpoint trả TOÀN BỘ lịch của mọi thiết bị. Đó là lỗi câm nhất trong họ
        này: FE gửi đúng, BE nuốt, không ai báo gì.

        Hai nửa của TC:
          * ``{asset: X}`` ⇒ đúng 2 dòng, mọi dòng ``asset == X``, **gồm cả** dòng
            ``is_active = 0`` (D-CR94-3: drill cấm tiêm ``is_active = 1``).
          * ``{asset: X, overdue: 1}`` ⇒ tập con THỰC SỰ (khác rỗng) của tập trên, mọi
            dòng vẫn ``asset == X``: chứng minh GIAO hai chiều — ``overdue`` không xoá
            ``asset`` và ``asset`` không xoá ``overdue`` (INV-CONN-20).
        """
        from assetcore.api import imm11 as api_imm11  # noqa: PLC0415 - khuôn cục bộ của file

        cell = self._items(self._payload("AC Asset", self.asset_sched))["IMM Calibration Schedule"]
        self.assertEqual(cell["total"], 2, "Ô phải đếm CẢ lịch đã tắt (is_active = 0)")
        self.assertEqual(cell["total_capped"], 0)

        res = api_imm11.list_calibration_schedules(
            filters=json.dumps({"asset": self.asset_sched}), page_size=50
        )
        self.assertTrue(res["success"], res)
        # envelope {success, data:{data, pagination}} — KHÁC shape của list_pm_schedules;
        # lấy sai tầng ⇒ len() của dict = số khoá = XANH GIẢ.
        rows = res["data"]["data"]
        self.assertEqual(
            len(rows), cell["total"],
            f"Ô báo {cell['total']} nhưng drill ra {len(rows)} dòng ⇒ BE nuốt bộ lọc "
            f"`asset` (shape vô hướng) hoặc tự tiêm bộ lọc mặc định",
        )
        foreign = [r["name"] for r in rows if r.get("asset") != self.asset_sched]
        self.assertEqual(
            foreign, [],
            f"{len(foreign)} dòng KHÔNG thuộc thiết bị {self.asset_sched} ⇒ nút «Xem tất "
            f"cả» sẽ mở ra danh sách toàn viện: {foreign[:3]}",
        )
        self.assertIn(
            0, {int(r.get("is_active") or 0) for r in rows},
            "Drill tự tiêm is_active=1 ⇒ mất lịch đã tắt (D-CR94-3) và phá count == drill",
        )
        self.assertEqual({r["name"] for r in rows},
                         {self.cal_active_overdue, self.cal_inactive})

        # INV-CONN-20 — GIAO, không clobber theo CẢ HAI chiều.
        both = api_imm11.list_calibration_schedules(
            filters=json.dumps({"asset": self.asset_sched, "overdue": 1}), page_size=50
        )
        self.assertTrue(both["success"], both)
        both_rows = both["data"]["data"]
        self.assertEqual(
            {r["name"] for r in both_rows}, {self.cal_active_overdue},
            "asset ∩ overdue phải ra ĐÚNG lịch đang bật + quá hạn: mất dòng ⇒ asset "
            "clobber overdue; thêm dòng ⇒ overdue clobber asset (một trong hai bị ghi đè câm)",
        )
        self.assertLessEqual(
            {r["name"] for r in both_rows}, {r["name"] for r in rows},
            "Tập giao phải là TẬP CON của tập chỉ-lọc-thiết-bị",
        )
        self.assertTrue(both_rows, "Tập giao rỗng ⇒ phép kiểm ⊆ thành vacuous (D-CR94-8)")
        self.assertEqual(
            [r["name"] for r in both_rows if r.get("asset") != self.asset_sched], [],
            "overdue đã ghi đè khoá asset ⇒ dòng của thiết bị khác lọt vào",
        )

    # ── TC-CONN-T-27 / T-28 — RATIFY cổng I/O bằng GUARD, không bằng lời ───────
    #
    # Hai TC này là ĐIỀU KIỆN HIỆU LỰC của ngoại lệ D-CR92-6 (ADR §17 ·
    # `04_Backend_Design.md §V.7.1` NGOẠI LỆ): lời gọi ORM được phép ở lại
    # `api/connections.py::_row_scoped_rows` **chỉ khi** hai mệnh đề dưới đây đo được.
    # Chúng đóng blocker #2 của run-3 (ADR §V.7.1 xếp `frappe.get_list` vào `services/`
    # ⇄ guard AST của `test_connections.py` soi `api/`) mà KHÔNG dời mã và KHÔNG sửa TC
    # bị đóng băng `test_counts_run_under_session_user_not_administrator`.
    #
    # Ngoại lệ kiến trúc ghi bằng một câu trong docstring thì KHÔNG ĐỎ ĐƯỢC; ở đây nó là
    # hai test có tên, nêu đúng tên trong ADR/Backend Design.

    @staticmethod
    def _called_names(mod) -> list[str]:
        """Tên hàm của MỌI lời gọi trong module (AST — không phải tìm chuỗi).

        Docstring nói "không dùng ``frappe.db.count``" vì thế KHÔNG làm guard đỏ oan, và
        ngược lại không ai lách được guard bằng cách tách chuỗi.
        """
        tree = ast.parse(inspect.getsource(mod))
        return [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]

    def test_t27_service_layer_has_zero_row_reading_orm(self) -> None:
        """INV-CONN-33 — ``services/connections.py`` KHÔNG đọc dòng, bằng 6 tên cụ thể.

        Nếu ai đó dời ORM xuống service "cho khớp §V.7.1 nguyên văn" thì: (a) TC này ĐỎ,
        (b) ``t04`` mất khả năng đếm số lời gọi ``list_fn`` ⇒ ZERO-COST không còn đo được,
        (c) ``t21`` phải monkeypatch ``frappe.get_list`` toàn cục thay vì tiêm 150 dòng
        giả. Đó là lý do ngoại lệ tồn tại — và lý do nó phải có guard.
        """
        called = self._called_names(conn_service)
        offenders = sorted({c for c in called if c in _ROW_READING_ORM})
        self.assertEqual(
            offenders, [],
            f"services/connections.py GỌI {offenders} — tầng nghiệp vụ phải THUẦN, mọi "
            f"lần đọc dòng đi qua cổng I/O `list_fn` do api/ tiêm (D-CR92-6(a))",
        )
        # Assert DƯƠNG TÍNH có kiểm soát: allowlist phải còn dùng được, nếu không guard
        # này biến thành "cấm mọi lần chạm frappe" và ai đó sẽ dọn lây đúng 4 lời gọi
        # vô hại (đọc bản ghi CHA + cổng quyền) xuống api/.
        self.assertIn("frappe.get_doc", called,
                      "Nhánh internal_links đọc CHÍNH bản ghi cha bằng frappe.get_doc — "
                      "được phép (quyền đọc đã kiểm ở api/)")
        self.assertIn("frappe.has_permission", called,
                      "Cổng ẩn ô theo DocPerm read PHẢI ở service (t22 canh) — được phép")

    def test_t28_api_layer_has_exactly_one_get_list_inside_the_port(self) -> None:
        """INV-CONN-34 — ``frappe.get_list`` ở ``api/`` xuất hiện ĐÚNG 1 lần, TRONG cổng.

        "Đúng 1 lần" là vế chống nợ mới (thêm truy vấn thứ hai ở tầng API là quay lại
        khuôn "hai truy vấn = hai cơ hội nói dối"); "trong thân ``_row_scoped_rows``" là
        vế chống ngoại lệ trôi: một lời gọi ORM nằm rải trong ``get_connections`` sẽ vẫn
        thoả "có 1 lần" nhưng không còn là **cổng** nào cả.
        """
        from assetcore.api import connections as api_mod

        tree = ast.parse(inspect.getsource(api_mod))
        hits = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call) and ast.unparse(node.func) == "frappe.get_list"
        ]
        self.assertEqual(
            len(hits), 1,
            f"api/connections.py có {len(hits)} lời gọi frappe.get_list — cổng I/O phải là "
            f"ĐIỂM ĐỌC DUY NHẤT (D-CR92-6(b))",
        )
        port = next(
            (node for node in ast.walk(tree)
             if isinstance(node, ast.FunctionDef) and node.name == "_row_scoped_rows"),
            None,
        )
        self.assertIsNotNone(port, "Không tìm thấy hàm cổng I/O `_row_scoped_rows`")
        self.assertIn(
            id(hits[0]), {id(node) for node in ast.walk(port)},
            "Lời gọi frappe.get_list KHÔNG nằm trong thân `_row_scoped_rows` ⇒ ngoại lệ "
            "cổng I/O đã trôi thành 'truy vấn rải ở tầng API' (D-CR92-6(b))",
        )


    # ── TC-CONN-T-29..34 — AC-CR-105: `create_prefill` LIVE + capability là TOKEN ──
    #
    # Sáu TC dưới đây đóng nợ AC-CR-90(b): «Tạo từ ngữ cảnh cha» hết là nút chết.
    # Quyết định: ADR §18 (D-CR105-1..9) · hợp đồng: `05 §III.24.11` · code shape:
    # `04 §V.10` · bộ TC: `07 §XXI.2`.
    #
    # ⚠️ MỆNH ĐỀ KHÔNG TỒN TẠI (§18 D-CR105-2): `can_create True ⇒ prefill != {}`.
    # Viết nó vào bất kỳ TC nào sẽ ĐỎ ở 3 doctype HỢP LỆ (`Asset Transfer` ·
    # `AC Purchase` · `Service Contract` — màn tạo đọc 0 khoá query) và người sửa tiếp
    # theo sẽ "chữa" bằng cách bịa khoá prefill (`asset_ref`!) hoặc tắt nút. TC nào đỏ
    # theo kiểu đó ⇒ SỬA TC, KHÔNG sửa BE.

    def test_t29_create_keys_are_consistent_and_prefill_is_always_a_dict(self) -> None:
        """INV-CONN105-1 + INV-CONN4-1 (đính chính D-CR105-2) — ba mệnh đề RỜI.

        ``create_prefill`` **luôn có mặt** và luôn là ``dict`` (không bao giờ ``None``):
        khoá optional là một nhánh fallback ở client, và mỗi nhánh fallback là một chỗ
        để hợp đồng lệch âm thầm.

        Ba mệnh đề được assert (KHÔNG phải chuỗi ``⟺`` ba vế — dạng đó tự mâu thuẫn với
        ca hợp lệ, xem D-CR105-2):
          1. ``can_create is False ⟺ create_route_hint == ""`` (biconditional THẬT, D8);
          2. ``can_create is False ⇒ create_prefill == {}``;
          3. vế dương của (2): ``prefill != {} ⇒ can_create is True ∧ hint != ""`` —
             **cấm prefill mồ côi** (nút tắt mà payload vẫn rò mã bản ghi cha ra client
             là dữ liệu không dùng được, và là mầm cho một FE tương lai "tận dụng"
             prefill để tự dựng nút vượt gate).
        """
        checked_hubs: list[str] = []
        checked_cells = 0
        cells_with_prefill = 0
        for hub in sorted(conn_service.allowed_source_doctypes()):
            rows = frappe.get_all(hub, fields=["name"], limit_page_length=1)
            if not rows:
                continue
            parent_name = rows[0]["name"]
            checked_hubs.append(hub)
            for item in self._all_items(self._payload(hub, parent_name)):
                checked_cells += 1
                where = f"{hub} → {item.get('doctype')}"
                prefill = item["create_prefill"]
                self.assertIsInstance(
                    prefill, dict,
                    f"{where}: create_prefill phải là dict (KHÔNG None) — client không "
                    f"dựa được vào khoá thì nhánh fallback lại mọc lên",
                )
                for key, value in prefill.items():
                    self.assertIs(type(key), str, f"{where}: khoá prefill không phải str")
                    self.assertIs(type(value), str,
                                  f"{where}.{key}: value prefill không phải str ⇒ "
                                  f"query-string rác / crash client")
                    self.assertNotEqual(value.strip(), "",
                                        f"{where}.{key}: value prefill rỗng")
                    self.assertNotIn(
                        key, _FORBIDDEN_PREFILL_KEYS,
                        f"{where}: khoá prefill '{key}' là Link fieldname của BE — màn "
                        f"tạo KHÔNG đọc khoá đó ⇒ 'đã điền sẵn' mà ô trống (D-CR105-3)",
                    )
                self.assertLessEqual(
                    len(prefill), 1,
                    f"{where}: prefill vòng này luôn 0 hoặc 1 cặp (ngữ cảnh cha chỉ có "
                    f"MỘT bản ghi) — đang {sorted(prefill)}",
                )
                if prefill:
                    self.assertEqual(
                        list(prefill.values()), [parent_name],
                        f"{where}: value prefill PHẢI là mã bản ghi cha ({parent_name})",
                    )
                    cells_with_prefill += 1

                # (1) biconditional THẬT
                self.assertEqual(
                    item["can_create"], bool(item["create_route_hint"]),
                    f"{where}: can_create lệch create_route_hint (nút chết / route mồ côi)",
                )
                # (2) + (3) — hai chiều của "không có prefill mồ côi"
                if item["can_create"] is False:
                    self.assertEqual(
                        prefill, {},
                        f"{where}: nút TẮT mà vẫn phát prefill ⇒ prefill MỒ CÔI",
                    )
                if prefill != {}:
                    self.assertIs(item["can_create"], True, f"{where}: prefill mồ côi")
                    self.assertNotEqual(item["create_route_hint"], "", f"{where}")

        self.assertLessEqual(
            {"AC Asset", "PM Work Order", "Incident Report"}, set(checked_hubs),
            f"Ba hub CÓ fixture trong file này phải luôn được kiểm; mới kiểm: {checked_hubs}",
        )
        self.assertGreaterEqual(checked_cells, 20,
                                f"Chỉ kiểm được {checked_cells} ô — duyệt cây hỏng")
        # Chống xanh-giả: nếu BE trả `{}` cho MỌI ô thì 3 mệnh đề trên vẫn xanh hết.
        self.assertGreater(
            cells_with_prefill, 0,
            "KHÔNG ô nào có prefill ⇒ 3 mệnh đề trên xanh VACUOUS (hợp đồng vẫn chết)",
        )

    def test_t30_prefill_uses_the_url_query_key_not_the_link_fieldname(self) -> None:
        """INV-CONN105-2 — khoá prefill là khoá URL của FE, KHÔNG phải Link fieldname.

        Hub ``AC Asset`` nối tới 5 doctype tạo được bằng **ba** Link fieldname khác nhau
        (``asset_ref`` cho PM/Sửa chữa/Hồ sơ, ``asset`` cho Hiệu chuẩn/Sự cố) nhưng cả 5
        màn tạo đều đọc **một** khoá query ``asset`` ⇒ đây là chỗ duy nhất phân biệt
        "đúng khoá URL" với "vô tình trùng tên".

        So bằng ``assertEqual`` trên CẢ dict: ``assertIn("asset", prefill)`` xanh cả khi
        BE gửi kèm ``asset_ref`` — đúng thứ vòng này cấm (`07 §XXI.4` mục 1).
        """
        items = self._items(self._payload("AC Asset", self.asset6))
        targets = [
            "PM Work Order", "Asset Repair", "IMM Asset Calibration",
            "Incident Report", "Asset Document",
        ]
        for dt in targets:
            self.assertIn(dt, items, f"Hub AC Asset thiếu ô {dt} — đồ thị hỏng?")
            item = items[dt]
            self.assertIs(item["can_create"], True,
                          f"{dt}: Administrator phải tạo được (tiền đề của TC này)")
            self.assertEqual(
                item["create_prefill"], {"asset": self.asset6},
                f"{dt}: prefill PHẢI là {{'asset': <mã thiết bị>}} — khoá URL mà chính "
                f"màn tạo đọc bằng route.query.asset (D-CR105-3)",
            )
            for forbidden in sorted(_FORBIDDEN_PREFILL_KEYS):
                self.assertNotIn(
                    forbidden, item["create_prefill"],
                    f"{dt}: khoá '{forbidden}' là schema BE ⇒ query rác + lời hứa giả",
                )
        # Bằng chứng hai bản đồ THẬT khác nhau ở đúng ô này (không phải trùng ngẫu nhiên).
        self.assertEqual(
            cmeta.CREATE_CONTEXT["PM Work Order"].parents["AC Asset"], "asset_ref",
            "Link fieldname của PM Work Order là asset_ref — nếu bảng `parents` đổi thì "
            "phép so 'khoá URL ≠ fieldname' mất ý nghĩa",
        )
        self.assertEqual(items["PM Work Order"]["deep_link_filters"],
                         {"asset_ref": self.asset6},
                         "deep_link_filters vẫn dùng Link fieldname — hai khoá cho hai "
                         "mục đích khác nhau, không được gộp")

    def test_t31_prefill_key_follows_the_parent_hub(self) -> None:
        """INV-CONN105-2 — CÙNG doctype đích, BA hub, BA khoá khác nhau.

        ``Asset Repair`` xuất hiện trong đồ thị của cả ``AC Asset`` (khoá ``asset``),
        ``PM Work Order`` (``pm_wo``) và ``Incident Report`` (``incident``). Đây là TC
        duy nhất chứng minh khoá **derive từ ``source_doctype``** chứ không phải hằng
        ``"asset"`` viết cứng (mutation (d) ở `07 §XXI.4`).
        """
        from_pm = self._items(self._payload("PM Work Order", self.wo6[0]))
        self.assertIn("Asset Repair", from_pm, "Đồ thị PM Work Order phải có ô Phiếu sửa chữa")
        self.assertEqual(
            from_pm["Asset Repair"]["create_prefill"], {"pm_wo": self.wo6[0]},
            "Hub PM Work Order ⇒ khoá 'pm_wo' (màn /cm/create đọc route.query.pm_wo); "
            "KHÔNG phải Link fieldname 'source_pm_wo'",
        )
        self.assertNotIn("source_pm_wo", from_pm["Asset Repair"]["create_prefill"])

        from_incident = self._items(self._payload("Incident Report", self.incident))
        self.assertIn("Asset Repair", from_incident,
                      "Đồ thị Incident Report phải có ô Phiếu sửa chữa")
        self.assertEqual(
            from_incident["Asset Repair"]["create_prefill"], {"incident": self.incident},
            "Hub Incident Report ⇒ khoá 'incident'; KHÔNG phải fieldname 'incident_report'",
        )
        self.assertNotIn("incident_report", from_incident["Asset Repair"]["create_prefill"])

        from_asset = self._items(self._payload("AC Asset", self.asset6))
        keys_by_hub = {
            "AC Asset": set(from_asset["Asset Repair"]["create_prefill"]),
            "PM Work Order": set(from_pm["Asset Repair"]["create_prefill"]),
            "Incident Report": set(from_incident["Asset Repair"]["create_prefill"]),
        }
        self.assertEqual(
            keys_by_hub, {"AC Asset": {"asset"}, "PM Work Order": {"pm_wo"},
                          "Incident Report": {"incident"}},
            f"Ba hub PHẢI cho ba khoá khác nhau cho cùng doctype đích: {keys_by_hub}",
        )

    def test_t32_create_screens_without_query_keys_get_empty_prefill(self) -> None:
        """INV-CONN4-1 + D-CR105-4 — "thà không prefill còn hơn hứa giả" (3 lớp ca).

        (a) Màn tạo đọc **0** khoá query (``Asset Transfer`` → ``/asset-transfers/new``):
            ``can_create`` có thể True mà prefill ``{}`` ⇒ **KHÔNG** assert can_create ở
            đây (nó phụ thuộc DocPerm của người chạy test);
        (b) Cặp (đích, cha) không có khoá dù màn tạo đọc khoá khác: hub ``PM Work Order``
            → ô «Phiếu hiệu chuẩn» (``/calibration/new`` đọc ``asset``/``schedule``,
            **không** đọc ``pm_wo``);
        (c) Liên kết **XUÔI** (``internal_links``): nút TẮT hoàn toàn — cả ba khoá.
        """
        from_asset = self._items(self._payload("AC Asset", self.asset6))
        self.assertIn("Asset Transfer", from_asset)
        self.assertEqual(
            from_asset["Asset Transfer"]["create_prefill"], {},
            "/asset-transfers/new KHÔNG đọc khoá query nào ⇒ prefill {} (nút vẫn sống, "
            "chỉ không điền sẵn) — bịa khoá 'cho có' là lời hứa giả",
        )
        self.assertEqual(
            cmeta.CREATE_CONTEXT["Asset Transfer"].query_keys, {},
            "Bảng query_keys của Asset Transfer phải TRỐNG (D-CR4-5)",
        )

        from_pm = self._items(self._payload("PM Work Order", self.wo6[0]))
        self.assertIn("IMM Asset Calibration", from_pm)
        self.assertEqual(
            from_pm["IMM Asset Calibration"]["create_prefill"], {},
            "Hub PM Work Order → ô Phiếu hiệu chuẩn: màn /calibration/new không đọc "
            "'pm_wo' ⇒ prefill {} (ca hợp lệ, ADR §18.7 backlog P2-fe)",
        )

        for internal_dt in ("AC Asset", "PM Schedule"):
            cell = from_pm[internal_dt]
            self.assertIs(cell["can_create"], False,
                          f"{internal_dt}: liên kết XUÔI không bao giờ được mời tạo")
            self.assertEqual(cell["create_route_hint"], "")
            self.assertEqual(cell["create_prefill"], {},
                             f"{internal_dt}: nhóm internal_links phải sạch cả prefill")

    def test_t33_create_capability_tokens_bind_to_the_same_doctype_create(self) -> None:
        """INV-CONN4-2 — token trỏ ĐÚNG ``(doctype, "create")``, không lệch một bit.

        ``rbac.can(cap)`` với cap **chưa có** trong ``CAPABILITY_MAP`` trả ``False`` IM
        LẶNG (stale-safe, ``rbac.py:183-185``) ⇒ khai sai một chữ là nút biến mất trên
        toàn hệ thống mà **không test nào đỏ**. Guard này chặn đúng ca đó.
        """
        from assetcore.services.shared import rbac

        self.assertEqual(
            len(cmeta.CREATE_CAPABILITY), 5,
            f"CREATE_CAPABILITY phải khai ĐÚNG 5 doctype (ADR §12 D-CR4-2); đang "
            f"{sorted(cmeta.CREATE_CAPABILITY)}",
        )
        for dt, token in sorted(cmeta.CREATE_CAPABILITY.items()):
            self.assertIn(token, rbac.CAPABILITY_MAP,
                          f"{dt}: token '{token}' KHÔNG có trong CAPABILITY_MAP ⇒ "
                          f"rbac.can trả False im lặng ⇒ nút chết toàn hệ thống")
            self.assertEqual(
                rbac.CAPABILITY_MAP[token], (dt, "create"),
                f"{dt}: token '{token}' bind tới {rbac.CAPABILITY_MAP[token]} — phải là "
                f"('{dt}', 'create'), nếu không gate NÓI DỐI",
            )
            self.assertIn(dt, cmeta.CREATE_CONTEXT,
                          f"{dt}: khai token cho doctype KHÔNG có màn tạo")
        self.assertEqual(
            _CREATE_CAPABILITY_ABSTENTIONS & set(cmeta.CREATE_CAPABILITY), set(),
            "Ba doctype này CỐ Ý không khai token (route tạo gác cap trỏ doctype KHÁC — "
            "ADR §12 D-CR4-2): khai thêm 'cho đủ' là đẻ nút mà route-guard chặn. Đọc "
            "ADR §12.9 + §18.7 trước khi bổ sung.",
        )
        self.assertLessEqual(set(cmeta.CREATE_CAPABILITY), set(cmeta.CREATE_CONTEXT))

    def test_t34_create_capability_parity_three_points(self) -> None:
        """INV-CONN4-3 — parity 3 điểm, cả ba **DERIVE từ nguồn**, parse fail-CLOSED.

        (1) chuỗi cap tại **chính hàm tạo** của module API (AST, bảng neo
            ``_CAP_PARITY_ANCHORS``);
        (2) ``connection_meta.CREATE_CAPABILITY[dt]``;
        (3) ``meta.requiredCapabilities`` của route ``CREATE_CONTEXT[dt].route`` đọc từ
            ``frontend/src/router/index.ts``.

        Viết 3 chuỗi hằng cạnh nhau rồi so với nhau là **chép**, không phải parity: luôn
        xanh, không bao giờ bắt được drift (`07 §XXI.4` mục 3). Và ``routeAccess.ts``
        **không** được regex từ Python — ``:141`` viết ``'doc' + 'ument.write'``.
        """
        self.assertEqual(
            set(_CAP_PARITY_ANCHORS), set(cmeta.CREATE_CAPABILITY),
            "Bảng neo parity phải phủ ĐÚNG tập doctype khai token — thêm token mà quên "
            "neo = thêm cap không ai canh",
        )
        for dt, (module_name, func_name, form) in sorted(_CAP_PARITY_ANCHORS.items()):
            api_cap = _api_create_capability(module_name, func_name, form)
            meta_cap = cmeta.CREATE_CAPABILITY[dt]
            route = cmeta.CREATE_CONTEXT[dt].route
            route_caps = _route_required_capabilities(route)

            self.assertEqual(
                api_cap, meta_cap,
                f"{dt}: cap ở {module_name}::{func_name} = '{api_cap}' nhưng "
                f"CREATE_CAPABILITY = '{meta_cap}' ⇒ ô liên quan gác bằng token KHÁC với "
                f"đường ghi THẬT (khuôn 'RBAC dead-gate')",
            )
            self.assertIn(
                meta_cap, route_caps,
                f"{dt}: route '{route}' gác {route_caps} nhưng CREATE_CAPABILITY = "
                f"'{meta_cap}' ⇒ BE mời tạo rồi route-guard FE đá ra /unauthorized",
            )
            self.assertEqual(
                route_caps, [meta_cap],
                f"{dt}: route '{route}' khai {route_caps} — vòng này chỉ hỗ trợ route "
                f"gác ĐÚNG 1 cap; khai thêm ⇒ phải mở rộng ADR §18 D-CR105-6 trước",
            )

    def test_t35_capability_denial_kills_the_prefill_too(self) -> None:
        """TC-BE-CONN4-08 — vị-từ P3 (capability) từ chối ⇒ prefill cũng phải TRỐNG.

        Vì sao cần TC riêng thay vì tin ``t29``: ``t29`` chạy dưới **Administrator**, ở đó
        P3 **luôn** True ⇒ mutation "tính prefill TRƯỚC khi kiểm quyền" (bẫy 1 của
        `04 §V.10.3`) sống sót toàn bộ suite. Đây là oracle DUY NHẤT của **prefill mồ côi
        trên đường capability**: nút tắt vì thiếu quyền mà payload vẫn mang mã bản ghi cha
        ra client.

        Hai nhánh, cố ý:
          (a) **xác định** — thay ``create_capability_allows`` bằng vị-từ luôn False. Đây
              là điểm chèn ĐÚNG: đi qua ``get_connections`` THẬT (đủ 4 vị-từ, đủ payload)
              mà không phụ thuộc DocPerm của site. Kèm phép kiểm KHÔNG-vacuous: cùng hub
              đó **không** patch phải có ≥ 1 ô ``can_create`` True.
          (b) **DocPerm thật** — user chỉ có base role (khuôn ``t17``). Nhánh này yếu hơn
              (ô mà user không có DocPerm *read* bị ẩn HẲN ở tầng trên nên không quan sát
              được) nên nó **bổ sung**, không thay thế (a).
        """
        baseline = self._all_items(self._payload("AC Asset", self.asset6))
        self.assertTrue(
            [it for it in baseline if it["can_create"]],
            "Tiền đề của TC: Administrator phải có ≥ 1 ô tạo được, nếu không nhánh (a) "
            "xanh VACUOUS (mọi ô đã False từ trước khi patch)",
        )

        real_predicate = conn_service.create_capability_allows
        conn_service.create_capability_allows = lambda target: False
        try:
            denied = self._all_items(self._payload("AC Asset", self.asset6))
        finally:
            conn_service.create_capability_allows = real_predicate

        self.assertEqual(len(denied), len(baseline),
                         "Số ô KHÔNG được đổi khi thiếu quyền TẠO (ô vẫn hiện, chỉ tắt nút)")
        for item in denied:
            self.assertFalse(item["can_create"], f"{item['doctype']}: P3 False mà nút vẫn bật")
            self.assertEqual(item["create_route_hint"], "", f"{item['doctype']}")
            self.assertEqual(
                item["create_prefill"], {},
                f"{item['doctype']}: nút TẮT vì thiếu quyền mà vẫn rò prefill "
                f"{item['create_prefill']} ⇒ PREFILL MỒ CÔI (mã bản ghi cha ra client "
                f"trong khi client không có đường hợp lệ để dùng)",
            )

        email = self._ensure_limited_user()
        frappe.set_user(email)
        try:
            res = get_connections("AC Asset", self.asset6)
        finally:
            frappe.set_user("Administrator")
        if not res["success"]:
            self.assertEqual(res["code"], "FORBIDDEN")
            return
        for item in self._all_items(res["data"]):
            self.assertFalse(item["can_create"],
                             f"{item['doctype']}: quảng cáo nút tạo cho user không có quyền")
            self.assertEqual(item["create_route_hint"], "")
            self.assertEqual(item["create_prefill"], {},
                             f"{item['doctype']}: prefill mồ côi trên đường DocPerm thật")

    def test_t36_untokened_doctypes_keep_the_has_permission_fallback(self) -> None:
        """TC-BE-CONN4-09 — 3 doctype không khai token đi nhánh ``frappe.has_permission``.

        Chứng minh D-CR105-5 ("đổi ĐƯỜNG THỰC THI, KHÔNG đổi hành vi hôm nay") bằng cách
        rỗng hoá ``CREATE_CAPABILITY`` — tức ép **mọi** doctype đi nhánh fallback — rồi so
        payload với bản có bảng đầy đủ: hai payload PHẢI y hệt. Nếu lệch, nghĩa là
        ``rbac.can(token)`` và ``has_permission(dt, "create")`` đang cho hai kết quả khác
        nhau ⇒ token bind sai (guard t33 phải bắt trước), hoặc helper đã đổi ngữ nghĩa.

        Vòng này KHÔNG được đổi trạng thái nút của bất kỳ ô nào trên UI (`07 §XXI` —
        "ai chấm 'không thấy khác gì' là FAIL thì đang chấm sai tiêu chí").
        """
        with_tokens = self._payload("AC Asset", self.asset6)
        real_table = cmeta.CREATE_CAPABILITY
        cmeta.CREATE_CAPABILITY = {}
        try:
            fallback_only = self._payload("AC Asset", self.asset6)
        finally:
            cmeta.CREATE_CAPABILITY = real_table

        self.assertEqual(
            [(i["doctype"], i["can_create"], i["create_route_hint"], i["create_prefill"])
             for i in self._all_items(with_tokens)],
            [(i["doctype"], i["can_create"], i["create_route_hint"], i["create_prefill"])
             for i in self._all_items(fallback_only)],
            "Đường token và đường has_permission cho ra KHÁC nhau ⇒ D-CR105-5 bị vi phạm "
            "(vòng này chỉ siết ràng buộc, không được đổi hành vi)",
        )
        # Ba doctype cố ý không khai token PHẢI thật sự đi nhánh fallback (không phải
        # "trùng kết quả vì bảng rỗng"): helper trả True cho chúng dưới Administrator.
        for dt in sorted(_CREATE_CAPABILITY_ABSTENTIONS):
            self.assertNotIn(dt, cmeta.CREATE_CAPABILITY)
            self.assertIs(
                conn_service.create_capability_allows(dt),
                bool(frappe.has_permission(dt, ptype="create")),
                f"{dt}: nhánh fallback phải KHỚP frappe.has_permission (hành vi cũ)",
            )

    def test_t37_decommissioned_asset_advertises_nothing_at_all(self) -> None:
        """TC-BE-CONN4-11 — cổng vòng đời chặn ⇒ **cả ba** khoá tắt, kể cả prefill.

        ``t19`` đã khoá vế ``can_create`` của cổng này; TC này thêm vế ``create_prefill``:
        cổng vòng đời là ``return`` SỚM NHẤT của ``_create_affordance`` nên nếu ai đó
        tính prefill **trước** nó (bẫy 1 `04 §V.10.3`), payload sẽ rò mã thiết bị đã
        thanh lý ra client trong khi mọi nút đều tắt.

        Cổng vòng đời vòng này GIỮ NGUYÊN (chặn-tất ``BLOCKED_FOR_WO``) — vị-từ
        per-doctype là ``AC-CR-90(c)``, ADR §18.6 ⇒ QA **không** chấm thiếu ở đây.
        """
        original = frappe.db.get_value("AC Asset", self.asset6, "lifecycle_status")
        # Fixture-only: đặt thẳng trạng thái để kiểm CỔNG HIỂN THỊ; nghiệp vụ THẬT đi qua
        # transition_asset_status (đường thanh lý IMM-14 có gate riêng) — khuôn của t19.
        frappe.db.set_value("AC Asset", self.asset6, "lifecycle_status", "Decommissioned",
                            update_modified=False)
        frappe.db.commit()
        try:
            cells = self._all_items(self._payload("AC Asset", self.asset6))
            self.assertTrue(cells, "Thiết bị đã thanh lý vẫn phải trả cây (chỉ tắt nút)")
            for item in cells:
                self.assertFalse(item["can_create"], f"{item['doctype']}")
                self.assertEqual(item["create_route_hint"], "", f"{item['doctype']}")
                self.assertEqual(
                    item["create_prefill"], {},
                    f"{item['doctype']}: cổng vòng đời đã chặn mà prefill vẫn lọt ra "
                    f"⇒ prefill tính TRƯỚC cổng (bẫy 1, `04 §V.10.3`)",
                )
        finally:
            frappe.db.set_value("AC Asset", self.asset6, "lifecycle_status", original,
                                update_modified=False)
            frappe.db.commit()

    def test_t34b_parity_parser_is_fail_closed(self) -> None:
        """`07 §XXI.4` mục 3 — parser của t34 phải **ĐỎ** khi không phân giải được.

        Một parser trả "không tìm thấy" rồi ``continue`` là guard XANH GIẢ: nó sẽ im lặng
        khi ai đó đổi tên hàm tạo hay xoá route. Ở đây ba đường thất bại được **gọi
        thẳng** để chứng minh chúng raise chứ không degrade.
        """
        with self.assertRaises(AssertionError):
            _api_create_capability("assetcore.api.imm08", "khong_ton_tai_o_dau_ca", "require")
        with self.assertRaises(AssertionError):
            _api_create_capability("assetcore.api.imm12", "report_incident", "const:_CAP_KHONG_CO")
        with self.assertRaises(AssertionError):
            _route_required_capabilities("/duong-dan-khong-ton-tai")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
