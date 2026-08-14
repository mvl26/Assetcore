# assetcore/tests/test_rowscope_scope_guard.py
# Copyright (c) 2026, AssetCore Team
"""Guard tĩnh cho hợp đồng row-scope (ADR-IMM00-LIST-SCOPE §8.3/§8.3b/§8.4).

Vì sao là guard TĨNH (AST) chứ không chỉ test hành vi: ma trận §8.4 liệt kê thủ
công 16 call site, nhưng repo có ~55 chỗ gọi ``.list(``. Không có gì chặn một vòng
sau lặng lẽ thêm ``scope="internal"`` (bỏ MỌI kiểm tra quyền) vào một endpoint
người-dùng, hoặc thêm entrypoint đọc mới quên bọc ``run_rowscoped`` → client nhận
500/dispatcher-403 thay vì Error envelope. 3 guard dưới đây bắt CẢ HAI lớp rot đó
tại thời điểm sửa code, không đợi tới lúc lộ dữ liệu ở production.

Bối cảnh lỗi đã xảy ra (2026-07-25):
  * ``scope="system"`` từng bỏ CẢ row-scope LẪN DocPerm read cấp vai-trò ⇒ user chỉ
    có role ``PM User`` đọc được toàn bộ ``Asset Repair`` (OWASP A01).
  * ``count_overdue_pm`` chuyển sang ``count_with_or`` (permission-aware) ⇒
    ``get_dashboard_stats`` ném ``frappe.PermissionError`` trần = 500 câm.

Run: bench --site miyano run-tests --app assetcore \
     --module assetcore.tests.test_rowscope_scope_guard
"""
from __future__ import annotations

import ast
import pathlib

import frappe
from frappe.tests.utils import FrappeTestCase

from assetcore.repositories.base import _LIST_SCOPES, BaseRepository
from assetcore.tests._helpers.paths import APP_ROOT

_APP_ROOT = pathlib.Path(APP_ROOT)
_SCAN_DIRS = ("services", "api", "repositories")

# ── Allowlist call site KHÔNG chạy scope="user" ──────────────────────────────
# Mỗi entry = (module, function, scope) và PHẢI có hàng tương ứng trong ma trận
# ADR-IMM00-LIST-SCOPE §8.4. Thêm entry mới = nới quyền ⇒ phải sửa ADR trước
# (BA ratify), không phải "sửa test cho xanh".
#   scope="system"   → bỏ ROW-scope, GIỮ DocPerm read cấp vai-trò (§8.3b)
#   scope="internal" → bỏ CẢ HAI: chỉ cho scheduler / domain-logic / enrich-nhãn
_ALLOWED_NON_USER_SCOPES: set[tuple[str, str, str]] = {
    # system — device/plan-centric + KPI kỳ báo cáo (D6), vẫn role-gated
    ("services/imm08.py", "get_calendar", "system"),          # P3
    ("services/imm08.py", "get_dashboard_stats", "system"),   # P4 + P5
    ("services/imm09.py", "get_asset_history", "system"),     # R5
    ("services/imm11.py", "get_due_calibrations", "system"),  # A4
    # internal — KHÔNG có client để hiển thị 403 / KHÔNG phải bề mặt phân quyền
    ("services/imm09.py", "check_repair_sla_breach", "internal"),      # R1 scheduler
    ("services/imm09.py", "check_repair_overdue", "internal"),         # R2 scheduler
    ("services/notifications.py", "run_sla_breach_scan", "internal"),  # R6 scheduler
    ("services/imm11.py", "perform_lookback_assessment", "internal"),  # A1 domain-logic
    ("services/imm11.py", "list_schedules", "internal"),               # A2 enrich-nhãn
    ("services/imm11.py", "list_calibrations", "internal"),            # A3 enrich-nhãn
    ("services/imm05.py", "list_documents", "internal"),               # A5 enrich-nhãn
    # A6 (CR-75) — `get_asset_documents` chạy HAI truy vấn, HAI vai (05 §2.7.a B8):
    #   V (hiển thị) scope="user" CHẠY TRƯỚC ⇒ role-gate/row-scope KHÔNG bị nới,
    #     user thiếu DocPerm read vẫn nhận PermissionError → 403 in-envelope.
    #   C (tính toán) scope="internal": tỷ lệ tuân thủ là sự thật của TỔ CHỨC, không
    #     phụ thuộc người xem (BR-05-20 / ADR-IMM05-03) ⇒ aggregate nội bộ, KHÔNG
    #     phải bề mặt phân quyền. `hidden_count` bộc lộ số bản bị ẩn.
    #   ⚠ [BA] mirror dòng này vào ma trận ADR-IMM00-LIST-SCOPE §8.4 (ratify đã có ở
    #     docs/imm-05/05_API_Specification.md §2.7.a B8, ADR chung chưa cập nhật).
    ("services/imm05.py", "get_asset_documents", "internal"),          # A6 aggregate org-truth
}

# Entrypoint đọc = hàm public tên list_*/get_* trong services/ — bề mặt client.
_ENTRYPOINT_PREFIXES = ("list_", "get_")

# ── G4 — raw query TRỰC TIẾP trên DocType row-scoped ────────────────────────
# G1–G3 chỉ nhìn thấy call site đi qua ``*Repo.list``. Endpoint gọi THẲNG
# ``frappe.get_all`` / ``frappe.db.count`` trên một DocType có
# ``permission_query_conditions`` thì **vô hình** với 3 guard đó — đúng lỗ đã lọt
# 2026-07-25: ``imm12.get_asset_incident_history`` phục vụ ``Incident Report`` cho
# persona 0-DocPerm-read trong khi 2 anh em cùng bộ-ba (imm08/imm09) đã gate, và
# suite guard vẫn 4 OK.
_RAW_QUERY_FUNCS = {
    ("frappe", "get_all"),
    ("frappe", "db", "count"),
    ("frappe", "db", "get_all"),
}
# Hàm được coi là ĐÃ gate role khi gọi một trong các helper này (đều resolve về
# ``frappe.has_permission`` — cap-SSoT). ``frappe.get_list`` KHÔNG tính: nó chỉ
# permission-aware cho CHÍNH truy vấn đó, không gate truy vấn ``get_all`` khác
# trong cùng hàm (đây đúng là mẫu lệch count-vs-rows đã biết).
_ROLE_GATE_CALLS = {"assert_doctype_read_permission", "require", "can", "require_role"}

# Backlog ĐÃ BIẾT (P1 — cần [BA] ratify từng dòng: device-centric role-gate hay
# row-scope thật). Guard chỉ chặn **THÊM MỚI**: entry biến mất = đã sửa (tin vui,
# KHÔNG fail build). TUYỆT ĐỐI không thêm dòng mới để "cho test xanh".
#
# AC-CR-98 (2026-07-30) — ĐÃ XOÁ ``("services/imm04.py", "list_commissioning")``:
# `total` đi `count_with_or` + `records` đi `frappe.get_list` (CÙNG engine, cùng
# `asset_commissioning_query`) + gate role tường minh `assert_doctype_read_permission`
# ⇒ 17 → 16 mục. Trần dưới đây khoá chiều: allowlist CHỈ-GIẢM.
_RAW_QUERY_UNGATED_BACKLOG: set[tuple[str, str]] = {
    ("services/imm04.py", "get_dashboard_stats"),
    ("services/imm04.py", "list_my_pending_approvals"),
    ("services/imm08.py", "get_calendar"),
    ("services/imm08.py", "get_due_pm_schedules"),
    ("services/imm12.py", "list_incidents"),
    ("services/imm12.py", "get_incident_stats"),
    ("services/imm12.py", "get_dashboard"),
    ("api/dashboard.py", "get_overview"),
    ("api/imm00.py", "get_asset_kpi"),
    ("api/imm00.py", "list_audit_trail"),
    ("api/imm00.py", "list_incidents"),
    ("api/imm00.py", "list_pm_schedules"),
    ("api/imm00.py", "list_assets_depreciation"),
    ("api/imm00.py", "get_depreciation_stats"),
    ("api/imm00.py", "get_depreciation_by_category"),
    ("api/purchase.py", "get_purchase_commissionings"),
}


# ── G5 — GET-detail đọc doc row-scoped mà KHÔNG gate (CR-74, ADR §9.8) ──────
# G1–G4 chỉ nhìn `*Repo.list` / raw-query. Đường **detail** (`<X>Repo.get(` /
# `frappe.get_doc(`) hoàn toàn VÔ HÌNH với cả 4 — đúng lỗ đã lọt của CR-74:
# `frappe.get_doc` KHÔNG gọi `check_permission` (frappe/model/document.py:36) ⇒ hook
# `has_permission` đã đăng ký ở hooks.py:448-455 chưa bao giờ chạy trên đường đọc
# chi tiết, và DocPerm read cấp vai-trò cũng không được kiểm.
_DETAIL_GATE_CALLS = _ROLE_GATE_CALLS | {"assert_can_read_doc"}

# Backlog ĐÃ BIẾT (ADR §9.9 B10 — mỗi dòng cần [BA] ratify row-scope trước khi gate).
# Allowlist CHỈ-GIẢM: entry biến mất = đã sửa (tin vui, KHÔNG fail build).
# TUYỆT ĐỐI KHÔNG thêm dòng mới để "cho test xanh" — thêm = mở lại lỗ IDOR-đọc.
_DETAIL_READ_UNGATED_BACKLOG: set[tuple[str, str]] = {
    ("services/imm04.py", "get_form_context"),
    ("services/imm04.py", "get_barcode_lookup"),
}

# G5b — 4 op C6-DETAIL nêu ĐÍCH DANH. Cần vế "named" vì G5a (quét theo
# `hooks.permission_query_conditions`) KHÔNG nhìn thấy:
#   * `services/imm11.py::get_calibration` — `IMM Asset Calibration` chưa có hook (D10);
#   * `services/imm12.py::get_incident_detail` — load doc qua helper `_get_incident`.
_CR74_NAMED_DETAIL_GATES: dict[tuple[str, str], str] = {
    ("services/imm08.py", "get_work_order"): "PM Work Order",
    ("services/imm09.py", "get_work_order"): "Asset Repair",
    ("services/imm11.py", "get_calibration"): "IMM Asset Calibration",
    ("services/imm12.py", "get_incident_detail"): "Incident Report",
}

# CR-76 (BR-04-16 / ADR-IMM-04-07) — bề mặt đọc-chi-tiết KHÔNG mang tiền tố `get_`.
# G5a chỉ quét `get_*` ⇒ `evaluate_gate_status` (thẻ cổng G01–G06 của 1 phiếu) hoàn
# toàn vô hình với nó, dù nó load nguyên bản ghi `Asset Commissioning` row-scoped.
# Vế NAMED là thứ duy nhất ghim được. Đặt tách khỏi `_CR74_*` để mỗi CR giữ nguyên
# lô của mình; G5b chấm trên HỢP của hai map.
_CR76_NAMED_DETAIL_GATES: dict[tuple[str, str], str] = {
    ("services/imm04.py", "evaluate_gate_status"): "Asset Commissioning",
}

_NAMED_DETAIL_GATES: dict[tuple[str, str], str] = {
    **_CR74_NAMED_DETAIL_GATES,
    **_CR76_NAMED_DETAIL_GATES,
}


def _rowscoped_doctypes() -> set[str]:
    """DocType có ``permission_query_conditions`` — đọc từ hooks (SSoT, KHÔNG chép tay)."""
    from assetcore import hooks

    return set(hooks.permission_query_conditions.keys())


def _repo_doctype_map() -> dict[str, str]:
    """``{<X>Repo: DOCTYPE}`` — đọc từ chính lớp repository (SSoT, KHÔNG chép tay).

    Cần vì ``RepairRepo.get(name)`` KHÔNG mang tên DocType ở call site: nó nằm trong
    ``DOCTYPE`` của lớp. Không có map này thì guard tĩnh không thể biết một
    ``*Repo.get`` đang chạm DocType row-scoped hay không.
    """
    import importlib
    import pkgutil

    import assetcore.repositories as pkg

    out: dict[str, str] = {}
    for mod_info in pkgutil.iter_modules(list(pkg.__path__)):
        mod = importlib.import_module(f"assetcore.repositories.{mod_info.name}")
        for nm, obj in vars(mod).items():
            if (isinstance(obj, type) and issubclass(obj, BaseRepository)
                    and obj is not BaseRepository and getattr(obj, "DOCTYPE", "")):
                out[nm] = obj.DOCTYPE
    return out


def _detail_load_hits(fn_node: ast.FunctionDef, consts: dict[str, str],
                      repo_map: dict[str, str], rowscoped: set[str]) -> set[str]:
    """DocType row-scoped được LOAD nguyên bản ghi trong thân hàm (không qua gate nào)."""
    hits: set[str] = set()
    for n in ast.walk(fn_node):
        if not isinstance(n, ast.Call):
            continue
        d = _dotted(n.func)
        if d and len(d) == 2 and d[1] == "get" and d[0] in repo_map:
            if repo_map[d[0]] in rowscoped:
                hits.add(repo_map[d[0]])
        if d == ("frappe", "get_doc") and n.args:
            arg = n.args[0]
            dt = arg.value if isinstance(arg, ast.Constant) else consts.get(getattr(arg, "id", ""))
            if dt in rowscoped:
                hits.add(dt)
    return hits


def _gate_calls(fn_node: ast.FunctionDef) -> set[str]:
    """Tên hàm gate quyền được gọi TRONG THÂN hàm (không tính decorator)."""
    found: set[str] = set()
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Call):
            d = _dotted(n.func)
            if d and d[-1] in _DETAIL_GATE_CALLS:
                found.add(d[-1])
    return found


def _dotted(node) -> tuple[str, ...] | None:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return tuple(reversed(parts))
    return None


def _module_str_consts(tree: ast.Module) -> dict[str, str]:
    """Hằng chuỗi cấp module (vd ``_DT_INCIDENT = "Incident Report"``) để resolve tên DocType."""
    out: dict[str, str] = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Constant) \
                and isinstance(n.value.value, str):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = n.value.value
    return out


def _raw_rowscoped_hits(fn_node: ast.FunctionDef, consts: dict[str, str],
                        rowscoped: set[str]) -> set[str]:
    """DocType row-scoped bị truy vấn RAW (bỏ mọi permission) trong thân hàm."""
    hits: set[str] = set()
    for n in ast.walk(fn_node):
        if not isinstance(n, ast.Call) or not n.args:
            continue
        if _dotted(n.func) not in _RAW_QUERY_FUNCS:
            continue
        arg = n.args[0]
        dt = arg.value if isinstance(arg, ast.Constant) else consts.get(getattr(arg, "id", ""))
        if dt in rowscoped:
            hits.add(dt)
    return hits


def _has_role_gate(fn_node: ast.FunctionDef) -> bool:
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Call):
            d = _dotted(n.func)
            if d and d[-1] in _ROLE_GATE_CALLS:
                return True
    return False

# Helper chỉ CHUYỂN TIẾP `scope` xuống Repo.list (keyword bắt buộc) — audit ở caller.
_PASSTHROUGH_HELPER_PREFIXES = ("_fetch_all_",)


def _iter_module_functions():
    """Yield (rel_path, FunctionDef) cho mọi hàm top-level trong vùng quét."""
    for sub in _SCAN_DIRS:
        for path in sorted((_APP_ROOT / sub).glob("*.py")):
            rel = f"{sub}/{path.name}"
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    yield rel, node


def _repo_list_scopes(fn_node: ast.FunctionDef) -> list[str]:
    """Scope của mọi lời gọi ``<X>Repo.list(...)`` **và** helper pass-through.

    ``_fetch_all_*`` (imm08/imm09) chỉ chuyển tiếp ``scope`` xuống Repo (keyword
    BẮT BUỘC, không default ẩn) ⇒ audit phải chấm ở CALLER, còn trong thân helper
    giá trị là tên tham số → ``"<passthrough>"`` (hợp lệ, không phải typo).
    """
    params = {a.arg for a in list(fn_node.args.args) + list(fn_node.args.kwonlyargs)}
    found: list[str] = []
    for n in ast.walk(fn_node):
        if not isinstance(n, ast.Call):
            continue
        func = n.func
        is_repo_list = (isinstance(func, ast.Attribute) and func.attr == "list"
                        and isinstance(func.value, ast.Name)
                        and func.value.id.endswith("Repo"))
        is_passthrough_helper = (isinstance(func, ast.Name)
                                 and func.id.startswith(_PASSTHROUGH_HELPER_PREFIXES))
        if not (is_repo_list or is_passthrough_helper):
            continue
        kw = next((k for k in n.keywords if k.arg == "scope"), None)
        if kw is None:
            if is_repo_list:
                found.append("user")       # default fail-safe của BaseRepository.list
            continue                       # helper: scope là keyword bắt buộc
        if isinstance(kw.value, ast.Constant):
            found.append(str(kw.value.value))
        elif isinstance(kw.value, ast.Name) and kw.value.id in params:
            found.append("<passthrough>")
        else:
            found.append("<dynamic>")
    return found


def _is_guarded(fn_node: ast.FunctionDef) -> bool:
    """True nếu hàm bọc PermissionError → 403 envelope (decorator hoặc delegate)."""
    for dec in fn_node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "rowscoped":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "rowscoped":
            return True
    for n in ast.walk(fn_node):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id == "run_rowscoped":
            return True
    return False


class TestRowScopeStaticGuard(FrappeTestCase):
    """Guard AST — chặn rot ma trận §8.4 ngay khi code đổi."""

    # ── G1 — mọi scope literal phải hợp lệ (chống typo "System" = permissive câm) ──
    def test_every_scope_literal_is_valid(self):
        bad = [
            (rel, fn.name, sc)
            for rel, fn in _iter_module_functions()
            for sc in _repo_list_scopes(fn)
            if sc not in _LIST_SCOPES and sc != "<passthrough>"
        ]
        self.assertEqual(
            bad, [],
            "scope literal không hợp lệ (hoặc dựng động — không audit được tĩnh). "
            f"Chỉ chấp nhận {_LIST_SCOPES}: {bad}",
        )

    # ── G2 — allowlist: nới quyền phải đi kèm ratify trong ADR §8.4 ─────────────
    def test_non_user_scope_call_sites_are_ratified(self):
        actual = {
            (rel, fn.name, sc)
            for rel, fn in _iter_module_functions()
            for sc in _repo_list_scopes(fn)
            if sc not in ("user", "<passthrough>")
        }
        added = actual - _ALLOWED_NON_USER_SCOPES
        removed = _ALLOWED_NON_USER_SCOPES - actual
        self.assertEqual(
            added, set(),
            "Call site MỚI bỏ row-scope mà CHƯA ratify: mỗi entry phải có hàng trong "
            "ma trận ADR-IMM00-LIST-SCOPE §8.4 + lý do nghiệp vụ. `internal` bỏ CẢ "
            "DocPerm read ⇒ TUYỆT ĐỐI không dùng cho endpoint người-dùng. "
            f"Chưa ratify: {sorted(added)}",
        )
        self.assertEqual(
            removed, set(),
            "Allowlist còn entry không tồn tại trong code (ma trận §8.4 đã rot) — "
            f"xoá khỏi allowlist + ADR: {sorted(removed)}",
        )

    # ── G3 — entrypoint đọc PHẢI bọc 403 envelope (không 500 câm) ───────────────
    def test_read_entrypoints_wrap_permission_error(self):
        unguarded = []
        for rel, fn in _iter_module_functions():
            if not rel.startswith("services/") or fn.name.startswith("_"):
                continue
            if not fn.name.startswith(_ENTRYPOINT_PREFIXES):
                continue
            scopes = set(_repo_list_scopes(fn))
            if not (scopes & {"user", "system"}):
                continue                      # chỉ internal ⇒ không raise được
            if not _is_guarded(fn):
                unguarded.append(f"{rel}::{fn.name} {sorted(scopes)}")
        self.assertEqual(
            unguarded, [],
            "Entrypoint đọc chạy `frappe.get_list` (scope user/system) mà KHÔNG bọc "
            "`@rowscoped`/`run_rowscoped` ⇒ persona thiếu DocPerm read nhận "
            "`frappe.PermissionError` TRẦN = 500 câm / dispatcher-403 (FE hiểu nhầm "
            "hết phiên → ĐĂNG XUẤT người dùng) thay vì Error envelope 403 trên "
            f"HTTP-200 (BR-00-ROWSCOPE-403): {unguarded}",
        )

    # ── G4 — raw query trên DocType row-scoped phải có role-gate tường minh ──
    def test_raw_queries_on_rowscoped_doctypes_are_gated(self):
        """Endpoint đọc gọi THẲNG ``frappe.get_all``/``frappe.db.count`` trên DocType
        có ``permission_query_conditions`` ⇒ bỏ CẢ ROW-scope LẪN DocPerm read
        (không ``BaseRepository`` nào chạy gate hộ) ⇒ phải gate tường minh
        (``assert_doctype_read_permission`` / ``rbac.require`` / ``rbac.can``) hoặc
        nằm trong backlog ĐÃ BIẾT.
        """
        rowscoped = _rowscoped_doctypes()
        offenders: set[tuple[str, str]] = set()
        detail: dict[tuple[str, str], list[str]] = {}
        for sub in _SCAN_DIRS:
            for path in sorted((_APP_ROOT / sub).glob("*.py")):
                rel = f"{sub}/{path.name}"
                tree = ast.parse(path.read_text(encoding="utf-8"))
                consts = _module_str_consts(tree)
                for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
                    if fn.name.startswith("_") or not fn.name.startswith(_ENTRYPOINT_PREFIXES):
                        continue
                    hits = _raw_rowscoped_hits(fn, consts, rowscoped)
                    if hits and not _has_role_gate(fn):
                        offenders.add((rel, fn.name))
                        detail[(rel, fn.name)] = sorted(hits)
        added = offenders - _RAW_QUERY_UNGATED_BACKLOG
        self.assertEqual(
            added, set(),
            "Endpoint đọc MỚI truy vấn RAW một DocType row-scoped mà KHÔNG gate "
            "quyền — mọi persona (kể cả Vendor Engineer ngoài viện) đọc được toàn "
            "bộ bảng, và `frappe.db.count` còn lộ TỔNG SỐ vượt ngoài `limit`. "
            "Fix: `assert_doctype_read_permission(<doctype>)` + `@rowscoped`, hoặc "
            "đi qua `BaseRepository.list(scope=...)`. "
            f"Chưa gate: {sorted((m + '::' + f, detail[(m, f)]) for m, f in added)}",
        )

    # ── G4b — allowlist raw-query CHỈ-GIẢM (AC-CR-98 / TC-BE-CR98-5) ────────
    def test_raw_query_backlog_only_shrinks(self):
        """Trần cứng cho ``_RAW_QUERY_UNGATED_BACKLOG``: **16** mục sau AC-CR-98.

        G4 chỉ chặn offender MỚI *không có trong* backlog ⇒ cách "sửa cho xanh" rẻ
        nhất là **thêm một dòng vào backlog**. Đó đúng là thao tác phải bất khả: mỗi
        dòng ở đây = một endpoint đọc RAW một DocType row-scoped, tức một chỗ để rò
        dữ liệu ngoài phạm vi + một chỗ để ``count != drill``.

        Sửa một mục ⇒ XOÁ dòng đó **và** hạ trần trong CÙNG commit (số chỉ được giảm).
        """
        self.assertNotIn(
            ("services/imm04.py", "list_commissioning"), _RAW_QUERY_UNGATED_BACKLOG,
            "AC-CR-98 đã land (count_with_or + frappe.get_list + "
            "assert_doctype_read_permission) ⇒ mục này KHÔNG được quay lại backlog",
        )
        self.assertLessEqual(
            len(_RAW_QUERY_UNGATED_BACKLOG), 16,
            "allowlist chỉ được GIẢM; thêm mục mới = thăng-hạng-ngược, phải gate thay "
            f"vì ghi nợ (hiện {len(_RAW_QUERY_UNGATED_BACKLOG)} mục, trần 16)",
        )

    # ── G5a — GET-detail load doc row-scoped phải gate tường minh (CR-74) ────
    def test_detail_reads_are_gated(self):
        """Mọi ``get_*`` public trong ``services/imm*.py`` load nguyên bản ghi của DocType
        row-scoped (``<X>Repo.get`` / ``frappe.get_doc``) PHẢI có gate quyền TRONG THÂN HÀM.

        ``frappe.get_doc`` KHÔNG kiểm tra quyền ⇒ không gate = bất kỳ user đã đăng nhập
        nào cũng đọc trọn hồ sơ bằng URL trực tiếp, kể cả persona 0 DocPerm read
        (IDOR-đọc, OWASP A01). Fix: khuôn 3 lớp ROLE→EXISTS→ROW (ADR-IMM00-LIST-SCOPE
        §9.4) — ``assert_doctype_read_permission(<DocType>)`` TRƯỚC ``exists``, rồi
        ``assert_can_read_doc(<DocType>, doc)`` trên doc đã load.
        """
        rowscoped = _rowscoped_doctypes()
        repo_map = _repo_doctype_map()
        offenders: set[tuple[str, str]] = set()
        detail: dict[tuple[str, str], list[str]] = {}
        for path in sorted((_APP_ROOT / "services").glob("imm*.py")):
            rel = f"services/{path.name}"
            tree = ast.parse(path.read_text(encoding="utf-8"))
            consts = _module_str_consts(tree)
            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
                if fn.name.startswith("_") or not fn.name.startswith("get_"):
                    continue
                hits = _detail_load_hits(fn, consts, repo_map, rowscoped)
                if hits and not _gate_calls(fn):
                    offenders.add((rel, fn.name))
                    detail[(rel, fn.name)] = sorted(hits)
        added = offenders - _DETAIL_READ_UNGATED_BACKLOG
        self.assertEqual(
            added, set(),
            "GET-detail MỚI load bản ghi của DocType row-scoped mà KHÔNG gate quyền — "
            "`frappe.get_doc` không gọi `check_permission`, nên hook `has_permission` "
            "(hooks.py:448-455) KHÔNG chạy và DocPerm read cũng không được kiểm ⇒ đọc "
            "trọn hồ sơ bằng URL trực tiếp. Fix: dán khuôn 3 lớp §9.4 "
            "(assert_doctype_read_permission → Repo.get → assert_can_read_doc) + "
            f"@rowscoped. Chưa gate: {sorted((m + '::' + f, detail[(m, f)]) for m, f in added)}",
        )

    # ── G5b — op C6-DETAIL nêu đích danh phải có ĐỦ CẢ HAI gate ─────────────
    def test_cr74_named_detail_ops_have_both_gates(self):
        """G5a mù với 2 trong 4 op CR-74 (IMM-11 chưa có hook; IMM-12 load qua helper) và
        mù với `evaluate_gate_status` của CR-76 (tên không mang tiền tố `get_`) ⇒ vế
        NAMED là thứ duy nhất ghim đủ. Cả hai lớp đều bắt buộc: thiếu L0 (ROLE) ⇒
        persona 0-DocPerm vẫn đọc được; thiếu L2 (ROW) ⇒ KTV đọc phiếu đồng nghiệp."""
        missing: list[str] = []
        for path in sorted((_APP_ROOT / "services").glob("imm*.py")):
            rel = f"services/{path.name}"
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
                key = (rel, fn.name)
                if key not in _NAMED_DETAIL_GATES:
                    continue
                gates = _gate_calls(fn)
                for need in ("assert_doctype_read_permission", "assert_can_read_doc"):
                    if need not in gates:
                        missing.append(f"{rel}::{fn.name} thiếu {need}()")
                if not _is_guarded(fn):
                    missing.append(f"{rel}::{fn.name} thiếu @rowscoped")
        seen = {(rel, fn.name)
                for path in sorted((_APP_ROOT / "services").glob("imm*.py"))
                for rel in [f"services/{path.name}"]
                for fn in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
                if isinstance(fn, ast.FunctionDef) and (rel, fn.name) in _NAMED_DETAIL_GATES}
        vanished = sorted(set(_NAMED_DETAIL_GATES) - seen)
        self.assertEqual(
            vanished, [],
            f"Hàm C6-DETAIL bị đổi tên/xoá ⇒ guard rot âm thầm: {vanished}",
        )
        self.assertEqual(
            missing, [],
            "CR-74 (ADR-IMM00-LIST-SCOPE §9.4) + CR-76 (BR-04-16): mọi op đọc-chi-tiết "
            "nêu đích danh PHẢI có ĐỦ khuôn 3 lớp ROLE→EXISTS→ROW + @rowscoped trong "
            "CHÍNH thân hàm service (gate ở API tier chỉ vá call site hiện tại, call "
            f"site nội bộ tương lai vẫn đọc trần). Thiếu: {missing}",
        )

    # ── G5c — allowlist CHỈ-GIẢM: op đã gate KHÔNG được quay lại backlog ────
    def test_named_detail_gates_never_in_ungated_backlog(self):
        """TC-04-GATE-19 (AC5) — một cặp KHÔNG thể vừa "đã gate" vừa "được miễn gate".

        `_DETAIL_READ_UNGATED_BACKLOG` là allowlist **chỉ-giảm**: thêm dòng = mở lại lỗ
        IDOR-đọc. Không có guard này thì cách "sửa cho xanh" rẻ nhất khi G5b đỏ là
        thêm hàm vào backlog — đúng thứ phải bất khả.
        """
        overlap = sorted(set(_NAMED_DETAIL_GATES) & _DETAIL_READ_UNGATED_BACKLOG)
        self.assertEqual(
            overlap, [],
            "Op đọc-chi-tiết ĐÃ có khuôn 3 lớp mà vẫn nằm trong allowlist miễn-gate "
            f"⇒ mâu thuẫn (và che mất regression thật): {overlap}",
        )


class _ProbeRepo(BaseRepository):
    DOCTYPE = "Asset Repair"


class TestRowScopeRepoContract(FrappeTestCase):
    """Hợp đồng hành vi của `BaseRepository.list` — 2 trục quyền ĐỘC LẬP."""

    _EMAIL = "scope_guard_probe@example.invalid"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        frappe.set_user("Administrator")
        if frappe.db.exists("User", cls._EMAIL):
            frappe.delete_doc("User", cls._EMAIL, force=True, ignore_permissions=True)
        u = frappe.get_doc({
            "doctype": "User", "email": cls._EMAIL, "first_name": "Scope Probe",
            "send_welcome_email": 0, "enabled": 1,
        }).insert(ignore_permissions=True)
        u.add_roles("AssetCore System User")   # base role: KHÔNG có read Asset Repair
        frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        if frappe.db.exists("User", cls._EMAIL):
            frappe.delete_doc("User", cls._EMAIL, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_system_scope_still_enforces_role_docperm(self):
        """`system` nới ROW-scope nhưng KHÔNG nới DocPerm read cấp vai-trò."""
        frappe.set_user(self._EMAIL)
        self.assertFalse(frappe.has_permission("Asset Repair", "read"),
                         "tiền đề: base role KHÔNG có DocPerm read Asset Repair")
        with self.assertRaises(frappe.PermissionError):
            _ProbeRepo.list(scope="system", page_size=1)

    def test_internal_scope_bypasses_everything(self):
        """`internal` = scheduler/domain-logic: KHÔNG kiểm tra quyền (có chủ đích)."""
        frappe.set_user(self._EMAIL)
        rows, pg = _ProbeRepo.list(scope="internal", page_size=1)
        self.assertIsInstance(rows, list)
        self.assertIn("total", pg)

    def test_invalid_scope_fails_fast(self):
        with self.assertRaises(ValueError):
            _ProbeRepo.list(scope="System", page_size=1)   # typo hoa/thường
